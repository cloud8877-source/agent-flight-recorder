from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from collector.storage import storage_backend  # noqa: E402


def storage_info() -> dict[str, Any]:
    backend = storage_backend()
    info: dict[str, Any] = {
        "backend": backend,
        "clickhouse_enabled": bool(os.environ.get("AFR_CLICKHOUSE_URL")),
        "object_storage_enabled": bool(os.environ.get("AFR_OBJECT_STORAGE_ENDPOINT")),
        "otlp_export_enabled": bool(os.environ.get("AFR_OTLP_EXPORT_ENDPOINT")),
    }
    if backend == "postgres":
        info["database_url_configured"] = bool(os.environ.get("AFR_DATABASE_URL"))
    else:
        info["database_path"] = os.environ.get("AFR_DATABASE_PATH", "./data/afr.db")
    return info


async def init_db(schema_path: Path | None = None) -> None:
    if storage_backend() == "postgres":
        from collector.storage.postgres_backend import init_postgres

        await init_postgres(schema_path)
        return

    from collector.storage.sqlite_backend import init_sqlite

    await init_sqlite(schema_path)


async def get_db() -> Any:
    if storage_backend() == "postgres":
        from collector.storage.postgres_backend import get_postgres_db

        return await get_postgres_db()

    from collector.storage.sqlite_backend import get_sqlite_db

    return await get_sqlite_db()