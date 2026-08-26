"""Player 2's Ork army list, checked unit by unit against the list the user
supplied - every model line, every weapon, the three attached units, and the
two transport assignments the AI is instructed to honour.

STILL PLAYER 2'S ARMY, just no longer the DEFAULT one: config.PLAYER2_ARMY now
says "necrons", and this list is fielded with `--army2 orks`. Nothing here
changes as a result - the suite builds the roster itself rather than reading
the config, and the Ork army is still built, still fielded and still played by
the AI whenever that flag is passed. See test_player2_necron_army.py for the
list that turns up by default.

Every item on that list is modeled, including the three whose rules arrived
after the datasheets did (the Warboss's Attack Squig, the Battlewagon's Zzap
gun and the Flash Gitz' Ammo Runt) - those have their own suite in
test_ork_wargear.py; here they only have to be present and free.

Builds the roster the same way main() does, rather than driving main()
itself: that keeps the check about WHAT the army is, independent of
deployment, which the Pre-game Sequence now owns.
"""

from testkit import Checks, GameState, build_squad

from game import attached_units
from game import pregame
from game.factions.orks import (
    BATTLEWAGON, BATTLEWAGON_ADD_BIG_SHOOTAS, BATTLEWAGON_ADD_ZZAP_GUN, BATTLEWAGON_ARD_CASE,
    FLASH_GITZ_AMMO_RUNT, WARBOSS_ADD_ATTACK_SQUIG,
    BEAST_SNAGGA_BOYZ, BEASTBOSS, BOYZ, BOYZ_BIG_CHOPPA_TO_POWER_KLAW, DEFF_DREAD, DEFFKOPTAS,
    FLASH_GITZ, GRETCHIN, KILL_RIG, MEGANOBZ, PAINBOY, PAINBOY_GROT_ORDERLY,
    STORMBOYZ, STORMBOYZ_CHOPPA_TO_POWER_KLAW,
    TANKBUSTAS, TANKBUSTAS_ADD_ROKKIT_LAUNCHA, TANKBUSTAS_BOSS_NOB_ADD_SMASH_HAMMER,
    TRUKK, WARBIKERS, WARBIKERS_ADD_POWER_KLAW, WARBOSS, WARBOSS_MEGA_ARMOUR,
)

c = Checks("Player 2 army")


def build(sheet, **kw):
    kw.setdefault("name", sheet.name)
    return build_squad(sheet, "Player 2", **kw)


def weapons(model):
    return sorted(w.name for w in model.weapons)


def line_counts(squad):
    out = {}
    for m in squad.models:
        out[m.profile.name] = out.get(m.profile.name, 0) + 1
    return out


# ---------------------------------------------------------------------------
# 1. Characters
# ---------------------------------------------------------------------------

beastboss = build(BEASTBOSS)
c.eq("Beastboss is one model", len(beastboss.models), 1)
c.eq("Beastboss weapons", weapons(beastboss.models[0]),
     ["Beast Snagga Klaw", "Beastchoppa", "Shoota"])
c.eq("Beastboss points", beastboss.points, 80)  # the list's own 80 pts too

warboss = build(WARBOSS, choices={"Warboss": {WARBOSS_ADD_ATTACK_SQUIG: 1}})
c.eq("Warboss is one model", len(warboss.models), 1)
c.eq("Warboss weapons, Attack Squig included", weapons(warboss.models[0]),
     ["Attack Squig", "Big Choppa", "Kombi-weapon", "Twin Slugga"])
c.eq("the squig is free", warboss.points, build(WARBOSS, name="bare").points)

painboy = build(PAINBOY, gear={"Painboy": [PAINBOY_GROT_ORDERLY]})
c.eq("Painboy is one model", len(painboy.models), 1)
c.eq("Painboy weapons", weapons(painboy.models[0]), ["'Urty Syringe", "Power Klaw"])
c.true("the Grot Orderly is on him", painboy.models[0].grot_orderly)
c.eq("...and it is free", painboy.points, build(PAINBOY, name="bare doc").points)
c.eq("Painboy points", painboy.points, 90)  # the list says 80 - see main.py's note

warboss_mega = build(WARBOSS_MEGA_ARMOUR)
c.eq("Warboss in Mega Armour is one model", len(warboss_mega.models), 1)
c.eq("Warboss in Mega Armour weapons", weapons(warboss_mega.models[0]),
     sorted(["Big Shoota", "'Uge Choppa"]))
c.eq("Warboss in Mega Armour points", warboss_mega.points, 80)  # matches the list


# ---------------------------------------------------------------------------
# 2. Infantry
# ---------------------------------------------------------------------------

bsb = build(BEAST_SNAGGA_BOYZ)
c.eq("Beast Snagga Boyz composition", line_counts(bsb),
     {"Beast Snagga Nob": 1, "Beast Snagga Boy": 9})
c.eq("Nob weapons", weapons(bsb.models[0]), ["Power Snappa", "Slugga"])
c.eq("Boy weapons", weapons(bsb.models[1]), ["Choppa", "Slugga"])

# One 20-strong mob (composition_index=1), not two 10s - and the size is
# load-bearing, see section 4: only a Starting Strength of 20 may take a
# second Leader.
boyz = build(BOYZ, composition_index=1, choices={"Boss Nob": {BOYZ_BIG_CHOPPA_TO_POWER_KLAW: 1}},
             unit_index=1)
c.eq("Boyz is the 20-model build", line_counts(boyz), {"Boss Nob": 1, "Boy": 19})
c.eq("Boyz Boss Nob has the Power Klaw", weapons(boyz.models[0]), ["Power Klaw", "Slugga"])
c.eq("Boyz rank and file", weapons(boyz.models[1]), ["Choppa", "Slugga"])
c.eq("Boyz points", boyz.points, 160)  # the list says 170 - see main.py's note
# The 10-model build stays reachable, which is what makes the new size an
# added composition rather than a replaced one.
c.eq("the 10-model composition still builds", len(build(BOYZ, name="small mob").models), 10)

flash = build(FLASH_GITZ, composition_index=1, gear={"Kaptin": [FLASH_GITZ_AMMO_RUNT]})
c.eq("Flash Gitz is the 10-model build", line_counts(flash), {"Kaptin": 1, "Flash Git": 9})
c.eq("Kaptin weapons", weapons(flash.models[0]), ["Choppa", "Snazzgun"])
c.eq("Flash Git weapons", weapons(flash.models[1]), ["Choppa", "Snazzgun"])
c.eq("exactly one model carries the Ammo Runt",
     sum(1 for m in flash.models if m.ammo_runt), 1)
c.eq("...and it is free (the published list prices no wargear here)",
     flash.points, build(FLASH_GITZ, name="bare gitz", composition_index=1).points)

for idx in (1, 2):
    grots = build(GRETCHIN, unit_index=idx)
    c.eq(f"Gretchin {idx} composition", line_counts(grots), {"Gretchin": 10, "Runtherd": 1})
    c.eq(f"Gretchin {idx} rank and file", weapons(grots.models[0]),
         ["Close Combat Weapon", "Grot Blasta"])
    c.eq(f"Gretchin {idx} Runtherd", weapons(grots.models[10]), ["Grot-Smacka", "Slugga"])

mega = build(MEGANOBZ, composition_index=1)
c.eq("Meganobz is the 6-model build", len(mega.models), 6)
c.eq("Meganobz weapons", weapons(mega.models[0]), ["Kustom Shoota", "Power Klaw"])

storm = build(STORMBOYZ, composition_index=1, choices={"Boss Nob": {STORMBOYZ_CHOPPA_TO_POWER_KLAW: 1}})
c.eq("Stormboyz is the 10-model build", line_counts(storm), {"Boss Nob": 1, "Stormboy": 9})
c.eq("Stormboyz Boss Nob has the Power Klaw", weapons(storm.models[0]), ["Power Klaw", "Slugga"])

tank = build(TANKBUSTAS, choices={
    "Boss Nob": {TANKBUSTAS_BOSS_NOB_ADD_SMASH_HAMMER: 1},
    "Tankbusta": {TANKBUSTAS_ADD_ROKKIT_LAUNCHA: 1},
})
c.eq("Tankbustas composition", line_counts(tank), {"Boss Nob": 1, "Tankbusta": 5})
c.eq("Boss Nob has the Smash Hammer", weapons(tank.models[0]),
     ["Choppa", "Rokkit Pistol", "Smash Hammer"])
doubles = [m for m in tank.models if sum(1 for w in m.weapons if w.name == "Rokkit Launcha") == 2]
c.eq("exactly one Tankbusta has two Rokkit Launchas", len(doubles), 1)

for idx in (1, 2):
    bikes = build(WARBIKERS, composition_index=0,
                  choices={"Boss Nob on Warbike": {WARBIKERS_ADD_POWER_KLAW: 1}}, unit_index=idx)
    c.eq(f"Warbikers {idx} is the 3-model build", len(bikes.models), 3)
    c.eq(f"Warbikers {idx} Boss Nob keeps all three weapons", weapons(bikes.models[0]),
         ["Close Combat Weapon", "Power Klaw", "Twin Dakkagun"])


# ---------------------------------------------------------------------------
# 3. Vehicles
# ---------------------------------------------------------------------------

wagon = build(BATTLEWAGON, gear={"Battlewagon": [BATTLEWAGON_ARD_CASE]},
              choices={"Battlewagon": {BATTLEWAGON_ADD_BIG_SHOOTAS: 1, BATTLEWAGON_ADD_ZZAP_GUN: 1}})
c.eq("Battlewagon weapons", sorted(w.name for w in wagon.models[0].weapons),
     ["Big Shoota"] * 4 + ["Tracks and Wheels", "Zzap Gun"])
c.eq("'Ard Case raised its Toughness", wagon.models[0].profile.toughness, 12)
c.eq("...and removed Firing Deck", wagon.models[0].profile.firing_deck, 0)
c.eq("Battlewagon points", wagon.points, 160)  # matches the list exactly
zzap = next(w for w in wagon.models[0].weapons if w.name == "Zzap Gun")
c.true("the Zzap gun's Strength is a real D6+6 roll", zzap.strength_notation is not None)
c.eq("...and both additions are free", wagon.points, 160)

dread = build(DEFF_DREAD)
c.eq("Deff Dread weapons", sorted(w.name for w in dread.models[0].weapons),
     ["Big Shoota", "Big Shoota", "Dread Klaw", "Dread Klaw", "Stompy Feet"])

koptas = build(DEFFKOPTAS, composition_index=1)
c.eq("Deffkoptas is the 6-model build", line_counts(koptas), {"Deffkopta": 6})
c.eq("Deffkopta weapons", weapons(koptas.models[0]),
     ["Kopta Rokkits", "Slugga", "Spinnin' Blades"])
c.true("...and every model carries the same three",
       all(weapons(m) == weapons(koptas.models[0]) for m in koptas.models))
c.eq("Deffkoptas points", koptas.points, 140)  # the list says 160 - see main.py's note
# The 3-model build stays reachable, which is what makes the new size an
# added composition rather than a replaced one.
c.eq("the 3-model composition still builds", len(build(DEFFKOPTAS, name="small koptas").models), 3)
c.eq("...and is priced separately", build(DEFFKOPTAS, name="small koptas 2").points, 75)

rig = build(KILL_RIG)
c.eq("Kill Rig weapons", sorted(w.name for w in rig.models[0].weapons),
     ["'Eavy Lobba", "Butcha Boyz", "Savage Horns and Hooves", "Saw Blades",
      "Stikka Kannon", "Wurrtower"])

# No Trukk on this list any more - the two that used to carry the Boyz mobs
# are gone with them. The datasheet is still used further down as the A/B
# foil for the transport-hint checks, which is a different question from
# whether the army fields one.


# ---------------------------------------------------------------------------
# 4. The three attached units (19.01), including the two-Leader mob
# ---------------------------------------------------------------------------

state = GameState()
bsb_unit = attached_units.attach(build(BEASTBOSS), build(BEAST_SNAGGA_BOYZ), game_state=state)
c.eq("Beastboss + Beast Snagga Boyz is one 11-model unit", len(bsb_unit.models), 11)
c.eq("...and its points are the sum", bsb_unit.points, 80 + 90)

mega_unit = attached_units.attach(build(WARBOSS_MEGA_ARMOUR),
                                  build(MEGANOBZ, composition_index=1), game_state=state)
c.eq("Warboss in Mega Armour + Meganobz is one 7-model unit", len(mega_unit.models), 7)

def boyz20(name="mob"):
    return build(BOYZ, name=name, composition_index=1,
                 choices={"Boss Nob": {BOYZ_BIG_CHOPPA_TO_POWER_KLAW: 1}})


boyz_unit = attached_units.attach(build(WARBOSS), boyz20("mob A"), game_state=state)
c.eq("Warboss + 20 Boyz is one 21-model unit", len(boyz_unit.models), 21)
# Boyz' "Bodyguard" ability: a SECOND Leader, allowed only because the mob
# has a Starting Strength of 20 and one of the two is a WARBOSS.
c.eq("...and the Painboy may join it as a second Leader",
     attached_units.can_attach(build(PAINBOY, name="doc A"), boyz_unit), [])
boyz_unit = attached_units.attach(build(PAINBOY, name="doc A2"), boyz_unit, game_state=state)
c.eq("Warboss + Painboy + 20 Boyz is one 22-model unit", len(boyz_unit.models), 22)
c.eq("...and it is one unit with three components",
     len(attached_units.components(boyz_unit)), 3)

# Each of the ability's own conditions, isolated - every one of these fails
# ONLY on the clause named, with the others satisfied.
small = attached_units.attach(build(WARBOSS, name="wb small"),
                              build(BOYZ, name="mob 10",
                                    choices={"Boss Nob": {BOYZ_BIG_CHOPPA_TO_POWER_KLAW: 1}}),
                              game_state=GameState())
c.true("a 10-model mob may NOT take a second Leader (Starting Strength 20 only)",
       attached_units.can_attach(build(PAINBOY, name="doc B"), small))
no_boss = attached_units.attach(build(PAINBOY, name="doc C"), boyz20("mob C"),
                                game_state=GameState())
c.true("two Leaders with NO Warboss among them is refused",
       attached_units.can_attach(build(PAINBOY, name="doc D"), no_boss))
c.eq("...while the same mob still accepts the Warboss himself",
     attached_units.can_attach(build(WARBOSS, name="wb C"), no_boss), [])
three = attached_units.attach(build(PAINBOY, name="doc E"),
                              attached_units.attach(build(WARBOSS, name="wb E"), boyz20("mob E"),
                                                    game_state=GameState()),
                              game_state=GameState())
c.true("a THIRD Leader is refused (\"up to two\")",
       attached_units.can_attach(build(PAINBOY, name="doc F"), three))
# A/B: nothing about this widens the rule for a datasheet without the ability.
big_bsb = attached_units.attach(build(WARBOSS_MEGA_ARMOUR, name="wbma X"),
                                build(MEGANOBZ, name="meg X", composition_index=1),
                                game_state=GameState())
c.true("a datasheet without Bodyguard still allows only one Leader",
       attached_units.can_attach(build(WARBOSS_MEGA_ARMOUR, name="wbma Y"), big_bsb))

# Every pairing is legal per the published Leader table, and the wrong ones
# are refused - the reason attach() accepted the three above.
c.true("Beastboss may not lead plain Boyz",
       attached_units.can_attach(build(BEASTBOSS), build(BOYZ)))
c.true("the plain Warboss may not lead Beast Snagga Boyz",
       attached_units.can_attach(build(WARBOSS), build(BEAST_SNAGGA_BOYZ)))
c.true("the Mega Armour Warboss may not lead Boyz",
       attached_units.can_attach(build(WARBOSS_MEGA_ARMOUR), build(BOYZ)))


# ---------------------------------------------------------------------------
# 5. The two instructed transport assignments
# ---------------------------------------------------------------------------

from game import formations  # noqa: E402

rig_token = build(KILL_RIG).models[0]
wagon_token = build(BATTLEWAGON, gear={"Battlewagon": [BATTLEWAGON_ARD_CASE]}).models[0]
trukk_token = build(TRUKK).models[0]

c.eq("Beast Snagga Boyz + Beastboss fit in the Kill Rig",
     formations.embark_errors(bsb_unit, rig_token), [])
c.eq("Meganobz + Warboss in Mega Armour fit in the Battlewagon",
     formations.embark_errors(mega_unit, wagon_token), [])
# Both fits are tight enough to be worth pinning down.
c.eq("...the Kill Rig is exactly full (11 of 11)",
     formations.transport_capacity_used(rig_token, [bsb_unit]), 11)
c.eq("...and the Battlewagon is at 14 of 22 (MEGA ARMOUR costs 2 each)",
     formations.transport_capacity_used(wagon_token, [mega_unit]), 14)

# The Kill Rig would REFUSE the Meganobz (not BEAST SNAGGA) - which is what
# makes the two assignments the only legal pairing, not just a preference.
c.true("the Kill Rig refuses the Meganobz", formations.embark_errors(mega_unit, rig_token))
c.true("a Trukk cannot take the Meganobz unit either (14 > capacity 12)",
       formations.embark_errors(mega_unit, trukk_token))

# The AI honours a scene hint exclusively: a hinted unit must not be swallowed
# by some other transport that happens to be processed first.
from ai.deployment_ai import _transport_affinity  # noqa: E402

hints = {id(bsb_unit): (pregame.EMBARK, rig_token)}
# Asserted as "tier 0" rather than as a literal tuple: the tier is what "the
# hint outranks everything else" actually means, and the rest of the tuple is
# an internal tie-break shape (see _transport_affinity).
c.eq("the hinted unit ranks top for its own transport",
     _transport_affinity(bsb_unit, rig_token, hints)[0], 0)
c.eq("...and is refused by any other transport",
     _transport_affinity(bsb_unit, trukk_token, hints), None)

# The A/B has to use a unit a Trukk would genuinely want, or "refused" proves
# nothing: the Beast Snagga unit is not on a Trukk's passenger priority list at
# all (see TRANSPORT_PASSENGER_PRIORITY) and so is turned away regardless of any
# hint. Plain Boyz are the real case - a Trukk's second choice, and the exact
# unit that would otherwise be swallowed.
plain_boyz = build(BOYZ, choices={"Boss Nob": {BOYZ_BIG_CHOPPA_TO_POWER_KLAW: 1}})
c.true("A/B: unhinted, a Trukk would happily take a Boyz mob",
       _transport_affinity(plain_boyz, trukk_token, {}) is not None)
c.eq("...but hinted at the Battlewagon, that same Trukk refuses it",
     _transport_affinity(plain_boyz, trukk_token,
                         {id(plain_boyz): (pregame.EMBARK, wagon_token)}), None)
c.eq("...while the Battlewagon still ranks it top",
     _transport_affinity(plain_boyz, wagon_token,
                         {id(plain_boyz): (pregame.EMBARK, wagon_token)})[0], 0)


# ---------------------------------------------------------------------------
# 6. Roster shape and total
# ---------------------------------------------------------------------------

# Built exactly as main() builds them, so the total is the engine's own
# answer rather than a number retyped here.
ROSTER = [
    attached_units.attach(build(BEASTBOSS), build(BEAST_SNAGGA_BOYZ), game_state=GameState()),
    attached_units.attach(
        build(PAINBOY, name="roster doc", gear={"Painboy": [PAINBOY_GROT_ORDERLY]}),
        attached_units.attach(
            build(WARBOSS, name="roster boss",
                  choices={"Warboss": {WARBOSS_ADD_ATTACK_SQUIG: 1}}),
            build(BOYZ, name="roster mob", composition_index=1,
                  choices={"Boss Nob": {BOYZ_BIG_CHOPPA_TO_POWER_KLAW: 1}}, unit_index=1),
            game_state=GameState()),
        game_state=GameState()),
    build(BATTLEWAGON, gear={"Battlewagon": [BATTLEWAGON_ARD_CASE]},
          choices={"Battlewagon": {BATTLEWAGON_ADD_BIG_SHOOTAS: 1, BATTLEWAGON_ADD_ZZAP_GUN: 1}}),
    build(DEFF_DREAD),
    build(DEFFKOPTAS, composition_index=1),
    build(FLASH_GITZ, composition_index=1, gear={"Kaptin": [FLASH_GITZ_AMMO_RUNT]}),
    build(GRETCHIN, unit_index=1),
    build(GRETCHIN, unit_index=2),
    build(KILL_RIG),
    attached_units.attach(build(WARBOSS_MEGA_ARMOUR), build(MEGANOBZ, composition_index=1),
                          game_state=GameState()),
    build(STORMBOYZ, composition_index=1, choices={"Boss Nob": {STORMBOYZ_CHOPPA_TO_POWER_KLAW: 1}}),
    build(TANKBUSTAS, choices={
        "Boss Nob": {TANKBUSTAS_BOSS_NOB_ADD_SMASH_HAMMER: 1},
        "Tankbusta": {TANKBUSTAS_ADD_ROKKIT_LAUNCHA: 1},
    }),
    build(WARBIKERS, composition_index=0,
          choices={"Boss Nob on Warbike": {WARBIKERS_ADD_POWER_KLAW: 1}}, unit_index=1),
    build(WARBIKERS, composition_index=0,
          choices={"Boss Nob on Warbike": {WARBIKERS_ADD_POWER_KLAW: 1}}, unit_index=2),
]
c.eq("the army is 14 units after attaching", len(ROSTER), 14)
c.true("every unit is priced", all(s.points is not None for s in ROSTER))
# The engine's own total, from this project's transcribed published list. The
# user's list totals higher unit by unit (a newer revision) - recorded in
# main.py's own note, with the transcribed data left as the source of truth.
c.eq("engine total", sum(s.points for s in ROSTER), 1935)
c.eq("model count", sum(len(s.models) for s in ROSTER), 103)

c.finish()
