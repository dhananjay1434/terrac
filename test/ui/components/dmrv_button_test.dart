import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:dmrv_app/ui/components/dmrv_button.dart';
import 'package:dmrv_app/ui/design/tokens.dart';

Widget _host(Widget child) => MaterialApp(
  theme: buildDmrvTheme(DmrvTokens.india),
  home: Scaffold(body: Center(child: child)),
);

void main() {
  group('DmrvButton', () {
    testWidgets('renders its label', (tester) async {
      await tester.pumpWidget(
        _host(DmrvButton(label: 'LOCK YIELD', onPressed: () {}, testId: 'b')),
      );
      expect(find.text('LOCK YIELD'), findsOneWidget);
    });

    testWidgets('enabled → tap fires onPressed', (tester) async {
      var taps = 0;
      await tester.pumpWidget(
        _host(
          DmrvButton(
            label: 'GO',
            testId: 'go-btn',
            onPressed: () => taps++,
          ),
        ),
      );
      await tester.tap(find.byType(DmrvButton));
      await tester.pump();
      expect(taps, 1);
    });

    testWidgets('disabled (onPressed null) → tap is a no-op', (tester) async {
      await tester.pumpWidget(
        _host(const DmrvButton(label: 'LOCKED', onPressed: null, testId: 'x')),
      );
      await tester.tap(find.byType(DmrvButton), warnIfMissed: false);
      await tester.pump();
      final btn = tester.widget<DmrvButton>(find.byType(DmrvButton));
      expect(btn.onPressed, isNull);
    });

    testWidgets('exposes its testId as a semantics identifier', (tester) async {
      await tester.pumpWidget(
        _host(DmrvButton(label: 'SAVE', testId: 'save-btn', onPressed: () {})),
      );
      expect(find.bySemanticsIdentifier('save-btn'), findsOneWidget);
    });
  });
}
