// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Hindi (`hi`).
class AppLocalizationsHi extends AppLocalizations {
  AppLocalizationsHi([String locale = 'hi']) : super(locale);

  @override
  String get tap_to_start => 'शुरू करने के लिए टैप करें';

  @override
  String get no_pending_batch =>
      'कोई लंबित बैच नहीं मिला। पहले एक नया स्कैन शुरू करें।';

  @override
  String get connect_crane_scale => 'क्रेन स्केल कनेक्ट करें';

  @override
  String get stabilize_reading => 'रीडिंग स्थिर करें';

  @override
  String get stabilized => 'स्थिर';

  @override
  String get scan_biomass_hindi => 'बायोमास स्कैन करें';

  @override
  String get connect_sensor_hindi => 'सेंसर कनेक्ट करें';

  @override
  String get record_yield_hindi => 'उपज दर्ज करें';
}
