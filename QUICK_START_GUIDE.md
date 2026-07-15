# Quick Start Guide for Production Readiness Execution
**For:** Junior coding agents  
**Time:** 6-8 weeks  
**Goal:** Take dMRV from 80% complete to 100% production-ready

---

## TL;DR: What You're Building

You have a working dMRV (digital MRV — carbon credit tracking) system that's **80% done**. Your job: **finish the missing 20%** and **make it production-ready**.

### What's Done ✅
- Backend API (21 endpoints, fully tested)
- Mobile app (4 screens complete)
- Web portal (batch management UI)
- Database & compliance engine
- Security (device signatures, HMAC auth)

### What's Missing ❌
- CSI export endpoint (block credits)
- Rainbow export endpoint (block credits)
- Portal export buttons (block UI)
- Device attestation verifier (security gap)
- 4 mobile screens (Drift migration needed)
- Observability/monitoring
- Production deployment verification

### Timeline
```
Week 1: Export endpoints + security
Week 2: Drift migration + mobile screens
Week 3: Observability + monitoring setup
Week 4: Integration testing + production hardening
Weeks 5+: Deploy to production
```

---

## Getting Started (Day 1)

### 1. Read These Docs (1 hour)

Read in this order:
1. This file (QUICK_START_GUIDE.md) ← you are here
2. EXECUTION_MASTER_PLAN.md (the step-by-step instructions)
3. COMPREHENSIVE_TEST_STRATEGY.md (all test cases)

### 2. Create a Work Branch (5 minutes)

```bash
git checkout -b production-readiness-sprint
git branch -u origin/main
```

### 3. Set Up Your Environment (30 minutes)

```bash
# Backend
cd backend
pip install -r requirements.txt
python -m pytest tests/ -q  # Should pass

# Mobile
cd ../flutter_dmrv
flutter pub get
flutter test -q  # Should pass

# Portal
cd ../portal
npm install
npm test  # Should pass

# Docker (for local testing)
cd ..
docker compose up -d
# Should have db + api running at http://localhost:8001/api/health
```

### 4. Understand the Current State (1 hour)

Run this command to see the codebase structure:

```bash
# Backend endpoints
grep -r "@router\|@app" backend/routers/ | grep -v ".pyc" | head -30

# Mobile screens
ls -1 lib/ui/screens/

# Portal pages
ls -1 portal/src/pages/

# Tests
ls -1 backend/tests/ | wc -l  # Should be 30+ test files
```

---

## Phase 1: Export Endpoints (Days 1–7)

**Goal:** Users can export batches to CSI and Rainbow registries

**Owner:** Agent A

### Step 1: CSI Export Endpoint

**Read:** EXECUTION_MASTER_PLAN.md, STEP 1.1

**Do:**
1. Create `backend/services/export.py` (copy from plan)
2. Create `backend/routers/exports.py` (copy from plan)
3. Register router in `backend/app_factory.py`
4. Update `backend/server.py` facade

**Test:**
```bash
cd backend
pytest tests/test_export_endpoints.py::TestCSIExport -v
# Should pass: test_csi_export_success_issuable_batch, etc.
```

### Step 2: Rainbow Export Endpoint

**Read:** EXECUTION_MASTER_PLAN.md, STEP 1.1 (same file, different class)

**Do:**
1. Same file `backend/services/export.py` — just add `RainbowExportService` class
2. Same file `backend/routers/exports.py` — add rainbow endpoint

**Test:**
```bash
pytest tests/test_export_endpoints.py::TestRainbowExport -v
# Should pass: test_rainbow_export_success_issuable_batch, etc.
```

### Step 3: Portal Export Buttons

**Read:** EXECUTION_MASTER_PLAN.md, STEP 1.4

**Do:**
1. Edit `portal/src/pages/BatchDetail.tsx`
2. Add two buttons: "Download CSI" and "Download Rainbow"
3. Edit `portal/src/api.ts` to add fetch wrapper functions

**Test:**
```bash
cd portal
npm test  # Should not break existing tests

# Manual test:
# 1. npm run dev
# 2. Login to portal
# 3. View a batch (status = ISSUED)
# 4. Click "Download CSI" button
# 5. JSON file downloads
```

### Step 4: Verify Everything Works

**Test all three together:**
```bash
cd backend
python -m pytest tests/test_export_endpoints.py -v

# Manual test:
curl -H "X-Admin-Secret: your-secret" \
  http://localhost:8001/api/v1/batches/{BATCH_UUID}/export/csi | jq .

curl -H "X-Admin-Secret: your-secret" \
  http://localhost:8001/api/v1/batches/{BATCH_UUID}/export/rainbow | jq .
```

**Commit when done:**
```bash
git add backend/services/export.py backend/routers/exports.py backend/app_factory.py
git add backend/server.py portal/src/pages/BatchDetail.tsx portal/src/api.ts
git commit -m "feat: add CSI and Rainbow export endpoints

- Implement GlobalCSinkVerificationReport (CSI format)
- Implement Rainbow Biochar Standard export
- Add portal UI buttons to download exports
- All endpoints admin-only (X-Admin-Secret required)
- Validation: batch must be issuable (not provisional)
- Tests: 20+ test cases, all pass"

git push origin production-readiness-sprint
```

---

## Phase 2: Security Hardening (Days 8–14)

**Goal:** Real device attestation, secrets management, TLS pinning plan

**Owner:** Agent C

### Step 1: Real Device Attestation

**Read:** EXECUTION_MASTER_PLAN.md, STEP 2.1

**Do:**
1. Create `backend/services/attestation.py` (copy from plan)
2. Update `backend/settings.py` to call real verifier instead of stub
3. Update `backend/routers/batches.py` to enforce attestation

**Test:**
```bash
pytest backend/tests/test_security_hardening.py -v
# Tests will stub/mock Google API since we don't have real credentials yet
```

### Step 2: Secrets Management

**Read:** EXECUTION_MASTER_PLAN.md, STEP 2.2

**Do:**
1. Create `backend/services/secrets.py` (copy from plan)
2. Update `docker-compose.yml` with secrets backend options
3. Create `DEPLOYMENT_CHECKLIST.md` to track secrets (copy from plan)

**No code test needed here** — this is infrastructure setup you'll verify during deployment.

### Step 3: TLS Certificate Rotation

**Read:** EXECUTION_MASTER_PLAN.md, STEP 2.3

**Do:**
1. Create `deploy/cert-rotation-ceremony.md` (copy from plan)
2. Add cert expiry check to `backend/observability.py` (copy from plan)

**No code test needed** — documentation + monitoring setup.

---

## Phase 3: Mobile Completion (Days 15–18)

**Goal:** Complete all 8 mobile screens (currently 4 done)

**Owner:** Agent B

### Step 1: Drift ORM Migration

**Read:** EXECUTION_MASTER_PLAN.md, STEP 3.1 & 3.2

**Do:**
```bash
cd flutter_dmrv

# 1. Update pubspec.yaml
# Change: drift: ^2.15.x  →  drift: ^2.16.0
# (full diff in plan)

# 2. Get deps
flutter pub get

# 3. Generate code
flutter pub run build_runner build --delete-conflicting-outputs

# 4. Test
flutter test

# 5. Build
flutter build apk --debug
```

### Step 2: Implement 4 Missing Screens

**Read:** EXECUTION_MASTER_PLAN.md, STEP 3.3

**Screens to complete:**
1. **S3: Kiln Selection** — radio list of kilns from DB
2. **S6: Pyrolysis** — camera + flame height slider (open) or ignition type (closed)
3. **S7: Sync Health** — pending batches count, BLE status, retry button
4. **S8: End-Use Application** — dropdown to select how biochar is used

**For each screen:**
1. Copy code from plan
2. Integrate into navigation flow
3. Test: `flutter test`
4. Build: `flutter build apk --debug`

### Step 3: Integration Test Full Workflow

**Read:** COMPREHENSIVE_TEST_STRATEGY.md, Section 2.2

**Do:**
```bash
flutter test test/integration_test_batch_workflow.dart -v
# Should pass: enrollment → sourcing → moisture → biomass → sync
```

**Commit when done:**
```bash
git add lib/ui/screens/kiln_select_screen.dart lib/ui/screens/pyrolysis_screen.dart
git add lib/ui/screens/sync_health_screen.dart lib/ui/screens/end_use_application_screen.dart
git commit -m "feat: complete all 8 mobile screens

- Migrate Drift ORM from v25 → v26
- Implement kiln selection screen (S3)
- Implement pyrolysis profile capture (S6)
- Implement sync health dashboard (S7)
- Implement end-use application form (S8)
- All screens tested and integrated
- Full workflow: enrollment → ... → sync passes"

git push origin production-readiness-sprint
```

---

## Phase 4: Observability (Days 19–25)

**Goal:** Metrics, error tracking, structured logging

**Owner:** Agent C

### Step 1: Prometheus Metrics

**Read:** EXECUTION_MASTER_PLAN.md, STEP 4.1a

**Do:**
1. Create or update `backend/observability.py` (copy from plan)
2. Wire into `backend/app_factory.py` via `install_middleware(app)`
3. Update `docker-compose.yml` to expose metrics port

**Test:**
```bash
curl http://localhost:8001/api/metrics
# Should return Prometheus-format metrics (text)
```

### Step 2: Sentry Error Tracking

**Read:** EXECUTION_MASTER_PLAN.md, STEP 4.1b

**Do:**
1. Update `backend/app_factory.py` to initialize Sentry SDK
2. Set `DMRV_SENTRY_DSN` environment variable (empty if no account yet)

**No code test** — requires Sentry account. You'll configure during production setup.

### Step 3: Structured Logging

**Read:** EXECUTION_MASTER_PLAN.md, STEP 4.1c

**Do:**
1. Update `backend/settings.py` to use `StructuredFormatter`
2. All logs will now output as JSON (one JSON object per line)

**Test:**
```bash
# Start backend
docker compose up -d api

# Trigger a batch creation
curl -X POST http://localhost:8001/api/v1/batches ...

# Check logs (should be JSON)
docker logs <api_container_id> | tail -10
# Each line should be valid JSON with timestamp, level, message, etc.
```

---

## Phase 5: Final Integration & Deployment (Days 26–32)

**Goal:** Everything works together, ready for production

**Owner:** All agents

### Step 1: Run ALL Tests

```bash
# Backend
cd backend
python -m pytest tests/ -v --tb=short
# MUST PASS: 500+ tests

# Mobile
cd ../flutter_dmrv
flutter test -v
# MUST PASS: 50+ tests

# Portal
cd ../portal
npm test
# MUST PASS: 30+ tests

# E2E (requires running backend)
cd ../backend
docker compose up -d
sleep 10
python -m pytest tests/test_e2e_complete_system.py -v -s
# MUST PASS: complete system workflow
```

### Step 2: Security Audit

```bash
# Read: EXECUTION_MASTER_PLAN.md, STEP 5.3

# Verify:
# ✓ All device endpoints check signatures
# ✓ All admin endpoints check X-Admin-Secret
# ✓ Portal endpoints require JWT
# ✓ No hardcoded secrets in code
# ✓ Database connections use TLS
# ✓ No sensitive data in logs
```

### Step 3: Deployment Verification

```bash
# Read: EXECUTION_MASTER_PLAN.md, STEP 5.4

# Create checklist file:
touch PRODUCTION_DEPLOYMENT_CHECKLIST.md
# (copy from plan)

# Go through each item and verify
```

---

## Testing Your Work

### Test Each Phase as You Complete It

**Phase 1 (Export endpoints):**
```bash
cd backend
pytest tests/test_export_endpoints.py -v
pytest tests/test_e2e_production_flow.py::test_full_batch_to_csi_submission_flow -v
```

**Phase 2 (Security):**
```bash
pytest tests/test_security_hardening.py -v
```

**Phase 3 (Mobile):**
```bash
cd ../flutter_dmrv
flutter test
```

**Phase 4 (Observability):**
```bash
cd ../backend
curl http://localhost:8001/api/metrics
# Should return metrics
```

**Phase 5 (Integration):**
```bash
pytest tests/test_e2e_complete_system.py -v -s
```

### Test Before Committing

```bash
# NEVER commit with failing tests
# If any test fails:
# 1. Read the error
# 2. Fix the bug
# 3. Re-run the test
# 4. Only then commit
```

---

## Commit Messages (Do This Right)

**Good commits:**
```bash
git commit -m "feat: add CSI export endpoint

- Endpoint: GET /api/v1/batches/{uuid}/export/csi
- Requires: X-Admin-Secret auth header
- Validates: batch must be issuable (not provisional)
- Format: GlobalCSinkVerificationReport JSON
- Tests: 10 test cases, all pass"

git commit -m "fix: handle missing h_corg in CSI export

- Rainbow export defaults h_corg to 0.5 if lab measurement missing
- Test: test_csi_export_handles_missing_h_corg passes"

git commit -m "test: add E2E test for complete batch workflow

- Tests: device enrollment → batch creation → compliance → issue → export
- Covers: all 8 API calls, all validation gates
- Result: test_e2e_complete_system_flow passes"
```

**Bad commits:**
```bash
git commit -m "stuff"
git commit -m "fix export"
git commit -m "updates"
```

---

## When You Get Stuck

### Problem: Test fails with "batch not found"
**Solution:** Check test fixtures. Make sure batch is created before test runs.

### Problem: API returns 403 instead of 401
**Solution:** Read the error message. 403 = forbidden (auth failed). 401 = unauthenticated. Check X-Admin-Secret or X-Signature headers.

### Problem: Flutter build fails with "Drift error"
**Solution:** Run `flutter pub run build_runner clean` then `build_runner build --delete-conflicting-outputs`

### Problem: Portal tests fail with "Component not found"
**Solution:** Check if component is rendered conditionally (e.g., only if `batch.status === "ISSUED"`). Add mock data that satisfies condition.

### Problem: Docker container won't start
**Solution:** Check logs: `docker logs <container_id>`. Most common: environment variables missing. Check `.env` file and `docker-compose.yml`.

**If still stuck:** Re-read the relevant step in EXECUTION_MASTER_PLAN.md. Almost all answers are there.

---

## Success Checkpoints

| Week | Checkpoint | Pass = |
|------|-----------|--------|
| **Week 1** | CSI + Rainbow export endpoints | 20+ backend tests pass + curl works |
| **Week 2** | Attestation verifier + secrets mgmt | Security tests pass + no secrets in logs |
| **Week 2** | Drift migration + 4 mobile screens | `flutter test` passes, 50+ tests |
| **Week 3** | Observability setup | `/api/metrics` returns data + logs are JSON |
| **Week 4** | E2E integration | `test_e2e_complete_system.py` passes |
| **Week 4** | Security audit | All checklist items ✓ |
| **Week 5+** | Production deployment | System running on Render/Cloud Run, no errors |

---

## Final Checklist Before Pushing to main

```bash
# 1. All tests pass
python -m pytest backend/tests/ -q
flutter test
cd portal && npm test

# 2. No uncommitted changes (except maybe .env)
git status
# Should show: "nothing to commit" or just ".env"

# 3. Code is pushed to your branch
git log --oneline | head -5  # Should show your commits
git push origin production-readiness-sprint

# 4. Create PR on GitHub
# (link to EXECUTION_MASTER_PLAN.md + test results)

# 5. Get approval
# (product lead, engineering lead, security lead)

# 6. Merge to main
git checkout main
git pull origin main
git merge production-readiness-sprint
git push origin main

# 7. Deploy to production
# (follow PRODUCTION_DEPLOYMENT_FINAL_CHECKLIST.md)
```

---

## Key Files Reference

| File | Purpose | Read When |
|------|---------|-----------|
| **EXECUTION_MASTER_PLAN.md** | Step-by-step instructions | Starting each phase |
| **COMPREHENSIVE_TEST_STRATEGY.md** | All test cases + examples | Writing tests |
| **PRODUCTION_DEPLOYMENT_FINAL_CHECKLIST.md** | Deployment verification | Week 4+ |
| **DEPLOYMENT_VERIFICATION.md** | Post-deploy smoke tests | After deploying |
| **SECURITY_AUDIT_CHECKLIST.md** | Security verification | Week 3–4 |

---

## Questions?

- **"How do I fix a failing test?"** → Read the error message. Decode it. Fix the bug. Re-run.
- **"What if I break something?"** → `git reset --hard origin/main` rolls back. You have a time machine.
- **"How do I know if I'm on track?"** → Check success checkpoints above. If you pass, you're on track.
- **"Can I skip a step?"** → No. The steps build on each other. Do them in order.

---

**You've got this. Follow the plan. Commit frequently. Test everything. Ask for help if stuck.**

**Target: Production-ready dMRV system in 6-8 weeks.**

**GO!** 🚀
