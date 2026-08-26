"""The three DESTROYER CULT re-rolls.

One module because they are one family: three datasheets, three abilities that
all read "re-roll a roll of 1, and under some condition you can re-roll the
whole roll instead". Splitting them into three files would put the same shape
in three places and invite the second one to drift.

RULES (printed, word for word):

  Lokhust Destroyers, "Hard-wired for Destruction": "Each time a model in this
  unit makes a ranged attack that targets the closest eligible enemy unit,
  re-roll a Hit roll of 1. If that target is within range of an objective
  marker your opponent controls, you can re-roll the Hit roll instead."

  Skorpekh Destroyers, "Whirling Onslaught": "Each time a model in this unit
  makes a melee attack, re-roll a Hit roll of 1. If this unit made a Charge
  move this turn, you can re-roll the Hit roll instead."

  Lokhust Heavy Destroyers, "Optimised for Slaughter": "Each time a model in
  this unit makes an attack with an enmitic exterminator that targets a unit
  (excluding MONSTERS and VEHICLES), re-roll a Wound roll of 1. Each time a
  model in this unit makes an attack with a gauss destructor that targets a
  MONSTER or VEHICLE, re-roll a Wound roll of 1."

"INSTEAD" IS THE WORD THAT SHAPES ALL OF THIS, exactly as it does for the
Windriders' Swift Demise (game/swift_demise.py), which is the working
precedent this follows rather than inventing a second arrangement:

  * the base clause is NOT optional ("re-roll", not "you can"), so it is an
    automatic re-roll of just the natural 1s;
  * the upgrade is optional and covers the WHOLE roll, and it happens IN PLACE
    OF the 1s rather than on top of them.

So when the upgrade is available the automatic throw is held back and the
player picks one of the two; otherwise the 1s simply go. Doing the 1s first and
then offering the rest would be strictly more generous than the printed text.
game/reroll_scope.py is what tells the two attack steps that this source has
that shape.

OPTIMISED FOR SLAUGHTER IS THE ODD ONE OUT, twice over, and both differences
are in its text: it has NO upgrade clause at all (so it is a plain automatic
re-roll of 1s, like Forward Observers), and its condition is per WEAPON rather
than per unit - the exterminator wants soft targets, the destructor wants hard
ones. That is why it takes a `weapon` argument and the other two do not.
"""

from game.objectives import is_within_range_of_objective
from game.squad import is_monster_or_vehicle_unit
from game.weapons import EnmiticExterminatorProfile, GaussDestructorProfile

HARD_WIRED_LABEL = "Hard-wired for Destruction"
WHIRLING_ONSLAUGHT_LABEL = "Whirling Onslaught"
OPTIMISED_FOR_SLAUGHTER_LABEL = "Optimised for Slaughter"


def _unit_has(squad, attribute):
    """Rule 19.03: a merged unit counts as having an ability if any component
    brought it, which reading it live off the models gives for free."""
    if squad is None:
        return False
    return any(getattr(m.profile, attribute, False)
               for m in squad.models if not m.is_dead())


# --- Lokhust Destroyers -----------------------------------------------------

def _is_closest_target(squad, target_squad, candidates):
    """Whether `target_squad` is the closest of the eligible `candidates`.

    Same measurement and same reasoning as swift_demise.is_closest_target():
    "eligible" is rule 10.02's own term and the targeting step already
    answered it, so the caller passes what was eligible and this only
    measures. Ties count as closest - "the closest" cannot single out one of
    two equals."""
    if squad is None or target_squad is None:
        return False
    others = [c for c in candidates or () if c is not target_squad]
    if not others:
        return True
    gap = squad.min_distance_to(target_squad)
    return all(gap <= squad.min_distance_to(other) + 1e-9 for other in others)


def hard_wired_applies(squad, target_squad, candidates=()):
    """The base clause: a ranged attack against the CLOSEST eligible target."""
    if not _unit_has(squad, "hard_wired_for_destruction"):
        return False
    return _is_closest_target(squad, target_squad, candidates)


def hard_wired_offers_full_reroll(squad, target_squad, candidates=(), objectives=()):
    """The upgrade: "if that target is within range of an objective marker
    YOUR OPPONENT controls".

    Note the ownership clause - an objective this unit's own side controls does
    not qualify, and neither does a contested or neutral one. Read off
    Objective.controlled_by, the same field the mission scoring uses."""
    if not hard_wired_applies(squad, target_squad, candidates):
        return False
    enemy_held = [o for o in objectives or ()
                  if o.controlled_by is not None and o.controlled_by != squad.owner]
    return bool(enemy_held) and is_within_range_of_objective(target_squad, enemy_held)


# --- Skorpekh Destroyers ----------------------------------------------------

def whirling_onslaught_applies(squad):
    """The base clause. Unconditional apart from having the ability - it is
    the only one of the three with no target test at all."""
    return _unit_has(squad, "whirling_onslaught")


def whirling_onslaught_offers_full_reroll(squad):
    """The upgrade: "if this unit made a Charge move this turn".

    Squad.charged_this_turn, NOT Squad.fights_first - the latter also gets set
    by Counteroffensive (15.12), so it means "fights first", not "charged".
    game/crit_hit.py's Mandiblasters records the same trap."""
    if not whirling_onslaught_applies(squad):
        return False
    return bool(getattr(squad, "charged_this_turn", False))


# --- Lokhust Heavy Destroyers -----------------------------------------------

def optimised_for_slaughter_applies(squad, weapon, target_squad):
    """The whole ability: a per-WEAPON condition with no upgrade clause.

    The two halves are mirror images - the exterminator re-rolls against
    everything that is NOT a MONSTER or VEHICLE, the destructor against
    everything that IS - so one helper answers both by comparing the weapon to
    the target's own hardness."""
    if not _unit_has(squad, "optimised_for_slaughter") or weapon is None:
        return False
    hard = is_monster_or_vehicle_unit(target_squad)
    if isinstance(weapon, EnmiticExterminatorProfile):
        return not hard
    if isinstance(weapon, GaussDestructorProfile):
        return hard
    return False
