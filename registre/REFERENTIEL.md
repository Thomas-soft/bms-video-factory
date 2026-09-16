# RÉFÉRENTIEL — cibles chiffrées par niche

Lecture humaine de `registre/REFERENTIEL.json`, le fichier que le code lit. Étape 3, mesuré le 15/09/2026.
Source : tableau de rythme de coupe P9 (`ROADMAP.md` § 3.3, 30 chaînes mesurées par l'équipe de Sofiane) + collecte de l'étape 2 (API YouTube Data v3, 74 chaînes, 21 919 vidéos, 349 transcriptions, 192 miniatures regardées).
**Aucune valeur de ce fichier n'est estimée.** Ce qui n'a pas été mesuré porte `a_mesurer: true`.

## 1. Les 8 niches

11 étiquettes de niche existaient dans `registre/chaines.csv`. Trois d'entre elles n'avaient qu'une seule chaîne et ont été fusionnées, sur preuve lexicale (mots-clés des titres), pas sur intuition :

| Étiquette d'origine | Devient | Preuve |
|---|---|---|
| `frugal` (Saving Savers) | `home_hacks` | mots-clés `hacks, grandma, life, grandpa, wish knew sooner` — « hacks » commun à la niche. Tranche aussi le doublon du PDF : la ligne `home_hacks` (3,8 s/plan) est retenue, la ligne `frugal` (6,9 s/plan) est un doublon qui collisionne avec Old Ways Chronicle |
| `yoder` (Elias Yoder Amish) | `home_hacks` | `amish, cheap, old, way, trick, genius, water, free` — 3 mots-clés communs avec la niche (`amish, without, never`) |
| `moreno` (Daniel Moreno) | `spiritualite` | `reality, dangerous, book, written, reveals, oldest, frequency, secret, elites` — **aucun** mot-clé commun avec `home_hacks` ; registre ésotérique, comme Library of Thoth |

La fusion `avatar_persona` (Moreno + Yoder ensemble) a été envisagée puis écartée : ces deux chaînes ne partagent qu'une **technique de production** (avatar), pas une audience. La technique est conservée comme variante de style, pas comme niche.

## 2. Cibles par niche

`rythme cible / montage` : médiane P9 de la niche / médiane après retrait des chaînes à plans > 3× la médiane (plateau, interview, image fixe). **Le code lit `cible_montage`**, `cible` sert de référence.
`cadence` : médiane de toutes les chaînes / **médiane des seules chaînes actives** sur 182 jours — c'est cette seconde valeur que le code lit (`cadence_par_semaine.cible`), la première tombant à 0 dès qu'une majorité de chaînes est inactive.
Durées, cadences, titres et breakouts excluent les Shorts (≤ 70 s). `breakouts` = part des vidéos à plus de 3× la médiane de leur propre chaîne.

| niche | ch | vidéos | rythme cible / montage (n) | durée méd (p25–p75) s | cadence méd/sem (**cible**) | jours · h UTC | titre car | hook mots · débit narration | breakouts |
|---|---|---|---|---|---|---|---|---|---|
| `histoire_doc` | 5 | 877 | 4,6 / 4,5 (5) | 1513 (296–2689) | 0,0 (1,52) | samedi/jeudi · 16h | 62 | 18 · 108 | 0,29 |
| `home_hacks` | 9 | 1835 | 8,6 / 6,9 (9) | 1083 (698–1408) | 1,65 (1,65) | mercredi/jeudi · 16h | 57 | 44 · 153 | 0,29 |
| `science_pop` | 9 | 2202 | 6,0 / 5,85 (5) | 648 (214–2754) | 0,96 (1,85) | mardi/samedi · 21h | 58 | 36 · 135 | 0,28 |
| `spiritualite` | 14 | 2374 | 13,2 / 11,4 (6) | 1870 (909–3181) | 1,63 (2,04) | mardi/vendredi · 18h | 70 | 40 · 150 | 0,20 |
| `true_crime` | 5 | 1608 | 21,8 / 15,7 (5) | 1528 (984–4066) | 6,65 (6,65) | vendredi/mercredi · 21h | 60 | 36 · 180 | 0,12 |
| `niche_monetisable_longevite` | 22 | 6654 | **aucune mesure** → repli 7,8 | 595 (166–1876) | 2,48 (2,85) | jeudi/vendredi · 13h | 55 | 46 · 172 | 0,19 |
| `niche_monetisable_complements_fr` | 5 | 505 | **aucune mesure** → repli 7,8 | 127 (93–178) | 1,65 (2,12) | jeudi/dimanche · 17h | 58 | 65 · 231 | 0,21 |
| `niche_monetisable_paris_sportifs` | 5 | 409 | **aucune mesure** → repli 7,8 | 538 (389–751) | 0,31 (0,38) | mercredi/lundi · 20h | 63 | 57 · 219 | 0,24 |

**Trois niches n'ont aucune mesure de rythme de coupe** (aucune de leurs chaînes n'est dans le tableau P9) : elles portent `cible: null`, `a_mesurer: true` et un repli de 7,8 s = médiane robuste des 30 chaînes mesurées. **Ce repli n'est pas une cible** : il existe pour que le code tourne, et doit être remplacé par une mesure au banc de l'étape 15.

Cas particuliers à connaître :
- `true_crime` : cadence 6,65/semaine et rythme 21,8 s viennent de Fox News, Law&Crime et Surviving The Survivor — des chaînes d'actualité et de plateau, pas des vidéos montées. Pour une chaîne BMS, lire `cible_montage` (15,7 s) et la cadence des chaînes produites (Ty Notts : 8,0 s/plan).
- `histoire_doc` : cadence médiane 0,0 car 3 chaînes sur 5 n'ont rien publié depuis 182 jours. Utiliser 1,52 (chaînes actives).
- `niche_monetisable_complements_fr` : 61 % de Shorts ; la durée médiane « longue » de 127 s reflète un corpus de vidéos très courtes.
- `histoire_doc` : débit de narration 108 mots/min sur n = 18 — **n faible** ; les documentaires parlent réellement plus lentement, mais la valeur reste fragile.
- Durées très dispersées (`p75/p25 > 4`) pour `histoire_doc` (9,1), `science_pop` (12,9) et `niche_monetisable_longevite` (11,3) : la médiane n'y est pas un mode, le champ `duree_s.distribution_large` le signale et l'étape 10 doit fixer la durée par chaîne, pas par niche.

## 3. Hooks — taxonomie (345 hooks classés, 74 chaînes)

Part globale sur l'ensemble du corpus ; les parts par niche sont dans le JSON.

| type | part | n | ce qui domine où |
|---|---|---|---|
| `in_medias_res` | 19,1 % | 66 | `true_crime` 64 %, `histoire_doc` 76 % |
| `question_contrarienne` | 16,8 % | 58 | `spiritualite` 28 %, `complements_fr` 17 % |
| `negation_du_sens_commun` | 13,9 % | 48 | `spiritualite` 31 % |
| `adresse_directe` | 9,6 % | 33 | `home_hacks` 18 % |
| `enjeu_personnel` | 8,7 % | 30 | `home_hacks` 21 %, `paris_sportifs` 21 % |
| `intro_chaine_neutre` | 8,1 % | 28 | `longevite` 15 % — type à éviter en production |
| `mystere_ouvert` | 7,5 % | 26 | `spiritualite` 13 % |
| `statistique_choc` | 3,8 % | 13 | — |
| `mise_en_scene_narrative` | 3,8 % | 13 | `science_pop` 22 % |
| `autorite_citee` | 3,8 % | 13 | — |
| `promesse_chiffree` | 2,6 % | 9 | `paris_sportifs` 25 % |
| `liste_annoncee` | 2,3 % | 8 | — |

Chaque type porte dans le JSON une définition opérationnelle, 2 à 4 règles vérifiables par script et des exemples verbatim.
`intro_chaine_neutre` porte `productible: false` : il est observé mais ne doit jamais être tiré pour un script.
**Boucles ouvertes** (« but before that… », « mais avant… ») : présentes dans 2,4 % (`science_pop`) à 13,6 % (`home_hacks`) des hooks, position médiane 24 s à 67 s ; médiane inter-niches **47,9 s** (n = 28), servie comme repli aux niches sans mesure. Le référentiel impose `boucles_minimum: 2` par script (étape 10), au-delà de l'usage observé : c'est une décision, pas une mesure.

## 4. Miniatures (192 miniatures codées, 20 chaînes, 8 niches)

| niche | mots de texte méd | part visage | palette | contraste | composition | marqueur | style dominant |
|---|---|---|---|---|---|---|---|
| `histoire_doc` | 3 | 0,65 | #1a1a1a #ffffff #808080 | moyen | centre | 0,10 | photo 0,95 |
| `home_hacks` | 4 | 0,73 | #ffffff #1a1a1a #1e5fd9 | élevé | droite | 0,43 | photo 0,57 |
| `science_pop` | 1,5 | 0,43 | #1a1a1a #ffffff #6b4423 | élevé | centre | 0,00 | photo 0,40 |
| `spiritualite` | 4 | 0,93 | #1a1a1a #d6221f #c9a227 | élevé | droite | 0,37 | illustration 0,63 |
| `true_crime` | 0 | 0,90 | #1a1a1a #1e5fd9 #808080 | moyen | centre | 0,05 | photo 0,95 |
| `niche_monetisable_longevite` | 1,5 | 0,60 | #1a1a1a #d6221f #ffffff | élevé | centre | 0,10 | photo 0,80 |
| `niche_monetisable_complements_fr` | 0 | 0,50 | #1a1a1a #2e7d32 #d6221f | moyen | centre | 0,00 | photo 1,00 |
| `niche_monetisable_paris_sportifs` | 3,5 | 0,90 | #f2c94c #1a1a1a #16213e | élevé | droite | 0,60 | photo 0,70 |

Palettes : estimation visuelle par familles de couleurs sur planches-contacts, pas une mesure pixel.

## 5. Comment le code s'en sert

La carte exacte champ → étape est dans `REFERENTIEL.json`, clé `consommateurs`. En résumé :

| Étape | Ce qu'elle lit | Ce qu'elle en fait |
|---|---|---|
| **10** — script | `sujets_porteurs`, `duree_s.cible` ± `tolerance` (0,15), `hooks.parts`, `hooks_taxonomie`, `mots_par_minute.mediane` | choisit le sujet dans les données (jamais au hasard), tire un type de hook selon les parts de la niche, dimensionne le script en mots = durée × mots/minute, impose ≥ 2 boucles ouvertes |
| **12.1** — découpage | `rythme_coupe_s.cible_montage`, `.min`, `.max`, `.facteur_hook` (0,7) | durée médiane de plan à ± 10 % de la cible, plans du hook à ≤ 0,7 × cible |
| **15** — banc | toutes les cibles + `n` | compare la vidéo rendue aux cibles de sa niche ; toute cible marquée `a_mesurer` ne doit pas être notée comme un écart |
| **16** — rétention | `hooks_taxonomie` (règles vérifiables), `hooks.longueur_mots`, `boucle_ouverte.position_s_mediane` | vérifie le script avant la voix, rejette et régénère |
| **20** — sujets | `sujets_porteurs`, `densite_breakouts`, `ratio_top1_median`, règles T7/T10/T12 | file de sujets notée, détection des trous multilingues, alerte de dérive lexicale |
| **21** — titres et miniatures | `titres.patrons`, `titres.longueur_car`, `miniatures.*` | 8 titres par patron de la niche, 3 miniatures notées sur contraste, mots de texte, composition |
| **23.2** — programmation | `cadence_par_semaine`, `creneaux`, `regles_trajectoire` | cadence et créneaux par chaîne, garde-fous T1/T3/T4/T8/T9/T11 |

## 6. Limites — à lire avant de traiter une valeur comme une cible

1. **Pas de groupe témoin.** Les miniatures (10 par chaîne) et les transcriptions (5 par chaîne) sont par construction celles des vidéos **les plus vues** : 188 miniatures sur 192 et 331 hooks sur 345 sont des « breakouts ». Les motifs et les parts de hooks décrivent **ce que font les meilleures vidéos**, pas ce qui les sépare des mauvaises. Toute comparaison gagnant/perdant est impossible avec cet échantillon.
2. **29 chaînes sur 74 sont tronquées** à leurs 500 vidéos les plus récentes : leurs agrégats décrivent l'activité récente.
3. **`mots_par_minute` est le débit de narration mesuré sur la transcription entière** (310 transcriptions, mots hors tags non verbaux ÷ durée parlée). Le débit des 60 premières secondes est conservé à part (`debut_60s`) : il caractérise l'ouverture, générique compris, et ne doit pas servir à dimensionner un script.
4. **Les patrons de titre** viennent de 10 heuristiques regex : parts non exclusives, `nom_propre_en_tete` sur-détecte l'anglais en title case. À lire comme un plafond.
5. **`rythme_coupe_s` n'est pas recalculable ici** : il vient du tableau P9, mesuré ailleurs, non reproductible depuis `registre/data/`.
6. **Purge API au 14/10/2026** (`docs/CONFORMITE.md` § 9) : les données sources disparaissent, ce référentiel — mesure dérivée — se conserve.
7. **La taxonomie des hooks est classée par un seul codeur**, sans double codage : les frontières `negation_du_sens_commun` / `mystere_ouvert` et `in_medias_res` / `mise_en_scene_narrative` sont poreuses, leurs parts se lisent à quelques points près. 4 transcriptions sur 349 (coréen, arabe) étaient illisibles et sont exclues.
8. `n faible` (< 20) est marqué dans le JSON partout où il s'applique.

## 7. Objections du contradicteur et leur traitement

Un sous-agent contradicteur (vague 2) a relu `REFERENTIEL.json`, `REFERENTIEL.md`, `TRAJECTOIRES.md` et les « Terminé quand » des étapes 10, 12.1, 15, 16, 20 et 21. 20 objections, toutes traitées : 18 corrigées, 2 corrigées autrement que proposé, 1 refusée sur preuve.

| # | Objection | Traitement |
|---|---|---|
| 1 | bloquant — le JSON livré n'était pas la sortie du script corrigé : `ruptures_s`, `densite_faits_par_minute`, `dispersion_p75_p25` absents | **corrigé** — script relancé, les 4 champs sont présents |
| 2 | bloquant — `cible_montage` nulle pour 3 niches, le repli vivait dans un champ non listé | **corrigé** — `ordre_de_lecture.rythme_coupe_s` = `cible_montage` → `cible` → `fallback_provisoire_s`, et le champ est ajouté aux consommateurs de l'étape 12.1 |
| 3 | bloquant — `histoire_doc.boucle_ouverte.position_s_mediane = null` alors que 2 boucles sont exigées | **corrigé autrement** — pas la valeur 50 s proposée : `position_s_repli = 47,9 s`, **médiane inter-niches mesurée** sur les 28 boucles du corpus, avec son origine |
| 4 | bloquant — `titres.longueur_car.max` contenait le p90 | **corrigé** — `max` supprimé, `p90` + `plafond_recommande` + `plafond_youtube: 100` |
| 5 | bloquant — `indetermine` présent dans les parts sans exister dans la taxonomie ; `intro_chaine_neutre` tirable | **corrigé** — `indetermine` retiré et parts renormalisées (`part_indeterminee` conservée à part), `productible: false` sur `intro_chaine_neutre` |
| 6 et 13 | bloquant — le débit servant à dimensionner les scripts mesurait 60 s de générique | **corrigé par une mesure** — pas la valeur forfaitaire 150 proposée : débit de narration **remesuré sur 310 transcriptions entières** (mots ÷ durée parlée), 108 à 231 mots/min selon la niche ; le débit d'ouverture est relégué dans `debut_60s` |
| 7 | bloquant — `histoire_doc.cadence.mediane = 0,0` | **corrigé** — `cadence_par_semaine.cible` = médiane des chaînes actives, sur toutes les niches |
| 8 | sérieux — `min`/`max` calculés en incluant les valeurs que `cible_montage` écarte | **corrigé** — min/max recalculés sur l'ensemble élagué (spiritualité : 73,9 → 16,8 s) |
| 9 | sérieux — `spiritualite.cible_montage = 11,4` serait fixée par la seule chaîne réaffectée (Daniel Moreno) | **refusé, sur preuve** — test de retrait d'une chaîne : l'écart maximal est de **1,8 s sur 11,4 (16 %)**, et retirer Moreno laisse la médiane à 11,4. Le champ `cible_montage_robustesse` publie le test ; `sensible_a_une_chaine: false` |
| 10 et 11 | sérieux — `n_faible` absent sur plusieurs blocs, et jamais calculé sur le nombre de chaînes | **corrigé** — `n_faible` sur rythme, longueur de hook, boucle ouverte et miniatures ; `n_chaines_faible` (≤ 5) par niche et (< 3) sur les miniatures |
| 12 | sérieux — palettes en hex exacts issus d'une estimation visuelle ; contraste catégoriel alors que l'étape 21 note en WCAG | **corrigé** — `precision_palette` explicite, `contraste_ratio_cible: 4,5` (WCAG AA) ajouté comme décision, distinct du jugement visuel |
| 14 | sérieux — sujets porteurs pollués par des titres non thématiques à ratio absurde | **corrigé autrement** — le filtre proposé (ratio ≤ 100) supprimait de vrais succès (6,6 M de vues). Cause réelle traitée : **exclusion des chaînes dont la médiane est < 1 000 vues** (le ratio y est du bruit) + vidéos de moins de 30 jours écartées, garde appliquée avant classement. 15 sujets par niche, `vues_medianes_chaine` publiée avec chaque entrée |
| 15 | sérieux — l'étape 15 doit comparer des niveaux sonores et une couverture de sous-titres sans cible | **corrigé** — bloc `production` (loudness −14 LUFS, true peak −1 dBTP, couverture 1,0, silence `a_mesurer`), chaque valeur étiquetée par son origine : **aucune ne vient du registre**, l'audio des chaînes tierces n'étant jamais téléchargé |
| 16 | sérieux — T5 circulaire | **corrigé** — T5 réécrite : la part de breakouts est relative à la médiane de la chaîne, donc mécaniquement écrasée quand celle-ci monte ; devient une mise en garde de lecture (confiance forte, arithmétique) |
| 17 | sérieux — T1 non testable ailleurs que sur une chaîne BMS | **corrigé** — T1 passe en `statut: hypothese a tester`, `appliquee_par` vidé |
| 18 | mineur — T8 testable mais non testé ; T12 seuil arbitraire | **corrigé en partie** — le test de T8 exige une étiquette de survie par chaîne que la collecte ne fournit pas (`trajectoire` = « inconnue » pour 70 chaînes sur 74) : consigné dans la règle. T12 porte `seuil_arbitraire: true` |
| 19 | mineur — deux densités de breakouts sans définition | **corrigé** — les deux champs sont définis ; l'étape 20 lit la médiane par chaîne |
| 20 | mineur — n = 13 dans le .md contre 14 dans le JSON ; miniatures avatar recomptées | **corrigé** — le .md donne le n mesuré (18, débit de narration) ; `variantes_style.avatar.recompte: true` |

Les deux arbitrages de fusion de niches (`frugal` et `yoder` → `home_hacks`, `moreno` → `spiritualite`) ont été validés par le contradicteur sur la preuve lexicale.

**Objection non résolue, laissée ouverte :** aucune comparaison gagnant/perdant n'est possible sur les miniatures et les hooks (§ 6.1). Y remédier exige de collecter des miniatures et des transcriptions de vidéos **médianes et faibles** des mêmes chaînes — faisable à l'étape 16, qui relit le registre. Tant que ce n'est pas fait, les « motifs gagnants » restent des motifs des vidéos les plus vues.
