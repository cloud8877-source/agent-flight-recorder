#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VENV="${ROOT}/.venv"
PYTHON="${VENV}/bin/python"
AFR="${VENV}/bin/afr"
DB="${ROOT}/data/afr-policy.db"
API="http://127.0.0.1:4318"

mkdir -p data
rm -f "$DB"
AFR_DATABASE_PATH="$DB" "$PYTHON" -c "import asyncio; from collector.db import init_db; asyncio.run(init_db())"

lsof -ti :4318 | xargs kill -9 2>/dev/null || true
AFR_DATABASE_PATH="$DB" "$VENV/bin/uvicorn" collector.main:app \
  --app-dir apps/collector/src --host 127.0.0.1 --port 4318 &
COLLECTOR_PID=$!
trap 'kill $COLLECTOR_PID 2>/dev/null || true' EXIT

sleep 2
curl -sf "$API/health" >/dev/null

POLICIES="$(curl -sf "$API/v1/policies")"
echo "$POLICIES" | "$PYTHON" -c "import sys,json; d=json.load(sys.stdin); assert len(d)>=2, d"

AFR_ENDPOINT="$API" "$PYTHON" examples/support-refund-agent/policy_violation.py

RUN_ID="$(curl -sf "$API/v1/runs" | "$PYTHON" -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")"
VIOLATIONS="$(curl -sf "$API/v1/runs/$RUN_ID/violations")"
echo "$VIOLATIONS" | "$PYTHON" -c "
import sys, json
items = json.load(sys.stdin)
actions = {v['action'] for v in items}
assert 'require_approval' in actions, items
assert any(v['tool_name'] == 'refund_payment' for v in items), items
"

RUN="$(curl -sf "$API/v1/runs/$RUN_ID")"
echo "$RUN" | "$PYTHON" -c "import sys,json; r=json.load(sys.stdin); assert r['status']=='failed'"

if AFR_ENDPOINT="$API" "$AFR" policy check "$RUN_ID" >/dev/null; then
  echo "expected policy check to exit 1 when violations exist"
  exit 1
fi

AFR_ENDPOINT="$API" "$PYTHON" examples/support-refund-agent/main.py
GOOD_ID="$(curl -sf "$API/v1/runs?user_id=user_123" | "$PYTHON" -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")"
GOOD_VIOLATIONS="$(curl -sf "$API/v1/runs/$GOOD_ID/violations")"
echo "$GOOD_VIOLATIONS" | "$PYTHON" -c "import sys,json; assert len(json.load(sys.stdin))==0"

echo "policy e2e passed"