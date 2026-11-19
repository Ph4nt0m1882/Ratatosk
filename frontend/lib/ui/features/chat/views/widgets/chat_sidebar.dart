import 'package:flutter/material.dart';

import '../../../../../domain/models/app_theme_spec.dart';
import '../../../../core/l10n/locale_controller.dart';
import '../../../../core/theme/appearance_modal.dart';
import '../../../../core/theme/theme_controller.dart';
import '../../../../core/widgets/ratatosk_logo.dart';
import '../../view_models/chat_view_model.dart';

class ChatSidebar extends StatelessWidget {
  const ChatSidebar({
    super.key,
    required this.viewModel,
    required this.themeController,
    this.onLogout,
    this.onCollapse,
  });

  final ChatViewModel viewModel;
  final ThemeController themeController;
  final VoidCallback? onLogout;
  final VoidCallback? onCollapse;

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;
    final l10n = context.l10n;

    return Container(
      decoration: BoxDecoration(
        color: spec.surfaceColor.withValues(alpha: 0.92),
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: spec.borderColor),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.16),
            blurRadius: 20,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Brand header
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 16, 10, 12),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(7),
                  decoration: BoxDecoration(
                    color: spec.accentColor.withValues(alpha: 0.14),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const RatatoskLogo(size: 22),
                ),
                const SizedBox(width: 11),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        l10n.appTitle,
                        style: TextStyle(
                          color: spec.textColor,
                          fontSize: 17,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 0.2,
                        ),
                      ),
                      Text(
                        l10n.sidebarSubtitle,
                        style: TextStyle(
                          color: spec.subtextColor,
                          fontSize: 11.5,
                        ),
                      ),
                    ],
                  ),
                ),
                if (onCollapse != null)
                  IconButton(
                    tooltip: l10n.sidebarCollapseTooltip,
                    onPressed: onCollapse,
                    visualDensity: VisualDensity.compact,
                    icon: Icon(
                      Icons.chevron_left_rounded,
                      color: spec.subtextColor,
                      size: 22,
                    ),
                  ),
              ],
            ),
          ),

          // Big tactile "New Chat" pill button
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14),
            child: FilledButton.icon(
              style: FilledButton.styleFrom(
                backgroundColor: spec.accentColor,
                foregroundColor: Colors.white,
                elevation: 0,
                padding:
                    const EdgeInsets.symmetric(vertical: 13, horizontal: 14),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
              ),
              onPressed: viewModel.startNewConversation,
              icon: const Icon(Icons.auto_awesome_rounded, size: 18),
              label: Text(
                l10n.sidebarNewChat,
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),

          const SizedBox(height: 18),

          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 18),
            child: Row(
              children: [
                Icon(
                  Icons.forum_outlined,
                  size: 14,
                  color: spec.subtextColor,
                ),
                const SizedBox(width: 6),
                Text(
                  l10n.sidebarMyChats,
                  style: TextStyle(
                    color: spec.subtextColor,
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),

          // Conversation list
          Expanded(
            child: viewModel.conversations.isEmpty
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.wb_sunny_outlined,
                            size: 28,
                            color: spec.subtextColor.withValues(alpha: 0.6),
                          ),
                          const SizedBox(height: 10),
                          Text(
                            l10n.sidebarEmptyChats,
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              color: spec.subtextColor,
                              fontSize: 12.5,
                              height: 1.4,
                            ),
                          ),
                        ],
                      ),
                    ),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    itemCount: viewModel.conversations.length,
                    itemBuilder: (context, index) {
                      final conv = viewModel.conversations[index];
                      final isSelected =
                          conv.id == viewModel.activeConversationId;
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 6),
                        child: Material(
                          color: isSelected
                              ? spec.accentColor.withValues(alpha: 0.16)
                              : Colors.transparent,
                          borderRadius: BorderRadius.circular(13),
                          child: InkWell(
                            borderRadius: BorderRadius.circular(13),
                            onTap: () => viewModel.selectConversation(conv.id),
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 12,
                                vertical: 10,
                              ),
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(13),
                                border: isSelected
                                    ? Border.all(
                                        color: spec.accentColor
                                            .withValues(alpha: 0.5),
                                      )
                                    : null,
                              ),
                              child: Row(
                                children: [
                                  Icon(
                                    isSelected
                                        ? Icons.chat_bubble_rounded
                                        : Icons.chat_bubble_outline_rounded,
                                    size: 16,
                                    color: isSelected
                                        ? spec.accentColor
                                        : spec.subtextColor,
                                  ),
                                  const SizedBox(width: 10),
                                  Expanded(
                                    child: Text(
                                      conv.title,
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: TextStyle(
                                        color: spec.textColor,
                                        fontSize: 13.5,
                                        fontWeight: isSelected
                                            ? FontWeight.w700
                                            : FontWeight.w500,
                                      ),
                                    ),
                                  ),
                                  InkWell(
                                    borderRadius: BorderRadius.circular(8),
                                    onTap: () =>
                                        viewModel.deleteConversation(conv.id),
                                    child: Padding(
                                      padding: const EdgeInsets.all(4),
                                      child: Icon(
                                        Icons.delete_outline_rounded,
                                        size: 16,
                                        color: spec.subtextColor
                                            .withValues(alpha: 0.8),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      );
                    },
                  ),
          ),

          // Warm user capsule footer
          Container(
            margin: const EdgeInsets.all(12),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: BoxDecoration(
              color: spec.backgroundColor.withValues(alpha: 0.55),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: spec.borderColor),
            ),
            child: Row(
              children: [
                CircleAvatar(
                  radius: 17,
                  backgroundColor: spec.accentColor.withValues(alpha: 0.22),
                  child: Text(
                    viewModel.session.username.isNotEmpty
                        ? viewModel.session.username
                            .substring(0, 1)
                            .toUpperCase()
                        : 'R',
                    style: TextStyle(
                      color: spec.accentColor,
                      fontWeight: FontWeight.w800,
                      fontSize: 14,
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        viewModel.session.username,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          color: spec.textColor,
                          fontSize: 13.5,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      Text(
                        viewModel.session.isAdmin
                            ? l10n.sidebarRoleAdmin
                            : l10n.sidebarRoleMember,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          color: spec.subtextColor,
                          fontSize: 11,
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  tooltip: l10n.sidebarOpenSettings,
                  visualDensity: VisualDensity.compact,
                  onPressed: () => AppearanceModal.show(
                    context,
                    themeController,
                    session: viewModel.session,
                    initialSection: SettingsSection.general,
                  ),
                  icon: Icon(
                    Icons.tune_rounded,
                    size: 19,
                    color: spec.accentColor,
                  ),
                ),
                if (onLogout != null)
                  IconButton(
                    tooltip: l10n.sidebarLogout,
                    visualDensity: VisualDensity.compact,
                    onPressed: onLogout,
                    icon: Icon(
                      Icons.logout_rounded,
                      size: 18,
                      color: spec.subtextColor,
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
