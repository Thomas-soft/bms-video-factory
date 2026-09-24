// Outils partagés par les trois traitements. Tout ce qui est temporel est ABSOLU :
// les tâches sont planifiées par `delay(t, …)` sur les horodatages de words.json,
// jamais par enchaînement, pour qu'aucune dérive ne s'accumule sur 32 s.
import donnees from './mots.json';

export type Mot = {w: string; t: number; e: number; seg: string};
export type Seg = {id: string; role: string; ost: string; intent: string; start: number; end: number};

export const MOTS: Mot[] = (donnees as any).mots;
export const SEGMENTS: Seg[] = (donnees as any).segments;

/** Regroupe les mots en blocs de lecture : ponctuation, silence, changement de segment. */
export function blocs(max = 5, maxCar = 999): Mot[][] {
  const out: Mot[][] = [];
  let cur: Mot[] = [];
  for (let i = 0; i < MOTS.length; i++) {
    const m = MOTS[i];
    cur.push(m);
    const suiv = MOTS[i + 1];
    const ponct = /[.,!?;:»]$/.test(m.w);
    const trou = suiv ? suiv.t - m.e : 99;
    const change = suiv ? suiv.seg !== m.seg : true;
    const car = cur.reduce((n, x) => n + x.w.length + 1, 0);
    if (cur.length >= max || car >= maxCar || (ponct && cur.length >= 2) || trou > 0.5 || change) {
      out.push(cur);
      cur = [];
    }
  }
  if (cur.length) out.push(cur);
  return out;
}

/** Horodatage du premier mot dont la forme normalisée commence par `prefixe`. */
export function quand(prefixe: string): number | null {
  const p = prefixe.toLowerCase();
  const m = MOTS.find(x =>
    x.w.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z']/g, '')
      .startsWith(p.normalize('NFD').replace(/[̀-ͯ]/g, '')));
  return m ? m.t : null;
}
