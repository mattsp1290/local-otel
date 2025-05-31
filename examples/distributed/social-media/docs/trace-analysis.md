# 🔍 Distributed Trace Analysis Guide

This guide explains how to analyze distributed traces in our social media platform using Jaeger, helping you understand request flows, identify bottlenecks, and debug issues.

## Understanding Distributed Traces

A distributed trace represents a request's journey through multiple services. Each trace consists of:
- **Trace**: The entire request flow
- **Spans**: Individual operations within services
- **Context**: Metadata propagated between services

## Accessing Jaeger UI

1. Start the telemetry stack and social media platform
2. Navigate to http://localhost:16686
3. You'll see the Jaeger query interface

## Key Trace Patterns

### 1. User Login Flow

```
Frontend (SvelteKit SSR)
  └── Auth Service: /api/auth/login
      ├── Redis: Check rate limit
      ├── PostgreSQL: Verify credentials
      ├── JWT: Generate token
      └── Redis: Store session
```

**What to Look For:**
- Total login time (should be < 200ms)
- Database query duration
- Redis operation latency
- JWT generation overhead

### 2. Timeline Generation

```
Frontend: GET /feed
  └── Feed Service: /api/timeline/{user_id}
      ├── Redis: Check timeline cache [HIT/MISS]
      │   └── (on HIT) Return cached data
      ├── User Profile Service: Get following list
      │   ├── Redis: Check profile cache
      │   └── PostgreSQL: Query relationships
      ├── PostgreSQL: Fetch posts
      ├── Media Service: Get media URLs (parallel)
      └── Redis: Cache timeline
```

**What to Look For:**
- Cache hit rate (check span attributes)
- Parallel vs sequential operations
- Service-to-service latency
- Database query performance

### 3. OAuth Login Flow

```
Browser: Click "Login with Google"
  └── Frontend: /auth/login
      └── Auth Service: /api/auth/google
          ├── Generate state token
          ├── Redis: Store state
          └── Redirect to Google
[Google Authorization]
Browser: OAuth callback
  └── Frontend: /auth/callback
      └── Auth Service: /api/auth/google/callback
          ├── Redis: Verify state
          ├── Exchange code for token
          ├── PostgreSQL: Create/update user
          ├── User Profile Service: Initialize profile
          └── Redis: Create session
```

## Using Jaeger Features

### 1. Service Map
- Click "System Architecture" tab
- Shows service dependencies
- Identifies high-traffic paths
- Reveals service bottlenecks

### 2. Trace Search
```
Service: feed-service
Operation: GET /api/timeline/{user_id}
Tags: cache.hit=false error=true
Min Duration: 1s
```

### 3. Trace Comparison
- Select multiple traces
- Click "Compare" button
- Identify performance variations
- Spot anomalies

## Analyzing Performance Issues

### Slow Requests
1. Search for traces > 1 second
2. Expand the trace timeline
3. Look for:
   - Long database queries (> 100ms)
   - Sequential operations that could be parallel
   - Missing cache hits
   - Network timeouts

### Error Traces
1. Filter by `error=true` tag
2. Check span logs for error details
3. Follow error propagation
4. Identify root cause service

### Cache Performance
Look for these span attributes:
- `cache.hit=true/false`
- `cache.operation=get/set`
- `cache.key=...`

Calculate cache hit ratio:
```
(traces with cache.hit=true) / (total traces) * 100
```

## Common Issues and Solutions

### 1. N+1 Query Problem
**Symptom**: Multiple database queries in a loop
```
Feed Service
  └── Loop (10 times)
      └── User Profile Service: Get profile
          └── PostgreSQL: SELECT * FROM profiles WHERE id = ?
```

**Solution**: Batch fetch profiles

### 2. Missing Trace Context
**Symptom**: Broken traces, orphaned spans
```
Auth Service [Trace A]
  └── (broken link)

User Profile Service [Trace B]
  └── Initialize profile
```

**Solution**: Ensure trace headers are propagated

### 3. Cache Stampede
**Symptom**: Multiple services hitting DB after cache expiry
```
Timeline Request 1 → Cache MISS → DB Query
Timeline Request 2 → Cache MISS → DB Query
Timeline Request 3 → Cache MISS → DB Query
```

**Solution**: Implement cache warming or locking

## Performance Optimization Tips

### 1. Identify Critical Path
- Find the longest span in the trace
- This is your optimization target
- Focus on operations that block others

### 2. Parallelization Opportunities
Look for sequential operations that could run in parallel:
```
Before:
  └── Get User Profile (100ms)
      └── Get User Posts (150ms)
          └── Get Media URLs (50ms)

After:
  ├── Get User Profile (100ms)
  ├── Get User Posts (150ms) [parallel]
  └── Get Media URLs (50ms) [parallel]
```

### 3. Cache Optimization
Track cache effectiveness:
- Hit rate by operation type
- Cache invalidation patterns
- TTL optimization opportunities

## Advanced Analysis

### 1. Baggage Propagation
Check for business context in spans:
- `user.id`
- `user.tier` (free/premium)
- `feature.flag`

### 2. Service Mesh Integration
If using Istio/Linkerd, look for:
- Sidecar proxy latency
- Circuit breaker activations
- Retry attempts

### 3. Database Query Analysis
Examine query spans for:
- Query execution time
- Row count
- Index usage (in span tags)

## Creating Custom Dashboards

### Trace Metrics
Export trace data to create dashboards for:
- P50/P95/P99 latencies by operation
- Error rate by service
- Cache hit rate trends
- Service dependency changes

### Business Metrics from Traces
Extract business insights:
- User actions per session
- Feature adoption rates
- User journey completion

## Debugging Workflows

### 1. User Complaint: "Feed is slow"
1. Get approximate timestamp
2. Search traces for user ID
3. Filter by feed service
4. Compare with baseline performance
5. Identify bottleneck

### 2. Intermittent Errors
1. Search for error traces in time window
2. Group by error type
3. Check for patterns (time, user, data)
4. Trace back to root cause

### 3. Service Degradation
1. Compare current vs historical traces
2. Check for new operations
3. Look for increased latencies
4. Verify cache performance

## Best Practices

1. **Add Context**: Include relevant business data in spans
2. **Use Semantic Conventions**: Follow OpenTelemetry standards
3. **Sample Wisely**: Balance visibility with overhead
4. **Monitor Cardinality**: Avoid high-cardinality tags
5. **Correlate Metrics**: Link traces with metrics/logs

## Example Queries

### Find Slow Timeline Generations
```
Service: feed-service
Operation: GET /api/timeline/*
Min Duration: 500ms
```

### Track OAuth Success Rate
```
Service: auth-service
Operation: oauth.*.callback
Tags: oauth.provider exists
```

### Cache Miss Analysis
```
Service: user-profile-service
Tags: cache.hit=false
```

## Troubleshooting Jaeger

### No Traces Appearing
1. Verify OTEL collector is running
2. Check service environment variables
3. Confirm network connectivity
4. Review collector logs

### Incomplete Traces
1. Check trace propagation headers
2. Verify all services have telemetry
3. Look for timing/timeout issues

### Performance Impact
1. Monitor telemetry overhead
2. Adjust sampling rate
3. Optimize span attributes
4. Use head-based sampling

This guide helps you leverage distributed tracing to understand, optimize, and debug your microservices architecture effectively.
