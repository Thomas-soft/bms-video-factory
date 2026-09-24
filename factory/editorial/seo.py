"""Référencement : description structurée, chapitres, tags, hashtags, sub-ID, commentaire épinglé.

Tout ce que `publish` enverra à l'API se compose ici, et **rien ne s'écrit à la main** : chaque
bloc vient d'un fichier du run ou de la configuration. Six points méritent d'être lus avant d'y
toucher.

- **Les chapitres sont des horodatages réels**, pris de `voice/timings.json` : ils ne peuvent
  donc pas mentir sur ce que la vidéo contient. YouTube exige un premier chapitre à `0:00`, au
  moins trois chapitres et 10 s d'écart minimal ; en dessous, aucun ne s'affiche.
- **Le sommaire n'est pas les chapitres.** Les chapitres donnent le *quand* ; le sommaire donne
  le *quoi*, et c'est lui que lisent les deux lignes visibles avant « …plus ». Il est composé
  des textes à l'écran du script, qui ont déjà été écrits pour être lus.
- **Le plafond de description se compte en octets, pas en caractères.** L'API dit 5 000 octets ;
  un tiret cadratin en vaut trois et une apostrophe typographique aussi. Une description de
  4 990 caractères bien française passe les 5 000 octets sans prévenir.
- **Un tag qui contient une espace coûte deux caractères de plus.** Règle de l'API : « if your
  request contains a tag with a space, the API server handles the tag value as though it were
  wrapped in quotation marks ». Compter sans les guillemets est le moyen d'obtenir un
  `400 invalidTags` sur une liste qu'on croyait au ras des 500.
- **Le sous-identifiant d'affiliation ne contient jamais de donnée personnelle** : `channel_id`,
  code de langue et `video_id`, rien d'autre. C'est la contrainte de CJ (« no personal
  information »), et c'est aussi la seule information dont la mesure par vidéo a besoin.
- **Le commentaire épinglé porte le même sous-identifiant que la description.** Deux liens sur
  la même vidéo avec deux sub-ID différents rendraient l'attribution par vidéo illisible.
"""

from __future__ import annotations

import re
from pathlib import Path

from factory.core import config as config_module
from factory.monetization import links
from factory.core.models import (
    Asset,
    BlocsDescription,
    Chapitre,
    Channel,
    Language,
    LibellesDescription,
    LienAffiliation,
    Research,
    RunManifest,
    Script,
    Timings,
    VideoMetadata,
    VideoSpec,
)

#: Écart minimal entre deux chapitres YouTube. Sous 10 s, le lecteur n'en affiche aucun.
ECART_CHAPITRE_MIN_S = 10.0
#: Nombre de chapitres visé au plus. Le contrat YouTube n'impose qu'un plancher de 3 et 10 s
#: d'écart ; un chapitre toutes les 20 secondes (27 sur 12 minutes, mesuré à l'étape 13.2)
#: n'est plus un sommaire, c'est la transcription du script.
CHAPITRES_MAX = 12
#: Plafond cumulé des tags, imposé par l'API. Se compte guillemets compris.
TAGS_MAX_CARACTERES = 500
#: Plafond de description, **en octets** — c'est ainsi que l'API le compte.
DESCRIPTION_MAX_OCTETS = 5000
#: Place réservée à la ligne de renvoi quand tous les crédits ne tiennent pas.
RENVOI_CREDITS_MAX = 140
#: Hashtags affichés au-dessus du titre. Au-delà de 60 dans la description, YouTube les ignore
#: tous — on en pose trois, ce qui est le nombre affiché.
HASHTAGS_AFFICHES = 3
#: Lignes du sommaire. Trois à cinq : au-delà, il double le bloc de chapitres.
SOMMAIRE_LIGNES = 4


# --------------------------------------------------------------------------------------
# Chapitres
# --------------------------------------------------------------------------------------

#: Mots outils des quatre langues publiées. Un titre de chapitre qui finit dessus est un
#: titre coupé au milieu d'une phrase — « Cinquante minutes de travail s'achètent avec ».
MOTS_SUSPENDUS = {
    "de", "du", "des", "le", "la", "les", "un", "une", "et", "ou", "à", "au", "aux", "en",
    "pour", "avec", "sans", "par", "sur", "dans", "que", "qui", "dont", "se", "ce", "cet",
    "the", "a", "an", "of", "to", "for", "with", "and", "or", "in", "on", "by", "that",
    "el", "los", "las", "y", "con", "para", "il", "lo", "gli", "e", "per", "da",
}


def _titre_depuis_narration(narration: str) -> str:
    """Premiers mots d'une phrase, sans finir sur un mot outil qui appelle une suite."""
    phrase = re.split(r"(?<=[.!?,;:])\s+", narration.strip())[0]
    mots = phrase.split()[:7]
    while mots and mots[-1].lower().strip(",;:'’") in MOTS_SUSPENDUS:
        mots.pop()
    return " ".join(mots)


def _nettoyer_titre(texte: str) -> str:
    """Titre de chapitre : pas de retour à la ligne, pas de ponctuation finale."""
    return re.sub(r"\s+", " ", texte).strip().rstrip(".,;:").strip()


def _casse_de_chapitre(texte: str, majuscules: str) -> str:
    """Un texte à l'écran est écrit en capitales ; une description se lit en casse normale.

    Le texte n'est **pas** recasé quand il n'est pas crié : le script l'a écrit ainsi, et
    décider de sa casse ici reviendrait à corriger le script depuis la description. Seule la
    première lettre est relevée — « how did it Grow » en tête de ligne est une coquille, pas
    une intention (mesuré sur le run `avwf`, 20/09/2026).
    """
    if not texte.isupper():
        return texte[:1].upper() + texte[1:] if texte else texte
    if majuscules == "title_case":
        # Le premier mot est capitalisé quelle que soit sa longueur : c'est la règle de la
        # casse de titre anglaise, et sans elle « HOW DID IT GROW » sort en « how did it Grow ».
        mots = [m.capitalize() if len(m) > 3 else m.lower() for m in texte.split()]
        if mots:
            mots[0] = mots[0].capitalize()
        return " ".join(mots).strip()
    minuscule = texte.lower()
    return minuscule[:1].upper() + minuscule[1:]


def chapitres_depuis_timings(
    timings: Timings, script: Script, duree_s: float | None = None,
    majuscules: str = "phrase_case",
) -> tuple[list[Chapitre], list[str]]:
    """Un chapitre par segment de script, espacés d'au moins `ecart`, au plus `CHAPITRES_MAX`.

    Le titre vient du texte à l'écran du segment quand il existe (il a été écrit pour être
    lu), sinon des premiers mots de la narration. Aucun titre n'est inventé.
    """
    alertes: list[str] = []
    par_id = {s.id: s for s in script.segments}
    chapitres: list[Chapitre] = []
    ecart = ECART_CHAPITRE_MIN_S
    if duree_s:
        ecart = max(ECART_CHAPITRE_MIN_S, duree_s / CHAPITRES_MAX)
    for segment in timings.segments:
        source = par_id.get(segment.id)
        if source is None:
            continue
        brut = (source.on_screen_text or "").strip() or _titre_depuis_narration(source.narration)
        titre = _casse_de_chapitre(_nettoyer_titre(brut), majuscules)
        # Le script réemploie parfois le même texte à l'écran à deux endroits (« Arrivée à
        # l'objectif » deux fois sur le run FR du 17/09) : deux chapitres du même nom ne
        # servent à personne. On retombe sur la narration, puis on saute.
        if titre.lower() in {c.title.lower() for c in chapitres}:
            titre = _casse_de_chapitre(
                _nettoyer_titre(_titre_depuis_narration(source.narration)), majuscules
            )
            if titre.lower() in {c.title.lower() for c in chapitres}:
                continue
        if not titre:
            continue
        debut = 0.0 if not chapitres else round(segment.start_s, 1)
        if chapitres and debut - chapitres[-1].start_s < ecart:
            continue  # fusionné dans le précédent : YouTube refuserait l'affichage
        if duree_s is not None and debut > duree_s - ECART_CHAPITRE_MIN_S:
            continue
        chapitres.append(Chapitre(start_s=debut, title=titre[:95]))
    if chapitres and chapitres[0].start_s != 0:
        chapitres[0] = Chapitre(start_s=0.0, title=chapitres[0].title)
    if len(chapitres) < 3:
        alertes.append(
            f"{len(chapitres)} chapitre(s) construits : YouTube en exige 3 — "
            "la description sortira sans sommaire"
        )
        return [], alertes
    return chapitres, alertes


# --------------------------------------------------------------------------------------
# Blocs de description
# --------------------------------------------------------------------------------------


def accroche(script: Script) -> str:
    """Deux lignes reprenant le hook : la promesse, puis ce que la vidéo tient."""
    hook = script.hook.text.strip().rstrip(".")
    premier = next((s for s in script.segments if s.role != "hook"), None)
    seconde = (premier.narration.strip() if premier else script.hook.text)
    seconde = re.split(r"(?<=[.!?])\s+", seconde)[0].strip()
    return f"{hook}.\n{seconde}"


def sommaire(script: Script, majuscules: str = "phrase_case") -> list[str]:
    """Trois à cinq lignes qui disent ce que la vidéo contient, avant les horodatages.

    Prises des textes à l'écran du script, en sautant le hook (il est déjà l'accroche) et les
    segments promotionnels (le sommaire décrit la vidéo, pas la publicité). Si le script n'en
    porte pas assez, le bloc sort plus court plutôt qu'inventé.
    """
    lignes: list[str] = []
    vues: set[str] = set()
    for segment in script.segments:
        if segment.role in {"hook", "sponsor"}:
            continue
        brut = (segment.on_screen_text or "").strip()
        if not brut:
            continue
        ligne = _casse_de_chapitre(_nettoyer_titre(brut), majuscules)
        if not ligne or ligne.lower() in vues:
            continue
        vues.add(ligne.lower())
        lignes.append(ligne)
        if len(lignes) >= SOMMAIRE_LIGNES:
            break
    return lignes


def sources(research: Research | None) -> list[str]:
    """Une ligne par source consultée, avec sa licence — les faits du script viennent d'elles."""
    if research is None:
        return []
    lignes = []
    for source in research.sources:
        licence = f" ({source.licence})" if source.licence else ""
        lignes.append(f"{source.title} — {source.url}{licence}")
    return lignes


def attribution(assets: list[Asset], libelles: LibellesDescription | None = None) -> list[str]:
    """Bloc d'attribution des assets : une ligne par exigence distincte, jamais 127 lignes.

    Les images générées localement portent la licence du modèle : elle n'exige pas de crédit,
    mais la dire coûte une ligne et documente la provenance (RIA art. 50, C2PA § 4).
    """
    libelles = libelles or LibellesDescription()
    lignes: list[str] = []
    vues: set[str] = set()
    for asset in assets:
        if asset.attribution_line:
            cle = asset.attribution_line
        elif asset.provider in {"flux", "mflux", "sdxl"}:
            cle = (f"{libelles.generated_locally} — {asset.generator.model}"
                   if asset.generator else f"{libelles.generated_locally} ({asset.provider})")
        else:
            auteur = asset.author or asset.provider
            cle = f"{auteur} — {asset.licence}"
        if cle not in vues:
            vues.add(cle)
            lignes.append(cle)
    return lignes


def ligne_divulgation_ia(
    langue: Language, manifest: RunManifest, virtuelles: bool
) -> str | None:
    """Divulgation IA de `CONFORMITE` § 3, dans la langue, sans rien revendiquer de faux."""
    morceaux: list[str] = []
    if virtuelles and langue.disclosure.virtual_images:
        morceaux.append(langue.disclosure.virtual_images.strip().rstrip(".") + ".")
    if langue.disclosure.ia_production:
        morceaux.append(langue.disclosure.ia_production.strip())
    relecteur = manifest.conformite.reviewer
    humain = relecteur not in (None, "", "auto-approve")
    if humain and langue.disclosure.ia_controle_humain:
        morceaux.append(langue.disclosure.ia_controle_humain.strip())
    return " ".join(morceaux) or None


# --------------------------------------------------------------------------------------
# Affiliation et sous-identifiant
# --------------------------------------------------------------------------------------


def produits_de(channel: Channel, cfg: config_module.ConfigSet, spec: VideoSpec) -> list:
    """Produits applicables à ce run : celui de la spec s'il est nommé, sinon ceux de la chaîne."""
    if spec.product_id and spec.product_id in cfg.products:
        return [cfg.products[spec.product_id]]
    return [cfg.products[p] for p in channel.products if p in cfg.products]


def url_avec_subid(produit, channel: Channel, video_id: str) -> tuple[str, str | None]:
    """URL suivie et sous-identifiant ; construits par `factory/monetization/links.py` (étape 27)."""
    lien = links.lien_pour(produit, channel.id, channel.lang, video_id)
    return lien.target_url, lien.subid_value


def bloc_affiliation(
    channel: Channel, cfg: config_module.ConfigSet, langue: Language, spec: VideoSpec
) -> tuple[list[str], list[LienAffiliation]]:
    """Bloc « Publicité » : mention légale, puis par produit l'appel, le lien et ses mentions."""
    produits = produits_de(channel, cfg, spec)
    if not produits:
        return [], []
    # Première ligne : mention générique + mention de chaque réseau (precheck 7-9 l'exige en
    # tête de description ; défaut constaté à l'étape 27, le bloc ouvrait sur la seule générique).
    lignes = [links.ligne_de_tete(produits, langue)]
    liens: list[LienAffiliation] = []
    for produit in produits:
        lien = links.lien_pour(produit, channel.id, channel.lang, spec.video_id)
        lignes.extend(links.lignes_produit(produit, lien, langue, channel.lang, lignes[0]))
        liens.append(lien)
    return lignes, liens


def commentaire_epingle(
    script: Script, channel: Channel, cfg: config_module.ConfigSet, langue: Language,
    spec: VideoSpec,
) -> str | None:
    """Question d'engagement, puis le lien produit **avec le même sous-identifiant**.

    La question sort du script, jamais d'un gabarit : le segment `cta` d'abord (il est écrit
    pour appeler une réponse), le hook ensuite. Un commentaire épinglé qui parle d'autre chose
    que la vidéo est un commentaire que personne ne lit. Sans question ni produit, il n'y a pas
    de commentaire — en poser un vide coûterait un appel d'API pour rien.
    """
    question = ""
    sources_question = [s.narration for s in script.segments if s.role == "cta"]
    sources_question.append(script.hook.text)
    for texte in sources_question:
        phrases = re.split(r"(?<=[.!?])\s+", texte.strip())
        question = next((p.strip() for p in phrases if p.strip().endswith("?")), "")
        if question:
            break
    if not question:
        # Le script de ce run n'a posé aucune question — c'est fréquent sur un hook narratif.
        # Le repli vient de la langue, jamais d'une phrase écrite dans le code.
        question = langue.titres.question_engagement.strip()
    produits = produits_de(channel, cfg, spec)
    lignes = [question] if question else []
    if produits:
        tete = links.ligne_de_tete(produits, langue)
        lignes.append(tete)
        for produit in produits:
            lien = links.lien_pour(produit, channel.id, channel.lang, spec.video_id)
            lignes.extend(links.lignes_produit(produit, lien, langue, channel.lang, tete))
    return "\n".join(lignes) if lignes else None


# --------------------------------------------------------------------------------------
# Tags et hashtags
# --------------------------------------------------------------------------------------


def cout_tag(tag: str) -> int:
    """Coût d'un tag dans le budget de 500 caractères, **guillemets compris** (règle de l'API)."""
    return len(tag) + (2 if " " in tag else 0)


def tags(
    script: Script, channel: Channel, research: Research | None,
    suggestions: list[str] | None = None,
) -> list[str]:
    """Mots-clés **dans la langue de la vidéo**, coupés au plafond cumulé de 500 caractères.

    **Le sujet du run n'entre pas dans les tags.** Il vient du corpus de l'étape 3, souvent
    anglophone : recopié tel quel, il produit des tags anglais sur une vidéo française
    (mesuré à l'étape 13.2 — « what happens every when », « sugar »). Les entités de la
    recherche et les textes à l'écran du script, eux, sont écrits dans la langue du run.

    Les `suggestions` viennent de l'autocomplete YouTube (étape 19) : ce sont des requêtes
    réellement tapées, donc les meilleurs mots-clés disponibles gratuitement. Elles passent
    **en tête** quand elles existent, et la fonction marche sans elles.
    """
    candidats: list[str] = list(suggestions or [])
    if research is not None:
        candidats += [e.name.lower() for e in research.entities[:12]]
    textes_ecran = [s.on_screen_text.lower() for s in script.segments if s.on_screen_text]
    candidats += textes_ecran[:10]
    for texte in textes_ecran[:10]:  # les mots seuls sont de meilleurs mots-clés que la phrase
        candidats += [m for m in texte.split() if len(m) > 4]
    candidats += [channel.niche.replace("_", " "), channel.name.lower()]

    retenus: list[str] = []
    vus: set[str] = set()
    cumul = 0
    for brut in candidats:
        tag = re.sub(r"\s+", " ", brut).strip().strip("-'").lower()
        if len(tag) < 3 or len(tag) > 40 or tag in vus:
            continue
        cout = cout_tag(tag) + (1 if retenus else 0)
        if cumul + cout > TAGS_MAX_CARACTERES:
            break
        vus.add(tag)
        retenus.append(tag)
        cumul += cout
    return retenus


def hashtags(liste_tags: list[str], prioritaires: list[str] | None = None) -> list[str]:
    """Trois au plus, affichés au-dessus du titre : les tags d'un seul mot font l'affaire.

    L'ordre compte, parce que ces trois-là sont les seuls que YouTube montre. Les mots qui
    nomment le **sujet** (entités de la recherche, niche) passent avant ceux qui viennent du
    découpage des textes à l'écran : sans cela, une vidéo sur l'univers sort « #billion
    #light #years » là où « #universe #space » dit de quoi elle parle (mesuré sur le run
    `avwf`, 20/09/2026).
    """
    simples = [t for t in liste_tags if " " not in t and t.isalpha()]
    tete = [t for t in simples if t in set(prioritaires or [])]
    reste = [t for t in simples if t not in set(tete)]
    return [f"#{t}" for t in (tete + reste)[:HASHTAGS_AFFICHES]]


def suggestions_autocomplete(
    sujet: str, langue_code: str, racine: Path | None = None, n: int = 6
) -> list[str]:
    """Suggestions de l'autocomplete YouTube pour le sujet, ou `[]` si la source est muette.

    Réseau **facultatif** : l'étape 19 met ces réponses en cache 14 jours et la fonction rend
    une liste vide au moindre refus. Une métadonnée ne bloque pas un run parce qu'un point
    d'entrée non documenté n'a pas répondu.
    """
    try:
        from factory.editorial import demand
    except ImportError:
        return []
    try:
        brutes = demand.autocomplete_youtube(sujet, hl=langue_code, racine=racine)
    except Exception:                                    # noqa: BLE001 — source non documentée
        return []
    sorties: list[str] = []
    for suggestion in brutes:
        propre = re.sub(r"\s+", " ", suggestion).strip().lower()
        if not 3 <= len(propre) <= 40:
            continue
        # Une suggestion qui prolonge une suggestion déjà retenue ne couvre pas une requête
        # de plus : elle couvre la même. Mesuré le 20/09 sur « mysteries of the universe »,
        # qui revenait cinq fois de suite (« … book », « … in hindi », « … in tamil »…) et
        # consommait 150 des 500 caractères de tags pour une seule idée.
        if any(propre.startswith(deja) or deja.startswith(propre) for deja in sorties):
            continue
        sorties.append(propre)
        if len(sorties) >= n:
            break
    return sorties


# --------------------------------------------------------------------------------------
# Localisations
# --------------------------------------------------------------------------------------


def localizations(
    channel: Channel, cfg: config_module.ConfigSet, titre: str, description: str
) -> dict[str, dict[str, str]]:
    """`{lang: {title, description}}` pour les autres langues des chaînes BMS.

    **Vide aujourd'hui, et c'est voulu.** La langue de production est l'anglais seulement
    (arbitrage d'Alek du 15/09/2026) et l'étape 24 — déclinaison multilingue — est différée.
    Traduire ici avec le LLM produirait des localisations que personne n'a relues, sur des
    chaînes qui n'existent pas. La fonction rend donc la structure exacte que `videos.update`
    attend, remplie des seules langues pour lesquelles une chaîne BMS existe **et** dont une
    traduction relue est disponible — c'est-à-dire aucune, tant que l'étape 24 n'a pas tourné.

    Elle n'est pas morte pour autant : elle porte la langue par défaut, qui est ce que l'API
    exige pour que `defaultLanguage` soit accepté avec un bloc `localizations`.
    """
    autres = sorted({c.lang for c in cfg.channels.values()} - {channel.lang})
    sorties: dict[str, dict[str, str]] = {}
    for code in autres:
        traduction = channel.localizations.get(code)
        if traduction is not None:
            sorties[code] = {
                "title": traduction.title[:100],
                "description": traduction.description or description,
            }
    if sorties:
        sorties[channel.lang] = {"title": titre, "description": description}
    return sorties


# --------------------------------------------------------------------------------------
# Composition de la description
# --------------------------------------------------------------------------------------

#: Lignes de crédit qu'un dégraissage a dû laisser hors description, pour l'alerte de l'étape.
credits_omis: list[str] = []


def _lignes_chapitres(chapitres: list[Chapitre]) -> str:
    return "\n".join(f"{c.horodatage()} {c.title}" for c in chapitres)


def composer_description(blocs: BlocsDescription, hashtags_liste: list[str] | None = None,
                         libelles: LibellesDescription | None = None) -> str:
    """Ordre de composition, et **il n'est pas celui d'`INTERFACES`** quand il y a promotion.

    `INTERFACES` § metadata.json donne : divulgation → accroche → chapitres → affiliation →
    attribution → crédit musical. Mais `CONFORMITE` § 3 couche 3 est plus strict et prime :
    la mention commerciale se place *« en première ligne de description […] avant toute autre
    ligne — y compris avant le bloc d'attribution des assets »*. Le bloc d'affiliation passe
    donc **en tête** dès qu'il existe, et la divulgation IA le suit. Sans produit, l'ordre
    d'`INTERFACES` s'applique tel quel.

    Les hashtags ferment la description : ceux qui y figurent sont ceux que YouTube affiche
    au-dessus du titre, et les mettre en tête volerait les deux lignes visibles à l'accroche.
    """
    libelles = libelles or LibellesDescription()
    parties: list[str] = []
    if blocs.affiliate:
        parties.append("\n".join(blocs.affiliate))
    if blocs.disclosure:
        parties.append(blocs.disclosure)
    parties.append(blocs.hook)
    if blocs.summary:
        parties.append("\n".join(f"• {ligne}" for ligne in blocs.summary))
    if blocs.chapters:
        parties.append(_lignes_chapitres(blocs.chapters))
    if blocs.sources:
        parties.append(f"{libelles.sources} :\n" + "\n".join(f"— {s}" for s in blocs.sources))
    if blocs.attribution:
        parties.append(f"{libelles.credits} :\n"
                       + "\n".join(f"— {a}" for a in blocs.attribution))
    if blocs.music_credit:
        parties.append(blocs.music_credit)
    if hashtags_liste:
        parties.append(" ".join(hashtags_liste))
    texte = "\n\n".join(parties)
    credits_omis.clear()
    if len(texte.encode("utf-8")) <= DESCRIPTION_MAX_OCTETS:
        return texte
    return _degraisser(parties, blocs, libelles)


def _octets(texte: str) -> int:
    return len(texte.encode("utf-8"))


def _degraisser(parties: list[str], blocs: BlocsDescription,
                libelles: LibellesDescription | None = None) -> str:
    """Ramène la description sous le plafond **sans jamais couper un crédit en deux**.

    Le style documentaire a fait apparaître ce cas, que le style illustré ne pouvait pas
    produire : une vidéo montée sur cent photographies CC-BY porte cent lignes d'attribution
    distinctes, là où cent images générées n'en portent qu'une. Un `[:5000]` tranchait alors au
    milieu du bloc de crédits — donc au milieu du nom d'un auteur — et **une attribution CC-BY
    coupée en deux est un manquement à la licence**, pas un défaut de mise en page.

    Ordre de sacrifice, du moins coûteux au plus coûteux : sommaire, puis chapitres (confort de
    lecture), puis sources (traçabilité éditoriale, que `review.json` porte de toute façon). Les
    crédits viennent en dernier et ne sont **jamais tronqués au caractère** : s'il en reste trop,
    les lignes entières qui ne tiennent pas sont retirées, comptées, et remplacées par une ligne
    qui dit combien et où les lire. `metadata.json` garde le tableau `attribution` **complet**
    quoi qu'il arrive, et `assets/<shot>/licence.json` reste l'enregistrement qui fait foi.

    La vraie correction n'est pas ici : elle est dans `PEXELS_KEY`, dont la licence n'exige
    aucun crédit par œuvre (`SUIVI.md` § 1).
    """
    libelles = libelles or LibellesDescription()
    credits_omis.clear()
    sacrifiables = []
    if blocs.summary:
        sacrifiables.append("\n".join(f"• {ligne}" for ligne in blocs.summary))
    if blocs.chapters:
        sacrifiables.append(_lignes_chapitres(blocs.chapters))
    if blocs.sources:
        sacrifiables.append(f"{libelles.sources} :\n"
                            + "\n".join(f"— {s}" for s in blocs.sources))
    restant = list(parties)
    for bloc in sacrifiables:
        if bloc in restant:
            restant.remove(bloc)
        if _octets("\n\n".join(restant)) <= DESCRIPTION_MAX_OCTETS:
            return "\n\n".join(restant)

    bloc_credits = next((b for b in restant if b.startswith(f"{libelles.credits} :")), None)
    if bloc_credits is None:
        return _couper_octets("\n\n".join(restant))
    autres = [b for b in restant if b is not bloc_credits]
    position = restant.index(bloc_credits)
    budget = DESCRIPTION_MAX_OCTETS - _octets("\n\n".join(autres)) - 2 * max(len(autres), 1)

    gardees: list[str] = []
    longueur = _octets(f"{libelles.credits} :")
    for ligne in blocs.attribution:
        cout = _octets(ligne) + 3                      # « — » et le retour à la ligne
        if longueur + cout > budget - RENVOI_CREDITS_MAX:
            credits_omis.append(ligne)
            continue
        gardees.append(ligne)
        longueur += cout
    corps = f"{libelles.credits} :\n" + "\n".join(f"— {a}" for a in gardees)
    if credits_omis:
        corps += (f"\n— … et {len(credits_omis)} autres crédits, listés en entier dans le "
                  f"manifeste de la vidéo (`metadata.json`, champ `attribution`).")
    final = list(autres)
    final.insert(min(position, len(final)), corps)
    return _couper_octets("\n\n".join(final))


def _couper_octets(texte: str) -> str:
    """Coupe au plafond **en octets**, sans jamais laisser un caractère à moitié encodé."""
    brut = texte.encode("utf-8")
    if len(brut) <= DESCRIPTION_MAX_OCTETS:
        return texte
    return brut[:DESCRIPTION_MAX_OCTETS].decode("utf-8", errors="ignore")


# --------------------------------------------------------------------------------------
# Assemblage
# --------------------------------------------------------------------------------------


def composer(
    spec: VideoSpec,
    script: Script,
    timings: Timings,
    research: Research | None,
    manifest: RunManifest,
    channel: Channel,
    cfg: config_module.ConfigSet,
    langue: Language,
    titre: str,
    miniature: str | None,
    synthetique: bool,
    motif_synthetique: str | None,
    virtuelles: bool,
    racine: Path | None = None,
    reseau: bool = True,
) -> tuple[VideoMetadata, list[LienAffiliation], list[str]]:
    """Compose `metadata.json` en entier. Renvoie `(metadata, liens d'affiliation, alertes)`."""
    alertes: list[str] = []
    majuscules = langue.typographie.majuscules_titre

    lignes_affiliation, liens = bloc_affiliation(channel, cfg, langue, spec)
    paid = bool(lignes_affiliation)
    for lien in liens:
        if lien.subid_value is None:
            alertes.append(
                f"produit {lien.network} : aucun sous-identifiant par vidéo "
                "(le réseau ne le permet pas) — la rentabilité par vidéo n'est pas mesurable"
            )

    chapitres, dits = chapitres_depuis_timings(
        timings, script, manifest.decisions.duration_s or timings.total_duration_s, majuscules
    )
    alertes += dits

    musique = manifest.decisions.music_track
    credit_musique = None
    if musique and musique.attribution_required:
        credit_musique = musique.credit_line
    elif musique:
        credit_musique = f"Musique : {musique.track_title} ({musique.licence})"
    elif manifest.decisions.music_warning:
        alertes.append("aucune musique : " + manifest.decisions.music_warning[:120])

    suggestions = (
        suggestions_autocomplete(spec.topic.sujet, channel.lang, racine) if reseau else []
    )
    liste_tags = tags(script, channel, research, suggestions)
    # Ce qui nomme le sujet, par ordre de fiabilité : les requêtes réellement tapées
    # (autocomplete), puis les entités de la recherche, puis le sujet du run et la niche.
    # Les entités sont vides sur les runs d'avant l'étape 17 — d'où les trois sources.
    mots_du_sujet = [mot for suggestion in suggestions for mot in suggestion.lower().split()]
    mots_du_sujet += [mot for entite in (research.entities[:12] if research else [])
                      for mot in entite.name.lower().split()]
    mots_du_sujet += spec.topic.sujet.lower().split()
    mots_du_sujet += channel.niche.replace("_", " ").split()
    liste_hashtags = hashtags(liste_tags, mots_du_sujet)

    blocs = BlocsDescription(
        disclosure=ligne_divulgation_ia(langue, manifest, virtuelles),
        hook=accroche(script),
        summary=sommaire(script, majuscules),
        chapters=chapitres,
        sources=sources(research),
        affiliate=lignes_affiliation,
        attribution=attribution(manifest.decisions.assets, langue.libelles),
        music_credit=credit_musique,
    )
    description = composer_description(blocs, liste_hashtags, langue.libelles)
    if credits_omis:
        # Bloquant à l'upload, pas ici : `metadata.json` porte les crédits en entier, mais la
        # description publiée n'en montre qu'une partie. CC-BY exige le crédit « d'une manière
        # raisonnable au support » — une liste tronquée par le plafond de YouTube ne l'est pas.
        alertes.append(
            f"{len(credits_omis)} crédit(s) hors description : le bloc d'attribution dépasse "
            f"les {DESCRIPTION_MAX_OCTETS} octets de YouTube. `metadata.json` les garde tous ; "
            f"la description publiée renvoie au manifeste. À régler avant publication — "
            f"poser PEXELS_KEY supprime le problème (licence sans crédit par œuvre)."
        )

    metadata = VideoMetadata(
        title_chosen=titre,
        title_variants=manifest.decisions.title_variants,
        description=description,
        description_blocks=blocs,
        tags=liste_tags,
        hashtags=liste_hashtags,
        localizations=localizations(channel, cfg, titre, description),
        pinned_comment=commentaire_epingle(script, channel, cfg, langue, spec),
        category_id=channel.youtube.category_id,
        default_language=channel.lang,
        default_audio_language=channel.lang,
        recording_date=None,
        chapters=chapitres,
        contains_synthetic_media=synthetique,
        contains_synthetic_media_reason=motif_synthetique,
        paid_promotion=paid,
        made_for_kids=False,
        notify_subscribers=channel.youtube.notify_subscribers,
        playlist_id=channel.youtube.playlist_id,
        caption_file="subtitles.srt",
        thumbnail_file="thumbnail.png",
    )
    if miniature is None:
        alertes.append("aucune miniature au manifeste : thumbnail_file pointe un fichier absent")
    if len(titre) > 70:
        alertes.append(f"titre de {len(titre)} caractères : au-delà de 70, YouTube tronque")
    if len(liste_hashtags) < HASHTAGS_AFFICHES:
        alertes.append(f"{len(liste_hashtags)} hashtag(s) pour {HASHTAGS_AFFICHES} affichés "
                       "par YouTube : les tags d'un seul mot manquent")
    return metadata, liens, alertes
