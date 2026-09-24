"""Éditorial : classement des niches et file de sujets par chaîne."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import commun as c  # noqa: E402
from commun import t  # noqa: E402

from factory.editorial import topics as tp  # noqa: E402

c.entete("page_editorial")
if message := st.session_state.pop("flash_editorial", None):
    st.success(message)

st.subheader(t("edi_niches"))
niches = c.lignes(
    "SELECT niche, lang, date, score, demande, concurrence, monetisation, faisabilite "
    "FROM niche_scores n WHERE date = (SELECT max(date) FROM niche_scores m "
    "WHERE m.niche = n.niche AND m.lang = n.lang) ORDER BY score DESC")
if niches:
    st.dataframe(niches, hide_index=True, width="stretch")
else:
    st.info(t("edi_pas_niches"))

st.subheader(t("edi_sujets"))
chaine = st.selectbox(t("rel_chaine"), c.chaines(), key="edi_chaine")
statuts = st.multiselect(t("col_statut"), list(tp.STATUTS), default=["proposed", "approved"])
sujets = c.lignes(
    "SELECT id, topic, angle, score, status, evidence_json FROM topics_queue "
    f"WHERE channel_id = ? AND status IN ({','.join('?' * len(statuts)) or 'NULL'}) "
    "ORDER BY score DESC", (chaine, *statuts))


def _preuve(brut: str | None) -> str:
    e = json.loads(brut or "{}")
    return (f"{e.get('n_videos', '—')} vid · {e.get('n_chaines', '—')} ch · "
            f"{e.get('n_percees', '—')} percées" + (f" · {e['gap_type']}" if e.get("gap_type") else ""))


if not sujets:
    st.info(t("edi_vide"))
else:
    st.dataframe(
        [{"#": s["id"], t("col_score"): round(s["score"] or 0, 3), t("col_sujet"): s["topic"],
          t("col_angle"): s["angle"], t("col_preuves"): _preuve(s["evidence_json"]),
          t("col_statut"): s["status"]} for s in sujets],
        hide_index=True, width="stretch")
    par_id = {s["id"]: s for s in sujets}
    choisis = st.multiselect(t("edi_choisir"), list(par_id),
                             format_func=lambda i: f"#{i} · {par_id[i]['topic']}")

    def _statut(statut: str) -> None:
        conn = c.base()
        try:
            for i in choisis:
                tp.changer_statut(conn, i, statut)
        finally:
            conn.close()
        st.session_state["flash_editorial"] = t("edi_fait", n=len(choisis), statut=statut)
        st.rerun()

    e1, e2 = st.columns(2)
    if e1.button(t("edi_approuver"), disabled=not choisis, type="primary"):
        _statut("approved")
    if e2.button(t("edi_bannir"), disabled=not choisis):
        _statut("banned")

st.divider()
c.bouton_tache(f"topics_{chaine}", ["editorial", "topics", "--channel", chaine], "edi_rafraichir")
