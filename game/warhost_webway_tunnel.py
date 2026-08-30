"""Warhost Stratagem: Webway Tunnel (1CP, Strategic Ploy).

RULE (verbatim, rules/aeldari/detachments/Warhost.md):
  WHEN:   End of your opponent's Fight phase.
  TARGET: One ASURYANI INFANTRY unit from your army that is wholly within 9" of
          one or more battlefield edges.
  EFFECT: If your unit is not within Engagement Range of one or more enemy
          units, remove it from the battlefield and place it into Strategic
          Reserves.
  RESTRICTIONS: none printed.

COST OF VICTORY WITHOUT THE RESURRECTION. Guardian Battlehost's version of this
withdrawal returns the unit's destroyed models on the way out; this one does
not, and that absence is the entire difference in the EFFECT line. So this is
the plain half: game/strategic_reserves.py's withdraw_to_reserves(), which also
re-evaluates objective control - a unit that leaves the board must stop holding
what it stood on.

WHAT THIS ONE ADDS IS A BOARD-EDGE CONDITION, and "WHOLLY within 9"" is the
strict reading: EVERY model has to be near an edge, not just one. This repo has
a test section on exactly that distinction because the two look alike and the
wrong one passes any test that puts a unit clearly inside or clearly outside -
so it is measured with a straggler left behind.

"OF ONE OR MORE BATTLEFIELD EDGES" IS ANY EDGE, not the unit's own. The engine
does have an owner-aware notion of edges (renderer.own_board_edges()), which is
exactly the near-miss here: reading this as "your own edge" would refuse a
perfectly legal withdrawal along a flank. Measured against all four.

THE TIMING IS THE ONE MOST EASILY READ BACKWARDS: "end of your OPPONENT'S Fight
phase", so the offer goes to whoever is NOT the turn owner - the same trap
game/airborne_agility.py, Ride the Wind and Cost of Victory all write out, and
the fourth time this engine has had to.

ENGAGEMENT IS ASKED OF game/engagement.py rather than of Squad.is_engaged(),
because a unit whose only nearby enemy died in the Fight phase that just ended
is not engaged with anything - and this Stratagem is offered at exactly that
instant. See that module for the measured difference.

THE AI DECLINES (standing Aeldari instruction): taking a unit off the board is
a whole-army judgement this engine cannot make - the same call Cost of Victory
records.
"""

from game import aeldari_detachments, engagement, martial_grace
from game.stratagems import Stratagem
from game.strategic_reserves import withdraw_to_reserves
from game.turn import PHASE_FIGHT

WEBWAY_TUNNEL_NAME = "Webway Tunnel"
WEBWAY_TUNNEL_CP = 1

#: 'wholly within 9" of one or more battlefield edges'.
WEBWAY_TUNNEL_EDGE_DISTANCE_IN = 9.0


def eligible_unit(squad):
    """"One ASURYANI INFANTRY unit from your army"."""
    if squad is None or not martial_grace.has_detachment(getattr(squad, "owner", None)):
        return False
    if not aeldari_detachments.is_asuryani_unit(squad):
        return False
    from game.attached_units import unit_has_datasheet_keyword
    return unit_has_datasheet_keyword(squad, "INFANTRY")


def wholly_within_board_edge(squad, board_width_in, board_height_in,
                             distance_in=WEBWAY_TUNNEL_EDGE_DISTANCE_IN):
    """'WHOLLY within 9" of one or more battlefield edges' - every model, and
    ANY of the four edges (each model may be near a different one; the printed
    text says "one or more edges", not "the same edge").

    Measured to the model's BASE like every other distance in this engine, so a
    model straddling the line by its radius is out."""
    if board_width_in is None or board_height_in is None:
        return False
    models = [m for m in (getattr(squad, "models", ()) or ()) if not m.is_dead()]
    if not models:
        return False
    for model in models:
        near = (model.x_in - model.radius_in <= distance_in
                or (board_width_in - model.x_in - model.radius_in) <= distance_in
                or model.y_in - model.radius_in <= distance_in
                or (board_height_in - model.y_in - model.radius_in) <= distance_in)
        if not near:
            return False
    return True


class WebwayTunnelController:
    """The end-of-opponent's-Fight-phase offer."""

    def __init__(self, stratagem_controller, game_state=None, turn_tracker=None,
                 all_tokens=None, board_width_in=None, board_height_in=None,
                 decision_manager=None, game_log=None, auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.game_state = game_state
        self.turn_tracker = turn_tracker
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.board_width_in = board_width_in
        self.board_height_in = board_height_in
        self.decision_manager = decision_manager
        self.game_log = game_log
        self.auto_players = set(auto_players)
        self._stratagem = Stratagem(
            name=WEBWAY_TUNNEL_NAME, cp_cost=WEBWAY_TUNNEL_CP, effect=self._withdraw,
        )

    def near_board_edge(self, squad):
        return wholly_within_board_edge(squad, self.board_width_in,
                                        self.board_height_in)

    def can_use(self, squad):
        if squad is None or self.stratagem_controller is None or self.game_state is None:
            return False
        if self.turn_tracker is not None and self.turn_tracker.phase != PHASE_FIGHT:
            return False
        if not eligible_unit(squad):
            return False
        if squad in (getattr(self.game_state, "reserves", None) or ()):
            return False
        if not any(not m.is_dead() for m in (getattr(squad, "models", ()) or ())):
            return False
        if not self.near_board_edge(squad):
            return False
        if engagement.is_engaged(squad, self.all_tokens):
            return False
        return self.stratagem_controller.can_use(squad.owner, self._stratagem, [squad])

    def offer_at_end_of_fight_phase(self, squads, ending_player):
        """`ending_player` is whose turn the Fight phase belonged to, so the
        offer goes to everyone ELSE - "your OPPONENT'S Fight phase"."""
        for squad in sorted((s for s in squads if s.owner != ending_player),
                            key=lambda s: (str(s.owner), s.name)):
            if not self.can_use(squad):
                continue
            if squad.owner in self.auto_players or self.decision_manager is None:
                return False           # no AI path
            self.decision_manager.request(
                squad.owner,
                "%s (%d CP): pull %s off the battlefield and into Strategic "
                "Reserves?" % (WEBWAY_TUNNEL_NAME, WEBWAY_TUNNEL_CP, squad.name),
                [("Use (%d CP)" % WEBWAY_TUNNEL_CP, (lambda s=squad: self.use(s))),
                 ("Decline", lambda: None)],
                is_stratagem=True,
            )
            return True
        return False

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _withdraw(self, controller, player, targets):
        for squad in targets or ():
            withdraw_to_reserves(
                self.game_state, squad, log=self.game_log,
                message="%s: %s slips into the webway and into Strategic "
                        "Reserves." % (WEBWAY_TUNNEL_NAME, squad.name))
