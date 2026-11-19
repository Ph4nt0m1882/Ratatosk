import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_svg/flutter_svg.dart';

import '../../../../../domain/models/app_theme_spec.dart';
import '../../../../core/l10n/locale_controller.dart';

class ChatMarkdownBody extends StatelessWidget {
  const ChatMarkdownBody({
    super.key,
    required this.data,
    this.fontSize = 14,
  });

  final String data;
  final double fontSize;

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;
    final blocks = _parseBlocks(data);

    if (blocks.isEmpty) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (int i = 0; i < blocks.length; i++) ...[
          if (i > 0) const SizedBox(height: 10),
          _buildBlockWidget(context, spec, blocks[i]),
        ],
      ],
    );
  }

  Widget _buildBlockWidget(
    BuildContext context,
    AppThemeSpec spec,
    _MdBlock block,
  ) {
    return switch (block) {
      _MdHeading(:final level, :final text) => _MarkdownHeading(
          level: level,
          text: text,
          baseFontSize: fontSize,
        ),
      _MdDivider() => Padding(
          padding: const EdgeInsets.symmetric(vertical: 4),
          child: Divider(color: spec.borderColor, height: 1),
        ),
      _MdCodeBlock(:final language, :final code) => _MarkdownCodeBlock(
          language: language,
          code: code,
        ),
      _MdBlockquote(:final lines) => _MarkdownBlockquote(
          text: lines.join('\n'),
          fontSize: fontSize,
        ),
      _MdList(:final items) => _MarkdownListBlock(
          items: items,
          fontSize: fontSize,
        ),
      _MdTable(:final headers, :final rows) => _MarkdownTableBlock(
          headers: headers,
          rows: rows,
          fontSize: fontSize,
        ),
      _MdParagraph(:final text) => _MarkdownRichText(
          text: text,
          fontSize: fontSize,
        ),
    };
  }

  static final RegExp _fenceOpenRegex = RegExp(r'^(`{3,4})(.*)$');
  static final RegExp _headingRegex = RegExp(r'^(#{1,6})\s+(.*)$');
  static final RegExp _hrRegex = RegExp(r'^\s*([-*_])\s*\1\s*\1[\s\-*_]*$');
  static final RegExp _listItemRegex =
      RegExp(r'^(\s*)(?:([-*+])|(\d+)\.)\s+(.*)$');
  static final RegExp _tableSepRegex =
      RegExp(r'^\s*\|?(\s*:?-{2,}:?\s*\|)+\s*:?-{2,}:?\s*\|?\s*$');

  List<_MdBlock> _parseBlocks(String raw) {
    final lines = raw.replaceAll('\r\n', '\n').split('\n');
    final List<_MdBlock> blocks = [];
    int i = 0;

    while (i < lines.length) {
      final line = lines[i];
      final trimmed = line.trim();

      if (trimmed.isEmpty) {
        i++;
        continue;
      }

      // 1. Fenced code block (``` or ````)
      final fenceMatch = _fenceOpenRegex.firstMatch(trimmed);
      if (fenceMatch != null) {
        final fenceTicks = fenceMatch.group(1)!;
        final lang = fenceMatch.group(2)!.trim();
        final codeLines = <String>[];
        i++;
        while (i < lines.length) {
          if (lines[i].trim().startsWith(fenceTicks)) {
            i++;
            break;
          }
          codeLines.add(lines[i]);
          i++;
        }
        blocks.add(_MdCodeBlock(language: lang, code: codeLines.join('\n')));
        continue;
      }

      // 2. Horizontal rule (---, ***, ___)
      if (_hrRegex.hasMatch(trimmed)) {
        blocks.add(const _MdDivider());
        i++;
        continue;
      }

      // 3. Heading (# .. ######)
      final headingMatch = _headingRegex.firstMatch(trimmed);
      if (headingMatch != null) {
        blocks.add(
          _MdHeading(
            level: headingMatch.group(1)!.length,
            text: headingMatch.group(2)!.trim(),
          ),
        );
        i++;
        continue;
      }

      // 4. Blockquote (> ...)
      if (trimmed.startsWith('>')) {
        final quoteLines = <String>[];
        while (i < lines.length && lines[i].trim().startsWith('>')) {
          quoteLines.add(
            lines[i].trim().replaceFirst(RegExp(r'^>\s?'), ''),
          );
          i++;
        }
        blocks.add(_MdBlockquote(lines: quoteLines));
        continue;
      }

      // 5. Markdown Table
      if (trimmed.contains('|') &&
          i + 1 < lines.length &&
          _tableSepRegex.hasMatch(lines[i + 1])) {
        final headers = _splitTableRow(lines[i]);
        i += 2; // skip header + separator
        final rows = <List<String>>[];
        while (i < lines.length &&
            lines[i].trim().isNotEmpty &&
            lines[i].contains('|')) {
          rows.add(_splitTableRow(lines[i]));
          i++;
        }
        blocks.add(_MdTable(headers: headers, rows: rows));
        continue;
      }

      // 6. Bullet or numbered list
      if (_listItemRegex.hasMatch(line)) {
        final items = <_MdListItem>[];
        while (i < lines.length) {
          final match = _listItemRegex.firstMatch(lines[i]);
          if (match == null) break;
          final indent = (match.group(1)?.length ?? 0) ~/ 2;
          final numberPrefix = match.group(3);
          final itemText = match.group(4)!.trim();
          items.add(
            _MdListItem(
              indent: indent,
              numberPrefix: numberPrefix,
              text: itemText,
            ),
          );
          i++;
        }
        blocks.add(_MdList(items: items));
        continue;
      }

      // 7. Standard paragraph
      final paraLines = <String>[];
      while (i < lines.length) {
        final cur = lines[i];
        final curTrim = cur.trim();
        if (curTrim.isEmpty ||
            _fenceOpenRegex.hasMatch(curTrim) ||
            _hrRegex.hasMatch(curTrim) ||
            _headingRegex.hasMatch(curTrim) ||
            curTrim.startsWith('>') ||
            _listItemRegex.hasMatch(cur) ||
            (curTrim.contains('|') &&
                i + 1 < lines.length &&
                _tableSepRegex.hasMatch(lines[i + 1]))) {
          break;
        }
        paraLines.add(cur);
        i++;
      }
      if (paraLines.isNotEmpty) {
        blocks.add(_MdParagraph(text: paraLines.join('\n')));
      } else {
        i++;
      }
    }

    return blocks;
  }

  List<String> _splitTableRow(String row) {
    var clean = row.trim();
    if (clean.startsWith('|')) clean = clean.substring(1);
    if (clean.endsWith('|')) clean = clean.substring(0, clean.length - 1);
    return clean.split('|').map((c) => c.trim()).toList();
  }
}

sealed class _MdBlock {
  const _MdBlock();
}

class _MdHeading extends _MdBlock {
  const _MdHeading({required this.level, required this.text});
  final int level;
  final String text;
}

class _MdDivider extends _MdBlock {
  const _MdDivider();
}

class _MdCodeBlock extends _MdBlock {
  const _MdCodeBlock({required this.language, required this.code});
  final String language;
  final String code;
}

class _MdBlockquote extends _MdBlock {
  const _MdBlockquote({required this.lines});
  final List<String> lines;
}

class _MdListItem {
  const _MdListItem({
    required this.indent,
    required this.numberPrefix,
    required this.text,
  });
  final int indent;
  final String? numberPrefix;
  final String text;
}

class _MdList extends _MdBlock {
  const _MdList({required this.items});
  final List<_MdListItem> items;
}

class _MdTable extends _MdBlock {
  const _MdTable({required this.headers, required this.rows});
  final List<String> headers;
  final List<List<String>> rows;
}

class _MdParagraph extends _MdBlock {
  const _MdParagraph({required this.text});
  final String text;
}

class _MarkdownHeading extends StatelessWidget {
  const _MarkdownHeading({
    required this.level,
    required this.text,
    required this.baseFontSize,
  });

  final int level;
  final String text;
  final double baseFontSize;

  @override
  Widget build(BuildContext context) {
    final scale = switch (level) {
      1 => 1.42,
      2 => 1.26,
      3 => 1.14,
      _ => 1.05,
    };
    return Padding(
      padding: const EdgeInsets.only(top: 4),
      child: _MarkdownRichText(
        text: text,
        fontSize: baseFontSize * scale,
        baseWeight: FontWeight.w700,
      ),
    );
  }
}

class _MarkdownBlockquote extends StatelessWidget {
  const _MarkdownBlockquote({
    required this.text,
    required this.fontSize,
  });

  final String text;
  final double fontSize;

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: spec.headerColor.withValues(alpha: 0.45),
        borderRadius: const BorderRadius.only(
          topRight: Radius.circular(8),
          bottomRight: Radius.circular(8),
        ),
        border: Border(
          left: BorderSide(color: spec.accentColor, width: 3.5),
        ),
      ),
      child: _MarkdownRichText(
        text: text,
        fontSize: fontSize,
        textColor: spec.subtextColor,
      ),
    );
  }
}

class _MarkdownListBlock extends StatelessWidget {
  const _MarkdownListBlock({
    required this.items,
    required this.fontSize,
  });

  final List<_MdListItem> items;
  final double fontSize;

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (int i = 0; i < items.length; i++) ...[
          if (i > 0) const SizedBox(height: 5),
          Padding(
            padding: EdgeInsets.only(left: items[i].indent * 16.0),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SizedBox(
                  width: items[i].numberPrefix != null ? 24 : 16,
                  child: Text(
                    items[i].numberPrefix != null
                        ? '${items[i].numberPrefix}.'
                        : '•',
                    style: TextStyle(
                      color: spec.accentColor,
                      fontSize: fontSize,
                      fontWeight: FontWeight.w700,
                      height: 1.5,
                    ),
                  ),
                ),
                Expanded(
                  child: _MarkdownRichText(
                    text: items[i].text,
                    fontSize: fontSize,
                  ),
                ),
              ],
            ),
          ),
        ],
      ],
    );
  }
}

class _MarkdownCodeBlock extends StatefulWidget {
  const _MarkdownCodeBlock({
    required this.language,
    required this.code,
  });

  final String language;
  final String code;

  @override
  State<_MarkdownCodeBlock> createState() => _MarkdownCodeBlockState();
}

class _MarkdownCodeBlockState extends State<_MarkdownCodeBlock> {
  bool _copied = false;

  static final RegExp _tokenRegex = RegExp(
    r'"""[\s\S]*?"""'
    r"|'''[\s\S]*?'''"
    r'|"(?:\\.|[^"\\])*"'
    r"|'(?:\\.|[^'\\])*'"
    r'|//[^\n]*'
    r'|/\*[\s\S]*?\*/'
    r'|#[^\n]*'
    r'|--[^\n]*'
    r'|@[A-Za-z_]\w*'
    r'|\b(?:def|class|return|if|elif|else|for|while|in|import|from|as|try|except|finally|raise|with|async|await|yield|lambda|pass|break|continue|and|or|not|is|True|False|None|const|final|var|let|function|void|int|double|bool|String|List|Map|Set|Future|Stream|required|late|extension|enum|sealed|switch|case|default|new|throw|catch|fn|pub|impl|struct|match|mut|use|SELECT|FROM|WHERE|INSERT|UPDATE|DELETE|JOIN|ORDER|BY|GROUP|LIMIT)\b'
    r'|\b(?:self|this|super|print|len|range|enumerate|zip|map|filter|dict|list|set|tuple|str|float|isinstance|getattr|setattr|hasattr|__name__|__init__|__main__)\b'
    r'|\b[A-Za-z_]\w*(?=\s*\()'
    r'|\b(?:0x[0-9A-Fa-f]+|\d+(?:\.\d+)?)\b',
  );

  static const Set<String> _keywords = {
    'def', 'class', 'return', 'if', 'elif', 'else', 'for', 'while', 'in',
    'import', 'from', 'as', 'try', 'except', 'finally', 'raise', 'with',
    'async', 'await', 'yield', 'lambda', 'pass', 'break', 'continue',
    'and', 'or', 'not', 'is', 'True', 'False', 'None', 'const', 'final',
    'var', 'let', 'function', 'void', 'int', 'double', 'bool', 'String',
    'List', 'Map', 'Set', 'Future', 'Stream', 'required', 'late',
    'extension', 'enum', 'sealed', 'switch', 'case', 'default', 'new',
    'throw', 'catch', 'fn', 'pub', 'impl', 'struct', 'match', 'mut', 'use',
    'SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE', 'JOIN',
    'ORDER', 'BY', 'GROUP', 'LIMIT',
  };

  static const Set<String> _builtins = {
    'self', 'this', 'super', 'print', 'len', 'range', 'enumerate', 'zip',
    'map', 'filter', 'dict', 'list', 'set', 'tuple', 'str', 'float',
    'isinstance', 'getattr', 'setattr', 'hasattr', '__name__', '__init__',
    '__main__',
  };

  Future<void> _copyCode() async {
    await Clipboard.setData(ClipboardData(text: widget.code));
    if (!mounted) return;
    setState(() => _copied = true);
    await Future<void>.delayed(const Duration(seconds: 2));
    if (mounted) {
      setState(() => _copied = false);
    }
  }

  static const String _pythonSvg = '''
<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path fill="#3776AB" d="M11.9 2C7.8 2 8.1 3.8 8.1 3.8v2h3.9v.6H6.5S4 6.1 4 10.2c0 4.1 2.2 3.9 2.2 3.9h1.3v-1.9s-.1-2.2 2.2-2.2h3.8s2.1 0 2.1-2v-3.9S16 2 11.9 2zm-2.1 1.2c.4 0 .7.3.7.7s-.3.7-.7.7-.7-.3-.7-.7.3-.7.7-.7z"/>
  <path fill="#FFD43B" d="M12.1 22c4.1 0 3.8-1.8 3.8-1.8v-2H12v-.6h5.5S20 17.9 20 13.8c0-4.1-2.2-3.9-2.2-3.9h-1.3v1.9s.1 2.2-2.2 2.2h-3.8s-2.1 0-2.1 2v3.9S8 22 12.1 22zm2.1-1.2c-.4 0-.7-.3-.7-.7s.3-.7.7-.7.7.3.7.7-.3.7-.7.7z"/>
</svg>''';

  static const String _dartSvg = '''
<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path fill="#01579B" d="M4.8 4.8L10.2 2l9.8 9.8v7.6l-2.6 2.6H9.8L2 14.2l2.8-9.4z"/>
  <path fill="#40C4FF" d="M10.2 2l9.8 9.8h-7.6L4.8 4.2 10.2 2z"/>
  <path fill="#29B6F6" d="M4.8 4.8l7.6 7.6v7.6L4.8 12.4V4.8z"/>
</svg>''';

  static const String _jsSvg = '''
<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <rect x="2" y="2" width="20" height="20" rx="3" fill="#F7DF1E"/>
  <path fill="#000000" d="M12.4 17.6c0 1.6-.9 2.4-2.3 2.4-1.2 0-1.9-.6-2.3-1.4l1.3-.8c.2.5.5.8 1 .8.5 0 .8-.2.8-1v-5.4h1.5v5.4zm4.8 2.4c-1.5 0-2.5-.7-3-1.7l1.3-.8c.3.6.8 1 1.6 1 .7 0 1.1-.3 1.1-.8 0-.6-.4-.8-1.3-1.2l-.5-.2c-1.3-.5-2.1-1.2-2.1-2.6 0-1.3 1-2.3 2.5-2.3 1.1 0 1.9.4 2.4 1.3l-1.3.8c-.3-.5-.6-.7-1.1-.7-.5 0-.8.3-.8.7 0 .5.3.7 1.1 1l.5.2c1.5.6 2.3 1.3 2.3 2.7 0 1.6-1.2 2.4-2.7 2.4z"/>
</svg>''';

  static const String _tsSvg = '''
<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <rect x="2" y="2" width="20" height="20" rx="3" fill="#3178C6"/>
  <path fill="#FFFFFF" d="M13.2 12.3h-2.4V19H9.2v-6.7H6.8V11h6.4v1.3zm4.1 6.8c-1.4 0-2.4-.6-2.9-1.5l1.2-.8c.3.5.9.9 1.6.9.7 0 1.1-.3 1.1-.7 0-.5-.4-.7-1.3-1.1l-.5-.2c-1.3-.5-2-1.1-2-2.4 0-1.2 1-2.2 2.5-2.2 1.1 0 1.9.4 2.4 1.2l-1.2.8c-.3-.4-.7-.7-1.2-.7-.5 0-.9.3-.9.7 0 .5.3.7 1.1 1l.5.2c1.4.6 2.2 1.2 2.2 2.5 0 1.5-1.2 2.3-2.8 2.3z"/>
</svg>''';

  static const String _htmlSvg = '''
<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path fill="#E34F26" d="M4 2l1.5 17L12 22l6.5-3L20 2H4zm13.1 5.5H9.1l.2 2.2h7.6l-.6 6.6-4.3 1.2-4.3-1.2-.3-3.4h2.1l.2 1.7 2.3.6 2.3-.6.2-2.7H7.5L6.9 5.3h10.4l-.2 2.2z"/>
</svg>''';

  static const String _cssSvg = '''
<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path fill="#1572B6" d="M4 2l1.5 17L12 22l6.5-3L20 2H4zm12.9 14.3L12 17.7l-4.9-1.4-.3-3.4h2.1l.2 1.7 2.9.8 2.9-.8.3-2.9H9.5l-.2-2.1h6.1l.2-2.1H7.1L6.9 5.3h10.2l-.2 11z"/>
</svg>''';

  static const String _jsonSvg = '''
<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path fill="#F59E0B" d="M8 4C6.3 4 5 5.3 5 7v2.5c0 1-.8 1.5-2 1.5v2c1.2 0 2 .5 2 1.5V17c0 1.7 1.3 3 3 3h1v-2H8c-.6 0-1-.4-1-1v-2.5c0-1.2-.6-2-1.6-2.5 1-.5 1.6-1.3 1.6-2.5V7c0-.6.4-1 1-1h1V4H8zm8 0h-1v2h1c.6 0 1 .4 1 1v2.5c0 1.2.6 2 1.6 2.5-1 .5-1.6 1.3-1.6 2.5V17c0 .6-.4 1-1 1h-1v2h1c1.7 0 3-1.3 3-3v-2.5c0-1 .8-1.5 2-1.5v-2c-1.2 0-2-.5-2-1.5V7c0-1.7-1.3-3-3-3z"/>
</svg>''';

  static const String _bashSvg = '''
<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <rect x="2" y="3" width="20" height="18" rx="3" fill="#27272A" stroke="#4ADE80" stroke-width="1.5"/>
  <path fill="#4ADE80" d="M6.5 8.5L10.5 12l-4 3.5-1.2-1.3L8 12 5.3 9.8l1.2-1.3zm5.5 6h6v1.8h-6v-1.8z"/>
</svg>''';

  static const String _sqlSvg = '''
<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <ellipse cx="12" cy="5.5" rx="7.5" ry="3" fill="#38BDF8"/>
  <path fill="#0284C7" d="M4.5 5.5v4.5c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3V5.5c0 1.7-3.4 3-7.5 3s-7.5-1.3-7.5-3zm0 6.5v4.5c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3V12c0 1.7-3.4 3-7.5 3s-7.5-1.3-7.5-3z"/>
</svg>''';

  static const String _rustSvg = '''
<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <circle cx="12" cy="12" r="9" fill="#EA580C"/>
  <path fill="#FFFFFF" d="M8.5 8h4.2c1.8 0 2.8.9 2.8 2.3 0 1-.6 1.8-1.6 2.1l2.1 3.6h-2.1l-1.8-3.3h-1.7V16H8.5V8zm1.9 1.6v1.8h2c.7 0 1.1-.3 1.1-.9s-.4-.9-1.1-.9h-2z"/>
</svg>''';

  static const String _mdSvg = '''
<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <rect x="2" y="4" width="20" height="16" rx="2.5" fill="#3B82F6"/>
  <path fill="#FFFFFF" d="M5 15V9h2l2 2.5L11 9h2v6h-2v-3.4l-2 2.5-2-2.5V15H5zm11.5 0l-2.5-3h1.7V9h1.6v3H19l-2.5 3z"/>
</svg>''';

  (Widget, String) _languageBadge(AppThemeSpec spec) {
    final raw = widget.language.trim().toLowerCase();
    final primary = raw.split(RegExp(r'\s+')).first;
    final label = raw.isEmpty ? 'code' : raw;

    final String? svgData = switch (primary) {
      'python' || 'py' => _pythonSvg,
      'dart' || 'flutter' => _dartSvg,
      'javascript' || 'js' => _jsSvg,
      'typescript' || 'ts' => _tsSvg,
      'html' || 'xml' || 'svg' => _htmlSvg,
      'css' || 'scss' => _cssSvg,
      'json' || 'yaml' || 'yml' || 'toml' => _jsonSvg,
      'bash' || 'sh' || 'zsh' || 'shell' => _bashSvg,
      'sql' || 'sqlite' || 'postgres' => _sqlSvg,
      'rust' || 'rs' => _rustSvg,
      'markdown' || 'md' => _mdSvg,
      _ => null,
    };

    if (svgData != null) {
      return (
        SvgPicture.string(svgData, width: 16, height: 16),
        label,
      );
    }

    return (
      Icon(Icons.code_rounded, size: 15, color: spec.accentColor),
      label,
    );
  }

  List<TextSpan> _buildHighlightedSpans(AppThemeSpec spec, TextStyle baseStyle) {
    final isDark = spec.brightness == Brightness.dark;
    final commentColor =
        isDark ? const Color(0xFF6A9955) : const Color(0xFF3F7D3B);
    final stringColor =
        isDark ? const Color(0xFFCE9178) : const Color(0xFFA31515);
    final keywordColor =
        isDark ? const Color(0xFFC586C0) : const Color(0xFF7C3AED);
    final builtinColor =
        isDark ? const Color(0xFF4EC9B0) : const Color(0xFF0F766E);
    final fnColor =
        isDark ? const Color(0xFFDCDCAA) : const Color(0xFF92400E);
    final numberColor =
        isDark ? const Color(0xFFB5CEA8) : const Color(0xFF098658);

    final spans = <TextSpan>[];
    final src = widget.code;
    int lastEnd = 0;

    for (final match in _tokenRegex.allMatches(src)) {
      if (match.start > lastEnd) {
        spans.add(TextSpan(text: src.substring(lastEnd, match.start)));
      }
      final token = match.group(0)!;
      TextStyle tokenStyle = baseStyle;

      if (token.startsWith('#') ||
          token.startsWith('//') ||
          token.startsWith('/*') ||
          token.startsWith('--')) {
        tokenStyle = baseStyle.copyWith(
          color: commentColor,
          fontStyle: FontStyle.italic,
        );
      } else if (token.startsWith('"') || token.startsWith("'")) {
        tokenStyle = baseStyle.copyWith(color: stringColor);
      } else if (token.startsWith('@')) {
        tokenStyle = baseStyle.copyWith(
          color: fnColor,
          fontWeight: FontWeight.w600,
        );
      } else if (_keywords.contains(token)) {
        tokenStyle = baseStyle.copyWith(
          color: keywordColor,
          fontWeight: FontWeight.w700,
        );
      } else if (_builtins.contains(token)) {
        tokenStyle = baseStyle.copyWith(color: builtinColor);
      } else if (RegExp(r'^(?:0x|\d)').hasMatch(token)) {
        tokenStyle = baseStyle.copyWith(color: numberColor);
      } else {
        tokenStyle = baseStyle.copyWith(
          color: fnColor,
          fontWeight: FontWeight.w600,
        );
      }

      spans.add(TextSpan(text: token, style: tokenStyle));
      lastEnd = match.end;
    }

    if (lastEnd < src.length) {
      spans.add(TextSpan(text: src.substring(lastEnd)));
    }
    return spans;
  }

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;
    final (langIconWidget, langLabel) = _languageBadge(spec);
    final baseCodeStyle = TextStyle(
      color: spec.textColor,
      fontSize: 12.5,
      height: 1.45,
      fontFamily: 'monospace',
    );

    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: spec.backgroundColor.withValues(alpha: 0.85),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: spec.borderColor),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            color: spec.headerColor,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    langIconWidget,
                    const SizedBox(width: 7),
                    Text(
                      langLabel,
                      style: TextStyle(
                        color: spec.textColor,
                        fontSize: 11.5,
                        fontWeight: FontWeight.w700,
                        fontFamily: 'monospace',
                      ),
                    ),
                  ],
                ),
                InkWell(
                  onTap: _copyCode,
                  borderRadius: BorderRadius.circular(6),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 6,
                      vertical: 2,
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          _copied ? Icons.check_rounded : Icons.copy_rounded,
                          size: 13,
                          color: _copied
                              ? const Color(0xFF22C55E)
                              : spec.accentColor,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          _copied
                              ? context.l10n.msgCopiedCode
                              : context.l10n.msgCopyCode,
                          style: TextStyle(
                            color: _copied
                                ? const Color(0xFF22C55E)
                                : spec.subtextColor,
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.all(12),
            child: SelectableText.rich(
              TextSpan(
                style: baseCodeStyle,
                children: _buildHighlightedSpans(spec, baseCodeStyle),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _MarkdownTableBlock extends StatelessWidget {
  const _MarkdownTableBlock({
    required this.headers,
    required this.rows,
    required this.fontSize,
  });

  final List<String> headers;
  final List<List<String>> rows;
  final double fontSize;

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;
    final colCount = headers.isNotEmpty ? headers.length : 1;

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: spec.borderColor),
        ),
        clipBehavior: Clip.antiAlias,
        child: Table(
          defaultColumnWidth: const IntrinsicColumnWidth(),
          border: TableBorder.symmetric(
            inside: BorderSide(color: spec.borderColor),
          ),
          children: [
            TableRow(
              decoration: BoxDecoration(color: spec.headerColor),
              children: List.generate(colCount, (c) {
                final cell = c < headers.length ? headers[c] : '';
                return Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 8,
                  ),
                  child: _MarkdownRichText(
                    text: cell,
                    fontSize: fontSize - 1,
                    baseWeight: FontWeight.w700,
                  ),
                );
              }),
            ),
            for (final row in rows)
              TableRow(
                children: List.generate(colCount, (c) {
                  final cell = c < row.length ? row[c] : '';
                  return Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 8,
                    ),
                    child: _MarkdownRichText(
                      text: cell,
                      fontSize: fontSize - 1,
                    ),
                  );
                }),
              ),
          ],
        ),
      ),
    );
  }
}

class _MarkdownRichText extends StatelessWidget {
  const _MarkdownRichText({
    required this.text,
    required this.fontSize,
    this.baseWeight = FontWeight.normal,
    this.textColor,
  });

  final String text;
  final double fontSize;
  final FontWeight baseWeight;
  final Color? textColor;

  static final RegExp _inlineRegex = RegExp(
    r'`([^`]+)`'
    r'|\*\*\*([^*]+)\*\*\*'
    r'|\*\*([^*]+)\*\*'
    r'|__([^_]+)__'
    r'|\*([^*\n]+)\*'
    r'|~~([^~]+)~~'
    r'|\[([^\]]+)\]\(([^)]+)\)',
  );

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;
    final baseStyle = TextStyle(
      color: textColor ?? spec.textColor,
      fontSize: fontSize,
      fontWeight: baseWeight,
      height: 1.5,
    );

    return SelectableText.rich(
      TextSpan(
        style: baseStyle,
        children: _parseInlineSpans(text, spec, baseStyle),
      ),
    );
  }

  List<InlineSpan> _parseInlineSpans(
    String input,
    AppThemeSpec spec,
    TextStyle baseStyle,
  ) {
    final spans = <InlineSpan>[];
    int lastEnd = 0;

    for (final match in _inlineRegex.allMatches(input)) {
      if (match.start > lastEnd) {
        spans.add(TextSpan(text: input.substring(lastEnd, match.start)));
      }

      if (match.group(1) != null) {
        // Inline `code`
        spans.add(
          TextSpan(
            text: match.group(1),
            style: baseStyle.copyWith(
              fontFamily: 'monospace',
              fontSize: fontSize * 0.92,
              color: spec.accentColor,
              backgroundColor: spec.headerColor,
            ),
          ),
        );
      } else if (match.group(2) != null) {
        // ***bold italic***
        spans.add(
          TextSpan(
            text: match.group(2),
            style: baseStyle.copyWith(
              fontWeight: FontWeight.w700,
              fontStyle: FontStyle.italic,
            ),
          ),
        );
      } else if (match.group(3) != null || match.group(4) != null) {
        // **bold** or __bold__
        spans.add(
          TextSpan(
            text: match.group(3) ?? match.group(4),
            style: baseStyle.copyWith(fontWeight: FontWeight.w700),
          ),
        );
      } else if (match.group(5) != null) {
        // *italic*
        spans.add(
          TextSpan(
            text: match.group(5),
            style: baseStyle.copyWith(fontStyle: FontStyle.italic),
          ),
        );
      } else if (match.group(6) != null) {
        // ~~strikethrough~~
        spans.add(
          TextSpan(
            text: match.group(6),
            style: baseStyle.copyWith(decoration: TextDecoration.lineThrough),
          ),
        );
      } else if (match.group(7) != null) {
        // [label](url)
        spans.add(
          TextSpan(
            text: match.group(7),
            style: baseStyle.copyWith(
              color: spec.accentColor,
              fontWeight: FontWeight.w600,
              decoration: TextDecoration.underline,
              decorationColor: spec.accentColor,
            ),
          ),
        );
      }

      lastEnd = match.end;
    }

    if (lastEnd < input.length) {
      spans.add(TextSpan(text: input.substring(lastEnd)));
    }

    return spans;
  }
}
