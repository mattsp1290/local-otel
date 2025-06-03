#!/bin/bash

# Test script for Feed Service endpoints
# This script tests all the endpoints of the Feed Service

BASE_URL=${BASE_URL:-"http://localhost:8080"}
USER_ID=${USER_ID:-"test_user_123"}

echo "Testing Feed Service endpoints at $BASE_URL"
echo "Using User ID: $USER_ID"
echo "========================================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to test an endpoint
test_endpoint() {
    local method=$1
    local endpoint=$2
    local description=$3
    local data=$4
    local expected_status=$5
    
    echo -n "Testing: $description... "
    
    if [ "$method" == "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" -X GET \
            -H "X-User-ID: $USER_ID" \
            "$BASE_URL$endpoint")
    elif [ "$method" == "POST" ]; then
        response=$(curl -s -w "\n%{http_code}" -X POST \
            -H "X-User-ID: $USER_ID" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$BASE_URL$endpoint")
    elif [ "$method" == "DELETE" ]; then
        response=$(curl -s -w "\n%{http_code}" -X DELETE \
            -H "X-User-ID: $USER_ID" \
            "$BASE_URL$endpoint")
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" == "$expected_status" ]; then
        echo -e "${GREEN}✓${NC} (Status: $http_code)"
        if [ ! -z "$body" ] && [ "$body" != "null" ]; then
            echo "  Response: $body" | head -n 3
        fi
    else
        echo -e "${RED}✗${NC} (Expected: $expected_status, Got: $http_code)"
        if [ ! -z "$body" ]; then
            echo "  Error: $body" | head -n 3
        fi
    fi
    echo
}

# 1. Test Health Check
test_endpoint "GET" "/health" "Health Check" "" "200"

# 2. Create a test post
echo "Creating a test post..."
create_response=$(curl -s -X POST \
    -H "X-User-ID: $USER_ID" \
    -H "Content-Type: application/json" \
    -d '{"content":"This is a test post from the Feed Service!"}' \
    "$BASE_URL/api/posts")

POST_ID=$(echo $create_response | grep -o '"id":"[^"]*' | grep -o '[^"]*$')
echo "Created post with ID: $POST_ID"
echo

# 3. Test Create Post
test_endpoint "POST" "/api/posts" \
    "Create Post" \
    '{"content":"Another test post with emojis! 🚀"}' \
    "201"

# 4. Test Get Post
if [ ! -z "$POST_ID" ]; then
    test_endpoint "GET" "/api/posts/$POST_ID" \
        "Get Post by ID" \
        "" \
        "200"
fi

# 5. Test Get User Posts
test_endpoint "GET" "/api/posts/user/$USER_ID?page=1" \
    "Get User Posts" \
    "" \
    "200"

# 6. Test Timeline
test_endpoint "GET" "/api/timeline/$USER_ID?page=1" \
    "Get User Timeline" \
    "" \
    "200"

# 7. Test Like Post
if [ ! -z "$POST_ID" ]; then
    test_endpoint "POST" "/api/posts/$POST_ID/like" \
        "Like Post" \
        "" \
        "200"
fi

# 8. Test Add Comment
if [ ! -z "$POST_ID" ]; then
    test_endpoint "POST" "/api/posts/$POST_ID/comment" \
        "Add Comment" \
        '{"content":"Great post! 👍"}' \
        "201"
fi

# 9. Test Get Comments
if [ ! -z "$POST_ID" ]; then
    test_endpoint "GET" "/api/posts/$POST_ID/comments?page=1" \
        "Get Comments" \
        "" \
        "200"
fi

# 10. Test Unlike Post
if [ ! -z "$POST_ID" ]; then
    test_endpoint "DELETE" "/api/posts/$POST_ID/like" \
        "Unlike Post" \
        "" \
        "200"
fi

# 11. Test Delete Post
if [ ! -z "$POST_ID" ]; then
    test_endpoint "DELETE" "/api/posts/$POST_ID" \
        "Delete Post" \
        "" \
        "204"
fi

# 12. Test error cases
echo "Testing error cases..."
echo "========================================"

# Test missing auth header
echo -n "Testing: Missing authentication... "
response=$(curl -s -w "\n%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -d '{"content":"This should fail"}' \
    "$BASE_URL/api/posts")
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" == "401" ]; then
    echo -e "${GREEN}✓${NC} Correctly rejected (401)"
else
    echo -e "${RED}✗${NC} Expected 401, got $http_code"
fi

# Test invalid post content
echo -n "Testing: Invalid post content... "
response=$(curl -s -w "\n%{http_code}" -X POST \
    -H "X-User-ID: $USER_ID" \
    -H "Content-Type: application/json" \
    -d '{"content":""}' \
    "$BASE_URL/api/posts")
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" == "400" ]; then
    echo -e "${GREEN}✓${NC} Correctly rejected (400)"
else
    echo -e "${RED}✗${NC} Expected 400, got $http_code"
fi

# Test non-existent post
echo -n "Testing: Non-existent post... "
response=$(curl -s -w "\n%{http_code}" -X GET \
    -H "X-User-ID: $USER_ID" \
    "$BASE_URL/api/posts/00000000-0000-0000-0000-000000000000")
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" == "404" ]; then
    echo -e "${GREEN}✓${NC} Correctly returned 404"
else
    echo -e "${RED}✗${NC} Expected 404, got $http_code"
fi

echo
echo "========================================"
echo "Feed Service endpoint tests completed!"
echo
echo "Next steps:"
echo "1. Check Jaeger UI (http://localhost:16686) for distributed traces"
echo "2. Check Grafana (http://localhost:3000) for metrics"
echo "3. Run the load test: python scripts/load-test.py --users 50 --duration 10"
