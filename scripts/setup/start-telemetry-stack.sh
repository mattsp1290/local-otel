#!/bin/bash

# SpacetimeDB Local Telemetry Stack Start Script
# This script starts all telemetry services using Docker Compose

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo -e "${BLUE}🚀 Starting SpacetimeDB Local Telemetry Stack${NC}"

# Function to print status
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Change to project root
cd "$PROJECT_ROOT"

# Check if setup has been run
if [ ! -f ".env" ]; then
    print_error "Environment not set up. Please run ./scripts/setup/setup-telemetry-env.sh first"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    print_error "Docker is not running. Please start Docker Desktop."
    exit 1
fi

# Stop any existing containers
echo -e "\n${BLUE}Stopping any existing containers...${NC}"
if docker-compose down 2>/dev/null || docker compose down 2>/dev/null; then
    print_status "Stopped existing containers"
else
    print_warning "No existing containers to stop"
fi

# Start the telemetry stack
echo -e "\n${BLUE}Starting telemetry services...${NC}"
echo "This may take a few minutes for first-time startup..."

# Use docker-compose or docker compose based on availability
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    COMPOSE_CMD="docker compose"
fi

# Start services in dependency order
echo "Starting Prometheus..."
if $COMPOSE_CMD up -d prometheus; then
    print_status "Prometheus started"
else
    print_error "Failed to start Prometheus"
    exit 1
fi

echo "Starting Grafana..."
if $COMPOSE_CMD up -d grafana; then
    print_status "Grafana started"
else
    print_error "Failed to start Grafana"
    exit 1
fi

echo "Starting Jaeger..."
if $COMPOSE_CMD up -d jaeger; then
    print_status "Jaeger started"
else
    print_error "Failed to start Jaeger"
    exit 1
fi

echo "Starting StatsD..."
if $COMPOSE_CMD up -d statsd; then
    print_status "StatsD started"
else
    print_error "Failed to start StatsD"
    exit 1
fi

echo "Starting OpenTelemetry Collector..."
if $COMPOSE_CMD up -d otel-collector; then
    print_status "OpenTelemetry Collector started"
else
    print_error "Failed to start OpenTelemetry Collector"
    exit 1
fi

echo "Starting Filebeat..."
if $COMPOSE_CMD up -d filebeat; then
    print_status "Filebeat started"
else
    print_error "Failed to start Filebeat"
    exit 1
fi

# Wait for services to be healthy
echo -e "\n${BLUE}Waiting for services to be healthy...${NC}"
sleep 10

# Check service health
check_service_health() {
    local service_name=$1
    local health_url=$2
    local max_attempts=30
    local attempt=1

    echo "Checking $service_name health..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$health_url" > /dev/null 2>&1; then
            print_status "$service_name is healthy"
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_warning "$service_name health check timed out"
    return 1
}

# Health checks
check_service_health "OpenTelemetry Collector" "http://localhost:13133/"
check_service_health "Prometheus" "http://localhost:9090/-/healthy"
check_service_health "Grafana" "http://localhost:3000/api/health"
check_service_health "Jaeger" "http://localhost:16686/"

# Check container status
echo -e "\n${BLUE}Container Status:${NC}"
$COMPOSE_CMD ps

# Show service URLs
echo -e "\n${GREEN}🎉 Telemetry stack started successfully!${NC}"
echo -e "\n${BLUE}Service URLs:${NC}"
echo "• Grafana Dashboard:     http://localhost:3000 (admin/admin)"
echo "• Prometheus:            http://localhost:9090"
echo "• Jaeger Tracing:        http://localhost:16686"
echo "• OpenTelemetry Health:  http://localhost:13133"
echo "• StatsD Admin:          http://localhost:8126"

echo -e "\n${BLUE}Telemetry Endpoints:${NC}"
echo "• OTLP gRPC:             localhost:4317"
echo "• OTLP HTTP:             localhost:4318"
echo "• StatsD UDP:            localhost:8125"
echo "• Prometheus Metrics:    localhost:8889"

echo -e "\n${BLUE}Data Directories:${NC}"
echo "• Traces:                ./data/traces/"
echo "• Metrics:               ./data/metrics/"
echo "• Logs:                  ./data/logs/"
echo "• Processed:             ./data/processed/"

echo -e "\n${BLUE}Next Steps:${NC}"
echo "1. Run health checks:"
echo "   ./scripts/verification/bash/check_telemetry_health.sh"
echo ""
echo "2. Send test data:"
echo "   ./scripts/verification/python/test_metrics_pipeline.py"
echo ""
echo "3. View logs:"
echo "   docker-compose logs -f otel-collector"
echo ""
echo "4. Stop the stack:"
echo "   ./scripts/setup/stop-telemetry-stack.sh"

echo -e "\n${YELLOW}Note: To integrate with SpacetimeDB, see docs/spacetimedb-integration.md${NC}"
