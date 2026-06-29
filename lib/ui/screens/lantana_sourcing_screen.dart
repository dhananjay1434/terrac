import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/dashboard_provider.dart';
import '../../providers/lantana_sourcing_notifier.dart';
import '../design/app_theme.dart';
import '../design/premium_field_components.dart';
import '../widgets/integrity_footer.dart';
import 'moisture_verification_screen.dart';

/// =============================================================================
/// LantanaSourcingScreen — migrated to AppTheme (Tactical Titanium light)
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
    final asyncS = ref.watch(lantanaSourcingProvider);
    final notifier = ref.read(lantanaSourcingProvider.notifier);
    final lastHash = ref.watch(dashboardProvider).lastHash;

    return asyncS.when(
      loading: () => const Scaffold(
        backgroundColor: AppTheme.tacticalTitanium,
        body: Center(child: CircularProgressIndicator()),
      ),
      error: (e, st) => Scaffold(
        backgroundColor: AppTheme.tacticalTitanium,
        body: Center(
          child: Text('Error: $e', style: const TextStyle(color: Colors.white)),
        ),
      ),
      data: (s) => Scaffold(
        backgroundColor: AppTheme.tacticalTitanium,
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
                  padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
                  children: [
                    _FeedstockBlock(species: s.feedstockSpecies),
                    const SizedBox(height: 16),
                    _PolygonBlock(
                      captured: s.polygonCaptured,
                      onTap: () async { await notifier.captureGpsPolygon(); },
                    ),
                    const SizedBox(height: 16),
                    _HarvestBlock(
                      hasHarvest: s.hasHarvest,
                      harvestAt: s.harvestTimestamp,
                      onLogNow: () async => await notifier.logHarvestNow(),
                      onLogMinusHours: (h) async => await notifier.logHarvestAt(
                        DateTime.now().subtract(Duration(hours: h)),
                      ),
                    ),
                    const SizedBox(height: 16),
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
                      const SizedBox(height: 16),
                      _DevBypassBlock(
                        value: s.devBypass,
                        onChanged: notifier.toggleDevBypass,
                      ),
                    ],
                    const SizedBox(height: 16),
                    PremiumFieldButton(
                      label: s.canProceedToMoisture
                          ? 'PROCEED TO MOISTURE CHECK'
                          : 'LOCKED // 72-HOUR DRY MANDATE',
                      testId: 'proceed-to-moisture-btn',
                      state: s.canProceedToMoisture
                          ? FieldButtonState.go
                          : FieldButtonState.locked,
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
    return PremiumFieldPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _BlockHeader('Feedstock // Registry Positive List'),
          const SizedBox(height: 12),
          Row(
            children: [
              const Icon(
                Icons.lock_outline,
                color: AppTheme.cobaltShield,
                size: 24,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Semantics(
                  identifier: 'feedstock-species',
                  child: Text(
                    species,
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              const PremiumStatusChip(
                label: 'IMMUTABLE',
                status: PremiumChipStatus.verified,
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Selection locked. Lantana camara is the only registry-approved feedstock for this artisan cohort.',
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: AppTheme.armorSlate70),
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
    final Color accent = captured ? AppTheme.yieldGold : AppTheme.cobaltShield;
    return PremiumFieldPanel(
      accentBorderColor: captured ? AppTheme.yieldGold : null,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _BlockHeader('GPS Polygon // Harvest Parcel'),
          const SizedBox(height: 12),
          Material(
            color: accent.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(10),
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
                    const SizedBox(width: 14),
                    Expanded(
                      child: Semantics(
                        identifier: 'capture-gps-polygon-btn',
                        button: true,
                        child: Text(
                          captured
                              ? 'Polygon captured // 4 vertices'
                              : 'Capture GPS Polygon',
                          style: Theme.of(context).textTheme.titleMedium
                              ?.copyWith(color: AppTheme.armorSlate),
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
    return PremiumFieldPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _BlockHeader('Harvest Timestamp'),
          const SizedBox(height: 12),
          if (hasHarvest)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              decoration: BoxDecoration(
                color: AppTheme.cobaltShield06,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Semantics(
                identifier: 'harvest-timestamp-display',
                child: Text(
                  harvestAt!.toUtc().toIso8601String(),
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ),
            )
          else
            Text(
              'Not yet logged',
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: AppTheme.armorSlate60),
            ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: PremiumFieldButton(
                  label: 'LOG HARVEST :: NOW',
                  testId: 'log-harvest-now-btn',
                  state: FieldButtonState.go,
                  onPressed: onLogNow,
                ),
              ),
              const SizedBox(width: 12),
              SizedBox(
                width: 96,
                child: Material(
                  color: AppTheme.tacticalTitanium,
                  borderRadius: BorderRadius.circular(12),
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
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: AppTheme.cobaltShield30,
                          width: 1.5,
                        ),
                      ),
                      child: Semantics(
                        identifier: 'log-harvest-minus-73h-btn',
                        button: true,
                        child: Text(
                          '-73h\nTEST',
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                            fontFamily: 'SpaceMono',
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                            color: AppTheme.armorSlate,
                            letterSpacing: 0.5,
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
  static const Color _stopRed = Color(0xFFDC2626);
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
  /// the 40sp SpaceMono readout.
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
    final bool cleared = widget.state.canProceedToMoisture;
    final Color accent = cleared ? AppTheme.yieldGold : _stopRed;

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
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  '72-Hour Sun-Dry Mandate',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
              PremiumStatusChip(label: _chipLabel(), status: _chipStatus()),
            ],
          ),
          const SizedBox(height: 14),
          Semantics(
            identifier: 'sourcing-lock-hud',
            child: Text(
              _countdownLabel(),
              style: const TextStyle(
                fontFamily: 'SpaceMono',
                fontSize: 40,
                fontWeight: FontWeight.w700,
                color: AppTheme.armorSlate,
                letterSpacing: -0.5,
                height: 1.0,
              ),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            widget.state.lockHudLabel,
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: AppTheme.armorSlate70),
          ),
          const SizedBox(height: 8),
          Text(
            'Per CSI Global Artisan C-Sink methodology, sourced biomass must air-dry for ≥ 72 hours before moisture verification.',
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: AppTheme.armorSlate60),
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
    return PremiumFieldPanel(
      accentBorderColor: AppTheme.cobaltShield,
      child: Row(
        children: [
          const Icon(
            Icons.science_outlined,
            color: AppTheme.cobaltShield,
            size: 22,
          ),
          const SizedBox(width: 12),
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
              activeThumbColor: AppTheme.cobaltShield,
            ),
          ),
        ],
      ),
    );
  }
}
