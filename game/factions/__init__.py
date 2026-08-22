"""Faction data scaffold: how a faction's army rules, detachment rules, and
unit (datasheet) rules are stored, independent of any particular battle.

This package holds DATA (a faction's datasheets and detachments, each with
their full rules and possible wargear loadouts) - it does not itself place
anything on a board. `datasheet.build_squad()` is the one bridge from this
data to the engine's existing Token/Squad objects: given a Datasheet plus a
chosen loadout, it produces the actual models a game uses, already carrying
their selected weapons - main.py (or, eventually, a real pregame deployment
flow) still decides WHERE those models start and for which player, exactly
like it already does for the hand-built demo scene.

Concrete factions (e.g. Orks, Adeptus Astartes) each get their own module in
this package (game/factions/orks.py, ...), built from the army/detachment/
unit rules the user supplies - none are populated yet, this is only the
scaffold those modules will be written against."""

from game.factions.datasheet import Datasheet, Gear, ModelLine, WargearOption, build_squad
from game.factions.detachment import Detachment, Enhancement
from game.factions.faction import FACTIONS, Faction, register_faction, get_faction
from game.factions.points import PointsTier, UnitPoints, flat_points

__all__ = [
    "Datasheet", "Gear", "ModelLine", "WargearOption", "build_squad",
    "Detachment", "Enhancement",
    "FACTIONS", "Faction", "register_faction", "get_faction",
    "PointsTier", "UnitPoints", "flat_points",
]
