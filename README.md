# BMS — usine de production de vidéos YouTube

Système de production de vidéos YouTube *faceless*, **entièrement local**, sans coût
récurrent et sans service en ligne payant. Il tourne sur un MacBook Air M2 de 16 Go.

De l'idée à la vidéo prête à publier, le pipeline enchaîne : recherche et choix du
sujet · écriture du script · voix off · sous-titres calés mot à mot · découpage en
plans · production des visuels · rendu · miniature · publication.

## Ce qu'on peut regarder en premier

| Où | Quoi |
|---|---|
| **`scripts-videos/`** | le texte intégral des deux vidéos de démonstration (FR et EN), avec le rôle éditorial de chaque segment, son horodatage réel dans la voix off et ses sources |
| **`benchmarks/preuve_motion/`** | **trois traitements de motion design rendus** sur le même texte et la même voix — typographie cinétique, schéma animé, hybride. Les MP4 sont dans le dossier ; les mesures dans `RESULTATS.md` |
| **`benchmarks/RESULTATS.md`** | ce que chaque brique coûte réellement sur cette machine : temps, mémoire, disque, qualité |
| **`docs/STYLES.md`** | les six styles visuels, ce qui est prouvé et ce qui ne l'est pas |
| **`docs/CONFORMITE.md`** | les règles que le système s'impose : API officielles seulement, aucune automatisation de navigateur, licence enregistrée pour chaque asset |
| **`ROADMAP.md`** | le plan complet, étape par étape |

## Les principes qui tiennent le projet

- **0 € de coût récurrent.** Modèles ouverts exécutés localement, aucune clé payante.
- **Preuve avant déclaration.** Rien n'est annoncé qui n'ait été exécuté et mesuré. Ce
  que la machine ne peut pas juger — le son, le mouvement en lecture — est marqué
  « non évalué » plutôt que noté à l'aveugle.
- **Conformité d'abord.** API officielles uniquement, aucun téléchargement de vidéos
  tierces, aucune automatisation de navigateur, aucun outil d'engagement.
- **Un seul modèle en mémoire à la fois.** C'est la condition pour que 16 Go suffisent.

## Techniquement

Python 3.12 (dépendances figées par `uv.lock`) · ffmpeg · modèles locaux via MLX et
llama.cpp pour le texte, la voix, la transcription et l'image · Revideo 0.11 + Chromium
headless pour le motion design · SQLite pour l'état et la bibliothèque d'assets.

Installation : `docs/INSTALL.md`. Architecture : `docs/ARCHITECTURE.md`.

---

*Ce dépôt public ne contient pas le cache de données de l'API YouTube utilisé par la
phase de recherche : les Developer Policies de YouTube (III.E.4) en limitent la
conservation à 30 jours, ce qu'un dépôt public ne permet pas de garantir. Seules les
mesures dérivées de ce cache — médianes, agrégats, comptages — sont publiées.*
