import 'package:flutter_test/flutter_test.dart';
import 'package:drift/native.dart';
import 'package:dmrv_app/data/local/app_database.dart';

void main() {
  test('AppDatabase migration from 1 to latest completes without customStatement deadlock', () async {
    final db = AppDatabase.forTesting(NativeDatabase.memory());
    // Executing any query forces the database to open and run migrations.
    // If migrations use customStatement (which delegates to the main executor),
    // it will deadlock and timeout, or throw. With m.issueCustomQuery, it passes.
    await db.customSelect('SELECT 1').get();
    await db.close();
  });
}
