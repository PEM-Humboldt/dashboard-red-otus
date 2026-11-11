from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from red_otus_pipeline.packaging import (
    UpdatePackageConfig,
    create_update_package,
    inspect_update_sources,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class UpdatePackagingTests(unittest.TestCase):
    def make_sources(self, root: Path) -> tuple[Path, Path]:
        data = root / "data"
        dataset = data / "validated_data" / "example.parquet"
        dataset.parent.mkdir(parents=True, exist_ok=True)
        dataset.write_bytes(b"approved parquet content")
        manifest = {
            "status": "approved",
            "run_id": "20261109T150000Z_ab12cd34",
            "cutoff_date": "2026-11-08",
            "datasets": [
                {
                    "file": "validated_data/example.parquet",
                    "bytes": dataset.stat().st_size,
                    "sha256": sha256(dataset),
                }
            ],
        }
        (data / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

        favorites = root / "favorites"
        image = favorites / "General" / "species.jpg"
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes(b"optimized image")
        gallery_manifest = {
            "version": 1,
            "files": {
                "General/species-original.jpg": {
                    "source_sha256": "example",
                    "output": "General/species.jpg",
                }
            },
        }
        (favorites / ".gallery_manifest.json").write_text(
            json.dumps(gallery_manifest), encoding="utf-8"
        )
        return data, favorites

    def test_creates_integral_package_and_checksum(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data, favorites = self.make_sources(root)
            output = root / "packages"
            events: list[str] = []
            result = create_update_package(
                UpdatePackageConfig(data, favorites, output),
                lambda _current, _total, message: events.append(message),
            )

            package = Path(str(result["package_path"]))
            checksum = Path(str(result["checksum_path"]))
            self.assertTrue(package.is_file())
            self.assertTrue(checksum.is_file())
            self.assertEqual(result["sha256"], sha256(package))
            self.assertIn(result["sha256"], checksum.read_text(encoding="ascii"))
            self.assertEqual(result["dataset_count"], 1)
            self.assertEqual(result["favorite_count"], 1)
            self.assertFalse(result["include_spatial"])
            self.assertEqual(events[-1], "Paquete creado correctamente")

            with zipfile.ZipFile(package) as archive:
                names = set(archive.namelist())
                self.assertIn("data/manifest.json", names)
                self.assertIn("data/validated_data/example.parquet", names)
                self.assertIn("favorites/General/species.jpg", names)
                self.assertIn("RELEASE.json", names)
                self.assertIn("FILES.sha256", names)
                release = json.loads(archive.read("RELEASE.json"))
                self.assertEqual(release["components"], ["data", "favorites"])

    def test_optionally_includes_spatial_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data, favorites = self.make_sources(root)
            spatial = root / "spatial"
            spatial.mkdir()
            (spatial / "CAR_MPIO.shp").write_bytes(b"shape")
            (spatial / "CAR_MPIO.dbf").write_bytes(b"attributes")
            result = create_update_package(
                UpdatePackageConfig(data, favorites, root / "packages", spatial)
            )
            self.assertTrue(result["include_spatial"])
            self.assertEqual(result["spatial_count"], 2)
            with zipfile.ZipFile(Path(str(result["package_path"]))) as archive:
                self.assertIn("spatial/CAR_MPIO.shp", archive.namelist())
                self.assertIn("spatial/CAR_MPIO.dbf", archive.namelist())

    def test_rejects_corrupt_data_and_missing_gallery_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data, favorites = self.make_sources(root)
            config = UpdatePackageConfig(data, favorites, root / "packages")
            (data / "validated_data" / "example.parquet").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "Hash o tamaño inválido"):
                inspect_update_sources(config)

            data, favorites = self.make_sources(root)
            (favorites / "General" / "species.jpg").unlink()
            with self.assertRaisesRegex(ValueError, "Falta el archivo registrado"):
                inspect_update_sources(config)

    def test_rejects_output_inside_the_published_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data, favorites = self.make_sources(root)
            with self.assertRaisesRegex(ValueError, "fuera de los insumos"):
                UpdatePackageConfig(data, favorites, data / "packages").validate()


if __name__ == "__main__":
    unittest.main()
