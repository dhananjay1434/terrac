import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/local/database_provider.dart';
import '../../data/local/pyrolysis_writer.dart';
import '../../providers/batch_session_notifier.dart';
import '../../providers/dashboard_provider.dart';
import '../../providers/pyrolysis_ble_notifier.dart';
import '../../services/ble_permission_gate.dart';
import '../../services/ble_temperature_service.dart';
import '../components/dmrv_button.dart';
import '../design/premium_field_components.dart';
import '../design/tokens.dart';
import '../widgets/integrity_footer.dart';
import '../../data/capture_types.dart';
import '../../services/secure_capture_service.dart';
import '../../providers/smoke_evidence_provider.dart';
import 'kiln_select_screen.dart';
import 'secure_camera_screen.dart';
import 'yield_scale_screen.dart';

/// The 4 smoke-opacity proofs every burn documents.
const kSmokeStages = {'smoke_0', 'smoke_50', 'smoke_90', 'smoke_100'};

/// The 3 extra Rainbow C3 stage photos an OPEN kiln must also carry.
const kOpenFlameStages = {'flame_curtain', 'quenching', 'flame_height'};

/// P1-C5 + P1-S4: END BURN gating, kiln-type aware and pure so it's unit-tested
/// without the burn widget harness. Every kiln needs the 4 smoke proofs. An
/// OPEN kiln additionally needs the 3 flame-stage photos and a recorded flame
/// height (the server grades the <0.5 m rule; we only require it be entered). A
/// CLOSED kiln instead needs a declared ignition-energy type.
bool canEndBurn({
  required bool ending,
  required bool isOpenKiln,
  required Set<String> capturedStages,
  required double? flameHeightM,
  required String? ignitionEnergyType,
}) {
  if (ending) return false;
  
  if (isOpenKiln) {
    if (!kOpenFlameStages.every(capturedStages.contains)) return false;
    if (flameHeightM == null) return false;
  } else {
    if (!kSmokeStages.every(capturedStages.contains)) return false;
    if (ignitionEnergyType == null || ignitionEnergyType.trim().isEmpty) {
      return false;
    }
  }
  return true;
}

/// =============================================================================
/// PyrolysisScreen — India paper skin (tokens + Dmrv components)
/// =============================================================================
class PyrolysisScreen extends ConsumerStatefulWidget {
  const PyrolysisScreen({super.key});
  @override
  ConsumerState<PyrolysisScreen> createState() => _PyrolysisScreenState();
}

class _PyrolysisScreenState extends ConsumerState<PyrolysisScreen> {
  bool _permRequested = false;
  String? _permError;
  bool _ending = false;

  // P1-S4 completion evidence (open kiln: flame height; closed kiln: ignition).
  final _flameHeightCtrl = TextEditingController();
  final _ignitionAmountCtrl = TextEditingController();
  String? _ignitionType;
  static const _ignitionTypes = <String, String>{
    'LPG': 'LPG',
    'WOOD_KINDLING': 'Wood kindling',
    'ELECTRIC': 'Electric',
    'SYNGAS': 'Syngas',
  };

  @override
  void dispose() {
    _flameHeightCtrl.dispose();
    _ignitionAmountCtrl.dispose();
    super.dispose();
  }

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
      final kiln = ref.read(selectedKilnProvider);
      if (kiln == null) {
        throw StateError('No kiln selected. Go back and choose a kiln.');
      }
      final capacity = kiln.capacityLitres;
      if (capacity == null) {
        throw StateError('Selected kiln has no capacity recorded.');
      }
      final final_ = await ref.read(pyrolysisBleProvider.notifier).endBurn();
      if (final_.temperatureLog.isEmpty) {
        throw StateError('No temperature samples captured. Cannot persist.');
      }

      final isOpen = kiln.kilnType == 'open';
      final db = await ref.read(appDatabaseProvider.future);
      final telemetryUuid = await db.insertPyrolysisTelemetryWithOutbox(
        batchUuid: batchUuid,
        kilnGrossCapacity: capacity,
        kilnId: kiln.kilnId,
        kilnType: kiln.kilnType,
        burnStart: final_.burnStartAt!,
        burnEnd: final_.burnEndAt!,
        temperatureReadings: final_.temperatureLog,
        flameHeightM: isOpen
            ? double.tryParse(_flameHeightCtrl.text.trim())
            : null,
        ignitionEnergyType: isOpen ? null : _ignitionType,
        ignitionEnergyAmount: isOpen
            ? null
            : double.tryParse(_ignitionAmountCtrl.text.trim()),
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
        final msg = e.toString().contains('smoke captures')
            ? 'Capture all 4 smoke-stage photos before ending the burn.'
            : e.toString().contains('No temperature')
            ? 'No thermocouple readings yet — connect and record before ending.'
            : 'Could not save the burn. Your data is safe on the device; '
                  'tap END BURN to try again.';
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(msg)));
      }
    } finally {
      if (mounted) setState(() => _ending = false);
    }
  }

  bool _isCapturingSmoke = false;

  Future<void> _captureSmoke(int currentProofsLength) async {
    if (currentProofsLength >= 4) return;
    await _captureStage(
      const [
        'smoke_0',
        'smoke_50',
        'smoke_90',
        'smoke_100',
      ][currentProofsLength],
    );
  }

  /// Photograph one evidence stage and persist it as a `mediaCaptures` row with
  /// the given [captureType] (also enqueued for /media sync). Used by both the
  /// smoke proofs and the P1-S4 flame-stage photos.
  Future<void> _captureStage(String captureType) async {
    if (_isCapturingSmoke) return;
    setState(() => _isCapturingSmoke = true);
    try {
      final result = await Navigator.of(context).push<SecureCaptureResult>(
        MaterialPageRoute(builder: (_) => const SecureCameraScreen()),
      );
      if (result != null && mounted) {
        final batchUuid = ref.read(batchSessionProvider);
        if (batchUuid == null) return;
        final db = await ref.read(appDatabaseProvider.future);
        await db.insertMediaCaptureAndEnqueue(
          batchUuid: batchUuid,
          captureType: captureType,
          sandboxPath: result.sandboxPath,
          sha256Hash: result.sha256Hash,
          isMockLocation: result.isMocked,
        );
      }
    } finally {
      if (mounted) setState(() => _isCapturingSmoke = false);
    }
  }

  bool _isCapturingQuenchVideo = false;
  bool _quenchVideoCaptured = false;

  /// V8 Part 4 (O) — optional short video of the quench (in addition to,
  /// never instead of, the required `quenching` still — this does not touch
  /// `canEndBurn`'s gating set).
  Future<void> _captureQuenchVideo() async {
    if (_isCapturingQuenchVideo) return;
    setState(() => _isCapturingQuenchVideo = true);
    try {
      final result = await Navigator.of(
        context,
      ).push<SecureVideoCaptureResult>(
        MaterialPageRoute(
          builder: (_) =>
              const SecureCameraScreen(captureMode: SecureCaptureMode.video),
        ),
      );
      if (result != null && mounted) {
        final batchUuid = ref.read(batchSessionProvider);
        if (batchUuid == null) return;
        final db = await ref.read(appDatabaseProvider.future);
        await db.insertMediaCaptureAndEnqueue(
          batchUuid: batchUuid,
          captureType: CaptureType.quenchingVideo,
          sandboxPath: result.sandboxPath,
          sha256Hash: result.sha256Hash,
          isMockLocation: result.isMocked,
        );
        if (mounted) setState(() => _quenchVideoCaptured = true);
      }
    } finally {
      if (mounted) setState(() => _isCapturingQuenchVideo = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final s = ref.watch(pyrolysisBleProvider);
    final lastHash = ref.watch(dashboardProvider).lastHash;
    final proofsAsync = ref.watch(smokeEvidenceProvider);
    final proofs = proofsAsync.valueOrNull ?? [];
    final kiln = ref.watch(selectedKilnProvider);
    final isOpenKiln = kiln?.kilnType == 'open';
    final captured = ref.watch(capturedStagesProvider).valueOrNull ?? <String>{};

    return Scaffold(
      backgroundColor: t.surface,
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
                padding: EdgeInsets.fromLTRB(t.gapL, 4, t.gapL, t.gapL),
                children: [
                  if (!_permRequested)
                    DmrvButton(
                      label: 'CONNECT ESP32 THERMOCOUPLE',
                      testId: 'connect-esp32-thermocouple-btn',
                      variant: DmrvButtonVariant.primary,
                      onPressed: _requestPermsAndStart,
                    ),
                  if (kDebugMode)
                    Padding(
                      padding: const EdgeInsets.only(top: 16.0),
                      child: DmrvButton(
                        label: 'DEV BYPASS // INJECT TEMP',
                        testId: 'dev-bypass-temp-btn',
                        variant: DmrvButtonVariant.danger,
                        onPressed: () async {
                          if (s.burnStartAt == null) {
                             await ref.read(pyrolysisBleProvider.notifier).beginBurn();
                          }
                          ref.read(pyrolysisBleProvider.notifier).debugIngest(400.0);
                        },
                      ),
                    ),
                  if (_permError != null) ...[
                    SizedBox(height: t.gapL),
                    PremiumFieldPanel(
                      accentBorderColor: t.danger,
                      padding: EdgeInsets.all(t.gapL),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Icon(Icons.error_outline, color: t.danger, size: 28),
                          SizedBox(width: t.gapM),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'BLE PERMISSIONS REQUIRED',
                                  style: t.chipLabel.copyWith(color: t.danger),
                                ),
                                SizedBox(height: t.gapS),
                                Text(
                                  _permError!,
                                  style: t.metadata.copyWith(
                                    color: t.textPrimary,
                                  ),
                                ),
                                SizedBox(height: t.gapM),
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
                                    SizedBox(width: t.gapM),
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
                  SizedBox(height: t.gapL),
                  _LinkStatePanel(connection: s.connection),
                  // P1-C4: surface a dropped thermocouple link during a burn so
                  // the operator acts instead of silently losing telemetry.
                  if (s.connectionLost || s.bleError != null) ...[
                    SizedBox(height: t.gapL),
                    PremiumFieldPanel(
                      accentBorderColor: t.danger,
                      padding: EdgeInsets.all(t.gapL),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Icon(
                            Icons.bluetooth_disabled,
                            color: t.danger,
                            size: 28,
                          ),
                          SizedBox(width: t.gapM),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'THERMOCOUPLE LINK LOST',
                                  style: t.chipLabel.copyWith(color: t.danger),
                                ),
                                SizedBox(height: t.gapS),
                                Text(
                                  s.bleError ??
                                      'No readings for 30s. Move closer to the '
                                          'kiln — recording resumes automatically.',
                                  style: t.metadata.copyWith(
                                    color: t.textPrimary,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                  SizedBox(height: t.gapL),
                  _TemperaturePanel(state: s),
                  SizedBox(height: t.gapXL),
                  // Smoke photo capture button (only during active burn)
                  if (s.burnStartAt != null && !isOpenKiln && proofs.length < 4)
                    Padding(
                      padding: EdgeInsets.only(bottom: t.gapL),
                      child: DmrvButton(
                        label: [
                          'CAPTURE 0% PROOF (IGNITION)',
                          'CAPTURE 50% PROOF (ACTIVE BURN)',
                          'CAPTURE 90% PROOF (CARBONIZATION)',
                          'CAPTURE 100% PROOF (QUENCHING)',
                        ][proofs.length],
                        onPressed: () => _captureSmoke(proofs.length),
                        variant: DmrvButtonVariant.primary,
                        testId: 'capture-smoke-proof-btn-${proofs.length}',
                      ),
                    ),
                  if (proofs.isNotEmpty)
                    ...proofs.map((proof) {
                      final stage =
                          "${proof.captureType.replaceAll('smoke_', '')}%";
                      return Padding(
                        padding: EdgeInsets.only(bottom: t.gapL),
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 16,
                            vertical: 12,
                          ),
                          decoration: BoxDecoration(
                            color: t.success.withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(t.radiusS),
                            border: Border.all(
                              color: t.success.withValues(alpha: 0.4),
                              width: 1,
                            ),
                          ),
                          child: Row(
                            children: [
                              Icon(
                                Icons.check_circle,
                                color: t.success,
                                size: 24,
                              ),
                              SizedBox(width: t.gapM),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      '$stage SMOKE PROOF CAPTURED',
                                      style: t.chipLabel.copyWith(
                                        color: t.success,
                                      ),
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      'SHA-256: ${proof.sha256Hash.substring(0, 16)}…',
                                      style: t.metadata.copyWith(
                                        fontSize: 11,
                                        color: t.textSecondary,
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
                  // P1-S4: kiln-type-specific completion evidence, once the
                  // burn is live and the 4 smoke proofs are in (for closed kilns).
                  if (s.burnStartAt != null &&
                      kiln != null &&
                      (isOpenKiln || proofs.length >= 4)) ...[
                    _completionSection(t, isOpenKiln, captured),
                    SizedBox(height: t.gapL),
                  ],
                  if (s.burnStartAt != null)
                    DmrvButton(
                      label: _ending ? 'PERSISTING…' : 'END BURN',
                      testId: 'end-burn-btn',
                      variant: DmrvButtonVariant.danger,
                      onPressed:
                          canEndBurn(
                            ending: _ending,
                            isOpenKiln: isOpenKiln,
                            capturedStages: captured,
                            flameHeightM: double.tryParse(
                              _flameHeightCtrl.text.trim(),
                            ),
                            ignitionEnergyType: _ignitionType,
                          )
                          ? _endBurn
                          : null,
                    ),
                  SizedBox(height: t.gapL),
                ],
              ),
            ),
            IntegrityFooter(lastHash: lastHash),
          ],
        ),
      ),
    );
  }

  // ===========================================================================
  // P1-S4 completion evidence
  // ===========================================================================

  Widget _completionSection(
    DmrvTokens t,
    bool isOpenKiln,
    Set<String> captured,
  ) {
    return PremiumFieldPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            isOpenKiln ? 'OPEN-KILN COMPLETION' : 'CLOSED-KILN IGNITION',
            style: t.chipLabel.copyWith(color: t.accentText),
          ),
          SizedBox(height: t.gapM),
          if (isOpenKiln) ...[
            // V8 Part 4 (J): stage-labeled prompts — each capture names WHEN
            // in the burn to shoot and what must be visible, instead of a
            // bare "photo" label.
            _stageCaptureRow(
              t,
              'flame_curtain',
              'Flame curtain photo',
              'Shoot when the flame curtain covers the kiln mouth — mid-burn, kiln ID visible.',
              captured,
            ),
            SizedBox(height: t.gapM),
            _stageCaptureRow(
              t,
              'quenching',
              'Quenching photo',
              'Shoot the moment water/soil is applied to quench — ~100% of run, kiln ID visible.',
              captured,
            ),
            SizedBox(height: t.gapS),
            // V8 Part 4 (O) — optional quench video, additive evidence only;
            // does not gate `canEndBurn`.
            DmrvButton(
              label: _quenchVideoCaptured
                  ? '✓ QUENCH VIDEO RECORDED'
                  : '+ RECORD QUENCH VIDEO (OPTIONAL)',
              testId: 'capture-quenching-video-btn',
              icon: _quenchVideoCaptured ? Icons.check_circle : Icons.videocam,
              variant: _quenchVideoCaptured
                  ? DmrvButtonVariant.success
                  : DmrvButtonVariant.neutral,
              onPressed: _captureQuenchVideo,
            ),
            SizedBox(height: t.gapM),
            _stageCaptureRow(
              t,
              'flame_height',
              'Flame-height photo',
              'Shoot the flame alongside a height marker for scale — used for the reading below.',
              captured,
            ),
            SizedBox(height: t.gapM),
            _numericField(
              t,
              'FLAME HEIGHT (m)',
              _flameHeightCtrl,
              'flame-height-input',
              'e.g. 0.30',
            ),
          ] else ...[
            Text(
              'KILN IGNITION ENERGY',
              style: t.chipLabel.copyWith(color: t.textSecondary),
            ),
            SizedBox(height: t.gapS),
            Wrap(
              spacing: t.gapS,
              runSpacing: t.gapS,
              children: [
                for (final e in _ignitionTypes.entries)
                  Semantics(
                    identifier: 'ignition-${e.key}',
                    button: true,
                    selected: _ignitionType == e.key,
                    child: ChoiceChip(
                      label: Text(e.value),
                      selected: _ignitionType == e.key,
                      onSelected: (_) => setState(() => _ignitionType = e.key),
                    ),
                  ),
              ],
            ),
            SizedBox(height: t.gapM),
            _numericField(
              t,
              'IGNITION AMOUNT (optional)',
              _ignitionAmountCtrl,
              'ignition-amount-input',
              'e.g. 2.0',
            ),
          ],
        ],
      ),
    );
  }

  Widget _stageCaptureRow(
    DmrvTokens t,
    String stage,
    String label,
    String hint,
    Set<String> captured,
  ) {
    final done = captured.contains(stage);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        DmrvButton(
          label: done ? '✓ ${label.toUpperCase()}' : 'CAPTURE ${label.toUpperCase()}',
          testId: 'capture-$stage-btn',
          icon: done ? Icons.check_circle : Icons.camera_alt,
          variant: done ? DmrvButtonVariant.success : DmrvButtonVariant.neutral,
          onPressed: () => _captureStage(stage),
        ),
        if (!done) ...[
          const SizedBox(height: 4),
          Semantics(
            identifier: 'capture-$stage-hint',
            child: Text(
              hint,
              style: t.metadata.copyWith(color: t.textSecondary),
            ),
          ),
        ],
      ],
    );
  }

  Widget _numericField(
    DmrvTokens t,
    String label,
    TextEditingController controller,
    String testId,
    String hint,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: t.chipLabel.copyWith(color: t.textSecondary)),
        const SizedBox(height: 6),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          decoration: BoxDecoration(
            color: t.surface,
            borderRadius: BorderRadius.circular(t.radiusM),
            border: Border.all(color: t.border, width: 1),
          ),
          child: Semantics(
            identifier: testId,
            textField: true,
            child: TextField(
              controller: controller,
              keyboardType: const TextInputType.numberWithOptions(
                decimal: true,
              ),
              inputFormatters: [
                FilteringTextInputFormatter.allow(RegExp(r'[0-9.]')),
              ],
              cursorColor: t.accentText,
              style: t.body.copyWith(color: t.textPrimary),
              onChanged: (_) => setState(() {}),
              decoration: InputDecoration(
                border: InputBorder.none,
                isCollapsed: true,
                contentPadding: const EdgeInsets.symmetric(vertical: 10),
                hintText: hint,
                hintStyle: t.body.copyWith(color: t.textDisabled),
              ),
            ),
          ),
        ),
      ],
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
    final t = context.tokens;
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
          SizedBox(height: t.gapS),
          Text(
            'BLE ESP32 · Thermocouple 0x1809 (MAX31855)',
            style: t.metadata.copyWith(color: t.textSecondary),
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
    final t = context.tokens;
    final bool streaming = state.connection == BleConnState.connected;
    // Heat is orange: a live reading glows in the accent; idle is muted.
    final Color accent = streaming ? t.accent : t.textDisabled;
    final String reading = state.liveCelsius?.toStringAsFixed(1) ?? '----';

    return PremiumFieldPanel(
      accentBorderColor: streaming ? t.accent : null,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'LIVE TEMPERATURE (°C)',
            style: t.chipLabel.copyWith(
              color: streaming ? t.accentText : t.textSecondary,
            ),
          ),
          SizedBox(height: t.gapL),
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Flexible(
                child: Semantics(
                  identifier: 'live-temperature-counter',
                  child: Text(
                    reading,
                    style: t.numericHero.copyWith(fontSize: 72, color: accent),
                  ),
                ),
              ),
              SizedBox(width: t.gapM),
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: Text(
                  '°C',
                  style: t.blockHeader.copyWith(color: t.textSecondary),
                ),
              ),
            ],
          ),
          SizedBox(height: t.gapM),
          Text(
            'samples logged (1/min): ${state.temperatureLog.length}    '
            'min=${state.temperatureLog.isEmpty ? "-" : state.minTemp.toStringAsFixed(1)}    '
            'max=${state.temperatureLog.isEmpty ? "-" : state.maxTemp.toStringAsFixed(1)}',
            style: t.metadata.copyWith(color: t.textSecondary),
          ),
        ],
      ),
    );
  }
}
