import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../../domain/models/app_theme_spec.dart';

class ThemeStorageService {
  static const String _activeThemeKey = 'ratatosk_active_theme_id';
  static const String _customThemesKey = 'ratatosk_custom_themes';

  Future<String?> loadActiveThemeId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_activeThemeKey);
  }

  Future<void> saveActiveThemeId(String themeId) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_activeThemeKey, themeId);
  }

  Future<List<AppThemeSpec>> loadCustomThemes() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getStringList(_customThemesKey) ?? const [];
    final List<AppThemeSpec> themes = [];
    for (final item in raw) {
      try {
        final decoded = jsonDecode(item) as Map<String, dynamic>;
        themes.add(AppThemeSpec.fromJson(decoded));
      } catch (_) {
        // Ignore malformed entries
      }
    }
    return themes;
  }

  Future<void> saveCustomThemes(List<AppThemeSpec> themes) async {
    final prefs = await SharedPreferences.getInstance();
    final encoded = themes.map((t) => jsonEncode(t.toJson())).toList();
    await prefs.setStringList(_customThemesKey, encoded);
  }
}
