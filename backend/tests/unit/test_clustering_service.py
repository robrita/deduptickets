"""
Unit tests for ClusteringService (cluster-first hybrid pipeline).

Tests vector-based clustering, multi-signal scoring, three-tier
decisions, centroid updates, and cluster lifecycle management.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from models.cluster import (
    Cluster,
    ClusterMember,
    ClusterStatus,
)
from models.ticket import Ticket
from services.clustering_service import (
    ClusteringService,
    _compute_confidence_score,
    _compute_time_proximity,
    _generate_partition_keys,
    _update_centroid,
)


def _mock_settings() -> AsyncMock:
    """Create a mock settings object with standard dedup config."""
    s = AsyncMock()
    s.cluster_search_months = 2
    s.dedup_window_days = 14
    s.cluster_top_k = 5
    s.dedup_open_statuses = ["open", "pending"]
    s.cluster_auto_threshold = 0.92
    s.cluster_review_threshold = 0.85
    s.dedup_filter_by_customer = False
    s.dedup_weight_semantic = 0.85
    s.dedup_weight_subcategory = 0.10
    s.dedup_weight_category = 0.03
    s.dedup_weight_time = 0.02
    s.cluster_max_members = 100
    return s


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_ticket_repo() -> AsyncMock:
    """Create mock ticket repository."""
    repo = AsyncMock()
    repo.assign_to_cluster = AsyncMock()
    repo.remove_from_cluster = AsyncMock()
    repo.get_by_id = AsyncMock()
    return repo


@pytest.fixture
def mock_cluster_repo() -> AsyncMock:
    """Create mock cluster repository."""
    repo = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.create = AsyncMock()
    repo.add_ticket = AsyncMock()
    repo.remove_ticket = AsyncMock()
    repo.update_status = AsyncMock()
    repo.find_cluster_candidates = AsyncMock(return_value=[])
    repo.update_cluster_with_etag = AsyncMock()
    return repo


@pytest.fixture
def mock_embedding_service() -> AsyncMock:
    """Create mock embedding service."""
    service = AsyncMock()
    service.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
    return service


@pytest.fixture
def sample_ticket() -> Ticket:
    """Create sample ticket with embedding for testing."""
    now = datetime.utcnow()
    return Ticket(
        id=uuid4(),
        pk="2025-01",
        ticket_number="TICKET-001",
        created_at=now,
        updated_at=now,
        channel="InApp",
        customer_id="CUST-001",
        category="Payments",
        subcategory="Payment Failed",
        summary="Payment failed for order 12345",
        description="Customer unable to complete payment.",
        severity="high",
        content_vector=[0.1] * 1536,
        dedup_text="Payment failed for order 12345",
    )


@pytest.fixture
def clustering_service(
    mock_ticket_repo: AsyncMock,
    mock_cluster_repo: AsyncMock,
    mock_embedding_service: AsyncMock,
) -> ClusteringService:
    """Create clustering service with mock dependencies."""
    return ClusteringService(
        mock_ticket_repo,
        mock_cluster_repo,
        mock_embedding_service,
    )


# =============================================================================
# Helper function tests
# =============================================================================


class TestComputeConfidenceScore:
    """Tests for multi-signal confidence score."""

    def test_perfect_score(self) -> None:
        score = _compute_confidence_score(
            semantic_score=1.0,
            subcategory_match=True,
            category_match=True,
            time_proximity=1.0,
        )
        assert score == pytest.approx(1.0)

    def test_zero_score(self) -> None:
        score = _compute_confidence_score(
            semantic_score=0.0,
            subcategory_match=False,
            category_match=False,
            time_proximity=0.0,
        )
        assert score == pytest.approx(0.0)

    def test_semantic_dominant(self) -> None:
        score = _compute_confidence_score(
            semantic_score=0.95,
            subcategory_match=False,
            category_match=False,
            time_proximity=0.0,
        )
        # 0.85 * 0.95 = 0.8075
        assert score == pytest.approx(0.8075)

    def test_all_signals(self) -> None:
        score = _compute_confidence_score(
            semantic_score=0.9,
            subcategory_match=True,
            category_match=True,
            time_proximity=0.5,
        )
        expected = 0.85 * 0.9 + 0.10 * 1.0 + 0.03 * 1.0 + 0.02 * 0.5
        assert score == pytest.approx(expected)

    def test_custom_weights(self) -> None:
        score = _compute_confidence_score(
            semantic_score=0.9,
            subcategory_match=True,
            category_match=True,
            time_proximity=0.5,
            w_semantic=0.70,
            w_subcategory=0.15,
            w_category=0.10,
            w_time=0.05,
        )
        expected = 0.70 * 0.9 + 0.15 * 1.0 + 0.10 * 1.0 + 0.05 * 0.5
        assert score == pytest.approx(expected)


class TestComputeTimeProximity:
    """Tests for time proximity calculation."""

    def test_identical_times(self) -> None:
        now = datetime.utcnow()
        assert _compute_time_proximity(now, now, 14) == pytest.approx(1.0)

    def test_edge_of_window(self) -> None:
        now = datetime.utcnow()
        edge = now + timedelta(days=14)
        assert _compute_time_proximity(now, edge, 14) == pytest.approx(0.0)

    def test_beyond_window(self) -> None:
        now = datetime.utcnow()
        beyond = now + timedelta(days=20)
        assert _compute_time_proximity(now, beyond, 14) == pytest.approx(0.0)

    def test_half_window(self) -> None:
        now = datetime.utcnow()
        half = now + timedelta(days=7)
        assert _compute_time_proximity(now, half, 14) == pytest.approx(0.5)

    def test_symmetric(self) -> None:
        now = datetime.utcnow()
        later = now + timedelta(days=3)
        assert _compute_time_proximity(now, later, 14) == pytest.approx(
            _compute_time_proximity(later, now, 14)
        )


class TestGeneratePartitionKeys:
    """Tests for partition key generation."""

    def test_single_month(self) -> None:
        dt = datetime(2025, 3, 15)
        keys = _generate_partition_keys(dt, 1)
        assert keys == ["2025-03"]

    def test_two_months(self) -> None:
        dt = datetime(2025, 3, 15)
        keys = _generate_partition_keys(dt, 2)
        assert keys == ["2025-03", "2025-02"]

    def test_year_boundary(self) -> None:
        dt = datetime(2025, 1, 10)
        keys = _generate_partition_keys(dt, 3)
        assert keys == ["2025-01", "2024-12", "2024-11"]


class TestUpdateCentroid:
    """Tests for incremental centroid update."""

    def test_first_addition(self) -> None:
        old = [1.0, 2.0, 3.0]
        new = [4.0, 5.0, 6.0]
        result = _update_centroid(old, new, 1)
        # (1*1 + 4) / 2 = 2.5, (2*1 + 5) / 2 = 3.5, (3*1 + 6) / 2 = 4.5
        assert result == pytest.approx([2.5, 3.5, 4.5])

    def test_multiple_additions(self) -> None:
        old = [2.0, 2.0]
        new = [5.0, 5.0]
        result = _update_centroid(old, new, 3)
        # (2*3 + 5) / 4 = 2.75, (2*3 + 5) / 4 = 2.75
        assert result == pytest.approx([2.75, 2.75])


# =============================================================================
# ClusteringService tests
# =============================================================================


class TestClusteringService:
    """Tests for ClusteringService."""

    @pytest.mark.asyncio
    async def test_no_candidates_creates_new_cluster(
        self,
        clustering_service: ClusteringService,
        mock_cluster_repo: AsyncMock,
        mock_ticket_repo: AsyncMock,
        sample_ticket: Ticket,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Should create CANDIDATE cluster when no candidates found."""
        mock_cluster_repo.find_cluster_candidates.return_value = []

        created_cluster = Cluster(
            id=uuid4(),
            pk="2025-01",
            members=[ClusterMember(ticket_id=sample_ticket.id, ticket_number="TICKET-001")],
            ticket_count=1,
            summary="Payments: Payment failed for order 12345",
            status=ClusterStatus.CANDIDATE,
        )
        mock_cluster_repo.create.return_value = created_cluster

        with (
            patch("services.clustering_service.get_settings") as mock_settings,
            caplog.at_level(logging.INFO, logger="services.clustering_service"),
        ):
            mock_settings.return_value = _mock_settings()

            _cluster, dedup = await clustering_service.find_or_create_cluster(
                sample_ticket,
                "2025-01",
            )

        assert _cluster.status == ClusterStatus.CANDIDATE
        assert dedup["decision"] == "new_cluster"
        assert dedup["decisionReason"] == "no_candidates"
        mock_cluster_repo.create.assert_called_once()
        mock_ticket_repo.assign_to_cluster.assert_called_once()
        assert any(
            "NEW_CLUSTER" in message and "reason: no_candidates" in message
            for message in caplog.messages
        )

    @pytest.mark.asyncio
    async def test_auto_decision_adds_to_existing(
        self,
        clustering_service: ClusteringService,
        mock_cluster_repo: AsyncMock,
        mock_ticket_repo: AsyncMock,
        sample_ticket: Ticket,
    ) -> None:
        """Should add to existing cluster with 'auto' decision when score >= 0.92."""
        existing_cluster_id = uuid4()

        # Return a high-scoring candidate
        mock_cluster_repo.find_cluster_candidates.return_value = [
            {
                "id": str(existing_cluster_id),
                "customerId": "CUST-001",
                "openCount": 2,
                "category": "Payments",
                "subcategory": "Payment Failed",
                "updatedAt": sample_ticket.created_at.isoformat(),
                "ticketCount": 2,
                "status": "pending",
                "pk": "2025-01",
                "similarityScore": 0.98,
            }
        ]

        existing_cluster = Cluster(
            id=existing_cluster_id,
            pk="2025-01",
            members=[
                ClusterMember(ticket_id=uuid4(), ticket_number="T-002"),
                ClusterMember(ticket_id=uuid4(), ticket_number="T-003"),
            ],
            ticket_count=2,
            summary="Payments: Payment issues",
            status=ClusterStatus.PENDING,
            centroid_vector=[0.1] * 1536,
            customer_id="CUST-001",
            open_count=2,
            etag="etag-123",
        )
        mock_cluster_repo.get_by_id.return_value = existing_cluster
        mock_cluster_repo.update_cluster_with_etag.return_value = existing_cluster

        with patch("services.clustering_service.get_settings") as mock_settings:
            mock_settings.return_value = _mock_settings()

            _cluster, dedup = await clustering_service.find_or_create_cluster(
                sample_ticket,
                "2025-01",
            )

        assert dedup["decision"] == "auto"
        assert dedup["confidenceScore"] > 0.92
        mock_cluster_repo.update_cluster_with_etag.assert_called_once()
        mock_ticket_repo.assign_to_cluster.assert_called_once()

    @pytest.mark.asyncio
    async def test_review_decision(
        self,
        clustering_service: ClusteringService,
        mock_cluster_repo: AsyncMock,
        sample_ticket: Ticket,
    ) -> None:
        """Should return 'review' decision when score is between thresholds."""
        existing_cluster_id = uuid4()

        # Score will be ~0.85*0.90 + 0.10 + 0.03 + 0.02 = 0.915 (review range)
        mock_cluster_repo.find_cluster_candidates.return_value = [
            {
                "id": str(existing_cluster_id),
                "customerId": "CUST-001",
                "openCount": 1,
                "category": "Payments",
                "subcategory": "Payment Failed",
                "updatedAt": sample_ticket.created_at.isoformat(),
                "ticketCount": 1,
                "status": "candidate",
                "pk": "2025-01",
                "similarityScore": 0.90,
            }
        ]

        existing_cluster = Cluster(
            id=existing_cluster_id,
            pk="2025-01",
            members=[ClusterMember(ticket_id=uuid4(), ticket_number="T-002")],
            ticket_count=1,
            summary="Payments: similar issue",
            status=ClusterStatus.CANDIDATE,
            centroid_vector=[0.1] * 1536,
            customer_id="CUST-001",
            open_count=1,
            etag="etag-456",
        )
        mock_cluster_repo.get_by_id.return_value = existing_cluster
        mock_cluster_repo.update_cluster_with_etag.return_value = existing_cluster

        with patch("services.clustering_service.get_settings") as mock_settings:
            mock_settings.return_value = _mock_settings()

            _cluster, dedup = await clustering_service.find_or_create_cluster(
                sample_ticket,
                "2025-01",
            )

        assert dedup["decision"] == "review"

    @pytest.mark.asyncio
    async def test_low_score_creates_new_cluster(
        self,
        clustering_service: ClusteringService,
        mock_cluster_repo: AsyncMock,
        sample_ticket: Ticket,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Should create new cluster when score is below review threshold."""
        mock_cluster_repo.find_cluster_candidates.return_value = [
            {
                "id": str(uuid4()),
                "customerId": "CUST-001",
                "openCount": 1,
                "category": "Different",
                "subcategory": "Other",
                "updatedAt": (sample_ticket.created_at - timedelta(days=13)).isoformat(),
                "ticketCount": 1,
                "status": "candidate",
                "pk": "2025-01",
                "similarityScore": 0.5,
            }
        ]

        created_cluster = Cluster(
            id=uuid4(),
            pk="2025-01",
            members=[ClusterMember(ticket_id=sample_ticket.id, ticket_number="TICKET-001")],
            ticket_count=1,
            summary="Payments: Payment failed",
            status=ClusterStatus.CANDIDATE,
        )
        mock_cluster_repo.create.return_value = created_cluster

        with (
            patch("services.clustering_service.get_settings") as mock_settings,
            caplog.at_level(logging.INFO, logger="services.clustering_service"),
        ):
            mock_settings.return_value = _mock_settings()

            _cluster, dedup = await clustering_service.find_or_create_cluster(
                sample_ticket,
                "2025-01",
            )

        assert dedup["decision"] == "new_cluster"
        assert dedup["decisionReason"] == "below_review_threshold"
        assert dedup["confidenceScore"] > 0.0
        assert dedup["semanticScore"] == pytest.approx(0.5)
        assert dedup["signals"]["timeProximity"] == pytest.approx(0.0714, rel=1e-3)
        assert any(
            "NEW_CLUSTER" in message
            and "reason: below_review_threshold" in message
            and "semantic=0.5000" in message
            for message in caplog.messages
        )
        mock_cluster_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_candidate_promoted_to_pending(
        self,
        clustering_service: ClusteringService,
        mock_cluster_repo: AsyncMock,
        sample_ticket: Ticket,
    ) -> None:
        """Should promote CANDIDATE to PENDING when second ticket joins."""
        existing_cluster_id = uuid4()

        mock_cluster_repo.find_cluster_candidates.return_value = [
            {
                "id": str(existing_cluster_id),
                "customerId": "CUST-001",
                "openCount": 1,
                "category": "Payments",
                "subcategory": "Payment Failed",
                "updatedAt": sample_ticket.created_at.isoformat(),
                "ticketCount": 1,
                "status": "candidate",
                "pk": "2025-01",
                "similarityScore": 0.99,
            }
        ]

        candidate_cluster = Cluster(
            id=existing_cluster_id,
            pk="2025-01",
            members=[ClusterMember(ticket_id=uuid4(), ticket_number="T-002")],
            ticket_count=1,
            summary="Payments: similar",
            status=ClusterStatus.CANDIDATE,
            centroid_vector=[0.1] * 1536,
            customer_id="CUST-001",
            open_count=1,
            etag="etag-789",
        )
        mock_cluster_repo.get_by_id.return_value = candidate_cluster

        # After update, should be PENDING
        updated = Cluster(
            id=existing_cluster_id,
            pk="2025-01",
            members=[
                ClusterMember(ticket_id=uuid4(), ticket_number="T-002"),
                ClusterMember(ticket_id=sample_ticket.id, ticket_number="TICKET-001"),
            ],
            ticket_count=2,
            summary="Payments: similar",
            status=ClusterStatus.PENDING,
            centroid_vector=[0.1] * 1536,
            customer_id="CUST-001",
            open_count=2,
            etag="etag-new",
        )
        mock_cluster_repo.update_cluster_with_etag.return_value = updated

        with patch("services.clustering_service.get_settings") as mock_settings:
            mock_settings.return_value = _mock_settings()

            cluster, _dedup = await clustering_service.find_or_create_cluster(
                sample_ticket,
                "2025-01",
            )

        assert cluster.status == ClusterStatus.PENDING

    @pytest.mark.asyncio
    async def test_ticket_without_vector_raises(
        self,
        clustering_service: ClusteringService,
    ) -> None:
        """Should raise ValueError when ticket has no content_vector."""
        ticket = Ticket(
            id=uuid4(),
            pk="2025-01",
            ticket_number="TICKET-X",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            channel="chat",
            customer_id="CUST-001",
            category="Test",
            summary="Test ticket without vector",
        )

        with (
            pytest.raises(ValueError, match="content_vector"),
            patch("services.clustering_service.get_settings"),
        ):
            await clustering_service.find_or_create_cluster(ticket, "2025-01")

    @pytest.mark.asyncio
    async def test_dismiss_cluster(
        self,
        clustering_service: ClusteringService,
        mock_cluster_repo: AsyncMock,
    ) -> None:
        """Should dismiss cluster with reason."""
        cluster_id = uuid4()
        mock_cluster_repo.get_by_id.return_value = Cluster(
            id=cluster_id,
            pk="2025-01",
            members=[
                ClusterMember(ticket_id=uuid4(), ticket_number="T-001"),
                ClusterMember(ticket_id=uuid4(), ticket_number="T-002"),
            ],
            ticket_count=2,
            summary="Test cluster",
            status=ClusterStatus.PENDING,
        )
        mock_cluster_repo.update_status.return_value = Cluster(
            id=cluster_id,
            pk="2025-01",
            members=[
                ClusterMember(ticket_id=uuid4(), ticket_number="T-001"),
                ClusterMember(ticket_id=uuid4(), ticket_number="T-002"),
            ],
            ticket_count=2,
            summary="Test cluster",
            status=ClusterStatus.DISMISSED,
        )

        result = await clustering_service.dismiss_cluster(
            cluster_id,
            "2025-01",
            dismissed_by="user@example.com",
            reason="Not duplicates",
        )

        assert result.status == ClusterStatus.DISMISSED

    @pytest.mark.asyncio
    async def test_remove_ticket_demotes_to_candidate(
        self,
        clustering_service: ClusteringService,
        mock_cluster_repo: AsyncMock,
    ) -> None:
        """Should demote cluster to CANDIDATE when only 1 member remains."""
        cluster_id = uuid4()
        ticket_id = uuid4()
        remaining_id = uuid4()

        mock_cluster_repo.get_by_id.return_value = Cluster(
            id=cluster_id,
            pk="2025-01",
            members=[
                ClusterMember(ticket_id=ticket_id, ticket_number="T-001"),
                ClusterMember(ticket_id=remaining_id, ticket_number="T-002"),
            ],
            ticket_count=2,
            summary="Test",
            status=ClusterStatus.PENDING,
        )

        mock_cluster_repo.remove_ticket.return_value = Cluster(
            id=cluster_id,
            pk="2025-01",
            members=[ClusterMember(ticket_id=remaining_id, ticket_number="T-002")],
            ticket_count=1,
            summary="Test",
            status=ClusterStatus.PENDING,
        )

        mock_cluster_repo.update_status.return_value = Cluster(
            id=cluster_id,
            pk="2025-01",
            members=[ClusterMember(ticket_id=remaining_id, ticket_number="T-002")],
            ticket_count=1,
            summary="Test",
            status=ClusterStatus.CANDIDATE,
        )

        result = await clustering_service.remove_ticket_from_cluster(
            cluster_id,
            ticket_id,
            "2025-01",
        )

        assert result.status == ClusterStatus.CANDIDATE
        mock_cluster_repo.update_status.assert_called_once_with(
            cluster_id,
            ClusterStatus.CANDIDATE,
            "2025-01",
        )

    @pytest.mark.asyncio
    async def test_full_cluster_fallback_to_next_candidate(
        self,
        clustering_service: ClusteringService,
        mock_cluster_repo: AsyncMock,
        mock_ticket_repo: AsyncMock,
        sample_ticket: Ticket,
    ) -> None:
        """When best candidate is full (race), should fall through to next candidate."""
        full_cluster_id = uuid4()
        good_cluster_id = uuid4()

        # Two candidates: first is full (race), second is good
        mock_cluster_repo.find_cluster_candidates.return_value = [
            {
                "id": str(full_cluster_id),
                "customerId": "CUST-001",
                "openCount": 2,
                "category": "Payments",
                "subcategory": "Payment Failed",
                "updatedAt": sample_ticket.created_at.isoformat(),
                "ticketCount": 99,
                "status": "pending",
                "pk": "2025-01",
                "similarityScore": 0.99,
            },
            {
                "id": str(good_cluster_id),
                "customerId": "CUST-001",
                "openCount": 1,
                "category": "Payments",
                "subcategory": "Payment Failed",
                "updatedAt": sample_ticket.created_at.isoformat(),
                "ticketCount": 5,
                "status": "pending",
                "pk": "2025-01",
                "similarityScore": 0.97,
            },
        ]

        # First cluster: full — add_member will raise ValueError
        full_cluster = Cluster(
            id=full_cluster_id,
            pk="2025-01",
            members=[
                ClusterMember(ticket_id=uuid4(), ticket_number=f"T-{i:03d}") for i in range(100)
            ],
            ticket_count=100,
            summary="Payments: full cluster",
            status=ClusterStatus.PENDING,
            centroid_vector=[0.1] * 1536,
            customer_id="CUST-001",
            open_count=2,
            etag="etag-full",
        )

        # Second cluster: has capacity
        good_cluster = Cluster(
            id=good_cluster_id,
            pk="2025-01",
            members=[
                ClusterMember(ticket_id=uuid4(), ticket_number=f"T-{i:03d}") for i in range(5)
            ],
            ticket_count=5,
            summary="Payments: good cluster",
            status=ClusterStatus.PENDING,
            centroid_vector=[0.1] * 1536,
            customer_id="CUST-001",
            open_count=1,
            etag="etag-good",
        )

        # get_by_id returns full cluster first, then good cluster
        mock_cluster_repo.get_by_id.side_effect = [full_cluster, good_cluster]
        mock_cluster_repo.update_cluster_with_etag.return_value = good_cluster

        with patch("services.clustering_service.get_settings") as mock_settings:
            mock_settings.return_value = _mock_settings()

            cluster, dedup = await clustering_service.find_or_create_cluster(
                sample_ticket,
                "2025-01",
            )

        assert str(cluster.id) == str(good_cluster_id)
        assert dedup["decision"] in ("auto", "review")
        assert dedup["matchedClusterId"] == str(good_cluster_id)
        # create should NOT have been called (we fell through to second candidate)
        mock_cluster_repo.create.assert_not_called()
        mock_ticket_repo.assign_to_cluster.assert_called_once()

    @pytest.mark.asyncio
    async def test_all_candidates_full_creates_new_cluster(
        self,
        clustering_service: ClusteringService,
        mock_cluster_repo: AsyncMock,
        mock_ticket_repo: AsyncMock,
        sample_ticket: Ticket,
    ) -> None:
        """When all candidates are full, should create a new cluster."""
        full_cluster_id = uuid4()

        mock_cluster_repo.find_cluster_candidates.return_value = [
            {
                "id": str(full_cluster_id),
                "customerId": "CUST-001",
                "openCount": 2,
                "category": "Payments",
                "subcategory": "Payment Failed",
                "updatedAt": sample_ticket.created_at.isoformat(),
                "ticketCount": 99,
                "status": "pending",
                "pk": "2025-01",
                "similarityScore": 0.99,
            },
        ]

        full_cluster = Cluster(
            id=full_cluster_id,
            pk="2025-01",
            members=[
                ClusterMember(ticket_id=uuid4(), ticket_number=f"T-{i:03d}") for i in range(100)
            ],
            ticket_count=100,
            summary="Payments: full cluster",
            status=ClusterStatus.PENDING,
            centroid_vector=[0.1] * 1536,
            customer_id="CUST-001",
            open_count=2,
            etag="etag-full",
        )
        mock_cluster_repo.get_by_id.return_value = full_cluster

        created_cluster = Cluster(
            id=uuid4(),
            pk="2025-01",
            members=[ClusterMember(ticket_id=sample_ticket.id, ticket_number="TICKET-001")],
            ticket_count=1,
            summary="Payments: Payment failed",
            status=ClusterStatus.CANDIDATE,
        )
        mock_cluster_repo.create.return_value = created_cluster

        with patch("services.clustering_service.get_settings") as mock_settings:
            mock_settings.return_value = _mock_settings()

            cluster, dedup = await clustering_service.find_or_create_cluster(
                sample_ticket,
                "2025-01",
            )

        assert cluster.status == ClusterStatus.CANDIDATE
        assert dedup["decision"] == "new_cluster"
        mock_cluster_repo.create.assert_called_once()
        mock_ticket_repo.assign_to_cluster.assert_called_once()
