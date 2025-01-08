import time
import psutil
import logging
from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.system_metrics import SystemMetricsInstrumentation
from opentelemetry.sdk.logs import LoggerProvider
from opentelemetry.sdk.logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter

# Common OTLP endpoint
OTEL_ENDPOINT = "http://otel-collector:4317"

# Set up OpenTelemetry resources
resource = Resource.create(
    attributes={"service.name": "sybase_app", "host.name": "sybase_host"}
)

# Configure tracing
tracer_provider = TracerProvider(resource=resource)
span_exporter = OTLPSpanExporter(endpoint=OTEL_ENDPOINT, insecure=True)
tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
trace.set_tracer_provider(tracer_provider)
tracer = trace.get_tracer("sybase_app")

# Configure metrics
metric_exporter = OTLPMetricExporter(endpoint=OTEL_ENDPOINT, insecure=True)
metric_reader = PeriodicExportingMetricReader(metric_exporter)
meter_provider = MeterProvider(metric_readers=[metric_reader], resource=resource)
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter_provider().get_meter("sybase_app")

# Add system metrics instrumentation
SystemMetricsInstrumentation(
    meter=meter, resource=resource, exporter=metric_exporter, export_interval_millis=10000
).start()

# Define custom metrics
active_connections_metric = meter.create_up_down_counter(
    name="sybase_active_connections",
    description="Active Sybase database connections",
    unit="connections",
)
transaction_rate_metric = meter.create_counter(
    name="sybase_transaction_rate",
    description="Rate of transactions executed",
    unit="transactions",
)

# Configure logging with OpenTelemetry
log_exporter = OTLPLogExporter(endpoint=OTEL_ENDPOINT, insecure=True)
logger_provider = LoggerProvider(resource=resource)
logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))

# Set up Python logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sybase_app")

# Simulate recording custom metrics
def record_custom_metrics():
    """Record active connections and transaction rate."""
    active_connections = 100  # Replace with actual Sybase query result
    transaction_rate = 50  # Replace with actual Sybase query result

    active_connections_metric.add(active_connections)
    transaction_rate_metric.add(transaction_rate)

    logger.info(f"Recorded active connections: {active_connections}")
    logger.info(f"Recorded transaction rate: {transaction_rate}")


# Main application loop
def main():
    while True:
        with tracer.start_as_current_span("sybase_operation_execution"):
            logger.info("Starting Sybase metrics collection...")
            record_custom_metrics()
            time.sleep(10)  # Simulate processing interval


if __name__ == "__main__":
    main()
