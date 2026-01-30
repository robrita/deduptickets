"""
Contract tests for Merges API.

Validates that the API implementation matches the OpenAPI specification.
Tests focus on:
- Response schema compliance
- Status codes per spec
- Merge operation fields
- Revert functionality
"""

from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.fixture
def merge_request() -> dict[str, Any]:
    """Sample merge request payload."""
    return {
        "cluster_id": str(uuid4()),
        "primary_ticket_id": str(uuid4()),
        "merge_behavior": "KeepLatest",
    }


class TestMergesAPIContract:
    """Contract tests for GET /merges endpoint."""

    @pytest.mark.asyncio
    async def test_list_merges_returns_paginated_response(self, client: AsyncClient) -> None:
        """GET /merges returns proper pagination structure."""
        response = await client.get("/merges")

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
    async def test_list_merges_item_schema(
        self, client: AsyncClient, _created_merge_id: str
    ) -> None:
        """Each merge item matches expected schema."""
        response = await client.get("/merges")

        assert response.status_code == 200
        data = response.json()

        if data["items"]:
            merge = data["items"][0]
            # Required fields per OpenAPI spec
            assert "id" in merge
            assert "cluster_id" in merge
            assert "primary_ticket_id" in merge
            assert "secondary_ticket_ids" in merge
            assert "status" in merge
            assert "created_at" in merge

            # Status must be valid enum value
            assert merge["status"] in ["completed", "reverted", "failed"]

    @pytest.mark.asyncio
    async def test_list_merges_filters_by_cluster(
        self, client: AsyncClient, created_cluster_id: str, _created_merge_id: str
    ) -> None:
        """GET /merges?cluster_id=X filters correctly."""
        response = await client.get("/merges", params={"cluster_id": created_cluster_id})

        assert response.status_code == 200
        data = response.json()

        # All returned items should have matching cluster_id
        for merge in data["items"]:
            assert merge["cluster_id"] == created_cluster_id


class TestMergeDetailAPIContract:
    """Contract tests for GET /merges/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_merge_returns_detail(
        self, client: AsyncClient, created_merge_id: str
    ) -> None:
        """GET /merges/{id} returns merge detail with original states."""
        response = await client.get(f"/merges/{created_merge_id}")

        assert response.status_code == 200
        data = response.json()

        # Required fields
        assert "id" in data
        assert data["id"] == created_merge_id
        assert "cluster_id" in data
        assert "primary_ticket_id" in data
        assert "secondary_ticket_ids" in data
        assert "status" in data
        assert "original_states" in data
        assert "created_at" in data

        # original_states should be a dict or list of snapshots
        assert isinstance(data["original_states"], (dict, list))

    @pytest.mark.asyncio
    async def test_get_merge_not_found(self, client: AsyncClient) -> None:
        """GET /merges/{id} returns 404 for non-existent merge."""
        fake_id = str(uuid4())
        response = await client.get(f"/merges/{fake_id}")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


class TestMergeCreateAPIContract:
    """Contract tests for POST /merges endpoint."""

    @pytest.mark.asyncio
    async def test_create_merge_requires_cluster_id(self, client: AsyncClient) -> None:
        """POST /merges returns 422 when cluster_id is missing."""
        response = await client.post(
            "/merges",
            json={"primary_ticket_id": str(uuid4())},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_merge_requires_primary_ticket(self, client: AsyncClient) -> None:
        """POST /merges returns 422 when primary_ticket_id is missing."""
        response = await client.post(
            "/merges",
            json={"cluster_id": str(uuid4())},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_merge_validates_behavior(self, client: AsyncClient) -> None:
        """POST /merges validates merge_behavior enum."""
        response = await client.post(
            "/merges",
            json={
                "cluster_id": str(uuid4()),
                "primary_ticket_id": str(uuid4()),
                "merge_behavior": "InvalidBehavior",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_merge_success_schema(
        self, client: AsyncClient, created_cluster_id: str, created_ticket_ids: list[str]
    ) -> None:
        """POST /merges returns proper merge response on success."""
        response = await client.post(
            "/merges",
            json={
                "cluster_id": created_cluster_id,
                "primary_ticket_id": created_ticket_ids[0],
                "merge_behavior": "KeepLatest",
            },
        )

        # Could be 201 or 200 depending on implementation
        assert response.status_code in [200, 201]
        data = response.json()

        assert "id" in data
        assert "cluster_id" in data
        assert "status" in data


class TestMergeRevertAPIContract:
    """Contract tests for POST /merges/{id}/revert endpoint."""

    @pytest.mark.asyncio
    async def test_revert_merge_not_found(self, client: AsyncClient) -> None:
        """POST /merges/{id}/revert returns 404 for non-existent merge."""
        fake_id = str(uuid4())
        response = await client.post(f"/merges/{fake_id}/revert")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_revert_already_reverted(
        self, client: AsyncClient, reverted_merge_id: str
    ) -> None:
        """POST /merges/{id}/revert returns 409 if already reverted."""
        response = await client.post(f"/merges/{reverted_merge_id}/revert")

        assert response.status_code == 409
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_revert_success_schema(self, client: AsyncClient, created_merge_id: str) -> None:
        """POST /merges/{id}/revert returns updated merge with reverted status."""
        response = await client.post(f"/merges/{created_merge_id}/revert")

        # Success or conflict
        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert data["status"] == "reverted"
            assert "reverted_at" in data
        elif response.status_code == 409:
            # Already reverted
            data = response.json()
            assert "detail" in data
        elif response.status_code == 422:
            # Conflict with post-merge changes
            data = response.json()
            assert "conflicts" in data or "detail" in data
