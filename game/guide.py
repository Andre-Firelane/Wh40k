"""The Farseer's "Guide" - a datasheet ability, so its own module.

RULE (printed, word for word):
  "At the end of your Movement phase, select one enemy unit within 18" of and
  visible to this model. Until the start of your next Command phase, each time
  a friendly AELDARI model makes an attack that targets that enemy unit, add 1
  to the Hit roll. Each unit can only be selected for this ability once per
  turn."

The mark itself - when it is set, how the candidate is chosen, how long it
lives, and whose attacks read it - is shared with Eldrad Ulthran's Doom and
lives in game/psychic_mark.py; that module's docstring carries the reasoning
about the unusually long duration, the army-wide scope, and why range and
visibility are selection criteria rather than per-attack conditions.

WHAT IS THIS ABILITY'S OWN is only two things: it modifies the HIT roll, so it
hangs in _hit_modifiers() in both game/shooting.py and game/fight.py ("makes an
attack", not "makes a ranged attack"); and it DOES print the once-per-turn cap,
which Doom does not.

"EACH UNIT CAN ONLY BE SELECTED FOR THIS ABILITY ONCE PER TURN" caps a player
with several Farseers: two of them cannot both mark the same enemy unit in the
same turn. Note it says each UNIT, not each Farseer - so two Farseers may each
mark a DIFFERENT unit.
"""

from game.psychic_mark import PsychicMark

GUIDE_RANGE_IN = 18.0


class GuideController(PsychicMark):
    ability_name = "Guide"
    flag = "guide"
    effect_text = "add 1 to Hit rolls"
    range_in = GUIDE_RANGE_IN
    once_per_turn = True   # printed on this datasheet; Doom's is not


def squad_has_guide(squad):
    """Kept for callers that only want the predicate. The controller has the
    same check as a method, since it needs the bearer models anyway."""
    return any(getattr(m.profile, "guide", False) and not m.is_dead()
               for m in getattr(squad, "models", None) or ())
