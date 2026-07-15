"""Local-disk storage for dev. Writes under `media_root` and serves the files at
/media/<key> (see main.py mount + the Next /media proxy). Fine for local; use S3
in production (Railway's filesystem is ephemeral)."""
from __future__ import annotations

from pathlib import Path


class LocalStorage:
    name = "local"

    def __init__(self, root: str) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # Keep keys inside the root (defense against traversal).
        p = (self._root / key).resolve()
        if not str(p).startswith(str(self._root.resolve())):
            raise ValueError("invalid storage key")
        return p

    def save(self, *, key: str, data: bytes, content_type: str) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return f"/media/{key}"

    def load(self, key: str) -> bytes | None:
        path = self._path(key)
        return path.read_bytes() if path.exists() else None

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()
