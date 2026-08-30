"""Kauyon Stratagem: Wall of Mirrors (1CP).

RULE (verbatim, rules/tau_empire/detachments/Kauyon.md):
  WHEN:   End of your opponent's Fight phase.
  TARGET: One STEALTH, GHOSTKEEL or COMMANDER SHADOWSUN unit from your army.
  EFFECT: Remove your unit from the battlefield and place it into Strategic
          Reserves.
  RESTRICTIONS: You cannot target a unit that is within Engagement Range of one
          or more enemy units.

STRUCTURALLY THE STARFLARE IGNITION SYSTEM, AT A DIFFERENT MOMENT
------------------------------------------------------------------
The Enhancement in game/starflare_ignition.py does the same thing - withdraw to
Strategic Reserves, refused inside Engagement Range - at the end of the
opponent's TURN. This is the end of their FIGHT PHASE, which is earlier and
happens even when the turn runs on. The mechanical half is
game/strategic_reserves.py's withdraw_to_reserves(), shared rather than
reimplemented; what differs is the WHEN and the unit list.

"END OF YOUR OPPONENT'S Fight phase" means the offer goes to whoever is NOT
the turn owner, and it is asked at a phase boundary rather than a turn one.

THE THREE NAMED UNITS are matched by datasheet keyword (STEALTH, GHOSTKEEL) and
by datasheet name for Commander Shadowsun, who is an EPIC HERO with no keyword
of her own that the others share. Measured: STEALTH and GHOSTKEEL each pick out
exactly one datasheet in this faction, so the keywords and the printed names
are the same set.
"""

from game import kauyon, strategic_reserves, tau_detachments
from game.attached_units import unit_has_datasheet_keyword
from game.stratagems import Stratagem
from game.turn import PHASE_FIGHT

WALL_OF_MIRRORS_CP = 1
WALL_OF_MIRRORS_NAME = "Wall of Mirrors"
WALL_OF_MIRRORS_KEYWORDS = ("STEALTH", "GHOSTKEEL")
WALL_OF_MIRRORS_DATASHEETS = ("Commander Shadowsun",)


def is_eligible_unit(squad):
    """"One STEALTH, GHOSTKEEL or COMMANDER SHADOWSUN unit"."""
    if squad is None:
        return False
    if any(unit_has_datasheet_keyword(squad, kw) for kw in WALL_OF_MIRRORS_KEYWORDS):
        return True
    sheet = getattr(squad, "datasheet", None)
    return getattr(sheet, "name", None) in WALL_OF_MIRRORS_DATASHEETS


class WallOfMirrorsController:
    def __init__(self, stratagem_controller, game_state=None, turn_tracker=None,
                 all_tokens=None, decision_manager=None, game_log=None,
                 auto_players=()):
        self.stratagem_controller = stratagem_controller
        self.game_state = game_state
        self.turn_tracker = turn_tracker
        self.all_tokens = all_tokens if all_tokens is not None else []
        self.decision_manager = decision_manager
        self.game_log = game_log
        # Reactive, so it answers itself for these players rather than opening
        # a prompt nobody is there to click - the `'Ard as Nails` arrangement.
        # There is no T'au AI path by standing instruction, so this stays empty
        # unless a caller asks for it.
        self.auto_players = tuple(auto_players)
        self._stratagem = Stratagem(
            name=WALL_OF_MIRRORS_NAME, cp_cost=WALL_OF_MIRRORS_CP, effect=self._withdraw,
        )
        self._pending = None

    def _log(self, message):
        if self.game_log is not None:
            self.game_log.add(message)

    def eligible_units(self, player):
        squads = []
        for token in self.all_tokens:
            squad = getattr(token, "squad", None)
            if squad is None or squad in squads:
                continue
            if squad.owner != player or not is_eligible_unit(squad):
                continue
            if not any(not m.is_dead() for m in squad.models):
                continue
            if not tau_detachments.has_detachment(player, kauyon.SETTING):
                continue
            if not tau_detachments.is_tau_unit(squad):
                continue
            # RESTRICTIONS: not within Engagement Range of any enemy.
            if squad.is_engaged(self.all_tokens):
                continue
            if not self.stratagem_controller.can_use(player, self._stratagem, [squad]):
                continue
            squads.append(squad)
        return sorted(squads, key=lambda s: s.name)

    def offer_at_end_of_fight_phase(self, ending_player):
        """WHEN: "end of your opponent's Fight phase" - called with the player
        whose Fight phase just ended, so the offer goes to the other side."""
        if self.turn_tracker is None:
            return False
        reactor = next((p for p in self._players() if p != ending_player), None)
        if reactor is None:
            return False
        candidates = self.eligible_units(reactor)
        if not candidates:
            return False
        if reactor in self.auto_players or self.decision_manager is None:
            return False   # nobody to ask, and withdrawing unasked is a real cost
        self.decision_manager.request(
            reactor,
            f"{WALL_OF_MIRRORS_NAME} ({WALL_OF_MIRRORS_CP} CP): withdraw a unit into "
            "Strategic Reserves?",
            [(squad.name, (lambda s=squad: self.use(s))) for squad in candidates]
            + [("Decline", lambda: None)],
        )
        return True

    def _players(self):
        seen = []
        for token in self.all_tokens:
            squad = getattr(token, "squad", None)
            owner = getattr(squad, "owner", None)
            if owner is not None and owner not in seen:
                seen.append(owner)
        return seen

    def can_use(self, squad):
        if squad is None or self.turn_tracker is None:
            return False
        if self.turn_tracker.phase != PHASE_FIGHT:
            return False
        return squad in self.eligible_units(squad.owner)

    def use(self, squad):
        if not self.can_use(squad):
            return False
        return self.stratagem_controller.use(squad.owner, self._stratagem, [squad])

    def _withdraw(self, controller, player, targets):
        for squad in targets or ():
            if self.game_state is None:
                continue
            strategic_reserves.withdraw_to_reserves(
                self.game_state, squad, log=self.game_log,
                message=(f"{WALL_OF_MIRRORS_NAME}: {squad.name} slips away into "
                         "Strategic Reserves."),
            )
