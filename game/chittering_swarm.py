"""Canoptek Scarab Swarms' "Chittering Swarm" (Necrons).

RULE (printed, word for word):
  "While an enemy unit is within Engagement Range of this unit, subtract 1 from
   the Objective Control characteristic of models in that enemy unit (to a
   minimum of 1). While this unit is within 6" of one or more friendly CRYPTEK
   models, the Objective Control characteristic of models in this unit is 1."

ONE PARAGRAPH, TWO CLAUSES, AND THEY ARE THE TWO FORMS game/objective_control.py
ALREADY KNOWS - which is the whole reason this fits in that fold rather than
growing a third shape:

  * clause 1 WORSENS by 1 to a minimum of 1, exactly like Scabrous Soulrot,
  * clause 2 SETS to 1, exactly like Hunting Hounds.

So this is the SECOND consumer of each form, and the ORDER that module already
records is what makes them compose: setters first, worsening second. A Scarab
inside a friendly Cryptek's 6" that is ALSO in Engagement Range of an enemy
therefore ends on 1 rather than 0 - the set gives it 1 and Soulrot's floor
(which is a floor on worsening, shared by every worsener) protects it.

THE TWO CLAUSES POINT IN OPPOSITE DIRECTIONS, and that is what makes them easy
to get backwards: the first is aimed at the ENEMY unit, the second at this
unit's OWN models. Each is written as its own function for that reason.

THE PRINTED OC 0 IS THE POINT OF CLAUSE 2. Scarab Swarms are the only OC 0
datasheet in this faction, so without a Cryptek nearby they contribute nothing
to holding an objective at all; the set is what turns four of them into four
points of control. And because it is a SET rather than an addition, the floor
in clause 1 cannot delete it.

"WITHIN ENGAGEMENT RANGE" is rule 03.04's 2", asked through game/engagement.py
rather than measured again here - the same definition Fire Overwatch and the
end-of-turn fight warning use.

"FRIENDLY CRYPTEK MODELS" is read off the DATASHEET keyword line, not a profile
flag: that is where the word is printed, and it keeps working for a Cryptek
added later without anyone remembering a flag. Five Crypteks carry it today,
and the Geomancer arriving in this same batch is the sixth.
"""

from game import engagement
from game.attached_units import model_has_datasheet_keyword

CHITTERING_SWARM_LABEL = "Chittering Swarm"

#: "the Objective Control characteristic of models in this unit is 1".
CHITTERING_SWARM_OC = 1
#: "subtract 1 ... (to a minimum of 1)".
CHITTERING_SWARM_ENEMY_PENALTY = 1
#: "within 6" of one or more friendly CRYPTEK models".
CRYPTEK_RANGE_IN = 6.0
CRYPTEK_KEYWORD = "CRYPTEK"


def _living(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


def unit_has_ability(squad):
    return squad is not None and any(
        getattr(m.profile, "chittering_swarm", False) for m in _living(squad))


def _edge_distance(a, b):
    dx, dy = a.x_in - b.x_in, a.y_in - b.y_in
    return max(0.0, (dx * dx + dy * dy) ** 0.5 - a.radius_in - b.radius_in)


def near_friendly_cryptek(squad, all_tokens=()):
    """Clause 2's condition: within 6" of one or more friendly CRYPTEK models.

    Measured base edge to base edge, like every other range test here. The
    CRYPTEK test is per MODEL and asked of the component it came from, so a
    Cryptek merged into a bodyguard unit under rule 19.01 still counts and its
    bodyguards do not."""
    if squad is None:
        return False
    owner = getattr(squad, "owner", None)
    mine = _living(squad)
    if not mine:
        return False
    for token in all_tokens or ():
        other = getattr(token, "squad", None)
        if other is None or other.owner != owner or token.is_dead():
            continue
        if not model_has_datasheet_keyword(other, token, CRYPTEK_KEYWORD):
            continue
        if any(_edge_distance(token, m) <= CRYPTEK_RANGE_IN for m in mine):
            return True
    return False


def objective_control(model, printed, all_tokens=()):
    """Clause 2, as a SETTER - the form game/objective_control.py folds first.

    `printed` is what the previous setter in that fold produced, so this
    behaves like every other one: it replaces, or it passes through."""
    if model is None or not getattr(model.profile, "chittering_swarm", False):
        return printed
    squad = getattr(model, "squad", None)
    if not near_friendly_cryptek(squad, all_tokens):
        return printed
    return CHITTERING_SWARM_OC


def worsen_enemy_oc(model, printed, all_tokens=()):
    """Clause 1, as a WORSENER - the form Scabrous Soulrot already has, and it
    shares that clause's reading of the floor.

    Aimed at the ENEMY: `model` here is a model of the unit being worsened, and
    the question is whether a Scarab unit is within Engagement Range of ITS
    unit. A printed 0 is left alone rather than clamped up to the floor - the
    clause is a floor on how far the rule may WORSEN a value, not a value it
    may raise something to."""
    if model is None or printed <= 0:
        return printed
    squad = getattr(model, "squad", None)
    if squad is None:
        return printed
    owner = getattr(squad, "owner", None)
    tokens = list(all_tokens or ())
    for other in _enemy_squads(tokens, owner):
        if unit_has_ability(other) and engagement.units_are_engaged(squad, other):
            return max(CHITTERING_SWARM_OC, printed - CHITTERING_SWARM_ENEMY_PENALTY)
    return printed


def _enemy_squads(all_tokens, owner):
    seen = {}
    for token in all_tokens or ():
        squad = getattr(token, "squad", None)
        if squad is not None and squad.owner != owner:
            seen[id(squad)] = squad
    return list(seen.values())
