/**
 * Figures génériques — les objets que les scènes **construisent**.
 *
 * Aucune n'est propre à un sujet : elles sont paramétrées par une couleur, une taille et un
 * libellé. C'est la réponse au coût qui a fait échouer la preuve du 16/09 — la séquence B était
 * belle mais sa géométrie était celle du saccharose, 371 lignes pour 32 secondes, non rejouables
 * sur un autre script. Ici la géométrie est générique, le script ne fournit que des mots et des
 * nombres.
 *
 * Toutes sont dessinées **au trait épais sur aplat**, contours arrondis : c'est le registre
 * graphique de la chaîne de référence, et c'est ce que des primitives vectorielles savent tenir.
 */
import {Rect, Txt, Node, Line, Circle} from '@revideo/2d';
import {createRef} from '@revideo/core';
import {C, melanger} from './charte';
import {alea} from './commun';

/** Sommets d'un polygone régulier à n côtés, rayon r, tourné de `rot` degrés. */
export function poly(n: number, r: number, rot = 0): [number, number][] {
  const p: [number, number][] = [];
  for (let i = 0; i < n; i++) {
    const a = ((i / n) * 360 + rot) * (Math.PI / 180);
    p.push([Math.cos(a) * r, Math.sin(a) * r]);
  }
  return p;
}

/** Contour irrégulier fermé — un « objet » qui n'est ni un cercle ni une boîte. */
export function blob(rayon: number, graine: number, sommets = 9): [number, number][] {
  const r = alea(graine);
  const p: [number, number][] = [];
  for (let i = 0; i < sommets; i++) {
    const a = (i / sommets) * Math.PI * 2;
    const d = rayon * (0.74 + r() * 0.5);
    p.push([Math.cos(a) * d, Math.sin(a) * d]);
  }
  return p;
}

/**
 * Un astre : disque plein, anneau de contour, quelques cratères, halo. Sert de « corps »
 * générique — planète, cellule, noyau, objet.
 */
export function astre(rayon: number, couleur: string, graine: number, halo = true) {
  const r = alea(graine * 31);
  const corps = createRef<Circle>();
  const anneau = createRef<Circle>();
  const lueur = createRef<Circle>();
  const taches: any[] = [];
  for (let i = 0; i < 4; i++) {
    const a = r() * Math.PI * 2;
    const d = r() * rayon * 0.62;
    taches.push(
      <Circle x={Math.cos(a) * d} y={Math.sin(a) * d} size={rayon * (0.16 + r() * 0.22)}
              fill={melanger(couleur, C.bg, 0.45)} opacity={0.75} />,
    );
  }
  const noeud = (
    <Node>
      {halo ? <Circle ref={lueur} size={rayon * 2.9} fill={couleur} opacity={0.10} /> : null}
      <Circle ref={corps} size={rayon * 2} fill={melanger(couleur, C.bg, 0.30)} />
      <Circle size={rayon * 2} clip cache>{taches}</Circle>
      <Circle ref={anneau} size={rayon * 2} stroke={couleur} lineWidth={Math.max(5, rayon * 0.09)} />
    </Node>
  );
  return {noeud, corps, anneau, lueur};
}

/**
 * Un visage — la brique qui transforme **n'importe quelle forme** en être vivant.
 *
 * Grammaire relevée sur la chaîne de référence (recherche du 19/09/2026) : « énormes yeux
 * ovoïdes blancs cernés, sourcils noirs fins, bouche large avec langue ». C'est cette grammaire,
 * et pas une silhouette particulière, qui fait que le spectateur voit un personnage : posée sur
 * un disque elle donne une planète qui parle, posée sur un haricot elle donne un organe.
 */
export function visage(taille: number, options: {sourcils?: boolean} = {}) {
  const oeilG = createRef<Node>();
  const oeilD = createRef<Node>();
  const paupG = createRef<Rect>();
  const paupD = createRef<Rect>();
  const pupG = createRef<Circle>();
  const pupD = createRef<Circle>();
  const sourcilG = createRef<Line>();
  const sourcilD = createRef<Line>();
  const bouche = createRef<Circle>();
  const langue = createRef<Circle>();
  const groupe = createRef<Node>();

  const rOeil = taille * 0.26;
  const ecart = taille * 0.30;
  const trait = Math.max(3, taille * 0.035);

  // La pupille et la paupière sont détourées **par l'œil** (`clip`). Sans cela, le volet de la
  // paupière se voit en entier au-dessus du visage : deux rectangles noirs sur le front, relevés
  // sur la planche du 19/09.
  const oeil = (ref: any, paup: any, pup: any, x: number) => (
    <Node ref={ref} x={x}>
      <Circle width={rOeil * 1.6} height={rOeil * 2} fill={'#ffffff'} clip cache>
        <Circle ref={pup} size={rOeil * 0.72} fill={'#0c0c0c'} />
        <Rect ref={paup} width={rOeil * 2.2} height={rOeil * 2.4} y={-rOeil * 2.4}
              fill={'#0c0c0c'} opacity={0} />
      </Circle>
      <Circle width={rOeil * 1.6} height={rOeil * 2} stroke={'#0c0c0c'} lineWidth={trait} />
    </Node>
  );

  const noeud = (
    <Node ref={groupe}>
      {oeil(oeilG, paupG, pupG, -ecart)}
      {oeil(oeilD, paupD, pupD, ecart)}
      {options.sourcils === false ? null : (
        <>
          <Line ref={sourcilG} points={[[-ecart - rOeil * 0.75, -rOeil * 1.74],
                                        [-ecart + rOeil * 0.62, -rOeil * 1.80]]}
                stroke={'#0c0c0c'} lineWidth={trait * 1.5} lineCap={'round'} />
          <Line ref={sourcilD} points={[[ecart - rOeil * 0.62, -rOeil * 1.80],
                                        [ecart + rOeil * 0.75, -rOeil * 1.74]]}
                stroke={'#0c0c0c'} lineWidth={trait * 1.5} lineCap={'round'} />
        </>
      )}
      {/* La bouche est une ellipse dont la hauteur suit la voix : fermée, elle est un trait. */}
      <Node y={taille * 0.52} clip cache>
        <Circle width={taille * 0.62} height={taille * 0.5} fill={'#0c0c0c'} />
        <Circle ref={langue} y={taille * 0.20} width={taille * 0.40} height={taille * 0.26}
                fill={'#e4726a'} />
      </Node>
      <Circle ref={bouche} y={taille * 0.52} width={taille * 0.62} height={taille * 0.5}
              stroke={'#0c0c0c'} lineWidth={trait} />
    </Node>
  );
  return {noeud, groupe, oeilG, oeilD, paupG, paupD, pupG, pupD, sourcilG, sourcilD, bouche, langue};
}

/**
 * Un être — un corps de n'importe quelle forme, un visage, quatre membres filiformes, des gants
 * et des chaussures blancs.
 *
 * `forme` décide de ce qu'il est : `rond` (une planète, une cellule), `carre` (un objet, une
 * boîte), `blob` (un organe, un aliment). Le reste est identique, et c'est voulu : une chaîne se
 * reconnaît à sa grammaire de personnages, pas à leur nombre.
 */
export function etre(
  hauteur: number, couleur: string, graine: number,
  forme: 'rond' | 'carre' | 'blob' = 'rond',
) {
  const corps = createRef<Node>();
  const buste = createRef<Node>();
  const brasG = createRef<Line>();
  const brasD = createRef<Line>();
  const jambeG = createRef<Line>();
  const jambeD = createRef<Line>();
  const gantG = createRef<Circle>();
  const gantD = createRef<Circle>();
  const face = visage(hauteur * 0.30);

  const rCorps = hauteur * 0.34;
  const trait = Math.max(6, hauteur * 0.034);
  const remplissage = melanger(couleur, '#ffffff', 0.18);
  const contour = '#0c0c0c';

  const silhouette =
    forme === 'carre'
      ? <Rect width={rCorps * 1.9} height={rCorps * 1.9} radius={rCorps * 0.32}
              fill={remplissage} stroke={contour} lineWidth={trait} />
      : forme === 'blob'
        ? <Line points={blob(rCorps, graine, 9)} closed fill={remplissage} stroke={contour}
                lineWidth={trait} lineJoin={'round'} radius={18} />
        : <Circle size={rCorps * 2} fill={remplissage} stroke={contour} lineWidth={trait} />;

  const membre = (
    ref: any, ax: number, ay: number, bx: number, by: number, cx?: number, cy?: number,
  ) => (
    <Line ref={ref}
          points={cx === undefined ? [[ax, ay], [bx, by]] : [[ax, ay], [cx, cy!], [bx, by]]}
          stroke={contour} lineWidth={trait} lineCap={'round'} lineJoin={'round'} radius={12} />
  );

  const noeud = (
    <Node ref={corps}>
      {membre(jambeG, -rCorps * 0.30, rCorps * 0.82, -rCorps * 0.44, rCorps * 1.46)}
      {membre(jambeD, rCorps * 0.30, rCorps * 0.82, rCorps * 0.44, rCorps * 1.46)}
      <Circle x={-rCorps * 0.46} y={rCorps * 1.54} width={rCorps * 0.44} height={rCorps * 0.28}
              fill={'#ffffff'} stroke={contour} lineWidth={trait * 0.8} />
      <Circle x={rCorps * 0.46} y={rCorps * 1.54} width={rCorps * 0.44} height={rCorps * 0.28}
              fill={'#ffffff'} stroke={contour} lineWidth={trait * 0.8} />
      {/* Bras **coudés et tombants**. Tendus à l'horizontale et terminés par une bille, ils se
          lisaient comme des antennes (planche du 19/09). */}
      {membre(brasG, -rCorps * 0.74, -rCorps * 0.02, -rCorps * 0.86, rCorps * 0.96,
              -rCorps * 1.06, rCorps * 0.42)}
      {membre(brasD, rCorps * 0.74, -rCorps * 0.02, rCorps * 0.86, rCorps * 0.96,
              rCorps * 1.06, rCorps * 0.42)}
      <Circle ref={gantG} x={-rCorps * 0.86} y={rCorps * 1.00} size={rCorps * 0.36}
              fill={'#ffffff'} stroke={contour} lineWidth={trait * 0.85} />
      <Circle ref={gantD} x={rCorps * 0.86} y={rCorps * 1.00} size={rCorps * 0.36}
              fill={'#ffffff'} stroke={contour} lineWidth={trait * 0.85} />
      <Node ref={buste}>
        {silhouette}
        <Node y={-rCorps * 0.12}>{face.noeud}</Node>
      </Node>
    </Node>
  );
  return {noeud, corps, buste, brasG, brasD, jambeG, jambeD, gantG, gantD, face, rCorps, trait};
}

/** Lignes de vitesse radiales — la ponctuation de la surprise. */
export function lignesDeVitesse(rayon: number, couleur: string, combien = 14) {
  const refs: any[] = [];
  const traits: any[] = [];
  for (let i = 0; i < combien; i++) {
    const ref = createRef<Line>();
    refs.push(ref);
    const a = (i / combien) * Math.PI * 2;
    const d1 = rayon * (1.0 + (i % 2) * 0.18);
    const d2 = d1 + rayon * (0.30 + (i % 3) * 0.12);
    traits.push(
      <Line ref={ref} points={[[Math.cos(a) * d1, Math.sin(a) * d1],
                               [Math.cos(a) * d2, Math.sin(a) * d2]]}
            stroke={couleur} lineWidth={7} lineCap={'round'} opacity={0} />,
    );
  }
  return {noeud: <Node>{traits}</Node>, refs};
}

/** Un bloc étiqueté : la brique des schémas de processus. */
export function bloc(largeur: number, hauteur: number, couleur: string, texte: string) {
  const cadre = createRef<Rect>();
  const mot = createRef<Txt>();
  const noeud = (
    <Node>
      <Rect ref={cadre} width={largeur} height={hauteur} radius={hauteur * 0.22}
            fill={melanger(couleur, C.bg, 0.70)} stroke={couleur} lineWidth={5} />
      <Txt ref={mot} text={texte.toUpperCase()} fontFamily={C.font_body.family} fontWeight={700}
           fontSize={Math.min(38, largeur / Math.max(4, texte.length * 0.62))} fill={C.text}
           width={largeur * 0.86} textWrap textAlign={'center'} letterSpacing={1} />
    </Node>
  );
  return {noeud, cadre, mot};
}

/** Une flèche d'un point à un autre, tracée progressivement, pointe comprise. */
export function fleche(de: [number, number], vers: [number, number], couleur: string, epaisseur = 7) {
  const corps = createRef<Line>();
  const pointe = createRef<Line>();
  const dx = vers[0] - de[0];
  const dy = vers[1] - de[1];
  const angle = (Math.atan2(dy, dx) * 180) / Math.PI;
  const t = Math.max(14, epaisseur * 2.4);
  const noeud = (
    <Node>
      <Line ref={corps} points={[de, vers]} stroke={couleur} lineWidth={epaisseur}
            lineCap={'round'} end={0} />
      <Line ref={pointe} x={vers[0]} y={vers[1]} rotation={angle}
            points={[[-t, -t * 0.8], [0, 0], [-t, t * 0.8]]} stroke={couleur}
            lineWidth={epaisseur} lineCap={'round'} lineJoin={'round'} scale={0} />
    </Node>
  );
  return {noeud, corps, pointe};
}
