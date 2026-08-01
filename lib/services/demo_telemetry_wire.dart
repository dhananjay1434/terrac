import 'package:flutter/foundation.dart';

import '../data/local/app_database.dart';
import 'crypto_signer.dart';
import 'simulation/demo_readiness.dart';
import 'simulation/simulated_edge_device.dart';
import 'telemetry_courier.dart';
import 'telemetry_outbox_drift.dart';

/// The actual demo-wire logic, unconditional — [maybeStartDemoTelemetry] is
/// the gated entry point real call sites use; this is split out so the
/// DMRV_DEMO_MODE ON path is provably correct in tests even though the
/// dart-define const can't be flipped at test-run time (same pattern as
/// `geofenceWarningFor(enforced: ...)` in geofence_check.dart).
Future<void> startDemoTelemetry({
  required AppDatabase db,
  required String sessionUuid,
  SimulatedEdgeDevice? deviceOverride,
}) async {
  // Soft-fail: never throw. If enrollment can't complete, we simply don't enqueue
  // v2 chunks (the phone UI + legacy write are unaffected).
  final ready = await ensureDemoReady();
  if (!ready.ok) return;
  final device = deviceOverride ??
      SimulatedEdgeDevice(
        deviceId: await CryptoSigner.getDeviceId(),
        sessionUuid: sessionUuid,
      );
  // Live streaming: chunks enqueue as the burn progresses (the call site
  // fire-and-forgets this, so the ~12s accelerated stream never blocks START).
  await TelemetryCourier(TelemetryOutboxDrift(db)).drainStream(device.stream());
}

/// DMRV_DEMO_MODE wire (WIRING P16): on burn start, spins up a
/// SimulatedEdgeDevice and couriers its signed T1+LOAD chunks into the real
/// outbox (P15's TelemetryOutboxDrift), so the on-phone demo burn also lands
/// in the portal. Dual-runs beside the untouched legacy PyrolysisTelemetry
/// write in pyrolysis_screen.dart — this function never touches that path.
/// Inert unless DMRV_DEMO_MODE is set (release builds always force it off).
Future<void> maybeStartDemoTelemetry({
  required AppDatabase db,
  required String sessionUuid,
}) async {
  const isDemoFlag = bool.fromEnvironment(
    'DMRV_DEMO_MODE',
    defaultValue: false,
  );
  if (!isDemoFlag || kReleaseMode) return;
  await startDemoTelemetry(db: db, sessionUuid: sessionUuid);
}
