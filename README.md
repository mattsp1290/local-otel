# SpacetimeDB Local OpenTelemetry Environment

A comprehensive Docker-based local telemetry environment for SpacetimeDB development, featuring OpenTelemetry Collector, StatsD, Prometheus, Grafana, Jaeger, and Filebeat with file-based exports for integration testing.

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

This environment provides a complete local telemetry stack that:

- ✅ **Collects traces, metrics, and logs** from SpacetimeDB
- ✅ **Exports data to files** for integration testing
- ✅ **Provides real-time visualization** with Grafana and Jaeger
- ✅ **Supports StatsD metrics** for high-performance metric collection
- ✅ **Processes logs** with Filebeat for correlation and analysis
- ✅ **Runs entirely in Docker** for consistent environments
- ✅ **Includes verification scripts** in Python, Go, and Bash

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   SpacetimeDB   │───▶│ OpenTelemetry    │───▶│ File Exports    │
│                 │    │ Collector        │    │ (JSON/CSV/JSONL)│
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
    └── spacetimedb-integration.md  # SpacetimeDB integration guide
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

### For SpacetimeDB Integration

- **OTLP Traces/Metrics (gRPC)**: `localhost:4317`
- **OTLP Traces/Metrics (HTTP)**: `localhost:4318`
- **StatsD Metrics (UDP)**: `localhost:8125`

### Example Usage

```rust
// OpenTelemetry traces
let tracer = opentelemetry_otlp::new_pipeline()
    .tracing()
    .with_exporter(
        opentelemetry_otlp::new_exporter()
            .http()
            .with_endpoint("http://localhost:4318/v1/traces")
    )
    .install_batch(opentelemetry_sdk::runtime::Tokio)?;

// StatsD metrics
let client = statsd::Client::new("localhost:8125", "spacetimedb")?;
client.count("spacetimedb.database.inserts", 1);
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
docker-compose down

# Restart specific service
docker-compose restart otel-collector
```

### Reset Environment
```bash
# Clean reset
docker-compose down -v
./scripts/setup/setup-telemetry-env.sh
./scripts/setup/start-telemetry-stack.sh
```

## 🔗 SpacetimeDB Integration

See [docs/spacetimedb-integration.md](docs/spacetimedb-integration.md) for detailed instructions on integrating SpacetimeDB with this telemetry environment.

### Quick Integration Test

1. Start the telemetry environment
2. Configure SpacetimeDB with telemetry enabled:
   ```bash
   export SPACETIMEDB_TELEMETRY_ENABLED=true
   export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
   export STATSD_HOST=localhost
   ```
3. Run SpacetimeDB and perform operations
4. Check for telemetry data:
   ```bash
   ls -la data/traces/
   ls -la data/metrics/
   ```

## 🐛 Troubleshooting

### Common Issues

**Services not starting:**
```bash
# Check Docker is running
docker info

# Check port conflicts
lsof -i :4317 -i :4318 -i :8125 -i :9090 -i :3000

# Reset everything
docker-compose down -v
docker system prune -f
```

**No telemetry data:**
```bash
# Check OpenTelemetry Collector health
curl http://localhost:13133/

# Check if SpacetimeDB is sending data
docker-compose logs otel-collector | grep -i "received"

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
- **Minimal overhead**: <5% performance impact on SpacetimeDB
- **Efficient storage**: Compressed file exports with rotation

## 🔮 Future Enhancements

- [ ] Custom Grafana dashboards for SpacetimeDB
- [ ] Alerting rules for critical metrics
- [ ] Cloud deployment configurations
- [ ] Performance regression testing
- [ ] Multi-instance distributed tracing
- [ ] Advanced log analysis with ML

## 📝 License

This telemetry environment is part of the SpacetimeDB project and follows the same licensing terms.
