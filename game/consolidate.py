from game import battle_focus
from game import fight
from game.turn import PHASE_FIGHT

IDLE = "idle"
CHOOSING_ENGAGING_TARGETS = "choosing_engaging_targets"  # Engaging Consolidation's real target choice
CHOOSING_OBJECTIVE = "choosing_objective"  # Objective Consolidation's real target choice, only reached with 2+ candidates

ONGOING = "ongoing"
ENGAGING = "engaging"
OBJECTIVE = "objective"

CONSOLIDATE_RANGE_IN = 3.0


def _reach(squad):
    """How far this unit may consolidate, and how far it may look for
    something to consolidate towards.

    Both, deliberately: the Aeldari Agile Manoeuvre Sudden Strike raises the
    move to 6", and this file derives which enemies and objectives are even
    reachable from the SAME number it moves - so widening the move widens those
    too. Confirmed as the intended reading with the user; rule 12.03's separate
    pile-in target range (game/pile_in.py's PILE_IN_TARGET_RANGE_IN) is the
    opposite case and is left alone."""
    return battle_focus.melee_move_range_in(squad, CONSOLIDATE_RANGE_IN)


class ConsolidateController:
    """Rules 12.07/12.08: after the Fight step, both players make optional
    consolidation moves with every unit that was eligible to fight this
    phase. Ongoing Consolidation (already engaged) auto-selects every
    currently-engaged enemy unit as its mandatory target, exactly like a
    pile-in move. Engaging Consolidation (unengaged but within 3" of an
    enemy) is a real choice of one or more of those nearby units. Objective
    Consolidation (unengaged, no enemy within 3", but within 3" of one or
    more objectives) is a real choice of exactly ONE of those objectives -
    auto-picked if there's only one candidate (same convention as every
    other single-choice-when-forced pattern in this codebase), otherwise a
    small panel button list (game/ui/action_panel.py's
    _draw_consolidate_choose_objective) - objectives aren't board tokens, so
    unlike Engaging's targets there's no board-click equivalent, only the
    panel list."""

    def __init__(
        self, game_log=None, turn_tracker=None, all_tokens=None,
        movement_controller=None, fight_controller=None, objectives=None,
    ):
        self.game_log = game_log
        self.turn_tracker = turn_tracker
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.movement_controller = movement_controller
        self.fight_controller = fight_controller
        self.objectives = objectives if objectives is not None else []

        self.state = IDLE
        self.active_squad = None
        self.targets = []  # squads chosen/declared so far (Engaging mode only, before the move begins)
        self.consolidated_squad_ids = set()

    def reset_fight_phase(self):
        """Rule 12.07: a new Fight phase comes around every battle round."""
        self.state = IDLE
        self.active_squad = None
        self.targets = []
        self.consolidated_squad_ids = set()

    def _enemy_squads(self, squad):
        return {
            token.squad for token in self.all_tokens
            if token.squad is not None and token.squad.owner != squad.owner
        }

    def can_consolidate(self, squad):
        """Rule 12.08 eligibility: was eligible to fight this phase (we use
        fought_squad_ids, which - since the Fight step always runs every
        eligible unit to completion - is exactly that set), AND the Fight
        step itself is over.

        That last condition was missing, and the user caught it: "eigentlich
        war consolidate ja schon falsch, weil der nahkampf noch gar nicht
        vorbei war". fought_squad_ids fills up one unit at a time as the
        Fight step alternates between the players (rule 12.04), so without
        this a unit could consolidate the instant IT had swung, while other
        units - including the enemy it is standing in - still had their
        attacks to make. Consolidation is a step 'after the Fight step' (see
        this class's own docstring), not something interleaved with it: the
        board must not shift under a unit that is still waiting to strike
        back. fight_controller.state == DONE is exactly "no unit on either
        side is eligible to fight anymore".

        Deliberately NOT narrowed further to "only if the enemy unit was
        destroyed": rule 12.08 as transcribed here defines an Ongoing
        Consolidation mode specifically for a unit that is still engaged,
        so a surviving enemy is a case the rule covers rather than
        excludes."""
        if squad is None or squad in self.consolidated_squad_ids:
            return False
        if self.turn_tracker is not None and self.turn_tracker.phase != PHASE_FIGHT:
            return False
        if self.fight_controller is None or self.fight_controller.state != fight.DONE:
            return False
        return squad in self.fight_controller.fought_squad_ids

    def determine_mode(self, squad):
        """Rule 12.08 BEFORE MOVING: the mode isn't a free choice - exactly
        one applies, in this priority order. None means nothing applies at
        all (not engaged, no enemy within 3", no objective within 3")."""
        if squad.is_engaged(self.all_tokens):
            return ONGOING
        if any(squad.min_distance_to(s) <= _reach(squad) for s in self._enemy_squads(squad)):
            return ENGAGING
        if self._objectives_within(squad):
            return OBJECTIVE
        return None

    def ongoing_targets(self, squad):
        return [s for s in self._enemy_squads(squad) if squad.is_engaged_with(s)]

    def eligible_engaging_targets(self, squad):
        return {s for s in self._enemy_squads(squad) if squad.min_distance_to(s) <= _reach(squad)}

    def _objectives_within(self, squad):
        return [
            obj for obj in self.objectives
            if any(obj.terrain_area.distance_to_model(m) <= _reach(squad) for m in squad.models)
        ]

    def start_consolidate(self, squad):
        if not self.can_consolidate(squad) or self.movement_controller is None:
            return
        if self.movement_controller.selected_squad is not squad:
            return
        mode = self.determine_mode(squad)
        if mode is None:
            return
        if mode == ONGOING:
            targets = self.ongoing_targets(squad)
            self.movement_controller.start_consolidate_move(_reach(squad), targets, ONGOING)
        elif mode == ENGAGING:
            self.active_squad = squad
            self.targets = []
            self.state = CHOOSING_ENGAGING_TARGETS
        else:  # OBJECTIVE
            objectives = self._objectives_within(squad)
            if len(objectives) == 1:
                self._begin_objective_move(squad, objectives[0])
            else:
                self.active_squad = squad
                self.state = CHOOSING_OBJECTIVE

    def toggle_engaging_target(self, enemy_squad):
        if self.state != CHOOSING_ENGAGING_TARGETS or enemy_squad not in self.eligible_engaging_targets(self.active_squad):
            return
        if enemy_squad in self.targets:
            self.targets.remove(enemy_squad)
        else:
            self.targets.append(enemy_squad)

    def begin_engaging_move(self):
        if self.state != CHOOSING_ENGAGING_TARGETS or not self.targets or self.movement_controller is None:
            return
        if self.movement_controller.selected_squad is not self.active_squad:
            return
        self.movement_controller.start_consolidate_move(_reach(self.active_squad), list(self.targets), ENGAGING)
        self.state = IDLE

    def can_switch_to_objective(self):
        """Whether "move to an objective instead" is available right now -
        user report: "kann mich entscheiden in eine andere Einheit
        reinzuconsolidaten, aber mir fehlt die Entscheidung das nicht zu
        tun und mich stattdessen auf ein Objective zu bewegen".
        determine_mode()'s Ongoing > Engaging > Objective priority order
        (straight from the user-supplied rule text) still decides which
        mode is offered FIRST when a squad qualifies for more than one -
        this doesn't change that default, it just means qualifying for
        Engaging doesn't make Objective Consolidation unreachable when the
        squad happens to qualify for both. Only offered while still
        choosing Engaging targets (no move made yet) and only if an
        objective is actually within range too."""
        return self.state == CHOOSING_ENGAGING_TARGETS and bool(self._objectives_within(self.active_squad))

    def switch_to_objective_consolidation(self):
        """The escape hatch itself: abandons the Engaging-mode target
        selection (nothing committed yet - no move has started) and
        proceeds exactly as if determine_mode() had returned OBJECTIVE to
        begin with (auto-picks a sole candidate, otherwise opens
        CHOOSING_OBJECTIVE - same as start_consolidate()'s own OBJECTIVE
        branch)."""
        if not self.can_switch_to_objective():
            return
        squad = self.active_squad
        self.targets = []
        objectives = self._objectives_within(squad)
        if len(objectives) == 1:
            self._begin_objective_move(squad, objectives[0])
        else:
            self.state = CHOOSING_OBJECTIVE

    def choosable_objectives(self):
        if self.state != CHOOSING_OBJECTIVE or self.active_squad is None:
            return []
        return self._objectives_within(self.active_squad)

    def choose_objective(self, objective):
        if self.state != CHOOSING_OBJECTIVE or objective not in self.choosable_objectives():
            return
        self._begin_objective_move(self.active_squad, objective)

    def _begin_objective_move(self, squad, objective):
        if self.movement_controller is None or self.movement_controller.selected_squad is not squad:
            self.active_squad = None
            self.state = IDLE
            return
        self.movement_controller.start_consolidate_move(_reach(squad), [objective], OBJECTIVE)
        self.active_squad = None
        self.state = IDLE

    def decline_consolidate(self):
        """Optional move - abandon without consuming the unit's allowance."""
        if self.movement_controller is not None and self.movement_controller.move_mode == "consolidate":
            self.movement_controller.cancel_move()
        self.active_squad = None
        self.targets = []
        self.state = IDLE

    def confirm_consolidate(self):
        """Wraps MovementController.confirm_move(): only consumes the
        squad's one consolidation move once actually confirmed, and - for
        Engaging Consolidation - forces any newly-engaged enemy unit that
        hasn't fought yet to fight immediately (rule 12.08)."""
        if self.movement_controller is None:
            return
        squad = self.movement_controller.selected_squad
        mode = self.movement_controller.consolidate_mode
        targets = list(self.movement_controller.consolidate_targets)
        self.movement_controller.confirm_move()
        if self.movement_controller.errors:
            return

        if squad is not None:
            self.consolidated_squad_ids.add(squad)
            if mode == ENGAGING and self.fight_controller is not None:
                for enemy_squad in self._enemy_squads(squad):
                    if squad.is_engaged_with(enemy_squad) and enemy_squad not in self.fight_controller.fought_squad_ids:
                        self.fight_controller.force_fight(enemy_squad)

        self.active_squad = None
        self.targets = []
        self.state = IDLE
