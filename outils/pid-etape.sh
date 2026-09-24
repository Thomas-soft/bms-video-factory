#!/bin/zsh
# PID réel du claude d'une étape, par filiation depuis sa session screen, à profondeur variable.
# Pas de recherche par ligne de commande : celle-ci porte le prompt entier (milliers de
# caractères accentués), `ps -e | grep` ne la retrouve pas, et « claude --model opus » matche
# aussi l'enveloppe SCREEN — d'où une fausse alerte de blocage le 18/09/2026.
# La profondeur varie : SCREEN → login → claude sans journal, SCREEN → script → login → claude
# avec (le lanceur enveloppe dans `script` depuis le 18/09/2026).
set -u
NOM="${1:?nom de session screen attendu}"
SCR=$(screen -ls 2>/dev/null | awk -v n="$NOM" '$1 ~ "\\."n"$" {split($1,a,"."); print a[1]}' | head -1)
[[ -z "$SCR" ]] && exit 1
niveau=($SCR)
for _ in 1 2 3 4 5; do
  suivant=()
  for p in $niveau; do
    [[ "$(ps -p $p -o comm= 2>/dev/null)" == *claude* ]] && { echo "$p"; exit 0; }
    suivant+=($(ps -eo pid,ppid | awk -v q="$p" '$2==q {print $1}'))
  done
  [[ ${#suivant[@]} -eq 0 ]] && break
  niveau=($suivant)
done
exit 1
