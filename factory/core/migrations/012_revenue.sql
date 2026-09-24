-- 012 — revenus par vidéo : publicité (Analytics API) et affiliation (exports des programmes).
-- Étape 27. Colonnes du prompt, plus trois colonnes de traçabilité :
--   sub_id    : sous-identifiant tel que lu dans l'export (NULL pour la publicité) ;
--   origin    : import | fixture | api — les lignes `fixture` ne comptent jamais dans l'économie ;
--   row_key   : empreinte de la ligne source, pour qu'un ré-import ne double pas les montants.
-- `video_id` NULL = conversion non rattachée (sous-ID inconnu, ou Amazon : suivi par tracking ID,
-- donc à la chaîne au mieux). Montants dans la devise du rapport, jamais convertis ici.
CREATE TABLE IF NOT EXISTS revenue (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id      TEXT,
    channel_id    TEXT,
    source        TEXT NOT NULL CHECK (source IN ('ads', 'affiliate')),
    program       TEXT NOT NULL,
    date          TEXT NOT NULL,
    clicks        INTEGER,
    conversions   INTEGER,
    amount        REAL NOT NULL DEFAULT 0,
    currency      TEXT NOT NULL,
    imported_at   TEXT NOT NULL,
    sub_id        TEXT,
    origin        TEXT NOT NULL DEFAULT 'import' CHECK (origin IN ('import', 'fixture', 'api')),
    row_key       TEXT NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS ix_revenue_video ON revenue (video_id);
CREATE INDEX IF NOT EXISTS ix_revenue_date ON revenue (date);
