# Rendement composé — coût de la vidéo n contre la vidéo 1

Étape 29, 24/09/2026. Sources : `manifest.json` de chaque run (`execution.cost`, `execution.timings`,
`decisions.library_reuse`) et la base (`library_uses`, `library_semantic_reuse`). Scripts :
`benchmarks/etape29_compound.py` et `benchmarks/etape29_potentiel_semantique.py`. Coût en euros :
électricité **estimée** (30 W, `eur_a_mesurer: true`), hors relecture humaine. Pour mémoire,
l'étape 27 attribue 99,7 % du coût estimé à la relecture.

## 1. Vidéo 1 et les 5 dernières

| Run | Date | Style | Origine | Calcul (min) | € (estimé) | Images générées | Images reprises | Part reprise | Réemplois entre runs | QC |
|---|---|---|---|---|---|---|---|---|---|---|
| `j7sf` (**vidéo 1**) | 15/09 | illustré | repris ¹ | 32,2 | 0,004 | 0 | 127 | 100 % ¹ | 0 / 83 | FAIL |
| `mtn7` | 19/09 | motion | neuf, sans image | 50,5 | 0,006 | 0 | — ² | — | 0 / 0 | PASS |
| `s57f` | 20/09 | illustré | repris ¹ | 61,2 | 0,008 | 0 | 98 | 100 % ¹ | 0 / 92 | PASS |
| `s2ur` (**vidéo neuve de référence**) | 20/09 | illustré | neuf | **252,0** | 0,032 | **101** | 12 | 11 % | 0 / 111 | FAIL |
| `c7km` | 23/09 | illustré | dérivé de `rtmk` (étape 24) | 74,6 | 0,009 | 0 | 124 | 100 % | 36 / 36 | FAIL |
| `fgr6` (**run avatar**) | 24/09 | avatar2d sur illustré | dérivé de `s57f` | **13,9** ³ | 0,002 ³ | 0 | 98 | 100 % | 92 / 93 | **PASS 88,2** |

¹ **Un manifeste ne garde que la dernière reprise.** `j7sf` et `s57f` montrent 0 image générée
et `render_assets` = 0,08 s parce que leurs images avaient été produites par un passage antérieur
**du même run**, dont le coût a été écrasé. Le coût réel de la vidéo 1 n'est donc **pas lisible
dans son manifeste** ; la seule vidéo neuve mesurée de bout en bout est `s2ur`.
² Le moteur motion ne génère aucune image (scènes vectorielles, étape 30.1).
³ Calculé sur les minuteurs propres de `fgr6` : rendu 528,4 s + assemblage 201,1 s + export 39,1 s
+ QC 64,9 s = 833,5 s. Script, voix et sous-titres sont hérités du parent (0 s). Son manifeste
porte encore le coût du parent (61,24 min) : l'export sorti en code 4 ne le recalcule pas.

## 2. Où passe le temps d'une vidéo neuve (`s2ur`, 252,0 min)

| Poste | Secondes | Part |
|---|---|---|
| Génération d'images (`render_assets`, 101 images) | 11 016 | **72,9 %** |
| Voix (Qwen3-TTS) | 2 229 | 14,7 % |
| Script (LLM) | 680 | 4,5 % |
| Rendu des clips hors images | 641 | 4,2 % |
| Reste (recherche, sous-titres, assemblage, export, QC) | 552 | 3,7 % |

## 3. Réemploi : ce qui est mesuré

| Mesure | Valeur |
|---|---|
| Emplois des 10 derniers runs servis par un asset **antérieur** (`factory library stats`) | **128 / 673 = 19,0 %** |
| … dont runs dérivés (`c7km` 36 + `fgr6` 92) | **128, soit 100 % du réemploi** |
| … dont sujets nouveaux | **0** |
| Intentions des sujets nouveaux (`s2ur`, `s57f`, `rtmk`) ayant une image d'un autre run au-dessus de 0,9 (cosinus centré) | **0 / 233** |
| Même mesure au seuil 0,8, puis 0,7 | 0 / 233, puis 0 / 233 |
| Médiane du meilleur voisin pour ces intentions | 0,25 à 0,27 (0,003 pour `rtmk`) |
| Intentions de `mtn7` au-dessus de 0,9 | 28 / 109 : c'est le même script que `avwf`, rejoué en motion |
| Réemplois sémantiques journalisés en production | 0 (mécanisme livré aujourd'hui) |

**Le seuil est en cosinus centré, pas brut.** Mesuré sur 554 images : en cosinus e5 brut, 17 %
des paires d'intentions distinctes dépassent 0,9 (« cristal de sucre » ≈ « pile de carrés et
horloge », à 0,912). Le seuil demandé n'aurait rien trié. Après soustraction du vecteur moyen de
la bibliothèque, 0,3 % des paires dépassent 0,9, et ce sont des paraphrases du même sujet.

## 4. Explication de l'écart

1. **Le coût d'une vidéo est bimodal, et c'est l'image qui décide.** Avec des images neuves, une
   vidéo coûte 252 min, dont 73 % de génération. Sans image neuve, elle coûte 14 à 75 min. Il n'y
   a pas de pente douce de la vidéo 1 à la vidéo n.
2. **La baisse observée ne vient pas de la bibliothèque entre sujets.** Elle vient de trois cas
   où le sujet ne change pas : la **reprise** d'un run (images du même `video_id`), la
   **dérivation** (`c7km`, `fgr6` : 100 % des images héritées) et le **moteur motion**, qui ne
   génère aucune image. Sur un sujet nouveau, aucune image d'un autre sujet n'est assez proche,
   même au seuil de 0,7. Le réemploi sémantique ne fera donc presque rien baisser tant que chaque
   vidéo traite un sujet différent.
3. **Le réemploi a un prix de qualité.** `rtmk` a échoué au QC parce que 71 % de ses plans
   étaient servis par une image déjà vue (`visual_distinct_ratio` 0,355). Le réemploi sémantique
   ne ressert donc jamais une image déjà employée dans le run, et reste soumis au cooldown de
   10 runs de la chaîne.
4. **Ce qui se capitalise vraiment, c'est le coût fixe.** Le personnage `nova` a coûté 53 min de
   génération une fois (3 bases à 106 s, puis 13 éditions pour 48 min). Chaque vidéo qui
   l'emploie paie ensuite **37,8 s** : Rhubarb 22,1 s, composition 5,4 s, incrustation 10,4 s,
   pour 7 plans et 25,9 s d'avatar à l'écran. Idem pour les intros et outros de charte, faites en
   quelques secondes, et pour les gabarits.

## 5. Ce qui reste à capitaliser

| Levier | Gain attendu | État |
|---|---|---|
| **Coût cumulé au manifeste** : sommer les passages d'un run au lieu d'écraser | rend la vidéo 1 mesurable ; aujourd’hui, 3 manifestes sur 6 du tableau portent un coût faux (`j7sf`, `s57f`, `fgr6`) | non fait |
| **Mode présentateur sans image hôte** : les plans du hook et du CTA n'appellent plus la génération | ≈ 7 plans × 110 s ≈ 13 min par vidéo neuve | à coder : l'hôte génère encore ces images |
| **Motifs récurrents par niche** (atome, galaxie, cerveau…) générés une fois, étiquetés, tirés au lieu de générés | seul gisement réel pour le réemploi entre sujets | à concevoir ; le potentiel mesuré aujourd'hui est nul |
| **Séries et suites** (un sujet en plusieurs vidéos) : mêmes intentions, réemploi à 100 % | jusqu'à −73 % sur les épisodes 2 et suivants | décision éditoriale (Alek) |
| **Voix** : 37 min par vidéo avec Qwen3-TTS (RTF 3,29) | deuxième poste de coût, rien n'y est réemployable | Kokoro bloqué par l'arbitrage GPL (STATE) |
| **Musique** : bibliothèque vide | condition de publication (CONFORMITE § 10.1) | à alimenter (Studio YouTube, Thomas) |
| **Intros et outros** : 4 fichiers en bibliothèque, déclarés par la charte | identité de chaîne | `assemble` ne les monte pas encore |
