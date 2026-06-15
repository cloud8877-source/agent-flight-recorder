#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VENV="${ROOT}/.venv"
PYTHON="${VENV}/bin/python"
AFR="${VENV}/bin/afr"
DB="${ROOT}/data/afr-regression.db"
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

AFR_ENDPOINT="$API" "$AFR" test examples/afr-tests/

RUN_ID="$(curl -sf "$API/v1/runs" | "$PYTHON" -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")"
REPLAY="$(AFR_ENDPOINT="$API" "$AFR" replay "$RUN_ID" --model gpt-4.1-mini)"
echo "$REPLAY" | grep -q "replay_"

echo "regression passed"