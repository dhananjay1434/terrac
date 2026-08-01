import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/services/simulation/demo_clock.dart';
void main() {
  test('wall clock is now-relative and monotonic', () async {
    final before = DateTime.now().toUtc();
    final c = WallDemoClock();
    expect(c.startedAt.isBefore(before.add(const Duration(seconds: 2))), isTrue);
    final e1 = c.elapsed();
    await Future.delayed(const Duration(milliseconds: 20));
    expect(c.elapsed() >= e1, isTrue);
  });
  test('fake clock is controllable', () {
    final c = FakeDemoClock(startedAt: DateTime.utc(2026, 7, 1), elapsed: const Duration(seconds: 30));
    expect(c.startedAt, DateTime.utc(2026, 7, 1));
    expect(c.elapsed(), const Duration(seconds: 30));
    c.setElapsed(const Duration(seconds: 90));
    expect(c.elapsed(), const Duration(seconds: 90));
  });
}
