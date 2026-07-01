import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:drift/native.dart';
import 'package:dmrv_app/data/local/app_database.dart';
import 'package:dmrv_app/data/local/wipe_context.dart';
import 'package:mocktail/mocktail.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class _FakeWipeContext implements WipeContext {
  @override
  Future<Directory> getDocsDir() async => Directory.systemTemp;

  @override
  Future<void> deleteSecureKey(String key) async {}

  @override
  Future<void> clearHmacKey() async {}
}

class MockRef extends Mock implements Ref {}

void main() {
  test(
    'secureWipe executes PRAGMA secure_delete without syntax errors',
    () async {
      final db = AppDatabase.forTesting(NativeDatabase.memory());
      final mockRef = MockRef();
      await db.secureWipe(
        ctx: _FakeWipeContext(),
        ref: mockRef,
      ); // Should not throw.
      // db is closed inside secureWipe — do not close again.
    },
  );
}
