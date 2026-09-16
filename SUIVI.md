# SUIVI — tableau de bord humain

Ce fichier est pour **Thomas**. Les sessions ne le lisent pas pour travailler : elles
l'alimentent en fin d'étape (règle 14 de `CLAUDE.md`). `STATE.md` est la mémoire des
sessions ; `SUIVI.md` est ton tableau de bord.

Dernière mise à jour : **15/09/2026**.

---

## 1. Ce que tu dois faire, toi

### Présence requise — tu dois être au clavier pendant la session

| Quand | Action | Durée | Statut |
|---|---|---|---|
| ~~Étape 2, au démarrage~~ | ~~Créer le projet Google Cloud « bms-factory »…~~ | ~10 min | ✅ fait 14/09/2026 — projet `bms-factory`, clé restreinte à *YouTube Data API v3*, dans `.env` |
| ~~Avant l'étape 3~~ | ~~Relancer la passe de transcriptions~~ | — | ✅ fait 14/09/2026 — 349 transcriptions, 74 chaînes, 11 niches |
| ~~Avant l'étape 5.2~~ | ~~Écouter les 8 échantillons de voix~~ | — | ✅ fait 15/09/2026 — « les voix sont plutôt bonnes », **sans note chiffrée**. La voix FR n'est pas disqualifiante : pas d'arbitrage à remonter à Alek. Qwen3-TTS conservé **par assouplissement assumé du seuil de vitesse** |
| ~~Avant l'étape 5.2~~ | ~~Trancher le disque~~ | — | ✅ fait 15/09/2026 — **rien à purger**, la route MLX 4-bit supprime le pic transitoire. `faster-whisper-large-v3` conservé |
| ⏰ **En retard — l'étape 7 est close sans cette décision** (attendue avant l'étape 7) | **Lire `docs/STYLES.md` § 9 et décider de l'envoi du message à Alek.** Version **WhatsApp**, 19 lignes, prête à coller — texte brut dans `docs/message-alek-whatsapp.txt`. **Vérifié chiffre par chiffre contre les sources le 15/09/2026** (sous-agent) : 11 chiffres tiennent, 6 formulations corrigées, 3 manques comblés — détail au § 9.2 de `STYLES.md`. Le texte est prêt à envoyer tel quel ; il annonce l'abandon des « animations poussées », le refus du photoréalisme généré, la correction de la dérive de personnage par le prompt (avec relecture humaine des plans à personnage en garde-fou), un plafond de ~7 vidéos/semaine **sur ton MacBook Air M2 16 Go nommément**, le fait que **la machine du serveur n'est pas encore choisie** — seulement son budget — et **le prochain objectif : la vidéo de démonstration complète de l'étape 13.2**. Il se termine par **deux demandes à Alek** (raison sociale/SIREN/adresse, et comptes Google), qui sont les questions n° 2 et n° 1 ci-dessous : si tu préfères les poser à part, coupe la dernière phrase. Rien n'y est promis qui ne soit pas dans la matrice du § 1. | ~10 min de lecture | ⬜ **à toi** |
| ⏰ **En retard — l'étape 11 est close sans cette décision** (attendue avant l'étape 11) | **Trancher Qwen3-TTS, après mesure de Kokoro EN.** **Alek a tranché l'anglais le 15/09/2026** : la prémisse qui gardait Qwen3-TTS — *« faute de repli à deux voix »* — **n'était vraie qu'en français**. En anglais, `SELECTION.md` § 2 désigne un repli : **Kokoro-82M, 0,33 Go contre 4,52**, rapide, catalogue fourni. **La session mesurera d'abord** (après l'étape 8) : vitesse, WER par palier 2/7/11/22 s, timbres réellement distincts. **Ton arbitrage vient ensuite** : Qwen3-TTS échoue déjà le seuil de vitesse (RTF 3,29, ~33 min par vidéo de 10 min) et sa purge rend **4,52 Go** là où il reste **0,48 Go de marge**. **À écouter d'ici là** : `workspace/logs/ladder_*.wav` (2 s, 7 s, 11 s, 22 s). | ~20 min | ⬜ **à toi** — extraits de 30 s prêts : `workspace/logs/ecoute11/voix_fr.wav` et `voix_en.wav` **L'étape 11 a tourné avec Qwen3-TTS et l'a mesuré en production : facteur temps réel 3,33 (FR) et 3,21 (EN), soit 2 451 s et 2 135 s de calcul par vidéo — le seuil de `SELECTION.md` § 2 (≤ 1,0) reste échoué d'un facteur 3,3. Les deux `voice.wav` sont aux normes YouTube, mais personne ne les a écoutés.** |
| **Avant l'étape 13 (montage et export)** | **Trancher le remplacement de ffmpeg : cette build n'a ni `libass` ni `libfreetype`.** Mesuré le 16/09/2026 : `drawtext`, `subtitles` et `ass` sont absents des filtres, et la formule `ffmpeg` de homebrew-core (8.1.2 installée, 9.0.1 disponible) ne dépend d'aucune des deux bibliothèques. Le moteur « cartes » s'en passe en gravant son texte avec Pillow, **mais `final.mp4` doit incruster `subtitles.ass` : sans libass, l'étape 13 ne peut pas tenir son contrat.** Deux routes : recompiler ffmpeg depuis les sources avec `--enable-libass --enable-libfreetype --enable-libfontconfig` (long, et il faudra le refaire à chaque mise à jour), ou installer un **build statique** à côté (~80 Mo, à gager sur le plancher de 8 Go et à inscrire au ledger). **Aucune mesure ne tranche à ta place : c'est un choix de disque et de maintenance.** | ~15 min | ⬜ **à toi** |
| **Avant d'adopter Kokoro (donc avant l'étape 11)** | **Trancher la licence : la revente de l'actif porte-t-elle sur le code du pipeline, ou seulement sur les chaînes ?** Kokoro tire `misaki` → `phonemizer-fork` → espeak-ng, **tous GPL-3.0 et chargés dans notre processus** (pas en binaire externe comme ffmpeg). `SELECTION.md` § 2 l'autorise *« tant que le pipeline n'est pas redistribué »*, au motif que *« BMS n'a jamais prévu de distribuer le pipeline »* — **mais `ROADMAP.md` écrit trois fois que le projet est un actif revendable**, et vendre un logiciel, c'est le distribuer. **Si la revente porte sur les chaînes, les comptes et la documentation, la GPL ne se déclenche jamais et Kokoro passe.** Si elle porte sur le code : soit espeak-ng en **binaire externe** (le motif déjà appliqué à ffmpeg), soit les **poids Kokoro seuls** (Apache-2.0) avec un G2P non GPL. **Question pour Alek ; aucune mesure ne la remplace.** | ~10 min | ⬜ à faire |

**[Dépôt GitHub — ajouté le 16/09/2026] Deux dépôts en ligne, et une chose à savoir.**

| Dépôt | Visibilité | Contenu |
|---|---|---|
| `github.com/Thomas-soft/bms-video-factory` | **PUBLIC** — le lien à envoyer à Alek | tout, **sauf `registre/data/`** |
| `github.com/Thomas-soft/bms-video-factory-interne` | privé | tout, historique de travail complet (51 commits) |

**Pourquoi deux dépôts, et pas un seul public.** `registre/data/` contient **89 Mo de
réponses brutes de l'API YouTube Data v3** sur **76 chaînes tierces** (`kind: youtube#video`,
`etag`, snippets et statistiques). `docs/CONFORMITE.md` § « durée de conservation » cite les
Developer Policies **III.E.4** : stockage **30 jours au maximum**, puis suppression ou
rafraîchissement — « clause contractuelle opposable lors d'un audit ». **Un dépôt public ne
peut pas tenir cette clause** : il est clonable, forkable, archivé. Et `audit_passed: false` —
l'audit API est précisément l'étape 14. Les **mesures dérivées** (`REFERENTIEL.json`, agrégats,
comptages) sont publiées : la même page de `CONFORMITE.md` dit qu'elles ne sont plus des
données API. **Rien d'autre n'a été retiré.**

Le dépôt public n'a **qu'un commit** : l'historique de travail porte le cache API dans chacun
de ses 51 commits, donc il n'était pas réutilisable tel quel. `outils/publier.sh` reconstruit
et republie l'instantané à la demande.

**Ce que tu peux vouloir retirer du public, et que je n'ai pas retiré parce que tu ne l'as pas
demandé** : `docs/message-alek-whatsapp.txt` et `docs/STYLES.md` § 9 (**le message qu'on n'a
pas encore envoyé**, avec le compte rendu de sa relecture au § 9.2) · `SUIVI.md` (ce fichier :
retards, questions à Alek, analyse licence/revente) · `config/economics.yaml` et
`config/team.yaml` · `registre/REGISTRE-CHAINES.pdf`. **En privé partagé c'était Alek qui
lisait ; en public, c'est n'importe qui, et Google indexe.** Dis-moi si j'en retire : c'est
une ligne dans `outils/publier.sh` et une republication.

**[Preuve motion design — ajouté le 16/09/2026] Deux choses à toi, et une seule est un arbitrage.**

**(a) Regarde les trois séquences et note-les. ⚠️ A et C sont des DEUXIÈMES VERSIONS.**
Ton verdict du 16/09 sur les premières — « B ça commence à être intéressant, par contre A et C
c'est très nul, non professionnel et ennuyant visuellement » — portait sur l'exécution, pas sur
les styles, et les causes étaient nommables (§ 0 de `RESULTATS.md`). **A et C ont été
entièrement réécrits ; B n'a pas été retouché.** `benchmarks/preuve_motion/motion_A.mp4`
(typographie cinétique), `motion_B.mp4` (schéma animé), `motion_C.mp4` (hybride sur fonds de
bibliothèque) — même texte, même voix, 32,0 s chacune, 1920×1080 à 30 ips, voix montée.
Tout ce qui se mesure est mesuré et versé à `benchmarks/preuve_motion/RESULTATS.md` (débit
91,4 à 134,3 img/s, pic mémoire 0,88-1,10 Go, **zéro image générée** dans les trois).
**Ce qui n'est pas mesuré : la fluidité en lecture et la synchronisation à l'oreille.** La
session ne les perçoit pas et ne les note pas — le seuil « vue et notée ≥ 3/5 » de
`docs/STYLES.md` § 7 reste ouvert tant que tu n'as pas regardé. C'est B qui compte : c'est
lui qui répond à « ce sont des images fixes avec un effet de glissement ».

**(b) Deux documents se contredisent depuis le 15/09, et je ne les départage pas.**
`docs/STYLES.md` § 6 déplace le motion design de la **phase 6 à la phase 2** (étape 30.1),
avec ses motifs écrits ; le **tableau § 5 de `ROADMAP.md`, ligne 30.1, n'a jamais été amendé**
et l'annonce toujours en **phase 6, après l'étape 29**. **Amendement proposé** — à porter à
`ROADMAP.md` § 5 : faire passer la ligne 30.1 en phase 2, juste après l'étape 17
(documentaire), et déplacer l'étape 29 (avatar 2D) en phase 6, conformément au classement
du § 6 de `STYLES.md` ; ajouter en note que l'ordre vient de la preuve disponible.
**Je ne le fais pas moi-même : il dépend de ce que tu verras dans les trois séquences.**
Si B te convainc, l'amendement se justifie ; s'il te déçoit, c'est `STYLES.md` § 6 qui est à
corriger, et le § 9 (message à Alek) avec lui, puisqu'il nomme le motion design en style n° 2.

**Ce que la preuve ne dit pas, et qui pèse sur ta décision** : B a demandé **43 repères
temporels écrits à la main**, dont 23 calés sur un mot, et une géométrie propre au saccharose
et à l'insuline. A et C se rejouent sur n'importe quel script ; **B non**. La question de
l'étape 30.1 n'est donc pas « sait-on faire un schéma animé » — c'est fait — mais **« d'où
vient le schéma quand personne ne le dessine »**.

**[Étape 12.2 — ajouté le 16/09/2026] Regarde les clips avant l'étape 13.2.**
Les 127 clips du run FR sont rendus et au contrat, mais **je ne perçois pas la vidéo en
mouvement** : la note de 3,5/5 au manifeste porte sur une image de début et une image de fin, pas
sur la lecture. Ce qu'il faut regarder, dans
`workspace/runs/bms-science-fr-20260915-j7sf/clips/` : la **traînée derrière un sujet net sur
fond uni** pendant la parallaxe. À 130 px de dérive le sujet se dédoublait franchement ; c'est
ramené à 30 px avec un fond flouté, et le contrôle automatique ne voit plus aucun trou — mais
l'œil peut encore accrocher. **Si cela te gêne, la parade coûte un réglage** (`config/styles/
illustre.yaml` → `motion.default: ken_burns`) **et 25 minutes de re-rendu, sans regénérer une
seule image.** À faire avant l'étape 13.2, qui produit la vidéo de démonstration.

### Non bloquant — à trancher avant l'étape indiquée

Sept questions pour **Alek**, une pour **Thomas**, une ajoutée à l'étape 9. La n° 8 s'est matérialisée à l'étape 2.
Source : `STATE.md` § Questions ouvertes.

| # | Question | Qui tranche | À répondre avant | Statut |
|---|---|---|---|---|
| 1 | Comptes Google et Brand Accounts des chaînes BMS : existent-ils, sous quelle propriété, qui détient la récupération ? | Alek | Étape 14 | ⬜ |
| 2 | Raison sociale, SIREN et adresse de BMS (formulaire d'audit API + mentions légales) | Alek | Étape 14 | ⬜ |
| 3 | Qui relit, à quelle fréquence, par lots de quelle taille ? « L'équipe » n'est pas une réponse valable. | Alek (désigne Alek ou Sofiane) | Étape 9 | ⬜ |
| 4 | `auto-approve` activé ou non, et sur quelles chaînes ? À acter par écrit : l'exception éditoriale RIA tombe pour ces vidéos. | Alek | Étape 22.2 | ⬜ |
| 5 | Acompte Awin de 5 £ accepté, ou Awin écarté ? Si écarté, l'attribution repose sur CJ et Impact seuls. | Alek | Étape 21 | ⬜ |
| 6 | Réseau d'affiliation primaire et niches de départ (détermine `config/products/`) | Alek et Sofiane | Étape 21 | ⬜ |
| 7 | Combien de chaînes au lancement ? (**langue tranchée : anglais, Alek, 15/09/2026**) | Alek | Étape 14 | 🔄 — **la moitié de la réponse est mesurée : ≈ 7 vidéos/semaine, soit 3 chaînes à 2/semaine avec 1 nuit de marge — pour des vidéos de 10 minutes.** L'étape 6 ajoute la nuance : **aux durées médianes du registre (18 à 31 min), c'est 7/semaine sur les niches à coupe lente et 3 à 4 sur `histoire_doc`**, et **10/semaine n'est pas atteignable en local** (`docs/STYLES.md` § 3.1) |
| 8 | Quel compte Google de recherche et quelle machine / IP résidentielle ? **Devenu concret** : l'IP de cette machine est bloquée par YouTube pour les transcriptions depuis le 14/09/2026. | **Thomas** | ~~Étape 3~~ → **Étape 16** | ⬜ — l'étape 3 n'a pas eu besoin de nouvelle collecte, elle a travaillé sur les 349 transcriptions existantes. La question reste entière pour l'étape 16, qui relira le registre. |
| 10 | **Fournir une adresse de contact pour les API gratuites** (`FACTORY_CONTACT` dans `.env`). Vide, Wikimedia plafonne le pipeline à **10 req/min au lieu de 200** et **PubMed est entièrement écarté** (NCBI exige `tool=` et `email=`) : les niches santé et science ne tournent aujourd'hui que sur Wikipedia. Le pipeline refuse d'inventer une adresse. | Thomas (ou Alek, si l'adresse doit être celle de BMS) | Avant la première production réelle (étape 22) | ⬜ ajoutée à l'étape 10 |
| 11 | **Trancher la durée des vidéos par chaîne, format court ou long.** `REFERENTIEL.md` § 2 : `science_pop` mélange des formats (p75/p25 = 12,9) et « l'étape 10 doit fixer la durée par chaîne ». Aucun champ ne le permet dans `config/channels/<id>.yaml` : `plan` emploie la médiane de niche (648 s) **et le signale à chaque passage**. | Thomas, sur proposition | Avant l'étape 15 (le banc compare la durée rendue à cette cible) | ⬜ ajoutée à l'étape 10 |
| 12 | **Fournir la phrase de divulgation ORALE pour Impact et Awin.** Leurs listes fermées ne contiennent que des hashtags (`#ad`, `#sponsored`, `#Ad`, `#PaidAd`) : ils ne se prononcent pas, or `CONFORMITE.md` § 3 impose une mention orale dans les 30 premières secondes du segment. Le code retombe aujourd'hui sur la mention générique de la langue (« Publicité » / « Paid promotion ») et **n'invente aucune reformulation d'une mention contractuelle**. | Alek (avec le contrat du réseau) | Avant la première vidéo affiliée (étape 27) | ⬜ ajoutée à l'étape 10 |
| 9 | **Vérifier mot pour mot les phrases de divulgation Amazon en fr, es et it** — `config/languages/{fr,es,it}.yaml` les portent, reprises de mémoire et **non vérifiées sur le portail du programme**. La phrase est contractuelle : une formulation approchée n'est pas conforme. L'anglais vient de la source officielle. | Alek (ou Thomas au portail) | Avant la première vidéo affiliée (étape 27) | ⬜ ajoutée à l'étape 9 |

> Les colonnes « à répondre avant » sont déduites de la ROADMAP, sauf la n° 8 qui est
> explicite dans `STATE.md`. Elles sont indicatives : une réponse plus tôt ne coûte rien.

#### Capacité mesurée du système — réponse chiffrée à la question n° 7

Mesuré à l'étape 5.2, sur cette machine. `benchmarks/RESULTATS.md` § 2.7.

| Élément | Valeur |
|---|---|
| Vidéo de 10 min, style le moins cher (documentaire) | **3 h 55** |
| Vidéo de 10 min, style le plus cher (motion design) | **6 h 00** |
| Runs simultanés | **1** (contrainte des 16 Go de RAM) |
| Hypothèse | **une vidéo par nuit de machine** — 3 h 55 à 6 h y tiennent, et le M2 est aussi la machine de travail de Thomas |
| **Capacité** | **≈ 7 vidéos par semaine** |
| **Portefeuille tenable** | **3 chaînes × 2 vidéos/semaine = 6**, 1 nuit de marge pour les reprises |
| 4 chaînes × 2/semaine | 8/semaine — **au-dessus de la capacité** |

**Ce n'est pas l'API qui limite** : le plafond YouTube est de 6 uploads/jour, soit
42 vidéos/semaine — **six fois** la capacité locale. Le goulot est sur la machine,
et à **84 % dans la génération d'images**.

**À dire à Alek tel quel** : le registre décrit des réseaux de ~70 chaînes ; le
matériel actuel en nourrit **trois**. Passer à l'échelle du registre suppose le
serveur GPU déjà approuvé — et c'est la brique image qu'il faut y déporter, pas
le TTS ni le rendu.

**Ce que ce chiffre ne couvre pas** : la charge humaine. Chaque vidéo demande un
geste manuel en Studio (~2 min) tant que l'audit API n'est pas obtenu, plus la
relecture par lots, dont le rythme est la **question n° 3**, toujours ouverte.

### Décisions techniques en attente

| Sujet | Détail | Statut |
|---|---|---|
| **[É12.2] La capacité de ≈ 7 vidéos/semaine est à recalculer** | Elle a été établie avant que le moteur illustré existe. Mesuré maintenant : **2 h 47 par vidéo de 10 min** pour la première d'une chaîne, dont **84 % en génération d'images** (83 images, 98,8 s de médiane). La bibliothèque ne fait baisser ce coût que sur les runs **suivants**, et la réutilisation entre vidéos différentes **n'a pas encore été mesurée** (première vraie mesure à l'étape 24). | ⬜ à refaire avec ces chiffres, avant de répondre à Alek sur le nombre de chaînes |
| **[É8] Combien de publications par jour, vraiment ?** | `CONFORMITE.md` § 2 et son contrôle 27 disent **6**, en ne comptant que `videos.insert` à 1 600 unités. Une vidéo **complète** coûte 2 050 unités (insert 1 600 + miniature 50 + sous-titres 400) : six en font **12 300 pour un quota de 10 000/jour**. `INTERFACES.md` retient **4 par jour**, décidées sur le solde réel de `quota_ledger`, au nom de la règle « la plus stricte prime ». **À trancher : amender `CONFORMITE.md` § 2 et le contrôle 27, ou acter la cohabitation des deux textes.** Aucune conséquence avant l'**étape 23.1**. → **Thomas** |
| **[É4] Échantillons de voix pour le clonage** | Aucun TTS gratuit n'offre nativement 2 voix en FR, ES et IT : l'exigence ne tient que par **clonage**. Trois voies — tu enregistres 8 échantillons ; un corpus CC0 (mais le CC0 lève le droit d'auteur, **pas les droits de la personnalité attachés à la voix**) ; ou renoncer à 2 voix hors anglais. Le clonage déclenche aussi `contains_synthetic_media = true`. | ✅ **tranché 15/09/2026 — tu n'enregistres rien pour l'instant.** Donc : pas de clonage, voix préréglées seules. Deux effets favorables — `contains_synthetic_media` reste `false` pour la voix, et aucun champ `voice_release` à créer. **Si l'accent des voix cross-lingual est mauvais en 5.1, l'exigence « 2 voix par langue » hors anglais devient un arbitrage produit pour Alek.** |
| **[É4] Playwright et la règle « aucune automatisation de navigateur »** | Rendre notre propre HTML local en PNG, sans réseau, n'est pas l'automatisation d'un service tiers que vise la règle 11. Je l'ai retenu sur cette lecture. Si tu tranches strictement, le repli satori + resvg-js n'utilise aucun navigateur et la brique tient. **Recoupe la question `.playwright-mcp/` déjà ouverte ci-dessous.** | ✅ **tranché 15/09/2026 — retenu.** Limité au rendu local ; n'élargit pas les règles de `CONFORMITE.md` § 9 sur les services tiers. |
| **[É4] Internet Archive dans la liste blanche** | `docs/CONFORMITE.md` § 8 l'autorise, mais le service « ne garantit pas le statut des droits ». Retrait, ou vérification manuelle pièce par pièce ? | ✅ **tranché 15/09/2026 (tu m'as laissé décider) — maintenu, mais hors chemin automatique** : `requires_manual_review: true`, licence saisie à la main. |
| **[É4] Filigrane PerTh de Chatterbox** | Si le TTS principal tombe, le repli applique un filigrane audio **non désactivable** à chaque sortie : toutes nos voix deviennent traçables en permanence. MIT l'autorise commercialement. Acceptable ? | ✅ **tranché 15/09/2026 — accepté.** Aucune action. |
| **[É4] Freesound : négocier ou renoncer** | Les sons sont CC0/CC-BY, mais les CGU de l'**API** la réservent au non-commercial, le commercial étant « négocié au cas par cas avec l'UPF ». Écarté du pipeline en attendant. | ✅ **tranché 15/09/2026 (tu m'as laissé décider) — écarté, sans négociation.** À rouvrir seulement si 5.1 montre un manque de SFX. |
| Règle 11 (« aucune automatisation de navigateur ») | Un sous-agent de l'étape 1 a fait sa veille par navigateur automatisé. La règle vise le pipeline de publication, pas la recherche documentaire, mais sa formulation est absolue — et les étapes 3 et 16 font de la recherche à plus grande échelle. À préciser dans `docs/CONFORMITE.md`. | ⬜ à trancher |
| `.playwright-mcp/` | 112 Ko de dumps laissés par ce sous-agent à la racine. Ignoré par git, mais présent sur le disque. | ⬜ garder ou effacer |
| Groupe témoin pour miniatures et hooks (issu de l'étape 3) | Les motifs et les types de hook du référentiel décrivent les vidéos **les plus vues** : 188 miniatures sur 192 sont des succès, il n'y a rien à quoi les comparer. Collecter des miniatures et transcriptions de vidéos **médianes** des mêmes chaînes coûterait ~150 requêtes de transcription (mêmes précautions d'IP qu'à l'étape 2) et rendrait les « motifs gagnants » vraiment discriminants. | ⬜ à trancher **avant l'étape 16** |
| ~~**[É5.2] Plafond de cumul de 18 Go**~~ | Cumul réel en fin de 5.2 : **21,52 Go** (projection de 5.1 : 21,89, juste à 0,37 près). | ✅ **tranché 15/09/2026 — plafond relevé de 18 à 22 Go.** Le 18 datait d'une machine annoncée à 30 Gi libres ; il en reste 23. **Le plancher de 8 Go reste la seule règle dure.** Répercuté dans `CLAUDE.md` § 3 et `ROADMAP.md` § 3.2 et § 7. **Marge restante : 0,48 Go** — tout nouveau poids se gage sur un retrait |
| ~~**[É5.2] Seuil image « ≤ 90 s par 1280×720 »**~~ | Mesuré : **137,0 s de médiane** (94,6 à 160,5 selon le style). Pic mémoire tenu (11,15 Go contre < 13), qualité 4,6/5. | ✅ **tranché 15/09/2026 — seuil réécrit à 180 s, FLUX conservé.** Les 90 s venaient d'un M1 Max 64 Go ; SDXL n'est mesuré nulle part sur M2. Motif et **trois conséquences** (goulot à 84 %, justification du serveur C2, réutilisation étape 12.2 à mesurer) dans `outils/SELECTION.md` § 4 |
| **[É5.2] Cohérence de style sur 8 plans d'une même vidéo** | **Mesurée le 15/09/2026 : NON TENUE.** Sur 8 plans d'une même série, le `plan_08` change le personnage (femme aux cheveux longs → coupe courte masculine), laisse une **mèche détachée** à 17 px de la tête et porte un **pied retourné** ; le `plan_01` est le seul encadré des huit. C'est le critère qui prime pour cette brique. | ⬜ **arbitrage à l'étape 6** — voir la ligne « relecture plan par plan » ci-dessus |
| **[É5.2] La brique image impose-t-elle une relecture plan par plan ?** | **Mesuré : oui, en l'état.** Sur 8 plans d'une même vidéo, un portait trois défauts indépendants (personnage changé, mèche détachée, pied retourné) qu'**aucun contrôle automatique atteignable ici** ne voit — trois contrôles écrits et exécutés, cadrage et palette marchent, la détection d'éléments détachés échoue par principe. Il faudrait un VLM : hors budget mémoire, hors 0 €. **Cela heurte la contrainte 3 de `ROADMAP.md` § 3.4** (« par lots, jamais plan par plan ») : 840 plans/semaine à 7 vidéos. **Trois voies** — (1) assumer la relecture par plan et retirer la promesse d'autonomie sur ce point ; (2) juge VLM sur le serveur GPU, qui se confond avec le sélecteur « 4 images pour en garder une » ; (3) **réduire l'exposition** : les 4 plans sans anatomie humaine étaient indemnes, donc cadrer les personnages en buste et privilégier objets et lieux — l'option la moins chère. | ⬜ **à trancher par Thomas, à l'étape 6** |
| ~~**[É5.2] Qualité en mouvement, à regarder**~~ | Quatre MP4 + la planche de cohérence. | ✅ **vu 15/09/2026 — parallaxe 4/5 (« propre, plus aucun trou, les plans dans le bon sens »), Ken Burns 4/5, whiteboard 4/5, Revideo 4/5, cohérence d'identité 4/5.** Tous les seuils de qualité sont tenus, aucun repli activé. Preuve LTX vue et **gardée pour la démonstration à Alek**. **Une réserve inscrite** : la tenue du personnage dérive → gabarit de prompt, étape 12.2 |
| **[É5.1] Seuil de facteur temps réel du TTS** | `SELECTION.md` § 2 fixe ≤ 1,0 ; le mesuré est 3,29. Le modèle est conservé quand même, faute de repli. **Un seuil qu'on dépasse sciemment doit être réécrit, pas laissé tel quel** — soit relevé avec sa justification, soit remplacé par une contrainte de débit à l'échelle du portefeuille. | ⬜ à réécrire, au plus tard à l'étape 24 (dimensionnement du portefeuille) |

---

## 2. Avancement

Légende : ✅ terminée · 🔄 en cours · ⬜ à lancer · ⛔ bloquée

| Phase | Étape | Titre | Statut | Date | Commit | Critères |
|---|---|---|---|---|---|---|
| P0 | **1** | Amorcer le dépôt et figer le cadre de conformité | ✅ | 14/09/2026 | `2a28e00` | 5/5 |
| P0 | **2** | Collecter les données du registre via l'API officielle | ✅ | 14/09/2026 | `a0a8e76` | 5/5 |
| P0 | **3** | Référentiel exploitable, sujets porteurs, taxonomie des hooks, trajectoires | ✅ | 15/09/2026 | `f763788` | 6/6 |
| P0 | **4** | Veille et sélection des outils par brique | ✅ | 15/09/2026 | `5b5b97f` | 4/4 |
| P0 | **5.1** | Mesurer texte et audio sur le M2 (LLM, TTS, ASR, musique) | ✅ | 15/09/2026 | `b97beae` | 5/6 — musique non mesurable (bloquée sur Alek) |
| P0 | **5.2** | Mesurer image, parallaxe, composition et une preuve vidéo IA conditionnelle | ✅ | 15/09/2026 | `9c96e2f` | **9/10** — preuve vidéo IA produite, seuil image réécrit (90 → 180 s). **Un seuil non tenu : cohérence sur 8 plans d'une même vidéo**, et la métrique employée ne sait pas la mesurer → arbitrage à l'étape 6 |
| P0 | **6** | Trancher les styles et la réponse à Alek | ✅ | 15/09/2026 | `c56fb69` | **4/4** — matrice de 9 lignes avec statut, coût et preuve · « Message à Alek » de 10 lignes · ordre des moteurs fixé (2 déplacements) · 18 objections traitées (17 retenues, 1 refusée sur preuve) |
| P0 | **7** | Installer et figer l'environnement | ✅ | 15/09/2026 | `4c4211d` | **3/3** — `uv run factory doctor` rend **0**, **14 contrôles en 69 s** (13 PASS + `ASR fr` en WARN, mesuré et non bloquant), plusieurs exécutions complètes · `docs/INSTALL.md` (198 l.) permet une installation depuis zéro en ~20 min hors téléchargements · `git status` propre |
| P1 | **8** | Architecture et contrats d'interface | ✅ | 15/09/2026 | `e39416c` | **4/4** — `INTERFACES.md` donne un exemple pour chacun des **31 contrats** (seuil : ≥ 10 fichiers intermédiaires + `config/channels/<id>.yaml`), **30 exemples** JSON/YAML/SQL · interface `StyleEngine` écrite en signature Python avec son registre · les **25 champs de `CONFORMITE.md` § 10.1** présents au manifeste, plus ceux de la boucle de rétroaction · « Objections et réponses » dans les deux documents, **19 objections traitées** (17 corrigées, 1 corrigée autrement, 1 refusée sur preuve). **1 objection non résolue portée au § 1** (plafond de publications par jour). |
| P1 | **9** | Modèle de données versionné, configuration, secrets | ✅ | 15/09/2026 | `5c0955c` | **4/4** — `uv run pytest -q` : **67 tests verts** (seuil ≥ 12) · `factory config validate` : **0** sur les exemples, **1** et 9 erreurs nommées sur `tests/fixtures/channel_invalide.yaml` · les **25 champs de `CONFORMITE.md` § 10.1** présents dans `models.py`, obligatoires ou à défaut explicite · `INTERFACES.md` mis à jour de ses **5 écarts** (§ 5 bis) |
| P1 | **10** | Sujet issu du référentiel → recherche → script structuré | ✅ | 15/09/2026 | `8bd61d2` | **4/4** — `factory plan --channel bms-science-fr` : sujet `source = referentiel`, rang 1, ratio 2 070× la médiane de sa chaîne source · `factory research` : **6 sources (FR) et 4 (EN)** avec URL, licence et citations, seuil ≥ 3 · `factory script` : deux `script.json` valides pydantic, durée estimée **+6,9 %** (FR) et **−3,6 %** (EN) de la cible de niche, tolérance ± 15 %, type de hook enregistré, **2 boucles plantées et 2 payées**, `editorial_signature` remplie · temps de chaque étape dans `manifest.json`. **93 tests verts.** 2 défauts de script mesurés et transmis à l'étape 16 |
| P1 | **11** | Voix et sous-titres | ✅ | 16/09/2026 | `67e416a` | **5/5** — `voice.wav` produit sur les deux runs · loudness intégrée mesurée par `ebur128` à **-14,3 LUFS** (fenêtre -15 à -13) et crête réelle **-1,4** et **-1,3 dBTP** (plafond -1) · `timings.json` couvre les **28 segments** des deux runs · `subtitles.srt` : **337** et **303** sous-titres, **0 tranche de 5 s sans sous-titre** sur 148 et 134, aucune ligne au-delà de **38 caractères**, aucun sous-titre de plus de 2 lignes · **WER 4,42 %** (FR) et **2,99 %** (EN), seuil 8 % · timings au manifeste. **125 tests verts.** **Voix non écoutée** : arbitrage TTS toujours dû |
| P1 | **12.1** | Découpage en plans, interface StyleEngine, moteur « cartes » | ✅ | 16/09/2026 | `c8ca2ba` | **4/4** — `shotlist.json` : **médiane hors hook 5,88 s** pour une cible de **5,85 s**, soit **+0,51 %** (tolérance ±10 %), obtenue **au premier essai** · hook : médiane **2,47 s**, plus long plan **2,80 s**, plafond **4,10 s** · **27 ruptures** aux positions du script, **127 plans** pavant la piste sans trou (737,921 s pour 737,921 s) · **127 clips**, boucle `ffprobe` à **0 erreur** (1920×1080, 30 ips, `yuv420p`, durée à ±0,05 s) · temps par plan au manifeste (**médiane 1,99 s**, total **259 s**). **143 tests verts.** **Résidu : ce ffmpeg n'a pas `drawtext` ni libass** — contourné ici par Pillow, **bloquant pour l'incrustation des sous-titres à l'étape 13** |
| P1 | **12.2** | Moteur « illustré animé » | ✅ | 16/09/2026 | `854febe` | **5/5** — **127 clips** en style illustré, boucle `ffprobe` à **0 erreur** (1920×1080, 30 ips, `yuv420p`, durée à ±0,05 s) · **83 images générées sur 83 au premier essai (100 %**, seuil ≥ 90 %) · temps au manifeste : **médiane 98,8 s par image** en 1280×720 (pic MLX **11,15 Go**), **médiane 10,64 s par plan**, **2 h 47 au total** · **4 images regardées, cohérence de style notée 4,5/5** et consignée dans `manifest.decisions.quality_notes` · chaque image a son `licence.json` (modèle, prompt, graine, étapes, résolution) · **2ᵉ exécution du même run : 0 génération**, `prepare_assets` **8 585,65 s → 0,66 s**. **158 tests verts**, `factory doctor` 14/14. **Résidus : le mouvement n'a été vu par personne en lecture** (à regarder avant l'étape 13.2) et **27 plans de rupture reçoivent une image au lieu d'un asset de banque** (étape 17) |
| P1 | 13.1 | Montage, musique, sous-titres, export vérifié | ⬜ | — | — | — |
| P1 | 13.2 | Miniature, métadonnées, `factory run`, première vidéo complète | ⬜ | — | — | — |
| P1 | 14 | Ouvrir le canal officiel : upload privé, OAuth en production, dépôt de l'audit API | ⬜ | — | — | — |
| P2 | 15 | Banc d'évaluation objectif et portillon qualité | ⬜ | — | — | — |
| P2 | 16 | Ingénierie du hook et de la rétention | ⬜ | — | — | — |
| P2 | 17 | Moteur « documentaire » (banques libres) et rythme de coupe vérifié | ⬜ | — | — | — |
| P3 | 18 | Entrepôt concurrentiel et snapshots quotidiens | ⬜ | — | — | — |
| P3 | 19 | Détection et notation de niches | ⬜ | — | — | — |
| P3 | 20 | Sujets gagnants, trous dans l'offre, file de sujets | ⬜ | — | — | — |
| P3 | 21 | Titres, miniatures et métadonnées en variantes, sub-ID d'affiliation | ⬜ | — | — | — |
| P4 | 22.1 | Orchestrateur : file, reprise, journal, daemon, sauvegardes | ⬜ | — | — | — |
| P4 | 22.2 | Relecture par lots, régénération sous seuil, alertes | ⬜ | — | — | — |
| P4 | 23.1 | Publication par l'API : OAuth par chaîne, upload, miniature, sous-titres, label, quota, rapports « reach » | ⬜ | — | — | — |
| P4 | 23.2 | Calendrier crédible, checklist de conformité pré-publication, bascule post-audit | ⬜ | — | — | — |
| P4 | 24 | Déclinaison multilingue par adaptation | ⬜ | — | — | — |
| P5 | 25 | Récupérer les performances et les joindre au manifeste | ⬜ | — | — | — |
| P5 | 26 | Apprendre et réinjecter ; valider le banc contre les vues | ⬜ | — | — | — |
| P5 | 27 | Affiliation, funnel et économie unitaire | ⬜ | — | — | — |
| P6 | 28 | Tableau de bord d'exploitation | ⬜ | — | — | — |
| P6 | 29 | Bibliothèque d'assets, voix et personnages cohérents, avatar 2D, chartes | ⬜ | — | — | **passe en dernier des moteurs de style** (étape 6) : aucun avatar animé n'a jamais été rendu |
| P6→**P2** | 30.1 | Moteur « motion design » (Revideo) | ⬜ | — | — | **remonté en phase 2 par l'étape 6** : seul moteur qui n'achète pas ses visuels à FLUX (2,7 min/min projetés contre 19,7 à 32,8), format de la chaîne la plus performante du registre, aucune anatomie générée |
| P6 | 30.2 | Moteur « whiteboard » | ⬜ | — | — | — |
| P6 | 31 | Documentation d'exploitation, reprise et plan de passage à l'échelle | ⬜ | — | — | — |

**37 sessions au total · 9 terminées · 28 restantes. Phase 0 close, phase 1 ouverte.**

---

## 3. Journal

### Preuve motion design — hors feuille de route (16/09/2026)

**Pourquoi.** Thomas a regardé les 127 plans de l'étape 12.2 : « ce sont des images fixes avec un
effet de glissement ». Le motion design est le style n° 2 du message à Alek et **n'avait jamais
été rendu en séquence** — la note 4/5 de la matrice portait, de l'aveu du document, sur « une
scène texte sur fond uni ». Session de preuve, pas de construction : **`factory/` n'est pas
touché**, rien n'est créé sous `config/styles/` ni `render/`.

**Livrables.** `benchmarks/preuve_motion/` — `motion_A.mp4` (typographie cinétique pure),
`motion_B.mp4` (schéma animé vectoriel saccharose → insuline), `motion_C.mp4` (hybride sur
3 PNG de `workspace/library/images`), `RESULTATS.md`, `README.md`, et le projet Revideo
(`revideo/src/motion_{a,b,c}.tsx`, 752 lignes, `charte.ts` recopié de la charte de chaîne,
`mesure.py` qui échantillonne la mémoire de l'arbre de processus). Même texte et même voix pour
les trois : hook + segment 1 du run `bms-science-fr-20260915-j7sf`, 0 → 32,000 s.

**Critères mesurés.** Trois MP4 **1920×1080, 30 ips, 960 images comptées, 32,000 s, piste aac
48 kHz** · rendu **54,5 / 115,5 / 122,9 img/s** (A/B/C), soit **0,56 / 0,28 / 0,25 minute de
calcul par minute de vidéo** · pic mémoire **1,14 / 1,11 / 1,06 Go** · **zéro image générée dans
les trois** (C réemploie 3 PNG de l'étape 12.2) · voix à **-15,0 LUFS** sur la fenêtre.
**Le seuil « ≥ 2 img/s » du § 7 de `STYLES.md` est tenu 27 à 61 fois.**

**Divergences et résidus.** (1) **La note ≥ 3/5 du § 7 n'est pas acquise** : la session ne
perçoit pas le mouvement en lecture et **ne note pas la fluidité** — porté au § 1. (2) La
projection « 2,7 min/min » de `STYLES.md` est **corrigée** : 0,28-0,56 en vecteur pur,
1,90 avec 1 fond/min à l'image mesurée de 12.2, 2,53 avec l'hypothèse d'origine. (3) **Le
Chromium de Puppeteer (0,59 Go) portait le cumul retenu à 22,11 Go, au-dessus du plafond** :
purgé, Revideo tourne sur le Chromium de Playwright déjà installé (8,05 s contre 8,31 s,
équivalent) ; **cumul revenu à 21,52 Go**. (4) **B ne se généralise pas** : 43 repères
temporels à la main et une géométrie propre au sujet. (5) **Les 83 PNG de bibliothèque ne sont
pas des fonds** — tonalité non homogène, 1280×720 agrandi à 1,5, sujet centré par construction.
(6) **Divergence de documents non tranchée** : `STYLES.md` § 6 met le motion design en phase 2,
`ROADMAP.md` § 5 ligne 168 le laisse en phase 6. Amendement proposé au § 1, **non appliqué**.

### Étape 12.2 — Moteur « illustré animé »

**Livrables.** `factory/assets/images.py` (prompt de charte, cache de bibliothèque, licence par
image, traduction des intentions), `factory/assets/parallax.py` et `_depth_worker.py` (profondeur
en lot, couches cumulatives, parallaxe, Ken Burns, contrôle magenta), `factory/styles/illustre.py`
(moteur), migration `002_library.sql` (`library_assets`, `library_uses`),
`tests/test_etape12_2.py` (15 tests). `charte` gagne `style_prefix`, `style_suffix` et
`negative_prompt` ; `charte.framing` gagne `background` et `subject_scale` ; le manifeste gagne
`decisions.quality_notes[]`. **7 écarts inscrits à `INTERFACES.md` § 5 bis** (n° 25 à 31).

**Critères, tous mesurés.** 127 plans rendus en style illustré · **83 images générées, 83 au
premier essai (100 %)** · temps au manifeste (médiane **98,8 s** par image, **10,64 s** par plan,
**10 020 s** au total) · 4 images extraites et regardées, **cohérence de style 4,5/5** · chaque
image porte son `licence.json` · **deuxième exécution : 0 génération**.

**Deux défauts trouvés en cours d'étape, et c'est le fait marquant.**

1. **Le prompt faisait écrire du texte dans l'image.** Sur les cinq premières images, deux
   portaient du faux texte en gros caractères et **l'une avait recopié le prompt français
   lui-même**. Deux causes cumulées : le suffixe de charte **nommait** le texte (« unmarked »,
   « untitled », « labels » sont eux-mêmes des déclencheurs), et FLUX.2 [klein], légendé en
   anglais, **rend littéralement ce qu'il ne comprend pas**. Corrigé par un suffixe positif et
   par la traduction des intentions via le LLM local (56/56, ~2 min, puis depuis le cache).
   Mesure après correction : **8 prompts sur 83 (10 %)** gardent un déclencheur.
2. **La parallaxe dédoublait le sujet.** À 130 px de dérive, sur une illustration plate — sujet
   net, fond uni — le glissement **découvre un fond qui n'existe pas** : trois copies décalées.
   Corrigé par un inpainting par flou et une dérive ramenée à 30 px. **0 trou magenta sur 127
   plans, 0 repli Ken Burns.**

**Divergences assumées.** Les 27 plans de rupture demandent un asset `stock` (banques libres,
étape 17) et reçoivent une image générée en cadrage large ; le journal le signale à chaque
passage. `charte.negative_prompt` existe mais **n'est pas envoyé** : FLUX.2 refuse les prompts
négatifs.

**Résidus.** Le mouvement n'a **jamais été vu en lecture** — la note de 3,5/5 porte sur deux
images fixes, à confirmer par Thomas avant l'étape 13.2. La bibliothèque pèse **96 Mo pour une
vidéo** et ne fait baisser le coût que sur les runs suivants : **la première vidéo d'une chaîne
paie tout**, soit 2 h 47. L'estimation de ≈ 7 vidéos/semaine date d'avant ce moteur et **doit
être refaite**.

### Étape 12.1 — Découpage en plans, interface StyleEngine, moteur « cartes »

**Date** : 16/09/2026 · **Commit** : `c8ca2ba` · **Poids disque ajouté** : 0 Go de modèle ; **0,86 Mo** de police (Inter, SIL OFL 1.1, dans le dépôt) ; 61 Mo de sorties de run, hors git.

**Livrables.** `factory/steps/shotlist.py` (découpage), `factory/steps/render.py` (boucle de rendu et vérification), `factory/video.py` (helpers ffmpeg, polices, calques, `verify_clip`), `factory/styles/base.py` (`Protocol StyleEngine` + socle), `factory/styles/__init__.py` (registre), `factory/styles/cartes.py` (premier moteur), commandes `factory shotlist --run [--style]` et `factory render --run [--style] [--force]`, `assets/fonts/`, `tests/test_etape12_1.py` (18 tests). Pour le run FR : `shotlist.json`, `assets/shot_XX/card.png` + `licence.json`, `clips/shot_000..126.mp4`, `workspace/logs/etape12_1.log`.

**Critères de fin d'étape — 4 sur 4.**

| Critère | Seuil | Mesuré |
|---|---|---|
| Médiane de durée de plan, hors hook | ± 10 % de `cut_rhythm_target_s` (5,85 s) | **5,88 s, +0,51 %** |
| Plans du hook | ≤ 0,7 × cible = 4,10 s | **2,47 s de médiane, 2,80 s au plus long** |
| Ruptures aux positions du script | 1 par segment porteur d'`interrupt` | **27 / 27** |
| Clips existants et au contrat | 1920×1080, 30 ips, durée ±0,05 s | **127 / 127, 0 écart** |
| Temps de rendu par plan au manifeste | présent | **médiane 1,99 s**, total **259 s** |

Déciles de durée : **p10 4,68 s / p90 7,07 s**. Pavage : **737,921 s de plans pour 737,921 s de piste, 0 trou**.

**Ce que l'étape a mesuré et qui déplace le projet.**

1. **Le rythme de coupe du registre est désormais un paramètre appliqué et auto-vérifié** — thèse n° 3 du projet. Il n'est plus une ligne de tableau : `shotlist` lit `REFERENTIEL.json → science_pop.cible_montage`, produit 127 plans et **refuse de livrer** (code 2) si la médiane sort de ±10 %. Le mécanisme qui la fait tomber juste n'est pas une correction après coup : c'est le **choix du nombre de plans par fenêtre** (`n = round(durée / cible)`, corrigé pour rester dans la bande de jitter), le jitter étant ensuite **normalisé** sur la durée exacte de la fenêtre — somme juste, aucune dérive cumulée. Les trois essais de repli n'ont pas servi.
2. **Ce ffmpeg n'a ni `drawtext` ni libass, et l'étape 13 va buter dessus.** L'étape 11 avait relevé l'absence de libass ; la mesure du 16/09 l'étend : la build Homebrew 8.1.2 est compilée **sans `libfreetype` ni `libfontconfig`** (« No such filter: 'drawtext' »), et la formule `ffmpeg` de homebrew-core 9.0.1 ne les liste pas non plus dans ses dépendances. Le moteur « cartes » contourne en **rastérisant le texte par Pillow** — le rendu vidéo reste entièrement ffmpeg —, et y gagne un retour à la ligne mesuré au pixel que `drawtext` n'a pas. **Mais incruster `subtitles.ass` dans `final.mp4` n'a pas de contournement de cette sorte : il faudra un ffmpeg avec libass.** → § 1.
3. **Le coût de rendu est enfin chiffré : 2 s par plan, soit ~4 min pour 12 min de vidéo** sur le moteur le plus léger. À comparer aux ~20 min de script (étape 10) et ~45 min de voix (étape 11) : **le montage n'est pas le poste coûteux**, l'étape 12.2 (images générées) le sera.
4. **Deux défauts visuels trouvés à l'œil, corrigés, puis remesurés au pixel.** *(a)* Le dégradé de fond traversait l'image d'une **bande à bord franc** — `gradients` répète son motif quand ses extrémités sont laissées au hasard ; extrémités imposées et palette ramenée à deux teintes mélangées, le plus grand saut de luminance tombe à **2,9 sur 20 px**. *(b)* Le souligné d'accent était **calé à gauche du bloc de texte** : centré, l'écart mesuré entre son centre et celui du texte est de **3 px sur 1920**.

**Divergences et résidus.**

- **8 écarts au contrat inscrits à `INTERFACES.md` § 5 bis** (n° 17 à 24) : rastérisation Pillow au lieu de `drawtext` ; `StatsShotlist` gagne `p10`, `p90`, `n_shots`, `median_hook_s` et sa médiane est mesurée hors hook ; `manifest.decisions` gagne `cut_rhythm_planned_s` à côté de `cut_rhythm_measured_s` ; `prompt_or_keywords` porte le gabarit pour un asset `card` ; une rupture sur un moteur à un seul type d'asset change de gabarit et le signale ; `provider: charte` avec une `source_url` pointant sur le fichier de chaîne ; la phrase de divulgation est **passée** au moteur ; `-crf 18` (contrat) et non 16 (prompt).
- **Aucun plan sponsor dans ce run** : le script FR ne porte aucun segment `disclosure_spoken`. Le bandeau « Publicité » a donc été prouvé **sur un plan fabriqué pour l'occasion** (image regardée, bandeau présent, texte lu dans `config/languages/fr.yaml`) et par un test. Il n'a **pas** été exercé par un run réel — il le sera au premier run à produit d'affiliation.
- **99 plans sur 127 n'ont aucun texte** : le contrat réserve `on_screen_text` au premier plan d'un segment. Ces plans montrent un dégradé et une barre mobile. C'est cohérent avec un moteur interne de calibration — et une raison de plus de **ne jamais le publier tel quel**.
- Le moteur « cartes » passe de `statut: planifie` à **`retenu_v1`** dans `config/styles/cartes.yaml`. Les cinq autres restent `planifie` et le registre nomme l'étape qui les livrera.

### Étape 11 — Voix, loudness aux normes YouTube, sous-titres dynamiques

**Date** : 16/09/2026 · **Commit** : `67e416a` · **Poids disque ajouté** : 0 Go de modèle ; 130 Mo de WAV de voix pour les deux runs, 836 Ko de cache de transcription.

**Livrables.** `factory/audio.py` (mesure `ebur128`, nettoyage des silences, concaténation avec pauses, normalisation deux passes), `factory/tts.py` et `factory/asr.py` (un sous-processus par modèle, qui se termine), `factory/steps/voice.py` et `factory/steps/subtitles.py`, commandes `factory voice --run` et `factory subtitles --run`, bloc `tts` dans les 4 `config/languages/`, 5 modèles de données de plus, `tests/test_etape11.py` (32 tests). Pour chaque run : `voice/segment_00..27.wav`, `voice/voice.wav`, `voice/timings.json`, `words.json`, `subtitles.srt`, `subtitles.ass`.

**Critères de fin d'étape — 5 sur 5.**

| Critère | Seuil | Mesuré FR | Mesuré EN |
|---|---|---|---|
| `voice.wav` existe, loudness intégrée | -15 à -13 LUFS | **-14,3** | **-14,3** |
| Crête réelle | ≤ -1 dBTP | **-1,4** | **-1,3** |
| `timings.json` couvre tous les segments | 28 / 28 | **28** | **28** |
| Sous-titres : ≥ 1 par tranche de 5 s | 0 tranche vide | **0 / 148** | **0 / 134** |
| Sous-titres : ≤ 2 lignes de 42 caractères | 0 dépassement | **0** (max 38 car.) | **0** (max 38 car.) |
| WER transcription / script | < 8 % | **4,42 %** | **2,99 %** |

Durées : **737,9 s** (FR, 337 sous-titres) et **667,2 s** (EN, 303 sous-titres).

**Ce que l'étape a mesuré et qui déplace le projet.**

1. **parakeet est inutilisable en français sur une piste de production, et cela clôt l'enquête ouverte à l'étape 5.1.** Sur 738 s de français, il rend **0,024 de couverture et 98,6 % de WER** — il transcrit quelques mots puis abandonne. Avec découpage en fenêtres de 20 s : 0,661 et 47,5 %. **whisper : 0,917 et 4,4 %.** En anglais l'ordre s'inverse — parakeet découpé donne **0,983 et 3,0 %** et whisper n'est pas appelé. La chaîne de repli écrite au contrat de l'étape 8 a fonctionné seule, sans intervention : c'est elle qui sépare un sous-titrage exploitable d'un sous-titrage vide. **La troncature ne s'atténue pas avec la longueur du fichier, elle s'aggrave.**
2. **La voix coûte 45 minutes de calcul par vidéo, machine monopolisée**, et le chiffre est maintenant mesuré en production, pas extrapolé : TTS **2 451 s** (FR) et **2 135 s** (EN) — facteur temps réel **3,33** et **3,21**, conforme aux 3,29-3,57 de l'étape 5.1 —, puis 29 s de normalisation et 139 à 293 s de transcription. À ajouter aux ~20 min de script de l'étape 10 : **une vidéo coûte ≈ 1 h 05 de calcul avant même la première image**. À porter au dimensionnement du portefeuille (étape 24).
3. **Le débit du référentiel est faux de 6 % pour cette voix.** `REFERENTIEL.json` retient 134,9 mots/min pour `science_pop` ; la voix synthétisée rend **126,7** (FR) et **126,3** (EN). Les durées dépassent l'estimation du script de **+6,5 %** et **+6,8 %** — **même signe, même ordre de grandeur sur deux langues**, donc une erreur systématique et non du bruit. Le référentiel mesure des présentateurs humains de chaînes tierces ; le pipeline emploie une voix de synthèse. **Correction à faire à l'étape 16.**
4. **Trois défauts d'exécution trouvés et corrigés, tous invisibles en test unitaire.** *(a)* Sans `torch.mps.empty_cache()` entre deux synthèses, le temps **entre** deux unités passe de 0 à **250-425 s** après la dixième, pour un calcul inchangé : la machine comprimait 4,4 Go de mémoire. Corrigé, l'inter-unité retombe à 0,4 s — **45 minutes récupérées par run**. *(b)* Le TTS **se fige** environ une unité sur cent : `seg_24` du run FR n'a pas rendu la main pendant **52 minutes**, et la même unité a été synthétisée en **71 s** à la tentative suivante. `voice` porte désormais un chien de garde de 420 s et jusqu'à 3 relances, les unités déjà écrites étant sautées. *(c)* `loudnorm` visé à -1,0 dBTP est **mesuré à -0,9** par `ebur128` : le filtre vise maintenant -1,5 pour que la mesure tienne le contrat.

**Divergences et résidus.**

- **La voix n'a été écoutée par personne** (Thomas indisponible le 16/09/2026) : « non évaluée ». L'exigence « ≥ 2 voix par langue » et l'arbitrage Qwen3-TTS / Kokoro restent entiers → § 1. Extraits de 30 s prêts dans `workspace/logs/ecoute11/`.
- **`subtitles.ass` n'a pas pu être affiché** : le build ffmpeg local n'a **pas libass** (`ffmpeg -filters` ne connaît ni `subtitles` ni `ass`). Le fichier est vérifié structurellement — 23 colonnes de style déclarées et écrites, sous-titres croissants et sans chevauchement, somme des balises de karaoké égale à la fenêtre sur 100 % des sous-titres — mais jamais rendu. Sans effet aujourd'hui (`burn_in: false`, la piste `.srt` est envoyée à l'API) ; **l'incrustation de l'étape 22 exigera un ffmpeg compilé avec libass**.
- **Deux sous-titres du run FR durent 0,20 s** au lieu du plancher de 0,4 s : `seg_26` compte 22 mots interpolés, faute d'ancrage whisper, et l'interpolation les tasse. 2 sur 337 ; aucun sur le run EN. Le levier est la couverture, pas le découpage.
- **Le hook reste une unité de synthèse de 6 s** là où `ARCHITECTURE.md` § 2.2 demande 15 s : la règle fusionne les segments **de même rôle**, et fusionner le hook supprimerait la respiration de 600 ms qui le suit. Assumé et signalé à chaque passage.
- **6 écarts inscrits à `INTERFACES.md` § 5 bis** (n° 11 à 16) : modélisation de `voice/timings.json`, bloc `tts` des langues, 5 champs de mesure au manifeste, ligne `Format:` ASS complète, largeur de ligne au plus strict des deux textes, `operator_override` ajouté aux motifs de repli.

### Étape 10 — Sujet issu du référentiel, recherche, script structuré

**15/09/2026 · commit `8bd61d2` · 0 Go téléchargé · un seul modèle en mémoire, un sous-processus par appel.**

**Livrables.** `factory/llm.py` (532 l. — client `llama-cli`, conversion JSON Schema → GBNF,
réparation JSON à 3 essais, cache d'appels), `factory/steps/plan.py` (166 l.),
`research.py` (532 l.), `script.py` (629 l.), `factory/core/referentiel.py` et `runs.py`
(184 l.), `factory/prompts/script_fr.md` et `script_en.md` (251 l.), 4 modèles racine de plus
dans `models.py` (`Research`, `Fait`, `SourceConsultee`, `AnglePropose`), 3 commandes CLI
(`plan`, `research`, `script`), `tests/test_etape10.py` (217 l.), 5 divergences ajoutées au
§ 5 bis de `INTERFACES.md`.

**Critères mesurés.** `factory plan --channel bms-science-fr` → sujet pris dans
`REFERENTIEL.json`, `source = referentiel`, preuve = rang 1, **ratio 2 070× la médiane de sa
chaîne source** · `factory research` → **6 sources FR / 4 EN**, chacune avec URL, titre,
licence et faits rattachés (seuil ≥ 3) · `factory script` → deux `script.json` valides
pydantic, **28 segments**, durée estimée **693 s (+6,9 %)** et **625 s (−3,6 %)** pour une
cible de 648 s à ± 15 %, hook du type tiré enregistré au manifeste, **2 boucles plantées et
2 payées**, `editorial_signature` remplie, **0 segment `point` sans fait cité**, **0 texte à
l'écran au-delà de 6 mots** · timings dans `manifest.json` · `uv run pytest -q` → **93 verts**.

**Temps mesurés (M2 16 Go).** `plan` 0,03 s · `research` 248 s (FR) / 274 s (EN) · `script`
669 s (FR) / 701 s (EN), 9 à 10 appels LLM, **9 à 14 jetons/s**. **≈ 20 min de calcul
par script, machine monopolisée** — à ajouter aux 33 min de TTS dans le dimensionnement du
portefeuille (étape 24).

**Divergences assumées avec le prompt d'étape.** (1) Le script est écrit en **plusieurs
appels** (plan, accroche, narration par lots de 4) et non en un seul objet `Script` : 8 k
jetons de contexte contre ~1 460 mots de cible. Le code construit le squelette, le modèle
remplit le texte. (2) Le raccourcissement est **déterministe, en code** (retaille par phrases
entières) ; les deux corrections par LLM prévues sont réservées au cas « trop court » et n'ont
servi sur aucun des deux runs. (3) `--json-schema` de llama.cpp échoue sur cette build : la
grammaire GBNF est produite par `factory/llm.py`.

**Résidus.** Deux défauts de script, mesurés, transmis à l'étape 16 : **répétition des faits**
(0,28 à 0,32 fait par segment de contenu, chaque fait resservi ~3 fois — une alerte le signale
désormais à chaque run) et **boucles ouvertes plantées à 0 s et 4-7 s** là où le référentiel
mesure 67,4 s sur `science_pop`. Deux actions humaines ouvertes (§ 1, n° 10 et 11) :
`FACTORY_CONTACT` et la durée par chaîne. Semantic Scholar et arXiv sont inutilisables depuis
cette machine (429), écartées avec leur motif dans `sources_rejected`.

### Étape 9 — Modèle de données versionné, configuration, secrets

**15/09/2026 · commit `5c0955c` · 0 Go · aucun modèle IA chargé, aucun réseau.**

**Livrables.** `factory/core/models.py` (1 506 l., **90 classes**, **18 modèles racine**),
`paths.py` (`RunPaths`, `LibraryPaths`), `config.py` (chargement, validations croisées,
`get_channel`, `list_channels`, génération de `video_id`), `secrets.py` (`.env` + `secrets/`,
jamais journalisés), `db.py` + `migrations/001_runs_jobs_review.sql` (`runs`, `jobs`,
`review_log`), `factory config validate|show`, **23 YAML d'exemple**, **3 fichiers de tests**
et un YAML volontairement cassé.

**Critères mesurés.** `uv run pytest -q` → **67 passed** en 0,8 s · `uv run factory config
validate` → **0**, 9 alertes · sur le fichier cassé → **1**, 9 erreurs nommées ·
`grep -c "class " factory/core/models.py` → **90**.

**Ce que le modèle rend impossible, et qui n'était qu'écrit jusqu'ici.** Une cadence à
3 vidéos par semaine (type entier `1..2`) · un jeton OAuth collé dans un YAML de chaîne
(motif `^secrets/….json$`) · un asset en licence non commerciale · une image générée
localement portant une `source_url` · un contrôle de qualité « non mesuré » noté comme
réussi · un script sponsorisé sans divulgation orale · un manifeste qui atteindrait
`ready_to_publish` avec un champ de `CONFORMITE.md` § 10.1 vide · deux chaînes de même
langue parlant de la même voix.

**Divergences avec `INTERFACES.md` — 5, toutes inscrites au § 5 bis du document.**
`youtube.captions_upload` et `style.templates[]` ajoutés (sans eux, deux règles du contrat
n'étaient pas vérifiables), `rythme_coupe_s.fallback_provisoire_s` ajouté (`spec.json`
l'invoquait sans qu'aucun fichier ne le porte), `schema_version` du manifeste à la racine,
pas d'entrée `cj` dans `disclosure`.

**Résidus.** *(1)* `research.json`, `voice/timings.json`, `metadata.json` et
`thumbnails.json` n'ont pas de modèle : les étapes 10, 11, 20 et 21 les écriront.
*(2)* Les 6 styles sont en `planifie` — aucun moteur n'existe, et le validateur le dit à
chaque passage. *(3)* Les voix Kokoro déclarées dans les 4 langues viennent du catalogue
publié du moteur : **le moteur n'est pas installé, aucune n'a été écoutée**, et l'arbitrage
de licence GPL reste ouvert. *(4)* Les phrases de divulgation Amazon fr, es et it sont à
vérifier au portail (§ 1, n° 9).

### Étape 8 — Architecture et contrats d'interface

**Date.** 15/09/2026. **Commit** `e39416c`. **Poids disque : 0.** Aucun code exécutable, aucun modèle touché, aucun téléchargement.

**Livrables.** `docs/ARCHITECTURE.md` (244 lignes) et `docs/INTERFACES.md` (1 022 lignes). `STATE.md` allégé de deux blocs vers `STATE-ARCHIVE.md` pour rester sous 120 lignes.

**Critères mesurés.** `grep -c "^### " docs/INTERFACES.md` = **31** (seuil 14) · `grep -c '```' docs/INTERFACES.md` = **60**, soit **30 exemples** (seuil 24, soit 12) · les **25 champs obligatoires de `CONFORMITE.md` § 10.1** sont tous présents dans le manifeste, vérifiés un par un · l'interface `StyleEngine` est écrite en signature Python avec son registre `STYLE_ENGINES` · la section « Objections et réponses » existe dans les deux documents.

**Ce que les documents fixent.** Huit principes (fichiers = vérité, étape = fonction pure idempotente avec `.done` et `inputs_hash`, un modèle résident en sous-processus, une vidéo à la fois, graine déterministe, `schema_version`, secrets hors dépôt, SQLite reconstructible) · un DAG de **19 nœuds** avec entrées, sorties, modèle chargé et temps mesuré attendu · la disposition d'un run et ses identifiants · la bibliothèque partagée et ses six règles de réutilisation · les moteurs de style et leurs deux backends · le multi-langues par run enfant · le journal · les règles de mémoire et de disque · **31 contrats de fichier** · **9 fichiers de configuration** · le schéma SQLite · **26 commandes** · les codes de retour, les tentatives et les timeouts.

**Divergences relevées et traitées.**
1. **Le plafond de 6 publications par jour de `CONFORMITE.md` § 2 ne tient pas** pour une vidéo complète : 2 050 unités (insert 1 600 + miniature 50 + sous-titres 400) × 6 = **12 300 contre un quota de 10 000**. `INTERFACES.md` retient **4 par jour**, sur le solde réel de `quota_ledger`. **Reporté au § 1 : Thomas tranche.**
2. **Les noms de tables du premier jet contredisaient ceux que `ROADMAP.md` fixe déjà.** Le schéma entier a été réécrit sur `publications`, `quota_ledger`, `reporting_jobs`, `perf_daily`, `perf_reach`, `v_video_perf`, `channels_watch`, `videos_ext`, `niche_scores`, `jobs`, `secrets/tokens/`, chacun vérifié dans `ROADMAP.md`.
3. **`c2pa_preserved` ne peut pas valoir `true` après un ré-encodage ffmpeg.** Le champ devient une **mesure** et non une déclaration ; le contrôle 14 reste un avertissement. Ce qui est tenu, c'est l'interdiction de retirer volontairement un marquage.
4. **Trois contrats portent des mesures de l'étape 7 devenues des règles** : segments de voix fusionnés à **≥ 15 s** (le creux de WER est entre 5 et 10 s) · **couverture et WER** exigés ensemble, avec seuil par longueur · timeouts calés sur le **pire cas mesuré** (`assets.image` à 900 s pour un pire connu de 621 s).

**Résidus.**
- La divergence n° 1 ci-dessus attend Thomas ; aucune conséquence avant l'étape 23.1.
- **Aucune fuite de langue ou de chaîne entre runs n'a été trouvée, et cela ne prouve rien** : rien n'a tourné. Première vérification réelle à l'**étape 24**.
- Le **pic mémoire du modèle d'embeddings de l'étape 20** n'est pas mesuré ; il est inscrit `a_mesurer` et devra entrer au ledger à son installation.
- `docs/INTERFACES.md` fait **1 022 lignes pour ≈ 450 annoncées** dans la feuille de route. Écart assumé : chaque section vient de la liste imposée par le prompt, et 31 contrats ne tiennent pas en 450 lignes sans en amputer.

---

### Étape 7 — Installer et figer l'environnement

**15/09/2026 · commit `4c4211d` · 3 critères sur 3 · 0 Go de modèle téléchargé.**

**Livrables.** `pyproject.toml` · `uv.lock` (**versionné**) · `factory/__init__.py`, `factory/cli.py`, `factory/doctor.py` · `tests/test_doctor.py` · `docs/INSTALL.md` (198 l.) · `outils/MODELES.md` à jour · `.env.example` complété.

**Critères mesurés.**

| Critère | Mesure |
|---|---|
| `uv run factory doctor` rend 0, chaque brique retenue en PASS | ✅ **13/13 PASS, code 0, 72 s**, reproduit sur deux exécutions complètes |
| `docs/INSTALL.md` permet une installation depuis zéro en moins de 30 min hors téléchargements | ✅ 198 lignes, ~20 min d'installation ; les 21,5 Go de modèles restent à part (2 à 4 h) |
| `git status` propre | ✅ |

**Ce que `doctor` prouve, brique par brique** (M2 16 Go, 15/09/2026) : LLM **20 jetons à 14,2 tok/s** en 7,8 s · TTS **2,2 s d'audio français** en 22,6 s et 2,0 s d'anglais en 19,8 s · ASR **retranscrit « ceci est un test »** en 2,1 s · image **512×512 en 14,3 s**, pic MLX 4,83 Go · profondeur **1,3 s** · Rhubarb 1.14.0 · ffmpeg/ffprobe 8.1.2 · 23,4 Go libres · les 3 caches sous `models/` · **9 modèles « retenu » présents**. Chaque brique lourde tourne dans un sous-processus qui se termine, timeout 180 s : un seul modèle en mémoire à la fois.

**Divergences avec le prompt d'étape.** *(1)* Le prompt listait `mlx-lm` comme runtime LLM ; **le LLM retenu en 5.1 est Qwen3.5-9B GGUF servi par `llama.cpp` (Homebrew)**, qui n'a pas de paquet Python. Rien de superflu n'a été installé. *(2)* `mflux` reste **hors de `.venv`**, en `uv tool` : installé dedans, il casse la pile audio (décision de 5.2). *(3)* Deux contrôles vont plus loin que demandé, parce qu'un succès muet était possible : la carte de profondeur doit avoir du **relief** (amplitude > 32/255), et l'ASR doit **retrouver le mot « test »** dans le WAV que le TTS vient d'écrire.

**Correction apportée le même jour, après relecture de Thomas.** Le contrôle ASR livré en premier jet faisait `"test" in texte.lower()` — une recherche de sous-chaîne. Il rendait **PASS sur « Bourjour, Cissy Edentest. »** : cinq mots faux sur cinq, mais « edentest » contient « test ». Remplacé par une **comparaison au texte attendu** — WER, **seuil explicite de 20 %** (5 mots par phrase : un mot faux toléré, deux non), **mots manqués nommés**, WER affiché dans le tableau. **La sonde anglaise, qui n'existait pas, a été ajoutée** ; le doctor compte 14 contrôles. Test de non-régression sur le cas exact.

**Et ce que la correction a fait apparaître — c'est le point important.** Une fois le WER mesuré au lieu d'être supposé : **la voix Serena échoue le français une fois sur deux.** 16 synthèses de la même phrase, transcrites par parakeet : 7 propres, 2 à 20 %, **7 à 60 % ou plus**. Contre-épreuve à deux ASR (méthode de 5.1) : whisper entend 0/40/60 % sur le même audio — **les deux ASR sont d'accord, donc la cause est la voix, pas l'ASR**. L'anglais est propre : **0 % sur 6 mesures**. Ce n'est **pas un verdict d'écoute** (2 s d'audio, et la session n'entend rien), mais c'est **le risque « ≥ 2 voix par langue » de l'étape 5.1 qui passe de « ni confirmé ni infirmé » à mesuré**. Conséquence de conception : `ASR fr` s'affiche en **WARN** et n'entre pas dans le code de retour — le doctor teste l'environnement, pas la qualité d'une voix — tandis que `ASR en`, mesuré propre, reste un vrai verrou. L'alerte est sous les yeux à chaque session ; l'arbitrage revient à Thomas (§ 1).

**Palier de longueur mesuré le même jour, sur une note de Thomas** (le pipeline synthétise segment par segment, donc dans le régime court). Voix Serena FR, WER parakeet : **~2 s / 5 mots → médiane 20 %** · **~7 s / 19 mots → 63 % et 84 %** · **~11 s / 28 mots → 4 % et 11 %** · **~22 s / 49 mots → 0 %** · **46-62 s → 1,8-4,4 %** (5.1). **La courbe n'est pas monotone : le creux est entre 5 et 10 s, la longueur d'une phrase de script.**

**Et la contre-épreuve à deux ASR renverse la cause selon la longueur — ce qui corrige ce que l'étape 7 avait d'abord conclu.** Sous 3 s, whisper confirme la dégradation (0/40/60 %) : c'est **la voix**. À 7 s, **whisper transcrit à 0 % et détecte « fr » tout seul, tandis que parakeet rend « The sugar disparaît from your alimentation, and your corps reag in three hours »** : c'est **parakeet**, qui traduit et tronque. « La cause est la voix, pas l'ASR » était vrai à 2 s et faux à 7 s. **C'est un deuxième mode de défaillance de parakeet sur le français**, à joindre à l'enquête sur les troncatures avant l'étape 11. **Porté au contrat d'interface de l'étape 8** (`voice/segment_XX.wav`) : longueur minimale de segment, couverture **et** WER contre le texte source, seuil dépendant du nombre de mots. Détail dans `STATE.md` § Bloqué.

**Résidus.** *(1)* Les deux lignes **Qwen3-TTS** passent de « échoue la vitesse » à **« retenu sous réserve »** dans le ledger : elles portent la seule brique TTS du projet et `doctor` les exerce. **Le verdict de vitesse (RTF 3,29) et l'écoute en attente de Thomas sont inchangés** — c'est le statut de ledger qui était faux, pas la mesure. *(2)* Le cumul disque reste à **21,52 Go** pour un plafond de 22 : **0,48 Go de marge**, inchangé. *(3)* `doctor` ne couvre pas les briques non encore installées — **rembg/détourage** (piège de licence `-m birefnet-general` non vérifié depuis 5.2), Revideo et tesseract. À ajouter aux étapes 30.1 et 15.

---

### Étape 6 — Trancher les styles et la réponse à Alek

**Livrables.** `docs/STYLES.md` (452 l.) et `docs/message-alek-whatsapp.txt` (texte brut à coller, mise en forme WhatsApp). 0 Go téléchargé,
rien d'installé. 1 sous-agent contradicteur.

**Critères du « terminé quand », tous tenus.** Matrice de **9 lignes** (les 7 styles
demandés, le réaliste éclaté en « par banques » et « généré », plus le moteur de
cartes) avec chaîne d'outils, qualité mesurée, coût par minute, poids disque, chemin
de preuve, apport du serveur GPU et statut · **« Message à Alek » de 10 lignes** (≤ 20)
· ordre des moteurs fixé · objections du contradicteur traitées.

**Statuts tranchés.** retenu v1 : illustré animé (12.2) et cartes (interne) · retenu
v2 : motion design (30.1), documentaire et réaliste par banques (17), whiteboard
(30.2), avatar 2D (29) · serveur seulement : réaliste généré, et même alors en b-roll
de quelques secondes · **abandonné : « animations poussées »** — aucun outil retenu à
l'étape 4, et la chaîne de référence d'Alek publie 57 vidéos en 5 ans.

**Deux déplacements dans l'ordre des moteurs.** Le motion design remonte de la phase 6
à la phase 2 (seul moteur qui n'achète pas ses visuels à FLUX ; 2,7 min/min projetés
contre 19,7 à 32,8 ; aucune anatomie générée). L'avatar 2D descend en dernier : c'est
le moteur dont le moins de choses ont été vues — **aucun avatar animé n'a jamais été
rendu**, quand le whiteboard a un MP4 noté 4/5.

**Les trois voies de la relecture sont tranchées** (`RESULTATS.md` § 2.12) : la charte
de 12.2 cadre les personnages en buste et privilégie objets et lieux (coût nul) ; la
relecture humaine est **ciblée sur les seuls plans à personnage**, drapeau posé
gratuitement par la liste de plans de 12.1 ; le juge VLM est reporté au serveur.

**Deux erreurs d'arithmétique corrigées dans des livrables antérieurs.** Le « rapport
de 1 à 300 en faveur du 2.5D » (`RESULTATS.md` § 2.5 et `SUIVI.md` § 3) était faux :
le bon rapport est **3,9 par seconde de vidéo, 3 à 5 par minute finie** — le 300
n'apparaît qu'en retirant le coût de génération d'images du seul côté 2.5D. Et
« un neuvième des pixels du 1080p » vaut **un quatorzième** (147 456 contre
2 073 600). Les deux fichiers portent la correction et son motif. **Aucune décision ne
change ; c'est le chiffre qu'on allait montrer au client qui changeait.**

**Divergence assumée avec le prompt de l'étape.** Le prompt demandait de regarder
« au plus 3 échantillons » : 3 ont été ouverts (fond de motion design, image médiane
de la preuve LTX, `plan_08` de la série de cohérence), tous en pleine résolution.

**Ajouts de Thomas après relecture du message (15/09/2026).** La machine actuelle est
nommée dans le message (MacBook Air M2, 16 Go, machine de travail de Thomas) · le
serveur y est présenté comme **un budget sans machine choisie**, avec l'engagement de
chiffrer avant de s'engager (étape 31) et l'arbitrage **débit contre qualité d'image**
posé explicitement · la dérive de personnage est présentée comme se corrigeant
**d'abord au prompt**, les garde-fous passant au second rang. `STYLES.md` § 1.2 et § 5.

**Résidus.** La qualité perçue du documentaire sur banques n'a **aucune preuve** et
ne s'obtient que par une mesure à l'étape 17 (seuil écrit dans `STYLES.md` § 7). Le
motion design n'a aucune séquence rendue au-delà d'un texte sur fond uni. L'avatar 2D
n'a aucun rendu. **Et, hors styles : il n'existe aujourd'hui aucune musique
disponible** — ACE-Step est hors budget disque, l'Audio Library exige un compte de
chaîne (question n° 1 pour Alek). Une vidéo sortirait sans musique de fond.

### Étape 5.2 — Mesurer image, parallaxe, composition et une preuve vidéo IA

**Livrables.** `benchmarks/bench_visuel.py` (300 l.), `bench_visuel.sh`, `timeout.sh`
(macOS n'a pas `timeout(1)`), `benchmarks/videoproof/` (3 scripts), `RESULTATS.md` § 2,
`benchmarks/samples/visuel/` (17 PNG, 3 MP4, 2 JSON de visèmes, 1 SVG),
`outils/revideo_projet/` (configuration Revideo qui fonctionne, 20 Ko),
`results_visuel.jsonl`, `outils/MODELES.md` mis à jour.

**Critères mesurés — 10 sur 10 ; 9 tenus, 1 non tenu** (cohérence sur 8 plans).

| Brique | Seuil | Mesuré | |
|---|---|---|---|
| Image 1280×720 | ≤ 90 s → **≤ 180 s** (réécrit) | **137,0 s** | ✅ |
| Cohérence de style, 8 plans d'une même vidéo | ≥ 4/5 | **non tenue** (mesuré le 15/09) | ❌ |
| Image, pic mémoire | < 13 Go | 11,15 Go (12,37 en 1024²) | ✅ |
| Profondeur | ≤ 5 s | 0,24 s | ✅ |
| Clip parallaxe 5 s 1080p | ≤ 20 s · qualité ≥ 3/5 | 3,7 s · **4/5** | ✅ |
| Rendu Revideo 1080p | ≥ 2 img/s | **98,4 img/s** | ✅ |
| Vectorisation whiteboard | ≤ 10 s · ≤ 800 chemins | 0,03 s · 27 chemins | ✅ |
| Rhubarb sur 60 s d'audio | ≤ 30 s | 6,2 s pour 53 s | ✅ |
| Miniature | ≤ 3 s | 0,20 s | ✅ |
| Preuve vidéo IA | produite ou motif | **produite** — 4,04 s en 438,7 s | ✅ |
| Disque libre en fin d'étape | ≥ 10 Go | **23 Gi** | ✅ |

**Le chiffre à retenir pour l'étape 6.** La vidéo IA générative coûte **108,5 s de
calcul par seconde de vidéo** en 512×288 sur cette machine — une minute de vidéo
demande 1 h 49. Le même plan de 5 s en 2.5D coûte **140,7 s** bout en bout (image
137,0 + profondeur 0,24 + mouvement 3,5). **Rapport de 3,9 en faveur du 2.5D par
seconde de vidéo** (28,1 contre 109,7 s), soit **3 à 5 par minute finie** (19,7 à
32,8 min contre 108,5) — et le 2.5D sort en 1080p quand la vidéo générative sort en
512×288 (**un quatorzième des pixels**) avec des fantômes de filigrane de banque
d'images. *(Corrigé à l'étape 6 : ce paragraphe annonçait « 1 à 300 », faux — le
coût de génération d'images avait disparu du côté 2.5D. `docs/STYLES.md` § 1.1.)*

**Coût mesuré par minute de vidéo produite** (12 plans/min) : documentaire 19,7 min de
machine, photo 27,1, whiteboard 28,1, cartoon 30,7, motion design 32,8. Une vidéo de
10 minutes bout en bout : **3 h 55 à 6 h 00 selon le style**, dont **84 % en génération
d'images**. C'est là, et nulle part ailleurs, que se joue le débit du système.

**Divergences avec ce qu'annonçaient les étapes précédentes.**

1. **Rhubarb n'avait pas besoin d'être recompilé.** L'étape 4 concluait au SIGSEGV et
   à une recompilation arm64 obligatoire. Le binaire x86_64 tourne sous **Rosetta 2**,
   une fois l'attribut de quarantaine retiré. Le repli MFA + OpenFaceFX (~400 Mo) n'est
   pas installé. **Dépendance nouvelle : Rosetta 2 sur toute machine de production.**
2. **La vidéo IA locale n'est pas « non viable », elle est impraticable.** La veille du
   13/09 la donnait impossible sur M2 16 Go. Elle tourne, en 7 min 19 pour 4 s, avec un
   pic de 7,71 Go et 1,52 Go de swap. La nuance compte pour répondre à Alek : ce n'est
   pas un mur technique, c'est un coût.
3. **Playwright pèse 0,21 Go et non 0,35.** `--only-shell` évite les 0,93 Go des trois
   navigateurs.
4. **La consigne « quantifier FLUX localement » tombe.** Elle visait les dépôts 4-bit
   tagués non commerciaux ; `mlx-community/FLUX.2-Klein-4B-4bit` est tagué Apache-2.0
   et pesé à 4,62 Go. C'est lui qui a servi.

**Correction après relecture de Thomas, le 15/09/2026.** Le premier clip de
parallaxe était faux, et aucune mesure du banc ne pouvait le signaler : le temps
(3,5 s), la durée (5,000 s) et le nombre d'images (150) étaient tous les trois
justes. Trois défauts relevés à l'œil — **rôles des couches inversés** (Depth
Anything sort une profondeur inverse : clair = proche ; la tranche sombre, 72,4 %
des pixels, est le fond et c'est elle qui glissait le plus vite), **trous** dus à
des masques binaires mutuellement exclusifs, **contours crénelés** faute de
fondu. Corrigés par ordre rétabli, masques cumulatifs et rampe d'alpha + flou de
3 px ; clip régénéré en 3,7 s. **Un contrôle automatique est entré au banc** :
le clip est rejoué sur fond magenta et les pixels magenta sont comptés — 0 trou
mesuré, et le banc échoue si ce compte n'est pas nul. **La ligne parallaxe de
`RESULTATS.md` reste à « non évalué » jusqu'au regard de Thomas.**

**Trois arbitrages rendus par Thomas le 15/09/2026.** (1) Seuil image réécrit de
90 s à **180 s**, FLUX conservé — avec l'inscription que **84 % du calcul part
dans les images**, que c'est la **première justification chiffrée du serveur
GPU** (étape C2), et que **la réutilisation de bibliothèque (étape 12.2) doit faire
baisser ce coût sans que ce soit encore un fait**. (2) Plafond de cumul disque
relevé de **18 à 22 Go**, le plancher de 8 Go libres restant la seule règle dure.
(3) La parallaxe n'est pas notée tant qu'il ne l'a pas vue.

**Notes de Thomas après visionnage, le 15/09/2026.** Parallaxe corrigée **4/5**
(« propre, plus aucun trou, les plans sont dans le bon sens ») → **Go**, repli
Ken Burns plat non activé. Ken Burns, whiteboard animé et rendu Revideo : **4/5**
chacun. Preuve LTX vue et **gardée pour la démonstration à Alek**. Planche de
cohérence : **4/5**, le visage tient sur les trois graines. **Tous les seuils de
qualité de `SELECTION.md` sont tenus ; aucun repli n'est activé.**

**Une réserve, à traiter à l'étape 12.2 : la tenue du personnage dérive.** Chemise
unie sur les graines 11 et 33, **à carreaux à deux poches à rabat** sur la graine
22 — le mot « flannel » du prompt désigne une matière, pas un motif. Les distances
de hachage le disaient déjà : 8 entre les deux graines « unies », 16 et 20 avec
celle à carreaux. **Invisible entre deux vidéos, visible entre deux plans d'une
même vidéo** — or c'est l'usage visé par le format avatar. Se règle au gabarit de
prompt (motif, couleur, poches, col décrits sans ambiguïté et figés dans la fiche
de personnage), **pas au modèle**. **Domicile : étape 12.2** — moteur « illustré
animé », bibliothèque d'images réutilisables et cohérence entre plans d'une même
vidéo. *La note avait d'abord été portée à l'étape 17, à tort : celle-ci est le
moteur documentaire sur banques libres et ne génère aucun personnage.* Copie
conservée à l'**étape 29** pour la récurrence d'un personnage d'une vidéo à
l'autre. **La cohérence de style sur 8 plans, jamais mesurée, part à 12.2 aussi.**

**Capacité du système — réponse chiffrée à la question n° 7 d'Alek.** Une vidéo de
10 min coûte **3 h 55 à 6 h 00** de machine, **un seul run à la fois**. À raison
d'une vidéo par nuit : **≈ 7 vidéos par semaine**, soit **3 chaînes à 2 vidéos par
semaine** avec une nuit de marge. Quatre chaînes au même rythme dépassent la
capacité. **Ce n'est pas l'API qui limite** : son plafond de 6 uploads/jour vaut
42 vidéos/semaine, six fois plus. Reportée au § 1.

**Précision pour l'étape 6 — ce que le serveur GPU achète, et ce qu'il n'achète
pas.** Il achète de la **vitesse**, et de la **qualité sur la seule brique image** :
le **4B en bf16** au lieu du 4B en 4 bits (le 9B est en licence non commerciale, vérifié le 15/09 : il est hors jeu quelle que soit la machine), davantage d'étapes de débruitage, et
surtout **4 images générées pour n'en garder qu'une** — impossible à 137 s pièce,
cela porterait une vidéo de 10 min à 13 h. Il **n'achète pas** la voix française
(aucun TTS gratuit n'a de voix native FR : c'est un problème de **données**, pas
de calcul), ni la dérive de tenue (**prompt**), ni le photoréalisme comme style
(**nature du média** : 108,5 s de calcul par seconde de vidéo en 512×288, avec des
fantômes de filigrane). **Aucun défaut de qualité de ce projet n'est limité par le
calcul.** Développé dans `benchmarks/RESULTATS.md` § 2.9.

**Test des 8 plans, ajouté le 15/09/2026 à la demande de Thomas — et il échoue.**
L'étape 6 ne pouvait pas le porter : budget disque 0, aucune génération. Un
script, une charte, 8 intentions consécutives, graine = `sha256(video_id, plan)`.

**La session a d'abord conclu 4/5. C'était faux, et Thomas l'a vu.** Sur le
`plan_08` d'une série où le personnage est une femme aux cheveux longs — chignon
au plan 5 — trois défauts **indépendants** : **coupe courte masculine** au crâne,
**chevelure subsistant en mèche détachée** flottant à hauteur d'épaule (17 px de
vide, vérifié au pixel), **pied arrière retourné** — la marche va à droite, la
pointe de la chaussure regarde à gauche, les deux chaussures sont vues sous des
angles incompatibles et l'ombre n'est ancrée sous aucun pied. Second écart : le
`plan_01` est le **seul encadré** des huit.

**Pourquoi la mesure n'a rien vu, et pourquoi la session non plus.** L'intersection
d'histogrammes compare des distributions de couleurs : un personnage qui change de
sexe ne déplace presque aucun pixel d'une classe à l'autre, la palette reste la
charte. Et le jugement « 4/5 » a été porté sur une **planche de contact à 440×248
par vignette**, un huitième des pixels, où une mèche de 17 px est invisible.
**Règle : une planche juge une famille de style et une palette, jamais l'anatomie
ni l'identité.**

**Trois contrôles écrits et exécutés** (`benchmarks/controles_plan.py`), pas
proposés : **cadrage ✅** — désigne exactement `plan_01`, 1 sur 8 ; **palette ✅** ;
**fragments détachés ❌** — n'a pas vu la mèche et a signalé 7 plans sur 8. Cet
échec est de principe : sur ces 8 plans, **3 séparations légitimes sur 13** ont la
même signature géométrique (10-25 px) que la fautive. Distinguer une mèche
détachée par erreur d'un vêtement séparé par dessin suppose de la sémantique.

**Réponse franche à la question posée : non, l'automatisation n'est pas
atteignable ici** pour l'anatomie, les éléments détachés et la dérive d'identité.
Il faudrait un modèle vision-langage ; le LLM retenu est textuel, aucun VLM ne
tient dans 22 Go, une API payante romprait le 0 €. **Donc la brique image impose
une relecture humaine plan par plan — contre la contrainte 3 de `ROADMAP.md`
§ 3.4**, et à 840 plans par semaine. Trois voies portées au § 1, dont la moins
chère : **réduire l'exposition**, les 4 plans sans anatomie humaine étant indemnes.

**Troisième angle mort de la même famille dans cette étape**, après la parallaxe
inversée et la dérive de chemise. Le facteur commun est mesuré, pas supposé :
**les trois défauts étaient structurels ou sémantiques, les trois mesures étaient
des statistiques agrégées.** Une mesure agrégée dit qu'un plan est *dans la
charte* ; elle ne dit jamais qu'il est *juste*.

Coût du test : 21,4 min, médiane 94 s par plan — avec un plan à 621 s, cause non
établie, et un écart non expliqué avec les 137 s du banc principal, que le modèle
de coût conserve par prudence.

**Résidus.**

- **Détourage rembg `birefnet-general` non mesuré** (0,9 Go non téléchargés). La
  miniature testée n'en avait pas besoin. Seuil ≤ 15 s toujours non vérifié → étape 6
  ou 30.1.
- **Cohérence de style sur 8 plans : NON TENUE** (`RESULTATS.md` § 2.11). Trois défauts sur un plan — personnage changé, mèche détachée, pied retourné — **que la métrique employée ne sait pas voir**. **Et l'automatisation n'est pas atteignable** pour cette classe (§ 2.12, trois contrôles exécutés, un échec par principe) : **la brique impose une relecture humaine plan par plan**, contre la contrainte 3 de `ROADMAP.md` § 3.4. **À trancher à l'étape 6.**
- ~~Qualité en mouvement non évaluée~~ → **levé le 15/09/2026**, quatre clips notés 4/5.
- **Le rendu Revideo à 98,4 img/s porte sur une scène de texte sur fond uni.** Une
  scène avec vidéos et images sera plus lente → à remesurer à l'étape 30.1.
- **Plafond de cumul dépassé de 3,52 Go** → § 1.

### Étape 5.1 — Mesurer texte et audio sur le M2

**Livrables.** `benchmarks/bench_audio.py` (308 l.), `bench_audio.sh`, `run_tts_asr.sh`, `complete_niveaux.py`, `recalcule_wer.py`, `RESULTATS.md` (§ 1), `METHODE.md`, `ECOUTE.md`, `MUSIQUE.md`, `results_audio.jsonl`, `samples/audio/` (8 WAV, 4 textes, 16 transcriptions — hors git, 7 Mo). `outils/MODELES.md` et `STATE.md` mis à jour ; `STATE-ARCHIVE.md` créé.

**Critères mesurés — 4 sur 6.**

| Critère de la ROADMAP | Résultat |
|---|---|
| Temps, RTF, pic mémoire, disque par outil | ✅ mesurés pour les 4 outils installés |
| WER pour TTS et ASR | ✅ mesuré, en deux variantes (brut et hors nombres) |
| Un outil « go » par brique | ⚠️ **LLM et ASR oui ; TTS retenu par assouplissement assumé** du seuil de vitesse, faute de repli ; musique non mesurable |
| TTS ≥ 2 voix en FR, EN, ES, IT | ⚠️ 2 voix produites dans les 4 langues et jugées « plutôt bonnes », mais **leur distinguabilité deux à deux n'a pas été vérifiée** |
| Qualité /5 humaine ou « non évaluée » | ✅ écoutée le 15/09 — **jugement global « plutôt bonnes », sans note chiffrée par voix** |
| Disque libre ≥ 12 Go à la fin | ✅ **26 Gi** |

**Chiffres qui comptent.** LLM Qwen3.5-9B Q4_K_M : **14,4 tok/s**, pic 6,96 Go — les deux seuils passent avec 80 % et 42 % de marge, et le repli n'a pas été téléchargé. TTS Qwen3-TTS : **facteur temps réel 3,29 à 3,57** contre ≤ 1,0 exigé, soit ~33 min de calcul par vidéo de 10 min. ASR parakeet : **RTF 0,037**, horodatage au mot natif, WER hors nombres médian 3,39 %.

**Divergences avec l'étape 4.**

1. **Quatre poids annoncés sur quatre étaient sous-évalués**, d'un facteur 1,07 à 4,2. Cause dominante : confusion entre nombre de paramètres et taille de fichier (parakeet « 0,6 Go » pèse 2,3 Go). S'y ajoute un dépôt entier oublié : le tokenizer audio de Qwen3-TTS, 0,66 Go, sans lequel le modèle ne démarre pas. **Conséquence : le budget de 16,47 Go de l'étape 4 n'est pas fiable**, et le plafond de 18 Go ne tiendra pas jusqu'au bout de 5.2 (21,3 Go projetés).
2. **ACE-Step : nom de dépôt faux et poids 4× sous-évalué** (~10,1 Go, non 2,39). La génération musicale locale est définitivement hors budget — ce n'est plus une condition à surveiller.
3. **`SELECTION.md` annonçait mlx-audio pour Qwen3-TTS** ; l'outil officiel est le paquet `qwen-tts` (transformers), et `flash_attention_2` n'existe pas sur Metal.

**Ce qui a été fait autrement que prévu, et pourquoi.**

- **LLM mesuré en premier** au lieu du 3ᵉ rang : c'est lui qui traduit le paragraphe dont le TTS a besoin, et le motif de l'ordre d'origine (économiser le disque) ne tenait pas avec 46 Gi libres.
- **ASR de repli mesuré** bien que le principal n'ait pas échoué. Sans second ASR, un WER de 36 % est indécidable. C'est précisément ce qui a permis d'établir que la voix était bonne et que l'ASR décrochait.
- **TTS sondé dans 3 configurations** sur une phrase courte avant de lancer les 8 synthèses. Le premier jet (`float32`) était le pire des trois : la sonde a coûté 3 minutes et économisé ~55 minutes de calcul sur la mauvaise configuration.

**Résidus.**

- **La cause des troncatures de parakeet (2 fichiers sur 8) est inconnue, et doit être trouvée avant l'étape 11.** Ce qui est établi : la troncature est reproductible (couverture 0,62 et 0,66), l'audio en cause est intact — ses 11 dernières secondes transcrites isolément rendent le texte exact —, et le découpage en fenêtres la corrige sur ces deux fichiers mais en casse d'autres (6 réglages mesurés, aucun bon partout, `fr_Serena` allant de 4,4 % à 51,8 %). Ce qui n'est pas établi : **pourquoi**. Pistes non explorées : décodage TDT s'arrêtant sur un jeton de fin prématuré, longueur d'audio, langue, caractéristiques du locuteur. **Tant que la cause est inconnue, le contournement (vérifier la couverture, basculer sur whisper) est un pansement dont on ignore le taux de fuite.** L'étape 11 produit les sous-titres : elle ne peut pas partir sur une brique dont le mode d'échec n'est pas compris. En parallèle, la contrainte de couverture est à inscrire au contrat d'interface de l'étape 8.
- **La brique musique est suspendue à la question n° 1 d'Alek** (comptes Google et Brand Accounts des chaînes). Le seuil « ≥ 5 pistes distinctes par niche » exige une session YouTube Studio authentifiée, et c'est cette authentification qui fonde la garantie Content ID — la seule raison du choix de l'Audio Library. Automatiser la navigation est exclu (`docs/CONFORMITE.md` § 9). **Aucune mesure de cette brique n'est possible avant que les comptes existent** ; elle n'est donc pas « en retard », elle est bloquée en amont. Reporté à l'étape 14. Pixabay Music, lui, est inventoriable par API et le sera avec le client des banques.
- **Le WER ne peut plus servir de note d'intelligibilité de la voix**, contrairement à ce que prévoyait la ROADMAP. Il mesure la rencontre d'une voix et d'un ASR.


### Étape 4 — Veille et sélection des outils par brique
**15/09/2026 · commit `5b5b97f` · 0 Go de disque (rien installé, rien téléchargé)**

- **Livrables** — `outils/SELECTION.md` (559 l., 12 briques + budget disque + ordre de mesure),
  `outils/LICENCES.md` (230 l., tableau des retenus, éliminés avec clause citée, attributions
  prêtes à l'emploi), `outils/MODELES.md` mis à jour (plan de téléchargement + 6 avertissements).
- **Critères — 4/4, mesurés** : 12 briques avec principal et repli chiffrés (17 sections `##`,
  seuil ≥ 12) · chaque outil avec licence exacte, usage commercial, obligations, URL et date ·
  **0 outil retenu à licence non commerciale** (grep sur les lignes du tableau des retenus) ·
  **somme des principaux 16,47 Go ≤ 18 Go**.
- **Méthode** — 4 sous-agents en vague 1, 1 contradicteur licences en vague 2, puis 1 recherche
  ciblée pour remplacer un repli tombé. Sources primaires exigées : fichier LICENSE brut, fiche
  Hugging Face, CGU officielles. Toute vitesse sans URL de mesure est marquée « à mesurer ».
- **Contradicteur — 3 erreurs bloquantes, 4 corrections, 6 confirmations** sur 7 points
  prioritaires. Traçées au § « Objections du contradicteur » de `SELECTION.md`.
- **Divergences avec la veille du 13/09 (`ROADMAP.md` § 3.5) : 7 points faux ou périmés**,
  corrigés en tête de `SELECTION.md`. Les deux plus lourds : **Qwen3.5-7B n'existe pas**
  (la série est 0,8/2/4/9B) et **Kokoro n'a qu'une seule voix française**, ce qui le disqualifie
  au regard de l'exigence « ≥ 2 voix par langue ».
- **Résidus** — trois pièges de licence doivent être **codés, pas documentés** : forcer
  `-m birefnet-general` dans rembg (le défaut `bria-rmbg` exige un contrat payant), quantifier
  FLUX.2-klein-4B localement (les dépôts 4-bit tiers sont non commerciaux), et poser
  `DISABLE_TELEMETRY=true` pour Revideo. Aucune vitesse n'est acquise : les seuils de décision
  de 5.1 et 5.2 sont dans `SELECTION.md` § Ordre de mesure.

### Étape 3 — Référentiel exploitable, sujets porteurs, hooks, trajectoires
**15/09/2026 · commit `f763788` · 0 Go de disque**

- **Livrables** — `registre/REFERENTIEL.json` (136 Ko, 8 niches, le fichier que le code lira),
  `registre/REFERENTIEL.md` (134 l., lecture humaine + section Objections),
  `registre/TRAJECTOIRES.md` (94 l., 12 règles T1–T12).
- **Critères — 6/6, mesurés** : JSON valide · 8 niches (≥ 6) avec tous les champs du schéma ·
  15 sujets porteurs par niche (≥ 10) · 12 types de hook avec exemples (≥ 8) · 12 règles
  chiffrées dans `TRAJECTOIRES.md` (≥ 8) · 20 objections du contradicteur traitées.
- **Matière mesurée** — 21 919 vidéos, 349 transcriptions classées, 192 miniatures regardées
  (par planches-contacts ffmpeg, 42 lectures d'image au lieu de 200), 310 transcriptions
  remesurées pour le débit de parole, 30 chaînes du tableau P9 pour le rythme de coupe.
- **Deux décisions qui changent les cibles** — (1) le rythme de coupe lu par le code est
  `cible_montage`, la médiane de niche débarrassée des chaînes de plateau et d'actualité
  (true_crime : 21,8 → 15,7 s ; home_hacks : 8,6 → 6,9 s) ; (2) le débit de parole est mesuré
  sur la transcription entière et non sur les 60 premières secondes, qui contiennent le
  générique — sans cette correction les scripts `histoire_doc` sortaient 40 % trop courts.
- **Divergences et résidus** — 3 niches sur 8 n'ont **aucune** mesure de rythme de coupe et
  tournent sur un repli de 7,8 s explicitement marqué « pas une cible » ; `ruptures_s` et
  `densite_faits_par_minute` restent vides (non calculables sur des métadonnées) ; l'échantillon
  n'a **pas de groupe témoin** — 188 miniatures sur 192 sont déjà des vidéos à succès, donc les
  « motifs gagnants » décrivent les meilleures vidéos, pas ce qui les distingue des autres.
- **Le doublon Saving Savers est tranché** (divergence n° 12 de l'étape 2) : étiquette
  `home_hacks`, 3,8 s/plan, sur la preuve des mots-clés de ses titres.

### Étape 1 — Ossature et cadre de conformité
**14/09/2026 · ~30 min · commit `2a28e00` · arbre propre**

- **Livrables** — 21 dossiers, `.gitignore` (26 l.), `.env.example` (17 l.), `CLAUDE.md` (17 l.),
  `STATE.md` (65 l.), `outils/MODELES.md` (15 l.), `docs/CONFORMITE.md` (379 l., 11 sections
  + Sources + Décisions, 68 lignes sourcées). 0 Go de disque consommé.
- **Critères — 5/5, vérifiés indépendamment** : `CLAUDE.md` 17 l. (≤ 40) · 13 sections dans
  `CONFORMITE.md` (≥ 12) · 68 occurrences de `http` (≥ 15) · 1 commit · 21/21 dossiers.
- **Les 3 règles les plus contraignantes** — (1) la case « promotion payante » n'existe pas en
  écriture dans l'API : toute vidéo affiliée garde un geste manuel en Studio, **même après
  l'audit** ; (2) upload forcé en privé tant que le projet API n'est pas audité, délai en
  semaines à mois → l'audit de l'étape 14 est le chemin critique ; (3) divulgation à **quatre**
  déclencheurs distincts, jamais fusionnables.
- **Divergences** — 10 écarts avec la veille de la ROADMAP, consignés dans `STATE.md` : quota
  réel ~6 uploads/jour (et non 100), accès étendu YPP exigeant aussi 3 000 h de visionnage,
  rétention des données API plafonnée à 30 jours, « étiquetage automatique par YouTube depuis
  05/2026 » **non confirmé** sur source officielle.
- **Questions ouvertes** — 8 (voir § 1).
- **Résidus** — `.playwright-mcp/` (112 Ko, ignoré par git, non supprimé).

### Étape 2 — Collecter les données du registre via l'API officielle
**✅ terminée le 14/09/2026** — commit `a0a8e76`.

**Livrables.** `registre/chaines.csv` (74 chaînes) · `collecte.py` · `index.py` ·
`data/<slug>/channel.json` + `videos.json` (74 dossiers) · `data/INDEX.md` (138 l.) ·
`collecte.log` · miniatures et transcriptions hors git.

**Critères : 5 sur 5.**

| Critère | Cible | Mesuré |
|---|---|---|
| Lignes de `chaines.csv` | ≥ 60 | **74** ✅ |
| Dossiers avec `channel.json` + `videos.json` | ≥ 55 | **74** ✅ |
| `INDEX.md` complet par chaîne | oui | **oui** ✅ (vidéos, abonnés, durée médiane, cadence, vues médianes, ratio top1/médiane) |
| Quota consommé | < 8 000 unités | **943** ✅ |
| Fichiers de transcription | ≥ 100 **ou** rapport d'échec | **349** ✅ — 74 chaînes, 11 niches |

**Divergences avec le registre de Sofiane.** Les chiffres d'abonnés du PDF sont périmés
(Library of Thoth : « ~29K » au PDF, **311 000** mesurés). `Saving Savers` y figure deux fois
avec deux médianes de rythme contradictoires (6,9 et 3,8 s/plan). `Tolga Örnek` est dans le
PDF mais absent du tableau des 29 chaînes de la roadmap — il y en a donc 30. Aucune chaîne
non résolue : les 74 URL `/channel/UC…` du PDF sont toutes valides.

**Transcriptions — comment elles ont fini par passer.** Six passes le 14/09/2026, 0 unité de
quota. La première, à 3–6 s depuis l'IP fixe, a valu un `IpBlocked` au bout d'une vingtaine de
récupérations : 19 fichiers. Les suivantes depuis le partage de connexion 4G de Thomas
(IP mobile personnelle, **sans proxy ni VPN**) à 25–45 s. Le blocage s'est reproduit une seule
fois, puis plus jamais : **la cadence comptait autant que l'adresse** — à refaire à l'identique
à l'étape 16. Les quatre arrêts suivants venaient de l'outil, pas de YouTube, et sont corrigés :
les erreurs sont classées par type (blocage / fait sur la vidéo / panne réseau) au lieu d'une
liste de noms toujours incomplète, et la session HTTP impose 30 s — sans quoi une 4G tombée
fige la passe indéfiniment, ce qui est arrivé une fois pendant 78 minutes.

**Résidus.** 1) **2 transcriptions manquantes** sur Spiritual Dive (délai réseau), et 16 vidéos
qui n'en auront jamais — interdites aux mineurs, sous-titres coupés ou injouables : marquées
`.absent`, jamais retentées. 2) **29 chaînes tronquées à 500 vidéos** (Fox News en déclare
144 176) : leurs agrégats décrivent l'activité récente, pas un historique. 3) **Purge du cache
API au 14/10/2026** : clause contractuelle, pas une optimisation de disque.
