"""
Pytest configuration and fixtures for DedupTickets tests.

Provides:
- Async test support
- Mock Cosmos DB containers
- Test client fixtures
- Factory fixtures for domain models
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from deduptickets.config import Settings
from deduptickets.models.ticket import Ticket

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

# =============================================================================
# Pytest Configuration
# =============================================================================


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Settings Fixtures
# =============================================================================


@pytest.fixture
def test_settings() -> Settings:
    """Get test settings with safe defaults."""
    return Settings(
        cosmos_endpoint="https://localhost:8081",
        cosmos_key="test-key",
        cosmos_database="test-db",
        cosmos_ssl_verify=False,
        api_key="test-api-key",
        debug=True,
        log_level="DEBUG",
    )


# =============================================================================
# Mock Container Fixtures
# =============================================================================


@pytest.fixture
def mock_container() -> AsyncMock:
    """Create a mock Cosmos DB container."""
    container = AsyncMock()

    # Mock standard operations
    container.create_item = AsyncMock()
    container.read_item = AsyncMock()
    container.upsert_item = AsyncMock()
    container.delete_item = AsyncMock()
    container.query_items = MagicMock()

    return container


@pytest.fixture
def mock_cosmos_client_manager(mock_container: AsyncMock) -> Generator[MagicMock, None, None]:
    """Mock the CosmosClientManager."""
    from unittest.mock import patch  # noqa: PLC0415

    with patch("deduptickets.cosmos.client.CosmosClientManager") as mock_manager:
        mock_manager.get_container = AsyncMock(return_value=mock_container)
        mock_manager.health_check = AsyncMock(return_value=True)
        mock_manager.initialize = AsyncMock()
        mock_manager.close = AsyncMock()
        yield mock_manager


# =============================================================================
# HTTP Client Fixtures
# =============================================================================


@pytest.fixture
def sync_client(
    test_settings: Settings,
    mock_cosmos_client_manager: MagicMock,
) -> Generator[TestClient, None, None]:
    """Create a synchronous test client."""
    from unittest.mock import patch  # noqa: PLC0415

    from deduptickets.main import create_app  # noqa: PLC0415

    with (
        patch("deduptickets.config.get_settings", return_value=test_settings),
        patch("deduptickets.dependencies.get_cached_settings", return_value=test_settings),
    ):
        app = create_app()
        with TestClient(app) as client:
            yield client


@pytest.fixture
async def async_client(
    test_settings: Settings,
    mock_cosmos_client_manager: MagicMock,
) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    from unittest.mock import patch  # noqa: PLC0415

    from deduptickets.main import create_app  # noqa: PLC0415

    with (
        patch("deduptickets.config.get_settings", return_value=test_settings),
        patch("deduptickets.dependencies.get_cached_settings", return_value=test_settings),
    ):
        app = create_app()
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client


@pytest.fixture
def auth_headers(test_settings: Settings) -> dict[str, str]:
    """Get authentication headers for tests."""
    return {
        "X-API-Key": test_settings.api_key.get_secret_value(),
        "X-User-ID": "test-user",
    }


# =============================================================================
# Model Factory Fixtures
# =============================================================================


@pytest.fixture
def ticket_factory() -> type:
    """Factory for creating test tickets."""

    class TicketFactory:
        @staticmethod
        def create(
            *,
            source_id: str | None = None,
            source_system: str = "test-system",
            title: str = "Test Ticket",
            description: str = "Test description",
            severity: str = "medium",
            product: str = "test-product",
            region: str = "us-east",
            cluster_id: str | None = None,
        ) -> Ticket:
            now = datetime.utcnow()
            pk = f"{region}|{now.strftime('%Y-%m')}"
            return Ticket(
                id=uuid4(),
                source_id=source_id or f"SRC-{uuid4().hex[:8]}",
                source_system=source_system,
                title=title,
                description=description,
                severity=severity,
                product=product,
                region=region,
                cluster_id=cluster_id,
                created_at=now,
                pk=pk,
            )

        @staticmethod
        def create_batch(count: int, **kwargs: Any) -> list[Ticket]:
            return [TicketFactory.create(**kwargs) for _ in range(count)]

    return TicketFactory


@pytest.fixture
def sample_ticket(ticket_factory: type) -> Ticket:
    """Create a sample ticket for tests."""
    return ticket_factory.create()


@pytest.fixture
def sample_ticket_dict() -> dict[str, Any]:
    """Create a sample ticket as dict for API requests."""
    return {
        "source_id": f"SRC-{uuid4().hex[:8]}",
        "source_system": "test-system",
        "title": "Test Ticket Title",
        "description": "This is a test ticket description with enough content.",
        "severity": "medium",
        "product": "test-product",
        "region": "us-east",
    }


# =============================================================================
# Async Utilities
# =============================================================================


@pytest.fixture
def async_iter_factory():
    """Factory for creating async iterators from lists."""

    def create_async_iter(items: list[Any]):
        async def async_gen():
            for item in items:
                yield item

        return async_gen()

    return create_async_iter
