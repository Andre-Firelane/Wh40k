"""The Crypteks: Chronomancer, Psychomancer and Orikan The Diviner (Etappe 1).

THREE DATASHEETS, ONE CHASSIS. They share the Plasmancer's statline and both
of its bodyguard units, so most of this suite is about each ability landing on
the right seam rather than about the numbers.

WHERE THIS MEASURES, AND WHY THERE
----------------------------------
  * Timesplinter Mantle is measured on an ATTACHED unit, not on a lone
    Chronomancer. Both halves are correct for a lone one no matter how they
    are written; the Stealth half is the one that goes wrong the moment he
    does the thing a SUPPORT model exists to do, because rule 24.33's
    every-model reading answers False for a bodyguard that does not print it.

  * The Stars Are Right is measured on the WOUND THRESHOLD, not on the flag.
    "Triple" turns S4 into S12, which crosses two Toughness boundaries at
    once - a test that only checked "the mark is set" would pass with the
    arithmetic wrong, and a test that only checked Strength would pass with
    "triple" implemented as "+2".

  * Its crit half is measured as a THRESHOLD EQUALITY against the wound
    threshold, because that is what "every successful Wound roll scores a
    Critical Wound" means here - and separately against an [ANTI-X] weapon,
    to show the grant never makes an already-better threshold worse.

  * The battle-shock abilities are measured through the REAL
    BattleShockController, so the -1 is read off the roll that actually
    happens rather than off the argument that was passed.

  * Section 9's sprite checks run AT THE MODEL, so a key naming a file that is
    not on disk fails here rather than passing on a mapping table nobody
    checked.
"""
import io

import testkit as tk
from testkit import Checks

from game import (attached_units, chronometron, invulnerable_save,
                  psychomancer, sprites, squad as squad_mod,
                  the_stars_are_right, timesplinter_mantle)
from game.battle_shock import BattleShockController
from game.decision import DecisionManager
from game.factions import necrons as nec
from game.factions.necrons_points import NECRONS_POINTS
from game.movement import MovementController
from game.units import (ChronomancerProfile, OrikanTheDivinerProfile,
                        PlasmancerProfile, PsychomancerProfile)
from game.weapons import (AbyssalLanceMeleeProfile, AbyssalLanceRangedProfile,
                          AeonstaveMeleeProfile, AeonstaveRangedProfile,
                          StaffOfTomorrowProfile)

checks = Checks("Necron Crypteks")

CHRONOMANCER = nec.NECRONS.datasheets["Chronomancer"]
PSYCHOMANCER = nec.NECRONS.datasheets["Psychomancer"]
ORIKAN = nec.NECRONS.datasheets["Orikan The Diviner"]
IMMORTALS = nec.NECRONS.datasheets["Immortals"]
WARRIORS = nec.NECRONS.datasheets["Necron Warriors"]

SHEETS = [(CHRONOMANCER, ChronomancerProfile),
          (PSYCHOMANCER, PsychomancerProfile),
          (ORIKAN, OrikanTheDivinerProfile)]


def build(sheet, owner="Player 2", n=1, **kw):
    """Named the way main.py names squads - sprites._key_for_name() matches the
    datasheet name as a SUBSTRING of the squad name, so a bare name finds no
    art and section 9 would pass by measuring nothing."""
    return tk.build(sheet, owner, name="%s %s %d" % (owner[-1], sheet.name, n), **kw)


# --- 1. the shared Cryptek chassis ---
print("--- 1. the shared Cryptek chassis ---")

for sheet, profile in SHEETS:
    checks.eq("%s: statline shared with the Plasmancer" % sheet.name,
              (profile.movement_in, profile.toughness, profile.armor_save,
               profile.wounds, profile.leadership, profile.oc),
              (PlasmancerProfile.movement_in, PlasmancerProfile.toughness,
               PlasmancerProfile.armor_save, PlasmancerProfile.wounds,
               PlasmancerProfile.leadership, PlasmancerProfile.oc))
    checks.eq("%s: 40 mm base" % sheet.name, round(profile.base_radius_in, 3), 0.787)
    checks.true("%s: INFANTRY CHARACTER with Reanimation Protocols" % sheet.name,
                profile.infantry and profile.character and profile.reanimation_protocols)
    checks.true("%s: CORE line reads Support, so the profile carries the role"
                % sheet.name, profile.support and not profile.leader)

# What separates them, measured rather than assumed from a neighbour.
checks.eq("only the Psychomancer prints no invulnerable save",
          [s.name for s, p in SHEETS if p.invulnerable_save == "-"], ["Psychomancer"])
checks.eq("only Orikan prints WS 3+ - his Staff of Tomorrow does",
          [s.name for s, p in SHEETS if p.weapon_skill == "3+"], ["Orikan The Diviner"])
checks.eq("only Orikan is an EPIC HERO",
          [s.name for s, p in SHEETS if p.epic_hero], ["Orikan The Diviner"])

# --- 2. weapons ---
print("--- 2. weapons ---")

aeon_r, aeon_m = AeonstaveRangedProfile(), AeonstaveMeleeProfile()
checks.eq("Aeonstave (ranged): 18\", D6 A, S5, AP-1, D1",
          (aeon_r.range_in, aeon_r.strength, aeon_r.ap, aeon_r.damage), (18, 5, -1, 1))
checks.true("...its Attacks are a real D6 roll, not the placeholder",
            aeon_r.attacks_notation is not None)
checks.eq("...and it is [BLAST]", aeon_r.blast, 1)
checks.eq("Aeonstave (melee): 3 A, S5, AP-1, D1",
          (aeon_m.attacks, aeon_m.strength, aeon_m.ap, aeon_m.damage), (3, 5, -1, 1))
checks.eq("...and prints NO [BLAST] - 24.05 is a ranged keyword", aeon_m.blast, 0)
checks.eq("both Aeonstave rows print one name", (aeon_r.name, aeon_m.name),
          ("Aeonstave", "Aeonstave"))

lance_r, lance_m = AbyssalLanceRangedProfile(), AbyssalLanceMeleeProfile()
checks.eq("Abyssal lance (ranged): 18\", 1 A, S6, AP-3, D3",
          (lance_r.range_in, lance_r.attacks, lance_r.strength, lance_r.ap, lance_r.damage),
          (18, 1, 6, -3, 3))
checks.eq("...and the melee row prints the same numbers",
          (lance_m.attacks, lance_m.strength, lance_m.ap, lance_m.damage), (1, 6, -3, 3))

staff = StaffOfTomorrowProfile()
checks.eq("Staff of Tomorrow: 2 A, S4, AP-3", (staff.attacks, staff.strength, staff.ap),
          (2, 4, -3))
checks.true("...D3 damage as a real roll", staff.damage_notation is not None)
checks.true("...and [DEVASTATING WOUNDS]", staff.devastating_wounds)

# --- 3. composition, points and the SUPPORT pairings ---
print("--- 3. composition, points and the SUPPORT pairings ---")

for sheet, _p in SHEETS:
    sq = build(sheet)
    checks.eq("%s is one model" % sheet.name, len(sq.models), 1)

checks.eq("Chronomancer costs 70, then 80 for the second",
          (NECRONS_POINTS["Chronomancer"].cost_for(1, 1),
           NECRONS_POINTS["Chronomancer"].cost_for(1, 2)), (70, 80))
checks.eq("Psychomancer costs 55 flat",
          (NECRONS_POINTS["Psychomancer"].cost_for(1, 1),
           NECRONS_POINTS["Psychomancer"].cost_for(1, 2)), (55, 55))
checks.eq("Orikan costs 90 flat",
          (NECRONS_POINTS["Orikan The Diviner"].cost_for(1, 1),
           NECRONS_POINTS["Orikan The Diviner"].cost_for(1, 2)), (90, 90))

for sheet, _p in SHEETS:
    sq = build(sheet)
    checks.eq("%s attaches by the SUPPORT role" % sheet.name,
              attached_units.attachment_role(sq), attached_units.SUPPORT)
    checks.eq("...to Immortals and Necron Warriors, and nothing else",
              sorted(attached_units.leadable_unit_names(sq)),
              ["Immortals", "Necron Warriors"])
    checks.eq("...and can_attach agrees", attached_units.can_attach(sq, build(IMMORTALS, n=9)), [])

# 19.01 allows ONE leader and ONE support. The Overlord is the Leader here, and
# a Cryptek must still fit beside him - the reason the two built Crypteks had
# their role corrected in this batch.
host = build(WARRIORS, n=8)
attached_units.attach(build(nec.NECRONS.datasheets["Overlord"], n=8), host)
checks.eq("a Cryptek still joins a unit that already has a Leader (19.01)",
          attached_units.can_attach(build(CHRONOMANCER, n=8), host), [])

# THE REGRESSION THE ROLE CORRECTION NEARLY SHIPPED. formations.py's
# is_support_platform() used to ask the ATTACHMENT ROLE, which was exact only
# while the three Aeldari SUPPORT WEAPON platforms were the game's only
# SUPPORT-role units. Giving the Crypteks their correct role made all five of
# them answer True, and the pre-game panel began offering each a "Support
# Artillery" join - a clause printed on three datasheets and on none of these.
# The whole suite stayed green. It now asks the SUPPORT WEAPON keyword.
from game import formations
from game.factions import aeldari as _ae
for sheet, _p in SHEETS:
    checks.eq("%s is NOT offered the Support Artillery join" % sheet.name,
              bool(formations.is_support_platform(build(sheet, n=21))), False)
for _built in ("Plasmancer", "Technomancer"):
    checks.eq("...nor is the %s, whose role was corrected with them" % _built,
              bool(formations.is_support_platform(
                  build(nec.NECRONS.datasheets[_built], n=21))), False)
_plat = tk.build(_ae.AELDARI.datasheets["D-cannon Platform"], "Player 1",
                 name="1 D-cannon Platform 1")
checks.true("...and the platform the clause IS printed on still is",
            bool(formations.is_support_platform(_plat)))

# --- 4. Timesplinter Mantle ---
print("--- 4. Timesplinter Mantle ---")

lone = build(CHRONOMANCER, n=2)
checks.true("a lone Chronomancer has the mantle", timesplinter_mantle.has_mantle(lone))
checks.eq("...worth -1, a MALUS, so positive on the threshold",
          [m.amount for m in timesplinter_mantle.hit_modifiers(lone)],
          [timesplinter_mantle.MELEE_HIT_PENALTY])
checks.eq("...and nothing for a unit without one",
          timesplinter_mantle.hit_modifiers(build(IMMORTALS, n=2)), [])

# THE CASE THAT GOES WRONG IF EITHER HALF IS ASKED THE EVERY-MODEL WAY.
merged = build(IMMORTALS, n=3)
plain_stealth = squad_mod.squad_has_stealth(merged)
attached_units.attach(build(CHRONOMANCER, n=3), merged)
checks.eq("Immortals alone have no Stealth", plain_stealth, False)
checks.true("...and gain it from an attached Chronomancer, as the ability grants",
            squad_mod.squad_has_stealth(merged))
checks.true("...and the melee -1 reaches the whole attached unit",
            bool(timesplinter_mantle.hit_modifiers(merged)))

# End to end through the REAL FightController, and the ranged counter-check -
# without it this section would pass on a mantle wired into both phases.
scene = tk.fight_scene(WARRIORS, CHRONOMANCER, attacker_owner="Player 1")
fc = scene["fight"]
fc.fighting_squad = scene["attacker"]
attacker_model = scene["attacker"].models[0]
mods = fc._hit_modifiers(attacker_model, scene["target"])
checks.true("the real melee chain carries the mantle",
            any(m.source == timesplinter_mantle.LABEL for m in mods))
plain = fc._hit_modifiers(attacker_model, build(IMMORTALS, n=4))
checks.true("...and not against a unit without one",
            not any(m.source == timesplinter_mantle.LABEL for m in plain))
fight_src = io.open("game/fight.py", encoding="utf-8").read()
shoot_src = io.open("game/shooting.py", encoding="utf-8").read()
checks.true("the mantle is melee-only: fight.py asks it, shooting.py does not",
            "timesplinter_mantle.hit_modifiers(" in fight_src
            and "timesplinter_mantle" not in shoot_src)

# --- 5. Chronometron ---
print("--- 5. Chronometron ---")

mover = build(CHRONOMANCER, n=5)
tk.line_up(mover, x=20.0, y=20.0)
far = build(IMMORTALS, owner="Player 1", n=5)
tk.line_up(far, x=20.0, y=40.0)
board = list(mover.models) + list(far.models)
checks.true("unengaged, so the ability is available",
            chronometron.can_use(mover, board))
checks.eq("its move is 5 inches", chronometron.CHRONOMETRON_MOVE_IN, 5.0)
checks.true("its move mode is waited on at a phase change",
            chronometron.CHRONOMETRON_MOVE_MODE
            in MovementController.OUT_OF_PHASE_MOVE_MODES)

near = build(IMMORTALS, owner="Player 1", n=6)
tk.line_up(near, x=20.0, y=20.8)          # inside Engagement Range (03.04)
checks.true("engaged, the printed condition refuses it",
            not chronometron.can_use(mover, list(mover.models) + list(near.models)))

# The attached case: the printed subject is "this model's UNIT".
merged2 = build(IMMORTALS, n=7)
tk.line_up(merged2, x=30.0, y=20.0)
attached_units.attach(build(CHRONOMANCER, n=7), merged2)
checks.true("an attached Chronomancer gives his UNIT the move",
            chronometron.unit_has_chronometron(merged2))

# --- 6. Nightmare Shroud and Harbinger of Despair ---
print("--- 6. Nightmare Shroud and Harbinger of Despair ---")

checks.eq("both subtract 1 from the test", psychomancer.BATTLE_SHOCK_PENALTY, 1)

psy = build(PSYCHOMANCER, n=1)
tk.line_up(psy, x=20.0, y=20.0)
prey = build(WARRIORS, owner="Player 1", n=1)
tk.line_up(prey, x=20.0, y=23.0)          # ~3" away, inside the 6" aura
tokens = list(psy.models) + list(prey.models)

checks.eq("a full-strength enemy is NOT a Nightmare Shroud candidate",
          psychomancer.below_starting_strength(prey), False)
prey.models[-1].current_wounds = 0        # one casualty
checks.true("...and a unit below its Starting Strength is",
            psychomancer.below_starting_strength(prey))

log = tk.Log()
bs = BattleShockController(dice_manager=tk.RecordingDice(), all_tokens=tokens, game_log=log)
shroud = psychomancer.NightmareShroudController(
    battle_shock_controller=bs, all_tokens=tokens, game_log=log)
# A SECOND enemy in range, at FULL strength. Without it the gate cannot be
# measured: with one candidate that happens to qualify, dropping the clause
# leaves the same list (found by the A/B probe, which reported NO BITE).
healthy = build(WARRIORS, owner="Player 1", n=2)
tk.line_up(healthy, x=24.0, y=23.0)
tokens += list(healthy.models)
shroud_tokens = tokens
checks.eq("...and a full-strength one is not",
          psychomancer.below_starting_strength(healthy), False)
checks.eq("the aura finds the wounded unit and ONLY it",
          [s.name for s in psychomancer.NightmareShroudController(
              all_tokens=shroud_tokens).candidates(psy)], [prey.name])
checks.eq("the aura finds it", [s.name for s in shroud.candidates(psy)], [prey.name])
started = shroud.begin_battle_shock_step({psy, prey}, command_phase_player="Player 1")
checks.true("...and a forced test really starts", started)
checks.true("...labelled as the Nightmare Shroud, at -1",
            "Nightmare Shroud" in (bs.dice_manager.last_roll or ("", []))[0]
            and "-1" in (bs.dice_manager.last_roll or ("", []))[0])

# "your OPPONENT's Command phase" - in the bearer's OWN, nothing happens.
bs2 = BattleShockController(dice_manager=tk.RecordingDice(), all_tokens=tokens, game_log=tk.Log())
shroud2 = psychomancer.NightmareShroudController(
    battle_shock_controller=bs2, all_tokens=tokens, game_log=tk.Log())
checks.eq("...but not in the Psychomancer's own Command phase",
          shroud2.begin_battle_shock_step({psy, prey}, command_phase_player="Player 2"), False)

dm = DecisionManager()
bs3 = BattleShockController(dice_manager=tk.RecordingDice(), all_tokens=tokens, game_log=tk.Log())
harb = psychomancer.HarbingerOfDespairController(
    battle_shock_controller=bs3, decision_manager=dm, all_tokens=tokens, game_log=tk.Log())
checks.eq("Harbinger reaches 18 inches", psychomancer.HARBINGER_RANGE_IN, 18.0)
checks.true("it offers in the bearer's own phase",
            harb.offer_at_start_of_phase({psy}, phase_owner="Player 2"))
checks.true("...naming the target unit, so it is answerable on the board",
            any(prey.name in label for label in tk.options_of(dm)))
tk.pick_option(dm, prey.name)
checks.true("...and once used it is spent for the turn", not harb.can_use(psy))
harb.reset_turn()
checks.true("...until the next turn", harb.can_use(psy))
checks.eq("...and it never offers in the opponent's phase",
          harb.offer_at_start_of_phase({psy}, phase_owner="Player 1"), False)

# --- 7. Master Chronomancer ---
print("--- 7. Master Chronomancer ---")

led = build(IMMORTALS, n=11)
checks.eq("Immortals alone have no invulnerable save",
          invulnerable_save.effective_invulnerable_save(led.models[0]), "-")
attached_units.attach(build(ORIKAN, n=11), led)
checks.eq("...and a 4+ while Orikan leads them",
          invulnerable_save.effective_invulnerable_save(led.models[0]), "4+")
checks.eq("...which reaches every model of the unit, not just him",
          {invulnerable_save.effective_invulnerable_save(m) for m in led.models}, {"4+"})

# It is a LEADING grant: a lone Orikan gives nobody else anything.
solo_orikan = build(ORIKAN, n=12)
bystander = build(IMMORTALS, n=12)
checks.eq("a lone Orikan grants a neighbouring unit nothing",
          invulnerable_save.effective_invulnerable_save(bystander.models[0]), "-")
checks.eq("...though he keeps his own printed 4+",
          invulnerable_save.effective_invulnerable_save(solo_orikan.models[0]), "4+")

# --- 8. The Stars Are Right ---
print("--- 8. The Stars Are Right ---")

checks.eq("it triples", the_stars_are_right.MULTIPLIER, 3)

orikan = build(ORIKAN, n=13)
model = orikan.models[0]
gun = StaffOfTomorrowProfile()
checks.true("inactive, the weapon is untouched",
            the_stars_are_right.adjusted_weapon(gun, model) is gun)

sar = the_stars_are_right.TheStarsAreRightController(game_log=tk.Log(), auto_players=("Player 2",))
checks.true("the AI answers it itself", sar.offer_at_start_of_fight_phase({orikan}))
tripled = the_stars_are_right.adjusted_weapon(gun, model)
checks.eq("A2 S4 becomes A6 S12", (tripled.attacks, tripled.strength), (6, 12))
checks.true("...as a COPY - the shared class object is untouched",
            tripled is not gun and StaffOfTomorrowProfile().strength == 4)

# IT NAMES THE WEAPON. Without this the clause could be "every melee weapon
# this model carries" and nothing would notice (the A/B probe reported NO
# BITE until it was added).
other = AeonstaveMeleeProfile()
checks.true("a weapon the rule does not name is untouched, even on an active model",
            the_stars_are_right.adjusted_weapon(other, model) is other)

# THE READING THAT MATTERS: it changes a CHARACTERISTIC, so it crosses
# Toughness boundaries a modifier could not have.
from game.shooting import _wound_threshold
checks.eq("S4 against T4 needs a 4+", _wound_threshold(4, 4), 4)
checks.eq("...and the tripled S12 against T4 needs a 2+ - two boundaries",
          _wound_threshold(12, 4), 2)

checks.eq("every successful Wound becomes a Critical Wound",
          the_stars_are_right.crit_wound_threshold(model, 3, 6), 3)
checks.eq("...and an already-better [ANTI-X] threshold is never made worse",
          the_stars_are_right.crit_wound_threshold(model, 4, 2), 2)
checks.eq("...while an inactive model keeps rule 05.02's unmodified 6",
          the_stars_are_right.crit_wound_threshold(build(ORIKAN, n=14).models[0], 3, 6), 6)

checks.true("it is once per BATTLE", not sar.can_use(orikan))
sar.reset_phase([orikan])
checks.true("...so the phase reset clears the mark",
            not the_stars_are_right.is_active(model))
checks.true("...but NOT the once-per-battle ledger", not sar.can_use(orikan))

# The per-MODEL half: an attached bodyguard's own weapon is untouched.
host2 = build(IMMORTALS, n=15)
attached_units.attach(build(ORIKAN, n=15), host2)
sar2 = the_stars_are_right.TheStarsAreRightController(
    game_log=tk.Log(), auto_players=("Player 2",))
sar2.offer_at_start_of_fight_phase({host2})
bodyguard = [m for m in host2.models
             if not getattr(m.profile, "the_stars_are_right", False)][0]
checks.true("a bodyguard model is not made active by its leader's ability",
            not the_stars_are_right.is_active(bodyguard))
checks.eq("...and its crit threshold stays rule 05.02's 6",
          the_stars_are_right.crit_wound_threshold(bodyguard, 3, 6), 6)

# END TO END through FightController._wound_crit(), which is what actually
# resolves. Everything above measures the module; a probe that made the
# controller read the SQUAD instead of the attacking model left the section
# fully green until this was added (error class 24).
scene2 = tk.fight_scene(IMMORTALS, WARRIORS, attacker_owner="Player 2")
fc2 = scene2["fight"]
fc2.fighting_squad = scene2["attacker"]
orikan2 = build(ORIKAN, n=16)
orikan2.models[0].stars_are_right_active = True
scene2["attacker"].models.append(orikan2.models[0])
plain_model = scene2["attacker"].models[0]
fc2.current_group = {"pairs": [(plain_model, AeonstaveMeleeProfile())]}
checks.eq("the real helper gives a BODYGUARD rule 05.02's unmodified 6",
          fc2._wound_crit(AeonstaveMeleeProfile(), scene2["target"], 3), 6)
fc2.current_group = {"pairs": [(orikan2.models[0], StaffOfTomorrowProfile())]}
checks.eq("...and the active model every-success-crits",
          fc2._wound_crit(StaffOfTomorrowProfile(), scene2["target"], 3), 3)

# --- 9. wiring, AI negative space and sprites ---
print("--- 9. wiring, AI negative space and sprites ---")

checks.true("Master Chronomancer is asked in the invulnerable chain",
            'leader_ability(squad, "master_chronomancer")'
            in io.open("game/invulnerable_save.py", encoding="utf-8").read())
checks.true("The Stars Are Right reaches the melee adjuster chain",
            "the_stars_are_right.adjusted_weapon(" in fight_src)
checks.true("...and its crit half is routed through one helper",
            "def _wound_crit(" in fight_src)
checks.eq("...which every crit-wound site in fight.py uses",
          fight_src.count("self._wound_crit("), 4)

# main.py's own wiring. Checked as CALL EXPRESSIONS rather than by counting a
# name: a name appears in its own import line and in comments, and this repo
# has been caught twice by a guard that matched its own explanation.
main_src = io.open("main.py", encoding="utf-8").read()
for needle, label in [
    ("shooting_controller.on_squad_finished_shooting.append("
     "chronometron_controller.offer_after_shooting)",
     "Chronometron is offered after shooting"),
    ("chronometron_controller=chronometron_controller,",
     "...and its Confirm button reaches its own controller"),
    ("harbinger_of_despair_controller.offer_at_start_of_phase(",
     "Harbinger of Despair is offered at a phase start"),
    ("harbinger_of_despair_controller.reset_turn()",
     "...and its once-per-turn ledger is cleared at end of turn"),
    ("nightmare_shroud_controller.begin_battle_shock_step(",
     "Nightmare Shroud fires in the Battle-Shock step"),
    ("nightmare_shroud_controller.on_dice_acknowledged()",
     "...and its queue is drained as each roll is acknowledged"),
    ("the_stars_are_right_controller.offer_at_start_of_fight_phase(",
     "The Stars Are Right is offered at the start of the Fight phase"),
    ("the_stars_are_right_controller.reset_phase(",
     "...and its ACTIVE mark is cleared on the phase change"),
]:
    checks.true("main.py: %s" % label, needle in main_src)

# Construction order (error class 23): every one of the four must be built
# before the line that first uses it, and no suite drives main() to find out.
for ctor, user in [
    ("chronometron_controller = ChronometronController(",
     "chronometron_controller.offer_after_shooting"),
    ("nightmare_shroud_controller = NightmareShroudController(",
     "nightmare_shroud_controller.begin_battle_shock_step("),
    ("harbinger_of_despair_controller = HarbingerOfDespairController(",
     "harbinger_of_despair_controller.offer_at_start_of_phase("),
    ("the_stars_are_right_controller = TheStarsAreRightController(",
     "the_stars_are_right_controller.offer_at_start_of_fight_phase("),
]:
    checks.true("main.py builds %s before it is used" % ctor.split(" =")[0],
                0 <= main_src.find(ctor) < main_src.find(user))

ai_src = io.open("ai/agent_driver.py", encoding="utf-8").read()
checks.true("no AI path names any of the three Cryptek abilities",
            not any(n in ai_src for n in ("timesplinter", "chronometron",
                                          "nightmare_shroud", "harbinger_of_despair",
                                          "master_chronomancer", "stars_are_right")))

for sheet, _p in SHEETS:
    sq = build(sheet, n=20)
    art = sprites.sprite_for(sq.models[0])
    checks.true("%s draws its own art" % sheet.name, art is not None)

# The shadowing check the substring matcher makes necessary.
checks.eq("Orikan does not borrow the Chronomancer's art",
          sprites._key_for_name("2 Orikan The Diviner 1"), "Orikan the Diviner")
checks.eq("...and the Chronomancer keeps his own",
          sprites._key_for_name("2 Chronomancer 1"), "Chronomancer")

checks.finish()
