// TerraCipher — dMRV client entry point.
//
// The entire app runs inside a Riverpod `ProviderScope`, which owns the
// lifecycle of every Notifier (dashboard, BLE telemetry, secure capture,
// sync queue, batch session, etc.). Persistent state is committed to a
// local Drift SQLite database (`AppDatabase`) and then forwarded to the
// FastAPI backend through a Two-Phase Syncing pipeline: every payload is
// atomically written to the local store + outbox table first, and only
// afterwards dispatched by the sync layer. An append-only outbox with
// per-operation idempotency keys minimizes double-counting under intermittent
// rural connectivity (the server deduplicates by idempotency key); it is a
// mitigation, not an absolute guarantee, and issuance integrity is enforced
// server-side (corroboration + PROVISIONAL gating), not by this client.

import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sentry_flutter/sentry_flutter.dart';
import 'package:dmrv_app/l10n/app_localizations.dart';

import 'app_version.dart';
import 'services/api_base.dart';
import 'services/crypto_signer.dart';
import 'services/device_integrity_service.dart';
import 'services/remote_config_service.dart';
import 'services/secure_capture_service.dart';
import 'services/server_signature_verifier.dart';
import 'ui/design/tokens.dart';
import 'ui/screens/dashboard_screen.dart';
import 'ui/screens/enrollment_screen.dart';

/// Validates release-critical runtime config and returns the DSN to use.
///
/// A release build with no `SENTRY_DSN` would silently disable crash
/// reporting — a production fleet whose crashes vanish. We refuse to boot in
/// that case. In debug/profile the empty DSN is allowed (local runs need no
/// DSN) and simply means reporting is off. Extracted as a pure function so the
/// contract is unit-testable without flipping [kReleaseMode].
String validateReleaseConfig({required bool isRelease, required String dsn}) {
  if (isRelease && dsn.isEmpty) {
    throw StateError(
      'Release build without SENTRY_DSN — crash reporting would be off. '
      'Pass --dart-define=SENTRY_DSN=... to release builds.',
    );
  }
  return dsn;
}

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await CryptoSigner.warmUp();

  const sentryDsn = String.fromEnvironment('SENTRY_DSN', defaultValue: '');
  final resolvedDsn =
      validateReleaseConfig(isRelease: kReleaseMode, dsn: sentryDsn);
  if (resolvedDsn.isEmpty) {
    debugPrint('[Sentry] DSN empty — crash reporting OFF (debug/profile only).');
  }

  await SentryFlutter.init(
    (options) {
      options.dsn = resolvedDsn;
      options.tracesSampleRate = kReleaseMode ? 0.05 : 1.0;
      // V8 Part 5 (N) — observability breadth. These three are the
      // sentry_flutter defaults already, but pinned explicitly here so a
      // future package upgrade changing its defaults can't silently turn
      // release-health tracking off for this field-deployed fleet:
      //   - crash-free-sessions / crash-free-users (release health)
      options.enableAutoSessionTracking = true;
      //   - app killed by the OS watchdog (low memory / excessive wakeups)
      //     counts as a crash, not a silent session drop
      options.enableWatchdogTerminationTracking = true;
      //   - UI-thread hangs (a real risk here: camera/BLE work on a field
      //     device) are reported like a slow crash, not invisible
      options.enableAppHangTracking = true;
      options.beforeBreadcrumb = (crumb, hint) {
        final m = crumb?.message ?? '';
        if (m.contains('lat=') || m.contains('lon=')) return null;
        return crumb;
      };
    },
    appRunner: () async {
      FlutterError.onError = (FlutterErrorDetails details) {
        Sentry.captureException(details.exception, stackTrace: details.stack);
      };

      await SecureCaptureService.cleanupStaleTemps();

      final container = ProviderContainer();
      await container.read(deviceIntegrityServiceProvider).initialize();

      // P1-S8: seed the live API base URL (enrolled secure-storage value →
      // dart-define fallback) so sync targets the right backend from launch.
      final apiBase = await resolveApiBaseUrl();
      container.read(apiBaseUrlProvider.notifier).state = apiBase;

      // V8 Part 0.4: load the last VERIFIED remote config from local secure
      // storage (instant, offline) so the kill-switch / min-version gate is
      // active from THIS launch even with no connectivity. Then refresh from
      // the server in the BACKGROUND — never awaited, so a sleeping/cold
      // backend can never strand the splash screen (offline-first invariant).
      await RemoteConfigService.loadCached();
      unawaited(_refreshRemoteConfig(apiBase));

      runApp(
        UncontrolledProviderScope(
          container: container,
          child: const TerraCipherApp(),
        ),
      );
    },
  );
}

/// Background remote-config refresh: pull the server's signed pubkeys, then
/// the signed config, verify + cache both. Never awaited by boot; failures are
/// swallowed (the cached config, if any, remains authoritative). The updated
/// cache takes effect on the next launch's [RemoteConfigService.loadCached].
Future<void> _refreshRemoteConfig(String apiBase) async {
  if (apiBase.isEmpty) return;
  try {
    await ServerSignatureVerifier.refreshFromServer(apiBase);
    await RemoteConfigService.fetchAndCache(apiBase);
  } catch (e) {
    debugPrint('[main] remote-config refresh failed (using cache): $e');
  }
}

class TerraCipherApp extends StatelessWidget {
  const TerraCipherApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'TerraCipher',
      theme: buildDmrvTheme(DmrvTokens.india),
      debugShowCheckedModeBanner: false,
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: const [Locale('en'), Locale('hi')],
      // V8 Part 5 (N) — automatic per-screen navigation transactions +
      // breadcrumbs, the standard Flutter perf-tracing hookup. Riding on the
      // `tracesSampleRate` already configured above; adds no new sampling
      // knob of its own.
      navigatorObservers: [SentryNavigatorObserver()],
      home: const _RootGate(),
    );
  }
}

/// Launch gate. Order of precedence (most severe first):
///   1. V8 Part 0.4 remote kill-switch — a signed, verified `kill_switch:true`
///      hard-stops the app fleet-wide (incident response / discovered fraud
///      vector). Enforced from the cached config loaded at boot.
///   2. Minimum supported version — a signed `min_version` above this build
///      forces an update before use.
///   3. Enrollment: an already-enrolled device goes to the dashboard; a fresh
///      device sees the in-app enrollment screen. This check reads only local
///      secure storage (never the network), so an offline enrolled device
///      boots instantly.
///
/// (1) and (2) derive ONLY from a signature-verified config — an unsigned or
/// tampered document is treated as "no remote config", so enforcement can
/// never be spoofed on, nor bypassed by serving unsigned config.
class _RootGate extends StatelessWidget {
  const _RootGate();

  @override
  Widget build(BuildContext context) {
    if (RemoteConfigService.isKillSwitchActive) {
      return _BlockScreen(
        icon: Icons.dangerous_outlined,
        title: 'Service paused',
        message: RemoteConfigService.killSwitchMessage ??
            'This app has been temporarily disabled by the administrator. '
                'Please contact your program coordinator.',
      );
    }
    if (RemoteConfigService.isBelowMinVersion(kAppVersion)) {
      return const _BlockScreen(
        icon: Icons.system_update_outlined,
        title: 'Update required',
        message: 'A newer version of the app is required to continue. '
            'Please install the latest build to keep capturing data.',
      );
    }
    return FutureBuilder<bool>(
      future: CryptoSigner.isEnrolled(),
      builder: (context, snap) {
        if (!snap.hasData) {
          return const Scaffold(
            body: Center(child: CircularProgressIndicator()),
          );
        }
        return snap.data! ? const DashboardScreen() : const EnrollmentScreen();
      },
    );
  }
}

/// Full-screen terminal state for the remote kill-switch / min-version gate.
/// Deliberately actionless — these are hard stops the operator cannot dismiss.
class _BlockScreen extends StatelessWidget {
  const _BlockScreen({
    required this.icon,
    required this.title,
    required this.message,
  });

  final IconData icon;
  final String title;
  final String message;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(icon, size: 64),
                const SizedBox(height: 24),
                Text(
                  title,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: 12),
                Text(
                  message,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
