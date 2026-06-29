import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// =============================================================================
/// LantanaSourcingNotifier
/// =============================================================================
/// Holds the state for the Sourcing Screen:
///   • the (immutable) feedstock selection ("Lantana_camara")
///   • the harvest timestamp captured at the moment of logging
///   • the GPS polygon mock state
///   • the 72-hour sun-drying temporal lock
///   • a hidden `devBypass` flag that QA can flip during testing to skip the
///     72-hour wait
/// =============================================================================

class SourcingState {
  const SourcingState({
    required this.feedstockSpecies,
    this.harvestTimestamp,
    this.harvestUptimeSeconds,
    this.polygonCaptured = false,
    this.devBypass = false,
    this.now,
  });

  /// Immutable per the Registry Positive List rule.
  final String feedstockSpecies;
  final DateTime? harvestTimestamp;

  /// Device monotonic uptime (seconds since boot) captured at the moment the
  /// artisan tapped "LOG HARVEST NOW". Used by the backend to detect wall-clock
  /// manipulation: if the wall-clock delta is 73 h but the uptime delta is
  /// only 1 h, a clock-spoof attack is flagged.
  final int? harvestUptimeSeconds;

  final bool polygonCaptured;
  final bool devBypass;

  /// Injected clock for deterministic tests. Defaults to `DateTime.now()`.
  final DateTime? now;

  static const Duration sunDryMandate = Duration(hours: 72);

  bool get hasHarvest => harvestTimestamp != null;

  Duration get elapsedSinceHarvest {
    if (harvestTimestamp == null) return Duration.zero;
    final clock = now ?? DateTime.now();
    return clock.difference(harvestTimestamp!);
  }

  Duration get timeRemainingOnLock {
    if (harvestTimestamp == null) return sunDryMandate;
    final remaining = sunDryMandate - elapsedSinceHarvest;
    return remaining.isNegative ? Duration.zero : remaining;
  }

  /// The headline gating predicate. The Sourcing screen disables the
  /// "Proceed to Moisture Check" button until this returns true.
  bool get canProceedToMoisture {
    if (devBypass) return true;
    if (!hasHarvest) return false;
    return elapsedSinceHarvest >= sunDryMandate;
  }

  /// Convenience for the HUD label.
  String get lockHudLabel {
    if (devBypass) return 'DEV-BYPASS // LOCK OVERRIDDEN';
    if (!hasHarvest) return 'AWAITING HARVEST LOG';
    if (canProceedToMoisture) return 'LOCK CLEARED // PROCEED';
    final r = timeRemainingOnLock;
    final h = r.inHours.toString().padLeft(2, '0');
    final m = (r.inMinutes % 60).toString().padLeft(2, '0');
    final s = (r.inSeconds % 60).toString().padLeft(2, '0');
    return 'LOCK ACTIVE // T-$h:$m:$s';
  }

  SourcingState copyWith({
    DateTime? harvestTimestamp,
    int? harvestUptimeSeconds,
    bool? polygonCaptured,
    bool? devBypass,
    DateTime? now,
    bool clearHarvest = false,
  }) {
    return SourcingState(
      feedstockSpecies: feedstockSpecies,
      harvestTimestamp: clearHarvest
          ? null
          : (harvestTimestamp ?? this.harvestTimestamp),
      harvestUptimeSeconds: clearHarvest
          ? null
          : (harvestUptimeSeconds ?? this.harvestUptimeSeconds),
      polygonCaptured: polygonCaptured ?? this.polygonCaptured,
      devBypass: devBypass ?? this.devBypass,
      now: now ?? this.now,
    );
  }
}

class LantanaSourcingNotifier extends AsyncNotifier<SourcingState> {
  @override
  FutureOr<SourcingState> build() async {
    return await _loadState();
  }

  Future<SourcingState> _loadState() async {
    final prefs = await SharedPreferences.getInstance();
    final tsString = prefs.getString('harvest_timestamp');
    final uptime = prefs.getInt('harvest_uptime_seconds');
    final poly = prefs.getBool('polygon_captured') ?? false;

    return SourcingState(
      feedstockSpecies: 'Lantana_camara',
      harvestTimestamp: tsString != null ? DateTime.parse(tsString) : null,
      harvestUptimeSeconds: uptime,
      polygonCaptured: poly,
    );
  }

  Future<void> _persistHarvest(DateTime? ts) async {
    final prefs = await SharedPreferences.getInstance();
    if (ts == null) {
      await prefs.remove('harvest_timestamp');
      await prefs.remove('harvest_uptime_seconds'); // keep in sync
    } else {
      await prefs.setString('harvest_timestamp', ts.toIso8601String());
    }
  }

  Future<void> _persistUptimeSeconds(int? uptime) async {
    final prefs = await SharedPreferences.getInstance();
    if (uptime == null) {
      await prefs.remove('harvest_uptime_seconds');
    } else {
      await prefs.setInt('harvest_uptime_seconds', uptime);
    }
  }

  Future<void> _persistPolygon(bool captured) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('polygon_captured', captured);
  }

  // logHarvestNow is now async — the UI should call it with unawaited() or
  // in a fire-and-forget pattern since the state update is near-instant.
  Future<void> logHarvestNow() async {
    final now = DateTime.now().toUtc();
    final uptime = await _readUptimeSeconds();
    await _persistHarvest(now);
    await _persistUptimeSeconds(uptime);
    state = AsyncData(
      state.requireValue.copyWith(
        harvestTimestamp: now,
        harvestUptimeSeconds: uptime,
      ),
    );
  }

  /// Testing hook — log harvest at a specific instant.
  Future<void> logHarvestAt(DateTime when) async {
    final ts = when.toUtc();
    final uptime = await _readUptimeSeconds();
    await _persistHarvest(ts);
    await _persistUptimeSeconds(uptime);
    state = AsyncData(
      state.requireValue.copyWith(
        harvestTimestamp: ts,
        harvestUptimeSeconds: uptime,
      ),
    );
  }

  /// Reads /proc/uptime on a background isolate (Android only).
  /// Returns null on non-Android platforms or if unreadable.
  Future<int?> _readUptimeSeconds() async {
    if (kIsWeb || !Platform.isAndroid) return null;
    try {
      // compute() runs on a background isolate — no main-thread blocking.
      return await compute(_parseUptimeFile, '/proc/uptime');
    } catch (e) {
      debugPrint('[Sourcing] could not read /proc/uptime: $e');
      return null;
    }
  }

  Future<void> captureGpsPolygon() async {
    await _persistPolygon(true);
    final current = state.valueOrNull;
    if (current == null) return;
    state = AsyncData(current.copyWith(polygonCaptured: true));
  }

  void toggleDevBypass(bool value) {
    // Dev bypass is compile-time stripped in release — kReleaseMode guard
    // prevents any caller (including DevTools) from activating it in the field.
    assert(() {
      final current = state.valueOrNull;
      if (current == null) return true; // build() hasn't completed; no-op
      state = AsyncData(current.copyWith(devBypass: value));
      return true;
    }());
  }

  /// Test-only — override the clock used to evaluate the lock.
  void debugSetNow(DateTime now) {
    state = AsyncData(state.requireValue.copyWith(now: now));
  }
}

final lantanaSourcingProvider =
    AsyncNotifierProvider<LantanaSourcingNotifier, SourcingState>(
      LantanaSourcingNotifier.new,
    );

/// Top-level function required by compute() — must NOT be a closure or method.
int? _parseUptimeFile(String path) {
  try {
    final content = File(path).readAsStringSync();
    return double.parse(content.trim().split(' ')[0]).floor();
  } catch (_) {
    return null;
  }
}
