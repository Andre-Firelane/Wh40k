"""Guardian Battlehost Enhancement: Breath of Vaul (10 pts).

RULE (verbatim, rules/aeldari/detachments/Guardian Battlehost.md):
  "ASURYANI model only. While the bearer is leading a STORM GUARDIANS unit,
  each time you roll to determine the number of attacks made with a flamer
  equipped by a model in that unit, you can re-roll the result, and each time
  you make a Damage roll for a model equipped with a fusion gun in that unit,
  you can re-roll the result."

(The corpus renders "killing heat of Vaul's" as "killing heal ofVaul's" - a
known Wahapedia artifact, transcribed rather than repaired, like the Farstalker
"tri-bade" typo.)

TWO RE-ROLLS ON TWO DIFFERENT ROLLS, and the pair is the whole point of the
card: the Storm Guardians' two special weapons each get their weak die
re-rolled. They are NOT one effect with two spellings.

  * the FLAMER's ATTACKS roll. A flamer's Attacks characteristic is a die
    (D6), rolled once per model before the Hit roll can start.
  * the FUSION GUN's DAMAGE roll.

THE ATTACKS HALF IS A SEAM THAT DID NOT EXIST. Damage-roll re-rolls have had a
home since Sunforge (game/notation_reroll.py); nothing had ever offered to
re-roll an ATTACKS roll. That module turned out to be entirely generic apart
from the word "Damage" in its prompt, so it took a `roll_name` parameter and a
rename rather than a second copy - see its docstring.

"YOU CAN RE-ROLL THE RESULT" - THE WHOLE ROLL, and an OFFER. Both halves say
it, so neither is a failures-only re-roll and neither belongs in
game/reroll_scope.py: that module is the narrower "the 1s OR the whole roll,
never just the failures" shape, and listing these there would offer the player
a subset the printed text never grants. Pinned as an ABSENCE, because that is
the only place it shows.

PER WEAPON, NOT PER TARGET. Every other source in the Damage-reroll chain
(Sunforge, Assured Destruction) asks about the TARGET; this one asks only what
the shooter is holding. So its predicate takes the weapon, and the target is
none of its business.

THE WEAPONS ARE MATCHED BY PROFILE CLASS, not by name string. "flamer" and
"fusion gun" are the printed Storm Guardian options, and the class is the
identity this engine already uses for that question (see game/sprites.py's own
note on printed names being free text).
"""
from game import attached_units, enhancements

BREATH_OF_VAUL = "Breath of Vaul"

BREATH_OF_VAUL_LABEL = "Breath of Vaul"

#: "a STORM GUARDIANS unit".
BREATH_OF_VAUL_KEYWORD = "STORM GUARDIANS"


def applies(squad):
    """The three conditions shared by both halves: carried, LEADING (24.22),
    and leading a STORM GUARDIANS unit specifically."""
    if squad is None:
        return False
    if not enhancements.is_active(squad, BREATH_OF_VAUL):
        return False
    if not attached_units.leader_ability(squad, "breath_of_vaul"):
        return False
    return attached_units.unit_has_datasheet_keyword(squad, BREATH_OF_VAUL_KEYWORD)


def _weapon_is(weapon, class_name):
    if weapon is None:
        return False
    return any(c.__name__ == class_name for c in type(weapon).__mro__)


def is_flamer(weapon):
    """The Storm Guardian flamer, whose ATTACKS characteristic is the die this
    re-rolls."""
    return _weapon_is(weapon, "AeldariFlamerProfile")


def is_fusion_gun(weapon):
    """The Storm Guardian fusion gun, whose DAMAGE roll this re-rolls."""
    return _weapon_is(weapon, "FusionGunProfile")


def attacks_reroll_applies(squad, weapon):
    """"the number of attacks made with a FLAMER equipped by a model in that
    unit"."""
    return is_flamer(weapon) and applies(squad)


def damage_reroll_applies(squad, weapon):
    """"a Damage roll for a model equipped with a FUSION GUN in that unit"."""
    return is_fusion_gun(weapon) and applies(squad)
