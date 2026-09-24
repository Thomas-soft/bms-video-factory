"""`factory thumbnail` — titres en variantes, trois miniatures mesurées, plan de rotation.

L'étape orchestre ; elle ne compose pas et elle ne note pas. Les titres viennent de
`factory/editorial/titles.py`, les miniatures et leurs mesures de
`factory/editorial/thumbnails_variants.py`. Ce qui reste ici est ce qui appartient au run :
choisir le fond, écrire les fichiers, remplir le manifeste.

Trois décisions portent cette étape.

1. **La miniature ne connaît pas le titre.** Elle passe avant `metadata` dans le DAG
   (`INTERFACES` § thumbnails.json) : son texte vient du script et du corpus de la niche,
   jamais d'un titre qui n'existe pas encore. C'est `titles` qui produit les deux familles,
   et `metadata` qui constate ensuite ce que la miniature a retenu.
2. **Le fond est une image du run, jamais une image neuve.** Générer une image de plus
   coûterait ~99 s (mesure de l'étape 12.2) pour une image que personne n'a validée. Le LLM
   choisit parmi les intentions visuelles déjà rendues ; à défaut, c'est l'image du plan de
   hook.
3. **Les trois variantes sont conservées, et un plan de rotation part avec elles.** YouTube
   n'expose aucun test A/B par API (étape 21) : la comparaison se fera par rotation mesurée,
   dont le plan est écrit ici et exécuté par la phase 5.
"""

from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

from factory.core import config as config_module
from factory.core import db, runs
from factory.core.models import (
    RotationMiniature,
    Script,
    Shotlist,
    VarianteMiniature,
    VideoSpec,
)
from factory.core.paths import RunPaths, racine_projet
from factory.editorial import thumbnails_variants as variantes_module
from factory.editorial import titles
from factory.editorial.thumbnails_variants import (
    CRITERE_ROTATION,
    HAUTEUR,
    LARGEUR,
    N_VARIANTES,
    POIDS_MAX_MO,
    ROTATION_APRES_JOURS,
    MiniatureImpossible,
    contraste_wcag,
)
from factory.llm import ErreurLLM, TraceLLM, generate_json

__all__ = [
    "HAUTEUR",
    "LARGEUR",
    "N_VARIANTES",
    "POIDS_MAX_MO",
    "MiniatureImpossible",
    "ResultatMiniature",
    "contraste_wcag",
    "executer",
]


@dataclass
class ResultatMiniature:
    """Ce que l'étape a produit et mesuré."""

    variantes: list[VarianteMiniature]
    retenue: str
    motif: str
    fond: Path
    fond_shot: str
    fond_source: str
    gabarit: str
    titre_retenu: str
    n_titres: int
    secondes: float
    secondes_llm: float
    rotation: RotationMiniature | None = None
    duels: list[str] = field(default_factory=list)
    promesse_tenue: bool | None = None
    appels_caches: int = 0
    alertes: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------------------
# Choix du fond
# --------------------------------------------------------------------------------------


def _images_disponibles(chemins: RunPaths, shotlist: Shotlist) -> list[tuple[str, Path, str]]:
    """`(shot_id, image, intention visuelle)` pour chaque plan dont l'image existe."""
    trouvees: list[tuple[str, Path, str]] = []
    for shot in shotlist.shots:
        image = chemins.asset_dir(shot.id) / "image.png"
        if image.exists():
            trouvees.append((shot.id, image, shot.visual_intent))
    return trouvees


def _choisir_fond(
    candidats: list[tuple[str, Path, str]], sujet: str, racine: Path | None, trace: TraceLLM
) -> tuple[str, str]:
    """Plan dont l'image fera le fond, par choix du LLM sur les intentions visuelles.

    Le premier candidat est le plan de hook : c'est lui qui gagne si le LLM échoue ou
    désigne un plan inconnu. Aucun pixel n'est regardé ici — le modèle retenu est textuel.
    """
    liste = "\n".join(f"{i}. {intent[:110]}" for i, (_sid, _img, intent) in enumerate(candidats))
    try:
        donnees, _ = generate_json(
            f"Sujet de la vidéo : {sujet}\n\n"
            f"Voici les images déjà produites pour cette vidéo, décrites par leur intention "
            f"visuelle :\n{liste}\n\n"
            "Laquelle ferait la miniature la plus forte — celle qui donne envie de cliquer, "
            "avec un sujet clair et lisible en tout petit ? Réponds par un objet JSON "
            '{"index": <numéro>, "motif": "<dix mots au plus>"}.',
            system="Tu choisis une image de miniature. Tu réponds uniquement en JSON valide.",
            json_schema={
                "type": "object", "required": ["index"],
                "properties": {"index": {"type": "integer"}, "motif": {"type": "string"}},
            },
            max_tokens=120, temperature=0.4, etiquette="thumbnail_fond",
            trace=trace, racine=racine,
        )
        index = int(donnees.get("index", 0))
        if 0 <= index < len(candidats):
            motif = str(donnees.get("motif", "")).strip()[:80] or "choix LLM"
            return candidats[index][0], f"llm : {motif}"
    except (ErreurLLM, ValueError, TypeError, KeyError) as erreur:
        return candidats[0][0], f"plan de hook (choix LLM indisponible : {erreur})"
    return candidats[0][0], "plan de hook (index LLM hors liste)"


# --------------------------------------------------------------------------------------
# Étape
# --------------------------------------------------------------------------------------


def executer(
    video_id: str, variantes: int = N_VARIANTES, racine: Path | None = None
) -> ResultatMiniature:
    """Compose `thumbnail.png` et ses variantes, mesure chacune, écrit le manifeste."""
    t0 = time.perf_counter()
    racine = racine or racine_projet()
    chemins = RunPaths.depuis_video_id(video_id, racine)
    if not chemins.script.exists() or not chemins.shotlist.exists():
        raise FileNotFoundError(
            f"miniature : script.json et shotlist.json exigés ({chemins.racine})"
        )
    spec = VideoSpec.model_validate_json(chemins.spec.read_text(encoding="utf-8"))
    script = Script.model_validate_json(chemins.script.read_text(encoding="utf-8"))
    shotlist = Shotlist.model_validate_json(chemins.shotlist.read_text(encoding="utf-8"))

    cfg = config_module.charger(racine, strict=False)
    channel = cfg.get_channel(spec.channel_id)
    langue = cfg.langue_de(channel)
    niche_cfg = cfg.niches[channel.niche]
    charte = channel.charte

    trace = TraceLLM()
    resultat_titres = titles.executer(
        script, niche_cfg, langue, channel.niche, seed=spec.seed, racine=racine, trace=trace
    )
    alertes = list(resultat_titres.alertes)

    candidats = _images_disponibles(chemins, shotlist)
    if not candidats:
        raise MiniatureImpossible(
            f"aucune image d'asset dans {chemins.assets_dir} : "
            "la miniature se compose sur une image du run, jamais sur une image neuve"
        )
    shot_fond, motif_fond = _choisir_fond(candidats[:10], spec.topic.sujet, racine, trace)
    fond = {sid: img for sid, img, _ in candidats}[shot_fond]

    # Coin de marque : le corpus mesure « logo de chaîne systématique en coin » et aucun logo
    # n'existe encore. Le nom de la chaîne en tient lieu — **jamais `template_id`**, qui est un
    # identifiant interne et n'a rien à faire sur une image publiée.
    bandeau = channel.name.upper()[:22]
    police = racine / "assets" / "fonts" / "Inter[opsz,wght].ttf"
    if not police.exists():
        alertes.append(f"police de charte absente ({police.name}) : repli sur Arial")

    candidats_texte = [(v.text, v.score or 0.5) for v in resultat_titres.textes_miniature]
    if not candidats_texte:
        candidats_texte = [(resultat_titres.texte_miniature_retenu, 0.5)]

    gabarits = list(charte.thumbnail.templates)
    if spec.parent_id:
        # Déclinaison (étape 24) : jamais le gabarit de la miniature du parent, quelle que
        # soit la variante que le score retiendra.
        fichier_parent = RunPaths.depuis_video_id(spec.parent_id, racine).thumbnails_json
        if fichier_parent.exists():
            du_parent = json.loads(fichier_parent.read_text(encoding="utf-8")).get("template")
            gabarits = [g for g in gabarits if g != du_parent] or gabarits
    combos = variantes_module.combinaisons(
        candidats_texte, gabarits, spec.seed, max(1, variantes)
    )
    dossier = chemins.thumbnails_dir
    travail = dossier / ".compo"
    composees, dits = variantes_module.composer(
        combos, fond, charte, bandeau, police, dossier, travail
    )
    alertes += dits
    shutil.rmtree(travail, ignore_errors=True)

    from factory.analytics import weights as wmod

    retenue, motif = variantes_module.choisir_initiale(composees, wmod.charger(racine), spec.seed)
    shutil.copyfile(chemins.racine / retenue.file, chemins.thumbnail)

    rotation = RotationMiniature(
        after_days=ROTATION_APRES_JOURS,
        criterion=CRITERE_ROTATION,
        next_variants=[Path(v.file).stem for v in composees if v is not retenue],
    )

    donnees = {
        "schema_version": "1.1",
        "chosen": Path(retenue.file).stem,
        "chosen_reason": motif,
        "template": retenue.template,
        "background": {"shot": shot_fond, "file": str(fond.relative_to(chemins.racine)),
                       "reason": motif_fond},
        "rotation": rotation.model_dump(mode="json"),
        "variants": [v.model_dump(mode="json") for v in composees],
    }
    chemins.thumbnails_json.write_text(
        json.dumps(donnees, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    secondes = time.perf_counter() - t0
    _ecrire_manifeste(video_id, racine, resultat_titres, composees,
                      Path(retenue.file).stem, rotation, secondes, trace.secondes_calculees)
    return ResultatMiniature(
        variantes=composees, retenue=Path(retenue.file).stem, motif=motif, fond=fond,
        fond_shot=shot_fond, fond_source=motif_fond, gabarit=retenue.template or "",
        titre_retenu=resultat_titres.titre_retenu, n_titres=len(resultat_titres.titres),
        secondes=secondes, secondes_llm=trace.secondes_calculees, rotation=rotation,
        duels=resultat_titres.duels, promesse_tenue=resultat_titres.promesse_tenue,
        appels_caches=trace.appels_caches, alertes=alertes,
    )


def _ecrire_manifeste(
    video_id: str, racine: Path | None, titres: titles.ResultatTitres,
    variantes: list[VarianteMiniature], retenue: str, rotation: RotationMiniature,
    secondes: float, secondes_llm: float,
) -> None:
    """Variantes de titres et de miniatures au manifeste — c'est la matière de la phase 3."""
    chemins = RunPaths.depuis_video_id(video_id, racine)
    manifest = runs.charger_manifest(video_id, racine)
    manifest.decisions.title_variants = titres.titres
    manifest.decisions.title_chosen = titres.titre_retenu
    manifest.decisions.thumbnail_text_variants = titres.textes_miniature
    manifest.decisions.thumbnail_variants = variantes
    manifest.decisions.thumbnail_chosen = retenue
    manifest.decisions.thumbnail_rotation = rotation
    from factory.analytics import weights as wmod
    poids = wmod.charger(racine)
    wmod.noter(manifest, poids, "title_patterns", titles.charger_poids_appris(racine) or "corpus")
    wmod.noter(manifest, poids, "thumbnail",
               "thompson" if (poids or {}).get("thumbnail_policy", {}).get("active") else "score composite")
    manifest.execution.timings["thumbnail"] = round(secondes, 2)
    manifest.execution.timings["thumbnail_llm"] = round(secondes_llm, 2)
    runs.ecrire_json(chemins.manifest, manifest)
    conn = db.ouvrir(None if racine is None else racine / "workspace" / "factory.db")
    db.migrer(conn)
    runs.enregistrer(conn, runs.charger_spec(video_id, racine), manifest, racine)
    conn.close()
