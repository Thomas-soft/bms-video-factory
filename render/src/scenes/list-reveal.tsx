/**
 * Liste révélée — les points apparaissent un à un, au rythme de la voix quand `words.json` le
 * permet, sinon à intervalle régulier. Un point = un filet d'accent, un numéro, une ligne.
 * Trois points au maximum visibles : au-delà, la liste n'est plus lue, elle est subie.
 */
import {Rect, Txt, Node, Circle} from '@revideo/2d';
import {all, createRef, delay, waitFor, easeOutCubic, easeOutExpo} from '@revideo/core';
import {C, L, H, UX, MARGE} from '../charte';
import {alea, fond, divulgation, titraille, taillePourTenir, ajuster} from '../commun';

export function listReveal(view: any, props: any, duree: number) {
  const graine: number = props.seed ?? 1;
  const taches: any[] = [fond(view, graine, duree, props.bg_variant ?? 0)];
  if (props.title) titraille(view, props.title);

  const points: string[] = (props.items ?? []).filter((x: any) => !!x).slice(0, 4);
  if (points.length === 0) points.push(props.on_screen_text || props.title || '—');

  const entete = createRef<Node>();
  const texteEntete = createRef<Txt>();
  const hauteurLigne = points.length >= 4 ? 150 : 190;
  const y0 = -((points.length - 1) * hauteurLigne) / 2 + (props.heading ? 70 : 0);

  if (props.heading) {
    view.add(
      <Node ref={entete} y={-H / 2 + MARGE + 70} opacity={0}>
        <Txt ref={texteEntete} text={String(props.heading).toUpperCase()} fontFamily={C.font_title.family}
             fontWeight={C.font_title.weight}
             fontSize={taillePourTenir(String(props.heading), UX * 1.8, 82, 40)}
             fill={C.text} width={UX * 1.8} textWrap textAlign={'center'} />
        <Rect y={62} width={180} height={7} radius={4} fill={C.highlight} />
      </Node>,
    );
    ajuster(texteEntete, UX * 1.8, 190, 32);
    taches.push(all(entete().opacity(1, 0.4, easeOutCubic), entete().y(-H / 2 + MARGE + 56, 0.4, easeOutCubic)));
  }

  const rythme = points.map((_, i) =>
    props.beats && props.beats[i] != null
      ? Math.min(duree - 0.3, Math.max(0.05, props.beats[i]))
      : 0.25 + i * Math.max(0.5, (duree - 0.9) / points.length));

  const corpsRefs: any[] = [];
  points.forEach((texte, i) => {
    const ligne = createRef<Node>();
    const filet = createRef<Rect>();
    const pastille = createRef<Circle>();
    const corps = createRef<Txt>();
    corpsRefs.push(corps);
    const taille = taillePourTenir(texte, UX * 1.55, points.length >= 4 ? 62 : 76, 34);
    view.add(
      <Node ref={ligne} x={-UX} y={y0 + i * hauteurLigne} opacity={0}>
        <Circle ref={pastille} size={62} stroke={C.accent} lineWidth={5} x={30} scale={0} />
        <Txt x={30} text={String(i + 1)} fontFamily={C.font_title.family} fontWeight={700}
             fontSize={32} fill={C.highlight} />
        <Txt ref={corps} x={96} offset={[-1, 0]} text={texte} fontFamily={C.font_body.family}
             fontWeight={C.font_body.weight} fontSize={taille} fill={C.text}
             width={UX * 1.6} textWrap />
        <Rect ref={filet} x={0} y={taille * 0.85} width={0} height={4} fill={C.accent}
              offset={[-1, 0]} opacity={0.7} />
      </Node>,
    );
    taches.push(delay(rythme[i], (function* () {
      ligne().x(-UX - 70);
      yield* all(
        ligne().opacity(1, 0.22),
        ligne().x(-UX, 0.38, easeOutExpo),
        pastille().scale(1, 0.4, easeOutCubic),
      );
      yield* filet().width(Math.min(UX * 1.7, texte.length * taille * 0.52), 0.5, easeOutCubic);
    })()));
  });

  // **Une seule taille pour toute la liste.** Ajustée point par point, la première ligne sortait
  // en corps 30 et la deuxième en corps 60 : la liste se lisait comme trois compositions
  // différentes empilées (rendu du 19/09).
  corpsRefs.forEach(ref => ajuster(ref, UX * 1.6, hauteurLigne * 0.84, 26));
  const commune = Math.min(...corpsRefs.map(ref => ref().fontSize()));
  corpsRefs.forEach(ref => ref().fontSize(commune));

  if (props.is_sponsor && props.disclosure) divulgation(view, props.disclosure);
  return taches;
}
