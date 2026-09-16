"""A printed "(Once per battle round, per army)" limit.

The 2026-09 Ork codex prints two such abilities on three datasheets:
Intimidating Motivation (Warboss AND Warboss in Mega Armour - ONE limit shared
by both, because "per army" counts the ability, not the model that prints it)
and Keep Huntin'! (Beastboss). A limit per ability NAME, then, spent by any
bearer in the army and restored at the next battle round.

WHERE THE SPEND IS WRITTEN. On the unit that used it, as the battle round
(`flag`, registered in activation_state.SQUAD_FLAGS), and read back over every
unit the player has - game/war_cry.py's and game/enh_da_boss_is_watchin.py's
arrangement, so a save keeps it. An in-memory ledger stands beside it, because
the unit that spent the limit can be destroyed later in the same round; a limit
that only lived on that unit would then quietly come back for its sibling.
"""


class PerArmyRoundLimit:
    def __init__(self, name, flag):
        self.name = name
        self.flag = flag
        self._spent = {}   # player -> battle round it was spent in

    def is_spent(self, player, battle_round, squads=()):
        """Whether `player`'s army has used this ability in `battle_round`."""
        if battle_round is None:
            return False
        if self._spent.get(player) == battle_round:
            return True
        return any(getattr(s, self.flag, None) == battle_round
                   for s in squads or () if getattr(s, "owner", None) == player)

    def spend(self, player, battle_round, squad=None):
        self._spent[player] = battle_round
        if squad is not None:
            setattr(squad, self.flag, battle_round)
