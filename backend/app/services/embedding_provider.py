"""Embedding Provider abstraction — deterministic mock for MVP, zero network.

P6.5: mock_hash_embedding_v1 produces a stable 64-dim L2-normalized vector from
any text input using deterministic SHA-256 → hash-bucket mapping. Same text always
produces the same vector — stable for CI and local testing. Real providers (OpenAI-
compatible / local sentence-transformer) are deferred to P6.6.
"""

import hashlib
import math
import struct

MOCK_PROVIDER_NAME = "mock"
MOCK_MODEL = "mock_hash_embedding_v1"
MOCK_DIM = 64


def _hash_to_floats(text: str, dim: int) -> list[float]:
    """Derive `dim` floats in [-1, 1) from sha256(text). Deterministic across runs."""
    raw = hashlib.sha256(text.encode("utf-8")).digest()
    vals: list[float] = []
    # Unpack 4-byte big-endian ints, map to [-1, 1)
    num_ints = len(raw) // 4
    for i in range(num_ints):
        n = struct.unpack(">i", raw[i * 4: (i + 1) * 4])[0]
        vals.append((n / 2_147_483_648.0))  # scale int32 to [-1.0, 1.0)
    # Extend / tile if we need more than 8 floats
    while len(vals) < dim:
        vals.append(vals[len(vals) % len(vals)] * 0.9)
    return vals[:dim]


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0.0:
        return [0.0] * len(vec)
    return [v / norm for v in vec]


def embed_text(text: str) -> list[float]:
    """Return a deterministic 64-dim L2-normalized vector. Fails closed on empty text."""
    if not text or not text.strip():
        raise ValueError("Cannot embed empty text")
    return _l2_normalize(_hash_to_floats(text, MOCK_DIM))
