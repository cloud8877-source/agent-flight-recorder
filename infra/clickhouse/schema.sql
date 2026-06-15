CREATE TABLE IF NOT EXISTS span_events (
  trace_id String,
  agent_run_id String,
  span_id String,
  span_type String,
  name String,
  status String,
  agent_name String,
  environment String,
  started_at DateTime64(3, 'UTC'),
  ended_at Nullable(DateTime64(3, 'UTC')),
  latency_ms Nullable(Int32),
  input_tokens Nullable(UInt32),
  output_tokens Nullable(UInt32),
  cost_usd Nullable(Float64),
  attributes String,
  ingested_at DateTime64(3, 'UTC') DEFAULT now64(3)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(started_at)
ORDER BY (trace_id, started_at, span_id);