-- 010 — calendrier de publication (étape 23.2).
--
-- `publish_at` : date **UTC** de publication décidée par `factory calendar plan`. Tant que
-- l'audit API n'est pas obtenu, c'est une intention : elle ressort dans
-- `factory publish manual-list` et le geste se fait dans Studio (CONFORMITE § 2).
-- `publish_plan` : JSON de la décision (créneau de base, jitter tiré, source des créneaux,
-- avertissements), pour qu'une date se relise sans rejouer le tirage.
ALTER TABLE jobs ADD COLUMN publish_at TEXT;
ALTER TABLE jobs ADD COLUMN publish_plan TEXT;

CREATE INDEX IF NOT EXISTS ix_jobs_publish_at ON jobs (publish_at);
