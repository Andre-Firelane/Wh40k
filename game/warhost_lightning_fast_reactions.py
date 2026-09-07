"""Warhost Stratagem: Lightning-Fast Reactions (1CP, Battle Tactic).

RULE (verbatim, rules/aeldari/detachments/Warhost.md):
  WHEN:   Your opponent's Shooting phase or the Fight phase, just after an
          enemy unit has selected its targets.
  TARGET: One ASURYANI unit from your army (excluding WRAITH CONSTRUCT units)
          that was selected as the target of one or more of the attacking
          unit's attacks.
  EFFECT: Until the end of the phase, each time an attack targets your unit,
          subtract 1 from the Hit roll.
  RESTRICTIONS: none printed.

REACTIVE IN BOTH PHASES, which is what separates it from its Windrider
cousin: Spiralling Evasion prints "your opponent's SHOOTING phase" and joins
one reaction list, this prints "or the Fight phase" and joins both. The
protocol is the same, and so is the trap in it - THE ARGUMENT ORDER IS THE
LIST'S: the unit this protects is the TARGET, the second argument.

THE SIGN IS POSITIVE. game/modifiers.py adjusts the THRESHOLD, so "subtract 1
from the Hit roll" makes the roll HARDER and is a positive Modifier. Written
backwards it would be a 1CP gift to the attacker, which is the shape that
still passes a "the modifier is there" test.

"EACH TIME AN ATTACK TARGETS YOUR UNIT" - so it is read on the DEFENDER's side
of _hit_modifiers(), beside Guardian Drone, and it applies to
every attacker for the rest of the phase rather than only to the one that
triggered it. That is what "until the end of the phase" buys and why it is
worth a CP against a unit about to be shot by three others.

"EXCLUDING WRAITH CONSTRUCT UNITS" is a real exclusion on this roster, not
boilerplate: Wraithguard, Wraithblades, the Wraithlord and the Clanblade all
carry the keyword, and all four are exactly the units a player would most want
to protect. Checked at its own name and given its own test line.

BOUGHT BY THE DEFENDER, so the offer goes to the target's owner - and the
turn-owner check is the one that decides which side that is. In the Fight
phase there is no such check at all, because "THE Fight phase" belongs to
nobody.

THE AI DECLINES (standing Aeldari instruction).
"""

from game import aeldari_detachments, ai_mode, martial_grace
from game.modifiers import Modifier
from game.stratagems import Stratagem
from game.turn import PHASE_FIGHT, PHASE_SHOOTING

LIGHTNING_FAST_REACTIONS_NAME = "Lightning-Fast Reactions"
LIGHTNING_FAST_REACTIONS_CP = 1

#: "subtract 1 from the Hit roll" - POSITIVE, because a Modifier adjusts the
#: threshold and this makes the roll harder.
LIGHTNING_FAST_REACTIONS_PENALTY = 1

#: The printed exclusion.
LIGHTNING_FAST_REACTIONS_EXCLUDED_KEYWORD = "WRAITH CONSTRUCT"


def is_active(squad):
    return bool(getattr(squad, "lightning_fast_reactions_active", False))


def eligible_unit(squad):
    """"One ASURYANI unit from your army (excluding WRAITH CONSTRUCT units)"."""
    if squad is None or not martial_grace.has_detachment(getattr(squad, "owner", None)):
        return False
    if not aeldari_detachments.is_asuryani_unit(squad):
        return False
    from game.attached_units import unit_has_datasheet_keyword
    return not unit_has_datasheet_keyword(
        squad, LIGHTNING_FAST_REACTIONS_EXCLUDED_KEYWORD)


def hit_modifiers(target_squad):
    """Read by BOTH attack chains' _hit_modifiers(), on the DEFENDER's side."""
    if not is_active(target_squad):
        return []
    return [Modifier(LIGHTNING_FAST_REACTIONS_PENALTY,
                     LIGHTNING_FAST_REACTIONS_NAME)]


def reset_phase(squads=()):
    for squad in squads or ():
        if squad is not None:
            squad.lightning_fast_reactions_active = False


class LightningFastReactionsController:
    """The just-after-targets-are-selected offer, in both attack phases."""

    def __init__(self, stratagem_controller, turn_tracker=None,
                 decision_manager=None, game_log=None, auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.turn_tracker = turn_tracker
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        self._offered_this_phase = set()
        self._stratagem = Stratagem(
            name=LIGHTNING_FAST_REACTIONS_NAME, cp_cost=LIGHTNING_FAST_REACTIONS_CP,
            effect=self._grant,
        )

    def reset_phase(self, squads=()):
        self._offered_this_phase = set()
        reset_phase(squads)

    def can_use(self, attacker, target):
        if attacker is None or target is None or self.stratagem_controller is None:
            return False
        if self.turn_tracker is not None:
            phase = self.turn_tracker.phase
            if phase == PHASE_SHOOTING:
                # "YOUR OPPONENT'S Shooting phase" - the protected unit is the
                # one NOT taking the turn.
                if target.owner == self.turn_tracker.turn_owner:
                    return False
            elif phase != PHASE_FIGHT:
                # "or THE Fight phase" - which belongs to nobody, so there is
                # deliberately no owner check on that half.
                return False
        if attacker.owner == target.owner:
            return False
        if is_active(target):
            return False
        if not eligible_unit(target):
            return False
        return self.stratagem_controller.can_use(target.owner, self._stratagem, [target])

    def maybe_offer(self, attacker, target, melee=False):
        """The target_reactions protocol, shared by both attack controllers."""
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
            "%s (%d CP): %s is attacking %s - subtract %d from Hit rolls against "
            "it this phase?"
            % (LIGHTNING_FAST_REACTIONS_NAME, LIGHTNING_FAST_REACTIONS_CP,
               attacker.name, target.name, LIGHTNING_FAST_REACTIONS_PENALTY),
            [("Use (%d CP)" % LIGHTNING_FAST_REACTIONS_CP,
              (lambda: self.use(target))),
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
            squad.lightning_fast_reactions_active = True
            if self.game_log is not None:
                self.game_log.add(
                    "%s: attacks against %s subtract %d from the Hit roll this "
                    "phase."
                    % (LIGHTNING_FAST_REACTIONS_NAME, squad.name,
                       LIGHTNING_FAST_REACTIONS_PENALTY))
