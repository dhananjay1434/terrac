import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/services/simulation/burn_profile.dart';
void main() {
  const p = DemoProfile();
  const profile = BurnProfile(p);
  Duration atBucket(int b) => Duration(seconds: b * p.bucketSeconds);
  ProbeSpec probe(String ch) => p.probes.firstWhere((x) => x.channel == ch);

  test('exactly four probes: T1-T3 sides, T4 bottom', () {
    expect(p.probes.map((x) => x.channel).toSet(), {'T1', 'T2', 'T3', 'T4'});
    expect(probe('T4').placement, 'bottom');
    expect(probe('T1').placement, startsWith('side'));
  });
  test('T1 remains the 420 reference (DH-C1 drift guard holds)', () {
    expect(probe('T1').plateauC, p.plateauC);
    expect(p.plateauC, 420.0);
  });
  test('placements read DIFFERENT plateau temps at steady state (T4>T1>T2>T3)', () {
    final t = {for (final c in ['T1', 'T2', 'T3', 'T4']) c: profile.sampleProbe(probe(c), atBucket(11))};
    expect(t['T4']!, greaterThan(t['T1']!));
    expect(t['T1']!, greaterThan(t['T2']!));
    expect(t['T2']!, greaterThan(t['T3']!));
  });
  test('all four climb past 350 by end of ramp', () {
    for (final c in ['T1', 'T2', 'T3', 'T4']) {
      expect(profile.sampleProbe(probe(c), atBucket(8)), greaterThan(350.0), reason: c);
    }
  });
  test('pure + canonical 1dp', () {
    final a = profile.sampleProbe(probe('T2'), atBucket(5));
    final b = profile.sampleProbe(probe('T2'), atBucket(5));
    expect(a, b);
    expect((a * 10).roundToDouble(), closeTo(a * 10, 1e-9));
  });
  test('legacy sample() unchanged: still the T1 curve + load', () {
    expect(profile.sample(atBucket(11)).tempC,
        closeTo(profile.sampleProbe(probe('T1'), atBucket(11)), 1e-9));
  });
}
