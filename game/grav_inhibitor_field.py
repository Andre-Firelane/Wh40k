"""T'au Empire detachment stratagem: Retaliation Cadre's Grav-Inhibitor Field,
as supplied by the user (not a rule from the generic 40k core rulebook, so it
lives in its own module - same reasoning as game/retaliation_cadre.py for that
detachment's Bonded Heroes rule, and its four sibling stratagems in
game/stim_injectors.py, game/arrokon_protocol.py, game/shortened_blade.py and
game/torchstar_gambit.py).

RULE (Grav-Inhibitor Field, 1CP, Retaliation Cadre Strategic Ploy Stratagem):
  WHEN:   Your opponent's Charge phase, just after an enemy unit has declared
          a charge.
  TARGET: One T'AU EMPIRE BATTLESUIT unit from your army that was selected as
          a target of that charge.
  EFFECT: That enemy unit must immediately take a Battle-shock test, and you
          must roll one D6 for each model in that enemy unit: for each 6,
          that enemy unit suffers 1 mortal wound.

THE TIMING, WHICH IS THE WHOLE DIFFICULTY

"Just after an enemy unit has declared a charge" is a real point in the
sequence, not a phase boundary: the targets are locked in and no model has
moved yet. ChargeController.begin_charge_move() is exactly that point, so
that is where the hook (on_charge_declared) lives.

The charge move is DEFERRED behind this rather than started alongside it. It
has to be: the effect rolls dice, and DiceManager holds one pending roll at a
time, so a charge move opened first would sit half-started underneath two
rolls the player must click through - and if those mortal wounds destroy the
charging unit, that half-started move is on a unit that no longer exists.
Deferring costs one callback (ChargeController._start_declared_move) and
removes the whole class of half-state.

The effect itself is two dice steps in sequence, for the same reason
explosives.py sequences its own: one pending roll at a time.
  1. the Battle-Shock test, run through the real BattleShockController so
     01.07's outcome (and its logging) has exactly one implementation;
  2. one D6 per model, each 6 a mortal wound, allocated through the same
     MortalWoundAllocationSession every other mortal-wound source uses -
     which is what makes rule 06.02's "the defending player chooses" work
     here without new code.
Note who "the defending player" is for step 2: the mortal wounds land on the
CHARGING unit, so the choice belongs to the player being reacted to, not the
one who spent the CP. turn_tracker.set_active() flips for exactly that, the
same way ExplosivesController already does it.

WHY THERE IS NO RELEVANCE GATE, UNLIKE STIM INJECTORS

Its sibling Stim Injectors fires on every enemy target selection and needed a
threshold to keep from interrupting the game. This trigger is far rarer (a
charge declared against one of your BATTLESUIT units) and rule 15.01's
once-per-phase cap applies on top, so the printed clauses are the whole
eligibility check. The prompt still carries the numbers - how many D6 and the
expected mortal wounds - for the reason recorded throughout this project: a
question you answer reflexively is the one that grates.

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
IS checked, via is_battlesuit_unit()'s rule 19.03 keyword pooling.
"""

from game.damage_resolution import MortalWoundAllocationSession
from game.retaliation_cadre import is_battlesuit_unit, stratagem_target_ok
from game.stratagems import Stratagem
from game.turn import PHASE_CHARGE

GRAV_INHIBITOR_CP_COST = 1
GRAV_INHIBITOR_MORTAL_THRESHOLD = 6  # "for each 6, that enemy unit suffers 1 mortal wound"

AWAITING_SHOCK = "awaiting_shock"      # the Battle-Shock test is on the table
AWAITING_MORTALS = "awaiting_mortals"  # the D6-per-model roll is on the table


def alive_models(squad):
    """"one D6 for each model in that enemy unit" - the models that are
    actually still there. Dead ones are only stripped from Squad.models once
    per frame (GameState.remove_dead_models()), so this cannot just be len()."""
    return [m for m in squad.models if not m.is_dead()]


class GravInhibitorFieldController:
    """WHEN/TARGET bookkeeping plus the two-step effect. Reactive, like Stim
    Injectors - the offer goes to the player being charged, through
    DecisionManager, which is also what makes it resolvable by an AI with no
    extra wiring."""

    def __init__(self, stratagem_controller, dice_manager=None, battle_shock_controller=None,
                 decision_manager=None, turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.dice_manager = dice_manager
        self.battle_shock_controller = battle_shock_controller
        self.decision_manager = decision_manager
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._stratagem = Stratagem(
            name="Grav-Inhibitor Field", cp_cost=GRAV_INHIBITOR_CP_COST, effect=self._begin_effect,
        )
        self._charging_squad = None
        self._defender = None
        self._step = None
        self._resume_charge = None
        self.mortal_wound_session = None
        # Which declaration has already been asked about. begin_charge_move()
        # is called AGAIN for every retry of a failed approach (ai/agent_
        # driver.py sweeps up to 13 of them), and a DECLINED offer leaves rule
        # 15.01's once-per-phase ledger untouched - so without this the same
        # declaration would re-prompt on every retry. Same "the engine has no
        # 'declined' concept of its own" memo AIMemory keeps for the AI's own
        # decision points. Keyed on the battle round too, so the same unit
        # charging the same target in a later round is a new question.
        self._offered_key = None

    @property
    def is_busy(self):
        """Whether this stratagem is mid-resolution - main.py gates "Next
        Phase" and the AI on it, the same way it does for every other
        controller that owns a multi-step dice sequence."""
        return self._step is not None or self.mortal_wound_session is not None

    def expected_mortal_wounds(self, charging_squad):
        """One D6 per model, each 6 a wound: the quoted number on the prompt."""
        return len(alive_models(charging_squad)) / 6.0

    def can_offer(self, charging_squad, target_squad):
        """Every condition of the WHEN/TARGET clauses as one predicate, so the
        offer path and the tests ask the same question."""
        if charging_squad is None or target_squad is None or self.decision_manager is None:
            return False
        if self.is_busy:
            return False
        # WHEN: "your opponent's Charge phase" - i.e. the charging player's own
        # phase, and the reacting unit belongs to the other side.
        if self.turn_tracker is not None and self.turn_tracker.phase != PHASE_CHARGE:
            return False
        if target_squad.owner == charging_squad.owner:
            return False
        if not alive_models(charging_squad) or not alive_models(target_squad):
            return False
        if not stratagem_target_ok(target_squad):
            return False
        if not is_battlesuit_unit(target_squad):
            return False
        return self.stratagem_controller.can_use(target_squad.owner, self._stratagem, [target_squad])

    def maybe_offer(self, charging_squad, targets, on_resolved=None):
        """ChargeController.on_charge_declared's shape: returns True if an
        offer was opened, in which case this controller owns `on_resolved`
        (the continuation that starts the charge move) and calls it once the
        whole sequence - including a declined offer - is finished.

        Only ONE eligible target is offered even when a charge names several:
        the TARGET clause is "one ... unit", and rule 15.01 allows the
        stratagem once per phase anyway, so the choice between two eligible
        BATTLESUIT targets would be a distinction without a difference. The
        first by name, for determinism."""
        key = self._declaration_key(charging_squad, targets)
        if key == self._offered_key:
            return False  # this same declaration has already been asked about
        eligible = sorted(
            (t for t in targets if self.can_offer(charging_squad, t)), key=lambda s: s.name,
        )
        if not eligible:
            return False
        target = eligible[0]
        self._offered_key = key
        self._charging_squad = charging_squad
        self._defender = target
        self._resume_charge = on_resolved
        dice = len(alive_models(charging_squad))
        self.decision_manager.request(
            target.owner,
            f"Grav-Inhibitor Field ({GRAV_INHIBITOR_CP_COST} CP): {charging_squad.name} has declared a charge "
            f"against {target.name}. It immediately takes a Battle-Shock test, and you roll {dice}D6 - "
            f"each 6 inflicts a mortal wound (~{self.expected_mortal_wounds(charging_squad):.1f} expected).",
            [
                (f"Use Grav-Inhibitor Field ({GRAV_INHIBITOR_CP_COST} CP)",
                 lambda: self.stratagem_controller.use(target.owner, self._stratagem, [target])),
                ("Decline", self._declined),
            ],
            is_stratagem=True,
        )
        return True

    def _declaration_key(self, charging_squad, targets):
        battle_round = getattr(self.turn_tracker, "battle_round", None)
        return (battle_round, id(charging_squad), tuple(sorted(id(t) for t in targets)))

    def _declined(self):
        self._charging_squad = None
        self._defender = None
        self._finish()

    def _begin_effect(self, controller, player, targets):
        """Step 1 of 2: the Battle-Shock test on the CHARGING unit."""
        charging = self._charging_squad
        if self.game_log is not None:
            self.game_log.add(
                f"{player}: Grav-Inhibitor Field - {charging.name} must take a Battle-Shock test "
                f"and suffers a mortal wound for each 6 on {len(alive_models(charging))}D6."
            )
        # Rule 01.07's outcome and its logging have exactly one implementation;
        # this only decides WHEN the test happens.
        if self.battle_shock_controller is not None and self.battle_shock_controller.start_forced_roll(
            charging, "Grav-Inhibitor Field",
        ):
            self._step = AWAITING_SHOCK
        else:
            self._begin_mortal_roll()

    def _begin_mortal_roll(self):
        """Step 2 of 2: one D6 per model in the charging unit."""
        charging = self._charging_squad
        count = len(alive_models(charging))
        if count <= 0 or self.dice_manager is None:
            self._finish()
            return
        self.dice_manager.roll(
            count=count, sides=6, label="Grav-Inhibitor Field",
            success_threshold=GRAV_INHIBITOR_MORTAL_THRESHOLD, target_name=charging.name,
            target_squad=charging,
        )
        self._step = AWAITING_MORTALS

    def on_dice_acknowledged(self):
        """Wired into main.py's dice-ack chain AFTER battle_shock_controller's,
        so the test's own outcome is already applied when the second roll is
        queued behind it."""
        if self.dice_manager is None:
            return
        # Rule 24.12 (Feel No Pain): this acknowledgement may be that ability's
        # extra dice step inside the mortal-wound session, not one of ours -
        # same shape as ExplosivesController.on_dice_acknowledged().
        if self.mortal_wound_session is not None and self.mortal_wound_session.pending_fnp is not None:
            self.mortal_wound_session.on_fnp_acknowledged()
            self._check_mortal_wounds_done()
            return
        if self._step == AWAITING_SHOCK:
            self._step = None
            self._begin_mortal_roll()
            return
        if self._step == AWAITING_MORTALS:
            self._step = None
            rolls = self.dice_manager.last_values
            hits = sum(1 for r in rolls if r >= GRAV_INHIBITOR_MORTAL_THRESHOLD)
            charging = self._charging_squad
            self._log(
                f"Grav-Inhibitor Field roll {rolls}: {hits} mortal wound(s) to {charging.name}."
            )
            if hits > 0:
                if self.turn_tracker is not None:
                    # Rule 06.02: which model takes each mortal wound is the
                    # DEFENDING player's choice - and the unit taking them here
                    # is the charging one, i.e. the opponent of whoever spent
                    # the CP.
                    self.turn_tracker.set_active(charging.owner)
                self.mortal_wound_session = MortalWoundAllocationSession(
                    charging, hits, dice_manager=self.dice_manager, log=self._log,
                )
                self._check_mortal_wounds_done()
            else:
                self._finish()

    @property
    def pending_damage_choice(self):
        if self.mortal_wound_session is None:
            return None
        return self.mortal_wound_session.pending_choice

    def choose_damage_model(self, model):
        if self.mortal_wound_session is None:
            return
        self.mortal_wound_session.choose_model(model)
        self._check_mortal_wounds_done()

    def _check_mortal_wounds_done(self):
        if self.mortal_wound_session is None or not self.mortal_wound_session.done:
            return
        self.mortal_wound_session = None
        self._finish()

    def _finish(self):
        """Hand control back to the charge, whatever happened - used,
        declined, or resolved to nothing. _start_declared_move() re-checks its
        own preconditions, including whether the charging unit survived."""
        if self.turn_tracker is not None and self._charging_squad is not None:
            # Put the active flag back where the phase says it belongs: this is
            # still the charging player's Charge phase.
            self.turn_tracker.set_active(self._charging_squad.owner)
        self._step = None
        self._charging_squad = None
        self._defender = None
        resume = self._resume_charge
        self._resume_charge = None
        if resume is not None:
            resume()

    def _log(self, message):
        if self.game_log is not None:
            self.game_log.add(message)
