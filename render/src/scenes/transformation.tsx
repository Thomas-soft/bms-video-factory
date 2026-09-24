/**
 * TRANSFORMATION — une forme devient une autre, sous les yeux.
 *
 * Le morphing est fait sur les **points** d'un polygone, donc les deux formes ont le même nombre
 * de sommets : c'est la seule façon d'interpoler proprement, et cela suffit à faire passer un
 * objet pour un autre.
 */
import {Txt, Node, Line, Circle} from '@revideo/2d';
import {all, createRef, delay, easeOutCubic, easeInOutCubic, easeOutBack, linear} from '@revideo/core';
import {C, L, H, UX, melanger} from '../charte';
import {alea, socle, surcouches, ajuster} from '../commun';
import {blob, poly} from '../figures';

export function transformation(view: any, props: any, duree: number) {
  const {cam, taches, graine} = socle(view, props, duree);

  const avant = String(props.avant ?? props.small ?? props.label ?? '');
  const apres = String(props.apres ?? props.big ?? props.heading ?? '');
  const sommets = 10;
  const formeA = blob(230, graine * 3, sommets);
  const formeB = poly(sommets, 240, -90);

  const objet = createRef<Line>();
  const halo = createRef<Circle>();
  const eclats: any[] = [];
  const eclatsRefs: any[] = [];
  const r = alea(graine * 97);
  for (let i = 0; i < 10; i++) {
    const ref = createRef<Line>();
    eclatsRefs.push(ref);
    const a = (i / 10) * Math.PI * 2;
    eclats.push(<Line ref={ref} points={[[Math.cos(a) * 250, Math.sin(a) * 250],
                                         [Math.cos(a) * 330, Math.sin(a) * 330]]}
                      stroke={C.highlight} lineWidth={6} lineCap={'round'} opacity={0} />);
  }

  const motA = createRef<Txt>();
  const motB = createRef<Txt>();
  cam().add(
    <Node>
      <Circle ref={halo} size={520} stroke={C.highlight} lineWidth={5} opacity={0} />
      {eclats}
      <Line ref={objet} points={formeA} closed fill={melanger(C.accent, C.bg, 0.55)}
            stroke={C.accent} lineWidth={9} lineJoin={'round'} scale={0} />
      <Txt ref={motA} y={330} text={avant.toUpperCase()} fontFamily={C.font_title.family}
           fontWeight={C.font_title.weight} fontSize={62} fill={C.accent} opacity={0} />
      <Txt ref={motB} y={330} text={apres.toUpperCase()} fontFamily={C.font_title.family}
           fontWeight={C.font_title.weight} fontSize={62} fill={C.highlight} opacity={0} />
    </Node>,
  );
  ajuster(motA, UX * 1.4, 110, 30);
  ajuster(motB, UX * 1.4, 110, 30);

  const tMorph = Math.max(0.9, duree * 0.38);
  taches.push((function* () {
    yield* objet().scale(1, 0.45, easeOutBack);
    if (avant) yield* motA().opacity(1, 0.3);
  })());
  taches.push(delay(0.35, objet().rotation(18, Math.max(1, duree), linear)));

  taches.push(delay(tMorph, (function* () {
    // Compression avant la bascule : la forme « prend son élan ».
    yield* all(objet().scale(0.9, 0.16, easeOutCubic), motA().opacity(0, 0.16));
    eclatsRefs.forEach(ref => ref().opacity(1));
    halo().opacity(0.9).size(420);
    // La couleur est **posée**, pas interpolée : l'interpolation de Motion Canvas passe par un
    // violet qui n'est dans aucune charte (extrait réel du 19/09).
    objet().fill(melanger(C.highlight, C.bg, 0.55));
    objet().stroke(C.highlight);
    yield* all(
      objet().points(formeB, 0.7, easeInOutCubic),
      objet().scale(1.08, 0.7, easeOutBack),
      halo().size(700, 0.7, easeOutCubic),
      halo().opacity(0, 0.7),
      ...eclatsRefs.map(ref => all(ref().scale(1.5, 0.5, easeOutCubic), ref().opacity(0, 0.5))),
    );
    yield* objet().scale(1, 0.2);
    if (apres) yield* motB().opacity(1, 0.3);
  })()));

  surcouches(view, props);
  return taches;
}
