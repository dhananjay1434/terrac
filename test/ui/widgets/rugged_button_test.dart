import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:dmrv_app/ui/design/app_theme.dart';
import 'package:dmrv_app/ui/design/farmer_theme.dart';
import 'package:dmrv_app/ui/widgets/rugged_button.dart';

// Mirror test/premium_components_test.dart: a minimal MaterialApp host with
// AppTheme.lightTheme so the SpaceGrotesk font tokens resolve. RuggedButton
// paints explicit FarmerTheme colours, so the host theme choice does not
// affect the colour assertions below.
Widget _host(Widget child) {
  return MaterialApp(
    theme: AppTheme.lightTheme,
    home: Scaffold(body: child),
  );
}

void main() {
  group('RuggedButton', () {
    testWidgets('renders with minHeight >= 64', (tester) async {
      await tester.pumpWidget(
        _host(
          RuggedButton(
            label: 'WEIGH BATCH',
            variant: RuggedButtonVariant.primary,
            onPressed: () {},
          ),
        ),
      );

      final Size size = tester.getSize(find.byType(RuggedButton));
      expect(
        size.height,
        greaterThanOrEqualTo(64),
        reason: 'glove targets must be at least 64px tall',
      );
    });

    testWidgets('primary variant: background is neonYellow', (tester) async {
      await tester.pumpWidget(
        _host(
          RuggedButton(
            label: 'WEIGH BATCH',
            variant: RuggedButtonVariant.primary,
            onPressed: () {},
          ),
        ),
      );

      final material = tester.widget<Material>(
        find
            .descendant(
              of: find.byType(RuggedButton),
              matching: find.byType(Material),
            )
            .first,
      );
      expect(
        material.color,
        FarmerTheme.neonYellow,
        reason: 'primary CTA must paint the neonYellow action colour',
      );
    });

    testWidgets(
      'disabled variant: onTap is null even when onPressed is non-null',
      (tester) async {
        await tester.pumpWidget(
          _host(
            RuggedButton(
              label: 'LOCKED',
              variant: RuggedButtonVariant.disabled,
              onPressed: () {}, // explicitly non-null, must still be disabled
            ),
          ),
        );

        final inkWell = tester.widget<InkWell>(find.byType(InkWell));
        expect(
          inkWell.onTap,
          isNull,
          reason:
              'disabled variant must hard-disable taps regardless of onPressed',
        );
      },
    );

    testWidgets('enabled tap fires the callback', (tester) async {
      var taps = 0;
      await tester.pumpWidget(
        _host(
          RuggedButton(
            label: 'CONFIRM',
            variant: RuggedButtonVariant.success,
            onPressed: () => taps++,
          ),
        ),
      );

      await tester.tap(find.byType(InkWell));
      await tester.pump();
      expect(taps, 1, reason: 'enabled tap must fire the supplied callback');
    });
  });
}
