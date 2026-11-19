import 'package:flutter/material.dart';

import '../../../core/theme/theme_controller.dart';
import '../../../core/theme/watermark_background.dart';
import '../view_models/chat_view_model.dart';
import 'widgets/chat_composer_bar.dart';
import 'widgets/chat_sidebar.dart';
import 'widgets/chat_top_bar.dart';
import 'widgets/chat_welcome_hero.dart';
import 'widgets/message_bubble.dart';

class ChatWorkspaceScreen extends StatefulWidget {
  const ChatWorkspaceScreen({
    super.key,
    required this.viewModel,
    required this.themeController,
    required this.onLogout,
  });

  final ChatViewModel viewModel;
  final ThemeController themeController;
  final VoidCallback onLogout;

  @override
  State<ChatWorkspaceScreen> createState() => _ChatWorkspaceScreenState();
}

class _ChatWorkspaceScreenState extends State<ChatWorkspaceScreen> {
  bool _isSidebarOpen = true;

  @override
  void initState() {
    super.initState();
    widget.viewModel.initialize();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: WatermarkBackground(
        child: SafeArea(
          child: ListenableBuilder(
            listenable: widget.viewModel,
            builder: (context, _) {
              return Row(
                children: [
                  // Floating left notebook sidebar with smooth animation
                  AnimatedContainer(
                    duration: const Duration(milliseconds: 240),
                    curve: Curves.easeOutCubic,
                    width: _isSidebarOpen ? 286 : 0,
                    child: ClipRect(
                      child: OverflowBox(
                        alignment: Alignment.centerLeft,
                        minWidth: 286,
                        maxWidth: 286,
                        child: Padding(
                          padding: const EdgeInsets.fromLTRB(12, 12, 4, 12),
                          child: ChatSidebar(
                            viewModel: widget.viewModel,
                            themeController: widget.themeController,
                            onLogout: widget.onLogout,
                            onCollapse: () =>
                                setState(() => _isSidebarOpen = false),
                          ),
                        ),
                      ),
                    ),
                  ),

                  // Main conversation area
                  Expanded(
                    child: Column(
                      children: [
                        ChatTopBar(
                          viewModel: widget.viewModel,
                          themeController: widget.themeController,
                          isSidebarOpen: _isSidebarOpen,
                          onToggleSidebar: () =>
                              setState(() => _isSidebarOpen = !_isSidebarOpen),
                        ),
                        Expanded(
                          child: widget.viewModel.messages.isEmpty
                              ? ChatWelcomeHero(
                                  viewModel: widget.viewModel,
                                )
                              : ListView.builder(
                                  padding: const EdgeInsets.fromLTRB(
                                    24,
                                    12,
                                    24,
                                    16,
                                  ),
                                  itemCount: widget.viewModel.messages.length,
                                  itemBuilder: (context, index) {
                                    final msg =
                                        widget.viewModel.messages[index];
                                    return MessageBubble(
                                      message: msg,
                                      viewModel: widget.viewModel,
                                    );
                                  },
                                ),
                        ),
                        ChatComposerBar(viewModel: widget.viewModel),
                      ],
                    ),
                  ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }
}
