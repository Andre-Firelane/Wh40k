"""Boyz' Ammo Runts (2026-09 Ork codex).

RULE (verbatim, rules/orks/Boyz.md):
  "Ammo Runts (Once per battle, per unit): In your Shooting phase, when this
   unit is selected to shoot, you can use this ability. If you do, this unit's
   ranged attacks have +1 to hit rolls."

NOT game/ammo_runt.py. That module is the Flash Gitz' pre-codex WARGEAR item
(one Runt on one model, [LETHAL HITS]); this is a unit ABILITY with a different
effect. Two modules because they are two rules - the shared word is flavour.

WHERE IT HANGS: "when this unit is selected to shoot" is
ShootingController.start_shooting(), the instant Nova Charge and the Flash
Gitz' Ammo Runt are already offered at. "In YOUR Shooting phase" is read off
the live clock, and that is right here: this is a start-of-activation offer,
not an end-of-phase one (game/phase_window.py does not apply). A reactive
shot in the opponent's turn therefore gets no offer.

THE GRANT is a Hit-roll Modifier (-1 on the threshold, this engine's sign
convention) read by shooting.py's _hit_modifiers(), for the phase. The
once-per-battle SPEND and the phase GRANT are two Squad flags in
activation_state.SQUAD_FLAGS, so a save keeps both.

"You can use this ability" is a real choice for a human (a once-per-battle
resource). The AI uses it at its first opportunity (auto_players), 0 API calls.
"""

from game import ai_mode
from game.modifiers import Modifier
from game.squad import unit_wide_ability
from game.turn import PHASE_SHOOTING

AMMO_RUNTS_NAME = "Ammo Runts"
#: "+1 to hit rolls" - a bonus, so -1 on the threshold.
AMMO_RUNTS_HIT_BONUS = 1


def has_ability(squad):
    return squad is not None and bool(unit_wide_ability(squad, "ammo_runts"))


def is_active(squad):
    return bool(getattr(squad, "ammo_runts_active", False))


def hit_modifiers(squad):
    """The Modifier shooting.py's _hit_modifiers() appends while the grant is up."""
    if not is_active(squad):
        return []
    return [Modifier(-AMMO_RUNTS_HIT_BONUS, AMMO_RUNTS_NAME)]


def reset_phase(squads=()):
    """"Until the end of the phase" is implicit in "this unit's ranged attacks"
    for the activation it was used in. The once-per-battle spend survives."""
    for squad in squads or ():
        if getattr(squad, "ammo_runts_active", False):
            squad.ammo_runts_active = False


class AmmoRuntsController:
    def __init__(self, decision_manager=None, turn_tracker=None, game_log=None, auto_players=()):
        self.decision_manager = decision_manager
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)

    def why_not(self, squad):
        """None when the ability may be used right now, else the reason."""
        if squad is None:
            return "no unit"
        if not has_ability(squad):
            return "this unit has no Ammo Runts"
        if getattr(squad, "ammo_runts_used", False):
            return "already used this battle"
        if is_active(squad):
            return "already in use"
        tt = self.turn_tracker
        if tt is not None and (tt.phase != PHASE_SHOOTING or squad.owner != tt.turn_owner):
            return "not your Shooting phase"
        return None

    def can_use(self, squad):
        return self.why_not(squad) is None

    def offer(self, squad):
        """Called from start_shooting(). True when it did something (used it
        for an auto player, or opened the prompt)."""
        if not self.can_use(squad):
            return False
        if squad.owner in self.auto_players:
            return self.use(squad)
        if self.decision_manager is None:
            return False
        self.decision_manager.request(
            squad.owner,
            f"{squad.name}: {AMMO_RUNTS_NAME} (once per battle) - +1 to hit rolls "
            f"for this unit's ranged attacks this phase?",
            [
                ("Use Ammo Runts", lambda s=squad: self.use(s)),
                ("Save it for later", lambda: None),
            ],
        )
        return True

    def use(self, squad):
        if not self.can_use(squad):
            return False
        squad.ammo_runts_used = True
        squad.ammo_runts_active = True
        if self.game_log is not None:
            self.game_log.add(f"{squad.name} uses {AMMO_RUNTS_NAME}: +1 to hit rolls for its "
                              "ranged attacks this phase.")
        return True

    def reset_phase(self, squads=()):
        reset_phase(squads)
