"""How a written army list is put on the table: the vocabulary a list is written
in (Unit / Leader) and the ONE builder that turns any of them into real Squads.

WHY THIS EXISTS. Every army list used to be its own builder FUNCTION, and the
eight of them came to 1460 lines to express eight lists of ~20 entries. They did
not even share a shape - three different tuple arities, three different escape
hatches for attached units, a hand-recounted magic number per list. Changing one
list meant reading its builder first.

THE ONE THING THAT MADE A TABLE IMPOSSIBLE, and how it is removed. Those
builders registered each unit INSIDE the loop that built it, and rule 19.01's
attach() has to run BEFORE registration so the scene records one merged unit
rather than two. So anything with a character attached had to be lifted out of
the table into hand-written code - which is most of a list. The fix is not
cleverness, it is separating the passes: build everything, then grant, then
attach, then register. build_tau_retaliation() had already found half of this
(its table carried a `leader` column and it had no hand-written blocks at all);
this is that idea with the remaining three cases - two leaders on one unit,
transports, and Enhancements - folded in.

THE FOUR PASSES, and what each one buys:

    1  BUILD      every bodyguard, then its leaders, in roster order.
                  Nothing is attached and nothing is registered yet.
    2  ENHANCE    while each character is STILL ITS OWN SQUAD. After 19.01 a
                  Cadre Fireblade is one model among eleven and
                  enhancements.grant() would have to be told which - it refuses
                  an ambiguous squad rather than guessing, and it is right to.
                  This reason used to be written out at three separate call
                  sites; the pass structure now makes it unsayable-wrong.
    3  ATTACH     19.01, leaders in the order the list wrote them. That order is
                  load-bearing and can_attach() enforces it: a Warlock Conclave
                  JOINS (stating its own limit) and so may join a unit a Farseer
                  already leads, while a plain Farseer may not join a unit
                  something is already attached to.
    4  REGISTER   in roster order, so a carrier is always registered before its
                  passenger and `scene_units` comes out in the order the
                  Pre-game Sequence and every measurement harness expect.

WHAT IS PARAMETERISED. The owner, and nothing else. It decides `owner=` and the
squad-name prefix ("1 Boyz 1" vs "2 Boyz 1"), which is what lets either player
field either list and makes a mirror match two distinct armies.
"""

from game import attached_units, enhancements, pregame
from game.factions import build_squad


class Leader:
    """A CHARACTER bought to join a Unit (19.01).

    `color` is REQUIRED rather than inherited from the unit it joins. Inheriting
    would save a few lines and is wrong in five of the eight shipped lists:
    Aeldari, Necrons, Orks, Death Guard and Retaliation paint their characters
    differently from their bodyguards, while Kauyon, Mont'ka and Prototypes
    happen to match. A default that is right three times out of eight silently
    repaints a character in the other five.
    """

    __slots__ = ("datasheet", "color", "composition_index", "gear", "choices",
                 "enhancement", "note")

    def __init__(self, datasheet, color, composition_index=0, gear=None,
                 choices=None, enhancement=None, note=None):
        self.datasheet = datasheet
        self.color = tuple(color)
        self.composition_index = composition_index
        self.gear = gear
        self.choices = choices
        self.enhancement = enhancement
        self.note = note


class Unit:
    """One line of a written army list: a datasheet, the build it buys, who
    leads it and what carries it.

    `transport` is another Unit from the SAME roster, and it must appear EARLIER
    in it - checked when the list is loaded, not worked around here. That single
    rule is what lets pass 4 be plain roster order and still guarantee a carrier
    is registered before its passenger, which main.py's roster guard requires.

    There is no `destination` field. Only EMBARK is ever used by a written list
    (RESERVES is decided by the Declare Battle Formations step, not by the list),
    so the destination is exactly "EMBARK if it has a transport, else DEPLOY" and
    a second field could only ever disagree with the first.
    """

    __slots__ = ("datasheet", "color", "composition_index", "gear", "choices",
                 "leaders", "transport", "enhancement", "entry_id", "note")

    def __init__(self, datasheet, color, composition_index=0, gear=None,
                 choices=None, leaders=(), transport=None, enhancement=None,
                 entry_id=None, note=None):
        self.datasheet = datasheet
        self.color = tuple(color)
        self.composition_index = composition_index
        self.gear = gear
        self.choices = choices
        self.leaders = tuple(leaders)
        self.transport = transport
        self.enhancement = enhancement
        self.entry_id = entry_id
        self.note = note


def unit_name(owner, text):
    """This army's name for a unit: the owner's digit, then the datasheet name
    and the copy number ("2 Boyz 1").

    One definition because the name is an IDENTIFIER, not a label:
    ai/agent_driver.py's plan orders address units by exact name, game/maps.py's
    partial rosters name them, and game/scene_io.py keys saved scenes on them.
    owner[-1] rather than a lookup table because the two players are "Player 1"
    and "Player 2" everywhere in this engine, and a third would need a great
    deal more than a prefix."""
    return f"{owner[-1]} {text}"


def check_positions(list_name, model_positions, wanted):
    """Refuse --no-deployment loudly when the map's hand-placed table does not
    cover this list.

    `wanted` is now simply len(roster) for every list. It used to be
    hand-maintained per builder and was inconsistent in three different ways:
    Aeldari asked for 5 positions for an 11-unit list, Kauyon asked for 19 while
    consuming 18, and Orks/Necrons/Death Guard passed 0 - which made this guard
    PASS on map3 (whose table is empty) and let the whole army start stacked on
    (0, 0), the exact failure the docstring below says it exists to prevent.

    The tables in game/maps.py are a property of the MAP and were written for a
    Player 1 Aeldari roster that has since been revised twice, so any other
    pairing has no table at all - and the failure without this is silent."""
    if model_positions is None:
        return
    if len(model_positions) != wanted:
        raise SystemExit(
            f"--no-deployment needs one hand-placed position list per unit, and the {list_name} "
            f"list does not have them: this map carries {len(model_positions)} position list(s) "
            f"for {wanted} unit(s). Every army list in this build was written on the "
            "understanding that the Pre-game Sequence (rule 03.01) places it - user: \"nicht "
            "aufstellen, wir haben ja jetzt die spieler aufstellung drin\". Run without "
            "--no-deployment, or add the missing entries to game/maps.py."
        )


def apply_positions(squad, model_positions, index):
    """Hand-place one unit's models, legacy --no-deployment mode only."""
    positions = model_positions[index] if model_positions and index < len(model_positions) else []
    for model, (x_in, y_in) in zip(squad.models, positions):
        model.x_in, model.y_in = x_in, y_in
    return positions


def build(roster, owner, register, list_name="army", state=None, model_positions=None):
    """Put `roster` on the table for `owner`, reporting each finished unit to
    `register`. Returns None - like every builder it replaced, the result is
    delivered through the callback and through mutation.

    `register(squad, destination=pregame.DEPLOY, transport=None)` is main.py's
    recorder. A DEPLOY unit is reported with ONE positional argument and never
    with an explicit destination: four callers in this repo pass a plain
    one-argument callable (a list's own `.append`), and spelling the default out
    would be a TypeError in all four.
    """
    check_positions(list_name, model_positions, len(roster))

    counts = {}

    def next_name(datasheet):
        """The name and the copy number, which are the same running count.

        The published points list charges more for later copies of some units,
        so this decides a price as well as an identifier - which is why there is
        one counter and not one per purpose."""
        counts[datasheet.name] = counts.get(datasheet.name, 0) + 1
        return unit_name(owner, f"{datasheet.name} {counts[datasheet.name]}"), counts[datasheet.name]

    def make(spec, index=None):
        name, unit_index = next_name(spec.datasheet)
        positions = (model_positions[index]
                     if model_positions and index is not None and index < len(model_positions)
                     else [])
        first_x, first_y = positions[0] if positions else (0.0, 0.0)
        squad = build_squad(
            spec.datasheet, owner=owner, composition_index=spec.composition_index,
            gear=spec.gear, choices=spec.choices, name=name,
            x_in=first_x, y_in=first_y, color=spec.color, unit_index=unit_index)
        if index is not None:
            apply_positions(squad, model_positions, index)
        return squad

    # PASS 1 - build. A leader deliberately takes NO model_positions index: the
    # hand-placed table has one entry per LIST ENTRY, and a character that joins
    # a unit is placed with it.
    built = []
    for index, entry in enumerate(roster):
        built.append((entry, make(entry, index), [make(spec) for spec in entry.leaders]))

    # PASS 2 - Enhancements, while every character is still its own squad.
    for entry, squad, leader_squads in built:
        if entry.enhancement:
            enhancements.grant(squad, entry.enhancement)
        for spec, leader_squad in zip(entry.leaders, leader_squads):
            if spec.enhancement:
                enhancements.grant(leader_squad, spec.enhancement)

    # PASS 3 - 19.01. attach() returns the surviving squad and empties the
    # leader's model list, so the result is re-bound rather than assumed to be
    # the same object; that the bodyguard squad happens to be mutated in place
    # today is attach()'s business, not this caller's.
    merged = {}
    for entry, squad, leader_squads in built:
        for leader_squad in leader_squads:
            squad = attached_units.attach(leader_squad, squad, game_state=state)
        merged[id(entry)] = squad

    # PASS 4 - register, in roster order.
    for entry, _, _ in built:
        squad = merged[id(entry)]
        if entry.transport is None:
            register(squad)
        else:
            carrier = merged[id(entry.transport)]
            register(squad, pregame.EMBARK, transport=carrier.models[0])
