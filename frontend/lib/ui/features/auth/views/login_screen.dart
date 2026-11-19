import 'package:flutter/material.dart';

import '../../../../domain/models/app_theme_spec.dart';
import '../../../core/l10n/locale_controller.dart';
import '../../../core/theme/appearance_modal.dart';
import '../../../core/theme/theme_controller.dart';
import '../../../core/theme/watermark_background.dart';
import '../../../core/widgets/ratatosk_logo.dart';
import '../view_models/auth_view_model.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({
    super.key,
    required this.viewModel,
    required this.themeController,
  });

  final AuthViewModel viewModel;
  final ThemeController themeController;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  late final TextEditingController _serverCtrl;
  late final TextEditingController _userCtrl;
  final TextEditingController _passCtrl = TextEditingController();

  @override
  void initState() {
    super.initState();
    _serverCtrl =
        TextEditingController(text: widget.viewModel.initialServerUrl);
    _userCtrl = TextEditingController(text: widget.viewModel.initialUsername);
    widget.viewModel.loadHints().then((_) {
      if (mounted) {
        _serverCtrl.text = widget.viewModel.initialServerUrl;
        _userCtrl.text = widget.viewModel.initialUsername;
      }
    });
  }

  @override
  void dispose() {
    _serverCtrl.dispose();
    _userCtrl.dispose();
    _passCtrl.dispose();
    super.dispose();
  }

  Future<void> _handleLogin() async {
    await widget.viewModel.login(
      serverUrl: _serverCtrl.text,
      username: _userCtrl.text,
      password: _passCtrl.text,
    );
  }

  @override
  Widget build(BuildContext context) {
    final spec = context.appTheme;
    final l10n = context.l10n;
    final localeCtrl = LocaleControllerScope.maybeOf(context);
    final currentLang = localeCtrl?.locale.languageCode ?? 'en';

    return Scaffold(
      body: WatermarkBackground(
        child: SafeArea(
          child: Stack(
            children: [
              Positioned(
                top: 16,
                right: 20,
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (localeCtrl != null) ...[
                      OutlinedButton.icon(
                        style: OutlinedButton.styleFrom(
                          foregroundColor: spec.textColor,
                          side: BorderSide(color: spec.borderColor),
                        ),
                        onPressed: () => localeCtrl.setLocale(
                          Locale(currentLang == 'en' ? 'fr' : 'en'),
                        ),
                        icon: Icon(
                          Icons.translate_rounded,
                          size: 16,
                          color: spec.accentColor,
                        ),
                        label: Text(currentLang.toUpperCase()),
                      ),
                      const SizedBox(width: 8),
                    ],
                    OutlinedButton.icon(
                      style: OutlinedButton.styleFrom(
                        foregroundColor: spec.textColor,
                        side: BorderSide(color: spec.borderColor),
                      ),
                      onPressed: () => AppearanceModal.show(
                        context,
                        widget.themeController,
                      ),
                      icon: Icon(
                        Icons.palette_outlined,
                        size: 18,
                        color: spec.accentColor,
                      ),
                      label: Text(l10n.themeButtonLabel(spec.name)),
                    ),
                  ],
                ),
              ),
              Center(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(24),
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 420),
                    child: Card(
                      child: Padding(
                        padding: const EdgeInsets.all(28),
                        child: ListenableBuilder(
                          listenable: widget.viewModel,
                          builder: (context, _) {
                            return Column(
                              mainAxisSize: MainAxisSize.min,
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                const Center(child: RatatoskLogo(size: 64)),
                                const SizedBox(height: 14),
                                Text(
                                  l10n.appTitle,
                                  textAlign: TextAlign.center,
                                  style: TextStyle(
                                    color: spec.textColor,
                                    fontSize: 26,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  l10n.loginTagline,
                                  textAlign: TextAlign.center,
                                  style: TextStyle(
                                    color: spec.subtextColor,
                                    fontSize: 13,
                                  ),
                                ),
                                const SizedBox(height: 24),
                                TextField(
                                  controller: _serverCtrl,
                                  style: TextStyle(color: spec.textColor),
                                  decoration: InputDecoration(
                                    labelText: l10n.loginServerLabel,
                                    prefixIcon:
                                        const Icon(Icons.dns_outlined, size: 18),
                                  ),
                                ),
                                const SizedBox(height: 14),
                                TextField(
                                  controller: _userCtrl,
                                  style: TextStyle(color: spec.textColor),
                                  decoration: InputDecoration(
                                    labelText: l10n.loginUsernameLabel,
                                    prefixIcon: const Icon(
                                      Icons.person_outline,
                                      size: 18,
                                    ),
                                  ),
                                ),
                                const SizedBox(height: 14),
                                TextField(
                                  controller: _passCtrl,
                                  obscureText: true,
                                  onSubmitted: (_) => _handleLogin(),
                                  style: TextStyle(color: spec.textColor),
                                  decoration: InputDecoration(
                                    labelText: l10n.loginPasswordLabel,
                                    prefixIcon: const Icon(
                                      Icons.lock_outline,
                                      size: 18,
                                    ),
                                  ),
                                ),
                                if (widget.viewModel.errorMessage != null) ...[
                                  const SizedBox(height: 14),
                                  Container(
                                    padding: const EdgeInsets.all(10),
                                    decoration: BoxDecoration(
                                      color: const Color(0xFFEF4444)
                                          .withValues(alpha: 0.14),
                                      borderRadius: BorderRadius.circular(8),
                                      border: Border.all(
                                        color: const Color(0xFFEF4444),
                                      ),
                                    ),
                                    child: Text(
                                      widget.viewModel.errorMessage!,
                                      style: const TextStyle(
                                        color: Color(0xFFFCA5A5),
                                        fontSize: 12,
                                      ),
                                    ),
                                  ),
                                ],
                                const SizedBox(height: 22),
                                SizedBox(
                                  height: 44,
                                  child: FilledButton(
                                    style: FilledButton.styleFrom(
                                      backgroundColor: spec.accentColor,
                                    ),
                                    onPressed: widget.viewModel.isLoading
                                        ? null
                                        : _handleLogin,
                                    child: widget.viewModel.isLoading
                                        ? const SizedBox(
                                            width: 20,
                                            height: 20,
                                            child: CircularProgressIndicator(
                                              strokeWidth: 2,
                                            ),
                                          )
                                        : Text(
                                            l10n.loginSubmitButton,
                                            style: const TextStyle(
                                              fontWeight: FontWeight.w600,
                                            ),
                                          ),
                                  ),
                                ),
                                const SizedBox(height: 10),
                                TextButton.icon(
                                  onPressed: () => widget.viewModel
                                      .enterOfflinePreview(
                                        serverUrl: _serverCtrl.text,
                                      ),
                                  icon: Icon(
                                    Icons.visibility_outlined,
                                    size: 16,
                                    color: spec.subtextColor,
                                  ),
                                  label: Text(
                                    l10n.loginOfflinePreview,
                                    style: TextStyle(
                                      color: spec.subtextColor,
                                      fontSize: 12,
                                    ),
                                  ),
                                ),
                              ],
                            );
                          },
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
