import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:dmrv_app/services/simulation/demo_readiness.dart';
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('already enrolled → ok, no throw', () async {
    FlutterSecureStorage.setMockInitialValues({'device_enrolled': '1', 'device_id_key': 'edge-x'});
    final r = await ensureDemoReady();
    expect(r.ok, isTrue);
  });
  test('not enrolled + no token → soft-fails to not-ok WITHOUT throwing', () async {
    FlutterSecureStorage.setMockInitialValues({}); // unenrolled, no ENROLLMENT_TOKEN dart-define
    final r = await ensureDemoReady();               // must not throw
    expect(r.ok, isFalse);
    expect(r.detail, contains('enroll'));
  });
}
