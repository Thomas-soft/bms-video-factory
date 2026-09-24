"""Configuration : réglages par chaîne, validés par `factory config validate` avant écriture."""

from __future__ import annotations

import difflib
import sys
from pathlib import Path

import streamlit as st
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import commun as c  # noqa: E402
from commun import t  # noqa: E402

c.entete("page_configuration")
if message := st.session_state.pop("flash_config", None):
    st.success(message)
    if diff := st.session_state.pop("diff_config", ""):
        st.code(diff, language="diff")

JOURS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
config = c.racine() / "config"


def _noms(dossier: str) -> list[str]:
    return sorted(p.stem for p in (config / dossier).glob("*.yaml"))


def _voix(langue: str) -> list[str]:
    fichier = config / "languages" / f"{langue}.yaml"
    if not fichier.exists():
        return []
    return [v["id"] for v in yaml.safe_load(fichier.read_text(encoding="utf-8")).get("voices", [])]


def _enregistrer(identifiant: str, texte: str, avant: str) -> None:
    problemes = c.enregistrer_config("channels", identifiant, texte)
    erreurs = [p for p in problemes if p.niveau == "erreur"]
    for p in problemes:
        (st.error if p.niveau == "erreur" else st.warning)(f"{p.fichier} : {p.message}")
    if erreurs:
        st.error(t("cfg_refuse", n=len(erreurs)))
        return
    st.session_state["flash_config"] = t("cfg_enregistre", id=identifiant)
    st.session_state["diff_config"] = "".join(difflib.unified_diff(
        avant.splitlines(True), texte.splitlines(True), "avant", "après"))
    st.rerun()


onglet_regler, onglet_ajouter = st.tabs([t("cfg_onglet_regler"), t("cfg_onglet_ajouter")])

with onglet_regler:
    chaine = st.selectbox(t("rel_chaine"), c.chaines(), key="cfg_chaine")
    fichier = config / "channels" / f"{chaine}.yaml"
    avant = fichier.read_text(encoding="utf-8")
    doc = yaml.safe_load(avant)
    cad = doc["cadence"]
    with st.form(f"form_{chaine}"):
        st.markdown(f"**{t('cfg_cadence')}**")
        f1, f2 = st.columns(2)
        par_semaine = f1.number_input(t("cfg_par_semaine"), 1, 7, int(cad["per_week_max"]),
                                      help=t("cfg_par_semaine_aide"), key="cfg_par_semaine")
        jitter = f2.number_input(t("cfg_jitter"), 0, 600, int(cad.get("jitter_min", 90)))
        jours = st.multiselect(t("cfg_jours"), JOURS, default=list(cad["days"]),
                               format_func=lambda j: t(f"jour_{j}"))
        heures = st.text_input(t("cfg_heures"), ", ".join(cad["hours_local"]),
                               help=t("cfg_heures_aide", tz=cad.get("timezone", "")))
        st.markdown(f"**{t('cfg_style_voix')}**")
        s1, s2 = st.columns(2)
        styles = _noms("styles")
        style = s1.selectbox(t("cfg_style"), styles, index=styles.index(doc["style"])
                             if doc["style"] in styles else 0)
        voix = _voix(doc["lang"]) or [doc["voice_id"]]
        voice_id = s2.selectbox(t("cfg_voix"), voix, index=voix.index(doc["voice_id"])
                                if doc["voice_id"] in voix else 0)
        templates = st.text_input(t("cfg_templates"), ", ".join(doc.get("templates", [])),
                                  help=t("cfg_templates_aide"))
        produits = st.multiselect(t("cfg_produits"), _noms("products"),
                                  default=[p for p in doc.get("products", []) if p in _noms("products")])
        autres = [""] + [x for x in c.chaines() if x != chaine]
        derive = st.selectbox(t("cfg_derive"), autres, format_func=lambda x: x or t("aucune"),
                              index=autres.index(doc.get("derive_from") or "")
                              if (doc.get("derive_from") or "") in autres else 0)
        st.markdown(f"**{t('cfg_auto')}**")
        st.error(t("cfg_auto_avertissement"))
        auto = st.checkbox(t("cfg_auto_case"), value=bool(doc.get("auto_approve")))
        confirme = st.checkbox(t("cfg_auto_confirme"))
        soumis = st.form_submit_button(t("cfg_valider"), type="primary")

    if soumis:
        if auto and not doc.get("auto_approve") and not confirme:
            st.error(t("cfg_auto_non_confirme"))
        else:
            voulu = [
                ("cadence", "per_week_max", int(par_semaine), False),
                ("cadence", "jitter_min", int(jitter), False),
                ("cadence", "days", jours, False),
                ("cadence", "hours_local", [h.strip() for h in heures.split(",") if h.strip()], True),
                (None, "style", style, False), (None, "voice_id", voice_id, False),
                (None, "templates", [x.strip() for x in templates.split(",") if x.strip()], False),
                (None, "products", produits, False), (None, "derive_from", derive or None, False),
                (None, "auto_approve", bool(auto), False),
            ]
            texte = avant
            try:
                for section, cle, valeur, guillemets in voulu:
                    actuel = (doc.get(section) or {}) if section else doc
                    if actuel.get(cle) != valeur:
                        texte = c.remplacer_valeur(texte, section, cle, valeur, guillemets)
            except KeyError as cle_absente:
                st.error(t("cfg_cle_absente", cle=cle_absente))
            else:
                _enregistrer(chaine, texte, avant)

with onglet_ajouter:
    st.caption(t("cfg_ajout_intro"))
    with st.form("ajout"):
        a1, a2 = st.columns(2)
        nouvel_id = a1.text_input(t("cfg_id"), placeholder="bms-niche-en", key="cfg_nouvel_id")
        nom = a2.text_input(t("cfg_nom"), placeholder="BMS Niche EN", key="cfg_nouveau_nom")
        compte = a1.text_input(t("cfg_compte"), help=t("cfg_compte_aide"))
        langue = a2.selectbox(t("cfg_langue"), _noms("languages"))
        niche = a1.selectbox(t("cfg_niche"), _noms("niches"))
        style_n = a2.selectbox(t("cfg_style"), _noms("styles"))
        toutes_voix = [f"{lg}:{v}" for lg in _noms("languages") for v in _voix(lg)]
        voix_n = a1.selectbox(t("cfg_voix"), toutes_voix, key="cfg_nouvelle_voix",
                              help=t("cfg_voix_aide"))
        modele = a2.selectbox(t("cfg_modele"), c.chaines(), help=t("cfg_modele_aide"))
        ajoute = st.form_submit_button(t("cfg_creer"), type="primary")
    if ajoute:
        if not nouvel_id.strip() or (config / "channels" / f"{nouvel_id}.yaml").exists():
            st.error(t("cfg_id_invalide"))
        else:
            texte = (config / "channels" / f"{modele}.yaml").read_text(encoding="utf-8")
            externe = config / "chartes" / f"{modele}.yaml"
            if externe.exists() and "\ncharte:" not in texte:
                # Étape 29 : la charte du modèle vit dans config/chartes/ ; la chaîne neuve en
                # reçoit une copie en ligne, à sortir dans son propre fichier au besoin.
                import yaml

                charte = yaml.safe_load(externe.read_text(encoding="utf-8"))
                for cle in ("schema_version", "channel"):
                    charte.pop(cle, None)
                charte["version"] = charte.pop("charte_version")
                texte = texte.rstrip("\n") + "\n" + yaml.safe_dump(
                    {"charte": charte}, allow_unicode=True, sort_keys=False, width=100)
            valeurs = [
                (None, "id", nouvel_id), (None, "name", nom or nouvel_id), (None, "lang", langue),
                (None, "niche", niche), (None, "style", style_n), (None, "products", []),
                (None, "derive_from", None), (None, "auto_approve", False),
                ("google_account", "alias", compte or nouvel_id),
                ("google_account", "brand_account", nom or nouvel_id),
                ("google_account", "token_ref", f"secrets/tokens/{nouvel_id}.json"),
                ("google_account", "two_fa_enabled", False),
                ("google_account", "phone_verified", False),
                ("youtube", "audit_passed", False), ("youtube", "channel_id", None),
                ("youtube", "playlist_id", None),
                (None, "voice_id", voix_n.split(":", 1)[1] if voix_n else None),
            ]
            try:
                for section, cle, valeur in valeurs:
                    texte = c.remplacer_valeur(texte, section, cle, valeur)
            except KeyError as cle_absente:
                st.error(t("cfg_cle_absente", cle=cle_absente))
            else:
                _enregistrer(nouvel_id, texte, "")
    st.markdown(f"**{t('cfg_jeton')}**")
    st.code(f"uv run factory publish auth --channel {nouvel_id or '<id>'}", language="bash")
    st.caption(t("cfg_jeton_aide"))
