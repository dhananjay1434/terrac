import 'dart:async';
import 'dart:collection';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/ble_weight_scale_service.dart';

/// =============================================================================
/// YieldScaleNotifier  (Prompt 5 — Task 1 — Yield)
/// =============================================================================
/// Subscribes to a [BleWeightScaleSource] and runs a **5-reading circular
/// buffer** + **variance lock** that mirrors how a real hanging crane scale
/// settles after the load stops swinging.
///
///   • Buffer size           : 5 (FIFO, drops oldest on overflow).
///   • Stabilization rule    : (max - min) < kStabilizationVarianceKg
///                             AND buffer is exactly full (5 readings).
///   • When stable, [state.stableKg] is the arithmetic mean of the 5 readings.
///   • When not stable, [state.stableKg] is null and the buffer keeps
///     sliding with each new packet.
///
/// The notifier exposes a synchronous [pushReading] hook so unit tests can
/// bypass the BLE stream and drive the lock directly.
/// =============================================================================

const double kStabilizationVarianceKg = 0.05; // 50 grams
const int kStabilizationBufferSize = 5;

class YieldScaleState {
  const YieldScaleState({
    this.connection = BleScaleState.idle,
    this.liveKg,
    this.window = const [],
    this.stableKg,
    this.confirmedKg,
  });

  final BleScaleState connection;
  final double? liveKg;
  final List<double> window; // most-recent up-to-5 readings
  final double? stableKg; // set when variance < threshold AND buffer full
  final double? confirmedKg; // operator-confirmed final reading

  bool get isStabilized => stableKg != null;
  bool get isConfirmed => confirmedKg != null;

  double get variance {
    if (window.isEmpty) return 0;
    final mn = window.reduce((a, b) => a < b ? a : b);
    final mx = window.reduce((a, b) => a > b ? a : b);
    return mx - mn;
  }

  YieldScaleState copyWith({
    BleScaleState? connection,
    double? liveKg,
    List<double>? window,
    double? stableKg,
    double? confirmedKg,
    bool clearStable = false,
    bool clearConfirmed = false,
  }) => YieldScaleState(
    connection: connection ?? this.connection,
    liveKg: liveKg ?? this.liveKg,
    window: window ?? this.window,
    stableKg: clearStable ? null : (stableKg ?? this.stableKg),
    confirmedKg: clearConfirmed ? null : (confirmedKg ?? this.confirmedKg),
  );
}

class YieldScaleNotifier extends StateNotifier<YieldScaleState> {
  YieldScaleNotifier(this._source) : super(const YieldScaleState());

  final BleWeightScaleSource _source;
  final Queue<double> _buf = Queue<double>();

  StreamSubscription<double>? _weightSub;
  StreamSubscription<BleScaleState>? _connSub;

  Future<void> begin() async {
    await _source.start();
    _connSub = _source.connectionStream.listen((s) {
      state = state.copyWith(connection: s);
    });
    _weightSub = _source.weightKgStream.listen(pushReading);
  }

  /// Public for unit tests. Feeds a single kg reading through the variance
  /// engine.
  void pushReading(double kg) {
    if (kg.isNaN || kg.isInfinite) return;
    _buf.addLast(kg);
    while (_buf.length > kStabilizationBufferSize) {
      _buf.removeFirst();
    }
    final win = List<double>.unmodifiable(_buf);
    final isFull = win.length == kStabilizationBufferSize;
    final mn = win.reduce((a, b) => a < b ? a : b);
    final mx = win.reduce((a, b) => a > b ? a : b);
    final stable = isFull && (mx - mn) < kStabilizationVarianceKg;
    final mean = win.fold<double>(0, (a, b) => a + b) / win.length;

    state = state.copyWith(
      liveKg: kg,
      window: win,
      stableKg: stable ? mean : null,
      clearStable: !stable,
    );
  }

  /// DEV HELPER: Bypass BLE scale and force a stable 30kg reading
  void mockDevYield() {
    for (int i = 0; i < kStabilizationBufferSize; i++) {
      pushReading(30.0);
    }
  }

  /// Operator presses LOCK / CONFIRM YIELD. Persists the current stable value
  /// into `confirmedKg` so the UI can render SAVE YIELD.
  void confirm() {
    final s = state.stableKg;
    if (s == null) return;
    state = state.copyWith(confirmedKg: s);
  }

  Future<void> finish() async {
    await _weightSub?.cancel();
    await _connSub?.cancel();
    await _source.stop();
  }

  @override
  void dispose() {
    _weightSub?.cancel();
    _connSub?.cancel();
    _source.stop();
    super.dispose();
  }
}

/// Production provider — wires the real BLE scale.
final yieldScaleProvider =
    StateNotifierProvider.autoDispose<YieldScaleNotifier, YieldScaleState>((
      ref,
    ) {
      const isDemo = bool.fromEnvironment(
        'DMRV_DEMO_MODE',
        defaultValue: false,
      );
      final source = isDemo
          ? MockBleWeightScaleService(
              tickInterval: const Duration(milliseconds: 500),
            )
          : BleWeightScaleService();
      return YieldScaleNotifier(source);
    });
