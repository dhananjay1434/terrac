import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/local/database_provider.dart';
import '../../data/local/yield_end_use_writers.dart';
import '../../providers/batch_session_notifier.dart';
import '../../providers/dashboard_provider.dart';
import '../../providers/yield_scale_notifier.dart';
import '../../services/ble_permission_gate.dart';
import '../../services/ble_weight_scale_service.dart';
import '../components/dmrv_button.dart';
import '../design/premium_field_components.dart';
import '../design/tokens.dart';
import '../widgets/integrity_footer.dart';
import 'package:dmrv_app/l10n/app_localizations.dart';
import 'end_use_application_screen.dart';

/// =============================================================================
/// YieldScaleScreen — India paper skin (tokens + Dmrv components)
/// =============================================================================
/// Operator flow:
///   1. CONNECT CRANE SCALE → BLE permissions → scan/connect 0x181D.
///   2. Live kg counter updates from the SIG Weight Measurement parser.
///   3. 5-reading circular buffer accumulates → when variance < 50 g the
///      "STABILIZED" badge lights up and the LOCK YIELD button enables.
///   4. LOCK YIELD confirms the stable kg into [state.confirmedKg].
///   5. SAVE YIELD writes a `YieldMetrics` + outbox row atomically and
///      navigates to the EndUseApplicationScreen.
/// =============================================================================
class YieldScaleScreen extends ConsumerStatefulWidget {
  const YieldScaleScreen({super.key});

  @override
  ConsumerState<YieldScaleScreen> createState() => _YieldScaleScreenState();
}

class _YieldScaleScreenState extends ConsumerState<YieldScaleScreen> {
  bool _permRequested = false;
  String? _permError;
  bool _saving = false;

  Future<void> _requestPermsAndStart() async {
    setState(() => _permRequested = true);
    final result = await BlePermissionGate().ensure();
    if (!result.isGranted) {
      setState(() => _permError = result.detail);
      return;
    }
    setState(() => _permError = null);
    await ref.read(yieldScaleProvider.notifier).begin();
  }

  Future<void> _saveYield() async {
    if (_saving) return;
    setState(() => _saving = true);
    try {
      final batchUuid = ref.read(batchSessionProvider);
      if (batchUuid == null) {
        throw StateError('No active batch.');
      }
      final s = ref.read(yieldScaleProvider);
      final kg = s.confirmedKg;
      if (kg == null) throw StateError('Lock the yield reading first.');

      final db = await ref.read(appDatabaseProvider.future);
      final yieldUuid = await db.insertYieldMetricsWithOutbox(
        batchUuid: batchUuid,
        quenchMethodology: 'WATER_QUENCH',
        grossVolume: 200.0, // default 200L kiln gross volume (placeholder)
        wetYieldWeightKg: kg,
      );
      ref.read(dashboardProvider.notifier).markYieldVerified();
      debugPrint(
        '[YieldScale] insertYieldMetricsWithOutbox OK — uuid=$yieldUuid kg=$kg',
      );

      await ref.read(yieldScaleProvider.notifier).finish();
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute<void>(
          builder: (_) => const EndUseApplicationScreen(),
        ),
      );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Save failed: $e')));
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  ({String label, PremiumChipStatus status}) _chipFor(BleScaleState s) {
    switch (s) {
      case BleScaleState.idle:
        return (label: 'IDLE', status: PremiumChipStatus.locked);
      case BleScaleState.scanning:
        return (label: 'SCANNING', status: PremiumChipStatus.pending);
      case BleScaleState.connecting:
        return (label: 'CONNECTING', status: PremiumChipStatus.pending);
      case BleScaleState.connected:
        return (label: 'CONNECTED', status: PremiumChipStatus.verified);
      case BleScaleState.disconnected:
        return (label: 'DISCONNECTED', status: PremiumChipStatus.error);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    ref.listen<YieldScaleState>(yieldScaleProvider, (prev, next) {
      if (prev != null && !prev.isStabilized && next.isStabilized) {
        HapticFeedback.heavyImpact();
      }
    });

    final s = ref.watch(yieldScaleProvider);
    final String footerHash = s.confirmedKg != null
        ? 'yield-locked@${s.confirmedKg!.toStringAsFixed(3)}kg'
        : '----------------------------------------------------------------';

    // Subtle "locked-in" pulse derived from tokens: a faint success tint over
    // the paper surface when the reading stabilizes, else the plain surface.
    final Color bgColor = (s.isStabilized && !s.isConfirmed)
        ? Color.alphaBlend(t.success.withValues(alpha: 0.10), t.surface)
        : t.surface;

    return Scaffold(
      backgroundColor: bgColor,
      body: AnimatedContainer(
        duration: const Duration(milliseconds: 400),
        color: bgColor,
        child: SafeArea(
          bottom: false,
          child: Column(
            children: [
              PremiumScreenHeader(
                stepNumber: '04',
                title: 'Yield · Crane Scale',
                onBack: () => Navigator.of(context).pop(),
              ),
              Expanded(
                child: ListView(
                  padding: EdgeInsets.fromLTRB(t.gapL, 4, t.gapL, t.gapL),
                  children: [
                    if (!_permRequested)
                      DmrvButton(
                        key: const Key('connect-crane-scale-btn'),
                        label: AppLocalizations.of(
                          context,
                        )!.connect_crane_scale,
                        variant: DmrvButtonVariant.primary,
                        testId: 'connect-crane-scale-btn',
                        onPressed: _requestPermsAndStart,
                      ),
                    if (_permError != null) ...[
                      SizedBox(height: t.gapL),
                      Container(
                        padding: EdgeInsets.all(t.gapL),
                        decoration: BoxDecoration(
                          color: t.dangerSurface,
                          borderRadius: BorderRadius.circular(t.radiusM),
                          border: Border.all(color: t.danger, width: 2),
                        ),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Icon(
                              Icons.error_outline,
                              color: t.danger,
                              size: 28,
                            ),
                            SizedBox(width: t.gapM),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'BLE PERMISSION DENIED',
                                    style: t.chipLabel.copyWith(
                                      color: t.danger,
                                    ),
                                  ),
                                  SizedBox(height: t.gapS),
                                  Text(
                                    _permError!,
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
                    _LinkStatePanel(
                      connection: s.connection,
                      chip: _chipFor(s.connection),
                    ),
                    SizedBox(height: t.gapL),
                    _HeroReadout(state: s),
                    SizedBox(height: t.gapXL),
                    if (!s.isConfirmed)
                      DmrvButton(
                        key: const Key('lock-yield-btn'),
                        label: s.isStabilized
                            ? 'LOCK YIELD @ ${s.stableKg!.toStringAsFixed(3)} kg'
                            : AppLocalizations.of(context)!.stabilize_reading,
                        variant: DmrvButtonVariant.success,
                        testId: 'lock-yield-btn',
                        onPressed: s.isStabilized
                            ? () => ref
                                  .read(yieldScaleProvider.notifier)
                                  .confirm()
                            : null,
                      )
                    else
                      DmrvButton(
                        key: const Key('save-yield-btn'),
                        label: _saving ? 'PERSISTING…' : 'SAVE YIELD → END USE',
                        variant: DmrvButtonVariant.primary,
                        testId: 'save-yield-btn',
                        onPressed: _saving ? null : _saveYield,
                      ),
                    SizedBox(height: t.gapL),
                  ],
                ),
              ),
              IntegrityFooter(lastHash: footerHash),
            ],
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// LINK STATE PANEL
// ---------------------------------------------------------------------------

class _LinkStatePanel extends StatelessWidget {
  const _LinkStatePanel({required this.connection, required this.chip});
  final BleScaleState connection;
  final ({String label, PremiumChipStatus status}) chip;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    return Container(
      padding: EdgeInsets.all(t.gapL),
      decoration: BoxDecoration(
        color: t.surfaceRaised,
        borderRadius: BorderRadius.circular(t.radiusM),
        border: Border.all(color: t.border, width: 1.5),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  'Link State',
                  style: t.blockHeader.copyWith(color: t.textPrimary),
                ),
              ),
              PremiumStatusChip(label: chip.label, status: chip.status),
            ],
          ),
          SizedBox(height: t.gapS),
          Text(
            'BLE 0x181D · Weight Measurement (SIG)',
            style: t.metadata.copyWith(color: t.textSecondary),
          ),
          const SizedBox(height: 4),
          Text(
            connection.name.toUpperCase(),
            style: t.metadata.copyWith(
              color: t.accentText,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.8,
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// HERO READOUT — centered column with giant kg counter
// ---------------------------------------------------------------------------

class _HeroReadout extends StatelessWidget {
  const _HeroReadout({required this.state});
  final YieldScaleState state;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final bool stable = state.isStabilized;
    final String reading = state.liveKg?.toStringAsFixed(3) ?? '----';
    final Color readingColor = stable ? t.success : t.textPrimary;

    return Container(
      padding: const EdgeInsets.symmetric(vertical: 32, horizontal: 20),
      decoration: BoxDecoration(
        color: t.surfaceRaised,
        borderRadius: BorderRadius.circular(t.radiusM),
        border: Border.all(
          color: stable ? t.success : t.border,
          width: stable ? 2 : 1.5,
        ),
      ),
      child: Column(
        children: [
          Semantics(
            label: 'live-weight-counter',
            child: Text(
              reading,
              textAlign: TextAlign.center,
              style: t.numericHero.copyWith(fontSize: 96, color: readingColor),
            ),
          ),
          const SizedBox(height: 4),
          Text('kg', style: t.blockHeader.copyWith(color: t.textSecondary)),
          if (stable) ...[
            SizedBox(height: t.gapL),
            Semantics(
              label: 'yield-stabilized-badge',
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.check_circle, color: t.success, size: 20),
                  SizedBox(width: t.gapS),
                  Text(
                    AppLocalizations.of(context)!.stabilized,
                    style: t.blockHeader.copyWith(color: t.success),
                  ),
                ],
              ),
            ),
          ],
          SizedBox(height: t.gapXL),
          Text(
            'VARIANCE: ${state.variance.toStringAsFixed(3)}',
            style: t.metadata.copyWith(color: t.textSecondary),
          ),
          SizedBox(height: t.gapS),
          Text(
            'BUFFER: ${state.window.length}/$kStabilizationBufferSize',
            style: t.metadata.copyWith(color: t.textSecondary),
          ),
        ],
      ),
    );
  }
}
