"""Seer Council's "Presentiment of Dread" (1CP, Strategic Ploy).

RULE (printed, word for word):
  WHEN: "Command phase"
  TARGET: "One ASURYANI PSYKER model from your army"
  EFFECT: "Select one enemy unit within 18" of and visible to your model. That
  enemy unit must take a Battle-shock test, subtracting 1 from that test."

TWO PIECES, ONE OF THEM ALREADY BUILT
-------------------------------------
The forced test is game/battle_shock.py's start_forced_roll(), added for The
Twin Lance's Grav-inhibitor Field and reused by its Neocapacitor Shields - a
third consumer, and word for word this ability's "must take a Battle-shock
test".

The "-1 to that test" is new. It goes onto the ROLL rather than the threshold so
the log can print both the dice and what they became, and it is threaded through
start_forced_roll(penalty=...) rather than mutated onto the unit - a modifier to
one specific test is not a state the unit carries.

"WITHIN 18 INCHES OF AND VISIBLE TO YOUR MODEL" is the same select-a-target
shape as the Farseer's Guide, so it reuses game/psychic_mark.py's reasoning
about measuring centre to centre and checking line of sight from the bearer -
but not that module itself, which is about a mark that LASTS. This resolves
immediately and leaves nothing behind.

WHEN is the bare "Command phase", not "your Command phase". Read literally: the
Command phase is not shared the way the Fight phase is, so in practice only the
active player has one - but the check is on the phase, not on ownership, exactly
as printed.
"""

from game.line_of_sight import has_line_of_sight
from game.turn import PHASE_COMMAND
from game.stratagems import Stratagem
from game import strands_of_fate

PRESENTIMENT_RANGE_IN = 18.0
PRESENTIMENT_TEST_PENALTY = 1
PRESENTIMENT_CP = 1
PRESENTIMENT_NAME = "Presentiment of Dread"


class PresentimentOfDreadController:
    """Human-only in practice like the rest of the Aeldari work, but the target
    choice is an ordinary DecisionManager break point, so an AI would resolve it
    through the generic path with nothing extra here."""

    def __init__(self, stratagem_controller=None, battle_shock=None, turn_tracker=None,
                 decision_manager=None, game_log=None, all_tokens=None,
                 obstacles=None, terrain_areas=None):
        self.stratagem_controller = stratagem_controller
        self.battle_shock = battle_shock
        self.turn_tracker = turn_tracker
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.obstacles = obstacles if obstacles is not None else []
        self.terrain_areas = terrain_areas if terrain_areas is not None else []
        self._stratagem = Stratagem(
            name=PRESENTIMENT_NAME, cp_cost=PRESENTIMENT_CP, effect=self._effect,
        )
        self._pending_squad = None

    def bearers(self, squad):
        """The living ASURYANI PSYKER models in this unit. Per MODEL, because
        the TARGET clause names a model, not a unit."""
        return [m for m in getattr(squad, "models", None) or ()
                if getattr(m.profile, "psyker", False) and not m.is_dead()]

    def panel_label(self, squad):
        """The button text, for game/proactive_stratagems.py.

        Migrated onto the registry rather than kept as its own parameter
        through ActionPanel.draw()'s three-stage chain: that chain already
        carries 81 of them, and this label used to be a string literal inside
        the panel, which is what let the panel's "nothing to do here" hint
        stay unaware that a button was on offer."""
        return "%s (%d CP)" % (PRESENTIMENT_NAME, PRESENTIMENT_CP)

    def can_use(self, squad):
        if squad is None or self.stratagem_controller is None or self.battle_shock is None:
            return False
        # Seer Council only - see game/strands_of_fate.py's has_detachment().
        if not strands_of_fate.has_detachment(squad.owner):
            return False
        if self.turn_tracker is None or self.turn_tracker.phase != PHASE_COMMAND:
            return False
        if not self.bearers(squad):
            return False
        if not self.candidates(squad):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def candidates(self, squad):
        """The enemy units a bearer of this unit could pick: within 18" of and
        visible to that model."""
        out = []
        for bearer in self.bearers(squad):
            for token in self.all_tokens:
                other = getattr(token, "squad", None)
                if other is None or other.owner == squad.owner or token.is_dead():
                    continue
                if other in out:
                    continue
                dx, dy = bearer.x_in - token.x_in, bearer.y_in - token.y_in
                if (dx * dx + dy * dy) ** 0.5 > PRESENTIMENT_RANGE_IN:
                    continue
                if has_line_of_sight(bearer, token, self.obstacles, self.all_tokens,
                                     terrain_areas=self.terrain_areas):
                    out.append(other)
                    break
        return sorted(out, key=lambda s: s.name)

    def use(self, squad):
        """Spends the CP and asks which enemy unit. With exactly one candidate
        there is nothing to choose and it is taken - the same reasoning that
        makes the Falcon's Fire Support mark automatic in that case."""
        if not self.can_use(squad):
            return False
        # Rule 15.01's order: targets, then CP, then effect. The stratagem's own
        # TARGET is the psyker's unit; WHICH enemy unit it points at is part of
        # the EFFECT, so it is chosen inside _effect() below.
        self._pending_squad = squad
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _effect(self, controller, player, targets):
        squad = self._pending_squad or (targets[0] if targets else None)
        self._pending_squad = None
        if squad is None:
            return
        options = self.candidates(squad)
        if not options:
            return
        if len(options) == 1 or self.decision_manager is None:
            self._impose(options[0])
            return
        self.decision_manager.request(
            squad.owner,
            f"{squad.name}: Presentiment of Dread - which enemy unit within "
            f'{PRESENTIMENT_RANGE_IN:g}" must take a Battle-shock test at -1?',
            [(t.name, (lambda x=t: self._impose(x)), t) for t in options],
        )

    def _impose(self, target):
        if self.game_log is not None:
            self.game_log.add(
                f"Presentiment of Dread: {target.name} must take a Battle-shock test, "
                f"subtracting {PRESENTIMENT_TEST_PENALTY} from it."
            )
        self.battle_shock.start_forced_roll(
            target, PRESENTIMENT_NAME, penalty=PRESENTIMENT_TEST_PENALTY,
        )
