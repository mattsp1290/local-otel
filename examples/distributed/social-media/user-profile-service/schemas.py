"""
Pydantic schemas for request/response validation
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl

class ProfileCreate(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[HttpUrl] = None

class ProfileUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[HttpUrl] = None

class ProfileResponse(BaseModel):
    user_id: str
    display_name: str
    bio: Optional[str]
    avatar_url: Optional[str]
    follower_count: int
    following_count: int
    created_at: datetime
    
    class Config:
        orm_mode = True

class RelationshipResponse(BaseModel):
    follower_id: str
    following_id: str
    created_at: datetime
    
    class Config:
        orm_mode = True

class SearchResponse(BaseModel):
    query: str
    results: List[ProfileResponse]
    total: int
    limit: int
    offset: int

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    trace_id: Optional[str] = None
