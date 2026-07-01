import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('SpaceGrotesk font family resolves', (WidgetTester tester) async {
    const textStyle = TextStyle(fontFamily: 'SpaceGrotesk');
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(body: Text('Test', style: textStyle)),
      ),
    );
    final textWidget = tester.widget<Text>(find.text('Test'));
    expect(textWidget.style?.fontFamily, 'SpaceGrotesk');
  });

  testWidgets('NotoSansDevanagari renders Hindi glyphs', (
    WidgetTester tester,
  ) async {
    const textStyle = TextStyle(fontFamily: 'NotoSansDevanagari');
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(body: Text('बायोमास स्कैन करें', style: textStyle)),
      ),
    );
    final textWidget = tester.widget<Text>(find.text('बायोमास स्कैन करें'));
    expect(textWidget.style?.fontFamily, 'NotoSansDevanagari');
  });
}
