-- 003 — le verdict du banc (étape 15) à côté du score déjà prévu par la migration 001.
-- `score_qc` existait ; sans son verdict, une requête ne peut pas distinguer « 68, refusé »
-- de « 68, publié parce qu'aucun bloquant n'a sauté ». La version du banc est nécessaire à
-- l'étape 26 : deux scores calculés par deux barèmes différents ne se corrèlent pas ensemble.
ALTER TABLE runs ADD COLUMN qc_verdict TEXT;
ALTER TABLE runs ADD COLUMN qc_version TEXT;

CREATE INDEX IF NOT EXISTS ix_runs_qc ON runs (qc_verdict, score_qc);
