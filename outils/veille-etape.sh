#!/bin/zsh
# Point de contrôle d'une étape en cours : écrit-elle encore, a-t-elle fini, a-t-elle cassé ?
# Usage : outils/veille-etape.sh [numéro d'étape]   — défaut : 15
set -u
ROOT="/Users/toms/Documents/Claude/Clients/Alek/Content-creation"
cd "$ROOT" || exit 1
ETAPE="${1:-15}"

echo "── veille · étape ${ETAPE} · $(date '+%H:%M:%S') ──"

# 1. L'étape a-t-elle été committée ? C'est le seul signal fiable de fin (CLAUDE.md règle 8).
DERNIER=$(git log -1 --format='%h %s')
if git log -1 --format='%s' | grep -qiE "^étape ${ETAPE}\b|^${ETAPE} :"; then
  echo "FIN     : commit d'étape présent → ${DERNIER}"
else
  echo "commit  : ${DERNIER}  (pas encore l'étape ${ETAPE})"
fi

# 2. Écrit-elle encore ? Sonde robuste : `find` est bfs ici et refuse `-newermt` relatif.
LIGNE=$("$ROOT/outils/derniere-ecriture.sh")
AGE=${LIGNE%% *}; F=${LIGNE#* }
if (( AGE > 1800 )); then
  echo "écrit   : rien depuis $(( AGE / 60 )) min  ⚠  (dernier : ${F})"
else
  echo "écrit   : il y a $(( AGE / 60 )) min $(( AGE % 60 ))s — ${F}"
fi

# 3. Arbre git : ce qui est en chantier.
N=$(git status --porcelain | wc -l | tr -d ' ')
echo "arbre   : ${N} fichier(s) non committé(s)"

# 4. Les tests passent-ils ? (une étape qui casse la suite est un signal fort)
T=$(uv run pytest -q 2>&1 | tail -1)
echo "tests   : ${T}"

# 5. Le rendu EN de fond.
A=$(find workspace/runs/bms-science-en-20260917-avwf/assets -name image.png 2>/dev/null | wc -l | tr -d ' ')
C=$(ls -1 workspace/runs/bms-science-en-20260917-avwf/clips/ 2>/dev/null | wc -l | tr -d ' ')
if pgrep -f 'factory.cli render' >/dev/null; then R="en cours"; else R="ARRÊTÉ"; fi
echo "rendu EN: ${A}/129 images · ${C} clips · ${R}"

# 6. Disque — plancher projet 8 Go (CLAUDE.md règle 3).
D=$(df -g / | tail -1 | awk '{print $4}')
if (( D < 8 )); then echo "disque  : ${D} Go libres  ⛔ SOUS LE PLANCHER"; else echo "disque  : ${D} Go libres"; fi
