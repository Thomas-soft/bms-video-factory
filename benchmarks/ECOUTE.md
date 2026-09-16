# À écouter — notation des voix de synthèse (Thomas)

**Pourquoi c'est toi qui notes.** La session ne peut pas entendre les fichiers
(`CLAUDE.md` § 5). Le WER qu'elle mesure dit si une voix est *intelligible par une
machine*, pas si elle est *écoutable par un humain* : une voix au fort accent chinois
parlant français peut très bien obtenir un WER bas. **Aucune note de ce tableau n'est
remplie par la session.**

**Ce qui dépend de ta note.** Le seuil de `outils/SELECTION.md` § 2 :
**≥ 3,5/5 en français** → Qwen3-TTS est retenu. **< 3,5** → on bascule sur Chatterbox
Multilingual et son filigrane PerTh (que tu as déjà accepté le 15/09).

**Le contexte à garder en tête en écoutant.** Aucun des 9 locuteurs préréglés de
Qwen3-TTS n'est natif français, espagnol ou italien : il y a 5 voix chinoises, 2
anglaises, 1 japonaise, 1 coréenne. Les huit fichiers ci-dessous sont donc tous en
mode *cross-lingual* — une voix anglophone (Ryan) et une voix sinophone (Serena) à
qui on demande de parler les quatre langues. C'est exactement la conséquence de ta
décision du 15/09 de ne pas cloner de voix, et c'est ce que l'étape devait mesurer.

## Grille

Deux notes par fichier, de 1 à 5. **Naturel** : est-ce que ça sonne comme une personne
qui parle, ou comme une machine ? **Accent** : est-ce que la prononciation est celle
d'un locuteur de cette langue, ou est-ce qu'on entend une langue étrangère par-dessus ?

| Fichier | Langue | Voix | Naturel /5 | Accent /5 | Remarque |
|---|---|---|---|---|---|
| `qwen3tts_fr_Ryan.wav` | FR | Ryan (anglophone) | | | |
| `qwen3tts_fr_Serena.wav` | FR | Serena (sinophone) | | | |
| `qwen3tts_en_Ryan.wav` | EN | Ryan (natif) | | | |
| `qwen3tts_en_Serena.wav` | EN | Serena (sinophone) | | | |
| `qwen3tts_es_Ryan.wav` | ES | Ryan (anglophone) | | | |
| `qwen3tts_es_Serena.wav` | ES | Serena (sinophone) | | | |
| `qwen3tts_it_Ryan.wav` | IT | Ryan (anglophone) | | | |
| `qwen3tts_it_Serena.wav` | IT | Serena (sinophone) | | | |

Tous dans `benchmarks/samples/audio/` (hors git, voir `.gitignore`).
Le texte lu est le même partout, traduit : `texte_fr.txt`, `texte_en.txt`,
`texte_es.txt`, `texte_it.txt` dans le même dossier.

## Deux questions en plus des notes

1. **Les deux voix d'une même langue sont-elles distinguables à l'oreille ?**
   C'est le second seuil de `SELECTION.md` § 2 : « ≥ 2 timbres distincts par langue,
   sans clonage ». Si Ryan et Serena sonnent pareil en français, l'exigence « 2 voix
   par langue » tombe — et ce n'est alors plus un arbitrage technique mais un
   **arbitrage produit à remonter à Alek**, pas un problème à contourner.
2. **La voix française est-elle diffusable en l'état sur une chaîne monétisée ?**
   Oui / non, sans demi-mesure. C'est le risque n° 5 du projet.
