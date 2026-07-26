"""
Test configuration for Marty Bot.
Ensures test isolation and prevents accidental use of production services.

CRITICAL: All tests must mock LLM API calls (Neuralwatt / GLM) to prevent:
- Unnecessary API costs
- Rate limiting and quota exhaustion
- Non-deterministic test results
- Leaking test data to external services

Only explicit smoke tests should use real API calls, never in CI.
"""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database import Base, get_db
from src.main import app

# SQLite for unit tests
SQLITE_URL = "sqlite+aiosqlite:///:memory:"
sqlite_engine = create_async_engine(SQLITE_URL, echo=False)
SqliteSessionLocal = async_sessionmaker(
    sqlite_engine, class_=AsyncSession, expire_on_commit=False
)


async def get_sqlite_db():
    async with SqliteSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def setup_sqlite_db():
    app.dependency_overrides[get_db] = get_sqlite_db
    async with sqlite_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with sqlite_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# Postgres for integration tests
POSTGRES_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://marty_test:password@localhost:55432/marty_test",
)
pg_engine = create_async_engine(
    POSTGRES_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_reset_on_return="commit",
)
PgSessionLocal = async_sessionmaker(
    pg_engine, class_=AsyncSession, expire_on_commit=False
)


async def get_pg_db():
    async with PgSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def use_postgres_db(request):
    # Create a fresh engine for this test to ensure complete isolation
    test_engine = create_async_engine(
        POSTGRES_URL,
        echo=False,
        pool_size=3,
        max_overflow=5,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_reset_on_return="commit",
    )
    TestSessionLocal = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def get_test_pg_db():
        async with TestSessionLocal() as session:
            yield session

    # Save the original overrides
    original_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = get_test_pg_db

    # Monkey patch get_db_session function directly
    from contextlib import asynccontextmanager

    import src.database

    original_get_db_session = src.database.get_db_session

    @asynccontextmanager
    async def test_get_db_session():
        # Create a fresh session for each call with proper isolation
        async with TestSessionLocal() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    src.database.get_db_session = test_get_db_session

    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield TestSessionLocal, test_engine

    # Drop tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    # Dispose of the test engine
    await test_engine.dispose()

    # Restore the original overrides
    if original_override is not None:
        app.dependency_overrides[get_db] = original_override
    else:
        app.dependency_overrides.pop(get_db, None)

    # Restore the original function
    src.database.get_db_session = original_get_db_session


@pytest_asyncio.fixture
async def clean_postgres_db(use_postgres_db):
    """Clean Postgres database between tests when using Postgres."""
    # Get the test engine from the use_postgres_db fixture
    test_session_local, test_engine = use_postgres_db

    # Clean all tables before the test
    async with test_engine.begin() as conn:
        # Disable foreign key checks temporarily
        await conn.execute(text("SET session_replication_role = replica;"))

        # Delete all data from all tables
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())

        # Re-enable foreign key checks
        await conn.execute(text("SET session_replication_role = DEFAULT;"))

    yield

    # Clean all tables after the test as well
    async with test_engine.begin() as conn:
        # Disable foreign key checks temporarily
        await conn.execute(text("SET session_replication_role = replica;"))

        # Delete all data from all tables
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())

        # Re-enable foreign key checks
        await conn.execute(text("SET session_replication_role = DEFAULT;"))


@pytest.fixture(autouse=True)
def test_environment():
    """Force test environment setup - no production API keys."""
    with patch.dict(
        os.environ,
        {
            # Remove production LLM keys; tests mock the client directly.
            "NEURALWATT_API_KEY": "test-token",
            # Set test database URL so health check works correctly
            "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
            # Set test values if needed
            "HARDCOVER_API_TOKEN": "test-token",
        },
        clear=False,
    ):
        yield


@pytest.fixture(autouse=True)
def mock_docs_index():
    """Stub the docs index fetch so unit tests don't hit raw.githubusercontent.com.

    The ai_client appends fetch_index() output to the system prompt on every
    request. Without this stub, tests either go to the network or each test
    has to remember to patch it.
    """
    from src.tools.docs.fetcher import DocPayload

    stub = DocPayload(
        slug="index",
        frontmatter={"publish": True, "title": "test index"},
        body="",
        agent_guidance=[],
        fetched_at=0.0,
    )
    with patch("src.tools.docs.fetcher.fetch_index", AsyncMock(return_value=stub)):
        yield


def _make_llm_response(text: str, tool_calls=None):
    """Build a mock LLM response in OpenAI chat-completions shape."""
    message = MagicMock()
    message.content = text
    message.tool_calls = tool_calls
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


@pytest.fixture(autouse=True)
def mock_llm_api():
    """
    Global mock for LLM API calls (Neuralwatt-hosted GLM).

    Mocks `client.chat.completions.create` so tests don't hit the network.
    Tests can override the mock response using:
        mock_llm_api.chat.completions.create.return_value = custom_response
    """
    default_response = _make_llm_response("hey! what can I help you with?")

    with patch("src.ai_client.client") as mock_client:
        mock_client.chat = MagicMock()
        mock_client.chat.completions = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=default_response)
        mock_client.chat.completions.create.reset_mock()

        yield mock_client


@pytest.fixture
def llm_response():
    """
    Factory fixture for creating LLM response objects in OpenAI shape.

    Usage:
        def test_something(llm_response):
            response = llm_response("Hello there!")
            mock_llm_api.chat.completions.create.return_value = response
    """
    return _make_llm_response


@pytest.fixture(scope="session", autouse=True)
def initialize_database_for_integration(request):
    if request.config.getoption("-m") and "integration" in request.config.getoption(
        "-m"
    ):

        async def init_db():
            async for _ in get_db():
                break

        asyncio.run(init_db())
