import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:uuid/uuid.dart';

import '../../providers/yield_scale_notifier.dart';
import '../../services/ble_permission_gate.dart';
import '../../services/density_service.dart';
import '../components/dmrv_button.dart';
import '../design/premium_field_components.dart';
import '../design/tokens.dart';

/// Deferred R3 — bulk-density calibration capture (feeds Part 4 F's
/// volume→mass yield fallback with a REAL captured density instead of
/// nothing). Reuses the existing BLE weight-scale stack
/// ([yieldScaleProvider]/[YieldScaleNotifier]) for the mass reading — no new
/// BLE code. Volume is a fixed container measurement the operator enters
/// (the kiln/sample container's known volume in litres). The displayed
/// density is DISPLAY ONLY; the server recomputes and stores the
/// authoritative value on submit (see [DensityService]).
class DensityCalibrationScreen extends ConsumerStatefulWidget {
  const DensityCalibrationScreen({super.key});

  @override
  ConsumerState<DensityCalibrationScreen> createState() =>
      _DensityCalibrationScreenState();
}

class _DensityCalibrationScreenState
    extends ConsumerState<DensityCalibrationScreen> {
  static const _projectId = String.fromEnvironment('DMRV_PROJECT_ID');

  final _volume = TextEditingController();
  bool _permRequested = false;
  String? _permError;
  bool _submitting = false;
  DensityTestResult? _result;

  @override
  void dispose() {
    _volume.dispose();
    super.dispose();
  }

  Future<void> _requestPermsAndConnect() async {
    setState(() => _permRequested = true);
    final result = await BlePermissionGate().ensure();
    if (!result.isGranted) {
      setState(() => _permError = result.detail);
      return;
    }
    setState(() => _permError = null);
    await ref.read(yieldScaleProvider.notifier).begin();
  }

  double? get _volumeL => double.tryParse(_volume.text.trim());

  Future<void> _submit(double massKg) async {
    final volumeL = _volumeL;
    if (volumeL == null || volumeL <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Enter a valid container volume (litres) greater than zero.'),
        ),
      );
      return;
    }
    if (_projectId.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'No project is configured for this device — density test cannot be scoped.',
          ),
        ),
      );
      return;
    }
    setState(() => _submitting = true);
    try {
      final result = await DensityService.submitDensityTest(
        testUuid: const Uuid().v4(),
        projectId: _projectId,
        massKg: massKg,
        volumeL: volumeL,
      );
      if (!mounted) return;
      if (result == null) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Could not submit — check connectivity and try again.'),
          ),
        );
        return;
      }
      setState(() => _result = result);
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final s = ref.watch(yieldScaleProvider);

    return Scaffold(
      backgroundColor: t.surface,
      body: SafeArea(
        bottom: false,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            PremiumScreenHeader(
              stepNumber: 'BD',
              title: 'Bulk-Density Calibration',
              onBack: () => Navigator.of(context).pop(),
            ),
            Expanded(
              child: ListView(
                padding: EdgeInsets.fromLTRB(t.gapL, 4, t.gapL, t.gapL),
                children: [
                  Text(
                    'Weigh a known-volume sample to calibrate wet biochar '
                    'density for the volumetric-mass fallback.',
                    style: t.body.copyWith(color: t.textSecondary),
                  ),
                  SizedBox(height: t.gapL),
                  if (!_permRequested)
                    DmrvButton(
                      label: 'CONNECT WEIGHT SCALE',
                      testId: 'density-connect-scale-btn',
                      variant: DmrvButtonVariant.primary,
                      onPressed: _requestPermsAndConnect,
                    ),
                  if (_permError != null) ...[
                    SizedBox(height: t.gapM),
                    PremiumFieldPanel(
                      accentBorderColor: t.danger,
                      child: Text(
                        _permError!,
                        style: t.body.copyWith(color: t.textPrimary),
                      ),
                    ),
                  ],
                  if (_permRequested && _permError == null) ...[
                    SizedBox(height: t.gapL),
                    Semantics(
                      identifier: 'density-live-mass',
                      child: Text(
                        s.liveKg != null
                            ? 'Live: ${s.liveKg!.toStringAsFixed(3)} kg'
                            : 'Waiting for scale…',
                        style: t.screenTitle.copyWith(color: t.textPrimary),
                      ),
                    ),
                    SizedBox(height: t.gapM),
                    _volumeField(t),
                    if (s.isStabilized) ...[
                      SizedBox(height: t.gapL),
                      _densityPreview(t, s.stableKg!),
                      SizedBox(height: t.gapL),
                      DmrvButton(
                        label: _submitting ? 'SUBMITTING…' : 'SUBMIT DENSITY TEST',
                        testId: 'density-submit-btn',
                        variant: DmrvButtonVariant.primary,
                        onPressed: _submitting
                            ? null
                            : () => _submit(s.stableKg!),
                      ),
                    ],
                  ],
                  if (_result != null) ...[
                    SizedBox(height: t.gapL),
                    Semantics(
                      identifier: 'density-result',
                      child: Text(
                        'Stored density: '
                        '${_result!.densityKgPerL.toStringAsFixed(4)} kg/L',
                        style: t.body.copyWith(color: t.success),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _volumeField(DmrvTokens t) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'CONTAINER VOLUME (LITRES)',
          style: t.chipLabel.copyWith(color: t.accentText),
        ),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          decoration: BoxDecoration(
            color: t.surface,
            borderRadius: BorderRadius.circular(t.radiusM),
            border: Border.all(color: t.border, width: 1),
          ),
          child: Semantics(
            identifier: 'density-volume-input',
            textField: true,
            child: TextField(
              controller: _volume,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              onChanged: (_) => setState(() {}),
              style: t.body.copyWith(color: t.textPrimary),
              decoration: InputDecoration(
                border: InputBorder.none,
                isCollapsed: true,
                contentPadding: const EdgeInsets.symmetric(vertical: 12),
                hintText: 'e.g. 200',
                hintStyle: t.body.copyWith(color: t.textDisabled),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _densityPreview(DmrvTokens t, double massKg) {
    final volumeL = _volumeL;
    final density = volumeL != null
        ? displayDensityKgPerL(massKg: massKg, volumeL: volumeL)
        : null;
    return PremiumFieldPanel(
      accentBorderColor: t.accent,
      child: Semantics(
        identifier: 'density-preview',
        child: Text(
          density != null
              ? 'Estimated density: ${density.toStringAsFixed(4)} kg/L '
                  '(server confirms on submit)'
              : 'Enter the container volume to see an estimated density.',
          style: t.body.copyWith(color: t.textPrimary),
        ),
      ),
    );
  }
}
