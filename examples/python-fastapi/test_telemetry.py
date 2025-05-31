#!/usr/bin/env python3
"""
Telemetry Verification Script for Canary API
Tests that traces, metrics, and logs are properly collected
"""

import json
import time
import requests
import sys
from datetime import datetime, timedelta

# Configuration
API_BASE_URL = "http://localhost:8000"
JAEGER_API_URL = "http://localhost:16686/api"
PROMETHEUS_API_URL = "http://localhost:9090/api/v1"
LOGS_FILE = "../../data/logs/logs.jsonl"

# ANSI color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
ENDC = '\033[0m'

def print_status(message, status="info"):
    """Print colored status messages"""
    if status == "success":
        print(f"{GREEN}✓ {message}{ENDC}")
    elif status == "error":
        print(f"{RED}✗ {message}{ENDC}")
    elif status == "warning":
        print(f"{YELLOW}⚠ {message}{ENDC}")
    else:
        print(f"{BLUE}ℹ {message}{ENDC}")

def test_api_endpoints():
    """Test all API endpoints and generate telemetry data"""
    print_status("\n=== Testing API Endpoints ===", "info")
    
    results = {
        "chirp": False,
        "nest": False,
        "flock": False
    }
    
    try:
        # Test /chirp endpoint
        print_status("Testing GET /chirp...")
        response = requests.get(f"{API_BASE_URL}/chirp")
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "alive":
                print_status(f"Chirp response: {data}", "success")
                results["chirp"] = True
        else:
            print_status(f"Chirp failed with status {response.status_code}", "error")
    except Exception as e:
        print_status(f"Chirp error: {e}", "error")
    
    try:
        # Test /nest endpoint
        print_status("\nTesting POST /nest...")
        nest_data = {
            "name": "Test Nest",
            "type": "deluxe",
            "material": "premium twigs"
        }
        response = requests.post(f"{API_BASE_URL}/nest", json=nest_data)
        if response.status_code == 201:
            data = response.json()
            print_status(f"Nest created: {data}", "success")
            results["nest"] = True
        else:
            print_status(f"Nest creation failed with status {response.status_code}", "error")
    except Exception as e:
        print_status(f"Nest error: {e}", "error")
    
    try:
        # Create more nests for flock testing
        for i in range(5):
            requests.post(f"{API_BASE_URL}/nest", json={
                "name": f"Nest {i}",
                "type": ["standard", "deluxe", "premium"][i % 3]
            })
        
        # Test /flock endpoint
        print_status("\nTesting GET /flock...")
        response = requests.get(f"{API_BASE_URL}/flock?limit=3&offset=0")
        if response.status_code == 200:
            data = response.json()
            print_status(f"Flock returned {len(data)} nests", "success")
            results["flock"] = True
        else:
            print_status(f"Flock failed with status {response.status_code}", "error")
    except Exception as e:
        print_status(f"Flock error: {e}", "error")
    
    return results

def verify_traces():
    """Verify traces are being collected in Jaeger"""
    print_status("\n=== Verifying Traces in Jaeger ===", "info")
    
    # Wait a bit for traces to be processed
    time.sleep(3)
    
    try:
        # Query Jaeger for canary-api traces
        response = requests.get(
            f"{JAEGER_API_URL}/traces",
            params={
                "service": "canary-api",
                "limit": 10,
                "lookback": "1h"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            traces = data.get("data", [])
            
            if traces:
                print_status(f"Found {len(traces)} traces in Jaeger", "success")
                
                # Analyze trace details
                operations = set()
                for trace in traces:
                    for span in trace.get("spans", []):
                        operations.add(span.get("operationName", ""))
                
                print_status(f"Operations found: {', '.join(operations)}", "info")
                
                # Check for expected operations
                expected_ops = ["chirp_handler", "nest_handler", "flock_handler"]
                found_ops = [op for op in expected_ops if any(op in trace_op for trace_op in operations)]
                
                if found_ops:
                    print_status(f"Found expected operations: {', '.join(found_ops)}", "success")
                    return True
                else:
                    print_status("Expected operations not found in traces", "warning")
            else:
                print_status("No traces found in Jaeger yet", "warning")
        else:
            print_status(f"Failed to query Jaeger API: {response.status_code}", "error")
    except Exception as e:
        print_status(f"Error verifying traces: {e}", "error")
    
    return False

def verify_metrics():
    """Verify metrics are being collected in Prometheus"""
    print_status("\n=== Verifying Metrics in Prometheus ===", "info")
    
    # Wait a bit for metrics to be scraped
    time.sleep(5)
    
    metrics_to_check = [
        ("canary_api_requests_total", "Request counter"),
        ("canary_api_request_duration", "Request duration"),
        ("canary_api_nest_count", "Nest count gauge"),
        ("canary_api_nests_created_total", "Nests created counter")
    ]
    
    found_metrics = []
    
    try:
        for metric_name, description in metrics_to_check:
            response = requests.get(
                f"{PROMETHEUS_API_URL}/query",
                params={"query": metric_name}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("data", {}).get("result"):
                    result = data["data"]["result"]
                    print_status(f"Found metric '{metric_name}' ({description})", "success")
                    
                    # Show sample values
                    for series in result[:2]:  # Show first 2 series
                        labels = series.get("metric", {})
                        value = series.get("value", [None, None])[1]
                        label_str = ", ".join([f"{k}={v}" for k, v in labels.items() if k != "__name__"])
                        print_status(f"  → {label_str}: {value}", "info")
                    
                    found_metrics.append(metric_name)
                else:
                    print_status(f"Metric '{metric_name}' not found yet", "warning")
            else:
                print_status(f"Failed to query metric '{metric_name}': {response.status_code}", "error")
    except Exception as e:
        print_status(f"Error verifying metrics: {e}", "error")
    
    return len(found_metrics) > 0

def verify_logs():
    """Verify structured logs are being written"""
    print_status("\n=== Verifying Structured Logs ===", "info")
    
    logs_found = False
    trace_ids_found = False
    
    try:
        # Check if logs file exists
        import os
        if not os.path.exists(LOGS_FILE):
            # Try checking stdout logs from docker
            print_status("Log file not found, checking container logs...", "warning")
            # In production, logs would be in the file or stdout
            return False
        
        # Read last 100 lines of logs
        with open(LOGS_FILE, 'r') as f:
            lines = f.readlines()[-100:]
        
        canary_logs = []
        for line in lines:
            try:
                log = json.loads(line.strip())
                if log.get("service") == "canary-api":
                    canary_logs.append(log)
                    if log.get("trace_id"):
                        trace_ids_found = True
            except:
                continue
        
        if canary_logs:
            print_status(f"Found {len(canary_logs)} canary-api log entries", "success")
            logs_found = True
            
            # Show sample logs
            for log in canary_logs[-3:]:
                level = log.get("level", "?")
                message = log.get("message", "")
                trace_id = log.get("trace_id", "")
                print_status(f"  [{level}] {message} (trace_id: {trace_id[:8]}...)" if trace_id else f"  [{level}] {message}", "info")
            
            if trace_ids_found:
                print_status("Logs contain trace IDs for correlation", "success")
            else:
                print_status("Logs missing trace IDs", "warning")
        else:
            print_status("No canary-api logs found", "warning")
            
    except Exception as e:
        print_status(f"Error verifying logs: {e}", "error")
    
    return logs_found

def run_full_test():
    """Run all telemetry verification tests"""
    print_status("🐦 Canary API Telemetry Verification", "info")
    print_status("=" * 50, "info")
    
    # Check if API is reachable
    try:
        response = requests.get(f"{API_BASE_URL}/metrics/health", timeout=5)
        if response.status_code != 200:
            print_status("API is not reachable. Is the service running?", "error")
            print_status("Run: docker-compose up", "info")
            return False
    except:
        print_status("Cannot connect to API at http://localhost:8000", "error")
        print_status("Make sure the telemetry stack and canary-api are running:", "info")
        print_status("  1. cd ../..", "info")
        print_status("  2. ./scripts/setup/start-telemetry-stack.sh", "info")
        print_status("  3. cd examples/python-fastapi", "info")
        print_status("  4. docker-compose up", "info")
        return False
    
    # Run tests
    results = {
        "endpoints": test_api_endpoints(),
        "traces": verify_traces(),
        "metrics": verify_metrics(),
        "logs": verify_logs()
    }
    
    # Summary
    print_status("\n=== Test Summary ===", "info")
    
    endpoint_success = all(results["endpoints"].values())
    all_passed = endpoint_success and results["traces"] and results["metrics"]
    
    if endpoint_success:
        print_status("All API endpoints working correctly", "success")
    else:
        print_status("Some API endpoints failed", "error")
    
    if results["traces"]:
        print_status("Traces are being collected in Jaeger", "success")
    else:
        print_status("Traces not verified in Jaeger", "warning")
    
    if results["metrics"]:
        print_status("Metrics are being collected in Prometheus", "success")
    else:
        print_status("Metrics not verified in Prometheus", "warning")
    
    if results["logs"]:
        print_status("Structured logs are being written", "success")
    else:
        print_status("Structured logs not verified", "warning")
    
    print_status("\n=== Next Steps ===", "info")
    print_status("View traces: http://localhost:16686 (search for 'canary-api')", "info")
    print_status("View metrics: http://localhost:9090 (search for 'canary_api')", "info")
    print_status("View dashboards: http://localhost:3000 (admin/admin)", "info")
    
    return all_passed

if __name__ == "__main__":
    success = run_full_test()
    sys.exit(0 if success else 1)
