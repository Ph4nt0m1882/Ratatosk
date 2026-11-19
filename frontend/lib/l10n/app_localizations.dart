import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_fr.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations? of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations);
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('fr'),
  ];

  /// No description provided for @appTitle.
  ///
  /// In en, this message translates to:
  /// **'Ratatosk'**
  String get appTitle;

  /// No description provided for @loginTagline.
  ///
  /// In en, this message translates to:
  /// **'Unified AI orchestrator on Yggdrasil'**
  String get loginTagline;

  /// No description provided for @loginServerLabel.
  ///
  /// In en, this message translates to:
  /// **'Ratatosk Server'**
  String get loginServerLabel;

  /// No description provided for @loginUsernameLabel.
  ///
  /// In en, this message translates to:
  /// **'Username'**
  String get loginUsernameLabel;

  /// No description provided for @loginPasswordLabel.
  ///
  /// In en, this message translates to:
  /// **'Password'**
  String get loginPasswordLabel;

  /// No description provided for @loginSubmitButton.
  ///
  /// In en, this message translates to:
  /// **'Sign in'**
  String get loginSubmitButton;

  /// No description provided for @loginOfflinePreview.
  ///
  /// In en, this message translates to:
  /// **'Explore interface offline'**
  String get loginOfflinePreview;

  /// No description provided for @themeButtonLabel.
  ///
  /// In en, this message translates to:
  /// **'Theme: {themeName}'**
  String themeButtonLabel(String themeName);

  /// No description provided for @languageLabel.
  ///
  /// In en, this message translates to:
  /// **'Language'**
  String get languageLabel;

  /// No description provided for @languageEnglish.
  ///
  /// In en, this message translates to:
  /// **'English'**
  String get languageEnglish;

  /// No description provided for @languageFrench.
  ///
  /// In en, this message translates to:
  /// **'Français'**
  String get languageFrench;

  /// No description provided for @sidebarSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Chat notebook'**
  String get sidebarSubtitle;

  /// No description provided for @sidebarCollapseTooltip.
  ///
  /// In en, this message translates to:
  /// **'Collapse notebook'**
  String get sidebarCollapseTooltip;

  /// No description provided for @sidebarNewChat.
  ///
  /// In en, this message translates to:
  /// **'New chat'**
  String get sidebarNewChat;

  /// No description provided for @sidebarMyChats.
  ///
  /// In en, this message translates to:
  /// **'My chats'**
  String get sidebarMyChats;

  /// No description provided for @sidebarEmptyChats.
  ///
  /// In en, this message translates to:
  /// **'No stories yet.\nAsk your first question!'**
  String get sidebarEmptyChats;

  /// No description provided for @sidebarRoleAdmin.
  ///
  /// In en, this message translates to:
  /// **'Guardian (Admin)'**
  String get sidebarRoleAdmin;

  /// No description provided for @sidebarRoleMember.
  ///
  /// In en, this message translates to:
  /// **'Explorer'**
  String get sidebarRoleMember;

  /// No description provided for @sidebarOpenSettings.
  ///
  /// In en, this message translates to:
  /// **'Open settings'**
  String get sidebarOpenSettings;

  /// No description provided for @sidebarLogout.
  ///
  /// In en, this message translates to:
  /// **'Sign out'**
  String get sidebarLogout;

  /// No description provided for @topBarOpenChats.
  ///
  /// In en, this message translates to:
  /// **'Chats'**
  String get topBarOpenChats;

  /// No description provided for @topBarOpenChatsTooltip.
  ///
  /// In en, this message translates to:
  /// **'Open chat notebook'**
  String get topBarOpenChatsTooltip;

  /// No description provided for @topBarThemeTooltip.
  ///
  /// In en, this message translates to:
  /// **'Change colors ({themeName})'**
  String topBarThemeTooltip(String themeName);

  /// No description provided for @topBarSettingsTooltip.
  ///
  /// In en, this message translates to:
  /// **'Settings'**
  String get topBarSettingsTooltip;

  /// No description provided for @welcomeMorning.
  ///
  /// In en, this message translates to:
  /// **'Good morning, {name}!'**
  String welcomeMorning(String name);

  /// No description provided for @welcomeAfternoon.
  ///
  /// In en, this message translates to:
  /// **'Good afternoon, {name}!'**
  String welcomeAfternoon(String name);

  /// No description provided for @welcomeEvening.
  ///
  /// In en, this message translates to:
  /// **'Good evening, {name}!'**
  String welcomeEvening(String name);

  /// No description provided for @welcomeSubtitle.
  ///
  /// In en, this message translates to:
  /// **'What shall we discover, invent, or create today?'**
  String get welcomeSubtitle;

  /// No description provided for @hubComingSoon.
  ///
  /// In en, this message translates to:
  /// **'{modeName} — Coming soon ({details})'**
  String hubComingSoon(String modeName, String details);

  /// No description provided for @hubDrawTitle.
  ///
  /// In en, this message translates to:
  /// **'Imagine a drawing'**
  String get hubDrawTitle;

  /// No description provided for @hubDrawSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Dedicated studio for image creation, retouching, and manipulation'**
  String get hubDrawSubtitle;

  /// No description provided for @hubDrawDetails.
  ///
  /// In en, this message translates to:
  /// **'Image editor & studio'**
  String get hubDrawDetails;

  /// No description provided for @hubExploreTitle.
  ///
  /// In en, this message translates to:
  /// **'Explore the world'**
  String get hubExploreTitle;

  /// No description provided for @hubExploreSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Interactive news map, research, and passion feed'**
  String get hubExploreSubtitle;

  /// No description provided for @hubExploreDetails.
  ///
  /// In en, this message translates to:
  /// **'World news map, research & passions'**
  String get hubExploreDetails;

  /// No description provided for @hubLearnTitle.
  ///
  /// In en, this message translates to:
  /// **'Learn & Write'**
  String get hubLearnTitle;

  /// No description provided for @hubLearnSubtitle.
  ///
  /// In en, this message translates to:
  /// **'NotebookLM-style studio: courses, emails, stories, and recipes'**
  String get hubLearnSubtitle;

  /// No description provided for @hubLearnDetails.
  ///
  /// In en, this message translates to:
  /// **'Source notebooks, learning & writing'**
  String get hubLearnDetails;

  /// No description provided for @hubPlayTitle.
  ///
  /// In en, this message translates to:
  /// **'Play'**
  String get hubPlayTitle;

  /// No description provided for @hubPlaySubtitle.
  ///
  /// In en, this message translates to:
  /// **'AI Tamagotchi, procedural dungeons, and Layton-style riddles'**
  String get hubPlaySubtitle;

  /// No description provided for @hubPlayDetails.
  ///
  /// In en, this message translates to:
  /// **'AI Tamagotchi, Mystery Dungeon & Riddles'**
  String get hubPlayDetails;

  /// No description provided for @welcomeResumeSection.
  ///
  /// In en, this message translates to:
  /// **'Pick up where you left off'**
  String get welcomeResumeSection;

  /// No description provided for @composerHint.
  ///
  /// In en, this message translates to:
  /// **'Write a message, ask a question, or request a drawing...'**
  String get composerHint;

  /// No description provided for @composerAttach.
  ///
  /// In en, this message translates to:
  /// **'Attach'**
  String get composerAttach;

  /// No description provided for @composerAttachTooltip.
  ///
  /// In en, this message translates to:
  /// **'Attach an image or file'**
  String get composerAttachTooltip;

  /// No description provided for @composerSend.
  ///
  /// In en, this message translates to:
  /// **'Send'**
  String get composerSend;

  /// No description provided for @composerSending.
  ///
  /// In en, this message translates to:
  /// **'Working...'**
  String get composerSending;

  /// No description provided for @composerChangeModelTooltip.
  ///
  /// In en, this message translates to:
  /// **'Change model for this message'**
  String get composerChangeModelTooltip;

  /// No description provided for @composerWebTooltip.
  ///
  /// In en, this message translates to:
  /// **'Choose web search mode'**
  String get composerWebTooltip;

  /// No description provided for @webOffTitle.
  ///
  /// In en, this message translates to:
  /// **'Offline'**
  String get webOffTitle;

  /// No description provided for @webOffDesc.
  ///
  /// In en, this message translates to:
  /// **'Answers using internal knowledge only'**
  String get webOffDesc;

  /// No description provided for @webStandardTitle.
  ///
  /// In en, this message translates to:
  /// **'Internet'**
  String get webStandardTitle;

  /// No description provided for @webStandardDesc.
  ///
  /// In en, this message translates to:
  /// **'Searches the web when needed'**
  String get webStandardDesc;

  /// No description provided for @webDeepTitle.
  ///
  /// In en, this message translates to:
  /// **'Deep Web'**
  String get webDeepTitle;

  /// No description provided for @webDeepDesc.
  ///
  /// In en, this message translates to:
  /// **'Explores and cross-checks multiple sources'**
  String get webDeepDesc;

  /// No description provided for @composerMemoryTooltip.
  ///
  /// In en, this message translates to:
  /// **'Choose conversation memory'**
  String get composerMemoryTooltip;

  /// No description provided for @memEcoTitle.
  ///
  /// In en, this message translates to:
  /// **'Eco Memory'**
  String get memEcoTitle;

  /// No description provided for @memEcoDesc.
  ///
  /// In en, this message translates to:
  /// **'Keeps key context efficiently (recommended)'**
  String get memEcoDesc;

  /// No description provided for @memAutoTitle.
  ///
  /// In en, this message translates to:
  /// **'Auto Memory'**
  String get memAutoTitle;

  /// No description provided for @memAutoDesc.
  ///
  /// In en, this message translates to:
  /// **'Automatically adapts history to your prompt'**
  String get memAutoDesc;

  /// No description provided for @memFullTitle.
  ///
  /// In en, this message translates to:
  /// **'Full Memory'**
  String get memFullTitle;

  /// No description provided for @memFullDesc.
  ///
  /// In en, this message translates to:
  /// **'Reads the entire conversation history'**
  String get memFullDesc;

  /// No description provided for @memFixedTitle.
  ///
  /// In en, this message translates to:
  /// **'Short Memory'**
  String get memFixedTitle;

  /// No description provided for @memFixedDesc.
  ///
  /// In en, this message translates to:
  /// **'Only keeps the most recent messages'**
  String get memFixedDesc;

  /// No description provided for @memNoneTitle.
  ///
  /// In en, this message translates to:
  /// **'No Memory'**
  String get memNoneTitle;

  /// No description provided for @memNoneDesc.
  ///
  /// In en, this message translates to:
  /// **'Every message starts from a blank slate'**
  String get memNoneDesc;

  /// No description provided for @msgInternalThinking.
  ///
  /// In en, this message translates to:
  /// **'Internal reasoning'**
  String get msgInternalThinking;

  /// No description provided for @msgCopyCode.
  ///
  /// In en, this message translates to:
  /// **'Copy'**
  String get msgCopyCode;

  /// No description provided for @msgCopiedCode.
  ///
  /// In en, this message translates to:
  /// **'Copied'**
  String get msgCopiedCode;

  /// No description provided for @msgDownloadTooltip.
  ///
  /// In en, this message translates to:
  /// **'Download'**
  String get msgDownloadTooltip;

  /// No description provided for @modelSelectorTitle.
  ///
  /// In en, this message translates to:
  /// **'Select a model'**
  String get modelSelectorTitle;

  /// No description provided for @modelSelectorRefreshTooltip.
  ///
  /// In en, this message translates to:
  /// **'Refresh from GitHub registry'**
  String get modelSelectorRefreshTooltip;

  /// No description provided for @modelSelectorSearchHint.
  ///
  /// In en, this message translates to:
  /// **'Search a model (Argon, Carbon, Hydrogen, Gemma...)'**
  String get modelSelectorSearchHint;

  /// No description provided for @modelSelectorEmptySearch.
  ///
  /// In en, this message translates to:
  /// **'No model matches \"{query}\".'**
  String modelSelectorEmptySearch(String query);

  /// No description provided for @modelSelectorFavorites.
  ///
  /// In en, this message translates to:
  /// **'Favorites ({count})'**
  String modelSelectorFavorites(int count);

  /// No description provided for @modelSelectorCount.
  ///
  /// In en, this message translates to:
  /// **'{count} models'**
  String modelSelectorCount(int count);

  /// No description provided for @modelSelectorRecommendedSection.
  ///
  /// In en, this message translates to:
  /// **'Recommended models'**
  String get modelSelectorRecommendedSection;

  /// No description provided for @modelSelectorAllModels.
  ///
  /// In en, this message translates to:
  /// **'All models ({count})'**
  String modelSelectorAllModels(int count);

  /// No description provided for @modelSelectorRecommendedBadge.
  ///
  /// In en, this message translates to:
  /// **'Recommended'**
  String get modelSelectorRecommendedBadge;

  /// No description provided for @modelSelectorFreeLocal.
  ///
  /// In en, this message translates to:
  /// **'Free / Local'**
  String get modelSelectorFreeLocal;

  /// No description provided for @modelSelectorAddFav.
  ///
  /// In en, this message translates to:
  /// **'Add to favorites'**
  String get modelSelectorAddFav;

  /// No description provided for @modelSelectorRemoveFav.
  ///
  /// In en, this message translates to:
  /// **'Remove from favorites'**
  String get modelSelectorRemoveFav;

  /// No description provided for @settingsTitle.
  ///
  /// In en, this message translates to:
  /// **'Settings'**
  String get settingsTitle;

  /// No description provided for @settingsClose.
  ///
  /// In en, this message translates to:
  /// **'Close'**
  String get settingsClose;

  /// No description provided for @settingsNavGeneralTitle.
  ///
  /// In en, this message translates to:
  /// **'My Space'**
  String get settingsNavGeneralTitle;

  /// No description provided for @settingsNavGeneralSub.
  ///
  /// In en, this message translates to:
  /// **'Profile, language & tools'**
  String get settingsNavGeneralSub;

  /// No description provided for @settingsNavThemesTitle.
  ///
  /// In en, this message translates to:
  /// **'Colors & Themes'**
  String get settingsNavThemesTitle;

  /// No description provided for @settingsNavThemesSub.
  ///
  /// In en, this message translates to:
  /// **'Change visual mood'**
  String get settingsNavThemesSub;

  /// No description provided for @settingsNavA11yTitle.
  ///
  /// In en, this message translates to:
  /// **'Visual Comfort'**
  String get settingsNavA11yTitle;

  /// No description provided for @settingsNavA11ySub.
  ///
  /// In en, this message translates to:
  /// **'Colorblindness & contrast'**
  String get settingsNavA11ySub;

  /// No description provided for @settingsNavAdminTitle.
  ///
  /// In en, this message translates to:
  /// **'Administration'**
  String get settingsNavAdminTitle;

  /// No description provided for @settingsNavAdminSub.
  ///
  /// In en, this message translates to:
  /// **'Server & System Prompts'**
  String get settingsNavAdminSub;

  /// No description provided for @themesSectionTitle.
  ///
  /// In en, this message translates to:
  /// **'Appearance Settings'**
  String get themesSectionTitle;

  /// No description provided for @themesSectionSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Choose the application theme. \"HC\" themes provide high contrast.'**
  String get themesSectionSubtitle;

  /// No description provided for @themesSystemHeader.
  ///
  /// In en, this message translates to:
  /// **'System Themes'**
  String get themesSystemHeader;

  /// No description provided for @themesCustomHeader.
  ///
  /// In en, this message translates to:
  /// **'Custom Themes'**
  String get themesCustomHeader;

  /// No description provided for @themesCreateButton.
  ///
  /// In en, this message translates to:
  /// **'Create a theme'**
  String get themesCreateButton;

  /// No description provided for @a11ySectionTitle.
  ///
  /// In en, this message translates to:
  /// **'Accessibility & Colorblindness'**
  String get a11ySectionTitle;

  /// No description provided for @a11ySectionSubtitle.
  ///
  /// In en, this message translates to:
  /// **'High-legibility palettes calibrated for protanopia, deuteranopia, tritanopia, and achromatopsia.'**
  String get a11ySectionSubtitle;

  /// No description provided for @a11yModesHeader.
  ///
  /// In en, this message translates to:
  /// **'Accessibility Themes (4 modes)'**
  String get a11yModesHeader;

  /// No description provided for @generalSectionTitle.
  ///
  /// In en, this message translates to:
  /// **'General Settings'**
  String get generalSectionTitle;

  /// No description provided for @generalSectionSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Manage your language, profile, and personal MCP tool servers.'**
  String get generalSectionSubtitle;

  /// No description provided for @generalAccountHeader.
  ///
  /// In en, this message translates to:
  /// **'My Account'**
  String get generalAccountHeader;

  /// No description provided for @generalConnectedUser.
  ///
  /// In en, this message translates to:
  /// **'Signed in as'**
  String get generalConnectedUser;

  /// No description provided for @generalRoleLabel.
  ///
  /// In en, this message translates to:
  /// **'Role'**
  String get generalRoleLabel;

  /// No description provided for @generalRoleAdmin.
  ///
  /// In en, this message translates to:
  /// **'Administrator'**
  String get generalRoleAdmin;

  /// No description provided for @generalRoleStandard.
  ///
  /// In en, this message translates to:
  /// **'Standard user'**
  String get generalRoleStandard;

  /// No description provided for @generalBackendServer.
  ///
  /// In en, this message translates to:
  /// **'Backend server'**
  String get generalBackendServer;

  /// No description provided for @generalActiveTheme.
  ///
  /// In en, this message translates to:
  /// **'Active theme'**
  String get generalActiveTheme;

  /// No description provided for @generalUsernameField.
  ///
  /// In en, this message translates to:
  /// **'Username'**
  String get generalUsernameField;

  /// No description provided for @generalEmailField.
  ///
  /// In en, this message translates to:
  /// **'Email (optional)'**
  String get generalEmailField;

  /// No description provided for @generalPasswordField.
  ///
  /// In en, this message translates to:
  /// **'New password (leave blank to keep)'**
  String get generalPasswordField;

  /// No description provided for @generalUpdateButton.
  ///
  /// In en, this message translates to:
  /// **'Update'**
  String get generalUpdateButton;

  /// No description provided for @generalProfileUpdated.
  ///
  /// In en, this message translates to:
  /// **'Profile updated successfully.'**
  String get generalProfileUpdated;

  /// No description provided for @generalMcpHeader.
  ///
  /// In en, this message translates to:
  /// **'MCP Servers ({count})'**
  String generalMcpHeader(int count);

  /// No description provided for @generalMcpImportJson.
  ///
  /// In en, this message translates to:
  /// **'Import JSON'**
  String get generalMcpImportJson;

  /// No description provided for @generalMcpAdd.
  ///
  /// In en, this message translates to:
  /// **'Add'**
  String get generalMcpAdd;

  /// No description provided for @generalMcpEmpty.
  ///
  /// In en, this message translates to:
  /// **'No MCP server configured. Add a server or import a JSON config to extend available tools.'**
  String get generalMcpEmpty;

  /// No description provided for @adminRestricted.
  ///
  /// In en, this message translates to:
  /// **'Restricted to administrators.'**
  String get adminRestricted;

  /// No description provided for @adminSectionTitle.
  ///
  /// In en, this message translates to:
  /// **'Administration'**
  String get adminSectionTitle;

  /// No description provided for @adminSectionSubtitle.
  ///
  /// In en, this message translates to:
  /// **'System Prompts management (admin only), server settings, users, and global MCP.'**
  String get adminSectionSubtitle;

  /// No description provided for @adminTabPrompts.
  ///
  /// In en, this message translates to:
  /// **'System Prompts ({count})'**
  String adminTabPrompts(int count);

  /// No description provided for @adminTabServer.
  ///
  /// In en, this message translates to:
  /// **'Server Settings'**
  String get adminTabServer;

  /// No description provided for @adminTabUsers.
  ///
  /// In en, this message translates to:
  /// **'Users ({count})'**
  String adminTabUsers(int count);

  /// No description provided for @adminTabGlobalMcp.
  ///
  /// In en, this message translates to:
  /// **'Global MCP ({count})'**
  String adminTabGlobalMcp(int count);

  /// No description provided for @commonCancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get commonCancel;

  /// No description provided for @commonSave.
  ///
  /// In en, this message translates to:
  /// **'Save'**
  String get commonSave;

  /// No description provided for @commonDelete.
  ///
  /// In en, this message translates to:
  /// **'Delete'**
  String get commonDelete;

  /// No description provided for @commonRefresh.
  ///
  /// In en, this message translates to:
  /// **'Refresh'**
  String get commonRefresh;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en', 'fr'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
    case 'fr':
      return AppLocalizationsFr();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
