"""The Necron Hypercrypt Legion list, armies/necrons_hypercrypt.json, checked
against the APP EXPORT the user supplied (newrecruit.eu, 2000 pts) - not against
itself.

WHY A SUITE BESIDE THE GOLDEN MASTER. armies/baseline.txt is written FROM the
build, so a mis-transcribed option - nine tesla carbines, an Overlord without
his orb, gauss flux arcs where the export says death rays - would be blessed by
the next --write. The numbers below are the export's own, typed from its text.

  1. the declaration: detachment, Force Disposition, Primary Mission, no Enhancements
  2. picking the list is what makes the Hypercrypt Legion live, for that player only
  3. the export, unit by unit: models, weapons, wargear
  4. the four attachments (19.01), with their roles
  5. points: the export sums to 2000, the engine to 1990, and the gap is exactly
     the two KNOWN transcription deviations - with the printed page agreeing with
     the export, so the deviation is the engine's and not a typo here
  6. the Monolith is the first TITANIC model any shipped list fields
"""

import io
import os
import re
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from testkit import Checks  # noqa: E402

from game import (army_lists, attached_units, config, detachments,  # noqa: E402
                  enhancements, primary_missions as pm, titanic)
from game import force_dispositions as fd  # noqa: E402

c = Checks("Necron Hypercrypt Legion list")
KEY = "necrons_hypercrypt"
entry = army_lists.get(KEY)
built = army_lists.preview_squads(KEY, "Player 1")
squads = {s.name: s for s in built}


def weapons_of(squad):
    counts = {}
    for model in squad.models:
        for weapon in model.weapons:
            counts[weapon.name] = counts.get(weapon.name, 0) + 1
    return counts


# ==========================================================================
print("=== 1. the declaration ===")
# ==========================================================================
c.eq("the list fields the Hypercrypt Legion alone", entry.detachments, ("Hypercrypt Legion",))
c.eq("...which is a legal set", detachments.validate(KEY), [])
c.eq("its Force Disposition is Reconnaissance", entry.force_disposition, fd.RECONNAISSANCE)
c.eq("...so it plays Reconnaissance Sweep",
     pm.mission_for(entry.force_disposition).name, "Reconnaissance Sweep")
c.eq("its army rule is Reanimation Protocols", entry.army_rule, "Reanimation Protocols")
c.eq("it is a Necron list", entry.faction_keyword, "NECRONS")
c.eq("the export buys no Enhancement", entry.enhancement_names(), [])
c.eq("...and none lands on a model",
     [n for s in built for n in enhancements.granted_names(s)], [])
c.true("it is nobody's default list",
       KEY not in (config.PLAYER1_ARMY, config.PLAYER2_ARMY))


# ==========================================================================
print("=== 2. picking it makes the detachment live ===")
# ==========================================================================
# A throwaway copy of config, so the shipped settings are never touched.
_cfg = types.ModuleType("cfg_copy")
_cfg.__dict__.update({k: v for k, v in vars(config).items() if not k.startswith("__")})
army_lists.apply_to_config({"Player 1": KEY, "Player 2": "necrons"}, config_module=_cfg)
c.eq("Player 1 fields the Hypercrypt Legion",
     tuple(_cfg.HYPERCRYPT_LEGION_PLAYERS), ("Player 1",))
c.eq("...and not Awakened Dynasty", "Player 1" in tuple(_cfg.AWAKENED_DYNASTY_PLAYERS), False)
c.eq("the default Necron list on the other side keeps Awakened Dynasty",
     tuple(_cfg.AWAKENED_DYNASTY_PLAYERS), ("Player 2",))
c.eq("the shipped config is untouched", tuple(config.HYPERCRYPT_LEGION_PLAYERS), ())


# ==========================================================================
print("=== 3. the export, unit by unit ===")
# ==========================================================================
# name -> (models, weapon rows). A weapon printed with a ranged AND a melee row
# (plasmic lance, staff of light, rod of covenant) counts twice per model, and
# the Void Dragon's spear carries its anti-vehicle row plus the strike row that
# leads its strike/sweep firing-mode pair.
EXPECTED = {
    "1 C'tan Shard of the Void Dragon 1": (1, {
        "Spear of the Void Dragon": 1, "Spear of the Void Dragon - Strike": 1,
        "Voltaic Storm": 1, "Canoptek Tail Blades": 1}),
    "1 Hexmark Destroyer 1": (1, {
        "Enmitic disintegrator pistols": 1, "Close Combat Weapon": 1}),
    "1 Immortals 1 + Plasmancer": (11, {
        "Tesla Carbine": 10, "Close Combat Weapon": 10, "Plasmic Lance": 2}),
    "1 Necron Warriors 1 + Technomancer": (21, {
        "Gauss Flayer": 20, "Close Combat Weapon": 20, "Staff of Light": 2}),
    "1 Lokhust Heavy Destroyers 1": (2, {
        "Gauss Destructor": 2, "Close Combat Weapon": 2}),
    "1 Lychguard 1 + Overlord": (11, {"Hyperphase Sword": 10, "Voidscythe": 1}),
    "1 Monolith 1": (1, {"Death Ray": 4, "Particle Whip": 1, "Portal of Exile": 1}),
    "1 Skorpekh Destroyers 1 + Skorpekh Lord": (4, {
        "Skorpekh Hyperphase Weapons": 3, "Enmitic Annihilator": 1,
        "Flensing Claw": 1, "Hyperphase Harvester": 1}),
    "1 Triarch Praetorians 1": (10, {"Rod of covenant": 20}),
}
c.eq("thirteen export lines make nine units, in roster order",
     [s.name for s in built], list(EXPECTED))
c.eq("...holding 62 models", sum(len(s.models) for s in built), 62)
for name, (models, weapons) in EXPECTED.items():
    squad = squads.get(name)
    c.eq("%s has %d models" % (name, models), len(squad.models) if squad else None, models)
    c.eq("%s carries exactly the export's weapons" % name,
         weapons_of(squad) if squad else None, weapons)

_lych = squads.get("1 Lychguard 1 + Overlord")
_lych_models = _lych.models if _lych else []
c.eq("every one of the ten Lychguard has a dispersion shield",
     sum(1 for m in _lych_models if getattr(m, "dispersion_shield", False)), 10)
c.eq("the Resurrection Orb is on the Overlord, and only on him",
     [m.profile.name for m in _lych_models if getattr(m, "resurrection_orb", False)],
     ["Overlord"])
_skorp = squads.get("1 Skorpekh Destroyers 1 + Skorpekh Lord")
c.eq("the export buys no Plasmacyte",
     sum(getattr(m, "plasmacyte_count", 0) for m in (_skorp.models if _skorp else [])), 0)


# ==========================================================================
print("=== 4. the four attachments ===")
# ==========================================================================
ROLES = {
    "1 Immortals 1 + Plasmancer": [("Immortals", attached_units.BODYGUARD),
                                   ("Plasmancer", attached_units.SUPPORT)],
    "1 Necron Warriors 1 + Technomancer": [("Necron Warriors", attached_units.BODYGUARD),
                                           ("Technomancer", attached_units.SUPPORT)],
    "1 Lychguard 1 + Overlord": [("Lychguard", attached_units.BODYGUARD),
                                 ("Overlord", attached_units.LEADER)],
    "1 Skorpekh Destroyers 1 + Skorpekh Lord": [
        ("Skorpekh Destroyers", attached_units.BODYGUARD),
        ("Skorpekh Lord", attached_units.LEADER)],
}
c.eq("exactly four units are attached",
     sorted(s.name for s in built if attached_units.is_attached_unit(s)), sorted(ROLES))
for name, roles in ROLES.items():
    squad = squads.get(name)
    c.eq("%s merges with these roles" % name,
         [(comp.datasheet.name, comp.role)
          for comp in getattr(squad, "attached_components", [])], roles)

# testkit.lists_fielding() reads LEADERS as well as entries - and no datasheet
# the "dormant by roster" pins name is a leader anywhere, so without this line
# nothing measures that half. The Plasmancer is fielded only as a leader, by
# both Necron lists.
import testkit as tk  # noqa: E402
c.eq("a character fielded only as a leader counts as fielded, by both Necron lists",
     tk.lists_fielding("Plasmancer"), ["necrons", "necrons_hypercrypt"])
c.eq("...and a list-entry unit is found too", tk.lists_fielding("Monolith"), [KEY])


# ==========================================================================
print("=== 5. points ===")
# ==========================================================================
EXPORT_POINTS = {
    "C'tan Shard of the Void Dragon": 345, "Hexmark Destroyer": 75, "Overlord": 90,
    "Plasmancer": 60, "Skorpekh Lord": 95, "Technomancer": 80, "Immortals": 140,
    "Necron Warriors": 190, "Lokhust Heavy Destroyers": 100, "Lychguard": 160,
    "Monolith": 420, "Skorpekh Destroyers": 85, "Triarch Praetorians": 160,
}
c.eq("the export's thirteen lines add up to its 2000", sum(EXPORT_POINTS.values()), 2000)

engine_points = {}
for squad in built:
    components = getattr(squad, "attached_components", None) or []
    if components:
        for comp in components:
            engine_points[comp.datasheet.name] = comp.points
    else:
        engine_points[squad.datasheet.name] = squad.points
c.eq("every export line has an engine price", sorted(engine_points), sorted(EXPORT_POINTS))
deviations = {name: (EXPORT_POINTS[name], engine_points.get(name))
              for name in EXPORT_POINTS if engine_points.get(name) != EXPORT_POINTS[name]}
c.eq("exactly two datasheets price differently - the two known deviations",
     deviations, {"Plasmancer": (60, 55), "Skorpekh Lord": (95, 90)})


def printed_first_price(datasheet_name):
    text = io.open(os.path.join("rules", "necrons", datasheet_name + ".md"),
                   encoding="utf-8").read()
    match = re.search(r"^\| YOUR [^|]*\| 1 model \| (\d+) \|", text, re.M)
    return int(match.group(1)) if match else None


for name, (printed, _engine) in sorted(deviations.items()):
    c.eq("the printed page agrees with the export on %s, so the deviation is the engine's" % name,
         printed_first_price(name), printed)
c.eq("the engine totals 1990", sum(s.points for s in built), 1990)


# ==========================================================================
print("=== 6. TITANIC ===")
# ==========================================================================
c.true("the Monolith is TITANIC", titanic.is_titanic_unit(squads.get("1 Monolith 1")))
c.eq("...and nothing else in this list is",
     [s.name for s in built if titanic.is_titanic_unit(s)], ["1 Monolith 1"])
c.eq("it is the only list that fields a TITANIC unit at all",
     [e.key for e in army_lists.ARMY_LISTS
      if any(titanic.is_titanic_unit(s) for s in army_lists.preview_squads(e.key, "Player 1"))],
     [KEY])

c.finish()
