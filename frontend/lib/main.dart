import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'data/repositories/auth_repository.dart';
import 'data/repositories/chat_repository.dart';
import 'data/services/ratatosk_api_client.dart';
import 'l10n/app_localizations.dart';
import 'ui/core/l10n/locale_controller.dart';
import 'ui/core/theme/theme_controller.dart';
import 'ui/features/auth/view_models/auth_view_model.dart';
import 'ui/features/auth/views/login_screen.dart';
import 'ui/features/chat/view_models/chat_view_model.dart';
import 'ui/features/chat/views/chat_workspace_screen.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final themeController = ThemeController();
  final localeController = LocaleController();
  await Future.wait([
    themeController.initialize(),
    localeController.initialize(),
  ]);
  runApp(
    RatatoskApp(
      themeController: themeController,
      localeController: localeController,
    ),
  );
}

class RatatoskApp extends StatefulWidget {
  const RatatoskApp({
    super.key,
    required this.themeController,
    this.localeController,
  });

  final ThemeController themeController;
  final LocaleController? localeController;

  @override
  State<RatatoskApp> createState() => _RatatoskAppState();
}

class _RatatoskAppState extends State<RatatoskApp> {
  late final RatatoskApiClient _apiClient;
  late final AuthRepository _authRepository;
  late final ChatRepository _chatRepository;
  late final AuthViewModel _authViewModel;
  late final LocaleController _localeController;
  bool _ownsLocaleController = false;

  ChatViewModel? _chatViewModel;

  @override
  void initState() {
    super.initState();
    if (widget.localeController != null) {
      _localeController = widget.localeController!;
    } else {
      _localeController = LocaleController();
      _ownsLocaleController = true;
    }
    _apiClient = RatatoskApiClient();
    _authRepository = AuthRepository(apiClient: _apiClient);
    _chatRepository = ChatRepository(apiClient: _apiClient);
    _authViewModel = AuthViewModel(authRepository: _authRepository)
      ..addListener(_onAuthChanged);
  }

  void _onAuthChanged() {
    final session = _authViewModel.session;
    setState(() {
      if (session == null) {
        _chatViewModel = null;
      } else if (_chatViewModel?.session.accessToken != session.accessToken) {
        _chatViewModel = ChatViewModel(
          chatRepository: _chatRepository,
          session: session,
        );
      }
    });
  }

  @override
  void dispose() {
    _authViewModel.removeListener(_onAuthChanged);
    _authViewModel.dispose();
    if (_ownsLocaleController) {
      _localeController.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: Listenable.merge([
        widget.themeController,
        _localeController,
      ]),
      builder: (context, _) {
        final activeSpec = widget.themeController.activeTheme;

        return LocaleControllerScope(
          controller: _localeController,
          child: MaterialApp(
            title: 'Ratatosk',
            debugShowCheckedModeBanner: false,
            theme: activeSpec.toThemeData(),
            locale: _localeController.locale,
            supportedLocales: LocaleController.supportedLocales,
            localizationsDelegates: const [
              AppLocalizations.delegate,
              GlobalMaterialLocalizations.delegate,
              GlobalWidgetsLocalizations.delegate,
              GlobalCupertinoLocalizations.delegate,
            ],
            home: _chatViewModel == null
                ? LoginScreen(
                    viewModel: _authViewModel,
                    themeController: widget.themeController,
                  )
                : ChatWorkspaceScreen(
                    viewModel: _chatViewModel!,
                    themeController: widget.themeController,
                    onLogout: _authViewModel.logout,
                  ),
          ),
        );
      },
    );
  }
}
