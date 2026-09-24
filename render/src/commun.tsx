/**
 * Outillage partagé par les scènes : générateur pseudo-aléatoire par graine, fond animé,
 * bandeau de divulgation, titraille, découpe des mots en blocs de lecture.
 *
 * Deux règles tenues ici, et nulle part ailleurs :
 * 1. **Tout le temporel est absolu.** Une tâche est planifiée par `delay(t, …)` sur l'horodatage
 *    du mot, jamais par enchaînement : sur un plan de 12 s, l'enchaînement dérive.
 * 2. **Rien de visible ne sort de la zone utile** (`UX`/`UY`). Une taille de texte est réduite
 *    tant que le bloc dépasse, plutôt que rognée au montage.
 */
import {Rect, Txt, Node, Line, Circle} from '@revideo/2d';
import {createRef, linear, easeOutCubic, easeOutBack, easeInOutCubic, all, delay, waitFor, tween} from '@revideo/core';
import {C, L, H, UX, UY, MARGE, melanger} from './charte';

/**
 * Couleur de fond d'un plan. Quatre teintes de la charte, en rotation : deux plans voisins n'ont
 * jamais la même.
 *
 * Ce n'est pas une coquetterie. Au premier montage complet du 19/09, **27 plans sur 114** étaient
 * détectés par PySceneDetect — exactement les 26 `dip_black` plus un. Une coupe entre deux scènes
 * qui commencent et finissent sur le même fond vide ne se voit ni d'un détecteur, ni d'un œil :
 * la vidéo « clignote » sur un fond identique cent quatorze fois. Un fond qui change à chaque
 * plan rend la coupe visible, et c'est aussi la rupture de couleur que le verdict du 16/09
 * réclamait.
 */
export function fondCouleur(variante: number): string {
  // Les quatre teintes sont tirées de la charte et d'elle seule. `text_outline` en est exclu :
  // sur cette charte il vaut #101010 contre un fond #0d1117, donc une variante invisible.
  const v = ((variante % 4) + 4) % 4;
  if (v === 1) return melanger(C.bg, C.accent, 0.30);
  if (v === 2) return melanger(C.bg, C.highlight, 0.17);
  if (v === 3) return melanger(C.bg, C.text, 0.17);
  return C.bg;
}

/** Suite déterministe : le même plan rejoué donne la même composition, au pixel près. */
export function alea(graine: number) {
  let etat = (graine >>> 0) || 1;
  return () => {
    etat ^= etat << 13; etat >>>= 0;
    etat ^= etat >> 17;
    etat ^= etat << 5; etat >>>= 0;
    return etat / 4294967296;
  };
}

/** Un mot de `words.json`, réexprimé en secondes depuis le début du plan. */
export type Mot = {w: string; t: number; e: number};

/**
 * Regroupe les mots en blocs de lecture : ponctuation, silence de plus de 0,4 s, plafond de mots.
 * Un bloc est ce qu'un œil lit d'un coup ; au-delà de cinq mots ce n'est plus de la typographie
 * cinétique, c'est un sous-titre.
 */
export function blocs(mots: Mot[], max = 4): Mot[][] {
  const out: Mot[][] = [];
  let cur: Mot[] = [];
  for (let i = 0; i < mots.length; i++) {
    cur.push(mots[i]);
    const suiv = mots[i + 1];
    const ponct = /[.,!?;:»)]$/.test(mots[i].w);
    const trou = suiv ? suiv.t - mots[i].e : 99;
    if (cur.length >= max || (ponct && cur.length >= 2) || trou > 0.4) {
      out.push(cur);
      cur = [];
    }
  }
  if (cur.length) out.push(cur);
  return out;
}

/**
 * Taille de départ estimée : 0,62 em par caractère (Inter en capitales, avec interlettrage).
 * **Une estimation ne suffit pas** — le premier rendu du 19/09 a sorti « BUT THERE IS A CATCH »
 * hors cadre avec un facteur 0,54. C'est `ajuster()` qui garantit le cadre ; ceci n'évite que
 * des itérations.
 */
export function taillePourTenir(texte: string, largeurMax: number, max: number, min = 24): number {
  const estimee = largeurMax / Math.max(1, texte.length * 0.62);
  return Math.max(min, Math.min(max, Math.floor(estimee)));
}

/**
 * Réduit la police d'un nœud **mesuré** jusqu'à ce qu'il tienne dans la boîte donnée.
 *
 * Appelé après `view.add()`, donc après le calcul de mise en page : la largeur et la hauteur
 * rendues sont connues, il n'y a plus rien à estimer. C'est la seule garantie d'absence de
 * débordement, et elle vaut pour toutes les scènes.
 */
export function ajuster(ref: any, largeurMax: number, hauteurMax: number, min = 22): void {
  for (let i = 0; i < 14; i++) {
    const taille = ref().fontSize();
    const l = ref().width();
    const h = ref().height();
    if ((l <= largeurMax && h <= hauteurMax) || taille <= min) return;
    const facteur = Math.min(largeurMax / Math.max(1, l), hauteurMax / Math.max(1, h), 0.94);
    const suivante = Math.max(min, Math.floor(taille * facteur));
    if (suivante >= taille) return;
    ref().fontSize(suivante);
  }
}

/**
 * Fond animé discret : trois partis tirés par la graine, tous à moins de 12 % d'opacité.
 * Il donne du mouvement à un plan statique sans disputer la lecture au texte — c'est la même
 * raison qui fait glisser une barre d'accent dans le moteur « cartes ».
 */
export function fond(view: any, graine: number, duree: number, variante = 0) {
  const r = alea(graine);
  const parti = graine % 3;
  const calque = createRef<Node>();
  // Les motifs se détachent du fond **du plan**, pas de celui de la charte : sur un fond déjà
  // teinté d'accent, une bande d'accent ne se verrait plus.
  const base = fondCouleur(variante);
  const teinte = melanger(base, (variante % 4) === 1 ? C.highlight : C.accent, 0.34);
  const elements: any[] = [];

  if (parti === 0) {
    // Grille qui dérive : le repère se déplace, les traits ne bougent pas les uns par rapport
    // aux autres — le mouvement se sent sans se regarder.
    for (let i = -9; i <= 9; i++) {
      elements.push(<Line points={[[i * 150, -H], [i * 150, H]]} stroke={teinte} lineWidth={1} opacity={0.40} />);
    }
    for (let j = -6; j <= 6; j++) {
      elements.push(<Line points={[[-L, j * 150], [L, j * 150]]} stroke={teinte} lineWidth={1} opacity={0.40} />);
    }
  } else if (parti === 1) {
    // Bandes diagonales lentes.
    for (let i = 0; i < 7; i++) {
      elements.push(
        <Rect x={-L + i * 340} width={150} height={H * 2.4} rotation={22}
              fill={teinte} opacity={0.10 + r() * 0.05} />,
      );
    }
  } else {
    // Pointillé : 40 points de deux tailles, répartis par la graine.
    for (let i = 0; i < 40; i++) {
      elements.push(
        <Rect x={(r() - 0.5) * L * 1.2} y={(r() - 0.5) * H * 1.2}
              width={r() > 0.7 ? 10 : 5} height={r() > 0.7 ? 10 : 5} radius={5}
              fill={r() > 0.5 ? C.accent : C.highlight} opacity={0.10 + r() * 0.08} />,
      );
    }
  }

  view.add(<Node ref={calque}>{elements}</Node>);
  const dx = (r() - 0.5) * 150;
  const dy = (r() - 0.5) * 110;
  return calque().position([dx, dy], duree, linear);
}

/**
 * Bandeau de divulgation d'un plan sponsorisé. Sans fondu et sur toute la durée du plan : la loi
 * française 2023-451 exige la mention **pendant** la promotion, pas après une rampe d'alpha
 * (`docs/CONFORMITE.md` § 3). Le texte est passé par le pipeline, jamais écrit ici.
 */
export function divulgation(view: any, texte: string) {
  const largeur = Math.max(260, texte.length * 26 + 72);
  view.add(
    <Node x={-L / 2 + MARGE + largeur / 2} y={-H / 2 + MARGE + 34}>
      <Rect width={largeur} height={68} radius={10} fill={C.highlight} />
      <Txt text={texte.toUpperCase()} fontFamily={C.font_body.family} fontWeight={700}
           fontSize={36} fill={C.bg} letterSpacing={2} />
    </Node>,
  );
}

/** Titraille de coin : filet d'accent + sur-titre. Optionnelle, jamais sur une citation. */
export function titraille(view: any, texte: string) {
  if (!texte) return;
  const t = texte.length > 46 ? texte.slice(0, 45) + '…' : texte;
  view.add(
    <Node x={-L / 2 + MARGE} y={H / 2 - MARGE + 6}>
      <Rect width={14} height={44} fill={C.highlight} offset={[-1, 0]} />
      <Txt x={34} text={t.toUpperCase()} fontFamily={C.font_body.family} fontWeight={600}
           fontSize={28} fill={C.accent} letterSpacing={3} offset={[-1, 0]} />
    </Node>,
  );
}

/** Volet d'ouverture : une barre d'accent balaie le cadre. Sert de rupture entre deux partis. */
export function* balayage(refBarre: any, couleur: string) {
  refBarre().fill(couleur).opacity(1).offset([-1, 0]).x(-L / 2).width(0);
  yield* refBarre().width(L, 0.16, easeOutCubic);
  refBarre().offset([1, 0]).x(L / 2);
  yield* refBarre().width(0, 0.20, easeOutCubic);
  refBarre().opacity(0);
}

/* ==========================================================================================
 * Socle d'une scène construite
 *
 * Verdict de Thomas du 16/09/2026, qui est le critère de ce moteur et pas une préférence :
 * « ce qui est perçu comme animation n'est pas le déplacement, c'est la construction et la
 * transformation » — « il faut qu'il se passe quelque chose à l'écran, pas que quelque chose
 * s'y déplace ». Et sur la typographie cinétique : « y'a trop trop de texte pour presque
 * aucune image, aucune animation, que du texte quasiment ».
 *
 * Conséquences tenues ici :
 * 1. Toute scène vit dans une **caméra** qui ne s'arrête jamais.
 * 2. Le fond porte des **couches en parallaxe** : il y a de la profondeur, pas un aplat.
 * 3. Le texte n'est plus la substance d'un plan — il est ponctuation ou étiquette.
 * ========================================================================================== */

/** Mouvement de caméra d'un plan : cinq partis, tirés par la graine, jamais nul. */
export function mouvementCamera(cam: any, graine: number, duree: number) {
  const r = alea(graine * 7919);
  const parti = graine % 5;
  const d = Math.max(0.5, duree);
  if (parti === 0) {                                   // poussée avant
    cam().scale(1);
    return cam().scale(1.13, d, linear);
  }
  if (parti === 1) {                                   // recul
    cam().scale(1.12);
    return cam().scale(1, d, linear);
  }
  if (parti === 2) {                                   // dérive latérale + légère poussée
    cam().position([(r() - 0.5) * 120, (r() - 0.5) * 60]).scale(1.04);
    return all(cam().position([(r() - 0.5) * 120, (r() - 0.5) * 60], d, linear),
               cam().scale(1.10, d, linear));
  }
  if (parti === 3) {                                   // bascule très lente
    cam().rotation(-1.2).scale(1.06);
    return all(cam().rotation(1.2, d, linear), cam().scale(1.12, d, linear));
  }
  cam().scale(1.15).position([40, 20]);                // plongée vers le centre
  return all(cam().scale(1.02, d, linear), cam().position([-20, -10], d, linear));
}

/**
 * Socle commun : fond en parallaxe, caméra, et la liste de tâches à laquelle la scène ajoute
 * les siennes. Tout ce qu'une scène dessine va dans `cam()`, jamais dans `view`.
 */
export function socle(view: any, props: any, duree: number) {
  const graine: number = props.seed ?? 1;
  const taches: any[] = [];
  const cam = createRef<Node>();
  taches.push(fond(view, graine, duree, props.bg_variant ?? 0));
  taches.push(...parallaxe(view, graine, duree, props.bg_variant ?? 0));
  view.add(<Node ref={cam} />);
  taches.push(mouvementCamera(cam, graine, duree));
  return {cam, taches, graine};
}

/** Surcouches d'interface : elles ne suivent pas la caméra, sinon elles ne seraient pas lisibles. */
export function surcouches(view: any, props: any) {
  if (props.title) titraille(view, props.title);
  if (props.is_sponsor && props.disclosure) divulgation(view, props.disclosure);
}

/** Trois couches de formes lentes à des vitesses différentes : la profondeur du plan. */
export function parallaxe(view: any, graine: number, duree: number, variante: number) {
  const r = alea(graine * 104729);
  const base = fondCouleur(variante);
  const taches: any[] = [];
  for (let couche = 0; couche < 3; couche++) {
    const ref = createRef<Node>();
    const teinte = melanger(base, couche === 1 ? C.highlight : C.accent, 0.18 + couche * 0.10);
    const formes: any[] = [];
    const combien = 5 - couche;
    for (let i = 0; i < combien; i++) {
      const taille = (120 + r() * 260) * (1 + couche * 0.7);
      const x = (r() - 0.5) * L * 1.5;
      const y = (r() - 0.5) * H * 1.5;
      formes.push(r() > 0.5
        ? <Circle x={x} y={y} size={taille} stroke={teinte} lineWidth={3 + couche * 2} opacity={0.5} />
        : <Rect x={x} y={y} width={taille} height={taille} radius={taille * 0.18}
                rotation={r() * 40 - 20} stroke={teinte} lineWidth={3 + couche * 2} opacity={0.42} />);
    }
    view.add(<Node ref={ref} scale={1 + couche * 0.15}>{formes}</Node>);
    const vitesse = (couche + 1) * 26;
    taches.push(ref().position([(r() - 0.5) * vitesse * 2, (r() - 0.5) * vitesse], duree, linear));
  }
  return taches;
}

/**
 * Étiquette d'annotation : un point sur l'objet, un trait coudé, un mot aligné en colonne.
 *
 * Le trait est **coudé** (oblique puis horizontal) et le mot est ancré du côté du cadre : c'est
 * ce qui garde les étiquettes alignées et **dans la zone utile**. Au premier essai du 19/09,
 * « CRUST » sortait du cadre par la droite.
 */
export function annotation(
  cible: [number, number], vers: [number, number], texte: string, couleur: string,
) {
  const point = createRef<Circle>();
  const trait = createRef<Line>();
  const mot = createRef<Txt>();
  const droite = vers[0] >= cible[0];
  // Le coude, puis le mot qui pousse **vers l'intérieur** du cadre.
  const coude: [number, number] = [vers[0] - (droite ? 120 : -120), vers[1]];
  const xMot = droite ? Math.min(vers[0], UX) : Math.max(vers[0], -UX);
  const court = texte.length > 18 ? texte.slice(0, 17) + '…' : texte;
  const noeud = (
    <Node>
      <Circle ref={point} x={cible[0]} y={cible[1]} size={18} fill={couleur} scale={0} />
      <Line ref={trait} points={[cible, coude, [xMot, vers[1]]]} stroke={couleur} lineWidth={4}
            end={0} lineJoin={'round'} />
      <Txt ref={mot} x={xMot} y={vers[1] - 30} offset={[droite ? 1 : -1, 0]}
           text={court.toUpperCase()} fontFamily={C.font_body.family} fontWeight={700}
           fontSize={34} fill={couleur} letterSpacing={2} opacity={0} />
    </Node>
  );
  const jouer = function* () {
    yield* all(point().scale(1, 0.22, easeOutCubic), trait().end(1, 0.34, easeOutCubic));
    yield* mot().opacity(1, 0.22);
  };
  return {noeud, jouer};
}
