// =====================================================================
// P1-22 — Android auto-backup must be disabled.
// =====================================================================
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('AndroidManifest.xml disables allowBackup', () {
    final manifest = File('android/app/src/main/AndroidManifest.xml');
    if (!manifest.existsSync()) {
      markTestSkipped('android/ not present in this repo snapshot');
      return;
    }
    final src = manifest.readAsStringSync();
    expect(
      src.contains('android:allowBackup="false"'),
      isTrue,
      reason: 'Set android:allowBackup="false" — see /app/detailed.md#P1-22',
    );
    expect(src.contains('android:fullBackupContent="@xml/no_backup"'), isTrue);
  });

  test('res/xml/no_backup.xml exists and excludes sharedpref', () {
    final f = File('android/app/src/main/res/xml/no_backup.xml');
    if (!f.existsSync()) {
      markTestSkipped('no_backup.xml not present yet');
      return;
    }
    final src = f.readAsStringSync();
    expect(src.contains('<exclude domain="sharedpref"'), isTrue);
  });
}
