"""Reranker provider abstraction (P6.10).

The reranker only reorders already-retrieved candidates.  It never adds new
KnowledgeItems, and the default provider is local/no-op to keep self-hosted
deployments private by default.
"""

from typing import Protocol

import httpx

from app.config import settings
from app.services.text_utils import as_text_list, overlap_score

MOCK_RERANKER_MODEL = "mock_overlap_reranker_v1"
MAX_EXCERPT_CHARS_FOR_RERANK = 260


class RerankerProviderError(Exception):
    """Raised when a reranker cannot produce a trusted candidate ordering."""


class RerankerProvider(Protocol):
    name: str
    model: str

    def rerank(self, query: str, candidates: list[dict]) -> list[dict]: ...


class NoneRerankerProvider:
    name = "none"
    model = "none"

    def rerank(self, query: str, candidates: list[dict]) -> list[dict]:
        return [dict(c) for c in candidates]


class MockRerankerProvider:
    name = "mock"
    model = MOCK_RERANKER_MODEL

    def rerank(self, query: str, candidates: list[dict]) -> list[dict]:
        scored: list[tuple[float, int, dict]] = []
        for idx, candidate in enumerate(candidates):
            title_score = overlap_score(query, candidate.get("title") or "") * 6
            summary_score = overlap_score(query, candidate.get("summary") or "") * 3
            excerpt_score = overlap_score(query, candidate.get("excerpt") or "")
            tag_score = overlap_score(query, as_text_list(candidate.get("tags") or [])) * 2
            base_score = float(candidate.get("score") or 0) / 100.0
            rerank_score = float(title_score + summary_score + excerpt_score + tag_score) + base_score
            enriched = dict(candidate)
            enriched["reranked"] = True
            enriched["rerank_score"] = round(rerank_score, 4)
            enriched["rerank_reason"] = "mock_overlap"
            scored.append((rerank_score, -idx, enriched))

        scored.sort(key=lambda row: (-row[0], row[1]))
        return [row[2] for row in scored]


class OpenAICompatibleRerankerProvider:
    name = "openai_compatible"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: int,
        _client: httpx.Client | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._client = _client

    def rerank(self, query: str, candidates: list[dict]) -> list[dict]:
        if not query or not query.strip():
            return [dict(c) for c in candidates]
        by_id = {c.get("knowledge_item_id"): dict(c) for c in candidates}
        payload_candidates = [_minimal_candidate_payload(c) for c in candidates]
        body = {
            "model": self.model,
            "query": query,
            "candidates": payload_candidates,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            client = self._client or httpx
            url = f"{self.base_url}/rerank"
            if self._client is not None:
                resp = client.post(url, json=body, headers=headers)
            else:
                resp = httpx.post(url, json=body, headers=headers, timeout=self.timeout_seconds)
            if not resp.is_success:
                raise RerankerProviderError(f"HTTP {resp.status_code}: {resp.text[:200]}")
            data = resp.json()
        except httpx.TimeoutException:
            raise RerankerProviderError(f"Request timed out after {self.timeout_seconds}s")
        except httpx.RequestError as exc:
            raise RerankerProviderError(f"Request failed: {exc}")
        except ValueError as exc:
            raise RerankerProviderError(f"Invalid JSON response: {exc}")

        results = data.get("results")
        if not isinstance(results, list):
            raise RerankerProviderError("Response missing results")

        ranked: list[dict] = []
        seen: set[str] = set()
        for row in results:
            if not isinstance(row, dict):
                raise RerankerProviderError("Invalid result row")
            item_id = row.get("knowledge_item_id")
            if item_id not in by_id:
                raise RerankerProviderError(f"unknown candidate id from reranker: {item_id}")
            if item_id in seen:
                continue
            candidate = dict(by_id[item_id])
            candidate["reranked"] = True
            candidate["rerank_score"] = float(row.get("score") or 0.0)
            candidate["rerank_reason"] = row.get("reason") or "openai_compatible"
            ranked.append(candidate)
            seen.add(item_id)

        for candidate in candidates:
            item_id = candidate.get("knowledge_item_id")
            if item_id not in seen:
                ranked.append(dict(candidate))
        return ranked


def _minimal_candidate_payload(candidate: dict) -> dict:
    return {
        "knowledge_item_id": candidate.get("knowledge_item_id"),
        "title": candidate.get("title"),
        "summary": candidate.get("summary"),
        "excerpt": (candidate.get("excerpt") or "")[:MAX_EXCERPT_CHARS_FOR_RERANK],
        "tags": candidate.get("tags") or [],
        "source_type": candidate.get("source_type"),
        "score": candidate.get("score"),
        "keyword_score": candidate.get("keyword_score"),
        "vector_score": candidate.get("vector_score"),
        "retrieval_mode": candidate.get("retrieval_mode"),
    }


_provider: RerankerProvider | None = None


def get_reranker_provider() -> RerankerProvider:
    global _provider
    if _provider is not None:
        return _provider

    provider_name = settings.reranker_provider
    if provider_name == "none":
        _provider = NoneRerankerProvider()
    elif provider_name == "mock":
        _provider = MockRerankerProvider()
    elif provider_name == "openai_compatible":
        _provider = OpenAICompatibleRerankerProvider(
            base_url=settings.reranker_base_url,
            api_key=settings.reranker_api_key,
            model=settings.reranker_model or "reranker",
            timeout_seconds=settings.reranker_timeout_seconds,
        )
    else:
        raise RerankerProviderError(f"Unknown reranker provider: {provider_name}")
    return _provider
