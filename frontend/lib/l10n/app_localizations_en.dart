// ignore: unused_import
import 'package:intl/intl.dart' as intl;

import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appTitle => 'Ratatosk';

  @override
  String get loginTagline => 'Unified AI orchestrator on Yggdrasil';

  @override
  String get loginServerLabel => 'Ratatosk Server';

  @override
  String get loginUsernameLabel => 'Username';

  @override
  String get loginPasswordLabel => 'Password';

  @override
  String get loginSubmitButton => 'Sign in';

  @override
  String get loginOfflinePreview => 'Explore interface offline';

  @override
  String themeButtonLabel(String themeName) {
    return 'Theme: $themeName';
  }

  @override
  String get languageLabel => 'Language';

  @override
  String get languageEnglish => 'English';

  @override
  String get languageFrench => 'Français';

  @override
  String get sidebarSubtitle => 'Chat notebook';

  @override
  String get sidebarCollapseTooltip => 'Collapse notebook';

  @override
  String get sidebarNewChat => 'New chat';

  @override
  String get sidebarMyChats => 'My chats';

  @override
  String get sidebarEmptyChats => 'No stories yet.\nAsk your first question!';

  @override
  String get sidebarRoleAdmin => 'Guardian (Admin)';

  @override
  String get sidebarRoleMember => 'Explorer';

  @override
  String get sidebarOpenSettings => 'Open settings';

  @override
  String get sidebarLogout => 'Sign out';

  @override
  String get topBarOpenChats => 'Chats';

  @override
  String get topBarOpenChatsTooltip => 'Open chat notebook';

  @override
  String topBarThemeTooltip(String themeName) {
    return 'Change colors ($themeName)';
  }

  @override
  String get topBarSettingsTooltip => 'Settings';

  @override
  String welcomeMorning(String name) {
    return 'Good morning, $name!';
  }

  @override
  String welcomeAfternoon(String name) {
    return 'Good afternoon, $name!';
  }

  @override
  String welcomeEvening(String name) {
    return 'Good evening, $name!';
  }

  @override
  String get welcomeSubtitle =>
      'What shall we discover, invent, or create today?';

  @override
  String hubComingSoon(String modeName, String details) {
    return '$modeName — Coming soon ($details)';
  }

  @override
  String get hubDrawTitle => 'Imagine a drawing';

  @override
  String get hubDrawSubtitle =>
      'Dedicated studio for image creation, retouching, and manipulation';

  @override
  String get hubDrawDetails => 'Image editor & studio';

  @override
  String get hubExploreTitle => 'Explore the world';

  @override
  String get hubExploreSubtitle =>
      'Interactive news map, research, and passion feed';

  @override
  String get hubExploreDetails => 'World news map, research & passions';

  @override
  String get hubLearnTitle => 'Learn & Write';

  @override
  String get hubLearnSubtitle =>
      'NotebookLM-style studio: courses, emails, stories, and recipes';

  @override
  String get hubLearnDetails => 'Source notebooks, learning & writing';

  @override
  String get hubPlayTitle => 'Play';

  @override
  String get hubPlaySubtitle =>
      'AI Tamagotchi, procedural dungeons, and Layton-style riddles';

  @override
  String get hubPlayDetails => 'AI Tamagotchi, Mystery Dungeon & Riddles';

  @override
  String get welcomeResumeSection => 'Pick up where you left off';

  @override
  String get composerHint =>
      'Write a message, ask a question, or request a drawing...';

  @override
  String get composerAttach => 'Attach';

  @override
  String get composerAttachTooltip => 'Attach an image or file';

  @override
  String get composerSend => 'Send';

  @override
  String get composerSending => 'Working...';

  @override
  String get composerChangeModelTooltip => 'Change model for this message';

  @override
  String get composerWebTooltip => 'Choose web search mode';

  @override
  String get webOffTitle => 'Offline';

  @override
  String get webOffDesc => 'Answers using internal knowledge only';

  @override
  String get webStandardTitle => 'Internet';

  @override
  String get webStandardDesc => 'Searches the web when needed';

  @override
  String get webDeepTitle => 'Deep Web';

  @override
  String get webDeepDesc => 'Explores and cross-checks multiple sources';

  @override
  String get composerMemoryTooltip => 'Choose conversation memory';

  @override
  String get memEcoTitle => 'Eco Memory';

  @override
  String get memEcoDesc => 'Keeps key context efficiently (recommended)';

  @override
  String get memAutoTitle => 'Auto Memory';

  @override
  String get memAutoDesc => 'Automatically adapts history to your prompt';

  @override
  String get memFullTitle => 'Full Memory';

  @override
  String get memFullDesc => 'Reads the entire conversation history';

  @override
  String get memFixedTitle => 'Short Memory';

  @override
  String get memFixedDesc => 'Only keeps the most recent messages';

  @override
  String get memNoneTitle => 'No Memory';

  @override
  String get memNoneDesc => 'Every message starts from a blank slate';

  @override
  String get msgInternalThinking => 'Internal reasoning';

  @override
  String get msgCopyCode => 'Copy';

  @override
  String get msgCopiedCode => 'Copied';

  @override
  String get msgDownloadTooltip => 'Download';

  @override
  String get modelSelectorTitle => 'Select a model';

  @override
  String get modelSelectorRefreshTooltip => 'Refresh from GitHub registry';

  @override
  String get modelSelectorSearchHint =>
      'Search a model (Argon, Carbon, Hydrogen, Gemma...)';

  @override
  String modelSelectorEmptySearch(String query) {
    return 'No model matches \"$query\".';
  }

  @override
  String modelSelectorFavorites(int count) {
    return 'Favorites ($count)';
  }

  @override
  String modelSelectorCount(int count) {
    return '$count models';
  }

  @override
  String get modelSelectorRecommendedSection => 'Recommended models';

  @override
  String modelSelectorAllModels(int count) {
    return 'All models ($count)';
  }

  @override
  String get modelSelectorRecommendedBadge => 'Recommended';

  @override
  String get modelSelectorFreeLocal => 'Free / Local';

  @override
  String get modelSelectorAddFav => 'Add to favorites';

  @override
  String get modelSelectorRemoveFav => 'Remove from favorites';

  @override
  String get settingsTitle => 'Settings';

  @override
  String get settingsClose => 'Close';

  @override
  String get settingsNavGeneralTitle => 'My Space';

  @override
  String get settingsNavGeneralSub => 'Profile, language & tools';

  @override
  String get settingsNavThemesTitle => 'Colors & Themes';

  @override
  String get settingsNavThemesSub => 'Change visual mood';

  @override
  String get settingsNavA11yTitle => 'Visual Comfort';

  @override
  String get settingsNavA11ySub => 'Colorblindness & contrast';

  @override
  String get settingsNavAdminTitle => 'Administration';

  @override
  String get settingsNavAdminSub => 'Server & System Prompts';

  @override
  String get themesSectionTitle => 'Appearance Settings';

  @override
  String get themesSectionSubtitle =>
      'Choose the application theme. \"HC\" themes provide high contrast.';

  @override
  String get themesSystemHeader => 'System Themes';

  @override
  String get themesCustomHeader => 'Custom Themes';

  @override
  String get themesCreateButton => 'Create a theme';

  @override
  String get a11ySectionTitle => 'Accessibility & Colorblindness';

  @override
  String get a11ySectionSubtitle =>
      'High-legibility palettes calibrated for protanopia, deuteranopia, tritanopia, and achromatopsia.';

  @override
  String get a11yModesHeader => 'Accessibility Themes (4 modes)';

  @override
  String get generalSectionTitle => 'General Settings';

  @override
  String get generalSectionSubtitle =>
      'Manage your language, profile, and personal MCP tool servers.';

  @override
  String get generalAccountHeader => 'My Account';

  @override
  String get generalConnectedUser => 'Signed in as';

  @override
  String get generalRoleLabel => 'Role';

  @override
  String get generalRoleAdmin => 'Administrator';

  @override
  String get generalRoleStandard => 'Standard user';

  @override
  String get generalBackendServer => 'Backend server';

  @override
  String get generalActiveTheme => 'Active theme';

  @override
  String get generalUsernameField => 'Username';

  @override
  String get generalEmailField => 'Email (optional)';

  @override
  String get generalPasswordField => 'New password (leave blank to keep)';

  @override
  String get generalUpdateButton => 'Update';

  @override
  String get generalProfileUpdated => 'Profile updated successfully.';

  @override
  String generalMcpHeader(int count) {
    return 'MCP Servers ($count)';
  }

  @override
  String get generalMcpImportJson => 'Import JSON';

  @override
  String get generalMcpAdd => 'Add';

  @override
  String get generalMcpEmpty =>
      'No MCP server configured. Add a server or import a JSON config to extend available tools.';

  @override
  String get adminRestricted => 'Restricted to administrators.';

  @override
  String get adminSectionTitle => 'Administration';

  @override
  String get adminSectionSubtitle =>
      'System Prompts management (admin only), server settings, users, and global MCP.';

  @override
  String adminTabPrompts(int count) {
    return 'System Prompts ($count)';
  }

  @override
  String get adminTabServer => 'Server Settings';

  @override
  String adminTabUsers(int count) {
    return 'Users ($count)';
  }

  @override
  String adminTabGlobalMcp(int count) {
    return 'Global MCP ($count)';
  }

  @override
  String get commonCancel => 'Cancel';

  @override
  String get commonSave => 'Save';

  @override
  String get commonDelete => 'Delete';

  @override
  String get commonRefresh => 'Refresh';
}
