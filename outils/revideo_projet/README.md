# Projet Revideo de référence (rescapé du banc de l'étape 5.2)

`benchmarks/revideo_test/` a été purgé en fin d'étape 5.2 (node_modules 0,28 Go,
Chromium 0,58 Go). Ces trois fichiers sont la configuration **mesurée
fonctionnelle** : 98,4 images/s en 1080p30, rendu headless, sans interface.

Réinstallation (étape 30.1) :

```sh
mkdir -p revideo_test/src && cp package.json render.mjs revideo_test/
cp project.tsx revideo_test/src/ && cd revideo_test
PUPPETEER_CACHE_DIR=../../models/puppeteer DISABLE_TELEMETRY=true npm install
npm install --no-audit @revideo/vite-plugin@0.11.0 @revideo/ui@0.11.0 vite@^5
node render.mjs          # sort dans output/out.mp4
```

**Trois pièges payés en séances d'essai, à ne pas repayer :**
1. `@revideo/renderer` ne tire **ni** `@revideo/vite-plugin` **ni** `@revideo/ui` :
   il faut les installer à la main, sinon `MODULE_NOT_FOUND`.
2. En 0.11, `makeScene2D` prend **un nom en premier argument** :
   `makeScene2D('texte', function* (view) {…})`. Sans lui, le rendu échoue sur
   `Cannot read properties of undefined (reading 'name')`, côté navigateur, sans
   indiquer la cause.
3. Le **premier** `node render.mjs` optimise les dépendances Vite, recharge la
   page et meurt sur `Navigation timeout of 30000 ms exceeded`. Le second passe.
   Prévoir une relance automatique.

Sortie réelle : `output/out.mp4`, pas `out.mp4` — `outFile` est relatif au
dossier de sortie.
