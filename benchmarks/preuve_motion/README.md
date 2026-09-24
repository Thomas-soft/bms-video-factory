# Preuve motion design — hors feuille de route (16/09/2026)

Trois traitements du **même texte et de la même voix** (hook + segment 1 du run
`workspace/runs/bms-science-fr-20260915-j7sf`, 0 → 32,0 s), pour que la seule
variable soit le traitement visuel. Le run n'est pas modifié : il est lu.

- `motion_A.mp4` — typographie cinétique pure, zéro image.
- `motion_B.mp4` — schéma animé en vecteur (saccharose → insuline).
- `motion_C.mp4` — hybride : 3 PNG de `workspace/library/images` (étape 12.2, 1280×720)
  sous typographie et formes animées. **Aucune image générée.**

Mesures et lecture : `RESULTATS.md`.

## Refaire la matière première (non versionnée : ce sont des copies de `workspace/`)

```sh
R=workspace/runs/bms-science-fr-20260915-j7sf
ffmpeg -y -i $R/voice/voice.wav -t 32.0 -af afade=t=out:st=31.5:d=0.5 \
  -ar 48000 -ac 2 benchmarks/preuve_motion/data/voix_32s.wav
S=benchmarks/preuve_motion/revideo/src
cp workspace/library/images/07b318b33e54ae0f.png $S/fonds/fond1.png   # cristal -> binaire
cp workspace/library/images/1aaf02e4a22b2f7e.png $S/fonds/fond2.png   # saccharose
cp workspace/library/images/7fd5881863a93362.png $S/fonds/fond3.png   # calories / horloge
cp "assets/fonts/Inter[opsz,wght].ttf" $S/fonts/Inter-Variable.ttf
```

`data/mots.json`, lui, **est versionné** : c'est le contrat temporel des trois scènes.

## Refaire les rendus

```sh
cd revideo
npm install --no-audit --no-fund      # npm 11 bloque les postinstall :
npm approve-scripts puppeteer esbuild @revideo/telemetry \
    @ffmpeg-installer/darwin-arm64 @ffprobe-installer/darwin-arm64
npm rebuild
python3 mesure.py ./src/motion_b.tsx b_brut.mp4 ../../../workspace/logs/b.log
cd .. && ffmpeg -y -i revideo/output/b_brut.mp4 -i data/voix_32s.wav \
  -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 192k -shortest motion_B.mp4
```

`mesure.py` impose `PUPPETEER_EXECUTABLE_PATH` sur le Chromium de Playwright
(`models/playwright/…`) : Revideo n'a pas besoin du sien, et `models/puppeteer`
a été purgé pour tenir le plafond de 22 Go. Ne pas relancer le postinstall de
puppeteer sans raison — il retélécharge 0,59 Go.

## Fichiers

| Chemin | Rôle |
|---|---|
| `data/voix_32s.wav` | 32,0 s de `voice/voice.wav`, fondu de sortie 0,5 s |
| `data/mots.json` | 77 mots horodatés + 3 segments, extraits de `words.json` |
| `revideo/src/motion_{a,b,c}.tsx` | les trois scènes |
| `revideo/src/charte.ts` | palette et polices recopiées de `config/channels/bms-science-fr.yaml` |
| `revideo/src/commun.ts` | découpage des mots en blocs de lecture |
| `revideo/src/fonds/` | 3 PNG de bibliothèque, copiés (`07b318…`, `1aaf02…`, `7fd588…`) |
| `planche.sh` | planche-contact de 6 images à partir d'un MP4 |
