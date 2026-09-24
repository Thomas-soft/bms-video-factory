/**
 * Bandeau — nom, fonction, filet d'accent. Entre par la gauche, sort avant la fin du plan pour
 * ne pas se confondre avec le bandeau de sous-titres, qui vit plus bas (charte.subtitles).
 */
import {Rect, Txt, Node} from '@revideo/2d';
import {all, createRef, delay, waitFor, easeOutExpo, easeInCubic, linear} from '@revideo/core';
import {C, L, H, UX, MARGE} from '../charte';
import {fond, divulgation, taillePourTenir, ajuster} from '../commun';

export function lowerThird(view: any, props: any, duree: number) {
  const graine: number = props.seed ?? 1;
  const taches: any[] = [fond(view, graine, duree, props.bg_variant ?? 0)];

  const nom = String(props.heading ?? props.on_screen_text ?? props.title ?? '');
  const fonction = String(props.label ?? props.subtitle ?? '');

  // Le fond reste habité : un mot-clé très grand, à peine visible, derrière le bandeau.
  if (props.watermark) {
    const filigrane = createRef<Txt>();
    view.add(
      <Txt ref={filigrane} text={String(props.watermark).toUpperCase()}
           fontFamily={C.font_title.family} fontWeight={C.font_title.weight}
           fontSize={300} fill={C.text} opacity={0.06} y={-60} />,
    );
    taches.push(filigrane().x(40, duree, linear));
  }

  const bandeau = createRef<Node>();
  const filet = createRef<Rect>();
  const plaque = createRef<Rect>();
  const texteNom = createRef<Txt>();
  const tailleNom = taillePourTenir(nom, UX * 1.4, 88, 40);
  const largeur = Math.min(UX * 1.9, Math.max(520, nom.length * tailleNom * 0.56 + 120));

  view.add(
    <Node ref={bandeau} x={-L / 2 + MARGE} y={H * 0.22} opacity={0}>
      <Rect ref={plaque} width={largeur} height={fonction ? 178 : 120} radius={[0, 12, 12, 0]}
            fill={C.bg} stroke={C.accent} lineWidth={3} offset={[-1, 0]} opacity={0.92} />
      <Rect ref={filet} width={14} height={fonction ? 178 : 120} fill={C.highlight} offset={[-1, 0]} />
      <Txt ref={texteNom} x={46} y={fonction ? -34 : 0} offset={[-1, 0]} text={nom}
           fontFamily={C.font_title.family} fontWeight={C.font_title.weight}
           fontSize={tailleNom} fill={C.text} />
      {fonction ? (
        <Txt x={46} y={44} offset={[-1, 0]} text={fonction.toUpperCase()}
             fontFamily={C.font_body.family} fontWeight={C.font_body.weight}
             fontSize={Math.round(tailleNom * 0.46)} fill={C.accent} letterSpacing={2} />
      ) : null}
    </Node>,
  );

  // La plaque suit le texte mesuré, pas l'inverse : un nom plus long qu'estimé ferait
  // déborder le cartouche, ce qui se voit davantage qu'une plaque un peu large.
  ajuster(texteNom, UX * 1.55, 130, 34);
  plaque().width(Math.min(UX * 1.9, texteNom().width() + 120));

  taches.push((function* () {
    bandeau().x(-L / 2 - largeur);
    yield* all(bandeau().opacity(1, 0.2), bandeau().x(-L / 2 + MARGE, 0.45, easeOutExpo));
  })());
  if (duree > 2.2) {
    taches.push(delay(duree - 0.6, all(
      bandeau().opacity(0, 0.35), bandeau().x(-L / 2 - largeur, 0.45, easeInCubic),
    )));
  }

  if (props.is_sponsor && props.disclosure) divulgation(view, props.disclosure);
  return taches;
}
