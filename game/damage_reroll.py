"""Re-export of game/notation_reroll.py, under this module's former name.

The class moved when Breath of Vaul made it serve an ATTACKS roll as well as a
Damage one - see that module's docstring. Kept as a shim rather than updating
every caller for the same reason game/crit_ap.py is one: there stays exactly
ONE definition, and an import that has not been moved yet still finds it
instead of quietly finding a copy.
"""
from game.notation_reroll import DamageRerollOffer  # noqa: F401
