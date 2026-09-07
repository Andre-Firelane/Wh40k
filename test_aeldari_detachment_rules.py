"""The seven Aeldari detachment RULES, and the groundwork they needed.

Aeldari had 54 datasheets and one modelled detachment. The corpus carries 15;
seven of them are being built - Aspect Host, Guardian Battlehost, Warhost,
Windrider Host, Spirit Conclave, Armoured Warhost, Path of the Outcast - and
this suite grows one section per stage.

Scope is the DETACHMENT RULE only. Each of the seven also prints 3-6 Stratagems
and 2-4 Enhancements; those stay data and are a separate piece of work, the
same three-way split the T'au batch had.

Sections:
  0. Groundwork: the ASURYANI faction keyword, the two extractions, and the
     Seer Council gate that was missing.
  1. Armoured Warhost - "Skilled Crews".
  2. Path of the Outcast - "Far-Reaching Doom".
  3. Guardian Battlehost - "Defend at All Costs".
  4. Aspect Host - "Path of the Warrior".
  5. Warhost - "Martial Grace".
  6. Windrider Host - "Ride the Wind".
  7. Spirit Conclave - "Shepherds of the Dead", and all seven together.
"""

import glob
import io
import os
import re
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import testkit as tk  # noqa: E402
from game import (aeldari_detachments as ad, attached_units, config,  # noqa: E402
                  detachment_gate, detachments, psychic_guidance,
                  strands_of_fate, tau_detachments)
from game.factions import aeldari as ae  # noqa: E402


def _corpus_enhancement_names(detachment_name):
    """{name: points} straight off the detachment's corpus page.

    Read from rules/aeldari/detachments/<name>.md rather than from a number in
    a comment: the Stratagem count in that same file was written by hand as 30
    when the corpus said 36, and this is the guard that would have caught it.

    The Errata block at the end of some pages repeats an Enhancement's own text
    verbatim, so the scan stops at the "## Stratagems" heading."""
    path = os.path.join("rules", "aeldari", "detachments", "%s.md" % detachment_name)
    src = io.open(path, encoding="utf-8").read()
    section = src.split("## Enhancements", 1)[1].split("## Stratagems", 1)[0]
    out = {}
    for line in section.splitlines():
        m = re.match(r"^### (.+?) - (\d+) pts\s*$", line.strip())
        if m:
            out[m.group(1).replace("’", "'")] = int(m.group(2))
    return out


c = tk.Checks("aeldari detachment rules")
D = ae.AELDARI.datasheets


def sq(name, owner="Player 1"):
    return tk.build(D[name], owner, name="%s %s 1" % (owner[-1], name))


# The one definition lives in testkit - eight suites had their own copy.
settings_as = tk.settings_as

# =========================================================================
# 0a. ASURYANI - the second printed keyword line
# =========================================================================
print("\n0a. The ASURYANI faction keyword")

# Pinned against the CORPUS, not against a list written here: a hand-kept
# expectation is the second copy that drifts. Every built datasheet's
# FACTION KEYWORDS line is read off its own rules/aeldari/<Name>.md.
corpus = {}
for _path in glob.glob("rules/aeldari/*.md"):
    _name = os.path.basename(_path)[:-3]
    _m = re.search(r"FACTION KEYWORDS:\s*(.+)", io.open(_path, encoding="utf-8").read())
    if _m:
        corpus[_name] = tuple(k.strip() for k in _m.group(1).split(","))

c.eq("every built datasheet has a corpus page with a FACTION KEYWORDS line",
     sorted(n for n in D if n not in corpus), [])
mismatch = [n for n, ds in D.items()
            if set(ds.faction_keywords) != set(corpus[n])]
c.eq("the engine's faction keywords match the printed line, datasheet for datasheet",
     mismatch, [])

# The line is NOT one keyword per datasheet - most craftworld units may be
# taken in a Ynnari army too, so they print both. Three shapes, all pinned.
_asuryani = {n for n, ds in D.items() if "ASURYANI" in ds.faction_keywords}
_ynnari_only = {n for n, ds in D.items() if ds.faction_keywords == ("YNNARI",)}
_asuryani_only = {n for n, ds in D.items() if ds.faction_keywords == ("ASURYANI",)}
c.eq("51 of the 54 are ASURYANI", len(_asuryani), 51)
c.eq("...and the three that are not are the Ynnari triumvirate",
     sorted(_ynnari_only), ["The Visarch", "The Yncarne", "Yvraine"])
c.eq("41 print both", 54 - len(_ynnari_only) - len(_asuryani_only), 41)

# The ten ASURYANI-only sheets are not an arbitrary list: they are Servant Of
# The Whispering God in the data. A Ynnari army may not include EPIC HEROes
# without the YNNARI keyword, so those heroes cannot carry it - and the ten
# are exactly the ten that set `epic_hero`. Pinned in both directions, because
# this is the correspondence the transcription is derived from.
_epic = {n for n in D if any(m.profile.epic_hero for m in sq(n).models)}
c.eq("thirteen datasheets are EPIC HEROes", len(_epic), 13)
c.eq("the ASURYANI-only sheets are the EPIC HEROes MINUS the Ynnari ones - "
     "which is Servant Of The Whispering God word for word",
     sorted(_asuryani_only), sorted(_epic - _ynnari_only))
c.eq("...ten of them", len(_asuryani_only), 10)
c.true("...and none of the ten may be taken in a Ynnari army",
       all("YNNARI" not in D[n].faction_keywords for n in _asuryani_only))
# The other direction: a non-hero craftworld unit CAN, which is what makes the
# exclusion a restriction rather than a description of the whole faction.
c.true("a non-hero craftworld unit may be taken in either army",
       D["Rangers"].faction_keywords == ("ASURYANI", "YNNARI"))

# THE MEASUREMENT THAT MADE THIS A STAGE OF ITS OWN. battle_focus looks like a
# stand-in for ASURYANI and is not: the Ynnari print the army rule while
# belonging to YNNARI. Had the flag been used, Spirit Conclave's "ASURYANI
# PSYKER" clause would have been wrong in the one place it bites - two of those
# three are PSYKERs.
_battle_focus = {n for n, ds in D.items()
                 if all(getattr(m.profile, "battle_focus", False)
                        for m in sq(n).models)}
# 48, not 54: the six datasheets that print no FACTION line at all - the
# three WRAITH CONSTRUCTs and the three SUPPORT WEAPON platforms - were
# setting the flag by transcription error. Measured against the corpus.
c.eq("48 datasheets print Battle Focus", len(_battle_focus), 48)
c.true("...and the six that do not are the wraiths and the platforms",
       not (_battle_focus & {"Wraithguard", "Wraithblades", "Wraithlord",
                             "D-cannon Platform", "Shadow Weaver Platform",
                             "Vibro Cannon Platform"}))
c.eq("...so the flag is NOT a stand-in for ASURYANI",
     sorted(_battle_focus - _asuryani), ["The Visarch", "The Yncarne", "Yvraine"])
c.true("...and two of those three are PSYKERs, which is why it matters",
       sum(1 for n in _ynnari_only
           if any(m.profile.psyker for m in sq(n).models)) == 2)

# It is kept OFF the ordinary keyword line, because those are two different
# printed lines meaning two different things.
c.eq("ASURYANI is not smuggled into the KEYWORDS line",
     [n for n, ds in D.items() if "ASURYANI" in ds.keywords], [])
c.eq("a non-Aeldari datasheet declares no faction keywords",
     tk.build(__import__("game.factions.orks", fromlist=["ORKS"]).ORKS.datasheets["Boyz"],
              "Player 2", name="2 Boyz 1").datasheet.faction_keywords, ())

# Read through rule 19.03's pooling, like every other keyword question.
c.true("a Ranger unit is ASURYANI", ad.is_asuryani_unit(sq("Rangers")))
c.true("...and Yvraine is not", not ad.is_asuryani_unit(sq("Yvraine")))
c.true("...but she is still AELDARI", ad.is_aeldari_unit(sq("Yvraine")))
# Corsairs and Exodites ARE ASURYANI - checked, not guessed from the names.
c.true("Corsairs are ASURYANI", ad.is_asuryani_unit(sq("Corsair Voidreavers")))
c.true("Exodites are ASURYANI", ad.is_asuryani_unit(sq("Dragon Knights")))

# 19.03 pooling. A real pairing cannot exercise it: every BODYGUARD datasheet
# prints both keywords, so the squad's own sheet always answers first and the
# component loop never decides anything. Measured, not assumed - and therefore
# isolated by hand, the only way to ask whether the loop does its job.
_real = sq("Guardian Defenders")
attached_units.attach(sq("Yvraine"), _real)
c.true("a real attached unit is ASURYANI", ad.is_asuryani_unit(_real))
c.true("...but only because its own datasheet already says so, not by pooling",
       "ASURYANI" in _real.datasheet.faction_keywords)


class _Sheet:
    def __init__(self, faction_keywords):
        self.faction_keywords = faction_keywords


class _Component:
    def __init__(self, datasheet):
        self.datasheet = datasheet


class _Squad:
    def __init__(self, datasheet, components):
        self.datasheet = datasheet
        self.attached_components = components


_pooled = _Squad(_Sheet(("YNNARI",)), [_Component(_Sheet(("YNNARI",))),
                                       _Component(_Sheet(("ASURYANI",)))])
c.true("a unit whose OWN sheet lacks the keyword still has it from a component",
       attached_units.unit_has_faction_keyword(_pooled, "ASURYANI"))
c.true("...and a unit where no component has it does not",
       not attached_units.unit_has_faction_keyword(
           _Squad(_Sheet(("YNNARI",)), [_Component(_Sheet(("YNNARI",)))]), "ASURYANI"))
c.true("...and a squad with no components at all is answered from its own sheet",
       attached_units.unit_has_faction_keyword(_Squad(_Sheet(("ASURYANI",)), []), "ASURYANI"))


# =========================================================================
# 0b. The two extractions
# =========================================================================
print("\n0b. The two extractions")

# has_detachment() reads one config constant and knows about no faction, so it
# does not belong in a T'au module once a second faction asks. ONE definition,
# re-exported - pinned as identity, because two copies that agree today are
# exactly what this check is for.
c.true("tau_detachments re-exports the gate rather than defining a second one",
       tau_detachments.has_detachment is detachment_gate.has_detachment)
_gate_src = io.open("game/tau_detachments.py", encoding="utf-8").read()
c.true("...and says so at the source",
       "detachment_gate.has_detachment" in _gate_src
       and "def has_detachment" not in _gate_src)

# The same treatment for the faction test, which thirteen modules reached into
# game/psychic_guidance.py for - a private name in a datasheet-ability module.
c.true("psychic_guidance._is_aeldari is the shared predicate",
       psychic_guidance._is_aeldari(sq("Rangers"))
       == ad.is_aeldari_unit(sq("Rangers")))
_pg_src = io.open("game/psychic_guidance.py", encoding="utf-8").read()
c.true("...delegating rather than keeping its own copy",
       "from game.aeldari_detachments import is_aeldari_unit" in _pg_src)
c.true("the thirteen callers still work through the old name",
       psychic_guidance._is_aeldari(sq("Yvraine")))
c.true("...and it says no to a non-Aeldari unit",
       not psychic_guidance._is_aeldari(
           tk.build(__import__("game.factions.orks", fromlist=["ORKS"]).ORKS.datasheets["Boyz"],
                    "Player 2", name="2 Boyz 1")))

c.true("the gate answers False for a player with no detachment",
       not detachment_gate.has_detachment("Player 2", "SEER_COUNCIL_PLAYERS"))
c.true("...and for a constant that does not exist at all",
       not detachment_gate.has_detachment("Player 1", "NO_SUCH_SETTING_PLAYERS"))
c.true("...and for no player", not detachment_gate.has_detachment(None, "SEER_COUNCIL_PLAYERS"))


# =========================================================================
# 0c. The Seer Council stratagems were never gated
# =========================================================================
print("\n0c. The Seer Council gate")

c.eq("the detachment names its own config constant",
     strands_of_fate.SETTING, "SEER_COUNCIL_PLAYERS")
# A rule that gates on a constant nobody writes is inert and looks right from
# the inside, so the constant is checked against the set game/detachments.py
# actually writes.
c.true("...and it is one game/detachments.py really writes",
       strands_of_fate.SETTING in detachments.all_settings())

with settings_as(SEER_COUNCIL_PLAYERS=("Player 1",)):
    c.true("a player fielding Seer Council passes the gate",
           strands_of_fate.has_detachment("Player 1"))
    c.true("...and one who is not, does not",
           not strands_of_fate.has_detachment("Player 2"))
with settings_as(SEER_COUNCIL_PLAYERS=()):
    c.true("nobody fielding it means nobody passes",
           not strands_of_fate.has_detachment("Player 1"))

# All six stratagems ask. Checked at the SOURCE and per file, because a wiring
# that reaches five of six looks complete from any one of them - the same
# counting the four-site Fated Hero wiring needs.
SEER_COUNCIL_STRATAGEMS = ["forewarned", "ishas_fury", "psychic_shield",
                           "presentiment_of_dread", "unshrouded_truth",
                           "fate_inescapable"]
for _mod in SEER_COUNCIL_STRATAGEMS:
    _src = io.open("game/%s.py" % _mod, encoding="utf-8").read()
    c.true("%s gates on the detachment" % _mod,
           "strands_of_fate.has_detachment(" in _src)
c.eq("...and that is all six of them", len(SEER_COUNCIL_STRATAGEMS), 6)

# Isha's Fury is the one where the payer is not the obvious unit: it reacts to
# an ENEMY move, so the reactor pays and it is the reactor's detachment that
# counts. Its own line, because taking the mover's owner would read fine.
_isha = io.open("game/ishas_fury.py", encoding="utf-8").read()
c.true("Isha's Fury asks about the REACTOR, not the mover",
       "strands_of_fate.has_detachment(reactor)" in _isha)

# =========================================================================
# 1. Armoured Warhost - "Skilled Crews"
# =========================================================================
print("\n1. Armoured Warhost - Skilled Crews")

from game import coldstar, skilled_crews  # noqa: E402
from game.weapons import RANGED  # noqa: E402

_det = ae.AELDARI.detachments["Armoured Warhost"]
c.eq("1 DP", _det.points, 1)
c.eq("its rule is named", _det.rule_name, "Skilled Crews")
c.eq("...and it declares the config constant the rule reads",
     _det.setting, skilled_crews.SETTING)
c.true("...which game/detachments.py really writes",
       skilled_crews.SETTING in detachments.all_settings())
c.eq("no exclusion tag - none of the seven prints one", _det.tag, None)
c.eq("stratagems stay data for now", _det.stratagems, [])
# Its two Enhancements are no longer data: the records are what
# game/enhancements.py's registry is pinned AGAINST, so they earn their place
# twice. Counted against the CORPUS rather than against a literal.
c.eq("...and it declares its two Enhancements", len(_det.enhancements), 2)

_falcon = sq("Falcon")
_rangers = sq("Rangers")

with settings_as(ARMOURED_WARHOST_PLAYERS=()):
    c.true("without the detachment the rule is inert", not skilled_crews.applies(_falcon))

with settings_as(ARMOURED_WARHOST_PLAYERS=("Player 1",)):
    c.true("an AELDARI VEHICLE of a player fielding it qualifies",
           skilled_crews.applies(_falcon))
    c.true("...but an AELDARI INFANTRY unit does not",
           not skilled_crews.applies(_rangers))
    c.true("...nor a vehicle belonging to the other player",
           not skilled_crews.applies(sq("Falcon", "Player 2")))
    # A non-Aeldari vehicle, so the faction half is isolated from the
    # VEHICLE half - a probe against an Ork INFANTRY unit would pass for
    # the wrong reason.
    _ork_wagon = tk.build(
        __import__("game.factions.orks", fromlist=["ORKS"]).ORKS.datasheets["Battlewagon"],
        "Player 1", name="1 Battlewagon 1")
    c.true("...and not a VEHICLE of another faction", not skilled_crews.applies(_ork_wagon))

    # The grant itself.
    _gun = next(w for w in _falcon.models[0].weapons if w.weapon_type == RANGED)
    c.true("the printed weapon does not have [ASSAULT]", not _gun.assault)
    c.true("...and the granted copy does",
           skilled_crews.adjusted_weapon(_gun, _falcon).assault)
    c.true("...without mutating the shared instance", not _gun.assault)

    # Never a downgrade, and never a melee grant.
    _already = next((w for w in _falcon.models[0].weapons
                     if w.weapon_type == RANGED and w.assault), None)
    _melee = next(w for w in _falcon.models[0].weapons if w.weapon_type != RANGED)
    c.true("a melee weapon is left alone - the text says 'ranged attacks'",
           not skilled_crews.adjusted_weapon(_melee, _falcon).assault)
    c.true("...and an unqualified unit's gun is returned unchanged",
           skilled_crews.adjusted_weapon(_gun, _rangers) is _gun)

    # THE READER THAT PAYS FOR IT. [ASSAULT] is bought to Advance and still
    # shoot (24.04), and that is decided by coldstar.weapon_has_assault(), not
    # by the damage maths - a grant that reached only the adjuster chain would
    # look wired while doing nothing the detachment is for.
    c.true("weapon_has_assault() sees the grant",
           coldstar.weapon_has_assault(_gun, _falcon))
with settings_as(ARMOURED_WARHOST_PLAYERS=()):
    c.true("...and stops seeing it without the detachment",
           not coldstar.weapon_has_assault(_gun, _falcon))

# Ranged-only is checked as NEGATIVE SPACE: game/fight.py never importing this
# module is stronger than a melee scene that happens to come out unchanged.
_fight_src = io.open("game/fight.py", encoding="utf-8").read()
c.true("the melee step never reads Skilled Crews", "skilled_crews" not in _fight_src)
_shoot_src = io.open("game/shooting.py", encoding="utf-8").read()
c.true("...while the shooting step does",
       "skilled_crews.adjusted_weapon(" in _shoot_src)

# No AI path (standing Aeldari instruction), as negative space.
_ai_src = io.open("ai/agent_driver.py", encoding="utf-8").read().lower()
for _needle in ("skilled_crews", "armoured warhost", "armoured_warhost"):
    c.true("ai/agent_driver.py never mentions %s" % _needle, _needle not in _ai_src)


# =========================================================================
# 2. Path of the Outcast - "Far-Reaching Doom"
# =========================================================================
print("\n2. Path of the Outcast - Far-Reaching Doom")

from game import detection_range, far_reaching_doom as frd, status_effects  # noqa: E402

_det2 = ae.AELDARI.detachments["Path of the Outcast"]
c.eq("1 DP", _det2.points, 1)
c.eq("its rule is named", _det2.rule_name, "Far-Reaching Doom")
c.eq("...and it declares the constant the rule reads", _det2.setting, frd.SETTING)
c.true("...which game/detachments.py really writes",
       frd.SETTING in detachments.all_settings())
c.eq("+6 inches", frd.FAR_REACHING_DOOM_BONUS_IN, 6.0)

# TWO RULES, ONE NAME. game/path_of_the_outcast.py is the RANGERS DATASHEET
# ability; this is the detachment. Pinned from both sides, because a future
# reader finding two modules one underscore apart deserves to be told.
from game import path_of_the_outcast as pto_datasheet  # noqa: E402

c.true("the datasheet ability is a reactive move, not a detection rule",
       hasattr(pto_datasheet, "PATH_OF_THE_OUTCAST_RANGE_IN")
       and not hasattr(pto_datasheet, "detection_bonus_in"))
c.true("...and the detachment rule is the other way round",
       hasattr(frd, "detection_bonus_in")
       and not hasattr(frd, "PATH_OF_THE_OUTCAST_RANGE_IN"))
c.eq("the module is named after the RULE", frd.FAR_REACHING_DOOM_LABEL,
     "Far-Reaching Doom")

frd.reset()
_rangers2 = sq("Rangers")
_shroud = sq("Shroud Runners")
_avengers = sq("Dire Avengers")
_foe = sq("Guardian Defenders", "Player 2")

with settings_as(PATH_OF_THE_OUTCAST_PLAYERS=()):
    c.true("without the detachment the unit does not qualify", not frd.applies(_rangers2))
with settings_as(PATH_OF_THE_OUTCAST_PLAYERS=("Player 1",)):
    c.true("Rangers qualify", frd.applies(_rangers2))
    c.true("...and Shroud Runners too", frd.applies(_shroud))
    c.true("...but no other Aeldari unit does", not frd.applies(_avengers))
    c.true("...nor the same datasheet under the other player",
           not frd.applies(sq("Rangers", "Player 2")))

    # The window. "selected to shoot" ... "until that unit has shot".
    frd.reset()
    c.true("closed before anything is selected", not frd.is_open())
    c.true("opening it reports the unit qualified", frd.begin_shooting(_rangers2))
    c.true("...and it is open for that owner", frd.is_open("Player 1"))
    frd.end_shooting(_rangers2)
    c.true("...and shut again once the unit has shot", not frd.is_open())
    c.true("a non-qualifying unit never opens it", not frd.begin_shooting(_avengers))
    c.true("...leaving it shut", not frd.is_open())

    # WHOSE range changes: the shooter's ENEMIES, not the shooter.
    frd.begin_shooting(_rangers2)
    c.eq("an enemy unit gains the bonus", frd.detection_bonus_in(_foe), 6.0)
    c.eq("...and the shooter's own side gains nothing",
         frd.detection_bonus_in(_rangers2), 0.0)
    c.eq("...and a friendly unit that is not shooting gains nothing either",
         frd.detection_bonus_in(_avengers), 0.0)

    # It reaches the shared fold, which is what any caller actually reads.
    c.eq("the fold sums it", detection_range.bonus_in(_foe), 6.0)

    # MEASURED IN BOTH BANDS. 13.09 has two base distances - the printed 15"
    # and the 12" house rule for a wall on the model's own footprint - and a
    # bonus checked against only one of them can be right on the wrong base.
    c.eq("the default band goes 15 to 21",
         detection_range.apply(status_effects.DETECTION_RANGE_IN, _foe), 21.0)
    c.eq("...and the house-rule band 12 to 18",
         detection_range.apply(status_effects.CLOSE_DETECTION_RANGE_IN, _foe), 18.0)
    c.eq("...while the shooter's own side keeps the printed 15",
         detection_range.apply(status_effects.DETECTION_RANGE_IN, _rangers2), 15.0)
    frd.end_shooting()
    c.eq("and once the window shuts, 15 again",
         detection_range.apply(status_effects.DETECTION_RANGE_IN, _foe), 15.0)

frd.reset()

# THE DIRECTION, stated as a check rather than only in a comment: detection
# range belongs to the HIDDEN model, so +6" makes the enemy visible from
# further away. A rule that hid one's own snipers better would read the same
# from the call site and be a different rule.
c.true("the bonus is positive, i.e. a penalty on the enemy",
       frd.FAR_REACHING_DOOM_BONUS_IN > 0)

# The window is opened and closed by the two seams the printed text names.
_shoot_src2 = io.open("game/shooting.py", encoding="utf-8").read()
c.true("start_shooting() opens it", "far_reaching_doom.begin_shooting(squad)" in _shoot_src2)
c.true("...and _actually_finish_squad() closes it",
       "far_reaching_doom.end_shooting(self.active_squad)" in _shoot_src2)
_dr_src = io.open("game/detection_range.py", encoding="utf-8").read()
c.true("the fold reads it without a new call-site argument",
       "far_reaching_doom.detection_bonus_in(squad)" in _dr_src)
c.eq("...and bonus_in() still takes exactly its two named sources",
     _dr_src.count("def bonus_in(squad, prey_marks=None, unmasking=None):"), 1)

for _needle in ("far_reaching_doom", "far-reaching doom"):
    c.true("ai/agent_driver.py never mentions %s" % _needle,
           _needle not in io.open("ai/agent_driver.py", encoding="utf-8").read().lower())



# =========================================================================
# 3. Guardian Battlehost - "Defend at All Costs"
# =========================================================================
print("\n3. Guardian Battlehost - Defend at All Costs")

from game import defend_at_all_costs as dac  # noqa: E402
from game.modifiers import Modifier  # noqa: E402

_det3 = ae.AELDARI.detachments["Guardian Battlehost"]
c.eq("2 DP", _det3.points, 2)
c.eq("its rule is named", _det3.rule_name, "Defend at All Costs")
c.eq("...and it declares the constant the rule reads", _det3.setting, dac.SETTING)
c.true("...which game/detachments.py really writes",
       dac.SETTING in detachments.all_settings())

# The sign. "add 1 to the Hit roll" is an EASIER roll, and modifiers adjust the
# THRESHOLD - so the amount is negative. Backwards, this detachment would be an
# army-wide penalty, which is the mistake Command Protocols records.
c.eq("the bonus is a -1 on the threshold", dac.DEFEND_AT_ALL_COSTS_BONUS, -1)


class _Area:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def distance_to_model(self, m):
        return ((m.x_in - self.x) ** 2 + (m.y_in - self.y) ** 2) ** 0.5


class _Objective:
    def __init__(self, x, y):
        self.terrain_area = _Area(x, y)


_obj = [_Objective(20.0, 20.0)]

_guard = sq("Guardian Defenders")
_avg = sq("Dire Avengers")
_walker = sq("War Walkers")
_platform = sq("D-cannon Platform")
_spears = sq("Shining Spears")           # Aeldari, none of the four keywords
_enemy = sq("Guardian Defenders", "Player 2")

with settings_as(GUARDIAN_BATTLEHOST_PLAYERS=("Player 1",)):
    # --- the four keywords, each measured ---------------------------------
    tk.line_up(_guard, 20.0, 20.0, spacing=1.2)     # on the objective
    tk.line_up(_enemy, 60.0, 60.0, spacing=1.2)     # far away
    for _name, _unit in (("Guardians", _guard), ("Dire Avengers", _avg),
                         ("War Walkers", _walker), ("SUPPORT WEAPON", _platform)):
        tk.line_up(_unit, 20.0, 20.0, spacing=1.4)
        c.true("%s qualify" % _name,
               dac.applies_to_group(_unit.models, _unit, _enemy, _obj))
    tk.line_up(_spears, 20.0, 20.0, spacing=1.4)
    c.true("...and an Aeldari unit with none of the four keywords does not",
           not dac.applies_to_group(_spears.models, _spears, _enemy, _obj))

    # --- "and/or" is an OR: all four board states -------------------------
    tk.line_up(_guard, 20.0, 20.0, spacing=1.2)     # attacker on
    tk.line_up(_enemy, 60.0, 60.0, spacing=1.2)     # target off
    c.true("attacker on the objective, target off: pays",
           dac.applies(_guard, _enemy, _obj))
    tk.line_up(_guard, 60.0, 60.0, spacing=1.2)     # attacker off
    tk.line_up(_enemy, 20.0, 20.0, spacing=1.2)     # target on
    c.true("attacker off, TARGET on: pays too - this is the half an AND "
           "reading would lose", dac.applies(_guard, _enemy, _obj))
    tk.line_up(_guard, 20.0, 20.0, spacing=1.2)
    tk.line_up(_enemy, 21.0, 21.0, spacing=1.2)
    c.true("both on: pays", dac.applies(_guard, _enemy, _obj))
    tk.line_up(_guard, 60.0, 60.0, spacing=1.2)
    tk.line_up(_enemy, 62.0, 62.0, spacing=1.2)
    c.true("neither on: does not pay", not dac.applies(_guard, _enemy, _obj))

    # --- the gates --------------------------------------------------------
    tk.line_up(_guard, 20.0, 20.0, spacing=1.2)
    c.true("no objectives on the board at all: nothing to defend",
           not dac.applies(_guard, _enemy, ()))
    c.true("...and the other player's Guardians get nothing",
           not dac.applies(sq("Guardian Defenders", "Player 2"), _enemy, _obj))
    _ork = tk.build(
        __import__("game.factions.orks", fromlist=["ORKS"]).ORKS.datasheets["Boyz"],
        "Player 1", name="1 Boyz 1")
    tk.line_up(_ork, 20.0, 20.0, spacing=1.2)
    c.true("...and a non-Aeldari unit of the same player gets nothing",
           not dac.applies(_ork, _enemy, _obj))

    # PER MODEL, and this is the case that a unit-level reading gets wrong:
    # a Farseer leading Guardian Defenders is NOT a GUARDIAN, so he must not
    # inherit the keyword from his bodyguards. A real attached unit, not a
    # synthetic mixture - which is what makes it worth pinning.
    _led = sq("Guardian Defenders")
    attached_units.attach(sq("Farseer"), _led)
    tk.line_up(_led, 20.0, 20.0, spacing=1.2)
    _farseer = next(m for m in _led.models if m.profile.name == "Farseer")
    _bodyguard = next(m for m in _led.models if m.profile.name == "Guardian Defender")
    c.true("a Guardian in the led unit still qualifies",
           dac.applies_to_group([_bodyguard], _led, _enemy, _obj))
    c.true("...but the Farseer leading them does NOT - he is no GUARDIAN",
           not dac.applies_to_group([_farseer], _led, _enemy, _obj))
    c.true("...and a group holding both grants nothing, since all() is the rule",
           not dac.applies_to_group([_bodyguard, _farseer], _led, _enemy, _obj))

    # --- the modifier list ------------------------------------------------
    _mods = dac.hit_modifiers(_guard.models, _guard, _enemy, _obj)
    c.eq("one modifier when it applies", len(_mods), 1)
    c.eq("...carrying the rule's own name", _mods[0].source, "Defend at All Costs")
    c.eq("...and -1", _mods[0].amount, -1)
    c.eq("an empty list when it does not",
         dac.hit_modifiers(_spears.models, _spears, _enemy, _obj), [])

with settings_as(GUARDIAN_BATTLEHOST_PLAYERS=()):
    tk.line_up(_guard, 20.0, 20.0, spacing=1.2)
    c.true("without the detachment, nothing", not dac.applies(_guard, _enemy, _obj))

# --- END TO END through the real controllers ------------------------------
# A predicate test cannot show the modifier reaching a roll, and both attack
# steps end by filtering modifiers - a bonus appended after those filters would
# be silently dropped. So the threshold is measured through the real thing.
_scene = tk.shooting_scene(D["Guardian Defenders"], D["Guardian Defenders"],
                           attacker_owner="Player 1", objectives=_obj)
tk.line_up(_scene["attacker"], 20.0, 20.0, spacing=1.2)
tk.line_up(_scene["target"], 20.0, 26.0, spacing=1.2)
_shoot = _scene["shooting"]
_shoot.start_shooting(_scene["attacker"])
_shoot.choose_target_squad(_scene["target"])
# The group dict is what _hit_modifiers() actually takes; built here rather
# than driven through the weapon-choice prompt, so the check is about the
# modifier list and not about the UI flow.
_gun = next(w for w in _scene["attacker"].models[0].weapons
            if w.weapon_type == RANGED)
_grp = {"pairs": [(m, _gun) for m in _scene["attacker"].models],
        "target_squad": _scene["target"]}
with settings_as(GUARDIAN_BATTLEHOST_PLAYERS=()):
    _without = [m.source for m in _shoot._hit_modifiers(_grp)]
with settings_as(GUARDIAN_BATTLEHOST_PLAYERS=("Player 1",)):
    _with = [m.source for m in _shoot._hit_modifiers(_grp)]
c.true("the real shooting hit step does not carry it without the detachment",
       "Defend at All Costs" not in _without)
c.true("...and does carry it with", "Defend at All Costs" in _with)

_fscene = tk.fight_scene(D["Guardian Defenders"], D["Guardian Defenders"],
                         attacker_owner="Player 1", objectives=_obj)
tk.line_up(_fscene["attacker"], 20.0, 20.0, spacing=1.2)
tk.line_up(_fscene["target"], 20.0, 21.0, spacing=1.2)
_fight = _fscene["fight"]
_fighter = _fscene["attacker"].models[0]
with settings_as(GUARDIAN_BATTLEHOST_PLAYERS=()):
    _fwithout = [m.source for m in _fight._hit_modifiers(_fighter, _fscene["target"])]
with settings_as(GUARDIAN_BATTLEHOST_PLAYERS=("Player 1",)):
    _fight.fighting_squad = _fscene["attacker"]
    _fwith = [m.source for m in _fight._hit_modifiers(_fighter, _fscene["target"])]
c.true("the real FIGHT hit step does not carry it without the detachment",
       "Defend at All Costs" not in _fwithout)
c.true("...and does carry it with - 'makes an attack' means both phases",
       "Defend at All Costs" in _fwith)

# Both files, counted per file: a wiring that reaches one looks complete from
# the other.
for _f in ("game/shooting.py", "game/fight.py"):
    c.eq("%s reads it exactly once" % _f,
         io.open(_f, encoding="utf-8").read().count("defend_at_all_costs.hit_modifiers("), 1)

for _needle in ("defend_at_all_costs", "guardian battlehost"):
    c.true("ai/agent_driver.py never mentions %s" % _needle,
           _needle not in io.open("ai/agent_driver.py", encoding="utf-8").read().lower())



# =========================================================================
# 4. Aspect Host - "Path of the Warrior"
# =========================================================================
print("\n4. Aspect Host - Path of the Warrior")

from game import path_of_the_warrior as potw, reroll_scope  # noqa: E402
from game.turn import PHASE_FIGHT, PHASE_SHOOTING  # noqa: E402

_det4 = ae.AELDARI.detachments["Aspect Host"]
c.eq("3 DP", _det4.points, 3)
c.eq("its rule is named", _det4.rule_name, "Path of the Warrior")
c.eq("...and it declares the constant the rule reads", _det4.setting, potw.SETTING)
c.true("...which game/detachments.py really writes",
       potw.SETTING in detachments.all_settings())
c.eq("two printed options", potw.PATH_OF_THE_WARRIOR_OPTIONS, ("hit", "wound"))


class _Turn:
    def __init__(self, phase):
        self.phase = phase


_avengers4 = sq("Dire Avengers")          # ASPECT WARRIORS
_avatar = sq("Avatar of Khaine")          # AVATAR OF KHAINE
_guard4 = sq("Guardian Defenders")        # neither
_rangers4 = sq("Rangers")                 # neither

with settings_as(ASPECT_HOST_PLAYERS=()):
    c.true("without the detachment nothing qualifies", not potw.eligible(_avengers4))
with settings_as(ASPECT_HOST_PLAYERS=("Player 1",)):
    c.true("ASPECT WARRIORS qualify", potw.eligible(_avengers4))
    c.true("...and the Avatar of Khaine", potw.eligible(_avatar))
    c.true("...but Guardians do not", not potw.eligible(_guard4))
    c.true("...nor Rangers", not potw.eligible(_rangers4))
    c.true("...nor the same unit under the other player",
           not potw.eligible(sq("Dire Avengers", "Player 2")))

    # THE CHOICE. Two exclusive options, so a real prompt - the opposite call
    # from Herald of Ynnead, whose single option was pure gain.
    _dm = tk.DecisionManager() if hasattr(tk, "DecisionManager") else None
    from game.decision import DecisionManager  # noqa: E402
    _dm = DecisionManager()
    _log4 = tk.Log()
    _ctrl4 = potw.PathOfTheWarriorController(
        decision_manager=_dm, game_log=_log4, turn_tracker=_Turn(PHASE_SHOOTING))
    c.true("a qualifying unit is asked", _ctrl4.offer(_avengers4))
    c.true("...and the prompt is pending", _dm.is_pending)
    c.eq("...with exactly the two printed options", len(tk.options_of(_dm)), 2)
    c.true("nothing is chosen until it is answered",
           _ctrl4.chosen_for(_avengers4) is None)
    tk.pick_option(_dm, "hit")
    c.eq("answering records the choice", _ctrl4.chosen_for(_avengers4), potw.HIT)
    c.true("...and only that half is live", _ctrl4.hit_ones_apply(_avengers4))
    c.true("...not the other", not _ctrl4.wound_ones_apply(_avengers4))
    c.true("...and it is logged", _log4.has("Path of the Warrior"))
    c.true("a second offer in the same phase does not ask again",
           not _ctrl4.offer(_avengers4))
    c.true("a non-qualifying unit is never asked", not _ctrl4.offer(_guard4))

    # PER PHASE. The same unit chooses again when it is selected to FIGHT,
    # and the two choices are independent - the ledger keys on the phase.
    _ctrl4.turn_tracker = _Turn(PHASE_FIGHT)
    c.true("the same unit is asked again in the Fight phase", _ctrl4.offer(_avengers4))
    tk.pick_option(_dm, "wound")
    c.eq("...and can take the other option", _ctrl4.chosen_for(_avengers4), potw.WOUND)
    _ctrl4.turn_tracker = _Turn(PHASE_SHOOTING)
    c.eq("...while the shooting choice is untouched",
         _ctrl4.chosen_for(_avengers4), potw.HIT)

    # "Until the end of the phase".
    _ctrl4.reset_phase()
    c.true("the phase reset clears it", _ctrl4.chosen_for(_avengers4) is None)
    _ctrl4.turn_tracker = _Turn(PHASE_FIGHT)
    c.true("...in both phases", _ctrl4.chosen_for(_avengers4) is None)

    # THE AI ANSWERS ITSELF, or the loop stalls on an unanswered prompt.
    _auto = potw.PathOfTheWarriorController(
        decision_manager=DecisionManager(), turn_tracker=_Turn(PHASE_SHOOTING),
        auto_players=("Player 1",))
    c.true("an auto player picks without a prompt", _auto.offer(_avengers4))
    c.true("...leaving nothing pending", not _auto.decision_manager.is_pending)
    c.eq("...and takes the Hit re-roll, since a miss never reaches the wound roll",
         _auto.chosen_for(_avengers4), potw.HIT)

# NOT a reroll_scope entry - each clause is a plain mandatory 1s re-roll with
# no "you can" and no "instead", so listing it would offer a second choice the
# datasheet never gives. Pinned as an ABSENCE, the only place it shows.
c.true("Path of the Warrior is not a ones-or-whole offer",
       potw.PATH_OF_THE_WARRIOR_LABEL not in reroll_scope.ONES_OR_WHOLE_LABELS)

# FOUR SITES, TWO FILES. A wiring that reaches three looks complete from any
# one of them, so each file is counted for each clause.
for _f in ("game/shooting.py", "game/fight.py"):
    _src4 = io.open(_f, encoding="utf-8").read()
    c.eq("%s reads the HIT clause once" % _f,
         _src4.count("path_of_the_warrior.hit_ones_apply("), 1)
    c.eq("%s reads the WOUND clause once" % _f,
         _src4.count("path_of_the_warrior.wound_ones_apply("), 1)
c.true("start_shooting() makes the offer",
       "self.path_of_the_warrior.offer(squad)" in
       io.open("game/shooting.py", encoding="utf-8").read())
c.true("...and so does the one funnel every fight activation goes through",
       "self.path_of_the_warrior.offer(squad)" in
       io.open("game/fight.py", encoding="utf-8").read())

# It must NOT be in the reroll-REASON methods: those drive the
# failures-or-whole offer, which is a wider entitlement than the printed text
# gives. Checked by reading each method's own body rather than the whole file,
# since the label legitimately appears elsewhere in both.
def _method_body(src, name):
    start = src.index("    def %s(" % name)
    rest = src[start:]
    m = re.search(r"\n    def (?!%s\()" % re.escape(name), rest)
    return rest[: m.start()] if m else rest


for _f in ("game/shooting.py", "game/fight.py"):
    _src4 = io.open(_f, encoding="utf-8").read()
    for _method in ("_hit_reroll_reason", "_wound_reroll_reason"):
        c.true("%s's %s does not offer it" % (_f, _method),
               "path_of_the_warrior" not in _method_body(_src4, _method))

# END TO END, with scripted dice: the 1s must really be thrown again. A
# predicate test cannot show that, and the automatic-ones branch it hangs in is
# guarded by three other conditions.
_e2e = tk.shooting_scene(D["Dire Avengers"], D["Guardian Defenders"],
                         attacker_owner="Player 1")
_e2e_shoot = _e2e["shooting"]
_e2e_shoot.path_of_the_warrior = potw.PathOfTheWarriorController(
    turn_tracker=_Turn(PHASE_SHOOTING), auto_players=("Player 1",))
with settings_as(ASPECT_HOST_PLAYERS=("Player 1",)):
    _e2e_shoot.path_of_the_warrior.offer(_e2e["attacker"])
    c.eq("the Dire Avengers took the Hit re-roll",
         _e2e_shoot.path_of_the_warrior.chosen_for(_e2e["attacker"]), potw.HIT)
    c.true("...which the shooting controller can see",
           _e2e_shoot.path_of_the_warrior.hit_ones_apply(_e2e["attacker"]))
    c.true("...and the wound half stays off",
           not _e2e_shoot.path_of_the_warrior.wound_ones_apply(_e2e["attacker"]))

# main.py builds it and clears it on the phase boundary.
_main4 = io.open("main.py", encoding="utf-8").read()
c.true("main.py builds the controller",
       "path_of_the_warrior_controller = PathOfTheWarriorController(" in _main4)
c.true("...hands it to BOTH attack controllers",
       "fight_controller.path_of_the_warrior = path_of_the_warrior_controller" in _main4
       and "shooting_controller.path_of_the_warrior = path_of_the_warrior_controller" in _main4)
c.true("...and clears it every phase change",
       "path_of_the_warrior_controller.reset_phase()" in _main4)

for _needle in ("path_of_the_warrior", "aspect host"):
    c.true("ai/agent_driver.py never mentions %s" % _needle,
           _needle not in io.open("ai/agent_driver.py", encoding="utf-8").read().lower())



# =========================================================================
# 5. Warhost - "Martial Grace"
# =========================================================================
print("\n5. Warhost - Martial Grace")

from game import battle_focus, martial_grace as mg  # noqa: E402

_det5 = ae.AELDARI.detachments["Warhost"]
c.eq("3 DP", _det5.points, 3)
c.eq("its rule is named", _det5.rule_name, "Martial Grace")
c.eq("...and it declares the constant the rule reads", _det5.setting, mg.SETTING)
c.true("...which game/detachments.py really writes",
       mg.SETTING in detachments.all_settings())

# --- clause 1: one additional Battle Focus token -------------------------
with settings_as(WARHOST_PLAYERS=()):
    c.eq("no detachment, no extra token", mg.extra_tokens_for("Player 1"), 0)
with settings_as(WARHOST_PLAYERS=("Player 1",)):
    c.eq("with it, one extra", mg.extra_tokens_for("Player 1"), 1)
    c.eq("...and only for that player", mg.extra_tokens_for("Player 2"), 0)

    # Through the REAL pool, because the grant loop is where a player is in
    # scope - a bonus put in tokens_for_battle_size() would have reached both
    # armies, and that mistake reads identically from the module.
    _pool = battle_focus.BattleFocusPool(players=("Player 1", "Player 2"),
                                        battle_size="strike_force")
    _pool.sync_battle_round(1)
    c.eq("Strike Force normally grants 4",
         battle_focus.tokens_for_battle_size("strike_force"), 4)
    c.eq("...so the Warhost player starts the round on 5", _pool.tokens["Player 1"], 5)
    c.eq("...and the opponent still on 4", _pool.tokens["Player 2"], 4)
    # It is per ROUND, not once: the next round grants the extra again.
    _pool.sync_battle_round(2)
    c.eq("and again next round", _pool.tokens["Player 1"], 5)

    # The battle size still decides the base, so this really is "1 additional"
    # rather than a flat number.
    _small = battle_focus.BattleFocusPool(players=("Player 1",), battle_size="incursion")
    _small.sync_battle_round(1)
    c.eq("Incursion 2 + 1", _small.tokens["Player 1"], 3)

# --- clause 2: an additional 1" on Swift as the Wind ---------------------
_wind = sq("Dire Avengers")
_model5 = _wind.models[0]
_printed_move = _model5.profile.movement_in

with settings_as(WARHOST_PLAYERS=("Player 1",)):
    _wind.swift_as_the_wind_active = False
    c.eq("a unit that has not used the manoeuvre gains nothing",
         mg.extra_move_in(_wind), 0.0)
    c.eq("...and its Move is the printed one",
         coldstar.effective_movement_in(_model5), _printed_move)
    _wind.swift_as_the_wind_active = True
    c.eq("having used it, the extra inch applies", mg.extra_move_in(_wind), 1.0)
    # Measured through the ONE function that answers "what is this model's
    # Move right now" - the manoeuvre's own 2" plus Martial Grace's 1".
    c.eq("Swift as the Wind alone is +2, with Martial Grace +3",
         coldstar.effective_movement_in(_model5), _printed_move + 3.0)
with settings_as(WARHOST_PLAYERS=()):
    c.eq("...and without the detachment it is +2 again",
         coldstar.effective_movement_in(_model5), _printed_move + 2.0)
_wind.swift_as_the_wind_active = False

with settings_as(WARHOST_PLAYERS=("Player 2",)):
    _wind.swift_as_the_wind_active = True
    c.eq("the other player fielding it does not help this unit",
         mg.extra_move_in(_wind), 0.0)
_wind.swift_as_the_wind_active = False

# --- clause 3: +1 on an Agile Manoeuvre's D6 -----------------------------
with settings_as(WARHOST_PLAYERS=("Player 1",)):
    c.eq("the roll bonus applies", mg.roll_bonus_for(_wind), 1)
    c.eq("...but not for the opponent", mg.roll_bonus_for(sq("Rangers", "Player 2")), 0)
with settings_as(WARHOST_PLAYERS=()):
    c.eq("...and not without the detachment", mg.roll_bonus_for(_wind), 0)

# WHICH MANOEUVRES ROLL A D6 IS MEASURED. Of the six, only Opportunity Seized
# and Fade Back throw anything, and both go through the one call this clause
# hangs on. Sudden Strike is the near-miss - its "up to 6 inches" is a
# distance, not a die - so the count is pinned rather than described.
_bf_src = io.open("game/battle_focus.py", encoding="utf-8").read()
c.eq("exactly one D6 is rolled anywhere in the army rule",
     _bf_src.count("count=1, sides=6"), 1)
c.eq("...and the roll bonus is applied at exactly that one place",
     _bf_src.count("martial_grace.roll_bonus_for("), 1)
c.true("...to the RESULT, not to the die",
       "distance += martial_grace.roll_bonus_for(squad)" in _bf_src)

# All three clauses land in the army rule's own seams, each exactly once.
c.eq("the token clause is in the grant loop",
     _bf_src.count("martial_grace.extra_tokens_for(player)"), 1)
c.eq("the move clause is in movement_bonus_in()",
     _bf_src.count("martial_grace.extra_move_in(squad)"), 1)

# No ASURYANI test is needed and none is written: has_battle_focus() already
# restricts every clause to units that print the ability. Pinned so that a
# later reader does not add a second gate meaning the same thing.
c.true("the module does not re-check ASURYANI",
       "is_asuryani_unit" not in io.open("game/martial_grace.py", encoding="utf-8").read())

for _needle in ("martial_grace", "warhost"):
    c.true("ai/agent_driver.py never mentions %s" % _needle,
           _needle not in io.open("ai/agent_driver.py", encoding="utf-8").read().lower())



# =========================================================================
# 6. Windrider Host - "Ride the Wind"
# =========================================================================
print("\n6. Windrider Host - Ride the Wind")

from game import ride_the_wind as rtw  # noqa: E402
from game.ingress import INGRESS_MIN_BATTLE_ROUND  # noqa: E402

_det6 = ae.AELDARI.detachments["Windrider Host"]
c.eq("2 DP", _det6.points, 2)
c.eq("its rule is named", _det6.rule_name, "Ride the Wind")
c.eq("...and it declares the constant the rule reads", _det6.setting, rtw.SETTING)
c.true("...which game/detachments.py really writes",
       rtw.SETTING in detachments.all_settings())

_windriders = sq("Windriders")            # ASURYANI MOUNTED
_vypers = sq("Vypers")                    # VYPERS (a VEHICLE, not MOUNTED)
_spears6 = sq("Shining Spears")           # ASURYANI MOUNTED too
_avengers6 = sq("Dire Avengers")          # neither
_yncarne = sq("The Yncarne")              # AELDARI but NOT ASURYANI

with settings_as(WINDRIDER_HOST_PLAYERS=()):
    c.true("without the detachment nothing qualifies", not rtw.applies(_windriders))
with settings_as(WINDRIDER_HOST_PLAYERS=("Player 1",)):
    c.true("Windriders qualify - ASURYANI MOUNTED", rtw.applies(_windriders))
    c.true("...and Vypers, by their own keyword", rtw.applies(_vypers))
    c.true("...and Shining Spears, also ASURYANI MOUNTED", rtw.applies(_spears6))
    c.true("...but not infantry", not rtw.applies(_avengers6))
    c.true("...nor the other player's Windriders",
           not rtw.applies(sq("Windriders", "Player 2")))
    # The ASURYANI half cannot discriminate on the built roster - measured:
    # nothing MOUNTED is Ynnari, so every MOUNTED unit passes it anyway. It is
    # still written, because it is printed; and it is isolated by hand, because
    # a probe against a real unit would fail on the MOUNTED half instead and
    # prove nothing (the masking that has made an A/B probe pass three times
    # before in this project).
    c.true("a non-ASURYANI Aeldari unit does not qualify", not rtw.applies(_yncarne))
    c.true("...but only because it is not MOUNTED either",
           not attached_units.unit_has_datasheet_keyword(_yncarne, "MOUNTED"))
    _mounted_ynnari = [n for n, ds in D.items()
                       if "MOUNTED" in (ds.keywords or ())
                       and "ASURYANI" not in ds.faction_keywords]
    c.eq("no built datasheet is MOUNTED and non-ASURYANI, so the clause is inert today",
         _mounted_ynnari, [])

    class _RTWSheet:
        name = "Hypothetical Ynnari Jetbike"
        keywords = ("MOUNTED", "AELDARI")
        faction_keywords = ("YNNARI",)

    class _RTWSquad:
        owner = "Player 1"
        datasheet = _RTWSheet()
        attached_components = ()
        models = ()

    c.true("a hand-built MOUNTED unit that is YNNARI-only is refused - the "
           "clause does work, there is just nothing on the roster for it to bite",
           not rtw.applies(_RTWSquad()))

    class _RTWAsuryani(_RTWSquad):
        class datasheet:
            name = "Hypothetical Asuryani Jetbike"
            keywords = ("MOUNTED", "AELDARI")
            faction_keywords = ("ASURYANI",)

    c.true("...while the same unit as ASURYANI qualifies", rtw.applies(_RTWAsuryani()))

    # --- the round clause -------------------------------------------------
    c.eq("+1", rtw.RIDE_THE_WIND_ROUND_BONUS, 1)
    c.eq("a qualifying unit counts round 1 as round 2",
         rtw.arrival_battle_round(_windriders, 1), 2)
    c.eq("...and everything else is untouched",
         rtw.arrival_battle_round(_avengers6, 1), 1)
    c.eq("...including a None round", rtw.arrival_battle_round(_windriders, None), None)

    # Through the REAL gate. Rule 20.03 forbids arrival before round 2, so a
    # Windrider unit may come in during round 1 and a Dire Avengers unit may
    # not - the whole point of the clause.
    class _Round:
        def __init__(self, n):
            self.battle_round = n

    _state6 = tk.GameState()
    _state6.reserves = [_windriders, _avengers6]
    from game.ingress import IngressController  # noqa: E402
    _ing = IngressController(None, _state6, [], turn_tracker=_Round(1))
    c.eq("rule 20.03 normally forbids arrival before round 2",
         INGRESS_MIN_BATTLE_ROUND, 2)
    c.true("a Windrider unit may arrive in round 1", _ing.can_ingress(_windriders))
    c.true("...while an ordinary unit may not", not _ing.can_ingress(_avengers6))
    _ing.turn_tracker = _Round(2)
    c.true("...and in round 2 both may", _ing.can_ingress(_avengers6))

    # THE SCOPE. "For the purposes of SETTING UP" - the counter itself is not
    # touched, so nothing else in the game sees a different round.
    c.eq("the real battle round is unchanged", _ing.turn_tracker.battle_round, 2)

with settings_as(WINDRIDER_HOST_PLAYERS=()):
    _ing2 = IngressController(None, tk.GameState(), [], turn_tracker=_Round(1))
    _ing2.game_state.reserves = [_windriders]
    c.true("without the detachment, round 1 is refused again",
           not _ing2.can_ingress(_windriders))

# --- the withdrawal clause and its cap -----------------------------------
c.eq("Incursion pulls back 1", rtw.withdrawal_limit("incursion"), 1)
c.eq("Strike Force 2", rtw.withdrawal_limit("strike_force"), 2)
c.eq("Onslaught 3", rtw.withdrawal_limit("onslaught"), 3)
c.eq("an unknown size falls back to Strike Force rather than to zero - zero "
     "would make the clause silently inert",
     rtw.withdrawal_limit("nonsense"), 2)
c.eq("...and the default comes from config.BATTLE_SIZE",
     rtw.withdrawal_limit(), rtw.withdrawal_limit(config.BATTLE_SIZE))

with settings_as(WINDRIDER_HOST_PLAYERS=("Player 1",)):
    _free = sq("Windriders")
    _stuck = sq("Shining Spears")
    _foe6 = sq("Guardian Defenders", "Player 2")
    tk.line_up(_free, 10.0, 10.0, spacing=1.4)
    tk.line_up(_stuck, 40.0, 40.0, spacing=1.4)
    tk.line_up(_foe6, 40.0, 40.6, spacing=1.4)          # inside Engagement Range
    _tokens6 = list(_free.models) + list(_stuck.models) + list(_foe6.models)
    c.true("a unit clear of the enemy is not engaged", not rtw.is_engaged(_free, _tokens6))
    c.true("...and one in Engagement Range is", rtw.is_engaged(_stuck, _tokens6))

    _gs6 = tk.GameState()
    _gs6.tokens = list(_tokens6)
    _gs6.reserves = []
    _ctrl6 = rtw.RideTheWindController(game_state=_gs6, all_tokens=_tokens6,
                                       battle_size="strike_force")
    c.true("the free unit may be pulled back", _ctrl6.can_use(_free))
    c.true("...but the engaged one may not - the printed exclusion",
           not _ctrl6.can_use(_stuck))
    c.eq("two withdrawals are allowed this turn", _ctrl6.remaining(), 2)
    c.true("using it works", _ctrl6.use(_free))
    c.eq("...and spends one of the two", _ctrl6.remaining(), 1)
    c.true("...and the unit really is in reserves", _free in _gs6.reserves)
    c.true("...and off the board", not any(t.squad is _free for t in _gs6.tokens))
    c.true("...so it cannot be pulled back twice", not _ctrl6.can_use(_free))

    # The cap really caps.
    _a, _b, _cc = sq("Windriders"), sq("Shining Spears"), sq("Warlock Skyrunners")
    for _u in (_a, _b, _cc):
        tk.line_up(_u, 10.0, 10.0, spacing=1.4)
    _gs7 = tk.GameState()
    _gs7.tokens = list(_a.models) + list(_b.models) + list(_cc.models)
    _gs7.reserves = []
    _ctrl7 = rtw.RideTheWindController(game_state=_gs7, all_tokens=_gs7.tokens,
                                       battle_size="incursion")
    c.eq("Incursion allows one", _ctrl7.remaining(), 1)
    c.true("the first goes back", _ctrl7.use(_a))
    c.true("...and the second is refused by the cap", not _ctrl7.can_use(_b))
    # The cap is per TURN, so a fresh offer window resets it.
    _ctrl7.offer_at_end_of_turn({_b, _cc}, ending_player="Player 2")
    c.eq("a new turn's window resets the cap", _ctrl7.remaining(), 1)

# TWO MEASURED NO-OPS, written out rather than dropped.
_bl = [n for n, ds in D.items() if "BATTLELINE" in (ds.keywords or ())]
c.true("BATTLELINE is printed on some Aeldari datasheets", len(_bl) > 0)
_aeldari_modules = io.open("game/ride_the_wind.py", encoding="utf-8").read()
c.true("...but this rule does not try to grant it, and says why",
       "BATTLELINE" in _aeldari_modules and "no-op" in _aeldari_modules.lower())
c.true("...and no Aeldari rule module reads the keyword",
       "BATTLELINE" not in io.open("game/battle_focus.py", encoding="utf-8").read())

# BOTH arrival gates take the adjusted number: one of them alone looks complete.
_ing_src = io.open("game/ingress.py", encoding="utf-8").read()
c.eq("both arrival gates read the adjusted round",
     _ing_src.count("ride_the_wind.arrival_battle_round("), 2)

_main6 = io.open("main.py", encoding="utf-8").read()
c.true("main.py builds the controller",
       "ride_the_wind_controller = RideTheWindController(" in _main6)
c.true("...and offers it at the end of a turn, to whoever is NOT ending it",
       "ride_the_wind_controller.offer_at_end_of_turn(" in _main6)

for _needle in ("ride_the_wind", "windrider host"):
    c.true("ai/agent_driver.py never mentions %s" % _needle,
           _needle not in io.open("ai/agent_driver.py", encoding="utf-8").read().lower())



# =========================================================================
# 7. Spirit Conclave - "Shepherds of the Dead"
# =========================================================================
print("\n7. Spirit Conclave - Shepherds of the Dead")

from game import shepherds_of_the_dead as sotd, status_effects as se  # noqa: E402

_det7 = ae.AELDARI.detachments["Spirit Conclave"]
c.eq("2 DP", _det7.points, 2)
c.eq("its rule is named", _det7.rule_name, "Shepherds of the Dead")
c.eq("...and it declares the constant the rule reads", _det7.setting, sotd.SETTING)
c.true("...which game/detachments.py really writes",
       sotd.SETTING in detachments.all_settings())
c.eq("the bonus is a -1 on the threshold", sotd.VENGEFUL_DEAD_BONUS, -1)

# The mark needs a board label or it is invisible - and this one never expires,
# so a unit could carry it for the rest of the battle with nothing to show.
c.true("Vengeful Dead has a board label", se.VENGEFUL_DEAD in se.LABELS)
c.eq("...two letters, like its eight siblings", se.LABELS[se.VENGEFUL_DEAD], "VD")

_farseer7 = sq("Farseer")
_wraithguard = sq("Wraithguard")
_wraithlord = sq("Wraithlord")
_avengers7 = sq("Dire Avengers")
_killer = sq("Guardian Defenders", "Player 2")

with settings_as(SPIRIT_CONCLAVE_PLAYERS=("Player 1",)):
    _ctrl7b = sotd.ShepherdsOfTheDeadController(game_log=tk.Log())

    # --- the trigger ------------------------------------------------------
    _psyker_model = next(m for m in _farseer7.models if m.profile.psyker)
    c.true("a Farseer is an ASURYANI PSYKER model",
           sotd.is_asuryani_psyker_model(_psyker_model, _farseer7))
    c.true("killing one marks the killer",
           _ctrl7b.notify_psyker_destroyed(_psyker_model, _farseer7, _killer))
    c.true("...and the killer carries a token", _ctrl7b.is_marked(_killer))
    c.eq("...exactly one", _ctrl7b.tokens_on(_killer), 1)

    # CUMULATIVE. "one or MORE tokens" - the count is printed, so it is kept.
    _ctrl7b.notify_psyker_destroyed(_psyker_model, _farseer7, _killer)
    c.eq("a second psyker adds a second token", _ctrl7b.tokens_on(_killer), 2)

    # THE ASURYANI HALF, which is the one place the faction keyword pays for
    # itself: Yvraine and The Yncarne are PSYKERs and are NOT ASURYANI.
    _yvraine7 = sq("Yvraine")
    _yv_model = next(m for m in _yvraine7.models if m.profile.psyker)
    c.true("Yvraine is a PSYKER", _yv_model.profile.psyker)
    c.true("...but not an ASURYANI one",
           not sotd.is_asuryani_psyker_model(_yv_model, _yvraine7))
    _ctrl7c = sotd.ShepherdsOfTheDeadController()
    c.true("...so killing her marks nobody",
           not _ctrl7c.notify_psyker_destroyed(_yv_model, _yvraine7, _killer))
    _psyker_sheets = [n for n in D if any(m.profile.psyker for m in sq(n).models)]
    c.eq("eleven PSYKER datasheets", len(_psyker_sheets), 11)
    c.eq("...two of which are not ASURYANI",
         sorted(n for n in _psyker_sheets if "ASURYANI" not in D[n].faction_keywords),
         ["The Yncarne", "Yvraine"])

    # A non-psyker death marks nobody, and neither does a friendly kill.
    _ctrl7d = sotd.ShepherdsOfTheDeadController()
    c.true("a non-psyker death marks nobody",
           not _ctrl7d.notify_psyker_destroyed(_avengers7.models[0], _avengers7, _killer))
    c.true('"destroyed BY AN ENEMY UNIT" - a friendly kill marks nobody',
           not _ctrl7d.notify_psyker_destroyed(
               _psyker_model, _farseer7, sq("Dire Avengers", "Player 1")))
    c.true("...and an unknown killer marks nobody",
           not _ctrl7d.notify_psyker_destroyed(_psyker_model, _farseer7, None))

    # --- who benefits -----------------------------------------------------
    c.true("Wraithguard are a WRAITH CONSTRUCT", sotd.is_wraith_construct(_wraithguard))
    c.true("...and so is a Wraithlord", sotd.is_wraith_construct(_wraithlord))
    c.true("...but Dire Avengers are not", not sotd.is_wraith_construct(_avengers7))
    c.true("a WRAITH CONSTRUCT attacking a marked unit gets it",
           _ctrl7b.grants(_wraithguard, _killer))
    c.true("...but not against an unmarked one",
           not _ctrl7b.grants(_wraithguard, sq("Storm Guardians", "Player 2")))
    c.true("...and a non-wraith unit gets nothing even against a marked one",
           not _ctrl7b.grants(_avengers7, _killer))

    # BOTH ROLLS, one condition.
    c.eq("one hit modifier", len(_ctrl7b.hit_modifiers(_wraithguard, _killer)), 1)
    c.eq("one wound modifier", len(_ctrl7b.wound_modifiers(_wraithguard, _killer)), 1)
    c.eq("...both named for the token",
         _ctrl7b.hit_modifiers(_wraithguard, _killer)[0].source, "Vengeful Dead")
    c.eq("...and both -1",
         (_ctrl7b.hit_modifiers(_wraithguard, _killer)[0].amount,
          _ctrl7b.wound_modifiers(_wraithguard, _killer)[0].amount), (-1, -1))

with settings_as(SPIRIT_CONCLAVE_PLAYERS=()):
    c.true("without the detachment nothing is granted",
           not _ctrl7b.grants(_wraithguard, _killer))
    c.true("...and no new tokens are handed out",
           not sotd.ShepherdsOfTheDeadController().notify_psyker_destroyed(
               _psyker_model, _farseer7, _killer))

# IT NEVER EXPIRES - the one thing that distinguishes it from all eight other
# marks, and the thing most likely to be "fixed" by a later reader.
c.true("the controller has no reset_turn()", not hasattr(_ctrl7b, "reset_turn"))
c.true("...and no reset_phase()", not hasattr(_ctrl7b, "reset_phase"))
_sotd_src = io.open("game/shepherds_of_the_dead.py", encoding="utf-8").read()
c.true("...and says why in as many words", "NEVER EXPIRES" in _sotd_src)

# --- Spirit Guides -------------------------------------------------------
with settings_as(SPIRIT_CONCLAVE_PLAYERS=("Player 1",)):
    tk.line_up(_farseer7, 20.0, 20.0, spacing=1.2)
    tk.line_up(_wraithguard, 20.0, 25.0, spacing=1.4)      # within 12"
    _far = sq("Wraithblades")
    tk.line_up(_far, 20.0, 60.0, spacing=1.4)              # far away
    _tok7 = list(_farseer7.models) + list(_wraithguard.models) + list(_far.models)
    _aura = sotd.ShepherdsOfTheDeadController(all_tokens=_tok7)
    c.eq('the aura is 12 inches', sotd.SPIRIT_GUIDES_RANGE_IN, 12.0)
    c.true("a wraith unit within 12in of the psyker is reached",
           _aura.spirit_guides_reaches(_wraithguard))
    c.true("...and one far away is not", not _aura.spirit_guides_reaches(_far))
    # The non-wraith case must stand INSIDE the aura, or it is refused for
    # being out of range and says nothing about the keyword filter - the
    # masking that has now made a probe pass four times in this project.
    tk.line_up(_avengers7, 20.0, 21.0, spacing=1.2)
    _aura.all_tokens = list(_tok7) + list(_avengers7.models)
    c.true("a non-wraith unit standing right beside the psyker is still not reached",
           not _aura.spirit_guides_reaches(_avengers7))
    c.true("...and it really is inside the 12 inches",
           min(((m.x_in - _farseer7.models[0].x_in) ** 2
                + (m.y_in - _farseer7.models[0].y_in) ** 2) ** 0.5
               for m in _avengers7.models) <= sotd.SPIRIT_GUIDES_RANGE_IN)

    # THIS BLOCK USED TO RECORD A BUG AS IF IT WERE THE RULE. It said the aura
    # was "a near-no-op on the built roster, measured: all three named
    # datasheets already print Battle Focus" - and they did, in the ENGINE.
    # They do not on their PRINTED datasheets: Wraithguard, Wraithblades and
    # Wraithlord carry no FACTION line at all, where every Aeldari sheet that
    # HAS the army rule prints "FACTION: **Battle Focus**". The flag was a
    # transcription error, and it made this whole half of Spirit Guides inert -
    # the aura granted its targets what they already had.
    #
    # Corrected, the aura is the ONLY way those three units ever get Battle
    # Focus, which is what the printed text means by "that unit HAS the Battle
    # Focus ability".
    c.true("none of the three named datasheets prints Battle Focus itself",
           not any(any(m.profile.battle_focus for m in sq(n).models)
                   for n in ("Wraithblades", "Wraithguard", "Wraithlord")))

    class _NoFocusProfile:
        battle_focus = False
        psyker = False
        name = "Hypothetical Ghost"

        def __init__(self):
            self.x_in = self.y_in = 0.0

    class _NoFocusModel:
        def __init__(self, x, y):
            self.profile = _NoFocusProfile()
            self.x_in, self.y_in = x, y

        def is_dead(self):
            return False

    class _NoFocusSquad:
        owner = "Player 1"
        datasheet = D["Wraithguard"]
        attached_components = ()

        def __init__(self):
            self.models = [_NoFocusModel(20.0, 22.0)]

    _nofocus = _NoFocusSquad()
    c.true("a wraith unit that does NOT print Battle Focus has none on its own",
           not battle_focus.has_battle_focus(_nofocus))
    _nofocus.spirit_guides_source = _aura
    c.true("...and gains it from the aura - which is what the clause does",
           battle_focus.has_battle_focus(_nofocus))
    _far_nofocus = _NoFocusSquad()
    _far_nofocus.models = [_NoFocusModel(20.0, 60.0)]
    _far_nofocus.spirit_guides_source = _aura
    c.true("...but only inside 12in", not battle_focus.has_battle_focus(_far_nofocus))

# The BATTLELINE clause is a measured no-op, named rather than dropped.
c.true("the module names the BATTLELINE clause and calls it a no-op",
       "BATTLELINE" in _sotd_src and "no-op" in _sotd_src.lower())

# FOUR SEAMS, TWO FILES - a wiring that reaches three looks complete from any
# one of them.
for _f in ("game/shooting.py", "game/fight.py"):
    _src7 = io.open(_f, encoding="utf-8").read()
    c.eq("%s reads the hit half once" % _f,
         _src7.count("shepherds_of_the_dead.hit_modifiers("), 1)
    c.eq("%s reads the wound half once" % _f,
         _src7.count("shepherds_of_the_dead.wound_modifiers("), 1)

_main7 = io.open("main.py", encoding="utf-8").read()
c.true("main.py builds the controller",
       "shepherds_of_the_dead_controller = ShepherdsOfTheDeadController(" in _main7)
c.true("...hands it to both attack controllers",
       "fight_controller.shepherds_of_the_dead = shepherds_of_the_dead_controller" in _main7
       and "shooting_controller.shepherds_of_the_dead = shepherds_of_the_dead_controller" in _main7)
c.true("...feeds it from the per-MODEL death sweep",
       "shepherds_of_the_dead_controller.notify_psyker_destroyed(" in _main7)
c.true("...and stamps the aura back-reference every frame",
       "shepherds_of_the_dead_controller.attach_to(" in _main7)

for _needle in ("shepherds_of_the_dead", "spirit conclave", "vengeful dead"):
    c.true("ai/agent_driver.py never mentions %s" % _needle,
           _needle not in io.open("ai/agent_driver.py", encoding="utf-8").read().lower())

# --- all seven, together --------------------------------------------------
print("\n   all seven")
_built = ["Armoured Warhost", "Path of the Outcast", "Guardian Battlehost",
          "Aspect Host", "Warhost", "Windrider Host", "Spirit Conclave"]
c.eq("the Aeldari now model Seer Council plus the seven",
     list(ae.AELDARI.detachments), ["Seer Council"] + _built)
for _name in _built:
    _d = ae.AELDARI.detachments[_name]
    c.true("%s names its rule" % _name, bool(_d.rule_name))
    c.true("%s carries the printed rule text" % _name, len(_d.rule_text or "") > 80)
    c.true("%s declares a setting game/detachments.py writes" % _name,
           _d.setting in detachments.all_settings())
    c.eq("%s declares no exclusion tag" % _name, _d.tag, None)
    c.eq("%s leaves its stratagems as data for now" % _name, _d.stratagems, [])
    # THE COUNT COMES FROM THE CORPUS, not from a number in a comment - the same
    # guard the Stratagem count uses, and for the same reason: a figure written
    # by hand once read 30 where the corpus said 36.
    _printed = _corpus_enhancement_names(_name)
    c.eq("%s declares every Enhancement its page prints" % _name,
         sorted(e.name for e in _d.enhancements), sorted(_printed))
    c.true("%s prices them as printed" % _name,
           all(e.points == _printed[e.name] for e in _d.enhancements))
# The DP costs are transcribed from each page's own heading line.
c.eq("the seven DP costs",
     {n: ae.AELDARI.detachments[n].points for n in _built},
     {"Armoured Warhost": 1, "Path of the Outcast": 1, "Guardian Battlehost": 2,
      "Aspect Host": 3, "Warhost": 3, "Windrider Host": 2, "Spirit Conclave": 2})
# ONE of the seven is now fielded, and the other six are still declared-only.
# When these rules were built the pin here read "Seer Council and nothing
# else", because the whole batch was verified with a selfplay run each rather
# than made the default. Path of the Outcast came off that shelf on 2026-09-01
# (user: "detechments: Seer Council + Path of the Outcast"), which is exactly
# the visible one-line change the pin existed to force.
c.eq("the Aeldari list fields Seer Council + Path of the Outcast",
     detachments.names_for("aeldari"), ["Seer Council", "Path of the Outcast"])
c.eq("...and is still legal", detachments.validate("aeldari"), [])
# 2 + 1 against a budget of 3: the pair is at the ceiling, so a THIRD cannot be
# added without something else giving way. Pinned because "legal" above would
# stay green with a DP or two to spare and would not say how close it is.
c.eq("...spending exactly the budget", detachments.points_for("aeldari"),
     detachments.DETACHMENT_POINT_BUDGET)
# The other six stay declared-only, so this pin keeps doing its job for them.
c.eq("the other six are still declared, not fielded",
     sorted(n for n in _built if n not in detachments.names_for("aeldari")),
     sorted(n for n in _built if n != "Path of the Outcast"))
# Far-Reaching Doom is not a dormant grant on this roster: it reads friendly
# RANGERS/SHROUD RUNNERS units, and the list fields Rangers. Measured, because
# a detachment whose rule can never fire would be a different kind of change
# from the one that was asked for.
from game import army_lists  # noqa: E402
_aeldari_units = []
army_lists.get("aeldari").build("Player 1", _aeldari_units.append)
_saved_path = config.PATH_OF_THE_OUTCAST_PLAYERS
config.PATH_OF_THE_OUTCAST_PLAYERS = ("Player 1",)
try:
    c.true("...and Far-Reaching Doom has a unit to fire on (the Rangers)",
           any(frd.applies(u) for u in _aeldari_units))
finally:
    config.PATH_OF_THE_OUTCAST_PLAYERS = _saved_path


c.finish()
