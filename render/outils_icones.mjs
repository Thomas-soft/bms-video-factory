// Extrait un sous-ensemble d'icônes Tabler (MIT) en un module TS committé.
// Le paquet @tabler/icons pèse 48 Mo ; seules les icônes nommées ici entrent au dépôt.
// Relancer après toute modification de LISTE : `node outils_icones.mjs`.
import {readFileSync, writeFileSync} from 'node:fs';

const LISTE = [
  'brain', 'heart', 'dna', 'atom', 'microscope', 'flask', 'bolt', 'battery',
  'clock', 'calendar', 'chart-bar', 'trending-up', 'trending-down', 'scale',
  'eye', 'bulb', 'shield', 'alert-triangle', 'check', 'x', 'moon', 'sun',
  'droplet', 'flame', 'leaf', 'world', 'users', 'user', 'book', 'search',
  'target', 'tree', 'pill', 'stethoscope', 'activity', 'apple', 'coin',
  'building-bank', 'plant', 'wind', 'temperature', 'hourglass',
];

const version = JSON.parse(readFileSync('node_modules/@tabler/icons/package.json', 'utf8')).version;
const sortie = [];
for (const nom of LISTE) {
  const brut = readFileSync(`node_modules/@tabler/icons/icons/outline/${nom}.svg`, 'utf8');
  // Les sous-chemins sont **concaténés en un seul `d`**. Le composant `Path` de Revideo centre
  // chaque chemin sur sa propre boîte : deux `Path` frères perdraient leur alignement relatif.
  // Un seul `d` garde la géométrie de l'icône et donne une boîte unique à centrer.
  const chemins = [...brut.matchAll(/<path[^>]*\sd="([^"]+)"/g)]
    .map(m => m[1].trim())
    .filter(d => d && d !== 'M0 0h24v24H0z');
  if (chemins.length === 0) throw new Error(`icône sans chemin : ${nom}`);
  sortie.push(`  '${nom}': ${JSON.stringify(chemins.join(' '))},`);
}
writeFileSync('src/icons.ts', `// Icônes Tabler ${version} — MIT, © Paweł Kuna. Extraites par \`outils_icones.mjs\`.
// Repère 24×24, trait seul : la couleur et l'épaisseur viennent de la charte, jamais d'ici.
// https://github.com/tabler/tabler-icons — licence recopiée dans outils/LICENCES.md.
export const TABLER_VERSION = '${version}';
export const ICONES: Record<string, string> = {
${sortie.join('\n')}
};
export const NOMS_ICONES = Object.keys(ICONES);
`);
console.log(`${LISTE.length} icônes écrites dans src/icons.ts (Tabler ${version})`);
