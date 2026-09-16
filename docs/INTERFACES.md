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
| `segments[].interrupt` | objet \| null | rupture de rythme programmée : `{type: question\|chiffre\|silence\|changement_de_plan, at_s_relative}` |
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
| `variants[].contrast_ratio` | WCAG, **cible ≥ 4,5** |
| `variants[].text_area_ratio` | surface de texte ÷ surface totale |
| `variants[].legible_at_320px` | bool, lisibilité à petite taille |
| `variants[].phash` | empreinte perceptuelle → `dedupe_hash.thumbnail_phash` |
| `chosen` | nom de la variante retenue |
| `chosen_reason` | `score` \| `manuel` \| `dedupe_conflict` |

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
| `title_variants[]` | liste | `{text, pattern, length_char, score}` — patrons de la niche, ≤ `titres.plafond_recommande`, plafond dur YouTube 100 |
| `title_chosen` | str | |
| `description` | str | **ordre imposé** : ligne de divulgation (§ 3 couche 3) → accroche → chapitres → liens d'affiliation → bloc d'attribution des assets → crédit musical |
| `description_blocks` | objet | `{disclosure, hook, chapters[], affiliate[], attribution[], music_credit}` — la description est **composée**, jamais écrite à la main |
| `tags[]` | liste[str] | ≤ 500 caractères cumulés |
| `hashtags[]` | liste[str] | ≤ 3 affichés au-dessus du titre ; exigés par l'étape 21 |
| `localizations` | objet | `{<lang>: {title, description}}` — versions localisées de la fiche, étapes 21 et 24 |
| `pinned_comment` | str \| null | commentaire épinglé (appel à l'action et lien d'affiliation), étape 27. **Soumis aux mêmes divulgations que la description** |
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

**Le plafond de 6 de `CONFORMITE.md` § 2 ne tient pas si la vidéo est complète.** Une publication coûte `videos.insert` 1 600 + `thumbnails.set` 50 + `captions.insert` 400 = **2 050 unités**. Six publications font **12 300 unités pour un quota de 10 000** : la 5ᵉ épuise déjà le quota de lecture du registre. Le plafond de 6 de `CONFORMITE.md` § 2 et le contrôle 27 de sa § 11 ne comptent que les `videos.insert` et supposent 1 600 unités par vidéo. **Règle retenue, la plus stricte des deux** (`CONFORMITE.md`, principe de conflit de normes) : **4 publications complètes par jour**, et la décision se prend sur le **solde réel** lu dans `quota_ledger`, jamais sur un compteur de vidéos. Divergence à porter dans `CONFORMITE.md` § 2 et § 11 à la prochaine révision — elle n'est pas tranchée ici.

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
review_log(review_hash PK, video_id, channel_id, reviewer, review_date, decision, batch_id)

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
topics_queue(topic_id PK, lang, niche, sujet, angle, score, evidence_json, cluster_id,
             state, created_at)

-- 004 (étape 23.1) : publication et quota
publications(video_id PK, channel_id, youtube_video_id, status, publish_at, uploaded_at,
             thumbnail_set, captions_set, playlist_added, units_used)
             -- status : published_private | scheduled | public | failed
quota_ledger(day, gcp_project, call, units, video_id, at)
reporting_jobs(job_id PK, channel_id, report_type, created_at, state)

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
| `editorial topics` | `[--lang] [--niche]` | `topics_queue` |
| `analytics pull` | `[--channel] [--since]` | `perf_daily`, `perf_traffic`, `perf_reach`, `perf_window`, `retention_curves`, `analytics_runs` ; rétro-remplit `published_at` ; recopie dans `manifest.resultats` |
| `analytics show` | `<run>` \| `--channel <id>` | rien ; lecture |
| `learn` | `[--min-n 12]` | `learned/weights.json` |
| `economics` | `[--by niche\|lang\|channel\|style]` | rapport de coût et de revenu par vidéo |
| `library` | `list` \| `add` \| `promote <run> <shot>` \| `prune` | `workspace/library/**`, `library_assets` |
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
