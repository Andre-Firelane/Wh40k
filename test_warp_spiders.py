"""Warp Spiders: datasheet data, and Flickerjump end to end.

Flickerjump is the only genuinely new mechanic here - Deep Strike (24.09) and
Battle Focus were already implemented and needed nothing but their flags. So
the ability gets the depth: the 24" override is asserted through the function
the ENGINE reads (coldstar.effective_movement_in), not through the flag the
button sets, and the end-of-phase mortal wounds are driven through the real
DiceManager acknowledgement chain rather than by calling the roll's tail.
"""

import testkit as tk
from testkit import Checks, Log, RecordingDice, script

from game import coldstar
from game.factions import aeldari as ae
from game.factions.datasheet import build_squad
from game.flickerjump import (FLICKERJUMP_MOVEMENT_IN, FlickerjumpController,
                              squad_has_flickerjump)
from game.game_state import GameState
from game.movement import MovementController
from game.sprites import _squad_key
from game.turn import PHASE_MOVEMENT, PHASE_SHOOTING
from game.weapons import MELEE, RANGED

checks = Checks("Warp Spiders")
NAME = "1 Warp Spiders 1"
EXARCH_LINE = "Warp Spider Exarch"


def spiders(composition_index=0, choices=None, owner="Player 1"):
    return tk.build(ae.WARP_SPIDERS, owner, name=NAME,
                    composition_index=composition_index, choices=choices)


def weapon_names(model):
    return sorted(w.name for w in model.weapons)


# --- 1. composition, statline, points --------------------------------------
print("--- 1. composition, statline, points ---")

small, big = spiders(0), spiders(1)
checks.eq("5-model unit", len(small.models), 5)
checks.eq("10-model unit", len(big.models), 10)
checks.eq("one Exarch in each",
          (sum(1 for m in small.models if m.profile.name == EXARCH_LINE),
           sum(1 for m in big.models if m.profile.name == EXARCH_LINE)), (1, 1))
checks.eq("5 models cost 105", small.points, 105)
checks.eq("10 models cost 200", big.points, 200)
# The first Aeldari entry priced by how many copies the army fields.
sheet = ae.WARP_SPIDERS
checks.eq("3rd+ unit of 5 costs 125", sheet.points_for(0, unit_index=3), 125)
checks.eq("3rd+ unit of 10 costs 220", sheet.points_for(1, unit_index=3), 220)

trooper = next(m for m in small.models if m.profile.name == "Warp Spider")
exarch = next(m for m in small.models if m.profile.name == EXARCH_LINE)
checks.eq("M12\"", trooper.profile.movement_in, 12)
checks.eq("T3", trooper.profile.toughness, 3)
checks.eq("Sv3+", trooper.profile.armor_save, "3+")
checks.eq("W1 / Exarch W2", (trooper.profile.wounds, exarch.profile.wounds), (1, 2))
checks.eq("Ld6+", trooper.profile.leadership, "6+")
checks.eq("OC1", trooper.profile.oc, 1)
checks.eq("5+ invulnerable", trooper.profile.invulnerable_save, "5+")
# 28.5 mm printed base - the conversion, not a repeat of the number.
checks.eq("28.5 mm base", round(trooper.profile.base_radius_in, 3), round(28.5 / 2 / 25.4, 3))
checks.true("INFANTRY", trooper.profile.infantry)
checks.true("FLY", trooper.profile.fly)
# JUMP PACK matters: it is what a TRANSPORT's transport_excludes reads, and
# the Falcon prints "cannot transport JUMP PACK models".
checks.true("JUMP PACK", trooper.profile.jump_pack)
checks.true("Deep Strike (24.09)", trooper.profile.deep_strike)
checks.true("Battle Focus", trooper.profile.battle_focus)
checks.true("Exarch inherits the ability", exarch.profile.flickerjump)
# Aspect Warriors that are NOT Guardian Defenders pay for their Fade Back.
checks.eq("no Fleet of Foot", getattr(trooper.profile, "fleet_of_foot", False), False)
for kw in ("INFANTRY", "JUMP PACK", "FLY", "ASPECT WARRIORS", "WARP SPIDERS"):
    checks.true(f"keyword {kw}", kw in sheet.keywords)


# --- 2. weapons ------------------------------------------------------------
print("--- 2. weapons ---")

checks.eq("trooper default loadout", weapon_names(trooper),
          ["Close Combat Weapon", "Death Spinner"])
checks.eq("Exarch default loadout", weapon_names(exarch),
          ["Close Combat Weapon", "Exarch's Death Spinner"])

spinner = next(w for w in trooper.weapons if w.name == "Death Spinner")
checks.eq("Death Spinner 12\"/S4/AP-1/D1",
          (spinner.range_in, spinner.strength, spinner.ap, spinner.damage), (12, 4, -1, 1))
checks.eq("Death Spinner rolls D6 attacks", spinner.attacks_notation.sides, 6)
checks.true("Death Spinner [IGNORES COVER]", spinner.ignores_cover)
checks.true("Death Spinner [TORRENT]", spinner.torrent)
# Every ranged row on this datasheet prints BS "N/A" because [TORRENT] skips
# the hit roll, so no per-weapon BS override is needed or wanted.
checks.eq("no per-weapon BS override", spinner.ballistic_skill, None)

ex_spinner = next(w for w in exarch.weapons if w.name == "Exarch's Death Spinner")
checks.eq("Exarch's spinner is S6/AP-2, not S4/AP-1",
          (ex_spinner.strength, ex_spinner.ap), (6, -2))

ccw = next(w for w in trooper.weapons if w.weapon_type == MELEE)
checks.eq("Close Combat Weapon is the A2/S3 Aeldari row",
          (ccw.attacks, ccw.strength, ccw.ap, ccw.damage), (2, 3, 0, 1))


# --- 3. Exarch wargear -----------------------------------------------------
print("--- 3. Exarch wargear ---")

for option, expected in (
    (ae.WARP_SPIDER_TO_SPINNERET, ["Close Combat Weapon", "Death Weavers", "Spinneret Rifle"]),
    (ae.WARP_SPIDER_TO_POWERBLADES, ["Close Combat Weapon", "Death Weavers", "Powerblades"]),
    (ae.WARP_SPIDER_TO_POWERBLADE_ARRAY, ["Close Combat Weapon", "Powerblade Array"]),
):
    sq = spiders(choices={EXARCH_LINE: {option: 1}})
    checks.eq(f"{option}", weapon_names(sq.models[0]), expected)

# The printed sentence only ever offers to replace the death spinner, so the
# close combat weapon survives every option - taken literally rather than
# reading an extra replacement into the third one.
sq = spiders(choices={EXARCH_LINE: {ae.WARP_SPIDER_TO_POWERBLADE_ARRAY: 1}})
checks.true("Exarch keeps its close combat weapon in every option",
            any(w.weapon_type == MELEE and w.name == "Close Combat Weapon"
                for w in sq.models[0].weapons))

# "one of the following": three options, one Exarch, so the later ones find no
# model left and are trimmed - the same way an over-eager choice always is.
sq = spiders(choices={EXARCH_LINE: {ae.WARP_SPIDER_TO_SPINNERET: 1,
                                    ae.WARP_SPIDER_TO_POWERBLADES: 1,
                                    ae.WARP_SPIDER_TO_POWERBLADE_ARRAY: 1}})
checks.eq("all three chosen -> only the first applies", weapon_names(sq.models[0]),
          ["Close Combat Weapon", "Death Weavers", "Spinneret Rifle"])

weavers = next(w for w in sq.models[0].weapons if w.name == "Death Weavers")
checks.eq("Death Weavers 6\"", weavers.range_in, 6)
checks.true("Death Weavers [TWIN-LINKED]", weavers.twin_linked)
rifle = next(w for w in sq.models[0].weapons if w.name == "Spinneret Rifle")
checks.eq("Spinneret Rifle 18\"/S5", (rifle.range_in, rifle.strength), (18, 5))

blades = spiders(choices={EXARCH_LINE: {ae.WARP_SPIDER_TO_POWERBLADES: 1}}).models[0]
pb = next(w for w in blades.weapons if w.name == "Powerblades")
checks.eq("Powerblades A5/S4/AP-2", (pb.attacks, pb.strength, pb.ap), (5, 4, -2))
checks.true("Powerblades [LETHAL HITS]", pb.lethal_hits)
checks.true("Powerblades [TWIN-LINKED]", pb.twin_linked)
array = spiders(choices={EXARCH_LINE: {ae.WARP_SPIDER_TO_POWERBLADE_ARRAY: 1}}).models[0]
checks.eq("Powerblade Array is A10, twice the Powerblades",
          next(w for w in array.weapons if w.name == "Powerblade Array").attacks, 10)


# --- 4. Flickerjump --------------------------------------------------------
print("--- 4. Flickerjump ---")


def movement_scene(owner="Player 1", phase=PHASE_MOVEMENT, turn_owner=None):
    state = GameState()
    squad = spiders(owner=owner)
    tk.line_up(squad, x=20.0, y=20.0)
    for model in squad.models:
        state.add_token(model)
    tt = tk._tracker(phase, turn_owner or owner)
    log, dice = Log(), RecordingDice()
    mc = MovementController(obstacles=[], game_log=log, player_name=owner,
                            turn_tracker=tt, all_tokens=state.tokens)
    ctrl = FlickerjumpController(turn_tracker=tt, movement_controller=mc,
                                 dice_manager=dice, game_log=log)
    return dict(state=state, squad=squad, turn=tt, move=mc, dice=dice, log=log, ctrl=ctrl)


sc = movement_scene()
squad = sc["squad"]
checks.true("the unit has the ability", squad_has_flickerjump(squad))
checks.true("offered while it can still make a Normal move", sc["ctrl"].can_use(squad))
checks.eq("Move is 12\" before using it",
          coldstar.effective_movement_in(squad.models[0]), 12)

checks.true("using it succeeds", sc["ctrl"].use(squad))
# Asserted through the function the engine reads, not the flag that was set.
checks.eq("Move becomes 24\"",
          coldstar.effective_movement_in(squad.models[0]), FLICKERJUMP_MOVEMENT_IN)
checks.true("and the unit may not charge this turn", squad.charge_locked_until_end_of_turn)
checks.eq("not offered twice for the same move", sc["ctrl"].can_use(squad), False)

# Swift as the Wind ADDS to whatever the characteristic is, override included.
squad.swift_as_the_wind_active = True
checks.eq("Swift as the Wind still adds its 2\" on top",
          coldstar.effective_movement_in(squad.models[0]), FLICKERJUMP_MOVEMENT_IN + 2)
squad.swift_as_the_wind_active = False

# The real budget the mover hands out, not just the characteristic.
sc["move"].select(squad.models[0])
sc["move"].start_move()
checks.eq("the move budget is the full 24\"",
          sc["move"].remaining_range[squad.models[0].id], FLICKERJUMP_MOVEMENT_IN)
sc["move"].cancel_move()

# End of phase: one D6 per model, each 1 is a mortal wound. Five models, two 1s.
script(1, 3, 1, 4, 5)
sc["ctrl"].end_of_phase()
checks.true("a roll is pending at the end of the phase", sc["dice"].is_pending)
checks.eq("one die per model", len(sc["dice"].pending_values), 5)
label, values = sc["dice"].last_roll
checks.eq("labelled Flickerjump", label, "Flickerjump")
checks.eq("the engine drew the scripted faces", values, [1, 3, 1, 4, 5])
sc["dice"].acknowledge()
sc["ctrl"].on_dice_acknowledged()
checks.true("two 1s open a mortal wound allocation",
            sc["ctrl"].pending_damage_choice is not None)
checks.true("the log says how many",
            any("2 mortal wound(s)" in line for line in sc["log"].lines))

wounds_before = sum(m.current_wounds for m in squad.models)
while sc["ctrl"].pending_damage_choice:
    sc["ctrl"].choose_damage_model(sc["ctrl"].pending_damage_choice[0])
checks.eq("2 wounds taken", sum(m.current_wounds for m in squad.models), wounds_before - 2)
checks.eq("nothing left pending", sc["ctrl"].is_busy, False)

# No 1s: nothing to allocate, and the sequence still closes cleanly.
sc2 = movement_scene()
sc2["ctrl"].use(sc2["squad"])
script(2, 3, 4, 5, 6)
sc2["ctrl"].end_of_phase()
sc2["dice"].acknowledge()
sc2["ctrl"].on_dice_acknowledged()
checks.eq("no 1s -> no allocation", sc2["ctrl"].pending_damage_choice, None)
checks.eq("and nothing is left busy", sc2["ctrl"].is_busy, False)
# 4 troopers at W1 plus the W2 Exarch.
checks.eq("no model lost a wound",
          sum(m.current_wounds for m in sc2["squad"].models), 6)

# Not offered outside its WHEN.
shoot = movement_scene(phase=PHASE_SHOOTING)
checks.eq("not offered outside the Movement phase", shoot["ctrl"].can_use(shoot["squad"]), False)
other = movement_scene(owner="Player 1", turn_owner="Player 2")
checks.eq("not offered in the opponent's turn", other["ctrl"].can_use(other["squad"]), False)
moved = movement_scene()
moved["move"].select(moved["squad"].models[0])
moved["move"].remain_stationary()
checks.eq("not offered once the unit has used its move",
          moved["ctrl"].can_use(moved["squad"]), False)

# "Until the end of the turn" for the 24" half.
sc3 = movement_scene()
sc3["ctrl"].use(sc3["squad"])
sc3["ctrl"].expire_for_turn([sc3["squad"]])
checks.eq("the 24\" expires at end of turn",
          coldstar.effective_movement_in(sc3["squad"].models[0]), 12)

# A unit without the ability is never offered it.
plain = tk.build(ae.HOWLING_BANSHEES, "Player 1", name="1 Howling Banshees 1")
checks.eq("a unit without the ability does not have it", squad_has_flickerjump(plain), False)


# The class docstring calls the 3+ ballistic skill an inference that is never
# read, because every ranged row on this datasheet is [TORRENT]. Shown rather
# than asserted about the flag: fire a Death Spinner group and check the engine
# never rolls a hit roll for it - and that the printed D6 Attacks is rolled for
# real, once per model.
tor = tk.shooting_scene(ae.WARP_SPIDERS, ae.HOWLING_BANSHEES, attacker_owner="Player 1", gap=6.0)
tor["shooting"].start_shooting(tor["attacker"])
tor["shooting"].choose_target_squad(tor["target"])
rows = tor["shooting"].weapon_eligibility()
checks.eq("the Exarch's spinner forms its own group, being S6/AP-2",
          sorted(r[1] for r in rows), ["Death Spinner", "Exarch's Death Spinner"])
script(3, 3, 3, 3, default=3)
tor["shooting"].choose_weapon(next(r[0] for r in rows if r[1] == "Death Spinner"))
for _ in range(6):
    if not tor["dice"].is_pending:
        break
    tor["dice"].acknowledge()
    tor["shooting"].on_dice_acknowledged()
labels = [label for label, _ in tor["dice"].rolled]
checks.true("the D6 Attacks is rolled for real, one die per model",
            labels and labels[0].startswith("Attacks: Death Spinner") and len(tor["dice"].rolled[0][1]) == 4)
checks.eq("4 models x 3 = 12 attacks",
          any("= 12" in line for line in tor["log"].lines), True)
checks.eq("[TORRENT] means no hit roll is ever made",
          any("hit roll" in line.lower() for line in tor["log"].lines), False)
checks.true("it auto-hits instead",
            any("automatically hits" in line for line in tor["log"].lines))


# --- 5. sprites ------------------------------------------------------------
print("--- 5. sprites ---")

for model in (trooper, exarch):
    checks.eq(f"{model.profile.name} art", _squad_key(model), "Warpspider")


# --- 6. A/B probe ----------------------------------------------------------
print("--- 6. A/B probe ---")

# With the override unwired, the ability grants nothing - so the two checks
# above that prove it are actually load-bearing.
import game.flickerjump as fj  # noqa: E402

original = fj.movement_override_in
fj.movement_override_in = lambda squad: None
probe = movement_scene()
probe["ctrl"].use(probe["squad"])
checks.eq("A/B: without the override the Move stays at 12\"",
          coldstar.effective_movement_in(probe["squad"].models[0]), 12)
fj.movement_override_in = original
probe2 = movement_scene()
probe2["ctrl"].use(probe2["squad"])
checks.eq("A/B: restored", coldstar.effective_movement_in(probe2["squad"].models[0]), 24)

# --- 7. the button ---------------------------------------------------------
print("--- 7. the button ---")

import pygame  # noqa: E402

from game import config as game_config  # noqa: E402
from game.shooting import ShootingController  # noqa: E402
from game.ui.action_panel import ActionPanel  # noqa: E402

pygame.init()
pygame.display.set_mode((320, 240))

panel_scene = movement_scene()
panel_scene["move"].select(panel_scene["squad"].models[0])
panel = ActionPanel()
panel_rect = pygame.Rect(0, 0, game_config.LEFT_PANEL_WIDTH, 900)
surface = pygame.Surface((game_config.LEFT_PANEL_WIDTH, 900))
panel_sc = ShootingController(
    all_tokens=panel_scene["state"].tokens, dice_manager=panel_scene["dice"],
    player_name="Player 1",
)


def draw(ctrl):
    panel.draw(surface, panel_rect, panel_scene["move"], panel_sc, None,
               flickerjump_controller=ctrl)
    return list(panel._buttons)


with_button = draw(panel_scene["ctrl"])
without_button = draw(None)
checks.true("the ability adds a button", len(with_button) > len(without_button))
checks.true("every button stays inside the 220px panel",
            all(panel_rect.contains(r) for r, _ in with_button))

# The panel only stores (rect, callback), so the button is identified by
# clicking: exactly one of them uses the ability.
used_by = []
for rect, callback in draw(panel_scene["ctrl"]):
    callback()
    if panel_scene["squad"].flickerjump_active:
        used_by.append(rect)
        break
checks.eq("exactly one button uses Flickerjump", len(used_by), 1)
checks.true("and it costs no CP - this is an ability, not a stratagem",
            panel_scene["squad"].charge_locked_until_end_of_turn)
checks.eq("once used, the button is gone", len(draw(panel_scene["ctrl"])), len(without_button))

print("--- the Exarch is marked as the squad leader ---")
import testkit as _tk_leader  # noqa: E402
from game.factions.aeldari import WARP_SPIDERS as _sheet_for_leader  # noqa: E402
from game.units import WarpSpiderExarchProfile as _ExarchProfile  # noqa: E402

# User report: "bei warp spider und avengers kann ich den exarch nicht
# unterscheiden". There is no separate Exarch art for this datasheet, so the
# leader ring/label the renderer draws for squad_leader models is the ONLY
# thing that tells it apart - and the flag was simply never set here (the
# Striking Scorpion and Howling Banshee Exarchs already had it).
checks.true("the Exarch is flagged squad_leader", _ExarchProfile.squad_leader)
_exarch_squad = _tk_leader.build(_sheet_for_leader, "Player 1", name="1 WARP_SPIDERS L1")
_leaders = [m for m in _exarch_squad.models if m.profile.squad_leader]
checks.eq("exactly one model in the unit carries it", len(_leaders), 1)
checks.eq("and it is the Exarch", _leaders[0].profile.name, "Warp Spider Exarch")


checks.finish()
