import 'package:flutter/material.dart';

import '../../../../../domain/models/app_theme_spec.dart';
import '../../../../../l10n/app_localizations.dart';
import '../../../../core/l10n/locale_controller.dart';
import '../../../../core/widgets/ratatosk_logo.dart';
import '../../view_models/chat_view_model.dart';

class ChatWelcomeHero extends StatelessWidget {
  const ChatWelcomeHero({
    super.key,
    required this.viewModel,
  });

  final ChatViewModel viewModel;

  static String _greetingForHour(
    AppLocalizations l10n,
    int hour,
    String username,
  ) {
    final cleanName = username.trim().isEmpty ? 'Ratatosk' : username.trim();
    if (hour >= 5 && hour < 12) {
      return l10n.welcomeMorning(cleanName);
    }
    if (hour >= 12 && hour < 18) {
      return l10n.welcomeAfternoon(cleanName);
    }
    return l10n.welcomeEvening(cleanName);
  }

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;
    final l10n = context.l10n;
    final greeting = _greetingForHour(
      l10n,
      DateTime.now().hour,
      viewModel.session.username,
    );

    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 20),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 740),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Glowing Ratatosk Medallion
              Container(
                width: 88,
                height: 88,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: RadialGradient(
                    colors: [
                      spec.accentColor.withValues(alpha: 0.26),
                      spec.surfaceColor.withValues(alpha: 0.85),
                    ],
                  ),
                  border: Border.all(
                    color: spec.accentColor.withValues(alpha: 0.45),
                    width: 1.5,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: spec.accentColor.withValues(alpha: 0.2),
                      blurRadius: 28,
                      spreadRadius: 2,
                    ),
                  ],
                ),
                child: const RatatoskLogo(size: 50),
              ),
              const SizedBox(height: 18),

              // Warm personal greeting
              Text(
                greeting,
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: spec.textColor,
                  fontSize: 28,
                  fontWeight: FontWeight.w800,
                  letterSpacing: -0.3,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                l10n.welcomeSubtitle,
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: spec.subtextColor,
                  fontSize: 15,
                  height: 1.35,
                ),
              ),
              const SizedBox(height: 32),

              // 4 Dedicated Universe Hub Cards (2x2 on desktop/tablet, 1 col on narrow screens)
              LayoutBuilder(
                builder: (context, constraints) {
                  void showComingSoon(String modeName, String details) {
                    ScaffoldMessenger.of(context)
                      ..hideCurrentSnackBar()
                      ..showSnackBar(
                        SnackBar(
                          behavior: SnackBarBehavior.floating,
                          backgroundColor: spec.surfaceColor,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(14),
                            side: BorderSide(color: spec.borderColor),
                          ),
                          content: Text(
                            l10n.hubComingSoon(modeName, details),
                            style: TextStyle(
                              color: spec.textColor,
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      );
                  }

                  final twoCols = constraints.maxWidth >= 520;
                  final cards = [
                    _InspirationCard(
                      icon: Icons.brush_rounded,
                      badgeColor: const Color(0xFFF59E0B),
                      title: l10n.hubDrawTitle,
                      subtitle: l10n.hubDrawSubtitle,
                      onTap: () => showComingSoon(
                        l10n.hubDrawTitle,
                        l10n.hubDrawDetails,
                      ),
                    ),
                    _InspirationCard(
                      icon: Icons.travel_explore_rounded,
                      badgeColor: const Color(0xFF38BDF8),
                      title: l10n.hubExploreTitle,
                      subtitle: l10n.hubExploreSubtitle,
                      onTap: () => showComingSoon(
                        l10n.hubExploreTitle,
                        l10n.hubExploreDetails,
                      ),
                    ),
                    _InspirationCard(
                      icon: Icons.menu_book_rounded,
                      badgeColor: const Color(0xFF10B981),
                      title: l10n.hubLearnTitle,
                      subtitle: l10n.hubLearnSubtitle,
                      onTap: () => showComingSoon(
                        l10n.hubLearnTitle,
                        l10n.hubLearnDetails,
                      ),
                    ),
                    _InspirationCard(
                      icon: Icons.sports_esports_rounded,
                      badgeColor: const Color(0xFFA855F7),
                      title: l10n.hubPlayTitle,
                      subtitle: l10n.hubPlaySubtitle,
                      onTap: () => showComingSoon(
                        l10n.hubPlayTitle,
                        l10n.hubPlayDetails,
                      ),
                    ),
                  ];

                  if (!twoCols) {
                    return Column(
                      children: cards
                          .map(
                            (c) => Padding(
                              padding: const EdgeInsets.only(bottom: 12),
                              child: c,
                            ),
                          )
                          .toList(),
                    );
                  }

                  return Column(
                    children: [
                      Row(
                        children: [
                          Expanded(child: cards[0]),
                          const SizedBox(width: 14),
                          Expanded(child: cards[1]),
                        ],
                      ),
                      const SizedBox(height: 14),
                      Row(
                        children: [
                          Expanded(child: cards[2]),
                          const SizedBox(width: 14),
                          Expanded(child: cards[3]),
                        ],
                      ),
                    ],
                  );
                },
              ),

              // Recent conversations quick pills
              if (viewModel.conversations.isNotEmpty) ...[
                const SizedBox(height: 28),
                Text(
                  l10n.welcomeResumeSection,
                  style: TextStyle(
                    color: spec.subtextColor,
                    fontSize: 12.5,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 10),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  alignment: WrapAlignment.center,
                  children: viewModel.conversations.take(4).map((conv) {
                    return Material(
                      color: spec.surfaceColor.withValues(alpha: 0.85),
                      borderRadius: BorderRadius.circular(999),
                      child: InkWell(
                        borderRadius: BorderRadius.circular(999),
                        onTap: () => viewModel.selectConversation(conv.id),
                        child: Container(
                          constraints: const BoxConstraints(maxWidth: 230),
                          padding: const EdgeInsets.symmetric(
                            horizontal: 14,
                            vertical: 8,
                          ),
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(999),
                            border: Border.all(color: spec.borderColor),
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(
                                Icons.history_rounded,
                                size: 15,
                                color: spec.accentColor,
                              ),
                              const SizedBox(width: 7),
                              Flexible(
                                child: Text(
                                  conv.title,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: TextStyle(
                                    color: spec.textColor,
                                    fontSize: 12.5,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    );
                  }).toList(),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _InspirationCard extends StatefulWidget {
  const _InspirationCard({
    required this.icon,
    required this.badgeColor,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final Color badgeColor;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  State<_InspirationCard> createState() => _InspirationCardState();
}

class _InspirationCardState extends State<_InspirationCard> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;

    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: AnimatedScale(
        scale: _hovered ? 1.02 : 1.0,
        duration: const Duration(milliseconds: 160),
        curve: Curves.easeOutCubic,
        child: Material(
          color: spec.surfaceColor.withValues(alpha: _hovered ? 0.96 : 0.86),
          borderRadius: BorderRadius.circular(20),
          child: InkWell(
            borderRadius: BorderRadius.circular(20),
            onTap: widget.onTap,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 160),
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: _hovered
                      ? widget.badgeColor.withValues(alpha: 0.7)
                      : spec.borderColor,
                  width: _hovered ? 1.5 : 1.0,
                ),
                boxShadow: [
                  BoxShadow(
                    color: _hovered
                        ? widget.badgeColor.withValues(alpha: 0.16)
                        : Colors.black.withValues(alpha: 0.08),
                    blurRadius: _hovered ? 18 : 10,
                    offset: const Offset(0, 5),
                  ),
                ],
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 44,
                    height: 44,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: widget.badgeColor.withValues(alpha: 0.16),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(
                        color: widget.badgeColor.withValues(alpha: 0.35),
                      ),
                    ),
                    child: Icon(
                      widget.icon,
                      color: widget.badgeColor,
                      size: 22,
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          widget.title,
                          style: TextStyle(
                            color: spec.textColor,
                            fontSize: 15,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          widget.subtitle,
                          style: TextStyle(
                            color: spec.subtextColor,
                            fontSize: 12.5,
                            height: 1.35,
                          ),
                        ),
                      ],
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
