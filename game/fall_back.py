"""Rule 09.07: Fall Back - the only move type available to a currently
engaged unit. Two modes:

Ordered Retreat: only available if the unit isn't battle-shocked. Moves
normally (still blocked by terrain/enemy models like any other move), must
end unengaged (game/movement.py's confirm_move() already falls through to
its generic "must end unengaged" check for any move_mode it doesn't
recognize, which covers "fall_back" - no special-casing needed there).

Desperate Escape: mandatory if the unit is battle-shocked (no real choice,
so the mode-choice screen is skipped entirely - see declare()), optional
otherwise. Models may be moved across other models (not terrain) during the
drag (game/movement.py's clamp_move(), gated on
MovementController.desperate_escape_this_move). After a successful Desperate
Escape move: one Hazard Roll (rule 06.03, game/hazard.py's HazardRollStep -
same mechanism already used by Transport's Combat/Emergency Disembark) per
model, then - if the unit isn't already battle-shocked - an immediate
Battle-Shock test (game/battle_shock.py's start_desperate_escape_roll(),
outside the normal Command-phase timing).

Both modes block shooting and charging until end of turn
(Squad.fell_back_this_turn, read by shooting.py's available_shooting_types()
and charge.py's can_declare_charge()) and "cannot start an action" (a no-op
- this engine has no Actions system yet, same as every other move type's
identical clause)."""

from game.hazard import HazardRollStep

IDLE = "idle"
CHOOSING_MODE = "choosing_mode"  # picking Ordered Retreat vs Desperate Escape, before the move starts

ORDERED_RETREAT = "ordered_retreat"
DESPERATE_ESCAPE = "desperate_escape"


class FallBackController:
    def __init__(self, movement_controller, battle_shock_controller, dice_manager=None, game_log=None):
        self.movement_controller = movement_controller
        self.battle_shock_controller = battle_shock_controller
        self.dice_manager = dice_manager
        self.game_log = game_log

        self.state = IDLE
        self.acting_squad = None
        self.mode = None
        self._hazard_step = None  # HazardRollStep while Desperate Escape's post-move hazard roll is pending

    def declare(self, squad):
        """Rule 09.07: begin declaring a Fall Back move for squad (must
        already be engaged - can_make_fall_back_move() gates the "Fall
        Back" button that calls this). A battle-shocked unit has no real
        choice (Ordered Retreat isn't available to it) - skip the mode-
        choice screen and go straight to Desperate Escape, the same "skip
        the dialog when there's only one real option" idiom used elsewhere
        in this codebase (e.g. Explosives auto-picking a sole qualifying
        model)."""
        if self.state != IDLE or squad is None or not self.movement_controller.can_make_fall_back_move(squad):
            return
        self.acting_squad = squad
        if squad.battle_shocked:
            self.choose_mode(DESPERATE_ESCAPE)
        else:
            self.state = CHOOSING_MODE

    def choose_mode(self, mode):
        if self.acting_squad is None or mode not in (ORDERED_RETREAT, DESPERATE_ESCAPE):
            return
        if mode == ORDERED_RETREAT and self.acting_squad.battle_shocked:
            return  # rule 09.07: Ordered Retreat isn't available to a battle-shocked unit
        self.mode = mode
        self.state = IDLE  # nothing more to show pre-move - the normal MOVING-state Confirm/Cancel UI takes over
        self.movement_controller.start_fall_back_move(mode)

    def decline(self):
        """Cancel, at any point: before a mode is even chosen (mode-choice
        screen's own Cancel button) or mid-drag after one was (MOVING-state
        Cancel button) - same "one decline method covers every stage"
        pattern as ChargeController.decline_charge_move()."""
        if self.movement_controller.move_mode == "fall_back":
            self.movement_controller.cancel_move()
        self.state = IDLE
        self.mode = None
        self.acting_squad = None

    def confirm(self):
        """Confirm button while movement_controller.move_mode == "fall_back"
        (see ActionPanel._draw_movement_ui()'s MOVING branch)."""
        if self.movement_controller.move_mode != "fall_back":
            return
        squad = self.movement_controller.selected_squad
        self.movement_controller.confirm_move()
        if self.movement_controller.errors:
            return  # failed (e.g. still engaged) - stays in MOVING for another attempt, same as Charge/Pile-In/Consolidate
        if self.mode == DESPERATE_ESCAPE and self.dice_manager is not None and squad is not None and squad.models:
            self._hazard_step = HazardRollStep(squad, len(squad.models), self.dice_manager, log=self._log)
        else:
            self.mode = None
            self.acting_squad = None

    # --- shared dice/damage-choice plumbing for Desperate Escape's post-move Hazard Roll ---
    # (exact copy of TransportController's own _hazard_step plumbing for its
    # Combat/Emergency Disembark hazard roll)

    @property
    def pending_damage_choice(self):
        return self._hazard_step.pending_damage_choice if self._hazard_step is not None else None

    def choose_damage_model(self, model):
        if self._hazard_step is None:
            return
        self._hazard_step.choose_damage_model(model)
        if self._hazard_step.done:
            self._finish_hazard_step()

    def on_dice_acknowledged(self):
        if self._hazard_step is None:
            return
        self._hazard_step.on_dice_acknowledged()
        if self._hazard_step.done:
            self._finish_hazard_step()

    def _finish_hazard_step(self):
        self._hazard_step = None
        squad = self.acting_squad
        if squad is not None and squad.models and not squad.battle_shocked:
            self.battle_shock_controller.start_desperate_escape_roll(squad)
        self.mode = None
        self.acting_squad = None

    def _log(self, message):
        if self.game_log is not None:
            self.game_log.add(message)
