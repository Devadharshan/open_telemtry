import time
import logging
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.exporter import OTLPLogExporter
from opentelemetry.sdk.logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk.logs.export import BatchLogProcessor

import psutil
import sybpydb

# Define OpenTelemetry Resource
resource = Resource(attributes={"service.name": "sybase_app"})

# === Setup Tracing ===
trace_provider = TracerProvider(resource=resource)
trace.set_tracer_provider(trace_provider)
span_exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)
trace_provider.add_span_processor(BatchSpanProcessor(span_exporter))
tracer = trace.get_tracer("sybase_app")

# === Setup Metrics ===
metric_exporter = OTLPMetricExporter(endpoint="http://localhost:4317", insecure=True)
metric_reader = PeriodicExportingMetricReader(metric_exporter)
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter_provider().get_meter("sybase_app")

# === System Metrics ===
from opentelemetry.instrumentation.system_metrics import SystemMetricsInstrumentation

SystemMetricsInstrumentation(
    meter=meter, resource=resource, exporter=metric_exporter, export_interval_millis=10000
).start()

# === Setup Logging ===
log_exporter = OTLPLogExporter(endpoint="http://localhost:4317", insecure=True)
logger_provider = LoggerProvider(resource=resource)
logger_provider.add_log_processor(BatchLogProcessor(log_exporter))

# Set up the Python logging module to work with OpenTelemetry
logging_handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
logging.basicConfig(level=logging.INFO, handlers=[logging_handler])

# Python logger
otel_logger = logging.getLogger("sybase_app_logger")

# === Custom Metrics ===
active_connections_metric = meter.create_up_down_counter(
    name="sybase_active_connections",
    description="Number of active connections to the Sybase database",
    unit="connections",
)

transaction_rate_metric = meter.create_up_down_counter(
    name="sybase_transaction_rate",
    description="Number of transactions processed per minute",
    unit="transactions/min",
)

cpu_usage_metric = meter.create_up_down_counter(
    name="process_cpu_usage_percent",
    description="CPU usage percentage of the current process",
    unit="%",
)

memory_usage_metric = meter.create_up_down_counter(
    name="process_memory_usage_bytes",
    description="Memory usage of the process in bytes",
    unit="bytes",
)

# === Sybase Database Connection ===
def connect_to_sybase():
    conn = sybpydb.connect(
        servername="YOUR_SERVER_NAME",
        database="YOUR_DATABASE_NAME",
        user="YOUR_USERNAME",
        password="YOUR_PASSWORD",
    )
    return conn


# === Helper Functions ===
def get_cpu_usage():
    return psutil.Process().cpu_percent(interval=None)


def get_memory_usage():
    return psutil.Process().memory_info().rss


def record_process_metrics():
    cpu_usage = get_cpu_usage()
    memory_usage = get_memory_usage()
    cpu_usage_metric.add(cpu_usage)
    memory_usage_metric.add(memory_usage)


def get_active_connections(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM master..sysprocesses WHERE status = 'active'")
    active_connections = cursor.fetchone()[0]
    cursor.close()
    return active_connections


def get_transaction_rate(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(logical_reads + writes) FROM master..sysprocesses")
    transaction_rate = cursor.fetchone()[0]
    cursor.close()
    return transaction_rate


def record_sybase_metrics(conn):
    active_connections = get_active_connections(conn)
    transaction_rate = get_transaction_rate(conn)
    active_connections_metric.add(active_connections)
    transaction_rate_metric.add(transaction_rate)


# === Main Application ===
def main():
    conn = connect_to_sybase()
    otel_logger.info("Connected to Sybase database.")

    while True:
        with tracer.start_as_current_span("sybase_metrics_collection") as span:
            span.set_attribute("operation.name", "metrics_collection")

            record_process_metrics()
            record_sybase_metrics(conn)

            otel_logger.info("Metrics collected and sent to OpenTelemetry Collector.")

        time.sleep(10)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        otel_logger.error(f"Application error: {str(e)}")
        raise