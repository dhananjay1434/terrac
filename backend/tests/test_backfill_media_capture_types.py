import pytest
import uuid
import json

from sqlalchemy import select
from datetime import datetime, timezone

from models import (
    MediaFile,
    PyrolysisTelemetry,
    Batch,
    EndUseApplication,
    MoistureReading,
    CompositePileSample,
)
from scripts.backfill_media_capture_types import backfill

pytestmark = pytest.mark.asyncio

async def test_backfill_media_capture_types(session_factory):
    async with session_factory() as s:
        b1 = str(uuid.uuid4())
        b2 = str(uuid.uuid4())
        b3 = str(uuid.uuid4())

        def make_batch(bu, sha=None):
            return Batch(
                batch_uuid=bu, 
                operation_id="op-" + bu,
                feedstock_species="Pine",
                harvest_timestamp=datetime.now(timezone.utc),
                moisture_percent=10.0,
                harvest_uptime_seconds=3600,
                device_id="test",
                sha256_hash=sha
            )

        # Batch 1 for telemetry
        s.add(make_batch(b1))
        s.add(PyrolysisTelemetry(
            telemetry_uuid=str(uuid.uuid4()),
            batch_uuid=b1,
            payload_json=json.dumps({"smoke_evidence": [{"stage": "flame_curtain", "sha256": "tel-hash"}]})
        ))
        s.add(MediaFile(
            batch_uuid=b1,
            operation_id="m-1",
            file_path="dummy.jpg",
            sha256_hash="tel-hash",
            capture_type_verified=False
        ))

        # Batch 2 for labcert
        s.add(make_batch(b2))
        s.add(MediaFile(
            batch_uuid=b2,
            operation_id="labcert-123",
            file_path="dummy.jpg",
            sha256_hash="lab-hash",
            capture_type_verified=False
        ))

        # Batch 3 for batch anchor
        s.add(make_batch(b3, sha="anchor-hash"))
        s.add(MediaFile(
            batch_uuid=b3,
            operation_id="m-2",
            file_path="dummy.jpg",
            sha256_hash="anchor-hash",
            capture_type_verified=False
        ))

        # Unchanged media
        s.add(MediaFile(
            batch_uuid=b3,
            operation_id="m-3",
            file_path="dummy.jpg",
            sha256_hash="random-hash",
            capture_type_verified=False
        ))

        # Batch 4 for a legacy farmer end-use photo (predates the app stamping
        # capture_type=end_use at capture time — the payload_json still has
        # the farmer_photo_sha256 the backfill must match against).
        b4 = str(uuid.uuid4())
        s.add(make_batch(b4))
        s.add(EndUseApplication(
            application_uuid=str(uuid.uuid4()),
            batch_uuid=b4,
            payload_json=json.dumps({
                "batch_uuid": b4,
                "farmer_photo_sha256": "farmer-hash",
            }),
        ))
        s.add(MediaFile(
            batch_uuid=b4,
            operation_id="m-4",
            file_path="dummy.jpg",
            sha256_hash="farmer-hash",
            capture_type_verified=False
        ))

        # Batch 5: moisture (C2) + composite (C4) photos that landed with a NULL
        # capture_type (the "Other / Uncategorized" bug). One moisture reading
        # REUSED the batch anchor image (sha == batch.sha256_hash) — that photo
        # must stay batch_photo, not be stolen by the moisture rule.
        b5 = str(uuid.uuid4())
        s.add(make_batch(b5, sha="b5-anchor-hash"))
        # moisture reading #1 reused the anchor image
        s.add(MoistureReading(
            reading_uuid=str(uuid.uuid4()), batch_uuid=b5,
            payload_json=json.dumps({"sequence": 1, "sha256_hash": "b5-anchor-hash"}),
        ))
        # moisture reading #2 — a distinct shot
        s.add(MoistureReading(
            reading_uuid=str(uuid.uuid4()), batch_uuid=b5,
            payload_json=json.dumps({"sequence": 2, "sha256_hash": "moist-hash-2"}),
        ))
        s.add(CompositePileSample(
            sample_uuid=str(uuid.uuid4()), batch_uuid=b5,
            payload_json=json.dumps({"sha256_hash": "composite-hash"}),
        ))
        s.add(MediaFile(batch_uuid=b5, operation_id="m-anchor",
                        file_path="d.jpg", sha256_hash="b5-anchor-hash", capture_type_verified=False))
        s.add(MediaFile(batch_uuid=b5, operation_id="m-moist2",
                        file_path="d.jpg", sha256_hash="moist-hash-2", capture_type_verified=False))
        s.add(MediaFile(batch_uuid=b5, operation_id="m-comp",
                        file_path="d.jpg", sha256_hash="composite-hash", capture_type_verified=False))

        await s.commit()

    async with session_factory() as s:
        counts = await backfill(s, apply=True)
        assert counts["telemetry"] == 1
        assert counts["lab_certificate"] == 1
        assert counts["end_use"] == 1
        assert counts["batch_photo"] == 2  # b3 anchor + b5 reused-anchor
        assert counts["moisture"] == 1     # only the distinct shot; anchor reuse skipped
        assert counts["composite_sample"] == 1
        assert counts["unchanged"] == 1

        # Check DB updates
        m1 = (await s.execute(select(MediaFile).where(MediaFile.operation_id == "m-1"))).scalar_one()
        assert m1.capture_type == "flame_curtain"
        assert m1.capture_type_verified is True

        m2 = (await s.execute(select(MediaFile).where(MediaFile.operation_id == "labcert-123"))).scalar_one()
        assert m2.capture_type == "lab_certificate"
        assert m2.capture_type_verified is True

        m3 = (await s.execute(select(MediaFile).where(MediaFile.operation_id == "m-2"))).scalar_one()
        assert m3.capture_type == "batch_photo"
        assert m3.capture_type_verified is True

        m4 = (await s.execute(select(MediaFile).where(MediaFile.operation_id == "m-3"))).scalar_one()
        assert m4.capture_type is None
        assert m4.capture_type_verified is False

        m5 = (await s.execute(select(MediaFile).where(MediaFile.operation_id == "m-4"))).scalar_one()
        assert m5.capture_type == "end_use"
        assert m5.capture_type_verified is False

        # b5: the reused-anchor moisture photo is batch_photo (verified, trust-root),
        # NOT stolen by the moisture rule.
        anchor = (await s.execute(select(MediaFile).where(MediaFile.operation_id == "m-anchor"))).scalar_one()
        assert anchor.capture_type == "batch_photo"
        assert anchor.capture_type_verified is True
        # the distinct moisture + composite shots get their (unverified) labels.
        moist2 = (await s.execute(select(MediaFile).where(MediaFile.operation_id == "m-moist2"))).scalar_one()
        assert moist2.capture_type == "moisture"
        assert moist2.capture_type_verified is False
        comp = (await s.execute(select(MediaFile).where(MediaFile.operation_id == "m-comp"))).scalar_one()
        assert comp.capture_type == "composite_sample"
        assert comp.capture_type_verified is False
