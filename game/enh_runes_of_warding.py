"""Seer Council Enhancement: Runes of Warding (25 pts).

RULE (verbatim, rules/aeldari/detachments/Seer Council.md):
  "ASURYANI PSYKER model only. Models in the bearer's unit have the Feel No
  Pain 4+ ability against mortal wounds, Psychic Attacks and Critical Wounds
  caused by attacks with the [devastating wounds] ability."

THE FIRST FEEL NO PAIN SOURCE WITH THREE CONDITIONS. Every other conditional
one in game/feel_no_pain.py's fold has exactly one (Advanced Armour and
Layered Wards: mortal wounds). These are three separate questions asked of
three different places, and each is answered where that fact actually exists:

  * MORTAL WOUNDS - MortalWoundAllocationSession is the mortal-wound path
    (rule 06.02), so it is the one caller that passes mortal=True. Already
    threaded; this source just reads the same flag.
  * PSYCHIC ATTACKS - a property of the WEAPON (rule 24.29's [PSYCHIC]
    keyword), which only DamageAllocationSession holds. New parameter.
  * CRITICAL WOUNDS FROM [DEVASTATING WOUNDS] - a property of the SESSION:
    DevastatingWoundAllocationSession exists precisely because those wounds
    are resolved apart from the rest. New parameter, set there and nowhere
    else, so it cannot leak into an ordinary wound.

WHY `devastating` RATHER THAN REUSING `mortal`. [DEVASTATING WOUNDS] resolves
its share as mortal wounds in the printed rules, so it is tempting to have
DevastatingWoundAllocationSession pass mortal=True and get this clause for
free. It does NOT pass it today - a pre-existing gap, MEASURED and left alone
on purpose (a user decision): flipping it would silently change Advanced
Armour and Layered Wards, which are two other datasheets' rules, and that is a
separate decision from building this card. So this Enhancement carries its own
flag and works whatever that gap does later. Named here rather than quietly
depended on.

4+ IS THE BEST THRESHOLD IN THE FOLD, which _better_threshold() handles
without a precedence rule - and a model that already prints something better
keeps it, the "never worse than printed" guarantee the fold is built on.

"MODELS IN THE BEARER'S UNIT" - unit-wide, so it is asked of the SQUAD via the
model, exactly like Layered Wards next to it.
"""
from game.enhancements import is_active as _enh_is_active

RUNES_OF_WARDING = "Runes of Warding"

#: "the Feel No Pain 4+ ability".
RUNES_OF_WARDING_THRESHOLD = "4+"

RUNES_OF_WARDING_LABEL = "Runes of Warding"


def applies(model, mortal=False, psychic=False, devastating=False):
    """Whether this model has the granted Feel No Pain against THIS wound.

    All three printed conditions are alternatives ("against mortal wounds,
    Psychic Attacks and Critical Wounds caused by ..."), so any one of them is
    enough - reading them as a conjunction would make the Enhancement almost
    unreachable."""
    if model is None or not (mortal or psychic or devastating):
        return False
    return _enh_is_active(getattr(model, "squad", None), RUNES_OF_WARDING)


def feel_no_pain(model, mortal=False, psychic=False, devastating=False):
    """This model's granted Feel No Pain threshold against THIS wound, or "-".

    Same shape and same return convention as its two neighbours in the fold,
    advanced_armour_feel_no_pain() and layered_wards_feel_no_pain(): a
    threshold STRING so _better_threshold() keeps parsing it with
    parse_threshold(), and "-" rather than None for a wound this does not
    cover - None collapses the fold, which cost eight foreign suites once
    already (see game/ynnari_abilities.py's yvraines_champion_feel_no_pain)."""
    if not applies(model, mortal=mortal, psychic=psychic, devastating=devastating):
        return "-"
    return RUNES_OF_WARDING_THRESHOLD
