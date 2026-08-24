from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    database_url: str = "sqlite+aiosqlite:///./chenforge.db"

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    resend_api_key: str = ""
    feishu_webhook_url: str = ""

    admin_token: str = "admin-dev-token"

    llm_provider: str = "mock"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"

    # ── Embedding (P6.7) ──
    embedding_provider: str = "mock"
    embedding_model: str = "mock_hash_embedding_v1"
    embedding_base_url: str = ""
    embedding_api_key: str = ""
    embedding_dim: int = 0  # 0 = auto-detect from first response
    embedding_timeout_seconds: int = 20
    embedding_max_input_chars: int = 12000

    # ── Vector Store (P6.8) ──
    vector_store: str = "sqlite_json"  # sqlite_json | pgvector
    pgvector_index_type: str = "hnsw"  # hnsw | ivfflat
    pgvector_distance: str = "cosine"  # cosine (only cosine wired in MVP)
    pgvector_probes: int = 10  # ivfflat probes / hnsw ef_search hint for migration script

    # ── Reranker (P6.10) ──
    reranker_provider: str = "none"  # none | mock | openai_compatible
    reranker_model: str = "none"
    reranker_base_url: str = ""
    reranker_api_key: str = ""
    reranker_timeout_seconds: int = 20
    reranker_max_candidates: int = 20
    reranker_min_candidates: int = 2

    upload_dir: str = "./storage/uploads"
    max_upload_size_mb: int = 20
    knowledge_document_storage_dir: str = "./storage/knowledge_documents"
    knowledge_document_max_size_mb: int = 2

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def knowledge_document_max_size_bytes(self) -> int:
        return self.knowledge_document_max_size_mb * 1024 * 1024


settings = Settings()
settings.upload_dir = str(Path(settings.upload_dir).resolve())
settings.knowledge_document_storage_dir = str(Path(settings.knowledge_document_storage_dir).resolve())
