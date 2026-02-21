"""
Contract tests for the health check endpoints.

Validates GET /health (liveness) and GET /health/ready (readiness probe)
under all relevant Cosmos DB states.

All readiness tests patch `routes.health.cosmos_manager` INSIDE the
request call so the mock stays active during handler execution.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from httpx import AsyncClient  # noqa: TC002

# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


class TestLivenessProbe:
    async def test_health_always_200(self, client: AsyncClient) -> None:
        response = await client.get("/health")
        assert response.status_code == 200

    async def test_health_returns_healthy_status(self, client: AsyncClient) -> None:
        data = (await client.get("/health")).json()
        assert data["status"] == "healthy"

    async def test_health_has_version(self, client: AsyncClient) -> None:
        data = (await client.get("/health")).json()
        assert "version" in data
        assert data["version"] != ""


# ---------------------------------------------------------------------------
# GET /health/ready
# ---------------------------------------------------------------------------


def _make_cosmos_mock(
    *,
    configured: bool,
    connected: bool,
    health_result: dict,
) -> AsyncMock:
    mock = AsyncMock()
    mock.is_configured = configured
    mock.is_connected = connected
    mock.health_check = AsyncMock(return_value=health_result)
    return mock


class TestReadinessProbe:
    async def test_readiness_healthy_when_fully_connected(self, client: AsyncClient) -> None:
        """Fully healthy: configured + connected + health_check healthy."""
        mock_cosmos = _make_cosmos_mock(
            configured=True, connected=True, health_result={"cosmos": "healthy"}
        )
        with patch("routes.health.cosmos_manager", mock_cosmos):
            response = await client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data.get("cosmos") == "connected"

    async def test_readiness_unhealthy_when_not_configured(self, client: AsyncClient) -> None:
        """Not configured → unhealthy."""
        mock_cosmos = _make_cosmos_mock(configured=False, connected=False, health_result={})
        with patch("routes.health.cosmos_manager", mock_cosmos):
            response = await client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data.get("cosmos") == "not_configured"

    async def test_readiness_degraded_when_not_connected(self, client: AsyncClient) -> None:
        """Configured but not connected → degraded."""
        mock_cosmos = _make_cosmos_mock(configured=True, connected=False, health_result={})
        with patch("routes.health.cosmos_manager", mock_cosmos):
            response = await client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data.get("cosmos") == "not_connected"

    async def test_readiness_unhealthy_when_health_check_fails(self, client: AsyncClient) -> None:
        """Connected but health_check returns non-healthy cosmos status."""
        mock_cosmos = _make_cosmos_mock(
            configured=True, connected=True, health_result={"cosmos": "error"}
        )
        with patch("routes.health.cosmos_manager", mock_cosmos):
            response = await client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data.get("cosmos") == "error"

    async def test_readiness_unhealthy_when_cosmos_unknown(self, client: AsyncClient) -> None:
        """health_check returns an unknown cosmos status."""
        mock_cosmos = _make_cosmos_mock(
            configured=True, connected=True, health_result={"cosmos": "unknown"}
        )
        with patch("routes.health.cosmos_manager", mock_cosmos):
            response = await client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
