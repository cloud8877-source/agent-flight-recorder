from __future__ import annotations

from pathlib import Path

import aiosqlite

from collector.paths import schema_path

DEFAULT_SCHEMA = schema_path("sqlite")


def database_path() -> str:
    import os

    return os.environ.get("AFR_DATABASE_PATH", "./data/afr.db")


async def init_sqlite(schema_path: Path | None = None) -> None:
    path = database_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    schema_file = schema_path or DEFAULT_SCHEMA
    schema_sql = schema_file.read_text(encoding="utf-8")
    async with aiosqlite.connect(path) as db:
        await db.executescript(schema_sql)
        await db.commit()


async def get_sqlite_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(database_path())
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    return db