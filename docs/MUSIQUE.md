# Déposer les pistes musicales — mode d'emploi

> État au 16/09/2026 : `workspace/library/music/` est **vide**. Le run FR est monté avec un lit
> silencieux, `manifest.decisions.music_track` est vide, et la publication est donc bloquée par
> `CONFORMITE.md` § 10.1 (contrôle 8). Ce document dit ce qu'il faut déposer pour lever ce blocage.
> C'est un geste humain : il n'existe **aucune** voie automatique conforme (voir § 3).

## 1. Où les prendre

**YouTube Studio de la chaîne qui publiera la vidéo** → menu de gauche → **Bibliothèque audio**
→ onglet **Musique**.

La licence est attachée au **contexte de téléchargement** (`CONFORMITE.md` § 7) : une piste prise
depuis le Studio d'une autre chaîne, ou depuis un miroir tiers, ne couvre pas la chaîne qui
publie. Tant que les comptes des chaînes n'existent pas (question ouverte pour Alek), prendre les
pistes depuis le **compte de test** et écrire son identifiant dans `telechargee_depuis` — la
piste devra être retéléchargée depuis le Studio de la vraie chaîne avant la première publication.

Filtres à appliquer, dans cet ordre :

1. **Attribution** → « Attribution non requise » pour quatre pistes. Rien à écrire en description,
   rien à oublier.
2. Une **cinquième** piste sous licence Creative Commons, avec **« Attribution requise »** :
   elle sert à exercer la chaîne de crédit automatique de bout en bout (le crédit est recopié en
   description par l'étape 13.2). Copier le texte de crédit **exactement** tel que le Studio le
   propose.
3. **Durée > 2 min** : le lit se boucle proprement, mais une piste de 40 s bouclée dix-huit fois
   s'entend.
4. **Sans voix** (« Instrumental ») : une voix sous la voix off est illisible.

## 2. Ce qu'il faut déposer

Cinq pistes, **cinq ambiances différentes**, dans `workspace/library/music/` :

| Ambiance (`mood`) | Pour quelles niches |
|---|---|
| `calme` | `spiritualite`, `niche_monetisable_longevite` |
| `tension` | `true_crime`, `niche_monetisable_paris_sportifs` |
| `curieux` | `science_pop` ← **la niche du run FR et du run EN** |
| `energique` | `home_hacks`, `niche_monetisable_complements_fr` |
| `sombre` | `histoire_doc` |

Chaque piste est un **couple** : le fichier audio et son manifeste de licence, même nom de base.

```
workspace/library/music/
  calme_slow_drift.mp3
  calme_slow_drift.json
  curieux_paper_planes.mp3
  curieux_paper_planes.json
  …
```

Un fichier audio **sans** son `.json` est refusé au chargement, nommément, et n'entre dans aucune
vidéo. C'est voulu : une piste sans licence est le seul défaut de cette étape qui se paie en
réclamation Content ID.

### Le manifeste `<slug>.json`

```json
{
  "titre": "Slow Drift",
  "artiste": "Nom exact affiché par le Studio",
  "source": "youtube_audio_library",
  "licence": "CC0",
  "licence_url": "https://support.google.com/youtube/answer/3376882",
  "attribution_requise": false,
  "credit_line": null,
  "mood": "calme",
  "bpm": 78,
  "telechargee_depuis": "bms-science-fr"
}
```

| Champ | Règle |
|---|---|
| `licence` | Tel qu'affiché. **`NC`, `ND` et « sampling » sont refusés** par le code, pas seulement par la documentation |
| `attribution_requise` | `true` pour la piste CC : alors `credit_line` est **obligatoire**, sinon la piste est rejetée |
| `credit_line` | Le texte de crédit **exact** proposé par le Studio, recopié tel quel en description |
| `mood` | Une des cinq valeurs ci-dessus, et rien d'autre |
| `bpm` | Approximatif, informatif ; sert au choix futur, pas au montage |
| `telechargee_depuis` | Identifiant de la chaîne **depuis laquelle** la piste a été téléchargée |

## 3. Pourquoi il n'y a pas d'alternative automatique

- **Freesound est écarté depuis le 15/09/2026** : les CGU de son API ne couvrent pas l'usage
  commercial, quelle que soit la licence du son téléchargé. Le prompt de l'étape 13.1 le
  proposait en repli ; ce repli n'existe plus.
- **L'automatisation du navigateur est exclue** (`CONFORMITE.md`, ToS YouTube) : la bibliothèque
  audio n'a pas d'API, donc le téléchargement reste un geste manuel.
- **La génération musicale locale** est conditionnée à une licence de **poids** commerciale
  (ACE-Step 1.5, Apache-2.0, est le seul candidat retenu ; MusicGen et YuE sont éliminés en
  CC-BY-NC). Non évalué à ce jour, et hors périmètre de l'étape 13.1.

## 4. Vérifier le dépôt

```bash
.venv/bin/python -c "
from factory.assets import music
pistes, refus = music.charger_bibliotheque()
print(f'{len(pistes)} piste(s) valide(s) :', [(p.slug, p.mood, p.licence) for p in pistes])
for r in refus: print('REFUS :', r)
"
```

Puis relancer le montage : `factory assemble --run <id>` choisit la piste du mood de la niche,
l'écarte des cinq derniers runs de la chaîne, la boucle ou la coupe à la durée de la vidéo avec
fondus, la ducke à -18 dB sous la voix, et inscrit sa licence au manifeste.
