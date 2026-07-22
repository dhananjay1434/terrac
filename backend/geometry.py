"""V8 Part 1.1 — geometry core for source-parcel boundaries.

Pure functions only (no DB/HTTP dependencies): GeoJSON parsing, complexity guards
(DoS protection), polygon validation via shapely, geodesic area calculation via
pyproj (WGS84), bounding-box extraction, projected overlap calculation with sliver
flooring, and buffered point-in-polygon checks for GPS corroboration.
"""

from __future__ import annotations

import json
import math
from typing import Any, Dict, List, Tuple, Union

import pyproj
from shapely.geometry import MultiPolygon, Point, Polygon, mapping, shape
from shapely.ops import transform as _shp_transform
from shapely.validation import make_valid

import settings

_GEOD = pyproj.Geod(ellps="WGS84")


def guard_complexity(geojson_dict: Dict[str, Any]) -> None:
    """DoS Guard: validate complexity & coordinate bounds BEFORE running expensive
    shapely geometry operations.

    Raises ValueError with a descriptive reason if:
    - Coordinate values are non-finite (NaN, Inf) or out-of-range (lat∈[-90,90], lon∈[-180,180])
    - Total vertex count exceeds DMRV_PARCEL_MAX_VERTICES
    - Interior ring count exceeds 50
    """
    if not isinstance(geojson_dict, dict):
        raise ValueError("GeoJSON must be a JSON object.")

    geom_type = geojson_dict.get("type")
    if geom_type == "Feature":
        geom = geojson_dict.get("geometry")
        if not isinstance(geom, dict):
            raise ValueError("GeoJSON Feature missing valid 'geometry' object.")
        geojson_dict = geom
        geom_type = geojson_dict.get("type")
    elif geom_type == "FeatureCollection":
        features = geojson_dict.get("features")
        if not isinstance(features, list) or not features:
            raise ValueError("GeoJSON FeatureCollection contains no features.")
        geom = features[0].get("geometry")
        if not isinstance(geom, dict):
            raise ValueError("First feature in FeatureCollection missing geometry.")
        geojson_dict = geom
        geom_type = geojson_dict.get("type")

    if geom_type != "Polygon":
        raise ValueError(f"Unsupported geometry type '{geom_type}'. Only 'Polygon' is supported.")

    coordinates = geojson_dict.get("coordinates")
    if not isinstance(coordinates, list) or not coordinates:
        raise ValueError("Polygon must contain a 'coordinates' array.")

    max_vertices = settings.parcel_max_vertices()
    if len(coordinates) > 51:
        raise ValueError(f"Polygon exceeds maximum interior ring count of 50 (got {len(coordinates) - 1}).")

    total_vertices = 0
    for ring in coordinates:
        if not isinstance(ring, list):
            raise ValueError("Ring coordinates must be a list of points.")
        total_vertices += len(ring)
        if total_vertices > max_vertices:
            raise ValueError(f"Polygon vertex count {total_vertices} exceeds limit of {max_vertices}.")

        for pt in ring:
            if not isinstance(pt, (list, tuple)) or len(pt) < 2:
                raise ValueError("Coordinate point must contain at least [lon, lat].")
            lon, lat = pt[0], pt[1]
            if not isinstance(lon, (int, float)) or not isinstance(lat, (int, float)):
                raise ValueError("Coordinate values must be numeric.")
            if not math.isfinite(lon) or not math.isfinite(lat):
                raise ValueError("Coordinate values must be finite numbers.")
            if not (-180.0 <= lon <= 180.0):
                raise ValueError(f"Longitude {lon} out of range [-180, 180].")
            if not (-90.0 <= lat <= 90.0):
                raise ValueError(f"Latitude {lat} out of range [-90, 90].")


def parse_geojson(geojson_input: Union[str, Dict[str, Any]]) -> Polygon:
    """Parse raw GeoJSON string or dict into a shapely Polygon.

    Runs guard_complexity first.
    """
    if isinstance(geojson_input, str):
        try:
            geojson_dict = json.loads(geojson_input)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid GeoJSON string: {exc}") from exc
    elif isinstance(geojson_input, dict):
        geojson_dict = geojson_input
    else:
        raise ValueError("geojson_input must be a JSON string or dict.")

    guard_complexity(geojson_dict)

    if geojson_dict.get("type") == "Feature":
        geojson_dict = geojson_dict["geometry"]
    elif geojson_dict.get("type") == "FeatureCollection":
        geojson_dict = geojson_dict["features"][0]["geometry"]

    try:
        geom = shape(geojson_dict)
    except Exception as exc:
        raise ValueError(f"Failed to construct geometry: {exc}") from exc

    if not isinstance(geom, Polygon):
        raise ValueError(f"Parsed geometry is {type(geom).__name__}, expected Polygon.")

    return geom


def validate_polygon(poly: Polygon) -> Polygon:
    """Validate shapely Polygon.

    - Attempts make_valid if invalid
    - Ensures valid Polygon result
    - Ensures exterior ring has >= 3 unique points
    """
    if poly is None or poly.is_empty:
        raise ValueError("Polygon is empty or None.")

    if not poly.is_valid:
        fixed = make_valid(poly)
        if isinstance(fixed, Polygon) and fixed.is_valid:
            poly = fixed
        elif isinstance(fixed, MultiPolygon):
            # Pick largest polygon by area
            polys = sorted(fixed.geoms, key=lambda p: p.area, reverse=True)
            if polys and polys[0].is_valid:
                poly = polys[0]
            else:
                raise ValueError("Self-intersecting polygon could not be repaired.")
        else:
            raise ValueError("Invalid polygon geometry.")

    # Unique vertices check
    exterior_coords = list(poly.exterior.coords)
    # Remove closing coordinate if identical to first
    if len(exterior_coords) > 1 and exterior_coords[0] == exterior_coords[-1]:
        unique_coords = set(exterior_coords[:-1])
    else:
        unique_coords = set(exterior_coords)

    if len(unique_coords) < 3:
        raise ValueError(f"Polygon exterior ring has only {len(unique_coords)} unique vertices (minimum 3 required).")

    return poly


def to_geojson_str(poly: Polygon) -> str:
    """Serialize a (validated) shapely Polygon to canonical GeoJSON text.

    Persisting THIS (rather than the raw client input) guarantees the stored
    boundary is the same repaired geometry the area/bbox/overlap checks ran on,
    and that it always re-parses to a valid polygon on later reads — closing the
    'stored raw geometry re-parses invalid → GEOSException / bbox drift' hole.
    """
    return json.dumps(mapping(poly))


def parse_trusted_geojson(geojson_str: str) -> Polygon:
    """Parse geometry we ALREADY validated + stored (a prior approved parcel).

    Unlike parse_geojson, this does NOT run guard_complexity: that guard is a
    DoS defense for UNTRUSTED client input, and re-running it on trusted stored
    rows would let a later-lowered DMRV_PARCEL_MAX_VERTICES turn a config change
    into a self-DoS (an over-limit but already-approved parcel would 500 every
    overlap check in its region). Stored geometry is canonical (to_geojson_str),
    so shape() alone reconstructs a valid polygon.
    """
    return shape(json.loads(geojson_str))


def geodesic_area_m2(poly: Polygon) -> float:
    """Compute exact WGS84 geodesic area in square meters using pyproj.Geod."""
    area, _ = _GEOD.geometry_area_perimeter(poly)
    return abs(area)


def bbox_of(poly: Polygon) -> Tuple[float, float, float, float]:
    """Return bounding box (bbox_min_lat, bbox_min_lon, bbox_max_lat, bbox_max_lon).

    Note shapely.bounds returns (minx, miny, maxx, maxy) = (min_lon, min_lat, max_lon, max_lat).
    This function reorders to (min_lat, min_lon, max_lat, max_lon).
    """
    min_lon, min_lat, max_lon, max_lat = poly.bounds
    return float(min_lat), float(min_lon), float(max_lat), float(max_lon)


def overlap_ratio(poly_a: Polygon, poly_b: Polygon) -> float:
    """Compute area overlap ratio between poly_a and poly_b.

    Computes intersection area in m² using geodesic area.
    If intersection area < DMRV_PARCEL_SLIVER_FLOOR_M2 (default 200m²),
    returns 0.0 to prevent false rejects of adjacent shared borders.

    Returns intersection_area_m2 / min(area_a_m2, area_b_m2).
    """
    # Guard intersects() too (not just intersection()): on a pathological/invalid
    # geometry GEOS can raise here, and a bare crash in an anti-fraud scan is
    # worse than a conservative check. Persisted geometry is canonical so this is
    # defense-in-depth. A raise means "cannot prove disjoint" → treat as
    # overlapping (fail-closed) rather than silently passing.
    try:
        if not poly_a.intersects(poly_b):
            return 0.0
        inter = poly_a.intersection(poly_b)
    except Exception:
        return 1.0

    if inter.is_empty:
        return 0.0

    inter_area = geodesic_area_m2(inter)
    sliver_floor = settings.parcel_sliver_floor_m2()

    if inter_area < sliver_floor:
        return 0.0

    area_a = geodesic_area_m2(poly_a)
    area_b = geodesic_area_m2(poly_b)
    min_area = min(area_a, area_b)

    if min_area <= 0:
        return 0.0

    return inter_area / min_area


_M_PER_DEG = 111320.0


def polygon_from_track_points(points: List[Tuple[float, float]]) -> Polygon:
    """V8 Part 5 (A phase-2) — build a Polygon from a device-recorded GPS walk
    track (a list of (lon, lat) points, in walk order). Reuses the same
    complexity/bounds guard as untrusted portal-drawn input (DoS defense: a
    device could submit an arbitrarily long track) and the same repair +
    validation pipeline, so a walked boundary is held to the identical
    trustworthiness bar as a portal-drawn one before its area/overlap is
    computed against the declared parcel.
    """
    if not isinstance(points, list) or len(points) < 3:
        raise ValueError("A field-walk track needs at least 3 points to form a boundary.")

    ring = list(points)
    if ring[0] != ring[-1]:
        ring = ring + [ring[0]]  # close the ring, mirroring GeoJSON's convention

    guard_complexity({"type": "Polygon", "coordinates": [ring]})

    try:
        poly = Polygon(ring)
    except Exception as exc:
        raise ValueError(f"Could not construct a polygon from the walked track: {exc}") from exc

    return validate_polygon(poly)


def point_in_polygon(poly: Polygon, lon: float, lat: float, buffer_m: float = 10.0) -> bool:
    """Check if point (lon, lat) is inside poly or within buffer_m METERS of its edge.

    A naive `poly.buffer(buffer_m / 111320)` buffers uniformly in DEGREES, which
    under-buffers longitude by cos(lat): one degree of longitude is only
    111320·cos(lat) m, so at lat 28° a 10 m tolerance shrinks to ~8.8 m E-W (and
    worse toward the poles) — producing false QUARANTINE_GPS_OUTSIDE_PARCEL for
    honest edge captures. To make the buffer truly isotropic in meters, project
    both the polygon and the point into a local equirectangular meter space
    centered on the point's latitude, then buffer there.
    """
    pt = Point(lon, lat)
    if poly.contains(pt):
        return True
    if buffer_m <= 0:
        return False

    cos_lat = math.cos(math.radians(lat)) or 1e-9

    def _to_m(x, y, z=None):
        # x (lon), y (lat) may be scalars or numpy arrays; scalar factors apply.
        return (x * _M_PER_DEG * cos_lat, y * _M_PER_DEG)

    poly_m = _shp_transform(_to_m, poly)
    pt_m = _shp_transform(_to_m, pt)
    return poly_m.buffer(buffer_m).contains(pt_m)
