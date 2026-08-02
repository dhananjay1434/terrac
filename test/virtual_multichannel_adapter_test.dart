import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/services/simulation/sensor_profile.dart';
import 'package:dmrv_app/services/simulation/virtual_multichannel_adapter.dart';

void main() {
  test('full profile emits exactly T1..T4 + LOAD', () async {
    final a = VirtualMultiChannelAdapter(
      profile: SensorProfile.full,
      tick: const Duration(milliseconds: 1),
    );
    expect(a.activeChannels, {'T1', 'T2', 'T3', 'T4', 'LOAD'});
    final seen = <String>{};
    final sub = a.sampleStream.listen((s) => seen.add(s.channel));
    await a.start();
    await Future<void>.delayed(const Duration(milliseconds: 40));
    await a.stop();
    await sub.cancel();
    await a.dispose();
    expect(seen, {'T1', 'T2', 'T3', 'T4', 'LOAD'});
  });

  test('load_only emits only LOAD; thermal_only never emits LOAD', () async {
    final load = VirtualMultiChannelAdapter(
      profile: SensorProfile.loadOnly, tick: const Duration(milliseconds: 1));
    final loadSeen = <String>{};
    final ls = load.sampleStream.listen((s) => loadSeen.add(s.channel));
    await load.start();
    await Future<void>.delayed(const Duration(milliseconds: 30));
    await load.stop(); await ls.cancel(); await load.dispose();
    expect(loadSeen, {'LOAD'});

    final therm = VirtualMultiChannelAdapter(
      profile: SensorProfile.thermalOnly, tick: const Duration(milliseconds: 1));
    final thermSeen = <String>{};
    final ts = therm.sampleStream.listen((s) => thermSeen.add(s.channel));
    await therm.start();
    await Future<void>.delayed(const Duration(milliseconds: 30));
    await therm.stop(); await ts.cancel(); await therm.dispose();
    expect(thermSeen.contains('LOAD'), isFalse);
    expect(thermSeen, {'T1', 'T2', 'T3', 'T4'});
  });

  test('none profile emits nothing', () async {
    final a = VirtualMultiChannelAdapter(
      profile: SensorProfile.none, tick: const Duration(milliseconds: 1));
    final seen = <String>[];
    final sub = a.sampleStream.listen((s) => seen.add(s.channel));
    await a.start();
    await Future<void>.delayed(const Duration(milliseconds: 20));
    await a.stop(); await sub.cancel(); await a.dispose();
    expect(seen, isEmpty);
  });
}
