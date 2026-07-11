"""Platform attestation verification (Play Integrity / DeviceCheck).

T2.1. Verdict verification lives behind an interface so the enforcement wiring in
`server.recompute_batch_credit` is testable with fixtures BEFORE real Google /
Apple credentials exist. `verify_attestation` returns a structured verdict; the
caller decides policy (provisional vs issuable) — it never raises to reject an
upload.

Until credentials + the provider integration land, every real token is treated
as UNVERIFIED (`verifier_not_configured`), so behaviour is unchanged while
enforcement is off. Tests inject a double via monkeypatch on this module.

Nonce/anti-replay note: a genuine Play Integrity nonce must be FRESH PER
ATTESTATION (not a single enrollment-time value reused forever, which would be
replayable). When the provider integration is built, bind the nonce to the
per-request T2.3 `signed_at` (already signed by the device) rather than a stored
enrollment nonce — hence no enrollment-nonce column is added here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional


@dataclass
class AttestationVerdict:
    verified: bool
    reason: Optional[str] = None  # why not verified — recorded in the audit trail


# P4.1: the token -> claims decode is the only step that needs Google credentials
# (playintegrity.googleapis.com decodeIntegrityToken, or a local JWE decrypt with
# the app's decryption/verification keys). It is a seam so the POLICY evaluation
# below is fully implemented + tested now, and only the decode is injected once a
# human provides credentials. A configured decoder returns the decoded verdict
# claims dict (or raises); None means "no verifier configured".
IntegrityDecoder = Callable[[str], dict]
_play_integrity_decoder: Optional[IntegrityDecoder] = None


def configure_play_integrity_decoder(decoder: Optional[IntegrityDecoder]) -> None:
    """Install (or clear) the token->claims decoder. Called from deploy wiring
    once Play Console credentials exist; tests inject a fake decoder."""
    global _play_integrity_decoder
    _play_integrity_decoder = decoder


def _expected_package() -> str:
    return os.environ.get("DMRV_PLAY_INTEGRITY_PACKAGE", "").strip()


def evaluate_play_integrity_verdict(
    claims: dict, *, expected_package: str, expected_nonce: str = ""
) -> AttestationVerdict:
    """Pure policy over decoded Play Integrity claims (no network).

    Requires: appIntegrity.appRecognitionVerdict == PLAY_RECOGNIZED,
    deviceIntegrity.deviceRecognitionVerdict contains MEETS_DEVICE_INTEGRITY,
    requestDetails.requestPackageName == expected_package, and (when an
    expected_nonce is supplied) requestDetails.nonce == expected_nonce.
    Returns a verdict with a specific reason on the first failing check.
    """
    if not isinstance(claims, dict):
        return AttestationVerdict(verified=False, reason="malformed_verdict")

    app = (claims.get("appIntegrity") or {}).get("appRecognitionVerdict")
    if app != "PLAY_RECOGNIZED":
        return AttestationVerdict(verified=False, reason="app_not_recognized")

    device = (claims.get("deviceIntegrity") or {}).get("deviceRecognitionVerdict") or []
    if "MEETS_DEVICE_INTEGRITY" not in device:
        return AttestationVerdict(verified=False, reason="device_integrity_failed")

    req = claims.get("requestDetails") or {}
    if expected_package and req.get("requestPackageName") != expected_package:
        return AttestationVerdict(verified=False, reason="package_mismatch")

    # Nonce anti-replay: bind to the per-request signed_at (T2.3) at call time.
    if expected_nonce and req.get("nonce") != expected_nonce:
        return AttestationVerdict(verified=False, reason="nonce_mismatch")

    return AttestationVerdict(verified=True)


def verify_play_integrity(token: str, *, expected_nonce: str = "") -> AttestationVerdict:
    """Verify a Google Play Integrity verdict token.

    Decodes via the configured decoder (a human wires real Play Console
    credentials through configure_play_integrity_decoder), then applies
    evaluate_play_integrity_verdict. Without a configured decoder the result is
    'verifier_not_configured' — behaviour is unchanged until credentials land.
    """
    if _play_integrity_decoder is None:
        return AttestationVerdict(verified=False, reason="verifier_not_configured")
    try:
        claims = _play_integrity_decoder(token)
    except Exception:  # noqa: BLE001 — a decode failure is an unverified verdict
        return AttestationVerdict(verified=False, reason="decode_failed")
    return evaluate_play_integrity_verdict(
        claims, expected_package=_expected_package(), expected_nonce=expected_nonce
    )


# ---------------------------------------------------------------------------
# P4.1 — grace period so flipping DMRV_ATTESTATION_ENFORCED on doesn't instantly
# brick the already-enrolled fleet. A device registered BEFORE enforcement began
# gets a grace window; a device that enrolled after enforcement gets none.
# ---------------------------------------------------------------------------
def _enforced_since() -> Optional[datetime]:
    raw = os.environ.get("DMRV_ATTESTATION_ENFORCED_SINCE", "").strip()
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _grace_days() -> int:
    try:
        return max(0, int(os.environ.get("DMRV_ATTESTATION_GRACE_DAYS", "0")))
    except ValueError:
        return 0


def device_in_grace(
    registered_at: Optional[datetime],
    now: datetime,
    *,
    enforced_since: Optional[datetime],
    grace_days: int,
) -> bool:
    """Pure predicate: is a device still inside the enforcement grace window?

    True only when a grace window is configured, the device registered before
    enforcement began, and we are still within grace_days of that start.
    """
    if grace_days <= 0 or enforced_since is None or registered_at is None:
        return False
    reg = registered_at if registered_at.tzinfo else registered_at.replace(tzinfo=timezone.utc)
    if reg >= enforced_since:
        return False  # enrolled after enforcement — no grace
    return now < enforced_since + timedelta(days=grace_days)


def attestation_in_grace(registered_at: Optional[datetime], now: datetime) -> bool:
    """Env-driven wrapper over device_in_grace."""
    return device_in_grace(
        registered_at, now, enforced_since=_enforced_since(), grace_days=_grace_days()
    )


def verify_device_check(token: str, *, expected_nonce: str = "") -> AttestationVerdict:
    """Verify an Apple App Attest / DeviceCheck assertion.

    TODO(creds): verify Apple's cert chain + the key assertion; requires an Apple
    Developer account and the app's attestation public key.
    """
    return AttestationVerdict(verified=False, reason="verifier_not_configured")


def verify_attestation(blob, *, expected_nonce: str = "") -> AttestationVerdict:
    """Dispatch by platform. `blob` is the client's hw_attestation payload (a list
    the device ships on telemetry). Returns a verdict; never raises.
    """
    if not blob:
        return AttestationVerdict(verified=False, reason="no_attestation")
    # Real android-vs-ios dispatch goes here once the payload shape is fixed and
    # provider credentials exist. Until then, unverified (fail-closed policy is
    # applied by the caller when enforcement is on).
    return AttestationVerdict(verified=False, reason="verifier_not_configured")
