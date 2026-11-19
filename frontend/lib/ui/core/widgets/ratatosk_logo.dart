import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

class RatatoskLogo extends StatelessWidget {
  const RatatoskLogo({
    super.key,
    this.size = 48,
  });

  final double size;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: SvgPicture.asset(
        'assets/brandings/ratatosk.svg',
        fit: BoxFit.contain,
      ),
    );
  }
}
