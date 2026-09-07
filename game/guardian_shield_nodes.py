"""Guardian Battlehost Stratagem: Shield Nodes (1CP, Battle Tactic).

RULE (verbatim, rules/aeldari/detachments/Guardian Battlehost.md):
  WHEN:   Your opponent's Shooting phase or the Fight phase, just after an
          enemy unit has selected its targets.
  TARGET: One DIRE AVENGERS or GUARDIANS unit from your army that was selected
          as the target of one or more of the attacking unit's attacks.
  EFFECT: If your unit is within range of one or more objective markers, until
          the end of the phase, each time an attack targets your unit, subtract
          1 from the Wound roll.
  RESTRICTIONS: none printed.

REACTIVE, so it joins ShootingController.target_reactions and
FightController.target_reactions and implements maybe_offer(attacker, target,
melee=). THE ARGUMENT ORDER IS THE LIST'S, NOT THIS STRATAGEM'S: every reaction
is called as (attacker, target, melee=...), and the unit this protects is the
TARGET. Getting that round the wrong way offers it to the attacker.

DEFENDER-SIDE, so it goes in _wound_modifiers() rather than _hit_modifiers().
That method is where this engine already keeps its defender-side entries -
Guardian Drone, 'Ard as Nails, Protect, the Wave Serpent Shield - and
game/protect.py is the closest shape: a flat -1 on the attacker's Wound roll
because of something about the DEFENDING unit.

SIGN: positive. game/modifiers.py adjusts the THRESHOLD, so "subtract 1 from
the Wound roll" makes the roll HARDER and is Modifier(+1, ...). Backwards it
would be a gift to the attacker.

THE OBJECTIVE CHECK IS PART OF THE EFFECT, NOT OF THE TARGET LINE. "If your
unit is within range" sits in the EFFECT, so a unit off an objective may still
be a legal target for the Stratagem and simply gets nothing - which would waste
the CP. This engine's standing rule is never to offer what buys nothing, so
can_use() checks it too; the printed reading is preserved in the docstring
rather than in a purchase that does nothing.

BOTH PHASES, with the same printed asymmetry Warding Salvoes has: "YOUR
opponent's Shooting phase" but "THE Fight phase".
"""

from game import aeldari_detachments, ai_mode, defend_at_all_costs
from game.modifiers import Modifier
from game.objectives import is_within_range_of_objective
from game.stratagems import Stratagem
from game.turn import PHASE_FIGHT, PHASE_SHOOTING

SHIELD_NODES_NAME = "Shield Nodes"
SHIELD_NODES_CP = 1

#: "subtract 1 from the Wound roll" - POSITIVE, because modifiers adjust the
#: threshold and this makes the roll harder.
SHIELD_NODES_PENALTY = 1

SHIELD_NODES_KEYWORDS = ("DIRE AVENGERS", "GUARDIANS")


def is_active(squad):
    return bool(getattr(squad, "shield_nodes_active", False))


def eligible_unit(squad):
    if squad is None or not defend_at_all_costs.has_detachment(getattr(squad, "owner", None)):
        return False
    if not aeldari_detachments.is_aeldari_unit(squad):
        return False
    from game.attached_units import unit_has_datasheet_keyword
    return any(unit_has_datasheet_keyword(squad, k) for k in SHIELD_NODES_KEYWORDS)


def wound_modifiers(target_squad):
    """A list, so a caller can `modifiers.extend(...)` it."""
    if is_active(target_squad):
        return [Modifier(SHIELD_NODES_PENALTY, SHIELD_NODES_NAME)]
    return []


def reset_phase(squads=()):
    for squad in squads or ():
        if squad is not None:
            squad.shield_nodes_active = False


class ShieldNodesController:
    """Sits in both attack controllers' target_reactions."""

    def __init__(self, stratagem_controller, turn_tracker=None, objectives=None,
                 decision_manager=None, game_log=None, auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self.objectives = objectives if objectives is not None else []
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self._offered_this_phase = set()
        self._stratagem = Stratagem(
            name=SHIELD_NODES_NAME, cp_cost=SHIELD_NODES_CP, effect=self._grant,
        )

    def reset_phase(self, squads=()):
        """Both the grant and the de-duplication memo - Split Fire's
        per-assignment hook would otherwise ask once per weapon group."""
        reset_phase(squads)
        self._offered_this_phase = set()

    def can_use(self, attacker, target):
        if attacker is None or target is None or self.stratagem_controller is None:
            return False
        if target.owner == attacker.owner:
            return False
        if is_active(target):
            return False
        if self.turn_tracker is None or self.turn_tracker.phase not in (PHASE_SHOOTING, PHASE_FIGHT):
            return False
        if self.turn_tracker.phase == PHASE_SHOOTING \
                and self.turn_tracker.turn_owner == target.owner:
            return False               # "YOUR OPPONENT'S Shooting phase"
        if not eligible_unit(target):
            return False
        if not any(not m.is_dead() for m in (getattr(target, "models", ()) or ())):
            return False
        # The EFFECT's own condition, asked here so the CP cannot buy nothing.
        if not (self.objectives and is_within_range_of_objective(target, self.objectives)):
            return False
        return self.stratagem_controller.can_use(target.owner, self._stratagem, [target])

    def maybe_offer(self, attacker, target, melee=False):
        """ShootingController/FightController target_reactions' protocol."""
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
            "%s (%d CP): %s is attacking %s, which holds an objective - subtract "
            "%d from Wound rolls against it this phase?"
            % (SHIELD_NODES_NAME, SHIELD_NODES_CP, attacker.name, target.name,
               SHIELD_NODES_PENALTY),
            [("Use (%d CP)" % SHIELD_NODES_CP, (lambda: self.use(target))),
             ("Decline", lambda: None)],
            is_stratagem=True,
        )
        return True

    def use(self, target):
        if self.stratagem_controller is None or target is None:
            return False
        return self.stratagem_controller.use(target.owner, self._stratagem, [target])

    def _grant(self, controller, player, targets):
        for squad in targets or ():
            squad.shield_nodes_active = True
            if self.game_log is not None:
                self.game_log.add(
                    "%s: attacks against %s subtract %d from the Wound roll this phase."
                    % (SHIELD_NODES_NAME, squad.name, SHIELD_NODES_PENALTY))
