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
from opentelemetry.sdk._logs import LogEmitterProvider, BatchLogProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
import sybpydb  # Sybase driver

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

# Configure logging
log_exporter = OTLPLogExporter(endpoint=OTEL_ENDPOINT, insecure=True)
log_emitter_provider = LogEmitterProvider(resource=resource)
log_emitter_provider.add_log_processor(BatchLogProcessor(log_exporter))
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sybase_app")
logger.addHandler(logging.StreamHandler())

# Sybase connection details
SYBASE_SERVER = "your_sybase_server"
SYBASE_USER = "your_username"
SYBASE_PASSWORD = "your_password"
SYBASE_DATABASE = "your_database"

# Establish a connection to the Sybase server
def connect_to_sybase():
    """Connect to the Sybase database."""
    try:
        conn = sybpydb.connect(
            servername=SYBASE_SERVER,
            user=SYBASE_USER,
            password=SYBASE_PASSWORD,
            database=SYBASE_DATABASE,
        )
        logger.info("Connected to Sybase database successfully.")
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to Sybase: {e}")
        raise

# Simulate recording custom metrics
def record_custom_metrics(connection):
    """Record active connections and transaction rate."""
    try:
        with connection.cursor() as cursor:
            # Query for active connections
            cursor.execute("SELECT COUNT(*) FROM master..sysprocesses WHERE dbid = DB_ID()")
            active_connections = cursor.fetchone()[0]

            # Query for transaction rate
            cursor.execute(
                "SELECT COUNT(*) FROM master..syslogshold WHERE dbid = DB_ID()"
            )
            transaction_rate = cursor.fetchone()[0]

            # Record metrics
            active_connections_metric.add(active_connections)
            transaction_rate_metric.add(transaction_rate)

            logger.info(
                f"Custom metrics recorded: Active Connections={active_connections}, Transaction Rate={transaction_rate}"
            )
    except Exception as e:
        logger.error(f"Error recording metrics: {e}")

# Main application loop
def main():
    connection = connect_to_sybase()
    while True:
        with tracer.start_as_current_span("sybase_operation_execution"):
            try:
                logger.info("Starting Sybase metrics collection...")
                record_custom_metrics(connection)
                logger.info("Metrics collection completed.")
                time.sleep(10)  # Simulate processing interval
            except Exception as e:
                logger.error(f"Error in main loop: {e}")


if __name__ == "__main__":
    main()