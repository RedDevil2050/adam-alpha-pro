import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from backend.config.settings import get_settings
from typing import AsyncGenerator, Generator

settings = get_settings()

# Check if we're in a testing environment
is_testing = os.getenv("PYTEST_CURRENT_TEST") is not None or settings.is_testing

if is_testing:
    # Use a synchronous engine for testing - SQLite doesn't support asyncio
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    
    # Convert async URL to sync URL for SQLite if needed
    db_url = settings.DATABASE_URL
    if db_url.startswith('sqlite+aiosqlite'):
        db_url = db_url.replace('sqlite+aiosqlite', 'sqlite')
    
    engine = create_engine(db_url, echo=False, connect_args={"check_same_thread": False})
    
    # Create a synchronous session factory for testing
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Dependency to get the database session for testing
    def get_db() -> Generator[Session, None, None]:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
else:
    # Use an async engine for production
    # Configure the database engine with proper URL format
    db_url = settings.DATABASE_URL
    if db_url.startswith('sqlite:') and not db_url.startswith('sqlite+aiosqlite:'):
        db_url = db_url.replace('sqlite:', 'sqlite+aiosqlite:')
        
    async_engine = create_async_engine(db_url, echo=False)
    
    # Create an async session factory for production
    AsyncSessionLocal = sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )

    # Dependency to get the database session for production
    async def get_db() -> AsyncGenerator[AsyncSession, None]:
        async with AsyncSessionLocal() as session:
            yield session
