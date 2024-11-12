from flask import Flask, jsonify
from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.prometheus import PrometheusMetrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.prometheus import PrometheusMetricsExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger import JaegerExporter
import psutil
import pyodbc
from prometheus_client import start_http_server, Gauge

# Initialize Flask App
app = Flask(__name__)

# Set up tracing
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Instrument Flask with OpenTelemetry
FlaskInstrumentor().instrument_app(app)

# Configure Prometheus metrics exporter
metrics_exporter = PrometheusMetricsExporter()
PrometheusMetrics(app, exporter=metrics_exporter)

# Custom metrics for CPU and Memory
cpu_metric = Gauge('flask_app_cpu_usage', 'CPU usage of Flask app')
memory_metric = Gauge('flask_app_memory_usage', 'Memory usage of Flask app')

# Configure Jaeger exporter
jaeger_exporter = JaegerExporter(agent_host_name="localhost", agent_port=6831)
span_processor = BatchSpanProcessor(jaeger_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Database connection details
DB_DRIVER = '{FreeTDS}'  # or '{Sybase ASE ODBC Driver}' if available
DB_SERVER = 'your_sybase_server'
DB_PORT = '5000'  # Replace with the correct Sybase port
DB_DATABASE = 'your_database'
DB_USER = 'your_user'
DB_PASSWORD = 'your_password'

# Helper function to get a database connection
def get_db_connection():
    conn_str = (
        f"DRIVER={DB_DRIVER};"
        f"SERVER={DB_SERVER};"
        f"PORT={DB_PORT};"
        f"DATABASE={DB_DATABASE};"
        f"UID={DB_USER};"
        f"PWD={DB_PASSWORD};"
    )
    return pyodbc.connect(conn_str)

@app.route("/check_db", methods=["GET"])
def check_db():
    with tracer.start_as_current_span("check_db_connection"):
        try:
            conn = get_db_connection()
            with tracer.start_as_current_span("run_sample_query"):
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM my_table")  # Example query
                result = cursor.fetchone()
                return jsonify({"status": "Connected", "query_result": result[0]}), 200
        except Exception as e:
            trace.get_current_span().record_exception(e)
            return jsonify({"status": "Connection failed", "error": str(e)}), 500

@app.route("/metrics")
def metrics():
    # Record system metrics
    cpu_metric.set(psutil.cpu_percent())
    memory_metric.set(psutil.virtual_memory().percent)
    return jsonify({"status": "Metrics recorded"}), 200

if __name__ == "__main__":
    start_http_server(8000)  # Start Prometheus client
    app.run(host="0.0.0.0", port=5000)
