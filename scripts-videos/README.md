# Scripts des vidéos

Texte intégral des deux vidéos de démonstration, tel qu'il a été écrit par le pipeline
puis enregistré en voix off. Rien n'est réécrit à la main : ces `.txt` sont produits
depuis `script.json` et `voice/timings.json` de chaque run, par
`outils/script_txt.py`.

| Fichier | Langue | Segments | Mots | Durée de la voix |
|---|---|---|---|---|
| `script-bms-science-FR.txt` | français | 28 | 1 558 | 12 min 17 s |
| `script-bms-science-EN.txt` | anglais | 28 | 1 405 | 11 min 07 s |

Chaque segment porte son rôle éditorial (`hook`, `contexte`, `point`, `conclusion`…),
son horodatage réel dans la piste voix, son texte à l'écran et ses sources.

**L'anglais est la langue retenue pour le lancement** (arbitrage d'Alek, 15/09/2026).
Le français existe pour que le multi-langues soit exercé par les tests.

Refaire ces fichiers après un nouveau run :

```sh
python3 outils/script_txt.py workspace/runs/<id-du-run>
```
