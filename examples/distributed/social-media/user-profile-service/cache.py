"""
Redis cache configuration and utilities
"""

import os
from redis.asyncio import Redis, ConnectionPool
from typing import Optional

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Global redis instance
redis_client: Optional[Redis] = None

async def init_redis():
    """Initialize Redis connection"""
    global redis_client
    
    # Create connection pool
    pool = ConnectionPool.from_url(
        REDIS_URL,
        decode_responses=True,
        max_connections=50
    )
    
    # Create Redis client
    redis_client = Redis(connection_pool=pool)
    
    # Test connection
    await redis_client.ping()
    
    return redis_client

async def get_redis() -> Redis:
    """Dependency to get Redis client"""
    if redis_client is None:
        await init_redis()
    return redis_client

async def close_redis():
    """Close Redis connection"""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None
