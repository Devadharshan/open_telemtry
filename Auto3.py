import time
import logging
from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk._logs import LogEmitterProvider, BatchLogProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
import psutil

# Configure resources
resource = Resource.create({"service.name": "sybase_app"})

# Configure tracing
tracer_provider = TracerProvider(resource=resource)
span_exporter = OTLPSpanExporter(endpoint="http://otel-collector:4317", insecure=True)
tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
trace.set_tracer_provider(tracer_provider)
tracer = trace.get_tracer("sybase_app")

# Configure metrics
metric_exporter = OTLPMetricExporter(endpoint="http://otel-collector:4317", insecure=True)
metric_reader = PeriodicExportingMetricReader(metric_exporter)
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)
meter = meter_provider.get_meter("sybase_app")

# Define custom metrics
cpu_usage_metric = meter.create_up_down_counter(
    name="process_cpu_usage_percent",
    description="CPU usage percentage of the process",
    unit="%",
)
memory_usage_metric = meter.create_up_down_counter(
    name="process_memory_usage_bytes",
    description="Memory usage of the process in bytes",
    unit="bytes",
)

def record_system_metrics():
    process = psutil.Process()
    cpu_usage_metric.add(process.cpu_percent(interval=None))
    memory_usage_metric.add(process.memory_info().rss)

# Configure logging
log_exporter = OTLPLogExporter(endpoint="http://otel-collector:4317", insecure=True)
log_emitter_provider = LogEmitterProvider(resource=resource)
log_emitter_provider.add_log_processor(BatchLogProcessor(log_exporter))
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sybase_app")
logger.addHandler(logging.StreamHandler())

# Application Logic Example
while True:
    with tracer.start_as_current_span("sybase_query_execution"):
        try:
            logger.info("Executing Sybase query")
            # Simulated Sybase query and metrics recording
            record_system_metrics()
            logger.info("Metrics recorded")
            time.sleep(10)
        except Exception as e:
            logger.error(f"Error during operation: {e}")