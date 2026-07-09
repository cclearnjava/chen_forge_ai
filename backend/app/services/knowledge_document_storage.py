"""Knowledge document local file storage (P6).

Files land under a per-workspace / per-document directory tree. The stored path
is always system-generated — the untrusted upload filename is never used for the
path, only for display. All writes are confined to the storage root.
"""

import os
from pathlib import Path
from app.config import settings


def _storage_root() -> Path:
    return Path(settings.knowledge_document_storage_dir).resolve()


def save_knowledge_document_file(workspace_id: str, document_id: str, filename: str, content: bytes) -> str:
    """Persist an uploaded file and return its path relative to the storage root.

    The directory is derived from workspace_id + document_id (both system UUIDs);
    the untrusted filename only contributes a sanitized extension.
    """
    root = _storage_root()
    # Only trust the extension from the filename; strip any path components.
    ext = os.path.splitext(os.path.basename(filename or ""))[1].lower()
    target_dir = (root / workspace_id / document_id).resolve()

    # Confinement: target must stay under the storage root (no traversal).
    if not str(target_dir).startswith(str(root)):
        raise ValueError("Resolved storage path escapes storage root")

    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"original{ext}"
    target.write_bytes(content)

    return str(target.relative_to(root))
