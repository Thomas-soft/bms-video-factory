# Méthode de mesure — étape 5.1 (texte et audio)

Machine : MacBook Air M2, 8 cœurs (4P + 4E), 16 Go de RAM unifiée, macOS 27.0.
Aucun GPU NVIDIA. Toutes les mesures de cette page ont été prises sur cette machine
le 15/09/2026, sur secteur, sans autre charge applicative.

## Protocole

- **Un outil = un processus.** `benchmarks/bench_audio.sh <étape>` lance
  `bench_audio.py` sous `/usr/bin/time -l` et relève le champ
  « maximum resident set size ». Le processus se termine avant le suivant :
  jamais deux modèles résidents (`CLAUDE.md` § 4).
- **Pic mémoire** = maximum resident set size du processus, en Go (÷ 2³⁰).
  Il inclut le chargement du modèle et l'inférence, pas le système.
- **Débit LLM** : lu dans la ligne de statut de `llama-cli`
  (`[ Prompt: … t/s | Generation: … t/s ]`). Cette ligne est **rafraîchie en continu
  par retour chariot** : la valeur retenue est la **dernière** occurrence de la
  sortie capturée. La première vaut ~0,8 t/s — elle mesure le tout premier token et
  n'a aucun sens comme débit. Une première passe du banc lisait la première
  occurrence et rapportait 0,8 tok/s en anglais ; elle a été jetée
  (`results_audio_v1.jsonl`, conservé comme trace) et la mesure refaite.
- **Facteur temps réel (RTF)** = temps de calcul ÷ durée de l'audio.
  RTF < 1 : plus rapide que le temps réel. C'est la convention de `SELECTION.md`
  (« retenu si ≤ 1,0 »), l'inverse de la formule du prompt d'étape.
- **WER** : distance de Levenshtein sur les mots ÷ nombre de mots de la référence.
  Normalisation : minuscules, accents retirés, ponctuation retirée, espaces
  normalisés (`bench_audio.py:normalise`). Implémentation locale, sans `jiwer`,
  pour que la normalisation soit lisible et identique pour tous les outils.

## Échantillon standard

- **LLM** : prompt fixe, contexte 8 192, `--temp 0.7 --seed 42`, raisonnement
  désactivé (`-rea off` — on mesure l'écriture, pas la chaîne de pensée).
  Sujet : premier sujet porteur de `science_pop` dans `registre/REFERENTIEL.json`
  (« What Happens Every Day When You Quit Sugar For 30 Days », 6 672 913 vues,
  @healthsnippet, ratio 2070× la médiane de la chaîne).
- **TTS et ASR** : un paragraphe unique de 126 mots, écrit en français
  (`samples/audio/texte_fr.txt`), traduit en EN, ES et IT **par le LLM mesuré
  juste avant**, pas par la session. Les quatre textes sont conservés.

## Écart assumé avec l'ordre de `SELECTION.md`

`SELECTION.md` § Ordre de mesure classe le LLM en 3ᵉ position, après l'ASR et le TTS,
pour garder le disque libre le plus longtemps possible. **Le LLM a été mesuré en
premier** : c'est lui qui produit les traductions EN/ES/IT dont le TTS a besoin, et
la mesure du TTS en dépend donc directement. Le motif de l'ordre d'origine — la
pression sur le disque — ne s'applique pas : 46 Gi étaient libres au départ, contre
25 Gi exigés par le pré-requis de l'étape. L'ordre ASR → TTS est conservé pour la
suite, puisque l'ASR sert d'instrument de mesure au TTS.

## Choix de la configuration TTS — trois mesures avant d'en retenir une

Le premier lancement du TTS a tourné **plus de dix minutes sur une seule synthèse de
126 mots**, à 98 % d'un cœur, sans que la mémoire résidente dépasse 0,12 Go — le
signe que le calcul ne passait pas par le GPU. Plutôt que de laisser tourner des
cycles de dix minutes, la configuration a été arbitrée sur une **sonde d'une phrase**
(~5 s d'audio), trois fois :

| Configuration | Chargement | Génération | Audio produit | Facteur temps réel |
|---|---|---|---|---|
| float16 / MPS | 11,7 s | 23,5 s | 5,0 s | **4,73** |
| bfloat16 / MPS | 9,3 s | 23,0 s | 4,6 s | 5,05 |
| float32 / CPU | 12,3 s | 30,4 s | 5,1 s | 5,94 |

**float16 sur MPS est retenu**, et c'est cette configuration qui produit les huit
échantillons. `attn_implementation="eager"` est imposé : `flash_attention_2` n'existe
pas sur Metal, le paquet l'annonce lui-même au chargement. `dtype=float32` — la
valeur du premier jet, reprise d'un réflexe Chatterbox — était le plus mauvais des
trois choix.

Aucune des trois ne tient le seuil de `SELECTION.md` § 2 (facteur temps réel ≤ 1,0).
C'est une mesure, pas une estimation, et elle est consignée telle quelle.

## Ce que la session ne mesure pas

La **qualité perçue de la voix** (naturel, accent) n'est pas mesurable par la
session : elle n'entend pas les fichiers produits (`CLAUDE.md` § 5). Elle est
soumise à Thomas, voix par voix, et reste « non évaluée » tant qu'il n'a pas écouté.
Le WER en tient lieu d'**indicateur d'intelligibilité**, pas de note de qualité :
une voix au fort accent étranger peut très bien obtenir un WER bas.
