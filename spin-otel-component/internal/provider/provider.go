package provider

import (
	"fmt"
	"sync"
	"time"

	"github.com/local-otel/spin-otel-component/internal/batching"
	"github.com/local-otel/spin-otel-component/internal/exporter"
	"github.com/local-otel/spin-otel-component/internal/exporter/debug"
	"github.com/local-otel/spin-otel-component/internal/logger"
	"github.com/local-otel/spin-otel-component/internal/meter"
	"github.com/local-otel/spin-otel-component/internal/tracer"
	"github.com/local-otel/spin-otel-component/internal/types"
)

// Provider represents the main telemetry provider
type Provider struct {
	config        *types.ProviderConfig
	exporters     map[types.ExportProtocol]exporter.Exporter
	logBatcher    *batching.Batcher[types.LogRecord]
	traceBatcher  *batching.Batcher[types.SpanData]
	metricBatcher *batching.Batcher[types.MetricPoint]
	mu            sync.RWMutex
	shutdown      bool
}

// NewProvider creates a new telemetry provider
func NewProvider() *Provider {
	return &Provider{
		exporters: make(map[types.ExportProtocol]exporter.Exporter),
		shutdown:  false,
	}
}

// Initialize sets up the provider with the given configuration
func (p *Provider) Initialize(config *types.ProviderConfig) error {
	p.mu.Lock()
	defer p.mu.Unlock()

	if p.shutdown {
		return fmt.Errorf("provider is shut down")
	}

	p.config = config

	// Create exporters based on protocol
	switch config.Protocol {
	case types.ExportProtocolOTLPHTTP:
		// TODO: Implement OTLP HTTP exporter
		return fmt.Errorf("OTLP HTTP exporter not yet implemented")
	case types.ExportProtocolDebugStdout:
		p.exporters[types.ExportProtocolDebugStdout] = debug.NewDebugExporter()
	default:
		return fmt.Errorf("unsupported protocol: %v", config.Protocol)
	}

	// Initialize batchers
	p.logBatcher = batching.NewBatcher[types.LogRecord](
		int(config.BatchSize),
		time.Duration(config.TimeoutMs)*time.Millisecond,
		func(items []types.LogRecord) error {
			return p.exportLogs(items)
		},
	)

	p.traceBatcher = batching.NewBatcher[types.SpanData](
		int(config.BatchSize),
		time.Duration(config.TimeoutMs)*time.Millisecond,
		func(items []types.SpanData) error {
			return p.exportTraces(items)
		},
	)

	p.metricBatcher = batching.NewBatcher[types.MetricPoint](
		int(config.BatchSize),
		time.Duration(config.TimeoutMs)*time.Millisecond,
		func(items []types.MetricPoint) error {
			return p.exportMetrics(items)
		},
	)

	return nil
}

// CreateLogger creates a new logger instance
func (p *Provider) CreateLogger(name string, version *string) (*logger.Logger, error) {
	p.mu.RLock()
	defer p.mu.RUnlock()

	if p.shutdown {
		return nil, fmt.Errorf("provider is shut down")
	}

	return logger.NewLogger(p, name, version), nil
}

// CreateTracer creates a new tracer instance
func (p *Provider) CreateTracer(name string, version *string) (*tracer.Tracer, error) {
	p.mu.RLock()
	defer p.mu.RUnlock()

	if p.shutdown {
		return nil, fmt.Errorf("provider is shut down")
	}

	return tracer.NewTracer(p, name, version), nil
}

// CreateMeter creates a new meter instance
func (p *Provider) CreateMeter(name string, version *string) (*meter.Meter, error) {
	p.mu.RLock()
	defer p.mu.RUnlock()

	if p.shutdown {
		return nil, fmt.Errorf("provider is shut down")
	}

	return meter.NewMeter(p, name, version), nil
}

// GetConfig returns the provider configuration (implements LoggerProvider, TracerProvider, MeterProvider)
func (p *Provider) GetConfig() *types.ProviderConfig {
	p.mu.RLock()
	defer p.mu.RUnlock()
	return p.config
}

// GetLogBatcher returns the log batcher (implements LoggerProvider)
func (p *Provider) GetLogBatcher() logger.LogBatcher {
	p.mu.RLock()
	defer p.mu.RUnlock()
	return p.logBatcher
}

// GetTraceBatcher returns the trace batcher (implements TracerProvider)
func (p *Provider) GetTraceBatcher() tracer.TraceBatcher {
	p.mu.RLock()
	defer p.mu.RUnlock()
	return p.traceBatcher
}

// GetMetricBatcher returns the metric batcher (implements MeterProvider)
func (p *Provider) GetMetricBatcher() meter.MetricBatcher {
	p.mu.RLock()
	defer p.mu.RUnlock()
	return p.metricBatcher
}

// ExportLogs exports logs (implements LoggerProvider)
func (p *Provider) ExportLogs(logs []types.LogRecord) error {
	return p.exportLogs(logs)
}

// ExportTraces exports traces (implements TracerProvider)
func (p *Provider) ExportTraces(spans []types.SpanData) error {
	return p.exportTraces(spans)
}

// ExportMetrics exports metrics (implements MeterProvider)
func (p *Provider) ExportMetrics(metrics []types.MetricPoint) error {
	return p.exportMetrics(metrics)
}

// ForceFlush forces all pending telemetry to be exported
func (p *Provider) ForceFlush() error {
	p.mu.RLock()
	defer p.mu.RUnlock()

	if p.shutdown {
		return fmt.Errorf("provider is shut down")
	}

	// Flush all batchers
	if p.logBatcher != nil {
		if err := p.logBatcher.Flush(); err != nil {
			return fmt.Errorf("failed to flush logs: %w", err)
		}
	}

	if p.traceBatcher != nil {
		if err := p.traceBatcher.Flush(); err != nil {
			return fmt.Errorf("failed to flush traces: %w", err)
		}
	}

	if p.metricBatcher != nil {
		if err := p.metricBatcher.Flush(); err != nil {
			return fmt.Errorf("failed to flush metrics: %w", err)
		}
	}

	return nil
}

// Shutdown shuts down the provider and releases resources
func (p *Provider) Shutdown() error {
	p.mu.Lock()
	defer p.mu.Unlock()

	if p.shutdown {
		return nil
	}

	// Force flush all pending data
	if err := p.ForceFlush(); err != nil {
		return fmt.Errorf("failed to flush during shutdown: %w", err)
	}

	// Stop all batchers
	if p.logBatcher != nil {
		p.logBatcher.Stop()
	}

	if p.traceBatcher != nil {
		p.traceBatcher.Stop()
	}

	if p.metricBatcher != nil {
		p.metricBatcher.Stop()
	}

	p.shutdown = true
	return nil
}

// exportLogs exports a batch of logs
func (p *Provider) exportLogs(logs []types.LogRecord) error {
	p.mu.RLock()
	defer p.mu.RUnlock()

	for _, exp := range p.exporters {
		if err := exp.ExportLogs(logs); err != nil {
			if p.config.DevMode {
				fmt.Printf("Failed to export logs: %v\n", err)
			}
			// Continue with other exporters even if one fails
		}
	}

	return nil
}

// exportTraces exports a batch of traces
func (p *Provider) exportTraces(spans []types.SpanData) error {
	p.mu.RLock()
	defer p.mu.RUnlock()

	for _, exp := range p.exporters {
		if err := exp.ExportTraces(spans); err != nil {
			if p.config.DevMode {
				fmt.Printf("Failed to export traces: %v\n", err)
			}
			// Continue with other exporters even if one fails
		}
	}

	return nil
}

// exportMetrics exports a batch of metrics
func (p *Provider) exportMetrics(metrics []types.MetricPoint) error {
	p.mu.RLock()
	defer p.mu.RUnlock()

	for _, exp := range p.exporters {
		if err := exp.ExportMetrics(metrics); err != nil {
			if p.config.DevMode {
				fmt.Printf("Failed to export metrics: %v\n", err)
			}
			// Continue with other exporters even if one fails
		}
	}

	return nil
}
