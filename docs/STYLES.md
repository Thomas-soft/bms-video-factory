# STYLES.md — ce que chaque style demandé coûte, vaut, et devient

Étape 6, 15/09/2026. Tranche les sept styles demandés par Alek avec les mesures des
étapes 5.1 et 5.2 (`benchmarks/RESULTATS.md`), les formats du registre
(`registre/REFERENTIEL.md`, `registre/TRAJECTOIRES.md`) et les règles de
`docs/CONFORMITE.md`.

**Aucune note de qualité n'est portée ici sans un fichier à ouvrir ou une mesure**, et
chaque note porte le nom de qui l'a donnée — *(Thomas)* pour un rendu vu et jugé,
*(session)* pour une note de la session, **non validée**. La distinction n'est pas
cosmétique : à l'étape 5.2, une note de la session (4/5 sur la cohérence de 8 plans)
s'est révélée fausse à la relecture de Thomas.

Partout où rien n'a été produit ni mesuré, la case dit « non mesuré » — y compris pour
des styles retenus. Un style peut être retenu sur son coût, ses licences et ce que
fait le registre sans que sa qualité soit encore mesurée : la case le dit, et la
condition de mesure qui lève la réserve est écrite au § 7.

---

## 1. Matrice des styles

Coût = **minutes de calcul par minute de vidéo finie**, partie **visuelle propre au
style**. Trois postes communs à tous les styles s'y ajoutent : voix off **3,4**
(facteur temps réel 3,373 en français, § 1.2 — et non 3,289, qui est l'anglais),
script **0,2**, rendu Revideo **0,3** (98,4 img/s à 1080p30), soit **+3,9 min/min**.
Un plan complet coûte **140,74 s** : image 137,0 + profondeur 0,24 + mouvement 3,5.
L'hypothèse « 12 plans/min » (5 s par plan) des lignes ci-dessous **est la plus chère
du registre** : les niches mesurées vont de 4,5 à 15,7 s par plan — voir § 3.1.

| Style demandé | Chaîne d'outils locale | Qualité mesurée /5 | Coût mesuré (min/min) | Poids disque | Preuve (chemin) | Ce que seul un serveur GPU ajouterait | Statut |
|---|---|---|---|---|---|---|---|
| **Motion design** | Revideo 0.11.0 headless (MIT) + typographie, formes, `lottie-web`/`Rive` + fonds FLUX réutilisés | **rendu 4/5** *(Thomas, 15/09 — scène « texte sur fond uni », pas une séquence)* · **fond abstrait 5,0/5** *(session)* · **trois séquences de 32 s rendues le 16/09** (typographie cinétique, schéma animé, hybride), 1920×1080, 30 ips, voix montée — **notées par Thomas le 16/09 : le schéma animé seul est retenu** — typographie cinétique et hybride écartés après deux exécutions | **mesuré le 16/09 : 0,28 à 0,56 en vecteur pur** (rendu seul, 54,5 à 122,9 img/s, pic mémoire 1,06-1,14 Go) · **1,90 avec 1 fond/min** (image à 98,8 s, mesure 12.2) · **9,5 au rythme de 3 fonds/32 s** · l'ancienne projection de 2,7 se recompose à **2,53** avec ses propres hypothèses | 0,30 Go (`node_modules`, hors plafond) + 0 Go de navigateur — **Revideo tourne sur le Chromium de Playwright déjà installé**, mesuré équivalent (8,05 s contre 8,31 s) | `benchmarks/preuve_motion/motion_{A,B,C}.mp4` + `RESULTATS.md` · `outils/revideo_projet/` · RESULTATS § 2.1 | **débit, mémoire, disque et coût de génération mesurés** ; note de qualité et fluidité **non évaluées** | **retenu v2, sur le seul schéma animé** — étape 30.1, remontée en phase 2 (§ 6) **dont l'argument est à revoir : il portait sur le coût de calcul des deux traitements écartés, pas sur le coût d'écriture du schéma, jamais chiffré**. Réserve du § 7 levée sur la part mesurable **et sur la note** |
| **Images cartoon** (illustré animé) | FLUX.2-klein-4B-4bit (mflux) + Depth Anything V2 Small + parallaxe / `zoompan` ffmpeg + Revideo | **image isolée 4,7/5** *(session)* · **parallaxe 4/5** et **Ken Burns 4/5** *(Thomas, 15/09)* · **cohérence sur 8 plans d'une même vidéo : NON TENUE** *(relecture de Thomas ; la métrique employée ne pouvait pas la voir)* | **30,7** (149,8 s/image) | 4,72 Go (FLUX 4,62 + profondeur 0,10) | `benchmarks/samples/visuel/img_cartoon_1280x720.png` · `benchmarks/samples/visuel/clip_parallaxe_1080p.mp4` (1920×1080, 150 img, 5,00 s, vérifié `ffprobe`) · `benchmarks/samples/visuel/coherence8/plan_08.png` | 4 images générées pour 1 gardée · bf16 au lieu de 4 bits · plus d'étapes de débruitage · **un juge VLM**, seul moyen connu de voir l'anatomie et l'identité (§ 5) | **retenu v1** — étape 12.2 |
| **Whiteboard animé** | FLUX.2-klein-4B-4bit (mflux) **en 768×768** + vtracer 0.6.15 (MIT) + `Path.end` de Revideo 0.11.0 + main PNG tracée par du code + Caveat (OFL) | **image 4,7/5** *(session, 15/09)* · **animation 4/5** *(Thomas, 15/09, clip de 5 s)* · **moteur livré et rendu à l'étape 30.2 ; la vidéo entière n'a pas été regardée** | **12,13 × le temps réel** mesuré sur 30 plans (727,9 s par minute de vidéo) — **96,7 % est la génération d'images** (médiane 66,2 s par plan en 768×768, contre 137,0 s en 1280×720). Le **rendu seul est à 0,395 ×** (Revideo 119,6 img/s + découpe) · vectorisation **18 ms par image** | 4,64 Go (FLUX 4,62 + vtracer 0,02) + **0 Go** de navigateur (Chrome du système) | `factory/styles/whiteboard.py` · `render/src/scenes/draw-svg.tsx` · `config/styles/whiteboard.yaml` · `RESULTATS.md` § 3.6 | le débit d'image, et lui seul : le tracé est vectoriel et déjà gratuit | **retenu v1** — étape 30.2 |
| **Documentaire** | Pexels / Pixabay / Openverse / Wikimedia / NASA / Internet Archive + ffmpeg + Revideo | **non mesuré** — aucun plan de banque n'a été récupéré ni monté à ce jour | **non mesuré** ; **génération d'images ≈ 0** (téléchargement et montage, pas de calcul) | **0 Go** de modèle | **aucune preuve visuelle.** Licences, quotas et attribution vérifiés à l'étape 4 (`outils/SELECTION.md` § 6) | **rien** : la brique est de l'entrée/sortie, pas du calcul | **retenu v2** — étape 17, **sous réserve de mesure** (§ 7) |
| **Réaliste par banques de vidéos libres** | identique au documentaire ; même moteur, autre configuration (plans contemporains filmés, en habillage sous n'importe quelle narration) | **non mesuré** | **non mesuré** ; génération ≈ 0 | 0 Go | **aucune preuve visuelle** | **rien** | **retenu v2** — étape 17, même réserve |
| **Réaliste généré** | LTX-Video 2B v0.9 Q6_K (GGUF) + T5-XXL bf16 en processus séparé — mesuré puis **purgé** | **3/5** *(session ; clip vu par Thomas et gardé pour la démonstration)* — 512×288, plan cohérent, **deux fantômes de filigrane** hérités des vidéos d'entraînement | **108,5** (108,5 s de calcul par seconde de vidéo) | 6,79 Go, purgés | `benchmarks/videoproof/ltx_512x288_4s.mp4` (512×288, 97 img à 24 ips, 4,042 s, vérifié `ffprobe`) · `benchmarks/videoproof/ltx_frame_mediane.png` | rend la brique **possible**, pas bonne. Le modèle reste à choisir : LTXV porte un plafond de revenus (10 M$), éliminatoire par principe. Ordre de grandeur annoncé pour la cible : **Wan 2.2 5B ≈ 9 min par clip de 5 s sur RTX 4090** (`ROADMAP.md` étape 31, à confirmer) | **serveur seulement** — et même alors, **b-roll de quelques secondes**, jamais une vidéo entière |
| **Avatar parlant** (2D) | personnage `nova` généré (FLUX.2 klein) puis édité par référence pour 9 bouches + yeux fermés, détouré par rembg BiRefNet ; Rhubarb 1.14 (`pocketSphinx` + texte en anglais, `phonetic` ailleurs) sous Rosetta 2 ; Pillow + ffmpeg, ProRes 4444 alpha incrusté sur le style hôte (`factory/styles/avatar2d.py`) | **produit le 24/09/2026** (`fgr6`, étape 29) : QC PASS 88,2 ; 3 images extraites à des visèmes D, F, X montrent la bouche attendue ; **synchronisation au son : non évaluée** (la session n'entend pas) | **+37,8 s par vidéo** pour 7 plans (Rhubarb 22,1 + composition 5,4 + incrustation 10,4) | 0,22 Go (rembg) + 0,17 Go (Rhubarb) | `workspace/runs/bms-science-en-20260924-fgr6/avatar/` · `workspace/library/characters/nova/` | style du personnage (cel-shading) ≠ style vectoriel de la chaîne ; tout le buste tourne (pas de calque cou/tête) | **retenu v2** — livré étape 29 |
| **Animations poussées** (animation de personnages ou d'organes, façon CasiCreativo) | **aucune chaîne d'outils retenue** | **non mesuré — rien n'a été produit** | non mesuré | — | **aucune** | **rien** : c'est du temps d'animateur, pas du calcul | **abandonné** (§ 2) |
| *Cartes* (non demandé par Alek — moteur d'amorçage de l'étape 12.1) | Revideo : titres, texte, fond uni | **non mesuré** en tant que style | **0** (le rendu est déjà dans le commun) | 0,86 Go | `outils/revideo_projet/` | rien | **retenu v1**, **usage interne** : ne doit jamais être publié tel quel (§ 8) |

**Poids disque non cumulables** : FLUX (4,62 Go) sert l'illustré, le whiteboard, le
documentaire généré et les fonds du motion design. Le cumul réel retenu est celui de
`outils/MODELES.md` — **21,52 Go mesurés** pour un plafond de 22.

**Ce que la colonne « qualité » mesure, et ce qu'elle ne mesure pas.** Les notes
d'image sont portées sur **une image isolée**, en pleine résolution. Le seul essai de
cohérence sur **8 plans d'une même vidéo** a échoué (RESULTATS § 2.11). Une bonne note
d'image n'est donc pas une bonne note de vidéo, et aucune ligne de cette matrice ne
prétend le contraire.

### 1.1 Deux corrections aux livrables antérieurs, appliquées dans cette étape

1. **Le rapport « 1 à 300 en faveur du 2.5D » était faux.** Le bon calcul compare des
   secondes de vidéo finie, images comprises des deux côtés : un plan 2.5D de 5 s
   coûte 137,0 + 0,24 + 3,5 = **140,7 s**, un plan LTX de 4 s coûte **438,7 s**, soit
   **28,1 contre 109,7 s par seconde de vidéo — un rapport de 3,9**. Par minute finie :
   **19,7 à 32,8 min contre 108,5, soit 3 à 5**. Le 300 n'apparaît qu'en retirant le
   coût de génération d'images du seul côté 2.5D.
2. **« un neuvième des pixels du 1080p » était faux.** 512 × 288 = 147 456 pixels ;
   1920 × 1080 = 2 073 600. Le rapport est de **14**, pas de 9.

**Corrigé le 15/09/2026 dans `benchmarks/RESULTATS.md` § 2.5 et `SUIVI.md` § 3**, avec
la mention de la correction dans les deux fichiers. Aucune décision ne change : le
réaliste généré reste hors production. Ce qui changeait, c'est le chiffre qu'on
s'apprêtait à montrer au client — et un chiffre faux dans un argumentaire vrai coûte
l'argumentaire entier.

### 1.2 Ce qu'on sait du serveur, et ce qu'on n'en sait pas

**La machine actuelle est le MacBook Air M2 de Thomas — 8 cœurs, 16 Go de mémoire
unifiée**, Metal/MPS ou CPU, et c'est **aussi sa machine de travail**
(RESULTATS § 2.7). Toutes les mesures de ce document viennent de là, et d'elle seule.

**La machine cible n'est pas choisie.** Le budget est acté par Alek (« 50 €/mois
approved »), la machine ne l'est pas : ni le loueur, ni le modèle de carte, ni le mode
de facturation (à l'heure chez RunPod, Vast.ai, TensorDock, Lambda ; au mois chez
Hetzner, OVHcloud, Scaleway). **C'est le travail de l'étape 31**, qui doit rendre, pour
50 €, les heures de calcul obtenues et le débit attendu par brique. **Aucun chiffre de
serveur n'est engagé ici**, à une exception près, elle-même annoncée et non vérifiée :
Wan 2.2 5B ≈ 9 min par clip de 5 s sur RTX 4090 (`ROADMAP.md` étape 31).

**Deux usages possibles du même budget, et il faudra arbitrer.**
1. **Du débit** — plus de chaînes, des vidéos plus longues, la capacité du § 3.1
   relevée. C'est l'usage que justifie le goulot mesuré : 84 % du temps de calcul est
   dans la génération d'images.
2. **De la qualité** — 4 images générées pour 1 gardée, bf16 au lieu de 4 bits, plus
   d'étapes de débruitage, et le **juge VLM** qui manque aujourd'hui (§ 5). Sur la
   vidéo, des plans de quelques secondes en habillage.

Les deux consomment le même calcul : **on ne les aura pas tous les deux à plein**.
L'arbitrage se fait à l'étape 31, chiffres en main, pas ici.

---

## 2. Pourquoi « animations poussées » est abandonné, et non reporté

C'est le seul refus franc de cette note, et il ne tient pas au calcul.

- **Aucun outil n'a été retenu pour cela à l'étape 4.** Le repli de composition
  (MoviePy + Manim) est décrit dans `outils/SELECTION.md` § 8 comme couvrant « le
  motion design de base, **pas le niveau CasiCreativo** ». Rien n'a été mesuré.
- **La vidéo générative ne le remplace pas** : 108,5 s de calcul par seconde, en
  512×288, avec filigranes — et elle produit du plan filmé, pas de l'animation de
  personnage.
- **La chaîne qui sert de référence à Alek publie 57 vidéos en 5 ans**, à des
  intervalles de 9 à 272 jours (`TRAJECTOIRES.md` § 1), pour une médiane de 271 617
  vues. Ce rythme est celui d'un studio d'animation, pas d'une usine à 2 vidéos par
  semaine et par chaîne. **Ce n'est pas une limite de notre machine : c'est la nature
  du travail.** Un serveur GPU n'y change rien.

**Ce qui est proposé à la place** : le motion design (formes, typographie, diagrammes
animés, `lottie-web`/`Rive`) couvre la part de l'intention qui est atteignable
automatiquement. La part qui ne l'est pas — un personnage animé image par image —
n'est pas promise.

---

## 3. Ce que fait le registre, et ce que cela impose

**CasiCreativo English** (« référence DA » d'Alek, chaîne mère ES à 8,75 M) : motion
design et animation d'organes, **57 vidéos en 5 ans**, médiane **271 617 vues**. Sa
seule chute mesurée vient d'un pivot vers l'ultra-court en 2024-Q3 (durée médiane
107 s → 30 s, vues/jour ÷ 9,5), **pas de sa direction artistique** ; « la rareté ne l'a
pas tuée » (`TRAJECTOIRES.md` § 1). Implication : son niveau d'animation s'achète en
temps d'animateur, et sa cadence n'est pas celle que BMS vise.

**Réseaux Thoth** (Library of Thoth EN 398 vidéos, Bibliothèque de Thot FR 324 pour
67,6 K abonnés, Biblioteca di Thoth IT 241) : **images fixes et voix off**, niche
`spiritualite`. **Aucune chaîne Thoth n'est dans les 29 rythmes de coupe mesurés**
(`ROADMAP.md` § 3.3) : la valeur de 11,4 s par plan est la médiane de montage de leur
niche, sur **n = 6 chaînes**, pas une mesure de Thoth. Avec cette réserve, elle donne
**5,3 plans par minute au lieu de 12**, et c'est le modèle de volume du registre
(« funnel + collabs », étape 24). **Aucun photoréalisme.**

**Elias Yoder Amish** : **358 000 abonnés**, **259 057 vues médianes** sur les vidéos
de plus de 90 jours (n = 34), chaîne ouverte le 17/05/2026 — **57 vidéos en 95
jours**, format long constant (~21 min), 0 % de Shorts, personnage récurrent
(`variantes_style.avatar`). *(Le « 345 K » de `ROADMAP.md` § 3.3 ne correspond à
aucune des deux mesures ; il vient du PDF, dont les abonnés sont périmés — divergence
déjà consignée dans `STATE-ARCHIVE.md`.)* Son rythme de coupe propre est de **4,1 s
par plan sur 92 mesures** : 21 minutes font alors **307 plans**, soit **12,0 h de
génération d'images** sur cette machine. **Ce format n'est pas tenable en images
générées ; il l'est en banques et en réutilisation de bibliothèque.**

### 3.1 Le coût par minute dépend de la niche, pas seulement du style

Calculé à partir de deux mesures : **140,74 s par plan** (étape 5.2) et le rythme de
coupe `cible_montage` de chaque niche (étape 3). **Arithmétique de deux mesures, pas
une mesure bout en bout.** Colonne « vidéo entière » = images + les 3,9 min/min
communs (voix, script, rendu), à la durée médiane de la niche.

| Niche | s/plan (n) | plans/min | Images générées : min/min | Durée médiane | Vidéo entière |
|---|---|---|---|---|---|
| `true_crime` | 15,7 (5) | 3,8 | **9,0** | 25,5 min | **5,5 h** |
| `spiritualite` | 11,4 (6) | 5,3 | **12,3** | 31,2 min | **8,4 h** |
| *repli, 3 niches sans mesure* | 7,8 | 7,7 | 18,0 | — | — |
| `home_hacks` | 6,9 (9) | 8,7 | **20,4** | 18,1 min | **7,3 h** |
| `science_pop` | 5,85 (5) | 10,3 | **24,1** | 10,8 min | **5,0 h** |
| `histoire_doc` | 4,5 (5) | 13,3 | **31,3** | 25,2 min | **14,8 h** |

**Trois conséquences, et la troisième est un avertissement.**

1. **L'hypothèse « 12 plans/min » de RESULTATS § 2.6 est plus chère que toutes les
   niches mesurées sauf une.** Seule `histoire_doc` (4,5 s) la dépasse — et c'est
   justement celle qui doit tourner en banques.
2. **Le style se choisit avec la niche.** Coupe lente (`spiritualite`, `true_crime`) →
   images générées tenables. Coupe rapide (`histoire_doc`, `home_hacks`) → banques de
   vidéos libres ou motion design, sinon le coût explose.
3. **La capacité de 7 vidéos/semaine de RESULTATS § 2.7 repose sur une vidéo de
   10 minutes. Les durées médianes du registre sont de 18 à 31 minutes.** Avec le
   diviseur de § 2.7 — **une vidéo par nuit de machine, soit 8 à 10 h, hypothèse non
   mesurée** — cela donne : **7 vidéos par semaine** pour `true_crime`, `science_pop`,
   `home_hacks` et, sans aucune marge, `spiritualite` (8,4 h) ; **3 à 4 seulement**
   pour `histoire_doc` (14,8 h, deux nuits). **Dans tous les cas, 10 vidéos par
   semaine ne sont pas atteignables en images générées sur cette machine.** À porter
   au dimensionnement du portefeuille (étape 24) et à la question ouverte n° 7 d'Alek.

---

## 4. Ce qu'un spectateur perçoit — et dans quel ordre

### 4.1 Avant les 5 secondes : la miniature et le titre

Ce sont le seul contact avant la vidéo, et **aucune ligne de la matrice ne les
couvre** : ce ne sont pas des styles. Ce qui est mesuré : le moteur de miniatures
(Playwright HTML→PNG, **0,20 s**, seuil ≤ 3 s), un échantillon
`benchmarks/samples/visuel/miniature_1280x720.png` **jamais noté**, et les cibles par
niche du registre (mots de texte, part de visage, palette, contraste, composition —
`REFERENTIEL.md` § 4). Le détourage `rembg` n'a **pas** été mesuré. C'est l'étape 21
qui porte ce sujet, et il décide si les 5 secondes suivantes ont lieu.

### 4.2 Les 5 premières secondes : l'image

Jugé sur `benchmarks/samples/visuel/coherence8/plan_08.png` **ouvert en pleine
résolution** (1280×720), pas sur une planche de contact — l'erreur de méthode de
l'étape 5.2 n'est pas répétée.

- **Ce qui est bon, et se voit d'abord** : aplats francs, palette tenue, composition
  lisible, texture de papier. À l'échelle d'un plan de 5 s, l'image passe pour un
  travail d'illustrateur.
- **Ce qui se voit ensuite, et ne pardonne pas** : le personnage n'est pas le même
  qu'aux sept plans précédents (femme aux cheveux longs → coupe courte), et **la
  chevelure précédente subsiste en mèche détachée**, séparée de la tête par un vide de
  17 px. Un spectateur ne nommera pas le défaut ; il verra que « ça change » d'un plan
  à l'autre.
- **Le pied arrière est retourné** : la marche va vers la droite, la pointe de la
  chaussure arrière regarde à gauche.
- **Les quatre plans sans anatomie humaine** de la même série (un cerveau, un réveil,
  des ondes, une tasse) **ne portent aucun de ces défauts.**

**Le risque n'est pas réparti sur l'image : il est concentré dans le corps humain en
pied et en mouvement.** C'est ce qui fonde l'arbitrage du § 5.

### 4.3 Les 5 premières secondes : le son, qui arrive avant l'image

Un spectateur juge une voix off plus vite qu'un plan, et trois faits mesurés
l'exposent — aucun n'est réglé par le choix d'un style :

- **Aucune voix française native.** Les 9 préréglages de Qwen3-TTS n'en comptent pas ;
  le cross-lingual est un pis-aller. Jugement de Thomas : « plutôt bonnes », **sans
  note chiffrée**, et 7 locuteurs sur 9 ne sont pas essayés. L'exigence « ≥ 2 voix par
  langue » n'est **ni confirmée ni infirmée**.
- **Aucune musique disponible aujourd'hui.** ACE-Step pèse ~10,1 Go (hors budget) et
  l'inventaire de l'Audio Library exige un compte de chaîne — question ouverte n° 1
  pour Alek. **En l'état, une vidéo sortirait sans musique de fond**, ce qui s'entend
  en 5 secondes sur une chaîne faceless.
- **Les sous-titres peuvent perdre un tiers d'une vidéo.** parakeet tronque 2 fichiers
  sur 8 de façon reproductible (couverture 0,62 et 0,66), cause inconnue. À traiter
  avant l'étape 11, avec bascule sur whisper sous un seuil de couverture.

Le niveau sonore mesuré (-21,8 à -28,7 LUFS contre -14 visés) n'est **pas** un défaut :
c'est une normalisation de rendu (`ffmpeg loudnorm`).

---

## 5. Les trois voies de la relecture — tranchées

`RESULTATS.md` § 2.12 a établi, mesures à l'appui, qu'**aucun contrôle automatique
n'est atteignable** ici pour l'anatomie, les éléments détachés et la dérive
d'identité : sur ces 8 plans, 3 séparations légitimes sur 13 tombent dans la même
fourchette de 10-25 px que la mèche fautive. Il faudrait un modèle vision-langage ;
aucun ne tient dans 22 Go et une API payante romprait le 0 €. Trois voies étaient
posées, à trancher ici.

**Voie 0, ajoutée par Thomas le 15/09/2026 — corriger le prompt avant tout le
reste.** *« Pour le personnage je pense que ça se règle avec des correctifs, des
meilleurs prompts. »* C'est cohérent avec la mesure : la dérive de tenue vient d'un mot
ambigu (« flannel » désigne une matière, pas un motif, § 2.3 de RESULTATS), et
`RESULTATS.md` § 2.11 conclut que **tout ce qui décrit le personnage doit être figé,
coiffure comprise**. Le gabarit de prompt et la fiche de personnage de l'étape 12.2
sont donc la **première** ligne de défense, pas la dernière.
**Ce que cette voie ne couvre pas, et qu'il faut garder en tête** : elle agit sur ce
qui est *décrit* — identité, coiffure, tenue, cadrage. Les deux autres défauts du
`plan_08` — **mèche détachée et pied retourné** — sont des accidents
d'échantillonnage, pas des descriptions manquantes. Aucune mesure ne dit qu'un prompt
les supprime. **Les voies ci-dessous restent donc nécessaires, et leur poids se
réévalue à l'étape 12.2 quand le taux de défaut après correctifs sera connu.**

**Voie 3 — réduire l'exposition par le choix de sujet : RETENUE.** C'est la règle de
la charte de l'étape 12.2.
- Personnages **cadrés en buste**, jamais en pied en mouvement.
- Priorité aux **objets, lieux, schémas et abstractions**.
- Preuve : les 4 plans sans anatomie humaine de la série mesurée sont indemnes.
- Coût : **nul**. C'est une contrainte de rédaction des intentions visuelles.

**Voie 1 — relecture humaine plan par plan : REFUSÉE comme régime, RETENUE comme
contrôle ciblé.** À 120 plans par vidéo et 7 vidéos par semaine, 840 plans
hebdomadaires heurtent de front la contrainte 3 de `ROADMAP.md` § 3.4. Mais la
relecture n'a pas à être aveugle : **c'est nous qui écrivons l'intention de chaque
plan**, donc nous savons sans aucun détecteur lesquels contiennent une silhouette
humaine. Règle retenue : **relecture en pleine résolution des seuls plans à
personnage**, que la charte (voie 3) maintient minoritaires. Le drapeau est gratuit,
il est posé par la liste de plans de l'étape 12.1.

**Voie 2 — juge VLM sur le serveur : RETENUE pour la phase serveur.** Elle se confond
avec le sélecteur de RESULTATS § 2.9 : générer 4 images pour n'en garder qu'une
**suppose un juge, et ce juge doit voir**. C'est la seule chose que le serveur achète
au-delà du débit et de la précision : non pas moins de défauts, mais la capacité de
les **détecter**.

**Ce que cet arbitrage retire de la promesse d'autonomie**, et qu'il faut écrire : le
pipeline reste automatique de bout en bout ; **les plans à personnage attendent un avis
humain avant montage**. C'est une file, pas un plan-par-plan universel. Et c'est dit à
Alek au § 9, pas seulement ici.

---

## 6. Ordre d'implémentation des moteurs

Ordre prévu par la feuille de route : cartes (12.1) → illustré (12.2) → documentaire
(17) → avatar 2D (29) → motion design (30.1) → whiteboard (30.2).
**Deux déplacements, tous deux imposés par des mesures.**

| # | Moteur | Étape | Phase | Pourquoi ici |
|---|---|---|---|---|
| 1 | **Cartes** | 12.1 | 1 | Inchangé. Porte le découpage en plans et l'interface `StyleEngine` : tout en dépend. Usage interne (§ 8) |
| 2 | **Illustré animé** | 12.2 | 1 | Inchangé. La contrainte 7 de `ROADMAP.md` § 3.4 exige une vidéo complète en fin de phase 1, et c'est le seul moteur dont l'image **et** le mouvement ont été produits et vus. Il hérite de trois obligations : charte de cadrage (§ 5), gabarit de personnage sans ambiguïté (tenue **et coiffure**), **mesure du taux de réutilisation de bibliothèque** — qui est supposé faire tomber les 137 s par plan et n'est pas encore un fait |
| 3 | **Motion design** | 30.1 | **6 → 2** | **Déplacé.** Trois raisons : (a) c'est le seul moteur qui n'achète pas ses visuels à FLUX — à 1 fond généré par minute son coût visuel projeté est de **2,7 min/min contre 19,7 à 32,8** pour les moteurs d'images, seule sortie connue du goulot des 84 % ; (b) c'est le format de la chaîne la plus performante du registre ; (c) il ne génère **aucune anatomie humaine**, donc il échappe entièrement au défaut du § 4.2. Le laisser en phase 6 revenait à livrer en dernier le style le moins cher et le mieux référencé. Ses dépendances (15 et 7) sont satisfaites en phase 2 |
| 4 | **Documentaire** | 17 | 2 | Inchangé. Coût de génération nul, aucune anatomie générée, **seule route tenable pour les niches à coupe rapide** (§ 3.1). Sa qualité n'est pas mesurée : réserve au § 7 |
| 5 | **Whiteboard** | 30.2 | 6 | Inchangé, et toujours après 30.1 : l'animation `stroke-dashoffset` est rendue par Revideo |
| 6 | **Avatar 2D** | 29 | 6 | **Déplacé en dernier** (il était 4ᵉ). Motif : c'est le moteur dont **le moins de choses ont été vues**. Les visèmes sont mesurés (6,2 s, 309 visèmes) mais jamais entendus, et **aucun avatar animé n'a jamais été rendu** ; le whiteboard, lui, a un MP4 noté 4/5 par Thomas. **On ordonne par preuve disponible.** L'étape 29 porte aussi la bibliothèque d'assets, qui bénéficie des mesures de réutilisation de 12.2 |

**Ce que ce classement ne change pas** : la phase 1 livre toujours une vidéo complète
en illustré. Ce que le client verra au lancement des chaînes, en revanche, ce sont les
trois moteurs disponibles à la fin de la phase 2 — illustré, documentaire, motion
design. C'est exactement ce que propose le § 9, et rien de plus.

---

## 7. Réserves de mesure attachées aux statuts

**Quatre styles étaient retenus sans preuve visuelle** (documentaire, réaliste par
banques, motion design au-delà d'un fond, avatar 2D), portés par **trois moteurs**.
**Le motion design en est sorti le 16/09/2026** : trois séquences de 32 s sont
rendues, mesurées et versées à `benchmarks/preuve_motion/`. **Il en reste trois.**
Ce n'est défendable que si la mesure qui manque est nommée, chiffrée, et que la
conséquence d'un échec est écrite d'avance. Aucune date calendaire n'est donnée : le
projet est ordonné par étapes, pas par dates.

| Style | Ce qui manque | Seuil de décision | Où | Si le seuil tombe |
|---|---|---|---|---|
| **Documentaire et réaliste par banques** | aucun plan récupéré, aucun montage, aucune mesure de pertinence | **≥ 3 plans pertinents pour 20 intentions visuelles** tirées d'un script réel, licences enregistrées, et un montage de 60 s vu et noté ≥ 3/5 | étape 17 | **il n'y a pas de repli utilisable.** L'illustré coûte 20,4 à 31,3 min/min sur les niches à coupe rapide, que le § 3.1 déclare intenables. La conséquence réelle est de **ne pas ouvrir ces niches** et de se replier sur les niches à coupe lente |
| **Motion design** | ~~aucune séquence rendue~~ — **trois séquences de 32 s existent depuis le 16/09** (`benchmarks/preuve_motion/`). Ce qui manque encore : **la note en lecture**, et **la fabrication automatique d'un schéma animé** à partir d'un script quelconque | **une séquence de 30 s** avec images, formes et texte animés, rendue en headless, **≥ 2 img/s**, vue et notée ≥ 3/5 | étape 30.1 | **seuil mesurable tenu le 16/09** : 32,000 s, 960 images, 1920×1080, images + formes + texte animés, headless, **54,5 à 122,9 img/s — le seuil de 2 img/s est tenu 27 à 61 fois**. **Note portée par Thomas le 16/09** sur les deuxièmes versions : *« jusqu'à présent y'a que le B qui est intéressant »* — **le seuil ≥ 3/5 est tenu par le schéma animé seul**. La typographie cinétique et l'hybride ont été réécrits entièrement après un premier verdict négatif et **échouent une seconde fois** ; les motifs sont nommés : pour l'hybride *« des images qui se découpent… pas cohérent visuellement »*, pour la typographie *« trop de texte, presque aucune image, aucune animation »* — c'est-à-dire sa prémisse même. **Constat unifiant : ce qui est perçu comme animation est la construction et la transformation, jamais le déplacement.** Même reproche que celui fait aux 127 plans de l'étape 12.2, appliqué cette fois au texte et aux fragments d'image. Le repli MoviePy + Manim **n'a pas été employé** : Revideo s'installe et rend sur Apple Silicon. **Le § 9 n'est pas invalidé** — mais il reste à dire si la promesse porte sur le style (démontré) ou sur sa fabrication automatique (non démontrée) |
| **Avatar 2D** | aucun avatar animé produit ; visèmes jamais entendus | **30 s de personnage parlant**, synchronisation notée ≥ 3/5 à l'écoute | étape 29 | repli réel : MFA + OpenFaceFX, **mêmes sprites de bouche**, format de sortie identique. C'est le seul repli de ce tableau qui en soit un |
| **Illustré** (retenu v1, avec preuve) | taux de réutilisation de bibliothèque supposé, non mesuré | **taux de réutilisation mesuré** sur 10 scripts réels | étape 12.2 | aucun repli n'est requis : c'est le coût qui reste à 137 s par plan, pas le style qui tombe |

---

## 8. Risques de conformité par style

Trois axes : la **variation** possible (la politique « contenu inauthentique » du
15/07/2025 vise les gabarits génériques et les diaporamas), la **signature humaine**
(`CONFORMITE.md` § 4), et les **étiquettes** dues.

| Style | Variation possible | Étiquettes dues | Risque principal |
|---|---|---|---|
| **Illustré** | **forte** — une image neuve par intention, jamais un gabarit | « Images virtuelles » dès qu'un plan montre un visage ou une silhouette (loi 2023-451) · `contains_synthetic_media` = **false** (l'illustration n'est pas réaliste) | faible. Le danger serait une charte figée au point de rendre toutes les vidéos superposables |
| **Documentaire / réaliste par banques** | moyenne — dépend du fonds disponible | attributions et licences **par plan** ; aucune étiquette de synthèse | **le plus élevé de la liste.** `CONFORMITE.md` § 8 : « un diaporama de banque d'images avec voix off descriptive tombe simultanément sous *contenu réutilisé* et sous *contenu inauthentique* ». **Exige une couche originale** — analyse, données, mise en récit — et non une description de ce qu'on voit |
| **Motion design** | **forte** — chaque vidéo anime ses propres données | aucune | gabarit d'animation réutilisé tel quel d'une vidéo à l'autre. Varier structure, palette et typographie par chaîne |
| **Whiteboard** | moyenne — le format est très reconnaissable | « Images virtuelles » si un personnage est dessiné | le format signe visuellement la production en série. Variation par le contenu dessiné, pas par l'habillage |
| **Avatar 2D** | forte sur le fond, **nulle sur le personnage** (c'est le principe) | « Images virtuelles » **systématique** (silhouette) · `contains_synthetic_media` = false tant que le personnage est dessiné **et la voix non clonée** | faible, et c'est même une **défense** : un persona récurrent est le contraire d'un contenu de gabarit anonyme |
| **Réaliste généré** | forte, mais sans objet | `contains_synthetic_media` = **true**, obligatoire, posé au moment de la génération du plan · étiquetage automatique YouTube depuis 05/2026 | maximal. **Et l'exception éditoriale du RIA art. 50 ne couvre pas la vidéo** — elle est attachée aux textes d'intérêt public. Nommer un relecteur ne préserve aucune exception ici : c'est la règle YouTube qui gouverne |
| **Cartes** | **faible** — texte sur fond uni | aucune | **le plus exposé de tous** : « scrolling text with minimal or no narrative » est littéralement le cas visé par la politique. **Moteur d'amorçage interne, jamais publié tel quel** |

**Commun à tous les styles** : relecture humaine tracée (`CONFORMITE.md` § 4), case
« promotion payante » **non écrivable par l'API** — aucune chaîne affiliée n'est
100 % automatique — et bandeau « Publicité » incrusté pendant tout segment promotionnel.

---

## 9. Message à Alek

*Mise en forme WhatsApp (`*gras*`, ni titres ni tableaux), **20 lignes non vides**,
805 mots. **Thomas décide de l'envoi.** Texte brut, identique à ce bloc et vérifié par
`diff` : `docs/message-alek-whatsapp.txt`. **Relu par un sous-agent vérificateur le
15/09/2026, chiffre par chiffre contre les sources** — 6 corrections appliquées, § 9.2.
**Réécrit le 18/09/2026** — trois affirmations étaient devenues fausses, § 9.3.*

> Salut Alek,
>
> On a tranché les 7 styles que tu voulais, mesures à l'appui. Résultat : *6 styles utilisables*, portés par 5 moteurs.
>
> 1. Illustration animée (images générées + mouvement de caméra)
> 2. Motion design
> 3. Documentaire (archives, images d'illustration)
> 4. Réaliste — vrais plans filmés, banques libres de droits
> 5. Whiteboard animé
> 6. Avatar 2D qui parle
>
> *Où on en est vraiment, style par style* : un seul a été produit en vidéo complète et regardé de bout en bout — l'illustration animée. Les 5 autres n'ont été vus que sur des extraits de quelques secondes, et je ne les compte pas comme validés tant qu'ils n'ont pas tourné sur 10 minutes. L'avatar 2D se pose par-dessus les autres styles, donc ça fait plus de rendus différents que 6 — et la vraie variété vient de la charte de chaque chaîne (palette, typo, rythme de coupe) : deux chaînes dans le même style ne se ressemblent pas.
>
> *Le 7e, les animations poussées, je l'abandonne.* C'est du travail d'animateur à la main, pas une question de puissance : CasiCreativo, ta référence, en fait — et publie 57 vidéos en 5 ans. On ne tiendra pas ce niveau à 2 vidéos par semaine, et aucun serveur n'y change quoi que ce soit.
>
> *Ce qu'on ne fait pas* : la vidéo réaliste générée par IA. Preuve plutôt qu'avis — 4 secondes en très basse résolution ont pris 7 minutes de calcul, avec des traces de filigrane dans l'image. Une minute coûterait 1h49, contre 20 à 33 minutes selon le style en images fixes. Ce n'est pas un réglage qu'on aurait raté, c'est une classe de matériel qu'on n'a pas. Sur le serveur on pourra en insérer des plans de 3-4 secondes en habillage, jamais une vidéo entière. Et regarde tes propres références : aucune n'en a besoin — CasiCreativo c'est du motion design, les 3 bibliothèques de Thoth (398, 324 et 241 vidéos) tournent sur de la voix off, Elias Yoder c'est 358 000 abonnés en 4 mois avec un personnage récurrent.
>
> *La démo est faite, et je te dis aussi ce qui cloche.* Le système a produit une vidéo entière tout seul : sujet, recherche, texte, voix, sous-titres, 124 plans, miniature, description. 12 minutes, 2h23 de calcul, zéro intervention. Et trois défauts que j'ai mesurés plutôt que devinés : elle ne montrait que 36 images différentes sur 12 minutes — l'une d'elles revenait 22 fois — la voix ne s'arrête jamais de parler (pas un silence en 12 minutes), et les images décorent au lieu d'expliquer. Le premier défaut était un bug, il est corrigé : on passe à 67 images. Les deux autres sont du réglage éditorial, c'est la suite du travail.
>
> *Un défaut que je te dis tout de suite* : sur une série de 8 plans, le 8e a changé le personnage. Ça se corrige en grande partie au texte qu'on donne au modèle ; pour le reste, on fait relire à l'œil les seuls plans qui montrent quelqu'un.
>
> *Volume* : tout tourne sur mon MacBook Air M2 16 Go, qui est aussi ma machine de travail. Une vidéo de 12 minutes coûte 2h23 de calcul — et la correction ci-dessus la fait passer à environ 3h15. Sur cette seule mesure je table sur 3 à 5 vidéos par semaine, pas 7, et je te redonne le chiffre quand j'en aurai produit plusieurs d'affilée. 10, non.
>
> *Le serveur* : on part sur les ~50 €/mois que tu as validés, mais la machine n'est pas choisie. Je regarde ce que ce budget achète vraiment et je te donne les chiffres avant qu'on engage. Il servira soit à produire plus, soit à faire de plus belles images — pas les deux à fond, c'est le même calcul. En revanche il ne donnera pas une voix française plus naturelle : ça, c'est une question de données d'entraînement, pas de puissance.
>
> *La suite* : une démo par style, en commençant par le documentaire — c'est le seul qui met à l'écran des plans qui bougent vraiment. Et surtout j'ouvre le dossier de publication : c'est le vrai chemin critique. YouTube force en privé tout ce qui sort d'un projet développeur non audité, et l'audit prend des semaines à des mois. Le code qui publie est écrit et testé ; ce qui manque, ce sont les comptes — d'où ma demande ci-dessous.
>
> *Il me faut 2 choses de ta part* :
> — raison sociale, SIREN et adresse de BMS (c'est obligatoire pour déposer le dossier d'audit : il faut une politique de confidentialité en ligne avec le nom de la société dessus)
> — les comptes Google sous lesquels les chaînes doivent vivre (ça débloque aussi la banque de musique de YouTube, sans laquelle nos vidéos sortent sans musique de fond — c'est le cas de la démo)
>
> Thomas

### 9.1 Ce que le message engage, ligne par ligne

**« 6 styles utilisables, 5 moteurs ».** Illustré animé (12.2) · motion design (30.1)
· documentaire et réaliste par banques (17, **un seul moteur, deux configurations**) ·
whiteboard (30.2) · avatar 2D (29). Les cartes (12.1) n'y figurent pas : moteur
d'amorçage interne, jamais publié seul (§ 8). Le réaliste généré non plus : serveur
seulement. **Sur les 7 styles demandés par Alek : 5 livrés tels quels, 1 scindé et
livré à moitié (le réaliste), 1 abandonné.**

**« L'avatar se pose par-dessus les autres ».** C'est le format d'Elias Yoder
(`variantes_style.avatar`) et c'est ce que prévoit l'architecture. **Non mesuré** :
aucun avatar n'a jamais été rendu. Le message dit « ça fait plus de rendus
différents », pas un chiffre.

**« La vraie variété vient de la charte ».** `chaîne = langue + niche + style + voix +
charte` (`ROADMAP.md` § 3.4, contrainte 4). C'est aussi la réponse au vrai risque : la
politique « contenu inauthentique » vise les gabarits génériques, pas le nombre de
moteurs (§ 8). **Ajouter un 7ᵉ moteur n'y change rien ; varier les chartes, si.**

**« Entre 3 et 7 vidéos par semaine selon le format ».** § 3.1 : 7 sur les niches à
coupe lente, 3 à 4 sur `histoire_doc` (14,8 h par vidéo, deux nuits). Le message ne
promet pas 7 partout.

**« Une vidéo de démo complète ».** Livrable `final.mp4` de l'**étape 13.2**, fin de
phase 1 (`ROADMAP.md` § 3.4, contrainte 7). **Une seule vidéo, en illustré** — seul
moteur retenu v1. Les démos par style suivent en phase 2.

**Les deux demandes finales** sont les questions ouvertes **n° 2** (raison sociale,
SIREN, adresse) et **n° 1** (comptes Google), toutes deux dues avant l'étape 14.

### 9.2 Vérification avant envoi — 6 corrections

Un sous-agent vérificateur a repris **chaque chiffre et chaque affirmation** du message
contre `RESULTATS.md`, `REFERENTIEL.json`, `TRAJECTOIRES.md`, `ROADMAP.md` et
`CONFORMITE.md`, en refaisant les calculs. Résultat : **les 11 chiffres tiennent**,
**6 formulations ne tenaient pas.**

| Ce qui était écrit | Pourquoi ça ne tenait pas | Corrigé en |
|---|---|---|
| « 20 à 33 minutes **en illustré** » | 19,7 à 32,8 est l'éventail de **quatre styles d'image** ; l'illustré seul vaut 30,7. La borne basse (documentaire, 94,6 s/image) n'est pas l'illustré | « 20 à 33 minutes **selon le style** en images fixes » |
| « L'avatar se pose par-dessus les autres, **comme Elias Yoder** » | **Le plus grave.** Le registre décrit cette variante comme « montage mixte **photo réelle du visage** + insert graphique » (`REFERENTIEL.json`), et l'autre chaîne du même format emploie un **acteur payé**. Rien n'établit un avatar **dessiné**. Notre avatar est en calques CC0 | la comparaison est **retirée** ; Elias Yoder n'est plus cité que pour ses chiffres d'audience |
| « Higgsfield tourne sur des cartes graphiques de datacenter » | **Aucune source dans le dépôt.** Le seul élément est la phrase de Thomas à Alek : « jamais au niveau de Higgsfield » | « ce n'est pas un réglage qu'on aurait raté, c'est **une classe de matériel qu'on n'a pas** » — même conclusion, sans affirmer ce qu'on ignore |
| « les 3 bibliothèques de Thoth c'est **images fixes** + voix off » · « Zéro photoréalisme » | **Aucune vidéo tierce n'a jamais été visionnée** (`CLAUDE.md` règle 11) : on ne peut pas affirmer ce que ces chaînes montrent. Seul le nombre de vidéos est mesuré | « les 3 bibliothèques de Thoth (**398, 324 et 241 vidéos**) tournent sur de la voix off » · et « **regarde tes propres références : aucune n'en a besoin** » — une invitation à vérifier, pas une affirmation à notre charge |
| « une vidéo de démo … **sans que je touche un seul plan** » | **Contradiction interne** : trois paragraphes plus haut, le message annonce une relecture humaine des plans à personnage — et la démo est en illustré, le seul moteur à personnages | « une vidéo de démo complète, **de l'idée à la miniature**, produite par le système » |
| « Ça se corrige **surtout** au texte qu'on donne au modèle » | Surévalué : la voie prompt ne couvre ni la mèche détachée ni le pied retourné (§ 5), et aucune mesure ne dit qu'un prompt les supprime | « **en grande partie** au texte … ; **pour le reste**, on fait relire à l'œil » |

**Trois manques signalés par le vérificateur et comblés** : le 7ᵉ style (« animations
poussées ») n'était **jamais nommé** alors qu'Alek l'avait demandé — il l'est
maintenant, avec son motif · **4 des 6 styles n'ont aucun rendu complet** — le message
le dit désormais et nomme les 2 qui sont validés · le réaliste généré **reste
disponible en b-roll sur serveur**, ce que le refus sec ne laissait pas entendre.

**Un manque comblé de notre initiative** : les comptes Google demandés à Alek
débloquent **aussi** la bibliothèque musicale de YouTube, seule source de musique
accessible au projet (`RESULTATS.md` § 1.4). Sans elle, une vidéo sortirait **sans
musique de fond**. C'est écrit dans la demande, pour qu'elle ait une raison d'être
traitée vite.

**Ce que le vérificateur a signalé et qui n'entre pas dans ce message**, mais devra
être dit à Alek avant les étapes concernées : le documentaire porte **le risque de
conformité le plus élevé** et exige une couche originale (§ 8, étape 17) · **aucune
chaîne affiliée ne pourra être 100 % automatique**, la case « promotion payante »
n'étant pas écrivable par l'API (étape 23.1) · il n'existe **aucune voix française
native** dans les modèles gratuits, ce que le message dit, et **aucune musique** tant
que les comptes ne sont pas ouverts.


### 9.3 Réécriture du 18/09/2026 — trois affirmations devenues fausses

Le message du 15/09 avait été vérifié chiffre par chiffre (§ 9.2). **Ce ne sont pas ses chiffres
qui ont vieilli, ce sont trois de ses affirmations** : les étapes 12.2, 13.1 et 13.2 ont produit
des faits qui les contredisent. Envoyé tel quel, il aurait annoncé à un client des validations
qui n'existent pas.

| Ce que disait le message | Pourquoi c'était devenu faux | Ce qu'il dit maintenant |
|---|---|---|
| *« Deux sont déjà validés sur des rendus que j'ai vus (illustration animée, whiteboard) »* | **Aucun des deux ne l'était.** L'illustration animée a été **rejetée** par Thomas le 16/09 dans sa version parallaxe (« c'est pas un style, c'est juste de la merde ») ; sa version Ken Burns n'a reçu qu'un « ça va c'est bien […] mais je pense que ça sera le thème le moins intéressant de tous », et `docs/DEFAUTS.md` y mesure trois défauts. Le whiteboard n'a **jamais** été vu en vidéo : sa note vient du banc de l'étape 5.2, dont la fonction de rendu portait le défaut `-loop 1` (clips sortis à 0,033 s). | *« Un seul a été produit en vidéo complète et regardé de bout en bout — l'illustration animée. Les 5 autres n'ont été vus que sur des extraits de quelques secondes, et je ne les compte pas comme validés tant qu'ils n'ont pas tourné sur 10 minutes. »* |
| *« La suite : prochain objectif, une vidéo de démo complète »* | **Elle est faite** — run `bms-science-fr-20260917-rtmk`, 17/09, 2 h 23, zéro intervention. Annoncer comme objectif ce qui est livré fait perdre le bénéfice du jalon. | Un paragraphe *« La démo est faite, et je te dis aussi ce qui cloche »* qui donne le résultat **et les trois défauts mesurés**. Le § « La suite » passe à la démo par style et au dossier de publication. |
| *« Entre 3 et 7 vidéos par semaine environ selon le format »* | La fourchette datait d'avant l'existence du moteur illustré. La seule mesure de bout en bout donne **2 h 23** pour 12 minutes, et la correction du 18/09 (67 images au lieu de 36) porte le coût à **≈ 3 h 15**. 7 par semaine supposerait ~22 h de calcul hebdomadaire sur une machine qui est aussi son poste de travail. | *« 3 à 5 vidéos par semaine, pas 7 »*, adossé à la mesure, avec la promesse explicite de redonner le chiffre après plusieurs vidéos d'affilée. |

**Deux ajouts de fond**, tirés de l'étape 14 : la demande de raison sociale est désormais
**justifiée** (elle conditionne la politique de confidentialité en ligne, donc le dépôt de
l'audit), et l'état du chemin de publication est dit tel qu'il est — *« le code qui publie est
écrit et testé ; ce qui manque, ce sont les comptes »*. La mention de la musique gagne
« c'est le cas de la démo » : la première vidéo est **réellement** sortie sans musique.

**Ce qui n'a pas bougé** : les 6 styles, l'abandon des animations poussées, le refus de la vidéo
réaliste générée, la dérive de personnage, le budget serveur, et les deux demandes à Alek. Les
chiffres vérifiés au § 9.2 sont conservés mot pour mot.

---

## 10. Objections du contradicteur

> **À lire avant le tableau.** Ces objections ont été traitées sur la **version longue**
> du message (10 paragraphes). Le message a ensuite été **raccourci pour WhatsApp** à la
> demande de Thomas. Les trois lignes concernées (2, 11, 16) disent ci-dessous ce qui
> vaut pour la version courte, qui est la seule en vigueur.

Un sous-agent contradicteur a relu `docs/STYLES.md` et `benchmarks/RESULTATS.md`, avec
accès aux sources (`REFERENTIEL.md`, `TRAJECTOIRES.md`, `SELECTION.md`,
`CONFORMITE.md`, `STATE.md`). **18 objections : 17 retenues et corrigées, 1 refusée
sur preuve.**

| # | Gravité | Objection | Traitement |
|---|---|---|---|
| 1 | bloquant | § 1.1 annonçait « les deux fichiers sont corrigés » alors que `RESULTATS.md` § 2.5 portait toujours « 1 à 300 » et « un neuvième » | **corrigé** — les deux fichiers sont réellement modifiés, avec l'encadré de correction |
| 2 | bloquant | Le message disait « on a mesuré les sept styles un par un » quand la matrice dit « non mesuré » sur trois lignes | **corrigé** — la version courte dit « **on a tranché les 7 styles, mesures à l'appui** ». *Le premier jet de la version WhatsApp avait réintroduit « on a testé les 7 styles » : même faute, rattrapée à la relecture.* |
| 3 | bloquant | « Elias Yoder, 345 000 vues » ne correspond à aucune mesure : `TRAJECTOIRES.md` § 2 donne 358 000 abonnés et 259 057 vues médianes | **corrigé** — les deux chiffres mesurés remplacent le 345 K, et son origine (PDF périmé) est consignée au § 3 |
| 4 | bloquant | « 82 minutes pour 2 secondes sur un Mac à 64 Go » n'aurait aucune source dans le dépôt | **refusé sur preuve** — la source est `ROADMAP.md` § 3.5 (« Wan 2.2 GGUF : 82 min pour 2 s sur M1 Max 64 Go ») et le chiffre est repris au registre des risques, `ROADMAP.md` étape 31. Le contradicteur a cherché dans `SELECTION.md`, où figure une autre mesure (31,7 s par image). **Conservé**, avec sa nature de veille assumée |
| 5 | bloquant | « 3 chaînes à 2 vidéos par semaine » contredisait le § 3.1 et ignorait la cible de 10/semaine | **corrigé** — le message annonce 7/semaine, 3 à 4 sur les niches à coupe rapide, et dit explicitement que 10 ne passent pas en local |
| 6 | bloquant | Le message taisait la cohérence sur 8 plans **non tenue** et la file de relecture humaine | **corrigé** — un paragraphe entier y est consacré, avec la parade et son coût |
| 7 | sérieux | « 11,4 s par plan mesurées sur 14 chaînes » : c'est n = 6, et aucune chaîne Thoth n'est dans les rythmes mesurés | **corrigé** — n = 6 affiché, et la réserve « Thoth non mesuré » écrite au § 3 |
| 8 | sérieux | Yoder donné à 4,1 s/plan au § 3 et à 6,9 s au § 3.1 sous la même étiquette | **corrigé** — l'étiquette « (Yoder) » est retirée du tableau, qui porte des médianes de niche |
| 9 | sérieux | « 3 à 5 vidéos/semaine » n'était pas dérivable du diviseur de RESULTATS § 2.7 | **corrigé** — le diviseur (une nuit = 8 à 10 h, hypothèse non mesurée) est écrit, et le résultat recalculé niche par niche |
| 10 | sérieux | La remontée du motion design s'appuyait sur « 0,3 min/min », déjà compté dans les postes communs | **corrigé** — la comparaison porte désormais sur 2,7 (1 fond/min, projection) contre 19,7 à 32,8 |
| 11 | sérieux | Les notes 4,6 et 4,7/5 sont des notes de la session, et une note de session s'est déjà révélée fausse | **corrigé** — chaque note de la matrice porte *(Thomas)* ou *(session)*. **La version courte du message ne cite plus aucune note chiffrée** : l'objection tombe d'elle-même |
| 12 | sérieux | Les replis du § 7 n'en étaient pas : l'illustré est déclaré intenable là où il sert de repli, MoviePy+Manim n'est pas le niveau visé | **corrigé** — la colonne s'appelle « si le seuil tombe » et écrit la conséquence réelle, y compris « ne pas ouvrir ces niches » et « reprendre le message auprès d'Alek » |
| 13 | sérieux | § 7 promettait des conditions « datées » sans aucune date | **corrigé** — la promesse de date est retirée (le projet est ordonné par étapes), et « sous réserve de mesure » est porté dans la colonne Statut de la matrice |
| 14 | sérieux | Le § sur les 5 secondes ne disait rien du son, que le spectateur juge en premier | **corrigé** — § 4.3 : aucune voix FR native, **aucune musique disponible**, sous-titres tronqués sur 2 fichiers sur 8 |
| 15 | sérieux | Rien sur la miniature ni le titre, seul contact avant les 5 secondes | **corrigé** — § 4.1, avec ce qui est mesuré (0,20 s) et ce qui ne l'est pas (la miniature elle-même, le détourage `rembg`) |
| 16 | mineur | Les chemins `samples/visuel/…` n'existent pas depuis la racine | **corrigé** — les 12 chemins sont préfixés `benchmarks/` et **vérifiés un par un sur le disque**. La version courte du message n'invite plus Alek à les ouvrir, mais ils servent à Thomas |
| 17 | mineur | La voix retenue à 3,3 est le facteur anglais ; le français est 3,373. Et « ≈ 3,0 » pour le motion design valait 2,7 | **corrigé** — 3,4 pour la voix (commun à 3,9) et 2,7 pour le motion design |
| 18 | mineur | § 3.1 calculait sur 137 s quand le reste calcule sur 140,74 ; § 7 annonçait « deux styles » pour quatre lignes | **corrigé** — tout le § 3.1 est recalculé sur 140,74 s, et le § 7 annonce quatre styles portés par trois moteurs |

**Ce que le contradicteur n'a pas trouvé, et qui reste ouvert** : la qualité perçue du
documentaire sur banques n'a aucune preuve, et aucune quantité de relecture ne la
fabriquera. Elle se mesure à l'étape 17 ou elle ne se mesure pas.
