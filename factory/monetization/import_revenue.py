"""Import des revenus : exports d'affiliation (CSV) et publicité (Analytics API) — étape 27.

Chaque programme a son rapport ; les colonnes sont cherchées par **noms candidats**, sans
tenir compte de la casse. Les formats ci-dessous sont reconstitués d'après la veille du
23/09/2026 : **aucun n'a été vérifié sur un vrai export** (aucun compte ouvert). Le premier
export réel de chaque programme doit être importé une fois à la main pour confirmer les noms ;
une colonne introuvable lève une erreur qui liste les en-têtes lus, jamais un zéro silencieux.

Rattachement : le sous-identifiant est le `video_id` (`sub_id_format: "{video_id}"`) ; l'ancien
format `<channel>_<lang>_<video_id>` est reconnu par suffixe. Amazon ne porte pas de
sous-identifiant ouvert (ascsubtag sur accord seulement) : ses lignes restent non rattachées
à une vidéo, `sub_id` = tracking ID.
"""

from __future__ import annotations

import csv
import hashlib
import io
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

#: Noms candidats par champ et par programme. `sub_id` est le sous-identifiant de la vidéo.
COLONNES: dict[str, dict[str, tuple[str, ...]]] = {
    "amazon": {"sub_id": ("tracking id",), "date": ("date shipped", "date"),
               "amount": ("ad fees($)", "ad fees", "earnings"),
               "conversions": ("items shipped", "qty"), "clicks": ("clicks",)},
    "awin": {"sub_id": ("click ref", "clickref"), "date": ("transaction date", "date"),
             "amount": ("commission amount", "commission"), "currency": ("currency",),
             "status": ("status", "commission status"), "clicks": ("clicks",)},
    "cj": {"sub_id": ("sid",), "date": ("event date", "posting date"),
           "amount": ("publisher commission", "commission amount", "commission"),
           "currency": ("currency", "publisher currency"), "status": ("action status", "status"),
           "clicks": ("clicks",)},
    "impact": {"sub_id": ("subid1", "sub id 1", "subid"), "date": ("action date", "event date"),
               "amount": ("payout", "earnings"), "currency": ("currency",),
               "status": ("status", "action status"), "clicks": ("clicks",)},
    "digistore24": {"sub_id": ("campaignkey", "campaign key", "tracking key"),
                    "date": ("date", "order date"), "amount": ("earnings", "commission"),
                    "currency": ("currency",), "status": ("status",), "clicks": ("clicks",)},
    "clickbank": {"sub_id": ("aff_sub1", "tid", "tracking id"),
                  "date": ("transaction date", "date"),
                  "amount": ("affiliate commission", "amount", "commission"),
                  "currency": ("currency",), "status": ("transaction type", "status"),
                  "clicks": ("clicks",)},
}

#: Devise par défaut quand le rapport n'a pas de colonne devise (Amazon US : dollars).
DEVISE_DEFAUT: dict[str, str] = {"amazon": "USD"}

#: Statuts qui annulent une conversion : ligne ignorée et comptée.
STATUTS_ANNULES = ("declined", "reversed", "rejected", "refund", "rfnd", "chargeback", "cancel")


@dataclass
class BilanImport:
    """Ce que l'import a fait, ligne par ligne."""

    program: str
    lues: int = 0
    inserees: int = 0
    doublons: int = 0
    annulees: int = 0
    non_rattachees: list[str] = field(default_factory=list)
    origin: str = "import"


def _cle(ligne: dict[str, str], candidats: tuple[str, ...]) -> str | None:
    index = {k.strip().lower(): k for k in ligne}
    return next((index[c] for c in candidats if c in index), None)


def _montant(texte: str) -> float:
    brut = (texte or "").replace("$", "").replace("€", "").replace("£", "").replace(" ", "")
    if brut.count(",") == 1 and "." not in brut:
        brut = brut.replace(",", ".")
    return float(brut.replace(",", "") or 0)


def _date(texte: str) -> str:
    brut = (texte or "").strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%m/%d/%Y", "%d/%m/%Y",
                "%m/%d/%Y %H:%M", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(brut[: len(datetime.now().strftime(fmt))], fmt).date().isoformat()
        except ValueError:
            continue
    return brut[:10]


def _lire_csv(fichier: Path) -> list[dict[str, str]]:
    """Lit le CSV ; saute les lignes de titre qu'Amazon met avant l'en-tête."""
    texte = fichier.read_text(encoding="utf-8-sig")
    lignes = texte.splitlines()
    debut = next((i for i, l in enumerate(lignes) if l.count(",") >= 2 or l.count("\t") >= 2), 0)
    corps = "\n".join(lignes[debut:])
    separateur = "\t" if corps.split("\n", 1)[0].count("\t") > corps.split("\n", 1)[0].count(",") else ","
    return list(csv.DictReader(io.StringIO(corps), delimiter=separateur))


def resoudre(sub_id: str | None, runs: dict[str, str]) -> tuple[str | None, str | None]:
    """`(video_id, channel_id)` d'un sous-identifiant ; `(None, None)` s'il est inconnu."""
    if not sub_id:
        return None, None
    if sub_id in runs:
        return sub_id, runs[sub_id]
    suffixes = [v for v in runs if sub_id.endswith("_" + v)]
    if suffixes:
        video = max(suffixes, key=len)
        return video, runs[video]
    return None, None


def importer(conn: sqlite3.Connection, program: str, fichier: Path,
             origin: str = "import") -> BilanImport:
    """Importe un export de programme dans `revenue`. Idempotent (clé = empreinte de ligne)."""
    if program not in COLONNES:
        raise ValueError(f"programme inconnu : {program} (connus : {', '.join(COLONNES)})")
    lignes = _lire_csv(fichier)
    bilan = BilanImport(program=program, origin=origin)
    if not lignes:
        return bilan
    cols = COLONNES[program]
    trouvees = {champ: _cle(lignes[0], cands) for champ, cands in cols.items()}
    manquantes = [c for c in ("sub_id", "date", "amount") if trouvees.get(c) is None]
    if manquantes:
        raise ValueError(
            f"{program} : colonnes introuvables {manquantes} ; en-têtes lus : "
            f"{list(lignes[0])}. Compléter COLONNES['{program}'] après vérification."
        )
    runs = {r["video_id"]: r["channel_id"]
            for r in conn.execute("SELECT video_id, channel_id FROM runs")}
    maintenant = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    for ligne in lignes:
        bilan.lues += 1
        statut = (ligne.get(trouvees["status"]) or "").lower() if trouvees.get("status") else ""
        if any(a in statut for a in STATUTS_ANNULES):
            bilan.annulees += 1
            continue
        sub_id = (ligne.get(trouvees["sub_id"]) or "").strip() or None
        video_id, channel_id = (None, None) if program == "amazon" else resoudre(sub_id, runs)
        if video_id is None:
            bilan.non_rattachees.append(sub_id or "(vide)")
        conv_col = trouvees.get("conversions")
        clic_col = trouvees.get("clicks")
        empreinte = hashlib.sha256(
            (program + "|" + "|".join(f"{k}={ligne[k]}" for k in sorted(ligne))).encode()
        ).hexdigest()
        curseur = conn.execute(
            "INSERT OR IGNORE INTO revenue (video_id, channel_id, source, program, date, clicks,"
            " conversions, amount, currency, imported_at, sub_id, origin, row_key)"
            " VALUES (?, ?, 'affiliate', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (video_id, channel_id, program, _date(ligne[trouvees["date"]]),
             int(float(ligne[clic_col])) if clic_col and ligne.get(clic_col) else None,
             int(float(ligne[conv_col])) if conv_col and ligne.get(conv_col) else 1,
             _montant(ligne[trouvees["amount"]]),
             ((ligne.get(trouvees["currency"]) if trouvees.get("currency") else None)
              or DEVISE_DEFAUT.get(program, "EUR")).strip().upper(),
             maintenant, sub_id, origin, empreinte),
        )
        if curseur.rowcount:
            bilan.inserees += 1
        else:
            bilan.doublons += 1
    return bilan


# --------------------------------------------------------------------------------------
# Publicité : estimatedRevenue (Analytics API)
# --------------------------------------------------------------------------------------

SCOPE_MONETAIRE = "https://www.googleapis.com/auth/yt-analytics-monetary.readonly"


@dataclass
class BilanAds:
    """Résultat de `pull-ads` pour une chaîne."""

    channel: str
    statut: str          # ok | sans_jeton | scope_absent | non_monetisee | erreur | rien_publie
    message: str
    lignes: int = 0


def tirer_ads(conn: sqlite3.Connection, racine: Path, jours: int = 90,
              channels: list[str] | None = None) -> list[BilanAds]:
    """`estimatedRevenue` par vidéo publiée et par jour (`filters=video==ID`, dimension `day`).

    La métrique exige le scope monétaire **et** une chaîne monétisée (YPP) ; un refus de l'API
    est rendu tel quel dans le message, jamais converti en revenu nul.
    """
    from factory.publish import oauth

    pubs = conn.execute(
        "SELECT video_id, channel_id, youtube_video_id FROM publications"
        " WHERE youtube_video_id IS NOT NULL").fetchall()
    connues = sorted({p["channel_id"] for p in pubs} | set(channels or []))
    if channels:
        connues = [c for c in connues if c in channels]
    if not connues:
        return [BilanAds("—", "rien_publie",
                         "aucune vidéo publiée (table publications vide) : aucun revenu "
                         "publicitaire à tirer")]
    bilans: list[BilanAds] = []
    fin = date.today()
    debut = fin - timedelta(days=jours)
    for channel in connues:
        etat = oauth.etat_jeton(channel, racine)
        if not etat.get("present"):
            bilans.append(BilanAds(channel, "sans_jeton",
                                   f"aucun jeton OAuth (secrets/tokens/{channel}.json) : "
                                   f"`factory publish auth --channel {channel}` d'abord"))
            continue
        if SCOPE_MONETAIRE not in (etat.get("scopes") or []):
            bilans.append(BilanAds(channel, "scope_absent",
                                   "le jeton n'a pas le scope yt-analytics-monetary.readonly : "
                                   "refaire `factory publish auth`"))
            continue
        api = oauth.service(channel, "youtubeAnalytics", "v2", racine=racine)
        maintenant = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        n = 0
        try:
            for pub in (p for p in pubs if p["channel_id"] == channel):
                rep = api.reports().query(
                    ids="channel==MINE", startDate=debut.isoformat(), endDate=fin.isoformat(),
                    metrics="estimatedRevenue", dimensions="day",
                    filters=f"video=={pub['youtube_video_id']}", sort="day").execute()
                for jour, montant in rep.get("rows", []) or []:
                    conn.execute(
                        "INSERT INTO revenue (video_id, channel_id, source, program, date, amount,"
                        " currency, imported_at, origin, row_key)"
                        " VALUES (?, ?, 'ads', 'youtube', ?, ?, 'USD', ?, 'api', ?)"
                        " ON CONFLICT(row_key) DO UPDATE SET amount = excluded.amount,"
                        " imported_at = excluded.imported_at",
                        (pub["video_id"], channel, jour, float(montant), maintenant,
                         f"ads|{pub['video_id']}|{jour}"))
                    n += 1
        except Exception as erreur:  # noqa: BLE001 — HttpError : le message de l'API est la preuve
            texte = str(erreur)
            statut = "non_monetisee" if "403" in texte or "Forbidden" in texte else "erreur"
            bilans.append(BilanAds(channel, statut,
                                   ("refus de l'API — chaîne hors YPP ou non monétisée "
                                    if statut == "non_monetisee" else "") + texte[:300], n))
            continue
        bilans.append(BilanAds(channel, "ok", f"{n} jour(s) × vidéo lus", n))
    return bilans
