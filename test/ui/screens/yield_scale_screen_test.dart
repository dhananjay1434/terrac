import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:dmrv_app/providers/yield_scale_notifier.dart';
import 'package:dmrv_app/services/ble_weight_scale_service.dart';
import 'package:dmrv_app/ui/components/dmrv_button.dart';
import 'package:dmrv_app/ui/design/tokens.dart';
import 'package:dmrv_app/ui/screens/yield_scale_screen.dart';
import 'package:dmrv_app/l10n/app_localizations.dart';

void main() {
  group('YieldScaleScreen — Phase 3 UI', () {
    testWidgets('connection=idle, no liveKg → readout shows ----', (
      tester,
    ) async {
      tester.view.physicalSize = const Size(1080, 3000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final mockState = const YieldScaleState(
        connection: BleScaleState.idle,
        liveKg: null,
        window: [],
        stableKg: null,
        confirmedKg: null,
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            yieldScaleProvider.overrideWith(
              (ref) => _MockYieldScaleNotifier(mockState),
            ),
          ],
          child: const MaterialApp(
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            locale: Locale('en'),
            home: YieldScaleScreen(),
          ),
        ),
      );

      expect(find.text('----'), findsOneWidget);
    });

    testWidgets('isStabilized=true → background flips to the locked tint', (
      tester,
    ) async {
      tester.view.physicalSize = const Size(1080, 3000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final mockState = const YieldScaleState(
        connection: BleScaleState.connected,
        liveKg: 15.025,
        window: [15.020, 15.025, 15.030, 15.022, 15.028],
        stableKg: 15.025,
        confirmedKg: null,
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            yieldScaleProvider.overrideWith(
              (ref) => _MockYieldScaleNotifier(mockState),
            ),
          ],
          child: const MaterialApp(
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            locale: Locale('en'),
            home: YieldScaleScreen(),
          ),
        ),
      );

      final scaffoldFinder = find.byType(Scaffold);
      expect(scaffoldFinder, findsOneWidget);

      // Paper skin: on stabilize the scaffold pulses to a faint success tint
      // over the surface (was the dark FarmerTheme.fieldGreen).
      final scaffold = tester.widget<Scaffold>(scaffoldFinder);
      expect(
        scaffold.backgroundColor,
        Color.alphaBlend(
          DmrvTokens.india.success.withValues(alpha: 0.10),
          DmrvTokens.india.surface,
        ),
      );
    });

    testWidgets('isStabilized=true → LOCK YIELD button is enabled', (
      tester,
    ) async {
      tester.view.physicalSize = const Size(1080, 3000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final mockState = const YieldScaleState(
        connection: BleScaleState.connected,
        liveKg: 12.500,
        window: [12.495, 12.500, 12.505, 12.498, 12.502],
        stableKg: 12.500,
        confirmedKg: null,
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            yieldScaleProvider.overrideWith(
              (ref) => _MockYieldScaleNotifier(mockState),
            ),
          ],
          child: const MaterialApp(
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            locale: Locale('en'),
            home: YieldScaleScreen(),
          ),
        ),
      );

      final btnFinder = find.byType(DmrvButton);
      expect(
        find.descendant(
          of: btnFinder,
          matching: find.textContaining('LOCK YIELD'),
        ),
        findsOneWidget,
      );
      final lockBtn = tester.widget<DmrvButton>(
        find.byKey(const Key('lock-yield-btn')),
      );
      expect(lockBtn.onPressed != null, isTrue);
    });

    testWidgets('isStabilized=false → action button onTap is null', (
      tester,
    ) async {
      tester.view.physicalSize = const Size(1080, 3000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final mockState = const YieldScaleState(
        connection: BleScaleState.connected,
        liveKg: 8.200,
        window: [8.000, 8.100, 8.200, 8.150],
        stableKg: null,
        confirmedKg: null,
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            yieldScaleProvider.overrideWith(
              (ref) => _MockYieldScaleNotifier(mockState),
            ),
          ],
          child: const MaterialApp(
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            locale: Locale('en'),
            home: YieldScaleScreen(),
          ),
        ),
      );

      expect(find.text('STABILIZE READING'), findsOneWidget);
      final lockBtn = tester.widget<DmrvButton>(
        find.byKey(const Key('lock-yield-btn')),
      );
      expect(lockBtn.onPressed == null, isTrue);
    });

    testWidgets('isConfirmed=true → SAVE YIELD button is visible', (
      tester,
    ) async {
      tester.view.physicalSize = const Size(1080, 3000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final mockState = const YieldScaleState(
        connection: BleScaleState.connected,
        liveKg: 20.000,
        window: [20.000, 20.005, 20.003, 20.002, 20.000],
        stableKg: 20.002,
        confirmedKg: 20.002,
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            yieldScaleProvider.overrideWith(
              (ref) => _MockYieldScaleNotifier(mockState),
            ),
          ],
          child: const MaterialApp(
            localizationsDelegates: AppLocalizations.localizationsDelegates,
            supportedLocales: AppLocalizations.supportedLocales,
            locale: Locale('en'),
            home: YieldScaleScreen(),
          ),
        ),
      );

      expect(find.textContaining('SAVE YIELD'), findsOneWidget);
    });
  });
}

class _MockYieldScaleNotifier extends YieldScaleNotifier {
  _MockYieldScaleNotifier(YieldScaleState initialState)
    : super(MockBleWeightScaleService()) {
    state = initialState;
  }
}
