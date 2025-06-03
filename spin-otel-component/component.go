package main

import (
	"fmt"

	"github.com/local-otel/spin-otel-component/bindings/local/otel/telemetry"
	"github.com/local-otel/spin-otel-component/internal/logger"
	"github.com/local-otel/spin-otel-component/internal/provider"
	"github.com/local-otel/spin-otel-component/internal/types"
	"go.bytecodealliance.org/cm"
)

// Resource tracking - using simple counters for MVP
var (
	providerCounter uint32
	loggerCounter   uint32
	providers       = make(map[uint32]*provider.Provider)
	loggers         = make(map[uint32]*logger.Logger)
)

func init() {
	// Wire up the TelemetryProvider exports
	telemetry.Exports.TelemetryProvider.Constructor = telemetryProviderConstructor
	telemetry.Exports.TelemetryProvider.Destructor = telemetryProviderDestructor
	telemetry.Exports.TelemetryProvider.CreateLogger = telemetryProviderCreateLogger

	// Wire up the Logger exports
	telemetry.Exports.Logger.Destructor = loggerDestructor
	telemetry.Exports.Logger.Emit = loggerEmit
}

// telemetryProviderConstructor creates a new telemetry provider
func telemetryProviderConstructor(config telemetry.ProviderConfig) telemetry.TelemetryProvider {
	// Create internal provider
	p := provider.NewProvider()

	// Convert WIT config to internal config
	internalConfig := &types.ProviderConfig{
		Endpoint:     config.Endpoint,
		ServiceName:  config.ServiceName,
		DevMode:      config.DevMode,
		Protocol:     types.ExportProtocolDebugStdout, // Default to debug for MVP
		BatchSize:    10,
		TimeoutMs:    1000,
		MaxQueueSize: 100,
		Sampling:     types.SamplingStrategyAlwaysOn,
	}

	// Initialize the provider
	if err := p.Initialize(internalConfig); err != nil {
		// In real implementation, we'd handle this error better
		fmt.Printf("Failed to initialize provider: %v\n", err)
	}

	// Create resource handle and store provider
	providerCounter++
	rep := cm.Rep(providerCounter)
	providers[providerCounter] = p

	return telemetry.TelemetryProviderResourceNew(rep)
}

// telemetryProviderDestructor cleans up a telemetry provider
func telemetryProviderDestructor(self cm.Rep) {
	id := uint32(self)
	if p, ok := providers[id]; ok {
		_ = p.Shutdown()
		delete(providers, id)
	}
}

// telemetryProviderCreateLogger creates a new logger
func telemetryProviderCreateLogger(self cm.Rep, name string) cm.Result[string, telemetry.Logger, string] {
	id := uint32(self)
	p, ok := providers[id]
	if !ok {
		return cm.Err[cm.Result[string, telemetry.Logger, string]]("provider not found")
	}

	l, err := p.CreateLogger(name, nil)
	if err != nil {
		return cm.Err[cm.Result[string, telemetry.Logger, string]](err.Error())
	}

	// Create resource handle and store logger
	loggerCounter++
	rep := cm.Rep(loggerCounter)
	loggers[loggerCounter] = l

	return cm.OK[cm.Result[string, telemetry.Logger, string]](telemetry.LoggerResourceNew(rep))
}

// loggerDestructor cleans up a logger
func loggerDestructor(self cm.Rep) {
	id := uint32(self)
	delete(loggers, id)
}

// loggerEmit emits a log record
func loggerEmit(self cm.Rep, log telemetry.LogRecord) cm.Result[string, struct{}, string] {
	id := uint32(self)
	l, ok := loggers[id]
	if !ok {
		return cm.Err[cm.Result[string, struct{}, string]]("logger not found")
	}

	// Convert WIT log record to internal log record
	internalRecord := types.LogRecord{
		Body:     log.Body,
		Severity: convertSeverityLevel(log.Severity),
	}

	if err := l.Emit(internalRecord); err != nil {
		return cm.Err[cm.Result[string, struct{}, string]](err.Error())
	}

	return cm.OK[cm.Result[string, struct{}, string]](struct{}{})
}

// convertSeverityLevel converts WIT severity level to internal severity level
func convertSeverityLevel(witLevel telemetry.SeverityLevel) types.SeverityLevel {
	switch witLevel {
	case telemetry.SeverityLevelInfo:
		return types.SeverityLevelInfo
	case telemetry.SeverityLevelWarn:
		return types.SeverityLevelWarn
	case telemetry.SeverityLevelError:
		return types.SeverityLevelError
	case telemetry.SeverityLevelDebug:
		return types.SeverityLevelDebug
	default:
		return types.SeverityLevelInfo
	}
}

// main is required for WASM but does nothing
func main() {}
