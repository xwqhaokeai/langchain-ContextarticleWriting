from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

def setup_tracing(app: FastAPI, service_name: str = "context-article-writing"):
    """
    为 FastAPI 应用配置 OpenTelemetry 链路追踪。
    """
    resource = Resource(attributes={"service.name": service_name})
    provider = TracerProvider(resource=resource)
    # processor = BatchSpanProcessor(ConsoleSpanExporter()) # 禁用控制台导出
    # provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)