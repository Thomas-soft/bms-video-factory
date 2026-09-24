/**
 * ASSEMBLAGE — des pièces arrivent du hors-champ, se verrouillent en un tout, se font annoter,
 * puis le tout se disloque.
 *
 * C'est le dispositif que Thomas a retenu dans la preuve du 16/09 (« jusqu'à présent y'a que le
 * B qui est intéressant ») : **il se passe quelque chose**, l'objet n'existe pas au début du plan
 * et existe à la fin. La géométrie, elle, est générique — le script ne fournit que des mots.
 */
import {Rect, Txt, Node, Line, Circle} from '@revideo/2d';
import {all, createRef, delay, easeOutCubic, easeInCubic, easeOutBack, easeInOutCubic, linear} from '@revideo/core';
import {C, L, H, UX, melanger} from '../charte';
import {alea, socle, surcouches, annotation, taillePourTenir} from '../commun';
import {poly, blob} from '../figures';

export function assemble(view: any, props: any, duree: number) {
  const {cam, taches, graine} = socle(view, props, duree);
  const r = alea(graine * 17);

  const pieces: string[] = (props.parts ?? []).slice(0, 5);
  const combien = Math.max(3, pieces.length || 4);
  // Le rayon suit le nombre de pièces : à trois, un anneau de 232 laisse un trou au milieu
  // plus grand que les pièces elles-mêmes.
  const rayon = combien <= 3 ? 158 : combien === 4 ? 192 : 228;
  const couleurs = [C.accent, C.highlight, C.text, C.accent, C.highlight];

  const groupe = createRef<Node>();
  const coeur = createRef<Circle>();
  const morceaux: any[] = [];
  const refs: any[] = [];
  const cibles: [number, number][] = poly(combien, rayon, -90);

  for (let i = 0; i < combien; i++) {
    const ref = createRef<Node>();
    refs.push(ref);
    const couleur = couleurs[i % couleurs.length];
    // Les pièces se touchent : la corde entre deux sommets voisins fixe leur taille, sinon le
    // « tout » n'est qu'un anneau de cailloux épars (essai du 19/09).
    const taille = (2 * rayon * Math.sin(Math.PI / combien)) * 1.55;
    morceaux.push(
      <Node ref={ref} opacity={0}>
        <Line points={blob(taille * 0.5, graine + i * 13, 8)} closed
              fill={melanger(couleur, C.bg, 0.55)} stroke={couleur} lineWidth={7}
              lineJoin={'round'} />
      </Node>,
    );
  }

  // Liens qui se tissent entre les pièces une fois posées : c'est ce qui fait « un tout ».
  const liens: any[] = [];
  const liensRefs: any[] = [];
  for (let i = 0; i < combien; i++) {
    const ref = createRef<Line>();
    liensRefs.push(ref);
    liens.push(<Line ref={ref} points={[cibles[i], cibles[(i + 1) % combien]]} stroke={C.accent}
                     lineWidth={4} opacity={0.6} end={0} />);
  }

  cam().add(
    <Node ref={groupe}>
      {liens}
      <Circle ref={coeur} size={0} fill={melanger(C.accent, C.bg, 0.55)} stroke={C.highlight}
              lineWidth={6} opacity={0} />
      {morceaux}
    </Node>,
  );

  // Annotations : une par pièce nommée, posées vers l'extérieur.
  const notes = pieces.slice(0, 3).map((texte, i) => {
    const c = cibles[i];
    const aDroite = c[0] >= 0;
    const vers: [number, number] = [aDroite ? UX : -UX, -200 + i * 175];
    return annotation(c, vers, texte, couleurs[i % couleurs.length]);
  });
  notes.forEach(n => cam().add(n.noeud));

  const pas = Math.min(0.4, (duree * 0.45) / combien);
  for (let i = 0; i < combien; i++) {
    const depart: [number, number] = [
      (r() > 0.5 ? 1 : -1) * (L * 0.62 + r() * 200),
      (r() - 0.5) * H * 1.2,
    ];
    taches.push(delay(0.12 + i * pas, (function* () {
      refs[i]().position(depart).rotation((r() - 0.5) * 220).scale(0.5);
      yield* all(
        refs[i]().opacity(1, 0.18),
        refs[i]().position(cibles[i], 0.55, easeOutBack),
        refs[i]().rotation(0, 0.55, easeOutCubic),
        refs[i]().scale(1, 0.55, easeOutBack),
      );
      yield* refs[i]().scale(0.94, 0.09);
      yield* refs[i]().scale(1, 0.12, easeOutBack);
    })()));
    taches.push(delay(0.5 + i * pas, liensRefs[i]().end(1, 0.35, easeOutCubic)));
  }

  const tVerrou = 0.2 + combien * pas + 0.5;
  taches.push(delay(tVerrou, (function* () {
    coeur().opacity(1);
    yield* coeur().size(rayon * 1.16, 0.45, easeOutBack);
    yield* all(groupe().scale(1.06, 0.14), coeur().stroke(C.text, 0.14));
    yield* all(groupe().scale(1, 0.22), coeur().stroke(C.highlight, 0.3));
  })()));
  // Rotation continue de l'ensemble : l'objet vit pendant tout le reste du plan.
  taches.push(delay(tVerrou, groupe().rotation(22, Math.max(0.6, duree - tVerrou), linear)));
  notes.forEach((n, i) => taches.push(delay(tVerrou + 0.25 + i * 0.35, n.jouer())));

  // Dislocation dans la dernière seconde : le plan se termine sur une transformation, pas sur un arrêt.
  if (duree > 3.2) {
    taches.push(delay(duree - 0.75, (function* () {
      yield* all(...refs.map((ref, i) => all(
        ref().position([cibles[i][0] * 2.6, cibles[i][1] * 2.6], 0.7, easeInCubic),
        ref().opacity(0, 0.7),
        ref().rotation((r() - 0.5) * 180, 0.7),
      )), ...liensRefs.map(ref => ref().start(1, 0.5, easeInCubic)),
      coeur().size(0, 0.5, easeInCubic), coeur().opacity(0, 0.5));
    })()));
  }

  if (props.heading) {
    const titre = createRef<Txt>();
    const bloc = createRef<Node>();
    view.add(
      <Node ref={bloc} y={H / 2 - 190} opacity={0}>
        <Txt ref={titre} text={String(props.heading).toUpperCase()}
             fontFamily={C.font_title.family} fontWeight={C.font_title.weight}
             fontSize={taillePourTenir(String(props.heading), UX * 1.6, 64, 30)} fill={C.text}
             width={UX * 1.7} textWrap textAlign={'center'} />
      </Node>,
    );
    taches.push(delay(tVerrou, bloc().opacity(1, 0.35)));
  }

  surcouches(view, props);
  return taches;
}
