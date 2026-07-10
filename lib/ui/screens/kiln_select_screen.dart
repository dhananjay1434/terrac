import 'package:drift/drift.dart' show OrderingTerm;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/local/app_database.dart';
import '../../data/local/database_provider.dart';
import '../components/dmrv_button.dart';
import '../design/premium_field_components.dart';
import '../design/tokens.dart';
import 'pyrolysis_screen.dart';

/// The kiln chosen for the current burn. Held for the session so the pyrolysis
/// telemetry (and, on the same run, the yield) can stamp the real kiln id/type/
/// capacity instead of a hardcoded 200 L. Null until the operator selects one —
/// [KilnSelectScreen] is mandatory before a burn starts.
final selectedKilnProvider = StateProvider<Kiln?>((ref) => null);

/// Locally-known kilns (registered server-side by an admin; entered here for
/// selection). Newest first.
final kilnListProvider = StreamProvider<List<Kiln>>((ref) async* {
  final db = await ref.watch(appDatabaseProvider.future);
  yield* (db.select(db.kilns)
        ..orderBy([(t) => OrderingTerm.desc(t.addedAt)]))
      .watch();
});

/// Mandatory kiln selection before pyrolysis. Lists known kilns as radio rows,
/// offers a manual ADD KILN form (no QR scanner in the app yet), and only
/// enables START BURN once a kiln is selected.
class KilnSelectScreen extends ConsumerStatefulWidget {
  const KilnSelectScreen({super.key});

  @override
  ConsumerState<KilnSelectScreen> createState() => _KilnSelectScreenState();
}

class _KilnSelectScreenState extends ConsumerState<KilnSelectScreen> {
  bool _showAddForm = false;
  bool _savingKiln = false;
  String? _addError;

  final _idCtrl = TextEditingController();
  final _capacityCtrl = TextEditingController();
  final _labelCtrl = TextEditingController();
  String _addType = 'open';

  @override
  void dispose() {
    _idCtrl.dispose();
    _capacityCtrl.dispose();
    _labelCtrl.dispose();
    super.dispose();
  }

  Future<void> _saveKiln() async {
    if (_savingKiln) return;
    final id = _idCtrl.text.trim();
    final capacity = double.tryParse(_capacityCtrl.text.trim());
    if (id.isEmpty) {
      setState(() => _addError = 'Enter the kiln ID.');
      return;
    }
    if (capacity == null || capacity <= 0) {
      setState(() => _addError = 'Enter a positive capacity in litres.');
      return;
    }
    setState(() {
      _savingKiln = true;
      _addError = null;
    });
    try {
      final db = await ref.read(appDatabaseProvider.future);
      final kiln = Kiln(
        kilnId: id,
        kilnType: _addType,
        capacityLitres: capacity,
        label: _labelCtrl.text.trim().isEmpty ? null : _labelCtrl.text.trim(),
        addedAt: DateTime.now().toUtc().toIso8601String(),
      );
      await db.into(db.kilns).insertOnConflictUpdate(kiln);
      ref.read(selectedKilnProvider.notifier).state = kiln;
      if (mounted) {
        setState(() {
          _showAddForm = false;
          _idCtrl.clear();
          _capacityCtrl.clear();
          _labelCtrl.clear();
        });
      }
    } catch (e) {
      if (mounted) setState(() => _addError = e.toString());
    } finally {
      if (mounted) setState(() => _savingKiln = false);
    }
  }

  void _startBurn() {
    Navigator.of(context).push(
      MaterialPageRoute<void>(builder: (_) => const PyrolysisScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final kilns = ref.watch(kilnListProvider).valueOrNull ?? const <Kiln>[];
    final selected = ref.watch(selectedKilnProvider);

    return Scaffold(
      backgroundColor: t.surface,
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            PremiumScreenHeader(
              stepNumber: '03',
              title: 'Select Kiln',
              onBack: () => Navigator.of(context).pop(),
            ),
            Expanded(
              child: ListView(
                padding: EdgeInsets.fromLTRB(t.gapL, 4, t.gapL, t.gapL),
                children: [
                  Text(
                    'Choose the kiln used for this burn. This stamps the real '
                    'kiln ID, type and volume onto the telemetry evidence.',
                    style: t.body.copyWith(color: t.textPrimary),
                  ),
                  SizedBox(height: t.gapL),
                  if (kilns.isEmpty && !_showAddForm)
                    _emptyHint(t)
                  else
                    for (final k in kilns) ...[
                      _kilnRow(t, k, selected?.kilnId == k.kilnId),
                      SizedBox(height: t.gapM),
                    ],
                  SizedBox(height: t.gapM),
                  if (_showAddForm)
                    _addForm(t)
                  else
                    DmrvButton(
                      label: 'ADD KILN',
                      testId: 'add-kiln-btn',
                      icon: Icons.add,
                      variant: DmrvButtonVariant.neutral,
                      onPressed: () => setState(() => _showAddForm = true),
                    ),
                  SizedBox(height: t.gapXL),
                  DmrvButton(
                    label: selected != null
                        ? 'START BURN'
                        : 'LOCKED // SELECT A KILN',
                    testId: 'start-burn-btn',
                    variant: DmrvButtonVariant.primary,
                    onPressed: selected != null ? _startBurn : null,
                  ),
                  SizedBox(height: t.gapL),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _emptyHint(DmrvTokens t) {
    return PremiumFieldPanel(
      child: Text(
        'No kilns yet. Tap ADD KILN to register the kiln you are burning in.',
        style: t.body.copyWith(color: t.textSecondary),
      ),
    );
  }

  Widget _kilnRow(DmrvTokens t, Kiln k, bool isSelected) {
    return Semantics(
      identifier: 'kiln-row-${k.kilnId}',
      button: true,
      selected: isSelected,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(t.radiusM),
          onTap: () {
            HapticFeedback.selectionClick();
            ref.read(selectedKilnProvider.notifier).state = k;
          },
          child: PremiumFieldPanel(
            accentBorderColor: isSelected ? t.success : null,
            child: Row(
              children: [
                Icon(
                  isSelected
                      ? Icons.radio_button_checked
                      : Icons.radio_button_unchecked,
                  color: isSelected ? t.success : t.textSecondary,
                ),
                SizedBox(width: t.gapM),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        k.label?.isNotEmpty == true ? k.label! : k.kilnId,
                        style: t.body.copyWith(
                          fontWeight: FontWeight.w700,
                          color: t.textPrimary,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        '${k.kilnType.toUpperCase()} · '
                        '${k.capacityLitres?.toStringAsFixed(0) ?? '—'} L · '
                        '${k.kilnId}',
                        style: t.metadata.copyWith(color: t.textSecondary),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _addForm(DmrvTokens t) {
    return PremiumFieldPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('ADD KILN', style: t.chipLabel.copyWith(color: t.accentText)),
          SizedBox(height: t.gapM),
          _field(t, 'Kiln ID', _idCtrl, 'kiln-id-input', 'e.g. KILN-42'),
          SizedBox(height: t.gapM),
          _field(
            t,
            'Capacity (litres)',
            _capacityCtrl,
            'kiln-capacity-input',
            'e.g. 200',
            numeric: true,
          ),
          SizedBox(height: t.gapM),
          _field(t, 'Label (optional)', _labelCtrl, 'kiln-label-input', ''),
          SizedBox(height: t.gapM),
          Text('KILN TYPE', style: t.chipLabel.copyWith(color: t.accentText)),
          SizedBox(height: t.gapS),
          Row(
            children: [
              Expanded(child: _typeChip(t, 'open', 'OPEN')),
              SizedBox(width: t.gapM),
              Expanded(child: _typeChip(t, 'closed', 'CLOSED')),
            ],
          ),
          if (_addError != null) ...[
            SizedBox(height: t.gapM),
            Text(
              _addError!,
              style: t.metadata.copyWith(fontSize: 13, color: t.danger),
            ),
          ],
          SizedBox(height: t.gapL),
          DmrvButton(
            label: _savingKiln ? 'SAVING…' : 'SAVE KILN',
            testId: 'save-kiln-btn',
            variant: DmrvButtonVariant.success,
            onPressed: _savingKiln ? null : _saveKiln,
          ),
        ],
      ),
    );
  }

  Widget _typeChip(DmrvTokens t, String value, String label) {
    final selected = _addType == value;
    return Semantics(
      identifier: 'kiln-type-$value',
      button: true,
      selected: selected,
      child: Material(
        color: selected ? t.success : t.surface,
        borderRadius: BorderRadius.circular(t.radiusM),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: () => setState(() => _addType = value),
          child: Container(
            constraints: const BoxConstraints(minHeight: 52),
            alignment: Alignment.center,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(t.radiusM),
              border: Border.all(
                color: selected ? t.success : t.border,
                width: 1.5,
              ),
            ),
            child: Text(
              label,
              style: t.buttonLabel.copyWith(
                fontSize: 15,
                color: selected ? t.onSuccess : t.textPrimary,
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _field(
    DmrvTokens t,
    String label,
    TextEditingController controller,
    String testId,
    String hint, {
    bool numeric = false,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: t.chipLabel.copyWith(color: t.textSecondary)),
        const SizedBox(height: 6),
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
              keyboardType: numeric
                  ? const TextInputType.numberWithOptions(decimal: true)
                  : TextInputType.text,
              inputFormatters: numeric
                  ? [FilteringTextInputFormatter.allow(RegExp(r'[0-9.]'))]
                  : null,
              cursorColor: t.accentText,
              style: t.body.copyWith(color: t.textPrimary),
              decoration: InputDecoration(
                border: InputBorder.none,
                isCollapsed: true,
                contentPadding: const EdgeInsets.symmetric(vertical: 10),
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
