"""
User Profile Service - Social Media Platform
Manages user profiles, relationships, and search functionality
"""

import asyncio
import os
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

import statsd
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from telemetry import init_telemetry
from database import get_db, init_db
from cache import get_redis, init_redis
from models import UserProfile, Relationship
from schemas import (
    ProfileCreate, ProfileUpdate, ProfileResponse,
    RelationshipResponse, SearchResponse
)
from auth import verify_token, get_current_user
from logger import setup_logging, logger

# Environment configuration
SERVICE_NAME = os.getenv("SERVICE_NAME", "user-profile-service")
SERVICE_VERSION = "1.0.0"
STATSD_HOST = os.getenv("STATSD_HOST", "localhost")
STATSD_PORT = int(os.getenv("STATSD_PORT", "8125"))

# Initialize telemetry
tracer = init_telemetry()

# Initialize StatsD client
statsd_client = statsd.StatsClient(
    host=STATSD_HOST,
    port=STATSD_PORT,
    prefix='user_profile_service'
)

# Setup logging
setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifecycle"""
    # Startup
    logger.info("Starting User Profile Service", extra={
        "event": "startup",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION
    })
    
    # Initialize database
    await init_db()
    
    # Initialize Redis
    await init_redis()
    
    yield
    
    # Shutdown
    logger.info("Shutting down User Profile Service", extra={
        "event": "shutdown"
    })

# Create FastAPI app
app = FastAPI(
    title="User Profile Service",
    description="Manages user profiles and relationships",
    version=SERVICE_VERSION,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/users/{user_id}", response_model=ProfileResponse)
async def get_profile(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: dict = Depends(get_current_user)
):
    """Get user profile by ID"""
    start_time = asyncio.get_event_loop().time()
    
    with tracer.start_as_current_span("get_profile") as span:
        span.set_attributes({
            "user.id": user_id,
            "requester.id": current_user["id"]
        })
        
        # Check cache first
        cache_key = f"profile:{user_id}"
        cached_profile = await redis.get(cache_key)
        
        if cached_profile:
            statsd_client.incr('cache.hit', tags=['operation:get_profile'])
            span.set_attribute("cache.hit", True)
            profile_data = json.loads(cached_profile)
            
            # Track response time
            elapsed = (asyncio.get_event_loop().time() - start_time) * 1000
            statsd_client.timing('request.duration', elapsed, tags=['endpoint:get_profile'])
            
            return ProfileResponse(**profile_data)
        
        # Cache miss - fetch from database
        statsd_client.incr('cache.miss', tags=['operation:get_profile'])
        span.set_attribute("cache.hit", False)
        
        profile = await UserProfile.get_by_user_id(db, user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Get follower/following counts
        follower_count = await Relationship.get_follower_count(db, user_id)
        following_count = await Relationship.get_following_count(db, user_id)
        
        profile_data = {
            "user_id": profile.user_id,
            "display_name": profile.display_name,
            "bio": profile.bio,
            "avatar_url": profile.avatar_url,
            "follower_count": follower_count,
            "following_count": following_count,
            "created_at": profile.created_at.isoformat()
        }
        
        # Cache the profile
        await redis.setex(cache_key, 3600, json.dumps(profile_data))  # 1 hour TTL
        
        # Track response time
        elapsed = (asyncio.get_event_loop().time() - start_time) * 1000
        statsd_client.timing('request.duration', elapsed, tags=['endpoint:get_profile'])
        
        return ProfileResponse(**profile_data)

@app.post("/api/users/{user_id}/profile", response_model=ProfileResponse)
async def create_or_update_profile(
    user_id: str,
    profile_data: ProfileCreate,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: dict = Depends(get_current_user)
):
    """Create or update user profile"""
    # Ensure user can only update their own profile
    if user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Cannot update another user's profile")
    
    with tracer.start_as_current_span("create_update_profile") as span:
        span.set_attributes({
            "user.id": user_id,
            "operation": "create_or_update"
        })
        
        # Check if profile exists
        existing = await UserProfile.get_by_user_id(db, user_id)
        
        if existing:
            # Update existing profile
            profile = await UserProfile.update(db, user_id, profile_data.dict())
            statsd_client.incr('profile.updated')
        else:
            # Create new profile
            profile = await UserProfile.create(db, user_id, profile_data.dict())
            statsd_client.incr('profile.created')
        
        # Invalidate cache
        await redis.delete(f"profile:{user_id}")
        
        # Get counts for response
        follower_count = await Relationship.get_follower_count(db, user_id)
        following_count = await Relationship.get_following_count(db, user_id)
        
        return ProfileResponse(
            user_id=profile.user_id,
            display_name=profile.display_name,
            bio=profile.bio,
            avatar_url=profile.avatar_url,
            follower_count=follower_count,
            following_count=following_count,
            created_at=profile.created_at
        )

@app.post("/api/users/{user_id}/follow", response_model=RelationshipResponse)
async def follow_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: dict = Depends(get_current_user)
):
    """Follow a user"""
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    
    with tracer.start_as_current_span("follow_user") as span:
        span.set_attributes({
            "follower.id": current_user["id"],
            "following.id": user_id
        })
        
        # Check if already following
        existing = await Relationship.get(db, current_user["id"], user_id)
        if existing:
            raise HTTPException(status_code=400, detail="Already following this user")
        
        # Create relationship
        relationship = await Relationship.create(db, current_user["id"], user_id)
        
        # Invalidate caches
        await redis.delete(f"profile:{user_id}")
        await redis.delete(f"profile:{current_user['id']}")
        await redis.delete(f"followers:{user_id}")
        await redis.delete(f"following:{current_user['id']}")
        
        statsd_client.incr('relationship.created', tags=['type:follow'])
        
        return RelationshipResponse(
            follower_id=relationship.follower_id,
            following_id=relationship.following_id,
            created_at=relationship.created_at
        )

@app.delete("/api/users/{user_id}/follow")
async def unfollow_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: dict = Depends(get_current_user)
):
    """Unfollow a user"""
    with tracer.start_as_current_span("unfollow_user") as span:
        span.set_attributes({
            "follower.id": current_user["id"],
            "following.id": user_id
        })
        
        # Delete relationship
        deleted = await Relationship.delete(db, current_user["id"], user_id)
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Not following this user")
        
        # Invalidate caches
        await redis.delete(f"profile:{user_id}")
        await redis.delete(f"profile:{current_user['id']}")
        await redis.delete(f"followers:{user_id}")
        await redis.delete(f"following:{current_user['id']}")
        
        statsd_client.incr('relationship.deleted', tags=['type:unfollow'])
        
        return {"message": "Unfollowed successfully"}

@app.get("/api/users/{user_id}/followers", response_model=List[ProfileResponse])
async def get_followers(
    user_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: dict = Depends(get_current_user)
):
    """Get user's followers"""
    with tracer.start_as_current_span("get_followers") as span:
        span.set_attributes({
            "user.id": user_id,
            "pagination.limit": limit,
            "pagination.offset": offset
        })
        
        # Try cache for follower IDs
        cache_key = f"followers:{user_id}"
        cached_ids = await redis.get(cache_key)
        
        if cached_ids:
            follower_ids = json.loads(cached_ids)
            span.set_attribute("cache.hit", True)
        else:
            # Get from database
            follower_ids = await Relationship.get_follower_ids(db, user_id)
            # Cache for 5 minutes
            await redis.setex(cache_key, 300, json.dumps(follower_ids))
            span.set_attribute("cache.hit", False)
        
        # Paginate
        paginated_ids = follower_ids[offset:offset + limit]
        
        # Fetch profiles
        profiles = []
        for follower_id in paginated_ids:
            profile = await get_profile(follower_id, db, redis, current_user)
            profiles.append(profile)
        
        statsd_client.gauge('followers.returned', len(profiles), tags=[f'user_id:{user_id}'])
        
        return profiles

@app.get("/api/users/{user_id}/following", response_model=List[ProfileResponse])
async def get_following(
    user_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: dict = Depends(get_current_user)
):
    """Get users that this user follows"""
    with tracer.start_as_current_span("get_following") as span:
        span.set_attributes({
            "user.id": user_id,
            "pagination.limit": limit,
            "pagination.offset": offset
        })
        
        # Try cache for following IDs
        cache_key = f"following:{user_id}"
        cached_ids = await redis.get(cache_key)
        
        if cached_ids:
            following_ids = json.loads(cached_ids)
            span.set_attribute("cache.hit", True)
        else:
            # Get from database
            following_ids = await Relationship.get_following_ids(db, user_id)
            # Cache for 5 minutes
            await redis.setex(cache_key, 300, json.dumps(following_ids))
            span.set_attribute("cache.hit", False)
        
        # Paginate
        paginated_ids = following_ids[offset:offset + limit]
        
        # Fetch profiles
        profiles = []
        for following_id in paginated_ids:
            profile = await get_profile(following_id, db, redis, current_user)
            profiles.append(profile)
        
        statsd_client.gauge('following.returned', len(profiles), tags=[f'user_id:{user_id}'])
        
        return profiles

@app.get("/api/users/search", response_model=SearchResponse)
async def search_users(
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Search users by name or username"""
    with tracer.start_as_current_span("search_users") as span:
        span.set_attributes({
            "search.query": q,
            "search.limit": limit,
            "search.offset": offset
        })
        
        # Search in database
        results = await UserProfile.search(db, q, limit, offset)
        
        # Convert to response format
        profiles = []
        for profile in results:
            profiles.append(ProfileResponse(
                user_id=profile.user_id,
                display_name=profile.display_name,
                bio=profile.bio,
                avatar_url=profile.avatar_url,
                follower_count=0,  # Could be optimized with batch query
                following_count=0,
                created_at=profile.created_at
            ))
        
        statsd_client.gauge('search.results', len(profiles), tags=[f'query:{q[:20]}'])
        
        return SearchResponse(
            query=q,
            results=profiles,
            total=len(profiles),
            limit=limit,
            offset=offset
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=os.getenv("RELOAD", "false").lower() == "true"
    )
