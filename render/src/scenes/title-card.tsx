/**
 * Carte de titre — un énoncé plein cadre, filet d'accent, sous-titre. Le plan le plus sobre du
 * jeu : il sert d'ouverture de segment et de respiration entre deux scènes denses.
 */
import {Rect, Txt, Node} from '@revideo/2d';
import {all, createRef, delay, waitFor, easeOutCubic, easeOutExpo, linear} from '@revideo/core';
import {C, L, H, UX, MARGE} from '../charte';
import {fond, divulgation, titraille, taillePourTenir, ajuster} from '../commun';

export function titleCard(view: any, props: any, duree: number) {
  const graine: number = props.seed ?? 1;
  const taches: any[] = [fond(view, graine, duree, props.bg_variant ?? 0)];
  if (props.title && props.heading !== props.title) titraille(view, props.title);

  const enonce = String(props.heading ?? props.on_screen_text ?? props.title ?? '');
  const sous = String(props.label ?? props.subtitle ?? '');
  const taille = taillePourTenir(enonce, UX * 1.7, 132, 46);

  const bloc = createRef<Node>();
  const filet = createRef<Rect>();
  const enonceRef = createRef<Txt>();
  view.add(
    <Node ref={bloc} opacity={0} y={-10}>
      <Rect ref={filet} width={0} height={9} y={-taille * 0.95} radius={5} fill={C.highlight} />
      <Txt ref={enonceRef} text={enonce.toUpperCase()} fontFamily={C.font_title.family}
           fontWeight={C.font_title.weight} fontSize={taille} fill={C.text}
           width={UX * 1.8} textWrap textAlign={'center'} />
      {sous ? (
        <Txt y={taille * 0.92} text={sous} fontFamily={C.font_body.family}
             fontWeight={C.font_body.weight}
             fontSize={taillePourTenir(sous, UX * 1.5, 52, 26)} fill={C.accent}
             width={UX * 1.6} textWrap textAlign={'center'} />
      ) : null}
    </Node>,
  );

  ajuster(enonceRef, UX * 1.8, H * 0.5, 40);

  taches.push((function* () {
    bloc().y(34);
    yield* all(bloc().opacity(1, 0.3), bloc().y(-10, 0.5, easeOutExpo));
    yield* filet().width(Math.min(520, UX), 0.45, easeOutCubic);
  })());
  taches.push(delay(0.3, bloc().scale(1.04, Math.max(0.4, duree - 0.3), linear)));

  if (props.is_sponsor && props.disclosure) divulgation(view, props.disclosure);
  return taches;
}
