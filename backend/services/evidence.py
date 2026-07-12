import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from models import Batch
from credit_engine import recompute_batch_credit

async def _assert_batch_ownership(
    session: AsyncSession, batch_uuid_str: str, device_id: str
) -> None:
    """Reject evidence targeting a batch owned by a DIFFERENT device.

    Security (batch-ownership hardening): the evidence endpoints authenticate the
    caller but historically never checked that the caller owns the batch the
    evidence is anchored to. Because the credit is corroborated server-side from
    these streams (recompute_batch_credit), any enrolled device could otherwise
    inject telemetry/yield/application/moisture/composite rows into a victim's
    batch and move its credit. This mirrors the media handler's `not_your_batch`
    rule (upload_media).

    Policy:
      * batch exists AND is owned by another device  -> 403 not_your_batch
      * batch exists AND owned by this device         -> OK
      * batch owned by nobody yet (device_id NULL)    -> OK (legacy/unowned)
      * batch does NOT exist yet                      -> OK (evidence-first is a
        legitimate flow; create_batch establishes ownership from its own signed
        payload when it arrives, and drives the authoritative recompute then)

    A malformed batch_uuid is left for the endpoint's own persistence/validation
    to handle; it cannot match an existing owned batch, so it is not a bypass.
    """
    try:
        buid = uuid.UUID(batch_uuid_str)
    except (ValueError, AttributeError, TypeError):
        return
    batch = (
        await session.execute(select(Batch).where(Batch.batch_uuid == buid))
    ).scalar_one_or_none()
    if (
        batch is not None
        and batch.device_id is not None
        and batch.device_id != device_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="not_your_batch"
        )

async def _upsert_one_to_one_evidence(
    session: AsyncSession,
    model,
    *,
    uuid_attr: str,
    uuid_value: str,
    batch_uuid: str,
    payload_json: str,
) -> dict:
    """Recover from an IntegrityError on a one-to-one evidence table
    (telemetry / yield / application: both `<x>_uuid` AND `batch_uuid` are UNIQUE).

    The commit can collide on either unique key, and the two cases mean different
    things:
      * same `<x>_uuid` again  -> a genuine idempotent retry of the SAME record.
        No-op; report duplicate. (Overwriting would be pointless and would reset
        received_at semantics.)
      * different `<x>_uuid`, same `batch_uuid` -> a CORRECTION / resubmission for
        the batch. Pre-fix this was silently dropped as `duplicate` — the batch
        kept the first (possibly attacker- or stale-) value and the real one was
        lost. Now we UPDATE the existing row in place so the corrected evidence
        wins and the credit re-derives from it.
      * `<x>_uuid` collides against a row on a DIFFERENT batch (pathological UUID
        reuse) -> there is no batch row to upsert; report duplicate rather than
        clobber another batch's record.

    The caller must have already rolled back the failed insert. Returns the JSON
    response body; caller commits + recomputes on the `updated` path.
    """
    await session.rollback()
    existing = (
        await session.execute(select(model).where(model.batch_uuid == batch_uuid))
    ).scalar_one_or_none()
    if existing is None or getattr(existing, uuid_attr) == uuid_value:
        # Same-record retry, or a cross-batch <x>_uuid clash we must not clobber.
        return {"status": "success", "duplicate": True}
    # Correction for this batch: overwrite the natural key + payload in place.
    setattr(existing, uuid_attr, uuid_value)
    existing.payload_json = payload_json
    await session.commit()
    await _recompute_if_batch_exists(session, batch_uuid)
    return {"status": "success", "updated": True}

async def _recompute_if_batch_exists(
    session: AsyncSession, batch_uuid_str: str
) -> None:
    """Recompute a batch's corroborated credit if the batch already exists.

    Called by the evidence endpoints so a batch's credit converges the moment its
    telemetry/yield/application lands. No-op if the batch hasn't arrived yet
    (create_batch will recompute when it does)."""
    try:
        buid = uuid.UUID(batch_uuid_str)
    except (ValueError, AttributeError, TypeError):
        return
    batch = (
        await session.execute(select(Batch).where(Batch.batch_uuid == buid))
    ).scalar_one_or_none()
    if batch is not None:
        # Evidence is already committed here (caller commits before this), so a
        # coalesced recompute is safe: a concurrent run observes our committed
        # rows. This collapses redundant recomputes under a burst of posts.
        await recompute_batch_credit(session, batch, coalesce=True)
        await session.commit()

def _assert_same_uuid(*, expected: str, **kwargs: str) -> None:
    """Raise 422 if any value in kwargs differs from expected."""
    for name, value in kwargs.items():
        if value != expected:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"batch_uuid mismatch: {name}={value} expected={expected}",
            )

