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

  @override
  String get kyc_screen_title => 'किसान केवाईसी';

  @override
  String get kyc_form_title => 'किसान पंजीकृत करें';

  @override
  String get kyc_subtitle =>
      'किसान को नामांकित करें और उनकी एफपीआईसी सहमति दर्ज करें। विवरण सत्यापनकर्ता पोर्टल में समन्वयित होंगे।';

  @override
  String get kyc_clear_draft_tooltip => 'ड्राफ़्ट साफ़ करें';

  @override
  String get kyc_draft_restored_banner =>
      'आपके पिछले सत्र से ड्राफ़्ट पुनर्स्थापित किया गया।';

  @override
  String get kyc_dismiss => 'खारिज करें';

  @override
  String get kyc_no_project_configured =>
      'इस डिवाइस के लिए कोई प्रोजेक्ट कॉन्फ़िगर नहीं है, इसलिए किसान को किसी प्रोजेक्ट से नहीं जोड़ा जा सकता। पंजीकरण अक्षम है।';

  @override
  String get kyc_section_personal => 'व्यक्तिगत';

  @override
  String get kyc_field_first_name => 'पहला नाम';

  @override
  String get kyc_field_first_name_hint => 'जैसे राहुल';

  @override
  String get kyc_field_last_name => 'अंतिम नाम (वैकल्पिक)';

  @override
  String get kyc_field_last_name_hint => 'जैसे कुमार';

  @override
  String get kyc_field_guardian => 'अभिभावक का नाम (वैकल्पिक)';

  @override
  String get kyc_field_mobile => 'मोबाइल नंबर';

  @override
  String get kyc_field_mobile_hint => '+91 ...';

  @override
  String get kyc_field_village => 'गांव (वैकल्पिक)';

  @override
  String get kyc_section_identity => 'पहचान (वैकल्पिक)';

  @override
  String get kyc_capture_signature => 'हस्ताक्षर';

  @override
  String get kyc_capture_id_document => 'पहचान दस्तावेज़ फ़ोटो';

  @override
  String get kyc_id_last4_label => 'पहचान के अंतिम 4 अंक';

  @override
  String get kyc_id_last4_hint => 'जैसे 1234';

  @override
  String get kyc_id_type_label => 'पहचान प्रकार';

  @override
  String get kyc_id_type_aadhaar => 'आधार';

  @override
  String get kyc_id_type_pan => 'पैन';

  @override
  String get kyc_id_type_passport => 'पासपोर्ट';

  @override
  String get kyc_id_type_nid => 'राष्ट्रीय पहचान पत्र';

  @override
  String get kyc_section_payment => 'भुगतान (वैकल्पिक, सेव करने पर छिपाया गया)';

  @override
  String get kyc_field_account_holder => 'खाताधारक';

  @override
  String get kyc_field_account_number => 'खाता संख्या';

  @override
  String get kyc_field_account_number_hint =>
      'छिपाकर संग्रहीत — पूरा नंबर कभी डिवाइस से बाहर नहीं जाता';

  @override
  String get kyc_field_pincode =>
      'पिनकोड (वैकल्पिक — ज़िला/राज्य स्वतः भरता है)';

  @override
  String get kyc_field_pincode_hint => 'जैसे 110001';

  @override
  String get kyc_lookup_button => 'खोजें';

  @override
  String kyc_pincode_found(String district, String state) {
    return 'मिला: $district, $state';
  }

  @override
  String get kyc_apply_to_village => 'गांव में जोड़ें';

  @override
  String get kyc_pincode_no_match =>
      'कोई मेल नहीं मिला — पिनकोड जांचें या पता स्वयं दर्ज करें।';

  @override
  String get kyc_field_ifsc => 'आईएफएससी (वैकल्पिक)';

  @override
  String get kyc_verify_button => 'सत्यापित करें';

  @override
  String kyc_ifsc_found(String bank, String branch) {
    return 'बैंक: $bank · शाखा: $branch';
  }

  @override
  String get kyc_ifsc_no_match =>
      'कोई मेल नहीं मिला — आईएफएससी कोड दोबारा जांचें।';

  @override
  String get kyc_section_consent => 'सहमति';

  @override
  String get kyc_fpic_consent_text =>
      'किसान ने स्वतंत्र, पूर्व एवं सूचित सहमति (एफपीआईसी) दी है, जिसमें विशिष्टता भी शामिल है।';

  @override
  String get kyc_capture_fpic_pdf =>
      'एफपीआईसी हस्ताक्षरित सहमति (फ़ॉर्म की फ़ोटो)';

  @override
  String get kyc_capture_fpic_holding => 'एफपीआईसी होल्डिंग फ़ोटो';

  @override
  String get kyc_register_button => 'किसान पंजीकृत करें';

  @override
  String get kyc_saving_label => 'सहेजा जा रहा है…';

  @override
  String get kyc_clear_draft_dialog_title => 'सभी दर्ज फ़ील्ड साफ़ करें?';

  @override
  String get kyc_clear_draft_dialog_content =>
      'यह इस किसान के लिए इस फ़ॉर्म के हर फ़ील्ड को मिटा देगा। इसे पूर्ववत नहीं किया जा सकता।';

  @override
  String get kyc_cancel_button => 'रद्द करें';

  @override
  String get kyc_clear_button => 'साफ़ करें';

  @override
  String get kyc_registered_snackbar => 'किसान पंजीकृत — सिंक के लिए कतारबद्ध।';

  @override
  String kyc_register_failed_snackbar(String error) {
    return 'किसान पंजीकृत नहीं हो सका: $error';
  }
}
