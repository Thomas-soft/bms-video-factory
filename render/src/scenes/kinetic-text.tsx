/**
 * Typographie cinétique — les mots apparaissent au rythme de `words.json`.
 *
 * Le défaut à ne pas répéter (verdict du 16/09 sur la preuve de l'étape 5.2 : « très nul,
 * non professionnel ») était l'uniformité : un bloc centré, même taille, même entrée, vingt fois.
 * Ici chaque bloc tire son **parti** dans une liste de quatre — échelle, ancrage, entrée — et
 * deux blocs voisins n'ont jamais le même. Le mot le plus long du bloc prend l'accent.
 */
import {Rect, Txt, Node} from '@revideo/2d';
import {all, createRef, delay, waitFor, easeOutCubic, easeOutBack, easeOutExpo, linear} from '@revideo/core';
import {C, L, H, UX, MARGE} from '../charte';
import {alea, blocs, fond, divulgation, titraille, taillePourTenir, ajuster, Mot} from '../commun';

export function kineticText(view: any, props: any, duree: number) {
  const graine: number = props.seed ?? 1;
  const r = alea(graine);
  const mots: Mot[] = props.words ?? [];
  const taches: any[] = [fond(view, graine, duree, props.bg_variant ?? 0)];
  if (props.title) titraille(view, props.title);

  const groupes = blocs(mots, 4);
  // Sans horodatage utilisable, le plan se rabat sur le texte incrusté : mieux vaut une carte
  // typographique qu'un plan vide.
  if (groupes.length === 0) {
    const secours = (props.on_screen_text || props.title || '').toString();
    if (!secours) return taches;
    const ref = createRef<Txt>();
    view.add(
      <Txt ref={ref} text={secours.toUpperCase()} fontFamily={C.font_title.family}
           fontWeight={C.font_title.weight} fontSize={taillePourTenir(secours, UX * 2, 150, 44)}
           fill={C.text} opacity={0} textWrap width={UX * 2} textAlign={'center'} />,
    );
    ajuster(ref, UX * 1.9, H * 0.66, 34);
    taches.push(ref().opacity(1, 0.4, easeOutCubic));
    taches.push(delay(0.2, ref().scale(1.04, duree - 0.2, linear)));
    return taches;
  }

  const zone = createRef<Node>();
  view.add(<Node ref={zone} />);
  let partiPrecedent = -1;

  groupes.forEach((groupe, index) => {
    // Quatre partis de composition, tirés sans répétition immédiate : c'est le contraste
    // d'échelle et d'ancrage qui fait lire un plan comme du motion design et non comme un
    // sous-titre animé.
    let parti = Math.floor(r() * 4);
    if (parti === partiPrecedent) parti = (parti + 1) % 4;
    partiPrecedent = parti;

    const texte = groupe.map(m => m.w).join(' ');
    const echelles = [1.0, 1.55, 0.72, 1.2];
    const base = taillePourTenir(texte, UX * 1.85, 190, 40);
    const taille = Math.max(38, Math.round(base * echelles[parti]));
    const ancrages: Array<[number, number]> = [[0, 0], [-1, 0], [1, 0], [0, 0]];
    const xs = [0, -UX, UX, 0];
    const ys = [0, -H * 0.16, H * 0.18, H * 0.04];

    const bloc = createRef<Node>();
    const masque = createRef<Rect>();
    const txt = createRef<Txt>();
    // Le mot le plus long du bloc prend la couleur d'accent : une rupture de couleur par bloc,
    // pas une par mot — au-delà, le plan clignote.
    const vedette = groupe.reduce((a, b) => (b.w.length > a.w.length ? b : a), groupe[0]).w;
    const morceaux = groupe.map(m => (
      <Txt text={m.w + ' '} fontFamily={C.font_title.family} fontWeight={C.font_title.weight}
           fontSize={taille} fill={m.w === vedette && groupe.length > 1 ? C.highlight : C.text} />
    ));

    view.add(
      <Node ref={bloc} x={xs[parti]} y={ys[parti]} opacity={0}>
        <Txt ref={txt} offset={ancrages[parti]} fontFamily={C.font_title.family}
             fontWeight={C.font_title.weight} fontSize={taille} fill={C.text}
             width={UX * 1.9} textWrap textAlign={parti === 1 ? 'left' : parti === 2 ? 'right' : 'center'}
             x={parti === 1 ? 0 : parti === 2 ? 0 : 0}>
          {morceaux}
        </Txt>
        <Rect ref={masque} width={0} height={taille * 0.16} fill={C.accent}
              y={taille * 0.62} offset={[-1, 0]} x={-UX * 0.9} opacity={parti === 0 ? 1 : 0} />
      </Node>,
    );

    ajuster(txt, UX * 1.9, H * 0.62, 34);
    const t0 = Math.max(0, groupe[0].t);
    const t1 = Math.min(duree, groupe[groupe.length - 1].e + 0.12);
    const vie = Math.max(0.35, t1 - t0);

    taches.push(delay(t0, (function* () {
      bloc().opacity(0);
      if (parti === 1) { bloc().x(xs[parti] - 90); yield* all(bloc().opacity(1, 0.18), bloc().x(xs[parti], 0.32, easeOutExpo)); }
      else if (parti === 2) { bloc().x(xs[parti] + 90); yield* all(bloc().opacity(1, 0.18), bloc().x(xs[parti], 0.32, easeOutExpo)); }
      else if (parti === 3) { bloc().scale(0.82); yield* all(bloc().opacity(1, 0.18), bloc().scale(1, 0.34, easeOutBack)); }
      else { bloc().y(ys[parti] + 46); yield* all(bloc().opacity(1, 0.2), bloc().y(ys[parti], 0.3, easeOutCubic)); }
      if (parti === 0) yield* masque().width(Math.min(UX * 1.7, texte.length * taille * 0.5), 0.3, easeOutCubic);
      yield* waitFor(Math.max(0.05, vie - 0.55));
      yield* all(bloc().opacity(0, 0.22), bloc().scale(parti === 3 ? 1.06 : 0.97, 0.22));
    })()));
  });

  if (props.is_sponsor && props.disclosure) divulgation(view, props.disclosure);
  return taches;
}
