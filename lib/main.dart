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

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sentry_flutter/sentry_flutter.dart';
import 'package:dmrv_app/l10n/app_localizations.dart';

import 'services/api_base.dart';
import 'services/crypto_signer.dart';
import 'services/device_integrity_service.dart';
import 'services/secure_capture_service.dart';
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
      container.read(apiBaseUrlProvider.notifier).state =
          await resolveApiBaseUrl();

      runApp(
        UncontrolledProviderScope(
          container: container,
          child: const TerraCipherApp(),
        ),
      );
    },
  );
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
      home: const _RootGate(),
    );
  }
}

/// Launch gate: an already-enrolled device goes straight to the dashboard; a
/// fresh device sees the in-app enrollment screen. The enrolled check reads
/// only local secure storage (never the network), so an offline enrolled device
/// boots instantly.
class _RootGate extends StatelessWidget {
  const _RootGate();

  @override
  Widget build(BuildContext context) {
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
