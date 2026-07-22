"""V8 Part 1.1 — geometry core unit tests.

Covers:
- Known square area calculation (geodesic accuracy)
- Overlap ratio calculation (accept/reject, sliver floor filtering)
- Invalid/self-intersecting polygon validation
- DoS guard_complexity checks (vertex count bomb, NaN/Inf, out-of-range coords)
- Point-in-polygon checks (inside, outside, buffer edge)
"""

import json
import pytest
from shapely.geometry import Polygon

import geometry


def _make_geojson_square(min_lon=0.0, min_lat=0.0, size_deg=0.001):
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [min_lon, min_lat],
                [min_lon + size_deg, min_lat],
                [min_lon + size_deg, min_lat + size_deg],
                [min_lon, min_lat + size_deg],
                [min_lon, min_lat],
            ]
        ],
    }


def test_area_of_known_square():
    # ~100m x 100m square near equator
    # 0.0009 degrees is approx 100m
    geojson = _make_geojson_square(0.0, 0.0, 0.0009)
    poly = geometry.parse_geojson(geojson)
    valid_poly = geometry.validate_polygon(poly)
    area = geometry.geodesic_area_m2(valid_poly)
    # 100m x 100m = 10,000 m^2. Near 0,0 0.0009 deg is ~100.18m => ~10,037 m^2
    assert 9500 <= area <= 10500


def test_bbox_extraction():
    geojson = _make_geojson_square(10.0, 20.0, 0.01)
    poly = geometry.parse_geojson(geojson)
    min_lat, min_lon, max_lat, max_lon = geometry.bbox_of(poly)
    assert pytest.approx(min_lat) == 20.0
    assert pytest.approx(min_lon) == 10.0
    assert pytest.approx(max_lat) == 20.01
    assert pytest.approx(max_lon) == 10.01


def test_overlap_ratio_calculation():
    # Square A: [0,0] to [0.01, 0.01] (~1.23 km^2)
    poly_a = geometry.parse_geojson(_make_geojson_square(0.0, 0.0, 0.01))
    
    # Square B: 50% overlap with A
    poly_b = geometry.parse_geojson(_make_geojson_square(0.005, 0.0, 0.01))

    # Square C: No overlap with A
    poly_c = geometry.parse_geojson(_make_geojson_square(0.05, 0.05, 0.01))

    ratio_ab = geometry.overlap_ratio(poly_a, poly_b)
    assert 0.45 <= ratio_ab <= 0.55

    ratio_ac = geometry.overlap_ratio(poly_a, poly_c)
    assert ratio_ac == 0.0


def test_sliver_floor_ignores_tiny_overlap(monkeypatch):
    # Two adjacent squares touching along an edge with tiny precision overlap (~50 m2)
    poly_a = geometry.parse_geojson({
        "type": "Polygon",
        "coordinates": [[[0,0], [0.001,0], [0.001,0.001], [0,0.001], [0,0]]]
    })
    # Slight overlap of ~1m width (0.00001 deg)
    poly_b = geometry.parse_geojson({
        "type": "Polygon",
        "coordinates": [[[0.00099,0], [0.002,0], [0.002,0.001], [0.00099,0.001], [0.00099,0]]]
    })

    # Slivers floor default is 200 m2; this ~100m x 1m overlap is ~100 m2 < 200 m2
    ratio = geometry.overlap_ratio(poly_a, poly_b)
    assert ratio == 0.0


def test_pathological_input_vertex_bomb():
    # > 5000 vertices
    coords = [[i * 0.00001, i * 0.00001] for i in range(5001)]
    coords.append(coords[0])
    payload = {"type": "Polygon", "coordinates": [coords]}
    
    with pytest.raises(ValueError, match="exceeds limit"):
        geometry.guard_complexity(payload)


def test_pathological_input_nan_or_inf():
    payload = {
        "type": "Polygon",
        "coordinates": [[[float("nan"), 0.0], [0.001, 0.0], [0.001, 0.001], [0.0, 0.0]]]
    }
    with pytest.raises(ValueError, match="finite"):
        geometry.guard_complexity(payload)


def test_pathological_input_out_of_bounds_coords():
    payload = {
        "type": "Polygon",
        "coordinates": [[[190.0, 0.0], [0.001, 0.0], [0.001, 0.001], [0.0, 0.0]]]
    }
    with pytest.raises(ValueError, match="Longitude"):
        geometry.guard_complexity(payload)

    payload_lat = {
        "type": "Polygon",
        "coordinates": [[[0.0, 95.0], [0.001, 0.0], [0.001, 0.001], [0.0, 0.0]]]
    }
    with pytest.raises(ValueError, match="Latitude"):
        geometry.guard_complexity(payload_lat)


def test_point_in_polygon_and_buffer():
    # Square from [0,0] to [0.01, 0.01] (~1.1 km x 1.1 km)
    poly = geometry.parse_geojson(_make_geojson_square(0.0, 0.0, 0.01))

    # Point clearly inside
    assert geometry.point_in_polygon(poly, 0.005, 0.005) is True

    # Point clearly outside (far)
    assert geometry.point_in_polygon(poly, 0.05, 0.05) is False

    # Point slightly outside (approx 5m outside edge: -0.00004 deg)
    assert geometry.point_in_polygon(poly, -0.00004, 0.005, buffer_m=10.0) is True
    # Without buffer (buffer=0), it's outside
    assert geometry.point_in_polygon(poly, -0.00004, 0.005, buffer_m=0.0) is False


def test_point_in_polygon_buffer_is_isotropic_in_meters_east_west():
    """Regression for the cos(lat) buffer bug: the buffer must be measured in
    METERS along longitude too. Near 60N, 1 deg lon is only ~55.66 km, so a
    naive uniform-degree buffer under-buffers E-W by ~2x and would falsely
    reject an honest edge capture. This point is 8 m east of the edge."""
    import math

    poly = geometry.parse_geojson(_make_geojson_square(0.0, 60.0, 0.01))
    lat = 60.005
    m_per_deg_lon = 111320.0 * math.cos(math.radians(lat))
    lon = 0.01 + 8.0 / m_per_deg_lon  # 8 m east of the east edge (lon=0.01)

    # 8 m is within a 10 m tolerance → inside. (The old uniform-degree buffer
    # gave ~4.4 m E-W here and returned False.)
    assert geometry.point_in_polygon(poly, lon, lat, buffer_m=10.0) is True
    # 8 m exceeds a 5 m tolerance → outside (proves it's a real metric distance).
    assert geometry.point_in_polygon(poly, lon, lat, buffer_m=5.0) is False


def test_to_geojson_str_roundtrips_via_trusted_parse():
    """Canonical persistence: a validated polygon serializes and re-parses
    (through the trusted, non-DoS-guarded path) to an equivalent valid polygon
    with a stable area — the property that lets create_parcel store canonical
    geometry and later overlap scans re-read it safely."""
    poly = geometry.validate_polygon(
        geometry.parse_geojson(_make_geojson_square(1.0, 1.0, 0.01))
    )
    reparsed = geometry.parse_trusted_geojson(geometry.to_geojson_str(poly))
    assert reparsed.is_valid
    assert abs(
        geometry.geodesic_area_m2(reparsed) - geometry.geodesic_area_m2(poly)
    ) < 1.0


# ---------------------------------------------------------------------------
# V8 Part 5 (A phase-2) — polygon_from_track_points
# ---------------------------------------------------------------------------


def test_polygon_from_track_points_builds_a_valid_polygon():
    points = [(0.0, 0.0), (0.01, 0.0), (0.01, 0.01), (0.0, 0.01)]
    poly = geometry.polygon_from_track_points(points)
    assert poly.is_valid
    assert geometry.geodesic_area_m2(poly) > 0


def test_polygon_from_track_points_closes_an_open_ring():
    """A device walk track naturally doesn't repeat its start point at the
    end — the function must close the ring itself rather than require the
    caller to."""
    open_points = [(0.0, 0.0), (0.01, 0.0), (0.01, 0.01), (0.0, 0.01)]
    closed_points = open_points + [open_points[0]]
    poly_open = geometry.polygon_from_track_points(open_points)
    poly_closed = geometry.polygon_from_track_points(closed_points)
    assert abs(
        geometry.geodesic_area_m2(poly_open) - geometry.geodesic_area_m2(poly_closed)
    ) < 1.0


def test_polygon_from_track_points_rejects_fewer_than_3_points():
    with pytest.raises(ValueError, match="at least 3 points"):
        geometry.polygon_from_track_points([(0.0, 0.0), (0.01, 0.0)])


def test_polygon_from_track_points_rejects_non_list_input():
    with pytest.raises(ValueError, match="at least 3 points"):
        geometry.polygon_from_track_points("not a list")


def test_polygon_from_track_points_enforces_complexity_guard():
    """An over-long track (e.g. a GPS logging bug appending duplicate points
    for hours) must not bypass the same DoS vertex-count guard untrusted
    portal-drawn polygons go through."""
    huge_track = [(0.0001 * i, 0.0001 * i) for i in range(20000)]
    with pytest.raises(ValueError):
        geometry.polygon_from_track_points(huge_track)


def test_polygon_from_track_points_rejects_out_of_range_coordinates():
    with pytest.raises(ValueError):
        geometry.polygon_from_track_points([(200.0, 0.0), (0.01, 0.0), (0.01, 0.01)])
