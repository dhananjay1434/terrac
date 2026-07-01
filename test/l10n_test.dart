import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/l10n/app_localizations.dart';

void main() {
  testWidgets('English locale loads all strings', (WidgetTester tester) async {
    late AppLocalizations localizations;

    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('en'),
        home: Builder(
          builder: (context) {
            localizations = AppLocalizations.of(context)!;
            return const SizedBox.shrink();
          },
        ),
      ),
    );

    expect(localizations.tap_to_start, isNotEmpty);
    expect(localizations.no_pending_batch, isNotEmpty);
    expect(localizations.connect_crane_scale, isNotEmpty);
    expect(localizations.stabilize_reading, isNotEmpty);
    expect(localizations.stabilized, isNotEmpty);
    expect(localizations.scan_biomass_hindi, isNotEmpty);
    expect(localizations.connect_sensor_hindi, isNotEmpty);
    expect(localizations.record_yield_hindi, isNotEmpty);
  });

  testWidgets('Hindi locale loads all strings', (WidgetTester tester) async {
    late AppLocalizations localizations;

    await tester.pumpWidget(
      MaterialApp(
        localizationsDelegates: AppLocalizations.localizationsDelegates,
        supportedLocales: AppLocalizations.supportedLocales,
        locale: const Locale('hi'),
        home: Builder(
          builder: (context) {
            localizations = AppLocalizations.of(context)!;
            return const SizedBox.shrink();
          },
        ),
      ),
    );

    expect(localizations.tap_to_start, 'शुरू करने के लिए टैप करें');
  });

  test('no hardcoded Hindi strings remain', () {
    final libDir = Directory('lib');
    final files = libDir
        .listSync(recursive: true)
        .whereType<File>()
        .where((f) => f.path.endsWith('.dart'));

    bool found = false;
    final regex = RegExp(r'[\u0900-\u097F]');

    for (var file in files) {
      if (file.path.contains('app_localizations') || file.path.contains('.arb'))
        continue;
      final lines = file.readAsLinesSync();
      for (var i = 0; i < lines.length; i++) {
        if (regex.hasMatch(lines[i])) {
          found = true;
          print('Found Hindi string in ${file.path}:${i + 1}');
        }
      }
    }
    expect(found, isFalse);
  });
}
