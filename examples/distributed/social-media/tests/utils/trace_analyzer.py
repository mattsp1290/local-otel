"""
Trace analyzer for fetching and validating distributed traces from Jaeger
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential


class TraceAnalyzer:
    """Analyze distributed traces from Jaeger"""
    
    def __init__(self, jaeger_url: str = "http://localhost:16686"):
        self.jaeger_url = jaeger_url
        self.api_url = f"{jaeger_url}/api"
        
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a trace by ID from Jaeger"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/traces/{trace_id}"
            )
            
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            data = response.json()
            
            if data.get('data') and len(data['data']) > 0:
                return data['data'][0]
            return None
    
    async def wait_for_trace(
        self, 
        trace_id: str, 
        timeout: int = 30,
        poll_interval: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """Wait for a trace to appear in Jaeger"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            trace = await self.get_trace(trace_id)
            if trace:
                return trace
            await asyncio.sleep(poll_interval)
        
        return None
    
    async def search_traces(
        self,
        service: str,
        operation: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search for traces matching criteria"""
        # Default to last hour if no time range specified
        if not end_time:
            end_time = datetime.utcnow()
        if not start_time:
            start_time = end_time - timedelta(hours=1)
        
        params = {
            "service": service,
            "limit": limit,
            "start": int(start_time.timestamp() * 1_000_000),  # microseconds
            "end": int(end_time.timestamp() * 1_000_000)
        }
        
        if operation:
            params["operation"] = operation
        
        if tags:
            params["tags"] = "&".join([f"{k}={v}" for k, v in tags.items()])
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_url}/traces",
                params=params
            )
            response.raise_for_status()
            data = response.json()
            return data.get('data', [])
    
    def analyze_trace_structure(self, trace: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the structure of a trace"""
        spans = trace.get('spans', [])
        processes = trace.get('processes', {})
        
        # Build span tree
        span_map = {span['spanID']: span for span in spans}
        root_spans = []
        
        for span in spans:
            if not span.get('references'):
                root_spans.append(span)
            else:
                # Find parent references
                for ref in span['references']:
                    if ref['refType'] == 'CHILD_OF':
                        parent_id = ref['spanID']
                        if parent_id in span_map:
                            parent = span_map[parent_id]
                            if 'children' not in parent:
                                parent['children'] = []
                            parent['children'].append(span)
        
        # Calculate statistics
        services_involved = set()
        operations = []
        total_duration = 0
        error_count = 0
        
        for span in spans:
            process = processes.get(span['processID'], {})
            service_name = process.get('serviceName', 'unknown')
            services_involved.add(service_name)
            
            operations.append({
                'service': service_name,
                'operation': span['operationName'],
                'duration': span['duration'],
                'start_time': span['startTime']
            })
            
            # Check for errors
            for tag in span.get('tags', []):
                if tag['key'] == 'error' and tag['value']:
                    error_count += 1
                    break
        
        # Find critical path (longest duration path from root to leaf)
        critical_path = self._find_critical_path(root_spans[0] if root_spans else None)
        
        return {
            'trace_id': trace['traceID'],
            'services': list(services_involved),
            'service_count': len(services_involved),
            'span_count': len(spans),
            'total_duration_us': root_spans[0]['duration'] if root_spans else 0,
            'error_count': error_count,
            'has_errors': error_count > 0,
            'root_span': root_spans[0] if root_spans else None,
            'operations': operations,
            'critical_path': critical_path
        }
    
    def _find_critical_path(self, span: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find the critical path (longest duration) through the trace"""
        if not span:
            return []
        
        path = [{
            'operation': span['operationName'],
            'duration': span['duration'],
            'service': span.get('process', {}).get('serviceName', 'unknown')
        }]
        
        if 'children' in span:
            # Find child with longest end time
            longest_child = None
            longest_end_time = 0
            
            for child in span['children']:
                child_end = child['startTime'] + child['duration']
                if child_end > longest_end_time:
                    longest_end_time = child_end
                    longest_child = child
            
            if longest_child:
                path.extend(self._find_critical_path(longest_child))
        
        return path
    
    def validate_trace_completeness(
        self, 
        trace: Dict[str, Any],
        expected_services: List[str],
        expected_operations: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Validate that a trace contains expected services and operations"""
        analysis = self.analyze_trace_structure(trace)
        
        validation_result = {
            'is_complete': True,
            'missing_services': [],
            'missing_operations': [],
            'unexpected_errors': [],
            'warnings': []
        }
        
        # Check for expected services
        actual_services = set(analysis['services'])
        expected_services_set = set(expected_services)
        missing_services = expected_services_set - actual_services
        
        if missing_services:
            validation_result['is_complete'] = False
            validation_result['missing_services'] = list(missing_services)
        
        # Check for expected operations if provided
        if expected_operations:
            actual_operations = {op['operation'] for op in analysis['operations']}
            expected_operations_set = set(expected_operations)
            missing_operations = expected_operations_set - actual_operations
            
            if missing_operations:
                validation_result['is_complete'] = False
                validation_result['missing_operations'] = list(missing_operations)
        
        # Check for errors
        if analysis['has_errors']:
            validation_result['unexpected_errors'].append(
                f"Trace contains {analysis['error_count']} error(s)"
            )
        
        # Check for orphaned spans
        spans = trace.get('spans', [])
        for span in spans:
            if span.get('warnings'):
                validation_result['warnings'].extend(span['warnings'])
        
        return validation_result
    
    def get_span_relationships(self, trace: Dict[str, Any]) -> Dict[str, List[str]]:
        """Get parent-child relationships between spans"""
        relationships = {}
        spans = trace.get('spans', [])
        
        for span in spans:
            span_id = span['spanID']
            relationships[span_id] = []
            
            # Find children
            for other_span in spans:
                if other_span['spanID'] != span_id:
                    for ref in other_span.get('references', []):
                        if ref['refType'] == 'CHILD_OF' and ref['spanID'] == span_id:
                            relationships[span_id].append(other_span['spanID'])
        
        return relationships
    
    def calculate_service_latencies(self, trace: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
        """Calculate latencies for each service in the trace"""
        spans = trace.get('spans', [])
        processes = trace.get('processes', {})
        
        service_latencies = {}
        
        for span in spans:
            process = processes.get(span['processID'], {})
            service_name = process.get('serviceName', 'unknown')
            
            if service_name not in service_latencies:
                service_latencies[service_name] = {
                    'total_duration_us': 0,
                    'span_count': 0,
                    'operations': {}
                }
            
            service_latencies[service_name]['total_duration_us'] += span['duration']
            service_latencies[service_name]['span_count'] += 1
            
            operation = span['operationName']
            if operation not in service_latencies[service_name]['operations']:
                service_latencies[service_name]['operations'][operation] = {
                    'count': 0,
                    'total_duration_us': 0
                }
            
            service_latencies[service_name]['operations'][operation]['count'] += 1
            service_latencies[service_name]['operations'][operation]['total_duration_us'] += span['duration']
        
        # Calculate averages
        for service in service_latencies.values():
            service['avg_duration_us'] = service['total_duration_us'] / service['span_count']
            
            for operation in service['operations'].values():
                operation['avg_duration_us'] = operation['total_duration_us'] / operation['count']
        
        return service_latencies
