import 'package:flutter/material.dart';

import '../../../data/services/theme_storage_service.dart';
import '../../../domain/models/app_theme_spec.dart';

class ThemeController extends ChangeNotifier {
  ThemeController({ThemeStorageService? storageService})
      : _storage = storageService ?? ThemeStorageService();

  final ThemeStorageService _storage;

  final List<AppThemeSpec> _customThemes = [];
  AppThemeSpec _activeTheme = AppThemeSpec.builtInSystemThemes.last; // Nidhogg

  AppThemeSpec get activeTheme => _activeTheme;
  List<AppThemeSpec> get systemThemes => AppThemeSpec.builtInSystemThemes;
  List<AppThemeSpec> get accessibilityThemes =>
      AppThemeSpec.builtInAccessibilityThemes;
  List<AppThemeSpec> get customThemes => List.unmodifiable(_customThemes);

  List<AppThemeSpec> get allThemes => [
        ...systemThemes,
        ...accessibilityThemes,
        ..._customThemes,
      ];

  Future<void> initialize() async {
    final savedCustom = await _storage.loadCustomThemes();
    _customThemes
      ..clear()
      ..addAll(savedCustom);

    final savedId = await _storage.loadActiveThemeId();
    if (savedId != null) {
      final match = allThemes.where((t) => t.id == savedId).firstOrNull;
      if (match != null) {
        _activeTheme = match;
      }
    }
    notifyListeners();
  }

  Future<void> selectTheme(AppThemeSpec theme) async {
    _activeTheme = theme;
    notifyListeners();
    await _storage.saveActiveThemeId(theme.id);
  }

  Future<void> addCustomTheme(AppThemeSpec customTheme) async {
    _customThemes.removeWhere((t) => t.id == customTheme.id);
    _customThemes.add(customTheme);
    _activeTheme = customTheme;
    notifyListeners();
    await _storage.saveCustomThemes(_customThemes);
    await _storage.saveActiveThemeId(customTheme.id);
  }

  Future<void> deleteCustomTheme(String themeId) async {
    _customThemes.removeWhere((t) => t.id == themeId);
    if (_activeTheme.id == themeId) {
      _activeTheme = AppThemeSpec.builtInSystemThemes.last;
      await _storage.saveActiveThemeId(_activeTheme.id);
    }
    notifyListeners();
    await _storage.saveCustomThemes(_customThemes);
  }
}
