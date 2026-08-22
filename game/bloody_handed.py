"""The Avatar of Khaine's "The Bloody-Handed" - a datasheet ability, so its own
module.

RULE (printed, word for word):
  "While a friendly AELDARI unit is within 6" of this model, add 1 to Advance
  and Charge rolls made for that unit."

THE FIRST AURA HERE THAT MODIFIES A ROLL rather than a characteristic. Every
other 6" aura in this codebase changes something about the unit itself (Psychic
Communion's Strength and Attacks, Psychic Guidance's Leadership and Hit rolls);
this one reaches into two dice rolls that already have a bonus hook, which is
why it needed no new plumbing - only a second source at each.

MEASURED PER MODEL, unit-wide result. "While a friendly AELDARI unit is within
6 inches of this model" is satisfied by ANY model of that unit being within 6"
of the Avatar - so the aura is read the same way game/psychic_communion.py
reads its own: centre to centre, matching how every "within X inches of a
model" aura here measures, and the answer applies to the whole unit because
that is who the roll is made for.

FRIENDLY AELDARI is asked of the SQUAD, using the same faction test
game/psychic_guidance.py, game/psychic_mark.py and game/whispering_web.py use.
Rule 19.01 only merges same-faction units, so no attached unit's models can
disagree.

IT REACHES THE AVATAR'S OWN UNIT TOO. He is a one-model unit, and "a friendly
AELDARI unit within 6" of this model" includes his own (distance 0 to himself).
That is the printed wording taken literally, and it is what a reader would
expect of a self-buffing aura - noted because "excluding this unit" is a clause
these auras often carry and this one does not.
"""

from game import psychic_guidance

BLOODY_HANDED_RANGE_IN = 6.0
BLOODY_HANDED_ROLL_BONUS = 1


def _bearers(all_tokens, owner):
    for token in all_tokens or ():
        if token.is_dead() or not getattr(token.profile, "bloody_handed", False):
            continue
        squad = getattr(token, "squad", None)
        if squad is not None and squad.owner == owner:
            yield token


def roll_bonus(squad, all_tokens=None):
    """The bonus this unit currently adds to its Advance and Charge rolls from
    this aura, or 0."""
    if squad is None or not squad.models:
        return 0
    if not psychic_guidance._is_aeldari(squad):
        return 0
    for bearer in _bearers(all_tokens, squad.owner):
        for model in squad.models:
            if model.is_dead():
                continue
            dx, dy = model.x_in - bearer.x_in, model.y_in - bearer.y_in
            if (dx * dx + dy * dy) ** 0.5 <= BLOODY_HANDED_RANGE_IN:
                return BLOODY_HANDED_ROLL_BONUS
    return 0
