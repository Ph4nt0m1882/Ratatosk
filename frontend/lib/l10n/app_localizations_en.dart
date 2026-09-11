// ignore: unused_import
import 'package:intl/intl.dart' as intl;

import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appName => 'Ratatosk';

  @override
  String get appTagline => 'Universal AI Orchestrator';

  @override
  String get settings => 'Settings';

  @override
  String get theme => 'Theme';

  @override
  String get darkTheme => 'Dark';

  @override
  String get lightTheme => 'Light';

  @override
  String get systemTheme => 'System';

  @override
  String get language => 'Language';

  @override
  String get chatTitle => 'Chat';

  @override
  String get typeMessage => 'Type a message...';

  @override
  String get send => 'Send';
}
