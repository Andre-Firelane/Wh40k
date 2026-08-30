"""Re-export of game/critical_wound_split.py, which this module became.

The name described what its first two sources CHANGE - the Armour Penetration -
and Spirit Conclave's Stave of Kurnous, the third, changes whether the attack
has [PRECISION] instead. Same split, different consequence, so the module moved
to a name that describes the QUESTION.

Kept as a re-export rather than updating every caller in one go, the same way
game/tau_detachments.py re-exports game/detachment_gate.py: one definition, and
existing readers keep their own vocabulary.
"""

from game.critical_wound_split import (  # noqa: F401
    adjusted_weapon, applies, label, sources)
