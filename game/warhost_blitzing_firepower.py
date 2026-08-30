"""Warhost Stratagem: Blitzing Firepower (1CP, Battle Tactic).

RULE (verbatim, rules/aeldari/detachments/Warhost.md):
  WHEN:   Your Shooting phase.
  TARGET: One ASURYANI unit from your army that has not been selected to shoot
          this phase.
  EFFECT: Until the end of the phase, ranged weapons equipped by models in your
          unit have the [SUSTAINED HITS 1] ability while targeting an enemy
          unit within 12". If such a weapon already has that ability, until the
          end of the phase, each time an attack is made with that weapon, an
          unmodified Hit roll of 5+ scores a Critical Hit.
  RESTRICTIONS: none printed.

TWO CLAUSES THAT NEVER BOTH APPLY TO ONE WEAPON, which is the whole design: a
gun without [SUSTAINED HITS] gains it, a gun that has it gets better crits
instead. So they are two separate reads at two separate seams, not one effect
with a branch.

CLAUSE ONE IS BLADESTORM WITH A FIXED DISTANCE. game/bladestorm.py is the same
sentence with "within half range" where this says 'within 12"', so this takes
that module's shape exactly: a per-group adjuster in the chain, on a
copy.copy(), granting rather than overwriting - a weapon printing
[SUSTAINED HITS 2] keeps its 2, and two sources never add up. The distance is
measured the way every other distance in that chain is: once per weapon group,
true if ANY attacking model is within 12" of ANY living model of the target.

CLAUSE TWO NEEDED THE CRIT THRESHOLD TO KNOW WHICH WEAPON. crit_hit_threshold()
took the attacking MODEL, because every source before this one was a property
of the model or its unit. This one is a property of the WEAPON - two guns on
one model can differ - so that function grew an optional `weapon=`, the same
shape `target_squad=` and `hit_threshold=` already have there, and the three
Shooting-phase call sites pass it. Every other caller keeps its behaviour.

"ALREADY HAS THAT ABILITY" IS JUDGED ON THE PRINTED PROFILE - A DECISION, and
the alternative is defensible. Read against the weapon as it arrives in the
adjuster chain, a Dire Avenger catapult inside half range would count as
"already having" [SUSTAINED HITS] because Bladestorm just granted it, and the
answer would then depend on which adjuster ran first. Judged on what the
datasheet prints, the answer is the same wherever this sits in the chain. The
narrower reading is also the one that cannot silently widen: it never turns a
granted ability into a second, better grant. Stated here rather than left as an
accident of ordering, and pinned in the test.

BOTH HALVES ARE SHOOTING-ONLY - "ranged weapons", and a WHEN that only reaches
the Shooting phase. game/fight.py never imports this module, checked as
negative space.

THE AI DECLINES (standing Aeldari instruction).
"""
import copy

from game import aeldari_detachments, martial_grace
from game.squad import edge_distance
from game.stratagems import Stratagem
from game.turn import PHASE_SHOOTING
from game.weapons import RANGED

BLITZING_FIREPOWER_NAME = "Blitzing Firepower"
BLITZING_FIREPOWER_CP = 1

#: "have the [SUSTAINED HITS 1] ability".
BLITZING_FIREPOWER_SUSTAINED_HITS = 1

#: 'while targeting an enemy unit within 12"'.
BLITZING_FIREPOWER_RANGE_IN = 12.0

#: "an unmodified Hit roll of 5+ scores a Critical Hit".
BLITZING_FIREPOWER_CRIT_HIT_THRESHOLD = 5


def is_active(squad):
    return bool(getattr(squad, "blitzing_firepower_active", False))


def eligible_unit(squad):
    """"One ASURYANI unit from your army"."""
    if squad is None or not martial_grace.has_detachment(getattr(squad, "owner", None)):
        return False
    return aeldari_detachments.is_asuryani_unit(squad)


def _prints_sustained_hits(weapon):
    """"If such a weapon ALREADY has that ability" - judged on the PRINTED
    profile. See the module docstring: the alternative reading makes the answer
    depend on adjuster order."""
    if weapon is None:
        return False
    printed = type(weapon)
    return bool(getattr(printed, "sustained_hits", 0)
                or getattr(printed, "sustained_hits_notation", None))


def adjusted_weapon(weapon, pairs, target_squad):
    """CLAUSE ONE: [SUSTAINED HITS 1] within 12".

    Takes the group's (shooter, weapon) `pairs` like every other adjuster in
    the chain, so the distance is measured from the models actually shooting."""
    if weapon is None or getattr(weapon, "weapon_type", None) != RANGED:
        return weapon
    if not pairs or target_squad is None:
        return weapon
    shooter = pairs[0][0]
    if not is_active(getattr(shooter, "squad", None)):
        return weapon
    # A weapon that already prints the ability takes clause TWO instead, and
    # granting is never a downgrade in any case.
    if BLITZING_FIREPOWER_SUSTAINED_HITS <= weapon.sustained_hits:
        return weapon
    in_range = any(
        edge_distance(model, defender) <= BLITZING_FIREPOWER_RANGE_IN
        for model, _ in pairs
        for defender in target_squad.models
        if not defender.is_dead()
    )
    if not in_range:
        return weapon
    boosted = copy.copy(weapon)
    boosted.sustained_hits = BLITZING_FIREPOWER_SUSTAINED_HITS
    return boosted


def crit_hit_threshold_for(model, weapon):
    """CLAUSE TWO: 5+ crits, for a weapon that already prints
    [SUSTAINED HITS]. Read by game/crit_hit.py's fold; None means "no
    opinion", which is what every other source there returns."""
    if model is None or weapon is None:
        return None
    if getattr(weapon, "weapon_type", None) != RANGED:
        return None
    if not is_active(getattr(model, "squad", None)):
        return None
    if not _prints_sustained_hits(weapon):
        return None
    return BLITZING_FIREPOWER_CRIT_HIT_THRESHOLD


def reset_phase(squads=()):
    for squad in squads or ():
        if squad is not None:
            squad.blitzing_firepower_active = False


class BlitzingFirepowerController:
    """A Shooting-phase panel button."""

    def __init__(self, stratagem_controller, shooting_controller=None,
                 turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.shooting_controller = shooting_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._stratagem = Stratagem(
            name=BLITZING_FIREPOWER_NAME, cp_cost=BLITZING_FIREPOWER_CP,
            effect=self._grant,
        )

    def panel_label(self, squad):
        return ('%s (%d CP) - [SUSTAINED HITS 1] within %g" this phase'
                % (BLITZING_FIREPOWER_NAME, BLITZING_FIREPOWER_CP,
                   BLITZING_FIREPOWER_RANGE_IN))

    def can_use(self, squad):
        if squad is None or self.stratagem_controller is None or self.turn_tracker is None:
            return False
        if self.turn_tracker.phase != PHASE_SHOOTING:
            return False
        if squad.owner != self.turn_tracker.active_player:
            return False               # "YOUR Shooting phase"
        if is_active(squad):
            return False
        if not eligible_unit(squad):
            return False
        if self.shooting_controller is not None \
                and self.shooting_controller.active_squad is squad:
            return False               # "has not been selected to shoot"
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            squad.blitzing_firepower_active = True
            if self.game_log is not None:
                self.game_log.add(
                    '%s: %s gains [SUSTAINED HITS %d] within %g" this phase, and '
                    "guns that already had it crit on %d+."
                    % (BLITZING_FIREPOWER_NAME, squad.name,
                       BLITZING_FIREPOWER_SUSTAINED_HITS, BLITZING_FIREPOWER_RANGE_IN,
                       BLITZING_FIREPOWER_CRIT_HIT_THRESHOLD))
