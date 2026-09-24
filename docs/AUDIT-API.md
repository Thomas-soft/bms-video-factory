# Dossier d'audit — YouTube API Services

> **Formulaire** : https://support.google.com/youtube/contact/yt_api_form
> **Projet** : `bms-factory` (un seul projet Google Cloud pour tout le portefeuille — décision
> d'architecture, `CONFORMITE.md` § 1). **Un seul audit à obtenir, et il conditionne tout.**
> **Objet de la demande** : *Compliance audit* — pas d'extension de quota (voir § 4).
>
> Ce fichier est fait pour être **copié champ par champ** dans le formulaire. Ce qui reste entre
> guillemets français (`«…»`) est une valeur que le dossier n'a pas : elle bloque le dépôt.

---

## 0. Ce qui manque encore pour déposer

| Champ du formulaire | Valeur | Qui tranche |
|---|---|---|
| Legal company name, address | `«RAISON-SOCIALE-BMS»` | **Alek** — question ouverte de `STATE.md` |
| Business / technical contact e-mail | `«CONTACT-BMS»` | **Alek / Thomas** |
| Privacy policy URL | `«URL-PUBLIQUE»` (`docs/PRIVACY.md` publiée) | **Thomas** |
| Google Cloud **project number** | relevé sur la page d'accueil de la console | **Thomas** |
| Demo account credentials | compte Google de la chaîne de test | **Thomas** |
| Public website | `«SITE-BMS»` — sinon, écrire « no public website; internal tool » | **Alek** |

Le formulaire demande des **captures d'écran**, pas une vidéo (§ 6). La vidéo de démonstration
relève de la *vérification OAuth des scopes sensibles*, dont nous sommes dispensés tant que
l'application reste sous 100 utilisateurs. Elle est tout de même scénarisée au § 7 : elle sert de
pièce jointe si un examinateur la réclame, et de preuve interne.

---

## 1. API Client name

`BMS Factory`

Le nom d'un client API **ne peut pas contenir « YouTube »** : celui-ci n'en contient pas.

---

## 2. Description de l'application (champ « description of your business / API usage »)

> À coller tel quel, en anglais.

```
BMS Factory is an internal, non-public desktop application. It is not distributed, not sold,
and not available to any third party. Its only users are the operators of BMS's own YouTube
channels — fewer than five people.

The application produces videos locally on BMS's own computers (script writing, synthetic
voice-over, illustration, editing — all on-device, no third-party service) and then uses the
YouTube API Services for two things:

1. PUBLISHING BMS'S OWN VIDEOS. videos.insert uploads the finished file to a channel owned by
   BMS, with its complete metadata set at insertion time: title, description including the AI
   assistance disclosure and the asset attribution block, tags, category, language,
   status.containsSyntheticMedia, thumbnails.set for the custom thumbnail and captions.insert
   for the subtitle track. Uploads are created with privacyStatus=private and are switched to
   public by a human in YouTube Studio after an editorial review.

2. READING BMS'S OWN PERFORMANCE DATA. The YouTube Analytics API and the YouTube Reporting API
   are used to read aggregated statistics for BMS's own channels only — views, watch time,
   average view duration, subscribers, traffic sources, audience retention curves, and revenue
   metrics where they exist. These numbers decide what BMS produces next. No viewer is
   identified; the data arrives already aggregated by YouTube.

The application also performs EDITORIAL RESEARCH on public data: it reads public channel and
video metadata of third-party channels through channels.list, playlists.list and
playlistItems.list, using an API key, to measure format conventions (publication cadence,
title patterns, video length) in the niches BMS works in. This research data is stored locally
for no more than 30 calendar days and is then deleted or refreshed, as required by Developer
Policies III.E.4. Only derived aggregate measurements (medians, counts) are kept beyond that
period; they carry no API data. This research data is never published, never shared, never
sold, and never used to contact or target anyone. search.list is not used at all: the research
works from explicit channel lists and their uploads playlists.

All data, of every kind, is stored on BMS's own machines. There is no server, no cloud
database, no analytics provider, no telemetry. No Google user data is ever sold, rented,
shared, transferred or disclosed to any third party, for any purpose, including advertising
and machine-learning training. OAuth tokens are stored on the local disk with owner-only file
permissions and are never transmitted anywhere except to Google.

The application uses no browser automation of any kind. It never drives youtube.com or
studio.youtube.com with Selenium, Playwright or any similar tool, and it does not scrape any
YouTube surface. Every access to YouTube data goes through the YouTube API Services.

The application does not automate views, likes, comments, subscriptions or any other form of
engagement, and offers no such feature to anyone.

Revenue model: BMS earns from advertising revenue on its own channels (YouTube Partner
Program, once eligible) and from affiliate commissions on products mentioned in its own video
descriptions. The application itself is never monetised: it is not sold, licensed or offered
as a service. No revenue is derived from YouTube API data itself.
```

---

## 3. Justification scope par scope

| Scope | Appels employés | Pourquoi il est nécessaire |
|---|---|---|
| `youtube.upload` | `videos.insert` | Seul moyen de déposer le fichier vidéo produit sur la chaîne de BMS. Sans lui, l'application n'a aucune raison d'exister. |
| `youtube` | `videos.list`, `videos.update`, `thumbnails.set`, `captions.insert`, `channels.list?mine=true`, `playlistItems.insert` | Poser la miniature et la piste de sous-titres, relire ce que YouTube a effectivement enregistré (`privacyStatus`, `processingDetails`), corriger une fiche, programmer la mise en ligne après audit, ranger la vidéo dans la playlist de la chaîne, et identifier la chaîne à laquelle le jeton donne accès. `youtube.upload` seul ne permet aucun de ces appels. |
| `yt-analytics.readonly` | `reports.query` (YouTube Analytics API) | Lire les statistiques agrégées des **seules chaînes de BMS** : vues, durée de visionnage, durée moyenne, abonnés, sources de trafic, courbe de rétention. C'est la boucle de rétroaction qui décide du sujet suivant. |
| `yt-analytics-monetary.readonly` | `reports.query` avec les métriques de revenus | Lire les revenus des **seules chaînes de BMS** une fois admises au programme partenaire, pour arbitrer entre niches. Sans ce scope, l'arbitrage se fait à l'aveugle sur le seul volume de vues. |

Aucun autre scope n'est demandé. L'application ne demande ni `youtubepartner`, ni aucun scope
Gmail, Drive, Contacts ou Calendar.

---

## 4. Quota demandé

**Demande : le quota par défaut suffit. Nous ne demandons pas d'extension** — seulement l'audit
de conformité qui lève le forçage en privé des uploads.

Volume réel, chiffré sur la capacité mesurée de la machine (≈ 7 vidéos par semaine, tous
canaux confondus) et sur le plafond de cadence que BMS s'impose (2 vidéos par semaine et par
chaîne, `CONFORMITE.md` § 6) :

| Appel | Unités | Pic par jour | Unités par jour |
|---|---|---|---|
| `videos.insert` | 1 600 | 4 | 6 400 |
| `captions.insert` | 400 | 4 | 1 600 |
| `thumbnails.set` | 50 | 4 | 200 |
| `videos.list` (vérification après upload) | 1 | ≈ 20 | 20 |
| `channels.list?mine=true` | 1 | ≈ 10 | 10 |
| `playlistItems.list` (veille éditoriale, listes explicites) | 1 | ≈ 200 | 200 |
| `search.list` | 100 | **0** | **0** |
| **Total, jour de pic** | | | **≈ 8 430 / 10 000** |

- **Uploads par jour** : 4 au pic, 2 en régime courant. L'ordonnanceur est **plafonné en dur à
  6 uploads par jour, toutes chaînes confondues** : à 1 600 unités, le quota d'unités sature
  avant le compteur de 100 `videos.insert`.
- **Lectures par jour** : ≈ 230 appels de lecture, ≈ 230 unités. Les statistiques de BMS
  passent par l'API Analytics et l'API Reporting, qui ont leur propre quota.
- **`search.list` : zéro appel.** La veille travaille sur des listes de chaînes explicites et
  leurs playlists d'uploads, jamais par recherche. C'est un choix d'architecture pris à
  l'étape 2, précisément pour ne pas dépendre du compartiment de 100 appels.

Si le portefeuille dépasse **6 chaînes actives**, une extension de quota sera demandée
séparément, avec les chiffres mesurés de l'exploitation.

---

## 5. Conformité aux Developer Policies — checklist

| Point de politique | État | Preuve dans le dépôt |
|---|---|---|
| III.E.4 — données API conservées ≤ 30 jours, puis supprimées ou rafraîchies | respecté | `fetched_at` sur chaque enregistrement du registre ; purge à 30 jours ; `CONFORMITE.md` § 9 |
| Interdiction du scraping et de tout accès hors API | respecté | Aucune automatisation de navigateur nulle part ; `CONFORMITE.md` § 2 l'inscrit comme contrainte d'architecture. Playwright n'est employé que pour rendre localement une miniature HTML→PNG, sans toucher aucun service Google |
| Interdiction de yt-dlp et du téléchargement de vidéos tierces | respecté | `CONFORMITE.md` § 9 ; aucune dépendance yt-dlp dans `pyproject.toml` |
| III.I.2 — pas de manipulation d'engagement (vues, likes, commentaires, abonnements automatisés) | respecté | Aucune fonction de ce type n'existe dans le code |
| Divulgation du contenu altéré ou synthétique | respecté | `status.containsSyntheticMedia` posé plan par plan à la génération, jamais reconstitué à l'upload ; `CONFORMITE.md` § 3 couche 1 |
| Divulgation de la promotion payante | respecté | L'API n'expose pas de champ d'écriture : le geste reste manuel dans Studio et l'uploader lève une alerte bloquante ; vérification a posteriori par `paidProductPlacementDetails` |
| Politique de confidentialité accessible et exacte | respecté | `docs/PRIVACY.md`, publiée à `«URL-PUBLIQUE»` |
| Pas de vente ni de partage de données utilisateur Google | respecté | Stockage local seul, aucun serveur, aucun prestataire tiers |
| Jetons stockés en sécurité | respecté | `secrets/tokens/*.json`, mode 600, hors dépôt (`.gitignore`), jamais journalisés (`factory/core/secrets.py`) |
| Conditions d'utilisation de YouTube acceptées et citées | respecté | `docs/PRIVACY.md` § 2 renvoie à https://www.youtube.com/t/terms |

---

## 6. Captures d'écran à joindre

Quatre, prises par Thomas, sans aucun jeton ni identifiant visible :

1. **La politique de confidentialité en ligne**, URL visible dans la barre d'adresse.
2. **L'écran de consentement OAuth** tel qu'il apparaît à l'opérateur, avec les quatre scopes
   listés.
3. **Le terminal pendant `factory publish auth --channel bms-test`**, montrant le tableau de
   `channels.list?mine=true` (identifiant et titre de la chaîne).
4. **Le terminal pendant `factory publish upload`**, montrant le tableau des appels, le coût en
   unités de quota, et la vérification `videos.list` avec `privacyStatus: private`.

Une cinquième, facultative : la vidéo privée dans YouTube Studio, avec son titre, sa miniature
et son état « Privée ».

---

## 7. Vidéo de démonstration — scénario de 60 s

> Non exigée par ce formulaire (§ 0). À enregistrer si un examinateur la demande. Capture
> d'écran du terminal et du navigateur, sans voix, sous-titrée en anglais. **Aucun jeton, aucune
> adresse e-mail, aucun identifiant ne doit apparaître à l'image** — vérifier image par image
> avant l'envoi.

| Temps | Ce qu'on voit | Sous-titre anglais |
|---|---|---|
| 0-8 s | `docs/PRIVACY.md` publiée, dans le navigateur | « BMS Factory is an internal tool used only by BMS to publish to its own channels. » |
| 8-20 s | Terminal : `factory publish auth --channel bms-test` ; le navigateur s'ouvre sur le consentement Google, les 4 scopes sont lisibles | « The operator signs in with the channel's own Google account and grants four scopes. » |
| 20-30 s | Retour au terminal : le tableau `channels.list?mine=true` avec l'identifiant et le titre de la chaîne | « The application reads which channel the token gives access to. » |
| 30-45 s | `factory publish upload --run … --channel bms-test` ; la barre de progression de l'upload résumable, puis le tableau des appels et le coût en unités | « The finished video is uploaded with its full metadata: title, description, tags, thumbnail, captions, and the synthetic-media disclosure. » |
| 45-55 s | La sortie de vérification `videos.list` : `privacyStatus: private` | « Every upload is created private and verified by reading it back from the API. » |
| 55-60 s | YouTube Studio, la vidéo en « Privée » | « A human reviews and publishes it from YouTube Studio. Nothing is automated on youtube.com. » |

---

## 8. Après le dépôt

- **Délai** : Google ne s'engage sur rien (« as soon as possible »). Les retours de
  développeurs en 2025-2026 vont de plusieurs semaines à plusieurs mois, avec des silences de
  plus de quatre semaines après remédiation. Le dépôt à l'étape 14 est précisément là pour que
  l'horloge tourne pendant les phases 2 et 3.
- **Surveillance** : relever la boîte e-mail BMS **une fois par semaine**. Une demande de
  complément non répondue referme le dossier.
- **À réception d'un avis favorable** : passer `youtube.audit_passed` à `true` dans
  `config/channels/<chaîne>.yaml`. Ce seul drapeau fait basculer `publish_path` de
  `manual_studio` à `api_scheduled` (`CONFORMITE.md` § 2) — aucune autre ligne de code à
  toucher.
- **En cas de refus** : le motif est écrit dans `STATE.md` tel quel, le dossier est corrigé, et
  le formulaire est redéposé en *re-audit*. Le chemin `manual_studio` continue de fonctionner
  entre-temps : la publication n'est jamais bloquée, seulement manuelle.
