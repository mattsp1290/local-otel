package meter

import (
	"github.com/local-otel/spin-otel-component/internal/types"
)

// Meter represents a meter instance
type Meter struct {
	provider MeterProvider
	name     string
	version  *string
}

// MeterProvider is the interface that the provider must implement for meter
type MeterProvider interface {
	GetConfig() *types.ProviderConfig
	GetMetricBatcher() MetricBatcher
	ExportMetrics([]types.MetricPoint) error
}

// MetricBatcher is the interface for the metric batcher
type MetricBatcher interface {
	Add(types.MetricPoint) error
}

// NewMeter creates a new meter instance
func NewMeter(provider MeterProvider, name string, version *string) *Meter {
	return &Meter{
		provider: provider,
		name:     name,
		version:  version,
	}
}

// RecordMetrics records metric measurements (stub)
func (m *Meter) RecordMetrics(metrics []types.MetricPoint) error {
	// TODO: Implement metric recording
	return nil
}

// RecordAggregated records pre-aggregated metrics (stub)
func (m *Meter) RecordAggregated(metrics []types.AggregatedMetric) error {
	// TODO: Implement aggregated metric recording
	return nil
}

// CreateObservableCallback creates a callback for observable instruments (stub)
func (m *Meter) CreateObservableCallback(metricNames []string, callbackID string) error {
	// TODO: Implement observable callback
	return nil
}
