import sybpydb
import time
from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.logs import LoggingHandler, LogEmitterProvider
import logging

# Set up OpenTelemetry
resource = Resource(attributes={
    "service.name": "sybase-query-app",
    "service.instance.id": "instance-1",
})

# Tracer setup
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)
span_processor = BatchSpanProcessor(ConsoleSpanExporter())
trace.get_tracer_provider().add_span_processor(span_processor)

# Metrics setup
meter_provider = MeterProvider(resource=resource)
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter(__name__)

# Add a metric reader
metric_reader = PeriodicExportingMetricReader(ConsoleMetricExporter(), export_interval_millis=5000)
meter_provider.add_metric_reader(metric_reader)

# Metrics for query execution
query_execution_count = meter.create_counter(
    name="query_execution_count",
    description="Count of Sybase queries executed",
    unit="1",
)

query_execution_time = meter.create_histogram(
    name="query_execution_time",
    description="Time taken to execute Sybase queries",
    unit="ms",
)

# Logging setup
log_handler = LoggingHandler(level=logging.INFO, resource=resource)
logger = logging.getLogger("sybase-query-logger")
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)

def connect_to_sybase(server: str, db: str, user: str, password: str):
    """
    Establish a connection to the Sybase database.
    """
    try:
        connection = sybpydb.connect(
            server=server,
            database=db,
            user=user,
            password=password
        )
        logger.info("Successfully connected to Sybase server.")
        return connection
    except Exception as e:
        logger.error(f"Failed to connect to Sybase server: {e}")
        raise

def execute_query(connection, query: str):
    """
    Execute a Sybase query and return the results.
    """
    with tracer.start_as_current_span("execute_query") as span:
        start_time = time.time()
        try:
            cursor = connection.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            logger.info(f"Query executed successfully: {query}")
            return results
        except Exception as e:
            logger.error(f"Error executing query: {query}, Error: {e}")
            raise
        finally:
            end_time = time.time()
            duration = (end_time - start_time) * 1000  # Convert to milliseconds
            query_execution_count.add(1)
            query_execution_time.record(duration)
            span.set_attribute("db.statement", query)
            span.set_attribute("db.execution_time", duration)

def main():
    # Sybase connection details
    server = "your_server_name"
    db = "your_database_name"
    user = "your_username"
    password = "your_password"

    # Connect to Sybase
    connection = connect_to_sybase(server, db, user, password)

    # Execute a query
    query = "SELECT * FROM your_table_name"
    results = execute_query(connection, query)

    # Print query results
    for row in results:
        print(row)

if __name__ == "__main__":
    main()