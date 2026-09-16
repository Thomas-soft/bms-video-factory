"""`factory plan` — choix du sujet et création du run.

Le sujet ne vient jamais du hasard : il est pris dans `sujets_porteurs` de la niche, dans
l'ordre de classement de l'étape 3, en sautant ceux qu'une chaîne de la même langue a déjà
traités. `--topic` reste possible, mais il est tracé `source = "manuel"` et sans preuve.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

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


def _point_extension_file_sujets(channel_id: str) -> list[dict] | None:
    """File de sujets éditoriale — branchée à l'étape 20, vide ici.

    L'étape 20 remplacera ce corps par la lecture de `workspace/topics_queue.json`
    (`config/editorial.yaml` → `topics_queue`). Le contrat est déjà fixé : renvoyer une liste
    de sujets notés, la plus haute d'abord, ou `None` pour laisser la main au référentiel.
    Tant qu'elle renvoie `None`, `source` ne peut valoir que `referentiel` ou `manuel`.
    """
    return None


def _choisir_sujet(
    channel_id: str, lang: str, nom_niche: str, pris: set[str], racine: Path | None
) -> tuple[Topic, int]:
    """Premier sujet porteur non encore employé par cette chaîne ni par sa langue."""
    file_editoriale = _point_extension_file_sujets(channel_id)
    if file_editoriale:  # étape 20
        raise NotImplementedError("file de sujets éditoriale : étape 20")

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
        )
    raise ValueError(
        f"niche {nom_niche} : les {len(candidats)} sujets porteurs sont déjà employés "
        f"par {channel_id} ou par une chaîne en {lang} — l'étape 20 doit alimenter la file"
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
        ecartes = 0
    else:
        pris = runs.sujets_deja_pris(conn, channel.id, channel.lang)
        sujet, ecartes = _choisir_sujet(channel.id, channel.lang, channel.niche, pris, racine)

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

    gabarit = channel.templates[seed % len(channel.templates)]
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
    manifest.conformite.paid_promotion = bool(produit)
    manifest.conformite.publish_path = channel.publish_path  # type: ignore[assignment]
    manifest.execution.run_state = "running"

    chemins = RunPaths.depuis_video_id(video_id, racine).creer()
    runs.ecrire_json(chemins.spec, spec)
    secondes = time.perf_counter() - t0
    manifest.execution.timings["plan"] = round(secondes, 2)
    runs.ecrire_json(chemins.manifest, manifest)
    runs.enregistrer(conn, spec, manifest, racine)
    conn.close()
    return ResultatPlan(spec, manifest, chemins, secondes, alertes, ecartes)
