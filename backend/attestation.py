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

from dataclasses import dataclass
from typing import Optional


@dataclass
class AttestationVerdict:
    verified: bool
    reason: Optional[str] = None  # why not verified — recorded in the audit trail


def verify_play_integrity(token: str, *, expected_nonce: str = "") -> AttestationVerdict:
    """Verify a Google Play Integrity verdict token.

    TODO(creds): call playintegrity.googleapis.com decodeIntegrityToken (or local
    JWE decrypt), then assert appIntegrity.appRecognitionVerdict == PLAY_RECOGNIZED,
    deviceIntegrity contains MEETS_DEVICE_INTEGRITY, the package name matches, and
    requestDetails.nonce == expected_nonce. Requires Play Console credentials.
    """
    return AttestationVerdict(verified=False, reason="verifier_not_configured")


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
