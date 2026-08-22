"""Asurmen's "Tactical Acumen" - a datasheet ability, so its own module.

RULE (printed, word for word):
  "While this model is leading a unit, in your Shooting phase, after that unit
  has shot, it can make a Normal move of up to 6". If it does, until the end of
  the turn, that unit is not eligible to declare a charge."

ALREADY-BUILT MACHINERY, TWICE OVER
-----------------------------------
This is Retaliation Cadre's The Torchstar Gambit with three differences: it
costs no CP, its distance is a flat 6" rather than the unit's M
characteristic, and it needs Asurmen to be leading the unit rather than a
keyword. Everything else - a Normal move in the Shooting phase, the "if it
does" charge lock, the Confirm button routed through the granting controller -
is that stratagem's shape, so:

  * the TRIGGER is ShootingController.on_squad_finished_shooting, whose
    "after that unit has shot" is word for word this clause. Fourth consumer
    of that list, after Suppression Volley, Fade Back and Fire Support.
  * the MOVE is MovementController.start_post_shooting_move(), generalised
    from start_torchstar_move() precisely because this is its second caller -
    the distance became a parameter and the move_mode stayed per-ability,
    since the mode is what routes Confirm to the controller that owns the
    consequence.
  * the CONSEQUENCE is Squad.charge_locked_until_end_of_turn, which rules
    18.04/18.05, The Shortened Blade and Flickerjump already use, and which
    main.py already clears at end of turn.

"IF IT DOES" IS CONDITIONAL ON THE MOVE, so the lock is set at CONFIRM, not
when the ability is taken - a cancelled move costs nothing. Exactly the
distinction The Torchstar Gambit's own confirm_move() draws, and the opposite
of The Shortened Blade, whose RESTRICTIONS clause is unconditional.

WHILE THIS MODEL IS LEADING A UNIT (19.01): read off the attached unit's own
components, so a lone Asurmen - who leads nobody - grants nothing, and the
ability ends with him.
"""

from game import attached_units

TACTICAL_ACUMEN_MOVE_IN = 6.0


def unit_has_asurmen(squad):
    """Whether this unit is being LED by a model with the ability.

    attached_units.leader_ability() is the 19.04-correct lookup: it requires a
    real attached unit (a lone character leads nobody) and it reads the ability
    off the leader COMPONENT, so it ends when he dies - and it brings 19.04's
    own grace window with it. unit_wide_ability() would be not merely
    imprecise here but always false: no Dire Avenger prints this."""
    return attached_units.leader_ability(squad, "tactical_acumen")


class TacticalAcumenController:
    """The offer after shooting, and the charge lock on confirm.

    Human-only in practice like the rest of the Aeldari work, but it is an
    ordinary DecisionManager break point, so an AI would resolve it through the
    generic path with nothing extra here."""

    def __init__(self, movement_controller=None, decision_manager=None, game_log=None):
        self.movement_controller = movement_controller
        self.decision_manager = decision_manager
        self.game_log = game_log
        self._moving_squad = None

    def _log(self, message, **kwargs):
        if self.game_log is not None:
            self.game_log.add(message, **kwargs)

    @property
    def is_moving(self):
        return self._moving_squad is not None

    def can_use(self, squad):
        if squad is None or not unit_has_asurmen(squad):
            return False
        if self.movement_controller is None or self._moving_squad is not None:
            return False
        return True

    def offer_after_shooting(self, squad, hit_squads):
        """Wired into ShootingController.on_squad_finished_shooting.

        `hit_squads` is unused: this clause triggers on having SHOT, not on
        having hit anything - unlike Fire Support, which shares the hook and
        does care."""
        if not self.can_use(squad) or self.decision_manager is None:
            return
        self.decision_manager.request(
            squad.owner,
            f'{squad.name}: Tactical Acumen - make a Normal move of up to '
            f'{TACTICAL_ACUMEN_MOVE_IN:g}"? It cannot declare a charge this turn if it does.',
            [("Make the move", lambda: self._start(squad)), ("Stay put", lambda: None)],
        )

    def _start(self, squad):
        self.movement_controller.select(squad.models[0])
        if self.movement_controller.selected_squad is not squad:
            return
        self.movement_controller.start_post_shooting_move(
            squad, move_mode="tactical_acumen", max_distance=TACTICAL_ACUMEN_MOVE_IN,
        )
        self._moving_squad = squad
        self._log(f"{squad.name} uses Tactical Acumen: a Normal move of up to "
                  f"{TACTICAL_ACUMEN_MOVE_IN:g}\".")

    def confirm_move(self):
        """"If it does" - so the charge lock is set only once the move has
        actually been made. confirm_move() clears move_mode on success and
        leaves it set on failure, which is how that is read (the same way
        IngressController.confirm_ingress() reads its own)."""
        if self.movement_controller is None or self._moving_squad is None:
            return
        squad = self._moving_squad
        self.movement_controller.confirm_move()
        if self.movement_controller.move_mode is None:
            squad.charge_locked_until_end_of_turn = True
            self._moving_squad = None
            self._log(f"{squad.name} moved with Tactical Acumen and cannot declare a charge this turn.")

    def cancel_move(self):
        if self.movement_controller is None or self._moving_squad is None:
            return
        self.movement_controller.cancel_move()
        self._moving_squad = None
