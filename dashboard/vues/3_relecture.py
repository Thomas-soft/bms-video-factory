"""Relecture : les scripts en attente, jugés par lots, décisions écrites par `review.py`."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import commun as c  # noqa: E402
from commun import t  # noqa: E402

from factory.core import config as config_module  # noqa: E402
from factory.core.paths import RunPaths  # noqa: E402
from factory.orchestrator import review  # noqa: E402
from factory.orchestrator.queue import ErreurFile  # noqa: E402

c.entete("page_relecture")
if message := st.session_state.pop("flash_relecture", None):
    st.success(message)

cfg = config_module.charger(c.racine(), strict=False)
equipe = {r.id: r.nom for r in (cfg.team.relecteurs if cfg.team else [])}
if not equipe:
    st.error(t("rel_pas_equipe"))
    st.stop()
relecteur = st.selectbox(t("rel_relecteur"), list(equipe), format_func=equipe.get,
                         key="relecteur")
chaine = st.selectbox(t("rel_chaine"), [""] + c.chaines(),
                      format_func=lambda x: x or t("toutes"))

conn = c.base()
try:
    fiches = review.en_attente(conn, chaine or None, racine=c.racine())
finally:
    conn.close()
st.caption(t("rel_compte", n=len(fiches)))
if not fiches:
    st.success(t("rel_rien"))
    st.stop()


def _decider(geste, fiche, *args, **options) -> None:
    """Appelle `review.<geste>` ; le message survit au rerun qui rafraîchit la liste."""
    conn = c.base()
    try:
        review.verifier_relecteur(relecteur, c.racine())
        resultat = geste(conn, fiche, relecteur, *args, racine=c.racine(), **options)
    except ErreurFile as erreur:
        st.error(str(erreur))
        return
    finally:
        conn.close()
    job = resultat[0] if isinstance(resultat, tuple) else resultat
    st.session_state["flash_relecture"] = t("rel_fait", job=job.id, statut=t(f"statut_{job.status}"),
                                            relecteur=equipe[relecteur])
    st.rerun()


for rang, fiche in enumerate(fiches, 1):
    job = fiche.job
    chemins = RunPaths.depuis_video_id(job.video_id, c.racine())
    script = json.loads(chemins.script.read_text(encoding="utf-8"))
    with st.container(border=True):
        st.markdown(f"#### {rang}/{len(fiches)} · {fiche.titre}")
        st.caption(f"#{job.id} · {fiche.channel_id} · {job.video_id}")
        for alerte in fiche.alertes:
            st.warning(c.masquer(alerte))
        st.markdown(f"**{t('rel_hook')}** ({fiche.hook_type}) — {fiche.hook}  \n"
                    f"**{t('rel_angle')}** — {fiche.angle}")
        k2, k3, k4 = st.columns(3)
        k2.metric(t("rel_duree"), f"{fiche.duree_estimee_s / 60:.1f} min",
                  delta=fiche.ecart_duree, delta_color="off",
                  help=t("rel_duree_aide", cible=fiche.duree_cible_s / 60))
        k3.metric(t("rel_densite"), "—" if fiche.densite is None else f"{fiche.densite:.1f}")
        k4.metric(t("rel_rejets"), fiche.rejets)
        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button(t("rel_approuver"), key=f"approuver_{job.id}", type="primary"):
                _decider(review.approuver, fiche)
        with b2:
            motif = st.text_input(t("rel_motif"), key=f"motif_{job.id}")
            if st.button(t("rel_rejeter"), key=f"rejeter_{job.id}", disabled=not motif.strip()):
                _decider(review.rejeter, fiche, motif.strip())
        with b3:
            with st.popover(t("rel_editer")):
                with st.form(f"edition_{job.id}"):
                    hook = st.text_area(t("rel_hook"), script["hook"]["text"], key=f"hook_{job.id}")
                    textes = [st.text_area(seg["role"], seg["narration"], key=f"seg_{job.id}_{i}")
                              for i, seg in enumerate(script["segments"])]
                    if st.form_submit_button(t("rel_valider_edition")):
                        nouveau = json.loads(json.dumps(script))
                        nouveau["hook"]["text"] = hook
                        for seg, texte in zip(nouveau["segments"], textes):
                            seg["narration"] = texte

                        def _ecrire(commande: list[str], contenu=nouveau) -> int:
                            # « L'éditeur » est ce formulaire : `review.editer` revalide ensuite.
                            Path(commande[-1]).write_text(
                                json.dumps(contenu, ensure_ascii=False, indent=2), encoding="utf-8")
                            return 0

                        _decider(review.editer, fiche, ouvrir=_ecrire)
        with st.expander(t("rel_texte", mots=fiche.mots, n=fiche.n_segments)):
            for seg in script["segments"]:
                st.markdown(f"**{seg['role']}** — {seg['narration']}")
