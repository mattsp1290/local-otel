#!/usr/bin/env python3
"""
Agent Observability Verifier - Telemetry Pipeline Test Script

This script tests the telemetry pipeline by sending sample data to the local
OpenTelemetry environment and verifying the data is properly processed.
"""

import json
import time
import socket
import requests
import sys
import os
from datetime import datetime
from typing import Dict, Any, List

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'

def print_status(message: str):
    print(f"{Colors.GREEN}✓{Colors.ENDC} {message}")

def print_error(message: str):
    print(f"{Colors.RED}✗{Colors.ENDC} {message}")

def print_warning(message: str):
    print(f"{Colors.YELLOW}⚠{Colors.ENDC} {message}")

def print_info(message: str):
    print(f"{Colors.BLUE}ℹ{Colors.ENDC} {message}")

class TelemetryTester:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.data_dir = os.path.join(self.base_dir, "data")
        self.results = {
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "errors": []
        }

    def check_services_health(self) -> bool:
        """Check if telemetry services are running and healthy."""
        print_info("Checking telemetry services health...")
        
        services = {
            "OpenTelemetry Collector": "http://localhost:13133/",
            "Prometheus": "http://localhost:9090/-/healthy",
            "Grafana": "http://localhost:3000/api/health",
            "Jaeger": "http://localhost:16686/"
        }
        
        all_healthy = True
        for service, url in services.items():
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    print_status(f"{service} is healthy")
                else:
                    print_error(f"{service} returned status {response.status_code}")
                    all_healthy = False
            except requests.exceptions.RequestException as e:
                print_error(f"{service} is not responding: {e}")
                all_healthy = False
        
        return all_healthy

    def send_statsd_metrics(self) -> bool:
        """Send test metrics via StatsD."""
        print_info("Sending test metrics via StatsD...")
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # Sample Canary API metrics
            metrics = [
                "canary.requests:1|c|#endpoint:chirp,method:GET",
                "canary.requests:1|c|#endpoint:nest,method:POST",
                "canary.response_time:25|ms|#endpoint:chirp",
                "canary.response_time:45|ms|#endpoint:nest",
                "canary.request_size:512|g|#endpoint:nest",
                "canary.active_connections:8|g",
                "canary.cache_hits:1|c|#endpoint:chirp",
                "canary.cache_misses:1|c|#endpoint:flock",
                "canary.error_rate:0.02|g|#endpoint:chirp",
                "canary.websocket_connections:3|g"
            ]
            
            for metric in metrics:
                sock.sendto(metric.encode(), ('localhost', 8125))
                time.sleep(0.1)  # Small delay between metrics
            
            sock.close()
            print_status("Successfully sent StatsD metrics")
            return True
            
        except Exception as e:
            print_error(f"Failed to send StatsD metrics: {e}")
            return False

    def send_otlp_traces(self) -> bool:
        """Send test traces via OTLP HTTP."""
        print_info("Sending test traces via OTLP HTTP...")
        
        try:
            # Sample trace data in OTLP format
            trace_data = {
                "resourceSpans": [
                    {
                        "resource": {
                            "attributes": [
                                {"key": "service.name", "value": {"stringValue": "canary-api"}},
                                {"key": "service.version", "value": {"stringValue": "1.0.0"}},
                                {"key": "deployment.environment", "value": {"stringValue": "local-development"}}
                            ]
                        },
                        "scopeSpans": [
                            {
                                "scope": {
                                    "name": "canary-api-tracer",
                                    "version": "1.0.0"
                                },
                                "spans": [
                                    {
                                        "traceId": "12345678901234567890123456789012",
                                        "spanId": "1234567890123456",
                                        "name": "GET /chirp",
                                        "kind": 2,  # SPAN_KIND_SERVER
                                        "startTimeUnixNano": int(time.time() * 1_000_000_000),
                                        "endTimeUnixNano": int((time.time() + 0.025) * 1_000_000_000),
                                        "attributes": [
                                            {"key": "http.method", "value": {"stringValue": "GET"}},
                                            {"key": "http.path", "value": {"stringValue": "/chirp"}},
                                            {"key": "http.status_code", "value": {"intValue": "200"}}
                                        ],
                                        "status": {"code": 1}  # STATUS_CODE_OK
                                    },
                                    {
                                        "traceId": "12345678901234567890123456789012",
                                        "spanId": "2345678901234567",
                                        "parentSpanId": "1234567890123456",
                                        "name": "cache_lookup",
                                        "kind": 3,  # SPAN_KIND_CLIENT
                                        "startTimeUnixNano": int((time.time() + 0.001) * 1_000_000_000),
                                        "endTimeUnixNano": int((time.time() + 0.003) * 1_000_000_000),
                                        "attributes": [
                                            {"key": "cache.key", "value": {"stringValue": "chirp_data_v1"}},
                                            {"key": "cache.hit", "value": {"boolValue": True}},
                                            {"key": "cache.ttl", "value": {"intValue": "3600"}}
                                        ],
                                        "status": {"code": 1}
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'canary-api-telemetry-test/1.0'
            }
            
            response = requests.post(
                'http://localhost:4318/v1/traces',
                json=trace_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                print_status("Successfully sent OTLP traces")
                return True
            else:
                print_error(f"OTLP traces failed with status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            print_error(f"Failed to send OTLP traces: {e}")
            return False

    def send_otlp_metrics(self) -> bool:
        """Send test metrics via OTLP HTTP."""
        print_info("Sending test metrics via OTLP HTTP...")
        
        try:
            # Sample metrics data in OTLP format
            metrics_data = {
                "resourceMetrics": [
                    {
                        "resource": {
                            "attributes": [
                                {"key": "service.name", "value": {"stringValue": "canary-api"}},
                                {"key": "service.version", "value": {"stringValue": "1.0.0"}}
                            ]
                        },
                        "scopeMetrics": [
                            {
                                "scope": {
                                    "name": "canary-api-metrics",
                                    "version": "1.0.0"
                                },
                                "metrics": [
                                    {
                                        "name": "canary_requests_total",
                                        "description": "Total number of API requests",
                                        "unit": "1",
                                        "sum": {
                                            "dataPoints": [
                                                {
                                                    "attributes": [
                                                        {"key": "method", "value": {"stringValue": "GET"}},
                                                        {"key": "endpoint", "value": {"stringValue": "/chirp"}}
                                                    ],
                                                    "timeUnixNano": int(time.time() * 1_000_000_000),
                                                    "asInt": "156"
                                                }
                                            ],
                                            "aggregationTemporality": 2,  # CUMULATIVE
                                            "isMonotonic": True
                                        }
                                    },
                                    {
                                        "name": "canary_response_duration_seconds",
                                        "description": "API response time in seconds",
                                        "unit": "s",
                                        "histogram": {
                                            "dataPoints": [
                                                {
                                                    "attributes": [
                                                        {"key": "method", "value": {"stringValue": "GET"}},
                                                        {"key": "endpoint", "value": {"stringValue": "/chirp"}}
                                                    ],
                                                    "timeUnixNano": int(time.time() * 1_000_000_000),
                                                    "count": "15",
                                                    "sum": 0.3755,
                                                    "bucketCounts": ["2", "8", "12", "15", "15"],
                                                    "explicitBounds": [0.01, 0.025, 0.05, 0.1]
                                                }
                                            ],
                                            "aggregationTemporality": 2
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'canary-api-telemetry-test/1.0'
            }
            
            response = requests.post(
                'http://localhost:4318/v1/metrics',
                json=metrics_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                print_status("Successfully sent OTLP metrics")
                return True
            else:
                print_error(f"OTLP metrics failed with status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            print_error(f"Failed to send OTLP metrics: {e}")
            return False

    def verify_file_exports(self) -> bool:
        """Verify that telemetry data is being exported to files."""
        print_info("Verifying file exports...")
        
        # Wait a bit for data to be processed
        time.sleep(5)
        
        expected_files = [
            "traces/traces.jsonl",
            "metrics/metrics.jsonl",
            "logs/logs.jsonl"
        ]
        
        files_found = 0
        for file_path in expected_files:
            full_path = os.path.join(self.data_dir, file_path)
            if os.path.exists(full_path) and os.path.getsize(full_path) > 0:
                print_status(f"Found data in {file_path}")
                files_found += 1
            else:
                print_warning(f"No data found in {file_path}")
        
        if files_found > 0:
            print_status(f"Found data in {files_found}/{len(expected_files)} expected files")
            return True
        else:
            print_error("No telemetry data files found")
            return False

    def check_prometheus_metrics(self) -> bool:
        """Check if metrics are available in Prometheus."""
        print_info("Checking Prometheus metrics...")
        
        try:
            # Query for Canary API metrics
            response = requests.get(
                'http://localhost:9090/api/v1/query',
                params={'query': 'canary_requests_total'},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success' and data.get('data', {}).get('result'):
                    print_status("Found Canary API metrics in Prometheus")
                    return True
                else:
                    print_warning("No Canary API metrics found in Prometheus yet")
                    return False
            else:
                print_error(f"Prometheus query failed with status {response.status_code}")
                return False
                
        except Exception as e:
            print_error(f"Failed to query Prometheus: {e}")
            return False

    def run_test(self, test_name: str, test_func) -> bool:
        """Run a single test and track results."""
        self.results["tests_run"] += 1
        try:
            result = test_func()
            if result:
                self.results["tests_passed"] += 1
            else:
                self.results["tests_failed"] += 1
                self.results["errors"].append(f"{test_name}: Test returned False")
            return result
        except Exception as e:
            self.results["tests_failed"] += 1
            self.results["errors"].append(f"{test_name}: {str(e)}")
            print_error(f"Test {test_name} failed with exception: {e}")
            return False

    def run_all_tests(self):
        """Run all telemetry tests."""
        print(f"{Colors.BLUE}🧪 Canary API Telemetry Pipeline Test{Colors.ENDC}")
        print(f"Data directory: {self.data_dir}")
        print()
        
        # Check if services are healthy first
        if not self.run_test("Service Health Check", self.check_services_health):
            print_error("Services are not healthy. Please start the telemetry stack first.")
            print("Run: ./scripts/setup/start-telemetry-stack.sh")
            return False
        
        print()
        
        # Send test data
        self.run_test("StatsD Metrics", self.send_statsd_metrics)
        self.run_test("OTLP Traces", self.send_otlp_traces)
        self.run_test("OTLP Metrics", self.send_otlp_metrics)
        
        print()
        
        # Verify data processing
        self.run_test("File Exports", self.verify_file_exports)
        self.run_test("Prometheus Metrics", self.check_prometheus_metrics)
        
        # Print summary
        print()
        print(f"{Colors.BLUE}Test Summary:{Colors.ENDC}")
        print(f"Tests run: {self.results['tests_run']}")
        print(f"Tests passed: {Colors.GREEN}{self.results['tests_passed']}{Colors.ENDC}")
        print(f"Tests failed: {Colors.RED}{self.results['tests_failed']}{Colors.ENDC}")
        
        if self.results["errors"]:
            print(f"\n{Colors.RED}Errors:{Colors.ENDC}")
            for error in self.results["errors"]:
                print(f"  • {error}")
        
        success_rate = (self.results["tests_passed"] / self.results["tests_run"]) * 100
        if success_rate >= 80:
            print(f"\n{Colors.GREEN}🎉 Telemetry pipeline is working! ({success_rate:.1f}% success rate){Colors.ENDC}")
            return True
        else:
            print(f"\n{Colors.YELLOW}⚠ Telemetry pipeline needs attention ({success_rate:.1f}% success rate){Colors.ENDC}")
            return False

def main():
    """Main function."""
    tester = TelemetryTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
