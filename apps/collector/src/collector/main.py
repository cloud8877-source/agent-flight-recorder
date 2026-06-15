from __future__ import annotations

import json
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import uvicorn
import yaml
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from collector.db import get_db, init_db
from collector.eval import build_regression_test, load_eval_yaml, run_eval
from collector.models import EvalRunIn, ReplayCreateIn, TraceBatchIn
from collector.otlp import persist_otlp_spans
from collector.replay import build_snapshot, create_replay, get_replay, save_snapshot

REPO_ROOT = Path(__file__).resolve().parents[4]


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
async def list_runs(
    limit: int = 50,
    user_id: str | None = None,
    trace_id: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    db = await get_db()
    try:
        query = """
            SELECT id, trace_id, agent_name, user_id, session_id, environment,
                   status, started_at, ended_at, metrics_json
            FROM agent_runs
            WHERE 1=1
        """
        params: list[Any] = []
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        if trace_id:
            query += " AND trace_id = ?"
            params.append(trace_id)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)

        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            item = dict(row)
            if item.get("metrics_json"):
                item["metrics"] = json.loads(item["metrics_json"])
            results.append(item)
        return results
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
        FROM spans WHERE agent_run_id = ? ORDER BY started_at ASC
        """,
        (run_id,),
    )
    spans = await cursor.fetchall()

    cursor = await db.execute(
        """
        SELECT id, provider, model, input_tokens, output_tokens, cost_usd,
               latency_ms, started_at, ended_at
        FROM model_calls WHERE agent_run_id = ? ORDER BY started_at ASC
        """,
        (run_id,),
    )
    model_calls = await cursor.fetchall()

    cursor = await db.execute(
        """
        SELECT id, tool_name, tool_provider, status, risk_level, latency_ms,
               started_at, ended_at
        FROM tool_calls WHERE agent_run_id = ? ORDER BY started_at ASC
        """,
        (run_id,),
    )
    tool_calls = await cursor.fetchall()

    result = dict(run)
    if result.get("metrics_json"):
        result["metrics"] = json.loads(result["metrics_json"])
    result["spans"] = [
        {**dict(span), "attributes": json.loads(span["attributes_json"] or "{}")}
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


@app.post("/v1/runs/{run_id}/snapshot")
async def create_snapshot(run_id: str) -> dict[str, Any]:
    db = await get_db()
    try:
        run = await _fetch_run_detail(db, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run not found")
        snapshot = await build_snapshot(db, run_id, run)
        snapshot_id = await save_snapshot(db, run_id, snapshot)
        return {"snapshot_id": snapshot_id, "snapshot": snapshot}
    finally:
        await db.close()


@app.get("/v1/runs/{run_id}/regression-test")
async def regression_test(run_id: str) -> PlainTextResponse:
    db = await get_db()
    try:
        run = await _fetch_run_detail(db, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run not found")
        payload = build_regression_test(run)
        return PlainTextResponse(yaml.safe_dump(payload, sort_keys=False), media_type="text/yaml")
    finally:
        await db.close()


@app.post("/v1/replays")
async def create_replay_endpoint(body: ReplayCreateIn) -> dict[str, Any]:
    if body.mode not in {"exact", "model"}:
        raise HTTPException(status_code=400, detail="supported replay modes: exact, model")
    if body.mode == "model" and not body.model:
        raise HTTPException(status_code=400, detail="model replay requires model")

    db = await get_db()
    try:
        run = await _fetch_run_detail(db, body.source_agent_run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="source run not found")
        try:
            return await create_replay(
                db,
                body.source_agent_run_id,
                run,
                mode=body.mode,
                model=body.model,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        await db.close()


@app.get("/v1/replays/{replay_id}")
async def fetch_replay(replay_id: str) -> dict[str, Any]:
    db = await get_db()
    try:
        replay = await get_replay(db, replay_id)
        if replay is None:
            raise HTTPException(status_code=404, detail="replay not found")
        return replay
    finally:
        await db.close()


@app.post("/v1/evals/run")
async def run_eval_endpoint(body: EvalRunIn) -> dict[str, Any]:
    db = await get_db()
    try:
        run = await _fetch_run_detail(db, body.agent_run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run not found")

        if body.eval_yaml:
            eval_def = load_eval_yaml(body.eval_yaml)
        else:
            eval_path = REPO_ROOT / "examples/evals/refund_tool_correctness.yml"
            eval_def = load_eval_yaml(eval_path.read_text(encoding="utf-8"))

        result = run_eval(eval_def, run)
        eval_id = f"eval_{uuid.uuid4().hex[:12]}"
        await db.execute(
            """
            INSERT INTO eval_results (id, agent_run_id, evaluator_name, eval_type, score, passed, result_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                eval_id,
                body.agent_run_id,
                result["evaluator_name"],
                result["eval_type"],
                result["score"],
                1 if result["passed"] else 0,
                json.dumps(result),
            ),
        )
        await db.commit()
        return {"id": eval_id, **result}
    finally:
        await db.close()


@app.post("/v1/traces")
async def ingest_traces(request: Request) -> Response:
    content_type = request.headers.get("content-type", "")

    if "application/json" in content_type:
        batch = TraceBatchIn.model_validate(await request.json())
        db = await get_db()
        try:
            if batch.agent_run is not None:
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
                        batch.agent_run.id,
                        batch.agent_run.trace_id,
                        batch.agent_run.agent_name,
                        batch.agent_run.agent_version,
                        batch.agent_run.user_id,
                        batch.agent_run.session_id,
                        batch.agent_run.environment,
                        batch.agent_run.status,
                        batch.agent_run.started_at,
                        batch.agent_run.ended_at,
                        json.dumps(batch.agent_run.input) if batch.agent_run.input else None,
                        json.dumps(batch.agent_run.output) if batch.agent_run.output else None,
                        json.dumps(batch.agent_run.metrics) if batch.agent_run.metrics else None,
                    ),
                )
            for span in batch.spans:
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
            await db.commit()
            return Response(content=json.dumps({"status": "accepted"}), media_type="application/json")
        finally:
            await db.close()

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
    return {"status": "accepted"}


@app.post("/v1/events")
async def ingest_events(batch: TraceBatchIn) -> dict[str, str]:
    return {"status": "accepted"}


def main() -> None:
    host = os.environ.get("AFR_HOST", "0.0.0.0")
    port = int(os.environ.get("AFR_PORT", "4318"))
    uvicorn.run("collector.main:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    main()