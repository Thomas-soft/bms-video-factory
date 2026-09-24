# BMS Factory — Privacy Policy / Politique de confidentialité

**Version 1.0 — 17 September 2026 / 17 septembre 2026**

> **À remplir par Thomas avant publication** (trois valeurs, nulle part ailleurs dans le fichier) :
> `«CONTACT-BMS»` → adresse e-mail d'assistance de BMS · `«RAISON-SOCIALE-BMS»` → raison sociale
> et adresse · `«URL-PUBLIQUE»` → l'URL de la page une fois en ligne (à reporter aussi dans
> `STATE.md`, dans l'écran de consentement Google et dans `docs/AUDIT-API.md`).
> La raison sociale est une question ouverte à Alek (`STATE.md`) : tant qu'elle manque, publier
> avec « BMS » seul est acceptable pour l'écran de consentement, pas pour les mentions légales.

---

## English

### 1. Who operates this application

**BMS Factory** ("the Application") is an internal, non-public desktop tool operated by
**«RAISON-SOCIALE-BMS»** ("BMS", "we"). It is not distributed, not sold, and not offered to
third parties. Its only users are the people who operate BMS's own YouTube channels.

Contact: **«CONTACT-BMS»**

### 2. What the Application does

The Application produces videos locally on BMS's own computers and uses the YouTube API
Services to:

- upload those videos to **YouTube channels owned by BMS**, and set their metadata (title,
  description, tags, category, language, thumbnail, captions, privacy status, synthetic-content
  disclosure);
- read **BMS's own channel and video statistics** (views, watch time, average view duration,
  subscribers, traffic sources, audience retention, and revenue metrics where they exist), in
  order to decide what BMS publishes next.

By using the Application, you are agreeing to be bound by the
[YouTube Terms of Service](https://www.youtube.com/t/terms).

### 3. Which Google data is read and written

| Data | Read | Written | Source |
|---|---|---|---|
| Channel id, title, upload playlist id of channels the signed-in account owns | yes | no | YouTube Data API v3 (`channels.list?mine=true`) |
| Video ids, metadata and processing status of BMS's own videos | yes | yes | YouTube Data API v3 (`videos.insert`, `videos.list`, `videos.update`) |
| Thumbnails and caption tracks of BMS's own videos | no | yes | YouTube Data API v3 (`thumbnails.set`, `captions.insert`) |
| Aggregated statistics of BMS's own channels and videos | yes | no | YouTube Analytics API, YouTube Reporting API |
| OAuth 2.0 access and refresh tokens for the signed-in Google account | yes | yes | Google OAuth 2.0 |

The Application **never** reads, collects or stores data about other people's channels,
videos, comments, subscribers or viewers. It does not identify individual viewers; YouTube
Analytics data is aggregated by YouTube before we receive it.

### 4. Where the data is stored

Everything stays **on BMS's own machines**. There is no server, no database in the cloud, no
analytics provider, no telemetry, no crash reporting.

- OAuth tokens are written to `secrets/tokens/<channel>.json` on the local disk, with file
  permissions restricted to the operating user (mode 600), outside version control.
- Statistics and API responses are written to local files under `workspace/`.
- Nothing is transmitted anywhere except to Google's own API endpoints.

### 5. Sharing

We do **not** sell, rent, share, transfer or disclose any Google user data to any third party,
for any purpose, including advertising, model training, or analytics. No human other than
BMS's own operators has access to it.

### 6. Retention and deletion

- **Authorisation data** (tokens) is kept only as long as the channel is operated by BMS. It is
  deleted when access is revoked or when the channel is closed.
- **API data** is refreshed on each run and is not accumulated as a historical archive beyond
  what BMS needs to decide its own publishing schedule. Data obtained from the YouTube API
  Services is stored for no longer than **30 days** unless the YouTube API Services Terms of
  Service permit a longer period, after which it is deleted or refreshed from the API.
- You may revoke the Application's access at any time at
  [https://myaccount.google.com/permissions](https://myaccount.google.com/permissions). Revoking
  access invalidates the stored token; deleting the local token file removes it from the disk.
- To request deletion of any data held by the Application, write to **«CONTACT-BMS»**.

### 7. Security

Tokens are stored with owner-only file permissions and are never printed to logs, never
committed to the code repository, and never sent anywhere other than Google. The Application
does not use any browser automation, session sharing or stored login cookies; all access to
Google services goes through OAuth 2.0.

### 8. Children

The Application is an internal production tool. It is not directed at children and collects no
data from anyone other than the BMS operator who signs in.

### 9. Changes

Any change to this policy is published at **«URL-PUBLIQUE»** with a new version number and
date. The version in force is the one published at that address.

---

## Français

### 1. Qui exploite cette application

**BMS Factory** (« l'Application ») est un outil de bureau **interne et non public**, exploité
par **«RAISON-SOCIALE-BMS»** (« BMS », « nous »). Il n'est ni distribué, ni vendu, ni proposé à
des tiers. Ses seuls utilisateurs sont les personnes qui exploitent les chaînes YouTube de BMS.

Contact : **«CONTACT-BMS»**

### 2. Ce que fait l'Application

L'Application produit des vidéos localement, sur les ordinateurs de BMS, et utilise les
services API de YouTube pour :

- publier ces vidéos sur **des chaînes YouTube appartenant à BMS** et en renseigner les
  métadonnées (titre, description, mots-clés, catégorie, langue, miniature, sous-titres, état de
  confidentialité, divulgation de contenu synthétique) ;
- lire **les statistiques des chaînes et des vidéos de BMS** (vues, durée de visionnage, durée
  moyenne, abonnés, sources de trafic, courbe de rétention et, le cas échéant, revenus), afin de
  décider ce que BMS publie ensuite.

En utilisant l'Application, vous acceptez d'être lié par les
[conditions d'utilisation de YouTube](https://www.youtube.com/t/terms).

### 3. Quelles données Google sont lues et écrites

| Donnée | Lue | Écrite | Source |
|---|---|---|---|
| Identifiant, titre et playlist d'uploads des chaînes détenues par le compte connecté | oui | non | YouTube Data API v3 (`channels.list?mine=true`) |
| Identifiants, métadonnées et état de traitement des vidéos de BMS | oui | oui | YouTube Data API v3 (`videos.insert`, `videos.list`, `videos.update`) |
| Miniatures et pistes de sous-titres des vidéos de BMS | non | oui | YouTube Data API v3 (`thumbnails.set`, `captions.insert`) |
| Statistiques agrégées des chaînes et vidéos de BMS | oui | non | YouTube Analytics API, YouTube Reporting API |
| Jetons OAuth 2.0 (accès et rafraîchissement) du compte Google connecté | oui | oui | Google OAuth 2.0 |

L'Application **ne lit, ne collecte et ne stocke jamais** de données relatives aux chaînes,
vidéos, commentaires, abonnés ou spectateurs de tiers. Elle n'identifie aucun spectateur : les
données Analytics sont agrégées par YouTube avant de nous parvenir.

### 4. Où les données sont stockées

Tout reste **sur les machines de BMS**. Aucun serveur, aucune base de données distante, aucun
prestataire d'analyse, aucune télémétrie, aucun rapport d'incident automatique.

- Les jetons OAuth sont écrits dans `secrets/tokens/<chaîne>.json` sur le disque local, en
  permissions restreintes au seul propriétaire (mode 600), hors du dépôt de code.
- Les statistiques et réponses de l'API sont écrites dans des fichiers locaux sous `workspace/`.
- Rien n'est transmis ailleurs qu'aux points d'accès de l'API Google.

### 5. Partage

Nous ne vendons, ne louons, ne partageons, ne transférons et ne divulguons **aucune** donnée
utilisateur Google à un tiers, pour quelque finalité que ce soit — publicité, entraînement de
modèles ou analyse comprises. Aucune personne autre que les exploitants de BMS n'y a accès.

### 6. Conservation et suppression

- Les **données d'autorisation** (jetons) sont conservées tant que la chaîne est exploitée par
  BMS. Elles sont supprimées à la révocation de l'accès ou à la fermeture de la chaîne.
- Les **données d'API** sont rafraîchies à chaque exécution et ne sont pas accumulées en
  archive historique au-delà de ce qui est nécessaire à la programmation des publications de
  BMS. Les données obtenues des services API de YouTube sont conservées **30 jours au plus**,
  sauf durée plus longue permise par les conditions d'utilisation des services API de YouTube ;
  au-delà, elles sont supprimées ou rafraîchies depuis l'API.
- Vous pouvez révoquer l'accès de l'Application à tout moment sur
  [https://myaccount.google.com/permissions](https://myaccount.google.com/permissions). La
  révocation invalide le jeton stocké ; la suppression du fichier de jeton l'efface du disque.
- Pour demander la suppression de données détenues par l'Application, écrivez à
  **«CONTACT-BMS»**.

### 7. Sécurité

Les jetons sont stockés en permissions propriétaire uniquement, ne sont jamais écrits dans les
journaux, jamais versionnés dans le dépôt, et jamais envoyés ailleurs qu'à Google.
L'Application n'utilise aucune automatisation de navigateur, aucun partage de session et aucun
cookie de connexion stocké : tout accès aux services Google passe par OAuth 2.0.

### 8. Mineurs

L'Application est un outil de production interne. Elle ne s'adresse pas aux mineurs et ne
collecte aucune donnée sur quiconque hors de l'exploitant BMS qui s'y connecte.

### 9. Modifications

Toute modification de cette politique est publiée à l'adresse **«URL-PUBLIQUE»**, avec un
nouveau numéro de version et une date. La version en vigueur est celle publiée à cette adresse.
