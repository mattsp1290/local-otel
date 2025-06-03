"""
OpenTelemetry configuration for User Profile Service
"""

import os
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

def init_telemetry():
    """Initialize OpenTelemetry tracing"""
    
    # Service information
    service_name = os.getenv("SERVICE_NAME", "user-profile-service")
    service_version = "1.0.0"
    
    # Create resource with service information
    resource = Resource.create({
        "service.name": service_name,
        "service.version": service_version,
        "service.instance.id": os.getenv("HOSTNAME", "local"),
        "deployment.environment": os.getenv("ENVIRONMENT", "development")
    })
    
    # Create tracer provider
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)
    
    # Configure OTLP exporter
    otlp_endpoint = os.getenv("OTLP_ENDPOINT", "http://localhost:4318/v1/traces")
    otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
    
    # Add span processor
    span_processor = BatchSpanProcessor(otlp_exporter)
    provider.add_span_processor(span_processor)
    
    # Set up W3C trace context propagator
    set_global_textmap(TraceContextTextMapPropagator())
    
    # Auto-instrument libraries
    FastAPIInstrumentor().instrument(tracer_provider=provider)
    SQLAlchemyInstrumentor().instrument(tracer_provider=provider)
    RedisInstrumentor().instrument(tracer_provider=provider)
    HTTPXClientInstrumentor().instrument(tracer_provider=provider)
    LoggingInstrumentor().instrument(set_logging_format=True)
    
    # Return tracer
    return trace.get_tracer(service_name, service_version)
