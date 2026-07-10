import 'package:drift/drift.dart' hide Column, Table;
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../../data/local/database_provider.dart';
import '../../providers/batch_session_notifier.dart';
import '../../services/secure_capture_service.dart';
import '../components/dmrv_button.dart';
import '../design/premium_field_components.dart';
import '../design/tokens.dart';
import '../widgets/integrity_footer.dart';
import 'end_use_application_screen.dart';
import 'secure_camera_screen.dart';

/// Rainbow compliance C4 chain-of-custody value carried on the batch QR card and
/// stored on each composite sample. Versioned so the P2 lab scanner can parse it.
String batchQrValue(String batchUuid) => 'dmrv-batch:v1:$batchUuid';

/// Live count of PHOTOGRAPHED composite-pile sub-samples for the active batch —
/// the C4 gate needs at least one. A sample counts once it carries a photo hash.
final compositeSampleCountProvider = StreamProvider.autoDispose<int>((
  ref,
) async* {
  final batchUuid = ref.watch(batchSessionProvider);
  if (batchUuid == null) {
    yield 0;
    return;
  }
  final db = await ref.watch(appDatabaseProvider.future);
  final tbl = db.compositePileSamples;
  final query = db.selectOnly(tbl)
    ..addColumns([tbl.id.count()])
    ..where(tbl.batchUuid.equals(batchUuid) & tbl.sha256Hash.isNotNull());
  yield* query.map((r) => r.read(tbl.id.count()) ?? 0).watchSingle();
});

/// C4 site composite pile sub-sample capture. The operator photographs one (or
/// more) sub-samples alongside the batch QR card; ≥1 photographed sample is
/// required to continue to the end-use step.
class CompositeSampleScreen extends ConsumerStatefulWidget {
  const CompositeSampleScreen({super.key});

  @override
  ConsumerState<CompositeSampleScreen> createState() =>
      _CompositeSampleScreenState();
}

class _CompositeSampleScreenState extends ConsumerState<CompositeSampleScreen> {
  bool _busy = false;
  String? _err;

  Future<void> _captureSample() async {
    if (_busy) return;
    final result = await Navigator.of(context).push<SecureCaptureResult>(
      MaterialPageRoute(builder: (_) => const SecureCameraScreen()),
    );
    if (result == null) return;

    setState(() {
      _busy = true;
      _err = null;
    });
    try {
      final batchUuid = ref.read(batchSessionProvider);
      if (batchUuid == null) throw StateError('No active batch.');
      final db = await ref.read(appDatabaseProvider.future);
      await db.insertCompositePileSampleWithOutbox(
        batchUuid: batchUuid,
        sampledAt: DateTime.now().toUtc().toIso8601String(),
        latitude: result.latitude,
        longitude: result.longitude,
        batchQr: batchQrValue(batchUuid),
        photoPath: result.sandboxPath,
        sha256Hash: result.sha256Hash,
      );
    } catch (e) {
      if (mounted) setState(() => _err = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _continue() {
    Navigator.of(context).pushReplacement(
      MaterialPageRoute<void>(builder: (_) => const EndUseApplicationScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final batchUuid = ref.watch(batchSessionProvider);
    final count = ref.watch(compositeSampleCountProvider).valueOrNull ?? 0;
    final canContinue = count >= 1;

    return Scaffold(
      backgroundColor: t.surface,
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            PremiumScreenHeader(
              stepNumber: '04',
              title: 'Composite Sample',
              onBack: () => Navigator.of(context).pop(),
            ),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
                children: [
                  _instructions(t),
                  const SizedBox(height: 16),
                  if (batchUuid != null) _qrCard(t, batchUuid),
                  const SizedBox(height: 16),
                  _counterHero(t, count),
                  const SizedBox(height: 16),
                  DmrvButton(
                    label: _busy ? 'SAVING…' : 'CAPTURE SAMPLE PHOTO',
                    testId: 'capture-composite-sample-btn',
                    icon: Icons.camera_alt,
                    variant: DmrvButtonVariant.primary,
                    onPressed: _busy ? null : _captureSample,
                  ),
                  if (count >= 1) ...[
                    const SizedBox(height: 8),
                    Text(
                      'One sample is enough. Capture more only if your run '
                      'produced multiple piles.',
                      style: t.metadata.copyWith(
                        fontSize: 13,
                        color: t.textSecondary,
                      ),
                    ),
                  ],
                  if (_err != null) ...[
                    const SizedBox(height: 16),
                    Text(
                      _err!,
                      style: t.metadata.copyWith(fontSize: 13, color: t.danger),
                    ),
                  ],
                  const SizedBox(height: 24),
                  DmrvButton(
                    label: canContinue
                        ? 'CONTINUE TO END-USE'
                        : 'LOCKED // CAPTURE ≥1 SAMPLE',
                    testId: 'composite-continue-btn',
                    variant: DmrvButtonVariant.success,
                    onPressed: canContinue ? _continue : null,
                  ),
                  const SizedBox(height: 12),
                ],
              ),
            ),
            IntegrityFooter(
              lastHash:
                  '----------------------------------------------------------------',
            ),
          ],
        ),
      ),
    );
  }

  Widget _instructions(DmrvTokens t) {
    return PremiumFieldPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'SITE COMPOSITE SAMPLE',
            style: t.chipLabel.copyWith(color: t.accentText),
          ),
          const SizedBox(height: 8),
          Text(
            'Set aside a composite sub-sample of the biochar pile in a labelled '
            'bag. Place the bag with the batch QR card below in frame, then '
            'photograph it. This links the physical sample to this batch for '
            'the lab.',
            style: t.body.copyWith(color: t.textPrimary),
          ),
        ],
      ),
    );
  }

  Widget _qrCard(DmrvTokens t, String batchUuid) {
    return PremiumFieldPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Text(
            'BATCH QR — CHAIN OF CUSTODY',
            style: t.chipLabel.copyWith(color: t.accentText),
          ),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(12),
            color: Colors.white,
            child: QrImageView(
              data: batchQrValue(batchUuid),
              version: QrVersions.auto,
              size: 200,
              gapless: true,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            batchUuid,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: t.metadata.copyWith(fontSize: 12, color: t.textSecondary),
          ),
        ],
      ),
    );
  }

  Widget _counterHero(DmrvTokens t, int count) {
    return PremiumFieldPanel(
      accentBorderColor: count >= 1 ? t.success : null,
      child: Row(
        children: [
          Expanded(
            child: Text(
              'SAMPLES CAPTURED',
              style: t.chipLabel.copyWith(color: t.textSecondary),
            ),
          ),
          Text(
            '$count',
            style: t.numericMedium.copyWith(
              color: count >= 1 ? t.success : t.textPrimary,
            ),
          ),
        ],
      ),
    );
  }
}
