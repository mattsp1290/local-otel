# 🚀 WASM Quick Start for Go Developers

**Time to first WASM component: 5 minutes** ⏱️

If you're a Go developer who's heard about WebAssembly (WASM) but never built anything with it, this guide is for you. We'll get you from zero to a working OpenTelemetry WASM component without the theory overload.

## 🎯 What Are We Building?

A Go-based OpenTelemetry component that compiles to WASM and can be used by any application that supports the WebAssembly Component Model. Think of it as a Go package, but instead of importing it in Go code, any language can use it.

**Current Status**: MVP with logging functionality (traces and metrics coming soon!)

## 📋 Prerequisites (2 minutes)

```bash
# You need Go 1.21+ (you probably have this)
go version

# Install the WASM interface type generator
go install go.bytecodealliance.org/cmd/wit-bindgen-go@latest

# That's it! No complex toolchain needed.
```

## 🏃 5-Minute Quick Start

### Step 1: Clone and Navigate
```bash
git clone <this-repo>
cd local-otel/spin-otel-component
```

### Step 2: Build Your First WASM Component
```bash
# This creates a 3MB wasm file
GOOS=wasip1 GOARCH=wasm go build -o otel-component.wasm .

# Verify it worked
ls -lh otel-component.wasm
```

### Step 3: See What You Built
```bash
# Check the component interface (optional, requires wasm-tools)
# brew install wasm-tools  # on macOS
# wasm-tools component wit otel-component.wasm
```

🎉 **Congrats! You just built a WASM component!** The file `otel-component.wasm` is a self-contained OpenTelemetry implementation that any WASM-compatible runtime can use.

## 🤔 Wait, What Just Happened?

Let's break down what's different from regular Go development:

### GOOS=wasip1 GOARCH=wasm
- **Regular Go**: Compiles to machine code for your OS/architecture
- **WASM Go**: Compiles to WebAssembly bytecode that runs in a sandbox
- **wasip1**: WASI Preview 1 - think of it as "POSIX for WASM"

### The WIT File (WebAssembly Interface Types)
Look at `wit/telemetry.wit`:
```wit
interface logger {
  new: func(provider: provider-resource, config: logger-config) -> result<logger-resource, string>
  emit: func(logger: logger-resource, record: log-record) -> result<_, string>
}
```

**Go Developer Translation**: 
- WIT interfaces are like Go interfaces but for WASM components
- They define the contract between your WASM code and the outside world
- `wit-bindgen-go` generates Go code from these definitions (like protobuf/gRPC)

## 🔍 Understanding the Code Structure

```
spin-otel-component/
├── component.go          # 🎯 Main entry point - adapts WIT to Go
├── wit/                  # 📄 Interface definitions
│   └── telemetry.wit    
├── internal/            # 📦 Regular Go packages
│   ├── logger/          # Logging implementation
│   ├── tracer/          # Tracing (stub for now)
│   └── meter/           # Metrics (stub for now)
└── bindings/            # 🤖 Generated from WIT files
```

### Key Differences from Regular Go

1. **No `main()` function** - WASM components export functions instead
2. **Resource management** - Components can't use goroutines that outlive function calls
3. **No direct I/O** - Everything goes through the WIT interface

### The Adapter Pattern (component.go)

```go
// This is how WIT types map to your Go implementation
func (e exportsImpl) ProviderNew(config telemetry.ProviderConfig) (provider.Exports, error) {
    // Convert WIT types to internal Go types
    cfg := &types.ProviderConfig{
        ServiceName: config.ServiceName,
        // ... more field mapping
    }
    
    // Use regular Go code internally
    return providerImpl{provider: prov}, nil
}
```

## 🧪 Testing Your Component

Currently, testing requires a WASM runtime. We're building a test harness, but for now:

```bash
# See current test status
cat spin-example/INTEGRATION_TEST_STATUS.md

# The component outputs logs to stdout (debug exporter)
# Real exporters (OTLP HTTP) are coming soon!
```

## 🚧 Common Gotchas for Go Developers

### 1. **"undefined: syscall"**
WASM doesn't have access to many system calls. Use the WASI APIs instead.

### 2. **Binary Size**
WASM binaries are larger than native Go binaries. Our 3MB is normal for a Go WASM component.

### 3. **No Goroutine Persistence**
Goroutines can't outlive the function call that created them in WASM components.

### 4. **Import Restrictions**
Not all Go packages work in WASM. Stick to pure Go packages when possible.

## 📚 Next Steps

### Want to Use the Component?
- Check out `proompts/spin/tasks/create-rust-test-app.md` for integration examples
- The component will eventually support OTLP export to any OpenTelemetry collector

### Want to Contribute?
1. **Implement Tracing**: Check `internal/tracer/tracer.go`
2. **Implement Metrics**: Check `internal/meter/meter.go`
3. **Add OTLP Exporter**: See the tasks in `proompts/spin/tasks.yaml`

### Want to Learn More?
- [WebAssembly Component Model](https://component-model.bytecodealliance.org/)
- [WASI Preview 1](https://github.com/WebAssembly/WASI)
- [WIT Format](https://component-model.bytecodealliance.org/design/wit.html)

## 💡 Quick Tips

1. **Development Workflow**:
   ```bash
   # Make changes
   GOOS=wasip1 GOARCH=wasm go build -o otel-component.wasm .
   # Test (when test harness is ready)
   ```

2. **Debugging**:
   - Use the debug exporter (currently implemented)
   - Add fmt.Println during development (outputs to stderr)
   - Check DEVELOPMENT_STATUS.md for current state

3. **Performance**:
   - WASM is slower than native Go (but still pretty fast!)
   - Our target: <5μs per log operation

## 🤝 Getting Help

- **Issues with WASM build?** Check you're using Go 1.21+
- **WIT questions?** The .wit files have comments explaining the interfaces
- **Architecture questions?** See spin-otel-wit/IMPLEMENTATION_GUIDE.md

---

**Remember**: WASM components are just Go programs with different compilation targets and some restrictions. If you can write Go, you can write WASM components! 🎉

**Total time invested**: 5 minutes to build, lifetime to master 😄
