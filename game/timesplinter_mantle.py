""""Timesplinter Mantle" - the Chronomancer's own ability (Necrons).

RULE (printed, word for word):
  - This unit has Stealth.
  - Melee attacks that target this unit have -1 to hit rolls.

TWO HALVES, ONE ABILITY, AND THEY ARE ASKED DIFFERENTLY
-------------------------------------------------------
The first half needs NO CODE AT ALL, and the measurement is the point.
game/squad.py's squad_has_stealth() ends in unit_wide_ability(), which reads
like "EVERY model prints it" - the every-model question rule 24.33 asks of a
datasheet that prints the CORE ability, and the wrong one for an ability that
GRANTS it. So a source was added here for the attached case, and an A/B probe
that took it away again did not move a single answer: unit_wide_ability()
delegates to attached_units.unit_has_ability(), which is 19.04's
COMPONENT-wise reading ("every model of ANY still-conferring component"), and
the Chronomancer is a component all of whose models print Stealth.

The extra source was removed. This paragraph is what is left of it, because
"the obvious second source is redundant" is the kind of thing the next reader
would otherwise re-derive - or, worse, add back.

The second half is a DEFENDER-side melee malus, which is a
FightController._hit_modifiers() entry read off the TARGET squad - the same
seam game/forewarned.py sits in, and the same one Warhost's Lightning-Fast
Reactions uses. It is melee-only because the printed line says "melee
attacks", so it is NOT registered in game/shooting.py.

ANY-MODEL, NOT EVERY-MODEL, and not leader_ability() either. The printed
subject is "this unit", which is the Chronomancer's own one-model unit when
he stands alone and the merged unit once he is attached. leader_ability()
would be wrong for the first case: it requires a real attached unit (19.01)
by design, so a lone Chronomancer would lose his own mantle. unit_has_keyword()
is 19.03's any-model pooling and covers both.
"""

from game.attached_units import unit_has_keyword
from game.modifiers import Modifier

#: "-1 to hit rolls". A malus, so POSITIVE under this engine's convention -
#: game/modifiers.py adjusts the THRESHOLD, and a harder roll is a higher one.
MELEE_HIT_PENALTY = 1

LABEL = "Timesplinter Mantle"


def has_mantle(squad):
    """Rule 19.03's any-model pooling - see the module docstring for why this
    is neither unit_wide_ability() nor leader_ability()."""
    if squad is None:
        return False
    return unit_has_keyword(squad, lambda m: getattr(m.profile, "timesplinter_mantle", False))


def hit_modifiers(target_squad):
    """The melee half, in the list shape FightController._hit_modifiers()
    extends. Returns a list so a caller never has to test for None."""
    if not has_mantle(target_squad):
        return []
    return [Modifier(MELEE_HIT_PENALTY, LABEL)]
