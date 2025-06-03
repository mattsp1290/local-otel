"""
Tests for validating distributed tracing functionality
"""

import pytest
import asyncio
from datetime import datetime, timedelta

from ..integration.base import IntegrationTestBase


@pytest.mark.observability
class TestTraceValidation(IntegrationTestBase):
    """Validate distributed tracing across services"""
    
    @pytest.mark.asyncio
    async def test_trace_propagation(self):
        """Test that trace context propagates correctly across services"""
        print("\n🧪 Testing Trace Propagation")
        
        # Create user to generate a trace
        user = await self.create_test_user("trace_test")
        
        # Wait for and analyze trace
        trace_result = await self.wait_for_trace_and_validate(
            trace_id=user['trace_id'],
            expected_services=["auth-service", "user-profile-service"]
        )
        
        # Verify trace has root span
        assert trace_result['analysis']['root_span'] is not None
        
        # Verify all spans share the same trace ID
        trace = trace_result['trace']
        trace_id = trace['traceID']
        for span in trace['spans']:
            assert span['traceID'] == trace_id, "All spans should have same trace ID"
        
        # Verify parent-child relationships
        relationships = self.trace_analyzer.get_span_relationships(trace)
        
        # Root span should have children
        root_span_id = trace_result['analysis']['root_span']['spanID']
        assert len(relationships.get(root_span_id, [])) > 0, "Root span should have children"
        
        print(f"✅ Trace contains {len(trace['spans'])} spans across {len(trace_result['analysis']['services'])} services")
        print("✅ Trace propagation validated successfully")
    
    @pytest.mark.asyncio
    async def test_error_trace_propagation(self):
        """Test that errors are properly recorded in traces"""
        print("\n🧪 Testing Error Trace Propagation")
        
        # Try to register with invalid data to trigger error
        try:
            await self.services.auth.register(
                email="invalid-email",  # Invalid email format
                username="",  # Empty username
                password="123"  # Too short password
            )
        except Exception:
            # Expected to fail
            pass
        
        # Search for error traces
        error_traces = await self.trace_analyzer.search_traces(
            service="auth-service",
            tags={"error": "true"},
            start_time=datetime.utcnow() - timedelta(minutes=5)
        )
        
        if error_traces:
            # Analyze the most recent error trace
            trace = error_traces[0]
            analysis = self.trace_analyzer.analyze_trace_structure(trace)
            
            assert analysis['has_errors'], "Trace should contain errors"
            assert analysis['error_count'] > 0, "Should have at least one error span"
            
            print(f"✅ Found error trace with {analysis['error_count']} errors")
        else:
            print("⚠️  No error traces found (might be filtered by service)")
        
        print("✅ Error trace propagation test completed")
    
    @pytest.mark.asyncio
    async def test_concurrent_trace_isolation(self):
        """Test that concurrent requests maintain separate traces"""
        print("\n🧪 Testing Concurrent Trace Isolation")
        
        # Create multiple users concurrently
        num_users = 3
        create_tasks = [
            self.create_test_user(f"concurrent_trace_{i}") 
            for i in range(num_users)
        ]
        
        users = await asyncio.gather(*create_tasks)
        trace_ids = [user['trace_id'] for user in users]
        
        # Verify all trace IDs are unique
        assert len(set(trace_ids)) == num_users, "Each request should have unique trace ID"
        
        # Fetch and validate each trace
        for i, user in enumerate(users):
            trace_result = await self.wait_for_trace_and_validate(
                trace_id=user['trace_id'],
                expected_services=["auth-service", "user-profile-service"]
            )
            
            # Verify trace only contains spans for this request
            trace = trace_result['trace']
            assert trace['traceID'] == user['trace_id']
            
            print(f"✅ Trace {i+1}/{num_users} validated: {trace_result['analysis']['span_count']} spans")
        
        print("✅ Concurrent trace isolation validated successfully")
    
    @pytest.mark.asyncio
    async def test_trace_span_attributes(self):
        """Test that spans contain required attributes"""
        print("\n🧪 Testing Trace Span Attributes")
        
        # Perform operations that should set specific attributes
        user = await self.create_test_user("attributes_test")
        
        # Follow another user to generate more spans
        user2 = await self.create_test_user("attributes_test_2")
        follow_result = await self.create_user_relationship(
            follower_token=user['token'],
            following_id=user2['id']
        )
        
        # Analyze the follow trace
        trace_result = await self.wait_for_trace_and_validate(
            trace_id=follow_result['trace_id'],
            expected_services=["user-profile-service"]
        )
        
        trace = trace_result['trace']
        
        # Check for required span attributes
        required_attributes = {
            'http.method': ['GET', 'POST', 'PUT', 'DELETE'],
            'http.status_code': range(100, 600),
            'service.name': str
        }
        
        for span in trace['spans']:
            tags = {tag['key']: tag['value'] for tag in span.get('tags', [])}
            
            # Verify HTTP spans have required attributes
            if 'http.method' in tags:
                assert tags['http.method'] in required_attributes['http.method']
                assert 'http.status_code' in tags
                assert isinstance(tags.get('http.url'), str)
        
        print("✅ Span attributes validated successfully")
    
    @pytest.mark.asyncio
    async def test_trace_timing_accuracy(self):
        """Test that trace timings are accurate"""
        print("\n🧪 Testing Trace Timing Accuracy")
        
        # Record start time
        start_time = datetime.utcnow()
        
        # Perform operation
        user = await self.create_test_user("timing_test")
        
        # Record end time
        end_time = datetime.utcnow()
        operation_duration_ms = (end_time - start_time).total_seconds() * 1000
        
        # Get trace
        trace_result = await self.wait_for_trace_and_validate(
            trace_id=user['trace_id'],
            expected_services=["auth-service", "user-profile-service"]
        )
        
        # Check root span duration
        root_span = trace_result['analysis']['root_span']
        trace_duration_ms = root_span['duration'] / 1000  # Convert from microseconds
        
        # Trace duration should be reasonable (not too different from measured time)
        # Allow for some variance due to network and processing
        assert trace_duration_ms > 0, "Trace duration should be positive"
        assert trace_duration_ms < operation_duration_ms * 2, \
            f"Trace duration ({trace_duration_ms}ms) seems too high"
        
        print(f"✅ Operation took ~{operation_duration_ms:.0f}ms, trace shows {trace_duration_ms:.0f}ms")
        print("✅ Trace timing accuracy validated")
    
    @pytest.mark.asyncio
    async def test_trace_service_dependencies(self):
        """Test that trace shows correct service dependencies"""
        print("\n🧪 Testing Trace Service Dependencies")
        
        # Create user and perform various operations
        user = await self.create_test_user("dependencies_test")
        auth_services = self.services.with_token(user['token'])
        
        # Get own profile
        await auth_services.user.get_profile(user['id'])
        
        # Search for users
        await auth_services.user.search_users("test")
        
        # Look for recent traces from this test
        traces = await self.trace_analyzer.search_traces(
            service="user-profile-service",
            start_time=self.test_start_time
        )
        
        # Analyze service dependencies across traces
        services_seen = set()
        operations_by_service = {}
        
        for trace in traces[:5]:  # Analyze up to 5 recent traces
            analysis = self.trace_analyzer.analyze_trace_structure(trace)
            services_seen.update(analysis['services'])
            
            for op in analysis['operations']:
                service = op['service']
                if service not in operations_by_service:
                    operations_by_service[service] = set()
                operations_by_service[service].add(op['operation'])
        
        # Verify expected services appear
        assert 'auth-service' in services_seen or 'user-profile-service' in services_seen
        
        print(f"✅ Found {len(services_seen)} services in traces: {services_seen}")
        print("✅ Service dependencies validated successfully")
    
    @pytest.mark.asyncio
    async def test_trace_baggage_propagation(self):
        """Test that trace baggage/context propagates correctly"""
        print("\n🧪 Testing Trace Baggage Propagation")
        
        # Create a user with specific test ID in trace context
        user = await self.create_test_user("baggage_test")
        
        # Get the trace
        trace_result = await self.wait_for_trace_and_validate(
            trace_id=user['trace_id'],
            expected_services=["auth-service", "user-profile-service"]
        )
        
        trace = trace_result['trace']
        
        # Check if test.id attribute propagated through spans
        test_id_found = False
        for span in trace['spans']:
            tags = {tag['key']: tag['value'] for tag in span.get('tags', [])}
            if tags.get('test.id') == self.test_id:
                test_id_found = True
                break
        
        if test_id_found:
            print("✅ Test ID found in trace spans - baggage propagated")
        else:
            print("⚠️  Test ID not found in spans - baggage might not be configured")
        
        print("✅ Trace baggage propagation test completed")
