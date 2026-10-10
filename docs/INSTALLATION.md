# Installation — Lisht Mail Cleaner

Guide destiné à un débutant sous **Linux Mint 22.x**.

## 1. Préparer le système

Le projet n'a pas besoin de privilèges administrateur pour fonctionner.
Si un paquet système manque (bibliothèques Qt), ils s'installent via le
gestionnaire de paquets de Mint. Sur une installation Mint standard, les
bibliothèques nécessaires sont déjà présentes.

Vérifier Python :

```bash
python3 --version        # doit afficher Python 3.12.x
```

## 2. Récupérer le projet

```bash
cd ~/Documents
git clone <url-du-depot> lisht-mail-cleaner
cd lisht-mail-cleaner
```

(Si vous avez reçu le projet sous forme d'archive, décompressez-le puis
placez-vous dans le dossier.)

## 3. Créer l'environnement virtuel

L'environnement virtuel isole les dépendances du projet du reste du système.

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Le prompt doit maintenant commencer par `(.venv)`.

## 4. Installer les dépendances

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Cette étape télécharge notamment PySide6 (interface graphique) — comptez
plusieurs dizaines de Mo.

## 5. Créer le fichier de configuration local

```bash
cp .env.example .env
```

Le fichier `.env` reste **local** : il n'est jamais envoyé sur Git.
Vous pouvez y ajuster le fuseau horaire, le seuil d'ancienneté, le mode
simulation, etc.

## 6. Lancer l'application

```bash
python app.py
```

La fenêtre « Lisht Mail Cleaner » doit s'ouvrir sur le tableau de bord.

## 7. Lancer les tests

```bash
pytest -q
```

Tous les tests doivent passer (ils n'effectuent aucune action sur Gmail).

## 8. Étapes suivantes

- Installer Ollama et un modèle local : voir la phase 4 de la documentation.
- Configurer l'accès Gmail : voir `docs/GOOGLE_OAUTH.md`.

## Désactivation de l'environnement

```bash
deactivate
```

## Dépannage

| Problème | Solution |
|---|---|
| `python3: command not found` | `sudo apt install python3 python3-venv` |
| Erreur Qt « could not load the Qt platform plugin xcb » | Installer `libxcb-*` via apt |
| `pip install` échoue (externally-managed) | Vérifier que le venv est bien activé |
| Base SQLite inaccessible | Vérifier les droits sur le dossier `data/` |
