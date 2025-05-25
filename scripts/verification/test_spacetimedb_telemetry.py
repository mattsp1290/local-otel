#!/usr/bin/env python3
"""
SpacetimeDB Telemetry Integration Test
Validates that SpacetimeDB is correctly emitting telemetry data
"""

import json
import os
import sys
from pathlib import Path

# Get the data directory path
DATA_DIR = Path(__file__).parent.parent.parent / "data"

def test_traces():
    """Verify SpacetimeDB traces are properly formatted"""
    trace_file = DATA_DIR / "traces" / "traces.jsonl"
    
    if not trace_file.exists():
        return False, "Trace file not found"
    
    try:
        with open(trace_file, 'r') as f:
            trace_data = json.loads(f.readline())
        
        # Check for SpacetimeDB service
        resource = trace_data['resourceSpans'][0]['resource']
        service_name = next(attr['value']['stringValue'] for attr in resource['attributes'] 
                           if attr['key'] == 'service.name')
        
        if service_name != 'spacetimedb':
            return False, f"Expected service.name 'spacetimedb', got '{service_name}'"
        
        # Check for database operations
        spans = trace_data['resourceSpans'][0]['scopeSpans'][0]['spans']
        db_operations = [s for s in spans if s['name'].startswith('database.')]
        
        if not db_operations:
            return False, "No database operation spans found"
        
        return True, f"Found {len(db_operations)} database operation spans"
        
    except Exception as e:
        return False, f"Error parsing traces: {str(e)}"

def test_metrics():
    """Verify SpacetimeDB metrics are being collected"""
    metrics_file = DATA_DIR / "metrics" / "metrics.prom"
    
    if not metrics_file.exists():
        return False, "Metrics file not found"
    
    try:
        with open(metrics_file, 'r') as f:
            metrics_data = f.read()
        
        # Check for SpacetimeDB metrics
        required_metrics = [
            'spacetimedb_database_operations_total',
            'spacetimedb_wasm_execution_duration_seconds'
        ]
        
        missing_metrics = []
        for metric in required_metrics:
            if metric not in metrics_data:
                missing_metrics.append(metric)
        
        if missing_metrics:
            return False, f"Missing metrics: {', '.join(missing_metrics)}"
        
        # Count metric lines
        metric_lines = [line for line in metrics_data.split('\n') 
                       if line and not line.startswith('#')]
        
        return True, f"Found {len(metric_lines)} metric data points"
        
    except Exception as e:
        return False, f"Error parsing metrics: {str(e)}"

def test_logs():
    """Verify SpacetimeDB logs are structured correctly"""
    log_file = DATA_DIR / "logs" / "spacetimedb-test-logs.jsonl"
    
    if not log_file.exists():
        return False, "Log file not found"
    
    try:
        log_count = 0
        spacetimedb_logs = 0
        
        with open(log_file, 'r') as f:
            for line in f:
                log_count += 1
                log_entry = json.loads(line)
                
                # Verify required fields
                required_fields = ['timestamp', 'level', 'service', 'message']
                for field in required_fields:
                    if field not in log_entry:
                        return False, f"Missing required field: {field}"
                
                # Count SpacetimeDB logs
                if log_entry.get('service') == 'spacetimedb':
                    spacetimedb_logs += 1
        
        if spacetimedb_logs == 0:
            return False, "No SpacetimeDB logs found"
        
        return True, f"Found {spacetimedb_logs}/{log_count} SpacetimeDB log entries"
        
    except Exception as e:
        return False, f"Error parsing logs: {str(e)}"

def test_processed_logs():
    """Verify Filebeat is processing logs correctly"""
    processed_file = DATA_DIR / "processed" / "filebeat-processed-logs.jsonl"
    
    if not processed_file.exists():
        return False, "Processed log file not found"
    
    try:
        with open(processed_file, 'r') as f:
            first_line = f.readline()
            if not first_line:
                return False, "Processed log file is empty"
            
            log_entry = json.loads(first_line)
            
            # Check for Filebeat enrichment
            if 'agent.type' not in log_entry:
                return False, "Missing Filebeat agent metadata"
            
            if log_entry.get('agent.type') != 'filebeat':
                return False, "Incorrect agent type"
            
        return True, "Filebeat processing is working correctly"
        
    except Exception as e:
        return False, f"Error parsing processed logs: {str(e)}"

def main():
    """Run all integration tests"""
    print("🧪 SpacetimeDB Telemetry Integration Test")
    print("=" * 50)
    
    tests = [
        ("Traces", test_traces),
        ("Metrics", test_metrics),
        ("Logs", test_logs),
        ("Processed Logs", test_processed_logs)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        success, message = test_func()
        
        if success:
            print(f"✅ {test_name}: {message}")
            passed += 1
        else:
            print(f"❌ {test_name}: {message}")
            failed += 1
    
    print("=" * 50)
    print(f"Tests Passed: {passed}/{len(tests)}")
    
    if failed > 0:
        print(f"⚠️  {failed} tests failed")
        sys.exit(1)
    else:
        print("🎉 All tests passed! SpacetimeDB telemetry is working correctly.")
        sys.exit(0)

if __name__ == "__main__":
    main()
