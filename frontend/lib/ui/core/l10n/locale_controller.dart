import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../../l10n/app_localizations.dart';

class LocaleController extends ChangeNotifier {
  static const String _storageKey = 'ratatosk_locale';
  static const List<Locale> supportedLocales = [
    Locale('en'),
    Locale('fr'),
  ];

  // English is the default application language
  Locale _locale = const Locale('en');
  Locale get locale => _locale;

  Future<void> initialize() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final savedCode = prefs.getString(_storageKey);
      if (savedCode != null &&
          supportedLocales.any((l) => l.languageCode == savedCode)) {
        _locale = Locale(savedCode);
      }
    } catch (_) {}
  }

  Future<void> setLocale(Locale newLocale) async {
    if (!supportedLocales.any((l) => l.languageCode == newLocale.languageCode)) {
      return;
    }
    if (_locale.languageCode == newLocale.languageCode) return;
    _locale = Locale(newLocale.languageCode);
    notifyListeners();
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_storageKey, _locale.languageCode);
    } catch (_) {}
  }
}

class LocaleControllerScope extends InheritedNotifier<LocaleController> {
  const LocaleControllerScope({
    super.key,
    required LocaleController controller,
    required super.child,
  }) : super(notifier: controller);

  static LocaleController? maybeOf(BuildContext context) {
    return context
        .dependOnInheritedWidgetOfExactType<LocaleControllerScope>()
        ?.notifier;
  }
}

extension AppL10nContext on BuildContext {
  AppLocalizations get l10n => AppLocalizations.of(this)!;
}
