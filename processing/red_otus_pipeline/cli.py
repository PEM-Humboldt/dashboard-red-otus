"""Define los parámetros y la ejecución no interactiva del pipeline."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from .config import PipelineConfig
from .engine import run_pipeline


def parser() -> argparse.ArgumentParser:
    """Construye el analizador de argumentos del procesamiento por consola."""
    command = argparse.ArgumentParser(description="Genera los datasets Silver/Gold del Dashboard Red OTUS")
    command.add_argument("--raw", type=Path, required=True)
    command.add_argument("--output", type=Path, required=True)
    command.add_argument(
        "--reports", type=Path, default=Path("processing_reports"),
        help="Carpeta independiente para informes de calidad y resúmenes operativos.",
    )
    command.add_argument("--shapefile", type=Path)
    command.add_argument("--initiative", default="Red OTUS")
    command.add_argument("--dashboard-title", default="Red OTUS")
    command.add_argument("--timezone", default="America/Bogota")
    command.add_argument("--start-date", type=date.fromisoformat, default=date(2020, 1, 1))
    command.add_argument("--cutoff", type=date.fromisoformat, default=date.today())
    command.add_argument("--intervals", nargs="+", type=int, choices=(0, 30, 60, 1440), default=(0, 30, 60, 1440))
    command.add_argument("--projects", nargs="*", default=[])
    command.add_argument(
        "--corporation-override", action="append", default=[], metavar="PROJECT_ID=CORPORATION",
        help="Reasigna manualmente una corporación; puede repetirse.",
    )
    return command


def main() -> None:
    """Valida los argumentos y ejecuta una publicación completa."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parser().parse_args()
    overrides: list[tuple[str, str]] = []
    for value in args.corporation_override:
        if "=" not in value:
            raise SystemExit("--corporation-override debe usar PROJECT_ID=CORPORATION")
        project_id, corporation = value.split("=", 1)
        overrides.append((project_id.strip(), corporation.strip()))
    config = PipelineConfig(
        raw_path=args.raw.resolve(), output_path=args.output.resolve(), reports_path=args.reports.resolve(),
        shapefile_path=args.shapefile.resolve() if args.shapefile else None,
        initiative_name=args.initiative, dashboard_title=args.dashboard_title, timezone=args.timezone,
        start_date=args.start_date, cutoff_date=args.cutoff,
        independence_minutes=tuple(args.intervals), selected_projects=tuple(args.projects),
        corporation_overrides=tuple(overrides),
    )
    result = run_pipeline(config, lambda stage, value, message: print(f"[{value:6.1%}] {stage}: {message}", flush=True))
    overview = result["quality_overview"]
    print(
        "\nPublicación completada"
        f"\n  run_id: {result['run_id']}"
        f"\n  duración: {result['elapsed_seconds']:.3f} s"
        f"\n  observaciones Silver: {result['silver_counts']['fact_observation']}"
        f"\n  tipos de situación de calidad: {overview['situation_types']}"
        f"\n  registros afectados: {overview['affected_records']}"
        f"\n  datos del dashboard: {config.output_path}"
        f"\n  informes del procesamiento: {result['reports_path']}"
    )


if __name__ == "__main__":
    main()
