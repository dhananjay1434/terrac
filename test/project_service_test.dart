import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:dmrv_app/services/project_service.dart';

/// FM-4 — ProjectConfig JSON round-trip + the offline-first cache
/// (mirrors ParcelService's contract: a failed/absent fetch returns the
/// cache, never throws; empty project_id / no cache returns null).
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
    SharedPreferences.setMockInitialValues({});
  });

  test('ProjectConfig round-trips through toJson/fromJson', () {
    const config = ProjectConfig(
      allowedFeedstocks: ['Wood_chips'],
      positiveList: ['Agricultural_waste', 'Lantana_camara', 'Wood_chips'],
      clientTarget: 12,
    );
    final decoded = ProjectConfig.fromJson(config.toJson());
    expect(decoded.allowedFeedstocks, ['Wood_chips']);
    expect(decoded.positiveList, [
      'Agricultural_waste',
      'Lantana_camara',
      'Wood_chips',
    ]);
    expect(decoded.clientTarget, 12);
  });

  test('fromJson tolerates missing fields (no crash)', () {
    final decoded = ProjectConfig.fromJson({});
    expect(decoded.allowedFeedstocks, isEmpty);
    expect(decoded.positiveList, isEmpty);
    expect(decoded.clientTarget, isNull);
  });

  test('loadCached returns null when nothing is cached', () async {
    final cached = await ProjectService.loadCached('proj-none');
    expect(cached, isNull);
  });

  test('fetchProjectConfig with empty projectId returns null, never throws', () async {
    final result = await ProjectService.fetchProjectConfig('');
    expect(result, isNull);
  });

  test('fetchProjectConfig with no api base falls back to cache (empty here)', () async {
    // No DMRV_API_BASE_URL dart-define and no persisted secure-storage
    // value in this test env, so resolveApiBaseUrl() returns '' and the
    // fetch short-circuits straight to the (empty) cache — never throws.
    final result = await ProjectService.fetchProjectConfig('proj-x');
    expect(result, isNull);
  });
}
