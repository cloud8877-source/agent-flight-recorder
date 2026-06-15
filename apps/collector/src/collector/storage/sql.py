from __future__ import annotations

import re
from datetime import datetime
from typing import Any


def coerce_postgres_params(params: tuple | list) -> list[Any]:
    coerced: list[Any] = []
    for value in params:
        if isinstance(value, str):
            coerced.append(_parse_iso_timestamp(value))
        else:
            coerced.append(value)
    return coerced


_ISO_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


def _parse_iso_timestamp(value: str) -> datetime | str:
    if not _ISO_TIMESTAMP.match(value):
        return value
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value


def convert_placeholders(query: str, params: tuple | list) -> tuple[str, list]:
    if "?" not in query:
        return query, list(params)
    parts = query.split("?")
    converted: list[str] = []
    for index, part in enumerate(parts[:-1]):
        converted.append(part)
        converted.append(f"${index + 1}")
    converted.append(parts[-1])
    return "".join(converted), list(params)


def adapt_query(query: str, backend: str) -> str:
    if backend == "sqlite":
        return query
    adapted = query.replace("INSERT OR REPLACE", "INSERT")
    if "ON CONFLICT" not in adapted:
        adapted = _add_upsert_clause(adapted)
    return adapted


def _add_upsert_clause(query: str) -> str:
    match = re.search(
        r"INSERT INTO (\w+)\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)",
        query,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match is None:
        return query

    table = match.group(1)
    columns = [part.strip() for part in match.group(2).split(",")]
    pk = columns[0]
    updates = ", ".join(f"{column}=EXCLUDED.{column}" for column in columns if column != pk)
    return f"{query.strip()}\nON CONFLICT ({pk}) DO UPDATE SET {updates}"