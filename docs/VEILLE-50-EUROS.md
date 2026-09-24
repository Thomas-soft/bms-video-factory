# Veille — ce que 50 €/mois achètent réellement (17/09/2026)

> Veille exploratoire demandée par Thomas le 17/09/2026, hors feuille de route.
> Cinq sous-agents, sources officielles uniquement, taux 1 USD = 0,87 €.
> **Ce document ne décide rien** : le jalon `ROADMAP.md` § 8 (critères C1 à C7) reste
> la condition d'engagement du budget. Il corrige en revanche l'hypothèse de départ.

## 1. La question posée et la réponse courte

Question : à 50 €/mois, faut-il un serveur GPU, ou un service type HeyGen / Higgsfield ?

**Réponse : ni l'un ni l'autre.** Le serveur dédié n'existe pas à ce prix, le SaaS vidéo
est dix à vingt fois trop cher pour nos durées, et **l'appel d'API à l'image rend le
serveur inutile** : le poste qui coûte 84 % du temps de production tombe à 3-33 €/mois.

## 2. Charge de référence (mesurée dans ce dépôt)

Une vidéo FR = 737 s (12,3 min), 127 plans, 83 images générées, ~12 min de voix.
Coût machine mesuré : **2 h 47 par vidéo**, dont 84 % en génération d'images
(98,8 s par image sur le M2). Capacité mesurée : ≈ 7 vidéos/semaine, une par nuit.

| | S1 — 8 vidéos/sem. | S2 — 20 vidéos/sem. |
|---|---|---|
| Vidéos/mois | ~35 | ~87 |
| Minutes de vidéo/mois | ~430 | ~1 070 |
| Images/mois | ~2 900 | ~7 200 |
| Heures de voix/mois | ~7,2 h | ~18 h |
| Chaînes requises (plafond 2/sem., `CONFORMITE.md` § 6) | 4 | 10 |

## 3. Serveur GPU — le dédié n'existe pas à ce prix

Aucun serveur dédié GPU ≥ 16 Go sous 70 €/mois au 17/09/2026. Moins cher trouvé :
Hostkey « à partir de 118 €/mois » (config non confirmée) ; Hetzner GEX44 ~184-234 €
+ 79 € d'installation ; OVH Scale-GPU-1 « from 1 145 $/mois ». 50 € achètent donc des
**heures à la demande** : ~170 h de RTX 4090 chez RunPod Community (0,34 $/h), ~78 h en
Secure (0,74 $/h), ~63 h de L4 chez Scaleway (0,79 €/h, seule offre en € et UE vérifiée).

Besoin réel estimé (débits 4090 relevés, **non mesurés sur notre pipeline**) :
S1 ~3 à 8 h/mois, S2 ~7 à 20 h/mois. Le budget couvre largement — mais voir § 5 :
l'API rend la question sans objet.

## 4. SaaS vidéo et avatar — hors d'échelle, et hors sujet pour Higgsfield

| Offre | Palier ~50 € | min/mois | Durée max/vidéo | Coût réel S1 | Coût réel S2 |
|---|---|---|---|---|---|
| HeyGen Pro | 49 $/mois | ~50 min | 30 min | ~504 $/mois | ~1 144 $/mois |
| Open-Higgsfield-AI (→ Muapi) | pay-as-you-go | 0,34 $/s en Seedance 720p | 5/10/15 s par clip | ~8 780 $/mois | ~21 800 $/mois |
| Synthesia Creator | 64 $/mois annuel | 30 min | quota réel 30 min | devis Enterprise | devis |
| Elai.io Team | 100 $/mois | 50 min | non vérifié | ~860 $/mois | ~2 140 $/mois |
| D-ID | — | — | **5 min** (officiel) | éliminatoire | éliminatoire |

50 € d'avatar parlant = **30 à 50 minutes par mois**, soit 3 à 4 vidéos sur les 35 à 87
nécessaires. Prix plancher réel du style : ~460 €/mois en S1, > 1 000 €/mois en S2.

**Higgsfield : ce n'est pas une question de prix, c'est la nature du produit.**
Officiel : Kling 3.0 « up to 15 seconds per generation », Seedance 2.5 plafonne à 30 s ;
facturation 0,112 $/seconde de sortie, pay-as-you-go, droits commerciaux explicitement
accordés (seul du lot à l'écrire). Aucun mode vidéo longue ni avatar long format.
Reconstituer 12,3 min par collage coûterait **83 $ la vidéo**, ~2 890 $/mois en S1, sans
aucune continuité de personnage ou de décor sur 50 clips successifs.
→ La phrase déjà écrite à Alek (« jamais au niveau de Higgsfield ») est à reformuler :
Higgsfield fait des plans de 15 s, pas des vidéos de 15 min. Il n'y a pas de comparaison.
Paliers d'abonnement web (Basic/Pro/Max) : **non vérifiés**, page en JS inaccessible.

### 4.1 « Open-Higgsfield-AI » — ce n'est pas un Higgsfield libre

`github.com/Autom8AI/Open-Higgsfield-AI`, signalé par Thomas le 17/09/2026. Vérifié le
jour même sur le dépôt et l'API GitHub. **Ce n'est ni un modèle, ni une réimplémentation :
c'est une interface Next.js/Electron qui appelle l'API payante Muapi.ai.** Le README
l'écrit : *« communicates with Muapi.ai using a two-step pattern »*, et *« A Muapi.ai API
key »* est un prérequis. Aucun poids n'est téléchargé, aucune exigence GPU ou VRAM n'est
annoncée — le calcul se fait chez Muapi. Le mot « Open » porte sur le client, pas sur les
modèles ni sur le coût.

Conséquences pour nous :
- **Il n'apporte rien au pipeline.** C'est un client graphique de bureau, à clics ; nous
  avons besoin d'appels programmatiques. Muapi expose sa propre API (et un CLI officiel) :
  ce wrapper serait une couche inutile entre l'usine et le fournisseur.
- **Il ne change pas le prix, il l'augmente.** Tarifs Muapi publiés : **0,03 $ par image**
  (Imagen 4, Qwen Image, Nano-Banana), soit **75,69 €/mois en S1 et 187,92 €/mois en S2** —
  59 fois le prix de FLUX.1-schnell chez DeepInfra. En vidéo, **Seedance 2.5 720p à
  0,34 $/s** : une vidéo de 738 s coûterait **250,92 $**, soit ~8 780 $/mois en S1. C'est
  **trois fois plus cher que Higgsfield lui-même** (0,112 $/s sur Kling 3.0).
- **Deux réserves de licence et de maintenance.** Le README annonce « MIT licensed », mais
  **le dépôt ne contient aucun fichier LICENSE** et la détection de licence de GitHub rend
  `None` : l'affirmation n'est pas étayée par le texte de licence. Et le dépôt a été
  **créé et poussé le 09/04/2026, sans un seul commit depuis** (66 commits, 274 étoiles,
  53 forks, 0 issue ouverte) — 5 mois d'immobilité. Muapi ne publie par ailleurs **aucune
  clause sur les droits commerciaux des sorties**, ce qui est éliminatoire ici tant que ce
  n'est pas lu dans les CGU.
- `flux-dev` y est proposé à 0,025 $/image : c'est le modèle **non commercial** de BFL
  (voir § 5), à ne pas utiliser quel que soit le prix.

→ **À écarter.** Si Muapi devait un jour servir, ce serait par son API directe, et le
comparatif du § 5 montre qu'elle n'est pas compétitive sur notre poste dominant.

## 5. Images par API — le renversement

| Fournisseur · modèle | €/image | S1 (2 900) | S2 (7 200) | Licence |
|---|---|---|---|---|
| DeepInfra · FLUX.1-schnell | 0,00044 € | **1,28 €** | **3,17 €** | Apache-2.0 vérifiée |
| Runware · FLUX.1-schnell | 0,00113 € | 3,28 € | 8,14 € | Apache-2.0 (page muette) |
| Replicate · FLUX-schnell | 0,00261 € | 7,57 € | 18,79 € | Apache-2.0 citée |
| **fal.ai · Z-Image-Turbo** | 0,00456 € | 13,22 € | **32,83 €** | « Commercial use » affiché |
| fal.ai · Qwen-Image | 0,0182 € | 52,90 € | 131,42 € | « Commercial use » affiché |
| Google Nano Banana 2 Lite | 0,0292 € | 84,76 € | 210,24 € | page muette |
| **Muapi.ai** (moteur d'« Open-Higgsfield-AI ») | 0,0261 € | 75,69 € | 187,92 € | **page muette** |
| OpenAI gpt-image-1 | 0,0365 € | 105,94 € | 262,94 € | page muette |

**Z-Image-Turbo mérite un essai** : Elo 942 contre 864 pour FLUX.2-klein (veille du
17/09 au matin), donc vitesse **et** qualité pour ~33 €/mois en S2.

**Deux pièges de licence :**
1. **FLUX.1-dev** est souvent proposé « pas cher » chez les agrégateurs et reste **non
   commercial** chez BFL. À écarter. FLUX.1-schnell (Apache-2.0) est sûr.
2. **Contradiction à trancher** : `ROADMAP.md` § 3.5 classe **FLUX.2-klein 9B parmi les
   non commerciaux, éliminés**, or fal.ai affiche « Commercial use » et DeepInfra le tague
   Apache-2.0. Un badge d'hébergeur ne réécrit pas la licence d'un modèle. À vérifier sur
   la licence publiée par BFL **avant** tout usage.

Clips de 5 s générés (appoint b-roll, jamais un style entier — `ROADMAP.md` § 9 risque 1) :
LTX-2 fast 0,131 € (720p), Runway Gen-4 Turbo 0,218 €, Wan 2.5 chez fal.ai 0,435 €
(seul avec usage commercial affiché). 20 clips par vidéo = 2,60 €, soit ~90 €/mois en S1.

## 6. Voix par API

| Offre | €/h audio | S1 (7,2 h) | S2 (18 h) | Monétisation |
|---|---|---|---|---|
| **OpenAI tts-1** | 0,70 € | **5,04 €** | **12,60 €** | sorties détenues par le client, confirmé |
| Azure Neural HD | 1,03 € | 7,42 € | 18,54 € | conditions Azure ; gratuit 500k car./mois confirmé |
| Fish Audio s2.1-pro | 1,09 € | 7,85 € | 19,62 € | gratuit = **non commercial** (ToS) |
| Google Chirp3-HD | 1,41 € | 10,15 € | 25,40 € | conditions GCP |
| ElevenLabs Flash | 2,35 € | 16,92 € | 42,30 € | gratuit = non commercial ; payant = OK |
| Speechify | 0,47 € | 3,38 € | 8,46 € | **droits non publiés** |

PlayHT / PlayAI : **service fermé** (DNS injoignable, fermeture au 31/12/2025 non
confirmée par annonce officielle lue).

À vérifier en priorité : si les paliers gratuits Azure (500k car./mois, confirmé) et
Google (~1M car./mois, non confirmé) couvrent les voix HD, **S1 serait gratuit en voix**
(7,2 h ≈ 389k-432k caractères).

Comparaison avec le local : Qwen3-TTS consomme ~33 min de calcul pour 10 min de voix,
soit ~59 h de machine monopolisée pour produire 18 h/mois. L'API coûte 12 à 20 €/mois et
rend la machine. Le local reste le repli hors ligne.

## 7. Musique — le poste qui débloque la publication

`workspace/library/music/` est vide, Freesound est écarté, la bibliothèque YouTube n'a
pas d'API : c'est aujourd'hui le seul blocage dur de la publication (`CONFORMITE.md` § 10.1).

| Offre | €/mois | Chaînes | Content ID | API | Perpétuel ? |
|---|---|---|---|---|---|
| **Epidemic Sound Pro** | ~17-20 € | 3 | safelisting officiel | **oui, API officielle** | oui, « cleared forever » |
| Uppbeat Pro | non vérifié (7-18 $) | ~10 (source secondaire) | safelist | aucune trouvée | oui |
| Storyblocks Audio | 11-30 $ | non vérifié | annoncé sans match | entreprise seulement | **non — expire à la résiliation** |
| YouTube Audio Library | 0 € | illimité | garanti par Google | **aucune, manuel** | oui |

Epidemic Sound Pro est la seule offre réunissant les trois preuves (multi-chaînes, sans
Content ID, API officielle) — mais **3 chaînes**, quand S2 en demande 10.
**Piège Storyblocks** : au palier individuel la licence expire à la résiliation, ce qui
rend illicite tout le catalogue déjà publié. Incompatible avec un actif revendable.

Banques vidéo pour le style documentaire (étape 17) : **Pexels API** — gratuit,
200 req/h et 20 000/mois, automatisation explicitement prévue, sans attribution obligatoire.
Pixabay **interdit** les téléchargements en masse ; Envato Elements ne renvoie aucun lien
de téléchargement par API ; Mixkit interdit l'agrégation. Coverr : gratuit, API conçue
pour l'automatisation, attribution requise.

## 8. Budget assemblé

| Poste | S1 (8/sem.) | S2 (20/sem.) |
|---|---|---|
| Images — FLUX.1-schnell chez DeepInfra | 1,28 € | 3,17 € |
| Images — Z-Image-Turbo chez fal.ai (option qualité) | 13,22 € | 32,83 € |
| Voix — OpenAI tts-1 | 5,04 € | 12,60 € |
| Musique — Epidemic Sound Pro | ~18 € | ~18 € |
| Banque vidéo — Pexels | 0 € | 0 € |
| Serveur GPU | **0 €** | **0 €** |
| **Total, images économiques** | **~24 €** | **~34 €** |
| **Total, option qualité** | **~36 €** | **~63 € (dépasse)** |

Lecture : **50 €/mois couvrent les 20 vidéos par semaine** avec le modèle d'image
économique, ou les 8 vidéos par semaine avec le meilleur modèle d'image. Le serveur
n'entre pas dans l'équation.

## 9. Ce que cela ne résout pas

1. **La conformité, pas le calcul, est le plafond de volume.** 20 vidéos/semaine imposent
   10 chaînes (`CONFORMITE.md` § 6 : 2/chaîne/semaine pendant 90 jours), donc 10 comptes
   Google et 10 audits API — et exactement le profil « IA + volume » visé par les
   terminaisons de janvier 2026. Aucun budget n'achète cela.
2. **Le jalon § 8 n'est pas atteint** (C1 : 13 étapes sur 31 ; C4 et C6 : aucune vidéo
   publiée, audit non déposé). L'engagement reste conditionné — mais à 1,28 € les
   2 900 images, **un test réel coûte quelques euros et n'a pas à attendre le jalon**.
3. **La dépendance fournisseur remplace la dépendance serveur.** La règle du § 8 (« le
   système continue en mode dégradé si le serveur disparaît ») doit s'appliquer aux API :
   le chemin local reste le repli, et chaque fournisseur voit ses conditions de sortie
   consignées par asset comme l'exige `CONFORMITE.md`.
4. **Les licences des sorties sont majoritairement muettes.** Recraft, Luma, Runway, LTX,
   BFL direct, Google, OpenAI images, Novita, Segmind, Runware : pages de tarifs
   silencieuses sur les droits. À lire dans les CGU avant tout engagement.

## 10. Non vérifié

Higgsfield (paliers web) ; Hedra, Argil, Creatify, Captions, Akool (non recherchés) ;
Vidnoz (page contradictoire) ; TensorDock, DataCrunch, Lambda, Novita GPU, Paperspace,
OVH horaire ; Modal, Replicate, Baseten, Beam en serverless ; Hetzner GEX44 sur sa propre
page ; Vast.ai non revérifié ; prix Uppbeat et son API ; API et perpétuité Artlist (403),
Soundstripe, PremiumBeat, Motion Array ; Kling, Hailuo, Seedance, Veo, Freepik, Leonardo ;
droits commerciaux Rime, MiniMax, Speechify, Deepgram ; gratuits Google/Azure sur voix HD.
