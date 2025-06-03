#!/usr/bin/env python3
"""
SigNoz Migration Verification Script

This script verifies that the migration to SigNoz is successful by:
1. Checking file exports are still working
2. Verifying data is flowing to SigNoz
3. Comparing data between both systems
4. Generating a migration success report
"""

import json
import time
import requests
from datetime import datetime, timedelta
import os
import sys
from typing import Dict, List, Tuple, Any
from pathlib import Path

# Configuration
SIGNOZ_QUERY_API = "http://localhost:8080"
JAEGER_API = "http://localhost:16686"
PROMETHEUS_API = "http://localhost:9090"
OTEL_COLLECTOR_HEALTH = "http://localhost:13133"

# File paths
TRACES_FILE = "/Users/punk1290/git/local-otel/data/traces/traces.jsonl"
METRICS_FILE = "/Users/punk1290/git/local-otel/data/metrics/metrics.jsonl"
LOGS_FILE = "/Users/punk1290/git/local-otel/data/logs/logs.jsonl"

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def print_header(title: str):
    """Print a formatted header"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{title.center(60)}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

def print_success(message: str):
    """Print success message"""
    print(f"{GREEN}✓ {message}{RESET}")

def print_error(message: str):
    """Print error message"""
    print(f"{RED}✗ {message}{RESET}")

def print_warning(message: str):
    """Print warning message"""
    print(f"{YELLOW}⚠ {message}{RESET}")

def check_service_health(name: str, url: str) -> bool:
    """Check if a service is healthy"""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print_success(f"{name} is healthy at {url}")
            return True
        else:
            print_error(f"{name} returned status {response.status_code}")
            return False
    except Exception as e:
        print_error(f"{name} is not accessible: {str(e)}")
        return False

def check_file_exports() -> Dict[str, Any]:
    """Check if file exports are still working"""
    print_header("Checking File Exports")
    
    results = {
        "traces": {"exists": False, "recent": False, "count": 0},
        "metrics": {"exists": False, "recent": False, "count": 0},
        "logs": {"exists": False, "recent": False, "count": 0}
    }
    
    # Check traces file
    if os.path.exists(TRACES_FILE):
        results["traces"]["exists"] = True
        stat = os.stat(TRACES_FILE)
        modified_time = datetime.fromtimestamp(stat.st_mtime)
        age = datetime.now() - modified_time
        
        if age < timedelta(minutes=5):
            results["traces"]["recent"] = True
            print_success(f"Traces file is recent (modified {age.seconds} seconds ago)")
        else:
            print_warning(f"Traces file is old (modified {age} ago)")
        
        # Count lines
        with open(TRACES_FILE, 'r') as f:
            results["traces"]["count"] = sum(1 for _ in f)
        print_success(f"Found {results['traces']['count']} trace records")
    else:
        print_error(f"Traces file not found at {TRACES_FILE}")
    
    # Check metrics file
    if os.path.exists(METRICS_FILE):
        results["metrics"]["exists"] = True
        stat = os.stat(METRICS_FILE)
        modified_time = datetime.fromtimestamp(stat.st_mtime)
        age = datetime.now() - modified_time
        
        if age < timedelta(minutes=5):
            results["metrics"]["recent"] = True
            print_success(f"Metrics file is recent (modified {age.seconds} seconds ago)")
        else:
            print_warning(f"Metrics file is old (modified {age} ago)")
        
        # Count lines
        with open(METRICS_FILE, 'r') as f:
            results["metrics"]["count"] = sum(1 for _ in f)
        print_success(f"Found {results['metrics']['count']} metric records")
    else:
        print_error(f"Metrics file not found at {METRICS_FILE}")
    
    # Check logs file
    if os.path.exists(LOGS_FILE):
        results["logs"]["exists"] = True
        stat = os.stat(LOGS_FILE)
        modified_time = datetime.fromtimestamp(stat.st_mtime)
        age = datetime.now() - modified_time
        
        if age < timedelta(minutes=5):
            results["logs"]["recent"] = True
            print_success(f"Logs file is recent (modified {age.seconds} seconds ago)")
        else:
            print_warning(f"Logs file is old (modified {age} ago)")
        
        # Count lines
        with open(LOGS_FILE, 'r') as f:
            results["logs"]["count"] = sum(1 for _ in f)
        print_success(f"Found {results['logs']['count']} log records")
    else:
        print_error(f"Logs file not found at {LOGS_FILE}")
    
    return results

def check_signoz_data() -> Dict[str, Any]:
    """Check if data is flowing to SigNoz"""
    print_header("Checking SigNoz Data")
    
    results = {
        "services": [],
        "traces": 0,
        "metrics": [],
        "logs": 0,
        "healthy": False
    }
    
    # Check SigNoz health
    try:
        response = requests.get(f"{SIGNOZ_QUERY_API}/api/v1/health", timeout=5)
        if response.status_code == 200:
            results["healthy"] = True
            print_success("SigNoz Query Service is healthy")
        else:
            print_error(f"SigNoz health check failed with status {response.status_code}")
            return results
    except Exception as e:
        print_error(f"Cannot connect to SigNoz: {str(e)}")
        return results
    
    # Get services from SigNoz
    try:
        response = requests.get(f"{SIGNOZ_QUERY_API}/api/v1/services", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "data" in data and isinstance(data["data"], list):
                results["services"] = [s.get("serviceName", "") for s in data["data"]]
                print_success(f"Found {len(results['services'])} services in SigNoz: {', '.join(results['services'])}")
            else:
                print_warning("No services found in SigNoz yet")
    except Exception as e:
        print_error(f"Failed to get services: {str(e)}")
    
    # Get trace count
    try:
        # Query traces from last hour
        end_time = int(time.time() * 1000)  # milliseconds
        start_time = end_time - (60 * 60 * 1000)  # 1 hour ago
        
        params = {
            "start": start_time,
            "end": end_time,
            "limit": 100
        }
        
        response = requests.get(f"{SIGNOZ_QUERY_API}/api/v1/traces", params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "data" in data and isinstance(data["data"], list):
                results["traces"] = len(data["data"])
                print_success(f"Found {results['traces']} traces in SigNoz (last hour)")
            else:
                print_warning("No traces found in SigNoz yet")
    except Exception as e:
        print_error(f"Failed to get traces: {str(e)}")
    
    # Get metrics
    try:
        response = requests.get(f"{SIGNOZ_QUERY_API}/api/v1/metrics", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "data" in data and isinstance(data["data"], list):
                results["metrics"] = data["data"][:10]  # First 10 metrics
                print_success(f"Found {len(data['data'])} metrics in SigNoz")
                for metric in results["metrics"]:
                    print(f"  - {metric}")
            else:
                print_warning("No metrics found in SigNoz yet")
    except Exception as e:
        print_error(f"Failed to get metrics: {str(e)}")
    
    return results

def compare_data_sources() -> Dict[str, Any]:
    """Compare data between file exports and SigNoz"""
    print_header("Comparing Data Sources")
    
    comparison = {
        "traces": {"file_only": [], "signoz_only": [], "both": []},
        "discrepancies": []
    }
    
    # Read recent traces from file
    file_traces = set()
    if os.path.exists(TRACES_FILE):
        with open(TRACES_FILE, 'r') as f:
            # Read last 100 traces
            lines = f.readlines()[-100:]
            for line in lines:
                try:
                    trace = json.loads(line)
                    if "traceID" in trace:
                        file_traces.add(trace["traceID"])
                    elif "trace_id" in trace:
                        file_traces.add(trace["trace_id"])
                except:
                    pass
    
    # Get trace IDs from SigNoz
    signoz_traces = set()
    try:
        end_time = int(time.time() * 1000)
        start_time = end_time - (60 * 60 * 1000)
        
        params = {
            "start": start_time,
            "end": end_time,
            "limit": 100
        }
        
        response = requests.get(f"{SIGNOZ_QUERY_API}/api/v1/traces", params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "data" in data:
                for trace in data["data"]:
                    if "traceID" in trace:
                        signoz_traces.add(trace["traceID"])
    except Exception as e:
        print_error(f"Failed to get SigNoz traces for comparison: {str(e)}")
    
    # Compare
    if file_traces and signoz_traces:
        both = file_traces.intersection(signoz_traces)
        file_only = file_traces - signoz_traces
        signoz_only = signoz_traces - file_traces
        
        comparison["traces"]["both"] = list(both)
        comparison["traces"]["file_only"] = list(file_only)
        comparison["traces"]["signoz_only"] = list(signoz_only)
        
        print_success(f"Found {len(both)} traces in both systems")
        if file_only:
            print_warning(f"Found {len(file_only)} traces only in files")
        if signoz_only:
            print_warning(f"Found {len(signoz_only)} traces only in SigNoz")
        
        # Calculate match percentage
        if file_traces:
            match_percentage = (len(both) / len(file_traces)) * 100
            if match_percentage > 90:
                print_success(f"Data consistency: {match_percentage:.1f}% match rate")
            else:
                print_warning(f"Data consistency: {match_percentage:.1f}% match rate")
    else:
        print_warning("Cannot compare traces - insufficient data")
    
    return comparison

def generate_report(file_results: Dict, signoz_results: Dict, comparison: Dict) -> str:
    """Generate a comprehensive migration report"""
    print_header("Migration Report")
    
    report = []
    report.append("# SigNoz Migration Verification Report")
    report.append(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # Summary
    report.append("## Summary")
    
    all_good = True
    
    # Check file exports
    if all(file_results[key]["exists"] and file_results[key]["recent"] for key in ["traces", "metrics", "logs"]):
        report.append("✅ File exports are working correctly")
    else:
        report.append("❌ File exports have issues")
        all_good = False
    
    # Check SigNoz
    if signoz_results["healthy"] and signoz_results["services"] and signoz_results["traces"] > 0:
        report.append("✅ SigNoz is receiving data")
    else:
        report.append("❌ SigNoz data collection has issues")
        all_good = False
    
    # Check data consistency
    if comparison["traces"]["both"]:
        report.append("✅ Data is flowing to both systems")
    else:
        report.append("⚠️  Data consistency could not be verified")
    
    report.append("")
    
    # Detailed Results
    report.append("## Detailed Results")
    report.append("")
    
    report.append("### File Exports")
    report.append(f"- Traces: {file_results['traces']['count']} records")
    report.append(f"- Metrics: {file_results['metrics']['count']} records")
    report.append(f"- Logs: {file_results['logs']['count']} records")
    report.append("")
    
    report.append("### SigNoz Data")
    report.append(f"- Services: {', '.join(signoz_results['services']) if signoz_results['services'] else 'None'}")
    report.append(f"- Traces: {signoz_results['traces']} (last hour)")
    report.append(f"- Metrics: {len(signoz_results['metrics'])} types")
    report.append("")
    
    report.append("### Data Consistency")
    if comparison["traces"]["both"]:
        report.append(f"- Traces in both systems: {len(comparison['traces']['both'])}")
        report.append(f"- Traces only in files: {len(comparison['traces']['file_only'])}")
        report.append(f"- Traces only in SigNoz: {len(comparison['traces']['signoz_only'])}")
    else:
        report.append("- Could not compare trace data")
    report.append("")
    
    # Recommendations
    report.append("## Recommendations")
    if all_good:
        report.append("✅ Migration is successful! You can:")
        report.append("- Access SigNoz UI at http://localhost:3301")
        report.append("- Continue using file exports for testing")
        report.append("- Start creating dashboards and alerts in SigNoz")
    else:
        report.append("⚠️  Please address the following:")
        if not signoz_results["healthy"]:
            report.append("- Check SigNoz services are running: `docker-compose -f docker-compose.signoz.yml ps`")
        if not signoz_results["services"]:
            report.append("- Generate test data: `cd examples/python-fastapi && python test_telemetry.py`")
        if not file_results["traces"]["recent"]:
            report.append("- Check OpenTelemetry Collector logs: `docker logs telemetry-nest-otel-collector`")
    
    report_text = "\n".join(report)
    
    # Save report
    report_path = "SIGNOZ_MIGRATION_REPORT.md"
    with open(report_path, 'w') as f:
        f.write(report_text)
    
    print_success(f"Report saved to {report_path}")
    
    return report_text

def main():
    """Main verification flow"""
    print_header("SigNoz Migration Verification")
    print("This script will verify that your SigNoz migration is successful.")
    print("It checks file exports, SigNoz data ingestion, and data consistency.")
    
    # Check service health
    print_header("Service Health Checks")
    services_healthy = True
    
    services_healthy &= check_service_health("OpenTelemetry Collector", OTEL_COLLECTOR_HEALTH)
    services_healthy &= check_service_health("Jaeger", f"{JAEGER_API}/")
    services_healthy &= check_service_health("Prometheus", f"{PROMETHEUS_API}/-/healthy")
    services_healthy &= check_service_health("SigNoz Query Service", f"{SIGNOZ_QUERY_API}/api/v1/health")
    
    if not services_healthy:
        print_error("\nSome services are not healthy. Please check docker-compose logs.")
        print("Run: docker-compose -f docker-compose.signoz.yml logs")
        return 1
    
    # Check file exports
    file_results = check_file_exports()
    
    # Check SigNoz data
    signoz_results = check_signoz_data()
    
    # Compare data sources
    comparison = compare_data_sources()
    
    # Generate report
    report = generate_report(file_results, signoz_results, comparison)
    
    # Print summary
    print("\n" + "="*60)
    if file_results["traces"]["exists"] and signoz_results["healthy"] and signoz_results["traces"] > 0:
        print_success("MIGRATION SUCCESSFUL! 🎉")
        print("\nNext steps:")
        print("1. Access SigNoz UI at http://localhost:3301")
        print("2. Explore your services, traces, metrics, and logs")
        print("3. Create custom dashboards and alerts")
        print("4. Your file exports continue to work for testing")
    else:
        print_warning("MIGRATION IN PROGRESS")
        print("\nPlease check the report for recommendations.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
