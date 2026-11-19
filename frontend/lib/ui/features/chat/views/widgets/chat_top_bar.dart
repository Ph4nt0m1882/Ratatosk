import 'package:flutter/material.dart';

import '../../../../../domain/models/app_theme_spec.dart';
import '../../../../core/l10n/locale_controller.dart';
import '../../../../core/theme/appearance_modal.dart';
import '../../../../core/theme/theme_controller.dart';
import '../../view_models/chat_view_model.dart';

class ChatTopBar extends StatelessWidget {
  const ChatTopBar({
    super.key,
    required this.viewModel,
    required this.themeController,
    required this.isSidebarOpen,
    required this.onToggleSidebar,
  });

  final ChatViewModel viewModel;
  final ThemeController themeController;
  final bool isSidebarOpen;
  final VoidCallback onToggleSidebar;

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;
    final l10n = context.l10n;
    final localeCtrl = LocaleControllerScope.maybeOf(context);
    final currentLang = localeCtrl?.locale.languageCode ?? 'en';
    final activeConv = viewModel.activeConversationId == null
        ? null
        : viewModel.conversations
            .where((c) => c.id == viewModel.activeConversationId)
            .firstOrNull;

    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 12, 18, 6),
      child: Row(
        children: [
          if (!isSidebarOpen) ...[
            _FloatingTopPill(
              tooltip: l10n.topBarOpenChatsTooltip,
              onTap: onToggleSidebar,
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.menu_book_rounded,
                    size: 18,
                    color: spec.accentColor,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    l10n.topBarOpenChats,
                    style: TextStyle(
                      color: spec.textColor,
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 10),
          ],

          if (activeConv != null && viewModel.messages.isNotEmpty)
            Flexible(
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
                decoration: BoxDecoration(
                  color: spec.surfaceColor.withValues(alpha: 0.72),
                  borderRadius: BorderRadius.circular(999),
                  border: Border.all(
                    color: spec.borderColor.withValues(alpha: 0.7),
                  ),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.chat_bubble_outline_rounded,
                      size: 15,
                      color: spec.accentColor,
                    ),
                    const SizedBox(width: 8),
                    Flexible(
                      child: Text(
                        activeConv.title,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          color: spec.textColor,
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),

          const Spacer(),

          if (localeCtrl != null) ...[
            _FloatingTopPill(
              tooltip: l10n.languageLabel,
              onTap: () => localeCtrl.setLocale(
                Locale(currentLang == 'en' ? 'fr' : 'en'),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.translate_rounded,
                    size: 15,
                    color: spec.accentColor,
                  ),
                  const SizedBox(width: 6),
                  Text(
                    currentLang.toUpperCase(),
                    style: TextStyle(
                      color: spec.textColor,
                      fontSize: 12,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
          ],

          // Quick Theme / Ambiance Pill
          _FloatingTopPill(
            tooltip: l10n.topBarThemeTooltip(spec.name),
            onTap: () => AppearanceModal.show(
              context,
              themeController,
              session: viewModel.session,
              initialSection: SettingsSection.themes,
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 12,
                  height: 12,
                  decoration: BoxDecoration(
                    color: spec.accentColor,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 8),
                Icon(
                  Icons.palette_outlined,
                  size: 17,
                  color: spec.textColor,
                ),
                const SizedBox(width: 6),
                Text(
                  spec.name,
                  style: TextStyle(
                    color: spec.textColor,
                    fontSize: 12.5,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),

          if (!isSidebarOpen) ...[
            const SizedBox(width: 8),
            _FloatingTopPill(
              tooltip: l10n.topBarSettingsTooltip,
              onTap: () => AppearanceModal.show(
                context,
                themeController,
                session: viewModel.session,
                initialSection: SettingsSection.general,
              ),
              child: Icon(
                Icons.tune_rounded,
                size: 18,
                color: spec.subtextColor,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _FloatingTopPill extends StatelessWidget {
  const _FloatingTopPill({
    required this.onTap,
    required this.child,
    this.tooltip,
  });

  final VoidCallback onTap;
  final Widget child;
  final String? tooltip;

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;
    final pill = Material(
      color: spec.surfaceColor.withValues(alpha: 0.9),
      borderRadius: BorderRadius.circular(999),
      child: InkWell(
        borderRadius: BorderRadius.circular(999),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(999),
            border: Border.all(color: spec.borderColor),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.1),
                blurRadius: 10,
                offset: const Offset(0, 3),
              ),
            ],
          ),
          child: child,
        ),
      ),
    );
    if (tooltip != null) {
      return Tooltip(message: tooltip!, child: pill);
    }
    return pill;
  }
}
