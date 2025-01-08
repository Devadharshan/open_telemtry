import time
import psutil
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.system_metrics import SystemMetricsInstrumentor
from pysyb import connect  # Sybase DB connection library

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
    with connect(dsn="server=your_server;database=your_db;chainxacts=0") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM master..sysprocesses WHERE status='active'")
        active_connections = cursor.fetchone()[0]
    return active_connections

def get_sybase_transaction_rate():
    """Fetch transaction rate from Sybase database."""
    with connect(dsn="server=your_server;database=your_db;chainxacts=0") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) AS transaction_count 
            FROM master..syslogins 
            WHERE logindatetime > GETDATE() - 1
        """)
        transaction_rate = cursor.fetchone()[0]
    return transaction_rate

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
    # Process-level metrics
    process_cpu_metric.add(get_process_cpu_usage())
    process_memory_metric.add(get_process_memory_usage_percent())

    # Sybase database metrics
    sybase_active_connections_metric.add(get_sybase_active_connections())
    sybase_transaction_rate_metric.add(get_sybase_transaction_rate())

    # Logging for debugging
    print(f"Process CPU Usage (%): {get_process_cpu_usage():.2f}")
    print(f"Process Memory Usage (%): {get_process_memory_usage_percent():.2f}")
    print(f"Active Connections: {get_sybase_active_connections()}")
    print(f"Transaction Rate: {get_sybase_transaction_rate()}")

# Application run loop
print("Metrics collection running. Sending to OTLP endpoint...")
while True:
    record_custom_metrics()  # Record custom metrics
    time.sleep(10)  # Adjust the interval as needed
