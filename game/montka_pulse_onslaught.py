"""Mont'ka Stratagem: Pulse Onslaught (2CP), and the `shaken` status.

RULE (verbatim, rules/tau_empire/detachments/Mont'ka.md):
  WHEN:   Your Shooting phase.
  TARGET: One T'AU EMPIRE INFANTRY unit (excluding KROOT units) from your army
          that has just shot, and one enemy unit (excluding MONSTERS and
          VEHICLES) hit by one or more of those attacks.
  EFFECT: Until the end of your opponent's next turn, that enemy unit is
          shaken. While a unit is shaken, subtract 2 from its Move
          characteristic and subtract 2 from Advance and Charge rolls made
          for it.

SHAKEN IS A STATUS, AND ITS THREE EFFECTS SIT AT THREE SEAMS
-------------------------------------------------------------
  * -2 Move          -> game/coldstar.py's effective_movement_in(), the one
                        place a model's Move characteristic is decided.
  * -2 Advance roll  -> the Advance roll's own total.
  * -2 Charge roll   -> game/charge.py's _capped_roll(), the charger-side
                        total Neocapacitor Shields and Photon Grenades already
                        share.

Three seams because the rulebook has three, not because the status is spread
out: `is_shaken()` is the single question all three ask.

"UNTIL THE END OF YOUR OPPONENT'S NEXT TURN" is longer than anything else in
this detachment, and it is NOT "until the end of the turn". It is stored as the
turn it expires after, so a phase or turn boundary cannot shorten it by
accident - the mistake a flag cleared in the usual end-of-turn block would make.
"""

from game import montka, tau_detachments
from game.attached_units import unit_has_datasheet_keyword
from game.stratagems import Stratagem
from game.turn import PHASE_SHOOTING

PULSE_ONSLAUGHT_CP = 2
PULSE_ONSLAUGHT_NAME = "Pulse Onslaught"
SHAKEN_PENALTY = 2
KROOT_KEYWORD = "KROOT"


def is_shaken(squad):
    """The one question the three effects ask."""
    return bool(getattr(squad, "shaken_until_turn", None) is not None)


def move_penalty_for(squad):
    """-2 to the Move characteristic, read by effective_movement_in()."""
    return SHAKEN_PENALTY if is_shaken(squad) else 0


def roll_penalty_for(squad):
    """-2 on Advance and Charge rolls made for this unit."""
    return SHAKEN_PENALTY if is_shaken(squad) else 0


def can_be_shaken(squad):
    """"one enemy unit (excluding MONSTERS and VEHICLES)"."""
    if squad is None:
        return False
    return not any(m.profile.monster or m.profile.vehicle
                   for m in squad.models if not m.is_dead())


def is_eligible_shooter(squad):
    """"One T'AU EMPIRE INFANTRY unit (excluding KROOT units)"."""
    if squad is None or not tau_detachments.is_tau_unit(squad):
        return False
    if unit_has_datasheet_keyword(squad, KROOT_KEYWORD):
        return False
    alive = [m for m in squad.models if not m.is_dead()]
    return bool(alive) and all(m.profile.infantry for m in alive)


class PulseOnslaughtController:
    def __init__(self, stratagem_controller, turn_tracker=None,
                 decision_manager=None, game_log=None, auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = tuple(auto_players)
        self._pending = None
        self._stratagem = Stratagem(
            name=PULSE_ONSLAUGHT_NAME, cp_cost=PULSE_ONSLAUGHT_CP, effect=self._shake,
        )

    def expire(self, squads=()):
        """Clear a shaken mark once its own deadline has passed.

        Compares against the CURRENT turn number rather than clearing on a
        boundary, which is what makes "until the end of your opponent's NEXT
        turn" survive the two boundaries in between."""
        if self.turn_tracker is None:
            return
        for squad in squads or ():
            until = getattr(squad, "shaken_until_turn", None)
            if until is None:
                continue
            if self.turn_tracker.turn_number_for(squad.owner) > until:
                squad.shaken_until_turn = None
                if self.game_log is not None:
                    self.game_log.add(f"{squad.name} is no longer shaken.")

    def offer_after_shooting(self, squad, hit_squads):
        """Wired into ShootingController.on_squad_finished_shooting - "a unit
        that has just shot, and one enemy unit hit by those attacks", which is
        exactly this hook's two arguments."""
        if self.turn_tracker is not None and self.turn_tracker.phase != PHASE_SHOOTING:
            return False
        if not tau_detachments.has_detachment(getattr(squad, "owner", None), montka.SETTING):
            return False
        if not is_eligible_shooter(squad):
            return False
        candidates = sorted(
            (t for t in (hit_squads or ()) if t is not None and can_be_shaken(t)
             and any(not m.is_dead() for m in t.models)),
            key=lambda s: s.name)
        if not candidates:
            return False
        if not self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad]):
            return False
        if squad.owner in self.auto_players or self.decision_manager is None:
            return False
        self.decision_manager.request(
            squad.owner,
            f"{PULSE_ONSLAUGHT_NAME} ({PULSE_ONSLAUGHT_CP} CP): shake one unit "
            f"{squad.name} hit (-{SHAKEN_PENALTY}\" Move, -{SHAKEN_PENALTY} Advance and "
            "Charge rolls, until the end of your opponent's next turn)?",
            [(target.name, (lambda t=target: self._accept(squad, t)))
             for target in candidates]
            + [("Decline", lambda: None)],
        )
        return True

    def _accept(self, shooter, target):
        self._pending = target
        used = self.stratagem_controller.use(shooter.owner, self._stratagem, [shooter])
        if not used:
            self._pending = None
        return used

    def _shake(self, controller, player, targets):
        target, self._pending = self._pending, None
        if target is None or self.turn_tracker is None:
            return
        # "the end of your opponent's NEXT turn" - the victim's own next turn,
        # counted in their turn numbers, which is what expire() compares to.
        target.shaken_until_turn = self.turn_tracker.turn_number_for(target.owner) + 1
        if self.game_log is not None:
            self.game_log.add(
                f"{PULSE_ONSLAUGHT_NAME}: {target.name} is shaken "
                f"(-{SHAKEN_PENALTY}\" Move, -{SHAKEN_PENALTY} Advance and Charge rolls) "
                "until the end of its next turn."
            )
