import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/local/proof_queries.dart';
import '../../providers/sync_providers.dart';
import '../design/farmer_theme.dart';
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
    final receipts = ref.watch(cryptographicReceiptsProvider);

    return Scaffold(
      backgroundColor: FarmerTheme.deepSlate,
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
                    child: const Padding(
                      padding: EdgeInsets.all(8),
                      child: Icon(
                        Icons.arrow_back,
                        color: FarmerTheme.pureAlbedo,
                        size: 22,
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  const Expanded(
                    child: Text(
                      'PROOF WALLET',
                      style: TextStyle(
                        fontFamily: 'SpaceGrotesk',
                        fontSize: 20,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 1.0,
                        color: FarmerTheme.neonYellow,
                      ),
                    ),
                  ),
                  const Icon(
                    Icons.verified_user,
                    color: FarmerTheme.neonYellow,
                    size: 24,
                  ),
                ],
              ),
            ),
            // Body
            Expanded(
              child: receipts.when(
                loading: () => const Center(
                  child: CircularProgressIndicator(
                    color: FarmerTheme.neonYellow,
                  ),
                ),
                error: (e, stack) => Center(
                  child: Text(
                    'ERROR // $e',
                    style: const TextStyle(
                      fontFamily: 'SpaceMono',
                      fontSize: 14,
                      color: FarmerTheme.crimsonRed,
                    ),
                  ),
                ),
                data: (list) {
                  if (list.isEmpty) {
                    return const Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.inbox_outlined,
                            size: 64,
                            color: FarmerTheme.fogWhite,
                          ),
                          SizedBox(height: 16),
                          Text(
                            'NO BATCHES RECORDED',
                            style: TextStyle(
                              fontFamily: 'SpaceGrotesk',
                              fontSize: 16,
                              fontWeight: FontWeight.w700,
                              color: FarmerTheme.fogWhite,
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
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: FarmerTheme.panelSlate,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: FarmerTheme.neonYellow30, width: 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Batch header
          Text(
            'BATCH // ${receipt.batchUuid.substring(0, 8).toUpperCase()}',
            style: const TextStyle(
              fontFamily: 'SpaceGrotesk',
              fontSize: 15,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.8,
              color: FarmerTheme.neonYellow,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            receipt.createdAt,
            style: TextStyle(
              fontFamily: 'SpaceMono',
              fontSize: 10,
              color: FarmerTheme.fogWhite50,
            ),
          ),
          const SizedBox(height: 12),
          const Divider(color: FarmerTheme.fogWhite, height: 1, thickness: 0.2),
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
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: RichText(
        text: TextSpan(
          children: [
            TextSpan(
              text: '$label: ',
              style: TextStyle(
                fontFamily: 'SpaceMono',
                fontSize: 11,
                color: FarmerTheme.fogWhite50,
              ),
            ),
            TextSpan(
              text: value,
              style: const TextStyle(
                fontFamily: 'SpaceMono',
                fontSize: 11,
                color: FarmerTheme.fogWhite,
              ),
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
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: RichText(
        text: TextSpan(
          children: [
            TextSpan(
              text: '$label: ',
              style: TextStyle(
                fontFamily: 'SpaceMono',
                fontSize: 11,
                color: FarmerTheme.fogWhite50,
              ),
            ),
            TextSpan(
              text: hash ?? 'NO EVIDENCE',
              style: TextStyle(
                fontFamily: 'SpaceMono',
                fontSize: 11,
                color: hash != null
                    ? FarmerTheme.fieldGreen
                    : FarmerTheme.crimsonRed70,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
