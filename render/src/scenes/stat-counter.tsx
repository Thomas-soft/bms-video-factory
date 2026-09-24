/**
 * Compteur de chiffres — une valeur qui monte, son unité, son libellé, un anneau qui se ferme.
 * La valeur vient du script (`props.value`), jamais d'un hasard : un chiffre inventé à l'écran
 * est une affirmation fausse sur une vidéo publiée.
 *
 * Deux pièges de Revideo 0.11 payés au rendu du 19/09, tous deux sur le même plan :
 * 1. `text={() => signal()}` — un texte **réactif** fait recalculer `Txt.spawnedChildren` dans un
 *    contexte sans scène : « The scene is not available in the current context. » 37 fois, et le
 *    chiffre n'apparaît pas. Le compteur est donc écrit par un `tween` qui pose le texte lui-même.
 * 2. Caler l'unité sur `chiffre().width()` lit la largeur d'un frère pendant sa mise en page. Un
 *    `Layout` en ligne fait ce calcul au bon moment.
 */
import {Rect, Txt, Node, Circle, Layout} from '@revideo/2d';
import {all, tween, createRef, delay, waitFor, easeOutCubic, easeOutExpo, easeOutQuint} from '@revideo/core';
import {C, L, H, UX} from '../charte';
import {fond, divulgation, titraille, taillePourTenir, ajuster} from '../commun';

export function statCounter(view: any, props: any, duree: number) {
  const graine: number = props.seed ?? 1;
  const taches: any[] = [fond(view, graine, duree, props.bg_variant ?? 0)];
  if (props.title) titraille(view, props.title);

  const cible = Number(props.value ?? 0);
  const decimales = Number.isInteger(cible) ? 0 : Math.min(2, (String(cible).split('.')[1] || '').length);
  const unite = String(props.unit ?? '');
  const libelle = String(props.label ?? props.on_screen_text ?? '');
  const prefixe = String(props.prefix ?? '');

  const arc = createRef<Circle>();
  const bloc = createRef<Node>();
  const rangee = createRef<Layout>();
  const chiffre = createRef<Txt>();
  const lbl = createRef<Node>();
  const texteLbl = createRef<Txt>();

  // Le chiffre final fixe la taille : dimensionner sur « 0 » ferait grandir le bloc pendant la
  // montée, et la composition bougerait sous les yeux.
  const final = prefixe + cible.toFixed(decimales);
  const taille = final.length > 5 ? 190 : final.length > 3 ? 230 : 280;

  view.add(
    <Node ref={bloc} y={-40} opacity={0}>
      <Circle size={580} stroke={C.text} lineWidth={9} opacity={0.12} />
      <Circle ref={arc} size={580} stroke={C.accent} lineWidth={9} startAngle={-90}
              endAngle={-90} closed={false} />
      <Layout ref={rangee} layout direction={'row'} alignItems={'start'} gap={14}>
        <Txt ref={chiffre} text={prefixe + (0).toFixed(decimales)}
             fontFamily={C.font_title.family} fontWeight={C.font_title.weight}
             fontSize={taille} fill={C.text} />
        <Txt text={unite} fontFamily={C.font_title.family} fontWeight={C.font_title.weight}
             fontSize={Math.round(taille * 0.38)} fill={C.highlight}
             marginTop={Math.round(taille * 0.12)} />
      </Layout>
    </Node>,
  );
  view.add(
    <Node ref={lbl} y={H * 0.30} opacity={0}>
      <Rect width={160} height={6} y={-64} radius={3} fill={C.highlight} />
      <Txt ref={texteLbl} text={libelle} fontFamily={C.font_body.family}
           fontWeight={C.font_body.weight}
           fontSize={taillePourTenir(libelle, UX * 1.6, 60, 30)} fill={C.text}
           width={UX * 1.7} textWrap textAlign={'center'} />
    </Node>,
  );
  ajuster(texteLbl, UX * 1.75, 180, 26);

  const montee = Math.min(1.6, Math.max(0.7, duree * 0.40));
  taches.push((function* () {
    bloc().scale(0.9);
    yield* all(bloc().opacity(1, 0.25), bloc().scale(1, 0.4, easeOutCubic));
    yield* all(
      tween(montee, valeur => {
        chiffre().text(prefixe + (cible * easeOutQuint(valeur)).toFixed(decimales));
      }, () => chiffre().text(final)),
      arc().endAngle(270, montee, easeOutCubic),
    );
    yield* all(rangee().scale(1.05, 0.14), arc().stroke(C.highlight, 0.14));
    yield* rangee().scale(1, 0.22);
  })());
  taches.push(delay(Math.min(duree * 0.5, montee + 0.15), (function* () {
    lbl().y(H * 0.32);
    yield* all(lbl().opacity(1, 0.3), lbl().y(H * 0.30, 0.4, easeOutExpo));
  })()));

  if (props.is_sponsor && props.disclosure) divulgation(view, props.disclosure);
  return taches;
}
