#!/usr/bin/env bash
# Enchaîne les 8 synthèses TTS (4 langues x 2 voix) puis les deux ASR.
# Un processus par synthèse : le modèle est rechargé à chaque fois, donc jamais
# deux modèles résidents (CLAUDE.md § 4). Le coût de chargement est mesuré à part.
cd /Users/toms/Documents/Claude/Clients/Alek/Content-creation
for lang in fr en es it; do
  for voix in Ryan Serena; do
    ./benchmarks/bench_audio.sh tts --lang "$lang" --voix "$voix" > /dev/null 2>&1
    echo "TTS $lang $voix exit=$?"
  done
done
echo "=== TTS TERMINE ==="
ls benchmarks/samples/audio/*.wav 2>/dev/null | wc -l
./benchmarks/bench_audio.sh asr > /dev/null 2>&1
echo "ASR-PRINCIPAL exit=$?"
./benchmarks/bench_audio.sh asr-repli > /dev/null 2>&1
echo "ASR-REPLI exit=$?"
echo "=== TOUT TERMINE ==="
