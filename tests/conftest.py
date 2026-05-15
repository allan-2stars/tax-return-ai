"""Shared test fixtures — async SQLite test DB + test client."""
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.ai.providers.mock import MockProvider
from app.db.base import Base
from app.db.deps import get_db
from app.ocr.providers.mock import MockOCRProvider
from app.routers import auth, workspaces, documents, items, export, compliance


@pytest_asyncio.fixture
async def db_session_factory(tmp_path: Path):
    """Per-test sync SQLite with async wrapper avoids aiosqlite runtime hangs."""
    _ = tmp_path  # keep fixture compatibility; DB is in-memory for focused tests
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    Base.metadata.create_all(bind=engine)

    yield session_factory

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


class AsyncSessionAdapter:
    """Minimal async facade over sync SQLAlchemy Session for focused API tests."""

    def __init__(self, session: Session):
        self._session = session

    async def execute(self, *args, **kwargs):
        return self._session.execute(*args, **kwargs)

    def add(self, *args, **kwargs):
        return self._session.add(*args, **kwargs)

    async def flush(self):
        self._session.flush()

    async def commit(self):
        self._session.commit()

    async def rollback(self):
        self._session.rollback()

    async def refresh(self, instance):
        self._session.refresh(instance)


@pytest_asyncio.fixture
async def db_session(db_session_factory):
    """Provide a raw async DB session for service-level tests."""
    session = db_session_factory()
    adapter = AsyncSessionAdapter(session)
    try:
        yield adapter
    finally:
        session.close()


@pytest_asyncio.fixture
async def async_client(db_session_factory):
    """FastAPI test client with overridden DB dependency."""
    test_app = FastAPI()
    test_app.include_router(auth.router)
    test_app.include_router(workspaces.router)
    test_app.include_router(documents.router)
    test_app.include_router(items.router)
    test_app.include_router(export.router)
    test_app.include_router(compliance.router)

    async def override_get_db() -> AsyncGenerator[AsyncSessionAdapter, None]:
        session = db_session_factory()
        adapter = AsyncSessionAdapter(session)
        try:
            yield adapter
        finally:
            session.close()

    test_app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    test_app.dependency_overrides.clear()


@pytest.fixture
def mock_ai_provider():
    return MockProvider()


@pytest.fixture
def mock_ocr_provider():
    return MockOCRProvider()
