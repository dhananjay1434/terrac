import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';

import '../../data/capture_types.dart';
import '../../data/local/database_provider.dart';
import '../../data/local/pyrolysis_writer.dart';
import '../../l10n/app_localizations.dart';
import '../../services/ifsc_lookup_service.dart';
import '../../services/pincode_lookup_service.dart';
import '../../services/secure_capture_service.dart';
import '../components/dmrv_button.dart';
import '../design/tokens.dart';
import 'secure_camera_screen.dart';

/// V8 Part 2 — real farmer registration (replaces the `// TODO` stub that
/// saved nothing). Collects the structured farmer record + an optional masked
/// payment method + an FPIC consent acknowledgement, and enqueues it to the
/// sync outbox (→ POST /api/v1/farmers), where it appears in the verifier
/// portal's Farmers page.
///
/// PII discipline:
///  - the account number is MASKED on-device (last-4 kept) before it is ever
///    persisted or sent — the full number never leaves the phone;
///  - identity-document PHOTOS and the FPIC signed-PDF/holding-photo ARE
///    captured here (deferred R1 — entity-scoped media via
///    `insertEntityMediaWithOutbox`, subject-scoped to this farmer's uuid).
///    Each is optional and shows "not captured" until present — capturing
///    media never blocks saving the farmer record (offline-first).
///
/// V8 Part 4 (J, field-UX pack) additions:
///  - pincode → district/state auto-fill (api.postalpincode.in);
///  - IFSC → bank/branch confirmation (ifsc.razorpay.com);
///  - save-to-draft: fields persist locally as the operator types and are
///    offered back if the screen is re-opened before submission — an
///    interrupted registration (call, low battery, app switch) is not lost.
class FarmerKycScreen extends ConsumerStatefulWidget {
  const FarmerKycScreen({super.key});

  @override
  ConsumerState<FarmerKycScreen> createState() => _FarmerKycScreenState();
}

class _FarmerKycScreenState extends ConsumerState<FarmerKycScreen> {
  static const _projectId = String.fromEnvironment('DMRV_PROJECT_ID');
  static const _draftPrefsKey = 'dmrv.farmer_kyc_draft.v1';

  final _firstName = TextEditingController();
  final _lastName = TextEditingController();
  final _guardian = TextEditingController();
  final _mobile = TextEditingController();
  final _village = TextEditingController();
  final _pincode = TextEditingController();
  final _accountHolder = TextEditingController();
  final _accountNumber = TextEditingController();
  final _ifsc = TextEditingController();

  bool _fpicAck = false;
  bool _submitting = false;
  bool _draftRestoredBannerVisible = false;

  // Deferred R1 — entity-scoped media. Generated ONCE per screen instance
  // (not at submit time, unlike before) so media captured before the farmer
  // record is submitted attaches to the SAME farmer_uuid the eventual
  // insertFarmerWithOutbox call uses — persisted in the draft so a restored
  // draft session doesn't orphan already-captured media under a fresh uuid.
  late String _farmerUuid;
  String? _signatureMediaId;
  String? _idDocMediaId;
  String? _fpicPdfMediaId;
  String? _fpicHoldingPhotoMediaId;
  String? _idDocType; // 'aadhaar' | 'pan' | 'passport' | 'nid'
  final _idDocLast4 = TextEditingController();
  bool _capturingMedia = false;

  bool _pincodeLookupBusy = false;
  PincodeLookupResult? _pincodeResult;
  String? _pincodeError;

  bool _ifscLookupBusy = false;
  IfscLookupResult? _ifscResult;
  String? _ifscError;

  final _fieldControllers = <String, TextEditingController>{};

  @override
  void initState() {
    super.initState();
    _farmerUuid = const Uuid().v4();
    _fieldControllers.addAll({
      'first_name': _firstName,
      'last_name': _lastName,
      'guardian': _guardian,
      'mobile': _mobile,
      'village': _village,
      'pincode': _pincode,
      'account_holder': _accountHolder,
      'account_number': _accountNumber,
      'ifsc': _ifsc,
      'id_doc_last4': _idDocLast4,
    });
    for (final c in _fieldControllers.values) {
      c.addListener(_saveDraft);
    }
    _loadDraft();
  }

  @override
  void dispose() {
    for (final c in _fieldControllers.values) {
      c.removeListener(_saveDraft);
      c.dispose();
    }
    super.dispose();
  }

  bool get _canSubmit =>
      _firstName.text.trim().isNotEmpty &&
      _mobile.text.trim().isNotEmpty &&
      _projectId.isNotEmpty &&
      !_submitting;

  // ---------------------------------------------------------------------
  // Save-to-draft (V8 Part 4 J)
  // ---------------------------------------------------------------------

  Future<void> _loadDraft() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_draftPrefsKey);
    if (raw == null || raw.isEmpty) return;
    try {
      final saved = jsonDecode(raw) as Map<String, dynamic>;
      for (final entry in _fieldControllers.entries) {
        final value = saved[entry.key];
        if (value is String && value.isNotEmpty) {
          entry.value.text = value;
        }
      }
      final ack = saved['fpic_ack'];
      // Deferred R1 — restore the SAME farmer_uuid + already-captured media
      // ids, so re-opening an interrupted registration doesn't orphan media
      // captured under a now-abandoned uuid.
      final savedFarmerUuid = saved['farmer_uuid'];
      if (mounted) {
        setState(() {
          _fpicAck = ack == true;
          _draftRestoredBannerVisible = true;
          if (savedFarmerUuid is String && savedFarmerUuid.isNotEmpty) {
            _farmerUuid = savedFarmerUuid;
          }
          _signatureMediaId = saved['signature_media_id'] as String?;
          _idDocMediaId = saved['id_doc_media_id'] as String?;
          _fpicPdfMediaId = saved['fpic_pdf_media_id'] as String?;
          _fpicHoldingPhotoMediaId = saved['fpic_holding_photo_media_id'] as String?;
          _idDocType = saved['id_doc_type'] as String?;
        });
      }
    } catch (_) {
      // Corrupt draft — ignore, start blank rather than crash the screen.
    }
  }

  Future<void> _saveDraft() async {
    final prefs = await SharedPreferences.getInstance();
    final data = <String, dynamic>{
      for (final entry in _fieldControllers.entries) entry.key: entry.value.text,
      'fpic_ack': _fpicAck,
      'farmer_uuid': _farmerUuid,
      'signature_media_id': _signatureMediaId,
      'id_doc_media_id': _idDocMediaId,
      'fpic_pdf_media_id': _fpicPdfMediaId,
      'fpic_holding_photo_media_id': _fpicHoldingPhotoMediaId,
      'id_doc_type': _idDocType,
    };
    await prefs.setString(_draftPrefsKey, jsonEncode(data));
  }

  Future<void> _clearDraft() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_draftPrefsKey);
  }

  Future<void> _confirmClearDraft() async {
    final l = AppLocalizations.of(context)!;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(l.kyc_clear_draft_dialog_title),
        content: Text(l.kyc_clear_draft_dialog_content),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: Text(l.kyc_cancel_button),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: Text(l.kyc_clear_button),
          ),
        ],
      ),
    );
    if (ok != true) return;
    for (final c in _fieldControllers.values) {
      c.clear();
    }
    setState(() {
      _fpicAck = false;
      _pincodeResult = null;
      _ifscResult = null;
      _draftRestoredBannerVisible = false;
      // Deferred R1 — a fresh farmer_uuid too: any media already captured
      // under the old uuid is orphaned by this explicit "start over" action
      // (same as clearing every other field), so don't carry it forward.
      _farmerUuid = const Uuid().v4();
      _signatureMediaId = null;
      _idDocMediaId = null;
      _fpicPdfMediaId = null;
      _fpicHoldingPhotoMediaId = null;
      _idDocType = null;
    });
    await _clearDraft();
  }

  // ---------------------------------------------------------------------
  // Pincode / IFSC lookups (V8 Part 4 J) — convenience only, never block
  // submission on failure.
  // ---------------------------------------------------------------------

  Future<void> _lookupPincode() async {
    setState(() {
      _pincodeLookupBusy = true;
      _pincodeError = null;
      _pincodeResult = null;
    });
    final result = await PincodeLookupService.lookup(_pincode.text);
    if (!mounted) return;
    setState(() {
      _pincodeLookupBusy = false;
      _pincodeResult = result;
      if (result == null) {
        _pincodeError = AppLocalizations.of(context)!.kyc_pincode_no_match;
      }
    });
  }

  void _applyPincodeResult() {
    final result = _pincodeResult;
    if (result == null) return;
    final existing = _village.text.trim();
    final suffix = '${result.district}, ${result.state}';
    _village.text = existing.isEmpty ? suffix : '$existing, $suffix';
    setState(() => _pincodeResult = null);
  }

  Future<void> _lookupIfsc() async {
    setState(() {
      _ifscLookupBusy = true;
      _ifscError = null;
      _ifscResult = null;
    });
    final result = await IfscLookupService.lookup(_ifsc.text);
    if (!mounted) return;
    setState(() {
      _ifscLookupBusy = false;
      _ifscResult = result;
      if (result == null) {
        _ifscError = AppLocalizations.of(context)!.kyc_ifsc_no_match;
      }
    });
  }

  /// Mask an account number on-device: keep the last 4, replace the rest with
  /// 'X'. The full number is never stored or transmitted. Also satisfies the
  /// server's masked-field guard (contains a mask char).
  static String _maskAccount(String raw) {
    final digits = raw.trim();
    if (digits.length <= 4) return digits;
    final last4 = digits.substring(digits.length - 4);
    return 'X' * (digits.length - 4) + last4;
  }

  // ---------------------------------------------------------------------
  // Deferred R1 — farmer media capture (signature, ID document, FPIC
  // consent PDF, FPIC holding photo). Each opens SecureCameraScreen and
  // enqueues via insertEntityMediaWithOutbox, subject-scoped to _farmerUuid
  // (stable for the life of this draft — see initState/_loadDraft).
  // ---------------------------------------------------------------------

  Future<void> _captureFarmerMedia({
    required String captureType,
    required void Function(String mediaId) onCaptured,
  }) async {
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
        subjectType: 'farmer',
        subjectUuid: _farmerUuid,
        captureType: captureType,
        sandboxPath: result.sandboxPath,
        sha256Hash: result.sha256Hash,
        isMockLocation: result.isMocked,
      );
      if (!mounted) return;
      setState(() => onCaptured(mediaId));
      await _saveDraft();
    } finally {
      if (mounted) setState(() => _capturingMedia = false);
    }
  }

  Future<void> _submit() async {
    final messenger = ScaffoldMessenger.of(context);
    final l = AppLocalizations.of(context)!;
    setState(() => _submitting = true);
    try {
      final db = await ref.read(appDatabaseProvider.future);

      final payments = <Map<String, dynamic>>[];
      if (_accountNumber.text.trim().isNotEmpty ||
          _accountHolder.text.trim().isNotEmpty) {
        payments.add({
          'rail': 'bank',
          'account_holder': _accountHolder.text.trim().isEmpty
              ? null
              : _accountHolder.text.trim(),
          'masked_account': _accountNumber.text.trim().isEmpty
              ? null
              : _maskAccount(_accountNumber.text),
          'ifsc_code': _ifsc.text.trim().isEmpty ? null : _ifsc.text.trim(),
        });
      }

      final consents = <Map<String, dynamic>>[];
      // Deferred R1 — carry captured FPIC media ids even if the operator
      // hasn't (yet) ticked the ack box; exclusivity_ack is a required field
      // on the schema so it's always sent explicitly as whatever it is.
      if (_fpicAck || _fpicPdfMediaId != null || _fpicHoldingPhotoMediaId != null) {
        consents.add({
          'exclusivity_ack': _fpicAck,
          'signed_pdf_media_id': _fpicPdfMediaId,
          'holding_photo_media_id': _fpicHoldingPhotoMediaId,
        });
      }

      final documents = <Map<String, dynamic>>[];
      final last4 = _idDocLast4.text.trim();
      if (_idDocMediaId != null && _idDocType != null && last4.length == 4) {
        documents.add({
          'doc_type': _idDocType,
          'last4': last4,
          'media_id': _idDocMediaId,
        });
      }

      await db.insertFarmerWithOutbox(
        farmerUuid: _farmerUuid,
        projectId: _projectId,
        firstName: _firstName.text.trim(),
        lastName: _lastName.text.trim().isEmpty ? null : _lastName.text.trim(),
        guardianName:
            _guardian.text.trim().isEmpty ? null : _guardian.text.trim(),
        mobileNumber: _mobile.text.trim(),
        village: _village.text.trim().isEmpty ? null : _village.text.trim(),
        kycStatus: 'self_declared',
        consentStatus: _fpicAck ? 'acknowledged' : 'pending',
        signatureMediaId: _signatureMediaId,
        payments: payments,
        consents: consents,
        documents: documents,
      );

      await _clearDraft();
      if (!mounted) return;
      messenger.showSnackBar(
        SnackBar(content: Text(l.kyc_registered_snackbar)),
      );
      Navigator.pop(context);
    } catch (e) {
      if (!mounted) return;
      setState(() => _submitting = false);
      messenger.showSnackBar(
        SnackBar(content: Text(l.kyc_register_failed_snackbar(e.toString()))),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final l = AppLocalizations.of(context)!;

    return Scaffold(
      backgroundColor: t.surface,
      appBar: AppBar(
        backgroundColor: t.surface,
        elevation: 0,
        iconTheme: IconThemeData(color: t.textPrimary),
        title: Text(
          l.kyc_screen_title,
          style: t.blockHeader.copyWith(color: t.textPrimary),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.delete_outline),
            tooltip: l.kyc_clear_draft_tooltip,
            onPressed: _confirmClearDraft,
          ),
        ],
      ),
      body: SafeArea(
        child: ListView(
          padding: EdgeInsets.fromLTRB(t.gapL, t.gapM, t.gapL, t.gapL),
          children: [
            Text(
              l.kyc_form_title,
              style: t.screenTitle.copyWith(color: t.textPrimary),
            ),
            SizedBox(height: t.gapS),
            Text(
              l.kyc_subtitle,
              style: t.body.copyWith(color: t.textSecondary),
            ),
            if (_draftRestoredBannerVisible) ...[
              SizedBox(height: t.gapM),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                decoration: BoxDecoration(
                  color: t.accent.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(t.radiusS),
                ),
                child: Row(
                  children: [
                    Icon(Icons.restore, size: 18, color: t.accentText),
                    SizedBox(width: t.gapS),
                    Expanded(
                      child: Text(
                        l.kyc_draft_restored_banner,
                        style: t.body.copyWith(color: t.textPrimary),
                      ),
                    ),
                    TextButton(
                      onPressed: () =>
                          setState(() => _draftRestoredBannerVisible = false),
                      child: Text(l.kyc_dismiss),
                    ),
                  ],
                ),
              ),
            ],
            if (_projectId.isEmpty) ...[
              SizedBox(height: t.gapM),
              Text(
                l.kyc_no_project_configured,
                style: t.body.copyWith(color: t.danger),
              ),
            ],
            SizedBox(height: t.gapXL),

            _section(t, l.kyc_section_personal),
            _field(t, l.kyc_field_first_name, _firstName, 'kyc-first', l.kyc_field_first_name_hint),
            SizedBox(height: t.gapL),
            _field(t, l.kyc_field_last_name, _lastName, 'kyc-last', l.kyc_field_last_name_hint),
            SizedBox(height: t.gapL),
            _field(t, l.kyc_field_guardian, _guardian, 'kyc-guardian', ''),
            SizedBox(height: t.gapL),
            _field(t, l.kyc_field_mobile, _mobile, 'kyc-mobile', l.kyc_field_mobile_hint),
            SizedBox(height: t.gapL),
            _field(t, l.kyc_field_village, _village, 'kyc-village', ''),
            SizedBox(height: t.gapL),
            _pincodeRow(t, l),

            SizedBox(height: t.gapXL),
            _section(t, l.kyc_section_identity),
            _mediaCaptureRow(
              t,
              label: l.kyc_capture_signature,
              testId: 'kyc-capture-signature',
              captured: _signatureMediaId != null,
              onPressed: () => _captureFarmerMedia(
                captureType: CaptureType.farmerSignature,
                onCaptured: (id) => _signatureMediaId = id,
              ),
            ),
            SizedBox(height: t.gapL),
            _mediaCaptureRow(
              t,
              label: l.kyc_capture_id_document,
              testId: 'kyc-capture-id-doc',
              captured: _idDocMediaId != null,
              onPressed: () => _captureFarmerMedia(
                captureType: CaptureType.farmerIdDocument,
                onCaptured: (id) => _idDocMediaId = id,
              ),
            ),
            if (_idDocMediaId != null) ...[
              SizedBox(height: t.gapM),
              _idDocTypeRow(t, l),
              SizedBox(height: t.gapL),
              _field(
                t,
                l.kyc_id_last4_label,
                _idDocLast4,
                'kyc-id-last4',
                l.kyc_id_last4_hint,
              ),
            ],

            SizedBox(height: t.gapXL),
            _section(t, l.kyc_section_payment),
            _field(t, l.kyc_field_account_holder, _accountHolder, 'kyc-holder', ''),
            SizedBox(height: t.gapL),
            _field(
              t,
              l.kyc_field_account_number,
              _accountNumber,
              'kyc-account',
              l.kyc_field_account_number_hint,
            ),
            SizedBox(height: t.gapL),
            _ifscRow(t, l),

            SizedBox(height: t.gapXL),
            _section(t, l.kyc_section_consent),
            CheckboxListTile(
              value: _fpicAck,
              onChanged: (v) => setState(() => _fpicAck = v ?? false),
              contentPadding: EdgeInsets.zero,
              controlAffinity: ListTileControlAffinity.leading,
              title: Text(
                l.kyc_fpic_consent_text,
                style: t.body.copyWith(color: t.textPrimary),
              ),
            ),
            SizedBox(height: t.gapL),
            _mediaCaptureRow(
              t,
              label: l.kyc_capture_fpic_pdf,
              testId: 'kyc-capture-fpic-pdf',
              captured: _fpicPdfMediaId != null,
              onPressed: () => _captureFarmerMedia(
                captureType: CaptureType.fpicConsentPdf,
                onCaptured: (id) => _fpicPdfMediaId = id,
              ),
            ),
            SizedBox(height: t.gapL),
            _mediaCaptureRow(
              t,
              label: l.kyc_capture_fpic_holding,
              testId: 'kyc-capture-fpic-holding',
              captured: _fpicHoldingPhotoMediaId != null,
              onPressed: () => _captureFarmerMedia(
                captureType: CaptureType.fpicHoldingPhoto,
                onCaptured: (id) => _fpicHoldingPhotoMediaId = id,
              ),
            ),

            SizedBox(height: t.gapXL),
            DmrvButton(
              label: _submitting ? l.kyc_saving_label : l.kyc_register_button,
              testId: 'kyc-save-btn',
              variant: DmrvButtonVariant.primary,
              onPressed: _canSubmit ? _submit : null,
            ),
          ],
        ),
      ),
    );
  }

  Widget _pincodeRow(DmrvTokens t, AppLocalizations l) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Expanded(
              child: _field(
                t,
                l.kyc_field_pincode,
                _pincode,
                'kyc-pincode',
                l.kyc_field_pincode_hint,
              ),
            ),
            SizedBox(width: t.gapM),
            SizedBox(
              height: 40,
              child: OutlinedButton(
                onPressed: _pincodeLookupBusy ? null : _lookupPincode,
                child: _pincodeLookupBusy
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : Text(l.kyc_lookup_button),
              ),
            ),
          ],
        ),
        if (_pincodeResult != null) ...[
          SizedBox(height: t.gapS),
          Semantics(
            identifier: 'kyc-pincode-result',
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    l.kyc_pincode_found(_pincodeResult!.district, _pincodeResult!.state),
                    style: t.body.copyWith(color: t.success),
                  ),
                ),
                TextButton(
                  onPressed: _applyPincodeResult,
                  child: Text(l.kyc_apply_to_village),
                ),
              ],
            ),
          ),
        ],
        if (_pincodeError != null) ...[
          SizedBox(height: t.gapS),
          Text(_pincodeError!, style: t.body.copyWith(color: t.textSecondary)),
        ],
      ],
    );
  }

  Widget _ifscRow(DmrvTokens t, AppLocalizations l) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Expanded(
              child: _field(t, l.kyc_field_ifsc, _ifsc, 'kyc-ifsc', ''),
            ),
            SizedBox(width: t.gapM),
            SizedBox(
              height: 40,
              child: OutlinedButton(
                onPressed: _ifscLookupBusy ? null : _lookupIfsc,
                child: _ifscLookupBusy
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : Text(l.kyc_verify_button),
              ),
            ),
          ],
        ),
        if (_ifscResult != null) ...[
          SizedBox(height: t.gapS),
          Semantics(
            identifier: 'kyc-ifsc-result',
            child: Text(
              l.kyc_ifsc_found(_ifscResult!.bankName, _ifscResult!.branch),
              style: t.body.copyWith(color: t.success),
            ),
          ),
        ],
        if (_ifscError != null) ...[
          SizedBox(height: t.gapS),
          Text(_ifscError!, style: t.body.copyWith(color: t.textSecondary)),
        ],
      ],
    );
  }

  Widget _section(DmrvTokens t, String label) => Padding(
        padding: EdgeInsets.only(bottom: t.gapM),
        child: Text(label, style: t.chipLabel.copyWith(color: t.accentText)),
      );

  /// Deferred R1 — one row for an optional farmer media capture. Shows
  /// "not captured" until present; capturing never blocks saving the farmer.
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

  Widget _idDocTypeRow(DmrvTokens t, AppLocalizations l) {
    final types = {
      'aadhaar': l.kyc_id_type_aadhaar,
      'pan': l.kyc_id_type_pan,
      'passport': l.kyc_id_type_passport,
      'nid': l.kyc_id_type_nid,
    };
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(l.kyc_id_type_label, style: t.chipLabel.copyWith(color: t.accentText)),
        SizedBox(height: t.gapS),
        Wrap(
          spacing: t.gapS,
          runSpacing: t.gapS,
          children: [
            for (final e in types.entries)
              Semantics(
                identifier: 'kyc-id-type-${e.key}',
                button: true,
                selected: _idDocType == e.key,
                child: ChoiceChip(
                  label: Text(e.value),
                  selected: _idDocType == e.key,
                  onSelected: (_) => setState(() => _idDocType = e.key),
                ),
              ),
          ],
        ),
      ],
    );
  }

  Widget _field(
    DmrvTokens t,
    String label,
    TextEditingController controller,
    String testId,
    String hint,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: t.chipLabel.copyWith(color: t.accentText)),
        const SizedBox(height: 8),
        Container(
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
              autocorrect: false,
              enableSuggestions: false,
              cursorColor: t.accentText,
              style: t.body.copyWith(color: t.textPrimary),
              onChanged: (_) => setState(() {}),
              decoration: InputDecoration(
                border: InputBorder.none,
                isCollapsed: true,
                contentPadding: const EdgeInsets.symmetric(vertical: 12),
                hintText: hint,
                hintStyle: t.body.copyWith(color: t.textDisabled),
              ),
            ),
          ),
        ),
      ],
    );
  }
}
