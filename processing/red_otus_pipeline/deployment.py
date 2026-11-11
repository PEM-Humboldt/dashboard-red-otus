"""Publicación segura de paquetes Red OTUS mediante SSH y SFTP."""

from __future__ import annotations

import base64
import hashlib
import json
import re
import shlex
import socket
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Callable, Literal


ProgressCallback = Callable[[int, int, str], None]
LogCallback = Callable[[str], None]
CancelCallback = Callable[[], bool]


class DeploymentError(RuntimeError):
    """Indica que una operación remota no pudo completarse de forma segura."""


class DeploymentCancelled(Exception):
    """Indica que el usuario canceló una transferencia o verificación."""


class UnknownHostFingerprint(DeploymentError):
    """Solicita confirmar por un canal confiable la identidad observada."""

    def __init__(self, fingerprint: str) -> None:
        self.fingerprint = fingerprint
        super().__init__(
            "La identidad del servidor aún no está fijada. "
            f"Huella observada: {fingerprint}"
        )


@dataclass(frozen=True)
class ServerProfile:
    """Configuración no sensible del servidor institucional."""

    host: str
    port: int
    username: str
    fingerprint: str
    remote_root: str = "/opt/red-otus"
    updater_path: str = "/opt/red-otus/bin/actualizar-release.sh"
    rollback_path: str = "/opt/red-otus/bin/revertir-release.sh"
    health_url: str = "http://127.0.0.1:3838/red-otus/"

    def validate(self, require_fingerprint: bool = True) -> None:
        if not self.host.strip() or any(char.isspace() for char in self.host):
            raise ValueError("Indique una dirección de servidor válida")
        if not 1 <= int(self.port) <= 65535:
            raise ValueError("El puerto SSH debe estar entre 1 y 65535")
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", self.username):
            raise ValueError("El usuario SSH contiene caracteres no permitidos")
        for label, value in (
            ("raíz remota", self.remote_root),
            ("actualizador", self.updater_path),
            ("script de reversión", self.rollback_path),
        ):
            path = PurePosixPath(value)
            if not path.is_absolute() or ".." in path.parts:
                raise ValueError(f"La ruta de {label} no es absoluta o no es segura")
        if require_fingerprint and not normalize_fingerprint(self.fingerprint):
            raise ValueError(
                "La identidad SSH del servidor todavía no ha sido confirmada"
            )


@dataclass(frozen=True)
class Authentication:
    """Contraseña efímera utilizada durante la conexión institucional."""

    password: str | None = None

    def validate(self) -> None:
        if not self.password:
            raise ValueError("Indique la contraseña suministrada por TI")


@dataclass(frozen=True)
class PackageInfo:
    package_path: Path
    checksum_path: Path
    sha256: str
    release_id: str
    cutoff_date: str
    dataset_count: int
    favorite_count: int
    components: tuple[str, ...]
    size_bytes: int


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_fingerprint(value: str) -> str:
    """Normaliza una huella OpenSSH SHA256 para comparaciones estrictas."""

    text = value.strip()
    if not text:
        return ""
    if not text.upper().startswith("SHA256:"):
        text = f"SHA256:{text}"
    prefix, encoded = text.split(":", 1)
    if not re.fullmatch(r"[A-Za-z0-9+/]{20,}={0,2}", encoded):
        raise ValueError("La huella SSH no tiene el formato SHA256 esperado")
    return f"{prefix.upper()}:{encoded.rstrip('=')}"


def fingerprint_sha256(key_bytes: bytes) -> str:
    encoded = base64.b64encode(hashlib.sha256(key_bytes).digest()).decode("ascii")
    return f"SHA256:{encoded.rstrip('=')}"


def inspect_update_package(package_path: Path, checksum_path: Path | None = None) -> PackageInfo:
    """Valida el ZIP local y obtiene el contrato que consumirá el servidor."""

    package = package_path.expanduser().resolve()
    checksum = (checksum_path or package.with_suffix(package.suffix + ".sha256")).expanduser().resolve()
    if not package.is_file() or package.suffix.casefold() != ".zip":
        raise ValueError(f"No existe un paquete ZIP válido: {package}")
    if not checksum.is_file():
        raise ValueError(f"No existe el archivo SHA-256 del paquete: {checksum}")
    expected = checksum.read_text(encoding="ascii").strip().split()
    if not expected or not re.fullmatch(r"[0-9a-fA-F]{64}", expected[0]):
        raise ValueError("El archivo .sha256 no contiene una huella válida")
    actual = _sha256(package)
    if actual.casefold() != expected[0].casefold():
        raise ValueError("La huella SHA-256 del ZIP no coincide")
    try:
        with zipfile.ZipFile(package) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError("El ZIP contiene nombres de archivo duplicados")
            for name in names:
                candidate = PurePosixPath(name)
                if candidate.is_absolute() or ".." in candidate.parts:
                    raise ValueError(f"El ZIP contiene una ruta insegura: {name}")
            if "RELEASE.json" not in names or "FILES.sha256" not in names:
                raise ValueError("El paquete no contiene RELEASE.json y FILES.sha256")
            metadata = json.loads(archive.read("RELEASE.json").decode("utf-8-sig"))
            registered: set[str] = set()
            for line in archive.read("FILES.sha256").decode("utf-8").splitlines():
                parts = line.strip().split(maxsplit=1)
                if len(parts) != 2 or not re.fullmatch(r"[0-9a-fA-F]{64}", parts[0]):
                    raise ValueError("FILES.sha256 contiene una entrada inválida")
                relative = parts[1].lstrip("*").strip().replace("\\", "/")
                if relative in registered or relative not in names:
                    raise ValueError(f"Archivo interno ausente o duplicado: {relative}")
                registered.add(relative)
                digest = hashlib.sha256()
                with archive.open(relative) as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(block)
                if digest.hexdigest().casefold() != parts[0].casefold():
                    raise ValueError(f"Huella interna inválida: {relative}")
            expected_files = {name for name in names if name and not name.endswith("/")}
            expected_files.discard("FILES.sha256")
            if registered != expected_files:
                raise ValueError("FILES.sha256 no cubre exactamente el contenido del paquete")
    except (zipfile.BadZipFile, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("El ZIP o su metadato RELEASE.json no son válidos") from exc
    release_id = str(metadata.get("release_id", ""))
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,160}", release_id):
        raise ValueError("RELEASE.json no contiene un release_id válido")
    components = tuple(str(item) for item in metadata.get("components", []))
    if "data" not in components or "favorites" not in components:
        raise ValueError("El paquete debe incluir data y favorites")
    return PackageInfo(
        package_path=package,
        checksum_path=checksum,
        sha256=actual,
        release_id=release_id,
        cutoff_date=str(metadata.get("cutoff_date", "")),
        dataset_count=int(metadata.get("dataset_count", 0)),
        favorite_count=int(metadata.get("favorite_count", 0)),
        components=components,
        size_bytes=package.stat().st_size,
    )


def _paramiko():
    try:
        import paramiko  # type: ignore
    except ImportError as exc:  # pragma: no cover - depende del entorno instalado
        raise DeploymentError(
            "Falta la dependencia Paramiko. Restaure processing/requirements.lock.txt."
        ) from exc
    return paramiko


def probe_server_fingerprint(host: str, port: int, timeout: float = 12) -> str:
    """Lee la clave presentada por el servidor sin enviar credenciales."""

    paramiko = _paramiko()
    try:
        with socket.create_connection((host, int(port)), timeout=timeout) as connection:
            transport = paramiko.Transport(connection)
            try:
                transport.start_client(timeout=timeout)
                key = transport.get_remote_server_key()
                return fingerprint_sha256(key.asbytes())
            finally:
                transport.close()
    except (OSError, paramiko.SSHException) as exc:
        raise DeploymentError(f"No fue posible consultar la identidad SSH: {exc}") from exc


class _PinnedHostKeyPolicy:
    def __init__(self, expected: str) -> None:
        self.expected = normalize_fingerprint(expected)

    def missing_host_key(self, client, hostname, key) -> None:  # pragma: no cover - red real
        observed = fingerprint_sha256(key.asbytes())
        if not self.expected:
            raise UnknownHostFingerprint(observed)
        if observed != self.expected:
            raise DeploymentError(
                "La huella SSH del servidor cambió. "
                f"Esperada: {self.expected}; observada: {observed}. "
                "No continúe hasta confirmarlo con el administrador."
            )
        client.get_host_keys().add(hostname, key.get_name(), key)


class SSHDeploymentClient:
    """Cliente restringido al contrato de despliegue de Red OTUS."""

    def __init__(
        self,
        profile: ServerProfile,
        authentication: Authentication,
        log: LogCallback | None = None,
        cancelled: CancelCallback | None = None,
    ) -> None:
        profile.validate()
        authentication.validate()
        self.profile = profile
        self.authentication = authentication
        self.log = log or (lambda _message: None)
        self.cancelled = cancelled or (lambda: False)
        self.client = None

    def connect(self) -> None:
        paramiko = _paramiko()
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(_PinnedHostKeyPolicy(self.profile.fingerprint))
        kwargs = {
            "hostname": self.profile.host,
            "port": int(self.profile.port),
            "username": self.profile.username,
            "timeout": 15,
            "banner_timeout": 15,
            "auth_timeout": 20,
            "allow_agent": False,
            "look_for_keys": False,
            "password": self.authentication.password,
        }
        try:
            client.connect(**kwargs)
        except Exception as exc:
            client.close()
            raise DeploymentError(f"No fue posible autenticar la conexión SSH: {exc}") from exc
        self.client = client

    def close(self) -> None:
        if self.client is not None:
            self.client.close()
            self.client = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc, traceback_value) -> None:
        self.close()

    def _exec(self, command: str, sudo: bool = False, timeout: int = 240) -> tuple[int, str, str]:
        if self.client is None:
            raise DeploymentError("La conexión SSH no está activa")
        if sudo:
            command = f"sudo -S -p '' -- {command}"
        stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
        if sudo:
            stdin.write((self.authentication.password or "") + "\n")
            stdin.flush()
        channel = stdout.channel
        out_parts: list[str] = []
        err_parts: list[str] = []
        started = time.monotonic()
        while not channel.exit_status_ready():
            if self.cancelled():
                channel.close()
                raise DeploymentCancelled()
            if time.monotonic() - started > timeout:
                channel.close()
                raise DeploymentError("La operación remota excedió el tiempo permitido")
            if channel.recv_ready():
                text = channel.recv(65536).decode("utf-8", errors="replace")
                out_parts.append(text)
                for line in text.splitlines():
                    self.log(line)
            if channel.recv_stderr_ready():
                text = channel.recv_stderr(65536).decode("utf-8", errors="replace")
                err_parts.append(text)
                for line in text.splitlines():
                    self.log(line)
            time.sleep(0.05)
        while channel.recv_ready():
            text = channel.recv(65536).decode("utf-8", errors="replace")
            out_parts.append(text)
            for line in text.splitlines():
                self.log(line)
        while channel.recv_stderr_ready():
            text = channel.recv_stderr(65536).decode("utf-8", errors="replace")
            err_parts.append(text)
            for line in text.splitlines():
                self.log(line)
        return channel.recv_exit_status(), "".join(out_parts), "".join(err_parts)

    def _checked(self, command: str, sudo: bool = False, timeout: int = 240) -> str:
        code, stdout, stderr = self._exec(command, sudo=sudo, timeout=timeout)
        if code != 0:
            detail = (stderr or stdout).strip().splitlines()
            raise DeploymentError(detail[-1] if detail else f"El comando remoto terminó con código {code}")
        return stdout.strip()

    def inspect(self) -> dict[str, object]:
        root = shlex.quote(self.profile.remote_root)
        updater = shlex.quote(self.profile.updater_path)
        rollback = shlex.quote(self.profile.rollback_path)
        command = (
            f"test -d {root} && test -x {updater} && test -x {rollback} && "
            f"printf 'release='; readlink -f {root}/releases/current; "
            f"printf '\\nactivated_at='; stat -c '%y' {root}/releases/current; "
            f"printf '\\ndisk_kb='; df -Pk {root} | awk 'NR==2 {{print $4}}'; "
            "printf '\\ndocker='; systemctl is-active docker; "
            f"printf '\\nupdater_meta='; stat -c '%U:%G %a' {updater}"
        )
        output = self._checked(command, timeout=30)
        values: dict[str, str] = {}
        for line in output.splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
        if values.get("docker") != "active":
            raise DeploymentError(
                f"Docker no está activo en el servidor (estado: {values.get('docker', 'desconocido')})"
            )
        release = Path(values.get("release", "")).name
        return {
            "release_id": release,
            "release_activated_at": values.get("activated_at", ""),
            "disk_available_bytes": int(values.get("disk_kb", "0") or 0) * 1024,
            "docker_status": values.get("docker", "desconocido"),
            "updater_meta": values.get("updater_meta", "desconocido"),
            "host": self.profile.host,
        }

    def _upload(self, source: Path, remote: str, callback: Callable[[int, int], None]) -> None:
        if self.client is None:
            raise DeploymentError("La conexión SSH no está activa")
        sftp = self.client.open_sftp()
        temporary = remote + ".part"
        try:
            sftp.put(str(source), temporary, callback=callback, confirm=True)
            sftp.rename(temporary, remote)
        except Exception:
            try:
                sftp.remove(temporary)
            except Exception:
                pass
            raise
        finally:
            sftp.close()

    def deploy(self, info: PackageInfo, progress: ProgressCallback | None = None) -> dict[str, object]:
        def emit(current: int, total: int, message: str) -> None:
            if self.cancelled():
                raise DeploymentCancelled()
            if progress:
                progress(current, total, message)

        before = self.inspect()
        if int(before["disk_available_bytes"]) < info.size_bytes * 3:
            raise DeploymentError("El servidor no tiene espacio suficiente para transferir y activar el paquete")
        upload_dir = f"/tmp/red-otus-upload-{self.profile.username}"
        remote_zip = f"{upload_dir}/{info.package_path.name}"
        remote_checksum = f"{upload_dir}/{info.checksum_path.name}"
        quoted_dir = shlex.quote(upload_dir)
        self._checked(f"mkdir -p -m 700 {quoted_dir}")
        emit(1, 6, "Conexión y precondiciones verificadas")

        def transferred(done: int, total: int) -> None:
            if self.cancelled():
                raise DeploymentCancelled()
            if progress:
                progress(2, 6, f"Transfiriendo paquete: {done * 100 // max(total, 1)} %")

        try:
            self._upload(info.package_path, remote_zip, transferred)
            self._upload(info.checksum_path, remote_checksum, lambda _done, _total: None)
            emit(3, 6, "Comprobando SHA-256 en el servidor")
            remote_hash = self._checked(
                f"sha256sum {shlex.quote(remote_zip)} | awk '{{print $1}}'", timeout=120
            )
            if remote_hash.casefold() != info.sha256.casefold():
                raise DeploymentError("La huella del archivo recibido no coincide con el paquete local")
            emit(4, 6, "Activando la nueva release")
            command = " ".join(
                (
                    "flock",
                    "-n",
                    "/run/lock/red-otus-update.lock",
                    shlex.quote(self.profile.updater_path),
                    shlex.quote(remote_zip),
                    shlex.quote(remote_checksum),
                )
            )
            self._checked(command, sudo=True, timeout=420)
            emit(5, 6, "Verificando release activa y respuesta HTTP")
            active = Path(
                self._checked(
                    f"readlink -f {shlex.quote(self.profile.remote_root)}/releases/current"
                )
            ).name
            if active != info.release_id:
                raise DeploymentError(
                    f"El servidor dejó activa la release {active}, no {info.release_id}"
                )
            http = self._checked(
                f"curl -fsS -o /dev/null -w '%{{http_code}}' {shlex.quote(self.profile.health_url)}",
                timeout=40,
            )
            if http != "200":
                raise DeploymentError(f"La comprobación HTTP devolvió {http}")
            after = self.inspect()
            emit(6, 6, "Actualización verificada correctamente")
            return {
                "status": "success",
                "host": self.profile.host,
                "previous_release": before["release_id"],
                "previous_release_activated_at": before.get("release_activated_at", ""),
                "active_release": active,
                "active_release_activated_at": after.get("release_activated_at", ""),
                "http_status": 200,
                "package_sha256": info.sha256,
                "release_id": info.release_id,
            }
        finally:
            try:
                self._exec(
                    f"rm -f -- {shlex.quote(remote_zip)} {shlex.quote(remote_checksum)} "
                    f"{shlex.quote(remote_zip + '.part')} {shlex.quote(remote_checksum + '.part')}",
                    timeout=30,
                )
            except Exception:
                pass

    def rollback(self, progress: ProgressCallback | None = None) -> dict[str, object]:
        before = self.inspect()
        if progress:
            progress(1, 3, "Ejecutando la reversión controlada")
        self._checked(
            " ".join(
                (
                    "flock",
                    "-n",
                    "/run/lock/red-otus-update.lock",
                    shlex.quote(self.profile.rollback_path),
                )
            ),
            sudo=True,
            timeout=420,
        )
        if progress:
            progress(2, 3, "Verificando la versión restaurada")
        after = self.inspect()
        http = self._checked(
            f"curl -fsS -o /dev/null -w '%{{http_code}}' {shlex.quote(self.profile.health_url)}",
            timeout=40,
        )
        if http != "200" or after["release_id"] == before["release_id"]:
            raise DeploymentError("La reversión no produjo una release saludable diferente")
        if progress:
            progress(3, 3, "Reversión verificada correctamente")
        return {
            "status": "rolled_back",
            "host": self.profile.host,
            "previous_release": before["release_id"],
            "previous_release_activated_at": before.get("release_activated_at", ""),
            "active_release": after["release_id"],
            "active_release_activated_at": after.get("release_activated_at", ""),
            "http_status": 200,
        }


def write_audit_record(
    result: dict[str, object],
    action: Literal["check", "deploy", "rollback", "failure"],
    output_dir: Path,
) -> Path:
    """Guarda una evidencia local sin credenciales ni secretos."""

    destination = output_dir.expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc)
    record = {
        "schema_version": 1,
        "timestamp_utc": timestamp.isoformat(),
        "action": action,
        **result,
    }
    path = destination / f"red-otus-{action}-{timestamp.strftime('%Y%m%dT%H%M%SZ')}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
