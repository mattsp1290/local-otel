package telemetry

import (
	"context"
	"log"
	"os"
	"time"

	"github.com/gin-gonic/gin"
	"go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.21.0"
	"go.opentelemetry.io/otel/trace"
)

var tracer trace.Tracer

// InitTelemetry initializes OpenTelemetry tracing
func InitTelemetry() func() {
	ctx := context.Background()

	// Create OTLP exporter
	endpoint := os.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
	if endpoint == "" {
		endpoint = "localhost:4318"
	}

	exporter, err := otlptrace.New(
		ctx,
		otlptracehttp.NewClient(
			otlptracehttp.WithEndpoint(endpoint),
			otlptracehttp.WithInsecure(),
		),
	)
	if err != nil {
		log.Fatalf("Failed to create OTLP exporter: %v", err)
	}

	// Create resource
	res, err := resource.New(ctx,
		resource.WithAttributes(
			semconv.ServiceName("feed-service"),
			semconv.ServiceVersion("1.0.0"),
			attribute.String("environment", os.Getenv("ENVIRONMENT")),
		),
		resource.WithHost(),
	)
	if err != nil {
		log.Fatalf("Failed to create resource: %v", err)
	}

	// Create tracer provider
	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exporter),
		sdktrace.WithResource(res),
	)

	// Set global tracer provider and propagator
	otel.SetTracerProvider(tp)
	otel.SetTextMapPropagator(propagation.TraceContext{})

	// Get tracer
	tracer = otel.Tracer("feed-service")

	// Return cleanup function
	return func() {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		if err := tp.Shutdown(ctx); err != nil {
			log.Printf("Error shutting down tracer provider: %v", err)
		}
	}
}

// TracingMiddleware returns Gin middleware for tracing
func TracingMiddleware() gin.HandlerFunc {
	return otelgin.Middleware("feed-service")
}

// LoggingMiddleware adds structured logging to requests
func LoggingMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		path := c.Request.URL.Path
		raw := c.Request.URL.RawQuery

		// Process request
		c.Next()

		// Get trace context
		span := trace.SpanFromContext(c.Request.Context())
		traceID := ""
		spanID := ""
		if span.SpanContext().IsValid() {
			traceID = span.SpanContext().TraceID().String()
			spanID = span.SpanContext().SpanID().String()
		}

		// Log request
		latency := time.Since(start)
		clientIP := c.ClientIP()
		method := c.Request.Method
		statusCode := c.Writer.Status()

		if raw != "" {
			path = path + "?" + raw
		}

		log.Printf(`{"timestamp":"%s","level":"INFO","service":"feed-service","trace_id":"%s","span_id":"%s","method":"%s","path":"%s","status":%d,"latency":%d,"client_ip":"%s"}`,
			time.Now().UTC().Format(time.RFC3339),
			traceID,
			spanID,
			method,
			path,
			statusCode,
			latency.Microseconds(),
			clientIP,
		)
	}
}

// GetTracer returns the global tracer
func GetTracer() trace.Tracer {
	if tracer == nil {
		return otel.Tracer("feed-service")
	}
	return tracer
}
