// TerraCipher — dMRV "Truth Machine" entry point.
//
// The entire app runs inside a Riverpod `ProviderScope`, which owns the
// lifecycle of every Notifier (dashboard, BLE telemetry, secure capture,
// sync queue, batch session, etc.). Persistent state is committed to a
// local Drift SQLite database (`AppDatabase`) and then forwarded to the
// FastAPI backend through a Two-Phase Syncing pipeline: every cryptographic
// payload is atomically written to the local store + outbox table first,
// and only afterwards dispatched by the sync layer with idempotency keys —
// so intermittent rural connectivity can never cause double-counted
// carbon credits.

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sentry_flutter/sentry_flutter.dart';
import 'package:dmrv_app/l10n/app_localizations.dart';

import 'services/crypto_signer.dart';
import 'services/device_integrity_service.dart';
import 'services/secure_capture_service.dart';
import 'ui/design/app_theme.dart';
import 'ui/screens/dashboard_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await CryptoSigner.warmUp();

  await SentryFlutter.init(
    (options) {
      options.dsn = const String.fromEnvironment(
        'SENTRY_DSN',
        defaultValue: '',
      );
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
      theme: AppTheme.lightTheme,
      debugShowCheckedModeBanner: false,
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: const [
        Locale('en'),
        Locale('hi'),
      ],
      home: const DashboardScreen(),
    );
  }
}
