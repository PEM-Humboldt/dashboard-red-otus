"""Valida y empaqueta una publicación aprobada para actualizar el servidor."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


ProgressCallback = Callable[[int, int, str], None]


class PackageCancelled(Exception):
    """Interrumpe la creación antes de publicar un paquete incompleto."""


@dataclass(frozen=True)
class UpdatePackageConfig:
    """Rutas que componen una actualización ordinaria del dashboard."""

    data_root: Path
    favorites_root: Path
    output_dir: Path
    spatial_root: Path | None = None

    def validate(self) -> None:
        data = self.data_root.expanduser().resolve()
        favorites = self.favorites_root.expanduser().resolve()
        output = self.output_dir.expanduser().resolve()
        if not data.is_dir():
            raise ValueError(f"No existe la carpeta de datos publicados: {data}")
        if not favorites.is_dir():
            raise ValueError(f"No existe la carpeta de imágenes publicadas: {favorites}")
        if data == favorites or data in favorites.parents or favorites in data.parents:
            raise ValueError("Las carpetas de datos e imágenes deben ser independientes")
        for source in (data, favorites):
            if output == source or output in source.parents or source in output.parents:
                raise ValueError("La carpeta de paquetes debe estar fuera de los insumos publicados")
        if self.spatial_root is not None:
            spatial = self.spatial_root.expanduser().resolve()
            if not spatial.is_dir():
                raise ValueError(f"No existe la carpeta espacial seleccionada: {spatial}")
            if output == spatial or output in spatial.parents or spatial in output.parents:
                raise ValueError("La carpeta de paquetes debe estar fuera de la carpeta espacial")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path, label: str) -> dict:
    if not path.is_file():
        raise ValueError(f"Falta {label}: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"No fue posible leer {label}: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label.capitalize()} no contiene un objeto JSON válido")
    return value


def _safe_file(root: Path, relative: object, label: str) -> Path:
    text = str(relative).replace("\\", "/").strip()
    candidate = Path(text)
    if not text or candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"Ruta insegura en {label}: {text or '<vacía>'}")
    root = root.resolve()
    resolved = (root / candidate).resolve()
    if resolved != root and root not in resolved.parents:
        raise ValueError(f"Ruta fuera de la publicación en {label}: {text}")
    if not resolved.is_file():
        raise ValueError(f"Falta el archivo registrado en {label}: {text}")
    return resolved


def inspect_update_sources(config: UpdatePackageConfig) -> dict[str, object]:
    """Comprueba manifiestos, archivos y huellas antes de habilitar el paquete."""

    config.validate()
    data_root = config.data_root.expanduser().resolve()
    favorites_root = config.favorites_root.expanduser().resolve()
    data_manifest = _load_json(data_root / "manifest.json", "el manifiesto de datos")
    if data_manifest.get("status") != "approved":
        raise ValueError(
            "El manifiesto de datos no está aprobado "
            f"(status={data_manifest.get('status', 'ausente')})"
        )
    run_id = str(data_manifest.get("run_id", "")).strip()
    if not run_id:
        raise ValueError("El manifiesto de datos no contiene run_id")

    datasets = data_manifest.get("datasets")
    if not isinstance(datasets, list) or not datasets:
        raise ValueError("El manifiesto de datos no registra datasets")
    for dataset in datasets:
        if not isinstance(dataset, dict):
            raise ValueError("El manifiesto contiene un dataset inválido")
        source = _safe_file(data_root, dataset.get("file"), "el manifiesto de datos")
        expected_size = dataset.get("bytes")
        expected_hash = str(dataset.get("sha256", "")).casefold()
        if source.stat().st_size != expected_size or _sha256(source) != expected_hash:
            raise ValueError(f"Hash o tamaño inválido en {dataset.get('file')}")

    gallery_manifest = _load_json(
        favorites_root / ".gallery_manifest.json", "el manifiesto de imágenes"
    )
    gallery_files = gallery_manifest.get("files")
    if not isinstance(gallery_files, dict) or not gallery_files:
        raise ValueError("El manifiesto de imágenes no registra archivos")
    outputs: set[str] = set()
    for item in gallery_files.values():
        if not isinstance(item, dict):
            raise ValueError("El manifiesto de imágenes contiene una entrada inválida")
        output = str(item.get("output", "")).replace("\\", "/")
        normalized = output.casefold()
        if normalized in outputs:
            raise ValueError(f"La imagen publicada está registrada más de una vez: {output}")
        outputs.add(normalized)
        _safe_file(favorites_root, output, "el manifiesto de imágenes")

    spatial_count = 0
    if config.spatial_root is not None:
        spatial_root = config.spatial_root.expanduser().resolve()
        spatial_count = sum(1 for path in spatial_root.rglob("*") if path.is_file())
        if spatial_count == 0:
            raise ValueError("La carpeta espacial seleccionada está vacía")

    return {
        "run_id": run_id,
        "cutoff_date": str(data_manifest.get("cutoff_date", "")),
        "dataset_count": len(datasets),
        "favorite_count": len(gallery_files),
        "spatial_count": spatial_count,
        "include_spatial": config.spatial_root is not None,
    }


def _copy_component(source: Path, target: Path) -> None:
    shutil.copytree(source, target, copy_function=shutil.copy2)


def _files(root: Path) -> list[Path]:
    return sorted(
        (path for path in root.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(root).as_posix().casefold(),
    )


def _emit(progress: ProgressCallback | None, current: int, total: int, message: str) -> None:
    if progress is not None:
        progress(current, total, message)


def create_update_package(
    config: UpdatePackageConfig,
    progress: ProgressCallback | None = None,
) -> dict[str, object]:
    """Crea de forma atómica el ZIP, su SHA-256 y el resumen de la actualización."""

    summary = inspect_update_sources(config)
    output_dir = config.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_run_id = re.sub(r"[^A-Za-z0-9_.-]", "_", str(summary["run_id"]))
    release_id = f"data-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{safe_run_id}"
    zip_path = output_dir / f"red-otus-update-{release_id}.zip"
    checksum_path = zip_path.with_suffix(zip_path.suffix + ".sha256")
    if zip_path.exists() or checksum_path.exists():
        raise FileExistsError(f"Ya existe un paquete con el identificador {release_id}")

    total_steps = 7 if config.spatial_root is not None else 6
    with tempfile.TemporaryDirectory(prefix="red-otus-package-", dir=output_dir) as temporary:
        workspace = Path(temporary)
        payload = workspace / "payload"
        payload.mkdir()
        _emit(progress, 1, total_steps, "Copiando los datos aprobados")
        _copy_component(config.data_root.expanduser().resolve(), payload / "data")
        _emit(progress, 2, total_steps, "Copiando las imágenes publicadas")
        _copy_component(config.favorites_root.expanduser().resolve(), payload / "favorites")

        components = ["data", "favorites"]
        step = 3
        if config.spatial_root is not None:
            _emit(progress, step, total_steps, "Copiando los polígonos espaciales")
            _copy_component(config.spatial_root.expanduser().resolve(), payload / "spatial")
            components.append("spatial")
            step += 1

        payload_files = _files(payload)
        metadata = {
            "schema_version": 1,
            "release_id": release_id,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_run_id": summary["run_id"],
            "cutoff_date": summary["cutoff_date"],
            "components": components,
            "dataset_count": summary["dataset_count"],
            "favorite_count": summary["favorite_count"],
            "spatial_file_count": summary["spatial_count"],
            "payload_file_count": len(payload_files),
            "payload_bytes": sum(path.stat().st_size for path in payload_files),
            "note": "Paquete de insumos; no contiene código ni imagen Docker.",
        }
        (payload / "RELEASE.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        _emit(progress, step, total_steps, "Calculando la integridad de los archivos")
        hash_lines = [
            f"{_sha256(path)}  {path.relative_to(payload).as_posix()}"
            for path in _files(payload)
        ]
        (payload / "FILES.sha256").write_text("\n".join(hash_lines) + "\n", encoding="utf-8")
        step += 1

        temporary_zip = workspace / zip_path.name
        _emit(progress, step, total_steps, "Comprimiendo el paquete de actualización")
        with zipfile.ZipFile(
            temporary_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for source in _files(payload):
                archive.write(source, source.relative_to(payload).as_posix())
        step += 1

        _emit(progress, step, total_steps, "Calculando la huella SHA-256 del paquete")
        zip_hash = _sha256(temporary_zip)
        temporary_checksum = workspace / checksum_path.name
        temporary_checksum.write_text(
            f"{zip_hash}  {zip_path.name}\n", encoding="ascii"
        )
        step += 1

        _emit(progress, step, total_steps, "Publicando los archivos finales")
        os.replace(temporary_zip, zip_path)
        try:
            os.replace(temporary_checksum, checksum_path)
        except Exception:
            zip_path.unlink(missing_ok=True)
            raise

    _emit(progress, total_steps, total_steps, "Paquete creado correctamente")
    return {
        **summary,
        "release_id": release_id,
        "package_path": str(zip_path),
        "checksum_path": str(checksum_path),
        "sha256": zip_hash,
        "size_bytes": zip_path.stat().st_size,
    }
