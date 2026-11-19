import 'package:shared_preferences/shared_preferences.dart';

import '../../domain/models/user_session.dart';
import '../services/ratatosk_api_client.dart';

class AuthRepository {
  AuthRepository({required this._apiClient});

  final RatatoskApiClient _apiClient;

  static const String _serverUrlKey = 'ratatosk_server_url';
  static const String _usernameKey = 'ratatosk_last_username';

  UserSession? _currentSession;
  UserSession? get currentSession => _currentSession;

  Future<(String, String)> loadSavedLoginHints() async {
    final prefs = await SharedPreferences.getInstance();
    final url = prefs.getString(_serverUrlKey) ?? 'http://127.0.0.1:8000';
    final username = prefs.getString(_usernameKey) ?? 'admin';
    return (url, username);
  }

  Future<UserSession> signIn({
    required String serverUrl,
    required String username,
    required String password,
  }) async {
    final session = await _apiClient.login(
      serverUrl: serverUrl,
      username: username,
      password: password,
    );
    _currentSession = session;

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_serverUrlKey, session.serverUrl);
    await prefs.setString(_usernameKey, session.username);
    return session;
  }

  void signOut() {
    _currentSession = null;
  }
}
