# Agent Observability Verifier - Integration Test Guide

## 🚀 Quick Start (Once Docker is Running)

### Prerequisites
✅ **Docker Desktop**: Installed and running  
✅ **Python 3.12+**: Available  
✅ **Go 1.21+**: Available  
✅ **All scripts**: Executable and ready  

### Step-by-Step Integration Testing

#### 1. **Environment Setup**
```bash
cd local-otel
./scripts/setup/setup-telemetry-env.sh
```
**Expected Output:**
- ✓ Docker prerequisites check
- ✓ Directory structure creation
- ✓ Docker network and volume setup
- ✓ Docker image pulling (6 images)
- ✓ Configuration validation

#### 2. **Start Telemetry Stack**
```bash
./scripts/setup/start-telemetry-stack.sh
```
**Expected Output:**
- ✓ Services starting in dependency order
- ✓ Health checks for all 6 services
- ✓ Service URLs displayed
- ✓ Container status summary

#### 3. **Health Verification**
```bash
./scripts/verification/bash/check_telemetry_health.sh
```
**Expected Output:**
- ✓ All 6 containers running
- ✓ Service endpoints responding
- ✓ Data directories accessible
- ✓ Network connectivity verified
- ✓ Configuration files validated

#### 4. **Python Pipeline Test**
```bash
./scripts/verification/python/test_metrics_pipeline.py
```
**Expected Output:**
- ✓ Service health checks pass
- ✓ StatsD metrics sent successfully
- ✓ OTLP traces sent successfully
- ✓ OTLP metrics sent successfully
- ✓ File exports verified
- ✓ Prometheus metrics available

#### 5. **Go Trace Generation**
```bash
cd scripts/verification/go
go run trace_generator.go
```
**Expected Output:**
- ✓ OpenTelemetry Collector availability check
- ✓ 10 realistic application traces generated
- ✓ All traces sent successfully
- ✓ Jaeger UI link provided

## 📊 Service Access Points

Once running, access these services:

| Service | URL | Credentials |
|---------|-----|-------------|
| **Grafana** | http://localhost:3000 | admin/admin |
| **Prometheus** | http://localhost:9090 | None |
| **Jaeger** | http://localhost:16686 | None |
| **OpenTelemetry Health** | http://localhost:13133 | None |

## 📁 File Exports Verification

Check these directories for telemetry data:

```bash
# Traces (JSON/JSONL format)
ls -la data/traces/
cat data/traces/traces.jsonl | head -5

# Metrics (JSON/Prometheus format)
ls -la data/metrics/
cat data/metrics/metrics.jsonl | head -5
cat data/metrics/metrics.prom | grep canary

# Logs (JSON format)
ls -la data/logs/
cat data/logs/canary-api-logs.jsonl | head -5

# Processed logs (Filebeat output)
ls -la data/processed/
```

## 🧪 Integration Test Scenarios

### Scenario 1: Basic Pipeline Test
1. Start telemetry stack
2. Send test data via Python script
3. Verify data in Grafana/Jaeger
4. Check file exports

### Scenario 2: Load Testing
1. Run Go trace generator multiple times
2. Monitor service performance
3. Verify data throughput
4. Check file rotation

### Scenario 3: Service Recovery
1. Stop individual services
2. Restart and verify recovery
3. Check data continuity
4. Validate health checks

### Scenario 4: Application Integration
1. Run example application (see `docs/application-integration-guide.md`)
2. Generate traffic to endpoints (/chirp, /nest, /flock)
3. Verify traces in Jaeger
4. Check metrics in Prometheus/Grafana

## 🔧 Troubleshooting

### Common Issues

**Services not starting:**
```bash
# Check Docker resources
docker system df
docker system prune -f

# Restart with clean slate
./scripts/setup/stop-telemetry-stack.sh --clean-data --remove-volumes
./scripts/setup/setup-telemetry-env.sh
```

**No telemetry data:**
```bash
# Check OpenTelemetry Collector logs
docker-compose logs otel-collector

# Verify endpoints
curl http://localhost:13133/
curl http://localhost:4318/v1/traces
```

**File permissions:**
```bash
# Fix data directory permissions
chmod -R 755 data/
```

## 📈 Success Criteria

### ✅ **Full Success** (100%)
- All 6 containers running healthy
- All service endpoints responding
- Test data flowing through pipeline
- Files being created in all directories
- Dashboards showing application data
- 100% test pass rate

### ✅ **Partial Success** (80%+)
- Most containers running
- Core services (OTel, Prometheus) working
- Some test data flowing
- Basic file exports working
- 80%+ test pass rate

### ❌ **Needs Investigation** (<80%)
- Multiple container failures
- Service endpoint issues
- No data flow
- File export failures
- <80% test pass rate

## 🚀 Next Steps After Success

1. **Application Integration**: Follow `docs/application-integration-guide.md`
2. **Custom Dashboards**: Create application-specific Grafana dashboards
3. **Production Setup**: Adapt configuration for production deployment
4. **Monitoring**: Set up alerting and monitoring rules

## 🐦 Testing with Canary API

Quick test with our example API:

```bash
# Send metrics via StatsD
echo "canary.requests:1|c|#endpoint:chirp,method:GET" | nc -u -w0 localhost 8125
echo "canary.response_time:42|ms|#endpoint:nest" | nc -u -w0 localhost 8125

# Send trace via OTLP HTTP
curl -X POST http://localhost:4318/v1/traces \
  -H "Content-Type: application/json" \
  -d '{
    "resourceSpans": [{
      "resource": {
        "attributes": [{
          "key": "service.name",
          "value": {"stringValue": "canary-api"}
        }]
      },
      "scopeSpans": [{
        "scope": {"name": "test"},
        "spans": [{
          "traceId": "5b8aa5a2d2c872e8321cf37308d69df2",
          "spanId": "051581bf3cb55c13",
          "name": "chirp-request",
          "startTimeUnixNano": "'$(date +%s%N)'",
          "endTimeUnixNano": "'$(date +%s%N)'",
          "kind": 2,
          "attributes": [{
            "key": "http.method",
            "value": {"stringValue": "GET"}
          }, {
            "key": "http.path",
            "value": {"stringValue": "/chirp"}
          }]
        }]
      }]
    }]
  }'

# Check results
docker logs telemetry-nest-otel-collector | tail -20
ls -la data/traces/
```

## 📝 Test Results Template

```
Date: ___________
Tester: ___________

Environment Setup: ✅/❌
Service Startup: ✅/❌
Health Checks: ✅/❌ (__/6 services healthy)
Python Tests: ✅/❌ (__/5 tests passed)
Go Trace Generation: ✅/❌ (__/10 traces sent)
File Exports: ✅/❌
Dashboard Access: ✅/❌

Overall Success Rate: ___%
Notes: ___________
```

---

**Ready to test? Start Docker Desktop and run the commands above!**
