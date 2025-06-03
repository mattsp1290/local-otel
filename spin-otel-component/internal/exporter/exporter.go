package exporter

import "github.com/local-otel/spin-otel-component/internal/types"

// Exporter is the interface for telemetry exporters
type Exporter interface {
	ExportLogs(logs []types.LogRecord) error
	ExportTraces(spans []types.SpanData) error
	ExportMetrics(metrics []types.MetricPoint) error
}
