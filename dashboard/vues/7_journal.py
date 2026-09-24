"""Journal : blocages et remèdes, fin de factory.log, événements d'un run."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import commun as c  # noqa: E402
from commun import t  # noqa: E402

from factory.orchestrator import journal  # noqa: E402

c.entete("page_journal")

st.subheader(t("jou_blocages"))
bloques = c.lignes("SELECT id, video_id, channel_id, stage, status, last_error, updated_at "
                   "FROM jobs WHERE status IN ('blocked', 'failed', 'awaiting_review') "
                   "ORDER BY updated_at DESC")
if not bloques:
    st.success(t("jou_aucun_blocage"))
for job in bloques:
    with st.container(border=True):
        st.markdown(f"**#{job['id']} · {job['video_id']}** — {t(f'statut_{job['status']}')} "
                    f"({t('col_etape')} {job['stage']})")
        st.write(c.masquer(job["last_error"] or t("jou_sans_raison")))
        # Renvoi vers la section d'EXPLOITATION.md qui traite ce cas : aucun diagnostic ici.
        cle = ("jou_remede_relecture" if job["status"] == "awaiting_review"
               else "jou_remede_qc" if job["stage"] == "qc"
               else "jou_remede_echec" if job["status"] == "failed" else "jou_remede_garde")
        st.caption(t(cle, job=job["id"]))

st.subheader(t("jou_log"))
fichier = journal.chemin_factory_log(c.racine())
f1, f2 = st.columns([3, 1])
filtre = f1.text_input(t("jou_filtre"))
n = f2.number_input(t("jou_lignes"), 20, 2000, 200, step=20)
if fichier.exists():
    lignes = fichier.read_text(encoding="utf-8", errors="replace").splitlines()
    if filtre:
        lignes = [x for x in lignes if filtre.lower() in x.lower()]
    st.code(c.masquer("\n".join(lignes[-int(n):])) or t("jou_rien"), language=None)
else:
    st.info(t("jou_pas_log", chemin=fichier))

st.subheader(t("jou_evenements"))
runs = [r["video_id"] for r in c.lignes("SELECT video_id FROM runs ORDER BY updated_at DESC")]
if runs:
    vid = st.selectbox(t("col_video"), runs, key="jou_run")
    evenements = [e for e in journal.lire_events(c.racine()) if e.get("video_id") == vid]
    if evenements:
        st.dataframe(
            [{t("col_date"): e.get("ts", "")[:19].replace("T", " "), t("col_niveau"): e.get("level"),
              t("col_etape"): e.get("stage"), t("col_message"): c.masquer(str(e.get("msg", "")))}
             for e in reversed(evenements)], hide_index=True, width="stretch")
    else:
        st.info(t("jou_rien"))
