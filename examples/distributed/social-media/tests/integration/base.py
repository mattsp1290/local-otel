"""
Base test class for integration tests
"""

import asyncio
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

import pytest
import pytest_asyncio
from opentelemetry import trace
from opentelemetry.propagate import extract, inject

from ..utils import ServiceClients, TraceAnalyzer


class IntegrationTestBase:
    """Base class for integration tests with common utilities"""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_base(self, http_client, faker):
        """Set up base test requirements"""
        # Note: http_client is the actual client from the async fixture
        self.faker = faker
        self.trace_analyzer = TraceAnalyzer()
        
        # Service URLs - pointing directly to services since nginx isn't running
        self.auth_url = "http://localhost:3001/api/auth"
        self.user_url = "http://localhost:8000/api/users"
        self.feed_url = "http://localhost:8080/api/feed"
        
        # Create service clients
        self.services = ServiceClients(
            http_client=http_client,
            auth_url=self.auth_url,
            user_url=self.user_url,
            feed_url=self.feed_url
        )
        
        # Test metadata
        self.test_id = str(uuid.uuid4())
        self.test_start_time = datetime.utcnow()
        
    async def create_test_user(self, username_prefix: str = "test") -> Dict[str, Any]:
        """Create a test user with profile"""
        # Generate unique user data
        username = f"{username_prefix}_{self.faker.user_name()}_{self.test_id[:8]}"
        email = f"{username}@test.com"
        password = "TestPassword123!"
        
        # Register user
        with trace.get_tracer(__name__).start_as_current_span("create_test_user") as span:
            span.set_attribute("test.id", self.test_id)
            span.set_attribute("user.username", username)
            
            # Register (service clients handle trace propagation internally)
            registration = await self.services.auth.register(email, username, password)
            user_id = registration["user"]["id"]
            token = registration["token"]
            
            # Create authenticated clients
            auth_services = self.services.with_token(token)
            
            # Create profile
            profile_data = await auth_services.user.create_or_update_profile(
                user_id=user_id,
                display_name=self.faker.name(),
                bio=self.faker.text(max_nb_chars=200),
                avatar_url=f"https://ui-avatars.com/api/?name={username}"
            )
            
            # Store trace ID for analysis
            trace_id = format(span.get_span_context().trace_id, '032x')
            
            return {
                "id": user_id,
                "email": email,
                "username": username,
                "password": password,
                "token": token,
                "profile": profile_data,
                "trace_id": trace_id
            }
    
    async def create_user_relationship(
        self, 
        follower_token: str,
        following_id: str
    ) -> Dict[str, Any]:
        """Create a follow relationship between users"""
        auth_services = self.services.with_token(follower_token)
        
        with trace.get_tracer(__name__).start_as_current_span("create_relationship") as span:
            span.set_attribute("test.id", self.test_id)
            span.set_attribute("following.id", following_id)
            
            result = await auth_services.user.follow_user(following_id)
            
            trace_id = format(span.get_span_context().trace_id, '032x')
            result["trace_id"] = trace_id
            
            return result
    
    async def wait_for_trace_and_validate(
        self,
        trace_id: str,
        expected_services: list[str],
        expected_operations: Optional[list[str]] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """Wait for trace to appear and validate it"""
        # Wait for trace to be available
        trace = await self.trace_analyzer.wait_for_trace(trace_id, timeout=timeout)
        
        if not trace:
            pytest.fail(f"Trace {trace_id} not found in Jaeger after {timeout}s")
        
        # Analyze trace
        analysis = self.trace_analyzer.analyze_trace_structure(trace)
        
        # Validate completeness
        validation = self.trace_analyzer.validate_trace_completeness(
            trace,
            expected_services,
            expected_operations
        )
        
        # Calculate service latencies
        latencies = self.trace_analyzer.calculate_service_latencies(trace)
        
        return {
            "trace": trace,
            "analysis": analysis,
            "validation": validation,
            "latencies": latencies
        }
    
    def assert_trace_valid(self, validation_result: Dict[str, Any]):
        """Assert that trace validation passed"""
        if not validation_result["is_complete"]:
            error_messages = []
            
            if validation_result["missing_services"]:
                error_messages.append(
                    f"Missing services: {validation_result['missing_services']}"
                )
            
            if validation_result["missing_operations"]:
                error_messages.append(
                    f"Missing operations: {validation_result['missing_operations']}"
                )
            
            if validation_result["unexpected_errors"]:
                error_messages.append(
                    f"Unexpected errors: {validation_result['unexpected_errors']}"
                )
            
            pytest.fail("\n".join(error_messages))
    
    def assert_latency_within_limits(
        self,
        latencies: Dict[str, Dict[str, float]],
        service: str,
        max_avg_latency_ms: float
    ):
        """Assert that service latency is within acceptable limits"""
        if service not in latencies:
            pytest.fail(f"Service {service} not found in trace")
        
        avg_latency_us = latencies[service]["avg_duration_us"]
        avg_latency_ms = avg_latency_us / 1000
        
        assert avg_latency_ms <= max_avg_latency_ms, (
            f"Service {service} average latency {avg_latency_ms:.2f}ms "
            f"exceeds limit of {max_avg_latency_ms}ms"
        )
    
    async def cleanup_test_data(self):
        """Clean up test data after test completion"""
        # This would normally clean up test data from databases
        # For now, it's a placeholder
        pass
    
    def generate_test_post_content(self) -> str:
        """Generate test post content"""
        return self.faker.text(max_nb_chars=280)  # Twitter-like length
    
    def log_trace_url(self, trace_id: str):
        """Log Jaeger URL for trace"""
        jaeger_url = f"http://localhost:16686/trace/{trace_id}"
        print(f"\n🔍 View trace in Jaeger: {jaeger_url}")
