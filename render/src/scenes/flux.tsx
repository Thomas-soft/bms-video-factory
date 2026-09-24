/**
 * FLUX — des étapes reliées, et quelque chose qui circule vraiment entre elles.
 *
 * Les particules suivent le tracé (`getPointAtPercentage`), elles ne glissent pas en ligne
 * droite par-dessus : c'est ce qui fait qu'un schéma de processus se regarde au lieu de se lire.
 */
import {Txt, Node, Line, Circle, Rect} from '@revideo/2d';
import {all, createRef, delay, easeOutCubic, easeInOutCubic, easeOutBack, linear, tween} from '@revideo/core';
import {C, L, H, UX, melanger} from '../charte';
import {alea, socle, surcouches, ajuster} from '../commun';
import {bloc, fleche} from '../figures';

export function flux(view: any, props: any, duree: number) {
  const {cam, taches, graine} = socle(view, props, duree);
  const r = alea(graine * 71);

  const etapes: string[] = (props.steps ?? props.parts ?? []).slice(0, 4);
  // Le nombre de boîtes est celui des étapes **nommées** : compléter à trois posait des
  // boîtes « 1 », « 2 », « 3 » à l'écran (extrait réel du 19/09).
  const combien = Math.max(2, etapes.length);
  // Deux couleurs de charte seulement : un bloc rempli de la couleur du **texte** se lit
  // comme une erreur d'étalonnage, pas comme une étape (essai du 19/09).
  const couleurs = [C.accent, C.highlight];
  const largeur = combien >= 4 ? 380 : 470;
  const hauteur = 190;
  const pasX = Math.min(520, (UX * 2 - largeur) / Math.max(1, combien - 1));

  const positions: [number, number][] = [];
  for (let i = 0; i < combien; i++) {
    const x = -((combien - 1) / 2) * pasX + i * pasX;
    // Les étapes ne sont pas alignées : une ligne droite de boîtes est un tableau, pas un flux.
    const y = (i % 2 === 0 ? -1 : 1) * (combien > 2 ? 155 : 0);
    positions.push([x, y]);
  }

  const blocsRefs: any[] = [];
  const chemins: any[] = [];
  const cheminsRefs: any[] = [];
  const contenu: any[] = [];

  for (let i = 0; i < combien - 1; i++) {
    const ref = createRef<Line>();
    cheminsRefs.push(ref);
    const a = positions[i];
    const b = positions[i + 1];
    const milieu: [number, number] = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + (a[1] < b[1] ? -70 : 70)];
    chemins.push(
      <Line ref={ref} points={[[a[0] + largeur / 2, a[1]], milieu, [b[0] - largeur / 2, b[1]]]}
            stroke={melanger(C.bg, C.accent, 0.8)} lineWidth={6} radius={80} end={0}
            lineCap={'round'} />,
    );
  }
  for (let i = 0; i < combien; i++) {
    const b = bloc(largeur, hauteur, couleurs[i % couleurs.length], String(etapes[i] ?? ''));
    const ref = createRef<Node>();
    blocsRefs.push({ref, cadre: b.cadre});
    contenu.push(<Node ref={ref} x={positions[i][0]} y={positions[i][1]} scale={0}>{b.noeud}</Node>);
  }

  // Les particules : trois par liaison, décalées, qui repartent en boucle jusqu'à la fin du plan.
  const particules: any[] = [];
  const particulesRefs: any[] = [];
  for (let i = 0; i < combien - 1; i++) {
    for (let k = 0; k < 3; k++) {
      const ref = createRef<Circle>();
      particulesRefs.push({ref, lien: i, retard: k * 0.34});
      particules.push(<Circle ref={ref} size={22} fill={C.highlight} opacity={0} />);
    }
  }

  // Le schéma est posé au centre du cadre, pas dans le tiers haut : l'en-tête vit au-dessus.
  cam().add(<Node y={props.heading ? 60 : 0}>{chemins}{particules}{contenu}</Node>);

  const pas = Math.min(0.5, (duree * 0.42) / combien);
  for (let i = 0; i < combien; i++) {
    taches.push(delay(0.15 + i * pas, (function* () {
      yield* blocsRefs[i].ref().scale(1, 0.4, easeOutBack);
      yield* blocsRefs[i].ref().scale(0.97, 0.1);
      yield* blocsRefs[i].ref().scale(1, 0.12, easeOutBack);
    })()));
    if (i < combien - 1) {
      taches.push(delay(0.42 + i * pas, cheminsRefs[i]().end(1, 0.38, easeOutCubic)));
    }
  }

  const tCircule = 0.2 + combien * pas;
  const cycle = Math.max(0.9, Math.min(1.5, duree * 0.2));
  particulesRefs.forEach(({ref, lien, retard}) => {
    taches.push(delay(tCircule + lien * 0.2 + retard, (function* () {
      const fin = Math.max(1, duree - tCircule - lien * 0.2 - retard);
      const tours = Math.max(1, Math.floor(fin / cycle));
      for (let n = 0; n < tours; n++) {
        ref().opacity(1);
        yield* tween(cycle, v => {
          const p = cheminsRefs[lien]().getPointAtPercentage(v);
          ref().position(p.position);
        });
        ref().opacity(0);
      }
    })()));
  });

  // L'étape qui reçoit s'allume au passage : le flux a un effet, il ne décore pas.
  for (let i = 1; i < combien; i++) {
    taches.push(delay(tCircule + i * 0.2 + cycle * 0.9, (function* () {
      yield* blocsRefs[i].cadre().fill(couleurs[i % couleurs.length], 0.25);
      yield* blocsRefs[i].cadre().fill(melanger(couleurs[i % couleurs.length], C.bg, 0.70), 0.5);
    })()));
  }

  if (props.heading) {
    const titre = createRef<Txt>();
    const enTete = createRef<Node>();
    view.add(
      <Node ref={enTete} y={-H / 2 + 150} opacity={0}>
        <Txt ref={titre} text={String(props.heading).toUpperCase()}
             fontFamily={C.font_title.family} fontWeight={C.font_title.weight} fontSize={56}
             fill={C.text} width={UX * 1.7} textWrap textAlign={'center'} />
      </Node>,
    );
    ajuster(titre, UX * 1.7, 120, 28);
    taches.push(enTete().opacity(1, 0.35));
  }

  surcouches(view, props);
  return taches;
}
