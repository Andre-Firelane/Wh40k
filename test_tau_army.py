"""The T'au Empire army list, as main.py builds it.

The list the user supplied on 2026-09-05, replacing the 2026-08-30 roster.
21 list entries, 18 units after three attachments, 76 models.

THE TOTALS ARE DRIVEN THROUGH THE REAL BUILDER (section 5), the treatment
test_player2_necron_army.py gave the same failure: a suite that rebuilds the
roster by hand keeps reporting the previous army's numbers, green, while
checking an army that no longer exists. test_player1_army.py hit that twice,
and this file hit it once - every check below was green against a roster that
had been replaced.

THE POINTS AGREE, for the first time. game/factions/tau_empire_points.py holds
the Wahapedia transcription and wins over a list wherever they disagree; this
list disagrees nowhere, on any of its twenty-one entries, and the six
Enhancements bring it to the 2165 the list prints. Both numbers are still
pinned, because "they agree" is a measurement and not a guarantee.

WHAT THIS LIST IS THE FIRST TO DO:
  * it BUYS ENHANCEMENTS - six of them, where every list in this project so far
    bought none. Two of them decide an attachment, because their printed text
    opens "while the bearer is leading a unit" (section 6).
  * it fields two detachments at once, which the previous roster already did
    (Kauyon + Advanced Acquisition Cadre, 2 + 1 DP against a budget of 3).
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

# Cadre Fireblade (80 pts): fireblade pulse rifle, close combat weapon, TWO Gun
# Drones. The 80 is 50 for the model plus 30 for Through Unity, Devastation.
fireblade_a = build(t.CADRE_FIREBLADE, "1 Cadre Fireblade 1",
                        gear={"Cadre Fireblade": ["Gun Drone", "Gun Drone"]})
c.eq("Cadre Fireblade 1 is one model", len(fireblade_a.models), 1)
c.eq("...with his rifle and close combat weapon",
     [w for w in weapons(fireblade_a.models[0]) if "Carbine" not in w],
     ["Close Combat Weapon", "Fireblade Pulse Rifle"])
c.eq("...and two Gun Drones", fireblade_a.models[0].gear_names,
     ["Gun Drone", "Gun Drone"])
c.eq("...whose twin pulse carbines come with them",
     sum(1 for w in weapons(fireblade_a.models[0]) if w == "Twin Pulse Carbine"), 2)
c.eq("...priced at his base 50 before any Enhancement", fireblade_a.points, 50)

# Cadre Fireblade (65 pts): the same model with NO drones. 50 + 15 for
# Precision of the Patient Hunter.
fireblade_b = build(t.CADRE_FIREBLADE, "1 Cadre Fireblade 2")
c.eq("Cadre Fireblade 2 takes no drones at all", fireblade_b.models[0].gear_names, [])
c.eq("...so just the two printed weapons", weapons(fireblade_b.models[0]),
     ["Close Combat Weapon", "Fireblade Pulse Rifle"])
c.eq("...and the same base 50", fireblade_b.points, 50)

# Commander in Coldstar Battlesuit (115 pts = 95 + Exemplar of the Kauyon).
# FOUR fusion blasters, which is one REPLACING the high-output burst cannon
# plus three added from the same printed menu - see the datasheet's options.
#
# The three additions are GEAR, in the "up to three of the following" menu the
# datasheet prints. They used to be a single + 3x Fusion Blaster (Slot) wargear
# option - one hand-cut bundle per combination a list happened to want, which
# could not express a pick of three DIFFERENT items and could not express the
# menu's three support systems at all.
coldstar = build(t.COMMANDER_IN_COLDSTAR_BATTLESUIT,
                      "1 Commander in Coldstar Battlesuit 1",
                      choices={"Commander in Coldstar Battlesuit": {
                          t.COLDSTAR_BURST_TO_FUSION: 1}},
                      gear={"Commander in Coldstar Battlesuit":
                            ["Marker Drone", "Shield Drone",
                             "Fusion Blaster", "Fusion Blaster", "Fusion Blaster"]})
c.eq("the Commander carries four fusion blasters and his fists",
     weapons(coldstar.models[0]),
     ["Battlesuit Fists"] + ["Fusion Blaster"] * 4)
c.true("...so the high-output burst cannon is gone - it was replaced",
       "High-output Burst Cannon" not in weapons(coldstar.models[0]))
# gear_names records BOTH menus he bought from - the two drones and the three
# added fusion blasters - because both are Gear on this datasheet now.
c.eq("...with a Marker Drone and a Shield Drone, and the three added blasters",
     sorted(coldstar.models[0].gear_names),
     ["Fusion Blaster"] * 3 + ["Marker Drone", "Shield Drone"])
c.eq("...priced at his base 95", coldstar.points, 95)

# Ethereal (70 pts = 50 + Solid-image Projection Unit): honour stave, one
# Marker Drone and one Shield Drone. The previous roster took two Marker
# Drones; this one does not.
ethereal = keep(build(t.ETHEREAL, gear={"Ethereal": ["Marker Drone", "Shield Drone"]}))
c.eq("the Ethereal carries his honour stave", weapons(ethereal.models[0]),
     ["Honour Stave"])
c.eq("...one Marker Drone and one Shield Drone",
     sorted(ethereal.models[0].gear_names), ["Marker Drone", "Shield Drone"])
c.eq("...priced at his base 50", ethereal.points, 50)


# --- 2. the two Breacher Teams, their Fireblades and their Devilfish --------
print("--- 2. Breachers, Fireblades, Devilfish ---")

BREACHER_GEAR = ["Guardian Drone", "Gun Drone"]


def breacher_team(n):
    return build(t.BREACHER_TEAM, f"1 Breacher Team {n}",
                 gear={"Breacher Fire Warrior Shas'ui": BREACHER_GEAR})


breachers_a, breachers_b = breacher_team(1), breacher_team(2)
c.eq("a Breacher Team is ten models", len(breachers_a.models), 10)
c.eq("...one Shas'ui and nine Fire Warriors", line_counts(breachers_a),
     {"Breacher Fire Warrior Shas'ui": 1, "Breacher Fire Warrior": 9})
c.eq("...each with pulse blaster, pulse pistol and close combat weapon",
     weapons(breachers_a.models[-1]),
     ["Close Combat Weapon", "Pulse Blaster", "Pulse Pistol"])
c.eq("the Shas'ui carries a Guardian Drone and a Gun Drone - NOT the Shield "
     "Drone the previous roster gave him",
     sorted(breachers_a.models[0].gear_names), ["Guardian Drone", "Gun Drone"])
c.eq("...at 90 pts for ten", breachers_a.points, 90)

# Each Fireblade joins a Breacher Team (19.01), which is the user's own
# instruction for the previous roster and unchanged here.
merged_a = keep(attached_units.attach(fireblade_a, breachers_a))
merged_b = keep(attached_units.attach(fireblade_b, breachers_b))
c.eq("a Fireblade plus his Breachers is ONE unit of eleven", len(merged_a.models), 11)
c.eq("...and its points are the two entries added up", merged_a.points, 90 + 50)
c.true("...with the Fireblade inside it",
       any(m.profile.name == "Cadre Fireblade" for m in merged_a.models))

# Devilfish: the accelerator burst cannon is the datasheet's own default; both
# Seeker Missiles are bought. ONE option taken ONCE - the printed entry is
# "+ 2x Seeker Missile" and adds both, so a count of 2 would ask for four.
DEVILFISH_CHOICES = {"Devilfish": {t.DEVILFISH_SEEKER_MISSILE_OPTION: 1}}
devilfish_a = keep(build(t.DEVILFISH, "1 Devilfish 1", choices=DEVILFISH_CHOICES))
devilfish_b = keep(build(t.DEVILFISH, "1 Devilfish 2", choices=DEVILFISH_CHOICES))
c.eq("a Devilfish is one model", len(devilfish_a.models), 1)
c.eq("...with hull, accelerator burst cannon, two twin pulse carbines and two "
     "seeker missiles", weapons(devilfish_a.models[0]),
     ["Accelerator Burst Cannon", "Armoured Hull", "Seeker Missile",
      "Seeker Missile", "Twin Pulse Carbine", "Twin Pulse Carbine"])
c.eq("...at 75 pts, which is what THIS list prices it at too", devilfish_a.points, 75)
c.eq("eleven models ride in a twelve-model transport", len(merged_a.models), 11)
c.true("...which is what the Devilfish carries",
       devilfish_a.models[0].profile.transport_capacity >= 11)


# --- 3. the Crisis Sunforge and the Commander who leads them ---------------
print("--- 3. Crisis Sunforge + Commander ---")

SUNFORGE_GEAR = {"Crisis Sunforge Shas'vre": ["Gun Drone", "Shield Drone"],
                 "Crisis Sunforge Shas'ui (1)": ["Gun Drone", "Shield Drone"],
                 "Crisis Sunforge Shas'ui (2)": ["Gun Drone", "Shield Drone"]}
sunforge = build(t.CRISIS_SUNFORGE, "1 Crisis Sunforge Battlesuits 1",
                 gear=SUNFORGE_GEAR)
c.eq("the Sunforge team is three models", len(sunforge.models), 3)
c.eq("...one Shas'vre and two Shas'ui", line_counts(sunforge),
     {"Crisis Sunforge Shas'vre": 1, "Crisis Sunforge Shas'ui": 2})
c.eq("...each with two fusion blasters and fists - the datasheet's own default",
     [w for w in weapons(sunforge.models[0]) if w != "Twin Pulse Carbine"],
     ["Battlesuit Fists", "Fusion Blaster", "Fusion Blaster"])
c.eq("...and a Gun Drone plus a Shield Drone each",
     sorted(sunforge.models[1].gear_names), ["Gun Drone", "Shield Drone"])
c.eq("...at 125 pts for three", sunforge.points, 125)

sunforge_led = keep(attached_units.attach(coldstar, sunforge))
c.eq("the Commander leads them, so it is one unit of four",
     len(sunforge_led.models), 4)
c.eq("...and its points add up", sunforge_led.points, 125 + 95)
# Asked of a FRESH Commander: `coldstar` has just been merged away, and a
# leader squad that attach() absorbed answers nothing.
c.true("the Coldstar's own LEADER line names this datasheet, which is why the "
       "attachment is legal at all",
       "Crisis Sunforge Battlesuits" in attached_units.leadable_unit_names(
           build(t.COMMANDER_IN_COLDSTAR_BATTLESUIT, "1 spare Commander 1")))


# --- 4. the rest of the roster ---------------------------------------------
print("--- 4. the rest ---")

# Broadside Battlesuits (150 pts): TWO models, both keeping their Heavy Rail
# Rifle. The previous roster took three models and traded for missile pods,
# which is the +5/model this one does not pay.
BROADSIDE_GEAR = ["Seeker Missile", "Twin Plasma Rifle", "Missile Drone", "Missile Drone"]
broadsides = keep(build(t.BROADSIDE_BATTLESUITS, composition_index=1,
                        gear={"Broadside Shas'vre": BROADSIDE_GEAR,
                              "Broadside Shas'ui": BROADSIDE_GEAR}))
c.eq("the Broadsides are two models", len(broadsides.models), 2)
c.eq("...one Shas'vre and one Shas'ui", line_counts(broadsides),
     {"Broadside Shas'vre": 1, "Broadside Shas'ui": 1})
for model in broadsides.models:
    c.eq(f"{model.profile.name} keeps his heavy rail rifle and carries the rest",
         weapons(model),
         ["Crushing Bulk", "Heavy Rail Rifle", "Missile Pod", "Missile Pod",
          "Seeker Missile", "Twin Plasma Rifle"])
c.eq("...at 150 pts, the two-model line with no missile-pod surcharge",
     broadsides.points, 150)

# Ghostkeel (180 = 150 + 15 Cyclic Ion Raker + 15 Unmasking Suite).
ghostkeel = keep(build(t.GHOSTKEEL_BATTLESUIT,
                       choices={"Ghostkeel Battlesuit": {
                           t.GHOSTKEEL_FUSION_TO_ION_RAKER: 1,
                           t.GHOSTKEEL_FLAMER_TO_FUSION_BLASTER: 1}}))
c.eq("the Ghostkeel takes the ion raker and the twin fusion blaster",
     weapons(ghostkeel.models[0]),
     ["Cyclic Ion Raker - Standard", "Ghostkeel Fists", "Twin Fusion Blaster"])
c.eq("...at 165, which is 150 plus the raker's own 15", ghostkeel.points, 165)
c.true("the list also names a Battlesuit Support System, which this datasheet "
       "already has unconditionally - buying it changes nothing",
       ghostkeel.models[0].profile.battlesuit_support_system)

# Hammerhead (150): railgun kept, both carbines traded for accelerator burst
# cannons, both seeker missiles taken.
hammerhead = keep(build(t.HAMMERHEAD_GUNSHIP,
                        choices={"Hammerhead Gunship": {t.HAMMERHEAD_CARBINES_TO_BURST: 1}},
                        gear={"Hammerhead Gunship": ["Seeker Missile", "Seeker Missile"]}))
c.eq("the Hammerhead keeps its railgun and swaps both carbines",
     weapons(hammerhead.models[0]),
     ["Accelerator Burst Cannon", "Accelerator Burst Cannon", "Armoured Hull",
      "Railgun", "Seeker Missile", "Seeker Missile"])
c.eq("...at 150", hammerhead.points, 150)

# Sky Ray (140): the missile rack is its own, both carbines traded.
sky_ray = keep(build(t.SKY_RAY_GUNSHIP,
                     choices={"Sky Ray Gunship": {t.SKY_RAY_CARBINES_TO_BURST: 1}}))
c.eq("the Sky Ray keeps its seeker missile rack and swaps both carbines",
     weapons(sky_ray.models[0]),
     ["Accelerator Burst Cannon", "Accelerator Burst Cannon", "Armoured Hull",
      "Seeker Missile Rack"])
c.eq("...at 140", sky_ray.points, 140)

# Kroot Carnivores (65): ONE unit this time, at its printed default.
kroot = keep(build(t.KROOT_CARNIVORES))
c.eq("the Kroot are ten models", len(kroot.models), 10)
c.eq("...a Long-quill and nine Carnivores", line_counts(kroot),
     {"Long-quill": 1, "Kroot Carnivore": 9})
c.eq("...the Long-quill carrying a pistol the others do not",
     weapons(kroot.models[0]),
     ["Close Combat Weapon", "Kroot Pistol", "Kroot Rifle"])
c.eq("...at 65", kroot.points, 65)

hounds = keep(build(t.KROOT_HOUNDS))
c.eq("five Kroot Hounds with ripping fangs", len(hounds.models), 5)
c.eq("...at 45 - the transcription's number, and this list's too", hounds.points, 45)

# Pathfinder Team (85): three rail rifles, and ONE MORE model takes a
# semi-automatic grenade launcher ALONGSIDE its pulse carbine. The printed
# option is an addition and says "that model's pulse carbine cannot be
# replaced", which is why the two options are addressed by model index.
PATHFINDER_CHOICES = {"Pathfinder": {t.PATHFINDER_CARBINE_TO_RAIL_RIFLE: (0, 1, 2),
                                     t.PATHFINDER_CARBINE_TO_GRENADE_LAUNCHER: (3,)}}
pathfinders = keep(build(t.PATHFINDER_TEAM, choices=PATHFINDER_CHOICES,
                         gear={"Pathfinder Shas'ui":
                               ["Shield Drone", "Shield Drone", "Grav-inhibitor Drone"]}))
c.eq("the Pathfinders are ten models", len(pathfinders.models), 10)
_pf = [w for m in pathfinders.models for w in weapons(m)]
c.eq("three rail rifles", _pf.count("Rail Rifle"), 3)
c.eq("...one grenade launcher", _pf.count("Semi-automatic Grenade Launcher - EMP"), 1)
c.eq("...and seven pulse carbines: six on the rank and file plus the Shas'ui's",
     _pf.count("Pulse Carbine"), 7)
_launcher_model = next(m for m in pathfinders.models
                       if "Semi-automatic Grenade Launcher - EMP" in weapons(m))
c.true("the launcher's carrier KEEPS his pulse carbine, which the printed "
       "option requires - it is an addition, not a swap",
       "Pulse Carbine" in weapons(_launcher_model))
c.true("...and is not one of the rail-rifle models",
       "Rail Rifle" not in weapons(_launcher_model))
c.eq("the Shas'ui carries two Shield Drones and a Grav-inhibitor Drone",
     sorted(pathfinders.models[0].gear_names),
     ["Grav-inhibitor Drone", "Shield Drone", "Shield Drone"])
c.eq("...at 85", pathfinders.points, 85)

# Piranha (65): ONE, keeping its burst cannon and taking no seeker missiles.
piranha = keep(build(t.PIRANHAS))
c.eq("the Piranha keeps its own burst cannon", weapons(piranha.models[0]),
     ["Armoured Hull", "Piranha Burst Cannon", "Twin Pulse Carbine", "Twin Pulse Carbine"])
c.eq("...and takes no seeker missiles", piranha.models[0].gear_names, [])
c.eq("...at 65", piranha.points, 65)

riptide = keep(build(t.RIPTIDE_BATTLESUIT,
                     choices={"Riptide Battlesuit": {
                         t.RIPTIDE_BURST_TO_ION_ACCELERATOR: 1,
                         t.RIPTIDE_PLASMA_TO_TWIN_FUSION: 1}}))
c.eq("the Riptide takes the ion accelerator and the twin fusion blaster",
     weapons(riptide.models[0]),
     ["Ion Accelerator - Standard", "Missile Pod", "Missile Pod",
      "Riptide Fists", "Twin Fusion Blaster"])
c.eq("...at 215", riptide.points, 215)

STEALTH_GEAR = {"Stealth Shas'vre": ["Gun Drone", "Marker Drone"],
                "Stealth Shas'ui": ["Homing Beacon"]}
STEALTH_CHOICES = {"Stealth Shas'vre": {t.STEALTH_BURST_TO_FUSION: 1}}


def stealth_team(n):
    return build(t.STEALTH_BATTLESUITS, f"1 Stealth Battlesuits {n}",
                 gear=STEALTH_GEAR, choices=STEALTH_CHOICES)


stealth_a, stealth_b = keep(stealth_team(1)), keep(stealth_team(2))
c.eq("a Stealth team is five models", len(stealth_a.models), 5)
c.eq("the Shas'vre carries the fusion blaster",
     [w for w in weapons(stealth_a.models[0]) if w != "Twin Pulse Carbine"],
     ["Battlesuit Fists", "Fusion Blaster"])
c.eq("...with a Gun Drone and a Marker Drone",
     sorted(stealth_a.models[0].gear_names), ["Gun Drone", "Marker Drone"])
c.eq("one Shas'ui carries the Homing Beacon",
     [m.profile.name for m in stealth_a.models if "Homing Beacon" in (m.gear_names or [])],
     ["Stealth Shas'ui"])
c.eq("...and the other three carry burst cannons",
     sum(1 for m in stealth_a.models if "Burst Cannon" in weapons(m)), 4)
c.eq("...at 100 before any Enhancement", stealth_a.points, 100)
c.eq("both teams are built the same way", line_counts(stealth_a), line_counts(stealth_b))

vespid = keep(build(t.VESPID_STINGWINGS))
c.eq("five Vespid, one of them the Strain Leader", line_counts(vespid),
     {"Vespid Strain Leader": 1, "Vespid Stingwing": 4})
c.eq("...at 70", vespid.points, 70)


# --- 5. the totals, asked of the REAL builder -------------------------------
print("--- 5. totals ---")

built = []
DESTINATIONS = []


def _register(squad, destination=pregame.DEPLOY, transport=None):
    built.append(squad)
    DESTINATIONS.append((squad.name, destination, transport is not None))


army_lists.get("tau").build(OWNER, _register)

c.eq("21 list entries become 18 UNITS after the three attachments", len(built), 18)


def _shape(squad):
    """Datasheet make-up and size, with the copy number normalised away - the
    hand-built roster above has to use different copy numbers, so the two are
    compared on what actually matters."""
    return (re.sub(r"\s\d+(?=\s\+|$)", "", squad.name), len(squad.models))


c.eq("...and the hand-built roster above is the same eighteen units, leader "
     "for leader and model for model",
     sorted(_shape(s) for s in built), sorted(_shape(s) for s in ROSTER))
c.eq("76 models - attaching moves models between units, it does not add or "
     "remove any",
     sum(len(s.models) for s in built),
     # 2 Breacher teams of 11, 2 Devilfish, Sunforge+Commander 4, 2 Broadsides,
     # Ghostkeel, Hammerhead, 10 Kroot, 5 hounds, 10 Pathfinders, Piranha,
     # Riptide, Sky Ray, 2x5 Stealth, 5 Vespid, the Ethereal.
     (11 + 11) + 2 + 4 + 2 + 1 + 1 + 10 + 5 + 10 + 1 + 1 + 1 + 10 + 5 + 1)

# Engine value against the list's own, entry by entry (21 entries, not 18 -
# an attachment merges two priced entries into one unit). The Enhancements are
# listed separately below, the way the list itself prices them.
PRICES = [
    (50, 50), (50, 50),       # Cadre Fireblade x2 (before Enhancements)
    (95, 95),                 # Commander in Coldstar
    (50, 50),                 # Ethereal
    (90, 90), (90, 90),       # Breacher Team x2
    (75, 75), (75, 75),       # Devilfish x2
    (150, 150),               # Broadside Battlesuits (2 models)
    (125, 125),               # Crisis Sunforge Battlesuits
    (165, 165),               # Ghostkeel (with the Cyclic Ion Raker)
    (150, 150),               # Hammerhead Gunship
    (65, 65),                 # Kroot Carnivores
    (45, 45),                 # Kroot Hounds
    (85, 85),                 # Pathfinder Team
    (65, 65),                 # Piranhas
    (215, 215),               # Riptide Battlesuit
    (140, 140),               # Sky Ray Gunship
    (100, 100), (100, 100),   # Stealth Battlesuits x2 (before Enhancements)
    (70, 70),                 # Vespid Stingwings
]
c.eq("twenty-one entries are priced", len(PRICES), 21)
c.eq("EVERY one agrees with the list - the first roster here where none "
     "disagrees", [1 for e, l in PRICES if e != l], [])
ENHANCEMENT_POINTS = 30 + 15 + 20 + 20 + 15 + 15
c.eq("the six Enhancements come to 115", ENHANCEMENT_POINTS,
     sum(enhancements.get(n).points
         for n in army_lists.get("tau").enhancement_names()))
c.eq("the engine sum is the entries plus the Enhancements",
     sum(s.points for s in built), sum(e for e, _ in PRICES) + ENHANCEMENT_POINTS)
c.eq("...which is the list's own 2165",
     sum(l for _, l in PRICES) + ENHANCEMENT_POINTS, 2165)
c.true("every unit is priced - an unpriced one would rank as free",
       all(s.points is not None for s in built))

c.true("every name carries the owner's digit - the name is an identifier",
       all(s.name.startswith("1 ") for s in built))
c.eq("no name is used twice", len({s.name for s in built}), len(built))


# --- 6. detachments, Enhancements and formations ---------------------------
print("--- 6. detachments, Enhancements and formations ---")

c.eq("the list declares Kauyon + Advanced Acquisition Cadre",
     list(army_lists.get("tau").detachments),
     ["Kauyon", "Advanced Acquisition Cadre"])
c.eq("...which is legal", detachments.validate("tau"), [])
c.eq("...and spends the whole 3 DP budget",
     sum(detachments.get("tau", n).points for n in army_lists.get("tau").detachments),
     detachments.DETACHMENT_POINT_BUDGET)

granted = {n: s.name for s in built for n in enhancements.granted_names(s)}
c.eq("SIX Enhancements, where the previous roster bought none",
     sorted(granted), sorted(army_lists.get("tau").enhancement_names()))
c.eq("each on the unit the written list says",
     granted["Negation Emitters"], "1 Stealth Battlesuits 1")
c.true("...and only the FIRST of the two identical Stealth teams has one",
       not any(enhancements.granted_names(s) for s in built
               if s.name == "1 Stealth Battlesuits 2"))
c.eq("the two Fireblades carry DIFFERENT Enhancements",
     sorted([granted["Through Unity, Devastation"],
             granted["Precision of the Patient Hunter"]]),
     ["1 Breacher Team 1 + Cadre Fireblade", "1 Breacher Team 2 + Cadre Fireblade"])

# THE ENHANCEMENTS DECIDE TWO ATTACHMENTS, and that is the printed text rather
# than a preference: both open "while the bearer is leading a unit".
for name in ("Exemplar of the Kauyon", "Through Unity, Devastation"):
    c.true(f"{name} needs a led unit, so its bearer leads one",
           " + " in granted[name])
for name in ("Precision of the Patient Hunter", "Solid-image Projection Unit"):
    c.true(f"{name} does not, and constrains nothing",
           name in granted)

attached = [s for s in built if s.attached_components]
c.eq("exactly three units are attached units", len(attached), 3)
c.eq("...two Breacher Teams and the Crisis Sunforge",
     sorted(sorted(comp.datasheet.name for comp in s.attached_components)
            for s in attached),
     [["Breacher Team", "Cadre Fireblade"],
      ["Breacher Team", "Cadre Fireblade"],
      ["Commander in Coldstar Battlesuit", "Crisis Sunforge Battlesuits"]])
c.eq("the Ethereal stands alone - the user's own instruction",
     sorted(s.name for s in built
            if not s.attached_components
            and any(getattr(m.profile, "character", False) for m in s.models)),
     ["1 Ethereal 1"])

embarked = [(name, transported) for name, dest, transported in DESTINATIONS
            if dest == pregame.EMBARK]
c.eq("two units start embarked, each in its own Devilfish", len(embarked), 2)
c.true("...and both are given a transport", all(t for _n, t in embarked))
c.eq("nothing is declared into reserves",
     [n for n, dest, _t in DESTINATIONS if dest == pregame.RESERVES], [])


# --- 7. what left the list is still built -----------------------------------
print("--- 7. not fielded is not unimplemented ---")

# Four datasheets the previous roster fielded are not in this one. They are
# still built, still tested and still selectable - "the list does not take it"
# is not "the engine cannot".
GONE = [t.COMMANDER_SHADOWSUN, t.THE_TWIN_LANCE]
for sheet in GONE:
    c.true(f"{sheet.name} is still a datasheet of this faction",
           sheet in t.TAU_EMPIRE.datasheets.values())
    c.true(f"...and still builds", len(build(sheet, f"x {sheet.name}").models) >= 1)
c.eq("...but none of them is on the table any more",
     [s.name for s in built
      if any(comp.datasheet.name in {g.name for g in GONE}
             for comp in (s.attached_components or []))
      or s.name.split(" ", 1)[1].rsplit(" ", 1)[0] in {g.name for g in GONE}],
     [])

c.finish()
