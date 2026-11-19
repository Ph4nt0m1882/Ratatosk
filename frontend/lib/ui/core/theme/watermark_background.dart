import 'package:flutter/material.dart';

import '../../../domain/models/app_theme_spec.dart';

class WatermarkBackground extends StatelessWidget {
  const WatermarkBackground({
    super.key,
    required this.child,
  });

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;
    final asset = spec.watermarkAsset;

    return ColoredBox(
      color: spec.backgroundColor,
      child: Stack(
        fit: StackFit.expand,
        children: [
          if (asset != null)
            IgnorePointer(
              child: Align(
                alignment: Alignment.centerRight,
                child: FractionallySizedBox(
                  widthFactor: 0.72,
                  heightFactor: 0.88,
                  child: Image.asset(
                    asset,
                    fit: BoxFit.contain,
                    alignment: Alignment.centerRight,
                    color: (spec.watermarkColor ?? spec.accentColor)
                        .withValues(alpha: spec.watermarkOpacity),
                    colorBlendMode: BlendMode.srcIn,
                  ),
                ),
              ),
            ),
          child,
        ],
      ),
    );
  }
}
