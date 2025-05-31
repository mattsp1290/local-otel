# 🦅 Agent Observability Verifier

A comprehensive Docker-based telemetry verification environment designed for AI agents to validate traces, metrics, and logs are properly collected from any application. Features OpenTelemetry Collector, StatsD, Prometheus, Grafana, Jaeger, and Filebeat with file-based exports for integration testing.

## 🚀 Quick Start

1. **Setup the environment:**
   ```bash
   ./scripts/setup/setup-telemetry-env.sh
   ```

2. **Start the telemetry stack:**
   ```bash
   ./scripts/setup/start-telemetry-stack.sh
   ```

3. **Verify everything is working:**
   ```bash
   ./scripts/verification/bash/check_telemetry_health.sh
   ```

4. **Access the dashboards:**
   - **Grafana**: http://localhost:3000 (admin/admin)
   - **Prometheus**: http://localhost:9090
   - **Jaeger**: http://localhost:16686
   - **OpenTelemetry Health**: http://localhost:13133

## 📋 Overview

This environment provides a complete local telemetry verification stack that:

- ✅ **Collects traces, metrics, and logs** from any application
- ✅ **Exports data to files** for integration testing
- ✅ **Provides real-time visualization** with Grafana and Jaeger
- ✅ **Supports StatsD metrics** for high-performance metric collection
- ✅ **Processes logs** with Filebeat for correlation and analysis
- ✅ **Runs entirely in Docker** for consistent environments
- ✅ **Includes verification scripts** in Python, Go, and Bash
- ✅ **AI Agent Optimized** - designed for automated observability verification

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Your Application│───▶│ OpenTelemetry    │───▶│ File Exports    │
│  (Canary API)   │    │ Collector        │    │ (JSON/CSV/JSONL)│
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       ▼                       ▼
         │              ┌─────────────────┐    ┌─────────────────┐
         │              │   Prometheus    │    │    Filebeat     │
         │              │   (Metrics)     │    │ (Log Processing)│
         │              └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     StatsD      │    │     Grafana     │    │ Processed Logs  │
│   (UDP:8125)    │    │  (Dashboards)   │    │   (Files)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │
         ▼                       │
┌─────────────────┐              │
│     Jaeger      │◀─────────────┘
│   (Tracing)     │
└─────────────────┘
```

## 📁 Directory Structure

```
local-otel/
├── docker/
│   ├── docker-compose.yml          # Main orchestration file
│   └── configs/                    # Service configurations
│       ├── otel/                   # OpenTelemetry Collector config
│       ├── statsd/                 # StatsD server config
│       ├── prometheus/             # Prometheus config
│       ├── grafana/                # Grafana provisioning
│       └── filebeat/               # Filebeat config
├── data/                           # Telemetry data exports
│   ├── traces/                     # Trace files (JSON, JSONL)
│   ├── metrics/                    # Metric files (JSON, Prometheus)
│   ├── logs/                       # Log files (JSON, text)
│   └── processed/                  # Filebeat processed logs
├── scripts/
│   ├── setup/                      # Environment setup scripts
│   ├── verification/               # Verification scripts
│   │   ├── python/                 # Python verification scripts
│   │   ├── go/                     # Go verification programs
│   │   └── bash/                   # Bash verification scripts
│   └── automation/                 # Additional automation
└── docs/
    └── application-integration-guide.md  # Application integration guide
```

## 🔧 Services

| Service | Port | Purpose | Health Check |
|---------|------|---------|--------------|
| **OpenTelemetry Collector** | 4317 (gRPC), 4318 (HTTP) | Central telemetry collection | http://localhost:13133 |
| **StatsD** | 8125 (UDP), 8126 (Admin) | High-performance metrics | http://localhost:8126 |
| **Prometheus** | 9090 | Metrics storage and querying | http://localhost:9090/-/healthy |
| **Grafana** | 3000 | Visualization dashboards | http://localhost:3000/api/health |
| **Jaeger** | 16686 (UI), 14250 (gRPC) | Distributed tracing | http://localhost:16686 |
| **Filebeat** | 5066 (HTTP) | Log processing and shipping | Internal health checks |

## 📊 Telemetry Endpoints

### For Application Integration

- **OTLP Traces/Metrics (gRPC)**: `localhost:4317`
- **OTLP Traces/Metrics (HTTP)**: `localhost:4318`
- **StatsD Metrics (UDP)**: `localhost:8125`

### Example Usage

```python
# Python OpenTelemetry example
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Setup tracing
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Configure OTLP exporter
otlp_exporter = OTLPSpanExporter(
    endpoint="http://localhost:4318/v1/traces",
)
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Create spans
with tracer.start_as_current_span("canary_chirp"):
    # Your application logic here
    pass
```

```javascript
// Node.js StatsD example
const StatsD = require('node-statsd');
const client = new StatsD({
  host: 'localhost',
  port: 8125,
  prefix: 'canary.'
});

// Send metrics
client.increment('requests_total', 1, {endpoint: '/chirp'});
client.timing('response_duration', 42, {endpoint: '/chirp'});
```

## 📄 File Exports

All telemetry data is exported to files for integration testing:

### Traces
- `data/traces/traces.jsonl` - JSONL format for streaming
- `data/traces/traces_detailed.json` - Full JSON with all details

### Metrics
- `data/metrics/metrics.jsonl` - JSONL format
- `data/metrics/metrics.prom` - Prometheus exposition format

### Logs
- `data/logs/logs.jsonl` - Structured JSON logs
- `data/processed/filebeat-processed*` - Filebeat processed logs

## 🧪 Verification Scripts

### Bash Scripts
```bash
# Health check all services
./scripts/verification/bash/check_telemetry_health.sh

# Validate file outputs
./scripts/verification/bash/validate_file_outputs.sh
```

### Python Scripts
```bash
# Test metrics pipeline
python3 scripts/verification/python/test_metrics_pipeline.py

# Verify Filebeat processing
python3 scripts/verification/python/verify_filebeat.py

# Validate traces
python3 scripts/verification/python/trace_validator.py
```

### Go Programs
```bash
# Load test metrics
go run scripts/verification/go/metrics_load_test.go

# Generate test traces
go run scripts/verification/go/trace_generator.go

# Parse logs for performance
go run scripts/verification/go/log_parser.go
```

## 🔍 Monitoring and Debugging

### View Real-time Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f otel-collector
docker-compose logs -f statsd
```

### Check Container Status
```bash
docker-compose ps
```

### Inspect Data Files
```bash
# Recent traces
ls -la data/traces/
tail -f data/traces/traces.jsonl

# Recent metrics
ls -la data/metrics/
tail -f data/metrics/metrics.jsonl

# Processed logs
ls -la data/processed/
```

## 🛠️ Management Scripts

### Start/Stop Services
```bash
# Start all services
./scripts/setup/start-telemetry-stack.sh

# Stop all services
./scripts/setup/stop-telemetry-stack.sh

# Stop and clean data
./scripts/setup/stop-telemetry-stack.sh --clean-data

# Full reset
./scripts/setup/stop-telemetry-stack.sh --clean-data --remove-volumes
./scripts/setup/setup-telemetry-env.sh
```

## 🤖 AI Agent Usage

This environment is specifically designed for AI agents to add and verify observability:

### For AI Agents
1. Read `AGENT_QUICKSTART.md` for a concise overview
2. Use the verification scripts to confirm telemetry is working
3. Follow the patterns in `examples/` for different languages
4. Check `data/` directories for exported telemetry data

### Common AI Agent Tasks
```bash
# Add observability to a web service
# 1. Instrument the code (see examples/)
# 2. Start the telemetry stack
# 3. Run the application
# 4. Verify with:
./scripts/verification/bash/check_telemetry_health.sh

# Debug missing telemetry
# 1. Check service health
# 2. Verify endpoints are correct
# 3. Check data files for output
ls -la data/traces/ data/metrics/ data/logs/
```

## 🐦 Example: Canary API Integration

Our example "Canary API" demonstrates common web service patterns:

### Endpoints
- `/chirp` - Quick health check endpoint
- `/nest` - Data creation endpoint  
- `/flock` - Batch operations endpoint

### Metrics
- `canary_requests_total` - Request counter by method/endpoint/status
- `canary_response_duration_seconds` - Response time histogram
- `canary_active_connections` - Current connection gauge
- `canary_error_rate` - Error percentage by endpoint

## 🐛 Troubleshooting

### Common Issues

**Services not starting:**
```bash
# Check Docker is running
docker info

# Check port conflicts
lsof -i :4317 -i :4318 -i :8125 -i :9090 -i :3000

# Reset everything
./scripts/setup/stop-telemetry-stack.sh --clean-data --remove-volumes
./scripts/setup/setup-telemetry-env.sh
```

**No telemetry data:**
```bash
# Check OpenTelemetry Collector health
curl http://localhost:13133/

# Check logs for errors
docker-compose logs otel-collector | grep -i "error"

# Verify configuration
./scripts/verification/bash/check_telemetry_health.sh
```

**Permission issues:**
```bash
# Fix data directory permissions
chmod -R 755 data/
```

### Getting Help

1. Run the health check script for detailed diagnostics
2. Check service logs for specific error messages
3. Verify all configuration files are present and valid
4. Ensure Docker has sufficient resources (4GB RAM minimum)

## 🚀 Performance

The telemetry environment is optimized for development use:

- **Low latency**: Sub-second data processing
- **High throughput**: Handles thousands of metrics/traces per second
- **Minimal overhead**: <5% performance impact on your application
- **Efficient storage**: Compressed file exports with rotation

## 🔮 Future Enhancements

- [ ] Language-specific instrumentation examples
- [ ] Pre-built Grafana dashboards for common patterns
- [ ] Cloud provider migration guides
- [ ] Performance regression testing suite
- [ ] Multi-service distributed tracing examples
- [ ] Advanced log correlation features

## 📝 License

This project is open source and available under the [MIT License](LICENSE).
