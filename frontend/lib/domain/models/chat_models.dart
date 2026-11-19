class ModelInfoModel {
  const ModelInfoModel({
    required this.id,
    required this.provider,
    required this.displayName,
    required this.tasks,
    required this.tier,
    required this.isRecommended,
    this.icon,
    this.category = 'general',
    this.contextWindow,
    this.inputPricePer1m,
    this.outputPricePer1m,
    this.description,
    this.descriptions,
    this.rank = 999,
  });

  final String id;
  final String provider;
  final String displayName;
  final String? icon;
  final String category;
  final List<String> tasks;
  final String tier;
  final bool isRecommended;
  final int? contextWindow;
  final double? inputPricePer1m;
  final double? outputPricePer1m;
  final String? description;
  final Map<String, String>? descriptions;
  final int rank;

  String? localizedDescription(String languageCode) {
    final map = descriptions;
    if (map != null && map.isNotEmpty) {
      return map[languageCode] ?? map['en'] ?? map.values.first;
    }
    return description;
  }

  factory ModelInfoModel.fromJson(Map<String, dynamic> json) {
    final rawTasks = json['tasks'] as List<dynamic>? ?? const ['text-generation'];
    final rawDescriptions = json['descriptions'];
    Map<String, String>? parsedDescriptions;
    if (rawDescriptions is Map) {
      parsedDescriptions = {
        for (final entry in rawDescriptions.entries)
          if (entry.value != null) entry.key.toString(): entry.value.toString(),
      };
    }
    return ModelInfoModel(
      id: json['id'] as String? ?? '',
      provider: json['provider'] as String? ?? 'google',
      displayName: json['display_name'] as String? ?? (json['id'] as String? ?? ''),
      icon: json['icon'] as String?,
      category: json['category'] as String? ?? 'general',
      tasks: rawTasks.map((e) => e.toString()).toList(),
      tier: json['tier'] as String? ?? 'standard',
      isRecommended: json['is_recommended'] as bool? ?? false,
      contextWindow: (json['context_window'] as num?)?.toInt(),
      inputPricePer1m: (json['input_price_per_1m'] as num?)?.toDouble(),
      outputPricePer1m: (json['output_price_per_1m'] as num?)?.toDouble(),
      description: json['description'] as String?,
      descriptions: parsedDescriptions,
      rank: (json['rank'] as num?)?.toInt() ?? 999,
    );
  }
}

class ConversationSummary {
  const ConversationSummary({
    required this.id,
    required this.title,
    required this.archived,
    this.updatedAt,
  });

  final String id;
  final String title;
  final bool archived;
  final DateTime? updatedAt;

  factory ConversationSummary.fromJson(Map<String, dynamic> json) {
    return ConversationSummary(
      id: json['id'] as String,
      title: (json['title'] as String?) ?? 'Nouvelle Conversation',
      archived: (json['archived'] as bool?) ?? false,
      updatedAt: json['updated_at'] != null
          ? DateTime.tryParse(json['updated_at'] as String)
          : null,
    );
  }
}

class ToolCallItem {
  const ToolCallItem({
    required this.name,
    required this.args,
    this.id,
    this.result,
  });

  final String? id;
  final String name;
  final Map<String, dynamic> args;
  final Map<String, dynamic>? result;

  ToolCallItem copyWith({Map<String, dynamic>? result}) {
    return ToolCallItem(
      id: id,
      name: name,
      args: args,
      result: result ?? this.result,
    );
  }
}

class AttachmentRef {
  const AttachmentRef({
    required this.id,
    required this.filename,
    required this.mimeType,
    this.isGenerated = false,
    this.externalUri,
    this.insertOffset,
  });

  final String id;
  final String filename;
  final String mimeType;
  final bool isGenerated;
  final String? externalUri;
  final int? insertOffset;

  bool get isImage => mimeType.startsWith('image/');

  factory AttachmentRef.fromJson(Map<String, dynamic> json) {
    return AttachmentRef(
      id: (json['id'] ?? json['attachment_id'] ?? '') as String,
      filename: (json['filename'] ?? 'attachment') as String,
      mimeType: (json['mime_type'] ?? 'application/octet-stream') as String,
      isGenerated: (json['is_generated'] as bool?) ?? false,
      externalUri: json['external_uri'] as String?,
      insertOffset: (json['insert_offset'] as num?)?.toInt(),
    );
  }
}

class SourceItemModel {
  const SourceItemModel({
    required this.kind,
    required this.title,
    this.url,
    this.attachmentId,
    this.mimeType,
    this.queries = const [],
  });

  final String kind; // 'web' or 'attachment'
  final String title;
  final String? url;
  final String? attachmentId;
  final String? mimeType;
  final List<String> queries;

  factory SourceItemModel.fromJson(Map<String, dynamic> json) {
    final qList = json['queries'] as List<dynamic>? ?? const [];
    return SourceItemModel(
      kind: (json['kind'] ?? 'web') as String,
      title: (json['title'] ?? 'Source') as String,
      url: json['url'] as String?,
      attachmentId: json['attachment_id'] as String?,
      mimeType: json['mime_type'] as String?,
      queries: qList.map((e) => e.toString()).toList(),
    );
  }
}

class ImageProgressState {
  const ImageProgressState({
    required this.step,
    required this.totalSteps,
    required this.progress,
    required this.model,
    this.status,
    this.previewBase64,
    this.mimeType = 'image/jpeg',
  });

  final int step;
  final int totalSteps;
  final double progress;
  final String model;
  final String? status;
  final String? previewBase64;
  final String mimeType;

  factory ImageProgressState.fromJson(Map<String, dynamic> json) {
    return ImageProgressState(
      step: (json['step'] as num?)?.toInt() ?? 0,
      totalSteps: (json['total_steps'] as num?)?.toInt() ?? 4,
      progress: ((json['progress'] as num?) ?? 0.0).toDouble(),
      model: (json['model'] as String?) ?? '',
      status: json['status'] as String?,
      previewBase64: json['preview_base64'] as String?,
      mimeType: (json['mime_type'] as String?) ?? 'image/jpeg',
    );
  }
}

class MessageUsageInfo {
  const MessageUsageInfo({
    required this.inputTokens,
    required this.outputTokens,
    required this.thoughtsTokens,
    required this.cost,
    required this.currency,
  });

  final int inputTokens;
  final int outputTokens;
  final int thoughtsTokens;
  final double cost;
  final String currency;

  factory MessageUsageInfo.fromJson(Map<String, dynamic> json) {
    return MessageUsageInfo(
      inputTokens: (json['input_tokens'] as num?)?.toInt() ?? 0,
      outputTokens: (json['output_tokens'] as num?)?.toInt() ?? 0,
      thoughtsTokens: (json['thoughts_tokens'] as num?)?.toInt() ?? 0,
      cost: ((json['cost'] as num?) ?? 0.0).toDouble(),
      currency: (json['currency'] as String?) ?? 'USD',
    );
  }
}

class ChatMessageItem {
  const ChatMessageItem({
    required this.id,
    required this.role,
    required this.content,
    this.model,
    this.thinking = '',
    this.toolCalls = const [],
    this.attachments = const [],
    this.sources = const [],
    this.imageProgress,
    this.usage,
    this.isStreaming = false,
    this.error,
  });

  final String id;
  final String role;
  final String content;
  final String? model;
  final String thinking;
  final List<ToolCallItem> toolCalls;
  final List<AttachmentRef> attachments;
  final List<SourceItemModel> sources;
  final ImageProgressState? imageProgress;
  final MessageUsageInfo? usage;
  final bool isStreaming;
  final String? error;

  ChatMessageItem copyWith({
    String? id,
    String? role,
    String? content,
    String? model,
    String? thinking,
    List<ToolCallItem>? toolCalls,
    List<AttachmentRef>? attachments,
    List<SourceItemModel>? sources,
    ImageProgressState? imageProgress,
    bool clearImageProgress = false,
    MessageUsageInfo? usage,
    bool? isStreaming,
    String? error,
  }) {
    return ChatMessageItem(
      id: id ?? this.id,
      role: role ?? this.role,
      content: content ?? this.content,
      model: model ?? this.model,
      thinking: thinking ?? this.thinking,
      toolCalls: toolCalls ?? this.toolCalls,
      attachments: attachments ?? this.attachments,
      sources: sources ?? this.sources,
      imageProgress:
          clearImageProgress ? null : (imageProgress ?? this.imageProgress),
      usage: usage ?? this.usage,
      isStreaming: isStreaming ?? this.isStreaming,
      error: error ?? this.error,
    );
  }

  factory ChatMessageItem.fromBackendJson(Map<String, dynamic> json) {
    final parts = json['parts'] as List<dynamic>? ?? const [];
    final StringBuffer thinkingBuf = StringBuffer();
    final List<ToolCallItem> calls = [];
    final List<SourceItemModel> parsedSources = [];

    for (final rawPart in parts) {
      if (rawPart is! Map<String, dynamic>) continue;
      final type = rawPart['type'] as String?;
      if (type == 'thinking') {
        thinkingBuf.write(rawPart['text'] ?? '');
      } else if (type == 'tool_call') {
        calls.add(
          ToolCallItem(
            id: rawPart['id'] as String?,
            name: (rawPart['name'] ?? '') as String,
            args: Map<String, dynamic>.from(
              (rawPart['args'] as Map?) ?? const {},
            ),
          ),
        );
      } else if (type == 'tool_response') {
        final callId = rawPart['id'] as String?;
        final callName = rawPart['name'] as String?;
        final result = Map<String, dynamic>.from(
          (rawPart['result'] as Map?) ?? const {},
        );
        final idx = calls.lastIndexWhere(
          (c) =>
              (callId != null && c.id == callId) ||
              (c.name == callName && c.result == null),
        );
        if (idx != -1) {
          calls[idx] = calls[idx].copyWith(result: result);
        }
      } else if (type == 'sources') {
        final items = rawPart['items'] as List<dynamic>? ?? const [];
        for (final s in items) {
          if (s is Map<String, dynamic>) {
            parsedSources.add(SourceItemModel.fromJson(s));
          }
        }
      }
    }

    final rawAtts = json['attachments'] as List<dynamic>? ?? const [];
    final atts = rawAtts
        .whereType<Map<String, dynamic>>()
        .map(AttachmentRef.fromJson)
        .toList();

    return ChatMessageItem(
      id: (json['id'] ?? '') as String,
      role: (json['role'] ?? 'assistant') as String,
      content: (json['content'] ?? '') as String,
      model: json['model'] as String?,
      thinking: thinkingBuf.toString(),
      toolCalls: calls,
      attachments: atts,
      sources: parsedSources,
    );
  }
}
