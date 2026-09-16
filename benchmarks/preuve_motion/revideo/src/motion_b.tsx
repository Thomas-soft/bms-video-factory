/**
 * Traitement B — schéma animé.
 * Un objet du script (le saccharose, puis sa régulation par l'insuline) construit en
 * vecteur : il s'assemble, s'annote, se casse, circule et se transforme pendant que la
 * voix l'explique. Zéro image. Tous les repères temporels viennent de words.json.
 */
import {
  makeProject, all, delay, createRef, waitFor, createSignal,
  easeOutCubic, easeInCubic, easeInOutCubic, easeOutBack, linear,
} from '@revideo/core';
import {Rect, Txt, Circle, Line, Node, makeScene2D} from '@revideo/2d';
import './styles.css';
import {BG, TEXTE, ACCENT, HIGHLIGHT, POLICE, L, H, FIN} from './charte';

await document.fonts.load('600 100px "InterBMS"');
await document.fonts.load('400 100px "InterBMS"');

/** Sommets d'un polygone régulier à n côtés, rayon r, tourné de `rot` degrés. */
function poly(n: number, r: number, rot = 0): [number, number][] {
  const p: [number, number][] = [];
  for (let i = 0; i < n; i++) {
    const a = ((i / n) * 360 + rot) * (Math.PI / 180);
    p.push([Math.cos(a) * r, Math.sin(a) * r]);
  }
  return p;
}

const scene = makeScene2D('motionB', function* (view) {
  view.fill(BG);

  // ================= décor commun =================
  const grille = createRef<Node>();
  const balai = createRef<Rect>();
  const titre = createRef<Txt>();
  const soustitre = createRef<Txt>();

  const traits: any[] = [];
  for (let i = -8; i <= 8; i++) traits.push(<Line points={[[i * 130, -H], [i * 130, H]]} stroke={ACCENT} lineWidth={1} opacity={0.10} />);
  for (let j = -5; j <= 5; j++) traits.push(<Line points={[[-L, j * 130], [L, j * 130]]} stroke={ACCENT} lineWidth={1} opacity={0.10} />);

  // ================= G1 : le cristal =================
  const g1 = createRef<Node>();
  const cubeA = createRef<Line>();
  const cubeB = createRef<Line>();
  const cubeC = createRef<Line>();
  const bits: any[] = [];
  const bitsRefs: any[] = [];
  for (let c = 0; c < 9; c++) {
    const r = createRef<Node>();
    bitsRefs.push(r);
    const col: any[] = [];
    for (let k = 0; k < 7; k++) {
      col.push(<Txt text={Math.random() > 0.5 ? '1' : '0'} fontFamily={POLICE} fontWeight={400}
                    fontSize={38} fill={HIGHLIGHT} y={k * 62 - 190} opacity={0.35 + (k % 3) * 0.2} />);
    }
    bits.push(<Node ref={r} x={-500 + c * 125} opacity={0}>{col}</Node>);
  }

  // faces d'un cube isométrique
  const s = 190;
  const haut: [number, number][] = [[0, -s], [s * 0.86, -s * 0.5], [0, 0], [-s * 0.86, -s * 0.5]];
  const gauche: [number, number][] = [[-s * 0.86, -s * 0.5], [0, 0], [0, s], [-s * 0.86, s * 0.5]];
  const droite: [number, number][] = [[s * 0.86, -s * 0.5], [0, 0], [0, s], [s * 0.86, s * 0.5]];

  // ================= G2 : la molécule =================
  const g2 = createRef<Node>();
  const hexa = createRef<Line>();
  const penta = createRef<Line>();
  const pont = createRef<Line>();
  const hexaN = createRef<Node>();
  const pentaN = createRef<Node>();
  const accolade = createRef<Line>();
  const nomMol = createRef<Txt>();
  const lblGlu = createRef<Txt>();
  const lblFru = createRef<Txt>();
  const tampon = createRef<Node>();
  const tamponTxt = createRef<Txt>();
  const vaisseau = createRef<Line>();
  const billes: any[] = [];
  const billesRefs: any[] = [];
  for (let i = 0; i < 7; i++) {
    const r = createRef<Circle>();
    billesRefs.push(r);
    billes.push(<Circle ref={r} size={26} fill={i % 2 ? HIGHLIGHT : ACCENT} opacity={0} x={-560} y={210} />);
  }
  const cadran = createRef<Circle>();
  const aiguille = createRef<Line>();
  const courbe = createRef<Line>();
  const bande = createRef<Rect>();
  const voile = createRef<Rect>();
  const voileTxt = createRef<Txt>();

  const cheminVaisseau: [number, number][] = [
    [-560, 210], [-380, 250], [-180, 190], [40, 250], [250, 190], [430, 230],
  ];
  const ptsCourbe: [number, number][] = [
    [-150, 40], [-80, 10], [-10, -55], [60, -30], [130, 25], [200, 60], [270, 40],
  ];

  // ================= G3 : l'insuline =================
  const g3 = createRef<Node>();
  const recepteur = createRef<Rect>();
  const encoche = createRef<Line>();
  const hormone = createRef<Line>();
  const halo = createRef<Circle>();
  const branches = [createRef<Line>(), createRef<Line>(), createRef<Line>()];
  const etiqs = [createRef<Node>(), createRef<Node>(), createRef<Node>()];
  const icones = [createRef<Node>(), createRef<Node>(), createRef<Node>()];
  const NOMS = ['GLUCIDES', 'LIPIDES', 'PROTÉINES'];
  const YS = [-250, 0, 250];

  yield view.add(
    <>
      <Node ref={grille} opacity={0}>{traits}</Node>

      <Node ref={g1} opacity={0}>
        <Node x={-40}>
          <Line ref={cubeA} points={haut} closed stroke={ACCENT} lineWidth={7} fill={'#16323a'} end={0} />
          <Line ref={cubeB} points={gauche} closed stroke={ACCENT} lineWidth={7} fill={'#122a30'} end={0} />
          <Line ref={cubeC} points={droite} closed stroke={HIGHLIGHT} lineWidth={7} fill={'#1b2a26'} end={0} />
        </Node>
        <Node y={-30}>{bits}</Node>
      </Node>

      <Node ref={g2} opacity={0}>
        <Node y={-120}>
          <Line ref={pont} points={[[-118, 0], [118, 0]]} stroke={TEXTE} lineWidth={8} end={0} />
          <Node ref={hexaN} x={-250}>
            <Line ref={hexa} points={poly(6, 130)} closed stroke={ACCENT} lineWidth={9} fill={'#14343a'} end={0} />
          </Node>
          <Node ref={pentaN} x={250}>
            <Line ref={penta} points={poly(5, 120, -90)} closed stroke={HIGHLIGHT} lineWidth={9} fill={'#2e2a1a'} end={0} />
          </Node>
          <Txt ref={lblGlu} x={-250} y={200} text={''} fontFamily={POLICE} fontWeight={400}
               fontSize={40} fill={ACCENT} opacity={0} />
          <Txt ref={lblFru} x={250} y={200} text={''} fontFamily={POLICE} fontWeight={400}
               fontSize={40} fill={HIGHLIGHT} opacity={0} />
        </Node>
        <Line ref={accolade} points={[[-420, -350], [-420, -400], [420, -400], [420, -350]]}
              stroke={TEXTE} lineWidth={5} end={0} />
        <Txt ref={nomMol} y={-470} text={''} fontFamily={POLICE} fontWeight={600} fontSize={64}
             fill={TEXTE} opacity={0} />

        <Line ref={vaisseau} points={cheminVaisseau} stroke={ACCENT} lineWidth={34} end={0}
              opacity={0.45} radius={40} lineCap={'round'} />
        {billes}

        <Node x={470} y={215}>
          <Circle ref={cadran} size={230} stroke={TEXTE} lineWidth={9} startAngle={-200} endAngle={20}
                  closed={false} opacity={0} />
          <Line ref={aiguille} points={[[0, 0], [0, -88]]} stroke={HIGHLIGHT} lineWidth={9}
                rotation={-70} opacity={0} lineCap={'round'} />
          <Circle size={22} fill={TEXTE} opacity={0} />
        </Node>

        <Node x={-60} y={330}>
          <Rect ref={bande} width={460} height={70} fill={ACCENT} opacity={0} radius={6} y={10} />
          <Line ref={courbe} points={ptsCourbe} stroke={HIGHLIGHT} lineWidth={7} end={0} />
        </Node>

        <Rect ref={voile} width={640} height={300} x={430} y={215} fill={BG} stroke={HIGHLIGHT}
              lineWidth={5} lineDash={[18, 14]} opacity={0} radius={10} />
        <Txt ref={voileTxt} x={430} y={215} text={''} fontFamily={POLICE} fontWeight={600}
             fontSize={54} fill={HIGHLIGHT} opacity={0} />

        <Node ref={tampon} x={470} y={330} rotation={-9} opacity={0} scale={2.2}>
          <Rect width={470} height={116} stroke={HIGHLIGHT} lineWidth={7} radius={8} />
          <Txt ref={tamponTxt} text={''} fontFamily={POLICE} fontWeight={600} fontSize={56} fill={HIGHLIGHT} />
        </Node>
      </Node>

      <Node ref={g3} opacity={0}>
        <Node x={-430}>
          <Rect ref={recepteur} width={300} height={360} stroke={ACCENT} lineWidth={9} radius={16}
                fill={'#14343a'} scale={0} />
          <Line ref={encoche} points={[[-70, -180], [0, -84], [70, -180]]} stroke={BG} lineWidth={16} end={0} />
          <Circle ref={halo} size={420} stroke={HIGHLIGHT} lineWidth={6} opacity={0} />
        </Node>
        <Line ref={hormone} points={poly(6, 62, 30)} closed stroke={HIGHLIGHT} lineWidth={8}
              fill={'#2e2a1a'} x={-430} y={-330} opacity={0} />
        {[0, 1, 2].map(i => (
          <Line ref={branches[i]} points={[[-260, 0], [-60, 0], [60, YS[i]], [300, YS[i]]]}
                stroke={i === 0 ? ACCENT : i === 1 ? HIGHLIGHT : TEXTE} lineWidth={7} end={0} radius={30} />
        ))}
        {[0, 1, 2].map(i => (
          <Node ref={etiqs[i]} x={520} y={YS[i]} opacity={0}>
            <Rect width={330} height={88} stroke={i === 0 ? ACCENT : i === 1 ? HIGHLIGHT : TEXTE}
                  lineWidth={5} radius={10} />
            <Txt text={NOMS[i]} fontFamily={POLICE} fontWeight={600} fontSize={44} fill={TEXTE} />
          </Node>
        ))}
        <Node ref={icones[0]} x={790} y={YS[0]} opacity={0}>
          <Line points={poly(6, 44)} closed stroke={ACCENT} lineWidth={6} />
        </Node>
        <Node ref={icones[1]} x={790} y={YS[1]} opacity={0}>
          <Circle size={62} stroke={HIGHLIGHT} lineWidth={6} y={12} />
          <Line points={[[-26, -2], [0, -52], [26, -2]]} stroke={HIGHLIGHT} lineWidth={6} />
        </Node>
        <Node ref={icones[2]} x={790} y={YS[2]} opacity={0}>
          <Line points={[[-52, 0], [52, 0]]} stroke={TEXTE} lineWidth={6} />
          <Circle size={34} x={-52} stroke={TEXTE} lineWidth={6} />
          <Circle size={34} stroke={TEXTE} lineWidth={6} />
          <Circle size={34} x={52} stroke={TEXTE} lineWidth={6} />
        </Node>
      </Node>

      {/* titraille */}
      <Rect x={-770} y={-470} width={20} height={64} fill={HIGHLIGHT} />
      <Txt ref={titre} x={-716} y={-470} offset={[-1, 0]} text={''} fontFamily={POLICE}
           fontWeight={600} fontSize={40} fill={TEXTE} opacity={0} />
      <Txt ref={soustitre} x={-716} y={-412} offset={[-1, 0]} text={''} fontFamily={POLICE}
           fontWeight={400} fontSize={28} fill={ACCENT} opacity={0} />
      <Rect ref={balai} width={0} height={H} fill={ACCENT} opacity={0} />
    </>,
  );

  // ================= planification absolue =================
  const T: any[] = [];
  const pousse = (t: number, tache: any) => T.push(delay(Math.max(0, t), tache));

  function* balayage(couleur: string) {
    balai().fill(couleur).opacity(1).offset([-1, 0]).x(-960).width(0);
    yield* balai().width(L, 0.18, easeInCubic);
    balai().offset([1, 0]).x(960);
    yield* balai().width(0, 0.22, easeOutCubic);
    balai().opacity(0);
  }
  function* titrer(t1: string, t2: string) {
    yield* all(titre().opacity(0, 0.12), soustitre().opacity(0, 0.12));
    titre().text(t1); soustitre().text(t2);
    yield* all(titre().opacity(1, 0.3), soustitre().opacity(1, 0.3));
  }

  T.push(grille().opacity(1, 0.8));
  T.push(grille().position([-60, 40], FIN, linear));

  // ---- 0,0-5,1 : le cristal, puis le code ----
  pousse(0.15, g1().opacity(1, 0.3));
  pousse(0.25, titrer('SACCHAROSE', 'cristal — maille cubique'));
  pousse(0.3, cubeA().end(1, 0.7, easeOutCubic));
  pousse(0.8, cubeB().end(1, 0.7, easeOutCubic));
  pousse(1.3, cubeC().end(1, 0.7, easeOutCubic));
  pousse(1.84, (function* () {                      // « sucre »
    yield* all(g1().scale(1.08, 0.35, easeOutBack));
    yield* g1().scale(1, 0.4);
  })());
  bitsRefs.forEach((r, i) => {                      // « un code » : 2,54
    pousse(2.54 + i * 0.045, (function* () {
      r().y(-260);
      yield* all(r().opacity(1, 0.25), r().y(120, 2.2, linear));
      yield* r().opacity(0, 0.4);
    })());
  });
  pousse(2.54, titrer('UN CODE', 'lecture métabolique'));
  pousse(4.30, all(g1().opacity(0, 0.55), g1().scale(0.55, 0.7, easeInCubic)));

  // ---- 5,1-11,2 : la molécule s'assemble ----
  pousse(4.95, balayage(ACCENT));
  pousse(5.15, g2().opacity(1, 0.3));
  pousse(5.20, titrer('SACCHAROSE', 'C12H22O11 — dimère'));
  pousse(6.60, hexa().end(1, 1.1, easeInOutCubic));      // « chimiquement »
  pousse(7.24, penta().end(1, 1.1, easeInOutCubic));     // « formé »
  pousse(8.30, pont().end(1, 0.5, easeOutCubic));        // « exclusivement »
  pousse(9.52, (function* () {                          // « saccharose »
    yield* accolade().end(1, 0.55, easeOutCubic);
    nomMol().text('SACCHAROSE');
    yield* all(nomMol().opacity(1, 0.3), nomMol().y(-450, 0.4, easeOutCubic));
  })());
  pousse(10.12, (function* () {                         // « cristallisé »
    lblGlu().text('glucose'); lblFru().text('fructose');
    yield* all(lblGlu().opacity(1, 0.35), lblFru().opacity(1, 0.35),
               lblGlu().y(220, 0.4, easeOutCubic), lblFru().y(220, 0.4, easeOutCubic));
  })());

  // ---- 11,2-13,5 : « pas un additif inerte » ----
  pousse(12.62, (function* () {                         // « additif inerte »
    tamponTxt().text('PAS INERTE');
    yield* all(tampon().opacity(1, 0.15), tampon().scale(1, 0.35, easeOutCubic));
    yield* all(tampon().rotation(-6, 0.25), tampon().scale(1.04, 0.25));
  })());
  pousse(11.90, (function* () {
    for (let i = 0; i < 5; i++) {
      yield* all(hexaN().x(-256, 0.06), pentaN().x(256, 0.06));
      yield* all(hexaN().x(-244, 0.06), pentaN().x(244, 0.06));
    }
  })());

  // ---- 13,5-16,7 : la liaison casse, les sucres circulent ----
  pousse(13.52, titrer('SUBSTRAT MÉTABOLIQUE', 'hydrolyse de la liaison'));
  pousse(13.52, (function* () {                         // « C'est un substrat »
    yield* pont().start(0.5, 0.35, easeInCubic);
    yield* all(hexaN().x(-420, 0.8, easeOutCubic), pentaN().x(420, 0.8, easeOutCubic),
               lblGlu().x(-420, 0.8, easeOutCubic), lblFru().x(420, 0.8, easeOutCubic),
               pont().opacity(0, 0.4));
  })());
  pousse(14.34, all(tampon().opacity(0, 0.4), tampon().scale(0.8, 0.4)));
  pousse(14.34, (function* () {                         // « substrat » : tout remonte
    yield* all(hexaN().scale(0.55, 0.7, easeInOutCubic), pentaN().scale(0.55, 0.7, easeInOutCubic),
               accolade().opacity(0, 0.4), nomMol().opacity(0.22, 0.4),
               lblGlu().opacity(0.25, 0.4), lblFru().opacity(0.25, 0.4));
  })());
  pousse(14.82, vaisseau().end(1, 1.2, easeInOutCubic));
  billesRefs.forEach((r, i) => {
    pousse(15.3 + i * 0.22, (function* () {
      r().opacity(1).position([-560, 210]);
      yield* all(
        r().x(430, 1.9, easeInOutCubic),
        (function* () {                                  // suit la courbe du vaisseau
          yield* r().y(250, 0.5); yield* r().y(190, 0.5);
          yield* r().y(250, 0.5); yield* r().y(215, 0.4);
        })(),
      );
      yield* r().opacity(0, 0.25);
    })());
  });

  // ---- 16,7-19,4 : la régulation ----
  pousse(16.66, titrer('RÉGULATION', 'glycémie — bande cible'));
  pousse(16.66, all(cadran().opacity(1, 0.4), aiguille().opacity(1, 0.4)));
  pousse(17.00, aiguille().rotation(55, 1.3, easeInOutCubic));
  pousse(17.62, all(bande().opacity(0.30, 0.4), courbe().end(0.62, 1.6, linear)));
  pousse(18.60, aiguille().rotation(-20, 1.0, easeInOutCubic));

  // ---- 19,4-23,7 : « régulation cachée » ----
  pousse(20.42, (function* () {                         // « régulation cachée »
    voileTxt().text('?  CACHÉE');
    yield* all(voile().opacity(1, 0.35), voileTxt().opacity(1, 0.35));
  })());
  pousse(21.44, courbe().end(1, 1.4, linear));          // la courbe sort de la bande
  pousse(21.44, aiguille().rotation(80, 1.4, easeInOutCubic));
  pousse(22.10, (function* () {                         // « malades »
    yield* bande().fill(HIGHLIGHT, 0.3);
    yield* all(bande().opacity(0.5, 0.2), bande().opacity(0.2, 0.3));
  })());
  pousse(23.20, all(g2().opacity(0, 0.5), g2().scale(1.08, 0.6, easeInCubic)));

  // ---- 23,7-32,0 : l'insuline ----
  pousse(23.55, balayage(HIGHLIGHT));
  pousse(23.72, g3().opacity(1, 0.3));
  pousse(23.72, titrer('INSULINE', 'hormone anabolique — récepteur'));
  pousse(23.80, recepteur().scale(1, 0.5, easeOutBack));
  pousse(24.20, encoche().end(1, 0.35, easeOutCubic));
  pousse(24.46, (function* () {                         // « est une hormone » : l'hormone descend
    hormone().opacity(1);
    yield* hormone().y(-96, 0.85, easeInCubic);
    yield* all(hormone().scale(1.15, 0.12), halo().opacity(0.9).size(420, 0.01));
    yield* all(hormone().scale(1, 0.18), halo().size(640, 0.5, easeOutCubic), halo().opacity(0, 0.5));
  })());
  pousse(25.30, (function* () {                         // « anabolique »
    yield* all(recepteur().stroke(HIGHLIGHT, 0.4), recepteur().fill('#2e2a1a', 0.4));
  })());
  pousse(26.44, branches[0]().end(1, 0.9, easeOutCubic));   // « régule »
  pousse(26.80, branches[1]().end(1, 0.9, easeOutCubic));
  pousse(27.18, branches[2]().end(1, 0.9, easeOutCubic));   // « métabolisme »
  [28.32, 29.62, 31.02].forEach((t, i) => {                  // glucides / lipides / protéines
    pousse(t, (function* () {
      etiqs[i]().x(620);
      yield* all(etiqs[i]().opacity(1, 0.2), etiqs[i]().x(520, 0.35, easeOutCubic));
      yield* all(icones[i]().opacity(1, 0.25), icones[i]().scale(1.12, 0.25, easeOutBack));
      yield* icones[i]().scale(1, 0.2);
    })());
  });
  pousse(31.66, (function* () {
    yield* all(...icones.map(r => r().scale(1.1, 0.25, easeOutBack)),
               ...etiqs.map(r => r().scale(1.04, 0.25)));
  })());

  yield* all(waitFor(FIN), ...T);
});

export default makeProject({scenes: [scene]});
