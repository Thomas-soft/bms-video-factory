/**
 * SYSTÈME — un centre, des satellites qui tournent réellement, un lien qui vient en désigner un.
 *
 * Le mouvement n'est pas décoratif : les orbites tournent pendant toute la durée du plan, à des
 * vitesses différentes. C'est la scène qui tient le mieux les plans longs, parce qu'elle ne
 * « finit » jamais.
 */
import {Txt, Node, Line, Circle, Rect} from '@revideo/2d';
import {all, createRef, delay, easeOutCubic, easeOutBack, linear} from '@revideo/core';
import {C, L, H, UX, melanger} from '../charte';
import {alea, socle, surcouches, ajuster} from '../commun';
import {astre} from '../figures';

export function systeme(view: any, props: any, duree: number) {
  const {cam, taches, graine} = socle(view, props, duree);
  const r = alea(graine * 47);

  const noms: string[] = (props.satellites ?? props.parts ?? []).slice(0, 4);
  const combien = Math.max(2, noms.length || 3);
  const centreNom = String(props.centre ?? props.heading ?? '');
  const couleurs = [C.highlight, C.accent, C.text, C.highlight];
  const departs: number[] = [];

  const centre = astre(165, C.accent, graine + 3);
  const centreRef = createRef<Node>();
  const orbites: any[] = [];
  const orbitesRefs: any[] = [];
  const satsRefs: any[] = [];
  const etiqRefs: any[] = [];

  for (let i = 0; i < combien; i++) {
    const rayon = 300 + i * 160;
    const orbite = createRef<Node>();
    const sat = createRef<Node>();
    const etiq = createRef<Node>();
    orbitesRefs.push(orbite);
    satsRefs.push(sat);
    etiqRefs.push(etiq);
    const corps = astre(66 + r() * 30, couleurs[i % couleurs.length], graine + i * 11, false);
    const depart = r() * 360;
    departs.push(depart);
    orbites.push(
      <Node ref={orbite} rotation={depart}>
        <Circle size={rayon * 2} stroke={melanger(C.bg, C.accent, 0.75)} lineWidth={4}
                lineDash={[12, 14]} opacity={0.85} scale={0} />
        <Node ref={sat} x={rayon} scale={0} opacity={0}>
          {corps.noeud}
          {/* L'étiquette tourne à l'envers pour rester lisible : elle suit le satellite, elle
              ne tourne pas avec l'orbite. */}
          {/* L'étiquette annule la rotation de l'orbite, **y compris son décalage de départ** :
              sans cela elle penche d'un angle arbitraire tiré par la graine (essai du 19/09). */}
          <Node ref={etiq} opacity={0} y={-96} rotation={-depart}>
            {/* Cartouche opaque : sans fond, deux étiquettes d'orbites voisines se superposent
                et deviennent illisibles (extrait réel du 19/09). */}
            <Rect width={String(noms[i] ?? '').length * 17 + 34} height={46} radius={23}
                  fill={C.bg} stroke={couleurs[i % couleurs.length]} lineWidth={3} opacity={0.94} />
            <Txt text={String(noms[i] ?? '').slice(0, 18).toUpperCase()}
                 fontFamily={C.font_body.family} fontWeight={700} fontSize={26}
                 fill={couleurs[i % couleurs.length]} letterSpacing={1} />
          </Node>
        </Node>
      </Node>,
    );
  }

  cam().add(
    <Node>
      {orbites}
      <Node ref={centreRef} scale={0}>{centre.noeud}</Node>
    </Node>,
  );

  const nomCentre = createRef<Txt>();
  if (centreNom) {
    cam().add(
      <Txt ref={nomCentre} y={H * 0.40} text={centreNom.toUpperCase()}
           fontFamily={C.font_title.family} fontWeight={C.font_title.weight} fontSize={52}
           fill={C.text} opacity={0} />,
    );
    ajuster(nomCentre, 420, 120, 26);
  }

  taches.push((function* () {
    yield* centreRef().scale(1, 0.5, easeOutBack);
    if (centreNom) yield* nomCentre().opacity(1, 0.3);
  })());

  const pas = Math.min(0.45, (duree * 0.4) / combien);
  for (let i = 0; i < combien; i++) {
    const cercle = orbitesRefs[i]().children()[0] as any;
    taches.push(delay(0.3 + i * pas, (function* () {
      yield* cercle.scale(1, 0.4, easeOutCubic);
      yield* all(satsRefs[i]().scale(1, 0.35, easeOutBack), satsRefs[i]().opacity(1, 0.25));
      if (noms[i]) yield* etiqRefs[i]().opacity(1, 0.25);
    })()));
    // La rotation dure tout le plan : sens alternés, vitesses différentes, rien ne se fige.
    const tours = (i % 2 === 0 ? 1 : -1) * (26 + (combien - i) * 16);
    taches.push(delay(0.3 + i * pas, all(
      orbitesRefs[i]().rotation(departs[i] + tours, Math.max(1, duree), linear),
      etiqRefs[i]().rotation(-(departs[i] + tours), Math.max(1, duree), linear),
    )));
  }

  // Un satellite est désigné à mi-plan : le plan a un sujet, pas seulement un décor.
  if (duree > 3.5 && noms.length > 0) {
    const cible = satsRefs[Math.min(satsRefs.length - 1, 1)];
    const halo = createRef<Circle>();
    cible().add(<Circle ref={halo} size={0} stroke={C.highlight} lineWidth={6} opacity={0} />);
    taches.push(delay(duree * 0.55, (function* () {
      halo().opacity(1);
      yield* all(halo().size(260, 0.6, easeOutCubic), halo().opacity(0, 0.6));
      halo().size(0).opacity(1);
      yield* all(halo().size(260, 0.6, easeOutCubic), halo().opacity(0, 0.6));
    })()));
  }

  surcouches(view, props);
  return taches;
}
