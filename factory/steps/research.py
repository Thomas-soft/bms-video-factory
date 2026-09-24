"""`factory research` — faits sourcés sur API gratuites, puis choix d'un angle éditorial.

Sources retenues (vérifiées le 15/09/2026, aucune clé, aucune carte) :
- **Wikipedia** — API Action `prop=extracts`, dans la langue de la chaîne puis en anglais.
  200 req/min avec un User-Agent conforme, **10 req/min sans** ; contenus en CC BY-SA 4.0.
- **PubMed E-utilities** — niches santé et science. 3 req/s sans clé, `tool=` et `email=`
  **exigés** par NCBI : sans contact configuré, la source est écartée, pas appelée à vide.
- Écartées : Semantic Scholar (429 sur le pool anonyme) et arXiv (429 puis échec depuis
  cette IP) — mesuré le 15/09/2026. Elles restent déclarées dans `sources_rejected`.

Aucune vidéo tierce n'est téléchargée (`CONFORMITE.md` § 9).
"""

from __future__ import annotations

import os
import time
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

from factory import llm
from factory.core import config as config_module
from factory.core import db, referentiel, runs
from factory.core.models import (
    AnglePropose,
    Entite,
    Fait,
    Research,
    SourceConsultee,
    SourceEcartee,
)
from factory.core.paths import RunPaths

VERSION_OUTIL = "0.1"
NOM_OUTIL = "BMS-video-factory"
#: Niches pour lesquelles une source spécialisée est exigée par le prompt de l'étape 10.
NICHES_SPECIALISEES = {
    "science_pop", "niche_monetisable_longevite", "niche_monetisable_complements_fr",
}
MAX_PAGES_PAR_LANGUE = 4
#: « 3 à 6 sources » (prompt de l'étape 10) : au-delà, le corpus ne tient plus dans 8 k jetons.
MAX_SOURCES = 6
CARACTERES_PAR_SOURCE = 1500


def contact() -> str | None:
    """Contact publié dans le User-Agent. Jamais une adresse devinée : `FACTORY_CONTACT`."""
    valeur = (os.environ.get("FACTORY_CONTACT") or "").strip()
    return valeur or None


def user_agent() -> str:
    """User-Agent conforme à la politique Wikimedia : outil, version, contact."""
    if contact():
        return f"{NOM_OUTIL}/{VERSION_OUTIL} ({contact()}) python-requests"
    return f"{NOM_OUTIL}/{VERSION_OUTIL} (contact non configuré : FACTORY_CONTACT) python-requests"


class Limiteur:
    """Respect d'un intervalle minimal entre deux appels d'un même service."""

    def __init__(self, intervalle_s: float) -> None:
        self.intervalle_s = intervalle_s
        self._dernier = 0.0

    def attendre(self) -> None:
        """Dort le temps nécessaire avant l'appel suivant."""
        reste = self.intervalle_s - (time.monotonic() - self._dernier)
        if reste > 0:
            time.sleep(reste)
        self._dernier = time.monotonic()


@dataclass
class Collecte:
    """Ce que la collecte HTTP a rapporté, avant tout passage par le LLM."""

    sources: list[SourceConsultee] = field(default_factory=list)
    textes: list[str] = field(default_factory=list)
    ecartees: list[SourceEcartee] = field(default_factory=list)
    secondes_http: float = 0.0


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": user_agent(), "Accept-Encoding": "gzip"})
    return session


def _wikipedia_recherche(
    session: requests.Session, lang: str, requete: str, limiteur: Limiteur, n: int = 3
) -> list[str]:
    """Titres d'articles les plus pertinents pour une requête."""
    limiteur.attendre()
    reponse = session.get(
        f"https://{lang}.wikipedia.org/w/api.php",
        params={"action": "query", "list": "search", "srsearch": requete,
                "srlimit": n, "format": "json", "formatversion": "2"},
        timeout=20,
    )
    reponse.raise_for_status()
    return [r["title"] for r in reponse.json().get("query", {}).get("search", [])]


def _wikipedia_extraits(
    session: requests.Session, lang: str, titres: list[str], limiteur: Limiteur
) -> list[dict[str, str]]:
    """Texte brut et URL canonique de plusieurs articles en un seul appel."""
    if not titres:
        return []
    limiteur.attendre()
    reponse = session.get(
        f"https://{lang}.wikipedia.org/w/api.php",
        # `exchars` n'est accepté qu'avec `exlimit=1` : pour un seul appel par langue, on prend
        # l'introduction entière (`exintro`) et on tronque ici.
        params={"action": "query", "prop": "extracts|info", "inprop": "url",
                "explaintext": "1", "exintro": "1", "exlimit": "max",
                "titles": "|".join(titres), "format": "json", "formatversion": "2"},
        timeout=30,
    )
    reponse.raise_for_status()
    pages = reponse.json().get("query", {}).get("pages", [])
    return [
        {"title": p["title"], "url": p.get("fullurl", ""),
         "extract": p.get("extract", "")[:CARACTERES_PAR_SOURCE]}
        for p in pages
        if p.get("extract") and not p.get("missing")
    ]


def _pubmed(
    session: requests.Session, requete: str, limiteur: Limiteur, n: int = 2
) -> list[dict[str, str]]:
    """Résumés PubMed. NCBI exige `tool=` et `email=` : sans contact, on n'appelle pas."""
    adresse = contact()
    if not adresse:
        return []
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    commun = {"db": "pubmed", "tool": NOM_OUTIL, "email": adresse}
    limiteur.attendre()
    rep = session.get(
        f"{base}/esearch.fcgi",
        params={**commun, "term": requete, "retmode": "json", "retmax": n, "sort": "relevance"},
        timeout=20,
    )
    rep.raise_for_status()
    ids = rep.json().get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []
    limiteur.attendre()
    rep = session.get(
        f"{base}/esummary.fcgi", params={**commun, "id": ",".join(ids), "retmode": "json"},
        timeout=20,
    )
    rep.raise_for_status()
    resumes = rep.json().get("result", {})
    limiteur.attendre()
    rep = session.get(
        f"{base}/efetch.fcgi",
        params={**commun, "id": ",".join(ids), "rettype": "abstract", "retmode": "text"},
        timeout=30,
    )
    rep.raise_for_status()
    morceaux = [m.strip() for m in rep.text.split("\n\n\n") if m.strip()]
    sorties: list[dict[str, str]] = []
    for i, pmid in enumerate(ids):
        meta = resumes.get(pmid, {})
        texte = morceaux[i] if i < len(morceaux) else ""
        sorties.append({
            "title": (meta.get("title") or f"PubMed {pmid}")[:300],
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "extract": texte[:CARACTERES_PAR_SOURCE],
            "date": (meta.get("pubdate") or "")[:10],
        })
    return [s for s in sorties if s["extract"]]


def pertinente(page: dict[str, str], mots_cles: list[str]) -> bool:
    """Vrai si la page **traite** du sujet, et pas seulement s'il y est mentionné.

    Deux garde-fous posés sur mesure, le 15/09/2026, sur le sujet « quit sugar » :
    - sans aucun contrôle, la recherche anglaise a rendu *MDMA*, *Nicotine gum* et
      *Angus Barbieri's fast* ;
    - avec un seul mot-clé exigé, elle a rendu *Sugar Ray Leonard* (le surnom d'un boxeur) et
      *Long-term effects of alcohol* (qui ne doit son passage qu'au mot « health »).

    La règle retenue : l'article canonique du mot-clé principal est accepté sur son titre ;
    tout autre article doit porter le mot-clé principal **et** un second mot-clé distinct.
    """
    # Une locution n'apparaît dans aucun article : elle ne peut rien valider. On ne retient
    # que les mots simples (mesuré : « quit sugar » et « no sugar diet » n'ont jamais filtré).
    utiles = [m.lower().strip() for m in mots_cles
              if len(m.strip()) >= 3 and len(m.strip().split()) == 1]
    if not utiles:
        return True
    titre = page.get("title", "").lower().strip()
    principal = utiles[0]
    if titre in utiles:
        return True  # article canonique de l'un des mots-clés
    corpus = (page.get("title", "") + " " + page.get("extract", "")).lower()
    presents = [m for m in utiles if m in corpus]
    if principal not in presents:
        return False
    return len(presents) >= min(2, len(utiles))


def collecter(
    sujet: str, lang: str, nom_niche: str, requetes: dict[str, list[str]],
    mots_cles: dict[str, list[str]] | None = None,
) -> Collecte:
    """Interroge les sources gratuites et renvoie ce qui a été réellement obtenu."""
    collecte = Collecte()
    t0 = time.perf_counter()
    session = _session()
    # Sans contact publié, Wikimedia plafonne à 10 req/min : on tient 6 s entre deux appels.
    limiteur_wiki = Limiteur(1.0 if contact() else 6.0)
    limiteur_ncbi = Limiteur(0.4)
    horodatage = runs.maintenant()

    mots_cles = mots_cles or {}
    langues = [lang] + (["en"] if lang != "en" else [])
    for code in langues:
        titres: list[str] = []
        # Le mot-clé principal seul est interrogé en premier : c'est la requête qui ramène
        # l'article canonique du sujet, là où les requêtes du modèle dérivent.
        cles = [m for m in mots_cles.get(code, []) if len(m.split()) == 1]
        # Chaque mot-clé simple est interrogé seul et **on n'en garde que le premier résultat** :
        # c'est ainsi qu'on obtient les articles canoniques (« Sugar », « Sucrose », « Glucose »,
        # « Fructose »). Sans cette limite, les trois résultats de « sugar » (dont un boxeur et
        # un groupe de rock) saturaient la liste avant le deuxième mot-clé. Les requêtes du
        # modèle ne viennent qu'en complément : mesuré, elles dérivent sur ce type de sujet.
        plan_requetes = [(c, 1) for c in cles[:4]] + [
            (r, 2) for r in requetes.get(code, [])[:2]]
        for requete, garde in plan_requetes:
            if not requete.strip():
                continue
            try:
                for titre in _wikipedia_recherche(session, code, requete, limiteur_wiki, garde)[:garde]:
                    if titre not in titres:
                        titres.append(titre)
            except requests.RequestException as exc:
                collecte.ecartees.append(SourceEcartee(
                    url=f"https://{code}.wikipedia.org/w/api.php?srsearch="
                        f"{urllib.parse.quote(requete)}",
                    reason=f"recherche en échec : {exc}",
                ))
        try:
            pages = _wikipedia_extraits(session, code, titres[:MAX_PAGES_PAR_LANGUE], limiteur_wiki)
        except requests.RequestException as exc:
            collecte.ecartees.append(SourceEcartee(
                url=f"https://{code}.wikipedia.org/w/api.php", reason=f"extraits en échec : {exc}"))
            continue
        for page in pages:
            if len(page["extract"]) < 200:
                collecte.ecartees.append(SourceEcartee(
                    url=page["url"] or page["title"], reason="extrait trop court (< 200 car.)"))
                continue
            if not pertinente(page, mots_cles.get(code, [])):
                collecte.ecartees.append(SourceEcartee(
                    url=page["url"] or page["title"],
                    reason=f"hors sujet : aucun mot-clé parmi {mots_cles.get(code, [])}"))
                continue
            collecte.sources.append(SourceConsultee(
                url=page["url"], title=page["title"], api="wikipedia", lang=code,
                licence="CC BY-SA 4.0", retrieved_at=horodatage,
            ))
            collecte.textes.append(page["extract"])

    if nom_niche in NICHES_SPECIALISEES:
        if not contact():
            collecte.ecartees.append(SourceEcartee(
                url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                reason="PubMed exige tool= et email= : variable FACTORY_CONTACT non configurée",
            ))
        else:
            requete_en = (requetes.get("en") or [sujet])[0]
            try:
                for article in _pubmed(session, requete_en, limiteur_ncbi):
                    collecte.sources.append(SourceConsultee(
                        url=article["url"], title=article["title"], api="pubmed", lang="en",
                        licence="notice NLM libre ; résumé sous droit de l'éditeur (citation courte)",
                        retrieved_at=horodatage,
                    ))
                    collecte.textes.append(article["extract"])
            except requests.RequestException as exc:
                collecte.ecartees.append(SourceEcartee(
                    url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/",
                    reason=f"PubMed en échec : {exc}"))
    for url, motif in (
        ("https://api.semanticscholar.org/graph/v1/paper/search",
         "429 sur le pool anonyme, mesuré le 15/09/2026 — non appelée"),
        ("https://export.arxiv.org/api/query",
         "429 puis échec de connexion depuis cette IP, mesuré le 15/09/2026 — non appelée"),
    ):
        collecte.ecartees.append(SourceEcartee(url=url, reason=motif))
    collecte.secondes_http = time.perf_counter() - t0
    return collecte


# --------------------------------------------------------------------------------------
# Appels LLM
# --------------------------------------------------------------------------------------

SCHEMA_REQUETES = {
    "type": "object",
    "properties": {
        "requetes_langue": {"type": "array", "minItems": 2, "items": {"type": "string"}},
        "requetes_en": {"type": "array", "minItems": 2, "items": {"type": "string"}},
        "mots_cles_langue": {"type": "array", "minItems": 3, "items": {"type": "string"}},
        "mots_cles_en": {"type": "array", "minItems": 3, "items": {"type": "string"}},
        "entites": {"type": "array", "items": {"type": "object", "properties": {
            "name": {"type": "string"},
            "type": {"type": "string", "enum": ["person", "place", "org", "concept"]},
            "real_person": {"type": "boolean"}}, "required": ["name", "type", "real_person"]}},
    },
    "required": ["requetes_langue", "requetes_en", "mots_cles_langue", "mots_cles_en", "entites"],
}

SCHEMA_FAITS = {
    "type": "object",
    "properties": {"faits": {"type": "array", "minItems": 5, "items": {"type": "object", "properties": {
        "claim": {"type": "string"},
        "value": {"type": "string"},
        "unit": {"type": "string"},
        "source": {"type": "integer"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]}},
        "required": ["claim", "value", "unit", "source", "confidence"]}},
        "questions_ouvertes": {"type": "array", "items": {"type": "string"}}},
    "required": ["faits", "questions_ouvertes"],
}

SCHEMA_ANGLES = {
    "type": "object",
    "properties": {
        "angles": {"type": "array", "minItems": 3, "items": {"type": "object", "properties": {
            "type": {"type": "string", "enum": ["contrarien", "comparatif_chiffre", "recit"]},
            "phrase": {"type": "string"},
            "signature": {"type": "string", "enum": [
                "opinion", "comparaison_chiffree", "test", "donnee_proprietaire"]}},
            "required": ["type", "phrase", "signature"]}},
        "choisi": {"type": "integer"},
        "motif": {"type": "string"},
        "elements_proprietaires": {"type": "array", "minItems": 2, "items": {"type": "string"}},
    },
    "required": ["angles", "choisi", "motif", "elements_proprietaires"],
}

SYSTEME = (
    "Tu es documentaliste et rédacteur en chef pour une chaîne YouTube. "
    "Tu ne réponds que par un objet JSON valide, sans commentaire ni texte autour. "
    "Tu n'inventes jamais un chiffre : si une information n'est pas dans les sources fournies, "
    "tu ne l'écris pas."
)


def persona(channel: Any, cfg: Any) -> str:
    """Persona de la chaîne, reconstituée depuis la configuration existante.

    `config/channels/*.yaml` ne porte pas encore de champ `persona` : cette fonction est le
    point d'extension. Tant qu'il n'existe pas, la persona est dérivée de ce qui est déclaré.
    """
    voix = cfg.voix_de(channel)
    cadrage = channel.charte.framing
    return (
        f"Chaîne « {channel.name} », langue {channel.lang}, niche {channel.niche}, "
        f"style visuel {channel.style}. Voix {channel.voice_id}"
        + (f" ({voix.gender})" if voix else "")
        + f". Cadrage imposé : {cadrage.person_shots}, on privilégie "
        f"{', '.join(cadrage.prefer)}. Ton : vulgarisation directe, sans sensationnalisme, "
        "chaque affirmation adossée à une source."
    )


def executer(video_id: str, racine: Path | None = None) -> tuple[Research, float, list[str]]:
    """Collecte les sources, en extrait des faits, choisit un angle → `research.json`."""
    t0 = time.perf_counter()
    alertes: list[str] = []
    spec = runs.charger_spec(video_id, racine)
    cfg = config_module.charger(racine, strict=False)
    channel = cfg.get_channel(spec.channel_id)
    trace = llm.TraceLLM()

    if not contact():
        alertes.append(
            "FACTORY_CONTACT non configuré : Wikimedia plafonne à 10 req/min et PubMed est "
            "écarté (NCBI exige tool= et email=). À renseigner dans .env avant la production."
        )

    # 1 — requêtes de recherche et entités, dans la langue de la chaîne et en anglais.
    donnees, _ = llm.generate_json(
        f"Sujet de la vidéo : « {spec.topic.sujet} ».\n"
        f"Langue de la chaîne : {spec.lang}.\n\n"
        "Identifie d'abord le SUJET PRINCIPAL : le nom commun central dont parle la vidéo "
        "(une substance, un organe, un phénomène), et non une conséquence, une durée, une "
        "personne ou une marque.\n"
        f"`mots_cles_langue` : 3 à 5 mots-clés de ce sujet en {spec.lang}, **chacun d'UN SEUL "
        "MOT**, au singulier, tel qu'il s'écrit dans un article d'encyclopédie (« sucre », "
        "« saccharose », « glucose », « insuline »). Pas de locution (« arrêter le sucre » n'est "
        "un mot d'aucun article), pas de mot passe-partout (« santé », « effets », « corps »). "
        "Le premier est le titre de l'article d'encyclopédie du sujet. `mots_cles_en` : les "
        "mêmes en anglais, même règle.\n"
        "`requetes_langue` : deux requêtes d'encyclopédie de 2 à 5 mots dans la langue "
        f"{spec.lang}, contenant au moins un mot-clé. `requetes_en` : deux équivalentes en "
        "anglais. Pas de question, pas de verbe conjugué.\n"
        "`entites` : les entités nommées du sujet ; `real_person` vaut true seulement pour une "
        "personne réelle identifiable.",
        system=SYSTEME, json_schema=SCHEMA_REQUETES, max_tokens=600,
        temperature=0.3, seed=spec.seed % 100000, etiquette="research:requetes",
        trace=trace, racine=racine,
    )
    requetes = {spec.lang: donnees["requetes_langue"], "en": donnees["requetes_en"]}
    mots_cles = {spec.lang: [str(m) for m in donnees["mots_cles_langue"][:4]],
                 "en": [str(m) for m in donnees["mots_cles_en"][:4]]}
    entites = [
        Entite(name=e["name"][:200], type=e["type"], real_person=bool(e["real_person"]))
        for e in donnees.get("entites", [])[:12]
    ]

    # 2 — collecte HTTP.
    collecte = collecter(spec.topic.sujet, spec.lang, spec.niche, requetes, mots_cles)
    if len(collecte.sources) < 3:
        hors_sujet = sum(1 for e in collecte.ecartees if e.reason.startswith("hors sujet"))
        raise RuntimeError(
            f"research : {len(collecte.sources)} source(s) obtenue(s), 3 exigées "
            f"({len(collecte.ecartees)} écartées, dont {hors_sujet} hors sujet ; "
            f"mots-clés retenus : {mots_cles})"
        )

    # 3 — extraction des faits. Les URL, titres et licences viennent de la collecte,
    #     jamais du modèle : il ne choisit que l'index de la source.
    if len(collecte.sources) > MAX_SOURCES:
        for surnumeraire in collecte.sources[MAX_SOURCES:]:
            collecte.ecartees.append(SourceEcartee(
                url=surnumeraire.url,
                reason=f"au-delà des {MAX_SOURCES} sources retenues (corpus plafonné à 8 k jetons)"))
        collecte.sources = collecte.sources[:MAX_SOURCES]
        collecte.textes = collecte.textes[:MAX_SOURCES]
    corpus = "\n\n".join(
        f"[{i}] {s.title} ({s.api}, {s.lang})\n{texte}"
        for i, (s, texte) in enumerate(zip(collecte.sources, collecte.textes, strict=True))
    )
    donnees_faits, _ = llm.generate_json(
        f"Sujet : « {spec.topic.sujet} ». Langue de rédaction : {spec.lang}.\n\n"
        f"Sources :\n{corpus}\n\n"
        "Extrais 6 à 8 faits saillants et brefs et vérifiables, chacun tiré d'UNE source citée par son "
        "index entre crochets. `claim` est une phrase de 25 mots au maximum, en "
        f"{spec.lang}, reprise du contenu de la source. `value` porte le chiffre s'il y en a un "
        "(sinon la chaîne vide), `unit` son unité (sinon la chaîne vide). Ne déduis rien, "
        "n'extrapole aucun chiffre. `questions_ouvertes` liste ce que les sources ne tranchent pas.",
        system=SYSTEME, json_schema=SCHEMA_FAITS, max_tokens=1900,
        temperature=0.2, seed=spec.seed % 100000, etiquette="research:faits",
        trace=trace, racine=racine,
    )
    faits: list[Fait] = []
    horodatage = runs.maintenant()
    for brut in donnees_faits["faits"][:14]:
        index = int(brut.get("source", -1))
        if not 0 <= index < len(collecte.sources):
            continue
        source = collecte.sources[index]
        identifiant = f"f{len(faits) + 1:02d}"
        faits.append(Fait(
            id=identifiant, claim=str(brut["claim"])[:400],
            value=str(brut.get("value") or "") or None, unit=str(brut.get("unit") or "") or None,
            source_url=source.url, source_title=source.title, licence=source.licence,
            confidence=brut.get("confidence", "medium"), retrieved_at=horodatage,
        ))
        source.fact_ids.append(identifiant)
    if len(faits) < 3:
        raise RuntimeError(f"research : {len(faits)} fait(s) retenu(s), 3 au minimum")

    # 4 — trois angles éditoriaux, un seul retenu, selon la persona de la chaîne.
    resume_faits = "\n".join(f"- {f.claim}" for f in faits[:10])
    donnees_angles, _ = llm.generate_json(
        f"{persona(channel, cfg)}\n\nSujet : « {spec.topic.sujet} ».\n"
        f"Faits établis :\n{resume_faits}\n\n"
        "Propose exactement trois angles éditoriaux, dans cet ordre : un `contrarien` (il "
        "conteste une idée reçue), un `comparatif_chiffre` (il compare des grandeurs mesurées), "
        "un `recit` (il suit un fil narratif). `phrase` décrit l'angle en une phrase "
        f"en {spec.lang}. `signature` dit ce que la vidéo apportera en propre. "
        "`choisi` est l'index (0, 1 ou 2) de l'angle le plus conforme à la persona ci-dessus, "
        "`motif` l'explique en une phrase. `elements_proprietaires` liste 2 à 4 apports concrets "
        "de cette vidéo qu'aucune source ne contient (une comparaison à construire, un calcul, "
        "une opinion argumentée, un test).\n"
        f"**Tout le texte que tu écris — `phrase`, `motif`, `elements_proprietaires` — est "
        f"rédigé en {spec.lang}**, la langue de la chaîne, et dans aucune autre : ces phrases "
        "sont reprises telles quelles dans le script et lues par le spectateur.",
        system=SYSTEME, json_schema=SCHEMA_ANGLES, max_tokens=1000,
        temperature=0.6, seed=spec.seed % 100000, etiquette="research:angles",
        trace=trace, racine=racine,
    )
    propositions = [
        AnglePropose(type=a["type"], phrase=str(a["phrase"])[:400], angle_signature=a["signature"])
        for a in donnees_angles["angles"][:3]
    ]
    index_choisi = int(donnees_angles.get("choisi", 0))
    if not 0 <= index_choisi < len(propositions):
        index_choisi = 0
        alertes.append("angle : index hors bornes renvoyé par le LLM, premier angle retenu")
    retenu = propositions[index_choisi]

    recherche = Research(
        lang=spec.lang, sujet=spec.topic.sujet, facts=faits, entities=entites,
        open_questions=[str(q)[:300] for q in donnees_faits.get("questions_ouvertes", [])[:6]],
        sources=collecte.sources, sources_rejected=collecte.ecartees,
        fact_count=len(faits), source_count=len(collecte.sources),
        angles_proposes=propositions, angle=retenu.phrase,
        angle_signature=retenu.angle_signature,
        elements_proprietaires=[
            str(e)[:300] for e in donnees_angles.get("elements_proprietaires", [])[:4]
        ],
    )

    chemins = RunPaths.depuis_video_id(video_id, racine)
    runs.ecrire_json(chemins.research, recherche)

    secondes = time.perf_counter() - t0
    manifest = runs.charger_manifest(video_id, racine)
    manifest.decisions.topic.angle = retenu.phrase[:400]
    manifest.execution.timings["research"] = round(secondes, 2)
    manifest.execution.timings["research_http"] = round(collecte.secondes_http, 2)
    manifest.execution.timings["research_llm"] = round(trace.secondes, 2)
    runs.ecrire_json(chemins.manifest, manifest)
    conn = db.ouvrir(None if racine is None else racine / "workspace" / "factory.db")
    db.migrer(conn)
    runs.enregistrer(conn, spec, manifest, racine)
    conn.close()
    return recherche, secondes, alertes
