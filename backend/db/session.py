from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from backend.config.settings import get_settings

settings = get_settings()

# Configure the database engine
async_engine = create_async_engine(settings.DATABASE_URL, echo=False)

# Create an async session factory
AsyncSessionLocal = sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)


# Dependency to get the database session
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
