# SUIVI — tableau de bord humain

Ce fichier est pour **Thomas**. Les sessions ne le lisent pas pour travailler : elles
l'alimentent en fin d'étape (règle 14 de `CLAUDE.md`). `STATE.md` est la mémoire des
sessions ; `SUIVI.md` est ton tableau de bord.

Dernière mise à jour : **24/09/2026** (étape 31, roadmap terminée).

---

## 1. Ce que tu dois faire, toi

### Présence requise — tu dois être au clavier pendant la session

| Quand | Action | Durée | Statut |
|---|---|---|---|
| ⏰ **Ajouté le 24/09/2026 par l'étape 31 — 20 min** | **Faire lire `docs/EXPLOITATION.md` à Sofiane ou Alek, pour de vrai, sur deux scénarios** : programmer une vidéo dans Studio (§ 6) et ajouter une chaîne (§ 10.1). Le test à l'aveugle a fini à **4/6** : ce sont les deux scénarios corrigés sans être retestés. Noter chaque question posée. | 20 min | ⬜ |
| ⏰ **Ajouté le 24/09/2026 par l'étape 31 — avant toute dépense** | **Faire valider par Alek le déclencheur serveur** de `docs/SCALE.md` § 2 (audit obtenu + sauvegarde hors machine vérifiée + file ≥ 2 × capacité trois semaines de suite), et lui demander s'il veut investir avant revenu. Aujourd'hui **1 critère sur 7** : aucune dépense justifiée. Lui transmettre aussi les 9 questions ouvertes de `STATE.md` § « Roadmap terminée ». **Qui : Alek.** | 10 min | ⬜ |
| ⏰ **Ajouté le 24/09/2026 par l'étape 31** | **Disque : 24 → 16 Gi pendant la session sans rien télécharger** ; instantanés de mise à jour macOS présents (`tmutil listlocalsnapshots /`). Appliquer ou reporter la mise à jour **avant** la première nuit de production (déjà demandé à l'étape 27). | 5 min | ⬜ |
| ⏰ **Ajouté le 24/09/2026 par l'étape 28 — 10 min, avant le 29/09** | **Ouvrir le tableau de bord et faire la prochaine relecture avec.** `uv run factory dashboard` ouvre http://localhost:8501. Page Relecture : choisir son nom, lire, Approuver / Rejeter (motif) / Éditer. Dire ce qui gêne. Décider si Alek et Sofiane l'utilisent tel quel, et si on le laisse toujours ouvert (`factory dashboard --agent`). **Qui : Thomas, puis Alek et Sofiane.** | 10 min | ⬜ |
| ⏰ **Ajouté le 20/09/2026 par l'étape 19 — à trancher avant l'étape 21** | **Deux niches sont juridiquement fermées, il faut un avis écrit ou un renoncement.** `niche_monetisable_paris_sportifs` et `marches_predictifs` sont marquées ⛔ dans `reports/niches.md`. Motif : **loi 2023-451 art. 4 VI** — un influenceur ne peut promouvoir aucun abonnement à des conseils ou pronostics sportifs, ce qui est le modèle même de ces niches ; sanction art. 4 IX : **2 ans et 300 000 €**. Le critère « public en France » de l'art. 9 ne vise que les personnes non établies dans l'UE : **produire en anglais n'exonère pas un éditeur français**. À cela s'ajoute la restriction d'âge YouTube sur les jeux d'argent (`answer/9229611`), qui vaut « limited or no ads ». Le statut propre des marchés événementiels (Kalshi, Polymarket) n'est tranché par aucune source officielle consultable. **Rien ne sera produit dans ces deux niches sans un avis juridique écrit.** | avis d'un avocat | ⛔ **ouvert — Alek** |
| ⏰ **Ajouté le 20/09/2026 par l'étape 19 — 30 secondes, à faire avant la prochaine collecte de demande** | **Renseigner `FACTORY_CONTACT` dans `.env`.** La variable existe mais elle est **vide**. La politique Wikimedia exige un contact joignable dans le User-Agent ; sans lui la limite de débit tombe de **200 à 10 requêtes par minute**. Mesuré le 20/09 : la première exécution a mis **256 s** pour 85 articles, à coups de 429, contre **4,1 s** une fois le cache chaud. Une adresse e-mail ou une URL de contact suffit ; `.env` est ignoré par git, rien ne part au dépôt. La session ne l'a pas renseignée d'elle-même : **cette adresse part à Wikimedia à chaque appel, c'est ton identité, pas la sienne.** | 30 s | ⛔ **ouvert — Thomas** |
| ⏰ **Ajouté le 19/09/2026 par l'étape 30.2 — à faire avant l'étape 31** | **Lancer le run complet en whiteboard, et regarder le lot.** Le moteur est livré et mesuré, mais **aucune vidéo entière n'a été produite dans ce style** : le run s'est arrêté à `research` (« 1 source obtenue, 3 exigées »), et la reprise a été écartée parce que la machine était sous le plancher de 8 Go. **Elle est depuis remontée à 10-11 Go.** La commande, quand la machine est libre et qu'aucune autre session ne travaille (≈ 2 h 30, dont 2 h de génération d'images) :<br>`uv run factory run --channel bms-science-en --style whiteboard --topic "<un sujet dont la recherche trouve 3 sources>"`<br>Puis `uv run factory qc --run <id>`. **En attendant, 3 minutes de visionnage** : `workspace/demos/a-regarder/whiteboard/lot_30_plans.mp4` (30 plans, 2,80 min, **sans voix**) — dis-moi si le tracé et la main tiennent **en mouvement**, c'est la seule chose que la session ne peut pas juger. | ~10 min | ⏰ **à faire** |
| ⏰ **Ajouté le 19/09/2026 par l'étape 30.1 — à faire avant l'étape 30.2** | **Regarder les cinq extraits de motion design et dire si on y est.** `workspace/demos/a-regarder/` — **3 minutes en tout**, pas une vidéo de dix minutes. Les deux premiers sont des extraits du **vrai run**, voix comprise ; les trois autres montrent le vocabulaire scène par scène. Ce qui a changé depuis ton retour : **1 plan de texte sur 12 au lieu de 51 %**, des personnages qui parlent et réagissent, des schémas qui se construisent, une caméra qui ne s'arrête jamais. **Ce que la session ne peut pas juger, c'est le mouvement** : elle n'a vu que des images extraites. Dis-moi ce qui manque encore, et sur quel extrait. | ~5 min | ⏰ **à faire** |
| ⏰ **Dû par l'étape 14, non fait — c'est le chemin critique du projet** | **Ouvrir le canal officiel : ~30 min au navigateur, en une seule séance.** Le code de l'étape 14 est écrit et testé (234 tests verts) ; **rien de ce qui manque n'est du code.** Dans l'ordre : **(1)** console GCP, projet `bms-factory` → activer *YouTube Analytics API* et *YouTube Reporting API* → écran de consentement **Externe**, nom « BMS Factory », statut **« En production »** (⚠️ en « Testing » les jetons **expirent sous 7 jours**, ce qui rend le daemon de la phase 4 impossible) → Identifiants → client OAuth **« Application de bureau »** → déposer le JSON dans `secrets/client_secret.json` (hors git, déjà couvert par `.gitignore`). **(2)** Publier `docs/PRIVACY.md` gratuitement (Google Sites ou GitHub Pages) et reporter l'URL aux **deux** emplacements `«URL-PUBLIQUE»` du fichier **et** dans l'écran de consentement. ⚠️ *Le fichier attend aussi la raison sociale de BMS — question n° 2 à Alek, toujours ⬜ : une politique de confidentialité sans opérateur nommé est un vice de forme dans un dossier d'audit.* **(3)** `uv run factory publish auth --channel bms-test`, se connecter avec le compte de la chaîne de test, vérifier que `channels.list` affiche bien la chaîne. **(4)** `uv run factory publish upload --run <id> --channel bms-test` — ⚠️ **l'étape 14 exige un run EN et le seul run exporté est FR** : soit tu reprends le run EN (ligne ci-dessous), soit tu lèves la règle pour ce seul upload de test, comme tu l'as fait pour le jalon de 13.2. **(5)** Soumettre le formulaire d'audit : tout le texte est prêt à coller dans `docs/AUDIT-API.md`, il te reste 4 valeurs à remplir (contact, URL de la politique, numéro de projet GCP, compte de démonstration) et une vidéo d'écran de 60 s à enregistrer (scénario écrit au même endroit). **Pourquoi ça presse** : l'audit prend **des semaines à des mois**, et tant qu'il n'est pas passé **toute vidéo publiée par l'API reste privée**. Lancer l'horloge maintenant la fait tourner pendant les phases 2 et 3 — c'est la raison même pour laquelle l'étape est placée ici. **À trancher avant le premier upload** : `virtual_images_mention` (§ « Décisions techniques en attente ») — sinon la première vidéo part avec des libellés faux. | ~30 min | ⬜ **à toi** |
| ⏰ **Ajouté le 23/09/2026 par l'étape 25 — même geste que la ligne ci-dessus** | **L'étape 25 tourne à vide tant que le canal n'est pas ouvert.** `factory analytics pull` passe chaque matin à 07:05 et s'inscrit `skipped`. Dès le jeton posé : `factory publish reporting-jobs --channel <id>` **avant** le premier upload (sinon impressions et CTR perdus), puis rien à faire — l'agent tire seul. Premier rapport reach 48 h après. | 0 min de plus | ⬜ |
| ⏰ **Ajouté le 23/09/2026 par l'étape 26 — rien à faire, à savoir** | **L'apprentissage est en place et gelé.** `factory learn` passe chaque lundi à 07:15 (agent `com.bms.factory.learn`, 1ᵉʳ passage le 28/09). Aucun poids n'agira avant **30 vidéos à J+7 et 3 chaînes à ≥ 5 vidéos** : au rythme mesuré (≈ 7 vidéos/semaine), pas avant **~6 semaines après la première publication**. Le rapport hebdomadaire est `reports/learn_<date>.md`. Deux corrections de la vue `v_video_perf` restent à faire (J0 en UTC, `LIKE` ambigu) avant de dégeler les créneaux. | 0 min | ⬜ |
| ⏰ **Dû avant toute reprise de l'étape 17 — sinon la reprise sera tuée comme celle-ci.** | **Décider qui tient la machine pendant un run, et le faire tenir.** Le 19/09 à 11h28, le rendu du run documentaire a reçu un **SIGTERM** après 69,6 min de calcul : code −15, « aucune sortie ». Ce n'est ni la mémoire ni le disque (aucun `jetsam` au journal noyau). Au même moment, **une seconde session menait une production complète sur le même arbre** (`bms-science-en-20260919-mtn7`, manifeste à 12h12). Deux runs simultanés violent la **règle 4** — et c'est **l'incident du 17/09 à l'identique**, où trois moteurs ont tourné sur le même run. `pkill -f "factory.cli run"` est le geste que n'importe quelle session fait pour nettoyer un processus qu'elle croit orphelin ; il tue celui de l'autre. **Trois façons d'en sortir, à toi de choisir** : *(1)* une seule session à la fois sur ce dépôt — le plus simple, gratuit ; *(2)* un verrou de run dans `factory` (un fichier `workspace/.run.lock` avec le PID, refus de démarrer si vivant) — ~20 lignes, mais ça ne protège pas d'un `pkill` ; *(3)* un arbre de travail git par session (`git worktree`), qui règle les collisions de fichiers mais **pas** la concurrence CPU ni le plancher disque. ⚠️ **Le plancher de 8 Go est franchi** : 7,7 Gio libres, dont **8,6 Go de swap système** et 550 Mo appartenant au run de l'autre session. **Rien n'a été purgé** — la règle est de n'effacer que ce que tu as nommé. | ~5 min de décision | ⬜ **à toi** |
| ⏰ **Dû par l'étape 17, non fait — le style documentaire n'est pas publiable sans ça.** | **Créer les deux clés de banque vidéo : ~6 min, gratuit, sans carte bancaire.** **(1) Pexels** — compte sur `pexels.com` (email + mot de passe, aucune carte), puis `pexels.com/api/new/` → « Your API Key » s'affiche **immédiatement** ; coller dans `.env` sous `PEXELS_KEY=…`. Quota : **200 requêtes/heure, 20 000/mois**. **(2) Pixabay** — compte sur `pixabay.com`, puis ouvrir `pixabay.com/api/docs/` **en étant connecté** : la clé est affichée dans les exemples de la page ; coller sous `PIXABAY_KEY=…`. Quota : **100 requêtes/60 s**. Openverse, Internet Archive et la NASA répondent **sans clé** — rien à faire pour eux. Aucune ligne de code ne change le jour où les clés arrivent : `factory/assets/stock.py` les lit dans l'environnement et remet Pexels et Pixabay en tête de chaîne tout seul (test `test_avec_une_cle_video_l_ordre_nominal_est_respecte`). ⚠️ **Pourquoi ça compte plus qu'un confort** : sans elles, la seule banque qui réponde presque toujours est Openverse, **qui n'indexe que des images**. Le run du 18/09 est donc un diaporama de photographies animées — et `docs/CONFORMITE.md` § 8 nomme exactement cela : *« un diaporama de banque d'images avec voix off descriptive tombe simultanément sous “contenu réutilisé” et sous “contenu inauthentique” »*, donc **inéligible à la monétisation**. Le moteur, lui, est livré et mesuré. | ~6 min | ⬜ **à toi** |
| ~~Dû par l'étape 13.2~~ | ~~Dicter 3 défauts de `final.mp4`.~~ | — | ✅ **fait le 18/09/2026, par la session, sur ta demande** (« fais ce que je devrais faire moi ») — **`docs/DEFAUTS.md`**. Trois défauts établis **sur mesure, pas sur impression** : *(1)* **36 images distinctes en 12 minutes, l'une servie 22 fois**, 71,0 % des plans montrant une image déjà vue — **deux bugs de `shotlist.py` trouvés et corrigés**, la variété était écrite dans le découpage et n'atteignait jamais l'image ; *(2)* **la narration ne respire jamais** — 90,1 % de parole, **0 silence ≥ 0,4 s**, LRA **3,3 LU** (le niveau, le débit et la durée sont conformes : c'est le relief qui manque) ; *(3)* **les images n'illustrent pas le sujet** — 32 % de la vidéo sur une seule intention abstraite, 33 des 67 intentions ouvrant par « Schéma ». ⚠️ **Ce document n'est pas ton verdict** : quatre questions restent sans jugement (tient-elle l'attention · la voix sur 12 min · le mouvement Ken Burns · la miniature), elles sont listées au § 4. |
| ~~Avant l'étape 15~~ | ~~Dire si le deuxième run doit être refait.~~ | — | ✅ **relancé le 18/09/2026 par la session, sur ta demande.** Reprise de `bms-science-en-20260917-avwf` à l'étape `render`, un seul moteur, journal dans `workspace/logs/reprise-en-20260918.log`. ⚠️ **Deux choses trouvées au lancement.** *(a)* La commande inscrite ici le 17/09 (`factory run --channel bms-science-en --from render`) était **fausse** : `--channel` **crée un run neuf** et aurait jeté l'heure et demie déjà payée en research, script, voix et sous-titres. La reprise, c'est **`--run <id>`**. *(b)* Le run que tu croyais avoir arrêté le 17/09 **n'avait jamais été tué** : il dormait depuis 17 h et s'est réveillé au lancement — **trois moteurs ont tourné en même temps sur le même run**, dont deux généraient la même image avec la même graine. Tout arrêté, bibliothèque vérifiée (160 images, **0 corrompue**, chacune avec son `licence.json`), un seul moteur relancé. **Le run EN a été découpé avec le code d'avant correction** : sa variété d'images sera aussi pauvre que celle du run FR. |
| ~~Étape 2, au démarrage~~ | ~~Créer le projet Google Cloud « bms-factory »…~~ | ~10 min | ✅ fait 14/09/2026 — projet `bms-factory`, clé restreinte à *YouTube Data API v3*, dans `.env` |
| ~~Avant l'étape 3~~ | ~~Relancer la passe de transcriptions~~ | — | ✅ fait 14/09/2026 — 349 transcriptions, 74 chaînes, 11 niches |
| ~~Avant l'étape 5.2~~ | ~~Écouter les 8 échantillons de voix~~ | — | ✅ fait 15/09/2026 — « les voix sont plutôt bonnes », **sans note chiffrée**. La voix FR n'est pas disqualifiante : pas d'arbitrage à remonter à Alek. Qwen3-TTS conservé **par assouplissement assumé du seuil de vitesse** |
| ~~Avant l'étape 5.2~~ | ~~Trancher le disque~~ | — | ✅ fait 15/09/2026 — **rien à purger**, la route MLX 4-bit supprime le pic transitoire. `faster-whisper-large-v3` conservé |
| ⏰ **En retard — l'étape 7 est close sans cette décision** (attendue avant l'étape 7) | **Lire `docs/STYLES.md` § 9 et décider de l'envoi du message à Alek.** 🔁 **RÉÉCRIT le 18/09/2026 — il n'était plus envoyable.** Trois affirmations étaient devenues fausses depuis le 15/09 : *(a)* « deux styles sont déjà validés (illustration animée, whiteboard) » — **aucun des deux ne l'est**, l'illustration animée a été rejetée en parallaxe puis jugée « le thème le moins intéressant » et porte trois défauts mesurés, le whiteboard n'a jamais été vu en vidéo (sa note vient du banc de l'étape 5.2, qui portait le défaut `-loop 1`) ; *(b)* « prochain objectif, une vidéo de démo complète » — **elle est faite** depuis le 17/09 ; *(c)* « 3 à 7 vidéos par semaine » — la seule mesure de bout en bout donne 2 h 23, et la correction du 18/09 la porte à ≈ 3 h 15, donc **3 à 5, pas 7**. Le texte dit maintenant l'état réel et donne les trois défauts à Alek. Détail des corrections : **`STYLES.md` § 9.3**. Les chiffres vérifiés au § 9.2 sont conservés mot pour mot. Version **WhatsApp**, 19 lignes, prête à coller — texte brut dans `docs/message-alek-whatsapp.txt`. **Vérifié chiffre par chiffre contre les sources le 15/09/2026** (sous-agent) : 11 chiffres tiennent, 6 formulations corrigées, 3 manques comblés — détail au § 9.2 de `STYLES.md`. Le texte est prêt à envoyer tel quel ; il annonce l'abandon des « animations poussées », le refus du photoréalisme généré, la correction de la dérive de personnage par le prompt (avec relecture humaine des plans à personnage en garde-fou), un plafond de ~7 vidéos/semaine **sur ton MacBook Air M2 16 Go nommément**, le fait que **la machine du serveur n'est pas encore choisie** — seulement son budget — et **le prochain objectif : la vidéo de démonstration complète de l'étape 13.2**. Il se termine par **deux demandes à Alek** (raison sociale/SIREN/adresse, et comptes Google), qui sont les questions n° 2 et n° 1 ci-dessous : si tu préfères les poser à part, coupe la dernière phrase. Rien n'y est promis qui ne soit pas dans la matrice du § 1. | ~10 min de lecture | ⬜ **à toi** |
| ⏰ **En retard — l'étape 11 est close sans cette décision** (attendue avant l'étape 11) | **Trancher Qwen3-TTS, après mesure de Kokoro EN.** **Alek a tranché l'anglais le 15/09/2026** : la prémisse qui gardait Qwen3-TTS — *« faute de repli à deux voix »* — **n'était vraie qu'en français**. En anglais, `SELECTION.md` § 2 désigne un repli : **Kokoro-82M, 0,33 Go contre 4,52**, rapide, catalogue fourni. **La session mesurera d'abord** (après l'étape 8) : vitesse, WER par palier 2/7/11/22 s, timbres réellement distincts. **Ton arbitrage vient ensuite** : Qwen3-TTS échoue déjà le seuil de vitesse (RTF 3,29, ~33 min par vidéo de 10 min) et sa purge rend **4,52 Go** là où il reste **0,48 Go de marge**. **À écouter d'ici là** : `workspace/logs/ladder_*.wav` (2 s, 7 s, 11 s, 22 s). | ~20 min | ⬜ **à toi** — extraits de 30 s prêts : `workspace/logs/ecoute11/voix_fr.wav` et `voix_en.wav` **L'étape 11 a tourné avec Qwen3-TTS et l'a mesuré en production : facteur temps réel 3,33 (FR) et 3,21 (EN), soit 2 451 s et 2 135 s de calcul par vidéo — le seuil de `SELECTION.md` § 2 (≤ 1,0) reste échoué d'un facteur 3,3. Les deux `voice.wav` sont aux normes YouTube, mais personne ne les a écoutés.** |
| ~~Avant l'étape 13 (montage et export)~~ | ~~Trancher le remplacement de ffmpeg~~ | — | ✅ **sans objet — vérifié le 16/09/2026, la question était mal posée.** Le blocage supposait que `final.mp4` devait **incruster** `subtitles.ass`. **Les quatre chaînes ont `charte.subtitles.burn_in: false` et `youtube.captions_upload: true`** : la route de production est le **mux** en piste séparée, pas l'incrustation — et l'objectif de l'étape 13.1 écrit lui-même « incruster **ou** muxer ». Mesuré sur la build Homebrew 8.1.2_1 en place : encodeurs `mov_text`, `srt`, `subrip`, `webvtt` présents ; mux réel d'un extrait de 10 s avec `subtitles.srt` → **exit 0, piste `mov_text` confirmée par ffprobe**. **Rien à installer, ni build statique ni recompilation ; les ~80 Mo et le poste de maintenance sont économisés.** `libass` ne redevient requis que le jour où une chaîne passe `burn_in: true` — à traiter alors, pas avant. **Résidu tranché le 16/09/2026 en session 13.1** : le « Terminé quand » exigeait « sous-titres visibles sur une image extraite ». `ROADMAP.md` § 13.1 est **amendé** — le critère devient conditionnel à `charte.subtitles.burn_in` : piste `mov_text` présente, codée et étiquetée de la langue quand il est faux (la route des quatre chaînes), image extraite quand il est vrai. Vérifié sur `final.mp4` : `mov_text (fra)`, 337 cues. `assemble` **échoue explicitement** si une charte passe `burn_in: true` sur cette machine, au lieu de retomber en silence sur le mux. *(Recommandation initiale du 16/09 — build statique arm64 — retirée : elle avait été formulée sans lire la charte.)* |
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

**(a) ✅ Noté par Thomas le 16/09/2026, sur les deuxièmes versions : « jusqu'à présent
y'a que le B qui est intéressant ».** Le seuil « vue et notée ≥ 3/5 » de `docs/STYLES.md` § 7
est donc **tenu par le schéma animé seul**. A et C ont été réécrits entièrement après le
premier verdict et **ne tiennent toujours pas** — deux exécutions distinctes, même résultat :
ce n'est plus un défaut d'exécution, c'est le traitement qui ne porte pas. **Aucun troisième
essai n'est lancé sur A ni sur C sans que tu le demandes.**

**Motif nommé pour C** (Thomas, 16/09) : *« c'est pas cohérent le visuel, des images qui se
découpent… vraiment pas très cohérent visuellement »*. La v2 traitait l'image **comme
matière** — bandes verticales, médaillon, grille de six vignettes, fentes horizontales,
spot circulaire, split — six dispositifs de découpe en 32 s. **Le découpage lui-même est le
défaut** : il ne fait pas langage, il fait accident, et il détruit le sujet de l'image sans
produire de composition. C'est cohérent avec la mesure déjà écrite au § 5 de `RESULTATS.md` :
les 83 PNG ont été générés pour être **le sujet centré d'un plan** (`framing.subject_scale`),
pas la matière d'une composition. **Conclusion à porter à l'étape 30.1 : ces images ne se
découpent pas. Si on les réemploie, c'est entières.**

**Motif nommé pour A** (Thomas, 16/09) : *« y'a trop trop de texte pour presque aucune image,
aucune animation, que du texte quasiment »*. **A est exactement cela par construction** —
typographie cinétique pure, zéro image, zéro forme figurative. Le verdict ne porte donc pas
sur l'exécution mais **sur la prémisse** : une troisième version serait encore du texte.
**La typographie cinétique est écartée comme substance d'un plan ; elle ne peut revenir qu'en
ponctuation à l'intérieur d'une séquence construite** (un mot qui tombe sur un temps), jamais
comme le fond du propos.

**Le constat qui unifie les trois verdicts, et qui est la vraie sortie de cette preuve.**
A anime en permanence — chaque mot bouge, la caméra bouge, les transitions changent — et
Thomas lit « aucune animation ». C déplace des fragments d'image et Thomas lit « pas
cohérent ». B construit, et Thomas le retient. **Ce qui est perçu comme animation n'est pas le
déplacement, c'est la construction et la transformation.** C'est mot pour mot le reproche
fait aux 127 plans de l'étape 12.2 — « des images fixes avec un effet de glissement » —
appliqué cette fois à du texte et à des fragments. **Critère unique à porter à l'étape 30.1 :
il faut qu'il se passe quelque chose à l'écran, pas que quelque chose s'y déplace.**

**La conséquence est lourde et elle est à ton arbitrage.** Le seul traitement retenu est
**celui qui coûte le plus cher à écrire et qui s'automatise le moins**. A et C se rejouent
sur n'importe quel script sans être réécrits ; B non : ses **43 repères temporels, dont 23
calés exactement sur un mot**, ont été écrits à la main, et sa géométrie est spécifique au
saccharose et à l'insuline — **371 lignes pour 32 secondes**, soit de l'ordre de **800 repères
pour une vidéo de 12 minutes**, que personne n'écrira. Deux choses en découlent :

- **Le motif de la remontée en phase 2 (§ 6 de `STYLES.md`) reposait sur le coût de calcul**
  — « le seul moteur qui n'achète pas ses visuels à FLUX », 2,7 min/min. **Cet argument tient,
  et il tient pour B :** les trois séquences génèrent zéro image, et B est la plus rapide des
  trois — **0,22 min de calcul par minute de vidéo, 134,3 img/s**, contre 13,6 min/min mesurés
  sur le run complet de 12.2. **Ce qui manque à l'argument, c'est l'autre coût :** l'écriture
  de la chorégraphie, **jamais chiffrée**, et qui ne se paie pas en calcul mais en heures.
  La remontée en phase 2 n'est pas invalidée — **elle est incomplète** : à toi de dire si elle
  tient une fois ce second coût mis en face.
- **Le § 9 (message à Alek) promet un style, pas sa fabrication.** Le style est démontré,
  **la fabrication automatique ne l'est pas.** Si le message part tel quel, il promet ce qui
  est prouvé, et rien de plus.

**Le prochain essai utile n'est pas une quatrième esthétique : c'est de prendre un autre sujet
et de voir ce qui reste de B sans réécrire les 43 repères.** Trois routes existent, aucune
n'est mesurée (gabarits paramétrés choisis par `visual_intent` · chorégraphie écrite par le
LLM local · vectorisation `vtracer` d'une image FLUX puis animation des chemins). C'est le
cœur de l'étape 30.1, et la question tient en une phrase : **d'où vient le schéma quand
personne ne le dessine.** Dis-moi si je le lance.

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

**[Étape 12.2 — ✅ FAIT le 17/09/2026] ~~Regarde les clips avant l'étape 13.2.~~** Thomas a regardé **`final.mp4`** (la vidéo complète, pas les clips) : « ça va c'est bien final.mp4 mais je pense que ça sera le thème le moins intéressant de tous ». Le blocage « mouvement non vu en lecture » est **levé** ; le classement « le moins intéressant » alimente la question « motion design en phase 2 ou 6 ». Le texte d'origine est conservé ci-dessous pour mémoire.
Les 127 clips du run FR sont rendus et au contrat, mais **je ne perçois pas la vidéo en
mouvement** : la note de 3,5/5 au manifeste porte sur une image de début et une image de fin, pas
sur la lecture. Ce qu'il faut regarder, dans
`workspace/runs/bms-science-fr-20260915-j7sf/clips/` : la **traînée derrière un sujet net sur
fond uni** pendant la parallaxe. À 130 px de dérive le sujet se dédoublait franchement ; c'est
ramené à 30 px avec un fond flouté, et le contrôle automatique ne voit plus aucun trou — mais
l'œil peut encore accrocher. **Si cela te gêne, la parade coûte un réglage** (`config/styles/
illustre.yaml` → `motion.default: ken_burns`) **et 25 minutes de re-rendu, sans regénérer une
seule image.** À faire avant l'étape 13.2, qui produit la vidéo de démonstration.

**[É23.2 — ajouté le 23/09/2026] La file est chargée pour le jalon ; six vidéos attendent des comptes, une relecture et un clic.**

| Quand | Action | Durée | Statut |
|---|---|---|---|
| **Avant le 29/09/2026** (première date) | **Comptes de bms-science-en et bms-histoire-en** selon `CONFORMITE.md` § 12.1 : Brand Account BMS, 2FA, **vérification téléphonique** (un numéro vérifie un nombre limité de chaînes par période : relire la page d'aide au moment du geste), jeton, jobs de rapports. Sans cela, `factory precheck` bloque chaque vidéo (contrôle 24-25) et les vidéos histoire-en de plus de 15 min sont refusées. Puis passer `two_fa_enabled` et `phone_verified` à `true` dans les deux YAML. | 1 h | ⬜ → **Thomas / Alek** |
| Avant de relancer le daemon | **Trancher l'action 17** (machine dédiée ou chien de garde) puis `factory daemon install`. Vérifier le disque : **11 Gi libres** le 23/09/2026. | 10 min | ⬜ → **Thomas** |
| Sous 48 h après chaque script | **Relire** : `factory queue approve <job> --reviewer <id>`. Trois sujets sur six sont hors niche (voir `STATE.md`) : les rejeter plutôt que les publier. | 10 min/script | ⬜ → **Thomas** |
| À chaque date, tant que l'audit n'est pas obtenu | **Clic Studio** d'après `factory publish manual-list` (§ 12.2) ; constater si Studio accepte une heure hors pas de 15 min (objection 8, sinon le jitter est arrondi). | 2 min/vidéo | ⬜ → **Thomas** |
| **Mercredi 14/10/2026** | **Vérification du jalon de phase 4** : vidéos publiées par chaîne, dates tenues, `factory calendar show --check`. | 30 min | ⬜ → **Thomas** |
| Avant l'étape 24 | Templates, police et locuteur **propres à chaque chaîne** sur tout le portefeuille (objections 3-4, `CONFORMITE.md` § 12.7). | — | ⬜ → **Thomas** |
| Après l'étape 24 | **Rendre `template_id` visible au rendu** (calques, cadrage, transitions par template) : aujourd'hui c'est une étiquette, et deux chaînes de même charte sortent des cadres identiques. | — | ⬜ → **Thomas** |

**[É23.1 — ajouté le 22/09/2026] Le code de publication est complet ; le canal ne l'est pas, et c'est toujours la même demi-heure qui manque.**

| Quand | Action | Durée | Statut |
|---|---|---|---|
| **Avant tout le reste** | **Ouvrir le canal, dans cet ordre exact.** (1) Console GCP : activer YouTube Analytics API **et Reporting API**, écran de consentement **Externe → En production**, client OAuth « Application de bureau » → `secrets/client_secret.json`. (2) `factory publish auth --channel bms-test`, puis reporter `channel_id` et `playlist_id` dans `config/channels/bms-test.yaml`. (3) **`factory publish reporting-jobs --channel bms-test` — avant la première vidéo** : les impressions et le CTR ne sont pas rétroactifs au-delà de 30 jours, et aucune autre API ne les donne. (4) `factory publish upload --run bms-science-en-20260920-s57f --channel bms-science-en`. (5) Déposer l'audit depuis `docs/AUDIT-API.md`. **Les deux réserves de l'étape 14 tiennent** : raison sociale de BMS pour `docs/PRIVACY.md` (→ Alek) et `virtual_images_mention` non tranché alors que les images montrent des corps. | ~30 min | ⏳ **à faire — chemin critique** |
| Avant le premier upload | **Vérifier chaque compte Google par téléphone.** `phone_verified: false` sur les six chaînes : sans cela YouTube refuse la miniature personnalisée (et les vidéos de plus de 15 min). Chaque tentative refusée coûte 50 unités et renvoie l'opérateur dans Studio. Mettre `google_account.phone_verified: true` dans le YAML une fois fait. | ~5 min/compte | ⏳ à faire |
| À la prochaine révision de `CONFORMITE.md` | **Corriger le chiffre de quota du § 2 et du contrôle 27 de la § 11** : « un `videos.insert` coûte 1 600 unités » est faux depuis juin 2026 (1 unité, compartiment « uploads » de 100/jour). Le plafond de **6 publications par jour** qui en découlait reste appliqué — décider s'il tient encore pour un motif de **cadence** (§ 6) ou s'il tombe. Je n'ai pas modifié `CONFORMITE.md` : c'est un document de conformité, il ne se réécrit pas au fil d'une étape. | Thomas | ⏳ à trancher |

### Non bloquant — à trancher avant l'étape indiquée

Sept questions pour **Alek**, deux pour **Thomas**, une ajoutée à l'étape 9, une à l'étape 20, une à l'étape 21. La n° 8 s'est matérialisée à l'étape 2.
Source : `STATE.md` § Questions ouvertes.

| # | Question | Qui tranche | À répondre avant | Statut |
|---|---|---|---|---|
| **11** | **Quel produit d'affiliation, sur quel réseau, pour quelle chaîne ?** *(ajoutée par l'étape 21)* Le sous-identifiant par vidéo est **livré et testé de bout en bout** — `<channel_id>_<lang>_<video_id>`, sans aucune donnée personnelle, limité à la longueur du réseau — mais uniquement sur `config/products/exemple-affilie.yaml`, qui ne pointe nulle part. Tant qu'aucun produit réel n'est configuré, aucune vidéo ne porte de lien, `paid_promotion` reste faux et **l'économie unitaire de l'étape 27 n'a rien à mesurer**. Il faut : le réseau (Awin, CJ ou Impact — **pas Amazon**, qui ne sait pas suivre par vidéo), l'identifiant de suivi, l'URL du produit, et la chaîne à qui l'attribuer. Rappel de `CONFORMITE.md` § 3 couche 2 : **toute vidéo affiliée exige un passage manuel dans Studio**, l'API n'exposant pas la case « promotion payante » en écriture. | **Alek et Sofiane** | avant l'étape 27 | 💡 **ouvert** |
| **10** | **Faut-il élargir le registre en FR, ES et IT sur les niches de production ?** *(ajoutée par l'étape 20)* La détection de trous multilingues fonctionne — 15 thèmes qui marchent en français et que les chaînes anglaises suivies n'ont pas traités — mais **13 des 15 viennent des trois chaînes françaises de compléments alimentaires** (Nutripure, Nutri&Co, Quentin fitlife), ni science ni histoire. Il reste **deux** thèmes exploitables pour les chaînes BMS d'aujourd'hui. La cause est le registre, pas le code : sur 74 chaînes suivies, **7 francophones, 2 hispanophones, 1 italophone — et l'italienne ne publie plus depuis le 02/02/2026**, donc elle n'apporte 0 vidéo dans la fenêtre de 180 jours. Une dizaine de chaînes FR/ES/IT en histoire documentaire, science et espace, ajoutées par `factory editorial watch add`, rendraient à cette brique ce qu'elle promet. 0 €, ~20 min de recherche. | **Thomas** (choix des chaînes) | avant l'étape 24 | 💡 **ouvert** |
| **14** | **Copier `~/BMS-backups` hors de cette machine, chaque semaine.** *(ajoutée par l'étape 22.1)* La sauvegarde quotidienne est en place et testée (archive de **17,8 Mo**, restauration à blanc vérifiée), mais elle est écrite **sur le même disque que l'original** : elle protège d'un effacement et d'une base corrompue, **de rien** si le Mac est perdu, volé ou noyé. Or c'est exactement le scénario où « l'actif est transférable » cesse d'être vrai. 30 jours d'archives tiennent dans **600 Mo**, c'est-à-dire dans n'importe quelle offre gratuite. Geste : `rsync -av ~/BMS-backups/ /Volumes/<disque>/BMS-backups/`, ou un dossier cloud. **Rien dans le code ne le fera à ta place** : envoyer les données du projet vers un service tiers est une décision qui t'appartient, pas à un daemon. Procédure dans `docs/EXPLOITATION.md` § 4. | **Thomas** | **immédiat, puis chaque semaine** | ⬜ |
| **15** | **Trancher ce qu'on fait de la purge post-export, sinon la production nocturne s'arrête après une vidéo.** *(ajoutée par l'étape 22.1)* Mesuré : 13 Gi libres au départ, **10 Gi** après un seul run arrivé au rendu, pour un plancher dur de 8 Go. La purge des intermédiaires prévue par `ARCHITECTURE` § 8 (≈ 1,5 Go par run) **ne s'exécute jamais** parce qu'elle est conditionnée à un export sans écart (`factory/steps/export.py:330`), et que `factory export` sort en code 4 sur cette charte depuis l'étape 13.1 — pour la raison de style que **tu as arbitrée** et qu'il ne faut pas « corriger ». Deux issues : *(a)* la purge s'exécute aussi quand le seul écart est celui, connu et arbitré, des plans détectés ; *(b)* la cadence descend à une vidéo par nuit. Le garde-fou fait déjà son travail — il met la production en pause à 8 Go — mais il la mettra en pause **avant la deuxième vidéo**. | **Thomas** | avant la première nuit de production réelle | ⬜ |
| **16** | **Deux sujets sur trois de la file éditoriale ne sont pas produisibles, et ça se voit seulement à la deuxième étape.** *(ajoutée par l'étape 22.1)* Sur trois plans consécutifs de `bms-science-en` : « Why the World Will Not End as Predicted » et « The Real Threat Behind the Invasion Rumors » sortent tous deux en **2 sources sur 3 exigées** ; seul « Mind-Bending Physics Paradoxes » passe. L'étape 20 note des **titres qui donnent envie de cliquer**, `research` exige des **référents encyclopédiques** : ce ne sont pas le même objet, et rien ne les relie. Conséquence : un job sur deux meurt après avoir consommé un sujet de la file et ~2 min de calcul. Ce n'est pas un défaut de l'orchestrateur — c'est une couture manquante entre deux étapes livrées. | **Thomas** (choix de la correction : filtrer à l'entrée en file, ou élargir les mots-clés de `research` au cluster) | avant l'étape 22.2 | ⬜ |
| **17** | **La machine doit-elle être dédiée pendant la production, ou le runner doit-il acquérir un chien de garde ?** *(ajoutée par l'étape 22.1)* Le 21/09 à 15:46, **ton Mac a paniqué** — `watchdog timeout: no checkins from watchdogd in 91 seconds`, rapport dans `/Library/Logs/DiagnosticReports/`. Rien n'a été perdu. La cause, mesurée : le pipeline tenait `subtitles` **et une machine virtuelle tournait à 27 % de CPU** ; le swap est monté à **11,5 Go sur 12**, la mémoire libre à **0,8 Go**. Les deux garde-fous de l'étape 22.1 n'ont rien empêché, et pour deux raisons distinctes : celui de la **mémoire** ne s'applique qu'**avant** une étape, alors qu'une étape dure de 10 min à 3 h ; celui du **disque** a été trompé — il a lu 6,34 Go libres sans qu'un seul fichier du projet ait grossi, **c'est le fichier de swap qui mangeait le disque**. Preuve que l'étape n'est pas en cause : sur la machine redémarrée et au repos, l'ASR qui avait échoué deux fois à 600 s est passé en **44 s**. **Deux issues.** *(a)* **La machine est dédiée pendant la fenêtre de production** : pas de VM, pas de seconde session. Gratuit, immédiat, et cohérent avec la règle 4. *(b)* **Le runner acquiert un chien de garde** qui surveille la mémoire *pendant* une étape et la SIGTERM avant la famine — c'est du code, une demi-journée, et il faut décider de son seuil. *(J'en ai écrit un provisoire pour cette session, hors dépôt : il a veillé sur les 3 h 14 du dernier rendu sans jamais avoir à couper.)* | **Thomas** | avant la première nuit de production réelle | ⬜ |
| **18** | **`respiration` décide seule du verdict `qc`, et elle varie d'un facteur 95 entre deux runs.** *(ajoutée par l'étape 22.1)* Mesuré sur deux runs consécutifs de `bms-science-en`, même style, même TTS, un jour d'écart : `s57f` rend **8,51 pauses ≥ 0,4 s par minute** → famille parole 100/100 → **PASS** ; `s2ur` rend **0,09** — **une seule pause en 10,5 minutes**, 98,3 % de part parlée → famille parole 36,5 → **FAIL**. Les scores globaux sont pourtant voisins (88,5 et 85,6). **La cause n'est pas établie** ; pistes non vérifiées : la ponctuation du script, le rognage de silence de `voice`, l'`atempo`. **Pourquoi ça presse** : l'étape 22.2 doit régénérer automatiquement sous seuil. Régénérer sur un critère qui oscille de 95× ferait tourner la machine des nuits entières sans converger — et sur cette machine, une régénération coûte **4 h 15**. | **Thomas** (puis correction en 22.2) | **avant l'étape 22.2** | ⬜ |
| **19** | **Créer le bot Telegram, ou accepter qu'Alek et Sofiane ne soient prévenus de rien.** *(ajoutée par l'étape 22.2)* Les six alertes sont en place et éprouvées, mais `.env` n'a ni `TELEGRAM_BOT_TOKEN` ni `TELEGRAM_CHAT_ID` : le canal retombe sur la **notification macOS**, qui **ne sort pas de ce Mac**. Elle dépanne Thomas, elle ne supervise ni Alek ni Sofiane — donc, en l'état, « supervisable par des non-développeurs » est faux dès qu'ils ne sont pas devant la machine. Coût : **0 €, deux minutes**, procédure complète dans `docs/EXPLOITATION.md` § 9. Un groupe Telegram avec le bot dedans suffit pour que les trois reçoivent la même alerte. | **Thomas** (puis Alek pour le groupe) | avant la première nuit de production réelle | ⬜ |
| **20** | **Dire à Alek et Sofiane qui relit, et à quelle cadence — sinon la production s'arrête d'elle-même.** *(ajoutée par l'étape 22.2)* `factory review --reviewer <id>` est livré et la trace de conformité est complète, mais **un script non relu bloque tout son aval** : c'est une condition d'entrée, pas un avertissement. À la cadence mesurée — une vidéo coûte ≈ 4 h 15 de machine, donc 2 à 3 par nuit au mieux —, **une séance tous les deux jours suffit** et une séance quotidienne de dix minutes est plus confortable. Ce qu'il manque n'est pas du code : c'est un nom et un jour. `config/team.yaml` connaît `alek`, `sofiane` et `thomas` ; il attend de savoir lequel. | **Alek** (désigne Alek ou Sofiane) | avant la première nuit de production réelle | ⬜ |
| **21** | **Ouvrir un programme d'affiliation et configurer un produit réel** *(étape 27)*. Suivi par vidéo possible sur Impact (`SubId1`), CJ (`sid`), Awin (`clickref`, dépôt de 5 £), Digistore24, ClickBank ; Amazon US seulement par chaîne. Fournir : programme, identifiant de suivi, URL, chaîne, phrase d'appel à l'action. Importer ensuite le premier export réel avec Thomas pour valider les colonnes. | **Alek** | avant la première vidéo affiliée | ⬜ |
| **22** | **Taux horaire de la relecture** : 15 €/h est une hypothèse de travail ; la relecture pèse 99,7 % du coût estimé d'une vidéo. | **Alek** | avant le prochain `factory economics` | ⬜ |
| **23** | **Mesurer la puissance au wattmètre** pendant un run complet (hypothèse 30 W) ; **appliquer ou reporter la mise à jour macOS en préparation** : elle a mis le disque à 0 deux fois le 24/09. | **Thomas** | avant le 29/09 (première nuit de production) | ⬜ |
| **24** | **Écouter le hook de `fgr6` avec l'avatar** (`workspace/runs/bms-science-en-20260924-fgr6/final.mp4`, 0-12 s et 474-488 s) : synchro labiale acceptable ? style cel-shading acceptable à côté des images vectorielles ? Et **Alek** : un présentateur récurrent pour `bms-histoire-en` ? *(étape 29)* | **Thomas**, puis **Alek** | avant d'activer `avatar2d` sur une chaîne | ⬜ |
| 1 | Comptes Google et Brand Accounts des chaînes BMS : existent-ils, sous quelle propriété, qui détient la récupération ? | Alek | Étape 14 | ⬜ |
| 2 | Raison sociale, SIREN et adresse de BMS (formulaire d'audit API + mentions légales) | Alek | Étape 14 | ⬜ |
| 3 | Qui relit, à quelle fréquence, par lots de quelle taille ? « L'équipe » n'est pas une réponse valable. | Alek (désigne Alek ou Sofiane) | Étape 9 | ⬜ |
| 4 | `auto-approve` activé ou non, et sur quelles chaînes ? À acter par écrit : l'exception éditoriale RIA tombe pour ces vidéos. | Alek | ~~Étape 22.2~~ → **avant la production réelle** | ⬜ — **la mécanique est livrée** : `factory review --auto --channel X` n'existe que si `auto_approve: true`, affiche un avertissement rouge, écrit `reviewer = "auto"` et `ria_exception_claimed = false` dans le manifeste. Toutes les chaînes sont à `false`. Il manque la décision, pas le code |
| 5 | Acompte Awin de 5 £ accepté, ou Awin écarté ? Si écarté, l'attribution repose sur CJ et Impact seuls. | Alek | Étape 21 | ⬜ |
| 6 | Réseau d'affiliation primaire et niches de départ (détermine `config/products/`) | Alek et Sofiane | Étape 21 | ⬜ |
| 7 | Combien de chaînes au lancement ? (**langue tranchée : anglais, Alek, 15/09/2026**) | Alek | Étape 14 | 🔄 — **la moitié de la réponse est mesurée : ≈ 7 vidéos/semaine, soit 3 chaînes à 2/semaine avec 1 nuit de marge — pour des vidéos de 10 minutes.** L'étape 6 ajoute la nuance : **aux durées médianes du registre (18 à 31 min), c'est 7/semaine sur les niches à coupe lente et 3 à 4 sur `histoire_doc`**, et **10/semaine n'est pas atteignable en local** (`docs/STYLES.md` § 3.1) |
| 8 | Quel compte Google de recherche et quelle machine / IP résidentielle ? **Devenu concret** : l'IP de cette machine est bloquée par YouTube pour les transcriptions depuis le 14/09/2026. | **Thomas** | ~~Étape 3~~ → **Étape 16** | ⬜ — l'étape 3 n'a pas eu besoin de nouvelle collecte, elle a travaillé sur les 349 transcriptions existantes. La question reste entière pour l'étape 16, qui relira le registre. |
| 10 | **Fournir une adresse de contact pour les API gratuites** (`FACTORY_CONTACT` dans `.env`). Vide, Wikimedia plafonne le pipeline à **10 req/min au lieu de 200** et **PubMed est entièrement écarté** (NCBI exige `tool=` et `email=`) : les niches santé et science ne tournent aujourd'hui que sur Wikipedia. Le pipeline refuse d'inventer une adresse. | Thomas (ou Alek, si l'adresse doit être celle de BMS) | Avant la première production réelle (étape 22) | ⬜ ajoutée à l'étape 10 |
| 11 | **Trancher la durée des vidéos par chaîne, format court ou long.** `REFERENTIEL.md` § 2 : `science_pop` mélange des formats (p75/p25 = 12,9) et « l'étape 10 doit fixer la durée par chaîne ». Aucun champ ne le permet dans `config/channels/<id>.yaml` : `plan` emploie la médiane de niche (648 s) **et le signale à chaque passage**. | Thomas, sur proposition | Avant l'étape 15 (le banc compare la durée rendue à cette cible) | ⬜ ajoutée à l'étape 10 |
| 12 | **Fournir la phrase de divulgation ORALE pour Impact et Awin.** Leurs listes fermées ne contiennent que des hashtags (`#ad`, `#sponsored`, `#Ad`, `#PaidAd`) : ils ne se prononcent pas, or `CONFORMITE.md` § 3 impose une mention orale dans les 30 premières secondes du segment. Le code retombe aujourd'hui sur la mention générique de la langue (« Publicité » / « Paid promotion ») et **n'invente aucune reformulation d'une mention contractuelle**. | Alek (avec le contrat du réseau) | Avant la première vidéo affiliée (étape 27) | ⬜ ajoutée à l'étape 10 |
| 9 | **Vérifier mot pour mot les phrases de divulgation Amazon en fr, es et it** — `config/languages/{fr,es,it}.yaml` les portent, reprises de mémoire et **non vérifiées sur le portail du programme**. La phrase est contractuelle : une formulation approchée n'est pas conforme. L'anglais vient de la source officielle. | Alek (ou Thomas au portail) | Avant la première vidéo affiliée (étape 27) | ⬜ ajoutée à l'étape 9 |
| 13 | **Autoriser l'accès complet au disque au binaire Python**, sinon la collecte nocturne de l'étape 18 ne démarre jamais. Le projet est sous `~/Documents`, protégé par macOS : une tâche launchd y reçoit `Operation not permitted` et l'interpréteur **se suspend avant d'avoir démarré** (mesuré le 20/09/2026). Geste : Réglages Système → Confidentialité et sécurité → **Accès complet au disque** → ajouter `/Users/toms/.local/share/uv/python/cpython-3.12.13-macos-aarch64-none/bin/python3.12`, puis `factory editorial collect --install-agent` qui revérifie et le dit. **Le chemin change si `uv` met Python à jour.** | **Thomas** | **immédiat** — chaque nuit sans collecte est un jour d'historique perdu, et c'est la valeur même de l'entrepôt | ⬜ |
| 14 | **Trancher III.E.4.h contre `ARCHITECTURE.md` § 9 : garde-t-on les mesures dérivées au-delà de 30 jours ?** Les Developer Policies interdisent d'« use [API Data] to create new or derived data or metrics » (III.E.4.h), et limitent les *Non-Authorized Data* — tout ce que l'étape 18 collecte, compteurs de vues compris — à **30 jours** (III.E.4.d, l'exception « statistics » de III.E.4.b ne valant que pour l'OAuth). Or `ARCHITECTURE.md` § 9 et `CONFORMITE.md` § 9 posent depuis l'étape 1 l'inverse. Le système applique par défaut la lecture « usage interne, jamais affiché » ; `factory editorial purge --strict` applique la lecture stricte en une commande. Détail et les deux lectures : `CONFORMITE.md` § 9.1. | **Thomas** | Étape 25 | ⬜ |

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
| **[É21] Au bout de combien de jours fait-on tourner la miniature ?** | Le plan écrit par `thumbnail` dit **7 jours**, parce que le prompt de l'étape le dit et parce que la Reporting API a 72 h de latence et ne garde ses rapports « reach » que 30 à 60 jours : attendre un mois ferait mesurer une bascule sur des données en train d'expirer. **Les blogs de créateurs conseillent l'inverse** — ne rien toucher pendant 30 jours, le temps de la phase de découverte. **Aucune source officielle de YouTube ne tranche**, et « Test & Compare » ne peut pas servir d'arbitre : il n'a aucune ressource dans la Data API v3. La valeur est un **paramètre** (`RotationMiniature.after_days`), pas une mesure. À réarbitrer à la phase 5 sur le CTR réel des premières vidéos, pas avant : d'ici là, personne n'a de CTR. | 💡 **ouvert — Thomas, à la phase 5** |
| **[É13.2 · CÂBLÉ le 18/09/2026] La mention « Images virtuelles » ne pouvait jamais être posée** | Les **124 plans** du run FR portent `contains_person: false`, **déclaré par le LLM à la shotlist, jamais mesuré sur l'image produite**. `virtual_images_mention` vaut donc `false`. Or la **miniature elle-même** — celle que YouTube affichera — montre **deux bras et deux mains**. `CONFORMITE.md` § 3 déclenche cette mention sur « un visage ou une **silhouette humaine**, réaliste ou non », par une condition **distincte** de `contains_synthetic_media` (qui, lui, reste correctement `false` : 124 scènes, 0 réaliste). Deux parades : un contrôle sur l'image, ou la mention posée par défaut sur les niches à personnages. | 🔄 **câblé, à confirmer sur image avant le premier upload.** La cause n'était pas le LLM : `AssetRequest.contains_person` était la **constante `False`** dans le code (`shotlist.py:434`) — le contrôle 27, marqué « Bloquant », était **du code mort sur tous les runs**. `figure_une_personne()` le déduit désormais de l'intention (vocabulaire fr/en/es, comparaison **mot à mot** : « mains » déclenche, « domaine » non). Mesuré sur le run FR : **0/124 → 20/124 plans**, `virtual_images_mention` `False` → **`True`**. **Reste ouvert** : c'est un plancher lexical, généreux à dessein ; seule une détection sur l'image verrait un corps qu'aucun mot n'annonce — et c'est le cas de la miniature. |
| **[É13.1] Le rythme de coupe *perçu* est le double du rythme planifié** | Mesuré sur `final.mp4` : **64 plans détectés pour 127**, soit **11,53 s par plan perçu** contre **5,88 s posés**. Le montage n'est pas en cause — les 127 coupes sont à l'image près (22 139 images attendues, 22 139 obtenues). Deux causes : **20 frontières réemploient la même image** (plafond structurel à 107), et les autres coupes sont **peu contrastées** — en abaissant le seuil de détection, 27 → 64, 18 → 77, 12 → 89, **8 → 103 soit 96 % du plafond**. C'est une propriété de la charte « illustre » (même palette, même fond, sujet centré), pas de l'assemblage. **Le seuil n'a pas été abaissé pour faire passer le critère.** **Recadré le 16/09 au soir par ton retour** (« pas mal si le style c'est vraiment avec des images fixes, une ambiance assez spéciale ») : si le fixe est assumé comme style, **la coupe porte tout le rythme** et son contraste devient le premier défaut à corriger, pas une subtilité de mesure. | ⬜ **à trancher avant l'étape 15** — durcir le contraste inter-plans dans la charte (fonds, cadrages, échelles), ou réécrire le critère contre le plafond détectable ; et dire si Ken Burns reste |
| **[É13.1] Cinq pistes musicales à déposer, et c'est un geste manuel** | `workspace/library/music/` est vide : le run FR est monté avec un **lit silencieux** et **aucune vidéo ne peut être publiée** tant que `music_track` est vide (`CONFORMITE.md` § 10.1, contrôle 8). Aucune voie automatique n'est conforme : Freesound écarté depuis le 15/09 (CGU de l'API non commerciales), automatisation du navigateur exclue, la bibliothèque audio n'a pas d'API. Procédure, filtres et schéma JSON dans **`docs/MUSIQUE.md`**. Le code est écrit et testé, il attend les fichiers. | ⬜ **toi, avant l'étape 13.2** — 5 pistes, 5 moods, depuis le Studio du compte de test |
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

**[Langue — ajouté le 17/09/2026] Anglais uniquement, plus aucune version FR.**

Alek a tranché l'anglais le 15/09/2026 ; Thomas a précisé le 17/09/2026 qu'aucune version FR ne doit plus être produite, ni en double, ni en repli : « je perds trop de temps à générer version FR et EN ». Appliqué le 17/09/2026 dans `ROADMAP.md` : ligne de décision au § 3.1, prompts des étapes 13.2 à 30.2 réécrits (deux runs EN en 13.2, upload du run EN en 14, `bms-histoire-en` à créer en 17, éditorial en anglais aux étapes 19 à 21, file et jalon sur chaînes EN aux étapes 22.1 et 23.2), étape 24 marquée différée, risque 5 du § 9 sans objet. Les étapes closes (1 à 13.1) ne sont pas réécrites. La documentation reste en français (règle 12).

| Quand | Action | Durée | Statut |
|---|---|---|---|
| Avant l'étape 15 | **Trancher le TTS anglais** : mesurer Kokoro EN (RTF, WER par palier, timbres distincts), puis purger Qwen3-TTS (4,52 Go) si Kokoro tient — c'est la marge disque qui débloque un juge VLM local (étape 15) et le banc Z-Image-Turbo. La question GPL de Kokoro reste entière et ne dépend pas de la langue. | ~1 h de mesure | ⏳ à faire |
| ~~Avant l'étape 17~~ | ~~Rejouer `bms-science-en-20260917-avwf` à partir de `voice`.~~ | — | ✅ **fait le 18/09/2026 par la session, Thomas absent.** Le rejeu a d'abord **révélé deux défauts** qui le rendaient inutile. *(1)* Le pipeline **ne réinvalide pas ses caches** quand une étape amont est réécrite hors pipeline : `script.done` datait du 17/09 alors que `script.json` avait été réécrit le 18 à 15h35 par l'étape 16, donc `voice` a rendu en **29 s** et `subtitles` en **2 s** sur l'ancien découpage — **2 h 52 de machine perdues** (EXIT 3). *(2)* `merged_from` porte déjà l'id de l'unité, ce qui **dédoublait le segment** (31 fenêtres pour 28) — corrigé en `916214b` avec un test qui échoue sans le correctif. Le même piège existe au niveau des **clips**, réutilisés par nom sans vérifier qu'ils collent au découpage courant. **Reprise avec `voice --force` et `subtitles --force`** : voix 634,93 s, shotlist **sain** (114 plans, somme = enveloppe, 0 chevauchement, plan le plus long 8,8 s), `final.mp4` **634,931 s contre 634,930 s de voix**. **Banc 87,1/100** (79,1 avant) : `coupes` 46,2 → **88,2**, `lisibilite` 56,8 → **82,7**, `variete` **100**, `visual_distinct_ratio` **0,921** contre 0,355. ⚠️ **Seul bloquant : `hook_visual_change`** (0,19 YAVG, seuil 0,5) — il passait avant parce que le **fondu d'ouverture** gonflait la moyenne à 0,80. Il vient du `zoompan` que tu as demandé de **garder** : **c'est ton arbitrage, rien n'a été « réparé ».** |
| Avant l'étape 17 | **Dire si le plancher de longueur du hook doit rester à 22 mots** (p25 de `science_pop`). Le 9B rend 19 mots sur trois tirages malgré la consigne explicite, avec une note de patron de 95,5/100 : soit le plancher descend, soit le hook est écrit en deux phrases imposées. L'infraction n'est pas bloquante aujourd'hui. | Thomas | ⏳ à trancher |
| Quand tu peux | **Libérer de la mémoire avant les étapes longues.** La session du 18/09 a tourné avec **6,2 Go de swap sur 7,1** : le LLM est descendu à 7 tok/s contre 22 de référence, et un seul appel de réparation a coûté 240 s. Aucun chiffre de temps de l'étape 16 n'est comparable aux étapes passées. | Thomas | ⏳ |
| Quand tu veux | **Décider du sort des fichiers `config/channels/bms-science-fr.yaml`, `bms-histoire-fr.yaml`, `bms-histoire-es.yaml`** : conservés comme exemples inactifs (rien ne les lance si personne ne les nomme) ou supprimés. Je n'ai rien effacé. | 2 min | ⏳ à trancher |
| Clos | Les enquêtes « Serena FR sous 3 s » et « parakeet traduit le français » deviennent **sans objet** pour la production ; elles restent dans `STATE.md` comme constats. | — | ✅ sans objet |

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
| P1 | **13.1** | Montage, musique, sous-titres, export vérifié | ✅ | 16/09/2026 | `93b1db7` | **4/5** — `final.mp4` **h264 High 1920×1080 30 ips + aac 189 kb/s** · durée **737,964 s** contre **737,921 s** de voix, **écart 0,043 s** (tolérance 0,5) · **-14,0 LUFS**, crête **-3,8 dBTP** · piste **`mov_text` (fra)**, 337 cues · **174,2 Mo** · 5 images de contrôle, **3 regardées** · montage **242,6 s**, export **47,6 s** · **181 tests verts** (2 échecs antérieurs à l'étape, prouvés par `git stash`). **Critère non tenu : plans détectés 64/127**, cause établie et mesurée (plafond 107 · seuil 8 → 103) → § 1. **Musique : lit silencieux**, bibliothèque vide et Freesound écarté |
| P1 | **13.2** | Miniature, métadonnées, `factory run`, première vidéo complète | ⚠️ | 17/09/2026 | `b27a817` | **JALON PHASE 1 ATTEINT — 1 run complet sur 2 demandés.** Run FR `bms-science-fr-20260917-rtmk` : **2 h 23 de bout en bout (8 566,1 s), aucune intervention manuelle**, `run_state = awaiting_review`, **coût 0,018 €** · `final.mp4` 145,1 Mo · `thumbnail.png` **1280×720, 0,70 Mo, texte à 53,6 % de la hauteur** (seuil 12 %), contraste **12,04**, 3 variantes · `metadata.json` **titre 49 car.**, **8 variantes** (≥ 5), **5 textes de miniature** (≥ 3), **10 chapitres**, mention IA, attribution, tags 388 car. · `manifest.json` timings par étape + wallclock + coût + variantes · `contains_synthetic_media = false` sur **124 scènes, 0 réaliste** · **214 tests verts** · **1 image regardée** (la miniature). **Divergences : le 2ᵉ run (EN) a été arrêté par Thomas pendant `render`** (4 images sur ~50) — la preuve « deux fois de suite » n'est pas faite ; **le run de démonstration est en FR** alors que la production est EN ; **les 3 défauts ne sont pas dictés** (→ § 1). **Résidu** : `virtual_images_mention = false` non vérifié sur l'image (→ § 1, avant l'étape 14) |
| P1 | **14** | Ouvrir le canal officiel : upload privé, OAuth en production, dépôt de l'audit API | 🔄 | 18/09/2026 | `44ca905` | **0/4 — LE CODE EST LIVRÉ, LE CANAL N'EST PAS OUVERT.** Livrés et testés : `factory/publish/oauth.py` (189 l.), `factory/publish/upload_min.py` (394 l.), `config/channels/bms-test.yaml`, `docs/PRIVACY.md` (186 l., EN + FR), `docs/AUDIT-API.md` (210 l.), `tests/test_etape14.py` (295 l.) — **234 tests verts** (214 à la clôture de 13.2). **Aucun des quatre critères du « Terminé quand » n'est tenu**, et aucun ne dépend du code : `secrets/client_secret.json` **absent**, `secrets/tokens/` **vide**, aucun `publish.json` sur les 5 runs, aucune vidéo uploadée, audit non soumis, `«URL-PUBLIQUE»` et `«CONTACT-BMS»` encore en gabarit. **Aucun appel n'a touché un point d'entrée Google : le chemin est testé contre des doublures.** L'étape demande **Thomas 30 min au navigateur** (→ § 1). **L'étape 15 ne dépend pas de l'étape 14** : ses pré-requis sont 13.2, deux runs exportés et `REFERENTIEL.json` |
| P2 | **15** | Banc d'évaluation objectif et portillon qualité | ✅ | 18/09/2026 | `005691e` | **4/4** — `factory qc --run <id>` produit `qc.json` avec **26 mesures dont 21 notées** (valeur, unité, cible, origine de la cible, score partiel, poids, bloquant), un score 0-100 et un verdict · **fixture idéale 100,0/100** (seuil ≥ 95) · **vidéo volontairement défectueuse rejetée** : 49,3/100, FAIL, `blocked`, durée à 50 % de la cible et **−29,6 LUFS** nommées séparément avec leurs bornes · **les deux runs de la phase 1 notés** : `rtmk` **70,6 FAIL**, `j7sf` **81,1 FAIL**, faiblesses listées · `docs/QC.md` (445 l.) documente métriques, cibles, pondérations, seuils, calibration et recalibration · **banc en 128,5 s et 168,0 s** pour 12 min de vidéo (contrainte < 180 s) · **253 tests verts** · contradicteur : **16 objections, 12 retenues, 3 retenues autrement, 1 refusée sur preuve** |
| P2 | **16** | Ingénierie du hook et de la rétention | ✅ | 18/09/2026 | `150d4d8` | **4/4, dont un critère tenu au 6ᵉ run.** `factory script` refuse un script non conforme, le régénère (3 essais) avec le motif exact, puis échoue explicitement (`run_state: failed` + motif) — prouvé sur 5 runs · **run 6 `awaiting_review`** : hook du type tiré (`in_medias_res`, 3 candidats, choix au manifeste), **2 boucles plantées et 2 payées vérifiées par marqueurs ET par juge sémantique**, 26 ruptures posées avec écart max 30 s pour une cadence de 23,4 s, densité **5,34** pour une cible de 5,0, durée 573 s pour 648 (−11,6 %) · `qc.json` porte les **6 nouvelles métriques**, toutes notées · **288 tests verts** (284 à la reprise). **Le code de la session perdue n'avait jamais été exécuté : 8 défauts trouvés en l'exécutant**, dont un qui empêchait le juge de boucle de trancher quoi que ce soit depuis son écriture. **Résidus** : hook à 19 mots sous le plancher de 22 (non bloquant) ; voix et rendu non rejoués, donc le score global de `qc.json` (78,4 FAIL) mesure l'ancienne vidéo contre le nouveau script et **ne vaut pas** |
| P2 | **17** | Moteur « documentaire » (banques libres) et rythme de coupe vérifié | 🔄 | 19/09/2026 | `62dad04` | **3/5 mesurés, 2 en attente du run.** Tenus : **rythme au découpage** — 174 plans à **4,32 s** de médiane pour une cible `histoire_doc` de 4,50 (**−4,0 %**), et **+12,3 %** sur le run illustré `avwf` (6,57 pour 5,85) : **les deux styles dans les ±15 %** · **repli testé** — mot inventé sur les trois requêtes, 5 banques interrogées, 12 requêtes, `None` rendu en 6,1 s **sans exception** · **`licence.json` par asset**, contrat `Asset` complet, 153 fichiers en bibliothèque. En attente : le run n'est **pas terminé** (86 images de repli à générer, 0 clip rendu — le Mac a dormi, puis `load average 42`), donc **ni `qc.json` documentaire ni le bloc d'attribution de `metadata.json` ne sont mesurés**. **311 tests verts** (289 à la reprise ; les deux modules livrés le 18/09 n'avaient aucun test). **Quatre défauts trouvés en exécutant du code jamais exécuté**, plus deux hors du module : polices de charte absentes du dépôt, et cent crédits CC-BY coupés au milieu d'un nom d'auteur par le plafond de description |
| P3 | **18** | Entrepôt concurrentiel et snapshots quotidiens | 🔄 | 20/09/2026 | `51c7ec1` | **3/4 tenus à la lettre · 1 impossible en une seule journée.** Tenus : **74 chaînes et 11 159 vidéos** en base (seuils 60 et 5 000) pour **480 unités** sur un plafond de 6 000, **0 erreur** · la seconde collecte `--force` ajoute **4 300 instantanés** pour **202 unités** et `factory editorial top` rend **20 vidéos classées** avec chaîne, âge, vues, vélocité et ratio · politique de conservation écrite en `CONFORMITE.md` § 9.1 · `launchctl list` montre la tâche chargée (03:08). **Non tenu : le classement par vélocité à 7 jours** — les deux collectes sont du même jour, un delta de vues exige deux dates ; la vue retombe sur la vitesse moyenne depuis publication **et le dit** (`velocity_source`). **Réserve grave : la tâche est chargée mais macOS l'empêche de s'exécuter** (TCC sur `~/Documents`, mesuré) → action Thomas n° 13. |
| P3 | **19** | Détection et notation de niches | ✅ | 20/09/2026 | `a5c7d44` | **4/4, avec une divergence assumée sur la langue.** Tenus : **11 niches classées** (8 du registre + 3 candidates hors registre) avec les 4 sous-scores, l'indice de saisonnalité et des liens de preuve — seuil ≥ 8 · **`niche_scores` : 11 lignes (niche, langue, date)**, chacune avec son `evidence_json` · **appels Wikimedia porteurs d'un User-Agent identifiant**, exemple reproductible dans le rapport, testé HTTP 200 · **objections du contradicteur traitées : 14 reçues, 12 appliquées, 2 écartées avec motif**, toutes au § Objections du rapport · **exécution 256 s à froid, 4,1 s avec le cache** — seuil < 30 min. **Non tenu : « × 4 langues ».** 1 langue, l'anglais — la production est en anglais seul depuis la décision d'Alek du 15/09/2026 (`ROADMAP.md` § 3.1) ; la colonne `lang` et l'option `--lang` existent. **Top 3 : `histoire_doc` 76,7 · `espace_astronomie` 74,5 (candidate) · `science_pop` 66,5 — et le rapport écrit que les deux premiers ne sont pas départagés** (écart 2,2 < un cran de note humaine à 5,0) |
| P3 | **20** | Sujets gagnants, trous dans l'offre, file de sujets | ✅ | 20/09/2026 | `6569719` | **5/5.** `factory editorial topics --channel bms-science-en` et `--channel bms-histoire-en` rendent chacun **37 sujets en file** (seuil 20) avec score, angle et preuves — vidéos sources, vélocité, demande, lacune · **`factory plan` prend le meilleur sujet non employé et l'enregistre `source = topics_queue`**, preuve recopiée dans `spec.json` · **aucun sujet identique sur deux chaînes de même langue** : le même sujet inséré de force dans la file de `bms-histoire-en` avec le score le plus haut (0,99) est écarté, la chaîne en prend un autre · rapport de trous multilingues produit pour les deux chaînes. Mesuré : **5 604 vidéos** sur 180 j, **943 percées**, **738 clusters**, **15 trous multilingues / 47 de demande / 6 résurgences**, **381 s** à froid puis **33 s** au cache. **455 tests verts** (435 à la clôture de 19). **Deux seuils de la littérature étaient faux sur ce modèle et échouaient en silence** (0,35 de regroupement → un seul cluster ; 0,80 de similarité → tous les candidats rejetés), **deux critères de trou étaient inopérants** (seuil d'âge hors fenêtre ; résurgence qui ne mesurait que l'âge). Tous les quatre corrigés sur mesure et verrouillés par `TopicsScoring` |
| P3 | **21** | Titres, miniatures et métadonnées en variantes, sub-ID d'affiliation | ✅ | 20/09/2026 | `9037c7c` | **4/4.** `factory run --channel bms-science-en --from thumbnail` sur `avwf` : **8 titres au manifeste** avec note de règles, rang de duel et verdict de promesse (seuil ≥ 8) — le vainqueur du tournoi avait la **4ᵉ heuristique (0,550)** et a battu le mieux noté (0,857) · **3 miniatures rendues et mesurées sur leurs pixels** (`variant_1..3.png`, 0,67 à 0,72 Mo), scores **1,000 / 0,992 / 0,615**, la 3ᵉ pénalisée à juste titre pour un contraste de **2,75** sous le seuil WCAG de 4,5 · `metadata.json` : **9 chapitres** (premier à 0:00, écarts ≥ 10 s), sommaire de 4 lignes, **29 tags pour 397 caractères** guillemets compris, **3 hashtags**, commentaire épinglé, catégorie 28, description **959 octets** · **plan de rotation** écrit (`thumbnails.set` après 7 j si CTR sous la médiane) · **486 tests verts**, dont 31 dans `tests/test_seo.py` (seuil ≥ 8). `factory/steps/titles_v1.py` supprimé. **Trois défauts trouvés en regardant le rendu, invisibles aux tests** : texte débordant du cadre avec toutes les mesures au vert, description anglaise portant trois intitulés français, autocomplete rendant cinq fois la même racine. **Deux constantes de mon propre score étaient inventées** (saturation de netteté à 300 contre 3 559-5 788 mesurés ; « optimum » de surface à 12 % qui mettait les trois variantes à zéro) : corrigées sur mesure. **Deux règles d'API violées sans le savoir** : description en **octets** et non en caractères, tags **+2 caractères** par tag à espace |
| P4 | **22.1** | Orchestrateur : file, reprise, journal, daemon, sauvegardes | ✅ | 21/09/2026 | `f104f6f` | **3 critères sur 4 mesurés ; le 4ᵉ atteint à moitié, pour une raison éditoriale et non orchestrale.** Reprise après `kill -9` ✅ (même étape, `attempts` 0 → 1, preuve dans `events.jsonl`, quatre fois) · trois archives dans `~/BMS-backups/` (17,8 à 17,9 Mo, **dont celle du 21/09 produite par launchd sans personne**) et `restore-test` **RESTAURABLE en 0,2 s** ✅ (runs 17 = 17, jobs 4 = 4, 18 tables, **0 secret**) · agents `launchd` ✅ · **1 job `exported` sur 2** ❌ : le job 2 passe `qc` (PASS, `final.mp4` 550 s, 122 Mo), le job 4 est `blocked` par `qc` **FAIL** — famille parole 36,5 sur un plancher de 50. C'est le comportement voulu (divergence 81) et `qc` nomme les étapes à refaire : c'est l'étape 22.2. **527 tests verts** (486 à la clôture de 21). **Trois défauts trouvés par le test de bout en bout, aucun par les tests unitaires** : une non-conformité (`script` en code 4 sautait la barrière de relecture), un clip tronqué que la reprise ne savait pas refaire, et un `launchctl bootout` qui ne survit pas à un redémarrage. **Une panique noyau** a interrompu la session |
| P4 | **22.2** | Relecture par lots, régénération sous seuil, alertes | ✅ | 22/09/2026 | `912de75` | **3 critères sur 3 mesurés.** *(1)* **Barrière de relecture** : le job 6 (`mtn7`) s'arrête en `awaiting_review` avant `assemble`, `factory review --reviewer thomas` affiche la fiche (titre, angle, hook, 573 s pour 648 s = −12 %, densité 5,34 faits/min, 3 premières lignes), **Thomas décide lui-même**, et `review_log` porte `thomas | approved | 40fd9e07 | 2026-09-22T14:30:11Z` — **la première ligne du projet qu'un humain a réellement signée**. Le job repart et `assemble` — l'étape que la barrière bloquait — tourne jusqu'au bout ; il s'arrête ensuite à `thumbnail` pour une raison étrangère à la relecture (run du 19/09 sans aucune image d'asset sur disque). *(2)* **Régénération ciblée, sur une vraie vidéo** : `final.mp4` de `s57f` saboté à **−26,0 LUFS** (mesuré `ebur128`), banc **FAIL** (score 82,6), remède `loudness → assemble`, reprise de `assemble` **et de l'aval seulement**, puis banc **PASS à −14,0 LUFS** (score 88,5) — **289 s de bout en bout** là où rejouer le run aurait coûté ≈ 4 h. `manifest.execution.regenerations[0]` porte `mesure, depuis, rang, valeur_mesuree −26.0, cible −14.0, resultat pass`. *(3)* **Digest et alertes** : `reports/digest_2026-09-22.md` produit ; quatre notifications macOS parties (`osascript` code 0), **vues à l'écran, confirmé par Thomas**. Telegram non configuré — action humaine 19. **570 tests verts** (527 à la clôture de 22.1), dont 43 dans `tests/test_etape22_2.py`. **Une contradiction entre deux documents tranchée par la mesure** (`QC.md` fait de `loudness` un bloquant sans reprise, le prompt de 22.2 demande « loudness → assemble ») et **une perte de preuve corrigée dans le schéma** (`review_log` écrasait le rejet qui précédait une approbation) |
| P4 | **23.1** | Publication par l'API : OAuth par chaîne, upload, miniature, sous-titres, label, quota, rapports « reach » | 🔄 | 22/09/2026 | `c299c67` | **2 critères sur 4 mesurés ; les 2 autres exigent un jeton OAuth qui n'existe pas.** Livrés : `009_publish.sql` (`publications`, `quota_ledger`, `reporting_jobs`, vue `v_quota_jour`), `factory/publish/{quota,youtube,reporting_jobs}.py` (≈ 1 150 l.), `factory publish upload | release | status | manual-list | reporting-jobs`, `PublicationConfig` + bloc `publication` de `config/orchestrator.yaml`, `docs/EXPLOITATION.md` § 10, `tests/test_etape23_1.py` (**34 tests**) — **604 tests verts** (570 à la clôture de 22.2). **Tenus : `quota_ledger` enregistre les unités du jour** (17 appels, deux compartiments, `ok` par appel) et **`publish.json` + manifeste sont écrits** au contrat de `INTERFACES.md`. **Non tenus : aucune vidéo au statut `published_private` et aucun job chez Google** — `secrets/` est vide, les trois tables sont à 0 ligne, et rien de ce qui manque n'est du code (action humaine de l'étape 14, toujours pas faite). **Toute la chaîne est prouvée sur API factice** : 5 jobs → `videos.insert` → miniature → sous-titres → `videos.list` (`private`, `en`, catégorie 28) → `release --at J+7` (`publishAt 2026-09-29T15:00:00Z`, ligne `scheduled`) → annulation (`publishAt` retiré). **Un chiffre du projet était faux partout** : `videos.insert` coûte **1 unité d'un compartiment « uploads » de 100/jour**, pas 1 600 des 10 000 → une publication complète = 1 upload + **501 unités**, soit **15/jour** au lieu des 4 calculées (`INTERFACES.md` corrigé, `CONFORMITE.md` § 2 **non**, → § 1). **Trois des cinq types de rapports du prompt n'existent pas** (`_a2` → `_a3`) ; `reportTypes.list` est interrogé avant toute création. **Trois défauts trouvés en exécutant** : `videos.update` réinitialisait `license`/`embeddable` en silence, une `HttpError` de construction échappait au filet, et `publication.md` (exigé par `CONFORMITE.md` § 2 depuis l'étape 1) n'était écrit par personne |
| P4 | **23.2** | Calendrier crédible, checklist de conformité pré-publication, bascule post-audit | ✅ | 23/09/2026 | `b8cc255` | **5 critères sur 5 mesurés.** `factory calendar plan --weeks 3` date **6 vidéos sur 2 chaînes** (29/09 → 10/10), `calendar show --check` : **0 violation** ; `factory precheck` **PASS** sur un run conforme (bac à sable) et **FAIL, code 5** une fois la mention IA retirée (« [3] mention_ia : mention IA absente de la description ») ; `publier_run` et le daemon appellent precheck avant tout upload (test : job `blocked` avec la raison) ; file : 6 jobs `queued` avec `publish_at` ; `CONFORMITE.md` § 12 écrit. **619 tests verts.** Sur le vrai run `s57f` : FAIL (relecture auto, comptes non vérifiés) — conforme. 11 objections, 7 corrigées |
| P4 | **24** | Déclinaison multilingue par adaptation | ⏸ différée | 23/09/2026 | `dbbb270` | **Désactivée le 23/09 : « Pas de FR, full anglais » (Thomas). Code livré, inactif. 3 critères sur 5.** Tenus : manifeste enfant avec `parent_id`, template `sci-b` ≠ `sci-a`, miniature `bandeau_bas` ≠ `bloc_gauche` (**pHash 28**), hook régénéré · coût mesuré et consigné : **74,6 / 142,8 min = 0,523** (cible ≤ 0,25 **non tenue**, la voix pèse 40 min) · l'orchestrateur enfile les enfants des chaînes `derive_from` (test). **Non tenus : `qc` FAIL 66,9 et `precheck` FAIL** : le parent `rtmk` n'a que 36 images pour 124 plans et échoue lui-même (70,6) ; en bac à sable, seul le qc bloque. **0 image générée, 124/124 héritées.** Étape **différée** par décision d'Alek, lancée par le prompt. 625 tests verts |
| P5 | **25** | Récupérer les performances et les joindre au manifeste | ✅ code · ⏳ réel | 23/09/2026 | `351746f` | **3 critères sur 6 mesurés en réel, 3 sur fixture.** Réels : `perf_reach` vide **et expliqué** (aucun job : pas de jeton OAuth) · `v_video_perf` expose **20 colonnes de facteurs** + métriques 7/30 j · agent `com.bms.factory.analytics` **chargé** (07:05). Sur API factice seulement : `perf_daily` par vidéo, courbe de **100 points**, `show` en ASCII avec chute située (« chute de 20 pts à 02:51 : segment 8 (seg_08), rôle point »). **0 vidéo publiée** : rien de réel à tirer. 633 tests verts |
| P5 | **26** | Apprendre et réinjecter ; valider le banc contre les vues | ✅ code · ⏳ réel | 23/09/2026 | `671b053` | **n = 0 vidéo à J+7 : tout est « non décidable », aucun poids actif.** Tenus : `factory learn` écrit `learned/weights.json` (version 1.0) et `reports/learn_2026-09-23.md` · rétrécissement prouvé sur données synthétiques (même effet brut de 0,5 : n = 2 → < 0,1 ; n = 40 → > 0,4) · section « Banc vs résultats » présente, décision **seuils inchangés, non décidable (n = 0, QC.md § 8 exige 30)** · 12 objections traitées (9 appliquées, 2 résidus sur la vue, 1 partielle). **Non tenu tel quel : les deux listes de `plan --dry-run` sont identiques** — attendu à n = 0 ; le mécanisme est prouvé avec des poids fictifs (sujet 9ᵉ → 1ᵉʳ). 648 tests verts (15 nouveaux) |
| P5 | **27** | Affiliation, funnel et économie unitaire | ✅ code · ⏳ réel | 24/09/2026 | `c6b64a3` | **3 critères sur 3 mesurés (revenu réel = 0).** Lien `?SubId1=<video_id>` identique en description, commentaire épinglé et `affiliate_links` (bac à sable `c7km`) · fixture Impact : 6 lues, 5 rattachées, 1 annulée, 1 non rattachée, ré-import idempotent · `reports/economics.md` : **3,76 €/vidéo (n=7), 99,7 % de relecture estimée** ; illustré 9,35 min de calcul/min (0,341 €/min, n=6), motion 4,77 (0,355 €/min, n=1) ; 3 décisions chiffrées. **Phase 5 non close** (0 vidéo publiée). 658 tests verts |
| P6 | **28** | Tableau de bord d'exploitation | ✅ | 24/09/2026 | `113903b` | **4/4.** 8 pages rendues sans exception (`AppTest`, 9 fichiers dont `app.py`, et sur la vraie base) · approbation depuis le navigateur → `review_log` `reviewer = alek, decision = approved` (bac à sable) · cadence 3/semaine **refusée** (`per_week_max ≤ 2`), 1/semaine **écrite**, diff d'**une ligne**, `.bak` gardé · 3 captures dans `docs/img/`, regardées. 15 tests, 673 au total |
| P6 | **29** | Bibliothèque d'assets, voix et personnages cohérents, avatar 2D, chartes | ✅ | 24/09/2026 | `e222858` | **4/4.** `factory library stats` : comptes par type (554 images, 108 stock, 1 personnage, 4 intros) et **réemploi 10 derniers runs 19,0 %** (128/673, tout venant des runs dérivés) · run `fgr6` en `avatar2d` overlay : **QC PASS 88,2**, visèmes **D, F, X** vus sur 3 images de `final.mp4` · **2 chartes × 3 gabarits**, `charte_version` + `template_id` au manifeste, rotation vérifiée par `precheck` · `reports/compound.md` : vidéo neuve 252 min contre 13,9 à 74,6 min sans image neuve ; **coût de la vidéo 1 illisible** (manifeste écrasé par les reprises). Avatar : **+37,8 s par vidéo**. 686 tests |
| P6→**P2** | 30.1 | Moteur « motion design » (Revideo) | ✅ | 19/09/2026 | `fb037f5` · `0e003d4` · `a08c947` | **4/4** — **21 scènes** (≥ 6 exigées), dont 12 jouées ou construites ajoutées après ton retour · 114/114 clips au contrat, 0 écart `ffprobe` · `factory qc` **PASS 95,5/100** · **20,1 s par minute de vidéo** inscrit dans `RESULTATS.md` § 3 (plafond du prompt : 8 × ; mesuré **0,335 ×**, puis 0,45 × en v2) · polices et palette vérifiées sur planches d'images · **part de texte ramenée de 51 % à 0-8 %** (§ 3.5) |
| P6 | **30.2** | Moteur « whiteboard » | 🔄 | 19/09/2026 | `9ca844f` | **3/4 mesurés, 1 en attente d'une vidéo entière.** Tenus : **30/30 clips au contrat, 0 écart `ffprobe`** · **plafond de 400 contours appliqué et journalisé par image** (médiane 20, étendue 2 → 150, 3 images re-simplifiées, aucune n'atteint le plafond) · **temps par plan inscrit** dans `RESULTATS.md` § 3.6 (67,9 s/plan, 12,13 × le temps réel, dont 96,7 % de génération d'images ; rendu seul 0,395 ×) · **la main suit le trait** sur les 3 images extraites à 20/50/80 %, palier d'encre exactement à 80 %. **Non tenu : `factory qc` en PASS** — il demande `final.mp4`, donc un run complet, et aucun n'a pu être produit (voir § 1) |
| P6 | **31** | Documentation d'exploitation, reprise et plan de passage à l'échelle | ✅ (réserve) | 24/09/2026 | `8c08abe` | **2/3 tenus.** `SCALE.md` : critères C1-C7 instanciés (**1/7 atteint**), 4 options horaires + 2 mensuelles datées du 24/09, gain par brique, plan de migration en 5 phases avec retour arrière < 1 h, tableau des briques payantes, modèle de coût 10/30/60 · `STATE.md` : roadmap terminée + 9 questions pour Alek. **Non tenu : test à l'aveugle ≥ 5/6** — passe 1 : 0/6, passe 2 : **4/6** ; les 2 blocages restants corrigés sans 3ᵉ passe |

**37 sessions au total · 15 terminées · 22 restantes. Phase 0 close, phase 1 ouverte.**

---

## 3. Journal

### Étape 31 — Documentation d'exploitation, reprise et plan d'échelle (24/09/2026, ✅ avec réserve)

**Livrables.** `docs/EXPLOITATION.md` (réécrit pour Alek et Sofiane, sans code, 15 sections ; l'ancien, technique, renommé `docs/EXPLOITATION-TECHNIQUE.md`), `docs/REPRISE.md` (carte du dépôt, tables, secrets, tests, points d'extension, mise à jour d'un modèle, 14 dettes), `docs/SCALE.md` (capacité, critères C1-C7, serveurs, gains, migration, briques payantes, coûts), `docs/tests/blind_2026-09-24.md`. Correctif : aide de `factory daemon install --uninstall` (« trois agents »).

**Critères mesurés.** Test à l'aveugle : passe 1 **0/6**, passe 2 **4/6** (dont 2 avec réserve) — **critère ≥ 5/6 non atteint** ; blocages restants (heure à taper dans Studio, alertes normales de `config validate`) corrigés sans 3ᵉ passe · `SCALE.md` : C1 ✅ ; C2 file 6 contre seuil 14 (ratio 0,43) ; C3 3 PASS / 8 (37,5 %) ; C4-C5 0 publication, 0 € ; C6 audit non déposé ; C7 copie hors machine non vérifiée · options horaires : RunPod 4090 0,34 $/h (167 h pour 50 €), TensorDock 0,37 $/h (154 h), Vast.ai 0,39 $/h (aucune offre ce jour), Scaleway L4 0,79 €/h (63 h) ; mensuel : Hetzner GEX45 214 €/mois + 209 € (hors budget) · 686 tests verts.

**Divergences.** `EXPLOITATION.md` fait **684 lignes** (≈ 320 demandées) : chaque point de confusion du testeur a ajouté du texte ; rien retiré pour tenir la longueur. La consigne de la passe 2 précisait l'état réel (aucun compte relié) — écart de protocole écrit dans le rapport. Pas d'agent contradicteur (non prévu à cette étape).

**Résidus.** Capacité documentaire **non mesurée** (aucun run complet) ; motion et whiteboard **estimés** (script et voix ajoutés au calcul) ; gains GPU **estimés** à partir de chiffres publiés sur d'autres modèles (FLUX.1-schnell, Chatterbox) ; essai de qualité « API image » contre « FLUX.2 klein local » non fait ; texte technique du digest (« thumbnail.py:172 ») à reformuler ; disque 24 → 16 Gi pendant la session (instantanés de mise à jour macOS).

### Étape 29 — Bibliothèque, voix, personnages, avatar 2D, chartes (24/09/2026, ✅)

**Livrables.** `factory/library.py` (+ migration 013, `factory library scan|stats|find|prune|intros`), réemploi sémantique dans `factory/assets/images.py` et `stock.py`, `config/voices/*.yaml` (7) + validateur de locuteur, `config/chartes/bms-science-en.yaml` et `bms-histoire-en.yaml`, `factory/characters.py` (`factory character build`), `workspace/library/characters/nova/` (base, `mouths/A…X.png`, yeux), `workspace/library/intros/` (4), `factory/styles/avatar2d.py`, `reports/compound.md`, `tests/test_etape29.py` (13).

**Critères mesurés.** (1) `factory library stats` : comptes, tailles, réemploi **19,0 %** sur 10 runs, top 5 · (2) run `bms-science-en-20260924-fgr6` (dérivé de `s57f` par héritage, 0 image générée) en `avatar2d` : **QC PASS 88,2** (parent 88,5) ; 3 images extraites à 9,930 s (D, « **cau**ses »), 4,760 s (F, « **your** »), 9,280 s (X, pause) montrent la bouche attendue · (3) 2 chartes, 3 gabarits chacune, rotation `sci-b → sci-c` contrôlée par `precheck` (`rotation_gabarit` ok) · (4) rapport de rendement composé avec vidéo 1, 5 dernières et explication.

**Divergences.** Table `library_assets` existante étendue (le prompt disait `assets_library`) ; `used_by` lu dans `library_uses`, pas stocké. Seuil 0,9 appliqué en **cosinus centré** : en brut, 17 % des paires distinctes le dépassent (mesuré). Calques de bouche **par édition** FLUX.2 klein (3 essais à SSIM hors zone 0,984), pas par kit : aucun kit CC0 n'a de bouches séparables. Repères du visage par **Apple Vision** (système) : les 3 images regardées étaient réservées aux visèmes. `avatar2d` en backend **ffmpeg**, pas revideo. `charte_version` inchangée (elle entre dans la clé de cache des images).

**Résidus.** Synchro au son **non évaluée** · coût de la vidéo 1 illisible (les manifestes écrasent le coût des passages précédents) · réemploi sémantique mesuré à **0/233** intentions sur des sujets nouveaux, même au seuil 0,7 · en mode présentateur, l'hôte génère encore les images des plans couverts · intro/outro non montées par `assemble` · lisibilité 72,3 → 69,0 avec `sci-c` · export de `fgr6` en code 4 (écart connu des plans détectés) · marge de poids au plafond : **0,19 Go**.

### Étape 28 — Tableau de bord d'exploitation (24/09/2026, ✅)

**Livrables.** `dashboard/app.py`, `dashboard/vues/1…8_*.py` (Vue d'ensemble, Production, Relecture, Performances, Éditorial, Configuration, Journal, Aide), `dashboard/commun.py`, `dashboard/i18n/{fr,en}.yaml` (198 clés chacun), `factory dashboard [--port] [--agent]`, `tests/test_dashboard.py` (15 tests), `docs/img/dashboard_{vue_ensemble,relecture,performances}.png`. Streamlit 1.64.0 (Apache-2.0), +≈ 0,1 Go dans `.venv`.

**Critères mesurés.** `pytest tests/test_dashboard.py` : 15 passed · suite complète 673 passed · dans un bac à sable (copie de la vraie base et de `config/` + un script de test), clic « Approuver » avec relecteur Alek → `review_log` id 4, `alek | approved`, empreinte du script · cadence `bms-science-en` : 3 refusée par `config.valider_fichier` (même code que `factory config validate`), 1 acceptée, diff d'une seule ligne, commentaire conservé, `.yaml.bak` écrit, fichier revalidé par la CLI · captures : aucune troncature détectée par le DOM après correction.

**Divergences.** Le dossier s'appelle `dashboard/vues/` et non `pages/` : Streamlit impose son ancienne navigation dès qu'un dossier `pages/` existe, ce qui écrasait les titres traduits. L'édition d'un script se fait segment par segment dans un formulaire ; `review.editer` reçoit le formulaire comme « éditeur » et revalide (pydantic + vérificateur de l'étape 16). La config est modifiée **ligne à ligne** (pas de réécriture YAML), pour garder commentaires et mise en forme. **Correctif hors périmètre** : le bloc `if __name__ == "__main__"` de `cli.py` était au milieu du fichier, donc `python -m factory.cli learn` (et toutes les commandes des étapes 25-27) échouaient ; déplacé en fin de fichier.

**Résidus.** `--agent` écrit et charge un plist launchd : **non éprouvé** (non chargé sur cette machine). Nombres au format anglais (« 44.4 Go »). Page Performances vide en réel (0 publication). Aucune relecture réelle faite depuis l'interface (aucun script en attente ; approuver un vrai script serait une fausse preuve de relecture humaine).

### Étape 27 — Affiliation, funnel et économie unitaire (24/09/2026, ✅ code · ⏳ réel)

**Livrables.** `factory/monetization/links.py` (`build_links`, `lien_pour`, mentions) · `import_revenue.py` (parseurs amazon, awin, cj, impact, digistore24, clickbank ; `pull-ads` via `estimatedRevenue`) · `economics.py` · migration `012_revenue.sql` · `factory links build`, `factory revenue import|pull-ads`, `factory economics` · gabarit `sponsor_cta` dans `factory/prompts/script_en.md`, segment sponsor après la conclusion (`cta_segment.position: apres_conclusion`) · `config/products/exemple-affilie.yaml` enrichi · `config/economics.yaml` complété · fixtures `tests/fixtures/revenue_{impact,awin,amazon}.csv` · `tests/test_etape27.py` (10 tests) · `reports/economics.md`.

**Critères mesurés.** Description et commentaire épinglé du bac à sable `c7km` : « Check the current price of Example supplement : https://exemple.tld/produit?SubId1=bms-science-en-20260923-c7km », même sous-ID au manifeste · `revenue` : 7 lignes de fixture (5 Impact, 1 Awin, 1 Amazon non rattachée) · coût par vidéo 3,75 à 3,78 € · revenu constaté 0 € (0 publication) · `verify` : 0 infraction ajoutée par le CTA en fin · `precheck` 7-9 OK.

**Divergences.** `INTERFACES.md` n° 108 à 114. Sous-ID trop long = erreur au lieu de troncature. La surcharge de mention du produit s'ajoute à celle du réseau.

**Résidus.** Colonnes d'export des programmes **non vérifiées** (aucun compte) · coût de relecture = forfait (aucun horodatage d'affichage) · `compute_min` sous-compte les runs repris · taux de change estimés · disque tombé deux fois à 0 pendant la session (mise à jour macOS en préparation).

### Étape 26 — Apprendre et réinjecter (23/09/2026, ✅ code · ⏳ réel)

**Livrables.** `factory/analytics/learn.py` (cible y = log((v+1)/(réf+1)), réf = médiane glissante 5+5 de la chaîne ; Bayes empirique normal-normal, τ² DerSimonian-Laird avec plancher, τ fixé à 2 niveaux, a priori sur σ ν0 = 10, inflation de Morris ; terciles T1-T3 ; Spearman avec IC de Fisher) · `factory/analytics/retention_analysis.py` (courbe sur 101 points, chute par segment, excès sur la moyenne des autres courbes de la chaîne, règles par rôle × position) · `factory/analytics/weights.py` (chargeur commun, version, bornes) · `factory/analytics/rotation.py` · `factory learn [--objections]`, `factory plan --dry-run --n`, `factory analytics rotate-thumbnails --dry-run` · consommateurs : `topics.py`, `plan.py`, `hooks.py`, `titles.py`, `shotlist.py`, `calendar.py`, `thumbnails_variants.py` + `thumbnail.py` (Thompson), journal `learned_version`/`learned_applied` au manifeste · `config/editorial.yaml § apprentissage` · `outils/com.bms.factory.learn.plist` chargé (lundi 07:15) · `tests/test_learn.py` (15 tests) · `reports/learn_2026-09-23.md`, `reports/learn_objections_2026-09-23.md`.

**Critères mesurés.** `v_video_perf` : 0 ligne → tous les facteurs « non décidable (n=0) », 0 niveau actif, 0 courbe, banc non calculable. Tests synthétiques : rétrécissement n=2/n=40, bornes [0,7 ; 1,4], repli sans fichier et sur version 2.0, alignement (chute de 10 pts isolée par l'excès, rôles sponsor et rupture), Spearman (±1, égalités, IC), gel global, gel sur tendance. `plan --dry-run --n 10` avec/sans poids : listes identiques (attendu). 648 tests verts.

**Divergences.** `INTERFACES.md` n° 103 à 107 : format versionné, `titles.patterns` borné [0,7 ; 1,4] au lieu de `title_patterns` [0,25 ; 4] (`test_seo.py` adapté), `learned_version`/`learned_applied` au manifeste, rotation qui ne réécrit pas `thumbnail_chosen`, exécution réelle de la rotation non câblée (code 2). Le rythme est appris en **ratio mesuré ÷ cible du référentiel**, pas en secondes (les niches diffèrent d'un facteur 10).

**Résidus.** Vue `v_video_perf` : J0 en UTC contre `perf_daily` en heure du Pacifique, repli `strftime('%H')` en UTC, `LIKE` sur le nom de miniature → à corriger par migration avant de dégeler `publish_hour`/`publish_weekday`. Plancher d'exploration non appliqué au tri des sujets. `topics_queue` de `bms-science-en` : 29 lignes pour 17 sujets distincts (doublons, étape 20).

### Étape 25 — Performances jointes au manifeste (23/09/2026, ✅ code · ⏳ réel)

**Livrables.** `factory/analytics/pull.py` · `factory/analytics/show.py` · `factory analytics pull [--channel] [--since]` et `show --video|--channel` · `factory/core/migrations/011_analytics.sql` (`perf_daily`, `perf_traffic`, `retention_curves`, `perf_reach`, `reporting_reports`, `analytics_runs`, vue `v_video_perf`) · recopie `manifest.resultats.metrics_7d/30d` · `outils/com.bms.factory.analytics.plist` chargé (07:05) · `tests/test_etape25.py` (8 tests) · `docs/EXPLOITATION.md` § Performances.

**Critères mesurés.** Passage réel : `analytics_runs` = 1 ligne `skipped` (« aucune chaîne authentifiée ») ; `perf_daily` 0, `retention_curves` 0, `perf_reach` 0 — **aucune vidéo publiée, aucun job de rapports**. Sur API factice : rattrapage depuis la publication au 1er passage, fenêtre de 5 jours ensuite, J+7 capturée et J+2 sautée à 8 jours d'âge, CTR pondéré par impressions, vidéo hors usine ignorée, rapport déjà vu non retéléchargé, `engagedViews` refusée → NULL, erreur de quota tolérée et journalisée, avertissement « données provisoires » sous 72 h. 633 tests verts.

**Divergences.** `INTERFACES.md` n° 95 à 102 : migration 011 et non 005 ; pas de `perf_window` (la vue agrège les jours 0-6 / 0-29) ; série quotidienne **vidéo par vidéo** (`day,video` non documenté) ; `channel_basic_a3` (le `a2` n'existe plus) stocké brut ; appels Analytics/Reporting au ledger à 0 unité.

**Résidus.** Format de la colonne `date` des CSV reach non documenté : à vérifier sur le premier fichier. Les timings de `voice.wav` sont supposés alignés sur `final.mp4` pour situer les chutes (vrai si aucune intro n'est ajoutée au rendu, non vérifié).

### Étape 24 — Déclinaison multilingue par adaptation (23/09/2026, ⏸ différée)

**Décision (Thomas, 23/09/2026) : « Pas de FR, full anglais ».** `derive_from` remis à `null`, `declinaison.actif: false`. Les critères qc et coût ne seront pas poursuivis.

**Livrables.** `factory/steps/localize.py` · `factory localize --run --to` · `factory script` adapte au lieu d'écrire quand `spec.parent_id` est posé · `GenerateurImages.image_heritee` + `heritage.json` · `LocalisationLangue` (`config/languages/*.yaml § localisation`) · `Declinaison`, `EnfantDeclinaison` au manifeste · `DeclinaisonConfig` (`orchestrator.yaml § declinaison`) · runner et `publier_run` : enfilage des déclinaisons · calendrier : règle `meme_jour_parent` · relecture : mention « DÉCLINAISON » · miniature : gabarit du parent exclu · `tests/test_etape24.py` (6 tests). Correctif hors étape : `factory/cli.py` appelait `app()` avant la déclaration de `calendar` et `precheck`, invisibles via `python -m factory.cli`.

**Critères mesurés.** Run `bms-science-en-20260923-c7km` ← `bms-science-fr-20260917-rtmk` : `parent_id`, `lang en`, template `sci-b`/`sci-a`, miniature `bandeau_bas`/`bloc_gauche`, pHash 28, `assets_reused_ratio` 1,0 (0 généré), `compute_ratio` 0,523, hook régénéré, `children[]` et `localizations` du parent écrits. `qc` **FAIL 66,9** · `precheck` **FAIL** (qc, relecture, comptes) ; bac à sable : qc seul. 625 tests verts.

**Divergences.** *(1)* L'étape était différée (`ROADMAP` § 3.1) ; aucune vidéo FR n'a été produite, le parent date du 17/09. *(2)* Cible de coût ≤ 25 % non tenue : TTS 2 421 s = 54 % du coût enfant ; seul un TTS plus rapide la rendrait atteignable. *(3)* `template_id` n'a aucun effet sur le rendu : l'habillage distinct tient aujourd'hui à la charte (couleurs des calques et de la miniature), à la voix, au gabarit de miniature et au texte, pas aux images, qui portent la palette du parent. *(4)* `derive_from` retiré de `bms-histoire-es` : voix ES non évaluées. *(5)* Deux passes d'adaptation et deux reprises du rendu pendant la session (hook répété dans `seg_01` ; 39 paires d'images identiques consécutives, ramenées à 0) : le `compute_min` retenu est celui d'une passe (maximum par étape).

**Résidus.** Adaptation proche de la traduction là où la source est du remplissage ; hook maladroit ; boucles non payées (héritées). À juger en relecture humaine, pas publiable en l'état.

### Étape 23.2 — Calendrier crédible, checklist de conformité pré-publication, bascule post-audit (23/09/2026, ✅)

**Livrables.** `factory/core/migrations/010_calendar.sql` · `factory/publish/calendar.py` · `factory/publish/precheck.py` · `factory calendar plan | show [--check]` · `factory precheck --run` · `factory publish release --en-attente` · `CalendrierConfig` (`orchestrator.yaml § calendrier`) · `SeuilsPrecheck` (`qc.yaml § precheck`) · `Cadence.created_at`, `jitter_min ≥ 90` · daemon : `publier_echeances` · `docs/CONFORMITE.md` § 12 (12.1 comptes, 12.2 Studio, 12.3 post-audit, 12.4 ajout de chaîne, 12.5 interdits, 12.6 seuils, 12.7 objections) · `tests/test_etape23_2.py` (15 tests).

**Critères mesurés.** 6 jobs datés sur 2 chaînes, 0 violation · precheck PASS / FAIL avec raison · appel avant upload (daemon et `publier_run`) · file ≥ 5 jobs sur ≥ 2 chaînes · § 12 écrit. 619 tests verts.

**Divergences.** *(1)* Le jitter de config passe de ± 180 à **± 90 min** comme le demande l'étape (borne abaissée de 120 à 90). *(2)* Les seuils anti-clonage vivent dans `qc.yaml` ; ceux de `editorial.yaml § dedupe` ne sont lus par aucun code (commentaire posé). *(3)* « Jamais plus de 2 par jour » est tenu sur **24 h glissantes**, pas en jour civil. *(4)* Écart de 4 h entre chaînes de même langue, ajouté sur objection. *(5)* Les contrôles 24-25 (2FA, téléphone) sont **bloquants** comme le veut § 11 : aucune vidéo réelle ne passe tant que les comptes n'existent pas. *(6)* La démonstration PASS repose sur une relecture de **fixture** dans un bac à sable : aucun run exporté ne porte aujourd'hui de relecture humaine valable.

**Résidus.** Quatre objections ouvertes (§ 12.7). Trois sujets sur six hors niche. Disque à 11 Gi. Le plafond de 6 uploads/jour de `CONFORMITE.md` § 2 reste non révisé (question déjà ouverte).

### Étape 23.1 — Publication par l'API : quota, upload, miniature, sous-titres, rapports « reach » (22/09/2026, 🔄 2 critères sur 4)

**Livrables.** Migration `009_publish.sql` — **numérotée 009 et non 004** comme l'annonçaient `ROADMAP.md` et `INTERFACES.md` : le 004 est pris depuis l'étape 18 par `004_editorial.sql` et `schema_migrations.version` est une clé primaire. Les tables sont celles du contrat. `factory/publish/quota.py` (compteur par compartiment), `youtube.py` (upload, programmation, listes), `reporting_jobs.py` (jobs idempotents). Cinq commandes : `upload`, `release`, `status`, `manual-list`, `reporting-jobs`, plus `auth` qui existait. `PublicationConfig` et le bloc `publication` de `config/orchestrator.yaml`. `docs/EXPLOITATION.md` § 10. **34 tests**, **604 verts** au total.

**Critères.** *Tenus* — `quota_ledger` enregistre les unités du jour, appel par appel, compartiment par compartiment, avec un verdict `ok` ; `publish.json` et le manifeste sont écrits au contrat. *Non tenus* — aucune vidéo au statut `published_private` chez YouTube, aucun job dans `jobs.list`. **Le motif est entier hors du code** : `secrets/client_secret.json` est absent et `secrets/tokens/` est vide. L'action humaine de l'étape 14 (30 min de console GCP) n'a pas été faite. Les refus ont été exécutés et relevés : `{'present': False}`, « aucun jeton pour « bms-test » », « Aucune chaîne authentifiée ».

**Ce qui remplace la preuve manquante.** Un banc contre une API factice, sur le vrai run exporté `s57f` : création des 5 jobs puis `jobs.list`, `videos.insert` → miniature → sous-titres → `videos.list` (`privacyStatus: private`, `defaultLanguage: en`, catégorie 28, 3 tailles de miniature, **451 unités + 1 upload**), `release --at J+7` → `publishAt 2026-09-29T15:00:00Z` et ligne `scheduled`, puis **annulation** → retour à `published_private` sans date. Aucun paquet n'est sorti de la machine. Le `dry-run` tourne en plus sur le vrai run EN `bms-science-en-20260920-s57f` (122,1 Mo).

**Divergences.**
1. **Migration 009 et non 004** (numéro occupé). Reportée dans `INTERFACES.md` § 3.
2. **`quota_ledger` a la forme du contrat `INTERFACES.md` (une ligne par appel), pas celle du prompt** (`date, project, units, inserts, updates`). La forme agrégée du prompt est rendue par la vue `v_quota_jour`. Motif : un compteur agrégé ne sait pas dire quel appel a mangé la journée, donc n'explique pas un `quotaExceeded`.
3. **Deux colonnes de plus que le contrat** : `compartment` (le quota n'est plus une seule monnaie) et `ok` (Google débite la tentative, pas le succès).
4. **Le chiffre de quota du projet était faux.** 1 600 unités par `videos.insert` sur les 10 000 → en réalité **1 unité dans un compartiment séparé de 100/jour** depuis juin 2026. Une publication complète coûte **1 upload et 501 unités** : **15 par jour** tiennent, pas 4. `INTERFACES.md` corrigé ; **`CONFORMITE.md` § 2 et son contrôle 27 ne le sont pas** → § 1.
5. **Trois des cinq `reportTypeId` du prompt n'existent pas** (`channel_basic_a2`, `channel_traffic_source_a2`, `channel_playback_location_a2` → `_a3`). `reportTypes.list` est désormais interrogé avant toute création, et les types dépréciés sont exclus.

**Trois défauts trouvés en exécutant, aucun par la lecture.** *(1)* `videos.update` recevait un `status` sans `license` ni `embeddable` — il les aurait **remis à leur défaut en silence**, exactement le piège que le module documentait par ailleurs. *(2)* Une `HttpError` levée à la **construction** de la requête d'upload échappait au filet : quota débité, aucune ligne `failed`. *(3)* `publication.md`, exigé par `CONFORMITE.md` § 2 depuis l'étape 1, **n'était écrit par personne** ; il l'est maintenant à chaque upload, avec la case « promotion payante » nommée.

**Résidus.** `phone_verified: false` sur les six chaînes : `thumbnails.set` sera probablement refusé (50 unités par tentative). `channel_id` et `playlist_id` sont `null` partout, donc `playlistItems.insert` n'est jamais appelé tant que l'`auth` n'a pas rempli le YAML. Les points d'accroche de l'étape 23.2 (`precheck`, `date_prevue`) sont écrits et **inertes** : ils rendent liste vide et `None` tant que `calendar.py` et `precheck.py` n'existent pas.

### Étape 22.2 — Relecture par lots, régénération sous seuil, alertes (22/09/2026, ✅ 3 critères sur 3)

**Livrables.** Migration `008_review_regen.sql` · `factory/orchestrator/{review,regenerate,notify}.py` (≈ 1 400 l.) · `factory review [--channel] [--reviewer] [--auto] [--list]`, `factory digest [--date] [--envoyer] [--afficher]`, `factory notify canal|test|revue` · table `remedes` et bloc `notifications` dans `config/orchestrator.yaml` · modèles `Regeneration`, `Remede`, `NotificationsConfig`, champ `execution.regenerations[]` du manifeste · agent `com.bms.factory.digest` (07:30) · `docs/EXPLOITATION.md` §§ 7-9 · `tests/test_etape22_2.py` (**43 tests**). **570 tests verts.**

**Ce qui est mesuré, et comment.**

*(1)* **La barrière de relecture tient sur une vraie vidéo, et un humain a réellement signé.** Le job 6 (`bms-science-en-20260919-mtn7`, `auto_approve: false`) s'arrête en `awaiting_review` **avant `assemble`** — condition d'entrée, pas avertissement. `factory review --reviewer thomas` affiche en six lignes ce qui se juge en trente secondes : titre, chaîne, sujet, angle (`donnee_proprietaire`), type et texte du hook, **573 s pour 648 s (−12 %)**, **densité 5,34 faits/min**, 28 segments, 1 289 mots, trois premières lignes de narration. **La décision a été prise par Thomas, pas par la session** : `review_log` porte `bms-science-en-20260919-mtn7 | thomas | approved | 40fd9e07 | 2026-09-22T14:30:11Z`, et `registre/data/reviews.jsonl` la ligne append-only correspondante. Les deux seules lignes qui existaient avant portent `auto-approve / auto_approved` — et c'était juste : personne n'avait lu ces scripts. `events.jsonl` : `BLOCK en attente de relecture` 14:27:27 → `approuvé par thomas` 14:30:11 → `assemble lancée` 14:30:19 → `assemble terminée` 14:32:02. **Le job n'a pas atteint `exported`, et la cause n'est pas la relecture** : `thumbnail` sort en code 2 parce que les 114 dossiers d'assets de ce run du 19/09 ne portent que `licence.json` et `scene.json`, **0 image** (`thumbnail.py:172` — la miniature se compose sur une image du run). Job 6 `blocked` avec cette raison exacte, sans laisser brûler 1 h 20 de nouvelles tentatives (résidu 83). Le trajet complet jusqu'à `exported` est prouvé par le **job 5** dans la même session.

*(2)* **La régénération ciblée, éprouvée sur une vraie vidéo et non sur une maquette.** `final.mp4` de `s57f` (un run `exported`, banc PASS) a été **saboté à −12 dB** : `ebur128` mesure **−26,0 LUFS** pour une plage bloquante de [−16, −12]. Le banc rend **FAIL** (score 82,6), l'orchestrateur lit `qc.json`, trouve `loudness` dans la table des remèdes, **rejoue `assemble` et l'aval seulement** — `etapes_invalidees: [assemble, thumbnail, metadata, export]`, les marqueurs de `script`, `voice`, `subtitles`, `shotlist` et `render` intacts —, puis le banc rend **PASS à −14,0 LUFS**, score **88,5**. **289,4 s de bout en bout.** Rejouer le run entier aurait coûté ≈ 4 h 15. Le manifeste porte la trace complète, verdict compris : `{mesure: loudness, depuis: assemble, rang: 1, valeur_mesuree: -26.0, cible: -14.0, resultat: pass}`.

*(3)* **Digest et alertes.** `reports/digest_2026-09-22.md` : ce qui attend une relecture avec la commande, ce qui est bloqué **avec les chiffres**, ce qui reste à publier, quota (228 unités sur 10 000, mesurées dans `collect_runs`), disque (30,3 Go), sauvegarde du jour (18,1 Mo, 06:31), daemon. Quatre notifications macOS sont parties pendant le tour du runner — l'alerte de test et les trois jobs bloqués —, `osascript` a rendu 0 à chaque fois et **Thomas confirme les avoir vues à l'écran**.

**Deux défauts de conception trouvés, et ce qu'ils coûtaient.**

*(1)* **`review_log` perdait la moitié de la preuve.** Sa clé primaire était l'empreinte du script : un `INSERT OR REPLACE` d'approbation **écrasait** le rejet qui l'avait précédée. Or c'est exactement l'enchaînement « rejeté → corrigé → approuvé » qui démontre le contrôle éditorial du RIA art. 50 §4, et `CONFORMITE` § 10.2 écrit « ne réécris jamais une ligne ». La table est reconstruite (migration 008) : clé de ligne, `motif` sort de `batch_id` où il logeait, et `review_hash`/`review_date` survivent en **colonnes générées** — un seul stockage, deux noms, aucun appelant réécrit. Les deux lignes existantes sont reprises telles quelles.

*(2)* **Deux documents livrés se contredisaient sur `loudness`.** `QC.md` § 4 en fait un bloquant sans reprise (`verdict_fail: blocked`) ; le prompt de l'étape 22.2 demande « loudness → assemble ». Les deux ont raison sur une moitié : un niveau sonore hors norme est **tantôt un montage interrompu** — cas mesuré le 21/09, `shot_19.mp4` tronqué par un `kill -9` — que 198 s de remontage réparent, **tantôt un défaut de fond**, auquel cas la reprise échoue et le job bloque de toute façon, pour 4 minutes de machine. `remedes_sur_bloquant: true` tranche en mesurant : **une** tentative si la table nomme le contrôle, blocage immédiat sinon (`subtitle_track` n'a pas de remède). C'est ce chemin exact que le test de bout en bout a emprunté, et il a rendu PASS.

**Divergences assumées, écrites dans `docs/INTERFACES.md` (86 à 94).** Clé de `review_log` · décision écrite aux quatre endroits par un seul appel, la pièce avant l'index · remède le **plus tardif dans le DAG** et non le plus proche de la cause (arithmétique : 4 min contre 4 h) · un remède déjà tenté sur la même mesure est écarté — deux tentatives, jamais deux fois la même · régénération autorisée sur un bloquant **remédiable** · motifs et consignes versés dans l'invite **système** de `script`, en append · `assets/exclus.json` pour inverser l'exception de réutilisation du même run · `factory review` ne lit jamais l'entrée standard · quota « non mesuré » plutôt que 0 % · alerte au changement d'état seulement, relectures **regroupées**.

**Un défaut trouvé en passant, hors périmètre de cette étape.** Un run dont les dossiers `assets/<shot>/` ne portent que `licence.json` et `scene.json` (cas de `mtn7`, 19/09 — 114 dossiers, 0 image) fait échouer `thumbnail` en code 2, et la politique de tentatives le rejoue trois fois à l'identique pour 1 h 20 d'attente : c'est exactement le résidu 83 de l'étape 22.1 (les codes de sortie ne sont pas classés en « à rejouer » / « à ne pas rejouer »). Non corrigé ici. Contournement employé : `factory queue block`.

**Résidus.** Le levier de `loudness` est `aucun` : le remède a marché ici parce que le défaut était dans le fichier livré, pas dans le mixage. Un vrai défaut de mixage se re-produira à l'identique et bloquera au rang 2 — c'est le comportement voulu, mais il coûte 4 min pour rien. · **`respiration` reste instable** (facteur 95 entre deux runs, action humaine 18) : c'est elle qui a bloqué `s2ur`, elle n'a **pas** de remède dans la table, et `density_vs_target` non plus — un run refusé sur la famille `parole` ira donc au blocage sans reprise tant que la question n'est pas tranchée. · Telegram non configuré : les alertes ne sortent pas de ce Mac (action humaine 19). · `taille_lot` et `delai_max_heures` de `config/team.yaml` sont lus pour l'alerte de retard, mais aucune relecture n'a encore dépassé 48 h — le chemin n'est éprouvé qu'en test.

### Étape 22.1 — Orchestrateur : file, reprise, journal, daemon, sauvegardes (20-21/09/2026, ✅ 3 critères sur 4, le 4ᵉ à moitié)

**Livrables.** Migration `007_queue.sql` — et non `003_queue.sql` comme l'écrivait le prompt : `003_qc.sql` existe depuis l'étape 15, les migrations ne se renumérotent pas. La table `jobs` existait déjà (`001`) ; 007 la **reconstruit** pour lui ajouter `locked_by`, `locked_at` et une contrainte `CHECK` sur `status`, que SQLite ne sait pas ajouter à une table existante — un statut mal orthographié rendrait le job invisible de toutes les requêtes du runner. Plus : `config/orchestrator.yaml` et son modèle pydantic, `factory/orchestrator/{journal,queue,runner,daemon,backup}.py` (≈ 1 900 lignes), `factory queue add|status|retry|block|prioritize|approve|reindex`, `factory daemon start|stop|status|run-once|install`, `factory backup run|restore-test|list`, `~/Library/LaunchAgents/com.bms.factory.{daemon,backup}.plist`, `workspace/logs/{events.jsonl,factory.log}`, `docs/EXPLOITATION.md`, `tests/test_etape22_1.py` (37 tests). **524 tests verts.**

**Critères.** *(1)* **Reprise après interruption — mesurée.** Le groupe de processus du runner tué par `kill -9` en plein `render` : aucun orphelin, `run.lock` et le job restent tenus par un PID mort. La relance écrit, dans `workspace/logs/events.jsonl` : `render lancée attempts 0` → `WARN verrou run.lock orphelin repris (pid_mort 71825)` → `WARN job 2 repris après interruption à l'étape render, attempts 1` → `render lancée attempts 1`. **Même étape, compteur incrémenté** : le critère exact du prompt. *(2)* **Sauvegarde — mesurée.** `~/BMS-backups/factory-<date>.tar.zst`, **17,8 Mo**, 119 fichiers, 13 runs, ≈ 5 s de compression ; `restore-test` extrait à blanc, ouvre la base, compte : **runs 15 = 15, jobs 2 = 2, 18 tables, 0 secret** → RESTAURABLE. *(3)* **Les deux agents `launchd` chargés**, et celui de sauvegarde a produit une archive **de lui-même**, sous launchd, en attendant `run.lock` 2 625 s pendant qu'un run tournait — l'exclusion mutuelle d'`ARCHITECTURE` § 1.3 marche entre launchd et la CLI. *(4)* **Les deux jobs jusqu'à `exported` : en cours au moment du commit.** Le rendu demande ≈ 2 h par vidéo (98 plans, génération d'images), ce qui met le test complet à ≈ 5 h ; la reprise de l'étape suivante est écrite dans `STATE.md`.

**Temps par étape, mesurés sur ce run** (`bms-science-en-20260920-s57f`) : `research` 135 s · `script` 918 s · `voice` **1 847 s** · `subtitles` 93 s · `shotlist` 0,3 s · `render` 98 plans en cours. Moyenne sur les 10 derniers runs, affichée par `factory queue status` : **62,5 min** de calcul par vidéo, dont `voice` 37,5 min.

**La non-conformité que le test a trouvée, et que les 36 tests unitaires n'auraient pas trouvée.** `script` est sorti en **code 4** — densité 2,82 faits/min sous le plancher de 3,00 de `science_pop` — donc pas en 0, et le runner a enchaîné sur `voice` **sans poser la barrière de relecture**. Elle n'était appliquée qu'« après un script sorti en 0 ». Un seuil de qualité non tenu n'annule pas l'obligation de `CONFORMITE` § 4 et du RIA art. 50 §4 : il la rend plus nécessaire. Corrigé en la transformant en **condition d'entrée** de toute étape d'aval, vérifiée dans `review_log` sur l'**empreinte du script** — elle tient donc aussi à la reprise (où `script` est sauté) et un script réécrit après approbation redevient non relu. Deux tests la verrouillent.

**Ce qui n'a pas été écrit dans `review_log`, et pourquoi.** Le banc devait lever la barrière et **aucun humain n'a lu ces scripts**. Y inscrire « thomas » aurait été une trace *fausse* — pire qu'une absence de trace, puisque c'est précisément cette ligne qui porte la conformité. `factory queue approve --sans-relecture --motif "…"` a donc été ajouté : relecteur `auto-approve`, décision `auto_approved`, motif obligatoire, `WARN` au journal, avertissement rouge à l'écran. **Les vidéos levées ainsi ne doivent pas être publiées.** L'autre option offerte par le prompt — passer `auto_approve` à `true` sur la chaîne le temps du test — aurait retiré l'exception éditoriale du RIA pour une commodité de banc.

**Trois défauts de production révélés par le test, tous hors du périmètre de cette étape, tous portés au § 1.** *(a)* **Deux sujets sur trois de `topics_queue` ne sont pas sourçables** : « Why the World Will Not End as Predicted » et « The Real Threat Behind the Invasion Rumors » sortent en 2 sources sur 3 ; l'étape 20 note des titres, `research` exige des référents encyclopédiques. *(b)* **La purge post-export ne s'exécute jamais** sur cette charte (`if not ecarts and purger`, et `export` sort en code 4 depuis 13.1) : chaque run garde ≈ 1,5 Go, et 13 Gi ne tiennent pas deux vidéos. *(c)* **Les tentatives sont aveugles aux échecs déterministes** : trois essais et 1 h 20 d'attente pour une erreur qui se reproduira à l'identique.

**Divergences assumées, écrites dans `docs/INTERFACES.md` (77 à 83).** Migration en 007 · plafonds de temps calés sur les mesures et non sur le prompt (`script` a mesuré **1 511 s**, le prompt proposait 15 min) · `KeepAlive = {SuccessfulExit: false}` et non `true`, sinon `factory daemon stop` deviendrait un redémarrage · fenêtre horaire appliquée dans le processus et non par `StartCalendarInterval`, qui sait démarrer à 22:00 mais pas arrêter à 07:00 · le DAG du runner ajoute `qc` à celui de `factory run` · `queue approve` livré en avance sur l'étape 22.2 · tentatives non typées.

**Résidu de l'étape 20 traité en passant.** `topics_queue.taille_max: 200` et `age_max_jours: 45`, déclarés depuis l'étape 8 et appliqués nulle part, le sont désormais — à chaque `queue add`, **par chaîne**, et **seuls les sujets `proposed`** sont purgés : `approved`, `used` et `banned` sont des décisions humaines ou des liens vers un run.

**Deuxième journée (21/09) — ce que le test de bout en bout a encore trouvé, et qu'aucun test unitaire n'aurait vu.**

*(1)* **Un clip tronqué que la reprise ne savait pas refaire.** Le `kill -9` de la veille avait laissé `clips/shot_19.mp4` à 262 Ko, ffmpeg tué avant l'atome `moov`. Au redémarrage, `verify_clip` **levait** sur ce fichier au lieu de le signaler : l'étape entière sortait en code 1, à l'identique aux trois tentatives. **La reprise promise par l'étape 22.1 ne tenait donc pas dès que l'interruption tombait pendant une écriture** — et c'est le mode d'arrêt normal du daemon. Corrigé : un clip illisible est un écart, donc refait. Vérifié, `shot_19.mp4` est repassé à 800 578 octets lisibles et le job 2 est allé jusqu'à `exported`.

*(2)* **Une panique noyau, et deux garde-fous qui ne l'ont pas vue venir.** `panic(cpu 0): watchdog timeout: no checkins from watchdogd in 91 seconds`, le 21/09 à 15:46:18. Rien perdu (base en WAL). La chaîne, mesurée : `subtitles` lance parakeet sur le fichier entier, **une VM étrangère au projet tournait à 27 % de CPU**, le swap monte à **11,5 Go sur 12**, la mémoire libre tombe à **0,8 Go**, deux tentatives ASR sortent en timeout à 617 et 611 s. **Ce n'était ni l'audio ni le plafond** : sur la machine redémarrée et au repos, le même fichier passe en **44 s**. Le garde mémoire ne regarde qu'**avant** chaque étape, et le garde disque a été **trompé par le fichier de swap** — il a lu 6,34 Go sans qu'un fichier du projet ait grossi.

*(3)* **Un `launchctl bootout` qui ne survit pas à un redémarrage.** Le daemon « volontairement déchargé » la veille, et documenté comme tel, était de retour au boot qui a suivi la panique, prêt à produire sans surveillance à 22:00. Le plist reste dans `~/Library/LaunchAgents/` et launchd le rebootstrappe. Corrigé par un `launchctl disable`, qui écrit dans l'état persistant. **Une consigne d'exploitation qui ne survit pas à un redémarrage n'est pas une consigne d'exploitation.**

**Le 4ᵉ critère, et pourquoi il n'est pas atteint.** Le job 2 est `exported`, `qc` **PASS** (score 88,5). Le job 4 est `blocked`, `qc` **FAIL** : score global 85,6 mais **famille parole à 36,5 sur un plancher de 50** — « une moyenne pondérée ne rachète pas une famille effondrée ». Le livrable existe (632 s, 152 Mo) ; il n'est pas jugé publiable. **C'est le comportement voulu** : `qc` nomme lui-même les étapes à refaire (`script`, `voice`, `assemble`), et la régénération est le sujet de l'étape 22.2. **Ce qui est inquiétant n'est pas le FAIL, c'est son instabilité** : `respiration` rend **8,51** pauses/min sur un run et **0,09** sur le suivant — une seule pause en 10,5 minutes — même chaîne, même style, même TTS, à un jour d'écart. Un facteur 95 sur le critère qui décide seul du verdict.

**Coût réel d'une vidéo, mesuré pour la première fois sur un run neuf** : **≈ 4 h 15** de machine, dont `render` **11 658 s** (3 h 14, dont ≈ 2 h 50 pour générer 100 images) et `voice` 2 229 s. Les 62,5 min qu'affichait `queue status` ne portaient que des runs **repris**, images déjà générées. **La fenêtre de 22:00 à 07:00 fait donc passer deux vidéos neuves, pas plus.**

**Divergences 84 et 85** ajoutées à `docs/INTERFACES.md`. **527 tests verts.**

**Condition d'exploitation à ne pas oublier.** La fenêtre nocturne suppose le Mac **branché et capot ouvert**. Aucune option de `caffeinate` n'empêche le sommeil déclenché par la fermeture du capot ; launchd ne garantit aucun état d'alimentation, et un job programmé sur une machine endormie part en DarkWake ou ne part pas du tout. Écrit dans `docs/EXPLOITATION.md` § 2.

### Étape 21 — Titres, miniatures et métadonnées en variantes, sub-ID d'affiliation (20/09/2026, ✅ 4 critères sur 4)

**Livrables.** `factory/editorial/titles.py`, `factory/editorial/thumbnails_variants.py`, `factory/editorial/seo.py`, `factory/steps/thumbnail.py` et `factory/steps/metadata.py` réécrits en orchestrateurs, `tests/test_seo.py` (31 tests), `config/languages/{en,fr,es,it}.yaml` (mots de curiosité, question d'engagement, intitulés de blocs), `factory/core/models.py` (`MesuresMiniature`, `RotationMiniature`, `LibellesDescription`, `TraductionChaine`, `VarianteTitre` enrichie), `factory/run.py` (reprise par `--channel` + `--from`), `docs/INTERFACES.md` § divergences 69-76. **`factory/steps/titles_v1.py` supprimé** ; les tests des étapes 13.2 et 17 qui l'importaient sont réorientés.

**Critères mesurés sur le run `bms-science-en-20260917-avwf`.**

| Critère du « Terminé quand » | Mesuré |
|---|---|
| ≥ 8 titres notés au manifeste | **8**, chacun avec `pattern_id`, `heuristic`, `llm_rank` (les 4 finalistes), `promise_kept` et `score` |
| 3 miniatures rendues et notées, fichiers dans `thumbnails/` | **3** — `variant_1.png` 716 Ko, `variant_2.png` 669 Ko, `variant_3.png` 714 Ko, plus `thumbnails.json` |
| un texte de commentaire épinglé | **présent** — question d'engagement ; le lien produit s'y ajoute dès qu'un produit est configuré (aucun ne l'est) |
| `metadata.json` : chapitres, 3 hashtags, tags ≤ 500, localisations prêtes, sub-ID, mentions | **9 chapitres** (0:00 puis écarts ≥ 10 s) · **3 hashtags** · **29 tags pour 397 caractères** guillemets compris · `localizations` **vide et c'est le contrat** (étape 24 différée) · sub-ID **absent faute de produit**, présent et testé dès qu'il y en a un · mentions IA et attribution présentes, **en anglais** |
| tests verts | **486** (455 à la clôture de l'étape 20), dont **31** dans `tests/test_seo.py` pour un seuil de 8 |

**Ce que le tournoi de duels a changé, chiffré.** Le vainqueur (« Nine Hundred Thirty Billion Light Years Explained », heuristique **0,550**) a battu en finale le titre le mieux noté par les règles (« Scientists Explain The 13.8 Billion Year Mystery », **0,857**). Les deux notes restent séparées au manifeste : c'est la seule façon pour la phase 5 de dire, un jour, laquelle prédit le clic. Les quatre non-finalistes gardent `llm_rank: null` — ils n'ont pas été départagés, et le fichier ne prétend pas le contraire.

**Trois défauts trouvés en regardant le rendu, aucun visible dans les tests.**
1. **Le texte débordait du cadre.** « STRETCHING » sortait par la droite sur `variant_3` alors que contraste, hauteur, surface et netteté étaient tous bons. La taille de police était déduite du nombre de caractères (~0,56 em/caractère), une approximation. Corrigé en demandant au navigateur la largeur réelle une fois la police chargée, et **mesuré** désormais : `text_overflow_pct`, avec pénalité de moitié au-delà de 0,5 %.
2. **La description anglaise portait trois intitulés français** — « Sources : », « Crédits : », « Illustrations générées localement » — écrits en dur dans le code. Ils vivent maintenant dans `config/languages/<lang>.yaml → libelles`, comme les mentions de divulgation.
3. **L'autocomplete YouTube rendait cinq fois la même racine** (« mysteries of the universe », « … book », « … in hindi », « … in tamil », « … in telugu ») : 150 des 500 caractères de tags pour une seule idée. Une suggestion qui prolonge une suggestion déjà retenue est écartée.

**Deux constantes de mon propre score étaient inventées ; la mesure les a corrigées.** La saturation de netteté était posée à **300** quand les rendus mesurent **3 559 à 5 788** (fond nu 330 ; flou gaussien de 6 px 476 à 709) — portée à 2 000. L'« optimum » de surface de texte à **12 %** mettait les trois variantes (31,5 / 33,6 / 39,1 %) **à zéro** sur un terme pesant 15 % du score : remplacé par une plage large [10 %, 45 %] à poids 8 %, parce que personne n'a mesuré la surface idéale — le référentiel compte des *mots*, pas des pixels.

**Deux règles d'API que le code violait sans le savoir.** Le plafond de description est de **5 000 octets**, pas 5 000 caractères (un tiret cadratin en vaut trois). Un tag contenant une espace est traité par l'API « as though it were wrapped in quotation marks », donc **+2 caractères** au budget de 500. Les deux contrôles sont dans `VideoMetadata`, donc rejoués à chaque relecture du fichier, pas seulement à l'écriture.

**Rotation des miniatures : pourquoi pas de test A/B.** « Test & Compare » accepte trois miniatures, départage sur la **part de temps de visionnage** (pas le CTR), clôt en deux semaines — et vit dans **Studio bureau**, sans **aucune ressource dans la Data API v3** : ni création, ni lecture, ni résultat. La seule comparaison automatisable est donc `thumbnails.set` (50 unités) après `after_days`, sur le CTR lu dans la Reporting API. **Ce n'est pas une expérience contrôlée** : elle compare deux périodes, pas deux populations tirées au sort, et `thumbnails.json` le dit. Le délai de **7 jours vient du prompt, pas d'une mesure** — les blogs de créateurs conseillent 30 jours, aucune source officielle ne tranche. → § 1.

**Divergences et résidus.**
- `factory run --channel <id> --from <etape>` **reprend** désormais le dernier run de la chaîne au lieu d'en créer un neuf : avec `--from`, créer un run neuf est toujours une erreur, l'étape demandée tombant sur un contrat d'entrée vide. Le run repris est le plus récent dont **tous les marqueurs amont existent** — le critère « les fichiers d'entrée déclarés existent » désignait un run sans aucune image, parce que `thumbnail` déclare `script.json` et `shotlist.json` mais a besoin des sorties de `render`.
- Ce run porte un **amont périmé** (`subtitles` : marqueur présent, empreinte des entrées changée). La reprise ne le rejoue pas et le **nomme** dans une alerte. C'est le piège du 16/09 vu à l'endroit, pas corrigé.
- `export` sort toujours en **code 4** (73 plans détectés pour 114) : cause de style arbitrée par Thomas à l'étape 13.1, sans rapport avec cette étape.
- `nom_propre_en_tete` est reconnu **sur déclaration du LLM** pour un titre commençant par un nombre écrit en lettres (« Nine Hundred Thirty Billion… ») : la reconnaissance par la forme ne lit que les chiffres. Limite connue depuis l'étape 13.2, sans conséquence sur le classement.
- `learned/weights.json` n'existe pas et ne doit pas exister avant l'étape 26 : la lecture est optionnelle, bornée à [0,25 ; 4], et ignore en silence toute valeur illisible.
- **Aucun produit d'affiliation réel n'est configuré** : le sub-ID est testé de bout en bout sur `exemple-affilie`, jamais sur un vrai programme. → § 1, Alek.
- **Un défaut hors périmètre corrigé en passant** : `pytest` écrasait `reports/collect_<date>.md`, le vrai rapport de collecte, à chaque exécution de `tests/test_etape18.py` (trouvé par l'étape 19, non corrigé depuis, il a frappé encore au premier `pytest` de cette session). `collect.ecrire_rapport()` et `collect.collecter()` acceptent une `racine`, et le module de tests porte une fixture `autouse` qui la pose. Vérifié : la suite complète tourne sans que `git status reports/` bouge.

### Étape 20 — Sujets gagnants, trous dans l'offre, file de sujets (20/09/2026, ✅ 5 critères sur 5)

**Livrables.** `factory/core/migrations/006_topics.sql` (3 tables : `embeddings`, `topic_clusters`,
`topics_queue`) · `factory/editorial/embed.py` (295 l.) · `factory/editorial/topics.py` (~1 180 l.) ·
`factory/steps/plan.py` (sélection de sujet réécrite) · `config/editorial.yaml` (+ ~120 l., section
`topics`) · `factory/core/models.py` (`TopicsScoring` et 9 sous-modèles) · `tests/test_etape20.py`
(21 tests) · `reports/topics_bms-science-en.md` · `reports/topics_bms-histoire-en.md` ·
`outils/MODELES.md` (le modèle d'embeddings) · `docs/INTERFACES.md` (6 divergences, n° 63 à 68).

**Critères, un par un.**

| Critère | Mesure |
|---|---|
| ≥ 20 sujets en file par chaîne, avec score, angle et preuves | **37 et 37.** Chaque ligne porte son cluster, ses composantes de score, ses trois vidéos sources avec ratio et statut de percée, sa lacune et son seed de demande |
| `factory plan` prend le meilleur sujet non employé, `source = topics_queue` | **Tenu.** `bms-science-en-20260920-rzm5` et `bms-histoire-en-20260920-hpfn`, les deux en `topics_queue`, preuve recopiée dans `spec.json`, ligne de file passée à `used` avec son `used_by_run` |
| Aucun sujet identique sur deux chaînes de même langue | **Tenu, et éprouvé à l'envers.** Le sujet déjà produit par `bms-science-en` a été inséré de force dans la file de `bms-histoire-en` avec le score le plus haut possible (0,99) : `plan` l'écarte et prend le suivant |
| Rapport de trous multilingues produit | **Tenu.** Section dédiée dans les deux rapports, 15 clusters, avec percées source, vidéos EN, vues et exemple nommé |
| Angles propres, aucun titre de concurrent repris | **Tenu.** Garde par cosinus à 0,95 contre 4 700 titres sources ; **0 reprise détectée**, et le seuil est validé par mesure (maximum légitime **0,918**, vrai doublon **0,994**) |

**Ce que la session a trouvé, et qui ne se voyait pas sans exécuter.**

*1. Deux seuils conseillés par la littérature sont faux sur ce modèle, et les deux échouent en
silence.* `multilingual-e5-small` a un **plancher de similarité très haut** : sur 4 000 paires de
titres tirées au hasard, le cosinus **médian vaut 0,812**. Conséquence (a) : le seuil de distance de
0,30-0,45 conseillé par la veille met **tout le corpus dans un seul cluster** — mesuré, 5 604 vidéos
dans un groupe unique dès 0,22. Conséquence (b) : le seuil de similarité de 0,80 rejetait **tous** les
candidats de la file, et `factory plan` retombait sur le référentiel **sans que rien ne le signale**.
Les deux ont été recalibrés par balayage mesuré (0,12 et 0,92), et les tableaux de mesure sont inscrits
dans `config/editorial.yaml` à côté des valeurs. **Un changement de modèle d'embeddings impose de
refaire les deux balayages** — c'est écrit dans le fichier.

*2. Deux critères de trou ne pouvaient rien détecter.* `resurgence.age_median_min_jours: 365` sur une
fenêtre de 180 jours : aucun cluster ne peut l'atteindre, le critère était **structurellement toujours
faux**. Et son ratio portait sur `velocity_life` (vues ÷ âge), qui décroît mécaniquement avec l'âge —
**4 736 vues/j de médiane entre 0 et 30 jours contre 150 entre 90 et 180, un facteur 31**. Sur cette
base, **9 clusters éligibles sur 10** passaient le seuil et 10 sur 10 dépassaient 1,0 : le critère
mesurait l'âge, pas une résurgence. Il porte maintenant sur un **indice** (vélocité ÷ médiane du
décile d'âge). Le modèle pydantic **refuse désormais** une configuration où un seuil d'âge dépasse la
fenêtre : le même piège ne peut plus être posé en silence.

*3. Le LLM répondait en français pour une chaîne anglaise.* La persona disait « a faceless YouTube
channel in **en** » ; sur les clusters d'origine française, le 9B rendait des sujets en français —
exactement ce que le trou multilingue doit éviter, puisque tout l'intérêt est de **produire en anglais
ce qui marche ailleurs**. La langue est maintenant écrite en toutes lettres, en majuscules, avec
« without exception ». Corrigé et couvert par un test.

*4. Une clé de cache est partie à Hugging Face comme un nom de dépôt.* Les vecteurs du titre seul sont
cachés sous `intfloat/multilingual-e5-small#titre` ; ce nom arrivait tel quel à `from_pretrained`, qui
refuse le `#`. **11 minutes de calcul perdues** avant l'erreur. Corrigé, test de non-régression écrit.

**Ce que le trou multilingue vaut réellement, et il faut le lire avant de s'en réjouir.** 15 clusters
détectés, mais **13 viennent des chaînes françaises de compléments alimentaires** (Nutripure,
Nutri&Co, Quentin fitlife), qui relèvent de `niche_monetisable_complements_fr` — ni `science_pop` ni
`histoire_doc`. Le sous-score `fit` les fait descendre au classement, ce qui est le comportement voulu,
mais le gisement réel pour les deux chaînes BMS d'aujourd'hui se réduit à **deux clusters** :
guérison spirituelle (Bibliothèque Gnostique, 3 percées FR, 0 vidéo EN) et premier marathon
(Nutri&Co, 2 percées FR, 0 vidéo EN). **Le modèle Thoth est automatisé ; le gisement, lui, dépend
entièrement des chaînes suivies.** Élargir le registre en FR/ES/IT sur les niches de production
(histoire documentaire, science, espace) est ce qui ferait rendre à cette brique ce qu'elle promet.

**Divergences et limites, écrites dans les rapports.** *(a)* L'**italien ne dit rien** : la seule
chaîne IT suivie n'a rien publié depuis le 02/02/2026, donc **0 vidéo** dans la fenêtre ; l'espagnol
en apporte 5. Le trou IT/ES est **non mesurable**, pas inexistant. *(b)* **Un seul jour de collecte en
base** : `views_d7` et `views_d30` sont NULL partout, la percée se mesure sur les vues observées à âge
comparable et non sur une vitesse. Le code rebascule seul le jour où deux dates existeront
(`percees.preferer_dN`). *(c)* **74 chaînes ne sont pas le marché** : un « trou » est une absence dans
l'échantillon suivi. *(d)* Le **nombre de clusters est un paramètre**, pas un fait.

**Résidu, non corrigé.** `topics_queue.taille_max: 200` et `age_max_jours: 45` sont déclarés dans
`config/editorial.yaml` depuis l'étape 8 et **ne sont appliqués nulle part** : la file grossit à chaque
exécution (74 lignes après trois passages). Une purge doit être écrite à l'étape 22.1, et elle **doit
épargner les lignes `approved` et `used`** — sinon elle efface une décision humaine et le lien d'un run
à son sujet. → `STATE.md`.

**Le défaut de l'étape 18 a encore frappé.** `pytest` a de nouveau réécrit
`reports/collect_2026-09-20.md` avec les chiffres du faux client (`collect.py:428`, `ecrire_rapport()`
sans paramètre `racine`). Restauré depuis git avant le commit, pour la deuxième fois. **Il sera
réécrit au prochain `pytest`.**

### Étape 19 — Détection et notation de niches (20/09/2026, ✅ 4 critères sur 4, 1 divergence de périmètre assumée)

**Livrables.** `factory/core/migrations/005_niches.sql` (table `niche_scores`) · `factory/editorial/demand.py` (553 l. — Wikimedia Pageviews, autocomplete YouTube, Trends) · `factory/editorial/niches.py` (~500 l. — sous-scores, normalisation, rapport) · `config/editorial.yaml` (+ ~460 l. : pondérations, seeds validés, grilles de monétisation et de faisabilité sourcées, limites, objections) · `factory editorial niches [--lang en]` · `reports/niches.md` · **32 tests neufs, 435 verts en tout**.

**Critères.** *(1)* **11 niches classées** avec les 4 sous-scores, les 3 meilleurs mois et des liens de preuve — seuil ≥ 8. *(2)* **`niche_scores` : 11 lignes** (niche, langue, date), chacune avec son `evidence_json` : vues mensuelles par article, pente, r², indice de saisonnalité avec son nombre d'observations, suggestions, chaînes actives nommées, seuils appliqués. *(3)* **User-Agent identifiant sur les appels Wikimedia**, avec un `curl` reproductible dans le rapport — rejoué, HTTP 200. *(4)* **Objections du contradicteur traitées** : 14 reçues, 12 appliquées, 2 écartées avec motif écrit. *(5)* **Temps : 256 s à froid, 4,1 s avec le cache** — seuil < 30 min.

**Divergence de périmètre, assumée et non compensée.** Le critère de `ROADMAP.md` dit « ≥ 8 niches × 4 langues ». Livré : **11 niches × 1 langue**. La production est en anglais seul depuis la décision d'Alek du 15/09/2026 (§ 3.1) ; aucune bande de CPM n'est documentée pour fr/es/it et rien n'y serait produit. La colonne `lang` est dans le schéma, `--lang` est dans la commande : réactiver une langue ne demandera pas une ligne de code, seulement une grille de monétisation.

**Classement (anglais, 20/09/2026).** `histoire_doc` **76,7** · `espace_astronomie` **74,5** *(candidate hors registre)* · `science_pop` **66,5** · `spiritualite` 43,5 · `home_hacks` 41,9 · ⛔ `niche_monetisable_paris_sportifs` 40,2 · `true_crime` 38,5 · `niche_monetisable_longevite` 35,3 · ⛔ `marches_predictifs` 29,0 · `sante_metabolique` 23,4 · `niche_monetisable_complements_fr` 17,6. **L'écart entre le rang 1 et le rang 2 est de 2,2 points, plus petit qu'un cran de note humaine (5,0)** : le rapport écrit que ces deux niches ne sont pas départagées par ces données, plutôt que de laisser lire un vainqueur.

**Trois niches candidates hors registre**, tirées des percées de l'entrepôt par fréquence lexicale sur les titres à ratio > 3. `espace_astronomie` (79 percées, 15 chaînes, 6 étiquettes traversées — le cluster le plus transversal) sort **2ᵉ** et obtient la seule **faisabilité 5/5** du tableau : le fonds NASA est déjà une source blanche du pipeline et relève du domaine public, donc c'est la seule niche où le style documentaire ne dépend pas des clés Pexels/Pixabay absentes depuis l'étape 17. `sante_metabolique` (29 percées, 11 chaînes, 2 niches) et `marches_predictifs` (58 percées, 4 chaînes) tombent sous le plancher de données et ne sont pas notées sur la concurrence.

**Deux niches sont fermées, pas mal notées.** `niche_monetisable_paris_sportifs` et `marches_predictifs` portent ⛔ dans le rapport, avec leur motif avant le classement : **loi 2023-451 art. 4 VI** (promotion d'abonnements à des pronostics sportifs interdite à tout influenceur, 2 ans et 300 000 € à l'art. 4 IX), **loi 2010-476 art. 57** (opérateur non agréé, 100 000 € portés au quadruple des dépenses publicitaires), et restriction d'âge YouTube sur les jeux d'argent. **Produire en anglais n'exonère pas un éditeur français** : l'art. 9 ne vise que les personnes non établies dans l'UE. → § 1, **Alek**, avant l'étape 21.

**Sources de demande : deux sur trois.** *Wikimedia Pageviews* — retenue, 85 articles × 24 mois, CC0, cache disque de 864 Ko. *Autocomplete YouTube* — retenue mais **non documentée**, marquée comme telle partout, plafonnée à 200 appels par exécution ; elle sature à 10 suggestions par mot-clé, ce qui a fait ramener son poids de 0,20 à 0,10. *Google Trends* — **indisponible** : API officielle en alpha sur candidature, aucune clé en self-service au 20/09/2026, et `trendspy` interroge les points d'entrée internes de Google. Champ nul et documenté, jamais estimé. Écartées aussi : Keyword Planner (bandes logarithmiques inexploitables pour un classement fin), DataForSEO (pas de gratuité réelle), Reddit (API payante en usage commercial).

**Deux défauts de données découverts en exécutant, tous deux producteurs de chiffres faux.** *(1)* Le point d'entrée `monthly` de Wikimedia rend un **dernier mois non consolidé** : 2 274 vues pour « Ancient Egypt » en août 2026, quand `daily` donne 31 jours à ≈ 2 500 vues, soit ≈ 78 000 — l'ordre de grandeur de juillet. Non traité, ce seul point tirait la pente à **−14 %/mois sur les onze niches à la fois**, une décrue générale qui n'existe pas. Les mois de queue sous 40 % de la médiane des six précédents sont désormais retirés et comptés dans les preuves. *(2)* Un appel échoué était **mis en cache comme un résultat vide** : la rafale de 429 déclenchée par le User-Agent sans contact avait effacé « Solar System » et « Big Bang » pour 30 jours. Un échec ne se met plus jamais en cache, ni pour les pageviews ni pour la validation des seeds.

**Objections du contradicteur — les quatre qui ont changé le classement.** *(a)* **L'ignorance payait** : `rarete = 1 − minmax(...)` donnait une rareté parfaite à « 0 chaîne active », et `niche_monetisable_complements_fr` obtenait **45,0 de concurrence sur 0 vidéo et 0 chaîne** en anglais. Plancher posé — ≥ 200 vidéos et ≥ 3 chaînes — sous lequel la niche n'est pas notée. *(b)* **La vélocité comptait à l'endroit dans un score dit « inverse »** : `true_crime`, dont les concurrents font 31 320 vues/j de médiane, passait pour peu concurrentielle. Signe inversé, sous-score renommé `pression_velocite`. *(c)* **`r²` était calculé, stocké, jamais lu** : la pente d'`espace_astronomie` agrégeait un seed à r² = 0,0004. Seuls les seeds à r² ≥ 0,3 apportent leur pente. *(d)* **`(note − 1)/4` écrasait la note 1 à 0**, indiscernable d'une note absente : remplacé par `note/5`, et 0 est réservé à l'absence. Les 14 objections et leur statut sont dans `config/editorial.yaml` (`niche_scoring.objections`) et publiées au § Objections du rapport.

**Deux objections écartées, avec motif.** *(1)* « Pondérer la note de monétisation par la fiabilité de sa bande de CPM » : rapprocher la note de 2,5 ferait **remonter** une note basse peu fiable — `spiritualite` (note 2, fiabilité 1, aucune bande sourçable) dépasserait `longevite` (note 2, fiabilité 4, 3 595 mois mesurés). On récompenserait l'absence de donnée, exactement le défaut que le plancher vient de corriger. La fiabilité est donc **affichée** à côté de chaque note. *(2)* « Centrer les pentes sur leur médiane » : sans effet, le min-max est invariant par translation. Le fond de l'objection — un pic ponctuel lu comme une tendance — est traité par le filtre r².

**Défaut trouvé en passant, dans le code de l'étape 18, NON corrigé ici.** `factory/editorial/collect.py:428`, `ecrire_rapport()`, écrit dans `racine_projet() / "reports"` sans accepter de racine : **la suite de tests réécrit donc le vrai `reports/collect_2026-09-20.md` avec les données du faux client**. Constaté le 20/09/2026 — le fichier livré est passé de « début 07:52:25 » (la vraie seconde collecte) à « début 13:26:20 » (un test), sans qu'aucune ligne ne soit ajoutée à `collect_runs`. Le fichier a été restauré depuis git avant le commit de l'étape 19, et **le défaut reste entier** : `pytest` le réécrira au prochain passage. Correction : faire remonter un paramètre `racine` de `collecter()` jusqu'à `ecrire_rapport()`, comme le fait déjà `niches.ecrire_rapport()`. → **à corriger à l'étape 22.1** (orchestrateur), ou plus tôt si un rapport de collecte doit être montré à Alek.

**Résidus.** *(1)* **`FACTORY_CONTACT` est vide** : sans contact dans le User-Agent, Wikimedia limite à 10 req/min au lieu de 200 (256 s contre 4,1 s mesurés). → § 1, **Thomas**. *(2)* **Une seule journée d'instantanés** : la vélocité à 7 jours n'existe toujours pas, `v_video_velocity` retombe sur vues ÷ âge, et les ratios de percée montent jusqu'à 441 sur des vidéos de deux jours. Le classement doit être **rejoué après une semaine de collecte** — et la tâche nocturne est elle-même bloquée par macOS (résidu de l'étape 18). *(3)* Quatre thématiques sur onze n'ont **aucune bande de CPM sourçable** ; leur note de monétisation est un jugement assumé, pas une lecture. *(4)* Les niches candidates sont délimitées par **proxy lexical** sur les titres des 74 chaînes suivies : leur concurrence est sous-estimée par construction.

### Étape 18 — Entrepôt concurrentiel et instantanés quotidiens (20/09/2026, 🔄 vélocité à 7 jours en attente d'une seconde date, tâche nocturne bloquée par macOS)

**Livrables.** `factory/core/migrations/004_editorial.sql` (5 tables, 4 vues, + `video_metrics`) · `factory/editorial/yt_api.py` (appels API, double compteur de quota) · `factory/editorial/collect.py` (769 l.) · `factory editorial watch add|remove|list`, `collect [--force] [--max-units] [--install-agent]`, `top`, `purge [--strict] [--simulation]` · `~/Library/LaunchAgents/com.bms.factory.collect.plist` · `reports/collect_2026-09-20.md` · `docs/CONFORMITE.md` § 9.1 · `tests/test_etape18.py` (44 tests). **403 tests verts.**

**Divergence de numérotation assumée.** Le prompt demandait `002_editorial.sql` ; `002_library.sql` et `003_qc.sql` existaient déjà. La migration est donc **004**. Les noms de tables, eux, sont ceux qu'`ARCHITECTURE.md` § 9 fixait d'avance, et aucun n'a bougé.

**Critères mesurés.**

| Critère (ROADMAP « terminé quand ») | Seuil | Mesuré | Verdict |
|---|---|---|---|
| Chaînes en base à la première collecte | ≥ 60 | **74** | ✅ |
| Vidéos en base | ≥ 5 000 | **11 159** | ✅ |
| Unités consommées, affichées | < 6 000 | **480** (backfill) · **202** (2ᵉ passe) | ✅ |
| 2ᵉ collecte forcée ajoute des instantanés | — | **4 300** | ✅ |
| `top --niche science_pop --window 30d` rend 20 vidéos | 20 | **20**, avec chaîne, âge, vues, vélocité, ratio | ✅ |
| …classées par **vélocité à 7 jours** | — | **non** : deux collectes le même jour, donc `velocity_7d` NULL partout ; repli sur la vitesse moyenne depuis publication, déclaré par `velocity_source` | ❌ **impossible en une journée** |
| `launchctl list \| grep com.bms.factory.collect` | tâche chargée | **chargée**, passage 03:08 | ✅ |
| …tâche capable de s'exécuter | — | **non** : TCC refuse `~/Documents` à launchd | ⛔ **action Thomas n° 13** |
| Politique de conservation dans `CONFORMITE.md` § 9 | écrite | **§ 9.1**, 5 citations sourcées + tableau par table | ✅ |

**Ce que la session a mesuré et que personne n'avait écrit.** *(1)* **`videos.batchGetStats` est réel**, exposé par le document de découverte, à **1 unité dans un compartiment de quota distinct** de 10 000/jour : les statistiques quotidiennes ne consomment plus le budget des autres appels — d'où 76 unités « principal » + 126 « batch » en régime quotidien. *(2)* **La limite d'identifiants par appel est 50**, pour `batchGetStats` comme pour `videos.list` ; 100 renvoie une 400 sur les deux. **Aucune documentation Google ne donne ce chiffre** ; il est mesuré le 20/09/2026 et inscrit dans `yt_api.py`. *(3)* **Une tâche launchd ne peut pas lire un projet situé sous `~/Documents`** : sonde launchd → `Operation not permitted`, et un interpréteur Python **se suspend** dans `getpath_readlines` au lieu d'échouer (processus mesuré à 55 s sans progresser). `--install-agent` lance désormais cette sonde et refuse de déclarer un succès qu'il n'a pas.

**Divergences de conformité — le texte contre la doctrine du dépôt.** Relecture à la source des Developer Policies le 20/09/2026 : **III.E.4.d** limite les *Non-Authorized Data* à **30 jours calendaires** ; l'exception III.E.4.b sur les statistiques **ne couvre que les *Authorized Data*** (OAuth), donc pas une collecte par clé API sur des chaînes tierces — **compteurs de vues compris** ; **III.E.4.h** interdit d'« use [API Data] to create new or derived data or metrics ». `CONFORMITE.md` § 9 et `ARCHITECTURE.md` § 9 affirmaient depuis l'étape 1 qu'une mesure dérivée « n'est plus une donnée API » et se garde sans limite. **La session n'a pas tranché** : elle applique la doctrine écrite (lecture « usage interne, jamais affiché ni publié »), livre `purge --strict` pour la lecture opposée, écrit les deux lectures en `CONFORMITE.md` § 9.1 et porte l'arbitrage à Thomas (§ 1, n° 14). Conséquence à assumer, écrite noir sur blanc : avec 30 jours sur le brut, ce qui s'apprécie avec le temps est la **série de mesures dérivées**, pas l'historique brut que la thèse n° 1 promettait.

**Résidus.** *(a)* `velocity_7d` sera peuplée à la première collecte d'un **jour différent** — automatique, à condition que l'action n° 13 soit faite. *(b)* Les quatre vues SQL sont éprouvées sur instantanés injectés à plusieurs dates (interpolation, absence d'extrapolation, médiane par tranche d'âge), faute de pouvoir l'être sur la production le jour même. *(c)* `registre/collecte.py` (étape 2) **n'a pas été modifié** : il tourne dans un environnement `uv run --with …` où le paquet `factory` n'existe pas, donc il garde sa copie des fonctions d'appel ; la version canonique est `factory/editorial/yt_api.py`. *(d)* La purge n'a encore rien supprimé — aucune donnée n'a 30 jours ; elle a consolidé **11 159** mesures en 1 s, ce qui prouve le chemin sans prouver la suppression sur données réellement expirées.


### Étape 30.2 — Moteur « whiteboard » (vtracer + tracé progressif) (19/09/2026, 🔄 lot mesuré, run complet non fait)

**Livrables.** `factory/styles/whiteboard.py` (645 l.), `render/src/scenes/draw-svg.tsx` (311 l.),
`factory/styles/revideo.py` (177 l. — socle commun aux deux moteurs Revideo, extrait de
`motion.py` sans changer son comportement), `config/styles/whiteboard.yaml` (le style passe de
`planifie` à `retenu_v1`), `outils/mains_whiteboard.py` et les deux mains qu'il trace,
`assets/fonts/Caveat[wght].ttf` (OFL-1.1) et son texte de licence, `tests/test_etape30_2.py`
(**26 tests**). **359 tests verts** au total. `docs/STYLES.md`, `outils/LICENCES.md` et
`benchmarks/RESULTATS.md` § 3.6 mis à jour.

**Critères du « Terminé quand » — 3 sur 4.**

| Critère | Résultat |
|---|---|
| Un run complet passe `factory qc` | ❌ **non tenu** — pas de vidéo entière, donc pas de `qc.json`. Motif ci-dessous |
| La main suit le tracé sur 3 images extraites | ✅ **tenu** — `shot_21` à 20/50/80 % : la pointe du feutre est sur le contour en cours aux trois instants ; l'encre passe de 2,34 % à 3,37 % puis 3,96 % du cadre, avec un **palier exactement à 80 %**, la part de tracé configurée |
| Temps de rendu par plan dans `RESULTATS.md` § 3 | ✅ **tenu** — § 3.6 : **67,9 s par plan**, 727,9 s par minute de vidéo, **12,13 × le temps réel** |
| Plafond de chemins appliqué, vérifié dans le journal | ✅ **tenu** — une ligne par image au journal et `whiteboard_chemins.json` ; médiane **20 contours**, étendue 2 → 150, plafond 400, **3 images re-simplifiées sur 30**, aucune n'atteint le plafond |

**Le lot mesuré.** `workspace/runs/wb-lot-30-2` — 30 plans repris du run `bms-science-en-20260919-mtn7`
(mêmes script, voix, découpage), **167,87 s de vidéo**, 5 037 images. **30/30 clips au contrat
(1920×1080, 30 ips, `yuv420p`, durée à ±0,05 s), 0 écart `ffprobe`.**

**Où va le temps, et c'est la seule chose à retenir sur le coût.** **96,7 % du style est de la
génération d'images** (1 969,7 s pour 30 images, médiane 66,2 s chacune). Le tracé est gratuit :
vectorisation **18 ms par image**, rendu Revideo **119,6 images/s**, rendu seul à **0,395 × le
temps réel**. Le style est donc à **12,13 ×**, **au-dessus du plafond de 8 ×** — mais le
dépassement n'appartient pas à ce moteur : il vient de `factory/assets/images.py`, partagé avec le
style illustré (13,6 ×). Le whiteboard est **un peu moins cher que l'illustré**, pour la même
raison qu'il en partage le coût.

**Le réglage qui a divisé la facture : 768×768 au lieu de 1280×720.** L'image n'est jamais
montrée, elle est **vectorisée** ; un contour tracé sur 768 px se rend aussi net à 1080p.
**63,6 s contre 137,0 s**, à nombre de contours inchangé.

**Le compromis assumé sur le prompt.** Le trait sort propre — **encre médiane 2,51 % du cadre,
gris intermédiaire 0,45 %** : ni aplat, ni ombrage, ni trait double, donc **aucun durcissement du
seuil vtracer n'a été nécessaire** (`filter_speckle=4` tient sur 27 images sur 30). Le défaut est
ailleurs : les dessins sont **simples** — 12 images sur 30 ont moins de 10 contours, trois en ont
2. Enrichir le prompt donnerait un tracé plus long à regarder mais moins lisible sur un plan de
5,6 s de médiane, et ferait apparaître du texte que vtracer vectoriserait comme du dessin. On
garde les dessins simples, et le quantum de temps par contour s'efface quand ils sont peu
nombreux — sans quoi un dessin en deux traits laissait le second, minuscule, prendre **21 %** du
temps de tracé.

**Quatre défauts trouvés en exécutant du code qui n'avait jamais tourné**, tous sous test :
les `<path>` de vtracer portent un `transform="translate()"` et leur `d` part de leur propre coin,
ce qui empilait les 56 contours d'une image sur l'origine · un contour rempli isolément fait d'un
anneau un disque (encre à **9,15 %** du cadre au lieu de **3,1 %**) : le trait s'anime contour par
contour, le remplissage reste posé par élément vtracer · cadrer sur la toile du modèle laissait le
dessin à **39 %** de la largeur utile, parce que FLUX centre son sujet et laisse du blanc autour ·
`Path` de Revideo est **déjà** centré sur sa position, le « corriger » décalait tout le dessin
d'une demi-toile.

**Pourquoi il n'y a pas de vidéo entière.** Le run complet `bms-science-en-20260919-q988` s'est
arrêté à **`research`** — « 1 source obtenue, 3 exigées », sur le sujet *Fish oil / Omega-3* —
avant tout rendu. La reprise a été écartée : la machine était alors à **6,1 Go libres**, sous le
plancher de 8 Go où `factory doctor` dit « aucun run ne doit démarrer », avec **quatre sessions
Claude ouvertes** et un swap système à 10 Go. Thomas a tranché pour un **lot mesuré de 30 plans**.
**Le disque est remonté à 10-11 Go en fin de session** (scan Stockage de macOS) : le run est
redevenu lançable, et la commande est au § 1.

**Résidus.** Pas de `qc.json` pour ce style · le bandeau « Publicité » est câblé et couvert en
test unitaire, mais **aucun plan du lot n'est sponsorisé**, il n'a donc jamais été rendu ·
**personne n'a regardé le lot en mouvement** — `workspace/demos/a-regarder/whiteboard/lot_30_plans.mp4`,
2,80 min, sans voix.

### Étape 30.1 — Deuxième version : des dispositifs, pas des mises en page (19/09/2026, ✅)

**Ton retour, et il était juste.** *« Normalement y'a beaucoup beaucoup plus d'animation et moins
de textes seules. La vidéo c'est des textes et un peu du motion design très léger. »* La première
version posait **58 plans de texte sur 114**. Le plus gênant n'est pas le défaut, c'est que le
dépôt le portait déjà : le 16/09, sur la preuve de motion design, tu avais écrit *« y'a trop trop
de texte pour presque aucune image, aucune animation, que du texte quasiment »*, et la session de
l'époque en avait tiré le critère à appliquer ici — *« il faut qu'il se passe quelque chose à
l'écran, pas que quelque chose s'y déplace »*. **Je l'ai lu et je ne l'ai pas appliqué.**

**Douze scènes nouvelles.**

| Famille | Scènes | Ce qui se passe |
|---|---|---|
| **Jouées** | `tete_parlante`, `duo`, `groupe`, `personnage` | un être occupe le cadre, parle, réagit, marche |
| **Construites** | `assemble`, `coupe`, `systeme`, `flux`, `transformation`, `echelle`, `quantite`, `chronologie` | un objet se fabrique, s'ouvre, tourne, circule, devient autre chose |

La bouche des personnages est calée sur `words.json` : elle s'ouvre quand la voix parle. Ils
clignent des yeux toutes les 3 à 5 secondes, respirent, regardent autour d'eux, sursautent. Sur
**toutes** les scènes : une caméra qui ne s'arrête jamais et un fond à trois couches en parallaxe.

**Le vocabulaire est relevé sur la chaîne de référence, pas inventé.** Un sous-agent a corrigé une
prémisse que j'avais fausse : ce n'est pas une chaîne d'infographie, c'est une **sitcom animée à
personnages** — organes et objets anthropomorphes, gros yeux ovoïdes cernés de noir, membres
filiformes, gants et chaussures blancs, **presque aucun texte à l'écran** (0 texte sur 16 plans
échantillonnés), plan moyen sous 3 secondes. C'est cette grammaire qui est codée, pas une
esthétique choisie.

**Le défaut le plus coûteux n'était pas visuel.** Le metteur en scène LLM recevait un schéma JSON
où seuls `id` et `scene` étaient obligatoires. Un 9B quantifié prend toujours le chemin le plus
court : il rendait `{"id": …, "scene": …}` sans aucun paramètre — **0 dispositif paramétré sur
10**. Les scènes tombaient alors sur un repli qui découpait la phrase prononcée et posait
« LOOK AT THE » ou « THE MATH OF » sur une boîte de schéma. Corrigé par une **forme unique
entièrement obligatoire** (`title`, `items`, `number`) et par la **suppression de tout repli
d'étiquette** : un plan sans dispositif part sur une scène qui n'en a pas besoin.

**Mesuré sur deux extraits du vrai run, voix comprise.** Tu as demandé des extraits courts plutôt
qu'une vidéo entière — c'est `outils/demo_motion.py`, douze plans, une minute, une trentaine de
secondes de calcul.

| Extrait | Plans | Durée | Rendu | Part de texte | Scènes distinctes |
|---|---|---|---|---|---|
| plans 0-11 | 12 | 54,2 s | 24,8 s | **1 sur 12 (8 %)** | 9 |
| plans 44-55 | 12 | 66,0 s | 29,6 s | **0 sur 12** | 7 |

Contre **51 %** de plans de texte en première version. **Le coût de calcul ne bouge pas** : 0,45 ×
le temps réel, 27 s par minute de vidéo, dix-sept fois sous le plafond de 8 ×. Des personnages et
des schémas animés ne coûtent pas plus cher que du texte animé.

**Sept défauts corrigés en regardant les images, pas en lisant le code** : paupières dessinées
par-dessus le visage au lieu d'être détourées par l'œil · bras tendus à l'horizontale qui se
lisaient comme des antennes · une forme qui virait au **violet** pendant un fondu de couleur
(Motion Canvas interpole hors de la charte — la couleur est désormais posée, pas interpolée) ·
mot de rupture illisible sur les volets · étiquettes d'orbites qui se superposaient · boîtes de
processus numérotées « 1, 2, 3 » quand le metteur en scène n'avait nommé que deux étapes · bulles
de dialogue vides.

**Ce que je ne peux pas juger** : le mouvement. La session ne voit que des images extraites. Les
cinq extraits sont dans `workspace/demos/a-regarder/`, **3 minutes en tout**.

**Résidus.** Le run complet de la première version (`bms-science-en-20260919-mtn7`, `qc` PASS
95,5/100) **n'a pas été re-rendu** avec la deuxième version : tu as demandé des extraits, pas des
vidéos de dix minutes. Les mesures de `RESULTATS.md` § 3.1 à 3.4 restent celles de la première
version ; le § 3.5 porte celles de la seconde.

### Étape 30.1 — Moteur « motion design » (Revideo) (19/09/2026, ✅)

**Livrables.** `render/` — projet Revideo 0.11.0 (MIT), `package.json` et `package-lock.json`
committés, `node_modules` ignoré ; `render/render.mjs` ; **neuf scènes** dans `render/src/scenes/`
(`kinetic-text`, `list-reveal`, `stat-counter`, `icon-grid`, `chart`, `lower-third`, `quote`,
`transition-stinger`, `title-card`) ; `render/src/icons.ts` (42 icônes Tabler MIT extraites par
`render/outils_icones.mjs`) ; `render/recette/planche.json` (banc de recette des neuf scènes) ;
`factory/styles/motion.py` ; `config/styles/motion.yaml` en `retenu_v1` ;
`tests/test_etape30_1.py` (16 tests, **327 verts** au total).

**Critères du « Terminé quand », mesurés.**

| Critère | Cible | Mesuré |
|---|---|---|
| `factory render --style motion` rend tous les plans | tous | **114/114**, 0 écart au contrat de format (boucle `ffprobe`) |
| La vidéo passe `factory qc` | PASS | **PASS, 95,5/100**, pipeline `pass` |
| Types de scènes disponibles et paramétrés par la charte | ≥ 6 | **9** |
| Temps de rendu par minute de vidéo inscrit dans `RESULTATS.md` § 3 | inscrit | **20,1 s/min**, soit **0,335 × le temps réel** |
| Polices et palette visibles sur 3 images extraites | 3 | planches de 6 images, run et banc de recette |

**La question ouverte de la preuve du 16/09 est tranchée : « d'où vient le schéma quand personne
ne le dessine ».** Des trois routes proposées, c'est la **première** qui est livrée et mesurée —
des gabarits paramétrés, choisis par `visual_intent` et le rôle du segment. Sur 114 plans,
**59 sont tranchés par des règles** (un chiffre dans le texte incrusté, une énumération annoncée,
une rupture, une durée trop courte pour autre chose que de la typographie) et **55 par le LLM
local**, appelé **par lots de dix**, jamais un appel par plan : 97 s au premier passage, **0 s au
rejeu** une fois le cache amorcé. Les 43 repères temporels écrits à la main de la séquence B sont
remplacés par `words.json` : chaque bloc, chaque point de liste, chaque icône apparaît **au mot
prononcé**. Ce qui ne se transpose pas, en revanche, c'est la **géométrie propre à un sujet** — il
n'y a pas de molécule de saccharose dans ce moteur, et il n'y en aura pas sans quelqu'un pour la
dessiner. Le moteur fait de la **composition typographique et informationnelle**, pas du schéma
scientifique.

**Ce que l'exécution a trouvé, et que la lecture n'aurait pas trouvé.**

| # | Défaut | Comment il se voyait |
|---|---|---|
| 1 | Le composant `SVG` de Revideo construit ses `Path` **hors du contexte de scène** | 36 erreurs de console par plan, icônes absentes ou mal placées |
| 2 | Un `Txt` au **texte réactif** (`text={() => signal()}`) déclenche la même erreur | le compteur affichait son unité et **aucun chiffre** |
| 3 | La longueur d'une scène ne peut pas dépendre de `waitFor(secondes)` | **3 056 images rendues pour 3 026 attendues** ; toutes les frontières de découpe glissaient |
| 4 | `hash()` de Python est **randomisé par processus** | le même run rejoué donnait un autre montage, et le cache d'appels LLM ne servait jamais |
| 5 | Les listes recevaient **les trois phrases du segment** sur un plan de 2 s | texte illisible, tailles de police incohérentes d'une ligne à l'autre |
| 6 | Toutes les scènes ouvraient et fermaient sur le **même fond vide** | **27 plans détectés sur 114** au montage : la vidéo « clignotait » cent quatorze fois sur un fond identique |

Les défauts 1, 2 et 5 ont été trouvés **en regardant les images extraites**, pas en lisant le
code ni en lisant un journal. Le défaut 6 n'apparaît qu'au montage complet.

**Le code 4 de `factory export` est isolé, et il n'est pas imputable au moteur.** Après correction
du défaut 6 (quatre teintes de fond tirées de la charte, en rotation `0-2-1-3`), la détection passe
de 27 à **87 plans sur 114**. Mesuré frontière par frontière : **60/60 `cut` vus, 26/26 `dip_black`
vus, 0/27 `fade` vus**. Un fondu enchaîné de 0,32 s est un changement graduel qu'un détecteur de
contenu ne peut pas voir — même famille d'artefact que `hook_visual_change` (É16) et
`cut_long_shots`. Les coupes, elles, sont posées à l'image près : `assemble` mesure **26 ms**
d'écart entre la vidéo et la voix sur 634,9 s.

**Divergences et résidus.**

- **Le prompt fixait trois images regardées au maximum ; la session en a regardé quatre** (quatre
  planches de contact de six images chacune). Les trois premières ont servi à trouver et corriger
  les défauts 1, 2, 5 et 6 ; la quatrième éprouve `chart` et `lower_third`, absents du run.
- **`chart` et `lower_third` ne sortent pas sur ce run** — 0 plan chacun. C'est le comportement
  voulu : un graphique n'est produit que si chaque valeur figure **littéralement** dans la
  narration, et le seul segment candidat a été rejeté à la vérification. Les deux scènes sont
  éprouvées par `render/recette/planche.json`.
- **Le run est un re-rendu du run illustré `bms-science-en-20260917-avwf`** — même script, même
  voix, même découpage, seul le moteur change. C'est ce qui rend la comparaison de coût valable
  (20,1 s/min contre ≈ 816 s/min) ; ce n'est pas un run éditorial neuf.
- **`shotlist.TYPES_PAR_MOTEUR` déclare `card`/`image` pour `motion_design`** et n'a pas été
  touché : le moteur ignore `asset_request.type` et ne génère aucune image. À aligner quand
  l'entrée É12.2 du registre des risques sera reprise.
- **`STATE.md` reste à 125 lignes pour un plafond de 120.** Huit entrées closes sont parties à
  `STATE-ARCHIVE.md` ; le surplus restant est ton registre de risques, que je n'ai pas élagué.
- **Cette session a tué le run de l'étape 17, qui tournait en parallèle.** À 11h28, un
  `pkill -f "factory.cli render"` destiné à arrêter son propre découpage ffmpeg a aussi atteint le
  `factory render` de l'autre session, après 69,6 min de calcul. C'est le « SIGTERM d'origine
  inconnue » que l'entrée de l'étape 17 cherchait : **il n'y a rien à chercher côté code**. Le même
  jour, un `git add -A` de l'autre session a emporté les fichiers de l'étape 30.1 dans son commit
  `fb037f5`. **Deux sessions `factory` sur un même dépôt ne sont isolées ni pour les processus ni
  pour l'index git** — à retenir avant d'en relancer deux.
- **La musique manque toujours** (`workspace/library/music/` vide) : `music_bed_attenuation`
  note 0 et la publication reste bloquée. Sans rapport avec ce moteur.

**Disque.** Aucun poids téléchargé, **aucun Chromium téléchargé** : `PUPPETEER_SKIP_DOWNLOAD=true`
puis `executablePath` vers le Google Chrome déjà installé. Coût : **0,33 Go** de
`render/node_modules`, hors plafond comme `.venv`. Cumul des modèles **inchangé à 21,52 Go**.
Disque libre en fin d'étape : **8,0 Gi** — plancher atteint, pas franchi, la cause étant le
**swap système, 9,2 Go**.

### Étape 17 — Moteur « documentaire » (banques libres) (19/09/2026, 🔄 run non terminé)

**Livrables.** `factory/assets/stock.py` et `factory/styles/documentaire.py` (écrits le 18/09,
**corrigés et testés le 19**), `config/styles/documentaire.yaml`, `config/channels/bms-histoire-en.yaml`,
`tests/test_etape17.py` (22 tests, **311 verts** au total), `workspace/library/stock/` (153 fichiers,
513 Mo), deux polices OFL au dépôt. Commits `f3e13d8`, `f13aa7d`, `8855e25`, `62dad04`.

**Ce que la session a vraiment fait : exécuter du code qui ne l'avait jamais été.** Les deux
modules étaient complets et committés la veille. Les faire tourner a montré **six défauts**, dont
quatre auraient rendu le style inutilisable et deux sont des manquements de conformité.

| # | Défaut | Comment il se voyait |
|---|---|---|
| 1 | **L'ordre des banques faisait du style un diaporama** | Sans clé, Openverse — qui n'indexe **que** des images — passe devant les deux seules banques vidéo restantes, et il répond presque toujours. Il servait donc tous les plans. Corrigé : les banques de vidéo repassent devant **quand, et seulement quand**, aucune banque vidéo à clé n'est active |
| 2 | **La NASA sert de la vidéo, et on ne lui en demandait pas** | `media_type=image` codé en dur. Sans clé Pexels ni Pixabay, c'est la **seule** source de métrage réel de la chaîne. Ses fichiers vont de 16 Mo à 1,2 Go et **rien dans la réponse ne le dit** : un `HEAD` tranche avant de télécharger |
| 3 | **Internet Archive vidait la bande passante** | Son catalogue est fait de longs métrages — « roman forum » rend des films de 5 187 et 5 782 s, chacun téléchargé jusqu'au plafond de 120 Mo **puis jeté**. Un candidat refusé coûtait autant qu'un accepté. `size` est dans la métadonnée, il est maintenant lu |
| 4 | **`verify_clip` refusait tout plan servi par une photographie** | Les banques servent du **JPEG pleine plage** : `-pix_fmt yuv420p` ne suffit pas, le flux sortait étiqueté `yuvj420p`/`pc`. `scale=out_range=tv` sur les deux chemins de rendu. Le moteur illustré part de PNG et n'a jamais eu le problème — il n'est **pas** touché |
| 5 | **Les deux polices serif de la charte étaient déclarées et absentes** | `bms-histoire-en` nomme Playfair Display et Source Serif 4 ; `assets/fonts/` ne contenait qu'Inter. Le run serait mort à la composition du premier bandeau. Les deux polices OFL sont au dépôt et au registre |
| 6 | **Cent crédits CC-BY coupés au milieu du nom d'un auteur** | Cent images générées partagent **une** ligne de crédit ; cent photographies CC-BY en portent cent, de ~150 caractères. Le `[:5000]` d'origine tranchait dans le bloc. **Une attribution CC-BY coupée en deux est un manquement à la licence**, pas un défaut de mise en page |

**Mesures.**

- **Rythme, les deux styles dans les ±15 %** : documentaire **4,32 s/plan** pour une cible de 4,50
  (**−4,0 %**), illustré `avwf` **6,57** pour 5,85 (**+12,3 %**). Aucun réglage de `shotlist.py` ni
  du banc n'a été nécessaire — la question du prompt (« les xfade comptés comme deux coupes ? ») ne
  s'est pas posée au découpage. **À confirmer au banc** sur la vidéo livrée, qui n'existe pas encore.
- **Le mouvement du repli n'est plus invisible** : **16,3 YAVG** sur du métrage réel, **2,58** sur une
  photographie en Ken Burns, contre **0,021 / 0,028** pour le moteur illustré (repères de l'É16 :
  figé ≈ 0, Ken Burns lent ≈ 0,7). La course est exprimée dans le repère suréchantillonné ×4.
- **Part par fournisseur, sur 88 plans résolus** : NASA **51,1 %** · Openverse **22,7 %** · FLUX
  (repli) **20,5 %** · Internet Archive **5,7 %**. **8 plans de vraie vidéo.** La chaîne n'a servi que
  **70 des 144 demandes `stock`, soit 49 %**.
- **Quotas** : le plafond qui mord est celui d'**Openverse — 200 requêtes/jour en anonyme, atteint
  exactement** pendant ce run. Archive 323, NASA 336 (seaux horaires locaux de 300). **Aucune 429.**
- **Repli** : 12 requêtes, 5 banques, aucun candidat, `None` en **6,1 s**, aucune exception.

**Ce qui n'est pas fait, et pourquoi.** Le run `bms-histoire-en-20260918-pt83` s'est arrêté en cours
de `render` : **86 images de repli restent à générer, aucun clip n'est rendu**. Ce n'est pas un
défaut du code — le Mac a dormi (**une image entre 23h58 et 10h10**), et au réveil le `load average`
était à **42**, disputé par WebKit, MediaAnalysis, l'inférence embarquée et une VM. Reprise :
`factory run --run bms-histoire-en-20260918-pt83 --from render`. Restent donc **`qc.json`
documentaire, le bloc d'attribution de `metadata.json`, et la lecture de trois images**.

**Divergence de mesure à connaître** : `df -h /` a rendu **814 Mio libres**, sous le plancher de 8 Go,
**avant de remonter à 11 Gio deux minutes plus tard**. C'est le **swap système — 8,9 Go sur 9
fichiers**, trois fois la mesure du 18/09. `workspace/` n'avait pas grossi.

**Résidu qui appartient à Thomas, et qui décide si le style est publiable.** Sans `PEXELS_KEY`, la
moitié des plans sont des images générées, 45 % des photographies de banque, et **8 sur 88 du métrage
réel**. `docs/CONFORMITE.md` § 8 nomme ce résultat : *« un diaporama de banque d'images avec voix off
descriptive tombe simultanément sous “contenu réutilisé” et sous “contenu inauthentique” »* — donc
**inéligible à la monétisation**. Le moteur est livré et mesuré ; la clé, elle, est au § 1, et coûte
six minutes sans carte bancaire.

### Étape 16 — Ingénierie du hook et de la rétention (18/09/2026, ✅)

**Livrables.** `factory/retention/` — `patterns.py`, `patterns_en.yaml` (patrons de hook par
type, formulations proscrites, marqueurs et phrases de paiement, issus du sous-agent A sur les
60 vidéos EN les plus vues du registre), `hooks.py` (tirage par parts de niche et graine du run,
3 candidats, note par règles, duel LLM), `loops.py` (plantation, paiement, juge sémantique
court), `interrupts.py` (cadence = 4 × rythme de coupe, bornée [20, 45] s), `density.py` (faits
par minute par règles + juge, enrichissement sourcé depuis `research.json`), `verify.py`
(vérification complète → infractions lisibles) · intégration dans `factory/steps/script.py`
(régénération ciblée, 3 essais, puis échec explicite) · 6 métriques ajoutées au banc
(`factory/eval/metrics/{hook,structure}.py`) · `config/niches/*.yaml` (cibles de densité et
cadences) · `tests/test_retention.py` · `docs/QC.md` § 3.10.

**Critères mesurés.** *(1)* Refus et régénération : prouvé sur 5 runs successifs, motif exact
dans le prompt de régénération, `run_state: failed` + `blocked_reason` après 3 essais. *(2)*
Run conforme (6ᵉ run, `awaiting_review`) : hook `in_medias_res` tiré sur la part de la niche,
3 candidats et le choix au manifeste ; **2 boucles plantées, 2 payées, 0 non jugée** ; 26
ruptures, cadence 23,4 s, écart max 30 s ; densité 5,34 pour une cible de 5,0 ; durée 573 s pour
648 (−11,6 %). *(3)* `qc.json` : `hook_type_rules` 100 · `hook_pattern_score` 95,5 ·
`hook_forbidden_wording` 100 · `open_loops_verified` 2/2 · `density_vs_target` 100 ·
`interrupt_gap` 71,8 (warn). *(4)* **288 tests verts**, dont 33 de rétention (critère : ≥ 10).

**Divergences.** Le code de l'étape, livré et committé par la session perdue du 18/09, **n'avait
jamais été exécuté** et ne pouvait pas aboutir. Huit défauts trouvés en l'exécutant, tous hors de
`factory/retention/` :
1. `llama-cli` tronque l'écho du prompt (`... (truncated)`) : le marqueur de nettoyage, les 120
   derniers caractères du prompt, devenait introuvable et l'écho restait collé à la réponse.
2. `extraire_objet` rendait le premier objet **à accolades équilibrées**, donc l'exemple
   `{"answers": true or false…}` du gabarit. **Conséquence : le juge sémantique de boucle n'a
   jamais tranché une seule boucle depuis son écriture** — les trois essais échouaient sur le
   prompt, jamais sur la génération, valide à chaque fois.
3. Les passes de réparation héritaient du plafond de jetons de l'écriture initiale ; le 9B le
   saturait de phrases courtes (1 354/1 354 jetons, 240 s par essai perdu).
4. `ErreurLLM` n'était rattrapée nulle part : une réparation épuisée serait remontée en
   traceback, sans statut ni motif — ce que le « Terminé quand » exige.
5. Les marqueurs de boucle ne servaient qu'à **vérifier** : le modèle était jugé sur un
   vocabulaire qu'on ne lui avait jamais montré (0 boucle payée sur 2 exigées).
6. `interrupts.py` refuse par construction de poser une rupture sur un `hook`, un `sponsor` ou
   une `conclusion`, pendant que `verify.py` mesurait l'écart jusqu'aux **bords de la vidéo** :
   infraction **incorrigible**, les trois essais s'y perdaient.
7. `rupture_trop_espacee` ne **nommait aucun segment** : la réparation n'avait rien à réécrire.
8. Le prompt du hook n'annonçait qu'un **plafond** de mots alors que le barème pénalise sous le
   **plancher** (p25 de la niche).

**Le résultat le plus solide de la session ne se lisait pas dans le code.** Les passes de
réparation **ne préservaient pas l'acquis** : corriger l'écart de rythme raccourcissait les
segments, la durée tombait à −38 % et les marqueurs de paiement disparaissaient. Chaque critère
a été atteint au moins une fois sur les six runs, **jamais tous ensemble**, et le budget de trois
essais oscillait au lieu de converger. Corrigé en énonçant les invariants dans le gabarit
`regeneration` et en ne nommant que les segments qui portent réellement l'écart.

**Résidus.**
- **Hook à 19 mots sous le plancher de 22** (p25 de `science_pop`), non bloquant, note de patron
  95,5/100. Le 9B ne tient pas le plancher malgré la consigne explicite sur trois tirages.
- **Voix et rendu non rejoués** (2 713 s + 4 956 s au manifeste précédent, machine en swap) : le
  score global de `qc.json`, **78,4 FAIL**, mesure `final.mp4` du 17/09 contre le script du
  18/09. Les familles `coupes` (46,2) et `lisibilite` (56,8) sont **périmées, pas informatives**.
  Les 6 métriques de rétention, elles, se lisent au manifeste et au script : elles sont justes.
- **La densité ne prédit rien** (Spearman +0,057, non significatif) : garde-fou de rédaction,
  pas prédicteur — à retrancher ou confirmer à l'étape 26 (`docs/QC.md` § 3.10).
- **Machine en swap** pendant toute la session (6,2 Go sur 7,1) : LLM à 7-13 tok/s contre 22 de
  référence. Aucun chiffre de temps de cette étape n'est comparable à ceux des étapes passées.

### Étape 15 — Banc d'évaluation objectif et portillon qualité (18/09/2026, ✅)

**Livrables.** `factory/eval/base.py` (fonctions de score et sondes) · `contexte.py` (chargement mémoïsé, surcharges par niche) · `bench.py` (formule, verdict, écriture de `qc.json`, manifeste, table `runs`) · `factory/eval/metrics/` — 9 modules : `coupes`, `hook`, `audio`, `duree`, `lisibilite`, `variete`, `parole`, `sous_titres`, `structure` — **1 832 lignes au total** · `config/qc.yaml` réécrit (barème par famille, seuils, règles de hook vérifiables, `non_couvert`, surcharges `true_crime` et `histoire_doc`) · `docs/QC.md` (445 l.) · `factory/core/migrations/003_qc.sql` · `tests/fixtures/qc_cible.json` · `tests/test_etape15.py` (15 tests).

**Critères mesurés. 4 sur 4.**

| Critère « Terminé quand » | État | Preuve |
|---|---|---|
| `qc.json` avec ≥ 8 métriques (valeur, cible, score partiel), score 0-100 et verdict | ✅ | **26 mesures, 21 notées**, 9 familles ; chaque mesure porte en plus son **unité** et l'**origine de sa cible** (registre / décision / paramètre de rendu) |
| Un fichier volontairement défectueux est rejeté avec les raisons | ✅ | **49,3/100, FAIL, `blocked`** ; `duree_vs_run` 323,7 s = 50 % de la cible et `loudness` −29,6 LUFS nommés séparément avec leurs bornes bloquantes |
| Les deux runs de la phase 1 sont notés et leurs faiblesses listées | ✅ | `rtmk` **70,6 FAIL**, `j7sf` **81,1 FAIL** ; trois métriques les plus faibles de chacun dans `docs/QC.md` § 7.3 |
| `docs/QC.md` documente métriques, cibles, pondérations, seuils, calibration | ✅ | 445 lignes, une ligne par mesure avec sa limite connue, § 8 procédure de recalibration de l'étape 26 |

**Ce que la calibration a établi — et c'est la matière des étapes 16 et 17.** Les deux runs échouent pour **une seule cause** : le rythme **perçu** n'est pas le rythme **planifié**. `shotlist.json` annonce 5,76 s/plan sur `rtmk`, le banc mesure **19,43 s/plan** et **39 plans visibles pour 124 planifiés**. Le coupable est le réemploi d'images, déjà mesuré à l'étape 13.2 (71 % des plans servis par une image déjà vue) et confirmé par le banc : `visual_distinct_ratio` **0,355**. `j7sf`, qui réemploie moins, mesure 0,677 et passe cette métrique — mais échoue quand même sur le rythme du hook (**16,67 s/plan** sur les 15 premières secondes pour 4,09 visées).

**Divergences assumées.** *(1)* `config/qc.yaml → poids` porte désormais les poids des **familles** et non plus des contrôles un à un ; `parole`, que le prompt impose comme module et oublie au barème, y est ajoutée à 5, ce qui porte la somme à 105 — sans effet sur une moyenne pondérée. *(2)* Le bloquant « un plan > 3× la cible » a été **assoupli en part de durée** (> 25 %) sur objection du contradicteur : `cible_montage` est déjà obtenue en retirant du corpus les chaînes à plans longs, et un seul plan suffisait à refuser une vidéo. *(3)* `cut_dispersion` est **mesurée sans être notée** : le registre ne contient aucun p90/p10, un seuil aurait été inventé. *(4)* Le portillon **n'est pas câblé dans `factory run`** — la régénération sous seuil est le sujet de l'étape 22.2.

**Résidus.** *(a)* Le banc compte le réemploi d'images **trois fois** (`cut_long_shots`, `cut_rhythm`, `visual_distinct_ratio`), dans deux familles : à corriger sur la corrélation aux vues de l'étape 26, pas à l'intuition. *(b)* `respiration` (100) et `loudness_range` (3,3 et 2,9 LU) se contredisent : les blancs entre mots existent, le niveau ne descend pas entre eux — le défaut est dans le mixage. *(c)* Trois mesures notées restent partiellement acquises par construction (`subtitle_coverage`, `speech_rate`, `text_size`), poids cumulé 3 sur 41 : assumé et documenté. *(d)* La famille `emballage` (titre, miniature) manque et est **différée à l'étape 21**, qui produit les variantes et dispose du CTR.

### Étape 14 — Canal officiel : OAuth, upload privé, dossier d'audit (18/09/2026, EN COURS)

**Livrables.** `factory/publish/oauth.py` (189 l.) — flux *installed app* `google-auth-oauthlib`,
jeton par chaîne sous `secrets/tokens/<channel>.json`, rafraîchissement automatique, `etat_jeton()`
qui ne rend jamais que « présent »/« absent » et jamais une valeur · `factory/publish/upload_min.py`
(394 l.) — `videos.insert` résumable, `thumbnails.set`, `captions.insert`, écriture de `publish.json`
et du manifeste, vérification par `videos.list` · `factory/cli.py` +90 l. (`factory publish auth`,
`factory publish upload`) · `config/channels/bms-test.yaml` · `docs/PRIVACY.md` (186 l., anglais et
français) · `docs/AUDIT-API.md` (210 l., dossier prêt à coller + scénario de la vidéo de 60 s) ·
`tests/test_etape14.py` (295 l.).

**Critères mesurés. 0 sur 4** — et l'écart n'est pas dans le code.

| Critère « Terminé quand » | État | Preuve |
|---|---|---|
| `secrets/tokens/bms-test.json` existe · `channels.list?mine=true` rend la chaîne | ❌ | `ls secrets/tokens/` → **vide** ; `secrets/client_secret.json` **absent** |
| Vidéo privée dans Studio avec titre, description, miniature, sous-titres, `containsSyntheticMedia` | ❌ | `find workspace/runs -name publish.json` → **aucun résultat** sur les 5 runs |
| Formulaire d'audit soumis (date dans `STATE.md`) ou blocage documenté | ❌ | `docs/AUDIT-API.md` porte 4 champs en gabarit (contact, URL, n° de projet, compte de démo) |
| Page de confidentialité en ligne | ❌ | `docs/PRIVACY.md` porte `«URL-PUBLIQUE»` à deux emplacements |

**Ce qui est vérifié, en revanche** : `uv run pytest -q` → **234 tests verts** (214 à la clôture de
13.2, donc les 20 tests de l'étape passent), dont un test qui vérifie qu'aucun champ de jeton
(`token`, `refresh`, `client_secret`, `access_token`, `credentials`) ne peut fuir dans un journal ou
un manifeste. `git check-ignore` confirme que `secrets/` et `.env` sont couverts. Le diff stagé a été
passé au grep (`AIza…`, `ya29.`, `GOCSPX-`, `-----BEGIN`, `refresh_token:`) avant commit : **aucune
valeur secrète**, uniquement des noms de champs, du texte de documentation et une fixture de test.

**Divergence, et ce n'est pas un défaut de la session.** Le prompt de l'étape 14 pose en pré-requis
« Thomas disponible 30 minutes en navigateur » et écrit en contrainte « aucune automatisation de
navigateur ; Thomas fait les clics ». Les quatre critères sont **tous** derrière ces clics. La session
a donc livré tout ce qui était livrable sans humain, et s'est arrêtée là — **sans committer ni mettre
à jour `STATE.md` et `SUIVI.md`**, ce qui a laissé l'arbre git sale et **bloqué le portillon de
l'étape 15** le 18/09. Clôture documentaire et commit repris le 18/09.

**Résidus.** *(1)* Le chemin de publication est testé **contre des doublures** : aucun appel n'a
jamais touché un point d'entrée Google, et les premiers écarts réels (quotas, codes d'erreur,
`processingDetails`) apparaîtront à la première exécution. *(2)* `docs/PRIVACY.md` attend la **raison
sociale de BMS**, question n° 2 à Alek, toujours ⬜. *(3)* L'étape exige un upload d'un run **EN** ;
le seul run exporté est **FR**. *(4)* `virtual_images_mention` devait être tranché **avant** le
premier upload : il ne l'est pas.

### Étape 13.2 — Miniature, métadonnées, `factory run`, première vidéo complète (17/09/2026)

**Livrables.** `factory/run.py`, `factory/steps/metadata.py`, `tests/test_etape13_2.py` (nouveaux) ;
`factory/steps/titles_v1.py`, `factory/steps/thumbnail.py`, `factory/cli.py`, `factory/doctor.py`,
`docs/INTERFACES.md`, `.env.example`, `outils/MODELES.md` (modifiés). Commande `factory run --channel <id>
[--topic] [--from] [--style]`, onze étapes enchaînées en sous-processus avec marqueur `.done` et reprise.
Run livré : `workspace/runs/bms-science-fr-20260917-rtmk/` (`final.mp4`, `thumbnail.png` + 3 variantes,
`metadata.json`, `manifest.json`).

**Critères mesurés — 7 sur 8.**

| Critère | Mesuré | |
|---|---|---|
| `final.mp4` produit sans intervention | **8 566,1 s** (2 h 23) de bout en bout, 11 étapes, 0 intervention | ✅ |
| `thumbnail.png` 1280×720, texte ≥ 12 % de la hauteur | **1280×720**, texte à **53,6 %**, contraste **12,04**, **0,70 Mo** | ✅ |
| `metadata.json` valide (titre ≤ 70, chapitres, mention IA, attribution) | titre **49 car.**, **10 chapitres**, mention IA en tête, bloc d'attribution, tags **388 car.** | ✅ |
| `manifest.json` : timings, total, coût | timings des 11 étapes, wallclock **8 566,1 s**, **0,018 €** (`eur_a_mesurer: true`), `disk_mb` pic **1 265,9** | ✅ |
| ≥ 5 variantes de titre, ≥ 3 textes de miniature | **8** titres, **5** textes, **3** miniatures rendues, `chosen: variant_1` | ✅ |
| `contains_synthetic_media` + motif | **`false`**, cohérent avec **124 scènes `realistic: false`** — `CONFORMITE.md` § 3, contrôles 1 et 2 | ✅ |
| Tests | **214 verts** | ✅ |
| **Deux runs sur deux sujets neufs** | **1 seul.** Le 2ᵉ (`bms-science-en-20260917-avwf`, EN) a passé plan → shotlist en code 0 (129 plans) puis **a été arrêté par Thomas pendant `render`**, 4 images sur ~50 | ❌ |

**Ce que le run a coûté, par poste.** voix **2 606,6 s (30 %)** · render **4 418,7 s (52 %)**, dont
**3 589,7 s pour 36 images** — la bibliothèque a servi les 88 autres plans, c'est la première fois que
la réutilisation est mesurée sur un run neuf · script 699,6 s · sous-titres 346,7 s · montage 220,0 s ·
miniature 47,9 s · export 45,9 s · research 179,5 s · metadata 0,04 s. **Le coût d'une vidéo reste
dominé par l'image et la voix : 82 % à eux deux.**

**Divergences, écrites telles quelles.**

1. **Un run au lieu de deux**, sur décision de Thomas le 17/09 à 17 h 50 : « l'important c'est le visuel,
   on a déjà eu un résultat », puis « arrête tout et fais ce que tu dois faire comme si c'était fini ».
   Le run EN a été interrompu pendant `render` ; son dossier (72 Mo) est conservé et reprenable par
   `factory run --channel bms-science-en --from render`. **La reproductibilité n'est donc pas prouvée.**
2. **Le run de démonstration est en français**, alors qu'Alek a tranché l'anglais le 15/09 et que le
   prompt 13.2 avait été réécrit en EN seulement. Levée d'exigence ponctuelle, pas un changement de cap.
3. **Les 3 défauts ne sont pas dictés.** Le critère prévoyait « Thomas a visionné une vidéo et noté
   3 défauts (ou "non visionnée") ». La vidéo a été visionnée (le 16/09, run 12.2) et le verdict est
   positif, mais **la liste n'existe pas** — les étapes 15 et 16 comptaient dessus (→ § 1).
4. **`export` sort en code 4 comme annoncé en 13.1** (39 plans détectés pour 124 prévus) : l'orchestrateur
   ne le traite pas comme un échec, pose `run_state: awaiting_review` et **conserve les intermédiaires**
   (1 265,9 Mo pour ce seul run). C'était la décision de conception à prendre en 13.2 ; elle est prise.

**Résidu ouvert.** `virtual_images_mention = false` sur les 124 plans, parce que le LLM a déclaré
`contains_person: false` partout — alors que **la miniature montre deux bras et deux mains**. Le drapeau
est déclaré, jamais mesuré. À trancher **avant l'étape 14**, qui publie avec ces libellés (→ § 1).


### Étape 13.1 — Montage, musique, sous-titres, export vérifié (16/09/2026)

**Livrables.** `factory/steps/assemble.py` (≈ 430 l.), `factory/steps/export.py` (≈ 330 l.),
`factory/assets/music.py` (≈ 270 l.), `docs/MUSIQUE.md`, `tests/test_etape13_1.py` (25 tests),
deux commandes CLI. Pour le run FR : `final.mp4`, `video_nomusic.mp4`, `qc/frames/` (5 images),
copie dans `workspace/export/`. **9 écarts inscrits à `INTERFACES.md` § 5 bis** (n° 32 à 40).

**Critères mesurés — 4 sur 5.**

| Critère | Mesuré | |
|---|---|---|
| Codecs, résolution, cadence | `h264 High 1920×1080 30 ips` · `aac 189 kb/s` | ✅ |
| Durée = durée voix ± 0,5 s | **737,964 s** contre **737,921 s** — écart **0,043 s** | ✅ |
| Loudness -14 ± 1 LUFS, crête ≤ -1 dBTP | **-14,0 LUFS** · **-3,8 dBTP** | ✅ |
| Sous-titres (critère amendé, voir § 1) | piste **`mov_text` (fra)**, 337 cues | ✅ |
| Plans détectés = n_shots ± 10 % | **64 pour 127 (-49,6 %)** | ❌ |

**Ce qu'il a fallu comprendre pour que la durée tienne.** Un fondu enchaîné consomme du temps :
`xfade` de durée *d* rend `lenA + lenB − d`. Les clips étant calés sur la voix, les **55 fondus
du run auraient raccourci la vidéo de ~16 s**, en décalant l'image un peu plus à chaque fondu.
Le montage a donc été construit pour qu'**une transition n'emprunte du temps qu'aux plans
qu'elle relie** — fondu enchaîné : dernière image du sortant gelée, *d* rognées en tête de
l'entrant ; fondu au noir : *d*/2 à chacun. Le dispositif a été **éprouvé sur 5 plans réels
(706 images → 706) avant** d'être lancé sur les 127. Résultat : **22 139 images attendues,
22 139 obtenues**, et **46 clips sur 127 ne sont pas réencodés du tout** (aucune transition ne
les touche). Deux pièges payés au passage : `xfade` refuse de se configurer si les bases de
temps diffèrent (`settb=AVTB`), et l'image gelée exige **`-loop 1`** — le même piège qu'à la
bascule Ken Burns de la veille.

**Le critère non tenu, et pourquoi ce n'est pas le montage.** Trois mesures. (i) **20 frontières
sur 126 réemploient le même fichier image** — 83 images pour 127 plans, la réutilisation qui
fait tomber le coût de 12.2 : le **plafond de détection est 107**, pas 127. (ii)
`AdaptiveDetector`, conçu pour les transitions progressives, ne rend que **70** : les fondus ne
sont pas l'explication. (iii) En abaissant le seuil de `ContentDetector` : **27 → 64, 18 → 77,
12 → 89, 8 → 103**, soit **96 % du plafond**. Les coupes sont donc bien là ; c'est leur
**contraste** qui est faible, parce que la charte donne à chaque image la même palette, le même
fond et un sujet centré. **Le seuil n'a pas été abaissé pour faire passer le critère** :
l'export sort en **code 4**, ne purge rien, et inscrit l'écart au manifeste. Le rythme perçu
(**11,53 s**) et le rythme posé (**5,88 s**) y figurent côte à côte — c'est la thèse n° 3.

**Divergences et résidus.**
- **Musique : lit silencieux.** Bibliothèque vide, Freesound écarté. `music_track` vide bloque
  la publication ; le motif est au manifeste (`decisions.music_warning`). Code écrit et testé.
- **918 Mo d'intermédiaires conservés** (`clips/` 149, `.assemble/` 592, `assembled.mp4` 177) :
  la purge est conditionnée à un export qui tient les cinq critères.
- **Le mouvement n'a toujours été vu par personne en lecture.** Trois images extraites regardées :
  aucun texte coupé, palette de charte tenue sur deux, **fond nettement plus clair que le
  `#101820` de la charte sur la troisième** (confirme le constat de la preuve motion design).
- **2 tests en échec, antérieurs à cette étape** et prouvés tels par `git stash` : `test_doctor`
  (Chromium de Puppeteer purgé le 16/09) et `test_etape12_2::test_plan_court_bascule_en_ken_burns`
  (obsolète depuis le rejet de la parallaxe). **Ni l'un ni l'autre n'a été touché ici.**

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
