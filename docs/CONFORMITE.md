# CONFORMITE.md — cadre de conformité de la fabrique vidéo BMS

**Statut :** contrat d'architecture. Figé à l'étape 1 (14/09/2026), lu par toutes les étapes suivantes.
**Portée :** règles YouTube (monétisation, spam, contenu synthétique, API), loi française n° 2023-451 modifiée, règlement (UE) 2024/1689 (RIA) art. 50, contrats des programmes d'affiliation.
**Principe de lecture :** chaque section donne d'abord la règle telle qu'elle est écrite à la source, puis « Conséquence de conception » en phrases impératives. **En cas de conflit entre une règle ci-dessous et une demande de vitesse ou de volume, la règle prime** (`CLAUDE.md` § 11).
**Principe de conflit de normes :** quand deux règles se recouvrent, on applique **la plus stricte des deux**. Le système obéit à YouTube, au droit français, au RIA et aux contrats d'affiliation simultanément ; il ne choisit pas.

---

## 1. Comptes et chaînes

**Règle — terminaison en cascade.** « If your YouTube channel is terminated, you are prohibited from using, possessing, or creating any other YouTube channels. » L'interdiction couvre « all of your existing channels, any new channels you create or acquire, and any channels in which you are repeatedly or prominently featured », et le contournement peut entraîner la suppression de l'ensemble. (https://support.google.com/youtube/answer/2802168)

**Règle — vérification du compte.** Les miniatures personnalisées et les vidéos de plus de 15 minutes sont réservées aux comptes vérifiés (vérification par téléphone). (https://support.google.com/youtube/answer/171664)

**Règle — audit et surveillance de l'API.** « YouTube may monitor, review and inspect your API Client(s), and monitor and audit your access to and use of the YouTube API Services, at any time and without further notice. » (https://developers.google.com/youtube/terms/api-services-terms-of-service)

### Le compromis, et la décision

Deux architectures de comptes sont possibles, et elles s'excluent :

| | **A — un projet Google Cloud unique** | **B — un projet Google Cloud par chaîne** |
|---|---|---|
| Audits à obtenir | 1 | autant que de chaînes (semaines à mois chacun) |
| Quota | 10 000 unités/jour partagées par tout le portefeuille | 10 000 unités/jour par chaîne |
| Isolation en cas d'incident API | nulle : une suspension du projet coupe la publication de toutes les chaînes | forte |
| Charge administrative | faible | rédhibitoire à 0 € et sans employé |

**Décision (étape 1) : architecture A — un seul projet Google Cloud, un seul audit.** Le facteur décisif n'est pas le quota, c'est le délai d'audit : multiplier les audits repousse la publication automatique de plusieurs mois par chaîne. Le risque d'isolation est réel mais il est **secondaire par rapport au risque de terminaison en cascade**, qui, lui, ne dépend pas du découpage des projets API : il dépend du compte Google propriétaire des chaînes. C'est donc là que l'isolation doit être payée, pas au niveau du projet API.

### Conséquence de conception

- Crée **un compte Google distinct par chaîne**. N'héberge jamais deux chaînes publiantes sur le même compte Google : la clause « chaînes associées » transforme sinon une sanction isolée en perte du portefeuille entier.
- Fais détenir chaque chaîne par un **Brand Account appartenant à BMS**, jamais par le compte personnel d'Alek, de Sofiane ou de Thomas. Un actif revendable doit se céder sans transférer l'identité d'une personne physique.
- Active la **2FA** et la **vérification téléphonique** sur chaque compte avant toute publication : sans vérification, ni miniature personnalisée ni vidéo de plus de 15 minutes, donc pas de format long.
- N'implémente aucun partage de session, aucun cookie de connexion stocké, aucune connexion automatisée. L'accès programmatique passe exclusivement par OAuth, jetons sous `secrets/yt_tokens`.
- Stocke dans `config/channels/<channel>.yml` : `google_account_alias`, `brand_account`, `owner: BMS`, `two_fa_enabled`, `phone_verified`, `gcp_project` (valeur unique et identique pour toutes les chaînes).
- Considère la couche API comme un **point de défaillance unique assumé** : le pipeline doit pouvoir retomber sur le chemin manuel de la section 2 sans réécriture si le projet est suspendu.

---

## 2. Chemin de publication

**Règle — upload forcé en privé.** « All videos uploaded via the `videos.insert` endpoint from unverified API projects created after 28 July 2020 will be restricted to private viewing mode. To lift this restriction, each project must undergo an audit to verify compliance with the Terms of Service. » (https://developers.google.com/youtube/v3/revision_history ; formulaire d'audit : https://support.google.com/youtube/contact/yt_api_form)

**Règle — quota.** Quota par défaut : 10 000 unités/jour, dont 100 appels `search.list` et 100 `videos.insert`. Un `videos.insert` coûte 1 600 unités. (https://developers.google.com/youtube/v3/guides/quota_and_compliance_audits)

**Règle — pas d'automatisation hors API.** Les Developer Policies interdisent de « scrape YouTube Applications » et d'« use any technology other than YouTube API Services to access or retrieve API Data ». (https://developers.google.com/youtube/terms/developer-policies)

### Conséquence de conception

- Implémente **un seul chemin de code**, avec un drapeau `publish_path` à deux valeurs. Phase 1 `manual_studio`, phase 2 `api_scheduled`. Ne construis jamais deux pipelines.
- Phase 1 (avant audit) : `videos.insert` avec `status.privacyStatus = "private"` et **toutes les métadonnées déjà complètes** (titre, description avec divulgations et attributions, tags, langue, `status.containsSyntheticMedia`, sous-titres, miniature). La seule action humaine restante est un basculement dans YouTube Studio, ≈ 2 minutes par vidéo.
- Génère à chaque run un **pense-bête de publication** (`workspace/runs/<run_id>/publication.md`) listant les gestes manuels à faire dans Studio : passage en programmé, **case « promotion payante »** (section 3), date/heure cible. Sans ce fichier, l'opérateur oublie la case.
- Phase 2 (après audit) : `videos.update` avec `status.privacyStatus = "private"` + `status.publishAt` (ISO-8601 UTC) pour la programmation. **La case « promotion payante » reste manuelle** (section 3) : la phase 2 supprime le geste de publication, pas le geste de divulgation.
- Plafonne le pipeline à **6 uploads par jour, toutes chaînes confondues** : à 1 600 unités par insert, le quota d'unités (10 000) sature avant le compteur de 100 inserts. Fais échouer l'ordonnanceur proprement au 7ᵉ, ne le laisse pas consommer le quota de lecture du registre.
- N'utilise **jamais** Playwright, Selenium ou tout pilotage de navigateur sur youtube.com ou studio.youtube.com : c'est une violation des ToS, et la sanction est la terminaison, donc la cascade de la section 1. Playwright reste autorisé pour le rendu local de miniatures HTML→PNG, qui ne touche aucun service Google.
- **Dépose le dossier d'audit à l'étape 14**, dès qu'une vidéo complète existe : le délai se compte en semaines à mois, il doit courir pendant que le reste se construit.

---

## 3. Divulgation en trois couches

Trois obligations distinctes se superposent. Elles ont trois déclencheurs différents et trois supports différents ; n'en fusionne aucune.

### Couche 1 — Contenu altéré ou synthétique (YouTube)

**Règle.** La divulgation est obligatoire quand le contenu « makes a real person appear to say or do something they didn't do », « alters footage of a real event or place », ou « generates a realistic scene that didn't actually occur ». Sont exclues l'animation et les scènes manifestement irréalistes, ainsi que « production assistance, like using generative AI tools to create or improve a video outline, script, thumbnail, title, or infographic ». Pour les sujets sensibles (santé, finance, élections, conflits, catastrophes), YouTube affiche « a more prominent label in the video player ». La non-divulgation répétée expose au retrait du contenu ou à la suspension du YPP. (https://support.google.com/youtube/answer/14328491)

**Règle API.** `status.containsSyntheticMedia` : « In a `videos.insert` or `videos.update` request, this property allows the channel owner to disclose that a video contains realistic Altered or Synthetic (A/S) content. » (https://developers.google.com/youtube/v3/docs/videos)

**Conséquence de conception**
- Applique cette **règle de décision, sans exception** : `contains_synthetic_media = true` dès qu'une scène **réaliste générée** figure un lieu, une personne ou un événement. Une voix clonée réaliste, une scène photoréaliste d'un lieu existant, une reconstitution d'événement : `true`. Un script écrit par le LLM, une miniature générée, une animation whiteboard, un motion design, une infographie : `false`.
- Calcule le drapeau **au moment de la génération de chaque plan**, pas à l'upload : `synthetic_scenes[].realistic` est posé par le module qui produit l'image ou la voix, puis agrégé. Un drapeau reconstitué après coup est un drapeau faux.
- Stocke le drapeau **dans le manifeste** et rejoue-le à chaque `videos.update` : l'API ne conserve pas de valeur par défaut fiable.
- Traite les niches **santé et finance** (longévité, biohacking, compléments alimentaires, peptides, paris sportifs — cf. registre) comme sujets sensibles : le label apparaîtra dans le lecteur, pas seulement en description. Conçois les miniatures et les 5 premières secondes en tenant compte de ce bandeau.
- Ne retire jamais les métadonnées C2PA produites par les outils de génération (section 4, RIA).

### Couche 2 — Promotion payante (YouTube)

**Règle.** La divulgation est obligatoire pour tout contenu comportant « branded content, sponsorships, endorsements, or other commercial relationships » ; YouTube affiche alors un message de divulgation pendant 10 secondes en début de vidéo. Pour l'affiliation : « If your content features a paid endorsement… select the paid promotion box… follow the current FTC guidance ». (https://support.google.com/youtube/answer/154235)

**Conséquence de conception**
- Pose `paid_promotion = true` **dès qu'un lien d'affiliation figure dans la description**, sans autre condition. Pas de seuil, pas de jugement au cas par cas.
- **Contrainte dure à propager partout :** il n'existe pas de champ d'écriture pour cocher cette case dans `videos.insert` / `videos.update` ; l'API ne l'expose qu'en lecture via `paidProductPlacementDetails.hasPaidProductPlacement`. **Toute vidéo affiliée exige donc un passage manuel dans YouTube Studio, même après l'audit.** Intègre ce geste au pense-bête de la section 2 et au tableau de bord ; ne promets jamais une chaîne affiliée 100 % automatique.
- Après publication, **vérifie** l'état réel via `videos.list(part=paidProductPlacementDetails)` et lève une alerte si `hasPaidProductPlacement` est `false` alors que `paid_promotion` est `true`. C'est le seul contrôle a posteriori qui détecte un oubli humain.

### Couche 3 — Mention légale française et contractuelle

**Règle — loi n° 2023-451, art. 5-2 (dans sa rédaction issue de l'ord. n° 2024-978).** Constitue une pratique commerciale trompeuse « l'absence d'indication par une mention claire, lisible et compréhensible, sur tout support utilisé, de l'intention commerciale… dès lors que cette intention ne ressort pas déjà du contexte. L'intention commerciale peut être explicitement indiquée par le recours aux mentions "publicité" ou "collaboration commerciale" ou par une mention équivalente adaptée… au format du support ». (https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000050457275)

**Règle — champ d'application.** Sont visées « les personnes physiques **ou morales** qui, à titre onéreux, mobilisent leur notoriété auprès de leur audience pour communiquer au public par voie électronique des contenus visant à faire la promotion, directement ou indirectement, de biens, de services ou d'une cause ». (https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000050468930) La DGCCRF range la rémunération par « pourcentage sur les ventes » dans le champ de l'obligation de divulgation. (https://www.economie.gouv.fr/influenceurs-quels-sont-mes-devoirs)

**Règle — images virtuelles.** « Les contenus comprenant des images produites par procédé d'intelligence artificielle **visant à représenter un visage ou une silhouette** sont accompagnés de la mention "Images virtuelles" », claire, lisible et compréhensible, sur tout support utilisé. (https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000050468897)

**Règle — contrat Impact.** « Creator's disclosure must be stated/displayed at the beginning of the video; a description listing is not enough. » Mentions autorisées : « 'paid ad,' 'sponsored,' 'promoted,' 'ad', '#ad,' and '#sponsored'. No other alternatives are permitted. » (https://app.impact.com/content/displaympserviceagreement.ihtml)

**Règle — contrat Amazon Partenaires.** Mention imposée : « En tant que Partenaire Amazon, je réalise un bénéfice sur les achats remplissant les conditions requises », affichée « clairement et de façon visible ». (https://partenaires.amazon.fr/help/operating/agreement)

**Règle — contrat Awin.** Mentions exigées : « #Ad, #PaidAd, #sponsorship, #sponsoredpost » ; « #affiliate », « #partner », « #spon » sont refusés. (https://www.awin.com/gb/news-and-events/tips-and-tricks/utilising-click-references)

**Conséquence de conception**
- BMS est une personne morale assujettie : **aucune chaîne n'est hors champ**. Applique la divulgation même sur une chaîne sans contrat annonceur, dès qu'un lien commissionné existe.
- Incruste à l'écran le bandeau **« Publicité »** (FR) ou **« Collaboration commerciale »** pendant **tout** segment promotionnel, et non seulement à son début. La rédaction issue de l'ordonnance 2024-978 n'impose plus explicitement l'affichage pendant toute la durée de la promotion, mais le contrat Impact impose une divulgation en début de vidéo et interdit la divulgation en description seule : **retiens la règle la plus stricte**, c'est-à-dire l'incrustation continue, déclenchée dès la première seconde du segment.
- Place la mention **en première ligne de description**, dans la langue de la vidéo, avant toute autre ligne — y compris avant le bloc d'attribution des assets.
- Insère une **mention orale dans les 30 premières secondes du segment promotionnel**, écrite dans le script, donc relue par l'humain (section 4), donc vérifiable par hash.
- Adapte le vocabulaire au réseau : `#ad` / `#sponsored` pour Impact, `#Ad` / `#PaidAd` pour Awin, la phrase Amazon **mot pour mot** pour Amazon Partenaires — elle est contractuelle, ne la traduis ni ne la reformule sur les chaînes FR. Stocke ces gabarits dans `config/languages/<lang>.yml` et `config/products/<produit>.yml`, jamais en dur dans le code.
- Déclenche la mention **« Images virtuelles »** sur une condition **distincte** de `contains_synthetic_media` : elle vise les images IA représentant **un visage ou une silhouette humaine**, réalistes ou non. Une illustration cartoon d'un personnage la déclenche ; un paysage photoréaliste généré ne la déclenche pas (mais il déclenche, lui, `contains_synthetic_media`). Porte `virtual_images_mention` comme champ propre.
- Pour les chaînes non francophones publiées par BMS, applique le même standard : l'obligation suit l'éditeur, pas la langue de l'audience.

---

## 4. Signature humaine — anti « contenu inauthentique » et exception RIA

**Règle — YouTube, contenu inauthentique** (politique renommée le 15/07/2025, ex-« contenu répétitif »). Sont inéligibles à la monétisation les « AI-generated content made with generic or unoriginal templates giving the impression of mass production » et les « image slideshows, templated storylines, or scrolling text with minimal or no narrative, commentary, or educational value ». Reste admis : « same intro and outro for your videos, but the bulk of your content is different ». YouTube précise : « This type of content has always been ineligible for monetization. » (https://support.google.com/youtube/answer/1311392)

**Règle — YouTube, contenu réutilisé.** Sont visés le « content downloaded or copied from another online source without any substantive modifications » et le « content that exclusively features readings of other materials you did not originally create ». (https://support.google.com/youtube/answer/1311392)

**Règle — RIA art. 50 §4.** Le déployeur d'un système générant un « deep fake » « shall disclose that the content has been artificially generated or manipulated ». L'obligation ne s'applique pas « where the content forms part of an evidently artistic, creative, satirical, fictional… work », ni « where the AI-generated content has undergone a process of human review or editorial control and where a natural or legal person holds editorial responsibility for the publication of the content ». (https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-50 ; https://digital-strategy.ec.europa.eu/en/faqs/transparency-obligations-under-article-50-ai-act)

**Règle — RIA art. 50 §5.** L'information est fournie « in a clear and distinguishable manner at the latest at the time of the first interaction or exposure », sous une forme perceptible « without need for any specific technical tools ». (https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-50)

**Règle — RIA art. 50 §2 et marquage machine.** Les **fournisseurs** de systèmes générant du contenu synthétique doivent garantir que les sorties « are marked in a machine-readable format and detectable as artificially generated or manipulated ». Le Code of Practice on Transparency of AI-generated Content (publié le 10/06/2026, adhésion volontaire) décrit un marquage à deux couches — métadonnées sécurisées et tatouage — et renvoie à **C2PA** et ISO 22144. (https://digital-strategy.ec.europa.eu/en/policies/code-practice-ai-generated-content)

**Règle — sanctions.** Art. 5 de la loi 2023-451 : « un an d'emprisonnement et de 4 500 euros d'amende ». Qualification en pratique commerciale trompeuse : 2 ans et 300 000 €, portés à **5 ans et 750 000 €** lorsque la pratique est commise via un service de communication au public en ligne, majoration possible à 10 % du chiffre d'affaires annuel moyen, quintuplée pour une personne morale. (https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000049532070) RIA art. 99 §4 : jusqu'à 15 000 000 € ou 3 % du chiffre d'affaires mondial. (https://artificialintelligenceact.eu/article/99/)

**Règle — DGCCRF.** Injonction de mise en conformité assortie d'une astreinte de 3 000 € par jour au maximum, plafonnée à 300 000 €, avec possibilité de déréférencement ou de blocage de compte. (https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000051830385)

### Conséquence de conception

La relecture humaine n'est pas un confort qualité : c'est **la pièce qui fait tomber l'obligation de divulgation RIA** (exception de responsabilité éditoriale) **et l'argument central contre la qualification de contenu inauthentique**. Elle doit donc produire une trace, pas seulement une opinion.

- Impose à chaque script un **angle éditorial propre**, choisi dans une liste fermée : opinion assumée, comparaison chiffrée, test ou vérification, donnée propriétaire. Un script sans angle est rejeté par la checklist (section 11, contrôle 11), pas seulement mal noté.
- Fais relire **par lots** (jamais plan par plan, cf. `ROADMAP.md` § 3.4) par un **membre nommé** de l'équipe — Alek, Sofiane ou Thomas. « L'équipe » n'est pas un relecteur : le champ `reviewer` porte une identité.
- Écris un **journal de relecture append-only** (`registre/data/reviews.jsonl`) : relecteur, date ISO-8601, hash SHA-256 du script relu, décision. Ce journal est la preuve produite en cas de contrôle DGCCRF ou de contestation RIA ; ne le réécris jamais, n'y fais jamais de mise à jour en place.
- Vérifie à la publication que `review_hash` correspond au **script effectivement monté**, pas à une version antérieure. Une relecture qui porte sur un autre texte que celui publié ne vaut rien.
- Le mode **`auto-approve` existe** — il est nécessaire pour tenir la promesse d'autonomie — mais il est **documenté comme risque assumé par le client** : quand il est actif, `reviewer = "auto-approve"`, la checklist émet un avertissement, le tableau de bord l'affiche en permanence, et le rapport de run porte la mention que l'exception éditoriale RIA n'est plus acquise pour ces vidéos. Ce mode se coupe par chaîne, dans `config/channels/<channel>.yml`.
- **Préserve les métadonnées C2PA** produites par les outils de génération : ne les retire jamais au montage, au réencodage ffmpeg ou à l'export. L'obligation §2 pèse sur le fournisseur du modèle, mais effacer son marquage détruit la conformité de la chaîne entière et nous place en contradiction avec le Code of Practice.
- Note pour les étapes suivantes : le champ d'application du §4 est plus étroit que la règle YouTube — la Commission retient trois critères cumulatifs impliquant une personne, un lieu ou un événement **existants**. **C'est la règle YouTube qui commande le pipeline**, parce qu'elle est la plus large et que sa sanction (démonétisation, terminaison) frappe l'actif directement.

---

## 5. Variation et anti-clonage

**Règle.** Les Community Guidelines sur le spam visent la « automated or synthetic mass-production: using automated tools or AI to churn out high volumes of similar content with minimal changes », le « malicious clickbait: using maliciously misleading titles, thumbnails, descriptions, or imagery » et l'« engagement manipulation: repetitive or templated content aimed at artificially inflating engagement ». Trois avertissements en 90 jours entraînent la suppression de la chaîne. (https://support.google.com/youtube/answer/2801973)

**Conséquence de conception**

Le registre montre des réseaux clonés par langue qui fonctionnent aujourd'hui (Library of Thoth EN / Bibliothèque de Thot FR / Biblioteca di Thoth IT). **Ne reproduis pas ce modèle mécaniquement** : c'est exactement la forme visée par la politique de 07/2025, et les terminaisons de janvier 2026 ont frappé ce profil. Le levier de volume reste le multi-chaînes ; le clonage littéral, non.

- Maintiens **au moins 3 templates visuels en rotation par chaîne**, avec un `template_id` par vidéo. La checklist avertit si le template répète l'une des 2 dernières publications de la chaîne.
- N'autorise **jamais le même script ni la même miniature sur deux chaînes de même langue**. Contrôle par `dedupe_hash` : SimHash/MinHash du script et hash perceptuel de la miniature, indexés **globalement**, toutes chaînes confondues, pas par chaîne.
- Traite une **déclinaison multilingue comme une adaptation**, pas comme une traduction : angle réécrit pour le marché, exemples et chiffres localisés, habillage visuel distinct, miniature distincte, voix distincte. Porte `source_run_id` pour garder la traçabilité sans masquer la parenté.
- Autorise explicitement l'intro et l'outro communes : c'est le cas que la politique déclare admis, à condition que « the bulk of your content is different ».
- Fais générer titre et miniature **à partir du contenu réel** et vérifie leur cohérence avec le script avant publication. Un titre promis que la vidéo ne tient pas est du clickbait malicieux, donc un avertissement, et trois avertissements suppriment la chaîne.
- N'implémente aucun appel à l'action d'incitation à l'engagement récompensé, aucun échange d'abonnements, aucun outil tiers d'engagement.

---

## 6. Cadence

**Règle — YPP, accès étendu.** « 500 subscribers with 3 valid public uploads in the last 90 days, and 3,000 qualified watch hours in the last 12 months, or… 3 million qualified Shorts views in the last 90 days. » (https://support.google.com/youtube/answer/13429240)

**Règle — YPP, monétisation publicitaire.** 1 000 abonnés et 4 000 heures de visionnage validées sur 12 mois, ou 10 millions de vues de Shorts sur 90 jours. **Seuils annoncés au 01/02/2027** : 8 000 heures sur 365 jours ou 20 millions de vues de Shorts sur 90 jours, le seuil de 1 000 abonnés étant maintenu. Maintien d'activité : 1 000 heures sur 365 jours, ou 1 million de vues de Shorts sur 90 jours, ou 2 vidéos longues / 5 Shorts par 90 jours. (https://support.google.com/youtube/answer/72851 ; https://support.google.com/youtube/answer/12843009)

**Conséquence de conception**

- Plafonne à **2 vidéos par chaîne et par semaine pendant les 90 premiers jours** de vie de la chaîne. Cette limite est appliquée par l'ordonnanceur, pas laissée à la configuration : elle est le principal amortisseur contre la qualification de production de masse.
- Applique un **jitter** sur l'heure de publication (fenêtre de plusieurs heures, jamais un horaire fixe au quart d'heure près) et évite les jours régulièrement identiques.
- Interdis les **rafales** : impose un intervalle minimal entre deux publications d'une même chaîne, et **interdis la publication simultanée sur plusieurs chaînes** (fenêtre d'exclusion de ± 30 minutes à l'échelle du portefeuille). Deux chaînes qui publient à la même minute signent l'exploitation commune.
- Tiens l'état de cadence dans `workspace/library/cadence.json` : `published_timestamps[]`, `next_allowed_at`. C'est **la seule source de vérité** sur « peut-on publier maintenant » ; aucun autre module ne décide.
- Note que 2/semaine (≈ 26 vidéos par trimestre) dépasse largement les minima de maintien d'activité du YPP (2 longues / 90 jours) : **la contrainte qui commande est le plafond de prudence, jamais un plancher de volume**. Ne remonte la cadence qu'après les 90 jours et sur décision explicite du client, chaîne par chaîne.
- Rappelle dans les rapports que **l'affiliation est la seule recette avant les seuils YPP**, et que le relèvement du 01/02/2027 double l'exigence d'heures : le modèle économique ne doit pas supposer AdSense.

---

## 7. Musique et sons

**Règle — Audio Library.** Les pistes se téléchargent depuis YouTube Studio > « Audio library ». « If you're using a track with a Creative Commons license, you must credit the artist in your video's description » (filtre « Attribution required »). La musique proposée est « copyright-safe… won't be claimed by a rights holder through the Content ID system ». L'usage en dehors de YouTube n'est pas couvert par une source officielle consultée. (https://support.google.com/youtube/answer/3376882)

**Conséquence de conception**

- Télécharge chaque piste **depuis le Studio de la chaîne qui la publiera**, pas depuis une autre chaîne ni depuis un miroir tiers. La licence est attachée au contexte de téléchargement.
- Enregistre par piste : titre, auteur, source, licence, URL de licence, drapeau `attribution_required`, texte de crédit exact, chaîne de téléchargement. Insère le crédit **automatiquement** en description quand `attribution_required` est vrai — un crédit manuel sera oublié.
- Filtre Freesound sur **CC0 et CC-BY uniquement** ; enregistre l'attribution de la même façon. Rejette tout CC-BY-NC, CC-BY-ND et toute licence « sampling ».
- **Élimine tout modèle de génération musicale à licence non commerciale** (MusicGen, YuE en CC-BY-NC sont déjà écartés). Si un modèle de génération est retenu, sa licence de **poids** doit être commerciale et inscrite dans `outils/MODELES.md`.
- Ne réutilise pas les pistes de l'Audio Library en dehors de YouTube (site, publicité, autre plateforme) tant qu'aucune source officielle ne l'autorise explicitement.
- Une vidéo sans `music.licence` renseignée ne peut pas être publiée (section 11, contrôle 8).

---

## 8. Images et vidéos

**Règle — contenu réutilisé.** Le montage de sources externes sans couche originale relève du « reused content » et est inéligible à la monétisation. (https://support.google.com/youtube/answer/1311392)

**Règle — images virtuelles.** Voir section 3, couche 3 : mention « Images virtuelles » pour toute image IA représentant un visage ou une silhouette. (https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000050468897)

**Conséquence de conception**

- Enregistre pour **chaque asset** : `provider`, `source_url`, `author`, `licence`, `licence_url`, `attribution_line`, `downloaded_at`. Un asset sans ces champs ne descend pas dans le pipeline — le contrôle se fait à l'acquisition, pas au montage, où il est trop tard.
- Restreins les fournisseurs à une **liste blanche** dans la configuration : Pexels, Pixabay, Openverse (filtre commercial), Wikimedia Commons, NASA, Internet Archive. Tout autre fournisseur exige une décision explicite tracée dans `STATE.md`.
- Compose **automatiquement un bloc d'attribution** en fin de description, agrégeant les `attribution_line` des assets utilisés et le crédit musical. Ne le laisse jamais à la main.
- N'utilise pour la génération d'images que des modèles à **licence de poids commerciale** (les non commerciaux sont éliminatoires et inscrits comme tels dans `outils/MODELES.md`).
- **N'utilise aucune image d'une personne réelle identifiable sans droit enregistré.** Porte `assets[].person_release` ; en son absence, le plan est refusé. Cela couvre aussi la génération : ne demande jamais à un modèle de produire le visage d'une personne existante.
- Ajoute une **couche originale** sur tout matériau externe : commentaire, analyse, mise en récit, données. Un diaporama de banque d'images avec voix off descriptive tombe simultanément sous « contenu réutilisé » et sous « contenu inauthentique ».

---

## 9. Données concurrentes

**Règle — durée de conservation.** Developer Policies III.E.4 : les données API peuvent être stockées « for no longer than 30 calendar days » ; passé ce délai, « the API Client must either delete or refresh the stored data ». (https://developers.google.com/youtube/terms/developer-policies)

**Règle — usages interdits.** Interdiction de « scrape YouTube Applications », de « separate, isolate, or modify the audio or video components » et d'« use any technology other than YouTube API Services to access or retrieve API Data ». (https://developers.google.com/youtube/terms/developer-policies)

**Conséquence de conception**

- Passe par l'**API Data v3 officielle** pour toute métadonnée de chaîne ou de vidéo, sans exception, dans tout le pipeline quotidien.
- **Purge ou rafraîchis le cache du registre à 30 jours au maximum.** Porte `fetched_at` sur chaque enregistrement et fais tourner une tâche de purge ; ce n'est pas une optimisation de disque, c'est une clause contractuelle opposable lors d'un audit.
- Conserve indéfiniment, en revanche, les **mesures dérivées** (médiane de secondes par plan, agrégats, comptages) : ce ne sont plus des données API, elles ne portent aucune information d'origine.
- N'utilise les **transcriptions de vidéos tierces** que pendant les phases de recherche des **étapes 3 et 16**, à faible volume, depuis une **IP résidentielle**, avec un **compte de recherche jamais lié aux chaînes publiantes** (compte Google distinct, jamais connecté sur une machine ou un navigateur utilisé pour Studio). Jamais dans le pipeline quotidien, jamais automatisé en continu.
- **N'utilise jamais yt-dlp** ni aucun téléchargement de vidéos tierces, à aucune étape, pour aucun motif — y compris pour « juste analyser le rythme de coupe ». La mesure de rythme se fait sur nos propres rendus ou sur des échantillons obtenus autrement.
- Ne fais transiter aucune donnée de recherche vers les comptes publiants : pas de fichier partagé via un Drive lié, pas de connexion croisée.
- N'automatise ni vues, ni commentaires, ni likes, ni abonnements : les Developer Policies III.I.2 l'interdisent sans consentement explicite de l'utilisateur, et c'est de la manipulation d'engagement au sens de la section 5.

---

## 10. Champs obligatoires du modèle de données — contrat pour l'étape 9

Ces champs ne sont pas facultatifs : chacun matérialise une règle des sections 1 à 9. Le schéma de l'étape 9 les porte tous, la checklist de la section 11 les vérifie, et **un run dont un champ obligatoire est vide ne peut pas atteindre l'état `ready_to_publish`**.

### 10.1 Manifeste de vidéo — `workspace/runs/<run_id>/manifest.json`

| Champ | Type | Obligatoire | Règle source |
|---|---|---|---|
| `contains_synthetic_media` | booléen | oui | § 3 |
| `contains_synthetic_media_reason` | texte : scènes concernées, modèle, décision | oui si `true` | § 3, § 4 |
| `synthetic_scenes[]` | `{scene_id, generator, prompt_hash, realistic: bool}` | oui | § 3 |
| `virtual_images_mention` | booléen — image IA figurant un visage ou une silhouette | oui | § 3 couche 3 |
| `paid_promotion` | booléen | oui | § 3 couche 2 |
| `paid_promotion_checked_in_studio` | booléen + date — geste manuel confirmé | oui si `paid_promotion` | § 2, § 3 |
| `sponsor_segments[]` | `{start_s, end_s, type: affiliate\|sponsor, product_id, overlay_rendered: bool, spoken_disclosure_at_s}` | oui si `paid_promotion` | § 3 |
| `disclosure_lines{lang}` | `{description_line, overlay_text, spoken_line}` par langue publiée | oui si `paid_promotion` ou `virtual_images_mention` | § 3 |
| `affiliate_links[]` | `{network: amazon\|awin\|cj\|impact, tracking_id, subid_param, subid_value, target_url}` | oui si `paid_promotion` | § 3, § 10.4 |
| `assets[]` | `{asset_id, provider, source_url, author, licence, licence_url, attribution_line, downloaded_at, person_release}` | oui, une entrée par plan | § 8 |
| `c2pa_preserved` | booléen — métadonnées de provenance non retirées au rendu | oui | § 4 |
| `music.licence` | `{track_title, source, author, licence, licence_url, attribution_required, credit_line, downloaded_from_channel}` | oui | § 7 |
| `reviewer` | identité nommée (Alek, Sofiane, Thomas) ou `auto-approve` | oui | § 4 |
| `review_hash` | SHA-256 du script relu | oui | § 4 |
| `review_date` | ISO-8601 | oui | § 4 |
| `review_decision` | `approved` \| `approved_with_edits` \| `rejected` \| `auto` | oui | § 4 |
| `editorial_angle` | `{type: opinion\|comparaison_chiffree\|test\|donnee_proprietaire, resume}` | oui | § 4 |
| `publish_channel_account` | `{channel_id, brand_account, google_account_alias, owner: BMS, gcp_project}` | oui | § 1 |
| `cadence_limits` | `{max_per_week, window_start, published_this_week, next_allowed_at, jitter_window}` | oui | § 6 |
| `dedupe_hash` | `{script_simhash, thumbnail_phash}` | oui | § 5 |
| `template_id` | template visuel utilisé (rotation ≥ 3 par chaîne) | oui | § 5 |
| `language`, `source_run_id` | langue publiée ; run d'origine si déclinaison | `source_run_id` obligatoire pour toute déclinaison | § 5 |
| `publish_path` | `manual_studio` \| `api_scheduled` | oui | § 2 |
| `publish_state` | `draft` → `ready_to_publish` → `uploaded_private` → `scheduled` → `public` | oui | § 2 |

### 10.2 Journal de relecture — `registre/data/reviews.jsonl`

Append-only, une ligne par décision : `{review_hash, run_id, channel_id, reviewer, review_date, decision, comment, script_excerpt_hash}`. **Ne réécris jamais une ligne** : ce fichier est la pièce produite en cas de contrôle DGCCRF ou de contestation de l'exception éditoriale RIA (§ 4).

### 10.3 État de cadence — `config/channels/<channel>.yml` + `workspace/library/cadence.json`

`{channel_id, created_at, days_since_creation, max_per_week, published_timestamps[], next_allowed_at, jitter_window, auto_approve: bool}`. L'ordonnanceur lit cet état ; il n'existe pas d'autre source de vérité (§ 6).

### 10.4 Attribution des conversions — contrainte par réseau

**Règles.** Amazon Partenaires : sous-étiquettes accordées « upon your request but subject to our approval », **100 identifiants de suivi au maximum par compte** ; export CSV/XLSX/XML gratuit par identifiant et par jour ; fenêtre d'ajout au panier de **24 heures** ; validation du compte conditionnée à **3 ventes qualifiées sous 180 jours**. (https://partenaires.amazon.fr/help/node/topic/GJDYPQZK6E37RLPU ; https://partenaires.amazon.fr/help/topic/reports/faq ; https://partenaires.amazon.fr/help/node/topic/G9SMD8TQHFJ7728F ; https://partenaires.amazon.fr/help/node/topic/G8TW5AE9XL2VX9VM) — Awin : `clickref` et `clickref2..6`, 50 caractères alphanumériques, seul `clickref` transmis à l'annonceur ; Publisher API gratuite, fenêtre de 31 jours, 20 appels/minute. (https://www.awin.com/gb/news-and-events/tips-and-tricks/utilising-click-references ; https://help.awin.com/apidocs/api-authentication.md) — CJ : `sid` « keep it to 64 characters or less », sans donnée personnelle, jamais « 0 » ; champ API `shopperId`. (https://developers.cj.com/docs/publisher-site-tracking/publisher-parameter ; https://developers.cj.com/graphql/reference/Commission%20Detail) — Impact : `SubId1/2/3`, 255 caractères alphanumériques sans espace ; rapport « Performance by Sub ID », export CSV, API REST gratuite. (https://help.impact.com/partner/what-would-you-like-to-learn-about/platform-features/tracking/tracking-links/link-parameters/sub-id-and-shared-id-parameters-explained-for-partners)

**Conséquence de conception**
- Modélise `subid_param` et `subid_value` **par réseau**, jamais en dur : le nom du paramètre et la longueur maximale diffèrent (`clickref` 50, `sid` 64, `SubId1` 255).
- Accepte que l'attribution **par vidéo soit impossible sur Amazon** : avec 100 identifiants de suivi au maximum et aucun sous-paramètre officiellement documenté, l'identifiant de suivi Amazon est alloué **par chaîne et par langue**. Ne construis aucun rapport de rentabilité par vidéo qui suppose Amazon.
- Réserve la mesure par vidéo à **Awin, CJ et Impact**, où `subid` accepte l'identifiant de run. Encode `chaine_langue_runid` en respectant la limite du réseau.
- Ingère les conversions par **téléchargement CSV planifié** pour Amazon (PA-API 5.0 dépréciée, Creators API sans endpoint de conversions) et par API pour les trois autres. Prévois une **resynchronisation à J+7** : la latence de consolidation des rapports n'est pas documentée officiellement.
- Place le premier appel à l'action **tôt dans la vidéo** : la fenêtre Amazon d'ajout au panier est de 24 heures, la plus courte du lot.

---

## 11. Checklist de pré-publication automatisée — contrat pour l'étape 23.2

Exécutée sur le manifeste avant tout appel à `videos.insert`. **Bloquant** = le run s'arrête, rien n'est uploadé. **Avertissement** = consigné dans le rapport de run et affiché au tableau de bord, la publication continue.

| # | Contrôle | Verdict |
|---|---|---|
| 1 | `contains_synthetic_media` renseigné (non nul) et cohérent avec `synthetic_scenes[].realistic` | **Bloquant** |
| 2 | Toute scène réaliste générée figurant un lieu, une personne ou un événement ⇒ `contains_synthetic_media = true` | **Bloquant** |
| 3 | Toute image IA figurant un visage ou une silhouette ⇒ `virtual_images_mention = true` et mention « Images virtuelles » incrustée | **Bloquant** |
| 4 | Présence d'un lien d'affiliation en description ⇒ `paid_promotion = true` | **Bloquant** |
| 5 | Si `paid_promotion` : au moins un `sponsor_segments[]` avec `overlay_rendered = true` couvrant l'intégralité du segment | **Bloquant** |
| 6 | Si `paid_promotion` : mention orale dans les 30 premières secondes du segment (`spoken_disclosure_at_s ≤ start_s + 30`) | **Bloquant** |
| 7 | Si `paid_promotion` : `disclosure_lines[lang].description_line` en première ligne de description, dans la langue de la vidéo | **Bloquant** |
| 8 | Si un lien Amazon est présent : phrase contractuelle Amazon **mot pour mot** en description | **Bloquant** |
| 9 | Vocabulaire de divulgation conforme au réseau (`#ad`/`#sponsored` Impact, `#Ad`/`#PaidAd` Awin) | **Bloquant** |
| 10 | Chaque asset porte `licence`, `source_url`, `author` non vides ; aucune licence non commerciale ; fournisseur en liste blanche | **Bloquant** |
| 11 | `assets[].person_release` présent pour toute personne réelle identifiable | **Bloquant** |
| 12 | `music.licence` renseignée ; si `attribution_required` : `credit_line` présente en description | **Bloquant** |
| 13 | Bloc d'attribution des assets présent en description | **Bloquant** |
| 14 | `c2pa_preserved = true` sur le rendu final | Avertissement |
| 15 | `reviewer` non vide et `review_hash` == SHA-256 du script effectivement monté | **Bloquant** |
| 16 | `review_decision` ∈ {`approved`, `approved_with_edits`} | **Bloquant** — avertissement si `auto-approve` activé pour la chaîne |
| 17 | `editorial_angle.type` renseigné et `resume` d'au moins une phrase | **Bloquant** |
| 18 | `dedupe_hash.script_simhash` absent de l'index global des scripts publiés (similarité sous le seuil), toutes chaînes confondues | **Bloquant** |
| 19 | `dedupe_hash.thumbnail_phash` absent de l'index global des miniatures publiées | **Bloquant** |
| 20 | `template_id` différent des 2 dernières publications de la chaîne (rotation ≥ 3) | Avertissement |
| 21 | Titre et miniature cohérents avec le contenu du script (anti-clickbait) | Avertissement |
| 22 | `cadence_limits.published_this_week < max_per_week` et `now ≥ next_allowed_at` | **Bloquant** |
| 23 | Aucune autre chaîne du portefeuille ne publie dans la fenêtre ± 30 min ; jitter appliqué à l'heure cible | **Bloquant** |
| 24 | `publish_channel_account.owner == BMS`, Brand Account renseigné, `two_fa_enabled` et `phone_verified` vrais | **Bloquant** |
| 25 | Durée > 15 min ou miniature personnalisée ⇒ compte vérifié par téléphone | **Bloquant** |
| 26 | `publish_path` cohérent avec l'état de l'audit API (`manual_studio` tant que l'audit n'est pas obtenu) | **Bloquant** |
| 27 | Quota du jour : moins de 6 `videos.insert` déjà consommés sur le projet GCP | **Bloquant** |
| 28 | Aucun asset issu d'un téléchargement de vidéo tierce ; aucune trace d'appel à yt-dlp dans le journal du run | **Bloquant** |
| 29 | Cache de données API du registre âgé de moins de 30 jours (sinon rafraîchi ou purgé) | Avertissement |
| 30 | Aucun secret, jeton ou clé dans le manifeste, la description ou les métadonnées | **Bloquant** |

**Contrôle a posteriori** (hors checklist, exécuté après publication) : `videos.list(part=paidProductPlacementDetails)` — alerte si `hasPaidProductPlacement` est faux alors que `paid_promotion` est vrai. C'est le seul détecteur d'un oubli de la case manuelle en Studio (§ 3 couche 2).

---

## Sources

**YouTube — règles et monétisation**
- Politiques de monétisation, contenu inauthentique et contenu réutilisé : https://support.google.com/youtube/answer/1311392
- Divulgation du contenu altéré ou synthétique : https://support.google.com/youtube/answer/14328491
- Spam, pratiques trompeuses et arnaques : https://support.google.com/youtube/answer/2801973
- Conditions du YPP : https://support.google.com/youtube/answer/72851
- Accès étendu (fan funding) : https://support.google.com/youtube/answer/13429240
- Évolution des seuils : https://support.google.com/youtube/answer/12843009
- Audio Library : https://support.google.com/youtube/answer/3376882
- Divulgation de contenu de marque et promotion payante : https://support.google.com/youtube/answer/154235
- Terminaison de compte et chaînes associées : https://support.google.com/youtube/answer/2802168
- Fonctionnalités des comptes vérifiés : https://support.google.com/youtube/answer/171664

**YouTube — API**
- Ressource `videos` (`status.containsSyntheticMedia`) : https://developers.google.com/youtube/v3/docs/videos
- Historique des révisions de l'API : https://developers.google.com/youtube/v3/revision_history
- Quota et audit de conformité : https://developers.google.com/youtube/v3/guides/quota_and_compliance_audits
- Formulaire d'audit : https://support.google.com/youtube/contact/yt_api_form
- Conditions d'utilisation des services API : https://developers.google.com/youtube/terms/api-services-terms-of-service
- Developer Policies : https://developers.google.com/youtube/terms/developer-policies

**Droit français**
- Loi n° 2023-451, art. 1 (champ d'application) : https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000050468930
- Loi n° 2023-451, art. 5-2 (mention de l'intention commerciale, réd. ord. 2024-978) : https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000050457275
- Loi n° 2023-451, art. 5 I (images retouchées, « Images virtuelles ») : https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000050468897
- Sanctions des pratiques commerciales trompeuses : https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000049532070
- Pouvoirs d'injonction et d'astreinte de la DGCCRF : https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000051830385
- DGCCRF — devoirs des influenceurs : https://www.economie.gouv.fr/influenceurs-quels-sont-mes-devoirs

**Droit européen**
- RIA (règlement UE 2024/1689), art. 50 : https://ai-act-service-desk.ec.europa.eu/en/ai-act/article-50
- Commission européenne — FAQ sur les obligations de transparence de l'art. 50 : https://digital-strategy.ec.europa.eu/en/faqs/transparency-obligations-under-article-50-ai-act
- Code of Practice on Transparency of AI-generated Content (10/06/2026) : https://digital-strategy.ec.europa.eu/en/policies/code-practice-ai-generated-content
- RIA, art. 99 (sanctions) : https://artificialintelligenceact.eu/article/99/

**Programmes d'affiliation**
- Amazon Partenaires — conditions d'adhésion : https://partenaires.amazon.fr/help/node/topic/G8TW5AE9XL2VX9VM
- Amazon Partenaires — identifiants de suivi et sous-étiquettes : https://partenaires.amazon.fr/help/node/topic/GJDYPQZK6E37RLPU
- Amazon Partenaires — rapports et exports : https://partenaires.amazon.fr/help/topic/reports/faq
- Amazon Partenaires — fenêtre d'attribution : https://partenaires.amazon.fr/help/node/topic/G9SMD8TQHFJ7728F
- Amazon Partenaires — contrat d'exploitation (mention obligatoire) : https://partenaires.amazon.fr/help/operating/agreement
- Awin — références de clic (`clickref`) : https://www.awin.com/gb/news-and-events/tips-and-tricks/utilising-click-references
- Awin — Publisher API : https://help.awin.com/apidocs/api-authentication.md
- CJ — paramètre éditeur (`sid`, `shopperId`) : https://developers.cj.com/docs/publisher-site-tracking/publisher-parameter
- CJ — Commission Detail API : https://developers.cj.com/graphql/reference/Commission%20Detail
- Impact — paramètres Sub ID : https://help.impact.com/partner/what-would-you-like-to-learn-about/platform-features/tracking/tracking-links/link-parameters/sub-id-and-shared-id-parameters-explained-for-partners
- Impact — accord de service (divulgation en début de vidéo) : https://app.impact.com/content/displaympserviceagreement.ihtml

---

## Décisions prises à cette étape

1. **Projet Google Cloud unique** pour l'ensemble du portefeuille : un seul audit à obtenir, un seul délai à subir. L'isolation est payée au niveau du **compte Google propriétaire** (un par chaîne, Brand Account BMS), là où se joue réellement la clause de terminaison en cascade. Conséquence acceptée : une suspension du projet API coupe la publication automatique de toutes les chaînes ; le chemin manuel de la § 2 reste le plan de repli.
2. **Compte de recherche séparé** : un compte Google dédié aux étapes 3 et 16, jamais connecté sur une machine ou un navigateur servant à Studio, jamais lié aux chaînes publiantes, utilisé à faible volume depuis une IP résidentielle. Aucune donnée de recherche ne transite par les comptes publiants.
3. **Cadence initiale : 2 vidéos par chaîne et par semaine pendant 90 jours**, avec jitter horaire, intervalle minimal entre publications d'une même chaîne et fenêtre d'exclusion de ± 30 minutes à l'échelle du portefeuille. Toute augmentation est une décision explicite du client, chaîne par chaîne, après les 90 jours.
4. **Attribution par vidéo réservée à Awin, CJ et Impact** ; Amazon Partenaires est suivi par identifiant de chaîne et de langue. Aucun rapport de rentabilité par vidéo ne doit supposer Amazon.
5. **Le mode `auto-approve` est conservé** mais déclenche un avertissement permanent : quand il est actif, l'exception de responsabilité éditoriale du RIA art. 50 §4 n'est plus acquise. C'est un risque assumé par le client, chaîne par chaîne.
