/**
 * Rendu sans interface d'un lot de plans.
 *
 *   node render.mjs specs/<video_id>/batch.json
 *
 * Le fichier de lot décrit la charte, la résolution, les images par seconde et la liste des
 * plans ; chaque **lot** est rendu en une seule vidéo continue, par un seul lancement de
 * Chromium. Un manifeste JSON accompagne chaque lot : nombre d'images de chaque plan, et donc
 * la frontière exacte où `factory/styles/motion.py` redécoupe.
 *
 * Trois pièges payés à l'étape 5.2 et retenus ici :
 * 1. `@revideo/renderer` ne tire ni `@revideo/vite-plugin` ni `@revideo/ui` : ils sont épinglés
 *    dans `package.json`, sinon `MODULE_NOT_FOUND`.
 * 2. `makeScene2D` prend un **nom** en premier argument depuis 0.10.
 * 3. Le premier lancement optimise les dépendances Vite, recharge la page et meurt sur
 *    « Navigation timeout of 30000 ms exceeded ». Une relance est prévue.
 */
import {renderVideo} from '@revideo/renderer';
import {mkdirSync, readFileSync, writeFileSync, existsSync, rmSync} from 'node:fs';
import {dirname, resolve, basename} from 'node:path';

const ICI = dirname(new URL(import.meta.url).pathname);
const CHEMIN_LOT_COURANT = resolve(ICI, 'src/lot.json');

const fichierSpec = process.argv[2];
if (!fichierSpec) {
  console.error('usage : node render.mjs <spec.json> [--lot nom]');
  process.exit(2);
}
const seulement = process.argv.includes('--lot')
  ? process.argv[process.argv.indexOf('--lot') + 1]
  : null;

const spec = JSON.parse(readFileSync(fichierSpec, 'utf8'));
const sortie = resolve(spec.out_dir);
mkdirSync(sortie, {recursive: true});

// Chrome déjà installé sur la machine plutôt que le Chrome for Testing de puppeteer : le poids
// disque du dispositif est plafonné (CLAUDE.md § 3) et un second navigateur coûterait 0,17 Go
// pour rien. `BMS_CHROME` permet d'en imposer un autre sans toucher au code.
const CHROME = process.env.BMS_CHROME
  || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const optionsPuppeteer = existsSync(CHROME) ? {executablePath: CHROME} : {};
if (!existsSync(CHROME)) {
  console.error(`AVERTISSEMENT: ${CHROME} absent — puppeteer cherchera son propre navigateur`);
}

async function rendreUnLot(lot) {
  writeFileSync(CHEMIN_LOT_COURANT, JSON.stringify({
    video_id: spec.video_id,
    lot: lot.name,
    fps: spec.fps,
    width: spec.width,
    height: spec.height,
    resolution_scale: spec.resolution_scale ?? 1,
    charte: spec.charte,
    shots: lot.shots,
  }, null, 1) + '\n');

  const appel = () => renderVideo({
    projectFile: resolve(ICI, 'src/project.tsx'),
    variables: {video_id: spec.video_id, lot: lot.name},
    settings: {
      outFile: `${lot.name}.mp4`,
      outDir: sortie,
      workers: spec.workers ?? 1,      // 2 workers saturent 16 Go (mesuré à l'étape 5.2)
      logProgress: false,
      puppeteer: optionsPuppeteer,
      ffmpeg: {ffmpegLogLevel: 'error'},
      // `src/fonts/` ne contient que des liens vers `assets/fonts/` : les polices OFL du dépôt
      // vivent à un seul endroit, et ne peuvent pas diverger d'une copie. Vite refuse par défaut
      // de servir hors de sa racine, d'où cette autorisation — limitée au dépôt.
      viteConfig: {server: {fs: {allow: [resolve(ICI, '..')]}}},
    },
  });

  const t0 = Date.now();
  let fichier;
  try {
    fichier = await appel();
  } catch (erreur) {
    console.error(`RELANCE ${lot.name}: ${erreur.message}`);
    fichier = await appel();
  }
  const secondes = (Date.now() - t0) / 1000;

  // Revideo laisse trois intermédiaires par lot : la vidéo muette, la piste audio (silencieuse
  // ici — aucune scène ne porte de son) et un remux. Quarante mégaoctets par lot que personne ne
  // relira : le disque de la machine cible est plafonné (`CLAUDE.md` § 3).
  for (const suffixe of ['-0.mp4', '-audio.wav', '-visuals.mp4']) {
    rmSync(resolve(sortie, `${lot.name}${suffixe}`), {force: true});
  }

  // Le manifeste porte la frontière de découpe en **images**, jamais en secondes : c'est la
  // seule unité où la somme des plans redonne exactement la durée du lot.
  //
  // Chaque scène occupe **exactement** son compte d'images — `project.tsx` les égrène une à une
  // plutôt que d'attendre une durée en secondes — et la vidéo porte **une image de plus** à la
  // toute fin. Étalonné le 19/09 : trois scènes de 10, 20 et 30 images sortent en 61 images.
  // `frames_attendues` permet à l'appelant de vérifier par `ffprobe` avant de découper.
  let curseur = 0;
  const plans = lot.shots.map(plan => {
    const images = Math.max(1, Math.round(plan.duration_s * spec.fps));
    const entree = {id: plan.id, scene: plan.scene, frame_debut: curseur, frames: images};
    curseur += images;
    return entree;
  });
  writeFileSync(resolve(sortie, `${lot.name}.json`), JSON.stringify({
    lot: lot.name, fichier, fps: spec.fps,
    frames_attendues: curseur + 1, frames_utiles: curseur,
    secondes_rendu: Number(secondes.toFixed(2)), shots: plans,
  }, null, 1) + '\n');

  console.log(`LOT ${lot.name} ${plans.length} plan(s) ${curseur} images ${secondes.toFixed(2)} s -> ${fichier}`);
  return {lot: lot.name, secondes, frames: curseur, fichier};
}

const lots = seulement ? spec.lots.filter(l => l.name === seulement) : spec.lots;
if (lots.length === 0) {
  console.error(`aucun lot nommé ${seulement} dans ${basename(fichierSpec)}`);
  process.exit(3);
}

const t0 = Date.now();
const resultats = [];
for (const lot of lots) resultats.push(await rendreUnLot(lot));
const total = (Date.now() - t0) / 1000;
const images = resultats.reduce((n, r) => n + r.frames, 0);
console.log(`TOTAL ${resultats.length} lot(s) ${images} images ${total.toFixed(2)} s `
  + `${(images / total).toFixed(1)} img/s`);
process.exit(0);
