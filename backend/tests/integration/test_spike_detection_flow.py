"""
Integration tests for spike detection workflow.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient


class TestSpikeListEndpoint:
    """Tests for GET /spikes endpoint."""

    @pytest.mark.asyncio
    async def test_list_spikes_empty(
        self,
        client: AsyncClient,
        api_key_header: dict[str, str],
    ) -> None:
        """Test listing spikes when none exist."""
        response = await client.get(
            "/api/v1/spikes",
            headers=api_key_header,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["pagination"]["total_items"] == 0

    @pytest.mark.asyncio
    async def test_list_spikes_with_filters(
        self,
        client: AsyncClient,
        api_key_header: dict[str, str],
    ) -> None:
        """Test listing spikes with region and month filters."""
        response = await client.get(
            "/api/v1/spikes?region=US&month=2025-01&active_only=true",
            headers=api_key_header,
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "pagination" in data


class TestSpikeAcknowledgeEndpoint:
    """Tests for POST /spikes/{id}/acknowledge endpoint."""

    @pytest.mark.asyncio
    async def test_acknowledge_nonexistent_spike(
        self,
        client: AsyncClient,
        api_key_header: dict[str, str],
    ) -> None:
        """Test acknowledging a spike that doesn't exist."""
        spike_id = uuid4()
        response = await client.post(
            f"/api/v1/spikes/{spike_id}/acknowledge?region=US&month=2025-01",
            headers=api_key_header,
            json={},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestSpikeResolveEndpoint:
    """Tests for POST /spikes/{id}/resolve endpoint."""

    @pytest.mark.asyncio
    async def test_resolve_nonexistent_spike(
        self,
        client: AsyncClient,
        api_key_header: dict[str, str],
    ) -> None:
        """Test resolving a spike that doesn't exist."""
        spike_id = uuid4()
        response = await client.post(
            f"/api/v1/spikes/{spike_id}/resolve?region=US&month=2025-01",
            headers=api_key_header,
            json={"resolution_notes": "Test resolved"},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestSpikeActiveCountEndpoint:
    """Tests for GET /spikes/active/count endpoint."""

    @pytest.mark.asyncio
    async def test_get_active_count_empty(
        self,
        client: AsyncClient,
        api_key_header: dict[str, str],
    ) -> None:
        """Test getting active count when no spikes exist."""
        response = await client.get(
            "/api/v1/spikes/active/count",
            headers=api_key_header,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["active_count"] == 0

    @pytest.mark.asyncio
    async def test_get_active_count_with_filters(
        self,
        client: AsyncClient,
        api_key_header: dict[str, str],
    ) -> None:
        """Test getting active count with region filter."""
        response = await client.get(
            "/api/v1/spikes/active/count?region=EU&month=2025-01",
            headers=api_key_header,
        )

        assert response.status_code == 200
        data = response.json()
        assert "active_count" in data


class TestSpikeDetailEndpoint:
    """Tests for GET /spikes/{id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_spike_detail_not_found(
        self,
        client: AsyncClient,
        api_key_header: dict[str, str],
    ) -> None:
        """Test getting details for nonexistent spike."""
        spike_id = uuid4()
        response = await client.get(
            f"/api/v1/spikes/{spike_id}?region=US&month=2025-01",
            headers=api_key_header,
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
