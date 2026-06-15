# Support Refund Agent (demo)

Minimal demo agent for Phase 1. Records model and tool spans to the local collector.

## Run locally

```bash
# Terminal 1 — collector
cd apps/collector
pip install -e .
AFR_DATABASE_PATH=../../data/afr.db afr-collector

# Terminal 2 — demo agent
pip install -e ../../packages/sdk-python
export AFR_ENDPOINT=http://localhost:4318
python main.py
```

Then open http://localhost:3000 (with web dev server running) to view the trace.