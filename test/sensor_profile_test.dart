import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/services/simulation/sensor_profile.dart';

void main() {
  test('parse maps known strings and defaults unknown to none', () {
    expect(sensorProfileFromString('full'), SensorProfile.full);
    expect(sensorProfileFromString('thermal_only'), SensorProfile.thermalOnly);
    expect(sensorProfileFromString('load_only'), SensorProfile.loadOnly);
    expect(sensorProfileFromString('none'), SensorProfile.none);
    expect(sensorProfileFromString(null), SensorProfile.none);
    expect(sensorProfileFromString('something_new'), SensorProfile.none);
  });

  test('expected channels per profile', () {
    expect(expectedChannels(SensorProfile.full), ['T1', 'T2', 'T3', 'T4', 'LOAD']);
    expect(expectedChannels(SensorProfile.thermalOnly), ['T1', 'T2', 'T3', 'T4']);
    expect(expectedChannels(SensorProfile.loadOnly), ['LOAD']);
    expect(expectedChannels(SensorProfile.none), isEmpty);
  });

  test('thermal/load predicates', () {
    expect(profileHasThermal(SensorProfile.full), isTrue);
    expect(profileHasThermal(SensorProfile.loadOnly), isFalse);
    expect(profileHasLoad(SensorProfile.full), isTrue);
    expect(profileHasLoad(SensorProfile.thermalOnly), isFalse);
  });
}
