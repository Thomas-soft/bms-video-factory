-- 007 — file de production de l'orchestrateur (étape 22.1).
--
-- La table `jobs` existe depuis la migration 001 ; il lui manquait le verrou. Elle est
-- **reconstruite** plutôt qu'étendue par `ALTER TABLE` pour une seule raison : SQLite ne
-- sait pas ajouter une contrainte `CHECK` à une table existante, et un statut de job mal
-- orthographié par un futur appelant est exactement le défaut qu'on ne verrait jamais —
-- le job resterait invisible de toutes les requêtes du runner. La table est vide à ce jour
-- (aucun job n'a jamais été enfilé), la reconstruction ne coûte donc rien.
--
-- `locked_by` porte « hôte:pid » et `locked_at` l'horodatage de la prise : un verrou dont
-- le PID est mort est repris d'office (ARCHITECTURE § 1.3), ce qui suppose de savoir QUI
-- le tenait. Un `locked_by` sans `locked_at` ne permettrait pas de distinguer un verrou
-- frais d'un verrou orphelin.

DROP INDEX IF EXISTS ix_jobs_status;
DROP INDEX IF EXISTS ix_jobs_video;
ALTER TABLE jobs RENAME TO jobs_001;

CREATE TABLE jobs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Le run existe déjà quand le job est enfilé : `queue add` exécute `plan` puis enfile.
    video_id    TEXT NOT NULL,
    channel_id  TEXT NOT NULL,
    -- Étape **courante**, celle qui reste à faire. C'est elle que la reprise relit.
    stage       TEXT NOT NULL,
    status      TEXT NOT NULL CHECK (status IN (
                    'queued', 'running', 'awaiting_review', 'blocked',
                    'failed', 'exported', 'published')),
    -- Tentatives de l'étape courante ; remis à 0 dès qu'une étape passe.
    attempts    INTEGER NOT NULL DEFAULT 0,
    next_run_at TEXT,
    last_error  TEXT,
    priority    INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    locked_by   TEXT,
    locked_at   TEXT
);

INSERT INTO jobs (id, video_id, channel_id, stage, status, attempts, next_run_at,
                  last_error, priority, created_at, updated_at)
SELECT id, video_id, channel_id, stage, status, attempts, next_run_at,
       last_error, priority, created_at, updated_at
  FROM jobs_001;

DROP TABLE jobs_001;

-- Le runner interroge « quel job prendre » : statut, priorité, âge.
CREATE INDEX IF NOT EXISTS ix_jobs_prise ON jobs (status, priority DESC, created_at);
CREATE INDEX IF NOT EXISTS ix_jobs_video ON jobs (video_id);
-- Un run n'a qu'un job vivant à la fois : deux jobs sur le même run se voleraient le
-- dossier. Les états terminaux sont exclus de l'unicité, pour qu'un run puisse être
-- ré-enfilé après coup (régénération de l'étape 22.2).
CREATE UNIQUE INDEX IF NOT EXISTS ux_jobs_actif ON jobs (video_id)
    WHERE status IN ('queued', 'running', 'awaiting_review', 'blocked');

-- Index du journal. `workspace/logs/events.jsonl` reste la source (ARCHITECTURE § 7) :
-- cette table est un confort de requête, elle se reconstruit en relisant le fichier.
CREATE TABLE IF NOT EXISTS events (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ts       TEXT NOT NULL,
    job      INTEGER,
    video_id TEXT,
    stage    TEXT,
    level    TEXT NOT NULL,
    msg      TEXT NOT NULL,
    data     TEXT
);

CREATE INDEX IF NOT EXISTS ix_events_job ON events (job, ts);
CREATE INDEX IF NOT EXISTS ix_events_video ON events (video_id, ts);
