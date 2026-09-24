# INTERFACES.md — contrats des fichiers, de la configuration et des commandes

**Statut :** contrat d'interface. Écrit à l'étape 8 (15/09/2026). Les étapes 9 à 31 l'implémentent ; l'étape 9 en fait des modèles pydantic v2.
**Document jumeau :** `docs/ARCHITECTURE.md` (principes, graphe, disque, mémoire). `docs/CONFORMITE.md` prime sur les deux.
**Aucun code exécutable ici :** les signatures et les exemples sont de la documentation. Les exemples sont volontairement courts et **tronqués** (`…`) ; c'est le tableau des champs qui fait foi.

---

## 0. Conventions

### Conventions communes à tous les fichiers

| Règle | Détail |
|---|---|
| Encodage | UTF-8, sans BOM. JSON indenté de 2 espaces, clés en `snake_case` anglais, valeurs de texte dans la langue du run |
| `schema_version` | Obligatoire sur tout fichier racine. `"<majeure>.<mineure>"`. Majeure différente = refus ; mineure inférieure = accepté avec `WARN`, défauts appliqués |
| Horodatages | ISO-8601 avec fuseau explicite, en UTC : `2026-09-18T21:14:07Z`. Les heures de publication *locales* sont dans la configuration de chaîne, jamais dans un fichier de run |
| Durées | Secondes, nombre flottant, suffixe `_s`. Les durées humaines (`target_duration_s`) sont entières |
| Identifiants de plan | `shot_00`, `shot_01`, … zéro-remplis sur 2 chiffres, 3 au-delà de 99 plans |
| Identifiants de segment | `seg_00`, `seg_01`, … |
| Écriture | `<nom>.tmp` puis `os.replace()`. Jamais d'écriture en place, jamais de JSON partiel sur disque |
| Nulls | Un champ non mesuré vaut `null` et porte un frère `<champ>_a_mesurer: true`. **Jamais une valeur inventée** (`CLAUDE.md` § 5) |
| Langue | `lang` est un code ISO-639-1 minuscule : `fr`, `en`, `es`, `it` |
| Secrets | Aucun fichier de run, de configuration ou de journal ne contient une valeur de secret. Seulement des `*_ref` pointant vers `secrets/` |

```json
{ "schema_version": "1.0", "generated_at": "2026-09-18T21:14:07Z", "generated_by": "factory 0.8.0" }
```

---

## 1. Fichiers d'un run

### spec.json
Écrit par `plan`. Contrat d'entrée de tout le pipeline : c'est le seul fichier qui fixe quoi produire.

| Champ | Type | Valeurs | Obligatoire |
|---|---|---|---|
| `schema_version` | str | `"1.0"` | oui |
| `video_id` | str | `<channel_id>-<AAAAMMJJ>-<4 car.>` | oui |
| `parent_id` | str \| null | `video_id` du run source si déclinaison | non |
| `channel_id` | str | doit exister dans `config/channels/` | oui |
| `lang` | str | ISO-639-1, **égal à `channel.lang`** | oui |
| `niche` | str | doit exister dans `config/niches/` | oui |
| `style` | str | doit exister dans `config/styles/` | oui |
| `topic.sujet` | str | ≤ 200 car. | oui |
| `topic.angle` | str | une phrase, l'angle éditorial propre | oui |
| `topic.source` | enum | `topics_queue` \| `referentiel` \| `manuel` | oui |
| `topic.evidence` | objet | preuve du choix : `{score, vues_medianes_chaine, ratio, n, requete}` ; `{}` si `manuel` | oui |
| `target_duration_s` | int | de `niche.duree_s.cible` ± `tolerance`, ou surcharge de chaîne | oui |
| `cut_rhythm_target_s` | float | de `niche.rythme_coupe_s.cible_montage`, repli `cible`, repli `fallback_provisoire_s` | oui |
| `seed` | int | 0 … 2⁶⁴−1, tirée une fois, **jamais retirée** | oui |
| `product_id` | str \| null | doit exister dans `config/products/` ; non nul ⇒ `paid_promotion = true` | non |
| `created_at` | str | ISO-8601 UTC | oui |

```json
{
  "schema_version": "1.0", "video_id": "bms-science-en-20260918-k7q2", "parent_id": null,
  "channel_id": "bms-science-en", "lang": "en", "niche": "science_pop", "style": "illustre",
  "topic": { "sujet": "Why your brain deletes memories while you sleep", "angle": "comparaison_chiffree",
             "source": "topics_queue",
             "evidence": { "score": 0.81, "vues_medianes_chaine": 41200, "ratio": 3.4, "n": 12 } },
  "target_duration_s": 648, "cut_rhythm_target_s": 5.85, "seed": 8123457690123456789,
  "product_id": null, "created_at": "2026-09-18T21:14:07Z"
}
```

### research.json
Écrit par `research`. Faits sourcés, sur sources gratuites et citables. Aucun téléchargement de vidéo tierce (`CONFORMITE.md` § 9).

| Champ | Type | Détail |
|---|---|---|
| `facts[]` | liste | `{id, claim, value, unit, date, source_url, source_title, licence, confidence: high\|medium\|low, retrieved_at}` |
| `entities[]` | liste | `{name, type: person\|place\|org\|concept, real_person: bool}` — `real_person` alimente le contrôle 11 de la checklist |
| `open_questions[]` | liste[str] | ce que la recherche n'a pas tranché ; le script ne doit pas l'affirmer |
| `sources_rejected[]` | liste | `{url, reason}` — trace de ce qui a été écarté, et pourquoi |
| `fact_count` | int | sert à `density_facts_per_min` au manifeste |
| `lang` / `sujet` | str | langue de rédaction et sujet repris de `spec.topic.sujet` |
| `sources[]` | liste | `{url, title, api, lang, licence, retrieved_at, fact_ids[]}` — **≥ 3**. `api` ∈ `wikipedia` \| `wikidata` \| `pubmed` \| `openlibrary` \| `arxiv` \| `semantic_scholar`. L'URL, le titre et la licence viennent de la collecte HTTP, **jamais du LLM** |
| `source_count` | int | doit valoir `len(sources)`, comme `fact_count` vaut `len(facts)` |
| `angles_proposes[]` | liste | `{type: contrarien \| comparatif_chiffre \| recit, phrase, angle_signature}` — les trois angles proposés, y compris les deux écartés |
| `angle` | str | l'angle retenu, en une phrase, recopié dans `spec.topic.angle` et `manifest.decisions.topic.angle` |
| `angle_signature` | enum | `opinion` \| `comparaison_chiffree` \| `test` \| `donnee_proprietaire` — alimente `script.editorial_signature.angle` |
| `elements_proprietaires[]` | liste[str] | ce que la vidéo apportera en propre (`CONFORMITE.md` § 4) ; recopié dans `script.editorial_signature` |

```json
{ "schema_version": "1.0",
  "facts": [ { "id": "f01", "claim": "Le sommeil lent élimine une part des synapses formées le jour",
               "value": 18, "unit": "%", "date": "2017-02-03",
               "source_url": "https://www.science.org/doi/10.1126/science.aai8355",
               "source_title": "Science, 355(6324)", "licence": "citation",
               "confidence": "high", "retrieved_at": "2026-09-18T21:15:02Z" } ],
  "entities": [ { "name": "Chiara Cirelli", "type": "person", "real_person": true } ],
  "open_questions": [ "La proportion varie-t-elle avec l'âge ?" ],
  "sources_rejected": [ { "url": "https://…/blog", "reason": "sans source primaire" } ],
  "fact_count": 14 }
```

### script.json
Écrit par `script`, relu par `review`, **fait foi pour le texte** — l'ASR ne fournira que le timing.

| Champ | Type | Valeurs permises |
|---|---|---|
| `hook.type` | enum | un type de `REFERENTIEL.json` → `hooks_taxonomie`, **jamais `intro_chaine_neutre`** (`productible: false`) |
| `hook.text` | str | le texte du hook, dans `lang` |
| `segments[].id` | str | `seg_00`, … |
| `segments[].role` | enum | `hook` \| `contexte` \| `point` \| `rupture` \| `sponsor` \| `cta` \| `conclusion` |
| `segments[].narration` | str | texte dit à voix haute, **seul texte envoyé au TTS** |
| `segments[].on_screen_text` | str \| null | texte incrusté ; `null` si aucun |
| `segments[].visual_intent` | str | une phrase décrivant ce qu'on voit ; **contrainte de charte : buste ou objet, jamais un personnage en pied en mouvement** |
| `segments[].open_loop` | enum | `plant` \| `payoff` \| `none` — **≥ 2 `plant` par script**, chacun avec son `payoff` |
| `segments[].interrupt` | objet \| null | rupture de rythme programmée : `{type: question\|chiffre\|changement_de_plan\|mini_recit\|silence, at_s_relative}` (`mini_recit` ajouté à l'étape 16 ; `silence` conservé pour les runs antérieurs, plus tiré) |
| `segments[].sources[]` | liste[str] | ids de `research.facts[]` ; un segment `point` sans source est rejeté par l'étape 16 |
| `segments[].disclosure_spoken` | bool | vrai pour la phrase de divulgation orale. **Obligatoire dans les 30 premières secondes de tout segment `sponsor`** (`CONFORMITE.md` § 11, contrôle 6, bloquant) : c'est ici qu'elle est écrite, donc relue par l'humain, donc couverte par `review_hash` |
| `editorial_signature.angle` | enum | `opinion` \| `comparaison_chiffree` \| `test` \| `donnee_proprietaire` (`CONFORMITE.md` § 4, liste fermée) |
| `editorial_signature.elements_proprietaires[]` | liste[str] | ce que cette vidéo apporte et qu'aucune source ne contient |
| `word_count` | int | mots de narration, hors texte à l'écran |
| `estimated_duration_s` | float | `word_count / niche.mots_par_minute.mediane × 60` |
| `lang` | str | ISO-639-1 |
| `disclosure_lines` | objet \| null | `{description_line, overlay_text, spoken_line}` dans `lang` ; obligatoire si `product_id` ou `virtual_images_mention` |

```json
{ "schema_version": "1.0", "lang": "en",
  "hook": { "type": "question_contrarienne", "text": "What if forgetting is the point?" },
  "segments": [
    { "id": "seg_00", "role": "hook", "narration": "What if forgetting is the point?",
      "on_screen_text": "FORGETTING IS THE POINT", "visual_intent": "Gros plan d'un réveil à 3 h du matin",
      "open_loop": "plant", "interrupt": null, "sources": [] },
    { "id": "seg_04", "role": "point", "narration": "Slow-wave sleep prunes about 18 % of the day's synapses.",
      "on_screen_text": "-18 %", "visual_intent": "Schéma de deux synapses, l'une s'efface",
      "open_loop": "payoff", "interrupt": { "type": "chiffre", "at_s_relative": 2.0 }, "sources": ["f01"] }
  ],
  "editorial_signature": { "angle": "comparaison_chiffree",
    "elements_proprietaires": ["Comparaison des 3 études sur une même échelle de pourcentage"] },
  "word_count": 1458, "estimated_duration_s": 648.0, "disclosure_lines": null }
```

### review.json
Écrit par `review`. Miroir dans un run de la ligne append-only de `registre/data/reviews.jsonl` (`CONFORMITE.md` § 10.2). **La ligne du journal fait foi** : c'est elle qui est produite en cas de contrôle.

| Champ | Type | Détail |
|---|---|---|
| `reviewer` | str | identité nommée de `config/team.yaml`, ou `"auto-approve"` — « l'équipe » n'est pas une réponse valable |
| `review_date` | str | ISO-8601 UTC |
| `review_hash` | str | SHA-256 du `script.json` **relu** (sérialisation canonique : clés triées, séparateurs compacts) |
| `decision` | enum | `approved` \| `approved_with_edits` \| `rejected` \| `auto` |
| `comment` | str | libre ; obligatoire si `rejected` ou `approved_with_edits` |
| `edits[]` | liste | `{segment_id, field, before_hash, after_hash}` si `approved_with_edits` |
| `batch_id` | str | lot de relecture ; la relecture est **par lots**, jamais plan par plan |
| `ria_exception_claimed` | bool | `false` si `reviewer == "auto-approve"` — c'est ce champ qui dit si l'exception éditoriale RIA est revendiquée pour cette vidéo |

```json
{ "schema_version": "1.0", "reviewer": "Sofiane", "review_date": "2026-09-19T08:40:00Z",
  "review_hash": "6f3c…a91b", "decision": "approved_with_edits",
  "comment": "Chiffre du seg_04 arrondi ; hook raccourci de 4 mots.",
  "edits": [ { "segment_id": "seg_04", "field": "narration", "before_hash": "11a…", "after_hash": "8c2…" } ],
  "batch_id": "2026-W38-b1", "ria_exception_claimed": true }
```

### voice/timings.json
Écrit par `voice`. Un enregistrement par **segment synthétisé**, dans l'ordre de concaténation.

| Champ | Type | Détail |
|---|---|---|
| `segments[].id` | str | `seg_XX` d'origine ; si des segments ont été **fusionnés**, `merged_from[]` les liste |
| `segments[].merged_from[]` | liste[str] | fusion imposée par le contrat : **on ne synthétise pas sous 15 s** (§ 2.2 d'`ARCHITECTURE.md`) |
| `segments[].file` | str | `voice/segment_XX.wav` |
| `segments[].start_s` / `end_s` / `duration_s` | float | position dans `voice/voice.wav` |
| `segments[].text` | str | texte réellement envoyé au TTS |
| `segments[].disclosure_at_s` | float \| null | début absolu de la phrase `disclosure_spoken` dans `voice.wav` ; alimente `sponsor_segments[].spoken_disclosure_at_s` |
| `voice_id` | str | voix de la chaîne, doit appartenir à `config/languages/<lang>.yaml` |
| `loudness_lufs` / `true_peak_dbtp` | float | cibles `-14,0` et `-1,0` (`REFERENTIEL.json` → `production`) |
| `sample_rate` / `channels` | int | 24 000 Hz, 1 |
| `total_duration_s` | float | durée de `voice.wav` ; entre dans `manifest.duration_s` |

```json
{ "schema_version": "1.0", "voice_id": "serena_en", "sample_rate": 24000, "channels": 1,
  "loudness_lufs": -14.0, "true_peak_dbtp": -1.1, "total_duration_s": 651.3,
  "segments": [ { "id": "seg_00", "merged_from": ["seg_00", "seg_01"], "file": "voice/segment_00.wav",
                  "start_s": 0.0, "end_s": 17.4, "duration_s": 17.4,
                  "text": "What if forgetting is the point? …", "disclosure_at_s": null } ] }
```

### words.json
Écrit par `subtitles`. Mots horodatés. **Le texte vient du script, le timing vient de l'ASR** : un mot que l'ASR a mal entendu porte le mot du script et `asr_confidence` bas, jamais le mot faux.

| Champ | Type | Détail |
|---|---|---|
| `words[].w` | str | mot **du script**, après alignement |
| `words[].start_s` / `end_s` | float | horodatage ASR aligné |
| `words[].seg` | str | `seg_XX` d'appartenance |
| `words[].asr_confidence` | float \| null | 0 … 1 |
| `coverage` | float | mots alignés ÷ mots du script. **Cible 1,0** (`REFERENTIEL.json` → `production.couverture_sous_titres`) |
| `wer_vs_script` | float | WER global contre le texte source |
| `engine` | enum | `parakeet` \| `whisper` |
| `fallback_reason` | str \| null | non nul si `engine == "whisper"` : `coverage_below_threshold` \| `wer_above_threshold` \| `language_drift` \| `operator_override` |
| `segments[]` | liste | `{id, coverage, wer_vs_script, wer_threshold, engine}` — **le WER par segment vit ici, pas dans `voice/timings.json`** : `subtitles` n'écrit jamais dans une sortie de `voice`, sinon le `.done` de `voice` et l'`inputs_hash` de `shotlist` deviendraient faux |
| `wer_threshold` | float | seuil **fonction de la longueur du segment**, lu dans `config/languages/<code>.yaml → asr.wer_thresholds` : ≤ 5 mots ⇒ 0,20 ; 6–20 ⇒ 0,15 ; > 20 ⇒ 0,08. Un seuil unique ne peut pas s'appliquer aux deux bouts : sur 5 mots, un seul mot faux vaut déjà 20 % |

**Règle de repli, mesurée et non négociable.** parakeet tronque 2 fichiers sur 8 et **traduit le français en anglais entre ~5 et ~10 s** (étape 7, WER 63 à 84 % là où whisper est à 0 %). `subtitles` mesure **couverture et WER** ; si `coverage < 0,98` **ou** `wer_vs_script > wer_threshold`, il rejoue avec whisper et conserve le meilleur des deux. La couverture seule ne suffit pas : à 2 s elle vaut 100–120 % avec tous les mots faux.

```json
{ "schema_version": "1.0", "engine": "parakeet", "fallback_reason": null,
  "coverage": 1.0, "wer_vs_script": 0.019, "wer_threshold": 0.08,
  "segments": [ { "id": "seg_00", "coverage": 1.0, "wer_vs_script": 0.021,
                  "wer_threshold": 0.08, "engine": "parakeet" } ],
  "words": [ { "w": "What", "start_s": 0.32, "end_s": 0.49, "seg": "seg_00", "asr_confidence": 0.99 },
             { "w": "if",   "start_s": 0.49, "end_s": 0.58, "seg": "seg_00", "asr_confidence": 0.98 } ] }
```

### subtitles.srt et subtitles.ass
Écrits par `subtitles`. `.srt` = distribution (piste `captions.insert` de l'API, 400 unités de quota). `.ass` = incrustation, **style lu dans la charte de la chaîne**, jamais en dur.

| Source du style | Champ de la charte |
|---|---|
| Police, graisse, taille | `charte.subtitles.font`, `.weight`, `.size_px` |
| Couleurs | `charte.palette.text`, `.text_outline`, `.highlight` |
| Position | `charte.subtitles.align` (`bottom_center` \| `bottom_left` \| `middle_center`), `.margin_v_px` |
| Mise en avant du mot dit | `charte.subtitles.karaoke: bool` — utilise `words.json` |
| Longueur de ligne | `charte.subtitles.max_chars_per_line` (défaut 38), `max_lines: 2` |
| Incrustation | `charte.subtitles.burn_in` (bool). **Exclusif de `metadata.caption_file`** : incruster *et* envoyer la piste donne un double affichage chez le spectateur et dépense 400 unités de quota pour rien. `config validate` refuse les deux à la fois |

```text
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, Bold, Alignment, MarginV
Style: BMS, Inter SemiBold, 64, &H00FFFFFF, &H00101010, -1, 2, 96

[Events]
Dialogue: 0,0:00:00.32,0:00:02.10,BMS,,0,0,0,,{\k32}What {\k17}if {\k21}forgetting…
```

### shotlist.json
Écrit par `shotlist`. C'est le pivot du système : il traduit un script en plans, et c'est lui qui porte le drapeau qui déclenche la barrière humaine et la mention « Images virtuelles ».

| Champ | Type | Valeurs permises |
|---|---|---|
| `shots[].id` | str | `shot_00`, … |
| `shots[].segment_id` | str | `seg_XX` — jointure obligatoire vers `script.json` |
| `shots[].start_s` / `end_s` / `duration_s` | float | issus de `words.json` : un plan ne coupe jamais au milieu d'un mot |
| `shots[].visual_intent` | str | hérité du segment, précisé pour ce plan |
| `shots[].on_screen_text` | str \| null | |
| `shots[].asset_request.type` | enum | `image` \| `stock` \| `card` \| `avatar` |
| `shots[].asset_request.prompt_or_keywords` | str | prompt complet si `image` ; mots-clés de banque si `stock` |
| `shots[].asset_request.reuse_ok` | bool | autorise la bibliothèque ; `false` pour un plan à texte incrusté |
| `shots[].asset_request.layer` | enum | `foreground` \| `background`. Sans ce champ, la règle « aucun asset de premier plan partagé entre deux chaînes de même langue » (`ARCHITECTURE.md` § 4) serait inapplicable |
| `shots[].asset_request.contains_person` | bool | **champ décisif** : déclenche la barrière humaine et `virtual_images_mention` |
| `shots[].asset_request.realistic` | bool | scène réaliste figurant un lieu, une personne ou un événement ⇒ `contains_synthetic_media` |
| `shots[].motion` | enum | `zoom_in` \| `zoom_out` \| `pan` \| `parallax` \| `static` |
| `shots[].transition_in` | enum | `cut` \| `fade` \| `dip_black` \| `whip` \| `none` — restreinte par `charte.transitions[]` |
| `shots[].is_sponsor` | bool | vrai ⇒ bandeau de divulgation incrusté sur **tout** le plan |
| `shots[].interrupt` | objet \| null | repris du segment |
| `shots[].seed` | int | `sha256(video_id + shot_id)` — déterminisme par plan |
| `stats.median_shot_s` | float | mesurée sur la liste produite |
| `stats.target_s` | float | `spec.cut_rhythm_target_s` |
| `stats.hook_shots_max_s` | float | `target_s × niche.rythme_coupe_s.facteur_hook` (0,7) |
| `stats.tolerance` | float | 0,10 — la médiane produite doit être à ± 10 % de la cible |

```json
{ "schema_version": "1.0",
  "stats": { "median_shot_s": 5.8, "target_s": 5.85, "hook_shots_max_s": 4.1, "tolerance": 0.10 },
  "shots": [
    { "id": "shot_00", "segment_id": "seg_00", "start_s": 0.0, "end_s": 3.9, "duration_s": 3.9,
      "visual_intent": "Gros plan d'un réveil à 3 h du matin", "on_screen_text": "FORGETTING IS THE POINT",
      "asset_request": { "type": "image", "prompt_or_keywords": "close-up of an alarm clock at 3am, …",
                         "reuse_ok": false, "contains_person": false, "realistic": false },
      "motion": "zoom_in", "transition_in": "cut", "is_sponsor": false, "interrupt": null,
      "seed": 3901284771 } ] }
```

### assets/<shot>/licence.json
Écrit par `assets`, un fichier par plan. **Un asset sans ces champs ne descend pas dans le pipeline** : le contrôle est à l'acquisition, pas au montage (`CONFORMITE.md` § 8). Ces champs remontent tels quels dans `manifest.assets[]`.

| Champ | Type | Détail |
|---|---|---|
| `asset_id` | str | `sha256(fichier)[:16]` — identifiant stable, réutilisable en bibliothèque |
| `path` | str | relatif au run |
| `provider` | enum | `flux` \| `pexels` \| `pixabay` \| `openverse` \| `wikimedia` \| `nasa` \| `internet_archive` \| `library` \| `charte`. **Liste blanche** ; tout autre exige une décision tracée dans `STATE.md` |
| `source_url` | str \| null | null seulement si `provider == "flux"` (généré localement) |
| `author` | str | « BMS (généré) » pour les images locales |
| `licence` | str | SPDX ou nom exact. **Toute licence non commerciale est éliminatoire** |
| `licence_url` | str | |
| `attribution_line` | str \| null | agrégée automatiquement en fin de description |
| `downloaded_at` | str | ISO-8601 UTC |
| `person_release` | str \| null | droit enregistré si une personne réelle identifiable figure ; **absence ⇒ plan refusé** |
| `generator` | objet \| null | si généré : `{model, model_revision, prompt_hash, seed, steps, resolution}` |
| `realistic` | bool | posé **au moment de la génération**, pas à l'upload — un drapeau reconstitué après coup est un drapeau faux |
| `has_text` | bool | texte incrusté dans l'image ⇒ jamais réutilisable dans une autre langue |
| `c2pa_present` | bool | métadonnées de provenance présentes ; **ne jamais les retirer** au montage ni au réencodage |

```json
{ "schema_version": "1.0", "asset_id": "9c1f4b77ad02e35a", "path": "assets/shot_00/image.png",
  "provider": "flux", "source_url": null, "author": "BMS (généré)",
  "licence": "Apache-2.0", "licence_url": "https://www.apache.org/licenses/LICENSE-2.0",
  "attribution_line": null, "downloaded_at": "2026-09-19T02:11:40Z", "person_release": null,
  "generator": { "model": "mlx-community/FLUX.2-Klein-4B-4bit", "model_revision": "a3f19c",
                 "prompt_hash": "77ce…", "seed": 3901284771, "steps": 4, "resolution": "1280x720" },
  "realistic": false, "has_text": false, "c2pa_present": true }
```

### clips/shot_XX.mp4, video_nomusic.mp4, final.mp4
Écrits par `render` et `assemble`. Contrat de format, vérifié par `ffprobe` et non déclaré.

| Fichier | Contrat |
|---|---|
| `clips/shot_XX.mp4` | H.264 `yuv420p`, 1920×1080, 30 ips **constantes**, sans audio, `-crf 18`, durée = `shots[].duration_s` à ± 1 image. Un clip hors tolérance fait échouer `render` sur ce plan, pas sur le run |
| `video_nomusic.mp4` | Concaténation des clips + `voice/voice.wav`, sous-titres **non** incrustés. Sert au QC de lisibilité et au diagnostic |
| `final.mp4` | H.264 1080p30, AAC 192 kb/s, sous-titres incrustés depuis `subtitles.ass`, lit musical mixé avec ducking, `faststart`. **Loudness −14 LUFS, true peak −1 dBTP**, mesurés par `ebur128` dans `qc.json`, pas supposés |

Deux règles de rendu qui viennent de mesures : `zoompan` **suréchantillonné ×4** (le suréchantillonnage ne coûte que 1,2 s et supprime le jitter) ; parallaxe à **masques cumulatifs** (chaque couche porte tout ce qui est plus proche) avec rampe d'alpha et flou de 3 px — le contrôle de non-régression rejoue le clip sur fond magenta et **échoue si un seul pixel magenta subsiste**.

### thumbnails/thumbnails.json, thumbnail.png et thumbnails/variant_X.png
Écrits par `thumbnail`, **avant** `metadata` dans le DAG : la miniature ne dépend donc pas du titre. Son texte vient de `script.json` (hook, `on_screen_text`) et de la cible de la niche, jamais d'un titre qui n'existe pas encore. `metadata` lit ensuite `thumbnails.json` et n'en recalcule rien. `thumbnail.png` est une **copie** de la variante retenue, pas un lien : le fichier envoyé à YouTube doit exister seul.

| Champ de `thumbnails/thumbnails.json` | Détail |
|---|---|
| `variants[].file` | `thumbnails/variant_1.png` … ≥ 3 variantes |
| `variants[].text` | mots incrustés ; cible par niche (`REFERENTIEL.json` → `miniatures.mots_texte_median`) |
| `variants[].template` | gabarit employé ; **les trois variantes diffèrent deux à deux** sur `(template, palette)`, étape 21 |
| `variants[].palette` | `charte` \| `accent` \| `inverse` — permutation des couleurs de la charte, jamais une couleur en dur |
| `variants[].measures` | `{contrast_ratio, text_area_pct, text_height_px_168, sharpness_168, saliency_under_text, palette_distance, text_overflow_pct}` — **toutes lues sur le PNG rendu** (étape 21) |
| `variants[].contrast_ratio` | WCAG, **cible ≥ 4,5** (extrait de `measures`, conservé pour le QC) |
| `variants[].text_area_ratio` | surface de texte ÷ surface totale (extrait de `measures`) |
| `variants[].legible_at_320px` | bool, lisibilité à petite taille : hauteur ≥ 10 px à 168 px **et** contraste ≥ 4,5 |
| `variants[].phash` | empreinte perceptuelle → `dedupe_hash.thumbnail_phash` |
| `chosen` | nom de la variante retenue |
| `chosen_reason` | `score` \| `manuel` \| `dedupe_conflict` |
| `rotation` | `{after_days, criterion, next_variants[], rotations_done}` — plan de rotation écrit à la production, exécuté par la phase 5 (étape 21) |

**Rotation, et pourquoi pas un test A/B.** « Test & Compare » de YouTube accepte trois miniatures, départage sur la part de temps de visionnage et clôt en deux semaines, mais il vit dans Studio **bureau** et n'a **aucune ressource dans la Data API v3** — ni création, ni lecture, ni résultat (vérifié à l'étape 21). La seule comparaison automatisable est donc la rotation : `thumbnails.set` (50 unités) après `after_days` si `criterion` est rempli, la Reporting API étant la seule à donner impressions et CTR. Ce n'est **pas** une expérience contrôlée : elle compare deux périodes, pas deux populations tirées au sort.

Format : PNG 1280×720, < 2 Mo (limite YouTube). Détourage éventuel par rembg **toujours avec `-m birefnet-general`** : le modèle par défaut `bria-rmbg` exige un contrat payant en usage commercial.

```json
{ "schema_version": "1.0", "chosen": "variant_1", "chosen_reason": "score",
  "variants": [ { "file": "thumbnails/variant_1.png", "text": "18 % GONE", "contrast_ratio": 7.1,
                  "text_area_ratio": 0.14, "legible_at_320px": true, "phash": "f0e2…", "score": 0.82 },
                { "file": "thumbnails/variant_2.png", "text": "YOUR BRAIN DELETES", "contrast_ratio": 4.9,
                  "text_area_ratio": 0.22, "legible_at_320px": true, "phash": "b731…", "score": 0.61 } ] }
```

### metadata.json
Écrit par `metadata`. C'est ce que `publish` envoie à l'API, mot pour mot. Aucune transformation à l'upload.

| Champ | Type | Détail |
|---|---|---|
| `title_variants[]` | liste | `{text, pattern_id, length_char, heuristic, llm_rank, promise_kept, score}` — patrons de la niche, ≤ 70 caractères (troncature d'affichage), plafond dur YouTube 100. `heuristic` = note de règles, `llm_rank` = rang du tournoi de duels (1 = meilleur, `null` hors tournoi), `promise_kept` = le script tient-il la promesse (`null` = non vérifié, **jamais** lu comme un oui). Le champ s'appelait `pattern` avant l'étape 21 et se lit encore sous ce nom |
| `title_chosen` | str | |
| `description` | str | **ordre imposé** : ligne de divulgation (§ 3 couche 3) → accroche → chapitres → liens d'affiliation → bloc d'attribution des assets → crédit musical |
| `description_blocks` | objet | `{disclosure, hook, summary[], chapters[], sources[], affiliate[], attribution[], music_credit}` — la description est **composée**, jamais écrite à la main. `summary` (étape 21) donne le *quoi* là où `chapters` donne le *quand* |
| `description` (plafond) | — | **5 000 octets**, pas 5 000 caractères : c'est ainsi que l'API compte, et un tiret cadratin en vaut trois (étape 21) |
| `tags[]` | liste[str] | ≤ 500 caractères cumulés, **guillemets compris** : un tag contenant une espace est traité par l'API comme s'il était entre guillemets, donc +2 caractères (étape 21) |
| `hashtags[]` | liste[str] | ≤ 3 affichés au-dessus du titre ; exigés par l'étape 21. Au-delà de **60** dans la description, YouTube les ignore tous. Les mots qui nomment le sujet passent avant ceux du découpage des textes à l'écran |
| `localizations` | objet | `{<lang>: {title, description}}` — versions localisées de la fiche, étapes 21 et 24. **Vide tant que l'étape 24 n'a pas tourné** : elles sont lues dans `config/channels/<id>.yaml → localizations`, jamais traduites à la volée |
| `pinned_comment` | str \| null | commentaire épinglé : question d'engagement (du segment `cta` du script, du hook, sinon `config/languages/<lang>.yaml → titres.question_engagement`) puis lien produit **portant le même sous-identifiant que la description**, étapes 21 et 27. **Soumis aux mêmes divulgations que la description** |
| `category_id` | str | id de catégorie YouTube |
| `default_language` / `default_audio_language` | str | = `lang` |
| `recording_date` | str \| null | |
| `chapters[]` | liste | `{start_s, title}` ; le premier est obligatoirement à `0` |
| `contains_synthetic_media` | bool | recopié du manifeste, **jamais recalculé ici** |
| `paid_promotion` | bool | idem |
| `playlist_id` | str \| null | de la configuration de chaîne |
| `caption_file` | str | `subtitles.srt` |
| `thumbnail_file` | str | recopié de `thumbnails/thumbnails.json → chosen` ; `metadata` ne choisit pas la miniature, il la constate |

```json
{ "schema_version": "1.0", "title_chosen": "Your Brain Deletes 18 % Of What You Learn Today",
  "title_variants": [ { "text": "Your Brain Deletes 18 % Of What You Learn Today",
                        "pattern": "chiffre_en_tete", "length_char": 47, "score": 0.78 } ],
  "description_blocks": { "disclosure": null, "hook": "Forgetting is not a bug…",
    "chapters": [ { "start_s": 0, "title": "The 3 a.m. question" } ],
    "affiliate": [], "attribution": ["Photo : NASA/JPL, domaine public"],
    "music_credit": "« Slow Drift » — YouTube Audio Library (CC-BY, crédit requis)" },
  "tags": ["neuroscience", "sleep", "memory"], "category_id": "28",
  "default_language": "en", "default_audio_language": "en",
  "contains_synthetic_media": false, "paid_promotion": false,
  "playlist_id": "PLxxxx", "caption_file": "subtitles.srt" }
```

### qc.json
Écrit par `qc`. Entrées : `final.mp4`, `script.json`, `shotlist.json`, **`words.json`** (sans lui `subtitle_coverage` n'est pas mesurable), `research.json` (densité de faits) et `config/qc.yaml`. Chaque contrôle compare une **mesure** à la cible de la niche. Une cible marquée `a_mesurer` dans le référentiel **ne doit pas être notée comme un écart** — elle est rendue `skipped`.

| Champ | Type | Détail |
|---|---|---|
| `checks[].id` | str | `cut_rhythm`, `duration`, `loudness`, `true_peak`, `silence`, `speech_rate`, `text_legibility`, `hook_form`, `visual_variety`, `subtitle_coverage`, `magenta_holes`, `c2pa`, `density_facts_per_min`, `interrupt_cadence`, `open_loops` — les trois derniers viennent de l'étape 16 |
| `checks[].measured` | nombre \| bool \| null | `null` ⇒ `status: skipped` |
| `checks[].target` / `tolerance` | nombre | de `config/qc.yaml` et du référentiel de la niche |
| `checks[].status` | enum | `pass` \| `warn` \| `fail` \| `skipped` |
| `checks[].source` | str | outil et méthode (`ffmpeg ebur128`, `PySceneDetect`, `tesseract fast`) |
| `score` | float | 0 … 100, pondéré par `config/qc.yaml` |
| `verdict` | enum | `pass` \| `regenerate` \| `blocked` |
| `regenerate_steps[]` | liste[str] | étapes à rejouer si `regenerate` — c'est ce champ que l'étape 22.2 consomme |

```json
{ "schema_version": "1.0", "score": 86.4, "verdict": "pass", "regenerate_steps": [],
  "checks": [
    { "id": "cut_rhythm", "measured": 5.8, "target": 5.85, "tolerance": 0.15, "status": "pass",
      "source": "PySceneDetect 0.7.1" },
    { "id": "loudness", "measured": -14.1, "target": -14.0, "tolerance": 0.5, "status": "pass",
      "source": "ffmpeg ebur128" },
    { "id": "silence", "measured": null, "target": null, "tolerance": null, "status": "skipped",
      "source": "cible a_mesurer dans REFERENTIEL.json" } ] }
```

### publish.json
Écrit par `publish`. Porte l'état réel côté YouTube et la comptabilité de quota.

| Champ | Type | Détail |
|---|---|---|
| `publish_path` | enum | `manual_studio` \| `api_scheduled` — un seul chemin de code, un drapeau |
| `publish_state` | enum | `draft` → `ready_to_publish` → `uploaded_private` → `scheduled` → `public` |
| `checklist[]` | liste | les **30 contrôles** de `CONFORMITE.md` § 11 : `{n, id, verdict: pass\|warn\|fail, detail}` |
| `youtube_video_id` | str \| null | **clé de jointure de la boucle de rétroaction** |
| `uploaded_at` | str \| null | écrit par `publish` |
| `publish_at` | str \| null | date de programmation visée |
| `published_at` | str \| null | **personne ne peut l'écrire en `manual_studio`** : c'est un humain qui met la vidéo en ligne dans Studio. `analytics pull` le **rétro-remplit** depuis `videos.list(part=status,snippet)` à chaque passage, et c'est lui qui fait démarrer les fenêtres J+7 et J+30. Sans ce rattrapage, aucune métrique ne serait jointe sur le seul chemin ouvert avant l'audit |
| `thumbnail_set` / `caption_id` / `playlist_item_id` | bool / str | |
| `quota_units_spent` | int | `videos.insert` 1600, `thumbnails.set` 50, `captions.insert` 400 |
| `quota_day` | str | `AAAA-MM-JJ` UTC. **Le plafond opérant est de 4 publications complètes par jour**, pas 6 — voir l'encadré ci-dessous |
| `reporting_job_id` | str \| null | job Reporting API. **Créé avant la première publication de la chaîne** : il n'y a aucun rétroactif, sans lui impressions et CTR sont perdus pour toujours |
| `manual_steps[]` | liste | `{id: paid_promotion_box\|schedule\|other, required: bool, done: bool, done_at}` |
| `post_check.has_paid_product_placement` | bool \| null | relu par `videos.list` — seul détecteur d'un oubli de la case manuelle |
| `retry_count` / `last_error` | int / str | |

**~~Le plafond de 6 de `CONFORMITE.md` § 2 ne tient pas si la vidéo est complète.~~ Corrigé le 22/09/2026 (étape 23.1) : le calcul ci-dessous partait d'un chiffre faux.** Il supposait `videos.insert` à **1 600 unités sur les 10 000**. Depuis juin 2026, ce n'est plus le cas : `videos.insert` coûte « 1 unit in the Video Uploads quota bucket », un compartiment **séparé de 100 appels par jour** (https://developers.google.com/youtube/v3/determine_quota_cost et https://developers.google.com/youtube/v3/getting-started, vérifiés le 22/09/2026). Le raisonnement « 2 050 unités par publication, donc 4 par jour » reposait donc sur une monnaie qui n'existe plus.

**Chiffrage réel d'une publication complète** : 1 upload (sur 100/jour) + `thumbnails.set` 50 + `captions.insert` 400 + `playlistItems.insert` 50 + `videos.list` 1 = **1 upload et 501 unités**. Sur les plafonds de l'usine (80 uploads, 8 000 unités — 80 % de la dotation, la marge absorbant le décalage entre notre jour UTC et le jour Pacifique de Google), **15 publications complètes par jour** tiennent, et c'est le compartiment des unités qui sature le premier. Le plafond de 6 de `CONFORMITE.md` § 2 reste donc **le plus strict des deux**, et reste celui qui s'applique — mais pour une raison de prudence éditoriale (cadence, CONFORMITE § 6), plus du tout pour une raison de quota.

**La décision se prend toujours sur le solde réel** lu dans `quota_ledger`, jamais sur un compteur de vidéos : `factory publish status` l'affiche compartiment par compartiment. **Divergence ouverte** : `CONFORMITE.md` § 2 (« un `videos.insert` coûte 1 600 unités ») et le contrôle 27 de sa § 11 portent encore l'ancien chiffre. À corriger à la prochaine révision de `CONFORMITE.md` — non tranché ici, parce que le plafond de 6 qui en découle est conservé pour un autre motif.

```json
{ "schema_version": "1.0", "publish_path": "manual_studio", "publish_state": "uploaded_private",
  "youtube_video_id": "dQw4w9WgXcQ", "uploaded_at": "2026-09-19T05:02:11Z",
  "publish_at": "2026-09-20T16:40:00Z", "published_at": null,
  "thumbnail_set": true, "caption_id": "AUieDaa…", "quota_units_spent": 2050, "quota_day": "2026-09-19",
  "reporting_job_id": "job_8812", 
  "manual_steps": [ { "id": "schedule", "required": true, "done": false, "done_at": null } ],
  "post_check": { "has_paid_product_placement": null },
  "checklist": [ { "n": 1, "id": "synthetic_flag", "verdict": "pass", "detail": "false, 0 scène réaliste" } ],
  "retry_count": 0, "last_error": null }
```

### manifest.json
Écrit par **toutes** les étapes, en ajout : chaque étape y dépose son bloc et n'écrase jamais celui d'une autre. C'est le fichier qui rend la boucle de rétroaction possible (thèse n° 2) et la pièce produite en cas de contrôle. Cinq blocs.

**Colonne « sert à »** : `conformité` = exigé par `CONFORMITE.md` · `boucle` = joint un résultat à une décision · `exploitation` = sert à faire tourner ou réparer la fabrique.

#### identite
| Champ | Type | Sert à | Note |
|---|---|---|---|
| `video_id` | str | exploitation | clé primaire, nom du dossier |
| `parent_id` | str \| null | conformité, boucle | **c'est le `source_run_id` de `CONFORMITE.md` § 10**, renommé pour être cohérent avec `video_id`. Obligatoire pour toute déclinaison ; parenté d'un seul niveau |
| `channel_id` | str | boucle | |
| `lang` | str | conformité, boucle | `language` dans `CONFORMITE.md` § 10 — même champ |
| `niche` / `style` | str | boucle | facteurs de production à corréler aux résultats |
| `template_id` | str | conformité, boucle | rotation ≥ 3 par chaîne (§ 5) ; aussi un facteur de performance |
| `charte_version` | str | boucle | sans lui, un changement de police serait attribué au hook |
| `schema_version` | str | exploitation | |

#### decisions
| Champ | Type | Sert à | Note |
|---|---|---|---|
| `topic` | objet | boucle | `{sujet, angle, source, score, evidence}` — recopié de `spec.json` |
| `hook_type` | str | boucle | le facteur que l'étape 26 corrèle à la courbe de rétention |
| `title_variants[]` / `title_chosen` | liste / str | boucle | **garder les variantes non retenues** : sans elles, on ne sait pas si le titre a aidé ou si le sujet portait |
| `thumbnail_variants[]` / `thumbnail_chosen` | liste / str | boucle | idem pour le CTR |
| `cut_rhythm_target_s` | float | boucle | ce qu'on visait |
| `cut_rhythm_measured_s` | float | boucle | ce qu'on a obtenu — **les deux, parce que l'écart est lui-même un facteur** |
| `duration_s` | float | boucle | |
| `density_facts_per_min` | float | boucle | `research.fact_count ÷ (duration_s / 60)` — mesure de densité d'information (étape 16) |
| `voice_id` | str | boucle | |
| `music_track` | objet | conformité | `{track_title, source, author, licence, licence_url, attribution_required, credit_line, downloaded_from_channel}` — **c'est le `music.licence` de § 10** ; la piste se télécharge depuis le Studio de la chaîne qui publie |
| `assets[]` | liste | conformité, boucle | union de `licence.json` de chaque plan + `path` |
| `open_loops` | objet | boucle | `{planted, paid, positions_s[]}` — le référentiel impose ≥ 2 |
| `interrupts[]` | liste | boucle | ruptures programmées. **Le champ `at_s_relative` y porte la position absolue sur la timeline**, comme `open_loops.positions_s` juste au-dessus — dans `script.segments[].interrupt`, le même champ est relatif au segment. C'est le même modèle `Interrupt` employé aux deux endroits (divergence 10) |
| `library_reuse` | objet | exploitation | `{assets_reused, assets_generated, reuse_ratio}` — c'est la **mesure** qui doit confirmer ou infirmer que la bibliothèque fait tomber les 137 s par plan |

#### conformite
| Champ | Type | Sert à | Règle source |
|---|---|---|---|
| `contains_synthetic_media` | bool | conformité | § 3 |
| `contains_synthetic_media_reason` | str \| null | conformité | obligatoire si `true` : scènes concernées, modèle, décision |
| `synthetic_scenes[]` | liste | conformité | `{scene_id, generator, prompt_hash, realistic}` — posé **à la génération**, agrégé ensuite |
| `virtual_images_mention` | bool | conformité | § 3 couche 3 — condition **distincte** : image IA figurant un visage ou une silhouette, réaliste ou non |
| `paid_promotion` | bool | conformité | § 3 couche 2 — vrai dès qu'un lien d'affiliation figure en description, sans seuil |
| `paid_promotion_checked_in_studio` | objet \| null | conformité | `{done: bool, at}` — geste **manuel**, l'API ne l'écrit pas |
| `sponsor_segments[]` | liste | conformité | `{start_s, end_s, type: affiliate\|sponsor, product_id, overlay_rendered, spoken_disclosure_at_s}` |
| `disclosure_lines` | objet | conformité | `{<lang>: {description_line, overlay_text, spoken_line}}` |
| `affiliate_links[]` | liste | conformité, boucle | `{network: amazon\|awin\|cj\|impact, tracking_id, subid_param, subid_value, target_url}` — `subid_param` et longueur **par réseau** : `clickref` 50, `sid` 64, `SubId1` 255. **Format imposé du `subid_value` : `<channel_id>_<lang>_<video_id>`** (`CONFORMITE.md` § 10.4), tronqué par la droite à la limite du réseau ; c'est lui qui permet à l'import de conversions de retrouver `video_id`. **Sur Amazon, `subid_value` est `null` et `attribution_par_video` vaut `false`** : 100 identifiants de suivi au maximum, aucune granularité par vidéo — ne construis aucun rapport de rentabilité par vidéo qui suppose Amazon |
| `c2pa_preserved` | bool | conformité | § 4. **Mesuré, pas déclaré** : un ré-encodage ffmpeg perd les métadonnées C2PA de l'image d'origine, et rien dans la chaîne actuelle ne les reporte sur le MP4. Le champ enregistre donc l'état **réel**, `false` le plus souvent, et le contrôle 14 est un avertissement, pas un blocage. Ce qui est tenu, c'est l'interdiction de **retirer** volontairement un marquage : les `licence.json` conservent `c2pa_present` par asset, et les PNG d'origine promus en bibliothèque gardent le leur. Reporter la provenance sur le rendu final est un travail d'étape 31, pas une case à cocher ici |
| `reviewer` | str | conformité | identité nommée ou `auto-approve` |
| `review_hash` | str | conformité | SHA-256 du script **effectivement monté** |
| `review_date` | str | conformité | |
| `review_decision` | enum | conformité | `approved` \| `approved_with_edits` \| `rejected` \| `auto` |
| `ria_exception_claimed` | bool | conformité | faux sous `auto_approve` : dit vidéo par vidéo si l'exception éditoriale RIA est revendiquée |
| `editorial_angle` | objet | conformité | `{type, resume}` — liste fermée, § 4 |
| `dedupe_hash` | objet | conformité | `{script_simhash, thumbnail_phash}` — index **global**, toutes chaînes confondues |
| `publish_channel_account` | objet | conformité | `{channel_id, brand_account, google_account_alias, owner: "BMS", gcp_project, two_fa_enabled, phone_verified}` — **aucune valeur de secret** |
| `cadence_limits` | objet | conformité | `{max_per_week, window_start, published_this_week, next_allowed_at, jitter_window, read_at}`. **C'est un instantané, pas une autorisation** : il date du moment où il a été écrit. Le contrôle 22 relit `cadence.json` **au moment de l'upload** et refuse si l'instantané a plus de `read_at + 1 h`. `CONFORMITE.md` § 10.3 fait de `cadence.json` la seule source de vérité ; le manifeste n'en garde une copie que pour la trace d'audit |
| `publish_path` | enum | conformité | `manual_studio` \| `api_scheduled` |
| `publish_state` | enum | conformité | `draft` → `ready_to_publish` → `uploaded_private` → `scheduled` → `public` |
| `person_releases_missing[]` | liste | conformité | plans refusés faute de droit enregistré — trace de ce qui a été **écarté**, pas seulement de ce qui passe |

#### execution
| Champ | Type | Sert à | Note |
|---|---|---|---|
| `timings` | objet | exploitation | `{<noeud>: secondes}` pour les **19 nœuds**, sous-phases d'`assets` comprises. Alimente `cost.compute_min` et le suivi du goulot des 84 % |
| `modeles[]` | liste | exploitation | `{brique, repo, revision, quantization, runtime, runtime_version}` — **sans version, « même graine » ne veut rien dire** |
| `cost.compute_min` | float | exploitation | somme de `timings` ÷ 60 |
| `cost.energy_kwh` | float \| null | exploitation | `compute_min` × puissance moyenne mesurée ; **`null` + `a_mesurer: true` tant que la puissance n'est pas mesurée** |
| `cost.eur` | float \| null | exploitation | `energy_kwh × economics.tarif_kwh_eur` + `relecture_min × economics.cout_horaire_eur / 60` |
| `disk_mb` | objet | exploitation | `{peak, after_export}` — le pic est ce qui fait tomber le run sous le plancher de 8 Go |
| `errors[]` | liste | exploitation | `{step, ts, code, message, retry}` — **message exact de l'outil**, jamais reformulé |
| `run_state` | enum | exploitation | **les valeurs de `jobs.status`** : `queued` \| `running` \| `awaiting_review` \| `blocked` \| `failed` \| `exported` \| `published`, plus `visual_review_pending`. Distinct de `publish_state`, qui est le champ de conformité ; la correspondance est dans le § `factory.db` |
| `blocked_reason` | str \| null | exploitation | phrase lisible **destinée à Alek**, pas à un développeur |

#### resultats *(remplis par la phase 5, étape 25)*
| Champ | Type | Sert à | Note |
|---|---|---|---|
| `youtube_video_id` | str \| null | boucle | **la seule clé de jointure** entre ce manifeste et YouTube |
| `published_at` | str \| null | boucle | origine des fenêtres J+7 et J+30 |
| `reporting_job_id` | str \| null | boucle | sans job créé **avant** publication, impressions et CTR n'existeront jamais pour cette vidéo |
| `metrics_7d` / `metrics_30d` | objet \| null | boucle | Copie de la ligne `perf_window` correspondante : `{views, watch_time_min, avg_view_duration_s, avg_view_percentage, subscribers_gained, impressions, ctr, traffic_sources{}, retention_curve_ref, window_start, window_end, day_count, pulled_at, complete}`. **Ce sont des sommes sur les jours 0 à 6 et 0 à 29**, pas les valeurs du 7ᵉ et du 30ᵉ jour |
| `metrics_*.complete` | bool | boucle | la latence des rapports va **jusqu'à 72 h** : une fenêtre tirée trop tôt est incomplète et ne doit pas entrer dans l'apprentissage |
| `metrics_*.retention_curve_ref` | str \| null | boucle | clé vers `retention_curves` en base — la courbe est un blob par fenêtre, jamais une ligne par point |
| `conversions` | objet \| null | boucle | `{network, clicks, orders, revenue_eur, subid_value, resynced_at}` ; **`null` sur Amazon** : 100 identifiants de suivi au maximum, aucune attribution par vidéo |

```json
{ "schema_version": "1.0",
  "identite": { "video_id": "bms-science-en-20260918-k7q2", "parent_id": null,
    "channel_id": "bms-science-en", "lang": "en", "niche": "science_pop", "style": "illustre",
    "template_id": "sci-b", "charte_version": "2026.09.1" },
  "decisions": { "topic": { "sujet": "Why your brain deletes memories while you sleep",
      "angle": "comparaison_chiffree", "source": "topics_queue", "score": 0.81, "evidence": { "n": 12 } },
    "hook_type": "question_contrarienne",
    "title_variants": [ { "text": "Your Brain Deletes 18 %…", "score": 0.78 } ],
    "title_chosen": "Your Brain Deletes 18 %…",
    "thumbnail_variants": [ { "file": "thumbnails/variant_1.png", "contrast_ratio": 7.1 } ],
    "thumbnail_chosen": "variant_1",
    "cut_rhythm_target_s": 5.85, "cut_rhythm_measured_s": 5.8, "duration_s": 651.3,
    "density_facts_per_min": 1.29, "voice_id": "serena_en",
    "music_track": { "track_title": "Slow Drift", "licence": "CC-BY", "attribution_required": true,
                     "downloaded_from_channel": "bms-science-en" },
    "assets": [ { "asset_id": "9c1f4b77ad02e35a", "path": "assets/shot_00/image.png",
                  "provider": "flux", "licence": "Apache-2.0", "person_release": null } ],
    "open_loops": { "planted": 2, "paid": 2, "positions_s": [31.0, 214.5] },
    "library_reuse": { "assets_reused": 18, "assets_generated": 94, "reuse_ratio": 0.16 } },
  "conformite": { "contains_synthetic_media": false, "contains_synthetic_media_reason": null,
    "synthetic_scenes": [], "virtual_images_mention": true, "paid_promotion": false,
    "paid_promotion_checked_in_studio": null, "sponsor_segments": [], "disclosure_lines": {},
    "affiliate_links": [], "c2pa_preserved": true,
    "reviewer": "Sofiane", "review_hash": "6f3c…a91b", "review_date": "2026-09-19T08:40:00Z",
    "review_decision": "approved_with_edits", "ria_exception_claimed": true,
    "editorial_angle": { "type": "comparaison_chiffree", "resume": "Trois études ramenées à une échelle." },
    "dedupe_hash": { "script_simhash": "a41c…", "thumbnail_phash": "f0e2…" },
    "publish_channel_account": { "channel_id": "UCxxxx", "brand_account": "BMS Science EN",
      "google_account_alias": "bms-science-en", "owner": "BMS", "gcp_project": "bms-factory",
      "two_fa_enabled": true, "phone_verified": true },
    "cadence_limits": { "max_per_week": 2, "published_this_week": 1,
                        "next_allowed_at": "2026-09-22T16:00:00Z", "jitter_window": "PT3H" },
    "publish_path": "manual_studio", "publish_state": "uploaded_private", "person_releases_missing": [] },
  "execution": { "timings": { "script": 152.0, "voice": 1983.0, "assets": 16440.0, "render": 444.0 },
    "modeles": [ { "brique": "llm", "repo": "bartowski/Qwen_Qwen3.5-9B-GGUF", "quantization": "Q4_K_M",
                   "runtime": "llama.cpp", "runtime_version": "0.4.1" } ],
    "cost": { "compute_min": 325.4, "energy_kwh": null, "energy_kwh_a_mesurer": true, "eur": null },
    "disk_mb": { "peak": 2290, "after_export": 1.4 }, "errors": [],
    "run_state": "done", "blocked_reason": null },
  "resultats": { "youtube_video_id": "dQw4w9WgXcQ", "published_at": null, "reporting_job_id": "job_8812",
                 "metrics_7d": null, "metrics_30d": null, "conversions": null } }
```

### events.jsonl
Écrit par toutes les étapes, **append-only, jamais réécrit**. Une ligne = un événement, un objet JSON sur une seule ligne.

| Champ | Type | Détail |
|---|---|---|
| `ts` | str | ISO-8601 UTC, milliseconde |
| `run` | str | `video_id` |
| `step` | str | nœud du DAG, ou `orchestrator` |
| `level` | enum | `DEBUG` \| `INFO` \| `WARN` \| `ERROR` \| `BLOCK` |
| `msg` | str | une phrase, en français, sans variable interpolée à l'aveugle |
| `data` | objet | charge structurée ; **jamais de secret, jamais de jeton, jamais d'en-tête d'authentification** |

```json
{"ts":"2026-09-19T02:11:40.318Z","run":"bms-science-en-20260918-k7q2","step":"assets","level":"INFO","msg":"Image générée","data":{"shot":"shot_00","seed":3901284771,"duration_s":136.2,"peak_gb":11.1}}
{"ts":"2026-09-19T02:14:02.771Z","run":"bms-science-en-20260918-k7q2","step":"assets","level":"WARN","msg":"Plan à personnage : mis en file de relecture visuelle","data":{"shot":"shot_07"}}
{"ts":"2026-09-19T05:02:11.004Z","run":"bms-science-en-20260918-k7q2","step":"publish","level":"BLOCK","msg":"Publication arrêtée : l'audit de l'API n'est pas obtenu, la vidéo reste privée","data":{"controle":26}}
```

### publication.md et .done/<etape>.done
`publication.md` est le pense-bête de gestes manuels exigé par `CONFORMITE.md` § 2 — sans lui, l'opérateur oublie la case « promotion payante ». `<etape>.done` est le marqueur d'idempotence décrit dans `ARCHITECTURE.md` § 1.2.

```json
{ "step": "voice", "schema_version": "1.0", "started_at": "2026-09-19T03:41:00Z",
  "ended_at": "2026-09-19T04:14:03Z", "duration_s": 1983.0,
  "inputs_hash": "c19b…", "outputs": ["voice/voice.wav", "voice/timings.json"], "exit_code": 0 }
```

---

## 2. Configuration

Tout ce qui est « chaîne », « niche », « style », « langue », « produit » est une **donnée validée**, jamais une constante dans le code. C'est ce qui rend le système multi-chaînes, multi-langues et multi-styles par construction. Chargement en pydantic v2, `extra="forbid"` : une clé mal orthographiée est une erreur, pas un silence.

### config/channels/<id>.yaml
Le fichier le plus important du dépôt : il est le seul endroit où une chaîne existe.

```yaml
schema_version: "1.0"
id: bms-science-en
name: "BMS Science EN"
lang: en                       # doit exister dans config/languages/
niche: science_pop             # doit exister dans config/niches/
style: illustre                # doit exister dans config/styles/
templates: [sci-a, sci-b, sci-c]        # >= 3, CONFORMITE.md § 5 (rotation)
charte:
  version: "2026.09.1"
  fonts: { title: "Inter SemiBold", body: "Inter Regular" }
  palette: { bg: "#0d1117", text: "#ffffff", text_outline: "#101010",
             accent: "#1e5fd9", highlight: "#f2c94c" }
  transitions: [cut, fade, dip_black]   # le moteur ne peut en employer aucune autre
  subtitles: { align: bottom_center, margin_v_px: 96, size_px: 64,
               max_chars_per_line: 38, max_lines: 2, karaoke: true }
  framing: { person_shots: bust_only, prefer: [objet, lieu, schema, abstraction] }
voice_id: serena_en            # doit appartenir à config/languages/en.yaml
cadence:
  per_week_max: 2              # plafond dur des 90 premiers jours, CONFORMITE.md § 6
  days: [tuesday, saturday]    # REFERENTIEL.json -> creneaux de la niche
  hours_local: ["21:00"]
  jitter_min: 180              # fenêtre de +/- 3 h ; jamais un horaire fixe
  timezone: "America/New_York"
google_account:
  alias: bms-science-en
  brand_account: "BMS Science EN"
  owner: BMS
  gcp_project: bms-factory     # valeur unique, identique pour toutes les chaînes
  token_ref: "secrets/tokens/bms-science-en.json"      # chemin fixé par l'étape 14 ; référence, jamais la valeur
  two_fa_enabled: true
  phone_verified: true
products: []                   # ids de config/products/ ; non vide => paid_promotion
derive_from: null              # id d'une chaîne source pour les déclinaisons
auto_approve: false            # true retire l'exception éditoriale RIA pour cette chaîne
youtube:
  audit_passed: false          # tant que false, publish_path = manual_studio
  channel_id: "UCxxxx"
  playlist_id: "PLxxxx"
  captions_upload: true        # exclusif de charte.subtitles.burn_in (etape 9, ecart 1)
library:
  cooldown_videos: 10          # anti-répétition d'asset sur la même chaîne
  max_uses_per_channel: 3
```

**Validations croisées refusées à `config validate`** : `voice_id` absent de la langue · `style` absent du registre des moteurs · moins de 3 `templates` · `per_week_max > 2` sans dérogation datée · `products` non vide sans `disclosure_lines` dans `config/languages/<lang>.yaml` · `token_ref` pointant hors de `secrets/tokens/` · `audit_passed: true` sans trace de décision dans `STATE.md`.

### config/niches/<id>.yaml
Copie lisible des cibles de `registre/REFERENTIEL.json`. **Le code lit le JSON** ; ce YAML porte les surcharges assumées et le motif de chacune.

```yaml
schema_version: "1.0"
id: science_pop
rythme_coupe_s: { cible: 6.0, cible_montage: 5.85, min: 3.5, max: 12.0,
                  facteur_hook: 0.7, n: 5, a_mesurer: false,
                  fallback_provisoire_s: null }   # non nul quand a_mesurer: true
duree_s: { cible: 648, p25: 214, p75: 2754, tolerance: 0.15, distribution_large: true }
mots_par_minute: { mediane: 135, n: 42 }
hooks: { parts: { mise_en_scene_narrative: 0.22, question_contrarienne: 0.14 },
         boucles_minimum: 2, boucle_position_s_repli: 47.9 }
titres: { longueur_car: { mediane: 58, p90: 74, plafond_recommande: 80, plafond_youtube: 100 } }
miniatures: { mots_texte_median: 1.5, part_visage: 0.43, contraste_ratio_cible: 4.5 }
cadence_par_semaine: { mediane: 0.96, cible: 1.85 }
surcharges: []    # {champ, valeur, motif, date, qui} — jamais une valeur sans motif
```

### config/styles/<id>.yaml
Sélectionne un moteur. **Aucun `if style == …` n'existe dans le code** : ce fichier est la seule chose qui change.

```yaml
schema_version: "1.0"
id: illustre
engine: illustre_anime          # clé du registre STYLE_ENGINES
backend: ffmpeg                 # ffmpeg | revideo — déclaré par le moteur, pas par le pipeline
statut: retenu_v1               # retenu_v1 | retenu_v2 | planifie | serveur_seulement | abandonne
templates: [sci-a, sci-b, sci-c]  # gabarits fournis par le moteur ; channel.templates doit y appartenir
params:
  image: { model: "mlx-community/FLUX.2-Klein-4B-4bit", resolution: "1280x720", steps: 4 }
  depth: { model: "depth-anything/Depth-Anything-V2-Small-hf" }
  motion: { default: parallax, ken_burns_supersample: 4, parallax_layers: 3,
            alpha_ramp_px: 3, magenta_hole_check: true }
  person_review: true           # met les plans à personnage en file de relecture humaine
```

Un style en `statut: planifie` est **accepté par le validateur** et refusé à l'exécution avec un message nommant l'étape qui le livrera. C'est ce qui permet d'écrire les configurations des six moteurs avant d'en avoir codé deux.

### config/languages/<code>.yaml
Porte tout ce qui empêche une langue de fuir dans une autre.

```yaml
schema_version: "1.0"
code: en
name: "English"
voices:
  - { id: serena_en, engine: qwen3_tts, gender: f, native: false, note_ecoute: null }
  - { id: kokoro_af, engine: kokoro, gender: f, native: true, note_ecoute: null }
typographie: { espace_avant_double_ponctuation: false, guillemets: ["“", "”"],
               majuscules_titre: title_case }
nombres: { decimal: ".", milliers: ",", pourcent: "18%", date: "September 18, 2026",
           unites: imperial_first }
disclosure:
  amazon: "As an Amazon Associate I earn from qualifying purchases."   # contractuel, mot pour mot
  impact: ["#ad", "#sponsored"]
  awin: ["#Ad", "#PaidAd"]
  overlay_generic: "Paid promotion"
  virtual_images: "AI-generated imagery"
asr: { primary: parakeet, fallback: whisper, wer_thresholds: { "5": 0.20, "20": 0.15, "999": 0.08 } }
```

**Le bloc `disclosure` ne se traduit pas.** La phrase Amazon est contractuelle ; les mentions Impact et Awin sont des listes fermées (« No other alternatives are permitted »). Une chaîne francophone porte la phrase française d'Amazon, mot pour mot, et `virtual_images: "Images virtuelles"`.

### config/products/<id>.yaml
```yaml
schema_version: "1.0"
id: exemple-affilie
name: "Exemple — complément"
network: impact                 # amazon | awin | cj | impact
tracking_id: "bms-1234"
subid_param: SubId1             # clickref (50) | sid (64) | SubId1 (255) — par réseau
subid_max_len: 255
target_url: "https://exemple.tld/produit"
attribution_par_video: true     # false sur amazon : 100 identifiants max, aucune granularité vidéo
cookie_window_days: 31
disclosure_override: {}         # sinon hérité de config/languages/<lang>.yaml
cta_segment: { role: sponsor, position: apres_premier_point, duree_s_max: 45 }
```

Un produit renseigné sur une chaîne impose `paid_promotion: true`, au moins un `sponsor_segments[]` avec bandeau incrusté sur **tout** le segment, une mention orale dans les 30 premières secondes du segment, et la ligne de divulgation en **première ligne** de description.

### config/qc.yaml
```yaml
schema_version: "1.0"
# Les poids couvrent TOUS les contrôles notés ; les contrôles binaires bloquants sont hors barème.
poids: { cut_rhythm: 15, duration: 8, loudness: 10, true_peak: 5, subtitle_coverage: 12,
         hook_form: 12, text_legibility: 8, visual_variety: 8, silence: 4,
         speech_rate: 6, density_facts_per_min: 6, interrupt_cadence: 3, open_loops: 3 }
hors_bareme: [magenta_holes, c2pa]      # binaires : bloquant et avertissement
seuils:
  cut_rhythm: { tolerance: 0.15, verdict_fail: regenerate }
  duration:   { tolerance: 0.15, verdict_fail: warn }
  loudness:   { cible: -14.0, tolerance: 0.5, verdict_fail: regenerate }
  true_peak:  { cible: -1.0,  tolerance: 0.2, verdict_fail: regenerate }
  subtitle_coverage: { cible: 1.0, min: 0.98, verdict_fail: regenerate }
  speech_rate: { source: "niche.mots_par_minute.mediane", tolerance: 0.15, verdict_fail: warn }
  density_facts_per_min: { min: 0.8, verdict_fail: warn }
  magenta_holes: { cible: 0, verdict_fail: blocked }     # contrôle de non-régression de la parallaxe
  c2pa: { verdict_fail: warn }                           # avertissement, CONFORMITE § 11 contrôle 14
score_minimal_pour_publier: 70
```

### config/editorial.yaml et config/team.yaml
```yaml
# config/editorial.yaml
schema_version: "1.0"
topics_queue: { taille_max: 200, score_minimal: 0.45, age_max_jours: 45 }
dedupe: { script_simhash_distance_min: 12, thumbnail_phash_distance_min: 10, portee: globale }
angles_autorises: [opinion, comparaison_chiffree, test, donnee_proprietaire]
sources_blanches: [pexels, pixabay, openverse, wikimedia, nasa, internet_archive]
purge_cache_api_jours: 30        # Developer Policies III.E.4
```
```yaml
# config/team.yaml
schema_version: "1.0"
relecteurs:
  - { id: thomas,  nom: "Thomas",  role: developpeur, langues: [fr, en], lots_par_semaine: 2 }
  - { id: alek,    nom: "Alek",    role: proprietaire, langues: [en, fr], lots_par_semaine: 1 }
  - { id: sofiane, nom: "Sofiane", role: proprietaire, langues: [en],     lots_par_semaine: 1 }
taille_lot: 5
delai_max_heures: 48             # au-delà, le run passe blocked et une alerte part
```

### config/economics.yaml
Nécessaire à `manifest.execution.cost` et à l'étape 27. Aucune de ces valeurs n'est mesurée aujourd'hui : elles portent leur origine.

```yaml
schema_version: "1.0"
tarif_kwh_eur: { valeur: 0.2516, source: "tarif réglementé FR", date: "2026-09-15" }
puissance_moyenne_w: { valeur: null, a_mesurer: true, note: "à mesurer avec un wattmètre, étape 27" }
cout_horaire_relecture_eur: { valeur: null, a_mesurer: true, note: "décision d'Alek" }
```

---

## 3. Base, bibliothèque, moteurs

### workspace/factory.db
SQLite unique, WAL, un seul écrivain. **Les tables de runs sont reconstructibles** en relisant les `manifest.json` (`factory queue reindex`). **Les noms viennent de `ROADMAP.md`**, migration par migration : ce document ne les invente pas, il les rassemble.

```sql
-- 001 : index des runs (reconstructible depuis les manifestes)
runs(video_id PK, parent_id, channel_id, lang, niche, style, template_id, charte_version,
     run_state, publish_state, publish_path, youtube_video_id, published_at,
     topic_sujet, topic_source, topic_score, topic_cluster, hook_type,
     title_pattern, title_chosen, thumbnail_variant_chosen, voice_id,
     duration_s, cut_rhythm_target_s, cut_rhythm_measured_s, density_facts_per_min,
     open_loops_planted, reuse_ratio, slot_local_day, slot_local_hour,
     score_qc, cost_compute_min, disk_mb_peak, reviewer, review_decision,
     created_at, updated_at, manifest_path, manifest_json)
CREATE INDEX ix_runs_channel_pub ON runs(channel_id, published_at);
CREATE UNIQUE INDEX ux_runs_youtube ON runs(youtube_video_id) WHERE youtube_video_id IS NOT NULL;

-- 003 (étapes 22.1, 22.2) : file et relecture
jobs(id PK, video_id, channel_id, stage, status, attempts, next_run_at, last_error,
     priority, created_at, updated_at)
     -- status : queued | running | awaiting_review | blocked | failed | exported | published
-- 008 (étape 22.2) : `review_log` reconstruite. Clé de ligne et non empreinte de script :
-- un texte rejeté puis approuvé produit DEUX décisions, et la première est la preuve du
-- contrôle éditorial. `review_hash` et `review_date` survivent en colonnes **générées**.
review_log(id PK, video_id, channel_id, reviewer, decision, motif, script_sha256,
           timestamp, batch_id, review_hash AS script_sha256, review_date AS timestamp)
     -- decision : approved | approved_with_edits | rejected | auto_approved

-- 002 (étape 18) : éditorial. Données API de TIERS : purgées ou rafraîchies à 30 jours
channels_watch(channel_id PK, handle, title, niche, lang, source, active, added_at,
               uploads_playlist_id)
videos_ext(video_id PK, channel_id, published_at, title, description_head, duration_s,
           tags_json, category_id, thumbnail_url, first_seen_at, last_seen_at)
video_snapshots(video_id, snapshot_date, views, likes, comments, PRIMARY KEY(video_id, snapshot_date))
channel_snapshots(channel_id, snapshot_date, subscribers, views, video_count)
collect_runs(date, units_used, channels_done, videos_new, errors)

-- étapes 19, 20 : notation et file de sujets
niche_scores(niche, lang, day, demande, concurrence, monetisation, saisonnalite, score)
topics_queue(id PK, channel_id, lang, niche, cluster_id, topic, angle, score,
             evidence_json, status, created_at, used_by_run)  -- UNIQUE(channel_id, topic)
             -- status : proposed | approved | used | banned
topic_clusters(cluster_id, run_date, label, n_videos, n_channels, n_breakouts, views_total,
             velocity_median, part_breakouts, langs, age_median_days, gap_type,
             demand_score, evidence_json, PRIMARY KEY(cluster_id, run_date))
embeddings(video_id, model, dim, vector, text_hash, computed_at, PRIMARY KEY(video_id, model))
             -- vector : float32 little-endian, L2-normalisé ; le produit scalaire EST le cosinus

-- 009 (étape 23.1) : publication et quota. **Numérotée 009, pas 004** : le 004 est pris
-- depuis l'étape 18 par `004_editorial.sql`, et `schema_migrations.version` est une clé
-- primaire. Les tables sont celles annoncées ici ; seul le numéro de fichier diverge.
publications(video_id PK, channel_id, youtube_video_id, status, publish_at, uploaded_at,
             thumbnail_set, captions_set, playlist_added, units_used, last_error, updated_at)
             -- status : published_private | scheduled | public | failed
-- `compartment` et `ok` sont deux colonnes de plus que le contrat d'origine. `compartment`
-- parce que le quota n'est plus une seule monnaie depuis juin 2026 (uploads 100/jour d'un
-- côté, 10 000 unités de l'autre) et qu'additionner les deux donne un solde faux ; `ok`
-- parce que Google débite la tentative, pas le succès — sans lui, une journée passée en 403
-- serait indiscernable d'une journée de travail.
quota_ledger(id PK, day, gcp_project, call, compartment, units, video_id, channel_id,
             ok, detail, at)
             -- compartment : uploads | search | units | reporting
v_quota_jour(day, gcp_project, units, uploads, inserts, updates, erreurs, appels)  -- vue
reporting_jobs(job_id PK, channel_id, report_type, created_at, state,
               first_report_expected_at, seen_at)

-- 005 (étape 25) : analytique de NOS chaînes. Conservation illimitée
perf_daily(video_id, youtube_video_id, channel_id, date, views, minutes_watched,
           avg_view_duration_s, avg_view_pct, subs_gained, likes, shares, comments,
           engaged_views, pulled_at, PRIMARY KEY(youtube_video_id, date))
perf_traffic(video_id, date, source, views)
perf_reach(video_id, date, impressions, ctr, pulled_at)
perf_window(youtube_video_id, window, views, minutes_watched, avg_view_pct, subs_gained,
            impressions, ctr, day_count, complete, pulled_at,
            PRIMARY KEY(youtube_video_id, window))     -- window : 'J7' | 'J30'
retention_curves(youtube_video_id, window, curve_json, pulled_at,
                 PRIMARY KEY(youtube_video_id, window))
analytics_runs(date, channel_id, videos_done, errors, pulled_at)

-- étape 27 : conversions d'affiliation
conversions(network, subid_value, day, video_id, clicks, orders, revenue_eur, resynced_at,
            PRIMARY KEY(network, subid_value, day))

-- bibliothèque
library_assets(asset_id PK, kind, layer, path, provider, licence, licence_url,
               attribution_line, person_release, has_text, lang, keywords, phash,
               uses, last_used_at)
library_uses(asset_id, video_id, channel_id, used_at)

-- dédoublonnage GLOBAL, toutes chaînes confondues (CONFORMITE § 5)
dedupe(kind, hash, video_id, channel_id, lang, published_at, PRIMARY KEY(kind, hash))
```

**Quatre choix qui viennent de contraintes, pas de goût.**

1. **`perf_window` existe parce qu'une fenêtre n'est pas un jour.** « Métriques à 7 jours » veut dire la **somme des jours 0 à 6**, pas la ligne du 7ᵉ jour. Une vue qui joindrait `perf_daily` sur `date(published_at, '+7 day')` rendrait le trafic d'une seule journée et l'apprentissage porterait sur du bruit. `perf_window` agrège, porte `day_count` et `complete`, et c'est lui que la vue lit.
2. **`complete` n'est pas décoratif.** La latence des rapports va **jusqu'à 72 h** ; une fenêtre J+7 tirée à J+7 est incomplète. `learn` n'admet que `complete = 1`.
3. **`dedupe` se lit par distance, jamais par égalité.** Sa clé primaire sert l'unicité, pas la recherche : le contrôle 18 exige une **distance de Hamming ≥ `script_simhash_distance_min` (12)** sur le simhash, stocké en **entier 64 bits** pour que la distance se calcule en base. Un `WHERE hash = ?` passerait tous les quasi-doublons, qui sont précisément ce que la politique vise.
4. **`retention_curves` stocke un blob par fenêtre.** À 2 600 vidéos par an, une ligne par point de courbe ferait des dizaines de millions de lignes sans qu'aucune requête n'en ait besoin.

**La vue de jointure**, celle qui rend la boucle de rétroaction possible — `v_video_perf`, nom fixé par l'étape 25 :

```sql
CREATE VIEW v_video_perf AS
SELECT r.video_id, r.channel_id, r.lang, r.niche, r.style, r.template_id, r.charte_version,
       r.hook_type, r.title_pattern, r.thumbnail_variant_chosen, r.voice_id,
       r.cut_rhythm_target_s, r.cut_rhythm_measured_s, r.duration_s,
       r.density_facts_per_min, r.open_loops_planted, r.topic_cluster,
       r.slot_local_day, r.slot_local_hour, r.score_qc, r.cost_compute_min,
       p.status AS publish_status, p.youtube_video_id, r.published_at,
       w7.views  AS views_7d,  w7.ctr AS ctr_7d,  w7.avg_view_pct AS avg_pct_7d,  w7.complete AS ok_7d,
       w30.views AS views_30d, w30.ctr AS ctr_30d, w30.avg_view_pct AS avg_pct_30d, w30.complete AS ok_30d
FROM runs r
LEFT JOIN publications p ON p.video_id = r.video_id
LEFT JOIN perf_window w7  ON w7.youtube_video_id  = r.youtube_video_id AND w7.window  = 'J7'
LEFT JOIN perf_window w30 ON w30.youtube_video_id = r.youtube_video_id AND w30.window = 'J30';
```

**Deux états, deux vocabulaires, une correspondance.** `CONFORMITE.md` § 10 impose `publish_state` (`draft` → `ready_to_publish` → `uploaded_private` → `scheduled` → `public`) ; `ROADMAP.md` fixe `publications.status` (`published_private` \| `scheduled` \| `public` \| `failed`) et `jobs.status` (`queued` \| `running` \| `awaiting_review` \| `blocked` \| `failed` \| `exported` \| `published`). Les trois coexistent, avec une correspondance écrite une fois et jamais réinventée :

| `manifest.publish_state` (conformité) | `publications.status` (base) | `jobs.status` (file) |
|---|---|---|
| `draft` | — | `queued` \| `running` \| `awaiting_review` |
| `ready_to_publish` | — | `exported` |
| `uploaded_private` | `published_private` | `published` |
| `scheduled` | `scheduled` | `published` |
| `public` | `public` | `published` |
| — | `failed` | `failed` \| `blocked` |

`manifest.execution.run_state` reprend **les valeurs de `jobs.status`** et rien d'autre, plus `visual_review_pending` pour la barrière des plans à personnage.

**Les jetons OAuth sont dans `secrets/tokens/<channel_id>.json`** — chemin fixé par l'étape 14, repris tel quel par `channel.google_account.token_ref`.

### workspace/library/
Arborescence `{images,stock,music,sfx,characters,intros}/`, un `licence.json` frère par fichier (même contrat que `assets/<shot>/licence.json`), index en base. `cadence.json` est la **seule source de vérité** sur « peut-on publier maintenant » (`CONFORMITE.md` § 10.3) :

```json
{ "schema_version": "1.0",
  "bms-science-en": { "channel_id": "bms-science-en", "created_at": "2026-09-01T00:00:00Z",
    "days_since_creation": 18, "max_per_week": 2,
    "published_timestamps": ["2026-09-16T20:52:00Z"],
    "next_allowed_at": "2026-09-22T16:00:00Z", "jitter_window": "PT3H", "auto_approve": false } }
```

Règles de réutilisation : un asset `has_text: true` ne sort jamais de sa langue ni de sa chaîne · `cooldown_videos` et `max_uses_per_channel` par chaîne · aucun asset **`layer: foreground`** partagé entre deux chaînes de **même langue** (le fond, lui, peut l'être) · `characters/` propre à une chaîne · intros et outros communes explicitement autorisées.

**Le cooldown ne s'applique jamais au rejeu du même run.** Il ne compte que les `library_uses` dont le `video_id` **diffère** du run courant. Sans cette exception, le critère de l'étape 12.2 — « deuxième exécution du même run réutilise les images de la bibliothèque, 0 génération » — serait impossible à tenir avec `cooldown_videos: 10`, et une reprise après incident regénérerait 4 h 34 d'images déjà payées.

### Interface StyleEngine et registre des moteurs
Deux méthodes, et rien d'autre. Le moteur ne connaît ni la langue, ni la conformité, ni la publication : tout le commun vit hors des moteurs.

```python
class StyleEngine(Protocol):
    name: str
    backend: Literal["ffmpeg", "revideo"]

    def prepare_assets(self, shotlist: Shotlist, channel: Channel, run: RunPaths) -> list[Asset]:
        """Acquiert ou génère les assets de tous les plans, écrit assets/<shot>/licence.json.
        Un sous-processus par modèle chargé, jamais deux modèles résidents (ARCHITECTURE § 1.3).
        Doit être idempotente au plan près : un plan déjà servi n'est pas régénéré."""

    def render_shot(self, shot: Shot, assets: list[Asset], channel: Channel,
                    run: RunPaths) -> Path:
        """Rend un plan en clips/shot_XX.mp4 au contrat de format, et rend son chemin.
        Ne lit que shot, assets, channel.charte et run. Aucun état entre deux appels."""

STYLE_ENGINES: dict[str, type[StyleEngine]] = {
    "cartes":        CartesEngine,        # 12.1  ffmpeg  — interne, jamais publié tel quel
    "illustre_anime": IllustreAnimeEngine, # 12.2  ffmpeg
    "documentaire":  DocumentaireEngine,  # 17    ffmpeg
    "motion_design": MotionDesignEngine,  # 30.1  revideo
    "whiteboard":    WhiteboardEngine,    # 30.2  revideo
    "avatar2d":      Avatar2dEngine,      # 29    revideo
}

def get_engine(style_id: str) -> StyleEngine:
    """Résout config/styles/<style_id>.yaml -> engine -> STYLE_ENGINES. Lève une erreur
    nommant l'étape qui le livrera si le style est en statut 'planifie'."""
```

Ajouter un style, c'est ajouter un YAML et une classe au registre. Le pipeline n'est jamais modifié.

---

## 4. Commandes et erreurs

### Commandes CLI
`factory <commande> [arguments]`. Sauf mention, toute commande de pipeline prend `--run <video_id>`, `--from <etape>`, `--force`, `--dry-run`, `--json`.
`--from` accepte les 19 nœuds du DAG, **sous-phases d'`assets` comprises** : `plan`, `research`, `script`, `review`, `voice`, `subtitles`, `shotlist`, `assets.fetch`, `assets.image`, `assets.depth`, `render`, `assemble`, `thumbnail`, `metadata`, `qc`, `export`, `publish`, `measure`, `learn`.

| Commande | Arguments | Écrit |
|---|---|---|
| `doctor` | `--quick` | rien ; 14 contrôles, dont 6 sondes qui exercent réellement chaque brique |
| `config validate` | `[chemin]` | rien ; 0 si tout valide, 1 avec messages lisibles sinon |
| `config show` | `<channel_id>` | rien ; affichage de la configuration résolue |
| `plan` | `--channel <id>` `[--topic "<sujet>"]` `[--product <id>]` | `spec.json`, `manifest.json`, ligne `runs`, dossier du run |
| `research` | `--run` | `research.json` |
| `script` | `--run` | `script.json` |
| `review` | `list` \| `show <run>` \| `approve <run> --by <id>` \| `reject <run> --by <id> --comment` | `review.json`, ligne dans `registre/data/reviews.jsonl`, `review_log` |
| `voice` | `--run` | `voice/*`, `voice/timings.json` |
| `subtitles` | `--run` `[--engine parakeet\|whisper]` | `words.json`, `subtitles.srt`, `subtitles.ass` |
| `shotlist` | `--run` | `shotlist.json` |
| `render` | `--run` `[--shots shot_03,shot_07]` `[--skip-assets]` | `assets/**`, `clips/*.mp4` (exécute `assets.fetch`, `assets.image`, `assets.depth` puis `render`) |
| `assemble` | `--run` | `video_nomusic.mp4`, `final.mp4` |
| `thumbnail` | `--run` `[--variants 3]` | `thumbnails/*`, `thumbnail.png` |
| `metadata` | `--run` | `metadata.json` |
| `qc` | `--run` | `qc.json` |
| `export` | `--run` | `workspace/export/<video_id>.mp4`, purge des intermédiaires |
| `run` | `--channel <id>` \| `--run <id>` | tout le DAG jusqu'à `export`, avec reprise ; s'arrête aux barrières humaines |
| `localize` | `--run <parent>` `--to-channel <id>` | run enfant complet (`parent_id` renseigné) |
| `publish` | `auth --channel` \| `upload --run` \| `release --run [--schedule <iso>]` \| `status` \| `manual-list` \| `reporting-jobs --channel` | `publish.json`, `publication.md`, `publications`, `quota_ledger`, `reporting_jobs` |
| `calendar` | `show [--weeks 4]` \| `plan` | créneaux proposés, jitter appliqué, conflits ±30 min signalés |
| `queue` | `add` \| `status` \| `retry <run>` \| `block <run>` \| `reindex` | table `jobs` ; `reindex` reconstruit `runs` depuis les manifestes |
| `daemon` | `start` \| `stop` \| `status` | exécuteur `launchd`, fenêtre nocturne, **un run à la fois** |
| `editorial collect` | `[--channels-file]` | `channels_watch`, `videos_ext`, `video_snapshots`, `channel_snapshots`, `collect_runs` (+ purge 30 jours) |
| `editorial niches` | `[--lang]` | `niche_scores`, `reports/niches_<lang>.md` |
| `editorial topics` | `[run] --channel <id> [--n 30]` \| `approve <id>` \| `ban <id>` | `topics_queue`, `topic_clusters`, `embeddings`, `reports/topics_<channel>.md` |
| `analytics pull` | `[--channel] [--since]` | `perf_daily`, `perf_traffic`, `perf_reach`, `perf_window`, `retention_curves`, `analytics_runs` ; rétro-remplit `published_at` ; recopie dans `manifest.resultats` |
| `analytics show` | `<run>` \| `--channel <id>` | rien ; lecture |
| `learn` | `[--min-n 12]` | `learned/weights.json` |
| `economics` | `[--by niche\|lang\|channel\|style]` | rapport de coût et de revenu par vidéo |
| `library` | `scan` \| `stats` \| `find "<description>" [--type]` \| `prune [--unused-days 180] [--execute]` \| `intros --channel` | `workspace/library/**`, `library_assets`, `library_semantic_reuse` |
| `character build` | `<id>` | `workspace/library/characters/<id>/` (base, calques, `character.yaml`) |
| `dashboard` | `[--port 8501]` | rien ; Streamlit local |

### Sémantique des erreurs

| Code | Sens | Exemple | Reprise |
|---|---|---|---|
| 0 | succès | | |
| 1 | usage ou configuration invalide | clé inconnue dans un YAML | corriger et relancer |
| 2 | contrat d'entrée non satisfait | `shotlist` sans `words.json` | `--from` l'étape amont |
| 3 | échec d'un outil externe après tentatives | ffmpeg, modèle, réseau | `--from <etape>` |
| 4 | seuil de qualité non tenu | `qc.verdict == regenerate` | `--from` les `regenerate_steps[]` |
| 5 | blocage de conformité | un contrôle **bloquant** de `CONFORMITE.md` § 11 | jamais automatique : un humain tranche |
| 6 | ressource insuffisante | < 8 Go libres, verrou modèle déjà tenu | libérer, relancer |
| 7 | attente humaine | `review_pending`, `visual_review_pending` | ce n'est pas un échec : le run sort de la file |
| 130 | interruption | Ctrl-C, `launchd` | le marqueur `.done` n'est pas écrit, l'étape rejoue |

**Tentatives.** Étapes réseau (`research`, `publish`, `analytics`, banques) : 3 essais, temporisation exponentielle 5 s / 25 s / 125 s, `Retry-After` respecté. Étapes à modèle : 1 nouvelle tentative, puis échec — un second échec est un défaut, pas un aléa. Étapes pures (`plan`, `shotlist`, `assemble`) : **0 tentative**, un échec y est un bogue et le masquer coûterait plus cher que l'arrêt.

**Ce qui bloque un run** (`run_state: blocked`, `blocked_reason` en français, destiné à Alek) : un contrôle bloquant de la checklist · le plancher de 8 Go franchi · `max_run_disk_mb` dépassé · un asset sans licence, sans `person_release` ou en licence non commerciale · `review_hash` ne correspondant pas au script monté · un délai de relecture dépassé · le quota du jour épuisé · une autre chaîne publiant dans la fenêtre ±30 min. Un run bloqué **n'est jamais dégradé pour passer** : il attend une décision.

**Timeouts par étape** (défauts, surchargeables), **calés sur les mesures et non sur des chiffres ronds** : `research` 300 s · `script` 900 s · `voice` **`max(180, 5 × duration_s)` par segment** (RTF mesuré 3,29 à 3,57, et le contrat impose des segments de ≥ 15 s : un segment de 30 s demande déjà 99 s) · `subtitles` 600 s · `assets.image` **900 s par plan** (médiane mesurée 137 s, **pire cas connu 621 s** : un plafond à 600 s tuerait un plan qui allait aboutir) · `assets.depth` 60 s par plan · `render` 120 s par plan · `assemble` 1800 s · `publish` 3600 s. Un dépassement est un code 3, pas un plantage silencieux.

---

## 5 bis. Écarts d'implémentation (étape 9, 15/09/2026)

`factory/core/models.py` implémente ce document en pydantic v2. Cinq points ont dû s'en écarter ;
les trois premiers sont reportés dans les exemples ci-dessus, les deux derniers sont des
précisions. Aucun champ obligatoire de `CONFORMITE.md` § 10.1 n'a été retiré ni assoupli.

| # | Écart | Motif |
|---|---|---|
| 1 | `config/channels/<id>.yaml` gagne `youtube.captions_upload` (défaut `true`) | Le § `subtitles.ass` rend `charte.subtitles.burn_in` **exclusif** de `metadata.caption_file` et charge `config validate` de le refuser — or `metadata.json` est un fichier de run, absent au moment de la validation. Sans un second drapeau **dans la configuration**, la règle n'est pas vérifiable. `Channel` refuse désormais `burn_in: true` avec `captions_upload: true` |
| 2 | `config/styles/<id>.yaml` gagne `templates[]` | `channel.templates` devait être validé contre quelque chose. Liste vide = le moteur n'impose rien ; liste non vide = `channel.templates` doit y appartenir |
| 3 | `config/niches/<id>.yaml` gagne `rythme_coupe_s.fallback_provisoire_s` | `spec.json` prévoyait déjà ce repli (« repli `fallback_provisoire_s` ») sans qu'aucun fichier ne le porte. Il vient de `REFERENTIEL.json` (7,8 s) et n'est obligatoire que si `a_mesurer: true` |
| 4 | `manifest.json` porte `schema_version` **à la racine**, pas dans `identite` | Le tableau du bloc `identite` le listait, l'exemple JSON le plaçait à la racine, comme tous les autres fichiers du § 0. L'exemple a raison |
| 5 | `config/languages/<code>.yaml` → `disclosure` n'a pas d'entrée `cj` | Le bloc est repris tel quel du document. Un produit CJ retombe sur `overlay_generic` ; à compléter si CJ devient le réseau primaire (question ouverte à Alek) |

**Ce que l'étape 9 n'a pas modélisé**, faute d'étape qui l'écrive : `voice/timings.json`
(étape 11), `metadata.json` et `thumbnails/thumbnails.json` (étapes 20 et 21). `research.json`
est modélisé depuis l'étape 10 (`Research`, `Fait`, `SourceConsultee`, `AnglePropose`).

### Divergences ajoutées par l'étape 10

| # | Écart | Motif |
|---|---|---|
| 6 | `plan` prend `--topic "<sujet>"` et `--product <id>`, non `--topic-id` / `--manual` | Signature imposée par le prompt de l'étape 10. `--topic-id` désignait une entrée de la file éditoriale, qui n'existe qu'à l'étape 20 : `factory/steps/plan.py` porte le point d'extension (`_point_extension_file_sujets`) et le nom sera repris là |
| 7 | `research.json` gagne `sources[]`, `source_count`, `angles_proposes[]`, `angle`, `angle_signature`, `elements_proprietaires[]` | Le contrat ne portait que `facts[]`, or « ≥ 3 sources avec URL et citations » est un critère de fin d'étape mesurable seulement sur une liste de sources, et `editorial_signature` du script doit venir d'une décision tracée, pas d'une reformulation |
| 8 | Un script est généré en **plusieurs appels** (plan, accroche, narration par lots), pas en un seul objet `Script` | Le contexte est plafonné à 8 k jetons et la cible de `science_pop` vaut ~1 460 mots : le script entier ne tient pas dans la fenêtre. Le squelette (rôles, boucles, ruptures, budget de mots par segment) est construit par le code ; le LLM ne remplit que le texte. C'est aussi ce qui permet de tenir la durée |
| 10 | `manifest.decisions.interrupts[].at_s_relative` porte une position **absolue**, pas relative | `ManifestDecisions.interrupts` réutilise le modèle `Interrupt` du script. Le manifeste décrit la cadence sur toute la vidéo — c'est ce que lit le contrôle `interrupt_cadence` de l'étape 15 — là où le segment décrit une position interne. Renommer le champ imposerait deux modèles pour une même notion ; la note au § manifeste lève l'ambiguïté |
| 9 | Une **rupture par segment au plus**, donc un segment par intervalle `N = 4 × rythme_coupe_s` | `ScriptSegment.interrupt` est un objet, pas une liste. Le nombre de segments est donc dérivé de la cadence de rupture (28 pour `science_pop`), et non choisi |
Leurs contrats restent ceux du § 1, sans modèle pydantic à ce jour.

### Divergences ajoutées par l'étape 11

| # | Écart | Motif |
|---|---|---|
| 11 | `voice/timings.json` est **modélisé** (`Timings`, `SegmentVoix`) et gagne `engine` et `speed` | Le § 1 le décrivait sans modèle. `engine` et `speed` sont nécessaires pour relire un run : la même voix synthétisée par un autre moteur, ou à une autre vitesse, ne rend pas le même fichier |
| 12 | `config/languages/<code>.yaml` gagne un bloc `tts` (`speed`, `pauses_ms`, `min_segment_s`, `silence_threshold_db`) | Le prompt de l'étape 11 exige une vitesse lue dans la configuration et des pauses configurables. Le modèle retenu **n'expose aucun paramètre de vitesse** : `speed` est appliquée après synthèse par `atempo`. Les pauses sont une propriété de prosodie, donc de langue, pas de charte visuelle |
| 13 | `manifest.decisions` gagne `loudness_lufs`, `true_peak_dbtp`, `asr_engine`, `subtitle_coverage`, `wer_vs_script` | Le manifeste reste en **cinq blocs**. Ces cinq valeurs sont des **mesures de facteurs de rétention** (thèse n° 3), au même titre que `cut_rhythm_measured_s` qui siège déjà dans `decisions` : c'est l'étape 26 qui les corrélera aux résultats |
| 14 | Le `Format:` de `[V4+ Styles]` est celui, complet, de la spécification ASS, et non la forme abrégée de l'exemple du § 1 | libass et ffmpeg lisent la ligne `Format:` pour nommer les colonnes : une forme abrégée prive le style de `SecondaryColour`, donc du karaoké, et de `Outline`, donc du contour de la charte |
| 16 | `words.fallback_reason` gagne `operator_override` | `subtitles --engine whisper` est prévu par le § des commandes. Sans cette valeur, un moteur forcé par l'opérateur obligerait à inscrire une cause mesurée qui n'existe pas — `words.json` mentirait sur le motif du repli |
| 15 | La largeur de ligne appliquée est `min(charte.subtitles.max_chars_per_line, 42)` | Le contrat de charte dit 38 par défaut, le prompt de l'étape 11 plafonne à 42. Le plus strict des deux s'applique, et le plafond de 42 ne peut pas être dépassé par une charte mal remplie |

### Divergences ajoutées par l'étape 12.1

| # | Écart | Motif |
|---|---|---|
| 17 | **Le texte n'est pas gravé par `drawtext` mais rastérisé par Pillow en PNG RGBA, composé par `overlay`** | Mesuré le 16/09/2026 : le ffmpeg de la machine cible (Homebrew 8.1.2, formule `ffmpeg` de homebrew-core) est compilé **sans `libfreetype`, `libfontconfig` ni `libass`** — `drawtext` répond `No such filter: 'drawtext'`, et `subtitles`/`ass` sont absents eux aussi. Le rendu vidéo reste entièrement ffmpeg. Effet de bord favorable : `drawtext` n'a **aucun retour à la ligne**, il aurait fallu mesurer la fonte en amont de toute façon. **Conséquence à traiter avant l'étape 13 : l'incrustation de `subtitles.ass` dans `final.mp4` exige libass — cette build ne peut pas la faire** |
| 18 | `StatsShotlist` gagne `p10_shot_s`, `p90_shot_s`, `n_shots`, `median_hook_s` ; `median_shot_s` est mesurée **hors hook** | Le § 1 ne portait que la médiane. Le hook coupe à 0,6 × cible par consigne : l'inclure ferait passer une consigne pour une dérive. Les déciles entrent au contrat pour que le banc de l'étape 15 compare une **distribution** et non un point |
| 19 | `manifest.decisions` gagne `cut_rhythm_planned_s` | `cut_rhythm_measured_s` est ce que le QC mesurera sur `final.mp4` par détection de plans ; `cut_rhythm_planned_s` est ce que `shotlist` a décidé. Les deux divergeront (un fondu enchaîné n'est pas une coupe pour PySceneDetect) : les confondre rendrait l'écart inexplicable à l'étape 26 |
| 20 | Pour un `asset_request.type == "card"`, `prompt_or_keywords` porte **l'identifiant du gabarit** (`plein` \| `bandeau_bas` \| `carte_centrale`) | Le contrat ne définit ce champ que pour `image` (prompt) et `stock` (mots-clés). Une carte n'a ni prompt ni banque : ce qui la décrit, c'est son gabarit, et c'est ce dont le moteur a besoin |
| 21 | Une rupture sur un moteur à **un seul type d'asset** change de gabarit et de mouvement, pas de type | La règle « une rupture force un changement de type d'asset » suppose que le moteur en offre deux. `cartes` n'a que `card` ; l'étape **signale** l'adaptation à chaque passage plutôt que de déclarer un changement qui n'a pas lieu |
| 22 | `provider: charte` avec `source_url` pointant sur `config/channels/<id>.yaml#charte@<version>` | Le validateur `Asset` exige une `source_url` pour tout fournisseur autre que `flux`. La source d'une carte **est** la charte ; l'écrire ainsi la rend vérifiable dans le dépôt, au lieu de forcer un `null` que le modèle refuse ou une URL inventée |
| 23 | Le `StyleEngine` reçoit la phrase de divulgation à la construction (`texte_divulgation`) | Le contrat dit qu'un moteur ne connaît pas la langue, et la loi 2023-451 exige la mention « Publicité » incrustée. Les deux tiennent si le pipeline lit `config/languages/<code>.yaml` et **passe** la phrase au moteur, qui ne la choisit jamais |
| 24 | `clips/shot_XX.mp4` est encodé en `-crf 18` | Le contrat du § 1 dit 18, le prompt de l'étape 12.1 disait 16. Le contrat gagne : c'est lui que le QC relira |

### Divergences ajoutées par l'étape 12.2

| # | Écart | Motif |
|---|---|---|
| 25 | **`charte` gagne `style_prefix`, `style_suffix` et `negative_prompt` ; `charte.framing` gagne `background` et `subject_scale`** | Le contrat de charte ne portait aucun style d'image. L'étape 5.2 a mesuré ce que cela coûte : sur 8 plans d'une même vidéo, **un plan encadré d'une marge quand les autres allaient au bord**, et un personnage qui change de sexe et de coiffure. Le cadrage et le fond laissés au modèle changent d'un plan à l'autre ; écrits dans la charte, ils ne changent pas. `negative_prompt` existe mais **n'est pas envoyé au modèle** : FLUX.2 refuse `--negative-prompt`, et la charte reste malgré tout le seul endroit où cela se déciderait |
| 26 | `library_assets` gagne `prompt_key` et `created_at` | La clé de cache du moteur illustré est `sha256(prompt normalisé + style + charte + format)`. Sans colonne, deux plans qui demandent la même image ne pourraient pas la partager — c'est pourtant ce qui fait tomber 127 plans à 56 générations sur le run FR |
| 27 | Un plan `asset_request.type == "stock"` reçoit, sous le moteur `illustre_anime`, **une image générée en cadre large** au lieu d'un asset de banque | Les banques libres sont livrées par l'**étape 17**. Le plan est servi, la règle « la rupture change de type d'asset » ne l'est pas, et le journal le signale à chaque passage. À retirer quand le moteur `documentaire` existera |
| 28 | `manifest.decisions` gagne `quality_notes[]` (`critere`, `note_sur_5`, `juge`, `date`, `commentaire`, `echantillon`) | Le prompt de l'étape 12.2 demande une note /5 au manifeste. Une note sans juge ni échantillon ne vaut rien : ce que la session perçoit (une image fixe) et ce qu'elle ne perçoit pas (le mouvement, le son) ne se jugent pas de la même façon, et le champ doit dire lequel des deux il porte |
| 29 | Les caches `HF_HOME` et `MFLUX_CACHE_DIR` sont **imposés à chaque sous-processus de modèle** par `factory.assets.images.environnement()` | Mesuré le 16/09/2026 : mflux est installé en `uv tool`, donc hors du `.venv` et hors du `.env` du projet. Lancé sans ces variables, il **re-télécharge 4,3 Go** dans `~/.cache/huggingface` — 2 Gi de disque partis en 13 minutes, contre la règle du ledger (`CLAUDE.md` § 3) |
| 30 | **Le sujet d'un prompt d'image est traduit en anglais par le LLM local** quand `channel.lang != "en"`, par lots de 8, avec le cache LLM du projet | Mesuré le 16/09/2026 sur les cinq premières images du run FR : deux portaient du faux texte en gros caractères et **l'une avait recopié le prompt français dans l'image** (« un cristal de sucre », lisible en toutes lettres). FLUX.2 [klein] est légendé en anglais : ce qu'il ne comprend pas, il le rend littéralement. Le traducteur remplace en outre toute mention d'écriture, de chiffre ou d'étiquette par un équivalent visuel — **nommer le texte, même pour le nier, le fait apparaître**. Coût mesuré : 18,4 s pour 8 intentions, soit ~2 min pour un run de 127 plans |
| 31 | Le `style_suffix` d'une charte ne contient **aucun mot désignant du texte** | Corollaire du n° 30, et il a fallu le payer : le premier suffixe écrit disait « clean unmarked surfaces, plain untitled objects, blank labels ». Les trois mots `unmarked`, `untitled` et `labels` sont eux-mêmes des déclencheurs. Le suffixe décrit désormais la matière en positif — « smooth matte surfaces, uniform colour fields, soft even shading » |


### Divergences ajoutées par l'étape 13.1

| # | Écart | Motif |
|---|---|---|
| 32 | **Une transition ne prend jamais de temps à la ligne du temps : elle en emprunte aux plans qu'elle relie** | `xfade` de durée *d* rend `lenA + lenB − d`. Les clips étant rendus à la durée exacte de leur plan, calée sur la voix, les **55 fondus** du run FR raccourciraient la vidéo de **16 s** et décaleraient l'image de la voix un peu plus à chaque fondu. Le montage se fait donc en pièces dont la somme des images est, par construction, celle des clips : un fondu enchaîné gèle la dernière image du plan sortant pendant *d* et rogne *d* en tête de l'entrant ; un fondu au noir prend *d*/2 à chacun. Mesuré : **22 139 images attendues, 22 139 obtenues** |
| 33 | `assemble` écrit `video_nomusic.mp4` et **`assembled.mp4`** ; `final.mp4` est écrit par `export` (§ clips disait `assemble` pour les deux) | C'est le découpage du prompt de l'étape 13.1, et il a un sens : `final.mp4` est le fichier **vérifié**. `export` le copie ensuite dans `workspace/export/<video_id>.mp4` comme le prévoit § Commandes |
| 34 | La ligne `final.mp4` de § clips disait « sous-titres **incrustés** depuis `subtitles.ass` » : l'incrustation devient **conditionnelle à `charte.subtitles.burn_in`** | Les quatre chaînes ont `burn_in: false` et `captions_upload: true` : la route est la piste `mov_text`, étiquetée de la langue en ISO 639-2. Corollaire codé : `burn_in: true` **échoue** sur cette machine (build ffmpeg sans `libass`) au lieu de retomber en silence sur le mux — livrer une vidéo sans les sous-titres qu'on croyait incrustés est le pire des deux résultats. `ROADMAP.md` § 13.1 est amendé du même coup |
| 35 | `charte` gagne `transition_duration_s` (défaut 0,32 s, borné à [0,25 ; 0,40]) | Le prompt impose « xfade 0,25-0,4 s » : la valeur appartient à la charte, comme le **type** de transition, pas au code du montage |
| 36 | `config/niches/<id>.yaml` gagne `musique.mood` ; `script.json` gagne `music_mood` facultatif | Une piste se choisit par ambiance. La niche en porte une par défaut (8 fichiers renseignés), un script peut la surcharger pour une vidéo |
| 37 | `manifest.decisions` gagne `music_warning` | Un lit silencieux est une **décision de production** ; sans motif écrit, elle est indistinguable d'un oubli. `music_track` reste vide, ce qui bloque déjà la publication (§ 10.1) — le champ dit *pourquoi* |
| 38 | Une piste de `library/music/` porte son manifeste en **`<slug>.json`** frère, et non un `licence.json` unique par dossier comme le suppose `LibraryPaths.licence()` | Le dossier `music/` contient plusieurs pistes ; un `licence.json` par dossier ne pourrait pas les distinguer. Les autres sous-dossiers de la bibliothèque, un asset par dossier, gardent la convention d'origine |
| 39 | `export` **ne réencode pas** le flux vidéo quand `ffprobe` le trouve déjà au contrat (H.264 High, 1920×1080, `yuv420p`) | `assemble` produit exactement ce que demande l'export, parce que `factory.video.arguments_encodage` est la seule porte d'encodage du projet. Réencoder ne changerait aucun paramètre : cela ajouterait une génération de perte et ~8 min de calcul. `--reencode` force le passage, et le contrôle `ffprobe` qui suit est ce qui rend la copie sûre |
| 40 | Le montage force la **coupe franche dans le hook**, même quand la charte autorise le fondu | Une vidéo dont les premières secondes s'enchaînent en douceur perd le bénéfice du hook. Sur le run FR le forçage n'a rien changé (`shotlist` donnait déjà `cut`), mais la règle ne doit pas dépendre d'une autre étape pour être vraie |


### Divergences ajoutées par l'étape 13.2

| # | Écart | Motif |
|---|---|---|
| 41 | `manifest.decisions` gagne `thumbnail_text_variants[]` (`{text, words, score, rendered_as}`), distinct de `thumbnail_variants[]` | Un **texte** peut être écarté avant d'avoir été composé : 5 textes sont produits, 3 seulement deviennent des fichiers. Les confondre perdrait deux candidats par run — exactement la matière que la phase 3 met en concurrence |
| 42 | `VarianteMiniature` gagne `text_height_ratio` | C'est le critère de l'étape 13.2 (texte ≥ 12 % de la hauteur) et il ne se déduit pas de `text_area_ratio` : un texte large et plat tient la surface sans être lisible. La valeur est **lue sur la page rendue** (`getBoundingClientRect`), pas estimée d'après la taille de police |
| 43 | `metadata.json` gagne `made_for_kids` (toujours faux, refusé à vrai par le modèle) et `notify_subscribers` (de `config/channels/<id>.yaml → youtube`) | Les deux sont des champs de `videos.insert` que `publish` enverra mot pour mot ; absents du fichier, ils seraient décidés à l'upload, donc hors trace |
| 44 | `description_blocks` gagne `sources[]`, placé après les chapitres ; et **le bloc d'affiliation passe en première position** quand il existe | Deux écarts, deux motifs. Les faits du script sont sourcés (`research.json`) : taire les sources serait un choix éditorial pris par omission. Et l'ordre imposé par ce document place l'affiliation après les chapitres, quand `CONFORMITE` § 3 couche 3 exige la mention commerciale *« en première ligne de description […] avant toute autre ligne »* — **la règle la plus stricte prime**. Sans produit configuré, l'ordre de ce document s'applique tel quel |
| 45 | `config/languages/<code>.yaml → disclosure` gagne `ia_production` et `ia_controle_humain` ; `titres.mots_interdits[]` s'y ajoute | La ligne de divulgation IA de `CONFORMITE` § 3 est du **texte dans une langue** : sa place est dans le fichier de langue, comme la phrase Amazon. `ia_controle_humain` n'est ajoutée que si un humain **nommé** a relu — sous `auto-approve`, elle ne s'écrit pas. Les mots d'appât sont eux aussi du vocabulaire, donc par langue |
| 46 | `config/channels/<id>.yaml → youtube` gagne `category_id` et `notify_subscribers` | `snippet.categoryId` varie par chaîne (28 Science, 27 Éducation) et n'est pas déductible de la niche |
| 47 | `charte` gagne `thumbnail: {uppercase, templates[], hauteur_texte_min, fond_luminosite}` — **≥ 2 gabarits**, refusé en dessous | La rotation de gabarits est une exigence anti-clonage (`CONFORMITE` § 5) ; la casse du texte incrusté est une décision de charte, le corpus ne mesurant que le nombre de mots |
| 48 | `config/economics.yaml` : `ValeurSourcee` gagne `defaut`, employé tant que `valeur` est nulle ; `a_mesurer` **reste vrai** et le coût produit porte le drapeau | Le jalon de la phase 1 doit sortir un coût. Une valeur de repli documentée (30 W) le permet sans faire passer une estimation pour une mesure ; une `defaut` sans `note` est refusée par le modèle |
| 49 | `manifest.execution` gagne `run_started_at`, `run_ended_at` et `wallclock_s` | `wallclock_s` ≠ somme de `timings` dès qu'un run est repris ou attend : la somme dit ce qu'a coûté le **calcul**, l'horloge ce qu'a duré la **production**. Le coût se calcule sur la première |
| 50 | `execution.timings[<noeud>]` porte la mesure de l'**orchestrateur**, pas celle de l'étape, quand les deux existent | Chaque étape mesure de l'intérieur de son processus : elle ignore le démarrage de l'interpréteur et le chargement du modèle. Le coût d'un run se calcule sur la mesure du dehors, jamais sur la plus flatteuse des deux. `compute_min` ne somme **que** les 11 nœuds du DAG : `timings` porte aussi des compteurs (`render_n_clips`, `subtitles_cues`) qui ne sont pas des secondes |
| 51 | **Un code 4 ne casse pas `factory run`** : le DAG continue, le run finit en `run_state: awaiting_review`, l'écart va dans `execution.errors[]` | `export` sort en code 4 depuis l'étape 13.1 sur un critère de style arbitré par Thomas ; s'arrêter là ne produirait jamais la vidéo complète du jalon. Un code 7 arrête le run **sans échec** (attente humaine), tout autre code le met en `failed` avec `blocked_reason` lisible. Ce qui n'est pas fait : abaisser un seuil pour faire passer un run |
| 52 | Les tags **n'emploient pas** `spec.topic.sujet` | Le sujet vient du corpus anglophone de l'étape 3 : recopié tel quel sur une chaîne française, il produit des tags anglais sur une vidéo française (mesuré : « what happens every when », « sugar »). Les entités de `research.json` et les textes à l'écran du script sont, eux, dans la langue du run |
| 53 | Les chapitres sont espacés d'au moins `max(10 s, durée ÷ 12)` et plafonnés à 12 | Le contrat YouTube n'impose qu'un plancher de 3 chapitres et 10 s d'écart. Un chapitre toutes les 20 s (27 sur 12 minutes, mesuré) n'est plus un sommaire, c'est la transcription du script |
| 55 | Les marqueurs `.done` sont écrits par **l'orchestrateur**, pas par l'étape elle-même, et `factory run` connaît **11 nœuds**, pas 19 | `ARCHITECTURE` § 1.2 prévoit que chaque étape écrive son marqueur en dernier. Le faire dans `run.py` évite de toucher aux neuf étapes déjà livrées et mesurées, au prix d'une conséquence à connaître : une étape lancée **à la main** (`factory voice --run …`) ne pose pas son marqueur, et `factory run` la rejouera. Les nœuds `review`, `qc`, `publish`, `measure`, `learn` et les trois sous-phases d'`assets` ne sont pas dans le DAG de la phase 1 : `assets.*` est exécuté à l'intérieur de `render` depuis l'étape 12.2, et les autres sont livrés par les étapes 15, 19 et 23 à 26. `--from` n'accepte donc que les 11 nœuds existants, et le dit |
| 54 | `PLAYWRIGHT_BROWSERS_PATH` rejoint `HF_HOME`, `OLLAMA_MODELS` et `LLAMA_CACHE` dans `.env` **et** est imposé par le code avant tout lancement de navigateur | Même défaut que mflux à l'étape 12.2 : sans la variable, Playwright retélécharge 0,21 Go dans `~/Library/Caches`. Rencontré au premier appel de `factory thumbnail` |


### Divergences ajoutées par l'étape 15

| # | Écart | Motif |
|---|---|---|
| 56 | `config/qc.yaml → poids` porte les poids des **familles** (coupes, hook, audio, durée, lisibilité, variété, parole, sous-titres, structure), et non plus ceux de chaque contrôle | Le barème écrit à l'étape 9 mettait `cut_rhythm` et `subtitle_coverage` sur le même plan alors que le premier est une famille de cinq mesures et le second une mesure isolée. Les poids par famille sont ceux du prompt de l'étape 15 ; `parole`, que ce prompt impose comme module mais oublie au barème, y est ajoutée à 5. Le poids **dans** la famille vit dans `seuils.<mesure>.poids` |
| 57 | `qc.json` porte `metrics{}` **et** `checks[]`, `verdict: PASS \| FAIL` **et** `verdict_pipeline: pass \| regenerate \| blocked` | Deux lecteurs, deux besoins. Le portillon répond oui ou non ; l'étape 22.2 a besoin de `regenerate_steps[]` et de la sémantique en trois états de ce document. Les deux vues sont calculées depuis les mêmes objets, jamais saisies deux fois. `checks[]` reste le contrat d'origine |
| 58 | Chaque mesure porte `unit`, `target_source` et `note` en plus de `value`/`target`/`status` | « Toute mesure a une unité, une cible et une source » (contrainte de l'étape 15). `target_source` distingue les trois origines possibles — registre, décision de production, paramètre de rendu — sans quoi l'étape 26 corrélerait le score aux vues sans savoir ce qu'elle corrèle |
| 59 | `manifest.decisions` gagne `qc_score`, `qc_verdict` et `qc_version` ; la table `runs` gagne `qc_verdict` et `qc_version` (migration 003) | `score_qc` existait déjà dans la table sans jamais être écrit, et sans son verdict une requête ne distingue pas « 68, refusé » de « 68, publié faute de bloquant ». La version du barème est nécessaire à l'étape 26 : deux scores calculés par deux bancs différents ne se corrèlent pas ensemble |
| 60 | `qc.json` gagne `not_covered[]`, recopié depuis `config/qc.yaml` | Le portillon doit **déclarer ses trous** (avertissement de l'étape 5.2 § 2.12) : l'anatomie fausse, les éléments détachés et la dérive d'identité ne sont pas atteignables sans modèle vision-langage. Une vidéo qui passe le banc n'est pas une vidéo relue |
| 61 | `qc.json` gagne `missing_inputs[]`, et un fichier d'entrée absent devient une **raison d'échec** | Une entrée manquante rend des mesures `skipped`, ce qui **monte** mécaniquement le score en retirant du dénominateur. Sans cette règle, supprimer `words.json` serait le moyen le plus simple de faire passer une vidéo |
| 62 | `factory.audio.measure_lufs` ajoute `-map 0:a:0 -vn` | Sans eux, ffmpeg décode aussi le flux vidéo pour l'envoyer au `null` : mesuré à **plus d'une minute contre 4 s** sur un MP4 de 12 minutes. Le résultat est identique, seul l'audio entre dans `ebur128`. Même correction sur `silencedetect` et `volumedetect` |

### Divergences ajoutées par l'étape 20

| # | Écart | Motif |
|---|---|---|
| 63 | `topics_queue` s'écrit `(id, channel_id, lang, niche, cluster_id, topic, angle, score, evidence_json, status, created_at, used_by_run)` et non `(topic_id, lang, niche, sujet, angle, score, evidence_json, cluster_id, state, created_at)` | Un sujet est noté **pour une chaîne**, pas pour une langue : le fit niche/style et le malus de similarité aux sujets déjà produits dépendent tous deux de la chaîne. `used_by_run` manquait et sans lui rien ne relie un run au sujet qui l'a produit. `topic_id`→`id`, `state`→`status`, `sujet`→`topic` suivent le prompt de l'étape 20. `UNIQUE(channel_id, topic)` empêche l'empilement à la reprise |
| 64 | Deux tables neuves non prévues : `embeddings(video_id, model, dim, vector, text_hash, computed_at)` et `topic_clusters(cluster_id, run_date, …)` | Le cache de vecteurs est une nécessité de coût (50 s pour 5 604 titres sur M2, à repayer à chaque exécution sinon) et `text_hash` est une nécessité de correction : sans lui un titre corrigé chez l'éditeur garderait le vecteur de l'ancien. `topic_clusters` conserve la trace datée d'un découpage que le seuil de distance rend non reproductible d'un modèle à l'autre |
| 65 | `topics.regroupement.seuil_distance` vaut **0,12**, non 0,30-0,45 comme le conseille la littérature | Mesuré sur les 5 604 titres du corpus : `multilingual-e5-small` a un cosinus **médian de 0,812 entre deux titres tirés au hasard**. À 0,35 de distance, **tout le corpus forme un seul cluster**. Le balayage complet est dans `config/editorial.yaml`. **Un changement de modèle d'embeddings impose de le refaire** |
| 66 | La résurgence porte sur un **indice** de vélocité (vélocité ÷ médiane du décile d'âge), non sur la vélocité brute | Mesuré : vélocité médiane de 4 736 vues/j entre 0 et 30 jours contre 150 entre 90 et 180, un facteur 31. `velocity_life` décroît mécaniquement avec l'âge ; sur la vélocité brute, **9 clusters éligibles sur 10** passaient le seuil de 1,5 et 10 sur 10 dépassaient 1,0. Le critère mesurait l'âge |
| 67 | `topics.trous.resurgence.age_median_min_jours` passe de 365 à **120** | Le corpus ne remonte qu'à `fenetre_jours` = 180 : un seuil de 365 rendait le critère **structurellement inatteignable**, donc silencieusement toujours faux |
| 68 | `plan` ne lit pas `workspace/topics_queue.json` comme l'annonçait le point d'extension de l'étape 10, mais la table `topics_queue` | La file porte un statut qu'un humain modifie (`approve`/`ban`) et un lien vers le run qui l'a consommée : un fichier JSON réécrit à chaque exécution perdrait les deux. `plan` se replie proprement si la migration 006 n'est pas appliquée (`sqlite3.OperationalError` → référentiel) |

### Divergences ajoutées par l'étape 21

| # | Écart | Motif |
|---|---|---|
| 69 | Le plafond de description est **5 000 octets**, pas 5 000 caractères, et le budget de tags compte **+2 caractères par tag contenant une espace** | Ce sont les deux règles exactes de l'API (`videos.insert`), vérifiées à l'étape 21. Compter en caractères et sans guillemets laisse passer une fiche qui sort en `400 invalidTags` ou en description tronquée par le serveur. Le contrôle est dans `VideoMetadata`, donc rejoué à chaque relecture du fichier |
| 70 | `VarianteTitre.pattern` devient `pattern_id`, et gagne `heuristic`, `llm_rank`, `promise_kept` | Une seule note ne distinguait pas ce que les règles savent juger (longueur, patron, forme) de ce qu'elles ne savent pas (l'envie de cliquer). La phase 5 ne pourra dire laquelle prédit le clic que si les deux sont conservées séparément. L'ancien nom `pattern` reste **lu** : les manifestes d'avant l'étape 21 doivent rester relisibles |
| 71 | Le classement final des titres est un **tournoi de duels** (4 entrants, 2 demi-finales, 1 finale), pas un classement demandé en un appel | Comparer deux objets est la tâche sur laquelle un 9B quantifié se trompe le moins ; lui demander de classer huit titres d'un coup produit un ordre qui ne survit pas à une permutation de l'entrée. Le tournoi ne donne qu'un **ordre partiel** — les deux éliminés de demi-finale ne sont pas départagés entre eux et gardent leur rang de semence, et le manifeste le dit |
| 72 | La netteté de la miniature se mesure sur la **vignette entière**, pas sur la boîte de texte, et sature à 2 000 | Mesuré le 20/09/2026 sur les trois rendus du run `avwf` : fond nu 330, miniature complète 3 559 à 5 788, flou gaussien de 6 px 476 à 709. Le texte occupe un tiers de la surface et domine le laplacien : c'est bien son apport qu'on lit, sur une zone dont l'échelle est calibrée |
| 73 | La surface de texte n'a **pas d'optimum**, seulement une plage [10 %, 45 %] à poids faible | Personne n'a mesuré la surface idéale — le référentiel compte des *mots*, pas des pixels. Un optimum inventé à 12 % mettait les trois variantes à zéro sur ce terme, c'est-à-dire ne départageait rien tout en pesant 15 % du score |
| 74 | La taille de police est **ajustée dans la page** avant la capture, et le débordement est mesuré (`text_overflow_pct`) | La taille déduite du nombre de caractères est une approximation : « STRETCHING » sortait du cadre sur le run `avwf` alors que toutes les autres mesures de la variante étaient bonnes. Le navigateur connaît la largeur réelle une fois la police chargée ; on la lui demande plutôt que d'affiner un coefficient au jugé |
| 75 | `factory run --channel <id> --from <etape>` **reprend le dernier run** de la chaîne au lieu d'en créer un neuf | Un run neuf n'a que sa `spec.json` : l'étape demandée tomberait sur un contrat d'entrée vide. Le run repris est le plus récent dont **tous les marqueurs amont existent** — et non celui dont les fichiers d'entrée déclarés existent, car ces entrées ne sont que les fichiers légers de l'empreinte (`thumbnail` déclare `script.json` et `shotlist.json` mais a besoin des images de `render`). Un marqueur à l'empreinte périmée n'empêche pas la reprise : il est **nommé** dans une alerte, ce que `--from` sert précisément à traiter |
| 76 | L'autocomplete YouTube est filtré : une suggestion qui **prolonge** une suggestion déjà retenue est écartée | Mesuré le 20/09 : « mysteries of the universe » revenait cinq fois (« … book », « … in hindi », « … in tamil »…) et consommait 150 des 500 caractères de tags pour une seule idée |
| 77 | La migration de la file est **`007_queue.sql`**, pas `003_queue.sql` comme l'écrivait le prompt de l'étape 22.1 | `003_qc.sql` existe depuis l'étape 15 et les migrations sont numérotées, jamais renumérotées (`db.migrations_disponibles()` lève sur un nom hors motif). La table `jobs` existait déjà, posée par `001_runs_jobs_review.sql` ; 007 la **reconstruit** pour lui ajouter `locked_by`, `locked_at` et une contrainte `CHECK` sur `status` — SQLite ne sait pas ajouter un `CHECK` à une table existante, et un statut mal orthographié rendrait le job invisible de toutes les requêtes du runner |
| 78 | Les plafonds de temps de `config/orchestrator.yaml` ne sont **pas** ceux du prompt (« script 15 min, render 90 min ») | Mesuré : `script` a pris **1 511 s (25 min)** sur `bms-histoire-en-20260918-pt83` et 1 522 s de LLM. Un plafond à 15 min tuerait un script en train d'aboutir. Les valeurs retenues sont celles de `factory/run.py`, calées sur les étapes 10 à 21 : `script` 2 700 s, `voice` 7 200 s, `render` **960 s par plan** et non un forfait — 114 plans donnent 30 h de plafond, ce qui est un garde-fou contre la boucle, pas une prévision |
| 79 | Le plist du daemon écrit `KeepAlive = {SuccessfulExit: false}` et non `KeepAlive = true` | Avec `true`, launchd relance le daemon à **chaque** sortie, y compris celle que `factory daemon stop` vient de demander : la commande d'arrêt deviendrait un redémarrage. Avec le dictionnaire, la relance n'a lieu que sur code non nul. `ThrottleInterval: 60` évite la boucle serrée si le démarrage échoue immédiatement, et `ProcessType: Standard` évite que launchd throttle le CPU et les E-S d'un rendu ffmpeg |
| 80 | La fenêtre nocturne est appliquée **dans le processus**, pas par `StartCalendarInterval` | `StartCalendarInterval` sait démarrer à 22:00, il ne sait pas arrêter une étape à 07:00 ; et launchd ne garantit aucun état d'alimentation — un job programmé sur une machine endormie part en DarkWake ou ne part pas du tout (forums développeurs Apple, 2025). Le daemon vit donc en continu et refuse les étapes lourdes hors fenêtre, étape par étape. Corollaire d'exploitation, écrit dans `EXPLOITATION.md` § 2 : **secteur + capot ouvert**, aucune option de `caffeinate` n'empêche le sommeil du capot fermé |
| 81 | Le DAG du runner est celui de `factory run` **plus `qc`** | `factory run` s'arrête à l'export : le portillon n'y est pas câblé (résidu assumé de l'étape 15) parce qu'un humain était là pour lancer `factory qc`. Sous daemon, personne. Un `qc` en code 4 met le job en `blocked` avec ses raisons ; la régénération sous seuil est le sujet de l'étape 22.2. Conséquence : un job n'atteint `exported` **que si le banc a rendu PASS** |
| 82 | `factory queue approve <job> --reviewer <id>` existe dès l'étape 22.1, alors que la relecture est livrée par l'étape 22.2 | Sans elle, un job en `awaiting_review` n'a aucun moyen de repartir et le test de bout en bout est impossible. L'alternative proposée par le prompt — passer `auto_approve` à `true` le temps du test — retirerait l'exception éditoriale du RIA art. 50 sur les vidéos produites, pour une commodité de test. La commande écrit la ligne `review_log` complète (relecteur de `config/team.yaml`, date, `sha256` du script) : **la trace de conformité est définitive dès maintenant**, c'est l'interface de relecture par lots qui reste à faire |
| 83 | La politique de nouvelle tentative ne distingue pas un échec transitoire d'un échec **déterministe** | Constaté le 20/09 au premier essai : `research` sort en code 1 sur « 2 sources obtenues, 3 exigées » pour un sujet non sourçable. Les trois tentatives échoueront à l'identique et coûteront 1 h 20 d'attente pour rien. Non corrigé à cette étape — classer les codes de sortie en « à rejouer » / « à ne pas rejouer » relève de la sémantique d'erreur de chaque étape, pas de l'orchestrateur. Contournement en place : `factory queue block <job> --reason` sort le job en une commande. **Porté à `SUIVI.md` § 1** |
| 84 | `verify_clip` traite un clip **illisible** comme un écart, pas comme une panne | Mesuré le 21/09/2026 : le `kill -9` du test de reprise a laissé `clips/shot_19.mp4` tronqué — 262 Ko écrits, ffmpeg tué avant l'atome `moov`. Au redémarrage, le réemploi de `render` appelait `verify_clip` sur ce fichier, `ffprobe` levait, et **l'étape entière sortait en code 1**, à l'identique aux trois tentatives. La fonction savait dire « absent », pas « présent et illisible ». Elle rend désormais l'écart, et le plan est simplement refait — vérifié : `shot_19.mp4` est repassé de 262 Ko tronqués à 800 578 octets lisibles. Couvre les quatre appelants (`render.py`, `whiteboard.py`, `motion.py`) |
| 85 | `decharger_agent` pose un `launchctl disable`, pas seulement un `bootout` | `bootout` ne vaut **que pour la session de démarrage en cours** : le plist reste dans `~/Library/LaunchAgents/` et launchd le rebootstrappe à l'ouverture de session suivante. Mesuré le 21/09/2026 après une panique noyau : `com.bms.factory.daemon`, déchargé la veille et documenté comme tel dans `STATE.md`, était de retour dans `launchctl list` (pid 1512), prêt à produire sans surveillance à 22:00. `disable` écrit dans l'état persistant de launchd et survit au redémarrage ; `charger_agent` le relève par `enable` avant `bootstrap`, sans quoi `bootstrap` réussit et launchd refuse quand même de lancer l'agent. **Une consigne d'exploitation qui ne survit pas à un redémarrage n'est pas une consigne d'exploitation** |
| 86 | `review_log` est **reconstruite** par la migration 008, sa clé primaire n'est plus l'empreinte du script | Avec `review_hash` en clé, l'`INSERT OR REPLACE` d'une approbation **écrasait** le rejet qui l'avait précédée : le journal perdait exactement l'enchaînement « rejeté → corrigé → approuvé » qui démontre le contrôle éditorial du RIA art. 50 §4, et `CONFORMITE` § 10.2 dit « ne réécris jamais une ligne ». La clé devient un identifiant de ligne, `motif` sort de `batch_id` où il logeait, et `review_hash`/`review_date` restent lisibles en **colonnes générées** — un seul stockage, deux noms, aucun appelant à réécrire |
| 87 | Une décision de relecture est écrite à **quatre** endroits par un seul appel (`review.enregistrer_decision`) | `registre/data/reviews.jsonl` (la pièce append-only), `review_log` (l'index), `review.json` (le miroir du run) et le manifeste. L'ordre n'est pas indifférent : la pièce d'abord, l'index ensuite — si le processus meurt entre les deux, `factory queue reindex` reconstruit l'index depuis les fichiers, l'inverse serait une preuve perdue. `factory queue approve` de l'étape 22.1 a été rebranché sur ce chemin : deux endroits qui écrivent la même preuve finissent toujours par diverger |
| 88 | Le remède choisi est le **plus tardif dans le DAG**, pas le plus proche de la cause | Arithmétique : repartir de `assemble` coûte 198 s + 25 s + 45 s (mesures de l'étape 22.1) ; repartir de `script` coûte 918 s **plus tout l'aval**, soit ≈ 4 h avec le rendu. Quand deux mesures échouent, corriger la plus tardive et remesurer est toujours moins cher que tout rejouer — et si le défaut amont persiste, la seconde régénération s'en charge. Un remède déjà tenté sur la même mesure est écarté : deux tentatives, jamais deux fois la même |
| 89 | Un contrôle `verdict_fail: blocked` a droit à **une** régénération quand la table `remedes` le nomme (`remedes_sur_bloquant: true`) | Deux documents se contredisaient : `QC.md` § 4 fait de `loudness` un bloquant sans reprise, le prompt de l'étape 22.2 demande « loudness → assemble ». Les deux ont raison sur une moitié — un niveau sonore hors norme est tantôt un montage interrompu (cas mesuré le 21/09 : `shot_19.mp4` tronqué par un `kill -9`, réparé en un remontage), tantôt un défaut de fond, auquel cas la reprise échoue et le job bloque quand même. On tente une fois et on mesure. Un bloquant **absent** de la table bloque sans reprise, comme avant |
| 90 | Le motif d'un rejet et les consignes des remèdes passent par `workspace/runs/<run>/consignes.json`, versé dans l'invite **système** de `factory script` | Versé dans le seul prompt du plan, le motif laisserait le modèle réécrire la même narration : l'étape enchaîne plan, accroche, narration et réparations, chacun avec son gabarit. L'invite système est le seul point que tous traversent. Le fichier est en **append** : un script rejeté deux fois porte les deux motifs, faute de quoi la seconde réécriture réintroduit le défaut de la première |
| 91 | Le levier `assets_differents` écrit `assets/exclus.json`, consulté par `_reutilisable` des images générées | Le rejeu du même run est précisément le cas où la bibliothèque **autorise** la réutilisation (objection 18 : sans cette exception, une reprise après incident régénérerait des heures d'images déjà payées). Le remède « variété visuelle faible » a besoin de l'exception inverse, et sans elle la reprise redemanderait les mêmes images : la variété ne bougerait pas d'un point. Les assets de banque, eux, n'ont rien eu à changer — ils refusaient déjà le doublon dans une même vidéo |
| 92 | `factory review` ne lit jamais l'entrée standard : la CLI lui **passe** une fonction `demander` | Une boucle interactive qui appelle `input()` n'est testable qu'avec un faux terminal. Ici le module rend `(touche, texte)` à qui l'appelle : la CLI branche `typer.prompt`, les tests branchent une liste, et les treize décisions de relecture sont éprouvées sans terminal |
| 93 | Le quota d'API du digest affiche « non mesuré » plutôt que 0 % | `quota_ledger` arrive à l'étape 23.1 ; la seule source honnête aujourd'hui est `collect_runs.units_used`, qui ne couvre que la collecte. Un « 0 % » rassurant ferait rater le jour où `videos.insert` s'arrête à 100 appels. `quota_consomme` rend `None` et la raison |
| 94 | Une alerte ne part qu'au **changement d'état** (`workspace/logs/alertes.json`) | Le daemon passe la revue à chaque tour de boucle, soit toutes les 60 s. Sans mémoire de ce qui a déjà été signalé, un job bloqué à 23:00 produirait 480 notifications avant le matin et l'exploitant couperait le canal dans la semaine. Les scripts en attente sont en outre **regroupés** : un message pour N scripts, jamais N messages — c'est la contrainte « par lots » de `ROADMAP` § 3.4 appliquée à l'alerte elle-même |

### Divergences ajoutées par l'étape 25

| # | Écart | Motif |
|---|---|---|
| 95 | Migration **`011_analytics.sql`**, pas `005` | Le 005 est pris par `005_niches.sql` (étape 19) ; même traitement que 009 |
| 96 | Clé de `perf_daily` : **`(video_id, date)`**, pas `(youtube_video_id, date)` ; `retention_curves` indexée par `(video_id, day_after_publish)` avec jalons **2, 7, 30** au lieu de `window` | `video_id` est l'identifiant du manifeste ; le prompt de l'étape fixe ces colonnes. J+2 donne le premier retour, capturé seulement si J+7 n'est pas atteignable |
| 97 | **Pas de table `perf_window`** : `v_video_perf` agrège les jours 0-6 et 0-29 (sommes, moyennes pondérées par les vues) et porte `complete_7d`/`complete_30d` (fenêtre close depuis 72 h) ; `manifest.resultats.metrics_7d/30d` en est la copie | Même sémantique que l'objection 3 (fenêtre, pas jour J+7), sans table à tenir à jour |
| 98 | Table en plus : **`reporting_reports`** (fichiers déjà téléchargés) | « Nouveaux fichiers seulement » ; un rapport révisé (nouvel `id`, même période) est rechargé et remplace les lignes de ses jours |
| 99 | La série quotidienne se demande **vidéo par vidéo** (`dimensions=day`, `filters=video==ID`) | Aucun rapport de chaîne de l'Analytics API ne documente `dimensions=day,video` (vérifié le 23/09/2026) |
| 100 | `channel_basic_a3`, pas `a2`, est téléchargé ; il reste **brut**, seul `channel_reach_basic_a1` est chargé (`perf_reach`) | `a2` n'est plus documenté ; les métriques de `basic` doublent celles de l'Analytics API |
| 101 | `engaged_views` vaut **NULL**, jamais 0, si l'API refuse la métrique | Un zéro serait une mesure fausse |
| 102 | Les appels Analytics et Reporting sont inscrits au ledger en compartiment `reporting` à **0 unité** | Leur quota est distinct de la Data API et non documenté en unités ; on compte les appels (`analytics_runs.calls`) |
| 103 | `learned/weights.json` porte `version` (majeure `1`) ; tout consommateur passe par `factory/analytics/weights.py` et retombe sur le référentiel si le fichier est absent ou de majeure différente | Étape 26 : repli toujours possible |
| 104 | Les multiplicateurs de titres se lisent sous `titles.patterns` (et non `title_patterns`), bornés [0,7 ; 1,4] au lieu de [0,25 ; 4] | Bornes du prompt de l'étape 26 ; `test_seo.py` mis à jour |
| 105 | `manifest.decisions` gagne `learned_version` et `learned_applied` (poids appliqué par clé : `topic_multiplier`, `hook_parts`, `title_patterns`, `cut_rhythm`, `thumbnail`) | Traçabilité du poids appliqué |
| 106 | La rotation J+7 ne réécrit jamais `decisions.thumbnail_chosen` | La miniature initiale est un facteur appris ; la réécrire ferait fuiter un choix post-publication |
| 107 | `factory analytics rotate-thumbnails` sans `--dry-run` sort en code 2 : `thumbnails.set` n'est pas câblé tant qu'aucun jeton OAuth n'existe | Rien de réel à tester (0 publication) |
| 108 | `config/products/<id>.yaml` accepte `program`, `base_url`, `tracking_param`, `disclosure` comme synonymes de `network`, `target_url`, `subid_param`, `disclosure_override` ; nouveaux champs `sub_id_format`, `cta_text`, `landing_type`, `commission_hint` | Étape 27 : noms du prompt acceptés sans casser l'étape 21 ni `precheck` |
| 109 | Sous-identifiant = `sub_id_format` (défaut historique `{channel_id}_{lang}_{video_id}`, exemple `{video_id}`) ; **trop long ou hors `[A-Za-z0-9_-]` = erreur**, plus de troncature | Tronqué, il perdait la fin du video_id et attribuait à la mauvaise vidéo |
| 110 | Réseaux `digistore24` (`campaignkey`, 127, **dans le chemin**) et `clickbank` (`aff_sub1`, 100 — `tid` limité à 24 ne tient pas un video_id) | Veille du 23/09/2026 ; colonnes d'export non vérifiées |
| 111 | Bloc d'affiliation : 1ʳᵉ ligne = « PAID PROMOTION — <mention réseau> » ; la surcharge du produit **s'ajoute** à la mention du réseau ; le contrôle croisé exige la mention du réseau même avec surcharge | `precheck` 7-9 bloquait (mention pas en première ligne) : défaut antérieur, constaté à l'étape 27 |
| 112 | `cta_segment.position: apres_conclusion` (ou `fin`) : le segment `sponsor` est ajouté **après** la conclusion, gabarit `sponsor_cta` ; les autres positions gardent l'index 3 | `verify` : 0 infraction ajoutée (mesuré sur `c7km`) ; `precheck` indifférent à la position |
| 113 | Table `revenue` (migration **012**) : colonnes du prompt + `sub_id`, `origin` (`import`/`fixture`/`api`), `row_key` unique (ré-import idempotent) ; `video_id` NULL = non rattaché (Amazon : tracking ID seulement) ; `factory economics` exclut `origin = 'fixture'` | Distinguer importé et test dans la même base |
| 114 | `config/economics.yaml` gagne `relecture_forfait_min`, `couts_fixes_mensuels_eur`, `amortissement_materiel_mensuel_eur`, `serveur_gpu_mensuel_eur`, `taux_eur.<devise>`, `horizon_retour_jours` | Aucune hypothèse économique dans le code |
| 115 | Migration **013** : `library_assets` gagne `description`, `tags` (JSON), `size_bytes`, `embedding` (float32), `embed_model`, `embed_hash` ; table `library_semantic_reuse` ; `used_by` **non stocké**, lu dans `library_uses` (étape 29) | Une seule source des emplois |
| 116 | Réemploi sémantique en **cosinus centré** (vecteur moyen de la bibliothèque soustrait), seuil `channel.library.semantic_threshold` = 0,9 ; images seulement sous le même `prefixe:<sha(style_prefix)>` ; jamais un asset déjà servi dans le run | Cosinus e5 brut : 17 % des paires distinctes > 0,9 (mesuré sur 554 images) |
| 117 | `config/voices/<id>.yaml` (`VoiceProfile`) : `speaker`, `speed` (× `languages.tts.speed`), `pitch_semitones`, `reference_wav` + `reference_rights` ; le validateur refuse deux chaînes de même langue sur le même **locuteur** (moteur + speaker), pas seulement le même `voice_id` ; dossier facultatif | Deux identifiants peuvent désigner la même voix |
| 118 | `config/chartes/<channel>.yaml` fusionné dans `channel.charte` au chargement (`charte_version` → `charte.version`, `layouts` = gabarits, `intro`/`outro`) ; charte déclarée deux fois = erreur ; `channel.templates` ⊆ `charte.layouts` | La charte se versionne à part de la chaîne |
| 119 | `template_id` tiré par rotation (`runs.gabarit_suivant`), plus par graine ; `precheck` : contrôle `rotation_gabarit` **bloquant** si le run précédent de la chaîne a le même gabarit | CONFORMITE § 5 |
| 120 | Style `avatar2d` : `backend: ffmpeg` (pas revideo), statut `retenu_v2`, `params.mode` overlay\|presenter, sur le style hôte `channel.style` ; sorties `avatar/` du run (visèmes, `timeline.json`, sprites, `.mov` ProRes 4444) | Pillow + ffmpeg suffisent, aucun navigateur |

---

## 5. Objections et réponses

Un sous-agent contradicteur a relu `ARCHITECTURE.md`, ce document, les descriptions courtes des **étapes 9 à 27** de `ROADMAP.md` et `CONFORMITE.md` § 10-11. **19 objections. 17 corrigées, 1 corrigée autrement que proposé, 1 refusée sur preuve.** Les six angles demandés sont tous couverts ; aucun n'est revenu vide.

| # | Gravité | Objection | Traitement |
|---|---|---|---|
| 1 | bloquant | Le plafond de 6 publications par jour de `CONFORMITE.md` § 2 dépasse le quota : 2 050 unités par vidéo complète × 6 = **12 300 pour 10 000** | **corrigé** — plafond opérant à **4 publications complètes par jour**, décision prise sur le solde réel de `quota_ledger` et non sur un compteur de vidéos. La divergence avec `CONFORMITE.md` § 2 et son contrôle 27 est **écrite dans le contrat de `publish.json`** et portée à `SUIVI.md` : elle n'est pas tranchée par cette étape |
| 2 | bloquant | Personne n'écrit `published_at` sur le chemin `manual_studio` — c'est un humain qui publie dans Studio — donc aucune métrique n'est jointe sur le seul chemin ouvert avant l'audit | **corrigé** — `analytics pull` **rétro-remplit** `published_at` depuis `videos.list(part=status,snippet)` à chaque passage, et c'est lui qui déclenche les fenêtres J+7 et J+30 |
| 3 | bloquant | La vue joignait `perf_daily` sur `date(published_at,'+7 day')` : **la journée J+7, pas la fenêtre 0-6 jours** — l'apprentissage aurait porté sur le trafic d'une seule journée | **corrigé** — table `perf_window(youtube_video_id, window, …, day_count, complete)` qui agrège la fenêtre ; `v_video_perf` la lit, et `manifest.metrics_7d` en est la copie |
| 4 | bloquant | `sponsor_segments[].spoken_disclosure_at_s`, exigé par le contrôle 6 (bloquant), n'était produit par aucun fichier | **corrigé** — `script.segments[].disclosure_spoken` (écrit dans le script, donc relu par l'humain, donc couvert par `review_hash`) et `voice/timings.json.segments[].disclosure_at_s` pour la position mesurée |
| 5 | bloquant | `manifest.json` figurait en entrée de `metadata` : `inputs_hash` auto-référentiel, tout l'aval invalidé à chaque écriture | **corrigé** — règle générale ajoutée : **`manifest.json` n'entre jamais dans un `inputs_hash`**, et aucune étape n'écrit dans une sortie déclarée d'une autre. Entrées de `metadata` corrigées |
| 6 | bloquant | `subtitles` réécrivait `voice/timings.json`, sortie déclarée de `voice` : le `.done` de `voice` et l'`inputs_hash` de `shotlist` devenaient faux | **corrigé** — le WER par segment vit dans `words.json → segments[]`, avec son seuil par longueur |
| 7 | bloquant | Timeouts sous les mesures : `voice` 90 s/segment contre 99 s pour un segment de 30 s à RTF 3,29 ; `assets` 600 s/plan contre **621 s au pire mesuré** | **corrigé** — `voice` `max(180, 5 × duration_s)` ; `assets.image` **900 s**. Un plafond sous la pire mesure connue tue un plan qui allait aboutir |
| 8 | bloquant | Aucune péremption de `run.lock` / `model.lock` : le `kill` testé à l'étape 22.1 laisse un verrou orphelin, code 6 fatal, daemon arrêté | **corrigé** — un verrou dont le **PID est mort** est repris d'office avec un `WARN` ; un verrou tenu par un processus vivant reste une erreur fatale |
| 9 | bloquant | Les agents `launchd` (collecte 18, analytics 25, sauvegarde 22.1) et le modèle d'embeddings de l'étape 20 ne prenaient aucun verrou, contre **3,6 Go de marge** pendant `assets.image` | **corrigé** — les tâches planifiées prennent `run.lock` **en attente** ; le modèle d'embeddings prend `model.lock` et son pic est inscrit `a_mesurer` au § 8 et au ledger |
| 10 | bloquant | La table `runs` ne portait pas assez de facteurs pour la vue de l'étape 25 (voix, densité, patron de titre, variante de miniature, cluster, créneau) | **corrigé** — 12 colonnes de facteurs ajoutées, plus `manifest_json` ; toutes reconstructibles par `queue reindex` |
| 11 | sérieux | Le contrôle 22 lisait `cadence_limits` du manifeste — un instantané figé — quand `CONFORMITE.md` § 10.3 fait de `cadence.json` **la seule vérité** | **corrigé en partie** — `cadence_limits` porte `read_at` et le contrôle **relit `cadence.json` à l'upload**, refusant un instantané de plus d'une heure. **La seconde moitié est refusée** : sortir `cadence.json` de `workspace/library/` contredirait `CONFORMITE.md` § 10.3, qui fixe ce chemin. L'emplacement est discutable ; il n'est pas à nous de le changer ici |
| 12 | sérieux | `dedupe` en `PRIMARY KEY(kind, hash)` invite au test d'égalité, quand le contrôle 18 exige une **distance de Hamming ≥ 12** | **corrigé** — simhash en entier 64 bits, lecture par balayage et distance, et la règle est écrite à côté du schéma |
| 13 | sérieux | `metadata.json` n'avait ni `hashtags`, ni `localizations`, ni `pinned_comment`, exigés par les étapes 21 et 27 | **corrigé** — les trois champs sont ajoutés ; le commentaire épinglé est soumis aux mêmes divulgations que la description |
| 14 | sérieux | `conversions` n'avait ni `video_id` ni clé primaire, et le format du `subid` n'était pas fixé | **corrigé** — clé `(network, subid_value, day)`, colonne `video_id`, format imposé `<channel_id>_<lang>_<video_id>` tronqué à la limite du réseau, et `null` sur Amazon |
| 15 | sérieux | `config/qc.yaml` ne pondérait pas tous les contrôles et omettait ceux de l'étape 16 ; `qc` ne déclarait pas `words.json` en entrée alors qu'il mesure la couverture des sous-titres | **corrigé** — barème complet à 13 contrôles, `hors_bareme` pour les deux binaires, entrées de `qc` déclarées |
| 16 | sérieux | Les sous-phases `assets.image / depth / fetch` n'existaient ni dans `.done/`, ni dans les timings, ni dans `--from` | **corrigé** — ce sont **trois nœuds à part entière** ; sans cela, aucune reprise n'est possible au milieu de 4 h 34 de génération. Le DAG compte 19 nœuds |
| 17 | sérieux | Les noms de tables inventés ici contredisaient ceux que `ROADMAP.md` fixe déjà (`publications`, `quota_ledger`, `perf_daily`, `v_video_perf`, `reporting_jobs`, `channels_watch`…), ainsi que `secrets/tokens/` et les énumérations d'états | **corrigé, et c'est l'objection la plus utile du lot** — le schéma entier est réécrit sur les noms de la feuille de route, vérifiés un par un dans `ROADMAP.md`. Les trois vocabulaires d'état (`publish_state` de la conformité, `publications.status`, `jobs.status`) coexistent avec **une table de correspondance écrite une fois** |
| 18 | sérieux | La règle « aucun asset de premier plan partagé entre chaînes de même langue » était inapplicable faute de champ, et `cooldown_videos: 10` rendait impossible le critère « 2ᵉ exécution, 0 génération » de l'étape 12.2 | **corrigé** — `asset_request.layer` et `library_assets.layer` ; le cooldown ne compte que les usages d'un **autre** `video_id`, donc un rejeu du même run réutilise tout |
| 19 | mineur | `c2pa_preserved: true` est inatteignable après ré-encodage ffmpeg ; incruster les sous-titres **et** envoyer la piste donne un double affichage et dépense 400 unités | **corrigé autrement que proposé** — le champ n'est pas assoupli, il devient **mesuré** : il vaut `false` quand c'est vrai, et le contrôle 14 reste un avertissement. Ce qui est tenu, c'est l'interdiction de retirer volontairement un marquage. `charte.subtitles.burn_in` est rendu **exclusif** de `metadata.caption_file`, refusé par `config validate` |

**Ce que le contradicteur n'a pas trouvé, et qu'il faut lire comme tel.** Il n'a relevé aucune fuite de langue ou de chaîne d'un run à l'autre au-delà de celle du § 4 sur le premier plan (objection 18). Cela ne prouve pas qu'il n'y en a pas : les règles de bibliothèque, la portée globale du dédoublonnage et l'isolement des sous-processus n'ont jamais tourné. **Première vérification réelle à l'étape 24**, quand un run enfant réutilisera pour de bon les assets d'un parent d'une autre langue.

**Objection non résolue, laissée ouverte.** La divergence du § quota (objection 1) touche `CONFORMITE.md`, qui est figé depuis l'étape 1 et prime sur ce document. Elle est écrite ici et portée à `SUIVI.md` § 1 : **Thomas tranche** s'il faut amender `CONFORMITE.md` § 2 et son contrôle 27, ou laisser les deux textes cohabiter avec la règle « la plus stricte prime ».
