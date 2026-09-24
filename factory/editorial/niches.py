"""Notation des niches : demande, concurrence, monétisation, faisabilité.

Quatre sous-scores, quatre statuts épistémiques différents, et le rapport les
sépare toujours :

  - **demande** — mesurée hors de YouTube (Wikimedia Pageviews) et complétée par
    un signal qualitatif non documenté (autocomplete). C'est un *proxy* : les
    lecteurs de Wikipédia ne sont pas les spectateurs de YouTube.
  - **concurrence** — mesurée dans l'entrepôt de l'étape 18, donc sur les 74
    chaînes du registre et **rien d'autre**. Ce n'est pas un recensement du
    marché : c'est un recensement de l'échantillon dont on dispose.
  - **monétisation** — entièrement lue dans `config/editorial.yaml`. Aucune note
    subjective n'est calculée par ce module ; chaque note y porte sa source.
  - **faisabilité** — lue aussi dans la configuration, adossée aux styles
    réellement rendus (`docs/STYLES.md` § 6 et § 7).

Le score composite est une **pondération d'opinions bien documentées**, pas une
mesure. Il sert à ordonner des candidats, jamais à prouver qu'une niche est bonne.
"""

from __future__ import annotations

import json
import math
import sqlite3
import statistics
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import yaml

from factory.core.paths import dossier_config, racine_projet
from factory.editorial import demand as dm

MOIS_FR = {1: "janvier", 2: "février", 3: "mars", 4: "avril", 5: "mai", 6: "juin",
           7: "juillet", 8: "août", 9: "septembre", 10: "octobre", 11: "novembre",
           12: "décembre"}


def charger_config(racine: Path | None = None) -> dict:
    chemin = dossier_config(racine) / "editorial.yaml"
    return yaml.safe_load(chemin.read_text(encoding="utf-8"))


# --------------------------------------------------------------- concurrence


def _portee_sql(definition: dict) -> tuple[str, list]:
    """Clause SQL qui délimite une niche dans l'entrepôt.

    Deux régimes, et ils ne valent pas la même chose :
      - `labels_entrepot` — les chaînes portent l'étiquette de niche. Recensement.
      - `filtre_titre` — la niche n'existe pas dans le registre et n'est repérée
        que par les mots de ses titres. **Proxy lexical**, marqué comme tel
        partout où le chiffre sort.
    """
    labels = definition.get("labels_entrepot") or []
    motifs = definition.get("filtre_titre") or []
    clauses, params = [], []
    if labels:
        clauses.append("cw.niche IN (" + ",".join("?" * len(labels)) + ")")
        params.extend(labels)
    if motifs:
        clauses.append("(" + " OR ".join(["lower(ve.title) LIKE ?"] * len(motifs)) + ")")
        params.extend(motifs)
    if not clauses:
        return "0", []
    return "(" + " OR ".join(clauses) + ")", params


def mesures_concurrence(conn: sqlite3.Connection, definition: dict, lang: str, reglages: dict) -> dict:
    """Chaînes actives, vélocité médiane des vidéos récentes, part de percées."""
    portee, params = _portee_sql(definition)
    conc = reglages["concurrence"]
    jours_activite = conc["fenetre_activite_jours"]
    seuil_semaine = conc["chaine_active_videos_par_semaine"]
    mini_videos = jours_activite / 7.0 * seuil_semaine
    jours_velocite = conc["fenetre_velocite_jours"]
    jours_percees = conc["fenetre_percees_jours"]
    seuil_percee = conc["seuil_percee_ratio"]
    plancher_videos = conc["plancher_videos"]
    plancher_chaines = conc["plancher_chaines"]

    base = f"""
        FROM videos_ext ve
        LEFT JOIN channels_watch cw ON cw.channel_id = ve.channel_id
        WHERE COALESCE(cw.lang, 'en') = ? AND {portee}
    """
    p = [lang, *params]

    actives = conn.execute(
        f"""SELECT ve.channel_id, COALESCE(cw.title, ve.channel_id) AS titre, COUNT(*) AS n
            {base} AND julianday('now') - julianday(ve.published_at) <= ?
            GROUP BY ve.channel_id HAVING n >= ?
            ORDER BY n DESC""",
        [*p, jours_activite, mini_videos],
    ).fetchall()
    n_chaines_total = conn.execute(
        f"SELECT COUNT(DISTINCT ve.channel_id) {base}", p
    ).fetchone()[0]
    n_videos = conn.execute(f"SELECT COUNT(*) {base}", p).fetchone()[0]

    # Vélocité et percées passent par la vue v_video_velocity (étape 18), qui porte
    # déjà l'âge exact, le ratio à la médiane de la chaîne et la source de vélocité.
    portee_v, params_v = _portee_sql(definition)
    portee_v = portee_v.replace("ve.title", "vv.title").replace("cw.niche", "vv.niche")
    base_v = f"FROM v_video_velocity vv WHERE COALESCE(vv.lang, 'en') = ? AND {portee_v}"
    pv = [lang, *params_v]

    recentes = [r[0] for r in conn.execute(
        f"SELECT vv.velocity {base_v} AND vv.age_days <= ? AND vv.velocity IS NOT NULL",
        [*pv, jours_velocite],
    ).fetchall()]
    velocite_mediane = float(statistics.median(recentes)) if recentes else None

    ratios = [r[0] for r in conn.execute(
        f"SELECT vv.ratio {base_v} AND vv.age_days <= ? AND vv.ratio IS NOT NULL",
        [*pv, jours_percees],
    ).fetchall()]
    part_percees = (sum(1 for r in ratios if r > seuil_percee) / len(ratios)) if ratios else None

    sources = conn.execute(
        f"SELECT DISTINCT vv.velocity_source {base_v} AND vv.velocity IS NOT NULL", pv
    ).fetchall()

    # Plancher de données. Sans lui, l'ignorance paie : une niche dont l'entrepôt ne
    # sait rien affiche « 0 chaîne active », donc une rareté parfaite, donc le meilleur
    # score de concurrence du tableau. Mesuré le 20/09/2026 :
    # `niche_monetisable_complements_fr` obtenait 45,0 sur **0 vidéo et 0 chaîne** en
    # anglais. Sous le plancher, les trois sous-mesures valent None et la niche n'est
    # pas notée sur la concurrence — elle ne gagne rien à n'être pas mesurée.
    assez = n_videos >= plancher_videos and n_chaines_total >= plancher_chaines

    return {
        "assez_de_donnees": assez,
        "plancher": f"≥ {plancher_videos} vidéos et ≥ {plancher_chaines} chaînes",
        "n_chaines_actives": len(actives),
        "n_chaines_actives_notees": len(actives) if assez else None,
        "n_chaines_total": n_chaines_total,
        "n_videos": n_videos,
        "chaines_actives": [{"titre": a["titre"], "videos_90j": a["n"]} for a in actives[:6]],
        "velocite_mediane_30j": velocite_mediane if assez else None,
        "velocite_mediane_brute": velocite_mediane,
        "n_videos_recentes": len(recentes),
        "part_percees": part_percees if assez else None,
        "part_percees_brute": part_percees,
        "n_videos_notees": len(ratios),
        "velocity_source": sorted({s[0] for s in sources if s[0]}),
        "portee": "labels de niche" if definition.get("labels_entrepot") else "proxy lexical",
        "seuils": {"chaine_active": f"≥ {seuil_semaine}/semaine sur {jours_activite} j",
                   "percee": f"ratio > {seuil_percee} sur {jours_percees} j"},
    }


# ------------------------------------------------------------------- demande


def mesures_demande(
    definition: dict, lang: str, reglages: dict, *, racine: Path | None = None,
    budget_wiki: dm.BudgetAppels | None = None, budget_auto: dm.BudgetAppels | None = None,
) -> dict:
    projet = f"{lang}.wikipedia"
    seeds = definition.get("seeds_wikipedia") or []
    series = dm.demande_wikimedia(
        seeds, projet, n_mois=reglages["demande"]["fenetre_mois"], racine=racine,
        budget=budget_wiki,
    )
    agrege = dm.agreger(series, r2_minimal=reglages["demande"]["r2_minimal"])

    region = (reglages.get("autocomplete_regions") or {}).get(lang, {"hl": lang, "gl": "US"})
    auto = dm.demande_autocomplete(
        definition.get("mots_cles") or [], hl=region["hl"], gl=region["gl"],
        racine=racine, budget=budget_auto,
    )
    trends, note_trends = dm.demande_trends(definition.get("mots_cles") or [], lang=lang)
    return {"wikimedia": agrege, "autocomplete": auto, "trends": trends, "note_trends": note_trends,
            "projet": projet}


# ---------------------------------------------------------------- normalisation


def normaliser(valeurs: list[float | None]) -> list[float]:
    """Min-max sur les niches d'une même exécution. Un manquant vaut 0, jamais la moyenne.

    Un `None` signifie « pas de donnée », et une niche sans donnée ne doit pas
    hériter du score moyen des autres : c'est exactement ainsi qu'une niche vide
    se retrouve surclassée. Elle prend 0 et le rapport dit pourquoi.
    """
    presents = [v for v in valeurs if v is not None]
    if not presents:
        return [0.0 for _ in valeurs]
    lo, hi = min(presents), max(presents)
    if hi - lo < 1e-12:
        return [0.5 if v is not None else 0.0 for v in valeurs]
    return [((v - lo) / (hi - lo)) if v is not None else 0.0 for v in valeurs]


def _log(v: float | None) -> float | None:
    return None if v is None else math.log10(1.0 + max(v, 0.0))


# ---------------------------------------------------------------------- score


@dataclass
class Note:
    niche: str
    lang: str
    origine: str
    demande: float = 0.0
    concurrence: float = 0.0
    monetisation: float = 0.0
    faisabilite: float = 0.0
    score: float = 0.0
    #: Une niche éliminatoire garde son score — on montre ce qu'elle vaudrait — mais
    #: elle est marquée, sortie du top 5 et précédée de son motif.
    eliminatoire: bool = False
    motif_eliminatoire: str | None = None
    top_mois: list[int] = field(default_factory=list)
    indice_top: float | None = None
    evidence: dict = field(default_factory=dict)


def _note_sur_100(note_1_5: float | None) -> float:
    """Note humaine 1-5 → 0-100, par `note / 5`.

    **Pas `(note − 1) / 4`** : cette formule écrasait la note 1 à 0, donc « la pire
    note que l'humain puisse donner » devenait indiscernable de « aucune note ». Ici
    une note 1 vaut 20 et **0 est réservé à l'absence de note**.
    """
    if note_1_5 is None:
        return 0.0
    return max(0.0, min(100.0, float(note_1_5) / 5.0 * 100.0))


def noter(
    conn: sqlite3.Connection, *, lang: str = "en", racine: Path | None = None,
    config: dict | None = None, echo=None,
) -> list[Note]:
    cfg = config or charger_config(racine)
    reglages = cfg["niche_scoring"]
    poids = reglages["ponderations"]
    definitions = cfg["niches_notees"]

    budget_wiki = dm.BudgetAppels(reglages["wikimedia"]["max_appels_par_execution"])
    budget_auto = dm.BudgetAppels(reglages["autocomplete"]["max_appels_par_execution"])

    brut = []
    for niche, definition in definitions.items():
        if echo:
            echo(f"  {niche} …")
        dem = mesures_demande(definition, lang, reglages, racine=racine,
                              budget_wiki=budget_wiki, budget_auto=budget_auto)
        conc = mesures_concurrence(conn, definition, lang, reglages)
        mon = (definition.get("monetisation") or {}).get(lang)
        fai = definition.get("faisabilite")
        brut.append({"niche": niche, "definition": definition, "demande": dem,
                     "concurrence": conc, "monetisation": mon, "faisabilite": fai})

    # Normalisation entre niches — c'est ici, et nulle part ailleurs, que les
    # niches deviennent comparables.
    n_niveau = normaliser([_log(b["demande"]["wikimedia"]["niveau"]) for b in brut])
    plafond = reglages["demande"]["pente_bornee"]
    n_pente = normaliser([
        None if b["demande"]["wikimedia"]["pente"] is None
        else max(-plafond, min(plafond, b["demande"]["wikimedia"]["pente"]))
        for b in brut
    ])
    n_auto = normaliser([float(b["demande"]["autocomplete"]["diversite"]) for b in brut])
    # `n_chaines_actives_notees` vaut None sous le plancher de données : la rareté
    # n'est alors pas retournée en 1,0, elle reste nulle.
    rarete_brute = normaliser([_log(b["concurrence"]["n_chaines_actives_notees"]) for b in brut])
    n_rarete = [(1.0 - v) if b["concurrence"]["assez_de_donnees"] else 0.0
                for v, b in zip(rarete_brute, brut, strict=True)]
    n_percees = normaliser([b["concurrence"]["part_percees"] for b in brut])
    # **La vélocité compte NÉGATIVEMENT.** Le sous-score s'appelle « concurrence » et
    # se lit à l'envers : une vélocité médiane élevée sur les vidéos récentes dit que
    # les chaînes en place captent déjà l'attention, donc que la place est chère.
    # Comptée positivement, elle faisait de `true_crime` — 31 320 vues/j de médiane,
    # c'est-à-dire des concurrents qui écrasent tout — une niche « peu concurrentielle ».
    # Lecture contraire assumée : une vélocité élevée signale aussi une niche vivante.
    # C'est le sous-score de demande qui porte cette lecture-là, pas celui-ci.
    pression = normaliser([_log(b["concurrence"]["velocite_mediane_30j"]) for b in brut])
    n_veloc = [(1.0 - v) if b["concurrence"]["assez_de_donnees"] else 0.0
               for v, b in zip(pression, brut, strict=True)]

    sd, sc = reglages["demande"]["sous_ponderations"], reglages["concurrence"]["sous_ponderations"]
    notes: list[Note] = []
    for i, b in enumerate(brut):
        score_d = 100 * (sd["niveau"] * n_niveau[i] + sd["tendance"] * n_pente[i]
                         + sd["autocomplete"] * n_auto[i])
        score_c = 100 * (sc["rarete_chaines"] * n_rarete[i] + sc["part_percees"] * n_percees[i]
                         + sc["pression_velocite"] * n_veloc[i])
        score_m = _note_sur_100((b["monetisation"] or {}).get("note"))
        score_f = _note_sur_100((b["faisabilite"] or {}).get("note"))
        composite = (poids["demande"] * score_d + poids["concurrence"] * score_c
                     + poids["monetisation"] * score_m + poids["faisabilite"] * score_f) / sum(poids.values())

        # Un mois n'est nommé que s'il a **deux observations** et un indice franc.
        # Après la coupe du mois non consolidé il reste 23 mois : août et septembre
        # n'ont qu'une observation, et un indice de 1,06 sur n = 1 est du bruit.
        saison = b["demande"]["wikimedia"]["saisonnalite"]
        seuil_saison = reglages["demande"]["seuil_saison_nomme"]
        nommables = [m for m, (indice, n) in saison.items() if n >= 2 and indice >= seuil_saison]
        top = sorted(nommables, key=lambda m: saison[m][0], reverse=True)[:3]

        notes.append(Note(
            niche=b["niche"], lang=lang, origine=b["definition"].get("origine", "registre"),
            demande=round(score_d, 1), concurrence=round(score_c, 1),
            monetisation=round(score_m, 1), faisabilite=round(score_f, 1),
            score=round(composite, 1), top_mois=top,
            indice_top=round(saison[top[0]][0], 3) if top else None,
            eliminatoire=bool((b["monetisation"] or {}).get("eliminatoire")),
            motif_eliminatoire=(b["monetisation"] or {}).get("motif_eliminatoire"),
            evidence={
                "demande": {
                    "projet": b["demande"]["projet"],
                    "niveau_vues_mensuelles": b["demande"]["wikimedia"]["niveau"],
                    "pente_mensuelle": b["demande"]["wikimedia"]["pente"],
                    "pente_n_seeds": b["demande"]["wikimedia"].get("pente_n_seeds", 0),
                    "r2_minimal": b["demande"]["wikimedia"].get("r2_minimal"),
                    "niveau_somme": b["demande"]["wikimedia"].get("niveau_somme"),
                    "mois_non_consolides": b["demande"]["wikimedia"].get("mois_non_consolides", 0),
                    "n_seeds": b["demande"]["wikimedia"]["n_seeds"],
                    "n_seeds_sans_donnee": b["demande"]["wikimedia"]["n_seeds_vides"],
                    "par_seed": b["demande"]["wikimedia"].get("par_seed", []),
                    "saisonnalite": {str(k): {"indice": round(v, 3), "n": n}
                                     for k, (v, n) in saison.items()},
                    "seuil_saison_nomme": seuil_saison,
                    "autocomplete": b["demande"]["autocomplete"],
                    "trends": b["demande"]["trends"],
                    "note_trends": b["demande"]["note_trends"],
                    "normalise": {"niveau": round(n_niveau[i], 3), "tendance": round(n_pente[i], 3),
                                  "autocomplete": round(n_auto[i], 3)},
                },
                "concurrence": {**b["concurrence"],
                                "normalise": {"rarete": round(n_rarete[i], 3),
                                              "percees": round(n_percees[i], 3),
                                              "pression_velocite": round(n_veloc[i], 3)}},
                "monetisation": b["monetisation"],
                "faisabilite": b["faisabilite"],
                "budgets": {"wikimedia_appels": budget_wiki.utilises,
                            "autocomplete_appels": budget_auto.utilises,
                            "autocomplete_refuses": budget_auto.refuses},
            },
        ))
    notes.sort(key=lambda n: n.score, reverse=True)
    return notes


# ------------------------------------------------------------------ écriture


def enregistrer(conn: sqlite3.Connection, notes: list[Note], *, jour: str | None = None) -> int:
    jour = jour or datetime.now(UTC).date().isoformat()
    maintenant = datetime.now(UTC).isoformat(timespec="seconds")
    for n in notes:
        conn.execute(
            """INSERT INTO niche_scores
               (niche, lang, date, demande, concurrence, monetisation, faisabilite, score,
                top_mois, indice_top, origine, evidence_json, computed_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(niche, lang, date) DO UPDATE SET
                 demande=excluded.demande, concurrence=excluded.concurrence,
                 monetisation=excluded.monetisation, faisabilite=excluded.faisabilite,
                 score=excluded.score, top_mois=excluded.top_mois,
                 indice_top=excluded.indice_top, origine=excluded.origine,
                 evidence_json=excluded.evidence_json, computed_at=excluded.computed_at""",
            (n.niche, n.lang, jour, n.demande, n.concurrence, n.monetisation, n.faisabilite,
             n.score, ",".join(f"{m:02d}" for m in n.top_mois), n.indice_top, n.origine,
             json.dumps(n.evidence, ensure_ascii=False), maintenant),
        )
    conn.commit()
    return len(notes)


def _fmt(v, n=0, defaut="—"):
    if v is None:
        return defaut
    return f"{v:,.{n}f}".replace(",", " ")


def _saison_txt(note: Note) -> str:
    """Les mois nommables, ou un tiret. Un tiret veut dire « aucun mois ne se détache »."""
    if not note.top_mois:
        return "—"
    saison = note.evidence["demande"]["saisonnalite"]
    return ", ".join(f"{MOIS_FR[m]} ({saison[str(m)]['indice']:.2f})" for m in note.top_mois)


def lignes_de_lecture(note: Note) -> list[str]:
    """Trois lignes par niche du top 5 : demande, concurrence, ce qui décide."""
    d, c = note.evidence["demande"], note.evidence["concurrence"]
    mon, fai = note.evidence["monetisation"] or {}, note.evidence["faisabilite"] or {}
    pente = d["pente_mensuelle"]
    pente_txt = (
        f"pente non significative (aucun seed à r² ≥ {d.get('r2_minimal', 0.3)})"
        if pente is None
        else f"{pente * 100:+.1f} %/mois sur {d.get('pente_n_seeds', 0)} seed(s) ajusté(s)"
    )
    veloc = c["velocite_mediane_brute"]
    part = c["part_percees_brute"]
    sans_donnee = (f", {d['n_seeds_sans_donnee']} sans donnée"
                   if d["n_seeds_sans_donnee"] else "")
    sous_plancher = ("" if c["assez_de_donnees"]
                     else f" **Sous le plancher ({c['plancher']}) : non notée.**")
    return [
        (f"**Demande** — {_fmt(d['niveau_vues_mensuelles'])} vues Wikipédia par mois "
         f"(médiane des {d['n_seeds']} articles qui répondent{sans_donnee}), {pente_txt} ; "
         f"{d['autocomplete']['diversite']} sujets distincts à l'autocomplete "
         "(non documenté, saturé à 10 suggestions par mot-clé)."),
        (f"**Concurrence** — {c['n_chaines_actives']} chaîne(s) active(s) sur "
         f"{c['n_chaines_total']} suivie(s), {c['n_videos']} vidéos ; pression de vélocité "
         f"{_fmt(veloc)} vues/j sur {c['n_videos_recentes']} vidéo(s) de moins de 30 j ; "
         f"percées {('%.0f %%' % (part * 100)) if part is not None else '—'} "
         f"({c['n_videos_notees']} vidéos notées, {c['portee']}).{sous_plancher}"),
        (f"**Décide** — monétisation {mon.get('note', '—')}/5, fiabilité de la bande de "
         f"CPM {mon.get('cpm_fiabilite') or '—'}/5 ({mon.get('resume', 'non renseignée')}) ; "
         f"faisabilité {fai.get('note', '—')}/5 ({fai.get('resume', 'non renseignée')})."),
    ]


def ecrire_rapport(
    notes: list[Note], *, racine: Path | None = None, duree_s: float | None = None,
    config: dict | None = None, objections: str | None = None, jour: str | None = None,
) -> Path:
    racine = racine or racine_projet()
    cfg = config or charger_config(racine)
    reglages = cfg["niche_scoring"]
    poids = reglages["ponderations"]
    jour = jour or datetime.now(UTC).date().isoformat()
    langues = sorted({n.lang for n in notes})

    lignes = [
        "# Niches — classement par demande, concurrence, monétisation, faisabilité",
        "",
        f"Généré le {jour} par `factory editorial niches`"
        + (f" en {duree_s:.1f} s" if duree_s is not None else "") + ".",
        "",
        (f"Pondérations : demande {poids['demande']} · concurrence {poids['concurrence']} · "
         f"monétisation {poids['monetisation']} · faisabilité {poids['faisabilite']}."),
        "",
        ("**Deux échelles, et elles ne se lisent pas pareil.** *Demande* et *concurrence* "
        "sont **relatives** : min-max entre les niches de cette exécution, donc 100 veut "
        "dire « la meilleure des onze » et le retrait d'une niche recalcule les dix "
        "autres — le tableau ne vaut qu'à périmètre constant. *Monétisation* et "
        "*faisabilité* sont **absolues** : `note / 5 × 100`, donc 100 veut dire « note 5 » "
        "et 0 veut dire « aucune note ». Ces deux-là pèsent 40 % du composite."),
        "",
        ("**Langue.** Une seule, l'anglais : la production est en anglais depuis la décision "
         "d'Alek du 15/09/2026 (`ROADMAP.md` § 3.1). La colonne `lang` existe dans "
         "`niche_scores` et la commande accepte `--lang`, mais aucun score n'est produit pour "
         "fr/es/it — aucune bande de CPM n'y est documentée, et rien ne serait produit dans "
         "ces langues. Les chaînes FR, ES et IT du registre restent des sources de veille."),
        "",
    ]

    for lang in langues:
        du_lang = [n for n in notes if n.lang == lang]
        lignes += [
            f"## Classement — {lang}", "",
            ("| # | niche | origine | score | demande | concurrence | monétisation "
            "| faisabilité | 3 meilleurs mois |"),
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for i, n in enumerate(du_lang, 1):
            marque = " ⛔" if n.eliminatoire else ""
            lignes.append(
                f"| {i} | `{n.niche}`{marque} | {n.origine} | **{n.score:.0f}** | "
                f"{n.demande:.0f} | {n.concurrence:.0f} | {n.monetisation:.0f} | "
                f"{n.faisabilite:.0f} | {_saison_txt(n)} |"
            )

        ecart = poids["monetisation"] / 5 * 100 / sum(poids.values())
        ecart_f = poids["faisabilite"] / 5 * 100 / sum(poids.values())
        tete = du_lang[0].score - du_lang[1].score if len(du_lang) > 1 else None
        lignes += ["", ("**Sensibilité — à lire avant le classement.** Un cran de note de "
                   f"monétisation (1 point sur 5) déplace le composite de **{ecart:.1f}**, "
                   f"un cran de faisabilité de **{ecart_f:.1f}**.")]
        if tete is not None and tete < max(ecart, ecart_f):
            lignes.append(
                f"L'écart entre le rang 1 et le rang 2 est de **{tete:.1f}** : il est plus "
                "petit qu'un seul cran de note humaine. **Les deux premières niches ne sont "
                "pas départagées par ces données** ; les classer dans cet ordre serait "
                "prêter à la mesure une précision qu'elle n'a pas."
            )
        lignes.append("")

        elimines = [n for n in du_lang if n.eliminatoire]
        if elimines:
            lignes += [("**⛔ Niches éliminatoires — notées, pas ouvrables.** Leur score est "
                       "affiché pour montrer ce qu'elles vaudraient si l'obstacle tombait ; "
                       "il ne les autorise pas."), ""]
            for n in elimines:
                lignes.append(f"- **`{n.niche}`** — {n.motif_eliminatoire}")
            lignes.append("")

        notables = [n for n in du_lang if not n.eliminatoire]
        lignes += [f"### Lecture du top 5 — {lang}", ""]
        for i, n in enumerate(notables[:5], 1):
            lignes.append(f"**{i}. `{n.niche}`** ({n.origine})")
            lignes += [f"- {l}" for l in lignes_de_lecture(n)]
            lignes.append("")

        candidates = [n for n in du_lang if n.origine == "candidate"]
        if candidates:
            lignes += [f"### Candidates hors registre — {lang}", "",
                       ("Trois niches que **le registre ne contient pas** : elles sortent des percées "
                       "de l'entrepôt (titres, pas chaînes) et sont notées à la même grille. Leur "
                       "concurrence est mesurée par **proxy lexical** sur les titres des 74 chaînes "
                       "suivies — c'est un sous-ensemble de chaînes existantes, pas un recensement "
                       "du marché : le chiffre sous-estime la concurrence réelle, et c'est le biais "
                       "le plus lourd de ce rapport."), ""]
            for n in candidates:
                c = n.evidence["concurrence"]
                lignes.append(
                    f"- **`{n.niche}`** — score {n.score:.1f} (rang "
                    f"{du_lang.index(n) + 1}/{len(du_lang)}) · {c['n_videos']} vidéos repérées chez "
                    f"{c['n_chaines_total']} chaînes · "
                    f"{n.evidence['demande']['n_seeds']} articles Wikipédia · "
                    f"{(n.evidence['demande']['par_seed'] or [{}])[0].get('article', '—')} en tête."
                )
            lignes.append("")

    if not dm.contact_renseigne():
        lignes += [
            ("> **`FACTORY_CONTACT` est vide.** La politique Wikimedia exige un contact "
            "joignable dans le User-Agent ; sans lui la limite tombe de 200 à 10 req/min. "
            "Mesuré le 20/09/2026 : la première exécution a mis **256 s** pour 85 articles, "
            "contre 4 s une fois le cache chaud. Action de Thomas, une ligne dans `.env`."),
            "",
        ]

    debut_ts, fin_ts = dm.mois_complets(
        datetime.fromisoformat(jour).date(), reglages["demande"]["fenetre_mois"]
    )
    lignes += ["## Preuves", "",
               ("Chaque ligne de `niche_scores` porte son `evidence_json` : vues mensuelles par "
               "article, pente, indice de saisonnalité mois par mois, suggestions YouTube, "
               "chaînes actives nommées, seuils appliqués. Exemple d'appel :"), "",
               "```", f'curl -H "User-Agent: {dm.user_agent()}" \\',
               (f'  "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/'
                f'{langues[0]}.wikipedia/all-access/user/True_crime/monthly/'
                f'{debut_ts}/{fin_ts}"'), "```", "",
               "Pour lire les preuves d'une niche :", "",
               "```",
               "sqlite3 workspace/factory.db \"select evidence_json from niche_scores \\",
               "  where niche='true_crime' and date=(select max(date) from niche_scores);\" \\",
               "  | python3 -m json.tool", "```", ""]

    lignes += ["## Limites des données", ""]
    lignes += [f"- {l}" for l in reglages["limites"]]
    lignes.append("")

    inscrites = reglages.get("objections") or []
    if inscrites:
        appliquees = sum(1 for o in inscrites if o["statut"].startswith("appliquée"))
        lignes += [
            "## Objections",
            "",
            (f"Contradicteur du {jour}, {len(inscrites)} objections : **{appliquees} "
            f"appliquées**, {len(inscrites) - appliquees} écartées avec motif. Les "
            "corrections appliquées sont dans le classement ci-dessus, pas en note de bas "
            "de page : le tableau qu'on lit est celui d'après."),
            "",
            "| Problème | Correction | Statut |",
            "|---|---|---|",
        ]
        for o in inscrites:
            probleme = " ".join(o["probleme"].split())
            correction = " ".join(o["correction"].split())
            lignes.append(f"| {probleme} | {correction} | {o['statut']} |")
        lignes.append("")

    if objections:
        lignes += ["### Objections restées ouvertes", "", objections, ""]

    chemin = racine / "reports" / "niches.md"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text("\n".join(lignes), encoding="utf-8")
    return chemin


def executer(
    conn: sqlite3.Connection, *, lang: str = "en", racine: Path | None = None, echo=None,
) -> tuple[list[Note], Path, float]:
    debut = time.monotonic()
    cfg = charger_config(racine)
    notes = noter(conn, lang=lang, racine=racine, config=cfg, echo=echo)
    enregistrer(conn, notes)
    duree = time.monotonic() - debut
    chemin = ecrire_rapport(notes, racine=racine, duree_s=duree, config=cfg)
    return notes, chemin, duree
