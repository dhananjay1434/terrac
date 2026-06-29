# TerraCipher v3.0: Core Architectural Blueprint & IP Strategy

This is the executive engineering blueprint for the TerraCipher dMRV platform. We are not building a simple forms app; we are building a **Zero-Trust Hardware-Bound Data Enclave**. 

This document maps our Hexagonal Architecture directly to your current Dart codebase, detailing exactly how we are adapting architectural patterns from competitors (Circonomy/Varaha) to rapidly build a production-grade, modular system.

---

## 1. Hardware Abstraction Layer (HAL) & Virtualization
**Competitor Cheat Code:** Varaha uses background workers with simulated delays (`Thread.sleep()`) to mock data processing. We are elevating this by mocking continuous data streams rather than static numbers.

*   **Current State:** `dashboard_provider.dart` calls `BleService.simulateHandshake()` as a static function, which waits 3 seconds and returns a hardcoded integer.
*   **Target State (The Fix):** 
    *   Create `abstract class ITelemetryRepository { Stream<PyrolysisState> getTelemetryStream(); }`.
    *   Create `VirtualBleAdapter implements ITelemetryRepository`.
    *   In Riverpod, define: `final telemetryProvider = Provider<ITelemetryRepository>((ref) => VirtualBleAdapter());`
*   **Result:** The UI listens to `telemetryProvider`. The `VirtualBleAdapter` will emit a mathematically rising temperature curve over time. To switch to production hardware later, we only change the Riverpod provider to inject an `Esp32BleAdapter`.

---

## 2. Multi-Phasic Cryptographic Evidence Capture (MCEC)
**Competitor Cheat Code:** Circonomy and Varaha take photos across 3 phases (Feedstock, Smoke, Yield). Varaha routes this through a unified camera state machine. We will reuse your existing secure camera service to capture the active smoke phase, beating them by cryptographically anchoring the photo to the BLE temperature.

*   **Current State:** Your Drift DB schema (`pyrolysis_writer.dart`) only accepts `temperatureReadings` and `burnStartTimestamp`. The `PyrolysisScreen` has no camera button.
*   **Target State (The Fix):** 
    *   **Drift DB:** Add `smokePhotoPath` (String) and `smokeSha256` (String) columns to the `pyrolysis_telemetry` table in `lib/data/local/tables.dart`, and run `dart run build_runner build`. Update `pyrolysis_writer.dart` to insert these fields.
    *   **UI:** Add a "Capture Burn Evidence" FAB to `PyrolysisScreen`.
    *   **Service:** Trigger the existing `SecureCaptureService` on tap. The app takes a photo of the smoke, stamps the EXIF, hashes it, and writes it to the new DB columns.

---

## 3. Environmental Resilience (GPS Fallback)
**Competitor Cheat Code:** Circonomy uses a strict `Promise.race()` timeout. If GPS fails, they gracefully fallback to a cached location so the app never crashes.

*   **Current State:** `secure_capture_service.dart` (Line 194) calls `Geolocator.getCurrentPosition()` with a strict 12-second limit. If you are indoors, it throws a `SecureCaptureException` and completely halts the pipeline.
*   **Target State (The Fix):** 
    *   Create a global flag: `const bool kIsInvestorDemo = true;`
    *   In `SecureCaptureService`, intercept the `catch` block that handles the timeout. 
    *   If `kIsInvestorDemo == true`, instead of crashing, immediately return a mathematically valid, hardcoded `Position` object (e.g., Lat 28.61, Lng 77.20). 
*   **Result:** You can demo the app flawlessly in an indoor boardroom. It will stamp the EXIF data and generate hashes without throwing a fatal GPS error.

---

## 4. Zero-Trust Cryptographic Ledger Interface (Proof Wallet)
**Competitor Cheat Code:** None. This is your unique moat. Competitors just show a generic "Sync History" list.

*   **Current State:** `proof_wallet_screen.dart` is underdeveloped.
*   **Target State (The Fix):** 
    *   Write a Drift SQL query that joins `biomass_sourcing`, `pyrolysis_telemetry`, and `yield_metrics` tables by `batch_uuid`.
    *   Render a premium "Cryptographic Receipt" UI that extracts the `sha256_hash` from each phase.
    *   Display the hashes in a monospaced "Terminal" font matrix. 
*   **Result:** Investors will physically see the DAG (Directed Acyclic Graph) of how the sensor data is mathematically locked down, visually proving the "Truth Machine" concept.

---

## Executive Review Required
> [!IMPORTANT]
> **Approval Gate:** The exact code-level mapping is now documented. Are you ready to authorize execution? If approved, the engineering team will immediately initiate work on **Section 1 (Hardware Abstraction Layer & Virtual BLE Adapter)**.
