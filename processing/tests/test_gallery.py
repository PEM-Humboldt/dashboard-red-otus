from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from red_otus_pipeline.gallery import GalleryCancelled, GalleryConfig, optimize_gallery


class GalleryOptimizationTests(unittest.TestCase):
    def test_optimizes_images_preserves_structure_and_skips_unchanged_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "originals"
            output = root / "published"
            reports = root / "reports"
            project = source / "2002517"
            general = source / "General"
            project.mkdir(parents=True)
            general.mkdir(parents=True)

            jpeg_path = project / "camera.jpg"
            Image.new("RGB", (2400, 1200), (30, 90, 40)).save(jpeg_path, quality=98)
            opaque_png = general / "landscape.png"
            Image.new("RGB", (1800, 900), (80, 120, 160)).save(opaque_png)
            alpha_png = general / "overlay.png"
            Image.new("RGBA", (900, 1800), (40, 80, 120, 100)).save(alpha_png)
            root_level = source / "ignored.jpg"
            Image.new("RGB", (100, 100), "red").save(root_level)

            config = GalleryConfig(source, output, reports)
            result = optimize_gallery(config)
            summary = result["summary"]
            self.assertEqual(summary["found"], 3)
            self.assertEqual(summary["processed"], 3)
            self.assertEqual(summary["failed"], 0)
            self.assertEqual(summary["skipped"], 0)
            self.assertTrue(summary["published"])

            published_jpeg = output / "2002517" / "camera.jpg"
            converted_png = output / "General" / "landscape.jpg"
            published_alpha = output / "General" / "overlay.png"
            self.assertTrue(published_jpeg.is_file())
            self.assertTrue(converted_png.is_file())
            self.assertTrue(published_alpha.is_file())
            self.assertFalse((output / "ignored.jpg").exists())
            with Image.open(published_jpeg) as image:
                self.assertEqual(image.size, (1600, 800))
            with Image.open(converted_png) as image:
                self.assertEqual(image.size, (1600, 800))
            with Image.open(published_alpha) as image:
                self.assertEqual(image.size, (800, 1600))
                self.assertEqual(image.mode, "RGBA")
            with Image.open(jpeg_path) as image:
                self.assertEqual(image.size, (2400, 1200))

            self.assertTrue((reports / "gallery_optimization.json").is_file())
            self.assertTrue((reports / "gallery_optimization.csv").is_file())
            manifest = json.loads((output / ".gallery_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["settings"]["max_dimension"], 1600)
            self.assertEqual(manifest["settings"]["jpeg_quality"], 82)

            second = optimize_gallery(config)
            self.assertEqual(second["summary"]["processed"], 0)
            self.assertEqual(second["summary"]["skipped"], 3)
            self.assertEqual(second["summary"]["failed"], 0)
            self.assertTrue(second["summary"]["published"])

    def test_errors_cancellation_and_removed_sources_preserve_consistency(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "originals"
            project = source / "2002517"
            project.mkdir(parents=True)
            output = root / "published"
            reports = root / "reports"
            first = project / "first.jpg"
            second = project / "second.jpg"
            Image.new("RGB", (2000, 1000), "green").save(first, quality=96)
            Image.new("RGB", (1200, 800), "blue").save(second, quality=96)
            config = GalleryConfig(source, output, reports)

            initial = optimize_gallery(config)
            self.assertTrue(initial["summary"]["published"])
            published_first = output / "2002517" / "first.jpg"
            previous_bytes = published_first.read_bytes()
            previous_manifest = (output / ".gallery_manifest.json").read_text(encoding="utf-8")

            Image.new("RGB", (2000, 1000), "red").save(first, quality=96)
            (project / "broken.jpg").write_bytes(b"not an image")
            rejected = optimize_gallery(config)
            self.assertFalse(rejected["summary"]["published"])
            self.assertEqual(rejected["summary"]["failed"], 1)
            self.assertEqual(published_first.read_bytes(), previous_bytes)
            self.assertEqual(
                (output / ".gallery_manifest.json").read_text(encoding="utf-8"),
                previous_manifest,
            )
            self.assertFalse((output / "2002517" / "broken.jpg").exists())

            (project / "broken.jpg").unlink()

            def cancel_after_first(current: int, _total: int, _message: str) -> None:
                if current >= 1:
                    raise GalleryCancelled()

            with self.assertRaises(GalleryCancelled):
                optimize_gallery(config, cancel_after_first)
            self.assertEqual(published_first.read_bytes(), previous_bytes)

            second.unlink()
            completed = optimize_gallery(config)
            self.assertTrue(completed["summary"]["published"])
            self.assertNotEqual(published_first.read_bytes(), previous_bytes)
            self.assertFalse((output / "2002517" / "second.jpg").exists())

    def test_rejects_nested_or_empty_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "originals"
            source.mkdir()
            output = source / "published"
            with self.assertRaisesRegex(ValueError, "independientes"):
                GalleryConfig(source, output, root / "reports").validate()

            output = root / "published"
            with self.assertRaisesRegex(ValueError, "No se encontraron imágenes"):
                optimize_gallery(GalleryConfig(source, output, root / "reports"))


if __name__ == "__main__":
    unittest.main()
