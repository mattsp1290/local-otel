#!/bin/bash

# Agent Observability Verifier Setup Script
# This script sets up the complete Docker-based telemetry environment

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

echo -e "${BLUE}🦅 Setting up Agent Observability Verifier${NC}"
echo "Project root: $PROJECT_ROOT"

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

# Check prerequisites
echo -e "\n${BLUE}Checking prerequisites...${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker Desktop."
    exit 1
fi
print_status "Docker is installed"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose is not available. Please install Docker Compose."
    exit 1
fi
print_status "Docker Compose is available"

# Check if Docker is running
if ! docker info &> /dev/null; then
    print_error "Docker is not running. Please start Docker Desktop."
    exit 1
fi
print_status "Docker is running"

# Check available resources
DOCKER_MEMORY=$(docker system info --format '{{.MemTotal}}' 2>/dev/null || echo "0")
if [ "$DOCKER_MEMORY" -lt 4000000000 ]; then
    print_warning "Docker has less than 4GB memory allocated. Consider increasing memory allocation."
else
    print_status "Docker has sufficient memory allocated"
fi

# Check for required tools
if command -v jq &> /dev/null; then
    print_status "jq is available"
else
    print_warning "jq is not installed. Install with: brew install jq"
fi

if command -v yq &> /dev/null; then
    print_status "yq is available"
else
    print_warning "yq is not installed. Install with: brew install yq"
fi

# Create directory structure
echo -e "\n${BLUE}Creating directory structure...${NC}"
cd "$PROJECT_ROOT"

# Ensure all directories exist
mkdir -p data/{metrics,traces,logs,processed}
mkdir -p docker/configs/{otel,statsd,prometheus,grafana,filebeat}
mkdir -p scripts/{setup,verification/{python,go,bash},automation}
mkdir -p docs

print_status "Directory structure created"

# Set proper permissions
chmod -R 755 data/
chmod -R 755 scripts/
chmod 644 docker/configs/*/*.{yml,yaml,js} 2>/dev/null || true

print_status "Permissions set"

# Create Docker network
echo -e "\n${BLUE}Setting up Docker network...${NC}"
if docker network ls | grep -q "telemetry-nest-network"; then
    print_warning "Network telemetry-nest-network already exists"
else
    docker network create telemetry-nest-network
    print_status "Created Docker network: telemetry-nest-network"
fi

# Create Docker volumes
echo -e "\n${BLUE}Setting up Docker volumes...${NC}"
if docker volume ls | grep -q "telemetry-nest-prometheus-data"; then
    print_warning "Volume telemetry-nest-prometheus-data already exists"
else
    docker volume create telemetry-nest-prometheus-data
    print_status "Created Docker volume: telemetry-nest-prometheus-data"
fi

if docker volume ls | grep -q "telemetry-nest-grafana-data"; then
    print_warning "Volume telemetry-nest-grafana-data already exists"
else
    docker volume create telemetry-nest-grafana-data
    print_status "Created Docker volume: telemetry-nest-grafana-data"
fi

# Pull Docker images
echo -e "\n${BLUE}Pulling Docker images...${NC}"
echo "This may take a few minutes..."

images=(
    "otel/opentelemetry-collector-contrib:latest"
    "statsd/statsd:latest"
    "prom/prometheus:latest"
    "grafana/grafana:latest"
    "jaegertracing/all-in-one:latest"
    "elastic/filebeat:8.11.0"
)

for image in "${images[@]}"; do
    echo "Pulling $image..."
    if docker pull "$image"; then
        print_status "Pulled $image"
    else
        print_error "Failed to pull $image"
        exit 1
    fi
done

# Create environment file
echo -e "\n${BLUE}Creating environment configuration...${NC}"
cat > .env << EOF
# Agent Observability Verifier Configuration

# Environment
ENVIRONMENT=local-development
PROJECT_NAME=canary-api

# OpenTelemetry Collector
OTEL_COLLECTOR_CONFIG_PATH=./docker/configs/otel/otel-collector-config.yaml
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318

# StatsD
STATSD_HOST=localhost
STATSD_PORT=8125
STATSD_CONFIG_PATH=./docker/configs/statsd/config.js

# Prometheus
PROMETHEUS_CONFIG_PATH=./docker/configs/prometheus/prometheus.yml
PROMETHEUS_DATA_RETENTION=7d

# Grafana
GRAFANA_ADMIN_PASSWORD=admin
GRAFANA_CONFIG_PATH=./docker/configs/grafana

# Filebeat
FILEBEAT_CONFIG_PATH=./docker/configs/filebeat/filebeat.yml

# Data paths
DATA_PATH=./data
LOGS_PATH=./data/logs
METRICS_PATH=./data/metrics
TRACES_PATH=./data/traces
PROCESSED_PATH=./data/processed

# Network
TELEMETRY_NETWORK=telemetry-nest-network

# Ports
OTEL_GRPC_PORT=4317
OTEL_HTTP_PORT=4318
OTEL_HEALTH_PORT=13133
OTEL_METRICS_PORT=8889
STATSD_PORT=8125
STATSD_ADMIN_PORT=8126
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
JAEGER_UI_PORT=16686
JAEGER_GRPC_PORT=14250
FILEBEAT_HTTP_PORT=5066
EOF

print_status "Created .env configuration file"

# Validate configuration files
echo -e "\n${BLUE}Validating configuration files...${NC}"

# Check if all required config files exist
config_files=(
    "docker-compose.yml"
    "docker/configs/otel/otel-collector-config.yaml"
    "docker/configs/statsd/config.js"
    "docker/configs/prometheus/prometheus.yml"
    "docker/configs/filebeat/filebeat.yml"
)

for config_file in "${config_files[@]}"; do
    if [ -f "$config_file" ]; then
        print_status "Found $config_file"
    else
        print_error "Missing $config_file"
        exit 1
    fi
done

# Test Docker Compose configuration
if docker-compose config > /dev/null 2>&1 || docker compose config > /dev/null 2>&1; then
    print_status "Docker Compose configuration is valid"
else
    print_error "Docker Compose configuration is invalid"
    exit 1
fi

# Create initial data files to ensure proper permissions
echo -e "\n${BLUE}Initializing data directories...${NC}"
touch data/logs/.gitkeep
touch data/metrics/.gitkeep
touch data/traces/.gitkeep
touch data/processed/.gitkeep

print_status "Data directories initialized"

# Summary
echo -e "\n${GREEN}🎉 Setup completed successfully!${NC}"
echo -e "\n${BLUE}Next steps:${NC}"
echo "1. Start the telemetry stack:"
echo "   ./scripts/setup/start-telemetry-stack.sh"
echo ""
echo "2. Access the services:"
echo "   • Grafana:     http://localhost:3000 (admin/admin)"
echo "   • Prometheus:  http://localhost:9090"
echo "   • Jaeger:      http://localhost:16686"
echo "   • OTel Health: http://localhost:13133"
echo ""
echo "3. Run verification tests:"
echo "   ./scripts/verification/bash/check_telemetry_health.sh"
echo ""
echo "4. View telemetry data files:"
echo "   ls -la data/"
echo ""
echo -e "${YELLOW}Note: Application integration requires additional configuration.${NC}"
echo "See docs/application-integration-guide.md for details."
