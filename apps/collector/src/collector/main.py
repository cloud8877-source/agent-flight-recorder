from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from collector.db import get_db, init_db
from collector.models import AgentRunIn, SpanIn, TraceBatchIn
from collector.otlp import persist_otlp_spans


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Agent Flight Recorder Collector",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/runs")
async def list_runs(limit: int = 50) -> list[dict[str, Any]]:
    db = await get_db()
    try:
        cursor = await db.execute(
            """
            SELECT id, trace_id, agent_name, user_id, session_id, environment,
                   status, started_at, ended_at
            FROM agent_runs
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def _fetch_run_detail(db: Any, run_id: str) -> dict[str, Any] | None:
    cursor = await db.execute("SELECT * FROM agent_runs WHERE id = ?", (run_id,))
    run = await cursor.fetchone()
    if run is None:
        return None

    cursor = await db.execute(
        """
        SELECT id, span_id, parent_span_id, span_type, name, status,
               started_at, ended_at, attributes_json
        FROM spans
        WHERE agent_run_id = ?
        ORDER BY started_at ASC
        """,
        (run_id,),
    )
    spans = await cursor.fetchall()

    cursor = await db.execute(
        """
        SELECT id, provider, model, input_tokens, output_tokens, cost_usd,
               latency_ms, started_at, ended_at
        FROM model_calls
        WHERE agent_run_id = ?
        ORDER BY started_at ASC
        """,
        (run_id,),
    )
    model_calls = await cursor.fetchall()

    cursor = await db.execute(
        """
        SELECT id, tool_name, tool_provider, status, risk_level, latency_ms,
               started_at, ended_at
        FROM tool_calls
        WHERE agent_run_id = ?
        ORDER BY started_at ASC
        """,
        (run_id,),
    )
    tool_calls = await cursor.fetchall()

    result = dict(run)
    result["spans"] = [
        {
            **dict(span),
            "attributes": json.loads(span["attributes_json"] or "{}"),
        }
        for span in spans
    ]
    result["model_calls"] = [dict(row) for row in model_calls]
    result["tool_calls"] = [dict(row) for row in tool_calls]
    return result


@app.get("/v1/runs/{run_id}")
async def get_run(run_id: str) -> dict[str, Any]:
    db = await get_db()
    try:
        result = await _fetch_run_detail(db, run_id)
        if result is None:
            raise HTTPException(status_code=404, detail="run not found")
        return result
    finally:
        await db.close()


async def _upsert_agent_run(db: Any, run: AgentRunIn) -> None:
    await db.execute(
        """
        INSERT INTO agent_runs (
            id, trace_id, agent_name, agent_version, user_id, session_id,
            environment, status, started_at, ended_at, input_json, output_json, metrics_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            status = excluded.status,
            ended_at = excluded.ended_at,
            output_json = excluded.output_json,
            metrics_json = excluded.metrics_json
        """,
        (
            run.id,
            run.trace_id,
            run.agent_name,
            run.agent_version,
            run.user_id,
            run.session_id,
            run.environment,
            run.status,
            run.started_at,
            run.ended_at,
            json.dumps(run.input) if run.input is not None else None,
            json.dumps(run.output) if run.output is not None else None,
            json.dumps(run.metrics) if run.metrics is not None else None,
        ),
    )


async def _insert_span(db: Any, span: SpanIn) -> None:
    await db.execute(
        """
        INSERT OR REPLACE INTO spans (
            id, agent_run_id, span_id, parent_span_id, span_type, name,
            status, started_at, ended_at, attributes_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            span.id,
            span.agent_run_id,
            span.span_id,
            span.parent_span_id,
            span.span_type,
            span.name,
            span.status,
            span.started_at,
            span.ended_at,
            json.dumps(span.attributes),
        ),
    )


async def _ingest_native_batch(batch: TraceBatchIn) -> dict[str, str]:
    db = await get_db()
    try:
        if batch.agent_run is not None:
            await _upsert_agent_run(db, batch.agent_run)
        for span in batch.spans:
            await _insert_span(db, span)
        await db.commit()
        return {"status": "accepted"}
    finally:
        await db.close()


@app.post("/v1/traces")
async def ingest_traces(request: Request) -> Response:
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        batch = TraceBatchIn.model_validate(await request.json())
        result = await _ingest_native_batch(batch)
        return Response(content=json.dumps(result), media_type="application/json")

    body = await request.body()
    db = await get_db()
    try:
        try:
            count = await persist_otlp_spans(db, body)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"invalid OTLP payload: {exc}") from exc
        return Response(status_code=200, content=json.dumps({"spans_stored": count}))
    finally:
        await db.close()


@app.post("/v1/afr/traces")
async def ingest_native_traces(batch: TraceBatchIn) -> dict[str, str]:
    """Legacy native JSON batch format (pre-OTel SDK clients)."""
    return await _ingest_native_batch(batch)


@app.post("/v1/events")
async def ingest_events(batch: TraceBatchIn) -> dict[str, str]:
    return await _ingest_native_batch(batch)


def main() -> None:
    host = os.environ.get("AFR_HOST", "0.0.0.0")
    port = int(os.environ.get("AFR_PORT", "4318"))
    uvicorn.run("collector.main:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    main()