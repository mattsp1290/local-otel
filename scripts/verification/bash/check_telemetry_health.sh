#!/bin/bash

# Agent Observability Verifier Health Check Script
# This script verifies that all telemetry services are running and healthy

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

echo -e "${BLUE}🔍 Agent Observability Verifier Health Check${NC}"

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

# Check if Docker is running
if ! docker info &> /dev/null; then
    print_error "Docker is not running. Please start Docker Desktop."
    exit 1
fi

# Use docker-compose or docker compose based on availability
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    COMPOSE_CMD="docker compose"
fi

# Check Docker containers
echo -e "\n${BLUE}Checking Docker containers...${NC}"

services=("otel-collector" "statsd" "prometheus" "grafana" "jaeger" "filebeat")
container_names=("telemetry-nest-otel-collector" "telemetry-nest-statsd" "telemetry-nest-prometheus" "telemetry-nest-grafana" "telemetry-nest-jaeger" "telemetry-nest-filebeat")

for i in "${!services[@]}"; do
    service="${services[$i]}"
    container="${container_names[$i]}"
    
    if docker ps --filter "name=$container" --filter "status=running" | grep -q "$container"; then
        print_status "$service container is running"
    else
        print_error "$service container is not running"
        echo "  Try: $COMPOSE_CMD up -d $service"
    fi
done

# Check service endpoints
echo -e "\n${BLUE}Checking service endpoints...${NC}"

check_endpoint() {
    local service_name=$1
    local url=$2
    local timeout=${3:-5}
    
    if curl -f -s --max-time "$timeout" "$url" > /dev/null 2>&1; then
        print_status "$service_name endpoint is responding"
        return 0
    else
        print_error "$service_name endpoint is not responding ($url)"
        return 1
    fi
}

# Health check endpoints
check_endpoint "OpenTelemetry Collector Health" "http://localhost:13133/"
check_endpoint "OpenTelemetry Collector Metrics" "http://localhost:8889/metrics"
check_endpoint "Prometheus Health" "http://localhost:9090/-/healthy"
check_endpoint "Prometheus Targets" "http://localhost:9090/api/v1/targets"
check_endpoint "Grafana Health" "http://localhost:3000/api/health"
check_endpoint "Jaeger UI" "http://localhost:16686/"

# Check StatsD (UDP, so we'll check the admin interface)
if nc -z -u localhost 8125 2>/dev/null; then
    print_status "StatsD UDP port is open"
else
    print_warning "StatsD UDP port check failed (this is normal if nc doesn't support UDP)"
fi

check_endpoint "StatsD Admin" "http://localhost:8126/" 10

# Check data directories
echo -e "\n${BLUE}Checking data directories...${NC}"

data_dirs=("data/traces" "data/metrics" "data/logs" "data/processed")

for dir in "${data_dirs[@]}"; do
    if [ -d "$dir" ]; then
        print_status "$dir directory exists"
        
        # Check if directory has files
        if [ "$(ls -A "$dir" 2>/dev/null)" ]; then
            file_count=$(ls -1 "$dir" | wc -l)
            echo "  └─ Contains $file_count files"
        else
            echo "  └─ Directory is empty (normal for new setup)"
        fi
    else
        print_error "$dir directory does not exist"
    fi
done

# Check file permissions
echo -e "\n${BLUE}Checking file permissions...${NC}"

if [ -w "data/" ]; then
    print_status "Data directory is writable"
else
    print_error "Data directory is not writable"
fi

# Check network connectivity between containers
echo -e "\n${BLUE}Checking container network connectivity...${NC}"

# Test if otel-collector can reach other services
if docker exec telemetry-nest-otel-collector nc -z prometheus 9090 2>/dev/null; then
    print_status "OTel Collector can reach Prometheus"
else
    print_warning "OTel Collector cannot reach Prometheus"
fi

if docker exec telemetry-nest-otel-collector nc -z jaeger 14250 2>/dev/null; then
    print_status "OTel Collector can reach Jaeger"
else
    print_warning "OTel Collector cannot reach Jaeger"
fi

# Check configuration files
echo -e "\n${BLUE}Checking configuration files...${NC}"

config_files=(
    "docker/configs/otel/otel-collector-config.yaml"
    "docker/configs/statsd/config.js"
    "docker/configs/prometheus/prometheus.yml"
    "docker/configs/filebeat/filebeat.yml"
)

for config_file in "${config_files[@]}"; do
    if [ -f "$config_file" ]; then
        print_status "$config_file exists"
    else
        print_error "$config_file is missing"
    fi
done

# Check for recent telemetry data
echo -e "\n${BLUE}Checking for recent telemetry data...${NC}"

# Check for recent trace files
if find data/traces -name "*.json*" -mmin -10 2>/dev/null | grep -q .; then
    print_status "Recent trace data found"
else
    print_warning "No recent trace data found (normal if no traces sent)"
fi

# Check for recent metric files
if find data/metrics -name "*.json*" -o -name "*.prom" -mmin -10 2>/dev/null | grep -q .; then
    print_status "Recent metric data found"
else
    print_warning "No recent metric data found (normal if no metrics sent)"
fi

# Check for recent log files
if find data/logs -name "*.json*" -mmin -10 2>/dev/null | grep -q .; then
    print_status "Recent log data found"
else
    print_warning "No recent log data found (normal if no logs sent)"
fi

# Check Prometheus targets
echo -e "\n${BLUE}Checking Prometheus targets...${NC}"

if command -v jq &> /dev/null; then
    targets_response=$(curl -s "http://localhost:9090/api/v1/targets" 2>/dev/null)
    if [ $? -eq 0 ]; then
        active_targets=$(echo "$targets_response" | jq -r '.data.activeTargets | length' 2>/dev/null)
        if [ "$active_targets" -gt 0 ]; then
            print_status "Prometheus has $active_targets active targets"
            
            # Show target health
            echo "$targets_response" | jq -r '.data.activeTargets[] | "  └─ \(.labels.job): \(.health)"' 2>/dev/null
        else
            print_warning "Prometheus has no active targets"
        fi
    else
        print_warning "Could not fetch Prometheus targets"
    fi
else
    print_warning "jq not available, skipping detailed Prometheus target check"
fi

# Summary
echo -e "\n${BLUE}Health Check Summary${NC}"

# Count successful checks
total_containers=${#services[@]}
running_containers=$(docker ps --filter "name=telemetry-nest-" --format "table {{.Names}}" | grep -c "telemetry-nest-" || echo "0")

echo "• Containers: $running_containers/$total_containers running"

# Check overall health
if [ "$running_containers" -eq "$total_containers" ]; then
    echo -e "${GREEN}🎉 All telemetry services are healthy!${NC}"
    
    echo -e "\n${BLUE}Ready to receive telemetry data:${NC}"
    echo "• Send OTLP traces/metrics: localhost:4317 (gRPC) or localhost:4318 (HTTP)"
    echo "• Send StatsD metrics: localhost:8125 (UDP)"
    echo "• View data files: ls -la data/"
    
    exit 0
else
    echo -e "${YELLOW}⚠ Some services may need attention${NC}"
    
    echo -e "\n${BLUE}Troubleshooting:${NC}"
    echo "• Check logs: docker-compose logs [service-name]"
    echo "• Restart services: ./scripts/setup/start-telemetry-stack.sh"
    echo "• Reset environment: ./scripts/setup/setup-telemetry-env.sh"
    
    exit 1
fi
