from __future__ import annotations

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from agent_flight_recorder.attributes import AFR_APP_NAME, AFR_ENVIRONMENT
from agent_flight_recorder.config import RecorderConfig

_provider: TracerProvider | None = None


def setup_telemetry(config: RecorderConfig) -> TracerProvider:
    global _provider

    resource = Resource.create(
        {
            "service.name": config.app_name,
            AFR_APP_NAME: config.app_name,
            AFR_ENVIRONMENT: config.environment,
            "deployment.environment": config.environment,
        }
    )
    provider = TracerProvider(resource=resource)
    headers: dict[str, str] | None = None
    if config.api_key:
        headers = {"Authorization": f"Bearer {config.api_key}"}

    exporter = OTLPSpanExporter(
        endpoint=f"{config.endpoint}/v1/traces",
        headers=headers,
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _provider = provider
    return provider


def get_tracer(name: str = "agent-flight-recorder") -> trace.Tracer:
    return trace.get_tracer(name)


def force_flush(timeout_millis: int = 5000) -> bool:
    if _provider is None:
        return True
    return _provider.force_flush(timeout_millis=timeout_millis)