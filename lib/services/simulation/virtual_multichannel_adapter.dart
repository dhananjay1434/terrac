import 'dart:async';

import 'package:flutter/foundation.dart';

import 'burn_profile.dart';
import 'sensor_profile.dart';

/// One reading on one channel. `channel` is 'T1'..'T4' or 'LOAD'.
class ChannelSample {
  const ChannelSample(this.channel, this.value);
  final String channel;
  final double value;
}

/// A telemetry source that can carry MORE than one channel. The live channel
/// set is whatever the source reports in [activeChannels] — the UI renders that,
/// never a config guess (audit fix #1 / #8). A real IoT device would implement
/// this from BLE service discovery; here we simulate it off the shared
/// [BurnProfile] so the phone matches the signed producer.
abstract class BleMultiChannelSource {
  Set<String> get activeChannels;
  Stream<ChannelSample> get sampleStream;
  Future<void> start();
  Future<void> stop();
  Future<void> dispose();
}

/// DEMO-ONLY multi-channel source. Samples the SAME [BurnProfile] the signed
/// [SimulatedEdgeDevice] reads (sampleProbe for T1..T4, sample().loadKg for
/// LOAD) on an accelerated wall clock, and emits ONLY the channels the given
/// [profile] expects. VirtualBleAdapter is untouched.
class VirtualMultiChannelAdapter implements BleMultiChannelSource {
  VirtualMultiChannelAdapter({
    required this.profile,
    BurnProfile? burn,
    Duration? tick,
  })  : _burn = burn ?? const BurnProfile(DemoProfile()),
        _tick = tick ?? const Duration(milliseconds: 500) {
    if (kReleaseMode) {
      throw UnsupportedError(
        'VirtualMultiChannelAdapter is forbidden in release builds.',
      );
    }
  }

  final SensorProfile profile;
  final BurnProfile _burn;
  final Duration _tick;

  final _samples = StreamController<ChannelSample>.broadcast();
  Timer? _timer;
  int _elapsedTicks = 0;

  @override
  Set<String> get activeChannels => expectedChannels(profile).toSet();

  @override
  Stream<ChannelSample> get sampleStream => _samples.stream;

  @override
  Future<void> start() async {
    _elapsedTicks = 0;
    final active = expectedChannels(profile);
    if (active.isEmpty) return; // 'none' → nothing to stream
    _timer = Timer.periodic(_tick, (_) {
      _elapsedTicks++;
      // Accelerated: each tick advances one burn bucket / accelerationFactor.
      final elapsed = Duration(
        milliseconds: (_elapsedTicks *
                _burn.profile.bucketSeconds *
                1000 ~/
                _burn.profile.accelerationFactor)
            .clamp(0, 1 << 40),
      );
      for (final probe in _burn.profile.probes) {
        if (active.contains(probe.channel)) {
          _samples.add(ChannelSample(probe.channel, _burn.sampleProbe(probe, elapsed)));
        }
      }
      if (active.contains('LOAD')) {
        _samples.add(ChannelSample('LOAD', _burn.sample(elapsed).loadKg));
      }
    });
  }

  @override
  Future<void> stop() async {
    _timer?.cancel();
    _timer = null;
  }

  @override
  Future<void> dispose() async {
    await stop();
    await _samples.close();
  }
}
