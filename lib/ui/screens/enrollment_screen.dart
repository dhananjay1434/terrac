import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../services/api_base.dart';
import '../../services/crypto_signer.dart';
import '../components/dmrv_button.dart';
import '../design/premium_field_components.dart';
import '../design/tokens.dart';
import 'dashboard_screen.dart';
import 'farmer_kyc_screen.dart';

/// Maps an enrollment failure to a human, cause-specific message. Pure so the
/// mapping is unit-tested without the network.
String enrollmentErrorMessage(Object error) {
  final s = error.toString();
  if (error is TimeoutException || s.toLowerCase().contains('timeout')) {
    return "Can't reach the server — check the URL and your connection.";
  }
  if (s.contains('401') || s.contains('403') || s.contains('409')) {
    return 'Token invalid or already used — ask your project admin for a new one.';
  }
  return 'Enrollment failed. Check the token and server URL, then try again.';
}

enum EnrollmentStatus { idle, enrolling, enrolled, failed }

class EnrollmentState {
  const EnrollmentState(this.status, [this.error]);
  final EnrollmentStatus status;
  final String? error;

  bool get isBusy => status == EnrollmentStatus.enrolling;
}

/// The device-registration call, injectable so the state machine can be tested
/// without hitting the network. Production delegates to [CryptoSigner.registerDevice].
typedef EnrollFn = Future<void> Function(String token, String apiBaseUrl);

final enrollmentRegisterProvider = Provider<EnrollFn>(
  (ref) =>
      (token, baseUrl) =>
          CryptoSigner.registerDevice(token: token, apiBaseUrl: baseUrl),
);

class EnrollmentController extends Notifier<EnrollmentState> {
  @override
  EnrollmentState build() => const EnrollmentState(EnrollmentStatus.idle);

  Future<void> enroll(String token, String apiBaseUrl) async {
    if (state.isBusy) return;
    state = const EnrollmentState(EnrollmentStatus.enrolling);
    try {
      await ref.read(enrollmentRegisterProvider)(token.trim(), apiBaseUrl.trim());
      // Persist the base URL and retarget this session's sync immediately.
      await persistApiBaseUrl(apiBaseUrl.trim());
      ref.read(apiBaseUrlProvider.notifier).state = apiBaseUrl.trim();
      state = const EnrollmentState(EnrollmentStatus.enrolled);
    } catch (e) {
      state = EnrollmentState(
        EnrollmentStatus.failed,
        enrollmentErrorMessage(e),
      );
    }
  }
}

final enrollmentControllerProvider =
    NotifierProvider<EnrollmentController, EnrollmentState>(
      EnrollmentController.new,
    );

/// First-launch enrollment: the operator pastes the one-time token from the
/// project admin and the backend URL, then enrolls this device (its Ed25519
/// public key). Replaces the compile-time ENROLLMENT_TOKEN dart-define.
class EnrollmentScreen extends ConsumerStatefulWidget {
  const EnrollmentScreen({super.key});

  @override
  ConsumerState<EnrollmentScreen> createState() => _EnrollmentScreenState();
}

class _EnrollmentScreenState extends ConsumerState<EnrollmentScreen> {
  final _tokenCtrl = TextEditingController();
  late final TextEditingController _urlCtrl;

  @override
  void initState() {
    super.initState();
    // Prefill with any resolved base URL (dart-define / previously stored).
    _urlCtrl = TextEditingController(text: ref.read(apiBaseUrlProvider));
  }

  @override
  void dispose() {
    _tokenCtrl.dispose();
    _urlCtrl.dispose();
    super.dispose();
  }

  bool get _canEnroll =>
      _tokenCtrl.text.trim().isNotEmpty && _urlCtrl.text.trim().isNotEmpty;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final enrollment = ref.watch(enrollmentControllerProvider);

    ref.listen<EnrollmentState>(enrollmentControllerProvider, (prev, next) {
      if (next.status == EnrollmentStatus.enrolled && mounted) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute<void>(builder: (_) => const DashboardScreen()),
        );
      }
    });

    return Scaffold(
      backgroundColor: t.surface,
      body: SafeArea(
        child: ListView(
          padding: EdgeInsets.fromLTRB(t.gapL, t.gapXL, t.gapL, t.gapL),
          children: [
            Text(
              'Enroll this device',
              style: t.screenTitle.copyWith(color: t.textPrimary),
            ),
            SizedBox(height: t.gapS),
            Text(
              'Paste the one-time enrollment token from your project admin and '
              'the server address. This registers this phone once.',
              style: t.body.copyWith(color: t.textSecondary),
            ),
            SizedBox(height: t.gapXL),
            _field(t, 'ENROLLMENT TOKEN', _tokenCtrl, 'enrollment-token-input',
                'paste token'),
            SizedBox(height: t.gapL),
            _field(t, 'SERVER URL', _urlCtrl, 'enrollment-url-input',
                'https://…'),
            if (enrollment.status == EnrollmentStatus.failed &&
                enrollment.error != null) ...[
              SizedBox(height: t.gapL),
              PremiumFieldPanel(
                accentBorderColor: t.danger,
                padding: EdgeInsets.all(t.gapL),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.error_outline, color: t.danger, size: 24),
                    SizedBox(width: t.gapM),
                    Expanded(
                      child: Text(
                        enrollment.error!,
                        style: t.body.copyWith(color: t.textPrimary),
                      ),
                    ),
                  ],
                ),
              ),
            ],
            SizedBox(height: t.gapXL),
            DmrvButton(
              label: enrollment.isBusy ? 'ENROLLING…' : 'ENROLL DEVICE',
              testId: 'enroll-device-btn',
              variant: DmrvButtonVariant.primary,
              onPressed: (enrollment.isBusy || !_canEnroll)
                  ? null
                  : () => ref
                        .read(enrollmentControllerProvider.notifier)
                        .enroll(_tokenCtrl.text, _urlCtrl.text),
            ),
            SizedBox(height: t.gapL),
            DmrvButton(
              label: 'FARMER KYC SETUP',
              testId: 'kyc-setup-btn',
              variant: DmrvButtonVariant.neutral,
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (_) => const FarmerKycScreen(),
                ),
              ),
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
