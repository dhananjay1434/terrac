import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/providers/multichannel_burn_notifier.dart';
import 'package:dmrv_app/services/simulation/sensor_profile.dart';
import 'package:dmrv_app/services/simulation/virtual_multichannel_adapter.dart';

void main() {
  test('decimates per channel and tracks per-channel min/max', () {
    DateTime now = DateTime.utc(2026, 1, 1);
    final n = MultiChannelBurnNotifier(
      VirtualMultiChannelAdapter(profile: SensorProfile.full),
      window: const Duration(seconds: 2),
      clock: () => now,
    );
    // First sample on a channel is always appended (lastAt null).
    n.debugIngest('T1', 400.0);
    n.debugIngest('T1', 410.0); // same window → decimated out of the log
    expect(n.state.log['T1']!.length, 1);
    expect(n.state.live['T1'], 410.0);
    now = now.add(const Duration(seconds: 3)); // cross the window
    n.debugIngest('T1', 420.0);
    expect(n.state.log['T1']!.length, 2);
    expect(n.state.min['T1'], 400.0);
    expect(n.state.max['T1'], 420.0);
    // Channels are independent.
    n.debugIngest('LOAD', 15.2);
    expect(n.state.log['LOAD']!.length, 1);
    expect(n.state.max.containsKey('LOAD'), isTrue);
  });
}
