<role>
Tu es architecte technique senior et directeur de production média. Tu conçois des systèmes de production de contenu automatisés qui fonctionnent comme des actifs : ils apprennent de leurs résultats, s'améliorent seuls et gardent leur valeur quand leur créateur s'en va. Tu maîtrises l'outillage IA open-source auto-hébergé, l'économie de l'audience sur YouTube, et l'écriture de prompts de niveau production pour Claude Code selon les recommandations officielles d'Anthropic.
</role>

<mission>
Produire **un seul livrable** : le fichier `/Users/toms/Documents/Claude/Clients/Alek/Content-creation/ROADMAP.md`.

Ce fichier est une **roadmap d'exécution découpée en phases et en étapes**, où chaque étape contient le **prompt exact** à copier-coller dans une **nouvelle session Claude Code vierge**, plus le **budget de contexte estimé** de cette session.

Tu ne codes rien. Tu n'installes rien. Tu ne crées aucun autre fichier. Tu produis le plan que de futures sessions Claude Code exécuteront étape par étape.

Raison d'être de ce format : le projet est trop gros pour une seule session. Chaque étape doit tenir dans une session courte, se terminer par un livrable fichier persistant, et la session suivante doit pouvoir repartir de zéro sans aucune mémoire de la précédente.

**Niveau d'ambition.** Le commanditaire ne veut pas un script qui fabrique des vidéos. Il veut un **actif valorisable à plusieurs dizaines de milliers d'euros**. Lis `<these_de_valeur>` avant toute chose : c'est le critère qui doit arbitrer chacune de tes décisions de conception. Un plan qui produit un générateur de vidéos correct mais aveugle est un échec, même s'il est bien écrit.
</mission>

<these_de_valeur>
Un générateur de vidéos vaut zéro. L'assemblage LLM local + synthèse vocale + ffmpeg est reproductible en un week-end par n'importe quel développeur compétent. Si la roadmap ne produit que ça, elle a échoué.

Ce qui fait la valeur d'un tel système, par ordre d'importance :

1. **Savoir quoi produire.** Le choix du sujet pèse plus lourd sur le résultat que toute la qualité de production réunie. Une vidéo excellente sur un sujet sans demande fait 200 vues ; une vidéo médiocre sur un sujet porteur en fait 200 000. Le système doit donc contenir une **couche de décision éditoriale** : détection de niches, extraction des sujets qui performent réellement chez les concurrents, mesure de la demande, repérage des trous dans l'offre existante. C'est la brique la plus rentable et la plus souvent absente.

2. **Mesurer, et réinjecter.** Un système qui publie sans lire ses résultats est un tapis roulant. Un système qui récupère le taux de clic, la rétention et les vues de chaque vidéo publiée, les rattache au sujet, au titre, à la miniature, au hook et au rythme de montage employés, puis oriente les productions suivantes, **devient plus rentable à chaque vidéo**. C'est cette boucle qui transforme un outil en actif : sa valeur monte avec le temps au lieu de se déprécier. L'API YouTube Analytics est gratuite — il n'y a aucune excuse pour s'en passer.

3. **Ingénierie de la rétention.** Ce qui sépare CasiCreativo (704 000 vues sur 57 vidéos) de Health Snippet (89 900 abonnés, chaîne morte en janvier 2025) — les deux figurent au registre — n'est pas l'outillage. C'est la construction des trois premières secondes, la densité d'information, les ruptures de rythme et les boucles ouvertes. Ces éléments doivent être **paramétrés, générés et vérifiés automatiquement**, pas laissés au hasard du modèle de langage.

4. **La multiplication.** Un script produit une vidéo. Le même script traduit et re-voixé produit quatre vidéos sur quatre chaînes, pour environ 10 % de coût supplémentaire. C'est exactement le modèle observé au registre (Library of Thoth en EN / FR / IT, Gnose en FR / ES). Le système doit être **multi-chaînes et multi-langues dès l'architecture**, jamais en rustine ajoutée à la fin.

5. **La survie.** Un système qui fait bannir les chaînes a une valeur négative. Conformité aux règles YouTube sur le contenu généré par IA et le contenu inauthentique, droits sur la musique et les images, rythme de publication crédible, absence d'empreintes d'automatisation grossières : c'est une contrainte de conception, pas une case à cocher en fin de parcours.

6. **L'exploitabilité par un tiers.** Si seul Thomas sait le faire tourner, ce n'est pas un actif, c'est une prestation. Alek et Sofiane doivent pouvoir lancer, superviser et régler le système sans lire une ligne de code. Pilotage par fichiers de configuration, tableau de bord, journalisation lisible, documentation d'exploitation.

7. **Le rendement composé.** La vidéo n° 50 doit coûter moins cher et être meilleure que la vidéo n° 1 : bibliothèque d'assets réutilisables, voix et personnages cohérents d'une vidéo à l'autre, chartes graphiques par chaîne, modèles de montage éprouvés. Un système sans capitalisation refait le même travail à chaque fois.

**Règle d'arbitrage.** Chaque fois que tu hésites entre deux découpages ou deux priorités, choisis celui qui sert le plus les points 1, 2 et 3. La qualité de rendu brute passe après : une vidéo correcte sur le bon sujet avec le bon hook bat une vidéo splendide sur un mauvais sujet.
</these_de_valeur>

<contexte_projet>
**Le client.** Alek (associé : Sofiane), structure « BMS ». Demande textuelle d'Alek : *« We need the process of creating YouTube videos for almost 0$ and no employees. Completed workflow that are working by themselves in total autonomy. »*

**Le but business.** Vendre des produits et faire de l'affiliation via des réseaux de chaînes YouTube faceless. Aucun produit précis n'est fourni à ce stade : le système doit être générique et piloté par configuration, jamais construit autour d'un produit particulier.

**Le niveau de qualité exigé.** Alek : *« faut que ça soit au niveau des vidéos du PDF de Sofiane »*. Le registre est décrit dans `<references_pdf>`.

**Les styles visuels demandés.** Le système doit permettre de **choisir le style** selon la vidéo : whiteboard animé, motion design, images cartoon, animations poussées, vidéos réalistes, documentaire, avatar parlant. Le style est un paramètre du pipeline, jamais un embranchement du code.

**Le budget.** Alek a validé : *« 50€/mois approved, t'as ma carte pour ça »* — pour un serveur GPU. **Ce budget n'est débloqué que lorsque le projet sera à ~90 % terminé.**

**Phase actuelle : 100 % gratuit, 100 % local.** Tout tourne sur le MacBook Air décrit dans `<machine_cible>`. Aucun abonnement, aucune API payante, aucun crédit cloud, aucun essai gratuit exigeant une carte bancaire. Ni ElevenLabs, ni Runway, ni Midjourney, ni HeyGen, ni API OpenAI/Anthropic payante à ce stade.

**Ce qui déclenchera la dépense.** Le passage au serveur GPU (~50 €/mois) est justifié **uniquement par le volume de production**, jamais par la faisabilité. Corollaire structurant : **la démonstration complète doit tourner sur le Mac.** Si une étape n'est réalisable que sur GPU dédié, elle est mal conçue — il faut une variante locale dégradée mais fonctionnelle, le GPU n'étant qu'un réglage de qualité et de débit.

**Une limite déjà identifiée, à traiter franchement.** Thomas a écrit à Alek : *« ça ne sera jamais au niveau de Higgsfield pour les styles réalistes »*. C'est exact : la génération vidéo photoréaliste en local sur M2, et même sur un GPU loué à 50 €/mois, n'atteindra pas ce niveau. La roadmap doit **assumer cette limite et la contourner par la stratégie**, pas la masquer : les chaînes les plus performantes du registre (CasiCreativo, les réseaux Thoth) ne font pas de photoréalisme, elles font du motion design et de la voix off. Prévois une étape qui tranche explicitement quels styles sont tenables à quel niveau de qualité, avec des preuves visuelles, et ce qu'on répond à Alek sur le réalisme.

**L'exécutant.** Thomas, développeur depuis 8 ans, francophone. Il pilotera chaque session. Il n'a pas besoin qu'on lui explique ce qu'est un environnement virtuel ; il a besoin de prompts précis, de décisions argumentées et de critères de validation nets.
</contexte_projet>

<machine_cible>
- MacBook Air, puce **Apple M2**, 8 cœurs (4P + 4E), **16 Go de RAM unifiée**
- macOS 27.0
- **~30 Go d'espace disque libre seulement** (sur 228 Go) — contrainte dure et systématiquement sous-estimée
- Déjà installés : Homebrew, Python 3.9 (système), Node, ffmpeg, git, uv, Docker
- Absent : ollama, ComfyUI, tout modèle local

Conséquences à intégrer dans le plan, sans les contourner :
- Pas de CUDA. Tout passe par **Metal / MPS**, tourne en CPU, ou est remplacé par une approche non générative (compositing, templates animés, banques d'assets libres de droits — souvent le meilleur rapport qualité/coût, ne le néglige pas).
- 16 Go unifiés : le modèle, le système et l'application se partagent la même mémoire. Les modèles vidéo lourds ne passent pas tels quels. Il faut viser les versions quantifiées, les résolutions réduites, la génération par plans courts, ou d'autres techniques que tu dois faire identifier.
- 30 Go libres : **le poids disque de chaque téléchargement de modèle doit être annoncé dans le plan**, le cumul restant sous ~20 Go. Prévois une règle de gestion et de purge des poids.
</machine_cible>

<references_pdf>
Fichier : `/Users/toms/Downloads/REGISTRE-CHAINES.pdf` — titre interne « Rapport BMS », 4 pages, « Registre des chaînes examinées — P9 (30/08 → 11/09/2026) ». Registre de reverse-engineering produit par l'équipe de Sofiane : ~70 chaînes YouTube ouvertes, mesurées ou citées.

Contenu déjà extrait — le PDF n'est qu'un index de liens, il n'apporte rien de plus, ne perds pas de contexte à le rouvrir :

- **Réseaux reverse-engineerés.** Une même marque **clonée par langue** : Library of Thoth (EN, 398 vidéos, ~29K abonnés) / Bibliothèque de Thot (FR, 324 vidéos, 67,6K) / Biblioteca di Thoth (IT, 241 vidéos, 13,1K) ; Bibliothèque Gnostique (FR, 120 vidéos) / La Biblioteca Gnóstica (ES, 14 vidéos). Également : Gnostic Library, Enoch Discoveries, Hermetic Talk (hub de collaborations). Modèle noté : « funnel + collabs ».
- **Signaux de trajectoire, à exploiter comme des enseignements.** CasiCreativo English : 704K vues pour 57 vidéos, cité « référence DA », chaîne mère espagnole à 8,75M. Elias Yoder Amish : 345K, croissance explosive mai → août 2026, format avatar. Life According to Science : 80,7K en 12 mois, **en décrue**. Health Snippet : 89,9K, **chaîne morte en janvier 2025**. Ces quatre trajectoires opposées sur des formats voisins sont une matière première : le plan doit prévoir d'en extraire ce qui distingue une chaîne qui décolle d'une chaîne qui meurt.
- **Étude du rythme de coupe (29 chaînes, médiane secondes par plan).** La donnée la plus directement exploitable : Saving Savers 3,8 s · Khachakirner20 3,9 s · Elias Yoder 4,1 s (92 mesures) · Our History 4,4 s · InsightInfinite 5,2 s · BBC Earth Science 5,5 s · Frugal Solutions 5,7 s · Science Channel 5,7 s · Spark 6,0 s · Old Ways Chronicle 6,9 s · Space Matters 7,3 s · Wellness+Wisdom 7,8 s · Ty Notts 8,0 s · Silas Crowe 8,6 s · AB Documentary 8,6 s · Crime Is Fun 9,6 s · Daniel Moreno 11,4 s · People Pattern 12,6 s · Grandpa's Old Ways 14,1 s · Affinity Arc 15,0 s · Bruce Lipton 18,5 s · The History Channel 18,5 s · Now Next 18,5 s · Law&Crime 21,8 s · Fox News 48,0 s · Frozen Pennies 48,0 s · Homestead Tessie 60,0 s · Surviving The Survivor 80,0 s · Spiritual Dive 240,0 s. Labels de niche : `home_hacks`, `spiritualite`, `histoire_doc`, `science_pop`, `true_crime`, `yoder`, `moreno`, `frugal`.
- **Formats observés.** Faceless voix off ; persona avatar avec acteur payé (Daniel Moreno) ; animation d'organes et motion design (CasiCreativo) ; home hacks avec avatar (Elias Yoder) ; documentaire histoire ; science populaire ; true crime.
- **Niches monétisables scannées.** Longévité et biohacking EN (Huberman, Bryan Johnson, FoundMyFitness, Dr. Eric Berg…), paris sportifs EN (PickFinder, Juiced Bets, Clark Knows Ball…), compléments alimentaires FR (Nutripure, Nutri&Co, Novoma, Vincent Biohack, Quentin Fitlife), peptides USA (Dr. Ashley Froese, Doctor Youn, Dr. Paul Anderson). Terrains d'affiliation visés.

Comment t'en servir : ce sont des **cibles produit mesurables**, pas de la décoration. Le rythme de coupe doit être un paramètre par niche appliqué au montage puis vérifié sur le rendu. Le clonage multilingue doit apparaître comme levier de volume dans l'architecture. Les 70 chaînes constituent le **corpus d'entraînement éditorial** du système : la roadmap doit prévoir de les exploiter systématiquement (sujets qui performent, structures de titre, motifs de miniature, formats de hook), pas seulement de les citer.
</references_pdf>

<contraintes_dures>
1. **0 € de dépense** sur toute la phase couverte. Un outil est éligible s'il est open-source ou gratuit, installable en local, et **utilisable commercialement** — vérifie la licence de chaque outil et de chaque modèle recommandé. Certains modèles de génération portent une licence non commerciale : c'est éliminatoire ici, et tu dois le signaler explicitement.
2. **Tout tourne sur le Mac M2 16 Go / 30 Go libres.** Aucune étape ne peut dépendre d'un GPU NVIDIA.
3. **Autonomie totale visée** : zéro employé, workflows qui tournent seuls. L'humain arbitre au niveau de la configuration et du contrôle qualité par lots, jamais plan par plan.
4. **Multi-style, multi-chaînes, multi-langues** : trois paramètres de configuration, jamais trois branches de code.
5. **Budget contexte par étape** : cible ≤ 30 %, plafond absolu 40 % (voir `<budget_contexte>`).
6. **Chaque prompt est autonome** : la session qui l'exécute démarre vierge, sans mémoire des précédentes. Le prompt doit indiquer quels fichiers lire pour se recontextualiser.
7. **Démonstration de bout en bout tôt.** Une vidéo complète, même imparfaite, doit sortir à la fin de la phase 1 — avant toute optimisation module par module. Un plan qui construit dix modules parfaits avant le premier rendu complet est un mauvais plan.
8. **Conformité YouTube dès la conception** : règles sur le contenu généré par IA et le contenu inauthentique, droits musique et images, rythme de publication crédible. Traité comme contrainte d'architecture, pas comme vérification finale.
</contraintes_dures>

<budget_contexte>
Pour chaque étape, estime le pourcentage de fenêtre de contexte que sa session consommera, et montre-le décomposé.

**Fenêtre de référence : 200 000 tokens = 100 %.** Exprime chaque total **en tokens et en pourcentage**, pour que le calcul reste valable si la fenêtre change.

| Poste | Coût estimé |
|---|---|
| Overhead de démarrage Claude Code (system prompt + outils + CLAUDE.md) | ~18 000 tk (9 %) — incompressible, à compter dans **chaque** étape |
| Le prompt de l'étape lui-même | nombre de mots × 1,4 |
| Lecture d'un fichier | ~1 tk / 3,5 caractères → 200 lignes ≈ 2 500 tk · 500 lignes ≈ 6 500 tk · 1 000 lignes ≈ 13 000 tk |
| Une recherche web (requête + extraits) | 3 000 – 6 000 tk |
| Récupération d'une page web complète | 2 000 – 10 000 tk |
| Commande shell à sortie courte | 200 – 800 tk |
| Commande shell verbeuse (install, build, ffmpeg, pip) | 1 000 – 4 000 tk → **règle à inscrire dans les prompts : rediriger vers un fichier de log, n'afficher qu'un `tail`** |
| **Rapport final d'un sous-agent** | **800 – 2 500 tk** |
| Écriture d'un fichier de 300 lignes | ~4 000 tk |
| Raisonnement et réponses intermédiaires | **+25 % appliqués au sous-total**, en marge de sécurité |

Formule : `total = (somme des postes) × 1,25`, puis `% = total / 200 000 × 100`.

**Le levier central.** Un sous-agent lit des dizaines de fichiers et fait des dizaines de recherches **dans sa propre fenêtre**. La session principale ne reçoit que son rapport final. Une veille qui coûterait 60 000 tokens en direct coûte ~2 000 tokens déléguée. C'est ce qui permet de tenir sous 30 % tout en travaillant en profondeur : tes prompts doivent l'exploiter systématiquement pour tout ce qui est exploratoire.

Si une étape dépasse 40 %, **découpe-la** en `Étape N.1` / `Étape N.2` plutôt que de rogner sur la qualité du travail, et indique le point de reprise.
</budget_contexte>

<usage_sous_agents>
Pour chaque étape, précise quels sous-agents lancer, combien, et ce que chacun rapporte.

- **Délègue tout ce qui est exploratoire** : veille d'outils, comparaison de solutions, lecture de documentation, exploration d'un dépôt, vérification de licences, analyse de chaînes concurrentes, extraction de données depuis le web.
- **Garde en session principale** : décisions d'architecture, écriture des livrables, tout ce qui exige la vue d'ensemble.
- **Parallélise** : les sous-agents indépendants sont lancés en un seul envoi, jamais en série. Inscris-le dans les prompts.
- **Impose un format de sortie court et structuré** à chaque sous-agent (par exemple : « 400 mots maximum, format : recommandation / alternatives écartées et pourquoi / poids disque / licence / commande d'installation / risque principal / source »). Un sous-agent sans format imposé renvoie un pavé qui annule l'économie de contexte.
- **Un sous-agent rapporte, il ne décide pas.** L'arbitrage revient à la session principale.
- **Prévois des sous-agents contradicteurs sur les étapes structurantes.** Sur les décisions d'architecture et les validations qualité, un agent dont la mission explicite est de chercher les failles du plan proposé — dépendance cachée, coût réel, point de rupture à l'échelle — vaut mieux que trois agents qui confirment. Inscris ce rôle dans les prompts concernés.
- **Dimensionne** : 3 à 5 agents pour une veille large, 1 à 2 pour une vérification ciblée. Pas de déploiement à 15 agents pour comparer deux bibliothèques.
</usage_sous_agents>

<regles_ecriture_des_prompts>
Les prompts de la roadmap sont le cœur du livrable. Applique les recommandations officielles d'Anthropic en prompt engineering :

1. **Rôle explicite** en ouverture, aligné sur la tâche.
2. **Contexte et motivation** : dis *pourquoi* la tâche est faite et à quoi le résultat servira. Un modèle qui comprend l'objectif décide mieux sur les cas non spécifiés.
3. **Balises XML** pour séparer les blocs (`<contexte>`, `<demarrage>`, `<sous_agents>`, `<tache>`, `<contraintes>`, `<format_sortie>`, `<criteres_de_validation>`, `<fin_de_session>`). Elles évitent la confusion entre instructions, données et exemples.
4. **Instructions positives et explicites** : décris précisément ce qu'il faut faire plutôt qu'une liste d'interdits. Ne laisse aucune décision importante implicite.
5. **Raisonnement avant action** : demande explicitement de réfléchir et de planifier avant d'écrire du code ou de lancer des installations, surtout sur les étapes d'architecture.
6. **Exemples quand le format compte** : montre un exemple court d'un JSON de configuration ou d'une structure attendue plutôt que de la décrire.
7. **Format de sortie spécifié** : noms exacts des fichiers, chemins absolus, structure attendue.
8. **Critères de succès mesurables** : chaque prompt se termine par un « terminé quand… » vérifiable objectivement — un fichier existe, une commande retourne 0, un MP4 de N secondes se lit, un test passe, un score dépasse un seuil. Jamais « quand c'est bien ».
9. **Preuve avant déclaration.** Inscris dans chaque prompt l'obligation de vérifier avant d'annoncer un succès : exécuter la commande, ouvrir le fichier produit, mesurer. Et de rapporter l'échec tel quel quand il survient. C'est la règle qui empêche un plan de s'effondrer trois étapes plus loin.
10. **Conditions d'arrêt et garde-fous** : que faire si un outil ne s'installe pas, si un modèle ne tient pas en mémoire, si une piste est un cul-de-sac. Donne une porte de sortie plutôt que de laisser l'agent boucler.
11. **Hygiène de contexte** : logs redirigés vers fichiers, pas de lecture intégrale quand un extrait suffit, délégation aux sous-agents, résultats écrits dans des fichiers plutôt que dans la conversation.
12. **Reprise à froid** : chaque prompt commence par les fichiers à lire pour se recontextualiser (typiquement `ROADMAP.md` partiellement + `STATE.md` + les livrables de l'étape précédente), et ces lectures sont comptées au budget.
13. **Mise à jour de l'état** : chaque prompt se termine par la consigne de mettre à jour `STATE.md` — ce qui est fait, ce qui est décidé, ce qui bloque, quelle question reste ouverte. C'est la mémoire entre sessions.

Écris les prompts **en français**, à la deuxième personne du singulier, prêts à copier-coller sans retouche. Aucun placeholder du type `[à compléter]` : si une information manque, le prompt doit dire comment l'obtenir.
</regles_ecriture_des_prompts>

<phases_et_domaines_obligatoires>
Organise la roadmap en **phases**, chacune close par un **jalon de phase** : un critère vérifiable sans lequel on ne passe pas à la suivante. Tu choisis le découpage en étapes à l'intérieur des phases, leur ordre et leur regroupement — c'est ton travail d'architecte.

**Phase 0 — Fondations et faisabilité réelle**
- Exploitation du registre : extraire des 70 chaînes les paramètres reproductibles (rythme de coupe par niche, structure narrative, durée, ton, type de hook, direction artistique, structures de titre, motifs de miniature). Produire un référentiel exploitable par le code, pas une note de synthèse.
- Analyse des trajectoires opposées du registre : ce qui distingue une chaîne qui décolle d'une chaîne qui meurt, sur des formats voisins.
- Veille et sélection des outils open-source par brique : LLM local, synthèse vocale, génération d'images, génération et animation vidéo, whiteboard animé, motion design, sous-titres, montage automatisé, miniatures.
- Faisabilité mesurée sur M2 16 Go : ce qui tourne, à quelle vitesse, à quel poids disque, à quelle qualité. Chiffres mesurés, jamais supposés.
- Arbitrage explicite sur les styles : lesquels sont tenables en local et à quel niveau, lequel ne l'est pas (le photoréalisme), et quelle réponse est faite à Alek.
- Installation et configuration de l'environnement retenu.

**Phase 1 — Pipeline v1 et première vidéo**
- Architecture de bout en bout : idée → recherche → script → découpage en plans → assets visuels → voix → montage → sous-titres → miniature → métadonnées → export. Interfaces entre modules définies avant le code.
- Moteurs de style interchangeables pilotés par configuration.
- Modèle de données : une vidéo, une chaîne, une niche, un style, une langue — décrits comme structures versionnées, pas comme variables éparpillées.
- **Jalon : une vidéo complète sort du pipeline, de l'idée au MP4 final.**

**Phase 2 — Qualité mesurable et rétention**
- Banc d'évaluation : un outil qui note objectivement une vidéo produite face aux cibles du registre (rythme de coupe, durée, densité de coupes, lisibilité du texte, niveaux sonores, présence et forme du hook) et produit un score. Sans mesure objective, la qualité progresse au feeling et stagne.
- Ingénierie du hook et de la rétention : construction des premières secondes, ruptures de rythme, boucles ouvertes, densité d'information — générés puis vérifiés automatiquement.
- Portillon de contrôle qualité : critères de rejet automatique avant publication. Rien ne se publie sans passer le score.

**Phase 3 — Intelligence éditoriale**
- Détection et notation de niches : demande, concurrence, potentiel de monétisation, saisonnalité.
- Extraction des sujets qui performent chez les concurrents et repérage des trous dans l'offre — à partir du registre puis au-delà. Outils gratuits uniquement : à faire identifier et vérifier par sous-agents.
- Génération et sélection de titres et de miniatures, avec un mécanisme de variantes et de comparaison.
- Référencement : métadonnées, description, chapitres, liens.
- **Cette phase est celle qui crée le plus de valeur. Ne la traite pas comme un accessoire du pipeline.**

**Phase 4 — Autonomie et publication**
- Orchestration : file d'attente, exécution par lots, reprise après erreur, journalisation, planification, supervision.
- Publication automatisée sur YouTube, gestion multi-chaînes, calendrier de publication crédible.
- Déclinaison multilingue d'une même production — le levier de volume du registre.
- Conformité : contenu généré par IA, contenu inauthentique, droits musique et images, sécurité des comptes.
- **Jalon : une série de vidéos est produite et publiée sans intervention humaine.**

**Phase 5 — Boucle de rétroaction et monétisation**
- Récupération automatique des performances publiées (API YouTube Analytics, gratuite) et rattachement de chaque métrique aux choix de production correspondants : sujet, titre, miniature, hook, rythme, style, langue.
- Exploitation de ces données pour orienter les productions suivantes. C'est le mécanisme qui fait monter la valeur du système avec le temps.
- Intégration des liens d'affiliation et du funnel dans le pipeline de publication.
- Attribution du revenu et économie unitaire : coût réel par vidéo, revenu par vidéo, par niche, par langue. Sans ça, impossible de savoir où investir.

**Phase 6 — Industrialisation et transmission**
- Tableau de bord d'exploitation utilisable par Alek et Sofiane sans lire de code.
- Bibliothèque d'assets réutilisables, cohérence des voix et des personnages, chartes graphiques par chaîne : le rendement composé.
- Documentation d'exploitation et de reprise.
- Passage à l'échelle : critères chiffrés déclenchant l'achat du serveur GPU ~50 €/mois, quel serveur, quel gain de débit mesuré, quel plan de migration, quelles briques payantes envisager alors (voix premium et assimilé) avec leur retour attendu.
</phases_et_domaines_obligatoires>

<structure_du_fichier>
`ROADMAP.md` doit suivre exactement cette structure :

1. **Titre et résumé exécutif** (10 lignes maximum) : ce que le système fera, la contrainte 0 €, le jalon serveur.
2. **Thèse de valeur** (15 lignes maximum) : pourquoi ce système est un actif et non un script, et ce qui doit primer en cas d'arbitrage. C'est ce que relira toute session qui hésite.
3. **Contexte figé** : demande du client, contraintes machine, cibles chiffrées du registre. Court et factuel — c'est la section que chaque future session relira au démarrage, elle doit rester sous 150 lignes.
4. **Vue d'ensemble du pipeline** : schéma en blocs, de l'idée à la vidéo publiée et à la mesure de ses résultats.
5. **Tableau récapitulatif** : `# | Phase | Étape | Livrables | Sous-agents | Contexte estimé | Dépend de`. Une ligne par étape.
6. **Les phases et leurs étapes détaillées**, au format imposé ci-dessous, chaque phase ouverte par son objectif et close par son jalon vérifiable.
7. **Règles de session permanentes** : hygiène valable partout (logs, purge des modèles, mise à jour de `STATE.md`, preuve avant déclaration, quand découper une session).
8. **Jalon de bascule vers le serveur** : critères objectifs et chiffrés.
9. **Risques et plans B** : les 6 risques les plus sérieux du projet, avec leur parade — dont le photoréalisme, la conformité YouTube et la contrainte disque.

Format imposé de chaque étape :

## Étape N — <titre d'action>

**Objectif.** Une phrase.
**Pourquoi maintenant.** Une phrase : ce que cette étape débloque.
**Valeur créée.** Une phrase rattachant l'étape à `<these_de_valeur>`.
**Pré-requis.** Étapes terminées et fichiers attendus en entrée.
**Sous-agents.** Combien, lesquels, ce que chacun rapporte (« aucun » si l'étape n'en justifie pas).
**Livrables.** Chemins absolus des fichiers créés ou modifiés.
**Poids disque.** Ce que l'étape télécharge, en Go (0 si rien).
**Terminé quand.** Critères vérifiables objectivement.

**Prompt à copier-coller :**

````text
<le prompt complet, autonome, prêt à l'emploi>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| … | … |
| Sous-total | … |
| Marge +25 % | … |
| **Total** | **… tk — … %** |

Note l'usage des **quatre** backticks autour des prompts : ils contiennent eux-mêmes des blocs de code à trois backticks.
</structure_du_fichier>

<exemple_etape>
Exemple d'étape correctement formée. Respecte ce niveau de précision et de densité — le contenu réel, lui, est à concevoir par toi.

## Étape 4 — Mesurer ce qui tourne réellement sur le M2

**Objectif.** Mesurer sur la machine cible les performances réelles des outils retenus à l'étape 3.
**Pourquoi maintenant.** Toute l'architecture dépend de ce qui est effectivement exécutable en local : la décider avant la mesure, c'est la refaire deux fois.
**Valeur créée.** Élimine le risque n° 1 du projet — bâtir sur un outil qui ne tient pas sur la machine.
**Pré-requis.** Étape 3 terminée · `outils/SELECTION.md` existe.
**Sous-agents.** 2 en parallèle — (a) procédure d'installation Apple Silicon de chaque outil retenu et poids disque exact ; (b) pièges MPS/Metal connus et contournements. 400 mots maximum chacun, format imposé.
**Livrables.** `/Users/.../benchmarks/RESULTATS.md`, `/Users/.../benchmarks/bench.sh`
**Poids disque.** ~6 Go (3 modèles quantifiés, purgés en fin d'étape sauf le retenu).
**Terminé quand.** `RESULTATS.md` contient pour chaque outil : temps mesuré, pic de mémoire, poids disque, verdict go/no-go — et au moins un outil par brique est en « go ».

**Prompt à copier-coller :**

````text
Tu es ingénieur performance, spécialiste de l'inférence de modèles IA sur Apple Silicon.

<contexte>
Projet : système autonome de production de vidéos YouTube, budget 0 €, tout en local.
Machine : MacBook Air M2, 16 Go de RAM unifiée, ~30 Go de disque libre, macOS 27, pas de CUDA.
Cette session mesure ce qui tourne réellement sur cette machine. Les résultats détermineront
toute l'architecture : une mesure fausse ici coûtera des semaines de travail plus tard.
</contexte>

<demarrage>
Lis, dans cet ordre :
1. /Users/.../ROADMAP.md — uniquement « Contexte figé » et l'étape 4
2. /Users/.../STATE.md
3. /Users/.../outils/SELECTION.md
Ne lis aucun autre fichier tant que tu n'en as pas besoin.
</demarrage>

<sous_agents>
Lance immédiatement 2 sous-agents en parallèle, en un seul envoi :
- Agent A : pour chaque outil de SELECTION.md, procédure d'installation officielle sur Apple
  Silicon (M2, 16 Go) et poids disque exact des modèles.
- Agent B : pièges connus de PyTorch MPS / Metal pour ces outils sur les 12 derniers mois
  (opérations non supportées, fuites mémoire, contournements).

Format de réponse imposé à chacun, 400 mots maximum :
  OUTIL | COMMANDES D'INSTALL | POIDS DISQUE | PIÈGE PRINCIPAL | SOURCE (URL)

N'effectue pas ces recherches toi-même : elles satureraient le contexte de cette session.
</sous_agents>

<tache>
1. À partir des rapports, écris /Users/.../benchmarks/bench.sh : pour chaque outil, installation,
   génération d'un échantillon standard identique, mesure du temps écoulé et du pic de mémoire,
   puis désinstallation.
2. Exécute-le en redirigeant la sortie vers benchmarks/bench.log ; n'affiche que les 20 dernières
   lignes après chaque outil.
3. Consigne les résultats dans /Users/.../benchmarks/RESULTATS.md.
4. Ouvre chaque échantillon produit et juge sa qualité sur 5. Un outil rapide qui produit un
   rendu inutilisable est un no-go : la mesure de vitesse seule ne suffit pas à décider.
</tache>

<contraintes>
- Redirige toute sortie verbeuse vers un log et ne lis que les extraits utiles.
- Vérifie l'espace disque avant chaque téléchargement : ne descends jamais sous 8 Go libres.
- Si un outil échoue après deux tentatives, note-le « no-go » avec le message d'erreur exact et
  passe au suivant. Ne cherche pas à le réparer : ce n'est pas l'objet de cette session.
- Chiffres mesurés uniquement. Aucune estimation présentée comme une mesure. Si tu n'as pas pu
  mesurer, écris « non mesuré » plutôt que de combler.
</contraintes>

<format_sortie>
RESULTATS.md : un tableau, puis un paragraphe de recommandation par brique.
| Outil | Brique | Temps | Pic mémoire | Disque | Qualité /5 | Verdict |
</format_sortie>

<fin_de_session>
Mets à jour /Users/.../STATE.md : étape 4 terminée, outils retenus par brique, no-go et motifs,
disque restant, question ouverte pour l'étape 5. Puis résume en 10 lignes maximum.
</fin_de_session>
````

**Budget de contexte.**

| Poste | Tokens |
|---|---|
| Overhead de démarrage | 18 000 |
| Lecture ROADMAP (partielle) + STATE + SELECTION | 7 500 |
| Prompt | 950 |
| 2 rapports de sous-agents | 4 000 |
| Écriture bench.sh + exécution (extraits de logs) | 9 000 |
| Inspection des échantillons produits | 3 000 |
| Écriture RESULTATS.md + mise à jour STATE | 5 000 |
| Sous-total | 47 450 |
| Marge +25 % | 11 860 |
| **Total** | **59 310 tk — 29,7 %** |
</exemple_etape>

<methode_de_travail>
1. **Réfléchis avant d'écrire.** Établis l'enchaînement complet des phases et des étapes, vérifie qu'aucune ne dépend d'un résultat produit après elle, place le jalon « première vidéo complète » à la fin de la phase 1, et vérifie que les phases 3 et 5 — l'intelligence éditoriale et la boucle de rétroaction — sont traitées avec autant de sérieux que le pipeline lui-même.
2. **Délègue la veille.** Tu ne connais pas l'état de l'art open-source d'aujourd'hui pour la génération vidéo sur Apple Silicon, ni les outils gratuits disponibles pour l'analyse d'audience YouTube : ces domaines bougent tous les mois. Lance des sous-agents en parallèle pour établir, à la date d'aujourd'hui : les outils gratuits par brique de production et leur compatibilité M2 16 Go ; les accès gratuits aux données YouTube (API officielles, quotas, alternatives) ; l'état des règles YouTube sur le contenu généré par IA.
   Cette veille sert à rendre la roadmap crédible et à nourrir les prompts en pistes concrètes — **elle ne remplace pas les étapes de veille du plan**, qui restent à exécuter avec mesures à l'appui.
3. **Dimensionne.** Vise **22 à 30 étapes** réparties sur les 7 phases. C'est le volume qu'exige l'ambition demandée. Si une phase tient en une étape, c'est qu'elle est sous-traitée.
4. **Calcule chaque budget** poste par poste avec le barème. Toute étape au-delà de 40 % est découpée.
5. **Écris `ROADMAP.md`** en un seul fichier.
6. **Relis-toi** selon `<criteres_de_qualite>` et corrige avant de rendre la main.
</methode_de_travail>

<criteres_de_qualite>
Vérifie chaque point et corrige le fichier avant de rendre la main :
- [ ] Chaque étape a un prompt complet, autonome, copiable sans retouche, sans placeholder.
- [ ] Chaque prompt indique les fichiers à lire au démarrage et la mise à jour de `STATE.md` à la fin.
- [ ] Aucune étape ne dépasse 40 %, la majorité est à 30 % ou moins, chaque budget est décomposé.
- [ ] Tous les outils cités sont gratuits, à licence commerciale compatible, exécutables sur M2 16 Go sans CUDA. Les licences restrictives sont signalées.
- [ ] Le cumul des téléchargements reste sous ~20 Go et une règle de purge existe.
- [ ] Une vidéo complète de bout en bout sort à la fin de la phase 1.
- [ ] Il existe un banc d'évaluation objectif qui note les vidéos produites face aux cibles du registre, et un portillon de qualité qui bloque la publication sous le seuil.
- [ ] Il existe une couche de décision éditoriale : le système choisit ses sujets sur des données, pas au hasard.
- [ ] Il existe une boucle de rétroaction : les performances publiées sont récupérées et orientent les productions suivantes.
- [ ] Le système est multi-chaînes et multi-langues par architecture, pas par ajout tardif.
- [ ] La conformité YouTube est traitée comme une contrainte de conception.
- [ ] L'économie unitaire est mesurée : coût et revenu par vidéo, par niche, par langue.
- [ ] Alek et Sofiane peuvent exploiter le système sans lire de code.
- [ ] Les cibles chiffrées du registre sont réellement appliquées puis vérifiées sur le rendu, pas seulement citées.
- [ ] Les dépendances entre étapes sont cohérentes : rien ne dépend d'un résultat ultérieur.
- [ ] Le jalon serveur GPU est déclenché par des critères chiffrés, et rien avant lui n'exige de payer.
- [ ] La limite du photoréalisme est traitée explicitement, avec la réponse à apporter à Alek.
- [ ] L'ensemble est en français, dense, sans remplissage.
</criteres_de_qualite>

<anti_objectifs>
- N'écris aucun code applicatif et ne lance aucune installation : ce n'est pas cette session qui exécute.
- Ne crée aucun fichier autre que `ROADMAP.md`.
- **Ne produis pas un plan de générateur de vidéos.** Un plan qui s'arrête au rendu du MP4, sans décision éditoriale, sans mesure objective et sans boucle de rétroaction, est un échec quelle que soit sa qualité d'écriture.
- Ne recommande aucun outil payant, freemium limité, ou exigeant une carte bancaire, pour la phase couverte. Les options payantes n'apparaissent qu'en phase 6, après le jalon des 90 %.
- N'affirme pas qu'un outil tourne sur M2 16 Go sans vérification : marque l'incertitude « à mesurer à l'étape N » plutôt que de l'effacer.
- Pas d'étape vague du type « améliorer la qualité » : chaque étape a un livrable fichier et un critère de fin vérifiable.
- Ne noie pas le fichier sous les précautions et les généralités : Thomas est développeur depuis 8 ans.
</anti_objectifs>

<action>
Lance d'abord tes sous-agents de veille en parallèle, puis écris
`/Users/toms/Documents/Claude/Clients/Alek/Content-creation/ROADMAP.md`.

Termine par un résumé de 15 lignes maximum : nombre de phases et d'étapes, budget de contexte le
plus élevé, les 3 décisions structurantes que tu as prises, et les questions ouvertes à trancher.
</action>
