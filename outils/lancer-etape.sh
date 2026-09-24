#!/bin/zsh
# Lance une étape dans une session `screen` détachée : vrai TTY, hors du contexte de l'appelant.
# Usage : outils/lancer-etape.sh 16 [--force]
#   suivre  : screen -r etape16        (détacher : Ctrl-A puis D)
#   journal : workspace/logs/etape16.log  (capturé par `script`, lisible de l'extérieur)
#   arrêter : screen -S etape16 -X quit
set -u
ROOT="/Users/toms/Documents/Claude/Clients/Alek/Content-creation"
cd "$ROOT" || exit 1
N="${1:?numéro d'étape attendu}"; shift
NOM="etape${N//./_}"

if screen -ls 2>/dev/null | grep -q "\.${NOM}[[:space:]]"; then
  echo "⛔ une session « ${NOM} » tourne déjà — screen -r ${NOM}"; exit 1
fi

# Le portillon d'abord : il refuse un arbre sale, un blocage ⛔N, un disque trop juste.
P=$(../prompts/etape.sh "$N" "$@") || { echo "⛔ portillon refusé — rien n'est lancé"; exit 1; }

# Journal par `script`, pas par `screen -L` : ce screen est la 4.00.03 (2006), sans -Logfile.
# Sans ce journal la session est HERMÉTIQUE depuis l'extérieur — vérifié le 18/09/2026 :
# `hardcopy` rend un fichier vide (buffer alterné d'un TUI) et `stuff`, `register`+`paste`
# n'atteignent pas la session, même sur un zsh de test. Une étape bloquée est alors
# indiagnosticable autrement qu'en s'y rattachant à la main.
mkdir -p workspace/logs
JOURNAL="workspace/logs/${NOM}.log"
: > "$JOURNAL"
screen -dmS "$NOM" script -q "$JOURNAL" claude --model opus --dangerously-skip-permissions "$P"
sleep 3
if screen -ls 2>/dev/null | grep -q "\.${NOM}[[:space:]]"; then
  echo "✓ étape ${N} lancée dans screen « ${NOM} », détachée"
  echo "  suivre  : screen -r ${NOM}     (détacher : Ctrl-A puis D)"
  echo "  journal : ${JOURNAL}   (sortie brute ; ANSI à filtrer)"
  echo "  arrêter : screen -S ${NOM} -X quit"
else
  echo "⛔ la session screen n'a pas démarré"; exit 1
fi
