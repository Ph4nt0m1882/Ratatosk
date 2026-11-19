import 'package:flutter/material.dart';

import '../../../domain/models/app_theme_spec.dart';

class CustomThemeDialog extends StatefulWidget {
  const CustomThemeDialog({super.key});

  @override
  State<CustomThemeDialog> createState() => _CustomThemeDialogState();
}

class _CustomThemeDialogState extends State<CustomThemeDialog> {
  final TextEditingController _nameCtrl =
      TextEditingController(text: 'Mon Thème');
  bool _isDark = true;
  Color _accentColor = const Color(0xFFFD824D);
  Color _backgroundColor = const Color(0xFF120C14);
  String? _watermarkAsset = 'assets/images/nidhoggr.webp';

  static const List<Color> _accentSwatches = [
    Color(0xFFFD824D), // Ratatosk Copper
    Color(0xFFB91C1C), // Nidhogg Crimson
    Color(0xFF2E7D32), // Yggdrasil Emerald
    Color(0xFF8B5CF6), // Huginn Violet
    Color(0xFF38BDF8), // Muninn Sky
    Color(0xFFEAB308), // Odin Gold
    Color(0xFFEC4899), // Bifrost Rose
  ];

  static const List<(String, Color, bool)> _bgPresets = [
    ('Obsidienne', Color(0xFF0D090E), true),
    ('Ardoise Nuit', Color(0xFF0F172A), true),
    ('Forêt Sombre', Color(0xFF0A140E), true),
    ('Sauge Clair', Color(0xFFF2F7F1), false),
    ('Parchemin', Color(0xFFFDFBF7), false),
    ('Ivoire Pur', Color(0xFFFFFFFF), false),
  ];

  @override
  void dispose() {
    _nameCtrl.dispose();
    super.dispose();
  }

  void _submit() {
    final name = _nameCtrl.text.trim().isEmpty
        ? 'Thème Custom'
        : _nameCtrl.text.trim();
    final id = 'custom_${DateTime.now().millisecondsSinceEpoch}';
    final surface = _isDark
        ? Color.lerp(_backgroundColor, Colors.white, 0.05)!
        : Color.lerp(_backgroundColor, Colors.white, 0.65)!;
    final header = _isDark
        ? Color.lerp(_backgroundColor, Colors.white, 0.10)!
        : Color.lerp(_backgroundColor, Colors.black, 0.05)!;
    final text = _isDark ? const Color(0xFFF8FAFC) : const Color(0xFF0F172A);
    final subtext = _isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B);
    final border = _isDark
        ? Color.lerp(_backgroundColor, _accentColor, 0.25)!
        : Color.lerp(_backgroundColor, _accentColor, 0.22)!;

    final spec = AppThemeSpec(
      id: id,
      name: name,
      category: ThemeCategory.custom,
      brightness: _isDark ? Brightness.dark : Brightness.light,
      backgroundColor: _backgroundColor,
      surfaceColor: surface,
      headerColor: header,
      textColor: text,
      subtextColor: subtext,
      accentColor: _accentColor,
      borderColor: border,
      watermarkAsset: _watermarkAsset,
      watermarkColor: _accentColor,
      watermarkOpacity: _isDark ? 0.08 : 0.055,
    );
    Navigator.of(context).pop(spec);
  }

  @override
  Widget build(BuildContext context) {
    final current = context.appTheme;

    return Dialog(
      backgroundColor: current.surfaceColor,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 460),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Créer un thème personnalisé',
                style: TextStyle(
                  color: current.textColor,
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _nameCtrl,
                style: TextStyle(color: current.textColor),
                decoration: const InputDecoration(
                  labelText: 'Nom du thème',
                ),
              ),
              const SizedBox(height: 16),
              Text(
                'Teinte de fond',
                style: TextStyle(
                  color: current.subtextColor,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: _bgPresets.map((preset) {
                  final (label, color, isDarkPreset) = preset;
                  final selected =
                      _backgroundColor.toARGB32() == color.toARGB32();
                  return ChoiceChip(
                    label: Text(label),
                    selected: selected,
                    onSelected: (_) {
                      setState(() {
                        _backgroundColor = color;
                        _isDark = isDarkPreset;
                      });
                    },
                  );
                }).toList(),
              ),
              const SizedBox(height: 16),
              Text(
                'Couleur d\'accentuation',
                style: TextStyle(
                  color: current.subtextColor,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 10,
                children: _accentSwatches.map((swatch) {
                  final selected = _accentColor.toARGB32() == swatch.toARGB32();
                  return GestureDetector(
                    onTap: () => setState(() => _accentColor = swatch),
                    child: Container(
                      width: 32,
                      height: 32,
                      decoration: BoxDecoration(
                        color: swatch,
                        shape: BoxShape.circle,
                        border: Border.all(
                          color: selected ? Colors.white : Colors.transparent,
                          width: 2.5,
                        ),
                      ),
                    ),
                  );
                }).toList(),
              ),
              const SizedBox(height: 16),
              Text(
                'Illustration en filigrane (décorative)',
                style: TextStyle(
                  color: current.subtextColor,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                children: [
                  ChoiceChip(
                    label: const Text('Aucune'),
                    selected: _watermarkAsset == null,
                    onSelected: (_) => setState(() => _watermarkAsset = null),
                  ),
                  ChoiceChip(
                    label: const Text('Yggdrasil'),
                    selected:
                        _watermarkAsset == 'assets/images/yggdrasil.webp',
                    onSelected: (_) => setState(
                      () => _watermarkAsset = 'assets/images/yggdrasil.webp',
                    ),
                  ),
                  ChoiceChip(
                    label: const Text('Nidhogg'),
                    selected:
                        _watermarkAsset == 'assets/images/nidhoggr.webp',
                    onSelected: (_) => setState(
                      () => _watermarkAsset = 'assets/images/nidhoggr.webp',
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: Text(
                      'Annuler',
                      style: TextStyle(color: current.subtextColor),
                    ),
                  ),
                  const SizedBox(width: 10),
                  FilledButton(
                    style: FilledButton.styleFrom(
                      backgroundColor: current.accentColor,
                    ),
                    onPressed: _submit,
                    child: const Text('Enregistrer'),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
