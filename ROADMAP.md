# ROADMAP — Usine autonome de vidéos YouTube faceless (BMS)

Version 1.0 · rédigée le 13/09/2026 · exécutant : Thomas · commanditaires : Alek et Sofiane (BMS)

## 1. Résumé exécutif

Ce document est le plan d'exécution d'un **système de production de vidéos YouTube faceless** qui choisit ses sujets sur des données, écrit, voise, monte, sous-titre, illustre et publie des vidéos sur plusieurs chaînes et dans plusieurs langues, puis **mesure ses résultats et s'en sert pour produire mieux**. Il est découpé en 7 phases et 31 étapes (37 sessions Claude Code), chacune livrant des fichiers persistants et un critère de fin vérifiable.
Contrainte absolue jusqu'à ~90 % d'avancement : **0 € de dépense**, tout tourne sur le MacBook Air M2 16 Go de Thomas, avec des outils open-source à licence commerciale. Aucun abonnement, aucune API payante, aucune carte bancaire.
Le passage à un serveur GPU (~50 €/mois, validé par Alek) n'est déclenché que par des **critères chiffrés de volume et de revenu** (section 8), jamais par la faisabilité : la démonstration complète tourne sur le Mac.
La première vidéo complète sort à la fin de la phase 1 (étape 13.2). L'intelligence éditoriale (phase 3) et la boucle de rétroaction (phase 5) sont les phases qui font la valeur de l'actif ; elles sont traitées avec le même sérieux que le pipeline.
Deux limites sont assumées d'emblée : la génération vidéo photoréaliste locale n'est pas viable (section 9, risque 1) et la publication automatique reste en « privé » tant que l'audit gratuit de l'API YouTube n'est pas passé (risque 4) — les deux ont une parade.

## 2. Thèse de valeur

Un générateur de vidéos vaut zéro : LLM local + synthèse vocale + ffmpeg se refont en un week-end. Ce qui vaut plusieurs dizaines de milliers d'euros, c'est un système qui :
1. **Sait quoi produire.** Le sujet pèse plus que toute la qualité de production. Le système contient une couche de décision éditoriale : niches notées, sujets qui performent réellement chez les concurrents, trous dans l'offre, demande mesurée (phase 3, et dès l'étape 3 pour la première vidéo).
2. **Mesure et réinjecte.** Chaque vidéo publiée est rattachée à ses choix de production (sujet, titre, miniature, hook, rythme, style, langue) et à ses résultats (rétention, durée de visionnage, CTR). Les productions suivantes en tiennent compte (phase 5). C'est ce qui fait monter la valeur avec le temps.
3. **Fabrique la rétention.** Hook des trois premières secondes, boucles ouvertes, ruptures de rythme, densité d'information, rythme de coupe par niche : paramétrés, générés, puis **vérifiés par un banc objectif** qui bloque la publication sous le seuil (phase 2).
4. **Multiplie.** Multi-chaînes et multi-langues par configuration dès le modèle de données (étape 9) ; une production en engendre d'autres par adaptation (étape 24).
5. **Survit.** Conformité YouTube (contenu inauthentique, contenu synthétique, droits musique/images), cadence crédible, isolation des comptes : contrainte de conception fixée à l'étape 1, vérifiée avant chaque publication.
6. **S'exploite sans son auteur.** Configuration par fichiers, tableau de bord, journal lisible, documentation d'exploitation (phase 6).
7. **Capitalise.** Bibliothèque d'assets, voix et personnages cohérents, chartes par chaîne : la vidéo n° 50 coûte moins cher et vaut plus que la n° 1 (étape 29).
**Règle d'arbitrage pour toute session qui hésite :** choisir ce qui sert le plus les points 1, 2 et 3. La beauté du rendu passe après : une vidéo correcte sur le bon sujet avec le bon hook bat une vidéo splendide sur un mauvais sujet.

## 3. Contexte figé

### 3.1 Le client et la demande
- Client : Alek (associé : Sofiane), structure « BMS ». Demande textuelle : *« We need the process of creating YouTube videos for almost 0$ and no employees. Completed workflow that are working by themselves in total autonomy. »*
- But business : vendre des produits et faire de l'affiliation via des réseaux de chaînes YouTube faceless. Aucun produit fourni : le système est générique et piloté par configuration.
- Qualité exigée : *« faut que ça soit au niveau des vidéos du PDF de Sofiane »* (registre décrit en 3.3).
- Styles à offrir **en paramètre** (jamais en branche de code) : whiteboard animé, motion design, images cartoon, animations poussées, vidéos réalistes, documentaire, avatar parlant.
- Budget : 0 € jusqu'à ~90 % du projet ; ensuite serveur GPU ~50 €/mois (*« 50€/mois approved, t'as ma carte pour ça »*), justifié par le volume seulement.
- Limite déjà annoncée par Thomas à Alek : *« ça ne sera jamais au niveau de Higgsfield pour les styles réalistes »*. Exact. Tranché à l'étape 6 avec preuves et réponse à Alek.
- Exécutant : Thomas, développeur depuis 8 ans, francophone. Exploitants finaux : Alek et Sofiane, sans lire de code. Documentation en français, identifiants de code en anglais.

### 3.2 Machine cible (vérifiée le 13/09/2026)
- MacBook Air, Apple M2, 8 cœurs (4P + 4E), 16 Go de RAM unifiée, macOS 27.0, **30 Gi libres** sur 228 Go.
- Installés : Homebrew, Python 3.9.6 système (ne pas l'utiliser : Python 3.12 via `uv`), Node, ffmpeg, git, uv, Docker. Absents : ollama, ComfyUI, tout modèle.
- Conséquences non négociables : Metal/MPS ou CPU seulement ; **un seul modèle résident en mémoire à la fois** (un processus par étape) ; poids disque annoncé avant chaque téléchargement ; cumul des modèles retenus **≤ 22 Go** (relevé de 18 à 22 le 15/09/2026 par Thomas, après la mesure de 21,52 Go en fin d'étape 5.2) ; **plancher 8 Go libres jamais franchi** ; ledger `outils/MODELES.md` ; purge des modèles non retenus en fin d'étape ; caches (`HF_HOME`, `MLX`, `OLLAMA_MODELS`) redirigés vers `models/`.

### 3.3 Cibles chiffrées du registre (« Rapport BMS », P9, 30/08 → 11/09/2026, ~70 chaînes)
- **Réseaux clonés par langue** : Library of Thoth EN (398 vidéos, ~29K abonnés) / Bibliothèque de Thot FR (324, 67,6K) / Biblioteca di Thoth IT (241, 13,1K) ; Bibliothèque Gnostique FR (120) / La Biblioteca Gnóstica ES (14) ; Gnostic Library, Enoch Discoveries, Hermetic Talk (hub de collaborations). Modèle : « funnel + collabs ». → Levier de volume de l'architecture (étape 24).
- **Trajectoires opposées** (matière première de l'étape 3) : CasiCreativo English 704K vues / 57 vidéos, « référence DA », chaîne mère ES 8,75M · Elias Yoder Amish 345K, explosion mai → août 2026, format avatar · Life According to Science 80,7K en 12 mois, en décrue · Health Snippet 89,9K abonnés, chaîne morte en janvier 2025.
- **Rythme de coupe** (médiane en secondes par plan, 29 chaînes) — paramètre par niche appliqué au découpage (étape 12.1) et vérifié par le banc (étape 15) :

| Chaîne | s/plan | Chaîne | s/plan | Chaîne | s/plan |
|---|---|---|---|---|---|
| Saving Savers | 3,8 | Old Ways Chronicle | 6,9 | Grandpa's Old Ways | 14,1 |
| Khachakirner20 | 3,9 | Space Matters | 7,3 | Affinity Arc | 15,0 |
| Elias Yoder (92 mesures) | 4,1 | Wellness+Wisdom | 7,8 | Bruce Lipton | 18,5 |
| Our History | 4,4 | Ty Notts | 8,0 | The History Channel | 18,5 |
| InsightInfinite | 5,2 | Silas Crowe | 8,6 | Now Next | 18,5 |
| BBC Earth Science | 5,5 | AB Documentary | 8,6 | Law&Crime | 21,8 |
| Frugal Solutions | 5,7 | Crime Is Fun | 9,6 | Fox News | 48,0 |
| Science Channel | 5,7 | Daniel Moreno | 11,4 | Frozen Pennies | 48,0 |
| Spark | 6,0 | People Pattern | 12,6 | Homestead Tessie | 60,0 |
| Surviving The Survivor | 80,0 | Spiritual Dive | 240,0 | | |

- **Labels de niche** : `home_hacks`, `spiritualite`, `histoire_doc`, `science_pop`, `true_crime`, `yoder`, `moreno`, `frugal`.
- **Formats observés** : faceless voix off ; persona avatar avec acteur payé (Daniel Moreno) ; animation d'organes et motion design (CasiCreativo) ; home hacks avec avatar (Elias Yoder) ; documentaire histoire ; science populaire ; true crime.
- **Niches monétisables scannées** : longévité/biohacking EN (Huberman, Bryan Johnson, FoundMyFitness, Dr. Eric Berg…), paris sportifs EN (PickFinder, Juiced Bets, Clark Knows Ball…), compléments alimentaires FR (Nutripure, Nutri&Co, Novoma, Vincent Biohack, Quentin Fitlife), peptides USA (Dr. Ashley Froese, Doctor Youn, Dr. Paul Anderson).
- Le PDF (`/Users/toms/Downloads/REGISTRE-CHAINES.pdf`, 4 pages) n'est qu'un index de liens : il est copié dans `registre/` et lu une seule fois, à l'étape 2, pour en extraire les URL des chaînes.

### 3.4 Contraintes dures
1. 0 € : outil éligible = open-source ou gratuit, local, **licence commerciale vérifiée** (les licences non commerciales sont éliminatoires et signalées).
2. Tout tourne sur le M2 16 Go / 30 Go libres ; aucune étape ne dépend d'un GPU NVIDIA.
3. Autonomie : l'humain arbitre par configuration et par contrôle qualité **par lots** (jamais plan par plan).
4. Multi-style, multi-chaînes, multi-langues = trois paramètres de configuration.
5. Budget de contexte par session : cible ≤ 30 %, plafond 40 % (200 000 tokens = 100 %).
6. Chaque prompt est autonome : la session démarre vierge et lit `ROADMAP.md` (sections 3 et son étape), `STATE.md` et les livrables nommés.
7. Une vidéo complète sort à la fin de la phase 1, avant toute optimisation module par module.
8. Conformité YouTube et droit français/UE traités comme contraintes d'architecture (étape 1), pas comme vérification finale.

### 3.5 Synthèse de veille du 13/09/2026 (pistes à mesurer, pas décisions)
**Briques et candidats (licence · poids · statut)** — vérification finale à l'étape 4, mesure aux étapes 5.1 et 5.2 :
- LLM : Qwen3.5-9B Q4 via mlx-lm (Apache-2.0 · ~5,2 Go · référence M2 Air : 7B Q4 ≈ 22 tok/s) ; repli Gemma 4 E4B Q4 (Apache-2.0 · ~3 Go). Mistral Small 24B ne tient pas à côté du reste.
- TTS : Kokoro-82M (Apache-2.0 · 0,33 Go · FR une seule voix notée B-, IT deux voix notées C) ; Chatterbox Multilingual (MIT · ~2 Go · 23 langues · MPS incertain · filigrane audio PerTh) ; Qwen3-TTS-12Hz-1.7B (Apache-2.0 · ~4 Go · 10 langues · clonage 3 s). Exigence : ≥ 2 voix par langue.
- ASR / sous-titres mot à mot : parakeet-tdt-0.6b-v3 via parakeet-mlx (CC-BY-4.0, attribution NVIDIA · 2,5 Go · 25 langues) ; whisper.cpp large-v3-turbo Core ML (MIT · 0,6-1,6 Go) ; WhisperX pour alignement forcé (CPU seul sur Mac).
- Image : FLUX.2 [klein] 4B en mflux 4-bit (Apache-2.0 · 4,6 Go · ~9 s en 512² sur puce M) ; SDXL 1.0 (OpenRAIL++ · 6,9 Go · écosystème LoRA, Draw Things gratuit) ; Z-Image-Turbo 6B (Apache-2.0 · ~5 Go en 4-bit, non sourcé).
- Parallaxe 2.5D : Depth Anything V2 **Small** (Apache-2.0 · 0,1 Go). Base/Large/Giant = CC-BY-NC, éliminés. Ken Burns : ffmpeg `zoompan` (suréchantillonner ×4 contre le jitter).
- Vidéo générative locale : **non viable sur M2 16 Go** (Wan 2.2 GGUF : 82 min pour 2 s sur M1 Max 64 Go ; LTX-2 : ~15 min pour ~4 s en 512×288 sur M1 16 Go ; FP8 plante sur Metal). Preuve locale conditionnelle à l'étape 5.2 ; le style réaliste = banques de vidéos libres + montage.
- Composition programmatique : Revideo (MIT, rendu serveur) ou Motion Canvas (MIT) ; Remotion est **gratuit jusqu'à 3 personnes, freelances inclus, payant à la 4ᵉ** → évité. Manim CE (MIT) et MoviePy v2 (MIT) en appoint.
- Whiteboard : vtracer (MIT) → SVG → animation `stroke-dashoffset` + main PNG ; pas d'équivalent VideoScribe clé en main.
- Avatar : 2D en calques + Rhubarb Lip Sync (MIT, visèmes) ; MuseTalk 1.5 port MLX (MIT · ~2 Go · lip-sync sur boucle vidéo, débit annoncé sans puce précisée). LivePortrait dépend d'InsightFace (non commercial) ; Wav2Lip, Hallo, EchoMimic v3 : éliminés (licence ou CUDA).
- Musique/SFX : YouTube Audio Library (téléchargée depuis le Studio de la chaîne, crédit CC automatisé) ; Freesound (filtre CC0/CC-BY) ; Incompetech (CC-BY) ; génération ACE-Step 1.5 (Apache-2.0, 2B turbo quantifié seulement). MusicGen et YuE (CC-BY-NC) éliminés.
- Banques vidéo/image : Pexels API (200 req/h, 20 000/mois, attribution enregistrée), Pixabay, Openverse (sans clé, filtre `commercial`), Wikimedia Commons, NASA, Internet Archive.
- Miniatures : Playwright HTML→PNG (Apache-2.0) ou satori + resvg (MPL-2.0) ; polices Google Fonts OFL ; détourage rembg-BiRefNet (MIT) ou Apple Vision (système). BRIA RMBG-2.0 payant en commercial.
- Banc : PySceneDetect (BSD-3), ffmpeg `ebur128`/`silencedetect`, imagehash (BSD).
**Éliminés pour licence** : F5-TTS (poids CC-BY-NC), XTTS/Coqui (CPML), FLUX.1-dev, FLUX.2-dev 32B et FLUX.2-klein 9B (non commerciaux), SDXL-Turbo/SD-Turbo, Higgs Audio v3, VibeVoice (recherche), IndexTTS 2 (licence maison), HunyuanVideo (territoire hors UE), Gemma 3 (Gemma Terms), Llama 4 (restrictions UE), CogVideoX-5B, potrace (GPL, préférer vtracer).
**YouTube — accès et règles (vérifiés sur documentation officielle)** :
- Data API v3 : quotas en compartiments depuis 06/2026 — 100 appels `search.list`/jour, 100 `videos.insert`/jour, 10 000 unités/jour pour le reste (`channels.list`, `playlistItems.list`, `videos.list` = 1 unité ; `videos.update` et `thumbnails.set` = 50 ; `captions.insert` = 400). Conséquence : veille par listes de chaînes et playlists d'uploads, jamais par `search.list`.
- **Tout upload par un projet API non audité est forcé en privé.** Audit gratuit (formulaire « Audit and Quota Extension »), délai de semaines à mois. Écran de consentement OAuth en « Testing » = jetons expirant sous 7 jours → passer « En production ». Automatisation navigateur = violation des ToS, exclue.
- Analytics API : vues, minutes, durée moyenne, %, abonnés, sources de trafic, **courbe de rétention** (`audienceWatchRatio` × `elapsedVideoTimeRatio`). Impressions et CTR : **Reporting API seulement** (rapports « reach » depuis 01/2026, rétention 30-60 jours, aucun rétroactif avant création du job). Latence jusqu'à 72 h. Rien sur les chaînes concurrentes.
- Sources de demande gratuites : Wikimedia Pageviews API (fiable, User-Agent obligatoire), autocomplete YouTube (non documenté), Google Trends API officielle (alpha sur candidature ; pytrends mort), Keyword Planner (sans carte, fourchettes larges). Reddit API = payante en usage commercial. Social Blade : scraping interdit. yt-dlp / youtube-transcript-api : hors ToS, bloqués en datacenter, tolérés à faible volume en IP résidentielle pour la recherche seulement.
- Politiques : « contenu inauthentique » (07/2025) et terminaisons de janvier 2026 ciblent « IA + templates génériques + volume » ; label « contenu altéré ou synthétique » (`status.containsSyntheticMedia`) obligatoire pour les scènes réalistes générées, étiquetage automatique par YouTube depuis 05/2026 ; case « promotion payante » pour toute affiliation ; loi française 2023-451 : mention « Publicité » incrustée pendant la promotion ; RIA (AI Act) art. 50 applicable depuis le 02/08/2026 (exception si contrôle éditorial humain documenté) ; YPP : 1 000 abonnés + 4 000 h, accès étendu à 500 abonnés ; YouTube Shopping indisponible en France ; en cas de terminaison, les « chaînes associées » tombent aussi.

## 4. Vue d'ensemble du pipeline

```
 ┌──────────────────────── COUCHE ÉDITORIALE (phase 3, alimentée dès l'étape 3) ────────────────────────┐
 │ registre (70 chaînes) ─► REFERENTIEL.json ─► entrepôt concurrentiel (snapshots quotidiens, API)        │
 │ demande (Wikimedia, autocomplete) ─► notation des niches ─► sujets gagnants / trous ─► topics_queue     │
 └──────────────────────────────────────────────┬──────────────────────────────────────────────────────┘
                                                ▼  (config : chaîne = langue + niche + style + voix + charte)
 plan ─► recherche ─► script (hook, boucles, densité, signature humaine) ─► RELECTURE PAR LOTS (journal)
   │                                                                                        │
   ▼                                                                                        ▼
 voix (TTS, -14 LUFS) ─► sous-titres (ASR mot à mot) ─► découpage en plans (rythme par niche)
   │
   ▼  StyleEngine (paramètre) : cartes · illustré · documentaire · motion · whiteboard · avatar 2D
 assets (images IA, banques libres, bibliothèque réutilisable, licences) ─► rendu des plans ─► montage
   │
   ▼
 miniature (variantes) + titres (variantes) + métadonnées (chapitres, divulgations, affiliation sub-ID)
   │
   ▼
 BANC QC (rythme, hook, durée, audio, lisibilité) ─► PORTILLON ─► régénération ou blocage
   │
   ▼
 publication (API : privé → programmé ; calendrier crédible ; checklist conformité) ─► déclinaisons multilingues
   │
   ▼
 mesure (Analytics + Reporting : vues, rétention, CTR) ─► jointure avec le manifeste de run ─► APPRENTISSAGE
   │                                                                                            │
   └────────────────────────── poids appris (sujets, hooks, titres, rythme, créneaux) ◄─────────┘
                                   + économie unitaire (coût/vidéo, revenu/vidéo, par niche et langue)
```
Chaque run vit dans `workspace/runs/<video_id>/` avec un `manifest.json` qui trace toutes les décisions : c'est la clé de jointure de la boucle de rétroaction.

## 5. Tableau récapitulatif

| # | Phase | Étape | Livrables | Sous-agents | Contexte estimé | Dépend de |
|---|---|---|---|---|---|---|
| 1 | 0 | Amorcer le dépôt et figer le cadre de conformité | arbo, `STATE.md`, `CLAUDE.md`, `outils/MODELES.md`, `docs/CONFORMITE.md` | 2 | 43 750 tk — 21,9 % | — |
| 2 | 0 | Collecter les données du registre via l'API officielle | projet GCP, `registre/chaines.csv`, `registre/collecte.py`, `registre/data/`, `registre/data/INDEX.md` | 1 | 56 000 tk — 28,0 % | 1 |
| 3 | 0 | Référentiel exploitable, sujets porteurs, hooks, trajectoires | `registre/REFERENTIEL.json`, `REFERENTIEL.md`, `TRAJECTOIRES.md` | 4 + 1 contradicteur | 59 125 tk — 29,6 % | 2 |
| 4 | 0 | Veille et sélection des outils par brique | `outils/SELECTION.md`, `outils/LICENCES.md` | 4 + 1 contradicteur | 54 125 tk — 27,1 % | 3 |
| 5.1 | 0 | Mesurer texte et audio sur le M2 | `benchmarks/bench_audio.sh`, `benchmarks/RESULTATS.md` §1 | 2 | 64 125 tk — 32,1 % | 4 |
| 5.2 | 0 | Mesurer image, parallaxe, composition, preuve vidéo IA | `benchmarks/bench_visuel.sh`, `RESULTATS.md` §2, `benchmarks/samples/` | 2 | 70 750 tk — 35,4 % | 5.1 |
| 6 | 0 | Trancher les styles et la réponse à Alek | `docs/STYLES.md` | 1 contradicteur | 51 125 tk — 25,6 % | 5.2 |
| 7 | 0 | Installer et figer l'environnement | `pyproject.toml`, `uv.lock`, `factory/doctor.py`, `docs/INSTALL.md` | 0 | 57 750 tk — 28,9 % | 6 |
| 8 | 1 | Architecture et contrats d'interface | `docs/ARCHITECTURE.md`, `docs/INTERFACES.md` | 1 contradicteur | 62 625 tk — 31,3 % | 7 |
| 9 | 1 | Modèle de données versionné, configuration, secrets | `factory/core/models.py`, `factory/core/config.py`, `config/**`, tests | 0 | 63 875 tk — 31,9 % | 8 |
| 10 | 1 | Sujet issu du référentiel → recherche → script structuré | `factory/steps/plan.py`, `research.py`, `script.py` | 1 | 59 875 tk — 29,9 % | 9 |
| 11 | 1 | Voix et sous-titres | `factory/steps/voice.py`, `subtitles.py` | 0 | 55 125 tk — 27,6 % | 10 |
| 12.1 | 1 | Découpage en plans, interface StyleEngine, moteur « cartes » | `factory/steps/shotlist.py`, `factory/styles/base.py`, `cartes.py` | 0 | 59 625 tk — 29,8 % | 11 |
| 12.2 | 1 | Moteur « illustré animé » | `factory/styles/illustre.py`, `factory/assets/images.py`, `parallax.py` | 1 | 67 875 tk — 33,9 % | 12.1 |
| 13.1 | 1 | Montage, musique, sous-titres, export vérifié | `factory/steps/assemble.py`, `export.py` | 0 | 63 625 tk — 31,8 % | 12.2 |
| 13.2 | 1 | Miniature, métadonnées, `factory run`, première vidéo complète | `thumbnail.py`, `metadata.py`, `factory/cli.py`, `final.mp4` | 0 | 66 375 tk — 33,2 % | 13.1 |
| 14 | 1 | Ouvrir le canal officiel : upload privé, OAuth, dépôt d'audit | `factory/publish/oauth.py`, `upload_min.py`, `docs/AUDIT-API.md`, `docs/PRIVACY.md` | 1 | 53 875 tk — 26,9 % | 13.2, 2 |
| 15 | 2 | Banc d'évaluation objectif et portillon qualité | `factory/eval/bench.py`, `config/qc.yaml`, `docs/QC.md` | 1 + 1 contradicteur | 59 250 tk — 29,6 % | 13.2 |
| 16 | 2 | Ingénierie du hook et de la rétention | `factory/retention/*.py`, tests | 2 | 67 750 tk — 33,9 % | 15 |
| 17 | 2 | Moteur « documentaire » et rythme de coupe vérifié | `factory/styles/documentaire.py`, `factory/assets/stock.py` | 1 | 68 125 tk — 34,1 % | 15 |
| 18 | 3 | Entrepôt concurrentiel et snapshots quotidiens | `factory/editorial/collect.py`, tables SQLite, plist launchd | 1 | 57 875 tk — 28,9 % | 2, 9 |
| 19 | 3 | Détection et notation de niches | `factory/editorial/niches.py`, `reports/niches.md` | 1 + 1 contradicteur | 59 500 tk — 29,8 % | 18 |
| 20 | 3 | Sujets gagnants, trous dans l'offre, file de sujets | `factory/editorial/topics.py`, table `topics_queue` | 1 | 59 875 tk — 29,9 % | 19 |
| 21 | 3 | Titres, miniatures et métadonnées en variantes, sub-ID | `factory/editorial/titles.py`, `thumbnails_variants.py`, `seo.py` | 1 | 66 500 tk — 33,2 % | 20, 13.2 |
| 22.1 | 4 | Orchestrateur : file, reprise, journal, daemon, sauvegardes | `factory/orchestrator/queue.py`, `runner.py`, `backup.py`, plist | 1 | 63 750 tk — 31,9 % | 15, 20 |
| 22.2 | 4 | Relecture par lots, régénération sous seuil, alertes | `factory/orchestrator/review.py`, `regenerate.py`, `notify.py` | 0 | 56 750 tk — 28,4 % | 22.1, 16 |
| 23.1 | 4 | Publication API : OAuth par chaîne, upload, label, quota, jobs « reach » | `factory/publish/youtube.py`, `quota.py`, `reporting_jobs.py` | 1 | 59 500 tk — 29,8 % | 14, 21, 22.1 |
| 23.2 | 4 | Calendrier crédible, checklist conformité, bascule post-audit | `factory/publish/calendar.py`, `precheck.py`, `docs/CONFORMITE.md` §op. | 1 contradicteur | 56 750 tk — 28,4 % | 23.1 |
| 24 | 4 | Déclinaison multilingue par adaptation | `factory/steps/localize.py` | 1 | 62 500 tk — 31,2 % | 23.2, 16 |
| 25 | 5 | Récupérer les performances et les joindre au manifeste | `factory/analytics/pull.py`, vues SQL | 1 | 59 625 tk — 29,8 % | 23.1, 18 |
| 26 | 5 | Apprendre et réinjecter ; valider le banc contre les vues | `factory/analytics/learn.py`, `learned/weights.json`, `reports/learn_*.md` | 1 + 1 contradicteur | 64 125 tk — 32,1 % | 25 |
| 27 | 5 | Affiliation, funnel et économie unitaire | `factory/monetization/*.py`, `reports/economics.md` | 1 | 58 125 tk — 29,1 % | 25, 21 |
| 28 | 6 | Tableau de bord d'exploitation | `dashboard/app.py`, `docs/img/` | 1 | 65 875 tk — 32,9 % | 22.2, 26 |
| 29 | 6 | Bibliothèque d'assets, voix et personnages cohérents, avatar 2D, chartes | `factory/library.py`, `factory/styles/avatar2d.py`, `config/chartes/`, `reports/compound.md` | 1 | 70 750 tk — 35,4 % | 17, 26 |
| 30.1 | 6 | Moteur « motion design » (Revideo) | `render/`, `factory/styles/motion.py` | 1 | 69 875 tk — 34,9 % | 15, 7 |
| 30.2 | 6 | Moteur « whiteboard » | `factory/styles/whiteboard.py`, `render/src/scenes/draw-svg.ts` | 0 | 59 500 tk — 29,8 % | 30.1 |
| 31 | 6 | Documentation d'exploitation, reprise, plan de passage à l'échelle | `docs/EXPLOITATION.md`, `docs/REPRISE.md`, `docs/SCALE.md` | 3 + 1 testeur | 59 750 tk — 29,9 % | 28, 29, 30.2 |

Plafond observé : 35,4 % (étape 5.2). 21 sessions sur 37 sont à 30 % ou moins.

## 6. Les phases et leurs étapes

## Phase 0 — Fondations et faisabilité réelle

**Objectif de la phase.** Transformer le registre en cibles exploitables par le code, fixer le cadre de conformité, choisir les outils sur licence vérifiée, **mesurer** ce qui tourne réellement sur le M2, trancher les styles, installer l'environnement.
**Jalon de phase.** `uv run factory doctor` retourne 0 (LLM, TTS, ASR, image, profondeur, ffmpeg, Rhubarb répondent) · `docs/STYLES.md` contient le verdict des 7 styles et la réponse à Alek · `registre/REFERENTIEL.json` est valide · ≥ 10 Go de disque libres.

## Étape 1 — Amorcer le dépôt et figer le cadre de conformité

**Objectif.** Créer l'ossature du projet, les règles de session et `docs/CONFORMITE.md`, le document qui contraint toute l'architecture qui suit.
**Pourquoi maintenant.** La conformité YouTube et le droit français/UE imposent des champs de données, un chemin de publication et des limites de cadence : les décider après l'architecture obligerait à la refaire.
**Valeur créée.** Thèse n° 5 (survie) et n° 6 (exploitabilité) : un système qui fait bannir des chaînes vaut moins que zéro.
**Pré-requis.** Aucun. `ROADMAP.md` existe.
**Sous-agents.** 2 en parallèle — (A) règles YouTube 2026 (contenu inauthentique, contenu réutilisé, label synthétique, spam, YPP, Audio Library, promotion payante, chaînes associées, ToS de l'API) ; (B) droit français et européen (loi 2023-451, RIA art. 50, conditions des programmes d'affiliation accessibles depuis la France). 450 mots maximum chacun, format imposé.
**Livrables.** `CLAUDE.md`, `STATE.md`, `.gitignore`, `.env.example`, `outils/MODELES.md`, `docs/CONFORMITE.md`, arborescence complète, premier commit git.
**Poids disque.** 0.
**Terminé quand.** `git log` montre un commit · `wc -l CLAUDE.md` ≤ 40 · `docs/CONFORMITE.md` contient les 11 sections listées dans le prompt, chacune avec au moins une source URL · `STATE.md` existe au format imposé · `ls` montre l'arborescence complète.

**Prompt à copier-coller :**

````text
Tu es architecte logiciel et responsable conformité d'un studio de production vidéo automatisé.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless pour BMS (Alek, Sofiane), 0 € de dépense, tout en local sur un MacBook Air M2 16 Go. Ce projet est conçu comme un actif revendable : il doit survivre aux règles YouTube (contenu inauthentique, contenu synthétique, chaînes associées), au droit français (loi 2023-451 sur l'influence commerciale) et au règlement européen sur l'IA (art. 50, applicable depuis le 02/08/2026).
Cette session crée l'ossature du dépôt et écrit docs/CONFORMITE.md, le document que toutes les sessions suivantes liront pour concevoir le modèle de données, le pipeline de publication et le contrôle qualité. Une règle oubliée ici se paie par une chaîne terminée plus tard.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation. Tous les chemins relatifs ci-dessous s'y rapportent ; place-toi dedans.
Lis, dans cet ordre, et rien d'autre :
1. ROADMAP.md — uniquement trois sections : « ## 3. Contexte figé », « ## Étape 1 » et « ## 7. Règles de session permanentes ». Localise-les avec
   grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 1 \|^## Étape 2 \|^## 7\.\|^## 8\." ROADMAP.md
   puis lis chaque section avec Read (offset/limit). Le fichier fait ~7 000 lignes : ne le lis jamais en entier.
2. Rien d'autre : STATE.md n'existe pas encore, c'est toi qui le crées.
</demarrage>

<sous_agents>
Lance immédiatement 2 sous-agents en parallèle, en un seul envoi. Ils font les recherches web ; tu ne les fais pas toi-même.
- Agent A — Règles YouTube au 13/09/2026, sources officielles support.google.com et developers.google.com uniquement : politique de monétisation « contenu inauthentique » (formulation exacte depuis le 15/07/2025), contenu réutilisé, divulgation « contenu altéré ou synthétique » et champ API status.containsSyntheticMedia, politique spam et pratiques trompeuses, seuils YPP et accès étendu, licence de l'Audio Library (pistes CC, crédit), case « promotion payante », clause de terminaison des « chaînes associées », conditions d'utilisation des services API YouTube (audit, données stockées, usages interdits), restriction « upload privé pour projet non audité ».
- Agent B — Droit applicable à une société française publiant des vidéos générées par IA et monétisées par affiliation : loi n° 2023-451 (mentions obligatoires, sanctions), RIA art. 50 §2 §4 §5 (obligations du déployeur, exception contrôle éditorial humain, marquage lisible par machine), conditions d'accès sans frais aux principaux programmes d'affiliation depuis la France (Amazon Partenaires, Awin, CJ, Impact : paramètre de sous-identifiant par lien, export CSV des conversions, durée de cookie).
Format de réponse imposé à chacun, 450 mots maximum, une ligne par règle :
  RÈGLE | FORMULATION EXACTE OU RÉSUMÉ FIDÈLE | CONSÉQUENCE DE CONCEPTION POUR NOTRE SYSTÈME | URL
Un sous-agent rapporte, il ne décide pas.
</sous_agents>

<tache>
Réfléchis d'abord, avant d'écrire : quels champs de données, quelles limites de cadence, quel chemin de publication découlent des règles rapportées. Puis :
1. Crée l'arborescence :
   docs/ registre/ registre/data/ outils/ benchmarks/ benchmarks/samples/ factory/ config/ config/channels/ config/niches/ config/styles/ config/languages/ config/products/ workspace/ workspace/runs/ workspace/library/ workspace/logs/ models/ reports/ secrets/ dashboard/ render/
   Ajoute un fichier .gitkeep dans chaque dossier vide.
2. Écris .gitignore : models/ workspace/ secrets/ .env .venv/ node_modules/ render/node_modules/ *.log __pycache__/ .DS_Store registre/data/**/thumbs/ registre/data/**/transcripts/ ; ainsi que .env.example avec les variables prévues (YT_API_KEY, HF_HOME=./models/hf, OLLAMA_MODELS=./models/ollama, TELEGRAM_BOT_TOKEN vide).
3. Écris CLAUDE.md (40 lignes maximum) : reprends la section « 7. Règles de session permanentes » de ROADMAP.md en la condensant, sans rien y ajouter d'autre. Ce fichier est chargé dans chaque session : chaque ligne coûte du contexte à toutes les étapes suivantes.
4. Écris STATE.md avec exactement ces sections, 120 lignes maximum en régime de croisière :
   # STATE — mémoire entre sessions
   ## Étape courante (numéro, date, statut)
   ## Fait (une ligne par étape terminée : numéro, date, livrables, commit)
   ## Décisions (une ligne par décision structurante, avec l'étape qui l'a prise)
   ## Bloqué / risques actifs
   ## Questions ouvertes (avec le nom de qui doit trancher : Thomas, Alek, Sofiane)
   ## Environnement (disque libre en Go, modèles installés → voir outils/MODELES.md, versions clés)
   Ajoute la consigne en tête : « Quand ce fichier dépasse 120 lignes, déplace les lignes les plus anciennes de « Fait » et « Décisions » dans STATE-ARCHIVE.md ».
5. Écris outils/MODELES.md, ledger des poids téléchargés : tableau | Modèle | Chemin | Go | Étape | Statut (retenu / purgé / en test) | Licence | ; ligne d'en-tête « Cumul retenu : 0 Go — plancher disque : 8 Go libres ».
6. Écris docs/CONFORMITE.md avec ces 11 sections numérotées, chacune : la règle (formulation ou résumé fidèle + URL), puis « Conséquence de conception » en phrases impératives :
   1. Comptes et chaînes : un compte Google par chaîne, Brand Accounts détenus par BMS (pas par une personne physique), 2FA, vérification téléphonique (nécessaire pour miniatures personnalisées et vidéos > 15 min), pas de partage de session, clause « chaînes associées » ; un seul projet Google Cloud pour l'API (un seul audit) — expose le compromis isolation vs audits multiples et la décision.
   2. Chemin de publication : upload privé via API avec métadonnées complètes → publication programmée manuellement dans YouTube Studio (≈ 2 min/vidéo) tant que l'audit n'est pas passé → bascule automatique (videos.update, publishAt) après audit. Automatisation navigateur interdite. Dépôt de l'audit dès l'étape 14.
   3. Divulgation en trois couches : status.containsSyntheticMedia (règle de décision : true dès qu'une scène réaliste générée figure un lieu, une personne ou un événement), case promotion payante dès qu'un lien d'affiliation figure, bandeau « Publicité » ou « Collaboration commerciale » incrusté à l'écran pendant tout segment promotionnel + mention en tête de description + mention orale dans les 30 premières secondes du segment.
   4. Signature humaine (anti « contenu inauthentique » et exception RIA art. 50 §4) : chaque script porte un angle éditorial propre (opinion, comparaison chiffrée, test, donnée propriétaire) et est relu par lots par un membre nommé de l'équipe ; journal de relecture (relecteur, date, hash du script, décision). Le mode « auto-approve » existe mais est documenté comme risque assumé par le client.
   5. Variation et anti-clonage : ≥ 3 templates visuels en rotation par chaîne, jamais le même script ni la même miniature sur deux chaînes de même langue, déclinaison multilingue = adaptation + habillage distinct, pas de série clonée.
   6. Cadence : ≤ 2 vidéos par chaîne et par semaine les 90 premiers jours, horaires irréguliers (jitter), pas de rafale, pas de publication simultanée sur plusieurs chaînes.
   7. Musique et sons : YouTube Audio Library téléchargée depuis le Studio de la chaîne concernée, crédit CC inséré automatiquement ; Freesound filtré CC0/CC-BY ; aucun modèle de génération musicale à licence non commerciale ; licence enregistrée pour chaque piste.
   8. Images et vidéos : banques libres avec attribution enregistrée par asset (fournisseur, URL, auteur, licence) et bloc d'attribution automatique en description ; images générées avec modèle à licence commerciale ; aucune image de personne réelle identifiable sans droit.
   9. Données concurrentes : API Data v3 officielle pour toute métadonnée ; transcriptions de vidéos tierces uniquement pendant les phases de recherche (étapes 3 et 16), à faible volume, depuis une IP résidentielle, avec un compte de recherche jamais lié aux chaînes publiantes ; jamais dans le pipeline quotidien ; jamais yt-dlp ni téléchargement de vidéos tierces ; données API stockées rafraîchies ou supprimées conformément aux conditions d'utilisation de l'API.
   10. Champs obligatoires du modèle de données (contrat pour l'étape 9) : liste explicite (contains_synthetic_media + raison, paid_promotion, sponsor_segments, disclosure_lines par langue, assets[].licence, music.licence, reviewer + review_hash + review_date, publish_channel_account, cadence_limits, dedupe_hash du script).
   11. Checklist de pré-publication automatisée (contrat pour l'étape 23.2) : liste de contrôles avec le verdict bloquant ou avertissement.
   Termine par « Sources » (toutes les URL des deux rapports) et « Décisions prises à cette étape » (compte de recherche, projet GCP unique, cadence initiale).
7. git init, premier commit « étape 1 : ossature et cadre de conformité ».
</tache>

<contraintes>
- Aucune installation d'outil, aucun téléchargement de modèle à cette étape.
- Ne recopie pas les rapports des sous-agents tels quels : chaque règle doit être suivie de sa conséquence de conception pour ce système précis.
- Si une règle rapportée contredit la synthèse de veille de ROADMAP.md, la source officielle la plus récente prime ; note la divergence dans STATE.md.
- Quand une information manque (par exemple : quel compte Google BMS utiliser), écris la question dans « Questions ouvertes » de STATE.md avec le nom de la personne qui tranche.
</contraintes>

<criteres_de_validation>
Avant d'annoncer la fin, vérifie et montre la sortie : ls -R (dossiers), wc -l CLAUDE.md (≤ 40), grep -c "^## " docs/CONFORMITE.md (≥ 12), grep -c "http" docs/CONFORMITE.md (≥ 15), git log --oneline (1 commit).
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 1 terminée (date, livrables, commit), décisions prises, questions ouvertes. Commit « étape 1 : ossature et cadre de conformité ». Résume en 10 lignes maximum : ce qui est fait, les 3 règles de conformité les plus contraignantes pour l'architecture, les questions ouvertes.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP (sections 3, étape 1, section 7 ≈ 400 lignes) | 5 000 |
| Prompt (~1 100 mots) | 1 500 |
| 2 rapports de sous-agents (450 mots chacun) | 2 400 |
| Commandes shell (mkdir, git) | 1 000 |
| Écriture CLAUDE.md + STATE.md + MODELES.md + .gitignore + .env.example (≈ 130 lignes) | 1 800 |
| Écriture docs/CONFORMITE.md (≈ 350 lignes) | 4 500 |
| Mise à jour STATE.md + résumé | 800 |
| Sous-total | 35 000 |
| Marge +25 % | 8 750 |
| **Total** | **43 750 tk — 21,9 %** |

## Étape 2 — Collecter les données du registre via l'API officielle

**Objectif.** Transformer l'index de liens du PDF en un jeu de données brut et complet sur les ~70 chaînes du registre (métadonnées de chaînes et de vidéos, miniatures, transcriptions des meilleures vidéos), collecté par l'API YouTube Data v3.
**Pourquoi maintenant.** Le référentiel (étape 3), la sélection des styles (étape 6) et la couche éditoriale (phase 3) reposent sur ces données ; sans elles, tout est opinion.
**Valeur créée.** Thèse n° 1 : c'est le corpus d'entraînement éditorial du système.
**Pré-requis.** Étape 1 terminée · `/Users/toms/Downloads/REGISTRE-CHAINES.pdf` présent · Thomas disponible 10 minutes pour créer le projet Google Cloud (gratuit, sans carte).
**Sous-agents.** 1 — API Data v3 au 13/09/2026 : résolution des handles (`channels.list?forHandle=`), playlist d'uploads, pagination `playlistItems.list`, parts de `videos.list`, coûts en unités, tailles de miniatures ; état actuel de `youtube-transcript-api` depuis une IP résidentielle (langues, cadence tolérée, erreurs). 400 mots maximum.
**Livrables.** `registre/REGISTRE-CHAINES.pdf` (copie), `registre/chaines.csv`, `registre/collecte.py`, `registre/data/<handle>/channel.json`, `videos.json`, `thumbs/`, `transcripts/`, `registre/data/INDEX.md`, `registre/collecte.log`.
**Poids disque.** ≈ 0,3 Go (miniatures et JSON, hors git pour les miniatures).
**Terminé quand.** `chaines.csv` ≥ 60 lignes · ≥ 55 dossiers `registre/data/<handle>/` avec `channel.json` et `videos.json` · `INDEX.md` liste chaque chaîne avec nombre de vidéos, abonnés, durée médiane, cadence · unités de quota consommées < 8 000 (affichées) · ≥ 100 fichiers de transcription ou rapport d'échec explicite.

**Prompt à copier-coller :**

````text
Tu es ingénieur données, spécialiste de l'API YouTube Data v3 et de la collecte reproductible.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local. Le registre de ~70 chaînes constitué par l'équipe de Sofiane est le corpus éditorial du système : la session suivante (étape 3) en extraira les cibles chiffrées par niche (durées, structures de titre, motifs de miniature, hooks, cadence, sujets porteurs). Cette session collecte les données brutes de façon reproductible et conforme : API officielle pour toutes les métadonnées, jamais search.list (100 appels/jour seulement), jamais yt-dlp.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation. Tous les chemins relatifs ci-dessous s'y rapportent.
Lis, dans cet ordre, et rien d'autre tant que tu n'en as pas besoin :
1. ROADMAP.md — uniquement « ## 3. Contexte figé » et « ## Étape 2 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 2 \|^## Étape 3 " ROADMAP.md puis Read en offset/limit.
2. STATE.md
3. docs/CONFORMITE.md — uniquement la section 9 (données concurrentes).
</demarrage>

<sous_agents>
Lance 1 sous-agent (recherche web, sources developers.google.com et dépôt GitHub de youtube-transcript-api) : pour l'API Data v3 au 13/09/2026 — paramètres exacts de channels.list (forHandle, forUsername, id ; parts snippet, statistics, contentDetails, brandingSettings), récupération de la playlist d'uploads, pagination de playlistItems.list (50 par page), parts et limites de videos.list (50 identifiants par appel), coût en unités de chacun, URL des miniatures maxres ; pour youtube-transcript-api — version courante, appel pour lister les langues disponibles et récupérer la transcription, erreurs fréquentes en 2026 et cadence d'appel raisonnable depuis une IP résidentielle. Format : 400 mots maximum, une ligne par point : POINT | VALEUR | URL.
Pendant qu'il travaille, fais les étapes 1 et 2 de la tâche.
</sous_agents>

<tache>
1. Projet Google Cloud (Thomas en navigateur, guide-le pas à pas) : console.cloud.google.com → nouveau projet « bms-factory » → « API et services » → activer « YouTube Data API v3 » → « Identifiants » → « Créer des identifiants » → « Clé API » → restreindre la clé à l'API YouTube Data v3. Thomas colle la clé dans .env (YT_API_KEY=...) — jamais dans la conversation. Vérifie avec : test -n "$(grep YT_API_KEY .env | cut -d= -f2)" && echo OK.
2. Copie le PDF : cp /Users/toms/Downloads/REGISTRE-CHAINES.pdf registre/. Lis-le avec Read (pages 1-4). Extrais chaque chaîne dans registre/chaines.csv, colonnes : handle_ou_url, nom, niche (labels du registre : home_hacks, spiritualite, histoire_doc, science_pop, true_crime, yoder, moreno, frugal, ou « niche_monetisable_<theme> » pour les chaînes des niches scannées), langue (fr/en/es/it, déduite du nom ou du contenu), s_par_plan (valeur du tableau de « Contexte figé » si présente, sinon vide), abonnes_pdf, videos_pdf, reseau (Thoth, Gnose, autre), trajectoire (decolle / decrue / morte / stable / inconnue), notes. Si une chaîne du tableau des rythmes de coupe n'a pas d'URL dans le PDF, tente channels.list?forHandle=@<NomSansEspaces> ; en cas d'échec, marque handle_ou_url = non_resolue.
3. Écris registre/collecte.py, exécuté avec : uv run --python 3.12 --with google-api-python-client,youtube-transcript-api,requests,python-dotenv registre/collecte.py
   Comportement : pour chaque ligne de chaines.csv → channels.list (snippet, statistics, contentDetails, brandingSettings) → playlist d'uploads → playlistItems.list pages successives jusqu'à 500 vidéos maximum → videos.list par lots de 50 (snippet, contentDetails, statistics, status) → écrit registre/data/<handle>/channel.json et videos.json (liste ordonnée par date). Télécharge la miniature maxresdefault (ou hqdefault) des 10 vidéos les plus vues dans thumbs/. Récupère la transcription des 5 vidéos les plus vues (langue de la chaîne, sinon auto-générée) dans transcripts/<video_id>.json, avec pause aléatoire de 3 à 6 s entre appels ; arrête les transcriptions après 3 échecs consécutifs et note-le. Compteur d'unités de quota affiché à la fin et arrêt automatique à 8 000. Reprise : saute les chaînes dont videos.json existe. Journal dans registre/collecte.log.
4. Exécute : ... > registre/collecte.log 2>&1 ; puis tail -30 registre/collecte.log. En cas d'erreur, corrige et relance (la reprise évite de re-consommer le quota).
5. Écris registre/data/INDEX.md : un tableau, une ligne par chaîne : handle, niche, langue, abonnés, vidéos collectées, vues totales, durée médiane (mm:ss), cadence (vidéos/mois sur les 6 derniers mois), vues médianes par vidéo, ratio top1/médiane, transcriptions obtenues ; puis la liste des chaînes non résolues et des échecs.
6. Commit : « étape 2 : collecte du registre » (registre/data/**/thumbs/ et transcripts/ restent hors git).
</tache>

<contraintes>
- Aucun appel search.list. Aucun yt-dlp. Aucune donnée collectée depuis un compte lié aux futures chaînes publiantes.
- Redirige toute sortie verbeuse vers un fichier et n'affiche que tail -30.
- Si une chaîne dépasse 500 vidéos, garde les 500 plus récentes et note-le.
- Ne lis pas les fichiers JSON produits en entier : vérifie avec des commandes ciblées (python -c "import json,...", jq, wc).
- Chiffres mesurés uniquement ; « non obtenu » plutôt qu'une estimation.
</contraintes>

<criteres_de_validation>
Montre la sortie de : wc -l registre/chaines.csv (≥ 61 avec l'en-tête) ; ls registre/data | wc -l (≥ 55) ; find registre/data -name videos.json | wc -l ; find registre/data -path '*transcripts*' -name '*.json' | wc -l ; grep -i "quota" registre/collecte.log | tail -1 (< 8 000 unités).
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 2 terminée, nombre de chaînes et de vidéos collectées, quota consommé, chaînes non résolues, échecs de transcription, disque libre. Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + CONFORMITE §9 | 7 000 |
| Prompt (~1 300 mots) | 1 800 |
| Lecture du PDF (4 pages) | 3 000 |
| 1 rapport de sous-agent | 1 200 |
| Écriture chaines.csv (≈ 75 lignes) | 1 500 |
| Écriture collecte.py (≈ 250 lignes) | 3 500 |
| Exécutions et extraits de log | 3 000 |
| Corrections et relances | 3 000 |
| Écriture INDEX.md (≈ 90 lignes) | 2 000 |
| Mise à jour STATE.md + résumé | 800 |
| Sous-total | 44 800 |
| Marge +25 % | 11 200 |
| **Total** | **56 000 tk — 28,0 %** |

## Étape 3 — Référentiel exploitable, sujets porteurs, taxonomie des hooks, trajectoires

**Objectif.** Produire `registre/REFERENTIEL.json`, le fichier que le code lira pour cibler chaque niche (rythme, durée, cadence, structures de titre, motifs de miniature, types de hook, sujets porteurs), et `registre/TRAJECTOIRES.md`, les règles qui séparent une chaîne qui décolle d'une chaîne qui meurt.
**Pourquoi maintenant.** Les étapes 10 (script), 12.1 (découpage), 15 (banc), 16 (hooks), 20 (sujets) et 21 (titres, miniatures) consomment ce fichier. Il fixe les cibles avant toute ligne de pipeline.
**Valeur créée.** Thèses n° 1 et n° 3 : le système saura ce qui marche par niche, en chiffres, avant de produire.
**Pré-requis.** Étape 2 terminée · `registre/data/` et `INDEX.md` existent.
**Sous-agents.** Vague 1, 4 en parallèle : (A) titres, durées, cadence, horaires, ratios d'outliers par niche ; (B) miniatures — inspection visuelle des 10 meilleures miniatures de 20 chaînes, motifs codables ; (C) hooks — analyse des 15 premières secondes des transcriptions, taxonomie, débit ; (D) trajectoires opposées — CasiCreativo vs Health Snippet, Elias Yoder vs Life According to Science. Vague 2 : (E) contradicteur sur le brouillon du référentiel.
**Livrables.** `registre/REFERENTIEL.json`, `registre/REFERENTIEL.md`, `registre/TRAJECTOIRES.md`.
**Poids disque.** 0.
**Terminé quand.** `python -c "import json; json.load(open('registre/REFERENTIEL.json'))"` réussit · ≥ 6 niches avec tous les champs du schéma · ≥ 10 `sujets_porteurs` par niche · ≥ 8 types dans `hooks_taxonomie` avec exemples · `TRAJECTOIRES.md` contient ≥ 8 règles testables avec preuve chiffrée · les objections du contradicteur sont traitées ou consignées.

**Prompt à copier-coller :**

````text
Tu es analyste éditorial quantitatif, spécialiste du reverse-engineering de chaînes YouTube.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local. Le choix du sujet, la construction du hook et le rythme de montage pèsent plus que la qualité de rendu. Cette session transforme les données brutes de ~70 chaînes (registre/data/) en un référentiel chiffré par niche que le code lira : registre/REFERENTIEL.json. Une valeur non mesurée ici deviendra une cible fausse pour toutes les vidéos produites.
Deux inputs précieux existent déjà dans ROADMAP.md « Contexte figé » : le tableau des rythmes de coupe (29 chaînes, mesuré par l'équipe de Sofiane) et les quatre trajectoires opposées.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 3 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 3 \|^## Étape 4 " ROADMAP.md puis Read en offset/limit.
2. STATE.md
3. registre/data/INDEX.md
Ne lis aucun videos.json ni transcription toi-même : c'est le travail des sous-agents.
</demarrage>

<sous_agents>
Vague 1 — lance 4 sous-agents en parallèle, en un seul envoi. Chacun travaille sur registre/data/ et registre/chaines.csv (colonne niche) et rapporte en 600 mots maximum, format imposé : uniquement des tableaux et des listes de valeurs, aucune prose.
- Agent A (titres, durées, cadence) : par niche — durée médiane, p25, p75 (secondes) ; cadence médiane (vidéos/semaine, 6 derniers mois) ; jours et heures de publication les plus fréquents (UTC) ; longueur médiane des titres ; 6 à 10 patrons de titre récurrents exprimés comme templates à emplacements (ex. « Why {sujet} {verbe} », « {nombre} {choses} that {promesse} », « The {adjectif} truth about {sujet} ») avec leur part et un exemple réel chacun ; ratio vues top 1 / vues médianes ; part des vidéos > 3× la médiane (« breakouts »). Calcule avec un script Python jetable, pas de tête.
- Agent B (miniatures) : regarde avec l'outil Read les 10 miniatures (thumbs/) de 20 chaînes couvrant toutes les niches (choisis les plus vues). Pour chaque niche, rapporte en attributs codables : nombre de mots de texte (médiane), présence de visage/personnage (part), palette dominante (3 codes hex), contraste (élevé/moyen/faible), composition (sujet à gauche/droite/centre), présence de flèche/cercle/emoji (part), style (photo/illustration/3D/mixte). Termine par 5 « motifs gagnants » par niche (attributs des miniatures des vidéos > 3× médiane).
- Agent C (hooks) : lis les transcriptions (transcripts/) des 5 meilleures vidéos de chaque chaîne. Sur les 15 premières secondes (≈ 40 premiers mots) : classe chaque hook dans une taxonomie que tu construis (8 à 12 types nommés en snake_case, ex. question_contrarienne, promesse_chiffree, in_medias_res, enjeu_personnel, statistique_choc, liste_annoncee, mystere_ouvert), donne la part de chaque type par niche, 2 exemples verbatim par type (≤ 25 mots), la longueur médiane du hook en mots, le débit médian (mots/minute) sur les 60 premières secondes, et repère les marqueurs de boucle ouverte (« mais avant… », « in a moment… ») et leur position moyenne.
- Agent D (trajectoires) : à partir de videos.json, compare CasiCreativo English vs Health Snippet, puis Elias Yoder Amish vs Life According to Science : cadence par trimestre, durée médiane par trimestre, vues par vidéo selon la date de publication, dérive des sujets (mots-clés des titres par trimestre), part de breakouts, changements survenus avant la décrue ou la mort. Rapporte 10 règles testables du type « faire X pendant les 90 premiers jours » avec la preuve chiffrée de chacune, et signale ce qui n'est pas prouvable avec ces données.
Vague 2 — quand tu as écrit le brouillon de REFERENTIEL.json et TRAJECTOIRES.md, lance 1 contradicteur (Agent E) qui les lit et cherche : échantillons trop petits présentés comme des cibles, valeurs absurdes, champs manquants dont le code aura besoin (étapes 10, 12.1, 15, 16, 20, 21 de ROADMAP.md — il lit leur description), règles de trajectoire non falsifiables. 400 mots maximum, liste numérotée « Problème → correction ».
</sous_agents>

<tache>
1. Écris registre/REFERENTIEL.json selon ce schéma (valeurs illustratives) :
{
  "schema_version": "1.0", "genere_le": "AAAA-MM-JJ", "source": "registre P9 + collecte étape 2",
  "niches": {
    "science_pop": {
      "chaines_source": ["@handle1", "@handle2"], "n_chaines": 6, "n_videos_analysees": 812,
      "rythme_coupe_s": {"cible": 5.5, "min": 4.0, "max": 7.5, "n_mesures": 4, "source": "tableau P9"},
      "duree_s": {"mediane": 540, "p25": 420, "p75": 720},
      "cadence_par_semaine": {"mediane": 2.0, "p75": 3.0},
      "creneaux": {"jours": ["mar", "jeu", "sam"], "heures_utc": [14, 16]},
      "titres": {"longueur_car": {"mediane": 52, "max": 70}, "patrons": [{"id": "why_x", "template": "Why {sujet} {verbe}", "part": 0.23, "exemple": "..."}]},
      "miniatures": {"texte_mots": {"mediane": 3, "max": 4}, "personnage": 0.7, "palette": ["#0b0b0b", "#f5c400", "#ffffff"], "contraste": "eleve", "motifs_gagnants": ["..."]},
      "hooks": {"parts": {"question_contrarienne": 0.31, "promesse_chiffree": 0.2}, "longueur_mots": {"mediane": 28}},
      "mots_par_minute": {"mediane": 150},
      "densite_breakouts": 0.12,
      "sujets_porteurs": [{"sujet": "...", "vues": 1200000, "chaine": "@handle", "video_id": "...", "ratio_vs_mediane": 8.4, "date": "2026-05-02"}]
    }
  },
  "hooks_taxonomie": [{"id": "question_contrarienne", "definition": "...", "exemples": ["...", "..."], "regles": ["≤ 35 mots", "contient une question"]}],
  "regles_trajectoire": [{"id": "T1", "regle": "...", "preuve": "...", "appliquee_par": ["etape_10", "etape_23.2"]}]
}
   Pour rythme_coupe_s : utilise les valeurs du tableau « Contexte figé » agrégées par niche (médiane des chaînes de la niche), jamais une estimation ; si une niche n'a aucune mesure, mets "cible": null et "a_mesurer": true.
   sujets_porteurs : les 10 à 20 vidéos au ratio vues/médiane le plus élevé par niche, avec titre normalisé en sujet.
2. Écris registre/REFERENTIEL.md (150 lignes maximum) : lecture humaine des cibles par niche + « comment le code s'en sert » (étape par étape).
3. Écris registre/TRAJECTOIRES.md : les deux comparaisons, les règles T1…Tn avec preuve, la liste de ce qui n'est pas prouvable.
4. Lance le contradicteur (vague 2), applique ses corrections ou consigne pourquoi tu les refuses dans une section « Objections » de REFERENTIEL.md.
5. Valide le JSON (python -c "import json; json.load(open('registre/REFERENTIEL.json'))") et commit « étape 3 : référentiel ».
</tache>

<contraintes>
- Chaque nombre vient d'un calcul sur registre/data ou du tableau P9 ; indique n (taille d'échantillon) partout, et marque « n faible » sous 20 vidéos.
- Ne lis pas les JSON bruts en session principale : les agents calculent, tu arbitres et tu écris.
- Si une niche a moins de 2 chaînes dans le registre, fusionne-la avec la plus proche et note-le.
</contraintes>

<criteres_de_validation>
Montre : la validation JSON ; python -c pour compter niches, sujets_porteurs par niche (≥ 10), types de hooks (≥ 8) ; grep -c "^| T" registre/TRAJECTOIRES.md (≥ 8) ; la liste des objections du contradicteur et leur traitement.
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 3 terminée, niches retenues, niches sans mesure de rythme (à mesurer plus tard), objections non résolues. Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + INDEX.md | 8 000 |
| Prompt (~1 450 mots) | 2 000 |
| 4 rapports de sous-agents (600 mots chacun) | 6 000 |
| 1 rapport contradicteur | 1 500 |
| Écriture REFERENTIEL.json (≈ 400 lignes) | 5 500 |
| Écriture REFERENTIEL.md (≈ 150 lignes) | 2 000 |
| Écriture TRAJECTOIRES.md (≈ 150 lignes) | 2 000 |
| Corrections après contradicteur | 1 500 |
| Mise à jour STATE.md + résumé | 800 |
| Sous-total | 47 300 |
| Marge +25 % | 11 825 |
| **Total** | **59 125 tk — 29,6 %** |

## Étape 4 — Veille et sélection des outils par brique

**Objectif.** Choisir, brique par brique, un outil principal et un repli, chacun gratuit, local, à licence commerciale vérifiée sur le fichier de licence lui-même, avec poids disque annoncé.
**Pourquoi maintenant.** Les bancs (5.1, 5.2) mesurent ce qui a été sélectionné ; sélectionner après aurait doublé les téléchargements sur un disque de 30 Go.
**Valeur créée.** Thèse n° 5 : une licence non commerciale découverte après publication est un risque juridique sur tout le catalogue.
**Pré-requis.** Étape 3 terminée (les styles et niches visés orientent les briques).
**Sous-agents.** Vague 1, 4 en parallèle : (A) LLM, TTS, ASR ; (B) images, parallaxe, détourage ; (C) composition programmatique, whiteboard, avatar 2D et lip-sync ; (D) musique, SFX, banques vidéo/image, miniatures, outils de mesure du banc. Vague 2 : (E) contradicteur licences qui ouvre le fichier LICENSE ou la fiche modèle de chaque outil retenu.
**Livrables.** `outils/SELECTION.md`, `outils/LICENCES.md`.
**Poids disque.** 0 (aucune installation).
**Terminé quand.** `SELECTION.md` donne pour chacune des 12 briques (LLM, TTS, ASR, image, parallaxe, banques vidéo/image, musique/SFX, composition, whiteboard, avatar 2D, miniatures/détourage, montage/banc) un principal et un repli avec poids disque · `LICENCES.md` liste chaque outil avec licence exacte, usage commercial oui/non, obligations (attribution), URL et date de vérification · aucun outil retenu à licence non commerciale · somme des poids des principaux ≤ 18 Go.

**Prompt à copier-coller :**

````text
Tu es architecte technique spécialiste de l'outillage IA open-source sur Apple Silicon et des licences logicielles.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local, MacBook Air M2 16 Go, ~30 Go de disque libre, pas de CUDA. Les vidéos seront monétisées : tout outil et tout poids de modèle doivent autoriser l'usage commercial, sans exclusion géographique de l'Union européenne. Cette session sélectionne les outils par brique ; les deux sessions suivantes (5.1, 5.2) les mesurent sur la machine. Une erreur de licence ici contamine tout le catalogue ; un outil trop lourd ici gaspille des téléchargements sur un disque presque plein.
La section « 3.5 Synthèse de veille » de ROADMAP.md donne des candidats datés du 13/09/2026 : ce sont des pistes à re-vérifier, pas des décisions.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 4 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 4 \|^## Étape 5\.1 " ROADMAP.md puis Read en offset/limit.
2. STATE.md
3. registre/REFERENTIEL.md (pour savoir quels styles et niches sont visés)
4. docs/CONFORMITE.md — sections 7 et 8 seulement (musique, images).
</demarrage>

<sous_agents>
Vague 1 — 4 sous-agents en parallèle, un seul envoi. Recherche web ; sources primaires exigées (fiche Hugging Face, fichier LICENSE du dépôt, documentation officielle) ; pour toute vitesse, l'URL de la mesure ou la mention « non sourcé ». Format imposé, 450 mots maximum :
  OUTIL | BRIQUE | LICENCE (nom exact ; commercial oui/non ; conditions : attribution, plafond de revenus, territoire) | POIDS Go | RAM min | VITESSE M2 (source) | LANGUES | INSTALL Apple Silicon | PIÈGE PRINCIPAL | URL
puis « Éliminés » (outil → motif exact) et « À mesurer » (ce qui n'a aucune source fiable pour un M2 16 Go).
- Agent A : LLM 4-9B Q4 (Qwen3.5, Gemma 4, alternatives 2026) et runtimes (mlx-lm, llama.cpp, ollama) ; TTS multilingues FR/EN/ES/IT à ≥ 2 voix par langue (Kokoro, Chatterbox Multilingual, Qwen3-TTS, autres 2026) ; ASR avec horodatage des mots (parakeet-mlx, whisper.cpp Core ML, mlx-whisper, WhisperX).
- Agent B : génération d'images (FLUX.2 klein 4B, Z-Image-Turbo, SDXL + LoRA via mflux, Draw Things, ComfyUI MPS), estimation de profondeur pour parallaxe (Depth Anything V2 Small et alternatives), détourage (rembg avec quel modèle, Apple Vision).
- Agent C : moteurs de composition programmatique (Revideo, Motion Canvas, Remotion — lire LICENSE.md, Manim CE, MoviePy v2), whiteboard (vtracer, animation SVG stroke-dashoffset, bibliothèques Python), avatar 2D et lip-sync (Rhubarb Lip Sync, MuseTalk MLX, kits de personnages 2D CC0 comme Open Peeps).
- Agent D : musique et SFX (YouTube Audio Library, Freesound API, Incompetech, Pixabay Music, ACE-Step 1.5, Stable Audio Open Small), banques vidéo/image (Pexels, Pixabay, Openverse, Wikimedia Commons, NASA, Internet Archive : API, clé sans carte, quotas, attribution), miniatures (Playwright, satori/resvg, polices OFL), outils du banc (PySceneDetect, imagehash, ffmpeg ebur128/silencedetect, tesseract).
Vague 2 — après ton brouillon de SELECTION.md, lance 1 contradicteur (Agent E) : pour chaque outil et modèle retenu (principal et repli), ouvrir le fichier de licence réel ou la fiche modèle, citer la clause qui autorise ou interdit l'usage commercial, signaler tout plafond de revenus, toute exclusion territoriale, toute obligation d'attribution, toute dépendance tierce à licence différente (détecteurs de visage, encodeurs de texte, datasets). 450 mots maximum, une ligne par outil : OUTIL | CLAUSE CITÉE | VERDICT | URL.
</sous_agents>

<tache>
Réfléchis avant d'écrire : pour chaque brique, quel critère prime (qualité FR pour la voix, cohérence de style pour l'image, licence pour la composition, poids pour le disque).
1. Écris outils/SELECTION.md : une section par brique (12 briques listées dans ROADMAP.md « Terminé quand ») avec : Principal (outil, version, modèle exact, poids Go, commande d'installation, pourquoi), Repli (idem), Écartés (outil → motif en une ligne), À mesurer en 5.1/5.2 (les incertitudes avec le seuil de décision : ex. « retenu si ≥ 8 tok/s », « retenu si WER < 8 % », « retenu si ≤ 90 s par image 1280×720 »). Termine par le tableau « Budget disque des principaux » (somme ≤ 18 Go) et « Ordre de mesure » pour 5.1 et 5.2.
2. Écris outils/LICENCES.md : tableau exhaustif de tous les outils et modèles cités comme principal ou repli : Outil | Composant (code / poids / dépendance) | Licence exacte | Commercial | Obligations | Territoire | URL | Vérifié le. Ajoute une section « Éliminés pour licence » avec le motif exact, et « Attributions à insérer automatiquement » (texte d'attribution prêt à l'emploi par outil : NVIDIA Parakeet CC-BY-4.0, banques, Audio Library CC).
3. Applique les corrections du contradicteur ; si un principal tombe, le repli monte et tu cherches un nouveau repli (une recherche ciblée, pas une nouvelle vague).
4. Commit « étape 4 : sélection des outils ».
</tache>

<contraintes>
- N'installe rien, ne télécharge rien.
- Remotion n'est acceptable que si Revideo et Motion Canvas sont éliminés par une preuve technique, et alors la clause « 3 personnes » doit être écrite en rouge dans SELECTION.md et STATE.md.
- Un outil sans licence commerciale claire est écarté, même s'il est meilleur.
- Une vitesse non sourcée est marquée « à mesurer », jamais présentée comme acquise.
</contraintes>

<criteres_de_validation>
Montre : grep -c "^## " outils/SELECTION.md (≥ 12) ; grep -ci "non commercial\|CC-BY-NC\|research only" outils/LICENCES.md sur les lignes des outils retenus (doit être 0 hors section « Éliminés ») ; le tableau « Budget disque des principaux » avec sa somme.
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 4 terminée, principaux par brique, éliminations notables, budget disque prévu, seuils de décision pour 5.1 et 5.2. Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + REFERENTIEL.md + CONFORMITE §7-8 | 8 500 |
| Prompt (~1 400 mots) | 2 000 |
| 4 rapports de sous-agents (450 mots) | 5 200 |
| 1 rapport contradicteur | 1 300 |
| Écriture SELECTION.md (≈ 300 lignes) | 4 000 |
| Écriture LICENCES.md (≈ 150 lignes) | 2 000 |
| Corrections | 1 500 |
| Mise à jour STATE.md + résumé | 800 |
| Sous-total | 43 300 |
| Marge +25 % | 10 825 |
| **Total** | **54 125 tk — 27,1 %** |

## Étape 5.1 — Mesurer texte et audio sur le M2 (LLM, TTS, ASR, musique)

**Objectif.** Mesurer sur la machine cible vitesse, pic mémoire, poids disque et qualité des outils texte et audio retenus à l'étape 4, avec des chiffres, pas des suppositions.
**Pourquoi maintenant.** Le script, la voix et les sous-titres sont les briques les plus utilisées du pipeline ; leur débit réel dimensionne tout le reste.
**Valeur créée.** Élimine le risque de bâtir sur un outil qui ne tient pas en mémoire ou qui produit une voix française inutilisable (risque 5 de la section 9).
**Pré-requis.** Étape 4 terminée · `outils/SELECTION.md` · ≥ 25 Go libres au départ.
**Sous-agents.** 2 en parallèle — (A) procédure d'installation Apple Silicon exacte et poids disque de chaque outil texte/audio retenu ; (B) pièges MLX / MPS connus pour ces outils (opérations non supportées, fuites mémoire, contournements). 400 mots maximum chacun.
**Livrables.** `benchmarks/bench_audio.sh`, `benchmarks/bench_audio.py`, `benchmarks/RESULTATS.md` (§1), `benchmarks/samples/audio/`, `outils/MODELES.md` mis à jour.
**Poids disque.** ≈ 12 Go en pic (LLM ~5 Go, TTS ~2-6 Go, ASR ~2,5 Go, musique ~3 Go) ; ≈ 10 Go conservés après purge.
**Terminé quand.** `RESULTATS.md` §1 contient pour chaque outil : temps mesuré, facteur temps réel, pic mémoire, poids disque, WER (pour TTS et ASR), qualité /5 (humaine ou « non évaluée »), verdict go/no-go · un outil « go » par brique · le TTS retenu offre ≥ 2 voix en FR, EN, ES, IT (ou l'écart est documenté) · disque libre ≥ 12 Go à la fin.

**Prompt à copier-coller :**

````text
Tu es ingénieur performance, spécialiste de l'inférence de modèles IA sur Apple Silicon (MLX, Metal, MPS).

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local. Machine : MacBook Air M2, 16 Go unifiés, ~30 Go de disque libre, macOS 27, pas de CUDA. Cette session mesure les briques texte et audio sélectionnées à l'étape 4 : LLM d'écriture, synthèse vocale multilingue (FR, EN, ES, IT), reconnaissance vocale avec horodatage des mots, génération musicale. Les résultats fixent l'architecture : une mesure fausse ici coûte des semaines. La qualité perçue de la voix française est un risque identifié du projet : mesure-la avec soin.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 5.1 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 5\.1 \|^## Étape 5\.2 " ROADMAP.md puis Read en offset/limit.
2. STATE.md
3. outils/SELECTION.md — briques LLM, TTS, ASR, musique et la section « Ordre de mesure ».
4. outils/MODELES.md
</demarrage>

<sous_agents>
Lance 2 sous-agents en parallèle, un seul envoi :
- Agent A : pour chaque outil texte/audio de SELECTION.md (principal et repli) — commandes d'installation officielles sur Apple Silicon avec Python 3.12 via uv, identifiant exact du modèle à télécharger (dépôt Hugging Face ou nom ollama), poids disque exact, variable d'environnement de cache, commande minimale de génération en ligne de commande ou en 5 lignes de Python.
- Agent B : pièges connus des 12 derniers mois pour ces outils sur MLX/MPS (opérations non supportées, retombée en CPU, fuites mémoire, réglage PYTORCH_MPS_HIGH_WATERMARK_RATIO, versions de torch à éviter) et leurs contournements.
Format imposé, 400 mots maximum : OUTIL | COMMANDES | MODÈLE ET POIDS | PIÈGE | CONTOURNEMENT | URL.
</sous_agents>

<tache>
1. Avant tout téléchargement : df -h / ; note la valeur dans STATE.md. Exporte HF_HOME=$PWD/models/hf et, si ollama est utilisé, OLLAMA_MODELS=$PWD/models/ollama. Crée un environnement unique : uv venv --python 3.12 .venv ; installe les outils dedans (uv pip install …), sortie redirigée vers benchmarks/install_audio.log, tail -20 seulement.
2. Écris benchmarks/bench_audio.py (appelé par bench_audio.sh) qui, pour chaque outil, exécute un échantillon standard identique et mesure le temps écoulé et le pic mémoire (/usr/bin/time -l, champ « maximum resident set size ») :
   - LLM : prompt fixe « Écris un script de 600 mots pour une vidéo YouTube sur <sujet issu de registre/REFERENTIEL.json, premier sujet porteur de science_pop>, en français, avec un hook de 2 phrases », contexte 8 k ; mesure tokens/s de génération et de traitement du prompt, temps total, pic mémoire ; répète en anglais. Teste le principal et, si < 8 tok/s ou échec, le repli.
   - TTS : le même paragraphe de 120 mots dans les 4 langues (écris-le en FR, fais-le traduire par le LLM en EN, ES, IT, garde les 4 textes dans benchmarks/samples/audio/texte_<lang>.txt), avec 2 voix par langue quand l'outil en offre ; mesure le facteur temps réel (durée audio / temps de calcul), le pic mémoire, produit benchmarks/samples/audio/<outil>_<lang>_<voix>.wav.
   - ASR : transcris chaque WAV produit avec chaque ASR retenu ; mesure le temps, vérifie la présence d'horodatages au mot ; calcule le WER entre la transcription et le texte source (implémente un WER simple, normalisation minuscules/ponctuation). Le WER sert à la fois de note d'intelligibilité de la voix et de précision de l'ASR : un WER > 8 % sur le TTS principal est un signal d'alerte à consigner.
   - Musique (si un générateur est retenu et si le disque le permet, sinon « non mesuré ») : 30 s d'ambiance « documentaire calme », temps et pic mémoire ; sinon documente le chemin Audio Library.
   Exécute chaque outil dans un processus séparé (un modèle résident à la fois). Redirige tout dans benchmarks/bench_audio.log ; affiche tail -20 après chaque outil.
3. Qualité humaine : demande à Thomas d'écouter les échantillons TTS (chemins listés) et de noter chaque voix de 1 à 5 sur naturel et accent ; s'il n'est pas disponible pendant la session, écris « non évaluée » et laisse la consigne dans STATE.md. Ne note jamais toi-même une qualité sonore que tu ne peux pas entendre.
4. Consigne benchmarks/RESULTATS.md § 1 « Texte et audio » : tableau | Outil | Brique | Modèle | Temps | RTF ou tok/s | Pic mémoire | Disque | WER | Qualité /5 | Verdict | puis un paragraphe de recommandation par brique avec le seuil de décision de SELECTION.md appliqué.
5. Purge : supprime les poids des outils no-go (rm dans models/ ; uv pip uninstall si volumineux), mets à jour outils/MODELES.md (statut, Go, cumul), vérifie df -h /.
6. Commit « étape 5.1 : bench texte et audio » (samples WAV hors git si > 5 Mo au total : ajoute benchmarks/samples/ au .gitignore).
</tache>

<contraintes>
- Vérifie l'espace disque avant chaque téléchargement ; ne descends jamais sous 8 Go libres : si un téléchargement ferait passer sous ce seuil, purge d'abord un no-go ou marque l'outil « non mesuré : disque ».
- Si un outil échoue après deux tentatives, note « no-go » avec le message d'erreur exact et passe au suivant ; ne le répare pas.
- Chiffres mesurés uniquement ; « non mesuré » plutôt qu'une estimation.
- Ne lis jamais un log en entier : tail, grep.
</contraintes>

<criteres_de_validation>
Montre : le tableau de RESULTATS.md §1 ; ls benchmarks/samples/audio | wc -l (≥ 8 WAV) ; la sortie de df -h / ; le cumul de outils/MODELES.md.
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 5.1 terminée, outils go par brique avec leurs chiffres clés, no-go et motifs, voix disponibles par langue, disque libre, question ouverte pour 5.2. Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + SELECTION (briques concernées) + MODELES | 9 000 |
| Prompt (~1 550 mots) | 2 200 |
| 2 rapports de sous-agents | 2 400 |
| Écriture bench_audio.sh + bench_audio.py (≈ 250 lignes) | 3 500 |
| Installations et exécutions (extraits tail -20, ~10 outils × 800) | 8 000 |
| Corrections et relances | 4 000 |
| Calculs WER et lectures ciblées | 1 000 |
| Écriture RESULTATS.md §1 (≈ 150 lignes) | 2 000 |
| Mise à jour MODELES.md + STATE.md + résumé | 1 200 |
| Sous-total | 51 300 |
| Marge +25 % | 12 825 |
| **Total** | **64 125 tk — 32,1 %** |

## Étape 5.2 — Mesurer image, parallaxe, composition et une preuve vidéo IA conditionnelle

**Objectif.** Mesurer sur le M2 la génération d'images, la parallaxe 2.5D, le rendu de composition programmatique, la vectorisation whiteboard, le lip-sync 2D et les miniatures ; produire, si le disque le permet, une preuve locale de la génération vidéo IA pour l'étape 6.
**Pourquoi maintenant.** L'arbitrage des styles (étape 6) doit s'appuyer sur des rendus mesurés, pas sur des benchmarks d'autres machines.
**Valeur créée.** Preuves visuelles pour la réponse à Alek ; élimination des moteurs qui ne tiennent pas.
**Pré-requis.** Étape 5.1 terminée (échantillon WAV pour Rhubarb) · `outils/SELECTION.md` · disque libre connu.
**Sous-agents.** 2 en parallèle — (A) procédure d'installation Apple Silicon et poids exacts des outils visuels retenus (mflux, Depth Anything Small, Revideo, vtracer, Rhubarb, Playwright/satori) ; (B) pièges MPS/Metal et paramètres mémoire pour la génération d'images et de vidéo sur 16 Go. 400 mots maximum chacun.
**Livrables.** `benchmarks/bench_visuel.sh`, `benchmarks/bench_visuel.py`, `benchmarks/RESULTATS.md` (§2), `benchmarks/samples/visuel/`, `outils/MODELES.md` mis à jour.
**Poids disque.** ≈ 6 Go conservés (image 4,6 + profondeur 0,1 + Rhubarb + Playwright/Chromium ~0,5) ; +8 à 10 Go temporaires si la preuve vidéo IA est tentée, purgés dans la session ; Revideo et Chromium purgés en fin de session (réinstallés à l'étape 30.1).
**Terminé quand.** `RESULTATS.md` §2 contient, mesurés : secondes par image à 1280×720 et 1024×1024, pic mémoire, secondes par clip de parallaxe, images par seconde du rendu Revideo à 1080p, temps de vectorisation, temps Rhubarb, temps de rendu d'une miniature ; verdict par brique ; preuve vidéo IA produite ou motif « non tentée : disque < 18 Go » avec la source citée · échantillons dans `benchmarks/samples/visuel/` · disque libre ≥ 10 Go.

**Prompt à copier-coller :**

````text
Tu es ingénieur performance, spécialiste des modèles de diffusion et du rendu vidéo sur Apple Silicon.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local, MacBook Air M2 16 Go, disque presque plein. Cette session mesure les briques visuelles : génération d'images, profondeur et parallaxe, composition programmatique, whiteboard, lip-sync 2D, miniatures. Elle produit aussi, si et seulement si le disque le permet, une courte preuve de génération vidéo IA locale : l'étape 6 s'en servira pour expliquer à Alek pourquoi le photoréalisme généré n'est pas la voie. Les benchmarks publics concernent d'autres puces : seule la mesure sur cette machine compte.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 5.2 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 5\.2 \|^## Étape 6 " ROADMAP.md puis Read en offset/limit.
2. STATE.md
3. outils/SELECTION.md — briques image, parallaxe, composition, whiteboard, avatar 2D, miniatures.
4. outils/MODELES.md
</demarrage>

<sous_agents>
Lance 2 sous-agents en parallèle, un seul envoi, 400 mots maximum chacun, format OUTIL | COMMANDES | MODÈLE ET POIDS | PIÈGE | CONTOURNEMENT | URL :
- Agent A : installation Apple Silicon (Python 3.12 via uv, Node pour Revideo) et poids exacts : mflux avec le modèle image retenu en 4-bit, Depth Anything V2 Small via transformers sur MPS, Revideo (création de projet, commande de rendu sans interface), vtracer, Rhubarb Lip Sync (binaire macOS), Playwright Chromium ou satori/resvg ; et, pour la preuve vidéo IA : la plus petite variante de LTX-Video ou de Wan 2.1 qui tourne sur MPS en 512×288, son poids total encodeur de texte compris, la commande diffusers minimale.
- Agent B : pièges MPS/Metal pour ces outils sur 16 Go (quantification, PYTORCH_MPS_HIGH_WATERMARK_RATIO, swap, plantages FP8, NaN au décodage VAE) et réglages recommandés.
</sous_agents>

<tache>
1. df -h / avant tout. Règle de décision de la preuve vidéo IA : si le disque libre est ≥ 18 Go, tente-la EN PREMIER (avant d'installer les autres briques), une seule variante, 512×288, 4 secondes, 20 minutes de calcul maximum (timeout), puis purge immédiatement ses poids et note le temps, le pic mémoire et le résultat (chemin du MP4 ou échec exact). Si le disque est < 18 Go, n'essaie pas : écris « non tentée : disque » et reprends dans RESULTATS.md les chiffres publics cités dans ROADMAP.md 3.5 avec leurs URL.
2. Installe les briques dans .venv (uv pip install …), sortie vers benchmarks/install_visuel.log, tail -20.
3. Écris benchmarks/bench_visuel.py (appelé par bench_visuel.sh) qui mesure, un processus par outil :
   - Images : 5 prompts fixes couvrant les styles visés (illustration cartoon plate, illustration détaillée style documentaire, photo réaliste d'un lieu, dessin au trait noir sur blanc type whiteboard, fond abstrait motion design), chacun en 1280×720 et 1024×1024, 4 étapes pour un modèle turbo (sinon le nombre recommandé), graine fixe ; mesure secondes par image et pic mémoire ; sauvegarde dans benchmarks/samples/visuel/img_<style>_<res>.png. Mesure aussi la cohérence : 3 images du même personnage décrit à l'identique avec 3 graines ; garde-les.
   - Parallaxe : carte de profondeur (Depth Anything V2 Small) sur 3 images, temps ; puis un clip de 5 s à 1080p30 par déplacement de couches (script simple : 3 couches seuillées sur la profondeur, décalage différencié, ffmpeg overlay) et un clip Ken Burns (ffmpeg zoompan suréchantillonné ×4) ; temps par clip.
   - Composition : projet Revideo minimal (une scène « texte animé sur fond » de 10 s à 1080p30), rendu sans interface ; mesure les images par seconde de rendu, le temps total, la taille de node_modules et de Chromium.
   - Whiteboard : vtracer sur l'image « dessin au trait » → SVG (nombre de chemins) ; animation stroke-dashoffset rendue en 5 s via Revideo ou via une page HTML capturée par Playwright ; temps.
   - Lip-sync 2D : Rhubarb sur benchmarks/samples/audio/<meilleur TTS>_fr_*.wav → JSON de visèmes ; temps ; teste le mode phonetic pour le français.
   - Miniature : une composition 1280×720 (image de fond + 3 mots en gros + bandeau) rendue via l'outil retenu ; temps.
   Tout dans benchmarks/bench_visuel.log, tail -20 après chaque brique.
4. Regarde avec l'outil Read au plus 5 fichiers : les 5 images de styles en 1280×720. Note chaque style de 1 à 5 sur : fidélité au style demandé, absence d'artefacts, exploitabilité en vidéo. Pour les clips, n'ouvre pas les vidéos : extrais une image médiane avec ffmpeg et regarde-la seulement si le verdict en dépend (2 images maximum).
5. Écris benchmarks/RESULTATS.md § 2 « Visuel » : tableau | Outil | Brique | Temps | Pic mémoire | Disque | Qualité /5 | Verdict | ; sous-section « Preuve vidéo IA » ; sous-section « Coût par minute de vidéo » estimée à partir des mesures (ex. 12 images par minute de vidéo × secondes par image) pour chaque style ; recommandation par brique avec les seuils de SELECTION.md.
6. Purge : poids de la preuve vidéo (déjà fait), outils no-go, projet Revideo de test et Chromium (rm -rf benchmarks/revideo_test node_modules ; npx playwright uninstall si installé pour le test) ; mets à jour outils/MODELES.md ; df -h /.
7. Commit « étape 5.2 : bench visuel ».
</tache>

<contraintes>
- Jamais sous 8 Go libres. Un seul modèle lourd en mémoire à la fois.
- Deux tentatives maximum par outil, puis no-go avec l'erreur exacte.
- Regarde au plus 7 images dans toute la session : chaque image coûte du contexte.
- Chiffres mesurés uniquement.
</contraintes>

<criteres_de_validation>
Montre : le tableau de RESULTATS.md §2 ; ls benchmarks/samples/visuel ; df -h / ; le cumul de MODELES.md ; le statut de la preuve vidéo IA.
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 5.2 terminée, verdicts par brique, coût mesuré par minute de vidéo par style, preuve vidéo IA, disque libre. Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + SELECTION (briques visuelles) + MODELES | 9 000 |
| Prompt (~1 750 mots) | 2 500 |
| 2 rapports de sous-agents | 2 400 |
| Écriture bench_visuel.sh + bench_visuel.py + projet Revideo minimal (≈ 300 lignes) | 4 000 |
| Installations et exécutions (extraits) | 6 000 |
| Inspection de 5 images (≈ 1 500 chacune) | 7 500 |
| Corrections et relances | 4 000 |
| Écriture RESULTATS.md §2 (≈ 150 lignes) | 2 000 |
| Mise à jour MODELES.md + STATE.md + résumé | 1 200 |
| Sous-total | 56 600 |
| Marge +25 % | 14 150 |
| **Total** | **70 750 tk — 35,4 %** |

## Étape 6 — Trancher les styles et la réponse à Alek

**Objectif.** Décider, style par style, ce qui est tenable en local et à quel niveau, ce qui attend le serveur, ce qui est abandonné ; écrire la réponse à Alek sur le réalisme.
**Pourquoi maintenant.** L'architecture (étape 8) et l'ordre des moteurs de style dépendent de ce verdict ; Alek attend une position claire sur Higgsfield.
**Valeur créée.** Thèse n° 5 et n° 6 : une promesse intenable coûte la confiance du client ; une décision documentée devient un argument de vente de l'actif.
**Pré-requis.** Étapes 5.1 et 5.2 terminées · `benchmarks/RESULTATS.md` · `registre/REFERENTIEL.md`.
**Sous-agents.** 1 contradicteur (vague 2) : attaque la matrice (notes de qualité complaisantes, coûts par minute mal calculés, styles surestimés, promesses implicites).
**Livrables.** `docs/STYLES.md`.
**Poids disque.** 0.
**Terminé quand.** `STYLES.md` contient la matrice des 7 styles avec statut (retenu v1 / retenu v2 / serveur seulement / abandonné), chaîne d'outils, qualité mesurée /5, coût mesuré par minute de vidéo, chemin d'une preuve visuelle · la section « Message à Alek » (≤ 20 lignes) existe · l'ordre d'implémentation des moteurs est fixé · objections du contradicteur traitées.

**Prompt à copier-coller :**

````text
Tu es directeur de production média et architecte technique ; tu tranches avec des preuves et tu sais dire non à un client.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local. Alek a demandé sept styles (whiteboard animé, motion design, images cartoon, animations poussées, vidéos réalistes, documentaire, avatar parlant) et a exigé « le niveau des vidéos du PDF de Sofiane ». Thomas lui a déjà écrit que le réalisme ne sera jamais au niveau de Higgsfield : c'est exact, et les mesures des étapes 5.1 et 5.2 le prouvent. Cette session tranche chaque style avec les chiffres mesurés et rédige la réponse à Alek. Les chaînes les plus performantes du registre (CasiCreativo, réseaux Thoth) ne font pas de photoréalisme : elles font du motion design, des images et de la voix off. C'est l'argument central.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 6 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 6 \|^## Étape 7 " ROADMAP.md puis Read en offset/limit.
2. STATE.md
3. benchmarks/RESULTATS.md (entier)
4. registre/REFERENTIEL.md — uniquement les parties sur les formats et la direction artistique des chaînes qui performent.
5. outils/SELECTION.md — uniquement les sections composition, whiteboard, avatar 2D, image.
</demarrage>

<sous_agents>
Après ton brouillon de docs/STYLES.md, lance 1 contradicteur : il lit STYLES.md et RESULTATS.md et cherche les notes de qualité non justifiées par un échantillon, les coûts par minute incohérents avec les mesures, les styles marqués « retenu » sans preuve visuelle, les promesses implicites à Alek qui ne tiendront pas à l'échelle (10 vidéos/semaine), et ce qu'un spectateur remarquerait en 5 secondes. 400 mots maximum, liste « Problème → correction ».
</sous_agents>

<tache>
Réfléchis avant d'écrire : pour chaque style, quel est le meilleur rapport entre qualité perçue, coût par minute mesuré et risque de conformité (« contenu inauthentique » vise les diaporamas génériques : un style doit permettre la variation).
1. Regarde au plus 3 échantillons de benchmarks/samples/visuel (les meilleurs par style, d'après RESULTATS.md) pour asseoir ton jugement.
2. Écris docs/STYLES.md :
   - Matrice : | Style demandé | Chaîne d'outils locale | Qualité mesurée /5 | Coût mesuré (minutes de calcul par minute de vidéo) | Poids disque | Preuve (chemin) | Ce que seul un serveur GPU ajouterait | Statut |. Statuts possibles : retenu v1 (phase 1), retenu v2 (phases 2 ou 6), serveur seulement, abandonné. Le style « réaliste » se décompose en « réaliste par banques de vidéos libres » (documentaire) et « réaliste généré » (serveur seulement, et même alors en b-roll de quelques secondes).
   - « Ce que fait le registre » : formats des chaînes qui performent (CasiCreativo, Thoth, Elias Yoder) et ce qu'ils impliquent.
   - « Ordre d'implémentation des moteurs » : cartes (12.1), illustré (12.2), documentaire (17), avatar 2D (29), motion design (30.1), whiteboard (30.2) — ajuste si les mesures l'imposent et explique.
   - « Message à Alek » (20 lignes maximum, en français, ton factuel, sans jargon) : ce que le système fait en local et à quel niveau, ce que le photoréalisme généré coûte réellement (chiffres de la preuve locale et des sources), pourquoi les chaînes qui gagnent n'en ont pas besoin, ce que le serveur à 50 €/mois débloquera et ne débloquera pas, et la proposition : lancer avec motion design, illustré et documentaire, ajouter l'avatar 2D et le whiteboard, garder le réalisme généré comme option b-roll sur serveur.
   - « Risques de conformité par style » (variation possible, signature humaine).
3. Lance le contradicteur, corrige, consigne les objections refusées dans une section « Objections ».
4. Commit « étape 6 : styles tranchés ».
</tache>

<contraintes>
- Aucune note de qualité sans échantillon ou mesure derrière ; « non mesuré » sinon.
- Le message à Alek ne promet rien qui ne soit pas dans la matrice avec statut « retenu ».
- N'installe rien.
</contraintes>

<criteres_de_validation>
Montre : la matrice complète (7 lignes ou plus) ; le message à Alek ; wc -l docs/STYLES.md ; les objections traitées.
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 6 terminée, statuts des styles, ordre des moteurs, message à Alek prêt à envoyer (Thomas décide de l'envoi), questions ouvertes. Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + RESULTATS.md (≈ 300 lignes) + extraits REFERENTIEL/SELECTION | 10 000 |
| Prompt (~1 150 mots) | 1 600 |
| Inspection de 3 échantillons | 4 500 |
| 1 rapport contradicteur | 1 200 |
| Écriture STYLES.md (≈ 250 lignes) | 3 300 |
| Corrections | 1 500 |
| Mise à jour STATE.md + résumé | 800 |
| Sous-total | 40 900 |
| Marge +25 % | 10 225 |
| **Total** | **51 125 tk — 25,6 %** |

## Étape 7 — Installer et figer l'environnement

**Objectif.** Figer l'environnement retenu (versions épinglées, caches redirigés, ledger disque à jour) et livrer `factory doctor`, la commande qui prouve en 2 minutes que toutes les briques répondent.
**Pourquoi maintenant.** Toutes les sessions de code qui suivent démarrent par `factory doctor` ; sans lui, chaque session redécouvre les mêmes pannes.
**Valeur créée.** Thèse n° 6 : un environnement reproductible est la première condition de transmission de l'actif.
**Pré-requis.** Étape 6 terminée · `outils/SELECTION.md`, `benchmarks/RESULTATS.md`, `docs/STYLES.md`.
**Sous-agents.** Aucun.
**Livrables.** `pyproject.toml`, `uv.lock`, `factory/__init__.py`, `factory/cli.py`, `factory/doctor.py`, `docs/INSTALL.md`, `outils/MODELES.md` à jour, `.env.example` complété.
**Poids disque.** ≈ 0,5 Go (dépendances Python) ; modèles déjà présents.
**Terminé quand.** `uv run factory doctor` retourne 0 avec un tableau où chaque brique retenue est PASS (LLM, TTS, ASR, image, profondeur, Rhubarb, ffmpeg/ffprobe, disque ≥ 8 Go) · `docs/INSTALL.md` permet une installation depuis zéro en moins de 30 minutes hors téléchargements · `git status` propre.

**Prompt à copier-coller :**

````text
Tu es ingénieur plateforme ; tu figes des environnements Python/Node reproductibles sur macOS Apple Silicon.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local, MacBook Air M2 16 Go. Les étapes précédentes ont mesuré et retenu les outils (benchmarks/RESULTATS.md, docs/STYLES.md). Cette session fige l'environnement dans un projet Python géré par uv, crée le squelette du paquet `factory` et sa commande `factory doctor`, qui vérifie chaque brique par un test de fumée. Toutes les sessions suivantes commencent par cette commande.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 7 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 7 \|^## Phase 1 " ROADMAP.md puis Read en offset/limit.
2. STATE.md
3. outils/SELECTION.md — sections des briques retenues (principal) uniquement.
4. benchmarks/RESULTATS.md — colonnes « Verdict » et commandes utilisées (grep -n "go\|Commande" suffit).
5. outils/MODELES.md
</demarrage>

<tache>
1. Écris pyproject.toml (nom : factory, Python ≥ 3.12, script console `factory = "factory.cli:app"`), dépendances épinglées aux versions installées en 5.1/5.2 (uv pip freeze | grep pour les retrouver) : les runtimes retenus (mlx-lm, mlx-audio ou équivalents, parakeet-mlx ou whisper, mflux, transformers/torch pour la profondeur, google-api-python-client, google-auth-oauthlib), pydantic ≥ 2, typer, pyyaml, rich, python-dotenv, pillow, scenedetect, imagehash, requests, pytest. Puis uv sync (sortie vers workspace/logs/install_7.log, tail -20). Reconstruis .venv proprement si nécessaire.
2. Écris factory/__init__.py, factory/cli.py (typer : commandes `doctor`, `version`) et factory/doctor.py : chaque contrôle retourne PASS/FAIL avec un message court et un temps :
   - python ≥ 3.12 ; ffmpeg et ffprobe présents (version) ; disque libre ≥ 8 Go ; variables d'environnement HF_HOME/OLLAMA_MODELS pointant dans models/ ; chaque modèle listé « retenu » dans outils/MODELES.md présent sur disque ;
   - LLM : génère 20 tokens (temps) ; TTS : synthétise « Bonjour, ceci est un test. » en FR et « Hello, this is a test. » en EN dans workspace/logs/doctor_tts_<lang>.wav (durée > 0,5 s via ffprobe) ; ASR : transcrit le WAV FR et vérifie que « test » apparaît ; image : génère une image 512×512 en 1 étape ou le minimum du modèle (temps) ; profondeur : carte de profondeur de cette image ; Rhubarb : binaire exécutable (--version) ;
   - chaque test s'exécute dans un sous-processus séparé (un modèle en mémoire à la fois) avec timeout de 180 s.
   Sortie : tableau rich + code de retour 0 si tout PASS, 1 sinon. Option --quick pour sauter les tests de génération.
3. Exécute uv run factory doctor ; corrige jusqu'au PASS complet. Deux échecs consécutifs d'une même brique → note-le dans STATE.md comme bloquant, n'insiste pas.
4. Écris docs/INSTALL.md : prérequis (Homebrew, uv, ffmpeg, Node), clonage, uv sync, variables d'environnement (.env.example complété), téléchargement des modèles (commandes exactes, poids, ordre), Rhubarb, `factory doctor`, dépannage des 5 pannes rencontrées pendant cette session.
5. Mets à jour outils/MODELES.md (cumul retenu) ; .gitignore (uv.lock est committé) ; commit « étape 7 : environnement figé ».
</tache>

<contraintes>
- Un seul environnement (.venv à la racine) ; pas d'installation globale hors brew et uv tool.
- Redirige les sorties d'installation vers des logs ; tail -20.
- Aucun nouveau modèle : si un test exige un modèle absent, c'est un FAIL à corriger avec les modèles retenus, pas un téléchargement.
</contraintes>

<criteres_de_validation>
Montre : la sortie complète de uv run factory doctor (tout PASS, code 0 : echo $?) ; wc -l docs/INSTALL.md ; git status (propre après commit) ; df -h /.
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 7 terminée, phase 0 close (jalon vérifié : doctor 0, STYLES tranché, REFERENTIEL valide, disque libre), versions figées, pannes rencontrées. Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + SELECTION (retenus) + extraits RESULTATS + MODELES | 9 000 |
| Prompt (~1 200 mots) | 1 700 |
| Écriture pyproject + cli.py + doctor.py (≈ 350 lignes) | 4 700 |
| Installation (extraits de logs) | 5 000 |
| Exécutions de doctor et corrections | 5 000 |
| Écriture INSTALL.md (≈ 120 lignes) | 1 600 |
| Mise à jour MODELES.md + STATE.md + résumé | 1 200 |
| Sous-total | 46 200 |
| Marge +25 % | 11 550 |
| **Total** | **57 750 tk — 28,9 %** |

## Phase 1 — Pipeline v1 et première vidéo

**Objectif de la phase.** Bâtir le pipeline de bout en bout (sujet → recherche → script → voix → sous-titres → plans → assets → montage → miniature → métadonnées → export), avec un modèle de données versionné, un premier moteur de style, un manifeste de run qui trace chaque décision, et ouvrir le canal officiel de publication.
**Jalon de phase.** `uv run factory run --channel bms-science-fr` produit deux fois de suite, sans intervention, `workspace/runs/<id>/final.mp4` (1080p30, durée à ±15 % de la cible de niche, voix normalisée, sous-titres, `thumbnail.png`, `metadata.json`, `manifest.json` avec timings et coût) · une vidéo est uploadée en privé sur la chaîne de test via l'API · le dossier d'audit est déposé.

## Étape 8 — Architecture et contrats d'interface

**Objectif.** Écrire `docs/ARCHITECTURE.md` et `docs/INTERFACES.md` : le DAG des étapes, le contrat de chaque fichier intermédiaire, l'interface des moteurs de style, le manifeste de run, les commandes, les règles mémoire et disque.
**Pourquoi maintenant.** Tout le code des étapes 9 à 31 implémente ces contrats ; les écrire après le code, c'est les réécrire trois fois.
**Valeur créée.** Thèse n° 2 (le manifeste rend la boucle de rétroaction possible), n° 4 (multi-chaînes et multi-langues par construction), n° 6 (un tiers peut comprendre le système sans lire le code).
**Pré-requis.** Phase 0 close · `docs/CONFORMITE.md`, `docs/STYLES.md`, `registre/REFERENTIEL.md`, `outils/SELECTION.md`, `benchmarks/RESULTATS.md`.
**Sous-agents.** 1 contradicteur (vague 2) : couplages cachés, cohabitation mémoire, fuites entre langues, ce qui casse à 50 vidéos par semaine, ce que la boucle de rétroaction ne pourra pas joindre.
**Livrables.** `docs/ARCHITECTURE.md`, `docs/INTERFACES.md`.
**Poids disque.** 0.
**Terminé quand.** `INTERFACES.md` donne un exemple JSON ou YAML pour chacun des ≥ 10 fichiers intermédiaires et pour `config/channels/<id>.yaml` · l'interface `StyleEngine` est écrite en signature Python · le manifeste liste tous les champs exigés par `CONFORMITE.md` §10 et par la boucle de rétroaction · une section « Objections et réponses » traite chaque point du contradicteur.

**Prompt à copier-coller :**

````text
Tu es architecte logiciel senior ; tu conçois des pipelines de données déterministes, reproductibles et pilotés par configuration.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local, MacBook Air M2 16 Go (un seul modèle IA résident à la fois). Le système doit être multi-chaînes, multi-langues et multi-styles par configuration, tracer chaque décision de production dans un manifeste pour que la phase 5 puisse relier les résultats YouTube (rétention, CTR, vues) aux choix faits (sujet, hook, titre, miniature, rythme, style, langue), respecter docs/CONFORMITE.md, et rester compréhensible par un développeur tiers. Cette session écrit les contrats que toutes les sessions de code suivantes implémenteront. Réfléchis longuement avant d'écrire : c'est l'étape la plus structurante du projet.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé », « ## 4. Vue d'ensemble du pipeline » et « ## Étape 8 » : grep -n "^## 3\. Contexte figé\|^## 5\.\|^## Étape 8 \|^## Étape 9 " ROADMAP.md puis Read en offset/limit.
2. STATE.md
3. docs/CONFORMITE.md (entier : les sections 3, 4, 5, 10 et 11 dictent des champs et des étapes)
4. docs/STYLES.md (entier)
5. registre/REFERENTIEL.md (entier)
6. outils/SELECTION.md — uniquement le tableau des principaux ; benchmarks/RESULTATS.md — uniquement les verdicts et le coût par minute de vidéo.
</demarrage>

<sous_agents>
Après ton brouillon des deux documents, lance 1 contradicteur qui les lit avec les étapes 9 à 27 de ROADMAP.md (descriptions courtes, pas les prompts) et cherche : un fichier intermédiaire dont le contrat ne permet pas l'étape qui le consomme ; deux étapes qui chargeraient deux modèles en même temps ; une information de langue ou de chaîne qui pourrait fuir d'un run à l'autre ; un champ de résultat (rétention, CTR) impossible à joindre au manifeste ; ce qui casse à 50 runs par semaine (disque, base, logs) ; ce qu'un développeur tiers ne comprendrait pas. 450 mots maximum, liste numérotée « Problème → correction ».
</sous_agents>

<tache>
1. Écris docs/ARCHITECTURE.md (≈ 250 lignes) :
   - Principes : tout est fichier sur disque ; une étape = une fonction pure (entrées : fichiers du run + config ; sortie : fichiers du run + entrée dans manifest) idempotente, avec marqueur `<etape>.done` ; un sous-processus par étape qui charge un modèle (un modèle résident à la fois, déchargement garanti à la sortie) ; une vidéo à la fois ; graine déterministe par run ; `schema_version` dans chaque fichier ; configuration YAML validée ; secrets hors dépôt (.env, secrets/) ; SQLite unique workspace/factory.db pour l'index des runs, la file, l'éditorial et l'analytique (les fichiers restent la source de vérité des runs, la base est un index reconstructible).
   - DAG : plan → research → script → review (humain, par lots) → voice → subtitles → shotlist → assets → render → assemble → thumbnail → metadata → qc → export → publish → measure → learn ; pour chaque nœud : entrées, sorties, modèle chargé, temps mesuré attendu (RESULTATS.md), reprise possible.
   - Disposition d'un run : workspace/runs/<video_id>/ avec spec.json, research.json, script.json, review.json, voice/segment_XX.wav, voice/voice.wav, voice/timings.json, subtitles.srt, subtitles.ass, words.json, shotlist.json, assets/<shot>/… + licence.json, clips/shot_XX.mp4, video_nomusic.mp4, final.mp4, thumbnail.png, thumbnails/variant_X.png, metadata.json, qc.json, publish.json, manifest.json, events.jsonl.
   - Identifiants : video_id = <chaîne>-<AAAAMMJJ>-<4 caractères aléatoires> ; un run enfant (déclinaison multilingue) porte parent_id.
   - Bibliothèque partagée workspace/library/ (images, stock, musique, sfx, personnages, intros) avec index dans factory.db et licence.json par asset ; règles de réutilisation et d'anti-répétition par chaîne.
   - Moteurs de style : interface StyleEngine, deux backends (ffmpeg natif ; Revideo), sélection par channel.style, templates en rotation (≥ 3 par chaîne, CONFORMITE §5), charte par chaîne (polices, palette, transitions, position des textes).
   - Multi-langues : la langue est une propriété de la chaîne et du run ; le script est produit directement dans la langue de la chaîne ; la déclinaison crée un run enfant qui réutilise les assets visuels et régénère texte, voix, sous-titres, titres, miniature (adaptation, pas clonage).
   - Journal : events.jsonl par run + workspace/logs/factory.log tournant ; niveaux ; ce qui est loggé.
   - Mémoire et disque : règles concrètes (plancher 8 Go, purge des clips intermédiaires après export réussi sauf assets réutilisables, taille max d'un run).
   - Ce qui n'est PAS dans l'architecture (automatisation navigateur, scraping, exécution parallèle).
2. Écris docs/INTERFACES.md (≈ 450 lignes) : pour chaque fichier intermédiaire, le contrat (champs, types, valeurs permises) et un exemple JSON court. En particulier :
   - spec.json : channel_id, lang, niche, style, topic {sujet, angle, source (topics_queue | referentiel | manuel), evidence}, target_duration_s, cut_rhythm_target_s, seed, product_id (optionnel), created_at.
   - script.json : hook {type, text}, segments[] {id, role (hook | contexte | point | rupture | sponsor | cta | conclusion), narration, on_screen_text, visual_intent, open_loop {plant | payoff | none}, interrupt (optionnel), sources[]}, editorial_signature {angle, elements_proprietaires[]}, word_count, estimated_duration_s, lang, disclosure_lines.
   - voice/timings.json et words.json (mots horodatés) ; subtitles.ass (style depuis la charte).
   - shotlist.json : shots[] {id, segment_id, start_s, end_s, duration_s, visual_intent, on_screen_text, asset_request {type: image | stock | card | avatar, prompt_or_keywords, reuse_ok}, motion (zoom_in | zoom_out | pan | parallax | static), transition_in, is_sponsor, interrupt}, stats {median_shot_s, target_s}.
   - manifest.json : identité (video_id, parent_id, channel_id, lang, niche, style, template_id, charte_version) ; décisions (topic + source + score, hook_type, title_variants[] + chosen, thumbnail_variants[] + chosen, cut_rhythm_target_s, cut_rhythm_measured_s, duration_s, density_facts_per_min, voice_id, music_track + licence, assets[] {path, source, licence, attribution}) ; conformité (contains_synthetic_media + raison, paid_promotion, sponsor_segments, disclosure_lines, reviewer, review_hash, review_date, dedupe_hash) ; exécution (timings par étape en secondes, modèles + versions, cost {compute_min, energy_kwh, eur}, disk_mb, errors[]) ; résultats (rempli par la phase 5 : youtube_video_id, published_at, metrics_7d, metrics_30d) ; schema_version.
   - qc.json, publish.json, events.jsonl (une ligne par événement : ts, run, step, level, msg, data).
   - config/channels/<id>.yaml (exemple complet) : id, name, lang, niche, style, templates[], charte, voice_id, cadence {per_week_max, days, hours_local, jitter_min}, google_account (référence vers secrets/, pas la valeur), products[], derive_from (optionnel), auto_approve: false, youtube {audit_passed: false, playlist_id}.
   - config/niches/<id>.yaml, config/styles/<id>.yaml (backend, params), config/languages/<code>.yaml (voix disponibles, règles typographiques, formats de nombre), config/products/<id>.yaml, config/qc.yaml, config/editorial.yaml, config/team.yaml (relecteurs).
   - Interface Python :
     class StyleEngine(Protocol):
         name: str; backend: Literal["ffmpeg", "revideo"]
         def prepare_assets(self, shotlist: Shotlist, channel: Channel, run: RunPaths) -> list[Asset]: ...
         def render_shot(self, shot: Shot, assets: list[Asset], channel: Channel, run: RunPaths) -> Path: ...
     et le registre des moteurs (dict nom → classe), chargé par config.
   - Commandes CLI prévues (nom, arguments, ce qu'elles écrivent) : doctor, config validate/show, plan, research, script, review, voice, subtitles, shotlist, render, assemble, thumbnail, metadata, qc, export, run, localize, publish, calendar, queue, daemon, editorial collect/niches/topics, analytics pull/show, learn, economics, library, dashboard.
   - Sémantique des erreurs : codes de retour, reprise `--from <etape>`, tentatives, ce qui bloque un run (statut blocked + raison lisible).
3. Lance le contradicteur, corrige les deux documents, ajoute « Objections et réponses ».
4. Commit « étape 8 : architecture et interfaces ».
</tache>

<contraintes>
- Aucun code exécutable à cette étape (les signatures et exemples sont de la documentation).
- Chaque champ du manifeste doit servir soit à la conformité, soit à la boucle de rétroaction, soit à l'exploitation : justifie en un mot ceux qui ne sont pas évidents.
- Aucun `if style == ...` dans la conception : le style est une valeur de configuration qui sélectionne un moteur.
</contraintes>

<criteres_de_validation>
Montre : grep -c "^### " docs/INTERFACES.md (≥ 14 contrats) ; grep -c '```' docs/INTERFACES.md (≥ 24, soit ≥ 12 exemples) ; la liste des champs du manifeste comparée à CONFORMITE.md §10 (tous présents) ; la section « Objections et réponses ».
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 8 terminée, décisions d'architecture (5 lignes maximum), objections non résolues. Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP (sections 3, 4, étape 8) + STATE + CONFORMITE + STYLES + REFERENTIEL.md + extraits SELECTION/RESULTATS | 16 000 |
| Prompt (~1 450 mots) | 2 000 |
| Écriture ARCHITECTURE.md (≈ 250 lignes) | 3 300 |
| Écriture INTERFACES.md (≈ 450 lignes) | 6 000 |
| 1 rapport contradicteur | 1 500 |
| Corrections et « Objections et réponses » | 2 500 |
| Mise à jour STATE.md + résumé | 800 |
| Sous-total | 50 100 |
| Marge +25 % | 12 525 |
| **Total** | **62 625 tk — 31,3 %** |

## Étape 9 — Modèle de données versionné, configuration, secrets

**Objectif.** Implémenter les structures de données (pydantic v2) et le chargeur de configuration, avec des exemples de configuration couvrant 2 niches × 2 langues, des tests, et la gestion des secrets hors dépôt.
**Pourquoi maintenant.** Toutes les étapes de pipeline lisent et écrivent ces structures ; un modèle solide évite les variables éparpillées que dénonce la thèse.
**Valeur créée.** Thèse n° 4 (multi-chaînes et multi-langues sont des données, pas du code) et n° 5 (les champs de conformité sont obligatoires par construction).
**Pré-requis.** Étape 8 terminée · `docs/INTERFACES.md`, `docs/CONFORMITE.md` §10.
**Sous-agents.** Aucun.
**Livrables.** `factory/core/models.py`, `factory/core/config.py`, `factory/core/paths.py`, `factory/core/secrets.py`, `factory/core/db.py` (création de `workspace/factory.db`), `config/**/*.yaml` (exemples), `tests/test_models.py`, `tests/test_config.py`, `factory config validate|show`.
**Poids disque.** 0.
**Terminé quand.** `uv run pytest -q` passe avec ≥ 12 tests · `uv run factory config validate` retourne 0 sur les exemples et 1 sur un fichier volontairement invalide · chaque champ de `CONFORMITE.md` §10 existe dans `models.py` comme champ obligatoire ou avec valeur par défaut explicite · `INTERFACES.md` mis à jour si le code a dû s'en écarter.

**Prompt à copier-coller :**

````text
Tu es développeur Python senior ; tu écris des modèles de données typés, versionnés et testés.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local. Les contrats sont dans docs/INTERFACES.md ; les champs de conformité obligatoires dans docs/CONFORMITE.md §10. Cette session implémente le modèle de données et la configuration. Tout ce qui est « chaîne », « niche », « style », « langue », « produit » doit être une donnée validée, jamais une constante dans le code : c'est ce qui rend le système multi-chaînes et multi-langues par construction.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 9 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 9 \|^## Étape 10 " ROADMAP.md puis Read en offset/limit.
2. STATE.md
3. docs/INTERFACES.md (entier)
4. docs/CONFORMITE.md — sections 10 et 6 uniquement.
5. registre/REFERENTIEL.json — uniquement la liste des niches (python -c "import json; print(list(json.load(open('registre/REFERENTIEL.json'))['niches']))").
</demarrage>

<tache>
1. factory/core/models.py (pydantic v2, `model_config = ConfigDict(extra="forbid")`, champ `schema_version: str` sur chaque modèle racine) : Language, Niche, Charte, Style (backend, params, templates), Voice, Product (programme, base_url, tracking_param, disclosure par langue), Channel (avec cadence et limites de CONFORMITE §6 validées : per_week_max ≤ 2 par défaut), Topic, VideoSpec, ScriptSegment, Script, WordTiming, Shot, Shotlist, Asset (source, licence, attribution), QCReport, PublishRecord, RunManifest (tous les champs de INTERFACES.md ; timings et cost avec valeurs par défaut vides). Validateurs croisés : la voix appartient à la langue de la chaîne ; le style référencé existe ; un produit configuré implique paid_promotion=True et des disclosure_lines dans la langue.
2. factory/core/paths.py : classe RunPaths (tous les chemins d'un run depuis video_id) et LibraryPaths ; factory/core/config.py : chargement YAML de config/ → modèles, validation croisée, fonction get_channel(id), list_channels(), fonction de génération de video_id ; factory/core/secrets.py : lecture de .env (python-dotenv) et de secrets/ (jamais loggé, jamais dans un manifeste) ; factory/core/db.py : ouverture de workspace/factory.db, création idempotente des tables runs (index des manifestes), jobs, review_log (schéma minimal, les autres étapes ajouteront les leurs via migrations numérotées dans factory/core/migrations/).
3. Exemples de configuration : config/languages/{fr,en,es,it}.yaml ; config/niches/ pour chaque niche de REFERENTIEL.json (cibles reprises du référentiel) ; config/styles/{cartes,illustre,documentaire,motion,whiteboard,avatar2d}.yaml (backend et paramètres, même si le moteur n'existe pas encore : le validateur accepte les moteurs déclarés « planifié ») ; config/channels/{bms-science-fr,bms-science-en,bms-histoire-fr,bms-histoire-es}.yaml complets ; config/products/exemple-affilie.yaml ; config/team.yaml (relecteurs : Thomas, Alek, Sofiane) ; config/qc.yaml et config/editorial.yaml squelettes.
4. factory/cli.py : commandes `config validate` (0 si tout valide, 1 avec messages lisibles sinon) et `config show <channel_id>` (affichage rich).
5. tests/ : aller-retour JSON de chaque modèle racine, validateurs croisés (cas valides et invalides), chargement des exemples, échec sur un YAML volontairement cassé (tests/fixtures/channel_invalide.yaml), génération de video_id, tables créées. ≥ 12 tests.
6. uv run pytest -q ; uv run factory config validate ; corrige jusqu'au vert. Si le code a dû s'écarter de INTERFACES.md, mets INTERFACES.md à jour et note-le.
7. Commit « étape 9 : modèle de données et configuration ».
</tache>

<contraintes>
- Aucun modèle IA chargé, aucun réseau.
- Noms de champs en anglais, docstrings courtes en français.
- Aucune valeur secrète dans un YAML ou un test.
</contraintes>

<criteres_de_validation>
Montre : uv run pytest -q (nombre de tests, tout vert) ; uv run factory config validate ; echo $? ; uv run factory config validate --file tests/fixtures/channel_invalide.yaml ; echo $? (1) ; grep -c "class " factory/core/models.py.
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 9 terminée, écarts par rapport à INTERFACES.md, chaînes d'exemple. Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + INTERFACES.md (≈ 450 lignes) + CONFORMITE §6, §10 | 11 000 |
| Prompt (~1 250 mots) | 1 800 |
| Écriture models.py (≈ 350 lignes) | 4 700 |
| Écriture config.py + paths.py + secrets.py + db.py (≈ 200 lignes) | 2 700 |
| Écriture des YAML d'exemple (≈ 250 lignes) | 3 300 |
| Écriture des tests (≈ 150 lignes) | 2 000 |
| CLI (≈ 60 lignes) | 800 |
| Exécutions pytest / validate (extraits) | 3 000 |
| Corrections | 3 000 |
| Mise à jour STATE.md + résumé | 800 |
| Sous-total | 51 100 |
| Marge +25 % | 12 775 |
| **Total** | **63 875 tk — 31,9 %** |

## Étape 10 — Sujet issu du référentiel → recherche → script structuré

**Objectif.** Implémenter les trois premières étapes du pipeline : choix du sujet (dans les sujets porteurs du référentiel, jamais au hasard), recherche factuelle sur sources gratuites, écriture d'un script structuré (hook typé, segments, texte à l'écran, intentions visuelles, boucles ouvertes, signature éditoriale, segment sponsor) par le LLM local.
**Pourquoi maintenant.** Le script est l'entrée de tout le reste ; il porte déjà les paramètres de rétention que l'étape 16 renforcera.
**Valeur créée.** Thèse n° 1 (le sujet vient des données dès la première vidéo) et n° 3 (le hook est typé et mesurable dès le premier script).
**Pré-requis.** Étape 9 terminée · `registre/REFERENTIEL.json` · `factory doctor` vert.
**Sous-agents.** 1 — sources factuelles gratuites et sans clé pour la recherche automatique (API REST Wikipedia et Wikidata, PubMed E-utilities, Semantic Scholar, arXiv, Open Library) : points d'entrée, limites de débit, User-Agent requis, format de réponse. 400 mots maximum.
**Livrables.** `factory/steps/plan.py`, `factory/steps/research.py`, `factory/steps/script.py`, `factory/llm.py` (client local unique), `factory/prompts/script_<lang>.md`, un run avec `spec.json`, `research.json`, `script.json`.
**Poids disque.** 0.
**Terminé quand.** `factory plan --channel bms-science-fr` crée un run dont le sujet vient de `REFERENTIEL.json` (source = referentiel) · `factory research` écrit ≥ 3 sources avec URL et citations · `factory script` produit un `script.json` valide (pydantic) dont la durée estimée est à ±15 % de la cible de niche, avec type de hook enregistré, ≥ 2 boucles ouvertes, `editorial_signature` remplie · temps de chaque étape écrit dans `manifest.json`.

**Prompt à copier-coller :**

````text
Tu es ingénieur LLM et rédacteur en chef ; tu fais produire à un modèle local des scripts structurés, vérifiables et conformes à des cibles chiffrées.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local. Le sujet pèse plus que la qualité de rendu : le pipeline choisit son sujet dans les sujets porteurs mesurés du registre (registre/REFERENTIEL.json), pas au hasard. Le script doit porter dès maintenant un hook typé (taxonomie du référentiel), des boucles ouvertes, un texte à l'écran et une intention visuelle par segment, une signature éditoriale humaine (angle propre, éléments propriétaires : comparaison chiffrée, opinion argumentée, test) exigée par docs/CONFORMITE.md §4, et, si un produit est configuré, un segment sponsor avec ses mentions. Le LLM local retenu (voir outils/SELECTION.md) tourne seul en mémoire : un processus par appel, contexte plafonné.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 10 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 10 \|^## Étape 11 " ROADMAP.md puis Read en offset/limit.
2. STATE.md
3. docs/INTERFACES.md — contrats spec.json, research.json, script.json, manifest.json et la commande plan/research/script (grep -n "spec.json\|research.json\|script.json\|manifest" pour localiser).
4. registre/REFERENTIEL.md (entier) et la structure de REFERENTIEL.json (python -c pour lister les clés d'une niche et de hooks_taxonomie ; ne lis pas le fichier entier).
5. factory/core/models.py — uniquement les classes VideoSpec, Script, ScriptSegment, RunManifest (grep -n "^class").
6. Exécute uv run factory doctor --quick.
</demarrage>

<sous_agents>
Lance 1 sous-agent (recherche web) : sources factuelles gratuites, sans clé ni carte, interrogeables par HTTP depuis un script — Wikipedia REST (résumé, sections, langues fr/en/es/it), Wikidata, PubMed E-utilities (santé), Semantic Scholar, arXiv, Open Library — avec pour chacune : URL d'appel exemple, format de réponse, limite de débit, en-tête User-Agent exigé, licence des contenus. 400 mots maximum, une ligne par source.
</sous_agents>

<tache>
Réfléchis avant de coder : comment garantir qu'un script respecte la durée cible (mots ÷ mots par minute du référentiel), le type de hook tiré selon les parts de la niche, et qu'il est validé par pydantic malgré un LLM local qui produit parfois du JSON invalide.
1. factory/llm.py : client unique vers le runtime retenu (mlx-lm ou ollama selon SELECTION.md), fonction generate(prompt, system, max_tokens, temperature, json_schema=None) exécutée dans un sous-processus, contexte plafonné à 8 k tokens, journalisation du temps et du nombre de tokens, réparation JSON (extraction du premier objet, nouvelle tentative avec le message d'erreur pydantic, 3 essais maximum).
2. factory/steps/plan.py : `factory plan --channel <id> [--topic "..."] [--product <id>]` → choisit le sujet : si --topic absent, prend dans REFERENTIEL.json niches[niche].sujets_porteurs le premier sujet non encore utilisé par cette chaîne ni par une autre chaîne de même langue (table runs de factory.db), source = "referentiel", avec evidence (vues, ratio, chaîne source) ; crée le dossier de run, spec.json (cible de durée = duree_s.mediane de la niche, cut_rhythm_target_s = rythme_coupe_s.cible), manifest.json initial, enregistre le run dans la base. Note : à l'étape 20, cette commande lira d'abord la file de sujets éditoriale ; laisse un point d'extension explicite.
3. factory/steps/research.py : `factory research --run <id>` → à partir du sujet et de la langue : 3 à 6 sources (Wikipedia dans la langue de la chaîne puis en anglais, plus une source spécialisée si la niche est santé ou science), extraction de faits saillants avec citation courte et URL, puis appel LLM pour proposer 3 angles éditoriaux (contrarien, comparatif chiffré, récit) et en choisir un selon la persona de la chaîne (config) → research.json (facts[], angle, elements_proprietaires proposés). User-Agent identifiant le projet avec un contact.
4. factory/steps/script.py : `factory script --run <id>` → tire le type de hook selon hooks.parts de la niche (aléa seedé, enregistré dans le manifeste), construit le prompt depuis factory/prompts/script_<lang>.md (structure imposée : hook ≤ hooks.longueur_mots.mediane de la niche (registre/REFERENTIEL.json ; mesuré à l'étape 3, jusqu'à 61 mots selon la niche — remplace l'ancien plafond fixe de 35 mots, invalidé par la mesure, décision Thomas 15/09/2026) du type tiré, segments avec rôle, texte à l'écran ≤ 6 mots, intention visuelle concrète, boucle ouverte plantée avant le 2e segment et payée avant la conclusion, rupture toutes les N secondes avec N = 4 × rythme_coupe_s.cible, segment sponsor avec phrase de divulgation exacte de CONFORMITE §3 si produit, conclusion avec appel à l'action), demande un JSON conforme au schéma Script, valide, calcule word_count et estimated_duration_s = mots ÷ (mots_par_minute.mediane ÷ 60) ; si la durée sort de ±15 % de la cible, redemande une version plus longue ou plus courte (2 fois maximum) ; écrit script.json et met à jour le manifeste (hook_type, density brute = faits cités ÷ minutes, timings).
5. Exécute la chaîne sur bms-science-fr, puis sur bms-science-en, avec journal dans workspace/logs/etape10.log (tail -30). Lis les deux script.json (ils sont courts) et juge : le hook est-il du type tiré, la signature éditoriale est-elle réelle, le texte à l'écran est-il utilisable ? Corrige les prompts si nécessaire (2 itérations maximum).
6. Commit « étape 10 : plan, recherche, script ».
</tache>

<contraintes>
- Un seul modèle en mémoire ; chaque appel LLM dans un sous-processus qui se termine.
- Aucune source payante ni clé ; respecte les limites de débit rapportées.
- Le sujet manuel (--topic) est autorisé mais tracé comme source = "manuel".
- Ne lis pas research.json en entier si > 200 lignes : vérifie les compteurs.
</contraintes>

<criteres_de_validation>
Montre : cat workspace/runs/<id>/spec.json ; python -c qui charge script.json dans le modèle Script et affiche hook.type, word_count, estimated_duration_s, cible, nombre de boucles ouvertes, editorial_signature ; le nombre de sources de research.json ; les timings dans manifest.json.
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 10 terminée, identifiants des deux runs, temps par étape, défauts observés dans les scripts (pour l'étape 16). Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + extraits INTERFACES + REFERENTIEL.md + classes models | 9 500 |
| Prompt (~1 450 mots) | 2 000 |
| 1 rapport de sous-agent | 1 200 |
| Écriture llm.py (≈ 120 lignes) | 1 600 |
| Écriture plan.py + research.py (≈ 320 lignes) | 4 300 |
| Écriture script.py + prompts (≈ 300 lignes) | 4 000 |
| Exécutions (extraits) et lecture de 2 script.json | 3 500 |
| Corrections de prompts et relances | 3 000 |
| Mise à jour STATE.md + résumé | 800 |
| Sous-total | 47 900 |
| Marge +25 % | 11 975 |
| **Total** | **59 875 tk — 29,9 %** |

## Étape 11 — Voix et sous-titres

**Objectif.** Synthétiser la voix segment par segment avec la voix de la chaîne, normaliser à -14 LUFS, produire les horodatages par segment et par mot, et générer des sous-titres stylés à partir du script (le texte du script fait foi, l'ASR fournit le timing).
**Pourquoi maintenant.** Le découpage en plans (12.1) se cale sur les timings de la voix.
**Valeur créée.** Thèse n° 3 (des sous-titres dynamiques et un audio aux normes YouTube sont des facteurs de rétention mesurables) et n° 7 (voix cohérente par chaîne).
**Pré-requis.** Étape 10 terminée · un run avec `script.json` · TTS et ASR retenus installés.
**Sous-agents.** Aucun.
**Livrables.** `factory/steps/voice.py`, `factory/steps/subtitles.py`, `factory/audio.py` (loudness, concaténation), pour le run : `voice/segment_XX.wav`, `voice/voice.wav`, `voice/timings.json`, `words.json`, `subtitles.srt`, `subtitles.ass`.
**Poids disque.** 0.
**Terminé quand.** `voice.wav` existe, loudness intégrée mesurée par `ffmpeg -af ebur128` entre -15 et -13 LUFS, true peak ≤ -1 dBTP · `timings.json` couvre tous les segments · `subtitles.srt` a ≥ 1 sous-titre par tranche de 5 s et aucun sous-titre > 2 lignes de 42 caractères · WER entre transcription ASR et script < 8 % (sinon consigné comme alerte) · timings dans le manifeste.

**Prompt à copier-coller :**

````text
Tu es ingénieur audio et développeur Python ; tu connais la synthèse vocale locale, la normalisation de loudness et les formats de sous-titres.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local. Cette session implémente la voix et les sous-titres du pipeline. La voix est une propriété de la chaîne (config/channels, config/languages : identifiant de voix du TTS retenu à l'étape 5.1). Les sous-titres dynamiques (1 à 5 mots à la fois) sont un levier de rétention observé sur les chaînes du registre ; l'audio doit respecter la norme YouTube (-14 LUFS). Le script fait foi pour le texte ; l'ASR donne les timings de mots.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 11 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 11 \|^## Étape 12\.1 " ROADMAP.md puis Read en offset/limit.
2. STATE.md
3. docs/INTERFACES.md — contrats voice/timings.json, words.json, subtitles.ass, Charte (grep -n).
4. benchmarks/RESULTATS.md §1 — commandes et paramètres du TTS et de l'ASR retenus (grep -n).
5. Le script.json du dernier run (court).
6. uv run factory doctor --quick.
</demarrage>

<tache>
1. factory/audio.py : fonctions concat(wavs, pauses), loudnorm_two_pass(in, out, target=-14, tp=-1) via ffmpeg (mesure puis application, valeurs mesurées retournées), measure_lufs(path), silence_trim(path, seuil).
2. factory/steps/voice.py : `factory voice --run <id>` → pour chaque segment du script : synthèse avec le TTS retenu (sous-processus, voix de la chaîne, vitesse depuis config/languages), nettoyage des silences en tête/queue, écriture voice/segment_XX.wav ; concaténation avec pauses configurables (charte : 350 ms entre segments, 600 ms après le hook, 250 ms avant le sponsor), normalisation deux passes, voice/voice.wav et voice/timings.json (segment_id, start_s, end_s) ; manifeste : voice_id, durée totale, LUFS mesuré, temps.
3. factory/steps/subtitles.py : `factory subtitles --run <id>` → ASR retenu sur voice.wav avec horodatage des mots → alignement souple avec le texte du script (correspondance mot à mot par similarité, le texte du script remplace le mot reconnu, les timings viennent de l'ASR ; les mots non alignés héritent d'une interpolation) → words.json ; puis subtitles.srt (groupes de 1 à 5 mots, ≤ 42 caractères par ligne, ≤ 2 lignes, durée 0,4 à 3 s) et subtitles.ass avec le style de la charte (police OFL, taille, couleur, contour, position, mot courant surligné si la charte le demande). Calcule le WER ASR vs script et écris-le dans le manifeste ; > 8 % = avertissement loggé.
4. Exécute sur le run FR puis sur le run EN de l'étape 10 ; journal workspace/logs/etape11.log (tail -30). Mesure : ffprobe voice.wav (durée), ffmpeg -af ebur128 (LUFS intégré, true peak), comptage des sous-titres par tranche de 5 s, plus longue ligne. Compare la durée réelle de la voix à estimated_duration_s du script et consigne l'écart (calibration du mots par minute du référentiel : si > 10 %, note-le pour l'étape 16).
5. Demande à Thomas d'écouter voice.wav des deux runs (30 s suffisent) et de noter 1-5 ; « non évaluée » s'il n'est pas disponible.
6. Commit « étape 11 : voix et sous-titres ».
</tache>

<contraintes>
- Un modèle en mémoire à la fois : TTS puis ASR, dans des sous-processus séparés.
- Aucun service en ligne.
- Ne lis pas words.json en entier ; vérifie par comptage.
</contraintes>

<criteres_de_validation>
Montre : ffprobe -v error -show_entries format=duration voice/voice.wav ; la ligne « Integrated » et « True peak » de ebur128 ; le nombre de cues SRT et la plus longue ligne ; le WER ; l'écart durée réelle vs estimée ; les timings du manifeste.
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 11 terminée, LUFS obtenus, WER, écart de durée, note humaine des voix, temps. Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + extraits INTERFACES/RESULTATS + script.json | 9 000 |
| Prompt (~1 150 mots) | 1 800 |
| Écriture audio.py + voice.py (≈ 220 lignes) | 2 900 |
| Écriture subtitles.py (≈ 250 lignes) | 3 300 |
| Exécutions (extraits) | 4 000 |
| Mesures ebur128 / ffprobe / comptages | 800 |
| Corrections | 3 500 |
| Mise à jour STATE.md + résumé | 800 |
| Sous-total | 44 100 |
| Marge +25 % | 11 025 |
| **Total** | **55 125 tk — 27,6 %** |

## Étape 12.1 — Découpage en plans, interface StyleEngine, moteur « cartes »

**Objectif.** Découper la vidéo en plans au rythme de coupe de la niche (avec hook plus rapide et ruptures programmées), implémenter l'interface `StyleEngine` et son registre, et livrer un premier moteur ffmpeg pur (« cartes » : texte à l'écran animé sur fonds de charte) qui rend chaque plan en clip vérifié.
**Pourquoi maintenant.** Le rythme de coupe est la cible chiffrée la plus directement exploitable du registre ; il faut l'appliquer avant de générer le moindre visuel. Le moteur « cartes » donne une vidéo complète dégradée dès maintenant.
**Valeur créée.** Thèse n° 3 : le rythme de coupe devient un paramètre appliqué et auto-vérifié.
**Pré-requis.** Étape 11 terminée · run avec `voice/timings.json`, `words.json`.
**Sous-agents.** Aucun.
**Livrables.** `factory/steps/shotlist.py`, `factory/styles/__init__.py` (registre), `factory/styles/base.py`, `factory/styles/cartes.py`, `factory/video.py` (helpers ffmpeg), `factory render`, pour le run : `shotlist.json`, `clips/shot_XX.mp4`.
**Poids disque.** 0.
**Terminé quand.** `shotlist.json` a une durée médiane de plan à ±10 % de `cut_rhythm_target_s` (hors hook), le hook a des plans ≤ 0,7 × cible, une rupture toutes les N secondes conformément au script · tous les clips existent, `ffprobe` confirme 1920×1080, 30 fps, durée = plan ±0,05 s · temps de rendu par plan dans le manifeste.

**Prompt à copier-coller :**

````text
Tu es développeur vidéo ; tu maîtrises ffmpeg (filtres, drawtext, zoompan, xfade) et la conception d'interfaces Python extensibles.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local. Le rythme de coupe par niche (registre/REFERENTIEL.json, rythme_coupe_s) est la cible produit la plus concrète du registre : cette session le transforme en découpage effectif, vérifié avant rendu. Elle pose aussi l'interface StyleEngine (docs/INTERFACES.md) et son premier moteur, « cartes », en ffmpeg pur : pas d'image générée, pas de navigateur, une vidéo complète mais sobre. Les moteurs suivants (illustré, documentaire, motion, whiteboard, avatar 2D) implémenteront la même interface.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 12.1 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 12\.1 \|^## Étape 12\.2 " ROADMAP.md puis Read en offset/limit.
2. STATE.md
3. docs/INTERFACES.md — contrats shotlist.json, StyleEngine, Charte, config/styles (grep -n).
4. docs/ARCHITECTURE.md — section « Moteurs de style ».
5. registre/REFERENTIEL.json — rythme_coupe_s de la niche du run (python -c).
6. Le script.json et voice/timings.json du run FR (courts).
</demarrage>

<tache>
Réfléchis avant de coder : comment obtenir une médiane de durée de plan égale à la cible avec un jitter naturel (±30 %), des plans plus courts dans le hook (× 0,6), des ruptures visuelles aux positions marquées par le script, et des coupes qui tombent sur des frontières de mots (words.json) plutôt qu'au milieu d'un mot.
1. factory/steps/shotlist.py : `factory shotlist --run <id>` → à partir de script.json, voice/timings.json, words.json, de la cible de la niche (surcharge possible par config/styles ou config/channels) : génère shots[] conformes au contrat (segment_id, start_s, end_s, visual_intent hérité ou découpé, on_screen_text seulement sur le premier plan d'un segment sauf indication, asset_request selon le moteur, motion alternée, transition_in, is_sponsor, interrupt) ; règles : durée tirée dans [0,7 ; 1,3] × cible (hook : × 0,6), coupe déplacée sur la frontière de mot la plus proche, un segment sponsor garde un plan dédié avec is_sponsor=true, une rupture (interrupt) force un changement de type d'asset et un plan court ; calcule stats {median_shot_s, p10, p90, n_shots, target_s} et refuse (code 2, message) si la médiane hors hook sort de ±10 % de la cible : dans ce cas ajuste automatiquement la graine ou le jitter (3 essais) avant d'échouer. Écrit shotlist.json et le manifeste (cut_rhythm_target_s, cut_rhythm_planned_s).
2. factory/styles/base.py : Protocol StyleEngine + classe utilitaire (chargement de la charte, chemins, verify_clip via ffprobe) ; factory/styles/__init__.py : registre nom → classe, get_engine(channel) ; factory/video.py : helpers ffmpeg (fond uni ou dégradé animé, drawtext avec police OFL de la charte, animation d'apparition par alpha, zoompan suréchantillonné, encodage intermédiaire ProRes ou H.264 CRF 16, verify_clip).
3. factory/styles/cartes.py : moteur « cartes » : pour chaque plan, un fond issu de la palette de la charte (dégradé animé lent, alternance de 3 templates : plein, bandeau bas, carte centrale), le texte à l'écran en gros (retour à la ligne automatique, ≤ 3 lignes), une forme géométrique animée subtile, durée exacte du plan ; is_sponsor → bandeau « Publicité » (texte de CONFORMITE §3 dans la langue) affiché pendant tout le plan.
4. `factory render --run <id> [--style cartes]` → prepare_assets puis render_shot pour chaque plan → clips/shot_XX.mp4 ; vérification ffprobe (1920×1080, 30 fps, durée ±0,05 s) ; temps par plan et total dans le manifeste ; journal workspace/logs/etape12_1.log (tail -30).
5. Exécute shotlist puis render sur le run FR. Extrais 2 images de 2 clips différents (ffmpeg -ss … -frames:v 1) et regarde-les : texte lisible, marges respectées, bandeau sponsor présent si applicable.
6. Commit « étape 12.1 : découpage et moteur cartes ».
</tache>

<contraintes>
- ffmpeg uniquement pour ce moteur ; aucun navigateur, aucun modèle IA.
- Deux images regardées au maximum.
- Toute sortie ffmpeg vers le log ; n'affiche que les erreurs et les vérifications.
</contraintes>

<criteres_de_validation>
Montre : python -c qui affiche stats de shotlist.json (médiane hors hook, cible, écart %, médiane du hook, n_shots) ; ls clips | wc -l = n_shots ; une boucle ffprobe qui vérifie durée/résolution/fps de chaque clip (0 erreur) ; le temps total de rendu.
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 12.1 terminée, écart médiane/cible, temps de rendu par plan, défauts visuels observés. Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + extraits INTERFACES/ARCHITECTURE + script/timings | 9 000 |
| Prompt (~1 300 mots) | 2 000 |
| Écriture shotlist.py (≈ 250 lignes) | 3 300 |
| Écriture base.py + registre (≈ 120 lignes) | 1 600 |
| Écriture cartes.py + video.py (≈ 260 lignes) | 3 500 |
| Exécutions et vérifications ffprobe (extraits) | 3 500 |
| Inspection de 2 images | 3 000 |
| Corrections | 3 000 |
| Mise à jour STATE.md + résumé | 800 |
| Sous-total | 47 700 |
| Marge +25 % | 11 925 |
| **Total** | **59 625 tk — 29,8 %** |

## Étape 12.2 — Moteur « illustré animé »

**Objectif.** Livrer le moteur de style principal de la phase 1 : images générées localement à partir des intentions visuelles, cohérence de style par chaîne, mouvement par parallaxe 2.5D ou Ken Burns, texte à l'écran, réutilisation des images via la bibliothèque.
**Pourquoi maintenant.** C'est le style des chaînes qui performent au registre (images + voix off) et le premier rendu « présentable » de la première vidéo.
**Valeur créée.** Thèse n° 7 (chaque image générée entre dans la bibliothèque réutilisable) et n° 3 (le mouvement continu soutient l'attention).
**Pré-requis.** Étape 12.1 terminée · modèle image et Depth Anything Small installés (`factory doctor` vert).
**Hérité de l'étape 5.2 (mesuré sur le M2).** Trois dossiers arrivent ici, et pas ailleurs — c'est cette étape qui tient le moteur illustré, la bibliothèque d'images réutilisables et la cohérence entre plans d'une même vidéo.
(a) **La cohérence de style sur 8 plans d'une même vidéo est mesurée, et elle N'EST PAS TENUE** (`benchmarks/RESULTATS.md` § 2.11 et § 2.12, plans dans `samples/visuel/coherence8/`). Protocole reproductible dans `benchmarks/coherence_8plans.py` : une charte, 8 intentions consécutives, **graine = `sha256(video_id, plan)`** — schéma à reprendre tel quel, et **pas `hash()` de Python**, randomisé par processus. **Trois choses à corriger ici.** (i) **La charte ne fixe pas le cadrage** : 1 plan sur 8 est encadré d'une marge quand les autres vont au bord. `charte` doit porter le traitement du fond, sa couleur, et la part du cadre qu'occupe le sujet. (ii) **La charte ne fixe pas assez le personnage** : sur 8 plans, l'un a changé de sexe et de coiffure. Tout ce qui décrit le personnage doit être figé dans sa fiche — coiffure comprise, comme la tenue (voir b). (iii) **Un plan sur 8 portait une anatomie fausse** (pied retourné, ombre non ancrée) et une **mèche détachée** — et **aucun contrôle automatique ne les attrape** : mesuré, trois contrôles écrits et exécutés (`benchmarks/controles_plan.py`), le cadrage et la palette marchent, la détection de fragments détachés échoue par principe (3 séparations légitimes sur 13 ont la même signature géométrique que la fautive). **Cette étape doit donc prévoir un portillon humain plan par plan, ou appliquer la réduction d'exposition décidée à l'étape 6** (personnages en buste, priorité aux objets et aux lieux : les 4 plans sans anatomie humaine étaient indemnes).
(b) **La tenue d'un personnage dérive d'une graine à l'autre.** Même description, trois graines : chemise unie sur deux, **à carreaux à deux poches à rabat** sur la troisième — « flannel » désigne une matière, pas un motif. Invisible entre deux vidéos, **visible entre deux plans d'une même vidéo**. Le gabarit de prompt doit décrire motif, couleur, poches et col sans ambiguïté. Planche : `benchmarks/samples/visuel/coherence_planche.png`, mesures dans `benchmarks/RESULTATS.md` § 2.3.
(c) **Coût de référence à faire baisser : 137 s par plan en 1280×720**, soit 84 % du temps d'une vidéo (pic MLX 11,15 Go, 4 étapes, graine fixe). `workspace/library/images/` est ce qui doit le faire tomber — **à mesurer ici, pas à supposer**. Mouvement déjà mesuré et validé : parallaxe 2.5D 3,7 s par clip de 5 s à 1080p30, Ken Burns `zoompan` ×4 en 2,6 s, tous deux notés 4/5.
**Piège de la parallaxe, payé à l'étape 5.2 :** Depth Anything sort une profondeur **inverse** (clair = proche). Les couches doivent être **cumulatives** (chacune porte tout ce qui est plus proche qu'elle, le fond est l'image entière) sous peine de trous, et l'alpha doit être adouci sous peine de contours crénelés. Implémentation de référence : `benchmarks/bench_visuel.py`, fonction `brique_parallax`.
**Sous-agents.** 1 — ingénierie de prompt pour la cohérence de style sur 40 images avec le modèle retenu (préfixe de style, tokens de cohérence, graines, format 16:9, nombre d'étapes) et pièges mflux connus (mémoire, quantification, lots). 400 mots maximum.
**Livrables.** `factory/assets/images.py`, `factory/assets/parallax.py`, `factory/styles/illustre.py`, `workspace/library/images/` indexée, pour le run : `assets/`, `clips/`.
**Poids disque.** ≈ 0,1 Go par run (images PNG) ; bibliothèque croissante, suivie dans le ledger.
**Terminé quand.** Tous les plans du run FR sont rendus en style illustré · ≥ 90 % des images générées au premier essai · temps médian par image et par plan dans le manifeste · 4 images extraites jugées cohérentes entre elles (note /5 consignée) · chaque image a un `licence.json` (modèle, prompt, graine) · deuxième exécution du même run réutilise les images de la bibliothèque (0 génération).

**Prompt à copier-coller :**

````text
Tu es développeur créatif ; tu maîtrises la génération d'images par diffusion en local, la cohérence de style par prompt et le compositing vidéo avec ffmpeg.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local, M2 16 Go. Cette session implémente le moteur « illustré animé » : chaque plan reçoit une image générée localement (modèle retenu à l'étape 5.2, ~30-90 s par image à mesurer), animée par parallaxe 2.5D (Depth Anything V2 Small) ou par Ken Burns, avec le texte à l'écran de la charte. Les images entrent dans une bibliothèque réutilisable (workspace/library/images) : la vidéo n° 50 doit réutiliser ce que la n° 1 a produit. La cohérence de style entre les images d'une même vidéo et d'une même chaîne est un critère de qualité perçue.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 12.2 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 12\.2 \|^## Étape 13\.1 " ROADMAP.md puis Read en offset/limit.
2. STATE.md
3. factory/styles/base.py et factory/styles/cartes.py (entiers, courts) ; docs/INTERFACES.md — contrat Asset et bibliothèque (grep -n).
4. benchmarks/RESULTATS.md §2 — commandes et paramètres du modèle image et de la profondeur (grep -n).
5. config/styles/illustre.yaml et la charte de bms-science-fr.
</demarrage>

<sous_agents>
Lance 1 sous-agent (recherche web + lecture du dépôt mflux) : pour le modèle image retenu (voir RESULTATS.md), les techniques de cohérence de style sur une série d'images (préfixe de style, description de palette, tokens négatifs si supportés, stratégie de graines, format 1280×720 ou 1024×576, nombre d'étapes), et les pièges connus de mflux sur 16 Go (pic mémoire, quantification 4-bit, génération en lot, cache). 400 mots maximum, points numérotés avec URL.
</sous_agents>

<tache>
1. factory/assets/images.py : construction du prompt = charte.style_prefix + visual_intent + charte.style_suffix (palette, « no text », cohérence) ; graine = hash(video_id, shot_id) ; génération via mflux en sous-processus (1280×720, étapes du modèle, quantification retenue) ; cache par hash(prompt normalisé + style) dans workspace/library/images/<hash>.png avec <hash>.json (modèle, prompt, graine, date, licence « generated », used_by[]) et enregistrement dans la table assets_library de factory.db ; réutilisation si présent et non utilisé par la même chaîne dans ses 10 derniers runs ; nettoyage des images inutilisables (fichier vide, exception) avec une nouvelle graine (2 essais).
2. factory/assets/parallax.py : carte de profondeur (Depth Anything V2 Small, sous-processus) → 3 couches seuillées avec remplissage des trous (inpainting simple par flou ou décalage) → clip 1080p30 de la durée du plan avec déplacement différencié des couches (amplitude selon motion du plan) ; repli Ken Burns (zoompan suréchantillonné ×4, zoom 1,0 → 1,08 ou inverse, pan léger) si la profondeur échoue ou si le plan est < 2 s.
3. factory/styles/illustre.py : StyleEngine « illustre » : prepare_assets génère ou réutilise une image par plan (plans « card » ou sponsor : fond de charte comme dans cartes.py) ; render_shot compose parallaxe/Ken Burns + texte à l'écran (style charte, apparition animée) + vignettage léger + bandeau « Publicité » si is_sponsor ; durée exacte ; verify_clip.
4. Exécute `factory render --run <id-FR> --style illustre` avec journal (tail -30). Mesure : temps médian par image, par plan, total, pic mémoire du sous-processus image (/usr/bin/time -l). Extrais 4 images de 4 clips et regarde-les : cohérence de style, absence de texte parasite généré, lisibilité du texte à l'écran, qualité du mouvement (compare une image au début et à la fin d'un même clip si nécessaire, dans la limite de 4 images au total). Note /5 dans le manifeste (champ quality_notes) et dans STATE.md.
5. Relance le même render : vérifie 0 génération (tout depuis la bibliothèque) et le temps.
6. Mets à jour outils/MODELES.md si de nouveaux poids ont été ajoutés (aucun n'est attendu) et le ledger de la bibliothèque (taille de workspace/library/images).
7. Commit « étape 12.2 : moteur illustré ».
</tache>

<contraintes>
- Un modèle en mémoire à la fois : image puis profondeur, jamais ensemble.
- 4 images regardées au maximum.
- Si le temps par image dépasse 120 s, réduis à 1024×576 et note-le ; si la parallaxe dépasse 20 s par plan, repli Ken Burns par défaut et note-le.
- Aucune image de personne réelle identifiable dans les prompts.
</contraintes>

<criteres_de_validation>
Montre : ls clips | wc -l = n_shots ; boucle ffprobe (0 erreur) ; python -c qui lit le manifeste (temps médian par image, par plan, total, part d'images réutilisées) ; ls workspace/library/images | wc -l ; le temps de la seconde exécution.
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 12.2 terminée, temps par image et par plan, note de cohérence, taille de la bibliothèque, réglages retenus (résolution, étapes, parallaxe ou Ken Burns). Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + base/cartes + extraits INTERFACES/RESULTATS + config | 9 000 |
| Prompt (~1 400 mots) | 2 000 |
| 1 rapport de sous-agent | 1 200 |
| Écriture images.py (≈ 200 lignes) | 2 700 |
| Écriture parallax.py (≈ 200 lignes) | 2 700 |
| Écriture illustre.py (≈ 180 lignes) | 2 400 |
| Exécutions (génération de 30-45 images, extraits) | 5 000 |
| Inspection de 4 images | 6 000 |
| Corrections | 4 500 |
| Mise à jour STATE.md + résumé | 800 |
| Sous-total | 54 300 |
| Marge +25 % | 13 575 |
| **Total** | **67 875 tk — 33,9 %** |

## Étape 13.1 — Montage, musique, sous-titres, export vérifié

**Objectif.** Assembler les clips avec transitions, mixer la voix et un lit musical sous licence avec ducking, incruster ou muxer les sous-titres, normaliser, exporter en H.264 1080p30 et vérifier objectivement le fichier (durée, loudness, nombre de plans détectés).
**Pourquoi maintenant.** C'est l'avant-dernière pièce du premier MP4 complet ; la vérification objective posée ici devient la base du banc de l'étape 15.
**Valeur créée.** Thèse n° 3 (rythme réellement obtenu mesuré) et n° 5 (musique et sons tracés avec licence).
**Pré-requis.** Étape 12.2 terminée · clips du run FR · Thomas a téléchargé ≥ 5 pistes depuis la bibliothèque audio YouTube du compte de test dans `workspace/library/music/` (sinon Freesound CC0 par l'API, ou lit silencieux signalé).
**Sous-agents.** Aucun.
**Livrables.** `factory/steps/assemble.py`, `factory/steps/export.py`, `factory/assets/music.py`, pour le run : `video_nomusic.mp4`, `final.mp4`.
**Poids disque.** ≈ 0,3 Go par run (intermédiaires purgés après export).
**Terminé quand.** `final.mp4` : `ffprobe` confirme H.264 1920×1080 30 fps + AAC, durée = durée de la voix ±0,5 s · loudness intégrée -14 ±1 LUFS, true peak ≤ -1 dBTP · nombre de plans détectés par PySceneDetect = n_shots ±10 % · sous-titres visibles sur une image extraite · `music.licence` dans le manifeste · temps de montage et d'export dans le manifeste.

**Prompt à copier-coller :**

````text
Tu es monteur vidéo et ingénieur ffmpeg ; tu produis des fichiers conformes aux normes YouTube et tu vérifies chaque sortie par la mesure.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local. Cette session assemble les clips de plans en une vidéo finale : transitions selon la charte (coupes franches dans le hook, fondus courts ailleurs), voix normalisée, lit musical sous licence avec ducking, sous-titres incrustés ou muxés selon la charte, export H.264 1080p30 conforme YouTube, puis vérification objective (durée, loudness, plans détectés). La musique vient exclusivement de sources tracées (docs/CONFORMITE.md §7) : chaque piste a un licence.json.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 13.1 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 13\.1 \|^## Étape 13\.2 " ROADMAP.md puis Read en offset/limit.
2. STATE.md
3. docs/CONFORMITE.md §7 ; docs/INTERFACES.md — contrats Charte (transitions, sous-titres), manifest (music, assets), commandes assemble/export.
4. factory/video.py et factory/audio.py (entiers, courts).
5. ls workspace/library/music/ ; shotlist.json du run FR (stats seulement).
</demarrage>

<tache>
1. Musique : si workspace/library/music/ est vide, guide Thomas : YouTube Studio du compte de test → Bibliothèque audio → filtrer « Attribution non requise » et une piste CC pour tester le crédit → télécharger 5 pistes de moods différents (calme, tension, curieux, énergique, sombre) dans workspace/library/music/<slug>.mp3 avec un <slug>.json (titre, artiste, source « youtube_audio_library », licence, attribution_requise, mood, bpm approximatif). S'il n'est pas disponible : factory/assets/music.py sait interroger l'API Freesound (compte gratuit, clé dans .env FREESOUND_KEY) avec filtre licence CC0 et durée > 60 s ; sinon lit silencieux et avertissement dans le manifeste. Enregistre les pistes dans la table assets_library.
2. factory/assets/music.py : choix d'une piste par mood (config/niches : mood par niche ; script : mood optionnel), rotation pour ne pas répéter la même piste sur les 5 derniers runs d'une chaîne, boucle ou coupe à la durée voulue avec fondu de sortie.
3. factory/steps/assemble.py : `factory assemble --run <id>` → concaténation des clips avec transitions (xfade 0,25-0,4 s hors hook ; coupe franche dans le hook et sur les ruptures ; type depuis la charte), piste voix + musique avec ducking (sidechaincompress, musique à -18 dB sous la voix, -24 dB pendant le sponsor si configuré), sons de transition optionnels depuis la bibliothèque (CC0), sous-titres : incrustation de subtitles.ass si charte.subtitles == "burn" sinon piste mov_text ; normalisation finale -14 LUFS ; produit video_nomusic.mp4 (pour contrôle) puis assembled.mp4.
4. factory/steps/export.py : `factory export --run <id>` → H.264 High, CRF 18, preset medium, 1920×1080, 30 fps, AAC 192 kbit/s, +faststart → final.mp4 ; vérifications : ffprobe (codecs, résolution, fps, durée = durée voix ±0,5 s), ebur128 (intégré, true peak), PySceneDetect ContentDetector (n_scenes vs n_shots ±10 % ; consigne cut_rhythm_measured_s = durée ÷ n_scenes dans le manifeste), extraction de 5 images (à 3 %, 25 %, 50 %, 75 %, 97 %) dans qc/frames/ ; purge des clips intermédiaires si export vérifié (assets conservés) ; manifeste : timings, taille du fichier, mesures.
5. Exécute sur le run FR ; journal workspace/logs/etape13_1.log (tail -30). Regarde 3 des 5 images extraites : sous-titres lisibles et bien placés, texte non coupé, bandeau sponsor si applicable.
6. Commit « étape 13.1 : montage et export ».
</tache>

<contraintes>
- Aucune musique sans licence.json ; aucune piste réencodée depuis une source tierce non tracée.
- Trois images regardées au maximum.
- Sorties ffmpeg vers le log.
</contraintes>

<criteres_de_validation>
Montre : ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate -show_entries format=duration final.mp4 ; lignes Integrated et True peak de ebur128 ; n_scenes détectées vs n_shots ; le champ music du manifeste ; la taille de final.mp4.
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 13.1 terminée, mesures de final.mp4 (durée, LUFS, plans détectés vs prévus, rythme mesuré vs cible), source des pistes, temps. Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + CONFORMITE §7 + extraits INTERFACES + video/audio.py | 9 000 |
| Prompt (~1 350 mots) | 2 000 |
| Écriture assemble.py (≈ 300 lignes) | 4 000 |
| Écriture export.py (≈ 120 lignes) | 1 600 |
| Écriture music.py (≈ 80 lignes) | 1 000 |
| Exécutions (extraits) | 4 000 |
| Mesures ffprobe / ebur128 / scenedetect | 2 000 |
| Inspection de 3 images | 4 500 |
| Corrections | 4 000 |
| Mise à jour STATE.md + résumé | 800 |
| Sous-total | 50 900 |
| Marge +25 % | 12 725 |
| **Total** | **63 625 tk — 31,8 %** |

## Étape 13.2 — Miniature, métadonnées, `factory run`, première vidéo complète

**Objectif.** Générer la miniature (variantes de titre et de texte conservées pour la phase 3), les métadonnées (titre, description avec chapitres et mentions, tags, drapeaux de conformité), orchestrer toute la chaîne dans `factory run` avec reprise, finaliser le manifeste (timings, coût), et produire la première vidéo complète sur un sujet neuf, deux fois de suite.
**Pourquoi maintenant.** C'est le jalon de la phase 1 : une vidéo complète avant toute optimisation.
**Valeur créée.** Thèse n° 2 (le manifeste complet, avec variantes et coût, est prêt pour la boucle) ; preuve de faisabilité pour Alek.
**Pré-requis.** Étape 13.1 terminée.
**Sous-agents.** Aucun.
**Livrables.** `factory/steps/thumbnail.py`, `factory/steps/titles_v1.py`, `factory/steps/metadata.py`, `factory/run.py`, `factory run`, deux runs complets avec `final.mp4`, `thumbnail.png`, `metadata.json`, `manifest.json` finalisé.
**Poids disque.** ≈ 0,3 Go par run.
**Terminé quand.** `uv run factory run --channel bms-science-fr` puis `--channel bms-science-en` produisent chacun `final.mp4`, `thumbnail.png` 1280×720 avec texte lisible (hauteur de texte ≥ 12 % de l'image), `metadata.json` valide (titre ≤ 70 caractères, description avec chapitres, mention IA, bloc d'attribution, mention affiliation si produit) · `manifest.json` contient timings par étape, temps total, coût en euros, variantes de titres (≥ 5) et de textes de miniature (≥ 3) · aucune intervention manuelle pendant les deux runs · Thomas a visionné une vidéo et noté 3 défauts dans `STATE.md` (ou « non visionnée »).

**Prompt à copier-coller :**

````text
Tu es chef de produit technique et développeur Python ; tu livres une première version complète, mesurée et honnête plutôt qu'une version parfaite.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local. Cette session ferme la phase 1 : miniature, métadonnées, commande `factory run` qui enchaîne toutes les étapes avec reprise, manifeste finalisé (timings, coût), puis deux vidéos complètes produites de bout en bout sur des sujets neufs. Les variantes de titres et de textes de miniature sont conservées dans le manifeste : la phase 3 les mettra en concurrence et la phase 5 apprendra desquelles fonctionnent. La description doit porter les mentions de docs/CONFORMITE.md §3 (contenu synthétique, affiliation) et le bloc d'attribution des assets.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 13.2 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 13\.2 \|^## Étape 14 " ROADMAP.md puis Read en offset/limit.
2. STATE.md
3. docs/INTERFACES.md — contrats metadata.json, manifest.json, commande run ; docs/CONFORMITE.md §3 et §10.
4. registre/REFERENTIEL.json — titres.patrons et miniatures de la niche du run (python -c).
5. factory/cli.py (entier) ; la liste des commandes existantes.
</demarrage>

<tache>
1. factory/steps/titles_v1.py : à partir de script.json et des patrons de titre de la niche (REFERENTIEL.json), demande au LLM 8 titres (≤ 70 caractères, ≥ 3 patrons différents, langue du run) et 5 textes de miniature (2 à 4 mots, majuscules ou non selon la charte) ; score heuristique v1 (longueur, présence d'un nombre ou d'une question, correspondance à un patron, pas de mots interdits par la politique spam) ; choisit le meilleur, conserve toutes les variantes avec scores dans le manifeste (title_variants, thumbnail_text_variants).
2. factory/steps/thumbnail.py : `factory thumbnail --run <id>` → image de fond = image de l'asset du plan hook (ou la plus « forte » selon un choix LLM sur les visual_intent), composition 1280×720 via l'outil retenu (Playwright HTML→PNG ou satori/resvg) avec template de charte (≥ 2 templates en rotation), texte choisi en très gros, contour et ombre, bandeau de couleur, contraste vérifié (luminance texte/fond) ; contrôle : hauteur du texte ≥ 12 % de la hauteur de l'image, poids < 2 Mo ; produit thumbnail.png et thumbnails/variant_1..3.png (textes alternatifs) ; manifeste : thumbnail_variants + chosen.
3. factory/steps/metadata.py : `factory metadata --run <id>` → metadata.json : title, description (accroche 2 lignes reprenant le hook ; chapitres générés depuis voice/timings.json avec titres de segments ; sources ; bloc « Publicité » avec lien produit si produit configuré, sinon rien ; ligne de divulgation IA (texte de CONFORMITE §3 dans la langue) ; bloc d'attribution des assets et de la musique quand requis), tags (≤ 500 caractères, mots-clés du sujet et de la niche), category_id, default_language, contains_synthetic_media (règle de CONFORMITE §3 appliquée au style et aux intentions visuelles, avec reason), paid_promotion, made_for_kids=false, notify_subscribers depuis config.
4. factory/run.py + `factory run --channel <id> [--topic ...] [--from <etape>] [--style ...]` : enchaîne plan → research → script → voice → subtitles → shotlist → render → assemble → thumbnail → metadata → export, chaque étape dans un sous-processus avec marqueur .done, reprise à partir de la première étape non faite ou de --from, arrêt à la première erreur avec statut du run « failed » et raison lisible ; à la fin : manifeste finalisé (timings par étape, total, cost : compute_min × puissance moyenne (config, 30 W par défaut) × prix du kWh (config, 0,25 €) + 0 € d'outils ; disk_mb ; modèles et versions), statut « exported », mise à jour de la table runs.
5. Exécute `factory run --channel bms-science-fr` sur un sujet neuf (le plan en choisit un non utilisé), journal workspace/logs/run_<id>.log (tail -40 seulement). Puis `factory run --channel bms-science-en`. Aucune intervention manuelle : si une étape échoue, corrige le code et relance avec --from.
6. Regarde thumbnail.png du run FR et 2 images de qc/frames/ ; vérifie la lisibilité.
7. Demande à Thomas de visionner final.mp4 du run FR et de dicter 3 défauts (ou « non visionnée ») ; consigne-les dans STATE.md pour les étapes 15 et 16.
8. Commit « étape 13.2 : première vidéo complète ».
</tache>

<contraintes>
- Aucune modification manuelle des fichiers d'un run entre deux étapes : tout passe par le code.
- Trois images regardées au maximum.
- Si un run dépasse 90 minutes de calcul, note-le : c'est une donnée pour le jalon serveur, pas un échec.
</contraintes>

<criteres_de_validation>
Montre : pour chaque run, ls du dossier (final.mp4, thumbnail.png, metadata.json, manifest.json) ; python -c qui affiche du manifeste : statut, temps total, coût, nombre de variantes de titres et de miniatures, contains_synthetic_media + reason ; python -c qui valide metadata.json (longueur du titre, présence des chapitres, de la mention IA, de l'attribution) ; identify ou python PIL pour la taille de thumbnail.png.
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 13.2 terminée, JALON PHASE 1 ATTEINT (identifiants des deux runs, durée, temps total, coût), 3 défauts notés par Thomas, questions ouvertes. Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + extraits INTERFACES/CONFORMITE + REFERENTIEL + cli.py | 9 000 |
| Prompt (~1 500 mots) | 2 200 |
| Écriture titles_v1.py (≈ 100 lignes) | 1 300 |
| Écriture thumbnail.py (≈ 200 lignes) | 2 700 |
| Écriture metadata.py (≈ 180 lignes) | 2 400 |
| Écriture run.py + CLI (≈ 200 lignes) | 2 700 |
| Deux exécutions complètes (extraits tail -40) | 5 000 |
| Inspection de 3 images | 4 500 |
| Corrections et relances --from | 4 500 |
| Mise à jour STATE.md + résumé | 800 |
| Sous-total | 53 100 |
| Marge +25 % | 13 275 |
| **Total** | **66 375 tk — 33,2 %** |

## Étape 14 — Ouvrir le canal officiel : upload privé, OAuth en production, dépôt de l'audit API

**Objectif.** Rendre la publication par l'API possible et lancer l'horloge de l'audit Google : consentement OAuth « En production », politique de confidentialité hébergée gratuitement, jeton pour la chaîne de test, premier upload privé du MP4 de l'étape 13.2 avec métadonnées et label synthétique, dossier d'audit déposé.
**Pourquoi maintenant.** L'audit prend des semaines à des mois et tout upload d'un projet non audité reste privé ; le déposer à la fin de la phase 1 laisse les phases 2 et 3 pour l'obtenir. Les jetons d'un projet en mode « Testing » expirent sous 7 jours : le daemon de la phase 4 en a besoin en production.
**Valeur créée.** Thèse n° 5 (chemin de publication conforme) et n° 4 (les chaînes multiples s'ajoutent par un jeton chacune).
**Pré-requis.** Étape 13.2 terminée · projet GCP « bms-factory » (étape 2) · un compte Google BMS avec une chaîne de test (Brand Account) et vérification téléphonique faite · Thomas disponible 30 minutes en navigateur.
**Sous-agents.** 1 — état 2026 des règles de l'écran de consentement OAuth pour les scopes YouTube (sensibles, Testing vs Production, application non vérifiée en production : avertissements, plafond d'utilisateurs, durée des jetons), contenu attendu du formulaire d'audit et de demande de quota (champs, vidéo de démonstration, URL de politique de confidentialité), création d'une chaîne Brand Account et vérification. 450 mots maximum.
**Livrables.** `factory/publish/oauth.py`, `factory/publish/upload_min.py`, `docs/PRIVACY.md` (+ URL publique), `docs/AUDIT-API.md`, `secrets/tokens/<channel>.json` (hors git), un identifiant de vidéo privée.
**Poids disque.** 0.
**Terminé quand.** `secrets/tokens/bms-test.json` existe et un appel `channels.list?mine=true` renvoie la chaîne · une vidéo privée est visible dans YouTube Studio avec titre, description, miniature (si le compte est vérifié), sous-titres et `containsSyntheticMedia` renseigné (vérifié par `videos.list`) · le formulaire d'audit est soumis (date dans `STATE.md`) ou le blocage exact est documenté · la page de confidentialité est en ligne.

**Prompt à copier-coller :**

````text
Tu es ingénieur intégration Google Cloud / YouTube Data API ; tu connais OAuth 2.0 pour applications installées et le processus d'audit des services API YouTube.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local. Contrainte n° 1 de la publication : toute vidéo uploadée par un projet API non audité est forcée en privé, et l'audit (gratuit) prend des semaines. Cette session ouvre le canal officiel : consentement OAuth en production (sinon les jetons expirent sous 7 jours), politique de confidentialité hébergée sans frais, jeton pour la chaîne de test, upload privé de la première vidéo (étape 13.2) avec toutes les métadonnées et le label de contenu synthétique, puis dépôt du dossier d'audit décrit honnêtement : outil interne de publication et de lecture des statistiques des chaînes de BMS. Aucune automatisation de navigateur : ce serait une violation des conditions d'utilisation.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 14 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 14 \|^## Phase 2 " ROADMAP.md puis Read en offset/limit.
2. STATE.md
3. docs/CONFORMITE.md — sections 1, 2 et 3.
4. Le metadata.json du run FR de l'étape 13.2 (court).
</demarrage>

<sous_agents>
Lance 1 sous-agent (recherche web, sources developers.google.com, support.google.com, console.cloud.google.com/apis docs) : (1) écran de consentement OAuth en 2026 pour les scopes youtube.upload, youtube, yt-analytics.readonly, yt-analytics-monetary.readonly : statut Testing vs In production, ce qu'implique « application non vérifiée » en production (avertissement, plafond de 100 utilisateurs, durée des refresh tokens), si une vérification de marque est exigée pour nos propres comptes ; (2) formulaire « YouTube API Services – Audit and Quota Extension » : URL, champs, pièces attendues (description d'usage, vidéo de démonstration, politique de confidentialité, conditions d'utilisation), délais rapportés ; (3) création d'une chaîne Brand Account, transfert de propriété à un compte BMS, vérification téléphonique et fonctionnalités qu'elle débloque. 450 mots maximum, points numérotés avec URL.
</sous_agents>

<tache>
1. Console Google Cloud (Thomas en navigateur, guide-le pas à pas et attends ses retours) : projet bms-factory → activer YouTube Analytics API et YouTube Reporting API en plus de Data API v3 → « Écran de consentement OAuth » : type Externe, nom « BMS Factory », e-mail d'assistance BMS, domaine autorisé de la page de confidentialité, scopes listés ci-dessus, statut de publication « En production » → « Identifiants » → client OAuth de type « Application de bureau » → télécharger le JSON dans secrets/client_secret.json (hors git ; vérifie que .gitignore couvre secrets/).
2. Politique de confidentialité : écris docs/PRIVACY.md (en anglais et en français : qui est l'opérateur, quelles données Google sont lues et écrites, stockage local uniquement, pas de partage, durée de conservation conforme aux conditions de l'API, contact, date) ; Thomas la publie sans frais sur une page Google Sites ou GitHub Pages ; l'URL va dans STATE.md et dans l'écran de consentement.
3. factory/publish/oauth.py : flux « installed app » (google-auth-oauthlib) → secrets/tokens/<channel_id>.json, rafraîchissement automatique, commande `factory publish auth --channel bms-test` (Thomas se connecte avec le compte de la chaîne de test et choisit la chaîne) ; test : channels.list mine=true affiche l'identifiant et le titre de la chaîne. Ajoute config/channels/bms-test.yaml (chaîne de test, style illustre, lang fr).
4. factory/publish/upload_min.py : `factory publish upload --run <id> --channel bms-test` → videos.insert résumable (snippet : title, description, tags, categoryId, defaultLanguage ; status : privacyStatus=private, selfDeclaredMadeForKids=false, containsSyntheticMedia depuis metadata.json ; notifySubscribers=false), puis thumbnails.set (si le compte est vérifié ; sinon avertissement), captions.insert (subtitles.srt, langue) ; écrit publish.json (youtube_video_id, url, quota_units, timestamps) et le manifeste ; vérification videos.list (status.privacyStatus, status.containsSyntheticMedia, processingDetails).
5. Exécute l'upload du run FR de l'étape 13.2. Demande à Thomas de confirmer dans YouTube Studio que la vidéo apparaît en privé avec ses métadonnées.
6. docs/AUDIT-API.md : dossier d'audit prêt à copier dans le formulaire : description de l'application (outil interne de BMS pour publier ses propres vidéos et lire ses propres statistiques ; pas de collecte sur des tiers ; pas de partage de données ; stockage local ; suppression des données conformément aux conditions), justification scope par scope, quota demandé (chiffré : uploads par jour, lectures par jour), scénario de la vidéo de démonstration de 60 s à enregistrer par Thomas (écran : commande auth, commande upload, résultat dans Studio), URL de la politique et des conditions d'utilisation, checklist de conformité aux Developer Policies. Thomas soumet le formulaire ; date de soumission dans STATE.md. Si le formulaire exige une pièce indisponible, documente le blocage exact.
7. Commit « étape 14 : canal officiel ouvert » (aucun secret dans le commit : git status et git diff --cached pour vérifier).
</tache>

<contraintes>
- Jamais de secret ni de jeton dans la conversation, les logs ou le dépôt.
- Aucune automatisation de navigateur ; Thomas fait les clics.
- Une seule vidéo uploadée à cette étape ; elle reste privée.
</contraintes>

<criteres_de_validation>
Montre : ls secrets/ (client_secret.json, tokens/bms-test.json) ; la sortie de channels.list mine=true ; la sortie de videos.list pour la vidéo uploadée (privacyStatus, containsSyntheticMedia) ; l'URL de la page de confidentialité (curl -sI … | head -1 : 200) ; la date de soumission de l'audit ou le blocage.
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 14 terminée, phase 1 close, identifiant de la vidéo privée, date de dépôt de l'audit (rappel : vérifier la boîte mail BMS chaque semaine ; à réception, passer youtube.audit_passed à true dans la config de la chaîne), compte et chaîne utilisés, questions ouvertes pour Alek (comptes Google des futures chaînes, numéros de téléphone pour vérification). Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + CONFORMITE §1-3 + metadata.json | 8 000 |
| Prompt (~1 500 mots) | 2 200 |
| 1 rapport de sous-agent | 1 300 |
| Écriture oauth.py (≈ 120 lignes) | 1 600 |
| Écriture upload_min.py (≈ 150 lignes) | 2 000 |
| Écriture PRIVACY.md + AUDIT-API.md (≈ 200 lignes) | 2 700 |
| Échanges guidés avec Thomas (console) et sorties API | 3 000 |
| Exécutions et corrections | 3 500 |
| Mise à jour STATE.md + résumé | 800 |
| Sous-total | 43 100 |
| Marge +25 % | 10 775 |
| **Total** | **53 875 tk — 26,9 %** |

## Phase 2 — Qualité mesurable et rétention

**Objectif de la phase.** Mesurer objectivement chaque vidéo produite face aux cibles du registre, bloquer sous le seuil, fabriquer la rétention (hook, boucles, ruptures, densité) et livrer le moteur « documentaire » qui répond au besoin de réalisme avec des vidéos libres de droits.
**Jalon de phase.** Trois vidéos (dont une en style documentaire) passent `factory qc` avec un score ≥ seuil de leur niche · le rythme de coupe mesuré par détection de plans est à ±15 % de la cible de niche sur chacune · un script rejeté par le vérificateur de rétention est régénéré automatiquement.

## Étape 15 — Banc d'évaluation objectif et portillon qualité

**Objectif.** Livrer `factory qc` : un banc qui mesure une vidéo produite (rythme de coupe, durée, densité de coupes, lisibilité du texte, niveaux sonores, silences, débit de parole, présence et forme du hook, variété visuelle, couverture des sous-titres), la compare aux cibles de sa niche et rend un score avec verdict bloquant.
**Hérité de l'étape 5.2 (mesuré, `RESULTATS.md` § 2.12).** Deux contrôles par plan sont **écrits, exécutés et concluants** — à reprendre dans le portillon : **cadrage** (marge uniforme sur les quatre bords : encadré ou pleine page ; a désigné exactement le plan intrus d'une série de 8) et **dérive de palette** (intersection d'histogrammes teinte × saturation contre la charte de la série). Code : `benchmarks/controles_plan.py`. **Et un avertissement à ne pas perdre : le portillon ne pourra pas être complet.** Un troisième contrôle, la détection d'éléments détachés, a été écrit, exécuté et **a échoué par principe** — sur 8 plans, 3 séparations légitimes sur 13 partagent la signature géométrique de la fautive. **L'anatomie fausse, les éléments détachés et la dérive d'identité d'un plan à l'autre ne sont pas atteignables sans modèle vision-langage**, qui ne tient ni dans le budget mémoire ni dans le 0 €. Le portillon doit donc **déclarer ce qu'il ne couvre pas**, et la relecture humaine rester prévue pour ces classes-là tant que l'étape 6 n'a pas tranché entre relecture par plan, juge VLM sur serveur, et réduction d'exposition par le choix de sujet.
**Pourquoi maintenant.** Sans mesure objective, la qualité progresse au feeling et stagne ; le banc est aussi la fonction de coût que les étapes 16, 17, 26 optimisent.
**Valeur créée.** Thèse n° 3 : les cibles chiffrées du registre sont vérifiées sur le rendu, pas seulement citées.
**Pré-requis.** Étape 13.2 terminée · deux runs exportés · `registre/REFERENTIEL.json`.
**Sous-agents.** Vague 1 : (A) métriques mesurables sur un MP4 sans modèle lourd (paramètres PySceneDetect avec transitions, ebur128, silencedetect, hachage perceptuel, OCR optionnel avec tesseract, mesure de contraste) ; vague 2 : (B) contradicteur sur la formule de score.
**Livrables.** `factory/eval/bench.py`, `factory/eval/metrics/*.py`, `config/qc.yaml`, `docs/QC.md`, pour chaque run : `qc.json`.
**Poids disque.** 0.
**Terminé quand.** `factory qc --run <id>` produit `qc.json` avec ≥ 8 métriques (valeur, cible, score partiel), un score global 0-100 et un verdict · un fichier volontairement défectueux (audio coupé, durée moitié) est rejeté avec les raisons · les deux runs de la phase 1 sont notés et leurs faiblesses listées · `docs/QC.md` documente métriques, cibles, pondérations, seuils et la calibration.

**Prompt à copier-coller :**

````text
Tu es ingénieur qualité vidéo ; tu transformes des cibles éditoriales en mesures automatiques reproductibles.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local. Le registre donne des cibles chiffrées par niche (rythme de coupe médian, durée, débit, forme du hook, motifs de miniature). Cette session construit le banc qui mesure chaque vidéo produite face à ces cibles et le portillon qui bloque la publication sous le seuil. Le score sera plus tard confronté aux vues réelles (étape 26) : il doit être décomposé, traçable et honnête, pas un chiffre magique. Rien ne se publie sans passer ce banc.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 15 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 15 \|^## Étape 16 " ROADMAP.md puis Read en offset/limit.
2. STATE.md (les 3 défauts notés par Thomas à l'étape 13.2)
3. registre/REFERENTIEL.md (entier)
4. docs/INTERFACES.md — contrats qc.json, shotlist.json, manifest (grep -n).
5. factory/steps/export.py (les mesures déjà faites : scenedetect, ebur128, images extraites).
</demarrage>

<sous_agents>
Vague 1 — 1 sous-agent (recherche web + lecture de la documentation des bibliothèques) : comment mesurer sans modèle lourd, sur un MP4 1080p : coupes avec PySceneDetect (ContentDetector vs AdaptiveDetector, seuils, gestion des fondus courts), loudness et true peak (ebur128), silences (silencedetect), variété visuelle (hachage perceptuel entre images consécutives, imagehash), contraste et taille du texte (à partir des paramètres de rendu ou par OCR tesseract sur images extraites), débit de parole (words.json), détection de mouvement (différence d'images). Pour chaque métrique : commande ou fonction, coût en temps pour une vidéo de 10 min, piège. 450 mots maximum.
Vague 2 — après ton brouillon de config/qc.yaml et docs/QC.md, 1 contradicteur : la formule de score récompense-t-elle des artefacts (coupes inutiles, texte omniprésent) ? les seuils sont-ils atteignables par les vidéos du registre elles-mêmes ? une métrique dépend-elle d'un choix de rendu plutôt que de la qualité perçue ? qu'est-ce qui manque pour prédire la rétention ? 400 mots maximum, « Problème → correction ».
</sous_agents>

<tache>
Réfléchis avant de coder : chaque métrique doit avoir une cible issue de REFERENTIEL.json (ou de config/qc.yaml quand le registre ne la donne pas), une fonction de score partielle (100 à la cible, décroissante avec l'écart, 0 hors plage), un poids, et éventuellement un statut « bloquant ».
1. factory/eval/metrics/ : un module par famille — coupes (n_scenes, rythme mesuré, p10/p90 des durées de plan, plans > 3× cible, rythme du hook sur 15 s), durée (vs cible de niche), audio (LUFS, true peak, silences > 1,5 s, ratio musique/voix estimé sur un segment sans voix), parole (mots/min depuis words.json vs référentiel), hook (dans les 3 premières secondes : ≥ 1 changement visuel ou mouvement, texte présent, première phrase du script ≤ hooks.longueur_mots.mediane de la niche (registre/REFERENTIEL.json) et conforme aux règles du type de hook enregistré), lisibilité (taille du texte en pixels depuis les paramètres de rendu ≥ 3,5 % de la hauteur, contraste ≥ 4,5:1 mesuré sur les images extraites, texte à l'écran ≤ 6 mots), variété (distance de hachage perceptuel médiane entre plans consécutifs, part de plans quasi identiques), sous-titres (couverture ≥ 90 % des secondes parlées, aucune ligne > 42 caractères), structure (segment sponsor pas dans les 60 premières secondes, boucle ouverte payée).
2. factory/eval/bench.py : `factory qc --run <id>` → calcule tout, écrit qc.json {metrics: {nom: {value, target, score, weight, blocking, note}}, score, verdict: PASS | FAIL, reasons[], version} ; pondérations et seuils dans config/qc.yaml (par défaut : coupes 25, hook 20, durée 10, audio 15, lisibilité 10, variété 10, sous-titres 5, structure 5 ; seuil PASS 70 ; bloquants : LUFS hors [-16, -12], durée < 60 % ou > 150 % de la cible, sous-titres absents, un plan > 3× cible, hook sans changement visuel, sponsor avant 60 s) ; surcharges par niche possibles ; met à jour le manifeste (qc_score, qc_verdict) et la table runs.
3. Calibration : (a) crée tests/fixtures/qc_cible.json représentant une vidéo idéale aux valeurs cibles et vérifie qu'elle score ≥ 95 ; (b) fabrique une vidéo défectueuse à partir d'un run (ffmpeg : audio à -30 LUFS, durée tronquée à 45 %) et vérifie le FAIL avec raisons ; (c) note les deux runs de la phase 1 et liste leurs 3 métriques les plus faibles.
4. docs/QC.md : chaque métrique (définition, méthode, cible et source, score partiel, poids, bloquant ou non, limites), la formule globale, les seuils par niche, la procédure de recalibration prévue à l'étape 26 (corrélation score ↔ vues), et les résultats de calibration de cette session.
5. Lance le contradicteur, corrige, consigne « Objections » dans QC.md.
6. Commit « étape 15 : banc et portillon ».
</tache>

<contraintes>
- Aucun modèle IA lourd dans le banc (il doit tourner en < 3 minutes sur une vidéo de 10 minutes) ; le LLM n'intervient pas ici.
- Regarde au plus 2 images (pour valider la mesure de contraste).
- Toute mesure a une unité, une cible et une source.
</contraintes>

<criteres_de_validation>
Montre : cat qc.json d'un run (structure complète) ; le score de la fixture idéale ; le verdict et les raisons de la vidéo défectueuse ; les scores des deux runs de la phase 1 avec leurs 3 métriques les plus faibles ; le temps d'exécution du banc.
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 15 terminée, scores des runs, métriques faibles récurrentes (entrées pour 16 et 17), seuils choisis, objections non résolues. Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + REFERENTIEL.md + extraits INTERFACES + export.py | 9 500 |
| Prompt (~1 400 mots) | 2 000 |
| 1 rapport de sous-agent + 1 contradicteur | 2 600 |
| Écriture metrics/*.py + bench.py (≈ 350 lignes) | 4 700 |
| Écriture qc.yaml + CLI (≈ 100 lignes) | 1 300 |
| Écriture QC.md (≈ 150 lignes) | 2 000 |
| Exécutions et calibration (extraits) | 3 500 |
| Corrections | 3 000 |
| Mise à jour STATE.md + résumé | 800 |
| Sous-total | 47 400 |
| Marge +25 % | 11 850 |
| **Total** | **59 250 tk — 29,6 %** |

## Étape 16 — Ingénierie du hook et de la rétention

**Objectif.** Rendre la rétention paramétrée, générée et vérifiée : bibliothèque de patrons de hook issus du registre, boucles ouvertes plantées et payées, ruptures de rythme programmées, densité d'information mesurée, vérificateur de script qui rejette et fait régénérer avant la voix.
**Pourquoi maintenant.** Le banc (15) mesure ; cette étape agit sur la cause principale de l'abandon : les 15 premières secondes et le creux du milieu.
**Valeur créée.** Thèse n° 3 : ce qui sépare CasiCreativo de Health Snippet devient du code.
**Pré-requis.** Étape 15 terminée · `registre/REFERENTIEL.json` (taxonomie des hooks) · transcriptions du registre.
**Sous-agents.** 2 en parallèle : (A) patrons de hook à emplacements et cadence des ruptures extraits des 60 meilleures transcriptions du registre ; (B) méthode de mesure de la densité d'information d'un script (faits par minute) et valeurs de référence sur les transcriptions (meilleures vs médianes).
**Livrables.** `factory/retention/hooks.py`, `loops.py`, `interrupts.py`, `density.py`, `verify.py`, `factory/retention/patterns_<lang>.yaml`, `tests/test_retention.py`, intégration dans `factory script` et dans le banc.
**Poids disque.** 0.
**Terminé quand.** `factory script` refuse un script qui viole les règles et le régénère (≤ 3 essais) avec le retour d'erreur · un nouveau run a un hook du type tiré, ≥ 2 boucles ouvertes payées, une rupture par tranche de N secondes, une densité ≥ cible de niche · `qc.json` inclut les métriques hook et densité · ≥ 10 tests de règles passent.

**Prompt à copier-coller :**

````text
Tu es spécialiste de la rétention YouTube et développeur Python ; tu transformes des observations éditoriales en règles génératives et en tests.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local. Le registre montre que ce qui distingue une chaîne qui décolle d'une chaîne qui meurt n'est pas l'outillage mais les trois premières secondes, la densité d'information, les ruptures de rythme et les boucles ouvertes. Cette session les paramètre, les fait générer par le LLM local et les vérifie automatiquement avant la synthèse vocale : un script qui échoue est régénéré avec le motif exact. La taxonomie des hooks et les parts par niche sont dans registre/REFERENTIEL.json ; les transcriptions du registre (registre/data/*/transcripts) sont la matière première (usage recherche uniquement, docs/CONFORMITE.md §9).
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 16 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 16 \|^## Étape 17 " ROADMAP.md puis Read en offset/limit.
2. STATE.md (métriques faibles notées à l'étape 15)
3. registre/REFERENTIEL.json — hooks_taxonomie et, pour 2 niches, hooks.parts et mots_par_minute (python -c).
4. factory/steps/script.py et factory/prompts/script_fr.md (entiers).
5. docs/QC.md — métriques hook et structure.
</demarrage>

<sous_agents>
Lance 2 sous-agents en parallèle, un seul envoi, 600 mots maximum chacun, format tableaux et listes :
- Agent A : sur les transcriptions des 60 vidéos les plus vues du registre (registre/data/*/transcripts, choisir par vues dans videos.json), extrais pour chaque type de hook de la taxonomie un patron à emplacements (ex. « Et si {croyance commune} était {contraire} ? En {durée}, je vous montre {promesse}. ») avec 3 exemples verbatim, la longueur en mots ; repère les marqueurs de boucle ouverte et leur position (secondes) ; estime la cadence des ruptures de sujet (changement de thème, question au spectateur, statistique) en secondes par niche ; liste 20 formulations à proscrire (« dans cette vidéo », « bonjour à tous », « n'oubliez pas de vous abonner » en ouverture).
- Agent B : propose une méthode de mesure de la densité d'information d'un script (nombre de faits vérifiables, chiffres, noms, comparaisons par minute) implémentable par règles et par un juge LLM local avec grille ; calcule-la sur 20 transcriptions des meilleures vidéos et 20 de vidéos médianes du registre, par niche ; rapporte la cible (médiane des meilleures) et l'écart avec les médianes.
</sous_agents>

<tache>
1. factory/retention/patterns_<lang>.yaml (fr, en, es, it) : patrons de hook par type (à partir du rapport A, adaptés par langue), formulations proscrites, marqueurs de boucle ouverte, phrases de paiement.
2. factory/retention/hooks.py : tirage du type (parts de la niche, graine du run), génération de 3 hooks du type par le LLM avec le patron, score par règles (≤ hooks.longueur_mots.mediane de la niche, pas de formulation proscrite, contient l'élément clé du type : question, chiffre, enjeu, contradiction), duel LLM entre les 2 meilleurs, choix enregistré dans le manifeste (hook_type, hook_candidates, hook_chosen).
3. factory/retention/loops.py : planter une boucle ouverte à la fin du segment 1 ou 2 (promesse d'une révélation), la payer avant la conclusion ; vérifier plantation et paiement par recherche des marqueurs et par cohérence sémantique (juge LLU court) ; interrupts.py : toutes les N secondes (N = 4 × rythme de coupe cible, borné 20-45 s) marquer un segment avec un type de rupture (question au spectateur, statistique, changement visuel, mini-récit) que shotlist.py consomme déjà via le champ interrupt ; density.py : faits par minute par règles (chiffres, entités, comparatifs) et juge LLM avec grille du rapport B, cible par niche dans config/niches ; si sous la cible, redemande au LLM d'ajouter des faits tirés de research.json (jamais inventés : chaque fait ajouté doit citer une source de research.json).
4. factory/retention/verify.py : vérification complète d'un script (hook, boucles, ruptures, densité, formulations proscrites, sponsor pas avant 60 s, texte à l'écran ≤ 6 mots, durée estimée ±15 %) → liste d'infractions lisibles ; intégré à factory/steps/script.py : après génération, verify → si infractions, régénération ciblée avec les infractions dans le prompt (3 essais), puis échec explicite du run (statut failed, raison).
5. Banc : ajoute aux métriques hook/structure de factory/eval la conformité au type de hook, le nombre de boucles payées et la densité (valeur du manifeste) ; mets à jour docs/QC.md.
6. tests/test_retention.py : règles de hook (bons et mauvais exemples), détection de formulations proscrites, plantation et paiement de boucle, planification des ruptures, densité par règles (≥ 10 tests).
7. Exécute `factory run --channel bms-science-fr --from script` sur un run existant ou un nouveau ; compare avant/après (mots, densité, hook, boucles) ; lance `factory qc`.
8. Commit « étape 16 : hook et rétention ».
</tache>

<contraintes>
- Aucun fait inventé : la densité augmente avec des faits sourcés de research.json.
- Les transcriptions du registre servent à extraire des patrons, jamais à copier des phrases dans un script.
- Un seul modèle en mémoire ; les appels LLM restent des sous-processus.
</contraintes>

<criteres_de_validation>
Montre : uv run pytest tests/test_retention.py -q ; le manifeste du run (hook_type, hook_chosen, boucles, ruptures, densité vs cible) ; les infractions détectées lors d'une régénération (log) ; le qc.json avec les nouvelles métriques.
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 16 terminée, cibles de densité par niche, taux de régénération observé, temps ajouté par run. Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + extraits REFERENTIEL + script.py + prompts + QC.md | 9 500 |
| Prompt (~1 450 mots) | 2 200 |
| 2 rapports de sous-agents (600 mots) | 2 600 |
| Écriture patterns yaml (4 langues, ≈ 160 lignes) | 2 100 |
| Écriture hooks.py + loops.py + interrupts.py (≈ 320 lignes) | 4 300 |
| Écriture density.py + verify.py (≈ 270 lignes) | 3 600 |
| Intégration script.py + banc (≈ 100 lignes) | 1 500 |
| Tests (≈ 120 lignes) | 1 600 |
| Exécutions et lecture des scripts avant/après | 5 000 |
| Corrections | 3 000 |
| Mise à jour STATE.md + résumé | 800 |
| Sous-total | 54 200 |
| Marge +25 % | 13 550 |
| **Total** | **67 750 tk — 33,9 %** |

## Étape 17 — Moteur « documentaire » (banques libres) et rythme de coupe vérifié

**Objectif.** Livrer le moteur de style « documentaire » : vidéos et images réelles issues de banques libres de droits, sélectionnées par mots-clés, tracées avec licence et attribution, montées au rythme de la niche ; vérifier par le banc que le rythme mesuré est à ±15 % de la cible sur les deux styles.
**Pourquoi maintenant.** C'est la réponse stratégique au besoin de réalisme (docs/STYLES.md) et le second style nécessaire pour valider que l'interface `StyleEngine` est réellement interchangeable.
**Valeur créée.** Thèse n° 3 (rythme vérifié sur du footage réel) et n° 5 (attribution automatique).
**Pré-requis.** Étape 15 terminée · clés API gratuites Pexels et Pixabay créées par Thomas (sans carte) dans `.env`.
**Sous-agents.** 1 — API vidéo de Pexels, Pixabay, Openverse, Internet Archive et NASA en 2026 : points d'entrée, paramètres (orientation, durée minimale, taille), quotas, conditions de licence et forme exacte de l'attribution attendue.
**Livrables.** `factory/assets/stock.py`, `factory/styles/documentaire.py`, `config/styles/documentaire.yaml`, `workspace/library/stock/`, un run complet en style documentaire avec `qc.json`.
**Poids disque.** ≈ 0,5-1 Go de clips en bibliothèque (suivi dans le ledger).
**Terminé quand.** Un run `bms-histoire-fr` en style documentaire passe `factory qc` · rythme mesuré à ±15 % de la cible sur ce run et sur un run illustré (mesures dans `STATE.md`) · aucun plan sans asset (le repli est testé en forçant un mot-clé sans résultat) · chaque clip a `licence.json` et le bloc d'attribution apparaît dans `metadata.json`.

**Prompt à copier-coller :**

````text
Tu es monteur documentaire et développeur ; tu construis des séquences à partir de banques de vidéos libres, avec une traçabilité de licence irréprochable.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local. Le photoréalisme généré n'est pas viable localement (docs/STYLES.md) : le style « documentaire » l'obtient avec des vidéos et images réelles, libres de droits (Pexels, Pixabay, Openverse, Internet Archive, NASA), choisies par mots-clés à partir des intentions visuelles du script, montées au rythme de coupe de la niche, avec attribution automatique. Chaque asset porte sa licence (docs/CONFORMITE.md §8). Cette session vérifie aussi, via le banc, que le rythme mesuré respecte la cible sur les deux styles disponibles.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 17 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 17 \|^## Phase 3 " ROADMAP.md puis Read en offset/limit.
2. STATE.md
3. docs/CONFORMITE.md §8 ; outils/LICENCES.md — lignes des banques (grep -n "Pexels\|Pixabay\|Openverse\|Archive\|NASA").
4. factory/styles/illustre.py et factory/assets/images.py (entiers) ; docs/INTERFACES.md — contrat Asset.
5. config/channels/bms-histoire-fr.yaml.
</demarrage>

<sous_agents>
Lance 1 sous-agent (recherche web, documentation officielle des API) : pour Pexels (vidéos et photos), Pixabay (vidéos), Openverse (images, audio), Internet Archive (films du domaine public) et NASA (images et vidéos) — point d'entrée de recherche, paramètres utiles (orientation paysage, durée minimale, résolution ≥ 1080p, tri), format de réponse (champ des fichiers et résolutions), clé gratuite sans carte (procédure), quotas par heure et par mois, licence des contenus et texte d'attribution exact à afficher, restrictions (personnes identifiables, marques). 450 mots maximum, une ligne par point.
</sous_agents>

<tache>
1. Clés : guide Thomas pour créer les clés Pexels et Pixabay (gratuites, sans carte) et les mettre dans .env (PEXELS_KEY, PIXABAY_KEY). Openverse et Internet Archive fonctionnent sans clé.
2. factory/assets/stock.py : mots-clés = LLM transforme visual_intent en 3 requêtes anglaises courtes ; chaîne de fournisseurs Pexels → Pixabay → Openverse → Internet Archive/NASA → repli image générée + Ken Burns (moteur illustré) pour qu'un plan n'échoue jamais ; critères : paysage, ≥ 1080p, durée ≥ durée du plan + 1 s, pas déjà utilisé par la chaîne dans ses 10 derniers runs, pas deux fois dans la vidéo ; téléchargement dans workspace/library/stock/<provider>/<id>.mp4 avec licence.json (fournisseur, URL, auteur, licence, attribution, date) et enregistrement dans assets_library ; cache et réutilisation ; respect des quotas (compteur local, pause si proche de la limite).
3. factory/styles/documentaire.py : StyleEngine « documentaire » : prepare_assets via stock.py ; render_shot : découpe au bon endroit (début du clip ou moment le plus mouvementé estimé par différence d'images), mise à l'échelle et recadrage 1920×1080, léger ralenti ou accéléré (±10 %) pour ajuster, étalonnage discret par LUT de la charte (ffmpeg colorbalance ou lut3d si un fichier .cube libre est fourni), texte à l'écran en bandeau bas (lower third) selon la charte, Ken Burns sur les images fixes ; bandeau « Publicité » sur les plans sponsor ; verify_clip.
4. Attribution : le bloc d'attribution de metadata.py doit lister les assets qui l'exigent (Pexels, Openverse CC-BY, Archive) avec le texte exact ; vérifie que metadata.json le contient.
5. Exécute `factory run --channel bms-histoire-fr --style documentaire` (sujet neuf), journal (tail -40). Lance `factory qc`. Compare cut_rhythm_measured_s à la cible pour ce run et pour le run illustré de la phase 1 (ou un nouveau run illustré si nécessaire) ; si l'écart dépasse 15 %, ajuste shotlist.py (jitter, placement des coupes) ou les seuils de détection du banc (transitions xfade détectées comme deux coupes ?) et documente le réglage dans docs/QC.md.
6. Test de repli : force une requête sans résultat (mot inventé) et vérifie qu'un plan tombe sur le repli image générée sans échec.
7. Regarde 3 images extraites de la vidéo documentaire : cadrage, bandeau, cohérence de l'étalonnage.
8. Commit « étape 17 : moteur documentaire » ; mets à jour le ledger (taille de workspace/library/stock).
</tache>

<contraintes>
- Aucun téléchargement hors des fournisseurs listés ; aucun contenu « éditorial seulement » ou avec personnes identifiables en gros plan.
- Trois images regardées au maximum.
- Respect strict des quotas (Pexels : 200 requêtes/heure) ; journalise le compteur.
</contraintes>

<criteres_de_validation>
Montre : ls clips | wc -l ; la part de plans par fournisseur et par repli (manifeste) ; qc.json (score, verdict, rythme mesuré vs cible) pour les deux styles ; le bloc d'attribution de metadata.json ; le résultat du test de repli ; le compteur de quota.
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 17 terminée, phase 2 close si le jalon est atteint (3 vidéos PASS, rythme ±15 %) sinon ce qui manque, taille de la bibliothèque stock, réglages du banc. Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + CONFORMITE §8 + LICENCES + illustre.py/images.py + config | 9 500 |
| Prompt (~1 400 mots) | 2 200 |
| 1 rapport de sous-agent | 1 300 |
| Écriture stock.py (≈ 280 lignes) | 3 700 |
| Écriture documentaire.py (≈ 200 lignes) | 2 700 |
| Ajustements metadata/shotlist (≈ 60 lignes) | 800 |
| Exécutions run + qc (extraits) | 5 000 |
| Lecture qc.json × 2 et comparaisons | 2 000 |
| Inspection de 3 images | 4 500 |
| Corrections | 4 000 |
| Mise à jour STATE.md + ledger + résumé | 800 |
| Sous-total | 54 500 |
| Marge +25 % | 13 625 |
| **Total** | **68 125 tk — 34,1 %** |

## Phase 3 — Intelligence éditoriale

**Objectif de la phase.** Donner au système sa couche de décision : un entrepôt de données concurrentielles alimenté chaque jour par l'API officielle, une notation des niches (demande, concurrence, monétisation, saisonnalité), l'extraction des sujets qui performent et des trous dans l'offre (y compris les trous multilingues), une file de sujets consommée par le pipeline, et des titres, miniatures et métadonnées en variantes notées. **C'est la phase qui crée le plus de valeur.**
**Jalon de phase.** `factory editorial topics --channel <id>` produit ≥ 20 sujets classés avec score et preuves (vues, vélocité, demande, concurrence) pour 2 chaînes · `factory plan` consomme cette file · `reports/niches.md` classe ≥ 8 niches × 4 langues · un run porte ≥ 8 titres et 3 miniatures notés dans son manifeste.

## Étape 18 — Entrepôt concurrentiel et snapshots quotidiens

**Objectif.** Construire l'entrepôt de données éditoriales dans `factory.db` (chaînes suivies, vidéos, instantanés quotidiens de vues → vélocité) alimenté par l'API officielle dans le respect des quotas, avec une tâche planifiée quotidienne.
**Pourquoi maintenant.** Aucune source gratuite ne fournit l'historique des concurrents : il faut commencer à l'enregistrer soi-même le plus tôt possible ; chaque jour perdu est une donnée perdue.
**Valeur créée.** Thèse n° 1 : la matière première de la décision éditoriale, propriété de BMS, qui s'apprécie avec le temps.
**Pré-requis.** Étapes 2 et 9 terminées · clé API Data v3 · `registre/chaines.csv`.
**Sous-agents.** 1 — API Data v3 au jour de la session : `videos.batchGetStats` (juin 2026) et son compartiment de quota, `playlistItems.list` pour détecter les nouvelles vidéos à moindre coût, champs utiles, ETag, bonnes pratiques de rafraîchissement, obligations de conservation des données stockées (conditions des services API). 450 mots maximum.
**Livrables.** `factory/editorial/collect.py`, `factory/editorial/schema.sql` (migration), `factory editorial collect|top|watch`, `~/Library/LaunchAgents/com.bms.factory.collect.plist`, `reports/collect_<date>.md`.
**Poids disque.** ≈ 0,1 Go par an de base.
**Terminé quand.** Première collecte : ≥ 60 chaînes et ≥ 5 000 vidéos en base avec quota consommé < 6 000 unités (affiché) · une deuxième collecte (forcée) ajoute des instantanés et `factory editorial top --niche science_pop --window 30d` affiche 20 vidéos classées par vélocité à 7 jours · `launchctl list | grep com.bms.factory.collect` montre la tâche chargée · la politique de conservation des données est écrite dans `docs/CONFORMITE.md` §9.

**Prompt à copier-coller :**

````text
Tu es ingénieur données ; tu construis des entrepôts analytiques légers (SQLite) alimentés par des API à quota.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local. Le choix du sujet est la décision la plus rentable du système ; il repose sur des données concurrentielles que personne ne fournit gratuitement en historique. Cette session construit l'entrepôt : liste de chaînes suivies (registre + ajouts), vidéos, instantanés quotidiens de vues, likes et commentaires, d'où l'on dérive la vélocité (vues gagnées par jour, normalisées par l'âge). Alimentation par l'API Data v3 officielle uniquement, sous 6 000 unités par jour (les compartiments 2026 : 10 000 unités/jour, jamais search.list). Une tâche launchd l'exécute chaque nuit.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 18 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 18 \|^## Étape 19 " ROADMAP.md puis Read en offset/limit.
2. STATE.md
3. docs/ARCHITECTURE.md — section base de données ; factory/core/db.py (entier).
4. registre/collecte.py (entier : à réutiliser, pas à réécrire).
5. docs/CONFORMITE.md §9.
</demarrage>

<sous_agents>
Lance 1 sous-agent (recherche web, developers.google.com) : videos.batchGetStats (introduit en juin 2026 : paramètres, nombre d'identifiants par appel, coût, compartiment de quota séparé), playlistItems.list pour détecter les nouvelles vidéos d'une chaîne (coût, tri, pagination), champs de statistics disponibles, comportement des ETag, et obligations des conditions des services API YouTube sur les données stockées (durée de conservation, rafraîchissement, suppression sur demande). 450 mots maximum, points numérotés avec URL.
</sous_agents>

<tache>
1. Migration factory/core/migrations/002_editorial.sql : tables channels_watch (channel_id, handle, title, niche, lang, source (registre | ajout), active, added_at, uploads_playlist_id), videos_ext (video_id, channel_id, published_at, title, description_head (200 caractères), duration_s, tags_json, category_id, thumbnail_url, first_seen_at, last_seen_at), video_snapshots (video_id, snapshot_date, views, likes, comments), channel_snapshots (channel_id, snapshot_date, subscribers, views, video_count), collect_runs (date, units_used, channels_done, videos_new, errors) ; index sur (video_id, snapshot_date) et (channel_id, published_at).
2. factory/editorial/collect.py : `factory editorial watch add|remove|list` (importe registre/chaines.csv au premier lancement) ; `factory editorial collect [--force] [--max-units 6000]` : pour chaque chaîne active — channel_snapshots (channels.list, 1 unité), nouvelles vidéos via playlistItems.list (première page ; pages suivantes seulement au backfill initial jusqu'à 200 vidéos), puis statistiques de toutes les vidéos de moins de 90 jours + un échantillon tournant de 10 % des plus anciennes (batchGetStats si disponible, sinon videos.list par 50) → video_snapshots ; compteur d'unités avec arrêt propre au plafond ; reprise (les chaînes déjà traitées ce jour sont sautées sauf --force) ; journal workspace/logs/collect.log ; rapport reports/collect_<date>.md (chaînes, vidéos nouvelles, unités, erreurs). Réutilise les fonctions de registre/collecte.py (importe-les ou déplace-les dans factory/editorial/yt_api.py).
3. Vues SQL : v_video_velocity (vues à 1, 7, 30 jours par interpolation des instantanés, vélocité = Δvues/Δjours sur les 7 derniers jours, ratio vs médiane de la chaîne à âge égal) ; `factory editorial top --niche X --window 30d [--lang fr]` affiche les 20 vidéos les plus « rapides » avec chaîne, âge, vues, vélocité, ratio.
4. Planification : ~/Library/LaunchAgents/com.bms.factory.collect.plist (StartCalendarInterval entre 03:00 et 05:00, minute aléatoire fixée à l'installation, WorkingDirectory racine, sortie vers workspace/logs/collect_launchd.log) ; `factory editorial collect --install-agent` écrit et charge le plist ; test avec launchctl kickstart.
5. Conservation : ajoute à docs/CONFORMITE.md §9 la politique dérivée du rapport (durée de conservation des données brutes, rafraîchissement, agrégats conservés, suppression) et implémente `factory editorial purge` conforme.
6. Exécute la première collecte (backfill) puis une seconde avec --force ; vérifie les vues.
7. Commit « étape 18 : entrepôt concurrentiel ».
</tache>

<contraintes>
- Jamais search.list ; jamais yt-dlp ; jamais de transcriptions dans ce pipeline.
- Plafond dur de 6 000 unités par exécution.
- Ne lis pas les JSON de l'API dans la conversation : comptages et requêtes SQL ciblées.
</contraintes>

<criteres_de_validation>
Montre : sqlite3 workspace/factory.db "select count(*) from channels_watch; select count(*) from videos_ext; select count(*) from video_snapshots; select * from collect_runs order by date desc limit 2;" ; la sortie de factory editorial top ; launchctl list | grep com.bms.factory ; la section conservation de CONFORMITE.md.
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 18 terminée, volumes en base, unités par collecte, heure planifiée, ce qui reste à surveiller. Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + ARCHITECTURE (db) + db.py + collecte.py + CONFORMITE §9 | 9 000 |
| Prompt (~1 350 mots) | 2 200 |
| 1 rapport de sous-agent | 1 200 |
| Écriture migration + collect.py (≈ 350 lignes) | 4 700 |
| Écriture vues SQL + CLI + plist (≈ 160 lignes) | 2 100 |
| Exécutions (extraits) et requêtes SQL | 4 500 |
| Corrections | 3 000 |
| Addendum CONFORMITE + STATE.md + résumé | 1 600 |
| Sous-total | 46 300 |
| Marge +25 % | 11 575 |
| **Total** | **57 875 tk — 28,9 %** |

## Étape 19 — Détection et notation de niches

**Objectif.** Noter chaque niche candidate, par langue, sur la demande (signaux gratuits : Wikimedia, autocomplete YouTube, Google Trends si accès), la concurrence (entrepôt : chaînes actives, vélocité médiane, part de percées), le potentiel de monétisation (configuration : programmes d'affiliation disponibles par langue, bandes de CPM documentées) et la saisonnalité ; produire un classement avec preuves.
**Pourquoi maintenant.** Le choix de niche précède le choix de sujet ; les chaînes de BMS doivent être placées là où la demande dépasse l'offre.
**Valeur créée.** Thèse n° 1 : le système sait où produire, pas seulement quoi.
**Pré-requis.** Étape 18 terminée (entrepôt alimenté ≥ 2 jours).
**Sous-agents.** Vague 1 : (A) signaux de demande gratuits au jour de la session (API Wikimedia Pageviews : appels, User-Agent, limites ; endpoint d'autocomplete YouTube : paramètres de langue et de région ; API Google Trends officielle : statut de l'alpha et candidature ; Keyword Planner sans dépense) avec exemples d'appels ; vague 2 : (B) contradicteur sur la formule de notation.
**Livrables.** `factory/editorial/demand.py`, `factory/editorial/niches.py`, `config/editorial.yaml` (pondérations), `reports/niches.md`, table `niche_scores`.
**Poids disque.** 0.
**Terminé quand.** `reports/niches.md` classe ≥ 8 niches × 4 langues avec les 4 sous-scores, l'indice de saisonnalité (meilleurs mois) et des liens de preuve · `niche_scores` contient une ligne par (niche, langue, date) · les appels Wikimedia portent un User-Agent identifiant · objections du contradicteur traitées · exécution < 30 minutes.

**Prompt à copier-coller :**

````text
Tu es analyste de marché quantitatif ; tu construis des scores composites à partir de sources gratuites et tu documentes leurs biais.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local. Avant de choisir des sujets, le système doit savoir dans quelles niches et quelles langues la demande dépasse l'offre et où la monétisation est possible. Cette session construit la notation des niches à partir de : signaux de demande gratuits (Wikimedia Pageviews, autocomplete YouTube, Google Trends si l'accès à l'API officielle est obtenu), l'entrepôt concurrentiel (étape 18), une configuration de monétisation renseignée par l'humain (programmes d'affiliation accessibles par langue, bandes de CPM documentées avec source), et une saisonnalité mensuelle. Reddit est exclu (API payante pour usage commercial) ; aucun scraping.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 19 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 19 \|^## Étape 20 " ROADMAP.md puis Read en offset/limit.
2. STATE.md
3. factory/editorial/collect.py — vues SQL disponibles (grep -n "CREATE VIEW\|def ") ; config/niches/*.yaml (liste et un exemple).
4. registre/REFERENTIEL.md — niches monétisables scannées.
</demarrage>

<sous_agents>
Vague 1 — 1 sous-agent (recherche web, documentation officielle) : (1) API Wikimedia Pageviews (per-article, aggregate ; projets fr/en/es/it ; granularité mensuelle ; limites 2026 ; User-Agent exigé) avec un exemple d'URL ; (2) endpoint d'autocomplete de YouTube (suggestqueries) : paramètres ds, client, hl, gl, format de réponse, limites observées, statut (non documenté) ; (3) API Google Trends officielle : statut de l'alpha, procédure de candidature, gratuité ; trendspy en repli et son statut ; (4) Google Keyword Planner sans campagne : niveau de précision des volumes ; (5) toute autre source gratuite de demande fiable pour l'automatisation. 450 mots maximum, une ligne par source : SOURCE | APPEL EXEMPLE | LIMITES | FIABILITÉ 1-5 | URL.
Vague 2 — après ton brouillon de reports/niches.md, 1 contradicteur : biais des proxys de demande (Wikipedia ≠ YouTube), confusion saisonnalité/tendance, scores de monétisation subjectifs, niches surclassées par manque de données, ce qu'un investisseur contesterait. 400 mots maximum, « Problème → correction ».
</sous_agents>

<tache>
1. config/editorial.yaml : pondérations (demande 35, concurrence 25, monétisation 25, faisabilité 15), seeds par niche et par langue (5 à 10 articles Wikipedia et 5 mots-clés par niche, proposés par le LLM puis validés par règles : existence de l'article), grille de monétisation (par niche et langue : programmes d'affiliation disponibles selon docs/CONFORMITE.md et le rapport de l'étape 1, bande de CPM avec source et date, note 1-5), faisabilité (styles disponibles localement adaptés à la niche, sources factuelles gratuites disponibles).
2. factory/editorial/demand.py : Wikimedia Pageviews mensuels sur 24 mois par seed → niveau (médiane 12 mois), tendance (pente 12 mois), indice de saisonnalité par mois (ratio au niveau) ; autocomplete : nombre et diversité des suggestions pour les mots-clés seeds par langue et région (hl, gl) ; Trends si accès (sinon champ null et note) ; cache disque des appels (workspace/cache/demand/), User-Agent « BMS-Factory/1.0 (contact e-mail BMS) ».
3. factory/editorial/niches.py : `factory editorial niches [--lang fr]` → pour chaque (niche, langue) : score de demande (normalisé entre niches), score de concurrence (inverse : nombre de chaînes actives ≥ 1 vidéo/semaine, vélocité médiane des vidéos de moins de 30 jours, part de percées — plus la niche a des percées avec peu de chaînes, mieux c'est), monétisation (grille), faisabilité (grille), score composite, saisonnalité (3 meilleurs mois), preuves (liens et chiffres) → table niche_scores (niche, lang, date, sous-scores, score, evidence_json) et reports/niches.md (classement par langue, tableau, 3 lignes de lecture par niche du top 5, section « limites des données »). Propose 3 niches candidates hors registre (générées par le LLM à partir des percées de l'entrepôt) et note-les de la même façon.
4. Exécute ; vérifie le temps ; lance le contradicteur ; corrige ; consigne « Objections » dans le rapport.
5. Commit « étape 19 : notation des niches ».
</tache>

<contraintes>
- Aucune source payante, aucun scraping de site ; les endpoints non documentés (autocomplete) sont utilisés avec parcimonie (≤ 200 appels par exécution) et marqués comme tels.
- Toute note subjective (monétisation) est dans la configuration, avec sa source, jamais dans le code.
- Chiffres de demande mis en cache : pas de re-téléchargement à chaque exécution.
</contraintes>

<criteres_de_validation>
Montre : sqlite3 "select niche, lang, score from niche_scores where date = (select max(date) from niche_scores) order by score desc limit 12;" ; la tête de reports/niches.md ; le temps d'exécution ; un exemple d'appel Wikimedia avec le User-Agent ; les objections traitées.
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 19 terminée, top 3 niches par langue, sources de demande réellement disponibles (Trends oui/non), limites. Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + extraits collect.py + niches yaml + REFERENTIEL.md | 9 500 |
| Prompt (~1 400 mots) | 2 200 |
| 1 rapport de sous-agent + 1 contradicteur | 2 700 |
| Écriture editorial.yaml (≈ 120 lignes) | 1 600 |
| Écriture demand.py + niches.py (≈ 320 lignes) | 4 300 |
| Exécutions (extraits) et requêtes | 4 000 |
| Lecture du rapport produit (≈ 150 lignes) | 2 000 |
| Corrections | 2 500 |
| Mise à jour STATE.md + résumé | 800 |
| Sous-total | 47 600 |
| Marge +25 % | 11 900 |
| **Total** | **59 500 tk — 29,8 %** |

## Étape 20 — Sujets gagnants, trous dans l'offre, file de sujets

**Objectif.** Détecter les vidéos en percée dans l'entrepôt, regrouper les sujets par similarité (embeddings multilingues locaux), repérer les trous (sujets forts dans une langue et absents dans une autre ; demande élevée et peu de vidéos récentes), générer des angles par sujet et alimenter une file de sujets notée que `factory plan` consomme.
**Pourquoi maintenant.** C'est la brique la plus rentable et la plus souvent absente : le système choisit désormais ses sujets sur des données vivantes, plus seulement sur le registre.
**Valeur créée.** Thèse n° 1 (sujets) et n° 4 (les trous multilingues sont le modèle Thoth automatisé).
**Pré-requis.** Étapes 18 et 19 terminées · `factory/steps/plan.py`.
**Sous-agents.** 1 — modèles d'embeddings multilingues (FR/EN/ES/IT) légers à licence commerciale exécutables sur M2 (sentence-transformers ou MLX), poids, qualité, et méthode de regroupement adaptée à quelques milliers de titres (HDBSCAN, agglomératif). 400 mots maximum.
**Livrables.** `factory/editorial/embed.py`, `factory/editorial/topics.py`, table `topics_queue`, `reports/topics_<channel>.md`, `factory/steps/plan.py` mis à jour, `outils/MODELES.md` (modèle d'embeddings).
**Poids disque.** ≈ 0,5 Go (modèle d'embeddings).
**Terminé quand.** `factory editorial topics --channel bms-science-fr` et `--channel bms-science-en` produisent chacun ≥ 20 sujets en file avec score, angle proposé et preuves (vidéos sources, vélocité, demande, lacune) · `factory plan --channel <id>` prend le meilleur sujet non utilisé et l'enregistre avec `source = topics_queue` · aucun sujet identique sur deux chaînes de même langue · rapport de trous multilingues produit.

**Prompt à copier-coller :**

````text
Tu es data scientist éditorial ; tu détectes ce qui marche chez les concurrents et ce qui manque dans l'offre, avec des méthodes simples et explicables.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local. L'entrepôt (étape 18) enregistre chaque jour les vues des vidéos de ~70 chaînes suivies ; la notation des niches (étape 19) dit où produire. Cette session dit quoi produire : percées (vidéos qui font plusieurs fois la médiane de leur chaîne à âge égal), regroupement des sujets par embeddings multilingues locaux, trous (un sujet fort en anglais absent en français, espagnol ou italien — le modèle des réseaux Thoth ; une demande élevée avec peu de vidéos récentes), angles proposés par le LLM selon la persona de la chaîne, file de sujets notée. `factory plan` consommera cette file en priorité. Les sujets ne sont jamais copiés : ce sont des thèmes, l'angle et le script sont propres à BMS (docs/CONFORMITE.md §4-5).
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 20 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 20 \|^## Étape 21 " ROADMAP.md puis Read en offset/limit.
2. STATE.md
3. factory/steps/plan.py (entier) ; factory/editorial/collect.py — vues SQL (grep -n "CREATE VIEW").
4. docs/INTERFACES.md — contrat Topic et spec.json (grep -n).
5. reports/niches.md — tête du classement pour fr et en.
</demarrage>

<sous_agents>
Lance 1 sous-agent (recherche web + fiches Hugging Face) : modèles d'embeddings de phrases multilingues (fr, en, es, it) légers (< 600 Mo) à licence commerciale (Apache-2.0 ou MIT), exécutables sur M2 via sentence-transformers (CPU/MPS) ou MLX : nom exact, poids, licence, qualité sur des titres courts, vitesse indicative ; méthode de regroupement conseillée pour 3 000 à 10 000 titres (HDBSCAN, agglomératif avec seuil de distance), bibliothèques et licences. 400 mots maximum, tableau puis recommandation.
</sous_agents>

<tache>
1. factory/editorial/embed.py : chargement du modèle retenu (sous-processus, cache des vecteurs dans une table embeddings (video_id, model, vector blob)), fonction embed(texts) ; inscris le modèle dans outils/MODELES.md.
2. factory/editorial/topics.py :
   - percées : depuis v_video_velocity, vidéos dont les vues à 7 ou 30 jours ≥ 3 × la médiane de leur chaîne à âge comparable (fenêtre ±30 % d'âge), sur les 180 derniers jours ;
   - regroupement : embeddings des titres (+ 200 premiers caractères de description) de toutes les vidéos des 180 derniers jours → clusters (algorithme du rapport) ; pour chaque cluster : libellé (LLM, 5 mots), vues totales, nombre de vidéos, nombre de chaînes, part de percées, langues couvertes, âge médian ;
   - trous : (a) multilingues : clusters avec ≥ 2 percées dans une langue et 0 ou 1 vidéo dans une langue cible d'une chaîne BMS ; (b) demande sans offre : clusters (ou seeds de config/editorial.yaml) à demande Wikimedia élevée et < 3 vidéos récentes chez les chaînes suivies ; (c) résurgences : clusters anciens qui regagnent de la vélocité ;
   - notation d'un sujet pour une chaîne : score = pondération (config/editorial.yaml) de la force du cluster, de la vélocité récente, de la lacune (langue, offre), de la demande, du fit niche/style, et malus de similarité avec les sujets déjà produits par BMS (embeddings) ;
   - angles : pour les 30 meilleurs clusters, le LLM propose 2 angles propres (contrarien, comparatif chiffré, récit, test) selon la persona de la chaîne, en langue de la chaîne ;
   - file : table topics_queue (id, channel_id, topic, angle, score, evidence_json, status: proposed | approved | used | banned, created_at, used_by_run) ; `factory editorial topics --channel <id> [--n 30]` remplit et écrit reports/topics_<channel>.md (tableau classé, preuves, section « trous multilingues » avec les sujets EN à décliner en FR/ES/IT) ; `factory editorial topics ban|approve <id>`.
3. factory/steps/plan.py : lit d'abord topics_queue (meilleur sujet proposed ou approved, non utilisé par une chaîne de même langue, similarité < seuil avec les sujets récents de BMS), source = "topics_queue", evidence copiée dans spec.json ; repli sur REFERENTIEL puis --topic.
4. Exécute pour bms-science-fr et bms-science-en ; puis `factory plan --channel bms-science-fr` ; vérifie la source et l'absence de doublon inter-chaînes (crée un plan pour bms-histoire-fr et vérifie qu'un sujet identique n'est pas repris).
5. Commit « étape 20 : sujets et trous ».
</tache>

<contraintes>
- Le modèle d'embeddings tourne seul en mémoire (sous-processus) ; vecteurs mis en cache.
- Un sujet est un thème + un angle propre : aucune reprise de titre de concurrent tel quel dans la file (vérifie par similarité > 0,95 → reformulation).
- Ne lis pas les tables en entier : requêtes ciblées.
</contraintes>

<criteres_de_validation>
Montre : sqlite3 "select channel_id, count(*) from topics_queue where status='proposed' group by channel_id;" (≥ 20 chacun) ; les 5 premières lignes de reports/topics_bms-science-fr.md ; la section trous multilingues ; le spec.json du nouveau plan (source, evidence) ; le résultat du test anti-doublon.
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 20 terminée, modèle d'embeddings (poids), nombre de clusters, trous multilingues notables, temps d'exécution. Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + plan.py + vues SQL + extraits INTERFACES + niches.md | 9 500 |
| Prompt (~1 450 mots) | 2 200 |
| 1 rapport de sous-agent | 1 200 |
| Écriture embed.py (≈ 80 lignes) | 1 000 |
| Écriture topics.py (≈ 350 lignes) | 4 700 |
| Mise à jour plan.py (≈ 60 lignes) | 800 |
| Exécutions (extraits) et requêtes | 4 000 |
| Lecture des rapports produits (têtes) | 2 000 |
| Corrections | 3 500 |
| Mise à jour STATE.md + ledger + résumé | 1 000 |
| Sous-total | 47 900 |
| Marge +25 % | 11 975 |
| **Total** | **59 875 tk — 29,9 %** |

## Étape 21 — Titres, miniatures et métadonnées en variantes, sub-ID d'affiliation

**Objectif.** Remplacer les versions v1 par un générateur de titres en variantes (patrons de la niche, heuristiques, duel LLM), des miniatures en 3 variantes notées objectivement (contraste, surface de texte, lisibilité à petite taille), et des métadonnées de référencement complètes (description structurée, chapitres, tags, hashtags, localisations, bloc d'affiliation avec sous-identifiant par vidéo, commentaire épinglé).
**Pourquoi maintenant.** Le titre et la miniature décident du clic ; les variantes conservées sont ce que la phase 5 apprendra à départager.
**Valeur créée.** Thèse n° 1 (le clic dépend du titre et de la miniature autant que du sujet) et n° 2 (variantes tracées pour l'apprentissage) ; économie unitaire (sub-ID par vidéo).
**Pré-requis.** Étape 20 terminée · `registre/REFERENTIEL.json` (patrons, motifs) · étape 13.2 (thumbnail v1).
**Sous-agents.** 1 — mesures locales de qualité d'une miniature (contraste WCAG, surface du texte, saillance, netteté après réduction à 168 px, harmonie de palette) avec bibliothèques libres, et état 2026 de la fonctionnalité « Tester et comparer » des miniatures (Studio uniquement ? limites) pour décider de la stratégie de rotation. 400 mots maximum.
**Livrables.** `factory/editorial/titles.py`, `factory/editorial/thumbnails_variants.py`, `factory/editorial/seo.py`, `factory/steps/thumbnail.py` et `metadata.py` mis à jour, `tests/test_seo.py`.
**Poids disque.** 0.
**Terminé quand.** Un run porte dans son manifeste ≥ 8 titres notés, 3 miniatures rendues et notées (fichiers dans `thumbnails/`), un texte de commentaire épinglé · `metadata.json` contient chapitres, hashtags (3), tags ≤ 500 caractères, localisations prêtes, bloc d'affiliation avec sous-identifiant = video_id quand un produit est configuré, mentions de conformité · tests verts.

**Prompt à copier-coller :**

````text
Tu es spécialiste du référencement YouTube et développeur ; tu produis des titres, miniatures et descriptions en variantes mesurables.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local. Le taux de clic dépend du titre et de la miniature ; le registre fournit les patrons de titre et les motifs de miniature gagnants par niche (registre/REFERENTIEL.json). Cette session génère des variantes, les note par des règles et des mesures locales, choisit, et conserve tout dans le manifeste pour que la phase 5 apprenne ce qui fonctionne (YouTube n'expose pas de test A/B de miniatures par API : la comparaison se fera par rotation mesurée). Elle finalise aussi les métadonnées de référencement et l'affiliation avec un sous-identifiant par vidéo, condition de l'économie unitaire (étape 27).
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 21 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 21 \|^## Phase 4 " ROADMAP.md puis Read en offset/limit.
2. STATE.md
3. factory/steps/titles_v1.py, thumbnail.py, metadata.py (entiers).
4. registre/REFERENTIEL.json — titres et miniatures de 2 niches (python -c).
5. docs/CONFORMITE.md §3 ; config/products/exemple-affilie.yaml.
</demarrage>

<sous_agents>
Lance 1 sous-agent (recherche web + documentation des bibliothèques) : (1) mesures locales de qualité d'une miniature : contraste (WCAG) entre texte et fond, part de surface occupée par le texte, netteté et lisibilité après réduction à 168×94 px (taille d'affichage mobile), saillance (OpenCV, Apache-2.0), harmonie de palette ; (2) état 2026 de « Tester et comparer » (nombre de miniatures, disponibilité API : aucune ?), et pratiques mesurées de rotation de miniatures ; (3) limites YouTube 2026 : longueur de titre affichée, tags (500 caractères), hashtags (3 affichés), chapitres (règles : 00:00 en premier, ≥ 3 chapitres, ≥ 10 s). 400 mots maximum, points numérotés avec URL.
</sous_agents>

<tache>
1. factory/editorial/titles.py : 8 titres par vidéo via LLM avec ≥ 3 patrons de la niche (tirage pondéré par part), langue du run ; score heuristique (longueur 40-70, patron reconnu, nombre ou question, mot de curiosité de la liste de la niche, absence de majuscules abusives et de termes trompeurs — liste de docs/CONFORMITE.md politique spam) ; duel LLM en tournoi entre les 4 meilleurs ; classement final ; manifeste : title_variants[{text, pattern_id, heuristic, llm_rank}], title_chosen ; à partir de l'étape 26, un fichier learned/weights.json pourra modifier les poids des patrons : prévois la lecture optionnelle.
2. factory/editorial/thumbnails_variants.py : 3 variantes (texte choisi parmi les textes de miniature × 2 templates de la charte × palette), rendu 1280×720 ; mesures : contraste texte/fond, surface de texte (%), lisibilité à 168 px (netteté des contours, texte ≥ 10 px de haut), score composite ; choix, fichiers thumbnails/variant_N.png, manifeste thumbnail_variants[{path, text, template, measures, score}] et thumbnail_chosen ; stratégie de rotation documentée (la phase 5 changera de miniature via thumbnails.set après 7 jours si le CTR est sous la médiane de la chaîne).
3. factory/editorial/seo.py : description structurée (accroche, sommaire, chapitres depuis voice/timings.json avec 00:00 et ≥ 3 chapitres ≥ 10 s, sources, bloc affiliation « Publicité » avec lien produit + paramètre de sous-identifiant = video_id selon config/products (tracking_param), mention IA, attribution, 3 hashtags), tags ≤ 500 caractères (sujet, niche, autocomplete YouTube de l'étape 19 si disponible), localizations (titre et description dans les autres langues des chaînes BMS, produits à l'étape 24), pinned_comment (question d'engagement + lien produit avec sous-identifiant), category_id ; mets à jour factory/steps/metadata.py pour utiliser seo.py et titles.py ; supprime titles_v1.py.
4. tests/test_seo.py : chapitres valides, longueur de tags, sous-identifiant présent quand un produit est configuré et absent sinon, mentions présentes par langue, titre ≤ 70 (≥ 8 tests).
5. Exécute `factory run --channel bms-science-fr --from thumbnail` sur un run existant ; regarde les 3 miniatures ; vérifie metadata.json.
6. Commit « étape 21 : titres, miniatures, métadonnées ».
</tache>

<contraintes>
- Aucun titre trompeur : le titre doit être tenu par le script (vérification LLM courte « le script répond-il à la promesse ? »).
- Trois images regardées au maximum.
- Le sous-identifiant ne contient jamais de donnée personnelle : uniquement video_id (et channel_id si le programme l'exige).
</contraintes>

<criteres_de_validation>
Montre : uv run pytest tests/test_seo.py -q ; python -c qui affiche du manifeste les 8 titres avec scores, les 3 miniatures avec mesures et le choix ; la description de metadata.json (chapitres, blocs) ; ls thumbnails/.
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 21 terminée, phase 3 close si le jalon est atteint, stratégie de rotation des miniatures, questions ouvertes (produits réels à configurer par Alek). Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + titles_v1/thumbnail/metadata + extraits REFERENTIEL/CONFORMITE/produit | 9 500 |
| Prompt (~1 450 mots) | 2 200 |
| 1 rapport de sous-agent | 1 200 |
| Écriture titles.py (≈ 220 lignes) | 2 900 |
| Écriture thumbnails_variants.py (≈ 220 lignes) | 2 900 |
| Écriture seo.py + mise à jour metadata.py (≈ 260 lignes) | 3 500 |
| Tests (≈ 90 lignes) | 1 200 |
| Exécutions (extraits) | 3 000 |
| Inspection de 3 miniatures | 4 500 |
| Corrections | 3 500 |
| Mise à jour STATE.md + résumé | 800 |
| Sous-total | 53 200 |
| Marge +25 % | 13 300 |
| **Total** | **66 500 tk — 33,2 %** |

## Phase 4 — Autonomie et publication

**Objectif de la phase.** Faire tourner le système seul : file de production, exécution par lots la nuit, reprise après erreur, journal lisible, relecture humaine par lots (la seule intervention éditoriale), régénération automatique sous le seuil de qualité, publication par l'API officielle sur plusieurs chaînes avec un calendrier crédible et une checklist de conformité, déclinaison multilingue par adaptation.
**Jalon de phase.** Sur 3 semaines, ≥ 5 vidéos sont produites et mises en ligne (programmées ou privées puis publiées dans Studio tant que l'audit n'est pas passé) sur ≥ 2 chaînes, à raison de ≤ 2 par chaîne et par semaine, à des horaires irréguliers · le journal prouve que les seules actions humaines ont été la relecture par lots et, le cas échéant, le clic de publication dans Studio · au moins une vidéo est une déclinaison multilingue d'une autre.

## Étape 22.1 — Orchestrateur : file, reprise, journal, daemon, sauvegardes

**Objectif.** Livrer la file de production (SQLite), l'exécuteur à une vidéo à la fois avec reprise par étape et nouvelles tentatives, le journal structuré et lisible, le daemon planifié par launchd avec fenêtre nocturne, et la sauvegarde planifiée de tout ce qui fait la valeur de l'actif (base, manifestes, configuration, poids appris).
**Pourquoi maintenant.** Sans file ni reprise, chaque vidéo exige un humain devant le terminal ; sans sauvegarde, l'actif tient sur un seul disque.
**Valeur créée.** Thèse n° 6 (autonomie réelle) et transférabilité de l'actif (sauvegardes).
**Pré-requis.** Étapes 15 et 20 terminées · `factory run` fonctionnel.
**Sous-agents.** 1 — bonnes pratiques launchd sur macOS 27 pour un agent utilisateur de longue durée (KeepAlive, StartCalendarInterval, comportement en veille et capot fermé, `caffeinate`, rotation des logs, pmset), 400 mots maximum.
**Livrables.** `factory/orchestrator/queue.py`, `runner.py`, `daemon.py`, `backup.py`, `factory queue add|status|retry|block`, `factory daemon start|stop|status`, `~/Library/LaunchAgents/com.bms.factory.daemon.plist`, `~/Library/LaunchAgents/com.bms.factory.backup.plist`, `workspace/logs/events.jsonl`, `workspace/logs/factory.log`.
**Poids disque.** ≈ 0,3 Go par run ; sauvegardes ≈ 50 Mo par jour (hors vidéos).
**Terminé quand.** `factory queue add --channel bms-science-fr --n 2` puis le daemon produisent les deux runs jusqu'au statut `exported` sans intervention · un test d'interruption (kill du daemon en cours de rendu) puis redémarrage reprend à l'étape interrompue (preuve dans `events.jsonl`) · une archive de sauvegarde est créée dans `~/BMS-backups/` et restaurable (test de restauration à blanc) · `launchctl list` montre les deux agents.

**Prompt à copier-coller :**

````text
Tu es ingénieur systèmes ; tu construis des orchestrateurs de tâches robustes, reprenables et observables sur une seule machine.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local, MacBook Air M2 16 Go. Le pipeline (factory run) produit une vidéo ; cette session le fait tourner seul : file de jobs, un run à la fois (un modèle en mémoire à la fois), reprise à l'étape interrompue, tentatives avec attente croissante, journal structuré (JSONL) et journal lisible, daemon launchd avec fenêtre nocturne, garde-fous disque et mémoire, sauvegarde quotidienne de la base, des manifestes, de la configuration et des poids appris : sans sauvegarde, l'actif n'est pas transférable. La relecture humaine et la régénération viennent à l'étape 22.2 ; prévois les états.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 22.1 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 22\.1 \|^## Étape 22\.2 " ROADMAP.md puis Read en offset/limit.
2. STATE.md
3. docs/ARCHITECTURE.md — sections DAG, journal, mémoire et disque, sémantique des erreurs.
4. factory/run.py (entier) ; factory/core/db.py (tables existantes).
</demarrage>

<sous_agents>
Lance 1 sous-agent (recherche web, documentation Apple et retours d'expérience récents) : agents launchd utilisateur sur macOS 26-27 — KeepAlive vs StartCalendarInterval, exécution quand le Mac dort ou a le capot fermé (branché ou non), utilisation de caffeinate -i/-s, pmset et « Wake for network access », rotation des logs (newsyslog ou rotation applicative), variables d'environnement et PATH dans un plist, chargement/déchargement (launchctl bootstrap/bootout), erreurs fréquentes. 400 mots maximum, points numérotés avec URL.
</sous_agents>

<tache>
1. Migration 003_queue.sql : table jobs (id, video_id, channel_id, stage, status : queued | running | awaiting_review | blocked | failed | exported | published, attempts, next_run_at, last_error, priority, created_at, updated_at, locked_by) ; table events optionnelle (le fichier JSONL reste la source).
2. factory/orchestrator/queue.py : `factory queue add --channel <id> [--n N] [--topic ...] [--priority P]` (crée les plans via topics_queue et enfile), `status` (tableau rich par statut, temps moyen par étape sur les 10 derniers runs), `retry <job>`, `block <job> --reason`, `prioritize <job>`.
3. factory/orchestrator/runner.py : boucle : prend le job le plus prioritaire (verrou), exécute l'étape courante dans un sous-processus (réutilise factory/run.py étape par étape) avec timeout par étape (config : script 15 min, render 90 min, etc.), enregistre l'événement (JSONL : ts, job, video_id, stage, level, msg, data), passe à l'étape suivante ou : échec → tentatives (3, attente 5 puis 15 puis 60 min) puis failed avec last_error lisible ; après script → awaiting_review si channel.auto_approve est false (l'étape 22.2 fournira la commande de relecture ; sans elle, le job attend) ; après qc FAIL → blocked (l'étape 22.2 ajoutera la régénération) ; garde-fous avant chaque étape : disque libre ≥ 8 Go (sinon pause et alerte), mémoire libre suffisante (vm_stat), aucun autre run en cours ; un seul job actif.
4. factory/orchestrator/daemon.py : `factory daemon start|stop|status|run-once` ; fenêtre de production configurable (config/orchestrator.yaml : nuit 22:00-07:00 pour les étapes lourdes, journée pour collecte/analytics), caffeinate -i pendant un run, arrêt propre (signal → fin de l'étape en cours) ; plist com.bms.factory.daemon (RunAtLoad, KeepAlive, PATH complet, WorkingDirectory, StandardOutPath vers workspace/logs/daemon.log) ; rotation applicative de factory.log (10 Mo × 5).
5. factory/orchestrator/backup.py : `factory backup run|restore-test` → archive tar.zst (ou tar.gz) de workspace/factory.db (copie cohérente via sqlite3 .backup), workspace/runs/*/manifest.json + metadata.json + qc.json + publish.json, config/, learned/, registre/REFERENTIEL.json, docs/ ; hors secrets ; destination ~/BMS-backups/factory-<date>.tar.zst, rétention 30 jours ; plist com.bms.factory.backup quotidien ; restore-test : extrait dans un dossier temporaire, ouvre la base, compte les runs, compare avec l'original. Consigne dans docs/EXPLOITATION.md (créé plus tard) l'obligation de copier ~/BMS-backups sur un support externe ou un cloud gratuit ; ajoute une ligne dans STATE.md.
6. Tests : enfile 2 jobs pour bms-science-fr (auto_approve temporairement true pour ce test, ou approuve avec une commande minimale) ; lance `factory daemon run-once` ; pendant le rendu du 2e, tue le processus (kill) ; relance ; vérifie dans events.jsonl la reprise à l'étape interrompue ; les deux jobs finissent exported. Lance backup run puis restore-test.
7. Charge les deux agents launchd ; vérifie launchctl list.
8. Commit « étape 22.1 : orchestrateur et sauvegardes ».
</tache>

<contraintes>
- Un seul run actif à la fois, un seul modèle en mémoire : c'est une règle d'architecture, pas une option.
- Journal JSONL append-only ; aucune donnée secrète dans les événements.
- Les sorties du daemon vont dans des fichiers ; tu ne lis que tail et grep.
</contraintes>

<criteres_de_validation>
Montre : factory queue status (2 jobs exported) ; grep de events.jsonl montrant l'interruption puis la reprise (stage identique, attempts incrémenté) ; ls -la ~/BMS-backups/ ; la sortie de restore-test ; launchctl list | grep com.bms.factory.
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 22.1 terminée, temps moyen par étape, fenêtre de production, emplacement des sauvegardes, rappel « copier ~/BMS-backups hors de la machine ». Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + ARCHITECTURE (sections) + run.py + db.py | 9 500 |
| Prompt (~1 450 mots) | 2 200 |
| 1 rapport de sous-agent | 1 200 |
| Écriture migration + queue.py (≈ 220 lignes) | 2 900 |
| Écriture runner.py (≈ 300 lignes) | 4 000 |
| Écriture daemon.py + plists (≈ 160 lignes) | 2 100 |
| Écriture backup.py (≈ 100 lignes) | 1 300 |
| Exécutions, test d'interruption, sauvegarde (extraits) | 5 000 |
| Corrections | 4 000 |
| Mise à jour STATE.md + résumé | 800 |
| Sous-total | 51 000 |
| Marge +25 % | 12 750 |
| **Total** | **63 750 tk — 31,9 %** |

## Étape 22.2 — Relecture par lots, régénération sous seuil, alertes

**Objectif.** Ajouter la seule intervention éditoriale humaine prévue (relecture des scripts par lots, journalisée avec relecteur et empreinte : la signature humaine exigée par la conformité), la régénération automatique ciblée quand le banc rejette une vidéo, et les alertes (Telegram gratuit si configuré, sinon notification macOS et digest quotidien).
**Pourquoi maintenant.** L'orchestrateur attend ces états ; sans relecture journalisée, le système est exposé à la politique « contenu inauthentique » et au RIA art. 50.
**Valeur créée.** Thèse n° 5 (signature humaine tracée) et n° 6 (supervision sans terminal).
**Pré-requis.** Étape 22.1 terminée · étape 16 (le vérificateur de script) · `config/team.yaml`.
**Sous-agents.** Aucun.
**Livrables.** `factory/orchestrator/review.py`, `regenerate.py`, `notify.py`, `factory review`, `factory digest`, table `review_log`, `reports/digest_<date>.md`.
**Poids disque.** 0.
**Terminé quand.** Un job s'arrête en `awaiting_review`, `factory review` l'approuve avec un relecteur nommé (ligne dans `review_log` avec hash du script) et le pipeline reprend · une vidéo dont le banc est forcé en échec (audio coupé) déclenche une régénération ciblée puis PASS ou `blocked` avec raison lisible · un digest quotidien est produit et une alerte est reçue (Telegram ou notification).

**Prompt à copier-coller :**

````text
Tu es développeur d'outils d'exploitation ; tu rends un système autonome supervisable par des non-développeurs en 10 minutes par jour.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local. L'orchestrateur (22.1) produit seul ; cette session ajoute : (1) la relecture par lots des scripts, unique intervention éditoriale humaine, journalisée avec le nom du relecteur, la date et l'empreinte du script — c'est la « signature humaine » exigée par docs/CONFORMITE.md §4 et l'exception de contrôle éditorial du RIA art. 50 ; (2) la régénération automatique ciblée quand le banc (étape 15) rejette une vidéo ; (3) les alertes et un digest quotidien pour Alek et Sofiane. L'objectif : dix scripts relus en quinze minutes, zéro terminal le reste du temps.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 22.2 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 22\.2 \|^## Étape 23\.1 " ROADMAP.md puis Read en offset/limit.
2. STATE.md
3. factory/orchestrator/runner.py (entier) ; docs/CONFORMITE.md §4 ; docs/QC.md — liste des métriques et des bloquants.
4. config/team.yaml.
</demarrage>

<tache>
1. factory/orchestrator/review.py : `factory review [--channel X] [--reviewer NOM]` → liste compacte des jobs awaiting_review : titre provisoire, chaîne, sujet et angle, type de hook, hook (texte), durée estimée, densité, 3 premières lignes ; pour chaque : a (approuver), r (rejeter avec motif → le job repasse en script avec le motif dans le prompt, 2 fois maximum), e (éditer : ouvre script.json dans $EDITOR, re-valide pydantic et re-vérifie retention/verify), s (passer) ; `--reviewer` obligatoire et présent dans config/team.yaml ; chaque décision → review_log (video_id, reviewer, decision, motif, script_sha256, timestamp) et manifeste (reviewer, review_hash, review_date) ; `factory review --auto --channel X` n'existe que si channel.auto_approve est true et écrit reviewer = "auto" avec un avertissement rouge (risque documenté).
2. factory/orchestrator/regenerate.py : après qc FAIL, lit qc.json et applique une table de remèdes (config/orchestrator.yaml) : rythme hors cible → shotlist avec graine suivante ; hook faible → script --from hook (regénère le hook seul) ; loudness → assemble ; durée hors plage → script avec consigne de longueur ; lisibilité → render (template suivant) ; variété faible → shotlist avec assets forcés différents ; 2 régénérations maximum par run, puis blocked avec la raison exacte et les métriques ; chaque régénération est un événement et un champ du manifeste (regenerations[]).
3. factory/orchestrator/notify.py : canal Telegram si TELEGRAM_BOT_TOKEN et TELEGRAM_CHAT_ID sont dans .env (création d'un bot gratuite via BotFather : guide Thomas), sinon notification macOS (osascript) ; événements notifiés : job blocked, job failed définitif, scripts en attente de relecture (regroupés), disque < 10 Go, quota API > 80 %, daemon arrêté ; `factory digest` → reports/digest_<date>.md (produits, en attente de relecture, bloqués avec raisons, publiés ou à publier manuellement, quota utilisé, disque, sauvegarde du jour) envoyé chaque matin (plist ou depuis le daemon).
4. Intègre dans runner.py les transitions awaiting_review → (approve) → voice, qc FAIL → regenerate → qc, blocked → notification.
5. Tests : enfile 1 job (auto_approve false) ; lance run-once jusqu'à awaiting_review ; approuve avec --reviewer Thomas ; reprends jusqu'à exported. Force un FAIL (par exemple remplace voice.wav par un silence après voice) et vérifie la régénération puis le résultat. Génère un digest ; envoie une alerte de test.
6. Commit « étape 22.2 : relecture, régénération, alertes ».
</tache>

<contraintes>
- Le nom du relecteur vient de config/team.yaml ; aucune relecture anonyme.
- Les remèdes régénèrent seulement l'étape fautive et les suivantes, jamais tout le run.
- Aucun secret dans les notifications ; jamais de lien de jeton.
</contraintes>

<criteres_de_validation>
Montre : sqlite3 "select video_id, reviewer, decision, substr(script_sha256,1,8), timestamp from review_log;" ; les événements de régénération dans events.jsonl et le verdict final ; cat reports/digest_<date>.md ; la preuve de l'alerte (réponse de l'API Telegram ou capture de la notification décrite par Thomas).
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 22.2 terminée, canal d'alerte en place, taux de régénération, consigne pour Alek/Sofiane (relire chaque jour ou tous les deux jours). Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + runner.py + CONFORMITE §4 + QC.md (extraits) + team.yaml | 9 000 |
| Prompt (~1 250 mots) | 1 800 |
| Écriture review.py (≈ 220 lignes) | 2 900 |
| Écriture regenerate.py (≈ 180 lignes) | 2 400 |
| Écriture notify.py + digest (≈ 150 lignes) | 2 000 |
| Intégration runner.py + config (≈ 80 lignes) | 1 000 |
| Exécutions et tests (extraits) | 4 500 |
| Corrections | 3 000 |
| Mise à jour STATE.md + résumé | 800 |
| Sous-total | 45 400 |
| Marge +25 % | 11 350 |
| **Total** | **56 750 tk — 28,4 %** |

## Étape 23.1 — Publication par l'API : OAuth par chaîne, upload, miniature, sous-titres, label, quota, rapports « reach »

**Objectif.** Industrialiser la publication : jeton OAuth par chaîne, upload résumable avec toutes les métadonnées et le label de contenu synthétique, miniature, sous-titres, playlist, comptabilité de quota, création des jobs de la Reporting API (impressions et CTR) **avant** la première publication, et bascule automatique privé → programmé quand l'audit est passé.
**Pourquoi maintenant.** Les vidéos de la phase 4 doivent générer des données de CTR dès leur mise en ligne ; les rapports « reach » ne sont pas rétroactifs.
**Valeur créée.** Thèse n° 2 (les données de clic existeront) et n° 4 (une chaîne de plus = un jeton de plus).
**Pré-requis.** Étape 14 (OAuth, upload minimal), étape 21 (métadonnées v2), étape 22.1 (file).
**Sous-agents.** 1 — Data API v3 et Reporting API au jour de la session : paramètres complets de `videos.insert` (status.publishAt, containsSyntheticMedia, license, embeddable, selfDeclaredMadeForKids), `thumbnails.set` (prérequis de vérification), `captions.insert`, `playlistItems.insert`, `videos.update` (coût 50), compartiments de quota ; Reporting API : `jobs.create` et types de rapports (`channel_reach_basic_a1`, `channel_basic_a2`, `channel_traffic_source_a2`, autres utiles), `reports.list`, téléchargement, délai de disponibilité. 450 mots maximum.
**Livrables.** `factory/publish/youtube.py`, `quota.py`, `reporting_jobs.py`, `factory publish auth|upload|release|status`, tables `publications`, `quota_ledger`, `reporting_jobs`.
**Poids disque.** 0.
**Terminé quand.** Une vidéo de la file atteint le statut `published_private` (ou `scheduled` si `audit_passed`) avec miniature et sous-titres attachés, vérifiés par `videos.list` · `reporting_jobs` contient les jobs créés pour la chaîne (sortie de `jobs.list`) · `quota_ledger` enregistre les unités du jour · `publish.json` et le manifeste sont mis à jour · `factory publish release --video X` passe une vidéo privée en programmée (testé sur la chaîne de test).

**Prompt à copier-coller :**

````text
Tu es ingénieur intégration YouTube Data API v3 et Reporting API ; tu écris des clients robustes, économes en quota et vérifiables.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local. La publication est le point de contact avec la plateforme : elle doit être conforme (docs/CONFORMITE.md §2-3), économe (compartiments de quota 2026 : 100 uploads/jour, 10 000 unités pour le reste), multi-chaînes (un jeton par chaîne) et instrumentée : les jobs de la Reporting API (impressions, CTR) doivent exister avant la première mise en ligne, car ils ne sont pas rétroactifs. Tant que l'audit Google n'est pas passé, les vidéos restent privées : la publication programmée se fait alors à la main dans Studio, et le système fournit la liste exacte à publier ; dès que config youtube.audit_passed passe à true, la bascule est automatique.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 23.1 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 23\.1 \|^## Étape 23\.2 " ROADMAP.md puis Read en offset/limit.
2. STATE.md (statut de l'audit)
3. docs/CONFORMITE.md §2 et §3 ; docs/INTERFACES.md — contrat publish.json.
4. factory/publish/oauth.py et upload_min.py (entiers).
5. Le metadata.json d'un run exporté (court).
</demarrage>

<sous_agents>
Lance 1 sous-agent (recherche web, developers.google.com uniquement) : (1) videos.insert : tous les champs de status (privacyStatus, publishAt et sa condition « private », containsSyntheticMedia, selfDeclaredMadeForKids, license, embeddable, publicStatsViewable), upload résumable et reprise, coût et compartiment ; (2) thumbnails.set (prérequis : compte vérifié), captions.insert (400 unités), playlistItems.insert, videos.update (50 unités, champs modifiables) ; (3) Reporting API : jobs.create (types de rapports disponibles pour un propriétaire de chaîne, dont channel_reach_basic_a1 pour impressions et CTR, channel_basic_a2, channel_traffic_source_a2, channel_demographics_a1, channel_playback_location_a2), fréquence, délai de première disponibilité, reports.list, media.download, durée de rétention ; (4) erreurs fréquentes (quotaExceeded, forbidden, uploadLimitExceeded). 450 mots maximum, points numérotés avec URL.
</sous_agents>

<tache>
1. Migration 004_publish.sql : publications (video_id, channel_id, youtube_video_id, status : published_private | scheduled | public | failed, publish_at, uploaded_at, thumbnail_set, captions_set, playlist_added, units_used), quota_ledger (date, project, units, inserts, updates), reporting_jobs (channel_id, job_id, report_type, created_at).
2. factory/publish/quota.py : compteur par jour et par compartiment, plafonds (config : 80 uploads, 8 000 unités), refus propre au-delà, `factory publish status` (quota du jour, vidéos privées à publier manuellement, programmées, erreurs).
3. factory/publish/youtube.py : `factory publish upload --run <id>` (ou depuis l'orchestrateur après export + qc PASS + precheck de l'étape 23.2 quand elle existera : prévois l'appel) → upload résumable avec snippet et status complets depuis metadata.json (containsSyntheticMedia, selfDeclaredMadeForKids=false, notifySubscribers depuis config, defaultLanguage, defaultAudioLanguage), privacyStatus=private ; si channel.youtube.audit_passed : publishAt = date du calendrier (23.2) ou fourni en argument ; thumbnails.set (si vérifié, sinon avertissement et champ thumbnail_set=false), captions.insert (SRT, langue), playlistItems.insert (playlist de la chaîne) ; écrit publish.json, publications, manifeste (youtube_video_id, published_at) ; vérification videos.list ; gestion des erreurs avec tentatives et journal ; `factory publish release --video <youtube_id> [--at ISO]` → videos.update status (privacyStatus private + publishAt) ; `factory publish auth --channel <id>` réutilise oauth.py.
4. factory/publish/reporting_jobs.py : `factory publish reporting-jobs --channel <id>` → crée (idempotent) les jobs reach, basic, traffic_source, demographics, playback_location pour la chaîne ; enregistre ; `--list` affiche jobs.list. Exécute-le pour la chaîne de test et pour toute chaîne BMS déjà authentifiée.
5. Liste « à publier manuellement » : `factory publish manual-list` → pour chaque vidéo published_private sans audit : titre, chaîne, date et heure de programmation prévues, lien Studio ; c'est ce que le digest (22.2) affiche.
6. Test : publie une vidéo exportée de la file sur la chaîne de test ; vérifie par videos.list ; teste release avec une date à J+7 (la vidéo reste privée puis programmée ; annule ensuite en repassant private sans publishAt si tu ne veux pas qu'elle sorte).
7. Commit « étape 23.1 : publication API et rapports reach ».
</tache>

<contraintes>
- Jamais de secret dans les logs ; jetons dans secrets/tokens/.
- Aucune vidéo rendue publique pendant cette session sans l'accord explicite de Thomas.
- Respect des plafonds de quota ; chaque appel est comptabilisé avant d'être fait.
</contraintes>

<criteres_de_validation>
Montre : la sortie de videos.list pour la vidéo publiée (privacyStatus, containsSyntheticMedia, thumbnails, publishAt le cas échéant) ; sqlite3 "select * from publications; select * from quota_ledger; select * from reporting_jobs;" ; la sortie de --list des jobs de rapports ; factory publish manual-list.
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 23.1 terminée, chaînes authentifiées, jobs de rapports créés (dates), quota du jour, statut de l'audit, rappel de la procédure manuelle. Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + CONFORMITE §2-3 + INTERFACES (publish) + oauth/upload_min + metadata.json | 10 000 |
| Prompt (~1 450 mots) | 2 200 |
| 1 rapport de sous-agent | 1 300 |
| Écriture migration + quota.py (≈ 140 lignes) | 1 900 |
| Écriture youtube.py (≈ 300 lignes) | 4 000 |
| Écriture reporting_jobs.py + manual-list (≈ 140 lignes) | 1 900 |
| Exécutions et sorties API (extraits) | 4 500 |
| Corrections | 3 000 |
| Mise à jour STATE.md + résumé | 800 |
| Sous-total | 47 600 |
| Marge +25 % | 11 900 |
| **Total** | **59 500 tk — 29,8 %** |

## Étape 23.2 — Calendrier crédible, checklist de conformité pré-publication, bascule post-audit

**Objectif.** Planifier les publications comme le ferait une chaîne humaine (cadence par chaîne, jours et heures issus du registre, jitter, jamais deux chaînes BMS dans la même heure, plafonds des 90 premiers jours), automatiser la checklist de conformité avant tout upload (signature humaine, QC, mentions, licences, anti-clonage, label synthétique, promotion payante), documenter la vérification téléphonique par compte et le passage post-audit ; charger la file pour le jalon de phase.
**Pourquoi maintenant.** La cadence est un signal de survie (les terminaisons de 2026 visent le volume mécanique) ; la checklist est la dernière ligne avant la plateforme.
**Valeur créée.** Thèse n° 5.
**Pré-requis.** Étape 23.1 terminée.
**Sous-agents.** 1 contradicteur « sécurité des comptes » (vague 2) : lit le calendrier et la checklist et cherche ce qui ferait repérer le réseau (motifs de métadonnées, similarités inter-chaînes, horaires, IP et appareils partagés, rafales).
**Livrables.** `factory/publish/calendar.py`, `precheck.py`, `factory calendar plan|show`, `factory precheck`, `docs/CONFORMITE.md` §opérationnel (vérification par compte, procédure post-audit, procédure manuelle Studio), file chargée pour 3 semaines.
**Poids disque.** 0.
**Terminé quand.** `factory calendar plan` attribue des dates à ≥ 5 vidéos sur 21 jours en respectant toutes les contraintes (tableau affiché, aucune violation détectée par le test) · `factory precheck` bloque un run volontairement non conforme (mention IA retirée) et laisse passer un run conforme · l'orchestrateur appelle precheck avant upload · la file contient ≥ 5 jobs sur ≥ 2 chaînes programmés sur 3 semaines · `CONFORMITE.md` §opérationnel écrit.

**Prompt à copier-coller :**

````text
Tu es responsable des opérations de chaînes YouTube et développeur ; tu fais publier une machine comme une équipe humaine prudente.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local. Les terminaisons de janvier 2026 ont visé des réseaux publiant en volume, à heures fixes, avec des templates identiques. Cette session rend le calendrier crédible (cadence par chaîne ≤ 2/semaine les 90 premiers jours, créneaux issus du registre et bientôt de l'analytique, jitter de ±90 minutes, jamais deux chaînes BMS dans la même heure, pas de rafale) et automatise la checklist de conformité avant tout upload (docs/CONFORMITE.md §11) : relecture journalisée, QC PASS, mentions IA et affiliation, licences de tous les assets et de la musique, anti-clonage inter-chaînes (empreinte de script et de miniature), label synthétique décidé avec raison, promotion payante cohérente, durée ≥ 60 s, langue renseignée. Elle documente aussi ce que chaque compte doit avoir (vérification téléphonique) et la bascule post-audit, puis charge la file pour le jalon de phase 4.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 23.2 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 23\.2 \|^## Étape 24 " ROADMAP.md puis Read en offset/limit.
2. STATE.md
3. docs/CONFORMITE.md (entier).
4. registre/REFERENTIEL.json — creneaux et cadence de 2 niches (python -c) ; registre/TRAJECTOIRES.md — règles de cadence.
5. factory/publish/youtube.py — signatures des fonctions (grep -n "def ").
</demarrage>

<sous_agents>
Vague 2 — après ton brouillon de calendar.py, precheck.py et de la section opérationnelle : 1 contradicteur « sécurité des comptes » qui lit ces trois éléments et la config des chaînes et cherche ce qui ferait repérer un réseau automatisé : horaires trop réguliers, descriptions à structure identique, miniatures au même template, même voix sur plusieurs chaînes de même langue, IP et appareil partagés, publication simultanée, métadonnées trompeuses, absence de variation de durée. 400 mots maximum, « Problème → correction ».
</sous_agents>

<tache>
1. factory/publish/calendar.py : `factory calendar plan [--weeks 3]` → pour chaque job exporté ou en cours sans date : chaîne → cadence (config, plafonnée par CONFORMITE §6 et par l'âge de la chaîne), créneaux (jours et heures locales de l'audience : config, initialisée depuis REFERENTIEL creneaux, remplacée par learned/weights.json à partir de l'étape 26), jitter ±90 min, espacement minimal 48 h par chaîne, aucune vidéo BMS toutes chaînes confondues dans la même heure, jamais plus de 2 vidéos BMS par jour, variation de durée entre vidéos consécutives d'une chaîne (≥ 10 %) sinon avertissement ; écrit publish_at dans jobs ; `factory calendar show` (tableau par semaine et par chaîne) ; test de contraintes intégré (`--check`) qui liste toute violation.
2. factory/publish/precheck.py : `factory precheck --run <id>` → chaque contrôle de CONFORMITE §11 avec verdict bloquant ou avertissement : review_log présent et hash = script actuel ; qc PASS ; mentions (IA, affiliation si produit) présentes dans la description dans la bonne langue ; paid_promotion cohérent avec la présence d'un lien produit ; contains_synthetic_media décidé avec raison ; licence.json pour chaque asset et piste ; bloc d'attribution présent si requis ; empreinte du script et hachage perceptuel de la miniature non similaires (> seuil) à toute vidéo publiée sur une autre chaîne BMS de même langue ; durée ≥ 60 s ; langue et catégorie renseignées ; titre non trompeur (vérification LLM de l'étape 21 présente) ; bandeau « Publicité » présent sur les plans sponsor (champ du manifeste) ; → precheck.json et statut ; l'orchestrateur l'appelle avant publish et bloque en cas d'échec.
3. docs/CONFORMITE.md — section « Opérationnel » : checklist par compte (Brand Account BMS, 2FA, vérification téléphonique : ce qu'elle débloque, une par numéro et par période), procédure manuelle de publication dans Studio (à partir de factory publish manual-list), procédure post-audit (passer youtube.audit_passed à true, lancer factory publish release pour les vidéos en attente), procédure d'ajout d'une chaîne (compte, jeton, config, jobs de rapports, calendrier), ce qu'il ne faut jamais faire (outils d'engagement, automatisation navigateur, republication de contenu tiers, rafales).
4. Lance le contradicteur ; corrige ; consigne « Objections ».
5. Charge la file pour le jalon : `factory queue add` sur ≥ 2 chaînes (au moins bms-science-fr et bms-science-en ou bms-histoire-fr) pour ≥ 5 vidéos ; `factory calendar plan --weeks 3` ; `factory calendar show --check` (0 violation). Note dans STATE.md : le daemon va produire et publier pendant 3 semaines ; les actions humaines attendues (relecture, clic Studio si pas d'audit) ; la date de vérification du jalon.
6. Test precheck : sur un run conforme (PASS) et sur une copie du run où la mention IA est retirée de metadata.json (FAIL, raison).
7. Commit « étape 23.2 : calendrier et conformité pré-publication ».
</tache>

<contraintes>
- Aucune règle de cadence codée en dur : tout vient de la config, bornée par CONFORMITE.
- Aucune publication publique pendant la session sans accord de Thomas.
- Les seuils de similarité (script, miniature) sont dans config/qc.yaml et documentés.
</contraintes>

<criteres_de_validation>
Montre : factory calendar show --check (tableau, 0 violation) ; les deux sorties de precheck (PASS et FAIL avec raison) ; factory queue status (≥ 5 jobs sur ≥ 2 chaînes avec publish_at) ; la section « Opérationnel » de CONFORMITE.md (titres) ; les objections traitées.
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 23.2 terminée, calendrier des 3 semaines (chaîne, dates), actions humaines attendues, date de vérification du jalon de phase 4, objections non résolues. Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + CONFORMITE (entier) + extraits REFERENTIEL/TRAJECTOIRES + signatures | 10 000 |
| Prompt (~1 400 mots) | 2 200 |
| 1 rapport contradicteur | 1 200 |
| Écriture calendar.py (≈ 200 lignes) | 2 700 |
| Écriture precheck.py (≈ 220 lignes) | 2 900 |
| Section opérationnelle de CONFORMITE.md (≈ 100 lignes) | 1 300 |
| Intégration orchestrateur + config (≈ 60 lignes) | 800 |
| Exécutions et tests (extraits) | 3 000 |
| Corrections | 2 500 |
| Mise à jour STATE.md + résumé | 800 |
| Sous-total | 45 400 |
| Marge +25 % | 11 350 |
| **Total** | **56 750 tk — 28,4 %** |

## Étape 24 — Déclinaison multilingue par adaptation

**Objectif.** Produire, à partir d'un run source, un run enfant pour une chaîne d'une autre langue : script adapté (pas traduit mot à mot : références, unités, exemples, hook et titres régénérés dans la langue), voix de la chaîne cible, sous-titres, redécoupage sur les nouveaux timings, réutilisation des assets visuels, habillage distinct (template et charte de la chaîne cible), métadonnées localisées ; mesurer le surcoût.
**Pourquoi maintenant.** C'est le levier de volume du registre (Thoth EN/FR/IT), et il doit rester conforme à l'anti-clonage : adaptation et habillage distinct.
**Valeur créée.** Thèse n° 4 : une production en engendre trois pour une fraction du coût.
**Pré-requis.** Étape 23.2 terminée (et étapes 16, 21) · chaînes cibles configurées avec voix et charte propres.
**Sous-agents.** 1 — techniques d'adaptation de scripts par LLM local 9B entre FR/EN/ES/IT (glossaire, instructions de localisation, pièges : nombres, unités, idiomes, longueur), et vérification que les voix retenues couvrent ES et IT (RESULTATS.md). 400 mots maximum.
**Livrables.** `factory/steps/localize.py`, `factory localize`, étage `localize` dans l'orchestrateur (déclenché par `channel.derive_from`), un run enfant complet, mesure du coût relatif dans les manifestes.
**Poids disque.** ≈ 0,2 Go par run enfant.
**Terminé quand.** Un run enfant EN issu d'un run FR passe `factory qc` et `factory precheck` · le manifeste enfant porte `parent_id`, un template et une miniature différents du parent (vérifié par hachage perceptuel), un hook régénéré · coût compute enfant ÷ parent mesuré et consigné (cible ≤ 25 %) · l'orchestrateur enfile automatiquement les déclinaisons pour les chaînes `derive_from`.

**Prompt à copier-coller :**

````text
Tu es responsable de la localisation et développeur ; tu déclines des productions entre langues sans les cloner.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local. Le registre montre que la même marque clonée par langue multiplie l'audience (Library of Thoth EN/FR/IT). Mais la politique « contenu inauthentique » et docs/CONFORMITE.md §5 interdisent le clonage mécanique : la déclinaison est une adaptation (références culturelles, unités, exemples, hook et titres régénérés dans la langue cible) avec un habillage distinct (charte, template, miniature de la chaîne cible) et la voix de la chaîne cible. Les assets visuels (images, clips) sont réutilisés : c'est là que se fait l'économie. Cette session implémente la déclinaison et mesure son coût réel par rapport au run source.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 24 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 24 \|^## Phase 5 " ROADMAP.md puis Read en offset/limit.
2. STATE.md
3. docs/ARCHITECTURE.md — section multi-langues ; docs/CONFORMITE.md §5.
4. factory/run.py — enchaînement des étapes (grep -n "def \|STEPS") ; factory/steps/shotlist.py — signature et champs asset_request (grep -n).
5. config/channels/bms-science-en.yaml (vérifie derive_from) ; benchmarks/RESULTATS.md §1 — voix disponibles par langue (grep -n "es\|it").
</demarrage>

<sous_agents>
Lance 1 sous-agent (recherche web + lecture de RESULTATS.md) : (1) techniques d'adaptation (pas de traduction littérale) de scripts vidéo par un LLM local de 9B entre FR, EN, ES, IT : structure de prompt, glossaire par niche, consignes de localisation (unités, dates, devises, références culturelles, exemples locaux), contrôle de longueur (les langues romanes allongent de 15-25 %), vérification de fidélité (aller-retour, juge LLM) ; (2) pour les voix retenues : disponibilité et qualité en ES et IT selon benchmarks/RESULTATS.md et les fiches des modèles. 400 mots maximum, points numérotés.
</sous_agents>

<tache>
1. factory/steps/localize.py : `factory localize --run <id-parent> --to <channel-cible>` → crée un run enfant (video_id nouveau, parent_id, spec dérivée : même sujet et angle, langue et niche de la cible, durée cible de la niche cible) ; script : adaptation par LLM avec glossaire (config/languages/<lang>.yaml : glossaire par niche, règles typographiques, unités), conservation de la structure des segments (ids) et des visual_intent, régénération du hook via factory/retention/hooks.py dans la langue cible, texte à l'écran adapté (≤ 6 mots), segment sponsor avec les mentions de la langue cible, vérification retention/verify ; voice et subtitles avec la voix de la chaîne cible ; shotlist recalculée sur les nouveaux timings mais avec les mêmes asset_request (réutilisation : images.py et stock.py retrouvent les assets par hash de prompt ou par identifiant, aucune régénération sauf plan nouveau) ; render avec le template et la charte de la chaîne cible (template ≠ template du parent : impose une rotation différente) ; assemble, thumbnail (texte régénéré, template différent), metadata (titles.py et seo.py dans la langue cible ; ajoute au parent des localizations pour son titre et sa description), qc, export ; manifeste enfant : parent_id, assets_reused_ratio, cost et timings ; manifeste parent : children[].
2. Orchestrateur : étage localize après export (ou après publication du parent, selon config/orchestrator.yaml) pour chaque chaîne dont derive_from = chaîne du parent ; le run enfant suit ensuite le flux normal (review par lots : le relecteur voit qu'il s'agit d'une déclinaison et relit l'adaptation), qc, precheck, calendrier (jamais le même jour que le parent).
3. Exécute sur un run FR exporté → bms-science-en ; puis `factory qc`, `factory precheck`. Mesure : compute_min enfant ÷ parent, part d'assets réutilisés, différence de template et distance perceptuelle des miniatures (imagehash) ; regarde 2 images extraites de la vidéo enfant pour vérifier l'habillage distinct et le texte anglais.
4. Si une voix ES ou IT manque (RESULTATS.md), note-le dans STATE.md comme limite et configure derive_from seulement pour les langues couvertes.
5. Commit « étape 24 : déclinaison multilingue ».
</tache>

<contraintes>
- Interdit : traduction mot à mot sans adaptation, même template, même miniature, même voix qu'une autre chaîne de même langue.
- Aucune régénération d'image si l'asset existe ; le ratio de réutilisation est mesuré.
- Deux images regardées au maximum.
</contraintes>

<criteres_de_validation>
Montre : python -c qui affiche du manifeste enfant : parent_id, lang, template vs parent, assets_reused_ratio, cost enfant et parent avec le ratio, hook_chosen ; distance perceptuelle des deux miniatures ; qc.json et precheck.json (PASS) ; la ligne children[] du parent.
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 24 terminée, ratio de coût mesuré, langues couvertes par les voix, chaînes derive_from actives, jalon de phase 4 (état : en cours sur 3 semaines, date de vérification). Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + ARCHITECTURE/CONFORMITE (sections) + signatures + config + extraits RESULTATS | 9 500 |
| Prompt (~1 400 mots) | 2 200 |
| 1 rapport de sous-agent | 1 200 |
| Écriture localize.py (≈ 300 lignes) | 4 000 |
| Adaptations shotlist/images/stock/orchestrateur (≈ 100 lignes) | 1 300 |
| Exécutions run enfant + qc + precheck (extraits) | 5 000 |
| Inspection de 2 images | 3 000 |
| Lecture des manifestes (extraits) et mesures | 1 500 |
| Corrections | 3 500 |
| Mise à jour STATE.md + résumé | 800 |
| Sous-total | 50 000 |
| Marge +25 % | 12 500 |
| **Total** | **62 500 tk — 31,2 %** |

## Phase 5 — Boucle de rétroaction et monétisation

**Objectif de la phase.** Récupérer automatiquement les performances de chaque vidéo publiée (vues, durée de visionnage, rétention, abonnés, sources, impressions, CTR), les rattacher aux choix de production tracés dans le manifeste, en tirer des poids qui orientent les productions suivantes (sujets, hooks, titres, rythme, créneaux, miniatures), valider le banc contre les vues réelles, intégrer l'affiliation avec suivi par vidéo et mesurer l'économie unitaire. **C'est le mécanisme qui fait monter la valeur du système avec le temps.**
**Jalon de phase.** `factory analytics pull` remplit les tables de performance pour les vidéos publiées en phase 4 (dont ≥ 1 courbe de rétention) · `factory learn` produit `learned/weights.json` et un rapport lisible, et la liste des 10 prochains sujets de `factory plan` diffère avec et sans poids · `reports/economics.md` donne le coût réel par vidéo et par minute, par style, et le revenu par vidéo (réel ou 0 avec le chemin d'import testé).

## Étape 25 — Récupérer les performances et les joindre au manifeste

**Objectif.** Livrer `factory analytics pull` : chaque jour, pour chaque chaîne authentifiée, les métriques par vidéo (Analytics API), la courbe de rétention à J+7 et J+30, les sources de trafic, et les rapports « reach » (Reporting API : impressions, CTR) ; les stocker dans `factory.db` et les joindre aux manifestes via une vue unique qui expose les facteurs de production et les résultats.
**Pourquoi maintenant.** Les premières vidéos de la phase 4 sont en ligne ; la latence de 72 h et la rétention de 30 jours des rapports imposent de collecter tout de suite.
**Valeur créée.** Thèse n° 2 : sans cette jointure, le système est un tapis roulant.
**Pré-requis.** Étape 23.1 terminée (jobs de rapports créés, vidéos publiées) · étape 18 (entrepôt).
**Sous-agents.** 1 — Analytics API et Reporting API au jour de la session : requêtes exactes par vidéo et par jour (métriques, dimensions, filtres), requête de courbe de rétention (`audienceWatchRatio`, `relativeRetentionPerformance` × `elapsedVideoTimeRatio`), sources de trafic, colonnes des rapports reach et basic, latence, quotas, pièges (fuseau, dates partielles). 450 mots maximum.
**Livrables.** `factory/analytics/pull.py`, `factory/analytics/schema.sql` (migration), `factory analytics pull|show`, vue `v_video_perf`, `~/Library/LaunchAgents/com.bms.factory.analytics.plist`.
**Poids disque.** ≈ 0,1 Go par an.
**Terminé quand.** `perf_daily` contient des lignes pour chaque vidéo publiée depuis ≥ 3 jours · `retention_curves` contient ≥ 1 courbe de 100 points · `perf_reach` contient des lignes ou le statut du job explique leur absence · `v_video_perf` renvoie, par vidéo, ≥ 12 colonnes de facteurs (sujet, cluster, hook_type, patron de titre, variante de miniature, style, template, rythme cible et mesuré, durée, langue, niche, voix, créneau, densité) et les métriques à 7 et 30 jours · `factory analytics show --video X` affiche la courbe de rétention en ASCII avec les chutes rattachées aux segments du script · l'agent launchd est chargé.

**Prompt à copier-coller :**

````text
Tu es ingénieur données analytiques ; tu relies des mesures de plateforme à des décisions de production pour rendre un système apprenant.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local. Chaque vidéo publiée porte un manifeste qui trace ses choix (sujet et source, hook, titre et patron, miniature, rythme cible et mesuré, style, template, langue, voix, créneau, densité). Cette session récupère les résultats (Analytics API : vues, minutes, durée moyenne, pourcentage moyen, abonnés gagnés, likes, partages, sources de trafic, courbe de rétention ; Reporting API : impressions et CTR via les rapports reach créés à l'étape 23.1) et les joint aux manifestes dans une vue unique. Latence YouTube jusqu'à 72 h : on relit toujours les 5 derniers jours. Les rapports ne sont conservés que 30 à 60 jours côté Google : on stocke tout localement.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 25 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 25 \|^## Étape 26 " ROADMAP.md puis Read en offset/limit.
2. STATE.md
3. docs/INTERFACES.md — contrat manifest.json (section résultats et décisions) ; factory/core/db.py et les migrations existantes (noms de tables).
4. factory/publish/reporting_jobs.py (entier) ; factory/publish/oauth.py — fonction de client.
5. sqlite3 workspace/factory.db "select video_id, youtube_video_id, status, publish_at from publications;"
</demarrage>

<sous_agents>
Lance 1 sous-agent (recherche web, developers.google.com/youtube/analytics et /reporting) : (1) requête Analytics API reports.query par vidéo et par jour : ids, startDate/endDate, metrics (views, estimatedMinutesWatched, averageViewDuration, averageViewPercentage, subscribersGained, likes, shares, comments, engagedViews), dimensions (day, video), filters, sort, maxResults ; (2) courbe de rétention : metrics audienceWatchRatio, relativeRetentionPerformance avec dimension elapsedVideoTimeRatio et filtre video==ID (100 points) ; (3) sources de trafic (insightTrafficSourceType) et appareils ; (4) Reporting API : reports.list par job, media.download, colonnes exactes de channel_reach_basic_a1 (video_thumbnail_impressions, video_thumbnail_impressions_ctr) et channel_basic_a2, délai de première disponibilité, rétention ; (5) latence et fuseau des dates ; quotas. 450 mots maximum, points numérotés avec URL et exemple de requête.
</sous_agents>

<tache>
1. Migration 005_analytics.sql : perf_daily (video_id, youtube_video_id, channel_id, date, views, minutes_watched, avg_view_duration_s, avg_view_pct, subs_gained, likes, shares, comments, engaged_views), perf_traffic (video_id, date, source_type, views), retention_curves (video_id, captured_at, day_after_publish, points_json), perf_reach (video_id, date, impressions, ctr, source_report), analytics_runs (date, channel_id, rows, status, error).
2. factory/analytics/pull.py : `factory analytics pull [--channel X] [--since J-5]` → pour chaque chaîne authentifiée : perf_daily pour toutes les vidéos publiées (fenêtre glissante des 5 derniers jours + rattrapage depuis la publication au premier passage), perf_traffic, courbe de rétention capturée à J+7 et J+30 (et une fois à J+2 pour le premier retour), rapports reach et basic téléchargés par job (nouveaux fichiers seulement, stockés dans workspace/analytics/reports/ puis chargés dans perf_reach), journal et analytics_runs ; erreurs tolérées par chaîne ; quota compté.
3. Vue v_video_perf : jointure runs/manifestes (extrait les champs facteurs du manifest.json indexé dans la table runs : ajoute une colonne manifest_json ou des colonnes matérialisées) × publications × agrégats perf_daily à 7 et 30 jours × CTR moyen à 7 jours × abonnés gagnés ; colonnes facteurs : topic, topic_cluster, topic_source, hook_type, title_pattern, thumbnail_template, thumbnail_text_len, style, template_id, cut_rhythm_target_s, cut_rhythm_measured_s, duration_s, lang, niche, voice_id, publish_weekday, publish_hour, density_facts_per_min, qc_score, is_child ; métriques : views_7d, views_30d, avg_view_pct_7d, avg_view_duration_7d, ctr_7d, impressions_7d, subs_7d.
4. `factory analytics show --video <id>` : tableau des métriques, courbe de rétention en ASCII (100 points → 50 colonnes), chutes > 5 points rattachées aux segments du script via voice/timings.json (« chute de 8 pts à 01:42 : segment 4, rôle point, début du sponsor ») ; `factory analytics show --channel X` : tableau par vidéo.
5. Planification : plist com.bms.factory.analytics quotidien (matin, après la collecte concurrentielle) ; charge-le.
6. Exécute pull ; vérifie les tables ; affiche show pour une vidéo publiée depuis ≥ 3 jours.
7. Commit « étape 25 : performances jointes au manifeste ».
</tache>

<contraintes>
- Aucune donnée d'une chaîne non détenue (l'API ne le permet pas de toute façon) ; les jetons restent dans secrets/.
- Les rapports téléchargés sont stockés bruts puis chargés ; jamais lus dans la conversation (comptages seulement).
- Latence : ne conclus jamais « 0 vue » pour une vidéo de moins de 72 h.
</contraintes>

<criteres_de_validation>
Montre : sqlite3 "select count(*) from perf_daily; select count(*) from retention_curves; select count(*) from perf_reach; select * from analytics_runs order by date desc limit 3;" ; sqlite3 "select * from v_video_perf limit 2;" (colonnes) ; la sortie de factory analytics show --video pour une vidéo ; launchctl list | grep analytics.
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 25 terminée, vidéos suivies, disponibilité des rapports reach (oui/non, depuis quand), premières observations de rétention (chutes rattachées à quels segments), heure de la tâche. Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + INTERFACES (manifest) + db/migrations + reporting_jobs + oauth + requête | 10 000 |
| Prompt (~1 450 mots) | 2 200 |
| 1 rapport de sous-agent | 1 300 |
| Écriture migration + pull.py (≈ 350 lignes) | 4 700 |
| Écriture vue SQL + show (≈ 180 lignes) | 2 400 |
| Plist + CLI (≈ 60 lignes) | 800 |
| Exécutions et sorties API (extraits) | 4 000 |
| Corrections | 3 500 |
| Mise à jour STATE.md + résumé | 800 |
| Sous-total | 47 700 |
| Marge +25 % | 11 925 |
| **Total** | **59 625 tk — 29,8 %** |

## Étape 26 — Apprendre et réinjecter ; valider le banc contre les vues

**Objectif.** Livrer `factory learn` : à partir de la vue de performance, estimer l'effet de chaque facteur de production avec des méthodes adaptées aux petits échantillons (rétrécissement bayésien, intervalles crédibles, seuil de n), analyser les courbes de rétention par segment, produire `learned/weights.json` consommé par les sujets, les hooks, les titres, le rythme, les créneaux et la rotation des miniatures, vérifier la corrélation du score du banc avec les résultats, et écrire un rapport lisible « ce que le système a appris ».
**Pourquoi maintenant.** C'est le mécanisme qui transforme l'outil en actif ; il doit exister avant l'industrialisation, même avec peu de données, pour que chaque vidéo suivante en profite.
**Valeur créée.** Thèse n° 2 (le système devient plus rentable à chaque vidéo) et n° 3 (le banc est validé, pas supposé).
**Pré-requis.** Étape 25 terminée (≥ 5 vidéos avec 7 jours de données, idéalement plus).
**Sous-agents.** Vague 1 : (A) méthodes pour apprendre à partir de 10-50 observations : rétrécissement empirique de Bayes des effets par facteur, sélection de variantes par échantillonnage de Thompson, pièges des comparaisons multiples, normalisation par chaîne et par âge, exploitation des courbes de rétention ; vague 2 : (B) contradicteur sur les résultats (effets fallacieux, confusions, fuite d'information).
**Livrables.** `factory/analytics/learn.py`, `factory/analytics/retention_analysis.py`, `learned/weights.json` (versionné), `reports/learn_<date>.md`, consommateurs mis à jour (`topics.py`, `hooks.py`, `titles.py`, `shotlist.py`, `calendar.py`, `thumbnails_variants.py`), `tests/test_learn.py`.
**Poids disque.** 0.
**Terminé quand.** `factory learn` écrit `weights.json` et le rapport · les tests synthétiques prouvent le rétrécissement (un effet observé sur n = 2 est ramené vers 0 ; sur n = 40, conservé) · `factory plan` produit une liste de 10 sujets différente avec et sans poids (diff affiché) · le rapport contient la section « Banc vs résultats » (corrélation score ↔ vues et rétention, avec n) et une décision sur les seuils · objections traitées.

**Prompt à copier-coller :**

````text
Tu es statisticien appliqué et développeur ; tu fais apprendre un système à partir de peu de données sans lui faire croire des choses fausses.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local. La vue v_video_perf relie, pour chaque vidéo publiée, ses facteurs de production à ses résultats. Cette session construit l'apprentissage : effets par facteur (type de hook, patron de titre, template de miniature, rythme mesuré, durée, style, cluster de sujet, créneau, densité, langue) avec rétrécissement vers zéro quand n est petit, intervalles crédibles, normalisation par chaîne et par âge ; analyse des courbes de rétention par segment (où les gens partent) ; poids exportés dans learned/weights.json et lus par les modules qui décident (sujets, hooks, titres, rythme, créneaux, rotation des miniatures) avec repli sur le référentiel quand n est insuffisant ; validation du banc (le score prédit-il les vues et la rétention ?). Les données sont peu nombreuses au début : le rapport doit dire l'incertitude, jamais l'effacer.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 26 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 26 \|^## Étape 27 " ROADMAP.md puis Read en offset/limit.
2. STATE.md
3. sqlite3 workspace/factory.db "select count(*) from v_video_perf where views_7d is not null;" et les colonnes de la vue (pragma).
4. docs/QC.md — formule du score et procédure de recalibration.
5. Les points d'extension prévus : grep -n "weights" factory/editorial/topics.py factory/retention/hooks.py factory/editorial/titles.py factory/steps/shotlist.py factory/publish/calendar.py factory/editorial/thumbnails_variants.py.
</demarrage>

<sous_agents>
Vague 1 — 1 sous-agent (recherche, sources statistiques sérieuses) : méthodes praticables en Python pur ou numpy pour 10-50 observations : estimation d'effets par facteur avec rétrécissement empirique de Bayes (formules), intervalles crédibles, normalisation des vues par chaîne et par âge (log-ratio à la médiane de la chaîne à âge égal), échantillonnage de Thompson pour choisir entre variantes (titres, miniatures) avec a priori, seuil de n avant d'agir, pièges (comparaisons multiples, confusion avec la date de publication, régression vers la moyenne), exploitation des courbes de rétention (détection de chutes, comparaison à la courbe moyenne de la chaîne). 450 mots maximum, formules et références.
Vague 2 — après le premier rapport learn, 1 contradicteur : effets probablement fallacieux au vu de n, confusions (âge, chaîne, saison), fuite d'information (un facteur calculé après publication), poids qui amplifieraient un biais (toujours le même hook), ce qui devrait être gelé jusqu'à n ≥ seuil. 400 mots maximum, « Problème → correction ».
</sous_agents>

<tache>
1. factory/analytics/learn.py : (a) cible principale y = log(views_7d ÷ médiane de la chaîne à âge égal) ; cibles secondaires avg_view_pct_7d et ctr_7d ; (b) pour chaque facteur catégoriel : effet moyen par niveau avec rétrécissement empirique de Bayes vers 0 (variance inter-niveaux estimée), intervalle crédible, n ; pour les facteurs continus (rythme mesuré, durée, densité) : effet par tranche (tercile) ; (c) analyse des courbes de rétention : retention_analysis.py aligne chaque courbe sur les segments du script (timings), calcule la chute par rôle de segment (hook, point, rupture, sponsor, conclusion) et par position, compare à la courbe moyenne de la chaîne, produit des règles candidates (« sponsor avant 40 % : chute moyenne de 9 pts, n=6 ») ; (d) learned/weights.json (version, date, n_videos, par facteur : niveaux → multiplicateur borné [0,7 ; 1,4] et n, hooks.parts ajustées, titles.patterns ajustés, cut_rhythm par niche ajusté ±20 % max autour du référentiel, creneaux par chaîne, thumbnail_policy avec paramètres Thompson par template, retention_rules[]) ; règle de garde : un facteur avec n < seuil (config/editorial.yaml, 8 par niveau par défaut) garde un multiplicateur de 1,0 ; (e) rapport reports/learn_<date>.md en français lisible : ce qui est appris avec n et incertitude, ce qui n'est pas encore décidable, les règles de rétention candidates, la section « Banc vs résultats » (corrélation de Spearman entre qc_score et y, entre les composantes du score et avg_view_pct, avec n ; décision : seuils inchangés / durcis / assouplis et pourquoi), les 5 actions que le système va changer.
2. Consommateurs : topics.py (multiplicateur de cluster et de niche), hooks.py (parts), titles.py (poids des patrons), shotlist.py (cible de rythme ajustée), calendar.py (créneaux), thumbnails_variants.py (politique Thompson : choisir la variante initiale et proposer la rotation à J+7 via thumbnails.set si le CTR est sous la médiane de la chaîne — commande `factory analytics rotate-thumbnails --dry-run`) ; chacun lit weights.json s'il existe et si la version est compatible, sinon repli référentiel ; journalise quel poids a été appliqué dans le manifeste (learned_version).
3. tests/test_learn.py avec données synthétiques : rétrécissement (n=2 → effet ramené proche de 0 ; n=40 → conservé), bornes des multiplicateurs, repli quand weights absent, alignement des courbes sur segments, corrélation calculée (≥ 8 tests).
4. Exécute `factory learn` sur les données réelles ; puis `factory plan --channel bms-science-fr --dry-run --n 10` avec et sans learned/weights.json (renomme temporairement) et montre le diff des deux listes.
5. Lance le contradicteur ; applique ses corrections (gel de facteurs, seuils) ; consigne « Objections » dans le rapport.
6. Commit « étape 26 : apprentissage et réinjection ».
</tache>

<contraintes>
- Aucun facteur calculé après publication ne peut servir de prédicteur (fuite) : vérifie chaque colonne.
- Les multiplicateurs sont bornés et le repli sur le référentiel est toujours possible (le système ne peut pas s'emballer sur un seul hook).
- Le rapport écrit « non décidable (n=…) » plutôt qu'une conclusion.
</contraintes>

<criteres_de_validation>
Montre : uv run pytest tests/test_learn.py -q ; head -40 learned/weights.json ; la section « Banc vs résultats » du rapport ; le diff des deux listes de 10 sujets ; les objections traitées.
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 26 terminée, n disponible, facteurs actifs et gelés, décision sur les seuils du banc, prochaine date de learn (hebdomadaire via le daemon). Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + colonnes de la vue + QC.md (extraits) + points d'extension | 9 500 |
| Prompt (~1 550 mots) | 2 400 |
| 1 rapport de sous-agent + 1 contradicteur | 2 700 |
| Écriture learn.py + retention_analysis.py (≈ 400 lignes) | 5 300 |
| Mise à jour des 6 consommateurs (≈ 150 lignes) | 2 000 |
| Tests (≈ 120 lignes) | 1 600 |
| Exécutions et diff (extraits) | 3 500 |
| Lecture du rapport produit (≈ 150 lignes) | 2 000 |
| Corrections | 3 500 |
| Mise à jour STATE.md + résumé | 800 |
| Sous-total | 51 300 |
| Marge +25 % | 12 825 |
| **Total** | **64 125 tk — 32,1 %** |

## Étape 27 — Affiliation, funnel et économie unitaire

**Objectif.** Intégrer l'affiliation et le funnel dans le pipeline (liens avec sous-identifiant par vidéo, segment d'appel à l'action, commentaire épinglé, import des conversions), calculer le coût réel par vidéo (temps de calcul, énergie, temps humain de relecture) et le revenu par vidéo (publicité si YPP, affiliation par sous-identifiant), agrégés par niche, langue, chaîne et style, avec un rapport qui dit où investir.
**Pourquoi maintenant.** Sans économie unitaire, impossible de décider où produire ni quand payer un serveur (section 8).
**Valeur créée.** Thèse n° 2 (la boucle inclut l'argent) et jalon serveur chiffré.
**Pré-requis.** Étape 25 terminée · étape 21 (sous-identifiants) · manifestes avec coûts (13.2).
**Sous-agents.** 1 — programmes d'affiliation accessibles sans frais depuis la France avec export des conversions par sous-identifiant (Amazon Partenaires, Awin, CJ, Impact, Digistore24, ClickBank) : paramètre de sous-identifiant, format d'export CSV ou API, durée de cookie, conditions de divulgation ; et disponibilité de `estimatedRevenue` via l'Analytics API (scope monétaire, condition YPP). 450 mots maximum.
**Livrables.** `factory/monetization/links.py`, `import_revenue.py`, `economics.py`, `factory economics`, `factory revenue import`, table `revenue`, `reports/economics.md`, template de segment d'appel à l'action dans les prompts.
**Poids disque.** 0.
**Terminé quand.** Un run avec produit configuré porte des liens avec sous-identifiant = video_id dans la description et le commentaire épinglé · l'import d'un CSV de test (fixture au format d'un programme) rattache des conversions à une vidéo · `reports/economics.md` donne le coût réel par vidéo et par minute par style (calculé depuis les manifestes), le revenu par vidéo (réel ou 0), les agrégats par niche, langue, chaîne, style, et 3 décisions chiffrées.

**Prompt à copier-coller :**

````text
Tu es contrôleur de gestion et développeur ; tu mesures ce que coûte et ce que rapporte chaque vidéo, sans hypothèse cachée.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local. Le but business est la vente de produits et l'affiliation. Cette session branche l'affiliation dans le pipeline (liens avec sous-identifiant par vidéo pour attribuer les conversions, segment d'appel à l'action, commentaire épinglé, import des conversions), calcule le coût réel par vidéo (temps de calcul × puissance × prix du kWh, temps humain de relecture × taux, part des coûts fixes) et le revenu par vidéo (publicité via estimatedRevenue si la chaîne est dans le YPP, affiliation par sous-identifiant), puis agrège par niche, langue, chaîne et style. YouTube Shopping n'est pas disponible en France : l'affiliation passe par des programmes externes. Les mentions obligatoires (docs/CONFORMITE.md §3) sont déjà gérées par precheck ; ne les contourne jamais.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 27 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 27 \|^## Phase 6 " ROADMAP.md puis Read en offset/limit.
2. STATE.md
3. config/products/exemple-affilie.yaml ; factory/editorial/seo.py — bloc affiliation (grep -n "affil\|sub") ; docs/INTERFACES.md — manifest.cost.
4. sqlite3 : colonnes de v_video_perf ; un manifest.json (section cost et timings) via python -c.
</demarrage>

<sous_agents>
Lance 1 sous-agent (recherche web, pages officielles des programmes) : pour Amazon Partenaires (FR/EN/ES/IT), Awin, CJ, Impact, Digistore24, ClickBank : conditions d'inscription sans frais depuis la France, paramètre de sous-identifiant par lien (nom exact), export des conversions (CSV, API, granularité, délai), durée de cookie, obligations de mention ; et pour YouTube : métrique estimatedRevenue de l'Analytics API (scope yt-analytics-monetary.readonly, condition YPP, granularité, délai). 450 mots maximum, tableau PROGRAMME | SOUS-ID | EXPORT | COOKIE | CONDITIONS | URL.
</sous_agents>

<tache>
1. config/products/<id>.yaml enrichi : program, base_url, tracking_param (nom du paramètre de sous-identifiant), sub_id_format ("{video_id}" ou "{channel_id}-{video_id}"), disclosure par langue, cta_text par langue, landing_type, commission_hint (optionnel, source) ; factory/monetization/links.py : build_links(run) → liens avec sous-identifiant, écrits dans le manifeste (affiliate_links[]) et consommés par seo.py (description, commentaire épinglé) ; segment d'appel à l'action : template dans factory/prompts (script.py insère un segment cta après la conclusion si produit, avec la mention orale et le bandeau ; vérifie que retention/verify et precheck l'acceptent).
2. factory/monetization/import_revenue.py : `factory revenue import --program amazon --file export.csv` → parseurs par programme (colonnes du rapport) → table revenue (video_id, channel_id, source : ads | affiliate, program, date, clicks, conversions, amount, currency, imported_at) via le sous-identifiant ; `factory revenue pull-ads` → estimatedRevenue par vidéo et par jour depuis l'Analytics API si le scope et le YPP le permettent, sinon message clair ; fixtures de test tests/fixtures/revenue_<program>.csv.
3. factory/monetization/economics.py : `factory economics [--since 90d]` → coût par vidéo = compute_min × puissance (config, W) × prix kWh (config) + minutes de relecture (review_log : durée entre affichage et décision, sinon forfait config) × taux horaire (config) + part des coûts fixes (config : 0 aujourd'hui, serveur plus tard) ; revenu par vidéo = ads + affiliation ; agrégats par niche, langue, chaîne, style (coût moyen, coût par minute de vidéo, revenu moyen, marge, délai de retour) ; reports/economics.md : tableaux, hypothèses explicites (chaque paramètre de config cité avec sa valeur), série temporelle du coût par vidéo (la vidéo n° 1 vs la dernière : effet de la bibliothèque), 3 décisions chiffrées (par exemple : « la niche X en EN coûte 0,9 € et rapporte 0 € après 30 jours avec n=4 : non décidable ; la niche Y… ») et les données manquantes pour décider.
4. Exécute : build_links sur un run avec produit ; import de la fixture ; economics sur les données réelles (revenu réel probablement 0 : dis-le).
5. Commit « étape 27 : affiliation et économie unitaire ».
</tache>

<contraintes>
- Aucune donnée personnelle dans les sous-identifiants ; aucune mention contournée.
- Les hypothèses économiques sont dans config/economics.yaml, jamais dans le code.
- Le rapport distingue mesuré, importé et estimé.
</contraintes>

<criteres_de_validation>
Montre : la description d'un run avec le lien et son sous-identifiant ; sqlite3 "select * from revenue limit 5;" après import de la fixture ; les tableaux de reports/economics.md (coût par vidéo et par minute par style, agrégats) ; les 3 décisions.
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 27 terminée, phase 5 close si le jalon est atteint, coût réel par vidéo et par minute par style, revenu constaté, produits réels à configurer (Alek), programmes d'affiliation à ouvrir (Alek). Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + produit yaml + extraits seo/INTERFACES + colonnes + manifeste | 9 000 |
| Prompt (~1 350 mots) | 2 000 |
| 1 rapport de sous-agent | 1 300 |
| Écriture links.py + template CTA (≈ 160 lignes) | 2 100 |
| Écriture import_revenue.py + fixtures (≈ 200 lignes) | 2 700 |
| Écriture economics.py + config (≈ 260 lignes) | 3 500 |
| Exécutions (extraits) | 3 000 |
| Lecture du rapport produit (≈ 120 lignes) | 1 600 |
| Corrections | 2 500 |
| Mise à jour STATE.md + résumé | 800 |
| Sous-total | 46 500 |
| Marge +25 % | 11 625 |
| **Total** | **58 125 tk — 29,1 %** |

## Phase 6 — Industrialisation et transmission

**Objectif de la phase.** Rendre le système exploitable par Alek et Sofiane sans lire de code (tableau de bord, documentation), capitaliser (bibliothèque d'assets, voix et personnages cohérents, chartes, avatar 2D), étendre les styles (motion design, whiteboard) et fixer le plan de passage à l'échelle avec des critères chiffrés pour le serveur GPU.
**Jalon de phase.** Un testeur qui ne connaît pas le projet, muni de `docs/EXPLOITATION.md` et du tableau de bord, réussit ≥ 5 des 6 scénarios d'exploitation sans poser de question · les six moteurs de style sont sélectionnables par configuration et passent le banc · `docs/SCALE.md` donne les critères chiffrés de bascule et deux options de serveur datées.

## Étape 28 — Tableau de bord d'exploitation

**Objectif.** Livrer un tableau de bord local (Streamlit, Apache-2.0) qui permet de superviser la file, relire les scripts, lire les performances et ce que le système a appris, gérer la file de sujets, modifier la configuration des chaînes avec validation, lire le journal et les blocages, sans terminal.
**Pourquoi maintenant.** L'exploitabilité par un tiers est la condition pour que le système soit un actif et non une prestation de Thomas.
**Valeur créée.** Thèse n° 6.
**Pré-requis.** Étapes 22.2 et 26 terminées.
**Sous-agents.** 1 — patrons Streamlit 2026 pour un outil d'exploitation local : formulaires d'édition YAML sûrs, lancement de commandes en arrière-plan, rafraîchissement automatique, tests `AppTest`, et alternatives (NiceGUI) si Streamlit pose problème sur macOS. 350 mots maximum.
**Livrables.** `dashboard/app.py`, `dashboard/pages/*.py`, `factory dashboard`, `docs/img/dashboard_*.png`, `tests/test_dashboard.py`.
**Poids disque.** ≈ 0,2 Go (dépendances).
**Terminé quand.** Les 8 pages se rendent sans erreur (tests `AppTest`) · approuver un script depuis l'interface écrit une ligne dans `review_log` avec le relecteur choisi · modifier la cadence d'une chaîne depuis l'interface passe par `factory config validate` et persiste · 3 captures d'écran sont dans `docs/img/` et regardées.

**Prompt à copier-coller :**

````text
Tu es développeur d'outils internes ; tu construis des interfaces sobres que des non-développeurs utilisent 10 minutes par jour sans formation.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local. Le système tourne seul (daemon), apprend (learn) et publie ; ses exploitants finaux, Alek et Sofiane, ne lisent pas de code. Cette session livre le tableau de bord local en Streamlit (Apache-2.0), en français avec bascule anglais, qui couvre la routine quotidienne : voir l'état, relire les scripts par lots, lire les performances et les apprentissages, arbitrer la file de sujets, régler la configuration des chaînes avec validation, comprendre les blocages. Tout passe par les commandes et les tables existantes : le tableau de bord n'introduit aucune logique métier nouvelle.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 28 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 28 \|^## Étape 29 " ROADMAP.md puis Read en offset/limit.
2. STATE.md
3. factory/cli.py — liste des commandes et de leurs options (grep -n "@app.command\|def ").
4. Les tables et vues de workspace/factory.db (sqlite3 .tables ; pragma table_info des principales : jobs, runs, review_log, topics_queue, v_video_perf, publications).
5. factory/orchestrator/review.py — fonctions d'approbation (grep -n "def ").
</demarrage>

<sous_agents>
Lance 1 sous-agent (recherche web, documentation Streamlit) : version courante de Streamlit et compatibilité macOS/Python 3.12 ; patrons pour éditer un YAML avec validation avant sauvegarde ; lancer une commande longue en arrière-plan et afficher son état ; rafraîchissement automatique (st.fragment, autorefresh) ; tests avec streamlit.testing AppTest ; internationalisation simple ; pièges (état de session, rerun) ; NiceGUI (MIT) en repli si Streamlit bloque. 350 mots maximum, points numérotés avec URL.
</sous_agents>

<tache>
1. dashboard/app.py + dashboard/pages/ (une page par fichier), textes dans dashboard/i18n/{fr,en}.yaml :
   1. Vue d'ensemble : jobs par statut, digest du jour, disque, mémoire, daemon (actif ?), quota API du jour, dernière sauvegarde, alertes récentes.
   2. Production : tableau des runs (chaîne, sujet, étape, statut, score QC, date prévue) avec actions (relancer, bloquer avec motif, prioriser), aperçu de la miniature et lien vers final.mp4 (ouverture locale).
   3. Relecture : scripts en attente, affichage compact (titre, hook, angle, durée, densité, texte complet dépliable), boutons Approuver / Rejeter (motif) / Éditer (zone de texte, re-validation), sélection du relecteur (config/team.yaml) ; écrit review_log via review.py.
   4. Performances : par chaîne, vues 7 j et 30 j, pourcentage moyen, CTR (si reach), top et flop 5, courbe de rétention d'une vidéo choisie avec chutes annotées, résumé de learned/weights.json (ce qui est appris, avec n), bouton « Recalculer (learn) ».
   5. Éditorial : classement des niches, file de sujets par chaîne (score, preuves, statut) avec Approuver / Bannir, bouton « Rafraîchir les sujets ».
   6. Configuration : formulaires par chaîne (cadence, jours et heures, style, templates, voix, auto_approve avec avertissement rouge et confirmation, produits, derive_from), assistant « Ajouter une chaîne » (compte, jeton via commande à exécuter, niche, style, langue), validation par factory config validate avant sauvegarde, sauvegarde du fichier précédent en .bak.
   7. Journal : blocages avec raisons et remèdes possibles, tail de factory.log filtrable, événements d'un run.
   8. Aide : contenu de docs/EXPLOITATION.md (quand il existera : lien) et la liste des commandes utiles.
   `factory dashboard` lance streamlit sur localhost:8501 ; option --agent pour un plist launchd.
2. tests/test_dashboard.py avec AppTest : chaque page se rend sans exception ; approbation d'un script de test écrit review_log ; édition de cadence refusée si invalide, acceptée si valide.
3. Captures : lance le tableau de bord, prends 3 captures (Playwright ou capture système) des pages Vue d'ensemble, Relecture, Performances dans docs/img/ ; regarde-les (lisibilité, textes en français, rien de tronqué).
4. Commit « étape 28 : tableau de bord ».
</tache>

<contraintes>
- Aucune logique métier dans le tableau de bord : il appelle les modules de factory.
- Aucun secret affiché (jetons, clés) ; l'assistant d'ajout de chaîne affiche la commande à exécuter, pas les valeurs.
- Trois captures regardées au maximum.
</contraintes>

<criteres_de_validation>
Montre : uv run pytest tests/test_dashboard.py -q ; sqlite3 "select * from review_log order by timestamp desc limit 1;" après approbation depuis l'interface ; le diff du YAML de chaîne modifié ; ls docs/img/.
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 28 terminée, URL locale, pages disponibles, limites connues. Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + commandes CLI + schéma des tables + review.py | 10 000 |
| Prompt (~1 300 mots) | 2 000 |
| 1 rapport de sous-agent | 1 100 |
| Écriture app.py + 8 pages + i18n (≈ 600 lignes) | 8 000 |
| Tests (≈ 100 lignes) | 1 300 |
| Exécutions et tests (extraits) | 3 000 |
| Inspection de 3 captures | 4 500 |
| Corrections | 4 000 |
| Mise à jour STATE.md + résumé | 800 |
| Sous-total | 52 700 |
| Marge +25 % | 13 175 |
| **Total** | **65 875 tk — 32,9 %** |

## Étape 29 — Bibliothèque d'assets, voix et personnages cohérents, avatar 2D, chartes

**Objectif.** Organiser le rendement composé : bibliothèque d'assets indexée et réutilisée sémantiquement (images, clips, musiques, sons, intros), profils de voix par chaîne, personnages récurrents cohérents, moteur « avatar 2D » (personnage en calques + Rhubarb Lip Sync) utilisable en incrustation ou en présentateur, chartes versionnées avec templates en rotation, et mesure du coût de la vidéo n par rapport à la vidéo 1.
**Pourquoi maintenant.** Après 20 à 30 vidéos, la bibliothèque existe de fait ; il faut la rendre exploitable et prouver que le coût baisse.
**Valeur créée.** Thèse n° 7 (rendement composé) et n° 5 (variation par templates).
**Pré-requis.** Étapes 17 et 26 terminées · Rhubarb installé.
**Hérité de l'étape 5.2 (mesuré).** **Le visage d'un personnage tient d'une graine à l'autre, la tenue non.** Trois graines sur la même description donnent le même visage (4/5 par Thomas) mais une chemise unie ou à carreaux selon la graine. Ici, l'enjeu est la **récurrence d'un personnage d'une vidéo à l'autre** : la fiche de personnage doit figer la tenue (motif, couleur, poches, col) en plus du visage, sans quoi la chaîne perd son identité visuelle. *Le même défaut, vu entre deux plans d'une même vidéo, est traité à l'**étape 12.2**.* Planche : `benchmarks/samples/visuel/coherence_planche.png`, mesures dans `benchmarks/RESULTATS.md` § 2.3.
**Rhubarb : pas de recompilation arm64**, le binaire x86_64 tourne sous **Rosetta 2** (mesuré : 6,2 s pour 53 s de français en `-r phonetic`).
**Sous-agents.** 1 — kits de personnages 2D en calques à licence commerciale (Open Peeps CC0, humaaans, autres), structure de calques pour un lip-sync par visèmes (correspondance des formes de bouche A-H, X de Rhubarb), techniques de clignement et de balancement de tête, et méthode de cohérence d'un personnage généré (même description, graine, image de référence) avec le modèle image retenu. 400 mots maximum.
**Livrables.** `factory/library.py`, `factory library scan|stats|find`, `config/voices/*.yaml`, `config/chartes/<channel>.yaml` (≥ 2 chartes avec ≥ 3 templates), `workspace/library/characters/<id>/` (calques), `factory/styles/avatar2d.py`, `reports/compound.md`.
**Poids disque.** ≈ 0,2 Go (personnages et calques).
**Terminé quand.** `factory library stats` affiche les comptes par type et le taux de réutilisation sur les 10 derniers runs · un run avec `avatar2d` (incrustation sur un autre style ou présentateur) passe `factory qc` et la synchronisation labiale est visible sur 3 images extraites à des visèmes différents · ≥ 2 chartes avec ≥ 3 templates chacune et `charte_version` dans les manifestes · `reports/compound.md` compare le coût et le temps de la vidéo 1 et des 5 dernières, et explique l'écart.

**Prompt à copier-coller :**

````text
Tu es directeur artistique technique ; tu rends une production répétable moins chère et plus cohérente à chaque vidéo.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local. Un système sans capitalisation refait le même travail à chaque vidéo. Cette session organise le rendement composé : bibliothèque d'assets indexée (déjà alimentée par images.py, stock.py, music.py) avec réutilisation sémantique, profils de voix par chaîne, personnages récurrents cohérents, moteur « avatar 2D » (personnage en calques animé par les visèmes de Rhubarb Lip Sync, MIT) en incrustation ou en présentateur pour le hook et l'appel à l'action, chartes versionnées avec ≥ 3 templates en rotation (docs/CONFORMITE.md §5), et mesure du coût de la vidéo n par rapport à la première. L'avatar réaliste généré est hors périmètre local (docs/STYLES.md).
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 29 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 29 \|^## Étape 30\.1 " ROADMAP.md puis Read en offset/limit.
2. STATE.md
3. factory/assets/images.py — cache et table assets_library (grep -n "library\|def ") ; factory/styles/base.py (entier) ; factory/styles/illustre.py — render_shot (grep -n).
4. docs/STYLES.md — ligne avatar ; benchmarks/RESULTATS.md — Rhubarb (grep -n -i rhubarb).
5. config/channels/bms-science-fr.yaml (charte actuelle).
</demarrage>

<sous_agents>
Lance 1 sous-agent (recherche web) : (1) kits de personnages 2D en calques à licence commerciale gratuite (Open Peeps CC0, humaaans, autres 2025-2026) : format (SVG/PNG), calques disponibles (corps, tête, yeux, bouches) ; (2) correspondance entre les visèmes de Rhubarb (A, B, C, D, E, F, G, H, X) et des formes de bouche dessinées ; (3) techniques simples de vie du personnage (clignement toutes les 3-5 s, micro-balancement de tête, respiration) en compositing PNG ; (4) méthode de cohérence d'un personnage généré par le modèle image retenu (description fixe, graine, image de référence si l'outil le permet) et détourage (rembg BiRefNet, MIT). 400 mots maximum, points numérotés avec URL.
</sous_agents>

<tache>
1. factory/library.py : index unifié de workspace/library (images, stock, music, sfx, characters, intros) dans assets_library (type, chemin, tags, source, licence, hachage perceptuel, embedding de la description, used_by, created_at) ; `factory library scan` (réindexe), `stats` (comptes par type, taille, taux de réutilisation sur les 10 derniers runs, top assets), `find "description"` (recherche sémantique via embed.py) ; réutilisation sémantique dans images.py et stock.py : si un asset de la bibliothèque a une similarité > 0,9 avec l'intention visuelle et n'a pas servi à la chaîne dans ses 10 derniers runs, il est réutilisé sans génération (journalisé) ; nettoyage : `factory library prune --unused-days 180`.
2. Voix : config/voices/<id>.yaml (moteur, identifiant de voix, vitesse, hauteur, langue, référence WAV éventuelle et ses droits consignés dans outils/LICENCES.md) ; chaque chaîne référence un voice_id ; vérifie que deux chaînes de même langue n'ont pas la même voix (validateur de config).
3. Personnages : workspace/library/characters/<id>/ avec base.png (généré : description fixe dans character.yaml, graine, détouré par rembg), calques mouths/A.png … X.png, eyes_open.png, eyes_closed.png (dérivés par génération avec la même description + variation de la bouche, puis détourage et recadrage ; ou kit CC0 si la génération n'est pas assez cohérente : décide sur 3 essais et documente) ; character.yaml (chaîne, description, graine, licence, calques).
4. factory/styles/avatar2d.py : StyleEngine « avatar2d » utilisable de deux façons (config/styles/avatar2d.yaml : mode overlay sur un autre style pour les segments hook et cta, ou mode présentateur plein cadre avec fond de charte) : Rhubarb sur voice/segment_XX.wav (mode phonetic pour les langues non anglaises) → timeline de visèmes → séquence PNG composée avec Pillow uniquement aux changements de visème et de clignement (pas 30 images identiques par seconde), balancement de tête sinusoïdal léger → clip avec alpha (ProRes 4444 ou PNG séquence) → composé par ffmpeg sur le clip du style hôte ; verify_clip.
5. Chartes : config/chartes/<channel>.yaml (polices OFL, palette, position des textes, transitions, ≥ 3 templates de mise en page, intro/outro de la bibliothèque, charte_version) pour ≥ 2 chaînes ; le manifeste enregistre charte_version et template_id ; la rotation des templates est vérifiée par precheck (pas deux fois le même template de suite sur une chaîne).
6. Exécute un run avec avatar2d en overlay (bms-science-fr) : qc ; extrais 3 images à des instants de visèmes différents (lis la timeline) et regarde-les ; mesure le temps ajouté par l'avatar.
7. reports/compound.md : depuis les manifestes : temps de calcul, coût, part d'assets réutilisés, nombre de générations d'images pour la vidéo 1 et les 5 dernières ; explication de l'écart ; ce qui reste à capitaliser.
8. Commit « étape 29 : bibliothèque, voix, personnages, avatar 2D, chartes ».
</tache>

<contraintes>
- Aucun kit ni image sans licence commerciale consignée dans LICENCES.md.
- Trois images regardées au maximum.
- Rhubarb en sous-processus ; Pillow pour le compositing ; pas de navigateur.
</contraintes>

<criteres_de_validation>
Montre : factory library stats ; ls workspace/library/characters/<id>/mouths ; qc.json du run avatar (PASS) ; les 3 instants extraits avec le visème attendu ; les tableaux de reports/compound.md.
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 29 terminée, taux de réutilisation, coût vidéo 1 vs dernières, personnages disponibles par chaîne, limites de l'avatar 2D. Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + extraits images/base/illustre + STYLES/RESULTATS + config | 9 500 |
| Prompt (~1 500 mots) | 2 400 |
| 1 rapport de sous-agent | 1 200 |
| Écriture library.py + intégration réutilisation (≈ 250 lignes) | 3 300 |
| Écriture voices/chartes yaml + validateur (≈ 140 lignes) | 1 900 |
| Génération et détourage des calques (extraits) | 2 500 |
| Écriture avatar2d.py (≈ 300 lignes) | 4 000 |
| Exécutions run + qc (extraits) | 3 500 |
| Inspection de 3 images | 4 500 |
| Écriture compound.md (≈ 80 lignes) | 1 000 |
| Corrections | 4 000 |
| Mise à jour STATE.md + résumé | 800 |
| Sous-total | 56 600 |
| Marge +25 % | 14 150 |
| **Total** | **70 750 tk — 35,4 %** |

## Étape 30.1 — Moteur « motion design » (Revideo)

**Objectif.** Livrer le moteur de composition programmatique : projet Revideo (MIT) avec des scènes paramétrées par JSON (typographie cinétique synchronisée aux mots, listes révélées, compteurs, grilles d'icônes, graphiques, bandeaux, transitions), piloté par la charte de la chaîne, et son adaptateur `StyleEngine`.
**Pourquoi maintenant.** C'est le style le plus fort du dispositif local (docs/STYLES.md : 5/5) et celui de la chaîne de référence CasiCreativo ; il arrive après la couche éditoriale et la boucle de mesure, conformément à l'ordre de la thèse.
**Valeur créée.** Thèse n° 3 (densité visuelle et rythme maîtrisés) et n° 7 (templates réutilisables).
**Pré-requis.** Étapes 15 et 7 terminées · Node installé · disque ≥ 10 Go.
**Sous-agents.** 1 — Revideo au jour de la session : création de projet, API de rendu sans interface, passage de props JSON, chargement de polices, options de performance (workers, parallélisme), installation de Chromium, problèmes connus sur Apple Silicon ; Motion Canvas en repli. 450 mots maximum.
**Livrables.** `render/` (projet Node), `render/src/scenes/*.ts` (≥ 6 scènes), `render/render.mjs`, `factory/styles/motion.py`, `config/styles/motion.yaml`, un run complet en style motion.
**Poids disque.** ≈ 0,8 Go (node_modules + Chromium), inscrit au ledger.
**Terminé quand.** `factory render --style motion` rend tous les plans d'un run et la vidéo passe `factory qc` · ≥ 6 types de scènes disponibles et paramétrés depuis la charte · temps de rendu par minute de vidéo mesuré et inscrit dans `RESULTATS.md` §3 · polices et palette de la charte visibles sur 3 images extraites.

**Prompt à copier-coller :**

````text
Tu es motion designer et développeur TypeScript ; tu construis des scènes paramétrées rendues sans interface.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local. Le motion design est le style le plus fort réalisable localement (docs/STYLES.md) et celui de CasiCreativo, référence du registre. Cette session crée le projet Revideo (MIT ; Remotion est évité pour sa licence limitée à 3 personnes) avec des scènes paramétrées par JSON — typographie cinétique synchronisée sur words.json, listes révélées, compteurs de chiffres, grilles d'icônes (Tabler Icons MIT ou Lucide ISC), graphiques simples à partir de données du script, bandeaux, transitions — pilotées par la charte de la chaîne, et l'adaptateur StyleEngine « motion » qui transforme chaque plan en scène et en rendu. Le rendu passe par Chromium sans interface ; sa vitesse sur M2 est à mesurer.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 30.1 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 30\.1 \|^## Étape 30\.2 " ROADMAP.md puis Read en offset/limit.
2. STATE.md
3. factory/styles/base.py (entier) ; factory/styles/cartes.py — structure d'un moteur ffmpeg ; docs/INTERFACES.md — contrat shotlist (visual_intent, on_screen_text) et Charte.
4. benchmarks/RESULTATS.md §2 — mesures Revideo de l'étape 5.2 (grep -n -i revideo).
5. config/chartes/bms-science-fr.yaml.
</demarrage>

<sous_agents>
Lance 1 sous-agent (recherche web + dépôt Revideo) : version courante, création de projet (npm), API de rendu sans interface (renderVideo : options, variables/props, résolution, fps, workers), chargement de polices locales, sons, performances rapportées et réglages (parallélisme, puppeteer/Chromium, mémoire), problèmes connus sur macOS Apple Silicon, procédure d'installation de Chromium ; Motion Canvas comme repli et différences. 450 mots maximum, points numérotés avec URL.
</sous_agents>

<tache>
1. render/ : projet Revideo (npm, versions épinglées, package-lock committé, node_modules ignoré) ; render/render.mjs : lit un fichier de spec JSON (scène, props, durée, fps, résolution, chemin de sortie, polices) et rend un MP4 par plan ou un MP4 pour une liste de plans en un seul lancement de Chromium (plus rapide) ; scènes dans render/src/scenes/ : kinetic-text (mots apparaissant au rythme de words.json, styles de la charte), list-reveal (points révélés un à un), stat-counter (chiffre animé avec libellé), icon-grid (icônes SVG libres + libellés), chart (barres ou lignes depuis des données du script : props data), lower-third (bandeau), quote (citation), transition-stinger ; toutes lisent palette, polices, marges depuis les props (charte) ; fond animé subtil ; bandeau « Publicité » si is_sponsor.
2. factory/styles/motion.py : StyleEngine « motion » : prepare_assets (icônes, données de graphique extraites du script par le LLM quand un segment contient des chiffres comparables) ; mapping visual_intent + rôle du segment → type de scène (règles + LLM pour les cas ambigus) ; écrit render/specs/<video_id>/*.json ; lance render.mjs en lot ; verify_clip ; alterne les scènes pour respecter la variété (pas deux fois la même scène de suite).
3. Mesure : rend un run complet (bms-science-fr, style motion) ; temps par plan, images par seconde de rendu, temps par minute de vidéo, pic mémoire de Chromium ; inscris dans benchmarks/RESULTATS.md §3 « Moteurs » ; si le rendu dépasse 8× temps réel, teste 1080p24 ou le rendu à 720p suivi d'un upscale ffmpeg et documente le compromis retenu.
4. qc sur la vidéo ; extrais 3 images et regarde-les (polices, palette, lisibilité, absence de débordement).
5. Inscris node_modules et Chromium au ledger (taille) ; commit « étape 30.1 : moteur motion design » (render/package-lock.json inclus).
</tache>

<contraintes>
- Revideo ou Motion Canvas uniquement (MIT) ; pas de Remotion.
- Icônes et polices à licence libre consignées dans LICENCES.md.
- Trois images regardées au maximum ; sorties de rendu vers les logs.
</contraintes>

<criteres_de_validation>
Montre : ls render/src/scenes (≥ 6) ; ls clips | wc -l = n_shots ; boucle ffprobe (0 erreur) ; qc.json (PASS) ; les mesures inscrites dans RESULTATS.md §3 ; le ledger mis à jour.
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 30.1 terminée, temps de rendu par minute, compromis de résolution, scènes disponibles. Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + base/cartes + extraits INTERFACES/RESULTATS + charte | 9 500 |
| Prompt (~1 350 mots) | 2 200 |
| 1 rapport de sous-agent | 1 300 |
| Écriture projet Revideo + 8 scènes + render.mjs (≈ 500 lignes) | 6 500 |
| Écriture motion.py (≈ 200 lignes) | 2 700 |
| Installation et rendus (extraits) | 5 000 |
| Inspection de 3 images | 4 500 |
| Corrections | 5 000 |
| RESULTATS §3 + ledger + STATE.md + résumé | 1 200 |
| Sous-total | 55 900 |
| Marge +25 % | 13 975 |
| **Total** | **69 875 tk — 34,9 %** |

## Étape 30.2 — Moteur « whiteboard »

**Objectif.** Livrer le moteur « whiteboard » : images au trait générées ou vectorisées (vtracer, MIT), animation de tracé progressif avec main dessinante, texte manuscrit, fond papier, couleurs marqueur de la charte.
**Pourquoi maintenant.** Style demandé par Alek, réalisable à 4/5 en local (docs/STYLES.md), qui réutilise le moteur de composition de 30.1.
**Valeur créée.** Thèse n° 4 (un style de plus par configuration) et n° 7 (scène réutilisable).
**Pré-requis.** Étape 30.1 terminée · vtracer installé.
**Sous-agents.** Aucun.
**Livrables.** `factory/styles/whiteboard.py`, `render/src/scenes/draw-svg.ts`, `config/styles/whiteboard.yaml`, un run complet en style whiteboard.
**Poids disque.** 0.
**Terminé quand.** Un run complet en style whiteboard passe `factory qc` · la main suit le tracé sur 3 images extraites à des instants différents · temps de rendu par plan inscrit dans `RESULTATS.md` §3 · le plafond de chemins SVG par image est appliqué (vérifié dans le journal).

**Prompt à copier-coller :**

````text
Tu es développeur créatif ; tu transformes des images en animations de tracé progressif convaincantes.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local. Le whiteboard animé est un style demandé par Alek et réalisable en local (docs/STYLES.md) : image au trait (générée par le modèle image avec un prompt « dessin au trait noir sur blanc » ou vectorisée depuis une illustration), vectorisation vtracer (MIT), animation stroke-dashoffset des chemins dans l'ordre de dessin, main PNG suivant l'extrémité du tracé, remplissage progressif, texte manuscrit avec une police OFL, fond papier, palette marqueur de la charte. Cette session s'appuie sur le projet Revideo de l'étape 30.1.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé » et « ## Étape 30.2 » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 30\.2 \|^## Étape 31 " ROADMAP.md puis Read en offset/limit.
2. STATE.md
3. factory/styles/motion.py (entier) ; render/render.mjs et une scène existante (kinetic-text) pour le style de code.
4. benchmarks/RESULTATS.md §2 — mesures vtracer et whiteboard de l'étape 5.2 (grep -n -i "vtracer\|whiteboard").
5. factory/assets/images.py — signature de génération (grep -n "def ").
</demarrage>

<tache>
1. factory/styles/whiteboard.py : StyleEngine « whiteboard » : prepare_assets : pour chaque plan, image au trait (prompt de style whiteboard : « clean black line art on white background, no shading, no text » + visual_intent ; réutilisation via la bibliothèque) → vtracer (mode contour, seuil de simplification, plafond de 400 chemins : au-delà, re-simplification) → SVG ; tri des chemins dans un ordre de dessin plausible (haut-gauche vers bas-droite, gros éléments d'abord) ; render_shot : spec JSON pour la scène draw-svg (SVG, durée de tracé = 80 % de la durée du plan, main PNG (2 variantes libres dessinées ou générées et détourées), couleur de trait et fond papier de la charte, texte à l'écran en police manuscrite OFL tracé de la même façon) ; bandeau « Publicité » si sponsor ; verify_clip.
2. render/src/scenes/draw-svg.ts : charge le SVG, anime stroke-dashoffset chemin par chemin selon l'ordre et la durée totale, calcule la position de l'extrémité courante (échantillonnage des chemins) pour placer la main avec un léger décalage et une rotation, fondu du remplissage après le tracé, léger tremblement de caméra optionnel.
3. Exécute un run complet en style whiteboard (bms-science-fr ou une niche home_hacks si configurée) ; qc ; extrais 3 images à 20 %, 50 %, 80 % d'un même plan et regarde-les (la main suit-elle le trait ? le résultat est-il lisible ?) ; mesure le temps par plan et inscris-le dans RESULTATS.md §3.
4. Si la génération d'images au trait n'est pas assez propre (traits doubles, aplats), documente le réglage (seuil vtracer, prompt) et le compromis retenu.
5. Commit « étape 30.2 : moteur whiteboard ».
</tache>

<contraintes>
- vtracer (MIT), pas potrace (GPL).
- Trois images regardées au maximum.
- Plafond de chemins appliqué et journalisé pour chaque image.
</contraintes>

<criteres_de_validation>
Montre : ls clips | wc -l = n_shots ; boucle ffprobe (0 erreur) ; qc.json (PASS) ; la ligne de journal du plafond de chemins ; le temps par plan inscrit dans RESULTATS.md §3.
</criteres_de_validation>

<fin_de_session>
Mets à jour STATE.md : étape 30.2 terminée, six moteurs disponibles (liste), temps par plan whiteboard, réglages. Commit. Résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP partiel + STATE + motion.py + render.mjs + scène + extraits RESULTATS/images.py | 9 000 |
| Prompt (~1 050 mots) | 1 600 |
| Écriture whiteboard.py (≈ 250 lignes) | 3 300 |
| Écriture draw-svg.ts (≈ 200 lignes) | 2 700 |
| Exécutions et rendus (extraits) | 4 000 |
| Inspection de 3 images | 4 500 |
| Corrections | 3 500 |
| RESULTATS §3 + STATE.md + résumé | 1 000 |
| Sous-total | 47 600 |
| Marge +25 % | 11 900 |
| **Total** | **59 500 tk — 29,8 %** |

## Étape 31 — Documentation d'exploitation, reprise et plan de passage à l'échelle

**Objectif.** Écrire la documentation qui rend l'actif transmissible : `EXPLOITATION.md` pour Alek et Sofiane (sans code), `REPRISE.md` pour un développeur tiers, `SCALE.md` avec les critères chiffrés de bascule vers le serveur GPU, deux options de serveur datées, le plan de migration et les briques payantes à envisager avec leur retour attendu ; valider la documentation par un test à l'aveugle.
**Pourquoi maintenant.** Dernière étape : tout existe, il faut que d'autres puissent le faire tourner et décider quand payer.
**Valeur créée.** Thèse n° 6 (exploitabilité) et jalon serveur (section 8) chiffré à partir des mesures réelles.
**Pré-requis.** Étapes 28, 29, 30.2 terminées · `reports/economics.md`, `reports/compound.md`, `benchmarks/RESULTATS.md`.
**Sous-agents.** Vague 1, 3 en parallèle : (A) offres GPU louées à ≤ 50 €/mois (à l'heure spot et à la demande : RunPod, Vast.ai, TensorDock, autres ; mensuel : Hetzner, OVH, Scaleway) avec débit attendu pour nos briques ; (B) approche de migration (image Docker du pipeline avec variantes CUDA des briques, Mac orchestrateur + worker GPU distant vs bascule complète, synchronisation des données, coûts de sortie) ; (C) briques payantes et leur retour (voix premium, génération vidéo à la seconde) avec prix 2026. Vague 2 : (D) testeur à l'aveugle qui suit `EXPLOITATION.md` sur 6 scénarios en mode simulation.
**Livrables.** `docs/EXPLOITATION.md`, `docs/REPRISE.md`, `docs/SCALE.md`, `docs/tests/blind_<date>.md`.
**Poids disque.** 0.
**Terminé quand.** Le testeur à l'aveugle réussit ≥ 5 des 6 scénarios sans question (rapport joint) et les points de confusion sont corrigés dans la doc · `SCALE.md` contient les critères chiffrés (section 8 de ROADMAP.md instanciée avec les mesures réelles), ≥ 2 options de serveur avec prix datés, le gain de débit estimé par brique, le plan de migration et un tableau des briques payantes avec retour attendu · `STATE.md` marque la roadmap terminée avec les questions ouvertes restantes.

**Prompt à copier-coller :**

````text
Tu es rédacteur technique senior et architecte ; tu écris pour deux publics distincts (exploitants non développeurs, développeur repreneur) et tu chiffres les décisions d'investissement.

<contexte>
Projet : système autonome de production de vidéos YouTube faceless (BMS), 0 €, local, exploité par Alek et Sofiane, construit par Thomas. Le système est complet ; sa valeur dépend maintenant de sa transmissibilité et d'un plan de passage à l'échelle crédible. Cette session écrit trois documents : EXPLOITATION.md (routine quotidienne et hebdomadaire sans code, à partir du tableau de bord et de quelques commandes copiables), REPRISE.md (carte du système pour un développeur : architecture, comment ajouter un style, une métrique, une source, une chaîne, une langue ; tests ; secrets ; mise à jour des modèles), SCALE.md (critères chiffrés de bascule vers un serveur GPU à ~50 €/mois, options de serveur datées, gain de débit attendu par brique, plan de migration avec retour arrière, briques payantes et retour attendu, modèle de coût à 10, 30 et 60 vidéos par mois). Un testeur à l'aveugle valide EXPLOITATION.md. Le budget de 50 €/mois est débloqué par Alek uniquement quand le projet est à ~90 % et sur critères de volume, jamais de faisabilité.
</contexte>

<demarrage>
Racine du projet : /Users/toms/Documents/Claude/Clients/Alek/Content-creation.
Lis, dans cet ordre :
1. ROADMAP.md — « ## 3. Contexte figé », « ## Étape 31 », « ## 8. Jalon de bascule vers le serveur » : grep -n "^## 3\. Contexte figé\|^## 4\.\|^## Étape 31 \|^## 7\.\|^## 8\.\|^## 9\." ROADMAP.md puis Read en offset/limit.
2. STATE.md (entier) et STATE-ARCHIVE.md (survol : grep des décisions).
3. docs/ARCHITECTURE.md (entier) ; docs/CONFORMITE.md — section « Opérationnel ».
4. reports/economics.md et reports/compound.md (tableaux) ; benchmarks/RESULTATS.md — coûts par minute par style et §3.
5. factory/cli.py — liste des commandes.
</demarrage>

<sous_agents>
Vague 1 — 3 sous-agents en parallèle, un seul envoi, 450 mots maximum chacun, tableaux exigés, prix datés avec URL :
- Agent A : offres de GPU loué compatibles avec ~50 €/mois — à l'heure (RunPod, Vast.ai, TensorDock, Lambda, autres 2026) pour RTX 3090/4090/A10/L4/L40S : prix spot et à la demande, stockage persistant, réseau ; au mois (Hetzner, OVHcloud, Scaleway, autres) ; pour chaque : heures de calcul obtenues pour 50 €, et débit attendu pour nos briques (génération d'images FLUX à 1024², TTS Chatterbox CUDA, Wan 2.2 5B en b-roll de 5 s, rendu Chromium) d'après des mesures publiées.
- Agent B : approche de migration d'un pipeline Python/Node local vers un worker GPU : conteneurisation (image Docker avec variantes CUDA des briques : vLLM ou ollama, TTS CUDA, diffusers FLUX, Wan 2.2), modèle « Mac orchestrateur + worker distant qui tire les jobs » vs bascule complète, synchronisation des runs et de la bibliothèque (rsync, rclone vers un stockage gratuit ou l'espace du serveur), secrets, coûts de sortie de données, retour arrière.
- Agent C : briques payantes envisageables après le jalon et leur retour attendu : voix premium (ElevenLabs et concurrents : prix 2026 par million de caractères, langues, clonage), génération vidéo (Kling, Runway, Higgsfield, Veo : prix à la seconde ou par crédit), outils d'analyse d'audience (vidIQ, TubeBuddy payants : prix, ce qu'ils apportent que nos données n'ont pas) ; pour chaque : coût par vidéo pour notre volume, gain plausible (CTR, rétention) et n de vidéos nécessaire pour le mesurer.
Vague 2 — après EXPLOITATION.md : 1 testeur à l'aveugle (Agent D) qui ne lit QUE docs/EXPLOITATION.md et exécute en mode simulation (commandes avec --dry-run ou --help, tableau de bord décrit) les 6 scénarios : démarrer et arrêter le système ; relire et approuver un lot de scripts ; traiter un job bloqué ; publier manuellement une vidéo privée dans Studio ; changer la cadence d'une chaîne ; ajouter une chaîne dans une nouvelle langue. Rapport 500 mots maximum : pour chaque scénario, réussi / bloqué à quelle phrase, question qu'il aurait posée.
</sous_agents>

<tache>
1. docs/EXPLOITATION.md (≈ 320 lignes, français, sans code hors commandes copiables) : ce que fait le système en une page ; démarrer, arrêter, vérifier (daemon, tableau de bord) ; routine quotidienne 10 minutes (digest, relecture par lots, bloqués, publication manuelle tant que l'audit n'est pas passé) ; routine hebdomadaire (performances, apprentissage, file de sujets, sauvegardes hors machine) ; ajouter une chaîne, une langue, un produit ; régler la cadence et les styles ; ce que signifient les alertes ; quoi faire quand : disque plein, quota dépassé, jeton expiré, audit reçu, vidéo bloquée, chaîne avertie par YouTube ; ce qu'il ne faut jamais faire (docs/CONFORMITE.md) ; glossaire.
2. docs/REPRISE.md (≈ 200 lignes) : carte du dépôt, DAG et contrats (renvois), base et tables, où sont les secrets, comment lancer les tests, comment ajouter un moteur de style / une métrique du banc / une source éditoriale / un programme d'affiliation, comment mettre à jour un modèle (ledger, doctor), dettes techniques connues (depuis STATE), conventions.
3. docs/SCALE.md (≈ 250 lignes) : capacité mesurée du Mac (vidéos par nuit par style, à partir des manifestes) ; critères de bascule instanciés (section 8 de ROADMAP.md avec les valeurs réelles : file approuvée vs capacité, taux de PASS, signal de marché, audit, économie) ; options de serveur (≥ 2, prix datés) et heures obtenues ; gain de débit par brique (mesuré ici vs publié là-bas) ; plan de migration en phases avec retour arrière ; briques payantes : tableau (brique, coût par vidéo à 30 vidéos/mois, gain attendu, n pour le mesurer, déclencheur) ; modèle de coût à 10 / 30 / 60 vidéos par mois (Mac seul, Mac + serveur, avec briques payantes) ; ce qui reste 0 €.
4. Lance le testeur à l'aveugle ; corrige EXPLOITATION.md pour chaque point de confusion ; joins son rapport dans docs/tests/blind_<date>.md ; relance-le une seconde fois seulement si un scénario était bloqué.
5. Mets à jour STATE.md : « roadmap terminée » avec la liste des questions ouvertes restantes pour Alek (comptes, produits, programmes d'affiliation, décision serveur) et les dettes techniques.
6. Commit « étape 31 : documentation et plan d'échelle ».
</tache>

<contraintes>
- EXPLOITATION.md ne contient aucun terme de code non expliqué ; chaque action est une suite de clics ou une commande à copier telle quelle.
- Tout prix est daté et sourcé ; toute capacité est mesurée (manifestes) ou marquée « estimée ».
- Aucune promesse de résultat d'audience.
</contraintes>

<criteres_de_validation>
Montre : wc -l des trois documents ; le tableau des scénarios du testeur (≥ 5/6 réussis) ; les critères chiffrés de SCALE.md avec leurs valeurs ; les deux options de serveur avec prix et date ; la section « roadmap terminée » de STATE.md.
</criteres_de_validation>

<fin_de_session>
Commit final. Résume en 15 lignes maximum : état du système (moteurs, chaînes, vidéos publiées, apprentissage actif), capacité mesurée, ce qui déclenchera le serveur, questions ouvertes pour Alek.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP (sections 3, étape 31, section 8) + STATE + ARCHITECTURE + CONFORMITE op. + rapports + CLI | 10 000 |
| Prompt (~1 550 mots) | 2 400 |
| 3 rapports de sous-agents (450 mots) | 3 600 |
| Écriture EXPLOITATION.md (≈ 320 lignes) | 4 300 |
| Écriture REPRISE.md (≈ 180 lignes) | 2 400 |
| Écriture SCALE.md (≈ 250 lignes) | 3 300 |
| Rapport du testeur à l'aveugle | 1 500 |
| Corrections de la documentation | 1 500 |
| Mise à jour STATE.md + résumé | 800 |
| Sous-total | 47 800 |
| Marge +25 % | 11 950 |
| **Total** | **59 750 tk — 29,9 %** |

## 7. Règles de session permanentes

Ces règles valent pour toutes les étapes ; l'étape 1 les condense dans `CLAUDE.md` (≤ 40 lignes), chargé à chaque session.

1. **Recontextualisation minimale.** Lire `ROADMAP.md` par sections (`grep -n "^## Étape N "` puis `Read` avec offset/limit), jamais en entier ; puis `STATE.md` ; puis uniquement les livrables nommés par le prompt. Une lecture non nécessaire est du contexte perdu pour le travail.
2. **Logs hors conversation.** Toute commande verbeuse (installation, build, ffmpeg, pip/uv, rendu, collecte) est redirigée vers un fichier de `workspace/logs/` ou du dossier de l'étape ; on n'affiche que `tail -20` ou un `grep` ciblé.
3. **Disque.** `df -h /` avant tout téléchargement ; jamais sous 8 Go libres ; chaque poids téléchargé est inscrit dans `outils/MODELES.md` (chemin, Go, étape, statut, licence) ; les modèles non retenus sont purgés avant la fin de l'étape ; caches (`HF_HOME`, MLX, `OLLAMA_MODELS`, `uv cache`) sous `models/` ou nettoyés ; cumul retenu **≤ 22 Go** (relevé de 18 à 22 le 15/09/2026 par Thomas, après la mesure de 21,52 Go en fin d'étape 5.2 — le **plancher de 8 Go libres reste la seule règle dure**).
4. **Mémoire.** Un seul modèle IA résident à la fois, dans un sous-processus qui se termine ; un seul run de production à la fois. Ce n'est pas une optimisation : c'est la condition pour que 16 Go tiennent.
5. **Preuve avant déclaration.** Exécuter la commande, ouvrir le fichier produit, mesurer (`ffprobe`, `ebur128`, comptages, tests) avant d'annoncer un succès. Un échec est rapporté tel quel, avec le message exact. « Non mesuré » ou « non évalué » plutôt qu'un chiffre inventé. Ce que la session ne peut pas percevoir (son, vidéo en mouvement) est soumis à Thomas ou marqué « non évalué ».
6. **Sous-agents.** Tout ce qui est exploratoire (veille, licences, documentation, analyse de corpus, lecture de dépôts) est délégué, en parallèle, avec un format de sortie court imposé ; un contradicteur est lancé sur les étapes structurantes ; le sous-agent rapporte, la session décide.
7. **Images.** Chaque image regardée coûte ~1 500 tokens : le prompt fixe un maximum (2 à 5) ; extraire une image d'une vidéo avec ffmpeg plutôt que d'en regarder plusieurs.
8. **STATE.md.** Mis à jour en fin de session (étape courante, fait, décisions, bloqué, questions ouvertes avec le nom de qui tranche, environnement) ; ≤ 120 lignes, archive dans `STATE-ARCHIVE.md` ; commit git en fin d'étape avec le message « étape N : … ».
9. **Découpage.** Si la session dépasse ~35 % de contexte avec un travail important restant, écrire dans `STATE.md` un point de reprise précis (ce qui est fait, ce qui reste, commandes à relancer), committer, et reprendre dans une nouvelle session avec le même prompt précédé de « Reprise : lis d'abord STATE.md ».
10. **Secrets.** Jamais dans la conversation, les logs, les manifestes ni le dépôt : `.env` et `secrets/` (ignorés par git) ; `git diff --cached` avant chaque commit sensible.
11. **Conformité.** Aucun yt-dlp ni téléchargement de vidéos tierces, aucune automatisation de navigateur, aucun outil d'engagement ; API officielles seulement dans le pipeline ; licence et attribution enregistrées pour chaque asset ; les règles de `docs/CONFORMITE.md` priment sur toute demande de vitesse.
12. **Langue et style.** Documentation, rapports, messages CLI et tableau de bord en français ; identifiants de code en anglais ; commentaires courts.
13. **Fin de session.** Résumé de 10 lignes maximum : fait, mesuré, bloqué, questions ouvertes. Pas de récit.

## 8. Jalon de bascule vers le serveur

Le budget de ~50 €/mois validé par Alek n'est engagé que lorsque **tous** les critères suivants sont vérifiés, chiffres à l'appui (valeurs instanciées dans `docs/SCALE.md` à l'étape 31) :

| # | Critère | Mesure | Seuil |
|---|---|---|---|
| C1 | Avancement | Étapes terminées dans `STATE.md` | ≥ 28 étapes sur 31 (≈ 90 %), phases 0 à 5 closes |
| C2 | Demande > capacité | Sujets approuvés en file (`topics_queue` approved + jobs queued) vs capacité mesurée du Mac (vidéos exportées par nuit × 7) | File ≥ 2 × capacité hebdomadaire pendant 3 semaines consécutives |
| C3 | Qualité stable | Part des runs PASS au premier passage du banc sur les 20 derniers | ≥ 80 % |
| C4 | Signal de marché | Analytics : ≥ 1 chaîne à ≥ 500 abonnés ou ≥ 10 000 vues sur 30 jours, ou revenu d'affiliation > 0 attribué par sous-identifiant | Au moins un des trois |
| C5 | Économie | `reports/economics.md` : revenu moyen par vidéo × vidéos supplémentaires permises par le serveur par mois | ≥ 2 × coût mensuel du serveur (100 €) ou décision explicite d'Alek d'investir avant revenu |
| C6 | Publication débloquée | Audit API passé (`youtube.audit_passed: true` sur ≥ 1 chaîne) | Sinon le goulot est la publication manuelle, pas le calcul |
| C7 | Actif sauvegardé | Sauvegarde hors machine vérifiée (restore-test) datant de < 7 jours | Obligatoire avant toute migration |

Ce que le serveur achète (à confirmer par les mesures de l'étape 31) : génération d'images ×20 à ×30 plus rapide, voix CUDA ×5 à ×10, b-roll généré de 5 s (Wan 2.2 5B ≈ 9 min par clip sur RTX 4090 : utilisable en appoint, pas en style principal), rendus en parallèle. Ce qu'il n'achète pas : de meilleurs sujets, de meilleurs hooks, une audience. Le Mac reste orchestrateur ; le serveur est un worker de rendu interchangeable, et le système doit continuer à tourner en mode dégradé si le serveur disparaît.

## 9. Risques et plans B

| # | Risque | Probabilité · impact | Parade intégrée à la roadmap | Plan B |
|---|---|---|---|---|
| 1 | **Photoréalisme attendu par Alek** : la génération vidéo IA locale est hors de portée (82 min pour 2 s sur un M1 Max 64 Go ; 15 min pour 4 s en 512×288 sur 16 Go) et le serveur à 50 €/mois n'atteindra pas Higgsfield. | Certaine · élevé (confiance client) | Étape 6 : matrice mesurée, preuves visuelles, message à Alek ; style « documentaire » sur banques libres (5/5) et « illustré » (4/5) comme réponse ; les chaînes qui gagnent au registre n'utilisent pas de photoréalisme. | Après le jalon serveur : b-roll généré de quelques secondes (Wan 2.2 5B) inséré dans des vidéos documentaires ; jamais un style entier. Si Alek exige davantage : chiffrer un abonnement vidéo payant (étape 31, Agent C) comme option post-jalon, à sa charge. |
| 2 | **Contenu inauthentique et terminaison de chaînes** (politique 07/2025, vague de janvier 2026 ; clause « chaînes associées »). | Moyenne · critique | Étape 1 (CONFORMITE) : signature humaine journalisée, ≥ 3 templates en rotation, anti-clonage inter-chaînes, cadence ≤ 2/semaine, comptes séparés propriété BMS, divulgation en 3 couches ; étape 23.2 : precheck bloquant et calendrier crédible ; étape 24 : déclinaison par adaptation. | Isolation des comptes limite la contagion ; à la première alerte YouTube sur une chaîne : pause de la chaîne, post-mortem sur les manifestes (quels facteurs), durcissement de precheck, aucune republication. Le mode « auto-approve » est désactivé. |
| 3 | **Disque (30 Go) et RAM (16 Go)** : modèles qui ne tiennent pas, swap, pipeline qui plante. | Élevée · moyen | Ledger `MODELES.md`, plancher 8 Go, purge par étape, un modèle résident à la fois, un run à la fois, modèles 4-9B en 4-bit, preuve vidéo IA conditionnelle, Revideo purgé jusqu'à l'étape 30.1. | Demander à Thomas de libérer 15-20 Go (question ouverte) ou un SSD externe (0 € s'il existe) pour `models/` et `workspace/` ; basculer sur les modèles de repli (Gemma 4 E4B, Kokoro) ; réduire les résolutions (1024×576) ; en dernier recours, avancer le jalon serveur pour le rendu seul, si les critères C1 à C7 hors C2 sont remplis. |
| 4 | **Audit API non obtenu ou lent** : toute vidéo uploadée reste privée ; jetons de test expirant. | Élevée · moyen | Étape 14 : consentement en production, politique de confidentialité, dossier d'audit honnête déposé dès la fin de la phase 1 ; étape 23.1 : liste « à publier manuellement » (≈ 2 min par vidéo dans Studio, conforme) ; digest quotidien. | Redéposer avec un dossier enrichi (vidéo de démonstration, usage strictement propriétaire) ; demander une extension de quota séparément ; ne jamais automatiser le navigateur. L'autonomie reste totale sur la production ; seul le clic de publication reste humain. |
| 5 | **Qualité des voix FR/IT/ES** : Kokoro n'a qu'une voix FR (B-) et deux IT (C) ; Chatterbox sur MPS incertain. | Moyenne · élevé (crédibilité des chaînes FR) | Étape 5.1 : mesure WER et écoute humaine, ≥ 2 voix par langue exigées, Chatterbox Multilingual et Qwen3-TTS en candidats ; étape 24 : `derive_from` limité aux langues couvertes. | Lancer d'abord les chaînes EN (Kokoro excellent) et ES si couvert, différer FR/IT jusqu'à une voix locale acceptable ; après le jalon serveur, chiffrer une voix premium (étape 31) sur le retour mesuré (rétention) ; clonage de la voix d'un membre de BMS avec droits consignés. |
| 6 | **Accès aux données concurrentes** : compartiments de quota (100 `search.list`/jour), transcriptions hors ToS, aucune source historique gratuite, pytrends mort. | Certaine · moyen | Étape 18 : entrepôt propriétaire alimenté par listes de chaînes et playlists (1 unité par appel), instantanés quotidiens ; étape 19 : Wikimedia Pageviews (fiable), autocomplete (parcimonie), candidature à l'API Trends ; transcriptions limitées aux étapes 3 et 16, IP résidentielle, compte de recherche séparé. | Analyse par titres, descriptions et miniatures seulement (sans transcriptions) ; élargir la liste de chaînes suivies à la main ; demander une extension de quota ; si l'entrepôt est le seul historique disponible, c'est précisément ce qui le rend précieux pour un acheteur. |

Deux risques secondaires, traités dans les prompts : la licence de Remotion (évitée : Revideo/Motion Canvas MIT) et la qualité de l'alignement mot à mot des sous-titres (WhisperX en repli, CPU).
