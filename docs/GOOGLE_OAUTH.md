# Configuration Google OAuth — Lisht Mail Cleaner

Ce guide explique, pas à pas, comment autoriser l'application à accéder à
**votre** compte Gmail. Aucun mot de passe Gmail n'est jamais demandé.

> Résumé : vous créez un « projet » dans Google Cloud, vous activez la Gmail API,
> vous déclarez l'application comme « application de bureau », puis vous
> téléchargez un fichier `credentials.json` que vous placez dans le dossier
> `credentials/` du projet.

---

## 1. Créer un projet Google Cloud

1. Ouvrez https://console.cloud.google.com/
2. Connectez-vous avec le compte Gmail concerné.
3. En haut, cliquez sur le sélecteur de projet → **Nouveau projet**.
4. Nom : par exemple `lisht-mail-cleaner`. Cliquez sur **Créer**.
5. Vérifiez que le nouveau projet est bien sélectionné en haut de la page.

## 2. Activer la Gmail API

1. Menu → **API et services** → **Bibliothèque**.
2. Recherchez **Gmail API**.
3. Cliquez sur **Gmail API** puis **Activer**.

## 3. Configurer l'écran de consentement OAuth

1. Menu → **API et services** → **Écran de consentement OAuth**.
2. Type d'utilisateur : **Externe** (puis **Créer**).
3. Renseignez :
   - **Nom de l'application** : `Lisht Mail Cleaner`
   - **E-mail d'assistance** : votre adresse
   - **Coordonnées du développeur** : votre adresse
4. Enregistrez. (Aucune validation Google n'est nécessaire pour un usage personnel.)
5. Onglet **Utilisateurs test** → **Ajouter des utilisateurs** → ajoutez votre
   adresse Gmail. Tant que l'application reste en mode « Test », seuls ces
   comptes peuvent l'autoriser.

## 4. Créer les identifiants OAuth (application de bureau)

1. Menu → **API et services** → **Identifiants**.
2. **Créer des identifiants** → **ID client OAuth**.
3. Type d'application : **Application de bureau**.
4. Nom : `Lisht Mail Cleaner Desktop`. Cliquez sur **Créer**.
5. Cliquez sur **Télécharger le JSON**.
6. Renommez le fichier en `credentials.json` et placez-le dans :

```text
lisht-mail-cleaner/credentials/credentials.json
```

> ⚠️ Ce fichier est un secret : il est déjà ignoré par `.gitignore`.
> Ne le partagez pas et ne le committez jamais.

## 5. Autoriser le compte

1. Lancez l'application : `python app.py`.
2. Sur le tableau de bord, cliquez sur **Connecter Gmail**.
3. Une page Google s'ouvre dans le navigateur. Choisissez votre compte.
4. Google affiche un avertissement « Application non vérifiée » (normal en mode test) :
   cliquez sur **Continuer**.
5. Cochez les autorisations demandées et validez.
6. Le navigateur indique que l'authentification est réussie ; l'application
   affiche le compte connecté.

## 6. À propos des périmètres (scopes)

| Périmètre | URL | Usage |
|---|---|---|
| Lecture seule | `https://www.googleapis.com/auth/gmail.readonly` | Analyser et classer les messages (phase 3-5) |
| Lecture + corbeille | `https://www.googleapis.com/auth/gmail.modify` | Déplacer vers la corbeille (pas d'effacement définitif) |
| Complet | `https://mail.google.com/` | **Suppression définitive** (obligatoire) |

Points importants :

- Google **ne propose pas** de périmètre limité à la seule suppression
  définitive. La suppression définitive immédiate exige le périmètre complet
  `https://mail.google.com/`.
- L'application **n'utilise jamais** de périmètre d'envoi d'e-mail.
- Le niveau d'accès est configuré dans **Paramètres → Général** (lecture,
  corbeille, complet). Passer au niveau « complet » nécessite une
  **reconnexion** pour accorder le nouveau consentement et le périmètre
  `https://mail.google.com/`.

## 7. Révoquer l'accès

Deux possibilités :

- **Depuis l'application** : bouton **Se déconnecter** (supprime les jetons locaux).
- **Côté Google** : https://myaccount.google.com/permissions → sélectionner
  l'application → **Supprimer l'accès**.

## 8. Où sont stockés les jetons

- Par défaut, dans le **trousseau du bureau** (GNOME Keyring / Secret Service).
- En repli, dans un fichier `data/token_*.json` protégé en `0600`.
- Jamais dans Git, jamais dans les journaux.

## 9. Problèmes courants

| Message | Cause probable | Solution |
|---|---|---|
| `credentials.json introuvable` | Fichier non placé au bon endroit | Le placer dans `credentials/credentials.json` |
| `Gmail API n'est pas activée` | API non activée | Refaire l'étape 2 |
| `access_denied` | Compte non ajouté aux utilisateurs test | Étape 3.5 |
| `Jeton expiré ou révoqué` | Accès retiré côté Google | Se reconnecter |
| `Quota dépassé` | Trop de requêtes | Attendre et réessayer |
| `Application non vérifiée` | Mode test | Cliquer sur « Continuer » (usage personnel) |

## 10. Bonnes pratiques de sécurité

- Ne committez jamais `credentials.json`, `token.json` ni le dossier `data/`.
- Révoquez l'accès si vous n'utilisez plus l'application.
- Utilisez un compte de test dédié pour les tests d'intégration.
