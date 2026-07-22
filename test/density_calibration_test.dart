import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/services/density_service.dart';

/// Deferred R3 — density calibration capture. `displayDensityKgPerL` is
/// DISPLAY ONLY, mirroring the server's authoritative formula
/// (`services/bulk_density.mass_and_volume_to_density_kg_per_l`,
/// mass_kg / volume_l) exactly — the server recomputes and stores its own
/// value on submit; this never gets trusted as the source of truth.
void main() {
  group('displayDensityKgPerL', () {
    test('computes mass / volume', () {
      expect(displayDensityKgPerL(massKg: 50.0, volumeL: 200.0), 0.25);
    });

    test('matches the server formula on a shared fixture', () {
      // Same fixture as backend/tests/test_bulk_density.py::
      // test_mass_and_volume_to_density_basic (mass=50.0, volume=200.0 -> 0.25).
      expect(displayDensityKgPerL(massKg: 50.0, volumeL: 200.0), 0.25);
    });

    test('zero volume returns null (guarded, never divides by zero)', () {
      expect(displayDensityKgPerL(massKg: 50.0, volumeL: 0.0), isNull);
    });

    test('negative volume returns null', () {
      expect(displayDensityKgPerL(massKg: 50.0, volumeL: -10.0), isNull);
    });

    test('zero or negative mass returns null', () {
      expect(displayDensityKgPerL(massKg: 0.0, volumeL: 200.0), isNull);
      expect(displayDensityKgPerL(massKg: -5.0, volumeL: 200.0), isNull);
    });
  });
}
