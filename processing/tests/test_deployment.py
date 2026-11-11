"""Pruebas locales del contrato de publicación remota."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from red_otus_pipeline.deployment import (
    Authentication,
    SSHDeploymentClient,
    ServerProfile,
    fingerprint_sha256,
    inspect_update_package,
    normalize_fingerprint,
    write_audit_record,
)


class DeploymentContractTests(unittest.TestCase):
    def _package(self, root: Path) -> tuple[Path, Path]:
        package = root / "red-otus-update-data-test.zip"
        release = {
            "release_id": "data-20261109-test",
            "cutoff_date": "2026-11-02",
            "dataset_count": 11,
            "favorite_count": 698,
            "components": ["data", "favorites"],
        }
        files = {
            "RELEASE.json": json.dumps(release).encode(),
            "data/manifest.json": b"{}",
            "favorites/.gallery_manifest.json": b"{}",
        }
        internal_hashes = "".join(
            f"{hashlib.sha256(content).hexdigest()}  {name}\n"
            for name, content in files.items()
        )
        with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in files.items():
                archive.writestr(name, content)
            archive.writestr("FILES.sha256", internal_hashes)
        digest = hashlib.sha256(package.read_bytes()).hexdigest()
        checksum = package.with_suffix(".zip.sha256")
        checksum.write_text(f"{digest}  {package.name}\n", encoding="ascii")
        return package, checksum

    def test_profile_and_fingerprint_validation(self) -> None:
        fingerprint = fingerprint_sha256(b"server-public-key")
        self.assertEqual(normalize_fingerprint(fingerprint + "="), fingerprint)
        ServerProfile("server.example", 2222, "deployer", fingerprint).validate()
        with self.assertRaises(ValueError):
            ServerProfile("server example", 2222, "deployer", fingerprint).validate()
        with self.assertRaises(ValueError):
            ServerProfile("server.example", 0, "deployer", fingerprint).validate()
        with self.assertRaises(ValueError):
            ServerProfile("server.example", 2222, "deployer", "").validate()

    def test_institutional_authentication_requires_only_password(self) -> None:
        Authentication(password="temporary").validate()
        with self.assertRaisesRegex(ValueError, "contraseña"):
            Authentication().validate()

    def test_inspection_reports_active_release_date(self) -> None:
        profile = ServerProfile(
            "server.example",
            2222,
            "deployer",
            fingerprint_sha256(b"server-public-key"),
        )

        class InspectClient(SSHDeploymentClient):
            def _checked(self, command: str, sudo: bool = False, timeout: int = 240) -> str:
                self.assert_command = command
                return (
                    "release=/opt/red-otus/releases/data-test\n"
                    "activated_at=2026-11-09 19:15:20.000000000 -0500\n"
                    "disk_kb=1024\n"
                    "docker=active\n"
                    "updater_meta=root:root 755"
                )

        client = InspectClient(profile, Authentication(password="temporary"))
        result = client.inspect()
        self.assertEqual(result["release_id"], "data-test")
        self.assertEqual(
            result["release_activated_at"], "2026-11-09 19:15:20.000000000 -0500"
        )
        self.assertIn("activated_at", client.assert_command)

    def test_inspects_integral_update_package(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package, checksum = self._package(Path(temporary))
            info = inspect_update_package(package, checksum)
            self.assertEqual(info.release_id, "data-20261109-test")
            self.assertEqual(info.dataset_count, 11)
            self.assertEqual(info.favorite_count, 698)
            self.assertEqual(info.components, ("data", "favorites"))

    def test_rejects_changed_or_unsafe_package(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package, checksum = self._package(root)
            package.write_bytes(package.read_bytes() + b"changed")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                inspect_update_package(package, checksum)

            unsafe = root / "unsafe.zip"
            with zipfile.ZipFile(unsafe, "w") as archive:
                archive.writestr("../RELEASE.json", "{}")
                archive.writestr("RELEASE.json", "{}")
                archive.writestr("FILES.sha256", "example")
            unsafe_hash = hashlib.sha256(unsafe.read_bytes()).hexdigest()
            unsafe_checksum = unsafe.with_suffix(".zip.sha256")
            unsafe_checksum.write_text(f"{unsafe_hash}  {unsafe.name}\n", encoding="ascii")
            with self.assertRaisesRegex(ValueError, "ruta insegura"):
                inspect_update_package(unsafe, unsafe_checksum)

    def test_audit_record_is_structured_and_external(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            record = write_audit_record(
                {
                    "host": "server.example",
                    "release_id": "data-test",
                    "http_status": 200,
                },
                "deploy",
                Path(temporary),
            )
            content = json.loads(record.read_text(encoding="utf-8"))
            self.assertEqual(content["action"], "deploy")
            self.assertEqual(content["http_status"], 200)
            self.assertNotIn("password", content)

    def test_deployment_uses_fixed_updater_lock_and_health_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package, checksum = self._package(Path(temporary))
            info = inspect_update_package(package, checksum)
            profile = ServerProfile(
                "server.example",
                2222,
                "deployer",
                fingerprint_sha256(b"server-public-key"),
            )

            class FakeClient(SSHDeploymentClient):
                def __init__(self) -> None:
                    super().__init__(profile, Authentication(password="temporary"))
                    self.commands: list[tuple[str, bool]] = []

                def inspect(self) -> dict[str, object]:
                    return {
                        "release_id": "release-before",
                        "disk_available_bytes": info.size_bytes * 10,
                        "docker_status": "active",
                        "host": profile.host,
                    }

                def _upload(self, source, remote, callback) -> None:
                    callback(source.stat().st_size, source.stat().st_size)

                def _checked(self, command: str, sudo: bool = False, timeout: int = 240) -> str:
                    self.commands.append((command, sudo))
                    if command.startswith("sha256sum"):
                        return info.sha256
                    if command.startswith("readlink"):
                        return f"/opt/red-otus/releases/{info.release_id}"
                    if command.startswith("curl"):
                        return "200"
                    return ""

                def _exec(self, command: str, sudo: bool = False, timeout: int = 240):
                    self.commands.append((command, sudo))
                    return 0, "", ""

            client = FakeClient()
            result = client.deploy(info)
            self.assertEqual(result["active_release"], info.release_id)
            updater = [item for item in client.commands if profile.updater_path in item[0]]
            self.assertEqual(len(updater), 1)
            self.assertTrue(updater[0][1])
            self.assertIn("flock -n /run/lock/red-otus-update.lock", updater[0][0])


if __name__ == "__main__":
    unittest.main()
