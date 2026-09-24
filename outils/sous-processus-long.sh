#!/bin/zsh
# Sous-processus d'une session d'étape qui dure anormalement. Sortie : une ligne par coupable,
# "<secondes> <pid> <commande tronquée>", ou rien.
# Signature d'un interblocage : un appel d'outil normal finit en secondes ; celui du 18/09/2026
# tenait 30 min (heredoc dont les sauts de ligne étaient passés en « \012 » littéraux, donc
# `python -` attendait un EOF qui ne venait jamais). Le CPU ne le distingue PAS d'une session
# qui attend une réponse d'API : les deux consomment ~0,1 s par 7 s.
set -u
ROOT="/Users/toms/Documents/Claude/Clients/Alek/Content-creation"
NOM="${1:?nom de session screen attendu}"
SEUIL="${2:-1200}"       # secondes — un appel au LLM local dure légitimement ~12 min
                         # (699 s mesurées au run FR, 649 s au run EN le 18/09/2026)
# CPU cumulé d'un processus et de toute sa descendance, en centièmes de seconde.
_cpu_arbre() {
  local racine=$1 total=0 t
  for q in $racine $(ps -eo pid,ppid | awk -v r="$racine" '$2==r {print $1}'); do
    t=$(ps -p "$q" -o time= 2>/dev/null | tr -d ' ')
    [[ -n "$t" ]] && total=$(( total + $(echo "$t" | awk -F'[:.]' '{print ($1*60+$2)*100+$3}') ))
  done
  echo "$total"
}

P=$("$ROOT/outils/pid-etape.sh" "$NOM") || exit 0
for enfant in $(ps -eo pid,ppid | awk -v p="$P" '$2==p {print $1}'); do
  CMD=$(ps -p "$enfant" -o command= 2>/dev/null)
  # les serveurs MCP vivent aussi longtemps que la session : ce ne sont pas des appels d'outil
  # MCP : vit aussi longtemps que la session. caffeinate : lancé par Claude Code lui-même et
  # ne consomme rien par nature, donc indiscernable d'un interblocage par le filtre CPU.
  [[ "$CMD" == *mcp* || "$CMD" == npm* || "$CMD" == *node* || "$CMD" == *caffeinate* ]] && continue
  E=$(ps -p "$enfant" -o etime= 2>/dev/null | tr -d ' ')
  S=$(echo "$E" | awk -F: '{if(NF==3) print $1*3600+$2*60+$3; else if(NF==2) print $1*60+$2; else print $1}')
  [[ -z "$S" || "$S" -le "$SEUIL" ]] && continue
  # Durer ne suffit pas : un interblocage ne consomme RIEN, un appel au LLM consomme.
  # On somme le CPU du sous-arbre sur 4 s ; inchangé = bloqué, sinon il travaille.
  avant=$(_cpu_arbre "$enfant"); sleep 4; apres=$(_cpu_arbre "$enfant")
  [[ "$avant" == "$apres" ]] && echo "$S $enfant $(ps -p $enfant -o command= | cut -c1-60)"
done
exit 0
