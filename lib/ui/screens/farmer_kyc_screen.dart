import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../components/dmrv_button.dart';
import '../design/tokens.dart';

class FarmerKycScreen extends ConsumerStatefulWidget {
  const FarmerKycScreen({super.key});

  @override
  ConsumerState<FarmerKycScreen> createState() => _FarmerKycScreenState();
}

class _FarmerKycScreenState extends ConsumerState<FarmerKycScreen> {
  final _nameCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  final _idCtrl = TextEditingController();

  @override
  void dispose() {
    _nameCtrl.dispose();
    _phoneCtrl.dispose();
    _idCtrl.dispose();
    super.dispose();
  }

  bool get _canSubmit =>
      _nameCtrl.text.trim().isNotEmpty && _phoneCtrl.text.trim().isNotEmpty;

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
              'Collect the farmer details to associate with their Kon-Tiki kiln subscription.',
              style: t.body.copyWith(color: t.textSecondary),
            ),
            SizedBox(height: t.gapXL),
            _field(t, 'FULL NAME', _nameCtrl, 'kyc-name', 'e.g. Rahul Kumar'),
            SizedBox(height: t.gapL),
            _field(t, 'PHONE NUMBER', _phoneCtrl, 'kyc-phone', '+91 ...'),
            SizedBox(height: t.gapL),
            _field(t, 'NATIONAL ID (OPTIONAL)', _idCtrl, 'kyc-id', 'Aadhar / PAN'),
            SizedBox(height: t.gapXL),
            DmrvButton(
              label: 'SAVE DETAILS',
              testId: 'kyc-save-btn',
              variant: DmrvButtonVariant.primary,
              onPressed: _canSubmit
                  ? () {
                      // TODO: Save KYC locally or sync to server
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text('Farmer KYC saved locally.')),
                      );
                      Navigator.pop(context);
                    }
                  : null,
            ),
          ],
        ),
      ),
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
