"""Load standalone operator scripts without adding them to the application package."""

from __future__ import annotations

import importlib.util
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]


def load_script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


bundle = load_script("backup_bundle")
postgres = load_script("backup_postgres")
backup = load_script("backup")
restore = load_script("restore")


def create_project(root: Path) -> Path:
    root.mkdir()
    (root / ".env.example").write_text("ASE_ENV=dev\n", encoding="utf-8")
    (root / ".env").write_text("ASE_ENCRYPTION_KEY=private-fixture\n", encoding="utf-8")
    (root / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
    (root / "live-cache.json").write_text('{"events": ["do not persist"]}', encoding="utf-8")
    database_path = root / "ase.db"
    with closing(sqlite3.connect(database_path)) as database:
        database.executescript(
            "CREATE TABLE reports (id TEXT PRIMARY KEY, title TEXT);"
            "INSERT INTO reports VALUES ('r1', 'Country brief');"
            "CREATE TABLE evidence (report_id TEXT, title TEXT);"
            "INSERT INTO evidence VALUES ('r1', 'Frozen source');"
            "CREATE TABLE configuration (name TEXT, value TEXT);"
            "INSERT INTO configuration VALUES ('model', 'local-model');"
        )
    return database_path


def create_backup(root: Path, destination: Path, *, secrets: bool = False) -> int:
    arguments = [
        "sqlite",
        "--database",
        str(root / "ase.db"),
        "--output",
        str(destination),
        "--project-root",
        str(root),
    ]
    if secrets:
        arguments.append("--include-secrets")
    return backup.main(arguments)
