# Règles de développement Flutter

## Phase 1 : Création (Nouveau fichier / Nouvel écran)
- Lorsque l'utilisateur demande de concevoir un nouvel écran ou un nouveau composant complet :
  - Génère l'écran complet avec une mise en page claire.
  - Découpe immédiatement l'interface en sous-widgets lisibles plutôt que de créer un seul bloc monolithique.
  - Utilise l'état local minimal nécessaire.

## Phase 2 : Retouche et Maintenance (Fichier ou composant existant)
- Lorsque l'utilisateur demande une modification, un ajustement ou un fix :
  - N'altère que le widget enfant ou la méthode ciblée.
  - Interdiction de régénérer l'ensemble de la classe ou du fichier.
  - Conserve strictement l'architecture en place sans ajouter de nouvelles couches d'abstraction.