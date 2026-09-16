# Brique 7 — musique et SFX : ce que 5.1 peut mesurer, et ce qu'elle ne peut pas

## Verdict de l'étape : génération musicale locale abandonnée, banques confirmées

**ACE-Step — « non mesuré : disque », et cette fois sans conditionnel.**
`SELECTION.md` annonçait 2,39 Go et conditionnait l'installation à une marge de
2,4 Go. La vérification du dépôt réel donne un tout autre chiffre.

| Source | Poids annoncé | Poids réel |
|---|---|---|
| `SELECTION.md` § 7 et `MODELES.md` | 2,39 Go | — |
| Dépôt `ACE-Step/Ace-Step1.5` (Hugging Face) | — | **~10,1 Go** (embedding 1,19 + LM 3,71 + turbo 4,79 + VAE 0,34) |
| Variante XL | « ~9 Go » | **~19,95 Go** |

Deux erreurs se cumulaient : le nom du dépôt (`ACE-Step-1.5` n'existe pas ; la casse
réelle est `Ace-Step1.5`) et le poids, sous-évalué d'un facteur 4. À 10,1 Go, le
modèle ne rentre pas dans la marge de 1,53 Go du budget de 18 Go, et il ne rentrerait
pas davantage si le LLM basculait sur Qwen3.5-4B (−3,47 Go). **La condition posée par
`SELECTION.md` n'est pas approchable : la question ne se rouvre pas en 5.1.**
Ce n'est pas un no-go de performance — aucune mesure n'a été prise — mais un no-go de
budget disque.

## Ce qui reste : les banques, à 0 Go

**Principal — YouTube Audio Library.** Pas d'API : le téléchargement se fait depuis
le Studio de la chaîne qui publiera (Studio → Bibliothèque audio → Musique). C'est
justement ce qui fonde la garantie Content ID, qui est la raison du choix.
**Conséquence pour l'étape : l'inventaire « ≥ 5 pistes distinctes par niche » ne peut
pas être fait par la session** — il exige une session Studio authentifiée, donc un
compte Google de chaîne, qui est la question ouverte n° 1 de `SUIVI.md` (→ Alek).
Automatiser cette navigation est exclu (`docs/CONFORMITE.md` § 9).

**Principal complémentaire — Pixabay Music**, accessible par la même clé d'API que
les images, Pixabay Content License, commercial, sans attribution. C'est la source
qui *peut* être inventoriée programmatiquement, et elle le sera à l'étape qui crée le
client d'API des banques, pas ici.

**Repli — Incompetech (CC-BY 4.0)**, crédit mot pour mot déjà figé dans
`outils/LICENCES.md`.

## Ce que cela change pour la suite

1. Le seuil « ≥ 5 pistes distinctes par niche » de `SELECTION.md` § Ordre de mesure
   **reste à vérifier**, et il ne relève pas d'une mesure machine : il relève de
   l'ouverture des comptes de chaîne. Reporté à l'étape 14, tracé dans `STATE.md`.
2. La marge de 1,53 Go du budget disque n'est plus grevée par ACE-Step. Elle est en
   revanche entamée par les poids réels de l'ASR et du TTS, bien supérieurs aux
   annonces — voir `RESULTATS.md` § 1 et le budget corrigé dans `MODELES.md`.
3. La réserve sur Freesound (écarté à l'étape 4, « à rouvrir seulement si 5.1 montre
   que les SFX manquent ») **n'est pas levée et n'est pas activée** : 5.1 n'a pas pu
   inventorier les SFX disponibles. Le déclencheur reste armé pour plus tard.
