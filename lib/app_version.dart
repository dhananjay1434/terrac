/// Single source of truth for the running app's semantic version, used by the
/// V8 Part 0.4 remote-config min-version gate (RemoteConfigService).
///
/// Defaults to the current `pubspec.yaml` version so dev/debug builds pass the
/// min-version floor. Release builds MUST pass the real build version via
/// `--dart-define=APP_VERSION=x.y.z` so the fleet's min-version enforcement is
/// accurate. Kept dependency-free on purpose (no package_info_plus / native
/// plugin) — it's a compile-time constant.
const String kAppVersion = String.fromEnvironment(
  'APP_VERSION',
  defaultValue: '1.0.0',
);
