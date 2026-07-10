import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../components/dmrv_button.dart';
import '../design/premium_field_components.dart';
import '../design/tokens.dart';
import '../widgets/integrity_footer.dart';
import '../../data/local/database_provider.dart';

import '../../providers/batch_session_notifier.dart';
import '../../providers/dashboard_provider.dart';
import '../../providers/lantana_sourcing_notifier.dart';
import '../../providers/moisture_gate_notifier.dart';
import '../../services/secure_capture_service.dart';
import 'pyrolysis_screen.dart';
import 'secure_camera_screen.dart';

/// =============================================================================
/// MoistureVerificationScreen — India paper skin (tokens + Dmrv components)
/// =============================================================================
/// Workflow:
///   1. Operator types the meter reading.
///   2. If reading is compliant (≤ 15.0%), they tap CAPTURE METER PHOTO.
///   3. Full-screen [SecureCameraScreen] opens, runs the anti-fraud pipeline,
///      and returns a [SecureCaptureResult].
///   4. We call [AppDatabase.insertBiomassSourcingWithOutbox], which atomically
///      writes the BiomassSourcing row + a SyncOutbox event.
///   5. Once persisted, "INITIATE PYROLYSIS" renders.
/// =============================================================================
class MoistureVerificationScreen extends ConsumerStatefulWidget {
  const MoistureVerificationScreen({super.key});

  @override
  ConsumerState<MoistureVerificationScreen> createState() =>
      _MoistureVerificationScreenState();
}

class _MoistureVerificationScreenState
    extends ConsumerState<MoistureVerificationScreen> {
  late final TextEditingController _controller;
  bool _persisting = false;
  String? _persistError;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _launchSecureCapture() async {
    final moisture = ref.read(moistureGateProvider);
    if (!moisture.isCompliant) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Enter a compliant (≤15%) reading before capturing.'),
        ),
      );
      return;
    }

    final result = await Navigator.of(context).push<SecureCaptureResult>(
      MaterialPageRoute(builder: (_) => const SecureCameraScreen()),
    );
    if (result == null) return;

    await _persistEvidence(result);
  }

  Future<void> _persistEvidence(SecureCaptureResult result) async {
    if (_persisting) return;
    setState(() {
      _persisting = true;
      _persistError = null;
    });
    try {
      final batchUuid = ref.read(requiredBatchUuidProvider);
      final sourcing = ref.read(lantanaSourcingProvider).requireValue;
      final moisture = ref.read(moistureGateProvider);
      if (moisture.moisturePercent == null) {
        throw StateError('Missing reading.');
      }

      final db = await ref.read(appDatabaseProvider.future);
      final sourcingUuid = await db.insertBiomassSourcingWithOutbox(
        batchUuid: batchUuid,
        feedstockSpecies: sourcing.feedstockSpecies,
        harvestTimestamp: (sourcing.harvestTimestamp ?? DateTime.now().toUtc())
            .toIso8601String(),
        moisturePercent: moisture.moisturePercent!,
        moistureCompliant: moisture.isCompliant,
        photoPath: result.sandboxPath,
        sha256Hash: result.sha256Hash,
        latitude: result.latitude,
        longitude: result.longitude,
        mockLocationEnabled: result.isMocked,
        harvestUptimeSeconds: sourcing.harvestUptimeSeconds,
        azimuth: result.azimuth,
        pitch: result.pitch,
        roll: result.roll,
        // Rainbow C1 (S2): biomass weight + method captured on the Sourcing
        // screen; drives the server C1 gate and the C2 moisture-sample target.
        biomassInputKg: sourcing.biomassInputKg,
        biomassMeasurementMethod: sourcing.biomassMeasurementMethod,
        // Rainbow T1.1: stamp the configured project so the server can run the
        // project-scoped C8/C9 gates. Empty (unconfigured build) => null, which
        // keeps the batch legacy-shaped and the gates inert.
        projectId: const String.fromEnvironment('DMRV_PROJECT_ID').isEmpty
            ? null
            : const String.fromEnvironment('DMRV_PROJECT_ID'),
        // scale_id is populated once BLE scale pairing exposes an identity.
        scaleId: null,
      );
      ref.read(dashboardProvider.notifier).markBiomassVerified();

      debugPrint(
        '[MoistureScreen] insertBiomassSourcingWithOutbox OK — '
        'sourcingUuid=$sourcingUuid batchUuid=$batchUuid '
        'sha256=${result.sha256Hash}',
      );
    } catch (e, st) {
      debugPrint('[MoistureScreen] persist failed: $e\n$st');
      setState(() => _persistError = e.toString());
    } finally {
      if (mounted) setState(() => _persisting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final s = ref.watch(moistureGateProvider);
    final notifier = ref.read(moistureGateProvider.notifier);
    final isNonCompliant = s.status == MoistureGateStatus.nonCompliant;

    final hasEvidence = ref.watch(moistureEvidenceProvider).value ?? false;
    final canInitiatePyrolysis = s.isCompliant && hasEvidence;
    final String footerHash = hasEvidence
        ? 'DECOUPLED-MEDIA-STORED-IN-DB'
        : '----------------------------------------------------------------';

    return Scaffold(
      backgroundColor: t.surface,
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            PremiumScreenHeader(
              stepNumber: '02',
              title: 'Moisture Verification',
              onBack: () => Navigator.of(context).pop(),
            ),
            Expanded(
              child: ListView(
                padding: EdgeInsets.fromLTRB(t.gapL, 4, t.gapL, t.gapL),
                children: [
                  _MeterReadingBlock(
                    controller: _controller,
                    rawInput: s.rawInput,
                    status: s.status,
                    onChanged: notifier.updateReading,
                  ),
                  SizedBox(height: t.gapL),
                  _PhotoBlock(
                    hasEvidence: hasEvidence,
                    persisting: _persisting,
                    enabled: s.isCompliant && !_persisting,
                    onTap: _launchSecureCapture,
                  ),
                  if (_persistError != null) ...[
                    SizedBox(height: t.gapM),
                    Container(
                      padding: EdgeInsets.all(t.gapM),
                      decoration: BoxDecoration(
                        color: t.dangerSurface,
                        borderRadius: BorderRadius.circular(t.radiusM),
                        border: Border.all(color: t.danger, width: 1),
                      ),
                      child: Text(
                        _persistError!,
                        style: t.metadata.copyWith(color: t.danger),
                      ),
                    ),
                  ],
                  SizedBox(height: t.gapL),
                  _StatusBlock(state: s, hasEvidence: hasEvidence),
                  if (isNonCompliant) ...[
                    SizedBox(height: t.gapL),
                    _SevereErrorBlock(message: s.errorMessage!),
                  ],
                  if (canInitiatePyrolysis) ...[
                    SizedBox(height: t.gapXL),
                    DmrvButton(
                      label: 'INITIATE PYROLYSIS',
                      testId: 'initiate-pyrolysis-btn',
                      variant: DmrvButtonVariant.primary,
                      onPressed: () {
                        Navigator.of(context).push(
                          MaterialPageRoute<void>(
                            builder: (_) => const PyrolysisScreen(),
                          ),
                        );
                      },
                    ),
                  ],
                  SizedBox(height: t.gapL),
                ],
              ),
            ),
            IntegrityFooter(lastHash: footerHash),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// METER READING BLOCK
// ---------------------------------------------------------------------------

class _MeterReadingBlock extends StatelessWidget {
  const _MeterReadingBlock({
    required this.controller,
    required this.rawInput,
    required this.status,
    required this.onChanged,
  });
  final TextEditingController controller;
  final String rawInput;
  final MoistureGateStatus status;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final Color accent = switch (status) {
      MoistureGateStatus.compliant => t.success,
      MoistureGateStatus.nonCompliant => t.danger,
      MoistureGateStatus.pending => t.accentText,
    };

    return PremiumFieldPanel(
      accentBorderColor: accent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'METER READING // % MOISTURE',
            style: t.chipLabel.copyWith(color: accent),
          ),
          SizedBox(height: t.gapM),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: t.surface,
              borderRadius: BorderRadius.circular(t.radiusM),
              border: Border.all(
                color: accent.withValues(alpha: 0.35),
                width: 1,
              ),
            ),
            child: Semantics(
              identifier: 'moisture-reading-input',
              child: TextField(
                controller: controller,
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                  signed: false,
                ),
                inputFormatters: [
                  FilteringTextInputFormatter.allow(RegExp(r'[0-9.]')),
                ],
                onChanged: onChanged,
                cursorColor: accent,
                style: t.numericHero.copyWith(fontSize: 56, color: accent),
                decoration: InputDecoration(
                  border: InputBorder.none,
                  isCollapsed: true,
                  contentPadding: const EdgeInsets.symmetric(vertical: 8),
                  hintText: '00.0',
                  hintStyle: t.numericHero.copyWith(
                    fontSize: 56,
                    color: t.textDisabled,
                  ),
                  suffixText: '%',
                  suffixStyle: t.numericHero.copyWith(
                    fontSize: 32,
                    color: accent,
                  ),
                ),
              ),
            ),
          ),
          SizedBox(height: t.gapS),
          Text(
            'COMPLIANCE CEILING :: ≤ 15.0%',
            style: t.metadata.copyWith(color: t.textSecondary),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// PHOTO CAPTURE BLOCK
// ---------------------------------------------------------------------------

class _PhotoBlock extends StatelessWidget {
  const _PhotoBlock({
    required this.hasEvidence,
    required this.persisting,
    required this.enabled,
    required this.onTap,
  });
  final bool hasEvidence;
  final bool persisting;
  final bool enabled;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final bool captured = hasEvidence;

    final Color iconColor = captured ? t.success : t.accentText;
    final IconData iconData = persisting
        ? Icons.hourglass_top
        : (captured ? Icons.verified : Icons.photo_camera_outlined);

    final String label = persisting
        ? 'PERSISTING TO OUTBOX…'
        : (captured
              ? 'PHOTO CAPTURED // EXIF + SHA-256 ANCHORED'
              : 'CAPTURE METER PHOTO');

    return Semantics(
      identifier: 'capture-meter-photo-btn',
      button: true,
      enabled: enabled,
      child: GestureDetector(
        onTap: enabled
            ? () {
                HapticFeedback.heavyImpact();
                onTap();
              }
            : null,
        behavior: HitTestBehavior.opaque,
        child: PremiumFieldPanel(
          accentBorderColor: captured ? t.success : null,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(iconData, color: iconColor, size: 28),
                  SizedBox(width: t.gapM),
                  Expanded(
                    child: Text(
                      label,
                      style: t.metadata.copyWith(
                        color: t.textPrimary,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  if (captured)
                    const PremiumStatusChip(
                      label: 'VERIFIED',
                      status: PremiumChipStatus.verified,
                    )
                  else if (enabled)
                    const PremiumStatusChip(
                      label: 'PENDING',
                      status: PremiumChipStatus.pending,
                    )
                  else
                    const PremiumStatusChip(
                      label: 'LOCKED',
                      status: PremiumChipStatus.locked,
                    ),
                ],
              ),
              if (captured) ...[
                SizedBox(height: t.gapS),
                Text(
                  'OUTBOX: COMMITTED (DECOUPLED)',
                  style: t.chipLabel.copyWith(color: t.success),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// STATUS BLOCK
// ---------------------------------------------------------------------------

class _StatusBlock extends StatelessWidget {
  const _StatusBlock({required this.state, required this.hasEvidence});
  final MoistureGateState state;
  final bool hasEvidence;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final Color accent = switch (state.status) {
      MoistureGateStatus.compliant => t.success,
      MoistureGateStatus.nonCompliant => t.danger,
      MoistureGateStatus.pending => t.accentText,
    };

    final PremiumChipStatus chipStatus = switch (state.status) {
      MoistureGateStatus.compliant => PremiumChipStatus.verified,
      MoistureGateStatus.nonCompliant => PremiumChipStatus.error,
      MoistureGateStatus.pending => PremiumChipStatus.pending,
    };

    final String chipLabel = switch (state.status) {
      MoistureGateStatus.compliant => 'COMPLIANT',
      MoistureGateStatus.nonCompliant => 'BLOCKED',
      MoistureGateStatus.pending => 'PENDING',
    };

    final String label = switch (state.status) {
      MoistureGateStatus.pending => 'AWAITING METER READING',
      MoistureGateStatus.compliant =>
        hasEvidence
            ? 'COMPLIANT // EVIDENCE PERSISTED'
            : 'COMPLIANT // CAPTURE PHOTO TO PROCEED',
      MoistureGateStatus.nonCompliant =>
        'NON-COMPLIANT // MOISTURE EXCEEDS 15%',
    };

    return PremiumFieldPanel(
      accentBorderColor: accent,
      child: Row(
        children: [
          PremiumStatusChip(label: chipLabel, status: chipStatus),
          SizedBox(width: t.gapM),
          Expanded(
            child: Semantics(
              identifier: 'moisture-status-hud',
              child: Text(
                label,
                style: t.metadata.copyWith(
                  color: t.textPrimary,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// SEVERE ERROR BLOCK
// ---------------------------------------------------------------------------

class _SevereErrorBlock extends StatelessWidget {
  const _SevereErrorBlock({required this.message});
  final String message;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    return Container(
      padding: EdgeInsets.all(t.gapL),
      decoration: BoxDecoration(
        color: t.dangerSurface,
        borderRadius: BorderRadius.circular(t.radiusM),
        border: Border.all(color: t.danger, width: 2),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.report, color: t.danger, size: 36),
          SizedBox(width: t.gapM),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'NON-COMPLIANT // WORKFLOW LOCKED',
                  style: t.blockHeader.copyWith(color: t.danger),
                ),
                SizedBox(height: t.gapS),
                Semantics(
                  identifier: 'moisture-error-message',
                  child: Text(
                    message,
                    style: t.numericMedium.copyWith(
                      fontSize: 22,
                      color: t.danger,
                    ),
                  ),
                ),
                SizedBox(height: t.gapS),
                Text(
                  'Continue air-drying the biomass. Re-measure once moisture\ndrops to or below 15.0%.',
                  style: t.metadata.copyWith(color: t.textSecondary),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
