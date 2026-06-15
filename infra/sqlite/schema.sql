-- Agent Flight Recorder SQLite schema v1 (local development mode)
-- See ADR-002 (stub) and ADR-001 Section 9.5

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS environments (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id),
  name TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agents (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id),
  name TEXT NOT NULL,
  version TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent_runs (
  id TEXT PRIMARY KEY,
  agent_id TEXT REFERENCES agents(id),
  trace_id TEXT NOT NULL,
  agent_name TEXT NOT NULL,
  agent_version TEXT,
  user_id TEXT,
  session_id TEXT,
  environment TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'success', 'failed')),
  started_at TEXT NOT NULL,
  ended_at TEXT,
  input_json TEXT,
  output_json TEXT,
  metrics_json TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS spans (
  id TEXT PRIMARY KEY,
  agent_run_id TEXT NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
  span_id TEXT NOT NULL,
  parent_span_id TEXT,
  span_type TEXT NOT NULL,
  name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'ok' CHECK (status IN ('ok', 'error')),
  started_at TEXT NOT NULL,
  ended_at TEXT,
  attributes_json TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS model_calls (
  id TEXT PRIMARY KEY,
  agent_run_id TEXT NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
  span_id TEXT,
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  input_tokens INTEGER,
  output_tokens INTEGER,
  cost_usd REAL,
  latency_ms INTEGER,
  started_at TEXT NOT NULL,
  ended_at TEXT,
  attributes_json TEXT
);

CREATE TABLE IF NOT EXISTS tool_calls (
  id TEXT PRIMARY KEY,
  agent_run_id TEXT NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
  span_id TEXT,
  tool_name TEXT NOT NULL,
  tool_provider TEXT,
  status TEXT NOT NULL DEFAULT 'success',
  risk_level TEXT,
  latency_ms INTEGER,
  started_at TEXT NOT NULL,
  ended_at TEXT,
  arguments_json TEXT,
  result_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_trace_id ON agent_runs(trace_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_user_id ON agent_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_started_at ON agent_runs(started_at);
CREATE INDEX IF NOT EXISTS idx_spans_agent_run_id ON spans(agent_run_id);
CREATE INDEX IF NOT EXISTS idx_model_calls_agent_run_id ON model_calls(agent_run_id);
CREATE INDEX IF NOT EXISTS idx_tool_calls_agent_run_id ON tool_calls(agent_run_id);

-- Default local project for development
INSERT OR IGNORE INTO projects (id, name) VALUES ('proj_local', 'local');
INSERT OR IGNORE INTO environments (id, project_id, name) VALUES ('env_dev', 'proj_local', 'development');