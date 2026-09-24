#!/bin/zsh
# État d'un run de production. Sortie : "<ETAT> <detail>"
#   FINI <taille>   final.mp4 présent
#   VIVANT <etape>  un processus du venv du projet travaille encore
#   MORT <detail>   ni final.mp4 ni processus
# Aucune détection par `pgrep -f 'factory …'` : le `pgrep` de macOS est en regex BASIQUE
# (« (run|render) » y est littéral) et le motif « factory run » matche aussi les sessions
# claude dont le prompt contient ces mots. On n'accepte que le python du venv du projet.
set -u
ROOT="/Users/toms/Documents/Claude/Clients/Alek/Content-creation"
cd "$ROOT" || exit 1
RUN="${1:?identifiant de run attendu}"
R="workspace/runs/$RUN"

if [[ -f "$R/final.mp4" ]]; then
  echo "FINI $(du -h "$R/final.mp4" | cut -f1)"; exit 0
fi

# Le processus doit porter CE run : sans ça, n'importe quel run sans final.mp4 passerait
# pour vivant dès qu'un autre run tourne.
ETAPE=$(ps -eo command \
  | grep -E "${ROOT}/\.venv/bin/python3? (-m factory\.cli|[^ ]*/bin/factory) " \
  | grep -- "--run ${RUN}" \
  | grep -v grep | sed -E 's/.*(factory\.cli|bin\/factory) ([a-z_]+).*/\2/' | sort -u | tr '\n' ',')

if [[ -n "$ETAPE" ]]; then
  echo "VIVANT ${ETAPE%,}"
else
  echo "MORT $(ls -1 "$R/clips" 2>/dev/null | wc -l | tr -d ' ') clips, pas de final.mp4"
fi
