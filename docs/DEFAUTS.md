# Défauts de la première vidéo complète

**Objet.** Liste des défauts de `workspace/runs/bms-science-fr-20260917-rtmk/final.mp4`
(11 min 59, style illustré animé, chaîne `bms-science-fr`), établie le **18/09/2026**.
Consommée par l'**étape 15** (le banc mesure ce qui est ici chiffré) et l'**étape 16**
(la boucle de correction traite ce qui est ici causé).

> **Ce document n'est pas le verdict de Thomas.** `CLAUDE.md` règle 5 : ce qu'une session ne
> perçoit pas — le son, l'image en mouvement, l'ennui — est soumis à Thomas ou marqué « non
> évalué ». Ce qui suit est **mesuré sur le fichier** ou **vu sur des images extraites**. Le § 4
> dit ce qui reste sans jugement. Thomas avait dit de `final.mp4` : « ça va c'est bien […] mais je
> pense que ça sera le thème le moins intéressant de tous » — une appréciation, pas une liste.

---

## 1. La vidéo montre 36 images en 12 minutes, et l'une d'elles 22 fois

**Mesure.** Empreinte SHA-256 des 124 fichiers `assets/shot_*/image.png` :

| | |
|---|---|
| Plans | 124 |
| **Images distinctes** | **36** |
| Plans servis par une image déjà vue | **88 (71,0 %)** |
| Image la plus servie | **22 plans** |
| Images vues une seule fois | 14 |

Sur une planche-contact de 12 images régulièrement espacées, **7 sont deux motifs répétés** : un
champ de carrés orange et une diagonale de points. Le manifeste annonçait « 36 images générées,
la bibliothèque a servi les 88 autres plans » — mais la bibliothèque n'a servi **aucune image
nouvelle** : elle a resservi les 36 du même run.

**Cause — deux défauts de code, trouvés et mesurés.** La clé de cache est
`sha256(prompt normalisé + style + charte + résolution)` : deux plans partagent une image
**seulement si leur prompt est identique au mot près**. Or il ne l'est que trop souvent.

`factory/steps/shotlist.py` écrit quatre cadrages dans `PRECISIONS`
(*plan large · détail · variation de cadre · contre-champ*) et les pose correctement sur
`Shot.visual_intent` — **67 intentions distinctes**. Mais `_asset_request` construisait le prompt
avec un rang **figé à 0 ou 1** : tout plan non initial demandait « — plan large », toujours. Et sa
branche `stock`, qui sert les plans de rupture, servait l'intention **nue**, donc mot pour mot
celle du premier plan de son segment.

Résultat : **67 intentions distinctes réduites à 30 prompts**. La variété était écrite, elle
n'atteignait jamais l'image.

**Corrigé le 18/09/2026**, et l'effet est mesuré en rejouant le découpage sur le script réel :

| | avant | après |
|---|---|---|
| Prompts distincts (124 plans) | 30 | **67** |
| Plan le plus resservi | 22× | **10×** |
| Plans servis par un doublon | 75,8 % | **46,0 %** |
| Plafond de plans détectables | 109 | **124** |

**Deux conséquences qui ne sont pas des détails.**

*(a) La question ouverte de l'étape 13.1 est tranchée, et dans l'autre sens.* Le critère
« plans détectés = `n_shots` ±10 % » échouait (64/127) et l'arbitrage proposé était de *durcir la
charte* ou de *réécrire le critère*. Ni l'un ni l'autre : **le critère était juste, c'est le
découpage qui était cassé.** Sur `rtmk`, 27 frontières sur 123 ne changeaient pas d'image — le
plafond physique était **97** pour un critère qui exige **112**. Après correction, le plafond est
**124**, soit la totalité des plans. Le seuil de détection n'a pas à être abaissé.

*(b) Le coût de production monte.* 67 images au lieu de 36, à une médiane mesurée de **98,8 s par
image**, c'est **+51 min de calcul par vidéo** sur la première vidéo d'une chaîne — le run de
démonstration passerait de 2 h 23 à ≈ 3 h 15. Le réemploi n'était pas qu'un bug : il payait la
tenue du budget. **Cet arbitrage revient à l'étape 16**, et il doit être posé avec ce chiffre.

**Ce qui reste, et qui n'est pas du code.** 46 % de doublons subsistent parce que le **script**
n'écrit que 67 intentions visuelles pour 124 plans, et qu'un segment porte jusqu'à **10 plans**
alors que `PRECISIONS` n'a que 4 entrées : le cycle se répète. Allonger `PRECISIONS` coûte des
images ; raccourcir les segments change le script. → **étape 16**.

---

## 2. La narration ne respire jamais

**Mesure** sur `final.mp4` et `words.json` (1 528 mots) :

| Mesure | Valeur | Lecture |
|---|---|---|
| Parole effective | **648,1 s sur 719,1 s = 90,1 %** | 9,9 % de la vidéo sans voix |
| Silences ≥ 0,4 s sous −45 dB | **0** | aucun blanc dans 12 minutes |
| Pause médiane entre deux mots | 0,45 s | |
| Pause la plus longue | **1,1 s** | aucun temps d'arrêt |
| Plage de loudness (LRA) | **3,3 LU** | ton plat de bout en bout |

**Ce qui est conforme et n'est donc pas en cause** : loudness intégrée **−14,0 LUFS** et crête
réelle **−3,3 dBFS** (aux normes YouTube) ; débit **127,5 mots/min**, dans la fourchette de la
niche `science_pop` (p25 118,3 · médiane 134,9 · p75 158,9) ; durée 719,1 s contre une cible de
648 s à ±15 % (fourchette 550,8 – 745,2 s).

Le défaut n'est donc **ni le niveau, ni le débit, ni la durée** : c'est l'absence de relief. Un
mur de parole de 12 minutes à 3,3 LU de dynamique, sans un seul silence, et sur lequel aucune
musique ne vient poser de contraste — `workspace/library/music/` est vide et le montage est parti
sur un **lit silencieux**. → **étape 15** doit mesurer LRA, part de parole et longueur de pause ;
→ **étape 16** doit les fabriquer.

---

## 3. Les images n'illustrent pas le sujet

**Constat sur images extraites** (planche-contact de 12 images, `CLAUDE.md` règle 7). Le sujet est
« ce qui se passe quand vous faites 25 squats deux fois par jour ». Ce que l'écran montre : une
diagonale de points dorés, un champ de carrés orange, un empilement de dalles, un cercle fissuré à
côté d'un rectangle noir. Ces images ne sont fausses ni laides — elles sont **décoratives** : elles
n'expliquent rien, elles occupent le cadre pendant que la voix parle.

**Ce qui est mesurable là-dedans** : sur 124 plans, l'intention la plus fréquente est
*« Schéma illustrant la progression du métabolisme au fil des semaines »* — **40 plans, soit 32 %
de la vidéo** sur une seule idée visuelle, elle-même abstraite. Et **33 des 67 intentions
distinctes commencent par le mot « Schéma »** : la moitié du découpage demande un diagramme.

C'est le même constat que celui de la preuve motion design du 16/09 —
*« ce qui est perçu comme animation est la construction, jamais le déplacement »* — appliqué à
l'illustration : **ce qui est perçu comme une explication est un objet qu'on reconnaît, jamais une
forme abstraite qui glisse.** → **étape 16**, sur le prompt de script, pas sur le moteur d'image.

---

## 4. Ce qui n'est pas jugé ici, et qui attend Thomas

Aucune de ces quatre questions n'est mesurable par la session (`CLAUDE.md` règle 5) :

1. **La vidéo tient-elle l'attention ?** Aucune mesure locale ne le dit ; seules les vues le
   diront (étape 26).
2. **La voix est-elle agréable sur 12 minutes ?** Thomas a validé des extraits de 30 s
   (« ok pour l'instant »), jamais la durée entière.
3. **Le mouvement Ken Burns est-il satisfaisant ?** Thomas a explicitement demandé à **garder** le
   rendu de `final.mp4` (« ah non alors moi je veux garder le truc de final.mp4 »), qui repose sur
   un `zoompan` au comportement inversé — verrouillé, à ne pas « corriger ».
4. **La miniature attire-t-elle le clic ?** Elle est **typographique** : le texte occupe 53,6 % de
   la hauteur et l'illustration disparaît derrière. Le référentiel de la niche donne **43 % de
   miniatures à personnage** et **0 % à marqueur** — notre miniature n'est ni l'un ni l'autre.

### 4.1 Mesuré le 18/09/2026, Thomas absent, sur sa demande

Thomas a demandé que la session fasse elle-même le travail de vérification plutôt que de
l'attendre. Trois des quatre questions ci-dessus reçoivent donc une **mesure** — qui ne remplace
pas un jugement de goût, mais qui en retire la part vérifiable. Tout porte sur le run **EN**
`bms-science-en-20260917-avwf`.

**Question 2 — la voix.** Elle est aux normes et elle respire ; ce qui lui manque est le relief.

| critère | mesure | verdict |
|---|---|---|
| niveau intégré | −14,0 LUFS | conforme à la cible YouTube |
| true peak | −3,7 dBFS | aucune saturation |
| respiration | **105 pauses ≥ 0,4 s**, 60,2 s cumulées, la plus longue 1,13 s | tenue — sous le seuil pénalisant de 1,5 s |
| part de parole | 91,7 % | dense mais respirée |
| relief | **LRA 2,6 LU** | **c'est le défaut** |

**Le défaut n° 2 ne se transporte pas d'une langue à l'autre** : le run FR n'avait aucun silence
≥ 0,4 s, l'EN en a 105. En revanche l'anglais est **plus plat** que le français (2,6 LU contre
3,3) : les blancs existent, l'intensité ne varie jamais — la voix se tait puis reprend au même
niveau, sans appui ni retrait. *Non évalué et irréductible* : le timbre, le naturel, la justesse
de la prononciation. Seule une écoute les tranche.

**Question 3 — le mouvement.** Le rendu reste **verrouillé par Thomas** ; la mesure ne demande
aucune correction, elle établit le mécanisme que `STATE.md` § Bloqué réclamait « avant toute
modification ». Échelle du banc (YAVG de `tblend=difference`) : figé ≈ 0, Ken Burns lent ≈ 0,7.
`zoom_in` **0,021** · `pan` **0,028** · `static` 0,177 · `zoom_out` **0,347**. Deux mécanismes
distincts, et non un seul : *(i)* `zoom` ne s'accumule pas à `d=1`, donc seule la branche arrière
vit — prouvé par la parité du seed sur 8 plans `static`, 4 pairs figés (0,019 à 0,038) contre
4 impairs animés (0,160 à 0,604), sans recouvrement ; *(ii)* le `pan`, lui, utilise bien `on`,
mais sa course est calculée en pixels de l'image finale et appliquée dans le repère
suréchantillonné ×4 — **29 px de sortie** sur tout un plan. Détail et conséquence pour l'étape 17
dans `STATE.md` § Bloqué.

**Le banc ne pouvait pas le voir.** `hook_visual_change` rend **0,80 → pass** (seuil 0,5) parce
que sa fenêtre de 3 s contient le fondu d'ouverture : **2,428 pendant le fondu, 0,012 après**.
Le contrôle valide une transition, pas un mouvement — même famille d'artefact que
`cut_long_shots`, qui compte des plans détectés et non réels.

**Question 4 — la miniature.** Regardée. **Conforme à tous les contrôles, faible à l'usage.**
Le texte est massif, hiérarchisé sur deux niveaux, parfaitement lisible ; le `contrast_ratio` de
10,97 et le `legible_at_320px` se vérifient à l'œil. Mais : *(a)* environ **deux tiers de la
surface sont un dégradé gris uni**, l'illustration réduite à un bandeau central presque
indiscernable ; *(b)* **le fond contredit le titre** — « BIG BANG EXPANSION » sur une **carte de
la Terre**, le `visual_intent` de `shot_00` demandait « a map showing space expanding » et le
générateur a rendu une mappemonde : c'est le défaut n° 3 visible dès la vignette ; *(c)* aucun
point d'accroche — ni visage, ni objet, ni profondeur ; *(d)* « EXPANSION » déborde du bandeau
noir. **Le banc mesure la lisibilité du texte ; personne ne mesure l'attrait, et c'est l'écart.**
*Non évalué* : le taux de clic réel — c'est une composition qui est jugée ici, pas une performance.

**Question 1 — l'attention.** Laissée telle quelle : c'est l'objet même de l'étape 16, et seules
les vues la trancheront (étape 26).

---

## 5. Ce qui a changé au dépôt le 18/09/2026

- `factory/steps/shotlist.py` — `_asset_request` reçoit `rang_dans_segment` ; la branche `stock`
  passe par `_intention` comme la branche `image`.
- `factory/steps/shotlist.py` — `AssetRequest.contains_person` n'est plus la constante `False` :
  il est déduit de l'intention par `figure_une_personne()`. Voir `CONFORMITE.md` § 3 couche 3.
- `tests/test_etape12_1.py` — 4 tests de régression. Suite complète : **238 verts**.
