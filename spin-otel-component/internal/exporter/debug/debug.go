package debug

import (
	"encoding/json"
	"fmt"

	"github.com/local-otel/spin-otel-component/internal/types"
)

// DebugExporter exports telemetry to stdout for development
type DebugExporter struct{}

// NewDebugExporter creates a new debug exporter
func NewDebugExporter() *DebugExporter {
	return &DebugExporter{}
}

// ExportLogs exports logs to stdout
func (e *DebugExporter) ExportLogs(logs []types.LogRecord) error {
	fmt.Println("=== DEBUG: Exporting Logs ===")
	for i, log := range logs {
		fmt.Printf("Log %d:\n", i+1)
		fmt.Printf("  Timestamp: %v\n", log.TimestampNanos)
		fmt.Printf("  Severity: %s\n", log.Severity.String())
		fmt.Printf("  Body: %s\n", log.Body)

		if log.TraceContext != nil {
			fmt.Printf("  TraceID: %s\n", log.TraceContext.TraceID)
			fmt.Printf("  SpanID: %s\n", log.TraceContext.SpanID)
		}

		if len(log.Attributes) > 0 {
			fmt.Printf("  Attributes:\n")
			for _, attr := range log.Attributes {
				fmt.Printf("    %s: %s\n", attr.Key, attr.Value.String())
			}
		}

		if log.Resource != nil && len(log.Resource.Attributes) > 0 {
			fmt.Printf("  Resource:\n")
			for _, attr := range log.Resource.Attributes {
				fmt.Printf("    %s: %s\n", attr.Key, attr.Value.String())
			}
		}

		fmt.Println()
	}
	return nil
}

// ExportTraces exports traces to stdout
func (e *DebugExporter) ExportTraces(spans []types.SpanData) error {
	fmt.Println("=== DEBUG: Exporting Traces ===")
	data, err := json.MarshalIndent(spans, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal spans: %w", err)
	}
	fmt.Println(string(data))
	return nil
}

// ExportMetrics exports metrics to stdout
func (e *DebugExporter) ExportMetrics(metrics []types.MetricPoint) error {
	fmt.Println("=== DEBUG: Exporting Metrics ===")
	data, err := json.MarshalIndent(metrics, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal metrics: %w", err)
	}
	fmt.Println(string(data))
	return nil
}
