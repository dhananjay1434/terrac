import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../services/sync_queue_manager.dart';

import '../../data/local/database_provider.dart';
import '../../data/local/yield_end_use_writers.dart';
import '../../providers/batch_session_notifier.dart';
import '../../providers/dashboard_provider.dart';
import '../../providers/yield_scale_notifier.dart';
import '../../services/ble_permission_gate.dart';
import '../../services/ble_weight_scale_service.dart';
import '../design/farmer_theme.dart';
import '../design/premium_field_components.dart';
import '../widgets/integrity_footer.dart';
import '../widgets/rugged_button.dart';
import 'package:dmrv_app/l10n/app_localizations.dart';
import 'end_use_application_screen.dart';

/// =============================================================================
/// YieldScaleScreen  (Prompt 5 — Task 1 — Yield)
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

  // ---------------------------------------------------------------------------
  // PremiumStatusChip mapping for the BLE connection state machine. We do NOT
  // mutate the state machine itself — only its visual surface.
  // ---------------------------------------------------------------------------
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
    // Set up haptic lock-in listener for stabilization transition
    ref.listen<YieldScaleState>(yieldScaleProvider, (prev, next) {
      if (prev != null && !prev.isStabilized && next.isStabilized) {
        HapticFeedback.heavyImpact();
      }
    });

    final s = ref.watch(yieldScaleProvider);
    final String footerHash = s.confirmedKg != null
        ? 'yield-locked@${s.confirmedKg!.toStringAsFixed(3)}kg'
        : '----------------------------------------------------------------';

    // Background color animation: deepSlate → fieldGreen when stabilized
    final Color bgColor = (s.isStabilized && !s.isConfirmed)
        ? FarmerTheme.fieldGreen
        : FarmerTheme.deepSlate;

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
                  padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
                  children: [
                    if (!_permRequested)
                      RuggedButton(
                        key: const Key('connect-crane-scale-btn'),
                        label: AppLocalizations.of(
                          context,
                        )!.connect_crane_scale,
                        variant: RuggedButtonVariant.primary,
                        semanticId: 'connect-crane-scale-btn',
                        onPressed: _requestPermsAndStart,
                      ),
                    if (_permError != null) ...[
                      const SizedBox(height: 16),
                      Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: FarmerTheme.crimsonRed15,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                            color: FarmerTheme.crimsonRed,
                            width: 2,
                          ),
                        ),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Icon(
                              Icons.error_outline,
                              color: FarmerTheme.crimsonRed,
                              size: 28,
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'BLE PERMISSION DENIED',
                                    style: TextStyle(
                                      fontFamily: 'SpaceGrotesk',
                                      fontSize: 14,
                                      fontWeight: FontWeight.w700,
                                      letterSpacing: 0.6,
                                      color: FarmerTheme.crimsonRed,
                                    ),
                                  ),
                                  const SizedBox(height: 6),
                                  Text(
                                    _permError!,
                                    style: TextStyle(
                                      fontFamily: 'SpaceMono',
                                      fontSize: 13,
                                      fontWeight: FontWeight.w400,
                                      color: FarmerTheme.fogWhite,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                    const SizedBox(height: 20),
                    _LinkStatePanel(
                      connection: s.connection,
                      chip: _chipFor(s.connection),
                    ),
                    const SizedBox(height: 20),
                    _HeroReadout(state: s),
                    const SizedBox(height: 24),
                    if (!s.isConfirmed)
                      RuggedButton(
                        key: const Key('lock-yield-btn'),
                        label: s.isStabilized
                            ? 'LOCK YIELD @ ${s.stableKg!.toStringAsFixed(3)} kg'
                            : AppLocalizations.of(context)!.stabilize_reading,
                        variant: s.isStabilized
                            ? RuggedButtonVariant.success
                            : RuggedButtonVariant.disabled,
                        semanticId: 'lock-yield-btn',
                        onPressed: s.isStabilized
                            ? () => ref
                                  .read(yieldScaleProvider.notifier)
                                  .confirm()
                            : null,
                      )
                    else
                      RuggedButton(
                        key: const Key('save-yield-btn'),
                        label: _saving ? 'PERSISTING…' : 'SAVE YIELD → END USE',
                        variant: _saving
                            ? RuggedButtonVariant.disabled
                            : RuggedButtonVariant.primary,
                        semanticId: 'save-yield-btn',
                        onPressed: _saving ? null : _saveYield,
                      ),
                    const SizedBox(height: 16),
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
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: FarmerTheme.panelSlate,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: FarmerTheme.fogWhite20, width: 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  'Link State',
                  style: TextStyle(
                    fontFamily: 'SpaceGrotesk',
                    fontSize: 20,
                    fontWeight: FontWeight.w600,
                    color: FarmerTheme.pureAlbedo,
                  ),
                ),
              ),
              PremiumStatusChip(label: chip.label, status: chip.status),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'BLE 0x181D · Weight Measurement (SIG)',
            style: TextStyle(
              fontFamily: 'SpaceMono',
              fontSize: 14,
              fontWeight: FontWeight.w400,
              color: FarmerTheme.fogWhite65,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            connection.name.toUpperCase(),
            style: TextStyle(
              fontFamily: 'SpaceMono',
              fontSize: 14,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.8,
              color: FarmerTheme.neonYellow,
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
    final bool stable = state.isStabilized;
    final String reading = state.liveKg?.toStringAsFixed(3) ?? '----';
    final Color readingColor = stable
        ? FarmerTheme.neonYellow
        : FarmerTheme.pureAlbedo;

    return Container(
      padding: const EdgeInsets.symmetric(vertical: 32, horizontal: 20),
      decoration: BoxDecoration(
        color: FarmerTheme.panelSlate,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: stable ? FarmerTheme.fieldGreen : FarmerTheme.fogWhite20,
          width: stable ? 2 : 1,
        ),
      ),
      child: Column(
        children: [
          // Giant kg readout
          Semantics(
            label: 'live-weight-counter',
            child: Text(
              reading,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontFamily: 'SpaceMono',
                fontSize: 96,
                fontWeight: FontWeight.w700,
                color: readingColor,
                height: 1.0,
              ),
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'kg',
            style: TextStyle(
              fontFamily: 'SpaceGrotesk',
              fontSize: 24,
              fontWeight: FontWeight.w600,
              color: FarmerTheme.fogWhite70,
            ),
          ),
          if (stable) ...[
            const SizedBox(height: 16),
            Semantics(
              label: 'yield-stabilized-badge',
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    Icons.check_circle,
                    color: FarmerTheme.fieldGreen,
                    size: 20,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    AppLocalizations.of(context)!.stabilized,
                    style: TextStyle(
                      fontFamily: 'SpaceGrotesk',
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                      color: FarmerTheme.fieldGreen,
                    ),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: 24),
          // Variance and buffer stats
          Text(
            'VARIANCE: ${state.variance.toStringAsFixed(3)}',
            style: TextStyle(
              fontFamily: 'SpaceMono',
              fontSize: 14,
              fontWeight: FontWeight.w400,
              color: FarmerTheme.fogWhite60,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'BUFFER: ${state.window.length}/$kStabilizationBufferSize',
            style: TextStyle(
              fontFamily: 'SpaceMono',
              fontSize: 14,
              fontWeight: FontWeight.w400,
              color: FarmerTheme.fogWhite60,
            ),
          ),
        ],
      ),
    );
  }
}
