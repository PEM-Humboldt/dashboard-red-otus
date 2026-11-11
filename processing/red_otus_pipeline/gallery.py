"""Optimización y publicación segura de fotografías para la galería."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from PIL import Image, ImageOps


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MANIFEST_NAME = ".gallery_manifest.json"
ProgressCallback = Callable[[int, int, str], None]


class GalleryCancelled(Exception):
    """Interrumpe la preparación antes de activar una galería incompleta."""


@dataclass(frozen=True)
class GalleryConfig:
    """Parámetros estables para preparar las imágenes publicadas."""

    source_root: Path
    output_root: Path
    reports_root: Path
    max_dimension: int = 1600
    jpeg_quality: int = 82

    def validate(self) -> None:
        """Comprueba rutas y parámetros de optimización."""
        source = self.source_root.expanduser().resolve()
        output = self.output_root.expanduser().resolve()
        if not source.is_dir():
            raise ValueError(f"No existe la carpeta de imágenes originales: {source}")
        if source == output or source in output.parents or output in source.parents:
            raise ValueError("La carpeta de originales y la carpeta publicada deben ser independientes")
        if self.max_dimension < 320:
            raise ValueError("La dimensión máxima debe ser de al menos 320 píxeles")
        if not 40 <= self.jpeg_quality <= 95:
            raise ValueError("La calidad JPEG debe estar entre 40 y 95")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_manifest(path: Path) -> dict:
    if not path.is_file():
        return {"version": 1, "files": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "files": {}}
    if not isinstance(data, dict) or not isinstance(data.get("files"), dict):
        return {"version": 1, "files": {}}
    return data


def _atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def _replace_with_retries(source: Path, target: Path, attempts: int = 8) -> None:
    for attempt in range(1, attempts + 1):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == attempts:
                raise
            time.sleep(0.20 * attempt)


def _remove_tree_with_retries(path: Path, attempts: int = 8) -> None:
    if not path.exists():
        return
    for attempt in range(1, attempts + 1):
        try:
            shutil.rmtree(path)
            return
        except PermissionError:
            if attempt == attempts:
                raise
            time.sleep(0.20 * attempt)


def _discover_images(source_root: Path) -> list[Path]:
    images: list[Path] = []
    for folder in sorted(path for path in source_root.iterdir() if path.is_dir()):
        images.extend(
            sorted(
                path
                for path in folder.iterdir()
                if path.is_file() and path.suffix.casefold() in SUPPORTED_EXTENSIONS
            )
        )
    return images


def _has_transparency(image: Image.Image) -> bool:
    return image.mode in {"RGBA", "LA"} or (
        image.mode == "P" and "transparency" in image.info
    )


def _target_relative_path(source: Path, source_root: Path) -> Path:
    relative = source.relative_to(source_root)
    if source.suffix.casefold() == ".png":
        with Image.open(source) as probe:
            if not _has_transparency(probe):
                return relative.with_suffix(".jpg")
    return relative


def _save_optimized(source: Path, target: Path, config: GalleryConfig) -> tuple[int, int, str]:
    target.parent.mkdir(parents=True, exist_ok=True)
    suffix = target.suffix.casefold()
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.stem}-", suffix=target.suffix, dir=target.parent
    )
    os.close(file_descriptor)
    temporary = Path(temporary_name)
    try:
        with Image.open(source) as opened:
            opened.load()
            image = ImageOps.exif_transpose(opened)
            image.thumbnail(
                (config.max_dimension, config.max_dimension),
                resample=Image.Resampling.LANCZOS,
            )
            width, height = image.size
            if suffix in {".jpg", ".jpeg"}:
                if _has_transparency(image):
                    rgba = image.convert("RGBA")
                    background = Image.new("RGB", rgba.size, "white")
                    background.paste(rgba, mask=rgba.getchannel("A"))
                    image = background
                else:
                    image = image.convert("RGB")
                image.save(
                    temporary,
                    format="JPEG",
                    quality=config.jpeg_quality,
                    optimize=True,
                    progressive=True,
                    subsampling="4:2:0",
                )
                output_format = "JPEG"
            else:
                if image.mode not in {"RGB", "RGBA", "L", "LA", "P"}:
                    image = image.convert("RGBA" if _has_transparency(image) else "RGB")
                image.save(temporary, format="PNG", optimize=True, compress_level=9)
                output_format = "PNG"
        os.replace(temporary, target)
        return width, height, output_format
    finally:
        temporary.unlink(missing_ok=True)


def _write_reports(config: GalleryConfig, result: dict) -> None:
    config.reports_root.mkdir(parents=True, exist_ok=True)
    _atomic_json(config.reports_root / "gallery_optimization.json", result)
    csv_path = config.reports_root / "gallery_optimization.csv"
    temporary = csv_path.with_name(f".{csv_path.name}.tmp")
    fields = (
        "source", "output", "status", "original_bytes", "optimized_bytes",
        "width", "height", "format", "message",
    )
    with temporary.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter=";")
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in result["files"])
    os.replace(temporary, csv_path)


def optimize_gallery(
    config: GalleryConfig,
    progress: ProgressCallback | None = None,
) -> dict:
    """Optimiza imágenes nuevas o modificadas y conserva intactas las demás."""

    config.validate()
    source_root = config.source_root.expanduser().resolve()
    output_root = config.output_root.expanduser().resolve()
    output_root.parent.mkdir(parents=True, exist_ok=True)
    images = _discover_images(source_root)
    if not images:
        raise ValueError(
            "No se encontraron imágenes JPG, JPEG o PNG dentro de carpetas como "
            "General o <project_id> en la carpeta de originales"
        )

    manifest = _load_manifest(output_root / MANIFEST_NAME)
    previous_files = manifest.get("files", {})
    next_files: dict[str, dict] = {}
    rows: list[dict] = []
    processed = skipped = failed = 0
    original_bytes = optimized_bytes = 0
    operation_id = uuid.uuid4().hex[:10]
    staging = output_root.parent / f".{output_root.name}.staging-{operation_id}"
    backup = output_root.parent / f".{output_root.name}.previous-{operation_id}"
    if staging.exists():
        _remove_tree_with_retries(staging)
    if backup.exists():
        _remove_tree_with_retries(backup)
    staging.mkdir(parents=False, exist_ok=False)
    (staging / ".gitkeep").write_text("\n", encoding="utf-8")

    targets: dict[str, str] = {}
    for source in images:
        relative_source = source.relative_to(source_root).as_posix()
        relative_target = _target_relative_path(source, source_root).as_posix()
        if relative_target.casefold() in targets:
            other = targets[relative_target.casefold()]
            raise ValueError(
                f"Dos originales generarían el mismo archivo publicado: {other} y {relative_source}"
            )
        targets[relative_target.casefold()] = relative_source

    total = len(images)
    published = False
    try:
        if progress:
            progress(0, total, "Preparando una publicación temporal de la galería")
        for index, source in enumerate(images, start=1):
            relative_source = source.relative_to(source_root).as_posix()
            target_relative = _target_relative_path(source, source_root)
            current_target = output_root / target_relative
            staged_target = staging / target_relative
            source_hash = _sha256(source)
            source_size = source.stat().st_size
            original_bytes += source_size
            previous = previous_files.get(relative_source, {})
            if (
                previous.get("source_sha256") == source_hash
                and previous.get("output") == target_relative.as_posix()
                and current_target.is_file()
            ):
                staged_target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(current_target, staged_target)
                target_size = staged_target.stat().st_size
                optimized_bytes += target_size
                skipped += 1
                next_files[relative_source] = dict(previous)
                row = {
                    "source": relative_source,
                    "output": target_relative.as_posix(),
                    "status": "Sin cambios",
                    "original_bytes": source_size,
                    "optimized_bytes": target_size,
                    "width": previous.get("width", ""),
                    "height": previous.get("height", ""),
                    "format": previous.get("format", ""),
                    "message": "Se reutilizó la copia optimizada de la publicación anterior.",
                }
            else:
                try:
                    width, height, output_format = _save_optimized(source, staged_target, config)
                    target_size = staged_target.stat().st_size
                    optimized_bytes += target_size
                    processed += 1
                    next_files[relative_source] = {
                        "source_sha256": source_hash,
                        "output": target_relative.as_posix(),
                        "width": width,
                        "height": height,
                        "format": output_format,
                        "original_bytes": source_size,
                        "optimized_bytes": target_size,
                    }
                    row = {
                        "source": relative_source,
                        "output": target_relative.as_posix(),
                        "status": "Optimizada",
                        "original_bytes": source_size,
                        "optimized_bytes": target_size,
                        "width": width,
                        "height": height,
                        "format": output_format,
                        "message": "",
                    }
                except Exception as exc:  # Revisa todo el conjunto antes de rechazarlo.
                    failed += 1
                    row = {
                        "source": relative_source,
                        "output": target_relative.as_posix(),
                        "status": "Error",
                        "original_bytes": source_size,
                        "optimized_bytes": 0,
                        "width": "",
                        "height": "",
                        "format": "",
                        "message": str(exc),
                    }
            rows.append(row)
            if progress:
                progress(index, total, f"{row['status']}: {relative_source}")

        generated_at = datetime.now(timezone.utc).isoformat()
        settings = {
            "max_dimension": config.max_dimension,
            "jpeg_quality": config.jpeg_quality,
        }
        savings = max(0, original_bytes - optimized_bytes)
        result = {
            "generated_at_utc": generated_at,
            "source_root": str(source_root),
            "output_root": str(output_root),
            "settings": settings,
            "summary": {
                "found": total,
                "processed": processed,
                "skipped": skipped,
                "failed": failed,
                "published": False,
                "original_bytes": original_bytes,
                "optimized_bytes": optimized_bytes,
                "saved_bytes": savings,
                "saved_percent": round((savings / original_bytes * 100) if original_bytes else 0, 2),
            },
            "files": rows,
        }
        if failed:
            _write_reports(config, result)
            return result

        staged_manifest = {
            "version": 1,
            "generated_at_utc": generated_at,
            "settings": settings,
            "files": next_files,
        }
        _atomic_json(staging / MANIFEST_NAME, staged_manifest)
        output_backed_up = False
        output_published = False
        try:
            if output_root.exists():
                _replace_with_retries(output_root, backup)
                output_backed_up = True
            _replace_with_retries(staging, output_root)
            output_published = True
        except Exception:
            if output_published and output_root.exists():
                _remove_tree_with_retries(output_root)
            if output_backed_up and backup.exists():
                _replace_with_retries(backup, output_root)
            raise
        if backup.exists():
            _remove_tree_with_retries(backup)
        published = True
        result["summary"]["published"] = True
        _write_reports(config, result)
        return result
    finally:
        if staging.exists():
            _remove_tree_with_retries(staging)
        if backup.exists() and published:
            _remove_tree_with_retries(backup)
