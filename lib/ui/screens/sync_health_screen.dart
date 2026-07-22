import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/local/app_database.dart';
import '../../providers/sync_providers.dart';
import '../../providers/upload_progress_provider.dart';
import '../../services/sync_queue_manager.dart';
import '../components/dmrv_button.dart';
import '../components/dmrv_panel.dart';
import '../design/tokens.dart';

/// Operator-facing view of the offline sync queue: a clock-skew warning, a
/// Synced / Waiting / Stuck summary, and every problem row with its verbatim
/// failure reason and a per-row RETRY (plus RETRY ALL when anything is stuck).
///
/// There is deliberately NO delete/dismiss action — evidence rows are never
/// operator-deletable (audit integrity). The only escape from a stuck row is
/// to fix the cause and retry it.
class SyncHealthScreen extends ConsumerWidget {
  const SyncHealthScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = context.tokens;
    final skew = ref.watch(clockSkewProvider);
    final problems = ref.watch(problemOutboxRowsProvider);
    final syncedCount = ref.watch(syncedOutboxCountProvider).valueOrNull ?? 0;
    // V8 Part 4 (H) — in-flight media upload progress, keyed by operationId.
    // Independent of the problem-rows query above: a first-attempt upload
    // (retryCount 0, not yet failed) never appears there, so this is the
    // only place progress on a fresh upload is visible.
    final uploadProgress = ref.watch(uploadProgressProvider);

    return Scaffold(
      backgroundColor: t.surface,
      body: SafeArea(
        bottom: false,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _Header(title: 'Sync Health', onBack: () => Navigator.of(context).pop()),
            Expanded(
              child: problems.when(
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (e, _) => Center(
                  child: Padding(
                    padding: EdgeInsets.all(t.gapL),
                    child: Text(
                      'Could not read the sync queue: $e',
                      style: t.body.copyWith(color: t.danger),
                    ),
                  ),
                ),
                data: (rows) {
                  final stuck = rows
                      .where((r) => r.status == 'FAILED_PERMANENTLY')
                      .toList();
                  final waiting = rows
                      .where((r) => r.status != 'FAILED_PERMANENTLY')
                      .toList();
                  return ListView(
                    padding: EdgeInsets.fromLTRB(t.gapL, 4, t.gapL, t.gapL),
                    children: [
                      if (skew != null) ...[
                        _ClockSkewBanner(skew: skew),
                        SizedBox(height: t.gapL),
                      ],
                      if (uploadProgress.isNotEmpty) ...[
                        _UploadProgressBanner(progress: uploadProgress),
                        SizedBox(height: t.gapL),
                      ],
                      _SummaryRow(
                        synced: syncedCount,
                        waiting: waiting.length,
                        stuck: stuck.length,
                      ),
                      SizedBox(height: t.gapL),
                      if (stuck.isNotEmpty) ...[
                        DmrvButton(
                          label: 'RETRY ALL STUCK (${stuck.length})',
                          testId: 'retry-all-btn',
                          variant: DmrvButtonVariant.primary,
                          onPressed: () => ref
                              .read(syncQueueManagerProvider)
                              .retryAllPermanentlyFailed(),
                        ),
                        SizedBox(height: t.gapL),
                      ],
                      if (rows.isEmpty)
                        _EmptyState()
                      else
                        for (final row in rows) ...[
                          _ProblemRowPanel(row: row),
                          SizedBox(height: t.gapM),
                        ],
                    ],
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Minimal back-button header (the shared PremiumScreenHeader stamps a "STEP N"
/// badge that only fits the numbered capture flow, not this utility screen).
class _Header extends StatelessWidget {
  const _Header({required this.title, required this.onBack});

  final String title;
  final VoidCallback onBack;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    return Padding(
      padding: EdgeInsets.symmetric(horizontal: t.gapL, vertical: t.gapM),
      child: Row(
        children: [
          Semantics(
            identifier: 'header.back',
            button: true,
            child: Material(
              color: t.surfaceRaised,
              borderRadius: BorderRadius.circular(t.radiusM),
              clipBehavior: Clip.antiAlias,
              child: InkWell(
                onTap: () {
                  HapticFeedback.heavyImpact();
                  onBack();
                },
                child: Container(
                  width: 48,
                  height: 48,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(t.radiusM),
                    border: Border.all(color: t.border, width: 1.5),
                  ),
                  child: Icon(
                    Icons.arrow_back_ios_new,
                    size: 20,
                    color: t.textPrimary,
                  ),
                ),
              ),
            ),
          ),
          SizedBox(width: t.gapM),
          Expanded(
            child: Text(
              title,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: t.blockHeader.copyWith(color: t.textPrimary),
            ),
          ),
        ],
      ),
    );
  }
}

class _ClockSkewBanner extends StatelessWidget {
  const _ClockSkewBanner({required this.skew});

  final Duration skew;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final minutes = skew.inMinutes.abs();
    return Container(
      width: double.infinity,
      padding: EdgeInsets.all(t.gapL),
      decoration: BoxDecoration(
        color: t.dangerSurface,
        borderRadius: BorderRadius.circular(t.radiusM),
        border: Border.all(color: t.danger, width: 1.5),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.schedule, color: t.danger, size: 22),
          SizedBox(width: t.gapM),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'PHONE CLOCK IS OFF',
                  style: t.chipLabel.copyWith(color: t.danger),
                ),
                SizedBox(height: t.gapS),
                Text(
                  "This phone's clock is off by $minutes "
                  '${minutes == 1 ? 'minute' : 'minutes'}. Fix Date & Time '
                  'settings (turn on automatic time) or evidence uploads will '
                  'be rejected.',
                  style: t.body.copyWith(color: t.textPrimary),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// V8 Part 4 (H) — shows the furthest-along in-flight upload's progress.
/// Uploads run one at a time in practice, but this takes the max fraction
/// defensively rather than assuming exactly one entry.
class _UploadProgressBanner extends StatelessWidget {
  const _UploadProgressBanner({required this.progress});

  final Map<String, double> progress;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    final fraction = progress.values.reduce((a, b) => a > b ? a : b);
    final pct = (fraction * 100).round();
    final count = progress.length;
    return DmrvPanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Semantics(
            identifier: 'upload-progress-label',
            child: Text(
              count > 1 ? 'UPLOADING EVIDENCE ($count)' : 'UPLOADING EVIDENCE',
              style: t.chipLabel.copyWith(color: t.accentText),
            ),
          ),
          SizedBox(height: t.gapS),
          Semantics(
            identifier: 'upload-progress-bar',
            value: '$pct%',
            child: ClipRRect(
              borderRadius: BorderRadius.circular(t.radiusS),
              child: LinearProgressIndicator(
                value: fraction,
                minHeight: 8,
                backgroundColor: t.surfaceRaised,
                valueColor: AlwaysStoppedAnimation(t.accent),
              ),
            ),
          ),
          SizedBox(height: t.gapS),
          Text('$pct%', style: t.metadata.copyWith(color: t.textSecondary)),
        ],
      ),
    );
  }
}

class _SummaryRow extends StatelessWidget {
  const _SummaryRow({
    required this.synced,
    required this.waiting,
    required this.stuck,
  });

  final int synced;
  final int waiting;
  final int stuck;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    return Row(
      children: [
        Expanded(
          child: _StatChip(label: 'SYNCED', count: synced, color: t.success),
        ),
        SizedBox(width: t.gapM),
        Expanded(
          child: _StatChip(label: 'WAITING', count: waiting, color: t.accentText),
        ),
        SizedBox(width: t.gapM),
        Expanded(
          child: _StatChip(label: 'STUCK', count: stuck, color: t.danger),
        ),
      ],
    );
  }
}

class _StatChip extends StatelessWidget {
  const _StatChip({
    required this.label,
    required this.count,
    required this.color,
  });

  final String label;
  final int count;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    return DmrvPanel(
      padding: EdgeInsets.all(t.gapM),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: t.chipLabel.copyWith(color: t.textSecondary)),
          SizedBox(height: t.gapS),
          Text('$count', style: t.numericMedium.copyWith(color: color)),
        ],
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    return DmrvPanel(
      child: Row(
        children: [
          Icon(Icons.check_circle_outline, color: t.success, size: 22),
          SizedBox(width: t.gapM),
          Expanded(
            child: Text(
              'Everything is synced. No evidence is waiting or stuck.',
              style: t.body.copyWith(color: t.textPrimary),
            ),
          ),
        ],
      ),
    );
  }
}

class _ProblemRowPanel extends ConsumerWidget {
  const _ProblemRowPanel({required this.row});

  final SyncOutboxData row;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = context.tokens;
    final isStuck = row.status == 'FAILED_PERMANENTLY';
    return DmrvPanel(
      accent: isStuck,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  _operationLabel(row.targetTable),
                  style: t.body.copyWith(
                    color: t.textPrimary,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              Text(
                isStuck ? 'STUCK' : 'WAITING',
                style: t.chipLabel.copyWith(
                  color: isStuck ? t.danger : t.accentText,
                ),
              ),
            ],
          ),
          SizedBox(height: t.gapS),
          Text(
            'Batch ${_shortBatch(row.batchUuid)}  ·  Last tried '
            '${_lastTried(row.lastAttemptAt)}'
            '${isStuck ? '' : '  ·  attempt ${row.retryCount}, waiting to retry'}',
            style: t.metadata.copyWith(color: t.textSecondary),
          ),
          if (row.failureReason != null &&
              row.failureReason!.isNotEmpty) ...[
            SizedBox(height: t.gapS),
            Text(
              row.failureReason!,
              style: t.metadata.copyWith(color: t.danger),
            ),
          ],
          // Stuck rows reset their retry ceiling (retryPermanentlyFailed);
          // backoff rows just skip the wait (retryNow) — either way the operator
          // is never left staring at a silently-stuck row with no action.
          SizedBox(height: t.gapM),
          DmrvButton(
            label: isStuck ? 'RETRY' : 'RETRY NOW',
            testId: 'retry-${row.operationId}',
            variant: DmrvButtonVariant.primary,
            fullWidth: false,
            minHeight: 48,
            onPressed: () {
              final mgr = ref.read(syncQueueManagerProvider);
              if (isStuck) {
                mgr.retryPermanentlyFailed(row.operationId);
              } else {
                mgr.retryNow(row.operationId);
              }
            },
          ),
        ],
      ),
    );
  }
}

/// Human label for a sync queue row, keyed by its target table. Keys mirror
/// [kEndpointByTable] in `sync_queue_manager.dart`.
String _operationLabel(String targetTable) {
  switch (targetTable) {
    case 'system_metadata':
      return 'Batch registration';
    case 'biomass_sourcing':
      return 'Biomass sourcing';
    case 'pyrolysis_telemetry':
      return 'Burn telemetry';
    case 'yield_metrics':
      return 'Yield measurement';
    case 'end_use_application':
      return 'End-use application';
    case 'moisture_readings':
      return 'Moisture reading';
    case 'composite_pile_samples':
      return 'Composite sample';
    case 'transport_events':
      return 'Transport event';
    default:
      return targetTable;
  }
}

String _shortBatch(String? batchUuid) {
  // Deferred R1 — entity-scoped media (farmer/dispatch) rows have no batch.
  if (batchUuid == null || batchUuid.isEmpty) return 'entity media';
  return batchUuid.length <= 8 ? batchUuid : batchUuid.substring(0, 8);
}

String _lastTried(String? lastAttemptAt) {
  if (lastAttemptAt == null || lastAttemptAt.isEmpty) return 'not yet';
  // ISO-8601 UTC; show "yyyy-MM-dd hh:mm" without pulling in intl.
  final t = lastAttemptAt.replaceFirst('T', ' ');
  return t.length >= 16 ? t.substring(0, 16) : t;
}
