#!/bin/bash

# Agent Observability Verifier Stop Script
# This script stops all telemetry services and optionally cleans up data

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

echo -e "${BLUE}🛑 Stopping Agent Observability Verifier${NC}"

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

# Parse command line arguments
CLEAN_DATA=false
REMOVE_VOLUMES=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --clean-data)
            CLEAN_DATA=true
            shift
            ;;
        --remove-volumes)
            REMOVE_VOLUMES=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --clean-data      Remove all telemetry data files"
            echo "  --remove-volumes  Remove Docker volumes (Prometheus/Grafana data)"
            echo "  --help, -h        Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    # Stop services only"
            echo "  $0 --clean-data      # Stop services and clean data files"
            echo "  $0 --remove-volumes  # Stop services and remove volumes"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check if Docker is running
if ! docker info &> /dev/null; then
    print_error "Docker is not running. Cannot stop containers."
    exit 1
fi

# Use docker-compose or docker compose based on availability
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    COMPOSE_CMD="docker compose"
fi

# Stop and remove containers
echo -e "\n${BLUE}Stopping telemetry services...${NC}"

if $COMPOSE_CMD down; then
    print_status "Stopped all telemetry containers"
else
    print_error "Failed to stop some containers"
fi

# Show container status
echo -e "\n${BLUE}Container Status:${NC}"
if docker ps --filter "name=telemetry-nest-" --format "table {{.Names}}\t{{.Status}}" | grep -q "telemetry-nest-"; then
    docker ps --filter "name=telemetry-nest-" --format "table {{.Names}}\t{{.Status}}"
    print_warning "Some telemetry nest containers are still running"
else
    print_status "All telemetry nest containers are stopped"
fi

# Clean data files if requested
if [ "$CLEAN_DATA" = true ]; then
    echo -e "\n${BLUE}Cleaning telemetry data files...${NC}"
    
    if [ -d "data" ]; then
        # Remove all data files but keep directory structure
        find data -type f -name "*.json*" -delete 2>/dev/null || true
        find data -type f -name "*.log" -delete 2>/dev/null || true
        find data -type f -name "*.prom" -delete 2>/dev/null || true
        find data -type f -name "filebeat-*" -delete 2>/dev/null || true
        
        # Recreate .gitkeep files
        touch data/logs/.gitkeep
        touch data/metrics/.gitkeep
        touch data/traces/.gitkeep
        touch data/processed/.gitkeep
        
        print_status "Cleaned telemetry data files"
    else
        print_warning "Data directory not found"
    fi
fi

# Remove Docker volumes if requested
if [ "$REMOVE_VOLUMES" = true ]; then
    echo -e "\n${BLUE}Removing Docker volumes...${NC}"
    
    volumes=("telemetry-nest-prometheus-data" "telemetry-nest-grafana-data")
    
    for volume in "${volumes[@]}"; do
        if docker volume ls | grep -q "$volume"; then
            if docker volume rm "$volume" 2>/dev/null; then
                print_status "Removed volume: $volume"
            else
                print_warning "Failed to remove volume: $volume (may be in use)"
            fi
        else
            print_warning "Volume not found: $volume"
        fi
    done
fi

# Check for any remaining telemetry containers
echo -e "\n${BLUE}Checking for remaining containers...${NC}"
remaining_containers=$(docker ps -a --filter "name=telemetry-nest-" --format "{{.Names}}" | wc -l)

if [ "$remaining_containers" -gt 0 ]; then
    print_warning "Found $remaining_containers remaining telemetry nest containers"
    echo "To remove them completely, run:"
    echo "  docker ps -a --filter \"name=telemetry-nest-\" --format \"{{.Names}}\" | xargs docker rm -f"
else
    print_status "No remaining telemetry nest containers found"
fi

# Check for any remaining networks
if docker network ls | grep -q "telemetry-nest-network"; then
    print_warning "Telemetry nest network still exists"
    echo "To remove it, run:"
    echo "  docker network rm telemetry-nest-network"
else
    print_status "Telemetry nest network is removed"
fi

# Summary
echo -e "\n${GREEN}🎉 Telemetry stack stopped successfully!${NC}"

if [ "$CLEAN_DATA" = true ] || [ "$REMOVE_VOLUMES" = true ]; then
    echo -e "\n${BLUE}Cleanup Summary:${NC}"
    [ "$CLEAN_DATA" = true ] && echo "• Data files cleaned"
    [ "$REMOVE_VOLUMES" = true ] && echo "• Docker volumes removed"
fi

echo -e "\n${BLUE}To restart the telemetry stack:${NC}"
echo "  ./scripts/setup/start-telemetry-stack.sh"

echo -e "\n${BLUE}To completely reset the environment:${NC}"
echo "  ./scripts/setup/stop-telemetry-stack.sh --clean-data --remove-volumes"
echo "  ./scripts/setup/setup-telemetry-env.sh"
