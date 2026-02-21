"""
Embedding service for vector-based ticket deduplication.

Provides:
- build_dedup_text: Concatenates non-PII ticket fields for embedding.
- EmbeddingService: Lazy-init wrapper around AsyncAzureOpenAI embeddings.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from openai import AsyncAzureOpenAI

if TYPE_CHECKING:
    from config import Settings
    from models.ticket import Ticket

logger = logging.getLogger(__name__)


def build_dedup_text(ticket: Ticket) -> str:
    """
    Build a text string for embedding from non-PII ticket fields.

    Concatenates summary, description, category, subcategory,
    merchant, channel, and severity — excluding PII fields
    (name, email, mobile_number, customer_id, account_type).

    Args:
        ticket: Ticket domain model.

    Returns:
        Concatenated text for embedding generation.
    """
    parts = [
        ticket.summary,
        ticket.description or "",
        ticket.category,
        ticket.subcategory or "",
        ticket.merchant or "",
        ticket.channel,
        ticket.severity or "",
    ]
    return " ".join(part for part in parts if part).strip()


class EmbeddingService:
    """
    Lazy-init Azure OpenAI embedding service.

    Does not connect on construction — the AsyncAzureOpenAI client
    is created on first call to generate_embedding(). If Azure OpenAI
    is not configured, the first call raises RuntimeError (caught by
    the route layer as HTTP 503).

    Supports two auth modes controlled by ``azure_openai_use_aad``:
    - **Entra ID (default)**: Uses ``DefaultAzureCredential`` with a
      bearer-token provider — no API key required.
    - **API key**: Uses the ``AZURE_OPENAI_KEY`` secret.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: AsyncAzureOpenAI | None = None

    def _ensure_client(self) -> AsyncAzureOpenAI:
        """Lazily create the AsyncAzureOpenAI client."""
        if self._client is not None:
            return self._client

        endpoint = self._settings.azure_openai_endpoint
        if not endpoint:
            msg = "Azure OpenAI not configured. Set AZURE_OPENAI_ENDPOINT."
            raise RuntimeError(msg)

        if self._settings.azure_openai_use_aad:
            from azure.identity import DefaultAzureCredential, get_bearer_token_provider  # noqa: PLC0415

            credential = DefaultAzureCredential()
            token_provider = get_bearer_token_provider(
                credential,
                "https://cognitiveservices.azure.com/.default",
            )
            self._client = AsyncAzureOpenAI(
                azure_endpoint=endpoint,
                azure_ad_token_provider=token_provider,
                api_version=self._settings.azure_openai_api_version,
            )
            logger.info("Azure OpenAI client initialized with Entra ID for %s", endpoint)
        else:
            key = (
                self._settings.azure_openai_key.get_secret_value()
                if self._settings.azure_openai_key
                else None
            )
            if not key:
                msg = (
                    "Azure OpenAI API key not configured. "
                    "Set AZURE_OPENAI_KEY or use AZURE_OPENAI_USE_AAD=true."
                )
                raise RuntimeError(msg)

            self._client = AsyncAzureOpenAI(
                azure_endpoint=endpoint,
                api_key=key,
                api_version=self._settings.azure_openai_api_version,
            )
            logger.info("Azure OpenAI client initialized with API key for %s", endpoint)

        return self._client

    async def generate_embedding(self, text: str) -> list[float]:
        """
        Generate an embedding vector for the given text.

        Args:
            text: Input text to embed.

        Returns:
            List of floats representing the embedding vector.

        Raises:
            RuntimeError: If Azure OpenAI is not configured.
            openai.OpenAIError: If the API call fails.
        """
        client = self._ensure_client()
        response = await client.embeddings.create(
            input=text,
            model=self._settings.azure_openai_embedding_deployment,
            dimensions=self._settings.azure_openai_embedding_dimensions,
        )
        return response.data[0].embedding

    async def close(self) -> None:
        """Close the underlying HTTP client if initialized."""
        if self._client is not None:
            await self._client.close()
            self._client = None
