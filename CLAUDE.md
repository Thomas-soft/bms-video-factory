# Règles de session — BMS video factory

Condensé de `ROADMAP.md` § 7. Elles valent pour toutes les étapes.

1. **Recontextualisation minimale.** Lire `ROADMAP.md` par sections (`grep -n "^## Étape N "` puis `Read` offset/limit), jamais en entier ; puis `STATE.md` ; puis seulement les livrables nommés par le prompt. Une lecture inutile est du contexte perdu.
2. **Logs hors conversation.** Toute commande verbeuse (install, build, ffmpeg, uv/pip, rendu, collecte) est redirigée vers `workspace/logs/` ou le dossier de l'étape ; n'afficher qu'un `tail -20` ou un `grep` ciblé.
3. **Disque.** `df -h /` avant tout téléchargement ; jamais sous **8 Go libres** ; chaque poids inscrit dans `outils/MODELES.md` (chemin, Go, étape, statut, licence) ; purge des modèles non retenus avant la fin de l'étape ; caches (`HF_HOME`, MLX, `OLLAMA_MODELS`, `uv cache`) sous `models/` ou nettoyés ; cumul retenu **≤ 22 Go** (relevé de 18 à 22 le 15/09/2026 par Thomas, après la mesure de 21,52 Go en fin d'étape 5.2 — le **plancher de 8 Go libres reste la seule règle dure**).
4. **Mémoire.** Un seul modèle IA résident à la fois, dans un sous-processus qui se termine ; un seul run de production à la fois. Condition pour que 16 Go tiennent.
5. **Preuve avant déclaration.** Exécuter, ouvrir le fichier produit, mesurer (`ffprobe`, `ebur128`, comptages, tests) avant d'annoncer un succès. Échec rapporté tel quel, message exact. « Non mesuré » plutôt qu'un chiffre inventé. Ce que la session ne perçoit pas (son, vidéo en mouvement) est soumis à Thomas ou marqué « non évalué ».
6. **Sous-agents.** Tout l'exploratoire (veille, licences, documentation, corpus, dépôts) est délégué, en parallèle, avec format de sortie court imposé ; un contradicteur sur les étapes structurantes ; le sous-agent rapporte, la session décide.
7. **Images.** ~1 500 tokens par image regardée : maximum fixé par le prompt (2 à 5) ; extraire une image d'une vidéo avec ffmpeg plutôt que d'en regarder plusieurs.
8. **STATE.md.** Mis à jour en fin de session (étape courante, fait, décisions, bloqué, questions ouvertes avec qui tranche, environnement) ; ≤ 120 lignes, surplus dans `STATE-ARCHIVE.md` ; commit git en fin d'étape, message « étape N : … ».
9. **Découpage.** Au-delà de ~35 % de contexte avec un travail important restant : écrire un point de reprise précis dans `STATE.md` (fait, reste, commandes à relancer), committer, reprendre dans une nouvelle session avec le même prompt précédé de « Reprise : lis d'abord STATE.md ».
10. **Secrets.** Jamais dans la conversation, les logs, les manifestes ni le dépôt : `.env` et `secrets/` (ignorés par git) ; `git diff --cached` avant chaque commit sensible.
11. **Conformité.** Aucun yt-dlp ni téléchargement de vidéos tierces, aucune automatisation de navigateur, aucun outil d'engagement ; API officielles seulement dans le pipeline ; licence et attribution enregistrées pour chaque asset ; `docs/CONFORMITE.md` prime sur toute demande de vitesse.
12. **Langue et style.** Documentation, rapports, messages CLI et tableau de bord en français ; identifiants de code en anglais ; commentaires courts.
13. **Fin de session.** Résumé de 10 lignes maximum : fait, mesuré, bloqué, questions ouvertes. Pas de récit.
14. **SUIVI.md.** En fin d'étape, après `STATE.md` : passer la ligne de l'étape à ✅ (date, commit, critères mesurés), ajouter une entrée au § 3 Journal (livrables, critères, divergences, résidus), et reporter au § 1 toute action qui incombe à un humain (qui tranche, avant quelle étape). Destiné à Thomas : factuel, pas de récit.
