from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import asyncpg

from collector.paths import schema_path
from collector.storage.sql import adapt_query, coerce_postgres_params, convert_placeholders

DEFAULT_SCHEMA = schema_path("postgres")


def _split_sql(schema_sql: str) -> list[str]:
    statements: list[str] = []
    for chunk in schema_sql.split(";"):
        statement = chunk.strip()
        if statement:
            statements.append(statement)
    return statements

_pool: asyncpg.Pool | None = None


class PostgresCursor:
    def __init__(self, rows: list[asyncpg.Record] | None = None) -> None:
        self._rows = rows or []
        self._index = 0

    async def fetchone(self) -> asyncpg.Record | None:
        if self._index >= len(self._rows):
            return None
        row = self._rows[self._index]
        self._index += 1
        return row

    async def fetchall(self) -> list[asyncpg.Record]:
        if self._index == 0:
            self._index = len(self._rows)
            return self._rows
        remaining = self._rows[self._index :]
        self._index = len(self._rows)
        return remaining


class PostgresDB:
    def __init__(self, conn: asyncpg.Connection, pool: asyncpg.Pool) -> None:
        self._conn = conn
        self._pool = pool
        self._tx = conn.transaction()
        self._tx_started = False

    async def _ensure_tx(self) -> None:
        if not self._tx_started:
            await self._tx.start()
            self._tx_started = True

    async def execute(self, query: str, params: tuple | list = ()) -> PostgresCursor:
        await self._ensure_tx()
        adapted = adapt_query(query, "postgres")
        sql, values = convert_placeholders(adapted, params)
        values = coerce_postgres_params(values)
        normalized = sql.strip().upper()
        if normalized.startswith("SELECT") or " RETURNING " in normalized:
            rows = await self._conn.fetch(sql, *values)
            return PostgresCursor(rows)
        await self._conn.execute(sql, *values)
        return PostgresCursor([])

    async def commit(self) -> None:
        if self._tx_started:
            await self._tx.commit()
            self._tx_started = False

    async def close(self) -> None:
        if self._tx_started:
            await self._tx.rollback()
            self._tx_started = False
        await self._pool.release(self._conn)


def database_url() -> str:
    url = os.environ.get("AFR_DATABASE_URL")
    if not url:
        raise RuntimeError("AFR_DATABASE_URL is required when AFR_STORAGE_BACKEND=postgres")
    return url


async def init_postgres(schema_path: Path | None = None) -> None:
    global _pool
    schema_file = schema_path or DEFAULT_SCHEMA
    schema_sql = schema_file.read_text(encoding="utf-8")
    _pool = await asyncpg.create_pool(database_url(), min_size=1, max_size=10)
    assert _pool is not None
    async with _pool.acquire() as conn:
        for statement in _split_sql(schema_sql):
            await conn.execute(statement)


async def get_postgres_db() -> PostgresDB:
    if _pool is None:
        await init_postgres()
    assert _pool is not None
    conn = await _pool.acquire()
    return PostgresDB(conn, _pool)


async def close_postgres_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None