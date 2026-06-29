import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../services/sync_queue_manager.dart';
import 'package:geolocator/geolocator.dart';

import '../../data/local/database_provider.dart';
import '../../data/local/yield_end_use_writers.dart';
import '../../providers/batch_session_notifier.dart';
import '../../services/location_service.dart';
import '../../services/secure_capture_service.dart';
import '../design/app_theme.dart';
import '../design/premium_field_components.dart';
import '../widgets/integrity_footer.dart';
import 'secure_camera_screen.dart';

/// =============================================================================
/// EndUseApplicationScreen  (Prompt 5 — Task 2 — EndUse)
/// =============================================================================
/// Final step of the batch lifecycle:
///   • CAPTURE APPLICATION GPS  → Geolocator one-shot fix.
///   • CAPTURE FARMER PHOTO     → SecureCameraScreen → sandboxed JPEG + SHA-256.
///   • APPLICATION METHOD       → dropdown over the registry-approved enum.
///   • TONNAGE APPLIED          → numeric input (tonnes biochar).
///   • TRANSPORT DISTANCE KM    → numeric input (default 0 for on-farm).
///   • COMMIT END-USE           → atomic insertEndUseWithOutbox + closeBatch.
/// =============================================================================

const _kMethods = <String, String>{
  'SURFACE_BROADCAST': 'Surface Broadcast',
  'ROOT_ZONE_TRENCHING': 'Root Zone Trenching',
  'BANDED_INCORPORATION': 'Banded Incorporation',
  'COMPOST_AMENDMENT': 'Compost Amendment',
};

class EndUseApplicationScreen extends ConsumerStatefulWidget {
  const EndUseApplicationScreen({super.key});
  @override
  ConsumerState<EndUseApplicationScreen> createState() =>
      _EndUseApplicationScreenState();
}

class _EndUseApplicationScreenState
    extends ConsumerState<EndUseApplicationScreen> {
  // Shared light-theme tokens for this screen.
  static const Color _errorRed = Color(0xFFDC2626);

  String? _methodCode;
  final _tonnageCtrl = TextEditingController();
  final _transportCtrl = TextEditingController(text: '0');

  Position? _gpsFix;
  String? _gpsError;
  bool _gpsBusy = false;

  SecureCaptureResult? _farmerPhoto;
  bool _busy = false;
  String? _err;

  @override
  void dispose() {
    _tonnageCtrl.dispose();
    _transportCtrl.dispose();
    super.dispose();
  }

  Future<void> _captureGps() async {
    if (_gpsBusy) return;
    setState(() {
      _gpsBusy = true;
      _gpsError = null;
    });
    try {
      // Service + permission preflight (reuses SecureCaptureService helper).
      await ref.read(secureCaptureServiceProvider).ensurePermissions();
      final pos = await ref.read(locationServiceProvider).acquirePosition();
      setState(() => _gpsFix = pos);
    } catch (e) {
      setState(() => _gpsError = e.toString());
    } finally {
      if (mounted) setState(() => _gpsBusy = false);
    }
  }

  Future<void> _captureFarmer() async {
    final r = await Navigator.of(context).push<SecureCaptureResult>(
      MaterialPageRoute(
        builder: (_) => const SecureCameraScreen(preferFrontCamera: true),
      ),
    );
    if (r != null) setState(() => _farmerPhoto = r);
  }

  bool get _canCommit =>
      _methodCode != null &&
      double.tryParse(_tonnageCtrl.text.trim()) != null &&
      double.tryParse(_transportCtrl.text.trim()) != null &&
      _gpsFix != null &&
      _farmerPhoto != null;

  Future<void> _commit() async {
    if (!_canCommit || _busy) return;
    setState(() {
      _busy = true;
      _err = null;
    });
    try {
      final batchUuid = ref.read(batchSessionProvider);
      if (batchUuid == null) throw StateError('No active batch.');
      final db = await ref.read(appDatabaseProvider.future);
      final val = double.tryParse(_tonnageCtrl.text.trim());
      if (val == null || val < 0) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Invalid application rate')),
        );
        return;
      }
      final uuid = await db.insertEndUseWithOutbox(
        batchUuid: batchUuid,
        applicationMethodology: _methodCode!,
        applicationRateTonnes: val,
        transportDistanceKm: double.parse(_transportCtrl.text.trim()),
        latitude: _gpsFix!.latitude,
        longitude: _gpsFix!.longitude,
        farmerPhotoPath: _farmerPhoto!.sandboxPath,
        farmerPhotoSha256: _farmerPhoto!.sha256Hash,
      );
      await db.closeBatch(batchUuid);
      debugPrint('[EndUse] insertEndUseWithOutbox OK uuid=$uuid');

      // Tear down the active batch session so the dashboard CTA flips back
      // to "START NEW BATCH".
      ref.read(batchSessionProvider.notifier).end();

      if (!mounted) return;
      // Pop everything back to the dashboard.
      Navigator.of(context).popUntil((r) => r.isFirst);
    } catch (e) {
      setState(() => _err = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final String footerHash =
        _farmerPhoto?.sha256Hash ??
        '----------------------------------------------------------------';

    return Scaffold(
      backgroundColor: AppTheme.tacticalTitanium,
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            PremiumScreenHeader(
              stepNumber: '05',
              title: 'End-Use Application',
              onBack: () => Navigator.of(context).pop(),
            ),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
                children: [
                  _gpsBlock(),
                  const SizedBox(height: 16),
                  _photoBlock(),
                  const SizedBox(height: 16),
                  _methodBlock(),
                  const SizedBox(height: 16),
                  _numericBlock(
                    label: 'TONNAGE APPLIED (t biochar)',
                    controller: _tonnageCtrl,
                    testId: 'tonnage-applied-input',
                    hint: '0.00',
                  ),
                  const SizedBox(height: 16),
                  _numericBlock(
                    label: 'TRANSPORT DISTANCE (km)',
                    controller: _transportCtrl,
                    testId: 'transport-distance-input',
                    hint: '0.0',
                  ),
                  if (_err != null) ...[
                    const SizedBox(height: 16),
                    PremiumFieldPanel(
                      accentBorderColor: _errorRed,
                      padding: const EdgeInsets.all(16),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Icon(
                            Icons.error_outline,
                            color: _errorRed,
                            size: 28,
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                const Text(
                                  'COMMIT FAILED',
                                  style: TextStyle(
                                    fontFamily: 'SpaceGrotesk',
                                    fontSize: 14,
                                    fontWeight: FontWeight.w700,
                                    letterSpacing: 0.6,
                                    color: _errorRed,
                                  ),
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  _err!,
                                  style: const TextStyle(
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
                    ),
                  ],
                  const SizedBox(height: 24),
                  PremiumFieldButton(
                    label: _busy
                        ? 'COMMITTING…'
                        : (_canCommit
                              ? 'COMMIT END-USE // CLOSE BATCH'
                              : 'LOCKED // COMPLETE ALL FIELDS'),
                    testId: 'commit-end-use-btn',
                    state: _busy
                        ? FieldButtonState.locked
                        : (_canCommit
                              ? FieldButtonState.go
                              : FieldButtonState.locked),
                    onPressed: _busy || !_canCommit ? null : _commit,
                  ),
                  const SizedBox(height: 12),
                ],
              ),
            ),
            IntegrityFooter(lastHash: footerHash),
          ],
        ),
      ),
    );
  }

  // ===========================================================================
  // BLOCK BUILDERS
  // ===========================================================================

  Widget _gpsBlock() {
    final bool captured = _gpsFix != null;
    final Color accent = captured ? AppTheme.yieldGold : AppTheme.cobaltShield;

    return PremiumFieldPanel(
      accentBorderColor: captured ? AppTheme.yieldGold : null,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  'APPLICATION GPS · CARBON SINK',
                  style: TextStyle(
                    fontFamily: 'SpaceGrotesk',
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.8,
                    color: accent,
                  ),
                ),
              ),
              PremiumStatusChip(
                label: captured ? 'VERIFIED' : 'PENDING',
                status: captured
                    ? PremiumChipStatus.verified
                    : PremiumChipStatus.pending,
              ),
            ],
          ),
          const SizedBox(height: 12),
          Semantics(
            identifier: 'capture-application-gps-btn',
            button: true,
            enabled: !_gpsBusy,
            child: Material(
              color: captured
                  ? AppTheme.yieldGold10
                  : AppTheme.tacticalTitanium,
              borderRadius: BorderRadius.circular(10),
              clipBehavior: Clip.antiAlias,
              child: InkWell(
                onTap: _gpsBusy
                    ? null
                    : () {
                        HapticFeedback.heavyImpact();
                        _captureGps();
                      },
                child: Container(
                  constraints: const BoxConstraints(minHeight: 72),
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 12,
                  ),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: captured
                          ? AppTheme.yieldGold40
                          : AppTheme.cobaltShield25,
                      width: 1,
                    ),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        _gpsBusy
                            ? Icons.hourglass_top
                            : (captured
                                  ? Icons.check_circle_outline
                                  : Icons.gps_fixed),
                        color: accent,
                        size: 28,
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              _gpsBusy
                                  ? 'ACQUIRING FIX…'
                                  : (captured
                                        ? 'GPS LOCKED'
                                        : 'CAPTURE APPLICATION GPS'),
                              style: const TextStyle(
                                fontFamily: 'SpaceGrotesk',
                                fontSize: 16,
                                fontWeight: FontWeight.w700,
                                letterSpacing: 0.4,
                                color: AppTheme.armorSlate,
                              ),
                            ),
                            if (captured) ...[
                              const SizedBox(height: 4),
                              Text(
                                '${_gpsFix!.latitude.toStringAsFixed(6)}, ${_gpsFix!.longitude.toStringAsFixed(6)}',
                                style: TextStyle(
                                  fontFamily: 'SpaceMono',
                                  fontSize: 13,
                                  fontWeight: FontWeight.w400,
                                  color: AppTheme.armorSlate75,
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
          if (_gpsError != null) ...[
            const SizedBox(height: 8),
            Text(
              _gpsError!,
              style: const TextStyle(
                fontFamily: 'SpaceMono',
                fontSize: 12,
                fontWeight: FontWeight.w400,
                color: _errorRed,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _photoBlock() {
    final bool captured = _farmerPhoto != null;
    final Color accent = captured ? AppTheme.yieldGold : AppTheme.cobaltShield;

    return PremiumFieldPanel(
      accentBorderColor: captured ? AppTheme.yieldGold : null,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  'FARMER ID PHOTO · SHA-256 ANCHORED',
                  style: TextStyle(
                    fontFamily: 'SpaceGrotesk',
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.8,
                    color: accent,
                  ),
                ),
              ),
              PremiumStatusChip(
                label: captured ? 'VERIFIED' : 'PENDING',
                status: captured
                    ? PremiumChipStatus.verified
                    : PremiumChipStatus.pending,
              ),
            ],
          ),
          const SizedBox(height: 12),
          Semantics(
            identifier: 'capture-farmer-photo-btn',
            button: true,
            child: Material(
              color: captured
                  ? AppTheme.yieldGold10
                  : AppTheme.tacticalTitanium,
              borderRadius: BorderRadius.circular(10),
              clipBehavior: Clip.antiAlias,
              child: InkWell(
                onTap: () {
                  HapticFeedback.heavyImpact();
                  _captureFarmer();
                },
                child: Container(
                  constraints: const BoxConstraints(minHeight: 72),
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 10,
                  ),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: captured
                          ? AppTheme.yieldGold40
                          : AppTheme.cobaltShield25,
                      width: 1,
                    ),
                  ),
                  child: Row(
                    children: [
                      ClipRRect(
                        borderRadius: BorderRadius.circular(8),
                        child: SizedBox(
                          width: 56,
                          height: 56,
                          child:
                              captured &&
                                  File(_farmerPhoto!.sandboxPath).existsSync()
                              ? Image.file(
                                  File(_farmerPhoto!.sandboxPath),
                                  width: 56,
                                  height: 56,
                                  fit: BoxFit.cover,
                                )
                              : Container(
                                  color: AppTheme.pureAlbedo,
                                  alignment: Alignment.center,
                                  child: Icon(
                                    captured
                                        ? Icons.verified
                                        : Icons.person_pin_circle_outlined,
                                    color: accent,
                                    size: 30,
                                  ),
                                ),
                        ),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              captured
                                  ? 'FARMER PHOTO ANCHORED'
                                  : 'CAPTURE FARMER ID / SELFIE',
                              style: const TextStyle(
                                fontFamily: 'SpaceGrotesk',
                                fontSize: 16,
                                fontWeight: FontWeight.w700,
                                letterSpacing: 0.4,
                                color: AppTheme.armorSlate,
                              ),
                            ),
                            if (captured) ...[
                              const SizedBox(height: 4),
                              Text(
                                'sha256: ${_farmerPhoto!.sha256Hash}',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(
                                  fontFamily: 'SpaceMono',
                                  fontSize: 13,
                                  fontWeight: FontWeight.w400,
                                  color: AppTheme.armorSlate75,
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _methodBlock() {
    final bool hasValue = _methodCode != null;
    return PremiumFieldPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'APPLICATION METHOD',
            style: TextStyle(
              fontFamily: 'SpaceGrotesk',
              fontSize: 13,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.8,
              color: AppTheme.cobaltShield,
            ),
          ),
          const SizedBox(height: 12),
          Semantics(
            identifier: 'application-method-dropdown',
            child: DropdownButtonFormField<String>(
              initialValue: _methodCode,
              isExpanded: true,
              icon: const Icon(
                Icons.keyboard_arrow_down,
                color: AppTheme.cobaltShield,
              ),
              dropdownColor: AppTheme.pureAlbedo,
              hint: Text(
                'SELECT METHOD',
                style: TextStyle(
                  fontFamily: 'SpaceGrotesk',
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 0.4,
                  color: AppTheme.armorSlate45,
                ),
              ),
              style: const TextStyle(
                fontFamily: 'SpaceGrotesk',
                fontSize: 16,
                fontWeight: FontWeight.w600,
                letterSpacing: 0.4,
                color: AppTheme.armorSlate,
              ),
              decoration: InputDecoration(
                filled: true,
                fillColor: AppTheme.tacticalTitanium,
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 14,
                ),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: BorderSide(
                    color: hasValue
                        ? AppTheme.cobaltShield40
                        : AppTheme.cobaltShield25,
                    width: 1,
                  ),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: BorderSide(
                    color: hasValue
                        ? AppTheme.cobaltShield40
                        : AppTheme.cobaltShield25,
                    width: 1,
                  ),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(10),
                  borderSide: const BorderSide(
                    color: AppTheme.cobaltShield,
                    width: 2,
                  ),
                ),
              ),
              items: _kMethods.entries
                  .map(
                    (e) => DropdownMenuItem<String>(
                      value: e.key,
                      child: Text(
                        e.value.toUpperCase(),
                        style: const TextStyle(
                          fontFamily: 'SpaceGrotesk',
                          fontSize: 15,
                          fontWeight: FontWeight.w600,
                          letterSpacing: 0.4,
                          color: AppTheme.armorSlate,
                        ),
                      ),
                    ),
                  )
                  .toList(),
              onChanged: (v) => setState(() => _methodCode = v),
            ),
          ),
        ],
      ),
    );
  }

  Widget _numericBlock({
    required String label,
    required TextEditingController controller,
    required String testId,
    required String hint,
  }) {
    return PremiumFieldPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: TextStyle(
              fontFamily: 'SpaceGrotesk',
              fontSize: 13,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.8,
              color: AppTheme.cobaltShield,
            ),
          ),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            decoration: BoxDecoration(
              color: AppTheme.tacticalTitanium,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: AppTheme.cobaltShield25, width: 1),
            ),
            child: Semantics(
              identifier: testId,
              textField: true,
              child: TextField(
                controller: controller,
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                  signed: false,
                ),
                inputFormatters: [
                  FilteringTextInputFormatter.allow(RegExp(r'[0-9.]')),
                ],
                cursorColor: AppTheme.cobaltShield,
                style: const TextStyle(
                  fontFamily: 'SpaceMono',
                  fontSize: 40,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.cobaltShield,
                  height: 1.0,
                ),
                onChanged: (_) => setState(() {}),
                decoration: InputDecoration(
                  border: InputBorder.none,
                  isCollapsed: true,
                  contentPadding: const EdgeInsets.symmetric(vertical: 10),
                  hintText: hint,
                  hintStyle: TextStyle(
                    fontFamily: 'SpaceMono',
                    fontSize: 40,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.cobaltShield25,
                    height: 1.0,
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
