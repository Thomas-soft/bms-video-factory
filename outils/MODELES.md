# MODELES.md — ledger des poids téléchargés

**Cumul retenu : 21,52 Go (mesuré) — plancher disque : 8 Go libres** (cumul plafonné à **22 Go**, cf. `CLAUDE.md` § 3, relevé de 18 à 22 le 15/09/2026).
**Disque libre au 15/09/2026 : 46 Gi au début de 5.1, 26 Gi à la fin de 5.1, 23 Gi à la fin de 5.2.**

> ✅ **Le plafond est tenu — après avoir été relevé.** Mesure de fin d'étape
> 5.2 : **21,52 Go**, contre 21,89 annoncés en 5.1 (prévision juste à 0,37 près).
> **Thomas a porté le plafond de 18 à 22 Go le 15/09/2026**, au vu de cette
> mesure : il restait **0,48 Go de marge**. Rien n'a été purgé.
>
> ⚠️ **La marge est mince : 0,48 Go.** Tout nouveau poids devra être gagé sur un
> retrait — le premier candidat reste Qwen3-TTS (4,52 Go), dont le sort dépend
> de la question « TTS local ou serveur GPU ».
>
> ✅ **Le plancher de 8 Go, lui, n'a jamais été approché** : minimum touché
> pendant l'étape, 12 Gi, et 23 Gi à la fin. **C'est la seule règle dure.**

Règle : toute ligne est écrite **avant** le téléchargement (poids annoncé), puis son statut est mis à jour en fin d'étape. Un modèle « purgé » reste inscrit avec la date et la raison — c'est la trace des essais.

## Téléchargés

| Modèle | Chemin | Go | Étape | Statut (retenu / purgé / en test) | Licence |
|---|---|---|---|---|---|
| `mlx-community/parakeet-tdt-0.6b-v3` | `models/hf/hub/models--mlx-community--parakeet-tdt-0.6b-v3` | **2,3** (annoncé 0,60) | 5.1 | **retenu sous réserve** — RTF 0,037, mais tronque 2 fichiers sur 8 | CC-BY-4.0 — attribution NVIDIA due |
| `bartowski/Qwen_Qwen3.5-9B-GGUF:Q4_K_M` | `models/llamacpp` | **6,6** (annoncé 6,17) | 5.1 | **retenu** — 14,4 tok/s, pic 6,96 Go | Apache-2.0 |
| `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` | `models/hf/hub/models--Qwen--Qwen3-TTS-12Hz-1.7B-CustomVoice` | **4,2** (annoncé 2,00) | 5.1 | **retenu sous réserve d'écoute** — échoue la vitesse (RTF 3,29 > 1,0), conservé faute de repli à deux voix ; contrôlé par `factory doctor` depuis l'étape 7 | Apache-2.0 |
| `Qwen/Qwen3-TTS-Tokenizer-12Hz` | `models/hf/hub/models--Qwen--Qwen3-TTS-Tokenizer-12Hz` | **0,66** (non listé à l'étape 4) | 5.1 | **retenu sous réserve** — inséparable du modèle ci-dessus | Apache-2.0 |
| `mlx-community/whisper-large-v3-turbo` | `models/hf/hub/models--mlx-community--whisper-large-v3-turbo` | **1,5** (annoncé 1,62) | 5.1 | **retenu comme repli** — indispensable au rattrapage des troncatures de parakeet | MIT |
| `mlx-community/FLUX.2-Klein-4B-4bit` | `models/hf/hub/models--mlx-community--FLUX.2-Klein-4B-4bit` | **4,62** (annoncé 4,62) | 5.2 | **retenu** — 137 s par 1280×720, **sous le seuil réécrit à 180 s** par Thomas le 15/09/2026 (l'ancien, 90 s, venait d'un M1 Max 64 Go). Qualité 4,6/5, pic MLX 11,15 Go | Apache-2.0 |
| `depth-anything/Depth-Anything-V2-Small-hf` | `models/hf/hub/models--depth-anything--Depth-Anything-V2-Small-hf` | **0,10** (annoncé 0,10) | 5.2 | **retenu** — 0,24 s par carte sur MPS, pic 0,77 Go | Apache-2.0 |
| Playwright `chromium-headless-shell` | `models/playwright` | **0,21** (annoncé 0,35) | 5.2 | **retenu** — 0,20 s par miniature ; `--only-shell` évite les 0,93 Go des trois navigateurs ; **exercé en production depuis 13.2** (`factory thumbnail`, 6 rendus par run) et `PLAYWRIGHT_BROWSERS_PATH` **imposé par le code** — sans lui, 0,21 Go se retéléchargent dans `~/Library/Caches` | Chromium BSD-3 |
| Rhubarb Lip Sync 1.14 (binaire **x86_64**) | `outils/rhubarb` | **0,17** (annoncé 0,16) | 5.2 | **retenu** — 6,2 s pour 53 s de FR en `-r phonetic`. **Tourne sous Rosetta 2 : aucune recompilation arm64 nécessaire**, contrairement à ce qu'annonçait l'étape 4 | MIT |

**Cumul mesuré en fin d'étape 5.2 : 21,52 Go** (détail et arbitrage en bas de page).

### Purgé pendant les étapes 5.1 et 5.2

| Quoi | Go | Raison |
|---|---|---|
| Doublon `mlx-community/whisper-large-v3-turbo` dans `~/.cache/huggingface` | 1,5 | Une sonde positionnait `HF_HOME` **après** l'import de `mlx_whisper` : trop tard, `huggingface_hub` lit la variable à l'import. Le modèle s'est téléchargé deux fois. Doublon supprimé, l'exemplaire sous `models/hf` est conservé. |
| Élagage du cache `uv` (`uv cache prune`) | 0,7 | `CLAUDE.md` § 3 : caches sous `models/` ou nettoyés. |
| `city96/t5-v1_1-xxl-encoder-bf16` (encodeur de texte de la preuve vidéo) | 9,53 | Étape 5.2. Chargé une seule fois pour calculer deux embeddings, dans un processus séparé, puis supprimé **avant** que le transformer n'entre en mémoire. Licence non déclarée par le dépôt — raison de plus de ne pas le garder. |
| `city96/LTX-Video-gguf` Q6_K + VAE `Lightricks/LTX-Video` | 3,40 | Étape 5.2. Poids de la preuve vidéo IA, purgés dès le MP4 produit, comme prévu. |
| `Wan-AI/Wan2.1-T2V-1.3B-Diffusers` (téléchargement interrompu) | 1,10 | Étape 5.2. Route abandonnée avant terme : 28,94 Go au total, dont 22,72 pour le seul UMT5-XXL en float32. |
| Chromium de Puppeteer (Revideo) | 0,58 | Étape 5.2, purge prévue par la feuille de route. Réinstallé à l'étape 30.1 — recette dans `outils/revideo_projet/README.md`. |
| `node_modules` du projet Revideo de test | 0,29 | Idem. Les trois fichiers source sont conservés dans `outils/revideo_projet/` (20 Ko) : la configuration qui fonctionne a coûté cinq tentatives. |

**Non purgé, et volontairement :** `~/.cache/huggingface/hub/models--Systran--faster-whisper-large-v3` (2,9 Go), daté du **13/07/2026**, antérieur à ce projet. Il n'a pas été téléchargé par la session et ne lui appartient pas. À supprimer par Thomas s'il n'en a plus l'usage — 2,9 Go immédiatement disponibles pour 5.2.

## Prévus par l'étape 4 — à télécharger en 5.1 puis 5.2

Poids **annoncés**, à repeser (`du -sh`) à l'installation. Sélection justifiée dans `outils/SELECTION.md`, licences dans `outils/LICENCES.md`.

| Modèle | Go annoncés | Étape | Brique | Licence des poids |
|---|---|---|---|---|
| `nvidia/parakeet-tdt-0.6b-v3` | 0,60 | 5.1 | ASR | CC-BY-4.0 — **attribution NVIDIA due** |
| `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` | 2,00 | 5.1 | TTS | Apache-2.0 |
| `Qwen/Qwen3.5-9B` GGUF Q4_K_M | 6,17 | 5.1 | LLM | Apache-2.0 |
| `depth-anything/Depth-Anything-V2-Small` | 0,10 | 5.2 | Parallaxe | Apache-2.0 |
| `birefnet-general` (via rembg) | 0,90 | 5.2 | Détourage | MIT |
| `mlx-community/FLUX.2-Klein-4B-4bit` | **4,62 (pesé par l'API)** | 5.2 | Image | Apache-2.0 — ⚠️ **ne pas prendre la route bf16** : le dépôt officiel pèse 23,74 Go |
| Playwright `chromium-headless-shell` | **0,35 (mesuré)** | 5.2 | Miniatures | Chromium BSD-3 |
| Rhubarb Lip Sync (compilé arm64) | 0,16 | 5.2 | Avatar | MIT |

**Replis, à ne télécharger que si un principal tombe** : `google/gemma-4-E4B` Q4_K_M (4,98) · `Qwen/Qwen3.5-4B` (~2,7) · Chatterbox Multilingual v3 (1,00) · Kokoro-82M (0,33, ⚠️ dépendances GPL-3.0) · `mlx-whisper` large-v3-turbo (1,62) · SDXL 1.0 (6,94) + IP-Adapter (0,7-2,0) · DA3-BASE (0,50) · `u2net` (0,176) · **modèles acoustiques MFA** (0,092 par langue **mesuré**, ~0,40 pour FR/EN/ES/IT, CC-BY-4.0 — attribution due) · ACE-Step 1.5 (2,39, **conditionnel au disque**).

## Avertissement de l'étape 5.1 — les poids annoncés sont faux, systématiquement à la baisse

**Cinq poids vérifiés, cinq sous-évalués**, d'un facteur allant de 1,07 à 4,2.
La cause diffère à chaque fois, et c'est ce qui rend la règle utile :

| Modèle | Annoncé | Réel | Cause de l'écart |
|---|---|---|---|
| parakeet-tdt-0.6b-v3 | 0,60 Go | **2,3 Go** | confusion entre **0,6 milliard de paramètres** et 0,6 Go sur disque ; les poids sont en fp32 |
| Qwen3-TTS-12Hz-1.7B | 2,00 Go | **4,86 Go** | poids réels 4,2 Go, **plus un tokenizer audio de 0,66 Go** (`Qwen3-TTS-Tokenizer-12Hz`) que l'étape 4 n'avait pas vu : le modèle ne fonctionne pas sans lui |
| Qwen3.5-9B Q4_K_M | 6,17 Go | **6,6 Go** | taille du fichier GGUF (6,17 Go) contre occupation réelle du cache llama.cpp |
| ACE-Step 1.5 | 2,39 Go | **~10,1 Go** | nom de dépôt erroné (`Ace-Step1.5`, pas `ACE-Step-1.5`) et somme des quatre composants ignorée |
| FLUX.2-klein-4B (dépôt officiel) | 13-16 Go | **23,74 Go** | **doublon interne de 7,75 Go** — le transformer figure deux fois, en fichier unique à la racine et en disposition diffusers ; le reste vient du text_encoder (8,05 Go) jamais compté. **Pesé avant téléchargement, ce qui a évité l'erreur** |

**Règle ajoutée : un poids annoncé ne vaut rien tant qu'il n'a pas été pesé.** Le
nombre de paramètres n'est pas une taille de fichier — un modèle de 0,6 Md de
paramètres pèse 2,4 Go en fp32, 1,2 Go en fp16 et 0,35 Go en 4 bits. Toute ligne de
ce ledger doit porter une taille `du -sh`, jamais une taille de fiche de modèle.

**Seconde règle : peser le modèle *et ce qu'il charge*.** Qwen3-TTS ne fonctionne pas
sans `Qwen3-TTS-Tokenizer-12Hz`, un second dépôt de 0,66 Go qu'aucune fiche ne compte
dans le poids du modèle. C'est la même leçon que SadTalker à l'étape 4 (§ 5
ci-dessous), appliquée au disque et non à la licence : **ce que l'installeur tire
compte autant que ce que le dépôt annonce.**

**Conséquence sur le budget de l'étape 4.** Les 16,47 Go annoncés pour les douze
briques reposaient sur ces chiffres. Sur les quatre poids vérifiés en 5.1, quatre
étaient sous-évalués, d'un facteur allant de 1,07 à 4,2. **Le budget doit être
recalculé sur des pesées.** La règle a immédiatement servi : FLUX.2-klein-4B a été
pesé par l'API **avant** tout téléchargement, ce qui a révélé un dépôt officiel de
23,74 Go — et non 13-16 — et fait choisir la route 4-bit. **Cinquième poids vérifié,
cinquième écart.**

## Avertissements de l'étape 4

1. ~~**FLUX.2-klein-4B — pic transitoire de ~20 Go.**~~ **Caduc au 15/09/2026.** Deux erreurs dans cet avertissement : le dépôt officiel pèse **23,74 Go** et non 13-16 (dont un **doublon de 7,75 Go** : le transformer y figure deux fois, en fichier unique à la racine et en disposition diffusers), et la quantification locale est inutile puisqu'un dépôt MLX 4-bit Apache-2.0 existe. Route retenue : `mlx-community/FLUX.2-Klein-4B-4bit`, 4,62 Go, aucun pic. Voir § « Route disque de 5.2 ».
2. **Ne jamais utiliser un dépôt 4-bit tiers de FLUX.2-klein *sans vérifier sa licence*** — la formulation d'origine était trop large. Les dépôts tagués `flux-1-dev-non-commercial-license` dérivent de **FLUX.1-dev**, non commercial. `mlx-community/FLUX.2-Klein-4B-4bit` dérive du **FLUX.2-klein-4B officiel**, Apache-2.0, et porte lui-même `license: apache-2.0` dans `cardData`, dans ses `tags` et dans son README — les trois vérifiés le 15/09/2026. **La règle est de vérifier, pas d'exclure par principe.**
3. **rembg : toujours forcer `-m birefnet-general`.** Le modèle par défaut `bria-rmbg` exige un contrat payant en usage commercial et se télécharge tout seul au premier appel (vérifié dans `bg.py:324`).
4. **Tracer la double provenance de `birefnet-general`.** Le fichier `.onnx` est servi par les releases de rembg (`danielgatis/rembg/releases/download/v0.0.0/`), **sans licence jointe** ; la licence MIT est portée par l'amont `ZhengPeng7/BiRefNet`. Inscrire les deux URL.
5. **Vérifier ce qu'un installeur télécharge, pas seulement ce que le dépôt déclare.** C'est ce qui a fait tomber SadTalker à l'étape 4 : licence propre Apache-2.0, mais `download_models.sh` tirait GFPGAN (StyleGAN2 en licence Nvidia non commerciale, DFDNet en CC-BY-NC-SA). À refaire pour tout nouvel outil.
6. **Caches à rediriger sous `models/` dès le premier téléchargement** : `HF_HOME=./models/hf`, `OLLAMA_MODELS=./models/ollama`, `PLAYWRIGHT_BROWSERS_PATH=./models/playwright`, cache MLX.

## Conventions
- Chemin toujours sous `models/` (caches `HF_HOME=./models/hf`, `OLLAMA_MODELS=./models/ollama`, MLX redirigés).
- Licence : la licence **des poids**, pas celle du code d'inférence. Toute licence non commerciale (CC-BY-NC, CPML, licence maison restrictive) est éliminatoire et notée comme telle.
- `Go` = taille réelle sur disque après téléchargement (`du -sh`), pas la taille annoncée par l'auteur.
- Purge : `rm -rf` du chemin + `df -h /` reporté dans `STATE.md` § Environnement.

## Route disque de 5.2 — réglée, plus d'arbitrage

**Décision de Thomas, 15/09/2026 : rien à purger.** La route bf16 est abandonnée au
profit d'un dépôt MLX déjà quantifié.

**`mlx-community/FLUX.2-Klein-4B-4bit` — 4,62 Go, Apache-2.0, vérifié par l'API.**
Deux fichiers : `text_encoder/0.safetensors` (2,14 Go) et
`transformer/0.safetensors` (2,15 Go). `base_model` déclaré :
`black-forest-labs/FLUX.2-klein-4B`, lui-même Apache-2.0. **Aucune clause non
commerciale, aucun tag `flux-1-dev-non-commercial-license`** — l'avertissement n° 2
de l'étape 4 visait les dérivés de FLUX.1-dev et **ne s'applique pas à ce dépôt**
(vérification faite sur `cardData`, `tags` et le README, et non sur le seul nom).

**Le dépôt officiel pèse 23,74 Go, pas 13-16.** Et il contient un doublon : le même
transformer y figure deux fois, en `flux-2-klein-4b.safetensors` à la racine et en
`transformer/diffusion_pytorch_model.safetensors`, **7,75 Go chacun** — format
fichier unique contre disposition diffusers. Un `snapshot_download` naïf télécharge
les deux.

| Route | Téléchargé | Pic transitoire | Conservé |
|---|---|---|---|
| bf16 officiel puis quantification locale | **23,74 Go** | **~28 Go** — impossible sur cette machine | 4,0 |
| **MLX 4-bit (retenue)** | **4,62 Go** | **4,62 Go** | **4,62** |

**Conséquence pour la session 5.2 : elle ne doit pas prendre le chemin bf16.** Ce
n'est plus une optimisation, c'est la seule route praticable — 23,74 Go de
téléchargement suivis d'une quantification en mémoire ne tiennent pas dans 26 Gi
libres, et l'annonce « 13-16 Go » sur laquelle reposait le plan de l'étape 4 était
fausse de 8 à 11 Go.

**Non purgé, à la demande de Thomas :** `faster-whisper-large-v3` (2,9 Go) est
conservé. La question ne se pose plus, le pic transitoire ayant disparu.

## Le plafond de 18 Go — non tranché, il dépend du sort du TTS

**Thomas ne tranche pas maintenant** : la réponse dépend de ce que devient
Qwen3-TTS, qui attend lui-même une décision (voir `benchmarks/RESULTATS.md` § 1.2).

Coût de 5.2 par la route 4-bit : **6,63 Go** — FLUX 4,62 + rembg `birefnet-general`
0,90 + Revideo 0,50 + Playwright 0,35 + Rhubarb 0,16 + Depth Anything V2 Small 0,10.

| Scénario | Cumul projeté après 5.2 | Contre le plafond de 18 Go |
|---|---|---|
| **Qwen3-TTS conservé** | 15,26 + 6,63 = **21,89 Go** | **dépassé de 3,89 Go** |
| **Qwen3-TTS purgé** (−4,86) | **17,03 Go** | **tenu**, avec 0,97 Go de marge |

Les deux chiffres sont à lire avec la réserve de l'étape : **quatre poids annoncés
sur quatre étaient sous-évalués**. Les 6,63 Go de 5.2 n'en comptent qu'un seul de
pesé (FLUX, par l'API) ; les cinq autres sont des annonces. Dans le scénario « purgé »,
la marge de 0,97 Go ne survivrait pas à un seul écart du type de ceux déjà rencontrés.

Commande de purge du TTS, si la décision tombe de ce côté :
`rm -rf models/hf/hub/models--Qwen--Qwen3-TTS-12Hz-1.7B-CustomVoice models/hf/hub/models--Qwen--Qwen3-TTS-Tokenizer-12Hz`

---

## Cumul au 15/09/2026, fin de l'étape 5.2 — **plafond relevé à 22 Go, tenu**

Mesuré par `du -sk`, converti en Go décimaux.

| Poste | Go | Brique |
|---|---|---|
| Qwen3.5-9B Q4_K_M | 7,09 | LLM |
| Qwen3-TTS-12Hz-1.7B + tokenizer | 4,52 | TTS |
| FLUX.2-Klein-4B-4bit | 4,62 | Image |
| parakeet-tdt-0.6b-v3 | 2,51 | ASR |
| whisper-large-v3-turbo | 1,61 | ASR de repli |
| Playwright chromium-headless-shell | 0,21 | Miniatures |
| Rhubarb Lip Sync | 0,17 | Avatar |
| Depth-Anything-V2-Small | 0,10 | Parallaxe |
| **Cumul** | **21,52** | **plafond 22 → 0,48 Go de marge** |

**Le dépassement du plafond d'origine n'était pas une surprise : `STATE.md`
l'annonçait à 21,89 Go en fin d'étape 5.1.** La mesure l'a confirmé à 0,37 Go
près, et **Thomas a relevé le plafond de 18 à 22 Go plutôt que de purger** — le
plafond de 18 datait d'une machine annoncée à 30 Gi libres, et la contrainte qui
protège réellement la machine est le plancher de 8 Go, jamais approché.

Les deux leviers restent disponibles si la marge de 0,48 Go devient insuffisante :

- **Retirer Qwen3-TTS (4,52 Go) → cumul à 17,00 Go**, 5,00 Go de marge. C'est le
  levier décisif, et il appartient à Thomas : il a conservé Qwen3-TTS le 15/09
  **en connaissance du dépassement de seuil de vitesse**, faute de repli à deux
  voix.
- **Retirer whisper-large-v3-turbo (1,61 Go) → cumul à 19,91 Go.** Ce repli est
  ce qui rattrape les troncatures de parakeet : le retirer coûterait la
  couverture des sous-titres. À ne faire qu'en dernier recours.

**Aucun poids n'a été supprimé.** Le plafond est un objectif de `ROADMAP.md`
§ 3.2 ; le plancher de 8 Go libres est la contrainte dure, et il est tenu
(23 Gi libres).

Hors `models/` : `mflux` installé en outil isolé (`uv tool`, 1,10 Go de
dépendances Python, pas des poids) et `.venv` (1,5 Go).

---

## Étape 7 — mesure de contrôle (15/09/2026)

Aucun poids téléchargé, aucun poids purgé. Le cumul est **repesé**, pas recopié :

```
du -sk models/hf models/llamacpp models/playwright outils/rhubarb
```

| Emplacement | Go |
|---|---|
| `models/hf` (FLUX.2-klein, parakeet, whisper, Qwen3-TTS + tokenizer, Depth Anything) | 14,05 |
| `models/llamacpp` (Qwen3.5-9B Q4_K_M + son mmproj) | 7,09 |
| `models/playwright` | 0,21 |
| `outils/rhubarb` | 0,17 |
| **Cumul retenu** | **21,52** |

**21,52 Go — identique à la mesure de fin d'étape 5.2, au centième près.** Plafond
22 Go : 0,48 Go de marge. Plancher de 8 Go libres : **22 Gi libres**, tenu.

**Hors `models/`, et à ne pas compter dans le plafond** (ce sont des dépendances
Python, pas des poids) : `.venv` **2,00 Go** (1,50 avant l'étape 7 ; **+0,50 Go**
pour scenedetect/opencv, les clients Google et pytest — conforme aux 0,5 Go
annoncés par la feuille de route) et l'outil isolé `mflux` **1,10 Go**.

**Deux statuts corrigés par cette étape.** Les deux lignes Qwen3-TTS passent de
« échoue la vitesse » à **« retenu sous réserve »** : elles restent sur le disque,
elles portent la seule brique TTS du projet, et `factory doctor` les exerce à
chaque session. Le verdict de vitesse (RTF 3,29) et l'écoute en attente de Thomas
sont inchangés — c'est le statut de ledger qui était faux, pas la mesure.

**Ce que `factory doctor` contrôle désormais à chaque session** : la présence sur
disque de chaque ligne « retenu » de ce tableau (9 lignes), le plancher de 8 Go,
et le fait que `HF_HOME`, `OLLAMA_MODELS` et `LLAMA_CACHE` pointent bien sous
`models/`. Ajouter une ligne « retenu » ici suffit à la faire contrôler.

## Étape 12.2 — aucun poids ajouté, une bibliothèque qui commence à peser (16/09/2026)

**Aucun téléchargement.** Les deux modèles employés étaient déjà au ledger :
FLUX.2-Klein-4B-4bit (4,62 Go, étape 5.2) et Depth-Anything-V2-Small (0,10 Go,
étape 5.2). Le cumul retenu est donc **inchangé à 21,52 Go**.

**Un incident de cache, mesuré et corrigé.** `mflux` est installé en `uv tool` :
il tourne **hors du `.venv` et hors du `.env` du projet**. Lancé sans
`HF_HOME`, il a commencé à re-télécharger FLUX.2-klein dans
`~/.cache/huggingface` — **2 Gi de disque partis en 13 minutes** avant
interruption, et le doublon purgé. Depuis, `factory.assets.images.environnement()`
impose `HF_HOME` et `MFLUX_CACHE_DIR` à **chaque** sous-processus de modèle.
`~/.cache/huggingface` conserve 2,9 Go de `faster-whisper-large-v3`, antérieur à
ce projet et hors de son périmètre : il n'est pas compté au plafond et n'a pas
été touché.

### Ledger de la bibliothèque d'images

`workspace/library/images/` n'est **pas un poids de modèle** : il ne compte pas
au plafond de 22 Go, mais il croît à chaque vidéo et doit être suivi. Chaque
image y est un PNG 1280×720 accompagné de son `licence.json` et de son
`prompt.txt`. Les cartes de profondeur vivent à côté, dans
`workspace/library/depth/`, une par image.

| Date | Étape | PNG | Fichiers | Taille | Profondeur |
|---|---|---|---|---|---|
| 16/09/2026 | 12.2, run FR (127 plans) | 83 | 249 | 92,2 Mo | 83 cartes, 7,2 Mo |

Commande de relevé : `du -sh workspace/library/images workspace/library/depth`.

### Ledger de la bibliothèque de banque

`workspace/library/stock/` est la bibliothèque du moteur documentaire : un fichier
par asset téléchargé, accompagné de son `<id>.json` au contrat `Asset` complet
(`CONFORMITE.md` § 8). Comme la bibliothèque d'images, elle **ne compte pas au
plafond de 22 Go** — ce ne sont pas des poids de modèle — mais elle croît à chaque
vidéo et le code lui impose désormais un budget.

| Date | Étape | Fournisseur | Fichiers | Taille |
|---|---|---|---|---|
| 19/09/2026 | 17, run `pt83` (174 plans) | Internet Archive | 12 | 287 Mo |
| 19/09/2026 | 17, run `pt83` | NASA | 96 | 215 Mo |
| 19/09/2026 | 17, run `pt83` | Openverse | 44 | 11 Mo |
| 19/09/2026 | **total** | — | **153** | **513 Mo** |

Commande de relevé : `du -sh workspace/library/stock`.

**Douze fichiers d'Archive pèsent plus que quatre-vingt-seize de la NASA**, et
c'est la mesure qui a fixé les deux garde-fous du module. Un clip de banque coûte
des dizaines de mégaoctets quand une photographie en coûte moins d'un ; un plan,
lui, n'en consomme que sept secondes. D'où **`TAILLE_MAXIMALE_OCTETS = 60 Mo`**
(abaissé de 120 après avoir vu une vidéo NASA de 82 Mo servir un plan de 6 s) et
**`BUDGET_BIBLIOTHEQUE_OCTETS = 2 Go`**, au-delà duquel plus aucun téléchargement
n'est lancé : la chaîne descend au repli généré, qui ne coûte pas de disque en
plus. La feuille de route prévoyait 0,5 à 1 Go pour cette étape ; 513 Mo pour un
run de 174 plans place le second run à la limite basse de cette fourchette, le
cache jouant à partir du troisième.


**249 fichiers pour 83 images** : chaque image a son PNG, son `licence.json` et son
`prompt.txt`. Le prompt complet est gardé à part parce que le contrat `Asset`
n'en garde que le hachage — et sans lui, « même graine » ne veut rien dire à la
relecture.

**Ordre de grandeur pour la suite** : ~1,1 Mo par image, soit **~92 Mo par vidéo
de 10 minutes** au premier passage. La bibliothèque ne croît que des images
neuves : la deuxième exécution du même run en a ajouté **zéro**. À 2 vidéos par
semaine et par chaîne, compter ~1 Go par chaîne et par trimestre **avant**
réutilisation croisée, qui n'a pas encore été mesurée (première vraie mesure à
l'étape 24).

**Disque libre en fin d'étape 12.2 : 18 Gi**, mesuré par `df -h /`. Plancher de
8 Go tenu, avec 10 Gi de marge. `factory doctor` : **14 contrôles PASS en 77 s**.

## Preuve motion design (hors feuille de route) — 16/09/2026

Revideo 0.11.0 installé pour rendre trois séquences de 32 s
(`benchmarks/preuve_motion/`). **Aucun poids de modèle téléchargé.**

| Élément | Chemin | Go | Étape | Statut | Licence |
|---|---|---|---|---|---|
| Revideo 0.11.0 + dépendances npm | `benchmarks/preuve_motion/revideo/node_modules` | **0,30** | preuve motion (30.1) | **conservé, hors plafond** — dépendance JS, pas un poids ; même traitement que `.venv` | MIT |
| Chromium de Puppeteer (`chrome` + `chrome-headless-shell`) | `models/puppeteer` | **0,59** | preuve motion (30.1) | **PURGÉ le 16/09/2026** — faisait passer le cumul retenu à **22,11 Go**, au-dessus du plafond de 22 | BSD-3 (Chromium) |

**Pourquoi la purge ne coûte rien.** Revideo rend avec le Chromium **déjà installé
pour Playwright** à l'étape 5.2 (`models/playwright/chromium_headless_shell-1234/`,
0,21 Go), en imposant `PUPPETEER_EXECUTABLE_PATH`. Mesuré sur la séquence B :
**8,05 s contre 8,31 s** avec le Chromium de Puppeteer — équivalent. Un seul
navigateur suffit au projet.

⚠️ **À ne pas repayer à l'étape 30.1** : `npm install` sous npm 11 ne lance plus les
`postinstall` (il faut `npm approve-scripts` puis `npm rebuild`), et le postinstall
de puppeteer **retélécharge 0,59 Go** dès qu'on le laisse faire. La marche à suivre
est dans `benchmarks/preuve_motion/README.md`.

**Cumul retenu après purge : 21,52 Go** — inchangé depuis l'étape 7, plafond de
22 Go tenu (0,48 Go de marge). **Disque libre en fin de session : 15 Gi**
(16 Gi au lancement), plancher de 8 Go jamais approché.

---

## Étape 30.1 — moteur motion design (19/09/2026)

**Aucun poids de modèle téléchargé, aucun navigateur téléchargé.**

| Élément | Chemin | Go | Étape | Statut | Licence |
|---|---|---|---|---|---|
| Revideo 0.11.0 + dépendances npm (dont `@tabler/icons` en dev) | `render/node_modules` | **0,33** | 30.1 | **conservé, hors plafond** — dépendance JS, pas un poids ; même traitement que `.venv` | MIT |
| Chromium | — | **0,00** | 30.1 | **aucun** — le rendu emploie le **Google Chrome déjà installé sur la machine** (152.0.7977.83, 1,4 Go, hors dépôt), par `settings.puppeteer.executablePath` | BSD-3 (Chromium) |
| Icônes Tabler extraites | `render/src/icons.ts` | 0,00 (8 Ko) | 30.1 | conservé, dans le dépôt | MIT |
| Polices servies à Vite | `render/src/fonts/` | 0,00 | 30.1 · 30.2 | conservé — **quatre liens** vers `assets/fonts/`, pas des copies : une seule source pour les polices OFL du dépôt. **Caveat ajoutée à l'étape 30.2** (manuscrite du style whiteboard, 0,40 Mo dans le dépôt, hors plafond de modèles) | OFL-1.1 |
| Sorties de lot Revideo | `render/out/<video_id>/` | 0,10 | 30.1 | **hors git**, effaçable — les clips de plan vivent dans le run | — |

**L'avertissement de la preuve du 16/09 a été suivi, et amélioré.** `PUPPETEER_SKIP_DOWNLOAD=true`
à l'installation évite les 0,59 Go du Chromium de puppeteer ; `render.mjs` pointe ensuite sur le
Chrome du système plutôt que sur le `chromium-headless-shell` de Playwright, ce qui retire aussi
la dépendance croisée entre deux briques. `BMS_CHROME` permet d'en imposer un autre. Les
`postinstall` restent non exécutés sous npm 11 : les deux binaires qui en avaient besoin
(`@ffmpeg-installer`, `@ffprobe-installer`) arrivent déjà exécutables, vérifié.

**Nettoyage automatique.** Revideo laisse trois intermédiaires par lot (`-0.mp4`, `-audio.wav`,
`-visuals.mp4`), ≈ 40 Mo chacun. `render.mjs` les efface dès que le lot est rendu.

**Cumul des modèles retenus : 21,52 Go, inchangé** — le moteur n'ajoute aucun poids. **Disque
libre en fin d'étape : 8,0 Gi**, mesuré par `df -h /`. Le plancher de 8 Go est **atteint, pas
franchi** ; la cause est le swap système, **9,2 Go répartis sur 9 `swapfile`**, mesuré par
`sysctl vm.swapusage` (7,80 Go utilisés). Le run de l'étape 30.1 pèse **0,55 Go**.

## Étape 20 — un poids neuf, et il consomme la marge du plafond (20/09/2026)

**Ligne écrite AVANT le téléchargement, poids annoncé** (règle de la page) :

| Modèle | Chemin | Go | Étape | Statut | Licence |
|---|---|---|---|---|---|
| `intfloat/multilingual-e5-small` | `models/hf/hub/models--intfloat--multilingual-e5-small` | **0,47 mesuré** (annoncé 0,47 — 470 Mo par `du -sh`) | 20 | **retenu** — 111 textes/s sur CPU M2, 5 604 titres en 50,4 s, 384 dimensions | **MIT** |

**Pourquoi celui-là.** Veille du 20/09/2026, sept candidats pesés par l'API Hugging Face.
118 M paramètres, 384 dimensions, 512 jetons de contexte (un titre plus 200 caractères de
description n'est jamais tronqué), 101 langues dont fr/en/es/it, et le meilleur rapport
qualité/poids attesté en regroupement multilingue. **MIT**, donc commercial sans réserve.
Contrainte d'emploi : **tous** les textes sont préfixés par `query: ` — c'est une exigence de
l'entraînement du modèle, pas une option de style ; sans le préfixe la qualité tombe.

**Écartés, et pourquoi.** `jinaai/jina-embeddings-v3` — **CC-BY-NC-4.0, éliminatoire**.
`google/embeddinggemma-300m` — licence « gemma », gated, même motif que Gemma 3 à l'étape 4.
`Alibaba-NLP/gte-multilingual-base` (611 Mo) et tout ce qui dépasse 600 Mo — hors limite de
poids : `multilingual-e5-base`, `paraphrase-multilingual-mpnet-base-v2` (1 112 Mo),
`snowflake-arctic-embed-m-v2.0` (1 221 Mo), `BAAI/bge-m3` (2 271 Mo).
**Replis retenus sur étagère** : `ibm-granite/granite-embedding-97m-multilingual-r2`
(195 Mo, Apache-2.0, aucun préfixe) puis `paraphrase-multilingual-MiniLM-L12-v2` (471 Mo,
Apache-2.0).

**Cumul repesé en fin d'étape : 21,59 Go, et le prévu était 21,99.** Méthode, pour qu'elle
soit refaisable : `du -sk` sur `models/hf`, `models/llamacpp`, `models/playwright`,
`outils/rhubarb` et `~/.local/share/uv/tools/mflux`, divisé par 1 048 576 (donc des Gio).
Détail : hf **13,54** · llamacpp **6,60** · playwright **0,19** · rhubarb **0,16** · mflux
**1,09**.

⚠️ **L'écart de 0,40 Go avec la prévision n'est pas expliqué, et il n'a pas été cherché.**
Hypothèse non vérifiée : `models/mflux` (cache déclaré par `factory/assets/images.py`)
**n'existe plus sur le disque** et pouvait peser cet ordre de grandeur en fin d'étape 5.2.
Le chiffre écrit ici est celui qui a été **mesuré aujourd'hui**, pas celui qui a été calculé.

**Le plafond de 22 Go tient, avec 0,41 Go de marge** — et non 0,01 comme annoncé avant le
téléchargement. Tout poids suivant reste à gager sur un retrait ; le premier candidat est
toujours Qwen3-TTS (4,86 Go avec son tokenizer), dont le sort dépend de l'arbitrage « TTS
local ou serveur GPU ». **Le plancher de 8 Go libres n'a pas été approché : 13 Gio à la fin**
de l'étape, 12 Gio au plus bas pendant les exécutions (swap système, cf. `STATE.md`).

**Poste neuf, hors plafond de modèles :** la table `embeddings` de `workspace/factory.db`
porte **10 304 vecteurs** (5 604 titre+description, 4 700 titre seul), et la base passe de
12,9 à **34 Mo**. C'est un cache de calcul, reconstructible en 50 s ; il se purge sans perte.

**Aucune dépendance Python neuve.** Le modèle tourne sur `transformers` + `torch`, déjà
installés et épinglés par `uv.lock` ; le regroupement sur `scikit-learn` 1.9.1, déjà présent.
`sentence-transformers`, `hdbscan` et `umap-learn` ne sont **pas** installés : la moyenne
masquée tient en dix lignes (`factory/editorial/embed.py`) et l'agglomératif de scikit-learn
suffit, conclusion explicite du rapport de veille.

## Étape 29 — 24/09/2026 : détourage des personnages

| Modèle | Chemin | Go | Étape | Statut | Licence |
|---|---|---|---|---|---|
| rembg `birefnet-general-lite` (ONNX) | `models/rembg/models/birefnet-general-lite` | **0,22 mesuré** | 29 | **retenu** — détourage de `base.png` des personnages (cache `U2NET_HOME`), sous-processus qui se termine (`python -m factory.characters detourer`) | MIT (code BiRefNet et rembg) |

Paquet Python `rembg[cpu]` 2.0.85 ajouté au `.venv` (+ onnxruntime, scikit-image, pymatting) :
`.venv` 2 135 → 2 164 Mo. Repères du visage : **Apple Vision** (framework système, 0 Go),
`outils/vision/reperes_visage` compilé depuis `reperes_visage.swift`.

**Cumul repesé en fin d'étape 29 : 21,81 Go** (même méthode : `du -sk` sur `models/hf`,
`models/llamacpp`, `models/playwright`, `models/rembg`, `outils/rhubarb`,
`~/.local/share/uv/tools/mflux`, ÷ 1 048 576). Détail : hf 13,54 · llamacpp 6,60 ·
playwright 0,19 · rembg 0,22 · rhubarb 0,16 · mflux 1,09. **Marge au plafond de 22 Go : 0,19.**
Le prochain poids retenu imposera une purge (candidats : § « Cumul au 15/09/2026 »).
