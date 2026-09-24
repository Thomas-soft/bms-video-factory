/**
 * La charte du lot en cours, lue dans `lot.json` — jamais une couleur ni une police en dur.
 *
 * `lot.json` est écrit par `render.mjs` juste avant chaque lancement de Chromium ; il est importé
 * statiquement parce que Vite doit connaître les scènes **à la construction** : le nombre de
 * scènes d'un projet Revideo ne peut pas dépendre de `variables`, qui n'arrivent qu'à l'exécution.
 */
import lot from './lot.json';

export type Charte = {
  bg: string;
  text: string;
  text_outline: string;
  accent: string;
  highlight: string;
  font_title: {family: string; weight: number};
  font_body: {family: string; weight: number};
  marge_px: number;
  /** Moteur « whiteboard » : les deux mains, en URI de données, et le grain du papier. */
  mains?: Array<{src: string; width: number; height: number; tip: [number, number]}>;
  grain?: number;
};

export type PlanSpec = {
  id: string;
  scene: string;
  duration_s: number;
  props: Record<string, any>;
};

export type LotSpec = {
  video_id: string;
  lot: string;
  fps: number;
  width: number;
  height: number;
  resolution_scale: number;
  charte: Charte;
  shots: PlanSpec[];
};

export const LOT = lot as unknown as LotSpec;
export const C = LOT.charte;
export const L = LOT.width;
export const H = LOT.height;
export const FPS = LOT.fps;
export const MARGE = C.marge_px;

/** Demi-largeur et demi-hauteur utiles : rien de lisible ne sort de cette zone. */
export const UX = L / 2 - MARGE;
export const UY = H / 2 - MARGE;

/** Mélange deux couleurs `#rrggbb` — sert aux fonds teintés, jamais à inventer une teinte. */
export function melanger(a: string, b: string, part: number): string {
  const lire = (c: string) => [1, 3, 5].map(i => parseInt(c.slice(i, i + 2), 16));
  const [ar, ag, ab] = lire(a);
  const [br, bg, bb] = lire(b);
  const mix = (x: number, y: number) => Math.round(x + (y - x) * part).toString(16).padStart(2, '0');
  return `#${mix(ar, br)}${mix(ag, bg)}${mix(ab, bb)}`;
}
