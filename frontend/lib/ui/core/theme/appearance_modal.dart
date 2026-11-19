import 'package:flutter/material.dart';

import '../../../domain/models/app_theme_spec.dart';
import '../../../domain/models/user_session.dart';
import '../l10n/locale_controller.dart';
import 'admin_settings_panel.dart';
import 'custom_theme_dialog.dart';
import 'general_settings_panel.dart';
import 'theme_controller.dart';
import 'theme_preview_card.dart';

enum SettingsSection {
  general,
  themes,
  accessibility,
  admin,
}

class AppearanceModal extends StatefulWidget {
  const AppearanceModal({
    super.key,
    required this.themeController,
    this.session,
    this.initialSection = SettingsSection.themes,
  });

  final ThemeController themeController;
  final UserSession? session;
  final SettingsSection initialSection;

  static Future<void> show(
    BuildContext context,
    ThemeController controller, {
    UserSession? session,
    SettingsSection initialSection = SettingsSection.themes,
  }) {
    return showDialog<void>(
      context: context,
      builder: (_) => AppearanceModal(
        themeController: controller,
        session: session,
        initialSection: initialSection,
      ),
    );
  }

  @override
  State<AppearanceModal> createState() => _AppearanceModalState();
}

class _AppearanceModalState extends State<AppearanceModal> {
  late SettingsSection _activeSection = widget.initialSection;

  Future<void> _openCreateTheme(BuildContext context) async {
    final created = await showDialog<AppThemeSpec>(
      context: context,
      builder: (_) => const CustomThemeDialog(),
    );
    if (created != null) {
      await widget.themeController.addCustomTheme(created);
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: widget.themeController,
      builder: (context, _) {
        final spec = context.appTheme;
        final isAdmin = widget.session?.isAdmin ?? false;

        return Dialog(
          backgroundColor: spec.surfaceColor,
          insetPadding: const EdgeInsets.symmetric(
            horizontal: 24,
            vertical: 28,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20),
            side: BorderSide(color: spec.borderColor),
          ),
          clipBehavior: Clip.antiAlias,
          child: ConstrainedBox(
            constraints: const BoxConstraints(
              maxWidth: 880,
              maxHeight: 640,
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _SettingsSidebar(
                  activeSection: _activeSection,
                  isAdmin: isAdmin,
                  onSelectSection: (section) =>
                      setState(() => _activeSection = section),
                ),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Expanded(
                        child: SingleChildScrollView(
                          padding: const EdgeInsets.fromLTRB(28, 24, 28, 20),
                          child: switch (_activeSection) {
                            SettingsSection.general => GeneralSettingsPanel(
                                session: widget.session,
                                activeThemeName:
                                    widget.themeController.activeTheme.name,
                              ),
                            SettingsSection.themes => _ThemesSectionContent(
                                themeController: widget.themeController,
                                onCreateTheme: () => _openCreateTheme(context),
                              ),
                            SettingsSection.accessibility =>
                              _AccessibilitySectionContent(
                                themeController: widget.themeController,
                              ),
                            SettingsSection.admin => AdminSettingsPanel(
                                session: widget.session,
                              ),
                          },
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 24,
                          vertical: 12,
                        ),
                        decoration: BoxDecoration(
                          border: Border(
                            top: BorderSide(color: spec.borderColor),
                          ),
                        ),
                        child: Align(
                          alignment: Alignment.centerRight,
                          child: TextButton(
                            onPressed: () => Navigator.of(context).pop(),
                            child: Text(
                              context.l10n.settingsClose,
                              style: TextStyle(
                                color: spec.accentColor,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _SettingsSidebar extends StatelessWidget {
  const _SettingsSidebar({
    required this.activeSection,
    required this.isAdmin,
    required this.onSelectSection,
  });

  final SettingsSection activeSection;
  final bool isAdmin;
  final ValueChanged<SettingsSection> onSelectSection;

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;
    final l10n = context.l10n;

    return Container(
      width: 242,
      decoration: BoxDecoration(
        color: spec.headerColor.withValues(alpha: 0.65),
        border: Border(
          right: BorderSide(color: spec.borderColor),
        ),
      ),
      padding: const EdgeInsets.fromLTRB(14, 20, 14, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(7),
                  decoration: BoxDecoration(
                    color: spec.accentColor.withValues(alpha: 0.16),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(
                    Icons.tune_rounded,
                    size: 18,
                    color: spec.accentColor,
                  ),
                ),
                const SizedBox(width: 10),
                Text(
                  l10n.settingsTitle,
                  style: TextStyle(
                    color: spec.textColor,
                    fontSize: 17,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          _SettingsNavTile(
            icon: Icons.person_outline_rounded,
            badgeColor: const Color(0xFF38BDF8),
            label: l10n.settingsNavGeneralTitle,
            subtitle: l10n.settingsNavGeneralSub,
            isSelected: activeSection == SettingsSection.general,
            onTap: () => onSelectSection(SettingsSection.general),
          ),
          const SizedBox(height: 8),
          _SettingsNavTile(
            icon: Icons.palette_outlined,
            badgeColor: const Color(0xFFF59E0B),
            label: l10n.settingsNavThemesTitle,
            subtitle: l10n.settingsNavThemesSub,
            isSelected: activeSection == SettingsSection.themes,
            onTap: () => onSelectSection(SettingsSection.themes),
          ),
          const SizedBox(height: 8),
          _SettingsNavTile(
            icon: Icons.visibility_outlined,
            badgeColor: const Color(0xFF10B981),
            label: l10n.settingsNavA11yTitle,
            subtitle: l10n.settingsNavA11ySub,
            isSelected: activeSection == SettingsSection.accessibility,
            onTap: () => onSelectSection(SettingsSection.accessibility),
          ),
          if (isAdmin) ...[
            const SizedBox(height: 16),
            Divider(color: spec.borderColor, height: 1),
            const SizedBox(height: 14),
            _SettingsNavTile(
              icon: Icons.shield_outlined,
              badgeColor: const Color(0xFFA855F7),
              label: l10n.settingsNavAdminTitle,
              subtitle: l10n.settingsNavAdminSub,
              isSelected: activeSection == SettingsSection.admin,
              onTap: () => onSelectSection(SettingsSection.admin),
            ),
          ],
          const Spacer(),
        ],
      ),
    );
  }
}

class _SettingsNavTile extends StatelessWidget {
  const _SettingsNavTile({
    required this.icon,
    required this.badgeColor,
    required this.label,
    required this.subtitle,
    required this.isSelected,
    required this.onTap,
  });

  final IconData icon;
  final Color badgeColor;
  final String label;
  final String subtitle;
  final bool isSelected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(14),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 10),
        decoration: BoxDecoration(
          color: isSelected
              ? spec.accentColor.withValues(alpha: 0.16)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: isSelected
                ? spec.accentColor.withValues(alpha: 0.5)
                : Colors.transparent,
          ),
        ),
        child: Row(
          children: [
            Container(
              width: 34,
              height: 34,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: badgeColor.withValues(alpha: isSelected ? 0.22 : 0.13),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(
                icon,
                size: 18,
                color: badgeColor,
              ),
            ),
            const SizedBox(width: 11),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    style: TextStyle(
                      color: isSelected ? spec.textColor : spec.textColor.withValues(alpha: 0.88),
                      fontSize: 13.5,
                      fontWeight: isSelected ? FontWeight.w700 : FontWeight.w600,
                    ),
                  ),
                  Text(
                    subtitle,
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
          ],
        ),
      ),
    );
  }
}

class _ThemesSectionContent extends StatelessWidget {
  const _ThemesSectionContent({
    required this.themeController,
    required this.onCreateTheme,
  });

  final ThemeController themeController;
  final VoidCallback onCreateTheme;

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;
    final l10n = context.l10n;
    final activeId = themeController.activeTheme.id;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.themesSectionTitle,
          style: TextStyle(
            color: spec.textColor,
            fontSize: 21,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          l10n.themesSectionSubtitle,
          style: TextStyle(
            color: spec.subtextColor,
            fontSize: 13,
          ),
        ),
        const SizedBox(height: 22),
        Text(
          l10n.themesSystemHeader,
          style: TextStyle(
            color: spec.textColor,
            fontSize: 13,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 12),
        GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: themeController.systemThemes.length,
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 3,
            crossAxisSpacing: 14,
            mainAxisSpacing: 14,
            childAspectRatio: 1.24,
          ),
          itemBuilder: (context, index) {
            final item = themeController.systemThemes[index];
            return ThemePreviewCard(
              spec: item,
              isSelected: item.id == activeId,
              onTap: () => themeController.selectTheme(item),
            );
          },
        ),
        const SizedBox(height: 26),
        Text(
          l10n.themesCustomHeader,
          style: TextStyle(
            color: spec.textColor,
            fontSize: 13,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 12),
        if (themeController.customThemes.isNotEmpty) ...[
          GridView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: themeController.customThemes.length,
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 3,
              crossAxisSpacing: 14,
              mainAxisSpacing: 14,
              childAspectRatio: 1.24,
            ),
            itemBuilder: (context, index) {
              final item = themeController.customThemes[index];
              return ThemePreviewCard(
                spec: item,
                isSelected: item.id == activeId,
                onTap: () => themeController.selectTheme(item),
                onDelete: () => themeController.deleteCustomTheme(item.id),
              );
            },
          ),
          const SizedBox(height: 14),
        ],
        SizedBox(
          width: double.infinity,
          height: 44,
          child: OutlinedButton.icon(
            style: OutlinedButton.styleFrom(
              foregroundColor: spec.accentColor,
              side: BorderSide(
                color: spec.accentColor.withValues(alpha: 0.55),
              ),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(10),
              ),
            ),
            onPressed: onCreateTheme,
            icon: const Icon(Icons.add_rounded, size: 18),
            label: Text(
              l10n.themesCreateButton,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ),
        ),
      ],
    );
  }
}

class _AccessibilitySectionContent extends StatelessWidget {
  const _AccessibilitySectionContent({
    required this.themeController,
  });

  final ThemeController themeController;

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;
    final l10n = context.l10n;
    final activeId = themeController.activeTheme.id;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.a11ySectionTitle,
          style: TextStyle(
            color: spec.textColor,
            fontSize: 21,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          l10n.a11ySectionSubtitle,
          style: TextStyle(
            color: spec.subtextColor,
            fontSize: 13,
          ),
        ),
        const SizedBox(height: 22),
        Text(
          l10n.a11yModesHeader,
          style: TextStyle(
            color: spec.textColor,
            fontSize: 13,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 12),
        GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: themeController.accessibilityThemes.length,
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: 2,
            crossAxisSpacing: 14,
            mainAxisSpacing: 14,
            childAspectRatio: 1.75,
          ),
          itemBuilder: (context, index) {
            final item = themeController.accessibilityThemes[index];
            return ThemePreviewCard(
              spec: item,
              isSelected: item.id == activeId,
              onTap: () => themeController.selectTheme(item),
            );
          },
        ),
      ],
    );
  }
}
