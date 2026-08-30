"""The standalone Warlock's "Runes of Fortune" - a datasheet ability.

RULE (printed, word for word):
  "Each time an enemy unit declares a charge, if one or more units with this
  ability are selected as a target of that charge, subtract 2 from the Charge
  roll."

THE FOURTH TERM IN ONE FOLD, AND THE FIRST ON THE DEFENDER'S SIDE
-----------------------------------------------------------------
game/charge.py's _capped_roll() already subtracts Photon Grenades, Mont'ka's
`shaken` and the Night Spinner's `pinned` from a Charge roll. All three are
properties of the CHARGING unit. This one is a property of the TARGET, and it
is the reason the fold reads `self.charge_targets` rather than only the active
squad.

"IF ONE OR MORE UNITS WITH THIS ABILITY ARE SELECTED AS A TARGET" - so it is
enough that ONE of the declared targets carries it, and it does not stack with
itself across several such targets: the rule says "subtract 2", once. Measured
in the test with two Warlock-bearing targets, because a naive per-target sum
would read the same way in every one-target scenario.

19.03's pooling applies to the bearer test: a Warlock attached to a Guardian
Defenders unit makes THAT unit a unit with the ability, so charging the
Guardians pays the 2. That falls out of reading the flag off the models rather
than off the datasheet, and is the reading the printed text supports - the
attached unit IS a unit with the ability.
"""

RUNES_OF_FORTUNE_LABEL = "Runes of Fortune"

#: "subtract 2 from the Charge roll".
RUNES_OF_FORTUNE_PENALTY = 2


def squad_has_runes_of_fortune(squad):
    """Read live off the living models, so it ends with the Warlock."""
    if squad is None:
        return False
    return any(getattr(m.profile, "runes_of_fortune", False)
               for m in getattr(squad, "models", ()) or () if not m.is_dead())


def charge_penalty_against(targets):
    """-2 if any declared charge target carries it, and only ever -2.

    Takes the TARGET LIST because that is what the rule names. Returns 0 for an
    empty or None list, so the caller does not have to guard."""
    for squad in targets or ():
        if squad_has_runes_of_fortune(squad):
            return RUNES_OF_FORTUNE_PENALTY
    return 0
