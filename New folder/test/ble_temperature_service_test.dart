import 'dart:async';
import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_reactive_ble/flutter_reactive_ble.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:dmrv_app/services/ble_temperature_service.dart';
import 'package:flutter/foundation.dart';
import 'package:mockito/mockito.dart';

class MockFlutterReactiveBle extends Mock implements FlutterReactiveBle {
  final StreamController<DiscoveredDevice> _scanStream = StreamController<DiscoveredDevice>.broadcast();

  void emitDevice(String id) {
    _scanStream.add(DiscoveredDevice(
      id: id,
      name: 'Test Device',
      serviceData: const {},
      manufacturerData: Uint8List(0),
      rssi: -50,
      serviceUuids: const [],
    ));
  }

  @override
  Stream<DiscoveredDevice> scanForDevices({
    required List<Uuid>? withServices,
    ScanMode? scanMode = ScanMode.balanced,
    bool? requireLocationServicesEnabled = true,
  }) {
    return _scanStream.stream;
  }

  @override
  Stream<ConnectionStateUpdate> connectToDevice({
    required String id,
    Map<Uuid, List<Uuid>>? servicesWithCharacteristicsToDiscover,
    Duration? connectionTimeout,
  }) {
    return Stream.value(ConnectionStateUpdate(
      deviceId: id,
      connectionState: DeviceConnectionState.connected,
      failure: null,
    ));
  }

  @override
  Future<int> requestMtu({required String deviceId, required int mtu}) async {
    return mtu;
  }

  @override
  Stream<List<int>> subscribeToCharacteristic(QualifiedCharacteristic characteristic) {
    return const Stream.empty();
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  FlutterSecureStorage.setMockInitialValues({'ble_paired_macs': 'AA:BB:CC:DD:EE:01, AA:BB:CC:DD:EE:02'});

  test('BleTemperatureService ignores devices not in the allow-list', () async {
    final fakeBle = MockFlutterReactiveBle();
    final service = BleTemperatureService(ble: fakeBle);
    final storage = const FlutterSecureStorage();
    await service.loadPairedMacs(storage);

    var connectedStateCount = 0;
    final sub = service.connectionStream.listen((state) {
      if (state == BleConnState.connecting) {
        connectedStateCount++;
      }
    });

    await service.start();

    fakeBle.emitDevice('UNKNOWN_MAC');
    await Future.delayed(const Duration(milliseconds: 50));
    expect(connectedStateCount, 0, reason: 'Should ignore un-paired device');

    fakeBle.emitDevice('AA:BB:CC:DD:EE:01');
    await Future.delayed(const Duration(milliseconds: 50));
    expect(connectedStateCount, 1, reason: 'Should connect to paired device');

    await sub.cancel();
    await service.stop();
    await service.dispose();
  });
}
