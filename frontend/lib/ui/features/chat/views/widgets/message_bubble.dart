import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../../../../../domain/models/app_theme_spec.dart';
import '../../../../../domain/models/chat_models.dart';
import '../../../../core/l10n/locale_controller.dart';
import '../../view_models/chat_view_model.dart';
import 'chat_markdown_body.dart';
import 'progressive_image_card.dart';

class MessageBubble extends StatefulWidget {
  const MessageBubble({
    super.key,
    required this.message,
    required this.viewModel,
  });

  final ChatMessageItem message;
  final ChatViewModel viewModel;

  @override
  State<MessageBubble> createState() => _MessageBubbleState();
}

class _MessageBubbleState extends State<MessageBubble> {
  bool _thinkingExpanded = false;

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;
    final msg = widget.message;
    final isUser = msg.role == 'user';

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 740),
        child: Container(
          margin: const EdgeInsets.symmetric(vertical: 8),
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: isUser
                ? spec.accentColor.withValues(alpha: 0.16)
                : spec.surfaceColor.withValues(alpha: 0.92),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: isUser
                  ? spec.accentColor.withValues(alpha: 0.45)
                  : spec.borderColor,
              width: spec.highContrastBorder ? 1.8 : 1.0,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Role & model header
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    isUser
                        ? Icons.person_outline_rounded
                        : Icons.auto_awesome_rounded,
                    size: 15,
                    color: spec.accentColor,
                  ),
                  const SizedBox(width: 6),
                  Text(
                    isUser
                        ? widget.viewModel.session.username
                        : (msg.model ?? 'Ratatosk'),
                    style: TextStyle(
                      color: spec.subtextColor,
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  if (msg.isStreaming) ...[
                    const SizedBox(width: 8),
                    SizedBox(
                      width: 10,
                      height: 10,
                      child: CircularProgressIndicator(
                        strokeWidth: 1.6,
                        color: spec.accentColor,
                      ),
                    ),
                  ],
                ],
              ),
              const SizedBox(height: 10),

              // Collapsible Thinking block
              if (msg.thinking.isNotEmpty) ...[
                InkWell(
                  onTap: () =>
                      setState(() => _thinkingExpanded = !_thinkingExpanded),
                  borderRadius: BorderRadius.circular(8),
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 6,
                    ),
                    decoration: BoxDecoration(
                      color: spec.headerColor.withValues(alpha: 0.55),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: spec.borderColor),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              Icons.psychology_outlined,
                              size: 15,
                              color: spec.accentColor,
                            ),
                            const SizedBox(width: 6),
                            Text(
                              context.l10n.msgInternalThinking,
                              style: TextStyle(
                                color: spec.subtextColor,
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            const SizedBox(width: 4),
                            Icon(
                              _thinkingExpanded
                                  ? Icons.expand_less_rounded
                                  : Icons.expand_more_rounded,
                              size: 15,
                              color: spec.subtextColor,
                            ),
                          ],
                        ),
                        if (_thinkingExpanded) ...[
                          const SizedBox(height: 6),
                          Text(
                            msg.thinking,
                            style: TextStyle(
                              color: spec.subtextColor,
                              fontSize: 12,
                              fontStyle: FontStyle.italic,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 10),
              ],

              // Tool Calls & Results
              if (msg.toolCalls.isNotEmpty) ...[
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: msg.toolCalls
                      .map((tc) => _ToolCallBadge(toolCall: tc))
                      .toList(),
                ),
                const SizedBox(height: 10),
              ],

              // Inline Content & Attachments (placed anywhere in the message)
              ..._buildContentAndAttachments(spec, msg, isUser),

              // Progressive Denoising Image Preview (shown inline while generating)
              if (msg.imageProgress != null)
                ProgressiveImageCard(
                  progressState: msg.imageProgress!,
                  hasFinalAttachment:
                      msg.attachments.any((a) => a.isImage && a.isGenerated),
                ),

              // Error message if any
              if (msg.error != null) ...[
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: const Color(0xFFEF4444).withValues(alpha: 0.14),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: const Color(0xFFEF4444)),
                  ),
                  child: Text(
                    msg.error!,
                    style: const TextStyle(
                      color: Color(0xFFFCA5A5),
                      fontSize: 12,
                    ),
                  ),
                ),
              ],

              // Sources (Web & Attachments)
              if (msg.sources.isNotEmpty) ...[
                const SizedBox(height: 12),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: msg.sources.map((src) {
                    return Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: spec.headerColor,
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: spec.borderColor),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            src.kind == 'web'
                                ? Icons.language_rounded
                                : Icons.attach_file_rounded,
                            size: 12,
                            color: spec.accentColor,
                          ),
                          const SizedBox(width: 5),
                          ConstrainedBox(
                            constraints: const BoxConstraints(maxWidth: 200),
                            child: Text(
                              src.title,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                color: spec.textColor,
                                fontSize: 11,
                              ),
                            ),
                          ),
                        ],
                      ),
                    );
                  }).toList(),
                ),
              ],

              // Usage & Cost footer
              if (msg.usage != null) ...[
                const SizedBox(height: 10),
                Text(
                  'Tokens : ${msg.usage!.inputTokens} in / ${msg.usage!.outputTokens} out'
                  '${msg.usage!.thoughtsTokens > 0 ? " (${msg.usage!.thoughtsTokens} réflexion)" : ""}'
                  ' • Coût : ${msg.usage!.cost.toStringAsFixed(6)} ${msg.usage!.currency}',
                  style: TextStyle(
                    color: spec.subtextColor,
                    fontSize: 10,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  static final RegExp _inlineAttachmentPattern = RegExp(
    r'!?\[([^\]]*)\]\(attachment://([^)\s]+)\)|\{\{attachment:([^}\s]+)\}\}',
  );

  List<Widget> _buildContentAndAttachments(
    AppThemeSpec spec,
    ChatMessageItem msg,
    bool isUser,
  ) {
    if (isUser) {
      return [
        if (msg.attachments.isNotEmpty) ...[
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: msg.attachments
                .map(
                  (att) => _AttachmentCard(
                    attachment: att,
                    viewModel: widget.viewModel,
                  ),
                )
                .toList(),
          ),
          const SizedBox(height: 10),
        ],
        if (msg.content.isNotEmpty) ChatMarkdownBody(data: msg.content),
      ];
    }

    final attById = {for (final a in msg.attachments) a.id: a};
    String effectiveContent = msg.content;

    final unreferenced = msg.attachments
        .where((a) => !effectiveContent.contains('attachment://${a.id}'))
        .toList()
      ..sort(
        (a, b) => (b.insertOffset ?? 0).compareTo(a.insertOffset ?? 0),
      );

    for (final att in unreferenced) {
      final tag = '![${att.filename}](attachment://${att.id})';
      if (effectiveContent.isEmpty) {
        effectiveContent = tag;
        continue;
      }
      int rawOff = att.insertOffset ?? 0;
      if (rawOff <= 0) {
        final firstBreak = effectiveContent.indexOf('\n\n');
        rawOff = firstBreak != -1 ? firstBreak : effectiveContent.length;
      }
      final off = rawOff.clamp(0, effectiveContent.length);
      final before = effectiveContent.substring(0, off).trimRight();
      final after = effectiveContent.substring(off).trimLeft();
      if (before.isNotEmpty && after.isNotEmpty) {
        effectiveContent = '$before\n\n$tag\n\n$after';
      } else if (before.isNotEmpty) {
        effectiveContent = '$before\n\n$tag';
      } else {
        effectiveContent = '$tag\n\n$after';
      }
    }

    if (effectiveContent.isEmpty) return const [];

    final List<Widget> widgets = [];
    int lastEnd = 0;

    for (final match in _inlineAttachmentPattern.allMatches(effectiveContent)) {
      if (match.start > lastEnd) {
        final slice = effectiveContent.substring(lastEnd, match.start).trim();
        if (slice.isNotEmpty) {
          widgets.add(ChatMarkdownBody(data: slice));
        }
      }
      final attId = (match.group(2) ?? match.group(3) ?? '').trim();
      final att = attById[attId];
      if (att != null) {
        widgets.add(
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: _AttachmentCard(
              attachment: att,
              viewModel: widget.viewModel,
            ),
          ),
        );
      }
      lastEnd = match.end;
    }

    if (lastEnd < effectiveContent.length) {
      final remaining = effectiveContent.substring(lastEnd).trim();
      if (remaining.isNotEmpty) {
        widgets.add(ChatMarkdownBody(data: remaining));
      }
    }

    return widgets;
  }
}

class _ToolCallBadge extends StatelessWidget {
  const _ToolCallBadge({required this.toolCall});

  final ToolCallItem toolCall;

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;
    final isDone = toolCall.result != null;
    final isMcp = toolCall.name.startsWith('mcp__');

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: spec.headerColor.withValues(alpha: 0.7),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: isDone
              ? spec.accentColor.withValues(alpha: 0.5)
              : spec.borderColor,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            isMcp ? Icons.extension_rounded : Icons.handyman_outlined,
            size: 13,
            color: spec.accentColor,
          ),
          const SizedBox(width: 6),
          Text(
            toolCall.name,
            style: TextStyle(
              color: spec.textColor,
              fontSize: 11,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(width: 6),
          Icon(
            isDone ? Icons.check_circle_outline_rounded : Icons.sync_rounded,
            size: 13,
            color: isDone ? const Color(0xFF22C55E) : spec.subtextColor,
          ),
        ],
      ),
    );
  }
}

class _AttachmentCard extends StatelessWidget {
  const _AttachmentCard({
    required this.attachment,
    required this.viewModel,
  });

  final AttachmentRef attachment;
  final ChatViewModel viewModel;

  Future<void> _downloadAttachment(BuildContext context) async {
    final messenger = ScaffoldMessenger.maybeOf(context);
    try {
      final bytes = await viewModel.downloadAttachmentBytes(attachment.id);
      final savePath = await FilePicker.platform.saveFile(
        dialogTitle: 'Enregistrer la pièce jointe',
        fileName: attachment.filename,
        bytes: bytes,
      );
      if (savePath == null || savePath.isEmpty) return;

      final file = File(savePath);
      if (!await file.exists() || await file.length() == 0) {
        await file.writeAsBytes(bytes);
      }
      messenger?.showSnackBar(
        SnackBar(
          content: Text('Fichier enregistré : $savePath'),
          behavior: SnackBarBehavior.floating,
        ),
      );
    } catch (e) {
      messenger?.showSnackBar(
        SnackBar(
          content: Text('Erreur lors du téléchargement : $e'),
          backgroundColor: const Color(0xFFEF4444),
          behavior: SnackBarBehavior.floating,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;

    if (attachment.isImage && !viewModel.isOfflineDemo) {
      final imageUrl = viewModel.buildAttachmentUrl(attachment.id);
      return ClipRRect(
        borderRadius: BorderRadius.circular(10),
        child: Container(
          constraints: const BoxConstraints(maxWidth: 360, maxHeight: 280),
          decoration: BoxDecoration(
            border: Border.all(color: spec.borderColor),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Stack(
            children: [
              Image.network(
                imageUrl,
                headers: {
                  'Authorization': 'Bearer ${viewModel.session.accessToken}',
                },
                fit: BoxFit.cover,
                errorBuilder: (_, _, _) => _buildFileChip(context, spec),
              ),
              Positioned(
                top: 8,
                right: 8,
                child: Material(
                  color: spec.surfaceColor.withValues(alpha: 0.85),
                  borderRadius: BorderRadius.circular(8),
                  child: InkWell(
                    onTap: () => _downloadAttachment(context),
                    borderRadius: BorderRadius.circular(8),
                    child: Padding(
                      padding: const EdgeInsets.all(6),
                      child: Icon(
                        Icons.download_rounded,
                        size: 16,
                        color: spec.accentColor,
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      );
    }

    return _buildFileChip(context, spec);
  }

  Widget _buildFileChip(BuildContext context, AppThemeSpec spec) {
    return InkWell(
      onTap: () => _downloadAttachment(context),
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
        decoration: BoxDecoration(
          color: spec.headerColor,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: spec.borderColor),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              attachment.isGenerated
                  ? Icons.auto_awesome_motion_rounded
                  : Icons.insert_drive_file_outlined,
              size: 15,
              color: spec.accentColor,
            ),
            const SizedBox(width: 6),
            Text(
              attachment.filename,
              style: TextStyle(
                color: spec.textColor,
                fontSize: 12,
                fontWeight: FontWeight.w500,
              ),
            ),
            const SizedBox(width: 8),
            Icon(
              Icons.download_rounded,
              size: 15,
              color: spec.accentColor,
            ),
          ],
        ),
      ),
    );
  }
}
