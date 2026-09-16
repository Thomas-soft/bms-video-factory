# Preuve motion design — trois traitements rendus

**16/09/2026. Hors feuille de route.** Décidée par Thomas après les 127 plans de
l'étape 12.2 : « ce sont des images fixes avec un effet de glissement ». Le motion
design est le style n° 2 du message à Alek (`docs/STYLES.md` § 9) et **il n'avait
jamais été rendu en séquence**. Cette session ne construit pas le moteur (c'est
l'étape 30.1) et ne touche pas à `factory/` : elle produit de quoi trancher à l'œil.

**Matière première, non modifiée** : run `workspace/runs/bms-science-fr-20260915-j7sf`
— `script.json`, `words.json` (77 mots horodatés sur la fenêtre), `voice/voice.wav`.
Fenêtre retenue : **0 → 32,000 s**, c'est-à-dire le hook (`seg_00`, 0 → 4,94) + le
premier segment (`seg_01`, 5,54 → 23,54) + les 8,5 s de `seg_02` nécessaires pour
finir sur une phrase complète (« … des glucides, des lipides et des protéines. »,
dernier mot à 31,66 s). **Les trois séquences portent exactement le même texte et la
même voix.** Palette, polices et cadrage viennent de
`config/channels/bms-science-fr.yaml` (charte `2026.09.1-fr`) ; aucun choix libre.

---

## 0. Verdict de Thomas sur la première version, et ce qui a été refait

**16/09/2026, après visionnage :** « Motion B ça commence à être intéressant, par contre
A et C c'est très nul, non professionnel et ennuyant visuellement. »

Le verdict portait sur l'exécution, pas sur les styles — et les causes étaient
identifiables :

- **A** répétait **un seul dispositif vingt fois** : un bloc de mots centré, même taille,
  même entrée, même sortie, même fond. Aucun contraste d'échelle, aucune composition
  hors-centre, aucune rupture de couleur, aucun mouvement de caméra, une seule sorte de
  transition. C'était de l'affichage de sous-titres, pas de la typographie cinétique.
- **C** était pire : l'image était posée en plein cadre, dérivait de 4 % et attendait,
  pendant qu'un bandeau de sous-titres karaoké tenait lieu de mouvement. **C'est le
  reproche fait à l'étape 12.2, en pire**, puisqu'il n'y avait même plus de parallaxe.
  Deuxième erreur : un dispositif d'**accessibilité** avait été pris pour un dispositif
  de **motion design**.

**A et C ont été entièrement réécrits** (v2 ci-dessous). **B n'a pas été retouché** :
« commence à être intéressant » n'est pas « fini », mais la session a fait porter l'effort
sur ce qui était jugé nul.

**Trois défauts de mise en œuvre trouvés en réécrivant, tous confirmés à l'image :**

1. **Le texte aligné sortait du cadre.** Le volet de révélation clippe sur 2100 px de
   large et le mot était posé à ±1040, alors que le cadre s'arrête à ±960 : 80 px hors
   champ, aggravés par le zoom de caméra. Tous les plans alignés étaient rognés.
2. **Un `.map()` qui rend un fragment `<>…</>` n'est pas monté.** Tout le plan 3 de A —
   la colonne « LE SUCRE DE TABLE » et ses quatre filets — était absent de l'image sans
   la moindre erreur au journal. Deux `.map()` séparés règlent la question.
3. **Animer la largeur d'un `Rect` déplace son centre, donc son enfant.** Le texte
   « PRÉCISION BIOLOGIQUE » glissait pendant que son masque s'ouvrait. On compense le
   demi-déplacement, ou — règle retenue pour C — **on n'anime jamais la largeur d'une
   fenêtre : on révèle par volets et on fait vivre le cadrage à l'intérieur.**

---

## 1. Ce qui est produit

| Fichier | Traitement | Images générées | Ce qu'il met à l'épreuve |
|---|---|---|---|
| `motion_A.mp4` **(v2)** | **Typographie cinétique pure**, découpée en **huit plans** ayant chacun son parti : aplomb aligné à gauche · mot géant à 440 px sur bloc de couleur et flux binaire · colonne et contrepoint · **fond plein accent**, mot construit lettre à lettre · **fond plein jaune, texte sombre**, mot biffé · ascenseur où les mots poussent les précédents · point d'interrogation à 1 100 px et mot littéralement caché · générique en trois tiers. **Rapport d'échelle de 1 à 11** (40 à 440 px), **trois fonds pleins de couleurs différentes**, caméra mobile, cinq sortes de transition (volets, zoom brutal, flash, coupe) | **0** | le style d'ouverture de CasiCreativo et le moins cher du dispositif |
| `motion_B.mp4` | **Schéma animé** — un cristal de saccharose se construit face par face, se change en code binaire, s'ouvre en molécule (hexagone glucose + pentagone fructose reliés), se fait annoter puis casser, circule dans un vaisseau jusqu'à un cadran de régulation et une courbe de glycémie, puis l'insuline s'emboîte dans son récepteur et ouvre trois branches GLUCIDES / LIPIDES / PROTÉINES | **0** | **l'« animation d'organes » que le registre attribue à CasiCreativo.** C'est le vrai test : si B ne tient pas, la réponse à Alek est à revoir |
| `motion_C.mp4` **(v2)** | **Hybride**, où l'image est une **matière** et jamais un fond en attente : fragmentée en **trois bandes verticales qui se recollent** sur le mot « code » · recadrée dur en **médaillon** au gros plan 2,6× puis **split** plein · **répétée en grille de six** vignettes dont une seule survit · **décalée par cinq fentes** horizontales que la circulation vectorielle traverse · réduite à un **projecteur** circulaire qui se referme sur « cachée » · **split qui s'inverse** puis trois vignettes. **La fenêtre ET le cadrage à l'intérieur bougent** | **0 générée, 3 réemployées** | la bibliothèque d'images est-elle recyclable en motion design, ou faut-il la jeter ? |

Les trois PNG réemployés par C sont ceux que l'étape 12.2 avait déjà attribués aux
plans de cette fenêtre : `07b318b33e54ae0f` (cristal → binaire), `1aaf02e4a22b2f7e`
(molécules de saccharose), `7fd5881863a93362` (calories / horloge biologique).
Licence Apache-2.0, `licence.json` déjà au dépôt.

### Vérification des fichiers (`ffprobe`, comptage réel des images)

| | Résolution | ips | Images comptées | Durée | Vidéo | Audio | Poids |
|---|---|---|---|---|---|---|---|
| `motion_A.mp4` | 1920×1080 | 30/1 | **960** | **32,000 s** | h264 | aac 48 kHz stéréo | 6,4 Mo |
| `motion_B.mp4` | 1920×1080 | 30/1 | **960** | **32,000 s** | h264 | aac 48 kHz stéréo | 3,2 Mo |
| `motion_C.mp4` | 1920×1080 | 30/1 | **960** | **32,000 s** | h264 | aac 48 kHz stéréo | 8,7 Mo |

Piste voix mesurée sur `motion_A.mp4` : **-15,0 LUFS intégré, LRA 3,2 LU** sur la
fenêtre de 32 s (la piste complète du run est à -14,3 LUFS ; un extrait de 32 s n'a
aucune raison de retomber sur la même valeur). La voix est bien montée, aux trois
fichiers, par `ffmpeg` après le rendu — Revideo rend l'image seule.

---

## 2. Mesures

Machine : MacBook Air M2, 16 Go, un seul rendu à la fois, `workers: 1`. Revideo
0.11.0, Chromium headless, cache Vite chaud. Le temps donné est le **mur** —
lancement de `node` et démarrage de Vite compris, c'est ce que coûte réellement un
plan dans un pipeline. Le pic mémoire est la somme des RSS du
processus `node` et de toute sa descendance (Chromium, ffmpeg), échantillonnée
toutes les 0,4 s.

| | Mur | Images/s | **min de calcul / min de vidéo** | Pic mémoire | Coût image | Lignes |
|---|---|---|---|---|---|---|
| **A** typographie (v2) | 8,48 s | **113,2** | **0,27** | **1,10 Go** | **0** | 421 |
| **B** schéma (v1, non retouché) | 7,15 s | **134,3** | **0,22** | **1,10 Go** | **0** | 371 |
| **C** hybride (v2) | 10,50 s | **91,4** | **0,33** | **0,88 Go** | **0 générée** | 374 |

Pour mémoire, la **première version** mesurait 0,56 (A), 0,28 (B) et 0,25 (C) min/min.
**A v2 est deux fois plus rapide que A v1 tout en étant beaucoup plus riche** : les huit
plans n'existent que pendant leur fenêtre, là où la v1 gardait 77 nœuds de texte et
198 cercles de grille vivants sur les 960 images. **C v2 est le plus lent des trois**,
et c'est attendu : jusqu'à dix-neuf fenêtres d'image décodées et recadrées à la fois.
Le banc de l'étape 5.2 mesurait **98,4 img/s** sur une scène de 301 images à un seul
titre : la mesure d'aujourd'hui l'encadre (91,4 à 134,3) et **ne la contredit pas**.

**Le seuil du § 7 de `docs/STYLES.md` est « ≥ 2 img/s ». Il est tenu 27 fois (A) à
61 fois (C).** Ce seuil n'a jamais été le risque.

**Mémoire : 1,06 à 1,14 Go de pic.** Sur une machine de 16 Go, c'est un ordre de
grandeur sous FLUX.2 (11,15 Go mesurés à l'étape 12.2). Le motion design ne dispute
pas la mémoire au reste du pipeline ; **deux `workers` étaient interdits par le banc
de 5.2, cette mesure suggère que la contrainte peut être réexaminée à l'étape 30.1**
— non testé ici.

### La projection « 2,7 min/min » de `docs/STYLES.md` — corrigée

Elle était marquée « projection, non mesurée », et recomposait 1 fond généré par
minute (137 s, chiffre du banc 5.2) plus ~0,4 min/min de rendu. Les deux moitiés
peuvent maintenant être remplacées par des mesures :

| Hypothèse | Génération | Rendu (mesuré) | **Total** |
|---|---|---|---|
| **Vecteur pur** (A, B) — aucune image | 0 | 0,22 à 0,27 | **0,22 à 0,27 min/min** |
| **Hybride, 1 fond par minute**, image à 98,8 s (médiane mesurée à l'étape 12.2, 1280×720) | 1,65 | 0,33 | **1,98 min/min** |
| **Hybride, 1 fond par minute**, image à 137 s (chiffre du banc 5.2 employé par la projection) | 2,28 | 0,33 | **2,61 min/min** |
| **Hybride au rythme réel de C** (3 fonds pour 32 s, soit 5,6 fonds/min) | 9,26 | 0,33 | **9,59 min/min** |

**La projection de 2,7 était donc légèrement pessimiste sur sa propre hypothèse
(2,53 mesuré), et la part « rendu » qu'elle supposait — ~0,4 min/min — est en
réalité de 0,25 à 0,56 selon la densité de la scène.** Mais la ligne qui compte
est la première : **en vecteur pur, le coût tombe à 0,22-0,27 min/min**, contre les
**13,6 min/min** que l'étape 12.2 a mesurés sur son run complet (10 020 s de calcul
pour 737,9 s de vidéo, dont 84 % en génération d'images). **Le rapport est de 50 à 62.**

Ce qui reste vrai de la projection : dès qu'on remet des images générées dans la
boucle, on retombe dans le goulot. C'est ce que dit la dernière ligne du tableau.

### Disque

| Élément | Chemin | Go | Licence |
|---|---|---|---|
| Revideo 0.11.0 + dépendances | `benchmarks/preuve_motion/revideo/node_modules` | **0,30** | MIT |
| Chromium de Puppeteer | `models/puppeteer` | **0,59** | **purgé en fin de session** |

**Le Chromium de Puppeteer a été purgé, et c'est un résultat, pas du ménage.**
Installé, il portait le cumul retenu à **22,11 Go, au-dessus du plafond de 22**.
Vérifié par le rendu : avec `PUPPETEER_EXECUTABLE_PATH` pointé sur le Chromium
**déjà présent pour Playwright** (`models/playwright/chromium_headless_shell-1234/`,
0,21 Go, installé à l'étape 5.2), Revideo rend la séquence B en **8,05 s contre
8,31 s** avec le sien — équivalent. `models/puppeteer` supprimé, **cumul retenu
revenu à 21,52 Go**, inchangé depuis l'étape 7. Disque libre en fin de session :
**15 Gi** (16 Gi au lancement), plancher de 8 Go jamais approché.

`mesure.py` impose désormais ce chemin. L'étape 30.1 n'a **aucun poids à télécharger**
pour le rendu ; seuls les 0,30 Go de `node_modules` sont à réinstaller, et ils ne
comptent pas au plafond (même traitement que `.venv`, cf. `MODELES.md` § étape 7).

---

## 3. Ce qui n'est pas mesuré

- **Le mouvement en lecture.** La session ne voit pas une vidéo bouger. Elle a
  extrait **une planche-contact de six images par MP4** (2,5 / 8 / 13 / 19 / 25 / 30 s)
  et les a regardées — une image par séquence, trois au total, plus une image de
  validation de la chaîne technique au début. Tout ce qui concerne la **fluidité, le
  rythme, l'impression de vie : non évalué, soumis à Thomas.** Aucune note de
  fluidité n'est donnée ici, ni 3/5 ni autre chose.
- **La synchronisation à l'oreille.** Les repères sont calés au centième de seconde
  sur `words.json` ; que cela *tombe juste à l'écoute* est **non évalué, soumis à
  Thomas**. Le doute porte d'ailleurs sur la source : l'ASR du run affiche un WER de
  **21,4 % sur `seg_00`** et 19,1 % sur `seg_01` (`words.json`), donc les
  horodatages du hook sont les moins sûrs de la fenêtre.
- **La note de qualité du § 7.** Son seuil est « vue et notée ≥ 3/5 ». La part
  mesurable est tenue (séquence de 30 s, images + formes + texte animés, headless,
  ≥ 2 img/s tenu 27 à 61 fois). **La note reste à porter par Thomas.**

## 4. Défauts vus sur les planches de la PREMIÈRE version, et ce qui a été corrigé

> Les défauts de fabrication de la deuxième version sont au § 0. Cette section garde la
> trace de la première, parce qu'elle explique ce que la relecture à l'image attrape.

Quatre défauts ont été trouvés en regardant, et corrigés avant le rendu final :

1. **A** — le bloc de couleur de l'étiquette de segment était décalé de 80 px à
   droite de son propre texte. Recalé.
2. **B** — le tampon « PAS INERTE » entrait en collision avec le titre
   « SACCHAROSE » dans le coin supérieur droit. Déplacé en bas à droite.
3. **B** — l'hormone descendait du bord haut et traversait la ligne de sous-titre.
   Départ abaissé sous la titraille.
4. **C** — deux défauts de mise en page du sous-titre karaoké, tous deux dus au
   même malentendu sur `Layout` : `gap` ne tenait pas l'espace entre les mots (le
   texte se lisait « lesucreestuncodequ'on ») et `Layout` **ne peint pas** son
   `fill`, donc la plaque sombre derrière les sous-titres n'existait pas et la
   deuxième ligne débordait sur la jauge. Reconstruit en `Rect` en mode layout,
   avec une marge portée par chaque mot. La mise à l'échelle du mot actif a été
   retirée dans la foulée : dans un flux, elle mange l'espace de ses voisins.

**Défauts restants, non corrigés, à verser au dossier :**

- **C — le troisième fond casse la charte.** `7fd5881863a93362.png` est nettement
  plus clair que les deux autres et que le fond `#101820` de la charte : le voile
  de 50 % ne suffit pas à l'unifier, et la moitié claire de la séquence n'a pas la
  même tenue que la première. **La bibliothèque de 83 PNG n'a pas été produite pour
  servir de fond** : elle a été produite pour être *le sujet*, au centre du cadre,
  et la charte le dit (`framing.subject_scale` : « sujet occupant deux tiers du
  cadre »). C'est la vraie réponse de C, plus que la définition.
- **C — les fonds sont en 1280×720 et la sortie en 1920×1080** : agrandissement de
  1,5, mollesse visible à l'image. L'étape 12.2 avait choisi 1280×720 pour tenir
  sous 120 s par image ; en motion design le fond est agrandi, jamais recadré.
- **B — la composition est clairsemée** dans son premier tiers, et l'ensemble
  cadran + courbe de glycémie, vers 19 s, est petit et peu contrasté.

---

## 5. Ce que chaque séquence permet de trancher

**A — la typographie cinétique tient, et elle est gratuite.** 0,56 min/min, zéro
génération, zéro dépendance à FLUX. C'est le plancher de coût du dispositif et il
est atteint. Ce qu'elle ne dit pas : si 10 minutes de ce traitement tiennent
l'attention. 32 s ne répondent pas à cette question.

**B — le schéma animé est produit, et c'est la réponse au reproche de Thomas.**
Rien n'y glisse : le cristal se construit face par face, la molécule se dessine,
l'annotation arrive, la liaison casse, les sucres circulent, l'aiguille bouge, la
courbe sort de sa bande, l'hormone s'emboîte, trois branches s'ouvrent sur les mots
qui les nomment. **C'est de la construction, pas du déplacement d'image.**

**Mais B porte le coût que A et C n'ont pas, et il faut le dire net :** ses
**43 repères temporels, dont 23 calés exactement sur un mot de `words.json`**, ont
été écrits à la main, et la géométrie (hexagone du glucose, pentagone du fructose,
récepteur, cadran) est **spécifique au saccharose et à l'insuline**. 371 lignes pour
32 s. **Rien de cela ne se généralise tout seul à un autre sujet.** A (165 lignes) et
C (216 lignes) se rejouent sur n'importe quel script sans être réécrits ; B non.
**La question que l'étape 30.1 devra trancher n'est pas « sait-on faire un schéma
animé » — la réponse est oui — mais « d'où vient le schéma quand personne ne le
dessine ».** Trois routes existent, aucune n'est mesurée : une bibliothèque de
gabarits paramétrés (molécule, cycle, comparaison, flux, courbe) choisis par
`visual_intent` ; une génération de la chorégraphie par le LLM local ; la
vectorisation d'une image FLUX par `vtracer` (0,03 s mesurées à l'étape 5.2) suivie
d'une animation des chemins.

**C — la bibliothèque est recyclable, mais pas comme fond.** Techniquement oui :
0,25 min/min, zéro génération, le réemploi fonctionne. Visuellement, les 83 PNG ont
été faits pour être le sujet centré d'un plan, pas la matière de fond d'une
composition ; leur tonalité n'est pas homogène et l'agrandissement se voit.
**La conclusion n'est pas « jeter la bibliothèque » mais « ne pas s'en servir comme
fond » :** en habillage — encadrée, masquée, annotée, en médaillon — elle a sa place,
et l'étape 30.1 devrait la prendre par là. Une charte de fond dédiée (tonalité
imposée, sujet hors champ, 1920×1080) réglerait le reste, au prix d'un lot d'images
neuves.

---

## 6. Ce qui reste à Thomas

1. **Regarder les trois MP4 en lecture** et noter chacun. La session ne note pas la
   fluidité.
2. **Trancher la divergence de documents** portée au § 1 de `SUIVI.md` :
   `docs/STYLES.md` § 6 a déplacé le motion design de la phase 6 à la phase 2, le
   tableau § 5 de `ROADMAP.md` (ligne 30.1) l'annonce toujours en phase 6. Les deux
   documents se contredisent depuis le 15/09.
3. **Dire si le § 9 (message à Alek) tient.** Il nomme le motion design en style
   n° 2. Ce qui est rendu aujourd'hui le soutient ; ce qui n'est pas rendu — la
   fabrication automatique d'un schéma comme B à partir d'un script quelconque —
   est ce qu'il faut savoir promettre ou non.
