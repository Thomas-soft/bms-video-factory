# LICENCES.md — licence de chaque outil et de chaque poids

Étape 4, vérifié le **15/09/2026** sur sources primaires (fiche Hugging Face, fichier LICENSE du dépôt, CGU officielles). Complète `outils/SELECTION.md` et `outils/MODELES.md`.

**Règle.** La licence des **poids** est distincte de celle du **code** : les deux sont listées séparément quand elles diffèrent. Toute licence non commerciale est éliminatoire (`CLAUDE.md` § 11) et figure en section « Éliminés pour licence », jamais dans le tableau des outils retenus.

**Territoire.** « mondial » signifie qu'aucune clause d'exclusion géographique n'a été trouvée dans le texte de la licence. C'est le point qui a fait tomber Llama 4, dont la licence exclut l'Union européenne.

---

## 1. Outils et modèles retenus (principal ou repli)

| Outil | Composant | Licence exacte | Commercial | Obligations | Territoire | URL | Vérifié le |
|---|---|---|---|---|---|---|---|
| **Qwen3.5-9B** | poids | Apache-2.0 | ✅ oui | notice Apache conservée | mondial | https://huggingface.co/Qwen/Qwen3.5-9B | 15/09/2026 |
| **Gemma 4 E4B** | poids | Apache-2.0 | ✅ oui | notice | mondial | https://huggingface.co/google/gemma-4-E4B | 15/09/2026 |
| **Qwen3.5-4B** | poids | Apache-2.0 | ✅ oui | notice | mondial | https://huggingface.co/Qwen/Qwen3.5-4B | 15/09/2026 |
| **llama.cpp** | code | MIT | ✅ oui | notice | mondial | https://github.com/ggml-org/llama.cpp | 15/09/2026 |
| **mlx-lm** | code | MIT | ✅ oui | notice | mondial | https://github.com/ml-explore/mlx-lm | 15/09/2026 |
| **Qwen3-TTS-12Hz-1.7B-CustomVoice** | code + poids | Apache-2.0 | ✅ oui | notice ; aucun filigrane | mondial | https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice | 15/09/2026 |
| **Chatterbox Multilingual v3** | code + poids | MIT | ✅ oui | notice ; **filigrane PerTh non désactivable** | mondial | https://resemble.ai/learn/models/chatterbox-multilingual | 15/09/2026 |
| **Kokoro-82M** | poids | Apache-2.0 | ✅ oui | notice | mondial | https://huggingface.co/hexgrad/Kokoro-82M | 15/09/2026 |
| **Kokoro-82M** | **dépendances d'exécution** | **GPL-3.0** (`phonemizer-fork`, espeak-ng via `espeakng-loader`) | ✅ oui (la GPL autorise l'usage commercial) | ⚠️ chargées **en processus**, pas en binaire externe. Obligations déclenchées **à la distribution** du logiciel — BMS ne distribue pas le pipeline. **Kokoro sort si cette hypothèse change.** Les vidéos produites ne sont pas des œuvres dérivées | mondial | https://pypi.org/pypi/phonemizer-fork/json | 15/09/2026 |
| **parakeet-mlx** | code | Apache-2.0 | ✅ oui | notice | mondial | https://github.com/senstella/parakeet-mlx | 15/09/2026 |
| **nvidia/parakeet-tdt-0.6b-v3** | **poids** | **CC-BY-4.0** | ✅ oui | ⚠️ **attribution NVIDIA obligatoire dans la description de chaque vidéo** | mondial | https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3 | 15/09/2026 |
| **mlx-whisper** | code | MIT | ✅ oui | notice | mondial | https://pypi.org/project/mlx-whisper | 15/09/2026 |
| **Whisper large-v3-turbo** | poids | MIT | ✅ oui | notice | mondial | https://huggingface.co/openai/whisper-large-v3-turbo | 15/09/2026 |
| **whisper.cpp** | code + poids GGML | MIT | ✅ oui | notice | mondial | https://github.com/ggml-org/whisper.cpp | 15/09/2026 |
| **FLUX.2-klein-4B** (dépôt officiel, bf16) | poids | Apache-2.0 — « *Open weights available for commercial use under the Apache 2.0 license.* » | ✅ oui | notice. ⚠️ **23,74 Go, dont un doublon interne de 7,75** : ce n'est **pas** la route retenue, voir la ligne suivante | mondial | https://huggingface.co/black-forest-labs/FLUX.2-klein-4B | 15/09/2026 |
| **`mlx-community/FLUX.2-Klein-4B-4bit`** — ✅ **route retenue, celle qui est installée** | poids quantifiés 4 bits | **Apache-2.0** — `license: apache-2.0` dans `cardData`, dans les `tags` et dans le README, **les trois vérifiés le 15/09/2026** | ✅ oui | notice. **4,62 Go, aucune quantification locale à faire.** Dérive du 4B officiel Apache-2.0, **pas** de FLUX.1-dev | mondial | https://huggingface.co/mlx-community/FLUX.2-Klein-4B-4bit | 15/09/2026 |
| **FLUX.2-klein-4B** | **encodeur de texte + VAE embarqués** | Apache-2.0 (même LICENSE) | ✅ oui | encodeur = `Qwen3ForCausalLM` in-repo (hidden 2560 → Qwen3-4B) ; **aucun CLIP ni T5 tiers n'est tiré** | mondial | https://huggingface.co/black-forest-labs/FLUX.2-klein-4B | 15/09/2026 |
| **mflux** | code | MIT | ✅ oui | notice | mondial | https://github.com/filipstrand/mflux | 15/09/2026 |
| **SDXL 1.0** | poids | CreativeML Open RAIL++-M | ✅ oui | « *Licensor claims no rights in the Output* » ; annexe A (11 interdictions) à répercuter en cas de redistribution du modèle ou d'un LoRA | mondial | https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/blob/main/LICENSE.md | 15/09/2026 |
| **IP-Adapter** | code + poids | Apache-2.0 | ✅ oui | notice | mondial | https://huggingface.co/h94/IP-Adapter | 15/09/2026 |
| **diffusers** | code | Apache-2.0 | ✅ oui | notice | mondial | https://github.com/huggingface/diffusers | 15/09/2026 |
| **Depth Anything V2 Small** | poids | Apache-2.0 | ✅ oui | notice | mondial | https://huggingface.co/depth-anything/Depth-Anything-V2-Small | 15/09/2026 |
| **DA3-BASE** | poids | Apache-2.0 | ✅ oui | notice | mondial | https://huggingface.co/depth-anything/DA3-BASE | 15/09/2026 |
| **MiDaS 3.1** | code + poids | MIT | ✅ oui | notice | mondial | https://github.com/isl-org/MiDaS | 15/09/2026 |
| **Revideo** | code | MIT — « *MIT License — Copyright (c) 2022 motion-canvas* » ; LICENSE **identique octet pour octet** sur `midrender/revideo` et `redotvideo/revideo` | ✅ oui | notice ; ⚠️ **télémétrie PostHog par défaut** → `DISABLE_TELEMETRY=true` ; **aucun service cloud ni clé requis** pour le rendu local | mondial | https://raw.githubusercontent.com/midrender/revideo/main/LICENSE | 15/09/2026 |
| **MoviePy 2.2.1** | code | MIT | ✅ oui | notice | mondial | https://github.com/Zulko/moviepy | 15/09/2026 |
| **Manim CE 0.21** | code | MIT | ✅ oui | notice | mondial | https://github.com/ManimCommunity/manim | 15/09/2026 |
| **vtracer** | code | MIT (crate `MIT OR Apache-2.0`) | ✅ oui | notice ; champ licence PyPI vide, licence lue au dépôt | mondial | https://github.com/visioncortex/vtracer | 15/09/2026 |
| **whiteboard-animator 0.1.1** | code | MIT | ✅ oui | notice | mondial | https://github.com/masihsultani/whiteboard-animator | 15/09/2026 |
| **Rhubarb Lip Sync 1.14** | code + binaire | MIT — « *Rhubarb Lip Sync is released under the MIT License (MIT)* » | ✅ oui | notice ; « *the resulting lip sync data belongs to you alone* » ; ⚠️ GitHub affiche « NOASSERTION » en façade, la licence est dans `LICENSE.md` | mondial | https://raw.githubusercontent.com/DanielSWolf/rhubarb-lip-sync/master/LICENSE.md | 15/09/2026 |
| **Montreal Forced Aligner 3.4.2** | code | MIT — « *Copyright (c) 2016 Montreal Corpus Tools* » | ✅ oui | notice ; **aucun poids téléchargé à l'installation** | mondial | https://github.com/MontrealCorpusTools/Montreal-Forced-Aligner | 15/09/2026 |
| **MFA — modèles acoustiques** (french_mfa, english_mfa, spanish_mfa, italian_mfa) | **poids** | **CC-BY-4.0** | ✅ oui | ⚠️ **attribution due** (texte en section 3) ; tirés à la demande par `mfa model download` | mondial | https://mfa-models.readthedocs.io | 15/09/2026 |
| **OpenFaceFX 0.24.0** | code | MIT | ✅ oui | notice ; **aucun poids** — `requires_dist` = numpy seul ; sortie 15 visèmes Oculus/Meta, retarget documenté vers **Preston Blair (Rhubarb)**, ARKit et VRM | agnostique | https://github.com/OpenFaceFX/OpenFaceFX | 15/09/2026 |
| **Open Peeps** | assets | CC0 1.0 | ✅ oui | aucune | mondial | https://www.openpeeps.com | 15/09/2026 |
| **Humaaans** | assets | CC0 1.0 | ✅ oui | aucune | mondial | https://www.humaaans.com | 15/09/2026 |
| **Avataaars** | assets + code | MIT | ✅ oui | notice | mondial | https://github.com/fangpenlin/avataaars | 15/09/2026 |
| **Kenney** | assets | CC0 1.0 | ✅ oui | aucune | mondial | https://kenney.nl | 15/09/2026 |
| **DiceBear** | code | MIT | ✅ oui | notice | mondial | https://www.dicebear.com/licenses | 15/09/2026 |
| **DiceBear** | styles | **42 styles en CC0 1.0**, 14 en CC-BY (confirmé sur la page des licences) | ✅ oui | ⚠️ **vérifier style par style** ; attribution due sur les 14 CC-BY | mondial | https://www.dicebear.com/licenses | 15/09/2026 |
| **rembg** | code | MIT | ✅ oui | notice ; ⚠️ **forcer `-m birefnet-general`** (défaut `bria-rmbg` = contrat payant) | mondial | https://github.com/danielgatis/rembg | 15/09/2026 |
| **BiRefNet (birefnet-general)** | code + poids | MIT (dépôt et fiche HF `license:mit`) | ✅ oui | notice ; ⚠️ le fichier `.onnx` est **redistribué par les releases de rembg** sans licence jointe — enregistrer les **deux** URL dans `MODELES.md` : l'origine de la licence et l'origine du fichier | mondial | https://huggingface.co/ZhengPeng7/BiRefNet | 15/09/2026 |
| **U-2-Net (u2net)** | code + poids | Apache-2.0 | ✅ oui | notice ; dataset DIS5K sous conditions séparées, non utilisé | mondial | https://github.com/xuebinqin/U-2-Net | 15/09/2026 |
| **PyObjC (framework Vision)** | code | MIT | ✅ oui | notice ; le framework Vision est un composant de macOS, couvert par la licence système | mondial | https://pyobjc.readthedocs.io | 15/09/2026 |
| **ffmpeg 8.1.2 (build Homebrew)** | binaire | **GPLv3** (`--enable-gpl --enable-version3`) | ✅ oui | ⚠️ appelé comme **binaire externe**, sans édition de liens ni redistribution → aucune obligation de diffusion de notre code. Si BMS redistribuait un jour le pipeline, repasser sur un build LGPL | mondial | https://ffmpeg.org/legal.html | 15/09/2026 |
| **Pexels** | contenu + API | Pexels License | ✅ oui | attribution non exigée par la licence, **imposée par l'API** : « Photo by X on Pexels » + lien ; copie massive et data mining interdits | mondial | https://www.pexels.com/license/ | 15/09/2026 |
| **Pixabay** | contenu + API | Pixabay Content License | ✅ oui | aucune attribution ; **cache 24 h obligatoire** ; pas de diffusion « standalone » ; marques et personnes reconnaissables hors licence | mondial | https://pixabay.com/service/terms/ | 15/09/2026 |
| **Wikimedia Commons** | contenu | par fichier : CC0 / CC-BY / CC-BY-SA / domaine public | ✅ oui (hors BY-SA) | auteur + licence + lien si CC-BY ; **User-Agent identifiant obligatoire** ; ⚠️ **filtrer CC-BY-SA en amont** (viral) | mondial | https://commons.wikimedia.org/wiki/Commons:Licensing | 15/09/2026 |
| **Openverse** | API | licence de la source, par élément | ⚠️ à revérifier | le service « *does not verify its licensing status* » → revérifier à la source avant usage | mondial | https://docs.openverse.org | 15/09/2026 |
| **NASA Image and Video Library** | contenu | domaine public américain | ✅ oui | crédit « NASA » ; ⚠️ logo protégé ; ⚠️ astronautes et employés NASA exclus du commercial ; ⚠️ **et toute personne identifiable** : « *If a NASA image […] includes an identifiable person, using the media for commercial purposes may infringe that person's right of privacy or publicity.* » → filtrer sur `person_release`, pas sur « astronaute » | mondial | https://www.nasa.gov/nasa-brand-center/images-and-media/ | 15/09/2026 |
| **Coverr** | contenu | Coverr License | ✅ oui | aucune attribution ; palier Demo 50 req/h | mondial | https://coverr.co/license | 15/09/2026 |
| **Mixkit** | contenu | Mixkit Stock Video License | ⛔ **non vérifié** | **Source inaccessible** : la page de licence charge son texte par une modale JavaScript, le HTML servi ne rend que la navigation. La distinction *Free* / *Restricted* n'a pas pu être lue. **Bloqué jusqu'à lecture à la source** | mondial | https://mixkit.co/license/ | 15/09/2026 |
| **Unsplash** | contenu + API | Unsplash License | ✅ oui | « Photo by X on Unsplash » + lien profil + utm imposés par l'API ; datasets IA et robots hors API interdits | mondial | https://unsplash.com/license | 15/09/2026 |
| **YouTube Audio Library** | pistes | YTAL ou CC-BY selon la piste | ✅ oui **sur YouTube** | crédit de l'artiste en description si « Attribution required » ; ⚠️ **usage hors YouTube non couvert** par une source officielle | mondial | https://support.google.com/youtube/answer/3376882 | 15/09/2026 |
| **Pixabay Music** | pistes | Pixabay Content License | ✅ oui | aucune attribution ; pas de diffusion « standalone » | mondial | https://pixabay.com/service/terms/ | 15/09/2026 |
| **Incompetech (Kevin MacLeod)** | pistes | CC-BY 4.0 | ✅ oui | ⚠️ **crédit exact obligatoire** (texte en section 3) | mondial | https://incompetech.com | 15/09/2026 |
| **ACE-Step 1.5** | code + poids | MIT | ✅ oui | notice ; **repli conditionnel au budget disque** | mondial | https://github.com/ace-step/ACE-Step-1.5 | 15/09/2026 |
| **Playwright** | code | Apache-2.0 | ✅ oui | notice ; Chromium embarqué sous BSD-3-Clause | mondial | https://playwright.dev | 15/09/2026 |
| **satori** | code | MPL-2.0 | ✅ oui | modifications **du fichier source MPL** à repartager ; notre code applicatif reste à nous | mondial | https://github.com/vercel/satori | 15/09/2026 |
| **resvg-js** | code | MPL-2.0 | ✅ oui | idem satori | mondial | https://github.com/yisibl/resvg-js | 15/09/2026 |
| **Pillow** | code | MIT-CMU (renommage SPDX de HPND) | ✅ oui | notice ; aucun changement de droits par rapport à HPND | mondial | https://github.com/python-pillow/Pillow | 15/09/2026 |
| **Anton, Oswald** (Google Fonts) | polices | SIL OFL 1.1 | ✅ oui | redistribuable ; nom réservé si modification ; **accents FR/ES/IT vérifiés présents** | mondial | https://github.com/google/fonts/tree/main/ofl | 15/09/2026 |
| **Inter** (variable, Google Fonts) | police | SIL OFL 1.1 | ✅ oui | **copiée dans le dépôt** (`assets/fonts/Inter[opsz,wght].ttf`, 0,86 Mo, + `OFL.txt`), c'est la police de charte des 4 chaînes ; instances nommées (Regular … Black) employées par Pillow ; accents FR vérifiés au rendu (étape 12.1) | mondial | https://github.com/google/fonts/tree/main/ofl/inter | 16/09/2026 |
| **Playfair Display**, **Source Serif 4** (variables, Google Fonts) | polices | SIL OFL 1.1 | ✅ oui | **copiées dans le dépôt** (`assets/fonts/PlayfairDisplay[wght].ttf` 0,30 Mo, `SourceSerif4[opsz,wght].ttf` 1,2 Mo) — charte de `bms-histoire-en`, posée par l'étape 17 : titre serif à fort contraste, texte serif lisible en petit corps ; instances nommées résolues par `factory/video.py:FICHIERS_POLICES` ; accents FR vérifiés au rendu | mondial | https://github.com/google/fonts/tree/main/ofl | 18/09/2026 |
| **Caveat** (variable, Google Fonts) | police | SIL OFL 1.1 | ✅ oui | **copiée dans le dépôt** (`assets/fonts/Caveat[wght].ttf`, 0,40 Mo) — **police manuscrite** du style `whiteboard`, posée par l'étape 30.2 : texte à l'écran et sur-titre de segment, tracés comme le dessin ; servie au navigateur par `render/src/fonts/Caveat-Variable.ttf` (lien vers le fichier du dépôt, jamais une copie) ; instance « SemiBold » résolue par `factory/video.py:FICHIERS_POLICES` | mondial | https://github.com/google/fonts/tree/main/ofl/caveat | 19/09/2026 |
| **Mains du whiteboard** (`assets/charte/main.png`, `main_2.png`) | assets de charte | travail propre (BMS) | ✅ oui | **tracées par du code** — `outils/mains_whiteboard.py`, 8 Ko chacune, reproductibles. Ni téléchargées (aucune licence tierce à suivre), ni générées par diffusion (FLUX dessine mal les mains, mesure de l'étape 5.2, et il aurait fallu les détourer). Aucune attribution à verser | mondial | — | 19/09/2026 |
| **Tabler Icons** | icônes SVG | MIT — « *MIT License — Copyright (c) 2020-2025 Paweł Kuna* » | ✅ oui | notice ; **42 icônes extraites dans le dépôt** (`render/src/icons.ts`, 8 Ko, générées par `render/outils_icones.mjs` depuis `@tabler/icons@3.36.0`) ; ligne d'attribution portée par chaque `assets/<plan>/licence.json` du style motion, **pas** dans la description des vidéos (§ 6) | mondial | https://github.com/tabler/tabler-icons/blob/main/LICENSE | 19/09/2026 |
| **PySceneDetect** | code | BSD-3-Clause | ✅ oui | notice ; dépendance dure à opencv-python (Apache-2.0) | mondial | https://github.com/Breakthrough/PySceneDetect | 15/09/2026 |
| **libvmaf** | code + modèles | BSD-2-Clause-Patent | ✅ oui | notice ; déjà compilé dans le ffmpeg local | mondial | https://github.com/Netflix/vmaf | 15/09/2026 |
| **imagehash** | code | BSD-2-Clause | ✅ oui | notice ; tire scipy (BSD-3) | mondial | https://pypi.org/project/ImageHash/ | 15/09/2026 |
| **jiwer 4.0** | code | Apache-2.0 | ✅ oui | notice | mondial | https://pypi.org/project/jiwer/ | 15/09/2026 |
| **tesseract** + `tessdata_fast` | code + données | Apache-2.0 | ✅ oui | notice | mondial | https://github.com/tesseract-ocr/tessdata_fast | 15/09/2026 |

---

### 1 bis. Étape 29 — personnages, détourage, voix, intros (24/09/2026)

| Outil / asset | Composant | Licence exacte | Commercial | Obligations | Territoire | URL | Vérifié le |
|---|---|---|---|---|---|---|---|
| **rembg 2.0.85** | code | MIT | ✅ oui | notice | mondial | https://github.com/danielgatis/rembg | 24/09/2026 |
| **BiRefNet** (`birefnet-general-lite`, ONNX servi par rembg) | poids | MIT (dépôt BiRefNet) | ✅ oui | notice | mondial | https://github.com/ZhengPeng7/BiRefNet | 24/09/2026 |
| **Apple Vision** (`VNDetectFaceLandmarksRequest`) | framework système | licence macOS | ✅ oui (usage local) | aucune redistribution | — | https://developer.apple.com/documentation/vision | 24/09/2026 |
| **Personnage `nova`** (`workspace/library/characters/nova/`) | `base.png`, `mouths/*.png`, `eyes_*.png` | sortie de FLUX.2 [klein] 4B (Apache-2.0) éditée par le même modèle ; calques dérivés par BMS | ✅ oui | aucune ; personnage **généré**, aucune personne réelle ni ressemblance recherchée | mondial | https://huggingface.co/black-forest-labs/FLUX.2-klein-4B | 24/09/2026 |
| **Intros / outros de charte** (`workspace/library/intros/`) | MP4 composés | BMS + polices SIL OFL 1.1 de la charte | ✅ oui | notice OFL si les polices sont redistribuées (elles ne le sont pas : rendu) | mondial | https://openfontlicense.org | 24/09/2026 |
| **Kits 2D écartés** : Open Peeps (CC0), Humaaans (CC0 sur le site, CC BY 4.0 sur le miroir GitHub), Avataaars | — | — | — | **non employés** : aucun ne fournit de bouches séparables par visème (sous-agent, 24/09/2026) | — | https://www.openpeeps.com/ | 24/09/2026 |

**Voix de référence (`config/voices/*.yaml → reference_wav`)** : aucune à ce jour. Toute
référence future doit être listée ici par nom de fichier, avec l'accord écrit du locuteur ;
`factory config validate` refuse un profil dont le WAV n'y figure pas.

## 2. Éliminés pour licence

Motif cité, pas résumé. Un outil listé ici ne doit **jamais** remonter en principal sans une nouvelle vérification datée.

### Exclusion territoriale — le motif le plus grave
| Outil | Motif exact |
|---|---|
| **Llama 4** (toutes variantes) | Llama 4 Community License + AUP : licence **non accordée aux personnes domiciliées dans l'Union européenne ni aux sociétés y ayant leur siège**. BMS est une société française. Toutes les variantes Llama 4 sont multimodales, donc toutes concernées. |
| **HunyuanVideo** | Territoire hors UE. |

### Plafond de revenus ou de personnes
| Outil | Motif exact |
|---|---|
| **Stable Audio Open Small** | Stability AI Community License : gratuité cessant au-delà de « *USD $1,000,000 in annual revenue* ». Un plafond de revenus transforme un succès en violation. |
| **Remotion** | Licence propriétaire : « *You are eligible to use Remotion for free if you are: an individual / a for-profit organization with up to 3 employees / a non-profit* ». Au-delà, Company License à 25 $/siège/mois. **Non retenu : Revideo (MIT) couvre le besoin, la clause n'a donc pas à s'appliquer.** |
| **Hallo3** | CogVideoX-5B : licence commerciale sur demande, plafond « *must not exceed 1 million visits per month* ». |
| **BRIA RMBG-2.0** | Contrat payant exigé pour l'usage commercial. |

### Non commercial explicite
| Outil | Motif exact |
|---|---|
| **FLUX.2-klein-9B, FLUX.1-dev, FLUX.2-dev 32B** | « FLUX Non-Commercial License ». |
| **Certains** dépôts tiers `FLUX.2-klein-4B-mflux-4bit` | Tagués `flux-1-dev-non-commercial-license` : **ceux-là dérivent de FLUX.1-dev**, non commercial. ⚠️ **Ne pas généraliser** : `mlx-community/FLUX.2-Klein-4B-4bit` dérive du 4B officiel et est Apache-2.0 (section « Utilisables en commercial »). **La règle est de vérifier le tag du dépôt, pas d'exclure les dépôts 4-bit par principe — et surtout pas de requantifier localement, ce qui coûterait 23,74 Go pour rien.** |
| **Depth Anything V2 Base / Large / Giant** | `cc-by-nc-4.0`. |
| **DA3 Large / Giant / Nested any-view** | CC-BY-NC-4.0. |
| **Apple Depth Pro** | Apple ML Research Model License : « *exclusively for Research Purposes* », « *excludes commercial exploitation* ». |
| **F5-TTS** | Poids CC-BY-NC. |
| **XTTS / Coqui** | Licence CPML, non commerciale. |
| **Higgs Audio v3 / OmniVoice** | « Research and Non-Commercial License ». |
| **VibeVoice** | Recherche seulement. |
| **MusicGen** | « *model weights are released under CC-BY-NC 4.0* ». |
| **Wav2Lip** | Aucun fichier LICENSE ; « *This repository can only be used for personal/research/non-commercial purposes* » et « *As the models are trained on the LRS2 dataset, any form of commercial use is strictly prohibited.* » |
| **Sonic** | CC-BY-NC-SA 4.0 : « *Note that our license is non-commercial.* » |
| **torchaudio MMS_FA** | API BSD-2, mais poids « *published under a CC-BY-NC 4.0 License* » (documentation PyTorch). |
| **allosaurus** | GPL-3.0, et le modèle est tiré des releases GitHub **sans licence déclarée**. |
| **papagayo-ng** | GPL-2, projet figé depuis le 25/04/2023. |
| **LivePortrait** | LICENSE l. 25-30 : « *The models of InsightFace are for non-commercial research purposes only […] you should remove and replace InsightFace's detection models* ». Les poids `KlingTeam` tagués `mit` embarquent `buffalo_l/det_10g.onnx`. |
| **Hallo / Hallo2** | InsightFace obligatoire, même clause. |
| **SadTalker** | **Éliminé par le contradicteur, pas par sa licence propre.** Son `scripts/download_models.sh` télécharge **GFPGANv1.4.pth sans condition**. Le LICENSE de GFPGAN porte StyleGAN2 sous licence Nvidia § 3.3 : « *The Work and any derivative works thereof only may be used or intended for use non-commercially […] "non-commercially" means for research or evaluation purposes only.* » et DFDNet : « *Their license is Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.* » Un catalogue YouTube monétisé est un usage commercial. **C'est exactement le motif retenu contre LivePortrait et Hallo** — il avait été appliqué de façon inégale dans mon premier jet. S'ajoute une ambiguïté propre : le LICENSE de SadTalker dit « *Apache 2.0 License, except for the third-party components listed below* », **sans qu'aucune liste ne figure dans le fichier** (carve-out indéfini), et ses poids viennent des *releases GitHub*, non d'un dépôt Hugging Face. |
| **Mixkit** | Licence **non lisible à la source** : la page charge son texte par une modale JavaScript. La distinction *Free* / *Restricted* n'a pas pu être vérifiée. Bloqué par la règle « pas de licence claire, pas d'outil » jusqu'à lecture effective. |
| **Linly-Talker** | MIT en façade, agrège Wav2Lip : contaminé. |
| **WhisperX — diarisation** | Backend DiariZen en CC-BY-NC-4.0 ; pyannote exige l'acceptation de conditions et un jeton HF. Le cœur BSD-2-Clause resterait utilisable, mais les modèles d'alignement wav2vec2 FR/ES/IT viennent de dépôts tiers aux licences non vérifiées. |
| **CC-BY-NC et CC-BY-ND sur Freesound et ccMixter** | Rejetés par `docs/CONFORMITE.md` § 7. |
| **SDXL-Turbo / SD-Turbo** | Licences non commerciales. |
| **IndexTTS 2** | Licence maison restrictive. |
| **CogVideoX-5B** | Licence restrictive, voir Hallo3. |

### Licence absente, contradictoire ou révocable — écartés par la règle « pas de licence claire, pas d'outil »
| Outil | Motif exact |
|---|---|
| **Freesound (API)** | Les sons sont sous CC0/CC-BY, mais les CGU de l'**API** la déclarent « *free for non-commercial use* », l'usage commercial étant « *negotiated case by case with UPF* ». **Contradiction non résolue par les CGU.** Écarté du pipeline automatisé ; téléchargement manuel de sons CC0 non concerné. |
| **MuseTalk 1.5 et son portage MLX** | Contradiction : le README annonce des poids « *available for any purpose, even commercially* », le champ de licence Hugging Face indique `creativeml-openrail-m`. Dépendance S3FD sans fichier LICENSE. Le portage MLX est une relabellisation MIT par un tiers sur un amont OpenRAIL. |
| **Draw Things** | Application gratuite **sans CGU ni EULA publiés** ; seule une politique de confidentialité existe, muette sur les sorties. Droit d'usage commercial des images **non établi par écrit**. |
| **Ollama — application de bureau** | **Aucune licence publiée** (issue #11634 fermée sans réponse). La CLI est MIT et resterait utilisable ; l'application ne l'est pas. |
| **GSAP 3.15** | Gratuit en commercial sous licence Webflow, mais **révocable**. Pas de dépendance structurelle sur une licence retirable. |
| **Videvo** | Redirection 301 vers freepik.com, page de licence en 403 : licence **non consultable**, donc non vérifiable. |
| **Internet Archive** | « *does not make guarantees as to the copyright status* ». Figure dans la liste blanche de `docs/CONFORMITE.md` § 8 — **retrait ou restriction proposé**. |
| **Supertonic 3** | Poids sous OpenRAIL-M avec restrictions d'usage attachées, et nombre de voix par langue non documenté. |

### Écartés pour un motif technique, pas juridique
| Outil | Motif exact |
|---|---|
| **Motion Canvas** | MIT, licence irréprochable. **Rendu headless non documenté** : issue #1218 ouverte le 14/10/2025, toujours ouverte. Sans rendu en ligne de commande, pas d'autonomie. |
| **Z-Image-Turbo 6B** | Apache-2.0, éligible. **33 Go à télécharger** avant quantification : incompatible avec la règle disque. |
| **YuE** | Passé en Apache-2.0 (la veille le disait CC-BY-NC, c'est périmé). 7 B de paramètres : hors budget. |
| **EchoMimicV3** | Apache-2.0 sur code, poids et base Wan2.1-Fun. 12 Go de VRAM annoncés, jamais testé en mémoire unifiée. |
| **Bebas Neue** | SIL OFL 1.1, licence parfaite. **Accents bas-de-casse absents** : inutilisable en FR, ES et IT. |
| **potrace** | GPL-2.0+. La sortie d'un **binaire** GPL n'est pas contaminée (GPL FAQ), l'usage serait donc licite ; écarté parce qu'il ne vectorise pas la couleur. ⚠️ **Ne jamais lier `libpotrace` ni `pypotrace`** (GPL-3, contaminant). |
| **ComfyUI** | GPL-3.0. Usage interne sans redistribution = sans conséquence ; écarté pour éviter une contrainte inutile quand mflux (MIT) suffit. |
| **cairosvg** | LGPL-3.0-or-later ; écarté sur le poids (wheel 46 Mo + ~10 formules Homebrew), pas sur la licence. |
| **wkhtmltoimage** | Projet archivé, aucun build arm64. |
| **Free Music Archive** | « *we unfortunately had to shut down our API* ». |
| **Mistral Small 24B** | Ne tient pas en mémoire à côté du reste du pipeline. |
| **Gemma 3** | Gemma Terms + Prohibited Use Policy. **Remplacé par Gemma 4, passé en Apache-2.0** — l'élimination ne vaut plus que pour la génération 3. |

---

## 3. Attributions à insérer automatiquement

Textes **prêts à l'emploi**. `docs/CONFORMITE.md` § 7 et § 8 imposent la composition automatique d'un bloc d'attribution en fin de description : un crédit manuel sera oublié. Ce bloc vient **après** la mention de promotion payante, qui reste en première ligne (§ 3, couche 3).

### 3.1 Toujours présent dès que l'outil est utilisé

**NVIDIA Parakeet — poids CC-BY-4.0, attribution obligatoire :**
```
Sous-titres générés avec NVIDIA Parakeet TDT 0.6B v3 (https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3), sous licence CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/).
```

**Modèles acoustiques MFA — CC-BY-4.0, attribution due dès que le repli avatar est utilisé :**
```
Synchronisation labiale alignée avec Montreal Forced Aligner (modèle acoustique {langue}_mfa), sous licence CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/).
```

### 3.2 Par asset, composé automatiquement

**Pexels** (imposé par les conditions de l'API) :
```
Photo by {author} on Pexels — {source_url}
Vidéo par {author} sur Pexels — {source_url}
```

**Unsplash** (imposé par l'API, avec lien de profil et paramètre utm) :
```
Photo by {author} on Unsplash — {profile_url}?utm_source=bms&utm_medium=referral
```

**Wikimedia Commons** (dès que la licence est CC-BY ; les CC-BY-SA sont filtrés en amont) :
```
{title} — {author}, via Wikimedia Commons, {licence} ({licence_url}) — {source_url}
```

**NASA** :
```
Crédit : NASA — {source_url}
```

**Openverse** — **le texte n'est pas composé localement** : l'API rend un champ `attribution`
déjà rédigé, et c'est lui qui fait foi. Le recomposer à partir de `creator` et `license`
perdrait la version de licence et la phrase « *To view a copy of this license, visit …* » que
Creative Commons exige. Gabarit de secours, employé seulement si le champ est vide :
```
{title} — {author}, via Openverse, {licence} ({licence_url}) — {source_url}
```

**Internet Archive** — aucun texte officiel n'est publié : le service ne garantit pas le statut
des œuvres (voir § « Écartés », ci-dessous). D'où une attribution qui **nomme la source du
doute** en même temps que l'auteur, pour qu'une réclamation puisse être instruite :
```
{title} — {author}, Internet Archive, {licence} — {source_url}
```
**Restriction appliquée par le code** (`factory/assets/stock.py`), en réponse au « retrait ou
restriction proposé » du § « Écartés » : seuls les items dont le champ `licenseurl` porte
explicitement `publicdomain/zero`, `publicdomain/mark` ou `licenses/by` sont retenus. Aucun item
n'est accepté au seul motif de son ancienneté, et les `by-sa` sont éliminés ensuite comme
partout ailleurs.

**Pixabay** et **Coverr** : aucune attribution exigée. Les champs `author` et `source_url` sont **tout de même enregistrés** dans le manifeste (`docs/CONFORMITE.md` § 8 les rend obligatoires à l'acquisition, indépendamment de l'obligation d'affichage).

### 3.3 Musique

**YouTube Audio Library**, uniquement quand la piste porte « Attribution required » :
```
Musique : « {titre} » — {artiste}, YouTube Audio Library, {licence} ({licence_url}).
```

**Incompetech / Kevin MacLeod — texte contractuel, à reproduire mot pour mot, sans traduction :**
```
« {titre} » Kevin MacLeod (incompetech.com)
Licensed under Creative Commons: By Attribution 4.0
https://creativecommons.org/licenses/by/4.0/
```

**Pixabay Music** : aucune attribution exigée.

### 3.4 Kits de personnages 2D

**Open Peeps, Humaaans, Kenney, styles DiceBear CC0** : domaine public, aucune attribution due. Un crédit de courtoisie reste possible.

**Styles DiceBear sous CC-BY** (14 des 56) — **vérifier style par style** avant usage :
```
Personnage : style « {style} » — {author}, DiceBear, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/).
```

### 3.5 Ce qui ne se met jamais dans la description

Les licences **MIT, Apache-2.0, BSD et MPL-2.0** des outils (llama.cpp, Revideo, rembg, Playwright, ffmpeg…) n'exigent aucune attribution auprès du **public** : elles exigent la conservation de la notice dans **le code distribué**. BMS ne distribue pas le pipeline. **Ne pas polluer les descriptions de vidéos avec ces mentions** — elles appartiennent au dépôt, pas à la chaîne.

Exception à surveiller : **ffmpeg est un binaire GPLv3**. Tant qu'il est appelé comme programme externe et que le pipeline n'est pas redistribué, aucune obligation n'est déclenchée. **Si BMS redistribuait un jour le pipeline, il faudrait soit repasser sur un build LGPL, soit satisfaire la GPL.**
