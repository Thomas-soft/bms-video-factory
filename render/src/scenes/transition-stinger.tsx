/**
 * Rupture — quatre volets d'accent balaient le cadre, portent le mot-charnière, puis sortent et
 * le laissent seul sur le fond. Les plans marqués `interrupt` par l'étape 16 s'en servent pour
 * **faire sentir** la cassure de rythme.
 *
 * La première version gardait les volets pendant toute la durée du plan : sur un plan de 6 s,
 * cela donnait six secondes d'aplat, donc un plan mort, et la règle de choix devait alors
 * interdire la scène au-delà de 3,5 s. Les volets tiennent maintenant une seconde, quelle que
 * soit la durée, et la scène est employable partout.
 */
import {Rect, Txt, Node} from '@revideo/2d';
import {all, createRef, delay, waitFor, easeOutExpo, easeInExpo, easeOutBack, linear} from '@revideo/core';
import {C, L, H, UX} from '../charte';
import {alea, fond, divulgation, taillePourTenir, ajuster} from '../commun';

export function transitionStinger(view: any, props: any, duree: number) {
  const graine: number = props.seed ?? 1;
  const taches: any[] = [fond(view, graine, duree, props.bg_variant ?? 0)];
  const mot = String(props.on_screen_text ?? props.heading ?? props.title ?? '').toUpperCase();

  const texte = createRef<Node>();
  const mot2 = createRef<Txt>();
  const taille = taillePourTenir(mot, UX * 1.6, 170, 50);
  view.add(
    <Node ref={texte} opacity={0} scale={0.86}>
      {/* Blanc cerné de noir : sur des volets bleus **et** jaunes, une seule couleur de texte ne
          peut pas être lisible sur les deux (extrait réel du 19/09). Le cerné règle les deux. */}
      <Txt ref={mot2} text={mot} fontFamily={C.font_title.family} fontWeight={800} fontSize={taille}
           fill={'#ffffff'} stroke={'#0c0c0c'} lineWidth={14} strokeFirst
           width={UX * 1.7} textWrap textAlign={'center'} letterSpacing={4} />
    </Node>,
  );
  if (mot) ajuster(mot2, UX * 1.7, H * 0.5, 44);

  // Volets par-dessus le texte : ils entrent par le haut, le découvrent, puis ressortent par le bas.
  const volets = [createRef<Rect>(), createRef<Rect>(), createRef<Rect>(), createRef<Rect>()];
  const couleurs = [C.accent, C.highlight, C.accent, C.highlight];
  const largeur = L / 4;
  volets.forEach((ref, i) => {
    view.add(
      <Rect ref={ref} width={largeur + 6} height={H * 1.5} x={-L / 2 + largeur * (i + 0.5)}
            y={-H * 1.5} fill={couleurs[i]} opacity={0.94} rotation={6} />,
    );
  });

  const entree = 0.34;
  const tenue = Math.min(0.5, Math.max(0.16, duree * 0.12));
  const sortie = 0.36;
  volets.forEach((ref, i) => {
    taches.push(delay(i * 0.045, ref().y(0, entree, easeOutExpo)));
    taches.push(delay(entree + tenue + i * 0.05, ref().y(H * 1.5, sortie, easeInExpo)));
  });
  if (mot) {
    taches.push(delay(entree * 0.75, (function* () {
      yield* all(texte().opacity(1, 0.14), texte().scale(1, 0.3, easeOutBack));
    })()));
    // Le mot passe du fond clair des volets au texte de charte au moment où ils le quittent :
    // une seule lecture, deux traitements, aucune coupure.

    taches.push(delay(entree + tenue + sortie,
      texte().scale(1.05, Math.max(0.3, duree - entree - tenue - sortie), linear)));
  }

  if (props.is_sponsor && props.disclosure) divulgation(view, props.disclosure);
  return taches;
}
