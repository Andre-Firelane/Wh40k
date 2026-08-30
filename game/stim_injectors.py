"""T'au Empire detachment stratagem: Retaliation Cadre's Stim Injectors, as
supplied by the user (not a rule from the generic 40k core rulebook, so it
lives in its own module - same reasoning as game/retaliation_cadre.py for that
detachment's Bonded Heroes rule).

RULE (Stim Injectors, 1CP, Retaliation Cadre Wargear Stratagem):
  WHEN:   Your opponent's Shooting phase or the Fight phase, just after an
          enemy unit has selected its targets.
  TARGET: One T'AU EMPIRE BATTLESUIT unit from your army that was selected as
          the target of one or more of the attacking unit's attacks.
  EFFECT: Until the end of the phase, models in your unit have the Feel No
          Pain 6+ ability.

WHY THERE IS A RELEVANCE GATE
-----------------------------
This is the first stratagem in the engine whose WHEN fires on *every enemy
target selection*, rather than at a phase boundary (Rapid Ingress, Fire
Overwatch, Heroic Intervention) or after a whole activation (Counteroffensive).
Left ungated it would interrupt the game every single time the opponent shoots
or fights - the user's own objection ("das würde sehr nerven"), and the reason
the feature was designed before it was built.

Two things already keep the count down without any new machinery: rule 15.01's
once-per-phase cap is enforced by StratagemController for free (so a phase can
produce at most one *accepted* offer), and the TARGET clause is narrow (only a
BATTLESUIT unit, only when it was actually selected as a target). What neither
of those removes is the offer that is legal but pointless - a Kroot squad
plinking at a Ghostkeel, where a 6+ Feel No Pain is expected to save a fraction
of a wound for 1 CP.

So this asks only when the answer is not already obvious. That is not a new
principle here; it is the same fix game/overwatch.py's _eligible_squads()
already carries, from a real user report about the same feeling:

    "this used to just check 'has any ranged weapon at all', so units clear
     across the board with nothing whatsoever in range were offered the
     stratagem every single time"

The answer there was to make eligibility honest, not to add a per-unit opt-in
toggle. Same here. A per-unit "ask me about this one" toggle was considered
with the user and deliberately deferred: it does not scale past one stratagem
(it would have to become per-unit-per-stratagem, or degrade into "ask me about
everything for this unit"), and it needs upkeep a player forgets mid-game. It
remains the right second step if the measured prompt count is still annoying -
this gate is the cheap half that costs the player no bookkeeping at all.

The gate is deliberately a floor on the EXPECTED BENEFIT, not on the danger:
what matters is whether the 6+ actually buys anything, and a huge incoming
attack against a unit that is about to die anyway buys just as little as a
tiny one. See MIN_EXPECTED_WOUNDS_SAVED for how the threshold was picked.

The prompt itself carries the numbers rather than asking a bare yes/no, for
the same reason _matchup_hint() and the charge odds do (see CLAUDE.md): a
question you can answer reflexively is not the one that grates. Note the
DIRECTION of the gate's error - it can only suppress offers, never invent
them, so a mis-set threshold costs a marginal option, never a legal one that
mattered.

DETACHMENT GATE
---------------
The T'AU EMPIRE half of the TARGET clause, and "from your army", are checked
through game/retaliation_cadre.py's stratagem_target_ok() - the shared
predicate all six of this detachment's Stratagems use, in the same shape as
game/awakened_dynasty.py's and game/death_lords_chosen.py's.

This module used to say the opposite: that the check was skipped because
"Retaliation Cadre is currently the only detachment that exists". That
assumption expired the moment a T'au army could be a Kauyon or Mont'ka one
instead, and in a T'au mirror match it was wrong for both players at once.

The BATTLESUIT half
IS checked, and via rule 19.03's keyword pooling, so an attached unit (19.01)
of Crisis Battlesuits plus a Commander qualifies as one unit.
"""

from game.damage_estimate import expected_wounds_against
# Shared with this detachment's other stratagem (The Arro'kon Protocol), so
# it lives in the detachment module both belong to - re-exported here under
# its original name, which is where every existing caller imports it from.
from game.retaliation_cadre import is_battlesuit_unit, stratagem_target_ok
from game.stratagems import Stratagem
from game.thresholds import parse_threshold
from game.turn import PHASE_FIGHT, PHASE_SHOOTING

STIM_INJECTORS_CP_COST = 1
STIM_INJECTORS_FEEL_NO_PAIN = "6+"

# A Feel No Pain 6+ ignores one wound in six, so the expected benefit of this
# stratagem is (wounds the attack is expected to strip) / 6. This is the floor
# on that benefit, in wounds, below which the offer is suppressed entirely.
#
# Measured rather than guessed - see measure_stim_injectors_gate.py, which
# prints everything below. Honest about what the measurement showed: the
# distribution across all 152 attacker-vs-BATTLESUIT matchups in the two demo
# armies is CONTINUOUS, not bimodal, so there is no natural empty gap to drop
# the line into (the nearest values either side of it are 0.247 and 0.278) and
# this is a judgement call, not a discovered constant. What the measurement
# does establish is that the call is a safe one:
#
#   * it suppresses 70% of matchups and keeps 30%, and every BATTLESUIT unit
#     in the army can still be protected - 14/38 of the attacks against the
#     Stealth Battlesuits and the Coldstar Commander, 13/38 against the Crisis
#     team, 4/38 against the Ghostkeel. The Ghostkeel being rarest is the gate
#     working, not failing: it is the toughest unit, so a 6+ genuinely does
#     save less against most of what shoots it.
#   * the error is one-directional. The gate can only ever SUPPRESS an offer,
#     never invent one, so setting it too high costs a marginal option and
#     never a legal one that mattered.
#   * the estimate it thresholds is a LOWER BOUND on the stratagem's real
#     value, which is why the line is this low rather than up at the ~0.5 a
#     Command Re-roll (also 1 CP) typically swings. The grant lasts "until the
#     end of the phase", so it also mitigates every LATER attack on that unit
#     in the same phase - none of which is knowable at the moment the question
#     has to be asked.
MIN_EXPECTED_WOUNDS_SAVED = 0.25


def stim_injectors_feel_no_pain(model):
    """This model's Feel No Pain threshold from an active Stim Injectors, or
    "-" if the stratagem is not currently up on its unit.

    Read straight off the unit flag rather than through the controller, so
    game/feel_no_pain.py can consult it without depending on anything heavy -
    and so the grant reaches every damage source uniformly (see
    Squad.stim_injectors_active's own note)."""
    squad = getattr(model, "squad", None)
    if squad is None or not getattr(squad, "stim_injectors_active", False):
        return "-"
    return STIM_INJECTORS_FEEL_NO_PAIN


def _already_as_good(squad):
    """True if every model already has a Feel No Pain at least this good, in
    which case the stratagem buys literally nothing and should not be offered.
    Distinct from the relevance gate below: this one is certainty, not
    estimation."""
    granted = parse_threshold(STIM_INJECTORS_FEEL_NO_PAIN)
    for model in squad.models:
        if model.is_dead():
            continue
        own = parse_threshold(model.profile.feel_no_pain)
        if own is None or own > granted:
            return False
    return bool(squad.models)


def expected_wounds_saved(attacker, target, melee=False):
    """Wounds the 6+ is expected to ignore if this stratagem is used against
    this attack. The number the gate thresholds and the prompt quotes.

    Inherits every approximation of game/damage_estimate.py (no re-rolls, no
    [SUSTAINED HITS]/[DEVASTATING WOUNDS], no cover, no per-weapon range
    filtering). One further approximation of its own: it values the attacker's
    WHOLE output against this target, which is exact for a normal activation
    (rule 10.02 sends every weapon at the one selected target) and an
    over-estimate under Split Fire, where only some of the unit's weapons are
    assigned here. Over-estimating errs toward asking, which is the safe
    direction for a gate that can only suppress offers."""
    incoming = expected_wounds_against(attacker, target, melee=melee)
    if incoming is None:
        return 0.0
    return incoming / 6.0


class StimInjectorsController:
    def __init__(self, stratagem_controller, decision_manager=None, turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.decision_manager = decision_manager
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._stratagem = Stratagem(
            name="Stim Injectors", cp_cost=STIM_INJECTORS_CP_COST, effect=self._grant,
        )
        # (attacking squad, target squad) pairs already offered for the current
        # attack, so Split Fire's per-model assignment step - which reaches the
        # "targets selected" hook once per assignment - asks once per target
        # rather than once per weapon. Cleared by reset_phase().
        self._offered_this_phase = set()

    def reset_phase(self, squads=()):
        """End of phase: the grant expires ("until the end of the phase") and
        the per-attack de-duplication starts over.

        Both halves live here rather than in main.py's phase loop so that "when
        does this stratagem stop applying" has exactly one answer, and so it is
        testable without standing up the whole game loop. Callers pass every
        squad on the board - the Fight phase is shared (12.04), so either army
        can be holding the grant when a phase ends."""
        self._offered_this_phase = set()
        for squad in squads:
            squad.stim_injectors_active = False

    def can_offer(self, attacker, target, melee=False):
        """Every condition of the WHEN/TARGET clauses plus the relevance gate,
        as one predicate - so the offer path and the tests ask the same
        question."""
        if attacker is None or target is None or self.decision_manager is None:
            return False
        # WHEN: "your opponent's Shooting phase or the Fight phase". Snap
        # Shooting from Fire Overwatch (15.08/15.09) also selects a target
        # through the same hook, but it happens at the end of the opponent's
        # MOVEMENT phase, so the WHEN does not cover it. Note the clause says
        # "the Fight phase", not "your opponent's" - both players' units fight
        # within one shared phase (12.04's alternation), the same reading
        # game/counteroffensive.py's docstring spells out.
        if self.turn_tracker is not None and self.turn_tracker.phase not in (PHASE_SHOOTING, PHASE_FIGHT):
            return False
        if target.owner == attacker.owner:
            return False  # "an ENEMY unit has selected its targets"
        if not target.models or all(m.is_dead() for m in target.models):
            return False
        if not stratagem_target_ok(target):
            return False
        if not is_battlesuit_unit(target):
            return False
        if target.stim_injectors_active or _already_as_good(target):
            return False  # nothing left to gain
        if not self.stratagem_controller.can_use(target.owner, self._stratagem, [target]):
            return False  # rule 15.01's once-per-phase/one-target-per-phase, CP, and 01.07's battle-shock block
        return expected_wounds_saved(attacker, target, melee=melee) >= MIN_EXPECTED_WOUNDS_SAVED

    def maybe_offer(self, attacker, target, melee=False):
        """Called at rule 10.02's "select targets" step (and the Fight phase's
        equivalent) with the attacking unit and one unit it just selected.
        Returns True if an offer was actually opened.

        Fire-and-forget: DecisionManager is a queue and main.py's event loop
        gives a pending decision priority over every board click, so the
        attacker physically cannot resolve an attack before the defender has
        answered - no completion callback is needed here, unlike
        game/stealth_drones.py, which has to hand a resolved damage amount
        back to its caller."""
        key = (id(attacker), id(target))
        if key in self._offered_this_phase or not self.can_offer(attacker, target, melee=melee):
            return False
        self._offered_this_phase.add(key)

        saved = expected_wounds_saved(attacker, target, melee=melee)
        self.decision_manager.request(
            target.owner,
            f"Stim Injectors ({STIM_INJECTORS_CP_COST} CP): {attacker.name} has targeted {target.name}. "
            f"Feel No Pain {STIM_INJECTORS_FEEL_NO_PAIN} until the end of the phase - "
            f"expected to ignore ~{saved:.1f} wounds of this attack.",
            [
                (f"Use Stim Injectors ({STIM_INJECTORS_CP_COST} CP)",
                 lambda: self.stratagem_controller.use(target.owner, self._stratagem, [target])),
                ("Decline", None),
            ],
            is_stratagem=True,
        )
        return True

    def _grant(self, controller, player, targets):
        squad = targets[0]
        squad.stim_injectors_active = True
        if self.game_log is not None:
            self.game_log.add(
                f"{player}: Stim Injectors - {squad.name} has Feel No Pain "
                f"{STIM_INJECTORS_FEEL_NO_PAIN} until the end of the phase."
            )
