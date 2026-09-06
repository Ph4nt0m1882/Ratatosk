<!--
=== RATATOSK TODO & ROADMAP CONVENTIONS ===
Ce fichier suit la convention de gestion de projet de Ratatosk :
ce qui est noté est le suivi du repo GitHub, une étape peut-être intégralement finit côté developpeur et ne pas être poussé

Statuts des cases :
  [ ]  : Pas terminé / Non commencé
  [*]  : Terminé mais pas encore testé
  [**] : Testé unitairement, mais compatibilité avec le reste non testée
  [v]  : Terminé, testé et validé
  [x]  : Annulé / Abandonné
  [-]  : Reporté / En attente

Hiérarchie :
  # [ ]   : Niveau Application globale (coché quand l'app est déployée et prête)
  ## [ ]  : Grande section (Backend, Frontend, Déploiement, Documentation)
  ### [ ] : Feature majeure (ex: Universal Router, MCP Host, Système de profils)
  - [ ]   : Élément technique ou composant spécifique
    - [ ] : Sous-tâche ou sous-composant
-->

# [ ] RATATOSK

## [ ] Backend (Python Engine & API)

### [ ] Socle & Initialisation
- [v] Mise en place de l'environnement avec `uv`
    - [ ] Configuration de `pyproject.toml`
    - [ ] Installation et verrouillage des dépendances de base (FastAPI, Pydantic, Uvicorn, SSE)
- [ ] Système de configuration déclarative (`config.yaml` / variables d'environnement)
    - [ ] Validation des schémas de configuration (Pydantic Settings)
    - [ ] Support du rechargement à chaud ou redémarrage propre
- [ ] Gestionnaire de logs et observabilité interne

### [ ] Fournisseurs d'IA (Providers)
- [ ] Interface unifiée `BaseProvider` (contrat d'abstraction)
- [ ] Provider Anthropic (Claude 3.5 Sonnet / Haiku / Opus)
    - [ ] Streaming textuel via SSE
    - [ ] Support du Tool Use / Function Calling
- [ ] Provider Google Gemini (Gemini Flash / Pro, Imagen, Robotics)
    - [ ] Streaming multimodal (texte, images, audio)
    - [ ] Intégration de la génération d'images (Imagen 3)
- [ ] Provider OpenAI (GPT-4o, Sora / Runway)
    - [ ] Streaming & Tool calling
    - [ ] Endpoints de génération média (vidéo / image)
- [ ] Provider Local (Ollama / vLLM)
    - [ ] Découverte automatique des modèles locaux
    - [ ] Streaming hors-ligne sans connexion externe

### [ ] Universal Router & Cross-Delegation (Le Cerveau)
- [ ] Registre dynamique des capacités des modèles (Text, Image, Video, Audio, Code)
- [ ] Détection des manques de compétences du modèle principal
- [ ] Moteur d'injection d'outils virtuels (ex: injecter `generate_image` à Claude)
- [ ] Interception des appels d'outils et routage vers le provider adéquat
- [ ] Fusion transparente des résultats dans le flux de réponse utilisateur

### [ ] Passerelle API & Distribution
- [ ] Endpoints compatibles avec le standard OpenAI (`/v1/chat/completions`, `/v1/models`)
- [ ] Endpoints étendus Ratatosk (`/api/v1/system/status`, `/api/v1/pair`, `/api/v1/modules`)
- [ ] Streaming temps réel (Server-Sent Events) pour les réponses et les logs d'outils
- [ ] Serveur de fichiers statiques (Portail web de téléchargement pour le mode serveur)

### [ ] Système de Profils & Garde-fous (Guardrails)
- [ ] Gestion des rôles utilisateurs (Admin vs Membre / Enfant / Invité)
- [ ] Restrictions d'accès (désactivation de la sandbox, masquage de certains modèles)
- [ ] Système d'appairage rapide (génération de token et de payload QR-Code)

### [ ] Sous-système MCP (Model Context Protocol)
- [ ] Client hôte MCP en Python pour exécuter et connecter des serveurs d'outils
- [ ] Exposition automatique des outils MCP au routeur universel

### [ ] Sous-système RAG & Mémoire Documentaire
- [ ] Moteur de vectorisation et stockage local (SQLite-vec ou ChromaDB)
- [ ] Parseurs de documents (PDF, Markdown, texte brut)
- [ ] Stratégie de recherche hybride et injection dans le prompt

### [ ] Sous-système Sandbox d'Exécution
- [ ] Environnement isolé d'exécution de code (Docker / namespaces Linux / bwrap)
- [ ] Sécurisation des accès réseau et système de fichiers hôte


## [ ] Frontend (Flutter Multiplateforme)

### [ ] Socle & Architecture UI
- [ ] Initialisation du projet Flutter
- [ ] Système de thèmes & esthétique personnalisable
    - [ ] Thème sombre / clair
    - [ ] Sélecteur de palettes de couleurs et styles d'interface
- [ ] Client HTTP / SSE pour la consommation des flux de streaming

### [ ] Système de Modules Flutter Dynamiques
- [ ] Architecture de widgets enfichables selon les capacités exposées par l'API
- [ ] Module Chat conversationnel fluide avec rendu Markdown & code
- [ ] Module Galerie & Génération multimédia (Images, Vidéos)
- [ ] Module Explorateur de documents (RAG)

### [ ] Mode Administrateur
- [ ] Tableau de bord de santé du serveur (CPU, RAM, état des sous-systèmes)
- [ ] Gestionnaire visuel des clés d'API et des modèles actifs
- [ ] Panneau de configuration des profils et restrictions
- [ ] Générateur de QR Code pour l'appairage des applications filles
- [ ] Déploiement en 1 clic (démon local ou serveur distant via SSH/Docker)

### [ ] Mode Fille / Membre (Companion App)
- [ ] Assistant de premier démarrage avec scanner de QR Code
- [ ] Interface épurée sans panneaux de configuration complexes
- [ ] Application en direct des restrictions décidées par l'administrateur

### [ ] Intégration Système & Cycle de vie
- [ ] Intégration en barre des tâches (Systray / Menubar)
- [ ] Lancement / arrêt en tâche de fond du démon Python local


## [ ] Déploiement & Distribution

### [ ] Mode Solo (Local)
- [ ] Commande de démarrage unifiée avec `uv` (`uv run ratatosk start`)
- [ ] Packaging exécutable local tout-en-un

### [ ] Mode Serveur (Hôte Partagé)
- [ ] Dockerfile et `docker-compose.yml` prêts pour VPS / serveur domestique
- [ ] Landing page web hébergée pour télécharger les binaires clients (APK, Desktop)


## [ ] Documentation & Vulgarisation ("No-Jargon")

### [ ] Pédagogie Intégrée
- [ ] Infobulles d'aide et explications claires dans l'interface Flutter
- [ ] Guide d'accueil illustré pour les familles et les équipes
