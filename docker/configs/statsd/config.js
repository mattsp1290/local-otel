module.exports = {
  // StatsD server configuration for Agent Observability Verifier
  
  // Network configuration
  port: 8125,
  mgmt_port: 8126,
  address: "0.0.0.0",
  
  // Timing configuration
  flushInterval: 10000,  // 10 seconds for development
  
  // Backends for data export
  backends: [
    "./backends/console",
    "./backends/graphite"
  ],
  
  // Console backend configuration (for debugging)
  console: {
    prettyprint: true
  },
  
  // Graphite backend configuration (for OpenTelemetry Collector)
  graphiteHost: "otel-collector",
  graphitePort: 2003,
  graphite: {
    legacyNamespace: false,
    globalPrefix: "canary",
    prefixCounter: "counters",
    prefixTimer: "timers",
    prefixGauge: "gauges",
    prefixSet: "sets"
  },
  
  // Metric processing configuration
  deleteIdleStats: true,
  deleteGauges: true,
  deleteTimers: true,
  deleteSets: true,
  deleteCounters: true,
  
  // Histogram configuration
  histogram: [
    {
      metric: "canary.api.response_time",
      bins: [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
    },
    {
      metric: "canary.api.request_size", 
      bins: [100, 500, 1000, 5000, 10000, 50000]
    },
    {
      metric: "canary.api.request_duration",
      bins: [0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
    }
  ],
  
  // Metric name mapping and validation
  keyNameSanitize: true,
  
  // Application specific metric namespaces
  prefixStats: "canary",
  
  // Logging configuration
  log: {
    backend: "stdout",
    level: "LOG_INFO"
  },
  
  // Health check configuration
  healthStatus: {
    enabled: true,
    threshold: 1000
  },
  
  // Development specific settings
  dumpMessages: false,
  debug: false,
  
  // Metric aggregation settings
  percentThreshold: [50, 75, 90, 95, 99]
};
