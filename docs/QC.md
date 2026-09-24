# QC — le banc d'évaluation et le portillon

`factory qc --run <id>` mesure `final.mp4` face aux cibles de sa niche, écrit `qc.json`, porte
la note au manifeste et à la table `runs`. **Rien ne se publie sans lui.**

> **Version `qc/1.1.0` (étape 16, 18/09/2026).** Cinq mesures ajoutées — `hook_pattern_score`,
> `hook_forbidden_wording`, `open_loops_verified`, `interrupt_gap`, `density_vs_target` — et le
> poids de la famille `structure` porté de 5 à 10. **Les scores `qc/1.0.0` du § 7 ne sont pas
> comparables aux suivants** : le barème a changé, pas la vidéo. Les valeurs de calibration du
> § 7 sont conservées telles quelles, avec leur version.

Trois choses à savoir avant de lire un score :

1. **Le score n'est pas une prédiction de rétention.** Il mesure la conformité aux cibles du
   registre et aux décisions de production. Sa valeur prédictive sera établie — ou infirmée —
   à l'étape 26, en corrélant `qc_score` aux vues réelles (§ 8).
2. **Le portillon ne peut pas être complet, et il le déclare.** Trois classes de défaut ne sont
   pas atteignables sans modèle vision-langage (§ 1.2). `qc.json` les recopie dans `not_covered[]`
   à chaque run. Une vidéo qui passe le banc n'est pas une vidéo relue.
3. **Toute mesure porte une unité, une cible et l'origine de cette cible** (`target_source`).
   Trois origines, jamais confondues : le **registre** (`registre/REFERENTIEL.json`, mesuré sur
   74 chaînes), une **décision de production** (`config/qc.yaml`, aucune mesure derrière), ou un
   **paramètre de rendu** (la charte de la chaîne, le moteur de style).

---

## 1. Périmètre

### 1.1 Ce que le banc mesure
Neuf familles, **31 mesures** (26 à l'étape 15, cinq ajoutées à l'étape 16), dont 21 à 26
notées selon ce que le run porte au manifeste. Aucun modèle n'est chargé par le banc :
`ffmpeg`, `ffprobe`, PySceneDetect, Pillow, imagehash. Les cinq mesures de l'étape 16 lisent
`script.json` et le manifeste — le juge LLM de la densité et des boucles tourne pendant
`factory script`, pas pendant `factory qc`. Détail au § 3.

### 1.2 Ce qu'il ne mesure pas, et pourquoi
Recopié dans `qc.json → not_covered[]`, tiré de `config/qc.yaml` :

| Non couvert | Pourquoi | Qui s'en charge |
|---|---|---|
| Anatomie fausse d'un sujet généré (mains, visages) | Exige un modèle vision-langage : ni le budget mémoire (16 Go, un seul modèle résident) ni le 0 € ne le permettent | Relecture humaine (étape 19) |
| Éléments détachés dans une image | Contrôle **écrit, exécuté et échoué par principe** à l'étape 5.2 : sur 8 plans, 3 séparations légitimes sur 13 partagent la signature géométrique de la fautive | Relecture humaine |
| Dérive d'identité d'un plan à l'autre | Même cause | Charte (`style_prefix`, `framing`) en prévention, relecture en contrôle |
| Justesse du texte à l'écran par rapport à ce qui est dit | Le banc lit `shotlist.json`, pas les pixels : pas d'OCR | `review.json` (étape 19) |
| Qualité perçue de la voix, de la musique, du montage sonore | Ce que la session ne perçoit pas n'est pas mesuré | Écoute par Thomas |
| Véracité des faits énoncés | Hors périmètre d'un banc de rendu | `research.json` et `review.json` |

Deux contrôles écrits à l'étape 5.2 (`benchmarks/controles_plan.py`) — **cadrage** (marge uniforme
sur les quatre bords) et **dérive de palette** (intersection d'histogrammes teinte × saturation
contre la charte) — sont mesurés et concluants mais ne sont **pas** encore câblés dans le banc :
ils travaillent sur les assets, pas sur la vidéo livrée. Ils rejoindront le banc à l'étape 17,
quand la bibliothèque d'assets deviendra un livrable à part entière.

---

## 2. La formule

```
score = Σ (poids_famille × score_famille) / Σ (poids_famille)     sur les familles NOTÉES
score_famille = Σ (poids_mesure × score_mesure) / Σ (poids_mesure)  sur les mesures NOTÉES
verdict = PASS  si  score ≥ 70
              ET  aucune famille notée sous 50           (plancher par famille)
              ET  aucun contrôle bloquant en échec
              ET  aucune entrée absente
          FAIL  sinon, avec `reasons[]`
```

**Le plancher par famille refuse la compensation.** Une moyenne pondérée rachète par
construction : le run `rtmk` sortait à 73,9 avec la famille `coupes` à 9,8/100, portée par cinq
familles à 100. Sans plancher, le portillon ne tenait plus qu'aux contrôles bloquants et le
score n'était qu'un ornement. Valeur dans `config/qc.yaml → plancher_par_famille`.

**Une mesure `skipped` quitte le numérateur et le dénominateur.** C'est la règle du référentiel :
une cible marquée `a_mesurer` (rythme de coupe de trois niches, silence maximal, densité de
faits) ne doit pas être notée comme un écart. Conséquence à connaître : un run dont une famille
entière est sautée est noté sur moins de familles, et son score reste comparable — mais
`families[].score = null` le signale, et `bench_seconds_by_family` dit ce qui a tourné.

**Un fichier d'entrée manquant est une raison d'échec, pas une dispense.** Sans cette règle,
supprimer `words.json` serait le moyen le plus simple de faire monter un score : les mesures de
parole et de sous-titres passeraient en `skipped` et quitteraient le dénominateur.

### Poids des familles (`config/qc.yaml → poids`)

| Famille | Poids | Ce qu'elle décide |
|---|---|---|
| `coupes` | 25 | Le rythme perçu, mesuré sur le fichier livré |
| `hook` | 20 | Les trois premières secondes et la forme de l'accroche |
| `audio` | 15 | Niveau, crête, silences, lit musical |
| `duree` | 10 | La vidéo livrée face à ce qu'elle visait |
| `lisibilite` | 10 | Taille du texte, contraste réel, densité de mots |
| `variete` | 10 | Chaque plan apporte-t-il une image nouvelle |
| `parole` | 5 | Débit de narration et respiration |
| `sous_titres` | 5 | Couverture de la parole, longueur des lignes |
| `structure` | **10** | Place du sponsor, boucles payées, cadence des ruptures, densité |

Les huit premiers poids sont ceux du prompt de l'étape 15. **`parole` y est ajoutée à 5** : le
prompt impose le module et l'oublie au barème. **`structure` passe de 5 à 10 à l'étape 16** :
la famille portait deux mesures, elle en porte six, et les trois nouvelles sont des facteurs de
rétention (thèse n° 3), pas des détails de forme. La somme fait 110, ce qui est sans effet sur
une moyenne pondérée — seuls comptent les rapports entre poids.

### Les fonctions de score partiel (`factory/eval/base.py`)

| Fonction | Forme | Employée quand |
|---|---|---|
| `score_cible(v, c, tol, plage)` | 100 à ± `tol` de la cible, 0 à ± `plage`, linéaire entre, **symétrique** | La cible est une valeur visée : rythme, durée, débit |
| `score_min(v, min, zero)` | 100 au-dessus de `min`, 0 à `zero`, **aucun bonus au-delà** | La cible est un plancher : contraste, couverture, variété |
| `score_max(v, max, zero)` | 100 sous `max`, 0 à `zero` | La cible est un plafond : crête, silences, mots à l'écran |
| `score_intervalle(v, bas, haut, marge)` | 100 dans l'intervalle, 0 à `marge` au-delà | Trop et trop peu sont mauvais : loudness, lit musical |
| `score_booleen(ok)` | 100 ou 0 | Ce qui est vrai ou faux, jamais ce qui se mesure |

**La symétrie de `score_cible` est ce qui empêche le banc de récompenser un artefact.** Sans elle,
un montage qui hache gagnerait des points en s'éloignant de la cible du bon côté. Aucune fonction
ne donne de bonus au dépassement : un contraste de 18:1 ne vaut pas plus que 4,5:1, un texte à
l'écran permanent ne vaut pas plus qu'un texte présent.

---

## 3. Les mesures, une par une

Colonnes : **unité** · **cible et son origine** · **forme du score** · **poids dans la famille** ·
**bloquant** · **limite connue**.

### 3.1 `coupes` — poids 25
| Mesure | Unité | Cible · origine | Score | Poids | Bloq. | Limite |
|---|---|---|---|---|---|---|
| `cut_rhythm` | s/plan | `rythme_coupe_s.cible_montage` de la niche · **registre** | `cible`, tol 15 %, plage 60 % | 3 | non | Mesure les coupes **visibles**, pas les plans planifiés : deux plans servis par la même image ne produisent aucune coupe. Cible `a_mesurer` sur 3 niches ⇒ `skipped` |
| `cut_dispersion` | p90/p10 | — · **aucune** | **non noté** | — | non | Le registre ne contient aucun p90/p10 (le tableau P9 ne donne qu'une médiane par chaîne, non recalculable — `REFERENTIEL.md` § 6.5). Un seuil aurait été inventé. Mesurée, publiée, notée à partir de l'étape 26 |
| `cut_long_shots` | part de la durée | ≤ 10 %, bloquant au-delà de 25 % · **décision** | `max`, 0 à 40 % | 2 | **oui** | Porte sur la **part de durée** occupée par les plans > 3 × la cible, non sur leur nombre : `cible_montage` est déjà obtenue en retirant du corpus les chaînes à plans > 3 × leur médiane, et un seul plan long suffisait à refuser une vidéo. Sauté quand la cible de niche est `a_mesurer` — le repli de 7,8 s n'est pas une cible |
| `cut_rhythm_hook` | s/plan | cible × `facteur_hook` (0,7) · **registre** | `max` (couper plus vite est la consigne) | 2 | non | Fenêtre de 15 s fixée par `config/qc.yaml` |
| `n_scenes` | plans | — | non noté | — | non | Mesure brute, pour l'étape 26 |
| `cut_rhythm_by_minute` | s/plan gagnée par minute | — · **aucune** | non noté | — | non | Cadence des ruptures par tranche de 60 s et sa pente. `REFERENTIEL.json → ruptures_s` porte `a_mesurer` et désigne le banc : il la mesure, l'étape 16 fixera la cible. Noter avant d'avoir une cible serait inventer une norme |

### 3.2 `hook` — poids 20
| Mesure | Unité | Cible · origine | Score | Poids | Bloq. | Limite |
|---|---|---|---|---|---|---|
| `hook_visual_change` | booléen | ≥ 1 coupe **ou** mouvement dans les 3 s · **décision** | booléen | 3 | **oui** | Mouvement = `tblend=difference,signalstats` (YAVG) : plan figé ≈ 0, Ken Burns lent ≈ 0,7, seuil à 0,5 |
| `hook_text_present` | booléen | texte à l'écran dans les 3 s · **décision** | booléen | 1 | non | Lu dans `shotlist.json`, pas par OCR : vérifie ce que le pipeline a **demandé** |
| `hook_first_word` | s | ≤ 1,5 s avant le premier mot · **décision** | `max`, 0 à 5 s | 1 | non | Aucune valeur de registre : l'audio des chaînes tierces n'est jamais téléchargé. L'abandon des trois premières secondes était mesuré à l'image et jamais au son |
| `hook_length` | mots | entre `p25` et `mediane` de `hooks.longueur_mots` · **registre** | `intervalle` | 2 | non | Le plafond exigé par l'étape 15 (≤ médiane) est conservé, un **plancher** lui est ajouté : plafonner seul donnait 100 à un hook de deux mots. `n_faible` est recopié dans la note |
| `hook_type_rules` | part | 1,0 des règles **mécaniques** du type tiré · **registre** | `part` | 2 × (règles mécanisées / règles écrites) | non | Les règles de sens (« verbe d'action décrivant un événement en cours ») ne sont pas vérifiables sans modèle : comptées **non vérifiées**, jamais réussies. Le **poids** suit la part de règles vérifiables — un type dont une seule règle sur quatre est mécanisable pèse le quart. Diviser le *score* par les règles écrites aurait puni la vidéo pour notre limite |
| `hook_pattern_score` | note /100 | 100 · **registre** (patrons mesurés sur les 60 vidéos les plus vues) | note directe | 2 | non | **Ajoutée à l'étape 16.** Note de `factory/retention/hooks.noter` : élément clé du type présent (question, chiffre, contradiction, `I`, `you`, énumération, mystère, autorité, mise en scène, action), longueur entre p25 et médiane, aucune formulation proscrite. Ne fait pas double emploi avec `hook_type_rules` : celle-ci vient des règles en prose du **référentiel**, celle-là des **patrons du corpus** |
| `hook_forbidden_wording` | booléen | aucune des 20 formulations proscrites · **registre** | booléen | 2 | non | **Ajoutée à l'étape 16.** Les 20 formulations de `patterns_en.yaml`, relevées comme absentes des hooks les plus vus ou typiques du seul type non productible (`intro_chaine_neutre`). Comparaison insensible à la casse et à l'apostrophe typographique — le modèle écrit « don’t » aussi souvent que « don't » |

### 3.3 `audio` — poids 15
| Mesure | Unité | Cible · origine | Score | Poids | Bloq. | Limite |
|---|---|---|---|---|---|---|
| `loudness` | LUFS | −14,0 ± 1 · **registre `production`** (norme YouTube, pas une mesure du corpus) | `intervalle` | 3 | **oui** hors [−16, −12] | — |
| `true_peak` | dBTP | ≤ −1,0 · **registre `production`** (pratique de diffusion) | `max` | 1 | non | Plafond : −3 dBTP ne vaut pas plus que −1 |
| `loudness_range` | LU | ≥ 5,0 · **décision** (défaut n° 2 de l'étape 13.2) | `min`, 0 à 1,0 | 1 | non | Aucune valeur de registre : l'audio des chaînes tierces n'est jamais téléchargé |
| `silence_long` | silences ≥ 1,5 s | ≤ 2 · **décision** | `max`, 0 à 8 | 1 | non | `production.silence_max_s` porte `a_mesurer: true` dans le registre ; la valeur est une décision assumée |
| `music_bed_attenuation` | dB | 10 à 30 · **décision** | `intervalle` ; **0 si aucune piste musicale au manifeste** | 1 | non | **Estimation**, pas mesure : sans piste isolée, compare un **blanc de narration** (`words.json`) à une fenêtre parlée. Le blanc vient de `words.json` et non de `silencedetect`, qui ne voit aucun silence quand un lit musical tient le niveau au-dessus du seuil — c'est-à-dire exactement quand la mesure a un sens. `manifest.decisions.music_track` est consulté d'abord : sans lui, la note est 0 et le motif de `music_warning` est recopié. Sans ce garde-fou, les deux runs de la phase 1, qui n'ont **aucune** musique, obtenaient 97/100 sur cette mesure — l'écart voix/blanc y vaut 30 dB parce qu'il n'y a rien sous la voix |

### 3.4 `duree` — poids 10
| Mesure | Unité | Cible · origine | Score | Poids | Bloq. | Limite |
|---|---|---|---|---|---|---|
| `duree_vs_run` | s | `spec.target_duration_s` · **décision de l'étape 10** | `cible`, tol 15 %, plage 50 % | 2 | **oui** hors [60 %, 150 %] | — |
| `duree_vs_niche` | s | `duree_s.cible` de la niche · **registre** | `cible` | 1 | non | **Sautée** quand elle coïncide avec la cible du run (cas par défaut : `spec.target_duration_s` est dimensionnée sur la médiane de niche) — sinon la famille noterait deux fois le même écart. Sautée aussi quand `distribution_large` : `science_pop` a `p75/p25 = 12,9`, la médiane n'y est pas un mode. **Jamais bloquante** |

### 3.5 `lisibilite` — poids 10
| Mesure | Unité | Cible · origine | Score | Poids | Bloq. | Limite |
|---|---|---|---|---|---|---|
| `text_size` | part de la hauteur | ≥ 3,5 % · **décision** | `min`, 0 à 2,0 % | 1 | non | Lu dans les **paramètres de rendu** (charte `subtitles.size_px`, moteur `TAILLE_TITRE_PX`) : c'est un **contrôle de non-régression**, pas une mesure du rendu. Il vaut 100 tant que la charte n'est pas modifiée, et son travail est de refuser une charte qui casserait la lisibilité |
| `text_contrast` | ratio WCAG | ≥ 4,5:1 · **registre** (`miniatures.contraste_ratio_cible`) | `min`, 0 à 1,5 | 2 | non | Seuillage d'Otsu sur le bandeau de texte, fond pris au **percentile le plus proche du texte** (pire cas local) et non à sa moyenne. Quand `shotlist.json` annonce un texte et qu'aucun bandeau n'en porte, la note est **0, jamais `skipped`** : sauter ferait *gagner* la famille en retirant son poids du dénominateur. Le bandeau est décrit en parts de l'image dans `config/qc.yaml → mesure.lisibilite` : un moteur de style qui place son texte ailleurs doit l'y déclarer |
| `on_screen_words` | mots | ≤ 6 · **décision** | `max` sur la **part** des textes trop longs | 1 | non | Lu dans `shotlist.json` |

### 3.6 `variete` — poids 10
| Mesure | Unité | Cible · origine | Score | Poids | Bloq. | Limite |
|---|---|---|---|---|---|---|
| `visual_variety` | distance de Hamming (0-64) | ≥ 20 · **décision** | `min`, 0 à 4 | 2 | non | Images prises aux plans **planifiés**, pas détectés : mesurer entre plans détectés serait circulaire (un plan n'est détecté que parce qu'il diffère) |
| `visual_redundancy` | part des paires | ≤ 0,15 · **décision** | `max`, 0 à 0,60 | 2 | non | « Quasi identique » = distance ≤ 8, échelle mesurée à l'étape 15 |
| `cut_redundancy` | part des coupes | ≤ 0,10 · **décision** | `max`, 0 à 0,50 | 1 | non | Part des coupes **visibles** qui ne changent pas l'image. Ferme le passage laissé par l'écart entre `coupes` (qui lit le fichier livré) et `visual_*` (qui échantillonne les plans planifiés) : sans elle, ajouter des coupes à l'intérieur d'un plan planifié faisait monter `cut_rhythm` sans rien coûter. Non circulaire : deux plans détectés peuvent porter la même image, la coupe ayant été vue sur un cartouche ou un mouvement |
| `visual_distinct_ratio` | images distinctes / plans | ≥ 0,60 · **décision** | `min`, 0 à 0,15 | 3 | non | Mesure exacte du défaut n° 1 de l'étape 13.2. Regroupement glouton : deux plans sont « la même image » si leur distance phash est ≤ 8. Un zoom sur la même image reste proche — comportement voulu |

### 3.7 `parole` — poids 5
| Mesure | Unité | Cible · origine | Score | Poids | Bloq. | Limite |
|---|---|---|---|---|---|---|
| `speech_rate` | mots/min | `mots_par_minute.mediane` de la niche · **registre** | `cible`, tol 15 % | 1 | non | Mesuré **comme le registre le mesure** : mots ÷ étendue parlée, pas ÷ durée vidéo. **Partiellement acquis par construction** : cette médiane dimensionne déjà le script et la voix ; ce qui reste mesuré est la dérive du TTS, du rognage de silence et de l'`atempo`. Poids réduit à 1 pour cette raison. `histoire_doc` : n = 18, tolérance élargie par surcharge |
| `respiration` | pauses ≥ 0,4 s / min | ≥ 2 · **décision** (défaut n° 2 de l'étape 13.2) | `min`, 0 à 0 | 2 | non | Blancs entre mots de `words.json` : mesure la **narration**, pas le fichier mixé |
| `speech_rate_p90` | mots/min | — | non noté | — | non | p90 des fenêtres de 30 s. **Non noté volontairement** : le registre mesure un débit global, comparer un p90 à une médiane globale serait une faute de méthode. Entrée pour les étapes 16 et 26 |
| `speech_share` | part | — | non noté | — | non | Part du temps où un mot est prononcé |

### 3.8 `sous_titres` — poids 5
| Mesure | Unité | Cible · origine | Score | Poids | Bloq. | Limite |
|---|---|---|---|---|---|---|
| `subtitle_track` | booléen | piste présente dans le fichier livré, dans la bonne langue · **décision** | booléen | 1 | **oui** | Lu par `ffprobe` sur `final.mp4` : **non circulaire**, et c'est la seule panne réellement arrivée dans ce projet — des sous-titres produits et absents du conteneur. Une charte en `burn_in` n'a pas de piste séparée : le contrôle est alors tenu par construction, et le dit |
| `subtitle_coverage` | part des secondes parlées | ≥ 0,90 · **décision** ; cible 1,0 au **registre** `production` | `min`, 0 à 0,50 | 1 | **oui** | Mesuré seconde à seconde (pas de 0,1 s) et non en nombre de mots : un sous-titre qui déborde sur un silence donnerait une couverture flatteuse. **Partiellement acquis par construction** : les sous-titres sont écrits depuis `words.json`, que cette mesure relit. Elle détecte l'absence, la troncature et la désynchronisation, pas la qualité. Poids réduit à 1 |
| `subtitle_line_length` | lignes > 42 car. | 0 · **décision** | `max` sur la part, 0 à 0,10 | 1 | non | La charte impose déjà 38 caractères ; 42 est le plafond de lisibilité admis |

### 3.9 `structure` — poids 5
| Mesure | Unité | Cible · origine | Score | Poids | Bloq. | Limite |
|---|---|---|---|---|---|---|
| `sponsor_position` | s | ≥ 60 s · **décision** | booléen | 1 | **oui** | **Sauté** quand il n'y a aucun sponsor : rendre 100 pour un contrôle qui n'a rien contrôlé offrait des points de barème à toutes nos vidéos, qui n'en ont aucune |
| `open_loops_paid` | part des boucles plantées | 1,0 · **registre** (`boucles_minimum: 2`, décision de production) | `part`, dénominateur `max(plantées, 2)` | 2 | non | Une boucle n'est payée que si son `payoff` vient **après** son `plant`. Le dénominateur est le plus grand des deux : une seule boucle plantée et payée ne vaut pas 100 quand le référentiel en exige deux |
| `open_loop_position` | s | ≤ `boucle_ouverte.position_s` de la niche · **registre** | `max` | 1 | non | `n = 1` sur `science_pop` (`n_faible: true`) ; repli inter-niches 47,9 s ailleurs. Planter plus tôt n'est pas pénalisé |
| `open_loops_verified` | boucles | `boucles_minimum` de la niche · **registre** | `part`, dénominateur `boucles_minimum` | 2 | non | **Ajoutée à l'étape 16.** Compte les boucles vérifiées **dans le texte** par `factory/retention/verify.py` : marqueur de promesse dans les deux dernières phrases du `plant`, marqueur de paiement dans les deux premières du `payoff`, et un juge LLM court qui n'a pas démenti. `open_loops_paid` ci-dessus compte les **étiquettes** `plant`/`payoff`, que le code pose lui-même avant toute génération : c'est la différence entre une boucle écrite et une boucle déclarée. Une boucle non jugée est comptée **non vérifiée**, jamais réussie |
| `interrupt_gap` | s | ≤ cadence de la niche · **décision** (4 × rythme de coupe, borné [20, 45] s) | `max`, zéro à 2 × cadence | 2 | non | **Ajoutée à l'étape 16.** Plus long intervalle sans rupture, bords de la vidéo compris. Poser une rupture plus tôt que la cadence n'est pas pénalisé ; l'espacement l'est. La cadence **observée** du corpus est portée au référentiel (`ruptures_s.observee_s`) sans être appliquée : 23 s mesurées sur `science_pop` contre 23,4 s calculées, mais 6 s sur les paris sportifs et 40,5 s sur l'histoire |
| `density_vs_target` | faits/min | `densite_faits_par_minute.cible` de la niche · **registre** | `min`, zéro au plancher | 2 | non | **Ajoutée à l'étape 16.** Valeur lue au manifeste (`decisions.density`), mesurée par les règles de `factory/retention/density.py` sur le texte parlé. **Cette note ne prédit rien** : voir § 3.10 |

### 3.10 La densité d'information, et pourquoi sa note ne prédit rien

La mesure existe, elle est reproductible, et **elle ne sépare pas les vidéos qui marchent des
autres**. Il faut le dire avant de la lire.

**Ce qui a été mesuré** (sous-agent B de l'étape 16, 263 transcriptions anglaises du registre,
règles de `factory/retention/density.py`) :

| niche | cible (faits/min) | plancher de refus | moitié la moins vue | n |
|---|---|---|---|---|
| `niche_monetisable_paris_sportifs` | 12,5 | 7,5 | 9,55 | 23 |
| `histoire_doc` | 11,5 | 6,9 | 3,23 | 12 |
| `true_crime` | 11,0 | 6,6 | 11,25 | 25 |
| `niche_monetisable_longevite` | 5,0 | 3,0 | 5,67 | 75 |
| `science_pop` | 5,0 | 3,0 | 5,52 | 37 |
| `home_hacks` | 4,0 | 2,4 | 3,41 | 34 |
| `spiritualite` | 3,5 | 2,1 | 5,66 | 41 |
| *repli inter-niches* | 5,5 | 3,3 | — | 262 |

**Le test de validité échoue.** Corrélation de Spearman entre faits/minute et vues, au sein de
chaque niche : **+0,057 sur l'ensemble des 263 transcriptions** (|t| = 0,93, non significatif).
L'écart entre la moitié la plus vue et la moitié la moins vue n'est significatif **dans aucune
niche sauf `spiritualite`, où il va dans le mauvais sens** (les plus vues sont 39 % *moins*
denses). Un test intra-chaîne (vidéo n° 1 contre n° 4-5 de 48 chaînes) donne 25 signes positifs
sur 48, **p = 0,885** : indiscernable du hasard. Les deux corrélations positives apparentes
(`home_hacks`, paris sportifs) s'effondrent dès qu'on retire les noms propres du comptage.

**Ce qu'on en fait, alors.** La densité reste au barème comme **garde-fou de rédaction** : un
script sans un seul fait vérifiable est mauvais, cela ne se discute pas. Elle n'est pas
présentée comme un prédicteur, `valide_comme_predicteur: false` est inscrit au référentiel, et
c'est l'étape 26 — la seule qui disposera de vues réelles sur **nos** vidéos — qui tranchera
son poids.

**Deux limites de la mesure elle-même, à garder en tête.**
1. **Plus de la moitié du score vient des noms propres** (54,9 % mesurés sur `science_pop`).
   Le score mesure d'abord une densité d'entités, pas une densité de preuves : `percent` et
   `attribution` réunis ne pèsent que 5,7 %. `qc.json` rapporte donc `entity_share` avec la
   valeur.
2. **Les cibles sont mesurées sur des transcriptions automatiques**, dont 81 sans ponctuation
   et 234 sur 263 auto-générées : les règles de majuscule y captent du bruit d'ASR. Nos scripts,
   eux, sont ponctués et à casse normalisée. La comparaison n'est donc pas de même nature des
   deux côtés, et les cibles des niches à forte densité d'entités (`true_crime`, `histoire_doc`,
   paris sportifs) sont probablement surestimées.

**Deux seuils, pas un.** `cible` déclenche l'enrichissement sourcé pendant `factory script` ;
`plancher` (60 % de la cible) fait échouer le run. Prendre la médiane du corpus comme seuil de
refus reviendrait à refuser tous les runs — nos scripts n'ont que les faits de `research.json`,
les chaînes du registre écrivent avec une documentation illimitée — et un portillon qui refuse
tout ne trie rien.

### 3.11 La cadence des ruptures : mesurée d'un côté, décidée de l'autre

La cadence **appliquée** est `4 × rythme_coupe_s.cible_montage`, bornée à [20, 45] s. La
cadence **observée** sur le corpus (sous-agent A : changement de thème à fenêtre de 15 s,
question au spectateur, ou chiffre) est inscrite au référentiel sans être appliquée :

| niche | cadence appliquée | cadence observée (médiane) | p25 – p75 | n |
|---|---|---|---|---|
| `science_pop` | 23,4 s | 23 s | 8 – 59 | 26 |
| `histoire_doc` | 20,0 s (plancher) | 40,5 s | 14 – 90 | 12 |
| `true_crime` | 45,0 s (plafond) | 25 s | 8 – 63 | 24 |
| `home_hacks` | 22,8 s | 26 s | 9 – 60 | 27 |
| `spiritualite` | 45,0 s (plafond) | 27 s | 8 – 67 | 34 |
| `niche_monetisable_paris_sportifs` | 20,0 s (plancher) | 6 s | 3 – 18 | 23 |
| *toutes niches* | — | 21 s | 7 – 58 | 225 |

Sur `science_pop`, la règle de production et la mesure du corpus tombent à 0,4 s l'une de
l'autre : le facteur 4 de l'étape 10 est corroboré là où il a été posé. **Ailleurs elles
divergent d'un facteur 3**, et les bornes [20, 45] s y pèsent plus que le rythme de coupe. La
règle n'est pas modifiée pour autant — 82 % des ruptures détectées par le sous-agent A sont
des chiffres, c'est-à-dire que la mesure voit surtout de la densité, pas du rythme. **À
reprendre à l'étape 26**, avec la même méthode que pour la densité.

---

## 4. Les six contrôles bloquants

Un bloquant en échec donne `FAIL` **quel que soit le score**. Une vidéo à 92 dont le niveau
sonore est hors norme ne se publie pas.

| Contrôle | Condition d'échec | Origine |
|---|---|---|
| `loudness` | hors [−16, −12] LUFS | Prompt de l'étape 15 ; norme YouTube |
| `duree_vs_run` | < 60 % ou > 150 % de `spec.target_duration_s` | Prompt de l'étape 15 |
| `subtitle_track` | aucune piste de sous-titres dans le fichier livré | Prompt de l'étape 15 (« sous-titres absents ») |
| `subtitle_coverage` | couverture < 90 % des secondes parlées | Prompt de l'étape 15 |
| `cut_long_shots` | les plans > 3 × la cible occupent plus de 25 % de la durée | Prompt de l'étape 15, **assoupli sur objection B3** : le prompt demandait « un plan > 3 × cible », ce qui refusait une vidéo pour un seul plan long |
| `hook_visual_change` | ni coupe ni mouvement dans les 3 premières secondes | Prompt de l'étape 15 |
| `sponsor_position` | premier plan sponsorisé avant 60 s (sauté s'il n'y a pas de sponsor) | Prompt de l'étape 15 |

`verdict_pipeline` (contrat d'`INTERFACES.md`, consommé par l'étape 22.2) vaut `blocked` quand le
contrôle en échec porte `verdict_fail: blocked` dans `config/qc.yaml`, `regenerate` sinon, et
`regenerate_steps[]` nomme les étapes à rejouer.

**Précision apportée par l'étape 22.2 (22/09/2026).** `blocked` ne veut pas dire « aucune reprise
n'est possible », il veut dire « ce n'est pas au barème de décider ». L'orchestrateur tente **une**
régénération sur un contrôle bloquant **si et seulement si** `config/orchestrator.yaml → remedes`
nomme ce contrôle (`remedes_sur_bloquant: true`, coupable d'un `false`). Le cas de `loudness`
l'explique : un niveau sonore hors norme est tantôt un **montage interrompu** — mesuré le
21/09/2026, un `kill -9` avait laissé `clips/shot_19.mp4` tronqué — que 198 s de remontage
réparent, tantôt un défaut de fond, auquel cas la reprise échoue et le job bloque de toute façon,
pour 4 minutes de machine. On mesure plutôt que de trancher à l'aveugle. Un contrôle bloquant
**absent** de la table bloque sans reprise, comme avant : `subtitle_track` n'a pas de remède, et
rejouer le montage pour une piste de sous-titres absente dépenserait le remontage pour se faire
refuser par le même contrôle.

---

## 5. Seuils par niche

Le barème par défaut vaut pour toutes les niches. `config/qc.yaml → surcharges_par_niche` le
**fusionne clé à clé**, jamais en remplacement. Deux surcharges à ce jour :

| Niche | Surcharge | Motif mesuré |
|---|---|---|
| `true_crime` | `cut_rhythm.part_longue_max` 0,10 → 0,20 ; `part_longue_bloquante` 0,25 → 0,40 | Rythme de plateau mesuré à 15,7 s/plan (`cible_montage`) : plan fixe long + inserts courts. Les plans longs y occupent structurellement une plus grande part de la durée ; le seuil par défaut ferait échouer une vidéo correcte de cette niche |
| `histoire_doc` | `speech_rate.tolerance` 0,15 → 0,25 ; `plage` 0,45 → 0,60 | Débit de narration mesuré sur **n = 18** seulement (`REFERENTIEL.md` § 2) : tolérance élargie tant que la mesure n'est pas consolidée, plutôt qu'une note fondée sur un petit n |

Les cibles, elles, viennent toutes de la niche du run : rythme de coupe, durée, débit, longueur
de hook, position de boucle. **Trois niches** (`longevite`, `complements_fr`, `paris_sportifs`)
n'ont aucune mesure de rythme de coupe : leur `cut_rhythm` sort `skipped`, le repli provisoire de
7,8 s n'étant pas une cible.

---

## 6. Coût

Mesuré sur le M2 16 Go, vidéo de 12 minutes en 1080p30 (run `bms-science-fr-20260917-rtmk`) :

| Famille | Secondes | Ce qui coûte |
|---|---|---|
| `coupes` | 28,7 | PySceneDetect sur la vidéo entière (`auto_downscale` actif) |
| `variete` | 16,0 | 124 images extraites (une par plan planifié) + phash |
| `audio` | 4,4 | `ebur128`, `silencedetect`, deux `volumedetect` |
| `lisibilite` | 1,7 | 5 images extraites en pleine résolution + Otsu |
| `hook` | 0,7 | `tblend=difference,signalstats` sur 3 s |
| `duree`, `parole`, `sous_titres`, `structure` | < 0,3 | Lecture de fichiers |
| **Total** | **51,6 s** | Contrainte : **< 180 s**. Tenue avec 3,5× de marge |

Deux économies mesurées, à ne pas défaire :
- **`-map 0:a:0 -vn` sur toute sonde audio.** Sans eux, ffmpeg décode aussi le flux vidéo pour
  l'envoyer au `null` : `ebur128` passe de 4 s à plus d'une minute. Corrigé dans
  `factory.audio.measure_lufs`, donc `factory export` en bénéficie aussi.
- **`-ss` avant `-i`** pour extraire une image (recherche par mots-clés) : 0,13 s au lieu de 20 s.
- **Ne pas employer `frame_skip`** dans PySceneDetect : mesuré **8,7× plus lent** à `frame_skip=2`,
  et les timecodes en sortent faussés. `auto_downscale` est déjà actif par défaut.

---

## 7. Calibration de cette session — 18/09/2026, banc `qc/1.0.0`

### 7.1 La fixture idéale

`tests/fixtures/qc_cible.json` porte, pour chaque mesure notée, la **valeur cible** de la niche
`science_pop` ou le seuil de `config/qc.yaml`. Les seuils, les poids et les fonctions de score
sont lus dans le barème déployé au moment du calcul — la fixture ne recopie aucun nombre, elle
y renvoie par `@seuil.champ`.

**Score : 100,0 / 100 · PASS · aucune raison d'échec.** Critère de l'étape 15 : ≥ 95. Tenu.
Ce qu'elle prouve : le barème donne bien 100 à une vidéo aux cibles, et aucune fonction de score
ne donne de bonus au dépassement. Ce qu'elle **ne** prouve pas : que le banc sait mesurer.
C'est ce que font les trois mesures suivantes.

### 7.2 La vidéo volontairement défectueuse

Fabriquée depuis le run `rtmk` par une seule commande, reproductible :

```
ffmpeg -i final.mp4 -t 323.6 -c:v copy -af "volume=-16dB" -c:a aac -b:a 192k \
       -c:s copy -movflags +faststart workspace/qc_calibration/defectueuse.mp4
```

Deux défauts injectés : **durée tronquée à 45 %** (323,7 s pour 648 s visées) et **niveau abaissé
de 16 dB** (−29,6 LUFS pour −14 visées).

**Score : 49,3 / 100 · FAIL · `verdict_pipeline: blocked`**, en 71,5 s. Les huit raisons rendues :

| Raison | Ce qui l'a déclenchée |
|---|---|
| `duree_vs_run` = 323,7 s, **50 %** de la cible | bloquant hors [60 %, 150 %] — **défaut injecté, attrapé** |
| `loudness` = **−29,6 LUFS** | bloquant hors [−16, −12] — **défaut injecté, attrapé** |
| `cut_long_shots` = 0,691 | 9 plans au-delà de 17,5 s occupent 69,1 % de la vidéo |
| famille `duree` à 0,0 | sous le plancher 50 |
| famille `audio` à 35,4 | sous le plancher 50 |
| famille `coupes` à 2,8 | sous le plancher 50 |
| famille `variete` à 21,5 | sous le plancher 50 |
| score 49,3 sous le seuil 70 | — |

`regenerate_steps` : `script`, `assemble`, `voice`, `shotlist`, `render`.

**Les deux défauts injectés sont nommés séparément, avec leur valeur mesurée et leur borne.**
Les six autres raisons sont des conséquences de la troncature : la `shotlist` couvre 738 s quand
le fichier en fait 324, donc la variété s'effondre — un effet réel de la troncature, pas un faux
positif, mais qui montre que le banc ne sait pas isoler une cause d'une conséquence.

### 7.3 Les deux runs de la phase 1

| Run | Score | Verdict | Temps du banc | Familles sous 100 |
|---|---|---|---|---|
| `bms-science-fr-20260917-rtmk` | **70,6** | **FAIL** | 128,5 s | `coupes` 2,8 · `audio` 79,6 · `variete` 78,9 · `hook` 93,1 |
| `bms-science-fr-20260915-j7sf` | **81,1** | **FAIL** | 168,0 s | `coupes` 42,9 · `audio` 78,2 · `hook` 88,8 · `variete` 99,5 |

Les deux échouent, et **aucun ne s'en tire par le score** : `rtmk` est au-dessus de 70, `j7sf`
bien au-dessus, et ce sont le bloquant `cut_long_shots` et le plancher par famille qui refusent.
C'était l'objet de l'objection A1 ; sans elle, `j7sf` serait passé à 81 avec une famille `coupes`
à 43.

**Les trois métriques les plus faibles de chaque run :**

| Run | 1 | 2 | 3 |
|---|---|---|---|
| `rtmk` | `cut_long_shots` **0** (0,816 de la durée en plans > 17,5 s) | `cut_rhythm` **0** (19,43 s/plan mesurés pour 5,85 visées) | `music_bed_attenuation` **0** (aucune piste musicale au manifeste) |
| `j7sf` | `cut_long_shots` **0** (0,496 de la durée) | `cut_rhythm_hook` **0** (16,67 s/plan sur les 15 premières secondes pour 4,09 visées) | `music_bed_attenuation` **0** (aucune piste musicale) |

**Ce que la calibration établit, et qu'il faut lire avec les deux runs sous les yeux :**

1. **Le rythme perçu n'est pas le rythme planifié, et l'écart est énorme.** `shotlist.json`
   annonce une médiane de 5,76 s hors hook sur `rtmk` ; le banc mesure **19,43 s/plan** sur le
   fichier livré, et **39 plans visibles pour 124 planifiés**. Sur `j7sf` : 6,53 s/plan mesurés
   et 64 plans visibles pour 127. La cause est mesurée et connue depuis l'étape 13.2 — 71 % des
   plans de `rtmk` sont servis par une image déjà vue, et le banc le confirme de son côté :
   `visual_distinct_ratio` = **0,355** (44 images distinctes pour 124 plans). `j7sf`, qui réemploie
   moins, mesure 0,677 et passe.
2. **Un même défaut est compté deux fois.** Sur ces deux runs, `cut_long_shots`, `cut_rhythm` et
   `visual_distinct_ratio` décrivent tous la même cause : le réemploi d'images. Le banc le
   rapporte donc trois fois, dans deux familles. Ce n'est pas faux — le spectateur voit bien une
   image fixe pendant 41,5 s — mais cela **pèse trois fois** sur le score. À revoir à l'étape 26
   avec la corrélation aux vues, pas avant : c'est exactement le genre d'ajustement qu'il faut
   fonder sur une mesure et non sur une intuition.
3. **Le hook est la famille la moins mauvaise, et c'est suspect.** 93,1 et 88,8. Trois de ses
   quatre mesures notées sont des booléens ou des contrôles à forte probabilité de succès
   (`hook_visual_change`, `hook_text_present`, `hook_first_word` à 0,0 s sur les deux runs).
   La seule qui discrimine est `hook_length` (68,9 et 80,0 : les deux hooks sont **trop courts**,
   11 et 15 mots pour une fourchette de 22 à 36). L'étape 16 devra donner au banc de quoi juger
   un hook autrement que par sa présence.
4. **Ce que le banc n'a pas su reprocher aux runs, et qui est pourtant un défaut connu.**
   `loudness_range` 3,3 et 2,9 LU (défaut n° 2 de l'étape 13.2, « la narration ne respire
   jamais ») ne coûte que 57,5 et 47,5 points sur une mesure de poids 1 — alors que `respiration`
   rend **100** sur les deux (7,68 et 4,88 pauses ≥ 0,4 s par minute). Les deux mesures se
   contredisent : les blancs **entre mots** existent, mais le niveau ne descend pas entre eux.
   Le défaut est dans le mixage, pas dans le débit. À trancher à l'étape 16.

### 7.4 Temps d'exécution

| Mesure | Temps | Condition |
|---|---|---|
| `rtmk` (12 min de vidéo) | **128,5 s** | machine chargée (un `factory render` résiduel en arrière-plan) |
| `j7sf` (12,3 min) | **168,0 s** | idem |
| Vidéo défectueuse (5,4 min) | **71,5 s** | idem |
| `rtmk`, machine peu chargée, avant l'ajout de `cut_redundancy` | **51,6 s** | mesuré plus tôt dans la session |

**Contrainte : < 180 s. Tenue sur les trois mesures, mais `j7sf` n'en est qu'à 12 s.** Les deux
postes qui coûtent sont la détection de plans (PySceneDetect, ~29 s à vide) et l'extraction des
images (124 plans planifiés + 39 à 64 plans détectés, ~0,13 s chacune). Si une vidéo plus longue
ou une machine plus chargée faisait sauter le plafond, le levier mesuré est de rendre
`cut_redundancy` optionnel — il coûte à lui seul une image par plan détecté.

---

## 8. Recalibration prévue à l'étape 26

Le barème de cette session est une **hypothèse** : les poids viennent du prompt de l'étape 15,
les seuils sans cible de registre sont des décisions. Rien ne dit encore qu'un score de 85 retient
mieux qu'un score de 70. L'étape 26 le tranche, et voici la procédure.

**Données.** Pour chaque run publié : `qc_score`, `qc_verdict`, `qc_version`, et chaque
`metrics[<nom>].value` de `qc.json` d'un côté ; de l'autre, l'API YouTube Analytics —
`views`, `averageViewPercentage`, `averageViewDuration` et la **courbe de rétention**
(`audienceWatchRatio` × `elapsedVideoTimeRatio`). `qc_version` est indispensable : deux scores
calculés par deux barèmes différents ne se corrèlent pas ensemble.

**Ce qui se corrèle, et dans quel ordre.**
1. `qc_score` global ↔ `averageViewPercentage`, à n ≥ 30 runs. Si le coefficient n'est pas
   significativement différent de zéro, **le barème global est invalidé** et doit être dit tel
   quel, pas retouché jusqu'à ce qu'il marche.
2. Chaque mesure, séparément, ↔ `averageViewPercentage`. C'est pour cela que `qc.json` publie
   `metrics` décomposé : une famille peut prédire là où le score global ne prédit rien.
3. `hook_visual_change`, `hook_length`, `cut_rhythm_hook` ↔ la rétention à 30 s de la courbe.
   Les mesures de hook doivent prédire l'abandon **précoce**, pas la moyenne.
4. `visual_distinct_ratio` et `visual_redundancy` ↔ la pente de la courbe au milieu de la vidéo.

**Ce que la recalibration a le droit de changer, et ce qu'elle n'a pas le droit de changer.**
Elle peut modifier les **poids** et les **seuils sans cible de registre** (`décision` dans le
tableau du § 3). Elle ne peut pas modifier une cible qui vient du registre : celle-là se remesure
sur le corpus, elle ne s'ajuste pas au résultat. Un changement de poids ou de seuil **incrémente
`VERSION` dans `factory/eval/bench.py`** et se consigne ici avec sa date et son n.

**Le biais à ne pas oublier.** `REFERENTIEL.md` § 6.1 : le corpus du registre ne contient que des
vidéos **parmi les plus vues** de leur chaîne. Les cibles décrivent ce que font les bonnes vidéos,
pas ce qui les sépare des mauvaises. Une corrélation nulle à l'étape 26 pourra donc vouloir dire
« le barème ne prédit rien » **ou** « les cibles décrivent un plafond que tous nos runs touchent
déjà ». Seule la variance des scores observés permettra de trancher entre les deux.

---

## 9. Objections du contradicteur

Un sous-agent contradicteur a relu `config/qc.yaml`, ce document, `factory/eval/base.py`,
`factory/eval/bench.py`, les neuf modules de mesure, `REFERENTIEL.md` § 2 et § 6, et les deux
`qc.json` déjà produits. **16 objections. 12 retenues telles quelles, 3 retenues autrement,
1 refusée sur preuve.**

### A — la formule récompense-t-elle un artefact ?

| # | Objection | Traitement |
|---|---|---|
| A1 | Le portillon ne tient que par les bloquants : `rtmk` sort à 73,9 avec `coupes` à 9,8/100, cinq familles à 100 le portant | **retenue** — `plancher_par_famille: 50` dans `config/qc.yaml`, appliqué dans `bench._verdicts`. Une moyenne pondérée ne rachète plus une famille effondrée |
| A2 | `coupes` lit `final.mp4`, `variete` échantillonne `shotlist.json` : ajouter des coupes **dans** un plan planifié fait monter `cut_rhythm` sans rien coûter à la variété | **retenue** — nouvelle mesure `cut_redundancy` : part des coupes visibles qui ne changent pas l'image |
| A3 | `hook_type_rules` note le script contre l'étiquette qu'il s'est donnée ; trois types n'ont qu'une règle mécanique, donc 100 gratuit | **retenue autrement** — la correction proposée (diviser par le nombre de règles écrites) aurait plafonné un script irréprochable au motif que *nous* ne savons pas vérifier le reste. C'est le **poids** qui suit la part de règles mécanisées, pas le score |
| A4 | `sponsor_position` rend 100 sans sponsor ; `open_loops.min: 2` ne sert que dans la note, une seule boucle payée vaut 100 | **retenue** — `sponsor_position` sort `skipped` sans sponsor ; le dénominateur des boucles devient `max(plantées, boucles_minimum)` |
| A5 | Un `skipped` dû à la vidéo monte le score : sans fenêtre sans parole, `music_bed_attenuation` quitte le dénominateur et la famille audio gagne | **retenue autrement** — noter 0 aurait puni deux fois le même défaut (`respiration` le note déjà). La vraie cause était ailleurs : `silencedetect` ne voit aucun silence quand un lit musical tient le niveau. La fenêtre vient désormais des blancs de `words.json`, qui existent toujours |

### B — les seuils sont-ils atteignables par les vidéos du registre ?

| # | Objection | Traitement |
|---|---|---|
| B1 | `cut_long_shots` s'exécutait contre le **repli provisoire de 7,8 s** que le référentiel refuse comme cible, alors même que `cut_rhythm` sortait `skipped` | **retenue** — conditionné à `not a_mesurer` |
| B2 | Bloquer sur le *nombre* de plans longs est trop brutal : `cible_montage` est déjà obtenue en retirant les chaînes à plans > 3 × leur médiane, et un seul plan suffisait à refuser une vidéo | **retenue** — le bloquant porte sur la **part de durée** occupée par ces plans (> 25 %), le nombre reste dans la note |
| B3 | `cut_dispersion` (max 3,0) et la surcharge `true_crime` 4,5 ne reposent sur rien : le registre ne contient aucun p90/p10, et les deux seules valeurs mesurées ici valent 4,33 et 5,07 | **retenue** — la mesure est publiée **sans note** jusqu'à l'étape 26 ; la surcharge `true_crime` porte désormais sur la part de durée |
| B4 | `hook_length` plafonne à une médiane que la moitié du corpus dépasse, et un hook de 2 mots vaut 100 | **retenue** — note en intervalle `p25` … `médiane` |

### C — une mesure dépend-elle d'un choix de rendu ?

| # | Objection | Traitement |
|---|---|---|
| C1 | `subtitle_coverage` croise `subtitles.ass` avec `words.json`, dont les sous-titres sont issus : 1,0 et 0,998 acquis par construction | **retenue** — poids 2 → 1, circularité écrite dans la note et ici ; ajout de `subtitle_track`, bloquant et **non circulaire**, lu par `ffprobe` sur le fichier livré |
| C2 | `speech_rate` compare `words.json` à la valeur qui dimensionne déjà script et voix | **retenue** — poids 2 → 1 et circularité nommée. La correction proposée (noter le p90 par fenêtre) est **refusée** : le registre mesure un débit **global**, comparer un p90 à une médiane globale serait une faute de méthode. Le p90 reste publié, non noté |
| C3 | `text_size` ne lit aucun pixel et `subtitle_line_length` teste 42 quand la charte impose 38 : deux 100 structurels, à sortir du barème | **retenue pour l'un, refusée sur preuve pour l'autre**. `text_size` est bien un contrôle de non-régression, et c'est dit au § 3.5 — il reste noté parce que son travail est de refuser une **charte** qui casserait la lisibilité. `subtitle_line_length`, lui, n'est pas structurel : il est mesuré sur le `.ass` **produit**, et une faute de lecture de ce fichier a fait apparaître 142 fausses lignes trop longues pendant cette session — preuve que la mesure a du contenu |
| C4 | `text_contrast` découpe un bandeau fixe : un moteur qui déplace son texte fait sortir la mesure en `skipped`, et la lisibilité **gagne** en perdant son poids | **retenue** — quand `shotlist.json` annonce un texte et qu'aucun bandeau n'en porte, la note est 0 |
| C5 | `duree_vs_run` et `duree_vs_niche` portent la même cible : la famille note deux fois le même écart | **retenue** — `duree_vs_niche` sort `skipped` quand les cibles coïncident ou que `distribution_large` |

### D — qu'est-ce qui manque pour prédire la rétention ?

| # | Objection | Traitement |
|---|---|---|
| D1 | Titre et miniature, mesurés au registre et absents du banc, décident du clic → famille `emballage` | **retenue, différée à l'étape 21**, qui produit les variantes de titre et de miniature. Le banc note ce qui est *dans* la vidéo ; l'emballage a ses propres cibles (`titres.longueur_car.p90`, `miniatures.texte_mots`, contraste) et son propre signal (le CTR, disponible seulement par la Reporting API, étape 25) |
| D2 | `ruptures_s` porte « faite au banc (étape 15) » et le champ est vide : la cadence des ruptures manque | **retenue** — `cut_rhythm_by_minute` mesure le rythme par tranche de 60 s et sa pente, **sans le noter** : la cible est fixée à l'étape 16 |
| D3 | Le délai avant le premier mot n'est jamais mesuré : l'abandon des 3 s est visuel dans le banc, jamais sonore | **retenue** — `hook_first_word`, plafond 1,5 s |
| D4 | Part de la fin sans contenu (CTA, écran de fin) | **refusée pour l'instant, sur preuve** — la `shotlist` pave la piste sans trou (mesuré à l'étape 12.1 : 737,921 s pour 737,921 s), la mesure vaudrait 0 sur tout run. Le CTA et l'écran de fin sont produits par l'étape 16 ; la mesure y a sa place, pas avant |

**Objection non résolue, laissée ouverte.** Le contradicteur a raison sur un point qu'aucune
correction ne ferme : `subtitle_coverage` et `speech_rate` restent partiellement acquis par
construction, et `text_size` entièrement. Trois des vingt et une mesures notées rendront 100 à
presque tous les runs tant que la charte et le pipeline ne changent pas. Leur poids cumulé est
de 3 sur les 41 poids internes du barème — assumé, documenté, et à revoir à l'étape 26 avec le
reste : c'est la corrélation aux vues qui dira si elles méritent leur place.
