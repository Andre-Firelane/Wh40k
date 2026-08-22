"""T'au Empire detachment stratagem: Retaliation Cadre's The Shortened Blade,
as supplied by the user (not a rule from the generic 40k core rulebook, so it
lives in its own module - same reasoning as game/retaliation_cadre.py for that
detachment's Bonded Heroes rule, and its two sibling stratagems in
game/stim_injectors.py and game/arrokon_protocol.py).

RULE (The Shortened Blade, 2CP, Retaliation Cadre Strategic Ploy Stratagem):
  WHEN:         Your Movement phase.
  TARGET:       One T'AU EMPIRE BATTLESUIT unit from your army that is
                arriving using the Deep Strike ability this phase.
  EFFECT:       Your unit can be set up anywhere on the battlefield that is
                more than 6" horizontally away from all enemy models.
  RESTRICTIONS: A unit targeted with this Stratagem is not eligible to
                declare a charge in the same turn.

WHAT IT ACTUALLY CHANGES

Only one number. The TARGET clause already restricts this to a unit arriving
by [DEEP STRIKE] (24.09), and game/ingress.py already waives both of the
normal Ingress move's placement constraints for such a unit - "wholly within
6" of a battlefield edge" and, before the third battle round, "not within
your opponent's deployment zone". So "anywhere on the battlefield" is already
true for the target, and the whole effect is 8" -> 6" on the distance to
enemy models.

"more than 6" HORIZONTALLY" is the full distance here: the board is flat
(no verticality is modelled - see CLAUDE.md's Später-Liste), so horizontal
distance and distance are the same measurement.

Modelled as an override on the CURRENT ingress rather than a flag on the
squad, exactly like IngressController.homing_beacon_bearer: both are "this
one arrival uses a different placement rule", both have to be armed while the
placement is still open so the green/red overlay and the drag clamp agree
with it, and both are cleared the moment that arrival is confirmed or
cancelled. Nothing about it outlives the placement - except the RESTRICTIONS
clause, which is a property of the unit for the rest of the turn and
therefore does land on the Squad (charge_locked_until_end_of_turn, the
already-existing field rules 18.04/18.05 use for their own no-charge lock and
that main.py already clears at end of turn).

SIMPLIFICATION (documented, matching game/retaliation_cadre.py's own note):
this engine has no army-building/detachment-selection flow yet, and
Retaliation Cadre is currently the only detachment that exists - the T'AU
EMPIRE half of the TARGET clause is therefore not checked, exactly as Bonded
Heroes applies unconditionally to any BATTLESUIT model. The BATTLESUIT half
IS checked, via is_battlesuit_unit()'s rule 19.03 keyword pooling, and so is
the [DEEP STRIKE] half.
"""

# The distance itself lives in game/ingress.py, next to the 8" it replaces and
# beside the code that enforces it - one definition, and this direction of the
# import is the one that doesn't cycle.
from game.ingress import INGRESS_MIN_ENEMY_DISTANCE_IN, SHORTENED_BLADE_MIN_ENEMY_DISTANCE_IN
from game.retaliation_cadre import is_battlesuit_unit
from game.stratagems import Stratagem
from game.turn import PHASE_MOVEMENT

SHORTENED_BLADE_CP_COST = 2


class ShortenedBladeController:
    """WHEN/TARGET bookkeeping and the two things using it does: arm the
    relaxed placement distance on the ingress that is currently open, and
    apply the RESTRICTIONS clause to the unit.

    Proactive and human-driven, like The Arro'kon Protocol - the active
    player picks the moment, so there is nothing to interrupt and no
    relevance gate to build. can_use() is just the printed clauses."""

    def __init__(self, stratagem_controller, ingress_controller=None, setup_controller=None,
                 turn_tracker=None, game_log=None):
        self.stratagem_controller = stratagem_controller
        self.ingress_controller = ingress_controller
        self.setup_controller = setup_controller
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self._stratagem = Stratagem(
            name="The Shortened Blade", cp_cost=SHORTENED_BLADE_CP_COST, effect=self._apply,
        )

    def can_use(self, squad):
        if squad is None or self.ingress_controller is None:
            return False
        if self.turn_tracker is not None:
            # WHEN: "Your Movement phase" - the user's own, not the opponent's.
            # Note this also covers Rapid Ingress (15.07), which arrives during
            # the OPPONENT's Movement phase: the turn tracker's active player is
            # then the opponent, so this correctly refuses.
            if self.turn_tracker.phase != PHASE_MOVEMENT:
                return False
            if squad.owner != self.turn_tracker.active_player:
                return False
        # TARGET: "arriving using the Deep Strike ability this phase" - i.e.
        # its placement is open right now. Asked of the controller that owns
        # that fact rather than re-derived, and _has_deep_strike() is 24.09's
        # own "every model in the unit has this ability" reading.
        if not self.ingress_controller.is_ingressing(squad):
            return False
        if not self.ingress_controller.deep_striking(squad):
            return False
        if self.ingress_controller.shortened_blade_squad is squad:
            return False  # already armed for this arrival
        if not is_battlesuit_unit(squad):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _apply(self, controller, player, targets):
        squad = targets[0]
        self.ingress_controller.shortened_blade_squad = squad
        # RESTRICTIONS: "not eligible to declare a charge in the same turn".
        # The same field rules 18.04/18.05 already use for their own no-charge
        # lock, so ChargeController.can_declare_charge() needs no new case and
        # main.py's end-of-turn cleanup already clears it.
        squad.charge_locked_until_end_of_turn = True
        # The overlay caches its legality mask per placement, and the answer
        # this stratagem changes is exactly what that mask holds - without
        # this, the board would keep painting the 8" ring until the placement
        # restarted. See SetupController.placement_generation.
        if self.setup_controller is not None:
            self.setup_controller.invalidate_placement()
        if self.game_log is not None:
            self.game_log.add(
                f"{player}: The Shortened Blade - {squad.name} can arrive more than "
                f'{SHORTENED_BLADE_MIN_ENEMY_DISTANCE_IN:.0f}" from all enemy models '
                f'instead of {INGRESS_MIN_ENEMY_DISTANCE_IN:.0f}", and cannot declare a charge this turn.'
            )
