"""Canoptek Macrocytes' "Harassment Swarm" (Aura) - Necrons.

RULE (printed, word for word):
  "While an enemy unit (excluding MONSTERS and VEHICLES) is within 3" of this
   unit, each time a model in that unit makes an attack, subtract 1 from the
   Hit roll."

IT IS A DEFENDER-SIDE AURA READ AT THE ATTACKER'S SEAM, which is the one thing
easy to get backwards here: the penalty lands on the attacks made BY the unit
standing near the Macrocytes, not on attacks made against it. So both attack
steps ask it of the unit that is SHOOTING or FIGHTING.

"EACH TIME A MODEL IN THAT UNIT MAKES AN ATTACK" says ATTACK, not "ranged
attack", so it reaches BOTH game/shooting.py's _hit_modifiers() and
game/fight.py's. Written out because the two neighbours in those folds
(Skullsquirm Blight, Suppression Volley) each reach only one, and the printed
noun is the whole difference.

"EXCLUDING MONSTERS AND VEHICLES" is checked with any() under rule 19.03's
keyword pooling - an attached unit has all of its models' keywords, so a
MONSTER in a unit exempts the unit. That is the same reading every other
keyword exclusion here takes.

A SQUAD FLAG STAMPED ONCE PER FRAME, for the reason Nurgle's Gift records: the
readers are hit-modifier folds that run per attack group, and re-deriving 3" of
geometry per group is what that module already decided against. Two properties
follow that a cached answer would not have: positions change every frame, and a
wiped-out Macrocyte unit stops projecting in the same frame it dies.
"""

from game.modifiers import Modifier

HARASSMENT_SWARM_LABEL = "Harassment Swarm"

#: "within 3" of this unit".
HARASSMENT_SWARM_RANGE_IN = 3.0
#: "subtract 1 from the Hit roll" - a WORSENING modifier, so POSITIVE on the
#: threshold under this engine's sign convention.
HARASSMENT_SWARM_PENALTY = 1


def _living(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


def unit_has_ability(squad):
    return squad is not None and any(
        getattr(m.profile, "harassment_swarm", False) for m in _living(squad))


def is_exempt(squad):
    """"(excluding MONSTERS and VEHICLES)", pooled per rule 19.03."""
    return any(getattr(m.profile, "monster", False) or getattr(m.profile, "vehicle", False)
               for m in _living(squad))


def _edge_distance(a, b):
    dx, dy = a.x_in - b.x_in, a.y_in - b.y_in
    return max(0.0, (dx * dx + dy * dy) ** 0.5 - a.radius_in - b.radius_in)


def applies(squad, all_tokens=()):
    """Whether THIS unit's attacks are at -1 right now."""
    if squad is None or is_exempt(squad):
        return False
    mine = _living(squad)
    if not mine:
        return False
    owner = getattr(squad, "owner", None)
    for token in all_tokens or ():
        other = getattr(token, "squad", None)
        if other is None or other.owner == owner or token.is_dead():
            continue
        if not getattr(token.profile, "harassment_swarm", False):
            continue
        if any(_edge_distance(token, m) <= HARASSMENT_SWARM_RANGE_IN for m in mine):
            return True
    return False


def refresh(all_tokens=()):
    """Stamp Squad.harassment_swarm_penalty for every unit on the board, once
    per frame - beside Nurgle's Gift and the Necron Feel No Pain auras."""
    squads = {}
    for token in all_tokens or ():
        squad = getattr(token, "squad", None)
        if squad is not None:
            squads[id(squad)] = squad
    for squad in squads.values():
        squad.harassment_swarm_penalty = applies(squad, all_tokens)


def hit_modifiers(squad):
    """Read by BOTH attack steps' _hit_modifiers() folds."""
    if squad is None or not getattr(squad, "harassment_swarm_penalty", False):
        return []
    return [Modifier(HARASSMENT_SWARM_PENALTY, HARASSMENT_SWARM_LABEL)]
