"""Performances : ce que les vidéos font, et ce que le système en a appris."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import commun as c  # noqa: E402
from commun import t  # noqa: E402

from factory.analytics import show, weights  # noqa: E402
from factory.core.paths import RunPaths  # noqa: E402

c.entete("page_performances")

chaine = st.selectbox(t("rel_chaine"), c.chaines(), key="perf_chaine")
perf = pd.DataFrame(c.lignes("SELECT * FROM v_video_perf WHERE channel_id = ?", (chaine,)))

st.subheader(t("perf_chaine"))
if perf.empty:
    st.info(t("perf_aucune"))
else:
    def _moy(col: str):
        serie = perf[col].dropna()
        return None if serie.empty else float(serie.mean())

    ctr = _moy("ctr_7d")
    pct = _moy("avg_view_pct_7d")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(t("perf_vues_7"), f"{perf['views_7d'].fillna(0).sum():.0f}")
    k2.metric(t("perf_vues_30"), f"{perf['views_30d'].fillna(0).sum():.0f}")
    k3.metric(t("perf_pct"), "—" if pct is None else f"{pct:.1f} %")
    k4.metric(t("perf_ctr"), t("perf_sans_reach") if ctr is None else f"{ctr * 100:.2f} %")
    colonnes = {"video_id": t("col_video"), "topic": t("col_sujet"), "views_7d": t("perf_vues_7"),
                "avg_view_pct_7d": t("perf_pct")}
    classees = perf.dropna(subset=["views_7d"]).sort_values("views_7d", ascending=False)
    h1, h2 = st.columns(2)
    h1.markdown(f"**{t('perf_top')}**")
    h1.dataframe(classees.head(5)[list(colonnes)].rename(columns=colonnes), hide_index=True)
    h2.markdown(f"**{t('perf_flop')}**")
    h2.dataframe(classees.tail(5).iloc[::-1][list(colonnes)].rename(columns=colonnes), hide_index=True)

st.subheader(t("perf_retention"))
courbes = c.lignes(
    "SELECT rc.video_id, rc.day_after_publish, rc.points_json, r.duration_s, r.topic_sujet "
    "FROM retention_curves rc JOIN runs r USING (video_id) WHERE r.channel_id = ? "
    "ORDER BY rc.video_id, rc.day_after_publish DESC", (chaine,))
derniere = {}
for courbe in courbes:
    derniere.setdefault(courbe["video_id"], courbe)
if not derniere:
    st.info(t("perf_pas_courbe"))
else:
    vid = st.selectbox(t("perf_video"), list(derniere),
                       format_func=lambda v: f"{v} · {derniere[v]['topic_sujet'] or ''}")
    courbe = derniere[vid]
    points = json.loads(courbe["points_json"])
    chemins = RunPaths.depuis_video_id(vid, c.racine())
    segments, roles, sponsors = [], {}, []
    if (chemins.racine / "voice" / "timings.json").is_file():
        segments, roles, sponsors = show._segments(chemins)  # noqa: SLF001
    duree = courbe["duration_s"] or (segments[-1]["end_s"] if segments else None)
    df = pd.DataFrame(points, columns=["x", "y"])
    df["t_s"] = df["x"] * (duree or 0)
    df["pct"] = df["y"] * 100
    axe_x = "t_s:Q" if duree else "x:Q"
    graphe = alt.Chart(df).mark_line().encode(
        x=alt.X(axe_x, title=t("perf_axe_temps") if duree else t("perf_axe_part")),
        y=alt.Y("pct:Q", title=t("perf_axe_retention")))
    if duree:
        chutes = pd.DataFrame([{"t_s": ch.t_s, "texte": f"-{ch.pts:.0f} pts · {ch.libelle}"}
                               for ch in show.chutes(points, float(duree), segments, roles, sponsors)])
        if not chutes.empty:
            graphe += alt.Chart(chutes).mark_rule(color="#d62728").encode(x="t_s:Q")
            graphe += alt.Chart(chutes).mark_text(align="left", dx=4, dy=-60, color="#d62728",
                                                  angle=0).encode(x="t_s:Q", text="texte:N")
    st.caption(t("perf_jour", j=courbe["day_after_publish"]))
    st.altair_chart(graphe, width="stretch")

st.subheader(t("perf_appris"))
poids = weights.charger(c.racine())
if poids is None:
    st.info(t("perf_pas_poids"))
else:
    p1, p2, p3 = st.columns(3)
    p1.metric(t("perf_n_videos"), poids.get("n_videos", 0))
    p2.metric(t("perf_n_y"), poids.get("n_videos_with_y", 0))
    p3.metric(t("perf_n_min"), poids.get("n_min_per_level", "—"))
    st.caption(t("perf_genere", date=str(poids.get("generated_at", ""))[:16].replace("T", " ")))
    appris = [{t("col_facteur"): f, t("col_niveau_f"): niv, "n": v.get("n"),
               t("col_multiplicateur"): v.get("multiplier")}
              for f, d in poids.get("factors", {}).items()
              for niv, v in (d.get("levels") or {}).items()]
    if appris:
        st.dataframe(appris, hide_index=True, width="stretch")
    else:
        st.info(t("perf_rien_appris", n=poids.get("n_min_per_level", "—")))
    gele = ", ".join(poids.get("frozen", []))
    if gele:
        st.caption(t("perf_geles", liste=gele))
    rythme = [{t("col_niche"): n, t("col_reference"): d.get("reference_s"),
               t("col_ajuste"): d.get("adjusted_s"), t("col_source"): d.get("source")}
              for n, d in poids.get("cut_rhythm", {}).items()]
    if rythme:
        st.markdown(f"**{t('perf_rythme')}**")
        st.dataframe(rythme, hide_index=True, width="stretch")
    st.caption(t("perf_regles", n=len(poids.get("retention_rules", []))))

c.bouton_tache("learn", ["learn"], "perf_recalculer")
