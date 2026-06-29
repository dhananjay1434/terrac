// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get tap_to_start => 'TAP TO START';

  @override
  String get no_pending_batch =>
      'No pending batch found. Start a new scan first.';

  @override
  String get connect_crane_scale => 'CONNECT CRANE SCALE';

  @override
  String get stabilize_reading => 'STABILIZE READING';

  @override
  String get stabilized => 'STABILIZED';

  @override
  String get scan_biomass_hindi => 'Scan Biomass Input';

  @override
  String get connect_sensor_hindi => 'Connect Sensor';

  @override
  String get record_yield_hindi => 'Record Yield Weight';
}
