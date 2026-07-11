"""P3.2 — pluggable evidence-media storage.

Evidence bytes must survive host death, so media lives behind a ``MediaStorage``
seam instead of being written straight to the local disk. Two implementations:

* ``LocalMediaStorage`` — filesystem under ``backend/uploads`` (the zero-config
  default, and what every historical ``media_files`` row points at).
* ``S3MediaStorage`` — boto3 against any S3-compatible store. An explicit
  endpoint makes MinIO (self-hosted) and GCS's S3-interop both work.

Backend selection is by env ``DMRV_MEDIA_BACKEND=local|s3``.

``media_files.file_path`` stores an ABSTRACT KEY for new rows, e.g.
``"device-7/op-abc.bin"`` — never an OS path. Historical rows hold an absolute
filesystem path; ``LocalMediaStorage`` resolves both (a value inside the upload
root is honored verbatim), so this change is fully additive.

This module imports nothing from ``server`` — the upload root is derived the
same way ``server.UPLOAD_DIR`` is (``<this dir>/uploads``) so there is no import
cycle and both point at the same directory.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator, Optional, Protocol, runtime_checkable

_CHUNK = 64 * 1024


def _default_root() -> Path:
    # Mirrors server.UPLOAD_DIR (backend/uploads) without importing server.
    return Path(__file__).parent / "uploads"


@runtime_checkable
class MediaStorage(Protocol):
    """Abstract evidence-media store. Keys are opaque strings persisted in
    ``media_files.file_path``; callers never construct OS paths themselves."""

    def write(self, op_id: str, device: str, content: bytes) -> str:
        """Persist ``content`` and return the stored key to record on the row."""
        ...

    def open_stream(self, stored_path: str) -> Iterator[bytes]:
        """Yield the object's bytes in chunks. Raises ``FileNotFoundError`` if
        the key is absent and ``ValueError`` on an unsafe key."""
        ...

    def exists(self, stored_path: str) -> bool:
        """True if the key resolves to a stored object."""
        ...

    def delete(self, stored_path: str) -> None:
        """Best-effort removal (used to roll back a failed upload). Never raises
        for a missing/invalid key."""
        ...


class LocalMediaStorage:
    """Filesystem backend. Back-compat: a stored value that is an absolute path
    inside the upload root is honored as-is (historical rows), while new writes
    return a root-relative POSIX key."""

    def __init__(self, root: Optional[Path] = None):
        self._root = (root or _default_root()).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, stored: str) -> Path:
        p = Path(stored)
        candidate = (p if p.is_absolute() else self._root / p).resolve()
        # Both new relative keys and legacy absolute paths must land inside the
        # upload root — anything else is a traversal attempt.
        if not candidate.is_relative_to(self._root):
            raise ValueError("path_traversal")
        return candidate

    def write(self, op_id: str, device: str, content: bytes) -> str:
        key = f"{device}/{op_id}.bin"
        dest = self._resolve(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        return key

    def open_stream(self, stored_path: str) -> Iterator[bytes]:
        path = self._resolve(stored_path)
        if not path.is_file():
            raise FileNotFoundError(stored_path)

        def _gen() -> Iterator[bytes]:
            with open(path, "rb") as f:
                while True:
                    chunk = f.read(_CHUNK)
                    if not chunk:
                        break
                    yield chunk

        return _gen()

    def exists(self, stored_path: str) -> bool:
        try:
            return self._resolve(stored_path).is_file()
        except ValueError:
            return False

    def delete(self, stored_path: str) -> None:
        try:
            self._resolve(stored_path).unlink(missing_ok=True)
        except (ValueError, OSError):
            pass


class S3MediaStorage:
    """S3-compatible backend (MinIO / GCS-interop / AWS). Keys are always
    root-relative; absolute or ``..`` keys are rejected so a poisoned row can
    never escape the bucket prefix."""

    def __init__(self, bucket: str, endpoint: Optional[str] = None, client=None):
        self._bucket = bucket
        if client is not None:
            self._client = client
        else:  # pragma: no cover - exercised in the MinIO CI job, not unit tests
            import boto3

            self._client = boto3.client(
                "s3",
                endpoint_url=endpoint or None,
                aws_access_key_id=os.environ.get("DMRV_S3_ACCESS_KEY") or None,
                aws_secret_access_key=os.environ.get("DMRV_S3_SECRET_KEY") or None,
                region_name=os.environ.get("DMRV_S3_REGION") or None,
            )

    @staticmethod
    def _key(stored: str) -> str:
        if stored.startswith("/") or ".." in stored.split("/"):
            raise ValueError("bad_key")
        return stored

    def write(self, op_id: str, device: str, content: bytes) -> str:
        key = f"{device}/{op_id}.bin"
        self._client.put_object(Bucket=self._bucket, Key=self._key(key), Body=content)
        return key

    def open_stream(self, stored_path: str) -> Iterator[bytes]:
        key = self._key(stored_path)
        try:
            obj = self._client.get_object(Bucket=self._bucket, Key=key)
        except Exception as exc:  # noqa: BLE001 — normalize to FileNotFoundError
            raise FileNotFoundError(stored_path) from exc
        return obj["Body"].iter_chunks(_CHUNK)

    def exists(self, stored_path: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=self._key(stored_path))
            return True
        except ValueError:
            return False
        except Exception:  # noqa: BLE001 — any client error ⇒ not present
            return False

    def delete(self, stored_path: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=self._key(stored_path))
        except Exception:  # noqa: BLE001 — best-effort
            pass


def build_storage() -> MediaStorage:
    """Construct the configured backend. ``DMRV_MEDIA_BACKEND=s3`` requires
    ``DMRV_MEDIA_BUCKET``; anything else (or unset) is the local filesystem."""
    backend = os.environ.get("DMRV_MEDIA_BACKEND", "local").strip().lower()
    if backend == "s3":
        bucket = os.environ.get("DMRV_MEDIA_BUCKET")
        if not bucket:
            raise RuntimeError(
                "DMRV_MEDIA_BACKEND=s3 requires DMRV_MEDIA_BUCKET to be set."
            )
        return S3MediaStorage(
            bucket=bucket, endpoint=os.environ.get("DMRV_S3_ENDPOINT") or None
        )
    return LocalMediaStorage()


_storage: Optional[MediaStorage] = None


def get_storage() -> MediaStorage:
    """Process-wide singleton (built once from env at first use)."""
    global _storage
    if _storage is None:
        _storage = build_storage()
    return _storage


def reset_storage_for_tests(instance: Optional[MediaStorage] = None) -> None:
    """Swap (or clear) the singleton — tests only."""
    global _storage
    _storage = instance
