"""Checklist de pré-publication — `factory precheck --run <id>` (étape 23.2).

Contrat : `docs/CONFORMITE.md` § 11. Chaque contrôle porte le numéro du § 11 qu'il tient, un
verdict (`ok`, `bloquant`, `avertissement`, `non_couvert`) et un détail lisible. Un seul
`bloquant` suffit : le run est FAIL et **rien n'est envoyé à YouTube** —
`youtube.publier_run` appelle `bloquants()` avant tout `videos.insert`, et le daemon passe le
job en `blocked` avec la raison.

Sortie : `workspace/runs/<id>/precheck.json` (réécrit à chaque passage : c'est un état, pas un
journal ; le journal est `events.jsonl`).

Seuils (anti-clonage, durée minimale) : `config/qc.yaml § precheck`.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from factory.core import config as config_module
from factory.core.models import Channel, SeuilsPrecheck
from factory.core.paths import RunPaths, racine_projet

OK, BLOQUANT, AVERT, NON_COUVERT = "ok", "bloquant", "avertissement", "non_couvert"

#: Décisions de relecture qui valent signature humaine (CONFORMITE § 4, contrôle 16).
DECISIONS_HUMAINES = ("approved", "approved_with_edits")
#: Domaines de liens commissionnés, par réseau — plus le domaine de chaque produit configuré.
DOMAINES_AFFILIATION = (
    r"amzn\.to", r"amazon\.[a-z.]+/.*(?:tag=|/dp/)", r"awin1\.com", r"anrdoezrs\.net",
    r"jdoqocy\.com", r"tkqlhce\.com", r"dpbolvw\.net", r"kqzyfj\.com", r"sjv\.io",
    r"pxf\.io", r"7eer\.net", r"ojrq\.net", r"impact\.com",
)
MOTIFS_SECRETS = (
    r"ya29\.[\w-]{20,}", r"AIza[0-9A-Za-z_-]{35}", r"\"refresh_token\"", r"client_secret",
    r"sk-[A-Za-z0-9]{20,}", r"-----BEGIN [A-Z ]*PRIVATE KEY",
)
LICENCES_INTERDITES = re.compile(r"\bNC\b|non[- ]?commercial|\bND\b|noderivs", re.I)


@dataclass
class Controle:
    id: str
    ref: str          # numéro(s) du § 11
    verdict: str
    detail: str


@dataclass
class Rapport:
    video_id: str
    channel_id: str
    at: str
    controles: list[Controle] = field(default_factory=list)

    @property
    def statut(self) -> str:
        return "FAIL" if self.bloquants else "PASS"

    @property
    def bloquants(self) -> list[Controle]:
        return [c for c in self.controles if c.verdict == BLOQUANT]

    @property
    def avertissements(self) -> list[Controle]:
        return [c for c in self.controles if c.verdict == AVERT]

    def en_json(self) -> dict[str, Any]:
        return {"schema_version": "1.0", "video_id": self.video_id,
                "channel_id": self.channel_id, "at": self.at, "status": self.statut,
                "blocking": len(self.bloquants), "warnings": len(self.avertissements),
                "checks": [asdict(c) for c in self.controles]}


# --------------------------------------------------------------------------------------
# Empreintes (CONFORMITE § 5)
# --------------------------------------------------------------------------------------


def texte_script(chemin: Path) -> str:
    donnees = json.loads(chemin.read_text(encoding="utf-8"))
    return " ".join(str(s.get("narration", "")) for s in donnees.get("segments", []))


def simhash(texte: str, n: int = 3) -> int:
    """SimHash 64 bits des n-grammes de mots : proche en Hamming ⇔ texte proche."""
    mots = re.findall(r"\w+", texte.lower())
    grammes = [" ".join(mots[i:i + n]) for i in range(max(1, len(mots) - n + 1))]
    poids = [0] * 64
    for g in grammes:
        h = int.from_bytes(hashlib.blake2b(g.encode(), digest_size=8).digest(), "big")
        for b in range(64):
            poids[b] += 1 if (h >> b) & 1 else -1
    return sum(1 << b for b in range(64) if poids[b] > 0)


def distance(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def phash_miniature(chemin: Path) -> int | None:
    if not chemin.exists():
        return None
    from factory.editorial.thumbnails_variants import phash

    return int(phash(chemin), 16)


def _duree_s(fichier: Path) -> float | None:
    if not fichier.exists():
        return None
    try:
        sortie = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
             "default=nw=1:nk=1", str(fichier)], capture_output=True, text=True, timeout=60,
            check=False).stdout.strip()
        return float(sortie)
    except (ValueError, OSError, subprocess.SubprocessError):
        return None


def _json(chemin: Path) -> dict[str, Any]:
    try:
        return json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _chercher(donnees: Any, cle: str) -> Any:
    """Première valeur de `cle` à n'importe quelle profondeur."""
    if isinstance(donnees, dict):
        if cle in donnees:
            return donnees[cle]
        for v in donnees.values():
            r = _chercher(v, cle)
            if r is not None:
                return r
    elif isinstance(donnees, list):
        for v in donnees:
            r = _chercher(v, cle)
            if r is not None:
                return r
    return None


# --------------------------------------------------------------------------------------
# Relecture — aussi appelée par le calendrier
# --------------------------------------------------------------------------------------


def refus_relecture(video_id: str, channel_id: str, racine: Path | None = None,
                    conn: sqlite3.Connection | None = None,
                    chaine: Channel | None = None) -> str | None:
    """`None` si le script **actuel** porte une relecture valable, sinon la raison (15-16)."""
    verdict, detail = _relecture(video_id, channel_id, racine or racine_projet(), conn, chaine)
    return detail if verdict == BLOQUANT else None


def _relecture(video_id: str, channel_id: str, racine: Path,
               conn: sqlite3.Connection | None, chaine: Channel | None) -> tuple[str, str]:
    from factory.core import db

    chemins = RunPaths.depuis_video_id(video_id, racine)
    if not chemins.script.exists():
        return BLOQUANT, "script.json absent"
    empreinte = hashlib.sha256(chemins.script.read_bytes()).hexdigest()
    fermer = conn is None
    conn = conn or db.ouvrir(racine / "workspace" / "factory.db")
    try:
        lignes = conn.execute(
            "SELECT reviewer, decision, script_sha256, timestamp FROM review_log "
            "WHERE video_id = ? ORDER BY timestamp DESC", (video_id,)).fetchall()
    finally:
        if fermer:
            conn.close()
    if not lignes:
        return BLOQUANT, "aucune ligne dans review_log pour ce run"
    actuelle = [l for l in lignes if l["script_sha256"] == empreinte]
    if not actuelle:
        return BLOQUANT, (f"relecture portant sur un autre texte : review_log "
                          f"{lignes[0]['script_sha256'][:8]} ≠ script actuel {empreinte[:8]}")
    ligne = actuelle[0]
    if chaine is None:
        chaine = config_module.charger(racine, strict=False).channels.get(channel_id)
    if ligne["decision"] in DECISIONS_HUMAINES:
        return OK, (f"{ligne['reviewer']} | {ligne['decision']} | {empreinte[:8]} "
                    f"({ligne['timestamp']})")
    if ligne["decision"] == "auto_approved" and chaine is not None and chaine.auto_approve:
        return AVERT, ("auto-approve actif sur la chaîne : l'exception éditoriale RIA "
                       "art. 50 n'est pas acquise pour cette vidéo")
    return BLOQUANT, (f"décision « {ligne['decision']} » par {ligne['reviewer']} — "
                      f"auto_approve={getattr(chaine, 'auto_approve', None)} sur {channel_id} : "
                      "`factory queue approve <job> --reviewer <id>` après lecture")


# --------------------------------------------------------------------------------------
# La checklist
# --------------------------------------------------------------------------------------


def controler(video_id: str, channel_id: str | None = None, *, racine: Path | None = None,
              conn: sqlite3.Connection | None = None, ecrire: bool = True) -> Rapport:
    """Exécute tous les contrôles et écrit `precheck.json`."""
    from factory.core import db

    racine = racine or racine_projet()
    chemins = RunPaths.depuis_video_id(video_id, racine)
    spec = _json(chemins.spec)
    channel_id = channel_id or spec.get("channel_id") or ""
    cfg = config_module.charger(racine, strict=False)
    chaine = cfg.channels.get(channel_id)
    rapport = Rapport(video_id, channel_id, datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"))
    ajout = rapport.controles.append
    if chaine is None:
        ajout(Controle("chaine", "24", BLOQUANT, f"chaîne « {channel_id} » absente de config"))
        return _ecrire(rapport, chemins, ecrire)
    seuils = cfg.qc.precheck if cfg.qc else SeuilsPrecheck()
    langue = cfg.languages.get(chaine.lang)
    meta = _json(chemins.racine / "metadata.json")
    manifeste = _json(chemins.racine / "manifest.json")
    conf = manifeste.get("conformite", {})
    description = str(meta.get("description", ""))
    premiere_ligne = description.split("\n", 1)[0]
    fermer = conn is None
    conn = conn or db.ouvrir(racine / "workspace" / "factory.db")
    try:
        # 15-16 — relecture signée, sur le script actuel
        verdict, detail = _relecture(video_id, channel_id, racine, conn, chaine)
        ajout(Controle("relecture", "15-16", verdict, detail))

        # QC
        qc = _json(chemins.racine / "qc.json")
        ajout(Controle("qc", "—", OK if qc.get("verdict") == "PASS" else BLOQUANT,
                       f"verdict {qc.get('verdict', 'absent')}, score {qc.get('score', '—')}"))

        # Mentions IA dans la langue de la chaîne (§ 3 couches 1 et 3)
        if not meta:
            ajout(Controle("metadata", "—", BLOQUANT, "metadata.json absent ou illisible"))
        if langue is None:
            ajout(Controle("mention_ia", "3", BLOQUANT,
                           f"config/languages/{chaine.lang}.yaml absent"))
        else:
            d = langue.disclosure
            if not d.ia_production:
                ajout(Controle("mention_ia", "3", BLOQUANT,
                               f"disclosure.ia_production vide dans {chaine.lang}.yaml"))
            elif d.ia_production not in description:
                ajout(Controle("mention_ia", "3", BLOQUANT,
                               f"mention IA absente de la description (attendue en "
                               f"« {chaine.lang} » : « {d.ia_production[:60]}… »)"))
            else:
                ajout(Controle("mention_ia", "3", OK, f"présente, langue {chaine.lang}"))
            if conf.get("virtual_images_mention"):
                incruste = (conf.get("disclosure_lines", {}).get(chaine.lang, {})
                            .get("overlay_text"))
                manque = [x for x, ok in (("description", d.virtual_images in description),
                                          ("incrustation", bool(incruste))) if not ok]
                ajout(Controle("images_virtuelles", "3", BLOQUANT if manque else OK,
                               "absente : " + ", ".join(manque) if manque
                               else f"« {d.virtual_images} » en description et incrustée"))

        # 4, 7-9 — affiliation et promotion payante
        _controles_affiliation(rapport, cfg, chaine, spec, conf, meta, description,
                               premiere_ligne, langue)

        # 1-2 — contenu synthétique décidé, avec raison
        csm = conf.get("contains_synthetic_media", meta.get("contains_synthetic_media"))
        raison = conf.get("contains_synthetic_media_reason") \
            or meta.get("contains_synthetic_media_reason")
        scenes = conf.get("synthetic_scenes") or []
        realistes = [s.get("scene_id") for s in scenes if s.get("realistic")]
        if csm is None:
            ajout(Controle("synthetique", "1", BLOQUANT, "contains_synthetic_media non décidé"))
        elif realistes and not csm:
            ajout(Controle("synthetique", "2", BLOQUANT,
                           f"{len(realistes)} scène(s) réaliste(s) ({', '.join(realistes[:4])}) "
                           "et contains_synthetic_media = false"))
        elif csm and not raison:
            ajout(Controle("synthetique", "1", BLOQUANT, "true sans raison écrite"))
        elif meta.get("contains_synthetic_media") is not None \
                and meta.get("contains_synthetic_media") != csm:
            ajout(Controle("synthetique", "1", BLOQUANT, "metadata.json et manifest divergent"))
        elif not csm and not raison:
            ajout(Controle("synthetique", "1", AVERT,
                           f"false sans raison écrite ; déduite : 0/{len(scenes)} scène "
                           "réaliste (règle § 3 couche 1)"))
        else:
            ajout(Controle("synthetique", "1-2", OK, f"{csm} — {raison}"))

        # 10-13 — licences, droits, musique, attribution
        _controles_licences(rapport, cfg, chemins, manifeste, description)

        # 14 — C2PA
        ajout(Controle("c2pa", "14", OK if conf.get("c2pa_preserved") else AVERT,
                       "préservé" if conf.get("c2pa_preserved")
                       else "c2pa_preserved = false (le générateur local n'en produit pas)"))

        # 17 — angle éditorial
        angle = (conf.get("editorial_angle") or {}).get("type") \
            or _chercher(manifeste.get("decisions", {}), "angle") \
            or (spec.get("topic") or {}).get("angle")
        autorises = cfg.editorial.angles_autorises if cfg.editorial else []
        ajout(Controle("angle", "17", OK if angle and (not autorises or angle in autorises)
                       else BLOQUANT, f"angle « {angle} »" if angle else "angle absent"))

        # 18-19 — anti-clonage inter-chaînes, même langue
        _controles_clonage(rapport, conn, racine, chemins, chaine, seuils)

        # 20 — rotation des templates
        tpl = (manifeste.get("identite") or {}).get("template_id")
        derniers = _templates_recents(conn, racine, channel_id, video_id)
        ajout(Controle("template", "20", AVERT if tpl in derniers else OK,
                       f"{tpl} ; 2 dernières publications : {derniers or 'aucune'}"))
        # Étape 29 : deux runs consécutifs d'une chaîne ne partagent jamais leur gabarit.
        from factory.core import runs as runs_module

        precedent = runs_module.dernier_gabarit_avant(conn, channel_id, video_id)
        ajout(Controle("rotation_gabarit", "20", BLOQUANT if tpl and tpl == precedent else OK,
                       f"{tpl} ; run précédent de la chaîne : {precedent or 'aucun'}"))

        # 21 — titre non trompeur : vérification LLM de l'étape 21
        titre = meta.get("title_chosen")
        variantes = meta.get("title_variants") or []
        choisie = next((v for v in variantes if isinstance(v, dict) and v.get("text") == titre),
                       None)
        if not titre or choisie is None or "promise_kept" not in choisie:
            ajout(Controle("titre", "21", BLOQUANT,
                           "vérification de promesse du titre (étape 21) absente"))
        else:
            ajout(Controle("titre", "21", OK if choisie["promise_kept"] else AVERT,
                           f"« {titre} » — promise_kept = {choisie['promise_kept']}"))

        # Durée et langue / catégorie
        duree = _duree_s(chemins.racine / "final.mp4")
        ajout(Controle("duree", "25", BLOQUANT if duree is None or duree < seuils.duree_min_s
                       else OK, "final.mp4 illisible" if duree is None
                       else f"{duree:.1f} s (minimum {seuils.duree_min_s:g})"))
        manques = [n for n, v in (
            ("default_language", meta.get("default_language") == chaine.lang),
            ("default_audio_language", bool(meta.get("default_audio_language"))),
            ("category_id", bool(meta.get("category_id"))
             and str(meta.get("category_id")) == chaine.youtube.category_id)) if not v]
        ajout(Controle("langue_categorie", "—", BLOQUANT if manques else OK,
                       ("incorrect : " + ", ".join(manques)) if manques else
                       f"{chaine.lang}, catégorie {meta.get('category_id')}"))

        # 22-23 — calendrier
        _controle_calendrier(rapport, conn, racine, video_id, channel_id)

        # 24-25 — compte
        compte = chaine.google_account
        manque_compte = [n for n, ok in (
            ("owner=BMS", compte.owner == "BMS"), ("brand_account", bool(compte.brand_account)),
            ("two_fa_enabled", compte.two_fa_enabled),
            ("phone_verified", compte.phone_verified)) if not ok]
        ajout(Controle("compte", "24-25", BLOQUANT if manque_compte else OK,
                       ("config/channels : " + ", ".join(manque_compte) + " — voir CONFORMITE "
                        "§ 12.1") if manque_compte else f"{compte.brand_account}, 2FA, téléphone"))

        # 26 — chemin de publication cohérent avec l'audit
        attendu = "api_scheduled" if chaine.youtube.audit_passed else "manual_studio"
        chemin_pub = conf.get("publish_path")
        ajout(Controle("publish_path", "26", OK if chemin_pub in (None, attendu) else BLOQUANT,
                       f"{chemin_pub or '(non posé)'} ; attendu {attendu}"))

        # 27 — quota : tenu par quota.py au moment de l'appel
        ajout(Controle("quota", "27", NON_COUVERT,
                       "vérifié par factory/publish/quota.py à l'appel, pas ici"))

        # 28 — aucun téléchargement de vidéo tierce
        traces = _traces_ytdlp(chemins.racine)
        ajout(Controle("yt_dlp", "28", BLOQUANT if traces else OK,
                       ("trace : " + ", ".join(traces[:3])) if traces else "aucune trace"))

        # 29 — cache API du registre
        ajout(Controle("cache_api", "29", NON_COUVERT, "tenu par `factory editorial purge`"))

        # 30 — aucun secret
        fuites = _secrets(chemins.racine)
        ajout(Controle("secrets", "30", BLOQUANT if fuites else OK,
                       ("motif trouvé dans " + ", ".join(fuites)) if fuites else "aucun motif"))
    finally:
        if fermer:
            conn.close()
    return _ecrire(rapport, chemins, ecrire)


def _ecrire(rapport: Rapport, chemins: RunPaths, ecrire: bool) -> Rapport:
    if ecrire and chemins.racine.exists():
        (chemins.racine / "precheck.json").write_text(
            json.dumps(rapport.en_json(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
    return rapport


def _controles_affiliation(rapport: Rapport, cfg: Any, chaine: Channel, spec: dict,
                           conf: dict, meta: dict, description: str, premiere_ligne: str,
                           langue: Any) -> None:
    ajout = rapport.controles.append
    produits_ids = set(chaine.products) | ({spec["product_id"]} if spec.get("product_id")
                                           else set())
    produits = [cfg.products[p] for p in produits_ids if p in cfg.products]
    motifs = list(DOMAINES_AFFILIATION) + [
        re.escape(re.sub(r"^https://(www\.)?", "", p.target_url).split("/")[0])
        for p in produits]
    liens = [m.group(0) for m in re.finditer(r"https?://\S+", description)
             if any(re.search(x, m.group(0)) for x in motifs)]
    liens_manifeste = conf.get("affiliate_links") or []
    payant = conf.get("paid_promotion", meta.get("paid_promotion"))
    presence = bool(liens or liens_manifeste)
    if payant is None:
        ajout(Controle("promotion_payante", "4", BLOQUANT, "paid_promotion non décidé"))
    elif presence and not payant:
        ajout(Controle("promotion_payante", "4", BLOQUANT,
                       f"lien commissionné ({(liens or ['manifeste'])[0][:60]}) et "
                       "paid_promotion = false"))
    elif produits_ids and not payant:
        ajout(Controle("promotion_payante", "4", BLOQUANT,
                       f"produit(s) {sorted(produits_ids)} et paid_promotion = false"))
    elif payant and not presence:
        ajout(Controle("promotion_payante", "4", AVERT,
                       "paid_promotion = true sans lien commissionné détecté"))
    else:
        ajout(Controle("promotion_payante", "4", OK,
                       f"paid_promotion = {payant}, {len(liens) + len(liens_manifeste)} lien(s)"))
    if not payant:
        return
    # 5-6 — bandeau « Publicité » et mention orale, par segment sponsor
    segments = conf.get("sponsor_segments") or []
    fautes = [f"{s.get('start_s')}-{s.get('end_s')} s" for s in segments
              if not s.get("overlay_rendered")]
    tard = [f"{s.get('start_s')} s" for s in segments
            if s.get("spoken_disclosure_at_s") is None
            or float(s["spoken_disclosure_at_s"]) > float(s.get("start_s", 0)) + 30]
    ajout(Controle("bandeau_publicite", "5", BLOQUANT if not segments or fautes else OK,
                   "aucun sponsor_segments" if not segments else
                   (f"bandeau non rendu : {', '.join(fautes)}" if fautes
                    else f"{len(segments)} segment(s) incrusté(s)")))
    ajout(Controle("mention_orale", "6", BLOQUANT if tard else OK,
                   f"au-delà de 30 s : {', '.join(tard)}" if tard else "dans les 30 s"))
    # 7-9 — mention d'affiliation en tête, vocabulaire du réseau, phrase Amazon
    if langue is None:
        return
    d = langue.disclosure
    for p in produits:
        attendus = {"amazon": [d.amazon], "impact": d.impact, "awin": d.awin}.get(
            p.network, d.impact + d.awin)
        present = [a for a in attendus if a in description]
        en_tete = any(a in premiere_ligne for a in attendus)
        ajout(Controle(f"mention_affiliation:{p.id}", "7-9",
                       OK if present and en_tete else BLOQUANT,
                       f"{p.network} : " + ("en première ligne" if en_tete else
                                            ("présente mais pas en première ligne" if present
                                             else f"absente (attendu : {attendus})"))))


def _controles_licences(rapport: Rapport, cfg: Any, chemins: RunPaths, manifeste: dict,
                        description: str) -> None:
    ajout = rapport.controles.append
    blanches = set(cfg.editorial.sources_blanches) if cfg.editorial else set()
    dossiers = sorted(p for p in (chemins.racine / "assets").glob("*") if p.is_dir()) \
        if (chemins.racine / "assets").exists() else []
    fautes: list[str] = []
    attributions: list[str] = []
    for dossier in dossiers:
        lic = _json(dossier / "licence.json")
        if not lic:
            fautes.append(f"{dossier.name} : licence.json absent")
            continue
        genere = bool(lic.get("generator"))
        manque = [k for k in ("licence", "author") if not lic.get(k)]
        if not genere and not lic.get("source_url"):
            manque.append("source_url")
        if manque:
            fautes.append(f"{dossier.name} : {', '.join(manque)} vide(s)")
        if LICENCES_INTERDITES.search(str(lic.get("licence", ""))):
            fautes.append(f"{dossier.name} : licence {lic['licence']} interdite")
        if not genere and blanches and str(lic.get("provider", "")).lower() not in blanches:
            fautes.append(f"{dossier.name} : fournisseur {lic.get('provider')} hors liste")
        if lic.get("person_identifiable") and not lic.get("person_release"):
            fautes.append(f"{dossier.name} : personne identifiable sans person_release")
        if lic.get("attribution_line"):
            attributions.append(str(lic["attribution_line"]))
    manquants = (manifeste.get("conformite") or {}).get("person_releases_missing") or []
    if manquants:
        fautes.append(f"person_release manquant : {manquants[:3]}")
    ajout(Controle("licences_assets", "10-11", BLOQUANT if fautes or not dossiers else OK,
                   "; ".join(fautes[:4]) + (f" (+{len(fautes) - 4})" if len(fautes) > 4 else "")
                   if fautes else (f"{len(dossiers)} asset(s), tous sous licence"
                                   if dossiers else "aucun dossier d'asset")))
    # 12 — musique
    piste = _chercher(manifeste, "music_track")
    musique = _chercher(manifeste, "music") if piste else None
    if not piste:
        ajout(Controle("musique", "12", OK, "aucune piste (lit silencieux) : rien à licencier"))
    else:
        lic = (musique or {}).get("licence") if isinstance(musique, dict) else None
        lic = lic or _json(chemins.racine / "music" / "licence.json")
        if not lic or not lic.get("licence"):
            ajout(Controle("musique", "12", BLOQUANT, f"piste {piste} sans licence"))
        else:
            if lic.get("attribution_required") and lic.get("credit_line"):
                attributions.append(str(lic["credit_line"]))
            manque_credit = lic.get("attribution_required") and not lic.get("credit_line")
            ajout(Controle("musique", "12", BLOQUANT if manque_credit else OK,
                           f"{piste} — {lic.get('licence')}"))
    # 13 — bloc d'attribution
    absentes = [a for a in attributions if a not in description]
    ajout(Controle("attribution", "13", BLOQUANT if absentes else OK,
                   f"{len(absentes)} ligne(s) absente(s) : « {absentes[0][:60]} »" if absentes
                   else (f"{len(attributions)} ligne(s) présentes" if attributions
                         else "aucune attribution requise")))


def _publiees(conn: sqlite3.Connection, video_id: str) -> list[tuple[str, str]]:
    lignes = conn.execute(
        "SELECT video_id, channel_id FROM publications WHERE status != 'failed' "
        "UNION SELECT video_id, channel_id FROM jobs WHERE status = 'published'").fetchall()
    return [(l[0], l[1]) for l in lignes if l[0] != video_id]


def _controles_clonage(rapport: Rapport, conn: sqlite3.Connection, racine: Path,
                       chemins: RunPaths, chaine: Channel, seuils: SeuilsPrecheck) -> None:
    ajout = rapport.controles.append
    if not chemins.script.exists():
        ajout(Controle("clonage_script", "18", BLOQUANT, "script.json absent"))
        return
    moi_s = simhash(texte_script(chemins.script))
    moi_m = phash_miniature(chemins.racine / "thumbnail.png")
    proches_s: list[str] = []
    proches_m: list[str] = []
    compares = 0
    for autre, cid in _publiees(conn, rapport.video_id):
        ac = RunPaths.depuis_video_id(autre, racine)
        compares += 1
        # Script : même langue seulement (une adaptation est un autre texte, § 5).
        if _json(ac.spec).get("lang") == chaine.lang and ac.script.exists():
            ds = distance(moi_s, simhash(texte_script(ac.script)))
            if ds < seuils.script_simhash_distance_min:
                proches_s.append(f"{autre} ({cid}, {ds} bits)")
        # Miniature : toutes langues — un même visuel sur EN et FR signe le réseau.
        autre_m = phash_miniature(ac.racine / "thumbnail.png")
        if moi_m is not None and autre_m is not None:
            dm = distance(moi_m, autre_m)
            if dm < seuils.thumbnail_phash_distance_min:
                proches_m.append(f"{autre} ({cid}, {dm} bits)")
    base = f"{compares} vidéo(s) publiée(s) comparée(s) (script : même langue ; miniature : toutes)"
    ajout(Controle("clonage_script", "18", BLOQUANT if proches_s else OK,
                   f"SimHash < {seuils.script_simhash_distance_min} bits : {proches_s[:3]}"
                   if proches_s else base))
    if moi_m is None:
        ajout(Controle("clonage_miniature", "19", BLOQUANT, "thumbnail.png absent"))
    else:
        ajout(Controle("clonage_miniature", "19", BLOQUANT if proches_m else OK,
                       f"pHash < {seuils.thumbnail_phash_distance_min} bits : {proches_m[:3]}"
                       if proches_m else base))


def _templates_recents(conn: sqlite3.Connection, racine: Path, channel_id: str,
                       video_id: str) -> list[str]:
    lignes = conn.execute(
        "SELECT video_id FROM publications WHERE channel_id = ? AND status != 'failed' "
        "AND video_id != ? ORDER BY coalesce(publish_at, uploaded_at) DESC LIMIT 2",
        (channel_id, video_id)).fetchall()
    sortie = []
    for l in lignes:
        m = _json(RunPaths.depuis_video_id(l[0], racine).racine / "manifest.json")
        if (m.get("identite") or {}).get("template_id"):
            sortie.append(m["identite"]["template_id"])
    return sortie


def _controle_calendrier(rapport: Rapport, conn: sqlite3.Connection, racine: Path,
                         video_id: str, channel_id: str) -> None:
    from factory.publish import calendar

    date = calendar.date_pour(conn, video_id, channel_id, racine)
    if date is None:
        rapport.controles.append(Controle(
            "calendrier", "22-23", AVERT,
            "aucune date au calendrier : `factory calendar plan` avant la publication"))
        return
    ctx = calendar.contexte(racine)
    violations, _ = calendar.verifier(ctx, calendar.evenements(conn, racine))
    miennes = [v.message for v in violations if video_id in v.videos]
    rapport.controles.append(Controle("calendrier", "22-23", BLOQUANT if miennes else OK,
                                      "; ".join(miennes[:2]) if miennes else f"date {date}"))


def _traces_ytdlp(dossier: Path) -> list[str]:
    motif = re.compile(r"yt[-_]dlp|youtube[-_]dl", re.I)
    traces = []
    for f in [*dossier.glob("*.json"), *dossier.glob("*.log"), *dossier.glob("assets/*/licence.json")]:
        if f.name == "precheck.json":   # porte l'identifiant du contrôle lui-même
            continue
        try:
            if motif.search(f.read_text(encoding="utf-8", errors="ignore")):
                traces.append(f.name)
        except OSError:
            continue
    return traces


def _secrets(dossier: Path) -> list[str]:
    motif = re.compile("|".join(MOTIFS_SECRETS))
    fuites = []
    for nom in ("metadata.json", "manifest.json", "publication.md", "publish.json"):
        f = dossier / nom
        if f.exists() and motif.search(f.read_text(encoding="utf-8", errors="ignore")):
            fuites.append(nom)
    return fuites


def bloquants(video_id: str, channel_id: str, racine: Path | None = None) -> list[str]:
    """Point d'accroche de `youtube.precheck` : messages des contrôles bloquants."""
    rapport = controler(video_id, channel_id, racine=racine)
    return [f"[{c.ref}] {c.id} : {c.detail}" for c in rapport.bloquants]
