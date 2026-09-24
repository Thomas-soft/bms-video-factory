/**
 * Graphique — barres ou ligne, à partir des **données du script** (`props.data.series`).
 * Aucune valeur n'est fabriquée ici : sans série, la scène ne doit pas être choisie.
 */
import {Rect, Txt, Node, Line, Circle} from '@revideo/2d';
import {all, createRef, delay, waitFor, easeOutCubic, easeInOutCubic, linear} from '@revideo/core';
import {C, L, H, UX, UY, MARGE} from '../charte';
import {fond, divulgation, titraille, taillePourTenir, ajuster} from '../commun';

export function chart(view: any, props: any, duree: number) {
  const graine: number = props.seed ?? 1;
  const taches: any[] = [fond(view, graine, duree, props.bg_variant ?? 0)];
  if (props.title) titraille(view, props.title);

  const donnees = props.data ?? {};
  const serie: Array<{label: string; value: number}> = (donnees.series ?? []).slice(0, 6);
  const unite = String(donnees.unit ?? '');
  const genre = donnees.kind === 'line' ? 'line' : 'bar';
  const entete = String(donnees.heading ?? props.heading ?? props.on_screen_text ?? '');

  const hautCadre = -H * 0.30;
  const basCadre = H * 0.22;
  const hauteurUtile = basCadre - hautCadre;
  const maxi = Math.max(...serie.map(s => Math.abs(Number(s.value) || 0)), 1);

  if (entete) {
    const tete = createRef<Node>();
    const texteTete = createRef<Txt>();
    view.add(
      <Node ref={tete} y={-H / 2 + MARGE + 34} opacity={0}>
        <Txt ref={texteTete} text={entete.toUpperCase()} fontFamily={C.font_title.family}
             fontWeight={C.font_title.weight}
             fontSize={taillePourTenir(entete, UX * 1.8, 68, 32)} fill={C.text}
             width={UX * 1.8} textWrap textAlign={'center'} />
      </Node>,
    );
    ajuster(texteTete, UX * 1.8, 170, 30);
    taches.push(tete().opacity(1, 0.35, easeOutCubic));
  }

  // Axe : un seul trait, à la base. Une grille complète sur un plan de 5 s ne se lit pas.
  const axe = createRef<Line>();
  view.add(
    <Line ref={axe} points={[[-UX, basCadre], [UX, basCadre]]} stroke={C.text_outline}
          lineWidth={4} opacity={0.6} end={0} />,
  );
  taches.push(axe().end(1, 0.45, easeOutCubic));

  const pas = (UX * 2) / Math.max(1, serie.length);

  if (genre === 'bar') {
    serie.forEach((point, i) => {
      const valeur = Math.abs(Number(point.value) || 0);
      const hauteur = Math.max(10, (valeur / maxi) * hauteurUtile * 0.92);
      const x = -UX + pas * (i + 0.5);
      const barre = createRef<Rect>();
      const val = createRef<Node>();
      const couleur = i === serie.findIndex(s => Math.abs(Number(s.value)) === maxi) ? C.highlight : C.accent;
      view.add(
        <Node x={x}>
          <Rect ref={barre} width={Math.min(190, pas * 0.56)} height={0} y={basCadre}
                offset={[0, 1]} radius={[8, 8, 0, 0]} fill={couleur} />
          <Node ref={val} y={basCadre - hauteur - 46} opacity={0}>
            <Txt text={`${point.value}${unite}`} fontFamily={C.font_title.family}
                 fontWeight={C.font_title.weight} fontSize={58} fill={C.text} />
          </Node>
          <Txt y={basCadre + 48} text={String(point.label ?? '')} fontFamily={C.font_body.family}
               fontWeight={C.font_body.weight}
               fontSize={taillePourTenir(String(point.label ?? ''), pas * 0.92, 40, 22)}
               fill={C.text} opacity={0.85} width={pas * 0.94} textWrap textAlign={'center'} />
        </Node>,
      );
      const t = 0.3 + i * Math.max(0.2, (duree - 1.2) / Math.max(1, serie.length));
      taches.push(delay(t, (function* () {
        yield* barre().height(hauteur, 0.55, easeOutCubic);
        yield* val().opacity(1, 0.25);
      })()));
    });
  } else {
    const points: [number, number][] = serie.map((point, i) => [
      -UX + pas * (i + 0.5),
      basCadre - (Math.abs(Number(point.value) || 0) / maxi) * hauteurUtile * 0.92,
    ]);
    const courbe = createRef<Line>();
    view.add(<Line ref={courbe} points={points} stroke={C.accent} lineWidth={9}
                   radius={20} lineCap={'round'} end={0} />);
    taches.push(delay(0.3, courbe().end(1, Math.min(2.2, duree * 0.55), easeInOutCubic)));
    points.forEach((p, i) => {
      const noeud = createRef<Node>();
      view.add(
        <Node ref={noeud} x={p[0]} y={p[1]} opacity={0}>
          <Circle size={26} fill={i === serie.length - 1 ? C.highlight : C.text} />
          <Txt y={-52} text={`${serie[i].value}${unite}`} fontFamily={C.font_title.family}
               fontWeight={C.font_title.weight} fontSize={46} fill={C.text} />
        </Node>,
      );
      view.add(
        <Txt x={p[0]} y={basCadre + 48} text={String(serie[i].label ?? '')}
             fontFamily={C.font_body.family} fontWeight={C.font_body.weight}
             fontSize={taillePourTenir(String(serie[i].label ?? ''), pas * 0.92, 38, 22)}
             fill={C.text} opacity={0.85} width={pas * 0.94} textWrap textAlign={'center'} />,
      );
      const t = 0.35 + (i + 1) * (Math.min(2.2, duree * 0.55) / Math.max(1, points.length));
      taches.push(delay(t, noeud().opacity(1, 0.2)));
    });
  }

  if (props.is_sponsor && props.disclosure) divulgation(view, props.disclosure);
  return taches;
}
