import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:dmrv_app/ui/design/app_theme.dart';
import 'package:dmrv_app/ui/design/premium_field_components.dart';

Widget _host(Widget child) {
  return MaterialApp(
    theme: AppTheme.lightTheme,
    home: Scaffold(body: child),
  );
}

void main() {
  group('PremiumFieldButton', () {
    testWidgets('state: go renders an enabled InkWell with a non-null onTap', (
      tester,
    ) async {
      var taps = 0;
      await tester.pumpWidget(
        _host(
          PremiumFieldButton(
            label: 'PROCEED',
            state: FieldButtonState.go,
            onPressed: () => taps++,
          ),
        ),
      );

      final inkWell = tester.widget<InkWell>(find.byType(InkWell));
      expect(
        inkWell.onTap,
        isNotNull,
        reason: 'go-state button must have an active onTap',
      );

      await tester.tap(find.byType(InkWell));
      await tester.pump();
      expect(taps, 1, reason: 'tap must fire the supplied callback');
    });

    testWidgets('state: locked renders an InkWell with onTap == null even '
        'when onPressed is provided', (tester) async {
      await tester.pumpWidget(
        _host(
          PremiumFieldButton(
            label: 'LOCKED',
            state: FieldButtonState.locked,
            onPressed: () {}, // explicitly non-null, must still be disabled
          ),
        ),
      );

      final inkWell = tester.widget<InkWell>(find.byType(InkWell));
      expect(
        inkWell.onTap,
        isNull,
        reason: 'locked state must hard-disable taps regardless of onPressed',
      );
    });
  });

  group('PremiumFieldPanel', () {
    testWidgets('accentBorderColor: yieldGold renders a yieldGold border', (
      tester,
    ) async {
      await tester.pumpWidget(
        _host(
          const PremiumFieldPanel(
            accentBorderColor: AppTheme.yieldGold,
            child: SizedBox(width: 100, height: 100),
          ),
        ),
      );

      // The first Container under PremiumFieldPanel carries the BoxDecoration.
      final container = tester.widget<Container>(
        find
            .descendant(
              of: find.byType(PremiumFieldPanel),
              matching: find.byType(Container),
            )
            .first,
      );

      final decoration = container.decoration as BoxDecoration;
      final border = decoration.border as Border;
      expect(
        border.top.color,
        AppTheme.yieldGold,
        reason: 'accentBorderColor must override the default cobalt edge',
      );
      expect(
        border.top.width,
        2,
        reason: 'accent border must render at 2px to read in sun',
      );
    });
  });
}
