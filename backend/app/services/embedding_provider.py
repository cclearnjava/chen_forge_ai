"""Embedding Provider abstraction (P6.7).

Mock provider: deterministic SHA-256 → 64-dim L2-normalized, zero network (default).
OpenAI-compatible provider: configurable endpoint, httpx with timeout, Bearer auth.
All access via get_embedding_provider() factory; top-level embed_text(text) preserved
for backward compatibility with knowledge_vectors.py.
"""

import hashlib
import math
import struct
from typing import Protocol

import httpx
from app.config import settings

MOCK_PROVIDER_NAME = "mock"
MOCK_MODEL = "mock_hash_embedding_v1"
MOCK_DIM = 64


# ── errors ──

class EmbeddingProviderError(Exception):
    """Raised when the provider cannot produce an embedding (network, auth, format)."""


# ── protocol ──

class EmbeddingProvider(Protocol):
    name: str
    model: str
    dim: int | None

    def embed_text(self, text: str) -> list[float]: ...


# ── mock provider (existing logic, now a class) ──

def _hash_to_floats(text: str, dim: int) -> list[float]:
    raw = hashlib.sha256(text.encode("utf-8")).digest()
    vals: list[float] = []
    num_ints = len(raw) // 4
    for i in range(num_ints):
        n = struct.unpack(">i", raw[i * 4: (i + 1) * 4])[0]
        vals.append(n / 2_147_483_648.0)
    while len(vals) < dim:
        vals.append(vals[len(vals) % len(vals)] * 0.9)
    return vals[:dim]


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0.0:
        return [0.0] * len(vec)
    return [v / norm for v in vec]


class MockHashEmbeddingProvider:
    def __init__(self):
        self.name = "mock"
        self.model = "mock_hash_embedding_v1"
        self.dim = 64

    def embed_text(self, text: str) -> list[float]:
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text")
        return _l2_normalize(_hash_to_floats(text, self.dim))  # type: ignore[arg-type]


# ── OpenAI-compatible provider ──

class OpenAICompatibleEmbeddingProvider:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        dim: int | None,
        timeout_seconds: int,
        max_input_chars: int,
        _client: httpx.Client | None = None,
    ):
        self.name = "openai_compatible"
        self.model = model
        self.dim = dim
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout_seconds
        self.max_input_chars = max_input_chars
        self._client = _client  # for testing with MockTransport

    def embed_text(self, text: str) -> list[float]:
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text")
        # Truncate to configured max input chars
        input_text = text[: self.max_input_chars] if len(text) > self.max_input_chars else text
        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {"model": self.model, "input": input_text}
        try:
            client = self._client or httpx
            if self._client is not None:
                resp = client.post(url, json=body, headers=headers)
            else:
                resp = httpx.post(url, json=body, headers=headers, timeout=self.timeout)
            if not resp.is_success:
                raise EmbeddingProviderError(f"HTTP {resp.status_code}: {resp.text[:200]}")
            data = resp.json()
        except httpx.TimeoutException:
            raise EmbeddingProviderError(f"Request timed out after {self.timeout}s")
        except httpx.RequestError as exc:
            raise EmbeddingProviderError(f"Request failed: {exc}")
        except ValueError as exc:
            raise EmbeddingProviderError(f"Invalid JSON response: {exc}")

        try:
            embedding = data["data"][0]["embedding"]
        except (KeyError, IndexError, TypeError):
            raise EmbeddingProviderError("Response missing data[0].embedding")
        if not embedding or not isinstance(embedding, list):
            raise EmbeddingProviderError("Empty or invalid embedding in response")
        if not all(isinstance(x, (int, float)) for x in embedding):
            raise EmbeddingProviderError("Embedding contains non-numeric values")
        if self.dim and len(embedding) != self.dim:
            raise EmbeddingProviderError(
                f"Embedding dimension mismatch: expected {self.dim}, got {len(embedding)}"
            )
        return [float(x) for x in embedding]


# ── factory ──

_provider: EmbeddingProvider | None = None


def get_embedding_provider() -> EmbeddingProvider:
    global _provider
    if _provider is not None:
        return _provider

    provider_name = settings.embedding_provider
    if provider_name == "mock":
        _provider = MockHashEmbeddingProvider()
    elif provider_name == "openai_compatible":
        _provider = OpenAICompatibleEmbeddingProvider(
            base_url=settings.embedding_base_url,
            api_key=settings.embedding_api_key,
            model=settings.embedding_model or "text-embedding-3-small",
            dim=settings.embedding_dim or None,
            timeout_seconds=settings.embedding_timeout_seconds,
            max_input_chars=settings.embedding_max_input_chars,
        )
    else:
        raise EmbeddingProviderError(f"Unknown embedding provider: {provider_name}")
    return _provider


def embed_text(text: str) -> list[float]:
    """Convenience top-level function — backward-compatible with existing callers."""
    return get_embedding_provider().embed_text(text)
