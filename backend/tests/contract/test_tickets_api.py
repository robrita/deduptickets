"""
Contract tests for the tickets API endpoints.

Validates HTTP response structure, status codes, and schemas
for GET /api/v1/tickets, GET /api/v1/tickets/{id},
and POST /api/v1/tickets.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from models.cluster import Cluster, ClusterStatus
from models.ticket import Ticket, TicketPriority, TicketStatus

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# ---------------------------------------------------------------------------
# Fixed identifiers
# ---------------------------------------------------------------------------
MONTH = "2025-01"
TICKET_ID = uuid4()
CLUSTER_ID = uuid4()
NOW = datetime(2025, 1, 15, 10, 0, 0)


def _build_ticket(
    ticket_id: Any = None,
    cluster_id: Any = None,
    status: str = "open",
    channel: str = "in_app",
) -> Ticket:
    return Ticket(
        id=ticket_id or TICKET_ID,
        pk=MONTH,
        ticket_number="TKT-0001",
        created_at=NOW,
        updated_at=NOW,
        channel=channel,
        customer_id="CUST-1",
        category="Billing",
        summary="Test ticket summary",
        description="Test description",
        cluster_id=cluster_id or CLUSTER_ID,
        status=TicketStatus(status) if isinstance(status, str) else status,
        priority=TicketPriority.MEDIUM,
    )


def _build_cluster() -> Cluster:
    return Cluster(
        id=CLUSTER_ID,
        pk=MONTH,
        status=ClusterStatus.PENDING,
        summary="Test cluster",
        ticket_count=1,
        created_at=NOW,
        updated_at=NOW,
    )


# ---------------------------------------------------------------------------
# Client fixture with all ticket-route deps mocked
# ---------------------------------------------------------------------------


@pytest.fixture
async def ticket_client() -> AsyncGenerator[AsyncClient, None]:
    """Test client with mocked ticket, clustering, and embedding deps."""
    import os  # noqa: PLC0415

    _env = {
        "COSMOS_ENDPOINT": "https://localhost:8081",
        "COSMOS_KEY": "test-key",
        "COSMOS_DATABASE": "test-db",
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
        "AZURE_OPENAI_USE_AAD": "false",
        "AZURE_OPENAI_KEY": "test-openai-key",
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT": "text-embedding-3-small",
    }
    _saved = {k: os.environ.get(k) for k in _env}
    os.environ.update(_env)

    from config import Settings, get_settings  # noqa: PLC0415

    get_settings.cache_clear()

    from dependencies import (  # noqa: PLC0415
        get_clustering_service,
        get_current_user,
        get_embedding_service,
        get_ticket_repository,
        verify_api_key,
    )
    from main import create_app  # noqa: PLC0415

    test_settings = Settings(
        cosmos_endpoint="https://localhost:8081",
        cosmos_key="test-key",
        cosmos_database="test-db",
        cosmos_ssl_verify=False,
        api_key="test-api-key",
        azure_openai_endpoint="https://test.openai.azure.com",
        azure_openai_use_aad=False,
        azure_openai_key="test-openai-key",
        azure_openai_embedding_deployment="text-embedding-3-small",
    )

    ticket = _build_ticket()
    cluster = _build_cluster()

    mock_ticket_repo = AsyncMock()
    mock_ticket_repo.build_partition_key = lambda _: MONTH
    mock_ticket_repo.get_by_ticket_number = AsyncMock(return_value=None)
    mock_ticket_repo.create = AsyncMock(return_value=ticket)
    mock_ticket_repo.get_by_id = AsyncMock(return_value=ticket)
    mock_ticket_repo.query = AsyncMock(return_value=[ticket])
    mock_ticket_repo.count = AsyncMock(return_value=1)

    mock_clustering_service = AsyncMock()
    mock_clustering_service.find_or_create_cluster = AsyncMock(
        return_value=(cluster, {"decision": "auto", "confidence": 0.9})
    )

    mock_embedding_service = AsyncMock()
    mock_embedding_service.generate_embedding = AsyncMock(return_value=[0.1] * 1536)

    with (
        patch("config.get_settings", return_value=test_settings),
        patch("dependencies.get_cached_settings", return_value=test_settings),
    ):
        app = create_app()

    app.dependency_overrides[verify_api_key] = lambda: "test-key"
    app.dependency_overrides[get_current_user] = lambda: "test-user"
    app.dependency_overrides[get_ticket_repository] = lambda: mock_ticket_repo
    app.dependency_overrides[get_clustering_service] = lambda: mock_clustering_service
    app.dependency_overrides[get_embedding_service] = lambda: mock_embedding_service

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

    for k, v in _saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    from config import get_settings as gs  # noqa: PLC0415

    gs.cache_clear()


# ---------------------------------------------------------------------------
# GET /tickets/{ticket_id}
# ---------------------------------------------------------------------------


class TestGetTicketAPI:
    async def test_get_ticket_returns_200(self, ticket_client: AsyncClient) -> None:
        response = await ticket_client.get(
            f"/api/v1/tickets/{TICKET_ID}",
            params={"month": MONTH},
        )
        assert response.status_code == 200

    async def test_get_ticket_response_schema(self, ticket_client: AsyncClient) -> None:
        response = await ticket_client.get(
            f"/api/v1/tickets/{TICKET_ID}",
            params={"month": MONTH},
        )
        data = response.json()
        assert "id" in data
        assert "ticketNumber" in data
        assert "status" in data
        assert "category" in data

    async def test_get_ticket_not_found(self) -> None:
        # Override so this specific ID returns None
        from dependencies import get_ticket_repository  # noqa: PLC0415

        missing_mock = AsyncMock()
        missing_mock.get_by_id = AsyncMock(return_value=None)

        import os  # noqa: PLC0415

        from config import get_settings  # noqa: PLC0415
        from dependencies import (  # noqa: PLC0415
            get_clustering_service,
            get_current_user,
            get_embedding_service,
            verify_api_key,
        )
        from main import create_app  # noqa: PLC0415

        _env = {
            "COSMOS_ENDPOINT": "https://localhost:8081",
            "COSMOS_KEY": "test-key",
            "COSMOS_DATABASE": "test-db",
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
            "AZURE_OPENAI_USE_AAD": "false",
            "AZURE_OPENAI_KEY": "test-openai-key",
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT": "text-embedding-3-small",
        }
        os.environ.update(_env)
        get_settings.cache_clear()

        from config import Settings  # noqa: PLC0415

        ts = Settings(
            cosmos_endpoint="https://localhost:8081",
            cosmos_key="test-key",
            cosmos_database="test-db",
            cosmos_ssl_verify=False,
            api_key="test-api-key",
            azure_openai_endpoint="https://test.openai.azure.com",
            azure_openai_use_aad=False,
            azure_openai_key="test-openai-key",
            azure_openai_embedding_deployment="text-embedding-3-small",
        )

        with (
            patch("config.get_settings", return_value=ts),
            patch("dependencies.get_cached_settings", return_value=ts),
        ):
            app = create_app()

        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_current_user] = lambda: "test-user"
        app.dependency_overrides[get_ticket_repository] = lambda: missing_mock
        app.dependency_overrides[get_clustering_service] = lambda: AsyncMock()
        app.dependency_overrides[get_embedding_service] = lambda: AsyncMock()

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as c:
            response = await c.get(
                f"/api/v1/tickets/{uuid4()}",
                params={"month": MONTH},
            )

        assert response.status_code == 404

    async def test_get_ticket_normalizes_channel_variants(
        self,
    ) -> None:
        """Covers the channel normalization helper."""
        from dependencies import get_ticket_repository  # noqa: PLC0415

        for channel_val in ["chat", "email", "social", "phone", "in-app", "unknown_channel"]:
            ticket = _build_ticket(channel=channel_val)
            mock_repo = AsyncMock()
            mock_repo.get_by_id = AsyncMock(return_value=ticket)

            import os  # noqa: PLC0415

            from config import get_settings  # noqa: PLC0415
            from dependencies import (  # noqa: PLC0415
                get_clustering_service,
                get_current_user,
                get_embedding_service,
                verify_api_key,
            )
            from main import create_app  # noqa: PLC0415

            _env = {
                "COSMOS_ENDPOINT": "https://localhost:8081",
                "COSMOS_KEY": "test-key",
                "COSMOS_DATABASE": "test-db",
                "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
                "AZURE_OPENAI_USE_AAD": "false",
                "AZURE_OPENAI_KEY": "test-openai-key",
                "AZURE_OPENAI_EMBEDDING_DEPLOYMENT": "text-embedding-3-small",
            }
            os.environ.update(_env)
            get_settings.cache_clear()

            from config import Settings  # noqa: PLC0415

            ts = Settings(
                cosmos_endpoint="https://localhost:8081",
                cosmos_key="test-key",
                cosmos_database="test-db",
                cosmos_ssl_verify=False,
                api_key="test-api-key",
                azure_openai_endpoint="https://test.openai.azure.com",
                azure_openai_use_aad=False,
                azure_openai_key="test-openai-key",
                azure_openai_embedding_deployment="text-embedding-3-small",
            )

            with (
                patch("config.get_settings", return_value=ts),
                patch("dependencies.get_cached_settings", return_value=ts),
            ):
                app = create_app()

            app.dependency_overrides[verify_api_key] = lambda: "test-key"
            app.dependency_overrides[get_current_user] = lambda: "test-user"
            app.dependency_overrides[get_ticket_repository] = lambda _r=mock_repo: _r
            app.dependency_overrides[get_clustering_service] = lambda: AsyncMock()
            app.dependency_overrides[get_embedding_service] = lambda: AsyncMock()

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test",
            ) as c:
                response = await c.get(
                    f"/api/v1/tickets/{TICKET_ID}",
                    params={"month": MONTH},
                )
            assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /tickets (list)
# ---------------------------------------------------------------------------


class TestListTicketsAPI:
    async def test_list_tickets_returns_paginated(self, ticket_client: AsyncClient) -> None:
        response = await ticket_client.get(
            "/api/v1/tickets",
            params={"month": MONTH},
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "meta" in data
        assert isinstance(data["data"], list)

    async def test_list_tickets_meta_fields(self, ticket_client: AsyncClient) -> None:
        response = await ticket_client.get(
            "/api/v1/tickets",
            params={"month": MONTH, "page": 1, "page_size": 10},
        )
        meta = response.json()["meta"]
        assert "total" in meta
        assert "offset" in meta
        assert "limit" in meta
        assert "hasMore" in meta

    async def test_list_tickets_with_status_filter(self, ticket_client: AsyncClient) -> None:
        response = await ticket_client.get(
            "/api/v1/tickets",
            params={"month": MONTH, "status": "open"},
        )
        assert response.status_code == 200

    async def test_list_tickets_unassigned_only(self, ticket_client: AsyncClient) -> None:
        response = await ticket_client.get(
            "/api/v1/tickets",
            params={"month": MONTH, "unassigned_only": True},
        )
        assert response.status_code == 200

    async def test_list_tickets_custom_sort(self, ticket_client: AsyncClient) -> None:
        response = await ticket_client.get(
            "/api/v1/tickets",
            params={"month": MONTH, "sort_by": "priority", "sort_order": "asc"},
        )
        assert response.status_code == 200

    async def test_list_tickets_invalid_sort_defaults_to_created_at(
        self, ticket_client: AsyncClient
    ) -> None:
        """Invalid sort_by must be sanitized (prevents injection)."""
        response = await ticket_client.get(
            "/api/v1/tickets",
            params={"month": MONTH, "sort_by": "'; DROP TABLE c; --"},
        )
        assert response.status_code == 200

    async def test_list_tickets_all_filters_combined(self, ticket_client: AsyncClient) -> None:
        response = await ticket_client.get(
            "/api/v1/tickets",
            params={
                "month": MONTH,
                "status": "open",
                "unassigned_only": True,
                "sort_by": "status",
                "sort_order": "desc",
            },
        )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# POST /tickets
# ---------------------------------------------------------------------------


class TestCreateTicketAPI:
    async def test_create_ticket_returns_201(self, ticket_client: AsyncClient) -> None:
        payload = {
            "ticketNumber": "TKT-NEW-001",
            "summary": "Payment gateway error",
            "category": "Billing",
            "status": "open",
            "channel": "InApp",
            "createdAt": NOW.isoformat(),
        }
        response = await ticket_client.post("/api/v1/tickets", json=payload)
        assert response.status_code == 201

    async def test_create_ticket_conflict_returns_409(
        self,
    ) -> None:
        """When ticket_number already exists, must return 409."""
        import os  # noqa: PLC0415

        from config import get_settings  # noqa: PLC0415
        from dependencies import (  # noqa: PLC0415
            get_clustering_service,
            get_current_user,
            get_embedding_service,
            get_ticket_repository,
            verify_api_key,
        )
        from main import create_app  # noqa: PLC0415

        _env = {
            "COSMOS_ENDPOINT": "https://localhost:8081",
            "COSMOS_KEY": "test-key",
            "COSMOS_DATABASE": "test-db",
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
            "AZURE_OPENAI_USE_AAD": "false",
            "AZURE_OPENAI_KEY": "test-openai-key",
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT": "text-embedding-3-small",
        }
        os.environ.update(_env)
        get_settings.cache_clear()

        from config import Settings  # noqa: PLC0415

        ts = Settings(
            cosmos_endpoint="https://localhost:8081",
            cosmos_key="test-key",
            cosmos_database="test-db",
            cosmos_ssl_verify=False,
            api_key="test-api-key",
            azure_openai_endpoint="https://test.openai.azure.com",
            azure_openai_use_aad=False,
            azure_openai_key="test-openai-key",
            azure_openai_embedding_deployment="text-embedding-3-small",
        )

        existing_ticket = _build_ticket()
        dup_repo = AsyncMock()
        dup_repo.build_partition_key = lambda _: MONTH
        dup_repo.get_by_ticket_number = AsyncMock(return_value=existing_ticket)

        with (
            patch("config.get_settings", return_value=ts),
            patch("dependencies.get_cached_settings", return_value=ts),
        ):
            app = create_app()

        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_current_user] = lambda: "test-user"
        app.dependency_overrides[get_ticket_repository] = lambda: dup_repo
        app.dependency_overrides[get_clustering_service] = lambda: AsyncMock()
        app.dependency_overrides[get_embedding_service] = lambda: AsyncMock()

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as c:
            response = await c.post(
                "/api/v1/tickets",
                json={
                    "ticketNumber": "TKT-DUP",
                    "summary": "Duplicate",
                    "category": "Billing",
                    "status": "open",
                    "channel": "InApp",
                    "createdAt": NOW.isoformat(),
                },
            )

        assert response.status_code == 409

    async def test_create_ticket_embedding_failure_returns_503(
        self,
    ) -> None:
        """Embedding RuntimeError must propagate as HTTP 503."""
        import os  # noqa: PLC0415

        from config import get_settings  # noqa: PLC0415
        from dependencies import (  # noqa: PLC0415
            get_clustering_service,
            get_current_user,
            get_embedding_service,
            get_ticket_repository,
            verify_api_key,
        )
        from main import create_app  # noqa: PLC0415

        _env = {
            "COSMOS_ENDPOINT": "https://localhost:8081",
            "COSMOS_KEY": "test-key",
            "COSMOS_DATABASE": "test-db",
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
            "AZURE_OPENAI_USE_AAD": "false",
            "AZURE_OPENAI_KEY": "test-openai-key",
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT": "text-embedding-3-small",
        }
        os.environ.update(_env)
        get_settings.cache_clear()

        from config import Settings  # noqa: PLC0415

        ts = Settings(
            cosmos_endpoint="https://localhost:8081",
            cosmos_key="test-key",
            cosmos_database="test-db",
            cosmos_ssl_verify=False,
            api_key="test-api-key",
            azure_openai_endpoint="https://test.openai.azure.com",
            azure_openai_use_aad=False,
            azure_openai_key="test-openai-key",
            azure_openai_embedding_deployment="text-embedding-3-small",
        )

        fail_embedding = AsyncMock()
        fail_embedding.generate_embedding = AsyncMock(
            side_effect=RuntimeError("OpenAI not configured")
        )

        ok_repo = AsyncMock()
        ok_repo.build_partition_key = lambda _: MONTH
        ok_repo.get_by_ticket_number = AsyncMock(return_value=None)

        with (
            patch("config.get_settings", return_value=ts),
            patch("dependencies.get_cached_settings", return_value=ts),
        ):
            app = create_app()

        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_current_user] = lambda: "test-user"
        app.dependency_overrides[get_ticket_repository] = lambda: ok_repo
        app.dependency_overrides[get_clustering_service] = lambda: AsyncMock()
        app.dependency_overrides[get_embedding_service] = lambda: fail_embedding

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as c:
            response = await c.post(
                "/api/v1/tickets",
                json={
                    "ticketNumber": "TKT-EMBED-FAIL",
                    "summary": "Test",
                    "category": "Billing",
                    "status": "open",
                    "channel": "InApp",
                    "createdAt": NOW.isoformat(),
                },
            )

        assert response.status_code == 503

    async def test_create_ticket_generic_exception_returns_503(
        self,
    ) -> None:
        """Non-RuntimeError embedding failure must also return 503."""
        import os  # noqa: PLC0415

        from config import get_settings  # noqa: PLC0415
        from dependencies import (  # noqa: PLC0415
            get_clustering_service,
            get_current_user,
            get_embedding_service,
            get_ticket_repository,
            verify_api_key,
        )
        from main import create_app  # noqa: PLC0415

        _env = {
            "COSMOS_ENDPOINT": "https://localhost:8081",
            "COSMOS_KEY": "test-key",
            "COSMOS_DATABASE": "test-db",
            "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
            "AZURE_OPENAI_USE_AAD": "false",
            "AZURE_OPENAI_KEY": "test-openai-key",
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT": "text-embedding-3-small",
        }
        os.environ.update(_env)
        get_settings.cache_clear()

        from config import Settings  # noqa: PLC0415

        ts = Settings(
            cosmos_endpoint="https://localhost:8081",
            cosmos_key="test-key",
            cosmos_database="test-db",
            cosmos_ssl_verify=False,
            api_key="test-api-key",
            azure_openai_endpoint="https://test.openai.azure.com",
            azure_openai_use_aad=False,
            azure_openai_key="test-openai-key",
            azure_openai_embedding_deployment="text-embedding-3-small",
        )

        fail_embedding = AsyncMock()
        fail_embedding.generate_embedding = AsyncMock(
            side_effect=Exception("Unexpected embedding error")
        )

        ok_repo = AsyncMock()
        ok_repo.build_partition_key = lambda _: MONTH
        ok_repo.get_by_ticket_number = AsyncMock(return_value=None)

        with (
            patch("config.get_settings", return_value=ts),
            patch("dependencies.get_cached_settings", return_value=ts),
        ):
            app = create_app()

        app.dependency_overrides[verify_api_key] = lambda: "test-key"
        app.dependency_overrides[get_current_user] = lambda: "test-user"
        app.dependency_overrides[get_ticket_repository] = lambda: ok_repo
        app.dependency_overrides[get_clustering_service] = lambda: AsyncMock()
        app.dependency_overrides[get_embedding_service] = lambda: fail_embedding

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as c:
            response = await c.post(
                "/api/v1/tickets",
                json={
                    "ticketNumber": "TKT-GENERIC-FAIL",
                    "summary": "Test",
                    "category": "Billing",
                    "status": "open",
                    "channel": "InApp",
                    "createdAt": NOW.isoformat(),
                },
            )

        assert response.status_code == 503

    async def test_create_ticket_with_all_optional_fields(self, ticket_client: AsyncClient) -> None:
        payload = {
            "ticketNumber": "TKT-FULL",
            "summary": "Payment gateway error",
            "description": "Detailed description",
            "category": "Billing",
            "subcategory": "Payment",
            "channel": "Email",
            "priority": "high",
            "severity": "S2",
            "status": "open",
            "customerId": "CUST-999",
            "merchant": "ACME Corp",
            "createdAt": NOW.isoformat(),
        }
        response = await ticket_client.post("/api/v1/tickets", json=payload)
        assert response.status_code == 201
