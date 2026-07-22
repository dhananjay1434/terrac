import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:dmrv_app/ui/screens/field_walk_screen.dart';

/// V8 Part 5 (A phase-2) — the scan step is the only stage renderable
/// without a live camera/GPS/network stack (same documented limitation as
/// SecureCameraScreen elsewhere). This verifies the entry state.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  testWidgets('initial state shows the scan-link entry point', (tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(home: FieldWalkScreen()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('SCAN FIELD-WALK LINK'), findsOneWidget);
    expect(find.text('Field-Walk Boundary'), findsOneWidget);
  });
}
