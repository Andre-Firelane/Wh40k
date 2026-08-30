"""The Vespid Strain Leader's "Oversight Drone".

RULE (printed, word for word):
  "Once per battle, when the bearer's unit is selected to shoot, until the end
   of the phase, ranged weapons equipped by models in this unit have the
   [IGNORES COVER] ability."
  Designer's Note: "Place an Oversight Drone token next to the bearer, removing
  it once this ability has been used."

RIPTIDE'S NOVA CHARGE IN ANOTHER FACTION'S TYPEFACE - once per battle, offered
at exactly the moment the unit is selected to shoot, granting a weapon keyword
for the phase. So it follows game/nova_charge.py: a collaborator handed to
ShootingController and offered from start_shooting() only, never from anywhere
in the middle of a sequence.

THREE THINGS WORTH NOT GETTING WRONG:

  * "ONCE PER BATTLE" is per BEARER, not per army and not per phase, so the
    ledger is keyed on the model and nothing ever clears it. The Designer's
    Note's token is exactly that ledger.
  * "UNTIL THE END OF THE PHASE" - a phase, not a turn. The grant is cleared on
    the shooting phase boundary, which is also where every other phase-scoped
    grant in this engine is cleared.
  * "RANGED WEAPONS EQUIPPED BY MODELS IN THIS UNIT" - the whole unit, not the
    bearer, so a chain entry keyed on the SQUAD, and the grant survives the
    Strain Leader's death within the phase (nothing in the text ties the effect
    to him still standing once it has been used).

"ONCE PER BATTLE" AND NOT "YOU CAN" TOGETHER: the text has no "you can", but a
once-per-battle resource spent automatically the first time the unit shoots
would be spent on whatever it happened to shoot at first. So it IS offered -
the same reading Nova Charge takes of the same shape, and the same reason.
"""

import copy

from game.weapons import MELEE

OVERSIGHT_DRONE_LABEL = "Oversight Drone"


def bearers(squad):
    """Living models in this unit carrying an unspent drone."""
    if squad is None:
        return []
    return [m for m in getattr(squad, "models", ()) or ()
            if not m.is_dead() and getattr(m.profile, "oversight_drone", False)]


def adjusted_weapon(weapon, squad):
    """[IGNORES COVER] on this unit's ranged weapons while the grant is up."""
    if weapon is None or getattr(weapon, "ignores_cover", False):
        return weapon
    if getattr(weapon, "weapon_type", None) == MELEE:
        return weapon
    if not getattr(squad, "oversight_drone_active", False):
        return weapon
    granted = copy.copy(weapon)
    granted.ignores_cover = True
    return granted


class OversightDroneController:
    """Offered from ShootingController.start_shooting(), like Nova Charge."""

    def __init__(self, decision_manager=None, game_log=None, auto_players=()):
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = set(auto_players)
        self._used = set()   # id(model) of drones already spent - never cleared

    def can_use(self, squad):
        if squad is None or getattr(squad, "oversight_drone_active", False):
            return False
        return any(id(m) not in self._used for m in bearers(squad))

    def offer(self, squad):
        """Returns True if a decision is now pending (or the grant was taken
        outright), which is the contract start_shooting() expects."""
        if not self.can_use(squad):
            return False
        if squad.owner in self.auto_players or self.decision_manager is None:
            # Deterministic for the AI: a once-per-battle keyword is worth
            # spending the first time the unit shoots at all, since a Vespid
            # unit that has been selected to shoot has already committed.
            return self.use(squad)
        self.decision_manager.request(
            squad.owner,
            f"{squad.name}: Oversight Drone - grant [IGNORES COVER] for this phase? "
            f"(once per battle)",
            [("Use the Oversight Drone", lambda: self.use(squad)), ("Save it", lambda: None)],
        )
        return True

    def use(self, squad):
        model = next((m for m in bearers(squad) if id(m) not in self._used), None)
        if model is None:
            return False
        self._used.add(id(model))
        squad.oversight_drone_active = True
        if self.game_log:
            self.game_log.add(
                f"{squad.name} uses its Oversight Drone: ranged weapons ignore cover "
                f"this phase.")
        return True

    def reset_phase(self, squads):
        """"Until the end of the phase" - the grant only, never the ledger."""
        for squad in squads or ():
            squad.oversight_drone_active = False


def oversight_drone_gear(model_line_name):
    """The Strain Leader's own drone. A Gear item so that a build can decline
    it, and because the printed option is conditional on the 10-model unit -
    which the datasheet expresses through its own gear_slots rather than here.

    The effect only marks the BEARER; the once-per-battle ledger and the phase
    grant both live on OversightDroneController, because a Gear effect runs at
    build time and this ability is spent during the battle."""
    from game.factions import Gear

    def effect(token):
        token.profile.oversight_drone = True

    return Gear(model_line_name, "Oversight Drone", effect, max_count=1)
