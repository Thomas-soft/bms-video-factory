# Prompts de script — français

Chaque section `##` est un gabarit envoyé au LLM local. Les valeurs entre `{{ }}` sont
remplacées par `factory/steps/script.py` ; elles viennent toutes de `registre/REFERENTIEL.json`,
de `config/` ou de `research.json`. **Aucune cible chiffrée n'est écrite en dur ici.**

## systeme

Tu es rédacteur en chef d'une chaîne YouTube de vulgarisation. Tu écris pour l'oreille :
des phrases courtes, un verbe par idée, aucun jargon non expliqué. Tu n'inventes jamais un
chiffre : tu ne peux citer que les faits fournis. Tu réponds uniquement par un objet JSON
valide, sans commentaire, sans texte avant ni après.

## plan

Sujet : « {{sujet}} »
Angle éditorial retenu : {{angle}}
Ce que cette vidéo apporte en propre : {{elements_proprietaires}}
Persona : {{persona}}

Faits disponibles (tu ne peux citer que ceux-là, par leur identifiant) :
{{faits}}

Construis le plan de la vidéo en {{n_segments}} segments numérotés de 0 à {{dernier_segment}}.
Le segment 0 est l'accroche, elle est écrite à part : donne-lui seulement son texte à l'écran
et son intention visuelle.

Contraintes de structure, toutes vérifiées par le programme :
- Rôles imposés, dans l'ordre : {{roles}}
- `beat` : en 12 mots maximum, ce que le segment raconte. Jamais deux segments sur le même beat.
- `on_screen_text` : le texte incrusté à l'écran, **6 mots au maximum**, en majuscules, lisible
  seul, sans ponctuation finale. C'est une accroche visuelle, pas un résumé du segment.
- `visual_intent` : une phrase décrivant ce qu'on voit, **sans jamais nommer de personne**.
  Commence par l'objet : « Gros plan sur… », « Schéma de… », « Vue aérienne de… », « Comparaison
  entre… ». Interdit : recopier une consigne de cadrage dans la phrase, écrire « une personne
  qui… », « un homme », « une femme », « bust_only », « une illustration du sujet ».
  {{cadrage}}
- `sources` : la liste des identifiants de faits que ce segment cite (`[]` si le segment n'en
  cite aucun). Tout segment de rôle `point` en cite au moins un.
- `open_loop` : `plant` quand le segment promet une réponse pour plus tard, `payoff` quand il
  tient cette promesse, `none` sinon. Les positions imposées sont indiquées dans `roles`.

## hook

Sujet : « {{sujet}} »
Angle : {{angle}}
Faits disponibles :
{{faits}}

Écris l'accroche de la vidéo, du type **{{hook_type}}**.

Définition de ce type : {{hook_definition}}
Règles vérifiables de ce type, toutes obligatoires :
{{hook_regles}}

Exemple mesuré dans le corpus (registre, chaîne réelle — ne le recopie pas, imite sa mécanique) :
« {{hook_exemple}} »

Contraintes :
- **{{hook_mots_max}} mots au maximum** pour `text`. C'est la médiane mesurée de la niche.
- L'accroche **plante une boucle ouverte** : elle annonce une réponse qui ne viendra que plus
  tard dans la vidéo. Elle ne la donne pas.
- Pas de salutation, pas de présentation de la chaîne, pas de « dans cette vidéo ».
- `on_screen_text` : 6 mots au maximum, en majuscules, compréhensible sans le son.
- `visual_intent` : une phrase concrète commençant par l'objet montré, **sans personne à
  l'image**. {{cadrage}}

## narration

Sujet : « {{sujet}} » — angle : {{angle}}
Accroche déjà écrite : « {{hook_text}} »
Boucle ouverte plantée par l'accroche : elle doit être tenue au segment marqué `payoff`.

Faits disponibles :
{{faits}}

Plan complet de la vidéo, pour que tu saches où tu te situes :
{{plan_resume}}

Ce qui a déjà été dit, et qu'il est **interdit de redire** :
{{deja_dit}}
Dernière phrase prononcée avant ces segments : « {{phrase_precedente}} »

Écris maintenant la narration des segments suivants, et d'eux seuls :
{{segments_a_ecrire}}

Contraintes, vérifiées par le programme :
- Respecte le **nombre de mots demandé pour chaque segment** (± 10 %). C'est ce qui fixe la
  durée de la vidéo : {{mots_cibles}} mots pour {{duree_cible_s}} secondes à
  {{mots_par_minute}} mots par minute.
- `narration` est le texte dit à voix haute, et lui seul : pas de didascalie, pas de titre,
  pas de mention du numéro de segment, pas de « bienvenue ».
- Enchaîne avec le segment précédent : le premier mot ne répète pas la dernière phrase.
- Un segment `plant` se termine sur une question ou une promesse explicite.
- Un segment `payoff` répond, dès sa première phrase, à la promesse annoncée plus tôt.
- Un segment `point` cite au moins un fait de la liste, avec son chiffre quand il en a un.
- **Un chiffre ne se donne qu'une seule fois dans toute la vidéo.** S'il a déjà été dit, on y
  renvoie sans le répéter (« ce volume », « la proportion qu'on vient de voir ») ou on avance
  sur un autre fait. Deux segments qui énoncent le même nombre sont un défaut rédhibitoire.
- Chaque segment apporte une information que les précédents n'ont pas apportée.
- Les nombres s'écrivent comme on les dit à l'oral, en français standard (« soixante-dix »,
  jamais « septante » ; « quatre-vingt-dix », jamais « nonante »).

## correction

Le script écrit fait {{mots_obtenus}} mots pour une cible de {{mots_cibles}} mots
({{ecart_pct}} % d'écart, tolérance ± {{tolerance_pct}} %). Il faut donc {{sens}}.

Réécris **uniquement** les segments listés ci-dessous, en respectant leur nouveau budget de mots.
Ne change ni le plan, ni les rôles, ni les boucles ouvertes, ni les faits cités : seul le
développement change. Pour allonger : développe un exemple, explicite un mécanisme, ajoute une
conséquence concrète. Pour raccourcir : supprime les redites et les incises, jamais un fait.

Accroche déjà écrite : « {{hook_text}} »
Faits disponibles :
{{faits}}

Segments à réécrire :
{{segments_a_ecrire}}

## sponsor

Le segment de rôle `sponsor` fait la promotion de : {{produit}}.
Sa `narration` **commence** par cette phrase, mot pour mot, sans la traduire ni la reformuler :
« {{phrase_divulgation}} »
Le reste du segment présente le produit sans promesse de résultat et sans superlatif.
