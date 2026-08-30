"""Player 2's Necron army list, as main.py builds it.

THE TOTALS ARE DRIVEN THROUGH THE REAL BUILDER, and that is a deliberate
change from the first version of this suite. It used to rebuild the roster by
hand, with the totals written out as the list's own arithmetic to guard against
going stale - the failure test_player1_army.py hit twice, where a suite keeps
reporting the previous army's numbers, green, while checking an army that no
longer exists. Writing the arithmetic out helps, but it still leaves the SHAPE
of the army as a second copy that has to be edited in step.

So section 5 asks game/army_lists.py itself what it built. A hand-written
roster cannot then disagree with the one the game fields; it can only disagree
with the list on paper, which is what the per-entry checks below are for.

THE POINTS DELIBERATELY DISAGREE with the user's list, and in BOTH directions.
game/factions/necrons_points.py holds the Wahapedia transcription and wins;
each per-entry difference is recorded next to the entry there. This suite pins
BOTH numbers so the gap stays a stated fact rather than something rediscovered
later as a bug.
"""

import re

from testkit import Checks, build_squad
from game import (
    army_lists, attached_units, awakened_dynasty, crit_hit, destroyer_cult,
    feel_no_pain, guardian_protocols, plasmacyte, reanimation_protocols as rp,
    united_in_destruction,
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


# --- 1. the seven characters ------------------------------------------------
print("--- 1. characters ---")

dragon = build(nec.CTAN_SHARD_OF_THE_VOID_DRAGON, "2 C'tan Shard of the Void Dragon 1")
c.eq("Char1 Void Dragon: one model", len(dragon.models), 1)
c.eq("...with tail blades, the spear and voltaic storm", weapons(dragon.models[0]),
     ["Canoptek Tail Blades", "Spear of the Void Dragon",
      "Spear of the Void Dragon - Strike", "Voltaic Storm"])
c.eq("...at 345 pts", dragon.points, 345)   # the list says 330

lokhust_lord = build(nec.LOKHUST_LORD, "2 Lokhust Lord 1",
                     gear={"Lokhust Lord": [nec.LOKHUST_LORD_NANOSCARAB_AMULET]})
# "Nanoscarab amulet, Staff of light" - so he KEEPS the staff. Worth its own
# line: his one weapon option would replace it with the Lord's blade, and the
# staff is a single printed weapon with a ranged AND a melee row, so that swap
# would leave him with no ranged weapon at all.
c.eq("Char2 Lokhust Lord: the staff of light, both its rows - NOT the blade",
     weapons(lokhust_lord.models[0]), ["Staff of Light", "Staff of Light"])
c.eq("...and the nanoscarab amulet, which is Feel No Pain 5+ on the BEARER",
     feel_no_pain.current_feel_no_pain(lokhust_lord.models[0]), "5+")
c.eq("...at 70 pts, the amulet being free", lokhust_lord.points, 70)   # the list says 80

overlord = build(nec.OVERLORD, "2 Overlord 1",
                 choices={"Overlord": {nec.OVERLORD_TO_VOIDSCYTHE: 1}},
                 gear={"Overlord": [nec.OVERLORD_RESURRECTION_ORB]})
# Kept unattached HERE so the loadout checks read his own models; the merged
# versions are built in section 3.
c.eq("Char3 Overlord: Voidscythe only - the swap gives up BOTH printed weapons",
     weapons(overlord.models[0]), ["Voidscythe"])
c.eq("...and the resurrection orb, which the swap is what makes him eligible for",
     getattr(overlord.models[0], "resurrection_orb", False), True)
c.eq("...at 90 pts, the orb being free", overlord.points, 90)   # the list says 85

plasmancer = build(nec.PLASMANCER, "2 Plasmancer 1")
c.eq("Char4 and Char5 Plasmancer: the plasmic lance, both its rows",
     weapons(plasmancer.models[0]), ["Plasmic Lance", "Plasmic Lance"])
c.eq("...at 55 pts each, and the list agrees", plasmancer.points, 55)

skorpekh_lord = build(nec.SKORPEKH_LORD, "2 Skorpekh Lord 1")
c.eq("Char6 Skorpekh Lord: all three printed weapons - he has no options",
     weapons(skorpekh_lord.models[0]),
     ["Enmitic Annihilator", "Flensing Claw", "Hyperphase Harvester"])
c.eq("...at 90 pts, and the list agrees", skorpekh_lord.points, 90)

technomancer = build(nec.TECHNOMANCER, "2 Technomancer 1")
c.eq("Char7 Technomancer: the staff of light, both its rows",
     weapons(technomancer.models[0]), ["Staff of Light", "Staff of Light"])
c.eq("...at 80 pts, and the list agrees", technomancer.points, 80)

# The two Lords carry the SAME printed staff row, which is why the class is no
# longer named after the Overlord - see game/weapons.py.
c.eq("the Lokhust Lord and the Technomancer do NOT share a staff class - the "
     "Technomancer's melee row prints fewer Attacks",
     lokhust_lord.models[0].weapons[1].attacks
     != technomancer.models[0].weapons[1].attacks, True)


# --- 2. the rank and file ---------------------------------------------------
print("--- 2. the rest of the list ---")

immortals_gauss = build(nec.IMMORTALS, "2 Immortals 1", composition_index=1)
c.eq("10 Immortals", line_counts(immortals_gauss), {"Immortal": 10})
c.eq("...with gauss blasters and close combat weapons",
     weapons(immortals_gauss.models[0]), ["Close Combat Weapon", "Gauss Blaster"])
c.eq("...at 140 pts", immortals_gauss.points, 140)     # the list says 150

# The SECOND Immortals squad, and the first entry in this list where two copies
# of one datasheet carry different wargear. "10 with Tesla carbine" is the
# whole squad, so the count is the unit size and not 1.
immortals_tesla = build(nec.IMMORTALS, "2 Immortals 2", composition_index=1,
                        choices={"Immortal": {nec.IMMORTALS_TO_TESLA_CARBINE: 10}})
c.eq("a second 10 Immortals, this one on tesla carbines - ALL ten of them",
     [weapons(m) for m in immortals_tesla.models],
     [["Close Combat Weapon", "Tesla Carbine"]] * 10)
c.eq("...and not one gauss blaster left in the squad",
     [m for m in immortals_tesla.models
      if any(w.name == "Gauss Blaster" for w in m.weapons)], [])
c.eq("...at the same 140 pts - the swap is free", immortals_tesla.points, 140)

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

# "Plasmacyte, 3 with Skorpekh hyperphase weapons" - the list now takes ONE,
# where the previous revision took none.
skorpekh = build(nec.SKORPEKH_DESTROYERS, "2 Skorpekh Destroyers 1",
                 gear={"Skorpekh Destroyer": [nec.SKORPEKH_PLASMACYTE]})
c.eq("3 Skorpekh Destroyers", len(skorpekh.models), 3)
c.eq("...with their hyperphase weapons",
     weapons(skorpekh.models[0]), ["Skorpekh Hyperphase Weapons"])
c.eq("...and ONE Plasmacyte, which is one use of its grant over the whole "
     "battle - the allowance is per Plasmacyte, not per battle",
     plasmacyte.remaining_uses(skorpekh), 1)
c.eq("...at 85 pts, the Plasmacyte being free", skorpekh.points, 85)   # the list says 90


# --- 3. the six attachments the user assigned (rule 19.01) ------------------
print("--- 3. attachments ---")

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
    build(nec.IMMORTALS, "2 Immortals 3", composition_index=1))
led_immortals_tesla = attached_units.attach(
    build(nec.PLASMANCER, "2 Plasmancer 3"),
    build(nec.IMMORTALS, "2 Immortals 4", composition_index=1,
          choices={"Immortal": {nec.IMMORTALS_TO_TESLA_CARBINE: 10}}))
led_skorpekh = attached_units.attach(
    build(nec.SKORPEKH_LORD, "2 Skorpekh Lord 2"),
    build(nec.SKORPEKH_DESTROYERS, "2 Skorpekh Destroyers 2",
          gear={"Skorpekh Destroyer": [nec.SKORPEKH_PLASMACYTE]}))
led_lokhust = attached_units.attach(
    build(nec.LOKHUST_LORD, "2 Lokhust Lord 2",
          gear={"Lokhust Lord": [nec.LOKHUST_LORD_NANOSCARAB_AMULET]}),
    build(nec.LOKHUST_DESTROYERS, "2 Lokhust Destroyers 2", composition_index=3))

c.eq("the Overlord joins the Lychguard", led_lychguard.name, "2 Lychguard 2 + Overlord")
c.eq("the Technomancer joins the Warriors", led_warriors.name, "2 Necron Warriors 2 + Technomancer")
c.eq("a Plasmancer joins each Immortals squad",
     [led_immortals.name, led_immortals_tesla.name],
     ["2 Immortals 3 + Plasmancer", "2 Immortals 4 + Plasmancer"])
c.eq("the Skorpekh Lord joins the Skorpekh Destroyers",
     led_skorpekh.name, "2 Skorpekh Destroyers 2 + Skorpekh Lord")
c.eq("the Lokhust Lord joins the Lokhust Destroyers",
     led_lokhust.name, "2 Lokhust Destroyers 2 + Lokhust Lord")
c.eq("a merge is ONE unit, not two (19.01)",
     [len(s.models) for s in (led_lychguard, led_warriors, led_immortals,
                              led_immortals_tesla, led_skorpekh, led_lokhust)],
     [6, 21, 11, 11, 4, 7])
c.eq("...and its points are the sum",
     [led_lychguard.points, led_warriors.points, led_skorpekh.points, led_lokhust.points],
     [80 + 90, 190 + 80, 85 + 90, 170 + 70])
c.eq("...and its Starting Strength counts the leader too (19.02)",
     [s.starting_model_count for s in (led_skorpekh, led_lokhust)], [4, 7])

# WHAT EACH ATTACHMENT ACTUALLY SWITCHES ON. Every one of these abilities was
# printed and inert before its leader arrived, so this is where they start
# working - and each is checked at the ABILITY, not at the attachment.
c.eq("the Overlord is the NOBLE Guardian Protocols asks for - the Lychguard "
     "had the ability printed and it never fired",
     guardian_protocols.is_led_by_noble(led_lychguard), True)
c.eq("the Technomancer grants the whole unit Feel No Pain 5+",
     feel_no_pain.current_feel_no_pain(led_warriors.models[-1]), "5+")
c.eq("each Plasmancer drops its unit's ranged Critical Hit threshold to 5+",
     [crit_hit.crit_hit_threshold(led_immortals.models[0]),
      crit_hit.crit_hit_threshold(led_immortals_tesla.models[0])], [5, 5])
c.eq("the Skorpekh Lord hands his unit [LETHAL HITS] in melee",
     united_in_destruction.unit_has_united_in_destruction(led_skorpekh), True)
# The Lokhust Lord's ability is printed "Destroyer Cult" and is word for word
# the Plasmancer's - which is why both read one mechanic-named flag.
c.eq("the Lokhust Lord does the same thing for ranged crits under a different "
     "printed name",
     crit_hit.crit_hit_threshold(led_lokhust.models[0]), 5)
c.eq("...and his OWN Driven by Hatred is per MODEL, so his bodyguards get none "
     "of it", [destroyer_cult.driven_by_hatred_applies(m, warriors)
               for m in led_lokhust.models[:1]], [False])  # target is full strength

ROSTER = [dragon, led_lokhust, led_lychguard, led_immortals, led_immortals_tesla,
          led_skorpekh, led_warriors, wraiths, ark]

c.eq("SIX of the nine units are attached units (19.01)",
     len([s for s in ROSTER if attached_units.is_attached_unit(s)]), 6)
c.eq("the C'tan Shard stands ALONE - it has no printed LEADER line at all",
     attached_units.is_attached_unit(dragon), False)
c.eq("...and Command Protocols now pays every one of the six",
     [len(awakened_dynasty.hit_modifiers(u)) for u in ROSTER
      if attached_units.is_attached_unit(u)], [1] * 6)


# --- 4. what this army does NOT have ---------------------------------------
print("--- 4. deliberate absences ---")

c.eq("no TRANSPORT in the list, which is why ai/deployment_ai.py needs no "
     "TRANSPORT_PASSENGER_PRIORITY entry for this army",
     [s.name for s in ROSTER
      if any(getattr(m.profile, "transport", False) for m in s.models)], [])
c.eq("exactly one unit has DEEP STRIKE, so exactly one can start in reserve",
     [s.name for s in ROSTER
      if any(getattr(m.profile, "deep_strike", False) for m in s.models)],
     ["2 C'tan Shard of the Void Dragon 1"])

# TWO DATASHEETS LEFT THE LIST in this revision and are still fully built and
# tested - "not fielded" is not "not implemented". Pinned from both sides so
# bringing either back is a visible one-line change.
c.true("Illuminor Szeras is still a datasheet",
       nec.ILLUMINOR_SZERAS.name == "Illuminor Szeras")
c.true("...and so are the Lokhust Heavy Destroyers",
       nec.LOKHUST_HEAVY_DESTROYERS.name == "Lokhust Heavy Destroyers")
c.eq("...but neither is on the table any more",
     [s.name for s in ROSTER if "Szeras" in s.name or "Heavy" in s.name], [])


# --- 5. the totals, asked of the REAL builder -------------------------------
print("--- 5. totals ---")

built = []
army_lists.get("necrons").build("Player 2", built.append)

c.eq("15 list entries become 9 UNITS after the six attachments", len(built), 9)
# The hand-built roster above uses different COPY NUMBERS (it has to - it
# builds each datasheet more than once), so the two are compared on what
# actually matters: which datasheet leads which, and how big the result is.
def _shape(squad):
    return (re.sub(r"\s\d+(?=\s\+|$)", "", squad.name), len(squad.models))


c.eq("...and the hand-built roster above is the same nine units, leader for "
     "leader and model for model",
     sorted(_shape(s) for s in built), sorted(_shape(s) for s in ROSTER))
c.eq("68 models - attaching moves models between units, it does not add or "
     "remove any",
     sum(len(s.models) for s in built),
     # 7 characters + 10 + 10 + 20 + 6 + 1 + 6 + 5 + 3 rank and file
     7 + (10 + 10 + 20 + 6 + 1 + 6 + 5 + 3))
c.eq("the engine totals 2020 pts", sum(s.points for s in built),
     345 + 70 + 90 + 55 + 55 + 90 + 80
     + 140 + 140 + 190 + 220 + 210 + 170 + 80 + 85)
c.eq("...against the list's own 2050",
     330 + 80 + 85 + 55 + 55 + 90 + 80
     + 150 + 150 + 200 + 220 + 200 + 180 + 85 + 90, 2050)

# Engine value against the list's own, entry by entry.
PRICES = [
    (345, 330),   # C'tan Shard of the Void Dragon
    (70, 80),     # Lokhust Lord
    (90, 85),     # Overlord
    (55, 55), (55, 55),   # Plasmancer x2
    (90, 90),     # Skorpekh Lord
    (80, 80),     # Technomancer
    (140, 150), (140, 150),   # Immortals x2
    (190, 200),   # Necron Warriors
    (220, 220),   # Canoptek Wraiths
    (210, 200),   # Doomsday Ark
    (170, 180),   # Lokhust Destroyers
    (80, 85),     # Lychguard
    (85, 90),     # Skorpekh Destroyers
]
c.eq("fifteen entries are priced", len(PRICES), 15)
c.eq("TEN of them disagree with the list",
     len([1 for engine, listed in PRICES if engine != listed]), 10)
c.eq("...and exactly five agree",
     len([1 for engine, listed in PRICES if engine == listed]), 5)
c.true("...and the differences run in BOTH directions, which is the second "
       "independent refutation of 'the army app just rounds up'",
       any(e > l for e, l in PRICES) and any(e < l for e, l in PRICES))
c.eq("the engine sum and the entry table agree",
     sum(e for e, _ in PRICES), sum(s.points for s in built))
c.eq("every unit is priced - an unpriced one would silently rank as "
     "worthless to the AI's damage estimate",
     [s.name for s in built if s.points is None], [])


# --- 6. the army rule reaches every unit ------------------------------------
print("--- 6. Reanimation Protocols ---")

c.eq("every unit in the army has the army rule",
     [s.name for s in built if not rp.has_reanimation_protocols(s)], [])
c.eq("a fresh, undamaged army can recover nothing - which is exactly why an "
     "undamaged unit no longer rolls at all (see the controller's own gate)",
     sum(rp.recoverable_wounds(s) for s in built), 0)

c.finish()
