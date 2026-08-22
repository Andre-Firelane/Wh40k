"""Eldrad Ulthran's "Diviner of Futures" - a datasheet ability, so its own
module.

RULE (printed, word for word):
  "At the start of your Command phase, if this model is on the battlefield,
  you gain 1CP."

NO DICE, unlike the other CP-granting ability here (Gretchin's Thievin'
Scavengers, which rolls a D6 per qualifying objective and needs a visible roll
because its outcome is uncertain). This one has no condition to resolve beyond
"is he on the battlefield", so it grants and logs, and there is nothing for the
player to acknowledge.

IT GOES THROUGH command_points.gain_cp(), NOT gain_core_cp(). The distinction
is load-bearing:

  * gain_core_cp() is rule 08.02's baseline - every player, every Command
    phase, guaranteed.
  * gain_cp() is a single-player grant from a unit ability, and it is where the
    user's house rule lives ("man kann in einer Schlachtrunde nicht mehr als 1
    zusätzlichen CP dazugewinnen", BONUS_CP_PER_ROUND_CAP). That cap is across
    ALL such abilities combined, not per ability, so an army fielding both
    Eldrad and Gretchin gets one bonus CP per round between them, not two.

Which means this ability can legitimately grant 0 - gain_cp() returns what it
actually granted and logs why - and that is not a bug to route around here. The
cap is enforced centrally on purpose so no caller can skip it.

"IF THIS MODEL IS ON THE BATTLEFIELD" is read off the token list, which is what
"on the battlefield" means in this engine: a unit in Strategic Reserves (20.03)
or embarked in a Transport (18.02) is deliberately not in it, and a dead model
is filtered too. Read per MODEL rather than per squad because the sentence says
"this model" - after rule 19.01 merges him into a bodyguard unit, the unit can
be on the battlefield while he personally is dead.
"""

DIVINER_OF_FUTURES_CP = 1
REASON = "Diviner of Futures"


def bearers_on_battlefield(player, all_tokens):
    """The living models with this ability that `player` has on the board."""
    out = []
    for token in all_tokens or ():
        if token.is_dead() or not getattr(token.profile, "diviner_of_futures", False):
            continue
        squad = getattr(token, "squad", None)
        if squad is None or squad.owner != player:
            continue
        out.append(token)
    return out


class DivinerOfFuturesController:
    """Fires once at the start of each player's own Command phase.

    No AI path, like the rest of the Aeldari work - but there is nothing to
    decide here anyway, so an AI-controlled Eldrad would gain the CP through
    this same call."""

    def __init__(self, command_points=None, all_tokens=None, turn_tracker=None, game_log=None):
        self.command_points = command_points
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.turn_tracker = turn_tracker   # for battle_round, which gain_cp() requires
        self.game_log = game_log

    def start_of_command_phase(self, player):
        """Returns the CP actually granted (0 if he is not on the battlefield,
        or if the round's bonus-CP cap was already used elsewhere)."""
        if self.command_points is None:
            return 0
        if not bearers_on_battlefield(player, self.all_tokens):
            return 0
        battle_round = self.turn_tracker.battle_round if self.turn_tracker is not None else None
        return self.command_points.gain_cp(
            player, battle_round, amount=DIVINER_OF_FUTURES_CP, reason=REASON,
        )
