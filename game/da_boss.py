"""The Orks army rule "Da Boss" (2026-09 Ork codex, Mecha Orks stage G2).

PRINTED (rules/orks/army_rules.md):
  "At the start of the battle round, if a model with this ability is your
   WARLORD, gain 1CP."

Carried by the Warboss, the Warboss in Mega Armour, the Beastboss and Ghazghkull
Thraka (their FACTION line prints it; UnitProfile.da_boss). Dormant until this
stage, because the engine had no Warlord - see game/warlord.py.

"IF A MODEL WITH THIS ABILITY IS YOUR WARLORD" is read as a LIVING one: a
destroyed Warlord has no abilities left on the table. Where he stands does not
matter (a Warlord in Strategic Reserves still counts) - the text does not say
"on the battlefield".

"AT THE START OF THE BATTLE ROUND" rides the seam the Aeldari Battle Focus pool
and the Seer Council Fate dice already use: sync_battle_round(), idempotent,
called when the battle begins and at every phase change - the first call of a
new round is its start. The round a player was paid is written onto the
Warlord's unit (Squad.da_boss_round, saved), so a game loaded mid-round does not
pay the CP twice.

THE CP IS AN ABILITY'S (command_points.SOURCE_ABILITY) and goes through
gain_cp(), so the house rule's one-extra-CP-per-battle-round cap sees it like any
other bonus CP.
"""

from game.command_points import SOURCE_ABILITY
from game.warlord import living_warlord

DA_BOSS_NAME = "Da Boss"
DA_BOSS_CP = 1
PLAYERS = ("Player 1", "Player 2")


def applies(squads, player):
    """The living Warlord model of `player`, when it has Da Boss; else None."""
    model = living_warlord(squads, player)
    if model is None or not getattr(model.profile, "da_boss", False):
        return None
    return model


class DaBossController:
    def __init__(self, command_points=None, squads_provider=None, game_log=None, players=PLAYERS):
        self.command_points = command_points
        self.squads_provider = squads_provider  # every unit, wherever it is (GameState.all_squads)
        self.game_log = game_log
        self.players = tuple(players)

    def _squads(self):
        return [s for s in (self.squads_provider() if self.squads_provider else ()) if s is not None]

    def sync_battle_round(self, battle_round):
        """Pay each player's Da Boss once for `battle_round`. Returns the players
        paid by this call."""
        if not battle_round or self.command_points is None:
            return []
        squads = self._squads()
        paid = []
        for player in self.players:
            model = applies(squads, player)
            if model is None or model.squad is None:
                continue
            if getattr(model.squad, "da_boss_round", None) == battle_round:
                continue
            model.squad.da_boss_round = battle_round
            granted = self.command_points.gain_cp(
                player, battle_round, DA_BOSS_CP, reason="%s - %s is the Warlord" % (DA_BOSS_NAME, model.profile.name),
                source=SOURCE_ABILITY)
            paid.append((player, granted))
        return paid
