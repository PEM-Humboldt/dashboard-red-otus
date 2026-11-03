"""Centraliza la configuración y las reglas previas a cada ejecución."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


@dataclass(frozen=True)
class PipelineConfig:
    """Parámetros inmutables que controlan una ejecución del pipeline."""
    raw_path: Path
    output_path: Path
    reports_path: Path | None = None
    shapefile_path: Path | None = None
    initiative_name: str = "Red OTUS"
    dashboard_title: str = "Red OTUS"
    timezone: str = "America/Bogota"
    start_date: date = field(default_factory=lambda: date(2020, 1, 1))
    cutoff_date: date = field(default_factory=date.today)
    independence_minutes: tuple[int, ...] = (0, 30, 60, 1440)
    minimum_event_year: int = 2020
    event_year_tolerance_before: int = 1
    event_year_tolerance_after: int = 1
    selected_projects: tuple[str, ...] = ()
    corporation_overrides: tuple[tuple[str, str], ...] = ()

    def validate(self) -> None:
        """Comprueba rutas, fechas, intervalos y reasignaciones."""
        if not self.raw_path.is_dir():
            raise ValueError(f"La carpeta RAW no existe: {self.raw_path}")
        if not self.initiative_name.strip():
            raise ValueError("El nombre de la iniciativa es obligatorio")
        if not self.dashboard_title.strip():
            raise ValueError("El texto del título del dashboard es obligatorio")
        intervals = tuple(sorted(set(self.independence_minutes)))
        if not intervals or set(intervals).difference({0, 30, 60, 1440}):
            raise ValueError("Seleccione al menos un intervalo válido: sin filtro, 30 minutos, 1 hora o 24 horas")
        if self.start_date > self.cutoff_date:
            raise ValueError("La fecha inicial no puede ser posterior a la fecha final")
        if self.shapefile_path is not None and not self.shapefile_path.is_file():
            raise ValueError(f"El shapefile no existe: {self.shapefile_path}")
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Zona horaria no válida: {self.timezone}") from exc
        raw = self.raw_path.resolve()
        output = self.output_path.resolve()
        reports = self.reports_path.resolve() if self.reports_path is not None else None
        if output == raw or output.is_relative_to(raw):
            raise ValueError("La salida no puede ubicarse dentro de la carpeta RAW")
        if reports is not None:
            if reports == raw or reports.is_relative_to(raw):
                raise ValueError("Los informes no pueden ubicarse dentro de la carpeta RAW")
            if reports == output or reports.is_relative_to(output) or output.is_relative_to(reports):
                raise ValueError("Los informes y los datos del dashboard deben usar carpetas independientes")

        project_ids = [project_id for project_id, _ in self.corporation_overrides]
        if len(project_ids) != len(set(project_ids)):
            raise ValueError("Un proyecto no puede tener más de una reasignación manual de corporación")
        if any(not project_id.strip() or not corporation.strip() for project_id, corporation in self.corporation_overrides):
            raise ValueError("Las reasignaciones manuales de corporación deben tener proyecto y corporación")
