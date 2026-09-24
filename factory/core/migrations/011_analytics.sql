-- 011 — performances des vidéos publiées, jointes au manifeste (étape 25).
--
-- **Numéro.** Le prompt de l'étape nomme `005_analytics.sql` ; le 005 est pris depuis
-- l'étape 19 (`005_niches.sql`) et `schema_migrations.version` est une clé primaire. Même
-- divergence que 009 : les tables sont celles du prompt, seul le numéro change.
--
-- **Clés.** `video_id` est toujours l'identifiant de run de l'usine (`runs.video_id`), jamais
-- l'identifiant YouTube : c'est lui que porte le manifeste. La correspondance passe par
-- `publications.youtube_video_id`. Une vidéo de la chaîne que l'usine n'a pas produite n'a
-- pas de run : elle n'est pas chargée (comptée dans `analytics_runs.skipped`).
--
-- **Dates.** `date` est le jour des rapports YouTube, en heure du Pacifique (fuseau des
-- deux API) ; il n'est jamais converti. Les lignes des 5 derniers jours sont réécrites à
-- chaque passage (latence jusqu'à 72 h) : `pulled_at` dit quand la valeur a été lue.

CREATE TABLE IF NOT EXISTS perf_daily (
    video_id            TEXT NOT NULL,
    youtube_video_id    TEXT NOT NULL,
    channel_id          TEXT NOT NULL,
    date                TEXT NOT NULL,
    views               INTEGER,
    minutes_watched     REAL,
    avg_view_duration_s REAL,
    avg_view_pct        REAL,
    subs_gained         INTEGER,
    likes               INTEGER,
    shares              INTEGER,
    comments            INTEGER,
    -- NULL si l'API refuse la métrique (elle est récente) : jamais 0 par défaut.
    engaged_views       INTEGER,
    pulled_at           TEXT NOT NULL,
    PRIMARY KEY (video_id, date)
);
CREATE INDEX IF NOT EXISTS ix_perf_daily_channel ON perf_daily (channel_id, date);

CREATE TABLE IF NOT EXISTS perf_traffic (
    video_id    TEXT NOT NULL,
    date        TEXT NOT NULL,
    source_type TEXT NOT NULL,
    views       INTEGER,
    minutes_watched REAL,
    pulled_at   TEXT NOT NULL,
    PRIMARY KEY (video_id, date, source_type)
);

-- Une courbe par jalon (J+2, J+7, J+30) : capturée une fois, jamais réécrite.
-- `points_json` : [[elapsed_ratio, audience_watch_ratio, relative_retention], …] (100 points).
CREATE TABLE IF NOT EXISTS retention_curves (
    video_id          TEXT NOT NULL,
    captured_at       TEXT NOT NULL,
    day_after_publish INTEGER NOT NULL,
    points_json       TEXT NOT NULL,
    PRIMARY KEY (video_id, day_after_publish)
);

-- Agrégé par (vidéo, jour) depuis le rapport brut : impressions sommées, CTR pondéré par
-- les impressions. `ctr` en fraction (0,045 = 4,5 %), tel que Google l'écrit.
CREATE TABLE IF NOT EXISTS perf_reach (
    video_id      TEXT NOT NULL,
    date          TEXT NOT NULL,
    impressions   INTEGER,
    ctr           REAL,
    source_report TEXT NOT NULL,
    PRIMARY KEY (video_id, date, source_report)
);

-- Fichiers de la Reporting API déjà téléchargés : « nouveaux fichiers seulement ».
CREATE TABLE IF NOT EXISTS reporting_reports (
    report_id   TEXT PRIMARY KEY,
    job_id      TEXT NOT NULL,
    channel_id  TEXT NOT NULL,
    report_type TEXT NOT NULL,
    start_time  TEXT,
    end_time    TEXT,
    create_time TEXT,
    path        TEXT NOT NULL,
    rows        INTEGER,
    loaded      INTEGER NOT NULL DEFAULT 0,
    downloaded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analytics_runs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    date       TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    rows       INTEGER NOT NULL DEFAULT 0,
    status     TEXT NOT NULL CHECK (status IN ('ok', 'partial', 'error', 'skipped')),
    error      TEXT,
    calls      INTEGER NOT NULL DEFAULT 0,
    skipped    INTEGER NOT NULL DEFAULT 0,
    started_at TEXT NOT NULL,
    ended_at   TEXT
);
CREATE INDEX IF NOT EXISTS ix_analytics_runs_date ON analytics_runs (date, channel_id);

-- La vue de la boucle : facteurs du manifeste × publication × résultats.
-- Les facteurs sont lus dans `runs.manifest_json` (colonnes matérialisées en repli) :
-- la vue suit le manifeste sans migration quand un run est réindexé.
-- Fenêtres : jours 0 à 6 et 0 à 29 après `publish_at` (sommes, pas valeurs du jour N).
-- `complete_7d` = 1 seulement si J+7 est passé de plus de 3 jours (latence).
CREATE VIEW IF NOT EXISTS v_video_perf AS
WITH base AS (
    SELECT p.video_id,
           p.channel_id,
           p.youtube_video_id,
           p.status AS publish_status,
           coalesce(p.publish_at, p.uploaded_at) AS publish_at,
           date(coalesce(p.publish_at, p.uploaded_at)) AS d0,
           r.manifest_json AS m,
           r.topic_cluster, r.title_pattern, r.parent_id,
           r.slot_local_day, r.slot_local_hour
      FROM publications p
      LEFT JOIN runs r ON r.video_id = p.video_id
     WHERE p.youtube_video_id IS NOT NULL
),
agg AS (
    SELECT b.video_id,
           sum(CASE WHEN d.date < date(b.d0, '+7 days')  THEN d.views END)           AS views_7d,
           sum(CASE WHEN d.date < date(b.d0, '+30 days') THEN d.views END)           AS views_30d,
           sum(CASE WHEN d.date < date(b.d0, '+7 days')  THEN d.minutes_watched END) AS minutes_7d,
           sum(CASE WHEN d.date < date(b.d0, '+7 days')  THEN d.subs_gained END)     AS subs_7d,
           sum(CASE WHEN d.date < date(b.d0, '+30 days') THEN d.subs_gained END)     AS subs_30d,
           -- moyennes pondérées par les vues du jour
           sum(CASE WHEN d.date < date(b.d0, '+7 days') THEN d.avg_view_pct * d.views END)
             / nullif(sum(CASE WHEN d.date < date(b.d0, '+7 days') THEN d.views END), 0)
             AS avg_view_pct_7d,
           sum(CASE WHEN d.date < date(b.d0, '+7 days') THEN d.avg_view_duration_s * d.views END)
             / nullif(sum(CASE WHEN d.date < date(b.d0, '+7 days') THEN d.views END), 0)
             AS avg_view_duration_7d,
           count(d.date) AS days_pulled,
           max(d.date)   AS last_date
      FROM base b
      LEFT JOIN perf_daily d ON d.video_id = b.video_id
     GROUP BY b.video_id
),
reach AS (
    SELECT b.video_id,
           sum(x.impressions) AS impressions_7d,
           sum(x.impressions * x.ctr) / nullif(sum(x.impressions), 0) AS ctr_7d
      FROM base b
      JOIN perf_reach x ON x.video_id = b.video_id
                       AND x.date < date(b.d0, '+7 days')
                       AND x.source_report LIKE 'channel_reach_basic%'
     GROUP BY b.video_id
)
SELECT b.video_id,
       b.channel_id,
       b.youtube_video_id,
       b.publish_status,
       b.publish_at,
       -- facteurs
       json_extract(b.m, '$.decisions.topic.sujet')  AS topic,
       coalesce(b.topic_cluster,
                json_extract(b.m, '$.decisions.topic.cluster_id'),
                CASE WHEN instr(json_extract(b.m, '$.decisions.topic.evidence.requete'), 'cluster ') > 0
                     THEN rtrim(substr(json_extract(b.m, '$.decisions.topic.evidence.requete'),
                                instr(json_extract(b.m, '$.decisions.topic.evidence.requete'), 'cluster ') + 8, 5), ' ')
                END)                                  AS topic_cluster,
       json_extract(b.m, '$.decisions.topic.source') AS topic_source,
       json_extract(b.m, '$.decisions.hook_type')    AS hook_type,
       coalesce(b.title_pattern,
                (SELECT json_extract(t.value, '$.pattern_id')
                   FROM json_each(b.m, '$.decisions.title_variants') t
                  WHERE json_extract(t.value, '$.text') = json_extract(b.m, '$.decisions.title_chosen')
                  LIMIT 1))                           AS title_pattern,
       (SELECT json_extract(v.value, '$.template')
          FROM json_each(b.m, '$.decisions.thumbnail_variants') v
         WHERE json_extract(v.value, '$.file') LIKE '%' || json_extract(b.m, '$.decisions.thumbnail_chosen') || '.png'
         LIMIT 1)                                     AS thumbnail_template,
       (SELECT length(json_extract(v.value, '$.text'))
          FROM json_each(b.m, '$.decisions.thumbnail_variants') v
         WHERE json_extract(v.value, '$.file') LIKE '%' || json_extract(b.m, '$.decisions.thumbnail_chosen') || '.png'
         LIMIT 1)                                     AS thumbnail_text_len,
       json_extract(b.m, '$.identite.style')         AS style,
       json_extract(b.m, '$.identite.template_id')   AS template_id,
       json_extract(b.m, '$.decisions.cut_rhythm_target_s')   AS cut_rhythm_target_s,
       json_extract(b.m, '$.decisions.cut_rhythm_measured_s') AS cut_rhythm_measured_s,
       json_extract(b.m, '$.decisions.duration_s')   AS duration_s,
       json_extract(b.m, '$.identite.lang')          AS lang,
       json_extract(b.m, '$.identite.niche')         AS niche,
       json_extract(b.m, '$.decisions.voice_id')     AS voice_id,
       coalesce(b.slot_local_day, CAST(strftime('%w', b.publish_at) AS INTEGER)) AS publish_weekday,
       coalesce(b.slot_local_hour, CAST(strftime('%H', b.publish_at) AS INTEGER)) AS publish_hour,
       json_extract(b.m, '$.decisions.density_facts_per_min') AS density_facts_per_min,
       json_extract(b.m, '$.decisions.qc_score')     AS qc_score,
       CASE WHEN coalesce(b.parent_id, json_extract(b.m, '$.identite.parent_id')) IS NOT NULL
            THEN 1 ELSE 0 END                         AS is_child,
       -- métriques
       a.views_7d, a.views_30d, a.avg_view_pct_7d, a.avg_view_duration_7d,
       x.ctr_7d, x.impressions_7d, a.subs_7d, a.subs_30d, a.minutes_7d,
       a.days_pulled, a.last_date,
       CASE WHEN date('now') >= date(b.d0, '+10 days') THEN 1 ELSE 0 END AS complete_7d,
       CASE WHEN date('now') >= date(b.d0, '+33 days') THEN 1 ELSE 0 END AS complete_30d
  FROM base b
  LEFT JOIN agg a   ON a.video_id = b.video_id
  LEFT JOIN reach x ON x.video_id = b.video_id;
