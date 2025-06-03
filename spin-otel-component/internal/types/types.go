package types

import (
	"time"
)

// Attribute represents a key-value attribute
type Attribute struct {
	Key   string
	Value AttributeValue
}

// AttributeValue represents the value of an attribute
type AttributeValue interface {
	String() string
}

// StringValue implements AttributeValue for string values
type StringValue string

func (s StringValue) String() string {
	return string(s)
}

// Header represents an HTTP header
type Header struct {
	Key   string
	Value string
}

// ExportProtocol represents the export protocol to use
type ExportProtocol int

const (
	ExportProtocolOTLPHTTP ExportProtocol = iota
	ExportProtocolOTLPGRPC
	ExportProtocolStatsD
	ExportProtocolPrometheus
	ExportProtocolZipkin
	ExportProtocolJaeger
	ExportProtocolDebugStdout
)

// SamplingStrategy represents the sampling strategy
type SamplingStrategy int

const (
	SamplingStrategyAlwaysOn SamplingStrategy = iota
	SamplingStrategyAlwaysOff
	SamplingStrategyProbability
	SamplingStrategyParentBased
)

// LogRecord represents a log entry
type LogRecord struct {
	Body           string
	Severity       SeverityLevel
	SeverityText   *string
	Attributes     []Attribute
	TraceContext   *TraceContext
	CorrelationID  *string
	RequestID      *string
	SessionID      *string
	TimestampNanos *uint64
	Resource       *Resource
}

// SeverityLevel represents log severity levels
type SeverityLevel int

const (
	SeverityLevelTrace SeverityLevel = iota
	SeverityLevelDebug
	SeverityLevelInfo
	SeverityLevelWarn
	SeverityLevelError
	SeverityLevelFatal
)

// TraceContext represents W3C trace context
type TraceContext struct {
	TraceID    string
	SpanID     string
	TraceFlags uint8
	TraceState *string
}

// Resource represents the entity producing telemetry
type Resource struct {
	Attributes []Attribute
	SchemaURL  *string
}

// SpanData represents trace span data
type SpanData struct {
	Name         string
	Kind         SpanKind
	TraceID      string
	SpanID       string
	ParentSpanID *string
	StartTime    time.Time
	EndTime      time.Time
	Attributes   []Attribute
	Events       []SpanEvent
	Links        []SpanLink
	Status       SpanStatus
	Resource     *Resource
}

// SpanKind represents the type of span
type SpanKind int

const (
	SpanKindInternal SpanKind = iota
	SpanKindServer
	SpanKindClient
	SpanKindProducer
	SpanKindConsumer
)

// SpanEvent represents an event within a span
type SpanEvent struct {
	Name           string
	Attributes     []Attribute
	TimestampNanos uint64
}

// SpanLink represents a link to another span
type SpanLink struct {
	TraceID    string
	SpanID     string
	Attributes []Attribute
}

// SpanStatus represents the status of a span
type SpanStatus struct {
	Code        StatusCode
	Description *string
}

// StatusCode represents span status codes
type StatusCode int

const (
	StatusCodeUnset StatusCode = iota
	StatusCodeOK
	StatusCodeError
)

// MetricPoint represents a metric data point
type MetricPoint struct {
	Name           string
	Description    *string
	Unit           *string
	Kind           MetricKind
	Value          MetricValue
	Attributes     []Attribute
	TimestampNanos *uint64
	Temporality    MetricTemporality
	Resource       *Resource
}

// MetricKind represents the type of metric instrument
type MetricKind int

const (
	MetricKindCounter MetricKind = iota
	MetricKindUpDownCounter
	MetricKindHistogram
	MetricKindGauge
	MetricKindObservableCounter
	MetricKindObservableUpDownCounter
	MetricKindObservableGauge
)

// MetricValue represents the value of a metric
type MetricValue interface {
	isMetricValue()
}

// Float64Value represents a float64 metric value
type Float64Value float64

func (Float64Value) isMetricValue() {}

// Int64Value represents an int64 metric value
type Int64Value int64

func (Int64Value) isMetricValue() {}

// HistogramValue represents histogram data
type HistogramValue struct {
	Count          uint64
	Sum            float64
	Min            *float64
	Max            *float64
	BucketCounts   []uint64
	ExplicitBounds []float64
}

func (HistogramValue) isMetricValue() {}

// MetricTemporality represents metric temporality
type MetricTemporality int

const (
	MetricTemporalityDelta MetricTemporality = iota
	MetricTemporalityCumulative
)

// Convert severity level to string
func (s SeverityLevel) String() string {
	switch s {
	case SeverityLevelTrace:
		return "TRACE"
	case SeverityLevelDebug:
		return "DEBUG"
	case SeverityLevelInfo:
		return "INFO"
	case SeverityLevelWarn:
		return "WARN"
	case SeverityLevelError:
		return "ERROR"
	case SeverityLevelFatal:
		return "FATAL"
	default:
		return "UNKNOWN"
	}
}

// Convert metric kind to string
func (m MetricKind) String() string {
	switch m {
	case MetricKindCounter:
		return "Counter"
	case MetricKindUpDownCounter:
		return "UpDownCounter"
	case MetricKindHistogram:
		return "Histogram"
	case MetricKindGauge:
		return "Gauge"
	case MetricKindObservableCounter:
		return "ObservableCounter"
	case MetricKindObservableUpDownCounter:
		return "ObservableUpDownCounter"
	case MetricKindObservableGauge:
		return "ObservableGauge"
	default:
		return "Unknown"
	}
}

// GetNanoseconds returns current time in nanoseconds since Unix epoch
func GetNanoseconds() uint64 {
	return uint64(time.Now().UnixNano())
}

// AggregatedMetric represents pre-aggregated metric data
type AggregatedMetric struct {
	Metric   MetricPoint
	Count    uint64
	WindowMs uint64
}

// SpanSpec represents specification for creating a new span
type SpanSpec struct {
	Name       string
	Kind       SpanKind
	Parent     *TraceContext
	Attributes []Attribute
	Links      []SpanLink
	StartTime  *time.Time
}

// ErrorInfo represents detailed error information
type ErrorInfo struct {
	Message                 string
	ErrorType               *string
	StackTrace              *string
	Fingerprint             *string
	CircuitBreakerTriggered bool
}

// ProviderConfig represents the configuration for the telemetry provider
type ProviderConfig struct {
	Endpoint           string
	Protocol           ExportProtocol
	ServiceName        string
	ServiceVersion     *string
	Environment        *string
	ResourceAttributes []Attribute
	DefaultTags        []Attribute
	Headers            []Header
	Compression        bool
	TimeoutMs          uint32
	BatchSize          uint32
	MaxQueueSize       uint32
	Sampling           SamplingStrategy
	DevMode            bool
}
