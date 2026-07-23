import contextlib
import fcntl
import hashlib
import json
import logging
import os
import re
import sqlite3
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.db import connections


logger = logging.getLogger(__name__)

BACKUP_NAME_PATTERN = re.compile(
    r"^qot-db-\d{8}-\d{6}-[a-f0-9]{8}\.(?:dump|sqlite3)$"
)


class BackupError(Exception):
    pass


class BackupBusyError(BackupError):
    pass


class BackupNotFoundError(BackupError):
    pass


def _backup_root():
    root = Path(
        getattr(settings, "ADMIN_BACKUP_ROOT", settings.BASE_DIR / "admin_backups")
    ).resolve()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    return root


def _database_config():
    config = settings.DATABASES["default"]
    engine = config.get("ENGINE", "")

    if engine.endswith("postgresql") or engine.endswith("postgresql_psycopg2"):
        return "postgresql", config

    if engine.endswith("sqlite3"):
        return "sqlite", config

    raise BackupError("This database engine is not supported for admin backups.")


def _command_environment(config):
    environment = os.environ.copy()
    password = str(config.get("PASSWORD") or "")

    if password:
        environment["PGPASSWORD"] = password

    return environment


def _postgres_connection_arguments(config):
    arguments = []

    if config.get("HOST"):
        arguments.extend(["--host", str(config["HOST"])])
    if config.get("PORT"):
        arguments.extend(["--port", str(config["PORT"])])
    if config.get("USER"):
        arguments.extend(["--username", str(config["USER"])])

    return arguments


def _run_database_command(command, config):
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=getattr(settings, "ADMIN_BACKUP_TIMEOUT", 900),
            env=_command_environment(config),
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        logger.exception("Unable to run database backup command")
        raise BackupError("The database backup tool could not be started.") from error

    if result.returncode != 0:
        logger.error(
            "Database backup command failed with exit code %s: %s",
            result.returncode,
            result.stderr[-2000:],
        )
        raise BackupError("The database backup operation failed.")


def _sha256(path):
    digest = hashlib.sha256()

    with path.open("rb") as backup_file:
        for chunk in iter(lambda: backup_file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def _metadata_path(path):
    return path.with_suffix(f"{path.suffix}.json")


def _write_metadata(path, metadata):
    metadata_path = _metadata_path(path)
    temporary_path = metadata_path.with_suffix(f"{metadata_path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    os.chmod(temporary_path, 0o600)
    temporary_path.replace(metadata_path)


def _read_metadata(path):
    metadata_path = _metadata_path(path)

    if metadata_path.exists():
        try:
            return json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            logger.warning("Ignoring invalid backup metadata: %s", metadata_path)

    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return {
        "name": path.name,
        "created_at": modified.isoformat(),
        "created_by": None,
        "database_vendor": "unknown",
        "kind": "manual",
    }


@contextlib.contextmanager
def _operation_lock():
    lock_path = _backup_root() / ".backup.lock"

    with lock_path.open("a+") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise BackupBusyError(
                "Another backup or restore operation is already running."
            ) from error

        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _backup_filename(vendor):
    extension = "dump" if vendor == "postgresql" else "sqlite3"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"qot-db-{timestamp}-{uuid.uuid4().hex[:8]}.{extension}"


def _create_backup(created_by=None, kind="manual"):
    vendor, config = _database_config()
    path = _backup_root() / _backup_filename(vendor)

    try:
        if vendor == "postgresql":
            command = [
                getattr(settings, "PG_DUMP_BINARY", "pg_dump"),
                "--format=custom",
                "--no-owner",
                "--no-privileges",
                "--file",
                str(path),
                *_postgres_connection_arguments(config),
                str(config["NAME"]),
            ]
            _run_database_command(command, config)
        else:
            database_path = Path(config["NAME"]).resolve()

            if not database_path.exists():
                raise BackupError("The SQLite database file does not exist.")

            with sqlite3.connect(database_path) as source:
                with sqlite3.connect(path) as destination:
                    source.backup(destination)

        os.chmod(path, 0o600)
        created_at = datetime.now(timezone.utc).isoformat()
        metadata = {
            "name": path.name,
            "created_at": created_at,
            "created_by": created_by,
            "database_vendor": vendor,
            "kind": kind,
            "size_bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        _write_metadata(path, metadata)
        return metadata
    except Exception:
        path.unlink(missing_ok=True)
        _metadata_path(path).unlink(missing_ok=True)
        raise


def create_backup(created_by=None, kind="manual"):
    with _operation_lock():
        return _create_backup(created_by=created_by, kind=kind)


def list_backups():
    backups = []

    for path in _backup_root().iterdir():
        if path.is_file() and BACKUP_NAME_PATTERN.fullmatch(path.name):
            metadata = _read_metadata(path)
            metadata.update(
                {
                    "name": path.name,
                    "size_bytes": path.stat().st_size,
                    "sha256": metadata.get("sha256") or _sha256(path),
                }
            )
            backups.append(metadata)

    return sorted(backups, key=lambda item: item.get("created_at", ""), reverse=True)


def get_backup_path(filename):
    if not BACKUP_NAME_PATTERN.fullmatch(filename or ""):
        raise BackupNotFoundError("Backup not found.")

    path = (_backup_root() / filename).resolve()

    if path.parent != _backup_root() or not path.is_file():
        raise BackupNotFoundError("Backup not found.")

    return path


def restore_backup(filename, restored_by=None):
    with _operation_lock():
        path = get_backup_path(filename)
        vendor, config = _database_config()
        expected_extension = ".dump" if vendor == "postgresql" else ".sqlite3"

        if path.suffix != expected_extension:
            raise BackupError("This backup does not match the active database engine.")

        safety_backup = _create_backup(
            created_by=restored_by,
            kind="pre_restore_safety",
        )

        connections.close_all()

        if vendor == "postgresql":
            command = [
                getattr(settings, "PG_RESTORE_BINARY", "pg_restore"),
                "--clean",
                "--if-exists",
                "--no-owner",
                "--no-privileges",
                "--exit-on-error",
                *_postgres_connection_arguments(config),
                "--dbname",
                str(config["NAME"]),
                str(path),
            ]
            _run_database_command(command, config)
        else:
            database_path = Path(config["NAME"]).resolve()

            with sqlite3.connect(path) as source:
                with sqlite3.connect(database_path) as destination:
                    source.backup(destination)

        connections.close_all()
        metadata = _read_metadata(path)
        metadata["last_restored_at"] = datetime.now(timezone.utc).isoformat()
        metadata["last_restored_by"] = restored_by
        _write_metadata(path, metadata)

        return {
            "backup": metadata,
            "safety_backup": safety_backup,
        }
