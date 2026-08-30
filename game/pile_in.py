from game import battle_focus
from game.turn import PHASE_FIGHT

PILE_IN_RANGE_IN = 3.0
PILE_IN_TARGET_RANGE_IN = 5.0


class PileInController:
    """Rule 12.02/12.03: during the Fight phase, both players can pile in
    with each of their eligible units once. Pile-in targets aren't really a
    player choice in practice: an engaged unit's targets are every enemy
    unit it's already engaged with (mandatory, not optional per the rule
    text) - the "1+ enemy units within 5"" branch only matters for a unit
    that's unengaged when piling in, which can't happen yet in our engine
    (Charge always ends engaged, and we haven't wired the Overrun Fight
    12.06 case that would allow it - see CLAUDE.md)."""

    def __init__(self, game_log=None, turn_tracker=None, all_tokens=None, movement_controller=None):
        self.game_log = game_log
        self.turn_tracker = turn_tracker
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.movement_controller = movement_controller
        self.piled_in_squad_ids = set()

    def reset_fight_phase(self):
        """Rule 12.02: a new Fight phase comes around every battle round."""
        self.piled_in_squad_ids = set()

    def _all_squads(self):
        return {token.squad for token in self.all_tokens if token.squad is not None}

    def _enemy_squads(self, squad):
        return {
            token.squad for token in self.all_tokens
            if token.squad is not None and token.squad.owner != squad.owner
        }

    def _pending(self, player=None):
        """Every squad (of `player`, or of anyone) that still owes a pile-in.
        A generator, so has_pending_squads() below keeps its short-circuit -
        one filter, two questions, rather than two copies that could drift."""
        return (
            squad for squad in self._all_squads()
            if (player is None or squad.owner == player) and self.can_pile_in(squad)
        )

    def has_pending_squads(self):
        """Rule 12.04: the Fight step can't begin until every unit eligible
        to pile in has done so (or explicitly skipped it, see
        skip_pile_in()) - both players resolve Pile In first, before either
        one starts selecting units to fight."""
        return any(self._pending())

    def squads_pending_pile_in(self, player=None):
        """The same question as has_pending_squads(), answered with the
        units themselves. Sorted by name, because _all_squads() is a SET and
        the caller prints these: unsorted, the list would reorder itself
        frame to frame.

        Exists for game/ui/action_panel.py - user: "ich finde es manchmal
        schwierig zu erkennen, dass ich noch mit allen einheiten pile in
        machen muss, bevor die KI weitermacht". The panel used to print one
        generic sentence ("Both players must resolve Pile In...") that named
        no unit and no side, so a game waiting on the human looked exactly
        like a game waiting on the AI."""
        return sorted(self._pending(player), key=lambda s: s.name)

    def skip_pile_in(self, squad):
        """Rule 12.03: piling in is optional ('can pile in'), not
        mandatory - this lets a player pass on an eligible unit's pile-in
        without moving it, so it stops blocking the Fight step from
        starting."""
        if not self.can_pile_in(squad):
            return
        self.piled_in_squad_ids.add(squad)

    def can_pile_in(self, squad):
        """Rule 12.03 eligibility: engaged, or made a charge move this turn
        (approximated via Squad.fights_first, which is only ever set by a
        successful charge move)."""
        if squad is None or squad in self.piled_in_squad_ids:
            return False
        if self.turn_tracker is not None and self.turn_tracker.phase != PHASE_FIGHT:
            return False
        return squad.is_engaged(self.all_tokens) or squad.fights_first

    def pile_in_targets(self, squad):
        """Rule 12.03 BEFORE MOVING."""
        if squad.is_engaged(self.all_tokens):
            return [s for s in self._enemy_squads(squad) if squad.is_engaged_with(s)]
        return [s for s in self._enemy_squads(squad) if squad.min_distance_to(s) <= PILE_IN_TARGET_RANGE_IN]

    def start_pile_in(self, squad):
        if not self.can_pile_in(squad) or self.movement_controller is None:
            return
        if self.movement_controller.selected_squad is not squad:
            return
        targets = self.pile_in_targets(squad)
        if not targets:
            return
        # Sudden Strike (Aeldari Battle Focus) can raise this to 6". Applied to
        # the MOVE distance only - PILE_IN_TARGET_RANGE_IN above is rule 12.03's
        # own BEFORE MOVING target range, a separate number this manoeuvre says
        # nothing about.
        reach = battle_focus.melee_move_range_in(squad, PILE_IN_RANGE_IN)
        self.movement_controller.start_pile_in_move(reach, targets)

    def confirm_pile_in(self):
        """Wraps MovementController.confirm_move(): only consumes the
        squad's one pile-in move once it's actually confirmed without
        errors - a rejected move stays in progress so the player can
        reposition, exactly like a normal move."""
        if self.movement_controller is None:
            return
        squad = self.movement_controller.selected_squad
        self.movement_controller.confirm_move()
        if self.movement_controller.errors:
            return
        if squad is not None:
            self.piled_in_squad_ids.add(squad)

    def decline_pile_in(self):
        """Abandon a pile-in move in progress. Unlike a charge, an aborted
        pile-in attempt doesn't consume the unit's pile-in for this step -
        no move was actually made, so it can still try again."""
        if self.movement_controller is not None and self.movement_controller.move_mode == "pile_in":
            self.movement_controller.cancel_move()
