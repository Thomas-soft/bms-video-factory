# TRAJECTOIRES — ce qui sépare une chaîne qui décolle d'une chaîne qui meurt

Étape 3 · mesuré le 15/09/2026 sur `registre/data/` (API YouTube Data v3, collecte du 14/09/2026).
Calculs : `agentD.py` (sous-agent D), sortie complète hors dépôt. Aucune valeur n'est estimée.

**Biais central, corrigé partout.** Les vues sont un **cumul mesuré au 14/09/2026**, pas les vues au moment de la publication : une vidéo ancienne a eu plus de temps pour les accumuler. Deux corrections sont appliquées et signalées :
- `v/j` = vues cumulées ÷ âge en jours (comparaison à cadence d'accumulation) ;
- `vues méd. > 90 j` = médiane des seules vidéos de plus de 90 jours (comparaison à âge minimal égal).
Un trimestre dont l'âge médian est inférieur à 60 jours est marqué ⚠ : son classement est instable.

---

## 1. Duel 1 — CasiCreativo English (croît) vs Health Snippet (morte en 01/2025)

| | CasiCreativo English | Health Snippet |
|---|---|---|
| Abonnés (API, 14/09/2026) | 707 000 | 89 900 |
| Vidéos collectées | 57 (toutes) | 116 (toutes) |
| Première → dernière | 30/04/2021 → 09/09/2026 | 27/08/2020 → 14/01/2025 |
| **Vues méd. des vidéos > 90 j** | **271 617** (n = 52) | **3 223** (n = 116) |
| Durée médiane | 24 s à 314 s selon le trimestre | 200 s à 387 s, stable |
| Part de Shorts | 0 % jusqu'en 2024-Q2, 40-100 % ensuite | 0 % sur toute la vie de la chaîne |

Trimestres saillants (n = nombre de vidéos publiées) :

| Trimestre | CE n | CE durée (s) | CE v/j | CE %breakout | HS n | HS durée (s) | HS v/j | HS %breakout |
|---|---|---|---|---|---|---|---|---|
| 2021-Q2 | 2 | 142 | 4 310 | 50 % | 5 | 242 | 48,8 | 80 % |
| 2022-Q4 | 6 | 170 | 2 197 | 67 % | 7 | 223 | 2,1 | 14 % |
| 2023-Q1 | — | — | — | — | 12 | 214 | 43,4 | 75 % |
| 2024-Q2 | 2 | 107 | 585 | 50 % | 7 | 242 | 1,5 | 0 % |
| **2024-Q3** | **4** | **30** | **61,9** | **25 %** | 13 | 277 | 1,1 | 15 % |
| 2024-Q4 | 8 | 102 | 378 | 12 % | 13 | 339 | 1,0 | 8 % |
| 2025-Q1 | 7 | 95 | 102 | 0 % | 1 | 243 | 3,0 | 0 % |

**Ce qui se voit.** CasiCreativo English publie peu (57 vidéos en 5 ans, intervalle médian de 9 à 272 jours) et garde une médiane de 271 617 vues ; son seul effondrement mesuré coïncide avec le pivot vers l'ultra-court de 2024-Q3 (durée médiane 107 s → 30 s, 75 % de Shorts, v/j ÷ 9,5), partiellement corrigé dès le trimestre suivant. Health Snippet publie **régulièrement** (intervalle médian de 7 jours pendant quatre ans, 116 vidéos), ne fait jamais de Short, et meurt à 683 vues médianes par vidéo au dernier trimestre plein. Sa dérive de sujets est mesurable : `exercises/benefits` (2021) → `every day eating/happens to your body` (2023) → `shocking secrets/anti aging` (2024). **La régularité n'a pas sauvé Health Snippet ; la rareté n'a pas tué CasiCreativo.**

**Mort sans préavis.** Health Snippet passe de 13 vidéos (2024-Q4) à 1 (2025-Q1) puis 0 : aucun ralentissement progressif détectable dans les métadonnées. Ce qui décline, c'est la médiane de vues par vidéo, pas la cadence.

## 2. Duel 2 — Elias Yoder Amish (explose) vs Life According to Science (décrue)

| | Elias Yoder Amish | Life According to Science |
|---|---|---|
| Abonnés (API) | 358 000 | 80 800 |
| Vidéos collectées | 152 (toutes) | 126 (toutes) |
| Première vidéo | 17/05/2026 (chaîne de 4 mois) | 14/09/2025 |
| **Vues méd. des vidéos > 90 j** | **259 057** (n = 34) | **4 499** (n = 107) |
| Part de Shorts | 0 % | 0 % |

| Trimestre | EY n | EY durée (s) | EY v/j | EY %breakout | LS n | LS durée (s) | LS v/j | LS %breakout |
|---|---|---|---|---|---|---|---|---|
| 2025-Q3 | — | — | — | — | 8 | 778 | 16,8 | 25 % |
| 2025-Q4 | — | — | — | — | 43 | 1 188 | 40,2 | 54 % |
| 2026-Q1 | — | — | — | — | 32 | 1 012 | 12,3 | 28 % |
| 2026-Q2 | 57 | 1 274 | 1 170 | 63 % | 28 | 828 | 14,8 | 25 % |
| 2026-Q3 ⚠ | 95 | 1 263 | 419 | 8 % | 15 | 1 272 | 42,1 | 0 % |

**Ce qui se voit.** Elias Yoder ouvre avec **57 vidéos en 95 jours** (intervalle médian 0 jour : plusieurs publications le même jour), en **format long constant** (~21 min, 0 % de Short), et sort 63 % de breakouts au premier trimestre. Au trimestre suivant il monte à 95 vidéos (+ 67 %) : la part de breakouts tombe à 8 % et les v/j sont divisées par 2,8. Life According to Science fait le même mouvement un an plus tôt — cadence × 5,38 en 2025-Q4 (8 → 43 vidéos) et durée × 1,53 — avec un pic de vues médianes ce trimestre-là (5 894 → 11 550) suivi d'une **division par 4,3 au trimestre suivant** (2 680). Les deux chaînes prouvent le même mécanisme : **le volume achète un trimestre de visibilité, puis dilue la médiane par vidéo.**

---

## 3. Règles testables

`conf.` = confiance : forte (plusieurs chaînes, n élevé), moyenne (un duel, n ≥ 100 vidéos), faible (une chaîne ou n < 40).
`appliquée par` = étape de `ROADMAP.md` qui doit lire la règle.

| id | Règle (impérative, chiffrée) | Preuve mesurée | Ce qui la réfuterait | conf. | appliquée par |
|---|---|---|---|---|---|
| T1 | **Hypothèse, pas règle.** Ouvrir une chaîne par ≥ 50 vidéos en 90 jours en format long (durée médiane ≥ 1 200 s), 0 % de Short. | Elias Yoder : 57 vidéos / 95 j, 1 274 s, 0 % Short → 259 057 vues méd. (n = 34, vidéos > 90 j) | Une chaîne suivant ce régime 90 j et restant sous 50 000 vues médianes — **le seul test possible serait une chaîne BMS**, aucune autre chaîne du registre n'est dans ce régime | faible (1 chaîne, 4 mois) | aucune (à tester, pas à appliquer) |
| T2 | Piloter sur la **médiane de vues des vidéos de plus de 90 jours**, jamais sur le cumul de vues ni sur le nombre d'abonnés. | Morte/décrue : HS 3 223 (n = 116), LS 4 499 (n = 107). Vivantes : CE 271 617 (n = 52), EY 259 057 (n = 34) | Une chaîne > 100 k vues médianes qui meurt, ou < 5 k qui décolle | moyenne | etape_15, etape_25, etape_26 |
| T3 | Ne jamais faire passer une chaîne longue à l'ultra-court (≤ 30 s, ≥ 75 % de Shorts) en un trimestre. | CasiCreativo 2024-Q2 → Q3 : 107 s → 30 s, Shorts 50 % → 75 %, v/j 585 → 61,9 (÷ 9,5) | Le même pivot sans chute de v/j sur une autre chaîne | faible (1 chaîne) | etape_23.2 |
| T4 | Ne pas augmenter la cadence de plus de 60 % d'un trimestre à l'autre sans vérifier la part de breakouts du trimestre précédent. | EY 57 → 95 vidéos (+ 67 %) : breakouts 63 % → 8 %, v/j 1 170 → 419. LS 8 → 43 (× 5,38) : vues méd. 11 550 → 2 680 au trimestre suivant | Un doublement de cadence sans baisse de la médiane par vidéo | moyenne (2 chaînes) | etape_23.2, etape_25 |
| T5 | Ne jamais lire une part de breakouts comme une performance : elle est relative à la médiane de la chaîne elle-même, donc mécaniquement écrasée dès que cette médiane monte. Comparer les vues absolues normalisées par l'âge. | EY 63 % → 8 % pendant que la médiane de la chaîne passe de 116 968 à 11 513 ; LS 54 % → 28 % ; HS 80 % → 57 % → 0 %. **La retombée est un artefact de la définition autant qu'un signal** | Une part de breakouts qui monte alors que la médiane de la chaîne monte aussi | forte (arithmétique) | etape_25, etape_26 |
| T6 | Déclencher l'alerte de décrue sur la **médiane de vues**, pas sur la cadence : une chaîne peut mourir sans ralentir. | HS publie 13 vidéos en 2024-Q4 à 683 vues médianes, puis 1, puis 0. Aucun ralentissement avant l'arrêt | Une mort précédée d'au moins deux trimestres de cadence décroissante | faible (1 chaîne) | etape_25 |
| T7 | Ne jamais comparer deux vidéos ou deux trimestres en vues brutes quand l'écart d'âge médian dépasse 90 jours : normaliser par l'âge. | Âges médians par trimestre : 29 à 1 944 j (CE), 31 à 358 j (LS) ; sans correction, 2026-Q3 de CE affiche 11 429 v/j sur un âge médian de 29 j | Un classement brut identique au classement normalisé malgré un écart > 90 j | forte (mesuré sur les 4 chaînes) | etape_15, etape_20, etape_25 |
| T8 | Ne pas compter sur la régularité de publication comme facteur de survie : elle ne prédit rien ici. **Non testé à l'échelle du registre** — le test sur ≥ 10 chaînes demande une étiquette de survie par chaîne, que la collecte de l'étape 2 ne fournit pas (colonne `trajectoire` = « inconnue » pour 70 chaînes sur 74). | HS : intervalle médian 7 j pendant 4 ans → morte. CE : intervalle 9 à 272 j, irrégulier → 707 k abonnés | Un lien mesurable régularité ↔ survie sur ≥ 10 chaînes étiquetées | moyenne | etape_23.2 |
| T9 | Ne pas ouvrir une chaîne sur les Shorts par imitation : aucune des trajectoires mesurées ne les associe au décollage. | EY 0 % de Shorts (explosion) ; HS et LS 0 % (morte et décrue) ; CE : le seul trimestre à 75 % de Shorts est son pire (61,9 v/j) | Une chaîne du registre décollant avec ≥ 50 % de Shorts | moyenne | etape_23.2 |
| T10 | Optimiser la médiane de vues par vidéo avant le volume : le volume seul ne convertit pas en audience. | CE : 57 vidéos → 707 k abonnés, 271 617 vues méd. HS : 116 vidéos → 89,9 k abonnés, 3 223 vues méd. (× 84 d'écart de médiane pour 2× moins de vidéos) | Une chaîne avec plus de vidéos, une médiane plus basse et plus d'abonnés | moyenne | etape_20, etape_25 |
| T11 | Garder la durée médiane stable d'un trimestre à l'autre (± 30 %) : chaque rupture de format mesurée ici précède une baisse. | CE 107 → 30 s (÷ 3,6) → v/j ÷ 9,5. LS 778 → 1 188 s (× 1,53) → vues méd. ÷ 4,3 au trimestre suivant | Une rupture de durée > 30 % suivie d'une hausse de la médiane | moyenne (2 chaînes) | etape_12.1, etape_23.2 |
| T12 | Ne pas laisser dériver le champ lexical des titres : suivre l'indice de Jaccard des mots-clés entre trimestres et alerter sous 0,15 (**seuil arbitraire**, tiré d'une seule chaîne, à recalibrer à l'étape 20). | HS : `exercises/benefits` → `every day eating` → `shocking secrets/anti aging`, Jaccard tombant à 0,00 entre trimestres consécutifs, vues méd. 93 184 → 683 | Une dérive à Jaccard < 0,15 suivie d'une hausse durable de la médiane | faible | etape_20 |

## 4. Ce qui n'est pas prouvable avec ces données

1. **Rétention, CTR, impressions** — hors API Data v3 ; seule l'Analytics API de nos propres chaînes les donnera (étape 25).
2. **Causalité** — tout ce qui précède est corrélationnel. Un pivot et une chute au même trimestre ne prouvent pas que le pivot a causé la chute.
3. **Effet de l'algorithme et des politiques YouTube** — invisible dans les métadonnées ; les terminaisons de janvier 2026 peuvent expliquer des ruptures sans qu'on puisse les distinguer.
4. **Raisons réelles de l'arrêt de Health Snippet** — abandon, démonétisation, suspension : indiscernables.
5. **Qualité éditoriale, montage, voix, miniatures** — non mesurés ici (agents B et C traitent miniatures et hooks séparément, sur d'autres chaînes).
6. **Vues au moment de la publication** — seul le cumul au 14/09/2026 est connu ; toute courbe de démarrage est reconstruite, jamais observée.
7. **Short « poussé par le flux » vs vidéo courte ordinaire** — la durée ≤ 70 s n'est qu'un proxy ; l'API ne déclare pas le statut Short.
8. **Généralisation aux 74 chaînes** — ces règles viennent de 4 chaînes. T2, T4, T7 et T10 sont les seules qui s'appuient sur plus de 100 vidéos.
9. **Effet de la cadence à volume constant** — cadence et nombre de vidéos varient ensemble ; impossible de les séparer.
9 bis. **La part de breakouts n'est pas une performance** — elle se définit par rapport à la médiane de la chaîne elle-même : une chaîne qui monte voit mécaniquement sa part de breakouts chuter (T5). Ne jamais la comparer entre chaînes.
10. **Sources de trafic, démographie, part d'abonnés dans les vues** — hors API.
