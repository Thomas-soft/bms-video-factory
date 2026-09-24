-- 005 — notation des niches (étape 19).
--
-- Une ligne par (niche, langue, date d'exécution). L'historique est conservé :
-- ce sont des mesures dérivées, pas des données de l'API YouTube (CONFORMITE § 9),
-- et la comparaison d'un classement à un mois d'écart est tout l'intérêt de la table.
--
-- `evidence_json` porte les chiffres et les liens qui ont produit chaque sous-score :
-- sans eux une note de 0 à 100 n'est qu'une opinion chiffrée.

CREATE TABLE IF NOT EXISTS niche_scores (
    niche         TEXT NOT NULL,
    lang          TEXT NOT NULL,
    date          TEXT NOT NULL,
    -- sous-scores, tous normalisés 0-100 entre les niches d'une même exécution
    demande       REAL,
    concurrence   REAL,
    monetisation  REAL,
    faisabilite   REAL,
    score         REAL,
    -- saisonnalité : les trois meilleurs mois, « 01,02,11 », et l'indice du meilleur
    top_mois      TEXT,
    indice_top    REAL,
    -- 'registre' pour les 8 niches mesurées, 'candidate' pour les propositions du LLM
    origine       TEXT NOT NULL DEFAULT 'registre',
    evidence_json TEXT,
    computed_at   TEXT NOT NULL,
    PRIMARY KEY (niche, lang, date)
);

CREATE INDEX IF NOT EXISTS ix_niche_scores_date ON niche_scores (date, score);
