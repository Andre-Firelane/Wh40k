"""Rule 04.01.03: weapons with more than one profile, and Hunter profiles.

"In the Select Weapons step (04.01), if a selected weapon has more than one
profile, then the controlling player must also select one of those profiles.
... Hunter profiles can only target units with the specified keywords. ... a
different profile can be selected for each model within that unit."

The profiles are the existing WeaponProfile.overcharge_profile chain read by
ONE module (game/weapon_profiles.py). What this suite pins, with synthetic
weapons carried by real squads through the REAL controllers:

  1. the chain itself - order, stable alternate instances, the [ONE SHOT] id
     tag, the grouping key and the Hunter test;
  2. grouping: two weapons identical in their first profile but not in the
     rest must NOT share a rule-04.03 group;
  3. the shooting flow - options per target, a Hunter profile only against its
     keywords, the chosen profile is what fires, the two-mode overcharge=True
     spelling still works;
  4. Split Fire - arming a profile per model, and a Hunter profile bouncing;
  5. the fight flow - the same, on the melee side, which read no link at all
     before the 2026-09 codex;
  6. the AI's deterministic choice - best expected wounds, never [HAZARDOUS],
     and [TORRENT] valued as an auto-hit;
  7. the hover datacard prints every profile as its own row;
  8. the REAL panel draws a button per profile, and pressing it fires that profile.
"""
import pygame

import testkit as tk
from ai import agent_driver
from game import shooting as shooting_mod
from game import weapon_profiles
from game import weapons as wp
from game.factions import orks, tau_empire as tau
from game.keyword_condition import MONSTER_OR_VEHICLE_TARGETS
from game.weapons import MELEE

c = tk.Checks("weapon profiles and Hunter profiles (rule 04.01.03)")


def section(title):
    print(f"--- {title} ---")


# ----------------------------------------------------------- synthetic arms
# Deliberately not real Ork weapons: the rule is what is under test, and a
# datasheet stage that retunes a real profile must not move this suite.

class GunLast(wp.WeaponProfile):
    name = "Test Gun - Hunter"
    range_in = 24
    attacks = 3
    strength = 10
    ap = -3
    damage = 3
    hunter_keywords = MONSTER_OR_VEHICLE_TARGETS


class GunSecond(wp.WeaponProfile):
    name = "Test Gun - Heavy"
    range_in = 24
    attacks = 2
    strength = 8
    ap = -1
    damage = 2
    overcharge_profile = GunLast


class GunFirst(wp.WeaponProfile):
    name = "Test Gun"
    range_in = 24
    attacks = 1
    strength = 4
    overcharge_profile = GunSecond


class PlainGun(wp.WeaponProfile):
    """Identical to GunFirst in every characteristic AND name - only the chain differs."""
    name = "Test Gun"
    range_in = 24
    attacks = 1
    strength = 4


class HazardSecond(GunSecond):
    name = "Test Gun - Overload"
    hazardous = True
    overcharge_profile = None


class HazardFirst(GunFirst):
    overcharge_profile = HazardSecond


class TorrentSecond(wp.WeaponProfile):
    name = "Test Gun - Spray"
    range_in = 12
    attacks = 3
    strength = 5
    torrent = True


class ShotFirst(wp.WeaponProfile):
    name = "Test Gun - Aimed"
    range_in = 24
    attacks = 3
    strength = 5
    overcharge_profile = TorrentSecond


class BladeHunter(wp.WeaponProfile):
    name = "Test Blade - Hunter"
    weapon_type = MELEE
    attacks = 3
    strength = 6
    ap = -2
    hunter_keywords = MONSTER_OR_VEHICLE_TARGETS


class Blade(wp.WeaponProfile):
    name = "Test Blade - Standard"
    weapon_type = MELEE
    attacks = 3
    strength = 4
    overcharge_profile = BladeHunter


class Loop(wp.WeaponProfile):
    name = "Loop"


Loop.overcharge_profile = Loop


def arm(squad, cls):
    """Every model carries its OWN instance - weapon instances are never shared."""
    for model in squad.models:
        model.weapons = [cls()]
    return squad


# ------------------------------------------------------------ 1. the chain

section("1. the profile chain")

carried = GunFirst()
chain = weapon_profiles.profiles(carried)
c.eq("the chain is in printed order", [type(p) for p in chain], [GunFirst, GunSecond, GunLast])
c.true("index 0 IS the carried instance", chain[0] is carried)
c.true("the alternates are built ONCE and cached (stable instances)",
       all(a is b for a, b in zip(chain, weapon_profiles.profiles(carried))))
c.eq("each alternate is tagged with the carried instance's id (the [ONE SHOT] ledger key)",
     [p.overcharge_of_id for p in chain[1:]], [id(carried), id(carried)])
c.eq("profile_classes() walks the chain without instantiating",
     weapon_profiles.profile_classes(carried), [GunFirst, GunSecond, GunLast])
c.eq("a self-linking chain stops instead of looping", len(weapon_profiles.profiles(Loop())), 1)

import copy  # noqa: E402
twin = copy.copy(carried)
twin_chain = weapon_profiles.profiles(twin)
c.true("a shallow COPY is answered freshly (its index 0 is the copy)", twin_chain[0] is twin)
c.true("...and it does not overwrite the carried instance's cache",
       weapon_profiles.profiles(carried)[1] is chain[1])

c.eq("chain_key() is empty for a one-profile weapon, so no existing group splits",
     weapon_profiles.chain_key(PlainGun()), ())
c.eq("...and names the alternates otherwise", weapon_profiles.chain_key(carried), ("GunSecond", "GunLast"))
c.eq("has_alternates()", (weapon_profiles.has_alternates(carried), weapon_profiles.has_alternates(PlainGun())),
     (True, False))

boyz = tk.build(orks.BOYZ, "Player 1", name="1 Boyz 1")
devilfish = tk.build(tau.DEVILFISH, "Player 1", name="1 Devilfish 1")
c.eq("a non-Hunter profile allows any target", weapon_profiles.hunter_allows(chain[1], boyz), True)
c.eq("a Hunter profile allows a target with its keywords", weapon_profiles.hunter_allows(chain[2], devilfish), True)
c.eq("...and not one without them", weapon_profiles.hunter_allows(chain[2], boyz), False)
c.eq("...and no target at all allows nothing", weapon_profiles.hunter_allows(chain[2], None), False)
c.eq("printed_keywords spells the Hunter row", wp.printed_keywords(GunLast), ["HUNTER: MONSTER/VEHICLE"])


# -------------------------------------------------------------- 2. grouping

section("2. a different chain is a different rule-04.03 group")

pair = tk.build(tau.STRIKE_TEAM, "Player 1", name="1 Strike Team 1")
tk.line_up(pair)
for model in pair.models:
    model.weapons = [PlainGun()]
c.eq("liveness: identical plain guns share ONE group", len(shooting_mod._attack_groups(pair)), 1)
pair.models[0].weapons = [GunFirst()]
c.eq("one model's gun has further profiles: TWO groups, though the first profiles are identical",
     len(shooting_mod._attack_groups(pair)), 2)


# ------------------------------------------------------ 3. the shooting flow

section("3. choosing a profile in the Shooting phase")


def shooting_at(target_sheet, cls=GunFirst):
    s = tk.shooting_scene(tau.STRIKE_TEAM, target_sheet, attacker_owner="Player 1", gap=10.0)
    arm(s["attacker"], cls)
    sc = s["shooting"]
    sc.start_shooting(s["attacker"])
    if sc.state == shooting_mod.CHOOSING_SHOOTING_TYPE:
        sc.choose_shooting_type(shooting_mod.NORMAL_SHOOTING)
    sc.choose_target_squad(s["target"])
    return s


s = shooting_at(orks.BOYZ)
sc = s["shooting"]
c.eq("scene: the activation is at the weapon choice", sc.state, shooting_mod.CHOOSING_WEAPON)
entries = sc.weapon_eligibility()
c.eq("one weapon group is offered", len(entries), 1)
key = entries[0][0] if entries else None
c.eq("its entry names the first profile", entries[0][1] if entries else None, "Test Gun")
c.eq("...and the two-mode overcharge_label is the second", entries[0][4] if entries else None, "Test Gun - Heavy")
options = sc.profile_options(key)
c.eq("against infantry the Hunter profile is NOT offered", [o[0] for o in options], [0, 1])
c.eq("a non-[HAZARDOUS] profile does not claim to be hazardous", [o[2] for o in options], [False, False])
sc.choose_weapon(key, profile=2)
c.eq("choosing the Hunter profile anyway is refused", (sc.state, sc.current_group),
     (shooting_mod.CHOOSING_WEAPON, None))
sc.choose_weapon(key, profile=1)
fired = [w for _m, w in (sc.current_group or {}).get("pairs", [])]
c.true("choosing profile 1 fires something", bool(fired))
c.true("...and what fires is that profile, on every model", fired and all(type(w) is GunSecond for w in fired))
c.true("...as the cached alternates of the carried guns",
       fired and all(w.overcharge_of_id is not None for w in fired))

s2 = shooting_at(tau.DEVILFISH)
key2 = s2["shooting"].weapon_eligibility()[0][0]
c.eq("against a vehicle all three profiles are offered",
     [o[0] for o in s2["shooting"].profile_options(key2)], [0, 1, 2])

s3 = shooting_at(orks.BOYZ)
key3 = s3["shooting"].weapon_eligibility()[0][0]
s3["shooting"].choose_weapon(key3, overcharge=True)
fired3 = [w for _m, w in (s3["shooting"].current_group or {}).get("pairs", [])]
c.true("overcharge=True still means the second selectable profile",
       fired3 and all(type(w) is GunSecond for w in fired3))

s4 = shooting_at(orks.BOYZ)
key4 = s4["shooting"].weapon_eligibility()[0][0]
s4["shooting"].choose_weapon(key4)
fired4 = [w for _m, w in (s4["shooting"].current_group or {}).get("pairs", [])]
c.true("no profile given fires the first", fired4 and all(type(w) is GunFirst for w in fired4))


# ------------------------------------------------------------ 4. split fire

section("4. Split Fire arms a profile per model")

s5 = tk.shooting_scene(tau.STRIKE_TEAM, orks.BOYZ, attacker_owner="Player 1", gap=10.0)
arm(s5["attacker"], GunFirst)
sc5 = s5["shooting"]
sc5.start_shooting(s5["attacker"])
if sc5.state == shooting_mod.CHOOSING_SHOOTING_TYPE:
    sc5.choose_shooting_type(shooting_mod.NORMAL_SHOOTING)
sc5.toggle_split_fire()
sc5.begin_assignment()
c.eq("scene: split fire is assigning", sc5.state, shooting_mod.ASSIGNING)
c.eq("every profile of the queued gun can be armed (the target is not known yet)",
     sc5.assignment_profile_names(), ["Test Gun", "Test Gun - Heavy", "Test Gun - Hunter"])
c.eq("the first profile is armed by default", getattr(sc5.armed_assignment_profile(), "name", None), "Test Gun")
sc5.toggle_assignment_overcharge()
c.eq("the toggle arms the next one", getattr(sc5.armed_assignment_profile(), "name", None), "Test Gun - Heavy")
queued = len(sc5.assignment_queue)
front = sc5.assignment_queue[0] if sc5.assignment_queue else None
sc5.assign_current(s5["target"], profile=2)
c.eq("a Hunter profile BOUNCES off infantry (the pair stays at the front)",
     (len(sc5.assignment_queue), sc5.assignment_queue[0] if sc5.assignment_queue else None), (queued, front))
sc5.assign_current(s5["target"], profile=1)
assigned = [w for pairs in sc5.assignments.values() for _m, w in pairs]
c.eq("assigning with profile 1 books that profile", [type(w) for w in assigned], [GunSecond])
c.eq("...and disarms back to the first for the next model", sc5.assignment_profile, 0)


# ----------------------------------------------------------- 5. the fight

section("5. choosing a profile in the Fight phase")


def fighting_against(target_sheet):
    f = tk.fight_scene(tau.STRIKE_TEAM, target_sheet, attacker_owner="Player 1")
    arm(f["attacker"], Blade)
    fc = f["fight"]
    fc.select_to_fight(f["attacker"])
    if fc.state == "choosing_target":
        fc.choose_target_squad(f["target"])
    return f


f1 = fighting_against(orks.BOYZ)
fc1 = f1["fight"]
c.eq("scene: the fight activation is at the weapon choice", fc1.state, "choosing_weapon")
melee_entries = fc1.weapon_eligibility()
c.true("scene: a melee group is offered", bool(melee_entries))
mkey = melee_entries[0][0] if melee_entries else None
c.eq("against infantry only the Standard profile is offered", [o[0] for o in fc1.profile_options(mkey)], [0])
c.eq("...so the AI has nothing to choose", agent_driver._best_profile_index(fc1, mkey, melee=True), None)

f2 = fighting_against(tau.DEVILFISH)
fc2 = f2["fight"]
mkey2 = fc2.weapon_eligibility()[0][0] if fc2.weapon_eligibility() else None
c.eq("against a vehicle the Hunter profile is offered too", [o[0] for o in fc2.profile_options(mkey2)], [0, 1])
c.eq("the AI swings the Hunter profile at the vehicle (S6 AP-2 beats S4 AP0)",
     agent_driver._best_profile_index(fc2, mkey2, melee=True), 1)
fc2.choose_weapon(mkey2, profile=1)
swung = [w for _m, w in (fc2.current_group or {}).get("pairs", [])]
c.true("choosing it swings that profile", swung and all(type(w) is BladeHunter for w in swung))

f3 = tk.fight_scene(tau.STRIKE_TEAM, orks.BOYZ, attacker_owner="Player 1")
arm(f3["attacker"], Blade)
fc3 = f3["fight"]
fc3.toggle_split_fire()
fc3.select_to_fight(f3["attacker"])
if fc3.state == "choosing_target":
    fc3.choose_target_squad(f3["target"])
if fc3.state != "assigning":
    fc3.begin_assignment()
c.eq("scene: melee split fire is assigning", fc3.state, "assigning")
c.eq("the queued blade's profiles are named", fc3.assignment_profile_names(),
     ["Test Blade - Standard", "Test Blade - Hunter"])
fc3.toggle_assignment_profile()
c.eq("the toggle arms the Hunter profile", getattr(fc3.armed_assignment_profile(), "name", None),
     "Test Blade - Hunter")
mqueued = len(fc3.assignment_queue)
fc3.assign_current(f3["target"])
c.eq("the armed Hunter profile bounces off infantry", len(fc3.assignment_queue), mqueued)


# ----------------------------------------------------- 6. the AI's choice

section("6. the AI picks deterministically")

a1 = shooting_at(orks.BOYZ)
akey = a1["shooting"].weapon_eligibility()[0][0]
c.eq("the heavier profile wins against infantry", agent_driver._best_profile_index(a1["shooting"], akey), 1)

a2 = shooting_at(orks.BOYZ, cls=HazardFirst)
hkey = a2["shooting"].weapon_eligibility()[0][0]
hopts = a2["shooting"].profile_options(hkey)
c.eq("scene: the better profile is [HAZARDOUS]", [o[2] for o in hopts], [False, True])
c.eq("...and the AI never picks it", agent_driver._best_profile_index(a2["shooting"], hkey), 0)

a3 = shooting_at(orks.BOYZ, cls=ShotFirst)
tkey = a3["shooting"].weapon_eligibility()[0][0]
# At 10" both profiles reach. Aimed: 3 shots at BS4+; Spray: 3 automatic hits
# at one more Strength. Valued as a 4+ hit roll the Spray would tie-lose; as
# the auto-hit it is, it wins.
c.eq("a [TORRENT] profile is valued as the auto-hit it is", agent_driver._best_profile_index(a3["shooting"], tkey), 1)

called = []


class StubController:
    target_squad = None

    def choose_weapon(self, key, **kwargs):
        called.append((key, kwargs))


agent_driver._choose_weapon_group(StubController(), "k")
c.eq("a controller that cannot name profiles gets exactly the old call", called, [("k", {})])


# ------------------------------------------------------ 7. the datacard rows

section("7. the datacard prints every profile")

pygame.init()
from game.ui.unit_datacard import UnitDatacardOverlay  # noqa: E402

card_squad = arm(tk.build(tau.STRIKE_TEAM, "Player 1", name="1 Strike Team 1"), GunFirst)
parts = UnitDatacardOverlay().card_parts(card_squad.models[0])
c.eq("one row per profile, in printed order",
     [w.name for w in parts.get("ranged_weapons", [])], ["Test Gun", "Test Gun - Heavy", "Test Gun - Hunter"])


# ------------------------------------------------------ 8. the real panel

section("8. the REAL panel draws a button per profile, and the button fires it")

from game import config as game_config  # noqa: E402
from game.movement import MovementController  # noqa: E402
from game.shooting import ShootingController  # noqa: E402
from game.ui.action_panel import ActionPanel  # noqa: E402

pygame.display.set_mode((320, 240))
panel_rect = pygame.Rect(0, 0, game_config.LEFT_PANEL_WIDTH, 900)
surface = pygame.Surface((game_config.LEFT_PANEL_WIDTH, 900))


def render(movement, shooting, **kwargs):
    """Draw the real panel once; return [(label, accent, rect)] and its buttons.
    Labels come from a spy on _draw_button - the panel stores only (rect,
    callback), so a button is found by the rect its label was drawn into."""
    panel = ActionPanel()
    drawn = []
    original = panel._draw_button

    def spy(surf, rect, text, *args, **kw):
        out = original(surf, rect, text, *args, **kw)
        drawn.append((text, kw.get("accent", args[0] if args else None), out))
        return out

    panel._draw_button = spy
    panel.draw(surface, panel_rect, movement, shooting, None, **kwargs)
    return drawn, list(panel._buttons)


def press(drawn, buttons, prefix):
    rect = next((r for text, _a, r in drawn if text.startswith(prefix)), None)
    callback = next((cb for r, cb in buttons if rect is not None and r == rect), None)
    if callback is not None:
        callback()
    return callback is not None


def mover(scene):
    return MovementController(obstacles=[], game_log=tk.Log(), player_name="Player 1",
                              turn_tracker=scene["turn"], all_tokens=scene["state"].tokens)


p1 = shooting_at(orks.BOYZ)
drawn, buttons = render(mover(p1), p1["shooting"])
labels = [text for text, _a, _r in drawn]
c.true("liveness: the weapon-choice screen drew the first profile's button",
       any(t.startswith("Test Gun (") for t in labels))
c.true("the second profile gets its own button", any(t.startswith("Test Gun - Heavy (") for t in labels))
c.true("...which does not claim [HAZARDOUS]", not any("Heavy [HAZARDOUS]" in t for t in labels))
c.eq("...and wears no danger accent",
     [a for t, a, _r in drawn if t.startswith("Test Gun - Heavy (")], [None])
c.true("the Hunter profile is not drawn against infantry", not any(t.startswith("Test Gun - Hunter") for t in labels))
c.true("pressing the second profile's button works", press(drawn, buttons, "Test Gun - Heavy ("))
pressed = [w for _m, w in (p1["shooting"].current_group or {}).get("pairs", [])]
c.true("...and fires THAT profile", pressed and all(type(w) is GunSecond for w in pressed))

p2 = shooting_at(tau.DEVILFISH)
labels2 = [t for t, _a, _r in render(mover(p2), p2["shooting"])[0]]
c.true("against a vehicle the Hunter profile gets a button", any(t.startswith("Test Gun - Hunter (") for t in labels2))

p3 = shooting_at(orks.BOYZ, cls=HazardFirst)
drawn3, _b3 = render(mover(p3), p3["shooting"])
c.eq("a [HAZARDOUS] profile says so and wears the danger accent",
     [(t.split(" (")[0], a) for t, a, _r in drawn3 if t.startswith("Test Gun - Overload")],
     [("Test Gun - Overload [HAZARDOUS]", "danger")])

p4 = tk.shooting_scene(tau.STRIKE_TEAM, orks.BOYZ, attacker_owner="Player 1", gap=10.0)
arm(p4["attacker"], GunFirst)
sc_p4 = p4["shooting"]
sc_p4.start_shooting(p4["attacker"])
if sc_p4.state == shooting_mod.CHOOSING_SHOOTING_TYPE:
    sc_p4.choose_shooting_type(shooting_mod.NORMAL_SHOOTING)
sc_p4.toggle_split_fire()
sc_p4.begin_assignment()
mv4 = mover(p4)
drawn4, buttons4 = render(mv4, sc_p4)
c.true("split fire names the armed profile on its mode button",
       any(t == "Mode: Test Gun" for t, _a, _r in drawn4))
c.true("pressing the mode button works", press(drawn4, buttons4, "Mode: "))
c.true("...and arms the next profile",
       any(t == "Mode: Test Gun - Heavy" for t, _a, _r in render(mv4, sc_p4)[0]))

f4 = fighting_against(tau.DEVILFISH)
idle = ShootingController(all_tokens=f4["state"].tokens, dice_manager=f4["dice"], player_name="Player 1")
drawn5, buttons5 = render(mover(f4), idle, fight_controller=f4["fight"])
labels5 = [t for t, _a, _r in drawn5]
c.true("liveness: the fight weapon-choice screen drew the Standard profile",
       any(t.startswith("Test Blade - Standard (") for t in labels5))
c.true("the fight screen draws the Hunter profile against a vehicle",
       any(t.startswith("Test Blade - Hunter (") for t in labels5))
c.true("pressing it works", press(drawn5, buttons5, "Test Blade - Hunter ("))
swung5 = [w for _m, w in (f4["fight"].current_group or {}).get("pairs", [])]
c.true("...and swings THAT profile", swung5 and all(type(w) is BladeHunter for w in swung5))

f5 = tk.fight_scene(tau.STRIKE_TEAM, orks.BOYZ, attacker_owner="Player 1")
arm(f5["attacker"], Blade)
fc5 = f5["fight"]
fc5.toggle_split_fire()
fc5.select_to_fight(f5["attacker"])
if fc5.state == "choosing_target":
    fc5.choose_target_squad(f5["target"])
if fc5.state != "assigning":
    fc5.begin_assignment()
idle5 = ShootingController(all_tokens=f5["state"].tokens, dice_manager=f5["dice"], player_name="Player 1")
mv5 = mover(f5)
drawn6, buttons6 = render(mv5, idle5, fight_controller=fc5)
c.true("melee split fire draws a mode button for a multi-profile blade",
       any(t == "Mode: Test Blade - Standard" for t, _a, _r in drawn6))
c.true("pressing it works", press(drawn6, buttons6, "Mode: "))
c.true("...and arms the Hunter profile",
       any(t == "Mode: Test Blade - Hunter" for t, _a, _r in render(mv5, idle5, fight_controller=fc5)[0]))

c.finish()
