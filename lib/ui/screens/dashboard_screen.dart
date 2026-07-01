import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../data/local/app_database.dart';
import '../../data/local/database_provider.dart';
import '../../providers/batch_session_notifier.dart';
import '../../providers/dashboard_provider.dart';
import '../../providers/dashboard_stats_provider.dart';
import '../../providers/sync_providers.dart';

import '../design/farmer_theme.dart';
import '../widgets/integrity_footer.dart';
import '../widgets/premium_action_card.dart';
import '../widgets/rugged_button.dart';
import 'package:dmrv_app/l10n/app_localizations.dart';
import 'lantana_sourcing_screen.dart';
import 'proof_wallet_screen.dart';
import 'yield_scale_screen.dart';
import '../../services/device_integrity_service.dart';
import '../../services/sync_queue_manager.dart';

class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({super.key});

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends ConsumerState<DashboardScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _pulseController;
  late final Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);

    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.2).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  Widget _buildAnimatedCard(Widget child, bool isPending) {
    if (!isPending) return child;
    return AnimatedBuilder(
      animation: _pulseAnimation,
      builder: (context, _) {
        return Transform.scale(scale: _pulseAnimation.value, child: child);
      },
    );
  }

  Widget _buildStatBox({
    required String title,
    required String value,
    required IconData icon,
  }) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: FarmerTheme.fogWhite05,
        border: Border.all(color: FarmerTheme.fogWhite10),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 16, color: FarmerTheme.neonYellow),
              const SizedBox(width: 6),
              Text(
                title,
                style: const TextStyle(
                  fontFamily: 'SpaceGrotesk',
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 1.0,
                  color: FarmerTheme.fogWhite,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            value,
            style: const TextStyle(
              fontFamily: 'SpaceMono',
              fontSize: 18,
              fontWeight: FontWeight.w700,
              color: FarmerTheme.pureAlbedo,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildConnector({bool nextIsPending = false}) {
    return Container(
      height: 24,
      width: 4,
      margin: const EdgeInsets.only(left: 32),
      decoration: BoxDecoration(
        color: nextIsPending
            ? FarmerTheme.neonYellow30
            : FarmerTheme.fogWhite30,
        borderRadius: BorderRadius.circular(2),
      ),
    );
  }

  /// Renders a PENDING step as a full-width RuggedButton (primary variant).
  Widget _buildPendingStep({
    required String title,
    required String subtitleHindi,
    required IconData icon,
    required VoidCallback onTap,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: FarmerTheme.neonYellow20,
                  shape: BoxShape.circle,
                ),
                child: Icon(icon, size: 28, color: FarmerTheme.neonYellow),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: const TextStyle(
                        fontFamily: 'SpaceGrotesk',
                        fontSize: 18,
                        fontWeight: FontWeight.w700,
                        color: FarmerTheme.pureAlbedo,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      subtitleHindi,
                      style: const TextStyle(
                        fontFamily: 'NotoSansDevanagari',
                        fontSize: 14,
                        fontWeight: FontWeight.w400,
                        color: FarmerTheme.fogWhite,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          RuggedButton(
            label: AppLocalizations.of(context)!.tap_to_start,
            onPressed: onTap,
            variant: RuggedButtonVariant.primary,
          ),
        ],
      ),
    );
  }

  /// Renders a VERIFIED step as a compact green row with checkmark.
  Widget _buildCompletedStep({
    required String title,
    required VoidCallback? onTap,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(8),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
            child: Row(
              children: [
                Container(
                  width: 32,
                  height: 32,
                  decoration: const BoxDecoration(
                    color: FarmerTheme.fieldGreen,
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    Icons.check,
                    size: 20,
                    color: FarmerTheme.deepSlate,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    title,
                    style: const TextStyle(
                      fontFamily: 'SpaceGrotesk',
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: FarmerTheme.fieldGreen,
                    ),
                  ),
                ),
                const Icon(
                  Icons.arrow_forward_ios,
                  size: 14,
                  color: FarmerTheme.fieldGreen,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  /// Renders a LOCKED step as a compact greyed row with lock icon.
  Widget _buildLockedStep({required String title}) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Opacity(
        opacity: 0.4,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
          child: Row(
            children: [
              Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(
                  color: FarmerTheme.fogWhite30,
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.lock,
                  size: 18,
                  color: FarmerTheme.fogWhite,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(
                    fontFamily: 'SpaceGrotesk',
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: FarmerTheme.fogWhite,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  bool _isNavigating = false;

  Future<void> _handleCardTap(String action, {required AppDatabase db}) async {
    if (ref.read(deviceCompromisedProvider)) return;
    if (_isNavigating) return;
    _isNavigating = true;

    try {
      HapticFeedback.heavyImpact();
      debugPrint('DashboardAction: $action');

      switch (action) {
        case 'scan_biomass':
          final prefs = await SharedPreferences.getInstance();
          final artisanId = prefs.getString('artisan_id') ?? 'UNKNOWN_ARTISAN';
          final deviceMac = prefs.getString('device_mac') ?? 'UNKNOWN_MAC';

          // Initialize a new batch session before entering the sourcing pipeline
          ref.read(dashboardProvider.notifier).resetForNewBatch();
          final newBatchId = ref.read(batchSessionProvider.notifier).start();

          // Write the foundational SystemMetadata row so Proof Wallet can see the batch
          await db.insertSystemMetadataWithOutbox(
            SystemMetadataCompanion.insert(
              batchUuid: newBatchId,
              artisanId: artisanId,
              deviceHardwareMac: deviceMac,
              appBuildVersion: '3.0.0',
              createdAt: DateTime.now().toUtc().toIso8601String(),
            ),
          );
          if (!mounted) return;
          await Navigator.of(context).push(
            MaterialPageRoute<void>(
              builder: (_) => const LantanaSourcingScreen(),
            ),
          );
          break;

        case 'connect_ble_sensor':
          // Guard: re-hydrate batch state from database if needed
          if (ref.read(batchSessionProvider) == null) {
            final pendingUuid = await ref
                .read(dashboardProvider.notifier)
                .findIncompleteBatch(db);
            if (pendingUuid == null) {
              if (mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(
                      AppLocalizations.of(context)!.no_pending_batch,
                    ),
                  ),
                );
              }
              return;
            }
            ref.read(batchSessionProvider.notifier).restore(pendingUuid);
          }
          // BLE handshake. Only fire the notifier action when the BLE
          // step is genuinely pending; verified / locked taps are no-ops at the
          // notifier level so we never re-trigger a cryptographic handshake.
          final DashboardState state = ref.read(dashboardProvider);
          if (state.bleStatus == CardStatus.pending) {
            await ref.read(dashboardProvider.notifier).startBleHandshake();
          }
          break;

        case 'record_yield':
          // Guard: re-hydrate batch state from database if needed
          if (ref.read(batchSessionProvider) == null) {
            final pendingUuid = await ref
                .read(dashboardProvider.notifier)
                .findIncompleteBatch(db);
            if (pendingUuid == null) {
              if (mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(
                      AppLocalizations.of(context)!.no_pending_batch,
                    ),
                  ),
                );
              }
              return;
            }
            ref.read(batchSessionProvider.notifier).restore(pendingUuid);
          }
          if (!mounted) return;
          await Navigator.of(context).push(
            MaterialPageRoute<void>(builder: (_) => const YieldScaleScreen()),
          );
          break;

        case 'view_proof_wallet':
          await Navigator.of(context).push(
            MaterialPageRoute<void>(builder: (_) => const ProofWalletScreen()),
          );
          break;
      }
    } finally {
      _isNavigating = false;
    }
  }

  @override
  Widget build(BuildContext context) {
    // Instantiate the background sync manager so it starts listening to network events.
    ref.watch(syncQueueManagerProvider);

    final TextTheme textTheme = Theme.of(context).textTheme;
    final DashboardState state = ref.watch(dashboardProvider);
    final dbAsync = ref.watch(appDatabaseProvider);
    final syncCountAsync = ref.watch(pendingOutboxCountProvider);
    final statsAsync = ref.watch(dashboardStatsProvider);
    final isCompromised = ref.watch(deviceCompromisedProvider);

    return dbAsync.when(
      loading: () => const Scaffold(
        backgroundColor: FarmerTheme.deepSlate,
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              CircularProgressIndicator(color: FarmerTheme.neonYellow),
              SizedBox(height: 16),
              Text(
                'Initializing secure database…',
                style: TextStyle(
                  fontFamily: 'SpaceMono',
                  fontSize: 14,
                  color: FarmerTheme.pureAlbedo,
                ),
              ),
            ],
          ),
        ),
      ),
      error: (err, stack) => Scaffold(
        backgroundColor: FarmerTheme.deepSlate,
        body: Center(
          child: Text(
            'Database error: $err',
            style: const TextStyle(color: FarmerTheme.crimsonRed),
          ),
        ),
      ),
      data: (db) {
        return Scaffold(
          backgroundColor: FarmerTheme.deepSlate,
          body: Stack(
            children: [
              SafeArea(
                bottom: false,
                child: Column(
                  children: [
                    // PHASE 2a: Sync Banner
                    syncCountAsync.when(
                      data: (count) {
                        final bool allSynced = count == 0;
                        return Container(
                          constraints: const BoxConstraints(minHeight: 56),
                          padding: const EdgeInsets.symmetric(
                            horizontal: 20,
                            vertical: 12,
                          ),
                          decoration: BoxDecoration(
                            color: allSynced
                                ? FarmerTheme.fieldGreen15
                                : FarmerTheme.neonYellow15,
                            border: Border(
                              bottom: BorderSide(
                                color: allSynced
                                    ? FarmerTheme.fieldGreen30
                                    : FarmerTheme.neonYellow30,
                                width: 1,
                              ),
                            ),
                          ),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Text(
                                allSynced ? '✅' : '☁',
                                style: const TextStyle(fontSize: 20),
                              ),
                              const SizedBox(width: 8),
                              Text(
                                allSynced
                                    ? 'ALL DATA SECURE'
                                    : '$count RECORDS PENDING',
                                style: TextStyle(
                                  fontFamily: 'SpaceGrotesk',
                                  fontSize: 16,
                                  fontWeight: FontWeight.w700,
                                  letterSpacing: 0.5,
                                  color: allSynced
                                      ? FarmerTheme.fieldGreen
                                      : FarmerTheme.neonYellow,
                                ),
                              ),
                            ],
                          ),
                        );
                      },
                      loading: () => Container(
                        height: 56,
                        alignment: Alignment.center,
                        child: const CircularProgressIndicator(
                          color: FarmerTheme.neonYellow,
                          strokeWidth: 2,
                        ),
                      ),
                      error: (err, st) => const SizedBox.shrink(),
                    ),
                    Expanded(
                      child: SingleChildScrollView(
                        physics: const ClampingScrollPhysics(),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Padding(
                              padding: const EdgeInsets.all(24),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'TerraCipher',
                                    style: textTheme.titleLarge?.copyWith(
                                      color: FarmerTheme.pureAlbedo,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    'dMRV Field Terminal v3.0',
                                    style: textTheme.bodyMedium?.copyWith(
                                      color: FarmerTheme.fogWhite,
                                    ),
                                  ),
                                  const SizedBox(height: 24),
                                  statsAsync.when(
                                    data: (stats) => Row(
                                      children: [
                                        Expanded(
                                          child: _buildStatBox(
                                            title: 'TOTAL YIELD',
                                            value:
                                                '${stats.totalYieldKg.toStringAsFixed(1)} kg',
                                            icon: Icons.scale,
                                          ),
                                        ),
                                        const SizedBox(width: 12),
                                        Expanded(
                                          child: _buildStatBox(
                                            title: 'BATCHES',
                                            value:
                                                '${stats.completedBatches} / ${stats.totalBatches}',
                                            icon: Icons.inventory_2,
                                          ),
                                        ),
                                      ],
                                    ),
                                    loading: () => const Center(
                                      child: CircularProgressIndicator(
                                        color: FarmerTheme.neonYellow,
                                      ),
                                    ),
                                    error: (err, stack) => Text(
                                      'Stats Error: $err',
                                      style: const TextStyle(
                                        color: FarmerTheme.crimsonRed,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(height: 8),
                            // PHASE 2b: Progress Flow
                            // Step 1: Scan Biomass Input
                            if (state.biomassStatus == CardStatus.pending)
                              _buildPendingStep(
                                title: 'Scan Biomass Input',
                                subtitleHindi: AppLocalizations.of(
                                  context,
                                )!.scan_biomass_hindi,
                                icon: Icons.document_scanner,
                                onTap: () =>
                                    _handleCardTap('scan_biomass', db: db),
                              )
                            else if (state.biomassStatus == CardStatus.verified)
                              _buildCompletedStep(
                                title: 'Scan Biomass Input',
                                onTap: () =>
                                    _handleCardTap('scan_biomass', db: db),
                              )
                            else
                              _buildLockedStep(title: 'Scan Biomass Input'),

                            _buildConnector(
                              nextIsPending:
                                  state.bleStatus == CardStatus.pending,
                            ),

                            // Step 2: Connect BLE Sensor
                            if (state.bleStatus == CardStatus.pending)
                              _buildAnimatedCard(
                                _buildPendingStep(
                                  title: 'Connect BLE Sensor',
                                  subtitleHindi: AppLocalizations.of(
                                    context,
                                  )!.connect_sensor_hindi,
                                  icon: Icons.sensors,
                                  onTap: () => _handleCardTap(
                                    'connect_ble_sensor',
                                    db: db,
                                  ),
                                ),
                                true,
                              )
                            else if (state.bleStatus == CardStatus.verified)
                              _buildCompletedStep(
                                title: 'Connect BLE Sensor',
                                onTap: () => _handleCardTap(
                                  'connect_ble_sensor',
                                  db: db,
                                ),
                              )
                            else
                              _buildLockedStep(title: 'Connect BLE Sensor'),

                            _buildConnector(
                              nextIsPending:
                                  state.yieldStatus == CardStatus.pending,
                            ),

                            // Step 3: Record Yield Weight
                            if (state.yieldStatus == CardStatus.pending)
                              _buildPendingStep(
                                title: 'Record Yield Weight',
                                subtitleHindi: AppLocalizations.of(
                                  context,
                                )!.record_yield_hindi,
                                icon: Icons.scale,
                                onTap: () =>
                                    _handleCardTap('record_yield', db: db),
                              )
                            else if (state.yieldStatus == CardStatus.verified)
                              _buildCompletedStep(
                                title: 'Record Yield Weight',
                                onTap: () =>
                                    _handleCardTap('record_yield', db: db),
                              )
                            else
                              _buildLockedStep(title: 'Record Yield Weight'),

                            _buildConnector(),

                            // Step 4: View Proof Wallet (always accessible)
                            _buildCompletedStep(
                              title: 'View Proof Wallet',
                              onTap: () =>
                                  _handleCardTap('view_proof_wallet', db: db),
                            ),

                            const SizedBox(height: 24),
                          ],
                        ),
                      ),
                    ),
                    IntegrityFooter(lastHash: state.lastHash),
                  ],
                ),
              ),
              if (isCompromised)
                Positioned.fill(
                  child: Container(
                    color: Colors.black87,
                    child: Center(
                      child: Padding(
                        padding: const EdgeInsets.all(24.0),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(
                              Icons.security,
                              size: 64,
                              color: FarmerTheme.crimsonRed,
                            ),
                            const SizedBox(height: 16),
                            const Text(
                              'SECURITY COMPROMISE DETECTED',
                              style: TextStyle(
                                fontFamily: 'SpaceGrotesk',
                                fontSize: 20,
                                fontWeight: FontWeight.bold,
                                color: FarmerTheme.crimsonRed,
                              ),
                            ),
                            const SizedBox(height: 12),
                            const Text(
                              'This device has failed hardware integrity checks (e.g. root, emulator, or hooking framework).\n\nAccess to TerraCipher is permanently locked to prevent Sybil attacks.',
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: 15,
                                height: 1.4,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          ),
        );
      },
    );
  }
}
