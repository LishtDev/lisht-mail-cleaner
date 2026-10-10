# Lisht Mail Cleaner

Application de bureau Linux (PySide6) pour analyser un compte Gmail et nettoyer
les e-mails anciens, avec **classification par IA locale** (Ollama) et
**suppression conditionnée à une confirmation humaine explicite**.

> État du projet : **Phase 8 terminée** — version **0.1.0**. Application
> fonctionnelle et testée. Voir la section « Avancement » et `docs/USER_GUIDE.md`.

## Fonctionnalités prévues

- Connexion sécurisée à un compte Gmail via OAuth 2.0 (aucun mot de passe stocké).
- Détection des messages plus anciens qu'un seuil configurable (défaut : 2 mois calendaires).
- Classification locale par IA (publicité, newsletter, facture, personnel, etc.).
- Protection des messages étoilés et des contacts déclarés importants.
- Mode simulation (aucune modification de Gmail).
- Suppression définitive uniquement après confirmation explicite.
- Rapports exportables (CSV / JSON) et historique des opérations.
- Planification hebdomadaire du scan (sans suppression automatique).

## Principe de confidentialité

Le contenu des e-mails n'est **jamais** envoyé à un service d'IA distant :
le moteur d'analyse tourne **localement via Ollama**. L'accès à Gmail se fait
en revanche forcément en ligne, via l'API officielle Google.

## Prérequis

- Linux Mint 22.x (ou Ubuntu 24.04 compatible)
- Python 3.12 (fourni par le système)
- Ollama (moteur IA local)
- Un projet Google Cloud avec la Gmail API activée (voir `docs/GOOGLE_OAUTH.md`)

## Installation rapide

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Détails complets : `docs/INSTALLATION.md`.

## Lancement

```bash
source .venv/bin/activate
python app.py
```

## Tests

```bash
source .venv/bin/activate
pytest -q
```

## Structure du projet

```text
app.py                  Point d'entree de l'application
config/settings.py      Configuration et valeurs par defaut
src/core/               Modeles de donnees partages
src/ui/                 Interface PySide6
src/gmail/              Authentification et acces Gmail (phase 3)
src/ai/                 Classification locale (phase 4)
src/services/           Orchestration metier (scan, cleanup, rapports, planification)
src/database/           Base SQLite locale
src/utils/              Dates, journalisation, validation
tests/                  Tests pytest
docs/                   Documentation en francais
data/                   Donnees locales (base, jamais commitees)
```

## Avancement

- [x] Phase 1 : analyse et conception
- [x] Phase 2 : squelette, environnement, interface de base, base de donnees
- [x] Phase 3 : connexion Gmail (OAuth, client, pagination)
- [x] Phase 4 : dates, protections, classification locale
- [x] Phase 5 : interface de selection
- [x] Phase 6 : suppression controlee
- [x] Phase 7 : rapports et planification
- [x] Phase 8 : validation finale

## Documentation

- `docs/INSTALLATION.md` — installation et dépendances.
- `docs/GOOGLE_OAUTH.md` — créer le projet Google Cloud et `credentials.json`.
- `docs/USER_GUIDE.md` — guide utilisateur écran par écran.
- `docs/SECURITY.md` — modèle de sécurité.
- `docs/ARCHITECTURE.md` — architecture technique.
- `CHANGELOG.md` — journal des modifications.

## Planification hebdomadaire

Le scan planifie s'active dans **Paramètres → Planification**. Il exécute
uniquement une analyse **en lecture seule** : aucune suppression automatique
n'a jamais lieu. Chaque suppression reste subordonnée à une confirmation
humaine dans l'application.

## Limites connues (à ce stade)

- La suppression définitive nécessite le périmètre OAuth complet (`https://mail.google.com/`).
- Les rapports utilisent les métadonnées (identifiant, date, expéditeur masqué,
  catégorie) ; ils n'incluent jamais le corps des messages.

## Licence et données

Aucun secret, jeton ou e-mail n'est stocké dans ce dépôt. Voir
`docs/SECURITY.md` pour le modèle de sécurité.
