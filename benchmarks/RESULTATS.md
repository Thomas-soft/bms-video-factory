# RESULTATS.md — mesures sur la machine cible

Machine : MacBook Air M2, 8 cœurs, 16 Go de RAM unifiée, macOS 27.0, Metal/MPS.
Protocole, conventions et écarts assumés : `benchmarks/METHODE.md`.
Mesures brutes : `benchmarks/results_audio.jsonl`.

---

## 1. Texte et audio (étape 5.1, 15/09/2026)

### Tableau

| Outil | Brique | Modèle | Temps | RTF ou tok/s | Pic mémoire | Disque | WER | Qualité /5 | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| llama.cpp | LLM | `bartowski/Qwen_Qwen3.5-9B-GGUF:Q4_K_M` | 79,1 s FR · 77,1 s EN | **14,4 tok/s** FR · 14,0 EN | 6,96 Go | 6,6 Go | — | non évaluée | **go** |
| qwen-tts | TTS | `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` | 151 à 221 s pour 46 à 62 s d'audio | **RTF 3,29 à 3,57** | 4,65 Go | 4,86 Go | 1,8 à 4,4 % (voix Serena) | non chiffrée — « plutôt bonnes » (Thomas, 15/09) | **retenu par assouplissement assumé** : échoue le seuil de vitesse, mais aucun repli n'est disponible |
| parakeet-mlx | ASR | `mlx-community/parakeet-tdt-0.6b-v3` | 1,3 à 4,3 s par fichier | **RTF 0,037** (médiane) | 0,84 Go | 2,3 Go | **3,39 %** (médiane, hors nombres) | s.o. | **go sous réserve** — tronque 2 fichiers sur 8 |
| mlx-whisper | ASR (repli) | `mlx-community/whisper-large-v3-turbo` | 6 à 27 s par fichier | RTF 0,388 (médiane) | 1,92 Go | 1,5 Go | 2,37 % (médiane, hors nombres) | s.o. | **repli utile** — hors seuil de vitesse (0,388 > 0,3) |
| — | Musique | ACE-Step 1.5 | — | — | — | ~10,1 Go | — | — | **non mesuré : disque** |
| — | Musique | YouTube Audio Library | — | — | — | 0 Go | — | — | **non mesurable** : exige un compte de chaîne |

Replis non téléchargés : **Gemma 4 E4B** et **Qwen3.5-4B** (le LLM principal passe
son seuil) · **Chatterbox** (n'est pas un repli utilisable — zero-shot, il exige un
échantillon de clonage exclu le 15/09) · **Kokoro** (seul repli réel, non déclenché :
il ne coûterait pas moins qu'il ne fait perdre — voir § 1.2).

### 1.1 LLM — **go**, sans réserve

| | Mesure |
|---|---|
| Modèle | `bartowski/Qwen_Qwen3.5-9B-GGUF:Q4_K_M` (Apache-2.0) |
| Runtime | llama.cpp 0.4.1 (Homebrew), Metal |
| Génération | **14,4 tok/s** en français · **14,0 tok/s** en anglais |
| Traitement du prompt | 81,5 tok/s (FR) · 79,2 tok/s (EN) |
| Temps total | 79,1 s (FR, 691 mots utiles) · 77,1 s (EN, 793 mots) |
| Pic mémoire | **6,96 Go** |
| Disque | **6,6 Go** (annoncé 6,17) |

**Les deux seuils bloquants de `SELECTION.md` § 1 sont franchis** : ≥ 8 tok/s (14,4
mesurés, 80 % de marge) et pic RAM < 12 Go (6,96 mesurés, 42 % sous le plafond).
**Conséquence directe : le repli Gemma 4 E4B n'a pas été téléchargé** — 4,98 Go
économisés sur le budget disque, et une brique de moins à maintenir.

Le contexte de 8 192 tokens tient sans difficulté ; le pic de 6,96 Go laisse ~9 Go au
système et à ffmpeg, ce qui valide la règle « un seul modèle résident » plutôt que de
la contredire : le LLM seul consomme déjà 44 % de la mémoire de la machine.

**Qualité du français — à relire, pas à jeter.** Le script produit est en français
natif, sans calque anglais, et la structure demandée est respectée (hook de deux
phrases, minutage, sections). Il contient en revanche de **vraies fautes d'accord et
de lexique** : « L'EFFONDRE » pour « l'effondrement », « l'appétit […] disparaît
souvent d'elles-mêmes », « se détoxiner », « pic d'insuline constante ». Aucune n'est
un anglicisme — ce sont des fautes de français. Le critère de `SELECTION.md` § 1
(« aucun calque anglais ») est tenu ; la relecture humaine de `docs/CONFORMITE.md`
§ 4 reste indispensable et ne se limitera pas à valider le fond.
**Note /5 : non évaluée** — elle revient à Thomas, sur les trois niches prévues.

Longueur : 691 mots pour 600 demandés (+15 %). À 134,9 mots/minute (médiane
`science_pop` de `REFERENTIEL.json`), cela fait 5 min 7 s de narration.
Le respect de `mots_par_minute` à ± 10 % se vérifiera à l'étape qui dimensionne les
scripts, pas ici.

### 1.2 TTS — **échoue le seuil de vitesse, et conservé quand même**

Modèle : `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` (Apache-2.0) + son tokenizer audio
`Qwen3-TTS-Tokenizer-12Hz` (Apache-2.0). Configuration : **float16 / MPS**,
`attn_implementation="eager"`. Sortie : 24 kHz, mono, PCM 16.

| Langue | Voix | Calcul | Audio | **RTF** | Mots/min | LUFS | Crête | Silences > 1,5 s |
|---|---|---|---|---|---|---|---|---|
| FR | Ryan | 178,7 s | 52,96 s | **3,373** | 142,7 | -27,3 | -8,0 | 0 |
| FR | Serena | 180,3 s | 53,28 s | **3,385** | 141,9 | -26,4 | -8,0 | 0 |
| EN | Ryan | 151,3 s | 45,92 s | **3,295** | 143,7 | -21,8 | -2,4 | 0 |
| EN | Serena | 150,8 s | 45,84 s | **3,289** | 144,0 | -24,8 | -6,3 | 0 |
| ES | Ryan | 220,9 s | 61,92 s | **3,568** | 117,2 | -27,5 | -6,5 | 0 |
| ES | Serena | 212,2 s | 60,88 s | **3,485** | 119,3 | -27,3 | -7,6 | 0 |
| IT | Ryan | 183,5 s | 55,12 s | **3,329** | 138,2 | -24,1 | -3,4 | 0 |
| IT | Serena | 193,0 s | 58,40 s | **3,304** | 130,5 | -28,7 | -7,4 | 0 |

Pic mémoire : **4,65 Go** (maximum sur les huit runs, 4,13 au minimum).
Disque : **4,86 Go** (4,2 de modèle + 0,66 de tokenizer).

**Le seuil de `SELECTION.md` § 2 est ≤ 1,0. La meilleure valeur mesurée est 3,289.**
Aucune configuration ne s'en approche : la sonde a testé float16/MPS (4,73),
bfloat16/MPS (5,05) et float32/CPU (5,94) sur une phrase courte ; sur les textes
complets, où le chargement du modèle s'amortit, le facteur se stabilise entre 3,29 et
3,57. **L'écart au seuil est d'un facteur 3,3, pas de quelques pour cent.**

Concrètement : **une vidéo de 10 minutes demande ~33 minutes de calcul pour la seule
voix off**, sur une machine qui ne peut rien faire d'autre pendant ce temps
(`CLAUDE.md` § 4). À 2 vidéos/chaîne/semaine, cela reste tenable pour quelques
chaînes et devient le goulot d'étranglement du portefeuille bien avant les 70 chaînes
du registre.

**Ce que les chiffres disent, et ne disent pas.** Les huit fichiers contiennent de la
parole continue : aucun silence de plus de 1,5 s, crêtes entre -2,4 et -8,0 dBFS,
débits de 117 à 144 mots/minute — cohérents avec la médiane `science_pop` de 134,9.
Ce n'est donc pas une génération ratée, c'est une génération lente. Le niveau
intégré, de -21,8 à -28,7 LUFS, est loin de la cible YouTube de -14 : c'est une
normalisation de rendu (`ffmpeg loudnorm`), pas un défaut.

Un motif mérite d'être signalé à l'écoute, sans que la session puisse l'interpréter :
**l'anglais — seule langue native d'un des deux locuteurs — est à la fois le plus
rapide (143,7 et 144,0 mots/min) et le plus fort (-21,8 LUFS), tandis que l'espagnol
est le plus lent (117,2) et parmi les plus faibles (-27,5).** Une synthèse moins
assurée hors langue native produirait exactement cette signature. **C'est une
hypothèse, pas une conclusion** — et elle **reste ouverte** : l'écoute du 15/09 a
porté un jugement global (« plutôt bonnes »), sans départager les langues entre
elles. À reprendre si la qualité par langue devient un sujet.

#### Écoute de Thomas, 15/09/2026

**Verdict : « les voix sont plutôt bonnes ».** Pas de note chiffrée par voix — la
grille de `benchmarks/ECOUTE.md` n'a pas été remplie ligne à ligne, et rien ici ne
prétend le contraire. Ce qui est acquis : **la voix française n'est pas
disqualifiante**, donc le scénario « note < 3,5 » de `SELECTION.md` § 2 — celui qui
aurait fait remonter un arbitrage produit à Alek — **ne s'est pas réalisé**.

Remarque de Thomas, qui déplace le sujet : *« de toute façon je pense que si on part
sur un serveur loué avec une grosse carte graphique on pourra faire des voix plus
réalistes »*. C'est cohérent avec le budget déjà acté (`ROADMAP.md` § 3.1 : serveur
GPU ~50 €/mois à partir de ~90 % du projet). **Conséquence : la qualité de voix
atteignable en local n'est pas le plafond du projet**, et l'effort d'optimisation du
TTS local ne mérite pas d'être poussé au-delà de ce qui rend la phase 1 possible.

#### Le seuil de vitesse reste manqué, et le dire est le sujet

**Même noté 5/5, le facteur temps réel de 3,29 est un échec de seuil.** `SELECTION.md`
§ 2 fixe ≤ 1,0. Une bonne note ne rend pas le chiffre conforme : elle change ce qu'on
accepte de payer pour lui.

**Si Qwen3-TTS est conservé, c'est un assouplissement assumé, pas un seuil tenu.** La
raison, écrite pour qu'elle puisse être contestée plus tard : **le repli coûte plus
cher que le dépassement.** Le détail de ce calcul est au paragraphe suivant.

#### Il n'y a pas de repli disponible — c'est le fait décisif

`SELECTION.md` § 2 désignait **Chatterbox Multilingual** comme repli. **Ce repli
n'existe pas en pratique** : Chatterbox est un modèle *zero-shot*, sans aucune voix
préréglée. Toute voix y vient d'un échantillon de référence fourni — c'est-à-dire du
**clonage**, que Thomas a exclu le 15/09/2026 (`STATE.md` § Décisions). Un repli qui
exige précisément ce qui a été écarté n'est pas un repli.

**Le seul repli réel est Kokoro-82M**, et son coût est connu d'avance :
**une seule voix française, notée B-** par le projet lui-même, contre les deux timbres
cross-lingual de Qwen3-TTS. Il fait donc tomber l'exigence « ≥ 2 voix par langue »
sur le français, l'espagnol et l'italien — l'exigence que le TTS était censé servir.
S'y ajoutent ses dépendances GPL-3.0 (`misaki` → `phonemizer-fork` → espeak-ng),
utilisables tant que le pipeline n'est pas redistribué, mais qui ne s'améliorent pas
avec le temps.

**Le choix réel n'est donc pas « rapide contre lent », c'est « lent avec deux voix »
contre « rapide avec une voix notée B- ».** À ~33 min de calcul par vidéo de 10 min,
la lenteur est une contrainte de cadence — elle se règle en étalant la production ou,
plus tard, sur le serveur GPU déjà budgété. La voix unique en B-, elle, se voit dans
chaque vidéo publiée et ne se règle pas.

**Recommandation : conserver Qwen3-TTS, en inscrivant l'assouplissement du seuil.**
Le seuil ≤ 1,0 de `SELECTION.md` doit être réécrit en connaissance de cause plutôt
que contourné en silence — soit relevé avec sa justification, soit remplacé par une
contrainte de débit à l'échelle du portefeuille (étape 24), qui est la question que
ce chiffre pose vraiment.

**Ce que cela n'autorise pas.** L'assouplissement porte sur la vitesse, mesurée, et
sur elle seule. Il ne vaut pas quitus sur la qualité : sept locuteurs sur neuf n'ont
pas été essayés, et la distinguabilité des deux timbres par langue — second seuil de
`SELECTION.md` § 2 — **reste non vérifiée**.

**Qualité /5 : non chiffrée** (jugement global de Thomas : « plutôt bonnes »).
Grille toujours disponible dans `benchmarks/ECOUTE.md`. C'est le
seuil qui décide entre garder Qwen3-TTS malgré sa lenteur et basculer sur Chatterbox.

### 1.3 ASR — **go sous réserve**, et une correction de méthode qui change tout

#### Le WER brut mesure autant les conventions d'écriture que la reconnaissance

Les ASR écrivent « 30 jours », « 16 heures », « 4 kg » ; le texte source écrit
« trente jours », « seize heures », « quatre kilos ». **Ce n'est pas une erreur de
reconnaissance, c'est une convention typographique.** Sur un paragraphe de 126 mots
qui en contient huit, cela crée à lui seul un WER de 5 à 6 % — assez pour déclencher
la « alerte WER > 8 % » sur une voix parfaitement intelligible.

Chaque ligne porte donc **deux** chiffres : le WER brut et le **WER hors nombres**,
qui retire chiffres et nombres en toutes lettres des deux côtés. C'est le second qui
doit être lu comme une mesure de reconnaissance. La fonction est dans
`bench_audio.py:sans_nombres`.

#### Mesures

| Fichier | parakeet WER / hors nb / couverture | whisper WER / hors nb / couverture |
|---|---|---|
| fr Ryan | 36,51 / **33,33** / **0,659** | 23,02 / **18,42** / **1,151** |
| fr Serena | 7,14 / 4,39 / 0,976 | 5,56 / 0,88 / 0,984 |
| en Ryan | 8,04 / 1,96 / 0,991 | 7,14 / 0,98 / 0,991 |
| en Serena | 8,04 / 1,96 / 0,991 | 8,93 / 2,94 / 0,991 |
| es Ryan | 53,72 / **49,55** / **0,620** | 5,79 / 1,80 / 0,983 |
| es Serena | 4,96 / 1,80 / 0,983 | 5,79 / 1,80 / 0,983 |
| it Ryan | 7,87 / 4,24 / 0,984 | 7,09 / 3,39 / 0,984 |
| it Serena | 6,30 / 2,54 / 0,984 | 6,30 / 3,39 / 1,000 |

| | parakeet-tdt-0.6b-v3 | mlx-whisper large-v3-turbo |
|---|---|---|
| Facteur temps réel (médiane) | **0,037** (0,028 à 0,053) | **0,388** (0,112 à 0,503) |
| WER hors nombres (médiane) | 3,39 % | 2,37 % |
| Horodatage au mot | **natif**, croissant, 866 mots | par alignement DTW, 998 mots |
| Pic mémoire | **0,84 Go** | 1,92 Go |
| Disque | 2,3 Go | 1,5 Go |

#### Ce que ces chiffres disent vraiment — et ce qu'ils ne disent pas

**Le WER ne mesure pas la qualité de la voix, contrairement à ce que l'étape
supposait.** Les deux pires valeurs — fr Ryan à 36,51 % et es Ryan à 53,72 % — ne
viennent pas de la voix. Vérification faite : l'audio de `qwen3tts_fr_Ryan.wav` est
**complet et correct**. Ses onze dernières secondes, extraites et transcrites seules,
donnent exactement le texte attendu (« …la balance affichait 4 kilos de moins et son
taux de triglycérides avait chuté de 20 % »). Ce sont les **ASR** qui décrochent, et
chacun à sa manière :

- **parakeet tronque** : couverture 0,659 sur fr Ryan et 0,620 sur es Ryan, soit un
  tiers du contenu perdu. Reproductible à l'identique sur deux exécutions.
- **whisper hallucine** : couverture 1,151 sur le même fichier, où il répète une
  phrase puis ajoute un mot inventé (« GREG ») — le mode d'échec classique de Whisper
  en fin de fichier.

**Conséquence de méthode, à retenir pour les étapes suivantes : le WER ne peut pas
servir de note d'intelligibilité de la voix.** Il mesure la rencontre entre une voix
et un ASR, et il décroche précisément là où on voudrait qu'il tranche. La qualité de
la voix reste entièrement à l'oreille de Thomas.

#### La troncature de parakeet : cause trouvée, remède non stabilisé

`parakeet_mlx.transcribe` accepte `chunk_duration` et `overlap_duration`. Sans
découpage, le modèle abandonne sur deux fichiers ; avec découpage, il les récupère —
mais en casse d'autres. Six configurations mesurées :

| Réglage | fr Ryan | es Ryan | fr Serena | it Serena |
|---|---|---|---|---|
| aucun découpage | 33,33 | 49,55 | **4,39** | 2,54 |
| chunk 20 / overlap 15 | **3,51** | **6,31** | 12,28 | — |
| chunk 30 / overlap 5 | 9,65 | 15,32 | 33,33 | 3,39 |
| chunk 30 / overlap 10 | 13,16 | 12,61 | 8,77 | **1,69** |
| chunk 40 / overlap 5 | 7,89 | 33,33 | 51,75 | **1,69** |

_(WER hors nombres, en %)_

**Aucun réglage n'est bon partout**, et l'amplitude est brutale : fr Serena passe de
4,39 % à 51,75 % selon le découpage. La recherche s'arrête ici — `CLAUDE.md` § 5
demande de consigner, pas de réparer indéfiniment.

**Verdict : go sous réserve.** parakeet reste le principal — il est **dix fois plus
rapide** que whisper (0,037 contre 0,388 de facteur temps réel ; seul parakeet tient
le seuil de 0,3), il a l'horodatage au mot **natif** et non reconstruit par DTW, et
il pèse 0,84 Go en mémoire contre 1,92. Sur six fichiers sur huit, son WER hors
nombres est de 1,80 à 4,39 %, très en dessous du seuil de 8 %.

**La réserve est une contrainte d'architecture, pas un détail :** la brique doit
**vérifier la couverture de chaque transcription** (nombre de mots transcrits rapporté
au nombre de mots du script, qui est connu puisque c'est nous qui l'écrivons) et
**réessayer avec découpage, puis basculer sur whisper**, quand la couverture tombe
sous un seuil. `REFERENTIEL.json → production.couverture_sous_titres` vise 100 % :
un ASR qui perd un tiers d'une vidéo sur 2 fichiers sur 8 ne l'atteint pas tout seul.
C'est à inscrire au contrat d'interface de l'étape 8.

**Le seuil « décalage médian ≤ 80 ms » n'est pas mesuré** : il demande un alignement
de référence dont la session ne dispose pas. Ce qui est vérifié à la place :
horodatages présents sur les 866 mots, strictement croissants, contenus dans la durée
de l'audio.

### 1.4 Musique — **non mesuré**, pour deux raisons distinctes

Détail dans `benchmarks/MUSIQUE.md`. En résumé :

- **ACE-Step — non mesuré : disque.** Le dépôt réel (`ACE-Step/Ace-Step1.5`, la casse
  de `SELECTION.md` était fausse) pèse **~10,1 Go**, non 2,39. La condition posée par
  `SELECTION.md` (« seulement si une brique a libéré ≥ 2,4 Go ») n'est pas
  approchable, même en basculant le LLM sur Qwen3.5-4B. **La question ne se rouvre
  pas.** Aucune mesure de performance n'a été prise : c'est un no-go de budget.
- **Inventaire de l'Audio Library — non mesurable par la session.** Le seuil « ≥ 5
  pistes distinctes par niche » exige une session YouTube Studio authentifiée, donc
  les comptes de chaîne, qui sont la question ouverte n° 1 pour Alek. Automatiser
  cette navigation est exclu (`docs/CONFORMITE.md` § 9). Reporté à l'étape 14.

---

## 2. Visuel (étape 5.2, 15/09/2026)

Machine : MacBook Air M2, 8 cœurs, 16 Go de RAM unifiée, macOS 27.0. Toutes les
valeurs sont mesurées sur cette machine, un processus par outil. Les pics MLX
sont ceux qu'annonce mflux lui-même ; les autres pics sont du RSS.

### 2.1 Tableau des briques

| Outil | Brique | Temps | Pic mémoire | Disque | Qualité /5 | Verdict |
|---|---|---|---|---|---|---|
| mflux FLUX.2-klein-4B 4-bit | Image 1280×720 | **137,0 s** (médiane, 94,6 → 160,5) | 11,15 Go | 4,62 Go | 4,6 | **Go** — sous le seuil réécrit à 180 s, voir 2.8 |
| mflux FLUX.2-klein-4B 4-bit | Image 1024×1024 | **161,0 s** (médiane, 134,4 → 173,0) | 12,37 Go | — | 4,6 | **Go** |
| mflux FLUX.2-klein-4B 4-bit | Cohérence d'identité, 3 graines | 158,8 s / image | 12,37 Go | — | **4** (Thomas, 15/09) | **Go pour le visage** — mais la **tenue** dérive, voir 2.3 |
| Depth Anything V2 Small | Carte de profondeur (MPS) | **0,24 s** (0,45 s la première) | 0,77 Go | 0,10 Go | non noté | **Go**, seuil ≤ 5 s tenu 20× |
| Depth Anything + ffmpeg overlay | Clip parallaxe 5 s 1080p30 | **3,7 s** (+0,7 s de découpe) | — | 0 | **4** (Thomas, 15/09) | **Go** — « propre, plus aucun trou, les plans sont dans le bon sens ». Seuil ≥ 3/5 tenu |
| ffmpeg `zoompan` ×4 | Clip Ken Burns 5 s 1080p30 | **2,6 s** | — | 0 | **4** (Thomas, 15/09) | **Go** |
| Revideo 0.11.0 headless | Rendu 1080p30, 301 images | **3,1 s → 98,4 img/s** | — | 0,86 Go (0,28 node_modules + 0,58 Chromium) | **4** (Thomas, 15/09) | **Go**, seuil ≥ 2 img/s tenu 49× |
| vtracer 0.6.x (API Python) | Vectorisation 1280×720 | **0,03 s** | — | 0,02 Go | 27 chemins | **Go**, seuils ≤ 10 s et ≤ 800 chemins |
| Playwright + ffmpeg | Animation `stroke-dashoffset` 5 s | **7,9 s** (7,5 capture + 0,4 encodage) | — | — | **4** (Thomas, 15/09) | **Go**, seuil ≥ 3/5 tenu |
| Rhubarb 1.14 `-r phonetic` | Visèmes sur 53 s de FR | **6,2 s** → 309 visèmes | — | 0,17 Go | non évalué (son) | **Go**, seuil ≤ 30 s |
| Rhubarb 1.14 `-r pocketSphinx` | Visèmes sur 53 s de FR | 23,6 s → 279 visèmes | — | — | — | Anglais seul, non retenu |
| Playwright HTML→PNG | Miniature 1280×720 | **0,20 s** (+0,24 s de lancement) | — | 0,21 Go (mesuré ; 0,35 annoncé) | non noté | **Go**, seuil ≤ 3 s tenu 15× |
| LTX-Video 2B v0.9 Q6_K | Vidéo IA 512×288, 4,04 s | **438,7 s** | 7,71 Go (MPS) | 6,79 Go, purgés | 3 | **No-go en production.** Clip vu et **gardé pour la démonstration à Alek** (Thomas, 15/09), voir 2.5 |

### 2.2 Qualité des cinq styles, notée sur les rendus 1280×720

Trois critères, chacun sur 5 : fidélité au style demandé · absence d'artefacts ·
exploitabilité en vidéo.

| Style | Fidélité | Artefacts | Exploitabilité | Moyenne | Observation |
|---|---|---|---|---|---|
| Illustration cartoon plate | 5 | 4 | 5 | **4,7** | Aplats et contours francs, exactement la cible. Main et arrosoir imprécis, bande verticale parasite au bord droit |
| Illustration documentaire | 5 | 4 | 5 | **4,7** | Rendu photographique plutôt qu'illustré ; perspective des rayonnages incohérente au fond |
| Photo réaliste d'un lieu | 5 | 5 | 5 | **5,0** | Aucun artefact visible. Le meilleur des cinq |
| Dessin au trait noir sur blanc | 5 | 4 | 5 | **4,7** | Trait propre, sans ombrage, idéal pour vtracer. **Deux engrenages au lieu des trois demandés**, un trait pend dans le vide |
| Fond abstrait motion design | 5 | 5 | 5 | **5,0** | Dégradés propres, aucun texte parasite |

**Moyenne des cinq styles : 4,6/5** — mais ces cinq notes portent sur **cinq
styles différents**, c'est-à-dire sur la qualité d'une image isolée. **Le seuil
de `SELECTION.md` § 4 porte, lui, sur 8 plans d'une même vidéo, et il n'est pas
tenu : voir § 2.11.** Une belle image isolée ne vaut rien si le plan suivant
change de personnage — ce qui est exactement ce qui s'est produit.

**Cohérence d'identité.** Même description, trois graines (11, 22, 33) :
`coherence_planche.png` montre le même personnage aux trois — mêmes lunettes
rondes, même barbe, même chemise verte, même cadrage. Seul le motif de la
chemise change (uni / à carreaux). Distances de hachage perceptuel entre les
trois : **8, 16 et 20 sur 64**, contre **32 de médiane** entre cinq styles
différents pris comme témoin. Mesure objective : les trois images sont deux fois
plus proches entre elles que des images sans rapport. **Le seuil de
`SELECTION.md` (« reconnaissable sans indication ») est un jugement de Thomas :
la planche est dans `samples/visuel/`. Note de la session : 4/5.**

### 2.3 Cohérence d'identité : le visage tient, la tenue dérive

**Confirmé par Thomas le 15/09/2026 sur `coherence_planche.png` : 4/5.** *(Cohérence d'**identité** d'un personnage sur 3 graines. La cohérence de **style** entre 8 plans d'une même vidéo est mesurée au § 2.11.)* Le
personnage est reconnaissable sans indication sur les trois graines — mêmes
lunettes rondes, même barbe, même cadrage, même style de trait. Le seuil de
`SELECTION.md` § 4 (« reconnaissable sans indication ») est tenu, et le repli
SDXL + IP-Adapter n'est pas activé.

**Mais la tenue dérive, et c'est un défaut exploitable.** La description de prompt
disait « green flannel shirt ». Résultat : chemise **unie** sur les graines 11 et
33, **à carreaux, à deux poches à rabat** sur la graine 22. Les distances de
hachage perceptuel le disaient déjà sans qu'on sache l'interpréter — la graine 22
est la plus éloignée des deux autres (20 et 16 sur 64), quand 11 et 33 ne sont
séparées que de 8.

| Paire | Distance pHash | Tenue |
|---|---|---|
| graine 11 ↔ graine 33 | **8** / 64 | unie ↔ unie |
| graine 22 ↔ graine 33 | 16 / 64 | à carreaux ↔ unie |
| graine 11 ↔ graine 22 | **20** / 64 | unie ↔ à carreaux |

**Pourquoi ça compte.** Entre deux vidéos d'une même chaîne, personne ne le
remarquerait. **Entre deux plans d'une même vidéo, ça se verrait** — et c'est
précisément l'usage visé par `REFERENTIEL.json` → `variantes_style.avatar`
(« même personnage/visage recyclé »).

**Où c'est traité : au prompt, à l'étape 12.2**, pas au modèle. *C'est cette étape qui tient le moteur illustré, la bibliothèque d'images réutilisables et la cohérence entre plans d'une même vidéo ; l'étape 17 est le moteur documentaire sur banques libres et ne génère aucun personnage. Copie à l'étape 29 pour la récurrence d'un personnage d'une vidéo à l'autre.* « Flannel » est un
mot ambigu — il désigne une matière, et le motif à carreaux n'est qu'une
association fréquente. Le gabarit de prompt du personnage devra décrire la tenue
sans ambiguïté (motif, couleur, nombre de poches, col) et la figer dans la fiche
de personnage. **Aucun changement de modèle n'est requis, et le serveur GPU n'y
changerait rien** — voir 2.9.

### 2.4 Le premier clip de parallaxe était faux — ce qui l'a corrigé

**Relevé par Thomas sur le rendu**, pas par la session. Le temps mesuré était bon,
le clip ne l'était pas. Trois défauts distincts, tous dans `bench_visuel.py`.

**1. Les rôles des couches étaient inversés.** Depth Anything V2 sort une
profondeur **inverse** : clair = proche. Vérifié sur l'image forêt elle-même —
la végétation du premier plan mesure **122** de luminance moyenne, la trouée de
ciel lointaine **40**. La tranche sombre `[0,00–0,34]` est donc le **fond**, et
elle occupe **72,4 % des pixels**. Le code la traitait en premier plan et la
faisait glisser le plus vite (−24·t), pendant que les troncs proches restaient
fixes derrière. Le mouvement était exactement à l'envers.

**2. Masques binaires mutuellement exclusifs → trous.** Chaque couche ne portait
que sa tranche de profondeur et rien d'autre. Dès qu'une couche glissait, on
voyait à travers — visible en bas à droite vers t = 4,5 s. **Corrigé par des
masques cumulatifs** : chaque couche contient tout ce qui est plus proche
qu'elle, et le fond est l'image entière sans masque. Une couche qui glisse
découvre alors une couche qui a du contenu là, pas un trou. Aucun inpainting
n'est nécessaire.

**3. Seuils nets → contours crénelés.** L'alpha suit désormais une rampe de
0,06 unité de profondeur autour du seuil, puis un flou gaussien de 3 px lisse
ce qui reste. Mesuré sur les couches produites : 8,3 % et 4,5 % de pixels en
fondu, contre 0 auparavant.

**Contrôle automatique ajouté au banc.** Le clip est rejoué sur un fond
**magenta**, la dernière image est extraite en PNG sans compression, et les
pixels magenta sont comptés : ce sont les trous. **Mesuré : 0 pixel à
t = 4,9 s.** Le banc échoue désormais si ce compte n'est pas nul.

| Couche | Rôle | Opacité moyenne | Dérive sur 5 s |
|---|---|---|---|
| `layer_0` | Fond (le plus loin) | 100 % (image entière) | −10 px |
| `layer_1` | Plan intermédiaire + premier plan | 27,7 % | −50 px |
| `layer_2` | Premier plan seul | 14,5 % | −130 px |

Les couches sont agrandies de 20 % (2304×1296 pour un cadre de 1920×1080) : la
dérive maximale de 130 px tient dans 192 px de marge, donc aucun bord vide.

**Ce que cet épisode dit de la méthode.** Le temps de calcul, la durée et le
nombre d'images étaient tous les trois justes. Rien dans les mesures ne pouvait
signaler que le mouvement partait dans le mauvais sens : **la règle « ouvrir le
fichier produit » ne suffit pas quand la session ne perçoit pas le mouvement.**
D'où le contrôle magenta, qui transforme un défaut visuel en compteur.

### 2.5 Preuve vidéo IA

**Tentée, et réussie — contrairement à ce qu'annonçait la veille du 13/09.**

| Élément | Valeur mesurée |
|---|---|
| Modèle | LTX-Video 2B v0.9, transformer GGUF **Q6_K** (1,72 Go) |
| VAE | `Lightricks/LTX-Video` (1,68 Go) |
| Encodeur de texte | T5-XXL bf16 (`city96/t5-v1_1-xxl-encoder-bf16`, 9,53 Go), **processus séparé, purgé avant la génération** |
| Sortie | `benchmarks/videoproof/ltx_512x288_4s.mp4` — 512×288, 97 images à 24 ips, **4,042 s**, h264, 58 ko |
| Chargement du pipeline | 35,1 s |
| **Génération** | **438,7 s, soit 108,5 s de calcul par seconde de vidéo** |
| Pic mémoire | 7,71 Go côté MPS, 6,33 Go de RSS |
| Swap pendant la génération | 1,52 Go — pas de thrashing |
| Poids total téléchargé | 6,79 Go (hors encodeur), **purgés dans la session** |
| Licence | LTXV Open Weights (gratuit en commercial **sous 10 M$ de CA**) — plafond de revenus, donc éliminatoire par principe en production (`STATE.md`, décision d'étape 4) |

**Ce que montre l'image extraite** (image médiane, `ltx_frame_mediane.png`) : une
forêt de pins brumeuse vue d'avion au lever du soleil, cohérente, sans
déformation grossière — **et deux fantômes de filigrane de banque d'images**, en
haut à gauche et en bas à droite, hérités des vidéos d'entraînement.

**Deux échecs à consigner, ils font partie de la preuve.**
1. **Wan 2.1-T2V-1.3B écarté avant même d'être lancé.** Le dépôt diffusers pèse
   **28,94 Go** (UMT5-XXL en float32 : 22,72 Go à lui seul), au-dessus du disque
   libre. Et sur MPS, Wan corrompt silencieusement au-delà de ~7 images latentes
   (dépassement de 2³¹ dans l'attention temporelle) — or 4 s à 16 ips en
   demandent 17. Source : ComfyUI issue #15793.
2. **Premier chargement de l'encodeur de texte : échec mémoire.** `transformers`
   déquantifie un GGUF **en float32** avant de caster : sur le T5-XXL Q5_K_M
   (3,39 Go sur disque), la machine est montée à **15,7 Go de swap** et le
   processus a été abandonné. Contournement retenu : un dépôt déjà en bfloat16,
   chargé en `low_cpu_mem_usage` — **pic de 7,9 Go, sans thrashing**.

**Conclusion pour l'étape 6.** La génération vidéo IA locale n'est pas
impossible sur ce M2 : elle est **impraticable à l'échelle**. À 108,5 s de calcul
par seconde de vidéo, **une minute de vidéo demande 1 h 49 de machine, et dix
minutes en demandent 18 h** — pour du 512×288, soit **un quatorzième** des pixels
du 1080p (147 456 contre 2 073 600), avec des fantômes de filigrane. Sur la même
machine, un plan de 5 s en 2.5D coûte **140,7 s** bout en bout (image 137,0 +
profondeur 0,24 + mouvement 3,5) quand 4 s de LTX en coûtent **438,7** : soit
**28,1 contre 109,7 s de calcul par seconde de vidéo, un rapport de 3,9** en
faveur du 2.5D. Par minute finie : **19,7 à 32,8 min contre 108,5, soit 3 à 5**.
C'est le chiffre à montrer à Alek.

> **Correction apportée à l'étape 6, le 15/09/2026.** Ce paragraphe portait
> « un rapport de 1 à 300 » et « un neuvième des pixels du 1080p ». **Les deux
> étaient faux.** Le 300 n'apparaît qu'en retirant le coût de génération
> d'images du seul côté 2.5D, c'est-à-dire en comparant une seconde de vidéo
> générative à un effet de mouvement ffmpeg, pas à un plan complet. Et
> 512 × 288 = 147 456 pixels contre 2 073 600 en 1080p : un quatorzième, pas un
> neuvième. Aucune décision ne change — le réaliste généré reste hors production.
> Détail dans `docs/STYLES.md` § 1.1.

### 2.6 Coût mesuré par minute de vidéo

Hypothèse de découpage : **12 plans par minute** (5 s par plan, au milieu des
rythmes du registre `ROADMAP.md` § 3.3, qui vont de 3,8 à 60 s par plan).
Chaque plan = 1 image 1280×720 + 1 carte de profondeur + 1 clip de mouvement.

| Style | s / image | Images + profondeur + mouvement, ×12 | **Minutes de machine par minute de vidéo** |
|---|---|---|---|
| Documentaire | 94,6 | 12 × (94,6 + 0,24 + 3,5) | **19,7 min** |
| Photo réaliste | 131,7 | 12 × (131,7 + 0,24 + 3,5) | **27,1 min** |
| Dessin au trait (whiteboard) | 137,0 | 12 × (137,0 + 0,24 + 3,5) | **28,1 min** |
| Cartoon plat | 149,8 | 12 × (149,8 + 0,24 + 3,5) | **30,7 min** |
| Motion design | 160,5 | 12 × (160,5 + 0,24 + 3,5) | **32,8 min** |
| *Vidéo IA générative, pour comparaison* | — | — | ***109 min*** |

**Une vidéo de 10 minutes, bout en bout, dans le style le moins cher :**

| Poste | Temps | Source |
|---|---|---|
| Images + profondeur + mouvement (documentaire, 120 plans) | 3 h 17 | mesuré ici |
| Voix off Qwen3-TTS (facteur temps réel 3,29) | 33 min | étape 5.1 |
| Script Qwen3.5-9B (14,4 tok/s, ~1 500 mots) | ~2 min | étape 5.1 |
| Rendu Revideo 1080p30 (18 000 images à 98,4 img/s) | 3 min | mesuré ici |
| Miniature | 0,2 s | mesuré ici |
| **Total** | **≈ 3 h 55** | |

Dans le style le plus cher (motion design), le même calcul donne **≈ 6 h 00**.
Le goulot d'étranglement est **la génération d'images, à 84 % du temps** — pas le
rendu, pas la voix. Toute optimisation doit commencer là.

### 2.7 Capacité du système, en vidéos par semaine

**C'est la réponse chiffrée à la question n° 7 d'Alek** (« combien de chaînes au
lancement, dans quelles langues ? »). Elle ne dit pas combien de chaînes ouvrir,
elle dit **combien le matériel actuel peut en nourrir**.

| Élément | Valeur |
|---|---|
| Vidéo de 10 min, style le moins cher (documentaire) | **3 h 55** |
| Vidéo de 10 min, style le plus cher (motion design) | **6 h 00** |
| Runs simultanés | **1** — `CLAUDE.md` § 4, condition pour que 16 Go tiennent |
| Hypothèse de cadence | **une vidéo par nuit de machine** : 3 h 55 à 6 h tiennent dans une nuit, et le M2 est aussi la machine de travail de Thomas |
| **Capacité** | **≈ 7 vidéos par semaine** |
| **Portefeuille tenable** | **3 chaînes à 2 vidéos/semaine = 6**, avec **1 nuit de marge** pour les reprises |
| 4 chaînes à 2/semaine | 8 vidéos/semaine — **au-dessus de la capacité** |

**Ce n'est pas l'API qui limite.** Le plafond de YouTube est de 6 uploads/jour,
soit **42 vidéos par semaine** : **six fois la capacité locale**. Le goulot est
entièrement sur cette machine, et à 84 % dans la génération d'images.

**Mise en regard du registre.** Les réseaux observés comptent ~70 chaînes
(`ROADMAP.md` § 3.3). **Trois chaînes, ce n'est pas ce modèle-là** — c'est ce que
le matériel actuel permet. Passer à l'échelle du registre suppose le serveur GPU,
et c'est le second chiffre à porter à l'étape 6.

**Ce que la capacité ne dit pas** : la charge humaine. Chaque vidéo demande un
geste manuel en Studio (~2 min) tant que l'audit API n'est pas obtenu, plus la
relecture par lots — dont le rythme est la question n° 3, toujours ouverte.

### 2.8 Recommandation par brique, contre les seuils de `SELECTION.md`

| Brique | Seuil | Mesuré | Décision |
|---|---|---|---|
| **Image** | **≤ 180 s** par 1280×720 (réécrit le 15/09/2026 ; 90 s auparavant) · pic < 13 Go | **137 s** (médiane) · 11,15 Go | **Retenu.** Thomas a réécrit le seuil après mesure : les 90 s venaient d'un M1 Max 64 Go, SDXL n'est mesuré nulle part sur M2 et pèse 2,3 Go de plus. Motivation complète dans `outils/SELECTION.md` § 4 |
| **Profondeur** | ≤ 5 s par carte | 0,24 s | **Retenu.** Aucune réserve |
| **Parallaxe** | ≤ 20 s par clip de 5 s · qualité ≥ 3/5 | 3,7 s · **4/5** | **Retenu.** Le premier clip était faux (voir 2.4) ; le clip corrigé est noté 4/5 par Thomas le 15/09. Le repli « Ken Burns plat » n'est pas activé |
| **Ken Burns** | — | 3,3 s en ×4 | **Retenu en ×4.** Mesuré aussi : ×1 = 2,3 s, ×2 = 2,7 s. Le suréchantillonnage ne coûte que 1,2 s : le garder |
| **Composition** | rendu headless fonctionnel · ≥ 2 img/s · pic < 8 Go | fonctionnel · **98,4 img/s** · non mesuré | **Retenu.** Réserve : la scène témoin est un texte sur fond uni ; une scène avec vidéos et images sera plus lente. À remesurer à l'étape 30.1 |
| **Whiteboard** | ≤ 10 s · ≤ 800 chemins · qualité ≥ 3/5 | 0,03 s · 27 chemins · **4/5** | **Retenu.** 27 chemins est très bas mais l'animation est jugée propre : `colormode=color` reste en réserve si un tracé plus riche est demandé |
| **Lip-sync** | ≤ 30 s pour 60 s d'audio | 6,2 s pour 53 s | **Retenu, et le blocage de l'étape 4 est levé** : le binaire x86_64 tourne sous **Rosetta 2**, aucune recompilation arm64 nécessaire. Le repli MFA + OpenFaceFX n'est pas installé |
| **Miniature** | ≤ 3 s | 0,20 s | **Retenu.** Le détourage rembg n'a pas été mesuré (non nécessaire à la composition testée) |
| **Vidéo IA** | aucun — la mesure sert à documenter | 108,5 s/s | **No-go**, et la preuve est produite |

### 2.9 Ce que le serveur GPU achète, et ce qu'il n'achète pas

**Précision demandée par Thomas le 15/09/2026, à porter à l'étape 6.** Elle évite
le malentendu le plus coûteux de la discussion avec Alek : croire qu'un serveur
règle les défauts de qualité.

**Ce qu'il achète — de la vitesse, partout.** Le calcul est le seul poste qu'un
GPU déplace. À 84 % du temps dans les images, c'est la brique image qu'il faut
déporter en premier ; le TTS (9 à 14 % du temps) et le rendu Revideo (1 %)
viennent loin derrière et ne justifient pas à eux seuls la dépense.

**Ce qu'il achète aussi — de la qualité, sur la seule brique image.** Trois
leviers, tous fermés aujourd'hui par le temps de calcul :

1. **Le 4B en bf16 au lieu du 4B en 4 bits.** Le même modèle, non quantifié : la
   quantification 4 bits fait gagner ~85 % de mémoire mais dévie visiblement du
   fp16. **Ce n'est pas le 9B** — vérifié le 15/09/2026, il est en
   `flux-non-commercial-license`, donc hors de ce projet quelle que soit la
   machine. **Monter en taille de modèle n'est pas une option ouverte par le
   serveur ; monter en précision, si.**
2. **Davantage d'étapes de débruitage.** 4 aujourd'hui, parce que c'est un modèle
   turbo et que chaque étape coûte ~34 s ici.
3. **Le levier le plus fort : générer 4 images pour n'en garder qu'une.** C'est
   la pratique qui fait la différence entre une image correcte et une bonne
   image. **Impossible à 137 s pièce** — cela porterait une vidéo de 10 min à
   13 h de machine. Un GPU la rend banale.

**Ce qu'il n'achète pas.** Trois défauts connus de ce projet, aucun n'est limité
par le calcul :

| Défaut | Cause réelle | Où ça se règle |
|---|---|---|
| **Voix française** — aucun TTS gratuit n'a de voix **native** FR ; le *cross-lingual* est un pis-aller | **Données d'entraînement**, pas calcul. Kokoro n'a qu'une voix FR notée B-, Qwen3-TTS aucune voix native FR/ES/IT sur ses 9 préréglages | Un TTS payant, ou du clonage — écarté le 15/09. **Pas un GPU** |
| **Dérive de tenue** du personnage (§ 2.3) | **Prompt ambigu** (« flannel ») | Gabarit de prompt, **étape 12.2** |
| **Photoréalisme comme style de vidéo** | **Nature du média** : la vidéo générative coûte 108,5 s par seconde de vidéo en 512×288, avec des fantômes de filigrane. Un GPU la rend possible, pas bonne | Banques de vidéos libres + montage, **décision de l'étape 6** |

> **Aucun défaut de qualité de ce projet n'est limité par le calcul.** Le serveur
> GPU achète du débit, et une marge de qualité sur la brique image. Tout le reste
> se joue dans les données, dans les prompts ou dans le choix du média.

### 2.10 Ce qui reste à trancher

1. ~~**Le seuil « ≤ 90 s par image 1280×720 » est manqué de 52 %.**~~
   **Tranché par Thomas le 15/09/2026 : seuil réécrit à 180 s, FLUX conservé.**
   Trois conséquences inscrites dans `outils/SELECTION.md` § 4 — (a) la
   génération d'images est le goulot d'étranglement n° 1 du système, à **84 % du
   temps de calcul** d'une vidéo ; (b) c'est **la première justification chiffrée
   du serveur GPU** (étape C2), et le poste à déporter en priorité — pas le TTS,
   pas le rendu ; (c) **la réutilisation de bibliothèque (étape 12.2) doit faire
   baisser ce coût, et ce n'est pas encore un fait** : le taux de réutilisation
   réel est à mesurer à l'étape 12.2, pas à supposer. Jusque-là, le coût de
   référence du système reste 137 s par plan.
2. ~~**La cohérence de style sur 8 plans d'une même vidéo n'a pas été mesurée.**~~
   **Mesurée le 15/09/2026 — § 2.11. Notée 4/5 par la session**, avec un défaut
   identifié : **la charte ne fixe pas le traitement du fond**, et le modèle
   tranche seul (5 plans « objet sur fond crème », 3 plans « pleine page »).
   À inscrire dans la charte à l'**étape 12.2**.
3. **Le pic MLX de 12,37 Go en 1024×1024 laisse 3,6 Go de marge** sur 16 Go.
   Aucune autre charge ne doit tourner pendant la génération d'images.
4. **La qualité en mouvement (parallaxe, Ken Burns, whiteboard, Revideo) n'est
   pas évaluée par la session** — quatre MP4 sont dans `samples/visuel/`.
   **Priorité au clip de parallaxe**, refait après le relevé de Thomas (§ 2.4) :
   son verdict conditionne la brique 2.5D, qui est le cœur de la réponse à Alek.
5. **Le plafond de cumul disque est passé de 18 à 22 Go** (Thomas, 15/09/2026).
   Cumul mesuré 21,52 Go : **0,48 Go de marge**. Tout nouveau poids devra être
   gagé sur un retrait.

### 2.11 Cohérence de style sur 8 plans d'une même vidéo

**Le seul seuil de 5.2 qui restait ouvert.** Les cinq styles du § 2.2 mesuraient
cinq styles *différents* ; le seuil de `SELECTION.md` § 4 porte sur **8 plans
consécutifs d'une même vidéo**, et c'est **le critère qui prime** pour la brique
image. Mesuré le 15/09/2026, à la demande de Thomas — l'étape 6 ne pouvait pas le
faire, son budget disque est de 0 et elle ne génère rien.

**Protocole.** Un script de vulgarisation sur le sommeil, une charte de chaîne
unique (préfixe + suffixe encadrant chaque intention visuelle, comme le fera
`charte.style_prefix` en 12.2), 8 intentions consécutives, **une graine par
plan** dérivée de `sha256(video_id, plan)` — exactement le schéma de production.
Script : `benchmarks/coherence_8plans.py`. Planche : `coherence8/planche_8plans.png`.

**Choix d'instrument, et pourquoi le pHash ne sert que de témoin.** Le pHash
compare des **structures** : entre 8 plans de contenus différents il est grand par
construction (médiane mesurée **30/64**), et cela ne dit rien du style. Ce qui se
voit quand un plan « ne va pas avec les autres », c'est la **palette** et le
**traitement du fond**. Les deux sont mesurés ; le pHash reste comme témoin de
contraste.

| Mesure | Valeur | Lecture |
|---|---|---|
| Intersection d'histogrammes teinte × saturation, médiane | **0,474** | Palette commune sur la moitié de la distribution |
| Intersection, maximum | 0,858 | Deux plans quasi identiques en palette |
| Intersection, minimum | **0,024** — paire `plan_01 \| plan_07` | Deux plans qui ne partagent presque rien |
| pHash, médiane (témoin) | 30 / 64 | Contenus différents, comme attendu |
| Luminance médiane · étendue | 204,4 · **82,9** | |
| Saturation médiane · étendue | 79,8 · **133,3** | L'étendue la plus large : c'est là qu'est le défaut |
| Contraste médian · étendue | 71,5 · 46,8 | |

**Verdict : NON TENUE.** *(La session avait d'abord écrit 4/5. Relecture de
Thomas le 15/09/2026 : faux, et la métrique ne pouvait pas le voir.)*

**Ce que la mesure a laissé passer, sur le seul `plan_08`.** Le personnage est
une femme aux cheveux longs sombres sur les plans 1 à 7 — chignon au `plan_05`.
Au `plan_08`, trois défauts **indépendants** :

1. **Le crâne porte une coupe courte masculine.** Le personnage a changé.
2. **Sa chevelure subsiste, en mèche détachée**, flottant à hauteur d'épaule,
   avec un vide net entre elle et la tête. Vérifié au pixel : deux composantes
   sombres distinctes, **séparées de 17 px**.
3. **Le pied arrière est retourné.** La marche va vers la droite ; la pointe de
   la chaussure arrière regarde à gauche. Les deux chaussures ne sont pas vues
   du même angle, et l'ombre — un grand triangle orange — n'est ancrée sous
   aucun pied.

**Et le cadrage : c'est le `plan_01` l'intrus**, seul plan encadré d'une marge
crème, quand `plan_05` et `plan_08` vont au bord. *La première rédaction de ce
§ classait `plan_05` avec les plans « objet sur fond crème » : la part de crème
dans l'image ne mesure pas le cadrage. Le contrôle C1 du § 2.12 le mesure, lui,
et désigne bien `plan_01`, seul sur huit.*

**Pourquoi la mesure n'a rien vu.** L'intersection d'histogrammes compare des
**distributions de couleurs**. Un personnage qui change de sexe, une mèche
détachée et un pied retourné **ne déplacent presque aucun pixel d'une classe de
couleur à une autre** : la palette reste exactement la charte. La métrique a
répondu juste à la question qu'elle sait poser, et cette question n'était pas
la bonne.

**Erreur de méthode de la session, à ne pas répéter.** Le jugement « 4/5 » a été
porté sur une planche de contact à **440×248 par vignette**, soit un huitième
des pixels. Une mèche détachée de 17 px et une pointe de chaussure inversée sont
**invisibles à cette taille**. **Une planche de contact juge une famille de
style et une palette ; elle ne juge ni l'anatomie ni l'identité.** Ceux-là
exigent le plan en pleine résolution, un par un.

**Troisième angle mort de la même famille sur cette étape**, après la parallaxe
inversée (§ 2.4) et la dérive de chemise (§ 2.3). Le facteur commun est net :
**les trois défauts étaient structurels ou sémantiques, et les trois mesures
étaient des statistiques agrégées** — temps, durée, nombre d'images, histogramme.
Aucune ne pouvait les atteindre. La mesure agrégée dit qu'un plan est *dans la
charte* ; elle ne dit jamais qu'il est *juste*.

**Un second écart, réel celui-là : le cadrage n'est pas fixé par la charte.**
Mesuré par le contrôle C1 (§ 2.12) : **1 plan encadré sur 8**, le `plan_01`,
dont l'illustration est enfermée dans un encadré au milieu d'une marge crème
quand les sept autres vont au bord du cadre. Sur une vidéo de 120 plans, un
cadrage laissé au tirage ne tiendra pas.

**Ce qu'il faut inscrire dans la charte, à l'étape 12.2** : le traitement du
fond (pleine page ou objet sur fond uni), la couleur de ce fond, et la part du
cadre qu'occupe le sujet. Et, pour le personnage, **tout ce qui le décrit
doit être figé** — coiffure comprise, puisque c'est elle qui a lâché ici comme
c'est la chemise qui avait lâché au § 2.3.

**Temps observé, et une divergence à signaler.** Médiane **94 s** par plan en
1280×720, **21,4 min pour les 8** — mais avec **un plan à 621 s**, soit 6,6 fois
la médiane, cause non établie (throttling thermique du M2 sans ventilateur, ou
contention avec un autre processus). Le § 2.6 retient **137 s** depuis le banc
principal. **L'écart entre 94 et 137 s n'est pas expliqué** — les prompts de ce
test sont plus courts, et la machine était plus froide au départ. **Le modèle de
coût garde 137 s**, la valeur conservatrice ; une mesure dédiée de la dispersion
reste à faire avant de s'appuyer sur un chiffre au pourcentage près.

### 2.12 Un contrôle automatique est-il atteignable ? Trois construits, deux qui marchent

Question posée par Thomas le 15/09/2026 après l'échec du § 2.11 : **proposer au
moins un contrôle qui aurait attrapé ces défauts, et dire franchement si
l'automatisation est atteignable ici.** Trois contrôles ont été écrits et
**exécutés** sur les 8 plans (`benchmarks/controles_plan.py`), pas seulement
proposés.

| Contrôle | Ce qu'il mesure | Résultat sur les 8 plans | Verdict |
|---|---|---|---|
| **C1 — cadrage** | Marge uniforme sur les quatre bords : le plan est-il encadré ou en pleine page ? | **1 encadré sur 8 : `plan_01`** — exactement l'intrus désigné à l'œil | ✅ **Marche.** Déterministe, sans modèle, quelques ms |
| **C2 — fragments détachés** | Petite forme isolée à quelques pixels d'une grande masse de même teinte — signature d'un morceau qui aurait dû être attaché | **Échec** : n'a **pas** vu la mèche (le plus proche des 15 signalés est à 75 px d'elle), et a signalé **7 plans sur 8**, dont un à 82 fragments | ❌ **Ne marche pas** |
| **C3 — palette** | Intersection d'histogrammes teinte × saturation contre la charte de la série | Isole `plan_07` (0,045 contre 0,474 de médiane) | ✅ **Marche**, mais ne voit que la couleur |

**Pourquoi C2 échoue, et pourquoi aucun réglage ne le sauvera.** La mèche *est*
géométriquement séparée : 17 px entre elle et la chevelure. Mais sur ces mêmes
8 plans, **13 séparations parfaitement légitimes** existent entre masses sombres
— médiane 27 px — et **3 d'entre elles tombent dans la même fourchette de 10 à
25 px**. Une mèche détachée par erreur et un vêtement séparé des cheveux par
dessin ont **exactement la même signature géométrique**. Les distinguer suppose
de savoir que *ce* bloc sombre est une chevelure et que *celui-là* est un tissu.
**C'est de la sémantique, pas de la géométrie.**

**Ce qui est atteignable aujourd'hui, sur cette machine, à 0 €**

- ✅ **Cadrage** (C1) — et il faut l'ajouter au portillon de l'étape 15.
- ✅ **Dérive de palette** (C3).
- ✅ **Dérive de luminance, de saturation, de contraste** — déjà mesurée au § 2.11.

**Ce qui ne l'est pas**

- ❌ **Membre ou mèche détachés** : indistinguable d'une séparation voulue (mesuré).
- ❌ **Anatomie fausse** — pied retourné, angles de vue incompatibles, ombre non
  ancrée. Aucune approche géométrique n'y donne accès.
- ❌ **Dérive d'identité d'un plan à l'autre** — sexe, coiffure, âge. Un
  encodeur de visages y répondrait, mais ceux qui sont disponibles sont soit
  non commerciaux (InsightFace, déjà écarté à l'étape 4), soit entraînés sur des
  visages photographiques et non sur des illustrations plates.

**Réponse franche à la question posée : non, l'automatisation n'est pas
atteignable pour cette classe de défauts sur cette machine.** Ce qui les
attraperait est un **modèle vision-langage** à qui l'on demande, plan par plan :
« cette illustration contient-elle une anatomie impossible, un élément détaché,
ou un personnage incompatible avec cette image de référence ? » Or le LLM retenu
est **textuel**, aucun VLM ne tient dans le budget de 22 Go, et une API payante
romprait la contrainte 0 €.

**Donc, en l'état, la brique image impose une relecture humaine plan par plan.**
Et **cela heurte de front la contrainte 3 de `ROADMAP.md` § 3.4** : « l'humain
arbitre par configuration et par contrôle qualité **par lots**, jamais plan par
plan ». À 120 plans par vidéo et 7 vidéos par semaine, c'est **840 plans à
regarder chaque semaine**.

**Trois voies, à trancher à l'étape 6 — aucune n'est gratuite**

1. **Assumer la relecture par plan pour la brique image seule**, et retirer la
   promesse d'autonomie sur ce point. C'est honnête, et c'est cher en temps
   humain.
2. **Un relecteur VLM sur le serveur GPU.** Il se confond avec le sélecteur dont
   parle le § 2.9 : générer 4 images pour n'en garder qu'une **suppose un
   juge**, et ce juge doit voir. *Nuance par rapport au § 2.9 : le défaut n'est
   pas causé par un manque de calcul, mais sa **détection** exige un modèle qui
   ne tient pas ici. Le serveur achète donc aussi cela.*
3. **Réduire l'exposition par le choix de sujet.** Les trois défauts sont
   concentrés sur **un personnage humain en pied, en mouvement**. Les plans 2,
   3, 4 et 6 — un cerveau, un réveil, des ondes, une tasse — n'en portent aucun.
   **Le risque n'est pas réparti : il est dans l'anatomie.** Une charte qui
   privilégie objets, lieux et abstractions, et qui cadre les personnages en
   buste plutôt qu'en pied, fait tomber l'essentiel du problème sans rien coûter.
   **C'est l'option la moins chère, et elle est directement exploitable à
   l'étape 6.**
