# 07 — Prioritized Remediation Plan

Based on the executive summary and detailed findings, here is the ordered fix plan to stabilize the Kon-Tiki / TerraCipher Biochar dMRV foundation before building new features.

## Phase 1: Stop the Bleeding (P0 Blocker Fixes)
1. **Fix Payload Rejection (BUG-1):** Update FastAPI schemas (`BatchPayload`) to match Flutter client payload, or define separate endpoints for different tables. Prevent all measurements from being rejected with HTTP 422.
2. **Implement Stub Endpoints (BUG-2 & BUG-3):** Implement actual persistence for `/telemetry`, `/yield`, `/metadata`, and `/application` endpoints so client data is not discarded permanently.
3. **Fix Device Registration Endpoint (BUG-4 & SEC-10):** Update `registerDevice()` in Flutter to use the correct `env`-driven base URL instead of the hardcoded `10.0.2.2:8000` emulator loopback.

## Phase 2: Secure the Perimeter (P0 Security Fixes)
1. **Require Real Authentication (SEC-1 & SEC-2):** Replace the self-generated, unauthenticated device key registration with an enrollment token or hardware attestation. Remove the global `DMRV_HMAC_SECRET` fallback for unknown devices.
2. **Gate Credit Issuance (SEC-3 & LCA-1):** Ensure that unverified/unsigned batches are rejected or quarantined without any carbon credit values computed or stored.
3. **Fix Fraud Detection (SEC-4):** Move mock-GPS and location spoofing detection logic to the server side (e.g., using hardware attestation, speed checks, EXIF vs server timestamp), rather than relying on a client-provided boolean header.

## Phase 3: Repo Hygiene and Configuration (SEC-5)
1. **Clean up `.gitignore`:** Rewrite `.gitignore` to be valid UTF-8 and correctly ignore environments, builds, DBs, and uploads.
2. **Remove Secrets & Bloat:** Delete `.env`, `all_user_inputs.txt`, SQLite databases, `build/` folder, JPEGs, and throwaway scripts from the repository. Rotate exposed credentials.
3. **Fix Server Boot & Keys (SEC-6):** Ensure `DMRV_HMAC_SECRET` is properly documented and configured in `.env.example`, and unify key encoding between the Dart client and FastAPI server.

## Phase 4: Backend & Client Stabilization (P1 Fixes)
1. **Fix Sync Engine (BUG-5, BUG-6, BUG-10):** Resolve Riverpod `FutureProvider` misuses in `SyncQueueManager`, fix the `autoDispose`/`keepAlive` contradiction, and add recovery mechanisms for `FAILED_PERMANENTLY` sync tasks.
2. **Fix Anchoring & Unique Constraints (BUG-7, BUG-8):** Anchor media files explicitly by `batch_uuid` rather than a non-unique `sha256_hash`. Handle specific Postgres `IntegrityError` constraints gracefully to avoid HTTP 500s.
3. **LCA Soundness (LCA-2, LCA-3):** Add proper endpoints for lab-measured `H:Corg` and full temperature logs, removing hardcoded defaults and easily-spoofed single-value temperature checks.
