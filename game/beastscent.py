"""Kill Rig's Beastscent (2026-09 Ork codex, stage E3e).

RULE (verbatim, rules/orks/Kill Rig.md):
  "Beastscent (psychic level 1): In your Movement phase, when a unit embarked
   within this unit is selected to make a disembark move, if this unit is not
   battle-shocked, you can make a psychic roll for this unit by rolling one D6.
   If you do:
   - On a 1, this unit is battle-shocked.
   - That disembarking unit's attacks that target a MONSTER/VEHICLE unit have +1
     to wound rolls until the end of the turn."

WHERE IT HANGS: TransportController.on_disembark_started (new with this stage),
fired by start_disembark() once the placement is open - the one door the panel's
Disembark button, the AI and a printed-mode caller all go through, so "selected to
make a disembark move" has a single moment.

TWO UNITS, TWO ROLES. "This unit" is the Kill Rig - the psychic roll, the Unstable
Energies budget (shared with Warpath for the battle round) and a shock on a 1 are
the TRANSPORT's, through game/psychic_roll.py. The grant is the PASSENGER's.

"YOUR MOVEMENT PHASE": the phase is Movement and the Kill Rig's owner owns the
turn. A reactive disembark in the opponent's phase (the Trukk's Pilin' Out shape)
is not one.

THE GRANT is Squad.beastscent_active, cleared for every unit by main.py's
end-of-turn sweep ("until the end of the turn"), and read as a -1 on the wound
threshold (game/modifiers.py's convention for a bonus) in BOTH _wound_modifiers()
- shooting.py and fight.py, since "attacks" names neither phase - whenever the
TARGET unit is MONSTER/VEHICLE (game/squad.is_monster_or_vehicle_unit()).

"You can" - a human is asked while the placement stands open (the die then has to
be acknowledged before a model can be dragged). The AI answers through an injected
verdict (ai/agent_driver.py's beastscent_verdict(), 0 API calls).

NAMED: a placement cancelled after the roll keeps its grant - the unit WAS selected
to make the move, which is the printed trigger, and the budget is spent either way.
"""

from game import ai_mode
from game.modifiers import Modifier
from game.squad import is_monster_or_vehicle_unit
from game.turn import PHASE_MOVEMENT

BEASTSCENT_NAME = "Beastscent"
BEASTSCENT_PSYCHIC_LEVEL = 1
BEASTSCENT_WOUND_BONUS = -1
ROLL_LABEL = "Make the psychic roll (Beastscent)"
DECLINE_LABEL = "Decline"


def has_ability(transport_token):
    profile = getattr(transport_token, "profile", None)
    return bool(getattr(profile, "beastscent", False))


def is_active(squad):
    return bool(getattr(squad, "beastscent_active", False))


def wound_modifiers(attacking_squad, target_squad):
    """[Modifier(-1, "Beastscent")] for an attack by a unit under the grant
    against a MONSTER/VEHICLE unit, else []."""
    if not is_active(attacking_squad) or target_squad is None or not target_squad.models:
        return []
    if not is_monster_or_vehicle_unit(target_squad):
        return []
    return [Modifier(BEASTSCENT_WOUND_BONUS, BEASTSCENT_NAME)]


def clear_turn(squads=()):
    for squad in squads or ():
        if getattr(squad, "beastscent_active", False):
            squad.beastscent_active = False


class BeastscentController:
    def __init__(self, psychic_roll, turn_tracker=None, decision_manager=None, game_log=None,
                 auto_players=(), verdict=None):
        self.psychic_roll = psychic_roll
        self.turn_tracker = turn_tracker
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = ai_mode.players(auto_players)
        #: The AI's rule: verdict(transport_token, passenger) -> bool.
        self.verdict = verdict

    def can_use(self, transport_token, passenger):
        if transport_token is None or passenger is None or not has_ability(transport_token):
            return False
        rig = getattr(transport_token, "squad", None)
        if rig is None or transport_token.is_dead():
            return False
        tt = self.turn_tracker
        if tt is None or tt.phase != PHASE_MOVEMENT or tt.turn_owner != rig.owner:
            return False
        # The psyker level is the only once-limit: a second passenger of the same
        # Movement phase is refused by the spent budget, not by a flag.
        return self.psychic_roll is not None and self.psychic_roll.can_roll(rig, BEASTSCENT_PSYCHIC_LEVEL)

    def on_disembark_started(self, passenger, transport_token):
        """TransportController.on_disembark_started listener."""
        if not self.can_use(transport_token, passenger):
            return False
        rig = transport_token.squad
        if rig.owner in self.auto_players:
            if self.verdict is not None and not self.verdict(transport_token, passenger):
                return False
            return self.use(transport_token, passenger)
        if self.decision_manager is None:
            return False
        self.decision_manager.request(
            rig.owner,
            "%s: %s (psychic level %d) - %s's attacks against MONSTER/VEHICLE units get +1 to wound "
            "until the end of the turn; roll one D6, on a 1 the Kill Rig is battle-shocked?"
            % (rig.name, BEASTSCENT_NAME, BEASTSCENT_PSYCHIC_LEVEL, passenger.name),
            [(ROLL_LABEL, lambda t=transport_token, p=passenger: self.use(t, p)),
             (DECLINE_LABEL, lambda: None)],
        )
        return True

    def use(self, transport_token, passenger):
        if not self.can_use(transport_token, passenger):
            return False
        passenger.beastscent_active = True
        if self.game_log is not None:
            self.game_log.add("%s uses %s: %s's attacks against MONSTER/VEHICLE units have +1 to wound "
                              "until the end of the turn." % (transport_token.squad.name, BEASTSCENT_NAME,
                                                              passenger.name))
        self.psychic_roll.roll(transport_token.squad, BEASTSCENT_NAME, BEASTSCENT_PSYCHIC_LEVEL)
        return True
