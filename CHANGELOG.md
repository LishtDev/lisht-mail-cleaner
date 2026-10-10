# Journal des modifications — Lisht Mail Cleaner

Le format suit les principes de « Keep a Changelog ». La numérotation suit
`MAJOR.MINEUR.CORRECTIF`.

## [0.1.0] — 2026-10-10

### Ajouté

- **Phase 1 — Conception** : analyse de l'environnement, architecture,
  périmètres OAuth, choix du modèle local et plan de développement.
- **Phase 2 — Squelette** : environnement virtuel, structure du projet,
  interface PySide6 de base, configuration, base SQLite locale, journalisation
  expurgée.
- **Phase 3 — Connexion Gmail** : authentification OAuth 2.0 (trousseau +
  repli fichier `0600`), client Gmail en lecture avec pagination, service de
  connexion, tests avec client simulé.
- **Phase 4 — Analyse** : calcul d'ancienneté en mois calendaires, protections
  (étoilés, contacts, expéditeur incertain), classification locale via Ollama
  avec repli par règles, service de scan.
- **Phase 5 — Interface d'analyse** : sélection, filtres, aperçu, panneau de
  contacts protégés, mode simulation.
- **Phase 6 — Suppression contrôlée** : corbeille (réversible) et suppression
  définitive (irréversible) avec confirmation explicite, phrase exacte,
  limite par opération, revérification avant action, historique des opérations.
- **Phase 7 — Rapports et planification** : export CSV / JSON, écran
  d'historique, scan hebdomadaire planifié en lecture seule.

### Sécurité

- Aucun mot de passe Gmail stocké ; jetons dans le trousseau avec repli `0600`.
- Purge des secrets dans les journaux (jetons, `client_secret`, en-têtes
  `Authorization`).
- Contenu des e-mails traité comme donnée non fiable (anti « prompt injection »).
- L'IA locale ne déclenche jamais d'action destructive : toute suppression
  exige une confirmation humaine.
- Exports et historique sans corps d'e-mail ; compte masqué.

### Documentation

- `docs/INSTALLATION.md`, `docs/GOOGLE_OAUTH.md`, `docs/SECURITY.md`,
  `docs/ARCHITECTURE.md`, `docs/USER_GUIDE.md`.
