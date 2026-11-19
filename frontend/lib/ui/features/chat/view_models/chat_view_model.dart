import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../../../data/repositories/chat_repository.dart';
import '../../../../domain/models/chat_models.dart';
import '../../../../domain/models/user_session.dart';

class ChatViewModel extends ChangeNotifier {
  ChatViewModel({
    required this._chatRepository,
    required this.session,
  });

  static const String _kFavoriteModelsKey = 'ratatosk_favorite_models';
  static const String _kSelectedModelKey = 'ratatosk_selected_model';

  final ChatRepository _chatRepository;
  final UserSession session;

  List<ModelInfoModel> _models = const [];
  List<ModelInfoModel> get models => _models;

  final Set<String> _favoriteModelIds = <String>{};
  Set<String> get favoriteModelIds => Set.unmodifiable(_favoriteModelIds);

  String _selectedModelId = 'gemini-4-carbon';
  String get selectedModelId => _selectedModelId;

  List<ConversationSummary> _conversations = const [];
  List<ConversationSummary> get conversations => _conversations;

  String? _activeConversationId;
  String? get activeConversationId => _activeConversationId;

  final List<ChatMessageItem> _messages = [];
  List<ChatMessageItem> get messages => List.unmodifiable(_messages);

  final List<AttachmentRef> _pendingAttachments = [];
  List<AttachmentRef> get pendingAttachments =>
      List.unmodifiable(_pendingAttachments);

  String _searchMode = 'search'; // 'no_search', 'search', 'full_search'
  String get searchMode => _searchMode;

  String _historyMode = 'eco'; // 'eco', 'auto', 'full', 'fixed', 'none'
  String get historyMode => _historyMode;

  bool _isStreaming = false;
  bool get isStreaming => _isStreaming;

  bool _isLoadingSidebar = false;
  bool get isLoadingSidebar => _isLoadingSidebar;

  String? _errorBanner;
  String? get errorBanner => _errorBanner;

  bool get isOfflineDemo => session.accessToken == 'demo_preview_token';

  bool isFavoriteModel(String modelId) => _favoriteModelIds.contains(modelId);

  Future<void> toggleFavoriteModel(String modelId) async {
    if (_favoriteModelIds.contains(modelId)) {
      _favoriteModelIds.remove(modelId);
    } else {
      _favoriteModelIds.add(modelId);
    }
    notifyListeners();
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setStringList(
        _kFavoriteModelsKey,
        _favoriteModelIds.toList(),
      );
    } catch (_) {}
  }

  Future<void> _loadModelPreferences() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final favs = prefs.getStringList(_kFavoriteModelsKey);
      if (favs != null) {
        _favoriteModelIds
          ..clear()
          ..addAll(favs);
      }
      final savedModel = prefs.getString(_kSelectedModelKey);
      if (savedModel != null && savedModel.isNotEmpty) {
        _selectedModelId = savedModel;
      }
    } catch (_) {}
  }

  Future<void> initialize() async {
    _isLoadingSidebar = true;
    notifyListeners();

    await _loadModelPreferences();

    if (isOfflineDemo) {
      _models = const [
        ModelInfoModel(
          id: 'gemini-4-argon',
          provider: 'google',
          displayName: 'Gemini 4 Argon',
          icon: 'argon',
          category: 'pro',
          tasks: ['text-generation'],
          tier: 'featured',
          isRecommended: true,
          rank: 1,
        ),
        ModelInfoModel(
          id: 'gemini-4-carbon',
          provider: 'google',
          displayName: 'Gemini 4 Carbon',
          icon: 'carbon',
          category: 'flash',
          tasks: ['text-generation'],
          tier: 'featured',
          isRecommended: true,
          rank: 2,
        ),
        ModelInfoModel(
          id: 'gemini-4-hydrogen',
          provider: 'google',
          displayName: 'Gemini 4 Hydrogen',
          icon: 'hydrogen',
          category: 'flash_lite',
          tasks: ['text-generation'],
          tier: 'featured',
          isRecommended: true,
          rank: 3,
        ),
        ModelInfoModel(
          id: 'gemini-3.8-flash',
          provider: 'google',
          displayName: 'Gemini 3.8 Flash',
          category: 'flash',
          tasks: ['text-generation'],
          tier: 'featured',
          isRecommended: false,
          rank: 5,
        ),
      ];
      if (!_models.any((m) => m.id == _selectedModelId)) {
        _selectedModelId = _models.first.id;
      }
      _isLoadingSidebar = false;
      notifyListeners();
      return;
    }

    try {
      await _fetchAndApplyModels(refresh: false);
      _conversations = await _chatRepository.getConversations(session);
    } catch (e) {
      _errorBanner = e.toString().replaceFirst('Exception: ', '');
    } finally {
      _isLoadingSidebar = false;
      notifyListeners();
    }
  }

  Future<void> refreshModels({bool forceRemote = false}) async {
    if (isOfflineDemo) return;
    try {
      await _fetchAndApplyModels(refresh: forceRemote);
      notifyListeners();
    } catch (e) {
      _errorBanner = e.toString().replaceFirst('Exception: ', '');
      notifyListeners();
    }
  }

  Future<void> _fetchAndApplyModels({required bool refresh}) async {
    final fetchedModels = await _chatRepository.getModels(
      session,
      refresh: refresh,
    );
    final chatCapable = fetchedModels
        .where((m) => m.tasks.contains('text-generation'))
        .toList()
      ..sort((a, b) {
        if (a.isRecommended != b.isRecommended) {
          return a.isRecommended ? -1 : 1;
        }
        return a.rank.compareTo(b.rank);
      });
    _models = chatCapable.isNotEmpty ? chatCapable : fetchedModels;
    if (_models.isNotEmpty && !_models.any((m) => m.id == _selectedModelId)) {
      _selectedModelId = _models.first.id;
    }
  }

  void selectModel(String modelId) {
    _selectedModelId = modelId;
    notifyListeners();
    SharedPreferences.getInstance().then((prefs) {
      prefs.setString(_kSelectedModelKey, modelId);
    }).catchError((_) {});
  }

  void setSearchMode(String mode) {
    _searchMode = mode;
    notifyListeners();
  }

  void setHistoryMode(String mode) {
    _historyMode = mode;
    notifyListeners();
  }

  void startNewConversation() {
    _activeConversationId = null;
    _messages.clear();
    _pendingAttachments.clear();
    _errorBanner = null;
    notifyListeners();
  }

  Future<void> selectConversation(String conversationId) async {
    _activeConversationId = conversationId;
    _errorBanner = null;
    notifyListeners();

    if (isOfflineDemo) return;

    try {
      final history =
          await _chatRepository.getMessages(session, conversationId);
      _messages
        ..clear()
        ..addAll(history);
      notifyListeners();
    } catch (e) {
      _errorBanner = e.toString().replaceFirst('Exception: ', '');
      notifyListeners();
    }
  }

  Future<void> deleteConversation(String conversationId) async {
    if (!isOfflineDemo) {
      await _chatRepository.deleteConversation(session, conversationId);
      _conversations = await _chatRepository.getConversations(session);
    } else {
      _conversations =
          _conversations.where((c) => c.id != conversationId).toList();
    }
    if (_activeConversationId == conversationId) {
      startNewConversation();
    } else {
      notifyListeners();
    }
  }

  Future<void> uploadAndStageAttachment(
    String filename,
    Uint8List bytes,
  ) async {
    if (isOfflineDemo) {
      _pendingAttachments.add(
        AttachmentRef(
          id: 'demo_att_${DateTime.now().millisecondsSinceEpoch}',
          filename: filename,
          mimeType: 'text/plain',
        ),
      );
      notifyListeners();
      return;
    }

    try {
      final uploaded = await _chatRepository.uploadAttachment(
        session: session,
        filename: filename,
        bytes: bytes,
      );
      _pendingAttachments.add(uploaded);
      notifyListeners();
    } catch (e) {
      _errorBanner = e.toString().replaceFirst('Exception: ', '');
      notifyListeners();
    }
  }

  void removePendingAttachment(String id) {
    _pendingAttachments.removeWhere((a) => a.id == id);
    notifyListeners();
  }

  String buildAttachmentUrl(String attachmentId, {bool preview = false}) =>
      _chatRepository.buildAttachmentUrl(
        session,
        attachmentId,
        preview: preview,
      );

  Future<Uint8List> downloadAttachmentBytes(String attachmentId) =>
      _chatRepository.downloadAttachmentBytes(session, attachmentId);

  Future<void> sendMessage(String rawPrompt) async {
    final prompt = rawPrompt.trim();
    if (prompt.isEmpty || _isStreaming) return;

    final stagedAtts = List<AttachmentRef>.from(_pendingAttachments);
    _pendingAttachments.clear();
    _errorBanner = null;

    final userMsg = ChatMessageItem(
      id: 'local_user_${DateTime.now().millisecondsSinceEpoch}',
      role: 'user',
      content: prompt,
      attachments: stagedAtts,
    );

    final assistantPlaceholderId =
        'local_asst_${DateTime.now().millisecondsSinceEpoch}';
    final assistantMsg = ChatMessageItem(
      id: assistantPlaceholderId,
      role: 'assistant',
      content: '',
      model: _selectedModelId,
      isStreaming: true,
    );

    _messages.addAll([userMsg, assistantMsg]);
    _isStreaming = true;
    notifyListeners();

    if (isOfflineDemo) {
      await _runOfflineDemoStream(prompt, assistantPlaceholderId);
      return;
    }

    try {
      final stream = _chatRepository.streamChat(
        session: session,
        model: _selectedModelId,
        conversationId: _activeConversationId,
        historyMode: _historyMode,
        searchMode: _searchMode,
        messages: [
          {
            'role': 'user',
            'content': prompt,
            'attachments': stagedAtts
                .map((a) => {'id': a.id, 'filename': a.filename})
                .toList(),
          },
        ],
      );

      await for (final frame in stream) {
        _applyStreamFrame(assistantPlaceholderId, frame.event, frame.data);
      }
      _conversations = await _chatRepository.getConversations(session);
    } catch (e) {
      _updateAssistantMessage(
        assistantPlaceholderId,
        (curr) => curr.copyWith(
          isStreaming: false,
          error: e.toString().replaceFirst('Exception: ', ''),
        ),
      );
    } finally {
      _isStreaming = false;
      _updateAssistantMessage(
        assistantPlaceholderId,
        (curr) => curr.copyWith(isStreaming: false),
      );
      notifyListeners();
    }
  }

  void _applyStreamFrame(
    String targetId,
    String event,
    Map<String, dynamic> data,
  ) {
    switch (event) {
      case 'thinking':
        final delta = (data['delta'] ?? '') as String;
        _updateAssistantMessage(
          targetId,
          (curr) => curr.copyWith(thinking: curr.thinking + delta),
        );
      case 'text':
        final delta = (data['delta'] ?? '') as String;
        _updateAssistantMessage(
          targetId,
          (curr) => curr.copyWith(content: curr.content + delta),
        );
      case 'tool_call':
        final call = ToolCallItem(
          id: data['id'] as String?,
          name: (data['name'] ?? '') as String,
          args: Map<String, dynamic>.from((data['args'] as Map?) ?? const {}),
        );
        _updateAssistantMessage(
          targetId,
          (curr) => curr.copyWith(toolCalls: [...curr.toolCalls, call]),
        );
      case 'tool_result':
        final callId = data['id'] as String?;
        final callName = data['name'] as String?;
        final result = Map<String, dynamic>.from(
          (data['result'] as Map?) ?? const {},
        );
        _updateAssistantMessage(targetId, (curr) {
          final updated = List<ToolCallItem>.from(curr.toolCalls);
          final idx = updated.lastIndexWhere(
            (c) =>
                (callId != null && c.id == callId) ||
                (c.name == callName && c.result == null),
          );
          if (idx != -1) {
            updated[idx] = updated[idx].copyWith(result: result);
          }
          return curr.copyWith(toolCalls: updated);
        });
      case 'image_progress':
        final prog = ImageProgressState.fromJson(data);
        _updateAssistantMessage(
          targetId,
          (curr) => curr.copyWith(imageProgress: prog),
        );
      case 'attachment':
        final att = AttachmentRef.fromJson(data);
        _updateAssistantMessage(
          targetId,
          (curr) => curr.copyWith(attachments: [...curr.attachments, att]),
        );
      case 'sources':
        final rawItems = data['items'] as List<dynamic>? ?? const [];
        final sources = rawItems
            .whereType<Map<String, dynamic>>()
            .map(SourceItemModel.fromJson)
            .toList();
        _updateAssistantMessage(
          targetId,
          (curr) => curr.copyWith(sources: sources),
        );
      case 'done':
        final convId = data['conversation_id'] as String?;
        if (convId != null && convId.isNotEmpty) {
          _activeConversationId = convId;
        }
        final usageMap = data['usage'] as Map<String, dynamic>?;
        final usage =
            usageMap != null ? MessageUsageInfo.fromJson(usageMap) : null;
        _updateAssistantMessage(
          targetId,
          (curr) => curr.copyWith(
            isStreaming: false,
            model: (data['model'] as String?) ?? curr.model,
            usage: usage,
          ),
        );
      case 'error':
        final msg = (data['message'] ?? 'Erreur inconnue') as String;
        _updateAssistantMessage(
          targetId,
          (curr) => curr.copyWith(isStreaming: false, error: msg),
        );
    }
  }

  void _updateAssistantMessage(
    String targetId,
    ChatMessageItem Function(ChatMessageItem current) updater,
  ) {
    final idx = _messages.indexWhere((m) => m.id == targetId);
    if (idx == -1) return;
    _messages[idx] = updater(_messages[idx]);
    notifyListeners();
  }

  Future<void> _runOfflineDemoStream(String prompt, String targetId) async {
    await Future<void>.delayed(const Duration(milliseconds: 220));
    _applyStreamFrame(targetId, 'thinking', {
      'delta': 'Analyse de la requête "$prompt" et sélection des outils Kornak / Cross-Delegation...',
    });

    final wantsImage = prompt.toLowerCase().contains('image') ||
        prompt.toLowerCase().contains('dessin') ||
        prompt.toLowerCase().contains('affiche');

    if (wantsImage) {
      await Future<void>.delayed(const Duration(milliseconds: 350));
      _applyStreamFrame(targetId, 'tool_call', {
        'id': 'demo_call_1',
        'name': 'generate_image',
        'args': {
          'prompt': prompt,
          'model': 'gemini-3.1-flash-image',
          'aspect_ratio': '16:9',
        },
      });
      for (final (step, prog, status) in [
        (1, 0.35, 'Débruitage latent — Étape 1/3 (basses fréquences)...'),
        (2, 0.65, 'Débruitage latent — Étape 2/3 (structures & couleurs)...'),
        (3, 0.90, 'Débruitage latent — Étape 3/3 (détails fins)...'),
        (4, 1.00, 'Image générée avec Nano Banana 2.'),
      ]) {
        await Future<void>.delayed(const Duration(milliseconds: 420));
        _applyStreamFrame(targetId, 'image_progress', {
          'step': step,
          'total_steps': 4,
          'progress': prog,
          'model': 'gemini-3.1-flash-image',
          'status': status,
        });
      }
      _applyStreamFrame(targetId, 'tool_result', {
        'id': 'demo_call_1',
        'name': 'generate_image',
        'result': {
          'status': 'generated',
          'delegated_model': 'gemini-3.1-flash-image',
          'aspect_ratio': '16:9',
        },
      });
    }

    await Future<void>.delayed(const Duration(milliseconds: 250));
    _applyStreamFrame(targetId, 'text', {
      'delta':
          'Voici la réponse de **Ratatosk** en mode aperçu hors-ligne.\n\n'
          '- Thème actif, recherche (`$_searchMode`) et mode historique (`$_historyMode`) opérationnels.\n'
          '- Connectez votre backend FastAPI sur `${session.serverUrl}` pour exécuter vos vrais appels Gemini, outils MCP et Cross-Delegation.',
    });
    _applyStreamFrame(targetId, 'done', {
      'model': _selectedModelId,
      'usage': {
        'input_tokens': 42,
        'output_tokens': 68,
        'thoughts_tokens': 18,
        'cost': 0.00014,
        'currency': 'EUR',
      },
    });
    _isStreaming = false;
    notifyListeners();
  }
}
