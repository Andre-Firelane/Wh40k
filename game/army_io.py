"""Army lists on disk: reading, validating and writing the JSON files in
`armies/`.

WHY ON DISK AND NOT IN SOURCE. This game is meant to become an executable, and a
Python module is baked INTO that executable when it is built - so a list
imported afterwards could not be added without writing source into a frozen
bundle, and executing an imported .py would be a code-execution path for a file
that came from somewhere else. A written army list carries no behaviour (unlike
a datasheet, which carries real callbacks - `_equip_shimmershield(token)` and
its kind), so it is data, and data belongs where the saved games are.

game/scene_io.py is the model this follows deliberately, down to the details
that matter for a packaged build:

    ARMIES_DIR is read AT CALL TIME, never captured as a default argument, so a
    packaged build can point it at a writable user directory at startup - the
    same reason scene_io says "not baked into the default" about SCENES_DIR.

    FORMAT_VERSION is refused loudly on mismatch rather than guessed at.

WHY NAMES AND NOT SYMBOLS. Everything a list refers to - a datasheet, a wargear
option, a gear item, an Enhancement - is named by the string that is already its
identity in the engine (the wargear constants in game/factions/*.py are literally
these strings: FARSEER_WITCHBLADE_TO_SPEAR is "Witchblade -> Singing Spear").
What a Python constant bought was a NameError on a typo; what validate() gives
instead is strictly more: every problem in the file at once, each naming the
datasheet that does not offer the option - which a NameError cannot do.

WHERE VALIDATION RUNS: at LOAD. Not in the builder, because a roster is built by
preview_squads() when the army-select screen is merely HOVERED
(game/ui/army_select.py), and a bad file must not raise inside a render frame.

LOUD OR SKIPPED, and the difference is deliberate. load() raises: a shipped list
that does not validate is a bug in this build. scan() reports and SKIPS: one bad
imported file must not stop the other seven from being playable.
"""

import io
import json
import os

from game import enhancements, force_dispositions
from game.army_roster import Leader, Unit
from game.factions.faction import get_faction

# The faction registry is populated as a SIDE EFFECT of importing each faction
# module, and nothing imports the five eagerly. Without these, get_faction()
# answers None in a fresh process and every roster silently fails to resolve -
# the same trap game/rules_text.py hit, where it quietly returned [] instead of
# a datasheet's rules. Imported for the registration, not for the names.
from game.factions import aeldari as _aeldari  # noqa: F401
from game.factions import death_guard as _death_guard  # noqa: F401
from game.factions import necrons as _necrons  # noqa: F401
from game.factions import orks as _orks  # noqa: F401
from game.factions import tau_empire as _tau_empire  # noqa: F401

FORMAT_VERSION = 1

#: Where the .json files live. Read at CALL TIME, never captured as a default
#: argument, so a packaged build can point it at a writable user directory at
#: startup - see the module docstring.
#:
#: Anchored to the repo root rather than left relative to the working directory,
#: which game/scene_io.py can afford because it only touches its directory when
#: somebody saves. This one is scanned when game/army_lists.py is IMPORTED, so a
#: relative path would make importing it from any other directory kill the
#: process - measured, not guessed.
ARMIES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "armies")


class ArmyFile:
    """One loaded army list: its registry metadata plus the resolved roster.

    The metadata lives in the FILE rather than in a table in source because an
    importer has to be able to produce a complete, playable list without anyone
    editing code - which is the whole reason these are files.
    """

    __slots__ = ("key", "name", "faction_keyword", "army_rule", "detachments",
                 "force_disposition", "sort_order", "note", "roster", "path")

    def __init__(self, key, name, faction_keyword, army_rule, detachments,
                 force_disposition, sort_order, note, roster, path):
        self.key = key
        self.name = name
        self.faction_keyword = faction_keyword
        self.army_rule = army_rule
        self.detachments = tuple(detachments)
        self.force_disposition = force_disposition
        self.sort_order = sort_order
        self.note = note
        self.roster = roster
        self.path = path


class ArmyFileError(Exception):
    """A file that cannot be turned into a playable list, carrying EVERY reason
    rather than the first - fixing a list one error per run is how a small edit
    turns into an afternoon."""

    def __init__(self, path, problems):
        self.path = path
        self.problems = list(problems)
        super().__init__(
            "%s is not a usable army list:\n  - %s" % (path, "\n  - ".join(self.problems))
        )


# --- reading -------------------------------------------------------------


def read(path):
    """The raw JSON, with the format version enforced."""
    with io.open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if data.get("format") != FORMAT_VERSION:
        raise ValueError(
            "%s is format %r, this build reads format %d"
            % (path, data.get("format"), FORMAT_VERSION)
        )
    return data


def load(path):
    """One army list, resolved and validated. Raises ArmyFileError listing every
    problem."""
    data = read(path)
    army, problems = parse(data, path)
    if problems:
        raise ArmyFileError(path, problems)
    return army


def summary(path):
    """(key, name) for a file that loads, or None for one that does not - the
    shape game/scene_io.py uses for the same job, so a chooser can offer only
    what it can actually open."""
    try:
        army = load(path)
    except Exception:
        return None
    return army.key, army.name


def scan(directory=None):
    """Every usable list in `directory`, ordered by (sort_order, key), plus the
    problems of the ones that were skipped.

    Returns (armies, problems). Ordering is explicit rather than alphabetical so
    the shipped lists keep the order the army-select screen has always
    shown them in, and an imported list lands at the end instead of in the
    middle of the T'au."""
    directory = directory if directory is not None else ARMIES_DIR
    armies, problems = [], []
    if not os.path.isdir(directory):
        return armies, ["%s does not exist" % directory]
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(directory, name)
        try:
            armies.append(load(path))
        except Exception as exc:  # a bad import must not take the others down
            problems.append(str(exc))
    armies.sort(key=lambda a: (a.sort_order, a.key))
    return armies, problems


# --- parsing and validation ----------------------------------------------


def parse(data, path="<data>"):
    """(ArmyFile, problems). Resolves every name to the object it denotes and
    collects everything wrong rather than stopping at the first."""
    problems = []

    def need(field):
        value = data.get(field)
        if value in (None, ""):
            problems.append("missing %r" % field)
        return value

    key = need("key")
    name = need("name")
    faction_keyword = need("faction_keyword")
    army_rule = data.get("army_rule") or ""
    detachments = tuple(data.get("detachments") or ())
    disposition = data.get("force_disposition")
    sort_order = data.get("sort_order", 1000)

    faction = get_faction(faction_keyword) if faction_keyword else None
    if faction_keyword and faction is None:
        problems.append(
            "faction_keyword %r is not a faction this build knows (%s)"
            % (faction_keyword, ", ".join(sorted(_known_factions())) or "none registered")
        )

    if disposition is not None and not force_dispositions.is_valid(disposition):
        problems.append(
            "force_disposition %r is not one of %s"
            % (disposition, ", ".join(force_dispositions.ALL))
        )

    roster = []
    if faction is not None:
        roster = _parse_roster(data.get("roster") or [], faction, detachments, problems)

    army = ArmyFile(key, name, faction_keyword, army_rule, detachments,
                    disposition, sort_order, data.get("note"), roster, path)
    return army, problems


def _known_factions():
    from game.factions.faction import FACTIONS
    return FACTIONS.keys()


def _parse_roster(entries, faction, detachments, problems):
    roster = []
    by_id = {}

    for index, raw in enumerate(entries):
        where = "roster[%d]" % index
        unit = _parse_entry(raw, faction, detachments, problems, where, leaders_allowed=True)
        if unit is None:
            continue

        entry_id = raw.get("id")
        if entry_id is not None:
            if entry_id in by_id:
                problems.append("%s: duplicate id %r" % (where, entry_id))
            by_id[entry_id] = unit
        unit.entry_id = entry_id
        roster.append((unit, raw.get("transport"), where))

    # Transports resolve in a second pass so an entry may only ever name a
    # carrier that appears EARLIER - which is what lets the builder register in
    # plain roster order and still guarantee the carrier is registered first.
    seen = set()
    units = []
    for unit, transport_id, where in roster:
        if transport_id is not None:
            if transport_id not in by_id:
                problems.append("%s: transport %r names no entry in this roster" % (where, transport_id))
            elif transport_id not in seen:
                problems.append(
                    "%s: transport %r is declared LATER in the roster; a carrier must come first, "
                    "or it would be registered after its passenger" % (where, transport_id)
                )
            else:
                unit.transport = by_id[transport_id]
        if unit.entry_id is not None:
            seen.add(unit.entry_id)
        units.append(unit)
    return units


def _parse_entry(raw, faction, detachments, problems, where, leaders_allowed):
    datasheet = _datasheet(raw.get("datasheet"), faction, problems, where)
    # A bad colour must not stop the rest of this entry being checked: without
    # the datasheet nothing else can be resolved, but with it everything else
    # can - and an entry that reported only "bad colour", hiding a misspelt
    # drone underneath it, would break this module's one promise.
    color = _color(raw.get("color"), problems, where)
    if datasheet is None:
        return None

    composition = raw.get("composition_index", 0)
    compositions = datasheet.compositions()
    if not isinstance(composition, int) or not 0 <= composition < len(compositions):
        problems.append("%s: composition_index %r, %s has %d"
                        % (where, composition, datasheet.name, len(compositions)))
        composition = 0

    gear = _gear(raw.get("gear"), datasheet, problems, where)
    choices = _choices(raw.get("choices"), datasheet, compositions[composition], problems, where)
    enhancement = _enhancement(raw.get("enhancement"), detachments, problems, where)

    leaders = []
    for i, spec in enumerate(raw.get("leaders") or ()):
        if not leaders_allowed:
            problems.append("%s: a leader cannot itself have leaders" % where)
            break
        led = _parse_entry(spec, faction, detachments, problems,
                           "%s.leaders[%d]" % (where, i), leaders_allowed=False)
        if led is not None:
            leaders.append(Leader(led.datasheet, led.color, led.composition_index,
                                  led.gear, led.choices, led.enhancement, spec.get("note")))

    if color is None:
        return None
    return Unit(datasheet, color, composition, gear, choices, leaders,
                None, enhancement, raw.get("id"), raw.get("note"))


def _datasheet(name, faction, problems, where):
    if not name:
        problems.append("%s: missing 'datasheet'" % where)
        return None
    sheet = faction.datasheets.get(name)
    if sheet is None:
        problems.append("%s: %r is not a %s datasheet%s"
                        % (where, name, faction.name, _did_you_mean(name, faction.datasheets)))
    return sheet


def _color(value, problems, where):
    if (not isinstance(value, (list, tuple)) or len(value) != 3
            or not all(isinstance(c, int) and 0 <= c <= 255 for c in value)):
        problems.append("%s: 'color' must be three 0-255 integers, got %r" % (where, value))
        return None
    return tuple(value)


def _gear(value, datasheet, problems, where):
    if not value:
        return None
    out = {}
    for line_name, items in value.items():
        offered = {g.name for g in datasheet.gear_for(line_name)}
        if not offered:
            problems.append("%s: %s offers no gear on a line called %r%s"
                            % (where, datasheet.name, line_name,
                               _did_you_mean(line_name, _gear_lines(datasheet))))
            continue
        for item in items:
            if item not in offered:
                problems.append("%s: %s's %r does not offer gear %r%s"
                                % (where, datasheet.name, line_name, item,
                                   _did_you_mean(item, offered)))
        out[line_name] = list(items)
    return out


def _choices(value, datasheet, lines, problems, where):
    if not value:
        return None
    line_names = {line.name for line in lines}
    out = {}
    for line_name, picks in value.items():
        if line_name not in line_names:
            problems.append("%s: %s has no model line %r in this composition%s"
                            % (where, datasheet.name, line_name,
                               _did_you_mean(line_name, line_names)))
            continue
        offered = {o.name for o in datasheet.wargear_for(line_name)}
        for option, count in picks.items():
            if option not in offered:
                problems.append("%s: %s's %r does not offer wargear option %r%s"
                                % (where, datasheet.name, line_name, option,
                                   _did_you_mean(option, offered)))
            if isinstance(count, bool) or not isinstance(count, (int, list, tuple)):
                problems.append("%s: %r must be a model count or a list of model indices, got %r"
                                % (where, option, count))
        # Model-index lists survive as lists; build_squad() accepts either shape.
        out[line_name] = dict(picks)
    return out


def _enhancement(name, detachments, problems, where):
    if not name:
        return None
    try:
        spec = enhancements.get(name)
    except KeyError:
        problems.append("%s: %r is not an engine-wired Enhancement" % (where, name))
        return None
    # The check that nothing did before: an Enhancement whose detachment this
    # list does not field is granted, costs its points, and then is_active()
    # quietly answers False forever. This is the real replacement for the
    # hand-maintained whitelist the T'au builders used to carry.
    if detachments and spec.detachment not in detachments:
        problems.append(
            "%s: %r belongs to the %s detachment, which this list does not field (%s)"
            % (where, name, spec.detachment, ", ".join(detachments))
        )
        return None
    return name


def _gear_lines(datasheet):
    return {g.model_line_name for g in datasheet.gear_options}


def _did_you_mean(value, candidates):
    """A suggestion, or "". Case- and punctuation-insensitive, because the two
    ways to mistype a name here are capitalisation and the apostrophe in
    "Shas'ui" / "Mont'ka"."""
    import difflib
    folded = {_fold(c): c for c in candidates}
    match = difflib.get_close_matches(_fold(value or ""), list(folded), n=1, cutoff=0.7)
    return ". Did you mean %r?" % folded[match[0]] if match else ""


def _fold(text):
    return "".join(ch for ch in str(text).lower() if ch.isalnum())


# --- writing -------------------------------------------------------------


def write(army_data, path):
    """Write a list back out - what an importer will use. Stable key order and a
    trailing newline so two writes of the same list are byte-identical and a
    diff shows only what really changed."""
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(army_data, handle, indent=2, ensure_ascii=False, sort_keys=False)
        handle.write("\n")
