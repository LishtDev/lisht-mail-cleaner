# Sécurité — Lisht Mail Cleaner

## 1. Modèle de sécurité en résumé

- **Aucun mot de passe Gmail** n'est jamais demandé ni stocké.
- Les e-mails sont analysés par une **IA locale** (Ollama) : leur contenu ne part
  pas vers un service d'IA distant.
- L'accès à Gmail se fait **en ligne**, via l'API officielle Google et OAuth 2.0.
  L'application n'est donc **pas** entièrement hors ligne.
- La **suppression définitive** est l'action la plus dangereuse : elle exige une
  double confirmation et l'ajout d'un périmètre OAuth complet.

## 2. Périmètres OAuth

| Périmètre | URL | Pour quoi |
|---|---|---|
| Lecture | `gmail.readonly` | Analyser et classer |
| Corbeille | `gmail.modify` | Déplacer vers la corbeille (réversible) |
| Complet | `https://mail.google.com/` | **Suppression définitive** |

Google n'expose pas de périmètre limité à la seule suppression définitive :
`users.messages.delete` exige le périmètre complet. L'application ne demande
jamais de droit d'**envoi** d'e-mail.

## 3. Stockage des jetons OAuth

- Priorité : **trousseau du bureau Linux** (GNOME Keyring / Secret Service).
- Repli : fichier `data/token_<compte>.json` en permissions `0600`.
- Les jetons ne sont **jamais** écrits dans Git ni dans les journaux.

## 4. Journalisation

Un filtre (`RedactingFilter`) masque les motifs sensibles
(`ya29.*`, `1//*`, `access_token`, `refresh_token`, `client_secret`,
en-têtes `Authorization: Bearer`). Par défaut, **aucune donnée personnelle**
(adresse, objet, corps) n'est journalisée.

## 5. Contenu des e-mails = donnée non fiable

Le contenu d'un message peut contenir des tentatives de manipulation
(« prompt injection »). Il est traité comme donnée, jamais comme instruction :
- les instructions trouvées dans un e-mail sont ignorées ;
- les pièces jointes ne sont ni ouvertes ni exécutées ;
- l'IA ne déclenche **jamais** d'action destructive.

## 6. Risques de suppression définitive

- La suppression définitive (`delete`) est **irréversible** : l'application ne
  peut pas restaurer un message.
- Garde-fous : mode simulation, liste de candidats avant action, protections
  (étoilés, contacts), revérification avant suppression, limite par opération,
  confirmation explicite distincte.
- **Recommandation** : conserver le mode simulation activé par défaut.

## 7. Base SQLite locale

- Contient : paramètres, contacts protégés, historique des opérations.
- **Ne contient pas** le corps des e-mails ni les jetons.
- Permissions du fichier restreintes au propriétaire (`0600`).

## 8. Dépendances

Les dépendances proviennent de PyPI (officiel). Évitez d'installer des paquets
depuis des sources non fiables. Vérifiez régulièrement les mises à jour.

## 9. Révocation et nettoyage

- Bouton **Se déconnecter** : supprime les jetons locaux.
- Suppression de l'accès côté Google :
  https://myaccount.google.com/permissions
- Nettoyage local : supprimer le dossier `data/` (base + jetons de repli).

## 10. Limites de confidentialité

- L'analyse de contenu par l'IA reste locale.
- L'accès au compte Gmail transite obligatoirement par les serveurs Google.
- Aucun engagement de chiffrement du disque : utilisez le chiffrement de votre
  système si nécessaire.
