"""Pruebas de cálculo, calidad, rutas y publicación transaccional."""

from __future__ import annotations

import json
import tempfile
import unittest
import sys
from unittest.mock import patch
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from red_otus_pipeline.config import PipelineConfig
from red_otus_pipeline.engine import _hill, _independent_records, _replace_with_retries, run_pipeline
from red_otus_pipeline.gui import (
    PipelineWorker,
    ProcessingCancelled,
    ScrollSafeTabBar,
    _format_duration,
    _project_root,
    _resources_dir,
)
from red_otus_pipeline.quality import QualityLog
from red_otus_pipeline.reports import write_quality_html
from red_otus_pipeline.validation import validate_release


class CalculationTests(unittest.TestCase):
    def test_project_layout_paths_are_resolved_from_source(self) -> None:
        root = _project_root()
        self.assertTrue((root / "processing" / "input" / "raw").is_dir())
        self.assertTrue((root / "dashboard" / "data").is_dir())
        self.assertTrue((root / "processing" / "input" / "spatial" / "CAR_MPIO.shp").is_file())
        self.assertTrue((_resources_dir() / "styles.qss").is_file())
        self.assertTrue((_resources_dir() / "red_otus.svg").is_file())
        self.assertTrue((_resources_dir() / "combo_arrow.svg").is_file())

    def test_independence_compares_against_last_retained_record(self) -> None:
        frame = pd.DataFrame(
            {
                "project_id": ["1"] * 3,
                "subproject_name": ["2025_1"] * 3,
                "deployment_id": ["A"] * 3,
                "deployment_key": ["1||2025_1||A"] * 3,
                "sp_binomial": ["Puma concolor"] * 3,
                "photo_datetime": pd.to_datetime(
                    ["2025-01-01 00:00:00", "2025-01-01 00:20:00", "2025-01-01 00:40:00"]
                ),
            }
        )
        result = _independent_records(frame, 30)
        self.assertEqual(result["photo_datetime"].dt.minute.tolist(), [0, 40])

    def test_hill_numbers(self) -> None:
        species = pd.Series(["A", "A", "B", "B"])
        self.assertEqual(_hill(species, 0), 2.0)
        self.assertAlmostEqual(_hill(species, 1), 2.0)
        self.assertAlmostEqual(_hill(species, 2), 2.0)

    def test_zero_interval_keeps_all_records(self) -> None:
        frame = pd.DataFrame(
            {
                "project_id": ["1"] * 3, "subproject_name": ["2025_1"] * 3,
                "deployment_id": ["A"] * 3, "sp_binomial": ["Puma concolor"] * 3,
                "photo_datetime": pd.to_datetime(["2025-01-01 00:00:00", "2025-01-01 00:01:00", "2025-01-01 00:02:00"]),
            }
        )
        self.assertEqual(len(_independent_records(frame, 0)), 3)

    def test_duration_uses_clock_format(self) -> None:
        self.assertEqual(_format_duration(172.34), "00:02:52")
        self.assertEqual(_format_duration(3661), "01:01:01")

    def test_worker_cancellation_is_cooperative(self) -> None:
        worker = PipelineWorker(PipelineConfig(raw_path=Path("raw"), output_path=Path("output")))
        worker.cancel()
        with self.assertRaises(ProcessingCancelled):
            worker._progress("bronze", 0.1, "Lectura")

    def test_publication_retries_transient_windows_lock(self) -> None:
        with patch("red_otus_pipeline.engine.os.replace", side_effect=[PermissionError(), PermissionError(), None]) as replace:
            with patch("red_otus_pipeline.engine.time.sleep") as sleep:
                _replace_with_retries(Path("source"), Path("target"), attempts=3)
        self.assertEqual(replace.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    def test_mouse_wheel_does_not_change_result_tabs(self) -> None:
        state = {"ignored": False}
        event = type("WheelEvent", (), {"ignore": lambda _self: state.__setitem__("ignored", True)})()
        ScrollSafeTabBar.wheelEvent(object(), event)
        self.assertTrue(state["ignored"])

    def test_quality_report_distinguishes_statuses_and_supports_filtering(self) -> None:
        quality = QualityLog()
        quality.add(
            stage="bronze", severity="error", rule="TIMESTAMP_INVALID", entity_type="row",
            entity_id="i1", field="timestamp", original_value="", action="excluded_invalid_timestamp",
            source_file="images.csv", source_row=2,
        )
        quality.add(
            stage="silver", severity="warning", rule="DEPLOYMENT_EVENT_AMBIGUOUS", entity_type="row",
            entity_id="i2", field="deployment_id", original_value="A", action="resolved_by_date",
            source_file="images.csv", source_row=3,
        )
        overview = quality.overview()
        self.assertEqual(overview["situation_types"], 2)
        self.assertEqual(overview["situations_by_status"]["Excluido por inconsistencia"], 1)
        self.assertEqual(overview["situations_by_status"]["Resuelto automáticamente"], 1)
        timestamp_rule = next(item for item in quality.rule_counts() if item["rule"] == "TIMESTAMP_INVALID")
        self.assertIn("timestamp de la observación está vacío", timestamp_rule["description"])
        self.assertIn("asignarse a un evento", timestamp_rule["result"])
        with tempfile.TemporaryDirectory() as temporary:
            report = Path(temporary) / "quality.html"
            write_quality_html(
                report, quality.to_user_frame(), quality.counts(), quality.rule_counts(), "test-run", overview
            )
            content = report.read_text(encoding="utf-8")
            self.assertIn("Filtrar por estado y situación", content)
            self.assertIn("Buscar en la muestra visible", content)
            self.assertIn("detalle completo contiene", content)
            self.assertIn("images.csv, fila 2", content)
            self.assertIn("badge excluded'>Excluido por inconsistencia", content)
            self.assertIn("badge resolved", content)


class PublicationTests(unittest.TestCase):
    def test_atomic_publication_and_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw = root / "raw"
            output = root / "output"
            raw.mkdir()
            pd.DataFrame(
                [{
                    "project_id": "1", "project_short_name": "Proyecto", "project_name": "Proyecto",
                    "project_admin": "Admin", "project_admin_email": "admin@example.org",
                    "project_admin_organization": "Entidad", "initiative_id": "I1",
                }]
            ).to_csv(raw / "projects.csv", index=False)
            pd.DataFrame(
                [{
                    "project_id": "1", "deployment_id": "A", "placename": "Sitio",
                    "longitude": -74.0, "latitude": 4.0, "start_date": "2025-01-01",
                    "end_date": "2025-01-20", "subproject_name": "2025_1",
                }, {
                    "project_id": "1", "deployment_id": "B", "placename": "Sitio sin evento",
                    "longitude": -74.1, "latitude": 4.1, "start_date": "2025-01-01",
                    "end_date": "2025-01-20", "subproject_name": "",
                }]
            ).to_csv(raw / "deployments.csv", index=False)
            pd.DataFrame(
                [
                    {
                        "project_id": "1", "deployment_id": "A", "image_id": "i0",
                        "timestamp": "2024-12-31 07:00:00", "wi_taxon_id": "t1",
                        "class": "Mammalia", "order": "Carnivora", "family": "Felidae",
                        "genus": "Puma", "species": "concolor", "common_name": "Puma",
                    },
                    {
                        "project_id": "1", "deployment_id": "A", "image_id": "i1",
                        "timestamp": "2025-01-01 07:00:00", "wi_taxon_id": "t1",
                        "class": "Mammalia", "order": "Carnivora", "family": "Felidae",
                        "genus": "Puma", "species": "concolor", "common_name": "Puma",
                    },
                    {
                        "project_id": "1", "deployment_id": "A", "image_id": "i1b",
                        "timestamp": "2025-01-01 07:05:00", "wi_taxon_id": "t1",
                        "class": "Mammalia", "order": "Carnivora", "family": "Felidae",
                        "genus": "Puma", "species": "concolor", "common_name": "Puma",
                    },
                    {
                        "project_id": "1", "deployment_id": "A", "image_id": "i2",
                        "timestamp": "2025-01-11 19:00:00", "wi_taxon_id": "t1",
                        "class": "Mammalia", "order": "Carnivora", "family": "Felidae",
                        "genus": "Puma", "species": "concolor", "common_name": "Puma",
                    },
                    {
                        "project_id": "1", "deployment_id": "B", "image_id": "i3",
                        "timestamp": "2025-01-12 10:00:00", "wi_taxon_id": "t1",
                        "class": "Mammalia", "order": "Carnivora", "family": "Felidae",
                        "genus": "Puma", "species": "concolor", "common_name": "Puma",
                    },
                    {
                        "project_id": "1", "deployment_id": "Z", "image_id": "i4",
                        "timestamp": "2025-01-12 11:00:00", "wi_taxon_id": "t1",
                        "class": "Mammalia", "order": "Carnivora", "family": "Felidae",
                        "genus": "Puma", "species": "concolor", "common_name": "Puma",
                    },
                ]
            ).to_csv(raw / "images_1.csv", index=False)

            progress_stages: list[str] = []
            reports = root / "processing_reports"
            reports.mkdir()
            (reports / "gallery_optimization.json").write_text('{"status":"preserved"}', encoding="utf-8")
            (reports / "gallery_optimization.csv").write_text("status\npreserved\n", encoding="utf-8")
            result = run_pipeline(
                PipelineConfig(
                    raw_path=raw, output_path=output, reports_path=reports,
                    start_date=date(2025, 1, 1), cutoff_date=date(2026, 9, 4),
                    dashboard_title="Iniciativa de prueba",
                    corporation_overrides=(("1", "CORPORACIÓN DE PRUEBA"),),
                ),
                lambda stage, _value, _message: progress_stages.append(stage),
            )
            metrics = pd.read_parquet(output / "dashboard_outputs" / "species_metrics.parquet")
            indicators = pd.read_parquet(output / "dashboard_outputs" / "indicator_summary.parquet")
            projects = pd.read_parquet(output / "validated_data" / "dim_project.parquet")
            row = metrics[
                (metrics["scope_type"] == "project")
                & (metrics["scope_id"] == "1")
                & (metrics["selection_event"] == "2025_1")
                & (metrics["interval_minutes"] == 30)
            ].iloc[0]
            self.assertEqual(result["status"], "approved")
            self.assertAlmostEqual(row["occupancy"], 1.0)
            # El despliegue cubre 20 días: con ocasiones semanales existen
            # tres ocasiones disponibles y detecciones en dos de ellas.
            self.assertEqual(int(row["total_occasions"]), 3)
            self.assertEqual(int(row["detected_occasions"]), 2)
            self.assertAlmostEqual(row["frequency"], 2 / 3)
            self.assertAlmostEqual(row["diurnality"], 0.5)
            self.assertEqual(set(metrics["interval_minutes"].astype(int)), {0, 30, 60, 1440})
            self.assertEqual(set(indicators["interval_minutes"].astype(int)), {0, 30, 60, 1440})
            indicator_rows = indicators[
                (indicators["scope_type"] == "project")
                & (indicators["scope_id"] == "1")
                & (indicators["event_id"] == "2025_1")
            ].set_index("interval_minutes")
            self.assertEqual(int(indicator_rows.loc[0, "images"]), 3)
            self.assertEqual(int(indicator_rows.loc[0, "independent_records"]), 3)
            self.assertEqual(int(indicator_rows.loc[30, "independent_records"]), 2)
            self.assertTrue((reports / "quality_report.json").exists())
            self.assertTrue((reports / "quality_report.html").exists())
            self.assertTrue((reports / "quality_issues.csv").exists())
            self.assertEqual(
                (reports / "gallery_optimization.json").read_text(encoding="utf-8"),
                '{"status":"preserved"}',
            )
            self.assertEqual(
                (reports / "gallery_optimization.csv").read_text(encoding="utf-8"),
                "status\npreserved\n",
            )
            self.assertFalse((output / "quality_report.json").exists())
            self.assertFalse((output / "quality_report.html").exists())
            self.assertFalse((output / "quality_issues.csv").exists())
            self.assertFalse((output / "releases").exists())
            self.assertTrue((output / ".gitkeep").is_file())
            self.assertTrue((reports / ".gitkeep").is_file())
            self.assertEqual(result["dashboard_title"], "Iniciativa de prueba")
            self.assertEqual(result["occasion_window_days"], 7)
            self.assertEqual(projects.loc[0, "Corporacion"], "CORPORACIÓN DE PRUEBA")
            self.assertEqual(result["raw_counts"]["images"], 6)
            self.assertEqual(result["silver_counts"]["fact_observation"], 3)
            report_data = json.loads((reports / "quality_report.json").read_text(encoding="utf-8"))
            report_rules = {item["rule"]: item for item in report_data["rules"]}
            self.assertEqual(report_rules["EVENT_NAME_MISSING"]["count"], 1)
            self.assertIn("subproject_name", report_rules["EVENT_NAME_MISSING"]["description"])
            self.assertEqual(report_rules["DEPLOYMENT_ORPHAN"]["count"], 1)
            self.assertGreaterEqual(result["quality_overview"]["situation_types"], 1)
            self.assertEqual(validate_release(output)["status"], "passed")
            self.assertIn("publish", progress_stages)

            published_manifest = (output / "manifest.json").read_text(encoding="utf-8")

            def cancel_before_publication(stage: str, _value: float, _message: str) -> None:
                if stage == "publish":
                    raise ProcessingCancelled()

            with self.assertRaises(ProcessingCancelled):
                run_pipeline(
                    PipelineConfig(
                        raw_path=raw, output_path=output, reports_path=reports,
                        start_date=date(2025, 1, 1), cutoff_date=date(2026, 9, 4),
                        dashboard_title="Ejecución cancelada",
                    ),
                    cancel_before_publication,
                )
            self.assertEqual((output / "manifest.json").read_text(encoding="utf-8"), published_manifest)


if __name__ == "__main__":
    unittest.main()
