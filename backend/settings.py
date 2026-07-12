"""Configuration & secrets layer (extracted from server.py, R2).

Env loading, mandatory-secret resolution with an entropy floor (T2.6), versioned
HMAC startup validation (P3.6), and the env-LIVE feature-flag readers (attestation
enforcement T2.1, canonical-v2 requirement T2.3).

IMPORTANT: the flag readers below (`_attestation_enforced`, `_require_canonical_v2`,
`_canonical_skew_seconds`) and `env_int`/`_rl_int` read os.environ on EVERY call, on
purpose — a test elsewhere does importlib.reload(server) and monkeypatches env, and
freezing these into import-time constants would desync the running app from the test's
env (SOP §6.5). Do not "optimize" them into module constants.
"""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv

import hmac_keys
import observability


def _load_env() -> None:
    """Populate os.environ from a local .env for developer convenience.

    Skipped when DMRV_DISABLE_DOTENV=1. CI and production supply configuration
    through the environment (not a checked-out .env), and the P0-21 regression
    test relies on this flag to assert the "refuse to start without a secret"
    guard against a genuinely clean environment — otherwise a developer .env on
    disk silently repopulates a deliberately-removed variable. load_dotenv never
    overrides a value already present in the environment.
    """
    if os.environ.get("DMRV_DISABLE_DOTENV") == "1":
        return
    load_dotenv()


_load_env()


_MIN_SECRET_LEN = 32
_MIN_SECRET_UNIQUE = 10


def _require_secret(name: str) -> str:
    """Resolve a mandatory secret from the environment or refuse to start.

    Single choke point for required-secret resolution so the fail-loud guarantee
    lives in exactly one place. T2.6 adds an entropy/length floor so a weak
    placeholder can never reach production. The floor is bypassed only when
    DMRV_ALLOW_WEAK_SECRETS=1 (the test suite sets this so its short fixed
    literals stay valid; never set it in production). Raises RuntimeError naming
    the offending variable.
    """
    # TODO(deploy, T2.8): at first real deployment generate FRESH 32-byte
    # DMRV_HMAC_SECRET / DMRV_ADMIN_SECRET (base64url) in the platform secret
    # manager — never a file. Rotating DMRV_HMAC_SECRET invalidates verification
    # of already-issued lca_signature values, so archive the old key for
    # historical verification or re-sign historical audits in a migration.
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} env var is required.")
    if os.environ.get("DMRV_ALLOW_WEAK_SECRETS") != "1":
        if len(value) < _MIN_SECRET_LEN or len(set(value)) < _MIN_SECRET_UNIQUE:
            raise RuntimeError(
                f"{name} is too weak: require >= {_MIN_SECRET_LEN} chars and "
                f">= {_MIN_SECRET_UNIQUE} distinct characters."
            )
    return value


# P3.6: the lca_signature HMAC key is now versioned (DMRV_HMAC_KEYS +
# DMRV_HMAC_ACTIVE_KEY, or the legacy DMRV_HMAC_SECRET as key id k0). Fail loud
# at import if no valid key is configured — same guarantee _require_secret gave.
hmac_keys.validate_startup()
# Back-compat shim: the active key's secret under its historical name. Live
# signing goes through hmac_keys.active_key() (versioned); this stays so existing
# guards/tests that read the resolved secret keep working.
_HMAC_SECRET = hmac_keys.active_key()[1]
_ADMIN_SECRET = _require_secret("DMRV_ADMIN_SECRET")


def env_int(name: str, default: int) -> int:
    """Read an integer env var, falling back to `default` on absent/invalid.

    Live-read (no import-time capture). Shared by the flag readers here and the
    rate-limit middleware (R8), which imports it as `_rl_int`.
    """
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


# Alias kept so `from settings import _rl_int` (used by middleware.py, R8) and any
# existing `server._rl_int` reference resolve to the same function.
_rl_int = env_int


# Platform attestation (Play Integrity / DeviceCheck). T2.1 added a verifier
# interface (attestation.py); real provider verification still awaits Google /
# Apple credentials, so verify_attestation returns UNVERIFIED for genuine tokens.
# Policy switch (env-live so it survives importlib.reload + is runtime-tunable):
#   0 (default, "Option B") — non-blocking: log a loud warning, do not gate.
#   1 ("Option A")          — fail closed: an unverified attestation keeps the
#                             batch PROVISIONAL (attestation_unverified). Flip via
#                             DMRV_ATTESTATION_ENFORCED=1 once the verifier is real
#                             and the fleet is verified-capable. See FINDINGS_BACKLOG.
def _attestation_enforced() -> bool:
    return os.environ.get("DMRV_ATTESTATION_ENFORCED", "0") == "1"


# T2.3 replay protection. The v1 request canonical carries no timestamp, so a
# captured request replays forever. v2 appends a client-signed unix timestamp and
# the server rejects requests outside a skew window. Rollout is backward
# compatible: v1 (no X-Canonical-Version header) is still accepted until the
# fleet ships v2 signing, then DMRV_REQUIRE_CANONICAL_V2=1 refuses v1. The skew
# window is generous (rural devices drift) and env-tunable. Read live from env so
# it survives importlib.reload(server) (see the rate-limit note).
def _canonical_skew_seconds() -> int:
    return max(1, env_int("DMRV_CANONICAL_SKEW_SECONDS", 300))


def _require_canonical_v2() -> bool:
    return os.environ.get("DMRV_REQUIRE_CANONICAL_V2", "0") == "1"


log = logging.getLogger("dmrv")
# P3.4: JSON structured logging (request_id bound per request) replaces
# basicConfig; Sentry initializes here if DMRV_SENTRY_DSN is set.
observability.configure_json_logging()
observability.init_sentry()
