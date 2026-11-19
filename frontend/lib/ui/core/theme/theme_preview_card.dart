import 'package:flutter/material.dart';

import '../../../domain/models/app_theme_spec.dart';

class ThemePreviewCard extends StatelessWidget {
  const ThemePreviewCard({
    super.key,
    required this.spec,
    required this.isSelected,
    required this.onTap,
    this.onDelete,
  });

  final AppThemeSpec spec;
  final bool isSelected;
  final VoidCallback onTap;
  final VoidCallback? onDelete;

  @override
  Widget build(BuildContext context) {
    final borderColor = isSelected ? spec.accentColor : spec.borderColor;
    final buttonTextColor =
        spec.accentColor.computeLuminance() > 0.5 ? Colors.black : Colors.white;

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        decoration: BoxDecoration(
          color: spec.backgroundColor,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: borderColor,
            width: isSelected ? 2.2 : 1.0,
          ),
          boxShadow: isSelected
              ? [
                  BoxShadow(
                    color: spec.accentColor.withValues(alpha: 0.28),
                    blurRadius: 12,
                    spreadRadius: 1,
                  ),
                ]
              : null,
        ),
        clipBehavior: Clip.antiAlias,
        child: Stack(
          children: [
            if (spec.watermarkAsset != null)
              Positioned.fill(
                child: IgnorePointer(
                  child: Align(
                    alignment: Alignment.bottomRight,
                    child: Opacity(
                      opacity: 0.22,
                      child: Image.asset(
                        spec.watermarkAsset!,
                        fit: BoxFit.contain,
                        color: spec.watermarkColor ?? spec.accentColor,
                        colorBlendMode: BlendMode.srcIn,
                      ),
                    ),
                  ),
                ),
              ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Header strip
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 8,
                  ),
                  color: spec.headerColor,
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          spec.name,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: spec.textColor,
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                      if (onDelete != null)
                        GestureDetector(
                          onTap: onDelete,
                          child: Padding(
                            padding: const EdgeInsets.only(right: 6),
                            child: Icon(
                              Icons.close_rounded,
                              size: 14,
                              color: spec.subtextColor,
                            ),
                          ),
                        ),
                      Icon(
                        Icons.link_rounded,
                        size: 14,
                        color: spec.accentColor,
                      ),
                    ],
                  ),
                ),
                // Skeleton body
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Container(
                          width: 78,
                          height: 9,
                          decoration: BoxDecoration(
                            color: spec.textColor,
                            borderRadius: BorderRadius.circular(4),
                          ),
                        ),
                        const SizedBox(height: 7),
                        Container(
                          width: 112,
                          height: 7,
                          decoration: BoxDecoration(
                            color: spec.subtextColor.withValues(alpha: 0.55),
                            borderRadius: BorderRadius.circular(4),
                          ),
                        ),
                        if (spec.subtitle != null) ...[
                          const SizedBox(height: 8),
                          Text(
                            spec.subtitle!,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              color: spec.subtextColor,
                              fontSize: 10,
                            ),
                          ),
                        ],
                        const Spacer(),
                        Align(
                          alignment: Alignment.bottomRight,
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 11,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: spec.accentColor,
                              borderRadius: BorderRadius.circular(999),
                            ),
                            child: Text(
                              'Actif',
                              style: TextStyle(
                                color: buttonTextColor,
                                fontSize: 10,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
