import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/simulation/virtual_multichannel_adapter.dart';

/// Live state for a multi-channel burn. Per-channel latest value + decimated
/// log + min/max. Channels present here are exactly the source's active set —
/// never fabricated. Separate from the single-channel PyrolysisState so the
/// legacy 'none' path is untouched.
class MultiChannelBurnState {
  const MultiChannelBurnState({
    this.channels = const [],
    this.live = const {},
    this.log = const {},
    this.min = const {},
    this.max = const {},
    this.started = false,
  });

  final List<String> channels; // active channel order (T1..T4, LOAD)
  final Map<String, double> live; // latest value per channel
  final Map<String, List<double>> log; // decimated series per channel
  final Map<String, double> min;
  final Map<String, double> max;
  final bool started;

  MultiChannelBurnState copyWith({
    List<String>? channels,
    Map<String, double>? live,
    Map<String, List<double>>? log,
    Map<String, double>? min,
    Map<String, double>? max,
    bool? started,
  }) =>
      MultiChannelBurnState(
        channels: channels ?? this.channels,
        live: live ?? this.live,
        log: log ?? this.log,
        min: min ?? this.min,
        max: max ?? this.max,
        started: started ?? this.started,
      );
}

class MultiChannelBurnNotifier extends StateNotifier<MultiChannelBurnState> {
  MultiChannelBurnNotifier(
    this._source, {
    this.window = const Duration(seconds: 2),
    DateTime Function()? clock,
  })  : _clock = clock ?? DateTime.now,
        super(const MultiChannelBurnState());

  final BleMultiChannelSource _source;
  final Duration window;
  final DateTime Function() _clock;

  StreamSubscription<ChannelSample>? _sub;
  final Map<String, DateTime> _lastAt = {};

  Future<void> begin() async {
    final channels = _source.activeChannels.toList()
      ..sort((a, b) => _order(a).compareTo(_order(b)));
    state = MultiChannelBurnState(channels: channels, started: true);
    _lastAt.clear();
    _sub = _source.sampleStream.listen(_onSample);
    await _source.start();
  }

  static int _order(String c) => c == 'LOAD' ? 99 : int.tryParse(c.substring(1)) ?? 50;

  /// Test hook — feed a sample directly (same path as the stream listener).
  void debugIngest(String channel, double value) => _onSample(ChannelSample(channel, value));

  void _onSample(ChannelSample s) {
    final now = _clock();
    final live = Map<String, double>.from(state.live)..[s.channel] = s.value;
    final last = _lastAt[s.channel];
    final append = last == null || now.difference(last) >= window;
    if (!append) {
      state = state.copyWith(live: live);
      return;
    }
    _lastAt[s.channel] = now;
    final log = {
      for (final e in state.log.entries) e.key: List<double>.from(e.value),
    };
    (log[s.channel] ??= <double>[]).add(s.value);
    final min = Map<String, double>.from(state.min);
    final max = Map<String, double>.from(state.max);
    min[s.channel] = min.containsKey(s.channel) ? (s.value < min[s.channel]! ? s.value : min[s.channel]!) : s.value;
    max[s.channel] = max.containsKey(s.channel) ? (s.value > max[s.channel]! ? s.value : max[s.channel]!) : s.value;
    state = state.copyWith(live: live, log: log, min: min, max: max);
  }

  Future<void> end() async {
    await _sub?.cancel();
    await _source.stop();
  }

  @override
  void dispose() {
    _sub?.cancel();
    _source.dispose();
    super.dispose();
  }
}
