# Sujets — BMS History EN (`bms-histoire-en`)

Généré le 2026-09-20 par `factory editorial topics --channel bms-histoire-en` en 33 s.

**Ce que ces chiffres sont, et ce qu'ils ne sont pas.** Les percées sont **mesurées** dans l'entrepôt. Les clusters sont **produits par un modèle** (`intfloat/multilingual-e5-small`) et un seuil de distance (`0.12`) : un autre seuil donnerait un autre découpage. Les trous sont des absences **dans l'échantillon des 74 chaînes suivies**, jamais dans « YouTube ». Le score est une pondération d'opinions documentées dans `config/editorial.yaml` : il ordonne des candidats, il ne prouve rien.

## Mesures de l'exécution

- **Corpus** — 5604 vidéos publiées dans les 180 derniers jours chez les chaînes suivies (en 5110, fr 461, tr 28, es 5).
- **Percées** — 943 vidéos à ≥ 3 × la médiane de leur chaîne dans une fenêtre d'âge de ±30 % ; 455 vidéos **non notées** faute de 5 comparables. Base : vues observées au dernier instantané — views_d7/d30 NULL faute d'un second jour de collecte.
- **Clusters** — 738 groupes d'au moins 2 vidéos ; 904 vidéos restées isolées (comptées, non classées).
- **Trous** — 15 multilingue(s), 47 de demande, 6 résurgence(s).
- **Embeddings** — 0 vecteurs calculés, 5604 relus en cache, 0 s.
- **LLM** — 12 appels, dont 12 servis par le cache ; **0 s réellement calculées** (607 s cumulées si l'on compte la durée d'origine des appels mis en cache).

> ⚠️ Aucune vidéo en it dans la fenêtre de 180 jours. Les chaînes suivies dans ces langues n'ont pas publié récemment : le trou multilingue y est **non mesurable**, pas inexistant.

> ⚠️ `views_d7` et `views_d30` sont NULL sur tout le corpus (un seul jour de collecte en base). Les percées sont mesurées sur les vues observées au dernier instantané, à âge comparable.

## File de sujets — 30 propositions

| # | score | sujet | angle | cluster | lacune | preuve |
|---|---|---|---|---|---|---|
| 1 | **0.799** | Thought Experiments That Changed Physics | recit — The video tells the dramatic story of how a simple mental scenario dismantled centuries of accepted physical law | `c1012` Physics Thought Experiments and Debates | demande | 2 vidéos · 1 chaînes · 14 276 842 vues · 0 percées · en |
| 2 | **0.799** | Thought Experiments That Changed Physics | comparatif_chiffre — We compare the theoretical outcomes of these debates with modern observational data to quantify the | `c1012` Physics Thought Experiments and Debates | demande | 2 vidéos · 1 chaînes · 14 276 842 vues · 0 percées · en |
| 3 | **0.795** | The Geopolitics of the Persian Conflict | test — This segment tests the credibility of current invasion threats by analyzing historical precedents and intelligenc | `c0459` Iran War Invasion Threats | demande | 4 vidéos · 1 chaînes · 13 904 035 vues · 2 percées · en |
| 4 | **0.795** | The Geopolitics of the Persian Conflict | contrarien — Evidence suggests that the perceived threat of invasion is a strategic distraction rather than an imminent  | `c0459` Iran War Invasion Threats | demande | 4 vidéos · 1 chaînes · 13 904 035 vues · 2 percées · en |
| 5 | **0.782** | When Circuit Failure Becomes Fatal | contrarien — The documentary argues that modern circuit safety protocols have eliminated the fatal risks depicted in his | `c1014` Electrical Engineering Scary Charts | demande | 2 vidéos · 1 chaînes · 7 146 446 vues · 0 percées · en |
| 6 | **0.782** | When Circuit Failure Becomes Fatal | recit — A narrative journey traces the evolution of safety standards from the deadly early 20th-century experiments to t | `c1014` Electrical Engineering Scary Charts | demande | 2 vidéos · 1 chaînes · 7 146 446 vues · 0 percées · en |
| 7 | **0.763** | Determining the Edge of Chaos | contrarien — The argument challenges the notion that true randomness exists, proposing instead that all systems follow h | `c0134` Randomness and Predictability in Systems | demande | 2 vidéos · 1 chaînes · 4 785 306 vues · 0 percées · en |
| 8 | **0.763** | Determining the Edge of Chaos | recit — A story unfolds through the eyes of a mathematician who discovers a pattern within a system previously thought t | `c0134` Randomness and Predictability in Systems | demande | 2 vidéos · 1 chaînes · 4 785 306 vues · 0 percées · en |
| 9 | **0.756** | The Science of Cosmic Alignment | comparatif_chiffre — The analysis compares statistical probabilities of random cosmic events against the frequency of al | `c0135` Universe and Manifestation | demande | 2 vidéos · 2 chaînes · 5 915 234 vues · 0 percées · en |
| 10 | **0.756** | The Science of Cosmic Alignment | test — The video tests whether specific planetary alignments can be isolated as the primary cause for sudden changes in  | `c0135` Universe and Manifestation | demande | 2 vidéos · 2 chaînes · 5 915 234 vues · 0 percées · en |
| 11 | **0.646** | The Convergence of Body and Mind | comparatif_chiffre — The report contrasts recovery rates in patients undergoing physical therapy with those receiving on | `c0342` Physics Medicine and Psychology | resurgence | 17 vidéos · 1 chaînes · 6 569 602 vues · 9 percées · en |
| 12 | **0.646** | The Convergence of Body and Mind | test — The investigation tests the validity of using psychological frameworks to predict physical deterioration in chron | `c0342` Physics Medicine and Psychology | resurgence | 17 vidéos · 1 chaînes · 6 569 602 vues · 9 percées · en |
| 13 | **0.623** | From Amateur to Elite: The Marathon Evolution | comparatif_chiffre — A statistical comparison of training paces and finish times between the first and modern marathon e | `c0585` First Marathon Training Journey | multilingue | 5 vidéos · 1 chaînes · 34 398 vues · 2 percées · fr |
| 14 | **0.623** | From Amateur to Elite: The Marathon Evolution | recit — The chronological story of how a single race transformed into a global endurance phenomenon. | `c0585` First Marathon Training Journey | multilingue | 5 vidéos · 1 chaînes · 34 398 vues · 2 percées · fr |
| 15 | **0.608** | The Hidden History of Ancient Spiritual Rituals | recit — A narrative journey through the forgotten ceremonies that once defined ancient healing practices. | `c0324` Spiritual Healing and Secrets | multilingue | 31 vidéos · 1 chaînes · 34 737 vues · 3 percées · fr |
| 16 | **0.608** | The Hidden History of Ancient Spiritual Rituals | contrarien — An argument debunking the myth that modern spiritual techniques are superior to historical methods. | `c0324` Spiritual Healing and Secrets | multilingue | 31 vidéos · 1 chaînes · 34 737 vues · 3 percées · fr |
| 17 | **0.602** | The Science of Fluid Balance | recit — Following a medical team as they monitor electrolyte shifts in a high-altitude expedition. | `c0586` Electrolytes and Hydration Facts | multilingue | 5 vidéos · 2 chaînes · 45 502 vues · 2 percées · fr |
| 18 | **0.602** | The Science of Fluid Balance | comparatif_chiffre — Measuring the hydration efficiency of natural foods versus synthetic electrolyte tablets. | `c0586` Electrolytes and Hydration Facts | multilingue | 5 vidéos · 2 chaînes · 45 502 vues · 2 percées · fr |
| 19 | **0.600** | Fueling the Modern Body | test — Testing the actual absorption rates of popular protein sources against their marketing claims. | `c0358` Healthy Protein Recipes | multilingue | 48 vidéos · 2 chaînes · 127 776 vues · 9 percées · fr |
| 20 | **0.600** | Fueling the Modern Body | comparatif_chiffre — Calculating the cost per gram of essential amino acids across three distinct dietary approaches. | `c0358` Healthy Protein Recipes | multilingue | 48 vidéos · 2 chaînes · 127 776 vues · 9 percées · fr |
| 21 | **0.594** | Surviving the Limits of Human Scale | contrarien — The documentary refutes the idea that extreme body weight is solely a matter of willpower, highlighting met | `c0540` Investigating Extreme Body Weight and | — | 10 vidéos · 1 chaînes · 79 156 901 vues · 9 percées · en |
| 22 | **0.594** | Surviving the Limits of Human Scale | recit — A gripping account follows a medical team navigating the ethical and logistical minefield of treating patients a | `c0540` Investigating Extreme Body Weight and | — | 10 vidéos · 1 chaînes · 79 156 901 vues · 9 percées · en |
| 23 | **0.593** | The Truth in Supplement Marketing | contrarien — Debunking the notion that expensive branded powders offer superior results to generic alternatives. | `c0286` Whey Protein Reviews and Scams | multilingue | 127 vidéos · 1 chaînes · 127 097 vues · 21 percées · fr |
| 24 | **0.593** | The Truth in Supplement Marketing | test — Conducting a blind taste and purity analysis on the most controversial products in the market. | `c0286` Whey Protein Reviews and Scams | multilingue | 127 vidéos · 1 chaînes · 127 097 vues · 21 percées · fr |
| 25 | **0.592** | Reality Check: When Physics Breaks, What Happens Next? | contrarien — Popular theories suggesting time travel creates paradoxes are mathematically impossible due to entropy cons | `c0458` Hypothetical Physics and Science Scenarios | — | 2 vidéos · 1 chaînes · 21 935 982 vues · 0 percées · en |
| 26 | **0.592** | Reality Check: When Physics Breaks, What Happens Next? | comparatif_chiffre — Comparing energy requirements for fictional wormholes against current global power output shows the | `c0458` Hypothetical Physics and Science Scenarios | — | 2 vidéos · 1 chaînes · 21 935 982 vues · 0 percées · en |
| 27 | **0.582** | The Invisible War: How Signal Interference Shapes Modern Conflict | recit — The untold story of how a single jamming device once caused a multi-million dollar military operation to fail. | `c0063` GPS Jamming and Technology Anomalies | — | 2 vidéos · 1 chaînes · 20 049 978 vues · 1 percées · en |
| 28 | **0.582** | The Invisible War: How Signal Interference Shapes Modern Conflict | test — We deploy a portable jammer in a controlled urban environment to measure exactly which devices lose connectivity  | `c0063` GPS Jamming and Technology Anomalies | — | 2 vidéos · 1 chaînes · 20 049 978 vues · 1 percées · en |
| 29 | **0.581** | The Unseen Routine of a Champion | contrarien — Arguing that the champion's greatest strength lies in her disciplined boredom rather than explosive talent. | `c0192` Cassandre Beaugrand Daily Life | multilingue | 9 vidéos · 2 chaînes · 134 439 vues · 2 percées · fr |
| 30 | **0.581** | The Unseen Routine of a Champion | recit — A chronological account of a single day that reveals the hidden sacrifices behind public success. | `c0192` Cassandre Beaugrand Daily Life | multilingue | 9 vidéos · 2 chaînes · 134 439 vues · 2 percées · fr |

### Décomposition des cinq premiers

**1. Thought Experiments That Changed Physics** — score 0.799
- *Angle* — recit — The video tells the dramatic story of how a simple mental scenario dismantled centuries of accepted physical laws.
- *Composantes* — force_cluster 0.87×0.25 · velocite 0.79×0.2 · lacune 0.80×0.25 · demande 0.68×0.15 · fit 0.81×0.15 = 0.799 ; malus de répétition −0.000 (le plus proche : « Mysteries of the Universe », cos 0.85).
- *Fit* — cosinus aux mots-clés de la niche 0.81.
- *Lacune* — 1 vidéo(s) de moins de 90 j chez les chaînes suivies  pour une demande de 83 036 vues Wikipédia/mois (seed « Quantum mechanics »).
- *Demande* — seed Wikipédia le plus proche « Quantum mechanics », 83 036 vues/mois (proxy : les lecteurs de Wikipédia ne sont pas les spectateurs de YouTube).
- *Vidéos sources* — Veritasium [en] 11 432 812 vues, ratio 1.9× ; Veritasium [en] 2 844 030 vues.

**2. Thought Experiments That Changed Physics** — score 0.799
- *Angle* — comparatif_chiffre — We compare the theoretical outcomes of these debates with modern observational data to quantify the shift in scientific consensus.
- *Composantes* — force_cluster 0.87×0.25 · velocite 0.79×0.2 · lacune 0.80×0.25 · demande 0.68×0.15 · fit 0.81×0.15 = 0.799 ; malus de répétition −0.000 (le plus proche : « Mysteries of the Universe », cos 0.85).
- *Fit* — cosinus aux mots-clés de la niche 0.81.
- *Lacune* — 1 vidéo(s) de moins de 90 j chez les chaînes suivies  pour une demande de 83 036 vues Wikipédia/mois (seed « Quantum mechanics »).
- *Demande* — seed Wikipédia le plus proche « Quantum mechanics », 83 036 vues/mois (proxy : les lecteurs de Wikipédia ne sont pas les spectateurs de YouTube).
- *Vidéos sources* — Veritasium [en] 11 432 812 vues, ratio 1.9× ; Veritasium [en] 2 844 030 vues.

**3. The Geopolitics of the Persian Conflict** — score 0.795
- *Angle* — test — This segment tests the credibility of current invasion threats by analyzing historical precedents and intelligence failures.
- *Composantes* — force_cluster 0.87×0.25 · velocite 0.67×0.2 · lacune 0.80×0.25 · demande 0.78×0.15 · fit 0.83×0.15 = 0.795 ; malus de répétition −0.000 (le plus proche : « When History Predicts Our Demise », cos 0.85).
- *Fit* — cosinus aux mots-clés de la niche 0.83.
- *Lacune* — 2 vidéo(s) de moins de 90 j chez les chaînes suivies  pour une demande de 186 702 vues Wikipédia/mois (seed « Cold War »).
- *Demande* — seed Wikipédia le plus proche « Cold War », 186 702 vues/mois (proxy : les lecteurs de Wikipédia ne sont pas les spectateurs de YouTube).
- *Vidéos sources* — The Diary Of A CEO [en] 7 299 182 vues, ratio 17.7× **percée** ; The Diary Of A CEO [en] 5 842 953 vues, ratio 15.7× **percée** ; The Diary Of A CEO [en] 478 113 vues, ratio 1.1×.

**4. The Geopolitics of the Persian Conflict** — score 0.795
- *Angle* — contrarien — Evidence suggests that the perceived threat of invasion is a strategic distraction rather than an imminent military reality.
- *Composantes* — force_cluster 0.87×0.25 · velocite 0.67×0.2 · lacune 0.80×0.25 · demande 0.78×0.15 · fit 0.83×0.15 = 0.795 ; malus de répétition −0.000 (le plus proche : « When History Predicts Our Demise », cos 0.85).
- *Fit* — cosinus aux mots-clés de la niche 0.83.
- *Lacune* — 2 vidéo(s) de moins de 90 j chez les chaînes suivies  pour une demande de 186 702 vues Wikipédia/mois (seed « Cold War »).
- *Demande* — seed Wikipédia le plus proche « Cold War », 186 702 vues/mois (proxy : les lecteurs de Wikipédia ne sont pas les spectateurs de YouTube).
- *Vidéos sources* — The Diary Of A CEO [en] 7 299 182 vues, ratio 17.7× **percée** ; The Diary Of A CEO [en] 5 842 953 vues, ratio 15.7× **percée** ; The Diary Of A CEO [en] 478 113 vues, ratio 1.1×.

**5. When Circuit Failure Becomes Fatal** — score 0.782
- *Angle* — contrarien — The documentary argues that modern circuit safety protocols have eliminated the fatal risks depicted in historical electrical engineering charts.
- *Composantes* — force_cluster 0.82×0.25 · velocite 0.79×0.2 · lacune 0.80×0.25 · demande 0.68×0.15 · fit 0.78×0.15 = 0.782 ; malus de répétition −0.000 (le plus proche : « When History Predicts Our Demise », cos 0.86).
- *Fit* — cosinus aux mots-clés de la niche 0.78.
- *Lacune* — 2 vidéo(s) de moins de 90 j chez les chaînes suivies  pour une demande de 83 036 vues Wikipédia/mois (seed « Quantum mechanics »).
- *Demande* — seed Wikipédia le plus proche « Quantum mechanics », 83 036 vues/mois (proxy : les lecteurs de Wikipédia ne sont pas les spectateurs de YouTube).
- *Vidéos sources* — Veritasium [en] 5 750 143 vues, ratio 1.5× ; Veritasium [en] 1 396 303 vues.

## Trous multilingues — à produire en anglais

**Le modèle des réseaux Thoth, automatisé, et dans un seul sens.** Un thème qui marche en fr, es, it et que les chaînes en suivies n'ont pas traité (≤ 1 vidéo) vaut le plus haut barème de lacune. L'anglais est la seule langue de production (`ROADMAP.md` § 3.1, arbitrage d'Alek du 15/09/2026) : le sens inverse n'est pas cherché. **Le thème se reprend, jamais le script ni le titre** (`docs/CONFORMITE.md` § 4-5).

| cluster | thème | percées source | vidéos EN | vues source | exemple |
|---|---|---|---|---|---|
| `c0204` | Stockholm Adventure Recap | 2 (fr) | 0 | 149 301 | Nutripure [fr], 86 174 vues |
| `c0192` | Cassandre Beaugrand Daily Life | 2 (fr) | 0 | 133 395 | Nutripure [fr], 84 790 vues |
| `c0358` | Healthy Protein Recipes | 9 (fr) | 0 | 105 606 | Nutripure [fr], 44 206 vues |
| `c0286` | Whey Protein Reviews and Scams | 21 (fr) | 0 | 61 519 | Quentin fitlife [fr], 14 412 vues |
| `c0586` | Electrolytes and Hydration Facts | 2 (fr) | 0 | 43 723 | Nutri&Co [fr], 42 668 vues |
| `c0212` | Isotonic Drinks for Athletes | 2 (fr) | 0 | 36 888 | Nutri&Co [fr], 21 698 vues |
| `c0324` | Spiritual Healing and Secrets | 3 (fr) | 0 | 12 721 | Bibliothèque Gnostique [fr], 6 567 vues |
| `c0585` | First Marathon Training Journey | 2 (fr) | 0 | 31 664 | Nutri&Co [fr], 19 340 vues |
| `c0086` | Sports Recovery and Routines | 2 (fr) | 0 | 22 088 | Nutri&Co [fr], 20 966 vues |
| `c0111` | Wellness Lifestyle and Supplements | 10 (fr) | 0 | 12 904 | Nutripure [fr], 4 204 vues |
| `c0334` | Fenugreek Benefits and Safety | 3 (fr) | 0 | 7 451 | Nutripure [fr], 4 904 vues |
| `c0624` | Essential Supplements for Muscles | 2 (fr) | 0 | 4 576 | Nutri&Co [fr], 3 183 vues |
| `c0225` | Sources of Vitamins and Minerals | 3 (fr) | 0 | 3 378 | Nutripure [fr], 1 249 vues |
| `c0165` | Benefits and Side Effects of | 2 (fr) | 0 | 2 252 | Nutripure [fr], 1 214 vues |
| `c0411` | Side Effects of Vitamins D3 | 2 (fr) | 0 | 1 875 | Nutripure [fr], 1 165 vues |

## Demande sans offre — 47 cluster(s)

| cluster | thème | détail |
|---|---|---|
| `c0291` | Apocalyptic World War Predictions | 2 vidéo(s) de moins de 90 j chez les chaînes suivies  pour une demande de 186 702 vues Wikipédia/mois (seed « Cold War ») |
| `c1012` | Physics Thought Experiments and Debates | 1 vidéo(s) de moins de 90 j chez les chaînes suivies  pour une demande de 83 036 vues Wikipédia/mois (seed « Quantum mechanics ») |
| `c0459` | Iran War Invasion Threats | 2 vidéo(s) de moins de 90 j chez les chaînes suivies  pour une demande de 186 702 vues Wikipédia/mois (seed « Cold War ») |
| `c1014` | Electrical Engineering Scary Charts | 2 vidéo(s) de moins de 90 j chez les chaînes suivies  pour une demande de 83 036 vues Wikipédia/mois (seed « Quantum mechanics ») |
| `c0135` | Universe and Manifestation | 1 vidéo(s) de moins de 90 j chez les chaînes suivies  pour une demande de 83 036 vues Wikipédia/mois (seed « Quantum mechanics ») |
| `c0134` | Randomness and Predictability in Systems | 1 vidéo(s) de moins de 90 j chez les chaînes suivies  pour une demande de 83 036 vues Wikipédia/mois (seed « Quantum mechanics ») |
| `c0185` | ~ amish setup 2hr deadly | 0 vidéo(s) de moins de 90 j chez les chaînes suivies  pour une demande de 87 724 vues Wikipédia/mois (seed « Amish ») |
| `c0649` | ~ jonny thomson according debate | 2 vidéo(s) de moins de 90 j chez les chaînes suivies  pour une demande de 117 055 vues Wikipédia/mois (seed « Gnosticism ») |
| `c0364` | ~ audible framedbyexistence original space | 0 vidéo(s) de moins de 90 j chez les chaînes suivies  pour une demande de 85 796 vues Wikipédia/mois (seed « Big Bang ») |
| `c0900` | ~ brian consciousness debate end | 2 vidéo(s) de moins de 90 j chez les chaînes suivies  pour une demande de 83 036 vues Wikipédia/mois (seed « Quantum mechanics ») |
| `c0578` | ~ torrential across country creating | 2 vidéo(s) de moins de 90 j chez les chaînes suivies  pour une demande de 83 421 vues Wikipédia/mois (seed « Vikings ») |
| `c0387` | ~ amish bill buying can | 0 vidéo(s) de moins de 90 j chez les chaînes suivies  pour une demande de 87 724 vues Wikipédia/mois (seed « Amish ») |
| `c0203` | ~ big lie impressive result | 2 vidéo(s) de moins de 90 j chez les chaînes suivies  pour une demande de 85 796 vues Wikipédia/mois (seed « Big Bang ») |
| `c0469` | ~ bill breaking centers' considering | 2 vidéo(s) de moins de 90 j chez les chaînes suivies  pour une demande de 85 451 vues Wikipédia/mois (seed « NASA ») |
| `c0460` | ~ fox highlights news september | 2 vidéo(s) de moins de 90 j chez les chaînes suivies  pour une demande de 139 945 vues Wikipédia/mois (seed « Solar System ») |

## Résurgences — 6 cluster(s)

| cluster | thème | détail |
|---|---|---|
| `c0342` | Physics Medicine and Psychology | indice de vélocité 18.80 sur 6 vidéo(s) récente(s) contre 7.63 sur 11 ancienne(s) (×2.5) — indice = vélocité / médiane du décile d'âge, sans quoi la mesure ne mesure que l'âge |
| `c0170` | ~ crime true cases stories | indice de vélocité 16.66 sur 2 vidéo(s) récente(s) contre 7.45 sur 5 ancienne(s) (×2.2) — indice = vélocité / médiane du décile d'âge, sans quoi la mesure ne mesure que l'âge |
| `c0279` | ~ tyrosine brain acid amino | indice de vélocité 0.48 sur 3 vidéo(s) récente(s) contre 0.28 sur 7 ancienne(s) (×1.7) — indice = vélocité / médiane du décile d'âge, sans quoi la mesure ne mesure que l'âge |
| `c0038` | ~ kidney kidneys disease foods | indice de vélocité 1.50 sur 3 vidéo(s) récente(s) contre 0.61 sur 9 ancienne(s) (×2.5) — indice = vélocité / médiane du décile d'âge, sans quoi la mesure ne mesure que l'âge |
| `c0348` | ~ betting sports actually about | indice de vélocité 0.30 sur 2 vidéo(s) récente(s) contre 0.06 sur 8 ancienne(s) (×5.1) — indice = vélocité / médiane du décile d'âge, sans quoi la mesure ne mesure que l'âge |
| `c0386` | ~ cup world game guide | indice de vélocité 0.01 sur 14 vidéo(s) récente(s) contre 0.00 sur 40 ancienne(s) (×2.6) — indice = vélocité / médiane du décile d'âge, sans quoi la mesure ne mesure que l'âge |

## Limites

- **74 chaînes ne sont pas le marché.** Un « trou » est une absence dans l'échantillon suivi. Une chaîne non suivie peut avoir traité le sujet hier.
- **Un seul jour de collecte en base** au moment de cette exécution : `views_d7` et `views_d30` sont NULL et la vélocité vaut `velocity_life` (vues / âge). Le ratio de percée compare donc des **vues cumulées** à âge comparable, pas des vitesses. Le second jour de collecte lève cette limite sans changer une ligne de code (`topics.percees.preferer_dN`).
- **Le nombre de clusters est un paramètre, pas un fait.** Seuil de distance 0.12 ; le rapport de veille conseille de balayer 0,30 à 0,45.
- **La demande est un proxy** : vues Wikipédia du seed le plus proche, médiane sur 24 mois. Google Trends reste indisponible (étape 19).

