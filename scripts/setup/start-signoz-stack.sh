#!/bin/bash

# SigNoz-Enhanced Telemetry Stack Startup Script
# This script starts the complete observability stack with SigNoz integration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting SigNoz-Enhanced Telemetry Stack${NC}"
echo "================================================"

# Change to project root
cd "$PROJECT_ROOT"

# Check if docker-compose.signoz.yml exists
if [ ! -f "docker-compose.signoz.yml" ]; then
    echo -e "${RED}Error: docker-compose.signoz.yml not found!${NC}"
    echo "Please ensure you're in the correct directory."
    exit 1
fi

# Create network if it doesn't exist
echo -e "\n${YELLOW}Creating telemetry network...${NC}"
docker network create telemetry-nest-network 2>/dev/null || true

# Start the stack
echo -e "\n${YELLOW}Starting all services...${NC}"
docker-compose -f docker-compose.signoz.yml up -d

# Wait for services to be healthy
echo -e "\n${YELLOW}Waiting for services to be healthy...${NC}"
sleep 10

# Check service status
echo -e "\n${GREEN}Service Status:${NC}"
docker-compose -f docker-compose.signoz.yml ps

# Display access URLs
echo -e "\n${GREEN}✅ Stack is running! Access your services at:${NC}"
echo "================================================"
echo -e "📊 ${GREEN}SigNoz UI:${NC} http://localhost:3301 (NEW!)"
echo -e "📈 ${GREEN}Grafana:${NC} http://localhost:3000 (admin/admin)"
echo -e "🔍 ${GREEN}Jaeger:${NC} http://localhost:16686"
echo -e "📊 ${GREEN}Prometheus:${NC} http://localhost:9090"
echo -e "🔧 ${GREEN}OTel Health:${NC} http://localhost:13133"
echo -e "🗄️ ${GREEN}ClickHouse:${NC} http://localhost:8123"
echo "================================================"

echo -e "\n${YELLOW}Quick Start:${NC}"
echo "1. Generate test data: cd examples/python-fastapi && docker-compose up -d && python test_telemetry.py"
echo "2. View SigNoz UI: open http://localhost:3301"
echo "3. Verify migration: python scripts/verification/python/verify_signoz_migration.py"
echo "4. Check file exports: ls -la data/traces/ data/metrics/ data/logs/"

echo -e "\n${GREEN}To stop the stack:${NC} docker-compose -f docker-compose.signoz.yml down"
echo -e "${GREEN}To view logs:${NC} docker-compose -f docker-compose.signoz.yml logs -f [service-name]"
