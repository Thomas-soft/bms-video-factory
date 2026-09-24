/**
 * GROUPE — quatre ou cinq personnages en cercle, un seul parle à la fois, les autres réagissent.
 *
 * Le dispositif « réunion » relevé sur la chaîne de référence. Il sert à donner une voix à
 * plusieurs entités d'un coup — trois organes, quatre planètes, cinq causes — sans les écrire
 * en liste à puces.
 */
import {Txt, Node, Rect} from '@revideo/2d';
import {all, createRef, delay, easeOutCubic, easeOutBack, linear} from '@revideo/core';
import {C, L, H, UX, melanger} from '../charte';
import {alea, socle, surcouches, ajuster} from '../commun';
import {etre} from '../figures';
import {cligner, respirer, regarder, sursaut, expression} from '../jeu';

const FORMES = ['rond', 'blob', 'carre'] as const;

export function groupe(view: any, props: any, duree: number) {
  const {cam, taches, graine} = socle(view, props, duree);
  const r = alea(graine * 509);

  const noms: string[] = (props.parts ?? props.satellites ?? []).slice(0, 5);
  const combien = Math.max(3, Math.min(5, noms.length || 4));
  const couleurs = [C.accent, C.highlight, C.accent, C.highlight, C.text];
  const scene = createRef<Node>();
  const membres: any[] = [];
  const refs: any[] = [];
  const etiqs: any[] = [];

  // Sur une ellipse, pas sur une ligne : ceux du fond sont plus petits, et c'est ce qui donne
  // la profondeur d'une assemblée.
  for (let i = 0; i < combien; i++) {
    const a = Math.PI + (i / (combien - 1)) * Math.PI;   // demi-cercle face caméra
    const x = Math.cos(a) * 560;
    const y = Math.sin(a) * 120 + 150;
    const profondeur = 0.86 + (y - 130) / 900;
    const ref = createRef<Node>();
    const etiq = createRef<Node>();
    refs.push(ref);
    etiqs.push(etiq);
    const personne = etre(520, couleurs[i % couleurs.length], graine + i * 13,
                          FORMES[(graine + i) % FORMES.length]);
    membres.push({personne, ref, x, y, profondeur});
  }
  // Les plus proches passent devant : on les ajoute du fond vers l'avant.
  const ordre = [...membres].sort((a, b) => a.y - b.y);

  cam().add(
    <Node ref={scene}>
      {ordre.map((m, k) => (
        <Node ref={m.ref} x={m.x} y={m.y} scale={0}>
          {m.personne.noeud}
          <Node ref={etiqs[membres.indexOf(m)]} y={330} opacity={0}>
            <Rect width={330} height={70} radius={35} fill={melanger(C.bg, C.text, 0.12)}
                  stroke={C.text} lineWidth={3} opacity={0.9} />
            <Txt text={String(noms[membres.indexOf(m)] ?? '').toUpperCase()}
                 fontFamily={C.font_body.family} fontWeight={800} fontSize={34} fill={C.text}
                 width={296} textWrap textAlign={'center'} letterSpacing={1} />
          </Node>
        </Node>
      ))}
    </Node>,
  );
  membres.forEach(m => m.ref().scale(m.profondeur * 0));

  // Entrée en cascade, du fond vers l'avant.
  ordre.forEach((m, k) => {
    taches.push(delay(0.1 + k * 0.13, (function* () {
      yield* m.ref().scale(m.profondeur, 0.38, easeOutBack);
      if (noms[membres.indexOf(m)]) yield* etiqs[membres.indexOf(m)]().opacity(1, 0.22);
    })()));
  });

  membres.forEach((m, i) => {
    taches.push(cligner(m.personne.face, graine + i * 17, duree));
    taches.push(delay(0.5, respirer(m.personne.buste, Math.max(0.6, duree - 0.5), 0.026)));
  });

  // Un seul parle à la fois : il grandit, les autres le regardent.
  const debut = 0.2 + combien * 0.13;
  const tour = Math.max(0.8, (duree - debut - 0.3) / combien);
  membres.forEach((m, i) => {
    taches.push(delay(debut + i * tour, (function* () {
      yield* all(
        m.ref().scale(m.profondeur * 1.16, 0.25, easeOutBack),
        ...membres.filter((_, j) => j !== i).map(autre =>
          all(regarder(autre.personne.face, m.x - autre.x, m.y - autre.y, 0.3),
              autre.ref().scale(autre.profondeur * 0.96, 0.25))),
      );
      // Il parle : la bouche s'ouvre et se ferme sur un rythme régulier.
      const battements = Math.max(2, Math.floor((tour - 0.5) / 0.18));
      for (let k = 0; k < battements; k++) {
        yield* m.personne.face.bouche().scale([1, 0.7], 0.08, easeOutCubic);
        yield* m.personne.face.bouche().scale([1, 0.18], 0.09, easeOutCubic);
      }
      yield* m.ref().scale(m.profondeur, 0.25);
    })()));
  });
  membres.forEach(m => {
    m.personne.face.bouche().scale([1, 0.18]);
    m.personne.face.langue().opacity(1);
  });

  surcouches(view, props);
  return taches;
}
