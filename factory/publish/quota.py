"""Comptabilité du quota des API YouTube — par jour, par projet, par compartiment.

Trois points méritent d'être lus avant d'y toucher.

- **Le quota n'est pas une seule monnaie.** Depuis juin 2026, la dotation d'un projet est
  « 100 `search.list` calls, 100 `videos.insert` calls, and 10,000 units per day combined for
  all other endpoints » (developers.google.com/youtube/v3/getting-started), et
  `videos.insert` coûte « 1 unit in the Video Uploads quota bucket »
  (developers.google.com/youtube/v3/determine_quota_cost). Additionner un upload et une
  lecture donnerait un solde faux dans les deux sens : trop pessimiste sur les unités, aveugle
  sur le compartiment qui sature vraiment. D'où trois compartiments comptés séparément.
- **L'appel est débité avant d'être fait, et il reste débité s'il échoue.** Google facture la
  tentative, pas le succès : un `403 forbidden` sur `captions.insert` coûte ses 400 unités.
  Un ledger qui n'inscrirait que les succès ferait croire à du quota disponible qui ne l'est
  plus, et le refus propre arriverait après le `quotaExceeded`, c'est-à-dire trop tard.
- **Le jour est compté en UTC, Google remet les compteurs à minuit Pacifique.** L'écart est
  connu et assumé : entre minuit UTC et minuit Pacifique, notre compteur est déjà reparti de
  zéro alors que celui de Google ne l'est pas encore. La conséquence est une **sur-estimation
  du disponible pendant ces heures** ; c'est pourquoi les plafonds de configuration sont à
  80 % de ceux de Google (80 uploads sur 100, 8 000 unités sur 10 000) : la marge absorbe le
  décalage. Ne remonte pas ces plafonds sans traiter le fuseau.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from factory.core import config as config_module
from factory.core.paths import racine_projet

#: Coût d'un appel : `(compartiment, unités)`. Vérifié le 22/09/2026 sur
#: developers.google.com/youtube/v3/determine_quota_cost.
#:
#: `reporting` n'est pas un compartiment de la Data API : la Reporting API a son propre quota,
#: que Google ne documente pas en unités. Les appels y sont inscrits au ledger à coût 0 pour
#: garder la trace de ce qui a été demandé, sans prétendre chiffrer ce qu'on ignore.
COUT: dict[str, tuple[str, int]] = {
    "videos.insert": ("uploads", 1),
    "search.list": ("search", 1),
    "videos.update": ("units", 50),
    "videos.list": ("units", 1),
    "thumbnails.set": ("units", 50),
    "captions.insert": ("units", 400),
    "captions.list": ("units", 50),
    "playlistItems.insert": ("units", 50),
    "playlistItems.list": ("units", 1),
    "channels.list": ("units", 1),
    "jobs.create": ("reporting", 0),
    "jobs.list": ("reporting", 0),
    "jobs.delete": ("reporting", 0),
    "reportTypes.list": ("reporting", 0),
    # Étape 25. L'Analytics API a son propre quota (1 unité par requête, plafond lu dans la
    # console GCP, non documenté) : inscrit à 0 dans « reporting » pour compter les appels
    # sans les mêler aux 10 000 unités de la Data API.
    "analytics.reports.query": ("reporting", 0),
    "jobs.reports.list": ("reporting", 0),
    "media.download": ("reporting", 0),
}

#: Dotation de Google, par compartiment. Ce sont **ses** chiffres, pas nos plafonds.
DOTATION: dict[str, int] = {"uploads": 100, "search": 100, "units": 10000}


class QuotaDepasse(RuntimeError):
    """Refus propre : l'appel demandé ferait franchir un plafond. Rien n'a été appelé."""


def aujourdhui() -> str:
    """Jour UTC, `AAAA-MM-JJ`."""
    return datetime.now(UTC).strftime("%Y-%m-%d")


def maintenant() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class Plafonds:
    """Ce que l'usine s'autorise, toujours en deçà de ce que Google autorise."""

    uploads: int = 80
    units: int = 8000
    gcp_project: str = "bms-factory"

    @classmethod
    def depuis_config(cls, racine: Path | None = None) -> Plafonds:
        """Lit `config/orchestrator.yaml` § publication. Aucune valeur en dur ailleurs."""
        cfg = config_module.charger(racine or racine_projet())
        pub = cfg.orchestrator.publication
        return cls(
            uploads=pub.uploads_max_jour,
            units=pub.unites_max_jour,
            gcp_project=pub.gcp_project,
        )


@dataclass(frozen=True)
class EtatQuota:
    """Le solde du jour, compartiment par compartiment."""

    day: str
    gcp_project: str
    uploads_utilises: int
    uploads_max: int
    unites_utilisees: int
    unites_max: int
    inserts: int
    updates: int
    erreurs: int
    appels: int

    @property
    def uploads_restants(self) -> int:
        return max(0, self.uploads_max - self.uploads_utilises)

    @property
    def unites_restantes(self) -> int:
        return max(0, self.unites_max - self.unites_utilisees)

    @property
    def part_unites(self) -> float:
        return self.unites_utilisees / self.unites_max if self.unites_max else 0.0

    @property
    def part_uploads(self) -> float:
        return self.uploads_utilises / self.uploads_max if self.uploads_max else 0.0

    @property
    def part_max(self) -> float:
        """La part du compartiment le plus consommé — celle qui déclenche l'alerte."""
        return max(self.part_unites, self.part_uploads)


def etat(conn: sqlite3.Connection, plafonds: Plafonds | None = None,
         day: str | None = None) -> EtatQuota:
    """Solde du jour, lu dans `quota_ledger` — jamais un compteur tenu en mémoire."""
    plafonds = plafonds or Plafonds()
    jour = day or aujourdhui()
    ligne = conn.execute(
        "SELECT * FROM v_quota_jour WHERE day = ? AND gcp_project = ?",
        (jour, plafonds.gcp_project),
    ).fetchone()
    if ligne is None:
        return EtatQuota(jour, plafonds.gcp_project, 0, plafonds.uploads, 0, plafonds.units,
                         0, 0, 0, 0)
    return EtatQuota(
        day=jour,
        gcp_project=plafonds.gcp_project,
        uploads_utilises=ligne["uploads"] or 0,
        uploads_max=plafonds.uploads,
        unites_utilisees=ligne["units"] or 0,
        unites_max=plafonds.units,
        inserts=ligne["inserts"] or 0,
        updates=ligne["updates"] or 0,
        erreurs=ligne["erreurs"] or 0,
        appels=ligne["appels"] or 0,
    )


def cout(appel: str) -> tuple[str, int]:
    """Compartiment et unités d'un appel. Un appel inconnu est une erreur, pas un zéro."""
    if appel not in COUT:
        raise KeyError(
            f"coût inconnu pour « {appel} » : ajoute-le à quota.COUT avec sa source "
            "(developers.google.com/youtube/v3/determine_quota_cost) plutôt que de le "
            "laisser passer à coût nul"
        )
    return COUT[appel]


def verifier(conn: sqlite3.Connection, appel: str, *, nombre: int = 1,
             plafonds: Plafonds | None = None) -> EtatQuota:
    """Refuse **avant** l'appel si le plafond serait franchi. Rend l'état courant sinon."""
    plafonds = plafonds or Plafonds()
    compartiment, unites = cout(appel)
    courant = etat(conn, plafonds)
    if compartiment == "uploads":
        if courant.uploads_utilises + unites * nombre > plafonds.uploads:
            raise QuotaDepasse(
                f"{appel} refusé : {courant.uploads_utilises} upload(s) déjà faits aujourd'hui "
                f"sur un plafond de {plafonds.uploads} (dotation Google : "
                f"{DOTATION['uploads']}/jour). Reprends demain, ou relève "
                "orchestrator.publication.uploads_max_jour en connaissance de cause."
            )
    elif compartiment == "units":
        if courant.unites_utilisees + unites * nombre > plafonds.units:
            raise QuotaDepasse(
                f"{appel} refusé : il coûte {unites * nombre} unités, il en reste "
                f"{courant.unites_restantes} sur le plafond de {plafonds.units} "
                f"(dotation Google : {DOTATION['units']}/jour). "
                "Le compartiment des lectures est saturé pour aujourd'hui."
            )
    return courant


def consommer(conn: sqlite3.Connection, appel: str, *, video_id: str | None = None,
              channel_id: str | None = None, ok: bool = True, detail: str = "",
              plafonds: Plafonds | None = None, nombre: int = 1) -> int:
    """Inscrit l'appel au ledger et rend son coût. À appeler **avant** l'appel réseau."""
    plafonds = plafonds or Plafonds()
    compartiment, unites = cout(appel)
    conn.execute(
        "INSERT INTO quota_ledger (day, gcp_project, call, compartment, units, video_id, "
        "channel_id, ok, detail, at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (aujourdhui(), plafonds.gcp_project, appel, compartiment, unites * nombre,
         video_id, channel_id, 1 if ok else 0, detail[:500] or None, maintenant()),
    )
    return unites * nombre


def noter_echec(conn: sqlite3.Connection, appel: str, detail: str, *,
                video_id: str | None = None, plafonds: Plafonds | None = None) -> None:
    """Marque en échec la dernière ligne de cet appel, sans changer son coût.

    Le quota reste débité : Google facture la tentative. Seul le verdict change, et c'est lui
    qui permettra de dire « la journée est passée en 403 » plutôt que « la journée a produit ».
    """
    plafonds = plafonds or Plafonds()
    ligne = conn.execute(
        "SELECT id FROM quota_ledger WHERE day = ? AND gcp_project = ? AND call = ? "
        "AND (video_id IS ? OR ? IS NULL) ORDER BY id DESC LIMIT 1",
        (aujourdhui(), plafonds.gcp_project, appel, video_id, video_id),
    ).fetchone()
    if ligne is None:
        return
    conn.execute("UPDATE quota_ledger SET ok = 0, detail = ? WHERE id = ?",
                 (detail[:500], ligne["id"]))


def cout_publication_complete() -> dict[str, int]:
    """Ce que coûte une publication complète, compartiment par compartiment.

    Sert au tableau de bord et à la décision « combien de vidéos tiennent encore aujourd'hui ».
    Sous le modèle de juin 2026, ce n'est **pas** 2 050 unités : l'insert est ailleurs.
    """
    total: dict[str, int] = {"uploads": 0, "units": 0, "reporting": 0, "search": 0}
    for appel in ("videos.insert", "thumbnails.set", "captions.insert",
                  "playlistItems.insert", "videos.list"):
        compartiment, unites = cout(appel)
        total[compartiment] += unites
    return total


def publications_possibles(courant: EtatQuota) -> int:
    """Combien de publications complètes tiennent encore aujourd'hui, sur le solde réel."""
    besoin = cout_publication_complete()
    par_uploads = courant.uploads_restants // besoin["uploads"] if besoin["uploads"] else 10**6
    par_unites = courant.unites_restantes // besoin["units"] if besoin["units"] else 10**6
    return max(0, min(par_uploads, par_unites))
