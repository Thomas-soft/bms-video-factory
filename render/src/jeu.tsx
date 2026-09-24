/**
 * JEU — ce qui fait qu'un personnage a l'air vivant : la bouche, les yeux, le souffle.
 *
 * Trois automatismes, tous calés sur des données réelles quand elles existent : la bouche suit
 * les mots de `words.json`, le clignement suit une cadence humaine (une fois toutes les 3 à 5 s),
 * le buste ne s'arrête jamais. Sans cela, une silhouette bien dessinée reste un autocollant.
 */
import {all, delay, waitFor, easeOutCubic, easeInOutCubic, linear, tween} from '@revideo/core';
import {alea, Mot} from './commun';

/**
 * Anime la bouche sur les mots prononcés pendant le plan.
 *
 * L'ouverture suit une enveloppe par mot : montée rapide, tenue, fermeture. Ce n'est pas de la
 * synchronisation labiale phonème par phonème — la chaîne de référence n'en fait pas non plus —
 * mais **la bouche s'ouvre quand la voix parle**, et c'est ce qui se voit.
 */
export function parler(face: any, mots: Mot[], duree: number) {
  const taches: any[] = [];
  const ferme = 0.14;
  face.bouche().scale([1, ferme]);
  face.langue().opacity(0);
  if (!mots.length) return taches;

  for (const m of mots) {
    const t0 = Math.max(0, m.t);
    const vie = Math.max(0.08, Math.min(m.e, duree) - t0);
    if (t0 > duree) break;
    taches.push(delay(t0, (function* () {
      const ouverture = 0.45 + Math.min(0.55, m.w.length / 12);
      face.langue().opacity(1);
      yield* all(
        face.bouche().scale([1, ouverture], Math.min(0.09, vie * 0.4), easeOutCubic),
        face.langue().opacity(1, 0.05),
      );
      yield* waitFor(Math.max(0.02, vie * 0.35));
      yield* face.bouche().scale([1, ferme], Math.min(0.12, vie * 0.45), easeOutCubic);
    })()));
  }
  return taches;
}

/** Clignements : un toutes les 3 à 5 secondes, jamais synchronisés entre deux personnages. */
export function cligner(face: any, graine: number, duree: number) {
  const r = alea(graine * 601);
  return (function* () {
    let t = 0.6 + r() * 1.6;
    while (t < duree) {
      yield* waitFor(Math.min(0.5, t));
      yield* all(face.paupG().y(0, 0.07), face.paupD().y(0, 0.07),
                 face.paupG().opacity(1, 0.02), face.paupD().opacity(1, 0.02));
      yield* waitFor(0.05);
      const h = face.paupG().height();
      yield* all(face.paupG().y(-h, 0.09), face.paupD().y(-h, 0.09));
      face.paupG().opacity(0); face.paupD().opacity(0);
      const pause = 2.6 + r() * 2.2;
      t += pause;
      yield* waitFor(pause - 0.21);
    }
  })();
}

/** Le buste respire. Amplitude minuscule, jamais nulle. */
export function respirer(corps: any, duree: number, amplitude = 0.02) {
  return (function* () {
    const battements = Math.max(1, Math.floor(duree / 1.1));
    for (let i = 0; i < battements; i++) {
      yield* corps().scale([1 - amplitude * 0.5, 1 + amplitude], 0.55, easeInOutCubic);
      yield* corps().scale([1 + amplitude * 0.5, 1 - amplitude * 0.5], 0.55, easeInOutCubic);
    }
  })();
}

/** Le regard suit une cible, avec la légère paresse d'un œil réel. */
export function regarder(face: any, x: number, y: number, duree = 0.3) {
  const d = Math.max(1, Math.hypot(x, y));
  const portee = Math.min(1, d / 700);
  const dx = (x / d) * 9 * portee;
  const dy = (y / d) * 7 * portee;
  return all(
    face.pupG().position([dx, dy], duree, easeOutCubic),
    face.pupD().position([dx, dy], duree, easeOutCubic),
  );
}

/** Écrasement-étirement : la réaction. Six images suffisent, le reste est du remous. */
export function sursaut(corps: any, force = 1) {
  return (function* () {
    yield* corps().scale([1 + 0.22 * force, 1 - 0.20 * force], 0.09, easeOutCubic);
    yield* corps().scale([1 - 0.16 * force, 1 + 0.24 * force], 0.10, easeOutCubic);
    yield* corps().scale([1 + 0.08 * force, 1 - 0.07 * force], 0.10);
    yield* corps().scale([1, 1], 0.14, easeOutCubic);
  })();
}

/** Sourcils en colère, en surprise, ou au repos. */
export function expression(face: any, quoi: 'repos' | 'surprise' | 'colere', rOeil: number) {
  const g = face.sourcilG, d = face.sourcilD;
  if (!g() || !d()) return waitFor(0);
  if (quoi === 'surprise') {
    return all(
      g().points([[-rOeil * 1.9, -rOeil * 2.3], [-rOeil * 0.6, -rOeil * 2.5]], 0.14),
      d().points([[rOeil * 0.6, -rOeil * 2.5], [rOeil * 1.9, -rOeil * 2.3]], 0.14),
    );
  }
  if (quoi === 'colere') {
    return all(
      g().points([[-rOeil * 1.9, -rOeil * 2.0], [-rOeil * 0.5, -rOeil * 1.2]], 0.14),
      d().points([[rOeil * 0.5, -rOeil * 1.2], [rOeil * 1.9, -rOeil * 2.0]], 0.14),
    );
  }
  return all(
    g().points([[-rOeil * 1.85, -rOeil * 1.74], [-rOeil * 0.48, -rOeil * 1.80]], 0.14),
    d().points([[rOeil * 0.48, -rOeil * 1.80], [rOeil * 1.85, -rOeil * 1.74]], 0.14),
  );
}

/** Cycle de marche latéral : quatre membres en polylignes, deux temps par pas. */
export function marcher(etre: any, duree: number, vers: 1 | -1 = 1) {
  const r = etre.rCorps;
  const pas = 0.30;
  return (function* () {
    const combien = Math.max(1, Math.floor(duree / pas));
    for (let i = 0; i < combien; i++) {
      yield* all(
        etre.jambeG().points([[-r * 0.30, r * 0.82], [-r * 0.78 * vers, r * 1.40]], pas / 2),
        etre.jambeD().points([[r * 0.30, r * 0.82], [r * 0.10 * vers, r * 1.46]], pas / 2),
        etre.brasG().points([[-r * 0.78, -r * 0.05], [-r * 0.9 * vers, r * 0.60]], pas / 2),
        etre.brasD().points([[r * 0.78, -r * 0.05], [r * 1.25 * vers, r * 0.10]], pas / 2),
        etre.gantG().position([-r * 0.9 * vers, r * 0.60], pas / 2),
        etre.gantD().position([r * 1.25 * vers, r * 0.10], pas / 2),
        etre.corps().y(etre.corps().y() - 9, pas / 2),
      );
      yield* all(
        etre.jambeG().points([[-r * 0.30, r * 0.82], [-r * 0.10 * vers, r * 1.46]], pas / 2),
        etre.jambeD().points([[r * 0.30, r * 0.82], [r * 0.78 * vers, r * 1.40]], pas / 2),
        etre.brasG().points([[-r * 0.78, -r * 0.05], [-r * 1.25 * vers, r * 0.10]], pas / 2),
        etre.brasD().points([[r * 0.78, -r * 0.05], [r * 0.9 * vers, r * 0.60]], pas / 2),
        etre.gantG().position([-r * 1.25 * vers, r * 0.10], pas / 2),
        etre.gantD().position([r * 0.9 * vers, r * 0.60], pas / 2),
        etre.corps().y(etre.corps().y() + 9, pas / 2),
      );
    }
  })();
}
