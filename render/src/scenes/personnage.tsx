/**
 * MARCHE — un personnage traverse le cadre, un décor défile derrière lui, il s'arrête devant
 * quelque chose et réagit.
 *
 * Cycle de marche latéral relevé sur la chaîne de référence : quatre membres en polylignes et un
 * fond qui défile à trois vitesses. C'est le plan qui donne le sentiment d'un **monde**, et pas
 * d'une suite de compositions.
 */
import {Txt, Node, Line, Circle, Rect} from '@revideo/2d';
import {all, createRef, delay, easeOutCubic, easeInOutCubic, easeOutBack, linear} from '@revideo/core';
import {C, L, H, UX, melanger} from '../charte';
import {alea, socle, surcouches, ajuster} from '../commun';
import {etre, astre, lignesDeVitesse} from '../figures';
import {marcher, cligner, respirer, regarder, sursaut, expression} from '../jeu';

export function personnageScene(view: any, props: any, duree: number) {
  const {cam, taches, graine} = socle(view, props, duree);
  const r = alea(graine * 211);

  const hauteur = 470;
  const heros = etre(hauteur, C.highlight, graine, 'rond');
  const sujet = astre(160, C.accent, graine + 9);
  const vitesse = lignesDeVitesse(320, C.text, 12);

  const sol = createRef<Line>();
  const decor = createRef<Node>();
  const groupe = createRef<Node>();
  const sujetRef = createRef<Node>();
  const bulle = createRef<Node>();
  const motBulle = createRef<Txt>();
  const vRef = createRef<Node>();
  const ySol = 300;

  // Le décor : des silhouettes de relief qui défilent, deux plans à deux vitesses.
  const reliefs: any[] = [];
  for (let couche = 0; couche < 2; couche++) {
    const formes: any[] = [];
    for (let i = 0; i < 7; i++) {
      const l = 260 + r() * 340;
      const h = (90 + r() * 200) * (couche === 0 ? 1.4 : 0.8);
      // Du relief, pas du mobilier : des buttes basses et sombres, très peu contrastées.
      formes.push(<Rect x={-L + i * 520 + r() * 120} y={ySol - h / 2 + 10} width={l * 1.5}
                        height={h * 0.62} radius={[h * 0.55, h * 0.55, 0, 0]}
                        fill={melanger(C.bg, couche ? C.accent : C.text, couche ? 0.13 : 0.07)} />);
    }
    reliefs.push(<Node>{formes}</Node>);
  }

  cam().add(
    <Node>
      <Node ref={decor}>{reliefs[0]}</Node>
      <Node>{reliefs[1]}</Node>
      <Line ref={sol} points={[[-UX * 1.6, ySol], [UX * 1.6, ySol]]}
            stroke={melanger(C.bg, C.text, 0.42)} lineWidth={7} end={0} lineCap={'round'} />
      <Node ref={sujetRef} x={430} y={ySol - 260} scale={0}>{sujet.noeud}</Node>
      <Node ref={groupe} x={-L * 0.6} y={ySol - hauteur * 0.58}>
        <Node ref={vRef} y={-hauteur * 0.1}>{vitesse.noeud}</Node>
        {heros.noeud}
      </Node>
      <Node ref={bulle} x={-100} y={ySol - hauteur - 190} opacity={0} scale={0.6}>
        <Circle width={430} height={180} fill={C.text} />
        <Circle x={-140} y={104} size={52} fill={C.text} />
        <Circle x={-190} y={142} size={24} fill={C.text} />
        <Txt ref={motBulle} text={String(props.label ?? '!').toUpperCase()}
             fontFamily={C.font_body.family} fontWeight={800} fontSize={50} fill={C.bg}
             width={350} textWrap textAlign={'center'} />
      </Node>
    </Node>,
  );
  ajuster(motBulle, 350, 140, 24);

  const tMarche = Math.min(2.2, Math.max(1.1, duree * 0.34));
  taches.push(sol().end(1, 0.5, easeOutCubic));
  taches.push(delay(0.15, groupe().x(-280, tMarche, easeInOutCubic)));
  taches.push(delay(0.15, marcher(heros, tMarche, 1)));
  // Le décor défile en sens inverse : c'est lui qui vend le déplacement, pas les jambes.
  taches.push(delay(0.15, decor().x(-460, tMarche + 0.6, easeInOutCubic)));
  taches.push(cligner(heros.face, graine, duree));

  // Il arrive, la chose apparaît, il sursaute.
  const tSujet = 0.15 + tMarche;
  taches.push(delay(tSujet, sujetRef().scale(1, 0.45, easeOutBack)));
  taches.push(delay(tSujet + 0.08, (function* () {
    vitesse.refs.forEach(ref => ref().opacity(0.85));
    yield* all(
      expression(heros.face, 'surprise', hauteur * 0.30 * 0.26),
      regarder(heros.face, 700, -160, 0.16),
      sursaut(heros.corps, 1),
      groupe().x(-340, 0.18, easeOutCubic),
      ...vitesse.refs.map(ref => all(ref().scale(1.5, 0.4, easeOutCubic), ref().opacity(0, 0.4))),
    );
    vitesse.refs.forEach(ref => ref().scale(1));
    yield* groupe().x(-300, 0.3, easeOutCubic);
  })()));

  // Il désigne, la bulle sort.
  const tGeste = tSujet + 0.55;
  taches.push(delay(tGeste, (function* () {
    yield* all(
      heros.brasD().points([[heros.rCorps * 0.78, -heros.rCorps * 0.05],
                            [heros.rCorps * 1.35, -heros.rCorps * 0.6]], 0.28, easeOutBack),
      heros.gantD().position([heros.rCorps * 1.35, -heros.rCorps * 0.6], 0.28, easeOutBack),
    );
    yield* all(bulle().opacity(1, 0.2), bulle().scale(1, 0.3, easeOutBack));
    yield* all(sujetRef().scale(1.14, 0.22, easeOutBack), sujet.anneau().lineWidth(28, 0.22));
    yield* all(sujetRef().scale(1, 0.28), sujet.anneau().lineWidth(15, 0.28));
  })()));

  taches.push(delay(tSujet, sujetRef().rotation(26, Math.max(1, duree - tSujet), linear)));
  taches.push(delay(tGeste + 0.5, respirer(heros.buste, Math.max(0.6, duree - tGeste - 0.5), 0.03)));

  surcouches(view, props);
  return taches;
}
