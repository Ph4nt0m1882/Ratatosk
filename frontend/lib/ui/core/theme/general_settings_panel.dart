import 'dart:convert';

import 'package:flutter/material.dart';

import '../../../data/services/ratatosk_api_client.dart';
import '../../../domain/models/app_theme_spec.dart';
import '../../../domain/models/user_session.dart';
import '../l10n/locale_controller.dart';

class GeneralSettingsPanel extends StatefulWidget {
  const GeneralSettingsPanel({
    super.key,
    required this.session,
    required this.activeThemeName,
  });

  final UserSession? session;
  final String activeThemeName;

  @override
  State<GeneralSettingsPanel> createState() => _GeneralSettingsPanelState();
}

class _GeneralSettingsPanelState extends State<GeneralSettingsPanel> {
  final RatatoskApiClient _api = RatatoskApiClient();

  bool _isLoading = false;
  String? _statusMessage;
  bool _isError = false;

  Map<String, dynamic>? _profile;
  List<Map<String, dynamic>> _mcpServers = const [];

  final TextEditingController _usernameCtrl = TextEditingController();
  final TextEditingController _emailCtrl = TextEditingController();
  final TextEditingController _passwordCtrl = TextEditingController();

  bool get _isOnline =>
      widget.session != null &&
      widget.session!.accessToken != 'demo_preview_token';

  @override
  void initState() {
    super.initState();
    _usernameCtrl.text = widget.session?.username ?? 'ratatosk';
    if (_isOnline) {
      _loadData();
    }
  }

  @override
  void dispose() {
    _usernameCtrl.dispose();
    _emailCtrl.dispose();
    _passwordCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    final session = widget.session;
    if (session == null || !_isOnline) return;
    setState(() {
      _isLoading = true;
      _statusMessage = null;
    });
    try {
      final results = await Future.wait([
        _api.fetchMyProfile(session),
        _api.listMcpServers(session),
      ]);
      if (!mounted) return;
      final prof = results[0] as Map<String, dynamic>;
      final servers = results[1] as List<Map<String, dynamic>>;
      setState(() {
        _profile = prof;
        _mcpServers = servers;
        _usernameCtrl.text = (prof['username'] as String?) ?? session.username;
        _emailCtrl.text = (prof['email'] as String?) ?? '';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isError = true;
        _statusMessage = e.toString().replaceFirst('Exception: ', '');
      });
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _saveProfile() async {
    final session = widget.session;
    if (session == null || !_isOnline) return;

    final patch = <String, dynamic>{};
    final newUsername = _usernameCtrl.text.trim();
    final newEmail = _emailCtrl.text.trim();
    final newPass = _passwordCtrl.text;

    if (newUsername.isNotEmpty) patch['username'] = newUsername;
    patch['email'] = newEmail.isEmpty ? null : newEmail;
    if (newPass.isNotEmpty) patch['password'] = newPass;

    try {
      final updated = await _api.updateMyProfile(session, patch);
      if (!mounted) return;
      _passwordCtrl.clear();
      setState(() {
        _profile = updated;
        _isError = false;
        _statusMessage = 'Profil mis à jour avec succès.';
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isError = true;
        _statusMessage = e.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  Future<void> _toggleMcpActive(Map<String, dynamic> server) async {
    final session = widget.session;
    if (session == null || !_isOnline) return;
    final id = server['id'] as String;
    final current = (server['is_active'] as bool?) ?? true;
    try {
      await _api.updateMcpServer(session, id, {'is_active': !current});
      await _loadData();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isError = true;
        _statusMessage = e.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  Future<void> _deleteMcpServer(String serverId) async {
    final session = widget.session;
    if (session == null || !_isOnline) return;
    try {
      await _api.deleteMcpServer(session, serverId);
      await _loadData();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isError = true;
        _statusMessage = e.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  Future<void> _showAddMcpDialog() async {
    final session = widget.session;
    if (session == null || !_isOnline) return;

    final nameCtrl = TextEditingController();
    final cmdCtrl = TextEditingController();
    final argsCtrl = TextEditingController();
    String transport = 'stdio';

    final created = await showDialog<bool>(
      context: context,
      builder: (ctx) {
        final spec = ctx.appTheme;
        return StatefulBuilder(
          builder: (ctx, setDialogState) {
            return AlertDialog(
              backgroundColor: spec.surfaceColor,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(14),
                side: BorderSide(color: spec.borderColor),
              ),
              title: Text(
                'Ajouter un serveur MCP',
                style: TextStyle(
                  color: spec.textColor,
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                ),
              ),
              content: SizedBox(
                width: 420,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    _DialogField(
                      controller: nameCtrl,
                      label: 'Nom du serveur (ex: filesystem)',
                    ),
                    const SizedBox(height: 10),
                    DropdownButtonFormField<String>(
                      initialValue: transport,
                      dropdownColor: spec.surfaceColor,
                      style: TextStyle(color: spec.textColor, fontSize: 13),
                      decoration: InputDecoration(
                        labelText: 'Transport',
                        labelStyle: TextStyle(
                          color: spec.subtextColor,
                          fontSize: 12,
                        ),
                        isDense: true,
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(8),
                        ),
                      ),
                      items: const [
                        DropdownMenuItem(value: 'stdio', child: Text('STDIO (Commande locale)')),
                        DropdownMenuItem(value: 'sse', child: Text('SSE (URL distante)')),
                        DropdownMenuItem(value: 'http', child: Text('HTTP (Streamable HTTP)')),
                      ],
                      onChanged: (v) {
                        if (v != null) setDialogState(() => transport = v);
                      },
                    ),
                    const SizedBox(height: 10),
                    _DialogField(
                      controller: cmdCtrl,
                      label: transport == 'stdio'
                          ? 'Commande (ex: npx, uvx, docker)'
                          : 'URL (ex: http://localhost:3001/sse)',
                    ),
                    if (transport == 'stdio') ...[
                      const SizedBox(height: 10),
                      _DialogField(
                        controller: argsCtrl,
                        label: 'Arguments séparés par des espaces (optionnel)',
                      ),
                    ],
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(ctx).pop(false),
                  child: Text(
                    'Annuler',
                    style: TextStyle(color: spec.subtextColor),
                  ),
                ),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: spec.accentColor,
                    foregroundColor: Colors.white,
                  ),
                  onPressed: () async {
                    final name = nameCtrl.text.trim();
                    final cmd = cmdCtrl.text.trim();
                    if (name.isEmpty || cmd.isEmpty) return;
                    final args = argsCtrl.text
                        .trim()
                        .split(RegExp(r'\s+'))
                        .where((s) => s.isNotEmpty)
                        .toList();
                    await _api.createMcpServer(session, {
                      'name': name,
                      'transport': transport,
                      'command_or_url': cmd,
                      'args': args,
                      'is_active': true,
                      'is_global': false,
                    });
                    if (ctx.mounted) Navigator.of(ctx).pop(true);
                  },
                  child: const Text('Ajouter'),
                ),
              ],
            );
          },
        );
      },
    );

    if (created == true) {
      await _loadData();
    }
  }

  Future<void> _showImportMcpJsonDialog() async {
    final session = widget.session;
    if (session == null || !_isOnline) return;
    final jsonCtrl = TextEditingController();

    final imported = await showDialog<bool>(
      context: context,
      builder: (ctx) {
        final spec = ctx.appTheme;
        return AlertDialog(
          backgroundColor: spec.surfaceColor,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
            side: BorderSide(color: spec.borderColor),
          ),
          title: Text(
            'Importer une configuration JSON MCP',
            style: TextStyle(
              color: spec.textColor,
              fontSize: 16,
              fontWeight: FontWeight.w700,
            ),
          ),
          content: SizedBox(
            width: 480,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Collez un bloc JSON au format Claude Desktop, Cursor ou VS Code ({"mcpServers": {...}}) :',
                  style: TextStyle(color: spec.subtextColor, fontSize: 12),
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: jsonCtrl,
                  maxLines: 8,
                  style: TextStyle(
                    color: spec.textColor,
                    fontSize: 12,
                    fontFamily: 'monospace',
                  ),
                  decoration: InputDecoration(
                    hintText:
                        '{\n  "mcpServers": {\n    "memory": {\n      "command": "npx",\n      "args": ["-y", "@modelcontextprotocol/server-memory"]\n    }\n  }\n}',
                    hintStyle: TextStyle(
                      color: spec.subtextColor.withValues(alpha: 0.6),
                      fontSize: 11.5,
                    ),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(false),
              child: Text('Annuler', style: TextStyle(color: spec.subtextColor)),
            ),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: spec.accentColor,
                foregroundColor: Colors.white,
              ),
              onPressed: () async {
                final raw = jsonCtrl.text.trim();
                if (raw.isEmpty) return;
                final parsed = jsonDecode(raw) as Map<String, dynamic>;
                await _api.importMcpServers(session, parsed, isGlobal: false);
                if (ctx.mounted) Navigator.of(ctx).pop(true);
              },
              child: const Text('Importer'),
            ),
          ],
        );
      },
    );

    if (imported == true) {
      await _loadData();
    }
  }

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;
    final l10n = context.l10n;
    final localeCtrl = LocaleControllerScope.maybeOf(context);
    final currentLang = localeCtrl?.locale.languageCode ?? 'en';
    final username = (_profile?['username'] as String?) ??
        widget.session?.username ??
        'ratatosk';
    final serverUrl = widget.session?.serverUrl ?? 'http://127.0.0.1:8000';
    final isAdmin =
        (_profile?['is_admin'] as bool?) ?? widget.session?.isAdmin ?? false;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    l10n.generalSectionTitle,
                    style: TextStyle(
                      color: spec.textColor,
                      fontSize: 21,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    l10n.generalSectionSubtitle,
                    style: TextStyle(color: spec.subtextColor, fontSize: 13),
                  ),
                ],
              ),
            ),
            if (_isOnline)
              IconButton(
                tooltip: l10n.commonRefresh,
                onPressed: _isLoading ? null : _loadData,
                icon: Icon(
                  Icons.refresh_rounded,
                  size: 19,
                  color: spec.subtextColor,
                ),
              ),
          ],
        ),
        if (_statusMessage != null) ...[
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: (_isError ? Colors.redAccent : Colors.green).withValues(
                alpha: 0.14,
              ),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: (_isError ? Colors.redAccent : Colors.green).withValues(
                  alpha: 0.45,
                ),
              ),
            ),
            child: Text(
              _statusMessage!,
              style: TextStyle(
                color: _isError ? Colors.redAccent : Colors.greenAccent,
                fontSize: 12,
              ),
            ),
          ),
        ],
        const SizedBox(height: 20),

        // 1. Session, Language & Profile Card
        Text(
          l10n.generalAccountHeader,
          style: TextStyle(
            color: spec.textColor,
            fontSize: 14,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 10),
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: spec.headerColor.withValues(alpha: 0.55),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: spec.borderColor),
          ),
          child: Column(
            children: [
              if (localeCtrl != null) ...[
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      l10n.languageLabel,
                      style: TextStyle(color: spec.subtextColor, fontSize: 13),
                    ),
                    SegmentedButton<String>(
                      showSelectedIcon: false,
                      style: SegmentedButton.styleFrom(
                        visualDensity: VisualDensity.compact,
                      ),
                      segments: [
                        ButtonSegment<String>(
                          value: 'en',
                          label: Text(l10n.languageEnglish),
                        ),
                        ButtonSegment<String>(
                          value: 'fr',
                          label: Text(l10n.languageFrench),
                        ),
                      ],
                      selected: {currentLang},
                      onSelectionChanged: (sel) {
                        localeCtrl.setLocale(Locale(sel.first));
                      },
                    ),
                  ],
                ),
                Divider(color: spec.borderColor, height: 20),
              ],
              _InfoRow(label: l10n.generalConnectedUser, value: username),
              Divider(color: spec.borderColor, height: 20),
              _InfoRow(
                label: l10n.generalRoleLabel,
                value: isAdmin
                    ? l10n.generalRoleAdmin
                    : l10n.generalRoleStandard,
              ),
              Divider(color: spec.borderColor, height: 20),
              _InfoRow(label: l10n.generalBackendServer, value: serverUrl),
              Divider(color: spec.borderColor, height: 20),
              _InfoRow(
                label: l10n.generalActiveTheme,
                value: widget.activeThemeName,
              ),
              if (_isOnline) ...[
                Divider(color: spec.borderColor, height: 24),
                Row(
                  children: [
                    Expanded(
                      child: _DialogField(
                        controller: _usernameCtrl,
                        label: l10n.generalUsernameField,
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: _DialogField(
                        controller: _emailCtrl,
                        label: l10n.generalEmailField,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: _DialogField(
                        controller: _passwordCtrl,
                        label: l10n.generalPasswordField,
                        obscureText: true,
                      ),
                    ),
                    const SizedBox(width: 10),
                    ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: spec.accentColor,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(
                          horizontal: 14,
                          vertical: 12,
                        ),
                      ),
                      onPressed: _saveProfile,
                      icon: const Icon(Icons.save_outlined, size: 16),
                      label: Text(l10n.generalUpdateButton),
                    ),
                  ],
                ),
              ],
            ],
          ),
        ),

        const SizedBox(height: 24),

        // 2. Personal MCP Servers
        Row(
          children: [
            Expanded(
              child: Text(
                l10n.generalMcpHeader(_mcpServers.length),
                style: TextStyle(
                  color: spec.textColor,
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            if (_isOnline) ...[
              OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                  foregroundColor: spec.textColor,
                  side: BorderSide(color: spec.borderColor),
                ),
                onPressed: _showImportMcpJsonDialog,
                icon: const Icon(Icons.code_rounded, size: 16),
                label: Text(
                  l10n.generalMcpImportJson,
                  style: const TextStyle(fontSize: 12),
                ),
              ),
              const SizedBox(width: 8),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: spec.accentColor,
                  foregroundColor: Colors.white,
                ),
                onPressed: _showAddMcpDialog,
                icon: const Icon(Icons.add_rounded, size: 16),
                label: Text(
                  l10n.generalMcpAdd,
                  style: const TextStyle(fontSize: 12),
                ),
              ),
            ],
          ],
        ),
        const SizedBox(height: 10),
        if (_mcpServers.isEmpty)
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: spec.headerColor.withValues(alpha: 0.4),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: spec.borderColor),
            ),
            child: Text(
              l10n.generalMcpEmpty,
              style: TextStyle(color: spec.subtextColor, fontSize: 12.5),
            ),
          )
        else
          ..._mcpServers.map((srv) {
            final id = srv['id'] as String? ?? '';
            final name = srv['name'] as String? ?? id;
            final transport = (srv['transport'] as String? ?? 'stdio').toUpperCase();
            final cmd = srv['command_or_url'] as String? ?? '';
            final isGlobal = (srv['is_global'] as bool?) ?? false;
            final isActive = (srv['is_active'] as bool?) ?? true;
            final canEdit = !isGlobal || isAdmin;

            return Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: spec.headerColor.withValues(alpha: 0.45),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: spec.borderColor),
              ),
              child: Row(
                children: [
                  Icon(
                    Icons.extension_rounded,
                    size: 18,
                    color: isActive ? spec.accentColor : spec.subtextColor,
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Text(
                              name,
                              style: TextStyle(
                                color: spec.textColor,
                                fontSize: 13,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const SizedBox(width: 6),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 6,
                                vertical: 1.5,
                              ),
                              decoration: BoxDecoration(
                                color: spec.accentColor.withValues(alpha: 0.14),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                isGlobal ? '$transport • GLOBAL' : transport,
                                style: TextStyle(
                                  color: spec.accentColor,
                                  fontSize: 10,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 2),
                        Text(
                          cmd,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            color: spec.subtextColor,
                            fontSize: 11,
                            fontFamily: 'monospace',
                          ),
                        ),
                      ],
                    ),
                  ),
                  if (canEdit) ...[
                    Switch(
                      value: isActive,
                      activeThumbColor: spec.accentColor,
                      onChanged: (_) => _toggleMcpActive(srv),
                    ),
                    IconButton(
                      tooltip: 'Supprimer',
                      onPressed: () => _deleteMcpServer(id),
                      icon: Icon(
                        Icons.delete_outline_rounded,
                        size: 18,
                        color: spec.subtextColor,
                      ),
                    ),
                  ],
                ],
              ),
            );
          }),
      ],
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: TextStyle(color: spec.subtextColor, fontSize: 13)),
        Text(
          value,
          style: TextStyle(
            color: spec.textColor,
            fontSize: 13,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}

class _DialogField extends StatelessWidget {
  const _DialogField({
    required this.controller,
    required this.label,
    this.obscureText = false,
  });

  final TextEditingController controller;
  final String label;
  final bool obscureText;

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;
    return TextField(
      controller: controller,
      obscureText: obscureText,
      style: TextStyle(color: spec.textColor, fontSize: 13),
      decoration: InputDecoration(
        labelText: label,
        labelStyle: TextStyle(color: spec.subtextColor, fontSize: 12),
        isDense: true,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: BorderSide(color: spec.borderColor),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: BorderSide(color: spec.borderColor),
        ),
      ),
    );
  }
}
