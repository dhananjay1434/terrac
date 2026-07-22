import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/services/geofence_check.dart';

/// V8 Part 4 (E) — on-device geofence-warning pure math. A 1km x 1km square
/// roughly centered near the equator (where 1 degree ~= 111.32km) so meter
/// math stays easy to reason about by hand.
void main() {
  // ~0.009 degrees ~= 1km at the equator.
  final square = [
    [0.0, 0.0],
    [0.009, 0.0],
    [0.009, 0.009],
    [0.0, 0.009],
  ];

  group('isPointInPolygonRing', () {
    test('point well inside the square is inside', () {
      expect(isPointInPolygonRing(0.0045, 0.0045, square), isTrue);
    });

    test('point well outside the square is outside', () {
      expect(isPointInPolygonRing(0.5, 0.5, square), isFalse);
    });

    test('degenerate ring (< 3 points) is never inside', () {
      expect(isPointInPolygonRing(0.0045, 0.0045, [
        [0.0, 0.0],
        [0.009, 0.009],
      ]), isFalse);
    });
  });

  group('isPointNearPolygon', () {
    test('inside point is near (trivially)', () {
      expect(isPointNearPolygon(0.0045, 0.0045, square), isTrue);
    });

    test('a point just outside the edge is within the default 10m buffer', () {
      // ~0.00005 deg longitude at the equator is ~5.5m — inside the buffer.
      expect(
        isPointNearPolygon(0.00905, 0.0045, square, bufferMeters: 10.0),
        isTrue,
      );
    });

    test('a point far outside the edge exceeds the buffer', () {
      expect(
        isPointNearPolygon(0.05, 0.0045, square, bufferMeters: 10.0),
        isFalse,
      );
    });

    test('bufferMeters <= 0 disables the buffer (exact containment only)', () {
      expect(
        isPointNearPolygon(0.00905, 0.0045, square, bufferMeters: 0),
        isFalse,
      );
    });
  });

  group('parsePolygonExteriorRing', () {
    test('parses a well-formed Polygon GeoJSON string', () {
      final geojson =
          '{"type":"Polygon","coordinates":[[[0.0,0.0],[0.009,0.0],[0.009,0.009],[0.0,0.009],[0.0,0.0]]]}';
      final ring = parsePolygonExteriorRing(geojson);
      expect(ring, isNotNull);
      expect(ring!.length, 5);
      expect(ring[0], [0.0, 0.0]);
      // A ring parsed this way still works with the point-in-polygon check.
      expect(isPointInPolygonRing(0.0045, 0.0045, ring), isTrue);
    });

    test('wrong geometry type returns null', () {
      final geojson = '{"type":"Point","coordinates":[0.0,0.0]}';
      expect(parsePolygonExteriorRing(geojson), isNull);
    });

    test('malformed JSON returns null, never throws', () {
      expect(parsePolygonExteriorRing('not json'), isNull);
    });

    test('missing coordinates returns null', () {
      expect(parsePolygonExteriorRing('{"type":"Polygon"}'), isNull);
    });

    test('too few points returns null', () {
      final geojson = '{"type":"Polygon","coordinates":[[[0.0,0.0],[1.0,1.0]]]}';
      expect(parsePolygonExteriorRing(geojson), isNull);
    });

    test('non-numeric coordinate values return null', () {
      final geojson =
          '{"type":"Polygon","coordinates":[[["a","b"],[1.0,0.0],[1.0,1.0]]]}';
      expect(parsePolygonExteriorRing(geojson), isNull);
    });
  });
}
