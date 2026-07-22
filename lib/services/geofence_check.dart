import 'dart:convert';
import 'dart:math' as math;

/// V8 Part 4 (E) — pure, on-device geofence-to-parcel check. This is a FAST,
/// approximate WARNING only for the capture UI ("this photo looks outside
/// the registered parcel — continue anyway?"); it is never the source of
/// truth. The authoritative check remains the server-side corroboration in
/// `backend/geometry.py::point_in_polygon` (shapely + true geodesic buffer).
///
/// [ring] is the polygon exterior ring as `[lon, lat]` pairs (GeoJSON
/// coordinate order), first ring only — interior rings/holes are not
/// evaluated on-device.
const double _kMetersPerDegree = 111320.0;

/// Deferred R4 — parses a GeoJSON Polygon string's exterior ring into
/// `[lon, lat]` pairs for [isPointNearPolygon]/[isPointInPolygonRing].
/// Returns null for anything malformed (wrong geometry type, missing/short
/// coordinates, non-numeric values) — never throws, so a corrupt or
/// unexpected cached geometry just leaves the capture ungated rather than
/// crashing the screen.
List<List<double>>? parsePolygonExteriorRing(String geojson) {
  try {
    final decoded = jsonDecode(geojson);
    if (decoded is! Map || decoded['type'] != 'Polygon') return null;
    final coords = decoded['coordinates'];
    if (coords is! List || coords.isEmpty) return null;
    final exterior = coords[0];
    if (exterior is! List) return null;

    final ring = <List<double>>[];
    for (final pt in exterior) {
      if (pt is! List || pt.length < 2) return null;
      final lon = pt[0];
      final lat = pt[1];
      if (lon is! num || lat is! num) return null;
      ring.add([lon.toDouble(), lat.toDouble()]);
    }
    if (ring.length < 3) return null;
    return ring;
  } catch (_) {
    return null;
  }
}

/// Standard ray-casting point-in-polygon test (even-odd rule).
bool isPointInPolygonRing(double lon, double lat, List<List<double>> ring) {
  if (ring.length < 3) return false;
  var inside = false;
  final n = ring.length;
  for (var i = 0, j = n - 1; i < n; j = i++) {
    final xi = ring[i][0], yi = ring[i][1];
    final xj = ring[j][0], yj = ring[j][1];
    final intersects =
        ((yi > lat) != (yj > lat)) &&
        (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi);
    if (intersects) inside = !inside;
  }
  return inside;
}

double _distanceMetersPointToSegment(
  double px,
  double py,
  double ax,
  double ay,
  double bx,
  double by,
) {
  final dx = bx - ax, dy = by - ay;
  if (dx == 0 && dy == 0) {
    return math.sqrt((px - ax) * (px - ax) + (py - ay) * (py - ay));
  }
  final t = (((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)).clamp(
    0.0,
    1.0,
  );
  final projX = ax + t * dx, projY = ay + t * dy;
  return math.sqrt((px - projX) * (px - projX) + (py - projY) * (py - projY));
}

/// True if the point is inside [ring], or within [bufferMeters] of its edge.
/// Mirrors the backend's cos(lat) longitude correction (see
/// `geometry.py::point_in_polygon`) so the buffer stays isotropic in meters
/// rather than under-buffering east-west near the poles.
bool isPointNearPolygon(
  double lon,
  double lat,
  List<List<double>> ring, {
  double bufferMeters = 10.0,
}) {
  if (isPointInPolygonRing(lon, lat, ring)) return true;
  if (bufferMeters <= 0 || ring.length < 2) return false;

  final cosLat = math.cos(lat * math.pi / 180).abs().clamp(1e-9, 1.0);
  double toX(double lo) => lo * _kMetersPerDegree * cosLat;
  double toY(double la) => la * _kMetersPerDegree;

  final px = toX(lon), py = toY(lat);
  final n = ring.length;
  for (var i = 0, j = n - 1; i < n; j = i++) {
    final ax = toX(ring[i][0]), ay = toY(ring[i][1]);
    final bx = toX(ring[j][0]), by = toY(ring[j][1]);
    final d = _distanceMetersPointToSegment(px, py, ax, ay, bx, by);
    if (d <= bufferMeters) return true;
  }
  return false;
}
