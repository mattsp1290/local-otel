package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log"
	"math/rand"
	"net/http"
	"time"
)

// OTLP trace data structures
type TraceData struct {
	ResourceSpans []ResourceSpan `json:"resourceSpans"`
}

type ResourceSpan struct {
	Resource   Resource    `json:"resource"`
	ScopeSpans []ScopeSpan `json:"scopeSpans"`
}

type Resource struct {
	Attributes []Attribute `json:"attributes"`
}

type ScopeSpan struct {
	Scope Scope  `json:"scope"`
	Spans []Span `json:"spans"`
}

type Scope struct {
	Name    string `json:"name"`
	Version string `json:"version"`
}

type Span struct {
	TraceID           string      `json:"traceId"`
	SpanID            string      `json:"spanId"`
	ParentSpanID      string      `json:"parentSpanId,omitempty"`
	Name              string      `json:"name"`
	Kind              int         `json:"kind"`
	StartTimeUnixNano int64       `json:"startTimeUnixNano"`
	EndTimeUnixNano   int64       `json:"endTimeUnixNano"`
	Attributes        []Attribute `json:"attributes"`
	Status            Status      `json:"status"`
}

type Attribute struct {
	Key   string      `json:"key"`
	Value interface{} `json:"value"`
}

type Status struct {
	Code int `json:"code"`
}

type StringValue struct {
	StringValue string `json:"stringValue"`
}

type IntValue struct {
	IntValue string `json:"intValue"`
}

type DoubleValue struct {
	DoubleValue float64 `json:"doubleValue"`
}

// Colors for output
const (
	ColorReset  = "\033[0m"
	ColorRed    = "\033[31m"
	ColorGreen  = "\033[32m"
	ColorYellow = "\033[33m"
	ColorBlue   = "\033[34m"
)

func printStatus(message string) {
	fmt.Printf("%s✓%s %s\n", ColorGreen, ColorReset, message)
}

func printError(message string) {
	fmt.Printf("%s✗%s %s\n", ColorRed, ColorReset, message)
}

func printInfo(message string) {
	fmt.Printf("%sℹ%s %s\n", ColorBlue, ColorReset, message)
}

// Generate a random hex string of specified length
func randomHex(length int) string {
	const hexChars = "0123456789abcdef"
	result := make([]byte, length)
	for i := range result {
		result[i] = hexChars[rand.Intn(len(hexChars))]
	}
	return string(result)
}

// Generate SpacetimeDB-like trace data
func generateSpacetimeDBTrace() TraceData {
	now := time.Now()
	traceID := randomHex(32)
	
	// Database operation span
	dbSpanID := randomHex(16)
	dbStartTime := now.UnixNano()
	dbEndTime := now.Add(time.Duration(rand.Intn(50)+10) * time.Millisecond).UnixNano()
	
	// WASM execution span (child of database operation)
	wasmSpanID := randomHex(16)
	wasmStartTime := now.Add(5 * time.Millisecond).UnixNano()
	wasmEndTime := now.Add(time.Duration(rand.Intn(30)+15) * time.Millisecond).UnixNano()
	
	// API request span (parent of database operation)
	apiSpanID := randomHex(16)
	apiStartTime := now.Add(-5 * time.Millisecond).UnixNano()
	apiEndTime := now.Add(time.Duration(rand.Intn(100)+50) * time.Millisecond).UnixNano()
	
	tables := []string{"users", "messages", "channels", "sessions"}
	operations := []string{"insert", "select", "update", "delete"}
	modules := []string{"chat", "auth", "game", "analytics"}
	functions := []string{"send_message", "authenticate", "update_score", "log_event"}
	
	selectedTable := tables[rand.Intn(len(tables))]
	selectedOperation := operations[rand.Intn(len(operations))]
	selectedModule := modules[rand.Intn(len(modules))]
	selectedFunction := functions[rand.Intn(len(functions))]
	
	return TraceData{
		ResourceSpans: []ResourceSpan{
			{
				Resource: Resource{
					Attributes: []Attribute{
						{Key: "service.name", Value: StringValue{StringValue: "spacetimedb"}},
						{Key: "service.version", Value: StringValue{StringValue: "dev"}},
						{Key: "deployment.environment", Value: StringValue{StringValue: "local-development"}},
						{Key: "host.name", Value: StringValue{StringValue: "localhost"}},
					},
				},
				ScopeSpans: []ScopeSpan{
					{
						Scope: Scope{
							Name:    "spacetimedb-tracer",
							Version: "1.0.0",
						},
						Spans: []Span{
							{
								TraceID:           traceID,
								SpanID:            apiSpanID,
								Name:              "api.request",
								Kind:              2, // SPAN_KIND_SERVER
								StartTimeUnixNano: apiStartTime,
								EndTimeUnixNano:   apiEndTime,
								Attributes: []Attribute{
									{Key: "http.method", Value: StringValue{StringValue: "POST"}},
									{Key: "http.url", Value: StringValue{StringValue: "/database/call"}},
									{Key: "http.status_code", Value: IntValue{IntValue: "200"}},
									{Key: "user.id", Value: StringValue{StringValue: fmt.Sprintf("user_%d", rand.Intn(1000))}},
								},
								Status: Status{Code: 1}, // STATUS_CODE_OK
							},
							{
								TraceID:           traceID,
								SpanID:            dbSpanID,
								ParentSpanID:      apiSpanID,
								Name:              fmt.Sprintf("database.%s", selectedOperation),
								Kind:              3, // SPAN_KIND_CLIENT
								StartTimeUnixNano: dbStartTime,
								EndTimeUnixNano:   dbEndTime,
								Attributes: []Attribute{
									{Key: "db.system", Value: StringValue{StringValue: "spacetimedb"}},
									{Key: "db.table", Value: StringValue{StringValue: selectedTable}},
									{Key: "db.operation", Value: StringValue{StringValue: selectedOperation}},
									{Key: "db.rows_affected", Value: IntValue{IntValue: fmt.Sprintf("%d", rand.Intn(10)+1)}},
								},
								Status: Status{Code: 1},
							},
							{
								TraceID:           traceID,
								SpanID:            wasmSpanID,
								ParentSpanID:      dbSpanID,
								Name:              "wasm.function_call",
								Kind:              2, // SPAN_KIND_SERVER
								StartTimeUnixNano: wasmStartTime,
								EndTimeUnixNano:   wasmEndTime,
								Attributes: []Attribute{
									{Key: "wasm.module_id", Value: StringValue{StringValue: selectedModule}},
									{Key: "wasm.function", Value: StringValue{StringValue: selectedFunction}},
									{Key: "wasm.execution_time_ms", Value: DoubleValue{DoubleValue: float64(wasmEndTime-wasmStartTime) / 1e6}},
									{Key: "wasm.memory_usage_bytes", Value: IntValue{IntValue: fmt.Sprintf("%d", rand.Intn(1024*1024)+512*1024)}},
								},
								Status: Status{Code: 1},
							},
						},
					},
				},
			},
		},
	}
}

// Send trace data to OpenTelemetry Collector
func sendTrace(traceData TraceData) error {
	jsonData, err := json.Marshal(traceData)
	if err != nil {
		return fmt.Errorf("failed to marshal trace data: %v", err)
	}
	
	req, err := http.NewRequest("POST", "http://localhost:4318/v1/traces", bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Errorf("failed to create request: %v", err)
	}
	
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("User-Agent", "spacetimedb-trace-generator/1.0")
	
	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to send request: %v", err)
	}
	defer resp.Body.Close()
	
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("received non-200 status code: %d", resp.StatusCode)
	}
	
	return nil
}

func main() {
	fmt.Printf("%s🚀 SpacetimeDB Trace Generator%s\n", ColorBlue, ColorReset)
	fmt.Println()
	
	// Check if OpenTelemetry Collector is available
	printInfo("Checking OpenTelemetry Collector availability...")
	resp, err := http.Get("http://localhost:13133/")
	if err != nil {
		printError("OpenTelemetry Collector is not available")
		printError("Please start the telemetry stack first: ./scripts/setup/start-telemetry-stack.sh")
		log.Fatal(err)
	}
	resp.Body.Close()
	printStatus("OpenTelemetry Collector is available")
	
	// Generate and send traces
	numTraces := 10
	printInfo(fmt.Sprintf("Generating %d SpacetimeDB traces...", numTraces))
	
	successCount := 0
	for i := 0; i < numTraces; i++ {
		traceData := generateSpacetimeDBTrace()
		
		if err := sendTrace(traceData); err != nil {
			printError(fmt.Sprintf("Failed to send trace %d: %v", i+1, err))
		} else {
			successCount++
			fmt.Printf("%s✓%s Sent trace %d/%d\n", ColorGreen, ColorReset, i+1, numTraces)
		}
		
		// Small delay between traces
		time.Sleep(100 * time.Millisecond)
	}
	
	fmt.Println()
	if successCount == numTraces {
		printStatus(fmt.Sprintf("Successfully sent all %d traces!", numTraces))
	} else {
		printError(fmt.Sprintf("Sent %d/%d traces", successCount, numTraces))
	}
	
	fmt.Println()
	printInfo("View traces in Jaeger: http://localhost:16686")
	printInfo("Check trace files: ls -la ../../../data/traces/")
}
