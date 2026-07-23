import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_hi.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations? of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations);
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('hi'),
  ];

  /// Button label to start an action
  ///
  /// In en, this message translates to:
  /// **'TAP TO START'**
  String get tap_to_start;

  /// Error message when no pending batch is found
  ///
  /// In en, this message translates to:
  /// **'No pending batch found. Start a new scan first.'**
  String get no_pending_batch;

  /// Button label to connect BLE crane scale
  ///
  /// In en, this message translates to:
  /// **'CONNECT CRANE SCALE'**
  String get connect_crane_scale;

  /// Button label to stabilize weight reading
  ///
  /// In en, this message translates to:
  /// **'STABILIZE READING'**
  String get stabilize_reading;

  /// Status text when weight is stabilized
  ///
  /// In en, this message translates to:
  /// **'STABILIZED'**
  String get stabilized;

  /// No description provided for @scan_biomass_hindi.
  ///
  /// In en, this message translates to:
  /// **'Scan Biomass Input'**
  String get scan_biomass_hindi;

  /// No description provided for @connect_sensor_hindi.
  ///
  /// In en, this message translates to:
  /// **'Connect Sensor'**
  String get connect_sensor_hindi;

  /// No description provided for @record_yield_hindi.
  ///
  /// In en, this message translates to:
  /// **'Record Yield Weight'**
  String get record_yield_hindi;

  /// No description provided for @kyc_screen_title.
  ///
  /// In en, this message translates to:
  /// **'Farmer KYC'**
  String get kyc_screen_title;

  /// No description provided for @kyc_form_title.
  ///
  /// In en, this message translates to:
  /// **'Register Farmer'**
  String get kyc_form_title;

  /// No description provided for @kyc_subtitle.
  ///
  /// In en, this message translates to:
  /// **'Enrol the farmer and record their FPIC consent. Details sync to the verifier portal.'**
  String get kyc_subtitle;

  /// No description provided for @kyc_clear_draft_tooltip.
  ///
  /// In en, this message translates to:
  /// **'Clear draft'**
  String get kyc_clear_draft_tooltip;

  /// No description provided for @kyc_draft_restored_banner.
  ///
  /// In en, this message translates to:
  /// **'Draft restored from your last session.'**
  String get kyc_draft_restored_banner;

  /// No description provided for @kyc_dismiss.
  ///
  /// In en, this message translates to:
  /// **'Dismiss'**
  String get kyc_dismiss;

  /// No description provided for @kyc_no_project_configured.
  ///
  /// In en, this message translates to:
  /// **'No project is configured for this device, so a farmer cannot be scoped to a project. Registration is disabled.'**
  String get kyc_no_project_configured;

  /// No description provided for @kyc_section_personal.
  ///
  /// In en, this message translates to:
  /// **'PERSONAL'**
  String get kyc_section_personal;

  /// No description provided for @kyc_field_first_name.
  ///
  /// In en, this message translates to:
  /// **'FIRST NAME'**
  String get kyc_field_first_name;

  /// No description provided for @kyc_field_first_name_hint.
  ///
  /// In en, this message translates to:
  /// **'e.g. Rahul'**
  String get kyc_field_first_name_hint;

  /// No description provided for @kyc_field_last_name.
  ///
  /// In en, this message translates to:
  /// **'LAST NAME (OPTIONAL)'**
  String get kyc_field_last_name;

  /// No description provided for @kyc_field_last_name_hint.
  ///
  /// In en, this message translates to:
  /// **'e.g. Kumar'**
  String get kyc_field_last_name_hint;

  /// No description provided for @kyc_field_guardian.
  ///
  /// In en, this message translates to:
  /// **'GUARDIAN NAME (OPTIONAL)'**
  String get kyc_field_guardian;

  /// No description provided for @kyc_field_mobile.
  ///
  /// In en, this message translates to:
  /// **'MOBILE NUMBER'**
  String get kyc_field_mobile;

  /// No description provided for @kyc_field_mobile_hint.
  ///
  /// In en, this message translates to:
  /// **'+91 ...'**
  String get kyc_field_mobile_hint;

  /// No description provided for @kyc_field_village.
  ///
  /// In en, this message translates to:
  /// **'VILLAGE (OPTIONAL)'**
  String get kyc_field_village;

  /// No description provided for @kyc_section_identity.
  ///
  /// In en, this message translates to:
  /// **'IDENTITY (OPTIONAL)'**
  String get kyc_section_identity;

  /// No description provided for @kyc_capture_signature.
  ///
  /// In en, this message translates to:
  /// **'SIGNATURE'**
  String get kyc_capture_signature;

  /// No description provided for @kyc_capture_id_document.
  ///
  /// In en, this message translates to:
  /// **'ID DOCUMENT PHOTO'**
  String get kyc_capture_id_document;

  /// No description provided for @kyc_id_last4_label.
  ///
  /// In en, this message translates to:
  /// **'ID LAST 4 DIGITS'**
  String get kyc_id_last4_label;

  /// No description provided for @kyc_id_last4_hint.
  ///
  /// In en, this message translates to:
  /// **'e.g. 1234'**
  String get kyc_id_last4_hint;

  /// No description provided for @kyc_id_type_label.
  ///
  /// In en, this message translates to:
  /// **'ID TYPE'**
  String get kyc_id_type_label;

  /// No description provided for @kyc_id_type_aadhaar.
  ///
  /// In en, this message translates to:
  /// **'Aadhaar'**
  String get kyc_id_type_aadhaar;

  /// No description provided for @kyc_id_type_pan.
  ///
  /// In en, this message translates to:
  /// **'PAN'**
  String get kyc_id_type_pan;

  /// No description provided for @kyc_id_type_passport.
  ///
  /// In en, this message translates to:
  /// **'Passport'**
  String get kyc_id_type_passport;

  /// No description provided for @kyc_id_type_nid.
  ///
  /// In en, this message translates to:
  /// **'National ID'**
  String get kyc_id_type_nid;

  /// No description provided for @kyc_section_payment.
  ///
  /// In en, this message translates to:
  /// **'PAYMENT (OPTIONAL, MASKED ON SAVE)'**
  String get kyc_section_payment;

  /// No description provided for @kyc_field_account_holder.
  ///
  /// In en, this message translates to:
  /// **'ACCOUNT HOLDER'**
  String get kyc_field_account_holder;

  /// No description provided for @kyc_field_account_number.
  ///
  /// In en, this message translates to:
  /// **'ACCOUNT NUMBER'**
  String get kyc_field_account_number;

  /// No description provided for @kyc_field_account_number_hint.
  ///
  /// In en, this message translates to:
  /// **'stored masked — full number never leaves the device'**
  String get kyc_field_account_number_hint;

  /// No description provided for @kyc_field_pincode.
  ///
  /// In en, this message translates to:
  /// **'PINCODE (OPTIONAL — AUTO-FILLS DISTRICT/STATE)'**
  String get kyc_field_pincode;

  /// No description provided for @kyc_field_pincode_hint.
  ///
  /// In en, this message translates to:
  /// **'e.g. 110001'**
  String get kyc_field_pincode_hint;

  /// No description provided for @kyc_lookup_button.
  ///
  /// In en, this message translates to:
  /// **'Look up'**
  String get kyc_lookup_button;

  /// No description provided for @kyc_pincode_found.
  ///
  /// In en, this message translates to:
  /// **'Found: {district}, {state}'**
  String kyc_pincode_found(String district, String state);

  /// No description provided for @kyc_apply_to_village.
  ///
  /// In en, this message translates to:
  /// **'Apply to village'**
  String get kyc_apply_to_village;

  /// No description provided for @kyc_pincode_no_match.
  ///
  /// In en, this message translates to:
  /// **'No match — check the pincode or enter the address manually.'**
  String get kyc_pincode_no_match;

  /// No description provided for @kyc_field_ifsc.
  ///
  /// In en, this message translates to:
  /// **'IFSC (OPTIONAL)'**
  String get kyc_field_ifsc;

  /// No description provided for @kyc_verify_button.
  ///
  /// In en, this message translates to:
  /// **'Verify'**
  String get kyc_verify_button;

  /// No description provided for @kyc_ifsc_found.
  ///
  /// In en, this message translates to:
  /// **'Bank: {bank} · Branch: {branch}'**
  String kyc_ifsc_found(String bank, String branch);

  /// No description provided for @kyc_ifsc_no_match.
  ///
  /// In en, this message translates to:
  /// **'No match — double-check the IFSC code.'**
  String get kyc_ifsc_no_match;

  /// No description provided for @kyc_section_consent.
  ///
  /// In en, this message translates to:
  /// **'CONSENT'**
  String get kyc_section_consent;

  /// No description provided for @kyc_fpic_consent_text.
  ///
  /// In en, this message translates to:
  /// **'Farmer has given free, prior & informed consent (FPIC), including exclusivity.'**
  String get kyc_fpic_consent_text;

  /// No description provided for @kyc_capture_fpic_pdf.
  ///
  /// In en, this message translates to:
  /// **'FPIC SIGNED CONSENT (PHOTO OF FORM)'**
  String get kyc_capture_fpic_pdf;

  /// No description provided for @kyc_capture_fpic_holding.
  ///
  /// In en, this message translates to:
  /// **'FPIC HOLDING PHOTO'**
  String get kyc_capture_fpic_holding;

  /// No description provided for @kyc_register_button.
  ///
  /// In en, this message translates to:
  /// **'REGISTER FARMER'**
  String get kyc_register_button;

  /// No description provided for @kyc_saving_label.
  ///
  /// In en, this message translates to:
  /// **'SAVING…'**
  String get kyc_saving_label;

  /// No description provided for @kyc_clear_draft_dialog_title.
  ///
  /// In en, this message translates to:
  /// **'Clear all entered fields?'**
  String get kyc_clear_draft_dialog_title;

  /// No description provided for @kyc_clear_draft_dialog_content.
  ///
  /// In en, this message translates to:
  /// **'This erases every field on this form for this farmer. This cannot be undone.'**
  String get kyc_clear_draft_dialog_content;

  /// No description provided for @kyc_cancel_button.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get kyc_cancel_button;

  /// No description provided for @kyc_clear_button.
  ///
  /// In en, this message translates to:
  /// **'Clear'**
  String get kyc_clear_button;

  /// No description provided for @kyc_registered_snackbar.
  ///
  /// In en, this message translates to:
  /// **'Farmer registered — queued for sync.'**
  String get kyc_registered_snackbar;

  /// No description provided for @kyc_register_failed_snackbar.
  ///
  /// In en, this message translates to:
  /// **'Could not register farmer: {error}'**
  String kyc_register_failed_snackbar(String error);

  /// No description provided for @daystart_title.
  ///
  /// In en, this message translates to:
  /// **'Start-of-Day Check'**
  String get daystart_title;

  /// No description provided for @daystart_subtitle.
  ///
  /// In en, this message translates to:
  /// **'Confirm these before your first capture today.'**
  String get daystart_subtitle;

  /// No description provided for @daystart_clock_label.
  ///
  /// In en, this message translates to:
  /// **'This device\'s clock (date & time) is correct.'**
  String get daystart_clock_label;

  /// No description provided for @daystart_project_label.
  ///
  /// In en, this message translates to:
  /// **'I am working the correct project today.'**
  String get daystart_project_label;

  /// No description provided for @daystart_calibration_label.
  ///
  /// In en, this message translates to:
  /// **'Any equipment needing calibration (scale, thermocouple) has been checked and is in date.'**
  String get daystart_calibration_label;

  /// No description provided for @daystart_confirm_button.
  ///
  /// In en, this message translates to:
  /// **'CONFIRM & START DAY'**
  String get daystart_confirm_button;

  /// No description provided for @daystart_saving_label.
  ///
  /// In en, this message translates to:
  /// **'SAVING…'**
  String get daystart_saving_label;

  /// No description provided for @daystart_facility_label.
  ///
  /// In en, this message translates to:
  /// **'FACILITY'**
  String get daystart_facility_label;

  /// No description provided for @daystart_facility_hint.
  ///
  /// In en, this message translates to:
  /// **'Select your facility'**
  String get daystart_facility_hint;

  /// No description provided for @daystart_facility_loading.
  ///
  /// In en, this message translates to:
  /// **'Loading facilities…'**
  String get daystart_facility_loading;

  /// No description provided for @daystart_facility_none_found.
  ///
  /// In en, this message translates to:
  /// **'No facilities found. Check your connection.'**
  String get daystart_facility_none_found;

  /// No description provided for @daystart_facility_retry_button.
  ///
  /// In en, this message translates to:
  /// **'RETRY'**
  String get daystart_facility_retry_button;

  /// No description provided for @daystart_photo_label.
  ///
  /// In en, this message translates to:
  /// **'CAPTURE FACILITY PHOTO'**
  String get daystart_photo_label;

  /// No description provided for @daystart_photo_captured_label.
  ///
  /// In en, this message translates to:
  /// **'FACILITY PHOTO CAPTURED'**
  String get daystart_photo_captured_label;

  /// No description provided for @daystart_video_label.
  ///
  /// In en, this message translates to:
  /// **'CAPTURE WALKTHROUGH VIDEO (OPTIONAL)'**
  String get daystart_video_label;

  /// No description provided for @daystart_video_captured_label.
  ///
  /// In en, this message translates to:
  /// **'WALKTHROUGH VIDEO CAPTURED'**
  String get daystart_video_captured_label;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en', 'hi'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
    case 'hi':
      return AppLocalizationsHi();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
