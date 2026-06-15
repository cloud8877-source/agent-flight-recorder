from __future__ import annotations

import os
from pathlib import Path

import aiosqlite

DEFAULT_SCHEMA = Path(__file__).resolve().parents[4] / "infra" / "sqlite" / "schema.sql"


def database_path() -> str:
    return os.environ.get("AFR_DATABASE_PATH", "./data/afr.db")


async def init_db(schema_path: Path | None = None) -> None:
    path = database_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    schema_file = schema_path or DEFAULT_SCHEMA
    schema_sql = schema_file.read_text(encoding="utf-8")
    async with aiosqlite.connect(path) as db:
        await db.executescript(schema_sql)
        await db.commit()


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(database_path())
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    return db