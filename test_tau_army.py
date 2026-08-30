"""The T'au Empire army list, as main.py builds it.

The list the user supplied on 2026-08-30, replacing the Retaliation Cadre
roster this list had been since it was restored from the initial commit.
21 list entries, 19 units after two attachments, 94 models.

THE TOTALS ARE DRIVEN THROUGH THE REAL BUILDER (section 5), the treatment
test_player2_necron_army.py gave the same failure: a suite that rebuilds the
roster by hand keeps reporting the previous army's numbers, green, while
checking an army that no longer exists. test_player1_army.py hit that twice.
The hand-built half below stays, because it is what checks each entry against
the list ON PAPER - but the SHAPE of the army is asked of game/army_lists.py
rather than written down a second time.

THE POINTS DELIBERATELY DISAGREE with the user's list, in BOTH directions.
game/factions/tau_empire_points.py holds the Wahapedia transcription and wins,
as it does for every other list here. Both numbers are pinned so the gap stays
a stated fact.

TWO THINGS THIS LIST IS THE FIRST TO DO, and both are pinned here rather than
left to be noticed:
  * it fields TWO detachments at once (Kauyon + Advanced Acquisition Cadre,
    2 + 1 DP against a budget of 3);
  * it buys NO Enhancement - it names none, so it takes none.
"""

import re

from testkit import Checks, build_squad
from game import army_lists, attached_units, detachments, enhancements, pregame
from game.factions import tau_empire as t

c = Checks("T'au Empire army list")

OWNER = "Player 1"


def build(sheet, name=None, **kw):
    kw.setdefault("name", name or f"1 {sheet.name} 1")
    return build_squad(sheet, OWNER, **kw)


def weapons(model):
    return sorted(w.name for w in model.weapons)


def line_counts(squad):
    out = {}
    for m in squad.models:
        out[m.profile.name] = out.get(m.profile.name, 0) + 1
    return out


ROSTER = []


def keep(squad):
    ROSTER.append(squad)
    return squad


# --- 1. the characters ------------------------------------------------------
print("--- 1. characters ---")

# Char3/Char4: two Cadre Fireblades, each with two Gun Drones. Identical
# builds, so they are pinned against EACH OTHER as well as against the list -
# a second copy that quietly differed would otherwise read as intentional.
fireblades = [build(t.CADRE_FIREBLADE, f"1 Cadre Fireblade {i}",
                    gear={"Cadre Fireblade": ["Gun Drone", "Gun Drone"]},
                    unit_index=i)
              for i in (1, 2)]
for i, fb in enumerate(fireblades, 1):
    c.eq(f"Fireblade {i}: one model", len(fb.models), 1)
    c.eq("...with his pulse rifle and close combat weapon, plus both Gun "
         "Drones' twin pulse carbines", weapons(fb.models[0]),
         ["Close Combat Weapon", "Fireblade Pulse Rifle",
          "Twin Pulse Carbine", "Twin Pulse Carbine"])
    c.eq("...and both drones in his two gear slots",
         fb.models[0].gear_names, ["Gun Drone", "Gun Drone"])
    c.eq("...at 50 pts", fb.points, 50)   # the list agrees
c.eq("the two Fireblades are built identically",
     weapons(fireblades[0].models[0]), weapons(fireblades[1].models[0]))

# Char1: Commander Shadowsun. Her whole loadout is the datasheet's - the list
# names no upgrade, and she HAS no wargear option. "Warlord" is a no-op here:
# this engine has no warlord concept (the same documented exception
# game/rapid_ingress.py records for AIRCRAFT).
shadowsun = keep(build(t.COMMANDER_SHADOWSUN))
c.eq("Char1 Shadowsun: one model", len(shadowsun.models), 1)
c.eq("...with the printed six weapons", weapons(shadowsun.models[0]),
     ["Battlesuit Fists", "Flechette Launcher", "High-energy Fusion Blaster",
      "High-energy Fusion Blaster", "Light Missile Pod", "Pulse Pistol"])
c.eq("...at 100 pts", shadowsun.points, 100)   # the list agrees
c.eq("...and she has no wargear option to get wrong",
     list(t.COMMANDER_SHADOWSUN.wargear_options or ()), [])
# She stands alone for a REASON, not by omission: no LEADER line at all, plus
# LONE OPERATIVE, which is the state that ability is written for.
c.eq("she prints no LEADER line, so she could not join anything",
     t.COMMANDER_SHADOWSUN.points.leads, ())
c.eq("...and LONE OPERATIVE 12\" is what standing alone buys her",
     shadowsun.models[0].profile.lone_operative, 12.0)

# Char5: the Ethereal, solo BY INSTRUCTION - unlike Shadowsun he CAN lead, so
# this one is a choice the user made ("der ethereal ist solo") and the check
# says which kind it is.
ethereal = keep(build(t.ETHEREAL))
c.eq("Char5 Ethereal: one model with the honour stave",
     weapons(ethereal.models[0]), ["Honour Stave"])
c.eq("...and no drone taken - the list names none", ethereal.models[0].gear_names, [])
c.eq("...at 50 pts", ethereal.points, 50)   # the list agrees
c.eq("he CAN lead a Breacher Team, so standing alone is the user's call",
     attached_units.can_attach(build(t.ETHEREAL, "1 Ethereal 9"),
                               build(t.BREACHER_TEAM, "1 Breacher Team 9")), [])

# Char2: The Twin Lance, one datasheet of two named models.
twin = keep(build(t.THE_TWIN_LANCE))
c.eq("Char2 The Twin Lance: two models", len(twin.models), 2)
c.eq("...Ri'Lantar with the fusion eliminators", weapons(twin.models[0]),
     ["Fusion Eliminator", "Fusion Eliminator", "Shardstorm Burst System",
      "Twin Pulse Blaster", "XV Pulse Pistol", "XV Pulse Pistol"])
c.eq("...Ri'Locai with the ion scattercannon and its second fire mode",
     weapons(twin.models[1]),
     ["Ion Scattercannon", "Ion Scattercannon - Standard",
      "Shardstorm Burst System", "Twin Pulse Blaster", "XV Pulse Pistol",
      "XV Pulse Pistol"])
c.eq("...at 220 pts", twin.points, 220)   # the list says 185
c.eq("...and it prints no LEADER line either",
     t.THE_TWIN_LANCE.points.leads, ())


# --- 2. the two Breacher Teams, their Fireblades and their Devilfish --------
print("--- 2. Breachers, Fireblades, Devilfish ---")

breachers = []
for i in (1, 2):
    br = build(t.BREACHER_TEAM, f"1 Breacher Team {i}",
               gear={"Breacher Fire Warrior Shas'ui": ["Guardian Drone", "Shield Drone"]},
               unit_index=i)
    breachers.append(br)
    c.eq(f"Breacher Team {i}: 1 Shas'ui + 9 Fire Warriors", line_counts(br),
         {"Breacher Fire Warrior Shas'ui": 1, "Breacher Fire Warrior": 9})
    c.eq("...every model with pulse blaster, pulse pistol and ccw",
         sorted({tuple(weapons(m)) for m in br.models}),
         [("Close Combat Weapon", "Pulse Blaster", "Pulse Pistol")])
    c.eq("...and the Shas'ui carrying the Guardian and Shield Drones",
         br.models[0].gear_names, ["Guardian Drone", "Shield Drone"])
    c.eq("...at 90 pts", br.points, 90)   # the list agrees

devilfish = [build(t.DEVILFISH, f"1 Devilfish {i}", unit_index=i) for i in (1, 2)]
for i, df in enumerate(devilfish, 1):
    c.eq(f"Devilfish {i}: the printed default, no seeker missiles",
         weapons(df.models[0]),
         ["Accelerator Burst Cannon", "Armoured Hull", "Twin Pulse Carbine",
          "Twin Pulse Carbine"])
    c.eq("...at 75 pts", df.points, 75)   # the list says 85
# The previous roster DID buy the seeker missiles; this one does not, and the
# option is still there. Pinned so dropping it reads as a choice.
c.true("the Devilfish seeker-missile option still exists, it is simply not taken",
       any(o.name == t.DEVILFISH_SEEKER_MISSILE_OPTION
           for o in t.DEVILFISH.wargear_options))

# The attachment the user named. attach() MERGES (19.01), so the result is one
# 11-model unit - which is also what has to fit the Devilfish's capacity of 12.
merged = [keep(attached_units.attach(fireblades[i], breachers[i])) for i in (0, 1)]
for i, unit in enumerate(merged, 1):
    c.eq(f"Breacher Team {i} + Fireblade is ONE unit of 11 models",
         len(unit.models), 11)
    c.eq("...priced as the sum of its two entries", unit.points, 140)
    c.eq("...and it still knows both datasheets it is made of",
         sorted(comp.datasheet.name for comp in unit.attached_components),
         ["Breacher Team", "Cadre Fireblade"])
c.true("11 models fit the Devilfish's 12-model T'AU EMPIRE INFANTRY capacity",
       all(m.profile.infantry for m in merged[0].models))
for df in devilfish:
    keep(df)


# --- 3. the rest of the roster ---------------------------------------------
print("--- 3. the rest ---")

# Broadside Battlesuits, three models, ALL identical: the heavy rail rifle
# traded for high-yield missile pods (this is the +5/model the price carries),
# a seeker missile and a twin plasma rifle in the two support slots, and two
# missile drones in the two drone slots. This datasheet's Gear is
# all_models=True, which is why one gear list dresses the whole unit.
broadside_gear = ["Seeker Missile", "Twin Plasma Rifle",
                  "Missile Drone", "Missile Drone"]
broadside = keep(build(
    t.BROADSIDE_BATTLESUITS, composition_index=2,
    choices={"Broadside Shas'vre": {t.BROADSIDE_RAIL_TO_MISSILE_PODS: 1},
             "Broadside Shas'ui": {t.BROADSIDE_RAIL_TO_MISSILE_PODS: 2}},
    gear={"Broadside Shas'vre": broadside_gear,
          "Broadside Shas'ui": broadside_gear}))
c.eq("Broadsides: 1 Shas'vre + 2 Shas'ui", line_counts(broadside),
     {"Broadside Shas'vre": 1, "Broadside Shas'ui": 2})
c.eq("...all three identically equipped",
     sorted({tuple(weapons(m)) for m in broadside.models}),
     [("Crushing Bulk", "High-yield Missile Pods", "Missile Pod", "Missile Pod",
       "Seeker Missile", "Twin Plasma Rifle")])
c.true("...with the heavy rail rifle really gone, not merely added to",
       all("Heavy Rail Rifle" not in weapons(m) for m in broadside.models))
c.eq("...at 270 pts: 255 for three, plus 5 per missile-pod swap",
     broadside.points, 270)   # the list agrees
c.eq("...which is 255 + 3x5", 255 + 3 * 5, 270)

for i in (1, 2):
    kc = keep(build(t.KROOT_CARNIVORES, f"1 Kroot Carnivores {i}", unit_index=i))
    c.eq(f"Kroot Carnivores {i}: 1 Long-quill + 9", line_counts(kc),
         {"Long-quill": 1, "Kroot Carnivore": 9})
    c.eq("...the Long-quill alone carries a pistol", weapons(kc.models[0]),
         ["Close Combat Weapon", "Kroot Pistol", "Kroot Rifle"])
    c.eq("...at 65 pts", kc.points, 65)   # the list agrees

hounds = keep(build(t.KROOT_HOUNDS, composition_index=0))
c.eq("Kroot Hounds: the 5-model composition", len(hounds.models), 5)
c.eq("...with ripping fangs and nothing else",
     sorted({tuple(weapons(m)) for m in hounds.models}), [("Ripping Fangs",)])
c.eq("...at 45 pts", hounds.points, 45)   # the list says 40

# Pathfinder Team: three rank-and-file take rail rifles and the Shas'ui KEEPS
# his pulse carbine. The previous roster traded that carbine for a
# semi-automatic grenade launcher, so "no swap on the leader" is the checkable
# difference, not an omission.
for i in (1, 2):
    pf = keep(build(t.PATHFINDER_TEAM, f"1 Pathfinder Team {i}",
                    choices={"Pathfinder": {t.PATHFINDER_CARBINE_TO_RAIL_RIFLE: 3}},
                    gear={"Pathfinder Shas'ui": ["Shield Drone", "Shield Drone",
                                                 "Grav-inhibitor Drone"]},
                    unit_index=i))
    c.eq(f"Pathfinder Team {i}: 1 Shas'ui + 9", line_counts(pf),
         {"Pathfinder Shas'ui": 1, "Pathfinder": 9})
    c.eq("...three rail rifles",
         len([m for m in pf.models if "Rail Rifle" in weapons(m)]), 3)
    c.eq("...six carbines among the rank and file, and the Shas'ui keeps his too",
         len([m for m in pf.models if "Pulse Carbine" in weapons(m)]), 7)
    c.eq("...so the leader takes NO grenade launcher, unlike the old roster",
         [m for m in pf.models
          if "Semi-automatic Grenade Launcher" in weapons(m)], [])
    c.eq("...and carries two Shield Drones plus the Grav-inhibitor Drone",
         pf.models[0].gear_names,
         ["Shield Drone", "Shield Drone", "Grav-inhibitor Drone"])
    c.eq("...at 85 pts", pf.points, 85)   # the list says 90

for i in (1, 2):
    pi = keep(build(t.PIRANHAS, f"1 Piranhas {i}", composition_index=0,
                    choices={"Piranhas": {t.PIRANHA_BURST_TO_FUSION: 1}},
                    gear={"Piranhas": ["Seeker Missile", "Seeker Missile"]},
                    unit_index=i))
    c.eq(f"Piranhas {i}: the single-model composition", len(pi.models), 1)
    c.eq("...fusion blaster, both seeker missiles, both twin pulse carbines",
         weapons(pi.models[0]),
         ["Armoured Hull", "Piranha Fusion Blaster", "Seeker Missile",
          "Seeker Missile", "Twin Pulse Carbine", "Twin Pulse Carbine"])
    c.eq("...at 65 pts", pi.points, 65)   # the list says 60

# TABLE SIZE, a user decision: "die piranhas sind zu gross, die sollten in
# etwa nur 2/3 so gross sein wie devil fish". Both datasheets PRINT a 60 mm
# flying base, so this is a deliberate departure and pinned against the
# Devilfish it is defined relative to rather than against a bare number - a
# ratio written down twice as two literals is what drifts.
_piranha_r = ROSTER[-1].models[0].radius_in
_devilfish_r = devilfish[0].models[0].radius_in
c.eq("the Piranha is two thirds of the Devilfish across",
     round(_piranha_r / _devilfish_r, 3), 0.667)
c.eq("...which is 2.80\" against 4.20\"",
     (round(2 * _piranha_r, 2), round(2 * _devilfish_r, 2)), (2.80, 4.20))
c.true("...and both datasheets really do print the same 60 mm base, so this "
       "is a table size and not a transcription",
       "60mm" in open("rules/tau_empire/Piranhas.md", encoding="utf-8").read()
       and "60mm" in open("rules/tau_empire/Devilfish.md", encoding="utf-8").read())

riptide = keep(build(t.RIPTIDE_BATTLESUIT,
                     choices={"Riptide Battlesuit": {
                         t.RIPTIDE_BURST_TO_ION_ACCELERATOR: 1,
                         t.RIPTIDE_PLASMA_TO_TWIN_FUSION: 1}}))
c.eq("Riptide: ion accelerator, twin fusion blaster, both missile pods",
     weapons(riptide.models[0]),
     ["Ion Accelerator - Standard", "Missile Pod", "Missile Pod",
      "Riptide Fists", "Twin Fusion Blaster"])
c.eq("...at 215 pts: 190 plus 25 for the accelerator", riptide.points, 215)   # list 200

# Stealth Battlesuits: the SHAS'VRE carries the fusion blaster. That is why
# game/factions/tau_empire.py now offers that swap on both model lines - it was
# scoped to the Shas'ui line alone, which made this printed build unbuildable.
for i in (1, 2):
    st = keep(build(t.STEALTH_BATTLESUITS, f"1 Stealth Battlesuits {i}",
                    choices={"Stealth Shas'vre": {t.STEALTH_BURST_TO_FUSION: 1}},
                    gear={"Stealth Shas'vre": ["Gun Drone", "Marker Drone"],
                          "Stealth Shas'ui": ["Homing Beacon"]},
                    unit_index=i))
    c.eq(f"Stealth {i}: 1 Shas'vre + 4 Shas'ui", line_counts(st),
         {"Stealth Shas'vre": 1, "Stealth Shas'ui": 4})
    c.eq("...the Shas'vre has the FUSION blaster, not a burst cannon",
         weapons(st.models[0]),
         ["Battlesuit Fists", "Fusion Blaster", "Twin Pulse Carbine"])
    c.eq("...plus his Gun Drone and Marker Drone",
         st.models[0].gear_names, ["Gun Drone", "Marker Drone"])
    c.eq("...all four Shas'ui keep their burst cannons",
         sorted({tuple(weapons(m)) for m in st.models[1:]}),
         [("Battlesuit Fists", "Burst Cannon")])
    c.eq("...and exactly one of them carries the Homing Beacon",
         [m.profile.name for m in st.models if m.profile.homing_beacon],
         ["Stealth Shas'ui"])
    c.eq("...at 100 pts", st.points, 100)   # the list agrees

vespid = keep(build(t.VESPID_STINGWINGS, composition_index=0))
c.eq("Vespid: 1 Strain Leader + 4", line_counts(vespid),
     {"Vespid Strain Leader": 1, "Vespid Stingwing": 4})
c.eq("...all with neutron blaster and stingwing claws",
     sorted({tuple(weapons(m)) for m in vespid.models}),
     [("Neutron Blaster", "Stingwing Claws")])
c.eq("...no blaster traded away - the list names none",
     [m for m in vespid.models if "Neutron Blaster" not in weapons(m)], [])
c.eq("...at 70 pts", vespid.points, 70)   # the list says 65


# --- 4. what the Stealth change did, and its known limitation --------------
print("--- 4. the Stealth Shas'vre swap ---")

# The printed line is "2 MODELS can each have their burst cannon replaced with
# 1 fusion blaster" - models, so the Shas'vre qualifies.
_stealth_md = "rules/tau_empire/Stealth Battlesuits.md"
_printed = open(_stealth_md, encoding="utf-8").read()
c.true("the printed line says MODELS, not Shas'ui",
       "2 models can each have their burst cannon replaced with 1 fusion blaster"
       in _printed)
_fusion_opts = [o for o in t.STEALTH_BATTLESUITS.wargear_options
                if o.name == t.STEALTH_BURST_TO_FUSION]
c.eq("...so the option sits on BOTH model lines", len(_fusion_opts), 2)
c.eq("...capped 1 on the Shas'vre and 2 on the Shas'ui",
     sorted(o.max_models for o in _fusion_opts), [1, 2])

# KNOWN LIMITATION: a WargearOption caps per LINE, so 1 + 2 = 3 is reachable
# against a printed 2. Measured rather than asserted away, and the roster
# cannot reach it because it takes exactly one.
_greedy = build(t.STEALTH_BATTLESUITS, "1 Stealth Battlesuits 9",
                choices={"Stealth Shas'vre": {t.STEALTH_BURST_TO_FUSION: 1},
                         "Stealth Shas'ui": {t.STEALTH_BURST_TO_FUSION: 2}})
c.eq("KNOWN LIMITATION: asking on both lines reaches 3 fusion blasters, "
     "against a printed cap of 2",
     len([m for m in _greedy.models if "Fusion Blaster" in weapons(m)]), 3)
c.eq("...but the roster asks on one line only, so it takes exactly one",
     len([m for m in ROSTER if "Stealth" in m.name
          for x in m.models if "Fusion Blaster" in weapons(x)]), 2)   # one per team


# --- 5. the totals, asked of the REAL builder -------------------------------
print("--- 5. totals ---")

built = []
DESTINATIONS = []


def _register(squad, destination=pregame.DEPLOY, transport=None):
    built.append(squad)
    DESTINATIONS.append((squad.name, destination, transport is not None))


army_lists.get("tau").build(OWNER, _register)

c.eq("21 list entries become 19 UNITS after the two attachments", len(built), 19)


def _shape(squad):
    """Datasheet make-up and size, with the copy number normalised away - the
    hand-built roster above has to use different copy numbers, so the two are
    compared on what actually matters."""
    return (re.sub(r"\s\d+(?=\s\+|$)", "", squad.name), len(squad.models))


c.eq("...and the hand-built roster above is the same nineteen units, leader "
     "for leader and model for model",
     sorted(_shape(s) for s in built), sorted(_shape(s) for s in ROSTER))
c.eq("94 models - attaching moves models between units, it does not add or "
     "remove any",
     sum(len(s.models) for s in built),
     # 2 Breacher teams of 11, 2 Devilfish, 3 Broadsides, 2x10 Kroot, 5 hounds,
     # 2x10 Pathfinders, 2 Piranhas, 1 Riptide, 2x5 Stealth, 5 Vespid,
     # Shadowsun, the Ethereal and the Twin Lance's two models.
     (11 + 11) + 2 + 3 + 20 + 5 + 20 + 2 + 1 + 10 + 5 + 1 + 1 + 2)
c.eq("the engine totals 2030 pts", sum(s.points for s in built),
     140 + 140 + 75 + 75 + 270 + 65 + 65 + 45 + 85 + 85 + 65 + 65
     + 215 + 100 + 100 + 70 + 100 + 50 + 220)

# Engine value against the list's own, entry by entry (21 entries, not 19 -
# an attachment merges two priced entries into one unit).
PRICES = [
    (50, 50), (50, 50),       # Cadre Fireblade x2
    (100, 100),               # Commander Shadowsun
    (50, 50),                 # Ethereal
    (220, 185),               # The Twin Lance
    (90, 90), (90, 90),       # Breacher Team x2
    (270, 270),               # Broadside Battlesuits
    (75, 85), (75, 85),       # Devilfish x2
    (65, 65), (65, 65),       # Kroot Carnivores x2
    (45, 40),                 # Kroot Hounds
    (85, 90), (85, 90),       # Pathfinder Team x2
    (65, 60), (65, 60),       # Piranhas x2
    (215, 200),               # Riptide Battlesuit
    (100, 100), (100, 100),   # Stealth Battlesuits x2
    (70, 65),                 # Vespid Stingwings
]
c.eq("twenty-one entries are priced", len(PRICES), 21)
c.eq("TEN of them disagree with the list",
     len([1 for engine, listed in PRICES if engine != listed]), 10)
c.eq("...and eleven agree exactly",
     len([1 for engine, listed in PRICES if engine == listed]), 11)
c.true("...and the differences run in BOTH directions, as they do for the "
       "Necron and Aeldari lists",
       any(e > l for e, l in PRICES) and any(e < l for e, l in PRICES))
c.eq("the engine sum and the entry table agree",
     sum(e for e, _ in PRICES), sum(s.points for s in built))
c.eq("...against the list's own 1990", sum(l for _, l in PRICES), 1990)
c.true("every unit is priced - an unpriced one would rank as free",
       all(s.points is not None for s in built))

c.true("every name carries the owner's digit - the name is an identifier",
       all(s.name.startswith("1 ") for s in built))
c.eq("no name is used twice", len({s.name for s in built}), len(built))


# --- 6. detachments, Enhancements and formations ---------------------------
print("--- 6. detachments and formations ---")

c.eq("the list declares Kauyon + Advanced Acquisition Cadre",
     list(army_lists.get("tau").detachments),
     ["Kauyon", "Advanced Acquisition Cadre"])
c.eq("...costing 2 + 1 Detachment Points", detachments.points_for("tau"), 3)
c.eq("...exactly the budget", detachments.DETACHMENT_POINT_BUDGET, 3)
c.eq("...and the pair is legal - different tags, inside the budget",
     detachments.validate("tau"), [])
c.eq("it is the only list here fielding more than one",
     [k for k in ("aeldari", "orks", "necrons", "tau", "death_guard")
      if len(army_lists.get(k).detachments) > 1], ["tau"])

# NO ENHANCEMENT: the supplied list names none. Pinned from both sides so
# adding one back is a visible change rather than a silent points drift.
c.eq("the list buys no Enhancement",
     sorted(n for s in built for n in enhancements.granted_names(s)), [])
c.eq("...because the table it would come from is empty",
     army_lists._TAU_LIST_ENHANCEMENTS, {})
# Counted per FACTION, not over the whole registry: that count was the same
# number while every Enhancement was a T'au one, and stopped being so when the
# 28 Aeldari ones were registered.
c.true("...while all nineteen T'au Enhancements are still registered and wired",
       len([s for s in enhancements.ENHANCEMENTS.values()
            if s.setting.endswith("_PLAYERS")
            and s.detachment in {d.name for d in t.TAU_EMPIRE.detachments.values()}]) == 19)

# Two attachments, and everything else with CHARACTER stands alone.
_merged = [s for s in built if getattr(s, "attached_components", None)]
c.eq("exactly two units are attached units", len(_merged), 2)
c.eq("...both of them a Breacher Team led by a Cadre Fireblade",
     sorted(sorted(comp.datasheet.name for comp in s.attached_components)
            for s in _merged),
     [["Breacher Team", "Cadre Fireblade"], ["Breacher Team", "Cadre Fireblade"]])
_alone = sorted(s.name for s in built
                if not getattr(s, "attached_components", None)
                and any(m.profile.character for m in s.models))
c.eq("three character units stand alone", _alone,
     ["1 Commander Shadowsun 1", "1 Ethereal 1", "1 The Twin Lance 1"])

# The list says nothing about reserves, so nothing is declared into them - a
# change from the old roster, which put the Coldstar and its Starscythes there
# on an explicit instruction.
c.eq("nothing is declared into Strategic Reserves",
     [n for n, d, _ in DESTINATIONS if d == pregame.RESERVES], [])
c.eq("both Breacher units are declared aboard a transport",
     sorted(n for n, d, has_transport in DESTINATIONS if has_transport),
     ["1 Breacher Team 1 + Cadre Fireblade", "1 Breacher Team 2 + Cadre Fireblade"])
c.eq("...as an EMBARK promise, one per Devilfish",
     [d for _n, d, has_transport in DESTINATIONS if has_transport],
     [pregame.EMBARK, pregame.EMBARK])
c.eq("...and every other unit simply deploys",
     sorted({d for _n, d, _t in DESTINATIONS}), sorted({pregame.DEPLOY, pregame.EMBARK}))


# --- 7. what left the list is still built -----------------------------------
print("--- 7. not fielded is not unimplemented ---")

# Five datasheets left in this revision. "Not fielded" is not "not
# implemented" - each is still a datasheet, still tested by its own suite.
for sheet in (t.GHOSTKEEL_BATTLESUIT, t.STRIKE_TEAM, t.CRISIS_STARSCYTHE,
              t.CRISIS_SUNFORGE, t.COMMANDER_IN_COLDSTAR_BATTLESUIT,
              t.COMMANDER_FARSIGHT):
    c.true(f"{sheet.name} is still a datasheet", bool(sheet.name))
c.eq("...but none of them is on the table any more",
     [s.name for s in built
      if any(k in s.name for k in ("Ghostkeel", "Strike Team", "Crisis",
                                   "Coldstar", "Farsight"))], [])

# No shipped map takes a slice of this list any more - the 30"x30" test board
# that named four units by EXACT name (and would have silently fielded nothing
# after a rename) has been replaced by a full 60"x44" one. What holds now is
# that every map fields the list whole, which is the state in which a rename
# cannot cost a unit at all.
from game import maps
_built_names = {s.name for s in built}
for _key in ("map1", "map2", "map3"):
    _armies = {"Player 1": "tau", "Player 2": "orks"}
    _fielded = [s.name for s in built if maps.get(_key).fields(s, _armies)]
    c.eq(f"{_key} fields the whole T'au list", sorted(set(_built_names) - set(_fielded)), [])

c.finish()
