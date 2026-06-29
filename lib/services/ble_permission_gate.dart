import 'package:permission_handler/permission_handler.dart';

/// =============================================================================
/// BLE Permission Gate  (Prompt 4 — Task 1)
/// =============================================================================
/// On Android 12+ a foreground BLE scan requires `BLUETOOTH_SCAN` +
/// `BLUETOOTH_CONNECT`, and on Android <= 11 it requires `ACCESS_FINE_LOCATION`.
/// iOS funnels everything through `Permission.bluetooth`. This gate requests
/// all three families and reports actionable failures to the caller.
/// =============================================================================

enum BlePermStatus { granted, denied, permanentlyDenied, restricted }

class BlePermissionResult {
  const BlePermissionResult({required this.status, required this.detail});
  final BlePermStatus status;
  final String detail;
  bool get isGranted => status == BlePermStatus.granted;
}

class BlePermissionGate {
  Future<BlePermissionResult> ensure() async {
    final needed = <Permission>[
      Permission.bluetoothScan,
      Permission.bluetoothConnect,
      Permission.locationWhenInUse,
      Permission.bluetooth,
    ];

    final statuses = await needed.request();

    for (final entry in statuses.entries) {
      final s = entry.value;
      if (s.isPermanentlyDenied) {
        return BlePermissionResult(
          status: BlePermStatus.permanentlyDenied,
          detail:
              '${entry.key} is permanently denied. Open OS Settings → App → '
              'Permissions and grant BLE + Location access.',
        );
      }
      if (s.isRestricted) {
        return BlePermissionResult(
          status: BlePermStatus.restricted,
          detail: '${entry.key} is restricted by device policy.',
        );
      }
    }

    // We only require: (scan+connect) OR (bluetooth) AND location.
    final scanOk = statuses[Permission.bluetoothScan]?.isGranted ?? false;
    final connectOk = statuses[Permission.bluetoothConnect]?.isGranted ?? false;
    final bluetoothOk = statuses[Permission.bluetooth]?.isGranted ?? false;
    final locationOk =
        statuses[Permission.locationWhenInUse]?.isGranted ?? false;

    final ok = (scanOk && connectOk) || bluetoothOk;
    if (ok && locationOk) {
      return const BlePermissionResult(
        status: BlePermStatus.granted,
        detail: 'All BLE permissions granted.',
      );
    }
    return const BlePermissionResult(
      status: BlePermStatus.denied,
      detail:
          'BLE scan/connect and Location are required. Tap RETRY to request again.',
    );
  }

  Future<void> openSettings() => openAppSettings();
}
