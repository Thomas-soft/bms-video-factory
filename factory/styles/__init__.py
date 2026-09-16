"""Registre des moteurs de style : nom de moteur → classe.

`config/styles/<id>.yaml` nomme un moteur, ce registre le résout, la chaîne nomme un style.
**Il n'existe nulle part un `if style == …`** (`ARCHITECTURE.md` § 5) : ajouter un style, c'est
ajouter un YAML et une entrée ici, jamais toucher au pipeline.

Un moteur non encore livré n'a pas d'entrée dans `STYLE_ENGINES` — il en a une dans
`MOTEURS_PLANIFIES`, qui nomme l'étape de la feuille de route qui le livrera. C'est cette étape
que porte le message d'erreur : « pas implémenté » n'aide personne, « livré par l'étape 12.2 » si.
"""

from __future__ import annotations

from pathlib import Path

from factory.core.models import Channel, Style
from factory.styles.base import MoteurBase, StyleEngine
from factory.styles.cartes import CartesEngine
from factory.styles.illustre import IllustreEngine

#: Moteurs livrés. La valeur est la classe, jamais une instance : un moteur est construit par run.
STYLE_ENGINES: dict[str, type] = {
    "cartes": CartesEngine,          # 12.1  ffmpeg — interne, jamais publié tel quel
    "illustre_anime": IllustreEngine,  # 12.2  ffmpeg — images locales + parallaxe 2.5D
}

#: Moteurs annoncés par `config/styles/` mais non livrés, et l'étape qui les livrera.
MOTEURS_PLANIFIES: dict[str, str] = {
    "documentaire": "17 — moteur « documentaire »",
    "motion_design": "30.1 — moteur « motion design » (backend revideo)",
    "whiteboard": "30.2 — moteur « whiteboard » (backend revideo)",
    "avatar2d": "29 — moteur « avatar 2D » (backend revideo)",
}


class MoteurIndisponible(RuntimeError):
    """Le style demandé existe en configuration mais son moteur n'est pas livré."""


def get_engine(style: Style, racine: Path | None = None, journal=None) -> StyleEngine:
    """Résout `config/styles/<id>.yaml` → moteur → `STYLE_ENGINES`, et l'instancie.

    Lève `MoteurIndisponible` en nommant l'étape qui le livrera si le style n'est pas exécutable
    ou si son moteur n'a pas encore de classe.
    """
    if not style.executable:
        etape = MOTEURS_PLANIFIES.get(style.engine, "une étape ultérieure de ROADMAP.md")
        raise MoteurIndisponible(
            f"style « {style.id} » en statut {style.statut} : son moteur {style.engine} est livré "
            f"par l'étape {etape}"
        )
    classe = STYLE_ENGINES.get(style.engine)
    if classe is None:
        etape = MOTEURS_PLANIFIES.get(style.engine, "une étape ultérieure de ROADMAP.md")
        raise MoteurIndisponible(
            f"moteur « {style.engine} » absent du registre : livré par l'étape {etape} "
            f"(livrés : {', '.join(sorted(STYLE_ENGINES)) or 'aucun'})"
        )
    return classe(style=style, racine=racine or Path.cwd(), journal=journal)


def moteur_de_chaine(channel: Channel, styles: dict[str, Style], racine: Path | None = None,
                     journal=None, surcharge: str | None = None) -> StyleEngine:
    """Moteur d'une chaîne, `surcharge` prenant le pas sur `channel.style` (option `--style`)."""
    style_id = surcharge or channel.style
    if style_id not in styles:
        connus = ", ".join(sorted(styles)) or "aucun"
        raise KeyError(f"style inconnu : {style_id} (connus : {connus})")
    return get_engine(styles[style_id], racine=racine, journal=journal)


__all__ = [
    "STYLE_ENGINES", "MOTEURS_PLANIFIES", "MoteurIndisponible", "MoteurBase", "StyleEngine",
    "get_engine", "moteur_de_chaine", "CartesEngine", "IllustreEngine",
]
