import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/services/ble_temperature_service.dart';

void main() {
  group('IEEE-11073 FLOAT parser (Phase 19)', () {
    test('parses 25.0 °C correctly', () {
      // 25.0 = 250 * 10^-1
      // flags: 0x00 (Celsius)
      // mantissa: 250 (0x0000FA) -> bytes: 0xFA, 0x00, 0x00
      // exponent: -1 (0xFF)
      final data = <int>[0x00, 0xFA, 0x00, 0x00, 0xFF];
      final temp = BleTemperatureService.parseTemperatureMeasurement(data);
      expect(temp, closeTo(25.0, 0.01));
    });

    test('parses -5.5 °C correctly', () {
      // -5.5 = -55 * 10^-1
      // flags: 0x00 (Celsius)
      // mantissa: -55 (0xFFFFFF - 55 + 1 = 0xFFFFC9) -> bytes: 0xC9, 0xFF, 0xFF
      // exponent: -1 (0xFF)
      final data = <int>[0x00, 0xC9, 0xFF, 0xFF, 0xFF];
      final temp = BleTemperatureService.parseTemperatureMeasurement(data);
      expect(temp, closeTo(-5.5, 0.01));
    });

    test('parses Fahrenheit correctly and converts to Celsius', () {
      // 77.0 °F -> 25.0 °C
      // 77.0 = 770 * 10^-1
      // flags: 0x01 (Fahrenheit)
      // mantissa: 770 (0x000302) -> bytes: 0x02, 0x03, 0x00
      // exponent: -1 (0xFF)
      final data = <int>[0x01, 0x02, 0x03, 0x00, 0xFF];
      final temp = BleTemperatureService.parseTemperatureMeasurement(data);
      expect(temp, closeTo(25.0, 0.01));
    });

    test('returns null if data too short', () {
      final data = <int>[0x00, 0xFA, 0x00, 0x00];
      final temp = BleTemperatureService.parseTemperatureMeasurement(data);
      expect(temp, isNull);
    });
  });
}
