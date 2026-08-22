"""Player 1's army list, checked unit by unit against the list the user
supplied - every model line, every weapon, every drone, plus the three
attached units and the points each unit comes to.

Builds the roster the same way main() does (same datasheets, same gear and
choices), rather than driving main() itself: that keeps the check about WHAT
the army is, independent of deployment, which the Pre-game Sequence now owns.
"""

from game import attached_units, loadout
from game.factions import build_squad
from game.factions.tau_empire import (
    BREACHER_TEAM, CADRE_FIREBLADE, COLDSTAR_ADD_2X_BURST_CANNON, COLDSTAR_ADD_CYCLIC_ION_BLASTER,
    COMMANDER_FARSIGHT, COMMANDER_IN_COLDSTAR_BATTLESUIT, CRISIS_STARSCYTHE, CRISIS_SUNFORGE,
    DEVILFISH, DEVILFISH_SEEKER_MISSILE_OPTION, GHOSTKEEL_BATTLESUIT,
    GHOSTKEEL_FLAMER_TO_FUSION_BLASTER, GHOSTKEEL_FUSION_TO_ION_RAKER, KROOT_CARNIVORES,
    PATHFINDER_CARBINE_TO_GRENADE_LAUNCHER, PATHFINDER_CARBINE_TO_RAIL_RIFLE,
    PATHFINDER_TEAM, RIPTIDE_BATTLESUIT,
    RIPTIDE_BURST_TO_ION_ACCELERATOR, RIPTIDE_PLASMA_TO_TWIN_FUSION, STARSCYTHE_FLAMER_TO_BURST,
    STEALTH_BATTLESUITS, STRIKE_TEAM, THE_TWIN_LANCE,
)

PASS = []
FAIL = []


def check(label, ok, detail=""):
    (PASS if ok else FAIL).append(label)
    print(f"  {'PASS' if ok else 'FAIL'}  {label}" + (f"   [{detail}]" if detail else ""))


def build(datasheet, **kw):
    kw.setdefault("name", datasheet.name)
    return build_squad(datasheet, "Player 1", x_in=20, y_in=20, **kw)


def weapons(model):
    return sorted(w.name for w in model.weapons)


def line(squad, profile_name):
    return [m for m in squad.models if m.profile.name == profile_name]


print("\n1. Infantry")

breachers = build(BREACHER_TEAM, gear={"Breacher Fire Warrior Shas'ui": ["Guardian Drone", "Shield Drone"]})
shasui = line(breachers, "Breacher Fire Warrior Shas'ui")[0]
check("Breacher Team: 10 models", len(breachers.models) == 10)
check("Shas'ui has Guardian Drone + Shield Drone",
      sorted(shasui.gear_names) == ["Guardian Drone", "Shield Drone"], str(shasui.gear_names))
check("rank and file: Close combat weapon, Pulse blaster, Pulse pistol",
      weapons(line(breachers, "Breacher Fire Warrior")[0]) == ["Close Combat Weapon", "Pulse Blaster", "Pulse Pistol"])
check("Breacher Team costs 90", breachers.points == 90, str(breachers.points))

strike = build(STRIKE_TEAM, gear={"Fire Warrior Shas'ui": ["Guardian Drone", "Shield Drone"]})
check("Strike Team: 10 models, Shas'ui with Guardian + Shield Drone",
      len(strike.models) == 10
      and sorted(line(strike, "Fire Warrior Shas'ui")[0].gear_names) == ["Guardian Drone", "Shield Drone"])
check("rank and file: Close combat weapon, Pulse pistol, Pulse rifle",
      weapons(line(strike, "Fire Warrior")[0]) == ["Close Combat Weapon", "Pulse Pistol", "Pulse Rifle"])
check("Strike Team costs 70", strike.points == 70, str(strike.points))

kroot = build(KROOT_CARNIVORES)
check("Kroot Carnivores: 10 models, Long-quill carries the Kroot pistol",
      len(kroot.models) == 10 and "Kroot Pistol" in weapons(line(kroot, "Long-quill")[0]))
check("rank and file: Close combat weapon + Kroot rifle only",
      weapons(line(kroot, "Kroot Carnivore")[0]) == ["Close Combat Weapon", "Kroot Rifle"])
check("Kroot Carnivores costs 65", kroot.points == 65, str(kroot.points))

stealth = build(STEALTH_BATTLESUITS)
check("Stealth Battlesuits: 5 models, Battlesuit fists + Burst cannon",
      len(stealth.models) == 5
      and all(weapons(m) == ["Battlesuit Fists", "Burst Cannon"] for m in stealth.models))
check("Stealth Battlesuits costs 100", stealth.points == 100, str(stealth.points))


print("\n2. Pathfinder Team")

pathfinders = build(
    PATHFINDER_TEAM,
    gear={"Pathfinder Shas'ui": ["Shield Drone", "Shield Drone", "Grav-inhibitor Drone"]},
    choices={
        "Pathfinder Shas'ui": {PATHFINDER_CARBINE_TO_GRENADE_LAUNCHER: 1},
        "Pathfinder": {PATHFINDER_CARBINE_TO_RAIL_RIFLE: 3},
    },
)
pf_leader = line(pathfinders, "Pathfinder Shas'ui")[0]
check("10 models", len(pathfinders.models) == 10)
check("Shas'ui has 2x Shield Drone AND the Grav-inhibitor Drone",
      sorted(pf_leader.gear_names) == ["Grav-inhibitor Drone", "Shield Drone", "Shield Drone"],
      str(pf_leader.gear_names))
check("...which is 2 ordinary drones plus the one special one - both caps respected",
      pf_leader.gear_names.count("Shield Drone") == 2
      and pf_leader.gear_names.count("Grav-inhibitor Drone") == 1)
check("the Grav-inhibitor Drone's rule is live on the unit",
      pf_leader.profile.grav_inhibitor_drone)
check("Shas'ui swapped his Pulse carbine for the grenade launcher",
      "Semi-automatic Grenade Launcher - EMP" in weapons(pf_leader)
      and "Pulse Carbine" not in weapons(pf_leader), str(weapons(pf_leader)))
check("Shas'ui keeps his Pulse pistol and Close combat weapon",
      {"Pulse Pistol", "Close Combat Weapon"} <= set(weapons(pf_leader)))
rank = line(pathfinders, "Pathfinder")
rail = [m for m in rank if "Rail Rifle" in weapons(m)]
check("9 rank-and-file", len(rank) == 9)
check("exactly 3 of them carry a Rail rifle", len(rail) == 3, str(len(rail)))
check("...each having given up its own Pulse carbine, keeping pistol + ccw",
      all(weapons(m) == ["Close Combat Weapon", "Pulse Pistol", "Rail Rifle"] for m in rail),
      str(weapons(rail[0])))
check("the other 6 keep their Pulse carbines",
      sum(1 for m in rank if "Pulse Carbine" in weapons(m)) == 6)
rr = next(w for w in rail[0].weapons if w.name == "Rail Rifle")
check('Rail rifle 30"/A1/BS5+/S10/AP-4/D3, [DEVASTATING WOUNDS] + [HEAVY]',
      (rr.range_in, rr.attacks, rr.ballistic_skill, rr.strength, rr.ap, rr.damage,
       rr.devastating_wounds, rr.heavy) == (30, 1, "5+", 10, -4, 3, True, True))
check("its BS5+ override is doing real work - the model itself is BS4+",
      rail[0].profile.ballistic_skill == "4+")
check("Pathfinder Team costs 85 (the list says 90 - see the points note)",
      pathfinders.points == 85, str(pathfinders.points))


print("\n3. Battlesuits and vehicles")

ghostkeel = build(GHOSTKEEL_BATTLESUIT, choices={
    "Ghostkeel Battlesuit": {GHOSTKEEL_FUSION_TO_ION_RAKER: 1, GHOSTKEEL_FLAMER_TO_FUSION_BLASTER: 1}})
check("Ghostkeel: Ghostkeel fists + Cyclic ion raker + Twin fusion blaster",
      weapons(ghostkeel.models[0]) == ["Cyclic Ion Raker - Standard", "Ghostkeel Fists", "Twin Fusion Blaster"],
      str(weapons(ghostkeel.models[0])))
check("Ghostkeel has its Battlesuit support system", ghostkeel.models[0].profile.battlesuit_support_system)
check("Ghostkeel costs 165 (the list says 160 - see the points note)",
      ghostkeel.points == 165, str(ghostkeel.points))

riptide = build(RIPTIDE_BATTLESUIT, choices={
    "Riptide Battlesuit": {RIPTIDE_BURST_TO_ION_ACCELERATOR: 1, RIPTIDE_PLASMA_TO_TWIN_FUSION: 1}})
rw = weapons(riptide.models[0])
check("Riptide: Riptide fists, Ion accelerator, 2x Missile pod, Twin fusion blaster",
      rw == ["Ion Accelerator - Standard", "Missile Pod", "Missile Pod", "Riptide Fists", "Twin Fusion Blaster"],
      str(rw))
check("...so the Heavy burst cannon AND the Twin plasma rifle are both gone",
      "Heavy Burst Cannon" not in rw and "Twin Plasma Rifle" not in rw)
check("the 2 Missile pods are the baseline Missile Drones", rw.count("Missile Pod") == 2)
check("Riptide costs 215 (the list says 200 - see the points note)",
      riptide.points == 215, str(riptide.points))

lance = build(THE_TWIN_LANCE)
check("The Twin Lance: 2 models, Ri'Lantar and Ri'Locai",
      sorted(m.profile.name for m in lance.models) == ["Ri'Lantar", "Ri'Locai"])
check("Ri'Lantar carries the Fusion eliminator, Ri'Locai the Ion scattercannon",
      "Fusion Eliminator" in weapons(line(lance, "Ri'Lantar")[0])
      and any(w.startswith("Ion Scattercannon") for w in weapons(line(lance, "Ri'Locai")[0])))
check("both carry the MV15 Gun Drone's Twin pulse blaster, the Shardstorm and the XV pulse pistol",
      all({"Twin Pulse Blaster", "Shardstorm Burst System", "XV Pulse Pistol"} <= set(weapons(m))
          for m in lance.models))
check("The Twin Lance costs 220 (the list says 185 - see the points note)",
      lance.points == 220, str(lance.points))

devilfish = build(DEVILFISH, choices={"Devilfish": {DEVILFISH_SEEKER_MISSILE_OPTION: 1}})
dw = weapons(devilfish.models[0])
check("Devilfish: Accelerator burst cannon, Armoured hull, 2x Seeker missile, 2x Twin pulse carbine",
      dw.count("Seeker Missile") == 2 and dw.count("Twin Pulse Carbine") == 2
      and "Accelerator Burst Cannon" in dw and "Armoured Hull" in dw, str(dw))
check("Devilfish costs 75 (the list says 85 - see the points note)",
      devilfish.points == 75, str(devilfish.points))


print("\n4. The three attached units")

fireblade = build(CADRE_FIREBLADE, gear={"Cadre Fireblade": ["Gun Drone", "Gun Drone"]})
check("Cadre Fireblade has 2x Gun Drone", fireblade.models[0].gear_names == ["Gun Drone", "Gun Drone"])
merged_breachers = attached_units.attach(fireblade, build(
    BREACHER_TEAM, gear={"Breacher Fire Warrior Shas'ui": ["Guardian Drone", "Shield Drone"]}))
check("Fireblade attaches to the Breacher Team (11 models, one unit)",
      attached_units.is_attached_unit(merged_breachers) and len(merged_breachers.models) == 11)
check("...and it fits a Devilfish's 12-model capacity", len(merged_breachers.models) <= 12)
check("the merged unit costs 90 + 50", merged_breachers.points == 140, str(merged_breachers.points))

STARSCYTHE_LINES = ("Crisis Starscythe Shas'vre", "Crisis Starscythe Shas'ui (1)", "Crisis Starscythe Shas'ui (2)")
starscythe = build(CRISIS_STARSCYTHE, gear={
    "Crisis Starscythe Shas'vre": ["Marker Drone", "Shield Drone"],
    "Crisis Starscythe Shas'ui (1)": ["Gun Drone", "Shield Drone"],
    "Crisis Starscythe Shas'ui (2)": ["Gun Drone", "Shield Drone"],
}, choices={ln: {STARSCYTHE_FLAMER_TO_BURST: 1} for ln in STARSCYTHE_LINES})
# Subset, not equality: a Gun Drone grants its bearer a Twin pulse carbine
# and so legitimately shows up in that model's weapon list too.
check("Starscythe: every model on 2x Burst cannon + Battlesuit fists",
      all(weapons(m).count("Burst Cannon") == 2 and "Battlesuit Fists" in weapons(m)
          for m in starscythe.models), str([weapons(m) for m in starscythe.models]))
check("...and no model kept a T'au flamer",
      not any("Flamer" in w for m in starscythe.models for w in weapons(m)))
check("Shas'vre has Marker + Shield Drone, both Shas'ui Gun + Shield Drone",
      sorted(line(starscythe, "Crisis Starscythe Shas'vre")[0].gear_names) == ["Marker Drone", "Shield Drone"]
      and all(sorted(m.gear_names) == ["Gun Drone", "Shield Drone"]
              for m in line(starscythe, "Crisis Starscythe Shas'ui")))
coldstar = build(COMMANDER_IN_COLDSTAR_BATTLESUIT,
                 gear={"Commander in Coldstar Battlesuit": ["Shield Drone", "Shield Drone"]},
                 choices={"Commander in Coldstar Battlesuit": {
                     COLDSTAR_ADD_2X_BURST_CANNON: 1, COLDSTAR_ADD_CYCLIC_ION_BLASTER: 1}})
cw = weapons(coldstar.models[0])
check("Coldstar: 2x Burst cannon, Cyclic ion blaster, High-output burst cannon, Battlesuit fists",
      cw.count("Burst Cannon") == 2 and "Cyclic Ion Blaster - Standard" in cw
      and "High-output Burst Cannon" in cw and "Battlesuit Fists" in cw, str(cw))
check("Coldstar has 2x Shield Drone", coldstar.models[0].gear_names == ["Shield Drone", "Shield Drone"])
check("Coldstar's own base cost is 95", coldstar.points == 95, str(coldstar.points))
from game import starflare_ignition
starflare_ignition.grant(coldstar)
check("with the Starflare Ignition System (user: 'gib bitte dem coldstar noch...') it is 115",
      coldstar.points == 115, str(coldstar.points))
merged_starscythe = attached_units.attach(coldstar, starscythe)
check("Coldstar attaches to the Starscythe team", attached_units.is_attached_unit(merged_starscythe))

sunforge = build(CRISIS_SUNFORGE, gear={
    "Crisis Sunforge Shas'vre": ["Marker Drone", "Shield Drone"],
    "Crisis Sunforge Shas'ui (1)": ["Gun Drone", "Shield Drone"],
    "Crisis Sunforge Shas'ui (2)": ["Gun Drone", "Shield Drone"],
})
check("Sunforge: every model on 2x Fusion blaster + Battlesuit fists",
      all(weapons(m).count("Fusion Blaster") == 2 and "Battlesuit Fists" in weapons(m)
          for m in sunforge.models), str([weapons(m) for m in sunforge.models]))
check("the drones really are what adds the extra weapons",
      "Twin Pulse Carbine" in weapons(line(sunforge, "Crisis Sunforge Shas'ui")[0]))
check("Shas'vre has Marker + Shield Drone, both Shas'ui Gun + Shield Drone",
      sorted(line(sunforge, "Crisis Sunforge Shas'vre")[0].gear_names) == ["Marker Drone", "Shield Drone"]
      and all(sorted(m.gear_names) == ["Gun Drone", "Shield Drone"]
              for m in line(sunforge, "Crisis Sunforge Shas'ui")))
farsight = build(COMMANDER_FARSIGHT)
merged_sunforge = attached_units.attach(farsight, sunforge)
check("Farsight attaches to the Sunforge team", attached_units.is_attached_unit(merged_sunforge))
check("...and his Way of the Short Blade is live on the merged unit",
      any(m.profile.way_of_the_short_blade for m in merged_sunforge.models))
check("the merged unit costs 125 + 70", merged_sunforge.points == 195, str(merged_sunforge.points))


print("\n5. Army totals")

units = [
    merged_breachers, strike, kroot, pathfinders, stealth, ghostkeel, riptide, lance,
    devilfish, merged_starscythe, merged_sunforge,
]
check("11 units", len(units) == 11)
total = sum(u.points for u in units)
check("every unit is priced (no None)", all(u.points is not None for u in units))
print(f"       engine total: {total} pts   |   the supplied list totals 1525 pts,")
print("       plus the 20-pt Starflare Ignition System the list does not carry.")
check("the total is within 25 pts of the list's own plus the Enhancement",
      abs(total - (1525 + 20)) <= 25, f"{total} vs {1525 + 20}")

print(f"\n{len(PASS)}/{len(PASS) + len(FAIL)} checks passed")
if FAIL:
    print("FAILED:")
    for f in FAIL:
        print("  -", f)
    raise SystemExit(1)
