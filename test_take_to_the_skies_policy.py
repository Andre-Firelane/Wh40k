"""Rule 21.03 (Take to the Skies): WHO pays for it, and WHEN is it worth it?

THE REPORTED CASE. User, on the last game: "die necron krieger sind hinten
nicht rausgekommen. sie hatten enorme schwierigkeiten nach vorne zu laufen."
In logs/game_20260826_185516.log the 21-model "2 Necron Warriors 1 +
Technomancer" gained 1.63" / 1.23" / 1.19" of centroid progress toward Central
Objective in three consecutive Movement phases, against a printed 5" move.

THE CAUSE was that the two halves of 21.03 were applied to DIFFERENT sets of
models: take_to_the_skies() charged the 2" to every model in the squad, while
clamp_move() granted the terrain/model bypass per model on `token.profile.fly`.
Rule 19.01 merges the Technomancer (FLY) into the Necron Warriors (no FLY), so
21 of 21 models paid and 1 of 21 flew - twenty Warriors cut from a 5" move to a
3" one, every Movement phase of the game, for nothing.

TWO USER RULINGS SETTLE IT, and this file is split along them.

  1. "es fliegen nur fly modelle." So clamp_move()'s per-model gate was right
     all along and the squad-wide penalty loop was the defect. Section 1
     measures the corrected engine at the movement budget: only FLY models pay.

  2. "einheiten, die ausschliesslich aus infanterie modellen bestehen sollten
     niemals take to the skies benutzen, weil sie ja eh durch waende laufen
     koennen." Rule 13.06 already crosses Dense terrain for INFANTRY, so the
     half of 21.03 worth having buys them nothing. Section 2 pins that in
     game.movement.take_to_the_skies_pays(), the one definition of "is this
     worth declaring", read by ai/agent_driver.py and
     measure_crowded_movement.py alike rather than spelled out in each.

The two are independent and both are needed: the first stops a human clicking
the button from taxing twenty walkers, the second stops the AI declaring it for
units the rule cannot help.
"""

import copy
import io
import os
import re

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import testkit as tk  # noqa: E402
from game import attached_units, army_lists, config, maps  # noqa: E402
from game.game_state import GameState  # noqa: E402
from game.movement import (  # noqa: E402
    TAKE_TO_THE_SKIES_DISTANCE_PENALTY_IN, MovementController,
    take_to_the_skies_pays,
)
from game.turn import PHASE_MOVEMENT, PHASES, TurnTracker  # noqa: E402
from game.factions import necrons as nec, orks as ork  # noqa: E402

checks = tk.Checks("Take to the Skies (21.03): who pays, who declares")

_map = maps.MAPS["map2"]
maps.apply_to_config(_map)


def line_up(squad, x=30.0, y=6.0, per_row=7, pitch=1.4):
    for index, model in enumerate(squad.models):
        model.x_in = x + (index % per_row) * pitch
        model.y_in = y + (index // per_row) * pitch
    return squad


def moving_controller(squad):
    tracker = TurnTracker(first_player="Player 2")
    tracker.phase_index = PHASES.index(PHASE_MOVEMENT)
    controller = MovementController(
        obstacles=[], player_name="Player 2", turn_tracker=tracker,
        all_tokens=list(squad.models), board_width_in=config.BOARD_WIDTH_IN,
        board_height_in=config.BOARD_HEIGHT_IN,
    )
    controller.select(squad.models[0])
    controller.start_move()
    return controller


def warriors_with_technomancer():
    """The exact reported unit, built the way army_lists does it.

    composition_index=1 is the 20-model unit the list fields (the default
    composition is 10) - the reported blob, not a smaller stand-in."""
    state = GameState()
    warriors = tk.build(nec.NECRON_WARRIORS, owner="Player 2", composition_index=1,
                        name="2 Necron Warriors 1")
    tech = tk.build(nec.TECHNOMANCER, owner="Player 2", name="2 Technomancer 1")
    return line_up(attached_units.attach(tech, warriors, game_state=state))


# --------------------------------------------------------------------------
# 1. WHO PAYS. Ruling: "es fliegen nur fly modelle" - so clamp_move()'s gate
#    was right and the penalty loop was the defect. Measured at the movement
#    budget rather than through a move, because the budget is where the two
#    halves disagreed.
# --------------------------------------------------------------------------
squad = warriors_with_technomancer()
flyers = [m for m in squad.models if m.profile.fly]
checks.eq("the reported unit is 21 models (19.01 merged the Technomancer in)",
          len(squad.models), 21)
checks.eq("...of which exactly one has FLY", len(flyers), 1)
checks.true("...and it is the Technomancer, i.e. the LEADER",
            type(flyers[0].profile).__name__ == "TechnomancerProfile")

controller = moving_controller(squad)
before = {m.id: controller.remaining_range[m.id] for m in squad.models}
controller.take_to_the_skies()
after = {m.id: controller.remaining_range[m.id] for m in squad.models}

paid = [m for m in squad.models if before[m.id] - after[m.id] > 0]
bypassed = [m for m in squad.models if controller.flying_this_move and m.profile.fly]
checks.eq("only the models with FLY pay the 21.03 distance penalty", len(paid), 1)
checks.eq("...which is exactly the set that gets the bypass", len(bypassed), 1)
checks.true("...the same models, which is the whole point of the ruling",
            [m.id for m in paid] == [m.id for m in bypassed])
checks.true("A/B: before the ruling all 21 paid, so the 20-model tax is gone",
            len(squad.models) - len(paid) == 20)

warrior = next(m for m in squad.models if not m.profile.fly)
checks.eq("a Necron Warrior keeps its full 5\" move", round(after[warrior.id], 2), 5.0)
checks.eq("...it is not taxed at all",
          round(before[warrior.id] - after[warrior.id], 2), 0.0)
tech = flyers[0]
checks.eq("the Technomancer, which does fly, pays the 2\"",
          round(before[tech.id] - after[tech.id], 2), TAKE_TO_THE_SKIES_DISTANCE_PENALTY_IN)

# Through clamp_move(), not just the budget: the walker really covers its whole
# move on open ground while the declaration is live. A budget that reads 5" and
# a model that still only travels 3" would be the same bug one layer down.
origin = (warrior.x_in, warrior.y_in)
x_in, y_in = controller.clamp_move(warrior, origin[0], origin[1] + 20.0)
checks.eq("...and really covers 5.00\" of open ground with the declaration live",
          round(((x_in - origin[0]) ** 2 + (y_in - origin[1]) ** 2) ** 0.5, 2), 5.0)


# --------------------------------------------------------------------------
# 2. WHO DECLARES. Ruling: an all-INFANTRY unit never does, because 13.06
#    already crosses Dense terrain for it.
# --------------------------------------------------------------------------
reported = warriors_with_technomancer()
checks.true("the reported unit is all INFANTRY",
            all(m.profile.infantry for m in reported.models))
checks.eq("...so it never declares 21.03 - 13.06 already crosses walls for it",
          take_to_the_skies_pays(reported), False)

boyz = line_up(tk.build(ork.STORMBOYZ, owner="Player 2", composition_index=1,
                        name="Stormboyz"))
checks.true("the Stormboyz fly on every model", all(m.profile.fly for m in boyz.models))
checks.true("...and are INFANTRY as well", all(m.profile.infantry for m in boyz.models))
checks.eq("...so the ruling grounds them too, not just the reported unit",
          take_to_the_skies_pays(boyz), False)

koptas = line_up(tk.build(ork.DEFFKOPTAS, owner="Player 2", composition_index=1,
                          name="Deffkoptas"))
checks.true("the Deffkoptas fly and are NOT infantry",
            all(m.profile.fly for m in koptas.models)
            and not any(m.profile.infantry for m in koptas.models))
checks.eq("...so they still declare it - 13.06 gives them nothing",
          take_to_the_skies_pays(koptas), True)

warriors_only = line_up(tk.build(nec.NECRON_WARRIORS, owner="Player 2",
                                 composition_index=1, name="2 Necron Warriors 1"))
checks.eq("a unit with no flyer at all does not declare it",
          take_to_the_skies_pays(warriors_only), False)


def with_flags(squad, **flags):
    """Copy the flying model's profile and set flags on the copy. UnitProfile
    subclasses are shared CLASS objects - setting a flag on one would switch it
    on for every other unit built from the same datasheet."""
    flyer = next(m for m in squad.models if m.profile.fly)
    flyer.profile = copy.copy(flyer.profile)
    for name, value in flags.items():
        setattr(flyer.profile, name, value)
    return squad


# Rule 24.17 (HOVER) removes the penalty, so there is no trade-off left to
# weigh. Built by flag rather than by finding a datasheet, because no unit in
# any of the four rosters prints HOVER - the branch would otherwise be dead.
hover_mixed = with_flags(warriors_with_technomancer(), hover=True, infantry=False)
checks.eq("a mixed non-INFANTRY unit with HOVER declares it - 24.17 makes it free",
          take_to_the_skies_pays(hover_mixed), True)

# "Niemals" is emphatic, so the INFANTRY rule is checked BEFORE the HOVER
# branch. Pinned because the two orderings differ only in this one case and a
# later reader could reasonably swap them.
hover_infantry = with_flags(warriors_with_technomancer(), hover=True)
checks.true("...but an all-INFANTRY unit stays grounded even with HOVER",
            all(m.profile.infantry for m in hover_infantry.models)
            and take_to_the_skies_pays(hover_infantry) is False)

hover_ctrl = moving_controller(hover_mixed)
hover_before = {m.id: hover_ctrl.remaining_range[m.id] for m in hover_mixed.models}
hover_ctrl.take_to_the_skies()
checks.true("...and with HOVER nothing is deducted from anyone, which is why it is free",
            all(hover_ctrl.remaining_range[m.id] == hover_before[m.id]
                for m in hover_mixed.models))


# --------------------------------------------------------------------------
# 3. What it changes across the REAL rosters, counted rather than asserted.
#    The units that keep it must be exactly the ones 13.06 does not already
#    carry - vehicles, walkers, beasts, monsters, mounted.
# --------------------------------------------------------------------------
def flying_units(builder):
    squads = []
    state = GameState()
    builder("Player 2", lambda squad, *a, **kw: squads.append(squad), state=state)
    return [s for s in squads if any(m.profile.fly for m in s.models)]


declines, keeps = [], []
for builder in (army_lists.build_aeldari, army_lists.build_orks,
                army_lists.build_necrons, army_lists.build_tau):
    for unit in flying_units(builder):
        (keeps if take_to_the_skies_pays(unit) else declines).append(unit)

checks.eq("seven flying units across the four rosters stop declaring 21.03",
          sorted(u.name for u in declines),
          ["2 Commander Shadowsun 1", "2 Necron Warriors 1 + Technomancer",
           "2 Stealth Battlesuits 1", "2 Stealth Battlesuits 2",
           "2 Stormboyz 1", "2 Vespid Stingwings 1",
           "2 Warp Spiders 1 + Lhykhis"])
checks.true("...and every one of them is all-INFANTRY, i.e. covered by 13.06",
            all(all(m.profile.infantry for m in u.models) for u in declines))
# FOURTEEN, and it has now moved three times for reasons worth carrying: a
# unit count is exactly the wrong thing to guess at here, because merging
# (19.01) removes units without removing models, and because a roster swap
# moves BOTH columns at once.
#   16 -> 15  the Necron revision dropped Illuminor Szeras, a FLY unit of his
#             own; the Lokhust Lord it added does NOT replace him, because he
#             merges into the Lokhust Destroyers, which already flew.
#   15 -> 14  the Aeldari revision swapped Shroud Runners for Windriders (both
#             FLY, so no change) and merged the Warlock Skyrunner - until then
#             a FLY unit of its own - into those same Windriders.
#   14 -> 14  the 2026-08-30 T'au revision, and the coincidence is the point:
#             it took out four FLY keeps (Ghostkeel, the Coldstar's
#             Starscythes, Farsight's Sunforges, and one Devilfish is now two)
#             and put back four (a second Devilfish, two Piranhas, and the
#             Riptide stayed), while the declines column grew by three -
#             Shadowsun, a second Stealth team and the Vespid, every one of
#             them all-INFANTRY and so covered by 13.06 already.
checks.eq("fourteen keep it", len(keeps), 14)
checks.true("...and not one of them is all-INFANTRY",
            not any(all(m.profile.infantry for m in u.models) for u in keeps))
# The Crisis Battlesuits the policy was written for left with the 2026-08-30
# T'au revision. The Riptide is the same case and the reason the pin is kept
# rather than dropped: a BATTLESUIT that 13.06 does not carry through Dense
# terrain, so 21.03 is the only way it crosses one.
checks.true("...including the Riptide, the T'au battlesuit that still needs 21.03",
            any(u.name == "2 Riptide Battlesuit 1" for u in keeps))
checks.true("...and no Crisis suit is in any roster any more, which is why that pin moved",
            not any("Crisis" in u.name for u in keeps + declines))
checks.true("...and the Deffkoptas, the flying unit the movement harness calls a worst case",
            any(u.name == "2 Deffkoptas 1" for u in keeps))


# --------------------------------------------------------------------------
# 4. Source guards. A behaviour test cannot see a second copy of the policy -
#    and a local copy of it is exactly how measure_crowded_movement.py drifted
#    from the code it measures three times before (see its own header).
# --------------------------------------------------------------------------
driver_src = io.open("ai/agent_driver.py", encoding="utf-8").read()
harness_src = io.open("measure_crowded_movement.py", encoding="utf-8").read()

checks.true("ai/agent_driver.py asks take_to_the_skies_pays()",
            "use_fly = take_to_the_skies_pays(squad)" in driver_src)
checks.true("measure_crowded_movement.py asks the same function",
            "use_fly = take_to_the_skies_pays(squad)" in harness_src)
for label, src in (("ai/agent_driver.py", driver_src),
                   ("measure_crowded_movement.py", harness_src)):
    checks.eq(f"{label} keeps no local any()-over-fly copy of the policy",
              re.findall(r"use_fly\s*=\s*any\(", src), [])

checks.eq("take_to_the_skies_pays lives in game/movement.py, beside the penalty it weighs",
          take_to_the_skies_pays.__module__, "game.movement")

checks.finish()
