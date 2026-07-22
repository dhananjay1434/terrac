import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/field_walk_link.dart';
import '../../services/field_walk_service.dart';
import '../../services/location_service.dart';
import '../components/dmrv_button.dart';
import '../design/premium_field_components.dart';
import '../design/tokens.dart';
import 'qr_scan_screen.dart';

/// V8 Part 5 (A phase-2) — ground-truthed boundary walk. Flow: scan the
/// admin-minted signed link (QR — reuses [QrScanScreen] from Part 5 L) →
/// verify it client-side → walk to each corner of the parcel and tap MARK
/// POINT (single GPS fixes via the existing [ILocationService], same
/// acquisition path secure capture uses — no continuous-stream/map
/// dependency was added for this) → submit once at least 3 corners are
/// marked → show the server's computed area + overlap-vs-declared.
class FieldWalkScreen extends ConsumerStatefulWidget {
  const FieldWalkScreen({super.key});

  @override
  ConsumerState<FieldWalkScreen> createState() => _FieldWalkScreenState();
}

enum _Stage { needLink, linkInvalid, walking, submitting, done, submitFailed }

class _FieldWalkScreenState extends ConsumerState<FieldWalkScreen> {
  FieldWalkLink? _link;
  _Stage _stage = _Stage.needLink;
  final List<List<double>> _points = [];
  bool _markingPoint = false;
  FieldWalkResult? _result;

  Future<void> _scanLink() async {
    final raw = await Navigator.of(context).push<String>(
      MaterialPageRoute<String>(
        builder: (_) => const QrScanScreen(title: 'SCAN FIELD-WALK LINK'),
      ),
    );
    if (raw == null || !mounted) return;

    final link = parseFieldWalkLink(raw);
    if (link == null) {
      setState(() => _stage = _Stage.linkInvalid);
      return;
    }
    final ok = await FieldWalkService.verifyLink(link);
    if (!mounted) return;
    if (!ok) {
      setState(() => _stage = _Stage.linkInvalid);
      return;
    }
    setState(() {
      _link = link;
      _points.clear();
      _stage = _Stage.walking;
    });
  }

  Future<void> _markPoint() async {
    if (_markingPoint) return;
    setState(() => _markingPoint = true);
    try {
      final pos = await ref.read(locationServiceProvider).acquirePosition();
      if (!mounted) return;
      setState(() {
        _points.add([pos.longitude, pos.latitude]);
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not get a GPS fix: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _markingPoint = false);
    }
  }

  void _undoLastPoint() {
    if (_points.isEmpty) return;
    setState(() => _points.removeLast());
  }

  Future<void> _submit() async {
    final link = _link;
    if (link == null || _points.length < 3) return;
    setState(() => _stage = _Stage.submitting);
    final result = await FieldWalkService.submit(link: link, points: _points);
    if (!mounted) return;
    setState(() {
      _result = result;
      _stage = result != null ? _Stage.done : _Stage.submitFailed;
    });
  }

  void _reset() {
    setState(() {
      _link = null;
      _points.clear();
      _result = null;
      _stage = _Stage.needLink;
    });
  }

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    return Scaffold(
      backgroundColor: t.surface,
      body: SafeArea(
        bottom: false,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            PremiumScreenHeader(
              stepNumber: 'FW',
              title: 'Field-Walk Boundary',
              onBack: () => Navigator.of(context).pop(),
            ),
            Expanded(
              child: Padding(
                padding: EdgeInsets.all(t.gapL),
                child: _buildBody(t),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBody(DmrvTokens t) {
    switch (_stage) {
      case _Stage.needLink:
        return Center(
          child: DmrvButton(
            label: 'SCAN FIELD-WALK LINK',
            testId: 'scan-field-walk-link-btn',
            variant: DmrvButtonVariant.primary,
            icon: Icons.qr_code_scanner,
            onPressed: _scanLink,
          ),
        );
      case _Stage.linkInvalid:
        return Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            PremiumFieldPanel(
              accentBorderColor: t.danger,
              child: Text(
                'This field-walk link is invalid or expired. Ask your '
                'project admin to mint a new one.',
                style: t.body.copyWith(color: t.textPrimary),
              ),
            ),
            SizedBox(height: t.gapL),
            DmrvButton(
              label: 'SCAN AGAIN',
              testId: 'field-walk-scan-again-btn',
              variant: DmrvButtonVariant.primary,
              onPressed: _scanLink,
            ),
          ],
        );
      case _Stage.walking:
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Walk to each corner of the parcel boundary and tap MARK '
              'POINT there. Mark at least 3 corners, in order, then Submit.',
              style: t.body.copyWith(color: t.textSecondary),
            ),
            SizedBox(height: t.gapL),
            Semantics(
              identifier: 'field-walk-point-count',
              child: Text(
                '${_points.length} point${_points.length == 1 ? '' : 's'} marked',
                style: t.screenTitle.copyWith(color: t.accentText),
              ),
            ),
            SizedBox(height: t.gapL),
            DmrvButton(
              label: _markingPoint ? 'GETTING GPS FIX…' : 'MARK POINT',
              testId: 'field-walk-mark-point-btn',
              variant: DmrvButtonVariant.primary,
              icon: Icons.add_location_alt,
              onPressed: _markingPoint ? null : _markPoint,
            ),
            SizedBox(height: t.gapM),
            DmrvButton(
              label: 'UNDO LAST POINT',
              testId: 'field-walk-undo-btn',
              variant: DmrvButtonVariant.neutral,
              onPressed: _points.isEmpty ? null : _undoLastPoint,
            ),
            const Spacer(),
            DmrvButton(
              label: 'SUBMIT WALK',
              testId: 'field-walk-submit-btn',
              variant: DmrvButtonVariant.success,
              onPressed: _points.length >= 3 ? _submit : null,
            ),
          ],
        );
      case _Stage.submitting:
        return const Center(child: CircularProgressIndicator());
      case _Stage.done:
        final r = _result!;
        final overlapPct = r.overlapRatioVsDeclared != null
            ? '${(r.overlapRatioVsDeclared! * 100).toStringAsFixed(1)}%'
            : 'not computed';
        return Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.check_circle, color: t.success, size: 48),
            SizedBox(height: t.gapM),
            Semantics(
              identifier: 'field-walk-result',
              child: Text(
                'Walked area: ${r.computedAreaM2.toStringAsFixed(0)} m²\n'
                'Overlap with declared boundary: $overlapPct',
                textAlign: TextAlign.center,
                style: t.body.copyWith(color: t.textPrimary),
              ),
            ),
            SizedBox(height: t.gapL),
            DmrvButton(
              label: 'DONE',
              testId: 'field-walk-done-btn',
              variant: DmrvButtonVariant.primary,
              onPressed: () => Navigator.of(context).pop(),
            ),
          ],
        );
      case _Stage.submitFailed:
        return Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            PremiumFieldPanel(
              accentBorderColor: t.danger,
              child: Text(
                'Could not submit the walk — check connectivity and try '
                'again. Your marked points are preserved.',
                style: t.body.copyWith(color: t.textPrimary),
              ),
            ),
            SizedBox(height: t.gapL),
            DmrvButton(
              label: 'RETRY SUBMIT',
              testId: 'field-walk-retry-submit-btn',
              variant: DmrvButtonVariant.primary,
              onPressed: () => setState(() => _stage = _Stage.walking),
            ),
            SizedBox(height: t.gapM),
            DmrvButton(
              label: 'START OVER',
              testId: 'field-walk-start-over-btn',
              variant: DmrvButtonVariant.neutral,
              onPressed: _reset,
            ),
          ],
        );
    }
  }
}
