"""Ejecuta la lectura, normalización, cálculo y publicación de los datos."""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import time
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import geopandas as gpd
import numpy as np
import pandas as pd
import psutil

from . import __version__
from .config import PipelineConfig
from .quality import QualityLog
from .reports import project_summary, write_quality_html

Progress = Callable[[str, float, str], None]
ALL = "ALL"
OCCASION_WINDOW_DAYS = 7


def _noop(stage: str, progress: float, message: str) -> None:
    del stage, progress, message


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _replace_with_retries(source: Path, target: Path, attempts: int = 8) -> None:
    """Reemplaza una ruta y tolera bloqueos breves de Windows."""
    for attempt in range(attempts):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == attempts - 1:
                raise
            time.sleep(min(2.0, 0.25 * (2**attempt)))


def _remove_tree_with_retries(path: Path, attempts: int = 5) -> bool:
    if not path.exists():
        return True
    for attempt in range(attempts):
        try:
            shutil.rmtree(path)
            return True
        except PermissionError:
            if attempt == attempts - 1:
                return False
            time.sleep(min(1.0, 0.2 * (2**attempt)))
    return False


def _read_csv(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, low_memory=False, dtype={"project_id": "string", "deployment_id": "string"})
    frame["source_file"] = path.name
    frame["source_row"] = np.arange(2, len(frame) + 2, dtype=np.int64)
    return frame


def _mode(series: pd.Series) -> object:
    values = series.dropna().astype(str).str.strip()
    values = values[values.ne("")]
    if values.empty:
        return pd.NA
    counts = values.value_counts()
    return sorted(counts[counts.eq(counts.max())].index)[0]


def _hill(values: pd.Series, q: int) -> float:
    """Calcula la diversidad efectiva para el orden de Hill solicitado."""
    counts = values.dropna().astype(str)
    counts = counts[counts.str.strip().ne("")].value_counts().to_numpy(dtype=float)
    if counts.size == 0:
        return 0.0
    if q == 0:
        return float(counts.size)
    proportions = counts / counts.sum()
    if q == 1:
        return float(np.exp(-(proportions * np.log(proportions)).sum()))
    return float(np.power(np.power(proportions, q).sum(), 1.0 / (1.0 - q)))


def _write_parquet(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serializable = frame.copy()
    object_columns = [
        column for column in serializable.columns
        if pd.api.types.is_object_dtype(serializable[column].dtype)
    ]
    for column in object_columns:
        serializable[column] = serializable[column].astype("string")
    serializable.to_parquet(path, index=False, engine="pyarrow", compression="zstd")


def _image_paths(config: PipelineConfig) -> list[Path]:
    if not config.selected_projects:
        return sorted(config.raw_path.glob("images_*.csv"))
    return [
        config.raw_path / f"images_{project_id}.csv"
        for project_id in config.selected_projects
        if (config.raw_path / f"images_{project_id}.csv").exists()
    ]


def _load_raw(
    config: PipelineConfig,
    quality: QualityLog,
    progress: Progress = _noop,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    projects_path = config.raw_path / "projects.csv"
    deployments_path = config.raw_path / "deployments.csv"
    image_paths = _image_paths(config)
    missing = [str(x) for x in (projects_path, deployments_path) if not x.exists()]
    if missing or not image_paths:
        raise ValueError(f"Faltan archivos RAW requeridos: {missing or ['images_*.csv']}")

    projects = _read_csv(projects_path)
    deployments = _read_csv(deployments_path)
    image_frames: list[pd.DataFrame] = []
    image_total = max(1, len(image_paths))
    for index, path in enumerate(image_paths, start=1):
        image_frames.append(_read_csv(path))
        progress("bronze", 0.02 + 0.13 * index / image_total, f"Leyendo archivo {index} de {image_total}")
    images = pd.concat(image_frames, ignore_index=True, sort=False)
    for frame in (projects, deployments, images):
        for column in ("project_id", "deployment_id"):
            if column in frame:
                frame[column] = frame[column].astype("string").str.strip()

    if config.selected_projects:
        selected = set(map(str, config.selected_projects))
        projects = projects[projects["project_id"].isin(selected)].copy()
        deployments = deployments[deployments["project_id"].isin(selected)].copy()
        images = images[images["project_id"].isin(selected)].copy()
        absent = selected.difference(projects["project_id"].dropna().astype(str))
        if absent:
            raise ValueError("Los proyectos solicitados no existen en projects.csv: " + ", ".join(sorted(absent)))

    duplicate_projects = projects[projects.duplicated("project_id", keep=False)]
    quality.add_rows(
        duplicate_projects, stage="bronze", severity="error", rule="PROJECT_KEY_DUPLICATE",
        id_column="project_id", field="project_id", action="deduplicated_mode"
    )
    projects = projects.drop_duplicates("project_id", keep="first")

    dep_key = ["project_id", "deployment_id", "subproject_name", "start_date", "end_date"]
    duplicate_deployments = deployments[deployments.duplicated(dep_key, keep=False)]
    quality.add_rows(
        duplicate_deployments, stage="bronze", severity="error", rule="DEPLOYMENT_KEY_DUPLICATE",
        id_column="deployment_id", field="deployment_id", action="deduplicated_first"
    )
    deployments = deployments.drop_duplicates(dep_key, keep="first")
    return projects, deployments, images


def _assign_corporations(deployments: pd.DataFrame, shapefile: Path | None, quality: QualityLog) -> pd.DataFrame:
    result = deployments[["project_id", "deployment_id", "longitude", "latitude"]].copy()
    result["longitude"] = pd.to_numeric(result["longitude"], errors="coerce")
    result["latitude"] = pd.to_numeric(result["latitude"], errors="coerce")
    valid = result["longitude"].between(-180, 180) & result["latitude"].between(-90, 90)
    invalid = result[~valid]
    quality.add_rows(
        invalid, stage="silver", severity="warning", rule="COORDINATE_INVALID",
        id_column="deployment_id", field="longitude", action="corporation_unassigned"
    )
    result["Corporacion"] = pd.NA
    if shapefile is None or not shapefile.exists() or not valid.any():
        return result[["project_id", "deployment_id", "Corporacion"]].drop_duplicates(
            ["project_id", "deployment_id"]
        )

    polygons = gpd.read_file(shapefile).to_crs(4326)
    name_column = next((x for x in ("NOMBRE_CAR", "CAR", "NOMBRE", "Nombre", "corporacion") if x in polygons), None)
    if name_column is None:
        raise ValueError("El shapefile no contiene una columna reconocible para la corporación")
    points = gpd.GeoDataFrame(
        result.loc[valid, ["project_id", "deployment_id"]],
        geometry=gpd.points_from_xy(result.loc[valid, "longitude"], result.loc[valid, "latitude"]),
        crs=4326,
    )
    joined = gpd.sjoin(points, polygons[[name_column, "geometry"]], how="left", predicate="within")
    unmatched = joined[name_column].isna()
    if unmatched.any():
        fallback = gpd.sjoin(points.loc[unmatched], polygons[[name_column, "geometry"]], how="left", predicate="intersects")
        joined.loc[unmatched, name_column] = fallback.groupby(level=0)[name_column].first()
    assignments = joined.groupby(["project_id", "deployment_id"], as_index=False)[name_column].agg(_mode)
    assignments = assignments.rename(columns={name_column: "Corporacion"})
    deployment_ids = result[["project_id", "deployment_id"]].drop_duplicates()
    return deployment_ids.merge(assignments, on=["project_id", "deployment_id"], how="left")


def _build_silver(
    projects: pd.DataFrame,
    deployments: pd.DataFrame,
    images: pd.DataFrame,
    config: PipelineConfig,
    quality: QualityLog,
) -> dict[str, pd.DataFrame]:
    """Normaliza los insumos y construye las tablas validadas."""
    start = pd.Timestamp(config.start_date)
    cutoff = pd.Timestamp(config.cutoff_date)
    images["timestamp_original"] = images.get("timestamp", pd.Series(index=images.index, dtype="string")).astype("string")
    images["photo_datetime"] = pd.to_datetime(images["timestamp_original"], errors="coerce", format="mixed")

    invalid_time = images["photo_datetime"].isna()
    before_start = images["photo_datetime"].dt.normalize().lt(start)
    after_end = images["photo_datetime"].dt.normalize().gt(cutoff)
    quality.add_rows(images[invalid_time], stage="silver", severity="error", rule="TIMESTAMP_INVALID", id_column="image_id", field="timestamp_original", action="quarantined")
    quality.add_rows(images[before_start], stage="silver", severity="info", rule="TIMESTAMP_BEFORE_START", id_column="image_id", field="timestamp_original", action="excluded_by_date_range")
    quality.add_rows(images[after_end], stage="silver", severity="info", rule="TIMESTAMP_AFTER_END", id_column="image_id", field="timestamp_original", action="excluded_by_date_range")
    images = images[~(invalid_time | before_start | after_end)].copy()

    merge_columns = [
        "project_id", "deployment_id", "placename", "longitude", "latitude", "start_date", "end_date",
        "subproject_name", "event_name", "recorded_by"
    ]
    deployment_lookup = deployments[[x for x in merge_columns if x in deployments]].copy()
    deployment_lookup["_deployment_match"] = True
    observations = images.merge(
        deployment_lookup,
        on=["project_id", "deployment_id"],
        how="left",
    )
    observations["_raw_row_id"] = observations["source_file"].astype(str) + "||" + observations["source_row"].astype(str)
    candidate_counts = observations.groupby("_raw_row_id")["_raw_row_id"].transform("size")
    candidate_start = pd.to_datetime(observations["start_date"], errors="coerce").dt.normalize()
    candidate_end = pd.to_datetime(observations["end_date"], errors="coerce").dt.normalize()
    photo_date = observations["photo_datetime"].dt.normalize()
    observations["_period_match"] = photo_date.between(candidate_start, candidate_end)
    ambiguous = observations[candidate_counts.gt(1)].drop_duplicates("_raw_row_id")
    quality.add_rows(
        ambiguous, stage="silver", severity="warning", rule="DEPLOYMENT_EVENT_AMBIGUOUS",
        id_column="image_id", field="deployment_id", action="resolved_by_installation_period"
    )
    observations = (
        observations.sort_values(["_raw_row_id", "_period_match", "subproject_name"], ascending=[True, False, True])
        .drop_duplicates("_raw_row_id", keep="first")
        .drop(columns=["_raw_row_id", "_period_match"])
    )
    missing_deployment = observations["_deployment_match"].isna()
    event_name = observations["subproject_name"].astype("string").str.strip()
    missing_event = ~missing_deployment & (event_name.isna() | event_name.eq(""))
    quality.add_rows(
        observations[missing_deployment], stage="silver", severity="error", rule="DEPLOYMENT_ORPHAN",
        id_column="image_id", field="deployment_id", action="quarantined"
    )
    quality.add_rows(
        observations[missing_event], stage="silver", severity="error", rule="EVENT_NAME_MISSING",
        id_column="image_id", field="subproject_name", action="quarantined"
    )
    observations = observations[~(missing_deployment | missing_event)].copy()
    observations = observations.drop(columns="_deployment_match")

    event_match = observations["subproject_name"].astype("string").str.extract(r"^(\d{4})_([1-9]\d*)$")
    event_year = pd.to_numeric(event_match[0], errors="coerce")
    valid_event = event_match[0].notna() & event_year.ge(config.minimum_event_year)
    quality.add_rows(observations[~valid_event], stage="silver", severity="error", rule="EVENT_CODE_INVALID", id_column="image_id", field="subproject_name", action="quarantined")
    observations = observations[valid_event].copy()
    event_year = event_year[valid_event]

    photo_year = observations["photo_datetime"].dt.year
    mismatch = photo_year.lt(event_year - config.event_year_tolerance_before) | photo_year.gt(event_year + config.event_year_tolerance_after)
    quality.add_rows(observations[mismatch], stage="silver", severity="error", rule="EVENT_YEAR_MISMATCH", id_column="image_id", field="timestamp_original", action="quarantined")
    observations = observations[~mismatch].copy()

    genus = observations.get("genus", pd.Series(index=observations.index, dtype="string")).astype("string").str.strip()
    species = observations.get("species", pd.Series(index=observations.index, dtype="string")).astype("string").str.strip()
    valid_taxon = genus.notna() & species.notna() & ~genus.isin(["No CV Result", "Unknown", ""]) & ~species.isin(["No CV Result", "Unknown", ""])
    quality.add_rows(observations[~valid_taxon], stage="silver", severity="info", rule="TAXON_EXCLUDED", id_column="image_id", field="wi_taxon_id", action="excluded_from_biodiversity")
    observations = observations[valid_taxon].copy()
    observations["sp_binomial"] = genus[valid_taxon] + " " + species[valid_taxon]

    corporations = _assign_corporations(deployments, config.shapefile_path, quality)
    overrides = dict(config.corporation_overrides)
    for project_id, corporation in overrides.items():
        affected = corporations["project_id"].astype(str).eq(str(project_id))
        if affected.any():
            previous = ", ".join(sorted(set(corporations.loc[affected, "Corporacion"].dropna().astype(str)))) or "Sin asignación"
            corporations.loc[affected, "Corporacion"] = corporation
            quality.add(
                stage="silver", severity="info", rule="MANUAL_CORPORATION_OVERRIDE",
                entity_type="project", entity_id=str(project_id), field="Corporacion",
                original_value=previous, action=f"reassigned_to:{corporation}",
            )
    deployments = deployments.merge(corporations, on=["project_id", "deployment_id"], how="left")
    project_corp = deployments.groupby("project_id", as_index=False)["Corporacion"].agg(_mode)
    projects = projects.merge(project_corp, on="project_id", how="left")
    observations = observations.merge(
        corporations[["project_id", "deployment_id", "Corporacion"]],
        on=["project_id", "deployment_id"],
        how="left",
        validate="many_to_one",
    )

    project_meta = projects[[x for x in ("project_id", "project_short_name", "project_name", "project_admin", "project_admin_email", "project_admin_organization", "initiative_id", "Corporacion") if x in projects]].copy()
    project_meta["initiative_name"] = config.initiative_name
    observations = observations.merge(project_meta.drop(columns=["Corporacion"], errors="ignore"), on="project_id", how="left")

    published_pairs = observations[["project_id", "subproject_name"]].drop_duplicates()
    deployments = deployments.merge(
        published_pairs.assign(_published=True),
        on=["project_id", "subproject_name"],
        how="inner",
        validate="many_to_one",
    ).drop(columns="_published")

    deployments["declared_start_date"] = pd.to_datetime(deployments["start_date"], errors="coerce").dt.normalize()
    deployments["declared_end_date"] = pd.to_datetime(deployments["end_date"], errors="coerce").dt.normalize()
    bad_order = deployments["declared_end_date"].lt(deployments["declared_start_date"])
    outside_range = deployments["declared_start_date"].gt(cutoff) | deployments["declared_end_date"].lt(start)
    quality.add_rows(deployments[bad_order], stage="silver", severity="error", rule="DEPLOYMENT_PERIOD_REVERSED", id_column="deployment_id", field="end_date", action="quarantined")
    quality.add_rows(deployments[outside_range], stage="silver", severity="info", rule="DEPLOYMENT_OUTSIDE_RANGE", id_column="deployment_id", field="start_date", action="excluded_by_date_range")
    deployments = deployments[~(bad_order | outside_range)].copy()

    observed = observations.groupby(["project_id", "deployment_id"], as_index=False).agg(
        observed_min_date=("photo_datetime", "min"), observed_max_date=("photo_datetime", "max")
    )
    observed["observed_min_date"] = observed["observed_min_date"].dt.normalize()
    observed["observed_max_date"] = observed["observed_max_date"].dt.normalize()
    deployments = deployments.merge(observed, on=["project_id", "deployment_id"], how="left")
    deployments["effective_start_date"] = deployments["declared_start_date"].fillna(deployments["observed_min_date"])
    deployments["effective_end_date"] = deployments["declared_end_date"].fillna(deployments["observed_max_date"])
    deployments["effective_start_date"] = deployments["effective_start_date"].clip(lower=start)
    deployments["effective_end_date"] = deployments["effective_end_date"].clip(upper=cutoff)
    deployments["deployment_days"] = (deployments["effective_end_date"] - deployments["effective_start_date"]).dt.days.add(1).clip(lower=0)
    deployments["deployment_key"] = (
        deployments["project_id"].astype(str) + "||" + deployments["subproject_name"].astype(str)
        + "||" + deployments["deployment_id"].astype(str)
    )
    observations["deployment_key"] = (
        observations["project_id"].astype(str) + "||" + observations["subproject_name"].astype(str)
        + "||" + observations["deployment_id"].astype(str)
    )

    dep_valid_keys = set(deployments["deployment_key"])
    observations = observations[observations["deployment_key"].isin(dep_valid_keys)].copy()

    taxonomy_columns = [x for x in ("wi_taxon_id", "sp_binomial", "class", "order", "family", "genus", "species", "common_name") if x in observations]
    taxonomy = observations[taxonomy_columns].groupby("sp_binomial", as_index=False).agg({x: _mode for x in taxonomy_columns if x != "sp_binomial"})
    observations = observations.drop(columns=[x for x in ("wi_taxon_id", "class", "order", "family", "genus", "species", "common_name") if x in observations]).merge(taxonomy, on="sp_binomial", how="left")

    event_dimension = deployments[["project_id", "subproject_name"]].dropna().drop_duplicates().rename(columns={"subproject_name": "event_id"})
    event_dimension["event_year"] = pd.to_numeric(event_dimension["event_id"].str.extract(r"^(\d{4})")[0], errors="coerce").astype("Int64")
    published_projects = set(observations["project_id"].dropna().astype(str))
    project_dimension = project_meta[project_meta["project_id"].astype(str).isin(published_projects)].copy()
    return {
        "dim_project": project_dimension.drop_duplicates("project_id"),
        "dim_event": event_dimension,
        "dim_deployment": deployments,
        "dim_taxon": taxonomy,
        "fact_observation": observations,
        "bridge_deployment_corporation": corporations.dropna(subset=["Corporacion"]).drop_duplicates(),
    }


def _independent_records(observations: pd.DataFrame, minutes: int) -> pd.DataFrame:
    """Conserva detecciones separadas por el intervalo solicitado."""
    group = ["project_id", "subproject_name", "deployment_id", "sp_binomial"]
    ordered = observations.sort_values(group + ["photo_datetime"]).copy()
    if minutes == 0:
        return ordered.reset_index(drop=True)
    threshold = minutes * 60

    keep_indices: list[int] = []
    for _, group_frame in ordered.groupby(group, sort=False, observed=True):
        seconds = (
            group_frame["photo_datetime"] - pd.Timestamp("1970-01-01")
        ).dt.total_seconds().to_numpy()
        mask = np.zeros(len(group_frame), dtype=bool)
        last = None
        for index, value in enumerate(seconds):
            if last is None or value - last >= threshold:
                mask[index] = True
                last = value
        keep_indices.extend(group_frame.index[mask].tolist())
    return ordered.loc[keep_indices].sort_values(group + ["photo_datetime"]).reset_index(drop=True)


def _scope_catalog(projects: pd.DataFrame, deployments: pd.DataFrame) -> list[tuple[str, str]]:
    scopes: list[tuple[str, str]] = [("global", ALL)]
    scopes.extend(("project", str(project)) for project in projects["project_id"].dropna().unique())
    scopes.extend(
        ("corporation", str(corporation))
        for corporation in deployments["Corporacion"].dropna().astype(str).unique()
        if corporation.strip()
    )
    return scopes


def _scope_filter(frame: pd.DataFrame, scope_type: str, scope_id: str) -> pd.DataFrame:
    if scope_type == "global":
        return frame
    column = "project_id" if scope_type == "project" else "Corporacion"
    return frame[frame[column].astype(str).eq(scope_id)]


def _indicator_row(
    observations: pd.DataFrame,
    independent: pd.DataFrame,
    deployments: pd.DataFrame,
    event_id: str,
) -> dict[str, object]:
    """Resume esfuerzo, cobertura y diversidad para un intervalo temporal."""
    return {
        "event_id": event_id,
        "images": int(len(observations)),
        "independent_records": int(len(independent)),
        "cameras": int(deployments["deployment_key"].nunique()),
        "camera_days": float(deployments["deployment_days"].fillna(0).sum()),
        "species": int(independent["sp_binomial"].nunique()),
        "mammals": int(independent.loc[independent["class"].eq("Mammalia"), "sp_binomial"].nunique()),
        "birds": int(independent.loc[independent["class"].eq("Aves"), "sp_binomial"].nunique()),
        "hill1": _hill(independent["sp_binomial"], 0),
        "hill2": _hill(independent["sp_binomial"], 1),
        "hill3": _hill(independent["sp_binomial"], 2),
    }


def _species_rows(
    observations: pd.DataFrame,
    independent: pd.DataFrame,
    deployments: pd.DataFrame,
    taxonomy: pd.DataFrame,
    selection_event: str,
) -> pd.DataFrame:
    images = observations.groupby("sp_binomial").size().rename("image_count")
    independent_count = independent.groupby("sp_binomial").size().rename("independent_count")
    base = pd.concat([images, independent_count], axis=1).fillna(0).reset_index()
    base["ranking"] = base.sort_values(["independent_count", "sp_binomial"], ascending=[False, True]).reset_index().index + 1
    ranking = base.sort_values(["independent_count", "sp_binomial"], ascending=[False, True]).copy()
    ranking["ranking"] = np.arange(1, len(ranking) + 1)
    base = ranking.merge(taxonomy, on="sp_binomial", how="left")

    events = sorted(observations["subproject_name"].dropna().astype(str).unique(), reverse=True)
    rows: list[pd.DataFrame] = []
    dep_cols = ["deployment_key", "subproject_name", "effective_start_date", "effective_end_date"]
    for event in events:
        event_ind = independent[independent["subproject_name"].astype(str).eq(event)].copy()
        event_dep = deployments[deployments["subproject_name"].astype(str).eq(event)].copy()
        eligible = event_dep["effective_start_date"].notna() & event_dep["effective_end_date"].notna() & event_dep["effective_end_date"].ge(event_dep["effective_start_date"])
        event_dep = event_dep[eligible]
        denominator = event_dep["deployment_key"].nunique()
        occupancy = event_ind.groupby("sp_binomial")["deployment_key"].nunique().div(denominator if denominator else np.nan).rename("occupancy")

        joined = event_ind.merge(event_dep[dep_cols], on=["deployment_key", "subproject_name"], how="inner")
        joined["photo_date"] = joined["photo_datetime"].dt.normalize()
        joined = joined[joined["photo_date"].between(joined["effective_start_date"], joined["effective_end_date"])]
        joined["total_occasions_camera"] = np.ceil(
            (joined["effective_end_date"] - joined["effective_start_date"]).dt.days.add(1)
            / OCCASION_WINDOW_DAYS
        ).clip(lower=1)
        joined["occasion"] = np.floor(
            (joined["photo_date"] - joined["effective_start_date"]).dt.days
            / OCCASION_WINDOW_DAYS
        ).add(1)
        den = joined[["sp_binomial", "deployment_key", "total_occasions_camera"]].drop_duplicates().groupby("sp_binomial")["total_occasions_camera"].sum().rename("total_occasions")
        num = joined[["sp_binomial", "deployment_key", "occasion"]].drop_duplicates().groupby("sp_binomial").size().rename("detected_occasions")
        frequency = pd.concat([num, den], axis=1).fillna(0)
        frequency["frequency"] = frequency["detected_occasions"].div(frequency["total_occasions"].replace(0, np.nan))

        event_ind["date"] = event_ind["photo_datetime"].dt.normalize()
        event_ind["is_day"] = event_ind["photo_datetime"].dt.hour.between(6, 17)
        daily = event_ind.groupby(["sp_binomial", "date"])["is_day"].agg([("day_records", "sum"), ("daily_records", "size")]).reset_index()
        daily["daily_diurnality"] = daily["day_records"] / daily["daily_records"]
        diurnality = daily.groupby("sp_binomial").agg(
            day_independent_records=("day_records", "sum"),
            independent_records_24h=("daily_records", "sum"),
            diurnality=("daily_diurnality", "mean"),
        )

        metric = base.copy()
        metric["metric_event"] = event
        metric = metric.merge(occupancy, on="sp_binomial", how="left")
        metric = metric.merge(frequency, on="sp_binomial", how="left")
        metric = metric.merge(diurnality, on="sp_binomial", how="left")
        no_detection = metric["occupancy"].isna()
        metric.loc[no_detection, "occupancy"] = 0.0
        metric.loc[no_detection & metric["frequency"].isna(), "frequency"] = 0.0
        metric["detected_deployments"] = metric["sp_binomial"].map(event_ind.groupby("sp_binomial")["deployment_key"].nunique())
        metric["eligible_deployments"] = denominator
        rows.append(metric)
    result = pd.concat(rows, ignore_index=True) if rows else base.assign(metric_event=pd.NA)
    result["selection_event"] = selection_event
    return result


def _map_rows(observations: pd.DataFrame, deployments: pd.DataFrame, projects: pd.DataFrame) -> pd.DataFrame:
    stats = observations.groupby(["project_id", "subproject_name", "deployment_key"], as_index=False).agg(
        images=("sp_binomial", "size"), species=("sp_binomial", "nunique")
    )
    mammals = observations[observations["class"].eq("Mammalia")].groupby("deployment_key")["sp_binomial"].nunique()
    birds = observations[observations["class"].eq("Aves")].groupby("deployment_key")["sp_binomial"].nunique()
    stats["mammals"] = stats["deployment_key"].map(mammals).fillna(0).astype(int)
    stats["birds"] = stats["deployment_key"].map(birds).fillna(0).astype(int)
    columns = ["project_id", "deployment_id", "deployment_key", "subproject_name", "placename", "latitude", "longitude", "Corporacion", "deployment_days"]
    result = deployments[[x for x in columns if x in deployments]].merge(stats, on=["project_id", "subproject_name", "deployment_key"], how="left")
    result[["images", "species", "mammals", "birds"]] = result[["images", "species", "mammals", "birds"]].fillna(0).astype(int)
    meta = projects[[x for x in ("project_id", "project_short_name", "project_admin", "project_admin_email") if x in projects]].drop_duplicates("project_id")
    return result.merge(meta, on="project_id", how="left")


def _build_gold(silver: dict[str, pd.DataFrame], config: PipelineConfig, progress: Progress) -> dict[str, pd.DataFrame]:
    """Precalcula los productos analíticos consumidos por el dashboard."""
    observations = silver["fact_observation"]
    deployments = silver["dim_deployment"]
    projects = silver["dim_project"]
    taxonomy = silver["dim_taxon"]
    scopes = _scope_catalog(projects, deployments)
    indicator_rows: list[dict[str, object]] = []
    species_frames: list[pd.DataFrame] = []
    activity_frames: list[pd.DataFrame] = []
    filter_rows: list[dict[str, str]] = []

    independent_by_interval = {minutes: _independent_records(observations, minutes) for minutes in config.independence_minutes}
    total_steps = max(1, len(scopes) * len(config.independence_minutes))
    step = 0
    for scope_type, scope_id in scopes:
        scope_obs = _scope_filter(observations, scope_type, scope_id)
        scope_dep = _scope_filter(deployments, scope_type, scope_id)
        events = sorted(scope_obs["subproject_name"].dropna().astype(str).unique(), reverse=True)
        for event in events:
            filter_rows.append({"scope_type": scope_type, "scope_id": scope_id, "event_id": event})
        filter_rows.append({"scope_type": scope_type, "scope_id": scope_id, "event_id": ALL})

        for minutes, independent_all in independent_by_interval.items():
            scope_ind = _scope_filter(independent_all, scope_type, scope_id)
            indicator_events = [
                (
                    event,
                    scope_obs[scope_obs["subproject_name"].astype(str).eq(event)],
                    scope_ind[scope_ind["subproject_name"].astype(str).eq(event)],
                    scope_dep[scope_dep["subproject_name"].astype(str).eq(event)],
                )
                for event in events
            ]
            indicator_events.append((ALL, scope_obs, scope_ind, scope_dep))
            for event, obs_event, ind_event, dep_event in indicator_events:
                row = _indicator_row(obs_event, ind_event, dep_event, event)
                row.update(
                    scope_type=scope_type,
                    scope_id=scope_id,
                    interval_minutes=minutes,
                )
                indicator_rows.append(row)

            for selection_event in events + [ALL]:
                obs_selection = scope_obs if selection_event == ALL else scope_obs[scope_obs["subproject_name"].astype(str).eq(selection_event)]
                ind_selection = scope_ind if selection_event == ALL else scope_ind[scope_ind["subproject_name"].astype(str).eq(selection_event)]
                dep_selection = scope_dep if selection_event == ALL else scope_dep[scope_dep["subproject_name"].astype(str).eq(selection_event)]
                metrics = _species_rows(obs_selection, ind_selection, dep_selection, taxonomy, selection_event)
                metrics["scope_type"] = scope_type
                metrics["scope_id"] = scope_id
                metrics["interval_minutes"] = minutes
                species_frames.append(metrics)

                activity = ind_selection.groupby(["sp_binomial", "subproject_name", ind_selection["photo_datetime"].dt.hour.rename("hour")]).size().rename("count").reset_index()
                totals = activity.groupby("sp_binomial")["count"].sum().sort_values(ascending=False)
                rank_map = pd.Series(np.arange(1, len(totals) + 1), index=totals.index)
                activity["ranking"] = activity["sp_binomial"].map(rank_map)
                activity["selection_event"] = selection_event
                activity["scope_type"] = scope_type
                activity["scope_id"] = scope_id
                activity["interval_minutes"] = minutes
                activity_frames.append(activity)
            step += 1
            progress("gold", 0.45 + 0.45 * step / total_steps, f"Gold: {scope_type} {scope_id} - {minutes} min")

    return {
        "filter_catalog": pd.DataFrame(filter_rows).drop_duplicates(),
        "indicator_summary": pd.DataFrame(indicator_rows),
        "species_metrics": pd.concat(species_frames, ignore_index=True),
        "activity_hour": pd.concat(activity_frames, ignore_index=True),
        "map_deployment": _map_rows(observations, deployments, projects),
    }


def _validate_products(silver: dict[str, pd.DataFrame], gold: dict[str, pd.DataFrame]) -> None:
    """Comprueba claves, rangos y cobertura antes de publicar."""
    required = {
        "fact_observation": {"project_id", "deployment_key", "subproject_name", "photo_datetime", "sp_binomial", "Corporacion"},
        "dim_deployment": {"project_id", "deployment_key", "subproject_name", "effective_start_date", "effective_end_date"},
        "species_metrics": {"scope_type", "scope_id", "selection_event", "metric_event", "interval_minutes", "occupancy", "frequency", "diurnality"},
        "indicator_summary": {
            "scope_type", "scope_id", "event_id", "interval_minutes", "images",
            "independent_records", "cameras", "camera_days",
        },
    }
    frames = {**silver, **gold}
    for name, columns in required.items():
        missing = columns.difference(frames[name].columns)
        if missing:
            raise ValueError(f"Contrato inválido en {name}: faltan {sorted(missing)}")
    if silver["fact_observation"].empty:
        raise ValueError("No quedaron observaciones válidas después del control de calidad")
    deployment_keys = set(silver["dim_deployment"]["deployment_key"].dropna())
    observation_keys = set(silver["fact_observation"]["deployment_key"].dropna())
    if not observation_keys.issubset(deployment_keys):
        raise ValueError("Integridad referencial inválida: hay observaciones sin deployment Silver")
    metrics = gold["species_metrics"]
    for column in ("occupancy", "frequency", "diurnality"):
        valid = metrics[column].dropna().between(0, 1)
        if not valid.all():
            raise ValueError(f"Dominio inválido: {column} contiene valores fuera de [0, 1]")
    allowed_intervals = set(config_value for config_value in metrics["interval_minutes"].dropna().unique())
    if allowed_intervals.difference({0, 30, 60, 1440}):
        raise ValueError("Gold contiene intervalos de independencia no admitidos")
    indicators = gold["indicator_summary"]
    indicator_intervals = set(indicators["interval_minutes"].dropna().unique())
    if indicator_intervals != allowed_intervals:
        raise ValueError("Los indicadores no contienen los mismos intervalos que las métricas de especies")
    if (indicators["independent_records"] > indicators["images"]).any():
        raise ValueError("Los registros independientes no pueden superar las observaciones incluidas")
    indicator_key = ["scope_type", "scope_id", "event_id", "interval_minutes"]
    if indicators.duplicated(indicator_key).any():
        raise ValueError("Los indicadores contienen filas duplicadas por alcance, evento e intervalo")
    unfiltered = indicators["interval_minutes"].eq(0)
    if not indicators.loc[unfiltered, "independent_records"].eq(indicators.loc[unfiltered, "images"]).all():
        raise ValueError("El intervalo sin filtro debe conservar todas las observaciones")
    ordered_indicators = indicators.sort_values(
        ["scope_type", "scope_id", "event_id", "interval_minutes"]
    )
    increases = ordered_indicators.groupby(
        ["scope_type", "scope_id", "event_id"], observed=True
    )["independent_records"].diff().gt(0)
    if increases.any():
        raise ValueError("Los registros independientes aumentan al ampliar el intervalo temporal")


def run_pipeline(config: PipelineConfig, progress: Progress | None = None) -> dict[str, object]:
    """Construye y publica una versión validada de todos los productos de datos."""
    progress = progress or _noop
    config.validate()
    reports_path = (
        config.reports_path
        if config.reports_path is not None
        else config.output_path.parent / "processing_reports"
    ).resolve()
    started = time.perf_counter()
    process = psutil.Process(os.getpid())
    memory_start = process.memory_info().rss
    memory_samples = [memory_start]
    cpu_start = process.cpu_times()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8]
    quality = QualityLog()
    progress("bronze", 0.02, "Leyendo archivos RAW")
    projects, deployments, images = _load_raw(config, quality, progress)
    memory_samples.append(process.memory_info().rss)
    raw_counts = {"projects": len(projects), "deployments": len(deployments), "images": len(images)}

    progress("silver", 0.18, "Validando y normalizando Silver")
    silver = _build_silver(projects, deployments, images, config, quality)
    memory_samples.append(process.memory_info().rss)
    progress("gold", 0.42, "Calculando productos Gold")
    gold = _build_gold(silver, config, progress)
    _validate_products(silver, gold)
    memory_samples.append(process.memory_info().rss)

    progress("publish", 0.91, "Preparando la publicación validada")
    config.output_path.parent.mkdir(parents=True, exist_ok=True)
    reports_path.parent.mkdir(parents=True, exist_ok=True)
    staging = config.output_path.parent / f".{config.output_path.name}.staging-{run_id}"
    reports_staging = reports_path.parent / f".{reports_path.name}.staging-{run_id}"
    staging.mkdir(parents=False, exist_ok=False)
    reports_staging.mkdir(parents=False, exist_ok=False)
    try:
        # Los reportes de galería pertenecen a una operación independiente de
        # la publicación analítica. Se conservan cuando existe una nueva
        # ejecución de datos para no perder la trazabilidad de las imágenes.
        for gallery_report in ("gallery_optimization.json", "gallery_optimization.csv"):
            current_report = reports_path / gallery_report
            if current_report.is_file():
                shutil.copy2(current_report, reports_staging / gallery_report)
        silver_total = max(1, len(silver))
        for index, (name, frame) in enumerate(silver.items(), start=1):
            _write_parquet(frame, staging / "validated_data" / f"{name}.parquet")
            progress("publish", 0.91 + 0.02 * index / silver_total, f"Publicando datos validados: {name}")
        gold_total = max(1, len(gold))
        for index, (name, frame) in enumerate(gold.items(), start=1):
            _write_parquet(frame, staging / "dashboard_outputs" / f"{name}.parquet")
            progress("publish", 0.93 + 0.02 * index / gold_total, f"Publicando resultados: {name}")
        issues = quality.to_frame()
        user_issues = quality.to_user_frame()
        _write_parquet(issues, reports_staging / "quality_issues.parquet")
        user_issues.to_csv(reports_staging / "quality_issues.csv", index=False, sep=";", encoding="utf-8-sig")
        rules = quality.rule_counts()
        quality_overview = quality.overview()
        quality_report = {
            "run_id": run_id,
            "start_date": config.start_date.isoformat(),
            "cutoff_date": config.cutoff_date.isoformat(),
            "counts": quality.counts(),
            "overview": quality_overview,
            "rules": rules,
        }
        (reports_staging / "quality_report.json").write_text(
            json.dumps(quality_report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        write_quality_html(
            reports_staging / "quality_report.html",
            user_issues,
            quality.counts(),
            rules,
            run_id,
            quality_overview,
        )

        summary = project_summary(silver["fact_observation"], silver["dim_deployment"], silver["dim_project"])
        summary.to_csv(reports_staging / "project_summary.csv", index=False, sep=";", encoding="utf-8-sig")

        source_files = sorted([
            config.raw_path / "projects.csv",
            config.raw_path / "deployments.csv",
            *_image_paths(config),
        ])
        data_files = sorted([*staging.glob("validated_data/*.parquet"), *staging.glob("dashboard_outputs/*.parquet")])
        elapsed_seconds = time.perf_counter() - started
        cpu_end = process.cpu_times()
        cpu_seconds = (cpu_end.user - cpu_start.user) + (cpu_end.system - cpu_start.system)
        memory_samples.append(process.memory_info().rss)
        manifest = {
            "schema_version": "2.2.0",
            "pipeline_version": __version__,
            "run_id": run_id,
            "status": "approved",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "initiative_name": config.initiative_name,
            "dashboard_title": config.dashboard_title,
            "timezone": config.timezone,
            "start_date": config.start_date.isoformat(),
            "cutoff_date": config.cutoff_date.isoformat(),
            "independence_minutes": list(config.independence_minutes),
            "occasion_window_days": OCCASION_WINDOW_DAYS,
            "raw_counts": raw_counts,
            "silver_counts": {name: len(frame) for name, frame in silver.items()},
            "gold_counts": {name: len(frame) for name, frame in gold.items()},
            "quality": quality.counts(),
            "quality_overview": quality_overview,
            "quality_gate": {
                "status": "passed",
                "blocking_contract_errors": 0,
                "policy": "Las filas inválidas se aíslan antes de validar los contratos publicables.",
            },
            "elapsed_seconds": round(elapsed_seconds, 3),
            "cpu_user_seconds": round(cpu_end.user - cpu_start.user, 3),
            "cpu_system_seconds": round(cpu_end.system - cpu_start.system, 3),
            "cpu_average_percent": round(100 * cpu_seconds / elapsed_seconds, 1) if elapsed_seconds else 0.0,
            "memory_start_mb": round(memory_start / 1024**2, 2),
            "memory_end_mb": round(process.memory_info().rss / 1024**2, 2),
            "memory_peak_sampled_mb": round(max(memory_samples) / 1024**2, 2),
            "sources": [{"file": path.name, "bytes": path.stat().st_size, "sha256": _sha256(path)} for path in source_files],
            "datasets": [
                {
                    "file": path.relative_to(staging).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": _sha256(path),
                }
                for path in data_files
            ],
        }
        (staging / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        progress("publish", 0.99, "Activando la nueva publicación")
        backup = config.output_path.parent / f".{config.output_path.name}.previous-{run_id}"
        reports_backup = reports_path.parent / f".{reports_path.name}.previous-{run_id}"
        if backup.exists():
            _remove_tree_with_retries(backup)
        if reports_backup.exists():
            _remove_tree_with_retries(reports_backup)
        output_backed_up = False
        reports_backed_up = False
        output_published = False
        reports_published = False
        try:
            if config.output_path.exists():
                _replace_with_retries(config.output_path, backup)
                output_backed_up = True
            if reports_path.exists():
                _replace_with_retries(reports_path, reports_backup)
                reports_backed_up = True
            _replace_with_retries(staging, config.output_path)
            output_published = True
            _replace_with_retries(reports_staging, reports_path)
            reports_published = True
        except Exception:
            if output_published and config.output_path.exists():
                _remove_tree_with_retries(config.output_path)
            if reports_published and reports_path.exists():
                _remove_tree_with_retries(reports_path)
            if output_backed_up and backup.exists():
                _replace_with_retries(backup, config.output_path)
            if reports_backed_up and reports_backup.exists():
                _replace_with_retries(reports_backup, reports_path)
            raise
        if backup.exists():
            _remove_tree_with_retries(backup)
        if reports_backup.exists():
            _remove_tree_with_retries(reports_backup)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        shutil.rmtree(reports_staging, ignore_errors=True)
        raise

    progress("done", 1.0, f"Publicación 2026 completada: {run_id}")
    return {
        **manifest,
        "output_path": str(config.output_path),
        "reports_path": str(reports_path),
        "quality_report_path": str(reports_path / "quality_report.html"),
        "quality_report_json_path": str(reports_path / "quality_report.json"),
        "quality_detail_path": str(reports_path / "quality_issues.csv"),
        "project_summary": summary.to_dict(orient="records"),
    }
