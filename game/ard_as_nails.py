"""Orks detachment stratagem: War Horde's 'Ard as Nails, as supplied by the
user (not a rule from the generic 40k core rulebook, so it lives in its own
module - same reasoning as game/war_horde.py for that detachment's Get Stuck
In rule and game/unbridled_carnage.py for its other stratagem).

RULE ('Ard as Nails, 1CP, War Horde Battle Tactic Stratagem):
  WHEN:   Your opponent's Shooting phase or the Fight phase, just after an
          enemy unit has selected its targets.
  TARGET: One ORKS unit from your army (excluding GROTS, MONSTER and VEHICLE
          units) that was selected as the target of one or more of the
          attacking unit's attacks.
  EFFECT: Until the end of the phase, each time an attack targets your unit,
          subtract 1 from the Wound roll.

THE EFFECT IS THE CHEAP HALF
----------------------------
"Subtract 1 from the Wound roll" against this unit is exactly the Guardian
Drone wargear item this engine already models (game/drones.py), so it is one
line in each of the two _wound_modifiers() hooks - a malus, so per the
Modifier sign convention (positive worsens) it is a +1 on the wound
THRESHOLD. Unlike the Guardian Drone it is not ranged-only: the EFFECT says
"each time an attack targets your unit", and the WHEN names the Fight phase
too, so it sits in game/fight.py's hook as well.

WHY THIS ONE DECIDES ITSELF (AND STIM INJECTORS DOES NOT)
---------------------------------------------------------
Its WHEN is the same every-enemy-target-selection trigger as Stim Injectors,
which is the trigger the user objected to being asked about ("das würde sehr
nerven"). Stim Injectors answers that with a relevance GATE and still asks.
This one is answered outright, per the user: "hier auch deterministisch",
with the condition spelled out in full - use it when

  * the unit is worth 100 points or more,
  * it still has more than half its models, and
  * the incoming attack is expected to take at least half of what is left of
    it.

(The third condition started as "would destroy it outright" and was relaxed
once measured: that version fired in 1 of 126 above-half matchups across the
two demo armies - see measure_ard_as_nails.py.)

That is a complete decision procedure, not a heuristic with a leftover
judgement call, which is what makes automating it honest rather than
presumptuous: there is nothing a player would add to it at the moment of
asking. It is also self-limiting in exactly the way the interruption
complaint needed - all three conditions have to hold at once, on top of rule
15.01's once-per-phase cap.

WHO IT DECIDES FOR
------------------
`auto_players` - main.py passes the AI's side. For anyone else the same
verdict becomes a relevance gate on a DecisionManager prompt instead (the
Stim Injectors shape), so a human running Orks keeps the choice and their CP,
and is only ever asked when all three conditions already hold. Without that
split, automating this would silently spend a human player's CP.

THE THIRD CONDITION IS A LOWER BOUND, AND THAT MATTERS
------------------------------------------------------
"Would take half of it" is game/damage_estimate.py's estimate, which models no
re-rolls, no [SUSTAINED HITS]/[LETHAL HITS]/[DEVASTATING WOUNDS] and no
cover - so it UNDERSTATES incoming damage and therefore fires less often than
the true condition would. That is the safe direction for something that
spends CP on its own: the error costs a use, never an unwanted one.

SIMPLIFICATION (documented, matching game/war_horde.py's own note): no
army-building/detachment-selection flow exists yet and War Horde is the only
Orks detachment, so there is no "is this army actually running War Horde"
check. The ORKS half of the TARGET clause IS checked, as are all three
exclusions - GROTS off the datasheet keyword line, MONSTER and VEHICLE off
the UnitProfile flags, both with rule 19.03's keyword pooling.
"""

from game.attached_units import unit_has_datasheet_keyword, unit_has_keyword
from game.damage_estimate import expected_wounds_against, models_destroyed_by
from game.squad import is_at_half_strength
from game.stratagems import Stratagem
from game.turn import PHASE_FIGHT, PHASE_SHOOTING
from game.unbridled_carnage import is_orks_unit

ARD_AS_NAILS_CP_COST = 1

# The user's own three conditions, as constants so the test and the log line
# quote the same numbers the decision uses.
MIN_POINTS = 100          # the unit's value floor, INCLUSIVE - a 100pt unit qualifies (user: "mach >= 100 nicht >100")
# How much of what is LEFT of the unit the incoming attack has to be expected
# to take. Relaxed from "would destroy it outright" at the user's instruction
# ("der ork squad muss nicht vernichtet werden sondern muss mindestens der
# hälfte seiner restlichen modelle verlieren") after that version was measured
# firing in 1 of 126 above-half matchups - see measure_ard_as_nails.py.
MIN_MODEL_LOSS_FRACTION = 0.5
ARD_AS_NAILS_WOUND_PENALTY = 1  # "subtract 1 from the Wound roll" - a malus, so a +1 on the wound THRESHOLD (this file's Modifier sign convention: positive worsens)


def ard_as_nails_wound_modifier_applies(target_squad):
    """Whether an attack against this unit currently takes the -1. Read
    straight off the unit flag so both _wound_modifiers() hooks (shooting and
    fight) can consult it without depending on the controller - same
    arrangement as Squad.stim_injectors_active."""
    return bool(getattr(target_squad, "ard_as_nails_active", False))


def is_eligible_unit(squad):
    """TARGET: "One ORKS unit from your army (excluding GROTS, MONSTER and
    VEHICLE units)".

    All four keyword tests use rule 19.03's pooling ("an attached unit has all
    of the keywords of all of its component units"), which cuts both ways and
    is meant to: a Warboss joined to a Boyz mob keeps the unit ORKS, and a
    character joined to a VEHICLE unit would not launder away the VEHICLE
    exclusion. GROTS is read off the datasheet keyword line because it is not
    one of the handful of keywords modeled as UnitProfile flags (see
    game/shooting.py's _KEYWORD_FIELDS and CLAUDE.md's Später-Liste for why
    there is no generic keyword system yet)."""
    if squad is None or not squad.models:
        return False
    if not is_orks_unit(squad):
        return False
    if unit_has_datasheet_keyword(squad, "GROTS"):
        return False
    if unit_has_keyword(squad, lambda m: getattr(m.profile, "monster", False)):
        return False
    if unit_has_keyword(squad, lambda m: getattr(m.profile, "vehicle", False)):
        return False
    return True


def alive_models(squad):
    """The models still standing - what "half its remaining models" counts."""
    return [m for m in squad.models if not m.is_dead()]


def remaining_wounds(squad):
    """Wounds still standing between this unit and destruction. Not part of
    the decision any more (see expected_models_lost() for what replaced it),
    but still the honest way to describe how much is left of a unit."""
    return sum(m.current_wounds for m in alive_models(squad) if m.current_wounds is not None)


def expected_models_lost(attacker, target, melee=False):
    """How many models the attacking unit's whole output is expected to kill.

    Wounds converted to MODELS the same way ai/observation.py's expected_kills()
    does it - through models_destroyed_by(), which spends them in rule 05.03/
    05.04 allocation order against the wounds those models actually have left -
    and capped at the models there are. Capping matters: without it, overkill
    would make a small unit look like it loses more models than it has, and the
    fraction below would be meaningless. Reading the CURRENT wounds matters
    here too: a mob that is already half dead is exactly the one this Stratagem
    is meant to save, and the printed characteristic said it was fresh.

    Values the attacker's WHOLE output against this target, which is exact for
    a normal activation (rule 10.02 sends every weapon at the one selected
    target) and an over-estimate under Split Fire, where only some weapons are
    assigned here - the same approximation, and the same direction of error, as
    StimInjectorsController's own expected_wounds_saved()."""
    incoming = expected_wounds_against(attacker, target, melee=melee)
    if incoming is None:
        return 0.0
    standing = alive_models(target)
    if not standing:
        return 0.0
    return min(len(standing), models_destroyed_by(target, incoming))


def attack_would_cripple(attacker, target, melee=False):
    """Whether the attack is expected to take at least half of what is left of
    the unit - the user's third condition, relaxed from "would destroy it"
    after that turned out to fire in 1 of 126 matchups (measured; see
    measure_ard_as_nails.py).

    Judged in MODELS rather than wounds, per the wording ("mindestens der
    hälfte seiner restlichen modelle"). For a homogeneous unit the two agree;
    for an attached unit (19.01) they do not, and models is the more honest
    reading of what a mob has lost. See the module docstring on why this
    estimate being a LOWER bound is the safe direction."""
    standing = alive_models(target)
    if not standing:
        return False
    return expected_models_lost(attacker, target, melee=melee) >= len(standing) * MIN_MODEL_LOSS_FRACTION


def is_worth_using(attacker, target, melee=False):
    """The user's three conditions, as one predicate: a valuable unit, still
    healthy, about to be gutted. Used BOTH as the AI's deterministic verdict
    and as the relevance gate on a human's prompt, so the two can never drift
    apart.

    `points` is None for a unit whose faction has no published points list
    (see game/factions/points.py). Treated as "does not qualify" rather than
    guessed at: the condition is explicitly about the unit's VALUE, and an
    unpriced unit has no value to compare. Both demo armies are priced, so
    this only affects a future faction added without its list."""
    if target.points is None or target.points < MIN_POINTS:
        return False
    if is_at_half_strength(target):
        return False  # "mehr als die hälfte ihrer modelle" - at half or below fails
    return attack_would_cripple(attacker, target, melee=melee)


class ArdAsNailsController:
    """WHEN/TARGET bookkeeping, the "until the end of the phase" grant, and
    the deterministic decision described in the module docstring.

    `auto_players` is the set of players whose answer this controller gives
    itself (main.py passes the AI's side). Anyone else gets a DecisionManager
    prompt, gated on the same verdict."""

    def __init__(
        self, stratagem_controller, decision_manager=None, turn_tracker=None, game_log=None,
        auto_players=(),
    ):
        self.stratagem_controller = stratagem_controller
        self.decision_manager = decision_manager
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self.auto_players = set(auto_players)
        self._stratagem = Stratagem(
            name="'Ard as Nails", cp_cost=ARD_AS_NAILS_CP_COST, effect=self._grant,
        )
        # (attacking squad, target squad) pairs already handled for the current
        # attack, so Split Fire's per-model assignment step - which reaches the
        # "targets selected" hook once per assignment - acts once per target
        # rather than once per weapon. Cleared by reset_phase(). Same field and
        # same reason as StimInjectorsController's.
        self._handled_this_phase = set()

    def reset_phase(self, squads=()):
        """End of phase: the grant expires ("until the end of the phase") and
        the per-attack de-duplication starts over. Both halves live here, not
        in main.py's phase loop, so "when does this stop applying" has exactly
        one answer and is testable without the game loop - same shape as
        StimInjectorsController.reset_phase(). Callers pass every squad on the
        board: the Fight phase is shared (12.04), so either army can be holding
        a grant when a phase ends."""
        self._handled_this_phase = set()
        for squad in squads:
            squad.ard_as_nails_active = False

    def can_use(self, attacker, target):
        """The printed WHEN/TARGET clauses plus rule 15.01 - everything that
        makes the stratagem LEGAL here, with no judgement about whether it is
        worth it (that is is_worth_using())."""
        if attacker is None or target is None:
            return False
        # WHEN: "your opponent's Shooting phase or the Fight phase". A Snap
        # Shot from Fire Overwatch (15.08/15.09) selects a target through the
        # same hook but happens at the end of the opponent's MOVEMENT phase,
        # so the WHEN does not cover it. Note the clause says "the Fight
        # phase", not "your opponent's" - both players' units fight within one
        # shared phase (12.04's alternation), the reading
        # game/counteroffensive.py's docstring spells out.
        if self.turn_tracker is not None and self.turn_tracker.phase not in (PHASE_SHOOTING, PHASE_FIGHT):
            return False
        if target.owner == attacker.owner:
            return False  # "an ENEMY unit has selected its targets"
        if all(m.is_dead() for m in target.models):
            return False
        if getattr(target, "ard_as_nails_active", False):
            return False  # already up on this unit - nothing left to buy
        if not is_eligible_unit(target):
            return False
        # Rule 15.01's once-per-phase/one-target-per-phase, CP, and 01.07's
        # battle-shock block.
        return self.stratagem_controller.can_use(target.owner, self._stratagem, [target])

    def maybe_offer(self, attacker, target, melee=False):
        """Called at rule 10.02's "select targets" step (and the Fight phase's
        equivalent) with the attacking unit and one unit it just selected.
        Returns True if this actually did something - used the stratagem, or
        opened a prompt.

        Named to match StimInjectorsController.maybe_offer(), since both are
        entries in the same target_reactions list that game/shooting.py and
        game/fight.py iterate."""
        key = (id(attacker), id(target))
        if key in self._handled_this_phase:
            return False
        if not self.can_use(attacker, target):
            return False
        if not is_worth_using(attacker, target, melee=melee):
            return False  # deliberately NOT memoised - see below
        # Only memoised once the verdict said yes: a "no" can legitimately turn
        # into a "yes" for the same pair (Split Fire assigns more weapons to
        # the same target one at a time, so the expected damage this sees only
        # grows), and re-deriving it is pure arithmetic with no API call and no
        # line-of-sight sweep.
        self._handled_this_phase.add(key)

        if target.owner in self.auto_players:
            return self.stratagem_controller.use(target.owner, self._stratagem, [target])
        if self.decision_manager is None:
            return False
        self.decision_manager.request(
            target.owner,
            f"'Ard as Nails ({ARD_AS_NAILS_CP_COST} CP): {attacker.name} has targeted {target.name} "
            f"({target.points} pts, above half strength) and is expected to kill "
            f"{expected_models_lost(attacker, target, melee=melee):.1f} of its "
            f"{len(alive_models(target))} remaining models. "
            f"Subtract 1 from the Wound roll against it until the end of the phase.",
            [
                (f"Use 'Ard as Nails ({ARD_AS_NAILS_CP_COST} CP)",
                 lambda: self.stratagem_controller.use(target.owner, self._stratagem, [target])),
                ("Decline", None),
            ],
            is_stratagem=True,
        )
        return True

    def _grant(self, controller, player, targets):
        squad = targets[0]
        squad.ard_as_nails_active = True
        if self.game_log is not None:
            self.game_log.add(
                f"{player}: 'Ard as Nails - subtract 1 from the Wound roll against {squad.name} "
                "until the end of the phase."
            )
