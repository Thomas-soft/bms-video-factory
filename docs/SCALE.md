# SCALE.md — passage à l'échelle : quand payer, quoi, combien

Écrit à l'étape 31 (24/09/2026). Instancie la section 8 de `ROADMAP.md` (jalon de bascule vers
le serveur) avec les mesures réelles du dépôt.

**Règle d'Alek** : le budget de ~50 €/mois se débloque sur des critères de **volume**, jamais de
faisabilité. **Réponse courte au 24/09/2026 : aucun critère de volume n'est atteint** (0 vidéo
publiée, 0 € de revenu, audit non déposé). Le goulot est la publication et la relecture, pas le
calcul. Ce document dit ce qui fera basculer, et quoi acheter ce jour-là.

Conventions : **mesuré** = manifeste, base ou `benchmarks/RESULTATS.md` sur ce Mac ;
**estimé** = arithmétique sur des mesures ; **publié** = chiffre d'un tiers, avec URL. Tous les
prix ont été **consultés le 24/09/2026**, sauf mention ; taux **1 € = 1,1379 $** (24/09/2026,
https://tradingeconomics.com/euro-area/currency). Aucun chiffre de ce document n'est une
promesse d'audience.

---

## 1. Capacité mesurée du Mac

Machine : MacBook Air M2, 16 Go, un seul run à la fois. Fenêtre des étapes lourdes : 22:00–07:00
(**540 min**, `config/orchestrator.yaml`).

| Style | Run de référence | Temps machine pour ~10 min de vidéo | Nature | Vidéos neuves par nuit |
|---|---|---|---|---|
| Illustré (images générées) | `s2ur`, 10,5 min | **252,0 min** (73 % génération d'images, 101 images) | mesuré, run neuf complet | **2** |
| Illustré, dérivé (images réemployées) | `c7km`, 11,6 min | 74,6 min | mesuré | 7 |
| Motion design (zéro image) | `mtn7`, 10,6 min | 50,5 min **hors script et voix** (repris d'`avwf`) ; ≈ 99 min avec voix 37 min + script 11 min | mesuré + estimé | ≈ 5 (estimé) |
| Whiteboard | lot de 30 plans, `wb-lot-30-2` | 727,9 s par minute de vidéo → ≈ 121 min + voix + script ≈ 178 min | mesuré sur lot + estimé | ≈ 3 (estimé) |
| Documentaire (banques libres) | aucun run complet (`pt83` échoué) | **non mesuré** | — | non mesuré |
| Avatar 2D (surcouche) | `fgr6` | **+37,8 s** par vidéo sur le style hôte | mesuré | = style hôte |

**Capacité retenue : 1 vidéo neuve illustrée par nuit, soit 7 par semaine, ≈ 30 par mois.**
Pourquoi 1 et pas 2 : la purge post-export ne s'exécute pas quand `export` sort en code 4 (dette
n° 5 de `REPRISE.md`), et deux runs complets ne tiennent pas au-dessus du plancher de 8 Go
(mesuré le 20/09 : 13 → 10 Gi après un seul run). Corriger cette dette porte la capacité à
**14 par semaine** en illustré, sans rien acheter.

**Ce qui borne vraiment la production aujourd'hui** (dans l'ordre) :
1. **Conformité** : 2 vidéos par chaîne et par semaine pendant 90 jours (`CONFORMITE.md` § 6).
   Avec 2 chaînes actives → **4 par semaine**, soit 57 % de la capacité mesurée.
2. **Publication** : audit non déposé → clic Studio par vidéo (≈ 2 min) ; comptes non reliés.
3. **Relecture** : 15 min par vidéo (estimé), **99,7 % du coût** (`reports/economics.md` § 7).
4. **Calcul** : seulement ensuite.

## 2. Critères de bascule instanciés (ROADMAP § 8)

| # | Critère | Seuil | Valeur au 24/09/2026 | Source | État |
|---|---|---|---|---|---|
| C1 | Avancement | ≥ 28/31 étapes, phases 0-5 closes | 29 étapes closes + 30.1 ✅ ; 30.2 à 3/4 (run whiteboard complet manquant) ; 24 différée | `SUIVI.md` | ✅ atteint (réserve 30.2) |
| C2 | Demande > capacité | file approuvée ≥ 2 × capacité hebdo, 3 semaines de suite | file = **6** jobs en file + **0** sujet approuvé (63 proposés) ; capacité = **7**/sem → seuil **14** ; ratio **0,43** ; 0 semaine | `jobs`, `topics_queue` | ❌ — **inatteignable à 2 chaînes** (plafond conformité 4/sem < 7) : il faut ≥ 4 chaînes publiant 2/sem |
| C3 | Qualité stable | ≥ 80 % de PASS au premier passage sur les 20 derniers | **3 PASS / 8 runs notés = 37,5 %** (n = 8 < 20 ; « premier passage » non distingué au manifeste) | `runs.qc_verdict` | ❌ |
| C4 | Signal de marché | ≥ 1 chaîne à 500 abonnés, ou 10 000 vues/30 j, ou revenu d'affiliation > 0 | **0 publication, 0 vue, 0 €** | `publications`, `perf_daily`, `revenue` (0 ligne) | ❌ |
| C5 | Économie | revenu/vidéo × vidéos en plus/mois ≥ 100 € | revenu/vidéo **0,000 €** → **0 €** | `reports/economics.md` | ❌ (sauf décision explicite d'Alek d'investir avant revenu) |
| C6 | Publication débloquée | `audit_passed: true` sur ≥ 1 chaîne | **false sur 6/6** ; audit non déposé ; `secrets/client_secret.json` absent | `config/channels/*.yaml` | ❌ |
| C7 | Actif sauvegardé | sauvegarde hors machine + restore-test < 7 jours | archive locale du 24/09 06:34 ✅ ; **copie hors machine non vérifiée** ; aucun restore-test journalisé dans `events.jsonl` | `~/BMS-backups` | ❌ |

**Bilan : 1 critère sur 7.** L'ordre dans lequel ils peuvent tomber : C6 et C7 (gestes humains,
une journée), puis C4 et C3 (4 à 8 semaines de publication), puis C2 (ouverture de chaînes
supplémentaires), puis C5 (revenu à 30 jours sur ≥ 5 vidéos avec produit).

**Déclencheur opérationnel proposé** (à valider par Alek) : C6 + C7 vrais **et** C2 vrai
3 semaines de suite. C4/C5 ne sont pas une condition de faisabilité mais de rentabilité : si Alek
veut investir avant revenu, C5 tombe par décision écrite (ROADMAP § 8).

## 3. Options de serveur (prix consultés le 24/09/2026)

**Constat : aucun serveur GPU dédié ne tient dans 50 €/mois.** Le moins cher trouvé est
4 fois au-dessus. La seule forme compatible est la **location à l'heure**.

| Option | GPU | Prix | Heures pour 50 € | Stockage | Source |
|---|---|---|---|---|---|
| **A. RunPod Community** | RTX 4090 24 Go | 0,34 $/h (0,30 €/h) | **167 h** | volume réseau 0,07 $/Go/mois ; disque de pod 0,20 $/Go/mois **à l'arrêt** | https://www.runpod.io/pricing ; https://getdeploying.com/gpus/nvidia-rtx-4090 |
| **A'. RunPod Secure** | RTX 4090 | 0,74 $/h (0,65 €/h) | 77 h | idem | https://www.runpod.io/pricing |
| **B. TensorDock** | RTX 4090 | 0,37 $/h (spot 0,20 $/h, source secondaire) | 154 h (284 en spot) | payant à l'arrêt, prix non trouvé | https://www.tensordock.com/gpu-4090.html |
| B'. Vast.ai | RTX 4090 | 0,39 $/h | 146 h | non trouvé | https://getdeploying.com/gpus/nvidia-rtx-4090 — **aucune offre 4090 ni 3090 en ligne ce jour** |
| C. Scaleway (UE) | L4 24 Go | 0,79 €/h | 63 h | non trouvé | https://www.scaleway.com/en/pricing/gpu/ |
| Hetzner GEX45 (mensuel) | RTX PRO 4000 Blackwell 24 Go | 214 €/mois + 209 € de mise en service | — | inclus | https://dohohub.com/news/hetzner-gex45-entry-level-gpu-server — **hors budget** |
| Scaleway L4-1-24G (mensuel) | L4 | ≈ 574,87 €/mois | — | — | https://www.scaleway.com/en/pricing/gpu/ — **hors budget** |

**Alternative sans GPU — l'image par API** (veille du 17/09/2026, `docs/VEILLE-50-EUROS.md` § 5) :
FLUX.1-schnell (Apache-2.0) chez DeepInfra à **0,00044 €/image**, Z-Image-Turbo chez fal.ai à
0,00456 €/image. Même effet sur le poste qui pèse 73 % du temps, sans serveur à administrer.
À départager par un essai de qualité (FLUX.2 klein 4B local contre FLUX.1-schnell / Z-Image
distants) : **non fait**.

**Recommandation** : option A (RunPod Community, 4090) en worker à l'heure, avec A' en repli de
disponibilité ; l'API à l'image comme option B si l'essai de qualité est concluant. Prix à
relever de nouveau le jour de la décision.

## 4. Gain de débit par brique

| Brique | Mesuré sur le Mac | Publié sur RTX 4090 | Gain | Source du publié |
|---|---|---|---|---|
| Image (73 % du temps) | FLUX.2 klein 4B 4-bit : **109 s/image** en production (`s2ur`, 11 016 s / 101), 137 s au banc (1280×720, 4 pas) | FLUX.1-schnell 1024², 4 pas : **2,9 à 5,5 s** ; FLUX.2 klein 4B : **non publié** | **≈ ×20 à ×40 (estimé)** | https://blog.salad.com/flux1-schnell/ |
| Voix (15 %) | Qwen3-TTS : **RTF 3,29** (37 min pour 10,5 min d'audio) | Chatterbox : **0,499 × la durée** (≈ 5 min) ; Qwen3-TTS CUDA : non publié | **≈ ×6,6 (estimé, autre modèle)** | https://github.com/davidbrowne17/chatterbox-streaming |
| Script LLM (4,5 %) | Qwen3.5-9B Q4 : 14,4 tok/s, 11 min | non relevé | non estimé — poste trop petit pour compter | — |
| Rendu Chromium / ffmpeg (4 %) | Revideo **0,335 × le temps réel** (146,5 img/s) | le rendu est **limité par le processeur** ; GPU utile seulement pour WebGL | **≈ ×1 — reste sur le Mac** | https://www.remotion.dev/docs/gpu |
| B-roll Wan 2.2 TI2V 5B, 5 s 720p | **non viable** (vidéo IA : 108,5 s par seconde de vidéo en 512×288) | **< 9 min par clip** | appoint seulement, jamais un style | https://github.com/Wan-Video/Wan2.2 |

**Vidéo neuve illustrée, images + voix sur le GPU, reste sur le Mac** : images 101 × ~4 s ≈ 7 min
+ voix ≈ 5 min + script 11 + rendu et reste ≈ 20 min → **≈ 45 min au lieu de 252 (estimé)**,
soit **≈ 12 vidéos par nuit au lieu de 2**. Le GPU ne consomme que ≈ 0,3 h par vidéo avec
chargement des modèles (estimé) : **50 €/mois achètent 5 à 10 fois plus d'heures que 60
vidéos/mois n'en demandent.**

**Ce que le GPU achète en qualité** (`RESULTATS.md` § 2.9) : le 4B en bf16 au lieu de 4 bits,
plus d'étapes de débruitage, et **4 images générées pour 1 retenue** (×4 sur le poste image,
≈ 0,6 h de GPU par vidéo, estimé). **Ce qu'il n'achète pas** : de meilleurs sujets, de meilleurs
hooks, une voix native hors anglais, une audience.

## 5. Plan de migration — Mac orchestrateur, worker GPU qui tire les jobs

Principe (ROADMAP § 8, recommandation de l'agent B) : **le Mac reste le chef d'orchestre**
(daemon, base SQLite, relecture, rendu Revideo, publication, jetons YouTube) ; le serveur est un
**worker interchangeable** qui exécute `assets.image` et `voice`. Si le worker disparaît, le Mac
reprend en mode dégradé. Aucune bascule complète : elle migrerait daemon, base et Remotion pour
un gain nul sur le rendu.

| Phase | Contenu | Durée estimée | Critère de sortie | Retour arrière |
|---|---|---|---|---|
| 0. Préalables | C6 et C7 vrais ; dette n° 5 (purge) corrigée ; essai de qualité API image vs local | 1-2 jours | restore-test < 7 j, audit obtenu | — |
| 1. Image Docker | base `pytorch/pytorch:2.14.0-cuda12.6-cudnn9-runtime` (3,69 Go) + diffusers FLUX (klein 4B bf16, Apache-2.0) + TTS CUDA ; `.dockerignore` couvrant `secrets/` et `.env` ; vérification `docker history` | 1 session | l'image génère 10 images et 1 min de voix, identiques en contrat (`ffprobe`, dimensions) | rien à défaire |
| 2. Worker à la demande | champ `worker_url` dans `config/orchestrator.yaml` (vide = local) ; le nœud `assets.image` envoie le lot d'intentions, récupère les PNG par rsync SSH ; bail d'expiration : un job « réclamé » non rendu repasse en file | 1-2 sessions | un run complet `bms-test` avec images distantes, QC comparable au run local | `worker_url` vide + redémarrage du daemon |
| 3. Nuit pilote | 1 semaine, 1 chaîne, pod démarré au début de la fenêtre et **détruit** à la fin | 1 semaine | vidéos/nuit mesurées, heures GPU et € relevés | idem |
| 4. Production | toutes les chaînes ; voix sur le worker si le TTS CUDA est validé à l'écoute (Thomas) | — | coût mensuel ≤ 50 € mesuré | idem |

**Synchronisation** : rsync sur SSH, dans le sens Mac → worker (intentions, config de style) et
worker → Mac (PNG, WAV). Pas de stockage tiers nécessaire ; si un échange asynchrone est utile :
Cloudflare R2 (10 Go-mois gratuits, sortie gratuite, https://developers.cloudflare.com/r2/pricing/).
Volume réseau RunPod pour les poids (≈ 15 Go × 0,07 $ ≈ 0,92 €/mois).

**Secrets** : le worker ne reçoit **aucun** jeton YouTube, aucun `.env` — seulement une clé SSH
dédiée et, au besoin, un jeton R2 limité à un seau. La publication reste sur le Mac.

**Retour au Mac seul en moins d'une heure** :
1. vider `worker_url` dans `config/orchestrator.yaml`, `uv run factory config validate`, redémarrer le daemon ;
2. remettre en file les jobs réclamés par le worker (`uv run factory queue retry <job>`) ;
3. rapatrier par rsync les runs partiels du worker vers `workspace/runs/` ;
4. détruire le pod et le volume, révoquer la clé SSH et le jeton R2 ;
5. lancer un run témoin sur le Mac et le vérifier (`ffprobe`, `factory qc`).

## 6. Briques payantes et retour attendu

Aucune n'est justifiée avant C4 : sans publication, aucun gain ne peut être mesuré.
Hypothèses : vidéo de ~8 min = **7 000 caractères** de narration, **30 vidéos/mois**. « Non
documenté » = aucune étude publique trouvée ; seuls des témoignages commerciaux existent.

| Brique | Coût par vidéo à 30/mois | Gain attendu | n pour le mesurer | Déclencheur | Source (24/09/2026) |
|---|---|---|---|---|---|
| Voix premium ElevenLabs Creator (22 $/mois, 220 000 car.) | **0,64 €** (19,33 €/mois) | non documenté ; la voix locale anglaise est jugée acceptable | ≈ 250 vidéos par bras pour +2 points de rétention | écoute à l'aveugle où Thomas rejette la voix locale, **ou** ouverture d'une langue sans voix native | https://elevenlabs.io/pricing/api |
| Voix OpenAI tts-1 (15 $/M car.) | **0,09 €** | idem ; aussi un gain de **temps** (37 min de voix locale en moins) | idem | voix = goulot après le GPU image | https://costgoat.com/pricing/openai-tts |
| B-roll Veo 3.1 Lite 720p (0,05 $/s, clips de 8 s) | **2,64 €** pour 60 s (79 €/mois) — le coût réel avec reprises peut être 3 à 5 fois plus élevé | non documenté | ≈ 250 vidéos par bras (+2 pts) | courbe de rétention qui décroche sur les plans fixes, mesurée sur ≥ 20 vidéos | https://ai.google.dev/gemini-api/docs/pricing |
| B-roll Kling 3.0 720p | ≈ 4,79 € pour 60 s | non documenté | idem | idem | https://www.cloudzero.com/blog/kling-ai-pricing/ |
| B-roll Runway Gen-4.5 | 6,33 € pour 60 s | non documenté | idem | idem | https://docs.dev.runwayml.com/guides/pricing/ |
| Higgsfield Plus | ≈ 16,70 € pour 60 s | non documenté | idem | aucun : hors d'échelle pour nos durées | https://www.blotato.com/blog/higgsfield-pricing |
| vidIQ Boost (39 $/mois) | 1,14 € | volumes de recherche estimés (méthode non publiée) | non mesurable par vidéo | besoin de volumes de mots-clés que Wikimedia Pageviews ne donne pas | https://1of10.com/blog/vidiq-pricing/ |
| YouTube « Test & Compare » (miniatures, titres) | **0 €** | mesure dans la vidéo elle-même (part du temps de visionnage) | par impressions, pas par vidéos | **tout de suite** après les premières publications | https://support.google.com/youtube/answer/13861714 |

**Ordre de grandeur statistique** (test bilatéral, α = 0,05, puissance 80 %, écart-type de la
rétention moyenne ≈ 8 points, estimé) : n = 2 × (1,96 + 0,84)² × 8² / Δ² par bras → **Δ = 1 point :
≈ 1 000 vidéos par bras** (≈ 67 mois à 30 vidéos/mois) ; Δ = 2 : ≈ 250 ; Δ = 3 : ≈ 112. **Aucune
brique payante ne peut prouver un gain de rétention à notre volume** ; seules des comparaisons
intra-vidéo (Test & Compare) mesurent vite.

## 7. Modèle de coût mensuel

Coûts par vidéo : énergie ≈ 0,03 € (mesuré sur `s2ur` × 30 W **estimé**) ; relecture **3,75 €**
(15 min × 15 €/h, **estimé**, taux à fixer par Alek). GPU à l'heure : 0,3 h/vidéo (estimé) à
0,30 €/h (option A) + volume 0,92 €/mois. Chaînes nécessaires à 2 vidéos/semaine : 10/mois → 2 ;
30/mois → 4 ; 60/mois → 7.

| Scénario | 10 vidéos/mois | 30 vidéos/mois | 60 vidéos/mois |
|---|---|---|---|
| **Mac seul** — faisable ? | oui (1 nuit sur 3) | **à la limite** : 1/nuit tous les soirs ; oui si la dette n° 5 est corrigée | **non** en illustré (2/nuit sans marge ni disque) ; oui en motion design (≈ 5/nuit, estimé) |
| Mac seul — machine | 0,30 € | 0,90 € | 1,80 € |
| **Mac + GPU à l'heure** (option A) — machine | 0,30 + 0,90 + 0,92 = **2,12 €** | 0,90 + 2,70 + 0,92 = **4,52 €** | 1,80 + 5,40 + 0,92 = **8,12 €** |
| … avec « 4 images pour 1 » (0,6 h/vidéo) | 3,92 € | 9,92 € | 19,52 € |
| **+ briques payantes** (voix ElevenLabs + b-roll Veo Lite 60 s) | + 19,33 + 26,40 = **+45,73 €** | + 19,33 + 79,20 = **+98,53 €** (dépasse 50 €) | + 87,00 (Pro, 99 $) + 158,40 = **+245,40 €** |
| Relecture humaine (estimé) | 37,50 € | 112,50 € | 225,00 € |

**Lecture.** (1) Le serveur loué à l'heure coûte **2 à 20 €/mois** pour 10 à 60 vidéos : le
budget de 50 € est largement suffisant pour le calcul ; il ne l'est pas pour le b-roll payant à
30 vidéos/mois. (2) **Le coût qui grandit avec le volume est la relecture humaine**, pas la
machine : à 60 vidéos/mois, 15 h de relecture par mois (estimé). (3) Le seuil C5 (100 € de
revenu en plus par mois) correspond à **≈ 3,40 € de revenu par vidéo** sur 30 vidéos
supplémentaires — à comparer au premier revenu réel, aujourd'hui 0.

## 8. Ce qui reste à 0 €, quoi qu'il arrive

- Script (LLM local), sous-titres (ASR local), rendu Revideo/ffmpeg, miniatures (Playwright
  local), banc qualité, orchestration, tableau de bord, sauvegarde locale.
- Collecte éditoriale (API YouTube Data v3 gratuite, Wikimedia Pageviews), analytique (YouTube
  Analytics + Reporting API gratuites), A/B de miniatures (Test & Compare).
- Musique : YouTube Audio Library (Studio) et banques CC0/CC-BY.
- Audit de l'API : gratuit (formulaire Google).
- La relecture reste humaine et nominative : elle ne s'achète pas (`CONFORMITE.md` § 4).
