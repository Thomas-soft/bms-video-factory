#!/bin/zsh
# Planche-contact : 6 images d'un MP4 (2,5 / 8 / 13 / 19 / 25 / 30 s) en une seule image.
# Une planche = une image regardée, mais six instants vus.
set -e
v=$1; out=$2
tmp=$(mktemp -d)
i=0
for t in 2.5 8 13 19 25 30; do
  ffmpeg -v error -y -ss $t -i "$v" -vframes 1 -vf scale=640:-1 "$tmp/f$i.png"
  i=$((i+1))
done
ffmpeg -v error -y -i "$tmp/f0.png" -i "$tmp/f1.png" -i "$tmp/f2.png" \
       -i "$tmp/f3.png" -i "$tmp/f4.png" -i "$tmp/f5.png" \
  -filter_complex "[0][1][2]hstack=3[h1];[3][4][5]hstack=3[h2];[h1][h2]vstack=2[o]" \
  -map "[o]" "$out"
rm -rf "$tmp"
