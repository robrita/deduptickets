"""
Contract tests for Clusters API.

Validates that the API implementation matches the actual response schemas.
Tests focus on:
- Response schema compliance
- Status codes per spec
- Required fields presence
- Pagination structure
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

MONTH = "2025-01"


class TestClustersAPIContract:
    """Contract tests for GET /api/v1/clusters endpoint."""

    @pytest.mark.asyncio
    async def test_list_clusters_returns_paginated_response(self, client: AsyncClient) -> None:
        """GET /api/v1/clusters returns proper pagination structure."""
        response = await client.get("/api/v1/clusters", params={"month": MONTH})

        assert response.status_code == 200
        data = response.json()

        # Response wraps items under "data" with "meta" for pagination
        assert "data" in data
        assert isinstance(data["data"], list)
        assert "meta" in data

        meta = data["meta"]
        assert "total" in meta
        assert "offset" in meta
        assert "limit" in meta
        assert "hasMore" in meta

    @pytest.mark.asyncio
    async def test_list_clusters_item_schema(
        self, client: AsyncClient, _created_cluster_id: str
    ) -> None:
        """Each cluster item matches expected schema."""
        response = await client.get("/api/v1/clusters", params={"month": MONTH})

        assert response.status_code == 200
        data = response.json()

        if data["data"]:
            cluster = data["data"][0]
            # Required fields per ClusterResponse schema
            assert "id" in cluster
            assert "status" in cluster
            assert "summary" in cluster
            assert "ticketCount" in cluster
            assert "createdAt" in cluster

            # Status must be valid enum value
            assert cluster["status"] in ["pending", "merged", "dismissed", "expired"]

    @pytest.mark.asyncio
    async def test_list_clusters_filters_by_status(self, client: AsyncClient) -> None:
        """GET /api/v1/clusters?status=pending filters correctly."""
        response = await client.get(
            "/api/v1/clusters", params={"status": "pending", "month": MONTH}
        )

        assert response.status_code == 200
        data = response.json()

        # All returned items should have pending status
        for cluster in data["data"]:
            assert cluster["status"] == "pending"

    @pytest.mark.asyncio
    async def test_list_clusters_pagination_params(self, client: AsyncClient) -> None:
        """GET /api/v1/clusters respects page and page_size params."""
        response = await client.get(
            "/api/v1/clusters", params={"page": 1, "page_size": 5, "month": MONTH}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["meta"]["limit"] == 5
        assert len(data["data"]) <= 5


class TestClusterDetailAPIContract:
    """Contract tests for GET /api/v1/clusters/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_cluster_returns_detail(
        self, client: AsyncClient, created_cluster_id: str
    ) -> None:
        """GET /api/v1/clusters/{id} returns cluster detail."""
        response = await client.get(
            f"/api/v1/clusters/{created_cluster_id}", params={"month": MONTH}
        )

        assert response.status_code == 200
        data = response.json()

        # Required fields per ClusterDetail schema
        assert "id" in data
        assert data["id"] == created_cluster_id
        assert "status" in data
        assert "summary" in data
        assert "ticketCount" in data
        assert "createdAt" in data
        assert "members" in data

    @pytest.mark.asyncio
    async def test_get_cluster_not_found(self, client: AsyncClient) -> None:
        """GET /api/v1/clusters/{id} returns 404 for non-existent cluster."""
        fake_id = str(uuid4())
        response = await client.get(f"/api/v1/clusters/{fake_id}", params={"month": MONTH})

        assert response.status_code == 404
        data = response.json()
        assert "message" in data


class TestClusterDismissAPIContract:
    """Contract tests for POST /api/v1/clusters/{id}/dismiss endpoint."""

    @pytest.mark.asyncio
    async def test_dismiss_cluster_returns_updated(
        self, client: AsyncClient, created_cluster_id: str
    ) -> None:
        """POST /api/v1/clusters/{id}/dismiss updates cluster status."""
        response = await client.post(
            f"/api/v1/clusters/{created_cluster_id}/dismiss",
            params={"month": MONTH},
            json={"reason": "Not a real duplicate"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "dismissed"

    @pytest.mark.asyncio
    async def test_dismiss_cluster_not_found(self, client: AsyncClient) -> None:
        """POST /api/v1/clusters/{id}/dismiss returns 404 for non-existent cluster."""
        fake_id = str(uuid4())
        response = await client.post(
            f"/api/v1/clusters/{fake_id}/dismiss",
            params={"month": MONTH},
            json={"reason": "test"},
        )

        assert response.status_code == 404


class TestClusterMemberRemovalAPIContract:
    """Contract tests for DELETE /api/v1/clusters/{id}/members/{ticket_id} endpoint."""

    @pytest.mark.asyncio
    async def test_remove_member_not_found_cluster(self, client: AsyncClient) -> None:
        """DELETE returns 404 for non-existent cluster."""
        fake_cluster_id = str(uuid4())
        fake_ticket_id = str(uuid4())
        response = await client.delete(
            f"/api/v1/clusters/{fake_cluster_id}/members/{fake_ticket_id}",
            params={"month": MONTH},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_remove_member_not_found_ticket(
        self, client: AsyncClient, created_cluster_id: str
    ) -> None:
        """DELETE returns 400 for ticket not in cluster."""
        fake_ticket_id = str(uuid4())
        response = await client.delete(
            f"/api/v1/clusters/{created_cluster_id}/members/{fake_ticket_id}",
            params={"month": MONTH},
        )

        assert response.status_code == 400
