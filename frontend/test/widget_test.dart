import 'dart:ui';

import 'package:flutter_test/flutter_test.dart';
import 'package:ratatosk_frontend/domain/models/app_theme_spec.dart';
import 'package:ratatosk_frontend/main.dart';
import 'package:ratatosk_frontend/ui/core/l10n/locale_controller.dart';
import 'package:ratatosk_frontend/ui/core/theme/theme_controller.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  testWidgets(
      'RatatoskApp defaults to English, switches to French, and switches themes',
      (WidgetTester tester) async {
    SharedPreferences.setMockInitialValues({});
    final themeController = ThemeController();
    final localeController = LocaleController();
    await themeController.initialize();
    await localeController.initialize();

    expect(themeController.activeTheme.id, 'nidhogg');
    expect(localeController.locale.languageCode, 'en');
    expect(AppThemeSpec.builtInSystemThemes.length, 6);
    expect(AppThemeSpec.builtInAccessibilityThemes.length, 4);

    await tester.pumpWidget(
      RatatoskApp(
        themeController: themeController,
        localeController: localeController,
      ),
    );
    await tester.pumpAndSettle();

    // Default English UI
    expect(find.text('Ratatosk'), findsWidgets);
    expect(find.text('Sign in'), findsOneWidget);

    // Switch to French
    await localeController.setLocale(const Locale('fr'));
    await tester.pumpAndSettle();
    expect(find.text('Se connecter'), findsOneWidget);

    // Switch theme
    await themeController.selectTheme(
      AppThemeSpec.builtInSystemThemes.firstWhere((t) => t.id == 'yggdrasil'),
    );
    await tester.pumpAndSettle();
    expect(themeController.activeTheme.id, 'yggdrasil');
  });
}
