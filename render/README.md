# `render/` — moteur de motion design (Revideo 0.11.0, MIT)

Projet Node autonome. Il ne connaît ni les runs, ni la conformité, ni la langue : il reçoit un
fichier de spécification JSON et rend des vidéos. C'est `factory/styles/motion.py` qui écrit ces
spécifications, lance ce projet et redécoupe le résultat en clips de plan.

## Lancer

```sh
npm install                       # PUPPETEER_SKIP_DOWNLOAD=true : on réemploie Chrome
node render.mjs specs/<video_id>/batch.json            # tous les lots
node render.mjs specs/<video_id>/batch.json --lot lot_003   # un seul lot
```

`BMS_CHROME` impose un autre navigateur que `/Applications/Google Chrome.app`. **Aucun Chromium
n'est téléchargé** : le poids disque du dispositif est plafonné (`CLAUDE.md` § 3).

## Ce que le projet fait

`render.mjs` écrit `src/lot.json` puis appelle `renderVideo()` **une fois par lot**. Le lot sort en
une seule vidéo continue ; le manifeste `out/<video_id>/<lot>.json` porte la frontière de chaque
plan **en images**, et c'est `motion.py` qui découpe. Un lancement de Chromium coûte une dizaine
de secondes : le payer une fois pour vingt plans est le premier levier de vitesse.

`src/fonts/` ne contient que des **liens** vers `assets/fonts/` : les polices OFL du dépôt vivent
à un seul endroit et ne peuvent pas diverger d'une copie. Vite refuse par défaut de servir hors de
sa racine, d'où le `viteConfig.server.fs.allow` de `render.mjs`, limité au dépôt. Vérifié : les
images rendues sont **identiques au pixel** avec les liens et avec des copies.

`src/lot.json` est **importé statiquement** par `src/project.tsx` : le nombre de scènes d'un projet
Revideo est figé à la construction, et `variables` n'arrive qu'à l'exécution. Le fichier est donc
ignoré par git — `render.mjs` le réécrit avant chaque rendu.

## Les scènes

**Le critère, et il n'est pas négociable** (Thomas, 16/09/2026) : « ce qui est perçu comme
animation n'est pas le déplacement, c'est la **construction** et la **transformation** — il faut
qu'il se passe quelque chose à l'écran, pas que quelque chose s'y déplace. » Et le 19/09, sur la
première version de ce moteur : « la vidéo c'est des textes et un peu du motion design très
léger ». Une scène qui écrit une phrase et la fait glisser ne remplit pas le contrat.

Trois familles dans `src/scenes/` :

| Famille | Scènes | Ce qui se passe |
|---|---|---|
| **Jouées** | `tete-parlante`, `duo`, `groupe`, `personnage` | un être occupe le cadre, parle, réagit, marche |
| **Construites** | `assemble`, `coupe`, `systeme`, `flux`, `transformation`, `echelle`, `quantite`, `chronologie` | un objet se fabrique, s'ouvre, tourne, circule, devient autre chose |
| **Écrites** | `kinetic-text`, `title-card`, `quote`, `transition-stinger`, `lower-third`, `list-reveal`, `icon-grid`, `chart`, `stat-counter` | du texte — **en ponctuation seulement**, plafonné à un plan sur quatre par `factory/styles/motion.py` |

Le vocabulaire des scènes jouées vient d'un relevé de la chaîne de référence (19/09/2026) : une
sitcom animée à personnages, organes et objets anthropomorphes, **presque aucun texte à l'écran**,
plan moyen sous 3 secondes. `src/figures.tsx` porte la grammaire — `visage()` transforme n'importe
quelle forme en être vivant, `etre()` lui ajoute quatre membres filiformes, des gants et des
chaussures. `src/jeu.tsx` porte le jeu : bouche calée sur `words.json`, clignement, souffle,
regard, écrasement-étirement, cycle de marche.

Toutes les scènes lisent palette, polices et marges dans les props ; toutes vivent dans une
**caméra qui ne s'arrête jamais** et sur un fond à **couches en parallaxe** ; toutes posent le
bandeau de divulgation si `is_sponsor`.

Une scène **retourne la liste de ses tâches** ; `project.tsx` les lance en parallèle puis égrène
exactement le nombre d'images du plan.

## Six pièges payés, à ne pas repayer

1. `@revideo/renderer` ne tire **ni** `@revideo/vite-plugin` **ni** `@revideo/ui` : ils sont
   épinglés dans `package.json`, sinon `MODULE_NOT_FOUND`.
2. `makeScene2D` prend un **nom** en premier argument depuis 0.10.
3. Le **premier** lancement optimise les dépendances Vite, recharge la page et meurt sur
   `Navigation timeout of 30000 ms exceeded`. `render.mjs` relance une fois.
4. Le composant **`SVG` construit ses `Path` hors du contexte de scène** et échoue silencieusement
   (« The scene is not available in the current context »). Les icônes passent par `Path` et un
   `d` unique — voir `outils_icones.mjs`.
5. **Un `Txt` au texte réactif** (`text={() => signal()}`) déclenche la même erreur à chaque
   changement, et le texte n'apparaît pas. Un compteur s'écrit avec `tween`, qui pose le texte.
6. La **longueur d'une scène** ne doit pas dépendre de `waitFor(secondes)` : l'arrondi flottant et
   les tâches qui débordent ajoutent des images, et toutes les frontières de découpe suivantes
   glissent. `project.tsx` égrène les images une à une ; la vidéo d'un lot porte exactement
   `somme(images) + 1` image.

## Extraits de démonstration

```sh
uv run --python .venv/bin/python outils/demo_motion.py <run_id> <premier> <dernier>
```

Rend **un extrait court d'un vrai run, voix comprise** — douze plans, une minute, une trentaine de
secondes de calcul. C'est la seule façon de juger le moteur sans rendre dix minutes de vidéo
(Thomas, 19/09 : « pour les tests faudrait que tu fasses quelques courtes vidéos de demo, pas une
vidéo complète »). Les extraits sortent dans `workspace/demos/a-regarder/`.

## Banc de recette

```sh
node render.mjs recette/planche.json      # out/recette/planche.mp4
```

Dix plans, les neuf scènes, les quatre teintes de fond, le bandeau « Publicité ». C'est le seul
moyen d'éprouver `chart` et `lower_third`, qui ne sortent que si le script s'y prête. Toute
modification d'une scène se relit ici avant d'être relancée sur un run : 945 images en 7,5 s, et
la sortie doit porter **zéro `console.error`**.

## Mesuré le 19/09/2026 (M2, 16 Go, 1080p30)

19 049 images d'un run complet en **140,9 s**, soit **135,2 images/s** — 0,22 × le temps réel pour
le seul rendu Revideo. Le découpage ffmpeg qui suit coûte à peu près autant.
