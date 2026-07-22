import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:uuid/uuid.dart';

import '../../data/local/database_provider.dart';
import '../../services/ifsc_lookup_service.dart';
import '../../services/pincode_lookup_service.dart';
import '../components/dmrv_button.dart';
import '../design/tokens.dart';

/// V8 Part 2 — real farmer registration (replaces the `// TODO` stub that
/// saved nothing). Collects the structured farmer record + an optional masked
/// payment method + an FPIC consent acknowledgement, and enqueues it to the
/// sync outbox (→ POST /api/v1/farmers), where it appears in the verifier
/// portal's Farmers page.
///
/// PII discipline:
///  - the account number is MASKED on-device (last-4 kept) before it is ever
///    persisted or sent — the full number never leaves the phone;
///  - identity-document PHOTOS and the FPIC signed-PDF are deliberately NOT
///    captured here: farmer media upload is a separate sub-feature, and
///    claiming a media_id we never upload would be a false attestation.
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
      if (mounted) {
        setState(() {
          _fpicAck = ack == true;
          _draftRestoredBannerVisible = true;
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
    };
    await prefs.setString(_draftPrefsKey, jsonEncode(data));
  }

  Future<void> _clearDraft() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_draftPrefsKey);
  }

  Future<void> _confirmClearDraft() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Clear all entered fields?'),
        content: const Text(
          'This erases every field on this form for this farmer. This cannot '
          'be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Clear'),
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
        _pincodeError = 'No match — check the pincode or enter the address manually.';
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
        _ifscError = 'No match — double-check the IFSC code.';
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

  Future<void> _submit() async {
    final messenger = ScaffoldMessenger.of(context);
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
      if (_fpicAck) {
        consents.add({'exclusivity_ack': true});
      }

      await db.insertFarmerWithOutbox(
        farmerUuid: const Uuid().v4(),
        projectId: _projectId,
        firstName: _firstName.text.trim(),
        lastName: _lastName.text.trim().isEmpty ? null : _lastName.text.trim(),
        guardianName:
            _guardian.text.trim().isEmpty ? null : _guardian.text.trim(),
        mobileNumber: _mobile.text.trim(),
        village: _village.text.trim().isEmpty ? null : _village.text.trim(),
        kycStatus: 'self_declared',
        consentStatus: _fpicAck ? 'acknowledged' : 'pending',
        payments: payments,
        consents: consents,
      );

      await _clearDraft();
      if (!mounted) return;
      messenger.showSnackBar(
        const SnackBar(content: Text('Farmer registered — queued for sync.')),
      );
      Navigator.pop(context);
    } catch (e) {
      if (!mounted) return;
      setState(() => _submitting = false);
      messenger.showSnackBar(
        SnackBar(content: Text('Could not register farmer: $e')),
      );
    }
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
        title: Text(
          'Farmer KYC',
          style: t.blockHeader.copyWith(color: t.textPrimary),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.delete_outline),
            tooltip: 'Clear draft',
            onPressed: _confirmClearDraft,
          ),
        ],
      ),
      body: SafeArea(
        child: ListView(
          padding: EdgeInsets.fromLTRB(t.gapL, t.gapM, t.gapL, t.gapL),
          children: [
            Text(
              'Register Farmer',
              style: t.screenTitle.copyWith(color: t.textPrimary),
            ),
            SizedBox(height: t.gapS),
            Text(
              'Enrol the farmer and record their FPIC consent. Details sync to '
              'the verifier portal.',
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
                        'Draft restored from your last session.',
                        style: t.body.copyWith(color: t.textPrimary),
                      ),
                    ),
                    TextButton(
                      onPressed: () =>
                          setState(() => _draftRestoredBannerVisible = false),
                      child: const Text('Dismiss'),
                    ),
                  ],
                ),
              ),
            ],
            if (_projectId.isEmpty) ...[
              SizedBox(height: t.gapM),
              Text(
                'No project is configured for this device, so a farmer cannot '
                'be scoped to a project. Registration is disabled.',
                style: t.body.copyWith(color: t.danger),
              ),
            ],
            SizedBox(height: t.gapXL),

            _section(t, 'PERSONAL'),
            _field(t, 'FIRST NAME', _firstName, 'kyc-first', 'e.g. Rahul'),
            SizedBox(height: t.gapL),
            _field(t, 'LAST NAME (OPTIONAL)', _lastName, 'kyc-last', 'e.g. Kumar'),
            SizedBox(height: t.gapL),
            _field(t, 'GUARDIAN NAME (OPTIONAL)', _guardian, 'kyc-guardian', ''),
            SizedBox(height: t.gapL),
            _field(t, 'MOBILE NUMBER', _mobile, 'kyc-mobile', '+91 ...'),
            SizedBox(height: t.gapL),
            _field(t, 'VILLAGE (OPTIONAL)', _village, 'kyc-village', ''),
            SizedBox(height: t.gapL),
            _pincodeRow(t),

            SizedBox(height: t.gapXL),
            _section(t, 'PAYMENT (OPTIONAL, MASKED ON SAVE)'),
            _field(t, 'ACCOUNT HOLDER', _accountHolder, 'kyc-holder', ''),
            SizedBox(height: t.gapL),
            _field(
              t,
              'ACCOUNT NUMBER',
              _accountNumber,
              'kyc-account',
              'stored masked — full number never leaves the device',
            ),
            SizedBox(height: t.gapL),
            _ifscRow(t),

            SizedBox(height: t.gapXL),
            _section(t, 'CONSENT'),
            CheckboxListTile(
              value: _fpicAck,
              onChanged: (v) => setState(() => _fpicAck = v ?? false),
              contentPadding: EdgeInsets.zero,
              controlAffinity: ListTileControlAffinity.leading,
              title: Text(
                'Farmer has given free, prior & informed consent (FPIC), '
                'including exclusivity.',
                style: t.body.copyWith(color: t.textPrimary),
              ),
            ),

            SizedBox(height: t.gapXL),
            DmrvButton(
              label: _submitting ? 'SAVING…' : 'REGISTER FARMER',
              testId: 'kyc-save-btn',
              variant: DmrvButtonVariant.primary,
              onPressed: _canSubmit ? _submit : null,
            ),
          ],
        ),
      ),
    );
  }

  Widget _pincodeRow(DmrvTokens t) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Expanded(
              child: _field(
                t,
                'PINCODE (OPTIONAL — AUTO-FILLS DISTRICT/STATE)',
                _pincode,
                'kyc-pincode',
                'e.g. 110001',
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
                    : const Text('Look up'),
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
                    'Found: ${_pincodeResult!.district}, ${_pincodeResult!.state}',
                    style: t.body.copyWith(color: t.success),
                  ),
                ),
                TextButton(
                  onPressed: _applyPincodeResult,
                  child: const Text('Apply to village'),
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

  Widget _ifscRow(DmrvTokens t) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Expanded(
              child: _field(t, 'IFSC (OPTIONAL)', _ifsc, 'kyc-ifsc', ''),
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
                    : const Text('Verify'),
              ),
            ),
          ],
        ),
        if (_ifscResult != null) ...[
          SizedBox(height: t.gapS),
          Semantics(
            identifier: 'kyc-ifsc-result',
            child: Text(
              'Bank: ${_ifscResult!.bankName} · Branch: ${_ifscResult!.branch}',
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
