package telemetry

import (
	"log"
	"os"
	"time"

	"github.com/DataDog/datadog-go/v5/statsd"
)

var statsdClient *statsd.Client

// InitMetrics initializes the StatsD client
func InitMetrics() {
	host := os.Getenv("STATSD_HOST")
	if host == "" {
		host = "localhost"
	}

	port := os.Getenv("STATSD_PORT")
	if port == "" {
		port = "8125"
	}

	client, err := statsd.New(host + ":" + port)
	if err != nil {
		log.Printf("Failed to create StatsD client: %v", err)
		return
	}

	client.Namespace = "feed_service."
	client.Tags = []string{"env:" + os.Getenv("ENVIRONMENT")}

	statsdClient = client
}

// RecordServiceStart records service startup
func RecordServiceStart() {
	if statsdClient != nil {
		statsdClient.Incr("service.started", nil, 1)
	}
}

// RecordRequest records request metrics
func RecordRequest(endpoint string, method string, status int, duration time.Duration) {
	if statsdClient == nil {
		return
	}

	tags := []string{
		"endpoint:" + endpoint,
		"method:" + method,
		"status:" + string(status),
	}

	// Count requests
	statsdClient.Incr("requests", tags, 1)

	// Record duration
	statsdClient.Timing("request.duration", duration, tags, 1)

	// Count errors
	if status >= 400 {
		statsdClient.Incr("errors", tags, 1)
	}
}

// RecordCacheHit records cache hit/miss
func RecordCacheHit(operation string, hit bool) {
	if statsdClient == nil {
		return
	}

	hitStr := "false"
	if hit {
		hitStr = "true"
	}
	tags := []string{
		"operation:" + operation,
		"hit:" + hitStr,
	}

	if hit {
		statsdClient.Incr("cache.hit", tags, 1)
	} else {
		statsdClient.Incr("cache.miss", tags, 1)
	}
}

// RecordPostCreated records post creation
func RecordPostCreated(userID string) {
	if statsdClient == nil {
		return
	}

	statsdClient.Incr("posts.created", nil, 1)
}

// RecordInteraction records post interactions
func RecordInteraction(interactionType string) {
	if statsdClient == nil {
		return
	}

	tags := []string{"type:" + interactionType}
	statsdClient.Incr("interactions", tags, 1)
}

// SetTimelineSize records timeline size
func SetTimelineSize(userID string, size int) {
	if statsdClient == nil {
		return
	}

	statsdClient.Gauge("timeline.size", float64(size), nil, 1)
}

// RecordDatabaseQuery records database query timing
func RecordDatabaseQuery(query string, duration time.Duration) {
	if statsdClient == nil {
		return
	}

	tags := []string{"query:" + query}
	statsdClient.Timing("db.query.duration", duration, tags, 1)
}
