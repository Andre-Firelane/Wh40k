"""Death Lord's Chosen Stratagem: SICKENING IMPACT (1 CP, Strategic Ploy).

  WHEN: Your Charge phase, just after a TERMINATOR unit from your army ends a
        Charge move.
  TARGET: That TERMINATOR unit.
  EFFECT: Select one enemy unit within Engagement Range of your unit, then roll
        one D6 for each model in your unit that is within Engagement Range of
        that enemy unit: for each 2+, that enemy unit suffers 1 mortal wound
        (to a maximum of 6 mortal wounds).

REACTIVE, so it answers inside its own controller via `auto_players` and needs
NOTHING in ai/ - the same arrangement 'Ard as Nails and the three reactive
Awakened Dynasty protocols use. The human gets a DecisionManager prompt from
exactly the same code path; there is one verdict, not two.

ITS SEAM ALREADY EXISTS. "Just after a unit ends a Charge move" is
ChargeController.on_charge_move_finished, the hook the Skorpekh Lord's Crimson
Harvest introduced - and it is deliberately NOT _finish_charge(), which also
runs for a DECLINED charge and for a unit destroyed before it could move.
Neither of those ends a Charge move.

THE DICE COUNT IS PER MODEL IN ENGAGEMENT RANGE OF THE CHOSEN TARGET, not per
model in the unit - a six-model Deathshroud squad that only got two models into
contact rolls two dice. Measured through squad.py's own model_engaged_with(),
so "within Engagement Range" means what it means everywhere else.

THE 6 MORTAL WOUND CAP is on the RESULT, not on the dice: a unit may roll more
than six dice and still inflict at most six. Written that way because clamping
the dice instead would also change what the player sees rolled.

IT IS OPTIONAL ("you can" is implicit in a Stratagem - you choose to spend the
CP), so the verdict is a real one: worth_using() takes it whenever there is
anything to hit at all, since 1 CP for an average of ~0.83 mortal wounds per
engaged model is a good trade for a unit that just charged, and the alternative
(measuring expected damage) needs a target profile the mortal wounds ignore.
"""
from game import ai_mode, death_lords_chosen
from game.damage_resolution import MortalWoundAllocationSession
from game.squad import ENGAGEMENT_RANGE_IN, model_engaged_with
from game.stratagems import Stratagem
from game.turn import PHASE_CHARGE

SICKENING_IMPACT_CP = 1
SICKENING_IMPACT_THRESHOLD = 2   # "for each 2+"
SICKENING_IMPACT_MAX_WOUNDS = 6  # "to a maximum of 6 mortal wounds"
SICKENING_IMPACT_LABEL = "Sickening Impact"


def engaged_targets(squad, all_tokens):
    """Every enemy unit within Engagement Range of this unit."""
    seen = {}
    for token in all_tokens or ():
        other = getattr(token, "squad", None)
        if other is None or token.is_dead() or other.owner == squad.owner:
            continue
        if id(other) in seen:
            continue
        if any(model_engaged_with(m, other) for m in squad.models if not m.is_dead()):
            seen[id(other)] = other
    return sorted(seen.values(), key=lambda s: s.name)


def dice_against(squad, target_squad):
    """"one D6 for each model in your unit that is within Engagement Range of
    THAT enemy unit" - not each model in the unit."""
    return sum(1 for m in squad.models
               if not m.is_dead() and model_engaged_with(m, target_squad))


class SickeningImpactController:
    """Fired by ChargeController.on_charge_move_finished."""

    def __init__(self, stratagem_controller, dice_manager=None, decision_manager=None,
                 turn_tracker=None, game_log=None, game_state=None, auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.dice_manager = dice_manager
        self.decision_manager = decision_manager
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self.game_state = game_state
        self.auto_players = ai_mode.players(auto_players)
        self._stratagem = Stratagem(
            SICKENING_IMPACT_LABEL, SICKENING_IMPACT_CP, self._effect,
            # Every charging TERMINATOR unit has its own "just after it ends a
            # Charge move" window, so 15.01's once-per-target-per-phase is the
            # wrong bound here - the same call Undying Legions makes.
            allow_repeat_target=True,
        )
        self._pending = None
        self.mortal_wound_session = None

    def _log(self, message, file_only=False):
        if self.game_log is not None:
            self.game_log.add(message, file_only=file_only)

    def _tokens(self):
        return list(self.game_state.tokens) if self.game_state is not None else []

    @property
    def is_busy(self):
        return self._pending is not None or self.mortal_wound_session is not None

    # ----------------------------------------------------------- conditions

    def can_use(self, squad):
        if squad is None or self.is_busy:
            return False
        if not death_lords_chosen.stratagem_target_ok(squad):
            return False
        if not death_lords_chosen.is_terminator_unit(squad):
            return False
        if self.turn_tracker is not None:
            if self.turn_tracker.phase != PHASE_CHARGE:
                return False
            if squad.owner != self.turn_tracker.turn_owner:
                return False   # "YOUR Charge phase"
        if not engaged_targets(squad, self._tokens()):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def is_worth_using(self, squad):
        """Anything in Engagement Range is worth 1 CP - see the module
        docstring on why this is not a damage measurement."""
        return any(dice_against(squad, t) > 0 for t in engaged_targets(squad, self._tokens()))

    # ------------------------------------------------------------ the offer

    def on_charge_move_finished(self, squad):
        """ChargeController's hook. A charge that fell short leaves nothing in
        Engagement Range, so can_use() simply finds no target - no separate
        "did the charge succeed" test is needed or wanted."""
        return self.maybe_offer(squad)

    def maybe_offer(self, squad):
        # is_worth_using() is the AI's verdict and is applied INSIDE the auto
        # branch below, not here. It used to run above the split - the second
        # place in the repo that did, after 'Ard as Nails - so a human was only
        # ever shown this Stratagem when the engine already thought it was
        # worth the CP.
        if not self.can_use(squad):
            return False
        targets = engaged_targets(squad, self._tokens())
        if squad.owner in self.auto_players or self.decision_manager is None:
            if not self.is_worth_using(squad):
                return False
            best = max(targets, key=lambda t: (dice_against(squad, t), t.name))
            return self.use(squad, best)
        options = [(f"Sickening Impact (1 CP): {t.name} "
                    f"({dice_against(squad, t)}D6)",
                    (lambda target=t: self.use(squad, target)), t)
                   for t in targets]
        options.append(("Decline", None))
        self.decision_manager.request(
            squad.owner,
            f"{squad.name} ended a Charge move - Sickening Impact?",
            options, is_stratagem=True)
        return True

    def use(self, squad, target):
        if target is None or not self.can_use(squad):
            return False
        dice = dice_against(squad, target)
        if dice <= 0:
            return False
        if not self.stratagem_controller.use(squad.owner, self._stratagem, [squad]):
            return False
        self._pending = {"squad": squad, "target": target}
        self.dice_manager.roll(
            dice, 6, label=f"{SICKENING_IMPACT_LABEL} ({dice}D6)",
            success_threshold=SICKENING_IMPACT_THRESHOLD,
            target_name=target.name, attacker_squad=squad, target_squad=target)
        return True

    def _effect(self, controller, player, targets):
        """The Stratagem's own effect callback. The work happens in use() and
        on_dice_acknowledged() - this exists so StratagemController's ledger
        and CP accounting run exactly as they do for every other Stratagem."""
        return True

    # --------------------------------------------------------- the resolution

    def on_dice_acknowledged(self):
        if self.mortal_wound_session is not None and self.mortal_wound_session.pending_fnp is not None:
            self.mortal_wound_session.on_fnp_acknowledged()
            self._check_session_done()
            return True
        if self._pending is None or self.dice_manager is None:
            return False
        ctx = self._pending
        self._pending = None
        rolls = self.dice_manager.last_values or []
        # The cap is on the RESULT, not on the dice - a unit may roll more than
        # six and still inflict at most six.
        wounds = min(SICKENING_IMPACT_MAX_WOUNDS,
                     sum(1 for r in rolls if r >= SICKENING_IMPACT_THRESHOLD))
        if wounds <= 0:
            self._log(f"[sickening impact] {ctx['squad'].name}: {rolls} - nothing landed.",
                      file_only=True)
            return True
        self._log(f"{SICKENING_IMPACT_LABEL} ({ctx['squad'].name}): rolled {rolls} "
                  f"(needed {SICKENING_IMPACT_THRESHOLD}+) - {ctx['target'].name} suffers "
                  f"{wounds} mortal wound(s).")
        self.mortal_wound_session = MortalWoundAllocationSession(
            ctx["target"], wounds, dice_manager=self.dice_manager, log=self._log)
        self._check_session_done()
        return True

    def _check_session_done(self):
        if self.mortal_wound_session is None or not self.mortal_wound_session.done:
            return
        self.mortal_wound_session = None

    @property
    def pending_damage_choice(self):
        if self.mortal_wound_session is None:
            return None
        return self.mortal_wound_session.pending_choice

    def choose_damage_model(self, model):
        if self.mortal_wound_session is None:
            return
        self.mortal_wound_session.choose_model(model)
        self._check_session_done()
