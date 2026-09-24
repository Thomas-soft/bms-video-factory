-- 008 — journal de relecture complet et traces de régénération (étape 22.2).
--
-- `review_log` de la migration 001 avait pour clé primaire l'empreinte du script. C'était
-- faux pour deux raisons, et les deux sont des pertes de preuve :
--
-- 1. **Une relecture a une histoire.** Un script rejeté avec motif, réécrit, puis approuvé,
--    produit deux décisions. Avec `review_hash` en clé primaire, la seconde écrasait la
--    première (`INSERT OR REPLACE`) : le rejet disparaissait du journal. Or c'est
--    précisément l'enchaînement « rejeté → corrigé → approuvé » qui démontre le contrôle
--    éditorial exigé par le RIA art. 50 §4. `CONFORMITE` § 10.2 l'écrit noir sur blanc :
--    « ne réécris jamais une ligne ». La clé devient donc un identifiant de ligne.
-- 2. **Le motif logeait dans `batch_id`.** Un champ dont le nom annonce un lot portait la
--    raison d'un rejet. `motif` existe maintenant pour lui-même, `batch_id` redevient le
--    lot de relecture.
--
-- `script_sha256` et `timestamp` remplacent `review_hash` et `review_date` — ce sont les
-- noms qu'emploient l'étape 22.2 et ses critères de validation. Les deux anciens noms
-- survivent en **colonnes générées** : `runner._script_relu` et tout lecteur écrit avant
-- cette migration continuent de fonctionner sans être réécrits, et il n'existe toujours
-- qu'une seule vérité stockée.

ALTER TABLE review_log RENAME TO review_log_001;
DROP INDEX IF EXISTS ix_review_video;

CREATE TABLE review_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id      TEXT NOT NULL,
    channel_id    TEXT NOT NULL,
    reviewer      TEXT NOT NULL,
    decision      TEXT NOT NULL CHECK (decision IN (
                      'approved', 'approved_with_edits', 'rejected', 'auto_approved')),
    -- Motif du rejet, ou raison d'une levée sans lecture. Obligatoire pour ces deux-là,
    -- vérifié par le code : SQLite ne sait pas contraindre « non vide si decision = X »
    -- sans interdire aussi la chaîne vide ailleurs.
    motif         TEXT,
    script_sha256 TEXT NOT NULL,
    timestamp     TEXT NOT NULL,
    batch_id      TEXT,
    -- Compatibilité avec la migration 001 : mêmes valeurs, deux noms, un seul stockage.
    review_hash   TEXT GENERATED ALWAYS AS (script_sha256) VIRTUAL,
    review_date   TEXT GENERATED ALWAYS AS (timestamp) VIRTUAL
);

-- Reprise des lignes existantes. `batch_id` y portait le motif des levées sans lecture :
-- il est remis dans `motif`, sa place.
INSERT INTO review_log (video_id, channel_id, reviewer, decision, motif, script_sha256,
                        timestamp, batch_id)
SELECT video_id, channel_id, reviewer, decision, batch_id, review_hash, review_date, NULL
  FROM review_log_001;

DROP TABLE review_log_001;

CREATE INDEX IF NOT EXISTS ix_review_video ON review_log (video_id, timestamp);
-- La barrière du runner interroge « ce script porte-t-il une approbation ? ».
CREATE INDEX IF NOT EXISTS ix_review_script ON review_log (script_sha256, decision);
