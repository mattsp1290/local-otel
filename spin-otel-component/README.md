# Spin OpenTelemetry Component

This is a WebAssembly Component Model implementation of the OpenTelemetry WIT interface for Fermyon Spin applications.

## Project Status

🚧 **Work in Progress** - This component is under active development.

### What's Done
- ✅ Basic project structure
- ✅ Go module setup
- ✅ Internal telemetry types (LogRecord, SpanData, MetricPoint)
- ✅ Provider, Logger, Tracer, and Meter stubs
- ✅ Batching implementation for efficient exports
- ✅ Debug exporter (stdout)
- ✅ Example Spin application structure

### What's Next
- 🔲 Generate Go bindings from WIT files using wit-bindgen-go
- 🔲 Wire up the component exports to the internal implementation
- 🔲 Implement OTLP HTTP exporter for real telemetry export
- 🔲 Complete the Spin example application
- 🔲 Add integration tests with local-otel stack

## Project Structure

```
spin-otel-component/
├── Makefile                    # Build automation
├── go.mod                      # Go module
├── component.go                # Main component entry point
├── wit/
│   ├── world.wit              # Component world definition
│   └── deps/opentelemetry/
│       └── opentelemetry.wit  # OpenTelemetry WIT interface
├── internal/                   # Internal implementation
│   ├── provider.go            # TelemetryProvider implementation
│   ├── logger.go              # Logger implementation
│   ├── tracer.go              # Tracer stub
│   ├── meter.go               # Meter stub
│   ├── types.go               # Common types
│   ├── batching.go            # Batching logic
│   └── exporter_debug.go      # Debug exporter
├── bindings/                   # Generated bindings (not yet created)
└── spin-example/              # Example Spin application
    ├── spin.toml
    ├── go.mod
    ├── main.go
    └── Makefile
```

## Building

### Prerequisites

1. Go 1.21+ with WASI support
2. Fermyon Spin CLI
3. wasm-tools
4. wit-bindgen-go

### Install Tools

```bash
# Install Spin
curl -fsSL https://developer.fermyon.com/downloads/install.sh | bash
sudo mv ./spin /usr/local/bin/spin

# Install wasm-tools
brew install wasm-tools  # macOS
# Or download from https://github.com/bytecodealliance/wasm-tools

# Install wit-bindgen-go
go install github.com/bytecodealliance/wit-bindgen-go/cmd/wit-bindgen-go@latest
```

### Build Component

```bash
# Generate bindings (first time)
make generate

# Build the component
make build

# Build and run the example
make dev
```

## Usage Example

Once the bindings are generated, the Spin application will use the component like this:

```go
// Initialize telemetry provider
config := otel.ProviderConfig{
    Endpoint:     "http://localhost:4318",
    Protocol:     otel.ExportProtocolOTLPHTTP,
    ServiceName:  "my-spin-app",
    Environment:  otel.String("development"),
    DevMode:      true,
}

provider, err := otel.NewTelemetryProvider(config)
if err != nil {
    return err
}
defer provider.Shutdown()

// Create logger
logger, _ := provider.CreateLogger("my-component", otel.String("1.0.0"))

// Log with automatic trace correlation
logger.Emit(otel.LogRecord{
    Body:     "Processing request",
    Severity: otel.SeverityLevelInfo,
    Attributes: []otel.Attribute{
        {Key: "user.id", Value: otel.StringValue("123")},
    },
})
```

## Testing

### Integration Tests

The integration tests verify that telemetry is correctly exported to the local-otel stack:

```bash
# Start local-otel stack (from parent directory)
cd ..
docker compose up -d

# Run integration tests
cd spin-otel-component
make test-integration
```

### Manual Testing

```bash
# Build and run the example
cd spin-example
make run

# In another terminal, make requests
curl http://localhost:3000/test
curl http://localhost:3000/health

# Check logs in local-otel
cat ../data/logs/logs.jsonl | jq 'select(.serviceName=="spin-example")'
```

## Implementation Notes

### Batching
The component implements batching to efficiently export telemetry:
- Configurable batch size (default: 512)
- Time-based flushing (default: 1 second)
- Automatic export when batch is full

### Export Protocols
Starting with:
1. Debug (stdout) - for development
2. OTLP HTTP - for production use with OpenTelemetry Collector

Future protocols:
- StatsD (for metrics)
- Prometheus (pull-based metrics)
- Jaeger (trace visualization)

### Memory Management
The component is designed for WebAssembly constraints:
- Bounded queues to prevent memory exhaustion
- Efficient batching to minimize allocations
- No goroutines (synchronous operation)

## Known Issues

1. **Import Cycles**: Currently working through Go import cycle issues between internal packages
2. **Binding Generation**: Need to run wit-bindgen-go to generate the component bindings
3. **WASM Adapter**: Need to ensure we have the correct WASI adapter for the component model

## Contributing

This is part of the local-otel project. The main goal is to provide observability for WebAssembly applications running in Spin.

## License

See the parent project's LICENSE file.
