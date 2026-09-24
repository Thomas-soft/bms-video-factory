#!/bin/zsh
# Empêche le Mac de dormir pendant les sessions longues (rendus, étapes enchaînées).
# Usage : outils/pas-de-veille.sh [heures]   — défaut 12 · arrêt : outils/pas-de-veille.sh stop
set -u
MARQUE="$HOME/.bms-pas-de-veille.pid"

if [[ "${1:-}" == "stop" ]]; then
  if [[ -f "$MARQUE" ]] && kill "$(cat "$MARQUE")" 2>/dev/null; then
    echo "veille réautorisée (pid $(cat "$MARQUE") arrêté)"
  else
    echo "rien à arrêter"
  fi
  rm -f "$MARQUE"; exit 0
fi

HEURES="${1:-12}"
SECONDES=$(( HEURES * 3600 ))

# Un seul garde à la fois.
if [[ -f "$MARQUE" ]] && kill -0 "$(cat "$MARQUE")" 2>/dev/null; then
  echo "déjà actif (pid $(cat "$MARQUE")) — arrête-le d'abord avec « stop »"; exit 0
fi

# -i idle · -m disque · -s système (secteur uniquement) · pas de -d : l'écran peut s'éteindre.
nohup caffeinate -ims -t "$SECONDES" >/dev/null 2>&1 &
echo $! > "$MARQUE"
echo "veille bloquée pour ${HEURES} h (pid $!) — l'écran peut s'éteindre, la machine ne dormira pas"
echo "arrêt : outils/pas-de-veille.sh stop"
