"""Warhost's "Martial Grace" - the detachment rule.

RULE (printed, word for word):
  "- At the start of the battle round, you receive 1 additional Battle Focus
     token.
   - Each time a unit from your army performs the Swift as the Wind Agile
     Manoeuvre, until the end of the phase, add an additional 1" to the Move
     characteristic of models in that unit.
   - Each time a unit from your army performs an Agile Manoeuvre that involves
     rolling a D6, add 1 to the result."

THREE CLAUSES, ALL OF THEM ABOUT THE ARMY RULE, so all three live in
game/battle_focus.py's own seams rather than anywhere new. That is the point of
this detachment: it does not add a mechanism, it turns the dials on the one the
faction already has.

  1. the token grant   -> BattleFocusPool.sync_battle_round()
  2. the extra inch    -> battle_focus.movement_bonus_in()
  3. the +1 on a D6    -> BattleFocusPool._perform_reactive()

NO ASURYANI CHECK IS NEEDED, and that is worth saying because two of its
siblings do need one. Every clause here is about "a unit from your army" that
is USING Battle Focus, and has_battle_focus() already restricts that to the
units which print the ability. A keyword test on top would be a second gate
saying the same thing.

WHICH MANOEUVRES ACTUALLY ROLL A D6 IS MEASURED, NOT ASSUMED. The clause says
"an Agile Manoeuvre that involves rolling a D6", and the six are not built
alike: Swift as the Wind, Flitting Shadows, Star Engines and Sudden Strike all
grant a flat effect with no roll, and only Opportunity Seized and Fade Back
throw anything - both through the single _perform_reactive() call, which is why
this clause reaches exactly one site. Sudden Strike is the near-miss: its "up
to 6 inches" is a distance, not a die.

THE TOKEN CLAUSE IS PER PLAYER, not per pool. tokens_for_battle_size() answers
a question about the BATTLE SIZE and knows nothing about who is fielding what;
the grant loop in sync_battle_round() is where a player is in scope, so the
extra token is added there. Putting it in tokens_for_battle_size() would have
given it to both armies.
"""

from game import aeldari_detachments

MARTIAL_GRACE_LABEL = "Martial Grace"

#: "you receive 1 ADDITIONAL Battle Focus token".
MARTIAL_GRACE_EXTRA_TOKENS = 1

#: "add an ADDITIONAL 1 inch to the Move characteristic" - on top of Swift as
#: the Wind's own 2", not instead of it.
MARTIAL_GRACE_EXTRA_MOVE_IN = 1.0

#: "add 1 to the result" of an Agile Manoeuvre's D6.
MARTIAL_GRACE_ROLL_BONUS = 1

#: The config constant game/detachments.py writes for Warhost.
SETTING = "WARHOST_PLAYERS"


def has_detachment(player):
    return aeldari_detachments.has_detachment(player, SETTING)


def extra_tokens_for(player):
    """Clause 1. Zero for anyone not fielding Warhost, so the caller can add it
    unconditionally."""
    return MARTIAL_GRACE_EXTRA_TOKENS if has_detachment(player) else 0


def extra_move_in(squad):
    """Clause 2 - and it is conditional on the MANOEUVRE, not just on the
    detachment: "each time a unit performs the SWIFT AS THE WIND Agile
    Manoeuvre". A unit of a Warhost army that has not used it gets nothing,
    which is what makes this an addition to that manoeuvre rather than a flat
    +1" for the whole army."""
    if squad is None or not has_detachment(getattr(squad, "owner", None)):
        return 0.0
    if not getattr(squad, "swift_as_the_wind_active", False):
        return 0.0
    return MARTIAL_GRACE_EXTRA_MOVE_IN


def roll_bonus_for(squad):
    """Clause 3. Applied to the RESULT of the die, not to the die itself -
    "add 1 to the result" - so a caller adds it after summing, and nothing
    here changes what was rolled."""
    if squad is None or not has_detachment(getattr(squad, "owner", None)):
        return 0
    return MARTIAL_GRACE_ROLL_BONUS
