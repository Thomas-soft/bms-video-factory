/**
 * COUPE — un objet s'ouvre couche par couche, chacune nommée.
 *
 * L'objet est d'abord plein et opaque ; il se tranche, ses couches s'écartent, le cœur apparaît.
 * C'est la mécanique de vulgarisation la plus lisible qui soit : on montre l'intérieur.
 */
import {Txt, Node, Line, Circle, Rect} from '@revideo/2d';
import {all, createRef, delay, easeOutCubic, easeInOutCubic, easeOutBack, linear} from '@revideo/core';
import {C, L, H, UX, melanger} from '../charte';
import {socle, surcouches, annotation, ajuster} from '../commun';

export function coupe(view: any, props: any, duree: number) {
  const {cam, taches, graine} = socle(view, props, duree);

  const noms: string[] = (props.layers ?? props.parts ?? []).slice(0, 4);
  const combien = Math.max(2, noms.length || 3);
  const couleurs = [C.accent, C.highlight, C.text, C.accent];
  const rMax = 360;

  const objet = createRef<Node>();
  const couchesRefs: any[] = [];
  const couches: any[] = [];
  // De l'extérieur vers l'intérieur : chaque couche est un anneau épais, découpé sur un quartier.
  for (let i = 0; i < combien; i++) {
    const ref = createRef<Node>();
    couchesRefs.push(ref);
    const rExt = rMax - i * (rMax / (combien + 0.6));
    const couleur = couleurs[i % couleurs.length];
    couches.push(
      <Node ref={ref} scale={0}>
        <Circle size={rExt * 2} fill={melanger(couleur, C.bg, i === combien - 1 ? 0.25 : 0.72)}
                stroke={couleur} lineWidth={7} startAngle={-90} endAngle={250} closed />
      </Node>,
    );
  }

  const lame = createRef<Line>();
  cam().add(
    <Node ref={objet}>
      {couches}
      <Line ref={lame} points={[[0, -rMax * 1.25], [0, rMax * 1.25]]} stroke={C.highlight}
            lineWidth={5} end={0} opacity={0} />
    </Node>,
  );

  const notes = noms.slice(0, 3).map((texte, i) => {
    const rExt = rMax - i * (rMax / (combien + 0.6));
    const cible: [number, number] = [Math.cos(-0.6 + i * 0.5) * rExt * 0.82,
                                     Math.sin(-0.6 + i * 0.5) * rExt * 0.82];
    return annotation(cible, [UX, -220 + i * 190], texte, couleurs[i % couleurs.length]);
  });
  notes.forEach(n => cam().add(n.noeud));

  // 1. L'objet apparaît plein.
  taches.push((function* () {
    for (let i = 0; i < combien; i++) {
      yield* couchesRefs[i]().scale(1, 0.26, easeOutBack);
    }
  })());

  // 2. La lame passe. C'est le moment où le plan bascule.
  const tLame = 0.2 + combien * 0.26;
  taches.push(delay(tLame, (function* () {
    lame().opacity(1);
    yield* lame().end(1, 0.3, easeOutCubic);
    yield* lame().opacity(0, 0.25);
  })()));

  // 3. Les couches s'écartent en éventail, de l'extérieur vers le cœur.
  const tOuvre = tLame + 0.35;
  for (let i = 0; i < combien - 1; i++) {
    taches.push(delay(tOuvre + i * 0.18, all(
      couchesRefs[i]().rotation(14 + i * 10, 0.7, easeInOutCubic),
      couchesRefs[i]().position([70 + i * 40, -30 - i * 18], 0.7, easeInOutCubic),
      couchesRefs[i]().opacity(0.85, 0.5),
    )));
  }
  taches.push(delay(tOuvre + 0.3, couchesRefs[combien - 1]().scale(1.12, 0.5, easeOutBack)));
  notes.forEach((n, i) => taches.push(delay(tOuvre + 0.5 + i * 0.32, n.jouer())));

  // 4. Respiration jusqu'à la fin : l'objet ne se fige pas.
  taches.push(delay(tOuvre + 0.4, objet().rotation(-6, Math.max(0.8, duree - tOuvre), linear)));

  if (props.heading) {
    const titre = createRef<Txt>();
    const bloc = createRef<Node>();
    view.add(
      <Node ref={bloc} y={-H / 2 + 150} opacity={0}>
        <Txt ref={titre} text={String(props.heading).toUpperCase()}
             fontFamily={C.font_title.family} fontWeight={C.font_title.weight} fontSize={58}
             fill={C.text} width={UX * 1.7} textWrap textAlign={'center'} />
      </Node>,
    );
    ajuster(titre, UX * 1.7, 130, 28);
    taches.push(bloc().opacity(1, 0.35));
  }

  surcouches(view, props);
  return taches;
}
