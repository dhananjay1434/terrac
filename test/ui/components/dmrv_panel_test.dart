import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:dmrv_app/ui/components/dmrv_panel.dart';
import 'package:dmrv_app/ui/design/tokens.dart';

void main() {
  testWidgets('DmrvPanel renders its child and paints the raised surface', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: buildDmrvTheme(DmrvTokens.india),
        home: const Scaffold(
          body: DmrvPanel(child: Text('panel body')),
        ),
      ),
    );
    expect(find.text('panel body'), findsOneWidget);

    final container = tester.widget<Container>(
      find
          .descendant(
            of: find.byType(DmrvPanel),
            matching: find.byType(Container),
          )
          .first,
    );
    final decoration = container.decoration as BoxDecoration;
    expect(decoration.color, DmrvTokens.india.surfaceRaised);
  });
}
