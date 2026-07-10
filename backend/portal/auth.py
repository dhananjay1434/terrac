"""Portal authentication: users, sessions, and the `require_role` dependency.

Populated in P2.1 (argon2 password hashing, opaque hashed session tokens,
role-based `require_role(*roles)`). Isolated here so the auth surface is small
and testable, and never leaks into the device-facing `server.py`.
"""
