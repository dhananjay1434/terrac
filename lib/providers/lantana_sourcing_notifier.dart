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
///   • the source parcel this batch is registered against (V8 Part 1; null
///     until the portal-registered-boundary feature ships — see Part 0.3)
///   • the 72-hour sun-drying temporal lock
///   • a hidden `devBypass` flag that QA can flip during testing to skip the
///     72-hour wait
/// =============================================================================

class SourcingState {
  const SourcingState({
    required this.feedstockSpecies,
    this.harvestTimestamp,
    this.harvestUptimeSeconds,
    this.devBypass = false,
    this.now,
    this.biomassInputKg,
    this.biomassMeasurementMethod,
    this.parcelUuid,
    this.parcelName,
  });

  /// Immutable per the Registry Positive List rule.
  final String feedstockSpecies;
  final DateTime? harvestTimestamp;

  /// Device monotonic uptime (seconds since boot) captured at the moment the
  /// artisan tapped "LOG HARVEST NOW". Used by the backend to detect wall-clock
  /// manipulation: if the wall-clock delta is 73 h but the uptime delta is
  /// only 1 h, a clock-spoof attack is flagged.
  final int? harvestUptimeSeconds;

  final bool devBypass;

  /// Injected clock for deterministic tests. Defaults to `DateTime.now()`.
  final DateTime? now;

  /// Rainbow C1 (biomass input): the feedstock weight (kg) + how it was measured
  /// ('direct_weigh' | 'yield_conversion'). Drives the C2 moisture-sample target
  /// (max(10, ceil(kg/100))) and the server C1 gate.
  final double? biomassInputKg;
  final String? biomassMeasurementMethod;

  /// V8 Part 1.6: the operator-selected source parcel for this batch. Null
  /// until the operator picks one (the server geofence stays inert for a batch
  /// with no parcel — grandfathered).
  final String? parcelUuid;
  final String? parcelName;

  bool get hasBiomass =>
      (biomassInputKg ?? 0) > 0 && biomassMeasurementMethod != null;

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
    bool? devBypass,
    DateTime? now,
    double? biomassInputKg,
    String? biomassMeasurementMethod,
    String? parcelUuid,
    String? parcelName,
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
      devBypass: devBypass ?? this.devBypass,
      now: now ?? this.now,
      biomassInputKg: biomassInputKg ?? this.biomassInputKg,
      biomassMeasurementMethod:
          biomassMeasurementMethod ?? this.biomassMeasurementMethod,
      parcelUuid: parcelUuid ?? this.parcelUuid,
      parcelName: parcelName ?? this.parcelName,
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

    return SourcingState(
      feedstockSpecies: 'Lantana_camara',
      harvestTimestamp: tsString != null ? DateTime.parse(tsString) : null,
      harvestUptimeSeconds: uptime,
      biomassInputKg: prefs.getDouble('biomass_input_kg'),
      biomassMeasurementMethod: prefs.getString('biomass_method'),
      parcelUuid: prefs.getString('selected_parcel_uuid'),
      parcelName: prefs.getString('selected_parcel_name'),
    );
  }

  /// V8 Part 1.6: record the operator's source-parcel selection for this batch.
  /// Persisted so it survives across the sourcing → moisture → capture steps
  /// (the batch is written at capture time, in moisture_verification_screen).
  Future<void> selectParcel(String parcelUuid, String parcelName) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('selected_parcel_uuid', parcelUuid);
    await prefs.setString('selected_parcel_name', parcelName);
    final current = state.valueOrNull;
    if (current == null) return;
    state = AsyncData(
      current.copyWith(parcelUuid: parcelUuid, parcelName: parcelName),
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

  /// Rainbow C1: record the biomass weight (kg) + measurement method for this
  /// batch. Persisted so a resumed batch keeps its C2 moisture-sample target.
  Future<void> setBiomass(double kg, String method) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setDouble('biomass_input_kg', kg);
    await prefs.setString('biomass_method', method);
    final current = state.valueOrNull;
    if (current == null) return;
    state = AsyncData(
      current.copyWith(biomassInputKg: kg, biomassMeasurementMethod: method),
    );
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
