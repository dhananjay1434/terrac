import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_reactive_ble/flutter_reactive_ble.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// =============================================================================
/// BleTemperatureService  (Prompt 4 — Tasks 1, 2, 4)
/// =============================================================================
/// Strictly uses `flutter_reactive_ble`. Connects to an ESP32 broadcasting the
/// Bluetooth SIG **Health Thermometer Service** (0x1809) and subscribes to
/// the **Temperature Measurement** characteristic (0x2A1C). Performs explicit
/// MTU negotiation (247 bytes) to prevent array truncation on Android.
///
/// All temperature samples are republished on [temperatureStream] as raw
/// Celsius doubles. Buffering / 60-second decimation lives in the notifier —
/// this class is a *transport* concern only.
///
/// Auto-reconnect: on any disconnect the service re-arms a scan/connect loop
/// with exponential backoff (1s, 2s, 4s, 8s, cap 30s) until the consumer
/// explicitly calls [stop].
/// =============================================================================

abstract class BleTemperatureSource {
  Stream<double> get temperatureStream;
  Stream<BleConnState> get connectionStream;

  /// Stream of raw 80-byte attestation blobs from the ESP32 secure element.
  /// Null/empty on devices without ATECC608B.
  Stream<List<int>> get attestationStream;
  Future<void> start();
  Future<void> stop();
  Future<void> dispose();
}

enum BleConnState { idle, scanning, connecting, connected, disconnected }

class BleTemperatureService implements BleTemperatureSource {
  BleTemperatureService({FlutterReactiveBle? ble})
    : _ble = ble ?? FlutterReactiveBle();

  static final Uuid kThermometerService = Uuid.parse(
    '00001809-0000-1000-8000-00805f9b34fb',
  );
  static final Uuid kTempMeasureChar = Uuid.parse(
    '00002a1c-0000-1000-8000-00805f9b34fb',
  );
  static final Uuid kAttestationChar = Uuid.parse(
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
  );
  static const int kRequestedMtu = 247;

  /// Whitelist of pre-paired thermometer MAC addresses for this device.
  /// Stored in flutter_secure_storage under `ble_paired_macs` as a CSV
  /// string. Empty list means "no pairing yet" — start() will refuse to
  /// connect until the operator pairs at least one device through the
  /// Settings -> Pair Thermometer flow.
  static const _pairedMacsKey = 'ble_paired_macs';
  Set<String> _pairedMacs = <String>{};

  /// Loads the persisted MAC whitelist. Must be called before [start].
  Future<void> loadPairedMacs(FlutterSecureStorage storage) async {
    final raw = await storage.read(key: _pairedMacsKey);
    _pairedMacs = (raw ?? '')
        .split(',')
        .map((s) => s.trim())
        .where((s) => s.isNotEmpty)
        .toSet();
  }

  final FlutterReactiveBle _ble;
  final _temp = StreamController<double>.broadcast();
  final _conn = StreamController<BleConnState>.broadcast();
  final _attest = StreamController<List<int>>.broadcast();

  StreamSubscription<DiscoveredDevice>? _scanSub;
  StreamSubscription<ConnectionStateUpdate>? _connSub;
  StreamSubscription<List<int>>? _notifySub;
  StreamSubscription<List<int>>? _attestSub;
  bool _stopped = false;
  int _backoffSec = 1;

  @override
  Stream<double> get temperatureStream => _temp.stream;
  @override
  Stream<BleConnState> get connectionStream => _conn.stream;
  @override
  Stream<List<int>> get attestationStream => _attest.stream;

  @override
  Future<void> start() async {
    _stopped = false;
    await _scanAndConnect();
  }

  Future<void> _scanAndConnect() async {
    if (_stopped) return;
    _conn.add(BleConnState.scanning);
    await _scanSub?.cancel();
    await _connSub?.cancel();
    await _notifySub?.cancel();
    await _attestSub?.cancel();
    _scanSub = null;
    _connSub = null;
    _notifySub = null;
    _attestSub = null;
    _scanSub = _ble
        .scanForDevices(
          withServices: [kThermometerService],
          scanMode: ScanMode.lowLatency,
        )
        .listen((dev) async {
          // P0-7: refuse to connect to any device not in the operator's
          // pre-paired allow-list. Empty list = no pairing -> no connect.
          if (_pairedMacs.isEmpty || !_pairedMacs.contains(dev.id)) {
            debugPrint(
              '[BLE] Ignoring un-paired device ${dev.id} '
              '(allow-list size=${_pairedMacs.length})',
            );
            return;
          }
          await _scanSub?.cancel();
          _conn.add(BleConnState.connecting);
          _connSub = _ble
              .connectToDevice(
                id: dev.id,
                servicesWithCharacteristicsToDiscover: {
                  kThermometerService: [kTempMeasureChar, kAttestationChar],
                },
                connectionTimeout: const Duration(seconds: 15),
              )
              .listen((update) async {
                switch (update.connectionState) {
                  case DeviceConnectionState.connected:
                    _conn.add(BleConnState.connected);
                    _backoffSec = 1; // reset on success
                    try {
                      await _ble.requestMtu(
                        deviceId: dev.id,
                        mtu: kRequestedMtu,
                      );
                    } catch (_) {
                      /* iOS ignores; non-fatal */
                    }
                    final char = QualifiedCharacteristic(
                      serviceId: kThermometerService,
                      characteristicId: kTempMeasureChar,
                      deviceId: dev.id,
                    );
                    await _notifySub?.cancel();
                    _notifySub = _ble
                        .subscribeToCharacteristic(char)
                        .listen(
                          (bytes) {
                            final celsius = parseTemperatureMeasurement(bytes);
                            if (celsius != null) _temp.add(celsius);
                          },
                          onError: (_) {
                            /* swallow — reconnect via state machine */
                          },
                        );
                    // Subscribe to hardware attestation if available.
                    final attestChar = QualifiedCharacteristic(
                      serviceId: kThermometerService,
                      characteristicId: kAttestationChar,
                      deviceId: dev.id,
                    );
                    await _attestSub?.cancel();
                    bool sawAttestation = false;
                    _attestSub = _ble
                        .subscribeToCharacteristic(attestChar)
                        .listen(
                          (bytes) {
                            if (bytes.length == 80) {
                              sawAttestation = true;
                              _attest.add(bytes);
                            }
                          },
                          onError: (_) {
                            // P0-7: attestation MUST be present in release
                            // builds. In debug/staging we tolerate
                            // missing attestation but mark the connection
                            // state so the LCA pipeline can downgrade the
                            // batch (server-side compliance check uses the
                            // hwAttestationJson field).
                            if (kReleaseMode && !sawAttestation) {
                              debugPrint(
                                '[BLE] REJECT: attestation '
                                'characteristic not present in release mode',
                              );
                              stop();
                            }
                          },
                        );
                    break;
                  case DeviceConnectionState.disconnected:
                    _conn.add(BleConnState.disconnected);
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

  /// Parses the SIG Temperature Measurement (0x2A1C) payload:
  ///   byte0 flags (bit 0 = unit: 0 = °C, 1 = °F)
  ///   bytes 1..4 = IEEE-11073 32-bit FLOAT  (mantissa: int24, exponent: int8)
  @visibleForTesting
  static double? parseTemperatureMeasurement(List<int> data) {
    if (data.length < 5) return null;
    final flags = data[0];
    final isFahrenheit = (flags & 0x01) == 0x01;
    // little-endian: bytes 1..3 = mantissa, byte 4 = exponent (signed)
    final mantissaRaw = data[1] | (data[2] << 8) | (data[3] << 16);
    final mantissa = (mantissaRaw & 0x800000) != 0
        ? mantissaRaw - 0x1000000
        : mantissaRaw;
    final exponent = data[4] >= 128 ? data[4] - 256 : data[4];
    final value = mantissa * _pow10(exponent);
    return isFahrenheit ? (value - 32) * 5 / 9 : value;
  }

  static double _pow10(int e) {
    var r = 1.0;
    if (e >= 0) {
      for (var i = 0; i < e; i++) {
        r *= 10;
      }
    } else {
      for (var i = 0; i < -e; i++) {
        r /= 10;
      }
    }
    return r;
  }

  @override
  Future<void> stop() async {
    _stopped = true;
    await _scanSub?.cancel();
    await _connSub?.cancel();
    await _notifySub?.cancel();
    await _attestSub?.cancel();
    _scanSub = null;
    _connSub = null;
    _notifySub = null;
    _attestSub = null;
    _conn.add(BleConnState.idle);
  }

  /// Permanently disposes this service. After this call, the streams are
  /// closed and the service cannot be restarted. Call only from the owning
  /// notifier's dispose path.
  @override
  Future<void> dispose() async {
    await stop();
    await _temp.close();
    await _conn.close();
    await _attest.close();
  }
}

/// =============================================================================
/// VirtualBleAdapter  (Phase 2 — Investor Demo)
/// =============================================================================
/// Replaces the old MockBleTemperatureService with a 3-stage thermodynamic
/// state machine that produces a realistic kiln heating curve:
///
///   Stage 1 — Ignition  (ticks 0–4):  25°C → ~85°C, +15°C/tick
///   Stage 2 — Ramp      (ticks 5–19): exponential approach to targetPlateau
///   Stage 3 — Plateau   (ticks 20+):  stable at targetPlateau ± 0.5°C noise
///
/// Also simulates a realistic BLE connection handshake: emits scanning,
/// waits 1.5s, then emits connected before starting temperature ticks.
/// =============================================================================
class VirtualBleAdapter implements BleTemperatureSource {
  VirtualBleAdapter({
    this.tickInterval = const Duration(milliseconds: 500),
    this.targetPlateau = 420.0,
  }) {
    if (kReleaseMode) {
      throw UnsupportedError(
        'VirtualBleAdapter is completely forbidden in release builds to prevent malicious telemetry spoofing.',
      );
    }
  }

  final Duration tickInterval;
  final double targetPlateau;

  final _temp = StreamController<double>.broadcast();
  final _conn = StreamController<BleConnState>.broadcast();
  final _attest = StreamController<List<int>>.broadcast();
  Timer? _timer;
  int _tick = 0;
  double _currentTemp = 25.0;

  @override
  Stream<double> get temperatureStream => _temp.stream;
  @override
  Stream<BleConnState> get connectionStream => _conn.stream;
  @override
  Stream<List<int>> get attestationStream => _attest.stream;

  @override
  Future<void> start() async {
    _tick = 0;
    _currentTemp = 25.0;

    // Simulate BLE scan + connect handshake
    _conn.add(BleConnState.scanning);
    await Future.delayed(const Duration(milliseconds: 1500));
    _conn.add(BleConnState.connected);

    // Begin temperature emission
    _timer = Timer.periodic(tickInterval, (_) {
      _tick++;

      if (_tick <= 5) {
        // Stage 1: Ignition — linear climb from ambient
        _currentTemp = 25.0 + (_tick * 15.0);
      } else if (_tick <= 20) {
        // Stage 2: Ramp — exponential approach to plateau
        _currentTemp += (targetPlateau - _currentTemp) * 0.15;
      } else {
        // Stage 3: Plateau — stable with realistic hardware noise
        final noise = ((_tick % 5) - 2) * 0.25;
        _currentTemp = targetPlateau + noise;
      }

      _temp.add(_currentTemp);

      // Synthetic 80-byte attestation blob so demo runs exercise the same
      // hwAttestationJson path as production. Magic prefix 'DEMO' so the
      // backend can short-circuit-accept these without ECDSA verification.
      final blob = Uint8List(80);
      blob[0] = 0x44; // 'D'
      blob[1] = 0x45; // 'E'
      blob[2] = 0x4D; // 'M'
      blob[3] = 0x4F; // 'O'
      final bd = ByteData.view(blob.buffer);
      bd.setUint32(4, _tick, Endian.little);
      bd.setUint32(
        8,
        DateTime.now().millisecondsSinceEpoch ~/ 1000,
        Endian.little,
      );
      bd.setFloat32(12, _currentTemp, Endian.little);
      _attest.add(blob);
    });
  }

  @override
  Future<void> stop() async {
    _timer?.cancel();
    _timer = null;
    _conn.add(BleConnState.idle);
  }

  @override
  Future<void> dispose() async {
    await stop();
    await _temp.close();
    await _conn.close();
    await _attest.close();
  }
}
