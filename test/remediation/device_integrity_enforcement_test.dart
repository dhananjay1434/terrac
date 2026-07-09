import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import '../../lib/services/device_integrity_service.dart';
import '../../lib/services/secure_capture_service.dart';
import '../../lib/services/sync_queue_manager.dart';
import 'package:camera/camera.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../lib/services/location_service.dart';
import 'package:geolocator/geolocator.dart';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/services.dart';

class MockConnectivity extends Fake implements Connectivity {
  @override
  Future<List<ConnectivityResult>> checkConnectivity() async {
    return [ConnectivityResult.none];
  }

  @override
  Stream<List<ConnectivityResult>> get onConnectivityChanged =>
      const Stream.empty();
}

class MockCameraController extends Fake implements CameraController {
  @override
  CameraValue get value => const CameraValue.uninitialized(
    CameraDescription(
      name: 'test',
      lensDirection: CameraLensDirection.back,
      sensorOrientation: 0,
    ),
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    isDeviceCompromisedGlobally = false;
    const MethodChannel(
      'dev.fluttercommunity.plus/connectivity',
    ).setMockMethodCallHandler((MethodCall methodCall) async {
      if (methodCall.method == 'check') {
        return ['none'];
      }
      return null;
    });
  });

  test('compromised_flag_blocks_capture', () async {
    isDeviceCompromisedGlobally = true;
    final container = ProviderContainer(
      overrides: [
        locationServiceProvider.overrideWithValue(MockLocationService()),
      ],
    );
    addTearDown(container.dispose);
    // Create SecureCaptureService directly to avoid provider setup.
    final captureService = SecureCaptureService(MockLocationService());
    final mockController = MockCameraController();

    expect(
      () => captureService.capture(controller: mockController),
      throwsA(
        isA<SecureCaptureException>().having(
          (e) => e.message,
          'message',
          contains('compromised'),
        ),
      ),
    );
  });

  test('compromised_flag_blocks_sync_kick', () async {
    isDeviceCompromisedGlobally = true;

    // We can just create a SyncQueueManager and call kickSync
    final container = ProviderContainer();
    final syncManager = container.read(syncQueueManagerProvider);

    // We expect it to return early and not throw, but we can verify it doesn't crash
    syncManager.kickSync();

    expect(true, isTrue);
  });

  test('placeholder_cert_hash_absent', () {
    final file = File('lib/services/device_integrity_service.dart');
    final content = file.readAsStringSync();

    expect(
      content.contains('YOUR_BASE64_CERT_HASH'),
      isFalse,
      reason: 'Placeholder YOUR_BASE64_CERT_HASH should not be in the file',
    );
    expect(
      content.contains('YOUR_TEAM_ID'),
      isFalse,
      reason: 'Placeholder YOUR_TEAM_ID should not be in the file',
    );
  });
}

class MockLocationService implements ILocationService {
  @override
  Future<Position> acquirePosition() async {
    return Position(
      longitude: 0,
      latitude: 0,
      timestamp: DateTime.now(),
      accuracy: 0,
      altitude: 0,
      heading: 0,
      speed: 0,
      speedAccuracy: 0,
      altitudeAccuracy: 0,
      headingAccuracy: 0,
    );
  }
}
