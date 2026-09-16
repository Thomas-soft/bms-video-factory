-- 002 — bibliothèque d'assets réutilisables (INTERFACES.md § 3, workspace/library/).
-- Les fichiers restent la source de vérité : chaque entrée a un `licence.json` frère sur
-- disque, et la base n'est qu'un index interrogeable (cooldown, compteurs, langue, couche).

CREATE TABLE IF NOT EXISTS library_assets (
    asset_id         TEXT PRIMARY KEY,
    kind             TEXT NOT NULL,          -- images | stock | music | sfx | characters | intros
    layer            TEXT NOT NULL DEFAULT 'background',
    path             TEXT NOT NULL,          -- relatif à la racine du projet
    provider         TEXT NOT NULL,
    licence          TEXT NOT NULL,
    licence_url      TEXT NOT NULL,
    attribution_line TEXT,
    person_release   TEXT,
    has_text         INTEGER NOT NULL DEFAULT 0,
    lang             TEXT,                   -- NULL = indifférent à la langue (has_text = 0)
    keywords         TEXT,
    phash            TEXT,
    -- Clé de cache du moteur illustré : sha256(prompt normalisé + style + charte + format).
    -- Deux plans qui demandent la même image la partagent ; c'est ce qui fait tomber le coût.
    prompt_key       TEXT,
    uses             INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT NOT NULL,
    last_used_at     TEXT
);

CREATE INDEX IF NOT EXISTS ix_library_prompt ON library_assets (prompt_key, kind);
CREATE INDEX IF NOT EXISTS ix_library_kind   ON library_assets (kind, layer);

CREATE TABLE IF NOT EXISTS library_uses (
    asset_id   TEXT NOT NULL,
    video_id   TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    used_at    TEXT NOT NULL,
    PRIMARY KEY (asset_id, video_id)
);

CREATE INDEX IF NOT EXISTS ix_library_uses_channel ON library_uses (channel_id, used_at);
CREATE INDEX IF NOT EXISTS ix_library_uses_video   ON library_uses (video_id);
