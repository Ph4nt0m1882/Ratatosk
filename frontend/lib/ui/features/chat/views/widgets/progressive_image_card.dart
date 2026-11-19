import 'dart:convert';
import 'dart:ui';

import 'package:flutter/material.dart';

import '../../../../../domain/models/app_theme_spec.dart';
import '../../../../../domain/models/chat_models.dart';

class ProgressiveImageCard extends StatelessWidget {
  const ProgressiveImageCard({
    super.key,
    required this.progressState,
    required this.hasFinalAttachment,
  });

  final ImageProgressState progressState;
  final bool hasFinalAttachment;

  @override
  Widget build(BuildContext context) {
    if (hasFinalAttachment && progressState.progress >= 1.0) {
      return const SizedBox.shrink();
    }

    final spec = context.appTheme;
    final pct = (progressState.progress.clamp(0.0, 1.0) * 100).round();
    final b64 = progressState.previewBase64;
    final blurSigma = (1.0 - progressState.progress.clamp(0.0, 1.0)) * 12.0;

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      constraints: const BoxConstraints(maxWidth: 420),
      decoration: BoxDecoration(
        color: spec.headerColor.withValues(alpha: 0.65),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: spec.accentColor.withValues(alpha: 0.45),
        ),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (b64 != null && b64.isNotEmpty)
            SizedBox(
              height: 220,
              child: AnimatedSwitcher(
                duration: const Duration(milliseconds: 260),
                child: ImageFiltered(
                  key: ValueKey<int>(progressState.step),
                  imageFilter: ImageFilter.blur(
                    sigmaX: blurSigma,
                    sigmaY: blurSigma,
                  ),
                  child: Image.memory(
                    base64Decode(b64),
                    fit: BoxFit.cover,
                    width: double.infinity,
                  ),
                ),
              ),
            )
          else
            Container(
              height: 150,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    spec.backgroundColor,
                    spec.accentColor.withValues(alpha: 0.18),
                    spec.surfaceColor,
                  ],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
              ),
              child: ImageFiltered(
                imageFilter: ImageFilter.blur(
                  sigmaX: blurSigma.clamp(0.5, 8.0),
                  sigmaY: blurSigma.clamp(0.5, 8.0),
                ),
                child: Icon(
                  Icons.auto_fix_high_rounded,
                  size: 42,
                  color: spec.accentColor,
                ),
              ),
            ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(
                      Icons.blur_on_rounded,
                      size: 16,
                      color: spec.accentColor,
                    ),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        'Diffusion & Débruitage (${progressState.model})',
                        style: TextStyle(
                          color: spec.textColor,
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                    Text(
                      '$pct%',
                      style: TextStyle(
                        color: spec.accentColor,
                        fontSize: 12,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                ClipRRect(
                  borderRadius: BorderRadius.circular(999),
                  child: LinearProgressIndicator(
                    value: progressState.progress.clamp(0.05, 1.0),
                    minHeight: 5,
                    backgroundColor: spec.borderColor,
                    color: spec.accentColor,
                  ),
                ),
                if (progressState.status != null) ...[
                  const SizedBox(height: 6),
                  Text(
                    progressState.status!,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: spec.subtextColor,
                      fontSize: 11,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}
