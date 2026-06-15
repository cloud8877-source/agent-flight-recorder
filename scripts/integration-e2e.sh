#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VENV="${ROOT}/.venv"
PYTHON="${VENV}/bin/python"
API="http://127.0.0.1:4318"
DB="${ROOT}/data/integration-e2e.db"
PID=""

cleanup() {
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    kill "$PID" 2>/dev/null || true
    wait "$PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

mkdir -p data
rm -f "$DB"
AFR_DATABASE_PATH="$DB" "$PYTHON" -c "import asyncio; from collector.db import init_db; asyncio.run(init_db())"

AFR_DATABASE_PATH="$DB" "$VENV/bin/uvicorn" collector.main:app \
  --app-dir apps/collector/src --host 127.0.0.1 --port 4318 &
PID=$!

for _ in $(seq 1 30); do
  if curl -sf "$API/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
curl -sf "$API/health" >/dev/null

AFR_ENDPOINT="$API" "$PYTHON" examples/langgraph-refund-agent/main.py >/dev/null
AFR_ENDPOINT="$API" "$PYTHON" examples/openai-agents-refund-agent/main.py >/dev/null

DASHBOARD="$(curl -sf "$API/v1/dashboard")"
echo "$DASHBOARD" | "$PYTHON" -c "import sys,json; d=json.load(sys.stdin); assert d['total_runs']>=2, d"

RUNS="$(curl -sf "$API/v1/runs")"
echo "$RUNS" | "$PYTHON" -c "import sys,json; runs=json.load(sys.stdin); names={r['agent_name'] for r in runs}; assert 'langgraph-refund-agent' in names; assert 'openai-agents-refund-agent' in names"

echo "integration e2e passed"