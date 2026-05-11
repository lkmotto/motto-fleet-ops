"""OpenTelemetry + Langfuse observability scaffolding.

Call init_observability("<agent-name>") once at startup. Every LLM call wrapped
in ``@traced`` (or manually with ``tracer.start_as_current_span``) is then visible
in Langfuse with cost, latency, prompt, and completion.
"""
import os
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter


def init_observability(service_name: str) -> trace.Tracer:
    """Initialize OTel tracing pointed at Langfuse. Idempotent."""
    if trace.get_tracer_provider().__class__.__name__ == "TracerProvider":
        return trace.get_tracer(service_name)

    endpoint = os.getenv(
        "LANGFUSE_OTEL_ENDPOINT",
        "https://us.cloud.langfuse.com/api/public/otel/v1/traces",
    )
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")

    headers = {}
    if public_key and secret_key:
        import base64 as _b64

        creds = public_key + chr(58) + secret_key
        encoded = _b64.b64encode(creds.encode()).decode()
        headers["Authorization"] = "Basic " + encoded

    provider = TracerProvider(
        resource=Resource.create({"service.name": service_name})
    )
    exporter = OTLPSpanExporter(endpoint=endpoint, headers=headers)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)
