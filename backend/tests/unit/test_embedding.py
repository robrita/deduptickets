"""
Unit tests for the EmbeddingService and build_dedup_text helper.

Covers:
- build_dedup_text: all fields, minimal fields, empty optional fields
- EmbeddingService._ensure_client: no endpoint, key auth path
- EmbeddingService.generate_embedding: happy path with mocked OpenAI client
- EmbeddingService.close: both when client is None and when initialized
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lib.embedding import EmbeddingService, build_dedup_text
from models.ticket import Ticket

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ticket(**kwargs: object) -> Ticket:
    from datetime import datetime  # noqa: PLC0415
    from uuid import uuid4  # noqa: PLC0415

    defaults: dict = {
        "id": uuid4(),
        "pk": "2025-01",
        "ticket_number": "TKT-001",
        "created_at": datetime(2025, 1, 1),
        "updated_at": datetime(2025, 1, 1),
        "channel": "in_app",
        "customer_id": "CUST-1",
        "category": "Billing",
        "summary": "Payment error",
    }
    defaults.update(kwargs)
    return Ticket(**defaults)  # type: ignore[arg-type]


def _make_settings(
    *,
    endpoint: str | None = "https://test.openai.azure.com",
    use_aad: bool = False,
    key: str | None = "sk-test-key",
    deployment: str = "text-embedding-3-small",
) -> MagicMock:
    settings = MagicMock()
    settings.azure_openai_endpoint = endpoint
    settings.azure_openai_use_aad = use_aad
    settings.azure_openai_api_version = "2024-02-01"
    settings.azure_openai_embedding_deployment = deployment
    settings.azure_openai_embedding_dimensions = 1536
    if key is not None:
        secret = MagicMock()
        secret.get_secret_value.return_value = key
        settings.azure_openai_key = secret
    else:
        settings.azure_openai_key = None
    return settings


# ---------------------------------------------------------------------------
# build_dedup_text
# ---------------------------------------------------------------------------


class TestBuildDedupText:
    def test_uses_all_fields(self) -> None:
        ticket = _make_ticket(
            summary="payment error",
            description="gateway timeout",
            category="Billing",
            subcategory="Payment",
            merchant="ACME",
            channel="email",
            severity="high",
        )
        text = build_dedup_text(ticket)
        assert "payment error" in text
        assert "gateway timeout" in text
        assert "Billing" in text
        assert "Payment" in text
        assert "ACME" in text
        assert "email" in text
        assert "high" in text

    def test_minimal_fields_no_error(self) -> None:
        ticket = _make_ticket(
            summary="minimal ticket",
            description=None,
            subcategory=None,
            merchant=None,
            severity=None,
        )
        text = build_dedup_text(ticket)
        assert "minimal ticket" in text

    def test_empty_optionals_not_in_output(self) -> None:
        ticket = _make_ticket(
            summary="test",
            description=None,
            subcategory=None,
            merchant=None,
            severity=None,
        )
        text = build_dedup_text(ticket)
        # Should not have trailing spaces from empty parts
        assert "  " not in text

    def test_returns_string(self) -> None:
        ticket = _make_ticket(summary="check type")
        result = build_dedup_text(ticket)
        assert isinstance(result, str)

    def test_pii_fields_not_included(self) -> None:
        """customer_id must never appear in the embedding text."""
        ticket = _make_ticket(summary="check pii", customer_id="CUST-SECRET-99")
        text = build_dedup_text(ticket)
        assert "CUST-SECRET-99" not in text


# ---------------------------------------------------------------------------
# EmbeddingService._ensure_client
# ---------------------------------------------------------------------------


class TestEmbeddingServiceEnsureClient:
    def test_raises_if_no_endpoint(self) -> None:
        settings = _make_settings(endpoint=None)
        svc = EmbeddingService(settings)
        with pytest.raises(RuntimeError, match="AZURE_OPENAI_ENDPOINT"):
            svc._ensure_client()

    def test_raises_if_key_auth_no_key(self) -> None:
        settings = _make_settings(use_aad=False, key=None)
        svc = EmbeddingService(settings)
        with pytest.raises(RuntimeError, match="AZURE_OPENAI_KEY"):
            svc._ensure_client()

    def test_key_auth_creates_client(self) -> None:
        settings = _make_settings(use_aad=False, key="sk-valid")
        svc = EmbeddingService(settings)
        with patch("lib.embedding.AsyncAzureOpenAI") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client
            client = svc._ensure_client()
        assert client is mock_client
        assert svc._client is mock_client

    def test_key_auth_reuses_existing_client(self) -> None:
        settings = _make_settings(use_aad=False, key="sk-valid")
        svc = EmbeddingService(settings)
        fake_client = MagicMock()
        svc._client = fake_client
        result = svc._ensure_client()
        assert result is fake_client

    def test_aad_auth_creates_client(self) -> None:
        settings = _make_settings(use_aad=True)
        svc = EmbeddingService(settings)
        with (
            patch("lib.embedding.AsyncAzureOpenAI") as MockClient,
            patch("azure.identity.DefaultAzureCredential"),
            patch("azure.identity.get_bearer_token_provider") as MockProvider,
        ):
            MockProvider.return_value = MagicMock()
            mock_client = MagicMock()
            MockClient.return_value = mock_client
            client = svc._ensure_client()
        assert client is mock_client


# ---------------------------------------------------------------------------
# EmbeddingService.generate_embedding
# ---------------------------------------------------------------------------


class TestEmbeddingServiceGenerateEmbedding:
    async def test_returns_float_list(self) -> None:
        settings = _make_settings()
        svc = EmbeddingService(settings)

        mock_embedding_response = MagicMock()
        mock_embedding_response.data = [MagicMock(embedding=[0.1] * 1536)]

        mock_client = MagicMock()
        mock_client.embeddings.create = AsyncMock(return_value=mock_embedding_response)

        with patch("lib.embedding.AsyncAzureOpenAI", return_value=mock_client):
            result = await svc.generate_embedding("test text")

        assert isinstance(result, list)
        assert len(result) == 1536
        assert result[0] == 0.1

    async def test_calls_create_with_correct_model(self) -> None:
        settings = _make_settings(deployment="text-embedding-ada-002")
        svc = EmbeddingService(settings)

        mock_embedding_response = MagicMock()
        mock_embedding_response.data = [MagicMock(embedding=[0.0])]

        mock_client = MagicMock()
        mock_client.embeddings.create = AsyncMock(return_value=mock_embedding_response)

        with patch("lib.embedding.AsyncAzureOpenAI", return_value=mock_client):
            await svc.generate_embedding("input text")

        mock_client.embeddings.create.assert_awaited_once()
        kwargs = mock_client.embeddings.create.call_args.kwargs
        assert kwargs["model"] == "text-embedding-ada-002"

    async def test_raises_if_not_configured(self) -> None:
        settings = _make_settings(endpoint=None)
        svc = EmbeddingService(settings)
        with pytest.raises(RuntimeError):
            await svc.generate_embedding("test")


# ---------------------------------------------------------------------------
# EmbeddingService.close
# ---------------------------------------------------------------------------


class TestEmbeddingServiceClose:
    async def test_close_when_no_client(self) -> None:
        settings = _make_settings()
        svc = EmbeddingService(settings)
        # Must not raise even if client was never initialised
        await svc.close()
        assert svc._client is None

    async def test_close_when_client_initialised(self) -> None:
        settings = _make_settings()
        svc = EmbeddingService(settings)

        mock_client = AsyncMock()
        svc._client = mock_client

        await svc.close()

        mock_client.close.assert_awaited_once()
        assert svc._client is None
