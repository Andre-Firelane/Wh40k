"""Saving and reloading a board position (game/scene_io.py).

The point of the feature is that a reported failure stops being a hand
reconstruction from log coordinates and becomes a fixture, so the thing to
prove is that a reload really is the same position - not approximately, but
model for model. Every check below therefore compares a full capture of the
scene before and after a round trip, and the scene is built from the REAL
rosters (attached units, a loaded transport, a unit in reserve, casualties),
because those are exactly the shapes a hand-written fixture gets wrong.

Run: python test_scene_io.py
"""

import json
import os
import tempfile

from testkit import Checks, GameState, PHASES, TurnTracker, build_squad

from game import attached_units, config, maps, scene_io
from game.command_points import CommandPointManager
from game.factions.orks import (
    BEAST_SNAGGA_BOYZ, BEASTBOSS, BOYZ, BOYZ_BIG_CHOPPA_TO_POWER_KLAW,
    DEFFKOPTAS, GRETCHIN, KILL_RIG, PAINBOY, WARBOSS,
)

c = Checks("scene snapshots")

# attached_units.attach() renames the merged unit (19.01), so these are the
# names a snapshot actually carries - spelled out once rather than repeated as
# literals, which is how the first version of this suite got them wrong.
MOB = "2 Boyz 1 + Warboss + Painboy"
CARGO = "2 Beast Snagga Boyz 1 + Beastboss"


def head(title):
    print("\n" + "=" * 74 + f"\n{title}\n" + "=" * 74)


def scene():
    """A board with one of everything that a snapshot has to survive: an
    attached unit (19.01), a transport with a unit aboard it (18.02), a unit in
    strategic reserves (03.02), and a plain unit on the board."""
    state = GameState()
    battle_map = maps.apply_to_config(maps.get("map2"))
    battle_map.build(state)

    mob = build_squad(BOYZ, owner="Player 2", composition_index=1,
                      choices={"Boss Nob": {BOYZ_BIG_CHOPPA_TO_POWER_KLAW: 1}},
                      name="2 Boyz 1")
    mob = attached_units.attach(build_squad(WARBOSS, owner="Player 2", name="2 Warboss 1"),
                                mob, game_state=state)
    mob = attached_units.attach(build_squad(PAINBOY, owner="Player 2", name="2 Painboy 1"),
                                mob, game_state=state)

    rig = build_squad(KILL_RIG, owner="Player 2", name="2 Kill Rig 1")
    cargo = attached_units.attach(
        build_squad(BEASTBOSS, owner="Player 2", name="2 Beastboss 1"),
        build_squad(BEAST_SNAGGA_BOYZ, owner="Player 2", name="2 Beast Snagga Boyz 1"),
        game_state=state)
    grots = build_squad(GRETCHIN, owner="Player 2", name="2 Gretchin 1")
    koptas = build_squad(DEFFKOPTAS, owner="Player 2", composition_index=1,
                         name="2 Deffkoptas 1")

    for index, model in enumerate(mob.models):
        model.x_in, model.y_in = 12.0 + (index % 5) * 1.4, 8.0 + (index // 5) * 1.4
    for index, model in enumerate(rig.models):
        model.x_in, model.y_in = 26.0 + index, 9.0
    for index, model in enumerate(grots.models):
        model.x_in, model.y_in = 34.0 + (index % 4) * 1.3, 7.0 + (index // 4) * 1.3
    for index, model in enumerate(cargo.models):  # inert while aboard, still saved
        model.x_in, model.y_in = 26.0, 9.0
    for index, model in enumerate(koptas.models):
        model.x_in, model.y_in = 0.0, 0.0  # in reserve: coordinates are leftovers

    state.tokens = list(mob.models) + list(rig.models) + list(grots.models)
    cargo.embarked_in = rig.models[0]
    state.embarked_squads.append(cargo)
    state.reserves.append(koptas)

    squads = [mob, rig, cargo, grots, koptas]
    return state, squads, {s.name: s for s in squads}


def fingerprint(state, squads):
    """Everything a reload has to reproduce, as a comparable structure. Built
    from the squads rather than from the capture, so the comparison cannot pass
    just because capture() is self-consistent."""
    out = {}
    for squad in squads:
        where = ("reserves" if squad in state.reserves else
                 "embarked" if squad in state.embarked_squads else "board")
        carrier = getattr(squad, "embarked_in", None)
        carrier_squad = getattr(carrier, "squad", None)
        out[squad.name] = {
            "where": where,
            "carrier": getattr(carrier_squad, "name", None),
            "shocked": bool(squad.battle_shocked),
            "models": [(m.x_in, m.y_in, m.current_wounds)
                       for m in squad.models],
            "on_board": [m in state.tokens for m in squad.models],
        }
    return out


def round_trip(state, squads, by_name, tracker=None, points=None):
    """Capture, scramble the scene, restore, and hand back the fingerprint."""
    data = scene_io.capture(state, "map2", tracker, points)
    for squad in squads:  # move everything somewhere else entirely
        for index, model in enumerate(squad.models):
            model.x_in, model.y_in = 2.0 + index * 0.9, 2.0
        squad.battle_shocked = not squad.battle_shocked
    state.tokens = []
    state.reserves.clear()
    state.embarked_squads.clear()
    problems = scene_io.restore(data, state, squads=squads)
    return data, problems


# =====================================================================
head("1. a round trip puts every model back exactly")
# =====================================================================
state, squads, by_name = scene()
by_name["2 Gretchin 1"].battle_shocked = True
by_name[MOB].models[3].current_wounds = 1
before = fingerprint(state, squads)
c.eq("the scene has all five units", len(before), 5)
c.true("it really does have a unit aboard a transport",
       before[CARGO]["where"] == "embarked")
c.eq("and the carrier is recorded by name",
     before[CARGO]["carrier"], "2 Kill Rig 1")
c.true("and one in reserve", before["2 Deffkoptas 1"]["where"] == "reserves")

data, problems = round_trip(state, squads, by_name)
after = fingerprint(state, squads)
c.eq("nothing is reported as mismatched", problems, [])
c.eq("every unit is back where it was", after, before)
c.true("a wounded model kept its wounds",
       after[MOB]["models"][3][2] == 1)
c.true("battle-shocked survived the trip", after["2 Gretchin 1"]["shocked"])
c.true("the embarked unit is out of state.tokens again",
       not any(after[CARGO]["on_board"]))
c.true("the reserve unit is out of state.tokens too",
       not any(after["2 Deffkoptas 1"]["on_board"]))
c.true("the board unit is IN state.tokens",
       all(after[MOB]["on_board"]))

# =====================================================================
head("2. A/B - the scramble really did move things")
# =====================================================================
state, squads, by_name = scene()
original = fingerprint(state, squads)
scene_io.capture(state, "map2")
for squad in squads:
    for index, model in enumerate(squad.models):
        model.x_in, model.y_in = 2.0 + index * 0.9, 2.0
scrambled = fingerprint(state, squads)
c.true("without a restore the positions are different",
       scrambled[MOB]["models"] != original[MOB]["models"])
c.true("...for every unit, so the comparison above is not trivially true",
       all(scrambled[n]["models"] != original[n]["models"]
           for n in original if len(original[n]["models"]) > 1))

# =====================================================================
head("3. casualties: a shorter unit in the snapshot loses its tail")
# =====================================================================
state, squads, by_name = scene()
mob = by_name[MOB]
full = len(mob.models)
data = scene_io.capture(state, "map2")
entry = next(e for e in data["squads"] if e["name"] == MOB)
entry["models"] = entry["models"][:6]
problems = scene_io.restore(data, state, squads=squads)
c.eq("no complaint - fewer models is casualties, not a mismatch", problems, [])
c.eq("the unit is cut down to the snapshot's size", len(mob.models), 6)
c.eq("and the removed models are out of state.tokens",
     sum(1 for m in state.tokens if m.squad is mob), 6)
c.true("the scene really did start bigger", full > 6)

# =====================================================================
head("4. mismatches are reported, not papered over")
# =====================================================================
state, squads, by_name = scene()
data = scene_io.capture(state, "map2")
data["squads"] = [e for e in data["squads"] if e["name"] != "2 Gretchin 1"]
data["squads"].append({"name": "2 Ghost Unit 1", "owner": "Player 2",
                       "placement": "board", "embarked_in": None,
                       "battle_shocked": False, "models": []})
problems = scene_io.restore(data, state, squads=squads)
c.true("a unit the snapshot is missing is reported",
       any("2 Gretchin 1" in p and "the snapshot does not" in p for p in problems))
c.true("a unit the scene does not have is reported",
       any("2 Ghost Unit 1" in p and "the scene does not" in p for p in problems))

state, squads, by_name = scene()
data = scene_io.capture(state, "map2")
entry = next(e for e in data["squads"] if e["name"] == "2 Gretchin 1")
entry["models"] = entry["models"] + [dict(entry["models"][0])]
problems = scene_io.restore(data, state, squads=squads)
c.true("a unit that GREW is reported rather than silently truncated",
       any("2 Gretchin 1" in p and "only" in p for p in problems))

state, squads, by_name = scene()
data = scene_io.capture(state, "map2")
entry = next(e for e in data["squads"] if e["name"] == CARGO)
entry["embarked_in"] = "2 Nonexistent Trukk 1"
problems = scene_io.restore(data, state, squads=squads)
c.true("an embarked unit whose transport is gone is reported",
       any("2 Nonexistent Trukk 1" in p for p in problems))
c.true("...and it is put on the board rather than left nowhere",
       all(m in state.tokens for m in by_name[CARGO].models))

# =====================================================================
head("5. turn state and command points")
# =====================================================================
state, squads, by_name = scene()
tracker = TurnTracker(first_player="Player 1")
tracker.battle_round = 3
tracker.turn_owner = "Player 2"
tracker.phase_index = PHASES.index("Charge")
tracker.set_active("Player 2")
points = CommandPointManager()
points.cp["Player 1"] = 4
points.cp["Player 2"] = 2

data = scene_io.capture(state, "map2", tracker, points)
c.eq("the phase is captured by name", data["turn"]["phase"], "Charge")

fresh = TurnTracker(first_player="Player 1")
fresh_points = CommandPointManager()
problems = scene_io.restore_turn(data, fresh, fresh_points)
c.eq("no complaints", problems, [])
c.eq("battle round restored", fresh.battle_round, 3)
c.eq("phase restored", fresh.phase, "Charge")
c.eq("turn owner restored", fresh.turn_owner, "Player 2")
c.eq("command points restored", dict(fresh_points.cp),
     {"Player 1": 4, "Player 2": 2})

data["turn"]["phase"] = "Elevenses"
problems = scene_io.restore_turn(data, TurnTracker(first_player="Player 1"))
c.true("an unknown phase is reported", any("Elevenses" in p for p in problems))

# =====================================================================
head("6. the file itself")
# =====================================================================
state, squads, by_name = scene()
tracker = TurnTracker(first_player="Player 2")
with tempfile.TemporaryDirectory() as tmp:
    path = scene_io.write(scene_io.capture(state, "map2", tracker), os.path.join(tmp, "s.json"))
    c.true("the file was written", os.path.exists(path))
    raw = json.load(open(path, encoding="utf-8"))
    c.eq("it records which map it was taken on", raw["map"], "map2")
    c.eq("and its format version", raw["format"], scene_io.FORMAT_VERSION)
    c.eq("reading it back gives the same dict", scene_io.read(path), raw)

    raw["format"] = 99
    json.dump(raw, open(path, "w", encoding="utf-8"))
    try:
        scene_io.read(path)
        c.true("a future format version is refused", False)
    except ValueError as exc:
        c.true("a future format version is refused, by name", "format 99" in str(exc))

# =====================================================================
head("7. the live path is wired up")
# =====================================================================
c.true("config carries a LOAD_SCENE slot", hasattr(config, "LOAD_SCENE"))
main_src = open("main.py", encoding="utf-8").read()
c.true("main() reads it", "config.LOAD_SCENE" in main_src)
c.true("F9 saves a snapshot", "pygame.K_F9" in main_src)
c.true("--load is a real argument", '"--load"' in main_src)
c.true("begin_battle runs before the turn state is restored",
       main_src.index("begin_battle((loaded") < main_src.index("scene_io.restore_turn"))
c.true("a snapshot from another map is refused",
       "was saved on" in main_src)

c.finish()
