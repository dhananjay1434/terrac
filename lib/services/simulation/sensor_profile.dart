/// Declared sensor suite of a kiln/machine. Values match the backend
/// `Kiln.sensor_profile` column and the capabilities.py tiers exactly.
/// This is an EXPECTATION used to pick a telemetry source and to warn on
/// mismatch — the live channel set always comes from the source's
/// `activeChannels`, never from this enum (audit fix #1).
enum SensorProfile { none, loadOnly, thermalOnly, full }

const _thermalChannels = <String>['T1', 'T2', 'T3', 'T4'];
const _loadChannel = 'LOAD';

/// Parse a backend profile string. Unknown / null → [SensorProfile.none] (safe
/// default — never crash, never over-claim capability).
SensorProfile sensorProfileFromString(String? raw) {
  switch (raw) {
    case 'full':
      return SensorProfile.full;
    case 'thermal_only':
      return SensorProfile.thermalOnly;
    case 'load_only':
      return SensorProfile.loadOnly;
    case 'none':
    default:
      return SensorProfile.none;
  }
}

/// The channels a profile is EXPECTED to carry. Ordered T1..T4 then LOAD.
List<String> expectedChannels(SensorProfile p) {
  switch (p) {
    case SensorProfile.full:
      return [..._thermalChannels, _loadChannel];
    case SensorProfile.thermalOnly:
      return [..._thermalChannels];
    case SensorProfile.loadOnly:
      return [_loadChannel];
    case SensorProfile.none:
      return const [];
  }
}

bool profileHasThermal(SensorProfile p) =>
    p == SensorProfile.full || p == SensorProfile.thermalOnly;
bool profileHasLoad(SensorProfile p) =>
    p == SensorProfile.full || p == SensorProfile.loadOnly;
