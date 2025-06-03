# 🧪 Integration Testing Suite

A comprehensive testing framework for validating the distributed social media platform's functionality, performance, and observability.

## 📋 Prerequisites

1. **Running Services**: Ensure all services are running:
   ```bash
   cd examples/distributed/social-media
   docker-compose up -d
   ```

2. **Telemetry Stack**: The main telemetry stack must be running:
   ```bash
   # From project root
   ./scripts/setup/start-telemetry-stack.sh
   ```

3. **Python Environment**: Install test dependencies:
   ```bash
   cd tests
   pip install -r requirements.txt
   ```

## 🚀 Running Tests

### Run All Tests
```bash
pytest -v
```

### Run Specific Test Categories

**Integration Tests** (User flows, cross-service interactions):
```bash
pytest -v -m integration
```

**Observability Tests** (Trace validation, metrics):
```bash
pytest -v -m observability
```

**Chaos Tests** (Service failures, resilience):
```bash
pytest -v -m chaos
```

**Performance Tests** (Load testing, benchmarks):
```bash
pytest -v -m performance
```

### Run Specific Test Files
```bash
# User flow tests
pytest -v integration/test_user_flows.py

# Trace validation tests
pytest -v observability/test_traces.py

# Service failure tests
pytest -v chaos/test_service_failures.py
```

### Run Tests in Parallel
```bash
# Use -n flag with number of workers
pytest -v -n 4
```

### Skip Slow Tests
```bash
pytest -v -m "not slow"
```

## 📊 Test Reports

Test reports are automatically generated in the `reports/` directory after each test run.

### View Latest Report
```bash
ls -la reports/
cat reports/test_report_*.json | jq
```

## 🏗️ Test Structure

```
tests/
├── integration/          # Cross-service integration tests
│   ├── base.py          # Base test class with utilities
│   └── test_user_flows.py
├── observability/       # Telemetry validation tests
│   └── test_traces.py
├── chaos/              # Resilience and failure tests
│   └── test_service_failures.py
├── performance/        # Load and performance tests
├── utils/              # Test utilities
│   ├── service_clients.py  # Service API clients
│   └── trace_analyzer.py   # Jaeger trace analysis
└── conftest.py         # Pytest configuration
```

## 🎯 Test Categories

### Integration Tests
- **User Onboarding**: Registration → Profile creation → View profile
- **Social Interactions**: Follow/unfollow, view followers/following
- **Profile Search**: Search users by name
- **Concurrent Operations**: Multiple users performing actions
- **Authentication Flow**: Token validation across services
- **Cache Behavior**: Verify caching works correctly

### Observability Tests
- **Trace Propagation**: Verify traces span multiple services
- **Error Traces**: Ensure errors are properly recorded
- **Trace Isolation**: Concurrent requests maintain separate traces
- **Span Attributes**: Validate required span metadata
- **Timing Accuracy**: Verify trace timings are reasonable
- **Service Dependencies**: Validate service relationships

### Chaos Tests
- **Service Failures**: Test behavior when services go down
- **Database Failures**: Verify graceful degradation
- **Cache Failures**: Test fallback mechanisms
- **Partial Degradation**: System behavior under stress
- **Cascading Prevention**: Failures don't cascade
- **Recovery**: Services recover properly

## 🔍 Debugging Failed Tests

### View Trace in Jaeger
Failed tests will print Jaeger URLs. Open them to investigate:
```
🔍 View trace in Jaeger: http://localhost:16686/trace/{trace_id}
```

### Check Service Logs
```bash
docker-compose logs -f auth-service
docker-compose logs -f user-profile-service
```

### Verify Service Health
```bash
# Check if all containers are running
docker-compose ps

# Test service endpoints manually
curl http://localhost:8080/health
```

## 🛠️ Writing New Tests

### 1. Create Test Class
```python
from integration.base import IntegrationTestBase

@pytest.mark.integration
class TestNewFeature(IntegrationTestBase):
    @pytest.mark.asyncio
    async def test_my_feature(self):
        # Your test code here
        pass
```

### 2. Use Service Clients
```python
# Create user
user = await self.create_test_user("test_prefix")

# Use authenticated services
auth_services = self.services.with_token(user['token'])
profile = await auth_services.user.get_profile(user['id'])
```

### 3. Validate Traces
```python
trace_result = await self.wait_for_trace_and_validate(
    trace_id=user['trace_id'],
    expected_services=["auth-service", "user-profile-service"],
    expected_operations=["POST /register", "GET /{user_id}"]
)
self.assert_trace_valid(trace_result['validation'])
```

## 📈 Continuous Integration

### GitHub Actions Example
```yaml
- name: Start services
  run: docker-compose up -d
  
- name: Wait for services
  run: sleep 30
  
- name: Run integration tests
  run: |
    cd tests
    pytest -v -m integration --tb=short
    
- name: Upload test reports
  uses: actions/upload-artifact@v2
  with:
    name: test-reports
    path: tests/reports/
```

## 🐛 Common Issues

### Services Not Ready
If tests fail with connection errors:
```bash
# Wait longer for services to start
sleep 10
# Or check specific service health
docker-compose exec auth-service curl http://localhost:3001/health
```

### Missing Traces
If traces don't appear in Jaeger:
- Check OTEL collector is running: `curl http://localhost:13133/`
- Verify service configuration: `docker-compose exec auth-service env | grep OTEL`
- Wait longer for trace processing: Increase timeout in `wait_for_trace()`

### Database Migrations
If database errors occur:
```bash
# Run migrations manually
docker-compose exec auth-service npm run migrate
docker-compose exec user-profile-service python -m alembic upgrade head
```

## 📝 Test Best Practices

1. **Use Unique Test Data**: Include test ID in usernames to avoid conflicts
2. **Clean Up After Tests**: Use fixtures to ensure cleanup
3. **Wait for Async Operations**: Use proper await and timeouts
4. **Validate Both Success and Failure**: Test error cases too
5. **Check Traces**: Always validate distributed traces
6. **Use Meaningful Assertions**: Include helpful error messages

## 🎉 Success Metrics

A healthy test suite should achieve:
- ✅ 100% of integration tests passing
- ✅ All traces complete with no orphaned spans
- ✅ Services recover from chaos tests
- ✅ Response times within acceptable limits
- ✅ No flaky tests (consistent results)
