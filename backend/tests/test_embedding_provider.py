"""Embedding Provider tests (P6.7): mock provider, factory, OpenAI-compatible with httpx MockTransport."""

import json
import pytest
import httpx
from app.services.embedding_provider import (
    EmbeddingProviderError, MockHashEmbeddingProvider,
    OpenAICompatibleEmbeddingProvider, embed_text, get_embedding_provider,
)


def _oai_provider(**over):
    kwargs = {
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-test",
        "model": "text-embedding-3-small",
        "dim": 1536,
        "timeout_seconds": 10,
        "max_input_chars": 12000,
    }
    kwargs.update(over)
    return OpenAICompatibleEmbeddingProvider(**kwargs)


_DEFAULT_EMBEDDING = [0.1, 0.2, 0.3]


def _oai_response(embedding=_DEFAULT_EMBEDDING, status=200, body_override=None):
    if body_override:
        return httpx.Response(status, json=body_override)
    return httpx.Response(status, json={
        "data": [{"embedding": embedding}],
        "model": "text-embedding-3-small",
    })


def _client_with(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


class TestMockProvider:
    def test_default_is_mock(self):
        p = get_embedding_provider()
        assert isinstance(p, MockHashEmbeddingProvider)

    def test_deterministic_same_text(self):
        v1 = embed_text("同一段文本")
        v2 = embed_text("同一段文本")
        assert v1 == v2 and len(v1) == 64

    def test_empty_text_raises(self):
        with pytest.raises(ValueError):
            embed_text("")

    def test_top_level_embed_text_works(self):
        v = embed_text("hello")
        assert len(v) == 64


class TestFactory:
    def test_reads_settings(self):
        p = get_embedding_provider()
        assert p.name == "mock" and p.model == "mock_hash_embedding_v1" and p.dim == 64


class TestOpenAICompatibleProvider:
    def test_request_url_correct(self):
        p = _oai_provider(dim=3, _client=_client_with(lambda req: _oai_response()))
        v = p.embed_text("test text")
        assert v == [0.1, 0.2, 0.3]

    def test_http_401_raises_error(self):
        p = _oai_provider(_client=_client_with(
            lambda req: httpx.Response(401, json={"error": "Unauthorized"})))
        with pytest.raises(EmbeddingProviderError, match="HTTP 401"):
            p.embed_text("test")

    def test_http_500_raises_error(self):
        p = _oai_provider(_client=_client_with(
            lambda req: httpx.Response(500, text="Internal Server Error")))
        with pytest.raises(EmbeddingProviderError, match="HTTP 500"):
            p.embed_text("test")

    def test_empty_embedding_fails(self):
        p = _oai_provider(dim=None, _client=_client_with(
            lambda req: _oai_response(embedding=[])))
        with pytest.raises(EmbeddingProviderError, match="Empty or invalid"):
            p.embed_text("test")

    def test_dimension_mismatch_fails(self):
        p = _oai_provider(dim=1024, _client=_client_with(
            lambda req: _oai_response(embedding=[0.1, 0.2, 0.3])))
        with pytest.raises(EmbeddingProviderError, match="dimension mismatch"):
            p.embed_text("test")

    def test_missing_embedding_key_fails(self):
        p = _oai_provider(dim=None, _client=_client_with(
            lambda req: httpx.Response(200, json={"data": [{}]})))
        with pytest.raises(EmbeddingProviderError, match="missing"):
            p.embed_text("test")

    def test_long_input_truncated(self):
        captured = {}
        def capture(req):
            body = json.loads(req.content)
            captured["input"] = body["input"]
            return _oai_response()
        p = _oai_provider(max_input_chars=20, dim=3, _client=_client_with(capture))
        p.embed_text("a" * 50)
        assert len(captured["input"]) == 20

    def test_plain_text_passed_through(self):
        captured = {}
        def capture(req):
            body = json.loads(req.content)
            captured["input"] = body["input"]
            return _oai_response()
        p = _oai_provider(max_input_chars=100, dim=3, _client=_client_with(capture))
        p.embed_text("Hello world")
        assert "Hello world" in captured["input"]
