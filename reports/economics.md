# Économie unitaire — 2026-09-24

Généré par `factory economics`. Nature de chaque chiffre : **mesuré** (chronométré ou compté par l'usine), **importé** (export de programme, Analytics API), **estimé** (hypothèse de `config/economics.yaml` non mesurée).

## 1. Hypothèses (config/economics.yaml)

| paramètre | valeur | nature | origine |
|---|---|---|---|
| `puissance_moyenne_w` | 30 | estimé | 30 W = ordre de grandeur d'un M2 Air en charge soutenue, NON mesuré ; à mesurer au wattmètre pendant un run complet |
| `tarif_kwh_eur` | 0,2516 | décidé/sourcé | tarif réglementé FR |
| `cout_horaire_relecture_eur` | 15 | estimé | 15 €/h = hypothèse de travail de l'étape 27, pas une décision ; taux à fixer par Alek |
| `relecture_forfait_min` | 15 | estimé | 15 min pour lire un script de ~10 min et regarder la vidéo en accéléré ; NON mesuré (aucun horodatage d'affichage) |
| `couts_fixes_mensuels_eur` | 0 | décidé/sourcé | aucun abonnement ni serveur au 24/09/2026 ; serveur GPU ~50 €/mois approuvé pour plus tard (ROADMAP § 3.1) |
| `amortissement_materiel_mensuel_eur` | 0 | décidé/sourcé | Mac existant, non affecté au projet : amortissement non imputé (décision de l'étape 27, à revoir si la machine devient dédiée) |
| `serveur_gpu_mensuel_eur` | 50 | décidé/sourcé | budget approuvé par Alek, ROADMAP § 3.1 (« 50€/mois approved ») |
| `taux_eur.EUR` | 1 | décidé/sourcé | identité |
| `taux_eur.USD` | 0,86 | estimé | ordre de grandeur, non relevé ; à relever (BCE) au premier revenu réel |
| `taux_eur.GBP` | 1,16 | estimé | ordre de grandeur, non relevé ; à relever (BCE) au premier revenu réel |
| `horizon_retour_jours` | 30 | décidé/sourcé | config/economics.yaml |

Formule : coût = compute_min (mesuré) ÷ 60 × puissance ÷ 1000 × tarif kWh + forfait de relecture ÷ 60 × taux horaire + (coûts fixes + amortissement) du mois ÷ vidéos livrées ce mois-là.

**Limite de la mesure de calcul** : `compute_min` somme la **dernière** exécution de chaque étape inscrite au manifeste. Un run repris (images déjà générées, étape rejouée) est sous-compté ; la colonne « étapes » le signale. Le seul run neuf complet chronométré de bout en bout est `s2ur` (≈ 4 h 12, STATE étape 22.1).

## 2. Coût par vidéo livrée

| vidéo | style | durée (min) | calcul (min, mesuré) | étapes | énergie (estimé) | relecture (estimé) | fixes | coût total | revenu (importé) | marge |
|---|---|---|---|---|---|---|---|---|---|---|
| `bms-science-fr-20260915-j7sf` | illustre | 12,3 | 32,2 | 11/11 | 0,004 € | 3,75 € | 0,000 € | **3,75 €** | 0,000 € | -3,75 € |
| `bms-science-fr-20260917-rtmk` | illustre | 12,0 | 142,8 | 11/11 | 0,018 € | 3,75 € | 0,000 € | **3,77 €** | 0,000 € | -3,77 € |
| `bms-science-en-20260917-avwf` | illustre | 10,6 | 56,0 | 11/11 | 0,007 € | 3,75 € | 0,000 € | **3,76 €** | 0,000 € | -3,76 € |
| `bms-science-en-20260919-mtn7` | motion | 10,6 | 50,5 | 11/11 | 0,006 € | 3,75 € | 0,000 € | **3,76 €** | 0,000 € | -3,76 € |
| `bms-science-en-20260920-s57f` | illustre | 9,2 | 61,2 | 11/11 | 0,008 € | 3,75 € | 0,000 € | **3,76 €** | 0,000 € | -3,76 € |
| `bms-science-en-20260920-s2ur` | illustre | 10,5 | 252,0 | 11/11 | 0,032 € | 3,75 € | 0,000 € | **3,78 €** | 0,000 € | -3,78 € |
| `bms-science-en-20260923-c7km` | illustre | 11,6 | 74,6 | 9/11 | 0,009 € | 3,75 € | 0,000 € | **3,76 €** | 0,000 € | -3,76 € |

Runs non livrés (échec, bloqués avant export, en cours) : 12 avec du calcul chronométré, **120,4 min** au total (mesuré). Réparti sur les 7 vidéos livrées, cela ajoute 17,2 min de calcul par vidéo.

## 3. Coût par minute de vidéo, par style

| style | n | calcul min / min vidéo (mesuré) | coût moyen / vidéo | coût / min vidéo | dont énergie / min |
|---|---|---|---|---|---|
| illustre | 6 | 9,35 | 3,76 € | 0,341 € | 0,001 € |
| motion | 1 | 4,77 | 3,76 € | 0,355 € | 0,001 € |

## 4. Agrégats

### Par niche

| niche | n | coût moyen | calcul min/min vidéo | coût / min vidéo | revenu moyen | marge moyenne | délai de retour |
|---|---|---|---|---|---|---|---|
| science_pop | 7 | 3,76 € | 8,72 | 0,343 € | 0,000 € | -3,76 € | n/a (0 publiée) |

### Par langue

| langue | n | coût moyen | calcul min/min vidéo | coût / min vidéo | revenu moyen | marge moyenne | délai de retour |
|---|---|---|---|---|---|---|---|
| en | 5 | 3,76 € | 9,42 | 0,359 € | 0,000 € | -3,76 € | n/a (0 publiée) |
| fr | 2 | 3,76 € | 7,20 | 0,310 € | 0,000 € | -3,76 € | n/a (0 publiée) |

### Par chaîne

| chaîne | n | coût moyen | calcul min/min vidéo | coût / min vidéo | revenu moyen | marge moyenne | délai de retour |
|---|---|---|---|---|---|---|---|
| bms-science-en | 5 | 3,76 € | 9,42 | 0,359 € | 0,000 € | -3,76 € | n/a (0 publiée) |
| bms-science-fr | 2 | 3,76 € | 7,20 | 0,310 € | 0,000 € | -3,76 € | n/a (0 publiée) |

### Par style

| style | n | coût moyen | calcul min/min vidéo | coût / min vidéo | revenu moyen | marge moyenne | délai de retour |
|---|---|---|---|---|---|---|---|
| illustre | 6 | 3,76 € | 9,35 | 0,341 € | 0,000 € | -3,76 € | n/a (0 publiée) |
| motion | 1 | 3,76 € | 4,77 | 0,355 € | 0,000 € | -3,76 € | n/a (0 publiée) |

## 5. Revenus

- Lignes de revenu importées (hors fixtures) : **0**. Revenu réel constaté : **0,000 €** — aucune vidéo n'est publiée (table `publications` vide), aucun programme d'affiliation n'est ouvert : **0 € est un fait, pas une mesure de performance**.
- Lignes de fixture présentes dans `revenue` et **exclues** du calcul : 7.
- Revenu importé non rattaché à une vidéo livrée : 0,000 €.

## 6. Série temporelle : vidéo n° 1 contre la dernière

| # | vidéo | créée | style | calcul (min) | calcul min/min | assets de bibliothèque utilisés | coût |
|---|---|---|---|---|---|---|---|
| 1 | `bms-science-fr-20260915-j7sf` | 2026-09-15 | illustre | 32,2 | 2,62 | 83 | 3,75 € |
| 2 | `bms-science-fr-20260917-rtmk` | 2026-09-17 | illustre | 142,8 | 11,91 | 36 | 3,77 € |
| 3 | `bms-science-en-20260917-avwf` | 2026-09-17 | illustre | 56,0 | 5,30 | 169 | 3,76 € |
| 4 | `bms-science-en-20260919-mtn7` | 2026-09-19 | motion | 50,5 | 4,77 | 0 | 3,76 € |
| 5 | `bms-science-en-20260920-s57f` | 2026-09-20 | illustre | 61,2 | 6,68 | 92 | 3,76 € |
| 6 | `bms-science-en-20260920-s2ur` | 2026-09-20 | illustre | 252,0 | 23,92 | 111 | 3,78 € |
| 7 | `bms-science-en-20260923-c7km` | 2026-09-23 | illustre | 74,6 | 6,44 | 36 | 3,76 € |

Première (bms-science-fr-20260915-j7sf) : 2,62 min de calcul par minute ; dernière (bms-science-en-20260923-c7km) : 6,44. **L'effet de la bibliothèque n'est pas isolable** sur ces données : les runs sont repris (étapes non rechronométrées) et changent de style ; seul un run neuf complet par mois, même chaîne et même style, le mesurera.

## 7. Trois décisions chiffrées

1. **Niches** : science_pop en EN coûte 3,76 € par vidéo et rapporte 0,000 € (n = 5 livrée(s), 0 publiée(s)) ; science_pop en FR coûte 3,76 € par vidéo et rapporte 0,000 € (n = 2 livrée(s), 0 publiée(s)). Revenu à 30 jours non observable : **non décidable**. Continuer ou arrêter une niche se tranchera sur le revenu à 30 j d'au moins 5 vidéos publiées par niche, pas sur le coût, qui varie peu.
2. **Le coût est humain, pas machine** : sur 7 vidéos, l'énergie pèse 0,084 € (0,3 %) et la relecture 26,25 € (99,7 %). Réduire le temps de calcul ne change pas l'économie ; la décision utile est de **mesurer puis réduire la relecture** (forfait de 15 min estimé). Un doublement de la puissance réelle (wattmètre) ne déplacerait le coût que de 0,012 € par vidéo.
3. **Style et serveur** : illustre 9,35 min de calcul par minute de vidéo (n=6), motion 4,77 min de calcul par minute de vidéo (n=1). Un serveur à 50 €/mois (`serveur_gpu_mensuel_eur`) ajouterait 7,14 € par vidéo au volume mesuré (7 vidéos livrées sur 30 jours) contre 0,012 € d'énergie aujourd'hui : **non justifié par le coût** ; il ne se justifiera que par la capacité (vidéos/nuit), avec un revenu par vidéo supérieur à 7,14 € — revenu constaté : 0,000 €.

## 8. Données manquantes pour décider

- **Revenu** : 0 vidéo publiée, 0 programme d'affiliation ouvert, chaîne hors YPP → aucun revenu observable. Premier chiffre utile : revenu à 30 jours de 5 vidéos publiées avec produit.
- **Puissance** : `puissance_moyenne_w` non mesurée (wattmètre pendant un run complet).
- **Relecture** : aucune heure d'affichage n'est journalisée ; le forfait et le taux horaire sont des hypothèses (taux à fixer par Alek).
- **Calcul** : un run neuf complet par style (seul `s2ur` l'est) ; les manifestes des runs repris sous-comptent.
- **Produits** : aucun produit réel dans `config/products/` (Alek).
