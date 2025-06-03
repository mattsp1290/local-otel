.PHONY: generate build test clean install-tools build-example test-integration

WIT_BINDGEN = wit-bindgen-go
WASM_TOOLS = wasm-tools
COMPONENT_NAME = otel-component.wasm

# Default target
all: build

# Install required tools
install-tools:
	@echo "Installing required tools..."
	@which $(WIT_BINDGEN) > /dev/null || go install go.bytecodealliance.org/cmd/wit-bindgen-go@latest
	@which $(WASM_TOOLS) > /dev/null || (echo "Please install wasm-tools: https://github.com/bytecodealliance/wasm-tools" && exit 1)
	@which spin > /dev/null || echo "WARNING: Spin CLI not installed. You'll need it to run the example app."

# Install tools for generation only
install-generate-tools:
	@echo "Installing tools for WIT generation..."
	@which $(WIT_BINDGEN) > /dev/null || go install go.bytecodealliance.org/cmd/wit-bindgen-go@latest

# Generate Go bindings from WIT
generate: install-generate-tools
	@echo "Generating Go bindings from WIT..."
	$(WIT_BINDGEN) generate ./wit/telemetry.wit --out ./bindings --world otel-component

# Build the WASM component
build: generate
	@echo "Building WASM component..."
	GOOS=wasip1 GOARCH=wasm go build -o $(COMPONENT_NAME) .
	$(WASM_TOOLS) component new $(COMPONENT_NAME) -o $(COMPONENT_NAME) --adapt wasi_snapshot_preview1.reactor.wasm

# Build the example Spin application
build-example: build
	@echo "Building example Spin application..."
	cd spin-example && $(MAKE) build

# Run integration tests
test-integration:
	@echo "Running integration tests..."
	cd integration-tests && go test -v ./...

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -rf bindings/
	rm -f *.wasm
	rm -f spin-example/*.wasm

# Development workflow
dev: build build-example
	@echo "Starting Spin application..."
	cd spin-example && spin up --listen localhost:3000

# Check local-otel logs
check-logs:
	@echo "Recent logs from spin-example:"
	@cat data/logs/logs.jsonl | tail -20 | jq 'select(.serviceName=="spin-example")' || echo "No logs found yet"
