/**
 * CHRONOLOGIE — la ligne défile, les événements passent devant un repère fixe.
 *
 * C'est la caméra qui voyage, pas les jalons qui apparaissent : le plan a un sens de lecture et
 * une durée vécue. Un simple empilement de dates n'aurait été qu'une liste de plus.
 */
import {Txt, Node, Line, Circle, Rect} from '@revideo/2d';
import {all, createRef, delay, easeOutCubic, easeInOutCubic, easeOutBack, linear} from '@revideo/core';
import {C, L, H, UX, melanger} from '../charte';
import {socle, surcouches, ajuster, taillePourTenir} from '../commun';

export function chronologie(view: any, props: any, duree: number) {
  const {cam, taches, graine} = socle(view, props, duree);

  const evenements: Array<{label: string; when?: string}> =
    (props.events ?? (props.parts ?? []).map((l: string) => ({label: l}))).slice(0, 5);
  const combien = Math.max(2, evenements.length || 3);
  const couleurs = [C.accent, C.highlight, C.text];
  const pas = 720;
  const ruban = createRef<Node>();
  const ligne = createRef<Line>();
  const jalons: any[] = [];
  const jalonsRefs: any[] = [];

  for (let i = 0; i < combien; i++) {
    const ref = createRef<Node>();
    jalonsRefs.push(ref);
    const couleur = couleurs[i % couleurs.length];
    const haut = i % 2 === 0;
    const e = evenements[i] ?? {label: ''};
    jalons.push(
      <Node ref={ref} x={i * pas} opacity={0}>
        <Line points={[[0, 0], [0, haut ? -130 : 130]]} stroke={couleur} lineWidth={5} />
        <Circle size={34} fill={couleur} />
        <Node y={haut ? -230 : 230}>
          <Rect width={520} height={132} radius={14} fill={melanger(couleur, C.bg, 0.78)}
                stroke={couleur} lineWidth={4} />
          {e.when ? (
            <Txt y={-36} text={String(e.when).toUpperCase()} fontFamily={C.font_body.family}
                 fontWeight={800} fontSize={34} fill={couleur} letterSpacing={2} />
          ) : null}
          <Txt y={e.when ? 24 : 0} text={String(e.label ?? '')} fontFamily={C.font_body.family}
               fontWeight={600} fontSize={taillePourTenir(String(e.label ?? ''), 470, 40, 22)}
               fill={C.text} width={470} textWrap textAlign={'center'} />
        </Node>
      </Node>,
    );
  }

  const repere = createRef<Node>();
  cam().add(
    <Node ref={ruban} x={UX * 0.55}>
      <Line ref={ligne} points={[[-500, 0], [(combien - 1) * pas + 500, 0]]}
            stroke={melanger(C.bg, C.text, 0.32)} lineWidth={8} lineCap={'round'} />
      {jalons}
    </Node>,
  );
  // Le repère est fixe, au tiers gauche : c'est lui qui donne le « maintenant » du plan.
  view.add(
    <Node ref={repere} x={-L / 2 + UX * 0.55 + 96} opacity={0}>
      <Line points={[[0, -H * 0.42], [0, H * 0.42]]} stroke={C.highlight} lineWidth={4}
            lineDash={[16, 12]} opacity={0.55} />
      <Circle size={26} stroke={C.highlight} lineWidth={5} />
    </Node>,
  );

  taches.push(repere().opacity(1, 0.4));
  const parcours = Math.max(1.2, duree - 0.8);
  taches.push(delay(0.25, ruban().x(UX * 0.55 - (combien - 1) * pas, parcours, easeInOutCubic)));

  // Chaque jalon apparaît juste avant d'atteindre le repère, et se rehausse en le croisant.
  for (let i = 0; i < combien; i++) {
    const tArrivee = 0.25 + (i / Math.max(1, combien - 1)) * parcours;
    taches.push(delay(Math.max(0, tArrivee - 0.5), jalonsRefs[i]().opacity(1, 0.3)));
    taches.push(delay(Math.max(0.05, tArrivee - 0.05), (function* () {
      yield* jalonsRefs[i]().scale(1.12, 0.18, easeOutBack);
      yield* jalonsRefs[i]().scale(1, 0.25);
    })()));
    // Un jalon qui a dépassé le repère **s'efface** : tranché par le bord du cadre, il se lit
    // comme un défaut de montage (essai du 19/09).
    if (i < combien - 1) {
      const sortie = 0.25 + ((i + 0.72) / Math.max(1, combien - 1)) * parcours;
      taches.push(delay(Math.min(duree - 0.2, sortie), jalonsRefs[i]().opacity(0, 0.45)));
    }
  }

  surcouches(view, props);
  return taches;
}
