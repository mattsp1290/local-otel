# 🦅 Agent Observability Verifier - Quick Start

## What This Does (One Paragraph)

A Docker-based telemetry verification environment that validates traces, metrics, and logs are properly collected from any application. It runs OpenTelemetry Collector, Prometheus, Grafana, Jaeger, StatsD, and Filebeat in containers, exports all telemetry data to files for verification, and provides health check scripts to confirm everything works. Perfect for AI agents adding observability to applications.

## Architecture (ASCII)

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Your Application│───▶│   Telemetry      │───▶│  Verification   │
│                 │    │   Nest Stack     │    │     Files       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
        │                       │                       │
        │                       ├── OTel Collector     ├── traces.jsonl
        ├── OTLP (4317/4318)   ├── Prometheus         ├── metrics.prom
        ├── StatsD (8125)      ├── Grafana            └── logs.jsonl
        └── Logs               ├── Jaeger
                               └── Filebeat
```

## Copy-Paste Commands

```bash
# 1. Setup (one time)
./scripts/setup/setup-telemetry-env.sh

# 2. Start the stack
./scripts/setup/start-telemetry-stack.sh

# 3. Verify it's working
./scripts/verification/bash/check_telemetry_health.sh

# 4. Stop when done
./scripts/setup/stop-telemetry-stack.sh
```

## Verification Steps

### 1. Check Services Are Running
```bash
docker ps | grep telemetry-nest
# Should see 6 containers running
```

### 2. Verify Traces
- **Jaeger UI**: http://localhost:16686
- **File**: `data/traces/traces.jsonl`
- **Test**: Send OTLP trace to `localhost:4317` (gRPC) or `localhost:4318` (HTTP)

### 3. Verify Metrics  
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **File**: `data/metrics/metrics.prom`
- **Test**: Send StatsD metric to `localhost:8125` (UDP)

### 4. Verify Logs
- **Files**: `data/logs/*.jsonl`
- **Processed**: `data/processed/filebeat-processed*`
- **Test**: Write structured JSON to `data/logs/`

## Common Integration Patterns

### Python + OpenTelemetry
```python
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
exporter = OTLPSpanExporter(endpoint="http://localhost:4318/v1/traces")
```

### Node.js + StatsD
```javascript
const StatsD = require('node-statsd');
const client = new StatsD({ host: 'localhost', port: 8125 });
client.increment('api.requests');
```

### Go + OTLP
```go
exporter, _ := otlptrace.New(
    context.Background(),
    otlptracegrpc.NewClient(
        otlptracegrpc.WithEndpoint("localhost:4317"),
        otlptracegrpc.WithInsecure(),
    ),
)
```

### Direct HTTP (Any Language)
```bash
# Send trace via HTTP
curl -X POST http://localhost:4318/v1/traces \
  -H "Content-Type: application/json" \
  -d '{"resourceSpans":[...]}'

# Send metric via StatsD
echo "api.requests:1|c" | nc -u -w0 localhost 8125
```

## Troubleshooting Decision Tree

```
Problem?
├── Services not starting?
│   ├── Check Docker: docker info
│   ├── Check ports: lsof -i :4317 -i :8125 -i :3000
│   └── Reset: ./scripts/setup/stop-telemetry-stack.sh --clean-data
├── No data appearing?
│   ├── Check health: curl http://localhost:13133/
│   ├── Check logs: docker logs telemetry-nest-otel-collector
│   └── Verify endpoints match (4317 gRPC, 4318 HTTP, 8125 UDP)
└── Permission errors?
    └── Fix: chmod -R 755 data/
```

## File Locations

- **Traces**: `data/traces/traces.jsonl`
- **Metrics**: `data/metrics/metrics.prom`  
- **Logs**: `data/logs/*.jsonl`
- **Configs**: `docker/configs/*/`
- **Scripts**: `scripts/verification/*/`

## Quick Validation

After instrumenting your application:

1. **Start your app** with telemetry pointing to localhost endpoints
2. **Perform some operations** to generate telemetry
3. **Check the files**:
   ```bash
   ls -la data/traces/   # Should have recent .jsonl files
   ls -la data/metrics/  # Should have metrics.prom
   ls -la data/logs/     # Should have log files
   ```
4. **Run verification**: `./scripts/verification/bash/check_telemetry_health.sh`

## Next Steps

- Add language-specific examples: Create `examples/<language>/` 
- Custom dashboards: Add to `docker/configs/grafana/dashboards/`
- Production setup: See `docs/` for cloud migration guides

---
*For full documentation, see README.md*
