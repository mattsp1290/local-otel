"""
Pytest configuration and shared fixtures for integration tests
"""

import os
import sys
import asyncio
import json
import time
from typing import Dict, Any, Generator
from datetime import datetime
from pathlib import Path

import pytest
import pytest_asyncio
import httpx
import docker
from faker import Faker
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter
)

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure OpenTelemetry for tests
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer("integration-tests")

# Test configuration
TEST_TIMEOUT = 30  # seconds
JAEGER_URL = os.getenv("JAEGER_URL", "http://localhost:16686")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")

# Service URLs - pointing directly to services since nginx isn't running
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:3001/api/auth")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:8000/api/users")
FEED_SERVICE_URL = os.getenv("FEED_SERVICE_URL", "http://localhost:8080/api/feed")


@pytest.fixture(scope="session")
def docker_client():
    """Docker client for managing containers"""
    return docker.from_env()


@pytest.fixture(scope="session")
def faker():
    """Faker instance for generating test data"""
    return Faker()


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment(docker_client):
    """Ensure all services are running before tests"""
    print("\n🚀 Setting up test environment...")
    
    # Check if services are running (excluding nginx since it needs feed-service)
    required_containers = [
        "social-media-auth-service-1",
        "social-media-user-profile-service-1",
        "social-media-auth-db-1",
        "social-media-user-db-1",
        "social-media-auth-redis-1",
        "social-media-profile-redis-1"
    ]
    
    running_containers = {c.name for c in docker_client.containers.list()}
    missing = [c for c in required_containers if c not in running_containers]
    
    if missing:
        print(f"⚠️  Missing containers: {missing}")
        print("Please run 'docker-compose up -d' from the social-media directory")
        pytest.exit("Required services not running", 1)
    
    # Wait for services to be healthy
    print("⏳ Waiting for services to be ready...")
    time.sleep(5)  # Give services time to fully initialize
    
    yield
    
    print("\n🧹 Cleaning up test environment...")


@pytest_asyncio.fixture
async def http_client():
    """Async HTTP client with tracing enabled"""
    async with httpx.AsyncClient(timeout=TEST_TIMEOUT) as client:
        yield client


@pytest.fixture
def trace_headers():
    """Generate trace headers for distributed tracing"""
    with tracer.start_as_current_span("test-request") as span:
        trace_id = format(span.get_span_context().trace_id, '032x')
        span_id = format(span.get_span_context().span_id, '016x')
        
        return {
            'traceparent': f'00-{trace_id}-{span_id}-01',
            'X-Request-ID': trace_id[:8]  # Short ID for logging
        }


@pytest_asyncio.fixture
async def test_user(faker, http_client, trace_headers):
    """Create a test user for tests"""
    user_data = {
        "email": faker.email(),
        "username": faker.user_name(),
        "password": "TestPassword123!"
    }
    
    # Register user
    response = await http_client.post(
        f"{AUTH_SERVICE_URL}/register",
        json=user_data,
        headers=trace_headers
    )
    
    if response.status_code != 201:
        pytest.fail(f"Failed to create test user: {response.text}")
    
    user_response = response.json()
    
    # Return user data with token
    return {
        **user_data,
        "id": user_response["user"]["id"],
        "token": user_response["token"]
    }


@pytest_asyncio.fixture
async def authenticated_client(http_client, test_user):
    """HTTP client with authentication headers"""
    http_client.headers.update({
        "Authorization": f"Bearer {test_user['token']}"
    })
    yield http_client


@pytest.fixture
def test_transaction_id(faker):
    """Generate unique transaction ID for test tracking"""
    return f"test-{faker.uuid4()}"


# Markers for test categorization
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "chaos: mark test as chaos engineering test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance test"
    )
    config.addinivalue_line(
        "markers", "observability: mark test as observability validation"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


# Test report generation
def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Generate test summary report"""
    print("\n" + "="*80)
    print("📊 Test Execution Summary")
    print("="*80)
    
    stats = terminalreporter.stats
    
    # Calculate statistics
    passed = len(stats.get('passed', []))
    failed = len(stats.get('failed', []))
    skipped = len(stats.get('skipped', []))
    total = passed + failed + skipped
    
    if total > 0:
        pass_rate = (passed / total) * 100
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⏭️  Skipped: {skipped}")
        print(f"📈 Pass Rate: {pass_rate:.1f}%")
    
    # Save report
    report_path = Path("reports") / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "total": total,
        "pass_rate": pass_rate if total > 0 else 0
    }
    
    report_path.parent.mkdir(exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    print(f"\n📄 Report saved to: {report_path}")
