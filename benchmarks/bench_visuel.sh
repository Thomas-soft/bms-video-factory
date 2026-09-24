#!/bin/zsh
# Banc visuel — étape 5.2. Un sous-processus par brique : un seul modèle
# résident à la fois. Tout le verbeux part dans benchmarks/bench_visuel.log.
set -u
cd "$(dirname "$0")/.."
set -a; source .env; set +a
export PYTORCH_ENABLE_MPS_FALLBACK=1          # DPT et RoPE manquent sur MPS
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.9   # 0.0 laisserait partir en swap
export PYTORCH_MPS_LOW_WATERMARK_RATIO=0.8    # doit rester sous le high, sinon erreur
export DISABLE_TELEMETRY=true                 # Revideo appelle PostHog par défaut
export PLAYWRIGHT_BROWSERS_PATH="$PWD/models/playwright"
export PUPPETEER_CACHE_DIR="$PWD/models/puppeteer"

LOG=benchmarks/bench_visuel.log
BRIQUES=${@:-"revideo lipsync image depth parallax whiteboard miniature"}

for b in ${=BRIQUES}; do
  libre=$(df -g / | tail -1 | awk '{print $4}')
  if [ "$libre" -lt 8 ]; then
    echo "ARRET : $libre Go libres, plancher atteint" | tee -a $LOG; exit 1
  fi
  echo "=== $b === $(date +%H:%M:%S) — $libre Go libres" | tee -a $LOG
  .venv/bin/python benchmarks/bench_visuel.py "$b" >> $LOG 2>&1
  echo "--- $b terminé (code $?) ---" >> $LOG
  grep -v 'it/s\]' $LOG | tail -6
done
