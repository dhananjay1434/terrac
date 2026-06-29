import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../design/app_theme.dart';

enum CardStatus {
  locked, // Card is inactive, waiting for a prior step to complete.
  pending, // Card is active and waiting for BLE hardware response.
  verified, // Cryptographic hash has been confirmed for this step.
}

@immutable
class ActionCardData {
  final String title;
  final String subtitleHindi;
  final IconData icon;
  final CardStatus status;
  final VoidCallback? onTap;

  const ActionCardData({
    required this.title,
    required this.subtitleHindi,
    required this.icon,
    required this.status,
    this.onTap,
  });

  ActionCardData copyWith({
    String? title,
    String? subtitleHindi,
    IconData? icon,
    CardStatus? status,
    VoidCallback? onTap,
  }) {
    return ActionCardData(
      title: title ?? this.title,
      subtitleHindi: subtitleHindi ?? this.subtitleHindi,
      icon: icon ?? this.icon,
      status: status ?? this.status,
      onTap: onTap ?? this.onTap,
    );
  }
}

class PremiumActionCard extends StatelessWidget {
  final ActionCardData data;

  const PremiumActionCard({super.key, required this.data});

  @override
  Widget build(BuildContext context) {
    final bool isLocked = data.status == CardStatus.locked;
    final bool isVerified = data.status == CardStatus.verified;

    final Color accentColor = isLocked
        ? Colors.grey
        : isVerified
        ? AppTheme.yieldGold
        : AppTheme.cobaltShield;

    final Color textColor = isLocked ? Colors.grey : AppTheme.armorSlate;

    return Opacity(
      opacity: isLocked ? 0.5 : 1.0,
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: AppTheme.pureAlbedo,
          borderRadius: BorderRadius.circular(16),
          border: isVerified
              ? Border.all(color: AppTheme.yieldGold, width: 2)
              : null,
          boxShadow: isVerified
              ? [
                  BoxShadow(
                    color: AppTheme.yieldGold30,
                    blurRadius: 12,
                    spreadRadius: 2,
                  ),
                ]
              : null,
        ),
        child: Material(
          color: Colors.transparent,
          borderRadius: BorderRadius.circular(16),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: isLocked
                ? null
                : () {
                    // HeavyImpact is required because industrial gloves
                    // dampen tactile sensation. MediumImpact is not sufficient.
                    HapticFeedback.heavyImpact();
                    data.onTap?.call();
                  },
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Row(
                children: [
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      color: accentColor.withValues(alpha: 0.1),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(data.icon, size: 32, color: accentColor),
                  ),
                  const SizedBox(width: 20),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          data.title,
                          style: Theme.of(
                            context,
                          ).textTheme.titleLarge?.copyWith(color: textColor),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          data.subtitleHindi,
                          style: Theme.of(
                            context,
                          ).textTheme.bodyLarge?.copyWith(color: textColor),
                        ),
                      ],
                    ),
                  ),
                  if (isVerified)
                    const Padding(
                      padding: EdgeInsets.only(left: 12),
                      child: Icon(
                        Icons.check_circle,
                        color: AppTheme.yieldGold,
                        size: 28,
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
