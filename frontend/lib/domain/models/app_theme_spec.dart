import 'package:flutter/material.dart';

enum ThemeCategory {
  system,
  accessibility,
  custom,
}

class AppThemeSpec extends ThemeExtension<AppThemeSpec> {
  const AppThemeSpec({
    required this.id,
    required this.name,
    required this.category,
    required this.brightness,
    required this.backgroundColor,
    required this.surfaceColor,
    required this.headerColor,
    required this.textColor,
    required this.subtextColor,
    required this.accentColor,
    required this.borderColor,
    this.highContrastBorder = false,
    this.watermarkAsset,
    this.watermarkColor,
    this.watermarkOpacity = 0.08,
    this.subtitle,
  });

  final String id;
  final String name;
  final ThemeCategory category;
  final Brightness brightness;
  final Color backgroundColor;
  final Color surfaceColor;
  final Color headerColor;
  final Color textColor;
  final Color subtextColor;
  final Color accentColor;
  final Color borderColor;
  final bool highContrastBorder;
  final String? watermarkAsset;
  final Color? watermarkColor;
  final double watermarkOpacity;
  final String? subtitle;

  bool get isDark => brightness == Brightness.dark;

  ThemeData toThemeData() {
    final colorScheme = ColorScheme(
      brightness: brightness,
      primary: accentColor,
      onPrimary: accentColor.computeLuminance() > 0.5 ? Colors.black : Colors.white,
      secondary: accentColor,
      onSecondary: accentColor.computeLuminance() > 0.5 ? Colors.black : Colors.white,
      error: const Color(0xFFEF4444),
      onError: Colors.white,
      surface: surfaceColor,
      onSurface: textColor,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: brightness,
      scaffoldBackgroundColor: backgroundColor,
      colorScheme: colorScheme,
      dividerColor: borderColor,
      cardTheme: CardThemeData(
        color: surfaceColor,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: BorderSide(
            color: borderColor,
            width: highContrastBorder ? 2.0 : 1.0,
          ),
        ),
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: surfaceColor,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: BorderSide(color: borderColor),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: headerColor.withValues(alpha: 0.65),
        hintStyle: TextStyle(color: subtextColor, fontSize: 14),
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: BorderSide(color: borderColor),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: BorderSide(
            color: borderColor,
            width: highContrastBorder ? 1.8 : 1.0,
          ),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: BorderSide(color: accentColor, width: 2.0),
        ),
      ),
      extensions: <ThemeExtension<dynamic>>[this],
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'category': category.name,
        'brightness': brightness.name,
        'backgroundColor': backgroundColor.toARGB32(),
        'surfaceColor': surfaceColor.toARGB32(),
        'headerColor': headerColor.toARGB32(),
        'textColor': textColor.toARGB32(),
        'subtextColor': subtextColor.toARGB32(),
        'accentColor': accentColor.toARGB32(),
        'borderColor': borderColor.toARGB32(),
        'highContrastBorder': highContrastBorder,
        'watermarkAsset': watermarkAsset,
        'watermarkColor': watermarkColor?.toARGB32(),
        'watermarkOpacity': watermarkOpacity,
        'subtitle': subtitle,
      };

  factory AppThemeSpec.fromJson(Map<String, dynamic> json) {
    final isDarkMode = json['brightness'] == 'dark';
    return AppThemeSpec(
      id: json['id'] as String,
      name: json['name'] as String,
      category: ThemeCategory.values.firstWhere(
        (c) => c.name == json['category'],
        orElse: () => ThemeCategory.custom,
      ),
      brightness: isDarkMode ? Brightness.dark : Brightness.light,
      backgroundColor: Color(json['backgroundColor'] as int),
      surfaceColor: Color(json['surfaceColor'] as int),
      headerColor: Color(json['headerColor'] as int),
      textColor: Color(json['textColor'] as int),
      subtextColor: Color(json['subtextColor'] as int),
      accentColor: Color(json['accentColor'] as int),
      borderColor: Color(json['borderColor'] as int),
      highContrastBorder: (json['highContrastBorder'] as bool?) ?? false,
      watermarkAsset: json['watermarkAsset'] as String?,
      watermarkColor: json['watermarkColor'] != null
          ? Color(json['watermarkColor'] as int)
          : null,
      watermarkOpacity: ((json['watermarkOpacity'] as num?) ?? 0.08).toDouble(),
      subtitle: json['subtitle'] as String?,
    );
  }

  @override
  AppThemeSpec copyWith({
    String? id,
    String? name,
    ThemeCategory? category,
    Brightness? brightness,
    Color? backgroundColor,
    Color? surfaceColor,
    Color? headerColor,
    Color? textColor,
    Color? subtextColor,
    Color? accentColor,
    Color? borderColor,
    bool? highContrastBorder,
    String? watermarkAsset,
    Color? watermarkColor,
    double? watermarkOpacity,
    String? subtitle,
  }) {
    return AppThemeSpec(
      id: id ?? this.id,
      name: name ?? this.name,
      category: category ?? this.category,
      brightness: brightness ?? this.brightness,
      backgroundColor: backgroundColor ?? this.backgroundColor,
      surfaceColor: surfaceColor ?? this.surfaceColor,
      headerColor: headerColor ?? this.headerColor,
      textColor: textColor ?? this.textColor,
      subtextColor: subtextColor ?? this.subtextColor,
      accentColor: accentColor ?? this.accentColor,
      borderColor: borderColor ?? this.borderColor,
      highContrastBorder: highContrastBorder ?? this.highContrastBorder,
      watermarkAsset: watermarkAsset ?? this.watermarkAsset,
      watermarkColor: watermarkColor ?? this.watermarkColor,
      watermarkOpacity: watermarkOpacity ?? this.watermarkOpacity,
      subtitle: subtitle ?? this.subtitle,
    );
  }

  @override
  AppThemeSpec lerp(ThemeExtension<AppThemeSpec>? other, double t) {
    if (other is! AppThemeSpec) return this;
    return AppThemeSpec(
      id: t < 0.5 ? id : other.id,
      name: t < 0.5 ? name : other.name,
      category: t < 0.5 ? category : other.category,
      brightness: t < 0.5 ? brightness : other.brightness,
      backgroundColor: Color.lerp(backgroundColor, other.backgroundColor, t)!,
      surfaceColor: Color.lerp(surfaceColor, other.surfaceColor, t)!,
      headerColor: Color.lerp(headerColor, other.headerColor, t)!,
      textColor: Color.lerp(textColor, other.textColor, t)!,
      subtextColor: Color.lerp(subtextColor, other.subtextColor, t)!,
      accentColor: Color.lerp(accentColor, other.accentColor, t)!,
      borderColor: Color.lerp(borderColor, other.borderColor, t)!,
      highContrastBorder: t < 0.5 ? highContrastBorder : other.highContrastBorder,
      watermarkAsset: t < 0.5 ? watermarkAsset : other.watermarkAsset,
      watermarkColor: Color.lerp(watermarkColor, other.watermarkColor, t),
      watermarkOpacity:
          watermarkOpacity + (other.watermarkOpacity - watermarkOpacity) * t,
      subtitle: t < 0.5 ? subtitle : other.subtitle,
    );
  }

  static const List<AppThemeSpec> builtInSystemThemes = [
    // Row 1: Light, Light High Contrast, Yggdrasil (Fantasy Light)
    AppThemeSpec(
      id: 'light',
      name: 'Light',
      category: ThemeCategory.system,
      brightness: Brightness.light,
      backgroundColor: Color(0xFFF6F9FC),
      surfaceColor: Color(0xFFFFFFFF),
      headerColor: Color(0xFFEEF2F6),
      textColor: Color(0xFF0F172A),
      subtextColor: Color(0xFF64748B),
      accentColor: Color(0xFF0284C7),
      borderColor: Color(0xFFE2E8F0),
    ),
    AppThemeSpec(
      id: 'light_hc',
      name: 'Light High Contrast',
      category: ThemeCategory.system,
      brightness: Brightness.light,
      backgroundColor: Color(0xFFFFFFFF),
      surfaceColor: Color(0xFFFFFFFF),
      headerColor: Color(0xFFF1F5F9),
      textColor: Color(0xFF000000),
      subtextColor: Color(0xFF1E293B),
      accentColor: Color(0xFF0000FF),
      borderColor: Color(0xFF0000FF),
      highContrastBorder: true,
    ),
    AppThemeSpec(
      id: 'yggdrasil',
      name: 'Yggdrasil',
      category: ThemeCategory.system,
      brightness: Brightness.light,
      backgroundColor: Color(0xFFF2F7F1),
      surfaceColor: Color(0xFFF9FCF8),
      headerColor: Color(0xFFE4EFE2),
      textColor: Color(0xFF16291A),
      subtextColor: Color(0xFF4F6B54),
      accentColor: Color(0xFF2E7D32),
      borderColor: Color(0xFFD3E4D0),
      watermarkAsset: 'assets/images/yggdrasil.webp',
      watermarkColor: Color(0xFF2E5A35),
      watermarkOpacity: 0.055,
      subtitle: 'Arbre-Monde — Vert sauge très clair',
    ),
    // Row 2: Dark, Dark High Contrast, Nidhogg (Fantasy Dark)
    AppThemeSpec(
      id: 'dark',
      name: 'Dark',
      category: ThemeCategory.system,
      brightness: Brightness.dark,
      backgroundColor: Color(0xFF0B1526),
      surfaceColor: Color(0xFF132238),
      headerColor: Color(0xFF1D304B),
      textColor: Color(0xFFF1F5F9),
      subtextColor: Color(0xFF94A3B8),
      accentColor: Color(0xFF38BDF8),
      borderColor: Color(0xFF263B59),
    ),
    AppThemeSpec(
      id: 'dark_hc',
      name: 'Dark High Contrast',
      category: ThemeCategory.system,
      brightness: Brightness.dark,
      backgroundColor: Color(0xFF000000),
      surfaceColor: Color(0xFF050505),
      headerColor: Color(0xFF121212),
      textColor: Color(0xFFFFFFFF),
      subtextColor: Color(0xFFD4D4D8),
      accentColor: Color(0xFF00FF00),
      borderColor: Color(0xFF00FF00),
      highContrastBorder: true,
    ),
    AppThemeSpec(
      id: 'nidhogg',
      name: 'Nidhogg',
      category: ThemeCategory.system,
      brightness: Brightness.dark,
      backgroundColor: Color(0xFF0B080C),
      surfaceColor: Color(0xFF150E16),
      headerColor: Color(0xFF201420),
      textColor: Color(0xFFF5EEF2),
      subtextColor: Color(0xFF9E8A95),
      accentColor: Color(0xFFB91C1C),
      borderColor: Color(0xFF2D1924),
      watermarkAsset: 'assets/images/nidhoggr.webp',
      watermarkColor: Color(0xFF7F1D1D),
      watermarkOpacity: 0.09,
      subtitle: 'Racines d\'Obsidienne — Rouge sombre',
    ),
  ];

  static const List<AppThemeSpec> builtInAccessibilityThemes = [
    AppThemeSpec(
      id: 'a11y_protanopia',
      name: 'Protanopie',
      subtitle: 'Daltonisme rouge — Palette Bleu & Or',
      category: ThemeCategory.accessibility,
      brightness: Brightness.dark,
      backgroundColor: Color(0xFF0D1322),
      surfaceColor: Color(0xFF172036),
      headerColor: Color(0xFF212D4A),
      textColor: Color(0xFFF8FAFC),
      subtextColor: Color(0xFFA5B4FC),
      accentColor: Color(0xFFEAB308),
      borderColor: Color(0xFF3B82F6),
    ),
    AppThemeSpec(
      id: 'a11y_deuteranopia',
      name: 'Deutéranopie',
      subtitle: 'Daltonisme vert — Palette Indigo & Ambre',
      category: ThemeCategory.accessibility,
      brightness: Brightness.dark,
      backgroundColor: Color(0xFF101223),
      surfaceColor: Color(0xFF1A1D36),
      headerColor: Color(0xFF262A4D),
      textColor: Color(0xFFF8FAFC),
      subtextColor: Color(0xFFC7D2FE),
      accentColor: Color(0xFFF59E0B),
      borderColor: Color(0xFF6366F1),
    ),
    AppThemeSpec(
      id: 'a11y_tritanopia',
      name: 'Tritanopie',
      subtitle: 'Daltonisme bleu-jaune — Palette Sarcelle & Corail',
      category: ThemeCategory.accessibility,
      brightness: Brightness.dark,
      backgroundColor: Color(0xFF0B171A),
      surfaceColor: Color(0xFF13262B),
      headerColor: Color(0xFF1C363D),
      textColor: Color(0xFFF0FDFA),
      subtextColor: Color(0xFF99F6E4),
      accentColor: Color(0xFFF43F5E),
      borderColor: Color(0xFF14B8A6),
    ),
    AppThemeSpec(
      id: 'a11y_monochrome',
      name: 'Achromatopsie',
      subtitle: 'Monochrome — Nuances de gris haute lisibilité',
      category: ThemeCategory.accessibility,
      brightness: Brightness.dark,
      backgroundColor: Color(0xFF09090B),
      surfaceColor: Color(0xFF18181B),
      headerColor: Color(0xFF27272A),
      textColor: Color(0xFFFAFAFA),
      subtextColor: Color(0xFFA1A1AA),
      accentColor: Color(0xFFE4E4E7),
      borderColor: Color(0xFF52525B),
    ),
  ];
}

extension AppThemeContextExtension on BuildContext {
  AppThemeSpec get appTheme =>
      Theme.of(this).extension<AppThemeSpec>() ??
      AppThemeSpec.builtInSystemThemes.last;
}
