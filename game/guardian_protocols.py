"""Lychguard's "Guardian Protocols".

RULE (printed, word for word):
  "While a NOBLE model is leading this unit, each time an attack targets this
   unit, if the Strength characteristic of that attack is greater than this
   unit's Toughness characteristic, subtract 1 from the Wound roll."

THIS IS THE WAVE SERPENT SHIELD WITH A LEADER CLAUSE. The S > T comparison,
the -1, the defender side, even the sign convention are identical to
game/wave_serpent_shield.py.

AND THE ARITHMETIC IS NOW GENUINELY SHARED, which for two stages it was not.
This docstring used to claim it already was:

    "Writing a second S>T comparison would be exactly the 'two places, same
     question, two answers' drift this repo keeps consolidating away, so the
     shared arithmetic stays shared and only the condition differs."

Only the HOOK was shared. Both files carried their own
`toughness is not None and strength > toughness`, and the sentence above was a
comment promising a behaviour no code delivered - the class this repo keeps
catching (see game/scouts.py's missing human branch). The Catacomb Command
Barge's Advanced Quantum Shielding is the third carrier, and it paid for
game/strength_over_toughness.py (the 50th extraction). This module keeps its
name and RE-EXPORTS what it always exported, so no caller moves.

TWO DIFFERENCES FROM THE SHIELD, both straight out of the printed text:

  * "each time an ATTACK targets this unit", not "each time a RANGED attack".
    So this is wired into game/fight.py as well as game/shooting.py - the
    Wave Serpent's own line says ranged and is therefore shooting-only. That
    is now `ranged_only` on the carrier rather than a fact about which file
    imports what.
  * "While a NOBLE model is LEADING this unit" - rule 24.22's real attached
    unit (19.01), not merely a squad containing an Overlord. That is
    attached_units.leader_ability()'s exact job, and using it also brings
    19.04's grace window along, so a Noble killed mid-sequence does not
    silently drop the protection for the rest of the attacking unit's attacks.
    It is the ONLY one of the three carriers with an extra clause at all.

WHY THE TOUGHNESS COMES FROM attached_unit_toughness(): rule 19.02, and the
same reason the wound threshold itself reads it. THIS CANNOT MATTER TODAY, and
that is measured rather than assumed: across every unit these five armies can
build, merged and unmerged, models[0].profile.toughness and
attached_unit_toughness() give the SAME answer - a Lychguard unit with an
Overlord attached is T5 either way. An earlier version of this paragraph
claimed the opposite ("here it genuinely matters"); it was wrong, and the
probe that tried to redden it reported NO BITE, which is how it was found.
It is written this way because nothing in rule 19.02 guarantees a future Noble
shares its bodyguard's Toughness, not because a board today can tell the two
readings apart.
"""

from game.strength_over_toughness import GUARDIAN_PROTOCOLS

GUARDIAN_PROTOCOLS_PENALTY = GUARDIAN_PROTOCOLS.penalty   # positive: it raises the threshold, see game/modifiers.py
GUARDIAN_PROTOCOLS_LABEL = GUARDIAN_PROTOCOLS.label


def unit_has_guardian_protocols(squad):
    """Whether this unit prints the ability at all - read live off the models,
    so per 19.03 a merged unit has it if any component brought it."""
    return GUARDIAN_PROTOCOLS.unit_has(squad)


def is_led_by_noble(squad):
    """"While a NOBLE model is leading this unit"."""
    return GUARDIAN_PROTOCOLS.extra_condition(squad)


def applies(target_squad, strength):
    """Whether Guardian Protocols modifies THIS attack's Wound roll.

    `strength` is the attack's Strength as the wound step computes it - the
    already-adjusted value, not the printed one, so a weapon pushed past the
    unit's Toughness by something else is caught too."""
    return GUARDIAN_PROTOCOLS.applies(target_squad, strength)
