import 'package:flutter/material.dart';

import '../../../providers/multichannel_burn_notifier.dart';
import '../../design/premium_field_components.dart';
import '../../design/tokens.dart';

/// Presentational multi-channel burn HUD: one tile per active channel in
/// [state.channels]. Thermocouples show °C, LOAD shows kg. No state, no
/// producer, no persistence — purely renders what it is given.
class MultiChannelBurnHud extends StatelessWidget {
  const MultiChannelBurnHud({super.key, required this.state});
  final MultiChannelBurnState state;

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;
    if (state.channels.isEmpty) {
      return PremiumFieldPanel(
        child: Text(
          'NO ACTIVE CHANNELS',
          style: t.chipLabel.copyWith(color: t.textSecondary),
        ),
      );
    }
    return Wrap(
      spacing: t.gapM,
      runSpacing: t.gapM,
      children: [
        for (final channel in state.channels) _channelTile(t, channel),
      ],
    );
  }

  Widget _channelTile(DmrvTokens t, String channel) {
    final isLoad = channel == 'LOAD';
    final unit = isLoad ? 'kg' : '°C';
    final live = state.live[channel];
    final min = state.min[channel];
    final max = state.max[channel];
    final reading = live?.toStringAsFixed(1) ?? '----';

    return SizedBox(
      width: 150,
      child: PremiumFieldPanel(
        accentBorderColor: live != null ? t.accent : null,
        padding: EdgeInsets.all(t.gapM),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              channel,
              style: t.chipLabel.copyWith(
                color: live != null ? t.accentText : t.textSecondary,
              ),
            ),
            SizedBox(height: t.gapS),
            Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Flexible(
                  child: Text(
                    reading,
                    style: t.numericHero.copyWith(
                      fontSize: 28,
                      color: live != null ? t.accent : t.textDisabled,
                    ),
                  ),
                ),
                SizedBox(width: t.gapS),
                Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Text(
                    unit,
                    style: t.metadata.copyWith(color: t.textSecondary),
                  ),
                ),
              ],
            ),
            SizedBox(height: t.gapS),
            Text(
              'min=${min == null ? "-" : min.toStringAsFixed(1)}  '
              'max=${max == null ? "-" : max.toStringAsFixed(1)}',
              style: t.metadata.copyWith(color: t.textSecondary, fontSize: 11),
            ),
          ],
        ),
      ),
    );
  }
}
