import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../../../domain/models/app_theme_spec.dart';
import '../../../../core/l10n/locale_controller.dart';
import '../../view_models/chat_view_model.dart';
import 'model_selector_modal.dart';

class ChatComposerBar extends StatefulWidget {
  const ChatComposerBar({
    super.key,
    required this.viewModel,
  });

  final ChatViewModel viewModel;

  @override
  State<ChatComposerBar> createState() => _ChatComposerBarState();
}

class _ChatComposerBarState extends State<ChatComposerBar> {
  final TextEditingController _promptCtrl = TextEditingController();
  late final FocusNode _focusNode = FocusNode(
    onKeyEvent: (node, event) {
      if (event is KeyDownEvent &&
          event.logicalKey == LogicalKeyboardKey.enter &&
          !HardwareKeyboard.instance.isShiftPressed) {
        _send();
        return KeyEventResult.handled;
      }
      return KeyEventResult.ignored;
    },
  );
  bool _isFocused = false;
  bool _hasText = false;

  @override
  void initState() {
    super.initState();
    _focusNode.addListener(() {
      if (mounted) {
        setState(() => _isFocused = _focusNode.hasFocus);
      }
    });
    _promptCtrl.addListener(() {
      final nonEmpty = _promptCtrl.text.trim().isNotEmpty;
      if (nonEmpty != _hasText && mounted) {
        setState(() => _hasText = nonEmpty);
      }
    });
  }

  @override
  void dispose() {
    _focusNode.dispose();
    _promptCtrl.dispose();
    super.dispose();
  }

  Future<void> _pickFile() async {
    final result = await FilePicker.platform.pickFiles(withData: true);
    if (result == null || result.files.isEmpty) return;
    final picked = result.files.first;
    if (picked.bytes == null) return;
    await widget.viewModel.uploadAndStageAttachment(
      picked.name,
      picked.bytes!,
    );
  }

  void _send() {
    final text = _promptCtrl.text.trim();
    if (text.isEmpty || widget.viewModel.isStreaming) return;
    _promptCtrl.clear();
    widget.viewModel.sendMessage(text);
  }

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;
    final l10n = context.l10n;
    final canSend = _hasText && !widget.viewModel.isStreaming;

    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 6, 20, 16),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 820),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 180),
            padding: const EdgeInsets.fromLTRB(16, 12, 14, 10),
            decoration: BoxDecoration(
              color: spec.surfaceColor.withValues(alpha: 0.95),
              borderRadius: BorderRadius.circular(24),
              border: Border.all(
                color: _isFocused
                    ? spec.accentColor.withValues(alpha: 0.75)
                    : spec.borderColor,
                width: _isFocused ? 1.6 : 1.0,
              ),
              boxShadow: [
                BoxShadow(
                  color: _isFocused
                      ? spec.accentColor.withValues(alpha: 0.14)
                      : Colors.black.withValues(alpha: 0.16),
                  blurRadius: _isFocused ? 22 : 16,
                  offset: const Offset(0, 6),
                ),
              ],
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Pending staged attachments
                if (widget.viewModel.pendingAttachments.isNotEmpty) ...[
                  Wrap(
                    spacing: 8,
                    runSpacing: 6,
                    children: widget.viewModel.pendingAttachments.map((att) {
                      return Chip(
                        backgroundColor:
                            spec.accentColor.withValues(alpha: 0.12),
                        side: BorderSide(
                          color: spec.accentColor.withValues(alpha: 0.4),
                        ),
                        avatar: Icon(
                          Icons.insert_drive_file_outlined,
                          size: 15,
                          color: spec.accentColor,
                        ),
                        label: Text(
                          att.filename,
                          style: TextStyle(
                            color: spec.textColor,
                            fontSize: 12.5,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        deleteIconColor: spec.subtextColor,
                        onDeleted: () =>
                            widget.viewModel.removePendingAttachment(att.id),
                      );
                    }).toList(),
                  ),
                  const SizedBox(height: 8),
                ],

                // Borderless roomy text input
                TextField(
                  controller: _promptCtrl,
                  focusNode: _focusNode,
                  minLines: 1,
                  maxLines: 5,
                  style: TextStyle(
                    color: spec.textColor,
                    fontSize: 15,
                    height: 1.4,
                  ),
                  decoration: InputDecoration(
                    hintText: l10n.composerHint,
                    hintStyle: TextStyle(
                      color: spec.subtextColor.withValues(alpha: 0.8),
                      fontSize: 14.5,
                    ),
                    border: InputBorder.none,
                    enabledBorder: InputBorder.none,
                    focusedBorder: InputBorder.none,
                    filled: false,
                    isDense: true,
                    contentPadding: const EdgeInsets.symmetric(
                      horizontal: 4,
                      vertical: 6,
                    ),
                  ),
                ),

                const SizedBox(height: 8),

                // Friendly tactile option pills + Model selector + Send button
                Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Expanded(
                      child: Wrap(
                        spacing: 8,
                        runSpacing: 6,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          // 1. Attach file pill
                          _ComposerActionPill(
                            icon: Icons.add_photo_alternate_outlined,
                            label: l10n.composerAttach,
                            tooltip: l10n.composerAttachTooltip,
                            isActive:
                                widget.viewModel.pendingAttachments.isNotEmpty,
                            onTap:
                                widget.viewModel.isStreaming ? null : _pickFile,
                          ),

                          // 2. Web Search friendly selector
                          _WebSearchMenuPill(viewModel: widget.viewModel),

                          // 3. Memory mode friendly selector
                          _MemoryModeMenuPill(viewModel: widget.viewModel),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),

                    // 4. Per-message Model Selector Pill
                    _ComposerModelPill(viewModel: widget.viewModel),
                    const SizedBox(width: 8),

                    // 5. Expressive Send Button
                    AnimatedContainer(
                      duration: const Duration(milliseconds: 160),
                      child: FilledButton.icon(
                        style: FilledButton.styleFrom(
                          backgroundColor: canSend
                              ? spec.accentColor
                              : spec.borderColor.withValues(alpha: 0.55),
                          foregroundColor: canSend
                              ? Colors.white
                              : spec.subtextColor,
                          elevation: 0,
                          padding: const EdgeInsets.symmetric(
                            horizontal: 18,
                            vertical: 12,
                          ),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(999),
                          ),
                        ),
                        onPressed: canSend ? _send : null,
                        icon: widget.viewModel.isStreaming
                            ? SizedBox(
                                width: 15,
                                height: 15,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: spec.accentColor,
                                ),
                              )
                            : const Icon(Icons.arrow_upward_rounded, size: 18),
                        label: Text(
                          widget.viewModel.isStreaming
                              ? l10n.composerSending
                              : l10n.composerSend,
                          style: const TextStyle(
                            fontSize: 13.5,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _ComposerModelPill extends StatelessWidget {
  const _ComposerModelPill({required this.viewModel});

  final ChatViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;
    final l10n = context.l10n;
    final models = viewModel.models;

    if (models.isEmpty) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
        decoration: BoxDecoration(
          color: spec.backgroundColor.withValues(alpha: 0.55),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: spec.borderColor),
        ),
        child: Text(
          viewModel.selectedModelId,
          style: TextStyle(
            color: spec.textColor,
            fontSize: 12.5,
            fontWeight: FontWeight.w700,
          ),
        ),
      );
    }

    final currentModel = models.firstWhere(
      (m) => m.id == viewModel.selectedModelId,
      orElse: () => models.first,
    );
    final isFav = viewModel.isFavoriteModel(currentModel.id);

    return Tooltip(
      message: l10n.composerChangeModelTooltip,
      child: Material(
        color: spec.backgroundColor.withValues(alpha: 0.65),
        borderRadius: BorderRadius.circular(999),
        child: InkWell(
          borderRadius: BorderRadius.circular(999),
          onTap: () => ModelSelectorModal.show(context, viewModel),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 6.5),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(999),
              border: Border.all(
                color: spec.accentColor.withValues(alpha: 0.4),
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                ModelBadgeIcon(
                  model: currentModel,
                  size: 15,
                  showContainer: false,
                ),
                const SizedBox(width: 7),
                ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 165),
                  child: Text(
                    currentModel.displayName,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: spec.textColor,
                      fontSize: 12.5,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
                if (isFav) ...[
                  const SizedBox(width: 5),
                  const Icon(
                    Icons.star_rounded,
                    size: 13.5,
                    color: Color(0xFFFBBF24),
                  ),
                ],
                const SizedBox(width: 4),
                Icon(
                  Icons.unfold_more_rounded,
                  size: 15,
                  color: spec.subtextColor,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _ComposerActionPill extends StatelessWidget {
  const _ComposerActionPill({
    required this.icon,
    required this.label,
    this.tooltip,
    this.isActive = false,
    this.onTap,
  });

  final IconData icon;
  final String label;
  final String? tooltip;
  final bool isActive;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;
    final content = Material(
      color: isActive
          ? spec.accentColor.withValues(alpha: 0.16)
          : spec.backgroundColor.withValues(alpha: 0.55),
      borderRadius: BorderRadius.circular(999),
      child: InkWell(
        borderRadius: BorderRadius.circular(999),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(999),
            border: Border.all(
              color: isActive
                  ? spec.accentColor.withValues(alpha: 0.55)
                  : spec.borderColor,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                icon,
                size: 16,
                color: isActive ? spec.accentColor : spec.subtextColor,
              ),
              const SizedBox(width: 6),
              Text(
                label,
                style: TextStyle(
                  color: isActive ? spec.textColor : spec.subtextColor,
                  fontSize: 12.5,
                  fontWeight: isActive ? FontWeight.w700 : FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ),
    );

    if (tooltip != null) {
      return Tooltip(message: tooltip!, child: content);
    }
    return content;
  }
}

class _WebSearchMenuPill extends StatelessWidget {
  const _WebSearchMenuPill({required this.viewModel});

  final ChatViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;
    final l10n = context.l10n;
    final options = [
      (
        'no_search',
        l10n.webOffTitle,
        l10n.webOffDesc,
        Icons.public_off_rounded,
      ),
      (
        'search',
        l10n.webStandardTitle,
        l10n.webStandardDesc,
        Icons.travel_explore_rounded,
      ),
      (
        'full_search',
        l10n.webDeepTitle,
        l10n.webDeepDesc,
        Icons.explore_rounded,
      ),
    ];
    final current = options.firstWhere(
      (o) => o.$1 == viewModel.searchMode,
      orElse: () => options[1],
    );
    final isWebActive = current.$1 != 'no_search';

    return PopupMenuButton<String>(
      tooltip: l10n.composerWebTooltip,
      color: spec.surfaceColor,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: spec.borderColor),
      ),
      onSelected: viewModel.setSearchMode,
      itemBuilder: (context) => options.map((opt) {
        final selected = opt.$1 == viewModel.searchMode;
        return PopupMenuItem<String>(
          value: opt.$1,
          child: Row(
            children: [
              Icon(
                opt.$4,
                size: 19,
                color: selected ? spec.accentColor : spec.subtextColor,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      opt.$2,
                      style: TextStyle(
                        color: spec.textColor,
                        fontSize: 13.5,
                        fontWeight:
                            selected ? FontWeight.w700 : FontWeight.w600,
                      ),
                    ),
                    Text(
                      opt.$3,
                      style: TextStyle(
                        color: spec.subtextColor,
                        fontSize: 11.5,
                      ),
                    ),
                  ],
                ),
              ),
              if (selected)
                Icon(Icons.check_circle_rounded,
                    size: 17, color: spec.accentColor),
            ],
          ),
        );
      }).toList(),
      child: IgnorePointer(
        child: _ComposerActionPill(
          icon: current.$4,
          label: current.$2,
          isActive: isWebActive,
          onTap: () {},
        ),
      ),
    );
  }
}

class _MemoryModeMenuPill extends StatelessWidget {
  const _MemoryModeMenuPill({required this.viewModel});

  final ChatViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;
    final l10n = context.l10n;
    final options = [
      ('eco', l10n.memEcoTitle, l10n.memEcoDesc, Icons.spa_outlined),
      ('auto', l10n.memAutoTitle, l10n.memAutoDesc, Icons.auto_fix_high_rounded),
      ('full', l10n.memFullTitle, l10n.memFullDesc, Icons.psychology_outlined),
      ('fixed', l10n.memFixedTitle, l10n.memFixedDesc, Icons.short_text_rounded),
      (
        'none',
        l10n.memNoneTitle,
        l10n.memNoneDesc,
        Icons.cleaning_services_outlined,
      ),
    ];
    final current = options.firstWhere(
      (o) => o.$1 == viewModel.historyMode,
      orElse: () => options.first,
    );

    return PopupMenuButton<String>(
      tooltip: l10n.composerMemoryTooltip,
      color: spec.surfaceColor,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: spec.borderColor),
      ),
      onSelected: viewModel.setHistoryMode,
      itemBuilder: (context) => options.map((opt) {
        final selected = opt.$1 == viewModel.historyMode;
        return PopupMenuItem<String>(
          value: opt.$1,
          child: Row(
            children: [
              Icon(
                opt.$4,
                size: 19,
                color: selected ? spec.accentColor : spec.subtextColor,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      opt.$2,
                      style: TextStyle(
                        color: spec.textColor,
                        fontSize: 13.5,
                        fontWeight:
                            selected ? FontWeight.w700 : FontWeight.w600,
                      ),
                    ),
                    Text(
                      opt.$3,
                      style: TextStyle(
                        color: spec.subtextColor,
                        fontSize: 11.5,
                      ),
                    ),
                  ],
                ),
              ),
              if (selected)
                Icon(Icons.check_circle_rounded,
                    size: 17, color: spec.accentColor),
            ],
          ),
        );
      }).toList(),
      child: IgnorePointer(
        child: _ComposerActionPill(
          icon: current.$4,
          label: current.$2,
          isActive: false,
          onTap: () {},
        ),
      ),
    );
  }
}
