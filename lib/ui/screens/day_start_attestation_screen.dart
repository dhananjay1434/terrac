import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:uuid/uuid.dart';

import '../../data/capture_types.dart';
import '../../data/local/database_provider.dart';
import '../../data/local/pyrolysis_writer.dart';
import '../../l10n/app_localizations.dart';
import '../../services/day_start_service.dart';
import '../../services/dispatch_service.dart';
import '../../services/secure_capture_service.dart';
import '../components/dmrv_button.dart';
import '../design/tokens.dart';
import 'secure_camera_screen.dart';

/// Deferred R6 + PR-5 — day-start audit lock, now with real evidence.
/// Full-screen, non-dismissible (no back button, no barrier dismiss): the
/// operator must explicitly attest all three items AND capture a facility
/// photo (walkthrough video optional) before the dashboard becomes usable
/// for the day. Pushed by [DashboardScreen] when [isDayStartValid] is
/// false; pops itself on confirm, revealing the dashboard underneath.
///
/// PR-5.2 — evidence is subject-scoped to a server-side `DayStartAudit`
/// record (audit_uuid), not the batch. The facility (nothing in the app
/// previously tracked "which facility does this device belong to") is
/// picked once via [DispatchService.fetchFacilities] and persisted for
/// future days. Server submission is best-effort/non-blocking: unlike
/// dispatch transitions, this gate must not brick the operator's day over
/// a network blip — see day_start_service.dart's submitAudit docstring.
class DayStartAttestationScreen extends ConsumerStatefulWidget {
  const DayStartAttestationScreen({super.key});

  @override
  ConsumerState<DayStartAttestationScreen> createState() =>
      _DayStartAttestationScreenState();
}

class _DayStartAttestationScreenState
    extends ConsumerState<DayStartAttestationScreen> {
  final String _auditUuid = const Uuid().v4();

  bool _clockChecked = false;
  bool _projectChecked = false;
  bool _calibrationChecked = false;
  bool _saving = false;

  bool _loadingFacilities = true;
  List<FacilityOption> _facilities = const [];
  String? _selectedFacilityUuid;

  bool _capturingMedia = false;
  String? _facilityPhotoMediaId;
  String? _walkthroughVideoMediaId;

  bool get _allChecked =>
      _clockChecked && _projectChecked && _calibrationChecked;

  bool get _canConfirm =>
      _allChecked &&
      _facilityPhotoMediaId != null &&
      _selectedFacilityUuid != null &&
      !_saving;

  @override
  void initState() {
    super.initState();
    _loadFacility();
  }

  Future<void> _loadFacility() async {
    final saved = await DayStartService.loadSelectedFacility();
    if (!mounted) return;
    if (saved != null) {
      setState(() {
        _selectedFacilityUuid = saved;
        _loadingFacilities = false;
      });
      return;
    }
    final facilities = await DispatchService.fetchFacilities();
    if (!mounted) return;
    setState(() {
      _facilities = facilities;
      _loadingFacilities = false;
    });
  }

  Future<void> _captureFacilityPhoto() async {
    if (_capturingMedia) return;
    setState(() => _capturingMedia = true);
    try {
      final result = await Navigator.of(context).push<SecureCaptureResult>(
        MaterialPageRoute<SecureCaptureResult>(
          builder: (_) => const SecureCameraScreen(),
        ),
      );
      if (result == null || !mounted) return;
      final db = await ref.read(appDatabaseProvider.future);
      final mediaId = await db.insertEntityMediaWithOutbox(
        subjectType: 'day_start_audit',
        subjectUuid: _auditUuid,
        captureType: CaptureType.dayStartFacilityPhoto,
        sandboxPath: result.sandboxPath,
        sha256Hash: result.sha256Hash,
        isMockLocation: result.isMocked,
      );
      if (!mounted) return;
      setState(() => _facilityPhotoMediaId = mediaId);
    } finally {
      if (mounted) setState(() => _capturingMedia = false);
    }
  }

  Future<void> _captureWalkthroughVideo() async {
    if (_capturingMedia) return;
    setState(() => _capturingMedia = true);
    try {
      final result = await Navigator.of(
        context,
      ).push<SecureVideoCaptureResult>(
        MaterialPageRoute<SecureVideoCaptureResult>(
          builder: (_) =>
              const SecureCameraScreen(captureMode: SecureCaptureMode.video),
        ),
      );
      if (result == null || !mounted) return;
      final db = await ref.read(appDatabaseProvider.future);
      final mediaId = await db.insertEntityMediaWithOutbox(
        subjectType: 'day_start_audit',
        subjectUuid: _auditUuid,
        captureType: CaptureType.dayStartWalkthroughVideo,
        sandboxPath: result.sandboxPath,
        sha256Hash: result.sha256Hash,
        isMockLocation: result.isMocked,
      );
      if (!mounted) return;
      setState(() => _walkthroughVideoMediaId = mediaId);
    } finally {
      if (mounted) setState(() => _capturingMedia = false);
    }
  }

  Future<void> _confirm() async {
    if (!_canConfirm) return;
    setState(() => _saving = true);
    final facilityUuid = _selectedFacilityUuid!;
    await DayStartService.saveSelectedFacility(facilityUuid);
    final now = DateTime.now();
    final auditDate =
        '${now.year.toString().padLeft(4, '0')}-'
        '${now.month.toString().padLeft(2, '0')}-'
        '${now.day.toString().padLeft(2, '0')}';
    // Best-effort — see submitAudit's docstring; never blocks confirm.
    await DayStartService.submitAudit(
      auditUuid: _auditUuid,
      facilityUuid: facilityUuid,
      auditDate: auditDate,
    );
    await DayStartService.saveAttestationNow();
    if (!mounted) return;
    Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final l = AppLocalizations.of(context)!;
    return PopScope(
      // Non-dismissible: no back-swipe/back-button escape. The operator
      // must confirm to proceed — there is no "skip for now".
      canPop: false,
      child: Scaffold(
        backgroundColor: t.surface,
        body: SafeArea(
          child: SingleChildScrollView(
            padding: EdgeInsets.all(t.gapL),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                SizedBox(height: t.gapXL),
                Text(
                  l.daystart_title,
                  style: t.screenTitle.copyWith(color: t.textPrimary),
                ),
                SizedBox(height: t.gapS),
                Text(
                  l.daystart_subtitle,
                  style: t.body.copyWith(color: t.textSecondary),
                ),
                SizedBox(height: t.gapXL),
                _facilityPicker(t, l),
                SizedBox(height: t.gapXL),
                _attestationTile(
                  t,
                  testId: 'daystart-clock-check',
                  label: l.daystart_clock_label,
                  value: _clockChecked,
                  onChanged: (v) => setState(() => _clockChecked = v ?? false),
                ),
                SizedBox(height: t.gapM),
                _attestationTile(
                  t,
                  testId: 'daystart-project-check',
                  label: l.daystart_project_label,
                  value: _projectChecked,
                  onChanged: (v) => setState(() => _projectChecked = v ?? false),
                ),
                SizedBox(height: t.gapM),
                _attestationTile(
                  t,
                  testId: 'daystart-calibration-check',
                  label: l.daystart_calibration_label,
                  value: _calibrationChecked,
                  onChanged: (v) =>
                      setState(() => _calibrationChecked = v ?? false),
                ),
                SizedBox(height: t.gapXL),
                DmrvButton(
                  label: _facilityPhotoMediaId != null
                      ? '✓ ${l.daystart_photo_captured_label}'
                      : l.daystart_photo_label,
                  testId: 'daystart-photo-capture-btn',
                  icon: _facilityPhotoMediaId != null
                      ? Icons.check_circle
                      : Icons.camera_alt,
                  variant: _facilityPhotoMediaId != null
                      ? DmrvButtonVariant.success
                      : DmrvButtonVariant.neutral,
                  onPressed: _capturingMedia ? null : _captureFacilityPhoto,
                ),
                SizedBox(height: t.gapM),
                DmrvButton(
                  label: _walkthroughVideoMediaId != null
                      ? '✓ ${l.daystart_video_captured_label}'
                      : l.daystart_video_label,
                  testId: 'daystart-video-capture-btn',
                  icon: _walkthroughVideoMediaId != null
                      ? Icons.check_circle
                      : Icons.videocam,
                  variant: _walkthroughVideoMediaId != null
                      ? DmrvButtonVariant.success
                      : DmrvButtonVariant.neutral,
                  onPressed: _capturingMedia ? null : _captureWalkthroughVideo,
                ),
                SizedBox(height: t.gapXL),
                DmrvButton(
                  label: _saving ? l.daystart_saving_label : l.daystart_confirm_button,
                  testId: 'daystart-confirm-btn',
                  variant: DmrvButtonVariant.primary,
                  onPressed: _canConfirm ? _confirm : null,
                ),
                SizedBox(height: t.gapL),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _facilityPicker(DmrvTokens t, AppLocalizations l) {
    if (_loadingFacilities) {
      return Text(
        l.daystart_facility_loading,
        style: t.body.copyWith(color: t.textSecondary),
      );
    }
    if (_selectedFacilityUuid != null) {
      final match = _facilities
          .where((f) => f.uuid == _selectedFacilityUuid)
          .toList();
      final name = match.isNotEmpty ? match.first.name : _selectedFacilityUuid!;
      return Text(
        '${l.daystart_facility_label}: $name',
        style: t.body.copyWith(color: t.textPrimary),
      );
    }
    if (_facilities.isEmpty) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            l.daystart_facility_none_found,
            style: t.body.copyWith(color: t.textSecondary),
          ),
          SizedBox(height: t.gapS),
          DmrvButton(
            label: l.daystart_facility_retry_button,
            testId: 'daystart-facility-retry-btn',
            variant: DmrvButtonVariant.neutral,
            onPressed: () {
              setState(() => _loadingFacilities = true);
              _loadFacility();
            },
          ),
        ],
      );
    }
    return Semantics(
      identifier: 'daystart-facility-picker',
      child: DropdownButtonFormField<String>(
        initialValue: null,
        decoration: InputDecoration(labelText: l.daystart_facility_label),
        hint: Text(l.daystart_facility_hint),
        items: _facilities
            .map((f) => DropdownMenuItem(value: f.uuid, child: Text(f.name)))
            .toList(),
        onChanged: (v) => setState(() => _selectedFacilityUuid = v),
      ),
    );
  }

  Widget _attestationTile(
    DmrvTokens t, {
    required String testId,
    required String label,
    required bool value,
    required ValueChanged<bool?> onChanged,
  }) {
    return Semantics(
      identifier: testId,
      child: CheckboxListTile(
        value: value,
        onChanged: onChanged,
        contentPadding: EdgeInsets.zero,
        controlAffinity: ListTileControlAffinity.leading,
        title: Text(label, style: t.body.copyWith(color: t.textPrimary)),
      ),
    );
  }
}
