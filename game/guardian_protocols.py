"""Lychguard's "Guardian Protocols".

RULE (printed, word for word):
  "While a NOBLE model is leading this unit, each time an attack targets this
   unit, if the Strength characteristic of that attack is greater than this
   unit's Toughness characteristic, subtract 1 from the Wound roll."

THIS IS THE WAVE SERPENT SHIELD WITH A LEADER CLAUSE. The S > T comparison,
the -1, the defender side, even the sign convention are identical to
game/wave_serpent_shield.py, so this reads the SAME hook: shooting.py's
_wound_modifiers(target_squad, strength). Writing a second S>T comparison
would be exactly the "two places, same question, two answers" drift this repo
keeps consolidating away, so the shared arithmetic stays shared and only the
condition differs.

TWO DIFFERENCES FROM THE SHIELD, both straight out of the printed text:

  * "each time an ATTACK targets this unit", not "each time a RANGED attack".
    So this is wired into game/fight.py as well as game/shooting.py - the
    Wave Serpent's own line says ranged and is therefore shooting-only.
  * "While a NOBLE model is LEADING this unit" - rule 24.22's real attached
    unit (19.01), not merely a squad containing an Overlord. That is
    attached_units.leader_ability()'s exact job, and using it also brings
    19.04's grace window along, so a Noble killed mid-sequence does not
    silently drop the protection for the rest of the attacking unit's attacks.

WHY THE TOUGHNESS COMES FROM attached_unit_toughness(): rule 19.02, and the
same reason the wound threshold itself reads it. Here it genuinely matters, as
opposed to the Wave Serpent's documented "cannot matter today" - a Lychguard
unit with an Overlord attached IS a mixed-Toughness unit (T5 both, as it
happens, but nothing about the rule guarantees that for a future Noble).
"""

from game.attached_units import leader_ability
from game.squad import attached_unit_toughness

GUARDIAN_PROTOCOLS_PENALTY = 1     # positive: it raises the threshold, see game/modifiers.py
GUARDIAN_PROTOCOLS_LABEL = "Guardian Protocols"


def unit_has_guardian_protocols(squad):
    """Whether this unit prints the ability at all - read live off the models,
    so per 19.03 a merged unit has it if any component brought it."""
    if squad is None:
        return False
    return any(getattr(m.profile, "guardian_protocols", False)
               for m in squad.models if not m.is_dead())


def is_led_by_noble(squad):
    """"While a NOBLE model is leading this unit"."""
    return leader_ability(squad, "noble")


def applies(target_squad, strength):
    """Whether Guardian Protocols modifies THIS attack's Wound roll.

    `strength` is the attack's Strength as the wound step computes it - the
    already-adjusted value, not the printed one, so a weapon pushed past the
    unit's Toughness by something else is caught too."""
    if strength is None or not unit_has_guardian_protocols(target_squad):
        return False
    if not is_led_by_noble(target_squad):
        return False
    toughness = attached_unit_toughness(target_squad)
    return toughness is not None and strength > toughness
