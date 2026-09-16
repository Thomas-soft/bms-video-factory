/**
 * Traitement C — hybride. DEUXIÈME VERSION (16/09/2026).
 *
 * La première posait l'image en plein cadre, lui donnait 4 % de dérive et attendait,
 * pendant qu'un bandeau de sous-titres karaoké tenait lieu de mouvement. Verdict de
 * Thomas : « très nul, non professionnel, ennuyant visuellement » — et c'était le
 * reproche fait à l'étape 12.2, en pire, puisqu'il n'y avait même plus de parallaxe.
 * Deux erreurs : l'image ne participait à rien, et un dispositif d'ACCESSIBILITÉ
 * (le sous-titre) avait été pris pour un dispositif de MOTION DESIGN.
 *
 * Cette version traite l'image comme une MATIÈRE, jamais comme un fond en attente :
 * fragmentée en bandes qui se recollent, recadrée dur en médaillon, répétée en
 * grille, décalée par fentes, réduite à un projecteur, mise en split qui s'inverse.
 * Ce qui bouge, c'est l'image elle-même — la fenêtre ET le cadrage dedans.
 * Toujours ZÉRO génération : les trois PNG viennent de la bibliothèque de 12.2.
 */
import {
  makeProject, all, delay, chain, createRef, waitFor,
  easeOutCubic, easeInCubic, easeInOutCubic, easeOutBack, easeOutExpo, easeInExpo, linear,
} from '@revideo/core';
import {Rect, Txt, Circle, Line, Node, Img, makeScene2D} from '@revideo/2d';
import './styles.css';
import fond1 from './fonds/fond1.png';
import fond2 from './fonds/fond2.png';
import fond3 from './fonds/fond3.png';
import {BG, TEXTE, ACCENT, HIGHLIGHT, POLICE, L, H, FIN} from './charte';

await document.fonts.load('600 100px "InterBMS"');
await document.fonts.load('400 100px "InterBMS"');

/**
 * Fenêtre sur l'image. Le Rect découpe, l'Img se déplace DEDANS : c'est le cadrage
 * qui vit, pas seulement la position de la fenêtre. La largeur du Rect n'est jamais
 * animée — cela déplacerait son centre, donc son enfant (défaut trouvé sur A v2).
 */
function fenetre(rr: any, ri: any, src: string, w: number, h: number, x: number, y: number,
                 ech: number, ix: number, iy: number, rayon = 0) {
  return (
    <Rect ref={rr} clip width={w} height={h} x={x} y={y} radius={rayon}>
      <Img ref={ri} src={src} width={L * ech} height={H * ech} x={ix} y={iy} />
    </Rect>
  );
}

const scene = makeScene2D('motionC', function* (view) {
  view.fill(BG);

  const cam = createRef<Node>();
  const flash = createRef<Rect>();
  const P = [0, 1, 2, 3, 4, 5].map(() => createRef<Node>());

  // C1 — trois bandes verticales qui se recollent sur « code »
  const c1r = [0, 1, 2].map(() => createRef<Rect>());
  const c1i = [0, 1, 2].map(() => createRef<Img>());
  const c1bloc = createRef<Rect>();
  const c1sucre = createRef<Txt>();
  const c1code = createRef<Txt>();
  const c1bas = [0, 1, 2].map(() => createRef<Txt>());
  const c1n = createRef<Txt>();

  // C2 — médaillon en gros plan, puis split plein
  const c2medR = createRef<Rect>(); const c2medI = createRef<Img>();
  const c2anneau = createRef<Circle>();
  const c2col = [0, 1, 2, 3].map(() => createRef<Txt>());
  const c2chim = createRef<Txt>();
  const c2splitR = createRef<Rect>(); const c2splitI = createRef<Img>();
  const c2pave = createRef<Rect>();
  const c2sac = createRef<Txt>();
  const c2cris = createRef<Txt>();
  const c2los: any[] = []; const c2losR: any[] = [];
  for (let i = 0; i < 9; i++) {
    const r = createRef<Rect>(); c2losR.push(r);
    c2los.push(<Rect ref={r} width={22} height={22} rotation={45} stroke={HIGHLIGHT}
                     lineWidth={3} x={140 + (i % 3) * 230} y={-300 + Math.floor(i / 3) * 300}
                     opacity={0} />);
  }

  // C3 — la même image répétée en grille, puis une seule
  const c3r = [0, 1, 2, 3, 4, 5].map(() => createRef<Rect>());
  const c3i = [0, 1, 2, 3, 4, 5].map(() => createRef<Img>());
  const c3pas = createRef<Txt>();
  const c3biff = createRef<Line>();

  // C4 — fentes décalées + circulation vectorielle par-dessus
  const c4r = [0, 1, 2, 3, 4].map(() => createRef<Rect>());
  const c4i = [0, 1, 2, 3, 4].map(() => createRef<Img>());
  const c4vais = createRef<Line>();
  const c4bille: any[] = []; const c4billeR: any[] = [];
  for (let i = 0; i < 6; i++) {
    const r = createRef<Circle>(); c4billeR.push(r);
    c4bille.push(<Circle ref={r} size={30} fill={i % 2 ? HIGHLIGHT : ACCENT} opacity={0}
                         x={-820} y={330} />);
  }
  const c4sub = createRef<Txt>();
  const c4prec = createRef<Txt>();
  const c4plaque = createRef<Rect>();

  // C5 — tout est noir sauf un projecteur
  const c5R = createRef<Rect>(); const c5I = createRef<Img>();
  const c5cercle = createRef<Circle>();
  const c5reg = createRef<Txt>();
  const c5cac = createRef<Txt>();
  const c5mal = createRef<Txt>();

  // C6 — split qui s'inverse, puis trois vignettes
  const c6R = createRef<Rect>(); const c6I = createRef<Img>();
  const c6pave = createRef<Rect>();
  const c6ins = createRef<Txt>();
  const c6sous = createRef<Txt>();
  const c6vR = [0, 1, 2].map(() => createRef<Rect>());
  const c6vI = [0, 1, 2].map(() => createRef<Img>());
  const c6vT = [0, 1, 2].map(() => createRef<Txt>());
  const NOMS = ['GLUCIDES', 'LIPIDES', 'PROTÉINES'];

  yield view.add(
    <>
      <Node ref={cam}>

        {/* ---------- C1 : l'image arrive en morceaux, se recolle sur « code » ---------- */}
        <Node ref={P[0]} opacity={0}>
          {[0, 1, 2].map(i => fenetre(c1r[i], c1i[i], fond1, 636, H, -640 + i * 640, 0,
                                      1.25, [180, -90, -240][i], 0))}
          <Rect ref={c1bloc} width={0} height={270} fill={ACCENT} y={-30} offset={[-1, 0]} x={-960} />
          <Txt ref={c1sucre} y={-30} text={'SUCRE'} fontFamily={POLICE} fontWeight={600}
               fontSize={290} fill={TEXTE} opacity={0} />
          <Txt ref={c1code} y={230} text={'UN CODE'} fontFamily={POLICE} fontWeight={600}
               fontSize={180} fill={'#00000000'} stroke={HIGHLIGHT} lineWidth={4} opacity={0} />
          <Txt ref={c1n} x={840} y={-450} text={'01'} fontFamily={POLICE} fontWeight={600}
               fontSize={40} fill={HIGHLIGHT} opacity={0} />
          {['QU\'ON', 'IGNORE', 'TOUS QUOTIDIENNEMENT'].map((m, i) => (
            <Txt ref={c1bas[i]} x={[-870, -640, -370][i]} y={440} offset={[-1, 0]} text={m}
                 fontFamily={POLICE} fontWeight={400} fontSize={38} fill={TEXTE} opacity={0} />
          ))}
        </Node>

        {/* ---------- C2 : gros plan en médaillon, puis split ---------- */}
        <Node ref={P[1]} opacity={0}>
          {fenetre(c2splitR, c2splitI, fond2, 960, H, 480, 0, 1.5, -100, 0)}
          <Rect ref={c2pave} width={1010} height={H} fill={ACCENT} x={-455} opacity={0} />
          {fenetre(c2medR, c2medI, fond2, 760, 760, 420, 0, 2.6, -120, 40, 380)}
          <Circle ref={c2anneau} size={772} x={420} stroke={HIGHLIGHT} lineWidth={6}
                  startAngle={-90} endAngle={-90} closed={false} />
          {['LE', 'SUCRE', 'DE', 'TABLE'].map((m, i) => (
            <Txt ref={c2col[i]} x={-900} y={-250 + i * 120} offset={[-1, 0]} text={m}
                 fontFamily={POLICE} fontWeight={600} fontSize={i === 1 ? 110 : 66}
                 fill={i === 1 ? HIGHLIGHT : TEXTE} opacity={0} />
          ))}
          <Txt ref={c2chim} x={-900} y={320} offset={[-1, 0]} text={'CHIMIQUEMENT FORMÉ'}
               fontFamily={POLICE} fontWeight={400} fontSize={52} fill={ACCENT} opacity={0} />
          <Txt ref={c2sac} x={-900} y={-60} offset={[-1, 0]} text={'SACCHAROSE'} fontFamily={POLICE}
               fontWeight={600} fontSize={106} fill={BG} opacity={0} />
          <Txt ref={c2cris} x={-900} y={70} offset={[-1, 0]} text={'CRISTALLISÉ'} fontFamily={POLICE}
               fontWeight={400} fontSize={56} fill={BG} opacity={0} />
          {c2los}
        </Node>

        {/* ---------- C3 : la même image six fois, puis une seule ---------- */}
        <Node ref={P[2]} opacity={0}>
          {[0, 1, 2, 3, 4, 5].map(i => fenetre(
            c3r[i], c3i[i], fond2, 560, 400, -600 + (i % 3) * 600, -230 + Math.floor(i / 3) * 460,
            1.1 + (i % 3) * 0.35, -240 + (i % 3) * 240, -120 + Math.floor(i / 3) * 240))}
          <Txt ref={c3pas} y={20} text={'PAS INERTE'} fontFamily={POLICE} fontWeight={600}
               fontSize={200} fill={HIGHLIGHT} opacity={0} />
          <Line ref={c3biff} points={[[-680, 60], [680, -20]]} stroke={HIGHLIGHT} lineWidth={20} end={0} />
        </Node>

        {/* ---------- C4 : l'image décalée par fentes, circulation dessus ---------- */}
        <Node ref={P[3]} opacity={0}>
          {[0, 1, 2, 3, 4].map(i => fenetre(
            c4r[i], c4i[i], fond2, L, 218, 0, -432 + i * 216, 1.30, 0, (432 - i * 216) * 1.30))}
          <Line ref={c4vais} stroke={ACCENT} lineWidth={30} opacity={0.6} end={0} radius={40}
                lineCap={'round'} points={[[-820, 330], [-420, 370], [0, 300], [420, 360], [820, 310]]} />
          {c4bille}
          <Rect ref={c4plaque} width={1240} height={160} fill={BG} y={-330} opacity={0} radius={8} />
          <Txt ref={c4sub} y={-330} text={'SUBSTRAT MÉTABOLIQUE'} fontFamily={POLICE}
               fontWeight={600} fontSize={92} fill={TEXTE} opacity={0} />
          <Txt ref={c4prec} y={-190} text={'PRÉCISION BIOLOGIQUE'} fontFamily={POLICE}
               fontWeight={400} fontSize={52} fill={HIGHLIGHT} opacity={0} />
        </Node>

        {/* ---------- C5 : un projecteur, et rien d'autre ---------- */}
        <Node ref={P[4]} opacity={0}>
          {fenetre(c5R, c5I, fond2, 900, 900, -180, 60, 1.6, 120, -40, 450)}
          <Circle ref={c5cercle} size={912} x={-180} y={60} stroke={HIGHLIGHT} lineWidth={5}
                  lineDash={[26, 18]} opacity={0} />
          <Txt ref={c5reg} x={-900} y={-390} offset={[-1, 0]} text={'RÉGULATION'} fontFamily={POLICE}
               fontWeight={600} fontSize={136} fill={TEXTE} opacity={0} />
          <Txt ref={c5cac} x={900} y={-250} offset={[1, 0]} text={'CACHÉE'} fontFamily={POLICE}
               fontWeight={600} fontSize={166} fill={HIGHLIGHT} opacity={0} />
          <Txt ref={c5mal} x={900} y={370} offset={[1, 0]} text={'MALADES ?'} fontFamily={POLICE}
               fontWeight={600} fontSize={116} fill={TEXTE} opacity={0} />
        </Node>

        {/* ---------- C6 : split qui s'inverse, puis trois vignettes ---------- */}
        <Node ref={P[5]} opacity={0}>
          {fenetre(c6R, c6I, fond3, 960, H, -480, 0, 1.5, 120, 0)}
          <Rect ref={c6pave} width={960} height={H} fill={BG} x={480} />
          <Txt ref={c6ins} x={480} y={-40} text={'INSULINE'} fontFamily={POLICE} fontWeight={600}
               fontSize={144} fill={TEXTE} opacity={0} />
          <Txt ref={c6sous} x={480} y={90} text={'HORMONE ANABOLIQUE'} fontFamily={POLICE}
               fontWeight={400} fontSize={44} fill={ACCENT} opacity={0} />
          {[0, 1, 2].map(i => fenetre(c6vR[i], c6vI[i], fond3, 520, 290, -600 + i * 600, 300,
                                      1.4, -260 + i * 260, -60))}
          {[0, 1, 2].map(i => (
            <Txt ref={c6vT[i]} x={-600 + i * 600} y={300} text={NOMS[i]} fontFamily={POLICE}
                 fontWeight={600} fontSize={52} fill={TEXTE} opacity={0} />
          ))}
        </Node>
      </Node>

      <Rect ref={flash} width={2600} height={1500} fill={TEXTE} opacity={0} />
    </>,
  );

  // ================= planification absolue =================
  const T: any[] = [];
  const t0 = (t: number, tache: any) => T.push(delay(Math.max(0, t), tache));
  function* coupe(i: number, j: number, couleur = TEXTE) {
    flash().fill(couleur);
    yield* flash().opacity(0.85, 0.05);
    P[i]().opacity(0);
    P[j]().opacity(1);
    yield* flash().opacity(0, 0.13);
  }

  T.push(chain(
    cam().scale(1.02, 4.9, linear), cam().scale(1, 0.01),
    cam().scale(1.025, 5.9, linear), cam().scale(1, 0.01),
    cam().scale(1.02, 2.3, linear), cam().scale(1, 0.01),
    cam().scale(1.025, 5.8, linear), cam().scale(1, 0.01),
    cam().scale(1.02, 4.3, linear), cam().scale(1, 0.01),
    cam().scale(1.03, 8.3, linear),
  ));

  // ---------------- C1 : 0,00 → 4,90 ----------------
  t0(0.00, P[0]().opacity(1, 0.01));
  [0.00, 0.46, 0.60].forEach((t, i) => t0(t, (function* () {
    c1r[i]().y(i % 2 ? 1140 : -1140);
    yield* c1r[i]().y(0, 0.5, easeOutExpo);
  })()));
  t0(0.60, all(c1i[0]().x(110, 1.9, linear), c1i[1]().x(-20, 1.9, linear),
               c1i[2]().x(-170, 1.9, linear)));
  t0(0.30, c1n().opacity(1, 0.3));
  t0(1.84, (function* () {
    c1sucre().scale(0.8);
    yield* all(c1bloc().width(L + 200, 0.32, easeOutExpo), c1sucre().opacity(1, 0.18),
               c1sucre().scale(1, 0.4, easeOutBack));
  })());
  // « un code » : les trois morceaux se recollent, l'image redevient entière
  t0(2.54, all(c1i[0]().x(640, 0.55, easeInOutCubic), c1i[1]().x(0, 0.55, easeInOutCubic),
               c1i[2]().x(-640, 0.55, easeInOutCubic),
               c1bloc().width(0, 0.4, easeInCubic), c1sucre().opacity(0, 0.3)));
  t0(2.60, (function* () {
    c1code().opacity(0).scale(0.8);
    yield* all(c1code().opacity(1, 0.25), c1code().scale(1, 0.7, easeOutExpo));
    yield* c1code().scale(1.05, 1.5, linear);
  })());
  [2.80, 3.32, 3.68].forEach((t, i) => t0(t, all(
    c1bas[i]().opacity(1, 0.16), c1bas[i]().x([-870, -640, -370][i] + 14, 0.26, easeOutCubic))));

  // ---------------- C2 : 5,10 → 10,80 ----------------
  t0(5.04, coupe(0, 1, ACCENT));
  t0(5.10, (function* () {
    c2medR().scale(0.2).rotation(-25);
    yield* all(c2medR().scale(1, 0.55, easeOutExpo), c2medR().rotation(0, 0.55, easeOutExpo));
    yield* c2anneau().endAngle(270, 0.6, easeOutCubic);
  })());
  t0(5.10, all(c2medI().x(60, 4.3, linear), c2medI().y(-60, 4.3, linear)));
  [5.10, 5.60, 5.90, 6.08].forEach((t, i) => t0(t, all(
    c2col[i]().opacity(1, 0.16), c2col[i]().x(-870, 0.28, easeOutCubic))));
  t0(6.60, all(c2chim().opacity(1, 0.2), c2chim().x(-870, 0.3, easeOutCubic)));
  // « saccharose » : coupe franche, le médaillon cède au plan large
  t0(9.46, (function* () {
    yield* all(c2medR().scale(2.6, 0.18, easeInExpo), c2medR().opacity(0, 0.18),
               c2anneau().opacity(0, 0.12),
               ...c2col.map(r => r().opacity(0, 0.12)), c2chim().opacity(0, 0.12));
    c2pave().opacity(1);
    yield* all(c2sac().opacity(1, 0.22), c2sac().x(-870, 0.32, easeOutCubic));
  })());
  t0(9.46, all(c2splitI().x(20, 3.0, linear), c2splitI().scale(1.05, 3.0, linear)));
  t0(10.12, all(c2cris().opacity(1, 0.2), c2cris().x(-870, 0.3, easeOutCubic)));
  c2losR.forEach((r, i) => t0(10.20 + i * 0.05, all(
    r().opacity(1, 0.2), r().rotation(225, 1.2, easeOutCubic))));

  // ---------------- C3 : 11,20 → 13,50 ----------------
  t0(11.14, coupe(1, 2, HIGHLIGHT));
  [11.20, 11.40, 11.60, 11.76, 11.96, 12.08].forEach((t, i) => t0(t, (function* () {
    c3r[i]().scale(0).rotation(-12 + i * 5);
    yield* all(c3r[i]().scale(1, 0.34, easeOutBack), c3r[i]().rotation(0, 0.34, easeOutCubic));
  })()));
  t0(11.30, all(...c3i.map((r, i) => r().x(-240 + (i % 3) * 240 + (i % 2 ? 120 : -120), 2.2, linear))));
  t0(12.62, (function* () {
    yield* all(...[0, 1, 2, 3, 5].map(i => all(c3r[i]().scale(0, 0.26, easeInCubic),
                                               c3r[i]().opacity(0, 0.26))));
    yield* all(c3r[4]().size([L, H], 0.42, easeOutExpo),
               c3r[4]().position([0, 0], 0.42, easeOutExpo),
               c3i[4]().scale(1.5, 0.42, easeOutExpo));
  })());
  t0(12.70, (function* () {
    c3pas().scale(1.3);
    yield* all(c3pas().opacity(1, 0.2), c3pas().scale(1, 0.4, easeOutBack));
  })());
  t0(13.08, c3biff().end(1, 0.3, easeInCubic));

  // ---------------- C4 : 13,52 → 18,76 ----------------
  t0(13.46, coupe(2, 3, ACCENT));
  [0, 1, 2, 3, 4].forEach(i => {
    t0(13.52 + i * 0.06, c4i[i]().x((i % 2 ? 1 : -1) * (90 + i * 34), 0.5, easeOutExpo));
    t0(17.62, c4i[i]().x(0, 0.8, easeInOutCubic));      // les fentes se recalent
  });
  t0(14.34, (function* () {
    c4sub().scale(0.85);
    yield* all(c4plaque().opacity(0.82, 0.2), c4sub().opacity(1, 0.22),
               c4sub().scale(1, 0.38, easeOutBack));
  })());
  t0(14.82, c4vais().end(1, 1.0, easeInOutCubic));
  c4billeR.forEach((r, i) => t0(15.2 + i * 0.26, (function* () {
    r().opacity(1).position([-820, 330]);
    yield* all(r().x(820, 1.7, easeInOutCubic),
               chain(r().y(370, 0.42), r().y(300, 0.42), r().y(360, 0.42), r().y(310, 0.44)));
    yield* r().opacity(0, 0.2);
  })()));
  t0(17.62, (function* () {
    c4prec().y(-120);
    yield* all(c4prec().opacity(1, 0.25), c4prec().y(-190, 0.35, easeOutCubic));
  })());

  // ---------------- C5 : 19,40 → 23,72 ----------------
  t0(19.34, coupe(3, 4, BG));
  t0(19.40, (function* () {
    c5R().scale(0.1);
    yield* all(c5R().scale(1, 0.6, easeOutExpo), c5cercle().opacity(0.8, 0.4));
    yield* all(c5R().position([160, -40], 2.2, easeInOutCubic),
               c5cercle().position([160, -40], 2.2, easeInOutCubic),
               c5I().x(-60, 2.2, linear));
  })());
  t0(20.42, all(c5reg().opacity(1, 0.22), c5reg().x(-870, 0.32, easeOutCubic)));
  t0(20.94, all(c5cac().opacity(1, 0.22), c5cac().x(870, 0.32, easeOutCubic)));
  t0(21.60, all(c5R().scale(0.42, 0.9, easeInOutCubic),     // « cachée » : il se referme
                c5cercle().scale(0.42, 0.9, easeInOutCubic)));
  t0(22.10, (function* () {
    c5mal().scale(1.3);
    yield* all(c5mal().opacity(1, 0.18), c5mal().scale(1, 0.34, easeOutBack),
               c5mal().x(870, 0.34, easeOutCubic));
  })());
  t0(22.94, all(c5R().scale(0.9, 0.7, easeOutCubic), c5cercle().scale(0.9, 0.7, easeOutCubic)));

  // ---------------- C6 : 23,72 → 32,00 ----------------
  t0(23.66, coupe(4, 5, HIGHLIGHT));
  t0(23.72, (function* () {
    c6R().x(-1440);
    yield* c6R().x(-480, 0.5, easeOutExpo);
  })());
  t0(23.72, (function* () {
    c6ins().y(60);
    yield* all(c6ins().opacity(1, 0.25), c6ins().y(-40, 0.4, easeOutCubic));
  })());
  t0(23.72, c6I().x(-40, 8.2, linear));                    // cadrage vivant jusqu'à la fin
  t0(24.98, all(c6sous().opacity(1, 0.25), c6sous().y(90, 0.3, easeOutCubic)));
  t0(26.44, all(c6R().x(480, 0.7, easeInOutCubic), c6pave().x(-480, 0.7, easeInOutCubic),
                c6ins().x(-480, 0.7, easeInOutCubic), c6sous().x(-480, 0.7, easeInOutCubic),
                c6ins().y(-260, 0.7, easeInOutCubic), c6sous().y(-140, 0.7, easeInOutCubic)));
  [28.32, 29.62, 31.02].forEach((t, i) => t0(t, (function* () {
    c6vR[i]().scale(0).y(420);
    yield* all(c6vR[i]().scale(1, 0.38, easeOutBack), c6vR[i]().y(290, 0.38, easeOutCubic));
    yield* all(c6vT[i]().opacity(1, 0.2), c6vT[i]().y(490, 0.3, easeOutCubic));
  })()));
  t0(31.66, all(...c6vR.map(r => r().scale(1.05, 0.3, easeOutCubic)),
                cam().scale(1.02, 0.34, easeOutCubic)));

  yield* all(waitFor(FIN), ...T);
});

export default makeProject({scenes: [scene]});
