"""Local storage adapter for generated proposal PDFs.

Path: storage/proposals/{opportunity_id}/{artifact_id}/proposal.pdf
"""

import os


class ProposalPdfStorage:
    """Local filesystem storage for proposal PDFs."""

    def __init__(self, base_dir: str | None = None):
        self.base_dir = base_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "storage", "proposals",
        )

    def _ensure_dir(self, opportunity_id: str, artifact_id: str) -> str:
        d = os.path.join(self.base_dir, opportunity_id, artifact_id)
        os.makedirs(d, exist_ok=True)
        return d

    def path(self, opportunity_id: str, artifact_id: str) -> str:
        d = self._ensure_dir(opportunity_id, artifact_id)
        return os.path.join(d, "proposal.pdf")

    def get(self, opportunity_id: str, artifact_id: str) -> bytes | None:
        p = self.path(opportunity_id, artifact_id)
        if os.path.exists(p):
            with open(p, "rb") as f:
                return f.read()
        return None

    def save(self, opportunity_id: str, artifact_id: str, pdf_bytes: bytes) -> str:
        p = self.path(opportunity_id, artifact_id)
        with open(p, "wb") as f:
            f.write(pdf_bytes)
        return p


# Module-level singleton
storage = ProposalPdfStorage()
