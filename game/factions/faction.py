"""Faction scaffold: the top-level container for one army's datasheets and
detachments, plus a small registry so a faction module only has to build
itself once (at import time) and everything else can look it up by keyword."""

from collections import Counter


class Faction:
    """One army's datasheets and detachments. A Faction alone isn't a
    playable army list - choosing one detachment plus a set of datasheet/
    loadout choices (an army list) is still the "Muster Armies" pregame step
    this engine deliberately hasn't modeled yet (see CLAUDE.md's Später-
    Liste); this only holds the data those choices would be made from."""

    def __init__(self, name, keyword):
        self.name = name
        self.keyword = keyword  # the faction keyword every one of its datasheets carries, e.g. "ORKS"
        self.datasheets = {}
        self.detachments = {}

    def add_datasheet(self, datasheet):
        datasheet.faction = self
        self.datasheets[datasheet.name] = datasheet
        return datasheet

    def add_detachment(self, detachment):
        detachment.faction = self
        self.detachments[detachment.name] = detachment
        return detachment


FACTIONS = {}


def register_faction(faction):
    FACTIONS[faction.keyword] = faction
    return faction


def get_faction(keyword):
    return FACTIONS.get(keyword)


def faction_keyword_of(squad):
    """This unit's faction keyword ("ORKS", "AELDARI", ...), or None for a
    hand-built Squad that was never made by build_squad() (its `datasheet`
    is None then - see Squad.datasheet) or for a datasheet that was never
    added to a Faction. Read through getattr all the way down so a test's
    stub squad degrades to None instead of raising - nothing here is a rule,
    it only decides which logo to draw."""
    datasheet = getattr(squad, "datasheet", None)
    faction = getattr(datasheet, "faction", None)
    return getattr(faction, "keyword", None)


def player_factions(squads):
    """{player name -> faction keyword} for the armies these units make up.

    Derived from the units themselves rather than configured, the same way
    game/battle_focus.py decides whose army is ASURYANI and for the same
    reason: a config constant is the thing someone forgets after swapping an
    army list, and the failure mode here would be a panel labelling a player
    with the wrong faction's logo.

    A player fielding units from more than one faction cannot happen in a
    legal list and is not something this engine can currently produce, but
    the majority answer is the honest one if it ever does - so it takes the
    most common keyword rather than whichever squad happened to be first.
    Players whose units carry no faction at all are simply absent from the
    result, which callers read as "no logo for this one"."""
    by_player = {}
    for squad in squads:
        owner = getattr(squad, "owner", None)
        keyword = faction_keyword_of(squad)
        if owner is None or keyword is None:
            continue
        by_player.setdefault(owner, Counter())[keyword] += 1
    return {player: counts.most_common(1)[0][0] for player, counts in by_player.items()}
