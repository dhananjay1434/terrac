import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/local/proof_queries.dart';
import '../../providers/sync_providers.dart';
import '../design/tokens.dart';
import '../widgets/integrity_footer.dart';

/// =============================================================================
/// ProofWalletScreen — Zero-Trust Cryptographic Ledger (Phase 4)
/// =============================================================================
/// Renders the full batch lifecycle as a premium "Cryptographic Receipt" card.
/// Each card shows the SHA-256 hashes of every evidence artifact (biomass photo,
/// smoke photo), GPS coordinates, temperature telemetry, and locked yield weight.
/// =============================================================================
class ProofWalletScreen extends ConsumerWidget {
  const ProofWalletScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = context.tokens;
    final receipts = ref.watch(cryptographicReceiptsProvider);

    return Scaffold(
      backgroundColor: t.surface,
      body: SafeArea(
        bottom: false,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              child: Row(
                children: [
                  InkWell(
                    onTap: () => Navigator.of(context).pop(),
                    child: Padding(
                      padding: const EdgeInsets.all(8),
                      child: Icon(
                        Icons.arrow_back,
                        color: t.textPrimary,
                        size: 22,
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      'PROOF WALLET',
                      style: t.blockHeader.copyWith(
                        letterSpacing: 1.0,
                        color: t.certified,
                      ),
                    ),
                  ),
                  Icon(Icons.verified_user, color: t.certified, size: 24),
                ],
              ),
            ),
            // Body
            Expanded(
              child: receipts.when(
                loading: () =>
                    Center(child: CircularProgressIndicator(color: t.accent)),
                error: (e, stack) => Center(
                  child: Text(
                    'ERROR // $e',
                    style: t.metadata.copyWith(color: t.danger),
                  ),
                ),
                data: (list) {
                  if (list.isEmpty) {
                    return Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.inbox_outlined,
                            size: 64,
                            color: t.textSecondary,
                          ),
                          const SizedBox(height: 16),
                          Text(
                            'NO BATCHES RECORDED',
                            style: t.blockHeader.copyWith(
                              fontSize: 16,
                              color: t.textSecondary,
                            ),
                          ),
                        ],
                      ),
                    );
                  }
                  return ListView.separated(
                    padding: const EdgeInsets.fromLTRB(16, 4, 16, 16),
                    itemCount: list.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 12),
                    itemBuilder: (_, i) => _ReceiptCard(receipt: list[i]),
                  );
                },
              ),
            ),
            const IntegrityFooter(
              lastHash:
                  '----------------------------------------------------------------',
            ),
          ],
        ),
      ),
    );
  }
}

class _ReceiptCard extends StatelessWidget {
  const _ReceiptCard({required this.receipt});
  final CryptographicReceipt receipt;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: t.surfaceRaised,
        borderRadius: BorderRadius.circular(t.radiusM),
        border: Border.all(color: t.certified.withValues(alpha: 0.3), width: 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Batch header
          Text(
            'BATCH // ${receipt.batchUuid.substring(0, 8).toUpperCase()}',
            style: t.chipLabel.copyWith(fontSize: 15, color: t.certified),
          ),
          const SizedBox(height: 4),
          Text(
            receipt.createdAt,
            style: t.metadata.copyWith(fontSize: 10, color: t.textSecondary),
          ),
          const SizedBox(height: 12),
          Divider(color: t.border, height: 1, thickness: 1),
          const SizedBox(height: 12),
          // Data lines
          _Line(label: 'artisan', value: receipt.artisanId),
          _Line(
            label: 'species',
            value: receipt.feedstockSpecies ?? 'Lantana camara (Pending)',
          ),
          _Line(
            label: 'moisture',
            value: receipt.moisturePercent != null
                ? '${receipt.moisturePercent!.toStringAsFixed(1)}%'
                : '—',
          ),
          _MediaHashesList(batchUuid: receipt.batchUuid),
          _Line(
            label: 'gps',
            value: receipt.biomassLat != null && receipt.biomassLon != null
                ? '${receipt.biomassLat!.toStringAsFixed(4)}, ${receipt.biomassLon!.toStringAsFixed(4)}'
                : 'NO FIX',
          ),
          _Line(
            label: 'burn',
            value: receipt.burnStart != null
                ? '${receipt.burnStart} → ${receipt.burnEnd ?? "IN PROGRESS"}'
                : '—',
          ),
          _Line(
            label: 'temp_range',
            value: receipt.maxTemp != null
                ? '${receipt.minTemp!.toStringAsFixed(0)}°C — ${receipt.maxTemp!.toStringAsFixed(0)}°C (${receipt.sampleCount ?? 0} samples)'
                : '—',
          ),

          _Line(
            label: 'yield',
            value: receipt.yieldWeightKg != null
                ? '${receipt.yieldWeightKg!.toStringAsFixed(2)} kg'
                : '—',
          ),
        ],
      ),
    );
  }
}

class _MediaHashesList extends ConsumerWidget {
  const _MediaHashesList({required this.batchUuid});
  final String batchUuid;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final mediaAsync = ref.watch(batchMediaProvider(batchUuid));
    final media = mediaAsync.valueOrNull ?? [];

    if (media.isEmpty) {
      return const _HashLine(label: 'media_sha256', hash: null);
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: media.map((m) {
        return _HashLine(label: '${m.captureType}_sha256', hash: m.sha256Hash);
      }).toList(),
    );
  }
}

class _Line extends StatelessWidget {
  const _Line({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: RichText(
        text: TextSpan(
          children: [
            TextSpan(
              text: '$label: ',
              style: t.metadata.copyWith(fontSize: 11, color: t.textSecondary),
            ),
            TextSpan(
              text: value,
              style: t.metadata.copyWith(fontSize: 11, color: t.textPrimary),
            ),
          ],
        ),
      ),
    );
  }
}

class _HashLine extends StatelessWidget {
  const _HashLine({required this.label, required this.hash});
  final String label;
  final String? hash;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: RichText(
        text: TextSpan(
          children: [
            TextSpan(
              text: '$label: ',
              style: t.metadata.copyWith(fontSize: 11, color: t.textSecondary),
            ),
            TextSpan(
              text: hash ?? 'NO EVIDENCE',
              style: t.metadata.copyWith(
                fontSize: 11,
                color: hash != null ? t.success : t.danger,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
