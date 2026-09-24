/**
 * Grille d'icônes — icônes Tabler (MIT) et libellés, révélés en cascade.
 * L'icône est un **trait** : sa couleur et son épaisseur viennent de la charte, jamais du SVG.
 */
import {Rect, Txt, Node, Path} from '@revideo/2d';
import {all, createRef, delay, waitFor, easeOutBack, easeOutCubic} from '@revideo/core';
import {C, L, H, UX, MARGE} from '../charte';
import {alea, fond, divulgation, titraille, taillePourTenir, ajuster} from '../commun';
import {ICONES, NOMS_ICONES} from '../icons';

/**
 * Boîte d'encre d'un chemin SVG, mesurée **par le navigateur** (`getBBox`), une fois par icône.
 *
 * Deux façons de se tromper ont été payées au rendu du 19/09 : le composant `SVG` de Revideo
 * construit ses `Path` hors du contexte de scène et échoue en silence ; et un `Path` seul se
 * dessine dans le repère du chemin, sans se centrer — les icônes tombaient en bas à droite de
 * leur cadre, par-dessus leur libellé. La boîte mesurée règle les deux : elle donne l'échelle
 * **et** le recentrage.
 */
const BOITES = new Map<string, {x: number; y: number; width: number; height: number}>();

function boiteDuChemin(d: string) {
  const connue = BOITES.get(d);
  if (connue) return connue;
  const NS = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('style', 'position:absolute;width:0;height:0;overflow:hidden');
  const chemin = document.createElementNS(NS, 'path');
  chemin.setAttribute('d', d);
  svg.appendChild(chemin);
  document.body.appendChild(svg);
  const b = chemin.getBBox();
  document.body.removeChild(svg);
  const boite = {x: b.x, y: b.y, width: b.width || 24, height: b.height || 24};
  BOITES.set(d, boite);
  return boite;
}

/** Une icône Tabler en trait, centrée et mise à la taille demandée. */
function icone(nom: string, couleur: string, taille: number) {
  const d = ICONES[nom] ?? ICONES[NOMS_ICONES[0]];
  const b = boiteDuChemin(d);
  const echelle = taille / Math.max(b.width, b.height);
  return (
    <Node scale={echelle}>
      <Path data={d} stroke={couleur} lineWidth={1.8} lineCap={'round'} lineJoin={'round'}
            x={-(b.x + b.width / 2)} y={-(b.y + b.height / 2)} />
    </Node>
  );
}

export function iconGrid(view: any, props: any, duree: number) {
  const graine: number = props.seed ?? 1;
  const r = alea(graine);
  const taches: any[] = [fond(view, graine, duree, props.bg_variant ?? 0)];
  if (props.title) titraille(view, props.title);

  const items: Array<{icon: string; label: string}> = (props.icons ?? []).slice(0, 6);
  if (items.length === 0) items.push({icon: NOMS_ICONES[graine % NOMS_ICONES.length], label: props.on_screen_text || ''});

  const colonnes = items.length <= 2 ? items.length : items.length <= 4 ? 2 : 3;
  const lignes = Math.ceil(items.length / colonnes);
  const pasX = Math.min(520, (UX * 2) / colonnes);
  const pasY = lignes > 1 ? 380 : 0;
  const yOffset = props.heading ? 60 : 0;

  if (props.heading) {
    const tete = createRef<Node>();
    view.add(
      <Node ref={tete} y={-H / 2 + MARGE + 40} opacity={0}>
        <Txt text={String(props.heading).toUpperCase()} fontFamily={C.font_title.family}
             fontWeight={C.font_title.weight}
             fontSize={taillePourTenir(String(props.heading), UX * 1.8, 74, 36)} fill={C.text}
             width={UX * 1.8} textWrap textAlign={'center'} />
      </Node>,
    );
    taches.push(tete().opacity(1, 0.35, easeOutCubic));
  }

  items.forEach((item, i) => {
    const col = i % colonnes;
    const lig = Math.floor(i / colonnes);
    const nbCetteLigne = Math.min(colonnes, items.length - lig * colonnes);
    const x = (col - (nbCetteLigne - 1) / 2) * pasX;
    const y = (lig - (lignes - 1) / 2) * pasY + yOffset;
    const couleur = i % 3 === 1 ? C.highlight : C.accent;
    const cellule = createRef<Node>();
    const cadre = createRef<Rect>();
    const etiquette = createRef<Txt>();
    const taille = Math.min(190, pasX * 0.42);
    view.add(
      <Node ref={cellule} x={x} y={y} opacity={0} scale={0.7}>
        <Rect ref={cadre} width={taille + 70} height={taille + 70} radius={22}
              stroke={couleur} lineWidth={4} opacity={0.35} />
        {icone(item.icon, couleur, taille)}
        <Txt ref={etiquette} y={taille * 0.62 + 76} text={String(item.label ?? '')}
             fontFamily={C.font_body.family} fontWeight={600}
             fontSize={taillePourTenir(String(item.label ?? ''), pasX * 0.92, 44, 24)}
             fill={C.text} width={pasX * 0.92} textWrap textAlign={'center'} />
      </Node>,
    );
    ajuster(etiquette, pasX * 0.94, 120, 22);

    const t = props.beats && props.beats[i] != null
      ? Math.min(duree - 0.25, Math.max(0.05, props.beats[i]))
      : 0.2 + i * Math.max(0.28, (duree - 0.8) / Math.max(1, items.length));
    taches.push(delay(t, (function* () {
      yield* all(cellule().opacity(1, 0.22), cellule().scale(1, 0.4, easeOutBack));
      yield* cadre().opacity(0.8, 0.3);
    })()));
  });

  if (props.is_sponsor && props.disclosure) divulgation(view, props.disclosure);
  return taches;
}
