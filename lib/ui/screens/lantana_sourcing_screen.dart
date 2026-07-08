import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/dashboard_provider.dart';
import '../../providers/lantana_sourcing_notifier.dart';
import '../components/dmrv_button.dart';
import '../design/premium_field_components.dart';
import '../design/tokens.dart';
import '../widgets/integrity_footer.dart';
import 'moisture_verification_screen.dart';

/// =============================================================================
/// LantanaSourcingScreen — India paper skin (tokens + Dmrv components)
/// =============================================================================
/// Three operational blocks (business logic unchanged):
///   1. IMMUTABLE feedstock placard ("Lantana_camara" — Registry Positive List)
///   2. GPS polygon capture (mock)
///   3. Harvest timestamp + 72-hour SUN-DRY temporal lock
///       • Hidden DEV BYPASS toggle (triple-tap the lock block to expose)
/// =============================================================================
class LantanaSourcingScreen extends ConsumerStatefulWidget {
  const LantanaSourcingScreen({super.key});

  @override
  ConsumerState<LantanaSourcingScreen> createState() =>
      _LantanaSourcingScreenState();
}

class _LantanaSourcingScreenState extends ConsumerState<LantanaSourcingScreen> {
  int _devToggleTaps = 0;
  bool _devToggleVisible = false;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final asyncS = ref.watch(lantanaSourcingProvider);
    final notifier = ref.read(lantanaSourcingProvider.notifier);
    final lastHash = ref.watch(dashboardProvider).lastHash;

    return asyncS.when(
      loading: () => Scaffold(
        backgroundColor: t.surface,
        body: Center(child: CircularProgressIndicator(color: t.accent)),
      ),
      error: (e, st) => Scaffold(
        backgroundColor: t.surface,
        body: Center(
          child: Text('Error: $e', style: t.body.copyWith(color: t.danger)),
        ),
      ),
      data: (s) => Scaffold(
        backgroundColor: t.surface,
        body: SafeArea(
          bottom: false,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              PremiumScreenHeader(
                stepNumber: '01',
                title: 'Biomass Sourcing',
                onBack: () => Navigator.of(context).pop(),
              ),
              Expanded(
                child: ListView(
                  padding: EdgeInsets.fromLTRB(t.gapL, 4, t.gapL, t.gapL),
                  children: [
                    _FeedstockBlock(species: s.feedstockSpecies),
                    SizedBox(height: t.gapL),
                    _PolygonBlock(
                      captured: s.polygonCaptured,
                      onTap: () async {
                        await notifier.captureGpsPolygon();
                      },
                    ),
                    SizedBox(height: t.gapL),
                    _HarvestBlock(
                      hasHarvest: s.hasHarvest,
                      harvestAt: s.harvestTimestamp,
                      onLogNow: () async => await notifier.logHarvestNow(),
                      onLogMinusHours: (h) async => await notifier.logHarvestAt(
                        DateTime.now().subtract(Duration(hours: h)),
                      ),
                    ),
                    SizedBox(height: t.gapL),
                    GestureDetector(
                      onTap: kDebugMode
                          ? () {
                              _devToggleTaps++;
                              if (_devToggleTaps >= 3) {
                                setState(() => _devToggleVisible = true);
                              }
                            }
                          : null,
                      child: _LockBlock(state: s),
                    ),
                    if (kDebugMode && _devToggleVisible) ...[
                      SizedBox(height: t.gapL),
                      _DevBypassBlock(
                        value: s.devBypass,
                        onChanged: notifier.toggleDevBypass,
                      ),
                    ],
                    SizedBox(height: t.gapL),
                    DmrvButton(
                      label: s.canProceedToMoisture
                          ? 'PROCEED TO MOISTURE CHECK'
                          : 'LOCKED // 72-HOUR DRY MANDATE',
                      testId: 'proceed-to-moisture-btn',
                      variant: DmrvButtonVariant.primary,
                      onPressed: s.canProceedToMoisture
                          ? () => Navigator.of(context).push(
                              MaterialPageRoute<void>(
                                builder: (_) =>
                                    const MoistureVerificationScreen(),
                              ),
                            )
                          : null,
                    ),
                  ],
                ),
              ),
              IntegrityFooter(lastHash: lastHash),
            ],
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Sub-widgets — visual layer only, no business logic.
// ---------------------------------------------------------------------------

class _BlockHeader extends StatelessWidget {
  const _BlockHeader(this.label);
  final String label;

  @override
  Widget build(BuildContext context) {
    return Text(label, style: Theme.of(context).textTheme.titleMedium);
  }
}

class _FeedstockBlock extends StatelessWidget {
  const _FeedstockBlock({required this.species});
  final String species;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    return PremiumFieldPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _BlockHeader('Feedstock // Registry Positive List'),
          SizedBox(height: t.gapM),
          Row(
            children: [
              Icon(Icons.lock_outline, color: t.accentText, size: 24),
              SizedBox(width: t.gapM),
              Expanded(
                child: Semantics(
                  identifier: 'feedstock-species',
                  child: Text(
                    species,
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                ),
              ),
              SizedBox(width: t.gapS),
              const PremiumStatusChip(
                label: 'IMMUTABLE',
                status: PremiumChipStatus.verified,
              ),
            ],
          ),
          SizedBox(height: t.gapS),
          Text(
            'Selection locked. Lantana camara is the only registry-approved feedstock for this artisan cohort.',
            style: t.metadata.copyWith(color: t.textSecondary),
          ),
        ],
      ),
    );
  }
}

class _PolygonBlock extends StatelessWidget {
  const _PolygonBlock({required this.captured, required this.onTap});
  final bool captured;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final Color accent = captured ? t.success : t.accentText;
    return PremiumFieldPanel(
      accentBorderColor: captured ? t.success : null,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _BlockHeader('GPS Polygon // Harvest Parcel'),
          SizedBox(height: t.gapM),
          Material(
            color: accent.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(t.radiusM),
            clipBehavior: Clip.antiAlias,
            child: InkWell(
              onTap: () {
                HapticFeedback.heavyImpact();
                onTap();
              },
              child: Container(
                constraints: const BoxConstraints(minHeight: 72),
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 14,
                ),
                child: Row(
                  children: [
                    Icon(
                      captured ? Icons.check_circle : Icons.gps_fixed,
                      color: accent,
                      size: 28,
                    ),
                    SizedBox(width: t.gapL),
                    Expanded(
                      child: Semantics(
                        identifier: 'capture-gps-polygon-btn',
                        button: true,
                        child: Text(
                          captured
                              ? 'Polygon captured // 4 vertices'
                              : 'Capture GPS Polygon',
                          style: Theme.of(context).textTheme.titleMedium
                              ?.copyWith(color: t.textPrimary),
                        ),
                      ),
                    ),
                    if (captured)
                      const PremiumStatusChip(
                        label: 'VERIFIED',
                        status: PremiumChipStatus.verified,
                      ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _HarvestBlock extends StatelessWidget {
  const _HarvestBlock({
    required this.hasHarvest,
    required this.harvestAt,
    required this.onLogNow,
    required this.onLogMinusHours,
  });
  final bool hasHarvest;
  final DateTime? harvestAt;
  final VoidCallback onLogNow;
  final void Function(int hours) onLogMinusHours;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    return PremiumFieldPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _BlockHeader('Harvest Timestamp'),
          SizedBox(height: t.gapM),
          if (hasHarvest)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              decoration: BoxDecoration(
                color: t.accent.withValues(alpha: 0.06),
                borderRadius: BorderRadius.circular(t.radiusS),
              ),
              child: Semantics(
                identifier: 'harvest-timestamp-display',
                child: Text(
                  harvestAt!.toUtc().toIso8601String(),
                  style: t.metadata.copyWith(color: t.textPrimary),
                ),
              ),
            )
          else
            Text(
              'Not yet logged',
              style: t.metadata.copyWith(color: t.textSecondary),
            ),
          SizedBox(height: t.gapL),
          Row(
            children: [
              Expanded(
                child: DmrvButton(
                  label: 'LOG HARVEST :: NOW',
                  testId: 'log-harvest-now-btn',
                  variant: DmrvButtonVariant.primary,
                  onPressed: onLogNow,
                ),
              ),
              SizedBox(width: t.gapM),
              SizedBox(
                width: 96,
                child: Material(
                  color: t.surfaceRaised,
                  borderRadius: BorderRadius.circular(t.radiusM),
                  clipBehavior: Clip.antiAlias,
                  child: InkWell(
                    onTap: () {
                      HapticFeedback.heavyImpact();
                      onLogMinusHours(73);
                    },
                    child: Container(
                      constraints: const BoxConstraints(minHeight: 64),
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(t.radiusM),
                        border: Border.all(color: t.border, width: 1.5),
                      ),
                      child: Semantics(
                        identifier: 'log-harvest-minus-73h-btn',
                        button: true,
                        child: Text(
                          '-73h\nTEST',
                          textAlign: TextAlign.center,
                          style: t.chipLabel.copyWith(
                            color: t.textSecondary,
                            height: 1.15,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _LockBlock extends StatefulWidget {
  const _LockBlock({required this.state});
  final SourcingState state;

  @override
  State<_LockBlock> createState() => _LockBlockState();
}

class _LockBlockState extends State<_LockBlock> {
  Timer? _ticker;

  @override
  void initState() {
    super.initState();
    _ticker = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _ticker?.cancel();
    super.dispose();
  }

  /// Pure-visual derivation from existing state. Mirrors the same branches
  /// used by `state.lockHudLabel` but emits a compact HH:MM:SS string for
  /// the large countdown readout.
  String _countdownLabel() {
    if (widget.state.devBypass) return '--:--:--';
    if (!widget.state.hasHarvest) return '--:--:--';
    if (widget.state.canProceedToMoisture) return '00:00:00';
    final r = widget.state.timeRemainingOnLock;
    final h = r.inHours.toString().padLeft(2, '0');
    final m = (r.inMinutes % 60).toString().padLeft(2, '0');
    final s = (r.inSeconds % 60).toString().padLeft(2, '0');
    return '$h:$m:$s';
  }

  PremiumChipStatus _chipStatus() {
    if (widget.state.devBypass) return PremiumChipStatus.pending;
    if (widget.state.canProceedToMoisture) return PremiumChipStatus.verified;
    if (!widget.state.hasHarvest) return PremiumChipStatus.locked;
    return PremiumChipStatus.error;
  }

  String _chipLabel() {
    if (widget.state.devBypass) return 'BYPASS';
    if (widget.state.canProceedToMoisture) return 'CLEARED';
    if (!widget.state.hasHarvest) return 'AWAITING';
    return 'LOCKED';
  }

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final bool cleared = widget.state.canProceedToMoisture;
    final Color accent = cleared ? t.success : t.danger;

    return PremiumFieldPanel(
      accentBorderColor: accent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                cleared ? Icons.lock_open : Icons.lock_clock,
                color: accent,
                size: 22,
              ),
              SizedBox(width: t.gapM),
              Expanded(
                child: Text(
                  '72-Hour Sun-Dry Mandate',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
              PremiumStatusChip(label: _chipLabel(), status: _chipStatus()),
            ],
          ),
          SizedBox(height: t.gapL),
          Semantics(
            identifier: 'sourcing-lock-hud',
            child: Text(
              _countdownLabel(),
              style: t.numericHero.copyWith(
                fontSize: 40,
                color: t.textPrimary,
                letterSpacing: -0.5,
              ),
            ),
          ),
          SizedBox(height: t.gapS),
          Text(
            widget.state.lockHudLabel,
            style: t.metadata.copyWith(color: t.textSecondary),
          ),
          SizedBox(height: t.gapS),
          Text(
            'Per CSI Global Artisan C-Sink methodology, sourced biomass must air-dry for ≥ 72 hours before moisture verification.',
            style: t.metadata.copyWith(color: t.textSecondary),
          ),
        ],
      ),
    );
  }
}

class _DevBypassBlock extends StatelessWidget {
  const _DevBypassBlock({required this.value, required this.onChanged});
  final bool value;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    return PremiumFieldPanel(
      accentBorderColor: t.accent,
      child: Row(
        children: [
          Icon(Icons.science_outlined, color: t.accentText, size: 22),
          SizedBox(width: t.gapM),
          Expanded(
            child: Text(
              'DEV BYPASS // 72h LOCK',
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ),
          Semantics(
            identifier: 'dev-bypass-switch',
            child: Switch(
              value: value,
              onChanged: onChanged,
              activeThumbColor: t.accent,
            ),
          ),
        ],
      ),
    );
  }
}
