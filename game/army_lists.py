"""The army lists this build can field, as data plus a builder each.

WHY THIS IS A MODULE AND NOT STILL INSIDE main(). Until now Player 1 WAS the
Aeldari list and Player 2 was whichever of Orks/Necrons config.PLAYER2_ARMY
named - three blocks of straight-line code in main(), each with its owner
hard-coded into every build_squad() call and into every squad NAME. User: "ich
haette gerne noch, bevor das Pre game losgeht, eine Auswahlmoeglichkeit fuer
die Voelker/listen ... man kann in grossen Kacheln auswaehlen, welche Liste wer
spielen soll." A screen that offers a list to EITHER player cannot be built on
top of code that knows which player it is for, so each list became a function
of its owner.

WHAT IS AND IS NOT PARAMETERISED. The owner is - it decides the `owner=`
argument and the squad-name prefix ("1 Boyz 1" vs "2 Boyz 1"). Nothing else is:
the compositions, the wargear choices, the attachments and the transport
declarations are the user-supplied lists, copied here verbatim from main() with
their reasoning comments intact. Every one of those comments earned its place
by being the answer to a question that came up once already, so they moved with
the code rather than being summarised away.

THE SQUAD NAME IS AN IDENTIFIER, not decoration. ai/agent_driver.py's plan
orders address units by exact name, game/maps.py's partial rosters name them,
and game/scene_io.py keys a saved position on them - so the "<player digit>
<datasheet> <copy>" shape is load-bearing and unit_name() below is the one
place it is formed.

WHAT A LIST CARRIES BESIDES ITS BUILDER: the faction keyword (which is how
game/sprites.py finds the badge - the same keyword the rules use, not a second
name to keep in sync), the army rule's name and the detachment's name. The last
two are list-building declarations and cannot be derived from the units - the
same reason config.SEER_COUNCIL_PLAYERS and config.AWAKENED_DYNASTY_PLAYERS
exist - which is also why apply_to_config() at the bottom is what turns a
choice into those settings.
"""

import os

from game import army_io, army_roster, config, pregame

#: Re-exported from game/army_roster.py, where it moved with the builder. It is
#: the one place a squad's identifier is formed, and four modules point at it by
#: this name (game/maps.py, game/ui/army_select.py, main.py and
#: test_player1_army.py all explain themselves in terms of
#: "army_lists.unit_name()"), so the name stays answerable here rather than
#: making five references stale to save one line.
unit_name = army_roster.unit_name
# The three keys this module and main.py still NAME. There used to be one per
# shipped list, from when ARMY_LISTS was a hand-written table here; the registry
# is a scan of armies/*.json now, so the rest had no readers - and TAU_EPC_ARMY
# had come to name a list that no longer exists, which get() answers with a
# SystemExit rather than with anything useful.
#
# These three earn their place: two are the DEFAULTS below (which player starts
# with which army), and main.py re-exports Orks and Necrons for its CLI.
AELDARI = "aeldari"
ORKS_ARMY = "orks"
NECRONS_ARMY = "necrons"



class ArmyList:
    """One selectable list: what to call it, what to badge it with, and how
    to build it for whichever player picked it.

    `detachments` is a TUPLE, and it belongs to the list: a detachment is part
    of how an army was written down, not something chosen at the table. You
    cannot swap it before a game, which is why there is no selection screen -
    that was tried and taken back out.

    A tuple rather than one name because an army may field SEVERAL detachments
    at once, paying each one's Detachment Points out of a shared budget
    (game/detachments.py). Kauyon plus Advanced Acquisition Cadre is a legal
    pair at 2+1; Mont'ka plus Kauyon is not, at 3+2.

    `detachment` remains as a read-only view of the first one, because a
    tile, a log line and a saved scene all want a single name to print.

    `force_disposition` is the list's declared Force Disposition, which decides
    its PRIMARY MISSION (game/primary_missions.py). Each detachment PERMITS
    exactly one (Detachment.force_disposition); a list fielding several picks
    one of the ones they grant, and writes it down here - user: "jedes
    detachment hat zugang zu einer force disposition. diese waehlt man beim
    listen bau ... ist aber in der Liste festgeschrieben."

    It lives on the LIST rather than being derived from the detachments even
    though it must be one of theirs, because with several detachments the
    derivation has no answer - it is a choice, and a choice belongs where the
    rest of the list-building choices are. game/detachments.py's validate() is
    what refuses a disposition none of this list's detachments permit.

    `roster` is the data form: a list of game/army_roster.py Unit records loaded
    from armies/<key>.json, which game.army_roster.build() turns into squads.
    `build` is the older shape - one hand-written builder function per list -
    and the two coexist only while the eight lists are converted one at a time.
    It stays the SIXTH POSITIONAL parameter throughout, because three suites
    construct an ArmyList variant by passing another list's builder positionally
    (test_army_select.py, test_force_dispositions.py); replacing it would break
    them for no gain."""

    def __init__(self, key, name, faction_keyword, army_rule, detachments, build=None,
                 force_disposition=None, roster=None):
        self.key = key
        self.name = name
        self.faction_keyword = faction_keyword
        self.army_rule = army_rule
        self.detachments = ((detachments,) if isinstance(detachments, str)
                            else tuple(detachments))
        self._build = build
        self.roster = roster
        self.force_disposition = force_disposition

    def build(self, owner, register, state=None, model_positions=None):
        """Put this list on the table for `owner`, reporting each finished unit
        to `register` - main.py's one call site, unchanged by the conversion
        because this has the same signature the stored callable had."""
        if self.roster is not None:
            return army_roster.build(self.roster, owner, register,
                                     list_name=self.name, state=state,
                                     model_positions=model_positions)
        return self._build(owner, register, state=state, model_positions=model_positions)

    @property
    def detachment(self):
        """The first detachment, for the callers that want one name."""
        return self.detachments[0] if self.detachments else None

    def enhancement_names(self):
        """Every Enhancement this list buys, in roster order.

        Read off the roster rather than kept in a table beside it: the four
        hand-maintained {slot: name} dicts this replaces existed only because a
        builder could not say WHICH of two identical units took one, and an
        entry that carries its own Enhancement answers that by being the entry.
        Their names were also unvalidated - a slot nothing matched was silently
        ignored - where army_io now refuses one whose detachment the list does
        not field."""
        names = []
        for entry in self.roster or ():
            if entry.enhancement:
                names.append(entry.enhancement)
            names.extend(led.enhancement for led in entry.leaders if led.enhancement)
        return names


def from_army_file(army):
    """One loaded army_io.ArmyFile, as an ArmyList."""
    return ArmyList(army.key, army.name, army.faction_keyword, army.army_rule,
                    army.detachments, roster=army.roster,
                    force_disposition=army.force_disposition)


def _scan_or_refuse(directory=None):
    """Every list in armies/, refusing LOUDLY if any file there is unusable.

    Today every file in that directory is shipped with this build, so one that
    does not load is a bug in the build and must not be silently skipped - a
    quietly missing army list is precisely the failure this whole arrangement
    exists to prevent. When lists can be IMPORTED, a broken import must not stop
    the shipped ones from being playable: this is where that split goes, and
    army_io.scan() already returns the problems separately so it can."""
    armies, problems = army_io.scan(directory)
    if problems:
        raise SystemExit(
            "%d army list file(s) in %s could not be read:\n  %s"
            % (len(problems), directory or army_io.ARMIES_DIR, "\n  ".join(problems))
        )
    return armies


def from_file(key, directory=None):
    """The list in armies/<key>.json, as an ArmyList.

    Every field comes from the FILE - name, faction, army rule, detachments,
    Force Disposition and roster alike. None of it is repeated at the call site,
    because a list written down twice is a list that drifts, and the whole point
    of moving these out of source was that an importer can add one without
    anybody editing code.

    Raises army_io.ArmyFileError listing every problem: a shipped list that does
    not validate is a bug in this build, and it should stop it at import rather
    than at an army-select hover."""
    directory = directory if directory is not None else army_io.ARMIES_DIR
    return from_army_file(army_io.load(os.path.join(directory, f"{key}.json")))


# The eight shipped lists, each one file in armies/. Everything about a list -
# its name, faction, army rule, detachments, Force Disposition and every unit -
# lives in that file; nothing is repeated here, because a list written down
# twice is a list that drifts.
#
# The ORDER is the files' own sort_order, which is what the army-select screen
# shows and what test_army_select.py pins. It is explicit rather than
# alphabetical so an imported list lands at the end instead of in the middle of
# the T'au.
ARMY_LISTS = [from_army_file(army) for army in _scan_or_refuse()]

BY_KEY = {entry.key: entry for entry in ARMY_LISTS}


class FactionChoice:
    """One FACTION as the army screen offers it, with the lists it has.

    User: "ich habe vor pro Volk mehrere listen anzulegen. daher muss sich der
    Volk Auswahl Prozess etwas aendern. erst waehlt man das Volk und dann
    kommen die verschiedenen Listen zur Auswahl. also in 2 Stufen." - so the
    screen needs a thing to put on a tile for step one, and this is it.

    DERIVED, never written down twice. The grouping is ArmyList's own
    `faction_keyword`, and the display name comes from the Faction the rules
    already carry (game/factions/faction.py's FACTIONS, keyed by that same
    keyword). A second table of faction names beside the lists is exactly the
    kind of copy this repo consolidates on sight - and it would be the copy
    that goes stale, since the keyword is what every datasheet, badge and rule
    actually matches on.

    `key` and `faction_keyword` are the same string on purpose: a tile can then
    ask a FactionChoice and an ArmyList the same two questions ("what is your
    key", "which badge do you wear") without knowing which it is holding."""

    __slots__ = ("key", "faction_keyword", "name", "lists")

    def __init__(self, keyword, name, lists):
        self.key = keyword
        self.faction_keyword = keyword
        self.name = name
        self.lists = tuple(lists)

    @property
    def army_rule(self):
        """The army rule, off the first list. Every list of a faction shares
        it - it is the FACTION's rule (Waaagh!, Battle Focus) - so this is a
        read of a shared fact rather than a guess from a sample."""
        return self.lists[0].army_rule if self.lists else None


def factions(lists=None):
    """Every faction that has at least one list, in ARMY_LISTS order.

    In ARMY_LISTS order rather than alphabetically: that file is the order the
    lists were written down in, and it is the order the screen has always shown
    them in - so adding a second Ork list does not silently reshuffle the first
    step's tiles.

    A faction with NO list is not offered. This engine builds five factions'
    datasheets, and one of them having no playable list yet would be a tile
    that answers nothing (CLAUDE.md error class 5)."""
    from game.factions.faction import FACTIONS

    order = []
    grouped = {}
    for entry in (ARMY_LISTS if lists is None else lists):
        if entry.faction_keyword not in grouped:
            order.append(entry.faction_keyword)
            grouped[entry.faction_keyword] = []
        grouped[entry.faction_keyword].append(entry)
    out = []
    for keyword in order:
        faction = FACTIONS.get(keyword)
        # The keyword itself is the fallback name. A faction with lists but no
        # registered Faction object is a build error rather than a display
        # problem, and a tile reading "ORKS" is a better way to notice it than
        # a crash on a screen that runs before anything else exists.
        out.append(FactionChoice(keyword,
                                 faction.name if faction is not None else keyword,
                                 grouped[keyword]))
    return out


def lists_for(keyword, lists=None):
    """Every list of one faction, in ARMY_LISTS order."""
    return [entry for entry in (ARMY_LISTS if lists is None else lists)
            if entry.faction_keyword == keyword]


def faction_of(key):
    """The faction keyword of one list, so a caller holding a saved list key
    (config.PLAYER1_ARMY, a scene snapshot, --army1) can find which faction
    step it belongs to."""
    return get(key).faction_keyword


def get(key):
    """The ArmyList for `key`, refusing an unknown one LOUDLY.

    The alternative - falling through to a default - is how a typo turns into
    "the game silently fielded a different army", which is exactly the failure
    main()'s own player2_army() guard was written against."""
    normalised = str(key or "").strip().lower()
    if normalised not in BY_KEY:
        raise SystemExit(
            f"{key!r} is not an army list this build knows. Known lists: "
            f"{', '.join(sorted(BY_KEY))}."
        )
    return BY_KEY[normalised]


def force_disposition_for(player, config_module=None):
    """The Force Disposition the list `player` is fielding declares, or None.

    Read through configured_choices() rather than off a stored answer, so it
    tracks whatever the army selection screen wrote back - the same way every
    detachment gate reads config at call time. None for an unrecognised army
    rather than raising: this is read on the render path (the mission strip)
    and from the Primary controller, where a stale setting should show no card
    rather than kill a frame."""
    key = configured_choices(config_module).get(player)
    entry = BY_KEY.get(key)
    return entry.force_disposition if entry is not None else None


def configured_choices(config_module=None):
    """{player -> army key} as the settings and the command line leave them,
    before any selection screen runs."""
    cfg = config_module if config_module is not None else config
    return {
        "Player 1": get(getattr(cfg, "PLAYER1_ARMY", AELDARI)).key,
        "Player 2": get(getattr(cfg, "PLAYER2_ARMY", NECRONS_ARMY)).key,
    }


def apply_to_config(choices, config_module=None):
    """Write who fields which detachment into config, where the rules read it.

    The same shape - and the same reason - as maps.apply_to_config(): call it
    once at startup, before anything reads one of these constants. A detachment
    is a list-building declaration and cannot be derived from the units (a
    Necron unit looks identical in every detachment), so picking the list is
    the moment its detachment becomes known, and this is the write that makes
    the choice real. Set from scratch rather than added to, so choosing a
    different list actually takes the old detachment away."""
    cfg = config_module if config_module is not None else config
    # The detachment settings are written by game/detachments.py, from the
    # detachments the chosen LISTS declare - a detachment is part of a written
    # army list, so picking the lists IS picking them. One writer, and this is
    # the only caller now that the selection screen is gone.
    from game import detachments
    detachments.apply_to_config(choices, config_module=cfg)
    cfg.PLAYER1_ARMY = choices.get("Player 1", getattr(cfg, "PLAYER1_ARMY", AELDARI))
    cfg.PLAYER2_ARMY = choices.get("Player 2", getattr(cfg, "PLAYER2_ARMY", NECRONS_ARMY))
    return choices


def preview_squads(key, owner, state=None):
    """Every unit this list fields for this owner, as a plain list - what the
    selection screen shows portraits and loadouts for.

    Built rather than described: a tile that listed hand-written unit names
    would be a second copy of the army list, and the first thing it would do
    is drift from the one that actually gets built. This calls the SAME
    builder main() calls, so what the tile shows is what turns up on the
    board - including the merged attached units (19.01), which is why the
    Aeldari list shows 13 tiles for 20 entries.

    `state=None` is deliberate: attach() takes an optional game_state only to
    unregister the leader's squad from a board it was never put on."""
    squads = []

    def register(squad, destination=pregame.DEPLOY, transport=None):
        squads.append(squad)
        return squad

    get(key).build(owner, register, state=state)
    return squads
