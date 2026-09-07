"""Windrider Host Stratagem: Spiralling Evasion (1CP, Battle Tactic).

RULE (verbatim, rules/aeldari/detachments/Windrider Host.md):
  WHEN:   Your opponent's Shooting phase, just after an enemy unit has selected
          its targets.
  TARGET: One ASURYANI MOUNTED or VYPER unit from your army that was selected
          as the target of one or more of the attacking unit's attacks.
  EFFECT: Until the end of the phase, models in your unit have a 4+
          invulnerable save.
  RESTRICTIONS: none printed.

A REACTIVE STRATAGEM, so it joins ShootingController.target_reactions and
implements maybe_offer(attacker, target, melee=False). THE ARGUMENT ORDER IS
THE LIST'S, NOT THE STRATAGEM'S: the unit this protects is the TARGET, the
second argument - reading them the other way round produces a module that
offers itself to the shooter, which looks plausible from inside and is wrong
at every use.

SHOOTING ONLY, and printed so: "your opponent's SHOOTING phase". It is
therefore NOT registered in fight_target_reactions, which is where the same
protocol would otherwise carry it into melee. Pinned as an absence, since a
reaction that is merely never triggered looks identical to one that is
correctly excluded.

THE GRANT IS A SQUAD FLAG READ BY game/invulnerable_save.py, which is the one
place a Save roll asks what invulnerable save a model has - and which already
composes every source with "take whichever is BETTER, never make an existing
one worse" (rule 05.04's own arithmetic). That matters here rather than being
boilerplate: a Shining Spears Exarch with a Shimmershield already has a 4+,
and a Windrider has none at all, so the same 1CP buys a great deal for one
unit and exactly nothing for another. Composing through _better() rather than
assigning means the first case cannot be made worse by the purchase.

game/damage_estimate.py reads UnitProfile.invulnerable_save DIRECTLY and so
sees none of these grants - the known gap that module's own docstring records
for the Waaagh! and Serpent Shield. This adds a third source to it rather than
a new problem, and is named here so it is not re-discovered as one.

UNTIL THE END OF THE PHASE, not until the attack resolves: a unit that buys
this against the first shooter keeps the save against every later one in the
same phase, which is what makes it worth a CP at all.

ONE OFFER PER (attacker, target) PAIR PER PHASE. Split Fire's per-assignment
hook reaches target_reactions once per weapon group, so without the memo the
same question would be asked several times for one selection - the same memo
every other reactive Stratagem in this batch carries.

THE AI DECLINES (standing Aeldari instruction).
"""

from game import ai_mode, ride_the_wind
from game.stratagems import Stratagem
from game.turn import PHASE_SHOOTING

SPIRALLING_EVASION_NAME = "Spiralling Evasion"
SPIRALLING_EVASION_CP = 1

#: "models in your unit have a 4+ invulnerable save".
SPIRALLING_EVASION_SAVE = "4+"


def is_active(squad):
    return bool(getattr(squad, "spiralling_evasion_active", False))


def invulnerable_save_for(squad):
    """Read by game/invulnerable_save.py's fold. None means "no grant", which
    is what every other source there returns when it does not apply."""
    return SPIRALLING_EVASION_SAVE if is_active(squad) else None


def eligible_unit(squad):
    """"One ASURYANI MOUNTED or VYPER unit from your army"."""
    if squad is None or not ride_the_wind.has_detachment(getattr(squad, "owner", None)):
        return False
    return ride_the_wind.applies(squad)


def reset_phase(squads=()):
    for squad in squads or ():
        if squad is not None:
            squad.spiralling_evasion_active = False


class SpirallingEvasionController:
    """The just-after-targets-are-selected offer."""

    def __init__(self, stratagem_controller, turn_tracker=None,
                 decision_manager=None, game_log=None, auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self._offered_this_phase = set()
        self._stratagem = Stratagem(
            name=SPIRALLING_EVASION_NAME, cp_cost=SPIRALLING_EVASION_CP,
            effect=self._grant,
        )

    def reset_phase(self, squads=()):
        self._offered_this_phase = set()
        reset_phase(squads)

    def can_use(self, attacker, target):
        if attacker is None or target is None or self.stratagem_controller is None:
            return False
        if self.turn_tracker is not None:
            if self.turn_tracker.phase != PHASE_SHOOTING:
                return False
            # "YOUR OPPONENT'S Shooting phase" - the protected unit's owner is
            # the one NOT taking the turn.
            if target.owner == self.turn_tracker.turn_owner:
                return False
        if attacker.owner == target.owner:
            return False
        if is_active(target):
            return False
        if not eligible_unit(target):
            return False
        return self.stratagem_controller.can_use(target.owner, self._stratagem, [target])

    def maybe_offer(self, attacker, target, melee=False):
        """ShootingController.target_reactions' protocol."""
        if melee:
            return False               # "your opponent's SHOOTING phase"
        if not self.can_use(attacker, target):
            return False
        key = (id(attacker), id(target))
        if key in self._offered_this_phase:
            return False
        self._offered_this_phase.add(key)
        if target.owner in self.auto_players or self.decision_manager is None:
            return False               # no AI path
        self.decision_manager.request(
            target.owner,
            "%s (%d CP): %s is shooting at %s - give it a %s invulnerable save "
            "this phase?"
            % (SPIRALLING_EVASION_NAME, SPIRALLING_EVASION_CP, attacker.name,
               target.name, SPIRALLING_EVASION_SAVE),
            [("Use (%d CP)" % SPIRALLING_EVASION_CP, (lambda: self.use(target))),
             ("Decline", lambda: None)],
            is_stratagem=True,
        )
        return True

    def use(self, target):
        if self.stratagem_controller is None or target is None:
            return False
        if is_active(target) or not eligible_unit(target):
            return False
        return self.stratagem_controller.use(target.owner, self._stratagem, [target])

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            squad.spiralling_evasion_active = True
            if self.game_log is not None:
                self.game_log.add(
                    "%s: %s has a %s invulnerable save this phase."
                    % (SPIRALLING_EVASION_NAME, squad.name, SPIRALLING_EVASION_SAVE))
