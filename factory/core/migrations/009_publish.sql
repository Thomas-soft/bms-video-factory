-- 009 — publication, quota et jobs de rapports (étape 23.1).
--
-- **Numéro.** `INTERFACES.md` § 3 annonce ces tables sous « 004 (étape 23.1) ». Le 004 est
-- pris depuis l'étape 18 par `004_editorial.sql`, et `schema_migrations.version` est une clé
-- primaire : deux migrations ne peuvent pas porter le même numéro. Les tables sont celles du
-- contrat, mot pour mot ; seul le numéro de fichier diverge. Divergence à reporter dans
-- `INTERFACES.md` § 3.
--
-- **`quota_ledger` porte une ligne par appel, pas un compteur par jour.** Le prompt de
-- l'étape décrivait `(date, project, units, inserts, updates)` ; `INTERFACES.md` décrit
-- `(day, gcp_project, call, units, video_id, at)`. Le contrat gagne, pour une raison de
-- fond : un compteur agrégé ne sait pas dire *quel* appel a mangé la journée, donc ne sait
-- pas expliquer un `quotaExceeded`. La forme agrégée du prompt est rendue par la vue
-- `v_quota_jour` ci-dessous, qui se calcule en une requête.
--
-- **Deux colonnes de plus que le contrat : `compartment` et `ok`.** Depuis juin 2026, le
-- quota de la Data API est compartimenté : `videos.insert` coûte **1 unité dans le
-- compartiment « Video Uploads » (100/jour)**, et non 1 600 unités sur les 10 000
-- (developers.google.com/youtube/v3/determine_quota_cost et /getting-started, vérifiés le
-- 22/09/2026). Un ledger à une seule colonne d'unités additionnerait deux monnaies
-- différentes et rendrait un solde faux. `ok` distingue un appel dépensé-et-réussi d'un
-- appel dépensé-et-refusé : le quota est débité dans les deux cas, et sans cette colonne une
-- journée perdue en 403 serait indiscernable d'une journée de travail.

CREATE TABLE IF NOT EXISTS publications (
    video_id         TEXT PRIMARY KEY,
    channel_id       TEXT NOT NULL,
    youtube_video_id TEXT,
    -- `published_private` : en ligne, privée, en attente du geste manuel dans Studio.
    -- `scheduled` : `status.publishAt` posé — possible seulement après l'audit.
    -- `public` : constaté par `videos.list`, jamais décidé par nous avant l'audit.
    status           TEXT NOT NULL CHECK (status IN (
                         'published_private', 'scheduled', 'public', 'failed')),
    publish_at       TEXT,
    uploaded_at      TEXT,
    thumbnail_set    INTEGER NOT NULL DEFAULT 0,
    captions_set     INTEGER NOT NULL DEFAULT 0,
    playlist_added   INTEGER NOT NULL DEFAULT 0,
    units_used       INTEGER NOT NULL DEFAULT 0,
    last_error       TEXT,
    updated_at       TEXT NOT NULL
);

-- La jointure de la boucle de rétroaction (étape 25) passe par là.
CREATE UNIQUE INDEX IF NOT EXISTS ux_publications_youtube ON publications (youtube_video_id)
    WHERE youtube_video_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_publications_channel ON publications (channel_id, status);

CREATE TABLE IF NOT EXISTS quota_ledger (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Jour **UTC** : c'est sur lui que Google remet les compteurs à zéro (minuit Pacifique
    -- pour les rapports, minuit Pacifique aussi pour le quota de la Data API). Le décalage
    -- est assumé et documenté dans `quota.py` : compter en UTC est plus strict, jamais plus
    -- laxiste, que compter en heure du Pacifique.
    day         TEXT NOT NULL,
    gcp_project TEXT NOT NULL,
    call        TEXT NOT NULL,
    compartment TEXT NOT NULL CHECK (compartment IN ('uploads', 'search', 'units', 'reporting')),
    units       INTEGER NOT NULL,
    video_id    TEXT,
    channel_id  TEXT,
    ok          INTEGER NOT NULL DEFAULT 1,
    detail      TEXT,
    at          TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_quota_jour ON quota_ledger (day, gcp_project, compartment);

-- La forme agrégée que le prompt de l'étape demandait, et que `factory publish status` lit.
CREATE VIEW IF NOT EXISTS v_quota_jour AS
SELECT day,
       gcp_project,
       sum(CASE WHEN compartment = 'units'   THEN units ELSE 0 END) AS units,
       sum(CASE WHEN compartment = 'uploads' THEN units ELSE 0 END) AS uploads,
       sum(CASE WHEN call = 'videos.insert' THEN 1 ELSE 0 END)      AS inserts,
       sum(CASE WHEN call = 'videos.update' THEN 1 ELSE 0 END)      AS updates,
       sum(CASE WHEN ok = 0 THEN 1 ELSE 0 END)                      AS erreurs,
       count(*)                                                     AS appels
  FROM quota_ledger
 GROUP BY day, gcp_project;

CREATE TABLE IF NOT EXISTS reporting_jobs (
    job_id      TEXT PRIMARY KEY,
    channel_id  TEXT NOT NULL,
    report_type TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    -- `active` tant que le job vit chez Google, `deleted` s'il a disparu de `jobs.list`.
    state       TEXT NOT NULL DEFAULT 'active',
    -- Premier rapport attendu : `createTime + 48 h` (Google : « within 48 hours of the time
    -- that the job is created »). Écrit à la création pour que le tableau de bord sache si
    -- l'absence de données est normale ou anormale.
    first_report_expected_at TEXT,
    seen_at     TEXT NOT NULL
);

-- Un seul job par (chaîne, type) : `jobs.create` est idempotent de notre côté, pas du sien.
CREATE UNIQUE INDEX IF NOT EXISTS ux_reporting_jobs_type
    ON reporting_jobs (channel_id, report_type);
