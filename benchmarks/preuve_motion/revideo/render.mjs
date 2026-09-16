// Rendu headless d'un projet Revideo. Deux arguments : fichier de projet, nom de sortie.
// Le premier lancement meurt sur « Navigation timeout » (optimisation des dépendances
// Vite, piège n° 3 du README d'outils/revideo_projet) : une relance est prévue.
import {renderVideo} from '@revideo/renderer';

const projet = process.argv[2];
const sortie = process.argv[3];

async function rendre() {
  return await renderVideo({
    projectFile: projet,
    settings: {
      outFile: sortie,
      logProgress: true,
      workers: 1,                       // 2 workers saturent 16 Go
      dimensions: [1920, 1080],
      fps: 30,
      ffmpeg: {ffmpegLogLevel: 'error'},
    },
  });
}

const t0 = Date.now();
let out;
try {
  out = await rendre();
} catch (e) {
  console.error(`PREMIER ESSAI ECHOUE: ${e.message}`);
  out = await rendre();
}
console.log(`RENDU ${out} en ${((Date.now() - t0) / 1000).toFixed(2)} s`);
