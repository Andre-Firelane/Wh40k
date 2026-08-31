"""Windrider Host Enhancement: Echoes of Ulthanesh (20 pts).

RULE (verbatim, rules/aeldari/detachments/Windrider Host.md):
  "ASURYANI MOUNTED model only. In your Command phase, roll one D6, adding 1 to
  the result if the bearer is not within your deployment zone, and adding an
  additional 1 to the result if the bearer is within your opponent's deployment
  zone: on a 5+, you gain 1CP."

THE TWO BONUSES STACK, AND THAT IS THE CARD. "adding an ADDITIONAL 1" - a
bearer standing in the opponent's deployment zone is by definition also not in
its own, so it gets BOTH: a 3+ rather than a 5+. Read as an either/or the
Enhancement would cap at +1 and the aggressive positioning it is built to
reward would buy nothing extra. Each of the three bands is measured.

THE ZONES ARE THE REAL CONDITION, so they are read from the actual
DeploymentZone objects (contains_point) rather than from a board half - a
deployment zone is a SHAPE in this engine, and on map3 it is a quadrant with a
disc cut out of it, which no half-board test could stand in for.

IT DOES NOT ROLL WHEN THE CP CANNOT BE PAID. game/command_points.py caps bonus
CP per battle round (BONUS_CP_PER_ROUND_CAP, shared by every bonus source), and
bonus_cp_remaining() is the one definition of what is left. Rolling a die that
cannot pay anything looks like a bug to whoever is watching - the same rule
Coordinated Leadership and the Secondary-Mission discard already follow.

MEASURED FROM THE BEARER MODEL, not from its unit: "if the BEARER is within",
and a 12"-long Windrider line can easily straddle a zone edge.
"""
from game import enhancements

ECHOES_OF_ULTHANESH = "Echoes of Ulthanesh"

ECHOES_LABEL = "Echoes of Ulthanesh"

#: "on a 5+, you gain 1CP".
ECHOES_THRESHOLD = 5
ECHOES_CP = 1
ECHOES_SIDES = 6


def bearer_models(squad):
    return enhancements.bearer_models(squad, ECHOES_OF_ULTHANESH)


def roll_bonus(model, own_zone=None, enemy_zone=None):
    """The printed additions, which STACK - see the module docstring."""
    if model is None:
        return 0
    bonus = 0
    if own_zone is not None and not own_zone.contains_point(model.x_in, model.y_in):
        bonus += 1
    if enemy_zone is not None and enemy_zone.contains_point(model.x_in, model.y_in):
        bonus += 1
    return bonus


class EchoesOfUlthaneshController:
    """The Command-phase roll."""

    def __init__(self, game_state=None, command_points=None, turn_tracker=None,
                 game_log=None, zones=None):
        self.game_state = game_state
        self.command_points = command_points
        self.turn_tracker = turn_tracker
        self.game_log = game_log
        #: player -> (own DeploymentZone, enemy DeploymentZone).
        self.zones = zones or {}

    def _squads(self):
        seen, out = set(), []
        for token in getattr(self.game_state, "tokens", ()) or ():
            squad = getattr(token, "squad", None)
            if squad is not None and id(squad) not in seen:
                seen.add(id(squad))
                out.append(squad)
        return out

    def bearers_for(self, player):
        return [(s, m) for s in self._squads() if s.owner == player
                for m in bearer_models(s)]

    def _headroom(self, player):
        if self.command_points is None:
            return ECHOES_CP
        return self.command_points.bonus_cp_remaining(
            player, getattr(self.turn_tracker, "battle_round", None))

    def begin_command_phase(self, player):
        """"In your Command phase, roll one D6 ... on a 5+, you gain 1CP"."""
        bearers = self.bearers_for(player)
        if not bearers:
            return False
        if self._headroom(player) <= 0:
            # Nothing to win - see the module docstring.
            return False
        from game.dice import random as dice_random
        squad, model = bearers[0]
        own_zone, enemy_zone = self.zones.get(player, (None, None))
        bonus = roll_bonus(model, own_zone, enemy_zone)
        roll = dice_random.randint(1, ECHOES_SIDES)
        total = roll + bonus
        if total >= ECHOES_THRESHOLD and self.command_points is not None:
            self.command_points.gain_cp(
                player, getattr(self.turn_tracker, "battle_round", None),
                amount=ECHOES_CP, reason=ECHOES_LABEL)
        if self.game_log is not None:
            self.game_log.add(
                "%s: %s rolls %d%s = %d - %s."
                % (player, ECHOES_LABEL, roll,
                   (" +%d" % bonus) if bonus else "", total,
                   "gains 1CP" if total >= ECHOES_THRESHOLD else "no CP"))
        return True
