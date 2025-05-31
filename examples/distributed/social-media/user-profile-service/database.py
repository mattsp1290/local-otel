"""
Database configuration and session management
"""

import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:password@localhost:5432/profiles")

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    poolclass=NullPool,  # Disable pooling for async
    echo=False,  # Set to True for SQL query logging
)

# Create async session factory
async_session_maker = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for models
Base = declarative_base()

async def init_db():
    """Initialize database - create tables if needed"""
    async with engine.begin() as conn:
        # Import models to ensure they're registered
        from models import UserProfile, Relationship
        
        # Create tables
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    """Dependency to get database session"""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
