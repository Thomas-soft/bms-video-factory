"""Ingénierie de la rétention (étape 16).

Quatre leviers, mesurés sur le registre et rendus exécutables : l'accroche (`hooks`), les
boucles ouvertes (`loops`), les ruptures de rythme (`interrupts`) et la densité d'information
(`density`). `verify` les vérifie tous sur un script écrit, avant la synthèse vocale : un
script qui viole une règle est régénéré avec le motif exact, jamais publié tel quel.

Les patrons et les listes de formulations vivent dans `patterns_<lang>.yaml`, pas dans le code
— la production est en anglais (décision d'Alek du 15/09/2026), le nommage reste prêt pour
l'étape 24, différée.
"""

from factory.retention import density, hooks, interrupts, loops, patterns, verify

__all__ = ["density", "hooks", "interrupts", "loops", "patterns", "verify"]
