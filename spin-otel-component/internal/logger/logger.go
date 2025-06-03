package logger

import (
	"fmt"

	"github.com/local-otel/spin-otel-component/internal/types"
)

// Logger represents a logger instance
type Logger struct {
	provider      LoggerProvider
	name          string
	version       *string
	traceContext  *types.TraceContext
	correlationID *string
	requestID     *string
	sessionID     *string
}

// LoggerProvider is the interface that the provider must implement for logger
type LoggerProvider interface {
	GetConfig() *types.ProviderConfig
	GetLogBatcher() LogBatcher
	ExportLogs([]types.LogRecord) error
}

// LogBatcher is the interface for the log batcher
type LogBatcher interface {
	Add(types.LogRecord) error
}

// NewLogger creates a new logger instance
func NewLogger(provider LoggerProvider, name string, version *string) *Logger {
	return &Logger{
		provider: provider,
		name:     name,
		version:  version,
	}
}

// Emit emits a log record
func (l *Logger) Emit(record types.LogRecord) error {
	// Enrich log record with logger metadata
	enrichedRecord := record

	// Add resource information
	if config := l.provider.GetConfig(); config != nil {
		resource := &types.Resource{
			Attributes: []types.Attribute{
				{Key: "service.name", Value: types.StringValue(config.ServiceName)},
				{Key: "logger.name", Value: types.StringValue(l.name)},
			},
		}

		if config.ServiceVersion != nil {
			resource.Attributes = append(resource.Attributes,
				types.Attribute{Key: "service.version", Value: types.StringValue(*config.ServiceVersion)})
		}

		if config.Environment != nil {
			resource.Attributes = append(resource.Attributes,
				types.Attribute{Key: "deployment.environment", Value: types.StringValue(*config.Environment)})
		}

		// Add default tags
		enrichedRecord.Attributes = append(enrichedRecord.Attributes, config.DefaultTags...)

		enrichedRecord.Resource = resource
	}

	// Add logger version if provided
	if l.version != nil {
		enrichedRecord.Attributes = append(enrichedRecord.Attributes,
			types.Attribute{Key: "logger.version", Value: types.StringValue(*l.version)})
	}

	// Add trace context if set
	if l.traceContext != nil {
		enrichedRecord.TraceContext = l.traceContext
	}

	// Add correlation IDs
	if l.correlationID != nil {
		enrichedRecord.CorrelationID = l.correlationID
	}
	if l.requestID != nil {
		enrichedRecord.RequestID = l.requestID
	}
	if l.sessionID != nil {
		enrichedRecord.SessionID = l.sessionID
	}

	// Set timestamp if not provided
	if enrichedRecord.TimestampNanos == nil {
		nanos := types.GetNanoseconds()
		enrichedRecord.TimestampNanos = &nanos
	}

	// Add to batch
	if batcher := l.provider.GetLogBatcher(); batcher != nil {
		return batcher.Add(enrichedRecord)
	}

	// If no batcher, export directly
	return l.provider.ExportLogs([]types.LogRecord{enrichedRecord})
}

// EmitBatch emits multiple log records
func (l *Logger) EmitBatch(records []types.LogRecord) error {
	for _, record := range records {
		if err := l.Emit(record); err != nil {
			return fmt.Errorf("failed to emit log record: %w", err)
		}
	}
	return nil
}

// WithTraceContext creates a logger with trace context
func (l *Logger) WithTraceContext(context *types.TraceContext) (*Logger, error) {
	newLogger := *l
	newLogger.traceContext = context
	return &newLogger, nil
}

// WithCorrelationID creates a logger with correlation ID
func (l *Logger) WithCorrelationID(correlationID string) (*Logger, error) {
	newLogger := *l
	newLogger.correlationID = &correlationID
	return &newLogger, nil
}

// WithRequestID creates a logger with request ID
func (l *Logger) WithRequestID(requestID string) (*Logger, error) {
	newLogger := *l
	newLogger.requestID = &requestID
	return &newLogger, nil
}

// WithSessionID creates a logger with session ID
func (l *Logger) WithSessionID(sessionID string) (*Logger, error) {
	newLogger := *l
	newLogger.sessionID = &sessionID
	return &newLogger, nil
}
