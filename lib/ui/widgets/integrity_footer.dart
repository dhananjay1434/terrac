import 'package:flutter/material.dart';

import '../design/tokens.dart';

/// The persistent trust strip at the bottom of every screen.
///
/// Paper surface with a hairline top rule (no dark "vault" panel, no heavy
/// shadow — both die in sunlight). A small live dot + integrity line, and the
/// last evidence hash in tabular metadata. Reads entirely from tokens.
class IntegrityFooter extends StatelessWidget {
  final String lastHash;

  const IntegrityFooter({super.key, required this.lastHash});

  @override
  Widget build(BuildContext context) {
    final t = context.tokens;

    return Container(
      width: double.infinity,
      padding: EdgeInsets.fromLTRB(t.gapXL, t.gapL, t.gapXL, t.gapXL + 8),
      decoration: BoxDecoration(
        color: t.surface,
        border: Border(top: BorderSide(color: t.border, width: 1.5)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(
                  color: t.live,
                  shape: BoxShape.circle,
                ),
              ),
              SizedBox(width: t.gapS),
              Text(
                'SYSTEM INTEGRITY: SECURE',
                style: t.chipLabel.copyWith(color: t.success),
              ),
            ],
          ),
          SizedBox(height: t.gapS),
          Text(
            'LAST HASH: $lastHash',
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: t.metadata.copyWith(
              color: t.textSecondary,
              fontFeatures: const [FontFeature.tabularFigures()],
            ),
          ),
        ],
      ),
    );
  }
}
