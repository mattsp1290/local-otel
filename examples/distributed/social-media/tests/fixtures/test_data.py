"""
Test data fixtures for integration tests
"""

# Sample user data for testing
TEST_USERS = [
    {
        "username": "alice_test",
        "email": "alice@test.com",
        "password": "TestPassword123!",
        "display_name": "Alice Test",
        "bio": "Test user Alice - loves testing distributed systems"
    },
    {
        "username": "bob_test",
        "email": "bob@test.com", 
        "password": "TestPassword123!",
        "display_name": "Bob Test",
        "bio": "Test user Bob - enthusiastic about observability"
    },
    {
        "username": "charlie_test",
        "email": "charlie@test.com",
        "password": "TestPassword123!",
        "display_name": "Charlie Test", 
        "bio": "Test user Charlie - chaos engineering expert"
    }
]

# Sample post content for testing
TEST_POSTS = [
    "Just deployed a new microservice! 🚀 #distributed #testing",
    "Distributed tracing is amazing for debugging! 🔍 #observability",
    "Running chaos tests in production... what could go wrong? 😅 #chaos",
    "Cache invalidation is one of the hardest problems in computer science",
    "Today I learned about OpenTelemetry and it's a game changer! #otel"
]

# Expected service names in traces
EXPECTED_SERVICES = {
    "auth": "auth-service",
    "profile": "user-profile-service",
    "feed": "feed-service",
    "nginx": "nginx"
}

# Performance benchmarks (in milliseconds)
PERFORMANCE_LIMITS = {
    "auth_service": {
        "register": 500,
        "login": 200,
        "validate_token": 50
    },
    "profile_service": {
        "get_profile": 100,
        "update_profile": 200,
        "follow_user": 150,
        "search_users": 300
    },
    "feed_service": {
        "create_post": 200,
        "get_timeline": 500,
        "like_post": 100
    }
}

# Error scenarios for chaos testing
ERROR_SCENARIOS = [
    {
        "name": "invalid_email",
        "data": {"email": "notanemail", "username": "test", "password": "Test123!"},
        "expected_error": "Invalid email format"
    },
    {
        "name": "short_password",
        "data": {"email": "test@test.com", "username": "test", "password": "123"},
        "expected_error": "Password too short"
    },
    {
        "name": "empty_username",
        "data": {"email": "test@test.com", "username": "", "password": "Test123!"},
        "expected_error": "Username required"
    }
]
