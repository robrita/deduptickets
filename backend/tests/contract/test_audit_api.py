"""
Contract tests for Audit API.

Validates that the API implementation matches the OpenAPI specification.
Tests focus on:
- Response schema compliance
- Search/filter capabilities
- Date range filtering
- Pagination structure
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.fixture
def sample_audit_entry() -> dict[str, Any]:
    """Sample audit entry data for testing."""
    return {
        "id": str(uuid4()),
        "action": "MERGE_EXECUTED",
        "entity_type": "cluster",
        "entity_id": str(uuid4()),
        "actor_id": "user@example.com",
        "timestamp": datetime.now(UTC).isoformat(),
        "changes": {"status": {"before": "pending", "after": "merged"}},
        "metadata": {"ip_address": "192.168.1.1"},
    }


class TestAuditListAPIContract:
    """Contract tests for GET /audit endpoint."""

    @pytest.mark.asyncio
    async def test_list_audit_returns_paginated_response(self, client: AsyncClient) -> None:
        """GET /audit returns proper pagination structure."""
        response = await client.get("/audit")

        assert response.status_code == 200
        data = response.json()

        # Verify pagination structure
        assert "items" in data
        assert isinstance(data["items"], list)
        assert "pagination" in data

        pagination = data["pagination"]
        assert "page" in pagination
        assert "page_size" in pagination
        assert "total_items" in pagination
        assert "total_pages" in pagination

    @pytest.mark.asyncio
    async def test_list_audit_item_schema(
        self, client: AsyncClient, _created_audit_entry_id: str
    ) -> None:
        """Each audit item matches expected schema."""
        response = await client.get("/audit")

        assert response.status_code == 200
        data = response.json()

        if data["items"]:
            entry = data["items"][0]
            # Required fields per OpenAPI spec
            assert "id" in entry
            assert "action" in entry
            assert "entity_type" in entry
            assert "entity_id" in entry
            assert "timestamp" in entry

            # Action must be valid enum value
            valid_actions = [
                "CLUSTER_CREATED",
                "CLUSTER_DISMISSED",
                "MERGE_EXECUTED",
                "MERGE_REVERTED",
                "TICKET_CREATED",
                "TICKET_UPDATED",
                "SPIKE_DETECTED",
                "SPIKE_ACKNOWLEDGED",
                "SPIKE_RESOLVED",
            ]
            assert entry["action"] in valid_actions

    @pytest.mark.asyncio
    async def test_list_audit_filters_by_action(self, client: AsyncClient) -> None:
        """GET /audit?action=MERGE_EXECUTED filters correctly."""
        response = await client.get("/audit", params={"action": "MERGE_EXECUTED"})

        assert response.status_code == 200
        data = response.json()

        # All returned items should have matching action
        for entry in data["items"]:
            assert entry["action"] == "MERGE_EXECUTED"

    @pytest.mark.asyncio
    async def test_list_audit_filters_by_entity_type(self, client: AsyncClient) -> None:
        """GET /audit?entity_type=cluster filters correctly."""
        response = await client.get("/audit", params={"entity_type": "cluster"})

        assert response.status_code == 200
        data = response.json()

        # All returned items should have matching entity_type
        for entry in data["items"]:
            assert entry["entity_type"] == "cluster"

    @pytest.mark.asyncio
    async def test_list_audit_date_range_filter(self, client: AsyncClient) -> None:
        """GET /audit respects start_date and end_date params."""
        now = datetime.now(UTC)
        start_date = (now - timedelta(days=7)).isoformat()
        end_date = now.isoformat()

        response = await client.get(
            "/audit",
            params={"start_date": start_date, "end_date": end_date},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all entries are within date range
        for entry in data["items"]:
            entry_date = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
            assert entry_date >= datetime.fromisoformat(start_date)
            assert entry_date <= datetime.fromisoformat(end_date)


class TestAuditDetailAPIContract:
    """Contract tests for GET /audit/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_audit_entry_returns_detail(
        self, client: AsyncClient, created_audit_entry_id: str
    ) -> None:
        """GET /audit/{id} returns audit entry detail."""
        response = await client.get(f"/audit/{created_audit_entry_id}")

        assert response.status_code == 200
        data = response.json()

        # Required fields
        assert "id" in data
        assert data["id"] == created_audit_entry_id
        assert "action" in data
        assert "entity_type" in data
        assert "entity_id" in data
        assert "timestamp" in data

        # Optional fields that should be present in detail view
        if "changes" in data:
            assert isinstance(data["changes"], dict)
        if "metadata" in data:
            assert isinstance(data["metadata"], dict)

    @pytest.mark.asyncio
    async def test_get_audit_entry_not_found(self, client: AsyncClient) -> None:
        """GET /audit/{id} returns 404 for non-existent entry."""
        fake_id = str(uuid4())
        response = await client.get(f"/audit/{fake_id}")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


class TestAuditEntityAPIContract:
    """Contract tests for GET /audit/entity/{type}/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_entity_audit_trail(
        self, client: AsyncClient, created_cluster_id: str
    ) -> None:
        """GET /audit/entity/{type}/{id} returns entity's audit history."""
        response = await client.get(f"/audit/entity/cluster/{created_cluster_id}")

        assert response.status_code == 200
        data = response.json()

        # Should return list or paginated response
        if isinstance(data, list):
            for entry in data:
                assert entry["entity_type"] == "cluster"
                assert entry["entity_id"] == created_cluster_id
        else:
            # Paginated response
            assert "items" in data
            for entry in data["items"]:
                assert entry["entity_type"] == "cluster"
                assert entry["entity_id"] == created_cluster_id

    @pytest.mark.asyncio
    async def test_get_entity_audit_empty(self, client: AsyncClient) -> None:
        """GET /audit/entity/{type}/{id} returns empty for non-existent entity."""
        fake_id = str(uuid4())
        response = await client.get(f"/audit/entity/cluster/{fake_id}")

        assert response.status_code == 200
        data = response.json()

        if isinstance(data, list):
            assert len(data) == 0
        else:
            assert data["items"] == []


class TestAuditSearchAPIContract:
    """Contract tests for POST /audit/search endpoint."""

    @pytest.mark.asyncio
    async def test_search_audit_with_query(self, client: AsyncClient) -> None:
        """POST /audit/search supports advanced search criteria."""
        search_params = {
            "entity_type": "cluster",
            "actions": ["MERGE_EXECUTED", "MERGE_REVERTED"],
            "start_date": (datetime.now(UTC) - timedelta(days=30)).isoformat(),
        }

        response = await client.post("/audit/search", json=search_params)

        assert response.status_code == 200
        data = response.json()

        assert "items" in data
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_search_audit_validates_params(self, client: AsyncClient) -> None:
        """POST /audit/search validates search parameters."""
        # Invalid date format
        response = await client.post(
            "/audit/search",
            json={"start_date": "invalid-date"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_search_audit_multiple_actions(self, client: AsyncClient) -> None:
        """POST /audit/search can filter by multiple actions."""
        search_params = {
            "actions": ["CLUSTER_CREATED", "CLUSTER_DISMISSED"],
        }

        response = await client.post("/audit/search", json=search_params)

        assert response.status_code == 200
        data = response.json()

        # All results should have one of the specified actions
        for entry in data["items"]:
            assert entry["action"] in ["CLUSTER_CREATED", "CLUSTER_DISMISSED"]
