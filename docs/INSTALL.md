# INSTALL — monter l'usine depuis zéro

Cible : **macOS 14+ sur Apple Silicon** (mesuré sur MacBook Air M2, 16 Go, macOS 27.0).
Rien de ce document ne suppose de GPU NVIDIA ni de compte payant.

**Durée** : ~20 minutes d'installation, **hors téléchargement des modèles** (compter
2 à 4 heures de plus la première fois, selon le débit — 21,5 Go de poids).
**Disque** : prévoir **35 Go libres** au départ ; le plancher absolu est de **8 Go
libres**, jamais franchi (`factory doctor` échoue en dessous).

---

## 1. Prérequis système

| Outil | Version mesurée | Installation |
|---|---|---|
| Homebrew | 4.x | `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"` |
| ffmpeg + ffprobe | **8.1.2** | `brew install ffmpeg` |
| llama.cpp (`llama-cli`) | **0.4.1** | `brew install llama.cpp` |
| Node | **v26.5.0** | `brew install node` |
| git | 2.54 | `brew install git` |
| uv | **0.11.28** | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Rosetta 2 | — | `softwareupdate --install-rosetta --agree-to-license` |

**Rosetta 2 n'est pas optionnel** : le binaire Rhubarb Lip Sync retenu est un
Mach-O **x86_64**. Sans Rosetta, la brique avatar tombe.

Le `ffmpeg` de Homebrew est compilé `--enable-gpl --enable-version3`, donc **GPLv3**.
Il est appelé **en binaire externe**, jamais lié : cela n'impose rien au code du projet.

Le **Python 3.9.6 du système ne sert jamais** : `uv` installe et gère Python 3.12.

## 2. Cloner et créer l'environnement

```bash
git clone <dépôt> Content-creation && cd Content-creation
uv sync                       # crée .venv (Python 3.12) à partir de uv.lock
```

`uv.lock` **est versionné** : `uv sync` reconstruit exactement les versions mesurées
aux étapes 5.1 et 5.2. Ne pas remplacer par `uv pip install` ni par `uv lock --upgrade`
sans repasser le banc de `benchmarks/` — chaque épinglage de `pyproject.toml`
correspond à une mesure de `benchmarks/RESULTATS.md`.

Pour repartir de zéro : `rm -rf .venv && uv sync`.

### mflux s'installe **hors** de cet environnement

```bash
uv tool install mflux         # v0.19.1, ~1,10 Go, hors .venv
```

mflux tire sa propre pile MLX ; installé dans `.venv`, il casse la pile audio de
la brique TTS. C'est délibéré : `factory doctor` cherche `mflux-generate-flux2`
dans le `PATH`, pas dans `.venv`. Vérifier que `~/.local/bin` est dans le `PATH`.

## 3. Variables d'environnement

```bash
cp .env.example .env && chmod 600 .env
```

`.env` est **ignoré par git** et ne doit jamais apparaître dans un log, un manifeste
ou une conversation.

| Variable | Valeur | Rôle |
|---|---|---|
| `HF_HOME` | `./models/hf` | cache Hugging Face — **obligatoire**, sinon 14 Go partent dans `~/.cache` |
| `OLLAMA_MODELS` | `./models/ollama` | réservé (ollama non installé à ce jour) |
| `LLAMA_CACHE` | `./models/llamacpp` | poids GGUF du LLM |
| `YT_API_KEY` | — | YouTube Data v3, clé restreinte à cette seule API |
| `YT_OAUTH_CLIENT_SECRET_FILE` | `./secrets/yt_client_secret.json` | upload (étape 14) |
| `YT_OAUTH_TOKEN_DIR` | `./secrets/yt_tokens` | jetons OAuth |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | — | notifications, optionnel |
| `DISABLE_TELEMETRY` | `true` | à poser pour Revideo (étape 30.1), qui envoie à PostHog par défaut |

`factory doctor` échoue si l'une des trois variables de cache pointe hors de `models/`.

## 4. Télécharger les modèles — dans cet ordre

**21,52 Go au total.** L'ordre compte : il va du plus utilisé au plus accessoire, et
chaque téléchargement est repesé (`du -sh`) puis inscrit dans `outils/MODELES.md`
**avant** le suivant. Un seul téléchargement à la fois ; `df -h /` entre chacun.

```bash
cd <racine du projet>
set -a && source .env && set +a          # HF_HOME AVANT toute commande Python
```

| # | Modèle | Go | Commande |
|---|---|---|---|
| 1 | LLM Qwen3.5-9B Q4_K_M | 6,6 | `llama-cli -hf bartowski/Qwen_Qwen3.5-9B-GGUF:Q4_K_M -n 1 -p ok` |
| 2 | Image FLUX.2-Klein-4B **4bit** | 4,62 | `uv run hf download mlx-community/FLUX.2-Klein-4B-4bit` |
| 3 | TTS Qwen3-TTS-12Hz-1.7B | 4,2 | `uv run hf download Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` |
| 4 | TTS tokenizer 12Hz | 0,66 | `uv run hf download Qwen/Qwen3-TTS-Tokenizer-12Hz` |
| 5 | ASR parakeet-tdt-0.6b-v3 | 2,3 | `uv run hf download mlx-community/parakeet-tdt-0.6b-v3` |
| 6 | ASR de repli whisper-large-v3-turbo | 1,5 | `uv run hf download mlx-community/whisper-large-v3-turbo` |
| 7 | Profondeur Depth-Anything-V2-**Small** | 0,10 | `uv run hf download depth-anything/Depth-Anything-V2-Small-hf` |
| 8 | Playwright chromium-headless-shell | 0,21 | `PLAYWRIGHT_BROWSERS_PATH=./models/playwright uv run playwright install --only-shell chromium` |

**Trois pièges de licence, à traiter comme du code, pas comme de la documentation :**

1. **Le dépôt image est exactement `mlx-community/FLUX.2-Klein-4B-4bit`** (Apache-2.0).
   `FLUX.2-dev`, `FLUX.2-klein-9B` et `FLUX.1-dev` sont **non commerciaux**. Le dépôt
   officiel `klein-4B` pèse par ailleurs 23,74 Go et contient un doublon de 7,75 Go :
   un `snapshot_download` naïf télécharge les deux copies.
2. **Depth Anything V2 : la variante `Small` seule** est Apache-2.0. Base, Large et
   Giant sont **CC-BY-NC**.
3. **parakeet est CC-BY-4.0** : l'attribution NVIDIA est **due** et doit figurer dans
   `outils/LICENCES.md` et dans les mentions des vidéos.

### Rhubarb Lip Sync (brique avatar, 0,17 Go)

```bash
curl -L -o /tmp/rhubarb.zip \
  https://github.com/DanielSWolf/rhubarb-lip-sync/releases/download/v1.14.0/Rhubarb-Lip-Sync-1.14.0-macOS.zip
unzip -q /tmp/rhubarb.zip -d /tmp/rhubarb-dl
mv "$(find /tmp/rhubarb-dl -maxdepth 2 -name rhubarb -type f -exec dirname {} \;)" outils/rhubarb
xattr -dr com.apple.quarantine outils/rhubarb     # sinon macOS tue le binaire
chmod +x outils/rhubarb/rhubarb
outils/rhubarb/rhubarb --version                  # → Rhubarb Lip Sync version 1.14.0
```

## 5. Vérifier — `factory doctor`

```bash
uv run factory doctor          # ~70 s, exerce réellement chaque brique
uv run factory doctor --quick  # ~1 s, saute les tests de génération
echo $?                        # 0 = tout passe
```

**Toute session de travail commence par cette commande.** Elle ne lit aucune version
affichée : elle génère 20 jetons, synthétise une phrase en français et en anglais,
**les retranscrit et compare mot à mot au texte demandé**, produit une image 512×512
et sa carte de profondeur. Chaque brique tourne dans un **sous-processus séparé**
(un seul modèle résident à la fois, règle `CLAUDE.md` § 4) avec un **timeout de 180 s**.
Les fichiers produits atterrissent dans `workspace/logs/doctor_*`.

Référence mesurée sur M2 16 Go, le 15/09/2026 : LLM 7,9 s (14,8 tok/s) · TTS fr
20,1 s · TTS en 21,7 s · ASR fr 2,1 s · ASR en 0,8 s · image 14,2 s (pic MLX 4,83 Go)
· profondeur 1,3 s · **69 s au total**, 14 contrôles. Un écart de plus du double sur
une brique signale une machine chargée ou un modèle rechargé depuis le disque.

### Les trois états, et pourquoi le français est en WARN

| État | Effet sur `echo $?` | Sens |
|---|---|---|
| **PASS** | 0 | la brique répond et rend le bon résultat |
| **FAIL** | **1** | l'environnement est cassé : il faut réparer avant de travailler |
| **WARN** | 0 | la brique répond, mais une **mesure de qualité** sort du seuil |
| **SKIP** | 0 | sauté par `--quick` |

Le contrôle ASR **compare la transcription au texte demandé** (WER, seuil **20 %** —
les phrases font 5 mots, donc un mot faux est toléré, deux non) et **nomme les mots
manqués** quand il échoue. Une recherche de sous-chaîne ne convient pas : la voix
rend parfois « Bourjour, Cissy Edentest. », qui *contient* « test » alors que les
cinq mots sont faux.

**`ASR fr` ne peut pas faire échouer le doctor, `ASR en` si.** Ce n'est pas une
indulgence : le chaînage TTS → ASR mesure deux choses à la fois, l'ASR **et la voix
qu'on lui donne à entendre. Sur 16 synthèses françaises de la phrase de test, la
voix Serena en *cross-lingual* sort 7 fois un français propre et 7 fois autre chose**
(WER ≥ 60 %) ; whisper entend la même dégradation (0/40/60 %), donc **la cause est la
voix, pas l'ASR**. L'anglais, lui, est mesuré à **0 % de WER sur 6 mesures** : c'est
donc lui qui garde le rôle de verrou, et le français s'affiche en WARN à chaque
session — le risque « ≥ 2 voix par langue » de l'étape 5.1 reste sous les yeux au
lieu de dormir dans un document. **Un WARN sur `ASR fr` ne se répare pas en
réinstallant** : il attend l'arbitrage de voix (`SUIVI.md` § 1).

## 6. Dépannage — les pannes rencontrées, et leur cause

**1. `uv sync` : `OSError: Readme file does not exist: docs/INSTALL.md`.**
`pyproject.toml` déclare un `readme` que hatchling exige **au moment du build**, et
le paquet se construit lui-même (`package = true`). Le fichier doit exister, même
vide. Rencontré à l'étape 7.

**2. `llama-cli` : `error: invalid argument: -no-cnv`.**
Les options de llama.cpp changent de nom entre les builds Homebrew. Le mode
« une réponse puis on sort » de ce build est `-st` / `--single-turn`. Vérifier avec
`llama-cli --help | grep single-turn` avant de figer une commande. Rencontré à l'étape 7.

**3. Un modèle se télécharge deux fois (1,5 Go perdus).**
`huggingface_hub` lit `HF_HOME` **à l'import**, pas à l'appel. Une variable posée
après `import mlx_whisper` arrive trop tard et le cache repart dans `~/.cache/huggingface`.
Poser `HF_HOME` **avant** tout import Python — c'est ce que fait `factory.doctor.charge_env()`,
appelée en première ligne de chaque sous-processus. Rencontré à l'étape 5.1.
Purge : `du -sh ~/.cache/huggingface/hub/*` puis suppression des doublons.

**4. Conflit `huggingface-hub` entre transformers et diffusers.**
diffusers ≥ 0.40 exige `huggingface-hub >= 1.0`, que transformers 4.57 refuse.
D'où l'épinglage **`diffusers==0.35.1` + `transformers==4.57.3` + `huggingface-hub==0.36.2`**
dans `pyproject.toml` : les trois lignes se déplacent ensemble ou pas du tout.
Rencontré à l'étape 5.2.

**5. Rhubarb : SIGSEGV, ou « ne peut pas être ouvert ».**
Le binaire v1.14.0 est **x86_64**. Deux conditions : Rosetta 2 installé, et
l'attribut de quarantaine retiré (`xattr -dr com.apple.quarantine outils/rhubarb`).
Réunies, il rend 309 visèmes en 6,2 s sur 53 s de français — **aucune recompilation
arm64 n'est nécessaire**, contrairement à ce qu'annonçait l'étape 4. Rencontré à
l'étape 5.2.

**6. `factory doctor` en FAIL sur `modeles`.**
Le contrôle lit le tableau d'`outils/MODELES.md` et exige, pour chaque ligne dont
le statut porte « retenu », que le chemin existe. Un FAIL veut dire : poids absent,
ou chemin du ledger faux. **Ne jamais y répondre par un téléchargement non inscrit** ;
corriger le ledger ou retélécharger la ligne concernée (§ 4).

**7. `ASR fr` en WARN à chaque session.**
Ce n'est pas une panne d'installation (voir § 5). Si `ASR en` passe et que `ASR fr`
alerte, l'environnement va bien et c'est la voix française qui décroche. Les WAV
sont dans `workspace/logs/doctor_tts_fr.wav` : les écouter, pas les réinstaller.
**Si `ASR en` alerte aussi**, alors c'est l'ASR : vérifier que
`models/hf/hub/models--mlx-community--parakeet-tdt-0.6b-v3` est complet.

**8. `timeout: command not found`.**
`timeout(1)` n'existe pas sur macOS. Le projet fournit `benchmarks/timeout.sh`.

**9. `mflux-generate-flux2: command not found`.**
mflux vit hors de `.venv` (`uv tool install mflux`) ; `~/.local/bin` doit être dans
le `PATH`. Ne pas « réparer » en l'installant dans `.venv` : il y casse la pile audio.

## 7. Règles qui survivent à l'installation

- **Un seul modèle résident en mémoire à la fois**, dans un sous-processus qui se
  termine. C'est la condition pour que 16 Go tiennent. Un seul run de production à la fois.
- **Plancher de 8 Go libres**, jamais franchi ; plafond de 22 Go de poids retenus.
  Tout nouveau poids se gage sur un retrait, et s'inscrit dans `outils/MODELES.md`
  **avant** le téléchargement.
- **Aucune automatisation de navigateur vers un service tiers**, aucun yt-dlp, API
  officielles seulement. `docs/CONFORMITE.md` prime sur toute demande de vitesse.
- **Licence et attribution enregistrées pour chaque asset** (`outils/LICENCES.md`).
