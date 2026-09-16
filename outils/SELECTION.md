# SELECTION.md — outils retenus par brique

Étape 4, arrêté le 15/09/2026. Machine cible : MacBook Air M2, 8 cœurs, 16 Go de RAM unifiée, macOS 27.0, **46 Gi libres** (mesuré ce jour), Metal/MPS ou CPU, pas de CUDA.

**Ce fichier est une sélection, pas une mesure.** Les vitesses portent leur source ou la mention « à mesurer ». Les étapes 5.1 et 5.2 mesurent, avec les seuils de décision inscrits ici. Les licences sont détaillées dans `outils/LICENCES.md` ; toute licence non commerciale est éliminatoire (`CLAUDE.md` § 11, `docs/CONFORMITE.md` § 7 et 8).

**Règle de lecture.** « Principal » = ce qui est téléchargé et mesuré en premier. « Repli » = ce qui monte si le principal tombe sous son seuil. Aucun des deux n'est acquis avant 5.1/5.2.

## Corrections apportées à la veille du 13/09/2026 (`ROADMAP.md` § 3.5)

Sept points de la veille sont faux ou périmés. Ils sont corrigés ici sur source primaire.

| # | La veille disait | Vérifié le 15/09/2026 | Conséquence |
|---|---|---|---|
| 1 | « Qwen3.5-**7B** Q4, ~5,2 Go, ≈ 22 tok/s » | **Le 7B n'existe pas** : la série Small est 0,8B / 2B / 4B / 9B. Les « 22 tok/s » sont extrapolés d'un ratio de bande passante, jamais mesurés sur un M2 Air | Principal = 9B (6,17 Go) ou 4B ; vitesse **à mesurer** |
| 2 | « Gemma 4 E4B (Apache-2.0) » présenté à côté de « Gemma 3 éliminé (Gemma Terms) » | **Confirmé et c'est une rupture** : Gemma 4 est bien sous Apache-2.0, sans gating HF, contrairement à Gemma 3 | Gemma 4 E4B devient un repli propre |
| 3 | « Kokoro-82M · FR une seule voix notée B- » donné comme candidat principal | **Une seule voix FR est disqualifiante** au regard de l'exigence « ≥ 2 voix par langue ». `VOICES.md` admet un G2P faible hors anglais | Kokoro rétrogradé en repli anglophone |
| 4 | « parakeet-tdt-0.6b-v3 · 2,5 Go » | **0,6 Go**, pas 2,5 | Budget disque allégé de 1,9 Go |
| 5 | « FLUX.2 [klein] 4B en mflux 4-bit · 4,6 Go » | Le modèle est Apache-2.0, mais **les dépôts 4-bit tiers sont tagués `flux-1-dev-non-commercial-license`** | Quantification **à faire nous-mêmes** ; pic disque ~20 Go pendant l'opération |
| 6 | « détourage rembg-BiRefNet (MIT) » | Exact, mais **le modèle par défaut de rembg est `bria-rmbg`, qui exige un contrat payant** en usage commercial | `-m birefnet-general` **obligatoire et explicite** dans le code |
| 7 | « potrace (GPL, préférer vtracer) » | Exact sur le choix, inexact sur le motif : la sortie d'un **binaire** GPL n'est pas contaminée (GPL FAQ) | vtracer retenu pour la couleur, pas pour la licence |

---

## 1. LLM — génération de script

**Critère qui prime : la qualité du français et de l'italien.** Le script est relu par un humain (`docs/CONFORMITE.md` § 4) mais jamais réécrit : un modèle qui calque l'anglais coûte plus cher en relecture qu'il ne rapporte en vitesse. Le second critère est la RAM, puisque `CLAUDE.md` § 4 impose un seul modèle résident.

**Principal — Qwen3.5-9B, quantification Q4_K_M, via llama.cpp.**
- Poids : **6,17 Go**. Licence : Apache-2.0, aucune condition, aucun territoire exclu. 201 langues annoncées, FR/EN/ES/IT couverts.
- Installation : `brew install llama.cpp` puis `llama-cli -hf bartowski/Qwen_Qwen3.5-9B-GGUF:Q4_K_M`
- Pourquoi : c'est le seul candidat Apache-2.0 de cette taille qui annonce les quatre langues cibles au même niveau. GGUF = un seul format sur disque, contrairement à mlx-lm qui exigerait un second jeu de poids.
- Piège : 9B + cache KV sature 16 Go si un TTS est co-résident. Le pipeline doit fermer le processus LLM avant d'ouvrir le TTS — c'est déjà la règle 4.

**Repli — Gemma 4 E4B, Q4_K_M.**
- Poids : **4,98 Go**. Licence : Apache-2.0 (rupture avec les « Gemma Terms » de Gemma 3), sans gating Hugging Face.
- Installation : `ollama pull gemma4:e4b` ou GGUF via llama.cpp.
- Piège : **27,5 Go de cache à 128k de contexte** — plafonner le contexte à 8k dans la configuration, sinon la machine tombe.
- Second repli si la RAM est le facteur limitant : **Qwen3.5-4B** (~2,7 Go, taille GGUF non lue sur fichier).

**Runtime — llama.cpp (MIT).** Repli : mlx-lm (MIT), généralement plus rapide sur Apple Silicon mais impose un second jeu de poids sur disque. Ollama n'est pas retenu comme runtime de production : la CLI est MIT, mais **l'application de bureau n'a aucune licence publiée** (issue #11634 fermée sans réponse) — on n'appuie pas un pipeline commercial sur un composant sans licence.

**Écartés**
- **Llama 4 (toutes variantes)** → la Llama 4 Community License n'accorde pas les droits aux personnes domiciliées ni aux sociétés ayant leur siège dans l'**Union européenne**. Rédhibitoire pour BMS.
- **Mistral Small 24B** → ne tient pas en mémoire à côté du reste du pipeline.
- **Ministral 3 8B Instruct 2512** (Apache-2.0, FR/EN/ES/IT natifs) → gardé en réserve documentaire, non mesuré en 5.1 faute de budget disque ; taille GGUF non vérifiée.

**À mesurer en 5.1**
| Incertitude | Seuil de décision |
|---|---|
| Débit réel du 9B Q4_K_M sur M2 Air (aucune mesure publique sur cette puce) | **Retenu si ≥ 8 tok/s** en génération. Sous 8 → Gemma 4 E4B ; sous 8 aussi → Qwen3.5-4B |
| Pic de RAM du 9B à 8k de contexte | **Retenu si < 12 Go** (marge pour ffmpeg et le système) |
| Qualité FR/IT du script sur 3 niches (`spiritualite`, `home_hacks`, `histoire_doc`) | **Retenu si aucun calque anglais** et respect de `mots_par_minute` à ± 10 % ; jugement de Thomas, noté /5 |

---

## 2. TTS — voix off

**Critère qui prime : la qualité du français à l'oreille.** C'est la brique que l'auditeur juge en premier et la seule que la session ne peut pas évaluer elle-même (`CLAUDE.md` § 5) : le verdict revient à Thomas en 5.1.

> **Aucun candidat n'offre nativement ≥ 2 voix en FR, ES et IT.** C'est le constat central de cette brique, et il contredit l'hypothèse de la veille. Le détail :
> - **Kokoro-82M** : 1 seule voix FR (`ff_siwis`, notée B-), 2 voix IT notées C. `VOICES.md` reconnaît un G2P faible hors anglais.
> - **Qwen3-TTS-12Hz-1.7B** : 9 voix préréglées, dont **aucune native FR, ES ou IT** (5 ZH, 2 EN, 1 JA, 1 KO). Le multilingue passe par le mode *cross-lingual* ou par le clonage.
> - **Chatterbox Multilingual** : **aucune voix préréglée**, zero-shot pur — toute voix vient d'un échantillon fourni.
>
> **Conséquence :** l'exigence « ≥ 2 voix par langue » ne peut être satisfaite que **par clonage**. Cela déclenche deux obligations déjà écrites : `contains_synthetic_media = true` pour une voix clonée réaliste (`docs/CONFORMITE.md` § 3, couche 1), et la question — **non résolue** — des droits sur l'échantillon source. Voir « Question ouverte » en fin de section.

**Principal — Qwen3-TTS-12Hz-1.7B-CustomVoice.**
- Poids : **~2,0 Go**. Licence : **Apache-2.0 sur le code *et* sur les poids** — la plus propre des trois candidats. 10 langues dont FR, ES, IT. **Aucun filigrane.**
- Installation : `uv pip install mlx-audio` puis chargement du dépôt `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice`.
- Pourquoi : licence sans réserve, pas de filigrane imposé, clonage intégré (3 s de référence) — c'est-à-dire le seul chemin réaliste vers « 2 voix par langue » sans dépendance externe.

**Repli — Chatterbox Multilingual v3.**
- Poids : **~1,0 Go** (0,5B). Licence : MIT, code et poids. 23 à 25 langues.
- Installation : `uv pip install chatterbox-tts`
- Piège assumé : **filigrane audio PerTh appliqué à chaque sortie, non désactivable.** MIT l'autorise commercialement, mais toutes nos voix deviennent traçables de façon permanente. À accepter en connaissance de cause.

**Second repli, anglophone seulement — Kokoro-82M** (poids Apache-2.0, 0,33 Go) : rapide et stable, retenu uniquement pour des chaînes EN où son catalogue de voix est fourni.
- ⚠️ **Chaîne de dépendances GPL-3.0, omise par la veille et par mon premier jet.** Le paquet PyPI `kokoro` exige `misaki[en]` → `phonemizer-fork` (**GPL-3.0**) → `espeakng-loader`, qui embarque espeak-ng (**GPL-3.0**). Ces bibliothèques sont chargées **dans notre processus Python**, ce n'est donc pas le cas « binaire externe » de ffmpeg.
- **Ce que cela change, exactement** : la GPL-3.0 **autorise l'usage commercial** — elle n'est pas éliminatoire au sens de `CLAUDE.md` § 11. Ses obligations se déclenchent à la **distribution** du logiciel, or BMS n'a jamais prévu de distribuer le pipeline. Kokoro reste donc utilisable **tant que le pipeline n'est pas redistribué**, et sort si cette hypothèse change. Les vidéos produites, elles, ne sont pas des œuvres dérivées du logiciel et ne sont jamais concernées.

**Écartés**
- **F5-TTS** → poids CC-BY-NC. **XTTS / Coqui** → licence CPML non commerciale. **Higgs Audio v3 / OmniVoice** → « Research and Non-Commercial License ». **VibeVoice** → recherche. **IndexTTS 2** → licence maison restrictive.
- **Supertonic 3** → poids sous OpenRAIL-M (restrictions d'usage attachées) et nombre de voix par langue non documenté.

**À mesurer en 5.1**
| Incertitude | Seuil de décision |
|---|---|
| Accent et prosodie FR/ES/IT des voix *cross-lingual* de Qwen3-TTS — **c'est le point qui tranche entre Qwen3-TTS et Chatterbox** | **Retenu si Thomas note ≥ 3,5/5** en FR sur un extrait de 60 s. Sous 3,5 → Chatterbox (filigrane accepté) |
| **≥ 2 timbres distincts par langue, sans clonage** (conséquence directe de la décision du 15/09) | **Retenu si 2 locuteurs préréglés produisent du FR, ES et IT distinguables à l'oreille.** Échec → l'exigence n'est pas tenable à 0 € sans clonage : **arbitrage produit à remonter à Alek**, pas à contourner |
| Facteur temps réel de la synthèse | **Retenu si ≤ 1,0** (une minute d'audio produite en une minute au plus) |
| WER de re-transcription (la voix est-elle intelligible par l'ASR ?) | **Retenu si WER < 5 %** en FR |
| Stabilité MPS sur textes longs (plantages rapportés sur Kokoro/PyTorch même avec `PYTORCH_ENABLE_MPS_FALLBACK=1`) | **Retenu si 10 synthèses de 5 min s'enchaînent sans plantage** |

**Décision de Thomas, 15/09/2026 — aucun clonage pour l'instant.** Thomas n'enregistre pas d'échantillons de référence à ce stade. Les deux autres voies tombent avec : le corpus CC0 est écarté (le CC0 lève le droit d'auteur, **pas les droits de la personnalité attachés à une voix** — risque non couvert pour un catalogue monétisé), et la voie « Thomas enregistre » est reportée, pas abandonnée.

**Ce que cela change, et c'est plutôt favorable :**
- **Le pipeline n'utilise que des voix préréglées.** L'exigence « ≥ 2 voix par langue » se joue donc entièrement sur le mode *cross-lingual* : les 9 locuteurs préréglés de Qwen3-TTS peuvent produire du français sans être des voix françaises. **Deux timbres distincts par langue restent atteignables sans cloner personne** — c'est exactement ce que 5.1 doit mesurer.
- **`contains_synthetic_media` reste `false` pour la voix.** `docs/CONFORMITE.md` § 3 vise « une voix **clonée** réaliste » : une voix de synthèse générique ne clone aucune personne réelle et ne déclenche pas la divulgation. Un souci de conformité en moins sur chaque vidéo.
- **Le champ `voice_release` n'est pas nécessaire** et n'est pas ajouté au modèle de données. À rouvrir seulement si Thomas décide d'enregistrer.
- **Si l'accent cross-lingual est jugé non diffusable en 5.1**, l'exigence « 2 voix par langue » hors anglais n'est pas tenable à 0 € sans clonage : ce n'est alors plus un arbitrage technique mais un arbitrage produit, **à remonter à Alek**, pas à contourner.

**Décision de Thomas sur le filigrane PerTh (question 4) : accepté.** Si Chatterbox monte en principal, son filigrane inaudible et non désactivable est sans conséquence pratique — MIT autorise l'usage commercial, et la traçabilité qu'il introduit va dans le sens des obligations de transparence du RIA art. 50 plutôt que contre elles.

---

## 3. ASR — sous-titres mot à mot

**Critère qui prime : l'horodatage au mot, natif.** La couverture de sous-titres visée est de 100 % (`REFERENTIEL.json` → `production.couverture_sous_titres`) et le style mot à mot suppose un timing par mot, non reconstruit.

**Principal — `nvidia/parakeet-tdt-0.6b-v3` via parakeet-mlx.**
- Poids : **~0,6 Go**. Licence : code parakeet-mlx Apache-2.0 ; **poids CC-BY-4.0 → attribution NVIDIA obligatoire en description de vidéo.** 25 langues européennes dont les quatre cibles.
- Installation : `uv add parakeet-mlx`
- Pourquoi : horodatage **natif** au mot (pas d'alignement a posteriori), sortie SRT/VTT avec `--highlight-words`, et le plus léger des candidats.
- Coût : une ligne d'attribution automatique dans chaque description (texte prêt à l'emploi dans `LICENCES.md`).

**Repli — mlx-whisper, modèle large-v3-turbo.**
- Poids : **1,62 Go**. Licence : MIT sur le code **et** sur les poids — aucune attribution due.
- Installation : `uv pip install mlx-whisper`
- Piège : `word_timestamps=True` procède par **alignement DTW**, pas par horodatage natif : précision à vérifier avant de bâtir un rendu karaoké dessus.
- Seule mesure publique trouvée : 1,0230 s contre 1,2293 s pour whisper.cpp Core ML — sur **MacBook Pro M4 24 Go**, pas sur notre machine.

**Écartés**
- **WhisperX — diarisation** → pyannote exige l'acceptation de conditions et un jeton HF ; le backend DiariZen est en CC-BY-NC-4.0. Le cœur WhisperX (BSD-2-Clause) resterait utilisable sans diarisation, mais ses modèles d'alignement wav2vec2 FR/ES/IT viennent de dépôts tiers **aux licences non vérifiées** : écarté tant que ce point n'est pas levé.
- **whisper.cpp `-ml 1`** → l'horodatage au mot y est marqué **expérimental** par le projet lui-même. Conservé comme second repli (574 Mo en q5_0), pas comme principal.

**À mesurer en 5.1**
| Incertitude | Seuil de décision |
|---|---|
| WER de parakeet-tdt-0.6b-v3 sur français, sur notre propre voix de synthèse | **Retenu si WER < 8 %** en FR |
| Justesse de l'horodatage au mot (décalage sur 100 mots) | **Retenu si décalage médian ≤ 80 ms** |
| Facteur temps réel de transcription | **Retenu si ≤ 0,3** (10 min d'audio transcrites en ≤ 3 min) |

---

## 4. Image — illustration des plans

**Critère qui prime : la cohérence de style d'un plan à l'autre**, et pour le format avatar la cohérence d'**identité** d'une vidéo à l'autre (`REFERENTIEL.json` → `variantes_style.avatar` : « même personnage/visage recyclé sur toutes les vidéos de la chaîne »). Une belle image isolée ne vaut rien si le plan suivant change de style.

**Principal — `mlx-community/FLUX.2-Klein-4B-4bit`, déjà quantifié, via mflux.**
- Poids : **4,62 Go, pesés par l'API du Hub puis mesurés sur disque**. Licence : **Apache-2.0** — `license: apache-2.0` dans `cardData`, dans les `tags` et dans le README du dépôt, **les trois vérifiés le 15/09/2026**.
- Installation : `uv tool install mflux` (**outil isolé**, pour ne pas heurter les dépendances de la pile audio), puis :
  `mflux-generate-flux2 --model mlx-community/FLUX.2-Klein-4B-4bit --width 1280 --height 720 --steps 4 --seed 42 --low-ram --vae-tiling --output plan.png`
  **Ne pas ajouter `-q 4`** : le dépôt est déjà en 4 bits. `--low-ram` et `--vae-tiling` ne sont pas optionnels — sans eux le seul décodage VAE réclame ~9,6 Go.
- **Mesuré à l'étape 5.2** : 137,0 s de médiane par 1280×720, 161,0 s en 1024×1024, pic MLX 11,15 et 12,37 Go, qualité 4,6/5 sur cinq styles.
- **Piège de licence, reformulé après vérification — la version d'origine était trop large et coûtait 20 Go pour rien.** *Certains* dépôts tiers nommés `FLUX.2-klein-4B-mflux-4bit` sont tagués **`flux-1-dev-non-commercial-license`** : ceux-là dérivent de **FLUX.1-dev** et contamineraient le catalogue. Mais `mlx-community/FLUX.2-Klein-4B-4bit` dérive du **4B officiel Apache-2.0** et porte lui-même ce tag. **La règle est de vérifier le tag du dépôt, pas d'exclure les dépôts 4-bit par principe.**
- **Aucune quantification locale n'est à faire, et il ne faut pas en refaire une.** Le dépôt officiel bf16 pèse **23,74 Go** — et non 13 à 16 comme annoncé à l'étape 4 — dont un **doublon interne de 7,75 Go** (le transformer y figure deux fois). Le télécharger pour le requantifier coûterait ~28 Go de pic, **impossible sur cette machine**, pour arriver au même résultat que les 4,62 Go déjà publiés.
- **Dépendances internes vérifiées** (c'est là que tombent la plupart des modèles d'image) : l'encodeur de texte est un `Qwen3ForCausalLM` **embarqué dans le dépôt** (dimension cachée 2560, soit Qwen3-4B, Apache-2.0) et le VAE y est également embarqué. Les deux sont couverts par le LICENSE Apache-2.0 du dépôt. Aucun encodeur CLIP ou T5 sous licence tierce n'est tiré.
- Vitesse connue : 31,7 s pour 1024², 4 étapes, sous mflux — sur **M1 Max 64 Go**, pas sur un M2 16 Go. **À mesurer.**

**Repli — SDXL 1.0 + IP-Adapter.**
- Poids : **6,94 Go** (SDXL) + 0,7 à 2 Go (IP-Adapter). Licences : CreativeML Open RAIL++-M pour SDXL, Apache-2.0 pour IP-Adapter (code et poids `h94`).
- Lecture de l'OpenRAIL++-M : « *Licensor claims no rights in the Output* » → les images produites sont commercialisables. L'annexe A énumère 11 interdictions d'usage (illégal, mineurs, désinformation, données personnelles, diffamation, discrimination, conseil médical, police/justice/immigration) : **aucune ne vise la vulgarisation YouTube**. Obligation : répercuter licence et restrictions si l'on redistribue le modèle ou un LoRA — ce que nous ne faisons pas.
- Pourquoi c'est un vrai repli et pas un sous-choix : **IP-Adapter ne fonctionne pas avec FLUX.2**, seulement avec SD1.5/SDXL. Or IP-Adapter est le mécanisme de cohérence d'identité. Si FLUX.2-klein échoue à tenir un personnage constant d'une vidéo à l'autre, SDXL + IP-Adapter devient le principal.
- **Vigilance santé** : l'annexe A interdit le conseil médical. Les niches `longevite` et `complements_fr` doivent rester descriptives ; c'est déjà la ligne de `docs/CONFORMITE.md`.

**Écartés**
- **FLUX.2-klein-9B, FLUX.1-dev, FLUX.2-dev 32B** → « FLUX Non-Commercial License ».
- **Z-Image-Turbo 6B** (Apache-2.0, pourtant éligible) → **33 Go à télécharger** avant toute quantification. Incompatible avec la règle disque de `CLAUDE.md` § 3 et avec le plancher de 8 Go. Réexaminable si le disque se libère.
- **Draw Things** → application gratuite mais **sans CGU ni EULA publiés** ; seule une politique de confidentialité existe, muette sur les sorties. Le droit d'usage commercial des images n'est **pas établi par écrit** : écarté par la règle « pas de licence claire, pas d'outil ».
- **SDXL-Turbo / SD-Turbo** → licences non commerciales.
- **ComfyUI** (GPL-3.0) → utilisable en interne sans conséquence, mais écarté comme runtime de production : il faudrait ne jamais redistribuer nos scripts liés, contrainte inutile quand mflux (MIT) fait le travail.

**À mesurer en 5.2**
| Incertitude | Seuil de décision |
|---|---|
| ~~Secondes par image 1280×720~~ | ~~**Retenu si ≤ 90 s par image 1280×720.** Au-delà → SDXL~~ → **seuil réécrit le 15/09/2026, voir ci-dessous** |
| Pic de RAM pendant la génération | **Retenu si < 13 Go** |
| **Cohérence de style sur 8 plans d'une même vidéo** (une charte, une graine par plan) | ❌ **NON TENUE — mesuré le 15/09/2026.** Sur 8 plans d'une même série, le `plan_08` change le personnage (femme aux cheveux longs → coupe courte masculine), laisse une **mèche détachée** à 17 px de la tête, et porte un **pied retourné** avec une ombre non ancrée ; le `plan_01` est le seul encadré des huit. **La métrique de palette ne voit rien de cela** et avait donné 4/5. **Aucun contrôle automatique n'est atteignable** pour l'anatomie, les éléments détachés et la dérive d'identité (§ 2.12 de `RESULTATS.md`) : il faudrait un VLM, hors budget mémoire et hors 0 €. **Conséquence : la brique impose une relecture humaine plan par plan**, contre la contrainte 3 de `ROADMAP.md` § 3.4. **Trois voies à trancher à l'étape 6**, la moins chère étant de cadrer les personnages en buste et de privilégier objets et lieux — les 4 plans sans anatomie humaine sont indemnes. |
| **Cohérence d'identité d'un personnage sur 3 vidéos** (format avatar) | ✅ **Tenu — 4/5 par Thomas le 15/09/2026.** Le visage est reconnaissable sans indication sur 3 graines ; SDXL + IP-Adapter n'est pas activé. **Réserve : la tenue dérive** (chemise unie / à carreaux selon la graine, le mot « flannel » étant ambigu). Invisible entre deux vidéos, **visible entre deux plans d'une même vidéo** → à fixer dans le gabarit de prompt du personnage, **étape 12.2** (et **29** pour la récurrence entre vidéos) |
| ~~Faisabilité de la quantification 4-bit locale depuis le bf16~~ | **Sans objet** : `mlx-community/FLUX.2-Klein-4B-4bit` est tagué Apache-2.0 et pesé à 4,62 Go. Aucune quantification locale n'a été nécessaire |

**Seuil de vitesse réécrit — tranché par Thomas le 15/09/2026, après mesure.**

> **Le seuil « ≤ 90 s par image 1280×720 » est remplacé par « ≤ 180 s ».**
> Mesuré en 5.2 : **137,0 s de médiane** (94,6 à 160,5 selon le style), pic MLX
> 11,15 Go, qualité 4,6/5. **FLUX.2-klein-4B est retenu.**

Trois raisons, et une conséquence qui engage la suite du projet.

1. **Le seuil de 90 s était une supposition, pas une contrainte.** Il venait
   d'une mesure publique sur **M1 Max 64 Go** (31,7 s en 1024², 4 étapes). Aucune
   mesure sur M2 16 Go n'existait. Un seuil hérité d'une autre puce ne décrit
   rien de cette machine.
2. **Le repli n'est pas meilleur, et n'est pas mesuré.** SDXL 1.0 pèse 6,94 Go
   contre 4,62, il n'existe aucune mesure de SDXL sur ce M2, et rien n'indique
   qu'un modèle non distillé de 2,6 Md de paramètres soit plus rapide qu'un
   modèle turbo de 4 Md en 4 bits à 4 étapes. Basculer, ce serait échanger une
   vitesse connue contre une vitesse inconnue.
3. **La qualité mesurée est au-dessus de la cible** : 4,6/5 sur les cinq styles,
   et le seul style noté 5/5 sur les trois critères est justement le
   photoréaliste. Le seuil qui prime pour cette brique n'est pas la vitesse, c'est
   la cohérence — et celle-là reste à vérifier sur 8 plans d'une même vidéo.

**Conséquence n° 1 — la génération d'images est le goulot d'étranglement du
système, et de loin.** Sur une vidéo de 10 minutes mesurée bout en bout
(≈ 3 h 55 en documentaire, ≈ 6 h 00 en motion design), **84 % du temps de calcul
part dans les images** — contre 14 % pour la voix off, 1 % pour le rendu Revideo
et moins de 1 % pour le script. Toute optimisation de débit qui ne touche pas
cette brique est du temps perdu.

**Conséquence n° 2 — c'est la première justification chiffrée du serveur GPU
(≈ 50 €/mois, déjà approuvé par Alek, `ROADMAP.md` § 3.1).** Le poste à déporter
en priorité est la génération d'images, pas le TTS ni le rendu. À chiffrer à
l'étape C2 avec ces mesures comme point de comparaison.

**Conséquence n° 3 — la réutilisation de bibliothèque (étape 12.2) doit faire
baisser ce coût, et ce n'est pas encore un fait.** Un plan déjà généré et
réutilisé coûte 0 s au lieu de 137. Le taux de réutilisation réel dépend de la
granularité de l'indexation et de la variété des scripts : **il est à mesurer à
l'étape 12.2, pas à supposer ici.** Tant qu'il ne l'est pas, le coût de référence
du système reste 137 s par plan.

---

## 5. Parallaxe 2.5D — profondeur et mouvement

**Critère qui prime : la licence, puis le poids.** C'est la brique où la veille avait raison sur le fond : hors du modèle *Small*, toute la famille Depth Anything est non commerciale.

**Principal — Depth Anything V2 Small.**
- Poids : **99,2 Mo**. Licence : **Apache-2.0**.
- Installation : `uv add transformers` puis chargement de `depth-anything/Depth-Anything-V2-Small`.
- Pourquoi : le seul modèle de la famille sous licence commerciale, et le plus léger de tous les candidats — 0,5 % du budget disque pour une brique qui tourne sur chaque image.

**Repli — DA3-BASE** (Apache-2.0, 0,12 B, ~0,5 Go), ou **MiDaS 3.1** (MIT, 21 à 345 Mo) si DA3-BASE déçoit.

**Mouvement — ffmpeg `zoompan`**, déjà installé (8.1.2, filtre vérifié présent ce jour). Suréchantillonner ×4 avant le zoom pour éviter le tremblement, comme indiqué par la veille.

**Écartés**
- **Depth Anything V2 Base / Large / Giant** → `cc-by-nc-4.0` (confirmé sur V2-Large).
- **DA3 Large / Giant / Nested any-view** → CC-BY-NC-4.0.
- **Apple Depth Pro** → « Apple ML Research Model License » : usage « *exclusively for Research Purposes* », « *excludes commercial exploitation* ». Éliminatoire malgré la qualité.
- **ZoeDepth** → dépôt archivé en 2025, dépend de poids BEiT non vérifiés.

**À mesurer en 5.2**
| Incertitude | Seuil de décision |
|---|---|
| Secondes par carte de profondeur sur MPS | **Retenu si ≤ 5 s par image** |
| Secondes par clip de parallaxe de 5 s à 1080p (profondeur + `zoompan` + encodage) | **Retenu si ≤ 20 s par clip** |
| Qualité visuelle du 2.5D (déchirures aux bords d'objets) | ✅ **Tenu — 4/5 par Thomas le 15/09/2026** (« propre, plus aucun trou, les plans sont dans le bon sens »). Repli Ken Burns plat non activé. **Trois défauts avaient dû être corrigés d'abord** : rôles des couches inversés (Depth Anything sort une profondeur inverse, clair = proche), trous dus à des masques exclusifs, contours crénelés. Détail dans `benchmarks/RESULTATS.md` § 2.4 |

---
## 6. Banques d'images et de vidéos

**Critère qui prime : la traçabilité de la licence par API.** `docs/CONFORMITE.md` § 8 impose d'enregistrer `provider`, `source_url`, `author`, `licence`, `licence_url`, `attribution_line`, `downloaded_at` **à l'acquisition**. Une banque sans API renvoyant ces champs oblige à une saisie manuelle : elle ne peut pas être principale.

> **Alerte CGU 2025-2026, commune à Pexels, Unsplash et Mixkit.** Pexels (révision du 15/11/2024, en vigueur) interdit « *Bulk, large-scale or systematic copying of Content* » et le data mining « *including without limitation for machine learning purposes* ». Unsplash interdit les jeux de données IA et les robots hors API. Mixkit (CGU du 02/10/2025) interdit les scripts de téléchargement massif.
> **Dans les trois cas, l'usage d'un média dans une vidéo YouTube monétisée reste autorisé** : c'est la **collecte automatisée** qui est visée. Conséquence de conception : le pipeline passe par les **API officielles avec pagination et cache**, jamais par un crawler — ce qui rejoint `CLAUDE.md` § 11.

**Principal — Pexels (images + vidéos).**
- Licence : Pexels License, usage commercial oui, attribution non exigée par la licence **mais imposée par les conditions de l'API** : « Photo by X on Pexels » + lien.
- Quota : **200 requêtes/h, 20 000/mois**. Clé web, **sans carte bancaire**.
- Pourquoi : c'est la seule banque qui couvre images **et** vidéos avec un quota confortable et une API qui renvoie l'auteur — donc la ligne d'attribution se compose toute seule.

**Principal complémentaire — Pixabay (images + vidéos + musique).**
- Licence : Pixabay Content License, commercial, **sans attribution**. Sans carte bancaire.
- Quota : 100 requêtes/60 s, et **mise en cache de 24 h obligatoire** (exigence de l'API, à implémenter, pas à subir).
- Piège : marques et personnes reconnaissables restent hors licence → croiser avec `person_release` (`docs/CONFORMITE.md` § 8).

**Principal complémentaire — Wikimedia Commons (images).**
- Licence : par fichier (CC0, CC-BY, CC-BY-SA, domaine public). Crédit auteur + licence + lien dû dès que c'est du BY.
- Quota : 10 req/min sans User-Agent, **200 req/min avec un User-Agent identifiant** — donc User-Agent obligatoire, comme pour Wikimedia Pageviews à l'étape 20.
- **Piège structurant : CC-BY-SA est viral.** Un fichier BY-SA impose le partage à l'identique de l'œuvre dérivée. Le pipeline doit **filtrer CC-BY-SA en amont** et ne retenir que CC0, CC-BY et domaine public.

**Replis**
- **Openverse** (20 req/min, 200/j en anonyme, sans clé) — utile pour la recherche multi-sources, mais le service « *does not verify its licensing status* » : à ne jamais utiliser sans revérifier la licence à la source.
- **NASA Image and Video Library** — domaine public américain, crédit « NASA ». **Trois restrictions à coder**, plus larges que ne le disait la veille :
  1. Le logo NASA (« meatball », « worm ») est protégé et ne peut pas figurer dans un contenu commercial.
  2. « *Astronauts or employees who are currently employed by NASA cannot have their names, likenesses or other personality traits displayed or position title used on any commercial products, advertisements, promotional material or commercial product packaging.* »
  3. **Et surtout, la restriction ne s'arrête pas aux astronautes** : « *If a NASA image […] includes an identifiable person, using the media for commercial purposes may infringe that person's right of privacy or publicity.* » Le filtre à coder porte donc sur **toute personne identifiable**, et rejoint `person_release` de `docs/CONFORMITE.md` § 8 — un filtre « pas d'astronautes » laisserait passer des visages tiers.
- **Coverr** (Coverr License, commercial sans attribution, palier Demo 50 req/h) et **Mixkit Free** pour la vidéo d'appoint.

**Écartés**
- **Internet Archive** → « *does not make guarantees as to the copyright status* ». **Décision (Thomas m'a laissé trancher) : il reste dans la liste blanche, mais sort du chemin automatique.** Retrait pur et simple aurait coûté un fonds réel (films du domaine public, archives sonores) sans contrepartie ; l'ingestion automatique aurait fait entrer des droits inconnus dans un catalogue monétisé. Le fournisseur porte donc `requires_manual_review: true` : **aucun asset Internet Archive ne descend dans le pipeline sans une vérification humaine tracée**, et le champ `licence` doit être renseigné à la main, jamais déduit de la réponse de l'API.
- **Mixkit, licence *Restricted*** → **non vérifiée, et donc traitée comme bloquante.** La page de licence charge son texte par une modale JavaScript ; le HTML servi ne rend que la navigation, la clause n'a pas pu être lue à la source. Tant qu'elle ne l'est pas, **aucun clip Mixkit ne descend dans le pipeline**, quelle que soit son étiquette.
- **Videvo** → redirection 301 vers freepik.com, page de licence en 403 : licence non consultable, donc non vérifiable.
- **Unsplash** → non retenu comme principal (images seulement, quota démo 50/h) ; utilisable si besoin, avec l'attribution imposée par l'API.

**À mesurer en 5.2** — aucun seuil de performance : la brique est un accès réseau. **Ce qui reste à vérifier est contractuel**, pas technique : quotas réels d'Openverse authentifié et d'`images.nasa.gov`, non documentés.

---

## 7. Musique et SFX

**Critère qui prime : la sécurité Content ID**, puis le poids disque. Une réclamation Content ID démonétise la vidéo : c'est un risque plus coûteux qu'une musique moins originale. `docs/CONFORMITE.md` § 7 impose déjà le téléchargement depuis le Studio de la chaîne qui publiera.

**Principal — YouTube Audio Library, téléchargée depuis le Studio de la chaîne publiante.**
- Poids disque : **0 Go de modèle**. Licence : YTAL ou CC-BY selon la piste ; la musique est annoncée « *copyright-safe… won't be claimed by a rights holder through the Content ID system* ».
- Pourquoi : c'est la seule source qui garantit l'absence de réclamation Content ID **sur YouTube**, et la seule que YouTube lui-même oppose à un litige.
- Limite déjà inscrite en conformité : l'usage **hors YouTube** n'est couvert par aucune source officielle. Ne pas réutiliser ces pistes ailleurs.
- Pas d'API : téléchargement manuel par lots, puis catalogage local avec `attribution_required` et le texte de crédit exact.

**Principal complémentaire — Pixabay Music** (Pixabay Content License, commercial, **sans attribution**, accessible par la même API que les images). Seule réserve : pas de diffusion « standalone » (on ne republie pas la piste seule).

**Repli — Incompetech (Kevin MacLeod), CC-BY 4.0.**
- Crédit exact, à insérer automatiquement, mot pour mot :
  `« Titre » Kevin MacLeod (incompetech.com) Licensed under Creative Commons: By Attribution 4.0 https://creativecommons.org/licenses/by/4.0/`
- Pas d'API : catalogage manuel.

**Repli conditionnel — ACE-Step 1.5 (génération locale).**
- Licence : **MIT sur le code *et* sur les poids**. Poids : **2,39 Go** (la variante XL ~9 Go est hors budget).
- **Conditionné au budget disque** : 2,39 Go consommeraient l'essentiel de la marge restante sous le plafond de 18 Go. À n'installer que si une brique principale tombe et libère de la place, ou si les banques s'avèrent insuffisantes pour la variété exigée par `docs/CONFORMITE.md` § 5 (anti-clonage).
- Support MLX annoncé, **aucune mesure sur Mac** : entièrement à mesurer.

**Écartés**
- **Freesound (API)** → **contradiction non résolue dans les CGU** : les sons individuels sont sous CC0/CC-BY, mais les conditions de l'**API** la déclarent « *free for non-commercial use* », l'usage commercial étant « *negotiated case by case with UPF* ». **Décision (Thomas m'a laissé trancher) : écarté du pipeline, et aucune négociation engagée maintenant.** Écrire à l'UPF coûterait un délai indéterminé pour une brique que Pixabay couvre déjà, sur un projet à 0 € où rien ne dépend de Freesound. **À rouvrir uniquement si 5.1 montre que les SFX manquent** — c'est le seul fait qui justifierait la démarche. Le téléchargement manuel de sons CC0 reste possible entre-temps.
- **Stable Audio Open Small** → Stability AI Community License : gratuité **plafonnée à 1 000 000 USD de revenus annuels**. Un plafond de revenus est éliminatoire par principe — il transforme un succès en violation de licence.
- **MusicGen** → « *model weights are released under CC-BY-NC 4.0* ».
- **YuE** → est bien passé en Apache-2.0 (la veille disait CC-BY-NC, c'est périmé), mais 7 B de paramètres : hors budget mémoire et disque.
- **Free Music Archive** → « *we unfortunately had to shut down our API* » : plus d'accès programmatique.
- **ccMixter** → majorité de pistes CC-BY-NC ; utilisable au cas par cas, pas comme source automatisée.
- **MOSS-SoundEffect v2.0** (Apache-2.0, génération de SFX) → documentation CUDA, `mps` non testé, poids non chiffrés. À revoir en 5.1 si les SFX manquent.

**À mesurer en 5.1**
| Incertitude | Seuil de décision |
|---|---|
| Variété réelle du catalogue Audio Library pour 8 niches (`docs/CONFORMITE.md` § 5 interdit la répétition) | **Retenu si ≥ 5 pistes distinctes par niche** sans réemploi à moins de 10 vidéos d'écart |
| ACE-Step 1.5 sur M2, **seulement si le disque le permet** | **Retenu si ≤ 60 s pour 30 s de musique** et pic RAM < 10 Go |

---
## 8. Composition programmatique — le moteur de rendu

**Critère qui prime : la licence.** C'est la contrainte explicite de l'étape : un moteur de composition est au cœur du pipeline, on ne peut pas en changer à moindre coût. Le second critère est le **rendu headless**, sans quoi il n'y a pas d'autonomie.

**Principal — Revideo.**
- Licence : **MIT** (fichier LICENSE lu). Aucune clause commerciale, aucun seuil, aucun territoire. Le dépôt a été renommé `redotvideo/revideo` → `midrender/revideo`.
- Poids : ~0,5 Go (Chromium embarqué). Installation : `npm init @revideo@latest`, rendu par `renderVideo()`.
- Pourquoi : **le seul moteur MIT avec un rendu headless natif et documenté.** C'est exactement le critère qui départage.
- **Deux pièges à traiter dès l'installation :**
  1. **Télémétrie PostHog activée par défaut** → poser `DISABLE_TELEMETRY=true` dans l'environnement du pipeline. Un pipeline qui téléphone à l'extérieur n'est pas acceptable ici.
  2. **Projet à risque de maintenance : 0 release publiée, dernier commit le 15/07/2026.** Deux mois de silence. À réévaluer à l'étape 30.1 ; épingler la version exacte dans `package.json`.

**Repli — MoviePy v2.2.1 (MIT) + Manim CE 0.21 (MIT) + ffmpeg.**
- Poids : ~0,1 Go + ~0,4 Go. Installation : `uv add moviepy` ; `brew install cairo pkg-config && uv add manim`.
- Partage des rôles : MoviePy assemble et compose (c'est un enrobage de ffmpeg, sans motion design) ; Manim anime textes et schémas, avec une esthétique « tableau » assumée. Ensemble ils couvrent le motion design de base, pas le niveau CasiCreativo.
- Pourquoi ce repli et pas Motion Canvas : voir ci-dessous.

**Écartés**
- **Motion Canvas** (MIT, donc licence irréprochable) → **écarté sur preuve technique : le rendu n'est documenté que via l'éditeur web.** Le rendu headless fait l'objet de l'issue #1218, **ouverte le 14/10/2025 et toujours ouverte**. Le paquet `packages/ffmpeg` existe mais reste piloté par l'éditeur. Sans rendu en ligne de commande, il n'y a pas d'autonomie : la brique entière tomberait.
- **Remotion** → **écarté, et il n'a pas à être discuté.** La contrainte de l'étape ne l'autorise que si Revideo *et* Motion Canvas tombent sur preuve technique. Revideo tient. Pour mémoire, sa licence propriétaire dit : « *You are eligible to use Remotion for free if you are: an individual / a for-profit organization with up to 3 employees / a non-profit* » ; au-delà, Company License à 25 $/siège/mois. BMS grandissant, ce seuil se refermerait — raison de plus de ne pas s'y appuyer. **Aucune mention en rouge n'est requise puisque Remotion n'est pas retenu.**
- **editly** (MIT) → dernier push 05/2025, projet dormant.
- **GSAP 3.15** → gratuit en commercial sous licence Webflow, mais **révocable** : pas de dépendance structurelle sur une licence que l'éditeur peut retirer.
- **storyboard-ai** → GPL-3.0.

**Bibliothèques d'appoint retenues** (toutes MIT, poids négligeable) : `ffmpeg-concat`, `Rive runtime`, `lottie-web`, `anime.js v4` — utilisables dans le rendu Revideo sans complication de licence.

**À mesurer en 5.2**
| Incertitude | Seuil de décision |
|---|---|
| Images par seconde du rendu Revideo à 1080p sur M2 (aucune mesure publique) | **Retenu si ≥ 2 fps** (une vidéo de 10 min rendue en ≤ 2 h 30). Sous 2 fps → MoviePy + Manim |
| Le rendu headless fonctionne-t-il hors éditeur, sur cette machine ? | **Bloquant** : échec → MoviePy + Manim montent immédiatement |
| Pic de RAM du rendu (Chromium + ffmpeg) | **Retenu si < 8 Go** |

---

## 9. Whiteboard animé

**Critère qui prime : la faisabilité.** Il n'existe aucun équivalent libre et clé en main de VideoScribe ; la question n'est pas de choisir le meilleur outil mais de vérifier qu'un chemin existe.

**Principal — vtracer → SVG → animation `stroke-dashoffset`, rendue par Revideo.**
- Licence : **MIT** (la crate Rust est `MIT OR Apache-2.0`). Poids : **~0,02 Go**.
- Installation : `uv pip install vtracer`
- Pourquoi : vectorisation **en couleur** (potrace ne fait que du bitmap noir et blanc), et le rendu réutilise le moteur de composition déjà retenu — pas de seconde chaîne d'outils à maintenir.
- Piège : le champ « licence » de la fiche PyPI est **vide** ; la licence a été lue dans le dépôt, pas sur PyPI.
- Limite technique connue : `stroke-dashoffset` anime des **tracés**. Les aplats de couleur et les formes fermées doivent être révélés autrement (masque progressif), et la main qui dessine est un PNG suivant le tracé — c'est un assemblage, pas une fonctionnalité prête.

**Repli — whiteboard-animator 0.1.1.**
- Licence : **MIT** (LICENSE vérifié, © 2026 M. Sultani). Poids : ~0,15 Go. Installation : `uv pip install whiteboard-animator`
- Pourquoi en repli et non en principal : il fait raster → MP4 avec main intégrée, ce qui est exactement le besoin, mais c'est un **projet neuf, en version 0.1.1, à auteur unique**. On ne met pas une brique de production sur cette base tant que le chemin vtracer n'a pas échoué.

**Écartés**
- **potrace** → GPL-2.0+. La sortie d'un binaire GPL n'est **pas** contaminée (GPL FAQ, « *What case is output GPL* »), donc l'usage serait licite ; il est écarté parce qu'il ne vectorise pas la couleur. **Ne jamais lier `libpotrace` ni `pypotrace`** (GPL-3, contaminant).
- **Potrace Professional** → payant.

**À mesurer en 5.2**
| Incertitude | Seuil de décision |
|---|---|
| Temps de vectorisation d'une illustration 1280×720 | **Retenu si ≤ 10 s par image** |
| Nombre de tracés produits par vtracer sur une illustration typique | **Retenu si ≤ 800 tracés** — au-delà, l'animation SVG devient injouable dans un navigateur |
| Rendu convaincant d'une séquence whiteboard de 30 s | ✅ **Tenu — 4/5 par Thomas le 15/09/2026** sur un clip de 5 s. Repli whiteboard-animator non activé. `colormode=color` reste en réserve si un tracé plus riche est demandé |

---

## 10. Avatar 2D et lip-sync

**Critère qui prime : la licence des dépendances tierces.** C'est la brique où presque tous les projets tombent — non sur leur propre licence, mais sur un détecteur de visage non commercial enfoui dans les dépendances. Le format avatar est demandé (`REFERENTIEL.json` → `variantes_style.avatar`, chaînes Elias Yoder et Daniel Moreno).

**Rappel de conformité :** un personnage 2D dessiné déclenche la mention **« Images virtuelles »** (`docs/CONFORMITE.md` § 3, couche 3 : « une illustration cartoon d'un personnage la déclenche »). Il ne déclenche **pas** `contains_synthetic_media`, qui vise le réalisme. La voix, elle, le déclenche si elle est clonée (brique 2).

**Principal — personnage 2D en calques (kit CC0/MIT) + Rhubarb Lip Sync pour les visèmes.**
- Licence Rhubarb : **MIT**, dépendances permissives, et le projet précise que « *the resulting lip sync data belongs to you alone* ». Poids : ~0,16 Go.
- Langues : le mode `-r phonetic` est décrit comme « *language-independent […] if your recordings are not in English* » → **le français est couvert**. Le mode `pocketSphinx` est anglais seul et ne sera pas utilisé.
- Kits de personnages vérifiés : **Open Peeps (CC0)**, **Humaaans (CC0)**, **Avataaars (MIT)**, **Kenney (CC0)**, **DiceBear** (code MIT, 42 styles CC0 et 14 CC-BY — vérifier style par style).
- **Piège mesuré par le sous-agent, pas supposé :** le binaire distribué de Rhubarb 1.14 est un **Mach-O x86_64 uniquement** ; son exécution s'est soldée par un **SIGSEGV**. Il n'existe pas de build arm64. Il faudra **recompiler depuis les sources (CMake)** en 5.2. C'est le risque principal de cette brique.

**Repli — Montreal Forced Aligner (MFA) + OpenFaceFX.**
- Licences : **MIT** pour les deux (LICENSE vérifiés). Modèles acoustiques MFA sous **CC-BY-4.0** → attribution due, texte prêt dans `LICENCES.md`.
- Poids : **~92 Mo par langue** (mesuré : `french_mfa.zip` 91,8 Mo, `english_mfa.zip` 92,2 Mo, dictionnaire FR 4,6 Mo), soit **~400 Mo pour FR/EN/ES/IT**. OpenFaceFX n'a **que numpy** en dépendance d'exécution.
- Installation : MFA par conda-forge (canal `osx-arm64` disponible, CPU pur) ; `uv pip install openfacefx`.
- **Pourquoi ce repli est meilleur que celui qu'il remplace :** MFA aligne les phonèmes sur le temps, OpenFaceFX en dérive les visèmes et **retargète vers le jeu Preston Blair — celui de Rhubarb**. Les sprites de bouche sont donc les mêmes : la chaîne est interchangeable sans rien redessiner, et le principal comme le repli partagent le même format de sortie.
- **Aucun modèle génératif, aucun poids non commercial** : ni InsightFace, ni GFPGAN, ni StyleGAN2, ni DFDNet, ni CodeFormer, ni Wav2Lip. C'est ce qui manquait au repli précédent.
- Bénéfice de robustesse : cette voie ne dépend pas de la recompilation arm64 de Rhubarb. Si celle-ci échoue, la brique tient quand même.

**Écartés — tous pour licence, sauf mention contraire**
- **SadTalker** → **éliminé par le contradicteur, après avoir été proposé en repli dans mon premier jet.** Sa licence propre est Apache-2.0, mais son `scripts/download_models.sh` télécharge **GFPGANv1.4.pth sans condition**, or le LICENSE de GFPGAN porte StyleGAN2 sous licence Nvidia § 3.3 — « *The Work and any derivative works thereof only may be used or intended for use non-commercially […] "non-commercially" means for research or evaluation purposes only.* » — et DFDNet sous **CC-BY-NC-SA 4.0**. **C'est exactement le motif retenu contre LivePortrait et Hallo** : je l'avais appliqué de façon inégale. S'ajoute que son propre LICENSE annonce « *except for the third-party components listed below* » **sans qu'aucune liste ne figure dans le fichier**, et que ses poids viennent des releases GitHub, non d'un dépôt Hugging Face.
- **torchaudio MMS_FA** → API BSD-2, mais **poids sous CC-BY-NC-4.0** (« *published under a CC-BY-NC 4.0 License* »).
- **allosaurus** → GPL-3.0, et son modèle est tiré des releases GitHub sans licence déclarée. **charsiu** → MIT, mais **anglais et chinois seulement**. **gentle** → MIT, mais anglais seul et poids Kaldi sans licence déclarée. **pyfoal** → MIT, mais anglais seul et checkpoint RAD-TTS de NVIDIA par défaut. **papagayo-ng** → GPL-2, figé depuis avril 2023.
- **MuseTalk 1.5 et son portage MLX** → **contradiction non levée** : le README annonce des poids « *available for any purpose, even commercially* », mais le champ de licence Hugging Face indique `creativeml-openrail-m`. La règle de l'étape est explicite — pas de licence claire, pas d'outil. S'ajoute une dépendance S3FD sans fichier LICENSE, et le portage MLX est une relabellisation MIT par un tiers sur un amont OpenRAIL. **Réexaminable si l'amont clarifie.**
- **Wav2Lip** → aucun LICENSE ; « *This repository can only be used for personal/research/non-commercial purposes* » et « *As the models are trained on the LRS2 dataset, any form of commercial use is strictly prohibited.* »
- **LivePortrait** → LICENSE l. 25-30 : « *The models of InsightFace are for non-commercial research purposes only […] you should remove and replace InsightFace's detection models* ». Les poids `KlingTeam` estampillés `mit` embarquent malgré tout `buffalo_l/det_10g.onnx`.
- **Hallo / Hallo2** → InsightFace obligatoire. **Hallo3** → CogVideoX-5B en plus, licence commerciale sur demande et plafond « *must not exceed 1 million visits per month* ».
- **Sonic** → CC-BY-NC-SA 4.0 : « *Note that our license is non-commercial.* »
- **Linly-Talker** → MIT en façade, mais agrège Wav2Lip : contaminé.
- **EchoMimic v1/v2** → Apache-2.0 mais base SD1.5 en CreativeML-OpenRAIL-M à répercuter. **EchoMimicV3** → Apache-2.0 propre (code, poids, base Wan2.1-Fun) mais **12 Go de VRAM annoncés**, jamais testé en mémoire unifiée : écarté sur la machine, pas sur la licence.
- **OpenMoji** → CC-BY-SA (partage à l'identique). **unDraw** → commercial sans attribution, mais **entraînement IA interdit** : utilisable tel quel, jamais pour affiner un modèle. **Mixamo** → royalty-free, redistribution brute interdite. **Blush** → commercial autorisé, revente interdite.

**À mesurer en 5.2**
| Incertitude | Seuil de décision |
|---|---|
| **Recompilation de Rhubarb en arm64 (CMake)** | **Non bloquant depuis le changement de repli** : si la compilation échoue, la brique bascule sur MFA + OpenFaceFX, qui produisent les mêmes visèmes |
| Qualité des visèmes en mode `phonetic` sur une voix française | **Retenu si Thomas note ≥ 3/5** la synchronisation labiale |
| Temps Rhubarb pour 60 s d'audio | **Retenu si ≤ 30 s** |
| MFA + OpenFaceFX : alignement d'une piste FR de 60 s, bout en bout (repli) | **Retenu si ≤ 60 s de traitement** et visèmes exploitables sans retouche |

---
## 11. Miniatures et détourage

**Critère qui prime : le contrôle typographique exact.** Le référentiel fixe des cibles de miniature par niche (mots de texte médians de 0 à 4, contraste WCAG ≥ 4,5, composition centre/droite) et l'étape 21 note 3 miniatures par vidéo. Sans contrôle fin du texte et des accents, ces cibles ne sont pas atteignables.

> **Point de règle tranché par Thomas le 15/09/2026 — Playwright est retenu.** `CLAUDE.md` § 11 interdit « aucune automatisation de navigateur » ; Thomas confirme que la règle ne vise pas ce cas. Rendre notre propre HTML local en PNG, sans aucune requête réseau, n'automatise aucun service tiers.
> **Portée de cet arbitrage, à ne pas élargir par commodité :** il tranche le **rendu local**. Il ne lève pas les interdictions de `docs/CONFORMITE.md` § 9 sur l'automatisation des services tiers (pas de `search.list` détourné, pas de yt-dlp, pas d'automatisation de Studio ni des banques hors API) — celles-là ne sont pas une préférence de méthode mais les Developer Policies de YouTube, sur lesquelles repose toute l'architecture de l'étape 1. Les élargir se déciderait en modifiant `CONFORMITE.md`, pas en interprétant cette ligne.

**Principal — Playwright, rendu HTML/CSS → PNG 1280×720.**
- Licence : **Apache-2.0**. Poids : **0,35 Go mesuré** (chromium-headless-shell seul).
- **Vitesse mesurée sur cette machine : 0,165 s par miniature**, lancement du navigateur 0,24 s. C'est la seule brique de l'étape dont la vitesse est déjà mesurée sur le M2 cible.
- Installation : `uv pip install playwright` puis `PLAYWRIGHT_BROWSERS_PATH=./models/playwright playwright install chromium-headless-shell` (cache redirigé sous `models/`, conformément à `CLAUDE.md` § 3).
- Pourquoi : CSS complet — donc polices, accents, ombres, dégradés, grille — et 13 fois plus rapide que l'alternative Chrome en ligne de commande (2,15 à 2,33 s mesurées).
- Piège : la révision de Chromium est épinglée par Playwright ; toute montée de version **retélécharge** le navigateur. Épingler la version dans le projet.

**Repli — satori + resvg-js.**
- Licences : **MPL-2.0** pour les deux. Poids : **0,009 Go au total** (0,006 + 0,003), soit 39 fois moins que Playwright, et **aucun navigateur**.
- Installation : `npm i satori @resvg/resvg-js` (binaire pré-compilé darwin-arm64 disponible).
- Limites qui en font un repli et non le principal : satori ne gère que **Flexbox** (pas de Grid, pas de `calc()`, pas de WOFF2) et resvg-js est **figé en 2.6.2 depuis mars 2024**.

**Polices — SIL OFL 1.1, donc commercial et redistribuable.**
- Retenues : **Anton** et **Oswald** — vérifiées pour les accents FR/ES/IT en bas-de-casse.
- **Bebas Neue est écartée** : ses minuscules sont des composites de capitales et **les accents bas-de-casse sont absents**. Sur des chaînes FR, ES et IT, c'est rédhibitoire — or c'est une des polices les plus employées du registre.

**Détourage — principal : rembg, modèle `birefnet-general` forcé.**
- Licences : rembg MIT, BiRefNet code MIT et poids tagués `mit`. Poids : **~0,9 Go**.
- Installation : `uv pip install "rembg[cpu,cli]"` puis **toujours** `rembg i -m birefnet-general …`
- **Piège de licence à coder, pas à documenter :** le modèle **par défaut** de rembg est `bria-rmbg`, dont l'usage commercial **exige un contrat payant** avec BRIA. Oublier `-m` une seule fois contamine la production. Le paramètre doit être en dur dans le module, avec un test qui échoue si le modèle résolu n'est pas celui attendu.
- **Provenance des poids à tracer :** rembg ne télécharge pas `birefnet-general` depuis le dépôt d'origine mais depuis ses **propres releases GitHub** (`danielgatis/rembg/releases/download/v0.0.0/BiRefNet-general-epoch_244.onnx`), sans fichier de licence joint. La licence MIT est bien celle de l'amont (dépôt et fiche HF de `ZhengPeng7/BiRefNet`) ; c'est la redistribution qui est opaque. **À enregistrer dans `MODELES.md` avec les deux URL**, celle d'où le fichier vient et celle qui porte la licence.
- **Repli : `u2net` ou `isnet-general-use`** (Apache-2.0 — la veille les disait académiques, c'est faux, vérifié deux fois : aucun fichier LICENSE des dépôts U-2-Net et DIS ne porte de clause non commerciale), **~176 Mo**, cinq fois plus légers.
- **Second repli : Apple Vision** via PyObjC (`VNGenerateForegroundInstanceMaskRequest`), **0 Go** — composant du système. Piège : la documentation PyObjC pour Vision est inexistante, l'appel est à écrire à la main.

**Écartés**
- **BRIA RMBG-2.0** → contrat payant pour l'usage commercial.
- **Chrome en ligne de commande** → 13× plus lent que Playwright (mesuré ici) et le processus `GoogleUpdater` retient le programme ~30 s après chaque capture.
- **cairosvg** → LGPL-3.0-or-later, et traîne une dizaine de formules Homebrew pour cairo. Écarté sur le poids et la complexité, pas sur la licence.
- **wkhtmltoimage** → projet archivé, aucun build arm64.
- **Pillow** n'est pas écarté : retenu comme utilitaire de composition (licence **MIT-CMU**, simple renommage SPDX de HPND, sans changement de droits).

**À mesurer en 5.2**
| Incertitude | Seuil de décision |
|---|---|
| Temps de rendu d'une miniature complète (fond + détourage + texte) | **Retenu si ≤ 3 s par miniature**, détourage compris |
| Temps de détourage `birefnet-general` sur CPU pour une image 1280×720 | **Retenu si ≤ 15 s** ; au-delà → `u2net`, puis Apple Vision |
| Qualité du détourage sur cheveux et contours fins | **Retenu si Thomas note ≥ 3/5** |
| Contraste WCAG mesuré des miniatures produites contre la cible du référentiel | **Retenu si ratio ≥ 4,5** sur le texte principal |

---

## 12. Montage et banc de mesure

**Critère qui prime : la mesurabilité.** Cette brique ne produit rien ; elle prouve. `CLAUDE.md` § 5 interdit d'annoncer un succès sans mesure, et l'étape 15 compare la vidéo rendue aux cibles du référentiel. Bonne nouvelle : **tout est déjà installé ou pèse presque rien, et l'essentiel est déjà mesuré sur cette machine.**

**Principal — ffmpeg 8.1.2 (Homebrew), déjà présent.**
- Licence : **GPL-3.0-or-later** — le build local est compilé `--enable-gpl --enable-version3` (vérifié ce jour sur le binaire). Il est **appelé comme binaire externe**, sans édition de liens, et le pipeline n'est pas redistribué : aucune obligation de diffusion de notre code. **Si BMS redistribuait un jour le pipeline, il faudrait repasser sur un build LGPL.**
- Filtres vérifiés présents sur le binaire local : `ebur128`, `silencedetect`, `blackdetect`, `zoompan`, `libvmaf`, `ssim`, `psnr`. Encodeurs : `h264_videotoolbox` (accélération Metal) et `libx264`.
- **Vitesse mesurée ici : `ebur128` tourne à 40× le temps réel** (1,24 s pour 60 s de 1080p).
- Commandes retenues, options vérifiées sur le binaire local :
  - Loudness et true peak : `-af ebur128=peak=true:framelog=quiet -f null -` → lignes « I: … LUFS » et « True peak: Peak: … dBFS ». Cibles : **−14 LUFS ± 1** et **−1 dBTP** (`REFERENTIEL.json` → `production`).
  - Silences : `silencedetect=noise=-50dB:d=0.5`
  - Trous noirs : `blackdetect=d=0.1:pic_th=0.98:pix_th=0.10`
  - Qualité : `libvmaf=n_threads=8:model=path\=…/vmaf_v0.6.1.json` (échapper le `=`)

**Outils du banc, tous à licence permissive et poids négligeable**

| Outil | Licence | Poids | Rôle | Mesure faite ici |
|---|---|---|---|---|
| **PySceneDetect** | BSD-3-Clause | 0,046 Go (opencv arm64) | rythme de coupe, contre `cible_montage` du référentiel | **759 images/s** |
| **libvmaf** | BSD-2-Clause-Patent | modèles 5,7 Mo, déjà compilés | qualité perçue du rendu | **2,14× le temps réel** (28 s pour 60 s de 1080p) |
| **imagehash** | BSD-2-Clause | 0,03 Go (tire scipy) | détection de plans répétés (anti-clonage, `docs/CONFORMITE.md` § 5) | non mesuré |
| **jiwer 4.0** | Apache-2.0 | 0,0001 Go | WER pour les seuils TTS et ASR de 5.1 | non mesuré — ⚠️ API changée en v4 |
| **tesseract** | Apache-2.0 | **0,0102 Go** (`tessdata_fast` fra+eng+spa+ita) | vérification du texte incrusté (bandeau « Publicité », mention « Images virtuelles ») | non mesuré |

- Installation : `uv pip install scenedetect ImageHash jiwer` ; `brew install tesseract` **sans** `tesseract-lang` (qui tirerait toutes les langues) — poser les 4 fichiers `tessdata_fast` à la main.

**Montage final** — assemblage par **ffmpeg** piloté depuis Python, avec **MoviePy v2** (MIT) en enrobage quand la logique devient trop verbeuse. Pas de nouvel outil : le moteur de composition (brique 8) produit les segments, ffmpeg les concatène et encode.

**À mesurer en 5.1 / 5.2**
| Incertitude | Seuil de décision |
|---|---|
| Temps d'encodage final d'une vidéo de 10 min en 1080p, `h264_videotoolbox` | **Retenu si ≤ 5 min** ; au-delà, basculer sur `libx264` en preset rapide et remesurer |
| Écart de qualité VMAF entre `h264_videotoolbox` et `libx264` | **VideoToolbox retenu si VMAF ≥ 90** contre la source |
| Vitesse de `tesseract`, `imagehash`, `jiwer` | Aucun seuil : ces outils tournent hors du chemin critique |

---
## Budget disque des principaux

Poids **retenus après purge**, c'est-à-dire ce qui reste sur le disque en régime permanent. Les poids marqués « mesuré » l'ont été sur cette machine ce jour ; les autres viennent de la fiche du modèle et seront repesés (`du -sh`) à l'installation, comme l'impose `outils/MODELES.md`.

| Brique | Outil / modèle principal | Go |
|---|---|---|
| 1. LLM | Qwen3.5-9B Q4_K_M | 6,17 |
| 2. TTS | Qwen3-TTS-12Hz-1.7B-CustomVoice | 2,00 |
| 3. ASR | nvidia/parakeet-tdt-0.6b-v3 | 0,60 |
| 4. Image | `mlx-community/FLUX.2-Klein-4B-4bit` (déjà quantifié) | 4,62 (mesuré) |
| 5. Parallaxe | Depth Anything V2 Small | 0,10 |
| 6. Banques vidéo/image | Pexels, Pixabay, Wikimedia (API) | **0,00** |
| 7. Musique / SFX | YouTube Audio Library + Pixabay Music | **0,00** |
| 8. Composition | Revideo (+ Chromium embarqué) | 0,50 |
| 9. Whiteboard | vtracer | 0,02 |
| 10. Avatar 2D | Rhubarb arm64 + kit 2D CC0 | 0,16 |
| 11a. Miniatures | Playwright chromium-headless-shell | **0,35 (mesuré)** |
| 11b. Détourage | rembg + birefnet-general | 0,90 |
| 12. Banc | PySceneDetect, tesseract *fast* ×4, imagehash, jiwer | 0,17 |
| — | Runtimes et dépendances (llama.cpp, mflux, paquets Python) | 1,50 (estimé) |
| | **TOTAL** | **16,47 Go** |

**16,47 Go ≤ 18 Go : le plafond de `CLAUDE.md` § 3 est tenu, avec 1,53 Go de marge.**

Trois avertissements que ce total ne montre pas :

1. ~~**Pic transitoire de ~20 Go pendant la quantification de FLUX.2-klein-4B.**~~ **Caduc au 15/09/2026 : il n'y a pas de quantification à faire.** Le dépôt `mlx-community/FLUX.2-Klein-4B-4bit` est publié en 4 bits, sous Apache-2.0, et pèse 4,62 Go. Aucun pic. *La route bf16 aurait coûté 23,74 Go de téléchargement et ~28 Go de pic — au-delà de ce que la machine peut faire.*
2. **La marge de 1,53 Go interdit la génération musicale locale.** ACE-Step 1.5 (2,39 Go) ne rentre pas. C'est la raison — et non une préférence — pour laquelle la brique 7 repose sur les banques. Si le LLM bascule sur Gemma 4 E4B (−1,19 Go) ou Qwen3.5-4B (−3,47 Go), la question se rouvre.
3. **Le LLM pèse 37 % du budget.** C'est le premier poste à revoir si un dépassement survient.

---

## Ordre de mesure

L'ordre suit une règle : **mesurer d'abord ce dont le reste dépend, et ce qui peut faire tomber une brique entière.** Un seul modèle résident à la fois (`CLAUDE.md` § 4), un seul téléchargement à la fois.

### Étape 5.1 — texte et audio

| # | Quoi | Pourquoi dans cet ordre | Seuil bloquant |
|---|---|---|---|
| 1 | **ASR parakeet-tdt-0.6b-v3** (0,6 Go) | Le plus léger, et il sert d'**instrument de mesure** pour le TTS : sans lui, pas de WER sur la voix | WER FR < 8 % |
| 2 | **TTS Qwen3-TTS** (2,0 Go) | Dépend de l'ASR pour être noté ; c'est la brique la plus incertaine de l'étape | Note FR de Thomas ≥ 3,5/5 · facteur temps réel ≤ 1,0 |
| 3 | **LLM Qwen3.5-9B** (6,17 Go) | Le plus lourd, mesuré en dernier pour que le disque reste libre tant que les deux premiers ne sont pas tranchés | ≥ 8 tok/s · pic RAM < 12 Go |
| 4 | **Musique** — inventaire de l'Audio Library, sans téléchargement de modèle | Coût disque nul, peut se faire pendant les autres mesures | ≥ 5 pistes distinctes par niche |
| 5 | ACE-Step 1.5 — **seulement si** une brique précédente a libéré ≥ 2,4 Go | Conditionnel par construction | ≤ 60 s pour 30 s de musique |

**Purge en fin de 5.1** : tout modèle qui n'a pas passé son seuil, avant de clore la session.

### Étape 5.2 — image, parallaxe, composition, avatar, miniatures

| # | Quoi | Pourquoi dans cet ordre | Seuil bloquant |
|---|---|---|---|
| 1 | **Miniatures — Playwright** (0,35 Go) | **Déjà mesuré à 0,165 s/miniature** : il ne reste qu'à valider la chaîne complète avec détourage et polices. Résultat acquis rapidement | ≤ 3 s par miniature complète |
| 2 | **Détourage rembg `birefnet-general`** (0,9 Go) | Nécessaire à la miniature ; vérifier au passage que le modèle résolu n'est **jamais** `bria-rmbg` | ≤ 15 s par image |
| 3 | **Whiteboard vtracer** (0,02 Go) | Poids négligeable, verdict rapide, et informe l'étape 6 sur un style entier | ≤ 10 s et ≤ 800 tracés par image |
| 4 | **Composition Revideo** (0,5 Go) | **Le rendu headless est un test bloquant** : s'il échoue, la brique 8 change de principal et tout le pipeline de rendu est à repenser. À lever tôt | rendu headless fonctionnel · ≥ 2 fps à 1080p |
| 5 | **Avatar — recompilation de Rhubarb en arm64** | Test bloquant connu (SIGSEGV mesuré sur le binaire x86_64). Ne coûte pas de disque, seulement du temps de compilation | compilation réussie · ≤ 30 s pour 60 s d'audio |
| 6 | **Parallaxe — Depth Anything V2 Small** (0,1 Go) | Léger, et prépare la mesure d'image qui suit | ≤ 5 s par carte · ≤ 20 s par clip |
| 7 | **Image — FLUX.2-klein-4B** (4,62 Go, dépôt déjà 4-bit) | **En dernier**, parce que c'est le plus gros téléchargement de l'étape. *Le pic de ~20 Go annoncé ici n'a pas eu lieu : la route bf16 a été abandonnée.* | ~~≤ 90 s~~ **≤ 180 s** par image 1280×720 (réécrit le 15/09/2026) · cohérence de style ≥ 4/5 |
| 8 | Preuve vidéo IA générative — **seulement si ≥ 18 Go libres** après le reste | Conditionnelle, et destinée à l'argumentaire de l'étape 6, pas à la production | aucune : la mesure sert à documenter l'échec attendu |

**Purge en fin de 5.2** : ~~le bf16 de FLUX~~ (jamais téléchargé), puis Revideo et Chromium (réinstallés à l'étape 30.1), puis tout modèle recalé. **Fait** : 14,90 Go téléchargés puis purgés, dont 9,53 pour l'encodeur de texte de la preuve vidéo.

---

## Décisions de Thomas — 15/09/2026

Les cinq questions ouvertes de cette étape sont tranchées. Deux par Thomas, trois déléguées à la session.

| # | Question | Décision | Effet |
|---|---|---|---|
| 1 | Origine des échantillons de voix pour le clonage | **Thomas : aucun enregistrement pour l'instant** | **Pas de clonage.** Voix préréglées seules ; « ≥ 2 voix par langue » se joue sur le mode *cross-lingual*, mesuré en 5.1. `contains_synthetic_media` **reste `false`** pour la voix, et le champ `voice_release` n'est pas créé. Si l'accent échoue, l'arbitrage remonte à **Alek** |
| 2 | Playwright contre « aucune automatisation de navigateur » | **Thomas : retenu, il est souple sur ce point** | Playwright confirmé pour le rendu **local**. **L'arbitrage ne s'étend pas** aux interdictions de `CONFORMITE.md` § 9 sur les services tiers, qui sont des Developer Policies, pas une préférence |
| 3 | Internet Archive dans la liste blanche | **Délégué → maintenu, mais hors chemin automatique** | `requires_manual_review: true` : vérification humaine tracée et `licence` saisie à la main pour chaque asset. Garde le fonds sans faire entrer de droits inconnus |
| 4 | Filigrane PerTh de Chatterbox | **Thomas : sans importance → accepté** | Aucune action. Inaudible, MIT, et va dans le sens du RIA art. 50 |
| 5 | Freesound : négocier avec l'UPF ? | **Délégué → écarté, sans négociation** | Pixabay couvre les SFX ; rien ne dépend de Freesound. **À rouvrir seulement si 5.1 montre un manque** |

**Aucune question de l'étape 4 ne reste ouverte.** Les questions encore en attente dans `SUIVI.md` § 1 viennent des étapes 1 à 3 et relèvent d'Alek.

---

## Objections du contradicteur et leur traitement

Un sous-agent contradicteur (vague 2) a ouvert le fichier LICENSE réel ou la fiche modèle de chacun des outils retenus, principal et repli, avec pour consigne de **chercher l'erreur**. Sept points lui étaient désignés comme prioritaires parce qu'ils portaient les affirmations les plus fortes de mon brouillon.

**Résultat : 3 erreurs bloquantes, 4 corrections, 6 confirmations sur les 7 points prioritaires.**

| # | Objection | Gravité | Traitement |
|---|---|---|---|
| 1 | **SadTalker** (repli avatar) est condamné non par sa licence propre mais par son installeur : `scripts/download_models.sh` télécharge GFPGAN, dont le LICENSE porte StyleGAN2 en licence Nvidia non commerciale et DFDNet en CC-BY-NC-SA 4.0. **« C'est exactement le motif qui a fait éliminer LivePortrait et Hallo — appliqué de façon inégale. »** | **bloquant** | **Accepté sans réserve. L'objection est juste et la critique de méthode aussi.** SadTalker sort. Une recherche ciblée a produit un repli plus propre : **MFA + OpenFaceFX**, MIT tous les deux, sans aucun poids génératif, et qui rendent les **mêmes visèmes Preston Blair que Rhubarb** — donc sprites interchangeables. Le repli est meilleur qu'avant l'objection |
| 2 | **Kokoro-82M** tire `phonemizer-fork` et espeak-ng, tous deux **GPL-3.0**, chargés **en processus** et non en binaire externe comme ffmpeg. Omis des deux livrables | **bloquant** | **Corrigé, mais pas par une élimination.** La GPL **autorise** l'usage commercial : elle n'est pas éliminatoire au sens de `CLAUDE.md` § 11. Ses obligations naissent à la **distribution**, que BMS ne prévoit pas. Kokoro reste en troisième repli anglophone, avec la chaîne GPL écrite noir sur blanc et la condition explicite : **il sort si le pipeline devient redistribuable** |
| 3 | **NASA** : la restriction ne vise pas « les photographies d'astronautes » mais **toute personne identifiable** — « *If a NASA image […] includes an identifiable person, using the media for commercial purposes may infringe that person's right of privacy or publicity.* » Le filtre décrit laisserait passer des visages tiers | **bloquant** | **Corrigé.** La règle est réécrite en trois restrictions et rebranchée sur `person_release` (`docs/CONFORMITE.md` § 8), qui est le champ qui existe déjà pour ça |
| 4 | **Mixkit** : la clause citée dans mon brouillon **n'est pas lisible à la source** — la page charge son texte par une modale JavaScript | sérieux | **Corrigé, et durci.** Je citais une clause que je ne pouvais pas produire. Mixkit passe de « vérifier clip par clip » à **bloqué jusqu'à lecture effective** |
| 5 | **rembg** ne tire pas `birefnet-general` de l'amont mais de **ses propres releases GitHub**, sans licence jointe | sérieux | **Corrigé.** La licence MIT de l'amont est confirmée ; c'est la redistribution qui est opaque. Les **deux** URL sont désormais exigées dans `MODELES.md` |
| 6 | **SadTalker** : ses poids viennent des releases GitHub et non d'un dépôt HF, et son LICENSE annonce un carve-out « *except for the third-party components listed below* » **sans qu'aucune liste n'existe dans le fichier** | sérieux | **Corrigé** — inscrit au motif d'élimination |
| 7 | **FLUX.2-klein-4B** : confirmé Apache-2.0, « *Open weights available for commercial use under the Apache 2.0 license.* » L'encodeur de texte est un `Qwen3ForCausalLM` **embarqué**, le VAE aussi, tous deux couverts par le même LICENSE | confirmation | **Documenté.** C'était le point le plus risqué de l'étape : aucun CLIP ni T5 tiers n'est tiré |
| 8 | **Gemma 4 E4B** : confirmé Apache-2.0 intégral, aucune Prohibited Use Policy, **aucune clause UE** | confirmation | Acquis |
| 9 | **U-2-Net** : Apache-2.0 non modifié. « La correction de la veille est juste » | confirmation | Acquis — la veille du 13/09 se trompait en les disant académiques |
| 10 | **Revideo** : LICENSE **identique octet pour octet** entre `midrender/revideo` et `redotvideo/revideo`, MIT ; rendu headless documenté ; **aucun cloud ni clé** | confirmation | Acquis — c'est ce qui autorise à écarter Remotion |
| 11 | **BiRefNet** : le « non-commercial » du README ne vise que `briaai/RMBG-2.0`, pas BiRefNet | confirmation | Acquis |
| 12 | **rembg** : le défaut `bria-rmbg` est confirmé dans le code (`bg.py:324`) — « le piège décrit est réel » | confirmation | Acquis, et transformé en test automatique |

**Ce que cette vague change dans la méthode, au-delà des lignes corrigées :** deux des trois erreurs bloquantes viennent de la même faute — avoir lu la licence que le dépôt **déclare** au lieu de regarder ce que son installeur **télécharge**. C'est inscrit comme avertissement n° 5 de `outils/MODELES.md`, pour tout outil ajouté après cette étape.
