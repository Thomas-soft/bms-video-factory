/**
 * ÉCHELLE — la caméra recule et découvre que l'objet regardé est minuscule à côté d'un autre.
 *
 * Le dispositif le plus payant d'une chaîne de vulgarisation : il ne dit pas « c'est grand »,
 * il le montre en une seule prise. Le rapport vient du script (`props.ratio`), les deux noms
 * aussi ; tout le reste est générique.
 */
import {Txt, Node, Line, Circle} from '@revideo/2d';
import {all, createRef, delay, tween, easeOutCubic, easeInOutCubic, linear} from '@revideo/core';
import {C, L, H, UX} from '../charte';
import {socle, surcouches, taillePourTenir, ajuster} from '../commun';
import {astre} from '../figures';

export function echelle(view: any, props: any, duree: number) {
  const {cam, taches, graine} = socle(view, props, duree);

  const petitNom = String(props.small ?? props.label ?? 'ici');
  const grandNom = String(props.big ?? props.heading ?? 'là');
  // **Le chiffre affiché est celui du script, jamais un chiffre borné.** Seul le *dessin* est
  // borné : au-delà d'un rapport de 400 en surface, le petit objet ne ferait plus un pixel. Au
  // premier essai du 19/09, un rapport de 700 s'affichait « × 400 » — c'était une affirmation
  // fausse à l'écran, pas un compromis de mise en page.
  const rapport = Math.max(1, Number(props.ratio ?? 40));
  const rapportDessin = Math.min(400, rapport);
  const rGrand = 380;
  const rPetit = Math.max(6, rGrand / Math.sqrt(rapportDessin));

  const scene = createRef<Node>();
  const grandGroupe = createRef<Node>();
  const petit = astre(rPetit, C.highlight, graine, false);
  const grand = astre(rGrand, C.accent, graine + 5);
  const cerne = createRef<Circle>();
  const lienP = createRef<Line>();
  const nomP = createRef<Txt>();
  const nomG = createRef<Txt>();
  const facteur = createRef<Txt>();

  const xPetit = -L * 0.26;
  const xGrand = L * 0.16;

  cam().add(
    <Node ref={scene}>
      <Node ref={grandGroupe} x={xGrand} opacity={0}>{grand.noeud}</Node>
      <Node x={xPetit}>
        {petit.noeud}
        {/* Le cerne est dessiné dans le repère du petit objet : à fort zoom de départ, un
            pointillé de 14 px devient une barre de 300 px. Il est donc divisé par le zoom. */}
        <Circle ref={cerne} size={rPetit * 2 + 44} stroke={C.highlight}
                lineWidth={4 / Math.max(1, Math.min(26, 320 / Math.max(6, rPetit)))}
                lineDash={[14 / Math.max(1, Math.min(26, 320 / Math.max(6, rPetit))),
                           10 / Math.max(1, Math.min(26, 320 / Math.max(6, rPetit)))]}
                opacity={0} />
      </Node>
      <Line ref={lienP} points={[[xPetit, rPetit + 34], [xPetit, rPetit + 108]]}
            stroke={C.highlight} lineWidth={4} end={0} />
      <Txt ref={nomP} x={xPetit} y={rPetit + 150} text={petitNom.toUpperCase()}
           fontFamily={C.font_body.family} fontWeight={700} fontSize={40} fill={C.highlight}
           letterSpacing={2} opacity={0} />
      <Txt ref={nomG} x={xGrand} y={rGrand + 74} text={grandNom.toUpperCase()}
           fontFamily={C.font_title.family} fontWeight={C.font_title.weight} fontSize={62}
           fill={C.text} opacity={0} />
    </Node>,
  );
  view.add(
    <Node y={-H / 2 + 190}>
      <Txt ref={facteur} text={''} fontFamily={C.font_title.family} fontWeight={800}
           fontSize={150} fill={C.highlight} opacity={0} />
    </Node>,
  );
  ajuster(nomG, UX * 1.2, 120, 30);

  // 1. On commence collé au petit objet : il remplit le cadre, on ne sait pas encore où il est.
  const zoomDepart = Math.min(26, 320 / Math.max(6, rPetit));
  const tRecul = Math.min(2.4, Math.max(1.1, duree * 0.42));
  scene().scale(zoomDepart).position([-xPetit * zoomDepart, 0]);
  grandGroupe().opacity(0);

  taches.push((function* () {
    yield* all(cerne().opacity(0.9, 0.3), lienP().end(1, 0.3, easeOutCubic));
    yield* nomP().opacity(1, 0.25);
  })());

  // 2. Le recul. C'est le plan.
  taches.push(delay(Math.min(1.0, duree * 0.2), (function* () {
    yield* all(
      scene().scale(1, tRecul, easeInOutCubic),
      scene().position([0, 0], tRecul, easeInOutCubic),
      delay(tRecul * 0.35, grandGroupe().opacity(1, tRecul * 0.5)),
      delay(tRecul * 0.55, nomG().opacity(1, 0.4)),
    );
  })()));

  // 3. Le facteur monte pendant le recul : le chiffre est le propos, pas une légende.
  const tFacteur = Math.min(1.0, duree * 0.2) + tRecul * 0.3;
  taches.push(delay(tFacteur, (function* () {
    facteur().opacity(1);
    yield* tween(Math.max(0.6, tRecul * 0.7), v => {
      facteur().text(`× ${Math.round(rapport * easeOutCubic(v)).toLocaleString('en-US')}`);
    }, () => facteur().text(`× ${Math.round(rapport).toLocaleString('en-US')}`));
    yield* all(facteur().scale(1.12, 0.14), facteur().fill(C.text, 0.14));
    yield* all(facteur().scale(1, 0.2), facteur().fill(C.highlight, 0.3));
  })()));

  // 4. Le plan ne s'arrête pas : tout respire lentement jusqu'à la fin.
  taches.push(delay(tFacteur, all(
    grand.anneau().lineWidth(52, Math.max(0.8, duree - tFacteur), linear),
    scene().rotation(3, Math.max(0.8, duree - tFacteur), linear),
  )));

  surcouches(view, props);
  return taches;
}
