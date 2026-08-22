"""Orks detachment stratagem: War Horde's Unbridled Carnage, as supplied by
the user (not a rule from the generic 40k core rulebook, so it lives in its
own module - same reasoning as game/war_horde.py for that detachment's Get
Stuck In rule, and as game/arrokon_protocol.py for the T'au side).

RULE (Unbridled Carnage, 1CP, War Horde Battle Tactic Stratagem):
  WHEN:   Fight phase.
  TARGET: One ORKS unit from your army that has not been selected to fight
          this phase.
  EFFECT: Until the end of the phase, each time a model in your unit makes a
          melee attack, an unmodified hit roll of 5+ scores a Critical Hit.

WHAT IT ACTUALLY CHANGES
------------------------
Exactly one number: the CRITICAL threshold of the hit roll, 6 -> 5. Rule
05.02's default already lives in game/shooting.py's _resolve_roll() as its
`crit_threshold` parameter (rule 24.03's [ANTI-X Y+] uses the same parameter
on the WOUND roll), and it is compared against the RAW die, which is exactly
what "unmodified hit roll of 5+" asks for - a -1 to hit still misses on a 4
but a natural 5 is still a Critical Hit.

Why that is worth 1 CP here rather than being a curiosity: War Horde's own
Get Stuck In (game/war_horde.py) gives every Orks melee weapon [SUSTAINED
HITS 1], and rule 24.36 turns each Critical Hit into an extra hit. Doubling
the crit rate on an army-wide [SUSTAINED HITS] is where the "carnage" comes
from; [LETHAL HITS] (24.23) would ride along the same way if an Ork weapon
ever printed it.

MELEE ONLY, AND WHY THAT NEEDS NO EXTRA CHECK
---------------------------------------------
The EFFECT says "makes a melee attack", and the grant is read only from
game/fight.py's hit step, so a ranged attack can never see it. It is also
cleared on every phase change (see UnbridledCarnageController.reset_phase(),
called from main.py's advance_turn_phase() alongside StratagemController.
reset_phase()), so the "until the end of the phase" duration cannot leak into
a later Shooting phase either. Both halves hold independently - same
belt-and-braces arrangement as The Arro'kon Protocol's shooting-only note.

SIMPLIFICATION (documented, matching game/war_horde.py's own note): this
engine has no army-building/detachment-selection flow yet (see CLAUDE.md's
Später-Liste) and War Horde is currently the only Orks detachment, so there
is no "is this army actually running War Horde" check - the stratagem is
available to any ORKS unit, exactly as Get Stuck In already applies
unconditionally to any model with the `orks` UnitProfile flag. The ORKS half
of the TARGET clause IS checked, via is_orks_unit() below.
"""

from game.stratagems import Stratagem
from game.turn import PHASE_FIGHT

UNBRIDLED_CARNAGE_CP_COST = 1

# Rule 05.02's default: an unmodified 6 is always a Critical Hit. This
# stratagem lowers that to 5 for the target unit's melee attacks.
DEFAULT_CRIT_HIT_THRESHOLD = 6
UNBRIDLED_CARNAGE_CRIT_HIT_THRESHOLD = 5


def is_orks_unit(squad):
    """TARGET's "One ORKS unit" - true if ANY model in the unit is an Orks
    model.

    any(), not all(), for rule 19.03 (Keywords in Attached Units): "an
    attached unit has all of the keywords of all of its component units", so
    a Boyz mob with a Warboss joined is still an ORKS unit. For an ordinary
    unit every model shares the flag anyway, so the two readings only differ
    once a squad actually mixes profiles. Same shape and same reasoning as
    game/shooting.py's _unit_has_keyword()."""
    if squad is None:
        return False
    return any(getattr(m.profile, "orks", False) for m in squad.models)


# crit_hit_threshold() used to live here, while this stratagem was the
# only source that could lower the melee crit threshold. It now folds two
# factions' sources together and lives in game/crit_hit.py - see that
# module's docstring. The thresholds themselves are defined there.


class UnbridledCarnageController:
    """WHEN/TARGET bookkeeping plus the "until the end of the phase" grant.
    The EFFECT itself is crit_hit_threshold() above, read by
    game/fight.py's hit step.

    Proactive, like The Arro'kon Protocol and unlike Stim Injectors: the
    active player buys it at a moment of their own choosing, so there is no
    interruption to gate and no DecisionManager hook - a plain ActionPanel
    button for a human, and a deterministic call for the AI (see
    ai/agent_driver.py's _unbridled_carnage_verdict(), per the user: "ki soll
    diese deterministisch einsetzen").

    What can_use() adds beyond the printed clauses is a CERTAINTY check, not
    an estimate: a unit that is not eligible to fight at all this phase can
    never make a melee attack, so the grant would buy literally nothing.
    Same kind of honest eligibility as ArrokonProtocolController's "nothing
    in range is big enough" refusal and game/overwatch.py's
    _eligible_squads(). Whether the CP is WORTH spending is a tactical
    judgement and deliberately not decided here - a human may buy it
    whenever the rules allow."""

    def __init__(self, stratagem_controller, fight_controller=None, turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.fight_controller = fight_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._stratagem = Stratagem(
            name="Unbridled Carnage", cp_cost=UNBRIDLED_CARNAGE_CP_COST, effect=self._grant,
        )

    def reset_phase(self, squads=()):
        """End of phase: the grant expires ("until the end of the phase").

        Lives here rather than in main.py's phase loop so "when does this
        stratagem stop applying" has exactly one answer, and so it is
        testable without standing up the whole game loop - same shape as
        ArrokonProtocolController.reset_phase()/StimInjectorsController.
        reset_phase(). Callers pass every squad on the board; the Fight phase
        is shared (12.04), so either army can be holding a grant when a phase
        ends."""
        for squad in squads:
            squad.unbridled_carnage_active = False

    def can_use(self, squad):
        if squad is None or self.fight_controller is None:
            return False
        if self.turn_tracker is not None and self.turn_tracker.phase != PHASE_FIGHT:
            return False  # WHEN: "Fight phase"
        # Deliberately NOT gated on whose turn it is. Unlike The Arro'kon
        # Protocol's "your Shooting phase", this stratagem's WHEN is the bare
        # "Fight phase" - which is shared, alternating between both players
        # (rule 12.04), the same reading game/counteroffensive.py spells out
        # for its own WHEN.
        if getattr(squad, "unbridled_carnage_active", False):
            return False  # already up on this unit - nothing left to buy
        if not is_orks_unit(squad):
            return False
        # TARGET: "has not been selected to fight this phase". fought_squad_ids
        # carries that for a unit that has finished; a unit MID-activation has
        # been selected but does not land in that set until it finishes - the
        # same gap ArrokonProtocolController closes with its active_squad
        # check.
        if squad in self.fight_controller.fought_squad_ids:
            return False
        if self.fight_controller.fighting_squad is squad:
            return False
        # Rule 15.01's once-per-phase/one-target-per-phase, CP, and 01.07's
        # battle-shock block. Checked BEFORE the eligibility probe below only
        # for cost: these are set lookups, while is_eligible_to_fight() runs a
        # real Engagement Range sweep, and this is re-asked every frame the AI
        # spends in the Fight step's selection state.
        if not self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad]):
            return False
        # Certainty check (see the class docstring): a unit that cannot fight
        # this phase cannot make a melee attack, so the grant buys nothing.
        return self.fight_controller.is_eligible_to_fight(squad)

    def use(self, squad):
        """Spends the CP and puts the grant up. TARGET is trivial (always this
        one unit), so there is no separate selection step to cancel out of -
        the CP is committed right here, exactly like CrushingImpactController's
        own start() and ArrokonProtocolController.use()."""
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _grant(self, controller, player, targets):
        squad = targets[0]
        squad.unbridled_carnage_active = True
        if self.game_log is not None:
            self.game_log.add(
                f"{player}: Unbridled Carnage - {squad.name}'s melee attacks score a Critical Hit on an "
                "unmodified hit roll of 5+ until the end of the phase."
            )
