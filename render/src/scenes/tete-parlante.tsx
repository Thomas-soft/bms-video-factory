/**
 * TÊTE PARLANTE — un personnage occupe le cadre et parle. C'est le plan le plus fréquent de la
 * chaîne de référence, et le plus absent d'un moteur programmatique.
 *
 * Le sujet du plan **devient** le personnage : `props.who` nomme ce qui parle (« a star »,
 * « your brain »), et le corps prend la forme qui va avec. Aucun texte à l'écran : la voix dit
 * déjà ce qu'il y a à dire.
 */
import {Txt, Node, Circle, Rect} from '@revideo/2d';
import {all, createRef, delay, easeOutCubic, easeOutBack, linear} from '@revideo/core';
import {C, L, H, UX, melanger} from '../charte';
import {alea, socle, surcouches, ajuster, Mot} from '../commun';
import {etre, lignesDeVitesse} from '../figures';
import {parler, cligner, respirer, regarder, sursaut, expression} from '../jeu';

const FORMES = ['rond', 'blob', 'carre'] as const;

export function tetePar(view: any, props: any, duree: number) {
  const {cam, taches, graine} = socle(view, props, duree);
  const r = alea(graine * 307);
  const mots: Mot[] = props.words ?? [];

  const forme = FORMES[graine % FORMES.length];
  const couleur = graine % 2 === 0 ? C.accent : C.highlight;
  const heros = etre(700, couleur, graine, forme);
  const groupe = createRef<Node>();
  const vitesse = lignesDeVitesse(430, C.text, 14);

  cam().add(
    <Node ref={groupe} y={90} scale={0}>
      {vitesse.noeud}
      {heros.noeud}
    </Node>,
  );

  // Le nom de ce qui parle, en cartouche discret — jamais une phrase.
  if (props.who && String(props.who).trim()) {
    const cartouche = createRef<Node>();
    const nom = createRef<Txt>();
    cam().add(
      <Node ref={cartouche} y={-H * 0.36} opacity={0}>
        <Rect width={560} height={92} radius={46} fill={melanger(C.bg, couleur, 0.35)}
              stroke={couleur} lineWidth={4} />
        <Txt ref={nom} text={String(props.who).toUpperCase()} fontFamily={C.font_body.family}
             fontWeight={800} fontSize={44} fill={C.text} letterSpacing={2}
             width={500} textWrap textAlign={'center'} />
      </Node>,
    );
    ajuster(nom, 500, 76, 24);
    taches.push(delay(0.35, cartouche().opacity(1, 0.3)));
  }

  taches.push((function* () {
    yield* groupe().scale(1, 0.45, easeOutBack);
    yield* sursaut(heros.corps, 0.5);
  })());
  taches.push(...parler(heros.face, mots, duree));
  taches.push(cligner(heros.face, graine, duree));
  taches.push(delay(0.5, respirer(heros.buste, Math.max(0.6, duree - 0.5), 0.028)));

  // Le regard va et vient : un personnage qui fixe l'objectif dix secondes est un masque.
  taches.push(delay(0.8, (function* () {
    let t = 0.8;
    while (t < duree) {
      yield* regarder(heros.face, (r() - 0.5) * 900, (r() - 0.5) * 400, 0.35);
      const pause = 0.8 + r() * 1.1;
      yield* regarder(heros.face, 0, 0, pause);
      t += pause + 0.35;
    }
  })()));

  // Un geste ponctue le milieu du plan : sourcils, bras levé, lignes de vitesse.
  if (duree > 3.0) {
    const t = duree * 0.48;
    taches.push(delay(t, (function* () {
      yield* all(
        expression(heros.face, 'surprise', heros.rCorps * 0.30 * 0.26),
        heros.brasD().points([[heros.rCorps * 0.78, -heros.rCorps * 0.05],
                              [heros.rCorps * 1.25, -heros.rCorps * 0.75]], 0.22, easeOutBack),
        heros.gantD().position([heros.rCorps * 1.25, -heros.rCorps * 0.75], 0.22, easeOutBack),
      );
      vitesse.refs.forEach(ref => ref().opacity(0.9));
      yield* all(sursaut(heros.corps, 0.7),
                 ...vitesse.refs.map(ref => all(ref().scale(1.4, 0.35, easeOutCubic),
                                                ref().opacity(0, 0.35))));
      vitesse.refs.forEach(ref => ref().scale(1));
      yield* all(
        expression(heros.face, 'repos', heros.rCorps * 0.30 * 0.26),
        heros.brasD().points([[heros.rCorps * 0.78, -heros.rCorps * 0.05],
                              [heros.rCorps * 1.12, heros.rCorps * 0.42]], 0.3),
        heros.gantD().position([heros.rCorps * 1.12, heros.rCorps * 0.42], 0.3),
      );
    })()));
  }

  surcouches(view, props);
  return taches;
}
