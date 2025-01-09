import time
import psutil
from opentelemetry import trace, metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.system_metrics import SystemMetricsInstrumentor
from pysyb import connect  # Sybase DB connection library

# Import logger and tracer from your `lib` folder
from lib.logger import logger  # Ensure logger is configured properly in `lib/logger.py`
from lib.tracer import tracer  # Ensure tracer is configured properly in `lib/tracer.py`

# Configure OpenTelemetry resources
resource = Resource.create(attributes={"service.name": "sybase_app"})

# Metrics Exporter and Provider
metric_exporter = OTLPMetricExporter(endpoint="http://localhost:4317", insecure=True)
metric_reader = PeriodicExportingMetricReader(metric_exporter)
meter_provider = MeterProvider(metric_readers=[metric_reader], resource=resource)
metrics.set_meter_provider(meter_provider)

# Enable system-level metrics instrumentation
SystemMetricsInstrumentor().instrument(meter_provider=meter_provider)

# Create a meter for custom metrics
meter = metrics.get_meter_provider().get_meter("sybase_app")

# Total system memory (in bytes)
total_memory = psutil.virtual_memory().total

# Tracer
tracer = trace.get_tracer("sybase_app")

# Custom metrics: Process-level instrumentation
def get_process_cpu_usage():
    """Fetch CPU usage percentage of the current process."""
    return psutil.Process().cpu_percent(interval=None)

def get_process_memory_usage_percent():
    """Fetch memory usage of the current process as a percentage of total system memory."""
    process_memory = psutil.Process().memory_info().rss
    return (process_memory / total_memory) * 100

# Custom metrics: Sybase database metrics
def get_sybase_active_connections():
    """Fetch active connections from Sybase database."""
    with tracer.start_as_current_span("fetch_sybase_active_connections"):
        try:
            with connect(dsn="server=your_server;database=your_db;chainxacts=0") as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM master..sysprocesses WHERE status='active'")
                active_connections = cursor.fetchone()[0]
            return active_connections
        except Exception as e:
            logger.error(f"Error fetching active connections: {e}")
            return 0

def get_sybase_transaction_rate():
    """Fetch transaction rate from Sybase database."""
    with tracer.start_as_current_span("fetch_sybase_transaction_rate"):
        try:
            with connect(dsn="server=your_server;database=your_db;chainxacts=0") as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) AS transaction_count 
                    FROM master..syslogins 
                    WHERE logindatetime > GETDATE() - 1
                """)
                transaction_rate = cursor.fetchone()[0]
            return transaction_rate
        except Exception as e:
            logger.error(f"Error fetching transaction rate: {e}")
            return 0

# Custom Metrics
process_cpu_metric = meter.create_up_down_counter(
    name="custom_process_cpu_usage_percent",
    description="CPU usage percentage of the process",
    unit="%",
)

process_memory_metric = meter.create_up_down_counter(
    name="custom_process_memory_usage_percent",
    description="Memory usage percentage of the process",
    unit="%",
)

sybase_active_connections_metric = meter.create_up_down_counter(
    name="sybase_active_connections",
    description="Number of active connections to Sybase",
    unit="connections",
)

sybase_transaction_rate_metric = meter.create_up_down_counter(
    name="sybase_transaction_rate",
    description="Transaction rate in Sybase",
    unit="transactions",
)

# Function to record custom metrics
def record_custom_metrics():
    """Record custom metrics for process and Sybase database."""
    with tracer.start_as_current_span("record_custom_metrics"):
        try:
            # Process-level metrics
            cpu_usage = get_process_cpu_usage()
            memory_usage = get_process_memory_usage_percent()
            process_cpu_metric.add(cpu_usage)
            process_memory_metric.add(memory_usage)

            # Sybase database metrics
            active_connections = get_sybase_active_connections()
            transaction_rate = get_sybase_transaction_rate()
            sybase_active_connections_metric.add(active_connections)
            sybase_transaction_rate_metric.add(transaction_rate)

            # Logging for debugging
            logger.info(f"Process CPU Usage (%): {cpu_usage:.2f}")
            logger.info(f"Process Memory Usage (%): {memory_usage:.2f}")
            logger.info(f"Active Connections: {active_connections}")
            logger.info(f"Transaction Rate: {transaction_rate}")

        except Exception as e:
            logger.error(f"Error recording metrics: {e}")

# Application run loop
logger.info("Metrics collection running. Sending to OTLP endpoint...")
while True:
    record_custom_metrics()  # Record custom metrics
    time.sleep(10)  # Adjust the interval as needed
