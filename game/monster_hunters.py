"""Beast Snagga Boyz' own "Monster Hunters" ability, as supplied by the user
(not a rule from the generic 40k core rulebook, so it lives in its own module
- same reasoning as game/sunforge.py for the Crisis Sunforge Battlesuits' and
game/target_uploaded.py for the Pathfinders').

RULE: Each time a model in this unit makes an attack that targets a MONSTER
or VEHICLE unit, you can re-roll the Hit roll.

THE SAME TARGET TEST AS TANK HUNTERS, A DIFFERENT KIND OF EFFECT
----------------------------------------------------------------
Tankbustas' Tank Hunters (game/squad.py's tank_hunters_modifiers()) reads
word-for-word the same condition - "makes an attack that targets a MONSTER
or VEHICLE unit" - so the target half reuses that same
is_monster_or_vehicle_unit() helper rather than restating it.

What differs is the effect. Tank Hunters is a MODIFIER, so it belongs in
_hit_modifiers()/_wound_modifiers(), which adjust a threshold before any
dice are read. A re-roll is not a modifier: it needs the dice to have been
rolled and read first, so it hooks the hit-roll STEP itself, next to rule
24.38 ([TWIN-LINKED])'s own wound-roll offer.

BOTH PHASES - AND THAT IS THE RULE, NOT A GENERALISATION
---------------------------------------------------------
"makes an attack", not "makes a ranged attack" (contrast Sunforge, whose own
line does say ranged). So this is wired into game/shooting.py AND
game/fight.py, exactly like Tank Hunters is, and for the same reason.

BOTH SCOPES ARE OFFERED - THE PLAYER PICKS
-------------------------------------------
The prompt has three options: re-roll the failures only, re-roll the whole
roll, or keep the result. That is an explicit user instruction ("man muss
die entscheidung haben entweder nur fails zu rerollen, oder alles zu
rerollen"), and it is the right shape here because neither scope dominates
the other:

  * failures only keeps every hit already rolled, so it can never lose
    anything - but it also cannot improve a hit into a Critical Hit;
  * the whole roll discards the current result, so it CAN lose hits - but
    against a roll with few failures and no criticals it is the only option
    that can actually change the outcome (which matters a lot with War
    Horde's army-wide [SUSTAINED HITS 1] turning every critical into an
    extra hit).

This is the first re-roll in this engine offered as a genuine two-way
choice. The wound side works differently, and deliberately: there each
source is pinned to one scope by its own explicit ruling - rule 24.38
([TWIN-LINKED]) to failures only, Breach and Clear and Sunforge to the whole
roll - see game/shooting.py's _wound_reroll_is_full(). Those rulings are
untouched.

RE-ROLLING ONCE
---------------
A die can never be re-rolled more than once, however many effects would each
allow it (game/dice.py's already_rerolled ledger, and CLAUDE.md's own entry
on the bug that came from not tracking that). Only the still-free share of
the roll is thrown again; whatever a Command Re-roll (15.02) or Forward
Observers already threw keeps what it landed on, and the hits among THOSE
dice are carried over even by a "discard the previous result" re-roll.
"""

from game.squad import is_monster_or_vehicle_unit

MONSTER_HUNTERS_REROLL_LABEL = "Monster Hunters"


def unit_has_monster_hunters(squad):
    """True while at least one live model with the ability is in the unit -
    the same reading every other datasheet ability here uses (rule 19.04's
    "applies while a model that has it is still alive"), which also makes an
    attached Leader model's presence irrelevant in either direction."""
    if squad is None:
        return False
    return any(m.profile.monster_hunters for m in squad.models if not m.is_dead())


def applies(attacking_squad, target_squad):
    """Whether Monster Hunters grants its Hit-roll re-roll for this attack.

    Both halves of the printed condition: the attacking unit has the ability
    at all, and the TARGET is a MONSTER or VEHICLE unit."""
    if attacking_squad is None or target_squad is None:
        return False
    if not unit_has_monster_hunters(attacking_squad):
        return False
    return is_monster_or_vehicle_unit(target_squad)
