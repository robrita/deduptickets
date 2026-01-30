"""
Contract tests for Clusters API.

Validates that the API implementation matches the OpenAPI specification.
Tests focus on:
- Response schema compliance
- Status codes per spec
- Required fields presence
- Pagination structure
"""

from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.fixture
def sample_cluster() -> dict[str, Any]:
    """Sample cluster data for testing."""
    return {
        "id": str(uuid4()),
        "status": "pending",
        "matching_fields": ["transactionId", "merchant"],
        "ticket_count": 3,
        "confidence_score": 0.85,
        "summary": "3 duplicate tickets for merchant ABC",
        "ticket_ids": [str(uuid4()) for _ in range(3)],
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z",
    }


class TestClustersAPIContract:
    """Contract tests for GET /clusters endpoint."""

    @pytest.mark.asyncio
    async def test_list_clusters_returns_paginated_response(self, client: AsyncClient) -> None:
        """GET /clusters returns proper pagination structure."""
        response = await client.get("/clusters")

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
    async def test_list_clusters_item_schema(
        self, client: AsyncClient, _created_cluster_id: str
    ) -> None:
        """Each cluster item matches expected schema."""
        response = await client.get("/clusters")

        assert response.status_code == 200
        data = response.json()

        if data["items"]:
            cluster = data["items"][0]
            # Required fields per OpenAPI spec
            assert "id" in cluster
            assert "status" in cluster
            assert "matching_fields" in cluster
            assert "ticket_count" in cluster
            assert "confidence_score" in cluster
            assert "created_at" in cluster

            # Status must be valid enum value
            assert cluster["status"] in ["pending", "merged", "dismissed"]

            # Confidence score must be between 0 and 1
            assert 0 <= cluster["confidence_score"] <= 1

    @pytest.mark.asyncio
    async def test_list_clusters_filters_by_status(self, client: AsyncClient) -> None:
        """GET /clusters?status=pending filters correctly."""
        response = await client.get("/clusters", params={"status": "pending"})

        assert response.status_code == 200
        data = response.json()

        # All returned items should have pending status
        for cluster in data["items"]:
            assert cluster["status"] == "pending"

    @pytest.mark.asyncio
    async def test_list_clusters_pagination_params(self, client: AsyncClient) -> None:
        """GET /clusters respects page and page_size params."""
        response = await client.get("/clusters", params={"page": 1, "page_size": 5})

        assert response.status_code == 200
        data = response.json()

        assert data["pagination"]["page"] == 1
        assert data["pagination"]["page_size"] == 5
        assert len(data["items"]) <= 5


class TestClusterDetailAPIContract:
    """Contract tests for GET /clusters/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_cluster_returns_detail(
        self, client: AsyncClient, created_cluster_id: str
    ) -> None:
        """GET /clusters/{id} returns cluster detail."""
        response = await client.get(f"/clusters/{created_cluster_id}")

        assert response.status_code == 200
        data = response.json()

        # Required fields
        assert "id" in data
        assert data["id"] == created_cluster_id
        assert "status" in data
        assert "matching_fields" in data
        assert "ticket_count" in data
        assert "confidence_score" in data
        assert "ticket_ids" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_get_cluster_not_found(self, client: AsyncClient) -> None:
        """GET /clusters/{id} returns 404 for non-existent cluster."""
        fake_id = str(uuid4())
        response = await client.get(f"/clusters/{fake_id}")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


class TestClusterDismissAPIContract:
    """Contract tests for POST /clusters/{id}/dismiss endpoint."""

    @pytest.mark.asyncio
    async def test_dismiss_cluster_returns_updated(
        self, client: AsyncClient, created_cluster_id: str
    ) -> None:
        """POST /clusters/{id}/dismiss updates cluster status."""
        response = await client.post(f"/clusters/{created_cluster_id}/dismiss")

        # May return 200 or 204 depending on implementation
        assert response.status_code in [200, 204]

        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "dismissed"

    @pytest.mark.asyncio
    async def test_dismiss_cluster_not_found(self, client: AsyncClient) -> None:
        """POST /clusters/{id}/dismiss returns 404 for non-existent cluster."""
        fake_id = str(uuid4())
        response = await client.post(f"/clusters/{fake_id}/dismiss")

        assert response.status_code == 404


class TestClusterMemberRemovalAPIContract:
    """Contract tests for DELETE /clusters/{id}/members/{ticket_id} endpoint."""

    @pytest.mark.asyncio
    async def test_remove_member_not_found_cluster(self, client: AsyncClient) -> None:
        """DELETE returns 404 for non-existent cluster."""
        fake_cluster_id = str(uuid4())
        fake_ticket_id = str(uuid4())
        response = await client.delete(f"/clusters/{fake_cluster_id}/members/{fake_ticket_id}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_remove_member_not_found_ticket(
        self, client: AsyncClient, created_cluster_id: str
    ) -> None:
        """DELETE returns 404 for non-existent ticket in cluster."""
        fake_ticket_id = str(uuid4())
        response = await client.delete(f"/clusters/{created_cluster_id}/members/{fake_ticket_id}")

        # Returns 404 or 422 depending on implementation
        assert response.status_code in [404, 422]
