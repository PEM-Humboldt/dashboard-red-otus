"""Comprueba la integridad y coherencia de una publicación terminada."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_release(output_path: Path) -> dict[str, object]:
    """Valida archivos, huellas, relaciones y productos analíticos publicados."""
    release = output_path.resolve()
    manifest = json.loads((release / "manifest.json").read_text(encoding="utf-8"))
    failures: list[str] = []

    if manifest.get("status") != "approved":
        failures.append("La publicación activa no está aprobada")
    for dataset in manifest.get("datasets", []):
        path = release / dataset["file"]
        if not path.exists():
            failures.append(f"Falta {dataset['file']}")
        elif path.stat().st_size != dataset["bytes"] or _sha256(path) != dataset["sha256"]:
            failures.append(f"Hash o tamaño inválido en {dataset['file']}")

    observations = pd.read_parquet(release / "validated_data" / "fact_observation.parquet")
    deployments = pd.read_parquet(release / "validated_data" / "dim_deployment.parquet")
    metrics = pd.read_parquet(release / "dashboard_outputs" / "species_metrics.parquet")
    indicators = pd.read_parquet(release / "dashboard_outputs" / "indicator_summary.parquet")
    activity = pd.read_parquet(release / "dashboard_outputs" / "activity_hour.parquet")

    if deployments["deployment_key"].duplicated().any():
        failures.append("dim_deployment contiene claves duplicadas")
    if not set(observations["deployment_key"]).issubset(set(deployments["deployment_key"])):
        failures.append("Hay observaciones sin deployment")
    expected_intervals = set(int(value) for value in manifest.get("independence_minutes", []))
    actual_intervals = set(metrics["interval_minutes"].dropna().astype(int))
    if actual_intervals != expected_intervals:
        failures.append("Los intervalos calculados no coinciden con los solicitados")
    indicator_intervals = set(indicators["interval_minutes"].dropna().astype(int))
    if indicator_intervals != expected_intervals:
        failures.append("Los indicadores no contienen todos los intervalos solicitados")
    if (indicators["independent_records"] > indicators["images"]).any():
        failures.append("Hay indicadores con más registros independientes que observaciones")
    indicator_key = ["scope_type", "scope_id", "event_id", "interval_minutes"]
    if indicators.duplicated(indicator_key).any():
        failures.append("Hay indicadores duplicados por alcance, evento e intervalo")
    unfiltered = indicators["interval_minutes"].eq(0)
    if not indicators.loc[unfiltered, "independent_records"].eq(indicators.loc[unfiltered, "images"]).all():
        failures.append("El intervalo sin filtro no conserva todas las observaciones")
    ordered_indicators = indicators.sort_values(
        ["scope_type", "scope_id", "event_id", "interval_minutes"]
    )
    increases = ordered_indicators.groupby(
        ["scope_type", "scope_id", "event_id"], observed=True
    )["independent_records"].diff().gt(0)
    if increases.any():
        failures.append("Los registros independientes aumentan al ampliar el intervalo")
    for column in ("occupancy", "frequency", "diurnality"):
        if not metrics[column].dropna().between(0, 1).all():
            failures.append(f"{column} contiene valores fuera de [0, 1]")

    project_profile = (
        observations.groupby("project_id")
        .agg(rows=("project_id", "size"), events=("subproject_name", "nunique"))
        .sort_values(["rows", "events"], ascending=False)
    )
    corporation_profile = (
        observations.dropna(subset=["Corporacion"])
        .groupby("Corporacion")
        .agg(rows=("Corporacion", "size"), events=("subproject_name", "nunique"))
        .sort_values(["rows", "events"], ascending=False)
    )
    if project_profile.empty:
        failures.append("No existen proyectos publicables")
    if corporation_profile.empty:
        failures.append("No existen corporaciones asignadas")

    cases: list[dict[str, object]] = []
    candidates = [("global", "ALL")]
    if not project_profile.empty:
        candidates.append(("project", str(project_profile.index[0])))
    if not corporation_profile.empty:
        candidates.append(("corporation", str(corporation_profile.index[0])))
    for scope_type, scope_id in candidates:
        for selection_event in ("ALL",):
            metric_count = len(metrics[(metrics.scope_type == scope_type) & (metrics.scope_id == scope_id) & (metrics.selection_event == selection_event)])
            indicator_count = len(indicators[
                (indicators.scope_type == scope_type)
                & (indicators.scope_id == scope_id)
                & (indicators.interval_minutes.isin(expected_intervals))
            ])
            activity_count = len(activity[(activity.scope_type == scope_type) & (activity.scope_id == scope_id) & (activity.selection_event == selection_event)])
            cases.append({
                "scope_type": scope_type, "scope_id": scope_id, "selection_event": selection_event,
                "species_rows": metric_count, "indicator_rows": indicator_count, "activity_rows": activity_count,
            })
            if min(metric_count, indicator_count, activity_count) == 0:
                failures.append(f"Productos Gold incompletos para {scope_type}:{scope_id}")

    return {
        "status": "passed" if not failures else "failed",
        "run_id": manifest.get("run_id"),
        "failures": failures,
        "counts": {
            "observations": len(observations), "deployments": len(deployments),
            "projects": observations["project_id"].nunique(),
            "events": observations["subproject_name"].nunique(),
            "corporations": observations["Corporacion"].nunique(),
            "species": observations["sp_binomial"].nunique(),
        },
        "representative_project": None if project_profile.empty else str(project_profile.index[0]),
        "representative_corporation": None if corporation_profile.empty else str(corporation_profile.index[0]),
        "cases": cases,
    }
