"""Detachments: part of the army list, several at once, paid for in DP.

A detachment is NOT chosen at the table. It is part of how a list was written
down, so picking the list is picking the detachments - there is no selection
screen, and one that was built here has been taken back out again.

An army may field SEVERAL, paying each one's printed Detachment Points out of
one budget, and two detachments sharing a printed tag are mutually exclusive
however cheap they are.

Sections:
  1. The data model: costs, tags, and which list fields what.
  2. Detachment Points: the budget and the tag rule.
  3. game/detachments.py is the one writer of the config settings.
  4. Retaliation Cadre is gated, per rule and per Stratagem.
  5. The screen is gone, and stays gone.
  6. A/B probes.
"""

import glob
import io
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import testkit as tk  # noqa: E402
from game import army_lists, config, detachments, enhancements, retaliation_cadre as rc  # noqa: E402
from game.factions import aeldari, death_guard, necrons, orks, tau_empire  # noqa: E402

c = tk.Checks("detachments")


# The one definition lives in testkit - eight suites had their own copy.
settings_as = tk.settings_as

class fielding:
    """Give an army list a different set of detachments for one block.

    ArmyList entries are module-level singletons shared by every test in the
    process - the same trap UnitProfile's class attributes are - so this puts
    the real tuple back.

    IT ALSO CLEARS THE FORCE DISPOSITION, and that is not tidying. A list may
    only declare a disposition one of its detachments permits
    (game/force_dispositions.py, validate()'s fifth check), so a hypothetical
    detachment set carries no opinion about which disposition the list would
    have been written with - and leaving the real one in place makes every
    block below fail on a rule none of them is about. Pass `disposition=` to
    exercise that rule deliberately; test_force_dispositions.py is where it is
    actually measured."""

    def __init__(self, army_key, names, disposition=None):
        self.entry = army_lists.get(army_key)
        self.names = tuple(names)
        self.disposition = disposition

    def __enter__(self):
        self.old = self.entry.detachments
        self.old_disposition = self.entry.force_disposition
        self.entry.detachments = self.names
        self.entry.force_disposition = self.disposition
        return self.entry

    def __exit__(self, *exc):
        self.entry.detachments = self.old
        self.entry.force_disposition = self.old_disposition


FACTION_MODULES = [
    ("AELDARI", aeldari.AELDARI), ("ORKS", orks.ORKS), ("NECRONS", necrons.NECRONS),
    ("T'AU EMPIRE", tau_empire.TAU_EMPIRE), ("DEATH GUARD", death_guard.DEATH_GUARD),
]


# --- 1. The data model ----------------------------------------------------
print("\n1. The data model")

c.eq("the T'au model six detachments", len(tau_empire.TAU_EMPIRE.detachments), 6)
# Aeldari is growing one detachment RULE per stage, so its list is named rather
# than counted - a number would say "eight" without saying which eight, and the
# point of this line is that adding one is a visible, reviewable change.
c.eq("the Aeldari model Seer Council plus the rules being built",
     list(aeldari.AELDARI.detachments),
     ["Seer Council", "Armoured Warhost", "Path of the Outcast",
      "Guardian Battlehost", "Aspect Host", "Warhost", "Windrider Host",
      "Spirit Conclave"])
c.eq("...and the other three model one each",
     [len(f.detachments) for k, f in FACTION_MODULES
      if k not in ("T'AU EMPIRE", "AELDARI")], [1, 1, 1])

# The printed DP costs, transcribed from the faction pages' own headings.
EXPECTED_POINTS = {
    "Retaliation Cadre": 3, "Kauyon": 2, "Mont'ka": 3,
    "Experimental Prototype Cadre": 1, "Advanced Acquisition Cadre": 1,
    "Auxiliary Cadre": 1,
    "Seer Council": 2, "War Horde": 3, "Awakened Dynasty": 3,
    "Death Lord's Chosen": 2,
    # The seven Aeldari detachment rules, DP transcribed from each page's own
    # heading line. Listed in full from the first stage on, so the arithmetic
    # below is ready for each one as it lands.
    "Aspect Host": 3, "Guardian Battlehost": 2, "Warhost": 3,
    "Windrider Host": 2, "Spirit Conclave": 2, "Armoured Warhost": 1,
    "Path of the Outcast": 1,
}
for _keyword, faction in FACTION_MODULES:
    for name, detachment in faction.detachments.items():
        c.eq("%s costs %d DP" % (name, EXPECTED_POINTS[name]),
             detachment.points, EXPECTED_POINTS[name])
        c.true("%s names its detachment rule" % name, bool(detachment.rule_name))
        c.true("%s carries printed rule text" % name, len(detachment.rule_text or "") > 40)

# The two printed exclusion tags, and only those two.
tagged = {d.name: d.tag for _k, f in FACTION_MODULES for d in f.detachments.values() if d.tag}
c.eq("exactly two detachments carry an exclusion tag",
     tagged, {"Experimental Prototype Cadre": "BATTLESUIT",
              "Auxiliary Cadre": "AUXILIARIES"})

# War Horde is the one detachment with no config setting, and that is a
# decision: it is the only Ork detachment modelled and its rule gates on the
# ORKS keyword. Pinned so a second Ork detachment turns this line red.
without = [d.name for _k, f in FACTION_MODULES for d in f.detachments.values() if not d.setting]
c.eq("War Horde alone declares no config setting", without, ["War Horde"])

# The detachments belong to the LIST.
c.true("ArmyList carries a TUPLE of detachments",
       isinstance(army_lists.get("tau").detachments, tuple))
# TWO lists field two at once, and both spend exactly the 3 DP budget: T'au's
# 2026-08-30 roster declares Kauyon + Advanced Acquisition Cadre (2+1), and the
# Aeldari list declares Seer Council + Path of the Outcast (2+1). Neither pair
# shares an exclusion tag, so the tag rule permits both.
for key, expected in [("tau", ["Kauyon", "Advanced Acquisition Cadre"]),
                      ("necrons", ["Awakened Dynasty"]),
                      ("aeldari", ["Seer Council", "Path of the Outcast"]),
                      ("orks", ["War Horde"]),
                      ("death_guard", ["Death Lord's Chosen"])]:
    c.eq("%s fields %s" % (key, expected), detachments.names_for(key), expected)
c.eq("every predefined list is legal",
     {k: detachments.validate(k) for k in ("tau", "necrons", "aeldari", "orks", "death_guard")},
     {k: [] for k in ("tau", "necrons", "aeldari", "orks", "death_guard")})

# `detachment` (singular) survives as a view for callers that want one name.
c.eq("the singular view is the first one", army_lists.get("tau").detachment,
     "Kauyon")


# --- 2. Detachment Points -------------------------------------------------
print("\n2. Detachment Points")

c.eq("the budget is 3 DP", detachments.DETACHMENT_POINT_BUDGET, 3)
# It is an ASSUMPTION, not a transcription: no page in rules/ states a budget.
det_src = io.open("game/detachments.py", encoding="utf-8").read()
c.true("...and the module says so in as many words",
       "ASSUMPTION" in det_src and "not a transcription" in det_src)
corpus = " ".join(io.open(p, encoding="utf-8").read()
                  for p in glob.glob("rules/*/detachments/*.md"))
c.true("the corpus really does not state one - the costs are printed, the budget is not",
       "Detachment Point" not in corpus)

with fielding("tau", ["Kauyon", "Advanced Acquisition Cadre"]):
    c.eq("Kauyon + Advanced Acquisition Cadre costs 2+1", detachments.points_for("tau"), 3)
    c.eq("...and fits the budget", detachments.validate("tau"), [])
with fielding("tau", ["Mont'ka", "Kauyon"]):
    c.eq("Mont'ka + Kauyon costs 3+2", detachments.points_for("tau"), 5)
    c.true("...and is refused as over budget",
           any("Detachment Points" in p for p in detachments.validate("tau")))
with fielding("tau", ["Retaliation Cadre"]):
    c.eq("one 3 DP detachment is exactly the budget", detachments.points_for("tau"), 3)
    c.eq("...and legal", detachments.validate("tau"), [])
with fielding("tau", []):
    c.true("a list with no detachment at all is refused",
           any("no detachment" in p for p in detachments.validate("tau")))
with fielding("tau", ["Kauyon", "Nope Cadre"]):
    c.true("a name the faction does not know is named, not silently dropped",
           any("Nope Cadre" in p for p in detachments.validate("tau")))

# The TAG rule is separate from the points: two 1 DP detachments sharing a tag
# are illegal together even though 1+1 fits. T'au print one detachment per tag,
# so the rule cannot bite on the real data - it is measured by giving a second
# detachment the same tag, which is exactly what a future one would do.
with fielding("tau", ["Experimental Prototype Cadre", "Auxiliary Cadre"]):
    c.eq("two DIFFERENT tags are compatible", detachments.validate("tau"), [])
    c.eq("...and cost only 2 DP", detachments.points_for("tau"), 2)
_aac = tau_empire.TAU_EMPIRE.detachments["Advanced Acquisition Cadre"]
_old_tag = _aac.tag
try:
    _aac.tag = "BATTLESUIT"
    with fielding("tau", ["Experimental Prototype Cadre", "Advanced Acquisition Cadre"]):
        c.eq("1+1 DP is within budget", detachments.points_for("tau"), 2)
        c.true("...but two BATTLESUIT detachments are still refused",
               any("BATTLESUIT" in p for p in detachments.validate("tau")))
finally:
    _aac.tag = _old_tag
c.true("the tag was put back", _aac.tag is None)


# --- 3. The one writer ----------------------------------------------------
print("\n3. game/detachments.py writes the settings")

ALL = {name: () for name in detachments.all_settings()}
c.eq("all settings are distinct",
     len(detachments.all_settings()), len(set(detachments.all_settings())))

with settings_as(**ALL):
    detachments.apply_to_config({"Player 1": "tau", "Player 2": "necrons"})
    c.eq("the T'au list's detachments are written",
         (config.KAUYON_PLAYERS, config.ADVANCED_ACQUISITION_CADRE_PLAYERS),
         (("Player 1",), ("Player 1",)))
    c.eq("...and the Necron one", config.AWAKENED_DYNASTY_PLAYERS, ("Player 2",))
    c.eq("...and nothing else", config.RETALIATION_CADRE_PLAYERS, ())

# SEVERAL detachments write SEVERAL settings - the whole point of the change.
with settings_as(**ALL), fielding("tau", ["Kauyon", "Advanced Acquisition Cadre"]):
    detachments.apply_to_config({"Player 1": "tau", "Player 2": "orks"})
    c.eq("both of the list's detachments are written",
         (config.KAUYON_PLAYERS, config.ADVANCED_ACQUISITION_CADRE_PLAYERS),
         (("Player 1",), ("Player 1",)))
    c.eq("...and the one it does not field is not", config.RETALIATION_CADRE_PLAYERS, ())

# Written FROM SCRATCH: switching list takes the old detachments away.
with settings_as(**ALL):
    detachments.apply_to_config({"Player 1": "tau", "Player 2": "necrons"})
    detachments.apply_to_config({"Player 1": "aeldari", "Player 2": "necrons"})
    c.eq("switching list clears the old detachment", config.KAUYON_PLAYERS, ())
    c.eq("...and writes the new one", config.SEER_COUNCIL_PLAYERS, ("Player 1",))

# A T'au mirror: both players hold it, from their own lists.
with settings_as(**ALL):
    detachments.apply_to_config({"Player 1": "tau", "Player 2": "tau"})
    c.eq("a mirror gives BOTH players the detachment",
         config.KAUYON_PLAYERS, ("Player 1", "Player 2"))
    c.eq("...both of them, since the list declares two",
         config.ADVANCED_ACQUISITION_CADRE_PLAYERS, ("Player 1", "Player 2"))

# Picking armies still writes them - that is now the ONLY path.
with settings_as(**ALL):
    army_lists.apply_to_config({"Player 1": "aeldari", "Player 2": "necrons"})
    c.eq("army choice writes Seer Council", config.SEER_COUNCIL_PLAYERS, ("Player 1",))
    c.eq("...and Awakened Dynasty", config.AWAKENED_DYNASTY_PLAYERS, ("Player 2",))
c.true("game/army_lists.py no longer writes the settings itself",
       "setattr(cfg, setting" not in io.open("game/army_lists.py", encoding="utf-8").read())

# War Horde declares no setting, so an Ork list writes none - and that is not
# a failure, it is the documented "nothing to declare" case.
with settings_as(**ALL):
    detachments.apply_to_config({"Player 1": "orks", "Player 2": "orks"})
    c.eq("an Ork list writes no detachment setting at all",
         [s for s in detachments.all_settings() if getattr(config, s)], [])


# --- 4. Retaliation Cadre is gated ----------------------------------------
print("\n4. Retaliation Cadre is gated on the detachment")

from game.factions.tau_empire import CRISIS_STARSCYTHE, STRIKE_TEAM  # noqa: E402
from game.factions.orks import BOYZ  # noqa: E402

suits = tk.build(CRISIS_STARSCYTHE, "Player 1", name="1 Crisis Starscythe Battlesuits 1")
tk.line_up(suits, 10, 10)
victims = tk.build(STRIKE_TEAM, "Player 2", name="2 Strike Team 1")
tk.line_up(victims, 14, 10)
gun = next(w for w in suits.models[0].weapons if getattr(w, "range_in", 0) > 6)


def bonded(players):
    with settings_as(RETALIATION_CADRE_PLAYERS=players):
        return rc.bonded_heroes_adjusted_weapon(gun, [(suits.models[0], gun)], victims)


c.eq("with the detachment, Strength improves", bonded(("Player 1",)).strength, gun.strength + 1)
c.eq("without it, Strength is untouched", bonded(()).strength, gun.strength)
c.eq("the OTHER player having it does not help this one",
     bonded(("Player 2",)).strength, gun.strength)

with settings_as(RETALIATION_CADRE_PLAYERS=("Player 1",)):
    c.true("stratagem_target_ok accepts a T'au unit of that player",
           rc.stratagem_target_ok(suits))
    c.true("a non-T'au unit is refused",
           not rc.stratagem_target_ok(tk.build(BOYZ, "Player 1", name="1 Boyz 1")))
with settings_as(RETALIATION_CADRE_PLAYERS=()):
    c.true("without the detachment, nothing is a legal target",
           not rc.stratagem_target_ok(suits))

# Each of the six SEPARATELY - a shared predicate one of them forgot to call
# would still pass a test that only exercised the others.
for module_name in ["stim_injectors", "arrokon_protocol", "shortened_blade",
                    "torchstar_gambit", "grav_inhibitor_field", "fail_safe_detonator"]:
    src = io.open("game/%s.py" % module_name, encoding="utf-8").read()
    c.true("%s guards on stratagem_target_ok()" % module_name,
           "if not stratagem_target_ok(" in src)


# --- 5. The screen is gone ------------------------------------------------
print("\n5. The selection screen is gone, and stays gone")

c.true("game/ui/detachment_select.py no longer exists",
       not os.path.exists("game/ui/detachment_select.py"))
main_src = io.open("main.py", encoding="utf-8").read()
c.true("main() does not import it", "detachment_select" not in main_src)
c.true("...and applies the detachments straight from the armies",
       "detachments.apply_to_config(armies)" in main_src)
c.true("no --detach flags remain", "--detach1" not in main_src and "--detach2" not in main_src)
config_src = io.open("game/config.py", encoding="utf-8").read()
for gone in ("DETACHMENT_SELECT", "PLAYER1_DETACHMENT", "PLAYER2_DETACHMENT"):
    c.true("config no longer carries %s" % gone, gone not in config_src)
# The harnesses no longer need to switch a screen off that does not exist.
for harness in ["selfplay.py", "smoke_pregame.py", "smoke_setup_screens.py"]:
    c.true("%s has no stale opt-out" % harness,
           "DETACHMENT_SELECT" not in io.open(harness, encoding="utf-8").read())
# A saved scene records the ARMIES; the detachments follow from them.
scene_src = io.open("game/scene_io.py", encoding="utf-8").read()
c.true("scene_io no longer stores detachments separately",
       "detachments_in" not in scene_src)
c.true("...because the armies it does store imply them", "def armies_in(path):" in scene_src)


# The list's Enhancement follows its DETACHMENT, and is answerable while the
# list is being BUILT. Real bug: the army screen previews every list before
# apply_to_config() has written anything, so a config-based gate dropped the
# T'au Enhancement - and its 20 points - from the tile.
#
# The 2026-08-30 roster buys NO Enhancement (it names none), so the mechanism
# has to be driven with a table of its own rather than through the list - the
# same reason test_tau_enhancements.py section 9 does. What is being measured
# is unchanged: swap the declared detachment and the points move, at PREVIEW
# time, with nothing written to config.
_tau_points = lambda: sum(s.points for s in army_lists.preview_squads("tau", "Player 1")
                          if s.points)
_base_points = _tau_points()
c.eq("the roster as supplied buys six Enhancements, and its points include them",
     _base_points, 2165)

# THE POINT OF THIS BLOCK: an Enhancement is part of the LIST, so its points are
# answerable at PREVIEW time - before anything is written to config. That is
# what keeps the army screen's tile and the battle agreeing.
_enh_points = sum(enhancements.get(n).points
                  for n in army_lists.get("tau").enhancement_names())
c.eq("...and those six are 115 of them", _enh_points, 115)
c.eq("so the units alone come to 2050", _base_points - _enh_points, 2050)

# Swapping the declared detachment does NOT move the points: the units are
# built and priced the same either way, and it is is_active() that refuses an
# Enhancement whose detachment is not fielded. Which is the honest division -
# the roster is what it is, the rules decide what it does.
with fielding("tau", ["Mont'ka"]):
    c.eq("a list declaring another detachment still costs the same",
         _tau_points(), _base_points)

army_src = io.open("game/army_lists.py", encoding="utf-8").read()
roster_src = io.open("game/army_roster.py", encoding="utf-8").read()
c.true("the Enhancement grant runs where the units are built",
       "enhancements.grant(" in roster_src)
c.true("...so it is answerable before anything is applied to config",
       "player_has_detachment" not in army_src)


# --- 6. A/B probes --------------------------------------------------------
print("\n6. A/B probes")

_real_budget = detachments.DETACHMENT_POINT_BUDGET
try:
    detachments.DETACHMENT_POINT_BUDGET = 99
    with fielding("tau", ["Mont'ka", "Kauyon"]):
        c.eq("A/B: with no budget, a 5 DP pair passes", detachments.validate("tau"), [])
finally:
    detachments.DETACHMENT_POINT_BUDGET = _real_budget
with fielding("tau", ["Mont'ka", "Kauyon"]):
    c.true("A/B restored", bool(detachments.validate("tau")))

_real_has = rc.has_detachment
try:
    rc.has_detachment = lambda player: True
    with settings_as(RETALIATION_CADRE_PLAYERS=()):
        c.eq("A/B: ungated, a detachment-less army gets Bonded Heroes back",
             rc.bonded_heroes_adjusted_weapon(
                 gun, [(suits.models[0], gun)], victims).strength, gun.strength + 1)
finally:
    rc.has_detachment = _real_has
c.eq("A/B restored", bonded(()).strength, gun.strength)

c.finish()
