#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VENV="${ROOT}/.venv"
PYTHON="${VENV}/bin/python"
DB="${ROOT}/data/afr.db"
API="http://127.0.0.1:4318"

mkdir -p data
AFR_DATABASE_PATH="$DB" "$PYTHON" -c "import asyncio; from collector.db import init_db; asyncio.run(init_db())"

lsof -ti :4318 | xargs kill -9 2>/dev/null || true
AFR_DATABASE_PATH="$DB" "$VENV/bin/uvicorn" collector.main:app \
  --app-dir apps/collector/src --host 127.0.0.1 --port 4318 &
COLLECTOR_PID=$!
trap 'kill $COLLECTOR_PID 2>/dev/null || true' EXIT

sleep 2
curl -sf "$API/health" >/dev/null

rm -f "$DB"
AFR_DATABASE_PATH="$DB" "$PYTHON" -c "import asyncio; from collector.db import init_db; asyncio.run(init_db())"

AFR_ENDPOINT="$API" "$PYTHON" examples/support-refund-agent/main.py

RUNS="$(curl -sf "$API/v1/runs")"
echo "$RUNS" | "$PYTHON" -c "import sys,json; d=json.load(sys.stdin); assert len(d)>=1, 'no runs'"

RUN_ID="$(echo "$RUNS" | "$PYTHON" -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")"

curl -sf "$API/v1/runs/$RUN_ID" | "$PYTHON" -c "import sys,json; r=json.load(sys.stdin); assert len(r['spans'])>=3"
curl -sf "$API/v1/runs?user_id=user_123" | "$PYTHON" -c "import sys,json; assert len(json.load(sys.stdin))>=1"

REPLAY="$(curl -sf -X POST "$API/v1/replays" -H 'Content-Type: application/json' -d "{\"source_agent_run_id\":\"$RUN_ID\",\"mode\":\"exact\"}")"
echo "$REPLAY" | "$PYTHON" -c "import sys,json; d=json.load(sys.stdin); assert d['mode']=='exact'"

EVAL="$(curl -sf -X POST "$API/v1/evals/run" -H 'Content-Type: application/json' -d "{\"agent_run_id\":\"$RUN_ID\"}")"
echo "$EVAL" | "$PYTHON" -c "import sys,json; d=json.load(sys.stdin); assert d['passed'] is True, d"

curl -sf "$API/v1/runs/$RUN_ID/regression-test" | grep -q "refund_agent_regression"

AFR="${VENV}/bin/afr"
AFR_ENDPOINT="$API" "$AFR" replay "$RUN_ID" --model gpt-4.1-mini | grep -q "replay_"
AFR_ENDPOINT="$API" "$AFR" eval run examples/evals/refund_tool_correctness.yml --run-id "$RUN_ID" | grep -q "passed=True"

echo "e2e passed"