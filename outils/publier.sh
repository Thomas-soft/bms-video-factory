#!/bin/zsh
# Reconstruit l'instantané PUBLIC du projet et le pousse.
#
# Deux dépôts, et la raison est contractuelle, pas esthétique :
#   · bms-video-factory-interne  (privé)  — tout, cache de données API compris
#   · bms-video-factory          (public) — tout SAUF registre/data/
#
# `registre/data/` contient des réponses brutes de l'API YouTube Data v3. Les
# Developer Policies III.E.4 limitent leur conservation à 30 jours ; un dépôt public,
# clonable et archivable, ne permet pas de tenir cette clause. Voir docs/CONFORMITE.md
# § « durée de conservation ». Les mesures DÉRIVÉES (REFERENTIEL.json, agrégats,
# comptages) ne sont plus des données API : elles sont publiées.
#
# L'instantané public n'a qu'un commit : l'historique de travail contient le cache,
# donc il n'est pas réutilisable tel quel.
set -e
SRC=${0:a:h:h}
PUB=$(mktemp -d)/bms-public
DATE=$(date +%d/%m/%Y)

cd "$SRC"
git ls-files | grep -v "^registre/data/" > "$PUB.liste" || true
mkdir -p "$PUB"
rsync -a --files-from="$PUB.liste" "$SRC"/ "$PUB"/
cd "$PUB"
printf '\n# Cache de donnees de l API YouTube : non publiable (Developer Policies III.E.4).\nregistre/data/\n' >> .gitignore

git init -q -b main
git add -A
git commit -q -m "BMS — usine de production de vidéos YouTube : état au $DATE

Instantané public. Le cache de données de l'API YouTube est absent, ici et de
l'historique : Developer Policies III.E.4, conservation limitée à 30 jours. Les
mesures qui en dérivent sont publiées."
git remote add origin https://github.com/Thomas-soft/bms-video-factory.git
git push -f origin main

echo "publié : https://github.com/Thomas-soft/bms-video-factory"
echo "fichiers : $(git ls-files | wc -l | tr -d ' ') · données API restantes : $(git ls-files | grep -c '^registre/data/' || echo 0)"
