import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:uuid/uuid.dart';

import '../../../data/capture_types.dart';
import '../../../data/local/database_provider.dart';
import '../../../data/local/pyrolysis_writer.dart';
import '../../../services/dispatch_service.dart';
import '../../../services/secure_capture_service.dart';
import '../../components/dmrv_button.dart';
import '../../design/tokens.dart';
import '../secure_camera_screen.dart';

/// V8 Part 3.4 — dispatch capture: create a draft custody-transfer shipment,
/// Submit (locks the source weight), and Mark as Received (facility re-weigh
/// + dual-weigh reconciliation). One screen, three phases, same session.
///
/// Deferred R1 — truck/invoice photos and the weigh ticket ARE captured here
/// once a draft exists (entity-scoped media via
/// `insertEntityMediaWithOutbox`, subject-scoped to this dispatch's uuid).
/// Each is optional and shows "not captured" until present.
///
/// Session-scoped by design: the in-progress draft/in_transit state lives in
/// this screen's memory, not persisted across app restarts. If the app is
/// killed mid-flow, the DRAFT itself is safe (already queued to the outbox
/// and will sync), but the operator must re-open it from the portal/next
/// screen visit to continue Submit/Receive — a smaller, explicit limitation
/// rather than a silently lost multi-step wizard.
class DispatchScreen extends ConsumerStatefulWidget {
  const DispatchScreen({super.key});

  @override
  ConsumerState<DispatchScreen> createState() => _DispatchScreenState();
}

enum _Phase { draft, inTransit, received }

// Deferred R2 — string currency shared with resolveResumePhase/the server's
// status field (which uses these exact strings).
String _phaseToStatus(_Phase p) => switch (p) {
      _Phase.draft => 'draft',
      _Phase.inTransit => 'in_transit',
      _Phase.received => 'received',
    };

_Phase _phaseFromStatus(String s) => switch (s) {
      'in_transit' => _Phase.inTransit,
      'received' => _Phase.received,
      _ => _Phase.draft,
    };

class _DispatchScreenState extends ConsumerState<DispatchScreen> {
  final _weightSource = TextEditingController();
  final _weightMethod = TextEditingController();
  final _driverName = TextEditingController();
  final _driverPhone = TextEditingController();
  final _truckNumber = TextEditingController();
  final _weightFacility = TextEditingController();

  String _kind = 'biomass';
  String? _dispatchUuid;
  FacilityOption? _selectedFacility;
  List<FacilityOption> _facilities = const [];
  _Phase _phase = _Phase.draft;
  bool _busy = false;
  bool? _lastFlagged;
  double? _lastDeltaPct;

  // Deferred R1 — dispatch media (truck/invoice photos, weigh ticket).
  String? _truckPhotoMediaId;
  String? _invoicePhotoMediaId;
  String? _weighTicketMediaId;
  bool _capturingMedia = false;

  // Deferred R2 — restart-resilience.
  bool _resumeBannerVisible = false;

  @override
  void initState() {
    super.initState();
    _loadFacilities();
    _resumeInFlightDispatch();
  }

  /// Deferred R2 — on launch, if a wizard was mid-flow when the app was
  /// killed, restore it: reconcile the persisted phase against server truth
  /// (server always wins — see resolveResumePhase's doc) and show a
  /// dismissible banner. A dispatch with no persisted state is untouched
  /// (fresh screen, no banner).
  Future<void> _resumeInFlightDispatch() async {
    final persisted = await DispatchService.loadInFlightDispatch();
    if (persisted == null) return;
    final (uuid, persistedPhase) = persisted;
    final serverStatus = await DispatchService.fetchStatus(dispatchUuid: uuid);
    final resolvedPhase = resolveResumePhase(
      persistedPhase: persistedPhase,
      serverStatus: serverStatus,
    );
    if (!mounted) return;
    setState(() {
      _dispatchUuid = uuid;
      _phase = _phaseFromStatus(resolvedPhase);
      _resumeBannerVisible = true;
    });
    // Keep the persisted record in sync with whatever we just resolved to
    // (e.g. server had already advanced past the stale local value) so a
    // SECOND kill-and-resume doesn't re-reconcile from stale data.
    await DispatchService.saveInFlightDispatch(uuid, resolvedPhase);
  }

  @override
  void dispose() {
    for (final c in [
      _weightSource,
      _weightMethod,
      _driverName,
      _driverPhone,
      _truckNumber,
      _weightFacility,
    ]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _loadFacilities() async {
    final facilities = await DispatchService.fetchFacilities();
    if (mounted) setState(() => _facilities = facilities);
  }

  double? _parsePositive(String s) {
    final v = double.tryParse(s.trim());
    return (v != null && v > 0) ? v : null;
  }

  Future<void> _createDraft() async {
    final weight = _parsePositive(_weightSource.text);
    if (weight == null) {
      _snack('Enter a valid source weight (kg) greater than zero.');
      return;
    }
    setState(() => _busy = true);
    try {
      final db = await ref.read(appDatabaseProvider.future);
      final uuid = const Uuid().v4();
      await db.insertDispatchWithOutbox(
        dispatchUuid: uuid,
        kind: _kind,
        destFacilityUuid: _selectedFacility?.uuid,
        weightSourceKg: weight,
        weightSourceMethod:
            _weightMethod.text.trim().isEmpty ? null : _weightMethod.text.trim(),
        driverName: _driverName.text.trim().isEmpty ? null : _driverName.text.trim(),
        driverPhone:
            _driverPhone.text.trim().isEmpty ? null : _driverPhone.text.trim(),
        truckNumber:
            _truckNumber.text.trim().isEmpty ? null : _truckNumber.text.trim(),
      );
      await DispatchService.saveInFlightDispatch(uuid, _phaseToStatus(_Phase.draft));
      if (!mounted) return;
      setState(() {
        _dispatchUuid = uuid;
      });
      _snack('Dispatch draft saved — queued for sync.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// Deferred R1 — capture a dispatch-scoped media artifact. Only callable
  /// once a draft exists (needs a real dispatch_uuid to attach to).
  Future<void> _captureDispatchMedia({
    required String captureType,
    required void Function(String mediaId) onCaptured,
  }) async {
    final dispatchUuid = _dispatchUuid;
    if (dispatchUuid == null || _capturingMedia) return;
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
        subjectType: 'dispatch',
        subjectUuid: dispatchUuid,
        captureType: captureType,
        sandboxPath: result.sandboxPath,
        sha256Hash: result.sha256Hash,
        isMockLocation: result.isMocked,
      );
      if (!mounted) return;
      setState(() => onCaptured(mediaId));
    } finally {
      if (mounted) setState(() => _capturingMedia = false);
    }
  }

  Future<void> _confirmSubmit() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Submit dispatch?'),
        content: const Text(
          'Once submitted, the source weight is LOCKED — you cannot change it '
          'afterward. The shipment moves to In-Transit.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Submit'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    await _submit();
  }

  Future<void> _submit() async {
    final uuid = _dispatchUuid;
    if (uuid == null) return;
    setState(() => _busy = true);
    try {
      final result = await DispatchService.transition(
        dispatchUuid: uuid,
        targetStatus: 'in_transit',
      );
      if (!mounted) return;
      if (result == null) {
        _snack(
          'Could not submit — check connectivity. The draft is safe and will '
          'sync; try Submit again once online.',
        );
        return;
      }
      await DispatchService.saveInFlightDispatch(uuid, _phaseToStatus(_Phase.inTransit));
      setState(() => _phase = _Phase.inTransit);
      _snack('Submitted — In-Transit. Weight is now locked.');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _confirmReceive() async {
    final weight = _parsePositive(_weightFacility.text);
    if (weight == null) {
      _snack('Enter a valid facility re-weigh (kg) greater than zero.');
      return;
    }
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Mark as Received?'),
        content: const Text(
          'This records the facility re-weigh and closes the shipment. This '
          'cannot be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Mark as Received'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    await _receive(weight);
  }

  Future<void> _receive(double weight) async {
    final uuid = _dispatchUuid;
    if (uuid == null) return;
    setState(() => _busy = true);
    try {
      final result = await DispatchService.transition(
        dispatchUuid: uuid,
        targetStatus: 'received',
        weightFacilityKg: weight,
      );
      if (!mounted) return;
      if (result == null) {
        _snack('Could not mark received — check connectivity and try again.');
        return;
      }
      await DispatchService.clearInFlightDispatch();
      setState(() {
        _phase = _Phase.received;
        _lastFlagged = result.weightFlagged;
        _lastDeltaPct = result.weightDeltaPct;
      });
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _snack(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    return Scaffold(
      backgroundColor: t.surface,
      appBar: AppBar(
        backgroundColor: t.surface,
        elevation: 0,
        iconTheme: IconThemeData(color: t.textPrimary),
        title: Text('Dispatch', style: t.blockHeader.copyWith(color: t.textPrimary)),
      ),
      body: SafeArea(
        child: ListView(
          padding: EdgeInsets.fromLTRB(t.gapL, t.gapM, t.gapL, t.gapL),
          children: [
            if (_resumeBannerVisible) ...[
              _resumeBanner(t),
              SizedBox(height: t.gapL),
            ],
            if (_phase == _Phase.draft) ..._draftForm(t),
            if (_phase == _Phase.inTransit) ..._inTransitSection(t),
            if (_phase == _Phase.received) ..._receivedSection(t),
          ],
        ),
      ),
    );
  }

  /// Deferred R2 — dismissible, consequence-free banner: the resumed state
  /// is already correct (reconciled against server truth), this just tells
  /// the operator what happened.
  Widget _resumeBanner(DmrvTokens t) {
    return Container(
      width: double.infinity,
      padding: EdgeInsets.all(t.gapM),
      decoration: BoxDecoration(
        color: t.surfaceRaised,
        borderRadius: BorderRadius.circular(t.radiusM),
        border: Border.all(color: t.border, width: 1),
      ),
      child: Row(
        children: [
          Icon(Icons.history, color: t.accentText, size: 20),
          SizedBox(width: t.gapM),
          Expanded(
            child: Semantics(
              identifier: 'dispatch-resume-banner',
              child: Text(
                'Resumed your in-progress dispatch.',
                style: t.body.copyWith(color: t.textPrimary),
              ),
            ),
          ),
          IconButton(
            icon: Icon(Icons.close, color: t.textSecondary, size: 18),
            tooltip: 'Dismiss',
            onPressed: () => setState(() => _resumeBannerVisible = false),
          ),
        ],
      ),
    );
  }

  List<Widget> _draftForm(DmrvTokens t) {
    return [
      Text('New Dispatch', style: t.screenTitle.copyWith(color: t.textPrimary)),
      SizedBox(height: t.gapS),
      Text(
        'Record a shipment of biomass or biochar moving to a facility.',
        style: t.body.copyWith(color: t.textSecondary),
      ),
      SizedBox(height: t.gapXL),
      _section(t, 'KIND'),
      Row(
        children: [
          Expanded(
            child: _kindChip(t, 'biomass', 'Biomass'),
          ),
          SizedBox(width: t.gapM),
          Expanded(
            child: _kindChip(t, 'biochar', 'Biochar'),
          ),
        ],
      ),
      SizedBox(height: t.gapXL),
      _section(t, 'SOURCE WEIGHT (LOCKS ON SUBMIT)'),
      _field(t, _weightSource, 'dispatch-weight-source', 'kg', keyboardType: TextInputType.number),
      SizedBox(height: t.gapL),
      _field(t, _weightMethod, 'dispatch-weight-method', 'e.g. platform_scale'),
      SizedBox(height: t.gapXL),
      _section(t, 'DESTINATION FACILITY'),
      _facilityPicker(t),
      SizedBox(height: t.gapXL),
      _section(t, 'DRIVER & TRUCK (OPTIONAL)'),
      _field(t, _driverName, 'dispatch-driver-name', 'Driver name'),
      SizedBox(height: t.gapL),
      _field(t, _driverPhone, 'dispatch-driver-phone', 'Driver phone'),
      SizedBox(height: t.gapL),
      _field(t, _truckNumber, 'dispatch-truck-number', 'Truck number'),
      SizedBox(height: t.gapXL),
      if (_dispatchUuid == null)
        DmrvButton(
          label: _busy ? 'SAVING…' : 'SAVE DRAFT',
          testId: 'dispatch-save-draft-btn',
          variant: DmrvButtonVariant.primary,
          onPressed: _busy ? null : _createDraft,
        )
      else ...[
        Text(
          'Draft saved. Review the details above, then submit to lock the '
          'weight and move to In-Transit.',
          style: t.body.copyWith(color: t.success),
        ),
        SizedBox(height: t.gapXL),
        _section(t, 'EVIDENCE (OPTIONAL)'),
        _mediaCaptureRow(
          t,
          label: 'TRUCK PHOTO',
          testId: 'dispatch-capture-truck',
          captured: _truckPhotoMediaId != null,
          onPressed: () => _captureDispatchMedia(
            captureType: CaptureType.dispatchTruckPhoto,
            onCaptured: (id) => _truckPhotoMediaId = id,
          ),
        ),
        SizedBox(height: t.gapL),
        _mediaCaptureRow(
          t,
          label: 'INVOICE PHOTO',
          testId: 'dispatch-capture-invoice',
          captured: _invoicePhotoMediaId != null,
          onPressed: () => _captureDispatchMedia(
            captureType: CaptureType.dispatchInvoicePhoto,
            onCaptured: (id) => _invoicePhotoMediaId = id,
          ),
        ),
        SizedBox(height: t.gapL),
        _mediaCaptureRow(
          t,
          label: 'WEIGH TICKET',
          testId: 'dispatch-capture-weigh-ticket',
          captured: _weighTicketMediaId != null,
          onPressed: () => _captureDispatchMedia(
            captureType: CaptureType.dispatchWeighTicket,
            onCaptured: (id) => _weighTicketMediaId = id,
          ),
        ),
        SizedBox(height: t.gapXL),
        DmrvButton(
          label: _busy ? 'SUBMITTING…' : 'SUBMIT (LOCK WEIGHT)',
          testId: 'dispatch-submit-btn',
          variant: DmrvButtonVariant.primary,
          onPressed: _busy ? null : _confirmSubmit,
        ),
      ],
    ];
  }

  List<Widget> _inTransitSection(DmrvTokens t) {
    return [
      Text('In-Transit', style: t.screenTitle.copyWith(color: t.textPrimary)),
      SizedBox(height: t.gapS),
      Text(
        'Source weight is locked. When the shipment arrives, record the '
        "facility's re-weigh to mark it received.",
        style: t.body.copyWith(color: t.textSecondary),
      ),
      SizedBox(height: t.gapXL),
      _section(t, 'FACILITY RE-WEIGH'),
      _field(t, _weightFacility, 'dispatch-weight-facility', 'kg', keyboardType: TextInputType.number),
      SizedBox(height: t.gapXL),
      DmrvButton(
        label: _busy ? 'SUBMITTING…' : 'MARK AS RECEIVED',
        testId: 'dispatch-receive-btn',
        variant: DmrvButtonVariant.primary,
        onPressed: _busy ? null : _confirmReceive,
      ),
    ];
  }

  List<Widget> _receivedSection(DmrvTokens t) {
    final flagged = _lastFlagged == true;
    return [
      Text('Received', style: t.screenTitle.copyWith(color: t.textPrimary)),
      SizedBox(height: t.gapL),
      Container(
        padding: EdgeInsets.all(t.gapL),
        decoration: BoxDecoration(
          color: (flagged ? t.danger : t.success).withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(t.radiusM),
        ),
        child: Text(
          flagged
              ? 'Weight discrepancy flagged for review: '
                  '${_lastDeltaPct?.toStringAsFixed(1) ?? "?"}% delta between '
                  'source and facility weights.'
              : 'Weights reconcile within tolerance. Shipment closed.',
          style: t.body.copyWith(color: flagged ? t.danger : t.success),
        ),
      ),
    ];
  }

  Widget _kindChip(DmrvTokens t, String value, String label) {
    final selected = _kind == value;
    return GestureDetector(
      onTap: () => setState(() => _kind = value),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12),
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: selected ? t.accent.withValues(alpha: 0.12) : t.surface,
          borderRadius: BorderRadius.circular(t.radiusM),
          border: Border.all(color: selected ? t.accent : t.border),
        ),
        child: Text(
          label,
          style: t.body.copyWith(color: selected ? t.accentText : t.textSecondary),
        ),
      ),
    );
  }

  Widget _facilityPicker(DmrvTokens t) {
    return Material(
      color: t.surface,
      borderRadius: BorderRadius.circular(t.radiusM),
      child: InkWell(
        borderRadius: BorderRadius.circular(t.radiusM),
        onTap: _facilities.isEmpty
            ? null
            : () async {
                final selected = await showModalBottomSheet<FacilityOption>(
                  context: context,
                  builder: (ctx) => SafeArea(
                    child: ListView(
                      shrinkWrap: true,
                      children: [
                        for (final f in _facilities)
                          ListTile(
                            title: Text(f.name),
                            subtitle: Text(f.type),
                            onTap: () => Navigator.of(ctx).pop(f),
                          ),
                      ],
                    ),
                  ),
                );
                if (selected != null) setState(() => _selectedFacility = selected);
              },
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(t.radiusM),
            border: Border.all(color: t.border),
          ),
          child: Row(
            children: [
              Expanded(
                child: Semantics(
                  identifier: 'dispatch-facility-selector',
                  child: Text(
                    _selectedFacility?.name ??
                        (_facilities.isEmpty
                            ? 'No facilities available'
                            : 'Select destination facility'),
                    style: t.body.copyWith(color: t.textPrimary),
                  ),
                ),
              ),
              Icon(Icons.chevron_right, color: t.textSecondary),
            ],
          ),
        ),
      ),
    );
  }

  Widget _section(DmrvTokens t, String label) => Padding(
        padding: EdgeInsets.only(bottom: t.gapM),
        child: Text(label, style: t.chipLabel.copyWith(color: t.accentText)),
      );

  /// Deferred R1 — one row for an optional dispatch media capture. Shows
  /// "not captured" until present; capturing never blocks Submit/Receive.
  Widget _mediaCaptureRow(
    DmrvTokens t, {
    required String label,
    required String testId,
    required bool captured,
    required VoidCallback onPressed,
  }) {
    return DmrvButton(
      label: captured ? '✓ ${label.toUpperCase()}' : 'CAPTURE ${label.toUpperCase()}',
      testId: testId,
      icon: captured ? Icons.check_circle : Icons.camera_alt,
      variant: captured ? DmrvButtonVariant.success : DmrvButtonVariant.neutral,
      onPressed: _capturingMedia ? null : onPressed,
    );
  }

  Widget _field(
    DmrvTokens t,
    TextEditingController controller,
    String testId,
    String hint, {
    TextInputType? keyboardType,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      decoration: BoxDecoration(
        color: t.surface,
        borderRadius: BorderRadius.circular(t.radiusM),
        border: Border.all(color: t.border, width: 1),
      ),
      child: Semantics(
        identifier: testId,
        textField: true,
        child: TextField(
          controller: controller,
          keyboardType: keyboardType,
          autocorrect: false,
          enableSuggestions: false,
          cursorColor: t.accentText,
          style: t.body.copyWith(color: t.textPrimary),
          decoration: InputDecoration(
            border: InputBorder.none,
            isCollapsed: true,
            contentPadding: const EdgeInsets.symmetric(vertical: 12),
            hintText: hint,
            hintStyle: t.body.copyWith(color: t.textDisabled),
          ),
        ),
      ),
    );
  }
}
