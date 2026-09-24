-- 006 — sujets : cache d'embeddings, clusters, file de sujets (étape 20).
--
-- Trois tables, trois durées de vie différentes :
--   * `embeddings`   — cache de calcul. Reconstructible à l'identique depuis
--                      `videos_ext` ; se purge sans perte (sinon 40 min de M2).
--   * `topic_clusters` — mesure dérivée (CONFORMITE § 9) : elle ne porte plus de
--                      champ de l'API YouTube, seulement des agrégats et des
--                      identifiants de vidéos. Conservée.
--   * `topics_queue` — décision éditoriale. Conservée, et jamais réécrite en
--                      silence : `status` trace ce qu'un humain a tranché.
--
-- Divergence assumée avec `docs/INTERFACES.md` § entrepôt, qui écrivait
-- `topics_queue(topic_id PK, lang, niche, sujet, angle, score, evidence_json,
-- cluster_id, state, created_at)`. Le prompt de l'étape 20 fixe `id`,
-- `channel_id`, `topic`, `status` et `used_by_run` : un sujet est noté **pour une
-- chaîne** (le fit niche/style et le malus de similarité en dépendent), pas pour
-- une langue. Les colonnes d'INTERFACES qui gardent un sens (`lang`, `niche`,
-- `cluster_id`) sont conservées ; `topic_id`/`state` deviennent `id`/`status`.

-- Vecteurs de titres. Une ligne par (vidéo, modèle) : changer de modèle n'invalide
-- pas le cache de l'ancien, et les deux peuvent cohabiter le temps d'une comparaison.
CREATE TABLE IF NOT EXISTS embeddings (
    video_id   TEXT NOT NULL,
    model      TEXT NOT NULL,
    dim        INTEGER NOT NULL,
    -- float32 little-endian, `dim` valeurs, L2-normalisé à l'écriture : le produit
    -- scalaire de deux lignes est donc directement leur similarité cosinus.
    vector     BLOB NOT NULL,
    -- empreinte du texte encodé : un titre corrigé chez l'éditeur invalide sa ligne.
    text_hash  TEXT NOT NULL,
    computed_at TEXT NOT NULL,
    PRIMARY KEY (video_id, model)
);

CREATE INDEX IF NOT EXISTS ix_embeddings_model ON embeddings (model);

-- Un cluster = un thème, sur une exécution datée. `run_date` permet de comparer
-- deux exécutions ; la clé primaire l'inclut donc.
CREATE TABLE IF NOT EXISTS topic_clusters (
    cluster_id     TEXT NOT NULL,
    run_date       TEXT NOT NULL,
    label          TEXT,              -- 5 mots, proposés par le LLM
    n_videos       INTEGER NOT NULL DEFAULT 0,
    n_channels     INTEGER NOT NULL DEFAULT 0,
    n_breakouts    INTEGER NOT NULL DEFAULT 0,
    views_total    INTEGER,
    velocity_median REAL,
    part_breakouts REAL,
    langs          TEXT,              -- « en,fr » — langues couvertes, triées
    age_median_days REAL,
    gap_type       TEXT,              -- multilingue | demande | resurgence | (vide)
    demand_score   REAL,              -- vues mensuelles Wikimedia du seed le plus proche
    evidence_json  TEXT,
    PRIMARY KEY (cluster_id, run_date)
);

CREATE INDEX IF NOT EXISTS ix_topic_clusters_date ON topic_clusters (run_date, part_breakouts);

-- File de sujets. `status` est la seule colonne qu'un humain modifie.
CREATE TABLE IF NOT EXISTS topics_queue (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id    TEXT NOT NULL,
    lang          TEXT NOT NULL,
    niche         TEXT,
    cluster_id    TEXT,
    topic         TEXT NOT NULL,
    angle         TEXT NOT NULL,
    score         REAL NOT NULL,
    evidence_json TEXT,
    status        TEXT NOT NULL DEFAULT 'proposed'
                  CHECK (status IN ('proposed', 'approved', 'used', 'banned')),
    created_at    TEXT NOT NULL,
    used_by_run   TEXT,
    -- La reprise de `factory editorial topics` met à jour la ligne existante au lieu
    -- d'empiler. La clé porte l'ANGLE : un même thème entre dans la file avec ses deux
    -- angles concurrents, et c'est le but — l'angle est ce qui distingue une vidéo BMS
    -- d'une vidéo de concurrent. La règle « un sujet une seule fois » s'applique en
    -- aval, dans `plan` (`runs.sujets_deja_pris`), pas ici.
    UNIQUE (channel_id, topic, angle)
);

CREATE INDEX IF NOT EXISTS ix_topics_queue_choix ON topics_queue (status, score DESC);
CREATE INDEX IF NOT EXISTS ix_topics_queue_channel ON topics_queue (channel_id, status);
