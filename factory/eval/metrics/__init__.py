"""Les neuf familles de mesures du banc.

Chaque module expose `mesurer(contexte) -> Famille`. Aucun n'écrit de fichier hors
`<run>/qc/`, aucun ne charge de modèle, aucun n'interprète : ils mesurent et notent.
"""

from factory.eval.metrics import (  # noqa: F401
    audio, coupes, duree, hook, lisibilite, parole, sous_titres, structure, variete,
)

#: Ordre d'exécution. Les familles coûteuses passent après les familles instantanées, pour
#: qu'un run aux fichiers manquants échoue avant d'avoir payé la détection de plans.
FAMILLES = [duree, structure, parole, sous_titres, audio, coupes, hook, variete, lisibilite]
