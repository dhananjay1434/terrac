/// The demo's clock, as a port. WallDemoClock gives now-relative wall time so
/// signed chunks are timestamped when the burn actually runs (not a hardcoded
/// date); FakeDemoClock makes emission deterministic in tests.
abstract class DemoClock {
  /// UTC wall time the burn started.
  DateTime get startedAt;

  /// Time since [startedAt].
  Duration elapsed();
}

class WallDemoClock implements DemoClock {
  WallDemoClock() : startedAt = DateTime.now().toUtc() {
    _sw.start();
  }
  @override
  final DateTime startedAt;
  final Stopwatch _sw = Stopwatch();
  @override
  Duration elapsed() => _sw.elapsed;
}

class FakeDemoClock implements DemoClock {
  FakeDemoClock({DateTime? startedAt, Duration elapsed = Duration.zero})
      : startedAt = startedAt ?? DateTime.utc(2026, 1, 1),
        _elapsed = elapsed;
  @override
  final DateTime startedAt;
  Duration _elapsed;
  // NOTE: a SETTER named `elapsed` would clash with the `elapsed()` method, so
  // mutation is a plain method.
  void setElapsed(Duration d) => _elapsed = d;
  @override
  Duration elapsed() => _elapsed;
}
