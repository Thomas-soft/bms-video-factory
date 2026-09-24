"""Vue d'ensemble : l'état de la fabrique en un coup d'œil."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import commun as c  # noqa: E402
from commun import t  # noqa: E402

from factory.orchestrator import backup, daemon, journal, notify, runner  # noqa: E402
from factory.orchestrator import queue as file_module  # noqa: E402

c.entete("page_vue")

conn = c.base()
try:
    compte = file_module.compter(conn)
    part, detail_quota = notify.quota_consomme(conn, c.racine())
    digest = notify.rendre(notify.collecter(conn, racine=c.racine()))
finally:
    conn.close()

st.subheader(t("vue_jobs"))
colonnes = st.columns(len(compte))
for col, (statut, n) in zip(colonnes, compte.items()):
    col.metric(t(f"statut_{statut}"), n)

st.subheader(t("vue_machine"))
etat = daemon.etat(c.racine())
memoire = runner.memoire_libre_go()
archive = backup.derniere_archive(c.racine())
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric(t("vue_disque"), f"{runner.disque_libre_go(c.racine()):.1f} Go")
m2.metric(t("vue_memoire"), "—" if memoire is None else f"{memoire:.1f} Go")
m3.metric(t("vue_daemon"), t("oui") if etat.vivant else t("non"),
          help=t("vue_daemon_aide", pid=etat.pid or "—"))
m4.metric(t("vue_quota"), "—" if part is None else f"{part * 100:.1f} %", help=detail_quota)
# `factory-AAAAMMJJ-HHMM.tar.zst` → « 24/09 04:34 »
horodatage = archive.name.split(".")[0].split("-")[1:] if archive else []
m5.metric(t("vue_sauvegarde"),
          f"{horodatage[0][6:8]}/{horodatage[0][4:6]} {horodatage[1][:2]}:{horodatage[1][2:4]}"
          if len(horodatage) == 2 else (archive.name if archive else t("aucune")),
          help=str(archive) if archive else None)
if runner.disque_libre_go(c.racine()) < 8:
    st.error(t("vue_disque_bas"))

st.subheader(t("vue_alertes"))
alertes = [e for e in journal.lire_events(c.racine()) if e.get("level") in ("WARN", "ERROR", "BLOCK")]
if alertes:
    st.dataframe(
        [{t("col_date"): e.get("ts", "")[:16].replace("T", " "), t("col_niveau"): e.get("level"),
          t("col_job"): e.get("job"), t("col_message"): c.masquer(str(e.get("msg", "")))}
         for e in reversed(alertes[-10:])],
        hide_index=True, width="stretch")
else:
    st.success(t("vue_aucune_alerte"))

with st.expander(t("vue_digest"), expanded=False):
    st.markdown(c.masquer(digest))
