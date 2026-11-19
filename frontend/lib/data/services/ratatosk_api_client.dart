import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../../domain/models/chat_models.dart';
import '../../domain/models/user_session.dart';

class SseFrame {
  const SseFrame({required this.event, required this.data});
  final String event;
  final Map<String, dynamic> data;
}

class RatatoskApiClient {
  RatatoskApiClient({http.Client? httpClient})
      : _client = httpClient ?? http.Client();

  final http.Client _client;

  String _cleanUrl(String baseUrl) =>
      baseUrl.trim().replaceAll(RegExp(r'/+$'), '');

  Map<String, String> _authHeaders(String token, {bool jsonBody = false}) => {
        'Authorization': 'Bearer $token',
        if (jsonBody) 'Content-Type': 'application/json',
      };

  Future<UserSession> login({
    required String serverUrl,
    required String username,
    required String password,
    bool rememberMe = true,
  }) async {
    final cleanBase = _cleanUrl(serverUrl);
    final loginUri = Uri.parse(
      '$cleanBase/auth/login?remember_me=$rememberMe&device_name=FlutterApp',
    );

    final loginResp = await _client.post(
      loginUri,
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: {'username': username, 'password': password},
    );

    if (loginResp.statusCode != 200) {
      String detail = 'Identifiants invalides (${loginResp.statusCode})';
      try {
        final decoded = jsonDecode(loginResp.body) as Map<String, dynamic>;
        if (decoded['detail'] != null) detail = decoded['detail'].toString();
      } catch (_) {}
      throw Exception(detail);
    }

    final tokenData = jsonDecode(loginResp.body) as Map<String, dynamic>;
    final accessToken = tokenData['access_token'] as String;

    final meUri = Uri.parse('$cleanBase/db/users/me');
    final meResp = await _client.get(
      meUri,
      headers: _authHeaders(accessToken),
    );
    if (meResp.statusCode != 200) {
      throw Exception('Impossible de récupérer le profil utilisateur.');
    }

    final meData = jsonDecode(meResp.body) as Map<String, dynamic>;
    return UserSession(
      serverUrl: cleanBase,
      accessToken: accessToken,
      userId: meData['id'] as String,
      username: meData['username'] as String,
      isAdmin: (meData['is_admin'] as bool?) ?? false,
    );
  }

  Future<List<ModelInfoModel>> fetchModels(
    UserSession session, {
    bool refresh = false,
  }) async {
    final uri = Uri.parse(
      '${session.serverUrl}/chat/models${refresh ? '?refresh=true' : ''}',
    );
    final resp = await _client.get(
      uri,
      headers: _authHeaders(session.accessToken),
    );
    if (resp.statusCode != 200) {
      throw Exception('Erreur lors du chargement des modèles (${resp.statusCode})');
    }
    final decoded = jsonDecode(resp.body) as List<dynamic>;
    return decoded
        .whereType<Map<String, dynamic>>()
        .map(ModelInfoModel.fromJson)
        .toList();
  }

  Future<List<ConversationSummary>> fetchConversations(
    UserSession session, {
    bool onlyNotArchived = true,
  }) async {
    final uri = Uri.parse(
      '${session.serverUrl}/db/conversations/list?only_not_archived=$onlyNotArchived',
    );
    final resp = await _client.get(
      uri,
      headers: _authHeaders(session.accessToken),
    );
    if (resp.statusCode != 200) return const [];
    final decoded = jsonDecode(resp.body) as List<dynamic>;
    return decoded
        .whereType<Map<String, dynamic>>()
        .map(ConversationSummary.fromJson)
        .toList();
  }

  Future<List<ChatMessageItem>> fetchMessages(
    UserSession session,
    String conversationId,
  ) async {
    final uri = Uri.parse(
      '${session.serverUrl}/db/conversations/messages'
      '?conversation_id=$conversationId&direction=before&limit=100',
    );
    final resp = await _client.get(
      uri,
      headers: _authHeaders(session.accessToken),
    );
    if (resp.statusCode != 200) return const [];
    final decoded = jsonDecode(resp.body) as List<dynamic>;
    return decoded
        .whereType<Map<String, dynamic>>()
        .map(ChatMessageItem.fromBackendJson)
        .toList();
  }

  Future<void> deleteConversation(
    UserSession session,
    String conversationId,
  ) async {
    final uri = Uri.parse(
      '${session.serverUrl}/db/conversations?conversation_id=$conversationId',
    );
    await _client.delete(uri, headers: _authHeaders(session.accessToken));
  }

  Future<AttachmentRef> uploadAttachment({
    required UserSession session,
    required String filename,
    required Uint8List bytes,
  }) async {
    final uri = Uri.parse('${session.serverUrl}/db/attachments/upload');
    final request = http.MultipartRequest('POST', uri)
      ..headers.addAll(_authHeaders(session.accessToken))
      ..files.add(
        http.MultipartFile.fromBytes(
          'file',
          bytes,
          filename: filename,
        ),
      );
    final streamed = await _client.send(request);
    final body = await streamed.stream.bytesToString();
    if (streamed.statusCode != 200) {
      throw Exception('Échec de l\'envoi de la pièce jointe (${streamed.statusCode})');
    }
    final decoded = jsonDecode(body) as Map<String, dynamic>;
    return AttachmentRef(
      id: decoded['id'] as String,
      filename: filename,
      mimeType: (decoded['mime_type'] ?? 'application/octet-stream') as String,
      isGenerated: (decoded['is_generated'] as bool?) ?? false,
    );
  }

  String buildAttachmentUrl(
    UserSession session,
    String attachmentId, {
    bool preview = false,
  }) {
    final endpoint = preview ? 'preview' : 'full';
    return '${session.serverUrl}/db/attachments/$endpoint?attachment_id=$attachmentId';
  }

  Future<Uint8List> downloadAttachmentBytes(
    UserSession session,
    String attachmentId,
  ) async {
    final uri = Uri.parse(buildAttachmentUrl(session, attachmentId));
    final resp = await _client.get(
      uri,
      headers: _authHeaders(session.accessToken),
    );
    if (resp.statusCode != 200) {
      throw Exception(
        'Échec du téléchargement de la pièce jointe (${resp.statusCode})',
      );
    }
    return resp.bodyBytes;
  }

  Stream<SseFrame> streamChat({
    required UserSession session,
    required String model,
    required List<Map<String, dynamic>> messages,
    String? conversationId,
    String historyMode = 'eco',
    String searchMode = 'search',
    double temperature = 0.7,
    bool enableBuiltinTools = true,
    List<String> unlockedTools = const [],
  }) async* {
    final uri = Uri.parse('${session.serverUrl}/chat/stream');
    final request = http.Request('POST', uri)
      ..headers.addAll(_authHeaders(session.accessToken, jsonBody: true))
      ..body = jsonEncode({
        'model': model,
        'messages': messages,
        'conversation_id': conversationId,
        'history_mode': historyMode,
        'search_mode': searchMode,
        'temperature': temperature,
        'enable_builtin_tools': enableBuiltinTools,
        'unlocked_tools': unlockedTools,
      });

    final response = await _client.send(request);
    if (response.statusCode != 200) {
      final errBody = await response.stream.bytesToString();
      throw Exception('Erreur stream (${response.statusCode}): $errBody');
    }

    String currentEvent = 'message';
    final lines = response.stream
        .transform(utf8.decoder)
        .transform(const LineSplitter());

    await for (final rawLine in lines) {
      final line = rawLine.trimRight();
      if (line.isEmpty) continue;
      if (line.startsWith('event:')) {
        currentEvent = line.substring(6).trim();
      } else if (line.startsWith('data:')) {
        final dataStr = line.substring(5).trim();
        if (dataStr.isEmpty) continue;
        try {
          final parsed = jsonDecode(dataStr) as Map<String, dynamic>;
          final resolvedEvent = (parsed['type'] as String?) ?? currentEvent;
          yield SseFrame(event: resolvedEvent, data: parsed);
        } catch (_) {
          // Ignore non-JSON keepalive lines
        }
      }
    }
  }

  // ==================== USERS & PROFILE ====================

  Future<Map<String, dynamic>> fetchMyProfile(UserSession session) async {
    final uri = Uri.parse('${session.serverUrl}/db/users/me');
    final resp = await _client.get(
      uri,
      headers: _authHeaders(session.accessToken),
    );
    if (resp.statusCode != 200) {
      throw Exception('Erreur lecture profil (${resp.statusCode})');
    }
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> updateMyProfile(
    UserSession session,
    Map<String, dynamic> patch,
  ) async {
    final uri = Uri.parse('${session.serverUrl}/db/users/me');
    final resp = await _client.patch(
      uri,
      headers: _authHeaders(session.accessToken, jsonBody: true),
      body: jsonEncode(patch),
    );
    if (resp.statusCode < 200 || resp.statusCode >= 300) {
      throw Exception('Erreur mise à jour profil (${resp.statusCode}): ${resp.body}');
    }
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> listUsers(UserSession session) async {
    final uri = Uri.parse('${session.serverUrl}/db/users/list');
    final resp = await _client.get(
      uri,
      headers: _authHeaders(session.accessToken),
    );
    if (resp.statusCode != 200) {
      throw Exception('Erreur chargement utilisateurs (${resp.statusCode})');
    }
    final decoded = jsonDecode(resp.body) as List<dynamic>;
    return decoded.whereType<Map<String, dynamic>>().toList();
  }

  Future<Map<String, dynamic>> createUser(
    UserSession session,
    Map<String, dynamic> payload,
  ) async {
    final uri = Uri.parse('${session.serverUrl}/db/users');
    final resp = await _client.post(
      uri,
      headers: _authHeaders(session.accessToken, jsonBody: true),
      body: jsonEncode(payload),
    );
    if (resp.statusCode < 200 || resp.statusCode >= 300) {
      throw Exception('Erreur création utilisateur (${resp.statusCode}): ${resp.body}');
    }
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> updateUser(
    UserSession session,
    String userId,
    Map<String, dynamic> patch,
  ) async {
    final uri = Uri.parse(
      '${session.serverUrl}/db/users?id=${Uri.encodeQueryComponent(userId)}',
    );
    final resp = await _client.patch(
      uri,
      headers: _authHeaders(session.accessToken, jsonBody: true),
      body: jsonEncode(patch),
    );
    if (resp.statusCode < 200 || resp.statusCode >= 300) {
      throw Exception('Erreur modification utilisateur (${resp.statusCode}): ${resp.body}');
    }
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<void> deleteUser(UserSession session, String userId) async {
    final uri = Uri.parse(
      '${session.serverUrl}/db/users?id=${Uri.encodeQueryComponent(userId)}',
    );
    final resp = await _client.delete(
      uri,
      headers: _authHeaders(session.accessToken),
    );
    if (resp.statusCode < 200 || resp.statusCode >= 300) {
      throw Exception('Erreur suppression utilisateur (${resp.statusCode}): ${resp.body}');
    }
  }

  // ==================== MCP SERVERS ====================

  Future<List<Map<String, dynamic>>> listMcpServers(
    UserSession session, {
    bool allUsers = false,
  }) async {
    final uri = Uri.parse(
      '${session.serverUrl}/db/mcp/list?all_users=$allUsers',
    );
    final resp = await _client.get(
      uri,
      headers: _authHeaders(session.accessToken),
    );
    if (resp.statusCode != 200) {
      throw Exception('Erreur chargement serveurs MCP (${resp.statusCode})');
    }
    final decoded = jsonDecode(resp.body) as List<dynamic>;
    return decoded.whereType<Map<String, dynamic>>().toList();
  }

  Future<Map<String, dynamic>> createMcpServer(
    UserSession session,
    Map<String, dynamic> payload,
  ) async {
    final uri = Uri.parse('${session.serverUrl}/db/mcp');
    final resp = await _client.post(
      uri,
      headers: _authHeaders(session.accessToken, jsonBody: true),
      body: jsonEncode(payload),
    );
    if (resp.statusCode < 200 || resp.statusCode >= 300) {
      throw Exception('Erreur ajout serveur MCP (${resp.statusCode}): ${resp.body}');
    }
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> importMcpServers(
    UserSession session,
    Map<String, dynamic> config, {
    bool isGlobal = false,
  }) async {
    final uri = Uri.parse('${session.serverUrl}/db/mcp/import');
    final resp = await _client.post(
      uri,
      headers: _authHeaders(session.accessToken, jsonBody: true),
      body: jsonEncode({
        'config': config,
        'is_global': isGlobal,
        'overwrite_existing': true,
      }),
    );
    if (resp.statusCode < 200 || resp.statusCode >= 300) {
      throw Exception('Erreur import JSON MCP (${resp.statusCode}): ${resp.body}');
    }
    final decoded = jsonDecode(resp.body) as List<dynamic>;
    return decoded.whereType<Map<String, dynamic>>().toList();
  }

  Future<Map<String, dynamic>> updateMcpServer(
    UserSession session,
    String serverId,
    Map<String, dynamic> patch,
  ) async {
    final uri = Uri.parse(
      '${session.serverUrl}/db/mcp?server_id=${Uri.encodeQueryComponent(serverId)}',
    );
    final resp = await _client.patch(
      uri,
      headers: _authHeaders(session.accessToken, jsonBody: true),
      body: jsonEncode(patch),
    );
    if (resp.statusCode < 200 || resp.statusCode >= 300) {
      throw Exception('Erreur modification serveur MCP (${resp.statusCode}): ${resp.body}');
    }
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<void> deleteMcpServer(UserSession session, String serverId) async {
    final uri = Uri.parse(
      '${session.serverUrl}/db/mcp?server_id=${Uri.encodeQueryComponent(serverId)}',
    );
    final resp = await _client.delete(
      uri,
      headers: _authHeaders(session.accessToken),
    );
    if (resp.statusCode < 200 || resp.statusCode >= 300) {
      throw Exception('Erreur suppression serveur MCP (${resp.statusCode}): ${resp.body}');
    }
  }

  // ==================== SYSTEM PROMPTS (ADMIN) ====================

  Future<List<Map<String, dynamic>>> listSystemPrompts(
    UserSession session,
  ) async {
    final uri = Uri.parse('${session.serverUrl}/db/system_prompts/list');
    final resp = await _client.get(
      uri,
      headers: _authHeaders(session.accessToken),
    );
    if (resp.statusCode != 200) {
      throw Exception('Erreur chargement System Prompts (${resp.statusCode})');
    }
    final decoded = jsonDecode(resp.body) as List<dynamic>;
    return decoded.whereType<Map<String, dynamic>>().toList();
  }

  Future<Map<String, dynamic>> getSystemPrompt(
    UserSession session,
    String id,
  ) async {
    final uri = Uri.parse(
      '${session.serverUrl}/db/system_prompts?id=${Uri.encodeQueryComponent(id)}',
    );
    final resp = await _client.get(
      uri,
      headers: _authHeaders(session.accessToken),
    );
    if (resp.statusCode != 200) {
      throw Exception('Erreur chargement du prompt (${resp.statusCode})');
    }
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> createSystemPrompt(
    UserSession session,
    Map<String, dynamic> payload,
  ) async {
    final uri = Uri.parse('${session.serverUrl}/db/system_prompts');
    final resp = await _client.post(
      uri,
      headers: _authHeaders(session.accessToken, jsonBody: true),
      body: jsonEncode(payload),
    );
    if (resp.statusCode < 200 || resp.statusCode >= 300) {
      throw Exception('Erreur création System Prompt (${resp.statusCode}): ${resp.body}');
    }
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> updateSystemPrompt(
    UserSession session,
    String id,
    Map<String, dynamic> patch,
  ) async {
    final uri = Uri.parse(
      '${session.serverUrl}/db/system_prompts?id=${Uri.encodeQueryComponent(id)}',
    );
    final resp = await _client.patch(
      uri,
      headers: _authHeaders(session.accessToken, jsonBody: true),
      body: jsonEncode(patch),
    );
    if (resp.statusCode < 200 || resp.statusCode >= 300) {
      throw Exception('Erreur modification System Prompt (${resp.statusCode}): ${resp.body}');
    }
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<void> deleteSystemPrompt(UserSession session, String id) async {
    final uri = Uri.parse(
      '${session.serverUrl}/db/system_prompts?id=${Uri.encodeQueryComponent(id)}',
    );
    final resp = await _client.delete(
      uri,
      headers: _authHeaders(session.accessToken),
    );
    if (resp.statusCode < 200 || resp.statusCode >= 300) {
      throw Exception('Erreur suppression System Prompt (${resp.statusCode}): ${resp.body}');
    }
  }

  Future<Map<String, dynamic>> resetSystemPrompt(
    UserSession session,
    String id,
  ) async {
    final uri = Uri.parse(
      '${session.serverUrl}/db/system_prompts/reset?id=${Uri.encodeQueryComponent(id)}',
    );
    final resp = await _client.post(
      uri,
      headers: _authHeaders(session.accessToken),
    );
    if (resp.statusCode < 200 || resp.statusCode >= 300) {
      throw Exception('Erreur réinitialisation System Prompt (${resp.statusCode}): ${resp.body}');
    }
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> resetAllSystemPrompts(
    UserSession session,
  ) async {
    final uri = Uri.parse('${session.serverUrl}/db/system_prompts/reset/all');
    final resp = await _client.post(
      uri,
      headers: _authHeaders(session.accessToken),
    );
    if (resp.statusCode < 200 || resp.statusCode >= 300) {
      throw Exception('Erreur réinitialisation globale (${resp.statusCode}): ${resp.body}');
    }
    final decoded = jsonDecode(resp.body) as List<dynamic>;
    return decoded.whereType<Map<String, dynamic>>().toList();
  }

  // ==================== DYNAMIC SERVER SETTINGS (ADMIN) ====================

  Future<Map<String, dynamic>> getServerSettings(UserSession session) async {
    final uri = Uri.parse('${session.serverUrl}/settings');
    final resp = await _client.get(
      uri,
      headers: _authHeaders(session.accessToken),
    );
    if (resp.statusCode != 200) {
      throw Exception('Erreur lecture paramètres serveur (${resp.statusCode})');
    }
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<List<String>> getSupportedCurrencies(UserSession session) async {
    final uri = Uri.parse('${session.serverUrl}/settings/currencies');
    final resp = await _client.get(
      uri,
      headers: _authHeaders(session.accessToken),
    );
    if (resp.statusCode != 200) return const ['USD', 'EUR', 'GBP'];
    final decoded = jsonDecode(resp.body) as List<dynamic>;
    return decoded.map((e) => e.toString()).toList();
  }

  Future<Map<String, dynamic>> updateServerSettings(
    UserSession session,
    Map<String, dynamic> patch,
  ) async {
    final uri = Uri.parse('${session.serverUrl}/settings');
    final resp = await _client.patch(
      uri,
      headers: _authHeaders(session.accessToken, jsonBody: true),
      body: jsonEncode(patch),
    );
    if (resp.statusCode < 200 || resp.statusCode >= 300) {
      throw Exception('Erreur sauvegarde paramètres (${resp.statusCode}): ${resp.body}');
    }
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> resetServerSettings(UserSession session) async {
    final uri = Uri.parse('${session.serverUrl}/settings/reset');
    final resp = await _client.post(
      uri,
      headers: _authHeaders(session.accessToken),
    );
    if (resp.statusCode < 200 || resp.statusCode >= 300) {
      throw Exception('Erreur réinitialisation paramètres (${resp.statusCode}): ${resp.body}');
    }
    return jsonDecode(resp.body) as Map<String, dynamic>;
  }
}
