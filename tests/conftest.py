import pytest
import pytest_asyncio # Import pytest_asyncio
from unittest.mock import AsyncMock, patch, Mock
import nltk # Import nltk
import warnings # Add this line
import sys
import pandas as pd
import numpy as np

pytest_plugins = ["pytest_httpx"] # Add this line

# Import database components for test setup
from backend.db.base import Base
from backend.db.session import get_db, is_testing
from backend.db.models import User, Portfolio, Holding, Watchlist, WatchlistSymbol, UserSetting, Alert
from sqlalchemy.orm import Session
from backend.security.utils import get_password_hash
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os
from backend.config.settings import get_settings
from backend.api.main import app

# Download vader_lexicon once per session
def pytest_configure(config):
    """Download NLTK data needed for tests."""
    # Suppress the specific DeprecationWarning from pandas_ta related to pkg_resources
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        message=r"pkg_resources is deprecated as an API.*"
    )
    
    # Also suppress RuntimeWarning for coroutine never awaited
    warnings.filterwarnings(
        "ignore",
        category=RuntimeWarning,
        message=r"coroutine '.*' was never awaited"
    )
    
    try:
        # Check if the resource exists to avoid repeated downloads
        nltk.data.find('sentiment/vader_lexicon.zip')
    except nltk.downloader.DownloadError:
        print("\nDownloading NLTK vader_lexicon...")
        nltk.download('vader_lexicon')
    except LookupError: # Handle cases where the path might be slightly different
        print("\nDownloading NLTK vader_lexicon (LookupError fallback)...")
        nltk.download('vader_lexicon')
    # Add other downloads here if needed, e.g., nltk.download('punkt')

@pytest_asyncio.fixture(scope="session", autouse=True) # Use pytest_asyncio.fixture
def mock_redis_client():
    """Globally mock redis_client for all tests with stateful behavior."""
    mock_instance = AsyncMock()  # This is the mock Redis client instance
    actual_cache = {}  # Simple dict to simulate cache storage

    async def mock_get(key):
        # logger.debug(f"Mock Redis GET: key={key}, value={actual_cache.get(key, None)}")
        return actual_cache.get(key, None)

    async def mock_set(key, value, ex=None): # ex is for expiry
        # logger.debug(f"Mock Redis SET: key={key}, value={value}, ex={ex}")
        actual_cache[key] = value
        return True

    async def mock_delete(key):
        # logger.debug(f"Mock Redis DELETE: key={key}")
        if key in actual_cache:
            del actual_cache[key]
            return 1
        return 0

    mock_instance.get = AsyncMock(side_effect=mock_get)
    mock_instance.set = AsyncMock(side_effect=mock_set)
    mock_instance.delete = AsyncMock(side_effect=mock_delete)
    mock_instance.ping = AsyncMock(return_value=True) # Mock ping as well

    # Define an actual async function to replace get_redis_client
    async def fake_async_get_redis_client(*args, **kwargs):
        return mock_instance

    # Patch get_redis_client with our actual async function
    # The target for the patch should be where 'get_redis_client' is looked up
    # by the 'standard_agent_execution' decorator in 'backend.agents.decorators.py'.
    with patch("backend.agents.decorators.get_redis_client", new=fake_async_get_redis_client):
        yield mock_instance
        actual_cache.clear() # Clear cache after session

@pytest.fixture
def sample_real_stock_data():
    """Fixture providing sample stock data for testing"""
    return {
        "symbol": "TEST_REAL_STOCK",
        "price": 100.0,
        "eps": 5.0,
        "pe_ratio": 20.0,
        "market_cap": 1000000000,
        "volume": 1000000,
        "historical_prices": pd.Series(
            np.linspace(90, 110, 50),
            index=pd.date_range(end=pd.Timestamp.now(), periods=50, freq='D')
        )
    }

@pytest.fixture
def mock_analyzer():
    """Fixture providing a mock VADER sentiment analyzer for news sentiment testing"""
    mock = Mock()
    mock.polarity_scores = Mock(return_value={
        'compound': 0.5,
        'neu': 0.5,
        'pos': 0.5,
        'neg': 0.0
    })
    return mock

# Database setup fixtures

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create all database tables and setup test data."""
    # Set testing environment
    os.environ["PYTEST_CURRENT_TEST"] = "True"
    
    # Create engine for testing
    settings = get_settings()
    db_url = settings.DATABASE_URL
    if db_url.startswith('sqlite+aiosqlite'):
        db_url = db_url.replace('sqlite+aiosqlite', 'sqlite')
    
    engine = create_engine(db_url, echo=False, connect_args={"check_same_thread": False})
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create a test user for authentication tests
    db = Session(bind=engine)
    try:
        # Create admin user for tests
        existing_admin = db.query(User).filter(User.username == "admin").first()
        if not existing_admin:
            admin_user = User(
                username="admin",
                email="admin@example.com",
                hashed_password=get_password_hash("changeme"),
                full_name="Admin User",
                is_active=True,
                is_superuser=True
            )
            db.add(admin_user)
            
        # Also create a regular test user for other tests
        existing_user = db.query(User).filter(User.username == "testuser").first()
        if not existing_user:
            test_user = User(
                username="testuser",
                email="test@example.com",
                hashed_password=get_password_hash("testpassword"),
                full_name="Test User",
                is_active=True,
                is_superuser=False
            )
            db.add(test_user)
            
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error creating test users: {e}")
        raise
    finally:
        db.close()
        
    # Create async engine for FastAPI dependency override
    async_db_url = db_url.replace('sqlite', 'sqlite+aiosqlite') if 'sqlite' in db_url else db_url
    async_engine = create_async_engine(async_db_url, echo=False)
    AsyncSessionLocal = sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )

    # Override the database dependency
    async def override_get_db():
        async with AsyncSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
        
    yield
    
    # Cleanup: Drop all tables and remove dependency override
    Base.metadata.drop_all(bind=engine)
    app.dependency_overrides.clear()