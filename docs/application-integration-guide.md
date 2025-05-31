# Application Telemetry Integration Guide

This guide shows how to integrate any application with the Agent Observability Verifier to send traces, metrics, and logs.

## Overview

The telemetry stack is ready to receive observability data from your application via standard protocols:
- **OpenTelemetry (OTLP)** for traces and metrics
- **StatsD** for high-performance metrics
- **JSON logs** for structured logging

## Quick Integration Examples

### 🐍 Python + FastAPI

```python
# requirements.txt
opentelemetry-api==1.20.0
opentelemetry-sdk==1.20.0
opentelemetry-exporter-otlp==1.20.0
opentelemetry-instrumentation-fastapi==0.41b0
statsd==4.0.1

# app.py
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
import statsd
import logging
import json

# Setup tracing
resource = Resource.create({"service.name": "canary-api"})
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)

# Configure OTLP exporter
otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4318/v1/traces")
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Setup metrics
statsd_client = statsd.StatsClient('localhost', 8125, prefix='canary')

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","service":"canary-api","message":"%(message)s"}',
    datefmt='%Y-%m-%dT%H:%M:%S.%fZ'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI()
FastAPIInstrumentor.instrument_app(app)

@app.get("/chirp")
async def chirp():
    with tracer.start_as_current_span("chirp_handler"):
        statsd_client.incr('requests', tags=['endpoint:chirp', 'method:GET'])
        logger.info('Handling chirp request', extra={'endpoint': '/chirp'})
        return {"message": "chirp chirp!"}

@app.post("/nest")
async def nest(data: dict):
    with tracer.start_as_current_span("nest_handler"):
        statsd_client.incr('requests', tags=['endpoint:nest', 'method:POST'])
        statsd_client.gauge('request_size', len(str(data)))
        logger.info('Creating nest entry', extra={'endpoint': '/nest', 'size': len(str(data))})
        return {"id": "nest_123", "data": data}
```

### 🟢 Node.js + Express

```javascript
// package.json dependencies
{
  "dependencies": {
    "@opentelemetry/api": "^1.4.0",
    "@opentelemetry/auto-instrumentations-node": "^0.37.0",
    "@opentelemetry/exporter-trace-otlp-http": "^0.37.0",
    "@opentelemetry/resources": "^1.9.0",
    "@opentelemetry/sdk-node": "^0.37.0",
    "@opentelemetry/semantic-conventions": "^1.9.0",
    "express": "^4.18.0",
    "node-statsd": "^0.1.1",
    "winston": "^3.8.0"
  }
}

// telemetry.js
const { NodeSDK } = require('@opentelemetry/sdk-node');
const { getNodeAutoInstrumentations } = require('@opentelemetry/auto-instrumentations-node');
const { Resource } = require('@opentelemetry/resources');
const { SemanticResourceAttributes } = require('@opentelemetry/semantic-conventions');
const { OTLPTraceExporter } = require('@opentelemetry/exporter-trace-otlp-http');

const traceExporter = new OTLPTraceExporter({
  url: 'http://localhost:4318/v1/traces',
});

const sdk = new NodeSDK({
  resource: new Resource({
    [SemanticResourceAttributes.SERVICE_NAME]: 'canary-api',
    [SemanticResourceAttributes.SERVICE_VERSION]: '1.0.0',
  }),
  traceExporter,
  instrumentations: [getNodeAutoInstrumentations()]
});

sdk.start();

// app.js
const express = require('express');
const StatsD = require('node-statsd');
const winston = require('winston');

const app = express();
app.use(express.json());

// Setup metrics
const statsd = new StatsD({
  host: 'localhost',
  port: 8125,
  prefix: 'canary.'
});

// Setup structured logging
const logger = winston.createLogger({
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  defaultMeta: { service: 'canary-api' },
  transports: [
    new winston.transports.File({ filename: 'data/logs/canary-api.jsonl' }),
    new winston.transports.Console()
  ]
});

app.get('/chirp', (req, res) => {
  statsd.increment('requests', 1, ['endpoint:chirp', 'method:GET']);
  logger.info('Handling chirp request', { endpoint: '/chirp' });
  res.json({ message: 'chirp chirp!' });
});

app.post('/nest', (req, res) => {
  statsd.increment('requests', 1, ['endpoint:nest', 'method:POST']);
  statsd.gauge('request_size', JSON.stringify(req.body).length);
  logger.info('Creating nest entry', { 
    endpoint: '/nest', 
    size: JSON.stringify(req.body).length 
  });
  res.json({ id: 'nest_123', data: req.body });
});

app.listen(3000, () => {
  logger.info('Canary API listening on port 3000');
});
```

### 🔷 Go + Gin

```go
// go.mod
module canary-api

go 1.21

require (
    github.com/gin-gonic/gin v1.9.1
    go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin v0.42.0
    go.opentelemetry.io/otel v1.16.0
    go.opentelemetry.io/otel/exporters/otlp/otlptrace v1.16.0
    go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc v1.16.0
    go.opentelemetry.io/otel/sdk v1.16.0
    github.com/cactus/go-statsd-client/v5 v5.0.0
    github.com/sirupsen/logrus v1.9.3
)

// main.go
package main

import (
    "context"
    "encoding/json"
    "fmt"
    "time"

    "github.com/gin-gonic/gin"
    "github.com/cactus/go-statsd-client/v5/statsd"
    "github.com/sirupsen/logrus"
    "go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin"
    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/attribute"
    "go.opentelemetry.io/otel/exporters/otlp/otlptrace"
    "go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
    "go.opentelemetry.io/otel/sdk/resource"
    sdktrace "go.opentelemetry.io/otel/sdk/trace"
    semconv "go.opentelemetry.io/otel/semconv/v1.17.0"
)

var (
    tracer = otel.Tracer("canary-api")
    metrics statsd.Statter
    logger *logrus.Logger
)

func initTelemetry(ctx context.Context) error {
    // Setup tracing
    exporter, err := otlptrace.New(
        ctx,
        otlptracegrpc.NewClient(
            otlptracegrpc.WithEndpoint("localhost:4317"),
            otlptracegrpc.WithInsecure(),
        ),
    )
    if err != nil {
        return err
    }

    tp := sdktrace.NewTracerProvider(
        sdktrace.WithSampler(sdktrace.AlwaysSample()),
        sdktrace.WithBatcher(exporter),
        sdktrace.WithResource(resource.NewWithAttributes(
            semconv.SchemaURL,
            semconv.ServiceNameKey.String("canary-api"),
            semconv.ServiceVersionKey.String("1.0.0"),
        )),
    )
    otel.SetTracerProvider(tp)

    // Setup metrics
    config := &statsd.ClientConfig{
        Address:       "127.0.0.1:8125",
        Prefix:        "canary",
        UseBuffered:   true,
        FlushInterval: 300 * time.Millisecond,
    }
    metrics, err = statsd.NewClientWithConfig(config)
    if err != nil {
        return err
    }

    // Setup logging
    logger = logrus.New()
    logger.SetFormatter(&logrus.JSONFormatter{
        TimestampFormat: time.RFC3339Nano,
    })
    logger.SetLevel(logrus.InfoLevel)

    return nil
}

func main() {
    ctx := context.Background()
    if err := initTelemetry(ctx); err != nil {
        panic(err)
    }
    defer metrics.Close()

    r := gin.Default()
    r.Use(otelgin.Middleware("canary-api"))

    r.GET("/chirp", func(c *gin.Context) {
        ctx, span := tracer.Start(c.Request.Context(), "chirp_handler")
        defer span.End()

        metrics.Inc("requests", 1, 1.0, statsd.Tag{"endpoint", "chirp"}, statsd.Tag{"method", "GET"})
        logger.WithFields(logrus.Fields{
            "endpoint": "/chirp",
            "method":   "GET",
            "trace_id": span.SpanContext().TraceID().String(),
        }).Info("Handling chirp request")

        c.JSON(200, gin.H{"message": "chirp chirp!"})
    })

    r.POST("/nest", func(c *gin.Context) {
        ctx, span := tracer.Start(c.Request.Context(), "nest_handler")
        defer span.End()

        var data map[string]interface{}
        c.BindJSON(&data)
        
        dataSize := len(fmt.Sprintf("%v", data))
        span.SetAttributes(attribute.Int("request.size", dataSize))

        metrics.Inc("requests", 1, 1.0, statsd.Tag{"endpoint", "nest"}, statsd.Tag{"method", "POST"})
        metrics.Gauge("request_size", dataSize, 1.0)
        
        logger.WithFields(logrus.Fields{
            "endpoint":     "/nest",
            "method":       "POST",
            "request_size": dataSize,
            "trace_id":     span.SpanContext().TraceID().String(),
        }).Info("Creating nest entry")

        c.JSON(201, gin.H{"id": "nest_123", "data": data})
    })

    r.Run(":8080")
}
```

### ☕ Java + Spring Boot

```java
// pom.xml dependencies
<dependencies>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
        <groupId>io.opentelemetry</groupId>
        <artifactId>opentelemetry-api</artifactId>
        <version>1.28.0</version>
    </dependency>
    <dependency>
        <groupId>io.opentelemetry</groupId>
        <artifactId>opentelemetry-sdk</artifactId>
        <version>1.28.0</version>
    </dependency>
    <dependency>
        <groupId>io.opentelemetry</groupId>
        <artifactId>opentelemetry-exporter-otlp</artifactId>
        <version>1.28.0</version>
    </dependency>
    <dependency>
        <groupId>io.opentelemetry.instrumentation</groupId>
        <artifactId>opentelemetry-spring-boot-starter</artifactId>
        <version>1.28.0-alpha</version>
    </dependency>
    <dependency>
        <groupId>com.timgroup</groupId>
        <artifactId>java-statsd-client</artifactId>
        <version>3.1.0</version>
    </dependency>
    <dependency>
        <groupId>net.logstash.logback</groupId>
        <artifactId>logstash-logback-encoder</artifactId>
        <version>7.3</version>
    </dependency>
</dependencies>

// application.yml
otel:
  exporter:
    otlp:
      endpoint: http://localhost:4318
      protocol: http/protobuf
  resource:
    attributes:
      service.name: canary-api
      service.version: 1.0.0

logging:
  pattern:
    console: "%d{ISO8601} [%thread] %-5level %logger{36} - %msg%n"
  level:
    root: INFO

// CanaryApiApplication.java
@SpringBootApplication
public class CanaryApiApplication {
    public static void main(String[] args) {
        SpringApplication.run(CanaryApiApplication.class, args);
    }
}

// TelemetryConfig.java
@Configuration
public class TelemetryConfig {
    
    @Bean
    public StatsDClient statsDClient() {
        return new NonBlockingStatsDClient("canary", "localhost", 8125);
    }
    
    @Bean
    public Tracer tracer() {
        return GlobalOpenTelemetry.getTracer("canary-api");
    }
}

// CanaryController.java
@RestController
@Slf4j
public class CanaryController {
    
    private final StatsDClient statsD;
    private final Tracer tracer;
    
    @Autowired
    public CanaryController(StatsDClient statsD, Tracer tracer) {
        this.statsD = statsD;
        this.tracer = tracer;
    }
    
    @GetMapping("/chirp")
    public Map<String, String> chirp() {
        Span span = tracer.spanBuilder("chirp_handler").startSpan();
        try (Scope scope = span.makeCurrent()) {
            statsD.incrementCounter("requests", "endpoint:chirp", "method:GET");
            log.info("Handling chirp request");
            return Map.of("message", "chirp chirp!");
        } finally {
            span.end();
        }
    }
    
    @PostMapping("/nest")
    public Map<String, Object> nest(@RequestBody Map<String, Object> data) {
        Span span = tracer.spanBuilder("nest_handler").startSpan();
        try (Scope scope = span.makeCurrent()) {
            int size = data.toString().length();
            span.setAttribute("request.size", size);
            
            statsD.incrementCounter("requests", "endpoint:nest", "method:POST");
            statsD.recordGaugeValue("request_size", size);
            
            log.info("Creating nest entry with size: {}", size);
            return Map.of("id", "nest_123", "data", data);
        } finally {
            span.end();
        }
    }
}
```

## Environment Variables

Set these environment variables for your application:

```bash
# OpenTelemetry
export OTEL_SERVICE_NAME=canary-api
export OTEL_SERVICE_VERSION=1.0.0
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf

# StatsD (if not using default localhost:8125)
export STATSD_HOST=localhost
export STATSD_PORT=8125

# Logging
export LOG_LEVEL=INFO
```

## Testing Your Integration

1. **Start the telemetry stack:**
   ```bash
   ./scripts/setup/start-telemetry-stack.sh
   ```

2. **Run your application** with the environment variables set

3. **Generate some traffic:**
   ```bash
   # Test the endpoints
   curl http://localhost:3000/chirp
   curl -X POST http://localhost:3000/nest \
     -H "Content-Type: application/json" \
     -d '{"type": "cozy", "material": "twigs"}'
   ```

4. **Verify telemetry is being collected:**
   ```bash
   # Check for traces
   ls -la data/traces/
   tail -f data/traces/traces.jsonl

   # Check for metrics
   cat data/metrics/metrics.prom | grep canary

   # Check for logs
   tail -f data/logs/canary*.jsonl
   ```

5. **View in dashboards:**
   - **Jaeger**: http://localhost:16686 - Search for "canary-api" service
   - **Grafana**: http://localhost:3000 - View metrics dashboards
   - **Prometheus**: http://localhost:9090 - Query metrics directly

## Direct Protocol Examples

### Send Trace via OTLP HTTP

```bash
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
        "scope": {"name": "manual-test"},
        "spans": [{
          "traceId": "5b8aa5a2d2c872e8321cf37308d69df2",
          "spanId": "051581bf3cb55c13",
          "name": "test-span",
          "startTimeUnixNano": "'$(date +%s%N)'",
          "endTimeUnixNano": "'$(date +%s%N)'",
          "kind": 1,
          "attributes": [{
            "key": "test",
            "value": {"stringValue": "true"}
          }]
        }]
      }]
    }]
  }'
```

### Send Metric via StatsD

```bash
# Increment counter
echo "canary.requests:1|c|#endpoint:chirp,method:GET" | nc -u -w0 localhost 8125

# Set gauge
echo "canary.active_connections:42|g" | nc -u -w0 localhost 8125

# Record timing
echo "canary.response_time:125|ms|#endpoint:nest" | nc -u -w0 localhost 8125
```

### Write Structured Log

```bash
echo '{"timestamp":"'$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)'","level":"INFO","service":"canary-api","message":"Manual log entry","endpoint":"/chirp"}' >> data/logs/canary-api.jsonl
```

## Best Practices

1. **Service Naming**: Use consistent service names across traces, metrics, and logs
2. **Resource Attributes**: Always include service.name and service.version
3. **Error Handling**: Instrument error cases with appropriate span status
4. **Sampling**: Use appropriate sampling rates for production
5. **Batching**: Configure appropriate batch sizes for exporters
6. **Correlation**: Include trace IDs in logs for correlation

## Troubleshooting

### No Data Appearing?

1. **Check endpoints are correct:**
   - OTLP gRPC: `localhost:4317`
   - OTLP HTTP: `localhost:4318`
   - StatsD UDP: `localhost:8125`

2. **Verify services are running:**
   ```bash
   docker ps | grep telemetry-nest
   ```

3. **Check collector logs:**
   ```bash
   docker logs telemetry-nest-otel-collector
   ```

4. **Test connectivity:**
   ```bash
   curl http://localhost:13133/  # OTel Collector health
   curl http://localhost:8126/   # StatsD admin
   ```

### Performance Considerations

- Use batch exporters for traces and metrics
- Configure appropriate flush intervals
- Use sampling for high-volume services
- Buffer StatsD metrics client-side

## Next Steps

1. Add custom dashboards in `docker/configs/grafana/dashboards/`
2. Configure alerts in Prometheus
3. Set up trace sampling strategies
4. Implement custom metrics for your domain
5. Add distributed tracing across services
