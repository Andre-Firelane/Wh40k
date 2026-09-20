"""The Ork army list "Mecha Orks", checked unit by unit against the export the
user supplied - every model line, every weapon, the three attached units, and
the three transport assignments the AI is instructed to honour.

STILL PLAYER 2'S ARMY, just no longer the DEFAULT one: config.PLAYER2_ARMY says
"necrons", and this list is fielded with `--army2 orks`. Nothing here changes as
a result - the suite builds the roster itself rather than reading the config,
and the Ork army is still built, still fielded and still played by the AI
whenever that flag is passed. See test_player2_necron_army.py for the list that
turns up by default.

REPLACED WHOLESALE on 2026-09-20 (Mecha Orks G6). The list the user exported
fields three detachments at exactly the 3 DP budget and four Enhancements that
are actually carried, and it drops eight entries the old roster had (Warbikers,
Stormboyz, Flash Gitz, Tankbustas, Deff Dread, a second Gretchin mob, the
Painboy, the Warboss in Mega Armour) for seven it did not (Ghazghkull, a
Bigboss, a Big Mek in Mega Armour, a Weirdboy, a Gunwagon, a second Beast Snagga
mob, a ten-Boy mob). Those datasheets are still built and still tested - by
their own suites (test_ork_specialists.py, test_ork_vehicles.py, test_ork_mobs.py,
test_ork_characters.py); what moved is which of them this LIST fields. That is
the whole reason this file exists: a suite that builds its own roster stays green
while checking an army nobody plays, so section 6 compares the hand-built roster
against armies/orks.json's own build.

Builds the roster the same way main() does, rather than driving main() itself:
that keeps the check about WHAT the army is, independent of deployment, which
the Pre-game Sequence now owns.

THE ENHANCEMENTS ARE NOT BUILT HERE. build_squad() takes datasheets and wargear;
an Enhancement is granted by the roster builder in its second pass
(game/army_roster.py), so the hand-built units below are the plain ones and
section 6 compares MODEL LINES and points of the plain build. The four the list
buys - Ferocious Show-off, 'Ardboyz, Boss Boomer, Targetin' Gizmos - are checked
where they are wired (test_ork_green_tide.py, test_ork_blitz_brigade.py) and
that the LIST names them is checked in section 6.
"""

from testkit import Checks, GameState, build_squad

from game import attached_units
from game import pregame
from game.factions.orks import (
    BATTLEWAGON, BATTLEWAGON_ADD_BIG_SHOOTAS, BATTLEWAGON_ADD_GRABBIN_KLAW,
    BATTLEWAGON_ADD_WRECKIN_BALL,
    BEAST_SNAGGA_BOYZ, BEASTBOSS, BIG_MEK_MA_TELLYPORT_BLASTA, BIG_MEK_MEGA_ARMOUR, BIGBOSS,
    BOYZ, BOYZ_BIG_SHOOTA, BOYZ_BURNA, BOYZ_ROKKIT_LAUNCHA,
    BOYZ_NOB_TO_BIG_CHOPPA, BOYZ_NOB_TO_POWER_KLAW,
    DEFFKOPTAS, GHAZGHKULL_THRAKA, GRETCHIN, GUNWAGON,
    GUNWAGON_ADD_BIG_SHOOTAS, GUNWAGON_ADD_GRABBIN_KLAW, GUNWAGON_ADD_LOBBA,
    GUNWAGON_ADD_WRECKIN_BALL, GUNWAGON_KANNON_TO_ZZAP_GUN,
    KILL_RIG, MEGANOBZ, MEGANOBZ_KUSTOM_SHOOTA_TO_KOMBI_WEAPON, TRUKK, WARBOSS,
    WARBOSS_KUSTOM_CHOPPA_TO_POWER_KLAW, WARBOSS_KUSTOM_SHOOTA_TO_KOMBI_SKORCHA, WEIRDBOY,
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


# The list's own wargear, in one place: every entry below and the roster in
# section 6 build from these, so the two cannot drift apart.
BOYZ_20_CHOICES = {
    "Nob": {BOYZ_NOB_TO_POWER_KLAW: 1, BOYZ_NOB_TO_BIG_CHOPPA: 1},
    "Boy": {BOYZ_BIG_SHOOTA: 2, BOYZ_ROKKIT_LAUNCHA: 2, BOYZ_BURNA: 2},
}
BOYZ_10_CHOICES = {
    "Nob": {BOYZ_NOB_TO_POWER_KLAW: 1},
    "Boy": {BOYZ_BIG_SHOOTA: 1, BOYZ_ROKKIT_LAUNCHA: 1, BOYZ_BURNA: 1},
}
WARBOSS_CHOICES = {"Warboss": {WARBOSS_KUSTOM_CHOPPA_TO_POWER_KLAW: 1,
                               WARBOSS_KUSTOM_SHOOTA_TO_KOMBI_SKORCHA: 1}}
BIG_MEK_CHOICES = {"Big Mek in Mega Armour": {"Kustom Shoota -> Kustom Mega-blasta": 1,
                                              BIG_MEK_MA_TELLYPORT_BLASTA: 1}}
MEGANOBZ_CHOICES = {"Meganob": {MEGANOBZ_KUSTOM_SHOOTA_TO_KOMBI_WEAPON: 3}}
BATTLEWAGON_CHOICES = {"Battlewagon": {BATTLEWAGON_ADD_WRECKIN_BALL: 1,
                                       BATTLEWAGON_ADD_BIG_SHOOTAS: 1,
                                       BATTLEWAGON_ADD_GRABBIN_KLAW: 1}}
GUNWAGON_CHOICES = {"Gunwagon": {GUNWAGON_KANNON_TO_ZZAP_GUN: 1, GUNWAGON_ADD_LOBBA: 1,
                                 GUNWAGON_ADD_BIG_SHOOTAS: 1, GUNWAGON_ADD_WRECKIN_BALL: 1,
                                 GUNWAGON_ADD_GRABBIN_KLAW: 1}}


# ---------------------------------------------------------------------------
# 1. Characters
# ---------------------------------------------------------------------------

warboss = build(WARBOSS, choices=WARBOSS_CHOICES)
c.eq("Warboss is one model", len(warboss.models), 1)
c.eq("Warboss weapons - the export's Power Klaw and Kombi-skorcha",
     weapons(warboss.models[0]), ["Kombi-skorcha - Shoota", "Power Klaw"])
c.eq("Warboss points", warboss.points, 100)

bigboss = build(BIGBOSS)
c.eq("Bigboss is one model", len(bigboss.models), 1)
c.eq("Bigboss weapons", weapons(bigboss.models[0]), ["Big Choppa", "Slugga"])
c.eq("Bigboss points (the export's 65 is this plus Ferocious Show-off's 15)",
     bigboss.points, 50)

big_mek = build(BIG_MEK_MEGA_ARMOUR, choices=BIG_MEK_CHOICES)
c.eq("Big Mek in Mega Armour is one model", len(big_mek.models), 1)
c.eq("Big Mek weapons - the export's three",
     weapons(big_mek.models[0]), ["Kustom Mega-blasta", "Power Klaw", "Tellyport Blasta"])
c.eq("Big Mek points (both choices are free)", big_mek.points, 90)

beastboss = build(BEASTBOSS)
c.eq("Beastboss is one model", len(beastboss.models), 1)
c.eq("Beastboss weapons", weapons(beastboss.models[0]),
     ["Beast Snagga Klaw and Beastchoppa", "Shoota"])
c.eq("Beastboss points", beastboss.points, 85)

weirdboy = build(WEIRDBOY)
c.eq("Weirdboy is one model", len(weirdboy.models), 1)
c.eq("Weirdboy weapons", weapons(weirdboy.models[0]), ["Copper Staff", "Power Vomit"])
c.eq("Weirdboy points", weirdboy.points, 65)

ghaz = build(GHAZGHKULL_THRAKA)
c.eq("Ghazghkull Thraka is one model", len(ghaz.models), 1)
c.eq("Ghazghkull weapons", weapons(ghaz.models[0]),
     ["Adamantine 'Eadbutt", "Gork's Klaw", "Mork's Roar - Aimed"])
c.eq("Ghazghkull points", ghaz.points, 300)


# ---------------------------------------------------------------------------
# 2. Infantry
# ---------------------------------------------------------------------------

boyz = build(BOYZ, composition_index=1, choices=BOYZ_20_CHOICES, unit_index=1)
c.eq("Boyz is the 20-model build", line_counts(boyz), {"Nob": 2, "Boy": 18})
c.eq("one Nob has the Power Klaw", weapons(boyz.models[1]),
     ["Kombi-skorcha - Shoota", "Power Klaw"])
c.eq("...and the other the Big Choppa, which costs it the Kombi-skorcha too",
     weapons(boyz.models[0]), ["Big Choppa"])
c.eq("two Boyz carry a Big Shoota", weapons(boyz.models[2]),
     ["Big Shoota", "Choppa", "Slugga"])
c.eq("two a Rokkit Launcha", weapons(boyz.models[4]),
     ["Choppa", "Rokkit Launcha - Blasta", "Slugga"])
c.eq("two a Burna", weapons(boyz.models[6]), ["Burna", "Choppa", "Slugga"])
c.eq("and the other twelve their Shoota", weapons(boyz.models[8]),
     ["Choppa", "Shoota", "Slugga"])
c.eq("Boyz points", boyz.points, 180)

small_mob = build(BOYZ, name="small mob", choices=BOYZ_10_CHOICES, unit_index=2)
c.eq("the second mob is the 10-model build", line_counts(small_mob), {"Nob": 1, "Boy": 9})
c.eq("its Nob has the Power Klaw", weapons(small_mob.models[0]),
     ["Kombi-skorcha - Shoota", "Power Klaw"])
c.eq("its points (the export's 115 is this plus 'Ardboyz' 25)", small_mob.points, 90)

for idx in (1, 2):
    bsb = build(BEAST_SNAGGA_BOYZ, name="bsb %d" % idx, unit_index=idx)
    # The Nob's PROFILE keeps its datasheet-qualified name (game/sprites.py keys
    # its art on it), while its model line is plain "Nob" - line_counts() reads
    # the profile.
    c.eq("Beast Snagga Boyz %d composition" % idx, line_counts(bsb),
         {"Beast Snagga Nob": 1, "Beast Snagga Boy": 9})
    c.eq("Nob weapons %d" % idx, weapons(bsb.models[0]), ["Power Snappa", "Slugga"])
    c.eq("Boy weapons %d" % idx, weapons(bsb.models[1]), ["Choppa - Standard", "Slugga"])
    c.eq("Beast Snagga Boyz %d points" % idx, bsb.points, 85)

# composition_index 1: the codex prices 2, 3, 5 and 6 Meganobz, in that order,
# and this list buys three.
mega = build(MEGANOBZ, composition_index=1, choices=MEGANOBZ_CHOICES)
c.eq("Meganobz is the 3-model build", line_counts(mega), {"Meganob": 3})
c.eq("each swapped its Kustom Shoota for a Kombi-weapon",
     weapons(mega.models[0]), ["Kombi-weapon - Shoota", "Power Klaw"])
c.true("...all three of them",
       all(weapons(m) == weapons(mega.models[0]) for m in mega.models))
c.eq("Meganobz points", mega.points, 110)

# The codex took the Runtherd out of this datasheet (it is a SUPPORT unit of
# its own now), so the mob is ten Gretchin and nothing else.
grots = build(GRETCHIN)
c.eq("Gretchin composition - no Runtherd", line_counts(grots), {"Gretchin": 10})
c.true("every Grot carries the same loadout",
       all(weapons(m) == weapons(grots.models[0]) for m in grots.models))
c.eq("Gretchin weapons", weapons(grots.models[0]), ["Grot Blasta", "Scavenged Shivs"])
c.eq("Gretchin points", grots.points, 45)


# ---------------------------------------------------------------------------
# 3. Vehicles
# ---------------------------------------------------------------------------

for idx in (1, 2):
    koptas = build(DEFFKOPTAS, name="koptas %d" % idx, unit_index=idx)
    c.eq("Deffkoptas %d is the 3-model build" % idx, line_counts(koptas), {"Deffkopta": 3})
    c.eq("Deffkopta weapons %d (the Rokkit Launcha's first profile stands for both)" % idx,
         weapons(koptas.models[0]),
         ["Choppa", "Rokkit Launcha - Blasta", "Slugga", "Spinnin' Blades"])
    c.eq("Deffkoptas %d points" % idx, koptas.points, 80)

wagon = build(BATTLEWAGON, choices=BATTLEWAGON_CHOICES)
c.eq("Battlewagon weapons - four Big Shootas and the two free add-ons",
     sorted(w.name for w in wagon.models[0].weapons),
     ["Big Shoota"] * 4 + ["Crushin' Bulk", "Grabbin' Klaw", "Wreckin' Ball"])
c.eq("Battlewagon points (every add-on is free; the export's 160 is this plus "
     "Boss Boomer's 10)", wagon.points, 150)

gun = build(GUNWAGON, choices=GUNWAGON_CHOICES)
c.eq("Gunwagon weapons - the Zzap Gun in place of the Kannon, plus the free four",
     sorted(w.name for w in gun.models[0].weapons),
     ["Big Shoota"] * 4 + ["Crushin' Bulk", "Grabbin' Klaw", "Lobba", "Wreckin' Ball", "Zzap Gun"])
c.eq("Gunwagon points (150 + 10 for the Zzap Gun; the export's 170 is this plus "
     "Targetin' Gizmos' 10)", gun.points, 160)

rig = build(KILL_RIG)
c.eq("Kill Rig weapons (2026-09 codex)", sorted(w.name for w in rig.models[0].weapons),
     ["'Eavy Lobba", "Butcha Boyz", "Savage Horns and Hooves", "Saw Blades",
      "Stikka Kannon", "Wurrtower"])
c.eq("Kill Rig points", rig.points, 175)

# No Trukk on this list - the datasheet is still used further down as the A/B
# foil for the transport-hint checks, which is a different question from
# whether the army fields one.


# ---------------------------------------------------------------------------
# 4. The three attached units (19.01), two of them Leader + Support
# ---------------------------------------------------------------------------

state = GameState()

c.eq("the Warboss attaches as a Leader",
     attached_units.attachment_role(build(WARBOSS, name="wb role")), attached_units.LEADER)
c.eq("the Bigboss attaches as a Support unit",
     attached_units.attachment_role(build(BIGBOSS, name="bb role")), attached_units.SUPPORT)
c.eq("the Weirdboy too",
     attached_units.attachment_role(build(WEIRDBOY, name="wz role")), attached_units.SUPPORT)
c.eq("the Big Mek in Mega Armour leads",
     attached_units.attachment_role(build(BIG_MEK_MEGA_ARMOUR, name="bm role")),
     attached_units.LEADER)
c.eq("Ghazghkull joins nothing - he is his own unit",
     attached_units.attachment_role(build(GHAZGHKULL_THRAKA, name="ghaz role")), None)


def boyz20(name="mob"):
    return build(BOYZ, name=name, composition_index=1, choices=BOYZ_20_CHOICES)


def boyz10(name="mob 10"):
    return build(BOYZ, name=name, choices=BOYZ_10_CHOICES)


boyz_unit = attached_units.attach(build(WARBOSS, name="roster boss", choices=WARBOSS_CHOICES),
                                  boyz20("mob A"), game_state=state)
c.eq("Warboss + 20 Boyz is one 21-model unit", len(boyz_unit.models), 21)
c.eq("...and the Bigboss may join it as its Support unit",
     attached_units.can_attach(build(BIGBOSS, name="bb A"), boyz_unit), [])
boyz_unit = attached_units.attach(build(BIGBOSS, name="bb A2"), boyz_unit, game_state=state)
c.eq("Warboss + Bigboss + 20 Boyz is one 22-model unit", len(boyz_unit.models), 22)
c.eq("...and it is one unit with three components",
     len(attached_units.components(boyz_unit)), 3)
c.eq("...priced as the sum of the three (the export's 345 adds Ferocious Show-off)",
     boyz_unit.points, 100 + 50 + 180)

mega_unit = attached_units.attach(build(BIG_MEK_MEGA_ARMOUR, name="bm unit", choices=BIG_MEK_CHOICES),
                                  build(MEGANOBZ, name="meg unit", composition_index=1,
                                        choices=MEGANOBZ_CHOICES),
                                  game_state=state)
c.eq("Big Mek in Mega Armour + 3 Meganobz is one 4-model unit", len(mega_unit.models), 4)
c.eq("...and its points are the sum", mega_unit.points, 90 + 110)

bsb_unit = attached_units.attach(build(BEASTBOSS, name="bboss unit"),
                                 build(BEAST_SNAGGA_BOYZ, name="bsb unit"), game_state=state)
c.eq("Beastboss + Beast Snagga Boyz is one 11-model unit", len(bsb_unit.models), 11)
c.eq("...and the Weirdboy may join it as its Support unit",
     attached_units.can_attach(build(WEIRDBOY, name="wz A"), bsb_unit), [])
bsb_unit = attached_units.attach(build(WEIRDBOY, name="wz A2"), bsb_unit, game_state=state)
c.eq("Beastboss + Weirdboy + Beast Snagga Boyz is one 12-model unit", len(bsb_unit.models), 12)
c.eq("...and its points are the sum", bsb_unit.points, 85 + 65 + 85)

# Each of 19.01's own limits, isolated - every refusal below fails ONLY on the
# slot named, with the other slot free.
small = attached_units.attach(build(WARBOSS, name="wb small"), boyz10(), game_state=GameState())
c.eq("a 10-model mob takes the Bigboss too (no Starting Strength clause any more)",
     attached_units.can_attach(build(BIGBOSS, name="bb B"), small), [])
led = attached_units.attach(build(WARBOSS, name="wb C"), boyz20("mob C"), game_state=GameState())
c.true("a SECOND Leader is refused, even on a 20-model mob with a Warboss (Bodyguard is gone)",
       attached_units.can_attach(build(WARBOSS, name="wb D"), led))
supported = attached_units.attach(build(BIGBOSS, name="bb C"), boyz20("mob D"),
                                  game_state=GameState())
c.true("a SECOND Support unit is refused",
       attached_units.can_attach(build(BIGBOSS, name="bb D"), supported))
c.eq("...while the same mob still accepts the Warboss as its Leader",
     attached_units.can_attach(build(WARBOSS, name="wb E"), supported), [])
three = attached_units.attach(build(BIGBOSS, name="bb E"),
                              attached_units.attach(build(WARBOSS, name="wb F"), boyz20("mob E"),
                                                    game_state=GameState()),
                              game_state=GameState())
c.true("a THIRD character is refused - as a Support unit",
       attached_units.can_attach(build(BIGBOSS, name="bb F"), three))
c.true("...and as a Leader",
       attached_units.can_attach(build(WARBOSS, name="wb G"), three))

# Every pairing is legal per the published Leader table, and the wrong ones
# are refused - the reason attach() accepted the three above.
c.true("Beastboss may not lead plain Boyz",
       attached_units.can_attach(build(BEASTBOSS, name="bb lead"), build(BOYZ, name="plain boyz")))
c.true("the plain Warboss may not lead Beast Snagga Boyz",
       attached_units.can_attach(build(WARBOSS, name="wb lead"),
                                 build(BEAST_SNAGGA_BOYZ, name="plain bsb")))
c.true("the Big Mek in Mega Armour may not lead Boyz",
       attached_units.can_attach(build(BIG_MEK_MEGA_ARMOUR, name="bm lead"),
                                 build(BOYZ, name="plain boyz 2")))


# ---------------------------------------------------------------------------
# 5. The three instructed transport assignments
# ---------------------------------------------------------------------------

from game import formations  # noqa: E402

rig_token = build(KILL_RIG, name="rig token").models[0]
wagon_token = build(BATTLEWAGON, name="wagon token", choices=BATTLEWAGON_CHOICES).models[0]
gun_token = build(GUNWAGON, name="gun token", choices=GUNWAGON_CHOICES).models[0]
trukk_token = build(TRUKK, name="trukk token").models[0]

plain_bsb = build(BEAST_SNAGGA_BOYZ, name="plain bsb ride")
c.eq("Warboss + Bigboss + Boyz fit in the Battlewagon",
     formations.embark_errors(boyz_unit, wagon_token), [])
c.eq("Big Mek + Meganobz fit in the Gunwagon",
     formations.embark_errors(mega_unit, gun_token), [])
c.eq("the plain Beast Snagga mob fits in the Kill Rig",
     formations.embark_errors(plain_bsb, rig_token), [])
# Two of the three fits are tight enough to be worth pinning down.
c.eq("...the Battlewagon is FULL at 22 of 22",
     formations.transport_capacity_used(wagon_token, [boyz_unit]), 22)
c.eq("...the Gunwagon at 8 of 12 (MEGA ARMOUR costs 2 each)",
     formations.transport_capacity_used(gun_token, [mega_unit]), 8)
c.eq("...and the Kill Rig at 10 of 12", formations.transport_capacity_used(rig_token, [plain_bsb]), 10)

# The Kill Rig would REFUSE the OTHER Beast Snagga unit, because the Weirdboy
# leading it is no BEAST SNAGGA - which is why the list rides the plain mob
# rather than the led one, and why this is a rule rather than a preference.
c.true("the Kill Rig refuses the mob the Weirdboy joined",
       formations.embark_errors(bsb_unit, rig_token))
c.true("...and the Meganobz unit as well", formations.embark_errors(mega_unit, rig_token))

# The AI honours a scene hint exclusively: a hinted unit must not be swallowed
# by some other transport that happens to be processed first.
from ai.deployment_ai import _transport_affinity  # noqa: E402

hints = {id(plain_bsb): (pregame.EMBARK, rig_token)}
# Asserted as "tier 0" rather than as a literal tuple: the tier is what "the
# hint outranks everything else" actually means, and the rest of the tuple is
# an internal tie-break shape (see _transport_affinity).
c.eq("the hinted unit ranks top for its own transport",
     _transport_affinity(plain_bsb, rig_token, hints)[0], 0)
c.eq("...and is refused by any other transport",
     _transport_affinity(plain_bsb, trukk_token, hints), None)

# The A/B has to use a unit a Trukk would genuinely want, or "refused" proves
# nothing: the Beast Snagga unit is not on a Trukk's passenger priority list at
# all (see TRANSPORT_PASSENGER_PRIORITY) and so is turned away regardless of any
# hint. Plain Boyz are the real case - a Trukk's second choice, and the exact
# unit that would otherwise be swallowed.
plain_boyz = boyz10("plain mob")
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
    build(BATTLEWAGON, name="roster wagon", choices=BATTLEWAGON_CHOICES),
    attached_units.attach(
        build(BIGBOSS, name="roster bigboss"),
        attached_units.attach(
            build(WARBOSS, name="roster warboss", choices=WARBOSS_CHOICES),
            build(BOYZ, name="roster mob", composition_index=1,
                  choices=BOYZ_20_CHOICES, unit_index=1),
            game_state=GameState()),
        game_state=GameState()),
    build(GUNWAGON, name="roster gunwagon", choices=GUNWAGON_CHOICES),
    attached_units.attach(
        build(BIG_MEK_MEGA_ARMOUR, name="roster bigmek", choices=BIG_MEK_CHOICES),
        build(MEGANOBZ, name="roster meganobz", composition_index=1, choices=MEGANOBZ_CHOICES),
        game_state=GameState()),
    build(KILL_RIG, name="roster rig"),
    build(BEAST_SNAGGA_BOYZ, name="roster bsb 1", unit_index=1),
    attached_units.attach(
        build(WEIRDBOY, name="roster weirdboy"),
        attached_units.attach(
            build(BEASTBOSS, name="roster beastboss"),
            build(BEAST_SNAGGA_BOYZ, name="roster bsb 2", unit_index=2),
            game_state=GameState()),
        game_state=GameState()),
    build(GHAZGHKULL_THRAKA, name="roster ghaz"),
    build(BOYZ, name="roster mob 10", choices=BOYZ_10_CHOICES, unit_index=2),
    build(GRETCHIN, name="roster grots"),
    build(DEFFKOPTAS, name="roster koptas 1", unit_index=1),
    build(DEFFKOPTAS, name="roster koptas 2", unit_index=2),
]
c.eq("the army is 12 units after attaching", len(ROSTER), 12)
c.true("every unit is priced", all(s.points is not None for s in ROSTER))
# The engine's own total, from this project's transcribed points. It is 60 short
# of the export's 1990 because the four Enhancements (15 + 25 + 10 + 10) are
# granted by the roster builder, not by build_squad() - see the module docstring.
c.eq("engine total without the Enhancements", sum(s.points for s in ROSTER), 1930)
c.eq("model count", sum(len(s.models) for s in ROSTER), 78)

# The hand-built roster above is only worth checking if it IS the shipped
# list: a suite that builds its own roster stays green while testing the wrong
# army. So the same shape is asked of armies/orks.json's own build - unit for
# unit, by model lines and points, since the squad names differ.
from game import army_lists  # noqa: E402

entry = army_lists.get("orks")
shipped = []
entry.build("Player 2", lambda squad, *a, **k: shipped.append(squad), state=GameState())


def shape(squad):
    return tuple(sorted(line_counts(squad).items()))


c.eq("armies/orks.json builds the same 12 units", len(shipped), 12)
c.eq("...and the hand-built roster matches it unit for unit, model line for model line",
     sorted(shape(s) for s in ROSTER), sorted(shape(s) for s in shipped))
c.eq("...at the export's 1990 points once the four Enhancements are paid for",
     sum(s.points for s in shipped), 1990)
c.eq("...which are exactly the four the list names",
     sorted(entry.enhancement_names()),
     ["'Ardboyz", "Boss Boomer", "Ferocious Show-off", "Targetin' Gizmos"])
c.eq("...and it declares the three detachments that grant them",
     list(entry.detachments), ["Blitz Brigade", "Da Big Hunt", "Green Tide"])

c.finish()
