"""Reranker provider tests (P6.10)."""

import json

import httpx
import pytest

from app.services.reranker_provider import (
    MockRerankerProvider,
    NoneRerankerProvider,
    OpenAICompatibleRerankerProvider,
    RerankerProviderError,
)


def _candidate(cid: str, **over):
    base = {
        "knowledge_item_id": cid,
        "title": "通用知识",
        "summary": "",
        "excerpt": "",
        "tags": [],
        "score": 10,
    }
    base.update(over)
    return base


class TestNoneRerankerProvider:
    def test_none_provider_preserves_order_without_extra_scores(self):
        candidates = [_candidate("a"), _candidate("b")]
        result = NoneRerankerProvider().rerank("企业微信自动回复", candidates)
        assert [c["knowledge_item_id"] for c in result] == ["a", "b"]
        assert all("rerank_score" not in c for c in result)


class TestMockRerankerProvider:
    def test_mock_provider_prefers_query_terms_in_business_fields(self):
        candidates = [
            _candidate("generic", title="通用实施说明", summary="销售流程说明", score=50),
            _candidate("specific", title="企业微信客服自动回复", summary="客户消息及时响应", score=10),
        ]
        result = MockRerankerProvider().rerank("企业微信自动回复", candidates)
        assert [c["knowledge_item_id"] for c in result] == ["specific", "generic"]
        assert result[0]["reranked"] is True
        assert result[0]["rerank_score"] > result[1]["rerank_score"]
        assert "mock_overlap" in result[0]["rerank_reason"]

    def test_mock_provider_never_adds_new_candidates(self):
        candidates = [_candidate("a"), _candidate("b")]
        result = MockRerankerProvider().rerank("无匹配", candidates)
        assert sorted(c["knowledge_item_id"] for c in result) == ["a", "b"]


class TestOpenAICompatibleRerankerProvider:
    def test_openai_compatible_provider_sends_minimal_candidate_payload(self):
        captured = {}

        def handler(req):
            captured["body"] = json.loads(req.content)
            return httpx.Response(
                200,
                json={
                    "results": [
                        {"knowledge_item_id": "b", "score": 0.91, "reason": "更匹配渠道"},
                        {"knowledge_item_id": "a", "score": 0.31, "reason": "泛化说明"},
                    ]
                },
            )

        provider = OpenAICompatibleRerankerProvider(
            base_url="https://reranker.example/v1",
            api_key="sk-test",
            model="rerank-model",
            timeout_seconds=10,
            _client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        candidates = [
            _candidate("a", title="通用说明", excerpt="A" * 500),
            _candidate("b", title="企业微信客服自动回复", excerpt="B" * 500),
        ]
        result = provider.rerank("企业微信自动回复", candidates)

        assert [c["knowledge_item_id"] for c in result] == ["b", "a"]
        assert captured["body"]["model"] == "rerank-model"
        assert "content_markdown" not in captured["body"]["candidates"][0]
        assert len(captured["body"]["candidates"][0]["excerpt"]) <= 260

    def test_openai_compatible_provider_rejects_unknown_candidate_id(self):
        provider = OpenAICompatibleRerankerProvider(
            base_url="https://reranker.example/v1",
            api_key="sk-test",
            model="rerank-model",
            timeout_seconds=10,
            _client=httpx.Client(transport=httpx.MockTransport(
                lambda req: httpx.Response(200, json={"results": [{"knowledge_item_id": "outside", "score": 1.0}]})
            )),
        )
        with pytest.raises(RerankerProviderError, match="unknown candidate"):
            provider.rerank("query", [_candidate("a")])
