/**
 * Citation — guillemet ouvrant très grand, texte en serif, attribution. Pas de titraille :
 * une citation qui porte un sur-titre de segment se lit comme un encadré de magazine.
 */
import {Rect, Txt, Node} from '@revideo/2d';
import {all, createRef, delay, waitFor, easeOutCubic, easeOutExpo, linear} from '@revideo/core';
import {C, L, H, UX, MARGE} from '../charte';
import {fond, divulgation, taillePourTenir, ajuster} from '../commun';

export function quote(view: any, props: any, duree: number) {
  const graine: number = props.seed ?? 1;
  const taches: any[] = [fond(view, graine, duree, props.bg_variant ?? 0)];

  const texte = String(props.quote ?? props.on_screen_text ?? props.heading ?? '');
  const auteur = String(props.author ?? props.label ?? '');

  const guillemet = createRef<Txt>();
  const corps = createRef<Txt>();
  const signature = createRef<Node>();
  const taille = taillePourTenir(texte, UX * 1.55, 96, 36) * 1.35;

  view.add(
    <Txt ref={guillemet} text={'“'} fontFamily={C.font_title.family} fontWeight={700}
         fontSize={420} fill={C.accent} opacity={0} x={-UX * 0.72} y={-H * 0.16} />,
  );
  view.add(
    <Txt ref={corps} text={texte} fontFamily={'BMSSourceSerif'} fontWeight={500}
         fontSize={Math.min(96, taille)} fill={C.text} width={UX * 1.6} textWrap
         textAlign={'center'} y={-10} opacity={0} lineHeight={`${Math.round(Math.min(96, taille) * 1.28)}px`} />,
  );
  // Sans auteur, **pas de signature** : le filet seul se lisait comme un bloc oublié au montage.
  if (auteur) {
    view.add(
      <Node ref={signature} y={H * 0.26} opacity={0}>
        <Rect width={90} height={4} y={-40} fill={C.highlight} />
        <Txt text={`— ${auteur}`} fontFamily={C.font_body.family}
             fontWeight={C.font_body.weight} fontSize={44} fill={C.accent} letterSpacing={1} />
      </Node>,
    );
  }

  taches.push((function* () {
    yield* all(guillemet().opacity(0.85, 0.35, easeOutCubic), guillemet().y(-H * 0.19, 0.5, easeOutCubic));
  })());
  ajuster(corps, UX * 1.65, H * 0.46, 32);
  taches.push(delay(0.15, (function* () {
    corps().y(24);
    yield* all(corps().opacity(1, 0.45), corps().y(-10, 0.6, easeOutExpo));
  })()));
  if (auteur) {
    taches.push(delay(Math.min(duree * 0.45, 1.1), signature().opacity(1, 0.4, easeOutCubic)));
  }
  taches.push(delay(0.2, corps().scale(1.03, Math.max(0.5, duree - 0.2), linear)));

  if (props.is_sponsor && props.disclosure) divulgation(view, props.disclosure);
  return taches;
}
