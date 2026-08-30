"""Spirit Conclave Enhancement: Stave of Kurnous (15 pts).

RULE (verbatim, rules/aeldari/detachments/Spirit Conclave.md):
  "SPIRITSEER model only. In your Command phase, select one friendly WRAITH
  CONSTRUCT unit within 12" of the bearer (excluding TITANIC units). Until the
  start of your next Command phase, each time a model in that unit makes an
  attack, on a Critical Wound, that attack has the [precision] ability."

THE MOST EXPENSIVE OF THE 28, and the cost is one word: "on a Critical Wound".

That is not a property of the attack, the weapon or the target - it is a
property of the DIE. A wound roll produces some critical wounds and some
ordinary ones from one weapon group, and only the critical share gets
[PRECISION]. This engine's Save roll is batched per group, so it cannot express
"these three wounds are precise and those four are not" in a single roll: the
critical share has to be pulled out and resolved separately.

THAT MACHINERY ALREADY EXISTED, for a different consequence.
game/critical_wound_split.py (which was game/crit_ap.py until this arrived)
does exactly this pull-out for Cadre Fireblade's Crack Shot and Seer Council's
Fate Inescapable, both of which give the critical share its own ARMOUR
PENETRATION. This is the third source, and the first whose consequence is not
an AP - which is why that module is now named after the question rather than
after what two of its three sources happen to change.

AND IT IS THE FIRST SOURCE THAT REACHES THE FIGHT PHASE. The other two print
"ranged", so game/fight.py never asked and had no critical-wound split at all.
This one says "makes AN ATTACK", and the units it can mark are Wraithblades,
Wraithguard and the Wraithlord - one of which is a pure melee datasheet. Read
as ranged-only it would have been nearly inert on its own targets. So the split
was mirrored into the Fight phase, which is the largest engine change in this
batch and the reason this Enhancement was built last in its stage.

"(EXCLUDING TITANIC UNITS)" IS PRINTED HERE AND ON NEITHER OF ITS TWO
NEIGHBOURS. Light of Clarity and Rune of Mists select from the same sentence
with no such clause, so the exclusion belongs to this module and not to the
shared marking machine - a shared filter would apply an exclusion two
Enhancements never printed. It is a MEASURED no-op today (nothing built is
TITANIC) and starts working by itself the day a Wraithknight is built.

THE MARKING HALF IS SHARED - see game/command_phase_mark.py, four carriers.
"""
import copy

from game import wraith_construct
from game.command_phase_mark import CommandPhaseMark

STAVE_OF_KURNOUS = "Stave of Kurnous"

#: 'select one friendly WRAITH CONSTRUCT unit within 12" of the bearer'.
STAVE_OF_KURNOUS_RANGE_IN = 12.0

FLAG_ATTR = "stave_of_kurnous_active"


def is_marked(squad):
    return bool(getattr(squad, FLAG_ATTR, False))


def applies(squad):
    """Read by game/critical_wound_split.py's source list, in BOTH phases."""
    return is_marked(squad)


def adjusted_weapon(weapon):
    """The weapon the CRITICAL share resolves against: the same weapon with
    [PRECISION]. A COPY, never the shared instance - and never a downgrade, so
    a weapon that already prints it comes back untouched."""
    if weapon is None or getattr(weapon, "precision", False):
        return weapon
    granted = copy.copy(weapon)
    granted.precision = True
    return granted


def eligible_target(squad):
    """"one friendly WRAITH CONSTRUCT unit ... (excluding TITANIC units)" -
    the exclusion is this card's alone."""
    return wraith_construct.is_non_titanic_wraith_construct(squad)


def reset(squads=()):
    for squad in squads or ():
        if squad is not None:
            setattr(squad, FLAG_ATTR, False)


class StaveOfKurnousController(CommandPhaseMark):
    """The Command-phase offer, on the shared machine."""

    def __init__(self, game_state=None, decision_manager=None, game_log=None,
                 auto_players=()):
        super().__init__(
            STAVE_OF_KURNOUS, STAVE_OF_KURNOUS_RANGE_IN, FLAG_ATTR,
            eligible_target,
            "scores [PRECISION] on a Critical Wound",
            game_state=game_state, decision_manager=decision_manager,
            game_log=game_log, auto_players=auto_players,
            exclude_own_unit=False,
        )
