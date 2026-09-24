-- 004 — entrepôt concurrentiel : chaînes suivies, vidéos, instantanés quotidiens.
--
-- Numérotée 004 et non 002 (le prompt de l'étape 18 disait « 002_editorial.sql ») :
-- 002_library.sql et 003_qc.sql existent déjà. Les noms de tables, eux, sont ceux
-- que fixe ARCHITECTURE.md § 9 et ne changent pas.
--
-- Conservation (CONFORMITE.md § 9, Developer Policies III.E.4) : tout ce qui vient
-- de l'API porte fetched_at et se purge ou se rafraîchit à 30 jours. Les mesures
-- dérivées (video_metrics) ne sont plus des données API et se conservent.

-- Chaînes suivies. source : registre (importée de registre/chaines.csv) | ajout (CLI).
CREATE TABLE IF NOT EXISTS channels_watch (
    channel_id          TEXT PRIMARY KEY,
    handle              TEXT,
    title               TEXT,
    niche               TEXT,
    lang                TEXT,
    source              TEXT NOT NULL DEFAULT 'ajout',
    active              INTEGER NOT NULL DEFAULT 1,
    added_at            TEXT NOT NULL,
    uploads_playlist_id TEXT,
    -- état de collecte, hors données API : sert la reprise, pas l'analyse
    last_collect_date   TEXT,
    backfilled          INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS ix_channels_watch_actives ON channels_watch (active, niche);

-- Métadonnées de vidéos tierces. Données API : rafraîchies (last_seen_at) ou purgées.
CREATE TABLE IF NOT EXISTS videos_ext (
    video_id         TEXT PRIMARY KEY,
    channel_id       TEXT NOT NULL,
    published_at     TEXT,
    title            TEXT,
    description_head TEXT,
    duration_s       INTEGER,
    tags_json        TEXT,
    category_id      TEXT,
    thumbnail_url    TEXT,
    first_seen_at    TEXT NOT NULL,
    last_seen_at     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_videos_ext_channel_pub ON videos_ext (channel_id, published_at);

-- Instantanés quotidiens. La clé primaire (video_id, snapshot_date) EST l'index
-- demandé sur ce couple ; un second index identique ne ferait que peser.
CREATE TABLE IF NOT EXISTS video_snapshots (
    video_id      TEXT NOT NULL,
    snapshot_date TEXT NOT NULL,
    views         INTEGER,
    likes         INTEGER,
    comments      INTEGER,
    fetched_at    TEXT NOT NULL,
    PRIMARY KEY (video_id, snapshot_date)
);

-- Parcours par date : c'est celui de la purge à 30 jours.
CREATE INDEX IF NOT EXISTS ix_video_snapshots_date ON video_snapshots (snapshot_date);

CREATE TABLE IF NOT EXISTS channel_snapshots (
    channel_id    TEXT NOT NULL,
    snapshot_date TEXT NOT NULL,
    subscribers   INTEGER,
    views         INTEGER,
    video_count   INTEGER,
    fetched_at    TEXT NOT NULL,
    PRIMARY KEY (channel_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS ix_channel_snapshots_date ON channel_snapshots (snapshot_date);

-- Un run de collecte. id auto : --force rejoue une collecte le même jour, et les
-- deux lignes doivent rester lisibles côte à côte.
CREATE TABLE IF NOT EXISTS collect_runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    date          TEXT NOT NULL,
    started_at    TEXT NOT NULL,
    finished_at   TEXT,
    mode          TEXT NOT NULL DEFAULT 'normal',
    units_used    INTEGER NOT NULL DEFAULT 0,
    channels_done INTEGER NOT NULL DEFAULT 0,
    videos_new    INTEGER NOT NULL DEFAULT 0,
    snapshots_new INTEGER NOT NULL DEFAULT 0,
    errors        INTEGER NOT NULL DEFAULT 0,
    note          TEXT
);

CREATE INDEX IF NOT EXISTS ix_collect_runs_date ON collect_runs (date);

-- Mesures dérivées, conservées sans limite de durée : elles ne portent plus de
-- donnée API (CONFORMITE.md § 9). Consolidées par `factory editorial purge` avant
-- la suppression des instantanés bruts de plus de 30 jours.
CREATE TABLE IF NOT EXISTS video_metrics (
    video_id      TEXT PRIMARY KEY,
    channel_id    TEXT NOT NULL,
    published_at  TEXT,
    views_d1      REAL,
    views_d7      REAL,
    views_d30     REAL,
    velocity_7d   REAL,
    velocity_life REAL,
    ratio_niche   REAL,
    n_snapshots   INTEGER NOT NULL DEFAULT 0,
    computed_at   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_video_metrics_channel ON video_metrics (channel_id);

-- ------------------------------------------------------------------ vues SQL

-- Âge exact d'un instantané : julianday(fetched_at) − julianday(published_at).
-- L'heure compte : la tâche tourne entre 03:00 et 05:00 locales, et une vidéo
-- publiée l'après-midi aurait un âge négatif si l'on datait l'instantané à minuit.
DROP VIEW IF EXISTS v_snapshot_age;
CREATE VIEW v_snapshot_age AS
SELECT s.video_id,
       v.channel_id,
       s.snapshot_date,
       s.views,
       s.likes,
       s.comments,
       v.published_at,
       julianday(s.fetched_at) - julianday(v.published_at) AS age_days
FROM video_snapshots s
JOIN videos_ext v ON v.video_id = s.video_id
WHERE v.published_at IS NOT NULL;

-- Vues à un âge cible, par interpolation linéaire entre les deux instantanés qui
-- l'encadrent. Sans encadrement (un seul instantané, ou tous du même côté), NULL :
-- une extrapolation serait un chiffre inventé.
DROP VIEW IF EXISTS v_video_views_at;
CREATE VIEW v_video_views_at AS
WITH cibles(age_cible) AS (VALUES (1.0), (7.0), (30.0)),
bornes AS (
    SELECT ve.video_id,
           c.age_cible,
           (SELECT s.age_days FROM v_snapshot_age s
             WHERE s.video_id = ve.video_id AND s.age_days <= c.age_cible
             ORDER BY s.age_days DESC LIMIT 1) AS lo_age,
           (SELECT s.views FROM v_snapshot_age s
             WHERE s.video_id = ve.video_id AND s.age_days <= c.age_cible
             ORDER BY s.age_days DESC LIMIT 1) AS lo_views,
           (SELECT s.age_days FROM v_snapshot_age s
             WHERE s.video_id = ve.video_id AND s.age_days >= c.age_cible
             ORDER BY s.age_days ASC LIMIT 1) AS hi_age,
           (SELECT s.views FROM v_snapshot_age s
             WHERE s.video_id = ve.video_id AND s.age_days >= c.age_cible
             ORDER BY s.age_days ASC LIMIT 1) AS hi_views
    FROM videos_ext ve
    CROSS JOIN cibles c
)
SELECT video_id,
       age_cible,
       CASE
           WHEN lo_age IS NULL OR hi_age IS NULL THEN NULL
           WHEN hi_age <= lo_age THEN lo_views
           ELSE lo_views + (hi_views - lo_views) * (age_cible - lo_age) / (hi_age - lo_age)
       END AS views
FROM bornes;

-- Δvues / Δjours sur la fenêtre des 7 derniers jours : premier et dernier
-- instantané de cette fenêtre. NULL tant qu'il n'y a qu'un seul jour en base —
-- c'est le cas au lendemain de la première collecte, et ce n'est pas un défaut.
DROP VIEW IF EXISTS v_velocity_7d;
CREATE VIEW v_velocity_7d AS
SELECT video_id,
       CASE WHEN (fin_age - debut_age) > 0
            THEN (fin_views - debut_views) / (fin_age - debut_age)
       END AS velocity_7d,
       n_points
FROM (
    SELECT s.video_id,
           MIN(s.age_days) AS debut_age,
           MAX(s.age_days) AS fin_age,
           COUNT(*) AS n_points,
           (SELECT t.views FROM v_snapshot_age t
             WHERE t.video_id = s.video_id
               AND julianday(t.snapshot_date) >= julianday('now', '-7 days')
             ORDER BY t.age_days ASC LIMIT 1) AS debut_views,
           (SELECT t.views FROM v_snapshot_age t
             WHERE t.video_id = s.video_id
               AND julianday(t.snapshot_date) >= julianday('now', '-7 days')
             ORDER BY t.age_days DESC LIMIT 1) AS fin_views
    FROM v_snapshot_age s
    WHERE julianday(s.snapshot_date) >= julianday('now', '-7 days')
    GROUP BY s.video_id
);

-- Vue de tête de l'étape 18. « velocity » est la vélocité à 7 jours quand deux
-- jours au moins sont en base, sinon la vitesse moyenne depuis la publication
-- (vues / âge) ; `velocity_source` dit laquelle, et rien n'est mélangé en silence.
-- « ratio » compare la vidéo à la médiane de sa chaîne dans la même tranche d'âge.
DROP VIEW IF EXISTS v_video_velocity;
CREATE VIEW v_video_velocity AS
WITH dernier AS (
    SELECT video_id,
           channel_id,
           published_at,
           age_days,
           views,
           likes,
           comments,
           ROW_NUMBER() OVER (PARTITION BY video_id ORDER BY age_days DESC) AS rang
    FROM v_snapshot_age
),
base AS (
    SELECT d.video_id,
           d.channel_id,
           d.published_at,
           d.age_days,
           d.views,
           d.likes,
           d.comments,
           v7.velocity_7d,
           CASE WHEN d.age_days > 0 THEN d.views / d.age_days END AS velocity_life,
           (SELECT views FROM v_video_views_at w
             WHERE w.video_id = d.video_id AND w.age_cible = 1.0) AS views_d1,
           (SELECT views FROM v_video_views_at w
             WHERE w.video_id = d.video_id AND w.age_cible = 7.0) AS views_d7,
           (SELECT views FROM v_video_views_at w
             WHERE w.video_id = d.video_id AND w.age_cible = 30.0) AS views_d30,
           CASE
               WHEN d.age_days < 7 THEN '0-7'
               WHEN d.age_days < 30 THEN '7-30'
               WHEN d.age_days < 90 THEN '30-90'
               WHEN d.age_days < 365 THEN '90-365'
               ELSE '365+'
           END AS age_bucket
    FROM dernier d
    LEFT JOIN v_velocity_7d v7 ON v7.video_id = d.video_id
    WHERE d.rang = 1
),
retenue AS (
    SELECT *, COALESCE(velocity_7d, velocity_life) AS velocity,
           CASE WHEN velocity_7d IS NOT NULL THEN '7d' ELSE 'life' END AS velocity_source
    FROM base
),
-- Médiane par (chaîne, tranche d'âge) : SQLite n'a pas de median(), donc rang
-- central — moyenne des deux valeurs centrales quand l'effectif est pair.
classe AS (
    SELECT channel_id, age_bucket, velocity,
           ROW_NUMBER() OVER (PARTITION BY channel_id, age_bucket ORDER BY velocity) AS rn,
           COUNT(*) OVER (PARTITION BY channel_id, age_bucket) AS n
    FROM retenue
    WHERE velocity IS NOT NULL
),
mediane AS (
    SELECT channel_id, age_bucket, AVG(velocity) AS med
    FROM classe
    WHERE rn IN ((n + 1) / 2, (n + 2) / 2)
    GROUP BY channel_id, age_bucket
)
SELECT r.video_id,
       r.channel_id,
       cw.title AS channel_title,
       cw.niche,
       cw.lang,
       ve.title,
       r.published_at,
       r.age_days,
       r.age_bucket,
       r.views,
       r.likes,
       r.comments,
       r.views_d1,
       r.views_d7,
       r.views_d30,
       r.velocity_7d,
       r.velocity_life,
       r.velocity,
       r.velocity_source,
       m.med AS velocity_median_channel,
       CASE WHEN m.med > 0 THEN r.velocity / m.med END AS ratio
FROM retenue r
JOIN videos_ext ve ON ve.video_id = r.video_id
LEFT JOIN channels_watch cw ON cw.channel_id = r.channel_id
LEFT JOIN mediane m ON m.channel_id = r.channel_id AND m.age_bucket = r.age_bucket;
