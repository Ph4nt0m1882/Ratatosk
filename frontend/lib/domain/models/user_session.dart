class UserSession {
  const UserSession({
    required this.serverUrl,
    required this.accessToken,
    required this.userId,
    required this.username,
    required this.isAdmin,
  });

  final String serverUrl;
  final String accessToken;
  final String userId;
  final String username;
  final bool isAdmin;
}
