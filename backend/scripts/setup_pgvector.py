"""Idempotent pgvector setup for the knowledge_vectors table (P6.8).

Creates the vector extension, adds the Postgres-only `embedding_vector` column
(dimension = EMBEDDING_DIM), and builds the metadata + ANN indexes. Safe to run
multiple times — every statement is IF NOT EXISTS.

The `embedding_vector` column is intentionally NOT declared in the SQLAlchemy model
(it has no SQLite equivalent); it lives only in Postgres and is managed by this script.

Usage (from backend/):
    .venv/bin/python scripts/setup_pgvector.py

Requires:
    VECTOR_STORE=pgvector
    DATABASE_URL=postgresql+psycopg://...
    EMBEDDING_DIM=<positive int matching your embedding provider's dimension>
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402
from app.config import settings  # noqa: E402
from app.db import engine  # noqa: E402


def _fail(msg: str) -> None:
    print(f"[setup_pgvector] ERROR: {msg}")
    sys.exit(1)


def main() -> None:
    dialect = engine.dialect.name
    if dialect != "postgresql":
        _fail(f"VECTOR_STORE=pgvector requires PostgreSQL, but DATABASE_URL dialect is '{dialect}'.")
    if settings.embedding_dim <= 0:
        _fail("EMBEDDING_DIM must be a positive integer (pgvector column needs a fixed dimension).")

    dim = settings.embedding_dim
    index_type = (settings.pgvector_index_type or "hnsw").lower()
    if index_type not in ("hnsw", "ivfflat"):
        _fail(f"Unsupported PGVECTOR_INDEX_TYPE='{index_type}' (expected hnsw or ivfflat).")

    statements = [
        "CREATE EXTENSION IF NOT EXISTS vector",
        f"ALTER TABLE knowledge_vectors ADD COLUMN IF NOT EXISTS embedding_vector vector({dim})",
        (
            "CREATE INDEX IF NOT EXISTS idx_knowledge_vectors_ws_model_status "
            "ON knowledge_vectors (workspace_id, embedding_model, status)"
        ),
    ]
    if index_type == "hnsw":
        statements.append(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_vectors_embedding_hnsw "
            "ON knowledge_vectors USING hnsw (embedding_vector vector_cosine_ops)"
        )
    else:
        statements.append(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_vectors_embedding_ivfflat "
            "ON knowledge_vectors USING ivfflat (embedding_vector vector_cosine_ops) WITH (lists = 100)"
        )

    with engine.begin() as conn:
        for stmt in statements:
            print(f"[setup_pgvector] {stmt}")
            conn.execute(text(stmt))

    print(f"[setup_pgvector] Done. embedding_vector is vector({dim}) with {index_type} cosine index.")


if __name__ == "__main__":
    main()
