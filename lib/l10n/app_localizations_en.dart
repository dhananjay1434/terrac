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

  @override
  String get kyc_screen_title => 'Farmer KYC';

  @override
  String get kyc_form_title => 'Register Farmer';

  @override
  String get kyc_subtitle =>
      'Enrol the farmer and record their FPIC consent. Details sync to the verifier portal.';

  @override
  String get kyc_clear_draft_tooltip => 'Clear draft';

  @override
  String get kyc_draft_restored_banner =>
      'Draft restored from your last session.';

  @override
  String get kyc_dismiss => 'Dismiss';

  @override
  String get kyc_no_project_configured =>
      'No project is configured for this device, so a farmer cannot be scoped to a project. Registration is disabled.';

  @override
  String get kyc_section_personal => 'PERSONAL';

  @override
  String get kyc_field_first_name => 'FIRST NAME';

  @override
  String get kyc_field_first_name_hint => 'e.g. Rahul';

  @override
  String get kyc_field_last_name => 'LAST NAME (OPTIONAL)';

  @override
  String get kyc_field_last_name_hint => 'e.g. Kumar';

  @override
  String get kyc_field_guardian => 'GUARDIAN NAME (OPTIONAL)';

  @override
  String get kyc_field_mobile => 'MOBILE NUMBER';

  @override
  String get kyc_field_mobile_hint => '+91 ...';

  @override
  String get kyc_field_village => 'VILLAGE (OPTIONAL)';

  @override
  String get kyc_section_identity => 'IDENTITY (OPTIONAL)';

  @override
  String get kyc_capture_signature => 'SIGNATURE';

  @override
  String get kyc_capture_id_document => 'ID DOCUMENT PHOTO';

  @override
  String get kyc_id_last4_label => 'ID LAST 4 DIGITS';

  @override
  String get kyc_id_last4_hint => 'e.g. 1234';

  @override
  String get kyc_id_type_label => 'ID TYPE';

  @override
  String get kyc_id_type_aadhaar => 'Aadhaar';

  @override
  String get kyc_id_type_pan => 'PAN';

  @override
  String get kyc_id_type_passport => 'Passport';

  @override
  String get kyc_id_type_nid => 'National ID';

  @override
  String get kyc_section_payment => 'PAYMENT (OPTIONAL, MASKED ON SAVE)';

  @override
  String get kyc_field_account_holder => 'ACCOUNT HOLDER';

  @override
  String get kyc_field_account_number => 'ACCOUNT NUMBER';

  @override
  String get kyc_field_account_number_hint =>
      'stored masked — full number never leaves the device';

  @override
  String get kyc_field_pincode =>
      'PINCODE (OPTIONAL — AUTO-FILLS DISTRICT/STATE)';

  @override
  String get kyc_field_pincode_hint => 'e.g. 110001';

  @override
  String get kyc_lookup_button => 'Look up';

  @override
  String kyc_pincode_found(String district, String state) {
    return 'Found: $district, $state';
  }

  @override
  String get kyc_apply_to_village => 'Apply to village';

  @override
  String get kyc_pincode_no_match =>
      'No match — check the pincode or enter the address manually.';

  @override
  String get kyc_field_ifsc => 'IFSC (OPTIONAL)';

  @override
  String get kyc_verify_button => 'Verify';

  @override
  String kyc_ifsc_found(String bank, String branch) {
    return 'Bank: $bank · Branch: $branch';
  }

  @override
  String get kyc_ifsc_no_match => 'No match — double-check the IFSC code.';

  @override
  String get kyc_section_consent => 'CONSENT';

  @override
  String get kyc_fpic_consent_text =>
      'Farmer has given free, prior & informed consent (FPIC), including exclusivity.';

  @override
  String get kyc_capture_fpic_pdf => 'FPIC SIGNED CONSENT (PHOTO OF FORM)';

  @override
  String get kyc_capture_fpic_holding => 'FPIC HOLDING PHOTO';

  @override
  String get kyc_register_button => 'REGISTER FARMER';

  @override
  String get kyc_saving_label => 'SAVING…';

  @override
  String get kyc_clear_draft_dialog_title => 'Clear all entered fields?';

  @override
  String get kyc_clear_draft_dialog_content =>
      'This erases every field on this form for this farmer. This cannot be undone.';

  @override
  String get kyc_cancel_button => 'Cancel';

  @override
  String get kyc_clear_button => 'Clear';

  @override
  String get kyc_registered_snackbar => 'Farmer registered — queued for sync.';

  @override
  String kyc_register_failed_snackbar(String error) {
    return 'Could not register farmer: $error';
  }

  @override
  String get daystart_title => 'Start-of-Day Check';

  @override
  String get daystart_subtitle =>
      'Confirm these before your first capture today.';

  @override
  String get daystart_clock_label =>
      'This device\'s clock (date & time) is correct.';

  @override
  String get daystart_project_label =>
      'I am working the correct project today.';

  @override
  String get daystart_calibration_label =>
      'Any equipment needing calibration (scale, thermocouple) has been checked and is in date.';

  @override
  String get daystart_confirm_button => 'CONFIRM & START DAY';

  @override
  String get daystart_saving_label => 'SAVING…';
}
