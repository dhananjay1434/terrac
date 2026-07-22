import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:dmrv_app/services/parcel_service.dart';

/// Deferred R4 — parcel geometry caching. Rides the SAME SharedPreferences
/// cache `ParcelOption` already used for uuid/name (Part 1.6) — no separate
/// store or Drift table needed, since the geometry travels inside the same
/// cached JSON blob per project.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  const projectId = 'proj-geo-test';
  final validGeojson =
      '{"type":"Polygon","coordinates":[[[0.0,0.0],[0.01,0.0],[0.01,0.01],[0.0,0.01],[0.0,0.0]]]}';

  Future<void> seedCache(List<ParcelOption> parcels) async {
    SharedPreferences.setMockInitialValues({
      'dmrv.parcels.v1.$projectId':
          jsonEncode(parcels.map((p) => p.toJson()).toList()),
    });
  }

  group('ParcelOption geometry round-trip', () {
    test('toJson/fromJson preserves boundary_geojson when present', () {
      const opt = ParcelOption(
        uuid: 'p1',
        name: 'Field 1',
        boundaryGeojson: '{"type":"Polygon","coordinates":[]}',
      );
      final roundTripped = ParcelOption.fromJson(opt.toJson());
      expect(roundTripped.boundaryGeojson, opt.boundaryGeojson);
    });

    test('toJson omits the key entirely when geometry is absent', () {
      const opt = ParcelOption(uuid: 'p1', name: 'Field 1');
      expect(opt.toJson().containsKey('boundary_geojson'), isFalse);
    });

    test('boundaryRing is null when boundaryGeojson is absent', () {
      const opt = ParcelOption(uuid: 'p1', name: 'Field 1');
      expect(opt.boundaryRing, isNull);
    });

    test('boundaryRing parses a valid cached geometry', () {
      final opt = ParcelOption(
        uuid: 'p1',
        name: 'Field 1',
        boundaryGeojson: validGeojson,
      );
      expect(opt.boundaryRing, isNotNull);
      expect(opt.boundaryRing!.length, 5);
    });
  });

  group('ParcelService.boundaryRingFor', () {
    test('returns the ring for a cached parcel with geometry', () async {
      await seedCache([
        ParcelOption(uuid: 'p1', name: 'Field 1', boundaryGeojson: validGeojson),
      ]);
      final ring = await ParcelService.boundaryRingFor(projectId, 'p1');
      expect(ring, isNotNull);
      expect(ring!.length, 5);
    });

    test('returns null when the parcel has no cached geometry (flag off)', () async {
      await seedCache([
        const ParcelOption(uuid: 'p1', name: 'Field 1'),
      ]);
      final ring = await ParcelService.boundaryRingFor(projectId, 'p1');
      expect(ring, isNull);
    });

    test('returns null when the parcel uuid is not in the cache', () async {
      await seedCache([
        ParcelOption(uuid: 'p1', name: 'Field 1', boundaryGeojson: validGeojson),
      ]);
      final ring = await ParcelService.boundaryRingFor(projectId, 'nonexistent');
      expect(ring, isNull);
    });

    test('returns null when nothing is cached for the project', () async {
      SharedPreferences.setMockInitialValues({});
      final ring = await ParcelService.boundaryRingFor(projectId, 'p1');
      expect(ring, isNull);
    });
  });
}
