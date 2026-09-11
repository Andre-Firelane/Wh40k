"""The three Necron VEHICLEs of stage 8: Catacomb Command Barge, Annihilation
Barge, Ghost Ark.

WHAT EACH SECTION IS FOR
  1. statlines, the SET the three agree on, and the table-size decision
  2. weapons - the four SHARED classes and the two per-weapon skill overrides
  3. points, wargear options, and the CHARACTER that leads nothing
  4. Advanced Quantum Shielding, in BOTH phases, against its two siblings
  5. Carrier Wave, through the real objective control reader
  6. Malevolent Arcing, end to end through the real ShootingController
  7. Repair Barge - the DELTA trigger, both phases, and its two ledgers
  8. the Ghost Ark's transport pools, at BOTH readers (18.01 and 18.02)
  9. the extractions, with their OTHER carriers still answering identically
 10. wiring, AI negative space, sprites, roster dormancy

THE RULE THIS FOLLOWS, as every Necron stage suite before it: each ability is
measured at its CONSUMING end - the threshold the wound step computes, the
number Objective Control resolves to, the wounds that actually land - and never
only at its own predicate. A flag that is set and never read is exactly the
failure a predicate test cannot see.
"""

import ast
import io
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

pygame.init()
pygame.display.set_mode((100, 100))

import testkit as tk
from testkit import Checks, script

from game import (attached_units, awakened_dynasty, carrier_wave, formations,
                  guardian_protocols, malevolent_arcing, objective_control,
                  reanimation_protocols, repair_barge, sprites,
                  strength_over_toughness as sot, transport as transport_mod,
                  wave_serpent_shield)
from game.decision import DecisionManager
from game.dice import DiceManager
from game.factions import aeldari as ael
from game.factions import necrons as nec
from game.factions import orks as ork
from game.factions.necrons_points import NECRONS_POINTS
from game.game_state import GameState
from game.malevolent_arcing import MalevolentArcingController
from game.repair_barge import RepairBargeController
from game.resurrection_orb import (RangedResurrectionOrbController,
                                   ResurrectionOrbController)
from game.units import (AnnihilationBargeProfile, CatacombCommandBargeProfile,
                        DoomsdayArkProfile, GhostArkProfile, UnitProfile)
from game.weapons import (ArmouredBulkProfile, CatacombCommandBargeStaffOfLightMeleeProfile,
                          CatacombCommandBargeStaffOfLightRangedProfile,
                          GaussCannonProfile, GaussFlayerArrayProfile,
                          LordStaffOfLightMeleeProfile,
                          LordStaffOfLightRangedProfile, OverlordsBladeProfile,
                          TeslaCannonProfile, TwinTeslaDestructorProfile)

c = Checks("Necron VEHICLES")

D = nec.NECRONS.datasheets
CCB = D["Catacomb Command Barge"]
ANNI = D["Annihilation Barge"]
ARK = D["Ghost Ark"]
WARRIORS = D["Necron Warriors"]
IMMORTALS = D["Immortals"]
LYCHGUARD = D["Lychguard"]
OVERLORD = D["Overlord"]
TECHNOMANCER = D["Technomancer"]

NEW = [CCB, ANNI, ARK]
PROFILES = {
    "Catacomb Command Barge": CatacombCommandBargeProfile,
    "Annihilation Barge": AnnihilationBargeProfile,
    "Ghost Ark": GhostArkProfile,
}


def build(sheet, owner="Player 2", n=1, **kw):
    """Named the way main.py names squads - see the substring trap in
    game/sprites.py's _key_for_name()."""
    return tk.build(sheet, owner, name="%s %s %d" % (owner[-1], sheet.name, n), **kw)


def place(squad, x, y, spacing=1.4):
    for i, m in enumerate(squad.models):
        m.x_in, m.y_in = x + i * spacing, y
    return squad


def cluster(squad, x, y, step=1.0, per_row=5):
    """A tight block, so every model is inside an embark reach. line_up()'s
    single row puts a ten-model unit 9" wide, which fails 18.02's 3" for the
    far half and would make a pool test measure the FORMATION."""
    for i, m in enumerate(squad.models):
        m.x_in = x + (i % per_row) * step - (per_row - 1) * step / 2.0
        m.y_in = y + (i // per_row) * step
    return squad


def corpus(name):
    return io.open(os.path.join("rules", "necrons", name + ".md"),
                   encoding="utf-8").read()


def row(text, weapon_name):
    """The printed table row for a weapon, or "" - find(), never index()."""
    i = text.find("| %s |" % weapon_name)
    if i < 0:
        return ""
    j = text.find("\n", i)
    return text[i:j if j > 0 else len(text)]


def weapon_names(squad):
    return sorted(w.name for w in squad.models[0].weapons)


MAIN = io.open("main.py", encoding="utf-8").read()
MAIN_TREE = ast.parse(MAIN)


def main_statements():
    """Every call in main.py that IS a whole statement - i.e. one that really
    runs when its branch runs. A bare substring, and even a Call node, survives
    `False and <call>` and `if False:` alike."""
    out = []
    for node in ast.walk(MAIN_TREE):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            out.append(ast.get_source_segment(MAIN, node.value) or "")
    return out


MAIN_STATEMENTS = main_statements()


def main_runs(fragment):
    return any(fragment in s for s in MAIN_STATEMENTS)


# --- 1. statlines -----------------------------------------------------------
print("--- 1. statlines ---")

STATS = {
    # M    T   Sv    W   Ld   OC
    "Catacomb Command Barge": (10, 8, "3+", 9, "6+", 3),
    "Annihilation Barge": (10, 8, "3+", 9, "7+", 3),
    "Ghost Ark": (10, 9, "3+", 14, "7+", 3),
}
for name, (m, t, sv, w, ld, oc) in sorted(STATS.items()):
    p = PROFILES[name]
    c.eq("%s statline" % name,
         (p.movement_in, p.toughness, p.armor_save, p.wounds, p.leadership, p.oc),
         (m, t, sv, w, ld, oc))
    # ...and the printed page says the same thing, so the numbers above are a
    # transcription rather than a second opinion.
    c.true("...and the corpus prints that row",
           '| %d" | %d | %s | %d | %s | %d |' % (m, t, sv, w, ld, oc) in corpus(name))

for name in sorted(PROFILES):
    p = PROFILES[name]
    c.eq("%s has a 4+ invulnerable" % name, p.invulnerable_save, "4+")
    c.true("...and is a VEHICLE that FLIES", p.vehicle and p.fly)
    c.true("...and carries the army rule", p.reanimation_protocols)
    c.true("...and derives DIRECTLY from UnitProfile - no shared chassis, "
           "unlike the four C'tan", p.__bases__ == (UnitProfile,))

# The SET, not three separate facts: what the three agree on and what exactly
# one of them has. Written this way so a fourth skimmer cannot slip in without
# declaring which side of each line it is on.
c.eq("exactly one of the three is a CHARACTER",
     sorted(n for n in PROFILES if getattr(PROFILES[n], "character", False)),
     ["Catacomb Command Barge"])
c.eq("exactly one is a TRANSPORT",
     sorted(n for n in PROFILES if getattr(PROFILES[n], "transport", False)),
     ["Ghost Ark"])
c.eq("exactly two print Deadly Demise 1 (the Ark prints D3)",
     sorted(n for n in PROFILES
            if PROFILES[n].deadly_demise == 1 and PROFILES[n].deadly_demise_notation is None),
     ["Annihilation Barge", "Catacomb Command Barge"])
c.eq("the Ghost Ark's Deadly Demise is a D3", GhostArkProfile.deadly_demise_notation.sides, 3)
c.eq("none of the three prints a Damaged bracket",
     [n for n in PROFILES if PROFILES[n].damaged_threshold is not None], [])
c.eq("...and the corpus agrees - no Damaged section on any of them",
     [n for n in PROFILES if "## Damaged" in corpus(n)], [])

# THE TABLE SIZE. Pinned as an IDENTITY against the Doomsday Ark so the pin
# carries the REASON ("as big as the other tanks") rather than a bare 2.1.
for name in sorted(PROFILES):
    c.eq("%s is the grav-tank table size, not its printed base" % name,
         PROFILES[name].base_radius_in, DoomsdayArkProfile.base_radius_in)
c.true("...and two of the three really do print 60 mm, so that is a DEVIATION",
       "60mm" in corpus("Catacomb Command Barge") and "60mm" in corpus("Ghost Ark"))
c.true("...while the Annihilation Barge prints no base at all",
       "Use model" in corpus("Annihilation Barge"))

# The Night Scythe is NOT built - the other half of the same decision.
c.true("the Night Scythe is not a registered datasheet",
       "Night Scythe" not in D)
c.true("...but its corpus file is still on disk, like the Doom Scythe's",
       os.path.isfile(os.path.join("rules", "necrons", "Night Scythe.md")))


# --- 2. weapons -------------------------------------------------------------
print("--- 2. weapons ---")

# FOUR SHARED CLASSES. Pinned as IDENTITY (`is`), because a clone with the same
# numbers passes every value comparison.
SHARED = [
    ("Gauss Cannon", GaussCannonProfile, [CCB, ANNI]),
    ("Armoured Bulk", ArmouredBulkProfile, [ANNI, ARK]),
    ("Gauss Flayer Array", GaussFlayerArrayProfile, [ARK]),
]
for label, cls, sheets in SHARED:
    for sheet in sheets:
        got = [w for w in build(sheet).models[0].weapons if w.name == label]
        # type(...) is, NOT isinstance(): a FORK is a subclass, and isinstance
        # waves it straight through - which is what the A/B probe found.
        c.true("%s on the %s is the SHARED %s" % (label, sheet.name, cls.__name__),
               bool(got) and all(type(w) is cls for w in got))
# The Doomsday Ark, already built, is the other end of two of those shares.
ark_old = build(D["Doomsday Ark"])
for label, cls in (("Armoured Bulk", ArmouredBulkProfile),
                   ("Gauss Flayer Array", GaussFlayerArrayProfile)):
    c.true("...and the Doomsday Ark uses the very same %s" % cls.__name__,
           any(isinstance(w, cls) and w.name == label for w in ark_old.models[0].weapons))

blade = build(CCB, choices={"Catacomb Command Barge": {nec.CATACOMB_BARGE_STAFF_TO_BLADE: 1}})
c.true("the Barge's Overlord's blade is the SHARED OverlordsBladeProfile - the "
       "share game/weapons.py's stage-7 block predicted by name",
       any(type(w) is OverlordsBladeProfile for w in blade.models[0].weapons))

# SHARING IS ONLY SAFE BECAUSE SKILL LIVES ON THE PROFILE. Measured per bearer,
# because that is the half a clone would also pass.
from game.shooting import effective_ballistic_skill  # noqa: E402
from game.fight import effective_weapon_skill  # noqa: E402

gauss = GaussCannonProfile()
ccb_model = build(CCB).models[0]
anni_model = build(ANNI).models[0]
c.eq("the shared gauss cannon resolves BS3+ on BOTH Barges",
     (effective_ballistic_skill(ccb_model, gauss),
      effective_ballistic_skill(anni_model, gauss)), ("3+", "3+"))
bulk = ArmouredBulkProfile()
c.eq("the shared armoured bulk resolves WS4+ on all three of its bearers",
     sorted({effective_weapon_skill(anni_model, bulk),
             effective_weapon_skill(build(ARK).models[0], bulk),
             effective_weapon_skill(ark_old.models[0], bulk)}), ["4+"])

# TWO NEW CLASSES.
tesla = TeslaCannonProfile()
c.eq("Tesla Cannon 24\"/A4/S6/AP0/D1 [SUSTAINED HITS 2]",
     (tesla.range_in, tesla.attacks, tesla.strength, tesla.ap, tesla.damage,
      tesla.sustained_hits), (24, 4, 6, 0, 1, 2))
c.true("...and the corpus prints that row",
       "| 24\" | 4 | 3+ | 6 | 0 | 1 | sustained hits 2 |" in row(corpus("Annihilation Barge"), "Tesla cannon"))
dest = TwinTeslaDestructorProfile()
c.eq("Twin Tesla Destructor 36\"/A6/S8/AP0/D2 [SUSTAINED HITS 2, TWIN-LINKED]",
     (dest.range_in, dest.attacks, dest.strength, dest.ap, dest.damage,
      dest.sustained_hits, dest.twin_linked), (36, 6, 8, 0, 2, 2, True))
c.true("...and the corpus prints that row",
       "sustained hits 2, twin-linked" in row(corpus("Annihilation Barge"), "Twin tesla destructor"))

# THE TWO SKILL OVERRIDES, pinned AGAINST THEIR BASES rather than literals: the
# assurance is that each differs in exactly ONE characteristic.
for sub, base, field in (
    (CatacombCommandBargeStaffOfLightRangedProfile, LordStaffOfLightRangedProfile, "ballistic_skill"),
    (CatacombCommandBargeStaffOfLightMeleeProfile, LordStaffOfLightMeleeProfile, "weapon_skill"),
):
    a, b = sub(), base()
    c.true("%s subclasses the Lord's staff" % sub.__name__, issubclass(sub, base))
    c.eq("...same printed name", a.name, b.name)
    c.eq("...same numbers", (a.range_in, a.attacks, a.strength, a.ap, a.damage),
         (b.range_in, b.attacks, b.strength, b.ap, b.damage))
    differing = [f for f in ("ballistic_skill", "weapon_skill")
                 if getattr(a, f) != getattr(b, f)]
    c.eq("...and differs in exactly one characteristic, the %s" % field,
         differing, [field])
c.eq("the Barge's staff fires at BS2+ where its cannons fire at BS3+",
     (effective_ballistic_skill(ccb_model, CatacombCommandBargeStaffOfLightRangedProfile()),
      effective_ballistic_skill(ccb_model, gauss)), ("2+", "3+"))
c.eq("...and its staff swings at WS3+ where the Overlord's blade swings at WS2+",
     (effective_weapon_skill(ccb_model, CatacombCommandBargeStaffOfLightMeleeProfile()),
      effective_weapon_skill(ccb_model, OverlordsBladeProfile())), ("3+", "2+"))
c.true("the printed page really does say BS2+ for the staff and BS3+ for the cannon",
       "| 18\" | 3 | 2+ |" in row(corpus("Catacomb Command Barge"), "Staff of light")
       and "| 24\" | 3 | 3+ |" in row(corpus("Catacomb Command Barge"), "Gauss cannon"))

# ...and those two are the WHOLE of the overrides in this stage.
overridden = sorted(w.name for sheet in NEW for w in build(sheet).models[0].weapons
                    if w.ballistic_skill is not None or w.weapon_skill is not None)
c.eq("exactly the two staff rows carry a per-weapon skill override",
     overridden, ["Staff of Light", "Staff of Light"])

c.eq("the Ghost Ark fields TWO gauss flayer arrays, as printed",
     sum(1 for w in build(ARK).models[0].weapons if w.name == "Gauss Flayer Array"), 2)
c.true("...the same phrasing the Doomsday Ark's line already carries",
       "2 gauss flayer arrays" in corpus("Ghost Ark")
       and "2 gauss flayer arrays" in corpus("Doomsday Ark"))
c.true("the Catacomb Command Barge carries NO armoured bulk, unlike its two siblings",
       "Armoured Bulk" not in weapon_names(build(CCB)))


# --- 3. points, wargear, and the CHARACTER that leads nothing ---------------
print("--- 3. points and wargear ---")

for sheet, cost in ((CCB, 120), (ANNI, 95), (ARK, 100)):
    c.eq("%s costs %d" % (sheet.name, cost), build(sheet).points, cost)
    c.true("...and the corpus prints that number",
           "| 1 model | %d |" % cost in corpus(sheet.name))
    c.eq("...a single tier, no 2nd-unit price",
         NECRONS_POINTS[sheet.name].cost_for(1, 1),
         NECRONS_POINTS[sheet.name].cost_for(1, 3))

c.eq("the Barge's gauss cannon can become a tesla cannon",
     weapon_names(build(CCB, choices={"Catacomb Command Barge": {nec.CATACOMB_BARGE_GAUSS_TO_TESLA: 1}})),
     ["Staff of Light", "Staff of Light", "Tesla Cannon"])
c.eq("...and its staff can become an Overlord's blade, giving up BOTH rows",
     weapon_names(blade), ["Gauss Cannon", "Overlord's Blade"])
c.eq("the Annihilation Barge has the same cannon swap",
     weapon_names(build(ANNI, choices={"Annihilation Barge": {nec.ANNIHILATION_BARGE_GAUSS_TO_TESLA: 1}})),
     ["Armoured Bulk", "Tesla Cannon", "Twin Tesla Destructor"])
c.eq("the Ghost Ark prints NO wargear options at all", list(ARK.wargear_options), [])
c.true("...and the corpus has no Wargear Options section either",
       "## Wargear Options" not in corpus("Ghost Ark"))

orb_squad = build(CCB, gear={"Catacomb Command Barge": [nec.CATACOMB_BARGE_RESURRECTION_ORB]})
c.true("the Barge can be equipped with a resurrection orb",
       getattr(orb_squad.models[0], "resurrection_orb", False))
c.true("...and a Barge without it carries none",
       not getattr(build(CCB).models[0], "resurrection_orb", False))

# THE CHARACTER THAT LEADS NOTHING, through the real 19.01 gate.
c.true("the Catacomb Command Barge really is a CHARACTER",
       CatacombCommandBargeProfile.character)
for body in (WARRIORS, IMMORTALS, LYCHGUARD):
    c.true("...but it cannot lead %s - it prints no Leader section" % body.name,
           attached_units.can_attach(build(CCB), build(body)) != [])
c.eq("...and the corpus has no Leader section to read",
     ["## Leader" in corpus(s.name) for s in NEW], [False, False, False])
for sheet in NEW:
    entry = NECRONS_POINTS[sheet.name]
    c.true("%s takes no leads/supports entry" % sheet.name,
           not getattr(entry, "leads", None) and not getattr(entry, "supports", None))


# --- 4. Advanced Quantum Shielding ------------------------------------------
print("--- 4. Advanced Quantum Shielding ---")

c.true("the Barge carries the flag", CatacombCommandBargeProfile.advanced_quantum_shielding)
c.true("it is one of the shared S>T carriers",
       sot.ADVANCED_QUANTUM_SHIELDING in sot.SHIELDS)
c.true("...and it is NOT ranged-only, unlike the Wave Serpent Shield",
       not sot.ADVANCED_QUANTUM_SHIELDING.ranged_only and sot.WAVE_SERPENT_SHIELD.ranged_only)

# THE BOUNDARY, walked. T8, so S8 is "not greater than" and S9 is.
shoot = tk.shooting_scene(D["Lokhust Heavy Destroyers"], CCB, gap=12.0)
sc, target = shoot["shooting"], shoot["target"]
sc.active_squad = shoot["attacker"]
c.eq("S8 vs T8 is NOT greater than - no penalty",
     sum(m.amount for m in sc._wound_modifiers(target, 8)), 0)
c.eq("S9 vs T8 raises the wound threshold by 1",
     sum(m.amount for m in sc._wound_modifiers(target, 9)), 1)
c.true("...and the modifier names itself, so the roll can be explained",
       "Advanced Quantum Shielding" in [m.source for m in sc._wound_modifiers(target, 9)])

# BOTH PHASES - the printed text says "an attack", not "a ranged attack".
fight = tk.fight_scene(D["Skorpekh Destroyers"], CCB)
fc = fight["fight"]
fc.fighting_squad = fight["attacker"]
from game import weapons as w  # noqa: E402
big = w.GaussDestructorProfile()          # S14, comfortably over T8
c.eq("it reaches the FIGHT phase too",
     sum(m.amount for m in fc._wound_modifiers(big, fight["target"])), 1)
# The GEGENPROBE, and it needs its own liveness line: a Wave Serpent that
# turned out not to carry the shield would make the melee assertion below pass
# for the wrong reason.
serpent = build(ael.WAVE_SERPENT, "Player 1", n=20)
c.true("staging: the Wave Serpent really carries its shield",
       wave_serpent_shield.unit_has_shield(serpent))
c.eq("...and it fires in the SHOOTING phase",
     [m.source for m in sot.wound_modifiers(serpent, 14)], ["Wave Serpent Shield"])
c.eq("...but NOT in melee, because its text prints 'a RANGED attack'",
     sot.wound_modifiers(serpent, 14, melee=True), [])

# NO GATE AT ALL - Guardian Protocols' clause is the difference between them.
lone = build(CCB, "Player 1")
c.true("a lone Barge is protected - no NOBLE clause to satisfy",
       sot.ADVANCED_QUANTUM_SHIELDING.applies(lone, 9))
c.true("...where unled Lychguard get nothing from Guardian Protocols",
       not guardian_protocols.applies(build(LYCHGUARD, "Player 1"), 9))
aqs_text = corpus("Catacomb Command Barge")
c.true("...measured: its printed sentence opens with 'Each time an attack targets'",
       "**Advanced Quantum Shielding:** Each time an attack targets this model" in aqs_text)


# --- 5. Carrier Wave --------------------------------------------------------
print("--- 5. Carrier Wave ---")

c.true("the Barge carries the flag", CatacombCommandBargeProfile.carrier_wave)


def oc_scene(gap=3.0, straggler=None, friend=WARRIORS, owner="Player 2"):
    """A Barge and a friendly unit, `gap` inches apart edge to edge."""
    state = GameState()
    barge = place(build(CCB, owner), 20.0, 20.0)
    unit = place(build(friend, owner, n=2), 20.0, 20.0 + gap + 2.1, spacing=1.0)
    if straggler is not None:
        unit.models[-1].x_in, unit.models[-1].y_in = 20.0, 20.0 + straggler
    for squad in (barge, unit):
        for m in squad.models:
            state.add_token(m)
    return state, barge, unit


state, barge, warriors = oc_scene(gap=3.0)
base_oc = warriors.models[0].profile.oc
c.eq("a friendly NECRONS unit within 6\" gets +1 OC",
     objective_control.effective_oc(warriors.models[0], state.tokens), base_oc + 1)
c.eq("...and so does the Barge's own unit - the text says 'a', not 'another'",
     objective_control.effective_oc(barge.models[0], state.tokens),
     CatacombCommandBargeProfile.oc + 1)

far_state, _far_barge, far_warriors = oc_scene(gap=9.0)
c.eq("a unit outside 6\" gets nothing",
     objective_control.effective_oc(far_warriors.models[0], far_state.tokens), base_oc)

# THE TWO DISTANCES IN ONE SENTENCE: the UNIT qualifies if ONE model is within
# 6", and then EVERY model of it is raised - including one 20" away. A test
# that puts the whole unit in range cannot tell the two readings apart.
st, _b, unit = oc_scene(gap=3.0, straggler=45.0)
c.eq("one model in range lifts the WHOLE unit, straggler included",
     objective_control.effective_oc(unit.models[-1], st.tokens), base_oc + 1)

enemy_state, _eb, enemy = oc_scene(gap=3.0, owner="Player 2")
foe = place(build(WARRIORS, "Player 1", n=9), 20.0, 25.0, spacing=1.0)
for m in foe.models:
    enemy_state.add_token(m)
c.eq("an ENEMY NECRONS unit in range gets nothing - 'friendly'",
     objective_control.effective_oc(foe.models[0], enemy_state.tokens),
     foe.models[0].profile.oc)

ork_state, _ob, _ow = oc_scene(gap=3.0)
orks = place(tk.build(ork.BOYZ, "Player 2", name="2 Boyz 1"), 20.0, 25.2, spacing=1.0)
for m in orks.models:
    ork_state.add_token(m)
c.true("an Ork unit of the same player is not a NECRONS unit",
       not awakened_dynasty.is_necrons_unit(orks))
c.eq("...so it gets nothing either",
     objective_control.effective_oc(orks.models[0], ork_state.tokens),
     orks.models[0].profile.oc)

# "A FRIENDLY NECRONS UNIT" IS THE DATASHEET KEYWORD, NOT THE PER-MODEL
# reanimation_protocols FLAG. On every built datasheet the two agree, so a live
# board cannot tell them apart - measured below, which is exactly why the case
# that separates them has to be constructed. A unit whose MODELS carry the army
# rule but whose DATASHEET is not Necron is not a NECRONS unit.
agree = [sh.name for sh in nec.NECRONS.datasheets.values()
         if awakened_dynasty.is_necrons_unit(build(sh)) is not
         any(getattr(m.profile, "reanimation_protocols", False) for m in build(sh).models)]
c.eq("on every built Necron datasheet the two readings agree", agree, [])
fake_state, _fb, impostor = oc_scene(gap=3.0)
c.true("staging: its models really do carry the army rule",
       all(m.profile.reanimation_protocols for m in impostor.models))
impostor.datasheet = ork.BOYZ                     # ...but its datasheet is not Necron
c.true("...and it is no longer a NECRONS unit by the datasheet reading",
       not awakened_dynasty.is_necrons_unit(impostor))
c.eq("so it gets no Carrier Wave, however its models are flagged",
     objective_control.effective_oc(impostor.models[0], fake_state.tokens),
     impostor.models[0].profile.oc)

dead_state, dead_barge, dead_warriors = oc_scene(gap=3.0)
for m in dead_barge.models:
    m.current_wounds = 0
c.eq("a dead Barge radiates nothing",
     objective_control.effective_oc(dead_warriors.models[0], dead_state.tokens), base_oc)

# AN ADDER MEETING A SETTER - the first time that can happen at all.
swarm_state, swarm_barge, scarabs = oc_scene(gap=3.0, friend=D["Canoptek Scarab Swarms"])
cryptek = place(build(TECHNOMANCER, "Player 2", n=7), 20.0, 21.0)
for m in cryptek.models:
    swarm_state.add_token(m)
plain_state, _pb, plain_scarabs = oc_scene(gap=20.0, friend=D["Canoptek Scarab Swarms"])
plain_cryptek = place(build(TECHNOMANCER, "Player 2", n=8), 20.0, 41.0)
for m in plain_cryptek.models:
    plain_state.add_token(m)
set_only = objective_control.effective_oc(plain_scarabs.models[0], plain_state.tokens)
both = objective_control.effective_oc(scarabs.models[0], swarm_state.tokens)
c.eq("a SET Objective Control is then raised by the adder, not overwritten",
     both, set_only + 1)


# --- 6. Malevolent Arcing ---------------------------------------------------
print("--- 6. Malevolent Arcing ---")

c.true("the Annihilation Barge carries the flag", AnnihilationBargeProfile.malevolent_arcing)
c.eq("5+ and D3, as printed",
     (malevolent_arcing.MALEVOLENT_ARCING_THRESHOLD,
      malevolent_arcing.MALEVOLENT_ARCING_SIDES,
      malevolent_arcing.MALEVOLENT_ARCING_RANGE_IN), (5, 3, 3.0))
c.true("...and it is the third carrier of the sweep",
       issubclass(MalevolentArcingController,
                  __import__("game.mortal_wound_sweep", fromlist=["x"]).MortalWoundSweepController))


def arc_scene(near_gap=2.0, far_gap=12.0):
    """A Barge shooting a Warriors unit, with a SECOND enemy unit `near_gap`
    from the target and a third far away."""
    state = GameState()
    barge = place(build(ANNI, "Player 2"), 20.0, 10.0)
    target = place(build(WARRIORS, "Player 1", n=1), 20.0, 24.0, spacing=1.0)
    near = place(build(IMMORTALS, "Player 1", n=2), 20.0, 24.0 + near_gap + 1.26, spacing=1.0)
    far = place(build(LYCHGUARD, "Player 1", n=3), 20.0, 24.0 + far_gap, spacing=1.0)
    for squad in (barge, target, near, far):
        for m in squad.models:
            state.add_token(m)
    ctrl = MalevolentArcingController(dice_manager=DiceManager(), game_state=state)
    return state, ctrl, barge, target, near, far


st6, arc, barge6, target6, near6, far6 = arc_scene()
cands = arc.arcing_candidates(barge6, target6)
c.true("the TARGET is always a candidate", target6 in cands)
c.true("...and an enemy unit within 3\" of the TARGET joins it", near6 in cands)
c.true("...while one further away does not", far6 not in cands)
c.true("...and the Barge's own side is never a candidate",
       all(s.owner != barge6.owner for s in cands))

# FROZEN AT SELECTION - the whole reason the sweep grew a `candidates` argument.
st7, arc7, barge7, target7, near7, far7 = arc_scene()
arc7.on_target_selected(barge7, target7)
for m in near7.models:                      # walks out of range AFTER selection
    m.y_in += 30.0
for m in far7.models:                       # ...and another walks in
    m.x_in, m.y_in = target7.models[0].x_in, target7.models[0].y_in + 2.0
# .get()/(cl or []): a probe must make this suite RED, not abort it. The
# pre-fix worlds leave _armed empty or its candidate list None, and either
# one crashes a bare [...] before any check reports.
frozen = [t for _t, cl in arc7._armed.get(id(barge7), ()) for t in (cl or ())]
c.true("a unit that walked OUT after selection is still struck", near7 in frozen)
c.true("...and one that walked IN afterwards is not", far7 not in frozen)

st8, arc8, barge8, target8, _n8, _f8 = arc_scene()
c.true("a REACTIVE activation (Fire Overwatch) arms nothing - 'in YOUR Shooting phase'",
       not arc8.on_target_selected(barge8, target8, reactive=True))
c.true("...and a unit without the ability arms nothing either",
       not arc8.on_target_selected(build(ARK, "Player 2"), target8))


# THROUGH THE REAL ShootingController, both halves. A stub that answers
# resolved_weapon_against() proves nothing about whether the engine ever calls
# the controller or ever records which weapon fired - which is precisely what
# two A/B probes found when this section was written against a fake.
def real_arc(near_gap=2.0):
    """A real shooting activation by an Annihilation Barge, with the ability
    registered on the controller exactly as main.py registers it."""
    s = tk.shooting_scene(ANNI, WARRIORS, gap=6.0)
    sc, barge, target = s["shooting"], s["attacker"], s["target"]
    near = place(build(IMMORTALS, "Player 1", n=30),
                 target.models[0].x_in, target.models[0].y_in + near_gap + 1.26, spacing=1.0)
    for m in near.models:
        s["state"].add_token(m)
    sc.all_tokens = s["state"].tokens
    ctrl = MalevolentArcingController(dice_manager=s["dice"], game_state=s["state"])
    sc.on_target_selected.append(ctrl.on_target_selected)
    return s, sc, ctrl, barge, target, near


def fire(sc, dice, weapon_name):
    """Resolve one weapon group to the end, draining every die it asks for."""
    keys = [e[0] for e in sc.weapon_eligibility() if e[1] == weapon_name]
    if not keys:
        return False
    script(*([1] * 24))          # everything misses - the arcing is what matters
    sc.choose_weapon(keys[0])
    for _ in range(16):
        if not dice.pending_values:
            break
        dice.acknowledge()
        sc.on_dice_acknowledged()
    return True


s9, sc9, arc9, barge9, target9, near9 = real_arc()
sc9.start_shooting(barge9)
sc9.choose_target_squad(target9)
c.true("the REAL controller arms it at rule 10.02's select-targets step",
       id(barge9) in arc9._armed)
armed_units = [t for _t, cl in arc9._armed.get(id(barge9), ()) for t in (cl or ())]
c.true("...and the frozen set holds the target and its 3\" neighbour",
       target9 in armed_units and near9 in armed_units)

c.true("staging: the destructor really resolves against that target",
       fire(sc9, s9["dice"], "Twin Tesla Destructor"))
c.true("the controller can see WHICH weapon resolved, off the real record",
       sc9.resolved_weapon_against("Twin Tesla Destructor", target9))
script(6, 6, 3, 3)               # both gate dice strike, then the D3s
arc9.on_squad_finished_shooting(barge9, shooting=sc9)
c.true("with the destructor fired, the sweep starts", arc9.is_busy)

# ...and the destructor-only clause, against the SAME real record.
s10, sc10, arc10, barge10, target10, _n10 = real_arc()
sc10.start_shooting(barge10)
sc10.choose_target_squad(target10)
c.true("staging: the gauss cannon fires instead", fire(sc10, s10["dice"], "Gauss Cannon"))
c.true("...so the destructor did NOT resolve against this target",
       not sc10.resolved_weapon_against("Twin Tesla Destructor", target10))
c.true("a target the destructor never fired at pays NOTHING",
       not arc10.on_squad_finished_shooting(barge10, shooting=sc10))
c.true("...and nothing is left owed", not arc10.is_busy)

# SPLIT FIRE: two target selections in one activation, both paid at the end.
st11, arc11, barge11, target11, near11, far11 = arc_scene()
arc11.on_target_selected(barge11, target11)
arc11.on_target_selected(barge11, far11)
c.eq("two target selections owe two sweeps", len(arc11._armed[id(barge11)]), 2)


class _AllFired:
    """The record's answer for a split-fire scene the real controller cannot
    easily stage: both targets were shot with the destructor."""

    def resolved_weapon_against(self, weapon_name, target_squad):
        return weapon_name == malevolent_arcing.MALEVOLENT_ARCING_WEAPON


script(1, 1, 1, 1)    # nothing strikes, so the queue drains without dice steps
arc11.on_squad_finished_shooting(barge11, shooting=_AllFired())
c.eq("...and the armed list is spent", arc11._armed.get(id(barge11)), None)


# --- 7. Repair Barge --------------------------------------------------------
print("--- 7. Repair Barge ---")

c.true("the Ghost Ark carries the flag", GhostArkProfile.repair_barge)
c.eq("3\" and the army rule's own D3",
     (repair_barge.REPAIR_BARGE_RANGE_IN, repair_barge.REPAIR_BARGE_DICE_SIDES), (3.0, 3))


def ark_scene(gap=2.0, friend=WARRIORS):
    state = GameState()
    ark = place(build(ARK, "Player 2"), 20.0, 10.0)
    unit = place(build(friend, "Player 2", n=1), 20.0, 10.0 + gap + 2.1 + 0.63, spacing=1.0)
    foe = place(build(LYCHGUARD, "Player 1", n=4), 40.0, 40.0, spacing=1.0)
    for squad in (ark, unit, foe):
        for m in squad.models:
            state.add_token(m)
    ctrl = RepairBargeController(dice_manager=DiceManager(),
                                 decision_manager=DecisionManager(),
                                 game_state=state, auto_players=("Player 2",))
    return state, ctrl, ark, unit, foe


def kill_one(state, squad):
    """A REAL loss: zero a model and let the engine sweep it onto
    destroyed_models. Merely zeroing current_wounds leaves the model out of
    _alive() AND out of destroyed_models, so recoverable_wounds() would read 0
    and the scene would prove nothing."""
    squad.models[0].current_wounds = 0
    state.remove_dead_models()
    return squad


st12, rb, ark12, warr12, foe12 = ark_scene()
c.eq("a NECRON WARRIORS unit within 3\" is nearby", rb.nearby_warriors(ark12), [warr12])
c.eq("...an Immortals unit is not a NECRON WARRIORS unit",
     ark_scene(friend=IMMORTALS)[1].nearby_warriors(ark_scene(friend=IMMORTALS)[2]), [])
st13, rb13, ark13, _w13, _f13 = ark_scene(gap=9.0)
c.eq("...and one further than 3\" is not nearby", rb13.nearby_warriors(ark13), [])

# THE DELTA. Undamaged -> nothing. Damaged by THOSE attacks -> offered.
rb.maybe_offer(foe12, warr12)
c.eq("an undamaged unit offers nothing", rb.wounded_candidates(ark12), [])

st14, rb14, ark14, warr14, foe14 = ark_scene()
rb14.maybe_offer(foe14, warr14)              # snapshot BEFORE
kill_one(st14, warr14)                       # ...the enemy kills one
c.eq("a unit that lost wounds to THOSE attacks is a candidate",
     rb14.wounded_candidates(ark14), [warr14])

# ...and the clause a recoverable_wounds()-only version would lose.
st15, rb15, ark15, warr15, foe15 = ark_scene()
kill_one(st15, warr15)                       # damaged LONG ago
rb15.maybe_offer(foe15, warr15)              # snapshot now includes the loss
c.eq("a unit damaged earlier, losing nothing NOW, is not a candidate",
     rb15.wounded_candidates(ark15), [])
c.true("...even though it plainly has something to reanimate",
       reanimation_protocols.recoverable_wounds(warr15) > 0)

# BOTH PHASES.
st16, rb16, ark16, warr16, foe16 = ark_scene()
rb16.maybe_offer(foe16, warr16)
kill_one(st16, warr16)
script(3)
c.true("the SHOOTING hook fires it", rb16.on_squad_finished_shooting(foe16))
st17, rb17, ark17, warr17, foe17 = ark_scene()
rb17.maybe_offer(foe17, warr17, melee=True)
kill_one(st17, warr17)
script(3)
c.true("the FIGHT hook fires it too - 'an enemy unit finishes making its attacks'",
       rb17.on_unit_finished_fighting(foe17))

# THE TWO LEDGERS, measured apart.
st18, rb18, ark18, warr18, foe18 = ark_scene()
rb18.maybe_offer(foe18, warr18)
kill_one(st18, warr18)
script(3)
rb18.on_squad_finished_shooting(foe18)
rb18.on_dice_acknowledged()
c.true("after use, the ark model is spent for the turn",
       rb18._available_ark(ark18) is None)
# THE BEHAVIOUR, not the ledger's contents: _use() still WRITES to
# _selected_this_turn even when the line that reads it is gone, so asserting
# membership passes in the broken world too. What the rule says is that the
# same unit is not OFFERED again, so that is what is measured - with the ark
# limit lifted first, so only the per-unit one can be doing the refusing.
rb18._used_this_turn.clear()
kill_one(st18, warr18)
rb18.maybe_offer(foe18, warr18)
kill_one(st18, warr18)
c.eq("...and the same NECRON WARRIORS unit is not offered a second time",
     rb18.wounded_candidates(ark18), [])
rb18.reset_turn()
c.true("both clear at the turn boundary",
       rb18._available_ark(ark18) is not None and not rb18._selected_this_turn)

c.true("main.py hands it a placer - the FOURTH door into reanimate()",
       "repair_barge_controller.placer = return_placement_controller" in MAIN)


# --- 8. the Ghost Ark's transport pools -------------------------------------
print("--- 8. transport ---")

c.eq("the pools sum to the printed total",
     sum(limit for limit, _kw in GhostArkProfile.transport_pools),
     GhostArkProfile.transport_capacity)
c.eq("...which is 11", GhostArkProfile.transport_capacity, 11)
c.true("and the corpus prints both halves",
       "10 NECRON WARRIOR models and 1 NECRONS INFANTRY CHARACTER model" in corpus("Ghost Ark"))


def loaded(body=WARRIORS, leader=None, ci=0):
    squad = build(body, "Player 2", ci if isinstance(ci, int) else 0, composition_index=ci)
    if leader is not None:
        ld = build(leader, "Player 2", n=5)
        reasons = attached_units.can_attach(ld, squad)
        c.eq("staging: %s can lead %s" % (leader.name, body.name), reasons, [])
        attached_units.attach(ld, squad)
    return squad


POOL_CASES = [
    ("10 Necron Warriors", loaded(WARRIORS, ci=0), True),
    ("10 Warriors + Overlord (one 19.01 unit)", loaded(WARRIORS, OVERLORD, ci=0), True),
    ("20 Necron Warriors", loaded(WARRIORS, ci=1), False),
    ("20 Warriors + Overlord", loaded(WARRIORS, OVERLORD, ci=1), False),
    ("10 Lychguard", build(LYCHGUARD, "Player 2", n=6), False),
    ("Immortals", build(IMMORTALS, "Player 2", n=7), False),
    ("an Overlord alone", build(OVERLORD, "Player 2", n=8), True),
]
POOLS = GhostArkProfile.transport_pools
for label, squad, want in POOL_CASES:
    c.eq("%s fits the Ghost Ark: %s" % (label, want),
         transport_mod.fits_pools(squad, POOLS), want)

# ALREADY-EMBARKED LOADS COUNT. Ten Warriors aboard leaves pool A full, so a
# second Warriors unit does not fit - but an Overlord still does, because the
# CHARACTER pool is untouched. Nothing staged this before the A/B probe asked.
aboard = cluster(loaded(WARRIORS, ci=0), 20.0, 21.5)
c.true("staging: ten Warriors fill pool A on their own",
       transport_mod.fits_pools(aboard, POOLS))
c.true("a SECOND Warriors unit does not fit beside them",
       not transport_mod.fits_pools(cluster(loaded(WARRIORS, ci=0), 20.0, 21.5),
                                    POOLS, [aboard]))
c.true("...but an Overlord still does - its pool is untouched",
       transport_mod.fits_pools(build(OVERLORD, "Player 2", n=21), POOLS, [aboard]))

# THE TWO POOLS ARE DISJOINT, so "first fitting pool wins" never arbitrates.
warriors_unit = loaded(WARRIORS, ci=0)
overlap = [m for m in warriors_unit.models
           if attached_units.model_has_datasheet_keyword(warriors_unit, m, "NECRON WARRIORS")
           and attached_units.model_has_datasheet_keyword(warriors_unit, m, "CHARACTER")]
c.eq("no model is both a NECRON WARRIOR and a CHARACTER", overlap, [])

# EVERY OTHER TRANSPORT IS UNTOUCHED, as a set difference.
transports = [v for v in vars(__import__("game.units", fromlist=["x"])).values()
              if isinstance(v, type) and issubclass(v, UnitProfile)
              and getattr(v, "transport", False)]
c.true("there really are several transports to check", len(transports) >= 6)
c.eq("exactly one TRANSPORT declares sub-pools",
     sorted(v.name for v in transports if getattr(v, "transport_pools", ())),
     ["Ghost Ark"])

# BOTH READERS AGREE - 18.02 mid-battle and 18.01 at Declare Battle Formations.
state_t = GameState()
ark_t = place(build(ARK, "Player 2"), 20.0, 20.0)
for m in ark_t.models:
    state_t.add_token(m)
from game.movement import MovementController  # noqa: E402
from game.transport import TransportController  # noqa: E402

for label, squad, want in POOL_CASES:
    cluster(squad, 20.0, 21.5)
    for m in squad.models:
        if m not in state_t.tokens:
            state_t.add_token(m)
    mc = MovementController(all_tokens=state_t.tokens)
    mc.moved_squad_ids.add(squad)     # 18.02's "after a move this phase"
    tc = TransportController(
        setup_controller=None, game_state=state_t, all_tokens=state_t.tokens,
        movement_controller=mc, ingress_controller=None, dice_manager=None,
    )
    got_1802 = tc.can_embark(squad, ark_t.models[0])
    got_1801 = formations.embark_errors(squad, ark_t.models[0]) == []
    c.eq("18.02 agrees for %s" % label, got_1802, want)
    c.eq("...and 18.01 gives the same answer", got_1801, want)
    for m in squad.models:
        if m in state_t.tokens:
            state_t.tokens.remove(m)

# THE KILL RIG FIX: transport_requires had ONE reader until this stage.
state_k = GameState()
rig = place(tk.build(ork.KILL_RIG, "Player 2", name="2 Kill Rig 1"), 20.0, 20.0)
snaggas = place(tk.build(ork.BEAST_SNAGGA_BOYZ, "Player 2", name="2 Beast Snagga Boyz 1"), 20.0, 23.0, spacing=0.9)
boyz = place(tk.build(ork.BOYZ, "Player 2", name="2 Boyz 2"), 20.0, 23.0, spacing=0.9)
for squad in (rig, snaggas):
    for m in squad.models:
        state_k.add_token(m)
c.eq("18.01 now refuses plain Boyz into the Kill Rig - its BEAST SNAGGA half",
     formations.embark_errors(boyz, rig.models[0]) == [], False)
c.eq("...and still allows Beast Snagga Boyz",
     formations.embark_errors(snaggas, rig.models[0]) == [], True)

# ...AND THE CONTROLLER HANDS THEM OVER. The fits_pools() calls above prove the
# ARITHMETIC counts an existing load; they say nothing about whether
# can_embark() passes one in, and that is its own line to forget - the A/B
# probe for it reported NO BITE until this block existed.
#
# THE CASE HAS TO BE ONE CAPACITY WOULD ALLOW, or the plain 11-model check
# answers first and the pools are never consulted at all: ten Warriors aboard
# leave one slot free, so a second Warriors unit is refused for its SIZE and
# the probe stays silent. A lone Overlord aboard is the discriminating load -
# it leaves ten slots and fills the CHARACTER pool outright.
state_e = GameState()
ark_e = place(build(ARK, "Player 2", n=30), 20.0, 20.0)
for m in ark_e.models:
    state_e.add_token(m)
first_lord = cluster(build(OVERLORD, "Player 2", n=31), 20.0, 21.5)
second_lord = cluster(build(OVERLORD, "Player 2", n=32), 20.0, 21.5)
more_warriors = cluster(loaded(WARRIORS, ci=0), 20.0, 21.5)
for squad in (first_lord, second_lord, more_warriors):
    for m in squad.models:
        state_e.add_token(m)
mc_e = MovementController(all_tokens=state_e.tokens)
for squad in (first_lord, second_lord, more_warriors):
    mc_e.moved_squad_ids.add(squad)        # 18.02's "after a move this phase"
tc_e = TransportController(
    setup_controller=None, game_state=state_e, all_tokens=state_e.tokens,
    movement_controller=mc_e, ingress_controller=None, dice_manager=None,
)
tc_e.embark(first_lord, ark_e.models[0])
c.eq("staging: the first Overlord is really aboard",
     tc_e.embarked_squads_in(ark_e.models[0]), [first_lord])
c.true("staging: capacity ALONE would take a second one",
       tc_e.remaining_capacity(ark_e.models[0]) >= 1)
c.eq("can_embark() refuses a SECOND character - pool B is full",
     tc_e.can_embark(second_lord, ark_e.models[0]), False)
c.eq("...but ten Warriors still board, because pool A is untouched",
     tc_e.can_embark(more_warriors, ark_e.models[0]), True)


# --- 9. the extractions, with their OTHER carriers ---------------------------
print("--- 9. the extractions ---")

c.eq("three S>T carriers share one comparison",
     len(sot.SHIELDS), 3)
c.true("wave_serpent_shield re-exports the shared carrier's answer",
       wave_serpent_shield.WAVE_SERPENT_SHIELD_LABEL == sot.WAVE_SERPENT_SHIELD.label)
c.true("...and so does guardian_protocols",
       guardian_protocols.GUARDIAN_PROTOCOLS_LABEL == sot.GUARDIAN_PROTOCOLS.label)
c.eq("only the Wave Serpent's is ranged-only",
     sorted(s.label for s in sot.SHIELDS if s.ranged_only), ["Wave Serpent Shield"])

# The orb's ledger moved onto the BEARER - behaviour-neutral where the two are
# the same unit, which is every carrier but the Barge.
state_o = GameState()
# The LOKHUST LORD, not the Overlord: the Overlord's orb is printed
# conditionally ("if this model is not equipped with a tachyon arrow"), so a
# plain gear request leaves him without one and this scene would be measuring
# that rather than the ledger. The Lokhust Lord's line is unconditional.
lord = place(build(D["Lokhust Lord"], "Player 2", n=9,
                   gear={"Lokhust Lord": [nec.LOKHUST_LORD_RESURRECTION_ORB]}), 20.0, 20.0)
for m in lord.models:
    state_o.add_token(m)
c.true("staging: the Lokhust Lord really carries an orb",
       getattr(lord.models[0], "resurrection_orb", False))
lord.models[0].current_wounds = 1
orb_ctrl = ResurrectionOrbController(game_state=state_o, auto_players=("Player 2",))
c.eq("a 'this unit resurrects' orb still targets only itself",
     orb_ctrl.targets_for(lord), [lord])
c.true("...and can_use() answers as it always did", orb_ctrl.can_use(lord))

state_b = GameState()
cbarge = place(build(CCB, "Player 2", gear={"Catacomb Command Barge": [nec.CATACOMB_BARGE_RESURRECTION_ORB]}),
               20.0, 20.0)
# Lychguard (W2) rather than Warriors (W1): a damaged W1 model is a DEAD one,
# and recoverable_wounds() would read 0 unless it had also been swept onto
# destroyed_models - which would make this scene about the sweep.
hurt = place(build(LYCHGUARD, "Player 2", n=11), 20.0, 24.0, spacing=1.0)
hurt.models[0].current_wounds = 1
distant = place(build(LYCHGUARD, "Player 2", n=12), 60.0, 60.0, spacing=1.0)
distant.models[0].current_wounds = 1
for squad in (cbarge, hurt, distant):
    for m in squad.models:
        state_b.add_token(m)
ranged_orb = RangedResurrectionOrbController(game_state=state_b, auto_players=("Player 2",))
c.eq("the Barge's orb targets a NEARBY unit, not itself",
     ranged_orb.targets_for(cbarge), [hurt])
c.true("...and never its own VEHICLE unit - it is neither INFANTRY nor MOUNTED",
       cbarge not in ranged_orb.targets_for(cbarge))
c.true("a unit outside 6\" is no target", distant not in ranged_orb.targets_for(cbarge))

# THE LEDGER KEYS THE BEARER - as BEHAVIOUR, because "(once per battle, per
# unit)" heads a WARGEAR ability and the wargear is the Barge's. A second
# damaged unit is moved into range AFTER the orb is spent: keyed on the target,
# the Barge could orb that one too, for the whole battle.
second = place(build(LYCHGUARD, "Player 2", n=13), 20.0, 26.0, spacing=1.0)
second.models[0].current_wounds = 1
for m in second.models:
    state_b.add_token(m)
c.eq("staging: two damaged units are now in range",
     sorted(sq.name for sq in ranged_orb.targets_for(cbarge)),
     sorted([hurt.name, second.name]))
ranged_orb._use(cbarge, hurt)
ranged_orb._pending = None            # the die is not what this line is about
ranged_orb.reset_turn()               # ...and neither is the per-TURN limit
c.eq("after orbing one unit the Barge's orb is spent for the battle",
     ranged_orb.targets_for(cbarge), [])
c.true("main.py hands the Barge's orb its own placer - section 7 of "
       "test_return_placement.py resolves the BASE class and cannot see this one",
       "catacomb_orb_controller.placer = return_placement_controller" in MAIN)


# --- 10. wiring, AI, sprites, dormancy --------------------------------------
print("--- 10. wiring ---")

for name in ("MalevolentArcingController(", "RepairBargeController(",
             "RangedResurrectionOrbController("):
    c.true("main.py constructs %s" % name, name in MAIN)

for fragment in (
    "shooting_controller.on_target_selected.append(",
    "repair_barge_controller.on_squad_finished_shooting)",
    "repair_barge_controller.on_unit_finished_fighting(_fighter)",
    "catacomb_orb_controller.offer_at_end_of_phase(",
    "catacomb_orb_controller.reset_turn()",
    "repair_barge_controller.reset_turn()",
    "malevolent_arcing_controller.on_dice_acknowledged()",
    "repair_barge_controller.on_dice_acknowledged()",
    "catacomb_orb_controller.on_dice_acknowledged()",
):
    c.true("...and RUNS %s as a whole statement" % fragment, main_runs(fragment))

# The five registrations that keep Malevolent Arcing from being error class 25.
for fragment, label in (
    ("malevolent_arcing_controller,", "the shared damage-pick tuple"),
    ("or malevolent_arcing_controller.is_busy", "the phase gate"),
    ("or malevolent_arcing_controller.pending_damage_choice is not None", "the AI pause"),
    ("malevolent_arcing_controller.choose_damage_model(clicked)", "a click branch"),
    ("renderer.draw_damage_choice_highlight(board_surface, board, malevolent_arcing_controller.pending_damage_choice)",
     "the board highlight"),
):
    c.true("Malevolent Arcing is in %s" % label, fragment in MAIN)

# CONSTRUCTION ORDER (error class 23): repair_barge joins both target_reactions
# tuples, so it must be built before them.
c.true("repair_barge_controller is constructed before the reactions tuples",
       0 <= MAIN.find("repair_barge_controller = RepairBargeController")
       < MAIN.find("shooting_target_reactions = ("))
c.true("...and malevolent_arcing_controller before its listener append",
       0 <= MAIN.find("malevolent_arcing_controller = MalevolentArcingController")
       < MAIN.find("shooting_controller.on_target_selected.append("))

AI = io.open(os.path.join("ai", "agent_driver.py"), encoding="utf-8").read()
for name in ("Catacomb Command Barge", "Annihilation Barge", "Ghost Ark",
             "carrier_wave", "malevolent_arcing", "repair_barge",
             "advanced_quantum_shielding"):
    # FULL datasheet names and flag names only: "Barge", "Ark" and "Scythe"
    # all appear in that file already, in comments about other things.
    c.true("the AI knows nothing about %s" % name, name not in AI)

for sheet in NEW:
    squad = build(sheet, "Player 1")
    got = sprites.sprite_for(squad.models[0])
    want = sheet.name != "Ghost Ark"
    c.eq("%s resolves a sprite: %s" % (sheet.name, want), bool(got), want)

ROSTER = io.open(os.path.join("armies", "necrons.json"), encoding="utf-8").read()
for sheet in NEW:
    c.true("%s is dormant by roster" % sheet.name, sheet.name not in ROSTER)

MISSING = io.open("fetch_datasheet_rules.py", encoding="utf-8").read()
c.true("the three are out of MISSING_NECRONS' build list",
       all('"%s"' % s.name not in MISSING for s in NEW))
c.true("...and the Night Scythe is beside the Doom Scythe in the out-of-scope tail",
       '"Doom Scythe", "Night Scythe", "Convergence Of Dominion"' in MISSING)

c.finish()
