"""
SQLAlchemy models for User Profile Service
"""

from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, UniqueConstraint, Index, select, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from database import Base
import uuid

class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    bio = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes for search
    __table_args__ = (
        Index('idx_display_name_search', 'display_name'),
    )
    
    @classmethod
    async def get_by_user_id(cls, db: AsyncSession, user_id: str):
        """Get profile by user ID"""
        result = await db.execute(
            select(cls).where(cls.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    @classmethod
    async def create(cls, db: AsyncSession, user_id: str, data: dict):
        """Create new profile"""
        profile = cls(user_id=user_id, **data)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
        return profile
    
    @classmethod
    async def update(cls, db: AsyncSession, user_id: str, data: dict):
        """Update profile"""
        profile = await cls.get_by_user_id(db, user_id)
        if profile:
            for key, value in data.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
            profile.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(profile)
        return profile
    
    @classmethod
    async def search(cls, db: AsyncSession, query: str, limit: int = 20, offset: int = 0):
        """Search profiles by display name"""
        result = await db.execute(
            select(cls)
            .where(cls.display_name.ilike(f"%{query}%"))
            .order_by(cls.display_name)
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()


class Relationship(Base):
    __tablename__ = "relationships"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    follower_id = Column(String(255), nullable=False, index=True)
    following_id = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('follower_id', 'following_id', name='uq_follower_following'),
        Index('idx_follower_id', 'follower_id'),
        Index('idx_following_id', 'following_id'),
    )
    
    @classmethod
    async def get(cls, db: AsyncSession, follower_id: str, following_id: str):
        """Get specific relationship"""
        result = await db.execute(
            select(cls).where(
                (cls.follower_id == follower_id) & 
                (cls.following_id == following_id)
            )
        )
        return result.scalar_one_or_none()
    
    @classmethod
    async def create(cls, db: AsyncSession, follower_id: str, following_id: str):
        """Create new relationship"""
        relationship = cls(follower_id=follower_id, following_id=following_id)
        db.add(relationship)
        await db.commit()
        await db.refresh(relationship)
        return relationship
    
    @classmethod
    async def delete(cls, db: AsyncSession, follower_id: str, following_id: str):
        """Delete relationship"""
        relationship = await cls.get(db, follower_id, following_id)
        if relationship:
            await db.delete(relationship)
            await db.commit()
            return True
        return False
    
    @classmethod
    async def get_follower_count(cls, db: AsyncSession, user_id: str):
        """Get follower count for a user"""
        result = await db.execute(
            select(func.count(cls.id)).where(cls.following_id == user_id)
        )
        return result.scalar() or 0
    
    @classmethod
    async def get_following_count(cls, db: AsyncSession, user_id: str):
        """Get following count for a user"""
        result = await db.execute(
            select(func.count(cls.id)).where(cls.follower_id == user_id)
        )
        return result.scalar() or 0
    
    @classmethod
    async def get_follower_ids(cls, db: AsyncSession, user_id: str):
        """Get list of follower IDs"""
        result = await db.execute(
            select(cls.follower_id).where(cls.following_id == user_id)
        )
        return [row[0] for row in result.fetchall()]
    
    @classmethod
    async def get_following_ids(cls, db: AsyncSession, user_id: str):
        """Get list of following IDs"""
        result = await db.execute(
            select(cls.following_id).where(cls.follower_id == user_id)
        )
        return [row[0] for row in result.fetchall()]
