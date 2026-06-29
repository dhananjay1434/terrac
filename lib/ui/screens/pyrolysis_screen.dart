import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../services/sync_queue_manager.dart';

import '../../data/local/database_provider.dart';
import '../../data/local/pyrolysis_writer.dart';
import '../../providers/batch_session_notifier.dart';
import '../../providers/dashboard_provider.dart';
import '../../providers/pyrolysis_ble_notifier.dart';
import '../../services/ble_permission_gate.dart';
import '../../services/ble_temperature_service.dart';
import '../design/app_theme.dart';

import '../design/premium_field_components.dart';
import '../widgets/integrity_footer.dart';
import '../widgets/rugged_button.dart';
import '../../services/secure_capture_service.dart';
import '../../providers/smoke_evidence_provider.dart';
import 'secure_camera_screen.dart';
import 'yield_scale_screen.dart';

/// =============================================================================
/// PyrolysisScreen — migrated to AppTheme (Tactical Titanium light)
/// =============================================================================
class PyrolysisScreen extends ConsumerStatefulWidget {
  const PyrolysisScreen({super.key});
  @override
  ConsumerState<PyrolysisScreen> createState() => _PyrolysisScreenState();
}

class _PyrolysisScreenState extends ConsumerState<PyrolysisScreen> {
  static const Color _errorRed = Color(0xFFDC2626);

  bool _permRequested = false;
  String? _permError;
  bool _ending = false;

  Future<void> _requestPermsAndStart() async {
    setState(() => _permRequested = true);
    final result = await BlePermissionGate().ensure();
    if (!result.isGranted) {
      setState(() => _permError = result.detail);
      return;
    }
    setState(() => _permError = null);
    await ref.read(pyrolysisBleProvider.notifier).beginBurn();
  }

  Future<void> _endBurn() async {
    if (_ending) return;
    setState(() => _ending = true);
    try {
      final batchUuid = ref.read(batchSessionProvider);
      if (batchUuid == null) {
        throw StateError('No active batch.');
      }
      final final_ = await ref.read(pyrolysisBleProvider.notifier).endBurn();
      if (final_.temperatureLog.isEmpty) {
        throw StateError('No temperature samples captured. Cannot persist.');
      }

      final db = await ref.read(appDatabaseProvider.future);
      final telemetryUuid = await db.insertPyrolysisTelemetryWithOutbox(
        batchUuid: batchUuid,
        kilnGrossCapacity: 200.0, // default kiln gross volume (L)
        burnStart: final_.burnStartAt!,
        burnEnd: final_.burnEndAt!,
        temperatureReadings: final_.temperatureLog,
      );
      ref.read(dashboardProvider.notifier).markBleVerified();
      debugPrint(
        '[PyrolysisScreen] insertPyrolysisTelemetryWithOutbox OK — '
        'telemetryUuid=$telemetryUuid samples=${final_.temperatureLog.length} '
        'min=${final_.minTemp} max=${final_.maxTemp}',
      );
      if (mounted) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute<void>(builder: (_) => const YieldScaleScreen()),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Persist failed: $e')));
      }
    } finally {
      if (mounted) setState(() => _ending = false);
    }
  }

  bool _isCapturingSmoke = false;

  Future<void> _captureSmoke(int currentProofsLength) async {
    if (_isCapturingSmoke) return;
    if (currentProofsLength >= 4) return;

    setState(() => _isCapturingSmoke = true);
    try {
      final result = await Navigator.of(context).push<SecureCaptureResult>(
        MaterialPageRoute(builder: (_) => const SecureCameraScreen()),
      );
      if (result != null && mounted) {
        final batchUuid = ref.read(batchSessionProvider);
        if (batchUuid == null) return;

        final type = [
          'smoke_0',
          'smoke_50',
          'smoke_90',
          'smoke_100',
        ][currentProofsLength];

        final db = await ref.read(appDatabaseProvider.future);
        await db.insertMediaCaptureAndEnqueue(
          batchUuid: batchUuid,
          captureType: type,
          sandboxPath: result.sandboxPath,
          sha256Hash: result.sha256Hash,
          isMockLocation: result.isMocked,
        );
      }
    } finally {
      if (mounted) setState(() => _isCapturingSmoke = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = ref.watch(pyrolysisBleProvider);
    final lastHash = ref.watch(dashboardProvider).lastHash;
    final proofsAsync = ref.watch(smokeEvidenceProvider);
    final proofs = proofsAsync.valueOrNull ?? [];

    return Scaffold(
      backgroundColor: AppTheme.tacticalTitanium,
      body: SafeArea(
        bottom: false,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            PremiumScreenHeader(
              stepNumber: '03',
              title: 'Pyrolysis · BLE Thermocouple',
              onBack: () => Navigator.of(context).pop(),
            ),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
                children: [
                  if (!_permRequested)
                    PremiumFieldButton(
                      label: 'CONNECT ESP32 THERMOCOUPLE',
                      testId: 'connect-esp32-thermocouple-btn',
                      state: FieldButtonState.hiVis,
                      onPressed: _requestPermsAndStart,
                    ),
                  if (_permError != null) ...[
                    const SizedBox(height: 16),
                    PremiumFieldPanel(
                      accentBorderColor: _errorRed,
                      padding: const EdgeInsets.all(16),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Icon(
                            Icons.error_outline,
                            color: _errorRed,
                            size: 28,
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text(
                                  'BLE PERMISSIONS REQUIRED',
                                  style: TextStyle(
                                    fontFamily: 'SpaceGrotesk',
                                    fontSize: 14,
                                    fontWeight: FontWeight.w700,
                                    letterSpacing: 0.6,
                                    color: _errorRed,
                                  ),
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  _permError!,
                                  style: const TextStyle(
                                    fontFamily: 'SpaceMono',
                                    fontSize: 13,
                                    fontWeight: FontWeight.w400,
                                    color: AppTheme.armorSlate,
                                  ),
                                ),
                                const SizedBox(height: 12),
                                Row(
                                  children: [
                                    Expanded(
                                      child: PremiumFieldButton(
                                        label: 'RETRY',
                                        testId: 'retry-ble-permissions-btn',
                                        state: FieldButtonState.hiVis,
                                        onPressed: _requestPermsAndStart,
                                      ),
                                    ),
                                    const SizedBox(width: 12),
                                    Expanded(
                                      child: PremiumFieldButton(
                                        label: 'OS SETTINGS',
                                        testId: 'open-os-settings-btn',
                                        state: FieldButtonState.locked,
                                        onPressed:
                                            BlePermissionGate().openSettings,
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                  const SizedBox(height: 20),
                  _LinkStatePanel(connection: s.connection),
                  const SizedBox(height: 20),
                  _TemperaturePanel(state: s),
                  const SizedBox(height: 24),
                  // Smoke photo capture button (only during active burn)
                  if (s.burnStartAt != null && proofs.length < 4)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 16),
                      child: RuggedButton(
                        label: [
                          'CAPTURE 0% PROOF (IGNITION)',
                          'CAPTURE 50% PROOF (ACTIVE BURN)',
                          'CAPTURE 90% PROOF (CARBONIZATION)',
                          'CAPTURE 100% PROOF (QUENCHING)',
                        ][proofs.length],
                        onPressed: () => _captureSmoke(proofs.length),
                        variant: RuggedButtonVariant.primary,
                        semanticId: 'capture-smoke-proof-btn-${proofs.length}',
                      ),
                    ),
                  if (proofs.isNotEmpty)
                    ...proofs.map((proof) {
                      final stage =
                          "${proof.captureType.replaceAll('smoke_', '')}%";
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 16),
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 16,
                            vertical: 12,
                          ),
                          decoration: BoxDecoration(
                            color: const Color(
                              0xFF00E676,
                            ).withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Row(
                            children: [
                              const Icon(
                                Icons.check_circle,
                                color: Color(0xFF00E676),
                                size: 24,
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      '$stage SMOKE PROOF CAPTURED',
                                      style: const TextStyle(
                                        fontFamily: 'SpaceGrotesk',
                                        fontSize: 13,
                                        fontWeight: FontWeight.w700,
                                        color: Color(0xFF00E676),
                                      ),
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      'SHA-256: ${proof.sha256Hash.substring(0, 16)}…',
                                      style: TextStyle(
                                        fontFamily: 'SpaceMono',
                                        fontSize: 11,
                                        color: Colors.white.withValues(
                                          alpha: 0.6,
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      );
                    }),
                  if (s.burnStartAt != null)
                    PremiumFieldButton(
                      label: _ending ? 'PERSISTING…' : 'END BURN',
                      testId: 'end-burn-btn',
                      state: (_ending || proofs.length < 4)
                          ? FieldButtonState.locked
                          : FieldButtonState.stop,
                      onPressed: (_ending || proofs.length < 4)
                          ? null
                          : _endBurn,
                    ),
                  const SizedBox(height: 16),
                ],
              ),
            ),
            IntegrityFooter(lastHash: lastHash),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// LINK STATE PANEL
// ---------------------------------------------------------------------------

class _LinkStatePanel extends StatelessWidget {
  const _LinkStatePanel({required this.connection});
  final BleConnState connection;

  @override
  Widget build(BuildContext context) {
    final PremiumChipStatus chipStatus = switch (connection) {
      BleConnState.idle => PremiumChipStatus.locked,
      BleConnState.disconnected => PremiumChipStatus.locked,
      BleConnState.scanning => PremiumChipStatus.pending,
      BleConnState.connecting => PremiumChipStatus.pending,
      BleConnState.connected => PremiumChipStatus.verified,
    };

    final String chipLabel = connection.name.toUpperCase();

    return PremiumFieldPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  'Link State',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
              PremiumStatusChip(label: chipLabel, status: chipStatus),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'BLE ESP32 · Thermocouple 0x1809 (MAX31855)',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: AppTheme.armorSlate.withValues(alpha: 0.65),
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// TEMPERATURE PANEL
// ---------------------------------------------------------------------------

class _TemperaturePanel extends StatelessWidget {
  const _TemperaturePanel({required this.state});
  final PyrolysisState state;

  @override
  Widget build(BuildContext context) {
    final bool streaming = state.connection == BleConnState.connected;
    final Color accent = streaming ? AppTheme.yieldGold : AppTheme.cobaltShield;
    final String reading = state.liveCelsius?.toStringAsFixed(1) ?? '----';

    return PremiumFieldPanel(
      accentBorderColor: streaming ? AppTheme.yieldGold : null,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'LIVE TEMPERATURE (°C)',
            style: TextStyle(
              fontFamily: 'SpaceGrotesk',
              fontSize: 13,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.8,
              color: accent,
            ),
          ),
          const SizedBox(height: 16),
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Flexible(
                child: Semantics(
                  identifier: 'live-temperature-counter',
                  child: Text(
                    reading,
                    style: TextStyle(
                      fontFamily: 'SpaceMono',
                      fontSize: 72,
                      fontWeight: FontWeight.w700,
                      color: accent,
                      height: 1.0,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Text(
                  '°C',
                  style: TextStyle(
                    fontFamily: 'SpaceGrotesk',
                    fontSize: 20,
                    fontWeight: FontWeight.w600,
                    color: AppTheme.armorSlate.withValues(alpha: 0.70),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            'samples logged (1/min): ${state.temperatureLog.length}    '
            'min=${state.temperatureLog.isEmpty ? "-" : state.minTemp.toStringAsFixed(1)}    '
            'max=${state.temperatureLog.isEmpty ? "-" : state.maxTemp.toStringAsFixed(1)}',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: AppTheme.armorSlate.withValues(alpha: 0.70),
            ),
          ),
        ],
      ),
    );
  }
}
