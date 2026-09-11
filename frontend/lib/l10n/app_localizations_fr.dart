// ignore: unused_import
import 'package:intl/intl.dart' as intl;

import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for French (`fr`).
class AppLocalizationsFr extends AppLocalizations {
  AppLocalizationsFr([String locale = 'fr']) : super(locale);

  @override
  String get appName => 'Ratatosk';

  @override
  String get appTagline => 'Orchestrateur universel d\'IA';

  @override
  String get settings => 'Paramètres';

  @override
  String get theme => 'Thème';

  @override
  String get darkTheme => 'Sombre';

  @override
  String get lightTheme => 'Clair';

  @override
  String get systemTheme => 'Système';

  @override
  String get language => 'Langue';

  @override
  String get chatTitle => 'Discussion';

  @override
  String get typeMessage => 'Écrivez un message...';

  @override
  String get send => 'Envoyer';
}
