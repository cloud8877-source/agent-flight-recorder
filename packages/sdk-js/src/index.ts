export type RecorderConfig = {
  appName: string;
  environment: string;
  endpoint: string;
  apiKey?: string;
};

export type AgentRunOptions = {
  name: string;
  userId?: string;
  sessionId?: string;
};

let config: RecorderConfig | null = null;

export function init(options: {
  appName: string;
  environment?: string;
  endpoint?: string;
  apiKey?: string;
}): void {
  config = {
    appName: options.appName,
    environment: options.environment ?? process.env.AFR_ENVIRONMENT ?? "development",
    endpoint: (options.endpoint ?? process.env.AFR_ENDPOINT ?? "http://localhost:4318").replace(/\/$/, ""),
    apiKey: options.apiKey ?? process.env.AFR_API_KEY,
  };
}

function requireConfig(): RecorderConfig {
  if (!config) {
    throw new Error("recorder.init() must be called before agentRun()");
  }
  return config;
}

function now(): string {
  return new Date().toISOString();
}

function id(prefix: string): string {
  return `${prefix}_${crypto.randomUUID().replace(/-/g, "").slice(0, 12)}`;
}

export async function agentRun<T>(
  options: AgentRunOptions,
  fn: () => Promise<T>,
): Promise<T> {
  const cfg = requireConfig();
  const runId = id("run");
  const traceId = id("trace");
  const startedAt = now();

  const payload: {
    agent_run: {
      id: string;
      trace_id: string;
      agent_name: string;
      user_id?: string;
      session_id?: string;
      environment: string;
      status: string;
      started_at: string;
      ended_at?: string;
      output?: Record<string, unknown>;
    };
    spans: Array<Record<string, unknown>>;
  } = {
    agent_run: {
      id: runId,
      trace_id: traceId,
      agent_name: options.name,
      user_id: options.userId,
      session_id: options.sessionId,
      environment: cfg.environment,
      status: "running",
      started_at: startedAt,
    },
    spans: [
      {
        id: id("span"),
        agent_run_id: runId,
        span_id: crypto.randomUUID().replace(/-/g, "").slice(0, 16),
        span_type: "agent.run",
        name: options.name,
        status: "ok",
        started_at: startedAt,
        ended_at: now(),
        attributes: { "afr.app_name": cfg.appName },
      },
    ],
  };

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (cfg.apiKey) headers.Authorization = `Bearer ${cfg.apiKey}`;

  try {
    const result = await fn();
    payload.agent_run.status = "success";
    payload.agent_run.ended_at = now();
    payload.agent_run.output = { value: result };
    await fetch(`${cfg.endpoint}/v1/traces`, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });
    return result;
  } catch (error) {
    payload.agent_run.status = "failed";
    payload.agent_run.ended_at = now();
    payload.agent_run.output = { error: String(error) };
    await fetch(`${cfg.endpoint}/v1/traces`, {
      method: "POST",
      headers,
      body: JSON.stringify(payload),
    });
    throw error;
  }
}