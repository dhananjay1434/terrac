"""PR-2.1 — pure independent (4-eyes) verification gate.

MVP scope (see docs/PRODUCTION_READINESS_EXECUTION_PROMPT.md PART PR-2): a
portal user holding 'verifier' or 'admin' role is a human channel distinct
from the producing device (devices sign with Ed25519 and have no portal
login) — that is the only thing checkable today. There is NO device<->
operator-user identity map, so a producer-equality check is NOT possible
and must not be faked here.
"""

from corroboration import derive_independent_verification


def test_verifier_role_with_user_id_is_ok():
    assert derive_independent_verification("verifier", 7) == (True, None)


def test_admin_role_with_user_id_is_ok():
    assert derive_independent_verification("admin", 3) == (True, None)


def test_lab_role_is_not_authorized():
    assert derive_independent_verification("lab", 5) == (
        False,
        "not_an_authorized_verifier",
    )


def test_org_admin_role_is_not_authorized():
    assert derive_independent_verification("org_admin", 5) == (
        False,
        "not_an_authorized_verifier",
    )


def test_missing_user_id_is_not_authorized_even_for_verifier_role():
    assert derive_independent_verification("verifier", None) == (
        False,
        "not_an_authorized_verifier",
    )


def test_unknown_role_is_not_authorized():
    assert derive_independent_verification("bogus", 1) == (
        False,
        "not_an_authorized_verifier",
    )
