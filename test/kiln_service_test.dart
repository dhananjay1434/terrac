import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'package:dmrv_app/services/kiln_service.dart';

/// P2.4 — KilnService's offline-first contract (mirrors ProjectService's
/// contract: a failed/absent fetch returns the cache, never throws; empty
/// kilnId / no cache returns null). Also covers the case ProjectService's own
/// test suite doesn't: the HTTP client itself throwing mid-request (e.g. a
/// DNS failure) must still resolve to the cache, never propagate.
class _ThrowingClient extends http.BaseClient {
  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) {
    throw Exception('network down');
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    FlutterSecureStorage.setMockInitialValues({});
    SharedPreferences.setMockInitialValues({});
  });

  test('loadCached returns null when nothing is cached', () async {
    final cached = await KilnService.loadCached('kiln-none');
    expect(cached, null);
  });

  test('fetchKilnProfile with empty kilnId returns null, never throws', () async {
    final result = await KilnService.fetchKilnProfile('');
    expect(result, null);
  });

  test('fetchKilnProfile with no api base falls back to cache (empty here)', () async {
    // No DMRV_API_BASE_URL dart-define and no persisted secure-storage value
    // in this test env, so resolveApiBaseUrl() returns '' and the fetch
    // short-circuits straight to the (empty) cache — never throws.
    final result = await KilnService.fetchKilnProfile('kiln-x');
    expect(result, null);
  });

  test(
    'fetchKilnProfile returns the cached profile when the HTTP client throws',
    () async {
      SharedPreferences.setMockInitialValues({
        'dmrv.kiln_profile.v1.kiln-cached': 'full',
      });
      final result = await KilnService.fetchKilnProfile(
        'kiln-cached',
        client: _ThrowingClient(),
        apiBaseUrl: 'https://example.invalid',
      );
      expect(result, 'full');
    },
  );

  test(
    'fetchKilnProfile caches and returns the profile on a 200 response',
    () async {
      final client = _RecordingClient(
        http.Response(jsonEncode({'sensor_profile': 'thermal_only'}), 200),
      );
      final result = await KilnService.fetchKilnProfile(
        'kiln-live',
        client: client,
        apiBaseUrl: 'https://example.invalid',
      );
      expect(result, 'thermal_only');
      final cached = await KilnService.loadCached('kiln-live');
      expect(cached, 'thermal_only');
    },
  );
}

class _RecordingClient extends http.BaseClient {
  _RecordingClient(this._response);
  final http.Response _response;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    return http.StreamedResponse(
      Stream.value(utf8.encode(_response.body)),
      _response.statusCode,
    );
  }
}
