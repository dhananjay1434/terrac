import 'package:flutter/material.dart';

import '../../l10n/app_localizations.dart';
import '../../services/day_start_service.dart';
import '../components/dmrv_button.dart';
import '../design/tokens.dart';

/// Deferred R6 — day-start audit lock. Full-screen, non-dismissible
/// (no back button, no barrier dismiss): the operator must explicitly
/// attest all three items before the dashboard becomes usable for the day.
/// Pushed by [DashboardScreen] when [isDayStartValid] is false; pops itself
/// on confirm, revealing the dashboard underneath.
class DayStartAttestationScreen extends StatefulWidget {
  const DayStartAttestationScreen({super.key});

  @override
  State<DayStartAttestationScreen> createState() =>
      _DayStartAttestationScreenState();
}

class _DayStartAttestationScreenState
    extends State<DayStartAttestationScreen> {
  bool _clockChecked = false;
  bool _projectChecked = false;
  bool _calibrationChecked = false;
  bool _saving = false;

  bool get _allChecked =>
      _clockChecked && _projectChecked && _calibrationChecked;

  Future<void> _confirm() async {
    if (!_allChecked || _saving) return;
    setState(() => _saving = true);
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
          child: Padding(
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
                const Spacer(),
                DmrvButton(
                  label: _saving ? l.daystart_saving_label : l.daystart_confirm_button,
                  testId: 'daystart-confirm-btn',
                  variant: DmrvButtonVariant.primary,
                  onPressed: _allChecked && !_saving ? _confirm : null,
                ),
              ],
            ),
          ),
        ),
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
