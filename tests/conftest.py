"""Shared test fixtures — async SQLite test DB + test client."""
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.db.base import Base
from app.db.deps import get_db
from app.main import app
from app.ai.providers.mock import MockProvider
from app.ocr.providers.mock import MockOCRProvider

# In-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite://"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the test session (pytest-asyncio)."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create tables before each test, drop after. Clean slate every time."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db():
    """Override FastAPI dependency with test DB session."""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def db_session():
    """Provide a raw async DB session for service-level tests."""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def async_client():
    """FastAPI test client with overridden DB dependency."""
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def mock_ai_provider():
    return MockProvider()


@pytest.fixture
def mock_ocr_provider():
    return MockOCRProvider()
