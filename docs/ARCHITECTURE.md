# ARCHITECTURE.md — la fabrique vidéo BMS

**Statut :** contrat d'architecture. Écrit à l'étape 8 (15/09/2026). Toutes les étapes 9 à 31 l'implémentent.
**Portée :** principes, graphe des étapes, disposition des fichiers, moteurs de style, multi-langues, journal, mémoire et disque.
**Document jumeau :** `docs/INTERFACES.md` donne le contrat champ par champ de chaque fichier cité ici.
**Priorité :** `docs/CONFORMITE.md` prime sur ce document ; ce document prime sur toute commodité d'implémentation.
**Chiffres :** tout temps annoncé porte sa source. « mesuré » = `benchmarks/RESULTATS.md` sur ce M2. « estimé » = arithmétique de mesures. « non mesuré » = inconnu, et écrit comme tel.

---

## 1. Principes

### 1.1 Tout est fichier sur disque
La vérité d'un run est son dossier `workspace/runs/<video_id>/`. Rien d'essentiel ne vit uniquement en mémoire, en base ou dans un service. Conséquence directe : on peut inspecter, rejouer, archiver et céder un run sans exécuter le code, ce qui est la condition de la thèse n° 6 (un tiers comprend le système) et de la revente de l'actif.

### 1.2 Une étape = une fonction pure et idempotente
Une étape lit **les fichiers du run + la configuration** et écrit **des fichiers du run + une entrée dans `manifest.json`**. Elle ne lit aucune variable globale, n'interroge aucun service pour décider, ne dépend d'aucune étape précédente autrement que par des fichiers.

Chaque étape écrit en dernier son marqueur `workspace/runs/<video_id>/.done/<etape>.done` (JSON : étape, `schema_version`, horodatages, durée, `inputs_hash`, liste des sorties, code de retour). Relancer une étape dont le marqueur existe **et** dont `inputs_hash` est inchangé ne fait rien et rend 0. `--force` efface le marqueur, `--from <etape>` efface celui-ci et tous les suivants.

`inputs_hash` = SHA-256 de la concaténation triée des empreintes des fichiers d'entrée déclarés + de la configuration résolue de la chaîne. Un changement de configuration invalide donc les étapes en aval, sans intervention.

**Écriture atomique, sans exception :** toute sortie s'écrit dans `<nom>.tmp` puis `os.replace()`. Une étape interrompue ne laisse jamais un JSON tronqué derrière elle.

**`manifest.json` n'entre jamais dans un `inputs_hash`.** Il est la sortie en ajout de toutes les étapes : le lire en entrée rendrait l'empreinte auto-référentielle et invaliderait tout l'aval à chaque écriture. Une étape qui a besoin d'une décision prise en amont la lit dans le fichier qui l'a produite, pas dans le manifeste. **Aucune étape n'écrit non plus dans une sortie déclarée d'une autre étape** : cela invaliderait son `.done` et l'`inputs_hash` de tout ce qui en dépend.

### 1.3 Un sous-processus par étape qui charge un modèle ; un seul modèle résident
Toute étape qui charge un modèle s'exécute dans un **sous-processus dédié qui se termine** — le déchargement est garanti par la mort du processus, jamais par un `del`. La machine a 16 Go : c'est la condition pour que le pipeline tienne (`CLAUDE.md` § 4).

Le verrou `workspace/model.lock` (PID + nom du modèle + horodatage) est pris par le sous-processus avant le chargement et libéré à sa sortie. Le prendre alors qu'il est tenu **par un processus vivant** est une erreur fatale, pas une attente : deux modèles résidents signalent un défaut de conception, et l'attente le masquerait. Mais un verrou dont le **PID est mort** est repris d'office, avec un `WARN` au journal — sinon un `kill` (celui que l'étape 22.1 teste) laisserait un verrou orphelin qui arrête le daemon jusqu'à intervention manuelle. Même règle pour `workspace/run.lock`.

Conséquence sur le découpage : une étape qui a besoin de deux modèles se découpe en autant de sous-processus séquentiels. L'étape `assets` en a besoin de deux : elle est donc **trois nœuds à part entière**, strictement sériels — `assets.fetch` (banques libres et bibliothèque, aucun modèle), `assets.image` (FLUX résident), `assets.depth` (Depth Anything résident). Ce ne sont pas des détails d'implémentation : chacun a son marqueur `.done/assets.image.done`, sa ligne dans `manifest.execution.timings`, et est une valeur acceptée par `--from`. Les nommer autrement rendrait la reprise impossible au milieu de 4 h 34 de génération. L'étape `subtitles` peut charger parakeet **puis** whisper en repli : jamais les deux en même temps.

### 1.4 Une vidéo à la fois
Un seul run avance à un instant donné, verrou `workspace/run.lock`. Ce n'est pas une limite d'ordonnancement, c'est la même contrainte de 16 Go. La capacité mesurée est de **≈ 7 vidéos par semaine** (`RESULTATS.md` § 2.7) ; aucun parallélisme ne la relèvera sur cette machine.

**Les tâches planifiées comptent comme des runs.** Les agents `launchd` des étapes 18 (`editorial collect`), 20 (regroupement par embeddings), 22.1 (sauvegarde) et 25 (`analytics pull`) prennent **le même `run.lock`, en attente** et non en échec : ils sont brefs et différables. Sans cela, un `collect` de 3 h du matin tournerait pendant `assets.image`, dont le pic mesuré à 11,15 Go ne laisse que 3,6 Go de marge. Le modèle d'embeddings de l'étape 20 est un modèle résident comme les autres : il prend `model.lock`, et **son pic mémoire n'est pas mesuré** — il est à inscrire dans `outils/MODELES.md` et au § 8 à son installation.

### 1.5 Déterminisme
`spec.json` porte une `seed` entière, tirée une fois à la création du run et jamais retirée. Toute décision aléatoire en dérive :
`seed_plan = int(sha256(f"{video_id}:{shot_id}").hexdigest()[:8], 16)` — la recette employée à l'étape 5.2.
Même `video_id`, même configuration, mêmes poids de modèle ⇒ mêmes sorties. Les modèles génératifs ne sont pas bit-à-bit reproductibles sur MPS ; le contrat porte donc sur les **décisions** (sujet, hook, découpage, choix de plan, rotation de template), pas sur les pixels. `manifest.json` enregistre `modeles[]` avec version et empreinte : sans cela « même graine » ne veut rien dire.

### 1.6 `schema_version` partout, configuration YAML validée
Chaque fichier racine (JSON ou YAML) porte `schema_version: "<majeure>.<mineure>"`. Une majeure différente de celle qu'attend le code est refusée ; une mineure inférieure est acceptée avec avertissement et les champs manquants prennent leur valeur par défaut. Les migrations de la base sont numérotées dans `factory/core/migrations/`.

La configuration est du YAML chargé en modèles pydantic v2 en `extra="forbid"` : une clé mal orthographiée est une erreur, pas un silence. Trois validations croisées obligatoires : la voix appartient à la langue de la chaîne ; le style référencé existe dans le registre des moteurs ; un produit configuré impose `paid_promotion = true` et des `disclosure_lines` dans la langue de la chaîne.

### 1.7 Secrets hors dépôt
`.env` (variables) et `secrets/` (jetons OAuth, clés) sont ignorés par git, en mode 600. La configuration ne contient **jamais** une valeur de secret, seulement une **référence** : `google_account: { alias: "bms-science-en", token_ref: "secrets/tokens/bms-science-en.json" }`. Aucun secret n'entre dans un manifeste, un journal, un événement ou un message d'erreur : le contrôle 30 de `CONFORMITE.md` § 11 le vérifie avant publication.

### 1.8 SQLite unique, index reconstructible
`workspace/factory.db` porte l'index des runs, la file de production, l'entrepôt éditorial et l'analytique. **Les fichiers restent la source de vérité des runs.** `factory queue reindex` reconstruit intégralement les tables de runs en relisant les `manifest.json` ; perdre la base coûte une reconstruction, pas des données.

Trois exceptions assumées, parce que ces données ne naissent pas d'un run : les instantanés concurrentiels (étape 18), les métriques YouTube (étape 25) et les poids appris (étape 26). Elles sont couvertes par la sauvegarde planifiée de l'étape 22.1, et les métriques sont réimportables depuis l'API.

---

## 2. Le graphe des étapes

Séquentiel, une seule branche. Temps donnés pour une vidéo de **10 minutes, 120 plans**, moteur illustré sauf mention.

| # | Nœud | Entrées | Sorties | Modèle chargé | Temps attendu | Reprise |
|---|---|---|---|---|---|---|
| 1 | `plan` | `factory.db` (topics_queue), `REFERENTIEL.json`, config chaîne | `spec.json` | aucun | < 1 s | oui |
| 2 | `research` | `spec.json` | `research.json` | aucun (HTTP : Wikimedia, sources libres) | 30–120 s *non mesuré* | oui |
| 3 | `script` | `spec.json`, `research.json`, `REFERENTIEL.json` | `script.json` | **LLM** Qwen3.5-9B Q4_K_M | ≈ 2,5 min *(estimé de 14,4 tok/s mesurés)* | oui |
| 4 | `review` | `script.json` | `review.json`, ligne dans `registre/data/reviews.jsonl` | aucun — **humain, par lots** | hors machine | barrière |
| 5 | `voice` | `script.json`, config langue + voix | `voice/segment_XX.wav`, `voice/voice.wav`, `voice/timings.json` | **TTS** Qwen3-TTS | **33 min** *(RTF 3,29 mesuré)* | oui |
| 6 | `subtitles` | `voice/voice.wav`, `script.json`, charte | `words.json`, `subtitles.srt`, `subtitles.ass` | **ASR** parakeet, repli whisper | 23 s *(RTF 0,037)* ; repli 3,9 min | oui |
| 7 | `shotlist` | `script.json`, `words.json`, `voice/timings.json`, cible de niche | `shotlist.json` | aucun | < 1 s | oui |
| 8 | `assets` | `shotlist.json`, bibliothèque, config style | `assets/<shot>/*`, `assets/<shot>/licence.json` | **image** FLUX, puis **profondeur** Depth Anything, en sous-processus séparés | illustré : **4 h 34** *(120 × 137,0 s — médiane toutes invites ; le prompt cartoon mesure 149,8 s, soit 5 h 00)* ; banques : réseau, *non mesuré* | oui, plan par plan |
| — | *barrière plans à personnage* | `shotlist.json`, `assets/` | `assets/review_visual.json` | aucun — **humain** | hors machine | barrière |
| 9 | `render` | `assets/`, `shotlist.json`, charte, moteur de style | `clips/shot_XX.mp4` | aucun (ffmpeg / Revideo) | **7,4 min** *(120 × 3,7 s mesurés, parallaxe)* | oui, plan par plan |
| 10 | `assemble` | `clips/`, `voice/voice.wav`, musique, `subtitles.ass` | `video_nomusic.mp4`, `final.mp4` | aucun (ffmpeg) | ≈ 3 min *(98,4 img/s mesurés)* | oui |
| 11 | `thumbnail` | `script.json`, `metadata` partielle, charte | `thumbnails/variant_X.png`, `thumbnail.png` | aucun (Playwright ; rembg si détourage) | 0,2 s par variante *(mesuré)* | oui |
| 12 | `metadata` | `script.json`, `shotlist.json`, `thumbnails/thumbnails.json`, `qc.json`, config produit + langue | `metadata.json` | **LLM** (variantes de titre) | ≈ 30 s *estimé* | oui |
| 13 | `qc` | `final.mp4`, `script.json`, `shotlist.json`, `config/qc.yaml` | `qc.json` | aucun (ffmpeg, PySceneDetect, tesseract) | 1–2 min *estimé* | oui |
| 14 | `export` | `qc.json` vert, `final.mp4` | `workspace/export/<video_id>.mp4`, purge des intermédiaires | aucun | ≈ 10 s | oui |
| 15 | `publish` | `export`, `metadata.json`, `manifest.json` | `publish.json` | aucun (API YouTube) | 1–5 min *non mesuré* | oui, avec reprise d'upload |
| 16 | `measure` | `publish.json` | lignes dans `factory.db` → `manifest.resultats` | aucun (Analytics + Reporting) | J+7 et J+30 | oui |
| 17 | `learn` | `factory.db` (vue de performance) | `learned/weights.json` | aucun | < 1 min *estimé* | oui |

**Total mesuré bout en bout** : ≈ 3 h 55 (style le moins cher) à 6 h 00 (motion design) pour 10 minutes, dont **84 % en génération d'images** (`RESULTATS.md` § 2.6). Les durées médianes du registre étant de 18 à 31 minutes, `histoire_doc` monte à 14,8 h et n'est **pas tenable en images générées** (`STYLES.md` § 3.1) : ces niches passent par le moteur documentaire.

### 2.1 Les deux barrières humaines
Elles ne sont pas des étapes : ce sont des **états d'attente**. Le run passe en `review_pending`, l'exécuteur le sort de la file et prend le suivant.

1. **`review` — relecture du script, par lots.** Obligatoire. C'est la pièce qui fait tomber l'obligation de divulgation RIA art. 50 §4 et l'argument contre le « contenu inauthentique » (`CONFORMITE.md` § 4). `auto_approve: true` la court-circuite, pose `reviewer = "auto-approve"`, lève un avertissement permanent et retire l'exception éditoriale pour ces vidéos ; il se règle par chaîne et Alek doit l'acter par écrit.
2. **Barrière des plans à personnage.** Seuls les plans dont `asset_request.contains_person` est vrai attendent un avis humain en pleine résolution, avant `render`. C'est l'arbitrage de `STYLES.md` § 5 : aucun contrôle automatique n'est atteignable pour l'anatomie et la dérive d'identité (`RESULTATS.md` § 2.12), et la charte maintient ces plans minoritaires. Le drapeau est gratuit : c'est nous qui écrivons l'intention de chaque plan.

### 2.2 Deux contrôles de contrat qui viennent de mesures, pas de préférences
- **Longueur minimale de segment de voix.** Le WER de re-transcription mesuré par palier (étape 7) creuse entre 5 et 10 s — c'est-à-dire la longueur d'une phrase de script. `voice` **fusionne les segments consécutifs d'un même rôle jusqu'à ≥ 15 s** avant synthèse, sinon le régime nominal est le régime dégradé.
- **Couverture *et* WER des sous-titres.** La couverture seule ment : à 2 s elle vaut 100–120 % avec tous les mots faux. `subtitles` mesure les deux contre le texte du script — que le pipeline connaît, puisqu'il l'écrit — avec un **seuil de WER fonction de la longueur du segment** ; sous le seuil de couverture, bascule sur whisper et re-mesure. Le texte du script fait foi ; l'ASR ne fournit que le timing.

---

## 3. Disposition d'un run

```
workspace/runs/<video_id>/
  spec.json  research.json  script.json  review.json
  voice/segment_00.wav … voice/voice.wav  voice/timings.json
  words.json  subtitles.srt  subtitles.ass
  shotlist.json
  assets/shot_00/{image.png,depth.png,source.mp4,licence.json} …
  assets/review_visual.json
  clips/shot_00.mp4 …
  video_nomusic.mp4  final.mp4
  thumbnail.png  thumbnails/variant_1.png …
  metadata.json  qc.json  publish.json
  manifest.json  events.jsonl  publication.md
  .done/<etape>.done
```

`publication.md` est le pense-bête de gestes manuels exigé par `CONFORMITE.md` § 2 : passage en programmé, **case « promotion payante »**, date cible. Sans lui l'opérateur oublie la case, et l'API ne sait pas l'écrire.

### 3.1 Identifiants
`video_id = <channel_id>-<AAAAMMJJ>-<4 caractères>`, les 4 caractères tirés de `abcdefghjkmnpqrstuvwxyz23456789` (ni `i`, `l`, `o`, `0`, `1`), dérivés de la graine. Exemple : `bms-science-en-20260918-k7q2`. Unicité vérifiée contre `factory.db` **et** contre le disque avant création.

Une déclinaison multilingue est un **run enfant** : `parent_id` porte le `video_id` du run source — c'est le champ que `CONFORMITE.md` § 10 nomme `source_run_id`, renommé ici pour être cohérent avec `video_id` ; `INTERFACES.md` le signale. Un enfant n'a jamais d'enfant : la parenté est d'un seul niveau, sinon la boucle de rétroaction ne sait plus à quoi attribuer un résultat.

---

## 4. Bibliothèque partagée

```
workspace/library/{images,stock,music,sfx,characters,intros}/
workspace/library/cadence.json
```

Chaque fichier a un `licence.json` frère portant les champs de `CONFORMITE.md` § 8 (`provider`, `source_url`, `author`, `licence`, `licence_url`, `attribution_line`, `downloaded_at`, `person_release`). **Un asset sans ces champs ne descend pas dans le pipeline** : le contrôle est à l'acquisition, pas au montage.

L'index est en base (`library_assets`) : empreinte perceptuelle, mots-clés, langue, chaînes l'ayant employé, dates d'emploi, compteur. La base est reconstructible en relisant les `licence.json`.

**Règles de réutilisation et d'anti-répétition.**
1. Un asset porteur de **texte incrusté** (`has_text: true`) n'est jamais réutilisé dans une autre langue, ni sur une autre chaîne. C'est la première fuite possible entre runs.
2. Un asset n'est pas réemployé sur la **même chaîne** avant `library.cooldown_videos` publications (défaut 10) ni plus de `library.max_uses_per_channel` fois (défaut 3).
3. Deux chaînes de **même langue** ne partagent aucun asset visuel de premier plan : `CONFORMITE.md` § 5 interdit le clonage, et l'index de dédoublonnage est global.
4. Les **personnages** (`characters/`) sont propres à une chaîne, jamais partagés : un persona récurrent est une défense contre le « contenu de gabarit », un persona partagé est un aveu d'exploitation commune.
5. Intros et outros communes à une chaîne sont **explicitement autorisées** : c'est le cas que la politique déclare admis.
6. Le taux de réutilisation est **supposé faire baisser le coût de 137 s par plan, et ce n'est pas encore un fait** : il se mesure à l'étape 12.2, il ne se suppose pas ici.

`cadence.json` est la **seule source de vérité** sur « peut-on publier maintenant » (`CONFORMITE.md` § 10.3). Aucun autre module ne décide ; la base n'en est qu'un miroir.

---

## 5. Moteurs de style

Le style est **une valeur de configuration qui sélectionne un moteur**. Il n'existe nulle part dans le code un `if style == …` : `config/styles/<id>.yaml` nomme un moteur, le registre `STYLE_ENGINES: dict[str, type[StyleEngine]]` le résout, la chaîne nomme un style. Ajouter un style, c'est ajouter un fichier YAML et une classe ; ce n'est jamais toucher au pipeline.

L'interface a deux méthodes seulement (`prepare_assets`, `render_shot`, signatures dans `INTERFACES.md`). Tout ce qui est commun — découpage, timings, sous-titres, montage, miniature, QC — vit **hors** des moteurs. Un moteur ne connaît ni la langue, ni la conformité, ni la publication.

Deux **backends** de rendu, déclarés par le moteur et non par le pipeline :
- `ffmpeg` — chaîne native : `zoompan` suréchantillonné ×4 (mesuré 3,3 s, le suréchantillonnage ne coûte que 1,2 s), parallaxe 2.5D à masques cumulatifs, incrustations. Moteurs *cartes*, *illustré*, *documentaire*.
- `revideo` — composition programmatique headless, 98,4 img/s mesurées à 1080p30, `DISABLE_TELEMETRY=true` imposé dans l'environnement. Moteurs *motion design*, *whiteboard*, *avatar 2D*.

Ordre de livraison des moteurs (`STYLES.md` § 6) : cartes (12.1) → illustré (12.2) → motion design (30.1) → documentaire (17) → whiteboard (30.2) → avatar 2D (29). Le moteur *cartes* est **interne** : il porte le découpage et l'interface, et ne doit jamais être publié tel quel (« scrolling text with minimal or no narrative » est littéralement le cas visé par la politique).

**Templates et charte.** Chaque chaîne déclare **≥ 3 templates** (`CONFORMITE.md` § 5) ; `template_id` est choisi par rotation en excluant les 2 dernières publications de la chaîne, lues en base. La `charte` (polices, palette, transitions, positions des textes, cadrage) est versionnée : `charte_version` entre au manifeste, faute de quoi un changement de charte rendrait incomparables deux vidéos de la même chaîne — et la boucle de rétroaction attribuerait à un hook ce qui vient d'une police.

La charte porte aussi la règle de cadrage tranchée en étape 6 : **personnages en buste, jamais en pied en mouvement**, priorité aux objets, lieux et abstractions. C'est une contrainte de rédaction des intentions visuelles, de coût nul, et c'est la première ligne de défense contre les défauts d'anatomie.

---

## 6. Multi-langues

La langue est une propriété de **la chaîne** et du **run**, jamais un paramètre de traduction en fin de chaîne.

- Le script est **produit directement dans la langue de la chaîne** par le LLM, à partir du référentiel de la niche dans cette langue. Il n'y a pas d'étape de traduction dans le DAG.
- `config/languages/<code>.yaml` porte les voix disponibles, les règles typographiques (espaces insécables, guillemets, ponctuation double), les formats de nombre, de date et d'unité, et les gabarits de divulgation par réseau d'affiliation. La phrase contractuelle Amazon y figure **mot pour mot** et ne se traduit pas.
- Une **déclinaison** crée un run enfant (`factory localize`) qui **réutilise les assets visuels sans texte incrusté** et **régénère** script adapté, voix, sous-titres, titres, miniature, habillage. `CONFORMITE.md` § 5 l'exige : adaptation, pas clonage — angle réécrit pour le marché, exemples et chiffres localisés, habillage visuel distinct.
- Le `dedupe_hash` est vérifié **globalement, toutes chaînes confondues**. Une déclinaison passe parce que son texte est réellement différent, pas parce qu'elle est exemptée.
- **Anti-fuite.** Le sous-processus d'un run ne reçoit que la configuration de sa chaîne ; aucun cache de prompt, aucune conversation, aucun état n'est partagé entre deux runs. La graine est propre au run. Les seuls objets partagés sont la bibliothèque (soumise aux règles § 4) et les index globaux de dédoublonnage et de cadence, qui sont globaux **par obligation de conformité**.

---

## 7. Journal

Deux journaux, deux usages.

- **`events.jsonl` par run** — une ligne JSON par événement (`ts`, `run`, `step`, `level`, `msg`, `data`), append-only, jamais réécrit. C'est la trace d'audit du run : elle sert au contrôle 28 de `CONFORMITE.md` § 11 (aucune trace d'appel à yt-dlp) et au diagnostic a posteriori. Compressée en `.gz` après 30 jours.
- **`workspace/logs/factory.log`** — journal d'exploitation tournant (10 Mo × 10 fichiers), toutes chaînes confondues, lisible par un humain.
- **`workspace/logs/events.jsonl`** — livrable de l'étape 22.1 : **même format de ligne** que l'`events.jsonl` d'un run, mais à l'échelle de la fabrique (orchestrateur, file, daemon, sauvegardes, tâches planifiées). Le runner y recopie les événements de niveau `WARN` et au-dessus de chaque run. Rotation quotidienne, compression à 30 jours. Les deux fichiers ne se remplacent pas : l'un est la trace d'audit d'une vidéo, l'autre l'histoire de la machine.

Niveaux : `DEBUG` (arguments d'outils externes, chemins) · `INFO` (début et fin d'étape, décisions : sujet retenu, hook tiré, template choisi, asset réutilisé) · `WARN` (seuil frôlé, repli activé, `auto_approve` actif) · `ERROR` (échec d'étape avec message exact de l'outil) · `BLOCK` (run bloqué, avec raison lisible destinée à Alek, pas à un développeur).

Sont **toujours** journalisés : chaque décision qui entre au manifeste, chaque licence enregistrée, chaque appel d'API avec son coût en unités de quota, chaque repli, chaque purge de disque. Ne sont **jamais** journalisés : secrets, jetons, clés, contenu de `secrets/`, en-têtes d'authentification. Les commandes verbeuses (ffmpeg, modèles) écrivent dans le dossier de l'étape, pas dans le journal.

---

## 8. Mémoire, disque, durée de vie d'un run

**Mémoire.** Un modèle résident (§ 1.3), un run (§ 1.4). Pics mesurés : LLM 6,96 Go · TTS 4,65 Go · image 1280×720 11,15 Go · image 1024² 12,37 Go · profondeur 0,77 Go · ASR parakeet 0,84 Go · ASR whisper 1,92 Go. **Non mesuré : le modèle d'embeddings de l'étape 20** — à peser et à inscrire au ledger à son installation. Le pic image laisse **3,6 Go de marge** : aucune étape, aucune tâche planifiée et aucun ffmpeg ne doit tourner à côté de lui.

**Disque.** `df -h /` avant toute étape qui écrit ; **plancher dur 8 Go libres**, jamais franchi (`CLAUDE.md` § 3). Sous le plancher, le run passe `blocked` avec raison lisible — il ne dégrade pas, il s'arrête. Cumul des poids de modèles retenus : plafond 22 Go, mesuré 21,52 Go, **0,48 Go de marge** : tout nouveau poids se gage sur un retrait.

**Taille d'un run.** Estimation, non mesurée : assets ≈ 240 Mo, clips ≈ 960 Mo, voix ≈ 60 Mo, `video_nomusic.mp4` + `final.mp4` ≈ 1 Go, JSON et miniatures ≈ 5 Mo — **pic ≈ 2,3 Go**. Plafond dur `max_run_disk_mb: 6000` : au-delà, le run est bloqué, ce qui attrape une boucle de génération avant qu'elle remplisse le disque.

**Purge, après `export` réussi et vérifié :** `clips/`, `video_nomusic.mp4`, `voice/segment_*.wav`, `assets/**/depth.png` et les images non promues en bibliothèque sont supprimés. Sont **conservés** : tous les JSON, `events.jsonl`, `subtitles.*`, `thumbnail.png`, `voice/voice.wav`, et les assets promus en bibliothèque (déplacés, pas copiés). `final.mp4` reste sous `workspace/export/` jusqu'à 14 jours après passage en `public`, puis est purgé : YouTube en détient la copie.

**Résidu après purge ≈ 1,5 Mo par run** (estimé) — soit ≈ 4 Go pour 2 600 runs, ce qui rend l'historique complet conservable indéfiniment. C'est ce résidu, pas la vidéo, qui porte la valeur de l'actif.

**Ce que 50 runs par semaine casserait, et pourquoi le chiffre n'est pas atteignable.** 50 runs/semaine à 2,3 Go de pic feraient 115 Go par semaine : impossible avec 22 Gi libres — la purge n'est donc pas une optimisation, c'est la condition de fonctionnement. En base, 50 runs/semaine font 2 600 lignes de runs par an et ≈ 950 000 lignes de métriques quotidiennes : SQLite les tient sans peine avec les index déclarés dans `INTERFACES.md`, à condition que les **courbes de rétention soient stockées comme un blob par fenêtre (J+7, J+30) et non point par point**. Mais la capacité **mesurée** de cette machine est de **≈ 7 vidéos par semaine** (`RESULTATS.md` § 2.7) : 50 est un objectif de format de données, pas une promesse de production, et ce document ne doit pas laisser croire l'inverse.

---

## 9. `workspace/factory.db`

Un seul fichier SQLite, WAL activé, un seul écrivain (une vidéo à la fois). Domaines : index des runs · file de production · publication et quota · éditorial (chaînes suivies, vidéos, instantanés) · analytique (métriques, rétention, reach) · bibliothèque · relecture. Le schéma table par table est dans `INTERFACES.md`.

**Les noms de tables ne sont pas libres.** `ROADMAP.md` les fixe déjà, migration par migration : `jobs`, `review_log` (22.1, 22.2) · `channels_watch`, `videos_ext`, `video_snapshots`, `channel_snapshots`, `collect_runs` (18) · `topics_queue`, `niche_scores` (19, 20) · `publications`, `quota_ledger`, `reporting_jobs` (23.1) · `perf_daily`, `perf_traffic`, `perf_reach`, `retention_curves`, `analytics_runs`, vue `v_video_perf` (25). Ce document et `INTERFACES.md` emploient **ces noms-là** et aucun autre : un schéma inventé ici obligerait vingt sessions à choisir entre deux vérités.

Deux règles :
1. **Les tables de runs sont reconstructibles** à partir des `manifest.json` (`factory queue reindex`). Aucune décision de production ne vit uniquement en base.
2. **Les données de l'API YouTube sur des tiers portent `fetched_at` et se purgent à 30 jours** (`CONFORMITE.md` § 9, Developer Policies III.E.4). Les mesures dérivées, elles, se conservent : ce ne sont plus des données API.

---

## 10. Ce qui n'est **pas** dans cette architecture

- **Aucune automatisation de navigateur sur un service Google.** Pas de Playwright, Selenium ou pilotage sur `youtube.com` ou `studio.youtube.com` : violation des ToS, sanction = terminaison, donc cascade sur tout le portefeuille. Playwright ne sert qu'au rendu local HTML→PNG des miniatures et à la capture d'animations, qui ne touchent aucun service tiers.
- **Aucun scraping, aucun `yt-dlp`, aucun téléchargement de vidéo tierce**, à aucune étape, pour aucun motif — y compris « juste mesurer un rythme de coupe ». Les métadonnées passent par l'API Data v3.
- **Aucune exécution parallèle** : ni deux runs, ni deux étapes, ni deux modèles. C'est la contrainte de 16 Go, et elle est structurante, pas provisoire.
- **Aucun outil d'engagement** : ni vues, ni likes, ni commentaires, ni abonnements automatisés.
- **Aucun service payant ni dépendance cloud** dans le pipeline quotidien. Le serveur GPU est une option d'étape 31, hors de ce document.
- **Aucune file de messages, aucun conteneur, aucun ordonnanceur distribué.** Une base SQLite, un `launchd`, un verrou. Un développeur tiers doit pouvoir lire ce système en une soirée.
- **Aucune publication 100 % automatique d'une vidéo affiliée** : la case « promotion payante » n'est pas écrivable par l'API. Ce n'est pas une lacune d'implémentation, c'est une limite de la plateforme, et elle se dit au client.

---

## 11. Objections et réponses

Le contradicteur a rendu **19 objections** ; elles sont traitées une par une dans `docs/INTERFACES.md` § 5, qui porte le tableau complet (17 corrigées, 1 corrigée autrement, 1 refusée sur preuve). **Cinq d'entre elles ont changé ce document**, et elles méritent d'être lues ici parce qu'elles touchent des principes, pas des champs :

1. **`manifest.json` ne peut pas être une entrée d'étape** (obj. 5) — il est la sortie en ajout de toutes les étapes ; le lire en entrée rendait l'`inputs_hash` auto-référentiel et invalidait tout l'aval à chaque écriture. Règle générale ajoutée au § 1.2, avec son corollaire : **aucune étape n'écrit dans une sortie déclarée d'une autre** (obj. 6).
2. **Les sous-phases d'`assets` sont des nœuds, pas un détail d'implémentation** (obj. 16) — sans marqueur `.done`, sans ligne de timing et sans valeur `--from`, aucune reprise n'est possible au milieu de 4 h 34 de génération d'images. Le DAG compte **19 nœuds**.
3. **Un verrou n'est fatal que s'il est vivant** (obj. 8) — un `kill` laissait un verrou orphelin qui arrêtait le daemon jusqu'à intervention manuelle. Le PID mort est repris d'office, avec un `WARN`.
4. **Les tâches planifiées sont des runs** (obj. 9) — une collecte de 3 h du matin tournant pendant `assets.image` mangerait les 3,6 Go de marge. Elles prennent `run.lock` en attente. Le modèle d'embeddings de l'étape 20 est un modèle résident comme un autre, et **son pic n'est pas mesuré**.
5. **Les noms de tables ne nous appartiennent pas** (obj. 17) — `ROADMAP.md` les fixe déjà migration par migration. Le § 9 les reprend tels quels plutôt que d'obliger vingt sessions à choisir entre deux vérités.

**Une objection refusée sur preuve** : sortir `cadence.json` de `workspace/library/` (obj. 11). L'emplacement est discutable, mais c'est `CONFORMITE.md` § 10.3 qui le fixe, et ce document lui est subordonné. Seule la moitié utile de l'objection est retenue : la cadence se **relit au moment de l'upload**, le manifeste n'en garde qu'une trace horodatée.

**Une objection non résolue, portée à Thomas** : le plafond de publications par jour. Une vidéo complète coûte 2 050 unités, six en coûtent 12 300 pour un quota de 10 000. Ce document retient **4 par jour** au nom de la règle « la plus stricte prime », mais `CONFORMITE.md` § 2 et son contrôle 27 disent 6. Il faut soit amender `CONFORMITE.md`, soit acter la cohabitation. → `SUIVI.md` § 1.
