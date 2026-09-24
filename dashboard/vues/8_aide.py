"""Aide : le mode d'emploi d'exploitation et les commandes utiles."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import commun as c  # noqa: E402
from commun import t  # noqa: E402

c.entete("page_aide")

st.subheader(t("aide_commandes"))
COMMANDES = [
    ("uv run factory dashboard", "aide_cmd_dashboard"),
    ("uv run factory queue status", "aide_cmd_status"),
    ("uv run factory review --reviewer <id>", "aide_cmd_review"),
    ("uv run factory daemon status", "aide_cmd_daemon"),
    ("uv run factory digest --afficher", "aide_cmd_digest"),
    ("uv run factory config validate", "aide_cmd_validate"),
    ("uv run factory publish manual-list", "aide_cmd_manual"),
    ("uv run factory backup list", "aide_cmd_backup"),
    ("uv run factory doctor --quick", "aide_cmd_doctor"),
]
st.dataframe([{t("aide_col_cmd"): cmd, t("aide_col_effet"): t(cle)} for cmd, cle in COMMANDES],
             hide_index=True, width="stretch")

st.subheader(t("aide_exploitation"))
doc = c.racine() / "docs" / "EXPLOITATION.md"
if doc.exists():
    st.caption(str(doc))
    with st.container(height=600):
        st.markdown(doc.read_text(encoding="utf-8"))
else:
    st.info(t("aide_pas_doc"))
