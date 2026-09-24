/**
 * QUANTITÉ — cent points, et la part dont parle le script s'en détache pour se regrouper.
 *
 * Un pourcentage écrit en gros est un chiffre ; cent points dont soixante-huit changent de camp
 * est une quantité. C'est la même donnée, et ce n'est pas le même plan.
 */
import {Txt, Node, Circle, Rect} from '@revideo/2d';
import {all, createRef, delay, easeOutCubic, easeInOutCubic, easeOutBack, linear, tween} from '@revideo/core';
import {C, L, H, UX, melanger} from '../charte';
import {alea, socle, surcouches, ajuster} from '../commun';

export function quantite(view: any, props: any, duree: number) {
  const {cam, taches, graine} = socle(view, props, duree);
  const r = alea(graine * 131);

  const part = Math.max(1, Math.min(99, Math.round(Number(props.value ?? 50))));
  const colonnes = 10;
  const lignes = 10;
  const pas = 68;
  const combien = colonnes * lignes;
  const marques = Math.round(combien * part / 100);

  const grille = createRef<Node>();
  const pointsRefs: any[] = [];
  const points: any[] = [];
  const ordre = [...Array(combien).keys()];
  // Les points marqués sont tirés par la graine, pas pris en tête de grille : sinon la part se
  // lit comme une barre de progression, et ce n'est pas ce qu'on montre.
  for (let i = combien - 1; i > 0; i--) {
    const j = Math.floor(r() * (i + 1));
    [ordre[i], ordre[j]] = [ordre[j], ordre[i]];
  }
  const marqueSet = new Set(ordre.slice(0, marques));

  for (let i = 0; i < combien; i++) {
    const ref = createRef<Circle>();
    pointsRefs.push(ref);
    const cx = (i % colonnes - (colonnes - 1) / 2) * pas;
    const cy = (Math.floor(i / colonnes) - (lignes - 1) / 2) * pas;
    points.push(<Circle ref={ref} x={cx} y={cy} size={40} fill={melanger(C.text, C.bg, 0.55)}
                        scale={0} />);
  }
  cam().add(<Node ref={grille} x={-330}>{points}</Node>);

  const compteur = createRef<Txt>();
  const legende = createRef<Txt>();
  const cadre = createRef<Rect>();
  cam().add(
    <Node x={480}>
      <Rect ref={cadre} width={0} height={300} radius={18} stroke={C.highlight} lineWidth={6}
            opacity={0.25} />
      <Txt ref={compteur} y={-30} text={'0%'} fontFamily={C.font_title.family} fontWeight={800}
           fontSize={200} fill={C.highlight} opacity={0} />
      <Txt ref={legende} y={135} text={String(props.label ?? '').toUpperCase()}
           fontFamily={C.font_body.family} fontWeight={700} fontSize={36} fill={C.text}
           width={520} textWrap textAlign={'center'} letterSpacing={1} opacity={0} />
    </Node>,
  );
  ajuster(legende, 520, 150, 22);

  // 1. La grille se pose, colonne par colonne — jamais tout d'un coup.
  const tPose = Math.min(1.1, duree * 0.22);
  for (let i = 0; i < combien; i++) {
    taches.push(delay((i % colonnes) * (tPose / colonnes) + Math.floor(i / colonnes) * 0.02,
                      pointsRefs[i]().scale(1, 0.22, easeOutBack)));
  }

  // 2. La part bascule : couleur, taille, et un pas de côté.
  const tBascule = tPose + 0.45;
  const etalement = Math.min(1.3, Math.max(0.6, duree * 0.28));
  let rang = 0;
  for (let i = 0; i < combien; i++) {
    if (!marqueSet.has(i)) continue;
    const decalage = (rang / Math.max(1, marques)) * etalement;
    rang++;
    taches.push(delay(tBascule + decalage, (function* () {
      yield* all(
        pointsRefs[i]().fill(C.highlight, 0.22),
        pointsRefs[i]().scale(1.35, 0.18, easeOutBack),
      );
      yield* pointsRefs[i]().scale(1.1, 0.16);
    })()));
  }

  // 3. Le chiffre monte au même rythme que les points changent : les deux disent la même chose.
  taches.push(delay(tBascule, (function* () {
    compteur().opacity(1);
    yield* all(
      cadre().width(640, 0.5, easeOutCubic),
      tween(etalement + 0.2, v => compteur().text(`${Math.round(part * easeOutCubic(v))}%`),
            () => compteur().text(`${part}%`)),
    );
    yield* legende().opacity(1, 0.3);
    yield* all(compteur().scale(1.08, 0.14), cadre().opacity(0.7, 0.14));
    yield* all(compteur().scale(1, 0.2), cadre().opacity(0.35, 0.3));
  })()));

  // 4. La grille respire jusqu'à la fin.
  taches.push(delay(tBascule, grille().rotation(-2.5, Math.max(1, duree - tBascule), linear)));

  surcouches(view, props);
  return taches;
}
