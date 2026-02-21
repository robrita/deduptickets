"""
Contract tests for Merges API.

Validates that the API implementation matches the actual response schemas.
Tests focus on:
- Response schema compliance
- Status codes per spec
- Merge operation fields
- Revert functionality
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

MONTH = "2025-01"


class TestMergesAPIContract:
    """Contract tests for GET /api/v1/merges endpoint."""

    @pytest.mark.asyncio
    async def test_list_merges_returns_paginated_response(self, client: AsyncClient) -> None:
        """GET /api/v1/merges returns proper pagination structure."""
        response = await client.get("/api/v1/merges", params={"month": MONTH})

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
    async def test_list_merges_item_schema(
        self, client: AsyncClient, _created_merge_id: str
    ) -> None:
        """Each merge item matches expected schema."""
        response = await client.get("/api/v1/merges", params={"month": MONTH})

        assert response.status_code == 200
        data = response.json()

        if data["data"]:
            merge = data["data"][0]
            # Required fields per MergeResponse schema
            assert "id" in merge
            assert "clusterId" in merge
            assert "primaryTicketId" in merge
            assert "secondaryTicketIds" in merge
            assert "mergeBehavior" in merge
            assert "status" in merge
            assert "performedBy" in merge
            assert "performedAt" in merge

            # Status must be valid enum value
            assert merge["status"] in ["completed", "reverted"]

            # Merge behavior must be valid
            assert merge["mergeBehavior"] in ["keep_latest", "combine_notes", "retain_all"]

    @pytest.mark.asyncio
    async def test_list_merges_filters_by_revertible(self, client: AsyncClient) -> None:
        """GET /api/v1/merges?revertible_only=true filters correctly."""
        response = await client.get(
            "/api/v1/merges", params={"revertible_only": "true", "month": MONTH}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["data"], list)


class TestMergeDetailAPIContract:
    """Contract tests for GET /api/v1/merges/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_merge_returns_detail(
        self, client: AsyncClient, created_merge_id: str
    ) -> None:
        """GET /api/v1/merges/{id} returns merge detail."""
        response = await client.get(f"/api/v1/merges/{created_merge_id}", params={"month": MONTH})

        assert response.status_code == 200
        data = response.json()

        # Required fields per MergeResponse schema
        assert "id" in data
        assert data["id"] == created_merge_id
        assert "clusterId" in data
        assert "primaryTicketId" in data
        assert "secondaryTicketIds" in data
        assert "mergeBehavior" in data
        assert "status" in data
        assert "performedBy" in data
        assert "performedAt" in data

    @pytest.mark.asyncio
    async def test_get_merge_not_found(self, client: AsyncClient) -> None:
        """GET /api/v1/merges/{id} returns 404 for non-existent merge."""
        fake_id = str(uuid4())
        response = await client.get(f"/api/v1/merges/{fake_id}", params={"month": MONTH})

        assert response.status_code == 404
        data = response.json()
        assert "message" in data


class TestMergeCreateAPIContract:
    """Contract tests for POST /api/v1/merges endpoint."""

    @pytest.mark.asyncio
    async def test_create_merge_requires_cluster_id(self, client: AsyncClient) -> None:
        """POST /api/v1/merges returns 422 when cluster_id is missing."""
        response = await client.post(
            "/api/v1/merges",
            params={"month": MONTH},
            json={"primaryTicketId": str(uuid4()), "mergeBehavior": "keep_latest"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_merge_requires_primary_ticket(self, client: AsyncClient) -> None:
        """POST /api/v1/merges returns 422 when primary_ticket_id is missing."""
        response = await client.post(
            "/api/v1/merges",
            params={"month": MONTH},
            json={"clusterId": str(uuid4()), "mergeBehavior": "keep_latest"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_merge_validates_behavior(self, client: AsyncClient) -> None:
        """POST /api/v1/merges validates merge_behavior enum."""
        response = await client.post(
            "/api/v1/merges",
            params={"month": MONTH},
            json={
                "clusterId": str(uuid4()),
                "primaryTicketId": str(uuid4()),
                "mergeBehavior": "InvalidBehavior",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_merge_success_schema(
        self, client: AsyncClient, created_cluster_id: str, created_ticket_ids: list[str]
    ) -> None:
        """POST /api/v1/merges returns proper merge response on success."""
        response = await client.post(
            "/api/v1/merges",
            params={"month": MONTH},
            json={
                "clusterId": created_cluster_id,
                "primaryTicketId": created_ticket_ids[0],
                "mergeBehavior": "keep_latest",
            },
        )

        assert response.status_code == 201
        data = response.json()

        assert "id" in data
        assert "clusterId" in data
        assert "status" in data
        assert data["status"] == "completed"


class TestMergeRevertAPIContract:
    """Contract tests for POST /api/v1/merges/{id}/revert endpoint."""

    @pytest.mark.asyncio
    async def test_revert_merge_not_found(self, client: AsyncClient) -> None:
        """POST /api/v1/merges/{id}/revert returns 404 for non-existent merge."""
        fake_id = str(uuid4())
        response = await client.post(
            f"/api/v1/merges/{fake_id}/revert",
            params={"month": MONTH},
            json={"reason": "testing"},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_revert_already_reverted(
        self, client: AsyncClient, reverted_merge_id: str
    ) -> None:
        """POST /api/v1/merges/{id}/revert returns 400 if already reverted."""
        response = await client.post(
            f"/api/v1/merges/{reverted_merge_id}/revert",
            params={"month": MONTH},
            json={"reason": "testing"},
        )

        assert response.status_code == 400
        data = response.json()
        assert "message" in data

    @pytest.mark.asyncio
    async def test_revert_success_schema(self, client: AsyncClient, created_merge_id: str) -> None:
        """POST /api/v1/merges/{id}/revert returns updated merge with reverted status."""
        response = await client.post(
            f"/api/v1/merges/{created_merge_id}/revert",
            params={"month": MONTH},
            json={"reason": "testing revert"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["status"] == "reverted"


class TestMergeConflictCheckAPIContract:
    """Contract tests for GET /api/v1/merges/{id}/conflicts endpoint."""

    @pytest.mark.asyncio
    async def test_check_conflicts_not_found(self, client: AsyncClient) -> None:
        """GET /api/v1/merges/{id}/conflicts returns 404 for non-existent merge."""
        fake_id = str(uuid4())
        response = await client.get(f"/api/v1/merges/{fake_id}/conflicts", params={"month": MONTH})

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_check_conflicts_no_conflicts(
        self, client: AsyncClient, created_merge_id: str
    ) -> None:
        """GET /api/v1/merges/{id}/conflicts returns OK when no conflicts."""
        response = await client.get(
            f"/api/v1/merges/{created_merge_id}/conflicts", params={"month": MONTH}
        )

        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "message" in data
        assert "conflicts" in data
