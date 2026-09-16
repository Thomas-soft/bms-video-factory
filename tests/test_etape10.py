"""Étape 10 — grammaire GBNF, réparation JSON, squelette de script, choix du sujet.

Aucun test n'appelle le LLM : la brique est mesurée par `factory doctor`, pas par pytest.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from factory.core import models as m
from factory.core import referentiel
from factory.llm import extraire_objet, schema_vers_gbnf
from factory.steps.script import construire_squelette


# --- grammaire ------------------------------------------------------------------------

SCHEMA = {
    "type": "object",
    "properties": {
        "segments": {"type": "array", "minItems": 2, "items": {"type": "object", "properties": {
            "id": {"type": "string"},
            "role": {"type": "string", "enum": ["hook", "point"]},
            "mots": {"type": "integer"}},
            "required": ["id", "role", "mots"]}},
    },
    "required": ["segments"],
}


def test_gbnf_sans_underscore_dans_les_noms_de_regles() -> None:
    """llama.cpp refuse un nom de règle contenant `_` : la génération doit employer `-`."""
    grammaire = schema_vers_gbnf(SCHEMA)
    noms = [ligne.split("::=")[0].strip() for ligne in grammaire.splitlines() if "::=" in ligne]
    assert noms, "grammaire vide"
    assert all("_" not in nom for nom in noms), [n for n in noms if "_" in n]
    assert noms[0] == "root"


def test_gbnf_porte_les_enums_et_le_minimum_d_elements() -> None:
    grammaire = schema_vers_gbnf(SCHEMA)
    assert '"\\"hook\\"" | "\\"point\\""' in grammaire
    # minItems = 2 : deux occurrences obligatoires avant la répétition libre.
    ligne = next(l for l in grammaire.splitlines() if l.startswith("n-segments") and '"["' in l)
    assert ligne.count("n-segments-item") == 3


# --- extraction JSON ------------------------------------------------------------------

@pytest.mark.parametrize(
    ("texte", "attendu"),
    [
        ('Voici : {"a": 1} et voilà', {"a": 1}),
        ('{"a": {"b": [1, 2]}}', {"a": {"b": [1, 2]}}),
        (r'{"a": "une }accolade{ dans une chaîne"}', {"a": "une }accolade{ dans une chaîne"}),
        (r'{"a": "guillemet \" échappé"}', {"a": 'guillemet " échappé'}),
    ],
)
def test_extraire_objet(texte: str, attendu: dict) -> None:
    brut = extraire_objet(texte)
    assert brut is not None
    assert json.loads(brut) == attendu


def test_extraire_objet_sans_objet() -> None:
    assert extraire_objet("aucune accolade ici") is None


# --- squelette de script --------------------------------------------------------------

def test_squelette_respecte_les_regles_de_script() -> None:
    """Deux boucles plantées, autant de payoffs, conclusion en dernier."""
    cases = construire_squelette(
        n_segments=28, mots_cibles=1457, mots_hook_max=36, avec_sponsor=False,
        seed=42, duree_cible_s=648.0, intervalle_rupture_s=23.4,
    )
    assert len(cases) == 28
    assert cases[0].role == "hook" and cases[-1].role == "conclusion"
    assert cases[0].mots <= 36
    plants = [c for c in cases if c.open_loop == "plant"]
    payoffs = [c for c in cases if c.open_loop == "payoff"]
    assert len(plants) >= 2
    assert len(payoffs) >= len(plants)
    assert max(c.index for c in plants) < min(c.index for c in payoffs)
    assert all(c.index < len(cases) - 1 for c in payoffs), "un payoff après la conclusion"
    assert abs(sum(c.mots for c in cases) - 1457) <= len(cases)


def test_squelette_place_le_sponsor_et_reste_valide() -> None:
    cases = construire_squelette(
        n_segments=12, mots_cibles=600, mots_hook_max=40, avec_sponsor=True,
        seed=7, duree_cible_s=300.0, intervalle_rupture_s=25.0,
    )
    assert [c.role for c in cases].count("sponsor") == 1
    assert next(c for c in cases if c.role == "sponsor").open_loop == "none"


def test_squelette_pose_une_rupture_par_segment_au_plus() -> None:
    """Le modèle de données n'accepte qu'une rupture par segment : le squelette le respecte."""
    cases = construire_squelette(28, 1457, 36, False, 1, 648.0, 23.4)
    assert all(c.interrupt is None or c.interrupt.at_s_relative >= 0 for c in cases)
    assert cases[0].interrupt is None, "l'accroche ne porte pas de rupture"


# --- référentiel ----------------------------------------------------------------------

def test_tirage_du_hook_est_seede_et_reproductible() -> None:
    premier = referentiel.tirer_type_hook("science_pop", 12345)
    assert referentiel.tirer_type_hook("science_pop", 12345) == premier
    assert premier[0] in referentiel.types_productibles()


def test_intro_chaine_neutre_n_est_jamais_tiree() -> None:
    """`productible: false` dans la taxonomie : le type est observé, jamais produit."""
    assert "intro_chaine_neutre" not in referentiel.types_productibles()
    tires = {referentiel.tirer_type_hook("niche_monetisable_longevite", s)[0] for s in range(200)}
    assert "intro_chaine_neutre" not in tires


def test_plafond_de_hook_vient_de_la_niche() -> None:
    """Le plafond n'est plus fixe : il vaut la médiane mesurée de la niche."""
    valeurs = {n: referentiel.longueur_hook_max(n) for n in referentiel.charger()["niches"]}
    assert len(set(valeurs.values())) > 1, "un plafond identique partout = plafond en dur"
    assert max(valeurs.values()) > 35


# --- research.json --------------------------------------------------------------------

def _fait(identifiant: str = "f01") -> m.Fait:
    return m.Fait(
        id=identifiant, claim="Le sucre ajouté représente une part des apports quotidiens",
        source_url="https://fr.wikipedia.org/wiki/Sucre", source_title="Sucre",
        licence="CC BY-SA 4.0", confidence="high", retrieved_at="2026-09-15T10:00:00Z",
    )


def _recherche(**surcharges) -> m.Research:
    base = dict(
        lang="fr", sujet="Arrêter le sucre", facts=[_fait()], fact_count=1,
        sources=[m.SourceConsultee(
            url="https://fr.wikipedia.org/wiki/Sucre", title="Sucre", api="wikipedia", lang="fr",
            licence="CC BY-SA 4.0", retrieved_at="2026-09-15T10:00:00Z", fact_ids=["f01"])],
        source_count=1, angle="Comparer les apports", angle_signature="comparaison_chiffree",
    )
    return m.Research(**{**base, **surcharges})


def test_research_compte_ses_faits_et_ses_sources() -> None:
    assert _recherche().fact_count == 1
    with pytest.raises(ValidationError, match="fact_count"):
        _recherche(fact_count=9)
    with pytest.raises(ValidationError, match="source_count"):
        _recherche(source_count=9)


def test_research_refuse_un_renvoi_vers_un_fait_inconnu() -> None:
    source = m.SourceConsultee(
        url="https://fr.wikipedia.org/wiki/Sucre", title="Sucre", api="wikipedia", lang="fr",
        licence="CC BY-SA 4.0", retrieved_at="2026-09-15T10:00:00Z", fact_ids=["f99"])
    with pytest.raises(ValidationError, match="f99"):
        _recherche(sources=[source])


def test_research_refuse_un_identifiant_de_fait_en_double() -> None:
    with pytest.raises(ValidationError, match="double"):
        _recherche(facts=[_fait("f01"), _fait("f01")], fact_count=2)


# --- garde-fous posés sur mesure le 15/09/2026 -----------------------------------------

from factory.steps.research import pertinente  # noqa: E402
from factory.steps.script import _normaliser_capitales, _retailler  # noqa: E402

MOTS_CLES = ["sugar", "sucrose", "glucose", "fructose"]


@pytest.mark.parametrize(
    ("titre", "extrait", "attendu"),
    [
        ("Sugar", "Sugar is a sweet carbohydrate; sucrose is its main form", True),
        ("Sucrose", "A compound of glucose and fructose", True),
        # Mesuré : le surnom d'un boxeur passait le filtre à un seul mot-clé.
        ("Sugar Ray Leonard", "Ray Charles Leonard, best known as Sugar Ray, is a boxer", False),
        # Mesuré : un article qui ne doit son passage qu'au mot « health ».
        ("Long-term effects of alcohol", "Alcohol has many health effects on the body", False),
        ("MDMA", "MDMA is a psychoactive drug first synthesized in 1912", False),
    ],
)
def test_pertinence_des_sources(titre: str, extrait: str, attendu: bool) -> None:
    assert pertinente({"title": titre, "extract": extrait}, MOTS_CLES) is attendu


def test_pertinence_ignore_les_locutions() -> None:
    """« quit sugar » n'est le mot d'aucun article : une locution ne peut rien valider."""
    assert pertinente({"title": "X", "extract": "y"}, ["quit sugar", "no sugar diet"]) is True


def test_retaille_par_phrases_entieres() -> None:
    texte = "Première phrase. Deuxième phrase un peu plus longue que la première. Troisième."
    court = _retailler(texte, 4)
    assert court == "Première phrase."
    assert _retailler(texte, 100) == texte, "un segment dans son budget n'est pas touché"


def test_retaille_ne_coupe_jamais_au_milieu_d_une_phrase() -> None:
    monobloc = "un texte sans aucune ponctuation finale mais vraiment très long pour le budget"
    assert _retailler(monobloc, 3) == monobloc


def test_capitales_rendues_a_la_casse_de_phrase() -> None:
    """`narration` est le seul texte envoyé au TTS : des capitales y font épeler des sigles."""
    assert _normaliser_capitales("ET SI LE SUCRE ÉTAIT UN CODE ? IL L'EST.").startswith("Et si")
    intact = "Une phrase normale avec un SIGLE dedans."
    assert _normaliser_capitales(intact) == intact


def test_ligne_de_divulgation_orale_n_est_jamais_un_hashtag() -> None:
    """`#ad` ne se prononce pas : la ligne orale retombe sur la mention générique de la langue."""
    from factory.core.config import charger
    from factory.steps.script import _lignes_divulgation

    cfg = charger(strict=False)
    produit = cfg.products[sorted(cfg.products)[0]]
    for lang in ("fr", "en"):
        lignes = _lignes_divulgation(produit, cfg, lang)
        assert not lignes.spoken_line.startswith("#")
        assert lignes.spoken_line == cfg.languages[lang].disclosure.overlay_generic
        # La mention contractuelle du réseau reste intacte en description.
        assert lignes.description_line == cfg.languages[lang].disclosure.pour_reseau(
            produit.network)
