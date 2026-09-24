/**
 * Projet Revideo du lot en cours : **une scène par plan**, dans l'ordre du lot.
 *
 * Le nombre de scènes d'un projet est figé à la construction — `variables` n'arrive qu'à
 * l'exécution et ne peut donc pas en décider. C'est pourquoi `render.mjs` écrit `src/lot.json`
 * avant chaque lancement : Vite reconstruit, le projet relit, les scènes suivent.
 *
 * Le lot sort en **une seule vidéo continue** ; `factory/styles/motion.py` la redécoupe en clips
 * de plan. Un lancement de Chromium coûte une dizaine de secondes : le faire une fois pour vingt
 * plans au lieu de vingt fois est le premier levier de vitesse du moteur.
 */
import {makeProject} from '@revideo/core';
import {makeScene2D} from '@revideo/2d';
import './styles.css';
import {LOT, C, L, H, FPS} from './charte';
import {fondCouleur} from './commun';

import {kineticText} from './scenes/kinetic-text';
import {listReveal} from './scenes/list-reveal';
import {statCounter} from './scenes/stat-counter';
import {iconGrid} from './scenes/icon-grid';
import {chart} from './scenes/chart';
import {lowerThird} from './scenes/lower-third';
import {quote} from './scenes/quote';
import {transitionStinger} from './scenes/transition-stinger';
import {titleCard} from './scenes/title-card';
import {assemble} from './scenes/assemble';
import {echelle} from './scenes/echelle';
import {systeme} from './scenes/systeme';
import {coupe} from './scenes/coupe';
import {flux} from './scenes/flux';
import {transformation} from './scenes/transformation';
import {quantite} from './scenes/quantite';
import {personnageScene} from './scenes/personnage';
import {chronologie} from './scenes/chronologie';
import {tetePar} from './scenes/tete-parlante';
import {duo} from './scenes/duo';
import {groupe} from './scenes/groupe';
import {drawSvg} from './scenes/draw-svg';

// Les polices doivent être **chargées** avant le premier calcul de mise en page, sinon les
// largeurs sont mesurées sur la police de repli et les blocs débordent (piège Revideo #259).
await Promise.all([
  document.fonts.load(`${C.font_title.weight} 100px "${C.font_title.family}"`),
  document.fonts.load(`${C.font_body.weight} 100px "${C.font_body.family}"`),
  document.fonts.load('500 100px "BMSSourceSerif"'),
  document.fonts.load('600 100px "BMSCaveat"'),
]);
await document.fonts.ready;

const SCENES: Record<string, (view: any, props: any, duree: number) => any[]> = {
  kinetic_text: kineticText,
  list_reveal: listReveal,
  stat_counter: statCounter,
  icon_grid: iconGrid,
  chart: chart,
  lower_third: lowerThird,
  quote: quote,
  transition_stinger: transitionStinger,
  title_card: titleCard,
  // Scènes construites — elles fabriquent un objet à l'écran au lieu d'y écrire une phrase.
  assemble: assemble,
  echelle: echelle,
  systeme: systeme,
  coupe: coupe,
  flux: flux,
  transformation: transformation,
  quantite: quantite,
  personnage: personnageScene,
  chronologie: chronologie,
  // Scènes jouées — un personnage occupe le cadre et agit. C'est la grammaire de la chaîne de
  // référence, relevée le 19/09 : « presque aucun texte à l'écran », des êtres qui parlent.
  tete_parlante: tetePar,
  duo: duo,
  groupe: groupe,
  // Moteur « whiteboard » (étape 30.2) : un dessin vectorisé se trace sous une main.
  draw_svg: drawSvg,
};

const scenes = LOT.shots.map(plan => {
  const fabrique = SCENES[plan.scene] ?? SCENES.kinetic_text;
  // La durée est posée **en images**, jamais en secondes.
  //
  // `waitFor(n / fps)` laisse la virgule flottante rendre 115,000000000000014 pour 115 : la scène
  // gagne une image, et toutes les frontières de découpe suivantes glissent (3 056 images pour
  // 3 026 attendues, rendu du 19/09). La scène égrène donc ses images une à une, plus bas.
  const images = Math.max(1, Math.round(plan.duration_s * FPS));
  const duree = images / FPS;
  return makeScene2D(`${LOT.lot}_${plan.id}`, function* (view) {
    view.fill(fondCouleur(plan.props?.bg_variant ?? 0));
    // Les tâches sont **lancées en parallèle**, puis la scène égrène exactement ses images.
    // `all(waitFor(d), …tâches)` attendait la plus longue : une animation qui dépasse d'un
    // cheveu rallongeait la scène d'une image, et toutes les frontières de découpe suivantes
    // glissaient (13 scènes sur 20 au rendu du 19/09). Ici la durée du plan fait loi.
    for (const tache of fabrique(view, {...plan.props, seed: plan.props?.seed ?? 1}, duree)) {
      yield tache;
    }
    for (let i = 0; i < images; i++) yield;
  });
});

export default makeProject({
  scenes,
  settings: {
    shared: {size: {x: L, y: H}, background: C.bg},
    rendering: {fps: FPS, resolutionScale: LOT.resolution_scale ?? 1},
  },
});
