# Comprehensive Test Strategy for Production Readiness
**Purpose:** Definitive guide to all tests required for production deployment  
**Audience:** Junior coding agents, QA engineers  
**Scope:** Backend, Mobile, Portal, Deployment, Security

---

# SECTION 1: BACKEND TEST STRATEGY

## 1.1 Unit Tests — Core Business Logic

### What to Test
- Credit calculation formula: `dry_yield_kg * h_corg * 3.67`
- Compliance rules: All C1–C10 gates
- Corroboration checks: moisture per 100 kg, photo evidence, GPS bounds
- Data validation: enum fields, numeric ranges, string lengths

### Where to Add Tests
**File:** `backend/tests/test_credit_calculation.py`

```python
def test_credit_calculation_full_issuable():
    """Credit = dry_yield * h_corg * 3.67 (constant)."""
    dry_yield = 100  # kg
    h_corg = 0.75
    expected = 100 * 0.75 * 3.67  # = 275.25
    
    result = calculate_net_credit_t_co2e(dry_yield, h_corg)
    assert result == pytest.approx(expected, rel=0.01)

def test_credit_calculation_with_assumed_h_corg():
    """Batch is provisional if h_corg is assumed (not lab-measured)."""
    batch = create_batch(lab_h_corg=None)  # Assumed default (0.5)
    
    assert batch.provisional == True
    assert "assumed_h_corg" in batch.provisional_reasons

def test_moisture_compliance_c2():
    """C2: at least 1 moisture reading per 100 kg, min 10 total."""
    batch_with_500kg = create_batch(biomass_input_kg=500)
    
    # 4 readings: need at least 5 (500/100)
    add_moisture_readings(batch_with_500kg, count=4)
    assert not is_c2_compliant(batch_with_500kg)
    
    # 5 readings: now compliant
    add_moisture_readings(batch_with_500kg, count=1)
    assert is_c2_compliant(batch_with_500kg)

def test_composite_sampling_c4():
    """C4: at least one composite pile sub-sample (photographed)."""
    batch = create_batch()
    
    # No samples: not compliant
    assert not is_c4_compliant(batch)
    
    # One sample with photo: compliant
    add_composite_sample(batch, has_photo=True)
    assert is_c4_compliant(batch)
    
    # One sample without photo: not compliant
    batch2 = create_batch()
    add_composite_sample(batch2, has_photo=False)
    assert not is_c4_compliant(batch2)

def test_gps_plausibility_no_teleport():
    """Batches must not teleport > 100 km between harvest locations."""
    device = create_device()
    
    # First batch at lat=10, lon=20
    batch1 = create_batch(device_id=device.id, latitude=10, longitude=20)
    
    # Second batch 500 km away (teleport): should fail plausibility check
    batch2_payload = BatchPayload(latitude=15, longitude=20, ...)
    
    with pytest.raises(HTTPException) as exc_info:
        create_batch(batch2_payload, device_id=device.id)
    
    assert "implausible_movement" in str(exc_info.value.detail)
```

**Run these tests:**
```bash
pytest backend/tests/test_credit_calculation.py -v
# Expected: all pass
```

---

### What Not to Test
- Database ORM behavior (SQLAlchemy handles this; trust it)
- Third-party library logic (trust proven libraries)
- Deployed infrastructure details (test in integration tests instead)

---

## 1.2 API Endpoint Tests — Request/Response Contracts

### What to Test
- HTTP status codes (201 for created, 400 for bad input, 403 for auth failure, 404 for not found)
- Request validation (missing headers, malformed JSON, wrong types)
- Response schema (all required fields present, correct types)
- Idempotency (duplicate requests return same result)

### Test Template

**File:** `backend/tests/test_api_contract_batch_creation.py`

```python
import pytest
from httpx import AsyncClient
from datetime import datetime, timezone
from uuid import uuid4

class TestBatchCreationAPI:
    """Contract tests for POST /api/v1/batches endpoint."""
    
    @pytest.mark.asyncio
    async def test_batch_creation_success_201(self, client: AsyncClient):
        """
        GIVEN: Valid batch payload with device signature
        WHEN: POST /api/v1/batches
        THEN: 201 Created with batch details in response
        """
        device_id = "test-device-001"
        batch_uuid = str(uuid4())
        
        payload = {
            "batch_uuid": batch_uuid,
            "device_id": device_id,
            "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
            "biomass_type": "Lantana",
            "species": "Lantana camara",
            "latitude": 10.5,
            "longitude": 20.5,
            "gps_accuracy_m": 5.0,
            "wet_yield_kg": 500,
            "dry_yield_kg": 120,
            "sha256_hash": "abc123def456",
        }
        
        # Sign payload
        signature = create_device_signature(device_id, payload)
        
        response = await client.post(
            "/api/v1/batches",
            json=payload,
            headers={
                "X-Device-Id": device_id,
                "X-Signature": signature,
                "X-Idempotency-Key": str(uuid4()),
            },
        )
        
        # Assertions
        assert response.status_code == 201
        
        data = response.json()
        assert data["batch_uuid"] == batch_uuid
        assert data["status"] == "ACCEPTED"
        assert data["net_credit_t_co2e"] > 0
        assert "received_at" in data

    @pytest.mark.asyncio
    async def test_batch_creation_idempotent_200(self, client: AsyncClient):
        """
        GIVEN: Batch already created with operation_id=X
        WHEN: POST same batch with operation_id=X again
        THEN: 200 OK (idempotent, not 201)
        """
        device_id = "test-device-001"
        batch_uuid = str(uuid4())
        idempotency_key = str(uuid4())
        
        payload = {...}
        signature = create_device_signature(device_id, payload)
        
        # First request → 201
        response1 = await client.post(
            "/api/v1/batches",
            json=payload,
            headers={
                "X-Device-Id": device_id,
                "X-Signature": signature,
                "X-Idempotency-Key": idempotency_key,
            },
        )
        assert response1.status_code == 201
        data1 = response1.json()
        
        # Second request (same idempotency key) → 200
        response2 = await client.post(
            "/api/v1/batches",
            json=payload,
            headers={
                "X-Device-Id": device_id,
                "X-Signature": signature,
                "X-Idempotency-Key": idempotency_key,
            },
        )
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Content should match
        assert data1["batch_uuid"] == data2["batch_uuid"]
        assert data1["net_credit_t_co2e"] == data2["net_credit_t_co2e"]

    @pytest.mark.asyncio
    async def test_batch_creation_missing_signature_403(self, client: AsyncClient):
        """
        GIVEN: Valid batch payload WITHOUT X-Signature header
        WHEN: POST /api/v1/batches
        THEN: 403 Forbidden
        """
        payload = {...}
        
        # Intentionally omit X-Signature
        response = await client.post(
            "/api/v1/batches",
            json=payload,
            headers={
                "X-Device-Id": "test-device-001",
                # No X-Signature
                "X-Idempotency-Key": str(uuid4()),
            },
        )
        
        assert response.status_code == 403
        assert "signature" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_batch_creation_invalid_uuid_format_400(self, client: AsyncClient):
        """
        GIVEN: Batch payload with malformed UUID
        WHEN: POST /api/v1/batches
        THEN: 422 Unprocessable Entity (pydantic validation error)
        """
        payload = {
            "batch_uuid": "not-a-uuid",  # Invalid
            "device_id": "test-device",
            ...
        }
        
        signature = create_device_signature("test-device", payload)
        
        response = await client.post(
            "/api/v1/batches",
            json=payload,
            headers={
                "X-Device-Id": "test-device",
                "X-Signature": signature,
                "X-Idempotency-Key": str(uuid4()),
            },
        )
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_batch_creation_gps_out_of_bounds_400(self, client: AsyncClient):
        """
        GIVEN: Batch payload with invalid GPS (lat > 90)
        WHEN: POST /api/v1/batches
        THEN: 400 Bad Request
        """
        payload = {
            "batch_uuid": str(uuid4()),
            "latitude": 95.0,  # Out of bounds
            "longitude": 20.0,
            ...
        }
        
        signature = create_device_signature("test-device", payload)
        
        response = await client.post(
            "/api/v1/batches",
            json=payload,
            headers={...},
        )
        
        assert response.status_code in (400, 422)
        assert "latitude" in response.json()["detail"].lower()
```

**Run these tests:**
```bash
pytest backend/tests/test_api_contract_batch_creation.py -v
# Expected: all pass (if any fail, read the assertion and fix the bug)
```

---

## 1.3 Export Endpoint Tests (CSI & Rainbow)

### CSI Export Validation

**File:** `backend/tests/test_csi_export_schema.py`

```python
class TestCSIExportSchema:
    """Validate CSI export payload structure."""
    
    @pytest.mark.asyncio
    async def test_csi_export_has_all_required_sections(self, client: AsyncClient):
        """CSI report must have all 10 sections."""
        batch_uuid = create_issuable_batch().batch_uuid
        admin_secret = "test-admin-secret"
        
        response = await client.get(
            f"/api/v1/batches/{batch_uuid}/export/csi",
            headers={"X-Admin-Secret": admin_secret},
        )
        
        assert response.status_code == 200
        csi = response.json()
        
        required_sections = [
            "project_id",
            "batch_uuid",
            "sourcing",
            "moisture_profile",
            "kiln_profile",
            "composite_samples",
            "yield_metrics",
            "transport_chain",
            "lab_results",
            "credit_calculation",
            "export_metadata",
        ]
        
        for section in required_sections:
            assert section in csi, f"CSI missing section: {section}"
    
    @pytest.mark.asyncio
    async def test_csi_sourcing_section_complete(self, client: AsyncClient):
        """CSI sourcing section must include location, species, farmer ID."""
        batch = create_batch_with_location(
            latitude=10.5,
            longitude=20.5,
            species="Lantana camara",
            device_id="farmer-001",
        )
        
        response = await client.get(
            f"/api/v1/batches/{batch.batch_uuid}/export/csi",
            headers={"X-Admin-Secret": "test-admin-secret"},
        )
        
        csi = response.json()
        sourcing = csi["sourcing"]
        
        assert sourcing["source_location"]["latitude"] == 10.5
        assert sourcing["source_location"]["longitude"] == 20.5
        assert sourcing["species"] == "Lantana camara"
        assert sourcing["farmer_id"] == "farmer-001"
    
    @pytest.mark.asyncio
    async def test_csi_moisture_profile_counts_correct(self, client: AsyncClient):
        """CSI moisture_profile.readings_count must match actual readings."""
        batch = create_batch(biomass_input_kg=500)  # Needs 5+ readings
        
        for i in range(5):
            add_moisture_reading(batch, moisture_percent=15.0 + i)
        
        response = await client.get(
            f"/api/v1/batches/{batch.batch_uuid}/export/csi",
            headers={"X-Admin-Secret": "test-admin-secret"},
        )
        
        csi = response.json()
        moisture = csi["moisture_profile"]
        
        assert moisture["readings_count"] == 5
        assert moisture["readings_compliant"] == True
        assert len(moisture["readings"]) == 5
    
    @pytest.mark.asyncio
    async def test_csi_credit_calculation_matches_batch(self, client: AsyncClient):
        """CSI credit_calculation.net_credit_t_co2e must match batch.net_credit_t_co2e."""
        batch = create_batch(
            dry_yield_kg=100,
            lab_h_corg=0.75,
        )
        
        expected_credit = 100 * 0.75 * 3.67  # ~275
        
        response = await client.get(
            f"/api/v1/batches/{batch.batch_uuid}/export/csi",
            headers={"X-Admin-Secret": "test-admin-secret"},
        )
        
        csi = response.json()
        actual_credit = csi["credit_calculation"]["net_credit_t_co2e"]
        
        assert actual_credit == pytest.approx(expected_credit, rel=0.01)
```

### Rainbow Export Validation

**File:** `backend/tests/test_rainbow_export_schema.py`

```python
class TestRainbowExportSchema:
    """Validate Rainbow export payload structure."""
    
    @pytest.mark.asyncio
    async def test_rainbow_export_has_required_fields(self, client: AsyncClient):
        """Rainbow export must have h_corg, dry_yield, credits."""
        batch = create_issuable_batch()
        
        response = await client.get(
            f"/api/v1/batches/{batch.batch_uuid}/export/rainbow",
            headers={"X-Admin-Secret": "test-admin-secret"},
        )
        
        assert response.status_code == 200
        rainbow = response.json()
        
        required = ["h_corg_ratio", "dry_yield_kg", "estimated_credits_t_co2e", "standard"]
        for field in required:
            assert field in rainbow, f"Rainbow missing field: {field}"
    
    @pytest.mark.asyncio
    async def test_rainbow_defaults_h_corg_if_not_measured(self, client: AsyncClient):
        """Rainbow defaults h_corg to 0.5 if lab hasn't measured it."""
        batch = create_batch(lab_h_corg=None)
        
        response = await client.get(
            f"/api/v1/batches/{batch.batch_uuid}/export/rainbow",
            headers={"X-Admin-Secret": "test-admin-secret"},
        )
        
        rainbow = response.json()
        assert rainbow["h_corg_ratio"] == 0.5
        assert rainbow["h_corg_source"] == "assumed"
```

**Run all export tests:**
```bash
pytest backend/tests/test_*export*.py -v
# Expected: 20+ tests, all pass
```

---

## 1.4 Integration Tests — Full Workflows

**File:** `backend/tests/test_integration_full_workflows.py`

```python
class TestFullBatchWorkflow:
    """End-to-end batch creation → evidence → compliance → export."""
    
    @pytest.mark.asyncio
    async def test_complete_batch_lifecycle(self, client: AsyncClient):
        """
        1. Device creates batch
        2. Adds evidence (moisture, composite sample)
        3. Lab adds h_corg measurement
        4. Portal issues credit
        5. Export to CSI/Rainbow
        """
        device_id = "farmer-001"
        batch_uuid = str(uuid4())
        
        # STEP 1: Create batch
        batch_payload = create_realistic_batch(
            device_id=device_id,
            batch_uuid=batch_uuid,
        )
        
        response = await client.post(
            "/api/v1/batches",
            json=batch_payload,
            headers={
                "X-Device-Id": device_id,
                "X-Signature": create_signature(device_id, batch_payload),
                "X-Idempotency-Key": str(uuid4()),
            },
        )
        assert response.status_code == 201
        
        # STEP 2: Add moisture evidence (C2 compliance)
        for i in range(5):  # 500 kg batch needs 5+ readings
            moisture_payload = {
                "batch_uuid": batch_uuid,
                "moisture_percent": 15.0 + i,
                "photo_operation_id": f"photo-{i}",
            }
            response = await client.post(
                f"/api/v1/evidence/{batch_uuid}/moisture",
                json=moisture_payload,
                headers={
                    "X-Device-Id": device_id,
                    "X-Signature": create_signature(device_id, moisture_payload),
                },
            )
            assert response.status_code == 200
        
        # STEP 3: Check compliance before lab measurement
        response = await client.get(
            f"/api/v1/batches/{batch_uuid}/compliance",
            headers={"X-Admin-Secret": "test-admin-secret"},
        )
        compliance_before = response.json()
        assert compliance_before["provisional"] == True  # h_corg not measured yet
        
        # STEP 4: Lab measures h_corg
        lab_payload = {
            "batch_uuid": batch_uuid,
            "lab_h_corg": 0.75,
            "certified_by": "Lab ABC",
        }
        response = await client.post(
            f"/api/v1/portal/batches/{batch_uuid}/lab-results",
            json=lab_payload,
            headers={"Authorization": "Bearer admin-token"},
        )
        assert response.status_code == 200
        
        # STEP 5: Check compliance after lab measurement
        response = await client.get(
            f"/api/v1/batches/{batch_uuid}/compliance",
            headers={"X-Admin-Secret": "test-admin-secret"},
        )
        compliance_after = response.json()
        assert compliance_after["provisional"] == False  # Now issuable
        assert compliance_after["issuable"] == True
        
        # STEP 6: Issue credit
        response = await client.post(
            f"/api/v1/portal/batches/{batch_uuid}/issue",
            headers={"Authorization": "Bearer admin-token"},
        )
        assert response.status_code == 200
        
        # STEP 7: Export CSI
        response = await client.get(
            f"/api/v1/batches/{batch_uuid}/export/csi",
            headers={"X-Admin-Secret": "test-admin-secret"},
        )
        assert response.status_code == 200
        csi = response.json()
        assert csi["lab_results"]["h_corg"] == 0.75
        
        # STEP 8: Export Rainbow
        response = await client.get(
            f"/api/v1/batches/{batch_uuid}/export/rainbow",
            headers={"X-Admin-Secret": "test-admin-secret"},
        )
        assert response.status_code == 200
        rainbow = response.json()
        assert rainbow["h_corg_ratio"] == 0.75
```

**Run integration tests:**
```bash
pytest backend/tests/test_integration_full_workflows.py -v --tb=short
# Expected: workflow tests pass, any failure indicates logic bug
```

---

## 1.5 Performance Baseline Tests

**File:** `backend/tests/test_performance.py`

```python
import time
import statistics

class TestPerformanceBaselines:
    """Establish and verify performance baselines."""
    
    @pytest.mark.asyncio
    async def test_batch_creation_latency(self, client: AsyncClient):
        """Batch creation P99 latency must be < 500 ms."""
        latencies = []
        
        for i in range(100):
            start = time.time()
            
            response = await client.post(
                "/api/v1/batches",
                json=create_test_batch(i),
                headers=create_signature_headers(f"device-{i}"),
            )
            
            latency = (time.time() - start) * 1000  # milliseconds
            latencies.append(latency)
            
            assert response.status_code == 201
        
        latencies.sort()
        p99 = latencies[int(len(latencies) * 0.99)]
        p95 = latencies[int(len(latencies) * 0.95)]
        mean = statistics.mean(latencies)
        
        print(f"\nBatch creation latency (100 requests):")
        print(f"  Mean: {mean:.1f} ms")
        print(f"  P95:  {p95:.1f} ms")
        print(f"  P99:  {p99:.1f} ms")
        
        assert p99 < 500, f"P99 latency {p99:.1f} ms exceeds target 500 ms"
    
    @pytest.mark.asyncio
    async def test_concurrent_batch_creation(self, client: AsyncClient):
        """50 concurrent batch creations must complete in < 30 seconds."""
        import asyncio
        
        async def create_batch(index):
            return await client.post(
                "/api/v1/batches",
                json=create_test_batch(index),
                headers=create_signature_headers(f"device-{index}"),
            )
        
        start = time.time()
        
        tasks = [create_batch(i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        
        duration = time.time() - start
        success_count = sum(1 for r in results if r.status_code == 201)
        
        print(f"\nConcurrent batch creation (50 devices):")
        print(f"  Duration: {duration:.1f} seconds")
        print(f"  Success: {success_count}/50")
        
        assert success_count >= 45, f"Only {success_count}/50 succeeded"
        assert duration < 30, f"Took {duration:.1f}s, target is 30s"
```

**Run performance tests:**
```bash
pytest backend/tests/test_performance.py -v -s
# Expected: prints performance metrics, assertions pass
```

---

## 1.6 Running All Backend Tests

```bash
# Run everything
cd backend
python -m pytest tests/ -v --tb=short

# Or run by category
python -m pytest tests/test_credit_calculation.py -v
python -m pytest tests/test_api_contract*.py -v
python -m pytest tests/test_*export*.py -v
python -m pytest tests/test_integration_full_workflows.py -v

# Expected summary:
# ============ 500+ tests passed in XX seconds ============
# (zero failures, zero errors)
```

---

# SECTION 2: MOBILE TEST STRATEGY

## 2.1 Widget Tests — Individual Screens

### Enrollment Screen Test

**File:** `test/widget_test_enrollment.dart`

```dart
void main() {
  group('Enrollment Screen', () {
    testWidgets('renders enrollment form with input fields', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: EnrollmentScreen(),
        ),
      );

      // Verify form fields exist
      expect(find.byType(TextFormField), findsWidgets);
      expect(find.text('Device Name'), findsOneWidget);
      expect(find.text('Farmer Name'), findsOneWidget);

      // Verify submit button
      expect(find.byType(ElevatedButton), findsWidgets);
    });

    testWidgets('enrollment button disabled until form filled', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: EnrollmentScreen(),
        ),
      );

      // Initially, submit button should be disabled
      final submitButton = find.byType(ElevatedButton);
      expect(tester.widget<ElevatedButton>(submitButton).enabled, false);

      // Fill in form
      await tester.enterText(find.byType(TextFormField).first, 'Device-001');
      await tester.pumpWidget(); // Rebuild

      // Button should now be enabled
      expect(tester.widget<ElevatedButton>(submitButton).enabled, true);
    });

    testWidgets('enrollment submits and navigates', (WidgetTester tester) async {
      // Mock the enrollment API call
      // (would use mockito or similar in real code)

      await tester.pumpWidget(
        const MaterialApp(
          home: EnrollmentScreen(),
        ),
      );

      // Fill form
      await tester.enterText(find.byType(TextFormField).first, 'Device-001');
      await tester.enterText(find.byType(TextFormField).at(1), 'John Farmer');

      // Tap submit
      await tester.tap(find.byType(ElevatedButton));
      await tester.pumpAndSettle(); // Wait for navigation

      // Verify navigation to next screen
      // (exact assertion depends on nav implementation)
    });
  });
}
```

### Moisture Verification Screen Test

**File:** `test/widget_test_moisture.dart`

```dart
void main() {
  group('Moisture Verification Screen', () {
    testWidgets('renders camera and reading list', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: MoistureVerificationScreen(),
        ),
      );

      // Camera preview or placeholder
      expect(find.byType(Container), findsWidgets);

      // "Add Reading" button
      expect(find.text('Add Moisture Reading'), findsOneWidget);

      // Reading list (initially empty)
      expect(find.text('0 readings'), findsOneWidget);
    });

    testWidgets('add reading updates count', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: MoistureVerificationScreen(),
        ),
      );

      // Initial state: 0 readings
      expect(find.text('0 readings'), findsOneWidget);

      // Tap "Add Reading"
      await tester.tap(find.text('Add Moisture Reading'));
      await tester.pumpAndSettle();

      // Simulate entering moisture value
      await tester.enterText(find.byType(TextFormField), '15.5');
      await tester.tap(find.text('Save'));
      await tester.pumpAndSettle();

      // Count should update
      expect(find.text('1 reading'), findsOneWidget);
    });

    testWidgets('next button disabled until min readings met', (WidgetTester tester) async {
      final batch = createTestBatch(biomassInputKg: 500);  // Needs 5+ readings

      await tester.pumpWidget(
        const MaterialApp(
          home: MoistureVerificationScreen(batch: batch),
        ),
      );

      // Next button initially disabled (0 < 5 readings)
      expect(
        tester.widget<ElevatedButton>(find.text('Next')).enabled,
        false,
      );

      // Add 4 readings
      for (int i = 0; i < 4; i++) {
        await tester.tap(find.text('Add Moisture Reading'));
        await tester.pumpAndSettle();
        await tester.enterText(find.byType(TextFormField).last, '15.0');
        await tester.tap(find.text('Save'));
        await tester.pumpAndSettle();
      }

      // Still disabled
      expect(
        tester.widget<ElevatedButton>(find.text('Next')).enabled,
        false,
      );

      // Add 5th reading
      await tester.tap(find.text('Add Moisture Reading'));
      await tester.pumpAndSettle();
      await tester.enterText(find.byType(TextFormField).last, '15.0');
      await tester.tap(find.text('Save'));
      await tester.pumpAndSettle();

      // Now enabled
      expect(
        tester.widget<ElevatedButton>(find.text('Next')).enabled,
        true,
      );
    });
  });
}
```

**Run widget tests:**
```bash
cd flutter_dmrv
flutter test test/widget_test_*.dart -v

# Expected:
# ✓ Enrollment Screen | renders enrollment form with input fields
# ✓ Enrollment Screen | enrollment button disabled until form filled
# ...
# ======================== XX tests passed ========================
```

---

## 2.2 Integration Tests — Batch Workflows

**File:** `test/integration_test_batch_workflow.dart`

```dart
import 'package:integration_test/integration_test.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/main.dart' as app;

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  group('Full Batch Workflow', () {
    testWidgets(
      'enrollment → sourcing → moisture → biomass → sync',
      (WidgetTester tester) async {
        app.main();
        await tester.pumpAndSettle();

        // STEP 1: Enrollment
        expect(find.text('Welcome to Kon-Tiki'), findsOneWidget);
        await tester.enterText(find.byType(TextFormField).first, 'Device-TEST-001');
        await tester.tap(find.text('Enroll'));
        await tester.pumpAndSettle();

        // STEP 2: Lantana sourcing
        expect(find.text('Lantana Sourcing'), findsOneWidget);
        await tester.enterText(
          find.byType(TextFormField).first,
          'Farmer-Name',
        );
        await tester.tap(find.text('Capture GPS'));
        await tester.pumpAndSettle();
        await tester.tap(find.text('Next'));
        await tester.pumpAndSettle();

        // STEP 3: Moisture readings (min 5)
        expect(find.text('Moisture Verification'), findsOneWidget);
        for (int i = 0; i < 5; i++) {
          await tester.tap(find.text('Add Reading'));
          await tester.pumpAndSettle();
          await tester.enterText(find.byType(TextFormField).last, '15.0');
          await tester.tap(find.text('Save'));
          await tester.pumpAndSettle();
        }
        await tester.tap(find.text('Next'));
        await tester.pumpAndSettle();

        // STEP 4: Biomass input
        expect(find.text('Biomass Input'), findsOneWidget);
        await tester.enterText(find.byType(TextFormField).first, '500');  // kg
        await tester.tap(find.text('Next'));
        await tester.pumpAndSettle();

        // STEP 5: Check sync health
        expect(find.text('Sync Health'), findsOneWidget);
        expect(find.text('1 pending batch'), findsOneWidget);  // Should show 1 pending

        // STEP 6: Initiate sync
        await tester.tap(find.text('Sync Now'));
        await tester.pumpAndSettle(const Duration(seconds: 3));

        // STEP 7: Verify sync succeeded
        expect(find.text('Sync complete'), findsOneWidget);
      },
    );

    testWidgets(
      'batch data persists in local database',
      (WidgetTester tester) async {
        // Create batch through workflow
        // ...

        // Restart app
        await tester.binding.window.physicalSizeTestValue = const Size(400, 800);
        addTearDown(tester.binding.window.clearPhysicalSizeTestValue);

        // Re-launch app
        app.main();
        await tester.pumpAndSettle();

        // Navigate to batch detail
        // ...

        // Verify batch data is still there
        expect(find.text('5 moisture readings'), findsOneWidget);
        expect(find.text('500 kg biomass'), findsOneWidget);
      },
    );
  });
}
```

**Run integration tests:**
```bash
cd flutter_dmrv
flutter test integration_test/ -v

# Expected:
# ✓ Full Batch Workflow | enrollment → sourcing → moisture → biomass → sync
# ✓ Full Batch Workflow | batch data persists in local database
# ======================== XX tests passed ========================
```

---

## 2.3 Provider State Tests

**File:** `test/unit_test_providers.dart`

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dmrv_app/providers/batch_session.dart';

void main() {
  group('Batch Session Provider', () {
    test('initializes with empty batch', () {
      final container = ProviderContainer();
      final state = container.read(batchSessionProvider);

      expect(state.batchUuid, isNull);
      expect(state.biomassInputKg, isNull);
      expect(state.moistureReadings, isEmpty);
    });

    test('setBiomassInput updates state', () {
      final container = ProviderContainer();

      container.read(batchSessionProvider.notifier).setBiomassInput(500);

      final state = container.read(batchSessionProvider);
      expect(state.biomassInputKg, 500);
    });

    test('addMoistureReading appends to list', () {
      final container = ProviderContainer();

      container.read(batchSessionProvider.notifier).addMoistureReading(15.0);
      container.read(batchSessionProvider.notifier).addMoistureReading(16.0);

      final state = container.read(batchSessionProvider);
      expect(state.moistureReadings.length, 2);
      expect(state.moistureReadings[0], 15.0);
      expect(state.moistureReadings[1], 16.0);
    });

    test('reset clears all state', () {
      final container = ProviderContainer();

      // Set some state
      container.read(batchSessionProvider.notifier).setBiomassInput(500);
      container.read(batchSessionProvider.notifier).addMoistureReading(15.0);

      // Reset
      container.read(batchSessionProvider.notifier).reset();

      // Verify cleared
      final state = container.read(batchSessionProvider);
      expect(state.biomassInputKg, isNull);
      expect(state.moistureReadings, isEmpty);
    });
  });
}
```

**Run provider tests:**
```bash
cd flutter_dmrv
flutter test test/unit_test_providers.dart -v
```

---

## 2.4 Run All Mobile Tests

```bash
cd flutter_dmrv

# Widget tests
flutter test test/widget_test_*.dart -v

# Unit tests
flutter test test/unit_test_*.dart -v

# Integration tests (if on device/emulator)
flutter test integration_test/ -v

# All together
flutter test -v

# Expected summary:
# ====================== XX tests passed in XX seconds =======================
```

---

# SECTION 3: PORTAL (REACT) TEST STRATEGY

## 3.1 Component Unit Tests

**File:** `portal/src/__tests__/ComplianceChecklist.test.tsx`

```typescript
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import ComplianceChecklist from "../components/ComplianceChecklist";

describe("ComplianceChecklist", () => {
  it("renders checklist items", () => {
    const checklist = [
      { code: "C1", section: "Sourcing", label: "GPS recorded", ok: true, enforcement: "required" },
      { code: "C2", section: "Moisture", label: "5+ readings", ok: false, enforcement: "required" },
    ];

    render(<ComplianceChecklist checklist={checklist} />);

    expect(screen.getByText("C1")).toBeInTheDocument();
    expect(screen.getByText("C2")).toBeInTheDocument();
  });

  it("shows checkmark for passing items", () => {
    const checklist = [
      { code: "C1", label: "GPS recorded", ok: true, enforcement: "required" },
    ];

    render(<ComplianceChecklist checklist={checklist} />);

    const item = screen.getByText("C1").closest("div");
    expect(item).toHaveClass("ok"); // or similar class for passed item
  });

  it("shows X mark for failing items", () => {
    const checklist = [
      { code: "C2", label: "5+ readings", ok: false, enforcement: "required" },
    ];

    render(<ComplianceChecklist checklist={checklist} />);

    const item = screen.getByText("C2").closest("div");
    expect(item).toHaveClass("fail"); // or similar class for failed item
  });
});
```

## 3.2 Page Integration Tests

**File:** `portal/src/__tests__/BatchDetail.test.tsx`

```typescript
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { BrowserRouter } from "react-router-dom";
import BatchDetail from "../pages/BatchDetail";
import * as api from "../api";

// Mock the API
vi.mock("../api");

describe("Batch Detail Page", () => {
  beforeEach(() => {
    // Reset mocks
    vi.clearAllMocks();
  });

  it("loads and displays batch details", async () => {
    const mockBatch = {
      batch: {
        batch_uuid: "uuid-123",
        device_id: "device-1",
        status: "ACCEPTED",
        provisional: false,
        net_credit_t_co2e: 150.5,
      },
      compliance: {
        issuable: true,
        checklist: [
          { code: "C1", label: "Sourcing", ok: true, enforcement: "required" },
        ],
      },
      evidence_counts: { moisture: 5, pyrolysis: 1 },
      media: [],
    };

    vi.mocked(api.getBatch).mockResolvedValue(mockBatch);

    render(
      <BrowserRouter>
        <BatchDetail />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("150.5")).toBeInTheDocument();
      expect(screen.getByText("ISSUABLE")).toBeInTheDocument();
    });
  });

  it("shows Issue Credit button when issuable", async () => {
    const mockBatch = {
      batch: { status: "ACCEPTED", net_credit_t_co2e: 150.5 },
      compliance: { issuable: true, checklist: [] },
      evidence_counts: {},
      media: [],
    };

    vi.mocked(api.getBatch).mockResolvedValue(mockBatch);

    render(
      <BrowserRouter>
        <BatchDetail />
      </BrowserRouter>
    );

    await waitFor(() => {
      const button = screen.getByRole("button", { name: /issue credit/i });
      expect(button).toBeInTheDocument();
      expect(button).not.toBeDisabled();
    });
  });

  it("shows Export buttons when issued", async () => {
    const mockBatch = {
      batch: { status: "ISSUED", net_credit_t_co2e: 150.5 },
      compliance: { issuable: true, checklist: [] },
      evidence_counts: {},
      media: [],
    };

    vi.mocked(api.getBatch).mockResolvedValue(mockBatch);

    render(
      <BrowserRouter>
        <BatchDetail />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /export csi/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /export rainbow/i })).toBeInTheDocument();
    });
  });

  it("downloads CSI export on button click", async () => {
    const mockBatch = {
      batch: { status: "ISSUED", batch_uuid: "uuid-123" },
      compliance: { issuable: true, checklist: [] },
      evidence_counts: {},
      media: [],
    };

    const mockCSI = { batch_uuid: "uuid-123", credit_calculation: {} };

    vi.mocked(api.getBatch).mockResolvedValue(mockBatch);
    vi.mocked(api.downloadCSIExport).mockResolvedValue(mockCSI);

    render(
      <BrowserRouter>
        <BatchDetail />
      </BrowserRouter>
    );

    await waitFor(() => {
      const button = screen.getByRole("button", { name: /export csi/i });
      fireEvent.click(button);
    });

    await waitFor(() => {
      expect(api.downloadCSIExport).toHaveBeenCalledWith("uuid-123");
    });
  });
});
```

## 3.3 Run Portal Tests

```bash
cd portal

# Install dependencies
npm install

# Run tests
npm test

# With coverage
npm test -- --coverage

# Expected:
# PASS src/__tests__/ComplianceChecklist.test.tsx
# PASS src/__tests__/BatchDetail.test.tsx
# PASS src/__tests__/api.test.ts
# ...
# ===================== XX tests passed =====================
```

---

# SECTION 4: END-TO-END INTEGRATION TEST

**File:** `backend/tests/test_e2e_complete_system.py`

```python
"""
End-to-end test: Mobile → Backend → Portal → Export
This test verifies the ENTIRE system works together.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_complete_system_flow(
    mobile_api_client,
    portal_api_client,
    admin_api_client,
):
    """
    Complete system workflow:
    1. Mobile: Device enrolls
    2. Mobile: Creates batch with all evidence
    3. Backend: Stores and validates
    4. Portal: Admin reviews compliance
    5. Portal: Issues credit
    6. Backend: Exports to CSI and Rainbow
    """
    
    # ===== PHASE 1: MOBILE ENROLLMENT =====
    device_id = f"device-e2e-{uuid4()}"
    enroll_resp = await mobile_api_client.post(
        "/api/v1/devices/enroll",
        json={"device_id": device_id},
    )
    assert enroll_resp.status_code == 201
    device_key = enroll_resp.json()["device_key"]
    
    # ===== PHASE 2: MOBILE BATCH CREATION =====
    batch_uuid = str(uuid4())
    batch_payload = {
        "batch_uuid": batch_uuid,
        "device_id": device_id,
        "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
        "biomass_type": "Lantana",
        "species": "Lantana camara",
        "latitude": 10.5,
        "longitude": 20.5,
        "gps_accuracy_m": 5.0,
        "kiln_type": "open",
        "kiln_id": "kiln-001",
        "wet_yield_kg": 500,
        "dry_yield_kg": 120,
        "yield_estimation_method": "WEIGHED",
        "moisture_content_percent": 15.0,
        "biomass_input_kg": 500,
        "sha256_hash": "test-hash-123",
    }
    
    # Sign with device key
    signature = sign_with_device_key(device_key, batch_payload)
    
    batch_resp = await mobile_api_client.post(
        "/api/v1/batches",
        json=batch_payload,
        headers={
            "X-Device-Id": device_id,
            "X-Signature": signature,
            "X-Idempotency-Key": str(uuid4()),
        },
    )
    assert batch_resp.status_code == 201
    
    # ===== PHASE 3: MOBILE EVIDENCE UPLOAD =====
    # Add 5 moisture readings (C2 compliance)
    for i in range(5):
        moisture_payload = {
            "batch_uuid": batch_uuid,
            "moisture_percent": 15.0 + i,
            "photo_operation_id": f"photo-{i}",
        }
        moisture_sig = sign_with_device_key(device_key, moisture_payload)
        
        resp = await mobile_api_client.post(
            f"/api/v1/evidence/{batch_uuid}/moisture",
            json=moisture_payload,
            headers={
                "X-Device-Id": device_id,
                "X-Signature": moisture_sig,
            },
        )
        assert resp.status_code == 200
    
    # ===== PHASE 4: PORTAL COMPLIANCE CHECK =====
    compliance_resp = await admin_api_client.get(
        f"/api/v1/batches/{batch_uuid}/compliance",
        headers={"X-Admin-Secret": "test-admin-secret"},
    )
    assert compliance_resp.status_code == 200
    compliance = compliance_resp.json()
    
    # Before lab h_corg: should be provisional
    assert compliance["provisional"] == True
    assert "assumed_h_corg" in compliance["reasons"]
    
    # ===== PHASE 5: PORTAL LAB ENTRY =====
    lab_resp = await portal_api_client.post(
        f"/api/v1/portal/batches/{batch_uuid}/lab-results",
        json={
            "batch_uuid": batch_uuid,
            "lab_h_corg": 0.75,
            "certified_by": "Lab ABC",
        },
        headers={"Authorization": "Bearer admin-token"},
    )
    assert lab_resp.status_code == 200
    
    # ===== PHASE 6: PORTAL CREDIT ISSUANCE =====
    issue_resp = await portal_api_client.post(
        f"/api/v1/portal/batches/{batch_uuid}/issue",
        headers={"Authorization": "Bearer admin-token"},
    )
    assert issue_resp.status_code == 200
    issue_data = issue_resp.json()
    assert issue_data["status"] == "ISSUED"
    
    # ===== PHASE 7: CSI EXPORT =====
    csi_resp = await admin_api_client.get(
        f"/api/v1/batches/{batch_uuid}/export/csi",
        headers={"X-Admin-Secret": "test-admin-secret"},
    )
    assert csi_resp.status_code == 200
    csi = csi_resp.json()
    
    # Validate CSI structure
    assert csi["batch_uuid"] == str(batch_uuid)
    assert csi["sourcing"]["latitude"] == 10.5
    assert csi["moisture_profile"]["readings_count"] == 5
    assert csi["lab_results"]["h_corg"] == 0.75
    assert csi["credit_calculation"]["net_credit_t_co2e"] > 0
    
    # ===== PHASE 8: RAINBOW EXPORT =====
    rainbow_resp = await admin_api_client.get(
        f"/api/v1/batches/{batch_uuid}/export/rainbow",
        headers={"X-Admin-Secret": "test-admin-secret"},
    )
    assert rainbow_resp.status_code == 200
    rainbow = rainbow_resp.json()
    
    # Validate Rainbow structure
    assert rainbow["batch_uuid"] == str(batch_uuid)
    assert rainbow["h_corg_ratio"] == 0.75
    assert rainbow["dry_yield_kg"] == 120
    assert rainbow["estimated_credits_t_co2e"] > 0
    
    # ===== SUCCESS =====
    print(f"\n✓ Complete system flow passed!")
    print(f"  Device: {device_id}")
    print(f"  Batch: {batch_uuid}")
    print(f"  Credits issued: {issue_data.get('net_credit_t_co2e')} tCO₂e")
    print(f"  CSI export: {csi['batch_uuid'][:8]}...")
    print(f"  Rainbow export: {rainbow['batch_uuid'][:8]}...")
```

**Run E2E test:**
```bash
pytest backend/tests/test_e2e_complete_system.py -v -s --tb=short
# Expected: test passes, prints success summary
```

---

# SECTION 5: FINAL TEST RUN CHECKLIST

## Pre-Deployment Test Execution

Run this exact sequence:

```bash
# ===== BACKEND TESTS =====
cd backend
python -m pytest tests/ -v --tb=short

# Check: 500+ tests pass, 0 failures
# If any fail: STOP, fix the bug, re-run

# ===== MOBILE TESTS =====
cd ../flutter_dmrv
flutter test -v

# Check: 50+ tests pass, 0 failures
# If any fail: STOP, fix the bug, re-run

# ===== PORTAL TESTS =====
cd ../portal
npm test -- --coverage

# Check: 30+ tests pass, coverage > 80%
# If any fail: STOP, fix the bug, re-run

# ===== E2E TEST (REQUIRES RUNNING BACKEND) =====
# Start backend in one terminal:
cd backend
docker compose up -d

# In another terminal:
sleep 10
pytest tests/test_e2e_complete_system.py -v -s

# Check: E2E test passes
# If fails: read error, fix, re-run

# ===== LOAD TEST =====
pytest tests/test_performance.py -v -s

# Check: all performance assertions pass
# If any fail: optimize code, re-run

# ===== SECURITY TEST =====
pytest tests/test_security_hardening.py -v

# Check: all security tests pass

# ===== FINAL STATUS =====
echo "✓ All tests passed!"
echo "✓ Ready for production deployment"
```

---

## Success Criteria

✅ **Backend:** 500+ tests pass, zero failures  
✅ **Mobile:** 50+ tests pass, zero failures  
✅ **Portal:** 30+ tests pass, zero failures  
✅ **E2E:** Complete system workflow passes  
✅ **Performance:** P99 latency < 500ms, throughput > 10 batches/sec  
✅ **Security:** All auth/encryption tests pass  
✅ **Code coverage:** >80% for critical paths  

**If ANY test fails:** Fix the bug, commit fix, re-run entire test suite. Do NOT deploy with failing tests.

---

**END OF COMPREHENSIVE TEST STRATEGY**
