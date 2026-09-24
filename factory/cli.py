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

publish_app = typer.Typer(
    add_completion=False, help="Publication : consentement OAuth et upload privé."
)
app.add_typer(publish_app, name="publish")

editorial_app = typer.Typer(
    add_completion=False,
    help="Entrepôt concurrentiel : chaînes suivies, collecte quotidienne, vélocité.",
)
app.add_typer(editorial_app, name="editorial")

queue_app = typer.Typer(
    add_completion=False, help="File de production : enfiler, regarder, débloquer."
)
app.add_typer(queue_app, name="queue")

daemon_app = typer.Typer(
    add_completion=False, help="Daemon de production : fenêtre nocturne, un run à la fois."
)
app.add_typer(daemon_app, name="daemon")

backup_app = typer.Typer(
    add_completion=False, help="Sauvegarde de l'actif : base, manifestes, config, appris."
)
app.add_typer(backup_app, name="backup")

calendar_app = typer.Typer(
    add_completion=False, help="Calendrier de publication : cadence, créneaux, jitter (étape 23.2).")
app.add_typer(calendar_app, name="calendar")

watch_app = typer.Typer(add_completion=False, help="Chaînes suivies (registre + ajouts).")
editorial_app.add_typer(watch_app, name="watch")

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
    dry_run: bool = typer.Option(False, "--dry-run",
                                 help="Liste les prochains sujets de la file sans créer de run."),
    n: int = typer.Option(10, "--n", help="Nombre de sujets listés avec --dry-run."),
) -> None:
    """Choisit le sujet dans le référentiel et crée le run (spec.json, manifest.json)."""
    from factory.steps import plan as etape_plan

    if dry_run:
        from factory.analytics import weights as wmod
        from factory.core.paths import racine_projet

        poids = wmod.charger(racine_projet())
        console.print(f"poids appris : {wmod.etiquette(poids) or 'aucun (référentiel)'}")
        for rang, x in enumerate(etape_plan.apercu(channel, n), 1):
            console.print(f"{rang:2d}. {x['score_adjusted']:.4f} (×{x['multiplier']:.2f}, "
                          f"{x['cluster']}) {x['topic']}", markup=False, highlight=False)
        return

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
    rapport = resultat.rapport
    if rapport is not None:
        densite = rapport.densite
        cible = rapport.densite_cible
        table.add_row("Densité", (
            f"{densite.faits_par_minute:.2f} fait/min"
            + (f" (cible {cible:.2f})" if cible else " (aucune cible de niche)")
            + f" · {densite.part_entites:.0%} d'entités" if densite else "non mesurée"))
        table.add_row("Ruptures", f"{rapport.ruptures_posees} posées, cadence "
                                  f"{rapport.cadence_s:.0f} s, écart max "
                                  f"{rapport.ecart_rupture_max_s:.0f} s")
        payees = sum(1 for b in rapport.boucles if b.payee)
        table.add_row("Boucles vérifiées", f"{payees}/{len(rapport.boucles)} payées "
                                           "(marqueurs + juge)")
        table.add_row("Régénérations", str(resultat.regenerations))
    table.add_row("Appels LLM", f"{len(resultat.trace.appels)} en {resultat.trace.secondes:.0f} s")
    console.print(table)
    for alerte in resultat.alertes:
        console.print(f"[yellow]ALERTE[/] {alerte}")
    if rapport is not None:
        for infraction in rapport.infractions:
            couleur = "red" if infraction.bloquante else "yellow"
            console.print(f"[{couleur}]INFRACTION[/] {infraction}")
    console.print(f"[green]script.json écrit[/] en {resultat.secondes:.1f} s")
    if resultat.echec:
        console.print(f"[red]RUN EN ÉCHEC[/] {resultat.echec}")
        raise typer.Exit(code=4)



@app.command("localize")
def commande_localize(
    run: str = typer.Option(..., "--run", help="Run parent, exporté."),
    to: str = typer.Option(..., "--to", help="Chaîne cible, d'une autre langue."),
) -> None:
    """Décline un run exporté vers une chaîne d'une autre langue (adaptation, étape 24)."""
    from factory.steps import localize as etape_localize

    try:
        resultat = etape_localize.executer(run, to)
    except etape_localize.DeclinaisonImpossible as erreur:
        console.print(f"[red]DÉCLINAISON IMPOSSIBLE[/] {erreur}")
        raise typer.Exit(code=2) from erreur
    for alerte in resultat.alertes:
        console.print(f"[yellow]ALERTE[/] {alerte}")
    d = resultat.declinaison
    console.print(f"run enfant [bold]{resultat.video_id}[/] — état {resultat.etat}")
    if d is not None:
        console.print(
            f"assets réutilisés {d.assets_reused_ratio} · coût enfant ÷ parent {d.compute_ratio} "
            f"· distance pHash des miniatures {d.thumbnail_phash_distance}")
    if resultat.etat == "failed":
        raise typer.Exit(code=1)


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


@app.command("assemble")
def commande_assemble(
    run: str = typer.Option(..., "--run", help="Identifiant du run."),
    force: bool = typer.Option(False, "--force", help="Rejoue toutes les pièces du montage."),
) -> None:
    """Monte les clips : transitions, voix, lit musical ducké, sous-titres, -14 LUFS."""
    from factory.steps import assemble as etape_montage

    try:
        resultat = etape_montage.executer(run, force=force)
    except FileNotFoundError as erreur:
        console.print(f"[red]contrat d'entrée non satisfait[/] {erreur}")
        raise typer.Exit(code=2) from erreur
    except etape_montage.MontageImpossible as erreur:
        console.print(f"[red]montage impossible[/] {erreur}")
        raise typer.Exit(code=3) from erreur

    table = Table(title=f"assemble — {run}", header_style="bold")
    table.add_column("Champ")
    table.add_column("Valeur")
    table.add_row(
        "Transitions",
        " · ".join(f"{g} {n}" for g, n in resultat.transitions.items())
        + f" ({resultat.pieces_reencodees} pièce(s) réencodée(s))",
    )
    table.add_row(
        "Durée",
        f"{resultat.duree_video_s:.3f} s contre {resultat.duree_voix_s:.3f} s de voix "
        f"(écart {resultat.ecart_duree_s:.3f} s) · {resultat.images} images",
    )
    table.add_row("Musique", f"{resultat.musique} — {resultat.musique_motif}")
    table.add_row("Sous-titres", resultat.sous_titres)
    table.add_row("Loudness", f"{resultat.lufs} LUFS · crête {resultat.true_peak_dbtp} dBTP")
    table.add_row("Temps", f"{resultat.secondes:.1f} s")
    console.print(table)
    for alerte in resultat.alertes:
        console.print(f"[yellow]ALERTE[/] {alerte}")
    console.print(f"[green]{resultat.assembled.name} et {resultat.video_nomusic.name} écrits[/]")


@app.command("export")
def commande_export(
    run: str = typer.Option(..., "--run", help="Identifiant du run."),
    purge: bool = typer.Option(True, "--purge/--no-purge", help="Purge les intermédiaires."),
    reencode: bool = typer.Option(
        False, "--reencode", help="Force le réencodage même si le flux est déjà au contrat."
    ),
) -> None:
    """Produit `final.mp4` et le mesure : ffprobe, ebur128, plans détectés, images de contrôle."""
    from factory.steps import export as etape_export

    echec = None
    try:
        resultat = etape_export.executer(run, purger=purge, reencode=reencode)
    except FileNotFoundError as erreur:
        console.print(f"[red]contrat d'entrée non satisfait[/] {erreur}")
        raise typer.Exit(code=2) from erreur
    except etape_export.ExportNonConforme as erreur:
        if erreur.resultat is None:
            console.print(f"[red]export non conforme[/] {erreur}")
            raise typer.Exit(code=4) from erreur
        resultat, echec = erreur.resultat, erreur

    table = Table(title=f"export — {run}", header_style="bold")
    table.add_column("Mesure")
    table.add_column("Valeur")
    table.add_row(
        "Flux",
        f"{resultat.codec_video} {resultat.profil} {resultat.largeur}×{resultat.hauteur} "
        f"{resultat.fps:.0f} ips · {resultat.codec_audio} "
        + (f"{resultat.debit_audio_kbps:.0f} kb/s" if resultat.debit_audio_kbps else ""),
    )
    table.add_row(
        "Durée",
        f"{resultat.duree_s:.3f} s contre {resultat.duree_voix_s:.3f} s de voix "
        f"(écart {resultat.ecart_duree_s:.3f} s)",
    )
    table.add_row("Loudness", f"{resultat.lufs} LUFS · crête {resultat.true_peak_dbtp} dBTP")
    table.add_row(
        "Plans",
        f"{resultat.n_scenes} détecté(s) pour {resultat.n_shots} prévu(s) · "
        f"rythme mesuré {resultat.cut_rhythm_measured_s} s "
        f"(cible {resultat.cut_rhythm_target_s} s)",
    )
    table.add_row("Sous-titres", resultat.sous_titres)
    table.add_row("Fichier", f"{resultat.taille_mo:.1f} Mo · {resultat.final}")
    table.add_row("Images QC", f"{len(resultat.images_qc)} dans qc/frames/")
    table.add_row(
        "Temps",
        f"{resultat.secondes:.1f} s"
        + (f" · purge {resultat.purge_mo:.1f} Mo" if resultat.purge_mo else ""),
    )
    console.print(table)
    for alerte in resultat.alertes:
        console.print(f"[yellow]ALERTE[/] {alerte}")
    if echec is not None:
        for ecart in resultat.ecarts:
            console.print(f"  [red]•[/] {ecart}")
        console.print("[red]export non conforme : intermédiaires conservés[/]")
        raise typer.Exit(code=4)
    console.print(f"[green]{resultat.final.name} vérifié — copie dans {resultat.copie_export}[/]")


@app.command("qc")
def commande_qc(
    run: str = typer.Option(..., "--run", help="Identifiant du run."),
    video: Path | None = typer.Option(
        None, "--video", help="Note un autre fichier que final.mp4 (calibration)."
    ),
    json_sortie: bool = typer.Option(False, "--json", help="Écrit qc.json sur la sortie."),
    ecrire: bool = typer.Option(
        True, "--ecrire/--no-ecrire",
        help="Écrit qc.json et note le manifeste. `--no-ecrire` pour une mesure de calibration.",
    ),
) -> None:
    """Banc et portillon : mesure `final.mp4` face aux cibles de sa niche, rend un verdict."""
    from factory.eval import bench

    try:
        resultat = bench.executer(run, video=video, ecrire=ecrire)
    except FileNotFoundError as erreur:
        console.print(f"[red]contrat d'entrée non satisfait[/] {erreur}")
        raise typer.Exit(code=2) from erreur

    if json_sortie:
        console.print_json(data=resultat.json())
    else:
        table = Table(title=f"qc — {run}", header_style="bold")
        for colonne in ("Famille", "Mesure", "Valeur", "Cible", "Score", "Poids"):
            table.add_column(colonne)
        for famille in resultat.familles:
            note = "—" if famille.score is None else f"{famille.score:.0f}"
            for index, mesure in enumerate(famille.mesures):
                couleur = {"pass": "green", "warn": "yellow", "fail": "red"}.get(
                    mesure.statut, "dim"
                )
                table.add_row(
                    f"{famille.nom} ({note}/{famille.poids})" if index == 0 else "",
                    ("[bold]" if mesure.bloquant else "") + mesure.nom,
                    f"[{couleur}]{mesure.valeur}[/] {mesure.unite}",
                    "—" if mesure.cible is None else str(mesure.cible),
                    "—" if mesure.score is None else f"{mesure.score:.0f}",
                    str(mesure.poids),
                )
        console.print(table)
        for absent in resultat.absents:
            console.print(f"[yellow]entrée absente[/] {absent}")
        couleur = "green" if resultat.verdict == "PASS" else "red"
        console.print(
            f"[{couleur}]{resultat.verdict}[/] · score {resultat.score:.1f}/100 · "
            f"pipeline {resultat.verdict_pipeline} · {resultat.secondes:.1f} s"
        )
        for raison in resultat.raisons:
            console.print(f"  [red]•[/] {raison}")
        if resultat.etapes_a_rejouer:
            console.print(f"à rejouer : {', '.join(resultat.etapes_a_rejouer)}")
        if resultat.chemin is not None:
            console.print(f"écrit dans {resultat.chemin}")
        else:
            console.print("[dim]mesure non écrite (--no-ecrire)[/]")
    if resultat.verdict != "PASS":
        raise typer.Exit(code=4)


@app.command("thumbnail")
def commande_thumbnail(
    run: str = typer.Option(..., "--run", help="Identifiant du run."),
    variants: int = typer.Option(3, "--variants", help="Nombre de variantes composées."),
) -> None:
    """Compose la miniature et ses variantes, mesure contraste, hauteur de texte et poids."""
    from factory.steps import thumbnail as etape_miniature

    try:
        resultat = etape_miniature.executer(run, variantes=variants)
    except FileNotFoundError as erreur:
        console.print(f"[red]contrat d'entrée non satisfait[/] {erreur}")
        raise typer.Exit(code=2) from erreur
    except etape_miniature.MiniatureImpossible as erreur:
        console.print(f"[red]miniature impossible[/] {erreur}")
        raise typer.Exit(code=2) from erreur

    table = Table(title=f"thumbnail — {run}", header_style="bold")
    table.add_column("Champ")
    table.add_column("Valeur")
    table.add_row("Fond", f"{resultat.fond_shot} — {resultat.fond_source}")
    table.add_row("Gabarit", resultat.gabarit)
    promesse = {True: "tenue", False: "[red]non tenue[/]", None: "[yellow]non vérifiée[/]"}
    table.add_row("Titres", f"{resultat.n_titres} variantes · retenu « {resultat.titre_retenu} » "
                            f"· promesse {promesse[resultat.promesse_tenue]}")
    for ligne in resultat.duels:
        table.add_row("  duel", ligne)
    for variante in resultat.variantes:
        mesures = variante.measures
        table.add_row(
            f"  {variante.file.split('/')[-1]}"
            + ("  ←" if variante.file.endswith(f"{resultat.retenue}.png") else ""),
            f"« {variante.text} » · {variante.template}/{variante.palette} · "
            f"contraste {variante.contrast_ratio} · "
            f"texte {(mesures.text_height_px_168 if mesures else 0) or 0:.1f} px à 168 · "
            f"surface {(mesures.text_area_pct if mesures else 0) or 0:.1f} % · "
            f"netteté {(mesures.sharpness_168 if mesures else 0) or 0:.0f} · "
            f"score {variante.score}",
        )
    if resultat.rotation:
        table.add_row("Rotation", f"après {resultat.rotation.after_days} j si "
                                  f"{resultat.rotation.criterion} → "
                                  f"{', '.join(resultat.rotation.next_variants) or 'rien'}")
    table.add_row("Temps", f"{resultat.secondes:.1f} s dont {resultat.secondes_llm:.0f} s de LLM"
                           + (f" ({resultat.appels_caches} appel(s) servis par le cache)"
                              if resultat.appels_caches else ""))
    console.print(table)
    for alerte in resultat.alertes:
        console.print(f"[yellow]ALERTE[/] {alerte}")
    console.print(f"[green]thumbnail.png écrit[/] ({resultat.retenue})")


@app.command("metadata")
def commande_metadata(
    run: str = typer.Option(..., "--run", help="Identifiant du run."),
) -> None:
    """Compose `metadata.json` : titre, description à blocs, tags, drapeaux de conformité."""
    from factory.steps import metadata as etape_metadata

    try:
        resultat = etape_metadata.executer(run)
    except FileNotFoundError as erreur:
        console.print(f"[red]contrat d'entrée non satisfait[/] {erreur}")
        raise typer.Exit(code=2) from erreur

    meta = resultat.metadata
    table = Table(title=f"metadata — {run}", header_style="bold")
    table.add_column("Champ")
    table.add_column("Valeur")
    table.add_row("Titre", f"« {meta.title_chosen} » ({len(meta.title_chosen)} caractères)")
    table.add_row("Variantes", f"{len(meta.title_variants)} titres conservés")
    table.add_row("Description", f"{len(meta.description.encode('utf-8'))} octets · "
                                 f"{len(meta.chapters)} chapitres · "
                                 f"{len(meta.description_blocks.summary)} ligne(s) de sommaire")
    table.add_row("Divulgation", meta.description_blocks.disclosure or "[red]aucune[/]")
    cumul_tags = (sum(meta.cout_tag(t) for t in meta.tags) + max(0, len(meta.tags) - 1))
    table.add_row("Tags", f"{len(meta.tags)} · {cumul_tags} caractères cumulés "
                          f"(guillemets compris)")
    table.add_row("Hashtags", " ".join(meta.hashtags) or "[yellow]aucun[/]")
    table.add_row("Commentaire épinglé",
                  (meta.pinned_comment or "[yellow]aucun[/]").splitlines()[0][:70])
    table.add_row("Localisations", ", ".join(sorted(meta.localizations)) or "aucune (étape 24)")
    table.add_row("Catégorie", f"{meta.category_id} · langue {meta.default_language}")
    table.add_row("Contenu synthétique",
                  ("oui — " + (meta.contains_synthetic_media_reason or ""))
                  if meta.contains_synthetic_media else "non (assistance de production)")
    table.add_row("Promotion payante", "oui" if meta.paid_promotion else "non")
    table.add_row("Attribution", f"{len(meta.description_blocks.attribution)} ligne(s) · "
                                 f"{len(meta.description_blocks.sources)} source(s)")
    console.print(table)
    for alerte in resultat.alertes:
        console.print(f"[yellow]ALERTE[/] {alerte}")
    console.print(f"[green]metadata.json écrit[/] en {resultat.secondes:.1f} s")


@app.command("run")
def commande_run(
    channel: str | None = typer.Option(None, "--channel", help="Chaîne : crée un run neuf."),
    run: str | None = typer.Option(None, "--run", help="Run existant : reprise."),
    topic: str | None = typer.Option(None, "--topic", help="Sujet imposé au plan."),
    depuis: str | None = typer.Option(None, "--from", help="Étape de reprise."),
    style: str | None = typer.Option(None, "--style", help="Surcharge le style de la chaîne."),
) -> None:
    """Enchaîne tout le DAG jusqu'à l'export, avec reprise et manifeste finalisé."""
    from factory import run as orchestrateur

    charge_env()
    try:
        resultat = orchestrateur.executer(
            channel_id=channel, video_id=run, topic=topic, depuis=depuis, style=style
        )
    except (ValueError, FileNotFoundError) as erreur:
        console.print(f"[red]{erreur}[/]")
        raise typer.Exit(code=1) from erreur
    except orchestrateur.EchecEtape as erreur:
        console.print(f"[red]{erreur}[/]")
        raise typer.Exit(code=erreur.code) from erreur

    table = Table(title=f"run — {resultat.video_id}", header_style="bold")
    table.add_column("Étape")
    table.add_column("Code", justify="center")
    table.add_column("Temps", justify="right")
    for etape in resultat.etapes:
        couleur = "dim" if etape.saute else ("green" if etape.code == 0 else
                                             "yellow" if etape.code == 4 else "red")
        table.add_row(etape.nom, f"[{couleur}]{'sauté' if etape.saute else etape.code}[/]",
                      "—" if etape.saute else f"{etape.secondes:.0f} s")
    console.print(table)

    cout = ("non calculé" if resultat.cout_eur is None
            else f"{resultat.cout_eur:.3f} €" + (" (estimé)" if resultat.cout_estime else ""))
    console.print(
        f"État [bold]{resultat.etat}[/] · horloge {resultat.secondes / 60:.1f} min · "
        f"calcul {resultat.compute_min:.1f} min · coût {cout} · "
        f"disque {resultat.disque_mo:.0f} Mo · journal {resultat.journal}"
    )
    if resultat.secondes > 90 * 60:
        console.print(f"[yellow]Le run a dépassé 90 minutes ({resultat.secondes / 60:.0f} min)[/] "
                      "— donnée pour le jalon serveur, pas un échec.")
    for alerte in resultat.alertes:
        console.print(f"[yellow]ALERTE[/] {alerte}")
    if resultat.raison:
        console.print(f"[yellow]{resultat.raison}[/]")
    if resultat.etat == "failed":
        raise typer.Exit(code=3)


@publish_app.command("auth")
def publish_auth(
    channel: str = typer.Option(..., "--channel", help="Chaîne de config/channels/."),
    show: bool = typer.Option(False, "--show", help="N'ouvre rien : décrit le jeton existant."),
) -> None:
    """Consentement OAuth d'une chaîne, puis `channels.list?mine=true` pour preuve."""
    from factory.publish import oauth

    charge_env()
    if show:
        etat = oauth.etat_jeton(channel)
        console.print(etat)
        raise typer.Exit(code=0 if etat.get("present") else 1)

    try:
        oauth.autoriser(channel)
    except oauth.ErreurOAuth as erreur:
        console.print(f"[red]{erreur}[/]")
        raise typer.Exit(code=1) from erreur

    console.print(f"[green]Jeton enregistré[/] — secrets/tokens/{channel}.json (mode 600)")

    try:
        chaines = oauth.chaines_du_compte(channel)
    except Exception as erreur:  # noqa: BLE001 — l'appel de contrôle ne doit pas perdre le jeton
        console.print(f"[yellow]channels.list a échoué[/] : {erreur}")
        raise typer.Exit(code=1) from erreur

    table = Table(title="channels.list?mine=true — 1 unité", header_style="bold")
    table.add_column("channel_id")
    table.add_column("Titre")
    table.add_column("Playlist uploads")
    for c in chaines:
        table.add_row(c.channel_id, c.titre, c.playlist_uploads or "—")
    console.print(table)
    if not chaines:
        console.print("[yellow]Aucune chaîne : le compte connecté n'en détient pas.[/] "
                      "Reconnecte-toi en choisissant la chaîne (Brand Account), pas le compte.")
        raise typer.Exit(code=1)
    console.print("Reporte le channel_id dans [bold]config/channels/"
                  f"{channel}.yaml[/] (youtube.channel_id) et la playlist dans playlist_id.")


@publish_app.command("upload")
def publish_upload(
    run: str = typer.Option(..., "--run", help="Identifiant du run à publier."),
    channel: str = typer.Option(..., "--channel", help="Chaîne de config/channels/."),
    at: str = typer.Option(None, "--at", help="Programmation ISO-8601 (après audit seulement)."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Contrôles seuls : aucun appel d'API."),
    force: bool = typer.Option(False, "--force",
                               help="Publie sans job de rapports. Les impressions seront perdues."),
) -> None:
    """`videos.insert` privé, miniature, sous-titres, playlist, puis vérification."""
    from factory.core import db
    from factory.publish import quota, youtube

    charge_env()
    conn = db.ouvrir()
    try:
        manque = youtube.premiere_publication_sans_job(conn, channel)
        if manque and not force:
            console.print(f"[red]{manque}[/]")
            console.print("[dim]--force publie quand même, en connaissance de la perte.[/]")
            raise typer.Exit(code=4)
        if manque:
            console.print(f"[yellow]ALERTE[/] {manque}")
        bloquants = youtube.precheck(run, channel)
        if bloquants:
            console.print("[red]precheck bloque la publication :[/] " + " · ".join(bloquants))
            raise typer.Exit(code=5)
        resultat = youtube.televerser(
            run, channel, publish_at=at or youtube.date_prevue(conn, run, channel),
            conn=conn, journal=lambda m: console.print(f"[dim]{m}[/]"), dry_run=dry_run,
        )
    except quota.QuotaDepasse as erreur:
        console.print(f"[red]QUOTA[/] {erreur}")
        raise typer.Exit(code=3) from erreur
    except youtube.ErreurPublication as erreur:
        console.print(f"[red]{erreur}[/]")
        raise typer.Exit(code=1) from erreur
    finally:
        conn.close()

    table = Table(title=f"publish — {run}", header_style="bold")
    table.add_column("Appel")
    table.add_column("État", justify="center")
    table.add_column("Détail")
    table.add_column("Unités", justify="right")
    for etape in resultat.etapes:
        couleur = "green" if etape.ok else "red"
        table.add_row(etape.nom, f"[{couleur}]{'ok' if etape.ok else 'échec'}[/]",
                      etape.message, str(etape.unites))
    console.print(table)

    if resultat.verification:
        console.print(resultat.verification)
    for alerte in resultat.avertissements:
        console.print(f"[yellow]ALERTE[/] {alerte}")
    console.print(
        f"Statut [bold]{resultat.statut}[/] · {resultat.unites} unités + 1 upload · "
        f"vidéo [bold]{resultat.url or 'non créée'}[/]"
    )
    if resultat.youtube_video_id:
        console.print("Geste manuel dans Studio : "
                      f"{youtube.LIEN_STUDIO.format(id=resultat.youtube_video_id)}")
    if resultat.verification.get("privacyStatus") not in (None, "private"):
        console.print("[red]La vidéo n'est pas privée[/] — vérifie immédiatement dans Studio.")
        raise typer.Exit(code=2)


def _release_en_attente(channel: str | None) -> None:
    """Bascule post-audit : chaque vidéo privée reçoit la date que le calendrier lui a donnée.

    Une date passée n'est **pas** rattrapée en rafale : la vidéo est listée et reste privée ;
    `factory calendar plan --replan` lui trouve un nouveau créneau.
    """
    from datetime import UTC, datetime

    from factory.core import db
    from factory.publish import calendar, quota, youtube

    cfg = config_module.charger(strict=False)
    conn = db.ouvrir()
    maintenant = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        lignes = conn.execute(
            "SELECT video_id, channel_id, youtube_video_id FROM publications "
            "WHERE status = 'published_private' AND youtube_video_id IS NOT NULL "
            + ("AND channel_id = ? " if channel else "") + "ORDER BY video_id",
            (channel,) if channel else ()).fetchall()
        faits = 0
        for l in lignes:
            chaine = cfg.channels.get(l["channel_id"])
            if chaine is None or not chaine.youtube.audit_passed:
                console.print(f"[yellow]ignorée[/] {l['video_id']} : audit_passed = false "
                              f"sur {l['channel_id']}")
                continue
            date = calendar.date_pour(conn, l["video_id"], l["channel_id"])
            if date is None or date <= maintenant:
                console.print(f"[yellow]sans date future[/] {l['video_id']} ({date or '—'}) — "
                              "`factory calendar plan --replan`, puis relancer")
                continue
            youtube.programmer(l["youtube_video_id"], channel_id=l["channel_id"], quand=date,
                               conn=conn, journal=lambda m: console.print(f"[dim]{m}[/]"))
            console.print(f"[green]programmée[/] {l['video_id']} → {date}")
            faits += 1
        console.print(f"{faits} vidéo(s) programmée(s) sur {len(lignes)} en attente")
    except quota.QuotaDepasse as erreur:
        console.print(f"[red]QUOTA[/] {erreur}")
        raise typer.Exit(code=3) from erreur
    except youtube.ErreurPublication as erreur:
        console.print(f"[red]{erreur}[/]")
        raise typer.Exit(code=1) from erreur
    finally:
        conn.close()


@publish_app.command("release")
def publish_release(
    video: str = typer.Option(None, "--video", help="Identifiant YouTube (11 caractères)."),
    at: str = typer.Option(None, "--at", help="Date ISO-8601 de programmation, UTC."),
    channel: str = typer.Option(None, "--channel", help="Chaîne, si la vidéo est inconnue."),
    annuler: bool = typer.Option(False, "--annuler",
                                 help="Retire publishAt : la vidéo redevient privée sans date."),
    en_attente: bool = typer.Option(
        False, "--en-attente",
        help="Après l'audit : programme toutes les vidéos privées à la date du calendrier."),
) -> None:
    """`videos.update` : pose (ou retire) `status.publishAt` sur une vidéo privée."""
    from factory.publish import quota, youtube

    charge_env()
    if en_attente:
        _release_en_attente(channel)
        return
    if not video:
        console.print("[red]--video ou --en-attente est requis[/]")
        raise typer.Exit(code=1)
    if not at and not annuler:
        console.print("[red]--at ou --annuler est requis[/]")
        raise typer.Exit(code=1)
    try:
        apres = youtube.programmer(video, channel_id=channel, quand=at, annuler=annuler,
                                   journal=lambda m: console.print(f"[dim]{m}[/]"))
    except quota.QuotaDepasse as erreur:
        console.print(f"[red]QUOTA[/] {erreur}")
        raise typer.Exit(code=3) from erreur
    except youtube.ErreurPublication as erreur:
        console.print(f"[red]{erreur}[/]")
        raise typer.Exit(code=1) from erreur
    console.print(apres)
    if annuler:
        console.print("[green]publishAt retiré[/] — la vidéo reste privée, sans date.")
    else:
        console.print(f"[green]Programmée[/] pour {apres.get('publishAt')}")


@publish_app.command("status")
def publish_status() -> None:
    """Quota du jour, vidéos à publier à la main, programmées, erreurs."""
    from factory.core import db
    from factory.publish import youtube

    conn = db.ouvrir()
    try:
        etat = youtube.etat_du_jour(conn)
    finally:
        conn.close()
    q = etat.quota

    table = Table(title=f"Quota du {q.day} — projet {q.gcp_project}", header_style="bold")
    table.add_column("Compartiment")
    table.add_column("Utilisé", justify="right")
    table.add_column("Plafond usine", justify="right")
    table.add_column("Dotation Google", justify="right")
    table.add_column("Reste", justify="right")
    table.add_row("uploads (videos.insert)", str(q.uploads_utilises), str(q.uploads_max),
                  "100", str(q.uploads_restants))
    table.add_row("unités (tout le reste)", str(q.unites_utilisees), str(q.unites_max),
                  "10 000", str(q.unites_restantes))
    console.print(table)
    console.print(f"{etat.publications_possibles} publication(s) complète(s) encore possible(s) "
                  f"aujourd'hui · {q.appels} appel(s), dont {q.erreurs} en erreur")

    if etat.a_publier:
        _table_manuelle(etat.a_publier)
    else:
        console.print("[dim]Aucune vidéo privée en attente de geste manuel.[/]")

    if etat.programmees:
        prog = Table(title="Programmées", header_style="bold")
        prog.add_column("video_id")
        prog.add_column("YouTube")
        prog.add_column("publishAt")
        for ligne in etat.programmees:
            prog.add_row(ligne["video_id"], ligne["youtube_video_id"] or "—",
                         ligne["publish_at"] or "—")
        console.print(prog)

    if etat.erreurs:
        err = Table(title="Échecs de publication", header_style="bold")
        err.add_column("video_id")
        err.add_column("Erreur")
        for ligne in etat.erreurs:
            err.add_row(ligne["video_id"], (ligne["last_error"] or "")[:90])
        console.print(err)

    if etat.jobs_rapports:
        console.print(f"[dim]{len(etat.jobs_rapports)} job(s) de rapports actif(s).[/]")
    else:
        console.print("[yellow]Aucun job de rapports[/] — impressions et CTR ne seront pas "
                      "collectés. `factory publish reporting-jobs --channel <id>`")


def _table_manuelle(lignes) -> None:
    """Le tableau que l'opérateur suit dans Studio, et que le digest (22.2) reprend."""
    table = Table(title="À publier à la main dans Studio (audit non obtenu)",
                  header_style="bold")
    table.add_column("Titre", max_width=40)
    table.add_column("Chaîne")
    table.add_column("Date et heure prévues")
    table.add_column("Lien Studio")
    for ligne in lignes:
        table.add_row(ligne.titre, ligne.channel_id, ligne.heure_locale, ligne.studio_url)
    console.print(table)


@publish_app.command("manual-list")
def publish_manual_list(
    json_sortie: bool = typer.Option(False, "--json", help="Sortie JSON pour le digest."),
) -> None:
    """Les vidéos privées qu'un humain doit programmer dans Studio, une par ligne."""
    import json as json_module

    from factory.core import db
    from factory.publish import youtube

    conn = db.ouvrir()
    try:
        lignes = youtube.liste_manuelle(conn)
    finally:
        conn.close()
    if json_sortie:
        console.print_json(json_module.dumps(
            [{"video_id": l.video_id, "channel_id": l.channel_id,
              "youtube_video_id": l.youtube_video_id, "titre": l.titre,
              "publish_at": l.publish_at, "heure_locale": l.heure_locale,
              "studio_url": l.studio_url} for l in lignes], ensure_ascii=False))
        return
    if not lignes:
        console.print("Aucune vidéo en attente de publication manuelle.")
        return
    _table_manuelle(lignes)
    console.print(f"{len(lignes)} vidéo(s) · environ {2 * len(lignes)} minutes dans Studio "
                  "(passage en programmé, et case « promotion payante » si la chaîne est "
                  "affiliée).")


@publish_app.command("reporting-jobs")
def publish_reporting_jobs(
    channel: str = typer.Option(None, "--channel", help="Chaîne de config/channels/."),
    toutes: bool = typer.Option(False, "--toutes",
                                help="Toutes les chaînes dont le jeton existe."),
    lister: bool = typer.Option(False, "--list", help="N'affiche que jobs.list."),
) -> None:
    """Crée (idempotent) les jobs de rapports d'une chaîne : reach, basic, trafic, démo, lieu."""
    from factory.core import db
    from factory.publish import oauth
    from factory.publish import reporting_jobs as rj

    charge_env()
    if not channel and not toutes:
        console.print("[red]--channel ou --toutes est requis[/]")
        raise typer.Exit(code=1)
    cibles = rj.chaines_authentifiees() if toutes else [channel]
    if not cibles:
        console.print("[yellow]Aucune chaîne authentifiée[/] — lance d'abord "
                      "`factory publish auth --channel <id>`.")
        raise typer.Exit(code=1)

    conn = db.ouvrir()
    code = 0
    try:
        for nom in cibles:
            console.print(f"[bold]{nom}[/]")
            try:
                if lister:
                    jobs = rj.lister(nom, conn=conn)
                    avertissements = []
                else:
                    jobs, avertissements = rj.creer(nom, conn=conn)
            except oauth.ErreurOAuth as erreur:
                console.print(f"  [red]{erreur}[/]")
                code = 1
                continue
            except Exception as erreur:  # noqa: BLE001 — une chaîne en échec n'arrête pas les autres
                console.print(f"  [red]{type(erreur).__name__}[/] {erreur}")
                code = 1
                continue
            table = Table(header_style="bold")
            table.add_column("reportTypeId")
            table.add_column("job_id")
            table.add_column("Créé le")
            table.add_column("Neuf", justify="center")
            for job in jobs:
                table.add_row(job.report_type, job.job_id, job.created_at,
                              "[green]oui[/]" if job.nouveau else "—")
            console.print(table)
            for alerte in avertissements:
                console.print(f"  [yellow]ALERTE[/] {alerte}")
            if any(j.nouveau for j in jobs):
                console.print(f"  [dim]Premier rapport attendu sous "
                              f"{rj.DELAI_PREMIER_RAPPORT_H} h ; backfill de 30 jours.[/]")
    finally:
        conn.close()
    if code:
        raise typer.Exit(code=code)


# --------------------------------------------------------------- éditorial (étape 18)


def _base_editoriale():
    from factory.core import db

    return db.ouvrir()


@watch_app.command("add")
def editorial_watch_add(
    url_ou_id: str = typer.Argument(..., help="URL /channel/UC… ou identifiant UC…"),
    niche: str = typer.Option(None, "--niche", help="Étiquette de niche."),
    lang: str = typer.Option(None, "--lang", help="Langue de la chaîne (en, fr, es, it)."),
) -> None:
    """Ajoute une chaîne à la surveillance."""
    from factory.editorial import collect as ed

    conn = _base_editoriale()
    ed.amorcer(conn)
    try:
        cid = ed.watch_add(conn, url_ou_id, niche=niche, lang=lang)
    except ValueError as exc:
        console.print(f"[red]ERREUR[/] {exc}")
        raise typer.Exit(code=2) from None
    console.print(f"[green]suivie[/] {cid}")


@watch_app.command("remove")
def editorial_watch_remove(
    url_ou_id: str = typer.Argument(..., help="URL /channel/UC… ou identifiant UC…"),
) -> None:
    """Désactive une chaîne (les données suivent la purge ordinaire)."""
    from factory.editorial import collect as ed

    conn = _base_editoriale()
    try:
        cid = ed.watch_remove(conn, url_ou_id)
    except ValueError as exc:
        console.print(f"[red]ERREUR[/] {exc}")
        raise typer.Exit(code=2) from None
    console.print(f"[yellow]désactivée[/] {cid}")


@watch_app.command("list")
def editorial_watch_list(
    toutes: bool = typer.Option(False, "--toutes", help="Inclure les chaînes désactivées."),
) -> None:
    """Liste les chaînes suivies."""
    from factory.editorial import collect as ed

    conn = _base_editoriale()
    ed.amorcer(conn)
    lignes = ed.watch_list(conn, toutes=toutes)
    table = Table(title=f"chaînes suivies ({len(lignes)})", header_style="bold")
    for col in ("Chaîne", "Niche", "Langue", "Source", "Vidéos", "Dernière collecte"):
        table.add_column(col, justify="right" if col == "Vidéos" else "left")
    for r in lignes:
        titre = r["title"] or r["channel_id"]
        if not r["active"]:
            titre = f"[dim]{titre} (inactive)[/]"
        table.add_row(
            titre, r["niche"] or "—", r["lang"] or "—", r["source"],
            str(r["videos"]), r["last_collect_date"] or "jamais",
        )
    console.print(table)


@editorial_app.command("collect")
def editorial_collect(
    force: bool = typer.Option(False, "--force", help="Recollecte les chaînes déjà faites ce jour."),
    max_units: int = typer.Option(6000, "--max-units", help="Plafond dur d'unités par compartiment."),
    install_agent: bool = typer.Option(
        False, "--install-agent", help="Écrit et charge la tâche launchd, puis sort."
    ),
) -> None:
    """Collecte les instantanés du jour pour chaque chaîne active."""
    from factory.editorial import collect as ed

    if install_agent:
        chemin, heure, minute = ed.ecrire_plist()
        ok, message = ed.charger_agent()
        console.print(f"plist écrit : {chemin}")
        console.print(f"passage quotidien à [bold]{heure:02d}:{minute:02d}[/] (heure locale)")
        console.print(f"[{'green' if ok else 'red'}]{message}[/]")
        if not ok:
            raise typer.Exit(code=1)

        # Charger la tâche ne prouve pas qu'elle pourra tourner : macOS protège
        # ~/Documents par TCC et une tâche launchd n'y a aucun droit par défaut.
        console.print("vérification de l'accès disque de la tâche…")
        acces, detail = ed.verifier_acces_launchd()
        if acces is True:
            console.print(f"[green]accès disque[/] — {detail}")
            raise typer.Exit(code=0)
        if acces is None:
            console.print(f"[yellow]accès disque non vérifié[/] — {detail}")
            raise typer.Exit(code=0)
        console.print(f"[red]ACCÈS DISQUE REFUSÉ[/] — {detail}")
        console.print(
            "\nLa tâche est chargée mais ne pourra pas lire le projet : il est sous "
            "[bold]~/Documents[/], protégé par macOS.\n"
            "Action manuelle de Thomas, une fois :\n"
            "  Réglages Système → Confidentialité et sécurité → [bold]Accès complet au disque[/]\n"
            f"  ajouter [bold]{ed.binaire_python()}[/]\n"
            "puis relancer `factory editorial collect --install-agent` pour revérifier.\n"
            "Sans cela, la collecte nocturne ne démarre pas (le processus reste suspendu)."
        )
        raise typer.Exit(code=2)

    conn = _base_editoriale()
    rapport = ed.collecter(conn, force=force, max_units=max_units, echo=console.print)

    table = Table(title=f"collecte {rapport.date} ({rapport.mode})", header_style="bold")
    table.add_column("Mesure")
    table.add_column("Valeur", justify="right")
    table.add_row("chaînes collectées", f"{rapport.chaines_faites}/{rapport.chaines_total}")
    table.add_row("chaînes sautées", str(rapport.chaines_sautees))
    table.add_row("vidéos nouvelles", str(rapport.videos_nouvelles))
    table.add_row("instantanés", str(rapport.instantanes))
    table.add_row("unités — principal", str(rapport.unites))
    table.add_row("unités — batchGetStats", str(rapport.unites_batch))
    table.add_row("erreurs", str(len(rapport.erreurs)))
    console.print(table)
    console.print(f"rapport → reports/collect_{rapport.date}.md")
    if rapport.arret_quota:
        console.print("[yellow]ARRÊT AU PLAFOND[/] — relancer demain ou relever --max-units.")
        raise typer.Exit(code=1)
    if rapport.erreurs:
        raise typer.Exit(code=1)


@editorial_app.command("top")
def editorial_top(
    niche: str = typer.Option(None, "--niche", help="Filtre de niche."),
    window: str = typer.Option("30d", "--window", help="Âge maximum des vidéos, par exemple 30d."),
    lang: str = typer.Option(None, "--lang", help="Filtre de langue."),
    limite: int = typer.Option(20, "--limit", help="Nombre de lignes."),
) -> None:
    """Les vidéos les plus rapides de la fenêtre, par vélocité."""
    from factory.editorial import collect as ed

    conn = _base_editoriale()
    try:
        lignes = ed.top(conn, niche=niche, fenetre=window, lang=lang, limite=limite)
    except ValueError as exc:
        console.print(f"[red]ERREUR[/] {exc}")
        raise typer.Exit(code=2) from None

    portee = " · ".join(
        filter(None, [f"niche {niche}" if niche else None, f"langue {lang}" if lang else None,
                      f"fenêtre {window}"])
    )
    table = Table(title=f"top vélocité — {portee}", header_style="bold", expand=True)
    # Une ligne par vidéo : les titres sont coupés, jamais repliés, sinon 20 lignes
    # deviennent 80 et le tableau n'est plus lisible dans un terminal.
    table.add_column("Chaîne", max_width=20, no_wrap=True, overflow="ellipsis")
    # Seul le titre cède quand le terminal est étroit ; les chiffres, jamais.
    table.add_column("Titre", ratio=1, min_width=16, no_wrap=True, overflow="ellipsis")
    table.add_column("Âge (j)", justify="right", min_width=7, no_wrap=True)
    table.add_column("Vues", justify="right", min_width=9, no_wrap=True)
    table.add_column("Vél. (vues/j)", justify="right", min_width=13, no_wrap=True)
    table.add_column("Ratio", justify="right", min_width=5, no_wrap=True)
    table.add_column("Base", min_width=4, no_wrap=True)
    for r in lignes:
        titre = r["title"] or "—"
        table.add_row(
            r["channel_title"] or r["channel_id"],
            titre,
            f"{r['age_days']:.1f}",
            f"{r['views']:,}".replace(",", " ") if r["views"] is not None else "—",
            f"{r['velocity']:,.0f}".replace(",", " ") if r["velocity"] is not None else "—",
            f"{r['ratio']:.2f}" if r["ratio"] is not None else "—",
            "7 j" if r["velocity_source"] == "7d" else "moy.",
        )
    console.print(table)
    if not lignes:
        console.print("[yellow]aucune ligne[/] — la fenêtre est peut-être vide, ou la collecte n'a pas tourné.")
    elif all(r["velocity_source"] == "life" for r in lignes):
        console.print(
            "[yellow]vélocité moyenne depuis publication[/] : il faut deux jours de collecte "
            "distincts pour que la vélocité à 7 jours existe."
        )


@editorial_app.command("purge")
def editorial_purge(
    jours: int = typer.Option(30, "--jours", help="Durée de conservation des données API."),
    strict: bool = typer.Option(
        False, "--strict", help="Supprime aussi les mesures dérivées (lecture stricte de III.E.4.h)."
    ),
    simulation: bool = typer.Option(False, "--simulation", help="Compte sans supprimer."),
) -> None:
    """Applique la conservation de docs/CONFORMITE.md § 9."""
    from factory.editorial import collect as ed

    conn = _base_editoriale()
    p = ed.purger(conn, jours=jours, strict=strict, simulation=simulation)
    table = Table(
        title=f"purge {'(simulation) ' if simulation else ''}— antérieur à {p.limite}",
        header_style="bold",
    )
    table.add_column("Catégorie")
    table.add_column("Lignes", justify="right")
    table.add_row("instantanés vidéo", str(p.instantanes_video))
    table.add_row("instantanés chaîne", str(p.instantanes_chaine))
    table.add_row("vidéos non rafraîchies", str(p.videos))
    table.add_row("mesures consolidées", str(p.metriques_consolidees))
    table.add_row("mesures supprimées", str(p.metriques_supprimees))
    console.print(table)


@editorial_app.command("niches")
def editorial_niches(
    lang: str = typer.Option("en", "--lang", help="Langue notée (production : en)."),
) -> None:
    """Note les niches : demande, concurrence, monétisation, faisabilité."""
    from factory.editorial import niches as nz

    from factory.editorial import demand as dmd

    conn = _base_editoriale()
    console.print(f"notation des niches — langue [bold]{lang}[/]")
    if not dmd.contact_renseigne():
        console.print(
            "[yellow]FACTORY_CONTACT vide[/] — la politique Wikimedia exige un contact "
            "dans le User-Agent. Sans lui, la limite tombe de 200 à 10 req/min et les "
            "appels partent en 429 (mesuré le 20/09/2026 : 256 s au lieu de quelques "
            "secondes). Renseigner `FACTORY_CONTACT` dans `.env` — action de Thomas."
        )
    try:
        notes, chemin, duree = nz.executer(conn, lang=lang, echo=console.print)
    except (KeyError, FileNotFoundError) as exc:
        console.print(f"[red]ERREUR[/] configuration incomplète : {exc}")
        raise typer.Exit(code=2) from None

    table = Table(title=f"niches — {lang} ({len(notes)})", header_style="bold")
    table.add_column("#", justify="right")
    table.add_column("Niche", max_width=34, no_wrap=True, overflow="ellipsis")
    table.add_column("Orig.", max_width=9)
    for col in ("Score", "Dem.", "Conc.", "Mon.", "Fais."):
        table.add_column(col, justify="right")
    table.add_column("Meilleurs mois")
    for i, n in enumerate(notes, 1):
        table.add_row(
            str(i), n.niche, n.origine, f"[bold]{n.score:.1f}[/]", f"{n.demande:.1f}",
            f"{n.concurrence:.1f}", f"{n.monetisation:.1f}", f"{n.faisabilite:.1f}",
            ", ".join(nz.MOIS_FR[m] for m in n.top_mois) or "—",
        )
    console.print(table)
    console.print(f"rapport → {chemin.relative_to(chemin.parents[1])} · {duree:.1f} s")
    budgets = notes[0].evidence["budgets"] if notes else {}
    console.print(
        f"appels : Wikimedia {budgets.get('wikimedia_appels', 0)} · "
        f"autocomplete {budgets.get('autocomplete_appels', 0)} "
        f"(non documenté, plafond par exécution)"
    )


# ------------------------------------------------------- sujets et trous (étape 20)


@editorial_app.command("topics")
def editorial_topics(
    action: str = typer.Argument(
        "run", help="run (défaut) | approve <id> | ban <id>", show_default=False
    ),
    topic_id: int | None = typer.Argument(None, help="Identifiant de file pour approve/ban."),
    channel: str = typer.Option(None, "--channel", "-c", help="Chaîne BMS notée."),
    n: int = typer.Option(30, "--n", help="Sujets retenus dans la file."),
) -> None:
    """Percées, regroupement, trous et file de sujets notée pour une chaîne."""
    from factory.editorial import topics as tp

    conn = _base_editoriale()
    if action in ("approve", "ban"):
        if topic_id is None:
            console.print(f"[red]ERREUR[/] `{action}` attend un identifiant de file.")
            raise typer.Exit(code=2)
        statut = "approved" if action == "approve" else "banned"
        try:
            ligne = tp.changer_statut(conn, topic_id, statut)
        except KeyError as exc:
            console.print(f"[red]ERREUR[/] {exc}")
            raise typer.Exit(code=2) from None
        console.print(
            f"sujet [bold]{ligne['id']}[/] ({ligne['channel_id']}) : "
            f"{ligne['avant']} → [bold]{ligne['apres']}[/] — {ligne['topic']}"
        )
        return

    if action != "run":
        console.print(f"[red]ERREUR[/] action inconnue : {action} (run | approve | ban)")
        raise typer.Exit(code=2)
    if not channel:
        console.print("[red]ERREUR[/] `--channel` est obligatoire : un sujet est noté "
                      "pour une chaîne, pas pour une langue.")
        raise typer.Exit(code=2)

    console.print(f"sujets — chaîne [bold]{channel}[/], file de {n}")
    try:
        sujets, clusters, chemin, mesures = tp.executer(
            conn, channel, n=n, echo=console.print
        )
    except (KeyError, ValueError, FileNotFoundError) as exc:
        console.print(f"[red]ERREUR[/] {exc}")
        raise typer.Exit(code=2) from None

    table = Table(title=f"file — {channel} ({len(sujets)})", header_style="bold")
    table.add_column("#", justify="right")
    table.add_column("Score", justify="right")
    table.add_column("Sujet", max_width=52, overflow="ellipsis")
    table.add_column("Lacune", max_width=12)
    table.add_column("Preuve", max_width=30, overflow="ellipsis")
    for i, s in enumerate(sujets[:15], 1):
        e = s.evidence
        table.add_row(
            str(i), f"[bold]{s.score:.3f}[/]", s.topic, e.get("gap_type") or "—",
            f"{e['n_videos']} vid · {e['n_chaines']} ch · {e['n_percees']} percées",
        )
    console.print(table)
    console.print(
        f"clusters {mesures['n_clusters']} · percées {mesures['percees']['n_percees']} · "
        f"trous ml {mesures['trous']['multilingue']} / demande "
        f"{mesures['trous']['demande']} / résurgence {mesures['trous']['resurgence']}"
    )
    console.print(
        f"embeddings : {mesures['embeddings']['calcules']} calculés, "
        f"{mesures['embeddings']['depuis_cache']} en cache "
        f"({mesures['embeddings']['secondes']:.0f} s) · LLM {mesures['llm']['appels']} appels "
        f"dont {mesures['llm']['caches']} en cache, "
        f"{mesures['llm']['secondes_calculees']:.0f} s calculées"
    )
    for avertissement in mesures.get("avertissements", []):
        console.print(f"[yellow]⚠[/] {avertissement}")
    console.print(f"rapport → {chemin.relative_to(chemin.parents[1])} · "
                  f"{mesures['secondes']:.0f} s")


# --------------------------------------------------------------------------------------
# File de production (étape 22.1)
# --------------------------------------------------------------------------------------


def _base_file():
    """Ouvre `workspace/factory.db` avec ses migrations. Une seule porte d'entrée."""
    from factory.core import db

    return db.ouvrir()


@queue_app.command("add")
def queue_add(
    channel: str = typer.Option(..., "--channel", help="Chaîne de config/channels/."),
    n: int = typer.Option(1, "--n", help="Nombre de vidéos à enfiler."),
    topic: str | None = typer.Option(None, "--topic", help="Sujet imposé au premier job."),
    priority: int = typer.Option(0, "--priority", "-p", help="Plus grand passe d'abord."),
) -> None:
    """Crée `n` plans via `topics_queue` et les enfile."""
    from factory.orchestrator import queue as file_module

    charge_env()
    conn = _base_file()
    try:
        jobs = file_module.ajouter(conn, channel, n=n, topic=topic, priority=priority,
                                   echo=console.print)
    except file_module.ErreurFile as erreur:
        console.print(f"[red]ERREUR[/] {erreur}")
        raise typer.Exit(code=2) from None
    finally:
        conn.close()
    console.print(f"[green]{len(jobs)} job(s) enfilé(s)[/] — "
                  f"`factory daemon run-once` ou le daemon les prendra")


@queue_app.command("status")
def queue_status(
    tout: bool = typer.Option(False, "--all", help="Montre aussi les jobs terminés."),
) -> None:
    """Tableau de la file par statut, et temps moyen par étape sur les 10 derniers runs."""
    from factory.orchestrator import queue as file_module
    from factory.orchestrator import runner as runner_module

    conn = _base_file()
    compte = file_module.compter(conn)
    statuts = None if tout else [s for s in file_module.STATUTS
                                 if s not in ("exported", "published")]
    jobs = file_module.lister(conn, statuts)
    etats = file_module.etat_runs(conn, [j.video_id for j in jobs])

    resume = Table(title="file — jobs par statut", header_style="bold")
    for statut in file_module.STATUTS:
        resume.add_column(statut, justify="right")
    couleurs = {"exported": "green", "failed": "red", "blocked": "red",
                "awaiting_review": "yellow", "running": "cyan"}
    resume.add_row(*[f"[{couleurs.get(s, 'white')}]{compte[s]}[/]" if compte[s]
                     else "[dim]0[/]" for s in file_module.STATUTS])
    console.print(resume)

    if jobs:
        table = Table(title=f"jobs ({len(jobs)})", header_style="bold")
        for colonne in ("#", "Run", "Chaîne", "Étape", "Statut", "Essais", "Pri.",
                        "Prochaine", "Publication (UTC)", "Dernière erreur"):
            table.add_column(colonne, overflow="ellipsis")
        for job in jobs:
            table.add_row(
                str(job.id), job.video_id, job.channel_id, job.stage,
                f"[{couleurs.get(job.status, 'white')}]{job.status}[/]",
                str(job.attempts), str(job.priority), job.next_run_at or "—",
                job.publish_at or "—", (job.last_error or "—")[:60],
            )
        console.print(table)
    else:
        console.print("[dim]aucun job en cours[/]")

    temps = file_module.temps_par_etape(conn, derniers=10)
    if temps:
        table = Table(title="temps moyen par étape — 10 derniers runs", header_style="bold")
        for colonne in ("Étape", "Moyenne", "Min", "Max", "n"):
            table.add_column(colonne, justify="right")
        total = 0.0
        for etape in file_module.ETAPES:
            mesure = temps.get(etape)
            if mesure is None:
                continue
            total += mesure["moyenne_s"]
            table.add_row(etape, f"{mesure['moyenne_s'] / 60:.1f} min",
                          f"{mesure['min_s'] / 60:.1f}", f"{mesure['max_s'] / 60:.1f}",
                          str(mesure["n"]))
        table.add_row("[bold]total[/]", f"[bold]{total / 60:.1f} min[/]", "", "", "")
        console.print(table)
    console.print(
        f"disque {runner_module.disque_libre_go():.1f} Go libres · "
        f"mémoire {runner_module.memoire_libre_go() or float('nan'):.1f} Go disponibles"
    )
    conn.close()


@queue_app.command("retry")
def queue_retry(job: int = typer.Argument(..., help="Identifiant du job.")) -> None:
    """Remet un job en file, à l'étape où il s'est arrêté, compteur à zéro."""
    _action_file("retry", job)


@queue_app.command("block")
def queue_block(
    job: int = typer.Argument(..., help="Identifiant du job."),
    reason: str = typer.Option(..., "--reason", help="Raison lisible, obligatoire."),
) -> None:
    """Sort un job de la file avec une raison lisible."""
    _action_file("block", job, reason=reason)


@queue_app.command("prioritize")
def queue_prioritize(
    job: int = typer.Argument(..., help="Identifiant du job."),
    priority: int = typer.Argument(..., help="Nouvelle priorité ; plus grand passe d'abord."),
) -> None:
    """Change la priorité d'un job."""
    _action_file("prioritize", job, priority=priority)


@queue_app.command("approve")
def queue_approve(
    job: int = typer.Argument(..., help="Identifiant du job."),
    reviewer: str = typer.Option("", "--reviewer", help="Identifiant de config/team.yaml."),
    sans_relecture: bool = typer.Option(
        False, "--sans-relecture",
        help="Lève la barrière SANS lecture humaine : relecteur « auto-approve », "
             "décision « auto_approved ». Exige --motif.",
    ),
    motif: str = typer.Option("", "--motif",
                              help="Pourquoi la barrière est levée sans lecture."),
) -> None:
    """Lève la barrière de relecture d'un job, avec trace (relecteur, date, empreinte).

    Minimale : l'étape 22.2 livre la relecture par lots avec le script sous les yeux.
    """
    if sans_relecture:
        console.print("[red]AVERTISSEMENT[/] levée SANS lecture humaine : l'exception "
                      "éditoriale du RIA art. 50 §4 tombe pour cette vidéo "
                      "(CONFORMITE § 4). Elle ne doit pas être publiée en l'état.")
    elif not reviewer:
        console.print("[red]ERREUR[/] `--reviewer` est obligatoire, ou "
                      "`--sans-relecture --motif \"…\"` pour une levée assumée sans lecture.")
        raise typer.Exit(code=2)
    _action_file("approve", job, reviewer=reviewer, sans_relecture=sans_relecture,
                 motif=motif)


@queue_app.command("reindex")
def queue_reindex() -> None:
    """Reconstruit l'index des runs en relisant les `manifest.json` (ARCHITECTURE § 1.8)."""
    from factory.orchestrator import queue as file_module

    conn = _base_file()
    n = file_module.reindexer(conn)
    conn.close()
    console.print(f"[green]{n} run(s) réindexé(s)[/] depuis workspace/runs/*/manifest.json")


def _action_file(action: str, job_id: int, **options) -> None:
    """Retry / block / prioritize / approve — même sortie, même traitement d'erreur."""
    from factory.orchestrator import queue as file_module

    conn = _base_file()
    try:
        if action == "retry":
            job = file_module.relancer(conn, job_id)
        elif action == "block":
            job = file_module.bloquer(conn, job_id, options["reason"])
        elif action == "prioritize":
            job = file_module.prioriser(conn, job_id, options["priority"])
        else:
            job = file_module.approuver(
                conn, job_id, options["reviewer"],
                sans_relecture=options.get("sans_relecture", False),
                motif=options.get("motif") or None,
            )
    except file_module.ErreurFile as erreur:
        console.print(f"[red]ERREUR[/] {erreur}")
        raise typer.Exit(code=2) from None
    finally:
        conn.close()
    console.print(f"job [bold]{job.id}[/] ({job.video_id}) → [bold]{job.status}[/] "
                  f"à l'étape {job.stage}, priorité {job.priority}, "
                  f"{job.attempts} tentative(s)")


# --------------------------------------------------------------------------------------
# Daemon (étape 22.1)
# --------------------------------------------------------------------------------------


def _resume_tours(tours) -> None:
    """Tableau des jobs traités par un tour du runner."""
    if not tours:
        console.print("[dim]aucun job éligible[/]")
        return
    table = Table(title=f"tour du runner — {len(tours)} job(s)", header_style="bold")
    for colonne in ("Job", "Run", "Statut", "Étapes", "Temps"):
        table.add_column(colonne, overflow="ellipsis")
    couleurs = {"exported": "green", "failed": "red", "blocked": "red",
                "awaiting_review": "yellow", "queued": "cyan"}
    for tour in tours:
        etapes = " ".join(f"{nom}:{code}" for nom, code, _ in tour.etapes) or "—"
        table.add_row(str(tour.job_id), tour.video_id,
                      f"[{couleurs.get(tour.statut, 'white')}]{tour.statut}[/]",
                      etapes, f"{tour.secondes / 60:.1f} min")
    console.print(table)
    for tour in tours:
        for alerte in tour.alertes:
            console.print(f"[yellow]ALERTE[/] job {tour.job_id} — {alerte}")
        if tour.raison:
            console.print(f"[dim]job {tour.job_id} :[/] {tour.raison}")


@daemon_app.command("run-once")
def daemon_run_once(
    max_jobs: int | None = typer.Option(None, "--max-jobs", help="Plafond de jobs."),
    fenetre: bool = typer.Option(
        False, "--fenetre/--sans-fenetre",
        help="Applique la fenêtre horaire. Par défaut non : run-once est une commande "
             "manuelle, l'humain est devant le terminal.",
    ),
) -> None:
    """Vide la file une fois, puis rend la main. C'est ce que fait un tour du daemon."""
    from factory.orchestrator import daemon as daemon_module

    charge_env()
    tours = daemon_module.tourner(une_fois=True, max_jobs=max_jobs,
                                 respecter_fenetre=fenetre, echo=console.print)
    _resume_tours(tours)


@daemon_app.command("start")
def daemon_start(
    foreground: bool = typer.Option(
        False, "--foreground", help="Reste au premier plan (c'est ce que fait launchd)."
    ),
    fenetre: bool = typer.Option(True, "--fenetre/--sans-fenetre",
                                help="Applique la fenêtre horaire de config/orchestrator.yaml."),
) -> None:
    """Démarre la boucle. Sans `--foreground`, charge l'agent launchd et rend la main."""
    from factory.orchestrator import daemon as daemon_module

    charge_env()
    if foreground:
        tours = daemon_module.tourner(une_fois=False, respecter_fenetre=fenetre,
                                      echo=console.print)
        _resume_tours(tours)
        return
    chemins = daemon_module.ecrire_plists()
    code, sortie = daemon_module.charger_agent(daemon_module.LABEL_DAEMON)
    for chemin in chemins:
        console.print(f"plist → {chemin}")
    if code != 0:
        console.print(f"[red]launchctl bootstrap : code {code}[/] {sortie}")
        raise typer.Exit(code=3)
    console.print("[green]agent chargé[/] — `factory daemon status` pour le voir tourner")


@daemon_app.command("stop")
def daemon_stop(
    attendre: int = typer.Option(0, "--wait", help="Secondes d'attente de la sortie."),
    decharger: bool = typer.Option(False, "--unload", help="Décharge aussi l'agent launchd."),
) -> None:
    """Arrêt propre : l'étape en cours va jusqu'au bout, puis le processus sort."""
    from factory.orchestrator import daemon as daemon_module

    if decharger:
        code, sortie = daemon_module.decharger_agent(daemon_module.LABEL_DAEMON)
        console.print(f"agent déchargé et désactivé durablement : code {code} {sortie}".rstrip())
        console.print("[dim]`factory daemon install` le relève et le recharge[/]")
    if daemon_module.arreter(attendre_s=attendre):
        console.print("[green]SIGTERM envoyé[/] — l'étape en cours finit avant la sortie")
    else:
        console.print("[dim]aucun daemon en cours[/]")


@daemon_app.command("status")
def daemon_status() -> None:
    """Qui tourne, dans quelle fenêtre, avec quelle file."""
    from factory.orchestrator import daemon as daemon_module

    etat = daemon_module.etat()
    console.print(
        f"daemon : " + (f"[green]en cours[/] pid {etat.pid} depuis {etat.depuis}"
                        if etat.vivant else "[dim]arrêté[/]")
    )
    console.print(f"agent launchd {daemon_module.LABEL_DAEMON} : "
                  + ("[green]chargé[/]" if etat.charge_launchd else "[dim]non chargé[/]"))
    console.print("fenêtre des étapes lourdes : "
                  + ("[green]ouverte[/]" if etat.fenetre_lourdes_ouverte
                     else "[yellow]fermée[/]"))
    console.print(f"verrou run.lock : {etat.verrou or '[dim]libre[/]'}")
    occupes = " · ".join(f"{k} {v}" for k, v in etat.jobs.items() if v)
    console.print(f"file : {occupes}" if occupes else "file : [dim]vide[/]")
    console.print(daemon_module.liste_agents())


@daemon_app.command("install")
def daemon_install(
    decharger: bool = typer.Option(False, "--uninstall", help="Décharge les trois agents."),
) -> None:
    """Écrit et charge les trois agents launchd (daemon, sauvegarde, digest)."""
    from factory.orchestrator import daemon as daemon_module

    if decharger:
        for label in (daemon_module.LABEL_DAEMON, daemon_module.LABEL_BACKUP,
                      daemon_module.LABEL_DIGEST):
            code, sortie = daemon_module.decharger_agent(label)
            console.print(f"bootout {label} : code {code} {sortie}".rstrip())
        return
    for chemin in daemon_module.ecrire_plists():
        console.print(f"plist → {chemin}")
    for label in (daemon_module.LABEL_DAEMON, daemon_module.LABEL_BACKUP,
                  daemon_module.LABEL_DIGEST):
        code, sortie = daemon_module.charger_agent(label)
        couleur = "green" if code == 0 else "red"
        console.print(f"[{couleur}]bootstrap {label} : code {code}[/] {sortie}".rstrip())
    console.print(daemon_module.liste_agents())


# --------------------------------------------------------------------------------------
# Sauvegardes (étape 22.1)
# --------------------------------------------------------------------------------------


@backup_app.command("run")
def backup_run(
    attendre: int = typer.Option(
        3600, "--wait",
        help="Secondes d'attente de run.lock. Au-delà, la sauvegarde passe outre.",
    ),
) -> None:
    """Archive la base, les JSON des runs, la configuration, l'appris et les docs."""
    from factory.orchestrator import backup as backup_module
    from factory.orchestrator import journal as journal_module

    tenu = journal_module.detenteur()
    if tenu is not None and tenu.vivant:
        console.print(f"[yellow]run.lock tenu[/] par le pid {tenu.pid} ({tenu.quoi}) — "
                      f"attente d'au plus {attendre} s, puis sauvegarde quand même")
    resultat = backup_module.executer(echo=console.print, attendre_verrou_s=attendre)
    console.print(
        f"[green]{resultat.archive}[/]\n"
        f"{resultat.mo} Mo · {resultat.fichiers} fichiers · {resultat.runs} runs · "
        f"{resultat.secondes:.1f} s · compression {resultat.compression}"
    )
    if resultat.supprimees:
        console.print(f"[dim]rétention : {len(resultat.supprimees)} archive(s) supprimée(s) "
                      f"— {', '.join(resultat.supprimees[:5])}[/]")
    console.print("[yellow]RAPPEL[/] cette archive est sur le même disque que l'original : "
                  "copie ~/BMS-backups sur un support externe ou un cloud "
                  "(docs/EXPLOITATION.md § 4).")


@backup_app.command("restore-test")
def backup_restore_test(
    archive: Path | None = typer.Option(None, "--archive", help="Archive à tester."),
) -> None:
    """Extrait à blanc, ouvre la base, compte les runs et compare avec l'original."""
    from factory.orchestrator import backup as backup_module

    try:
        resultat = backup_module.tester_restauration(archive, echo=console.print)
    except (FileNotFoundError, OSError) as erreur:
        console.print(f"[red]ERREUR[/] {erreur}")
        raise typer.Exit(code=2) from None

    table = Table(title=f"restore-test — {resultat.archive.name}", header_style="bold")
    for colonne in ("Mesure", "Archive", "Original", "Verdict"):
        table.add_column(colonne, justify="right")
    for nom, a, o in (("runs en base", resultat.runs_archive, resultat.runs_original),
                      ("jobs en base", resultat.jobs_archive, resultat.jobs_original)):
        egal = a == o
        table.add_row(nom, str(a), str(o),
                      "[green]=[/]" if egal else "[red]écart[/]")
    table.add_row("tables", str(resultat.tables_archive), "—",
                  "[green]base lisible[/]" if resultat.tables_archive else "[red]vide[/]")
    table.add_row("manifest.json", str(resultat.manifestes), "—", "")
    table.add_row("secrets trouvés", str(len(resultat.secrets_trouves)), "0",
                  "[green]aucun[/]" if not resultat.secrets_trouves else "[red]FUITE[/]")
    console.print(table)
    for fuite in resultat.secrets_trouves[:10]:
        console.print(f"[red]SECRET DANS L'ARCHIVE[/] {fuite}")
    couleur = "green" if resultat.ok else "red"
    console.print(f"[{couleur}]{'RESTAURABLE' if resultat.ok else 'ÉCHEC'}[/] · "
                  f"{resultat.secondes:.1f} s")
    if not resultat.ok:
        raise typer.Exit(code=4)


@backup_app.command("list")
def backup_list() -> None:
    """Les archives présentes, de la plus ancienne à la plus récente."""
    from factory.orchestrator import backup as backup_module

    dossier = backup_module.destination()
    archives = sorted(dossier.glob("factory-*.tar.*"))
    if not archives:
        console.print(f"[dim]aucune archive dans {dossier}[/]")
        return
    table = Table(title=str(dossier), header_style="bold")
    for colonne in ("Archive", "Mo", "Date"):
        table.add_column(colonne, justify="right")
    from datetime import datetime as _dt

    for chemin in archives:
        stat = chemin.stat()
        table.add_row(chemin.name, f"{stat.st_size / 1e6:.2f}",
                      _dt.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"))
    console.print(table)



# --------------------------------------------------------------------------------------
# Relecture, digest et alertes (étape 22.2)
# --------------------------------------------------------------------------------------


def _fiche_rich(fiche, rang: int, total: int) -> None:
    """Affiche une fiche de relecture : ce qui se juge en trente secondes."""
    densite = "—" if fiche.densite is None else f"{fiche.densite:.2f}"
    couleur_duree = "green" if abs(fiche.duree_estimee_s - fiche.duree_cible_s) \
        <= 0.15 * fiche.duree_cible_s else "yellow"
    console.rule(f"[bold]{rang}/{total}[/] {fiche.titre}")
    console.print(f"[dim]chaîne[/] {fiche.channel_id}   "
                  f"[dim]sujet[/] {fiche.sujet}   [dim]angle[/] [bold]{fiche.angle}[/]")
    console.print(f"[dim]hook[/] ([bold]{fiche.hook_type}[/]) « {fiche.hook} »")
    console.print(
        f"[dim]durée[/] [{couleur_duree}]{fiche.duree_estimee_s:.0f} s[/] pour "
        f"{fiche.duree_cible_s} s ({fiche.ecart_duree})   [dim]densité[/] {densite} faits/min"
        f"   [dim]{fiche.n_segments} segments, {fiche.mots} mots[/]"
    )
    for ligne in fiche.premieres_lignes:
        console.print(f"  [dim]│[/] {ligne}")
    if fiche.rejets:
        console.print(f"  [yellow]déjà rejeté {fiche.rejets} fois[/]")
    for alerte in fiche.alertes:
        console.print(f"  [yellow]⚠[/] {alerte}")


@app.command("review")
def commande_review(
    channel: str | None = typer.Option(None, "--channel", help="Ne relire qu'une chaîne."),
    reviewer: str = typer.Option("", "--reviewer",
                                 help="Identifiant de config/team.yaml : alek, sofiane, thomas."),
    auto: bool = typer.Option(False, "--auto",
                              help="Lève sans lecture. Exige channel.auto_approve = true."),
    lister_seulement: bool = typer.Option(False, "--list",
                                          help="Affiche la file de relecture sans rien décider."),
) -> None:
    """Relit par lots les scripts en attente : approuver, rejeter, éditer, passer.

    C'est la seule intervention éditoriale humaine du système, et la pièce qui fait tomber
    l'obligation de divulgation du RIA art. 50 §4 (`docs/CONFORMITE.md` § 4).
    """
    from factory.orchestrator import review as review_module

    conn = _base_file()
    try:
        if auto:
            if not channel:
                console.print("[red]ERREUR[/] `--auto` exige `--channel`.")
                raise typer.Exit(code=2)
            console.print(
                "[bold red]AVERTISSEMENT — LEVÉE SANS LECTURE HUMAINE.[/] "
                f"Les scripts de [bold]{channel}[/] vont être approuvés par la machine. "
                "L'exception éditoriale du RIA art. 50 §4 [bold]tombe[/] pour ces vidéos "
                "(CONFORMITE § 4) : `reviewer = auto`, `ria_exception_claimed = false`, "
                "et la divulgation « contenu synthétique » redevient obligatoire."
            )
            liberes = review_module.auto_approuver(conn, channel, echo=console.print)
            console.print(f"[yellow]{len(liberes)} script(s) levé(s) sans lecture.[/]")
            return
        if not reviewer and not lister_seulement:
            console.print("[red]ERREUR[/] `--reviewer` est obligatoire. « L'équipe » n'est "
                          "pas un relecteur (CONFORMITE § 4) : le champ porte une identité.")
            raise typer.Exit(code=2)
        if reviewer:
            nom = review_module.verifier_relecteur(reviewer)
            console.print(f"relecteur : [bold]{nom}[/] ({reviewer.lower()})")

        fiches = review_module.en_attente(conn, channel)
        if not fiches:
            console.print("[green]aucun script en attente de relecture[/]")
            return
        if lister_seulement:
            for rang, fiche in enumerate(fiches, start=1):
                _fiche_rich(fiche, rang, len(fiches))
            console.print(f"\n[dim]{len(fiches)} script(s). "
                          f"`factory review --reviewer <id>` pour décider.[/]")
            return

        def _demander(fiche) -> tuple[str, str]:
            touche = typer.prompt(
                "  [a]pprouver  [r]ejeter  [e]diter  [s]auter  [q]uitter", default="s",
            ).strip().lower()[:1]
            if touche == "r":
                return "r", typer.prompt("  motif du rejet (il part dans le prompt du modèle)")
            return touche, ""

        bilan = review_module.relire(
            conn, reviewer, channel=channel, demander=_demander, afficher=_fiche_rich,
            echo=console.print, rejets_max=_orchestrateur().rejets_max,
        )
    except Exception as erreur:  # noqa: BLE001 — message lisible, pas de trace
        if isinstance(erreur, typer.Exit):
            raise
        console.print(f"[red]ERREUR[/] {erreur}")
        raise typer.Exit(code=2) from None
    finally:
        conn.close()
    console.print(
        f"\n[bold]lot {bilan.batch_id}[/] — "
        f"[green]{len(bilan.approuves)} approuvé(s)[/], "
        f"[yellow]{len(bilan.rejetes)} rejeté(s)[/], "
        f"{len(bilan.edites)} édité(s), {len(bilan.passes)} passé(s)"
    )
    for erreur in bilan.erreurs:
        console.print(f"[red]{erreur}[/]")


def _orchestrateur():
    """`config/orchestrator.yaml`, ou les valeurs par défaut du modèle."""
    from factory.core.models import OrchestratorConfig

    return config_module.charger(strict=False).orchestrator or OrchestratorConfig()


@app.command("digest")
def commande_digest(
    date: str | None = typer.Option(None, "--date", help="AAAA-MM-JJ ; aujourd'hui par défaut."),
    envoyer: bool = typer.Option(False, "--envoyer",
                                 help="Envoie aussi le résumé par le canal d'alerte."),
    afficher: bool = typer.Option(False, "--afficher", help="Écrit le digest sur la sortie."),
) -> None:
    """Écrit `reports/digest_<date>.md` — la lecture quotidienne d'Alek et de Sofiane."""
    from factory.orchestrator import notify as notify_module

    conn = _base_file()
    try:
        if envoyer:
            chemin, envoi = notify_module.envoyer_digest(conn, date)
            console.print(f"[green]{chemin}[/] — alerte {envoi.canal} : "
                          f"{'envoyée' if envoi.ok else 'NON envoyée'} ({envoi.reponse})")
        else:
            chemin = notify_module.ecrire_digest(conn, date)
            console.print(f"[green]{chemin}[/]")
        if afficher:
            console.print(chemin.read_text(encoding="utf-8"))
    finally:
        conn.close()


notify_app = typer.Typer(
    add_completion=False, help="Alertes : canal, test, revue des motifs."
)
app.add_typer(notify_app, name="notify")


@notify_app.command("canal")
def notify_canal() -> None:
    """Dit par quel canal partiraient les alertes, et pourquoi."""
    from factory.orchestrator import notify as notify_module

    voie = notify_module.canal()
    couleur = {"telegram": "green", "macos": "yellow", "aucun": "red"}[voie.nom]
    console.print(f"canal : [{couleur}]{voie.nom}[/] — {voie.pourquoi}")
    if voie.nom != "telegram":
        console.print("[dim]Telegram atteint Alek et Sofiane où qu'ils soient ; la "
                      "notification macOS ne sort pas de ce Mac. Création du bot : "
                      "docs/EXPLOITATION.md § alertes.[/]")


@notify_app.command("test")
def notify_test(
    message: str = typer.Option("alerte de test de l'étape 22.2", "--message"),
) -> None:
    """Envoie une alerte de test par le canal disponible."""
    from factory.orchestrator import notify as notify_module

    conn = _base_file()
    try:
        envoi = notify_module.envoyer("🔔 BMS — test", message, motif="test", conn=conn)
    finally:
        conn.close()
    couleur = "green" if envoi.ok else "red"
    console.print(f"canal [bold]{envoi.canal}[/] : [{couleur}]"
                  f"{'envoyée' if envoi.ok else 'NON envoyée'}[/] — {envoi.reponse}")
    if not envoi.ok:
        raise typer.Exit(code=1)


@notify_app.command("revue")
def notify_revue() -> None:
    """Passe les six motifs en revue et envoie ce qui a changé depuis la dernière fois."""
    from factory.orchestrator import notify as notify_module

    conn = _base_file()
    try:
        envois = notify_module.verifier_et_alerter(conn)
    finally:
        conn.close()
    if not envois:
        console.print("[green]rien à signaler[/] (ou déjà signalé — "
                      "workspace/logs/alertes.json)")
        return
    for envoi in envois:
        console.print(f"[{'green' if envoi.ok else 'red'}]{envoi.motif}[/] par "
                      f"{envoi.canal} : {envoi.reponse}")




# --------------------------------------------------------------------------------------
# Calendrier et checklist de pré-publication (étape 23.2)
# --------------------------------------------------------------------------------------


def _afficher_calendrier(conn, check: bool) -> int:
    from factory.publish import calendar

    ctx = calendar.contexte()
    evts = calendar.evenements(conn, ctx.racine)
    semaines = calendar.lignes_par_semaine(ctx, evts)
    for semaine, lignes in semaines.items():
        table = Table(title=semaine, header_style="bold")
        for colonne in ("Chaîne", "Jour local", "Heure locale", "UTC", "Paris", "Run",
                        "Statut", "Durée"):
            table.add_column(colonne)
        for l in lignes:
            table.add_row(l["chaine"], l["jour"], l["heure"], l["utc"], l["paris"], l["run"],
                          l["statut"], l["duree"])
        console.print(table)
    if not semaines:
        console.print("[dim]aucune date au calendrier[/]")
    par_chaine: dict[str, int] = {}
    for e in evts:
        par_chaine[e.channel_id] = par_chaine.get(e.channel_id, 0) + 1
    console.print("total : " + ", ".join(f"{c} {n}" for c, n in sorted(par_chaine.items()))
                  + f" — {len(evts)} vidéo(s)")
    if not check:
        return 0
    violations, avertissements = calendar.verifier(ctx, evts)
    for a in avertissements:
        console.print(f"[yellow]avertissement[/] {a}")
    for v in violations:
        console.print(f"[red]VIOLATION[/] {v.regle} : {v.message}")
    cal = ctx.cal
    console.print(
        f"contrôle : {len(violations)} violation(s), {len(avertissements)} avertissement(s) — "
        f"règles : ≤ plafond/semaine par chaîne (jeune chaîne ≤ {cal.plafond_semaine_jeune_chaine}), "
        f"≥ {cal.espacement_chaine_h} h par chaîne, ≥ {cal.exclusion_portefeuille_min} min et "
        f"jamais la même heure entre chaînes, ≥ {cal.ecart_meme_langue_min} min entre chaînes de même langue, "
        f"≤ {cal.max_par_jour_portefeuille} vidéos BMS sur 24 h glissantes, aucune date dépassée")
    return len(violations)


@calendar_app.command("plan")
def calendar_plan(
    weeks: int = typer.Option(3, "--weeks", min=1, max=8, help="Horizon en semaines."),
    replan: bool = typer.Option(False, "--replan", help="Redate aussi les jobs déjà datés."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Calcule sans rien écrire."),
) -> None:
    """Date chaque job exporté ou en cours sans date (écrit jobs.publish_at, UTC)."""
    from factory.publish import calendar

    conn = _base_file()
    try:
        rapport = calendar.planifier(conn, semaines=weeks, replan=replan, ecrire=not dry_run,
                                     echo=lambda m: console.print(f"  {m}"))
        for d in rapport.ecartes:
            console.print(f"[yellow]non daté[/] job {d.job_id} {d.video_id} : {d.raison}")
        for a in rapport.durees_ajustees:
            console.print(f"[cyan]durée[/] {a}")
        console.print(f"{len(rapport.decisions)} job(s) daté(s), {len(rapport.ecartes)} écarté(s)"
                      + (" — [dim]dry-run, rien d'écrit[/]" if dry_run else ""))
        if not dry_run:
            _afficher_calendrier(conn, check=False)
    finally:
        conn.close()


@calendar_app.command("show")
def calendar_show(
    check: bool = typer.Option(False, "--check", help="Liste toute violation ; code 1 s'il y en a."),
) -> None:
    """Tableau par semaine et par chaîne, heure locale de l'audience et heure de Paris."""
    conn = _base_file()
    try:
        violations = _afficher_calendrier(conn, check)
    finally:
        conn.close()
    if violations:
        raise typer.Exit(code=1)


@app.command("precheck")
def commande_precheck(
    run: str = typer.Option(..., "--run", help="Identifiant du run."),
    channel: str = typer.Option(None, "--channel", help="Chaîne (défaut : celle du run)."),
) -> None:
    """Checklist de conformité avant upload (CONFORMITE § 11) → precheck.json. Code 5 si FAIL."""
    from factory.publish import precheck

    rapport = precheck.controler(run, channel)
    couleurs = {"ok": "green", "bloquant": "red", "avertissement": "yellow",
                "non_couvert": "dim"}
    table = Table(title=f"precheck — {run}", header_style="bold")
    for colonne in ("§ 11", "Contrôle", "Verdict", "Détail"):
        table.add_column(colonne, overflow="fold")
    for c in rapport.controles:
        table.add_row(c.ref, c.id, f"[{couleurs[c.verdict]}]{c.verdict}[/]", c.detail)
    console.print(table)
    couleur = "green" if rapport.statut == "PASS" else "red"
    console.print(f"[bold {couleur}]{rapport.statut}[/] — {len(rapport.bloquants)} bloquant(s), "
                  f"{len(rapport.avertissements)} avertissement(s) → "
                  f"workspace/runs/{run}/precheck.json")
    for c in rapport.bloquants:
        console.print(f"[red]raison[/] [{c.ref}] {c.id} : {c.detail}")
    if rapport.statut != "PASS":
        raise typer.Exit(code=5)



# --- étape 25 : performances ----------------------------------------------------------------

analytics_app = typer.Typer(
    add_completion=False, help="Performances YouTube jointes aux manifestes (étape 25).")
app.add_typer(analytics_app, name="analytics")


@analytics_app.command("pull")
def analytics_pull(
    channel: str = typer.Option(None, "--channel", help="Une chaîne ; défaut : toutes les authentifiées."),
    since: str = typer.Option(None, "--since",
                              help="Date AAAA-MM-JJ ou J-N ; défaut : 5 derniers jours, "
                                   "depuis la publication au premier passage."),
) -> None:
    """Tire Analytics API + rapports reach/basic, stocke tout localement."""
    from datetime import date, timedelta

    from factory.analytics import pull

    charge_env()
    depuis = None
    if since:
        depuis = (date.today() - timedelta(days=int(since[2:]))
                  if since.upper().startswith("J-") else date.fromisoformat(since))
    bilans = pull.tirer([channel] if channel else None, depuis=depuis)
    if not bilans:
        console.print("[yellow]Aucune chaîne authentifiée[/] (secrets/tokens/ vide) — "
                      "passage inscrit à analytics_runs, rien tiré.")
        return
    table = Table(header_style="bold")
    for col in ("chaîne", "statut", "vidéos", "lignes", "courbes", "rapports", "appels"):
        table.add_column(col)
    for b in bilans:
        table.add_row(b.channel, b.status, str(b.videos), str(b.rows), str(b.curves),
                      str(b.reports), str(b.calls))
    console.print(table)
    for b in bilans:
        for e in b.erreurs:
            console.print(f"  [red]{b.channel}[/] {e}")
    if any(b.status == "error" for b in bilans):
        raise typer.Exit(code=1)


@analytics_app.command("rotate-thumbnails")
def analytics_rotate_thumbnails(
    dry_run: bool = typer.Option(False, "--dry-run", help="Propose sans appeler thumbnails.set."),
) -> None:
    """Rotation J+7 : propose une autre variante si le CTR est sous la médiane de la chaîne."""
    from factory.analytics import rotation
    from factory.core import db
    from factory.core.paths import racine_projet

    conn = db.ouvrir()
    try:
        props = rotation.propositions(conn, racine_projet())
    finally:
        conn.close()
    if not props:
        console.print("Aucune vidéo à fenêtre J+7 complète : rien à proposer.")
    for p in props:
        console.print(f"{p['video_id']} → {p['proposal'] or 'aucune bascule'} ({p['reason']})",
                      markup=False, highlight=False)
    if not dry_run and any(p["proposal"] for p in props):
        console.print("[red]Exécution réelle non câblée[/] : thumbnails.set exige un jeton OAuth "
                      "(secrets/tokens/ vide). Relancer avec --dry-run.")
        raise typer.Exit(code=2)


@app.command("learn")
def commande_learn(
    dry_run: bool = typer.Option(False, "--dry-run", help="Calcule sans écrire weights.json ni le rapport."),
    objections: Path | None = typer.Option(
        None, "--objections", help="Fichier Markdown des objections du contradicteur, recopié au rapport."),
) -> None:
    """Apprend des vidéos publiées : effets rétrécis, rétention, banc ; écrit learned/weights.json."""
    from factory.analytics import learn
    from factory.core import db
    from factory.core.models import ApprentissageConfig
    from factory.core.paths import racine_projet

    racine = racine_projet()
    cfg = config_module.charger(racine, strict=False)
    p = (cfg.editorial.apprentissage if cfg.editorial else None) or ApprentissageConfig()
    conn = db.ouvrir()
    try:
        res = learn.executer(racine, conn, p, ecrire=not dry_run,
                             objections=objections.read_text("utf-8") if objections else None)
    finally:
        conn.close()
    w = res["weights"]
    actifs = sum(1 for f in w["factors"].values() for v in f["levels"].values() if v["active"])
    console.print(f"n = {w['n_videos']} vidéo(s) à J+7 complet · niveaux actifs : {actifs} · "
                  f"courbes : {res['retention']['n_curves']}")
    console.print(f"banc : {res['bench']['decision']}", markup=False, highlight=False)
    for k, v in res["paths"].items():
        console.print(f"[green]{k}[/] → {v}")


@analytics_app.command("show")
def analytics_show(
    video: str = typer.Option(None, "--video", help="video_id de run ou identifiant YouTube."),
    channel: str = typer.Option(None, "--channel", help="Tableau par vidéo d'une chaîne."),
) -> None:
    """Métriques, courbe de rétention en ASCII et chutes rattachées aux segments."""
    from factory.analytics import show
    from factory.core import db

    if not video and not channel:
        console.print("[red]--video ou --channel est requis[/]")
        raise typer.Exit(code=1)
    conn = db.ouvrir()
    try:
        if video:
            for ligne in show.rapport_video(conn, video):
                console.print(ligne, markup=False, highlight=False)
            return
        lignes = show.rapport_chaine(conn, channel)
        if not lignes:
            console.print(f"Aucune vidéo publiée pour « {channel} ».")
            return
        table = Table(header_style="bold")
        for col in ("vidéo", "publiée", "vues 7 j", "vues 30 j", "% vu 7 j", "CTR 7 j",
                    "impr. 7 j", "abo 7 j", "hook", "titre", "miniature"):
            table.add_column(col)
        def f(v, fmt="{:.0f}"):
            return "—" if v is None else fmt.format(v)
        for r in lignes:
            table.add_row(r["video_id"], (r["publish_at"] or "")[:10], f(r["views_7d"]),
                          f(r["views_30d"]), f(r["avg_view_pct_7d"], "{:.1f}"),
                          f(None if r["ctr_7d"] is None else r["ctr_7d"] * 100, "{:.2f} %"),
                          f(r["impressions_7d"]), f(r["subs_7d"]), r["hook_type"] or "—",
                          r["title_pattern"] or "—", r["thumbnail_template"] or "—")
        console.print(table)
    finally:
        conn.close()


# --------------------------------------------------------------------------------------
# Étape 27 — affiliation et économie unitaire
# --------------------------------------------------------------------------------------

links_app = typer.Typer(add_completion=False, help="Liens d'affiliation par vidéo (étape 27).")
app.add_typer(links_app, name="links")
revenue_app = typer.Typer(add_completion=False, help="Revenus : affiliation et publicité (étape 27).")
app.add_typer(revenue_app, name="revenue")


@links_app.command("build")
def links_build(
    run: str = typer.Option(..., "--run", help="video_id du run."),
    product: str = typer.Option(None, "--product", help="Force un produit de config/products/."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Affiche sans écrire le manifeste."),
) -> None:
    """Liens avec sous-identifiant → `manifest.conformite.affiliate_links`."""
    from factory.monetization import links

    liens = links.build_links(run, product_id=product, ecrire=not dry_run)
    if not liens:
        console.print("Aucun produit pour ce run (spec.product_id et channel.products vides).")
        return
    for lien in liens:
        console.print(f"{lien.product_id} [{lien.network}] {lien.subid_param}="
                      f"{lien.subid_value} → {lien.target_url}")
    console.print("manifeste " + ("non modifié (--dry-run)" if dry_run else "mis à jour"))


@revenue_app.command("import")
def revenue_import(
    program: str = typer.Option(..., "--program", help="amazon|awin|cj|impact|digistore24|clickbank"),
    file: Path = typer.Option(..., "--file", exists=True, dir_okay=False, help="Export CSV."),
    fixture: bool = typer.Option(False, "--fixture",
                                 help="Marque les lignes « fixture » (exclues de l'économie)."),
) -> None:
    """Importe un export de conversions dans la table `revenue`, rattaché par sous-identifiant."""
    from factory.core import db
    from factory.monetization import import_revenue

    origin = "fixture" if fixture or "fixtures" in file.parts else "import"
    conn = db.ouvrir()
    try:
        b = import_revenue.importer(conn, program, file, origin=origin)
    except ValueError as erreur:
        console.print(f"[red]{erreur}[/]")
        raise typer.Exit(code=2) from erreur
    finally:
        conn.close()
    console.print(f"{program} ({origin}) : {b.lues} lue(s), {b.inserees} insérée(s), "
                  f"{b.doublons} déjà présente(s), {b.annulees} annulée(s) ignorée(s)")
    if b.non_rattachees:
        console.print(f"[yellow]{len(b.non_rattachees)} non rattachée(s) à une vidéo[/] : "
                      + ", ".join(sorted(set(b.non_rattachees))))


@revenue_app.command("pull-ads")
def revenue_pull_ads(
    channel: str = typer.Option(None, "--channel", help="Une chaîne ; défaut : les publiées."),
    days: int = typer.Option(90, "--days", help="Fenêtre en jours."),
) -> None:
    """`estimatedRevenue` par vidéo et par jour (Analytics API, scope monétaire, YPP)."""
    from factory.core import db
    from factory.core.paths import racine_projet
    from factory.monetization import import_revenue

    charge_env()
    conn = db.ouvrir()
    try:
        bilans = import_revenue.tirer_ads(conn, racine_projet(), days,
                                          [channel] if channel else None)
    finally:
        conn.close()
    for b in bilans:
        couleur = "green" if b.statut == "ok" else "yellow"
        console.print(f"[{couleur}]{b.channel} — {b.statut}[/] : {b.message}")


@app.command("economics")
def economics_cmd(
    since: str = typer.Option(None, "--since", help="Fenêtre : 90d, ou date AAAA-MM-JJ."),
) -> None:
    """Coût et revenu par vidéo, agrégats → reports/economics.md."""
    from datetime import date, timedelta

    from factory.core import db
    from factory.core.paths import racine_projet
    from factory.monetization import economics

    racine = racine_projet()
    cfg = config_module.charger(racine, strict=False)
    if cfg.economics is None:
        console.print("[red]config/economics.yaml absent[/]")
        raise typer.Exit(code=2)
    depuis = None
    if since:
        depuis = (date.today() - timedelta(days=int(since[:-1]))
                  if since.endswith("d") else date.fromisoformat(since))
    conn = db.ouvrir()
    try:
        chemin, e = economics.ecrire(conn, cfg.economics, racine, depuis)
    finally:
        conn.close()
    console.print(f"{len(e.videos)} vidéo(s) livrée(s), coût total "
                  f"{sum(v.cout for v in e.videos):.2f} €, revenu {sum(v.revenu for v in e.videos):.2f} € "
                  f"→ {chemin.relative_to(racine)}")


# --------------------------------------------------------------------------------------
# Tableau de bord (étape 28)
# --------------------------------------------------------------------------------------

LABEL_DASHBOARD = "com.bms.factory.dashboard"


@app.command("dashboard")
def commande_dashboard(
    port: int = typer.Option(8501, "--port", help="Port local."),
    agent: bool = typer.Option(
        False, "--agent",
        help="Installe et charge un agent launchd qui garde le tableau de bord ouvert."),
) -> None:
    """Lance le tableau de bord Streamlit sur http://localhost:<port> (local seulement)."""
    import os
    import plistlib
    import subprocess
    import sys

    from factory.core.paths import racine_projet
    from factory.orchestrator import daemon as daemon_module
    from factory.orchestrator import journal

    racine = racine_projet()
    commande = [sys.executable, "-m", "streamlit", "run", str(Path(__file__).resolve().parents[1] / "dashboard" / "app.py"),
                "--server.address", "localhost", "--server.port", str(port),
                "--server.headless", "true", "--browser.gatherUsageStats", "false",
                "--client.toolbarMode", "viewer"]
    if agent:
        charge = daemon_module._plist_commun(  # noqa: SLF001
            racine, LABEL_DASHBOARD, commande,
            journal.dossier_logs(racine) / "dashboard.log")
        charge["RunAtLoad"] = True
        charge["KeepAlive"] = True
        fichier = daemon_module.dossier_agents() / f"{LABEL_DASHBOARD}.plist"
        fichier.parent.mkdir(parents=True, exist_ok=True)
        fichier.write_bytes(plistlib.dumps(charge))
        fichier.chmod(0o644)
        code, sortie = daemon_module.charger_agent(LABEL_DASHBOARD, racine)
        couleur = "green" if code == 0 else "red"
        console.print(f"[{couleur}]{fichier}[/] — launchctl {code} {sortie}".rstrip())
        console.print(f"tableau de bord : http://localhost:{port}")
        raise typer.Exit(code=0 if code == 0 else 1)
    console.print(f"tableau de bord : http://localhost:{port} — Ctrl+C pour arrêter")
    serveur = subprocess.Popen(commande, cwd=racine)
    # `headless` évite la question « Email » du premier lancement ; on ouvre le navigateur ici.
    if not os.environ.get("FACTORY_DASHBOARD_NO_BROWSER"):
        subprocess.Popen(["sh", "-c", f"sleep 3; open http://localhost:{port}"])
    try:
        code = serveur.wait()
    except KeyboardInterrupt:
        serveur.terminate()
        code = serveur.wait()
    raise typer.Exit(code=code)


# --------------------------------------------------------------------------------------
# Bibliothèque d'assets (étape 29)
# --------------------------------------------------------------------------------------

library_app = typer.Typer(add_completion=False,
                          help="Bibliothèque d'assets : index, statistiques, recherche, purge.")
app.add_typer(library_app, name="library")


def _base_bibliotheque():
    from factory.core import db
    from factory.core.paths import racine_projet

    return db.ouvrir(racine_projet() / "workspace" / "factory.db")


@library_app.command("scan")
def library_scan(
    sans_embeddings: bool = typer.Option(False, "--sans-embeddings",
                                         help="Index seul, sans calcul d'embeddings."),
) -> None:
    """Réindexe workspace/library/ (fichiers, licences, pHash, descriptions, embeddings)."""
    from factory import library

    r = library.scan(_base_bibliotheque(), avec_embeddings=not sans_embeddings, echo=console.print)
    console.print(f"{r['indexes']} asset(s) indexé(s) : {r['ajoutes']} ajouté(s), "
                  f"{r['mis_a_jour']} mis à jour, {r['orphelins_retires']} orphelin(s) retiré(s), "
                  f"{r['embeddings_calcules']} embedding(s) calculé(s) en {r['secondes']} s")
    for motif in r["refus"][:10]:
        console.print(f"[yellow]refusé[/] {motif}")
    if len(r["refus"]) > 10:
        console.print(f"[yellow]… {len(r['refus']) - 10} autre(s) refus[/]")


@library_app.command("stats")
def library_stats() -> None:
    """Comptes par type, taille, taux de réemploi sur les 10 derniers runs, top assets."""
    from factory import library

    s = library.stats(_base_bibliotheque())
    table = Table(title="bibliothèque — par type", header_style="bold")
    for c in ("Type", "Assets", "Taille (Mo)", "Emplois", "Sans embedding"):
        table.add_column(c, justify="right" if c != "Type" else "left")
    for kind in library.TYPES:
        v = s["par_type"].get(kind, {"assets": 0, "octets": 0, "emplois": 0, "sans_embedding": 0})
        table.add_row(kind, str(v["assets"]), f"{v['octets'] / 1e6:.1f}", str(v["emplois"]),
                      str(v["sans_embedding"]))
    console.print(table)
    r = s["reemploi_10_runs"]
    console.print(f"Réemploi sur les {r['runs']} derniers runs : {r['reemplois']} / {r['emplois']} "
                  f"emplois servis par un asset antérieur = [bold]{r['taux']:.1%}[/] · "
                  f"réemplois sémantiques journalisés : {s['reemplois_semantiques']}")
    top = Table(title="top 5 assets", header_style="bold")
    for c in ("asset_id", "Type", "Emplois", "Chaînes", "Description"):
        top.add_column(c, overflow="ellipsis")
    for t in s["top"]:
        top.add_row(t["asset_id"], t["kind"], str(t["uses"]), t["used_by"] or "", t["description"])
    console.print(top)


@library_app.command("find")
def library_find(
    description: str = typer.Argument(..., help="Description libre, en anglais de préférence."),
    kind: str = typer.Option(None, "--type", help="images, stock, music, sfx, characters, intros."),
    k: int = typer.Option(10, "--k", help="Nombre de résultats."),
) -> None:
    """Recherche sémantique dans la bibliothèque (embeddings e5-small)."""
    from factory import library

    table = Table(title=f"« {description} »", header_style="bold")
    for c in ("Similarité", "Type", "Emplois", "Chemin", "Description"):
        table.add_column(c, overflow="ellipsis")
    for r in library.find(_base_bibliotheque(), description, kind=kind, k=k):
        table.add_row(f"{r['similarity']:.3f}", r["kind"], str(r["uses"]), r["path"],
                      (r["description"] or "")[:60])
    console.print(table)


@library_app.command("prune")
def library_prune(
    unused_days: int = typer.Option(180, "--unused-days", help="Jours sans emploi."),
    executer: bool = typer.Option(False, "--execute",
                                  help="Supprime réellement (sinon simulation)."),
) -> None:
    """Assets inemployés depuis N jours (hors personnages et intros). Simulation par défaut."""
    from factory import library

    r = library.prune(_base_bibliotheque(), unused_days=unused_days, executer=executer)
    verbe = "supprimé(s)" if executer else "à supprimer (simulation, --execute pour agir)"
    console.print(f"{r['candidats']} asset(s) {verbe} — {r['octets'] / 1e6:.1f} Mo, "
                  f"inemployés avant {r['limite']}")
    for e in r["exemples"]:
        console.print(f"  {e}")


@library_app.command("intros")
def library_intros(channel: str = typer.Option(..., "--channel", help="Identifiant de chaîne.")) -> None:
    """Compose l'intro et l'outro de la charte et les verse dans library/intros/."""
    from factory import library

    cfg = config_module.charger()
    for chemin in library.construire_intros(cfg.get_channel(channel)):
        console.print(f"écrit {chemin}")


character_app = typer.Typer(add_completion=False,
                            help="Personnages récurrents : base, détourage, calques (étape 29).")
app.add_typer(character_app, name="character")


@character_app.command("build")
def character_build(personnage: str = typer.Argument(..., help="Dossier sous library/characters/.")) -> None:
    """Base générée, détourage rembg, 3 essais d'édition mesurés, calques de bouche et d'yeux."""
    from factory import characters

    conf = characters.construire(personnage, echo=console.print)
    console.print(f"{personnage} : calques par {conf['derivation']['methode']}, "
                  f"graine {conf['seed']}")


if __name__ == "__main__":
    app()
