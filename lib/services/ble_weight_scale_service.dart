import 'dart:async';

import 'package:flutter_reactive_ble/flutter_reactive_ble.dart';

/// =============================================================================
/// BleWeightScaleService  (Prompt 5 — Task 1 — Yield)
/// =============================================================================
/// Connects to a digital hanging crane scale advertising the Bluetooth SIG
/// **Weight Scale Service** (0x181D) and subscribes to the
/// **Weight Measurement** characteristic (0x2A9D).
///
/// Parser (per BLE SIG GATT Spec for org.bluetooth.characteristic.weight_measurement):
///   byte 0       = flags
///                  bit 0 = unit (0 = SI / kg, 1 = imperial / lb)
///                  bit 1 = timestamp present
///                  bit 2 = user id present
///                  bit 3 = BMI + height present
///   bytes 1..2   = uint16 raw weight, LITTLE ENDIAN
///                  resolution = 0.005 kg (SI) or 0.01 lb (imperial)
///
/// We ALWAYS coerce the final result to kilograms. If the SI flag is unset we
/// convert lb → kg (× 0.45359237). Anything that fails parsing is dropped on
/// the floor — the notifier's circular buffer simply won't fill, so the
/// stabilization lock will never trip and the user sees the scale label
/// remain `----`.
///
/// MTU negotiation (247 bytes) + 1s→30s exponential auto-reconnect backoff
/// are identical in shape to [BleTemperatureService] so field operators get
/// uniform link behaviour across hardware.
/// =============================================================================

abstract class BleWeightScaleSource {
  Stream<double> get weightKgStream;
  Stream<BleScaleState> get connectionStream;
  Future<void> start();
  Future<void> stop();
}

enum BleScaleState { idle, scanning, connecting, connected, disconnected }

class BleWeightScaleService implements BleWeightScaleSource {
  BleWeightScaleService({FlutterReactiveBle? ble})
    : _ble = ble ?? FlutterReactiveBle();

  static final Uuid kWeightScaleService = Uuid.parse(
    '0000181d-0000-1000-8000-00805f9b34fb',
  );
  static final Uuid kWeightMeasureChar = Uuid.parse(
    '00002a9d-0000-1000-8000-00805f9b34fb',
  );
  static const int kRequestedMtu = 247;

  final FlutterReactiveBle _ble;
  final _weight = StreamController<double>.broadcast();
  final _conn = StreamController<BleScaleState>.broadcast();

  StreamSubscription<DiscoveredDevice>? _scanSub;
  StreamSubscription<ConnectionStateUpdate>? _connSub;
  StreamSubscription<List<int>>? _notifySub;
  bool _stopped = false;
  int _backoffSec = 1;

  @override
  Stream<double> get weightKgStream => _weight.stream;
  @override
  Stream<BleScaleState> get connectionStream => _conn.stream;

  @override
  Future<void> start() async {
    _stopped = false;
    await _scanAndConnect();
  }

  Future<void> _scanAndConnect() async {
    if (_stopped) return;
    _conn.add(BleScaleState.scanning);
    await _scanSub?.cancel();
    _scanSub = _ble
        .scanForDevices(
          withServices: [kWeightScaleService],
          scanMode: ScanMode.lowLatency,
        )
        .listen((dev) async {
          await _scanSub?.cancel();
          _conn.add(BleScaleState.connecting);
          _connSub = _ble
              .connectToDevice(
                id: dev.id,
                servicesWithCharacteristicsToDiscover: {
                  kWeightScaleService: [kWeightMeasureChar],
                },
                connectionTimeout: const Duration(seconds: 15),
              )
              .listen((update) async {
                switch (update.connectionState) {
                  case DeviceConnectionState.connected:
                    _conn.add(BleScaleState.connected);
                    _backoffSec = 1;
                    try {
                      await _ble.requestMtu(
                        deviceId: dev.id,
                        mtu: kRequestedMtu,
                      );
                    } catch (_) {
                      /* iOS ignores; non-fatal */
                    }
                    final char = QualifiedCharacteristic(
                      serviceId: kWeightScaleService,
                      characteristicId: kWeightMeasureChar,
                      deviceId: dev.id,
                    );
                    await _notifySub?.cancel();
                    _notifySub = _ble
                        .subscribeToCharacteristic(char)
                        .listen(
                          (bytes) {
                            final kg = parseWeightMeasurement(bytes);
                            if (kg != null) _weight.add(kg);
                          },
                          onError: (_) {
                            /* swallow — reconnect via state machine */
                          },
                        );
                    break;
                  case DeviceConnectionState.disconnected:
                    _conn.add(BleScaleState.disconnected);
                    await _retryWithBackoff();
                    break;
                  default:
                    break;
                }
              });
        });
  }

  Future<void> _retryWithBackoff() async {
    if (_stopped) return;
    await Future.delayed(Duration(seconds: _backoffSec));
    _backoffSec = (_backoffSec * 2).clamp(1, 30);
    await _scanAndConnect();
  }

  /// Parse the SIG Weight Measurement payload. Exposed publicly so tests can
  /// drive it directly without a live BLE device.
  ///
  /// Returns weight in KILOGRAMS or `null` if the payload is malformed.
  static double? parseWeightMeasurement(List<int> data) {
    if (data.length < 3) return null;
    final flags = data[0];
    final isSI = (flags & 0x01) == 0x00; // bit 0 = unit, 0 = SI/kg
    // little-endian uint16
    final raw = data[1] | (data[2] << 8);
    if (isSI) {
      return raw * 0.005; // kg
    } else {
      final lb = raw * 0.01;
      return lb * 0.45359237; // → kg
    }
  }

  @override
  Future<void> stop() async {
    _stopped = true;
    await _scanSub?.cancel();
    await _connSub?.cancel();
    await _notifySub?.cancel();
    _conn.add(BleScaleState.idle);
  }
}

/// =============================================================================
/// MockBleWeightScaleService  (used by the unit test)
/// =============================================================================
/// Lets the unit test push synthetic kg readings into the notifier through a
/// real stream. Driven manually via [push].
/// =============================================================================
class MockBleWeightScaleService implements BleWeightScaleSource {
  MockBleWeightScaleService({this.tickInterval, this.seed = 42});

  final Duration? tickInterval;
  final int seed;

  final _weight = StreamController<double>.broadcast();
  final _conn = StreamController<BleScaleState>.broadcast();
  Timer? _timer;
  int _i = 0;

  @override
  Stream<double> get weightKgStream => _weight.stream;
  @override
  Stream<BleScaleState> get connectionStream => _conn.stream;

  @override
  Future<void> start() async {
    _conn.add(BleScaleState.connected);
    if (tickInterval != null) {
      _timer = Timer.periodic(tickInterval!, (_) {
        // Start with some jitter, then stabilize at ~15.2 kg after 10 ticks
        final base = 15.2;
        final jitter = _i < 10 ? (((seed + _i) * 17) % 5) * 0.1 : 0.0;
        _weight.add(base + jitter);
        _i++;
      });
    }
  }

  void push(double kg) => _weight.add(kg);

  @override
  Future<void> stop() async {
    _timer?.cancel();
    _conn.add(BleScaleState.idle);
  }
}
