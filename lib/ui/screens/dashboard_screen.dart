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

import '../components/dmrv_button.dart';
import '../components/dmrv_panel.dart';
import '../design/tokens.dart';
import '../widgets/integrity_footer.dart';
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

    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.04).animate(
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
    final t = context.tokens;
    return DmrvPanel(
      padding: EdgeInsets.all(t.gapM),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 18, color: t.accentText),
              SizedBox(width: t.gapS),
              Expanded(
                child: Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: t.chipLabel.copyWith(color: t.textSecondary),
                ),
              ),
            ],
          ),
          SizedBox(height: t.gapM),
          Text(value, style: t.numericMedium.copyWith(color: t.textPrimary)),
        ],
      ),
    );
  }

  Widget _buildConnector({bool nextIsPending = false}) {
    final t = context.tokens;
    return Container(
      height: 20,
      width: 3,
      margin: EdgeInsets.only(left: t.gapXL + 16),
      decoration: BoxDecoration(
        color: nextIsPending ? t.accent : t.border,
        borderRadius: BorderRadius.circular(2),
      ),
    );
  }

  /// A PENDING step: a focused panel with a primary DmrvButton call-to-action.
  Widget _buildPendingStep({
    required String title,
    required String subtitleHindi,
    required IconData icon,
    required VoidCallback onTap,
  }) {
    final t = context.tokens;
    return Padding(
      padding: EdgeInsets.symmetric(horizontal: t.gapL, vertical: t.gapS),
      child: DmrvPanel(
        accent: true,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(
                    color: t.accent.withValues(alpha: 0.12),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(icon, size: 26, color: t.accentText),
                ),
                SizedBox(width: t.gapM),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: t.blockHeader.copyWith(color: t.textPrimary),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        subtitleHindi,
                        style: t.bodyHindi.copyWith(color: t.textSecondary),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            SizedBox(height: t.gapL),
            DmrvButton(
              label: AppLocalizations.of(context)!.tap_to_start,
              onPressed: onTap,
              variant: DmrvButtonVariant.primary,
            ),
          ],
        ),
      ),
    );
  }

  /// A VERIFIED step: a compact success row with a check.
  Widget _buildCompletedStep({
    required String title,
    required VoidCallback? onTap,
  }) {
    final t = context.tokens;
    return Padding(
      padding: EdgeInsets.symmetric(horizontal: t.gapL, vertical: t.gapS),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(t.radiusM),
          child: Padding(
            padding: EdgeInsets.symmetric(horizontal: t.gapM, vertical: t.gapM),
            child: Row(
              children: [
                Container(
                  width: 32,
                  height: 32,
                  decoration: BoxDecoration(
                    color: t.success,
                    shape: BoxShape.circle,
                  ),
                  child: Icon(Icons.check, size: 20, color: t.onSuccess),
                ),
                SizedBox(width: t.gapM),
                Expanded(
                  child: Text(
                    title,
                    style: t.metadata.copyWith(
                      color: t.success,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                Icon(Icons.arrow_forward_ios, size: 14, color: t.success),
              ],
            ),
          ),
        ),
      ),
    );
  }

  /// A LOCKED step: a greyed row with a lock.
  Widget _buildLockedStep({required String title}) {
    final t = context.tokens;
    return Padding(
      padding: EdgeInsets.symmetric(horizontal: t.gapL, vertical: t.gapS),
      child: Opacity(
        opacity: 0.4,
        child: Padding(
          padding: EdgeInsets.symmetric(horizontal: t.gapM, vertical: t.gapM),
          child: Row(
            children: [
              Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(
                  color: t.border,
                  shape: BoxShape.circle,
                ),
                child: Icon(Icons.lock, size: 18, color: t.textSecondary),
              ),
              SizedBox(width: t.gapM),
              Expanded(
                child: Text(
                  title,
                  style: t.metadata.copyWith(
                    color: t.textSecondary,
                    fontWeight: FontWeight.w700,
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

  Widget _syncBanner(int count) {
    final t = context.tokens;
    final bool allSynced = count == 0;
    final Color tone = allSynced ? t.success : t.accentText;
    return Container(
      constraints: const BoxConstraints(minHeight: 52),
      padding: EdgeInsets.symmetric(horizontal: t.gapXL, vertical: t.gapM),
      decoration: BoxDecoration(
        color: tone.withValues(alpha: 0.10),
        border: Border(
          bottom: BorderSide(color: tone.withValues(alpha: 0.30), width: 1),
        ),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            allSynced ? Icons.verified_outlined : Icons.cloud_queue_rounded,
            size: 20,
            color: tone,
          ),
          SizedBox(width: t.gapS),
          Text(
            allSynced ? 'ALL DATA SECURE' : '$count RECORDS PENDING',
            style: t.chipLabel.copyWith(fontSize: 15, color: tone),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    // Instantiate the background sync manager so it starts listening to network events.
    ref.watch(syncQueueManagerProvider);

    final t = context.tokens;
    final DashboardState state = ref.watch(dashboardProvider);
    final dbAsync = ref.watch(appDatabaseProvider);
    final syncCountAsync = ref.watch(pendingOutboxCountProvider);
    final statsAsync = ref.watch(dashboardStatsProvider);
    final isCompromised = ref.watch(deviceCompromisedProvider);

    return dbAsync.when(
      loading: () => Scaffold(
        backgroundColor: t.surface,
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              CircularProgressIndicator(color: t.accent),
              SizedBox(height: t.gapL),
              Text(
                'Initializing secure database…',
                style: t.metadata.copyWith(color: t.textSecondary),
              ),
            ],
          ),
        ),
      ),
      error: (err, stack) => Scaffold(
        backgroundColor: t.surface,
        body: Center(
          child: Text(
            'Database error: $err',
            style: t.body.copyWith(color: t.danger),
          ),
        ),
      ),
      data: (db) {
        return Scaffold(
          backgroundColor: t.surface,
          body: Stack(
            children: [
              SafeArea(
                bottom: false,
                child: Column(
                  children: [
                    syncCountAsync.when(
                      data: (count) => _syncBanner(count),
                      loading: () => Container(
                        height: 52,
                        alignment: Alignment.center,
                        child: CircularProgressIndicator(
                          color: t.accent,
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
                              padding: EdgeInsets.all(t.gapXL),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'TerraCipher',
                                    style: t.screenTitle.copyWith(
                                      color: t.textPrimary,
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    'dMRV Field Terminal v3.0',
                                    style: t.metadata.copyWith(
                                      color: t.textSecondary,
                                    ),
                                  ),
                                  SizedBox(height: t.gapXL),
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
                                        SizedBox(width: t.gapM),
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
                                    loading: () => Center(
                                      child: CircularProgressIndicator(
                                        color: t.accent,
                                      ),
                                    ),
                                    error: (err, stack) => Text(
                                      'Stats Error: $err',
                                      style: t.metadata.copyWith(
                                        color: t.danger,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            SizedBox(height: t.gapS),
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

                            SizedBox(height: t.gapXL),
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
                    color: t.textPrimary.withValues(alpha: 0.92),
                    child: Center(
                      child: Padding(
                        padding: EdgeInsets.all(t.gapXL),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.security, size: 64, color: t.danger),
                            SizedBox(height: t.gapL),
                            Text(
                              'SECURITY COMPROMISE DETECTED',
                              textAlign: TextAlign.center,
                              style: t.blockHeader.copyWith(color: t.danger),
                            ),
                            SizedBox(height: t.gapM),
                            Text(
                              'This device has failed hardware integrity checks (e.g. root, emulator, or hooking framework).\n\nAccess to TerraCipher is permanently locked to prevent Sybil attacks.',
                              textAlign: TextAlign.center,
                              style: t.body.copyWith(color: t.surface),
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
