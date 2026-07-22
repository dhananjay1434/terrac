import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:dmrv_app/ui/screens/dispatch/dispatch_screen.dart';

/// Deferred R1 — dispatch media capture rows. The capture flow itself needs
/// a real camera (same documented limitation as farmer_kyc_media_test.dart);
/// the outbox payload shape is covered at the writer level in
/// entity_media_outbox_test.dart ("dispatch media enqueues with
/// subject_type=dispatch"). This covers the gating this screen adds:
/// capture rows must not appear before a dispatch draft exists (there's no
/// dispatch_uuid yet to attach media to).
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() => FlutterSecureStorage.setMockInitialValues({}));

  testWidgets('media capture rows are absent before a draft is created', (
    tester,
  ) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(home: DispatchScreen()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('CAPTURE TRUCK PHOTO'), findsNothing);
    expect(find.text('CAPTURE INVOICE PHOTO'), findsNothing);
    expect(find.text('CAPTURE WEIGH TICKET'), findsNothing);
    // The draft form itself renders, confirming the screen didn't crash.
    expect(find.text('New Dispatch'), findsOneWidget);
  });
}
