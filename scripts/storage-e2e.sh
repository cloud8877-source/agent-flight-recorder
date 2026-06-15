#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker not available; skipping storage e2e"
  exit 0
fi

VENV="${ROOT}/.venv"
PYTHON="${VENV}/bin/python"
API="http://127.0.0.1:4318"
CH="http://afr:afr@127.0.0.1:8123"

docker compose -f infra/docker-compose.prod.yml up -d --build postgres clickhouse minio minio-init collector
trap 'docker compose -f infra/docker-compose.prod.yml down -v' EXIT

for _ in $(seq 1 60); do
  if curl -sf "$API/health" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
curl -sf "$API/health" >/dev/null

curl -sf "${CH}/ping" >/dev/null
curl -sf "${CH}/" --data-binary @"infra/clickhouse/schema.sql" >/dev/null

STORAGE="$(curl -sf "$API/v1/storage")"
echo "$STORAGE" | "$PYTHON" -c "import sys,json; d=json.load(sys.stdin); assert d['backend']=='postgres', d; assert d['clickhouse_enabled'] is True"

AFR_ENDPOINT="$API" "$PYTHON" examples/support-refund-agent/main.py

RUNS="$(curl -sf "$API/v1/runs")"
echo "$RUNS" | "$PYTHON" -c "import sys,json; assert len(json.load(sys.stdin))>=1"

TRACE_ID="$(echo "$RUNS" | "$PYTHON" -c "import sys,json; print(json.load(sys.stdin)[0]['trace_id'])")"
CH_COUNT=0
for _ in $(seq 1 15); do
  CH_COUNT="$(curl -sf "${CH}/?query=SELECT%20count()%20FROM%20span_events%20WHERE%20trace_id%3D%27${TRACE_ID}%27%20FORMAT%20JSON" | "$PYTHON" -c "import sys,json; print(json.load(sys.stdin)['data'][0]['count()'])")"
  if [ "$CH_COUNT" -ge 3 ]; then
    break
  fi
  sleep 1
done
[ "$CH_COUNT" -ge 3 ]

echo "storage e2e passed"