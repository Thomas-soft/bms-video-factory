"""Signaux de demande gratuits : Wikimedia Pageviews, autocomplete YouTube, Trends.

Trois sources, trois statuts très différents, et le code ne les mélange jamais :

  - **Wikimedia Pageviews** (REST v1) — officielle, gratuite, CC0, multilingue.
    C'est la seule source *chiffrée* du module. Politique d'agent utilisateur
    obligatoire : un User-Agent identifiant donne 200 req/min, un User-Agent
    générique fait tomber la limite à 10 (vérifié le 20/09/2026).
  - **Autocomplete YouTube** (`suggestqueries.google.com`) — **non documenté**,
    hors de toutes conditions d'utilisation explicites. Il ne donne aucun volume,
    seulement un *ordre* de suggestions. Employé comme signal qualitatif, plafonné
    à `max_appels_par_execution`, et derrière un cache pour survivre à sa
    disparition. Tout ce qui en sort porte `source: "non documenté"`.
  - **Google Trends** — l'API officielle est en alpha sur candidature depuis
    07/2025 ; aucune clé en self-service. `trendspy` tape les points d'entrée
    internes de Google (429 fréquents, zone grise contractuelle) et est écarté.
    La fonction existe, renvoie `None` et une note : un champ nul documenté vaut
    mieux qu'un chiffre d'une source instable.

Conformité (docs/CONFORMITE.md) : aucune page HTML n'est aspirée, aucun navigateur
n'est piloté, aucune source payante n'est appelée.
"""

from __future__ import annotations

import json
import math
import os
import re
import statistics
import time
import unicodedata
import urllib.parse
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path

import requests

from factory.core.paths import dossier_workspace
from factory.core.secrets import charger_env

# --------------------------------------------------------------------- réglages

WIKIMEDIA_REST = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
WIKIPEDIA_API = "https://{projet}/w/api.php"
AUTOCOMPLETE = "https://suggestqueries.google.com/complete/search"

TIMEOUT_S = 20
#: La documentation Wikimedia annonce 200 req/min avec un User-Agent conforme.
#: **Mesuré le 20/09/2026 : faux.** Le REST des pageviews renvoie des 429 bien avant,
#: sur une poignée d'appels par seconde depuis une IP résidentielle. Une seconde de
#: pause tient, et le cache disque fait que le prix n'est payé qu'une fois par mois.
PAUSE_S = 1.0
TENTATIVES = 4

#: Durée de validité du cache, par source. Les vues mensuelles de Wikimedia ne
#: bougent plus une fois le mois clos ; la clé de cache porte déjà la plage de
#: mois, donc un nouveau mois crée une entrée neuve. 30 jours suffisent.
TTL_JOURS = {"wikimedia": 30, "wikipedia_existe": 30, "autocomplete": 14}


def contact_renseigne() -> bool:
    """Vrai si `FACTORY_CONTACT` porte une valeur. Ce n'est pas un détail de politesse.

    **Mesuré le 20/09/2026** : sans contact, le REST des pageviews renvoie des 429 dès
    quelques appels par seconde, et les 85 seeds de l'étape 19 ont mis 256 s au lieu de
    quelques secondes. La variable est vide dans `.env` : c'est une action de Thomas.
    """
    charger_env()
    return bool(os.environ.get("FACTORY_CONTACT", "").strip())


def user_agent() -> str:
    """User-Agent Wikimedia : `Produit/version (contact)`.

    La politique Wikimedia exige un contact joignable. `FACTORY_CONTACT` est lu
    dans `.env` ; sans lui, l'appel reste possible mais la limite de debit tombe
    de 200 a 10 req/min. La valeur doit rester en ASCII : un en-tete HTTP est
    encode en latin-1, et un tiret cadratin echoue avant meme l'appel.
    """
    charger_env()
    contact = os.environ.get("FACTORY_CONTACT", "").strip()
    if not contact:
        return "BMS-Factory/1.0 (contact absent: FACTORY_CONTACT non renseigne)"
    ascii_contact = unicodedata.normalize("NFKD", contact).encode("ascii", "ignore").decode()
    return f"BMS-Factory/1.0 ({ascii_contact})"


class BudgetAppels:
    """Plafond dur d'appels pour une source, refusé **avant** l'appel."""

    def __init__(self, plafond: int) -> None:
        self.plafond = plafond
        self.utilises = 0
        self.refuses = 0

    def prendre(self) -> bool:
        if self.utilises >= self.plafond:
            self.refuses += 1
            return False
        self.utilises += 1
        return True


# ------------------------------------------------------------------------ cache


def dossier_cache(racine: Path | None = None) -> Path:
    return dossier_workspace(racine) / "cache" / "demand"


def _chemin_cache(source: str, cle: str, racine: Path | None = None) -> Path:
    sur = re.sub(r"[^A-Za-z0-9._-]", "_", cle)[:150]
    return dossier_cache(racine) / source / f"{sur}.json"


def lire_cache(source: str, cle: str, racine: Path | None = None) -> dict | None:
    chemin = _chemin_cache(source, cle, racine)
    if not chemin.exists():
        return None
    try:
        enveloppe = json.loads(chemin.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    age_j = (time.time() - enveloppe.get("fetched_ts", 0)) / 86400
    if age_j > TTL_JOURS.get(source, 30):
        return None
    return enveloppe.get("data")


def ecrire_cache(source: str, cle: str, data: dict, racine: Path | None = None) -> None:
    chemin = _chemin_cache(source, cle, racine)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(
        json.dumps(
            {"fetched_ts": time.time(), "fetched_at": datetime.now(UTC).isoformat(), "data": data},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


# ------------------------------------------------------------------- Wikimedia


def titre_url(titre: str) -> str:
    """Titre d'article → segment d'URL Wikimedia (espaces en `_`, puis percent-encoding)."""
    return urllib.parse.quote(titre.strip().replace(" ", "_"), safe="")


def mois_complets(fin: date, n: int) -> tuple[str, str]:
    """Bornes `YYYYMMDD00` des `n` derniers mois **clos** avant `fin`.

    Le mois courant est exclu : au 20 du mois il ne porte que deux tiers de ses
    vues, et le comparer aux précédents fabriquerait une chute qui n'existe pas.
    """
    dernier_a, dernier_m = (fin.year, fin.month - 1) if fin.month > 1 else (fin.year - 1, 12)
    debut_index = dernier_a * 12 + (dernier_m - 1) - (n - 1)
    debut_a, debut_m = divmod(debut_index, 12)
    return f"{debut_a:04d}{debut_m + 1:02d}0100", f"{dernier_a:04d}{dernier_m:02d}0100"


#: Appels qui ont échoué pendant l'exécution, pour que le rapport puisse le dire.
ECHECS: list[str] = []


def _get_json(url: str, *, params: dict | None = None, entetes: dict | None = None) -> dict | None:
    """GET avec User-Agent identifiant et réessais sur 429/5xx.

    `None` **seulement** sur 404, c'est-à-dire « la ressource n'existe pas » — une
    réponse, pas une panne. Tout le reste lève : un appel qui échoue ne doit jamais
    pouvoir être mis en cache comme un résultat vide, sinon une rafale de 429 efface
    un seed pour la durée du cache. C'est arrivé le 20/09/2026 sur « Solar System »
    et « Big Bang », tous deux revenus à zéro point alors que l'API les sert.
    """
    tetes = {"User-Agent": user_agent(), "Accept": "application/json"}
    tetes.update(entetes or {})
    for essai in range(TENTATIVES):
        try:
            rep = requests.get(url, params=params, headers=tetes, timeout=TIMEOUT_S)
        except requests.RequestException:
            time.sleep(1.5 * (essai + 1))
            continue
        if rep.status_code == 200:
            time.sleep(PAUSE_S)
            try:
                return rep.json()
            except ValueError:
                return None
        if rep.status_code == 404:  # article inconnu de Wikimedia : c'est une réponse
            return None
        if rep.status_code == 429:
            # `Retry-After` quand le serveur le donne ; sinon un recul qui double.
            attente = rep.headers.get("Retry-After")
            try:
                pause = float(attente) if attente else 0.0
            except ValueError:
                pause = 0.0
            time.sleep(max(pause, 5.0 * (2 ** essai)))
            continue
        if rep.status_code in (500, 502, 503, 504):
            time.sleep(2.0 * (essai + 1))
            continue
        raise ConnectionError(f"HTTP {rep.status_code} sur {url}")
    raise ConnectionError(f"{TENTATIVES} tentatives épuisées sur {url}")


def pageviews_mensuels(
    article: str, projet: str = "en.wikipedia", *, fin: date | None = None, n_mois: int = 24,
    racine: Path | None = None,
) -> list[tuple[str, int]]:
    """Vues mensuelles d'un article sur les `n_mois` derniers mois clos.

    Retourne `[("2024-10", 16186), …]`, vide si l'article est inconnu. Agent `user` :
    les robots et les araignées sont exclus par l'API elle-même.
    """
    fin = fin or datetime.now(UTC).date()
    debut_ts, fin_ts = mois_complets(fin, n_mois)
    cle = f"{projet}_{titre_url(article)}_{debut_ts}_{fin_ts}"
    cache = lire_cache("wikimedia", cle, racine)
    if cache is not None:
        return [(m, v) for m, v in cache["points"]]

    url = f"{WIKIMEDIA_REST}/{projet}/all-access/user/{titre_url(article)}/monthly/{debut_ts}/{fin_ts}"
    try:
        data = _get_json(url)
    except ConnectionError as exc:
        # Rien n'est mis en cache : l'appel sera retenté à la prochaine exécution.
        ECHECS.append(f"{projet}/{article} : {exc}")
        return []
    points: list[tuple[str, int]] = []
    if data and "items" in data:
        for it in data["items"]:
            ts = it["timestamp"]
            points.append((f"{ts[:4]}-{ts[4:6]}", int(it.get("views") or 0)))
    ecrire_cache("wikimedia", cle, {"points": points, "url": url}, racine)
    return points


#: L'API d'action de MediaWiki accepte 50 titres par appel et limite sévèrement le
#: débit (429 après une poignée d'appels isolés, mesuré le 20/09/2026). On valide
#: donc une niche entière en un appel, jamais un article à la fois.
TITRES_PAR_APPEL = 50


def articles_existent(
    titres: list[str], projet: str = "en.wikipedia", *, racine: Path | None = None,
) -> dict[str, tuple[bool, str]]:
    """Règle de validation des seeds : l'article existe-t-il, sous quel titre canonique ?

    Les redirections sont suivies : « Biohacking » est un titre valable, mais les
    vues sont comptées sur la cible de la redirection, et c'est ce titre-là qu'il
    faut écrire dans la configuration.

    Un appel qui échoue lève : **une panne réseau n'est pas une absence d'article**,
    et la mettre en cache condamnerait le seed pour la durée du cache.
    """
    resultats: dict[str, tuple[bool, str]] = {}
    a_demander: list[str] = []
    for titre in titres:
        cache = lire_cache("wikipedia_existe", f"{projet}_{titre_url(titre)}", racine)
        if cache is not None:
            resultats[titre] = (cache["existe"], cache["canonique"])
        else:
            a_demander.append(titre)

    for debut in range(0, len(a_demander), TITRES_PAR_APPEL):
        lot = a_demander[debut:debut + TITRES_PAR_APPEL]
        data = _get_json(
            WIKIPEDIA_API.format(projet=projet.replace(".wikipedia", ".wikipedia.org")),
            params={"action": "query", "titles": "|".join(lot), "redirects": "1",
                    "format": "json", "formatversion": "2"},
        )
        if data is None or "query" not in data:
            raise ConnectionError(
                f"validation des seeds impossible sur {projet} ({len(lot)} titres) : "
                "appel refusé ou limité (429). Réessayer plus tard."
            )
        requete = data["query"]
        # `normalized` et `redirects` disent comment chaque titre demandé a été
        # transformé ; sans eux, on ne sait pas à quelle page appartient la réponse.
        vers_canonique = {n["from"]: n["to"] for n in requete.get("normalized", [])}
        redirections = {r["from"]: r["to"] for r in requete.get("redirects", [])}
        pages = {p.get("title"): p for p in requete.get("pages", [])}
        for titre in lot:
            cible = vers_canonique.get(titre, titre)
            cible = redirections.get(cible, cible)
            page = pages.get(cible)
            existe = bool(page) and not page.get("missing", False)
            canonique = page.get("title", titre) if page else titre
            resultats[titre] = (existe, canonique)
            ecrire_cache("wikipedia_existe", f"{projet}_{titre_url(titre)}",
                         {"existe": existe, "canonique": canonique}, racine)
        time.sleep(1.0)  # l'API d'action est bien plus stricte que le REST des pageviews
    return resultats


def article_existe(titre: str, projet: str = "en.wikipedia", *, racine: Path | None = None) -> tuple[bool, str]:
    """Validation d'un seul seed. Préférer `articles_existent` pour une niche entière."""
    return articles_existent([titre], projet, racine=racine)[titre]


# ------------------------------------------- niveau, tendance, saisonnalité


#: Un mois de queue dont le total tombe sous cette fraction de la médiane des six
#: mois précédents est tenu pour **non consolidé**, pas pour un effondrement.
SEUIL_MOIS_INCOMPLET = 0.40


def couper_queue_incomplete(points: list[tuple[str, int]]) -> tuple[list[tuple[str, int]], int]:
    """Retire les derniers mois dont l'agrégat mensuel n'est manifestement pas consolidé.

    **Défaut mesuré le 20/09/2026.** Le point d'entrée `monthly` de Wikimedia rend,
    pour le dernier mois, une valeur qui ne couvre qu'une fraction du mois : « Ancient
    Egypt » sort à **2 274 vues pour août 2026** quand le point d'entrée `daily` du
    même mois donne 31 jours à ~2 500 vues, soit ≈ 78 000 — l'ordre de grandeur de
    juillet (80 003). La latence réelle de consolidation dépasse donc les « 1 à 2
    jours » annoncés, et le mois clos le plus récent n'est pas fiable.

    Laissé tel quel, ce seul point tire la pente log-linéaire à **−14 %/mois sur les
    onze niches à la fois** — une décrue générale qui n'existe pas. On coupe la queue
    plutôt que de corriger : une valeur reconstituée serait une valeur inventée.
    """
    if len(points) < 8:
        return points, 0
    coupes = 0
    restants = list(points)
    while len(restants) >= 8:
        reference = statistics.median(v for _, v in restants[-7:-1])
        if reference > 0 and restants[-1][1] < SEUIL_MOIS_INCOMPLET * reference:
            restants.pop()
            coupes += 1
        else:
            break
    return restants, coupes


@dataclass
class SerieDemande:
    """Décomposition d'une série mensuelle : niveau, tendance, saisonnalité."""

    article: str
    projet: str
    points: list[tuple[str, int]]
    niveau: float | None = None          # médiane des 12 derniers mois clos
    pente_mensuelle: float | None = None  # croissance relative par mois, ajustement log-linéaire
    r2: float | None = None
    #: mois civil 1-12 → (indice, nombre d'observations). Le n compte : avec 23 mois,
    #: certains mois civils n'ont qu'une seule observation, et un indice sur n = 1 n'est
    #: pas une saison.
    saisonnalite: dict[int, tuple[float, int]] = field(default_factory=dict)
    n_mois: int = 0
    n_mois_non_consolides: int = 0

    @property
    def url(self) -> str:
        return f"https://pageviews.wmcloud.org/?project={self.projet}&pages={titre_url(self.article)}"


def decomposer(article: str, projet: str, points: list[tuple[str, int]]) -> SerieDemande:
    """Niveau, tendance et saisonnalité d'une série mensuelle.

    **La tendance est retirée avant de mesurer la saisonnalité**, faute de quoi une
    niche en croissance afficherait un « pic de décembre » qui n'est que sa pente.
    Le modèle est multiplicatif : `log(vues) = a + b·t`, puis l'indice du mois
    civil *m* est la moyenne des résidus `vues / exp(a + b·t)` observés ce mois-là.
    Avec 24 mois, chaque mois civil n'a que **deux observations** : l'indice est un
    indice, pas une saison établie.
    """
    points, coupes = couper_queue_incomplete(points)
    serie = SerieDemande(article=article, projet=projet, points=points, n_mois=len(points),
                         n_mois_non_consolides=coupes)
    if not points:
        return serie

    valeurs = [v for _, v in points]
    serie.niveau = float(statistics.median(valeurs[-12:] if len(valeurs) >= 12 else valeurs))

    # Ajustement log-linéaire sur les 12 derniers mois (la pente courte est celle
    # qui décide ; une pente sur 24 mois lisse un retournement récent).
    fenetre = points[-12:] if len(points) >= 12 else points
    if len(fenetre) >= 6:
        xs = list(range(len(fenetre)))
        ys = [math.log(max(v, 1)) for _, v in fenetre]
        n = len(xs)
        mx, my = sum(xs) / n, sum(ys) / n
        sxx = sum((x - mx) ** 2 for x in xs)
        if sxx > 0:
            b = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / sxx
            a = my - b * mx
            serie.pente_mensuelle = math.expm1(b)  # +0,03 = +3 % par mois
            sst = sum((y - my) ** 2 for y in ys)
            sse = sum((y - (a + b * x)) ** 2 for x, y in zip(xs, ys, strict=True))
            serie.r2 = (1 - sse / sst) if sst > 0 else None

    # Saisonnalité sur toute la fenêtre disponible, tendance retirée.
    if len(points) >= 12:
        xs = list(range(len(points)))
        ys = [math.log(max(v, 1)) for _, v in points]
        n = len(xs)
        mx, my = sum(xs) / n, sum(ys) / n
        sxx = sum((x - mx) ** 2 for x in xs)
        b = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / sxx if sxx else 0.0
        a = my - b * mx
        par_mois: dict[int, list[float]] = {}
        for i, (mois, v) in enumerate(points):
            attendu = math.exp(a + b * i)
            if attendu > 0:
                par_mois.setdefault(int(mois[5:7]), []).append(max(v, 1) / attendu)
        serie.saisonnalite = {m: (sum(r) / len(r), len(r)) for m, r in sorted(par_mois.items())}
    return serie


def demande_wikimedia(
    seeds: list[str], projet: str = "en.wikipedia", *, fin: date | None = None,
    n_mois: int = 24, racine: Path | None = None, budget: BudgetAppels | None = None,
) -> list[SerieDemande]:
    """Décompose chaque seed d'une niche. Les seeds inconnus sortent avec 0 point."""
    sorties = []
    for article in seeds:
        if budget is not None and not budget.prendre():
            break
        points = pageviews_mensuels(article, projet, fin=fin, n_mois=n_mois, racine=racine)
        sorties.append(decomposer(article, projet, points))
    return sorties


def agreger(series: list[SerieDemande], *, r2_minimal: float = 0.3) -> dict:
    """Agrège les seeds d'une niche : niveau médian, pente et saisonnalité pondérées.

    **Le niveau est la médiane des seeds, pas leur somme.** Une somme récompense le
    nombre de seeds et se gonfle en ajoutant deux articles massifs à la configuration ;
    la médiane mesure ce qu'elle prétend mesurer — le niveau typique d'un sujet de la
    niche. La somme reste dans les preuves sous `niveau_somme`.

    **La pente n'est prise que des seeds dont l'ajustement tient** (`r² ≥ r2_minimal`).
    Sans ce filtre, une série plate et bruitée apporte une pente aussi lourde qu'une
    tendance nette : `espace_astronomie` agrégeait un seed à r² = 0,0004.

    Pente et saisonnalité sont pondérées **par le niveau** de chaque seed : sans cela,
    un article confidentiel qui double ses 40 vues pèserait autant que l'article
    principal de la niche.
    """
    utiles = [s for s in series if s.niveau is not None and s.niveau > 0]
    if not utiles:
        return {"niveau": 0.0, "niveau_somme": 0.0, "pente": None, "pente_n_seeds": 0,
                "saisonnalite": {}, "n_seeds": 0, "n_seeds_vides": len(series),
                "mois_non_consolides": 0}

    niveau = float(statistics.median(s.niveau for s in utiles))
    poids = [s.niveau for s in utiles]

    ajustes = [(s, p) for s, p in zip(utiles, poids, strict=True)
               if s.pente_mensuelle is not None and (s.r2 or 0.0) >= r2_minimal]
    pente = (sum(s.pente_mensuelle * p for s, p in ajustes) / sum(p for _, p in ajustes)
             if ajustes else None)

    saison: dict[int, tuple[float, int]] = {}
    for mois in range(1, 13):
        contrib = [(s.saisonnalite[mois][0], s.saisonnalite[mois][1], p)
                   for s, p in zip(utiles, poids, strict=True) if mois in s.saisonnalite]
        if contrib:
            total = sum(p for _, _, p in contrib)
            saison[mois] = (sum(v * p for v, _, p in contrib) / total,
                            min(n for _, n, _ in contrib))

    return {
        "niveau": niveau,
        "niveau_somme": sum(s.niveau for s in utiles),
        "pente": pente,
        "pente_n_seeds": len(ajustes),
        "r2_minimal": r2_minimal,
        "saisonnalite": saison,
        "n_seeds": len(utiles),
        "n_seeds_vides": len(series) - len(utiles),
        "mois_non_consolides": max((s.n_mois_non_consolides for s in series), default=0),
        "par_seed": [
            {"article": s.article, "niveau": s.niveau, "pente": s.pente_mensuelle,
             "r2": s.r2, "n_mois": s.n_mois,
             "n_mois_non_consolides": s.n_mois_non_consolides, "url": s.url}
            for s in series
        ],
    }


# ----------------------------------------------------------------- autocomplete

_MOTS_VIDES = {"the", "a", "an", "of", "to", "in", "and", "for", "you", "your", "is",
               "it", "on", "with", "how", "what", "de", "la", "le", "les", "des", "du"}


def autocomplete_youtube(
    mot_cle: str, *, hl: str = "en", gl: str = "US", racine: Path | None = None,
    budget: BudgetAppels | None = None,
) -> list[str]:
    """Suggestions de l'autocomplete YouTube. **Point d'entrée non documenté.**

    `client=firefox` renvoie du JSON pur (`client=youtube` renvoie du JSONP à
    décaper, et une suggestion de plus : le gain ne vaut pas le parsing fragile).
    La réponse est en ISO-8859-1 et doit être décodée explicitement, sinon les
    accents des langues latines sortent en mojibake.
    """
    cle = f"{hl}_{gl}_{mot_cle}"
    cache = lire_cache("autocomplete", cle, racine)
    if cache is not None:
        return cache["suggestions"]
    if budget is not None and not budget.prendre():
        return []

    try:
        rep = requests.get(
            AUTOCOMPLETE,
            params={"client": "firefox", "ds": "yt", "hl": hl, "gl": gl, "q": mot_cle},
            headers={"User-Agent": user_agent()}, timeout=TIMEOUT_S,
        )
    except requests.RequestException:
        return []
    if rep.status_code != 200:
        return []
    rep.encoding = "ISO-8859-1"
    try:
        charge = json.loads(rep.text)
    except ValueError:
        return []
    time.sleep(PAUSE_S)
    suggestions = [s for s in (charge[1] if len(charge) > 1 else []) if isinstance(s, str)]
    ecrire_cache("autocomplete", cle, {"suggestions": suggestions}, racine)
    return suggestions


def _jetons(phrase: str) -> set[str]:
    sans_accent = unicodedata.normalize("NFKD", phrase.lower())
    sans_accent = "".join(c for c in sans_accent if not unicodedata.combining(c))
    return {m for m in re.findall(r"[a-z0-9]+", sans_accent) if len(m) > 2 and m not in _MOTS_VIDES}


def demande_autocomplete(
    mots_cles: list[str], *, hl: str = "en", gl: str = "US", racine: Path | None = None,
    budget: BudgetAppels | None = None,
) -> dict:
    """Largeur d'intention : combien de suggestions, et combien de sujets distincts.

    Ni l'un ni l'autre n'est un volume de recherche. Le nombre de suggestions
    sature à 10 (limite du point d'entrée) ; c'est la **diversité** — jetons
    distincts hors des mots-clés semés — qui distingue une niche large d'une
    niche où toutes les suggestions redisent la même chose.
    """
    total, details = [], []
    jetons_semes: set[str] = set()
    for mot in mots_cles:
        jetons_semes |= _jetons(mot)
    for mot in mots_cles:
        sugg = autocomplete_youtube(mot, hl=hl, gl=gl, racine=racine, budget=budget)
        total.extend(sugg)
        details.append({"mot_cle": mot, "n": len(sugg), "exemples": sugg[:3]})
    jetons_neufs: set[str] = set()
    for s in total:
        jetons_neufs |= _jetons(s) - jetons_semes
    n_appels = len(mots_cles)
    return {
        "n_suggestions": len(total),
        "n_par_mot_cle": (len(total) / n_appels) if n_appels else 0.0,
        "diversite": len(jetons_neufs),
        "hl": hl, "gl": gl,
        "statut": "non documenté",
        "details": details,
    }


# ----------------------------------------------------------------------- Trends


def demande_trends(mots_cles: list[str], *, lang: str = "en") -> tuple[None, str]:
    """Google Trends : pas d'accès, et le champ reste nul.

    L'API officielle (v1alpha) est sur candidature depuis 07/2025 et n'a **aucune
    clé en self-service** au 20/09/2026 ; `trendspy` interroge les points d'entrée
    internes de Google (429 fréquents, dépend d'un cookie de consentement, zone
    grise contractuelle) et ne peut pas tenir une chaîne automatisée. Le jour où
    une clé arrive, c'est cette fonction seule qui change.
    """
    return None, (
        "Google Trends indisponible : API officielle en alpha sur candidature "
        "(aucune clé self-service au 20/09/2026), trendspy écarté (points d'entrée "
        "internes, blocages 429, zone grise contractuelle). Champ nul, non estimé."
    )
