import 'dart:convert';

import 'package:flutter/material.dart';

import '../../../data/services/ratatosk_api_client.dart';
import '../../../domain/models/app_theme_spec.dart';
import '../../../domain/models/user_session.dart';
import '../l10n/locale_controller.dart';

enum _AdminSubTab {
  systemPrompts,
  serverSettings,
  users,
  globalMcp,
}

class AdminSettingsPanel extends StatefulWidget {
  const AdminSettingsPanel({
    super.key,
    required this.session,
  });

  final UserSession? session;

  @override
  State<AdminSettingsPanel> createState() => _AdminSettingsPanelState();
}

class _AdminSettingsPanelState extends State<AdminSettingsPanel> {
  final RatatoskApiClient _api = RatatoskApiClient();
  _AdminSubTab _activeTab = _AdminSubTab.systemPrompts;

  bool _isLoading = false;
  String? _statusMessage;
  bool _isError = false;

  // 1. System prompts state
  List<Map<String, dynamic>> _systemPrompts = const [];

  // 2. Dynamic server settings state
  List<String> _currencies = const ['USD', 'EUR', 'GBP'];
  final TextEditingController _agentNameCtrl =
      TextEditingController(text: 'Ratatosk');
  String _selectedCurrency = 'USD';
  final TextEditingController _accessExpireCtrl =
      TextEditingController(text: '15');
  final TextEditingController _refreshExpireCtrl =
      TextEditingController(text: '15');
  bool _keepGeneratedAttachments = true;
  final TextEditingController _retentionDeleteCtrl =
      TextEditingController(text: '7');
  bool _expireOnArchive = false;
  final TextEditingController _retentionArchiveCtrl =
      TextEditingController(text: '30');

  // 3. Users state
  List<Map<String, dynamic>> _users = const [];

  // 4. Global MCP state
  List<Map<String, dynamic>> _allMcpServers = const [];

  bool get _isAdmin => widget.session?.isAdmin ?? false;
  bool get _isOnline =>
      widget.session != null &&
      widget.session!.accessToken != 'demo_preview_token';

  @override
  void initState() {
    super.initState();
    if (_isOnline && _isAdmin) {
      _loadAllAdminData();
    }
  }

  @override
  void dispose() {
    _agentNameCtrl.dispose();
    _accessExpireCtrl.dispose();
    _refreshExpireCtrl.dispose();
    _retentionDeleteCtrl.dispose();
    _retentionArchiveCtrl.dispose();
    super.dispose();
  }

  void _setFeedback(String message, {bool isError = false}) {
    if (!mounted) return;
    setState(() {
      _statusMessage = message;
      _isError = isError;
    });
  }

  Future<void> _loadAllAdminData() async {
    final session = widget.session;
    if (session == null || !_isOnline || !_isAdmin) return;
    setState(() {
      _isLoading = true;
      _statusMessage = null;
    });
    try {
      final results = await Future.wait([
        _api.listSystemPrompts(session),
        _api.getServerSettings(session),
        _api.getSupportedCurrencies(session),
        _api.listUsers(session),
        _api.listMcpServers(session, allUsers: true),
      ]);
      if (!mounted) return;

      final prompts = (results[0] as List<Map<String, dynamic>>)..sort((a, b) {
          final ha = (a['hierarchy'] as num?)?.toInt() ?? 0;
          final hb = (b['hierarchy'] as num?)?.toInt() ?? 0;
          return ha.compareTo(hb);
        });
      final srvSettings = results[1] as Map<String, dynamic>;
      final currencies = results[2] as List<String>;
      final users = results[3] as List<Map<String, dynamic>>;
      final mcpList = results[4] as List<Map<String, dynamic>>;

      setState(() {
        _systemPrompts = prompts;
        _currencies = currencies.isNotEmpty ? currencies : const ['USD', 'EUR'];
        _applyServerSettingsToControllers(srvSettings);
        _users = users;
        _allMcpServers = mcpList;
      });
    } catch (e) {
      _setFeedback(
        e.toString().replaceFirst('Exception: ', ''),
        isError: true,
      );
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  void _applyServerSettingsToControllers(Map<String, dynamic> data) {
    _agentNameCtrl.text = (data['agent_name'] as String?) ?? 'Ratatosk';
    final cur = (data['currency'] as String?) ?? 'USD';
    _selectedCurrency = _currencies.contains(cur) ? cur : _currencies.first;
    _accessExpireCtrl.text =
        ((data['access_token_expire_minutes'] as num?)?.toInt() ?? 15)
            .toString();
    _refreshExpireCtrl.text =
        ((data['refresh_token_expire_days'] as num?)?.toInt() ?? 15).toString();
    _keepGeneratedAttachments =
        (data['keep_generated_attachments'] as bool?) ?? true;
    _retentionDeleteCtrl.text =
        ((data['attachment_retention_days_on_delete'] as num?)?.toInt() ?? 7)
            .toString();
    _expireOnArchive =
        (data['expire_attachments_on_archive'] as bool?) ?? false;
    _retentionArchiveCtrl.text =
        ((data['attachment_retention_days_on_archive'] as num?)?.toInt() ?? 30)
            .toString();
  }

  // ==================== SYSTEM PROMPTS ACTIONS ====================

  Future<void> _togglePromptActive(Map<String, dynamic> prompt) async {
    final session = widget.session;
    if (session == null || !_isOnline) return;
    final id = prompt['id'] as String;
    final current = (prompt['is_active'] as bool?) ?? true;
    try {
      await _api.updateSystemPrompt(session, id, {'is_active': !current});
      await _loadAllAdminData();
    } catch (e) {
      _setFeedback(e.toString().replaceFirst('Exception: ', ''), isError: true);
    }
  }

  Future<void> _resetSinglePrompt(String id) async {
    final session = widget.session;
    if (session == null || !_isOnline) return;
    try {
      await _api.resetSystemPrompt(session, id);
      _setFeedback('System Prompt réinitialisé à sa valeur d\'origine.');
      await _loadAllAdminData();
    } catch (e) {
      _setFeedback(e.toString().replaceFirst('Exception: ', ''), isError: true);
    }
  }

  Future<void> _resetAllPrompts() async {
    final session = widget.session;
    if (session == null || !_isOnline) return;
    try {
      await _api.resetAllSystemPrompts(session);
      _setFeedback('Tous les System Prompts par défaut ont été réinitialisés.');
      await _loadAllAdminData();
    } catch (e) {
      _setFeedback(e.toString().replaceFirst('Exception: ', ''), isError: true);
    }
  }

  Future<void> _deletePrompt(String id) async {
    final session = widget.session;
    if (session == null || !_isOnline) return;
    try {
      await _api.deleteSystemPrompt(session, id);
      _setFeedback('System Prompt supprimé.');
      await _loadAllAdminData();
    } catch (e) {
      _setFeedback(e.toString().replaceFirst('Exception: ', ''), isError: true);
    }
  }

  Future<void> _openPromptEditor({Map<String, dynamic>? existingMeta}) async {
    final session = widget.session;
    if (session == null || !_isOnline) return;

    Map<String, dynamic>? fullPrompt;
    if (existingMeta != null) {
      try {
        fullPrompt = await _api.getSystemPrompt(
          session,
          existingMeta['id'] as String,
        );
      } catch (e) {
        _setFeedback(
          e.toString().replaceFirst('Exception: ', ''),
          isError: true,
        );
        return;
      }
    }

    if (!mounted) return;

    final nameCtrl = TextEditingController(
      text: (fullPrompt?['name'] as String?) ?? '',
    );
    final hierarchyCtrl = TextEditingController(
      text: ((fullPrompt?['hierarchy'] as num?)?.toInt() ?? 10).toString(),
    );
    final descCtrl = TextEditingController(
      text: (fullPrompt?['description'] as String?) ?? '',
    );
    final contentCtrl = TextEditingController(
      text: (fullPrompt?['content'] as String?) ?? '',
    );
    bool isActive = (fullPrompt?['is_active'] as bool?) ?? true;

    final saved = await showDialog<bool>(
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
                fullPrompt == null
                    ? 'Nouveau System Prompt'
                    : 'Modifier le System Prompt (${fullPrompt['name']})',
                style: TextStyle(
                  color: spec.textColor,
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                ),
              ),
              content: SizedBox(
                width: 580,
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            flex: 3,
                            child: _AdminTextField(
                              controller: nameCtrl,
                              label: 'Nom (ex: 05_CUSTOM_RULES)',
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: _AdminTextField(
                              controller: hierarchyCtrl,
                              label: 'Hiérarchie (ordre)',
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      _AdminTextField(
                        controller: descCtrl,
                        label: 'Description (optionnel)',
                      ),
                      const SizedBox(height: 10),
                      TextField(
                        controller: contentCtrl,
                        maxLines: 12,
                        style: TextStyle(
                          color: spec.textColor,
                          fontSize: 12.5,
                          fontFamily: 'monospace',
                        ),
                        decoration: InputDecoration(
                          labelText: 'Contenu du System Prompt (Markdown)',
                          alignLabelWithHint: true,
                          labelStyle: TextStyle(
                            color: spec.subtextColor,
                            fontSize: 12,
                          ),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(8),
                          ),
                        ),
                      ),
                      const SizedBox(height: 8),
                      SwitchListTile(
                        contentPadding: EdgeInsets.zero,
                        title: Text(
                          'Activer ce System Prompt',
                          style: TextStyle(color: spec.textColor, fontSize: 13),
                        ),
                        value: isActive,
                        activeThumbColor: spec.accentColor,
                        onChanged: (v) => setDialogState(() => isActive = v),
                      ),
                    ],
                  ),
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
                    final content = contentCtrl.text;
                    if (name.isEmpty || content.trim().isEmpty) return;
                    final hierarchy =
                        int.tryParse(hierarchyCtrl.text.trim()) ?? 0;
                    final desc = descCtrl.text.trim();

                    if (fullPrompt == null) {
                      await _api.createSystemPrompt(session, {
                        'name': name,
                        'hierarchy': hierarchy,
                        'description': desc.isEmpty ? null : desc,
                        'content': content,
                        'is_active': isActive,
                      });
                    } else {
                      await _api.updateSystemPrompt(
                        session,
                        fullPrompt['id'] as String,
                        {
                          'name': name,
                          'hierarchy': hierarchy,
                          'description': desc.isEmpty ? null : desc,
                          'content': content,
                          'is_active': isActive,
                        },
                      );
                    }
                    if (ctx.mounted) Navigator.of(ctx).pop(true);
                  },
                  child: const Text('Enregistrer'),
                ),
              ],
            );
          },
        );
      },
    );

    if (saved == true) {
      _setFeedback('System Prompt enregistré avec succès.');
      await _loadAllAdminData();
    }
  }

  // ==================== SERVER SETTINGS ACTIONS ====================

  Future<void> _saveServerSettings() async {
    final session = widget.session;
    if (session == null || !_isOnline) return;
    try {
      final patch = {
        'agent_name': _agentNameCtrl.text.trim().isEmpty
            ? 'Ratatosk'
            : _agentNameCtrl.text.trim(),
        'currency': _selectedCurrency,
        'access_token_expire_minutes':
            int.tryParse(_accessExpireCtrl.text.trim()) ?? 15,
        'refresh_token_expire_days':
            int.tryParse(_refreshExpireCtrl.text.trim()) ?? 15,
        'keep_generated_attachments': _keepGeneratedAttachments,
        'attachment_retention_days_on_delete':
            int.tryParse(_retentionDeleteCtrl.text.trim()) ?? 7,
        'expire_attachments_on_archive': _expireOnArchive,
        'attachment_retention_days_on_archive':
            int.tryParse(_retentionArchiveCtrl.text.trim()) ?? 30,
      };
      final updated = await _api.updateServerSettings(session, patch);
      setState(() => _applyServerSettingsToControllers(updated));
      _setFeedback('Paramètres serveur sauvegardés.');
    } catch (e) {
      _setFeedback(e.toString().replaceFirst('Exception: ', ''), isError: true);
    }
  }

  Future<void> _resetServerSettings() async {
    final session = widget.session;
    if (session == null || !_isOnline) return;
    try {
      final reset = await _api.resetServerSettings(session);
      setState(() => _applyServerSettingsToControllers(reset));
      _setFeedback('Paramètres serveur réinitialisés aux valeurs par défaut.');
    } catch (e) {
      _setFeedback(e.toString().replaceFirst('Exception: ', ''), isError: true);
    }
  }

  // ==================== USERS ACTIONS ====================

  Future<void> _openCreateUserDialog() async {
    final session = widget.session;
    if (session == null || !_isOnline) return;
    final usernameCtrl = TextEditingController();
    final emailCtrl = TextEditingController();
    final passwordCtrl = TextEditingController();
    bool isAdminRole = false;

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
                'Créer un utilisateur',
                style: TextStyle(
                  color: spec.textColor,
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                ),
              ),
              content: SizedBox(
                width: 400,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    _AdminTextField(
                      controller: usernameCtrl,
                      label: 'Nom d\'utilisateur',
                    ),
                    const SizedBox(height: 10),
                    _AdminTextField(
                      controller: emailCtrl,
                      label: 'Email (optionnel)',
                    ),
                    const SizedBox(height: 10),
                    _AdminTextField(
                      controller: passwordCtrl,
                      label: 'Mot de passe initial',
                      obscureText: true,
                    ),
                    const SizedBox(height: 8),
                    SwitchListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text(
                        'Administrateur',
                        style: TextStyle(color: spec.textColor, fontSize: 13),
                      ),
                      value: isAdminRole,
                      activeThumbColor: spec.accentColor,
                      onChanged: (v) => setDialogState(() => isAdminRole = v),
                    ),
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
                    final u = usernameCtrl.text.trim();
                    final p = passwordCtrl.text;
                    if (u.isEmpty || p.isEmpty) return;
                    final e = emailCtrl.text.trim();
                    await _api.createUser(session, {
                      'username': u,
                      'email': e.isEmpty ? null : e,
                      'password': p,
                      'is_active': true,
                      'is_admin': isAdminRole,
                    });
                    if (ctx.mounted) Navigator.of(ctx).pop(true);
                  },
                  child: const Text('Créer'),
                ),
              ],
            );
          },
        );
      },
    );

    if (created == true) {
      _setFeedback('Utilisateur créé avec succès.');
      await _loadAllAdminData();
    }
  }

  Future<void> _patchUserField(
    String userId,
    Map<String, dynamic> patch,
  ) async {
    final session = widget.session;
    if (session == null || !_isOnline) return;
    try {
      await _api.updateUser(session, userId, patch);
      await _loadAllAdminData();
    } catch (e) {
      _setFeedback(e.toString().replaceFirst('Exception: ', ''), isError: true);
    }
  }

  Future<void> _deleteUserById(String userId) async {
    final session = widget.session;
    if (session == null || !_isOnline) return;
    try {
      await _api.deleteUser(session, userId);
      _setFeedback('Utilisateur supprimé.');
      await _loadAllAdminData();
    } catch (e) {
      _setFeedback(e.toString().replaceFirst('Exception: ', ''), isError: true);
    }
  }

  // ==================== GLOBAL MCP ACTIONS ====================

  Future<void> _showImportGlobalMcpDialog() async {
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
            'Importer des serveurs MCP Globaux (JSON)',
            style: TextStyle(
              color: spec.textColor,
              fontSize: 16,
              fontWeight: FontWeight.w700,
            ),
          ),
          content: SizedBox(
            width: 480,
            child: TextField(
              controller: jsonCtrl,
              maxLines: 8,
              style: TextStyle(
                color: spec.textColor,
                fontSize: 12,
                fontFamily: 'monospace',
              ),
              decoration: InputDecoration(
                hintText: '{"mcpServers": { ... }}',
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
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
                await _api.importMcpServers(session, parsed, isGlobal: true);
                if (ctx.mounted) Navigator.of(ctx).pop(true);
              },
              child: const Text('Importer en Global'),
            ),
          ],
        );
      },
    );

    if (imported == true) {
      _setFeedback('Serveurs MCP globaux importés.');
      await _loadAllAdminData();
    }
  }

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;
    final l10n = context.l10n;

    if (!_isAdmin) {
      return Center(
        child: Text(
          l10n.adminRestricted,
          style: TextStyle(color: spec.subtextColor, fontSize: 14),
        ),
      );
    }

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
                    l10n.adminSectionTitle,
                    style: TextStyle(
                      color: spec.textColor,
                      fontSize: 21,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    l10n.adminSectionSubtitle,
                    style: TextStyle(color: spec.subtextColor, fontSize: 13),
                  ),
                ],
              ),
            ),
            if (_isOnline)
              IconButton(
                tooltip: l10n.commonRefresh,
                onPressed: _isLoading ? null : _loadAllAdminData,
                icon: Icon(
                  Icons.refresh_rounded,
                  size: 19,
                  color: spec.subtextColor,
                ),
              ),
          ],
        ),
        const SizedBox(height: 16),

        // Sub-navigation tabs
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            children: [
              _AdminTabChip(
                icon: Icons.terminal_rounded,
                label: l10n.adminTabPrompts(_systemPrompts.length),
                selected: _activeTab == _AdminSubTab.systemPrompts,
                onTap: () =>
                    setState(() => _activeTab = _AdminSubTab.systemPrompts),
              ),
              const SizedBox(width: 8),
              _AdminTabChip(
                icon: Icons.settings_suggest_rounded,
                label: l10n.adminTabServer,
                selected: _activeTab == _AdminSubTab.serverSettings,
                onTap: () =>
                    setState(() => _activeTab = _AdminSubTab.serverSettings),
              ),
              const SizedBox(width: 8),
              _AdminTabChip(
                icon: Icons.people_alt_outlined,
                label: l10n.adminTabUsers(_users.length),
                selected: _activeTab == _AdminSubTab.users,
                onTap: () => setState(() => _activeTab = _AdminSubTab.users),
              ),
              const SizedBox(width: 8),
              _AdminTabChip(
                icon: Icons.hub_outlined,
                label: l10n.adminTabGlobalMcp(_allMcpServers.length),
                selected: _activeTab == _AdminSubTab.globalMcp,
                onTap: () =>
                    setState(() => _activeTab = _AdminSubTab.globalMcp),
              ),
            ],
          ),
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

        const SizedBox(height: 18),

        if (_isLoading)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 32),
            child: Center(
              child: CircularProgressIndicator(color: spec.accentColor),
            ),
          )
        else
          switch (_activeTab) {
            _AdminSubTab.systemPrompts => _buildSystemPromptsView(spec),
            _AdminSubTab.serverSettings => _buildServerSettingsView(spec),
            _AdminSubTab.users => _buildUsersView(spec),
            _AdminSubTab.globalMcp => _buildGlobalMcpView(spec),
          },
      ],
    );
  }

  // ==================== TAB 1: SYSTEM PROMPTS ====================

  Widget _buildSystemPromptsView(AppThemeSpec spec) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                'Prompts Systèmes de l\'Orchestrateur',
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
                  foregroundColor: spec.subtextColor,
                  side: BorderSide(color: spec.borderColor),
                ),
                onPressed: _resetAllPrompts,
                icon: const Icon(Icons.restore_rounded, size: 16),
                label: const Text(
                  'Tout réinitialiser',
                  style: TextStyle(fontSize: 12),
                ),
              ),
              const SizedBox(width: 8),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: spec.accentColor,
                  foregroundColor: Colors.white,
                ),
                onPressed: () => _openPromptEditor(),
                icon: const Icon(Icons.add_rounded, size: 16),
                label: const Text(
                  'Nouveau Prompt',
                  style: TextStyle(fontSize: 12),
                ),
              ),
            ],
          ],
        ),
        const SizedBox(height: 10),
        if (_systemPrompts.isEmpty)
          Text(
            'Aucun System Prompt chargé.',
            style: TextStyle(color: spec.subtextColor, fontSize: 13),
          )
        else
          ..._systemPrompts.map((p) {
            final id = p['id'] as String? ?? '';
            final name = p['name'] as String? ?? id;
            final hierarchy = (p['hierarchy'] as num?)?.toInt() ?? 0;
            final desc = p['description'] as String?;
            final isActive = (p['is_active'] as bool?) ?? true;
            final isDefault = (p['is_default'] as bool?) ?? false;

            return Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: spec.headerColor.withValues(alpha: 0.48),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: spec.borderColor),
              ),
              child: Row(
                children: [
                  Container(
                    width: 30,
                    height: 30,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: spec.accentColor.withValues(alpha: 0.16),
                      borderRadius: BorderRadius.circular(7),
                    ),
                    child: Text(
                      '#$hierarchy',
                      style: TextStyle(
                        color: spec.accentColor,
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Flexible(
                              child: Text(
                                name,
                                style: TextStyle(
                                  color: spec.textColor,
                                  fontSize: 13.5,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 6,
                                vertical: 1.5,
                              ),
                              decoration: BoxDecoration(
                                color: (isDefault
                                        ? Colors.blueAccent
                                        : Colors.purpleAccent)
                                    .withValues(alpha: 0.16),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                isDefault ? 'Système' : 'Personnalisé',
                                style: TextStyle(
                                  color: isDefault
                                      ? Colors.lightBlueAccent
                                      : Colors.purpleAccent,
                                  fontSize: 10,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                          ],
                        ),
                        if (desc != null && desc.trim().isNotEmpty) ...[
                          const SizedBox(height: 2),
                          Text(
                            desc,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              color: spec.subtextColor,
                              fontSize: 11.5,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                  Switch(
                    value: isActive,
                    activeThumbColor: spec.accentColor,
                    onChanged: (_) => _togglePromptActive(p),
                  ),
                  IconButton(
                    tooltip: 'Modifier le contenu',
                    onPressed: () => _openPromptEditor(existingMeta: p),
                    icon: Icon(
                      Icons.edit_outlined,
                      size: 18,
                      color: spec.textColor,
                    ),
                  ),
                  if (isDefault)
                    IconButton(
                      tooltip: 'Réinitialiser ce prompt par défaut',
                      onPressed: () => _resetSinglePrompt(id),
                      icon: Icon(
                        Icons.restore_rounded,
                        size: 18,
                        color: spec.subtextColor,
                      ),
                    )
                  else
                    IconButton(
                      tooltip: 'Supprimer ce prompt',
                      onPressed: () => _deletePrompt(id),
                      icon: Icon(
                        Icons.delete_outline_rounded,
                        size: 18,
                        color: spec.subtextColor,
                      ),
                    ),
                ],
              ),
            );
          }),
      ],
    );
  }

  // ==================== TAB 2: SERVER SETTINGS ====================

  Widget _buildServerSettingsView(AppThemeSpec spec) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: spec.headerColor.withValues(alpha: 0.48),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: spec.borderColor),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                flex: 2,
                child: _AdminTextField(
                  controller: _agentNameCtrl,
                  label: 'Nom de l\'agent (agent_name)',
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: DropdownButtonFormField<String>(
                  initialValue: _selectedCurrency,
                  dropdownColor: spec.surfaceColor,
                  style: TextStyle(color: spec.textColor, fontSize: 13),
                  decoration: InputDecoration(
                    labelText: 'Devise (ISO 4217)',
                    labelStyle: TextStyle(
                      color: spec.subtextColor,
                      fontSize: 12,
                    ),
                    isDense: true,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                  items: _currencies
                      .map((c) => DropdownMenuItem(value: c, child: Text(c)))
                      .toList(),
                  onChanged: (v) {
                    if (v != null) setState(() => _selectedCurrency = v);
                  },
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _AdminTextField(
                  controller: _accessExpireCtrl,
                  label: 'Expiration Access Token (minutes)',
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _AdminTextField(
                  controller: _refreshExpireCtrl,
                  label: 'Expiration Refresh Token (jours)',
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(
              'Conserver les pièces jointes générées par l\'IA',
              style: TextStyle(color: spec.textColor, fontSize: 13),
            ),
            value: _keepGeneratedAttachments,
            activeThumbColor: spec.accentColor,
            onChanged: (v) => setState(() => _keepGeneratedAttachments = v),
          ),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: Text(
              'Expirer les pièces jointes à l\'archivage d\'une conversation',
              style: TextStyle(color: spec.textColor, fontSize: 13),
            ),
            value: _expireOnArchive,
            activeThumbColor: spec.accentColor,
            onChanged: (v) => setState(() => _expireOnArchive = v),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: _AdminTextField(
                  controller: _retentionDeleteCtrl,
                  label: 'Rétention après suppression (jours)',
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _AdminTextField(
                  controller: _retentionArchiveCtrl,
                  label: 'Rétention après archivage (jours)',
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                  foregroundColor: spec.subtextColor,
                  side: BorderSide(color: spec.borderColor),
                ),
                onPressed: _resetServerSettings,
                icon: const Icon(Icons.restore_rounded, size: 16),
                label: const Text('Valeurs par défaut'),
              ),
              const SizedBox(width: 10),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: spec.accentColor,
                  foregroundColor: Colors.white,
                ),
                onPressed: _saveServerSettings,
                icon: const Icon(Icons.save_outlined, size: 16),
                label: const Text('Enregistrer'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  // ==================== TAB 3: USERS ====================

  Widget _buildUsersView(AppThemeSpec spec) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                'Comptes Utilisateurs',
                style: TextStyle(
                  color: spec.textColor,
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            if (_isOnline)
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: spec.accentColor,
                  foregroundColor: Colors.white,
                ),
                onPressed: _openCreateUserDialog,
                icon: const Icon(Icons.person_add_alt_1_rounded, size: 16),
                label: const Text(
                  'Nouvel utilisateur',
                  style: TextStyle(fontSize: 12),
                ),
              ),
          ],
        ),
        const SizedBox(height: 10),
        ..._users.map((u) {
          final id = u['id'] as String? ?? '';
          final username = u['username'] as String? ?? '';
          final email = u['email'] as String?;
          final isActive = (u['is_active'] as bool?) ?? true;
          final isAdminUser = (u['is_admin'] as bool?) ?? false;
          final isSelf = id == widget.session?.userId;

          return Container(
            margin: const EdgeInsets.only(bottom: 8),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: spec.headerColor.withValues(alpha: 0.48),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: spec.borderColor),
            ),
            child: Row(
              children: [
                Icon(
                  isAdminUser
                      ? Icons.shield_outlined
                      : Icons.person_outline_rounded,
                  size: 19,
                  color: isAdminUser ? spec.accentColor : spec.subtextColor,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text(
                            username,
                            style: TextStyle(
                              color: spec.textColor,
                              fontSize: 13.5,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          if (isSelf) ...[
                            const SizedBox(width: 6),
                            Text(
                              '(vous)',
                              style: TextStyle(
                                color: spec.subtextColor,
                                fontSize: 11,
                              ),
                            ),
                          ],
                        ],
                      ),
                      if (email != null && email.isNotEmpty)
                        Text(
                          email,
                          style: TextStyle(
                            color: spec.subtextColor,
                            fontSize: 11.5,
                          ),
                        ),
                    ],
                  ),
                ),
                FilterChip(
                  label: const Text('Admin', style: TextStyle(fontSize: 11)),
                  selected: isAdminUser,
                  selectedColor: spec.accentColor.withValues(alpha: 0.22),
                  onSelected: isSelf
                      ? null
                      : (val) => _patchUserField(id, {'is_admin': val}),
                ),
                const SizedBox(width: 8),
                Switch(
                  value: isActive,
                  activeThumbColor: spec.accentColor,
                  onChanged: isSelf
                      ? null
                      : (val) => _patchUserField(id, {'is_active': val}),
                ),
                if (!isSelf)
                  IconButton(
                    tooltip: 'Supprimer cet utilisateur',
                    onPressed: () => _deleteUserById(id),
                    icon: Icon(
                      Icons.delete_outline_rounded,
                      size: 18,
                      color: spec.subtextColor,
                    ),
                  ),
              ],
            ),
          );
        }),
      ],
    );
  }

  // ==================== TAB 4: GLOBAL MCP ====================

  Widget _buildGlobalMcpView(AppThemeSpec spec) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                'Tous les Serveurs MCP de l\'instance',
                style: TextStyle(
                  color: spec.textColor,
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            if (_isOnline)
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(
                  backgroundColor: spec.accentColor,
                  foregroundColor: Colors.white,
                ),
                onPressed: _showImportGlobalMcpDialog,
                icon: const Icon(Icons.code_rounded, size: 16),
                label: const Text(
                  'Importer JSON Global',
                  style: TextStyle(fontSize: 12),
                ),
              ),
          ],
        ),
        const SizedBox(height: 10),
        if (_allMcpServers.isEmpty)
          Text(
            'Aucun serveur MCP enregistré sur l\'instance.',
            style: TextStyle(color: spec.subtextColor, fontSize: 13),
          )
        else
          ..._allMcpServers.map((srv) {
            final id = srv['id'] as String? ?? '';
            final name = srv['name'] as String? ?? id;
            final transport =
                (srv['transport'] as String? ?? 'stdio').toUpperCase();
            final cmd = srv['command_or_url'] as String? ?? '';
            final isGlobal = (srv['is_global'] as bool?) ?? false;
            final isActive = (srv['is_active'] as bool?) ?? true;

            return Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: spec.headerColor.withValues(alpha: 0.48),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: spec.borderColor),
              ),
              child: Row(
                children: [
                  Icon(
                    Icons.hub_outlined,
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
                                color: spec.accentColor.withValues(alpha: 0.15),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                isGlobal
                                    ? '$transport • GLOBAL'
                                    : '$transport • UTILISATEUR',
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
                  Switch(
                    value: isActive,
                    activeThumbColor: spec.accentColor,
                    onChanged: (_) async {
                      final session = widget.session;
                      if (session == null) return;
                      await _api.updateMcpServer(
                        session,
                        id,
                        {'is_active': !isActive},
                      );
                      await _loadAllAdminData();
                    },
                  ),
                  IconButton(
                    tooltip: 'Supprimer',
                    onPressed: () async {
                      final session = widget.session;
                      if (session == null) return;
                      await _api.deleteMcpServer(session, id);
                      await _loadAllAdminData();
                    },
                    icon: Icon(
                      Icons.delete_outline_rounded,
                      size: 18,
                      color: spec.subtextColor,
                    ),
                  ),
                ],
              ),
            );
          }),
      ],
    );
  }
}

class _AdminTabChip extends StatelessWidget {
  const _AdminTabChip({
    required this.icon,
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;
    return InkWell(
      borderRadius: BorderRadius.circular(8),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
        decoration: BoxDecoration(
          color: selected
              ? spec.accentColor.withValues(alpha: 0.18)
              : spec.headerColor.withValues(alpha: 0.45),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: selected
                ? spec.accentColor.withValues(alpha: 0.6)
                : spec.borderColor,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 15,
              color: selected ? spec.accentColor : spec.subtextColor,
            ),
            const SizedBox(width: 6),
            Text(
              label,
              style: TextStyle(
                color: selected ? spec.textColor : spec.subtextColor,
                fontSize: 12,
                fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _AdminTextField extends StatelessWidget {
  const _AdminTextField({
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
