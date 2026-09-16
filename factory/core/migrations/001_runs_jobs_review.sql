-- 001 — index des runs, file de production, journal de relecture.
-- Les fichiers restent la source de vérité : `factory queue reindex` reconstruit
-- intégralement `runs` en relisant les manifest.json (ARCHITECTURE § 1.8).

CREATE TABLE IF NOT EXISTS runs (
    video_id                TEXT PRIMARY KEY,
    parent_id               TEXT,
    channel_id              TEXT NOT NULL,
    lang                    TEXT NOT NULL,
    niche                   TEXT,
    style                   TEXT,
    template_id             TEXT,
    charte_version          TEXT,
    run_state               TEXT,
    publish_state           TEXT,
    publish_path            TEXT,
    youtube_video_id        TEXT,
    published_at            TEXT,
    topic_sujet             TEXT,
    topic_source            TEXT,
    topic_score             REAL,
    topic_cluster           TEXT,
    hook_type               TEXT,
    title_pattern           TEXT,
    title_chosen            TEXT,
    thumbnail_variant_chosen TEXT,
    voice_id                TEXT,
    duration_s              REAL,
    cut_rhythm_target_s     REAL,
    cut_rhythm_measured_s   REAL,
    density_facts_per_min   REAL,
    open_loops_planted      INTEGER,
    reuse_ratio             REAL,
    slot_local_day          TEXT,
    slot_local_hour         INTEGER,
    score_qc                REAL,
    cost_compute_min        REAL,
    disk_mb_peak            REAL,
    reviewer                TEXT,
    review_decision         TEXT,
    created_at              TEXT NOT NULL,
    updated_at              TEXT NOT NULL,
    manifest_path           TEXT,
    manifest_json           TEXT
);

CREATE INDEX IF NOT EXISTS ix_runs_channel_pub ON runs (channel_id, published_at);
CREATE UNIQUE INDEX IF NOT EXISTS ux_runs_youtube
    ON runs (youtube_video_id) WHERE youtube_video_id IS NOT NULL;

-- File de production. status : queued | running | awaiting_review | blocked | failed
--                              | exported | published
CREATE TABLE IF NOT EXISTS jobs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id    TEXT NOT NULL,
    channel_id  TEXT NOT NULL,
    stage       TEXT NOT NULL,
    status      TEXT NOT NULL,
    attempts    INTEGER NOT NULL DEFAULT 0,
    next_run_at TEXT,
    last_error  TEXT,
    priority    INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_jobs_status ON jobs (status, next_run_at);
CREATE INDEX IF NOT EXISTS ix_jobs_video ON jobs (video_id);

-- Journal de relecture. La ligne de registre/data/reviews.jsonl fait foi ; ceci est l'index.
CREATE TABLE IF NOT EXISTS review_log (
    review_hash TEXT PRIMARY KEY,
    video_id    TEXT NOT NULL,
    channel_id  TEXT NOT NULL,
    reviewer    TEXT NOT NULL,
    review_date TEXT NOT NULL,
    decision    TEXT NOT NULL,
    batch_id    TEXT
);

CREATE INDEX IF NOT EXISTS ix_review_video ON review_log (video_id);
