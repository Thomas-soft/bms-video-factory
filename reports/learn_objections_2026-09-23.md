Contradicteur du 23/09/2026 (12 objections). Aucune n'a pu être testée sur données réelles (n=0) ; chaque correction est couverte par un test synthétique quand elle est du code.

| # | Problème | Correction | Statut |
|---|---|---|---|
| 1 | La médiane de toutes les autres vidéos de la chaîne, futures comprises : une chaîne qui grandit fait gagner tout facteur adopté tard, et la boucle s'auto-renforce | Référence = médiane **glissante** de 5 vidéos avant et 5 après ; `publication_rank` en diagnostic ; **tous les poids gelés** si son effet rétréci dépasse 0,10 | appliqué (`tendance_max`, test `test_tendance_de_publication_gele_tout`) |
| 2 | Thompson : 10⁴ impressions d'une vidéo écrasent l'a priori de 200 ; `hash()` non rejouable | 300 impressions au plus par vidéo ; `zlib.crc32` | appliqué |
| 3 | Un niveau à ×0,7 n'est plus produit, donc jamais remesuré | Part plancher 1/(2K) par type de hook ; créneaux gelés (voir 6) | appliqué pour les hooks ; **non appliqué au tri des sujets** (un classement n'a pas de « part » : le plancher ×0,7 est le seul garde-fou) |
| 4 | ~60 niveaux avec P ≥ 0,8 : ~20 % de faux positifs par niveau ; variance plug-in trop étroite | `prob_min_action` 0,8 → **0,95** ; inflation de Morris (k−1)/(k−3) si k > 3 | appliqué |
| 5 | Niche, style, lang, voice_id, is_child ≈ 0 par construction une fois y centré par chaîne ; le repli sur la médiane de niche mesurait la niche | Ces 5 facteurs **gelés** ; vidéos à moins de 3 voisines **exclues** au lieu du repli | appliqué |
| 6 | J0 en UTC contre `perf_daily` en heure du Pacifique : une publication à 23 h UTC perd ~1 jour, ce qui fabrique un effet d'heure ; repli `strftime('%H')` en UTC | `days_pulled ≥ 7` exigé ; `publish_hour` et `publish_weekday` **gelés** | appliqué ; **résidu** : la vue `v_video_perf` (étape 25) garde J0 en UTC et le repli UTC — à corriger par migration |
| 7 | Le ratio de rythme se divise par une cible déjà ajustée : dérive | Division par la cible du **référentiel** de la niche | appliqué |
| 8 | y = None à 0 vue : les échecs disparaissent | y = log((v+1)/(ref+1)) | appliqué, testé |
| 9 | Les vidéos enfants dupliquent sujet, hook et titre du parent | Exclues (`is_child = 0`) | appliqué |
| 10 | Effets marginaux de hook et de cluster confondus avec la niche | Garde de n **par niche** pour `hook_type`, `topic_cluster`, `title_pattern` | appliqué (garde) ; estimation intra-niche non faite |
| 11 | `title_pattern` vient de `title_chosen`, que rien ne doit réécrire après publication ; `LIKE '%'||chosen||'.png'` ambigu dans la vue | Vérifié : seuls `thumbnail.py` et `seo.py` (avant upload) écrivent `title_chosen` ; la rotation J+7 ne réécrit jamais `thumbnail_chosen` | vérifié ; **résidu** : `LIKE` → égalité, à corriger dans la vue |
| 12 | Clés de tercile contenant les bornes, instables d'un run à l'autre | Clés `T1`/`T2`/`T3`, bornes publiées à part (`bounds`) | appliqué |
| — | Gel global | Aucun multiplicateur actif avant **n ≥ 30** vidéos à y calculable **et 3 chaînes à ≥ 5 vidéos** | appliqué, testé |
