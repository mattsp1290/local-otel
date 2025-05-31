# 🔧 Telemetry Troubleshooting Guide

This guide helps diagnose and resolve common telemetry issues across traces, metrics, and logs. Each solution includes verification steps to ensure the fix works.

## 🚨 Quick Diagnostics Checklist

Before diving into specific issues, run through this checklist:

1. **Service Health**
   ```bash
   # Check if telemetry stack is running
   docker ps | grep -E "(otel-collector|jaeger|prometheus|grafana|statsd)"
   
   # Check container logs for errors
   docker logs telemetry-nest-otel-collector 2>&1 | tail -20
   ```

2. **Network Connectivity**
   ```bash
   # Test OTLP endpoint
   curl -v http://localhost:4318/v1/traces
   
   # Test StatsD port
   echo "test.metric:1|c" | nc -u -w1 localhost 8125
   
   # Test Prometheus metrics endpoint
   curl http://localhost:9090/-/healthy
   ```

3. **Configuration Validation**
   ```bash
   # Verify environment variables
   docker-compose exec your-service env | grep -E "(OTEL|STATSD|LOG)"
   ```

## 📊 Common Issues and Solutions

### Issue 1: No Traces in Jaeger

**Symptoms:**
- Application appears to be running correctly
- No traces visible in Jaeger UI
- No errors in application logs

**Diagnosis:**
```bash
# 1. Check if Jaeger is receiving any data
curl http://localhost:16686/api/services

# 2. Verify OTLP collector is running
curl http://localhost:13133/  # Health check

# 3. Check collector metrics
curl http://localhost:8888/metrics | grep otel
```

**Solutions:**

1. **Verify OTLP Endpoint Configuration**
   ```yaml
   # docker-compose.yml
   environment:
     OTLP_ENDPOINT: http://telemetry-nest-otel-collector:4318/v1/traces
     # NOT http://localhost:4318 when running in Docker!
   ```

2. **Check Network Connectivity**
   ```bash
   # From within your application container
   docker-compose exec your-service sh -c "curl -v http://telemetry-nest-otel-collector:4318/v1/traces"
   ```

3. **Enable Debug Logging**
   ```python
   # Python example
   import logging
   logging.getLogger("opentelemetry").setLevel(logging.DEBUG)
   ```

4. **Verify Instrumentation is Active**
   ```python
   # Add debug span to verify
   from opentelemetry import trace
   tracer = trace.get_tracer(__name__)
   with tracer.start_as_current_span("debug_test") as span:
       span.set_attribute("debug", True)
       print(f"Trace ID: {span.get_span_context().trace_id:032x}")
   ```

### Issue 2: Missing Metrics in Prometheus

**Symptoms:**
- StatsD metrics not appearing in Prometheus
- Grafana dashboards show "No Data"

**Diagnosis:**
```bash
# 1. Check StatsD is receiving metrics
docker logs telemetry-nest-statsd 2>&1 | tail -20

# 2. Verify Prometheus scrape config
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job=="statsd")'

# 3. Check raw metrics from StatsD exporter
curl http://localhost:9102/metrics | grep -v "^#"
```

**Solutions:**

1. **Fix StatsD Connection**
   ```python
   # Verify StatsD client configuration
   import statsd
   
   # Debug mode
   client = statsd.StatsClient(
       host='telemetry-nest-statsd',  # Use container name, not localhost
       port=8125,
       prefix='myapp'
   )
   
   # Test metric
   client.incr('debug.test')
   ```

2. **Check Metric Naming**
   ```bash
   # StatsD converts dots to underscores for Prometheus
   # myapp.requests.count → myapp_requests_count
   
   # Query Prometheus for your metrics
   curl -g 'http://localhost:9090/api/v1/query?query={__name__=~"myapp.*"}'
   ```

3. **Increase Flush Interval**
   ```javascript
   // statsd config.js
   {
     flushInterval: 10000,  // 10 seconds instead of default
     deleteIdleStats: false  // Keep metrics visible
   }
   ```

### Issue 3: Logs Missing Trace Context

**Symptoms:**
- Logs are being written
- trace_id and span_id fields are empty or missing

**Diagnosis:**
```python
# Check if spans are being created
from opentelemetry import trace

span = trace.get_current_span()
print(f"Current span: {span}")
print(f"Is recording: {span.is_recording()}")
print(f"Trace ID: {span.get_span_context().trace_id}")
```

**Solutions:**

1. **Ensure Instrumentation Order**
   ```python
   # Correct order - instrument BEFORE creating app
   from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
   
   # 1. Setup tracing
   init_telemetry()
   
   # 2. Create app
   app = FastAPI()
   
   # 3. Instrument app
   FastAPIInstrumentor.instrument_app(app)
   ```

2. **Manual Context Injection**
   ```python
   import logging
   from opentelemetry import trace
   
   def get_trace_context():
       span = trace.get_current_span()
       if span and span.is_recording():
           ctx = span.get_span_context()
           return {
               "trace_id": format(ctx.trace_id, '032x'),
               "span_id": format(ctx.span_id, '016x')
           }
       return {"trace_id": "", "span_id": ""}
   
   # Use in logging
   logger.info("Processing", extra=get_trace_context())
   ```

### Issue 4: High Memory Usage from Telemetry

**Symptoms:**
- Application memory steadily increasing
- OOM errors after running for extended periods

**Diagnosis:**
```bash
# Monitor memory usage
docker stats your-service

# Check span processor queue
curl http://localhost:8888/metrics | grep -E "(queue|dropped)"
```

**Solutions:**

1. **Configure Batch Processing**
   ```python
   from opentelemetry.sdk.trace.export import BatchSpanProcessor
   
   # Adjust batch settings
   span_processor = BatchSpanProcessor(
       exporter,
       max_queue_size=2048,  # Default is 2048
       max_export_batch_size=512,  # Default is 512
       export_timeout_millis=30000,  # 30 seconds
       schedule_delay_millis=5000  # 5 seconds
   )
   ```

2. **Implement Sampling**
   ```python
   from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
   
   # Sample 10% of traces
   sampler = TraceIdRatioBased(0.1)
   
   provider = TracerProvider(
       resource=resource,
       sampler=sampler
   )
   ```

### Issue 5: Telemetry Data Gaps

**Symptoms:**
- Intermittent gaps in metrics/traces
- Some requests missing telemetry

**Diagnosis:**
```bash
# Check for dropped data
docker logs telemetry-nest-otel-collector 2>&1 | grep -i "drop\|fail\|error"

# Monitor export failures
curl http://localhost:8888/metrics | grep "failed"
```

**Solutions:**

1. **Add Retry Logic**
   ```python
   from opentelemetry.exporter.otlp.proto.http import Retry
   
   exporter = OTLPSpanExporter(
       endpoint=OTLP_ENDPOINT,
       timeout=30,
       retry=Retry(
           max_attempts=5,
           initial_backoff=1,
           max_backoff=30,
           backoff_multiplier=1.5
       )
   )
   ```

2. **Implement Circuit Breaker**
   ```python
   import time
   
   class TelemetryExporter:
       def __init__(self):
           self.failures = 0
           self.last_attempt = 0
           self.circuit_open = False
           
       def export(self, data):
           if self.circuit_open:
               if time.time() - self.last_attempt < 60:  # 1 minute cooldown
                   return  # Skip export
               else:
                   self.circuit_open = False  # Try again
           
           try:
               self._do_export(data)
               self.failures = 0
           except Exception as e:
               self.failures += 1
               if self.failures > 5:
                   self.circuit_open = True
                   self.last_attempt = time.time()
   ```

## 🔍 Platform-Specific Issues

### Docker Networking Issues

**Problem:** Services can't reach telemetry stack

**Solution:**
```yaml
# Ensure all services use the same network
networks:
  telemetry-nest:
    external: true

services:
  your-service:
    networks:
      - telemetry-nest
```

### Kubernetes Issues

**Problem:** Traces not correlating across pods

**Solution:**
```yaml
# Ensure trace propagation headers
env:
  - name: OTEL_PROPAGATORS
    value: "tracecontext,baggage"
  - name: OTEL_EXPORTER_OTLP_ENDPOINT
    value: "http://otel-collector.observability:4318"
```

### AWS/Cloud Issues

**Problem:** Can't reach telemetry endpoints from Lambda/Cloud Functions

**Solution:**
```python
# Use environment-specific endpoints
import os

if os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
    # Lambda environment
    OTLP_ENDPOINT = os.getenv('OTLP_LAMBDA_ENDPOINT')
else:
    # Local/container environment
    OTLP_ENDPOINT = os.getenv('OTLP_ENDPOINT', 'http://localhost:4318')
```

## 🛠️ Debug Tools and Commands

### Trace Debugging
```bash
# Generate test trace
curl -X POST http://localhost:4318/v1/traces \
  -H "Content-Type: application/json" \
  -d @test-trace.json

# Query Jaeger API
curl "http://localhost:16686/api/traces?service=your-service&limit=20"
```

### Metric Debugging
```bash
# Send test metric to StatsD
echo "test.counter:1|c" | nc -u -w1 localhost 8125
echo "test.gauge:42|g" | nc -u -w1 localhost 8125
echo "test.timer:320|ms" | nc -u -w1 localhost 8125

# Query Prometheus
curl -g 'http://localhost:9090/api/v1/query?query=test_counter'
```

### Log Debugging
```bash
# Check log parsing
docker logs your-service 2>&1 | jq -r 'select(.trace_id != "")'

# Verify JSON structure
docker logs your-service 2>&1 | jq . 2>/dev/null || echo "Invalid JSON"
```

## 📋 Verification Scripts

### Complete Health Check Script
```bash
#!/bin/bash
# save as check_telemetry.sh

echo "🔍 Checking Telemetry Stack Health..."

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Check services
services=("otel-collector:4318" "jaeger:16686" "prometheus:9090" "grafana:3000" "statsd:8125")

for service in "${services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    if nc -z localhost $port 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $name is running on port $port"
    else
        echo -e "${RED}✗${NC} $name is not accessible on port $port"
    fi
done

# Check data flow
echo -e "\n📊 Checking Data Flow..."

# Test trace
trace_id=$(printf '%032x' $RANDOM$RANDOM$RANDOM$RANDOM)
echo "Sending test trace with ID: $trace_id"

# Test metric
echo "test.health.check:1|c" | nc -u -w1 localhost 8125

# Wait for processing
sleep 5

# Verify in Jaeger
if curl -s "http://localhost:16686/api/traces/$trace_id" | grep -q "data"; then
    echo -e "${GREEN}✓${NC} Traces are flowing to Jaeger"
else
    echo -e "${RED}✗${NC} Traces not found in Jaeger"
fi

# Verify in Prometheus
if curl -s "http://localhost:9090/api/v1/query?query=test_health_check" | grep -q "success"; then
    echo -e "${GREEN}✓${NC} Metrics are flowing to Prometheus"
else
    echo -e "${RED}✗${NC} Metrics not found in Prometheus"
fi
```

## 🚀 Performance Optimization

If telemetry is impacting performance:

1. **Reduce Span Creation**
   ```python
   # Only trace significant operations
   if operation_duration_estimate > 100:  # ms
       with tracer.start_as_current_span("operation"):
           do_work()
   else:
       do_work()  # No span
   ```

2. **Batch Operations**
   ```python
   # Batch multiple metrics
   with statsd_client.pipeline() as pipe:
       pipe.incr('requests')
       pipe.timing('duration', elapsed)
       pipe.gauge('queue_size', len(queue))
   ```

3. **Async Export**
   ```python
   # Use async exporters when available
   from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
   
   # gRPC is generally more efficient than HTTP
   exporter = OTLPSpanExporter(
       endpoint="localhost:4317",  # gRPC port
       compression=Compression.Gzip
   )
   ```

## 📞 Getting Help

If you're still stuck:

1. **Gather Diagnostics**
   ```bash
   # Create diagnostic bundle
   mkdir telemetry-debug
   docker-compose logs > telemetry-debug/docker-logs.txt
   docker ps -a > telemetry-debug/containers.txt
   docker-compose config > telemetry-debug/config.yml
   tar -czf telemetry-debug.tar.gz telemetry-debug/
   ```

2. **Check Documentation**
   - [OpenTelemetry Troubleshooting](https://opentelemetry.io/docs/reference/specification/protocol/exporter/)
   - [Jaeger Troubleshooting](https://www.jaegertracing.io/docs/latest/troubleshooting/)
   - [Prometheus Troubleshooting](https://prometheus.io/docs/prometheus/latest/troubleshooting/)

3. **Common Fix Checklist**
   - [ ] Restart all containers in correct order
   - [ ] Verify network connectivity between containers
   - [ ] Check for port conflicts
   - [ ] Ensure sufficient resources (CPU, memory, disk)
   - [ ] Review recent configuration changes

Remember: Most telemetry issues are configuration-related. Double-check your environment variables and network settings first!
