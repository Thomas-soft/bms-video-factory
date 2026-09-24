"""`factory plan` — choix du sujet et création du run.

Le sujet ne vient jamais du hasard. Trois sources, dans cet ordre, et la première qui
rend quelque chose gagne :

  1. **`topics_queue`** (étape 20) — le meilleur sujet `proposed` ou `approved` de la
     chaîne, non repris par une chaîne de la même langue, et à similarité inférieure au
     seuil avec les sujets récents de BMS. La preuve du choix est recopiée telle quelle
     dans `spec.json`.
  2. **`REFERENTIEL.json`** — les `sujets_porteurs` de la niche, dans l'ordre de
     classement de l'étape 3.
  3. **`--topic`** — tracé `source = "manuel"`, sans preuve, par construction.

La règle anti-clonage (`CONFORMITE` § 5) s'applique aux trois : deux chaînes de même
langue ne traitent jamais le même sujet.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from factory.core import config as config_module
from factory.core import db, referentiel, runs
from factory.core.models import (
    ManifestDecisions,
    ManifestIdentite,
    RunManifest,
    Topic,
    TopicEvidence,
    VideoSpec,
)
from factory.core.paths import RunPaths


@dataclass
class ResultatPlan:
    """Ce que `plan` a produit, pour le journal et la CLI."""

    spec: VideoSpec
    manifest: RunManifest
    chemins: RunPaths
    secondes: float
    alertes: list[str]
    sujets_ecartes: int


def _seuil_similarite(racine: Path | None) -> float:
    """Seuil de proximité au-delà duquel un sujet de file est considéré déjà traité.

    Lu dans `config/editorial.yaml` → `topics.malus_similarite.seuil`. Le même nombre
    sert de malus à la notation (étape 20) et de refus ici : deux seuils différents pour
    la même notion donneraient deux vérités.
    """
    import yaml

    from factory.core.paths import dossier_config

    chemin = dossier_config(racine) / "editorial.yaml"
    if not chemin.exists():
        return 0.80
    cfg = yaml.safe_load(chemin.read_text(encoding="utf-8")) or {}
    return float((cfg.get("topics") or {}).get("malus_similarite", {}).get("seuil", 0.80))


def _niche_de(conn, channel_id: str, racine: Path | None) -> str | None:
    try:
        return config_module.charger(racine, strict=False).get_channel(channel_id).niche
    except Exception:  # noqa: BLE001 — la niche ne sert qu'au multiplicateur appris
        return None


def classer_file(conn, channel_id: str, niche: str | None, racine: Path | None,
                 poids: dict[str, Any] | None | bool = True) -> list[dict[str, Any]] | None:
    """Sujets libres de la file, classés : `approved` d'abord, puis score × multiplicateur appris.

    `poids=True` lit `learned/weights.json` ; `None`/`False` force le classement de l'étape 20.
    Rend `None` si la table n'existe pas.
    """
    from factory.analytics import weights as wmod
    from factory.editorial import topics as topics_module

    if poids is True:
        poids = wmod.charger(racine)
    try:
        lignes = conn.execute(
            """SELECT id, topic, angle, score, evidence_json, status
                 FROM topics_queue
                WHERE channel_id = ? AND status IN ('proposed', 'approved')
                  AND used_by_run IS NULL""",
            (channel_id,),
        ).fetchall()
    except sqlite3.OperationalError:
        return None  # migration 006 non appliquée : la file n'existe pas encore
    sortie = []
    for topic_id, sujet, angle, score, evidence_json, statut in lignes:
        cluster = (json.loads(evidence_json) if evidence_json else {}).get("cluster_id")
        mult = topics_module.multiplicateur_appris(poids or None, cluster, niche)
        sortie.append({"id": topic_id, "topic": sujet, "angle": angle, "score": score,
                       "evidence_json": evidence_json, "status": statut, "cluster": cluster,
                       "multiplier": mult, "score_adjusted": (score or 0.0) * mult})
    sortie.sort(key=lambda x: (x["status"] != "approved", -x["score_adjusted"], x["id"]))
    return sortie


def _sujet_depuis_file(
    conn, channel_id: str, lang: str, pris: set[str], racine: Path | None
) -> tuple[Topic, int, int | None] | None:
    """Meilleur sujet de `topics_queue` pour cette chaîne, ou `None` si la file est vide.

    Trois filtres, dans l'ordre du coût : statut, sujet déjà pris par la langue, puis
    similarité aux sujets récents de BMS — cette dernière charge le modèle d'embeddings
    et n'est donc évaluée que sur les candidats qui ont passé les deux premières.
    """
    lignes = classer_file(conn, channel_id, _niche_de(conn, channel_id, racine), racine)
    if lignes is None or not lignes:
        return None
    lignes = [(x["id"], x["topic"], x["angle"], x["score"], x["evidence_json"]) for x in lignes]

    ecartes = 0
    candidats = []
    for ligne in lignes:
        if str(ligne[1]).strip().lower() in pris:
            ecartes += 1
            continue
        candidats.append(ligne)
    if not candidats:
        return None

    recents = sorted(
        {
            s.strip()
            for (s,) in conn.execute(
                "SELECT topic_sujet FROM runs WHERE topic_sujet IS NOT NULL AND lang = ?",
                (lang,),
            )
            if s and s.strip()
        }
    )
    if recents:
        from factory.editorial import embed as em

        seuil = _seuil_similarite(racine)
        vec_recents = em.embed(recents, racine=racine)
        vec_candidats = em.embed([str(c[1]) for c in candidats], racine=racine)
        retenus = []
        for ligne, vec in zip(candidats, vec_candidats, strict=True):
            if max(em.similarite(vec, r) for r in vec_recents) >= seuil:
                ecartes += 1
                continue
            retenus.append(ligne)
        candidats = retenus
        if not candidats:
            return None

    topic_id, sujet, angle, score, evidence_json = candidats[0]
    preuve = json.loads(evidence_json) if evidence_json else {}
    evidence = TopicEvidence(
        score=score,
        ratio=(preuve.get("videos_sources") or [{}])[0].get("ratio"),
        n=preuve.get("n_videos"),
        requete=(
            f"topics_queue#{topic_id} — cluster {preuve.get('cluster_id')} "
            f"« {preuve.get('label')} », {preuve.get('n_videos')} vidéos / "
            f"{preuve.get('n_chaines')} chaînes / {preuve.get('n_percees')} percées, "
            f"lacune {preuve.get('gap_type') or 'aucune'}"
        ),
    )
    return (
        Topic(sujet=str(sujet)[:200], angle=str(angle), source="topics_queue",
              evidence=evidence),
        ecartes,
        int(topic_id),
    )


def _choisir_sujet(
    channel_id: str, lang: str, nom_niche: str, pris: set[str], racine: Path | None,
    conn=None,
) -> tuple[Topic, int, int | None]:
    """File de sujets d'abord, référentiel ensuite. Rend aussi l'id de file consommé."""
    if conn is not None:
        depuis_file = _sujet_depuis_file(conn, channel_id, lang, pris, racine)
        if depuis_file is not None:
            return depuis_file

    candidats = referentiel.sujets_porteurs(nom_niche, racine)
    if not candidats:
        raise ValueError(f"niche {nom_niche} : aucun sujet porteur dans REFERENTIEL.json")
    ecartes = 0
    for rang, entree in enumerate(candidats):
        sujet = str(entree["sujet"]).strip()
        if sujet.lower() in pris:
            ecartes += 1
            continue
        evidence = TopicEvidence(
            vues_medianes_chaine=entree.get("vues_medianes_chaine"),
            ratio=entree.get("ratio_vs_mediane"),
            n=rang + 1,
            requete=(
                f"REFERENTIEL.json niches.{nom_niche}.sujets_porteurs[{rang}] — "
                f"{entree.get('chaine')} / {entree.get('video_id')}, {entree.get('vues')} vues"
            ),
        )
        return (
            Topic(sujet=sujet[:200], angle="à définir par la recherche", source="referentiel",
                  evidence=evidence),
            ecartes,
            None,
        )
    raise ValueError(
        f"niche {nom_niche} : les {len(candidats)} sujets porteurs sont déjà employés "
        f"par {channel_id} ou par une chaîne en {lang}, et `topics_queue` ne rend aucun "
        f"sujet libre — relancer `factory editorial topics --channel {channel_id}`"
    )


def executer(
    channel_id: str,
    topic: str | None = None,
    product_id: str | None = None,
    racine: Path | None = None,
) -> ResultatPlan:
    """Crée le run : sujet, dossier, `spec.json`, `manifest.json`, ligne en base."""
    t0 = time.perf_counter()
    alertes: list[str] = []
    cfg = config_module.charger(racine, strict=False)
    channel = cfg.get_channel(channel_id)
    niche_cfg = cfg.niches.get(channel.niche)
    if niche_cfg is None:
        raise KeyError(f"niche {channel.niche} absente de config/niches/")

    conn = db.ouvrir(None if racine is None else racine / "workspace" / "factory.db")
    db.migrer(conn)

    if topic:
        sujet = Topic(sujet=topic.strip()[:200], angle="à définir par la recherche", source="manuel")
        ecartes, topic_id = 0, None
    else:
        pris = runs.sujets_deja_pris(conn, channel.id, channel.lang)
        sujet, ecartes, topic_id = _choisir_sujet(
            channel.id, channel.lang, channel.niche, pris, racine, conn=conn
        )

    produit = product_id or (channel.products[0] if channel.products else None)
    if produit and produit not in cfg.products:
        raise KeyError(f"produit inconnu : {produit}")

    cible_duree = int(round(niche_cfg.duree_s.cible))
    if getattr(niche_cfg.duree_s, "distribution_large", False):
        alertes.append(
            f"niche {channel.niche} : durées très dispersées (p75/p25 > 4). La cible retenue est "
            f"la médiane de niche ({cible_duree} s) faute de champ de durée par chaîne. "
            "REFERENTIEL.md § 2 demande une durée fixée par chaîne — à trancher par Thomas."
        )
    rythme = cfg.cible_rythme(channel)
    if getattr(niche_cfg.rythme_coupe_s, "a_mesurer", False):
        alertes.append(
            f"niche {channel.niche} : rythme de coupe non mesuré, repli provisoire {rythme} s"
        )

    seed = config_module.nouvelle_graine()
    video_id = config_module.attribuer_video_id(channel.id, seed, racine=racine, conn=conn)
    spec = VideoSpec(
        video_id=video_id, parent_id=None, channel_id=channel.id, lang=channel.lang,
        niche=channel.niche, style=channel.style, topic=sujet,
        target_duration_s=cible_duree, cut_rhythm_target_s=rythme, seed=seed,
        product_id=produit, created_at=runs.maintenant(),
    )
    problemes = config_module.verifier_spec(spec, cfg)
    bloquants = [p for p in problemes if p.niveau == "erreur"]
    if bloquants:
        raise ValueError("spec.json refusé : " + " ; ".join(p.message for p in bloquants))
    alertes += [p.message for p in problemes if p.niveau != "erreur"]

    # Rotation (étape 29) : le suivant du dernier run, plus un tirage par graine.
    gabarit = runs.gabarit_suivant(conn, channel.id, list(channel.templates))
    manifest = RunManifest(
        identite=ManifestIdentite(
            video_id=video_id, parent_id=None, channel_id=channel.id, lang=channel.lang,
            niche=channel.niche, style=channel.style, template_id=gabarit,
            charte_version=channel.charte.version,
        ),
        decisions=ManifestDecisions(
            topic=sujet, hook_type="a_tirer", cut_rhythm_target_s=rythme,
            voice_id=channel.voice_id,
        ),
    )
    from factory.analytics import weights as wmod
    from factory.editorial import topics as topics_module

    poids = wmod.charger(racine)
    cluster = None
    if sujet.source == "topics_queue" and sujet.evidence and sujet.evidence.requete:
        cluster = sujet.evidence.requete.split("cluster ")[-1].split(" ")[0]
    wmod.noter(manifest, poids, "topic_multiplier",
               topics_module.multiplicateur_appris(poids, cluster, channel.niche))
    manifest.conformite.paid_promotion = bool(produit)
    manifest.conformite.publish_path = channel.publish_path  # type: ignore[assignment]
    manifest.execution.run_state = "running"

    chemins = RunPaths.depuis_video_id(video_id, racine).creer()
    runs.ecrire_json(chemins.spec, spec)
    secondes = time.perf_counter() - t0
    manifest.execution.timings["plan"] = round(secondes, 2)
    runs.ecrire_json(chemins.manifest, manifest)
    runs.enregistrer(conn, spec, manifest, racine)
    if topic_id is not None:
        # La ligne passe à `used` **après** l'écriture du run : si `plan` échoue plus haut,
        # le sujet reste disponible pour le prochain appel plutôt que d'être perdu.
        conn.execute(
            "UPDATE topics_queue SET status = 'used', used_by_run = ? WHERE id = ?",
            (video_id, topic_id),
        )
        conn.commit()
    conn.close()
    return ResultatPlan(spec, manifest, chemins, secondes, alertes, ecartes)


def apercu(channel_id: str, n: int = 10, racine: Path | None = None,
           avec_poids: bool = True) -> list[dict[str, Any]]:
    """`factory plan --dry-run` : les n prochains sujets de la file, sans créer de run.

    Mêmes filtres que `executer` (statut, sujet déjà pris par la langue), **sauf** la
    similarité aux sujets récents, qui charge le modèle d'embeddings et ne dépend pas des
    poids appris.
    """
    cfg = config_module.charger(racine, strict=False)
    channel = cfg.get_channel(channel_id)
    conn = db.ouvrir(None if racine is None else racine / "workspace" / "factory.db")
    try:
        pris = runs.sujets_deja_pris(conn, channel.id, channel.lang)
        lignes = classer_file(conn, channel.id, channel.niche, racine,
                              True if avec_poids else None) or []
    finally:
        conn.close()
    return [x for x in lignes if str(x["topic"]).strip().lower() not in pris][:n]
