-- 013 — index unifié de la bibliothèque (étape 29) : description, tags, embedding, poids.
-- `used_by` n'est pas stocké : il se lit dans `library_uses` (source unique des emplois).

ALTER TABLE library_assets ADD COLUMN description TEXT;
ALTER TABLE library_assets ADD COLUMN tags TEXT;              -- JSON, ex. ["charte:bms-science-en"]
ALTER TABLE library_assets ADD COLUMN size_bytes INTEGER;
ALTER TABLE library_assets ADD COLUMN embedding BLOB;         -- float32 L2-normalisé
ALTER TABLE library_assets ADD COLUMN embed_model TEXT;
ALTER TABLE library_assets ADD COLUMN embed_hash TEXT;        -- sha256(description)[:16]

-- Journal des réemplois sémantiques : ce qui a été repris sans génération, et pourquoi.
CREATE TABLE IF NOT EXISTS library_semantic_reuse (
    video_id   TEXT NOT NULL,
    shot_id    TEXT NOT NULL,
    asset_id   TEXT NOT NULL,
    kind       TEXT NOT NULL,
    similarity REAL NOT NULL,
    intention  TEXT NOT NULL,
    reused_at  TEXT NOT NULL,
    PRIMARY KEY (video_id, shot_id)
);
