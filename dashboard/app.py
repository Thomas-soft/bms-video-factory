"""Tableau de bord BMS — point d'entrée : `factory dashboard` (localhost:8501)."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from commun import t  # noqa: E402

st.set_page_config(page_title="BMS", page_icon="🎬", layout="wide")

PAGES = [
    ("vues/1_vue_ensemble.py", "page_vue", "🏠"),
    ("vues/2_production.py", "page_production", "🎞️"),
    ("vues/3_relecture.py", "page_relecture", "✍️"),
    ("vues/4_performances.py", "page_performances", "📈"),
    ("vues/5_editorial.py", "page_editorial", "🗂️"),
    ("vues/6_configuration.py", "page_configuration", "⚙️"),
    ("vues/7_journal.py", "page_journal", "🧾"),
    ("vues/8_aide.py", "page_aide", "❓"),
]

st.navigation([st.Page(chemin, title=t(cle), icon=icone) for chemin, cle, icone in PAGES]).run()
