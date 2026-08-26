from game import line_of_sight
from game.damage_resolution import MortalWoundAllocationSession
from game.shooting import available_shooting_types
from game.squad import edge_distance
from game.stratagems import Stratagem
from game.turn import PHASE_SHOOTING

IDLE = "idle"
CHOOSING_MODEL = "choosing_model"    # the unit has more than one EXPLOSIVES/GRENADES model - pick which one throws
CHOOSING_TARGET = "choosing_target"  # pick an enemy unit within 8" of, and visible to, that model

EXPLOSIVES_CP_COST = 1
EXPLOSIVES_RANGE_IN = 8.0
EXPLOSIVES_DICE_COUNT = 6
EXPLOSIVES_SUCCESS_THRESHOLD = 4


class ExplosivesController:
    """Rule 15.05 (Explosives, Core Stratagem, 1CP): during your Shooting
    phase, an eligible friendly EXPLOSIVES/GRENADES unit picks one such
    model, then one unengaged enemy unit within 8" of and visible to it,
    then rolls 6D6 - each 4+ inflicts 1 mortal wound (06.02) on that enemy
    unit. "Eligible to shoot" is read as available_shooting_types() being
    non-empty (the same check the Shoot button itself uses) rather than
    "hasn't shot yet this phase" - the stratagem doesn't consume the unit's
    own shooting action, so a unit can still Explosives after (or instead
    of) shooting normally this phase."""

    def __init__(
        self, stratagem_controller, dice_manager, movement_controller=None,
        all_tokens=None, obstacles=None, terrain_areas=None, turn_tracker=None, game_log=None,
    ):
        self.stratagem_controller = stratagem_controller
        self.dice_manager = dice_manager
        self.movement_controller = movement_controller
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.obstacles = obstacles if obstacles is not None else []
        self.terrain_areas = terrain_areas if terrain_areas is not None else []
        self.turn_tracker = turn_tracker
        self.game_log = game_log

        self.state = IDLE
        self.acting_squad = None
        self.acting_model = None
        self.target_squad = None
        self._pending_roll = False
        self.mortal_wound_session = None

        self._stratagem = Stratagem(name="Explosives", cp_cost=EXPLOSIVES_CP_COST, effect=self._begin_roll)

    def _qualifying_models(self, squad):
        return [m for m in squad.models if m.profile.explosives or m.profile.grenades]

    def _has_reachable_target(self, squad):
        """TARGET (rule 15.05): is there any unengaged enemy unit within 8"
        of, and visible to, at least one qualifying model? Checked in
        can_use() so the button/offer doesn't appear when nothing is in
        range - mirrors eligible_target_squads(), but across every
        qualifying model rather than a single already-chosen one, since no
        model has been picked yet at this point."""
        qualifying = self._qualifying_models(squad)
        if not qualifying:
            return False
        enemy_squads = {
            token.squad for token in self.all_tokens
            if token.squad is not None and token.squad.owner != squad.owner
        }
        for enemy_squad in enemy_squads:
            if enemy_squad.is_engaged(self.all_tokens):
                continue
            for model in qualifying:
                if not any(edge_distance(model, m) <= EXPLOSIVES_RANGE_IN for m in enemy_squad.models):
                    continue
                if any(
                    line_of_sight.has_line_of_sight(model, m, self.obstacles, self.all_tokens, self.terrain_areas)
                    for m in enemy_squad.models
                ):
                    return True
        return False

    def can_use(self, squad):
        if squad is None or self.state != IDLE:
            return False
        if self.turn_tracker is not None:
            if self.turn_tracker.phase != PHASE_SHOOTING:
                return False
            if squad.owner != self.turn_tracker.active_player:
                return False
        if squad.is_engaged(self.all_tokens):
            return False
        # Swooping Hawks' Grenade Pack Flyover: "each time this unit uses this
        # ability, until the end of the turn, you cannot target this unit with
        # the Explosives Stratagem" - see game/grenade_pack_flyover.py.
        if getattr(squad, "explosives_locked_until_end_of_turn", False):
            return False
        if self.movement_controller is not None and squad in self.movement_controller.advanced_squad_ids:
            return False
        if not self._qualifying_models(squad):
            return False
        if not available_shooting_types(squad, self.all_tokens, self.movement_controller):
            return False
        if not self._has_reachable_target(squad):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def start(self, squad):
        if not self.can_use(squad):
            return
        self.acting_squad = squad
        qualifying = self._qualifying_models(squad)
        if len(qualifying) == 1:
            self.acting_model = qualifying[0]
            self.state = CHOOSING_TARGET
        else:
            self.acting_model = None
            self.state = CHOOSING_MODEL

    def choosable_models(self):
        if self.state != CHOOSING_MODEL or self.acting_squad is None:
            return []
        return self._qualifying_models(self.acting_squad)

    def choose_model(self, model):
        if self.state != CHOOSING_MODEL or model not in self.choosable_models():
            return
        self.acting_model = model
        self.state = CHOOSING_TARGET

    def eligible_target_squads(self):
        """Rule 15.05 TARGET: enemy units within 8" of, and visible to, the
        chosen model, that are themselves unengaged."""
        if self.state != CHOOSING_TARGET or self.acting_model is None:
            return []
        enemy_squads = {
            token.squad for token in self.all_tokens
            if token.squad is not None and token.squad.owner != self.acting_squad.owner
        }
        result = []
        for squad in enemy_squads:
            if squad.is_engaged(self.all_tokens):
                continue
            if not any(edge_distance(self.acting_model, m) <= EXPLOSIVES_RANGE_IN for m in squad.models):
                continue
            if not any(
                line_of_sight.has_line_of_sight(self.acting_model, m, self.obstacles, self.all_tokens, self.terrain_areas)
                for m in squad.models
            ):
                continue
            result.append(squad)
        return result

    def cancel(self):
        """Back out before CP is spent (rule 15.01 step 1, target selection,
        hasn't completed yet) - no cost, the unit stays eligible."""
        if self._pending_roll:
            return  # can't cancel mid dice-roll/resolution
        self.state = IDLE
        self.acting_squad = None
        self.acting_model = None
        self.target_squad = None

    def choose_target(self, target_squad):
        if self.state != CHOOSING_TARGET or target_squad not in self.eligible_target_squads():
            return
        self.target_squad = target_squad
        self.stratagem_controller.use(self.acting_squad.owner, self._stratagem, [self.acting_squad])

    def _begin_roll(self, controller, player, targets):
        self.dice_manager.roll(
            count=EXPLOSIVES_DICE_COUNT, sides=6,
            label=f"Explosives: {self.acting_model.profile.name}",
            success_threshold=EXPLOSIVES_SUCCESS_THRESHOLD,
            target_name=self.target_squad.name, target_squad=self.target_squad,
        )
        self._pending_roll = True

    def on_dice_acknowledged(self):
        if not self._pending_roll or self.dice_manager is None:
            return
        # Rule 24.12 (Feel No Pain): this acknowledgement might be that
        # ability's extra dice step, not the original Explosives 6D6 roll.
        if self.mortal_wound_session is not None and self.mortal_wound_session.pending_fnp is not None:
            self.mortal_wound_session.on_fnp_acknowledged()
            self._check_mortal_wound_done()
            return

        rolls = self.dice_manager.last_values
        hits = sum(1 for r in rolls if r >= EXPLOSIVES_SUCCESS_THRESHOLD)
        self._log(f"Explosives ({self.acting_model.profile.name}) roll {rolls}: {hits} mortal wound(s) to {self.target_squad.name}.")
        if hits > 0:
            if self.turn_tracker is not None:
                # Rule 06.02: which model takes each mortal wound, whenever
                # more than one candidate qualifies, is the defending
                # player's choice, not the attacker's.
                self.turn_tracker.set_active(self.target_squad.owner)
            self.mortal_wound_session = MortalWoundAllocationSession(
                self.target_squad, hits, dice_manager=self.dice_manager, log=self._log,
            )
            self._check_mortal_wound_done()
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
        self._check_mortal_wound_done()

    def _check_mortal_wound_done(self):
        if self.mortal_wound_session is None or not self.mortal_wound_session.done:
            return
        self.mortal_wound_session = None
        self._finish()

    def _finish(self):
        if self.turn_tracker is not None:
            self.turn_tracker.set_active(self.acting_squad.owner)
        self._pending_roll = False
        self.state = IDLE
        self.acting_squad = None
        self.acting_model = None
        self.target_squad = None

    def _log(self, message):
        if self.game_log is not None:
            self.game_log.add(message)
