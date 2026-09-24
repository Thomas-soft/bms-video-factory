/**
 * Traitement A — typographie cinétique. DEUXIÈME VERSION (16/09/2026).
 *
 * La première répétait un seul dispositif vingt fois : un bloc de mots centré, même
 * taille, même entrée, même sortie, sur le même fond. Verdict de Thomas : « très nul,
 * non professionnel, ennuyant visuellement ». Il avait raison, et la cause était
 * identifiable : aucun contraste d'échelle, aucune composition hors-centre, aucune
 * rupture de couleur, aucun mouvement de caméra, une seule sorte de transition.
 *
 * Cette version est découpée en HUIT PLANS typographiques, chacun avec son parti :
 * sa composition, son fond, son échelle, sa transition d'entrée. Rapport d'échelle
 * de 1 à 11 (40 px à 440 px). Trois fonds pleins de couleurs différentes. Caméra
 * mobile sur les huit plans. Zéro image.
 */
import {
  makeProject, all, delay, chain, createRef, waitFor,
  easeOutCubic, easeInCubic, easeInOutCubic, easeOutBack, easeOutExpo, easeInExpo, linear,
} from '@revideo/core';
import {Rect, Txt, Circle, Line, Node, makeScene2D} from '@revideo/2d';
import './styles.css';
import {BG, TEXTE, ACCENT, HIGHLIGHT, POLICE, L, H, FIN} from './charte';

await document.fonts.load('600 100px "InterBMS"');
await document.fonts.load('400 100px "InterBMS"');

/** Mot masqué par un volet : il monte depuis sous la ligne. Le clip est vertical,
 *  donc aucune largeur n'a besoin d'être estimée. */
function volet(refRect: any, refTxt: any, texte: string, taille: number, couleur: string,
               x: number, y: number, ancrage: -1 | 0 | 1 = 0, poids = 600, etirement = 1) {
  return (
    <Rect ref={refRect} clip width={2100} height={taille * 1.30} x={x} y={y}>
      <Txt ref={refTxt} text={texte} fontFamily={POLICE} fontWeight={poids}
           fontSize={taille} fill={couleur} y={taille * 1.15}
           x={ancrage === -1 ? -870 : ancrage === 1 ? 870 : 0}
           offset={[ancrage, 0]} scale={[etirement, 1]} />
    </Rect>
  );
}

const scene = makeScene2D('motionA', function* (view) {
  view.fill(BG);

  const cam = createRef<Node>();
  const flash = createRef<Rect>();
  const bandes = [createRef<Rect>(), createRef<Rect>(), createRef<Rect>(),
                  createRef<Rect>(), createRef<Rect>()];

  // ---- références par plan ----
  const P: any[] = [];
  for (let i = 0; i < 8; i++) P.push(createRef<Node>());

  // P1
  const p1r = [0, 1, 2, 3, 4].map(() => createRef<Rect>());
  const p1t = [0, 1, 2, 3, 4].map(() => createRef<Txt>());
  const p1f = createRef<Line>();
  const p1n = createRef<Txt>();
  const p1q = createRef<Txt>();
  // P2
  const p2sucreR = createRef<Rect>(); const p2sucre = createRef<Txt>();
  const p2bloc = createRef<Rect>();
  const p2est = createRef<Txt>();
  const p2code = createRef<Txt>();
  const p2bas = [0, 1, 2].map(() => createRef<Txt>());
  const p2bits: any[] = []; const p2bitsR: any[] = [];
  for (let c = 0; c < 11; c++) {
    const r = createRef<Node>(); p2bitsR.push(r);
    const col: any[] = [];
    for (let k = 0; k < 8; k++)
      col.push(<Txt text={Math.random() > 0.5 ? '1' : '0'} fontFamily={POLICE} fontWeight={400}
                    fontSize={34} fill={HIGHLIGHT} y={k * 70 - 245} opacity={0.3 + (k % 3) * 0.25} />);
    p2bits.push(<Node ref={r} x={-960 + c * 192} opacity={0}>{col}</Node>);
  }
  // P3
  const p3r = [0, 1, 2, 3].map(() => createRef<Rect>());
  const p3t = [0, 1, 2, 3].map(() => createRef<Txt>());
  const p3fil = [0, 1, 2, 3].map(() => createRef<Line>());
  const p3d1 = createRef<Txt>(); const p3d2 = createRef<Txt>();
  const p3forme = createRef<Line>();
  const p3n = createRef<Txt>();
  // P4
  const p4fond = createRef<Rect>();
  const p4L = 'SACCHAROSE'.split('').map(() => createRef<Rect>());
  const p4Lt = 'SACCHAROSE'.split('').map(() => createRef<Txt>());
  const p4haut = [0, 1, 2].map(() => createRef<Txt>());
  const p4cris = createRef<Txt>();
  const p4los: any[] = []; const p4losR: any[] = [];
  for (let i = 0; i < 14; i++) {
    const r = createRef<Rect>(); p4losR.push(r);
    p4los.push(<Rect ref={r} width={26} height={26} rotation={45} stroke={BG} lineWidth={3}
                     x={-880 + (i % 7) * 293} y={i < 7 ? -430 : 430} opacity={0} />);
  }
  // P5
  const p5fond = createRef<Rect>();
  const p5haut = [0, 1, 2, 3, 4].map(() => createRef<Txt>());
  const p5aR = createRef<Rect>(); const p5a = createRef<Txt>();
  const p5iR = createRef<Rect>(); const p5i = createRef<Txt>();
  const p5biff = createRef<Line>();
  // P6
  const p6R = [0, 1, 2].map(() => createRef<Rect>());
  const p6t = [0, 1, 2].map(() => createRef<Txt>());
  const p6pile = createRef<Node>();
  const p6barre = createRef<Rect>();
  const p6droite = [0, 1, 2].map(() => createRef<Txt>());
  const p6mask = createRef<Rect>();
  const p6prec = createRef<Txt>();
  const p6n = createRef<Txt>();
  // P7
  const p7q = createRef<Txt>();
  const p7regR = createRef<Rect>(); const p7reg = createRef<Txt>();
  const p7cacR = createRef<Rect>(); const p7cac = createRef<Txt>();
  const p7voile = createRef<Rect>();
  const p7mal = createRef<Txt>();
  const p7pet = createRef<Txt>();
  // P8
  const p8ins = createRef<Txt>();
  const p8insR = createRef<Rect>();
  const p8sous = createRef<Txt>();
  const p8tiers = [createRef<Rect>(), createRef<Rect>(), createRef<Rect>()];
  const p8mots = [createRef<Txt>(), createRef<Txt>(), createRef<Txt>()];
  const p8num = [createRef<Txt>(), createRef<Txt>(), createRef<Txt>()];
  const TIERS = [
    {c: ACCENT, t: TEXTE, m: 'GLUCIDES', n: '01'},
    {c: HIGHLIGHT, t: BG, m: 'LIPIDES', n: '02'},
    {c: BG, t: TEXTE, m: 'PROTÉINES', n: '03'},
  ];

  yield view.add(
    <>
      <Node ref={cam}>

        {/* ---------- P1 : aplomb, aligné à gauche, bas de cadre ---------- */}
        <Node ref={P[0]} opacity={0}>
          <Line ref={p1f} points={[[-880, -380], [880, -380]]} stroke={ACCENT} lineWidth={5} end={0} />
          <Txt ref={p1n} x={840} y={-440} text={'01'} fontFamily={POLICE} fontWeight={600}
               fontSize={40} fill={ACCENT} opacity={0} />
          {volet(p1r[0], p1t[0], 'ET SI', 190, TEXTE, 0, -120, -1)}
          {volet(p1r[1], p1t[1], 'JE VOUS', 190, TEXTE, 0, 70, -1)}
          {volet(p1r[2], p1t[2], 'DISAIS', 250, HIGHLIGHT, 0, 290, -1)}
          <Txt ref={p1q} x={-880} y={430} offset={[-1, 0]} text={'QUE LE…'} fontFamily={POLICE}
               fontWeight={400} fontSize={52} fill={ACCENT} opacity={0} />
        </Node>

        {/* ---------- P2 : le mot géant, contraste 1:11 ---------- */}
        <Node ref={P[1]} opacity={0}>
          <Node>{p2bits}</Node>
          <Rect ref={p2bloc} width={0} height={330} fill={ACCENT} y={-90} offset={[-1, 0]} x={-960} />
          {volet(p2sucreR, p2sucre, 'SUCRE', 440, TEXTE, 0, -90, 0)}
          <Txt ref={p2est} x={880} y={170} offset={[1, 0]} text={'EST UN'} fontFamily={POLICE}
               fontWeight={400} fontSize={56} fill={HIGHLIGHT} opacity={0} />
          <Txt ref={p2code} y={190} text={'CODE'} fontFamily={POLICE} fontWeight={600}
               fontSize={300} fill={'#00000000'} stroke={HIGHLIGHT} lineWidth={4} opacity={0} />
          {['QU\'ON', 'IGNORE', 'TOUS QUOTIDIENNEMENT'].map((m, i) => (
            <Txt ref={p2bas[i]} x={-880 + i * 300} y={430} offset={[-1, 0]} text={m}
                 fontFamily={POLICE} fontWeight={400} fontSize={40} fill={TEXTE} opacity={0} />
          ))}
        </Node>

        {/* ---------- P3 : colonne à gauche, contrepoint à droite ---------- */}
        <Node ref={P[2]} opacity={0}>
          <Line ref={p3forme} points={[[620, 520], [620, 120], [1020, 520]]} closed
                stroke={ACCENT} lineWidth={6} end={0} />
          <Txt ref={p3n} x={840} y={-440} text={'02'} fontFamily={POLICE} fontWeight={600}
               fontSize={40} fill={ACCENT} opacity={0} />
          {[0, 1, 2, 3].map(i => (
            <Line ref={p3fil[i]} points={[[-870, -240 + i * 140], [-560, -240 + i * 140]]}
                  stroke={ACCENT} lineWidth={3} end={0} />
          ))}
          {['LE', 'SUCRE', 'DE', 'TABLE'].map((m, i) => (
            volet(p3r[i], p3t[i], m, i === 1 ? 130 : 78, i === 1 ? HIGHLIGHT : TEXTE,
                  0, -300 + i * 140, -1)
          ))}
          <Txt ref={p3d1} x={880} y={-120} offset={[1, 0]} text={'EST'} fontFamily={POLICE}
               fontWeight={400} fontSize={64} fill={TEXTE} opacity={0} />
          <Txt ref={p3d2} x={880} y={-20} offset={[1, 0]} text={'CHIMIQUEMENT FORMÉ'}
               fontFamily={POLICE} fontWeight={600} fontSize={92} fill={TEXTE} opacity={0} />
        </Node>

        {/* ---------- P4 : fond plein accent, lettre à lettre ---------- */}
        <Node ref={P[3]} opacity={0}>
          <Rect ref={p4fond} width={2600} height={1500} fill={ACCENT} />
          {p4los}
          {['PRESQUE', 'EXCLUSIVEMENT', 'DE'].map((m, i) => (
            <Txt ref={p4haut[i]} x={[-870, -640, -140][i]} y={-340} offset={[-1, 0]} text={m}
                 fontFamily={POLICE} fontWeight={400} fontSize={46} fill={HIGHLIGHT} opacity={0} />
          ))}
          {'SACCHAROSE'.split('').map((c, i) => (
            volet(p4L[i], p4Lt[i], c, 190, BG, -756 + i * 168, -60, 0)
          ))}
          <Txt ref={p4cris} y={230} text={'CRISTALLISÉ'} fontFamily={POLICE} fontWeight={600}
               fontSize={200} fill={'#00000000'} stroke={BG} lineWidth={4} opacity={0} />
        </Node>

        {/* ---------- P5 : inversion, fond highlight, texte sombre ---------- */}
        <Node ref={P[4]} opacity={0}>
          <Rect ref={p5fond} width={2600} height={1500} fill={HIGHLIGHT} />
          {['MAIS', 'CE', 'N\'EST', 'PAS', 'JUSTE UN'].map((m, i) => (
            <Txt ref={p5haut[i]} x={-880 + i * 210} y={-380} offset={[-1, 0]} text={m}
                 fontFamily={POLICE} fontWeight={400} fontSize={50} fill={BG} opacity={0} />
          ))}
          {volet(p5aR, p5a, 'ADDITIF', 230, BG, 0, -70, 0)}
          {volet(p5iR, p5i, 'INERTE', 320, BG, 0, 190, 0)}
          <Line ref={p5biff} points={[[-720, 240], [720, 150]]} stroke={BG} lineWidth={26} end={0} />
        </Node>

        {/* ---------- P6 : ascenseur, les mots poussent ---------- */}
        <Node ref={P[5]} opacity={0}>
          <Rect ref={p6barre} width={14} height={0} fill={ACCENT} x={-880} offset={[0, -1]} y={-420} />
          <Txt ref={p6n} x={840} y={-440} text={'03'} fontFamily={POLICE} fontWeight={600}
               fontSize={40} fill={ACCENT} opacity={0} />
          <Node ref={p6pile} y={180}>
            {['SUBSTRAT', 'MÉTABOLIQUE', 'COMPLEXE'].map((m, i) => (
              volet(p6R[i], p6t[i], m, 165, i === 2 ? HIGHLIGHT : TEXTE, 0, i * 175, -1)
            ))}
          </Node>
          {['NOTRE', 'CORPS', 'GÈRE'].map((m, i) => (
            <Txt ref={p6droite[i]} x={880} y={-390 + i * 70} offset={[1, 0]} text={m}
                 fontFamily={POLICE} fontWeight={400} fontSize={54} fill={ACCENT} opacity={0} />
          ))}
          <Rect ref={p6mask} clip width={0} height={200} x={-870} offset={[-1, 0]} y={400}>
            <Txt ref={p6prec} x={0} offset={[-1, 0]} text={'PRÉCISION BIOLOGIQUE'}
                 fontFamily={POLICE} fontWeight={600} fontSize={130} fill={HIGHLIGHT} />
          </Rect>
        </Node>

        {/* ---------- P7 : la question, un mot littéralement caché ---------- */}
        <Node ref={P[6]} opacity={0}>
          <Txt ref={p7q} text={'?'} fontFamily={POLICE} fontWeight={600} fontSize={1100}
               fill={'#00000000'} stroke={ACCENT} lineWidth={5} opacity={0} x={420} y={40} />
          {volet(p7regR, p7reg, 'RÉGULATION', 200, TEXTE, 0, -170, -1)}
          <Rect ref={p7cacR} clip width={2100} height={280} x={0} y={70}>
            <Txt ref={p7cac} x={-870} offset={[-1, 0]} text={'CACHÉE'} fontFamily={POLICE}
                 fontWeight={600} fontSize={230} fill={HIGHLIGHT} y={260} />
          </Rect>
          <Rect ref={p7voile} width={0} height={290} fill={BG} x={-880} offset={[-1, 0]} y={70}
                stroke={HIGHLIGHT} lineWidth={4} lineDash={[22, 16]} />
          <Txt ref={p7mal} x={-880} y={350} offset={[-1, 0]} text={'MALADES'} fontFamily={POLICE}
               fontWeight={600} fontSize={150} fill={HIGHLIGHT} opacity={0} />
          <Txt ref={p7pet} x={880} y={430} offset={[1, 0]} text={'SANS QU\'ON LE SACHE'}
               fontFamily={POLICE} fontWeight={400} fontSize={44} fill={ACCENT} opacity={0} />
        </Node>

        {/* ---------- P8 : générique en trois tiers ---------- */}
        <Node ref={P[7]} opacity={0}>
          {[0, 1, 2].map(i => (
            <Rect ref={p8tiers[i]} width={640} height={0} fill={TIERS[i].c} x={-640 + i * 640}
                  offset={[0, 1]} y={540} stroke={i === 2 ? TEXTE : undefined} lineWidth={i === 2 ? 5 : 0} />
          ))}
          {[0, 1, 2].map(i => (
            <Txt ref={p8num[i]} x={-640 + i * 640} y={-170} text={TIERS[i].n} fontFamily={POLICE}
                 fontWeight={600} fontSize={64} fill={TIERS[i].t} opacity={0} />
          ))}
          {[0, 1, 2].map(i => (
            <Txt ref={p8mots[i]} x={-640 + i * 640} y={220} text={TIERS[i].m} fontFamily={POLICE}
                 fontWeight={600} fontSize={74} fill={TIERS[i].t} opacity={0} rotation={-90} />
          ))}
          <Rect ref={p8insR} clip width={2100} height={300} y={-330}>
            <Txt ref={p8ins} text={'INSULINE'} fontFamily={POLICE} fontWeight={600} fontSize={250}
                 fill={TEXTE} y={330} />
          </Rect>
          <Txt ref={p8sous} y={-140} text={'HORMONE ANABOLIQUE'} fontFamily={POLICE}
               fontWeight={400} fontSize={50} fill={ACCENT} opacity={0} />
        </Node>
      </Node>

      {/* ---------- transitions, au-dessus de la caméra ---------- */}
      {[0, 1, 2, 3, 4].map(i => (
        <Rect ref={bandes[i]} width={2100} height={0} fill={i % 2 ? HIGHLIGHT : ACCENT}
              y={-432 + i * 216} />
      ))}
      <Rect ref={flash} width={2600} height={1500} fill={TEXTE} opacity={0} />
    </>,
  );

  // ================= planification absolue =================
  const T: any[] = [];
  const t0 = (t: number, tache: any) => T.push(delay(Math.max(0, t), tache));
  /** Passe du plan i au plan j : les cinq bandes se ferment puis se rouvrent. */
  function* volets(i: number, j: number) {
    yield* all(...bandes.map((b, k) => delay(k * 0.03, b().height(220, 0.16, easeInExpo))));
    P[i]().opacity(0);
    P[j]().opacity(1);
    yield* all(...bandes.map((b, k) => delay(k * 0.03, b().height(0, 0.18, easeOutExpo))));
  }

  // caméra : elle ne s'arrête jamais complètement
  T.push(chain(
    all(cam().scale(1.03, 4.9, linear), cam().position([-24, 10], 4.9, linear)),
    all(cam().scale(1, 0.01), cam().position([26, -12], 0.01)),
    all(cam().scale(1.025, 6.1, linear), cam().position([-20, 8], 6.1, linear)),
    all(cam().scale(1, 0.01), cam().position([0, 0], 0.01)),
    all(cam().scale(1.03, 5.4, linear), cam().position([18, -10], 5.4, linear)),
    all(cam().scale(1, 0.01), cam().position([-22, 0], 0.01)),
    all(cam().scale(1.03, 6.1, linear), cam().position([16, 12], 6.1, linear)),
    all(cam().scale(1, 0.01), cam().position([0, 0], 0.01)),
    all(cam().scale(1.03, 9.4, linear), cam().position([0, -14], 9.4, linear)),
  ));

  // ---------------- P1 : 0,00 → 1,84 ----------------
  t0(0.00, P[0]().opacity(1, 0.01));
  t0(0.05, p1f().end(1, 0.7, easeOutCubic));
  t0(0.30, p1n().opacity(1, 0.3));
  t0(0.00, p1t[0]().y(0, 0.36, easeOutCubic));          // « Et si »
  t0(0.46, p1t[1]().y(0, 0.36, easeOutCubic));          // « je vous »
  t0(0.60, all(p1t[2]().y(0, 0.42, easeOutCubic),       // « disais »
               p1r[2]().x(60, 0.42, easeOutCubic)));
  t0(1.04, all(p1q().opacity(1, 0.25), p1q().x(-840, 0.35, easeOutCubic)));

  // ---------------- P2 : 1,84 → 4,90 — le mot géant ----------------
  t0(1.78, volets(0, 1));
  t0(1.84, all(p2bloc().width(L + 200, 0.34, easeOutExpo),
               p2sucre().y(0, 0.40, easeOutCubic)));
  t0(2.20, all(p2est().opacity(1, 0.2), p2est().x(840, 0.3, easeOutCubic)));
  t0(2.54, (function* () {                              // « code » : creux, il grandit
    p2code().opacity(0).scale(0.75);
    yield* all(p2code().opacity(1, 0.25), p2code().scale(1, 0.9, easeOutCubic));
    yield* p2code().scale(1.06, 1.6, linear);
  })());
  p2bitsR.forEach((r, i) => t0(2.54 + i * 0.035, (function* () {
    r().y(-300);
    yield* all(r().opacity(1, 0.2), r().y(180, 1.9, linear));
    yield* r().opacity(0, 0.35);
  })()));
  [2.80, 3.32, 3.68].forEach((t, i) => t0(t, all(
    p2bas[i]().opacity(1, 0.18), p2bas[i]().x(-880 + i * 300 + 16, 0.28, easeOutCubic))));
  t0(4.20, all(p2sucre().y(-260, 0.5, easeInCubic), p2bloc().width(0, 0.5, easeInCubic)));

  // ---------------- P3 : 5,10 → 8,08 — colonne ----------------
  t0(5.02, volets(1, 2));
  t0(5.10, p3n().opacity(1, 0.3));
  t0(5.10, p3forme().end(1, 1.1, easeOutCubic));
  [5.10, 5.60, 5.90, 6.08].forEach((t, i) => {   // colonne : un mot, un filet
    t0(t, all(p3t[i]().y(0, 0.34, easeOutCubic), p3fil[i]().end(1, 0.4, easeOutCubic)));
  });
  t0(6.34, all(p3d1().opacity(1, 0.2), p3d1().x(840, 0.3, easeOutCubic)));
  t0(6.60, all(p3d2().opacity(1, 0.22), p3d2().x(840, 0.34, easeOutCubic)));
  t0(7.24, p3d2().fill(HIGHLIGHT, 0.3));

  // ---------------- P4 : 8,08 → 11,00 — fond plein, lettre à lettre ----------------
  t0(8.02, (function* () {                              // zoom brutal, pas un fondu
    yield* all(P[2]().scale(7, 0.22, easeInExpo), P[2]().opacity(0, 0.22));
    P[2]().scale(1);
    P[3]().opacity(1).scale(0.4);
    yield* P[3]().scale(1, 0.30, easeOutExpo);
  })());
  [7.68, 8.08, 9.12].forEach((t, i) => t0(t, all(
    p4haut[i]().opacity(1, 0.2), p4haut[i]().x([-870, -640, -140][i] + 14, 0.3, easeOutCubic))));
  p4Lt.forEach((r, i) => t0(9.52 + i * 0.035, r().y(0, 0.34, easeOutBack)));
  p4losR.forEach((r, i) => t0(9.70 + i * 0.03, (function* () {
    yield* all(r().opacity(1, 0.25), r().rotation(225, 1.8, easeOutCubic));
  })()));
  t0(10.12, (function* () {
    p4cris().opacity(0).scale([0.6, 1]);
    yield* all(p4cris().opacity(1, 0.28), p4cris().scale([1, 1], 0.55, easeOutExpo));
  })());

  // ---------------- P5 : 11,20 → 13,52 — inversion de couleur ----------------
  t0(11.14, (function* () {                             // coupe franche au flash
    yield* flash().opacity(0.9, 0.05);
    P[3]().opacity(0);
    P[4]().opacity(1);
    yield* flash().opacity(0, 0.14);
  })());
  [11.20, 11.76, 11.96, 12.08, 12.20].forEach((t, i) => t0(t, all(
    p5haut[i]().opacity(1, 0.14), p5haut[i]().x(-880 + i * 210 + 12, 0.24, easeOutCubic))));
  t0(12.62, p5a().y(0, 0.34, easeOutCubic));
  t0(13.08, all(p5i().y(0, 0.34, easeOutCubic), p5i().scale([1.02, 1], 0.34)));
  t0(13.30, (function* () {                             // biffure + secousse
    yield* p5biff().end(1, 0.26, easeInCubic);
    yield* all(cam().position([14, -8], 0.05), cam().rotation(0.5, 0.05));
    yield* all(cam().position([0, 0], 0.09), cam().rotation(0, 0.09));
  })());

  // ---------------- P6 : 13,52 → 18,90 — ascenseur ----------------
  t0(13.86, volets(4, 5));
  t0(13.90, all(p6barre().height(860, 0.8, easeOutCubic), p6n().opacity(1, 0.3)));
  [14.34, 14.82, 15.40].forEach((t, i) => t0(t, all(
    p6t[i]().y(0, 0.32, easeOutCubic),
    p6pile().y(180 - i * 175, 0.42, easeOutCubic),   // la pile monte sous le mot neuf
  )));
  [16.44, 16.66, 16.94].forEach((t, i) => t0(t, all(
    p6droite[i]().opacity(1, 0.18), p6droite[i]().x(840, 0.28, easeOutCubic))));
  t0(17.62, all(p6mask().width(1740, 0.7, easeOutExpo),
                p6prec().x(-870, 0.7, easeOutExpo)));      // masque qui s'ouvre, texte immobile
  t0(18.10, p6prec().fill(TEXTE, 0.3));

  // ---------------- P7 : 19,40 → 23,72 — la question ----------------
  t0(19.34, volets(5, 6));
  t0(19.40, (function* () {
    yield* p7q().opacity(0.85, 0.5);
    yield* all(p7q().rotation(8, 3.6, easeInOutCubic), p7q().scale(1.12, 3.6, linear));
  })());
  t0(20.42, p7reg().y(0, 0.36, easeOutCubic));
  t0(20.94, p7cac().y(0, 0.34, easeOutCubic));
  t0(21.44, p7voile().width(1160, 0.42, easeOutExpo));   // « cachée » se fait cacher
  t0(22.10, (function* () {
    p7mal().opacity(0).scale(1.4);
    yield* all(p7mal().opacity(1, 0.16), p7mal().scale(1, 0.34, easeOutBack));
  })());
  t0(22.64, all(p7pet().opacity(1, 0.2), p7pet().x(840, 0.3, easeOutCubic)));

  // ---------------- P8 : 23,72 → 32,00 — générique ----------------
  t0(23.66, volets(6, 7));
  t0(23.72, p8ins().y(0, 0.42, easeOutExpo));
  t0(24.98, all(p8sous().opacity(1, 0.25), p8sous().y(-120, 0.35, easeOutCubic)));
  t0(26.44, (function* () {                              // l'écran se divise
    yield* all(p8insR().y(-410, 0.5, easeOutCubic), p8insR().scale(0.58, 0.5, easeOutCubic),
               p8sous().opacity(0, 0.3));
  })());
  [26.44, 26.92, 27.18].forEach((t, i) => t0(t, all(
    p8tiers[i]().height(880, 0.55, easeOutExpo), p8num[i]().opacity(1, 0.3))));
  [28.32, 29.62, 31.02].forEach((t, i) => t0(t, (function* () {
    p8mots[i]().opacity(0).y(430);
    yield* all(p8mots[i]().opacity(1, 0.2), p8mots[i]().y(220, 0.42, easeOutExpo));
  })()));
  t0(31.66, all(...p8tiers.map((r, i) => r().width(636, 0.3, easeOutCubic)),
                cam().scale(1.02, 0.34, easeOutCubic)));

  yield* all(waitFor(FIN), ...T);
});

export default makeProject({scenes: [scene]});
