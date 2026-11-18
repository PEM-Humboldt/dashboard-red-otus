"""Inspecciona los archivos de entrada antes de habilitar el procesamiento."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import geopandas as gpd
import pandas as pd


@dataclass(frozen=True)
class InputInspection:
    """Resultado de la validación preliminar de los insumos."""

    projects: pd.DataFrame
    corporations: tuple[str, ...]
    image_files: int
    raw_file_counts: Mapping[str, int]
    raw_record_counts: Mapping[str, int]
    gallery_image_files: int
    gallery_general_images: int
    gallery_project_folders: int
    gallery_projects_with_images: int
    gallery_projects_without_images: int
    warnings: tuple[str, ...]


def _mode_text(values: pd.Series) -> str:
    clean = values.dropna().astype(str).str.strip()
    clean = clean[clean.ne("")]
    if clean.empty:
        return "Sin asignación"
    counts = clean.value_counts()
    return sorted(counts[counts.eq(counts.max())].index)[0]


def _csv_record_count(path: Path) -> int:
    """Cuenta registros CSV respetando campos entrecomillados y saltos de línea."""
    if not path.is_file():
        return 0
    return sum(len(chunk) for chunk in pd.read_csv(path, chunksize=100_000, low_memory=False))


def _gallery_inventory(gallery_path: Path | None, project_ids: set[str]) -> dict[str, int]:
    """Distingue fotografías, carpetas de proyecto y la carpeta General."""
    empty = {
        "gallery_image_files": 0,
        "gallery_general_images": 0,
        "gallery_project_folders": 0,
        "gallery_projects_with_images": 0,
        "gallery_projects_without_images": len(project_ids),
    }
    if gallery_path is None or not gallery_path.is_dir():
        return empty

    extensions = {".jpg", ".jpeg", ".png"}
    folders = [path for path in gallery_path.iterdir() if path.is_dir()]
    image_counts = {
        folder.name: sum(
            1
            for path in folder.iterdir()
            if path.is_file() and path.suffix.casefold() in extensions
        )
        for folder in folders
    }
    project_folders = {
        name for name, count in image_counts.items()
        if name.casefold() != "general" and count > 0
    }
    projects_with_images = project_ids.intersection(project_folders)
    return {
        "gallery_image_files": sum(image_counts.values()),
        "gallery_general_images": next(
            (count for name, count in image_counts.items() if name.casefold() == "general"), 0
        ),
        "gallery_project_folders": len(project_folders),
        "gallery_projects_with_images": len(projects_with_images),
        "gallery_projects_without_images": len(project_ids.difference(projects_with_images)),
    }


def inspect_input(
    raw_path: Path,
    shapefile_path: Path | None,
    gallery_path: Path | None = None,
) -> InputInspection:
    """Valida insumos mínimos y construye el catálogo inicial de proyectos."""
    projects_path = raw_path / "projects.csv"
    deployments_path = raw_path / "deployments.csv"
    image_paths = sorted(raw_path.glob("images_*.csv"))
    missing = [str(path) for path in (projects_path, deployments_path) if not path.is_file()]
    if missing or not image_paths:
        raise ValueError(f"Faltan archivos requeridos: {', '.join(missing or ['images_*.csv'])}")

    projects = pd.read_csv(projects_path, low_memory=False, dtype={"project_id": "string"})
    deployments = pd.read_csv(
        deployments_path,
        low_memory=False,
        dtype={"project_id": "string", "deployment_id": "string"},
    )
    if "project_id" not in projects or "project_id" not in deployments:
        raise ValueError("projects.csv y deployments.csv deben contener la columna project_id")
    projects["project_id"] = projects["project_id"].astype("string").str.strip()
    deployments["project_id"] = deployments["project_id"].astype("string").str.strip()

    name_column = next(
        (column for column in ("project_short_name", "project_name", "name") if column in projects),
        None,
    )
    project_catalog = projects[["project_id"]].drop_duplicates().copy()
    project_catalog["project_name"] = (
        projects.drop_duplicates("project_id").set_index("project_id")[name_column].reindex(project_catalog["project_id"]).to_numpy()
        if name_column else "Sin nombre"
    )
    stats = deployments.groupby("project_id", as_index=False).agg(
        deployments=("deployment_id", "nunique"),
        events=("subproject_name", "nunique") if "subproject_name" in deployments else ("deployment_id", "size"),
    )
    project_catalog = project_catalog.merge(stats, on="project_id", how="left")
    project_catalog[["deployments", "events"]] = project_catalog[["deployments", "events"]].fillna(0).astype(int)
    available_image_ids = {path.stem.removeprefix("images_") for path in image_paths}
    project_catalog["has_images"] = project_catalog["project_id"].isin(available_image_ids)
    project_catalog["corporation"] = "Sin asignación"

    warnings: list[str] = []
    corporations: tuple[str, ...] = ()
    if shapefile_path is None or not shapefile_path.is_file():
        warnings.append("No se proporcionó un archivo espacial válido; no se precargaron corporaciones.")
    elif not {"longitude", "latitude"}.issubset(deployments.columns):
        warnings.append("deployments.csv no contiene longitude y latitude; no se precargaron corporaciones.")
    else:
        polygons = gpd.read_file(shapefile_path).to_crs(4326)
        corporation_column = next(
            (column for column in ("NOMBRE_CAR", "CAR", "NOMBRE", "Nombre", "corporacion") if column in polygons),
            None,
        )
        if corporation_column is None:
            warnings.append("El archivo espacial no contiene una columna reconocible para las corporaciones.")
        else:
            corporations = tuple(sorted(polygons[corporation_column].dropna().astype(str).str.strip().unique()))
            points_source = deployments.copy()
            points_source["longitude"] = pd.to_numeric(points_source["longitude"], errors="coerce")
            points_source["latitude"] = pd.to_numeric(points_source["latitude"], errors="coerce")
            valid = points_source["longitude"].between(-180, 180) & points_source["latitude"].between(-90, 90)
            if valid.any():
                points = gpd.GeoDataFrame(
                    points_source.loc[valid, ["project_id", "deployment_id"]],
                    geometry=gpd.points_from_xy(
                        points_source.loc[valid, "longitude"], points_source.loc[valid, "latitude"]
                    ),
                    crs=4326,
                )
                joined = gpd.sjoin(points, polygons[[corporation_column, "geometry"]], how="left", predicate="within")
                assignment = joined.groupby("project_id")[corporation_column].agg(_mode_text)
                project_catalog["corporation"] = project_catalog["project_id"].map(assignment).fillna("Sin asignación")

    project_catalog = project_catalog.sort_values(["project_name", "project_id"]).reset_index(drop=True)
    optional_csv = {
        "projects.csv": projects_path,
        "deployments.csv": deployments_path,
        "cameras.csv": raw_path / "cameras.csv",
        "sequences.csv": raw_path / "sequences.csv",
    }
    raw_file_counts = {
        **{name: int(path.is_file()) for name, path in optional_csv.items()},
        "images_*.csv": len(image_paths),
    }
    raw_record_counts = {
        "projects.csv": len(projects),
        "deployments.csv": len(deployments),
        "cameras.csv": _csv_record_count(optional_csv["cameras.csv"]),
        "sequences.csv": _csv_record_count(optional_csv["sequences.csv"]),
        "images_*.csv": sum(_csv_record_count(path) for path in image_paths),
    }
    project_ids = set(project_catalog["project_id"].dropna().astype(str))
    gallery = _gallery_inventory(gallery_path, project_ids)
    if gallery_path is None or not gallery_path.is_dir():
        warnings.append("No se encontró una carpeta válida de fotografías originales para inventariar la galería.")
    return InputInspection(
        project_catalog,
        corporations,
        len(image_paths),
        raw_file_counts,
        raw_record_counts,
        gallery["gallery_image_files"],
        gallery["gallery_general_images"],
        gallery["gallery_project_folders"],
        gallery["gallery_projects_with_images"],
        gallery["gallery_projects_without_images"],
        tuple(warnings),
    )
