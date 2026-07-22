import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/dashboard_provider.dart';
import '../../providers/lantana_sourcing_notifier.dart';
import '../../services/parcel_service.dart';
import '../components/dmrv_button.dart';
import '../design/premium_field_components.dart';
import '../design/tokens.dart';
import '../widgets/integrity_footer.dart';
import 'moisture_verification_screen.dart';

/// =============================================================================
/// LantanaSourcingScreen — India paper skin (tokens + Dmrv components)
/// =============================================================================
/// Three operational blocks:
///   1. IMMUTABLE feedstock placard ("Lantana_camara" — Registry Positive List)
///   2. Source parcel status (read-only; real parcel registration + overlap
///      checking lands in V8 Part 1 — see docs/BOUNDARY_DESIGN.md)
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
                    const _SourceParcelBlock(),
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
                    _BiomassBlock(
                      kg: s.biomassInputKg,
                      method: s.biomassMeasurementMethod,
                    ),
                    SizedBox(height: t.gapL),
                    DmrvButton(
                      label: (s.canProceedToMoisture && s.hasBiomass)
                          ? 'PROCEED TO MOISTURE CHECK'
                          : (!s.hasBiomass
                                ? 'RECORD BIOMASS WEIGHT FIRST'
                                : 'LOCKED // 72-HOUR DRY MANDATE'),
                      testId: 'proceed-to-moisture-btn',
                      variant: DmrvButtonVariant.primary,
                      onPressed: (s.canProceedToMoisture && s.hasBiomass)
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

/// Rainbow C1 — biomass weight + measurement method. Pushes the value into the
/// sourcing notifier so the Sourcing gate and the moisture-sample target react.
class _BiomassBlock extends ConsumerStatefulWidget {
  const _BiomassBlock({required this.kg, required this.method});
  final double? kg;
  final String? method;
  @override
  ConsumerState<_BiomassBlock> createState() => _BiomassBlockState();
}

class _BiomassBlockState extends ConsumerState<_BiomassBlock> {
  late final TextEditingController _ctrl;
  String? _method;
  String? _error;

  @override
  void initState() {
    super.initState();
    _ctrl = TextEditingController(
      text: (widget.kg != null && widget.kg! > 0)
          ? widget.kg!.toStringAsFixed(0)
          : '',
    );
    _method = widget.method;
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  void _commit() {
    final kg = double.tryParse(_ctrl.text.trim());
    if (kg == null || kg <= 0 || kg > 100000) {
      setState(() => _error = 'Enter a weight between 1 and 100000 kg');
      return;
    }
    if (_method == null) {
      setState(() => _error = 'Select how the weight was measured');
      return;
    }
    setState(() => _error = null);
    ref.read(lantanaSourcingProvider.notifier).setBiomass(kg, _method!);
  }

  void _pick(String method) {
    setState(() => _method = method);
    _commit();
  }

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    return PremiumFieldPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _BlockHeader('BIOMASS INPUT'),
          SizedBox(height: t.gapM),
          PremiumInputField(
            controller: _ctrl,
            hint: 'Feedstock weight',
            suffix: const Text('kg'),
            semanticId: 'biomass-weight-input',
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            inputFormatters: [
              FilteringTextInputFormatter.allow(RegExp(r'[0-9.]')),
            ],
            errorText: _error,
            onChanged: (_) => _commit(),
          ),
          SizedBox(height: t.gapM),
          Row(
            children: [
              Expanded(
                child: DmrvButton(
                  label: 'WEIGHED',
                  testId: 'biomass-method-direct_weigh',
                  variant: _method == 'direct_weigh'
                      ? DmrvButtonVariant.primary
                      : DmrvButtonVariant.neutral,
                  onPressed: () => _pick('direct_weigh'),
                ),
              ),
              SizedBox(width: t.gapM),
              Expanded(
                child: DmrvButton(
                  label: 'EST. FROM YIELD',
                  testId: 'biomass-method-yield_conversion',
                  variant: _method == 'yield_conversion'
                      ? DmrvButtonVariant.primary
                      : DmrvButtonVariant.neutral,
                  onPressed: () => _pick('yield_conversion'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

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

/// V8 Part 1.6 — source-parcel selector. Replaces the removed
/// `captureGpsPolygon()` boolean theatre (Part 0.3, which persisted a tap as
/// "Polygon captured // 4 vertices" with no real geometry — a false
/// attestation). This fetches the project's APPROVED parcels (offline-cached),
/// lets the operator pick one, and persists the choice; the selected
/// `parcel_uuid` rides the batch so the server geofences the capture against
/// that approved, non-overlapping parcel. Honest "not yet assigned" until a
/// real parcel is chosen.
class _SourceParcelBlock extends ConsumerStatefulWidget {
  const _SourceParcelBlock();

  @override
  ConsumerState<_SourceParcelBlock> createState() => _SourceParcelBlockState();
}

class _SourceParcelBlockState extends ConsumerState<_SourceParcelBlock> {
  static const _projectId = String.fromEnvironment('DMRV_PROJECT_ID');
  bool _loading = false;

  Future<void> _pickParcel() async {
    final messenger = ScaffoldMessenger.of(context);
    if (_projectId.isEmpty) {
      messenger.showSnackBar(
        const SnackBar(content: Text('No project configured for this device.')),
      );
      return;
    }
    setState(() => _loading = true);
    final parcels = await ParcelService.fetchForProject(_projectId);
    if (!mounted) return;
    setState(() => _loading = false);
    if (parcels.isEmpty) {
      messenger.showSnackBar(
        const SnackBar(
          content: Text('No approved parcels available for this project.'),
        ),
      );
      return;
    }
    final selected = await showModalBottomSheet<ParcelOption>(
      context: context,
      builder: (ctx) => SafeArea(
        child: ListView(
          shrinkWrap: true,
          children: [
            for (final p in parcels)
              ListTile(
                title: Text(p.name),
                subtitle: Text(
                  p.uuid,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                onTap: () => Navigator.of(ctx).pop(p),
              ),
          ],
        ),
      ),
    );
    if (selected != null) {
      await ref
          .read(lantanaSourcingProvider.notifier)
          .selectParcel(selected.uuid, selected.name);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final parcelName =
        ref.watch(lantanaSourcingProvider).valueOrNull?.parcelName;
    final hasParcel = parcelName != null && parcelName.isNotEmpty;
    final accent = hasParcel ? t.success : t.textSecondary;
    return PremiumFieldPanel(
      accentBorderColor: hasParcel ? t.success : null,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _BlockHeader('Source Parcel // Harvest Origin'),
          SizedBox(height: t.gapM),
          Material(
            color: accent.withValues(alpha: 0.06),
            borderRadius: BorderRadius.circular(t.radiusM),
            clipBehavior: Clip.antiAlias,
            child: InkWell(
              onTap: _loading ? null : _pickParcel,
              child: Container(
                constraints: const BoxConstraints(minHeight: 72),
                padding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                child: Row(
                  children: [
                    Icon(
                      hasParcel ? Icons.check_circle : Icons.map_outlined,
                      color: accent,
                      size: 28,
                    ),
                    SizedBox(width: t.gapL),
                    Expanded(
                      child: Semantics(
                        identifier: 'source-parcel-selector',
                        button: true,
                        child: Text(
                          hasParcel
                              ? 'Source parcel: $parcelName'
                              : 'Select source parcel',
                          style: Theme.of(context).textTheme.titleMedium
                              ?.copyWith(color: t.textPrimary),
                        ),
                      ),
                    ),
                    if (_loading)
                      const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    else
                      Icon(Icons.chevron_right, color: t.textSecondary),
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
