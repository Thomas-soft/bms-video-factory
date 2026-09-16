"""Ligne de commande de l'usine — point d'entrée `factory`."""
from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from factory import __version__
from factory.core import config as config_module
from factory.doctor import charge_env, execute

app = typer.Typer(
    add_completion=False,
    help="Usine à vidéos BMS — production locale, 0 €, un modèle en mémoire à la fois.",
)
console = Console()

config_app = typer.Typer(add_completion=False, help="Configuration : validation et lecture.")
app.add_typer(config_app, name="config")

COULEURS = {"PASS": "green", "FAIL": "red", "WARN": "yellow", "SKIP": "dim"}


@app.command()
def version() -> None:
    """Affiche la version du paquet."""
    console.print(f"factory {__version__}")


@app.command()
def doctor(
    quick: bool = typer.Option(
        False, "--quick", help="Saute les tests de génération (LLM, TTS, ASR, image, profondeur)."
    ),
) -> None:
    """Vérifie chaque brique par un test de fumée. Code de retour 0 si tout passe."""
    charge_env()
    resultats = execute(quick=quick)

    table = Table(title="factory doctor", title_style="bold", header_style="bold")
    table.add_column("Brique")
    table.add_column("État", justify="center")
    table.add_column("Détail")
    table.add_column("Temps", justify="right")
    for r in resultats:
        table.add_row(
            r.nom,
            f"[{COULEURS[r.etat]}]{r.etat}[/]",
            r.message,
            "—" if r.saute else f"{r.secondes:.1f} s",
        )
    console.print(table)

    echecs = [r for r in resultats if not r.ok and not r.saute]
    total = sum(r.secondes for r in resultats)
    if echecs:
        console.print(
            f"[red]{len(echecs)} brique(s) en échec[/] — {total:.0f} s : "
            + ", ".join(r.nom for r in echecs)
        )
        raise typer.Exit(code=1)
    sautes = sum(1 for r in resultats if r.saute)
    alertes = [r for r in resultats if r.alerte]
    if alertes:
        console.print(
            f"[yellow]{len(alertes)} alerte(s), sans effet sur le code de retour[/] : "
            + ", ".join(f"{r.nom} — {r.message}" for r in alertes)
        )
    suffixe = f", {sautes} sautée(s)" if sautes else ""
    verdict = "Environnement sain" if alertes else "Tout passe"
    console.print(f"[green]{verdict}[/] — {len(resultats) - sautes} contrôles en {total:.0f} s{suffixe}.")


@config_app.command("validate")
def config_validate(
    chemin: Path | None = typer.Argument(
        None, help="Fichier à valider seul ; sinon, tout config/ est validé."
    ),
    fichier: Path | None = typer.Option(
        None, "--file", help="Équivalent de l'argument positionnel."
    ),
    kind: str | None = typer.Option(
        None, "--kind", help="Genre du fichier (channels, languages, niches, styles, products…)."
    ),
) -> None:
    """Valide la configuration. Retourne 0 si tout valide, 1 sinon."""
    cible = fichier or chemin
    if cible is not None:
        problemes = config_module.valider_fichier(cible, kind)
        portee = str(cible)
    else:
        problemes = config_module.valider()
        portee = "config/"

    erreurs = [p for p in problemes if p.niveau == "erreur"]
    alertes = [p for p in problemes if p.niveau == "avertissement"]
    for probleme in erreurs:
        console.print(f"[red]ERREUR[/] {probleme.fichier} : {probleme.message}")
    for probleme in alertes:
        console.print(f"[yellow]ALERTE[/] {probleme.fichier} : {probleme.message}")

    if erreurs:
        console.print(f"[red]{len(erreurs)} erreur(s)[/] dans {portee}.")
        raise typer.Exit(code=1)
    console.print(
        f"[green]{portee} valide[/]"
        + (f" — {len(alertes)} alerte(s), sans effet sur le code de retour." if alertes else ".")
    )


@config_app.command("show")
def config_show(channel_id: str = typer.Argument(..., help="Identifiant de chaîne.")) -> None:
    """Affiche la configuration résolue d'une chaîne."""
    try:
        cfg = config_module.charger(strict=False)
        channel = cfg.get_channel(channel_id)
    except KeyError as erreur:
        console.print(f"[red]{erreur.args[0]}[/]")
        raise typer.Exit(code=1) from erreur

    langue = cfg.languages.get(channel.lang)
    niche = cfg.niches.get(channel.niche)
    style = cfg.styles.get(channel.style)
    voix = cfg.voix_de(channel)

    table = Table(title=f"{channel.name} ({channel.id})", title_style="bold", header_style="bold")
    table.add_column("Champ")
    table.add_column("Valeur résolu" + "e")
    table.add_row("Langue", f"{langue.name} ({channel.lang})" if langue else f"[red]{channel.lang} inconnue[/]")
    table.add_row(
        "Voix",
        f"{voix.id} — {voix.engine}, {voix.gender}" + (f", {voix.note_ecoute}" if voix and voix.note_ecoute else "")
        if voix else f"[red]{channel.voice_id} absente de la langue[/]",
    )
    table.add_row("Niche", channel.niche)
    if niche:
        table.add_row("  Rythme de coupe visé", f"{niche.rythme_coupe_s.cible_effective():.2f} s/plan"
                      + (" [yellow](valeur de secours, non mesurée)[/]" if niche.rythme_coupe_s.a_mesurer else ""))
        table.add_row("  Durée cible", f"{niche.duree_s.cible} s ± {niche.duree_s.tolerance:.0%}")
        table.add_row("  Débit", f"{niche.mots_par_minute.mediane:.0f} mots/min")
    table.add_row("Style", f"{channel.style} → moteur {style.engine} ({style.statut})" if style
                  else f"[red]{channel.style} inconnu[/]")
    table.add_row("Gabarits", ", ".join(channel.templates))
    table.add_row("Charte", f"version {channel.charte.version}, "
                            f"transitions {', '.join(channel.charte.transitions)}")
    table.add_row(
        "Cadence",
        f"{channel.cadence.per_week_max}/semaine — {', '.join(channel.cadence.days)} à "
        f"{', '.join(channel.cadence.hours_local)} ({channel.cadence.timezone}), "
        f"jitter ± {channel.cadence.jitter_min} min",
    )
    table.add_row("Chemin de publication", channel.publish_path
                  + ("" if channel.youtube.audit_passed else " (audit API non obtenu)"))
    table.add_row("Promotion payante", "oui" if channel.paid_promotion else "non")
    table.add_row("Produits", ", ".join(channel.products) or "aucun")
    table.add_row("Relecture", "auto-approve" if channel.auto_approve else "humaine, par lots")
    table.add_row("Jeton OAuth", f"{channel.google_account.token_ref} (référence, jamais la valeur)")
    table.add_row("Bibliothèque",
                  f"cooldown {channel.library.cooldown_videos} vidéos, "
                  f"{channel.library.max_uses_per_channel} emplois max")
    console.print(table)

    erreurs = [p for p in cfg.erreurs if channel.id in p.fichier]
    for probleme in erreurs:
        console.print(f"[red]ERREUR[/] {probleme.fichier} : {probleme.message}")
    if erreurs:
        raise typer.Exit(code=1)


@app.command("plan")
def commande_plan(
    channel: str = typer.Option(..., "--channel", help="Identifiant de la chaîne."),
    topic: str | None = typer.Option(None, "--topic", help="Sujet imposé ; tracé source=manuel."),
    product: str | None = typer.Option(None, "--product", help="Produit d'affiliation."),
) -> None:
    """Choisit le sujet dans le référentiel et crée le run (spec.json, manifest.json)."""
    from factory.steps import plan as etape_plan

    resultat = etape_plan.executer(channel, topic=topic, product_id=product)
    spec = resultat.spec
    table = Table(title=f"plan — {spec.video_id}", header_style="bold")
    table.add_column("Champ")
    table.add_column("Valeur")
    table.add_row("Sujet", spec.topic.sujet)
    table.add_row("Source", spec.topic.source
                  + (f" (rang {spec.topic.evidence.n}, {resultat.sujets_ecartes} déjà pris)"
                     if spec.topic.source == "referentiel" else ""))
    if spec.topic.evidence.ratio is not None:
        table.add_row("Preuve", f"ratio {spec.topic.evidence.ratio}× la médiane de "
                                f"{spec.topic.evidence.vues_medianes_chaine} vues")
    table.add_row("Durée cible", f"{spec.target_duration_s} s")
    table.add_row("Rythme de coupe", f"{spec.cut_rhythm_target_s} s")
    table.add_row("Graine", str(spec.seed))
    table.add_row("Produit", spec.product_id or "aucun")
    console.print(table)
    for alerte in resultat.alertes:
        console.print(f"[yellow]ALERTE[/] {alerte}")
    console.print(f"[green]run créé[/] en {resultat.secondes:.2f} s → {resultat.chemins.racine}")


@app.command("research")
def commande_research(
    run: str = typer.Option(..., "--run", help="Identifiant du run."),
) -> None:
    """Collecte des faits sourcés sur API gratuites et choisit un angle éditorial."""
    from factory.steps import research as etape_research

    recherche, secondes, alertes = etape_research.executer(run)
    table = Table(title=f"research — {run}", header_style="bold")
    table.add_column("Champ")
    table.add_column("Valeur")
    table.add_row("Sources retenues", str(recherche.source_count))
    table.add_row("Faits", str(recherche.fact_count))
    table.add_row("Entités", str(len(recherche.entities)))
    table.add_row("Sources écartées", str(len(recherche.sources_rejected)))
    table.add_row("Angle retenu", recherche.angle)
    table.add_row("Signature", recherche.angle_signature)
    table.add_row("Éléments propriétaires", str(len(recherche.elements_proprietaires)))
    console.print(table)
    for alerte in alertes:
        console.print(f"[yellow]ALERTE[/] {alerte}")
    console.print(f"[green]research.json écrit[/] en {secondes:.1f} s")


@app.command("script")
def commande_script(
    run: str = typer.Option(..., "--run", help="Identifiant du run."),
) -> None:
    """Écrit le script structuré : hook typé, segments, boucles ouvertes, signature."""
    from factory.steps import script as etape_script

    resultat = etape_script.executer(run)
    script = resultat.script
    table = Table(title=f"script — {run}", header_style="bold")
    table.add_column("Champ")
    table.add_column("Valeur")
    table.add_row("Type de hook tiré", f"{resultat.hook_type} (part {resultat.hook_part:.1%})")
    table.add_row("Hook", f"{len(script.hook.text.split())} mots")
    table.add_row("Segments", str(len(script.segments)))
    table.add_row("Mots", f"{script.word_count} (cible {resultat.mots_cibles})")
    table.add_row("Durée estimée", f"{script.estimated_duration_s:.0f} s")
    table.add_row("Boucles ouvertes",
                  f"{sum(1 for s in script.segments if s.open_loop == 'plant')} plantées, "
                  f"{sum(1 for s in script.segments if s.open_loop == 'payoff')} payées")
    table.add_row("Signature", script.editorial_signature.angle)
    table.add_row("Corrections de durée", str(resultat.corrections))
    table.add_row("Appels LLM", f"{len(resultat.trace.appels)} en {resultat.trace.secondes:.0f} s")
    console.print(table)
    for alerte in resultat.alertes:
        console.print(f"[yellow]ALERTE[/] {alerte}")
    console.print(f"[green]script.json écrit[/] en {resultat.secondes:.1f} s")



@app.command("voice")
def commande_voice(
    run: str = typer.Option(..., "--run", help="Identifiant du run."),
    force: bool = typer.Option(False, "--force", help="Resynthétise même si les WAV existent."),
) -> None:
    """Synthétise la voix off, la normalise à -14 LUFS et horodate chaque segment."""
    from factory.steps import voice as etape_voice

    resultat = etape_voice.executer(run, force=force)
    timings = resultat.timings
    table = Table(title=f"voice — {run}", header_style="bold")
    table.add_column("Champ")
    table.add_column("Valeur")
    table.add_row("Voix", f"{timings.voice_id} ({timings.engine}, vitesse {timings.speed:g})")
    table.add_row("Unités de synthèse", f"{len(resultat.unites)} pour {len(timings.segments)} segments")
    table.add_row("Durée", f"{timings.total_duration_s:.1f} s")
    table.add_row("Loudness", f"{timings.loudness_lufs} LUFS · crête réelle "
                              f"{timings.true_peak_dbtp} dBTP")
    table.add_row("Écart / script", f"{resultat.ecart_duree * 100:+.1f} % "
                                    f"({resultat.duree_estimee_script_s:.0f} s estimées)")
    table.add_row("Temps", f"{resultat.secondes:.0f} s dont {resultat.secondes_tts:.0f} s de TTS"
                           + (f" (facteur temps réel {resultat.rtf:.2f})" if resultat.rtf else ""))
    console.print(table)
    for alerte in resultat.alertes:
        console.print(f"[yellow]ALERTE[/] {alerte}")
    console.print(f"[green]voice/voice.wav et voice/timings.json écrits[/]")


@app.command("subtitles")
def commande_subtitles(
    run: str = typer.Option(..., "--run", help="Identifiant du run."),
    engine: str | None = typer.Option(
        None, "--engine", help="Force un moteur ASR (parakeet|whisper) et coupe le repli."
    ),
    force: bool = typer.Option(False, "--force", help="Ignore le cache de transcription."),
) -> None:
    """Aligne l'ASR sur le texte du script et écrit words.json, subtitles.srt et subtitles.ass."""
    from factory.steps import subtitles as etape_soustitres

    resultat = etape_soustitres.executer(run, moteur=engine, force=force)
    words = resultat.words
    table = Table(title=f"subtitles — {run}", header_style="bold")
    table.add_column("Champ")
    table.add_column("Valeur")
    table.add_row("Moteur retenu", resultat.retenue.etiquette
                  + (f" (repli : {words.fallback_reason})" if words.fallback_reason else ""))
    table.add_row("Mots", f"{len(words.words)} du script, {len(resultat.retenue.mots_asr)} entendus")
    table.add_row("Couverture", f"{words.coverage:.3f} (cible 1,0)")
    table.add_row("WER contre le script", f"{words.wer_vs_script:.2%} brut · "
                                          f"{resultat.retenue.wer_hors_nombres:.2%} hors nombres "
                                          f"(seuil {words.wer_threshold:.0%})")
    table.add_row("Sous-titres", f"{resultat.cues} cues · ligne la plus longue "
                                 f"{resultat.ligne_la_plus_longue} caractères")
    table.add_row("Plus long trou", f"{resultat.trous_max_s:.1f} s")
    table.add_row("Temps", f"{resultat.secondes:.0f} s dont {resultat.secondes_asr:.0f} s d'ASR")
    console.print(table)
    for alerte in resultat.alertes:
        console.print(f"[yellow]ALERTE[/] {alerte}")
    console.print("[green]words.json, subtitles.srt et subtitles.ass écrits[/]")



@app.command("shotlist")
def commande_shotlist(
    run: str = typer.Option(..., "--run", help="Identifiant du run."),
    style: str | None = typer.Option(
        None, "--style", help="Surcharge le style de la chaîne (type d'asset demandé par plan)."
    ),
) -> None:
    """Découpe le script en plans au rythme de coupe de la niche et écrit shotlist.json."""
    from factory.steps import shotlist as etape_shotlist

    try:
        resultat = etape_shotlist.executer(run, style_surcharge=style)
    except etape_shotlist.ContratNonSatisfait as erreur:
        console.print(f"[red]shotlist refusée[/] {erreur}")
        raise typer.Exit(code=2) from erreur
    except (ValueError, KeyError) as erreur:
        console.print(f"[red]configuration invalide[/] {erreur}")
        raise typer.Exit(code=1) from erreur

    stats = resultat.shotlist.stats
    table = Table(title=f"shotlist — {run}", header_style="bold")
    table.add_column("Champ")
    table.add_column("Valeur")
    table.add_row("Plans", f"{stats.n_shots} sur {len({s.segment_id for s in resultat.shotlist.shots})} segments")
    table.add_row("Cible", f"{stats.target_s:.2f} s ({resultat.source_cible})")
    table.add_row(
        "Médiane hors hook",
        f"{stats.median_shot_s:.2f} s · écart {resultat.ecart_relatif:+.1%} "
        f"(tolérance ±{stats.tolerance:.0%})",
    )
    table.add_row("Déciles", f"p10 {stats.p10_shot_s:.2f} s · p90 {stats.p90_shot_s:.2f} s")
    table.add_row(
        "Hook",
        f"médiane {stats.median_hook_s:.2f} s · plafond {stats.hook_shots_max_s:.2f} s"
        if stats.median_hook_s is not None else "aucun plan de hook",
    )
    table.add_row("Ruptures", str(sum(1 for s in resultat.shotlist.shots if s.interrupt)))
    table.add_row("Sponsor", str(sum(1 for s in resultat.shotlist.shots if s.is_sponsor)))
    table.add_row("Essais", f"{resultat.essais} (graine {resultat.graine})")
    table.add_row("Temps", f"{resultat.secondes:.2f} s")
    console.print(table)
    for alerte in resultat.alertes:
        console.print(f"[yellow]ALERTE[/] {alerte}")
    console.print("[green]shotlist.json écrit[/]")


@app.command("render")
def commande_render(
    run: str = typer.Option(..., "--run", help="Identifiant du run."),
    style: str | None = typer.Option(None, "--style", help="Surcharge le style de la chaîne."),
    force: bool = typer.Option(False, "--force", help="Re-rend les clips déjà conformes."),
) -> None:
    """Rend un clip par plan avec le moteur du style, et vérifie chacun par ffprobe."""
    from factory.steps import render as etape_rendu

    from factory.styles import MoteurIndisponible

    try:
        resultat = etape_rendu.executer(run, style_surcharge=style, force=force)
    except (MoteurIndisponible, KeyError) as erreur:
        console.print(f"[red]moteur indisponible[/] {erreur}")
        raise typer.Exit(code=1) from erreur
    except FileNotFoundError as erreur:
        console.print(f"[red]contrat d'entrée non satisfait[/] {erreur}")
        raise typer.Exit(code=2) from erreur
    except etape_rendu.RenduIncomplet as erreur:
        console.print(f"[red]rendu incomplet[/] {erreur}")
        if erreur.resultat is not None:
            for ecart in erreur.resultat.ecarts[:10]:
                console.print(f"  [red]•[/] {ecart}")
        raise typer.Exit(code=1) from erreur

    table = Table(title=f"render — {run}", header_style="bold")
    table.add_column("Champ")
    table.add_column("Valeur")
    table.add_row("Style", f"{resultat.style_id} → moteur {resultat.moteur}")
    table.add_row("Clips", f"{resultat.clips} au contrat (1920×1080, 30 ips, ±0,05 s)")
    table.add_row("Assets", f"{len(resultat.assets)} en {resultat.secondes_assets:.1f} s")
    table.add_row(
        "Temps par plan",
        f"médiane {resultat.secondes_median_par_plan:.2f} s · "
        f"total {resultat.secondes_total:.1f} s",
    )
    console.print(table)
    for alerte in resultat.alertes:
        console.print(f"[yellow]ALERTE[/] {alerte}")
    console.print(f"[green]{resultat.clips} clip(s) écrits dans clips/[/]")


if __name__ == "__main__":
    app()
