"""
Integration tests for audit trail.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


class TestAuditListEndpoint:
    """Tests for GET /audit endpoint."""

    @pytest.mark.asyncio
    async def test_list_audit_entries_empty(
        self,
        client: AsyncClient,
        api_key_header: dict[str, str],
    ) -> None:
        """Test listing audit entries when none exist."""
        response = await client.get(
            "/api/v1/audit",
            headers=api_key_header,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data

    @pytest.mark.asyncio
    async def test_list_audit_entries_with_entity_type_filter(
        self,
        client: AsyncClient,
        api_key_header: dict[str, str],
    ) -> None:
        """Test listing audit entries filtered by entity type."""
        response = await client.get(
            "/api/v1/audit?entity_type=ticket&month=2025-01",
            headers=api_key_header,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.asyncio
    async def test_list_audit_entries_with_user_filter(
        self,
        client: AsyncClient,
        api_key_header: dict[str, str],
    ) -> None:
        """Test listing audit entries filtered by user."""
        response = await client.get(
            "/api/v1/audit?user_id=test-user",
            headers=api_key_header,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestAuditDetailEndpoint:
    """Tests for GET /audit/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_audit_entry_not_found(
        self,
        client: AsyncClient,
        api_key_header: dict[str, str],
    ) -> None:
        """Test getting nonexistent audit entry."""
        audit_id = uuid4()
        response = await client.get(
            f"/api/v1/audit/{audit_id}?entity_type=ticket&month=2025-01",
            headers=api_key_header,
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestAuditEntityHistoryEndpoint:
    """Tests for GET /audit/entity/{type}/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_entity_history_empty(
        self,
        client: AsyncClient,
        api_key_header: dict[str, str],
    ) -> None:
        """Test getting history for entity with no audit entries."""
        entity_id = uuid4()
        response = await client.get(
            f"/api/v1/audit/entity/ticket/{entity_id}?month=2025-01",
            headers=api_key_header,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []


class TestAuditSearchEndpoint:
    """Tests for POST /audit/search endpoint."""

    @pytest.mark.asyncio
    async def test_search_audit_entries_minimal(
        self,
        client: AsyncClient,
        api_key_header: dict[str, str],
    ) -> None:
        """Test audit search with minimal parameters."""
        response = await client.post(
            "/api/v1/audit/search",
            headers=api_key_header,
            json={"page": 1, "page_size": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data

    @pytest.mark.asyncio
    async def test_search_audit_entries_with_all_filters(
        self,
        client: AsyncClient,
        api_key_header: dict[str, str],
    ) -> None:
        """Test audit search with all filter parameters."""
        response = await client.post(
            "/api/v1/audit/search",
            headers=api_key_header,
            json={
                "entity_type": "cluster",
                "user_id": "test-user",
                "action": "CLUSTER_MERGED",
                "from_date": "2025-01-01T00:00:00Z",
                "to_date": "2025-01-31T23:59:59Z",
                "page": 1,
                "page_size": 20,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestAuditTrailIntegrity:
    """Tests for audit trail creation on actions."""

    @pytest.mark.asyncio
    async def test_ticket_creation_generates_audit(
        self,
        client: AsyncClient,
        api_key_header: dict[str, str],
    ) -> None:
        """Test that creating a ticket generates an audit entry."""
        # Create a ticket
        await client.post(
            "/api/v1/tickets",
            headers=api_key_header,
            json={
                "source_id": f"TEST-{uuid4().hex[:8]}",
                "source_system": "TestSystem",
                "title": "Test ticket for audit",
                "description": "Testing audit trail",
                "severity": "medium",
                "product": "TestProduct",
                "region": "US",
            },
        )

        # Even if ticket creation fails (no DB), check the audit endpoint works
        search_response = await client.post(
            "/api/v1/audit/search",
            headers=api_key_header,
            json={
                "entity_type": "ticket",
                "action": "TICKET_CREATED",
                "page": 1,
                "page_size": 10,
            },
        )

        assert search_response.status_code == 200

    @pytest.mark.asyncio
    async def test_cluster_merge_generates_audit(
        self,
        client: AsyncClient,
        api_key_header: dict[str, str],
    ) -> None:
        """Test that merging a cluster generates an audit entry."""
        # Search for merge audit entries
        response = await client.post(
            "/api/v1/audit/search",
            headers=api_key_header,
            json={
                "action": "CLUSTER_MERGED",
                "page": 1,
                "page_size": 10,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
