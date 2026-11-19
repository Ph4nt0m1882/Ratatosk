// ignore: unused_import
import 'package:intl/intl.dart' as intl;

import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for French (`fr`).
class AppLocalizationsFr extends AppLocalizations {
  AppLocalizationsFr([String locale = 'fr']) : super(locale);

  @override
  String get appTitle => 'Ratatosk';

  @override
  String get loginTagline => 'Orchestrateur IA unifié sur Yggdrasil';

  @override
  String get loginServerLabel => 'Serveur Ratatosk';

  @override
  String get loginUsernameLabel => 'Nom d\'utilisateur';

  @override
  String get loginPasswordLabel => 'Mot de passe';

  @override
  String get loginSubmitButton => 'Se connecter';

  @override
  String get loginOfflinePreview => 'Explorer l\'interface hors-ligne';

  @override
  String themeButtonLabel(String themeName) {
    return 'Thème : $themeName';
  }

  @override
  String get languageLabel => 'Langue';

  @override
  String get languageEnglish => 'English';

  @override
  String get languageFrench => 'Français';

  @override
  String get sidebarSubtitle => 'Carnet d\'échanges';

  @override
  String get sidebarCollapseTooltip => 'Replier le carnet';

  @override
  String get sidebarNewChat => 'Nouvelle discussion';

  @override
  String get sidebarMyChats => 'Mes discussions';

  @override
  String get sidebarEmptyChats =>
      'Aucune histoire pour le moment.\nLance ta première question !';

  @override
  String get sidebarRoleAdmin => 'Gardien (Admin)';

  @override
  String get sidebarRoleMember => 'Explorateur';

  @override
  String get sidebarOpenSettings => 'Ouvrir les réglages';

  @override
  String get sidebarLogout => 'Se déconnecter';

  @override
  String get topBarOpenChats => 'Discussions';

  @override
  String get topBarOpenChatsTooltip => 'Ouvrir le carnet de discussions';

  @override
  String topBarThemeTooltip(String themeName) {
    return 'Changer les couleurs ($themeName)';
  }

  @override
  String get topBarSettingsTooltip => 'Réglages';

  @override
  String welcomeMorning(String name) {
    return 'Bonjour, $name !';
  }

  @override
  String welcomeAfternoon(String name) {
    return 'Bon après-midi, $name !';
  }

  @override
  String welcomeEvening(String name) {
    return 'Bonsoir, $name !';
  }

  @override
  String get welcomeSubtitle =>
      'Que souhaite-t-on découvrir, inventer ou créer aujourd\'hui ?';

  @override
  String hubComingSoon(String modeName, String details) {
    return '$modeName — Bientôt disponible ($details)';
  }

  @override
  String get hubDrawTitle => 'Imaginer un dessin';

  @override
  String get hubDrawSubtitle =>
      'Atelier dédié de création, retouche et manipulation d\'images';

  @override
  String get hubDrawDetails => 'Éditeur et studio d\'images';

  @override
  String get hubExploreTitle => 'Explorer le monde';

  @override
  String get hubExploreSubtitle =>
      'Carte d\'actualités interactive, recherches et suivi de tes passions';

  @override
  String get hubExploreDetails => 'Mappemonde d\'actus, recherche & passions';

  @override
  String get hubLearnTitle => 'Apprendre & Rédiger';

  @override
  String get hubLearnSubtitle =>
      'Studio façon NotebookLM : cours, mails, récits et recettes';

  @override
  String get hubLearnDetails => 'Carnets de sources, apprentissage & rédaction';

  @override
  String get hubPlayTitle => 'Jouer';

  @override
  String get hubPlaySubtitle =>
      'Tamagotchi IA, donjons aléatoires et énigmes façon Layton';

  @override
  String get hubPlayDetails => 'Tamagotchi IA, Donjon Mystère & Énigmes';

  @override
  String get welcomeResumeSection => 'Reprendre là où on s\'était arrêté';

  @override
  String get composerHint =>
      'Écris ton message, pose une question ou demande un dessin...';

  @override
  String get composerAttach => 'Joindre';

  @override
  String get composerAttachTooltip => 'Ajouter une image ou un fichier';

  @override
  String get composerSend => 'Envoyer';

  @override
  String get composerSending => 'En cours...';

  @override
  String get composerChangeModelTooltip => 'Changer de modèle pour ce message';

  @override
  String get composerWebTooltip => 'Choisir le mode de recherche sur Internet';

  @override
  String get webOffTitle => 'Sans Internet';

  @override
  String get webOffDesc => 'Répond uniquement avec ses connaissances';

  @override
  String get webStandardTitle => 'Internet';

  @override
  String get webStandardDesc => 'Cherche sur le web si nécessaire';

  @override
  String get webDeepTitle => 'Enquête Web';

  @override
  String get webDeepDesc => 'Explore plusieurs sources en profondeur';

  @override
  String get composerMemoryTooltip => 'Choisir la mémoire de conversation';

  @override
  String get memEcoTitle => 'Mémoire Éco';

  @override
  String get memEcoDesc => 'Garde l\'essentiel de la discussion (recommandé)';

  @override
  String get memAutoTitle => 'Mémoire Auto';

  @override
  String get memAutoDesc =>
      'Adapte automatiquement le souvenir selon la question';

  @override
  String get memFullTitle => 'Tout retenir';

  @override
  String get memFullDesc => 'Relit l\'intégralité de la conversation';

  @override
  String get memFixedTitle => 'Mémoire Courte';

  @override
  String get memFixedDesc => 'Ne garde que les derniers messages échangés';

  @override
  String get memNoneTitle => 'Sans Souvenir';

  @override
  String get memNoneDesc => 'Chaque question repart d\'une feuille blanche';

  @override
  String get msgInternalThinking => 'Réflexion interne';

  @override
  String get msgCopyCode => 'Copier';

  @override
  String get msgCopiedCode => 'Copié';

  @override
  String get msgDownloadTooltip => 'Télécharger';

  @override
  String get modelSelectorTitle => 'Sélectionner un modèle';

  @override
  String get modelSelectorRefreshTooltip =>
      'Actualiser depuis le registre GitHub';

  @override
  String get modelSelectorSearchHint =>
      'Rechercher un modèle (Argon, Carbon, Hydrogen, Gemma...)';

  @override
  String modelSelectorEmptySearch(String query) {
    return 'Aucun modèle ne correspond à \"$query\".';
  }

  @override
  String modelSelectorFavorites(int count) {
    return 'Favoris ($count)';
  }

  @override
  String modelSelectorCount(int count) {
    return '$count modèles';
  }

  @override
  String get modelSelectorRecommendedSection => 'Modèles recommandés';

  @override
  String modelSelectorAllModels(int count) {
    return 'Tous les modèles ($count)';
  }

  @override
  String get modelSelectorRecommendedBadge => 'Recommandé';

  @override
  String get modelSelectorFreeLocal => 'Gratuit / Local';

  @override
  String get modelSelectorAddFav => 'Ajouter aux favoris';

  @override
  String get modelSelectorRemoveFav => 'Retirer des favoris';

  @override
  String get settingsTitle => 'Réglages';

  @override
  String get settingsClose => 'Fermer';

  @override
  String get settingsNavGeneralTitle => 'Mon Espace';

  @override
  String get settingsNavGeneralSub => 'Profil, langue & outils';

  @override
  String get settingsNavThemesTitle => 'Couleurs & Thèmes';

  @override
  String get settingsNavThemesSub => 'Changer l\'ambiance';

  @override
  String get settingsNavA11yTitle => 'Confort Visuel';

  @override
  String get settingsNavA11ySub => 'Daltonisme & lisibilité';

  @override
  String get settingsNavAdminTitle => 'Administration';

  @override
  String get settingsNavAdminSub => 'Serveur & System Prompts';

  @override
  String get themesSectionTitle => 'Paramètres d\'Apparence';

  @override
  String get themesSectionSubtitle =>
      'Choisissez le thème de l\'application. Les thèmes \"HC\" sont à haut contraste.';

  @override
  String get themesSystemHeader => 'Thèmes Systèmes';

  @override
  String get themesCustomHeader => 'Thèmes Personnalisés';

  @override
  String get themesCreateButton => 'Créer un thème';

  @override
  String get a11ySectionTitle => 'Accessibilité & Daltonisme';

  @override
  String get a11ySectionSubtitle =>
      'Palettes haute lisibilité calibrées pour la protanopie, la deutéranopie, la tritanopie et l\'achromatopsie.';

  @override
  String get a11yModesHeader => 'Thèmes d\'Accessibilité (4 modes)';

  @override
  String get generalSectionTitle => 'Paramètres Généraux';

  @override
  String get generalSectionSubtitle =>
      'Gérez votre langue, votre profil utilisateur et vos serveurs MCP personnels.';

  @override
  String get generalAccountHeader => 'Mon Compte';

  @override
  String get generalConnectedUser => 'Utilisateur connecté';

  @override
  String get generalRoleLabel => 'Rôle';

  @override
  String get generalRoleAdmin => 'Administrateur';

  @override
  String get generalRoleStandard => 'Utilisateur standard';

  @override
  String get generalBackendServer => 'Serveur Backend';

  @override
  String get generalActiveTheme => 'Thème actif';

  @override
  String get generalUsernameField => 'Nom d\'utilisateur';

  @override
  String get generalEmailField => 'Email (optionnel)';

  @override
  String get generalPasswordField =>
      'Nouveau mot de passe (laisser vide pour conserver)';

  @override
  String get generalUpdateButton => 'Mettre à jour';

  @override
  String get generalProfileUpdated => 'Profil mis à jour avec succès.';

  @override
  String generalMcpHeader(int count) {
    return 'Serveurs MCP ($count)';
  }

  @override
  String get generalMcpImportJson => 'Importer JSON';

  @override
  String get generalMcpAdd => 'Ajouter';

  @override
  String get generalMcpEmpty =>
      'Aucun serveur MCP configuré. Ajoutez un serveur ou importez une configuration JSON pour étendre les outils disponibles.';

  @override
  String get adminRestricted => 'Accès réservé aux administrateurs.';

  @override
  String get adminSectionTitle => 'Administration';

  @override
  String get adminSectionSubtitle =>
      'Modification des System Prompts (réservé admin), paramètres serveur, utilisateurs et MCP globaux.';

  @override
  String adminTabPrompts(int count) {
    return 'System Prompts ($count)';
  }

  @override
  String get adminTabServer => 'Paramètres Serveur';

  @override
  String adminTabUsers(int count) {
    return 'Utilisateurs ($count)';
  }

  @override
  String adminTabGlobalMcp(int count) {
    return 'MCP Globaux ($count)';
  }

  @override
  String get commonCancel => 'Annuler';

  @override
  String get commonSave => 'Enregistrer';

  @override
  String get commonDelete => 'Supprimer';

  @override
  String get commonRefresh => 'Rafraîchir';
}
