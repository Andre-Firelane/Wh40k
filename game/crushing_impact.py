from game.damage_resolution import MortalWoundAllocationSession
from game.squad import is_monster_or_vehicle_unit, model_engaged_with
from game.stratagems import Stratagem
from game.turn import PHASE_CHARGE

CRUSHING_IMPACT_CP_COST = 1
CRUSHING_IMPACT_MAX_MORTAL_WOUNDS_PER_UNIT = 6

IDLE = "idle"
CHOOSING_ENEMY = "choosing_enemy"  # EFFECT step 1: pick an enemy unit engaged with your unit
CHOOSING_MODEL = "choosing_model"  # EFFECT step 2: pick a model in your unit engaged with that enemy unit


class CrushingImpactController:
    """Rule 15.06 (Crushing Impact, Core Stratagem, 1CP): WHEN a friendly
    MONSTER/VEHICLE unit ends a charge move in your Charge phase, TARGET
    that unit, EFFECT: pick an engaged enemy unit (step 1) and one of your
    own models engaged with it (step 2), then roll a number of D6 equal to
    that model's Toughness (step 3) - each 1 deals your unit a mortal
    wound, each 5+ deals the enemy unit a mortal wound (each capped at 6
    mortal wounds).

    WHEN is read the same as Epic Challenge/Command Re-roll: usable any
    time the charging unit is selected on the board after its charge move
    was confirmed this phase (charge_controller.charged_squad_ids), not
    only the literal instant the move ends - the "Crushing Impact (1CP)"
    button lives in the normal per-squad panel, next to Battle-Shock
    Roll/Explosives/Epic Challenge.

    TARGET is trivial (the stratagem is always used on the unit that just
    charged, no real choice), so CP is spent immediately on the button
    click, before the interactive 3-step EFFECT sequence runs - unlike
    Explosives (whose actual TARGET, an enemy unit, is chosen as part of
    its own multi-step flow). can_use()'s preconditions (must be engaged)
    guarantee a valid enemy unit and a valid own model exist at every step
    of that sequence, so there's no cancel/back-out path once started."""

    def __init__(
        self, stratagem_controller, dice_manager, charge_controller, all_tokens=None,
        turn_tracker=None, game_log=None,
    ):
        self.stratagem_controller = stratagem_controller
        self.dice_manager = dice_manager
        self.charge_controller = charge_controller
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.turn_tracker = turn_tracker
        self.game_log = game_log

        self.state = IDLE
        self.acting_squad = None
        self.enemy_squad = None
        self.acting_model = None
        self._pending_roll = False
        self._enemy_wounds = 0
        self._own_wounds = 0
        self.mortal_wound_session = None

        self._stratagem = Stratagem(
            name="Crushing Impact", cp_cost=CRUSHING_IMPACT_CP_COST, effect=self._begin_choice, when=self._when,
        )

    def _when(self, controller, player):
        return self.turn_tracker is None or self.turn_tracker.phase == PHASE_CHARGE

    def _all_squads(self):
        return {token.squad for token in self.all_tokens if token.squad is not None}

    def can_use(self, squad):
        if squad is None or self.state != IDLE:
            return False
        if self.turn_tracker is not None and squad.owner != self.turn_tracker.active_player:
            return False
        if squad not in self.charge_controller.charged_squad_ids:
            return False
        if not is_monster_or_vehicle_unit(squad):
            return False
        if not squad.is_engaged(self.all_tokens):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def start(self, squad):
        if not self.can_use(squad):
            return
        self.acting_squad = squad
        self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _begin_choice(self, controller, player, targets):
        self.state = CHOOSING_ENEMY

    def eligible_enemy_squads(self):
        if self.state != CHOOSING_ENEMY or self.acting_squad is None:
            return []
        return [
            s for s in self._all_squads()
            if s.owner != self.acting_squad.owner and self.acting_squad.is_engaged_with(s)
        ]

    def choose_enemy(self, enemy_squad):
        if self.state != CHOOSING_ENEMY or enemy_squad not in self.eligible_enemy_squads():
            return
        self.enemy_squad = enemy_squad
        self.state = CHOOSING_MODEL

    def choosable_models(self):
        if self.state != CHOOSING_MODEL or self.acting_squad is None or self.enemy_squad is None:
            return []
        return [m for m in self.acting_squad.models if model_engaged_with(m, self.enemy_squad)]

    def choose_model(self, model):
        if self.state != CHOOSING_MODEL or model not in self.choosable_models():
            return
        self.acting_model = model
        self.state = IDLE
        self._begin_roll()

    def _begin_roll(self):
        count = self.acting_model.profile.toughness
        self.dice_manager.roll(
            count=count, sides=6,
            label=f"Crushing Impact: {self.acting_model.profile.name} (T{count})",
            target_name=self.enemy_squad.name,
        )
        self._pending_roll = True

    def on_dice_acknowledged(self):
        if self._pending_roll:
            self._pending_roll = False
            rolls = self.dice_manager.last_values
            ones = sum(1 for r in rolls if r == 1)
            fives_plus = sum(1 for r in rolls if r >= 5)
            self._own_wounds = min(ones, CRUSHING_IMPACT_MAX_MORTAL_WOUNDS_PER_UNIT)
            self._enemy_wounds = min(fives_plus, CRUSHING_IMPACT_MAX_MORTAL_WOUNDS_PER_UNIT)
            self._log(
                f"Crushing Impact roll {rolls}: {self._enemy_wounds} mortal wound(s) to {self.enemy_squad.name}, "
                f"{self._own_wounds} mortal wound(s) to {self.acting_squad.name}."
            )
            self._start_next_allocation()
            return

        if self.mortal_wound_session is not None and self.mortal_wound_session.pending_fnp is not None:
            self.mortal_wound_session.on_fnp_acknowledged()
            self._check_allocation_done()

    def _start_next_allocation(self):
        """Rule 06.02: each side's mortal wounds are allocated by that
        unit's own owner - resolved as two separate, sequential sessions
        (enemy unit first, then the charging unit itself) rather than one,
        exactly like DeadlyDemiseController queues one affected squad after
        another."""
        if self._enemy_wounds > 0:
            target, wounds = self.enemy_squad, self._enemy_wounds
            self._enemy_wounds = 0
        elif self._own_wounds > 0:
            target, wounds = self.acting_squad, self._own_wounds
            self._own_wounds = 0
        else:
            self._finish()
            return
        if self.turn_tracker is not None:
            self.turn_tracker.set_active(target.owner)
        self.mortal_wound_session = MortalWoundAllocationSession(
            target, wounds, dice_manager=self.dice_manager, log=self._log,
        )
        self._check_allocation_done()

    @property
    def pending_damage_choice(self):
        if self.mortal_wound_session is None:
            return None
        return self.mortal_wound_session.pending_choice

    def choose_damage_model(self, model):
        if self.mortal_wound_session is None:
            return
        self.mortal_wound_session.choose_model(model)
        self._check_allocation_done()

    def _check_allocation_done(self):
        if self.mortal_wound_session is None or not self.mortal_wound_session.done:
            return
        self.mortal_wound_session = None
        self._start_next_allocation()

    def _finish(self):
        if self.turn_tracker is not None and self.acting_squad is not None:
            self.turn_tracker.set_active(self.acting_squad.owner)
        self.state = IDLE
        self.acting_squad = None
        self.enemy_squad = None
        self.acting_model = None
        self._pending_roll = False

    def _log(self, message):
        if self.game_log is not None:
            self.game_log.add(message)
