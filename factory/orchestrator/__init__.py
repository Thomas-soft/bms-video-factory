"""Orchestrateur de la fabrique : file de jobs, exécuteur, daemon, sauvegardes.

Découpage volontaire en quatre modules qui ne se connaissent que dans un sens :
`queue` remplit la file, `runner` la vide une étape à la fois, `daemon` appelle `runner`
dans une fenêtre horaire, `backup` ne dépend d'aucun des trois. Le journal (`journal`) est
partagé : c'est la seule trace qui survit à un `kill -9`.
"""
