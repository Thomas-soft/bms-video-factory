# Script prompts — English

Each `##` section is a template sent to the local LLM. Values inside `{{ }}` are substituted by
`factory/steps/script.py`; they all come from `registre/REFERENTIEL.json`, `config/` or
`research.json`. **No numeric target is hard-coded here.**

## systeme

You are the editor-in-chief of a science explainer channel on YouTube. You write for the ear:
short sentences, one verb per idea, no unexplained jargon. You never invent a number: you may
only cite the facts provided. You answer with a valid JSON object only — no commentary, no text
before or after it.

## plan

Topic: "{{sujet}}"
Chosen editorial angle: {{angle}}
What this video adds that no source contains: {{elements_proprietaires}}
Persona: {{persona}}

Available facts (you may only cite these, by their id):
{{faits}}

Build the outline of the video in {{n_segments}} segments numbered 0 to {{dernier_segment}}.
Segment 0 is the hook; it is written separately, so give it only its on-screen text and its
visual intent.

Structural constraints, all checked by the program:
- Required roles, in order: {{roles}}
- `beat`: in 12 words or fewer, what the segment covers. Never two segments on the same beat.
- `on_screen_text`: the burned-in text, **6 words maximum**, upper case, readable on its own,
  no final punctuation. It is a visual hook, not a summary of the segment.
- `visual_intent`: one sentence describing what is on screen, **never naming a person**. Start
  with the object: "Close-up of…", "Diagram of…", "Aerial view of…", "Comparison between…".
  Forbidden: copying a framing instruction into the sentence, writing "a person who…", "a man",
  "a woman", "bust_only", "an illustration of the topic".
  {{cadrage}}
- `sources`: the list of fact ids this segment cites (`[]` if it cites none). Every segment with
  role `point` cites at least one.
- `open_loop`: `plant` when the segment promises an answer for later, `payoff` when it delivers
  that promise, `none` otherwise. The required positions are given in `roles`.

## hook

Topic: "{{sujet}}"
Angle: {{angle}}
Available facts:
{{faits}}

Write the hook of the video, of type **{{hook_type}}**.

Definition of this type: {{hook_definition}}
Checkable rules of this type, all mandatory:
{{hook_regles}}

Example measured in the corpus (registry, real channel — do not copy it, imitate its mechanics):
"{{hook_exemple}}"

Constraints:
- **{{hook_mots_max}} words maximum** for `text`. That is the measured median of the niche.
- The hook **plants an open loop**: it announces an answer that only comes later in the video.
  It does not give that answer away.
- No greeting, no channel introduction, no "in this video".
- `on_screen_text`: 6 words maximum, upper case, understandable with the sound off.
- `visual_intent`: one concrete sentence starting with the object shown, **no person on
  screen**. {{cadrage}}

## narration

Topic: "{{sujet}}" — angle: {{angle}}
Hook already written: "{{hook_text}}"
Open loop planted by the hook: it must be paid off in the segment marked `payoff`.

Available facts:
{{faits}}

Full outline of the video, so you know where you stand:
{{plan_resume}}

What has already been said, and what you must **not** say again:
{{deja_dit}}
Last sentence spoken before these segments: "{{phrase_precedente}}"

Now write the narration of the following segments, and of those only:
{{segments_a_ecrire}}

Constraints, checked by the program:
- Respect the **word count requested for each segment** (± 10 %). It is what sets the length of
  the video: {{mots_cibles}} words for {{duree_cible_s}} seconds at {{mots_par_minute}} words
  per minute.
- `narration` is the spoken text and nothing else: no stage directions, no headings, no segment
  numbers, no "welcome".
- Follow on from the previous segment: the first word must not repeat its last sentence.
- A `plant` segment ends on an explicit question or promise.
- A `payoff` segment answers, in its first sentence, the promise made earlier.
- A `point` segment cites at least one fact from the list, with its number when it has one.
- **A number is given once in the whole video.** If it has already been said, refer back to it
  without repeating it ("that volume", "the share we just saw") or move on to another fact. Two
  segments stating the same number is a disqualifying defect.
- Every segment adds information the previous ones did not.
- Write numbers the way they are spoken.

## correction

The script as written is {{mots_obtenus}} words against a target of {{mots_cibles}} words
({{ecart_pct}} % off, tolerance ± {{tolerance_pct}} %). It must therefore be {{sens}}.

Rewrite **only** the segments listed below, respecting their new word budget. Do not change the
outline, the roles, the open loops or the facts cited: only the development changes. To expand:
develop an example, spell out a mechanism, add a concrete consequence. To shorten: cut
repetitions and asides, never a fact.

Hook already written: "{{hook_text}}"
Available facts:
{{faits}}

Segments to rewrite:
{{segments_a_ecrire}}

## sponsor

The segment with role `sponsor` promotes: {{produit}}.
Its `narration` **starts** with this sentence, word for word, neither translated nor reworded:
"{{phrase_divulgation}}"
The rest of the segment presents the product with no promise of results and no superlatives.
