import 'dart:typed_data';

import '../../domain/models/chat_models.dart';
import '../../domain/models/user_session.dart';
import '../services/ratatosk_api_client.dart';

class ChatRepository {
  ChatRepository({required this._apiClient});

  final RatatoskApiClient _apiClient;

  Future<List<ModelInfoModel>> getModels(
    UserSession session, {
    bool refresh = false,
  }) =>
      _apiClient.fetchModels(session, refresh: refresh);

  Future<List<ConversationSummary>> getConversations(
    UserSession session, {
    bool onlyNotArchived = true,
  }) =>
      _apiClient.fetchConversations(
        session,
        onlyNotArchived: onlyNotArchived,
      );

  Future<List<ChatMessageItem>> getMessages(
    UserSession session,
    String conversationId,
  ) =>
      _apiClient.fetchMessages(session, conversationId);

  Future<void> deleteConversation(
    UserSession session,
    String conversationId,
  ) =>
      _apiClient.deleteConversation(session, conversationId);

  Future<AttachmentRef> uploadAttachment({
    required UserSession session,
    required String filename,
    required Uint8List bytes,
  }) =>
      _apiClient.uploadAttachment(
        session: session,
        filename: filename,
        bytes: bytes,
      );

  String buildAttachmentUrl(
    UserSession session,
    String attachmentId, {
    bool preview = false,
  }) =>
      _apiClient.buildAttachmentUrl(
        session,
        attachmentId,
        preview: preview,
      );

  Future<Uint8List> downloadAttachmentBytes(
    UserSession session,
    String attachmentId,
  ) =>
      _apiClient.downloadAttachmentBytes(session, attachmentId);

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
  }) =>
      _apiClient.streamChat(
        session: session,
        model: model,
        messages: messages,
        conversationId: conversationId,
        historyMode: historyMode,
        searchMode: searchMode,
        temperature: temperature,
        enableBuiltinTools: enableBuiltinTools,
        unlockedTools: unlockedTools,
      );
}
