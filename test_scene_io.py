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
head("3. casualties: a shorter unit in the snapshot loses the models it "
     "does not name")
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
# WHICH models are the casualties is the whole of test_scene_activation.py's
# first section - trimming the front of the snapshot's list here would leave
# the Warboss and Painboy standing, not the first six Boyz.
c.eq("the casualties are recorded as destroyed, not merely dropped",
     len(mob.destroyed_models), full - 6)
c.true("...at zero wounds, which is how this engine spells destroyed",
       all(m.current_wounds == 0 for m in mob.destroyed_models))

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

# =====================================================================
head("8. a unit destroyed before the save does not come back")
# =====================================================================
# capture() walks the three GameState lists, and a wiped squad is in none of
# them - so it is simply absent from the file. Leaving the rebuilt copy alone
# was nearly harmless on the default path (nothing has been deployed yet, so
# it just sits off-board) and WRONG on the legacy already-deployed one, where
# register_unit() has already put it on the battlefield at full strength.
from game.squad import Squad  # noqa: E402
from game.token import Token  # noqa: E402


class _P:
    name = "Probe"
    wounds = 2
    fly = hover = transport = character = squad_leader = False


class _State:
    def __init__(self):
        self.tokens, self.reserves, self.embarked_squads = [], [], []


def _squad(name, n=1):
    models = [Token(x_in=float(i), y_in=1.0, radius_in=0.5, color=(1, 1, 1), profile=_P())
              for i in range(n)]
    squad = Squad(name, models, owner="Player 1")
    for model in models:
        model.squad = squad
    return squad


alive, doomed = _squad("Alive", 2), _squad("Doomed", 1)
live_state = _State()
live_state.tokens = list(alive.models)      # the sweep already removed `doomed`
wiped = scene_io.capture(live_state, "map2")
c.eq("a destroyed unit is not in the snapshot at all",
     [e["name"] for e in wiped["squads"]], ["Alive"])

a2, d2 = _squad("Alive", 2), _squad("Doomed", 1)
s2 = _State()
problems = scene_io.restore(wiped, s2, squads=[a2, d2])
c.true("the restore says which unit the snapshot did not have",
       any("Doomed" in p for p in problems))
c.eq("...and the rebuilt copy is emptied, which is how this engine spells destroyed",
     len(d2.models), 0)
c.eq("...its models kept as casualties, where the rules read a last position from",
     len(d2.destroyed_models), 1)
c.eq("the surviving unit is restored as normal", len(a2.models), 2)

# The legacy path: register_unit() puts everything on the board up front.
a3, d3 = _squad("Alive", 2), _squad("Doomed", 1)
s3 = _State()
s3.tokens = list(a3.models) + list(d3.models)
scene_io.restore(wiped, s3, squads=[a3, d3])
c.true("a destroyed unit is taken OFF the board, not left standing",
       not any(m in s3.tokens for m in d3.destroyed_models))
c.eq("...and has no models left", len(d3.models), 0)

# The valve. A snapshot of a different roster names nothing in this scene, and
# evicting on that basis would delete both armies.
x, y = _squad("Other", 2), _squad("Else", 1)
s4 = _State()
s4.tokens = list(x.models) + list(y.models)
problems = scene_io.restore(wiped, s4, squads=[x, y])
c.eq("a snapshot from another roster deletes nothing", [len(x.models), len(y.models)], [2, 1])
c.true("...and says why", any("wrong roster" in p for p in problems))
a5, d5 = _squad("Alive", 2), _squad("Doomed", 1)
s5 = _State()
s5.tokens = list(a5.models) + list(d5.models)
scene_io.restore(wiped, s5, squads=[a5, d5], evict_missing=False)
c.eq("...and then the old behaviour is unchanged", len(d5.models), 1)

# =====================================================================
head("9. the mission state survives a round trip")
# =====================================================================
# Without this a resumed battle restarted at 0 VP with a fresh deck, which is
# the gap CLAUDE.md listed as open. The rule that decides what is in here: a
# field scoped to ONE TURN is left out, because the autosave is taken at a
# battle-round boundary where all of them are empty - and several of them
# (pending_pick's callbacks, the id(squad)-keyed sets) could not be written to
# JSON at all.
from game.missions import MissionController  # noqa: E402
from game.primary_missions import DEATH_TRAP_ALL_SLOT, PrimaryMissionController  # noqa: E402
from game.secondary_missions import ALL_CARDS, SecondaryMissionController  # noqa: E402


class _Obj:
    def __init__(self, name):
        self.name = name


class _Area:
    pass


def _mission_set(objectives, areas):
    ledger = MissionController()
    secondary = SecondaryMissionController(
        player="Player 1", mission_controller=ledger, command_points=None,
        decision_manager=None, turn_tracker=None, game_log=None)
    secondary.set_objectives_source(lambda: objectives)
    secondary.set_squads_source(lambda: [])
    primary = PrimaryMissionController(
        player="Player 1", mission_controller=ledger, turn_tracker=None,
        game_log=None, action_controller=None)
    primary.set_terrain_source(lambda: areas)
    return {"ledger": ledger, "secondary": secondary, "primary": primary}


objs = [_Obj("Central Objective"), _Obj("Objective East")]
areas = [_Area(), _Area(), _Area()]
before = _mission_set(objs, areas)
before["ledger"].primary_points["Player 1"] = 13
before["ledger"].secondary_points["Player 1"] = 8
before["ledger"]._unscored_kills["Player 1"] = 2
sec = before["secondary"]
sec.hand = [ALL_CARDS[0], ALL_CARDS[1]]
sec.discarded = [ALL_CARDS[2]]
sec.deck = [card for card in ALL_CARDS if card not in sec.hand + sec.discarded]
sec._drawn_round, sec._scored_round, sec._scored_vp_this_round = 3, 3, 7
sec.card_state.setdefault("a_tempting_target", {})["objective"] = objs[1]
pri = before["primary"]
pri.points, pri._battle_scored = 11, True
pri.card_state[DEATH_TRAP_ALL_SLOT] = {id(areas[2]): areas[2], id(areas[0]): areas[0]}

saved = scene_io.capture(_State(), "map2", missions=before)
c.eq("every controller gets its own slot", sorted(saved["missions"]), ["ledger", "primary", "secondary"])
# Cards are module-level singletons shared by every battle, so they go by key.
c.true("cards are stored by key, not pickled",
       all(isinstance(k, str) for k in saved["missions"]["secondary"]["deck"]))
# A TerrainArea has no name, so the trapped set goes by index into the list
# battle_map.build() produces - deterministic for a given map key, which the
# snapshot pins.
c.eq("trapped ground is stored as indices", saved["missions"]["primary"]["trapped"], [0, 2])
c.true("turn-scoped card state is NOT stored",
       "guards" not in json.dumps(saved["missions"]) and "_this_turn" not in json.dumps(saved["missions"]))

objs2 = [_Obj("Central Objective"), _Obj("Objective East")]
areas2 = [_Area(), _Area(), _Area()]
after = _mission_set(objs2, areas2)
problems = scene_io.restore_missions(saved, after)
c.eq("a clean round trip complains about nothing", problems, [])
c.eq("the VP ledger comes back", after["ledger"].primary_points["Player 1"], 13)
c.eq("...both halves", after["ledger"].secondary_points["Player 1"], 8)
c.eq("...including kills banked but not yet scored", after["ledger"]._unscored_kills["Player 1"], 2)
c.eq("the hand comes back", [card.key for card in after["secondary"].hand],
     [card.key for card in sec.hand])
c.eq("the discard pile comes back", [card.key for card in after["secondary"].discarded],
     [card.key for card in sec.discarded])
# ORDER matters: the deck is drawn from the top with pop(0), so a reshuffle on
# load would deal a different battle.
c.eq("the deck comes back IN ORDER", [card.key for card in after["secondary"].deck],
     [card.key for card in sec.deck])
c.eq("the round ledgers come back",
     [after["secondary"]._drawn_round, after["secondary"]._scored_round,
      after["secondary"]._scored_vp_this_round], [3, 3, 7])
c.true("a WHEN DRAWN pick resolves to the SAME objective in the new scene",
       after["secondary"].card_state["a_tempting_target"]["objective"] is objs2[1])
c.eq("the Primary's running score comes back", after["primary"].points, 11)
c.true("...and its once-per-battle latch", after["primary"]._battle_scored)
c.eq("trapped ground resolves back to the same areas",
     sorted(areas2.index(a) for a in after["primary"].card_state[DEATH_TRAP_ALL_SLOT].values()),
     [0, 2])

# A snapshot written before any of this existed has no "missions" section and
# must restore exactly as it always did - the same promise `armies` makes, and
# the reason FORMAT_VERSION does not move.
old_style = scene_io.capture(_State(), "map2")
c.true("an older snapshot carries no mission section", "missions" not in old_style)
untouched = _mission_set(objs2, areas2)
c.eq("...and restoring one changes nothing", scene_io.restore_missions(old_style, untouched), [])
c.eq("...leaving the score at zero", untouched["ledger"].primary_points["Player 1"], 0)

# A pick whose target is gone is reported, not guessed at.
gone = _mission_set([_Obj("Central Objective")], areas2)
problems = scene_io.restore_missions(saved, gone)
c.true("a pick that is not in this scene is reported",
       any("Objective East" in p for p in problems))
c.true("...and the card is simply left without one",
       gone["secondary"].card_state.get("a_tempting_target", {}).get("objective") is None)

c.true("main() restores the missions after begin_battle()",
       main_src.index("begin_battle((loaded") < main_src.index("scene_io.restore_missions"))
c.eq("there is ONE definition of which controller fills which slot",
     main_src.count("def _mission_slots("), 1)

c.finish()
