/**
 * DUO — deux personnages, l'un parle, l'autre réagit, et la caméra passe de l'un à l'autre.
 *
 * C'est la scène de dialogue de la chaîne de référence, et le dispositif le plus économique pour
 * porter une objection ou une bascule : le doute n'est pas écrit, il est joué.
 */
import {Txt, Node, Circle} from '@revideo/2d';
import {all, createRef, delay, easeOutCubic, easeInOutCubic, easeOutBack, linear} from '@revideo/core';
import {C, L, H, UX, melanger} from '../charte';
import {alea, socle, surcouches, ajuster, Mot} from '../commun';
import {etre, lignesDeVitesse} from '../figures';
import {parler, cligner, respirer, regarder, sursaut, expression} from '../jeu';

export function duo(view: any, props: any, duree: number) {
  const {cam, taches, graine} = socle(view, props, duree);
  const r = alea(graine * 401);
  const mots: Mot[] = props.words ?? [];

  const hauteur = 560;
  const gauche = etre(hauteur, C.accent, graine, 'rond');
  const droite = etre(hauteur, C.highlight, graine + 7, graine % 2 ? 'blob' : 'carre');
  const gRef = createRef<Node>();
  const dRef = createRef<Node>();
  const scene = createRef<Node>();
  const vitesse = lignesDeVitesse(300, C.text, 12);
  const vRef = createRef<Node>();

  const xG = -440;
  const xD = 440;

  cam().add(
    <Node ref={scene} y={110}>
      <Node ref={gRef} x={xG} scale={0}>{gauche.noeud}</Node>
      <Node ref={dRef} x={xD} scale={0}>{droite.noeud}</Node>
      <Node ref={vRef} x={xD} y={-hauteur * 0.1}>{vitesse.noeud}</Node>
    </Node>,
  );

  // Entrées décalées, puis chacun regarde l'autre.
  taches.push((function* () {
    yield* gRef().scale(1, 0.4, easeOutBack);
  })());
  taches.push(delay(0.18, (function* () {
    yield* dRef().scale(1, 0.4, easeOutBack);
    yield* all(regarder(gauche.face, xD - xG, 0, 0.3), regarder(droite.face, xG - xD, 0, 0.3));
  })()));

  // Le premier parle sur toute la première moitié ; le second écoute et hoche.
  const bascule = duree * 0.55;
  const motsG = mots.filter(m => m.t < bascule);
  const motsD = mots.filter(m => m.t >= bascule).map(m => ({...m, t: m.t, e: m.e}));
  taches.push(...parler(gauche.face, motsG, bascule));
  taches.push(...parler(droite.face, motsD, duree));
  taches.push(cligner(gauche.face, graine, duree));
  taches.push(cligner(droite.face, graine + 11, duree));
  taches.push(delay(0.4, respirer(gauche.buste, Math.max(0.6, duree - 0.4), 0.03)));
  taches.push(delay(0.4, respirer(droite.buste, Math.max(0.6, duree - 0.4), 0.026)));

  // La caméra se rapproche de celui qui parle : c'est le champ-contrechamp, en un seul plan.
  taches.push(delay(0.6, all(
    scene().position([-xG * 0.45, 130], Math.max(0.6, bascule - 0.6), easeInOutCubic),
    scene().scale(1.18, Math.max(0.6, bascule - 0.6), easeInOutCubic),
  )));

  // Bascule : le second sursaute, lignes de vitesse, la caméra passe sur lui.
  taches.push(delay(bascule, (function* () {
    vitesse.refs.forEach(ref => ref().opacity(0.9));
    yield* all(
      expression(droite.face, 'surprise', droite.rCorps * 0.30 * 0.26),
      sursaut(droite.corps, 1),
      scene().position([-xD * 0.45, 130], 0.5, easeInOutCubic),
      ...vitesse.refs.map(ref => all(ref().scale(1.5, 0.4, easeOutCubic),
                                     ref().opacity(0, 0.4))),
      droite.brasG().points([[-droite.rCorps * 0.78, -droite.rCorps * 0.05],
                             [-droite.rCorps * 1.2, -droite.rCorps * 0.7]], 0.25, easeOutBack),
      droite.gantG().position([-droite.rCorps * 1.2, -droite.rCorps * 0.7], 0.25, easeOutBack),
    );
    yield* all(regarder(gauche.face, xD - xG, 0, 0.3), regarder(droite.face, xG - xD, 0, 0.3));
  })()));

  if (props.label && String(props.label).trim()) {
    const bulle = createRef<Node>();
    const mot = createRef<Txt>();
    cam().add(
      <Node ref={bulle} x={xD - 40} y={-220} opacity={0} scale={0.6}>
        <Circle width={430} height={190} fill={C.text} />
        <Circle x={-150} y={110} size={54} fill={C.text} />
        <Circle x={-200} y={150} size={26} fill={C.text} />
        <Txt ref={mot} text={String(props.label).toUpperCase()} fontFamily={C.font_body.family}
             fontWeight={800} fontSize={50} fill={C.bg} width={360} textWrap
             textAlign={'center'} />
      </Node>,
    );
    ajuster(mot, 360, 150, 24);
    taches.push(delay(bascule + 0.15, all(bulle().opacity(1, 0.2),
                                          bulle().scale(1, 0.3, easeOutBack))));
    taches.push(delay(Math.min(duree - 0.3, bascule + 1.6), bulle().opacity(0, 0.3)));
  }

  surcouches(view, props);
  return taches;
}
