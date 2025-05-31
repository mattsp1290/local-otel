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

// Generate Canary API trace data
func generateCanaryAPITrace() TraceData {
	now := time.Now()
	traceID := randomHex(32)

	// API endpoints and operations
	endpoints := []string{"/chirp", "/nest", "/flock"}
	methods := []string{"GET", "POST", "PUT", "DELETE"}
	statusCodes := []int{200, 201, 400, 404, 500}

	// Select random endpoint and method
	selectedEndpoint := endpoints[rand.Intn(len(endpoints))]
	selectedMethod := methods[rand.Intn(len(methods))]
	selectedStatus := statusCodes[rand.Intn(len(statusCodes))]

	// For successful requests, use 200/201
	if selectedStatus < 400 {
		if selectedMethod == "POST" {
			selectedStatus = 201
		} else {
			selectedStatus = 200
		}
	}

	// Main API request span
	apiSpanID := randomHex(16)
	apiStartTime := now.UnixNano()
	apiEndTime := now.Add(time.Duration(rand.Intn(100)+20) * time.Millisecond).UnixNano()

	// Cache lookup span (child of API request)
	cacheSpanID := randomHex(16)
	cacheStartTime := now.Add(2 * time.Millisecond).UnixNano()
	cacheEndTime := now.Add(time.Duration(rand.Intn(5)+2) * time.Millisecond).UnixNano()
	cacheHit := rand.Float32() > 0.3 // 70% cache hit rate

	// Backend service span (if cache miss)
	backendSpanID := randomHex(16)
	backendStartTime := now.Add(8 * time.Millisecond).UnixNano()
	backendEndTime := now.Add(time.Duration(rand.Intn(50)+10) * time.Millisecond).UnixNano()

	spans := []Span{
		{
			TraceID:           traceID,
			SpanID:            apiSpanID,
			Name:              fmt.Sprintf("%s %s", selectedMethod, selectedEndpoint),
			Kind:              2, // SPAN_KIND_SERVER
			StartTimeUnixNano: apiStartTime,
			EndTimeUnixNano:   apiEndTime,
			Attributes: []Attribute{
				{Key: "http.method", Value: StringValue{StringValue: selectedMethod}},
				{Key: "http.path", Value: StringValue{StringValue: selectedEndpoint}},
				{Key: "http.status_code", Value: IntValue{IntValue: fmt.Sprintf("%d", selectedStatus)}},
				{Key: "http.user_agent", Value: StringValue{StringValue: "canary-api-client/1.0"}},
				{Key: "user.id", Value: StringValue{StringValue: fmt.Sprintf("user_%d", rand.Intn(1000))}},
			},
			Status: Status{Code: 1}, // STATUS_CODE_OK
		},
		{
			TraceID:           traceID,
			SpanID:            cacheSpanID,
			ParentSpanID:      apiSpanID,
			Name:              "cache_lookup",
			Kind:              3, // SPAN_KIND_CLIENT
			StartTimeUnixNano: cacheStartTime,
			EndTimeUnixNano:   cacheEndTime,
			Attributes: []Attribute{
				{Key: "cache.key", Value: StringValue{StringValue: fmt.Sprintf("%s_data", selectedEndpoint)}},
				{Key: "cache.hit", Value: StringValue{StringValue: fmt.Sprintf("%t", cacheHit)}},
				{Key: "cache.backend", Value: StringValue{StringValue: "redis"}},
			},
			Status: Status{Code: 1},
		},
	}

	// Add backend service span if cache miss
	if !cacheHit {
		spans = append(spans, Span{
			TraceID:           traceID,
			SpanID:            backendSpanID,
			ParentSpanID:      apiSpanID,
			Name:              "backend_service_call",
			Kind:              3, // SPAN_KIND_CLIENT
			StartTimeUnixNano: backendStartTime,
			EndTimeUnixNano:   backendEndTime,
			Attributes: []Attribute{
				{Key: "service.name", Value: StringValue{StringValue: "canary-backend"}},
				{Key: "rpc.method", Value: StringValue{StringValue: "GetData"}},
				{Key: "response.size", Value: IntValue{IntValue: fmt.Sprintf("%d", rand.Intn(10000)+1000)}},
			},
			Status: Status{Code: 1},
		})
	}

	return TraceData{
		ResourceSpans: []ResourceSpan{
			{
				Resource: Resource{
					Attributes: []Attribute{
						{Key: "service.name", Value: StringValue{StringValue: "canary-api"}},
						{Key: "service.version", Value: StringValue{StringValue: "1.0.0"}},
						{Key: "deployment.environment", Value: StringValue{StringValue: "local-development"}},
						{Key: "host.name", Value: StringValue{StringValue: "localhost"}},
					},
				},
				ScopeSpans: []ScopeSpan{
					{
						Scope: Scope{
							Name:    "canary-api-tracer",
							Version: "1.0.0",
						},
						Spans: spans,
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
	req.Header.Set("User-Agent", "canary-api-trace-generator/1.0")

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
	fmt.Printf("%s🦅 Canary API Trace Generator%s\n", ColorBlue, ColorReset)
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
	printInfo(fmt.Sprintf("Generating %d Canary API traces...", numTraces))

	successCount := 0
	for i := 0; i < numTraces; i++ {
		traceData := generateCanaryAPITrace()

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
