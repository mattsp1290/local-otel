# 🚀 SigNoz Quick Start Guide

Welcome to SigNoz - an open-source alternative to DataDog and New Relic that provides traces, metrics, and logs in a single pane of glass!

## 📋 What is SigNoz?

SigNoz is a full-stack open-source Application Performance Monitoring (APM) and observability platform built natively on OpenTelemetry. Unlike traditional setups that require multiple tools (Prometheus for metrics, Jaeger for traces, Elasticsearch for logs), SigNoz provides everything in one unified interface.

## 🏗️ Architecture Overview

```
Your Apps → OpenTelemetry Collector → ┬→ File System (testing/backup)
                                      └→ SigNoz (ClickHouse)
```

### Key Components:
- **SigNoz Frontend**: Web UI at http://localhost:3301
- **Query Service**: API backend for the frontend
- **ClickHouse**: High-performance columnar database for storage
- **OpenTelemetry Collector**: Dual-configured to send data to both SigNoz and files

## 🚀 Getting Started

### 1. Start the Stack

```bash
# Start the enhanced stack with SigNoz
docker-compose -f docker-compose.signoz.yml up -d

# Verify all services are running
docker-compose -f docker-compose.signoz.yml ps
```

### 2. Access SigNoz UI

Open your browser and navigate to:
- **SigNoz UI**: http://localhost:3301
- **ClickHouse**: http://localhost:8123 (for direct DB access)
- **Query API**: http://localhost:8080 (for programmatic access)

## 📊 First Steps in SigNoz

### 1. View Services
Navigate to the Services tab to see all services sending telemetry data. You should see:
- Service names
- Latency percentiles (p50, p95, p99)
- Error rates
- Request rates

### 2. Explore Traces
Click on any service to view its traces:
- See distributed traces across multiple services
- Analyze span details and timings
- Filter by status, duration, or attributes

### 3. Check Metrics
Go to the Dashboards tab to view:
- Pre-built dashboards for common metrics
- Custom metric exploration
- Time-series visualization

### 4. Search Logs
Use the Logs tab to:
- Search across all application logs
- Filter by severity, service, or custom attributes
- Correlate logs with traces

## 🧪 Verify the Migration

### 1. Generate Test Data

```bash
# Use the Python FastAPI example to generate telemetry
cd examples/python-fastapi
docker-compose up -d

# Send test requests
python test_telemetry.py
```

### 2. Check File Exports (Still Working!)

```bash
# Verify traces are still being written to files
ls -la data/traces/
tail -f data/traces/traces.jsonl

# Check metrics
tail -f data/metrics/metrics.jsonl

# Check logs
tail -f data/logs/logs.jsonl
```

### 3. Query SigNoz API

```bash
# List services in SigNoz
curl -s http://localhost:8080/api/v1/services | jq .

# Get trace data
curl -s "http://localhost:8080/api/v1/traces?start=$(date -u -d '1 hour ago' +%s)000&end=$(date -u +%s)000&limit=10" | jq .

# Check metrics
curl -s http://localhost:8080/api/v1/metrics | jq .
```

### 4. Run Verification Script

```bash
# Run the comprehensive verification
python scripts/verification/python/verify_signoz_migration.py
```

## 📈 Common Use Cases

### 1. Finding Slow Endpoints
1. Go to Services → Select your service
2. Sort by P99 latency
3. Click on a slow trace to analyze

### 2. Debugging Errors
1. Services → Filter by error rate > 0
2. Click on traces with errors
3. View error details and stack traces

### 3. Creating Custom Dashboards
1. Dashboards → New Dashboard
2. Add panels for your metrics
3. Save and share with your team

### 4. Setting Up Alerts
1. Alerts → New Alert
2. Define conditions (e.g., error rate > 5%)
3. Configure notification channels

## 🔍 Querying in SigNoz

### Trace Queries
```
# Find traces for a specific service
service.name = "canary-api"

# Find slow traces
duration > 1000ms

# Find failed traces
status.code = "ERROR"
```

### Metric Queries
```
# Request rate
sum(rate(http_requests_total[5m])) by (service)

# Error percentage
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100
```

### Log Queries
```
# Error logs
severity = "ERROR"

# Logs from specific service
service.name = "auth-service" AND body contains "failed"
```

## 🔧 Configuration

### Sending Data to SigNoz

Your applications send data to the same OpenTelemetry Collector endpoints:
- **OTLP gRPC**: `localhost:4317`
- **OTLP HTTP**: `localhost:4318`
- **StatsD**: `localhost:8125`

The collector automatically dual-exports to both SigNoz and file system.

### Example: Python with OpenTelemetry

```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Configure OTLP exporter (same as before!)
trace.set_tracer_provider(TracerProvider())
otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Your code remains unchanged
tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span("my_operation"):
    # Your business logic
    pass
```

## 🎯 Benefits of This Setup

1. **No Lock-in**: Data is stored in both SigNoz and files
2. **Easy Rollback**: Just switch back to original docker-compose.yml
3. **Testing Friendly**: File exports enable integration testing
4. **Unified View**: See traces, metrics, and logs together
5. **Cost Effective**: Open-source alternative to commercial APMs

## 🐛 Troubleshooting

### SigNoz UI Not Loading
```bash
# Check if all services are healthy
docker-compose -f docker-compose.signoz.yml ps

# Check SigNoz frontend logs
docker logs signoz-frontend

# Verify query service is running
curl http://localhost:8080/api/v1/health
```

### No Data in SigNoz
```bash
# Check OpenTelemetry Collector logs
docker logs telemetry-nest-otel-collector

# Verify SigNoz collector is receiving data
docker logs signoz-otel-collector

# Check ClickHouse is accessible
docker exec -it signoz-clickhouse clickhouse-client -q "SELECT 1"
```

### High Memory Usage
```bash
# Check ClickHouse memory
docker stats signoz-clickhouse

# Adjust memory limits in docker-compose if needed
# See clickhouse-users.xml for configuration
```

## 📚 Advanced Topics

### 1. Data Retention
By default, SigNoz retains:
- Traces: 7 days
- Metrics: 30 days
- Logs: 7 days

Configure in ClickHouse settings as needed.

### 2. Custom Attributes
Add custom attributes in your OTel configuration:
```yaml
processors:
  attributes:
    actions:
      - key: team
        value: platform
        action: insert
```

### 3. Sampling
Configure trace sampling for high-volume services:
```yaml
processors:
  probabilistic_sampler:
    sampling_percentage: 10  # Sample 10% of traces
```

## 🔄 Migration from Other Tools

### From Jaeger
- Traces appear in SigNoz automatically
- Use the same trace IDs to correlate
- Jaeger UI still available at http://localhost:16686

### From Prometheus
- Metrics flow to both Prometheus and SigNoz
- PromQL queries can be adapted for SigNoz
- Grafana dashboards remain functional

### From ELK Stack
- Configure log forwarding to OpenTelemetry
- Use SigNoz's log search instead of Kibana
- Correlate logs with traces using trace IDs

## 🎉 Next Steps

1. **Explore the UI**: Familiarize yourself with all tabs
2. **Create Dashboards**: Build custom views for your metrics
3. **Set Up Alerts**: Configure alerts for critical issues
4. **Integrate More Services**: Add OpenTelemetry to all your apps
5. **Join the Community**: https://signoz.io/slack

## 📖 Resources

- **SigNoz Documentation**: https://signoz.io/docs/
- **OpenTelemetry Docs**: https://opentelemetry.io/docs/
- **ClickHouse Docs**: https://clickhouse.com/docs/
- **Example Applications**: See `examples/` directory

---

Remember: Your existing file-based exports continue to work! This migration adds SigNoz's powerful UI while maintaining all your current capabilities. Happy monitoring! 🚀
