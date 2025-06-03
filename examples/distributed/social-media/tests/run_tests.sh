#!/bin/bash

# Run Integration Tests for Distributed Social Media Platform

echo "🚀 Starting Integration Test Suite"
echo "================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Change to tests directory
cd "$(dirname "$0")"

# Check if virtual environment exists, create if not
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo -e "${YELLOW}Installing test dependencies...${NC}"
pip install -q -r requirements.txt

# Check if services are running
echo -e "\n${YELLOW}Checking service status...${NC}"
REQUIRED_SERVICES=(
    "social-media-nginx-1"
    "social-media-auth-service-1" 
    "social-media-user-profile-service-1"
    "social-media-auth-db-1"
    "social-media-user-db-1"
    "social-media-auth-redis-1"
    "social-media-profile-redis-1"
)

ALL_RUNNING=true
for service in "${REQUIRED_SERVICES[@]}"; do
    if docker ps --format '{{.Names}}' | grep -q "^${service}$"; then
        echo -e "${GREEN}✓${NC} $service is running"
    else
        echo -e "${RED}✗${NC} $service is NOT running"
        ALL_RUNNING=false
    fi
done

if [ "$ALL_RUNNING" = false ]; then
    echo -e "\n${RED}❌ Not all required services are running!${NC}"
    echo "Please run 'docker-compose up -d' from the social-media directory first."
    exit 1
fi

# Create reports directory if it doesn't exist
mkdir -p reports

# Run different test categories
echo -e "\n${YELLOW}Running Integration Tests...${NC}"
echo "================================="

# Run a quick smoke test first
echo -e "\n${YELLOW}1. Running smoke test...${NC}"
pytest -v -k "test_user_onboarding_flow" --tb=short

# Run integration tests (excluding slow ones for demo)
echo -e "\n${YELLOW}2. Running integration tests...${NC}"
pytest -v -m "integration and not slow" --tb=short -x

# Run observability tests
echo -e "\n${YELLOW}3. Running observability tests...${NC}"
pytest -v -m "observability" --tb=short -x

# Show test summary
echo -e "\n${GREEN}✅ Test execution completed!${NC}"
echo "================================="

# Display report location
if ls reports/test_report_*.json 1> /dev/null 2>&1; then
    LATEST_REPORT=$(ls -t reports/test_report_*.json | head -n1)
    echo -e "\n📊 Test report saved to: ${YELLOW}$LATEST_REPORT${NC}"
    
    # Show summary from report
    if command -v jq &> /dev/null; then
        echo -e "\n📈 Test Summary:"
        jq -r '. | "   Total Tests: \(.total)\n   Passed: \(.passed)\n   Failed: \(.failed)\n   Pass Rate: \(.pass_rate)%"' "$LATEST_REPORT"
    fi
fi

echo -e "\n${YELLOW}💡 Tips:${NC}"
echo "   - View traces in Jaeger: http://localhost:16686"
echo "   - View metrics in Grafana: http://localhost:3000"
echo "   - Run all tests: pytest -v"
echo "   - Run specific test: pytest -v -k 'test_name'"
