# Third-Party Trace Exporters

Agent Flight Recorder can forward OTLP traces to external observability platforms on ingest.

## Generic OTLP forward

```bash
export AFR_OTLP_EXPORT_ENDPOINT=https://your-collector.example/v1/traces
make collector
```

## Langfuse

Langfuse accepts OpenTelemetry traces at its public OTLP endpoint.

```bash
export LANGFUSE_HOST=https://cloud.langfuse.com
export LANGFUSE_PUBLIC_KEY=pk-lf-...
export LANGFUSE_SECRET_KEY=sk-lf-...
make collector
```

Traces ingested via `POST /v1/traces` are forwarded automatically.

## Phoenix (Arize)

```bash
export PHOENIX_OTLP_ENDPOINT=http://localhost:6006/v1/traces
make collector
```

See [Arize Phoenix OTLP docs](https://docs.arize.com/phoenix) for local server setup.

## Verify export targets

```bash
curl http://localhost:4318/v1/storage
```

Response includes `export_targets` when exporters are configured.