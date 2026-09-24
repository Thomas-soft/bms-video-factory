# REPRISE.md — carte du système pour un développeur qui reprend

Écrit à l'étape 31 (24/09/2026). Public : développeur Python confirmé qui découvre le dépôt.
Ce document **renvoie** aux contrats plutôt que de les recopier ; en cas de conflit, l'ordre de
priorité est `docs/CONFORMITE.md` > `docs/ARCHITECTURE.md` > `docs/INTERFACES.md` > ce fichier.

Lecture minimale conseillée, dans l'ordre (≈ une soirée) : ce fichier → `docs/ARCHITECTURE.md`
(§ 1, 2, 5, 8) → `STATE.md` (risques actifs) → `docs/INTERFACES.md` (au besoin, par champ).

---

## 1. En une phrase

Un pipeline séquentiel de **19 nœuds** (Python 3.12 + un moteur de rendu Node/Revideo), piloté
par un daemon `launchd`, qui écrit tout dans `workspace/runs/<video_id>/` et indexe dans une base
SQLite ; **un seul run et un seul modèle résident à la fois** (Mac M2 16 Go), chaque étape qui
charge un modèle tourne dans un sous-processus qui meurt.

## 2. Carte du dépôt

| Chemin | Rôle |
|---|---|
| `factory/cli.py` | point d'entrée unique `factory` (Typer) — ≈ 70 commandes, groupes `config`, `queue`, `daemon`, `backup`, `publish`, `calendar`, `editorial`, `analytics`, `links`, `revenue`, `library`, `character`, `notify` |
| `factory/run.py` | DAG de `factory run` (enchaînement des étapes, marqueurs `.done`, `--from`, `--force`) |
| `factory/steps/` | une étape = un module : `plan`, `research`, `script`, `voice`, `subtitles`, `shotlist`, `render`, `assemble`, `thumbnail`, `metadata`, `export`, `localize` |
| `factory/styles/` | moteurs de style ; registre `STYLE_ENGINES` dans `__init__.py` ; base `MoteurBase` dans `base.py` ; pont Node dans `revideo.py` |
| `factory/assets/` | génération d'images (`images.py`, mflux), banques libres (`stock.py`), profondeur, parallaxe, musique |
| `factory/llm.py`, `tts.py`, `asr.py` | briques IA (llama.cpp, Qwen3-TTS / Kokoro, parakeet / whisper), toutes en sous-processus |
| `factory/retention/` | vérificateur de script (boucles ouvertes, ruptures, densité de faits, hooks) |
| `factory/eval/` | banc qualité : `bench.py` + `metrics/` (9 familles) → `qc.json` |
| `factory/orchestrator/` | file (`queue.py`), exécuteur (`runner.py`), daemon, relecture, régénération, sauvegarde, alertes, journal |
| `factory/publish/` | OAuth, upload, precheck (checklist CONFORMITE § 11), calendrier, reporting |
| `factory/editorial/` | collecte concurrentielle (API Data v3), demande (Wikimedia Pageviews…), niches, sujets, titres, SEO |
| `factory/analytics/` | tirage Analytics + Reporting, rétention, apprentissage (`learn.py` → `learned/weights.json`) |
| `factory/monetization/` | liens d'affiliation, import de revenus, économie unitaire |
| `factory/core/` | modèles pydantic (`models.py`), config, base (`db.py`), migrations SQL, chemins, secrets |
| `factory/doctor.py` | diagnostic machine + modèles (lit `outils/MODELES.md`) |
| `dashboard/` | Streamlit (`app.py`, 8 vues, `i18n/fr.yaml|en.yaml`) — `factory dashboard` |
| `render/` | projet Node Revideo (scènes TSX), `node_modules` ≈ 0,33 Go |
| `config/` | YAML validés en `extra="forbid"` : `channels/`, `styles/`, `chartes/`, `voices/`, `languages/`, `niches/`, `products/`, `orchestrator.yaml`, `qc.yaml`, `team.yaml`, `editorial.yaml`, `economics.yaml` |
| `registre/` | référentiel des niches (`REFERENTIEL.json`), données API de tiers (`data/`, **purge 30 j**, jamais publiées), `reviews.jsonl` |
| `workspace/` | runs, bibliothèque, base `factory.db`, journaux, exports — **non versionné** |
| `models/` | poids (≈ 21,8 Go), caches HF/llama redirigés ici — non versionné |
| `outils/` | ledger `MODELES.md`, plists `launchd`, `SELECTION.md`, script de publication du dépôt public |
| `benchmarks/` | mesures (`RESULTATS.md`) et scripts de banc |
| `reports/` | rapports générés (digest, collecte, économie, rendement composé) |
| `tests/` | 32 fichiers, un par étape pour l'essentiel |

## 3. DAG et contrats

- Graphe, entrées/sorties, modèle chargé et temps par nœud : `ARCHITECTURE.md` § 2.
- Contrat champ par champ de chaque fichier de run et de chaque table : `INTERFACES.md`
  (§ 5 = divergences numérotées entre contrat et code — **lire avant de « corriger »** un écart).
- Idempotence : marqueur `.done/<étape>.done` + `inputs_hash` (§ 1.2). **Piège connu** : une
  étape relancée à la main hors DAG ne met pas à jour les marqueurs aval → après un
  `factory script`/`plan` manuel, reprendre avec `voice --force` **et** `subtitles --force`.
- Barrières humaines : relecture du script (obligatoire) et plans à personnage (§ 2.1).
- Checklist de pré-publication : `CONFORMITE.md` § 11, implémentée dans `factory/publish/precheck.py`.

## 4. Base et tables

`workspace/factory.db`, SQLite en WAL, un seul écrivain. Migrations numérotées
`factory/core/migrations/NNN_*.sql` (dernière : `013_library_index.sql`), appliquées au
démarrage, tracées dans `schema_migrations`. Domaines :

| Domaine | Tables |
|---|---|
| runs et file | `runs`, `jobs`, `events`, `review_log` |
| éditorial | `channels_watch`, `videos_ext`, `video_snapshots`, `channel_snapshots`, `collect_runs`, `topics_queue`, `topic_clusters`, `niche_scores`, `embeddings` |
| publication | `publications`, `quota_ledger` (+ vue `v_quota_jour`), `reporting_jobs`, `reporting_reports` |
| analytique | `perf_daily`, `perf_traffic`, `perf_reach`, `retention_curves`, `video_metrics`, `analytics_runs`, vues `v_video_perf`… |
| argent | `revenue` |
| bibliothèque | `library_assets`, `library_uses`, `library_semantic_reuse` |

`runs`/`jobs` se reconstruisent depuis les manifestes (`factory queue reindex`) ; éditorial,
analytique et poids appris ne se reconstruisent pas → couverts par la sauvegarde quotidienne.

## 5. Secrets

| Quoi | Où | Lu par |
|---|---|---|
| `YT_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `PEXELS_KEY`, `PIXABAY_KEY`, `HF_HOME`… | `.env` (600, ignoré par git) | `factory/core/secrets.py` / `charge_env()` |
| Client OAuth « Application de bureau » | `secrets/client_secret.json` (**absent au 24/09**) | `factory/publish/oauth.py` |
| Jetons par chaîne | `secrets/tokens/<channel>.json` (vide) | idem, référencé par `google_account.token_ref` |

Règles : la config ne porte que des **références** ; aucun secret dans manifestes, journaux,
événements, messages d'erreur (contrôle 30) ; ni `secrets/` ni `.env` dans les sauvegardes
(`backup restore-test` le vérifie) ; `git diff --cached` avant tout commit sensible. Deux dépôts
distants : privé (tout) et public (sans `registre/data/`, via `outils/publier.sh`).

## 6. Lancer les tests

```bash
uv sync                       # rebâtit .venv à l'identique depuis uv.lock
uv run pytest -q              # 686 tests, ≈ 48 s, aucun modèle chargé (mesuré le 24/09/2026)
uv run pytest -q tests/test_etape22_1.py -k queue   # un sous-ensemble
uv run factory doctor --quick # environnement, disque, .env, ffmpeg, ledger (sans génération)
uv run factory doctor         # + génération réelle LLM/TTS/ASR/image/profondeur (minutes)
uv run factory config validate
```

Les tests n'appellent aucune API réelle (API YouTube factice, fixtures sous `tests/fixtures/`).
Un bout-en-bout réel : `uv run factory run --channel bms-test --topic "<sujet sourçable>"` (≈ 4 h
en style illustré ; hors fenêtre de nuit, arrêter le daemon avant).

## 7. Étendre le système

### 7.1 Ajouter un moteur de style

1. `config/styles/<id>.yaml` : `engine: <nom>`, backend (`ffmpeg` ou `revideo`), paramètres.
2. `factory/styles/<nom>.py` : classe dérivée de `MoteurBase` (`base.py`) implémentant
   `prepare_assets(...)` et `render_shot(...)` (signatures : `INTERFACES.md`). Le moteur ne
   connaît ni langue, ni conformité, ni publication.
3. L'inscrire dans `STYLE_ENGINES` (`factory/styles/__init__.py:26`). **Aucun `if style == …`
   ailleurs** : c'est un principe d'architecture (`ARCHITECTURE.md` § 5).
4. Tout modèle chargé → sous-processus + `workspace/model.lock` ; poids au ledger (§ 8).
5. Tests : copier le patron de `tests/test_etape30_2.py` (contrat de clip `ffprobe`, temps par plan).
6. Mesurer le coût par minute de vidéo et l'inscrire dans `benchmarks/RESULTATS.md` § 3.

### 7.2 Ajouter une métrique au banc qualité

1. Soit une mesure dans une famille existante de `factory/eval/metrics/` (fonction qui lit le
   `contexte`, rend une valeur et une note), soit une nouvelle famille : module exposant
   `mesurer(contexte) -> Famille`, ajouté à `FAMILLES` (`metrics/__init__.py`, ordre = coût
   croissant). Une métrique **mesure**, n'écrit rien hors `<run>/qc/`, ne charge aucun modèle.
2. Seuils et poids dans `config/qc.yaml`.
3. Si un échec doit déclencher une régénération : entrée dans `remedes` de
   `config/orchestrator.yaml` (étape de reprise + levier). Sans remède, le run passe `blocked`.
4. Tester sur un run PASS et un run FAIL connus (`s57f` PASS 88,5, `s2ur` FAIL).

### 7.3 Ajouter une source éditoriale

- **Chaîne concurrente suivie** : `factory editorial watch add` (API Data v3 par playlists
  d'uploads, **jamais** `search.list`, jamais yt-dlp). Données brutes purgées à 30 jours
  (`factory editorial purge`, `CONFORMITE.md` § 9).
- **Signal de demande** : une fonction dans `factory/editorial/demand.py` sur le modèle de
  Wikimedia Pageviews (User-Agent obligatoire, cache `workspace/cache/demand`, limiteur de
  débit) ; la brancher dans le score de `topics.py`. Sources payantes ou scrapées interdites
  (Reddit API commerciale payante, Social Blade).
- **Source de recherche factuelle** (étape `research`) : `factory/steps/research.py`
  (`_wikipedia_recherche`, `MAX_SOURCES = 6`). Licence et URL inscrites dans `research.json`.

### 7.4 Ajouter un programme d'affiliation

1. Ajouter le réseau au `Literal` `Reseau` (`factory/core/models.py:71`).
2. Paramètre de sous-identifiant par vidéo : `SUBID_EN_CHEMIN` / construction du lien dans
   `factory/monetization/links.py`.
3. Ligne de divulgation **par langue** dans `config/languages/<code>.yaml` (`disclosure`) —
   la validation croisée refuse un produit sans ligne dans la langue de la chaîne.
4. Correspondance des colonnes d'export dans `factory/monetization/import_revenue.py` —
   **aucune colonne d'export réelle n'est vérifiée** : importer le premier export à la main.
5. Produit : `config/products/<id>.yaml` (patron : `exemple-affilie.yaml`) ; il impose
   `paid_promotion = true` → case Studio manuelle (non écrivable par l'API).

### 7.5 Ajouter une chaîne ou une langue

Procédure opérateur : `EXPLOITATION.md` § 10 (et `CONFORMITE.md` § 12.4). Côté code : une
langue = `config/languages/<code>.yaml` (typographie, formats, divulgations) + un gabarit
d'invite `factory/prompts/script_<code>.md` + ≥ 1 voix `config/voices/*.yaml`. La déclinaison
(`factory localize`, étape 24) est **désactivée** (production anglaise seulement).

## 8. Mettre à jour un modèle

1. `df -h /` : jamais sous 8 Go libres ; cumul retenu ≤ 22 Go (**21,81 Go au 24/09, marge
   0,19**) → tout nouveau poids se gage sur un retrait.
2. Télécharger sous `models/` (caches `HF_HOME`, `LLAMA_CACHE`, `OLLAMA_MODELS` redirigés par
   `.env` et contrôlés par `doctor`).
3. Inscrire la ligne au ledger `outils/MODELES.md` : chemin, Go, étape, statut, **licence
   commerciale vérifiée** (les licences non commerciales sont éliminatoires : FLUX.2 klein 9B,
   FLUX.1-dev, F5-TTS…).
4. Mettre à jour l'identifiant dans le module (`factory/doctor.py` fige les identifiants).
5. `uv run factory doctor` (génération réelle) puis un run témoin + `factory qc` ; comparer au
   run de référence. `manifest.modeles[]` enregistre version et empreinte.
6. Purger l'ancien poids, mettre le ledger à jour. Épinglages Python : `uv.lock` (torch,
   diffusers, transformers bougent ensemble).

## 9. Dettes techniques connues (au 24/09/2026)

| # | Dette | Effet | Où |
|---|---|---|---|
| 1 | Le coût au manifeste est écrasé à chaque reprise | 3 manifestes sur 6 portent un coût faux | `execution.cost`, `reports/compound.md` § 5 |
| 2 | `respiration` varie d'un facteur 95 entre deux runs de même chaîne, cause non établie | bascule seule le verdict QC | STATE, É22.1 |
| 3 | `research` cherche les mots du titre, pas le sujet | ≈ 1 sujet sur 2 non sourçable, job mort en 2ᵉ étape | `steps/research.py` |
| 4 | Les tentatives ne distinguent pas échec transitoire et déterministe | 1 h 20 d'attente inutile par échec | `orchestrator/runner.py`, INTERFACES div. 83 |
| 5 | La purge post-export ne s'exécute pas quand `export` sort en code 4 (écart de plans détectés) | ≈ 1,5 Go gardés par run ; 2 runs/nuit ne tiennent pas | `steps/export.py:330` |
| 6 | Pas de ré-invalidation aval après une étape relancée à la main | caches périmés silencieux | `run.py`, marqueurs `.done` |
| 7 | Le garde mémoire ne s'applique qu'avant une étape ; le garde disque est trompé par le swap | panique noyau du 21/09 | `orchestrator/runner.py` |
| 8 | `zoompan` : 43 % de plans figés, **qui font le style approuvé** | ne pas « réparer » sans Thomas | `styles/illustre.py:_rendre_ken_burns` |
| 9 | `assemble` ne monte pas intro/outro ; mode présentateur génère encore les images hôte | identité de chaîne ; ≈ 13 min/vidéo perdues | `steps/assemble.py`, `styles/avatar2d.py` |
| 10 | Whiteboard : aucun run complet ni QC PASS | style non prouvé bout en bout | SUIVI étape 30.2 |
| 11 | `CONFORMITE.md` § 2 porte un chiffre de quota faux (1 600 unités par upload) | plafond de 6/jour à re-motiver | STATE, question Thomas |
| 12 | Rhubarb x86_64 sous Rosetta 2 ; Kokoro bloqué par l'arbitrage GPL | dépendance Rosetta ; voix à RTF 3,29 (37 min/vidéo) | `outils/MODELES.md` |
| 13 | Sujets hors niche sortis de `topics_queue` (3/6 le 23/09) | la relecture humaine est le seul filtre | `editorial/topics.py` |
| 14 | Taux de conversion EUR/USD de `config/economics.yaml` estimé (0,86) | à relever au premier revenu | `economics.yaml` |

## 10. Conventions

- **Langue** : documentation, messages CLI, tableau de bord en français ; identifiants de code en
  anglais ou français court selon le module existant (suivre le voisinage) ; commentaires courts.
- **Configuration** : YAML + pydantic v2 `extra="forbid"` ; `schema_version` dans chaque fichier racine.
- **Écriture atomique** : `<nom>.tmp` puis `os.replace()`, toujours.
- **Codes de sortie** : 0 succès · 1 erreur d'outil · 2 erreur d'usage/config · 3 incohérence de run · 4 contrôle métier en échec (voir `INTERFACES.md`).
- **Chiffres** : « mesuré » (source), « estimé » (calcul), « non mesuré ». Jamais de chiffre inventé.
- **Journaux** : commandes verbeuses redirigées vers `workspace/logs/` ; jamais de secret.
- **Commits** : « étape N : … » ; `STATE.md` ≤ 120 lignes (surplus → `STATE-ARCHIVE.md`) ;
  `SUIVI.md` tenu pour Thomas.
- **Conformité** : aucune automatisation de navigateur sur un service Google, aucun yt-dlp,
  aucun outil d'engagement, licence enregistrée pour chaque asset (`licence.json`).
- **Règles de session** (si la reprise se fait avec un assistant) : `CLAUDE.md`.
