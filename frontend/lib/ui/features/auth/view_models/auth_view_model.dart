import 'package:flutter/foundation.dart';

import '../../../../data/repositories/auth_repository.dart';
import '../../../../domain/models/user_session.dart';

class AuthViewModel extends ChangeNotifier {
  AuthViewModel({required this._authRepository});

  final AuthRepository _authRepository;

  UserSession? _session;
  UserSession? get session => _session;

  bool _isLoading = false;
  bool get isLoading => _isLoading;

  String? _errorMessage;
  String? get errorMessage => _errorMessage;

  String _initialServerUrl = 'http://127.0.0.1:8000';
  String get initialServerUrl => _initialServerUrl;

  String _initialUsername = 'admin';
  String get initialUsername => _initialUsername;

  Future<void> loadHints() async {
    final (url, username) = await _authRepository.loadSavedLoginHints();
    _initialServerUrl = url;
    _initialUsername = username;
    notifyListeners();
  }

  Future<bool> login({
    required String serverUrl,
    required String username,
    required String password,
  }) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      _session = await _authRepository.signIn(
        serverUrl: serverUrl,
        username: username,
        password: password,
      );
      return true;
    } catch (e) {
      _errorMessage = e.toString().replaceFirst('Exception: ', '');
      return false;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  void enterOfflinePreview({String serverUrl = 'http://127.0.0.1:8000'}) {
    _errorMessage = null;
    _session = UserSession(
      serverUrl: serverUrl,
      accessToken: 'demo_preview_token',
      userId: 'demo_user',
      username: 'Explorateur',
      isAdmin: true,
    );
    notifyListeners();
  }

  void logout() {
    _authRepository.signOut();
    _session = null;
    notifyListeners();
  }
}
