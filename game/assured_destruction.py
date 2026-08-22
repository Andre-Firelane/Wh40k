"""Fire Dragons' "Assured Destruction" - a datasheet ability, so its own
module, like every other named ability here.

RULE (printed, word for word):
  "In your Shooting phase, each time a model in this unit makes a ranged attack
  that targets a MONSTER or VEHICLE unit, you can re-roll the Hit roll, you can
  re-roll the Wound roll and you can re-roll the Damage roll."

THREE RE-ROLLS, THREE EXISTING MECHANISMS, NO NEW ONES
------------------------------------------------------
This is Crisis Sunforge Battlesuits' Sunforge ability plus a Hit-roll re-roll
plus a phase restriction, so all three halves plug into machinery that already
exists and nothing here re-derives an offer:

  * the HIT half joins game/shooting.py's _hit_reroll_reason(), which already
    offers this exact choice for Beast Snagga Boyz' Monster Hunters - and
    offers BOTH scopes (failures only / the whole roll) as a real decision,
    per the user's own instruction there;
  * the WOUND half joins _wound_reroll_reason()/_wound_reroll_is_full(),
    alongside [TWIN-LINKED], Breach and Clear and Sunforge;
  * the DAMAGE half is game/damage_reroll.py's DamageRerollOffer - extracted
    from game/sunforge.py precisely because this is its second consumer.

WHOLE ROLL, NOT FAILURES ONLY - and it is worth saying why, because this repo
has read the two apart before. The printed line says "you can re-roll the Hit
roll" / "the Wound roll" with no "failed", which is word for word the wording
that settled Breach and Clear and Sunforge as full re-rolls; [TWIN-LINKED] is
the failures-only one on an explicit user correction about that keyword. And in
practice the distinction costs nothing here: wherever a full re-roll is on
offer, shooting.py also offers the failures-only subset of it, since "you can
re-roll the roll" permits re-rolling fewer of its dice than all.

"IN YOUR SHOOTING PHASE" IS A REAL RESTRICTION, not decoration - and it is the
one thing that differs from Sunforge, whose own line has no phase clause. The
ranged attacks that happen OUTSIDE your Shooting phase are reactive Snap Shots
(Fire Overwatch, 15.08/15.09), which land at the end of the opponent's Movement
phase. Those get none of this.
"""

from game.squad import is_monster_or_vehicle_unit
from game.turn import PHASE_SHOOTING

ASSURED_DESTRUCTION_LABEL = "Assured Destruction"


def unit_has_assured_destruction(squad):
    """True while at least one live model with the ability is in the unit -
    rule 19.04's "applies while a model that has it is still alive", the same
    reading every other datasheet ability here uses."""
    if squad is None:
        return False
    return any(getattr(m.profile, "assured_destruction", False)
               for m in squad.models if not m.is_dead())


def applies(attacking_squad, target_squad, turn_tracker=None):
    """Whether this attack is one the ability covers.

    is_monster_or_vehicle_unit() is the engine's single definition of that
    keyword test (rule 19.03 pooling included), already used by rule 10.06's
    Close-Quarters malus - reused rather than re-derived.

    `turn_tracker` is optional so a caller that has none degrades to checking
    only the printed target clause; every real caller passes one, and without
    it the phase half of the WHEN cannot be answered at all."""
    if attacking_squad is None or target_squad is None:
        return False
    if not unit_has_assured_destruction(attacking_squad):
        return False
    if not is_monster_or_vehicle_unit(target_squad):
        return False
    if turn_tracker is not None:
        # "In YOUR Shooting phase" - turn_owner, not active_player: the latter
        # is a transient "whose decision is this right now" flag that a
        # defending save roll or a reactive stratagem flips, and this question
        # is about whose phase it actually is (the same bug class documented
        # in ai/agent_driver.py's _is_blocked()).
        if turn_tracker.phase != PHASE_SHOOTING:
            return False
        if turn_tracker.turn_owner != attacking_squad.owner:
            return False
    return True
