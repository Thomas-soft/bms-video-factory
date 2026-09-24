#!/usr/bin/env bash
# Banc texte et audio — étape 5.1.
# Chaque outil tourne dans un processus séparé (CLAUDE.md § 4 : un seul modèle
# résident), enveloppé dans /usr/bin/time -l pour le pic mémoire.
# Usage : ./benchmarks/bench_audio.sh <etape> [args…]
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export HF_HOME="$ROOT/models/hf"
export LLAMA_CACHE="$ROOT/models/llamacpp"
export PYTORCH_ENABLE_MPS_FALLBACK=1   # agent B : aten::_fft_r2c absent sur MPS
export TOKENIZERS_PARALLELISM=false

PY="$ROOT/.venv/bin/python"
LOG="$ROOT/benchmarks/bench_audio.log"
MEM="$ROOT/benchmarks/mem_audio.log"

etiquette="$1"; shift
echo "=== $etiquette $* — $(date '+%H:%M:%S') ===" | tee -a "$LOG"

/usr/bin/time -l "$PY" "$ROOT/benchmarks/bench_audio.py" "$etiquette" "$@" \
    >> "$LOG" 2>&1
code=$?

# Pic mémoire : dernier « maximum resident set size » écrit par time -l
pic=$(grep "maximum resident set size" "$LOG" | tail -1 | awk '{printf "%.2f", $1/1073741824}')
echo "$etiquette $* | pic_Go=$pic | exit=$code" | tee -a "$MEM"
exit $code
