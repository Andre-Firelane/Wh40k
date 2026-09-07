"""What a save has to bring back besides coordinates.

Two user reports, one session:

  1. "schaden auf einheiten wurde nicht gespeichert"
  2. "es wurde nicht gespeichert, wer schon welche aktion ausgefuehrt hat.
     zb wer schon geschossen hat und wer nicht"

The first one was NOT a missing field - every model's remaining wounds were in
the file all along. They were being put back on the WRONG MODEL: a snapshot
holds a unit's survivors, the scene it loads into holds the unit as built, and
pairing them off in order gives a character's wounds to whichever trooper sat
at that index. Section 1 drives the exact unit out of the user's own save file.

The second one was a missing section outright, and it is the one that needs a
source guard rather than a behaviour test: a NINTH activation ledger can be
added tomorrow, and no behaviour test can fail for a ledger that does not
exist yet. Section 5 is that guard.

Run: python test_scene_activation.py
"""

import copy
import json

from testkit import Checks, GameState, PHASES, TurnTracker, build_squad

from game import activation_state, attached_units, maps, scene_io
from game.factions.necrons import SKORPEKH_DESTROYERS, SKORPEKH_LORD
from game.factions.aeldari import (
    STORM_GUARDIAN_PISTOL_TO_FLAMER, STORM_GUARDIAN_PISTOL_TO_FUSION,
    STORM_GUARDIANS,
)
from game.movement import MovementController
from game.shooting import ShootingController
from game.charge import ChargeController

c = Checks("save/load: damage and activation")

SKORPEKH = "2 Skorpekh Destroyers 1 + Skorpekh Lord"


def head(title):
    print("\n" + "=" * 74 + f"\n{title}\n" + "=" * 74)


def board():
    state = GameState()
    maps.apply_to_config(maps.get("map2")).build(state)
    return state


def skorpekh(state):
    """The unit out of the user's own save: three 3-wound Destroyers with a
    7-wound Lord attached, and rule 19.01 puts the Lord LAST."""
    squad = attached_units.attach(
        build_squad(SKORPEKH_LORD, owner="Player 2", name="2 Skorpekh Lord 1"),
        build_squad(SKORPEKH_DESTROYERS, owner="Player 2",
                    name="2 Skorpekh Destroyers 1"),
        game_state=state)
    for index, model in enumerate(squad.models):
        model.x_in, model.y_in = 20.0 + index * 1.6, 20.0
        state.tokens.append(model)
    return squad


def kill(squad, state, model):
    """What a battle leaves behind: off the board and off squad.models, but
    still on destroyed_models with its last position."""
    squad.models.remove(model)
    if model in state.tokens:
        state.tokens.remove(model)
    model.current_wounds = 0
    squad.destroyed_models.append(model)


def strip_identity(data):
    """A snapshot written before models carried an identity - which is what
    every file already on disk is, and the A/B world for section 1."""
    older = copy.deepcopy(data)
    for entry in older["squads"]:
        for model in entry["models"]:
            model.pop("model", None)
            model.pop("weapons", None)
    return older


# =====================================================================
head("1. the reported unit: the survivor is the LORD, not a trooper")
# =====================================================================
state = board()
squad = skorpekh(state)
c.eq("as built: three Destroyers then the Lord",
     [m.profile.name for m in squad.models],
     ["Skorpekh Destroyer"] * 3 + ["Skorpekh Lord"])
c.true("...and the Lord has more wounds than a Destroyer",
       squad.models[-1].profile.wounds > squad.models[0].profile.wounds)

# Exactly the state in scenes/scene_20260904_214638.json: one model left,
# on 5 wounds. The three Destroyers are dead; the survivor is the Lord.
lord = squad.models[-1]
for model in list(squad.models[:-1]):
    kill(squad, state, model)
lord.current_wounds = 5
lord.x_in, lord.y_in = 31.5, 17.25

data = scene_io.capture(state, "map2")
entry = next(e for e in data["squads"] if e["name"] == SKORPEKH)
c.eq("the snapshot holds one model", len(entry["models"]), 1)
c.eq("...and says WHICH model it is", entry["models"][0]["model"], "Skorpekh Lord")
c.eq("...on 5 wounds", entry["models"][0]["wounds"], 5)

fresh_state = board()
fresh = skorpekh(fresh_state)
problems = scene_io.restore(data, fresh_state, squads=[fresh])
c.eq("no complaints", problems, [])
c.eq("the survivor is the Skorpekh Lord",
     [m.profile.name for m in fresh.models], ["Skorpekh Lord"])
c.eq("...restored on its 5 of 7 wounds", fresh.models[0].current_wounds, 5)
c.true("...which is at or below its own maximum",
       fresh.models[0].current_wounds <= fresh.models[0].profile.wounds)
c.eq("the three casualties are the Destroyers",
     sorted(m.profile.name for m in fresh.destroyed_models),
     ["Skorpekh Destroyer"] * 3)
c.eq("...and none of them is on the board",
     sum(1 for m in fresh_state.tokens if m.squad is fresh), 1)

# A/B: the same file without the identity is the world the report came from.
fresh_state = board()
fresh = skorpekh(fresh_state)
scene_io.restore(strip_identity(data), fresh_state, squads=[fresh])
c.eq("A/B - without an identity the survivor is a TROOPER, as reported",
     [m.profile.name for m in fresh.models], ["Skorpekh Destroyer"])
c.eq("...and the Lord is the model that was deleted instead",
     sorted(m.profile.name for m in fresh.destroyed_models),
     ["Skorpekh Destroyer", "Skorpekh Destroyer", "Skorpekh Lord"])
c.eq("...but the clamp keeps it off 5/3, i.e. healthier than it was saved",
     fresh.models[0].current_wounds, 3)

# =====================================================================
head("2. wargear tells identical datasheet lines apart")
# =====================================================================
# Storm Guardians are ten models off ONE line; two of them carry a special
# weapon. Matching on the datasheet name alone would happily hand the fusion
# gunner's place to a plain Guardian.
state = board()
guardians = build_squad(
    STORM_GUARDIANS, owner="Player 1", name="1 Storm Guardians 1",
    choices={"Storm Guardian": {STORM_GUARDIAN_PISTOL_TO_FUSION: 1,
                                STORM_GUARDIAN_PISTOL_TO_FLAMER: 1}})
for index, model in enumerate(guardians.models):
    model.x_in, model.y_in = 10.0 + index * 1.2, 30.0
    state.tokens.append(model)


def weapon_names(model):
    return sorted(w.name for w in model.weapons)


special = [m for m in guardians.models
           if any("Fusion" in w.name or "Flamer" in w.name for w in m.weapons)]
c.eq("the unit really does carry two special weapons", len(special), 2)
c.true("...and they are the first models built, which is what makes the "
       "name-only fallback look right until it is not",
       guardians.models.index(special[0]) < 2)

# Kill the FUSION gunner and three plain Guardians. That is the arrangement
# that separates the two ideas: the flamer model is now the first surviving
# "Storm Guardian", so matching on the datasheet name alone would hand it the
# fusion gunner's build slot and give it the wrong gun back. (Killing only
# plain models happens to come out right, which is why this suite does not.)
kill(guardians, state, special[0])
for model in [m for m in guardians.models if m not in special][:3]:
    kill(guardians, state, model)
survivors = [(m.profile.name, tuple(weapon_names(m))) for m in guardians.models]

data = scene_io.capture(state, "map2")
fresh_state = board()
fresh = build_squad(
    STORM_GUARDIANS, owner="Player 1", name="1 Storm Guardians 1",
    choices={"Storm Guardian": {STORM_GUARDIAN_PISTOL_TO_FUSION: 1,
                                STORM_GUARDIAN_PISTOL_TO_FLAMER: 1}})
for model in fresh.models:
    fresh_state.tokens.append(model)
problems = scene_io.restore(data, fresh_state, squads=[fresh])
c.eq("no complaints", problems, [])
c.eq("every survivor comes back with the weapons it had",
     [(m.profile.name, tuple(weapon_names(m))) for m in fresh.models], survivors)

fresh_state = board()
fresh = build_squad(
    STORM_GUARDIANS, owner="Player 1", name="1 Storm Guardians 1",
    choices={"Storm Guardian": {STORM_GUARDIAN_PISTOL_TO_FUSION: 1,
                                STORM_GUARDIAN_PISTOL_TO_FLAMER: 1}})
for model in fresh.models:
    fresh_state.tokens.append(model)
scene_io.restore(strip_identity(data), fresh_state, squads=[fresh])
c.true("A/B - without an identity the special weapons are the ones deleted",
       [(m.profile.name, tuple(weapon_names(m))) for m in fresh.models] != survivors)

# =====================================================================
head("3. a casualty is restored as a casualty, not merely dropped")
# =====================================================================
state = board()
squad = skorpekh(state)
lord = squad.models[-1]
kill(squad, state, squad.models[0])
data = scene_io.capture(state, "map2")

fresh_state = board()
fresh = skorpekh(fresh_state)
scene_io.restore(data, fresh_state, squads=[fresh])
c.eq("the dead model is on destroyed_models", len(fresh.destroyed_models), 1)
# Read through a padded copy: indexing an empty list would ABORT the suite
# instead of reddening it, and a probe that crashes hides which check broke.
dead = (fresh.destroyed_models or [None])[0]
c.eq("...at zero wounds, which is how this engine spells destroyed",
     getattr(dead, "current_wounds", None), 0)
c.true("...and is_dead() agrees", dead is not None and dead.is_dead())
c.true("...and it is off the board",
       dead is not None and dead not in fresh_state.tokens)
c.true("this matters: Reanimation Protocols and Undying Legions bring models "
       "back off exactly that list", bool(fresh.destroyed_models))

# =====================================================================
head("4. who has already acted, through the real controllers")
# =====================================================================
state = board()
squad = skorpekh(state)
other = build_squad(SKORPEKH_DESTROYERS, owner="Player 2",
                    name="2 Skorpekh Destroyers 2")
for index, model in enumerate(other.models):
    model.x_in, model.y_in = 26.0 + index * 1.6, 24.0
    state.tokens.append(model)

tracker = TurnTracker(first_player="Player 2")
tracker.phase_index = PHASES.index("Movement")


def controllers(tracker, state):
    return {
        "movement": MovementController(turn_tracker=tracker,
                                       all_tokens=state.tokens),
        "shooting": ShootingController(turn_tracker=tracker,
                                       all_tokens=state.tokens),
        "charge": ChargeController(turn_tracker=tracker,
                                   all_tokens=state.tokens),
    }


live = controllers(tracker, state)
c.true("before anything happens the unit may move",
       live["movement"].can_move(squad))

live["movement"].moved_squad_ids.add(squad)
live["movement"].advanced_squad_ids.add(squad)
live["movement"].moved_distance_this_turn[squad] = 7.5
live["movement"].advance_bonus_by_squad[squad] = 4
live["movement"].stationary_squad_ids.add(other)
live["shooting"].shot_squad_ids.add(squad)
live["shooting"].last_ranged_attack_turn[squad] = 3
live["charge"].charged_squad_ids.add(other)
squad.charged_this_turn = True
squad.set_up_this_turn = True
other.ere_we_go_active = True
other.aspect_shrine_tokens_used = 1

c.true("...and after moving it may not", not live["movement"].can_move(squad))

data = scene_io.capture(state, "map2", activation=live)
c.true("the snapshot has an activation section", "activation" in data)
ledgers = (data.get("activation") or {}).get("controllers") or {}
c.true("...naming the controller ledgers",
       set(ledgers) == {"movement", "shooting", "charge"})
c.eq("...and the unit that shot, by name",
     (ledgers.get("shooting") or {}).get("shot_squad_ids"), [SKORPEKH])

fresh_state = board()
fresh = skorpekh(fresh_state)
fresh_other = build_squad(SKORPEKH_DESTROYERS, owner="Player 2",
                          name="2 Skorpekh Destroyers 2")
for model in fresh_other.models:
    fresh_state.tokens.append(model)
fresh_tracker = TurnTracker(first_player="Player 2")
fresh_tracker.phase_index = PHASES.index("Movement")
new = controllers(fresh_tracker, fresh_state)

c.true("a fresh scene would let the unit move again - the reported bug",
       new["movement"].can_move(fresh))

problems = scene_io.restore_activation(data, [fresh, fresh_other], new)
c.eq("no complaints", problems, [])
c.true("after the restore the unit has already moved",
       not new["movement"].can_move(fresh))
c.true("...and is on the shot list", fresh in new["shooting"].shot_squad_ids)
c.true("...and on the advanced list", fresh in new["movement"].advanced_squad_ids)
c.eq("...with the distance [HEAVY] reads (24.16)",
     new["movement"].moved_distance_this_turn.get(fresh), 7.5)
c.eq("...and the Advance roll it already made (09.06)",
     new["movement"].advance_bonus_by_squad.get(fresh), 4)
c.eq("...and the turn it last fired, which is what ends Hidden (13.09)",
     new["shooting"].last_ranged_attack_turn.get(fresh), 3)
c.true("the other unit remained stationary",
       fresh_other in new["movement"].stationary_squad_ids)
c.true("...and had declared a charge",
       fresh_other in new["charge"].charged_squad_ids)
c.true("the unit's own charged_this_turn flag is back (11.04)",
       fresh.charged_this_turn)
c.true("...and set_up_this_turn, which begin_battle() would have cleared (18.02)",
       fresh.set_up_this_turn)
c.true("a stratagem paid for until the end of the turn is still on",
       fresh_other.ere_we_go_active)
c.eq("...and a once-per-battle token stays spent",
     fresh_other.aspect_shrine_tokens_used, 1)

# The negative: a unit that did nothing gets nothing back.
c.true("a unit that did not move can still move",
       new["movement"].can_move(fresh_other))
c.true("...and is not on the shot list",
       fresh_other not in new["shooting"].shot_squad_ids)

# A/B: the section removed is the world the report came from.
fresh_tracker2 = TurnTracker(first_player="Player 2")
fresh_tracker2.phase_index = PHASES.index("Movement")
new2 = controllers(fresh_tracker2, fresh_state)
fresh.charged_this_turn = False
fresh.set_up_this_turn = False
fresh_other.ere_we_go_active = False
fresh_other.aspect_shrine_tokens_used = 0
scene_io.restore_activation({}, [fresh, fresh_other], new2)
c.true("A/B - with no activation section the unit may move again",
       new2["movement"].can_move(fresh))
c.true("...and may shoot again", fresh not in new2["shooting"].shot_squad_ids)
c.true("...and its charged_this_turn is gone", not fresh.charged_this_turn)

# An untouched board writes nothing, so a start-of-round autosave is the size
# it always was.
clean_state = board()
clean = skorpekh(clean_state)
clean_data = scene_io.capture(clean_state, "map2",
                              activation=controllers(tracker, clean_state))
c.true("an untouched board writes no activation section at all",
       "activation" not in clean_data)

# A name the scene does not have is reported, not guessed at.
broken = copy.deepcopy(data)
broken.setdefault("activation", {}).setdefault("controllers", {}).setdefault(
    "shooting", {})["shot_squad_ids"] = ["2 Ghost 1"]
problems = scene_io.restore_activation(broken, [fresh, fresh_other],
                                       controllers(fresh_tracker, fresh_state))
c.true("a ledger naming a unit this scene does not have is reported",
       any("2 Ghost 1" in p for p in problems))

# =====================================================================
head("5. the source guard: nothing can be added and forgotten")
# =====================================================================
# A behaviour test cannot fail for the ninth ledger, because it does not exist
# yet. These two can.
import ast

squad_src = open("game/squad.py", encoding="utf-8").read()
assigned = []
for node in ast.walk(ast.parse(squad_src)):
    if isinstance(node, ast.ClassDef) and node.name == "Squad":
        for fn in node.body:
            if isinstance(fn, ast.FunctionDef) and fn.name == "__init__":
                for stmt in fn.body:
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if (isinstance(target, ast.Attribute)
                                    and getattr(target.value, "id", None) == "self"):
                                assigned.append(target.attr)
known = set(activation_state.SQUAD_FLAGS) | set(activation_state.SQUAD_FLAGS_EXCLUDED)
c.true("the sweep found Squad's fields at all", len(assigned) > 20)
c.eq("every field Squad.__init__ sets is either saved or excluded WITH A REASON",
     sorted(f for f in assigned if f not in known), [])
c.eq("...and neither list names a field Squad does not have",
     sorted(known - set(assigned)), [])

# Every set-of-squads ledger in game/ has to be in the table - which is the
# check that fails when a ninth one is written.
import os
import re

LEDGER_FIELDS = {field for fields in activation_state.LEDGERS.values()
                 for field, _kind in fields}
# Deliberately out: not every "set of squads" is an activation record. Each
# entry says why, so an excuse cannot quietly outlive its reason.
NOT_ACTIVATION = {
    "_destroyed_squad_ids": "a kill ledger, restored with the mission state",
    "rolled_squad_ids": "in the table already",
}
found = {}
for name in sorted(os.listdir("game")):
    if not name.endswith(".py"):
        continue
    src = open(os.path.join("game", name), encoding="utf-8").read()
    for field in re.findall(r"self\.([a-z_]*squad_ids)\s*=\s*set\(\)", src):
        found.setdefault(field, set()).add(name)
c.true("the sweep found the ledgers at all", len(found) >= 8)
missing = sorted(f for f in found
                 if f not in LEDGER_FIELDS and f not in NOT_ACTIVATION)
c.eq("every *_squad_ids ledger in game/ is either in the table or excused",
     missing, [])
c.eq("...and no excuse has outlived the field it names",
     sorted(f for f in NOT_ACTIVATION if f not in found), [])

main_src = open("main.py", encoding="utf-8").read()
c.eq("main.py has ONE definition of the activation slots",
     main_src.count("def _activation_slots("), 1)
c.true("...the writer passes it to capture()",
       "activation=_activation_slots()" in main_src)
c.true("...and the --load path restores it",
       "scene_io.restore_activation(" in main_src)
found_slots = re.search(r"def _activation_slots\(\):(.*?)\n    def ", main_src, re.S)
slots = found_slots.group(1) if found_slots else ""
c.eq("every slot the table knows is wired in main()",
     sorted(s for s in activation_state.LEDGERS if f'"{s}":' not in slots), [])
# find(), not index(): a missing needle has to redden this line, not abort the
# suite - the fifth time that lesson has been paid for in this repo.
began = main_src.find("begin_battle((loaded.get")
restored = main_src.find("scene_io.restore_activation(")
c.true("restore_activation runs AFTER begin_battle, which clears set_up_this_turn",
       began >= 0 and restored >= 0 and began < restored)

# =====================================================================
head("6. an older snapshot still loads")
# =====================================================================
# Same promise `armies` and `missions` made when they were added, and the
# reason FORMAT_VERSION does not move for this either.
state = board()
squad = skorpekh(state)
data = scene_io.capture(state, "map2")
old = strip_identity(data)
old.pop("activation", None)
fresh_state = board()
fresh = skorpekh(fresh_state)
problems = scene_io.restore(old, fresh_state, squads=[fresh])
c.eq("a file with no identity and no activation section restores cleanly",
     problems, [])
c.eq("...with every model back", len(fresh.models), len(squad.models))
c.eq("...and restore_activation is a no-op on it",
     scene_io.restore_activation(old, [fresh], controllers(tracker, fresh_state)), [])
c.eq("the format version has not moved", scene_io.FORMAT_VERSION, 1)
c.true("the file is still plain JSON",
       isinstance(json.loads(json.dumps(data)), dict))

c.finish()
