"""Player 2's Necron army list, as main.py builds it.

Builds the roster the same way main() does rather than driving main() itself:
that keeps the check about WHAT the army is, independent of deployment.

THE TOTALS ARE WRITTEN AS THE LIST'S OWN ARITHMETIC, not as whatever the
engine happened to produce on the day. test_player1_army.py went stale twice
in exactly that way - it kept reporting the previous army's numbers, green,
while checking an army that no longer existed. A total copied from a passing
run cannot catch the case it exists for; a total written out as
"5 characters + 54 rank and file" can.

THE POINTS DELIBERATELY DISAGREE with the user's list, and in BOTH directions.
game/factions/necrons_points.py holds the Wahapedia transcription and wins;
each per-entry difference is recorded next to the entry there. This suite pins
BOTH numbers so the gap stays a stated fact rather than something rediscovered
later as a bug.
"""

from testkit import Checks, build_squad
from game import (
    attached_units, awakened_dynasty, crit_hit, feel_no_pain, guardian_protocols,
    reanimation_protocols as rp,
)
from game.factions import necrons as nec

c = Checks("Player 2 - Necrons")


def build(sheet, name=None, **kw):
    kw.setdefault("name", name or f"2 {sheet.name} 1")
    return build_squad(sheet, "Player 2", **kw)


def line_counts(squad):
    out = {}
    for m in squad.models:
        out[m.profile.name] = out.get(m.profile.name, 0) + 1
    return out


def weapons(model):
    return sorted(w.name for w in model.weapons)


# --- 1. the five characters -------------------------------------------------
print("--- 1. characters ---")

dragon = build(nec.CTAN_SHARD_OF_THE_VOID_DRAGON, "2 C'tan Shard of the Void Dragon 1")
c.eq("Char1 Void Dragon: one model", len(dragon.models), 1)
c.eq("...with tail blades, the spear and voltaic storm", weapons(dragon.models[0]),
     ["Canoptek Tail Blades", "Spear of the Void Dragon",
      "Spear of the Void Dragon - Strike", "Voltaic Storm"])
c.eq("...at 345 pts", dragon.points, 345)   # the list says 330

szeras = build(nec.ILLUMINOR_SZERAS, "2 Illuminor Szeras 1")
c.eq("Char2 Illuminor Szeras: eldritch lance and impaling legs",
     weapons(szeras.models[0]), ["Eldritch Lance", "Eldritch Lance", "Impaling Legs"])
c.eq("...at 175 pts", szeras.points, 175)   # the list says 165

overlord = build(nec.OVERLORD, "2 Overlord 1",
                 choices={"Overlord": {nec.OVERLORD_TO_VOIDSCYTHE: 1}},
                 gear={"Overlord": [nec.OVERLORD_RESURRECTION_ORB]})
# Kept unattached HERE so the loadout checks below read his own models; the
# merged versions are built in section 3.
c.eq("Char3 Overlord: Voidscythe only - the swap gives up BOTH printed weapons",
     weapons(overlord.models[0]), ["Voidscythe"])
c.eq("...and the resurrection orb, which the swap is what makes him eligible for",
     getattr(overlord.models[0], "resurrection_orb", False), True)
c.eq("...at 90 pts, the orb being free", overlord.points, 90)   # the list says 85

plasmancer = build(nec.PLASMANCER, "2 Plasmancer 1")
c.eq("Char4 Plasmancer: the plasmic lance, both its rows",
     weapons(plasmancer.models[0]), ["Plasmic Lance", "Plasmic Lance"])
c.eq("...at 55 pts - the one character the list AGREES on", plasmancer.points, 55)

technomancer = build(nec.TECHNOMANCER, "2 Technomancer 1")
c.eq("Char5 Technomancer: the staff of light, both its rows",
     weapons(technomancer.models[0]), ["Staff of Light", "Staff of Light"])
c.eq("...at 80 pts, and the list agrees", technomancer.points, 80)


# --- 2. the rank and file ---------------------------------------------------
print("--- 2. the rest of the list ---")

immortals = build(nec.IMMORTALS, "2 Immortals 1", composition_index=1)
c.eq("10 Immortals", line_counts(immortals), {"Immortal": 10})
c.eq("...with gauss blasters and close combat weapons",
     weapons(immortals.models[0]), ["Close Combat Weapon", "Gauss Blaster"])
c.eq("...at 140 pts", immortals.points, 140)     # the list says 150

warriors = build(nec.NECRON_WARRIORS, "2 Necron Warriors 1", composition_index=1)
c.eq("20 Necron Warriors", line_counts(warriors), {"Necron Warrior": 20})
c.eq("...with gauss flayers", weapons(warriors.models[0]),
     ["Close Combat Weapon", "Gauss Flayer"])
c.eq("...at 190 pts", warriors.points, 190)      # the list says 200

wraiths = build(nec.CANOPTEK_WRAITHS, "2 Canoptek Wraiths 1", composition_index=1)
c.eq("6 Canoptek Wraiths", line_counts(wraiths), {"Canoptek Wraith": 6})
c.eq("...with vicious claws and NOTHING added - the list takes no casters",
     weapons(wraiths.models[0]), ["Vicious Claws"])
c.eq("...at 220 pts, and the list agrees at the 1st unit", wraiths.points, 220)

ark = build(nec.DOOMSDAY_ARK, "2 Doomsday Ark 1")
c.eq("1 Doomsday Ark with cannon, TWO arrays and the bulk", weapons(ark.models[0]),
     ["Armoured Bulk", "Doomsday Cannon", "Gauss Flayer Array", "Gauss Flayer Array"])
c.eq("...at 210 pts", ark.points, 210)           # the list says 200

lokhust = build(nec.LOKHUST_DESTROYERS, "2 Lokhust Destroyers 1", composition_index=3)
c.eq("6 Lokhust Destroyers", line_counts(lokhust), {"Lokhust Destroyer": 6})
c.eq("...with gauss cannons", weapons(lokhust.models[0]),
     ["Close Combat Weapon", "Gauss Cannon"])
c.eq("...at 170 pts", lokhust.points, 170)       # the list says 180

heavies = build(nec.LOKHUST_HEAVY_DESTROYERS, "2 Lokhust Heavy Destroyers 1",
                composition_index=2,
                choices={"Lokhust Heavy Destroyer": {nec.LOKHUST_HEAVY_TO_ENMITIC_EXTERMINATOR: 1}})
c.eq("3 Lokhust Heavy Destroyers", len(heavies.models), 3)
carried = sorted(w.name for m in heavies.models for w in m.weapons
                 if w.name != "Close Combat Weapon")
c.eq("...ONE exterminator and TWO destructors, exactly as the list writes it",
     carried, ["Enmitic Exterminator", "Gauss Destructor", "Gauss Destructor"])
c.eq("...at 160 pts", heavies.points, 160)       # the list says 165

lychguard = build(nec.LYCHGUARD, "2 Lychguard 1",
                  choices={"Lychguard": {nec.LYCHGUARD_TO_HYPERPHASE_SWORD: 5}},
                  gear={"Lychguard": [nec.LYCHGUARD_DISPERSION_SHIELD]})
c.eq("5 Lychguard", len(lychguard.models), 5)
c.eq("...all five with hyperphase swords",
     [weapons(m) for m in lychguard.models], [["Hyperphase Sword"]] * 5)
c.eq("...and all five with the dispersion shield, which is the half of that "
     "printed option that is NOT a weapon",
     sum(1 for m in lychguard.models if getattr(m, "dispersion_shield", False)), 5)
c.eq("...at 80 pts", lychguard.points, 80)       # the list says 85

skorpekh = build(nec.SKORPEKH_DESTROYERS, "2 Skorpekh Destroyers 1")
c.eq("3 Skorpekh Destroyers", len(skorpekh.models), 3)
c.eq("...with their hyperphase weapons and NO Plasmacyte - the list takes none",
     (weapons(skorpekh.models[0]), getattr(skorpekh.models[0], "plasmacyte_count", 0)),
     (["Skorpekh Hyperphase Weapons"], 0))
c.eq("...at 85 pts", skorpekh.points, 85)        # the list says 90


# --- 3. what this army does NOT have ---------------------------------------
print("--- 3. deliberate absences ---")

# --- the three attachments the user assigned (rule 19.01) -------------------
# attach() MERGES the leader into the bodyguard squad and discards the leader
# squad, so these are the units the scene actually holds - which is why they
# are rebuilt here rather than reusing the standalone squads above.
led_lychguard = attached_units.attach(
    build(nec.OVERLORD, "2 Overlord 2",
          choices={"Overlord": {nec.OVERLORD_TO_VOIDSCYTHE: 1}},
          gear={"Overlord": [nec.OVERLORD_RESURRECTION_ORB]}),
    build(nec.LYCHGUARD, "2 Lychguard 2",
          choices={"Lychguard": {nec.LYCHGUARD_TO_HYPERPHASE_SWORD: 5}},
          gear={"Lychguard": [nec.LYCHGUARD_DISPERSION_SHIELD]}))
led_warriors = attached_units.attach(
    build(nec.TECHNOMANCER, "2 Technomancer 2"),
    build(nec.NECRON_WARRIORS, "2 Necron Warriors 2", composition_index=1))
led_immortals = attached_units.attach(
    build(nec.PLASMANCER, "2 Plasmancer 2"),
    build(nec.IMMORTALS, "2 Immortals 2", composition_index=1))

c.eq("the Overlord joins the Lychguard", led_lychguard.name, "2 Lychguard 2 + Overlord")
c.eq("the Technomancer joins the Warriors", led_warriors.name, "2 Necron Warriors 2 + Technomancer")
c.eq("the Plasmancer joins the Immortals", led_immortals.name, "2 Immortals 2 + Plasmancer")
c.eq("a merge is ONE unit, not two (19.01)",
     [len(led_lychguard.models), len(led_warriors.models), len(led_immortals.models)],
     [6, 21, 11])
c.eq("...and its points are the sum",
     [led_lychguard.points, led_warriors.points, led_immortals.points],
     [80 + 90, 190 + 80, 140 + 55])
c.eq("...and its Starting Strength counts the leader too (19.02)",
     [led_lychguard.starting_model_count, led_warriors.starting_model_count,
      led_immortals.starting_model_count], [6, 21, 11])

# WHAT EACH ATTACHMENT ACTUALLY SWITCHES ON. Each of these three abilities was
# printed and inert before the leaders arrived, so this is where they start
# working - and each is checked at the ability, not at the attachment.
c.eq("the Overlord is the NOBLE Guardian Protocols asks for - the Lychguard "
     "had the ability printed and it never fired",
     guardian_protocols.is_led_by_noble(led_lychguard), True)
c.eq("the Technomancer grants the whole unit Feel No Pain 5+",
     feel_no_pain.current_feel_no_pain(led_warriors.models[-1]), "5+")
c.eq("the Plasmancer drops the unit's ranged Critical Hit threshold to 5+",
     crit_hit.crit_hit_threshold(led_immortals.models[-1]), 5)
c.eq("...and Command Protocols now has three units to pay",
     [len(awakened_dynasty.hit_modifiers(u)) for u in
      (led_lychguard, led_warriors, led_immortals)], [1, 1, 1])

ROSTER = [dragon, szeras, led_lychguard, led_warriors, led_immortals,
          wraiths, ark, lokhust, heavies, skorpekh]

c.eq("exactly three units are attached units (19.01)",
     len([s for s in ROSTER if attached_units.is_attached_unit(s)]), 3)
c.eq("the other two characters stand ALONE - Szeras has no printed LEADER "
     "line at all, and neither does the C'tan Shard",
     [s.name for s in ROSTER
      if attached_units.is_attached_unit(s) and s in (dragon, szeras)], [])
c.eq("no TRANSPORT in the list, which is why ai/deployment_ai.py needs no "
     "TRANSPORT_PASSENGER_PRIORITY entry for this army",
     [s.name for s in ROSTER
      if any(getattr(m.profile, "transport", False) for m in s.models)], [])
c.eq("exactly one unit has DEEP STRIKE, so exactly one can start in reserve",
     [s.name for s in ROSTER
      if any(getattr(m.profile, "deep_strike", False) for m in s.models)],
     ["2 C'tan Shard of the Void Dragon 1"])

# The three characters that COULD have led something - pinned so that adding
# an attachment later is a deliberate, visible change rather than a surprise.
c.eq("the Overlord could legally lead the Immortals if the list ever says so",
     attached_units.can_attach(build(nec.OVERLORD, "2 Overlord 2"),
                               build(nec.IMMORTALS, "2 Immortals 2", composition_index=1)), [])
c.eq("...and the Technomancer the Wraiths",
     attached_units.can_attach(build(nec.TECHNOMANCER, "2 Technomancer 2"),
                               build(nec.CANOPTEK_WRAITHS, "2 Canoptek Wraiths 2", composition_index=1)), [])


# --- 4. the army rule reaches every unit ------------------------------------
print("--- 4. Reanimation Protocols ---")

c.eq("every unit in the army has the army rule",
     [s.name for s in ROSTER if not rp.has_reanimation_protocols(s)], [])
c.eq("a fresh, undamaged army can recover nothing - which is exactly why an "
     "undamaged unit no longer rolls at all (see the controller's own gate)",
     sum(rp.recoverable_wounds(s) for s in ROSTER), 0)


# --- 5. the totals, as the LIST's own arithmetic ----------------------------
print("--- 5. totals ---")

c.eq("13 list entries become 10 UNITS after the three attachments",
     len(ROSTER), 10)
c.eq("59 models either way - attaching moves models between units, it does "
     "not add or remove any",
     sum(len(s.models) for s in ROSTER),
     5 + 10 + 20 + 6 + 1 + 6 + 3 + 5 + 3)
c.eq("the engine totals 2000 pts",
     sum(s.points for s in ROSTER),
     345 + 175 + 90 + 55 + 80 + 140 + 190 + 220 + 210 + 170 + 160 + 80 + 85)
c.eq("...against the list's own 2005",
     330 + 165 + 85 + 55 + 80 + 150 + 200 + 220 + 200 + 180 + 165 + 85 + 90, 2005)
# Engine value against the list's own, entry by entry.
PRICES = [
    (345, 330), (175, 165), (90, 85), (55, 55), (80, 80), (140, 150),
    (190, 200), (220, 220), (210, 200), (170, 180), (160, 165), (80, 85), (85, 90),
]
c.eq("TEN of the thirteen entries disagree with the list",
     len([1 for engine, listed in PRICES if engine != listed]), 10)
c.eq("...and exactly three agree",
     len([1 for engine, listed in PRICES if engine == listed]), 3)
c.true("...and the differences run in BOTH directions, which is the second "
       "independent refutation of 'the army app just rounds up'",
       any(e > l for e, l in PRICES) and any(e < l for e, l in PRICES))
c.eq("every unit is priced - an unpriced one would silently rank as "
     "worthless to the AI's damage estimate",
     [s.name for s in ROSTER if s.points is None], [])

c.finish()
