"""Publication vers les services API de YouTube — OAuth, upload, vérification.

Un seul chemin de code, drapeau `publish_path` (CONFORMITE § 2) : tant que
`youtube.audit_passed` est faux, l'upload est privé et la mise en ligne reste un geste
manuel dans YouTube Studio. Aucune automatisation de navigateur n'est employée ici ni
ailleurs : ce serait une violation des conditions d'utilisation, sanctionnée par la
terminaison en cascade (CONFORMITE § 1).
"""
