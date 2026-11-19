import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../../../../../domain/models/app_theme_spec.dart';
import '../../../../../domain/models/chat_models.dart';
import '../../../../core/l10n/locale_controller.dart';
import '../../view_models/chat_view_model.dart';

/// Displays a 3-tier fallback icon for an AI model:
/// 1. Model-specific icon from registry (`icon` URL, asset path, or element/family key)
/// 2. Provider default icon (`google`, `anthropic`, `openai`, etc.)
/// 3. Ratatosk default branding (`assets/brandings/ratatosk.svg`)
class ModelBadgeIcon extends StatelessWidget {
  const ModelBadgeIcon({
    super.key,
    required this.model,
    this.size = 20,
    this.showContainer = true,
  });

  final ModelInfoModel model;
  final double size;
  final bool showContainer;

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;
    final iconWidget = _resolveIconWidget(spec);

    if (!showContainer) {
      return SizedBox(width: size, height: size, child: iconWidget);
    }

    final boxSize = size + 14;
    return Container(
      width: boxSize,
      height: boxSize,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: spec.backgroundColor.withValues(alpha: 0.65),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: model.isRecommended
              ? spec.accentColor.withValues(alpha: 0.45)
              : spec.borderColor,
        ),
      ),
      child: SizedBox(width: size, height: size, child: iconWidget),
    );
  }

  Widget _resolveIconWidget(AppThemeSpec spec) {
    final rawIcon = (model.icon ?? '').trim();
    final lowerId = model.id.toLowerCase();
    final key = rawIcon.isNotEmpty ? rawIcon.toLowerCase() : lowerId;

    // 1a. Remote URL or local asset path if explicitly configured in AI_registery
    if (rawIcon.startsWith('http://') || rawIcon.startsWith('https://')) {
      if (rawIcon.toLowerCase().endsWith('.svg')) {
        return SvgPicture.network(
          rawIcon,
          width: size,
          height: size,
          placeholderBuilder: (_) =>
              ProviderBadgeIcon(providerId: model.provider, size: size),
        );
      }
      return Image.network(
        rawIcon,
        width: size,
        height: size,
        fit: BoxFit.contain,
        errorBuilder: (_, _, _) =>
            ProviderBadgeIcon(providerId: model.provider, size: size),
      );
    }

    if (rawIcon.startsWith('assets/')) {
      if (rawIcon.toLowerCase().endsWith('.svg')) {
        return SvgPicture.asset(
          rawIcon,
          width: size,
          height: size,
        );
      }
      return Image.asset(
        rawIcon,
        width: size,
        height: size,
        fit: BoxFit.contain,
        errorBuilder: (_, _, _) =>
            ProviderBadgeIcon(providerId: model.provider, size: size),
      );
    }

    // 1b. Minimalist vector icons for chemical element nomenclature & model families
    final modelSvg = _modelSpecificSvg(key, spec.accentColor);
    if (modelSvg != null) {
      return SvgPicture.string(modelSvg, width: size, height: size);
    }

    // 2. Fallback to Provider icon (which itself falls back to Ratatosk default)
    return ProviderBadgeIcon(providerId: model.provider, size: size);
  }

  static String? _modelSpecificSvg(String key, Color accent) {
    final hex = _colorToHex(accent);

    // Hydrogen (Z=1): single nucleus + 1 orbital ring + 1 electron
    if (key == 'hydrogen' || key.contains('hydrogen')) {
      return '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
          '<circle cx="12" cy="12" r="7.5" stroke="#38BDF8" stroke-width="1.6" stroke-dasharray="2 1.5"/>'
          '<circle cx="12" cy="12" r="2.6" fill="#38BDF8"/>'
          '<circle cx="19.5" cy="12" r="2.0" fill="#E0F2FE" stroke="#38BDF8" stroke-width="1.2"/>'
          '</svg>';
    }

    // Carbon (Z=6): minimalist hexagonal crystal / graphene ring with core
    if (key == 'carbon' || key.contains('carbon')) {
      return '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
          '<polygon points="12,3.5 19.4,7.75 19.4,16.25 12,20.5 4.6,16.25 4.6,7.75" stroke="#10B981" stroke-width="1.7" stroke-linejoin="round"/>'
          '<polygon points="12,7.5 15.9,9.75 15.9,14.25 12,16.5 8.1,14.25 8.1,9.75" stroke="#10B981" stroke-width="1.1" stroke-opacity="0.6"/>'
          '<circle cx="12" cy="12" r="1.8" fill="#10B981"/>'
          '</svg>';
    }

    // Argon (Z=18): noble gas dual concentric orbitals + symmetrical valence nodes
    if (key == 'argon' || key.contains('argon')) {
      return '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
          '<circle cx="12" cy="12" r="9" stroke="#A855F7" stroke-width="1.5"/>'
          '<circle cx="12" cy="12" r="5.2" stroke="#C084FC" stroke-width="1.3" stroke-opacity="0.75"/>'
          '<circle cx="12" cy="12" r="2.3" fill="#A855F7"/>'
          '<circle cx="12" cy="3" r="1.5" fill="#E9D5FF"/>'
          '<circle cx="12" cy="21" r="1.5" fill="#E9D5FF"/>'
          '<circle cx="3" cy="12" r="1.5" fill="#E9D5FF"/>'
          '<circle cx="21" cy="12" r="1.5" fill="#E9D5FF"/>'
          '</svg>';
    }

    // Other noble gases / elements (helium, neon, krypton, xenon, nitrogen, oxygen)
    if (key == 'helium' ||
        key == 'neon' ||
        key == 'krypton' ||
        key == 'xenon' ||
        key == 'nitrogen' ||
        key == 'oxygen') {
      return '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
          '<ellipse cx="12" cy="12" rx="9" ry="4.2" transform="rotate(30 12 12)" stroke="$hex" stroke-width="1.5"/>'
          '<ellipse cx="12" cy="12" rx="9" ry="4.2" transform="rotate(-30 12 12)" stroke="$hex" stroke-width="1.5"/>'
          '<circle cx="12" cy="12" r="2.2" fill="$hex"/>'
          '</svg>';
    }

    // Nano Banana / Image generation models
    if (key == 'nano-banana' || key.contains('banana') || key.contains('image')) {
      return '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
          '<path d="M7 17.5C11.5 18.5 16.5 14.5 17.5 7.5C14.5 11.5 10.5 14 6.5 14.5C5.5 14.7 5.8 17.2 7 17.5Z" stroke="#FBBF24" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>'
          '<path d="M17.5 7.5L19 5.5" stroke="#FBBF24" stroke-width="1.7" stroke-linecap="round"/>'
          '</svg>';
    }

    // Gemma (Open Source family)
    if (key == 'gemma' || key.contains('gemma')) {
      return '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
          '<polygon points="12,3 20,9 17,20 7,20 4,9" stroke="#2DD4BF" stroke-width="1.6" stroke-linejoin="round"/>'
          '<path d="M4 9H20M12 3L9 9L12 20L15 9L12 3Z" stroke="#2DD4BF" stroke-width="1.2" stroke-opacity="0.7"/>'
          '</svg>';
    }

    return null;
  }

  static String _colorToHex(Color c) {
    final r = (c.r * 255.0).round().clamp(0, 255).toRadixString(16).padLeft(2, '0');
    final g = (c.g * 255.0).round().clamp(0, 255).toRadixString(16).padLeft(2, '0');
    final b = (c.b * 255.0).round().clamp(0, 255).toRadixString(16).padLeft(2, '0');
    return '#$r$g$b';
  }
}

/// Renders the default emblem for a provider (`google`, `anthropic`, `openai`, etc.),
/// falling back to the Ratatosk default logo (`assets/brandings/ratatosk.svg`).
class ProviderBadgeIcon extends StatelessWidget {
  const ProviderBadgeIcon({
    super.key,
    required this.providerId,
    this.size = 18,
  });

  final String providerId;
  final double size;

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;
    final cleanId = providerId.trim().toLowerCase();
    final svg = _providerSvg(cleanId, spec.accentColor);

    if (svg != null) {
      return SvgPicture.string(svg, width: size, height: size);
    }

    // Level 3 fallback: Ratatosk default branding asset
    return SvgPicture.asset(
      'assets/brandings/ratatosk.svg',
      width: size,
      height: size,
      colorFilter: ColorFilter.mode(spec.accentColor, BlendMode.srcIn),
    );
  }

  static String? _providerSvg(String provider, Color accent) {
    switch (provider) {
      case 'google':
      case 'gemini':
        // 4-point Gemini sparkle
        return '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M12 2C12 7.52 16.48 12 22 12C16.48 12 12 16.48 12 22C12 16.48 7.52 12 2 12C7.52 12 12 7.52 12 2Z" fill="#60A5FA"/>'
            '</svg>';
      case 'anthropic':
      case 'claude':
        // Minimalist warm sunburst / spark for Claude
        return '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M12 3V21M3 12H21M5.6 5.6L18.4 18.4M18.4 5.6L5.6 18.4" stroke="#D97757" stroke-width="2.0" stroke-linecap="round"/>'
            '<circle cx="12" cy="12" r="2.5" fill="#D97757"/>'
            '</svg>';
      case 'openai':
        // Minimalist hexagonal loop
        return '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<circle cx="12" cy="12" r="8" stroke="#10A37F" stroke-width="1.8"/>'
            '<polygon points="12,6.5 16.8,9.2 16.8,14.8 12,17.5 7.2,14.8 7.2,9.2" stroke="#10A37F" stroke-width="1.5"/>'
            '</svg>';
      case 'mistral':
        return '<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M4 18V6L12 13L20 6V18" stroke="#F97316" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>'
            '</svg>';
      default:
        return null;
    }
  }
}

class ModelSelectorModal extends StatefulWidget {
  const ModelSelectorModal({
    super.key,
    required this.viewModel,
  });

  final ChatViewModel viewModel;

  static Future<void> show(
    BuildContext context,
    ChatViewModel viewModel,
  ) {
    return showDialog<void>(
      context: context,
      builder: (_) => ModelSelectorModal(viewModel: viewModel),
    );
  }

  @override
  State<ModelSelectorModal> createState() => _ModelSelectorModalState();
}

class _ModelSelectorModalState extends State<ModelSelectorModal> {
  final TextEditingController _searchController = TextEditingController();
  final Set<String> _expandedProviders = <String>{};
  String _searchQuery = '';
  bool _isRefreshing = false;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _handleRefresh() async {
    if (_isRefreshing) return;
    setState(() => _isRefreshing = true);
    await widget.viewModel.refreshModels(forceRemote: true);
    if (mounted) {
      setState(() => _isRefreshing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;
    final l10n = context.l10n;

    return ListenableBuilder(
      listenable: widget.viewModel,
      builder: (context, _) {
        final allModels = widget.viewModel.models;
        final q = _searchQuery.trim().toLowerCase();

        final filteredModels = q.isEmpty
            ? allModels
            : allModels.where((m) {
                return m.displayName.toLowerCase().contains(q) ||
                    m.id.toLowerCase().contains(q) ||
                    m.category.toLowerCase().contains(q) ||
                    (m.description?.toLowerCase().contains(q) ?? false);
              }).toList();

        // Favorites section
        final favoriteModels = filteredModels
            .where((m) => widget.viewModel.isFavoriteModel(m.id))
            .toList();

        // Group models by provider
        final byProvider = <String, List<ModelInfoModel>>{};
        for (final m in filteredModels) {
          byProvider.putIfAbsent(m.provider, () => <ModelInfoModel>[]).add(m);
        }

        return Dialog(
          backgroundColor: spec.surfaceColor,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
            side: BorderSide(color: spec.borderColor),
          ),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 620, maxHeight: 680),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Header
                Padding(
                  padding: const EdgeInsets.fromLTRB(18, 14, 12, 10),
                  child: Row(
                    children: [
                      SvgPicture.asset(
                        'assets/brandings/ratatosk.svg',
                        width: 20,
                        height: 20,
                        colorFilter: ColorFilter.mode(
                          spec.accentColor,
                          BlendMode.srcIn,
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          l10n.modelSelectorTitle,
                          style: TextStyle(
                            color: spec.textColor,
                            fontSize: 16,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                      IconButton(
                        tooltip: l10n.modelSelectorRefreshTooltip,
                        onPressed: _isRefreshing ? null : _handleRefresh,
                        icon: _isRefreshing
                            ? SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: spec.accentColor,
                                ),
                              )
                            : Icon(
                                Icons.sync_rounded,
                                size: 19,
                                color: spec.subtextColor,
                              ),
                      ),
                      IconButton(
                        tooltip: l10n.settingsClose,
                        onPressed: () => Navigator.of(context).pop(),
                        icon: Icon(
                          Icons.close_rounded,
                          size: 19,
                          color: spec.subtextColor,
                        ),
                      ),
                    ],
                  ),
                ),

                // Search bar
                Padding(
                  padding: const EdgeInsets.fromLTRB(18, 0, 18, 12),
                  child: TextField(
                    controller: _searchController,
                    onChanged: (val) => setState(() => _searchQuery = val),
                    style: TextStyle(color: spec.textColor, fontSize: 13),
                    decoration: InputDecoration(
                      hintText: l10n.modelSelectorSearchHint,
                      hintStyle: TextStyle(
                        color: spec.subtextColor,
                        fontSize: 13,
                      ),
                      prefixIcon: Icon(
                        Icons.search_rounded,
                        size: 18,
                        color: spec.subtextColor,
                      ),
                      suffixIcon: _searchQuery.isNotEmpty
                          ? IconButton(
                              onPressed: () {
                                _searchController.clear();
                                setState(() => _searchQuery = '');
                              },
                              icon: Icon(
                                Icons.clear_rounded,
                                size: 16,
                                color: spec.subtextColor,
                              ),
                            )
                          : null,
                      isDense: true,
                      filled: true,
                      fillColor: spec.backgroundColor.withValues(alpha: 0.55),
                      contentPadding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 10,
                      ),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(9),
                        borderSide: BorderSide(color: spec.borderColor),
                      ),
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(9),
                        borderSide: BorderSide(color: spec.borderColor),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(9),
                        borderSide: BorderSide(color: spec.accentColor),
                      ),
                    ),
                  ),
                ),

                Divider(height: 1, color: spec.borderColor),

                // Scrollable body
                Expanded(
                  child: filteredModels.isEmpty
                      ? Center(
                          child: Text(
                            l10n.modelSelectorEmptySearch(_searchQuery),
                            style: TextStyle(
                              color: spec.subtextColor,
                              fontSize: 13,
                            ),
                          ),
                        )
                      : ListView(
                          padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
                          children: [
                            // 1. Favorites section (if any)
                            if (favoriteModels.isNotEmpty) ...[
                              _SectionHeader(
                                leading: const Icon(
                                  Icons.star_rounded,
                                  size: 17,
                                  color: Color(0xFFFBBF24),
                                ),
                                title: l10n.modelSelectorFavorites(
                                  favoriteModels.length,
                                ),
                              ),
                              const SizedBox(height: 6),
                              ...favoriteModels.map(
                                (m) => _ModelRowTile(
                                  model: m,
                                  isSelected:
                                      m.id == widget.viewModel.selectedModelId,
                                  isFavorite: true,
                                  onSelect: () {
                                    widget.viewModel.selectModel(m.id);
                                    Navigator.of(context).pop();
                                  },
                                  onToggleFavorite: () =>
                                      widget.viewModel.toggleFavoriteModel(m.id),
                                ),
                              ),
                              const SizedBox(height: 14),
                            ],

                            // 2. Provider sections (Google, Anthropic, OpenAI, ...)
                            ...byProvider.entries.map((entry) {
                              final providerId = entry.key;
                              final providerModels = entry.value;
                              final recommended = providerModels
                                  .where((m) => m.isRecommended)
                                  .toList();
                              final others = providerModels
                                  .where((m) => !m.isRecommended)
                                  .toList();
                              final isExpanded = q.isNotEmpty ||
                                  _expandedProviders.contains(providerId) ||
                                  recommended.isEmpty;

                              return _ProviderModelsSection(
                                providerId: providerId,
                                recommendedModels: recommended,
                                otherModels: others,
                                isAllExpanded: isExpanded,
                                selectedModelId:
                                    widget.viewModel.selectedModelId,
                                isFavorite: widget.viewModel.isFavoriteModel,
                                onToggleExpandAll: () {
                                  setState(() {
                                    if (_expandedProviders
                                        .contains(providerId)) {
                                      _expandedProviders.remove(providerId);
                                    } else {
                                      _expandedProviders.add(providerId);
                                    }
                                  });
                                },
                                onSelectModel: (modelId) {
                                  widget.viewModel.selectModel(modelId);
                                  Navigator.of(context).pop();
                                },
                                onToggleFavorite:
                                    widget.viewModel.toggleFavoriteModel,
                              );
                            }),
                          ],
                        ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({
    required this.leading,
    required this.title,
    this.trailing,
  });

  final Widget leading;
  final String title;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
      child: Row(
        children: [
          leading,
          const SizedBox(width: 8),
          Text(
            title,
            style: TextStyle(
              color: spec.textColor,
              fontSize: 13,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.2,
            ),
          ),
          if (trailing != null) ...[
            const Spacer(),
            trailing!,
          ],
        ],
      ),
    );
  }
}

class _ProviderModelsSection extends StatelessWidget {
  const _ProviderModelsSection({
    required this.providerId,
    required this.recommendedModels,
    required this.otherModels,
    required this.isAllExpanded,
    required this.selectedModelId,
    required this.isFavorite,
    required this.onToggleExpandAll,
    required this.onSelectModel,
    required this.onToggleFavorite,
  });

  final String providerId;
  final List<ModelInfoModel> recommendedModels;
  final List<ModelInfoModel> otherModels;
  final bool isAllExpanded;
  final String selectedModelId;
  final bool Function(String modelId) isFavorite;
  final VoidCallback onToggleExpandAll;
  final ValueChanged<String> onSelectModel;
  final ValueChanged<String> onToggleFavorite;

  static String _providerDisplayName(String id) {
    switch (id.toLowerCase()) {
      case 'google':
        return 'Google Gemini';
      case 'anthropic':
        return 'Anthropic Claude';
      case 'openai':
        return 'OpenAI';
      case 'mistral':
        return 'Mistral AI';
      case 'ollama':
        return 'Ollama (Local)';
      default:
        return id.isEmpty
            ? 'Ratatosk'
            : '${id[0].toUpperCase()}${id.substring(1)}';
    }
  }

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;
    final l10n = context.l10n;

    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _SectionHeader(
            leading: ProviderBadgeIcon(providerId: providerId, size: 16),
            title: _providerDisplayName(providerId),
            trailing: Text(
              l10n.modelSelectorCount(
                recommendedModels.length + otherModels.length,
              ),
              style: TextStyle(color: spec.subtextColor, fontSize: 11),
            ),
          ),
          const SizedBox(height: 6),

          // Recommended models for this provider
          if (recommendedModels.isNotEmpty) ...[
            Padding(
              padding: const EdgeInsets.only(left: 6, bottom: 4),
              child: Text(
                l10n.modelSelectorRecommendedSection,
                style: TextStyle(
                  color: spec.subtextColor,
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            ...recommendedModels.map(
              (m) => _ModelRowTile(
                model: m,
                isSelected: m.id == selectedModelId,
                isFavorite: isFavorite(m.id),
                onSelect: () => onSelectModel(m.id),
                onToggleFavorite: () => onToggleFavorite(m.id),
              ),
            ),
          ],

          // Expandable "All models" subsection
          if (otherModels.isNotEmpty) ...[
            const SizedBox(height: 4),
            InkWell(
              borderRadius: BorderRadius.circular(8),
              onTap: onToggleExpandAll,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 7),
                child: Row(
                  children: [
                    Icon(
                      isAllExpanded
                          ? Icons.keyboard_arrow_down_rounded
                          : Icons.keyboard_arrow_right_rounded,
                      size: 17,
                      color: spec.subtextColor,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      l10n.modelSelectorAllModels(otherModels.length),
                      style: TextStyle(
                        color: spec.subtextColor,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            if (isAllExpanded) ...[
              const SizedBox(height: 4),
              ...otherModels.map(
                (m) => _ModelRowTile(
                  model: m,
                  isSelected: m.id == selectedModelId,
                  isFavorite: isFavorite(m.id),
                  onSelect: () => onSelectModel(m.id),
                  onToggleFavorite: () => onToggleFavorite(m.id),
                ),
              ),
            ],
          ],
        ],
      ),
    );
  }
}

class _ModelRowTile extends StatelessWidget {
  const _ModelRowTile({
    required this.model,
    required this.isSelected,
    required this.isFavorite,
    required this.onSelect,
    required this.onToggleFavorite,
  });

  final ModelInfoModel model;
  final bool isSelected;
  final bool isFavorite;
  final VoidCallback onSelect;
  final VoidCallback onToggleFavorite;

  static (String, Color)? _categoryBadge(String category) {
    switch (category.toLowerCase()) {
      case 'pro':
        return ('Pro', const Color(0xFFA855F7));
      case 'flash':
        return ('Flash', const Color(0xFF10B981));
      case 'flash_lite':
        return ('Lite', const Color(0xFF38BDF8));
      case 'open_source':
        return ('Open Source', const Color(0xFF2DD4BF));
      case 'thinking':
        return ('Thinking', const Color(0xFFF59E0B));
      default:
        return null;
    }
  }

  static String? _formatContextWindow(int? tokens) {
    if (tokens == null || tokens <= 0) return null;
    if (tokens >= 1000000) {
      final m = tokens / 1000000;
      return '${m == m.roundToDouble() ? m.toInt() : m.toStringAsFixed(1)}M ctx';
    }
    if (tokens >= 1000) {
      return '${(tokens / 1000).round()}k ctx';
    }
    return '$tokens ctx';
  }

  static String? _formatPrice(
    double? inPrice,
    double? outPrice,
    String freeLabel,
  ) {
    if (inPrice == null && outPrice == null) return null;
    if (inPrice == 0 && outPrice == 0) return freeLabel;
    final inStr = inPrice != null ? '\$${inPrice.toStringAsFixed(2)}' : '-';
    final outStr = outPrice != null ? '\$${outPrice.toStringAsFixed(2)}' : '-';
    return 'In: $inStr • Out: $outStr';
  }

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;
    final l10n = context.l10n;
    final catBadge = _categoryBadge(model.category);
    final ctxLabel = _formatContextWindow(model.contextWindow);
    final priceLabel = _formatPrice(
      model.inputPricePer1m,
      model.outputPricePer1m,
      l10n.modelSelectorFreeLocal,
    );

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Material(
        color: isSelected
            ? spec.accentColor.withValues(alpha: 0.14)
            : spec.backgroundColor.withValues(alpha: 0.35),
        borderRadius: BorderRadius.circular(10),
        child: InkWell(
          borderRadius: BorderRadius.circular(10),
          onTap: onSelect,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 9),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: isSelected
                    ? spec.accentColor.withValues(alpha: 0.7)
                    : spec.borderColor.withValues(alpha: 0.7),
              ),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // 3-tier resolved icon badge
                Padding(
                  padding: const EdgeInsets.only(top: 2),
                  child: ModelBadgeIcon(model: model, size: 20),
                ),
                const SizedBox(width: 11),

                // Model details
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Flexible(
                            child: Text(
                              model.displayName,
                              style: TextStyle(
                                color: spec.textColor,
                                fontSize: 13.5,
                                fontWeight: FontWeight.w700,
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          if (catBadge != null) ...[
                            const SizedBox(width: 7),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 6,
                                vertical: 1.5,
                              ),
                              decoration: BoxDecoration(
                                color: catBadge.$2.withValues(alpha: 0.16),
                                borderRadius: BorderRadius.circular(5),
                                border: Border.all(
                                  color: catBadge.$2.withValues(alpha: 0.45),
                                ),
                              ),
                              child: Text(
                                catBadge.$1,
                                style: TextStyle(
                                  color: catBadge.$2,
                                  fontSize: 10,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ),
                          ],
                          if (model.isRecommended) ...[
                            const SizedBox(width: 6),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 6,
                                vertical: 1.5,
                              ),
                              decoration: BoxDecoration(
                                color: spec.accentColor.withValues(alpha: 0.15),
                                borderRadius: BorderRadius.circular(5),
                              ),
                              child: Text(
                                l10n.modelSelectorRecommendedBadge,
                                style: TextStyle(
                                  color: spec.accentColor,
                                  fontSize: 10,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                          ],
                        ],
                      ),
                      const SizedBox(height: 2),
                      Wrap(
                        spacing: 8,
                        runSpacing: 2,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          Text(
                            model.id,
                            style: TextStyle(
                              color: spec.subtextColor,
                              fontSize: 11,
                              fontFamily: 'monospace',
                            ),
                          ),
                          if (ctxLabel != null)
                            Text(
                              '• $ctxLabel',
                              style: TextStyle(
                                color: spec.subtextColor,
                                fontSize: 11,
                              ),
                            ),
                          if (priceLabel != null)
                            Text(
                              '• $priceLabel',
                              style: TextStyle(
                                color: spec.subtextColor,
                                fontSize: 11,
                              ),
                            ),
                        ],
                      ),
                      if (model
                              .localizedDescription(
                                Localizations.localeOf(context).languageCode,
                              )
                              ?.trim()
                              .isNotEmpty ??
                          false) ...[
                        const SizedBox(height: 4),
                        Text(
                          model
                              .localizedDescription(
                                Localizations.localeOf(context).languageCode,
                              )!
                              .trim(),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: spec.subtextColor.withValues(alpha: 0.9),
                            fontSize: 11.5,
                            height: 1.3,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),

                const SizedBox(width: 6),

                // Favorite star button
                IconButton(
                  tooltip: isFavorite
                      ? l10n.modelSelectorRemoveFav
                      : l10n.modelSelectorAddFav,
                  onPressed: onToggleFavorite,
                  visualDensity: VisualDensity.compact,
                  icon: Icon(
                    isFavorite ? Icons.star_rounded : Icons.star_border_rounded,
                    size: 20,
                    color: isFavorite
                        ? const Color(0xFFFBBF24)
                        : spec.subtextColor,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
