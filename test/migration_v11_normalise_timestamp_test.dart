// =====================================================================
// P1-17 — Migration v11 must normalise non-UTC timestamps to ISO-Z.
//
// Strategy: open the DB at schemaVersion <= 10 (via createV10),
// stuff a row with a `+05:30` timestamp, then run the migration. The
// resulting system_metadata.created_at must end with 'Z'.
//
// NOTE: This requires a `createV10()` helper or a Drift schema-history
// fixture. If your project does not yet expose one, treat this file as
// a TODO checkpoint until the fixture is added.
// =====================================================================
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('migration v11 normalises +05:30 timestamps to UTC Z', () {
    markTestSkipped(
      'Requires Drift schema-history fixture for v10. '
      'Add via `dart run drift_dev schema dump` and re-enable.',
    );
  });
}
