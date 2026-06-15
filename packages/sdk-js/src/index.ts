import { context, trace, SpanStatusCode, type Span } from "@opentelemetry/api";
import {
  AFR_AGENT_NAME,
  AFR_APP_NAME,
  AFR_ENVIRONMENT,
  AFR_RUN_ID,
  AFR_SESSION_ID,
  AFR_SPAN_TYPE,
} from "./attributes.js";
import { getConfig, loadFromEnv, setConfig, type RecorderConfig } from "./config.js";
import { forceFlush, getTracer, setupTelemetry } from "./telemetry.js";

export type AgentRunOptions = {
  name: string;
  userId?: string;
  sessionId?: string;
};

export class AgentRun {
  readonly id: string;
  readonly traceId: string | undefined;
  readonly name: string;
  readonly userId?: string;
  readonly sessionId?: string;

  constructor(options: {
    id: string;
    traceId?: string;
    name: string;
    userId?: string;
    sessionId?: string;
  }) {
    this.id = options.id;
    this.traceId = options.traceId;
    this.name = options.name;
    this.userId = options.userId;
    this.sessionId = options.sessionId;
  }

  span(
    name: string,
    spanType: string,
    attributes: Record<string, string | number | boolean> = {},
  ): SpanRecorder {
    return new SpanRecorder(this, name, spanType, attributes);
  }
}

export class SpanRecorder {
  private span: Span | null = null;
  private ctx = context.active();

  constructor(
    private readonly run: AgentRun,
    private readonly name: string,
    private readonly spanType: string,
    private readonly attributes: Record<string, string | number | boolean>,
  ) {}

  setAttribute(key: string, value: string | number | boolean): void {
    this.span?.setAttribute(key, value);
  }

  start(): this {
    const cfg = getConfig();
    const tracer = getTracer();
    const attrs: Record<string, string | number | boolean> = {
      [AFR_SPAN_TYPE]: this.spanType,
      [AFR_RUN_ID]: this.run.id,
      [AFR_AGENT_NAME]: this.run.name,
      [AFR_APP_NAME]: cfg.appName,
      [AFR_ENVIRONMENT]: cfg.environment,
      ...this.attributes,
    };
    if (this.run.userId) attrs["enduser.id"] = this.run.userId;
    if (this.run.sessionId) attrs[AFR_SESSION_ID] = this.run.sessionId;

    this.span = tracer.startSpan(this.name, { attributes: attrs }, this.ctx);
    this.ctx = trace.setSpan(this.ctx, this.span);
    return this;
  }

  end(error?: unknown): void {
    if (!this.span) return;
    if (error) {
      this.span.recordException(error instanceof Error ? error : new Error(String(error)));
      this.span.setStatus({ code: SpanStatusCode.ERROR, message: String(error) });
    }
    this.span.end();
    this.span = null;
  }
}

export function init(options: {
  appName: string;
  environment?: string;
  endpoint?: string;
  apiKey?: string;
}): void {
  const cfg: RecorderConfig = {
    ...loadFromEnv(options.appName, options.environment ?? process.env.AFR_ENVIRONMENT ?? "development"),
    appName: options.appName,
    environment: options.environment ?? process.env.AFR_ENVIRONMENT ?? "development",
    endpoint: (options.endpoint ?? process.env.AFR_ENDPOINT ?? "http://localhost:4318").replace(/\/$/, ""),
    apiKey: options.apiKey ?? process.env.AFR_API_KEY,
  };
  setConfig(cfg);
  setupTelemetry(cfg);
}

function runId(): string {
  return `run_${crypto.randomUUID().replace(/-/g, "").slice(0, 12)}`;
}

export async function agentRun<T>(
  options: AgentRunOptions,
  fn: (run: AgentRun) => Promise<T>,
): Promise<T> {
  const cfg = getConfig();
  const tracer = getTracer();
  const id = runId();

  const rootAttrs: Record<string, string> = {
    [AFR_SPAN_TYPE]: "agent.run",
    [AFR_RUN_ID]: id,
    [AFR_AGENT_NAME]: options.name,
    [AFR_APP_NAME]: cfg.appName,
    [AFR_ENVIRONMENT]: cfg.environment,
  };
  if (options.userId) rootAttrs["enduser.id"] = options.userId;
  if (options.sessionId) rootAttrs[AFR_SESSION_ID] = options.sessionId;

  return tracer.startActiveSpan(options.name, { attributes: rootAttrs }, async (rootSpan) => {
    const traceId = rootSpan.spanContext().traceId;
    const run = new AgentRun({
      id,
      traceId,
      name: options.name,
      userId: options.userId,
      sessionId: options.sessionId,
    });

    try {
      const result = await fn(run);
      rootSpan.setStatus({ code: SpanStatusCode.OK });
      return result;
    } catch (error) {
      rootSpan.recordException(error instanceof Error ? error : new Error(String(error)));
      rootSpan.setStatus({ code: SpanStatusCode.ERROR, message: String(error) });
      throw error;
    } finally {
      rootSpan.end();
      await forceFlush();
    }
  });
}