# SpacetimeDB Telemetry Integration Guide

This document outlines the required changes to integrate SpacetimeDB with the local OpenTelemetry environment.

## Overview

The local telemetry environment is ready to receive telemetry data from SpacetimeDB. However, the SpacetimeDB server needs to be configured to send telemetry data to the local OpenTelemetry Collector.

## Required SpacetimeDB Server Changes

### 1. Add OpenTelemetry Dependencies

Add the following dependencies to the relevant `Cargo.toml` files:

```toml
[dependencies]
opentelemetry = "0.21"
opentelemetry-otlp = "0.14"
opentelemetry-semantic-conventions = "0.13"
opentelemetry_sdk = "0.21"
tracing = "0.1"
tracing-opentelemetry = "0.22"
tracing-subscriber = "0.3"

# For StatsD metrics
statsd = "0.16"
```

### 2. Core Telemetry Integration Points

#### A. Main Server Initialization (`crates/standalone/src/main.rs`)

```rust
use opentelemetry::global;
use opentelemetry_otlp::WithExportConfig;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

fn init_telemetry() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize OpenTelemetry tracer
    let tracer = opentelemetry_otlp::new_pipeline()
        .tracing()
        .with_exporter(
            opentelemetry_otlp::new_exporter()
                .http()
                .with_endpoint("http://localhost:4318/v1/traces")
        )
        .with_trace_config(
            opentelemetry_sdk::trace::config()
                .with_resource(opentelemetry_sdk::Resource::new(vec![
                    opentelemetry::KeyValue::new("service.name", "spacetimedb"),
                    opentelemetry::KeyValue::new("service.version", env!("CARGO_PKG_VERSION")),
                ]))
        )
        .install_batch(opentelemetry_sdk::runtime::Tokio)?;

    // Initialize tracing subscriber with OpenTelemetry layer
    tracing_subscriber::registry()
        .with(tracing_opentelemetry::layer().with_tracer(tracer))
        .with(tracing_subscriber::EnvFilter::from_default_env())
        .with(tracing_subscriber::fmt::layer())
        .init();

    Ok(())
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize telemetry early in main
    init_telemetry()?;
    
    // ... rest of main function
    
    Ok(())
}
```

#### B. StatsD Metrics Client (`crates/metrics/src/lib.rs`)

```rust
use statsd::Client;
use std::sync::OnceLock;

static STATSD_CLIENT: OnceLock<Client> = OnceLock::new();

pub fn init_metrics() -> Result<(), Box<dyn std::error::Error>> {
    let client = Client::new("localhost:8125", "spacetimedb")?;
    STATSD_CLIENT.set(client).map_err(|_| "Failed to set StatsD client")?;
    Ok(())
}

pub fn get_metrics_client() -> Option<&'static Client> {
    STATSD_CLIENT.get()
}

// Metric helper macros
#[macro_export]
macro_rules! counter {
    ($name:expr, $value:expr) => {
        if let Some(client) = get_metrics_client() {
            let _ = client.count($name, $value);
        }
    };
    ($name:expr, $value:expr, $tags:expr) => {
        if let Some(client) = get_metrics_client() {
            let _ = client.count_with_tags($name, $value).with_tags($tags).send();
        }
    };
}

#[macro_export]
macro_rules! gauge {
    ($name:expr, $value:expr) => {
        if let Some(client) = get_metrics_client() {
            let _ = client.gauge($name, $value);
        }
    };
}

#[macro_export]
macro_rules! timing {
    ($name:expr, $value:expr) => {
        if let Some(client) = get_metrics_client() {
            let _ = client.time($name, $value);
        }
    };
}
```

#### C. Database Operations Instrumentation (`crates/core/src/db/mod.rs`)

```rust
use tracing::{instrument, info, warn, error};

impl Database {
    #[instrument(skip(self), fields(table_name = %table_name))]
    pub fn insert(&mut self, table_name: &str, row: ProductValue) -> Result<(), DBError> {
        let start = std::time::Instant::now();
        
        // Existing insert logic...
        let result = self.do_insert(table_name, row);
        
        // Record metrics
        let duration = start.elapsed();
        timing!("spacetimedb.database.insert_duration", duration.as_millis() as i64);
        counter!("spacetimedb.database.inserts", 1, &[("table", table_name)]);
        
        if result.is_err() {
            counter!("spacetimedb.database.insert_errors", 1, &[("table", table_name)]);
        }
        
        result
    }

    #[instrument(skip(self), fields(table_name = %table_name))]
    pub fn select(&self, table_name: &str, query: &Query) -> Result<Vec<ProductValue>, DBError> {
        let start = std::time::Instant::now();
        
        // Existing select logic...
        let result = self.do_select(table_name, query);
        
        // Record metrics
        let duration = start.elapsed();
        timing!("spacetimedb.database.select_duration", duration.as_millis() as i64);
        counter!("spacetimedb.database.selects", 1, &[("table", table_name)]);
        
        if let Ok(ref rows) = result {
            gauge!("spacetimedb.database.rows_returned", rows.len() as f64);
        }
        
        result
    }
}
```

#### D. WASM Module Instrumentation (`crates/vm/src/lib.rs`)

```rust
use tracing::{instrument, span, Level};

impl WasmModule {
    #[instrument(skip(self), fields(module_id = %self.module_id, function_name = %function_name))]
    pub fn call_function(&mut self, function_name: &str, args: &[Value]) -> Result<Value, VMError> {
        let span = span!(Level::INFO, "wasm_function_call", 
            module_id = %self.module_id, 
            function_name = %function_name
        );
        let _enter = span.enter();
        
        let start = std::time::Instant::now();
        
        // Existing function call logic...
        let result = self.do_call_function(function_name, args);
        
        // Record metrics
        let duration = start.elapsed();
        timing!("spacetimedb.wasm.execution_time", duration.as_micros() as i64);
        counter!("spacetimedb.wasm.function_calls", 1, &[
            ("module_id", &self.module_id.to_string()),
            ("function", function_name)
        ]);
        
        if result.is_err() {
            counter!("spacetimedb.wasm.execution_errors", 1, &[
                ("module_id", &self.module_id.to_string()),
                ("function", function_name)
            ]);
        }
        
        result
    }
}
```

#### E. API Endpoint Instrumentation (`crates/client-api/src/lib.rs`)

```rust
use tracing::{instrument, info};

#[instrument(skip(req), fields(method = %req.method(), path = %req.uri().path()))]
pub async fn handle_request(req: Request<Body>) -> Result<Response<Body>, Error> {
    let start = std::time::Instant::now();
    let method = req.method().to_string();
    let path = req.uri().path().to_string();
    
    // Existing request handling logic...
    let result = do_handle_request(req).await;
    
    // Record metrics
    let duration = start.elapsed();
    let status_code = result.as_ref()
        .map(|r| r.status().as_u16())
        .unwrap_or(500);
    
    timing!("spacetimedb.api.request_duration", duration.as_millis() as i64);
    counter!("spacetimedb.api.requests", 1, &[
        ("method", &method),
        ("path", &path),
        ("status", &status_code.to_string())
    ]);
    
    result
}
```

### 3. Configuration Changes

#### A. Environment Variables

Add support for telemetry configuration via environment variables:

```rust
// In configuration module
pub struct TelemetryConfig {
    pub enabled: bool,
    pub otlp_endpoint: String,
    pub statsd_endpoint: String,
    pub service_name: String,
    pub service_version: String,
}

impl Default for TelemetryConfig {
    fn default() -> Self {
        Self {
            enabled: std::env::var("SPACETIMEDB_TELEMETRY_ENABLED")
                .unwrap_or_else(|_| "false".to_string())
                .parse()
                .unwrap_or(false),
            otlp_endpoint: std::env::var("OTEL_EXPORTER_OTLP_ENDPOINT")
                .unwrap_or_else(|_| "http://localhost:4318".to_string()),
            statsd_endpoint: std::env::var("STATSD_HOST")
                .map(|host| format!("{}:8125", host))
                .unwrap_or_else(|_| "localhost:8125".to_string()),
            service_name: std::env::var("OTEL_SERVICE_NAME")
                .unwrap_or_else(|_| "spacetimedb".to_string()),
            service_version: std::env::var("OTEL_SERVICE_VERSION")
                .unwrap_or_else(|_| env!("CARGO_PKG_VERSION").to_string()),
        }
    }
}
```

#### B. Configuration File Support

Add telemetry section to `config.toml`:

```toml
[telemetry]
enabled = true
otlp_endpoint = "http://localhost:4318"
statsd_endpoint = "localhost:8125"
service_name = "spacetimedb"
log_level = "info"

[telemetry.sampling]
traces_per_second = 100
```

### 4. Development Environment Setup

#### A. Environment Variables for Development

Create a `.env` file in the SpacetimeDB root:

```bash
# Telemetry Configuration
SPACETIMEDB_TELEMETRY_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
OTEL_SERVICE_NAME=spacetimedb
OTEL_SERVICE_VERSION=dev
STATSD_HOST=localhost
RUST_LOG=info,spacetimedb=debug
```

#### B. Development Scripts

Create `scripts/run-with-telemetry.sh`:

```bash
#!/bin/bash
export SPACETIMEDB_TELEMETRY_ENABLED=true
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
export STATSD_HOST=localhost
cargo run --bin spacetimedb -- start
```

### 5. Testing Integration

#### A. Test Module with Telemetry

Create test modules that generate telemetry data:

```rust
// In tests/telemetry_test.rs
#[cfg(test)]
mod tests {
    use super::*;
    
    #[tokio::test]
    async fn test_telemetry_integration() {
        // Initialize telemetry
        init_telemetry().unwrap();
        init_metrics().unwrap();
        
        // Perform operations that generate telemetry
        let mut db = Database::new();
        db.insert("test_table", test_row()).unwrap();
        
        // Give time for telemetry to be sent
        tokio::time::sleep(Duration::from_secs(2)).await;
        
        // Verify telemetry was sent (check local files)
        assert!(std::path::Path::new("../local-otel/data/traces/traces.jsonl").exists());
    }
}
```

## Implementation Priority

1. **Phase 1**: Basic OpenTelemetry tracing integration
2. **Phase 2**: StatsD metrics for database operations
3. **Phase 3**: WASM module instrumentation
4. **Phase 4**: API endpoint tracing
5. **Phase 5**: Advanced metrics and custom dashboards

## Verification Steps

After implementing the changes:

1. Start the local telemetry environment:
   ```bash
   cd local-otel
   ./scripts/setup/setup-telemetry-env.sh
   ./scripts/setup/start-telemetry-stack.sh
   ```

2. Run SpacetimeDB with telemetry enabled:
   ```bash
   cd SpacetimeDB
   SPACETIMEDB_TELEMETRY_ENABLED=true cargo run --bin spacetimedb -- start
   ```

3. Verify telemetry data:
   ```bash
   cd local-otel
   ./scripts/verification/bash/check_telemetry_health.sh
   ls -la data/traces/
   ls -la data/metrics/
   ```

4. View dashboards:
   - Grafana: http://localhost:3000
   - Jaeger: http://localhost:16686
   - Prometheus: http://localhost:9090

## Notes

- All telemetry is optional and can be disabled via configuration
- The local environment is designed for development and testing
- Production deployments will require different endpoint configurations
- Performance impact should be minimal with proper sampling configuration

## Future Enhancements

- Custom Grafana dashboards for SpacetimeDB metrics
- Alerting rules for critical errors
- Distributed tracing across multiple SpacetimeDB instances
- Integration with cloud telemetry services
