# Guide utilisateur — Lisht Mail Cleaner

Ce guide décrit l'utilisation de l'application, écran par écran, ainsi que le
circuit de sécurité des suppressions.

## 1. Ce que fait l'application

1. Se connecte à votre compte Gmail (OAuth 2.0, aucun mot de passe stocké).
2. Trouve les messages **plus anciens qu'un seuil** (2 mois calendaires par défaut).
3. Les **classe localement** avec une IA (Ollama) : publicité, newsletter,
   facture, personnel, etc.
4. **Protège** les messages étoilés et les contacts déclarés importants.
5. Vous laisse **choisir** les messages à traiter, puis les met à la corbeille
   ou les supprime définitivement **après confirmation explicite**.
6. Produit des **rapports** exportables (CSV / JSON) et tient un **historique**.

> Par défaut, le **mode simulation** est actif : aucune modification réelle de
> Gmail n'est effectuée. Désactivez-le uniquement quand vous êtes prêt.

## 2. Premier lancement

1. Démarrez Ollama puis vérifiez la présence du modèle :
   ```bash
   ollama pull qwen2.5:1.5b-instruct
   ```
2. Installez les dépendances et le fichier de configuration (voir
   `docs/INSTALLATION.md`), puis placez votre `credentials.json` dans
   `credentials/` (voir `docs/GOOGLE_OAUTH.md`).
3. Lancez l'application :
   ```bash
   source .venv/bin/activate
   python app.py
   ```

## 3. Écran « Tableau de bord »

- **Se connecter à Gmail** : ouvre le navigateur pour le consentement Google.
- **Se déconnecter** : supprime les jetons locaux (ne révoque pas côté Google ;
  voir https://myaccount.google.com/permissions).
- **État de l'IA locale** : indique si Ollama répond. Si l'IA est indisponible,
  l'application **bascule automatiquement sur des règles simples** (toujours
  locale, jamais de service distant).

## 4. Écran « Analyse des e-mails »

- **Périmètre** : boîte de réception, archives, promotions, réseaux sociaux,
  forums, mises à jour, ou tous les messages.
- **Lancer l'analyse** : récupère les métadonnées et classe les messages.
  L'analyse est annulable à tout moment.
- **Filtres** : recherche par texte, catégorie, protection, recommandation,
  ou « candidats uniquement ».
- **Tableau** : chaque ligne affiche la date, l'expéditeur, l'objet, la
  catégorie, la confiance, la protection et la recommandation. Les messages
  protégés ne sont **pas** cochables.
- **Aperçu du message** : affiche les métadonnées et un extrait (le corps n'est
  jamais envoyé à une IA distante).
- **Tout sélectionner / désélectionner**.

## 5. Nettoyage contrôlé

Deux actions sont disponibles :

| Action | Réversible ? | Périmètre OAuth requis |
|---|---|---|
| **Mettre à la corbeille** | Oui (Gmail conserve 30 jours) | `gmail.modify` |
| **Supprimer définitivement** | Non | `https://mail.google.com/` |

Avant toute action, une **fenêtre de confirmation** affiche :
- le compte concerné (masqué),
- le **nombre exact** de messages,
- le nombre de messages protégés,
- la date limite d'ancienneté.

Pour une **suppression définitive**, vous devez en plus **saisir la phrase
exacte** `SUPPRIMER DÉFINITIVEMENT`. Tant que la phrase n'est pas correcte, le
bouton reste désactivé.

Garde-fous appliqués à l'exécution :
1. confirmation humaine vérifiée ;
2. limite du nombre de messages par opération ;
3. revérification de chaque message juste avant l'action (protections,
   existence, ancienneté) ;
4. en simulation, **aucun appel de modification** n'est effectué ;
5. arrêt propre en cas d'erreur, avec compte-rendu des résultats partiels.

> ⚠️ Une suppression définitive est **irréversible** : l'application ne peut pas
> restaurer un message.

## 6. Écran « Paramètres »

Onglet **Général** :
- seuil d'ancienneté (1, 2, 3, 6 ou 12 mois) ;
- mode simulation ;
- limite de suppression par opération ;
- modèle Ollama ;
- fuseau horaire ;
- niveau de journalisation.

Onglet **Planification** :
- active un **scan hebdomadaire** ;
- choix du jour et de l'heure ;
- affiche la prochaine exécution.

> Le scan planifié est **strictement en lecture seule** : il ne supprime
> jamais aucun message. Vous validez toujours chaque suppression manuellement.

Onglet **Contacts protégés** :
- ajoutez les adresses dont les messages ne doivent jamais être candidats ;
- importez une liste d'adresses.

## 7. Écran « Historique »

Liste les analyses et nettoyages passés : date, type, compte masqué, nombre de
messages analysés, protégés, candidats, sélectionnés, supprimés, échecs, mode
(simulation/réel) et statut. **Aucun contenu d'e-mail** n'y est conservé.

## 8. Écran « Rapport »

Génère une synthèse du dernier scan et permet d'exporter :
- **JSON** : rapport complet (chiffres + une entrée par message) ;
- **CSV** : une ligne par message.

Les exports contiennent des **métadonnées** (identifiant, date, expéditeur
masqué, objet tronqué, catégorie, protection, recommandation). Le **corps des
messages n'est jamais inclus**. Le compte y est **partiellement masqué**.

> Le nombre de messages supprimés ne correspond pas nécessairement à un volume
> d'espace disque libéré immédiatement mesurable.

## 9. Bonnes pratiques

1. Laissez le **mode simulation** activé pour un premier passage.
2. Vérifiez les candidats et le contenu du rapport avant toute action réelle.
3. Privilégiez la **corbeille** (réversible) plutôt que la suppression définitive.
4. Tenez à jour votre liste de **contacts protégés**.
5. Pour la suppression définitive, faites un premier essai sur un **petit lot**.

## 10. Dépannage

- **OAuth échoue** : vérifiez que la Gmail API est activée et que le type de
  client est « Application de bureau » (`docs/GOOGLE_OAUTH.md`).
- **IA indisponible** : démarrez Ollama et vérifiez `ollama list`. L'application
  reste utilisable avec le repli par règles.
- **Suppression définitive refusée (403)** : le périmètre complet n'a pas été
  accordé ; reconnectez-vous et acceptez le nouveau consentement.
- **Trousseau indisponible** : les jetons sont alors stockés dans un fichier
  local en permissions `0600` (voir `docs/SECURITY.md`).
