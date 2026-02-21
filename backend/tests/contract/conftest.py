"""
Contract test fixtures.

Provides a test client with mocked repositories via FastAPI dependency overrides.
All contract tests validate HTTP response structure against the actual API implementation.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from models.cluster import (
    Cluster,
    ClusterMember,
    ClusterStatus,
)
from models.merge_operation import MergeBehavior, MergeOperation, MergeStatus
from models.ticket import Ticket

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# ---------------------------------------------------------------------------
# Fixed test data identifiers
# ---------------------------------------------------------------------------
MONTH = "2025-01"
CLUSTER_ID = uuid4()
TICKET_IDS = [uuid4() for _ in range(3)]
MERGE_ID = uuid4()
REVERTED_MERGE_ID = uuid4()
NOW = datetime(2025, 1, 15, 10, 0, 0)


def _build_test_cluster(
    cluster_id: UUID = CLUSTER_ID,
    status: ClusterStatus = ClusterStatus.PENDING,
) -> Cluster:
    return Cluster(
        id=cluster_id,
        pk=MONTH,
        status=status,
        summary="3 duplicate tickets for merchant ABC",
        ticket_count=3,
        created_at=NOW,
        updated_at=NOW,
        members=[
            ClusterMember(ticket_id=tid, ticket_number=f"T-{i}", added_at=NOW)
            for i, tid in enumerate(TICKET_IDS)
        ],
    )


def _build_test_tickets() -> list[Ticket]:
    return [
        Ticket(
            id=tid,
            pk=MONTH,
            ticket_number=f"TKT-{i:04d}",
            created_at=NOW,
            updated_at=NOW,
            channel="InApp",
            customer_id=f"CUST-{i}",
            category="Billing",
            summary=f"Test ticket summary {i}",
            description=f"Description for ticket {i}",
            cluster_id=CLUSTER_ID,
        )
        for i, tid in enumerate(TICKET_IDS)
    ]


def _build_test_merge(
    merge_id: UUID = MERGE_ID,
    status: MergeStatus = MergeStatus.COMPLETED,
) -> MergeOperation:
    m = MergeOperation(
        id=merge_id,
        pk=MONTH,
        cluster_id=CLUSTER_ID,
        primary_ticket_id=TICKET_IDS[0],
        secondary_ticket_ids=TICKET_IDS[1:],
        merge_behavior=MergeBehavior.KEEP_LATEST,
        performed_by="test-user",
        performed_at=NOW,
        status=status,
        revert_deadline=datetime.utcnow() + timedelta(hours=24),
    )
    if status == MergeStatus.REVERTED:
        m.reverted_at = NOW
        m.reverted_by = "test-user"
        m.revert_reason = "testing"
    return m


# ---------------------------------------------------------------------------
# Mock repository factories
# ---------------------------------------------------------------------------


def _make_cluster_repo() -> AsyncMock:
    repo = AsyncMock()
    cluster = _build_test_cluster()

    async def _get_by_id(cluster_id: Any, partition_key: str) -> Cluster | None:
        if str(cluster_id) == str(CLUSTER_ID):
            return _build_test_cluster()
        return None

    async def _update_status(
        cluster_id: Any,
        status: ClusterStatus,
        partition_key: str,
        **kwargs: Any,
    ) -> Cluster | None:
        if str(cluster_id) == str(CLUSTER_ID):
            return _build_test_cluster(status=status)
        return None

    async def _remove_ticket(
        cluster_id: Any,
        ticket_id: Any,
        partition_key: str,
    ) -> Cluster | None:
        if str(cluster_id) == str(CLUSTER_ID):
            c = _build_test_cluster()
            c.members = [m for m in c.members if m.ticket_id != ticket_id]
            c.ticket_count = len(c.members)
            return c
        return None

    repo.get_pending_clusters = AsyncMock(return_value=[cluster])
    repo.get_by_status = AsyncMock(return_value=[cluster])
    repo.get_by_id = AsyncMock(side_effect=_get_by_id)
    repo.update_status = AsyncMock(side_effect=_update_status)
    repo.remove_ticket = AsyncMock(side_effect=_remove_ticket)
    repo.get_pending_review_count = AsyncMock(return_value=5)
    return repo


def _make_ticket_repo() -> AsyncMock:
    repo = AsyncMock()
    tickets = _build_test_tickets()

    async def _get_by_id(ticket_id: Any, partition_key: str) -> Ticket | None:
        for t in tickets:
            if str(t.id) == str(ticket_id):
                return t
        return None

    repo.get_by_cluster_id = AsyncMock(return_value=tickets)
    repo.get_by_id = AsyncMock(side_effect=_get_by_id)
    repo.remove_from_cluster = AsyncMock()
    return repo


def _make_merge_repo() -> AsyncMock:
    repo = AsyncMock()
    merge = _build_test_merge()

    async def _get_by_id(merge_id: Any, partition_key: str) -> MergeOperation | None:
        if str(merge_id) == str(MERGE_ID):
            return _build_test_merge()
        if str(merge_id) == str(REVERTED_MERGE_ID):
            return _build_test_merge(merge_id=REVERTED_MERGE_ID, status=MergeStatus.REVERTED)
        return None

    async def _create(entity: MergeOperation, partition_key: str) -> MergeOperation:
        return entity

    async def _update_status(
        merge_id: Any,
        status: MergeStatus,
        partition_key: str,
        **kwargs: Any,
    ) -> MergeOperation | None:
        if str(merge_id) == str(MERGE_ID):
            return _build_test_merge(status=status)
        return None

    repo.get_revertible_merges = AsyncMock(return_value=[merge])
    repo.query = AsyncMock(return_value=[merge])
    repo.get_by_id = AsyncMock(side_effect=_get_by_id)
    repo.create = AsyncMock(side_effect=_create)
    repo.update_status = AsyncMock(side_effect=_update_status)
    repo.check_revert_conflicts = AsyncMock(return_value=[])
    return repo


# ---------------------------------------------------------------------------
# Client fixture with dependency overrides
# ---------------------------------------------------------------------------


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with mocked deps via FastAPI overrides."""
    import os  # noqa: PLC0415

    # Set required Azure OpenAI env vars before importing main (which triggers
    # module-level Settings() construction via create_app()).
    _openai_env = {
        "COSMOS_ENDPOINT": "https://localhost:8081",
        "COSMOS_KEY": "test-key",
        "COSMOS_DATABASE": "test-db",
        "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
        "AZURE_OPENAI_USE_AAD": "false",
        "AZURE_OPENAI_KEY": "test-openai-key",
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT": "text-embedding-3-small",
    }
    _saved = {k: os.environ.get(k) for k in _openai_env}
    os.environ.update(_openai_env)

    from config import Settings, get_settings  # noqa: PLC0415

    # Clear lru_cache so Settings re-reads with the new env vars
    get_settings.cache_clear()

    from dependencies import (  # noqa: PLC0415
        get_cluster_repository,
        get_current_user,
        get_merge_repository,
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
        debug=True,
        log_level="DEBUG",
    )

    mock_cluster_repo = _make_cluster_repo()
    mock_merge_repo = _make_merge_repo()
    mock_ticket_repo = _make_ticket_repo()

    with (
        patch("config.get_settings", return_value=test_settings),
        patch("dependencies.get_cached_settings", return_value=test_settings),
    ):
        app = create_app()

    # Override dependencies so no Cosmos DB connection is needed
    app.dependency_overrides[verify_api_key] = lambda: "test-key"
    app.dependency_overrides[get_current_user] = lambda: "test-user"
    app.dependency_overrides[get_cluster_repository] = lambda: mock_cluster_repo
    app.dependency_overrides[get_merge_repository] = lambda: mock_merge_repo
    app.dependency_overrides[get_ticket_repository] = lambda: mock_ticket_repo

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

    # Restore env vars and clear settings cache
    for k, v in _saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Data identity fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def created_cluster_id() -> str:
    """Return the ID of a pre-existing test cluster."""
    return str(CLUSTER_ID)


@pytest.fixture
def _created_cluster_id() -> str:
    """Ensure a cluster exists (marker fixture). Returns its ID."""
    return str(CLUSTER_ID)


@pytest.fixture
def created_ticket_ids() -> list[str]:
    """Return the IDs of pre-existing test tickets."""
    return [str(tid) for tid in TICKET_IDS]


@pytest.fixture
def created_merge_id() -> str:
    """Return the ID of a pre-existing completed merge."""
    return str(MERGE_ID)


@pytest.fixture
def _created_merge_id() -> str:
    """Ensure a merge exists (marker fixture). Returns its ID."""
    return str(MERGE_ID)


@pytest.fixture
def reverted_merge_id() -> str:
    """Return the ID of a pre-existing reverted merge."""
    return str(REVERTED_MERGE_ID)
