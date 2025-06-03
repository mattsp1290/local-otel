# SigNoz Configuration Options

## Overview

We provide three different configuration options for the observability stack:

### 1. Original Stack (`docker-compose.yml`)
- **When to use**: If you want to keep using the existing tools you're familiar with
- **Components**: OpenTelemetry Collector, StatsD, Prometheus, Grafana, Jaeger, Filebeat
- **Pros**: Familiar tools, each specialized for its purpose
- **Cons**: Multiple UIs to check, more resources required

### 2. Full Migration (`docker-compose.signoz.yml`)
- **When to use**: During transition period when you want both old and new tools running
- **Components**: All original tools PLUS SigNoz
- **Pros**: Can compare data between systems, gradual migration path
- **Cons**: Highest resource usage, redundant functionality

### 3. Minimal SigNoz Stack (`docker-compose.signoz-minimal.yml`) ⭐ RECOMMENDED
- **When to use**: For a clean, efficient setup with SigNoz as primary observability platform
- **Components**: SigNoz, OpenTelemetry Collector, StatsD, Filebeat
- **Pros**: Single UI for traces/metrics/logs, lower resource usage, simpler architecture
- **Cons**: Need to learn SigNoz if coming from Jaeger/Grafana

## Component Comparison

| Feature | Original Stack | SigNoz Minimal |
|---------|---------------|----------------|
| **Traces UI** | Jaeger | SigNoz |
| **Metrics UI** | Grafana + Prometheus | SigNoz |
| **Logs UI** | None (files only) | SigNoz |
| **Dashboards** | Grafana | SigNoz |
| **Alerts** | Prometheus Alertmanager | SigNoz Alertmanager |
| **Storage** | Prometheus (metrics) | ClickHouse (all data) |
| **File Exports** | ✅ Yes | ✅ Yes |
| **StatsD Support** | ✅ Yes | ✅ Yes |

## What SigNoz Replaces

### Replaces Jaeger
- Full distributed tracing with better search capabilities
- Trace-to-logs correlation
- Service dependency graphs
- RED metrics from traces

### Replaces Grafana
- Built-in dashboards for common metrics
- Custom dashboard builder
- PromQL-compatible query language
- Better integration with traces and logs

### Replaces Prometheus
- ClickHouse provides more efficient storage
- Longer retention at lower cost
- Built-in downsampling
- Still supports PromQL queries

## Resource Usage Comparison

### Original Stack
- ~2.5 GB RAM total
- 6 separate containers
- Multiple databases (Prometheus TSDB)

### SigNoz Minimal
- ~1.8 GB RAM total
- 7 containers (but simpler architecture)
- Single database (ClickHouse)

## Quick Start Commands

```bash
# Option 1: Use minimal SigNoz stack (RECOMMENDED)
docker-compose -f docker-compose.signoz-minimal.yml up -d

# Option 2: Use full migration stack (for comparison)
docker-compose -f docker-compose.signoz.yml up -d

# Option 3: Use original stack (no SigNoz)
docker-compose up -d
```

## Migration Path

1. **Start with minimal**: Use `docker-compose.signoz-minimal.yml`
2. **Import dashboards**: Recreate important Grafana dashboards in SigNoz
3. **Update alerts**: Migrate Prometheus alerts to SigNoz format
4. **Train team**: SigNoz UI is intuitive but different from Jaeger/Grafana
5. **Retire old stack**: Once comfortable, you're already using the minimal setup!

## File Exports Still Work!

Regardless of which configuration you choose:
- Traces still export to `/data/traces/`
- Metrics still export to `/data/metrics/`
- Logs still export to `/data/logs/`
- All your integration tests continue to work

## FAQ

**Q: Can I still use my Grafana dashboards?**
A: You'll need to recreate them in SigNoz, but SigNoz supports PromQL so queries are similar.

**Q: What about my Prometheus recording rules?**
A: SigNoz supports similar functionality through its query engine.

**Q: Is ClickHouse reliable for production?**
A: Yes! It's used by many large companies and is more efficient than Prometheus for this use case.

**Q: Can I export from SigNoz to other systems?**
A: Yes, SigNoz can forward data via OpenTelemetry exporters if needed.
