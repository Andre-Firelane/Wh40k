"""Faction scaffold: the top-level container for one army's datasheets and
detachments, plus a small registry so a faction module only has to build
itself once (at import time) and everything else can look it up by keyword."""


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
