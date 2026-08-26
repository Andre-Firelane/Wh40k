"""Baharroth's "Cloudstrider" - two halves, and NEITHER of them is new
machinery. Both are mechanisms this engine already had, which is the whole
reason this module is short.

RULE (printed, word for word):
  "While this model is leading a unit, at the end of your opponent's turn, if
   that unit is not within Engagement Range of one or more enemy units, you can
   remove it from the battlefield and place it into Strategic Reserves. In
   addition, while this model is leading a unit, when that unit is set up on
   the battlefield using the Deep Strike ability, in your movement phase, it can
   use this ability. If it does, that unit can be set up anywhere on the
   battlefield that is more than 6" horizontally away from all enemy models,
   but until the end of the turn, it is not eligible to declare a charge."

HALF ONE is game/starflare_ignition.py's own withdraw, condition for condition:
"at the end of your opponent's turn", "not within Engagement Range", "place it
into Strategic Reserves". So it calls the same
game/strategic_reserves.withdraw_to_reserves() - the third consumer of the
board->reserves move, after that T'au Enhancement and Seer Council's Unshrouded
Truth - and inherits the two things that are not optional there: clearing
ingress_locked and recomputing objective control.

HALF TWO is Retaliation Cadre's The Shortened Blade, sentence for sentence:
the same 6" horizontal minimum in place of rule 20.04's 8", and the same
"cannot declare a charge this turn". So it arms the same override on
IngressController - which is why that field is no longer named after the
stratagem.

WHAT IS ACTUALLY THIS ABILITY'S OWN is only the CONDITION: "while this model is
leading a unit". Read through attached_units.leader_ability(), not
unit_wide_ability() - the latter asks whether EVERY model prints the ability,
and on a Leader ability no bodyguard does, which is the whole point. That also
brings 19.04's grace window along for free.

THE ENGAGEMENT CHECK reads the LIVING models, for the reason
game/starflare_ignition.py had to learn the hard way: this fires at the end of
a turn, and main.py's once-per-frame remove_dead_models() has not necessarily
run yet, so a unit surrounded only by corpses would otherwise look engaged.
"""

from game import attached_units
from game.ingress import SHORTENED_BLADE_MIN_ENEMY_DISTANCE_IN
from game.strategic_reserves import withdraw_to_reserves

CLOUDSTRIDER_LABEL = "Cloudstrider"
CLOUDSTRIDER_MIN_ENEMY_DISTANCE_IN = SHORTENED_BLADE_MIN_ENEMY_DISTANCE_IN


def applies(squad):
    """"While this model is LEADING a unit" - so a Baharroth standing on his
    own has it and grants nothing, which is what leader_ability() answers."""
    return attached_units.leader_ability(squad, "cloudstrider")


def _living(models):
    return [m for m in models if not m.is_dead()]


def refusal_reason(squad, game_state):
    """Why the withdraw half cannot be used right now, or None."""
    if squad is None or game_state is None:
        return "no unit"
    if not applies(squad):
        return f"{getattr(squad, 'name', '?')} is not led by a model with {CLOUDSTRIDER_LABEL}"
    if squad in game_state.reserves:
        return f"{squad.name} is already in Strategic Reserves"
    if not _living(squad.models):
        return f"{squad.name} has no models left"
    enemies = [m for t in game_state.tokens
               if (getattr(t, "squad", None) is not None
                   and t.squad.owner != squad.owner and not t.is_dead())
               for m in (t,)]
    if squad.is_engaged(enemies):
        return f"{squad.name} is within Engagement Range of an enemy unit"
    return None


def can_withdraw(squad, game_state):
    return refusal_reason(squad, game_state) is None


class CloudstriderController:
    """Offered at the end of the opponent's turn (the withdraw half); the
    deep-strike half is armed from the reserves-arrival flow.

    Human-driven like the rest of the Aeldari work - the offer goes through
    DecisionManager, so an AI would resolve it generically if one ever played
    this faction."""

    def __init__(self, game_state=None, decision_manager=None, ingress_controller=None,
                 game_log=None):
        self.game_state = game_state
        self.decision_manager = decision_manager
        self.ingress_controller = ingress_controller
        self.game_log = game_log

    # -- half one: back into Strategic Reserves ---------------------------
    def offer_at_end_of_turn(self, opponent):
        """`opponent` is the player whose turn is ending - so the units that
        may react are the OTHER player's."""
        if self.game_state is None or self.decision_manager is None:
            return
        for squad in self._candidates(opponent):
            self.decision_manager.request(
                squad.owner,
                f"{squad.name}: {CLOUDSTRIDER_LABEL} - withdraw into Strategic Reserves?",
                [("Withdraw", lambda s=squad: self.withdraw(s)), ("Stay", lambda: None)],
            )
            return   # one at a time; the next end of turn offers again

    def _candidates(self, opponent):
        squads, seen = [], set()
        for token in list(getattr(self.game_state, "tokens", ())):
            squad = getattr(token, "squad", None)
            if squad is None or id(squad) in seen or squad.owner == opponent:
                continue
            seen.add(id(squad))
            if can_withdraw(squad, self.game_state):
                squads.append(squad)
        return squads

    def withdraw(self, squad):
        reason = refusal_reason(squad, self.game_state)
        if reason is not None:
            if self.game_log is not None:
                self.game_log.add(f"{CLOUDSTRIDER_LABEL} not used: {reason}.")
            return False
        return withdraw_to_reserves(
            self.game_state, squad, log=self.game_log,
            message=(f"{squad.owner}: {squad.name} uses {CLOUDSTRIDER_LABEL} - back into "
                     "Strategic Reserves."),
        )

    # -- half two: the 6" arrival ----------------------------------------
    def arm_arrival(self, squad):
        """"That unit can be set up anywhere more than 6" horizontally away
        from all enemy models, but until the end of the turn it is not eligible
        to declare a charge" - the same override The Shortened Blade arms, and
        the same charge lock, so it is the same field on IngressController.

        The charge lock is set HERE rather than on confirm because the printed
        text is unconditional ("but until the end of the turn..."), the way The
        Shortened Blade's is and unlike The Torchstar Gambit's "if it does"."""
        if squad is None or self.ingress_controller is None or not applies(squad):
            return False
        self.ingress_controller.relaxed_arrival_squad = squad
        squad.charge_locked_until_end_of_turn = True
        if self.game_log is not None:
            self.game_log.add(
                f"{squad.owner}: {squad.name} uses {CLOUDSTRIDER_LABEL} - it may arrive more "
                f'than {CLOUDSTRIDER_MIN_ENEMY_DISTANCE_IN:g}" from every enemy model, and '
                "cannot declare a charge this turn."
            )
        return True
