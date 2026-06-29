import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../services/sync_queue_manager.dart';

import '../design/app_theme.dart';
import '../design/premium_field_components.dart';
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
/// MoistureVerificationScreen
/// =============================================================================
/// Workflow:
///   1. Operator types the meter reading.
///   2. If reading is compliant (≤ 15.0%), they tap CAPTURE METER PHOTO.
///   3. Full-screen [SecureCameraScreen] opens, runs the anti-fraud pipeline,
///      and returns a [SecureCaptureResult].
///   4. We call [AppDatabase.insertBiomassSourcingWithOutbox], which atomically
///      writes the BiomassSourcing row + a SyncOutbox event. The dashboard
///      counter stream is wired to the outbox table and increments instantly.
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
  // ---------------------------------------------------------------------------
  // Light-theme palette shared with sibling widgets in this file. Defined here
  // so the visual rules ("Tactical Titanium") stay co-located with the screen.
  // ---------------------------------------------------------------------------
  static const Color _errorRed = Color(0xFFDC2626);
  static const Color _errorRedSoftBg = Color(0xFFFEF2F2);

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
      );
      ref.read(dashboardProvider.notifier).markBiomassVerified();

      // The BiomassSourcing record natively contains the photo_path and uploads
      // the media file automatically during the sync process.

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
    final s = ref.watch(moistureGateProvider);
    final notifier = ref.read(moistureGateProvider.notifier);
    final isNonCompliant = s.status == MoistureGateStatus.nonCompliant;

    // Watch Drift for the presence of the photo evidence
    final hasEvidence = ref.watch(moistureEvidenceProvider).value ?? false;
    final canInitiatePyrolysis = s.isCompliant && hasEvidence;
    final String footerHash = hasEvidence
        ? 'DECOUPLED-MEDIA-STORED-IN-DB'
        : '----------------------------------------------------------------';

    return Scaffold(
      backgroundColor: AppTheme.tacticalTitanium,
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
                padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
                children: [
                  _MeterReadingBlock(
                    controller: _controller,
                    rawInput: s.rawInput,
                    status: s.status,
                    onChanged: notifier.updateReading,
                  ),
                  const SizedBox(height: 16),
                  _PhotoBlock(
                    hasEvidence: hasEvidence,
                    persisting: _persisting,
                    enabled: s.isCompliant && !_persisting,
                    onTap: _launchSecureCapture,
                  ),
                  if (_persistError != null) ...[
                    const SizedBox(height: 12),
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: _errorRedSoftBg,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: _errorRed, width: 1),
                      ),
                      child: Text(
                        _persistError!,
                        style: const TextStyle(
                          fontFamily: 'SpaceMono',
                          fontSize: 13,
                          fontWeight: FontWeight.w400,
                          color: _errorRed,
                        ),
                      ),
                    ),
                  ],
                  const SizedBox(height: 16),
                  _StatusBlock(state: s, hasEvidence: hasEvidence),
                  if (isNonCompliant) ...[
                    const SizedBox(height: 16),
                    _SevereErrorBlock(message: s.errorMessage!),
                  ],
                  if (canInitiatePyrolysis) ...[
                    const SizedBox(height: 24),
                    PremiumFieldButton(
                      label: 'INITIATE PYROLYSIS',
                      testId: 'initiate-pyrolysis-btn',
                      state: FieldButtonState.go,
                      onPressed: () {
                        Navigator.of(context).push(
                          MaterialPageRoute<void>(
                            builder: (_) => const PyrolysisScreen(),
                          ),
                        );
                      },
                    ),
                  ],
                  const SizedBox(height: 16),
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

  static const Color _errorRed = Color(0xFFDC2626);

  @override
  Widget build(BuildContext context) {
    final Color accent = switch (status) {
      MoistureGateStatus.compliant => AppTheme.yieldGold,
      MoistureGateStatus.nonCompliant => _errorRed,
      MoistureGateStatus.pending => AppTheme.cobaltShield,
    };

    return PremiumFieldPanel(
      accentBorderColor: accent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'METER READING // % MOISTURE',
            style: TextStyle(
              fontFamily: 'SpaceGrotesk',
              fontSize: 13,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.8,
              color: accent,
            ),
          ),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: BoxDecoration(
              color: AppTheme.tacticalTitanium,
              borderRadius: BorderRadius.circular(10),
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
                style: TextStyle(
                  fontFamily: 'SpaceMono',
                  fontSize: 56,
                  fontWeight: FontWeight.w700,
                  color: accent,
                  height: 1.0,
                ),
                decoration: InputDecoration(
                  border: InputBorder.none,
                  isCollapsed: true,
                  contentPadding: const EdgeInsets.symmetric(vertical: 8),
                  hintText: '00.0',
                  hintStyle: TextStyle(
                    fontFamily: 'SpaceMono',
                    fontSize: 56,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.armorSlate20,
                    height: 1.0,
                  ),
                  suffixText: '%',
                  suffixStyle: TextStyle(
                    fontFamily: 'SpaceMono',
                    fontSize: 32,
                    fontWeight: FontWeight.w700,
                    color: accent,
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'COMPLIANCE CEILING :: ≤ 15.0%',
            style: TextStyle(
              fontFamily: 'SpaceMono',
              fontSize: 12,
              fontWeight: FontWeight.w400,
              color: AppTheme.armorSlate55,
            ),
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
    final bool captured = hasEvidence;

    final Color iconColor = captured
        ? AppTheme.yieldGold
        : AppTheme.cobaltShield;
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
          accentBorderColor: captured ? AppTheme.yieldGold : null,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(iconData, color: iconColor, size: 28),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      label,
                      style: const TextStyle(
                        fontFamily: 'SpaceGrotesk',
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 0.4,
                        color: AppTheme.armorSlate,
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
                const SizedBox(height: 8),
                Text(
                  'OUTBOX: COMMITTED (DECOUPLED)',
                  style: TextStyle(
                    fontFamily: 'SpaceGrotesk',
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.8,
                    color: AppTheme.yieldGold,
                  ),
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

  static const Color _errorRed = Color(0xFFDC2626);

  @override
  Widget build(BuildContext context) {
    final Color accent = switch (state.status) {
      MoistureGateStatus.compliant => AppTheme.yieldGold,
      MoistureGateStatus.nonCompliant => _errorRed,
      MoistureGateStatus.pending => AppTheme.cobaltShield,
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
          const SizedBox(width: 12),
          Expanded(
            child: Semantics(
              identifier: 'moisture-status-hud',
              child: Text(
                label,
                style: const TextStyle(
                  fontFamily: 'SpaceGrotesk',
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 0.4,
                  color: AppTheme.armorSlate,
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

  static const Color _errorRed = Color(0xFFDC2626);
  static const Color _errorRedSoftBg = Color(0xFFFEF2F2);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: _errorRedSoftBg,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: _errorRed, width: 2),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.report, color: _errorRed, size: 36),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'NON-COMPLIANT // WORKFLOW LOCKED',
                  style: TextStyle(
                    fontFamily: 'SpaceGrotesk',
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.5,
                    color: _errorRed,
                  ),
                ),
                const SizedBox(height: 8),
                Semantics(
                  identifier: 'moisture-error-message',
                  child: Text(
                    message,
                    style: const TextStyle(
                      fontFamily: 'SpaceGrotesk',
                      fontSize: 22,
                      fontWeight: FontWeight.w700,
                      color: _errorRed,
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Continue air-drying the biomass. Re-measure once moisture\ndrops to or below 15.0%.',
                  style: TextStyle(
                    fontFamily: 'SpaceMono',
                    fontSize: 13,
                    fontWeight: FontWeight.w400,
                    color: AppTheme.armorSlate,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
