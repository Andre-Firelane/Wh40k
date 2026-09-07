"""Warlock / Spiritseer / Farseer Skyrunner (Etappe 4a).

THE THREE STANDALONE ASURYANI PSYKERS. Together because all three are one-model
CHARACTER PSYKERs whose abilities plug into machinery that already exists for
someone else - which is the thing most likely to go wrong quietly:

  * the Warlock reuses the Warlock Conclave's STATLINE but not its abilities;
  * the Spiritseer reuses Illuminor Szeras' conditional Lone Operative seam;
  * the Farseer Skyrunner reuses Guide/Doom's mark and Branching Fates' flag.

WHERE THIS MEASURES, AND WHY THERE
----------------------------------
  * Misfortune is measured through the real _wound_modifiers() on the ATTACKER
    side. Read against the target instead it would still look like a working
    mark and be the mirror image of the printed rule.
  * Runes of Fortune is measured on the real Charge roll total, and with TWO
    bearing targets, because a naive per-target sum reads identically in every
    one-target scenario.
  * Tears of Isha's two branches are measured on a unit that has lost a model
    AND on one that has only lost wounds - "otherwise" is not a free choice.
"""
import testkit as tk
from testkit import Checks

from game import (misfortune, psychic_communion, runes_of_fortune, spiritseer,
                  sprites, status_effects)
from game.factions import aeldari as ae
from game.factions.aeldari_points import AELDARI_POINTS
from game.units import (
    FarseerProfile, FarseerSkyrunnerProfile, LoneWarlockProfile,
    SpiritseerProfile, WarlockProfile, WarlockSkyrunnerProfile,
)
from game.weapons import (
    EldritchStormProfile, ShurikenPistolProfile, SingingSpearMeleeProfile,
    TwinShurikenCatapultProfile, WitchStaffProfile, WitchbladeProfile,
)

checks = Checks("Aeldari psykers")


def build(sheet, owner="Player 1", n=1, **kw):
    return tk.build(sheet, owner, name="%s %s %d" % (owner[-1], sheet.name, n), **kw)


# --- 1. statlines -----------------------------------------------------------
print("--- 1. statlines ---")

lw = LoneWarlockProfile
checks.true("the lone Warlock INHERITS the Conclave's statline",
            issubclass(lw, WarlockProfile))
checks.eq("...so every characteristic matches",
          (lw.movement_in, lw.toughness, lw.wounds, lw.armor_save, lw.leadership,
           lw.oc, lw.invulnerable_save, lw.base_radius_in),
          (WarlockProfile.movement_in, WarlockProfile.toughness, WarlockProfile.wounds,
           WarlockProfile.armor_save, WarlockProfile.leadership, WarlockProfile.oc,
           WarlockProfile.invulnerable_save, WarlockProfile.base_radius_in))
# ...and exactly the printed differences, each one separately: an inherited
# flag left standing is the Sky Ray's `armour_hunter` mistake.
checks.true("it does NOT inherit Protect - the Conclave prints that, this does not",
            WarlockProfile.protect and not lw.protect)
checks.true("it does NOT inherit the Conclave's leader-slot-free JOIN",
            WarlockProfile.joins_without_leader_slot and not lw.joins_without_leader_slot)
checks.true("its CORE line is Support, not Leader", lw.support and not lw.leader)
checks.true("it DOES print Runes of Fortune, where the Conclave does not",
            lw.runes_of_fortune and not WarlockProfile.runes_of_fortune)
checks.true("...and both keep Psychic Communion",
            lw.psychic_communion and WarlockProfile.psychic_communion)

sp = SpiritseerProfile
checks.eq('Spiritseer M7"/T3/Sv6+/W3/Ld6+/OC1',
          (sp.movement_in, sp.toughness, sp.armor_save, sp.wounds, sp.leadership, sp.oc),
          (7, 3, "6+", 3, "6+", 1))
checks.eq("WS2+/BS2+", (sp.weapon_skill, sp.ballistic_skill), ("2+", "2+"))
checks.eq("Invulnerable 4+", sp.invulnerable_save, "4+")
checks.eq("25 mm base", round(sp.base_radius_in, 3), round(25 / 2 / 25.4, 3))
checks.true("INFANTRY CHARACTER PSYKER with Stealth",
            sp.infantry and sp.character and sp.psyker and sp.stealth)
checks.true("...and it does NOT print lone_operative outright - the grant is "
            "conditional", not sp.lone_operative)

fs = FarseerSkyrunnerProfile
checks.eq('Farseer Skyrunner M14"/T4/Sv6+/W5/Ld6+/OC2',
          (fs.movement_in, fs.toughness, fs.armor_save, fs.wounds, fs.leadership, fs.oc),
          (14, 4, "6+", 5, "6+", 2))
checks.eq("WS2+/BS3+", (fs.weapon_skill, fs.ballistic_skill), ("2+", "3+"))
checks.true("MOUNTED, FLY, PSYKER and a FARSEER", fs.mounted and fs.fly and fs.psyker and fs.farseer)
checks.eq("45 mm on the table, like the other three jetbike datasheets",
          fs.base_radius_in, WarlockSkyrunnerProfile.base_radius_in)
checks.true("...which is NOT its printed 32 mm",
            abs(fs.base_radius_in - 32 / 2 / 25.4) > 0.2)
checks.true("it shares the foot Farseer's Branching Fates flag",
            fs.branching_fates and FarseerProfile.branching_fates)
checks.true("all three carry Battle Focus and PSYKER",
            all(p.battle_focus and p.psyker for p in (lw, sp, fs)))


# --- 2. weapons and wargear -------------------------------------------------
print("--- 2. weapons and wargear ---")

warlock, seer, sky = build(ae.WARLOCK), build(ae.SPIRITSEER), build(ae.FARSEER_SKYRUNNER)
checks.eq("Warlock loadout", sorted(w.name for w in warlock.models[0].weapons),
          ["Destructor", "Shuriken Pistol", "Witchblade"])
checks.eq("Spiritseer loadout", sorted(w.name for w in seer.models[0].weapons),
          ["Shuriken Pistol", "Witch Staff"])
checks.eq("Farseer Skyrunner loadout", sorted(w.name for w in sky.models[0].weapons),
          ["Eldritch Storm", "Shuriken Pistol", "Twin Shuriken Catapult", "Witchblade"])

ws, wb = WitchStaffProfile(), WitchbladeProfile()
checks.eq("the Witch Staff matches the Witchblade in A/S/AP and both keywords",
          (ws.attacks, ws.strength, ws.ap, ws.psychic, ws.anti),
          (wb.attacks, wb.strength, wb.ap, wb.psychic, wb.anti))
checks.eq("...and differs ONLY in Damage - D3 against a flat 2",
          (ws.damage_notation.sides, wb.damage_notation), (3, None))

for sheet, opt, line in ((ae.WARLOCK, ae.LONE_WARLOCK_WITCHBLADE_TO_SPEAR, "Warlock"),
                         (ae.FARSEER_SKYRUNNER,
                          ae.FARSEER_SKYRUNNER_WITCHBLADE_TO_SPEAR, "Farseer Skyrunner")):
    swapped = build(sheet, n=2, choices={line: {opt: 1}})
    names = [w.name for w in swapped.models[0].weapons]
    checks.true("%s: the witchblade becomes a singing spear" % sheet.name,
                "Witchblade" not in names and names.count("Singing Spear") == 2)
checks.eq("...and 'Singing Spear' twice is right - one gun row, one melee row",
          len([w for w in build(ae.WARLOCK, n=3,
                                choices={"Warlock": {ae.LONE_WARLOCK_WITCHBLADE_TO_SPEAR: 1}}
                                ).models[0].weapons if w.name == "Singing Spear"]), 2)
checks.eq("the Spiritseer has no wargear options at all",
          len(ae.SPIRITSEER.wargear_options), 0)


# --- 3. points and pairings -------------------------------------------------
print("--- 3. points and pairings ---")

checks.eq("Warlock 40", AELDARI_POINTS["Warlock"].cost_for(1, 1), 40)
checks.eq("Spiritseer 50", AELDARI_POINTS["Spiritseer"].cost_for(1, 1), 50)
checks.eq("Farseer Skyrunner 60", AELDARI_POINTS["Farseer Skyrunner"].cost_for(1, 1), 60)
checks.eq("the Warlock SUPPORTS the two Guardian datasheets",
          tuple(AELDARI_POINTS["Warlock"].supports),
          ("Guardian Defenders", "Storm Guardians"))
checks.eq("...and leads nothing", tuple(AELDARI_POINTS["Warlock"].leads), ())
checks.eq("the Farseer Skyrunner LEADS Windriders",
          tuple(AELDARI_POINTS["Farseer Skyrunner"].leads), ("Windriders",))
checks.eq("the Spiritseer neither leads nor supports - it stands alone",
          (tuple(AELDARI_POINTS["Spiritseer"].leads),
           tuple(AELDARI_POINTS["Spiritseer"].supports)), ((), ()))

from game import attached_units
guardians = tk.build(ae.GUARDIAN_DEFENDERS, "Player 1", name="1 Guardian Defenders 1")
windriders = tk.build(ae.WINDRIDERS, "Player 1", name="1 Windriders 1")
checks.eq("the Warlock really attaches to Guardian Defenders",
          attached_units.can_attach(build(ae.WARLOCK, n=4), guardians), [])
checks.true("...and not to Windriders",
            bool(attached_units.can_attach(build(ae.WARLOCK, n=5), windriders)))
checks.eq("the Farseer Skyrunner really attaches to Windriders",
          attached_units.can_attach(build(ae.FARSEER_SKYRUNNER, n=4), windriders), [])
checks.true("the Spiritseer attaches to nothing",
            bool(attached_units.can_attach(build(ae.SPIRITSEER, n=4), guardians)))
checks.eq("the Warlock is the SUPPORT role, not LEADER",
          attached_units.attachment_role(build(ae.WARLOCK, n=6)), attached_units.SUPPORT)


# --- 4. Runes of Fortune ----------------------------------------------------
print("--- 4. Runes of Fortune ---")

checks.eq("the penalty is 2", runes_of_fortune.RUNES_OF_FORTUNE_PENALTY, 2)
checks.true("the Warlock carries it",
            runes_of_fortune.squad_has_runes_of_fortune(build(ae.WARLOCK, n=7)))
checks.true("...and the Warlock Conclave does not",
            not runes_of_fortune.squad_has_runes_of_fortune(
                tk.build(ae.WARLOCK_CONCLAVE, "Player 1", name="1 Warlock Conclave 1")))
plain = tk.build(ae.GUARDIAN_DEFENDERS, "Player 1", name="1 Guardian Defenders 2")
checks.eq("no bearer among the targets -> no penalty",
          runes_of_fortune.charge_penalty_against([plain]), 0)
checks.eq("empty targets -> no penalty", runes_of_fortune.charge_penalty_against([]), 0)
one = build(ae.WARLOCK, n=8)
checks.eq("one bearer -> -2", runes_of_fortune.charge_penalty_against([plain, one]), 2)
# The clause a per-target sum would get wrong, and only here.
two = build(ae.WARLOCK, n=9)
checks.eq("TWO bearing targets -> still -2, not -4",
          runes_of_fortune.charge_penalty_against([one, two]), 2)
# 19.03's pooling: a Warlock attached to Guardians makes THAT unit a bearer.
merged = tk.build(ae.GUARDIAN_DEFENDERS, "Player 1", name="1 Guardian Defenders 3")
attached_units.attach(build(ae.WARLOCK, n=10), merged)
checks.eq("a unit the Warlock has joined carries it too (19.03)",
          runes_of_fortune.charge_penalty_against([merged]), 2)

# Measured on the real Charge roll total.
from game.charge import ChargeController
cc = ChargeController(dice_manager=tk.RecordingDice(), game_log=tk.Log())
cc.active_squad = tk.build(ae.STRIKING_SCORPIONS, "Player 2", name="2 Striking Scorpions 1")
cc.charge_targets = [plain]
base_total, _note = cc._capped_roll(8)
cc.charge_targets = [one]
runed_total, runed_note = cc._capped_roll(8)
checks.eq("the real Charge roll is 2 lower against a Warlock-bearing target",
          runed_total, base_total - 2)
checks.true("...and the note says why", "Runes of Fortune" in runed_note)


# --- 5. Psychic Communion, shared with the Conclave -------------------------
print("--- 5. Psychic Communion ---")

lone = build(ae.WARLOCK, n=11)
checks.eq("the lone Warlock is a Psychic Communion bearer, like the Conclave's",
          len(psychic_communion._warlocks(lone)), 1)
# ...and it really earns the bonus from a nearby friendly AELDARI PSYKER, which
# is the half a flag check cannot see.
tk.line_up(lone, x=20.0, y=20.0)
buddy = tk.build(ae.FARSEER, "Player 1", name="1 Farseer 2")
tk.line_up(buddy, x=20.0, y=22.0)
tokens = list(lone.models) + list(buddy.models)
checks.eq("+1 from one other friendly AELDARI PSYKER within 6\"",
          psychic_communion.bonus_for(lone.models[0], lone, tokens), 1)
far_buddy = tk.build(ae.FARSEER, "Player 1", name="1 Farseer 3")
tk.line_up(far_buddy, x=20.0, y=60.0)
checks.eq("...and nothing from one out of range",
          psychic_communion.bonus_for(lone.models[0], lone,
                                      list(lone.models) + list(far_buddy.models)), 0)


# --- 6. the Spiritseer's three abilities ------------------------------------
print("--- 6. the Spiritseer ---")

seer2 = build(ae.SPIRITSEER, n=5)
wraiths = tk.build(ae.WRAITHGUARD, "Player 1", name="1 Wraithguard 1")
tk.line_up(seer2, x=20.0, y=20.0)
tk.line_up(wraiths, x=20.0, y=21.0)
near = list(seer2.models) + list(wraiths.models)
checks.true("a WRAITH CONSTRUCT unit is recognised",
            spiritseer.is_wraith_construct_unit(wraiths))
checks.true("...and Guardian Defenders are not",
            not spiritseer.is_wraith_construct_unit(guardians))
checks.true("Lone Operative is granted within 3\" of one",
            spiritseer.grants_lone_operative(seer2, near))
checks.eq("...and it reaches the real status question",
          status_effects.lone_operative_range(seer2, near),
          spiritseer.SPIRITSEER_LONE_OPERATIVE_RANGE_IN)
far_seer = build(ae.SPIRITSEER, n=6)
far_wraiths = tk.build(ae.WRAITHGUARD, "Player 1", name="1 Wraithguard 2")
tk.line_up(far_seer, x=20.0, y=20.0)
tk.line_up(far_wraiths, x=20.0, y=50.0)
far = list(far_seer.models) + list(far_wraiths.models)
checks.true("...and NOT when the wraiths are far away",
            not spiritseer.grants_lone_operative(far_seer, far))
checks.eq("...so the status question says it has none",
          status_effects.lone_operative_range(far_seer, far), None)

# Spirit Mark: a PAIR, not a mark.
sm = spiritseer.SpiritMarkController(game_log=tk.Log(), all_tokens=near)
enemy_a = tk.build(ae.GUARDIAN_DEFENDERS, "Player 2", name="2 Guardian Defenders 1")
enemy_b = tk.build(ae.GUARDIAN_DEFENDERS, "Player 2", name="2 Guardian Defenders 2")
checks.true("available before use", sm.available(seer2))
checks.eq("the wraiths are a legal friendly choice",
          [s.name for s in sm.friendly_candidates(seer2)], [wraiths.name])
sm.mark(seer2, wraiths, enemy_a)
checks.true("the marked pair gets the grant",
            sm.applies_to(wraiths, enemy_a))
checks.true("...but the SAME friendly unit against another enemy does NOT - "
            "the pair is the rule", not sm.applies_to(wraiths, enemy_b))
checks.true("...and another friendly unit against the marked enemy does not either",
            not sm.applies_to(guardians, enemy_a))
checks.true("once per turn, per army", not sm.available(seer2))
sm.start_of_movement_phase("Player 1")
checks.true("...and the mark ends at the start of the next Movement phase",
            not sm.applies_to(wraiths, enemy_a))
checks.true("...which also refreshes the use", sm.available(seer2))

# The grant itself, and the no-downgrade guard.
from game.weapons import WraithcannonProfile
gun = WraithcannonProfile()
sm2 = spiritseer.SpiritMarkController(all_tokens=near)
checks.true("unmarked -> the very same weapon object back",
            spiritseer.spirit_mark_adjusted_weapon(gun, sm2, wraiths, enemy_a) is gun)
sm2.mark(seer2, wraiths, enemy_a)
granted = spiritseer.spirit_mark_adjusted_weapon(gun, sm2, wraiths, enemy_a)
checks.eq("marked -> [SUSTAINED HITS 1]", granted.sustained_hits, 1)
checks.true("...as a copy, never mutating the shared profile",
            granted is not gun and WraithcannonProfile().sustained_hits == 0)
already = WraithcannonProfile()
already.sustained_hits = 2
checks.true("a weapon that already prints a HIGHER X keeps it - the grant never "
            "downgrades", spiritseer.spirit_mark_adjusted_weapon(
                already, sm2, wraiths, enemy_a).sustained_hits == 2)

# Tears of Isha: two branches, and "otherwise" is not a free choice.
hurt = tk.build(ae.WRAITHGUARD, "Player 1", name="1 Wraithguard 3")
tk.line_up(hurt, x=20.0, y=21.0)
toi = spiritseer.TearsOfIshaController(
    game_log=tk.Log(), all_tokens=list(seer2.models) + list(hurt.models))
checks.eq("a full-strength, undamaged unit is not offered - it would buy nothing",
          toi.candidates(seer2), [])
hurt.models[0].current_wounds = 1
checks.eq("a DAMAGED unit is offered", [s.name for s in toi.candidates(seer2)], [hurt.name])
tk.script(2)
checks.eq("...and with nothing destroyed it HEALS", toi.resolve(seer2, hurt), "healed")
checks.eq("...by the D3 rolled", hurt.models[0].current_wounds, 3)
checks.eq("once per unit per turn", toi.candidates(seer2), [])
toi.reset_turn()

dead_unit = tk.build(ae.WRAITHGUARD, "Player 1", name="1 Wraithguard 4")
tk.line_up(dead_unit, x=20.0, y=21.0)
lost = dead_unit.models.pop()
dead_unit.destroyed_models.append(lost)
toi2 = spiritseer.TearsOfIshaController(
    game_log=tk.Log(), all_tokens=list(seer2.models) + list(dead_unit.models))
checks.eq("a unit that LOST a model returns it instead of healing",
          toi2.resolve(seer2, dead_unit), "returned")
checks.true("...back in the squad", lost in dead_unit.models)
checks.true("...and off the destroyed list", lost not in dead_unit.destroyed_models)


# --- 7. Misfortune ----------------------------------------------------------
print("--- 7. Misfortune ---")

mf = misfortune.MisfortuneController(game_log=tk.Log())
checks.eq("it prints the once-per-turn cap Doom does not", mf.once_per_turn, True)
victim = tk.build(ae.GUARDIAN_DEFENDERS, "Player 2", name="2 Guardian Defenders 7")
checks.true("nothing is afflicted to begin with", not mf.afflicts(victim))
mf._marks.setdefault("Player 1", set()).add(victim)
checks.true("a marked unit is afflicted", mf.afflicts(victim))
checks.true("...and an unmarked one is not",
            not mf.afflicts(tk.build(ae.GUARDIAN_DEFENDERS, "Player 2",
                                     name="2 Guardian Defenders 8")))
# THE reading that matters, measured through the real fold rather than off the
# inherited predicate: Guide and Doom help a FRIENDLY attack that TARGETS the
# marked unit; Misfortune must do nothing there. Read the Guide/Doom way it
# would still look like a working mark and be the mirror of the printed rule.
mirror = tk.shooting_scene(ae.GUARDIAN_DEFENDERS, ae.GUARDIAN_DEFENDERS,
                           attacker_owner="Player 1")
msc = mirror["shooting"]
msc.active_squad = mirror["attacker"]
plain_mods = sum(m.amount for m in msc._wound_modifiers(mirror["target"]))
mirror_mf = misfortune.MisfortuneController()
mirror_mf._marks.setdefault("Player 1", set()).add(mirror["target"])
msc.misfortune = mirror_mf
checks.eq("a friendly attack TARGETING the marked unit gets nothing - the "
          "mark is not read the Guide/Doom way",
          sum(m.amount for m in msc._wound_modifiers(mirror["target"])), plain_mods)

# Through the real wound folds, on the attacker side, in BOTH phases.
scene = tk.shooting_scene(ae.GUARDIAN_DEFENDERS, ae.GUARDIAN_DEFENDERS,
                          attacker_owner="Player 2")
sc = scene["shooting"]
sc.active_squad = scene["attacker"]
before = sum(m.amount for m in sc._wound_modifiers(scene["target"]))
live = misfortune.MisfortuneController()
live._marks.setdefault("Player 1", set()).add(scene["attacker"])
sc.misfortune = live
after = sum(m.amount for m in sc._wound_modifiers(scene["target"]))
checks.eq("the shooting wound step is 1 WORSE for a marked attacker",
          after - before, misfortune.MISFORTUNE_PENALTY)
checks.true("...labelled Misfortune",
            any(m.source == misfortune.MISFORTUNE_LABEL
                for m in sc._wound_modifiers(scene["target"])))

fscene = tk.fight_scene(ae.GUARDIAN_DEFENDERS, ae.GUARDIAN_DEFENDERS,
                        attacker_owner="Player 2")
fc = fscene["fight"]
fc.fighting_squad = fscene["attacker"]
fbefore = sum(m.amount for m in fc._wound_modifiers(WitchbladeProfile(), fscene["target"]))
flive = misfortune.MisfortuneController()
flive._marks.setdefault("Player 1", set()).add(fscene["attacker"])
fc.misfortune = flive
fafter = sum(m.amount for m in fc._wound_modifiers(WitchbladeProfile(), fscene["target"]))
checks.eq('the fight wound step too - "makes an attack", not "a ranged attack"',
          fafter - fbefore, misfortune.MISFORTUNE_PENALTY)


# --- 8. wiring and sprites --------------------------------------------------
print("--- 8. wiring and sprites ---")

main_src = open("main.py", encoding="utf-8").read()
for needle, label in [
    ("misfortune_controller = MisfortuneController(", "Misfortune is constructed"),
    ("misfortune_controller.offer_at_end_of_movement(", "...offered at the end of the Movement phase"),
    ("misfortune_controller.start_of_command_phase(turn_tracker.turn_owner)",
     "...and cleared at the start of the next Command phase"),
    ("misfortune=misfortune_controller, spirit_mark=spirit_mark_controller,",
     "both marks reach the attack controllers"),
    ("tears_of_isha_controller.reset_turn()", "Tears of Isha's per-turn ledger clears"),
]:
    checks.true("main.py: %s" % label, needle in main_src)
checks.eq("...and the marks reach BOTH attack controllers, not one",
          main_src.count("misfortune=misfortune_controller, spirit_mark=spirit_mark_controller,"), 2)

ai_src = open("ai/agent_driver.py", encoding="utf-8").read()
checks.true("no AI path for any of the three",
            not any(n in ai_src for n in
                    ("runes_of_fortune", "misfortune", "spirit_mark", "tears_of_isha")))

ART = {  # datasheets whose art the user has since supplied
    'Spiritseer': 'Spirit Seer.png',
    # The lone Warlock BORROWS the Conclave's file - same model, and the
    # Conclave is a unit of them (user decision).
    'Warlock': 'Warlock Conclaive.png',
}
for sheet in (ae.WARLOCK, ae.SPIRITSEER):
    sq = build(sheet, n=30)
    _p = sprites.sprite_for(sq.models[0])
    if sheet.name in ART:
        # AT THE MODEL, so a key naming a file that is not on disk fails here
        # rather than passing on a mapping table nobody checked. Named file, so
        # a datasheet quietly borrowing a NEIGHBOUR's art by substring match
        # fails too - which is how "Autarch" would shadow "Autarch Wayleaper".
        checks.true("%s draws its own art" % sheet.name,
                    ART[sheet.name] in (_p or ""))
    else:
        checks.eq("%s has no art yet - pinned so adding one is visible" % sheet.name,
                  _p, None)
# The Farseer Skyrunner has no file of its own and DELIBERATELY borrows the foot
# Farseer's: same character, and the closest thing in the folder. Pinned as a
# decision, because _key_for_name()'s substring matching would have produced the
# same result by accident and an accident is not worth relying on.
sky_art = sprites.sprite_for(build(ae.FARSEER_SKYRUNNER, n=30).models[0])
checks.true("the Farseer Skyrunner borrows the foot Farseer's art", sky_art)
checks.true("...and it is that file", "Farseer" in (sky_art or ""))
checks.true("...through an EXPLICIT mapping placed before the plain Farseer key",
            list(sprites.SQUAD_SPRITE_KEYS).index("Farseer Skyrunner")
            < list(sprites.SQUAD_SPRITE_KEYS).index("Farseer"))

checks.finish()
