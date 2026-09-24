"""Production : la file des runs et les trois gestes (relancer, bloquer, prioriser)."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import commun as c  # noqa: E402
from commun import t  # noqa: E402

from factory.core.paths import RunPaths  # noqa: E402
from factory.orchestrator import queue as file_module  # noqa: E402

c.entete("page_production")

tous = st.toggle(t("prod_tous"), value=False)
jobs = c.lignes(
    "SELECT j.id, j.video_id, j.channel_id, j.stage, j.status, j.priority, j.publish_at, "
    "j.last_error, r.topic_sujet, r.score_qc FROM jobs j LEFT JOIN runs r USING (video_id) "
    + ("" if tous else "WHERE j.status NOT IN ('exported', 'published') ")
    + "ORDER BY j.priority DESC, j.id")
if not jobs:
    st.info(t("prod_vide"))
    st.stop()

st.dataframe(
    [{t("col_job"): j["id"], t("col_chaine"): j["channel_id"], t("col_sujet"): j["topic_sujet"],
      t("col_etape"): j["stage"], t("col_statut"): t(f"statut_{j['status']}"),
      t("col_qc"): j["score_qc"], t("col_priorite"): j["priority"],
      t("col_date_prevue"): (j["publish_at"] or "")[:16].replace("T", " ")} for j in jobs],
    hide_index=True, width="stretch")

par_id = {j["id"]: j for j in jobs}
choix = st.selectbox(t("prod_choisir"), list(par_id),
                     format_func=lambda i: f"#{i} · {par_id[i]['video_id']} · {par_id[i]['topic_sujet'] or ''}")
job = par_id[choix]
if job["last_error"]:
    st.warning(c.masquer(job["last_error"]))


def _geste(action, *args) -> None:
    conn = c.base()
    try:
        resultat = action(conn, choix, *args, racine=c.racine())
    except file_module.ErreurFile as erreur:
        st.error(str(erreur))
        return
    finally:
        conn.close()
    st.success(t("prod_fait", job=resultat.id, statut=t(f"statut_{resultat.status}"),
                 etape=resultat.stage, priorite=resultat.priority))


g1, g2, g3 = st.columns(3)
with g1:
    st.markdown(f"**{t('prod_relancer')}**")
    if st.button(t("prod_relancer"), key="relancer"):
        _geste(file_module.relancer)
with g2:
    motif = st.text_input(t("prod_motif"), key="motif_blocage")
    if st.button(t("prod_bloquer"), key="bloquer", disabled=not motif.strip()):
        _geste(file_module.bloquer, motif.strip())
with g3:
    priorite = st.number_input(t("prod_priorite"), value=int(job["priority"] or 0), step=1)
    if st.button(t("prod_prioriser"), key="prioriser"):
        _geste(file_module.prioriser, int(priorite))

st.divider()
chemins = RunPaths.depuis_video_id(job["video_id"], c.racine())
a1, a2 = st.columns([1, 1])
with a1:
    st.markdown(f"**{t('prod_miniature')}**")
    if chemins.thumbnail.exists():
        st.image(str(chemins.thumbnail), width="stretch")
    else:
        st.caption(t("prod_pas_miniature"))
with a2:
    st.markdown(f"**{t('prod_video')}**")
    if chemins.final.exists():
        st.code(str(chemins.final), language=None)
        if st.button(t("prod_ouvrir"), key="ouvrir"):
            c.ouvrir_localement(chemins.final)
    else:
        st.caption(t("prod_pas_video"))
