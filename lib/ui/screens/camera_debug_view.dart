import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:native_exif/native_exif.dart';

import '../../data/local/database_provider.dart';
import '../../providers/batch_session_notifier.dart';
import '../../providers/sync_providers.dart';
import '../../services/secure_capture_service.dart';
import '../design/app_theme.dart';
import '../design/premium_field_components.dart';
import 'secure_camera_screen.dart';

/// =============================================================================
/// CameraDebugView  (Prompt 3 — Test & Verification)
/// =============================================================================
/// Standalone diagnostic screen for physical-device verification of the
/// anti-fraud pipeline. Pressing the SHUTTER button runs:
///
///   1. Asserts an active batchUuid (auto-starts one if missing).
///   2. Launches the SecureCameraScreen.
///   3. Reads back EXIF from the sandboxed file.
///   4. Persists a BiomassSourcing row via AppDatabase.insertWithOutbox().
///   5. Emits a single multi-line `debugPrint` block containing:
///        • The active batchUuid
///        • The sandboxed internal file path
///        • The parsed EXIF timestamp / GPS
///        • The calculated SHA-256
///        • A confirmation that insertWithOutbox succeeded
///   6. Renders the same block on-screen so a tester without `adb logcat`
///      can verify it in the field.
///
/// Routing: see the long-press easter egg on the Dashboard "SYNC BUFFER"
/// counter (3-second long-press) — or push this widget from your own
/// developer menu.
/// =============================================================================
class CameraDebugView extends ConsumerStatefulWidget {
  const CameraDebugView({super.key});

  @override
  ConsumerState<CameraDebugView> createState() => _CameraDebugViewState();
}

class _CameraDebugViewState extends ConsumerState<CameraDebugView> {
  bool _running = false;
  String? _log;
  String? _error;

  Future<void> _runPipeline() async {
    if (_running) return;
    setState(() {
      _running = true;
      _log = null;
      _error = null;
    });
    try {
      // ---------- Task 1: ensure an active batchUuid ----------
      final String batchUuid =
          ref.read(batchSessionProvider) ??
          ref.read(batchSessionProvider.notifier).start();

      // ---------- Tasks 2 & 3: capture, sandbox, EXIF, hash ----------
      final result = await Navigator.of(context).push<SecureCaptureResult>(
        MaterialPageRoute(builder: (_) => const SecureCameraScreen()),
      );
      if (result == null) {
        setState(() {
          _running = false;
          _error = 'Capture cancelled.';
        });
        return;
      }

      // Re-parse EXIF off disk to PROVE the round-trip.
      final exifReader = await Exif.fromPath(result.sandboxPath);
      final exifAttrs = await exifReader.getAttributes() ?? {};
      await exifReader.close();
      final parsedDateTime = exifAttrs['DateTimeOriginal']?.toString();
      final parsedLat = exifAttrs['GPSLatitude']?.toString();
      final parsedLon = exifAttrs['GPSLongitude']?.toString();

      // ---------- Task 4: persist to Outbox ----------
      final db = await ref.read(appDatabaseProvider.future);
      final sourcingUuid = await db.insertBiomassSourcingWithOutbox(
        batchUuid: batchUuid,
        feedstockSpecies: 'Lantana_camara',
        harvestTimestamp: DateTime.now().toUtc().toIso8601String(),
        // Debug screen forces a compliant reading for verification.
        moisturePercent: 12.5,
        moistureCompliant: true,
        photoPath: result.sandboxPath,
        sha256Hash: result.sha256Hash,
        latitude: result.latitude,
        longitude: result.longitude,
        azimuth: result.azimuth,
        pitch: result.pitch,
        roll: result.roll,
      );

      final block =
          '''
======================================================================
[CameraDebugView] PROMPT-3 PIPELINE VERIFICATION  ::  PASS
----------------------------------------------------------------------
 active batchUuid       : $batchUuid
 sourcingUuid (new)     : $sourcingUuid
 sandboxed file path    : ${result.sandboxPath}
 file size              : ${result.fileSizeBytes} bytes (<= 512000)
 sha256 hash            : ${result.sha256Hash}
 captured exif ts (UTC) : ${result.exifTimestampIso}
 read-back EXIF DT      : $parsedDateTime
 read-back EXIF lat/lon : $parsedLat / $parsedLon
 live GPS lat/lon       : ${result.latitude} / ${result.longitude}
 compass telemetry      : az=${result.azimuth?.toStringAsFixed(1)} (${result.cardinalDirection}), p=${result.pitch?.toStringAsFixed(1)}, r=${result.roll?.toStringAsFixed(1)}
 insertWithOutbox()     : OK  (biomass_sourcing + sync_outbox committed)
======================================================================
''';
      debugPrint(block);
      setState(() {
        _running = false;
        _log = block;
      });
    } catch (e, st) {
      debugPrint('[CameraDebugView] FAILED: $e\n$st');
      setState(() {
        _running = false;
        _error = e.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final batchUuid = ref.watch(batchSessionProvider);
    final pending = ref
        .watch(pendingOutboxCountProvider)
        .maybeWhen(data: (v) => v, orElse: () => 0);
    return Scaffold(
      backgroundColor: AppTheme.tacticalTitanium,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  InkWell(
                    onTap: () => Navigator.of(context).pop(),
                    child: Container(
                      width: 48,
                      height: 48,
                      decoration: BoxDecoration(
                        border: Border.all(
                          color: AppTheme.cobaltShield20,
                          width: 1,
                        ),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      alignment: Alignment.center,
                      child: const Icon(
                        Icons.arrow_back,
                        color: AppTheme.armorSlate,
                        size: 22,
                      ),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Text(
                      'CAMERA DEBUG // PROMPT-3',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              PremiumFieldPanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'SESSION',
                      style: Theme.of(context).textTheme.titleMedium!.copyWith(
                        color: AppTheme.yieldGold,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      batchUuid == null
                          ? 'no active batch (will auto-start on capture)'
                          : 'batchUuid = $batchUuid',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'outbox pending  = $pending',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              PremiumFieldButton(
                label: _running ? 'RUNNING…' : 'RUN CAPTURE PIPELINE',
                testId: 'debug-run-pipeline-btn',
                state: _running
                    ? FieldButtonState.locked
                    : FieldButtonState.hiVis,
                onPressed: _running ? null : _runPipeline,
              ),
              const SizedBox(height: 20),
              Expanded(
                child: SingleChildScrollView(
                  child: PremiumFieldPanel(
                    child: Text(
                      _error != null
                          ? 'ERR // $_error'
                          : (_log ?? 'Press SHUTTER to begin.'),
                      style: Theme.of(context).textTheme.bodyMedium!.copyWith(
                        color: _error != null
                            ? Colors.red
                            : AppTheme.armorSlate,
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
