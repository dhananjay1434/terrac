import 'package:flutter/material.dart';

import '../design/app_theme.dart';

class IntegrityFooter extends StatelessWidget {
  final String lastHash;

  const IntegrityFooter({super.key, required this.lastHash});

  @override
  Widget build(BuildContext context) {
    final TextStyle? monoStyle = Theme.of(context).textTheme.bodyMedium;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(24, 16, 24, 32),
      decoration: const BoxDecoration(
        color: AppTheme.midnightCyber,
        boxShadow: [
          BoxShadow(
            color: Color(0x66000000),
            blurRadius: 20,
            offset: Offset(0, -4),
          ),
        ],
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
                decoration: const BoxDecoration(
                  color: AppTheme.telemetryCyan,
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 8),
              Text(
                'SYSTEM INTEGRITY: SECURE',
                style: monoStyle?.copyWith(color: AppTheme.telemetryCyan),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'LAST HASH: $lastHash',
            style: monoStyle?.copyWith(color: AppTheme.telemetryCyan70),
          ),
        ],
      ),
    );
  }
}
