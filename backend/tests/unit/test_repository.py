"""
Unit tests for BaseRepository CRUD operations.

Uses a concrete TestRepo subclass to exercise the abstract base.
All Cosmos DB container calls are mocked with AsyncMock.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceNotFoundError
from pydantic import BaseModel

from repositories.base import BaseRepository

# ---------------------------------------------------------------------------
# Minimal domain model + concrete repo for testing
# ---------------------------------------------------------------------------


class _Item(BaseModel):
    id: str
    pk: str
    name: str = "default"


class _TestRepo(BaseRepository[_Item]):
    def _to_document(self, entity: _Item) -> dict[str, Any]:
        return entity.model_dump()

    def _from_document(self, doc: dict[str, Any]) -> _Item:
        return _Item(**doc)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_container() -> MagicMock:
    container = MagicMock()
    container.create_item = AsyncMock()
    container.read_item = AsyncMock()
    container.upsert_item = AsyncMock()
    container.delete_item = AsyncMock()
    return container


@pytest.fixture
def repo(mock_container: MagicMock) -> _TestRepo:
    return _TestRepo(container=mock_container, container_name="test-container")


def _make_item(name: str = "test") -> _Item:
    return _Item(id=str(uuid4()), pk="2025-01", name=name)


def _make_cosmos_error(status: int = 500) -> CosmosHttpResponseError:
    """Create a real CosmosHttpResponseError without invoking the HTTP-response constructor."""
    err = CosmosHttpResponseError.__new__(CosmosHttpResponseError)
    err.status_code = status
    err.message = f"cosmos error {status}"
    err.args = (f"cosmos error {status}",)
    return err


# ---------------------------------------------------------------------------
# BaseRepository.container property
# ---------------------------------------------------------------------------


class TestContainerProperty:
    def test_container_returns_underlying_proxy(
        self, repo: _TestRepo, mock_container: MagicMock
    ) -> None:
        assert repo.container is mock_container


# ---------------------------------------------------------------------------
# BaseRepository.create
# ---------------------------------------------------------------------------


class TestBaseRepositoryCreate:
    async def test_create_returns_entity(self, repo: _TestRepo, mock_container: MagicMock) -> None:
        item = _make_item("create-test")
        mock_container.create_item.return_value = item.model_dump()
        result = await repo.create(item, "2025-01")
        assert result.name == "create-test"

    async def test_create_calls_container_create_item(
        self, repo: _TestRepo, mock_container: MagicMock
    ) -> None:
        item = _make_item()
        mock_container.create_item.return_value = item.model_dump()
        await repo.create(item, "2025-01")
        mock_container.create_item.assert_awaited_once()

    async def test_create_propagates_cosmos_error(
        self, repo: _TestRepo, mock_container: MagicMock
    ) -> None:
        mock_container.create_item.side_effect = _make_cosmos_error(409)
        item = _make_item()
        with pytest.raises(CosmosHttpResponseError):
            await repo.create(item, "2025-01")


# ---------------------------------------------------------------------------
# BaseRepository.get_by_id
# ---------------------------------------------------------------------------


class TestBaseRepositoryGetById:
    async def test_returns_entity_when_found(
        self, repo: _TestRepo, mock_container: MagicMock
    ) -> None:
        item = _make_item("found-item")
        mock_container.read_item.return_value = item.model_dump()
        result = await repo.get_by_id(item.id, "2025-01")
        assert result is not None
        assert result.name == "found-item"

    async def test_returns_none_when_not_found(
        self, repo: _TestRepo, mock_container: MagicMock
    ) -> None:
        mock_container.read_item.side_effect = CosmosResourceNotFoundError(
            message="404, Resource Not Found"
        )
        result = await repo.get_by_id(str(uuid4()), "2025-01")
        assert result is None

    async def test_propagates_cosmos_error(
        self, repo: _TestRepo, mock_container: MagicMock
    ) -> None:
        mock_container.read_item.side_effect = _make_cosmos_error(503)
        with pytest.raises(CosmosHttpResponseError):
            await repo.get_by_id(str(uuid4()), "2025-01")

    async def test_accepts_uuid_type(self, repo: _TestRepo, mock_container: MagicMock) -> None:
        uid = uuid4()
        item = _make_item()
        item.id = str(uid)
        mock_container.read_item.return_value = item.model_dump()
        result = await repo.get_by_id(uid, "2025-01")
        assert result is not None


# ---------------------------------------------------------------------------
# BaseRepository.update
# ---------------------------------------------------------------------------


class TestBaseRepositoryUpdate:
    async def test_update_returns_entity(self, repo: _TestRepo, mock_container: MagicMock) -> None:
        item = _make_item("updated")
        mock_container.upsert_item.return_value = item.model_dump()
        result = await repo.update(item, "2025-01")
        assert result.name == "updated"

    async def test_update_calls_upsert_item(
        self, repo: _TestRepo, mock_container: MagicMock
    ) -> None:
        item = _make_item()
        mock_container.upsert_item.return_value = item.model_dump()
        await repo.update(item, "2025-01")
        mock_container.upsert_item.assert_awaited_once()

    async def test_update_propagates_cosmos_error(
        self, repo: _TestRepo, mock_container: MagicMock
    ) -> None:
        mock_container.upsert_item.side_effect = _make_cosmos_error(429)
        item = _make_item()
        with pytest.raises(CosmosHttpResponseError):
            await repo.update(item, "2025-01")


# ---------------------------------------------------------------------------
# BaseRepository.delete
# ---------------------------------------------------------------------------


class TestBaseRepositoryDelete:
    async def test_delete_returns_true_when_deleted(
        self, repo: _TestRepo, mock_container: MagicMock
    ) -> None:
        mock_container.delete_item.return_value = None
        result = await repo.delete(str(uuid4()), "2025-01")
        assert result is True

    async def test_delete_returns_false_when_not_found(
        self, repo: _TestRepo, mock_container: MagicMock
    ) -> None:
        mock_container.delete_item.side_effect = CosmosResourceNotFoundError(
            message="404, Resource Not Found"
        )
        result = await repo.delete(str(uuid4()), "2025-01")
        assert result is False

    async def test_delete_propagates_cosmos_error(
        self, repo: _TestRepo, mock_container: MagicMock
    ) -> None:
        mock_container.delete_item.side_effect = _make_cosmos_error(503)
        with pytest.raises(CosmosHttpResponseError):
            await repo.delete(str(uuid4()), "2025-01")

    async def test_delete_accepts_uuid_type(
        self, repo: _TestRepo, mock_container: MagicMock
    ) -> None:
        mock_container.delete_item.return_value = None
        result = await repo.delete(uuid4(), "2025-01")
        assert result is True


# ---------------------------------------------------------------------------
# BaseRepository.query
# ---------------------------------------------------------------------------


async def _async_gen_items(items: list[dict[str, Any]]):
    for item in items:
        yield item


class TestBaseRepositoryQuery:
    async def test_query_returns_entities(self, repo: _TestRepo, mock_container: MagicMock) -> None:
        items = [_make_item(f"item-{i}").model_dump() for i in range(3)]
        mock_container.query_items = MagicMock(return_value=_async_gen_items(items))
        results = await repo.query("SELECT * FROM c")
        assert len(results) == 3

    async def test_query_with_partition_key(
        self, repo: _TestRepo, mock_container: MagicMock
    ) -> None:
        mock_container.query_items = MagicMock(return_value=_async_gen_items([]))
        await repo.query("SELECT * FROM c", partition_key="2025-01")
        call_kwargs = mock_container.query_items.call_args.kwargs
        assert call_kwargs.get("partition_key") == "2025-01"

    async def test_query_adds_offset_limit_if_missing(
        self, repo: _TestRepo, mock_container: MagicMock
    ) -> None:
        mock_container.query_items = MagicMock(return_value=_async_gen_items([]))
        await repo.query("SELECT * FROM c", offset=5, max_item_count=50)
        call_kwargs = mock_container.query_items.call_args.kwargs
        assert "OFFSET 5 LIMIT 50" in call_kwargs["query"]

    async def test_query_no_offset_if_already_present(
        self, repo: _TestRepo, mock_container: MagicMock
    ) -> None:
        mock_container.query_items = MagicMock(return_value=_async_gen_items([]))
        sql = "SELECT * FROM c OFFSET 0 LIMIT 10"
        await repo.query(sql)
        call_kwargs = mock_container.query_items.call_args.kwargs
        # Should NOT add another OFFSET ... LIMIT
        assert call_kwargs["query"].count("OFFSET") == 1

    async def test_query_propagates_cosmos_error(
        self, repo: _TestRepo, mock_container: MagicMock
    ) -> None:
        mock_container.query_items = MagicMock(side_effect=_make_cosmos_error(500))
        with pytest.raises(CosmosHttpResponseError):
            await repo.query("SELECT * FROM c")

    async def test_query_with_parameters(self, repo: _TestRepo, mock_container: MagicMock) -> None:
        item = _make_item()
        mock_container.query_items = MagicMock(return_value=_async_gen_items([item.model_dump()]))
        results = await repo.query(
            "SELECT * FROM c WHERE c.pk = @pk",
            parameters=[{"name": "@pk", "value": "2025-01"}],
        )
        assert len(results) == 1


# ---------------------------------------------------------------------------
# BaseRepository.query_with_projection
# ---------------------------------------------------------------------------


class TestBaseRepositoryQueryWithProjection:
    async def test_returns_raw_dicts(self, repo: _TestRepo, mock_container: MagicMock) -> None:
        raw = [{"id": str(uuid4()), "name": "item"}]
        mock_container.query_items = MagicMock(return_value=_async_gen_items(raw))
        results = await repo.query_with_projection(fields=["id", "name"])
        assert results == raw

    async def test_with_where_clause(self, repo: _TestRepo, mock_container: MagicMock) -> None:
        mock_container.query_items = MagicMock(return_value=_async_gen_items([]))
        await repo.query_with_projection(
            fields=["id"],
            where_clause="c.status = @status",
            parameters=[{"name": "@status", "value": "open"}],
        )
        call_kwargs = mock_container.query_items.call_args.kwargs
        assert "WHERE" in call_kwargs["query"]

    async def test_with_order_by(self, repo: _TestRepo, mock_container: MagicMock) -> None:
        mock_container.query_items = MagicMock(return_value=_async_gen_items([]))
        await repo.query_with_projection(
            fields=["id"],
            order_by="c.createdAt DESC",
        )
        call_kwargs = mock_container.query_items.call_args.kwargs
        assert "ORDER BY" in call_kwargs["query"]

    async def test_with_partition_key(self, repo: _TestRepo, mock_container: MagicMock) -> None:
        mock_container.query_items = MagicMock(return_value=_async_gen_items([]))
        await repo.query_with_projection(fields=["id"], partition_key="2025-01")
        call_kwargs = mock_container.query_items.call_args.kwargs
        assert call_kwargs.get("partition_key") == "2025-01"

    async def test_propagates_cosmos_error(
        self, repo: _TestRepo, mock_container: MagicMock
    ) -> None:
        mock_container.query_items = MagicMock(side_effect=_make_cosmos_error(503))
        with pytest.raises(CosmosHttpResponseError):
            await repo.query_with_projection(fields=["id"])


# ---------------------------------------------------------------------------
# BaseRepository.count
# ---------------------------------------------------------------------------


class TestBaseRepositoryCount:
    async def test_count_returns_int(self, repo: _TestRepo, mock_container: MagicMock) -> None:
        mock_container.query_items = MagicMock(return_value=_async_gen_items([5]))
        result = await repo.count()
        assert result == 5

    async def test_count_with_where_clause(
        self, repo: _TestRepo, mock_container: MagicMock
    ) -> None:
        mock_container.query_items = MagicMock(return_value=_async_gen_items([3]))
        result = await repo.count(query="c.status = 'open'")
        assert result == 3
        call_kwargs = mock_container.query_items.call_args.kwargs
        assert "WHERE" in call_kwargs["query"]

    async def test_count_empty_result_returns_zero(
        self, repo: _TestRepo, mock_container: MagicMock
    ) -> None:
        mock_container.query_items = MagicMock(return_value=_async_gen_items([]))
        result = await repo.count()
        assert result == 0

    async def test_count_with_partition_key(
        self, repo: _TestRepo, mock_container: MagicMock
    ) -> None:
        mock_container.query_items = MagicMock(return_value=_async_gen_items([1]))
        await repo.count(partition_key="2025-01")
        call_kwargs = mock_container.query_items.call_args.kwargs
        assert call_kwargs.get("partition_key") == "2025-01"

    async def test_count_propagates_cosmos_error(
        self, repo: _TestRepo, mock_container: MagicMock
    ) -> None:
        mock_container.query_items = MagicMock(side_effect=_make_cosmos_error(500))
        with pytest.raises(CosmosHttpResponseError):
            await repo.count()
