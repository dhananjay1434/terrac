import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/ble_temperature_service.dart';

/// =============================================================================
/// PyrolysisBleNotifier  (Prompt 4 — Task 3)
/// =============================================================================
/// Subscribes to a [BleTemperatureSource] and DECIMATES the high-frequency
/// stream to exactly one sample every 60 seconds.
///
/// Why? The ESP32 emits temperature floats at ~2 Hz which is noise from an
/// audit standpoint. Carbon registries want a sparse, deterministic log. We
/// therefore maintain `lastSampleAt` and only append `temperatureLog` when
/// `now - lastSampleAt >= window`. The most-recent raw reading is also held
/// in `liveCelsius` so the HUD shows realtime telemetry without polluting
/// the persisted log.
///
/// The window is overridable from tests via `PyrolysisBleNotifier(source, window: ...)`.
/// =============================================================================

class PyrolysisState {
  const PyrolysisState({
    this.connection = BleConnState.idle,
    this.liveCelsius,
    this.temperatureLog = const [],
    this.attestationLog = const [],
    this.burnStartAt,
    this.burnEndAt,
    this.minTemp = 0.0,
    this.maxTemp = 0.0,
  });

  final BleConnState connection;
  final double? liveCelsius;
  final List<double> temperatureLog;

  /// Raw 80-byte ECDSA attestation blobs from the ESP32 secure element.
  final List<List<int>> attestationLog;
  final DateTime? burnStartAt;
  final DateTime? burnEndAt;
  final double minTemp;
  final double maxTemp;

  PyrolysisState copyWith({
    BleConnState? connection,
    double? liveCelsius,
    List<double>? temperatureLog,
    List<List<int>>? attestationLog,
    DateTime? burnStartAt,
    DateTime? burnEndAt,
    double? minTemp,
    double? maxTemp,
  }) => PyrolysisState(
    connection: connection ?? this.connection,
    liveCelsius: liveCelsius ?? this.liveCelsius,
    temperatureLog: temperatureLog ?? this.temperatureLog,
    attestationLog: attestationLog ?? this.attestationLog,
    burnStartAt: burnStartAt ?? this.burnStartAt,
    burnEndAt: burnEndAt ?? this.burnEndAt,
    minTemp: minTemp ?? this.minTemp,
    maxTemp: maxTemp ?? this.maxTemp,
  );
}

class PyrolysisBleNotifier extends StateNotifier<PyrolysisState> {
  PyrolysisBleNotifier(
    this._source, {
    this.window = const Duration(seconds: 60),
    DateTime Function()? clock,
  }) : _clock = clock ?? DateTime.now,
       super(const PyrolysisState());

  final BleTemperatureSource _source;
  final Duration window;
  final DateTime Function() _clock;

  StreamSubscription<double>? _tempSub;
  StreamSubscription<BleConnState>? _connSub;
  StreamSubscription<List<int>>? _attestSub;
  DateTime? _lastSampleAt;
  double _runningMin = double.infinity;
  double _runningMax = double.negativeInfinity;

  Future<void> beginBurn() async {
    _runningMin = double.infinity;
    _runningMax = double.negativeInfinity;
    _lastSampleAt = null;
    state = state.copyWith(
      burnStartAt: _clock(),
      temperatureLog: const [],
      attestationLog: const [],
      minTemp: 0.0,
      maxTemp: 0.0,
    );
    await _source.start();
    _connSub = _source.connectionStream.listen(_onConn);
    _tempSub = _source.temperatureStream.listen(_onTemp);
    _attestSub = _source.attestationStream.listen(_onAttest);
  }

  void _onConn(BleConnState s) {
    state = state.copyWith(connection: s);
  }

  void _onTemp(double c) {
    final now = _clock();
    final log = state.temperatureLog;
    final shouldAppend =
        _lastSampleAt == null || now.difference(_lastSampleAt!) >= window;
    if (shouldAppend) {
      if (c < _runningMin) _runningMin = c;
      if (c > _runningMax) _runningMax = c;

      _lastSampleAt = now;
      state = state.copyWith(
        liveCelsius: c,
        temperatureLog: [...log, c],
        minTemp: _runningMin,
        maxTemp: _runningMax,
      );
    } else {
      state = state.copyWith(liveCelsius: c);
    }
  }

  void _onAttest(List<int> blob) {
    state = state.copyWith(attestationLog: [...state.attestationLog, blob]);
  }

  Future<PyrolysisState> endBurn() async {
    state = state.copyWith(burnEndAt: _clock());
    await _tempSub?.cancel();
    await _connSub?.cancel();
    await _attestSub?.cancel();
    await _source.stop();
    return state;
  }

  /// Test hook — inject a synthetic sample directly (bypasses the stream).
  void debugIngest(double celsius) => _onTemp(celsius);

  @override
  void dispose() {
    _tempSub?.cancel();
    _connSub?.cancel();
    _attestSub?.cancel();
    // Fire-and-forget. StateNotifier.dispose cannot be async; the underlying
    // platform-channel calls in dispose() are safe to leave un-awaited.
    _source.dispose();
    super.dispose();
  }
}

final pyrolysisBleProvider =
    StateNotifierProvider.autoDispose<PyrolysisBleNotifier, PyrolysisState>((ref) {
      const isDemoFlag = bool.fromEnvironment(
        'DMRV_DEMO_MODE',
        defaultValue: false,
      );
      final isDemo = isDemoFlag && !kReleaseMode;
      final source = isDemo
          ? VirtualBleAdapter(tickInterval: const Duration(seconds: 1))
          : BleTemperatureService();
      return PyrolysisBleNotifier(
        source,
        window: isDemo
            ? const Duration(seconds: 2)
            : const Duration(seconds: 60),
      );
    });
