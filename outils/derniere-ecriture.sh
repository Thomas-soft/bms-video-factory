#!/bin/zsh
# Âge en secondes de la plus récente écriture d'une session d'étape, et le fichier concerné.
# `outils/` est exclu : c'est l'espace de la session de surveillance, et ses propres
# écritures masqueraient le silence de l'étape surveillée (constaté le 18/09/2026).
# Sortie : "<secondes> <chemin>".  Aucun -newermt : `find` est bfs ici et refuse les dates
# relatives (« Invalid timestamp »). On compare les mtime numériquement, ça marche partout.
set -u
cd "/Users/toms/Documents/Claude/Clients/Alek/Content-creation" || exit 1
LIGNE=$(/usr/bin/find . -type f \
          -not -path './.git/*' -not -path './workspace/*' -not -path './.venv/*' \
          -not -path '*/__pycache__/*' -not -path './registre/data/*' \
          -not -path './.pytest_cache/*' -not -path './.claude/*' \
          -not -path './outils/*' \
          -print0 2>/dev/null \
        | xargs -0 stat -f '%m %N' 2>/dev/null | sort -rn | head -1)
[[ -z "$LIGNE" ]] && { echo "999999 aucun"; exit 0; }
echo "$(( $(date +%s) - ${LIGNE%% *} )) ${LIGNE#* }"
