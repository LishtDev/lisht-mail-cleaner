# Architecture — Lisht Mail Cleaner

## 1. Vue d'ensemble

L'application suit une architecture **en couches**, avec une séparation nette
entre l'interface, l'accès à Gmail, la classification, la protection et la
suppression.

```text
        +-------------------------------------------+
        |              UI (PySide6)                 |
        |  dashboard, table, settings, rapports      |
        +------------------+------------------------+
                           | appelle
        +------------------v------------------------+
        |           Services (orchestration)        |
        |  connection, scan, protection, cleanup,    |
        |  scheduler, report                         |
        +----+-------------+-------------+-----------+
             |             |             |
     +-------v---+  +------v-----+  +----v--------+
     |  gmail/   |  |    ai/     |  | database/   |
     | client,   |  | classifier |  | SQLite      |
     | auth      |  | ollama     |  | repositories|
     +-----------+  +------------+  +-------------+
```

## 2. Rôle de chaque module

| Module | Rôle |
|---|---|
| `app.py` | Bootstrap : config, logs, base, services, fenêtre Qt |
| `config/settings.py` | Configuration `.env`, valeurs par défaut sûres |
| `src/core/models.py` | Modèles partagés (`EmailMessage`, `Classification`, `Candidate`, enums) |
| `src/ui/` | Interface uniquement ; aucune logique Gmail/IA |
| `src/ui/workers.py` | Exécution des tâches longues hors du thread graphique |
| `src/gmail/base.py` | Interface abstraite du client Gmail |
| `src/gmail/authentication.py` | OAuth2, stockage des jetons, révocation |
| `src/gmail/gmail_client.py` | Client réel (pagination, métadonnées, corps) |
| `src/gmail/email_repository.py` | Requêtes Gmail et parsing des métadonnées |
| `src/gmail/fake_client.py` | Faux client pour tests/simulation |
| `src/ai/local_model.py` | Accès à Ollama et vérification du modèle |
| `src/ai/classifier.py` | Classification par IA + repli par règles + validation |
| `src/services/connection_service.py` | État de la connexion Gmail |
| `src/services/scan_service.py` | Scan en lecture seule et construction des candidats |
| `src/services/protection_service.py` | Règles de protection (étoilés, contacts, prudence) |
| `src/services/cleanup_service.py` | Suppression contrôlée (phase 6) |
| `src/services/scheduler_service.py` | Scan hebdomadaire (phase 7) |
| `src/services/report_service.py` | Rapports CSV/JSON (phase 7) |
| `src/database/` | Connexion SQLite et dépôts de données |
| `src/utils/` | Dates, journalisation, validation |

## 3. Circulation des données

1. L'UI demande un scan au `ScanService`.
2. `ScanService` interroge le client Gmail (pagination complète).
3. Chaque message est filtré (périmètre, ancienneté stricte).
4. `ProtectionService` exclut les messages protégés.
5. Le `Classifier` (IA locale, sinon règles) produit une recommandation.
6. `ScanService` renvoie des `Candidate` (jamais présélectionnés).
7. L'UI affiche la liste ; l'utilisateur choisit.
8. En phase 6, `CleanupService` revérifie protections et existence, puis agit.

## 4. Séparation interface / Gmail / classification / suppression

- L'UI **ne parle jamais** directement à l'API Gmail ni à Ollama.
- L'accès Gmail est isolé derrière `GmailClientProtocol`, ce qui permet de
  substituer un faux client dans les tests.
- La classification est isolée dans `src/ai/` : on peut utiliser l'IA ou les
  règles sans changer le reste.
- La suppression est isolée dans `CleanupService` : c'est **le seul** endroit
  qui pourra appeler une méthode destructive, sous conditions vérifiables.

## 5. Stratégie de test

- **Tests unitaires** (`pytest`, par défaut) : dates, validation, base,
  journalisation, parsing Gmail, protection, classification, scan. Aucun accès
  réseau, aucun e-mail réel.
- **Faux client Gmail** : simule l'API pour tester la logique de bout en bout.
- **Tests d'intégration opt-in** (`pytest -m integration`) : moteur IA local
  (et, plus tard, compte Gmail de test). Jamais de suppression définitive.
- **Objectif de sécurité** : vérifier qu'aucun chemin d'exécution ne peut
  appeler la suppression définitive sans confirmation humaine valide.
