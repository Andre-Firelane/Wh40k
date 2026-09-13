"""Canoptek Court detachment rule: Power Matrix.

RULE (verbatim, rules/necrons/detachments/Canoptek Court.md):
  "Certain areas of the battlefield are considered to be within your army's
   Power Matrix, as follows:
   - Your deployment zone is always within your army's Power Matrix.
   - At the start of any phase, if you control at least half of the objective
     markers within No Man's Land, until the end of that phase, No Man's Land
     is within your army's Power Matrix.
   - At the start of any phase, if you control at least half of the objective
     markers within your opponent's deployment zone, until the end of that
     phase, your opponent's deployment zone is within your army's Power Matrix.
   Each time a model in a CRYPTEK or CANOPTEK unit from your army makes an
   attack, re-roll a Hit roll of 1. If such a unit is wholly within your army's
   Power Matrix, you can re-roll the Hit roll instead."

THREE REGIONS THAT PARTITION THE BOARD
--------------------------------------
Your deployment zone, the opponent's, and No Man's Land (everything in neither).
The Power Matrix is a UNION of some of them, so "wholly within the Power Matrix"
is a statement about which regions a base may NOT touch:

  own zone only              -> wholly within your own zone
  own zone + No Man's Land   -> not reaching into the opponent's zone
  own zone + opponent's zone -> wholly within one of the two (they are separated
                                by No Man's Land, so a base cannot span both
                                without touching it)
  all three                  -> anywhere on the battlefield

Measured with DeploymentZone's own signed distance (contains_circle() is rule
03.01's "wholly within"; distance_to_point() is conservative OUTSIDE a corner, so
it can refuse a base that is in fact clear - the safe direction for a bonus).

"AT THE START OF ANY PHASE ... UNTIL THE END OF THAT PHASE" IS A LATCH
----------------------------------------------------------------------
Objective control is recomputed at phase boundaries in this engine, but not only
there (a unit withdrawn to Strategic Reserves recomputes it on the spot). The
printed text decides the region ONCE, when the phase starts, so the controller
stamps it in main.py's start-of-any-phase block and every reader asks the latch.
A phase with no stamp (a scene loaded mid-phase, a test that never ran main())
falls back to the live answer, which is what the stamp would have said.

"AT LEAST HALF" OF ZERO IS NOT A MAJORITY
-----------------------------------------
n == 0 objectives in a region puts that region OUTSIDE the matrix. Read the other
way, 0 >= 0 would put an opponent's objective-less deployment zone permanently in
the matrix, which the clause - a reward for holding ground - cannot mean. Measured
on the four shipped maps: every No Man's Land and every deployment zone holds at
least one objective, so the case is unreachable today and pinned by its suite.

THE RE-ROLL IS A TEXTBOOK ONES-OR-WHOLE SOURCE (game/reroll_scope.py): an
automatic re-roll of Hit rolls of 1 that always applies, and "you can re-roll the
Hit roll INSTEAD" while the unit is wholly within the matrix. "An attack", so
both game/shooting.py and game/fight.py read it.
"""

from types import SimpleNamespace

from game import config, detachment_gate

SETTING = "CANOPTEK_COURT_PLAYERS"
POWER_MATRIX_LABEL = "Power Matrix"

#: The battle's controller, for the one reader that has no controller in hand:
#: ai/observation.py builds a unit summary from a Squad and nothing else. Set by
#: main() each battle, like game/battle_stats.CURRENT, and None in any test or
#: harness that never ran main() - where observation() below simply reports
#: nothing.
CURRENT = None

OWN_ZONE = "own_deployment_zone"
NO_MANS_LAND = "no_mans_land"
ENEMY_ZONE = "enemy_deployment_zone"

REGION_LABELS = {
    OWN_ZONE: "your deployment zone",
    NO_MANS_LAND: "No Man's Land",
    ENEMY_ZONE: "your opponent's deployment zone",
}

#: A base resting exactly on a region edge counts as inside it - the same
#: tolerance game/deployment.py applies to "wholly within".
EDGE_TOLERANCE_IN = 1e-9


def has_detachment(player):
    return detachment_gate.has_detachment(player, SETTING)


def players_with_detachment():
    return tuple(getattr(config, SETTING, ()) or ())


# ------------------------------------------------------------------ regions

def _zones(game_state):
    return list(getattr(game_state, "deployment_zones", ()) or ())


def own_zones(zones, player):
    return [z for z in zones if getattr(z, "owner", None) == player]


def enemy_zones(zones, player):
    return [z for z in zones if getattr(z, "owner", None) not in (None, player)]


def objectives_in_no_mans_land(game_state):
    """"the objective markers within No Man's Land" - the same geometric test
    the Secondary Missions use (centre in nobody's deployment zone), asked of
    game/mission_context.py rather than written a second time."""
    from game import mission_context
    ctx = SimpleNamespace(objectives=list(getattr(game_state, "objectives", ()) or ()),
                          deployment_zones=_zones(game_state))
    return mission_context.no_mans_land_objectives(ctx)


def objectives_in_enemy_zone(game_state, player):
    """"the objective markers within your opponent's deployment zone"."""
    from game.mission_context import objective_centre
    theirs = enemy_zones(_zones(game_state), player)
    out = []
    for objective in getattr(game_state, "objectives", ()) or ():
        cx, cy = objective_centre(objective)
        if any(z.contains_point(cx, cy) for z in theirs):
            out.append(objective)
    return out


def controls_at_least_half(objectives, player):
    """"if you control at least half" - and of zero, never (module docstring)."""
    objectives = list(objectives)
    if not objectives:
        return False
    held = sum(1 for o in objectives if getattr(o, "controlled_by", None) == player)
    return held * 2 >= len(objectives)


def regions_now(game_state, player):
    """The live answer: which regions would be in the matrix if the phase
    started this instant."""
    regions = {OWN_ZONE}
    if game_state is None:
        return frozenset(regions)
    if controls_at_least_half(objectives_in_no_mans_land(game_state), player):
        regions.add(NO_MANS_LAND)
    if controls_at_least_half(objectives_in_enemy_zone(game_state, player), player):
        regions.add(ENEMY_ZONE)
    return frozenset(regions)


def model_wholly_within(model, player, regions, zones):
    """Whether this model's BASE lies wholly within the union `regions` - see
    the module docstring's table."""
    if model is None:
        return False
    x, y, r = model.x_in, model.y_in, model.radius_in
    if NO_MANS_LAND in regions and ENEMY_ZONE in regions:
        return True
    mine = own_zones(zones, player)
    theirs = enemy_zones(zones, player)
    if NO_MANS_LAND in regions:
        # Everything but the opponent's zone: the base must not reach into it.
        return bool(mine) and all(z.distance_to_point(x, y) >= r - EDGE_TOLERANCE_IN
                                  for z in theirs)
    in_own = any(z.contains_circle(x, y, r) for z in mine)
    if ENEMY_ZONE in regions:
        return in_own or any(z.contains_circle(x, y, r) for z in theirs)
    return in_own


class PowerMatrixController:
    """The per-phase latch, and the one place "wholly within" is answered.

    Held by main() and handed to ShootingController.power_matrix and
    FightController.power_matrix (both default None - no matrix, so no full
    re-roll), and to the Canoptek Court Stratagems that print "wholly within
    your army's Power Matrix" in their TARGET line.
    """

    def __init__(self, game_state=None, turn_tracker=None, game_log=None):
        self.game_state = game_state
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._latched = {}     # player -> (phase key, frozenset of regions)

    def _phase_key(self):
        tt = self.turn_tracker
        if tt is None:
            return None
        return (getattr(tt, "battle_round", None), getattr(tt, "turn_owner", None),
                getattr(tt, "phase", None))

    def zones(self):
        return _zones(self.game_state)

    def stamp_at_start_of_phase(self):
        """"At the start of any phase" - called from main.py's start-of-any-phase
        block, where objective control has just been recomputed. Stamps every
        player who fields the detachment, and says what changed."""
        key = self._phase_key()
        for player in players_with_detachment():
            regions = regions_now(self.game_state, player)
            previous = self._latched.get(player)
            self._latched[player] = (key, regions)
            if self.game_log is not None and (previous is None or previous[1] != regions):
                self.game_log.add(
                    "[power matrix] %s: %s." % (player, describe(regions)), file_only=True)

    def regions_for(self, player):
        latched = self._latched.get(player)
        if latched is not None and latched[0] == self._phase_key():
            return latched[1]
        return regions_now(self.game_state, player)

    def unit_wholly_within(self, squad):
        """"wholly within your army's Power Matrix" - every living model's base."""
        if squad is None:
            return False
        living = [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]
        if not living:
            return False
        regions = self.regions_for(squad.owner)
        zones = self.zones()
        return all(model_wholly_within(m, squad.owner, regions, zones) for m in living)


def describe(regions):
    order = (OWN_ZONE, NO_MANS_LAND, ENEMY_ZONE)
    return " + ".join(REGION_LABELS[r] for r in order if r in regions)


# ------------------------------------------------------------------ the re-roll

def is_court_unit(squad):
    """"a CRYPTEK or CANOPTEK unit from your army" - 19.03's pooled keywords,
    and an owner who fields the detachment."""
    if squad is None or not has_detachment(getattr(squad, "owner", None)):
        return False
    from game import necron_detachments
    return necron_detachments.is_cryptek_unit(squad) or necron_detachments.is_canoptek_unit(squad)


def applies(squad):
    """The automatic half: re-roll a Hit roll of 1, always."""
    return is_court_unit(squad)


def unit_wholly_within(squad, matrix):
    return matrix is not None and matrix.unit_wholly_within(squad)


def offers_full_reroll(squad, matrix):
    """The conditional half: the whole Hit roll, INSTEAD of the 1s."""
    return applies(squad) and unit_wholly_within(squad, matrix)


def observation(squad, matrix):
    """The planner's view of it: which regions are in the matrix and whether
    this unit stands wholly inside them. None for a unit the rule is not about,
    so no other army pays a key for it (the reanimation_protocols field's
    arrangement in ai/observation.py)."""
    if matrix is None or not applies(squad):
        return None
    regions = matrix.regions_for(squad.owner)
    return {
        "regions": describe(regions),
        "wholly_within": matrix.unit_wholly_within(squad),
        "note": ("wholly within the Power Matrix this unit can re-roll whole Hit rolls "
                 "(otherwise only 1s); hold half the objectives in No Man's Land or in "
                 "the enemy zone at the start of a phase to extend it there"),
    }
