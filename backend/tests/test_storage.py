"""P3.2 — media storage abstraction.

LocalMediaStorage is the default and is covered fully here (roundtrip, legacy
absolute-path back-compat, traversal rejection). S3MediaStorage is unit-tested
against a tiny in-memory fake boto3 client (key construction, roundtrip, error
normalization) so the S3 code path is exercised without a network; the real
MinIO integration runs in the media-s3-smoke CI job.
"""

import os
from pathlib import Path

import pytest

from storage import (
    LocalMediaStorage,
    S3MediaStorage,
    build_storage,
    get_storage,
    reset_storage_for_tests,
)


# --------------------------------------------------------------------------
# LocalMediaStorage
# --------------------------------------------------------------------------
def test_local_write_exists_stream_roundtrip(tmp_path):
    st = LocalMediaStorage(root=tmp_path)
    key = st.write("op-123", "device-7", b"hello-bytes")
    # New rows record a root-relative POSIX key, never an OS path.
    assert key == "device-7/op-123.bin"
    assert not os.path.isabs(key)
    assert st.exists(key)
    assert b"".join(st.open_stream(key)) == b"hello-bytes"


def test_local_delete_removes_object(tmp_path):
    st = LocalMediaStorage(root=tmp_path)
    key = st.write("op-1", "dev", b"x")
    assert st.exists(key)
    st.delete(key)
    assert not st.exists(key)
    # delete of an absent key is a no-op, never raises.
    st.delete(key)


def test_local_reads_legacy_absolute_path(tmp_path):
    """Historical media_files rows stored an absolute path; the local backend
    must still resolve them (additive migration)."""
    st = LocalMediaStorage(root=tmp_path)
    legacy = tmp_path / "olddevice" / "old-op.bin"
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b"legacy")
    assert st.exists(str(legacy))
    assert b"".join(st.open_stream(str(legacy))) == b"legacy"


def test_local_rejects_traversal(tmp_path):
    st = LocalMediaStorage(root=tmp_path)
    with pytest.raises(ValueError):
        list(st.open_stream("../../etc/passwd"))
    # exists() swallows the traversal into a clean False rather than raising.
    assert st.exists("../../etc/passwd") is False


def test_local_open_missing_raises_filenotfound(tmp_path):
    st = LocalMediaStorage(root=tmp_path)
    with pytest.raises(FileNotFoundError):
        list(st.open_stream("dev/never-written.bin"))


# --------------------------------------------------------------------------
# S3MediaStorage against an in-memory fake client
# --------------------------------------------------------------------------
class _FakeS3:
    def __init__(self):
        self.store = {}

    def put_object(self, Bucket, Key, Body):
        self.store[(Bucket, Key)] = Body

    def get_object(self, Bucket, Key):
        if (Bucket, Key) not in self.store:
            raise KeyError("NoSuchKey")
        data = self.store[(Bucket, Key)]

        class _Body:
            def iter_chunks(self, n):
                yield data

        return {"Body": _Body()}

    def head_object(self, Bucket, Key):
        if (Bucket, Key) not in self.store:
            raise KeyError("404")
        return {}

    def delete_object(self, Bucket, Key):
        self.store.pop((Bucket, Key), None)


def test_s3_roundtrip_with_fake_client():
    fake = _FakeS3()
    st = S3MediaStorage(bucket="evidence", client=fake)
    key = st.write("op-9", "dev-2", b"payload")
    assert key == "dev-2/op-9.bin"
    assert ("evidence", "dev-2/op-9.bin") in fake.store
    assert st.exists(key)
    assert b"".join(st.open_stream(key)) == b"payload"
    st.delete(key)
    assert not st.exists(key)


def test_s3_missing_key_normalizes_to_filenotfound():
    st = S3MediaStorage(bucket="b", client=_FakeS3())
    with pytest.raises(FileNotFoundError):
        list(st.open_stream("dev/absent.bin"))
    assert st.exists("dev/absent.bin") is False


def test_s3_rejects_absolute_and_traversal_keys():
    st = S3MediaStorage(bucket="b", client=_FakeS3())
    for bad in ("/etc/passwd", "a/../../b"):
        with pytest.raises(ValueError):
            list(st.open_stream(bad))
        assert st.exists(bad) is False


# --------------------------------------------------------------------------
# build_storage / get_storage selection
# --------------------------------------------------------------------------
def test_build_storage_defaults_to_local(monkeypatch):
    monkeypatch.delenv("DMRV_MEDIA_BACKEND", raising=False)
    assert isinstance(build_storage(), LocalMediaStorage)


def test_build_storage_s3_requires_bucket(monkeypatch):
    monkeypatch.setenv("DMRV_MEDIA_BACKEND", "s3")
    monkeypatch.delenv("DMRV_MEDIA_BUCKET", raising=False)
    with pytest.raises(RuntimeError):
        build_storage()


def test_get_storage_is_singleton_and_resettable(monkeypatch):
    monkeypatch.delenv("DMRV_MEDIA_BACKEND", raising=False)
    reset_storage_for_tests(None)
    a = get_storage()
    b = get_storage()
    assert a is b
    reset_storage_for_tests(None)  # leave the singleton clean for other suites


# --------------------------------------------------------------------------
# Real MinIO integration — only runs when a live endpoint is provided (CI job).
# --------------------------------------------------------------------------
@pytest.mark.skipif(
    not os.environ.get("DMRV_TEST_S3_ENDPOINT"),
    reason="set DMRV_TEST_S3_ENDPOINT to run the live MinIO integration",
)
def test_s3_live_minio_roundtrip():
    import boto3

    endpoint = os.environ["DMRV_TEST_S3_ENDPOINT"]
    bucket = os.environ.get("DMRV_MEDIA_BUCKET", "evidence-test")
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=os.environ.get("DMRV_S3_ACCESS_KEY", "minioadmin"),
        aws_secret_access_key=os.environ.get("DMRV_S3_SECRET_KEY", "minioadmin"),
        region_name="us-east-1",
    )
    try:
        client.create_bucket(Bucket=bucket)
    except Exception:
        pass  # already exists
    st = S3MediaStorage(bucket=bucket, client=client)
    content = b"live-minio-evidence-bytes"
    key = st.write("live-op", "live-dev", content)
    assert st.exists(key)
    assert b"".join(st.open_stream(key)) == content
