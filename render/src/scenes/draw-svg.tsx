/**
 * Whiteboard animé — un dessin au trait s'allonge sous une main qui en suit la pointe.
 *
 * Trois mécanismes, et rien d'autre.
 *
 * 1. **Un contour = un geste.** `factory/styles/whiteboard.py` livre les contours déjà **dans
 *    l'ordre de dessin** (gros éléments d'abord, chaque passe balayée haut-gauche → bas-droite).
 *    La scène ne réordonne rien : elle déroule.
 * 2. **Une horloge unique.** `avancee` va de 0 à 1 sur les 80 % de tracé du plan. La position
 *    de la main n'est pas animée séparément — elle est **calculée** depuis cette horloge, donc
 *    elle ne peut pas se désynchroniser du trait. C'est le seul moyen de tenir la promesse du
 *    style : la main est sur le trait, toujours.
 * 3. **Le remplissage vient après.** Chaque contour porte un jumeau plein, à opacité nulle, qui
 *    monte une fois le trait refermé. Un contour rempli pendant son tracé donnerait une tache
 *    qui pousse, pas un dessin qui se fait.
 *
 * Le temps est réparti au **prorata de la longueur d'arc** mesurée par Revideo, pas du nombre de
 * contours : sans cela, un point de ponctuation coûterait autant qu'une silhouette entière et la
 * main passerait son temps sur les détails.
 */
import {Img, Node, Path, Rect, Txt} from '@revideo/2d';
import {
  createRef, createSignal, easeOutCubic, linear, all, delay, tween,
  transformVectorAsPoint, Vector2,
} from '@revideo/core';
import {C, L, H, UX, UY, MARGE} from '../charte';
import {alea} from '../commun';

/** Épaisseur du trait, en pixels d'écran (l'échelle du dessin est compensée à la pose). */
const EPAISSEUR = 3.4;

/** Opacité du remplissage. Plein à 1, le dessin devient une masse ; à 0,9 il respire. */
const OPACITE_PLEIN = 0.9;

/** Part du cadre occupée par le dessin quand il n'y a pas de texte manuscrit. */
const PART_DESSIN_SEUL = 0.84;
/** Part du cadre occupée par le dessin quand un texte manuscrit partage la page. */
const PART_DESSIN_AVEC_TEXTE = 0.62;

/**
 * Couleur d'un contour. L'encre domine ; l'accent et le rehaut **ponctuent**.
 *
 * Trois marqueurs en alternance stricte — le premier essai du 19/09 — donnaient un dessin
 * bariolé où plus rien ne se lisait : un whiteboard est un dessin noir que la couleur souligne,
 * pas un dessin en couleur.
 */
function marqueur(index: number): string {
  if (index % 7 === 3) return C.accent;
  if (index % 11 === 5) return C.highlight;
  return C.text;
}

export function drawSvg(view: any, props: any, duree: number) {
  const graine: number = props.seed ?? 1;
  const contours: string[] = props.paths ?? [];
  const texte = String(props.on_screen_text ?? '').trim();
  const taches: any[] = [];

  // -- la page ------------------------------------------------------------------------
  view.fill(C.bg);
  papier(view, graine);
  if (props.title) entete(view, String(props.title));

  // La caméra porte tout : le tremblement doit bouger la page, pas le dessin dans la page.
  const cam = createRef<Node>();
  view.add(<Node ref={cam} />);
  if (props.shake !== false) taches.push(tremblement(cam, graine, duree));

  const dureeTrace = Math.max(0.35, duree * (props.draw_ratio ?? 0.8));

  // -- le dessin ----------------------------------------------------------------------
  const largeurSvg: number = props.svg_width || 768;
  const hauteurSvg: number = props.svg_height || 768;
  // On cadre sur la **boîte de l'encre**, pas sur la toile du modèle : celle-ci porte les marges
  // blanches que le générateur laisse autour du sujet, et le dessin n'occupait plus que 39 % de
  // la largeur utile (mesuré le 19/09/2026 sur le premier rendu).
  const boite: number[] = props.bbox ?? [0, 0, largeurSvg, hauteurSvg];
  const largeurEncre = Math.max(1, boite[2] - boite[0]);
  const hauteurEncre = Math.max(1, boite[3] - boite[1]);
  const part = texte ? PART_DESSIN_AVEC_TEXTE : PART_DESSIN_SEUL;
  const echelle = Math.min((UX * 2 * part) / largeurEncre, (UY * 2 * part) / hauteurEncre);
  const decalageX = texte ? -UX * 0.40 : 0;

  const dessin = createRef<Node>();
  cam().add(
    <Node
      ref={dessin}
      x={decalageX}
      y={texte ? -H * 0.02 : 0}
      scale={echelle}
      // Le SVG de vtracer a son origine en haut à gauche ; le nœud est centré. Sans ce
      // recentrage, le dessin sort du cadre par le bas à droite.
      offset={[0, 0]}
    />,
  );
  const centre = createRef<Node>();
  dessin().add(
    <Node ref={centre} x={-(boite[0] + boite[2]) / 2} y={-(boite[1] + boite[3]) / 2} />,
  );

  const traits: any[] = [];
  contours.forEach((d: string, index: number) => {
    const trait = createRef<Path>();
    centre().add(
      <Path ref={trait} data={d} fill={null} stroke={marqueur(index + (props.marker ?? 0))}
            lineWidth={EPAISSEUR / echelle} lineCap={'round'} lineJoin={'round'}
            end={0} />,
    );
    traits.push(trait);
  });

  // -- l'horloge de tracé --------------------------------------------------------------
  const longueurs = traits.map((t: any) => Math.max(1, t().arcLength()));
  const total = longueurs.reduce((a: number, b: number) => a + b, 0);
  // Bornes de chaque contour sur l'horloge [0, 1]. Un contour minuscule reçoit tout de même un
  // quantum : sans plancher, la main s'y téléporte en une image et le saut se voit.
  //
  // Le quantum s'efface quand les contours sont peu nombreux. Un dessin en **deux** traits — le
  // cas de plusieurs plans du lot du 19/09 — voyait sinon le second, minuscule, occuper 21 % du
  // temps de tracé : la main s'arrêtait sur un point pendant une seconde.
  const poids = 0.35 * Math.min(1, traits.length / 20);
  const quantum = poids / Math.max(1, traits.length);
  const parts = longueurs.map((l: number) => (1 - poids) * (l / total) + quantum);
  const bornes: Array<[number, number]> = [];
  let curseur = 0;
  for (const p of parts) {
    bornes.push([curseur, curseur + p]);
    curseur += p;
  }

  const avancee = createSignal(0);

  traits.forEach((trait: any, index: number) => {
    const [a, b] = bornes[index];
    trait().end(() => {
      const t = avancee();
      if (t <= a) return 0;
      if (t >= b) return 1;
      return (t - a) / Math.max(1e-6, b - a);
    });
  });

  // Le remplissage est posé **par élément vtracer**, jamais par contour : un élément porte sa
  // règle de remplissage, donc ses trous. Découpé en contours, un anneau se remplirait comme un
  // disque et le dessin virerait à la tache noire — mesuré au premier rendu du 19/09/2026.
  const remplissages: any[] = props.fills ?? [];
  remplissages.forEach((groupe: any) => {
    const membres: number[] = groupe.membres ?? [];
    if (!membres.length) return;
    const debut = Math.min(...membres.map((i: number) => bornes[i]?.[1] ?? 1));
    const fin = Math.max(...membres.map((i: number) => bornes[i]?.[1] ?? 1));
    const plein = createRef<Path>();
    // `insert(…, 0)` : sous tous les traits déjà posés, sinon le plein les recouvre.
    centre().insert(
      <Path ref={plein} data={groupe.d} fill={C.text} opacity={0} lineWidth={0} />, 0,
    );
    plein().opacity(() => {
      const t = avancee();
      const etendue = Math.max(0.04, fin - debut);
      return OPACITE_PLEIN * Math.max(0, Math.min(1, (t - debut) / etendue));
    });
  });

  // Vitesse **constante** : une main dessine à vitesse à peu près régulière. Une courbe en S
  // (premier essai du 19/09) faisait poser le grand contour en trombe puis traîner sur les
  // détails — le contraire de ce qu'on regarde.
  taches.push(tween(dureeTrace, value => avancee(value)));

  // -- la main -------------------------------------------------------------------------
  const mains: any[] = C.mains ?? [];
  if (mains.length && traits.length) {
    const main = mains[(props.hand ?? 0) % mains.length];
    const hauteurMain = H * 0.30;
    const largeurMain = (main.width / main.height) * hauteurMain;
    // La planche est ancrée sur la pointe du feutre : `offset` place ce point sur l'origine du
    // nœud, et l'origine est ce qu'on pose sur le trait.
    const offset: [number, number] = [
      main.tip[0] * 2 - 1,
      main.tip[1] * 2 - 1,
    ];
    const refMain = createRef<Img>();
    cam().add(
      <Img ref={refMain} src={main.src} height={hauteurMain} width={largeurMain}
           offset={offset} opacity={0} />,
    );

    /** Extrémité courante du tracé, dans le repère de `cam` — la main s'y pose. */
    const pointe = () => {
      const t = avancee();
      let index = bornes.findIndex(([a, b]) => t >= a && t < b);
      if (index < 0) index = t <= 0 ? 0 : traits.length - 1;
      const [a, b] = bornes[index];
      const dedans = Math.max(0, Math.min(1, (t - a) / Math.max(1e-6, b - a)));
      const trait = traits[index]();
      const point = trait.getPointAtPercentage(dedans).position;
      const monde = transformVectorAsPoint(point, trait.localToWorld());
      return transformVectorAsPoint(monde, cam().worldToLocal());
    };

    refMain().position(() => {
      const p = pointe();
      // Un léger décalage : la pointe du feutre touche le trait, la planche pend en dessous.
      return new Vector2(p.x + 4, p.y + 3);
    });
    refMain().rotation(() => {
      // La main s'incline doucement au fil du tracé : un feutre parfaitement immobile en angle
      // trahit une image collée sur une courbe.
      const t = avancee();
      return -7 + Math.sin(t * Math.PI * 3 + graine) * 5;
    });

    taches.push((function* () {
      yield* refMain().opacity(1, 0.18, easeOutCubic);
      yield* tween(Math.max(0.05, dureeTrace - 0.34), () => {});
      yield* refMain().opacity(0, 0.16, easeOutCubic);
    })());
  }

  // -- le texte manuscrit ----------------------------------------------------------------
  if (texte) taches.push(manuscrit(cam, texte, dureeTrace, avancee, props));

  if (props.is_sponsor && props.disclosure) bandeau(view, String(props.disclosure));
  return taches;
}

/** Fond papier : grain fin et deux plis, tirés de la graine. Rien qui bouge, rien qui clignote. */
function papier(view: any, graine: number) {
  const r = alea(graine * 131);
  const grain = C.grain ?? 0.05;
  const couche = createRef<Node>();
  view.add(<Node ref={couche} />);
  for (let i = 0; i < 26; i++) {
    couche().add(
      <Rect x={(r() - 0.5) * L} y={(r() - 0.5) * H}
            width={40 + r() * 320} height={1 + r() * 2}
            rotation={(r() - 0.5) * 12} fill={C.text} opacity={grain * (0.3 + r() * 0.7)} />,
    );
  }
  // Marge gauche du cahier : un filet, pas un cadre.
  couche().add(
    <Rect x={-L / 2 + MARGE * 0.55} width={3} height={H} fill={C.accent} opacity={0.18} />,
  );
}

/** Sur-titre de segment, écrit à la main dans le coin haut-gauche. */
function entete(view: any, texte: string) {
  const t = texte.length > 44 ? texte.slice(0, 43) + '…' : texte;
  view.add(
    <Node x={-L / 2 + MARGE} y={-H / 2 + MARGE * 0.72}>
      <Txt x={0} text={t} fontFamily={C.font_body.family} fontWeight={600}
           fontSize={40} fill={C.accent} offset={[-1, 0]} />
      <Rect x={0} y={30} width={Math.min(520, t.length * 17)} height={4} radius={2}
            fill={C.accent} opacity={0.5} offset={[-1, 0]} />
    </Node>,
  );
}

/**
 * Texte manuscrit, découvert de gauche à droite sur la même horloge que le dessin.
 *
 * Il n'est pas tracé lettre par lettre : convertir une police en chemins dans le navigateur
 * demanderait d'embarquer un moteur de fonte, et le gain visuel est nul à 30 images par
 * seconde. Le voile qui recule reproduit exactement ce que fait un outil de whiteboard sur du
 * texte — et il reste calé sur `avancee`, donc sur la main.
 */
function manuscrit(cam: any, texte: string, dureeTrace: number, avancee: any, props: any) {
  const zone = createRef<Node>();
  const voile = createRef<Rect>();
  const largeur = UX * 0.72;
  const corps = Math.max(34, Math.min(84, Math.floor(1500 / Math.max(10, texte.length) + 34)));
  cam().add(
    <Node ref={zone} x={UX * 0.55} opacity={0}>
      <Txt text={texte} fontFamily={C.font_body.family} fontWeight={C.font_body.weight}
           fontSize={corps} fill={C.text} width={largeur} textWrap textAlign={'left'}
           lineHeight={corps * 1.32} offset={[-1, 0]} x={-largeur / 2} />
      <Rect ref={voile} width={largeur + 24} height={H} fill={C.bg} offset={[-1, 0]}
            x={-largeur / 2 - 12} />
    </Node>,
  );
  // Le texte ne commence qu'au tiers du tracé : le dessin pose le sujet, la phrase le nomme.
  const depart = 0.34;
  voile().x(() => {
    const t = Math.max(0, Math.min(1, (avancee() - depart) / (1 - depart)));
    return -largeur / 2 - 12 + t * (largeur + 24);
  });
  return delay(dureeTrace * depart, zone().opacity(1, 0.2, easeOutCubic));
}

/** Bandeau « Publicité » — obligation légale, jamais une décoration : il reste tout le plan. */
function bandeau(view: any, texte: string) {
  const largeur = Math.max(260, texte.length * 26 + 72);
  view.add(
    <Node x={-L / 2 + MARGE + largeur / 2} y={H / 2 - MARGE * 0.6}>
      <Rect width={largeur} height={68} radius={8} fill={C.highlight} />
      <Txt text={texte.toUpperCase()} fontFamily={C.font_body.family} fontWeight={700}
           fontSize={36} fill={C.text} letterSpacing={2} />
    </Node>,
  );
}

/** Flottement de caméra : une page posée sur une table, pas un scan. Trois pixels, pas trente. */
function tremblement(cam: any, graine: number, duree: number) {
  const r = alea(graine * 7717);
  const ampleur = 5 + r() * 4;
  const depart: [number, number] = [(r() - 0.5) * ampleur, (r() - 0.5) * ampleur];
  cam().position(depart).scale(1.006);
  return all(
    cam().position([-depart[0], -depart[1]], Math.max(0.5, duree), linear),
    cam().scale(1.022, Math.max(0.5, duree), linear),
  );
}
