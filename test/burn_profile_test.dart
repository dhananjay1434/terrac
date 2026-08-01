import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/services/simulation/burn_profile.dart';
void main() {
  const p = DemoProfile();
  const profile = BurnProfile(p);
  Duration atBucket(int b) => Duration(seconds: b * p.bucketSeconds);
  test('starts at ambient, climbs past 350 before plateau', () {
    expect(profile.sample(Duration.zero).tempC, closeTo(p.ambientC, 5.0));
    expect(profile.sample(atBucket(6)).tempC, greaterThan(350.0));
  });
  test('plateau settles near plateauC', () {
    expect(profile.sample(atBucket(10)).tempC, closeTo(p.plateauC, 1.0));
  });
  test('load is 0 during ignition, then settles to loadKg', () {
    expect(profile.sample(atBucket(0)).loadKg, 0.0);
    expect(profile.sample(atBucket(p.ignitionBuckets + 1)).loadKg, closeTo(p.loadKg, 1e-9));
  });
  test('pure: same elapsed → same sample', () {
    final a = profile.sample(atBucket(4));
    final b = profile.sample(atBucket(4));
    expect(a.tempC, b.tempC);
    expect(a.loadKg, b.loadKg);
  });
  test('values are 1dp (canonical-safe)', () {
    final v = profile.sample(atBucket(4)).tempC;
    expect((v * 10).roundToDouble(), closeTo(v * 10, 1e-9));
  });
}
