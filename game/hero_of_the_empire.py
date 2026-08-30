"""Commander Shadowsun's "Hero of the Empire (Aura)".

RULE (printed, word for word):
  "While a friendly T'AU EMPIRE unit is within 6" of this model, each time a
   model in that unit makes a ranged attack, re-roll a Hit roll of 1."

AN AUTOMATIC RE-ROLL OF 1s, NOT AN OFFER. "re-roll a Hit roll of 1" carries no
"you can", so it joins the existing automatic-1s sources in
ShootingController's hit step (Forward Observers, Swift Demise, Hard-wired for
Destruction, Conquering Tyrant) rather than _hit_reroll_reason()'s offers. HIT
ONLY - Forward Observers, which it otherwise resembles exactly, re-rolls both
the Hit and the Wound roll, and copying that would hand out twice the ability.

AN AURA, so unlike every other source in that list it is not a property of the
attacking unit at all: it is a distance from a model in a THIRD unit. That is
why this takes the token list - there is no other way to find her.

MEASURED EDGE TO EDGE from HER MODEL, like every range in this engine, and
"while a friendly T'AU EMPIRE unit is within 6"" is satisfied by ANY one model
of that unit being in range: the aura affects the UNIT, so one model inside it
gives the whole unit the re-roll.

SHE IS T'AU EMPIRE HERSELF, so a lone Shadowsun benefits from her own aura -
the printed text excludes nothing, and "a friendly unit within 6" of this
model" is trivially true of her own unit at distance 0. Asserted rather than
left implicit, because "not the bearer's own unit" is the obvious wrong guess.

WHAT COUNTS AS T'AU EMPIRE is read off `for_the_greater_good`, which is exactly
the set of units the T'au army rule already treats as T'AU EMPIRE - and which
the Kroot deliberately lack, on their own datasheets' authority. So a Kroot
unit standing next to her gets nothing, which is the printed behaviour and is
its own test line.
"""

from game.squad import edge_distance

HERO_OF_THE_EMPIRE_LABEL = "Hero of the Empire"
HERO_OF_THE_EMPIRE_RANGE_IN = 6.0


def bearers(all_tokens, owner):
    """Living models belonging to `owner` that print the aura."""
    return [t for t in all_tokens or ()
            if not t.is_dead()
            and getattr(t.profile, "hero_of_the_empire", False)
            and getattr(getattr(t, "squad", None), "owner", None) == owner]


def applies(attacking_squad, all_tokens):
    """Whether this unit is currently inside the aura."""
    if attacking_squad is None or not all_tokens:
        return False
    models = [m for m in getattr(attacking_squad, "models", ()) or () if not m.is_dead()]
    if not any(getattr(m.profile, "for_the_greater_good", False) for m in models):
        return False
    for bearer in bearers(all_tokens, attacking_squad.owner):
        for model in models:
            if edge_distance(bearer, model) <= HERO_OF_THE_EMPIRE_RANGE_IN:
                return True
    return False
