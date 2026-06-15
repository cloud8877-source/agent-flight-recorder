import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
import { resourceFromAttributes } from "@opentelemetry/resources";
import { BatchSpanProcessor } from "@opentelemetry/sdk-trace-base";
import { NodeTracerProvider } from "@opentelemetry/sdk-trace-node";
import { trace, type Tracer } from "@opentelemetry/api";
import { AFR_APP_NAME, AFR_ENVIRONMENT } from "./attributes.js";
import type { RecorderConfig } from "./config.js";

let provider: NodeTracerProvider | null = null;

export function setupTelemetry(config: RecorderConfig): NodeTracerProvider {
  const headers: Record<string, string> = {};
  if (config.apiKey) {
    headers.Authorization = `Bearer ${config.apiKey}`;
  }

  const nextProvider = new NodeTracerProvider({
    resource: resourceFromAttributes({
      "service.name": config.appName,
      [AFR_APP_NAME]: config.appName,
      [AFR_ENVIRONMENT]: config.environment,
      "deployment.environment": config.environment,
    }),
    spanProcessors: [
      new BatchSpanProcessor(
        new OTLPTraceExporter({
          url: `${config.endpoint}/v1/traces`,
          headers,
        }),
      ),
    ],
  });

  nextProvider.register();
  provider = nextProvider;
  return nextProvider;
}

export function getTracer(name = "agent-flight-recorder"): Tracer {
  return trace.getTracer(name);
}

export async function forceFlush(): Promise<void> {
  if (provider) {
    await provider.forceFlush();
  }
}