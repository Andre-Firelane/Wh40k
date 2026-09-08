"""The 28 Aeldari detachment Enhancements.

The seven detachments' RULES and their 36 Stratagems are built; these are the
Enhancements - 24 of the seven plus Seer Council's four, because Seer Council is
the one Aeldari detachment the army list actually fields and therefore the only
one where a grant could ever be live in a default game.

Cut by MECHANISM rather than by detachment (user decision), so a section here is
a SEAM and its members come from several detachments.

Sections:
  0. The registry, the bearer predicates, and what grant() refuses.
  0b. The extractions this batch made, each pinned behaviour-neutral.
  1. Objective Control - Craftworld's Champion, Strategic Savant,
     Light of Clarity.
"""

import io
import os
import re
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import testkit as tk  # noqa: E402
from game import attached_units, config, enhancements as E  # noqa: E402
from game.factions.aeldari import AELDARI  # noqa: E402
from game.units import UnitProfile  # noqa: E402
from game import fight as _gf  # noqa: E402

c = tk.Checks("Aeldari Enhancements")
D = AELDARI.datasheets
HUMAN = "Player 1"

#: Every Aeldari detachment name, for scoping the registry.
AELDARI_DETACHMENTS = {d.name for d in AELDARI.detachments.values()}
SPECS = {name: spec for name, spec in E.ENHANCEMENTS.items()
         if spec.detachment in AELDARI_DETACHMENTS}


# The one definition lives in testkit - eight suites had their own copy.
settings_as = tk.settings_as

ALL_SETTINGS = sorted({spec.setting for spec in E.ENHANCEMENTS.values()})


def only(setting, players=(HUMAN,)):
    """Field exactly one detachment and EMPTY every other, so a check can never
    pass because some other detachment happened to be on."""
    return settings_as(**{s: (tuple(players) if s == setting else ())
                          for s in ALL_SETTINGS})


def none_fielded():
    return settings_as(**{s: () for s in ALL_SETTINGS})


def before(src, first, second):
    """`first` appears in `src`, and before `second`. NOT str.index(): a
    missing needle would RAISE and abort the run instead of turning one line
    red - a trap this repo has met three times."""
    i, j = src.find(first), src.find(second)
    return i != -1 and j != -1 and i < j


def refused(squad, name):
    """grant()'s refusal MESSAGE, or None when it succeeds. Every refusal path
    is a ValueError rather than a silent skip, because this runs while the
    scene is built and a dropped Enhancement shows up much later as "the rule
    never triggers"."""
    try:
        E.grant(squad, name)
    except ValueError as exc:
        return str(exc)
    return None


def sq(name, owner=HUMAN):
    return tk.build(D[name], owner, name="%s %s 1" % (owner[-1], name))


def corpus_enhancements(detachment_name):
    """{name: points} straight off the detachment's corpus page - the same
    reader test_aeldari_detachment_rules.py uses, and for the same reason: a
    count written by hand once read 30 where the corpus said 36."""
    path = os.path.join("rules", "aeldari", "detachments", "%s.md" % detachment_name)
    src = io.open(path, encoding="utf-8").read()
    section = src.split("## Enhancements", 1)[1].split("## Stratagems", 1)[0]
    out = {}
    for line in section.splitlines():
        m = re.match(r"^### (.+?) - (\d+) pts\s*$", line.strip())
        if m:
            out[m.group(1).replace("’", "'")] = int(m.group(2))
    return out


# =========================================================================
# 0. The registry
# =========================================================================
print("\n0. The registry")

c.eq("28 Aeldari Enhancements are engine-wired", len(SPECS), 28)
# Counted per detachment, so a 29th cannot appear without this line moving.
for _det, _n in (("Aspect Host", 4), ("Guardian Battlehost", 4), ("Warhost", 4),
                 ("Windrider Host", 4), ("Spirit Conclave", 4),
                 ("Armoured Warhost", 2), ("Path of the Outcast", 2),
                 ("Seer Council", 4)):
    c.eq("%s has %d" % (_det, _n), len(E.for_detachment(_det)), _n)

# ...and the counts come from the CORPUS, not from these literals.
_corpus_total = 0
for _det in sorted(AELDARI_DETACHMENTS):
    _printed = corpus_enhancements(_det)
    _corpus_total += len(_printed)
    c.eq("%s declares exactly what its page prints" % _det,
         sorted(s.name for s in E.for_detachment(_det)), sorted(_printed))
    c.true("%s prices them as printed" % _det,
           all(s.points == _printed[s.name] for s in E.for_detachment(_det)))
c.eq("...and the corpus itself says 28", _corpus_total, 28)

# Points and detachment agree with the descriptive faction record. Pinned
# against each other rather than against literals - the assurance that matters
# is that the two tables cannot drift.
_recorded = {}
for _detachment in AELDARI.detachments.values():
    for _e in _detachment.enhancements:
        _recorded[_e.name] = (_e.points, _detachment.name)
c.eq("points and detachment match game/factions/aeldari.py's own record",
     [n for n, s in SPECS.items() if _recorded.get(n) != (s.points, s.detachment)], [])

c.true("every Aeldari flag is declared on UnitProfile",
       all(hasattr(UnitProfile, s.flag) for s in SPECS.values()))
c.true("...and defaults to False",
       all(getattr(UnitProfile, s.flag) is False for s in SPECS.values()))
c.eq("28 DISTINCT flags", len({s.flag for s in SPECS.values()}), 28)

# EXACTLY TWO are unit-level - "RANGERS unit only" and "RANGERS/SHROUD RUNNERS
# unit only". The other 26 say "model only", and reading one as the other would
# hand a 10-point upgrade to a whole squad.
c.eq("two unit-level Enhancements",
     sorted(n for n, s in SPECS.items() if s.unit_level),
     ["Assassins' Eye", "Camouflaged Snipers"])

# --- the bearer predicates, at their printed boundaries -------------------
# NINE shapes across the 28, measured off the corpus - so nine predicates,
# not 28 near-copies.
_shapes = {}
for _spec in SPECS.values():
    _shapes.setdefault(_spec.bearer_text, []).append(_spec.name)
c.eq("the 28 printed clauses fall into nine shapes", len(_shapes), 9)

_farseer = sq("Farseer")             # ASURYANI PSYKER, on foot
_autarch = sq("Autarch")
_spiritseer = sq("Spiritseer")
_skyrunner = sq("Warlock Skyrunners")   # ASURYANI MOUNTED PSYKER
_rangers = sq("Rangers")
_shroud = sq("Shroud Runners")
_avengers = sq("Dire Avengers")      # ASURYANI, no psyker, not mounted
_yvraine = sq("Yvraine")             # AELDARI PSYKER but NOT ASURYANI

with only("SEER_COUNCIL_PLAYERS"):
    c.true("a Farseer can bear an ASURYANI PSYKER Enhancement",
           E.ENHANCEMENTS["Lucid Eye"].can_bear(_farseer.models[0], _farseer))
    # THE MEASURED LIMIT, stated where it bites: ASURYANI is a FACTION keyword
    # on the DATASHEET, and this engine has no per-model faction keyword - the
    # same gap _is_tau() records. Yvraine is AELDARI and NOT ASURYANI, which is
    # exactly the case that makes the two clauses different sets.
    c.true("...and Yvraine cannot - she is AELDARI, not ASURYANI",
           not E.ENHANCEMENTS["Lucid Eye"].can_bear(_yvraine.models[0], _yvraine))
    c.true("...while an AELDARI PSYKER clause DOES take her",
           E.ENHANCEMENTS["Guiding Presence"].can_bear(_yvraine.models[0], _yvraine))
# The plain "ASURYANI model only" clause needs its own driving - five of the
# 28 use it and none of the checks above touch it.
with only("GUARDIAN_BATTLEHOST_PLAYERS"):
    c.true("an ASURYANI model only clause takes a Dire Avenger",
           E.ENHANCEMENTS["Craftworld's Champion"].can_bear(
               _avengers.models[0], _avengers))
    c.true("...and refuses Yvraine, who is AELDARI but not ASURYANI",
           not E.ENHANCEMENTS["Craftworld's Champion"].can_bear(
               _yvraine.models[0], _yvraine))
    c.true("...and a non-psyker ASURYANI does not qualify either",
           not E.ENHANCEMENTS["Lucid Eye"].can_bear(_avengers.models[0], _avengers))

c.true("the Autarch clause names two datasheets",
       E.ENHANCEMENTS["Aspect of Murder"].can_bear(_autarch.models[0], _autarch))
c.true("...and refuses a Farseer",
       not E.ENHANCEMENTS["Aspect of Murder"].can_bear(_farseer.models[0], _farseer))
# A MEASURED NO-OP, pinned so it does not read as an untested branch: only two
# datasheets contain the string "Autarch" and both ARE Autarchs, so a substring
# match and an exact match cannot disagree on this roster. The exact match is
# kept because _is_kroot_shaper()'s substring form is the looseness this avoids.
c.eq("only the two Autarch datasheets contain the word",
     sorted(n for n in D if "Autarch" in n), ["Autarch", "Autarch Wayleaper"])
c.true("the SPIRITSEER clause takes a Spiritseer",
       E.ENHANCEMENTS["Light of Clarity"].can_bear(_spiritseer.models[0], _spiritseer))
c.true("...and refuses an Autarch",
       not E.ENHANCEMENTS["Light of Clarity"].can_bear(_autarch.models[0], _autarch))
# MEASURED, and the reason the predicate reads the KEYWORD: UnitProfile.mounted
# is a strict subset of the datasheet keyword - four Aeldari datasheets carry
# the keyword with no flag, and they are exactly the Windrider units these four
# Enhancements exist for.
_mounted_flag = {n for n in sorted(D)
                 if any(getattr(m.profile, "mounted", False) for m in sq(n).models)}
_mounted_kw = {n for n in sorted(D)
               if attached_units.unit_has_datasheet_keyword(sq(n), "MOUNTED")}
c.eq("no datasheet has the MOUNTED flag without the keyword",
     sorted(_mounted_flag - _mounted_kw), [])
c.eq("...but four have the keyword without the flag",
     sorted(_mounted_kw - _mounted_flag),
     ["Shining Spears", "Shroud Runners", "Warlock Skyrunners", "Windriders"])
c.true("the MOUNTED clause takes a Warlock Skyrunner",
       E.ENHANCEMENTS["Firstdrawn Blade"].can_bear(_skyrunner.models[0], _skyrunner))
c.true("...and a Windrider, which has no profile flag at all",
       E.ENHANCEMENTS["Firstdrawn Blade"].can_bear(
           sq("Windriders").models[0], sq("Windriders")))
c.true("...and refuses a Farseer on foot",
       not E.ENHANCEMENTS["Firstdrawn Blade"].can_bear(_farseer.models[0], _farseer))
c.true("the MOUNTED PSYKER clause needs all three",
       E.ENHANCEMENTS["Seersight Strike"].can_bear(_skyrunner.models[0], _skyrunner))
c.true("the RANGERS unit clause takes Rangers",
       E.ENHANCEMENTS["Camouflaged Snipers"].can_bear(_rangers.models[0], _rangers))
c.true("...and NOT Shroud Runners, which the other one names",
       not E.ENHANCEMENTS["Camouflaged Snipers"].can_bear(_shroud.models[0], _shroud))
c.true("...while RANGERS/SHROUD RUNNERS takes both",
       E.ENHANCEMENTS["Assassins' Eye"].can_bear(_rangers.models[0], _rangers)
       and E.ENHANCEMENTS["Assassins' Eye"].can_bear(_shroud.models[0], _shroud))

# --- grant() --------------------------------------------------------------
_grant_seer = sq("Spiritseer")
_before_points = _grant_seer.points
c.eq("granting sets the flag on the bearer's own profile instance",
     E.grant(_grant_seer, "Light of Clarity").profile.light_of_clarity, True)
c.eq("...and the points land on the unit",
     _grant_seer.points, (_before_points or 0) + 30)
c.true("...and a second grant is refused LOUDLY, not silently doubled",
       "already has" in (refused(_grant_seer, "Light of Clarity") or ""))
c.true("an illegal bearer is refused by name",
       "SPIRITSEER model only" in (refused(sq("Autarch"), "Light of Clarity") or ""))

# The gate: registered is not active.
with none_fielded():
    c.true("without the detachment it is inert",
           not E.is_active(_grant_seer, "Light of Clarity"))
    c.true("...but the bearer is still found",
           bool(E.bearer_models(_grant_seer, "Light of Clarity")))
with only("SPIRIT_CONCLAVE_PLAYERS"):
    c.true("with it, it is live", E.is_active(_grant_seer, "Light of Clarity"))
with only("ASPECT_HOST_PLAYERS"):
    c.true("...and a DIFFERENT Aeldari detachment does not switch it on",
           not E.is_active(_grant_seer, "Light of Clarity"))


# =========================================================================
# 0b. The extractions this batch made
# =========================================================================
print("\n0b. The extractions")

from game import (command_phase_mark, conditional_lone_operative,  # noqa: E402
                  spiritseer, status_effects, wraith_construct)
from game.enh_admired_leader import AdmiredLeaderController  # noqa: E402
from game.enh_light_of_clarity import LightOfClarityController  # noqa: E402

# --- conditional LONE OPERATIVE: four carriers, one fold -------------------
# Three already existed and TWO of their comments each called themselves "the
# second", which is what three copies of one shape look like from the inside.
c.eq("four conditional sources are registered",
     len(conditional_lone_operative.SOURCES), 4)
_se_src = io.open("game/status_effects.py", encoding="utf-8").read()
c.true("status_effects folds them instead of listing them",
       "conditional_lone_operative.granted_ranges(squad, all_tokens)" in _se_src)
for _gone in ("illuminor.grants_lone_operative(", "spiritseer.grants_lone_operative(",
              "death_guard_defenders.grants_lone_operative("):
    c.true("...and no longer names %s itself" % _gone.split(".")[0],
           _gone not in _se_src)

# BEHAVIOUR-NEUTRAL, driven rather than asserted: a Spiritseer alone has no
# Lone Operative, and gains it beside a WRAITH CONSTRUCT unit.
_lo_seer = sq("Spiritseer")
_lo_guard = sq("Wraithguard")
tk.line_up(_lo_seer, 30.0, 30.0, spacing=1.2)
tk.line_up(_lo_guard, 60.0, 5.0, spacing=1.4)
_lo_tokens = list(_lo_seer.models) + list(_lo_guard.models)
c.true("a Spiritseer far from any wraith has no Lone Operative",
       status_effects.lone_operative_range(_lo_seer, _lo_tokens) is None)
tk.line_up(_lo_guard, 31.0, 30.0, spacing=1.4)
c.eq('...and gains it within 3" of one',
     status_effects.lone_operative_range(_lo_seer, _lo_tokens),
     spiritseer.SPIRITSEER_LONE_OPERATIVE_RANGE_IN)
# max() over the sources, inherited rather than invented - a model with two
# grants keeps the better, like rule 05.04's two saves.
c.true("the fold takes the LONGEST range, not the first",
       "max(values)" in _se_src)

# --- the WRAITH CONSTRUCT question: two answers, now one -------------------
# MEASURED: the profile-flag reading and the datasheet-keyword reading agree on
# every built datasheet, so the consolidation is behaviour-neutral today.
_by_flag, _by_keyword = set(), set()
for _n in sorted(D):
    try:
        _u = sq(_n)
    except Exception:
        continue
    if any(getattr(m.profile, "wraith_construct", False) for m in _u.models):
        _by_flag.add(_n)
    if attached_units.unit_has_datasheet_keyword(_u, "WRAITH CONSTRUCT"):
        _by_keyword.add(_n)
c.eq("the flag and the keyword name the same three datasheets",
     sorted(_by_flag), sorted(_by_keyword))
c.eq("...and there are three of them", len(_by_keyword), 3)
c.true("the Spiritseer now delegates rather than reading the flag",
       "wraith_construct.is_wraith_construct_unit(squad)"
       in io.open("game/spiritseer.py", encoding="utf-8").read())

# THE DEAD FILTER, replaced. profile.titanic is not declared on UnitProfile, so
# the old test was unconditionally False - a silent no-op.
c.true("UnitProfile still has no `titanic` field",
       not hasattr(UnitProfile, "titanic"))
c.true("...so the TITANIC exclusion reads the keyword line now",
       'getattr(other.models[0].profile, "titanic", False)'
       not in io.open("game/spiritseer.py", encoding="utf-8").read())
c.true("...which is a MEASURED no-op today - nothing built is TITANIC",
       not any(wraith_construct.is_titanic_unit(sq(n))
               for n in sorted(_by_keyword)))


# The exclusion is its OWN question, and the two answers differ only for a unit
# that carries both keywords - which nothing built does. Driven with a
# hand-built datasheet, because a clause no input can reach is untested.
class _TitanicSheet:
    keywords = ("INFANTRY", "AELDARI", "WRAITH CONSTRUCT", "TITANIC")


_titan = sq("Wraithguard")
_titan_sheet = _titan.datasheet
_titan.datasheet = _TitanicSheet
c.true("a TITANIC wraith unit is still a WRAITH CONSTRUCT unit",
       wraith_construct.is_wraith_construct_unit(_titan))
c.true("...and is excluded by the clause that prints the exclusion",
       not wraith_construct.is_non_titanic_wraith_construct(_titan))
_titan.datasheet = _titan_sheet
# The exclusion is its OWN function, because only one of the four printed
# clauses carries it.
c.true("non-titanic is a separate question from wraith-construct",
       wraith_construct.is_non_titanic_wraith_construct(_lo_guard)
       and wraith_construct.is_wraith_construct_unit(_lo_guard))

# --- the Command-phase mark: four carriers ---------------------------------
c.true("Admired Leader runs on the shared machine",
       issubclass(AdmiredLeaderController, command_phase_mark.CommandPhaseMark))
_cpm_src = io.open("game/command_phase_mark.py", encoding="utf-8").read()
c.true("the machine clears BEFORE it offers",
       before(_cpm_src, "self.clear(player)\n        asked = False",
              "for bearer_squad in self.bearer_units(player):"))
# `exclude_own_unit` is a PARAMETER, and both settings are pinned - folding it
# either way would silently widen Admired Leader or narrow the three new marks.
c.true("Admired Leader excludes the bearer's own unit",
       AdmiredLeaderController().exclude_own_unit)
c.true("...and Light of Clarity does not",
       not LightOfClarityController().exclude_own_unit)
c.true("...because the shared machine reads it as a flag",
       "self.exclude_own_unit and squad is bearer_squad" in _cpm_src)
# Tears of Isha is deliberately NOT on it - its selection is the same sentence,
# its resolution leaves no mark to expire.
# THE RANGE IS FROM THE BEARER MODEL, not from its unit - after a 19.01 merge
# those are different circles, and every one of the four cards says "of this
# model".
#
# A MEASURED NO-OP FOR THE THREE AELDARI MARKS, and the reason is worth
# stating: all three are SPIRITSEER-only, and the Spiritseer prints no LEADER
# line at all - attach() refuses it - so its unit is always exactly itself and
# the two circles cannot come apart. Admired Leader's bearer CAN be merged (a
# T'au character inside a Breacher Team), which is where that distinction is
# actually exercised. Here it is pinned at the source and as a fact about the
# roster.
c.true("a Spiritseer cannot be attached to anything",
       not sq("Spiritseer").models[0].profile.leader)
c.true("the shared machine measures from the BEARER MODELS",
       "for b in bearers for m in _living(squad)" in _cpm_src)
c.true("...which it gets from the registry, not from the unit",
       "bearers = self._bearer_models(bearer_squad)" in _cpm_src)

c.true("Tears of Isha stays off the shared machine",
       not issubclass(spiritseer.TearsOfIshaController,
                      command_phase_mark.CommandPhaseMark))
# ...and game/psychic_mark.py is a sibling, not a parent.
c.true("psychic_mark is untouched by the extraction",
       "CommandPhaseMark" not in io.open("game/psychic_mark.py", encoding="utf-8").read())

# --- the gate's lying import path ------------------------------------------
# BEHAVIOURALLY IDENTICAL - tau_detachments.has_detachment IS
# detachment_gate.has_detachment, re-exported - so this can only be checked at
# the SOURCE. It was a lying path the moment a non-T'au Enhancement registered.
_enh_src = io.open("game/enhancements.py", encoding="utf-8").read()
c.true("the registry reaches the gate directly",
       "from game import detachment_gate" in _enh_src)
c.true("...and not through the T'au module that merely re-exports it",
       "from game import tau_detachments" not in _enh_src)
from game import detachment_gate, tau_detachments  # noqa: E402

c.true("...which are the same function, so nothing moved but the name",
       tau_detachments.has_detachment is detachment_gate.has_detachment)


# =========================================================================
# 1. Objective Control
# =========================================================================
print("\n1. Objective Control")

from game import enh_craftworlds_champion as ecc  # noqa: E402
from game import enh_light_of_clarity as elc  # noqa: E402
from game import enh_strategic_savant as ess  # noqa: E402
from game import hunting_hounds, objective_control  # noqa: E402

c.eq("Craftworld's Champion sets OC 5", ecc.CRAFTWORLDS_CHAMPION_OC, 5)
c.eq("Strategic Savant adds 1", ess.STRATEGIC_SAVANT_OC_BONUS, 1)
c.eq("Light of Clarity adds 1 to INFANTRY", elc.LIGHT_OF_CLARITY_INFANTRY_OC, 1)
c.eq("...and 3 to MONSTER", elc.LIGHT_OF_CLARITY_MONSTER_OC, 3)
c.true("...which are NOT the same number",
       elc.LIGHT_OF_CLARITY_INFANTRY_OC != elc.LIGHT_OF_CLARITY_MONSTER_OC)

# --- 1a. Craftworld's Champion: a SET, and on the BEARER only --------------
_cc_avengers = sq("Dire Avengers")
_cc_bearer = _cc_avengers.models[0]
_cc_other = _cc_avengers.models[1]
_printed_oc = _cc_bearer.profile.oc
E.grant(_cc_avengers, "Craftworld's Champion", model=_cc_bearer)

with none_fielded():
    c.eq("without the detachment the bearer keeps its printed OC",
         objective_control.effective_oc(_cc_bearer), _printed_oc)
with only("GUARDIAN_BATTLEHOST_PLAYERS"):
    c.eq("with it the bearer has OC 5", objective_control.effective_oc(_cc_bearer), 5)
    # "the BEARER has", not "models in that unit" - the opposite noun from
    # Strategic Savant, one word apart on the two cards.
    c.eq("...and its squadmate does not",
         objective_control.effective_oc(_cc_other), _printed_oc)
    # A SET, not an ADD: 5, not printed+5.
    c.true("it SETS rather than adding", 5 != _printed_oc + 5)

# THE TWO SETTERS CANNOT MEET - measured, not assumed.
_hh = [n for n in sorted(D)
       if any(getattr(m.profile, "hunting_hounds", False) for m in sq(n).models)]
c.eq("no Aeldari datasheet has Hunting Hounds", _hh, [])
c.true("...so the two SET sources are disjoint on the built rosters",
       not any(getattr(m.profile, "hunting_hounds", False)
               for m in _cc_avengers.models))

# --- 1b. Strategic Savant: an ADD, on the LED unit -------------------------
_ss_banshees = sq("Howling Banshees")
_ss_autarch = sq("Autarch")
_ss_printed = _ss_banshees.models[0].profile.oc
attached_units.attach(_ss_autarch, _ss_banshees)
E.grant(_ss_banshees, "Strategic Savant")

with only("ASPECT_HOST_PLAYERS"):
    c.eq("every model in the led unit gains 1",
         objective_control.effective_oc(_ss_banshees.models[-1]), _ss_printed + 1)
    c.true("...and the module says so through leader_ability()",
           ess.applies(_ss_banshees))
with none_fielded():
    c.eq("without the detachment, nothing",
         objective_control.effective_oc(_ss_banshees.models[-1]), _ss_printed)

# THE TWO CLAUSES, EACH ISOLATED. A case that fails both proves neither; the
# bearer is the AUTARCH, so "not leading" means the Autarch stands alone.
_ss_solo = sq("Autarch")                    # bearer, leading nothing
E.grant(_ss_solo, "Strategic Savant")
_ss_led_wrong = sq("Guardian Defenders")    # led, but NOT Aspect Warriors
attached_units.attach(sq("Autarch"), _ss_led_wrong)
E.grant(_ss_led_wrong, "Strategic Savant")
with only("ASPECT_HOST_PLAYERS"):
    c.true("an Autarch leading nobody grants nothing", not ess.applies(_ss_solo))
    c.true("...and a LED unit that is not Aspect Warriors grants nothing either",
           not ess.applies(_ss_led_wrong))
    c.true("...while the one that satisfies both does", ess.applies(_ss_banshees))
    # ...and the second case really does pass the LEADER half, so it is the
    # keyword clause that refuses it and not both at once.
    c.true("the wrongly-led unit does have a leader",
           attached_units.leader_ability(_ss_led_wrong, "strategic_savant"))
    # THE "WHILE LEADING" CLAUSE IS UNREACHABLE ON THIS ROSTER, and that is
    # measured rather than assumed. Two guards overlap it: a bearer inside an
    # ASPECT WARRIORS unit is necessarily LEADING it (that is how an Autarch
    # gets in), and a DEAD bearer is already caught upstream by the registry's
    # own 19.04 filter in bearer_models(). Neutralising leader_ability() alone
    # changes no answer. It is kept because the card prints it and because it
    # carries 19.04's grace window, and it is pinned here as a no-op so the
    # next reader does not mistake it for untested.
    _ss_bearer = [m for m in _ss_banshees.models
                  if getattr(m.profile, "name", "") == "Autarch"][0]
    _ss_bearer.current_wounds = 0
    c.true("a dead bearer ends it", not ess.applies(_ss_banshees))
    _ss_bearer.current_wounds = _ss_bearer.profile.wounds
    c.true("...and it comes back when it does not", ess.applies(_ss_banshees))

# --- 1c. Light of Clarity: two numbers, one per keyword --------------------
_lc_guard = sq("Wraithguard")      # INFANTRY
_lc_lord = sq("Wraithlord")        # MONSTER
c.true("Wraithguard are INFANTRY", _lc_guard.models[0].profile.infantry)
c.true("...and the Wraithlord is a MONSTER", _lc_lord.models[0].profile.monster)
_lc_gp = _lc_guard.models[0].profile.oc
_lc_lp = _lc_lord.models[0].profile.oc

with only("SPIRIT_CONCLAVE_PLAYERS"):
    c.eq("unmarked, nothing changes",
         objective_control.effective_oc(_lc_guard.models[0]), _lc_gp)
    setattr(_lc_guard, elc.FLAG_ATTR, True)
    setattr(_lc_lord, elc.FLAG_ATTR, True)
    # TWO SEPARATE LINES: one check covering "the OC went up" is a tautology
    # that passes with one bonus wired and the other missing.
    c.eq("a marked INFANTRY model gains 1",
         objective_control.effective_oc(_lc_guard.models[0]), _lc_gp + 1)
    c.eq("a marked MONSTER model gains 3",
         objective_control.effective_oc(_lc_lord.models[0]), _lc_lp + 3)
    # A MEASURED no-op branch, driven with a hand-built model rather than left
    # unexercised: nothing built is a WRAITH CONSTRUCT that is neither.
    class _NeitherProfile:
        infantry = False
        monster = False
        oc = 1

    class _NeitherModel:
        profile = _NeitherProfile()
        squad = _lc_guard

        def is_dead(self):
            return False

    c.eq("a model that is neither gains nothing", elc.oc_bonus(_NeitherModel()), 0)

    # THE ORDER of the two keyword tests is a MEASURED no-op today - no built
    # datasheet is both INFANTRY and MONSTER, so checking either first gives
    # the same answer. Driven with a hand-built model that is both, because
    # that is the only shape where the order can be wrong, and MONSTER is
    # worth three times as much.
    class _BothProfile:
        infantry = True
        monster = True
        oc = 1

    class _BothModel:
        profile = _BothProfile()
        squad = _lc_guard

        def is_dead(self):
            return False

    c.eq("no built datasheet is both INFANTRY and MONSTER",
         [n for n in sorted(D)
          if any(getattr(m.profile, "infantry", False)
                 and getattr(m.profile, "monster", False) for m in sq(n).models)], [])
    setattr(_lc_guard, elc.FLAG_ATTR, True)
    c.eq("...and a model that IS both takes the MONSTER bonus",
         elc.oc_bonus(_BothModel()), elc.LIGHT_OF_CLARITY_MONSTER_OC)
    setattr(_lc_guard, elc.FLAG_ATTR, False)
    setattr(_lc_lord, elc.FLAG_ATTR, False)

# --- 1d. the ORDER, which is the whole of this stage -----------------------
_oc_src = io.open("game/objective_control.py", encoding="utf-8").read()
c.true("the SET runs before Soulrot's floor",
       before(_oc_src, "enh_craftworlds_champion.objective_control(model, oc)",
              "plagues.worsen_oc(model, oc)"))
c.true("...and the ADDs run after it",
       before(_oc_src, "plagues.worsen_oc(model, oc)",
              "enh_strategic_savant.oc_bonus(model)"))
# WIRING, which no behaviour test can see - this repo has been bitten seven
# times by a controller that was built and never fed.
_main_src = io.open("main.py", encoding="utf-8").read()
c.true("main.py builds the Light of Clarity controller",
       "light_of_clarity_controller = LightOfClarityController(" in _main_src)
c.true("...and drives it from the Command phase",
       "light_of_clarity_controller.begin_command_phase(turn_tracker.turn_owner)"
       in _main_src)
c.true("...right beside Admired Leader, which is the same instant",
       before(_main_src,
              "admired_leader_controller.begin_command_phase(turn_tracker.turn_owner)",
              "light_of_clarity_controller.begin_command_phase(turn_tracker.turn_owner)"))
c.true("...and Light of Clarity is in the ADD layer too",
       before(_oc_src, "plagues.worsen_oc(model, oc)",
              "enh_light_of_clarity.oc_bonus(model)"))

# SOULROT'S FLOOR does not swallow the SET: applied first, an afflicted bearer
# sits at 4, not at 1. Measured through the real fold, because the two layers
# are one line apart.
from game import plagues  # noqa: E402

with only("GUARDIAN_BATTLEHOST_PLAYERS"):
    # BOTH halves of active_plague() have to hold - Afflicted AND a chosen
    # Plague - and they are stamped by one per-frame pass, so a test that set
    # only the plague would measure nothing.
    _cc_avengers.afflicted = True
    _cc_avengers.afflicted_plague = plagues.SCABROUS_SOULROT
    c.eq("an afflicted bearer is 5 worsened by 1, not floored to 1",
         objective_control.effective_oc(_cc_bearer), 4)
    _cc_avengers.afflicted = False
    _cc_avengers.afflicted_plague = None


# =========================================================================
# 2. The attack chains
# =========================================================================
print("\n2. The attack chains")

from game import enh_aspect_of_murder as eam  # noqa: E402
from game import enh_assassins_eye as eae  # noqa: E402
from game import enh_psychic_weapons as epw  # noqa: E402
from game import weapon_range  # noqa: E402
from game.dice_notation import DiceNotation
from game.weapons import RANGED  # noqa: E402

c.eq("Assassins' Eye improves AP by 1", eae.ASSASSINS_EYE_AP_BONUS, 1)
c.eq("Psychic Destroyer adds 1 Damage", epw.PSYCHIC_DESTROYER_DAMAGE, 1)
c.eq('Stone of Eldritch Fury adds 12"', epw.STONE_OF_ELDRITCH_FURY_RANGE_IN, 12.0)
c.eq("Seersight Strike grants two [ANTI-X 2+] entries",
     epw.SEERSIGHT_STRIKE_ANTI, (("MONSTER", 2), ("VEHICLE", 2)))
c.eq("Aspect of Murder adds 1 Damage", eam.ASPECT_OF_MURDER_DAMAGE, 1)


class _W:
    """A purpose-built profile so the ONLY variable is the Enhancement - a real
    gun brings its own keywords and its own modifiers."""

    weapon_type = RANGED
    name = "probe gun"
    strength = 4
    ap = -1
    damage = 2
    damage_notation = None
    range_in = 24.0
    psychic = False
    anti = None
    precision = False


class _WPsychic(_W):
    psychic = True


class _WPsychicMelee(_WPsychic):
    weapon_type = "melee"


class _WPsychicAnti(_WPsychic):
    anti = ("INFANTRY", 4)


class _WNotation(_WPsychic):
    #: A REAL DiceNotation, not the string "D6" this stood at first. The string
    #: made the fake unable to answer the one question the rule asks of a rolled
    #: Damage - what its BONUS is - so the pin below could only ever have
    #: recorded "nothing happened".
    damage_notation = DiceNotation(6, 0)


class _WMeleeNotation(_W):
    weapon_type = "melee"
    damage_notation = DiceNotation(3, 0)


class _WMelee(_W):
    weapon_type = "melee"


class _WMeleePrecise(_WMelee):
    precision = True


# --- 2a. Assassins' Eye: conditional on the TARGET ------------------------
_ae_rangers = sq("Rangers")
E.grant(_ae_rangers, "Assassins' Eye")
_ae_character = sq("Farseer", "Player 2")
_ae_plain = sq("Guardian Defenders", "Player 2")
c.true("a Farseer unit is a CHARACTER unit", eae.target_is_character(_ae_character))
c.true("...and Guardian Defenders are not", not eae.target_is_character(_ae_plain))
# 19.03's POOLING is the point, and it only shows on a MERGED unit whose FIRST
# model is a bodyguard: reading models[0] would answer False for exactly the
# case this clause exists for - a character sheltering inside a squad.
_ae_merged = sq("Guardian Defenders", "Player 2")
attached_units.attach(sq("Farseer", "Player 2"), _ae_merged)
c.true("a squad sheltering a character IS a CHARACTER unit",
       eae.target_is_character(_ae_merged))
c.true("...even though its first model is not one",
       not getattr(_ae_merged.models[0].profile, "character", False))

_ae_gun = _W()
with only("PATH_OF_THE_OUTCAST_PLAYERS"):
    c.eq("against a CHARACTER the AP improves",
         eae.adjusted_weapon(_ae_gun, _ae_rangers, _ae_character).ap, _W.ap - 1)
    c.true("...on a COPY",
           eae.adjusted_weapon(_ae_gun, _ae_rangers, _ae_character) is not _ae_gun)
    c.eq("...and against anything else it does not",
         eae.adjusted_weapon(_ae_gun, _ae_rangers, _ae_plain).ap, _W.ap)
    # MELEE is excluded as printed.
    c.eq("a melee weapon is untouched",
         eae.adjusted_weapon(_WMelee(), _ae_rangers, _ae_character).ap, _W.ap)
with none_fielded():
    c.eq("no detachment, no bonus",
         eae.adjusted_weapon(_ae_gun, _ae_rangers, _ae_character).ap, _W.ap)

# UNIT-LEVEL: every model carries it, so "a living model still has it" means
# "the unit still exists".
c.true("every Ranger carries it",
       all(m.profile.assassins_eye for m in _ae_rangers.models))
c.true("...and Shroud Runners are a legal bearer unit too",
       E.grant(sq("Shroud Runners"), "Assassins' Eye") is not None)

# --- 2b. the three psychic-weapon Enhancements ----------------------------
_pw_seer = sq("Farseer")
_pw_model = _pw_seer.models[0]
E.grant(_pw_seer, "Psychic Destroyer")

with only("WARHOST_PLAYERS"):
    c.eq("a ranged PSYCHIC weapon gains 1 Damage",
         epw.adjusted_weapon(_WPsychic(), _pw_model).damage, _W.damage + 1)
    # THE KEYWORD, not a weapon name: a non-psychic gun gains nothing.
    c.eq("a non-psychic gun gains nothing",
         epw.adjusted_weapon(_W(), _pw_model).damage, _W.damage)
    # "RANGED psychic weapons" - one printed word, and Seersight Strike next
    # door does NOT have it.
    c.eq("a MELEE psychic weapon gains nothing either",
         epw.adjusted_weapon(_WPsychicMelee(), _pw_model).damage, _W.damage)
    # A ROLLED DAMAGE GETS THE BONUS TOO, on its NOTATION. "Add 1 to the Damage
    # characteristic" of a D6 weapon makes it D6+1, and rule 24.25's [MELTA]
    # already does exactly this (game/shooting.py's melta_adjusted_weapon).
    # BOTH halves are pinned: the notation because it is what the roll reads,
    # and `damage` because it is the preview shown beside it.
    _pw_rolled = epw.adjusted_weapon(_WNotation(), _pw_model)
    c.eq("a rolled Damage gains the bonus on its NOTATION",
         _pw_rolled.damage_notation.bonus, _WNotation.damage_notation.bonus + 1)
    c.eq("...the die itself is untouched", _pw_rolled.damage_notation.sides, 6)
    c.eq("...and its preview value moves with it",
         _pw_rolled.damage, _W.damage + 1)
with none_fielded():
    c.eq("no detachment, no bonus",
         epw.adjusted_weapon(_WPsychic(), _pw_model).damage, _W.damage)

_ss_sky = sq("Warlock Skyrunners")
_ss_model = _ss_sky.models[0]
E.grant(_ss_sky, "Seersight Strike")
with only("WINDRIDER_HOST_PLAYERS"):
    c.eq("a psychic weapon gains both [ANTI-X 2+] entries",
         epw.adjusted_weapon(_WPsychic(), _ss_model).anti,
         (("MONSTER", 2), ("VEHICLE", 2)))
    # NO "ranged" in this one's printed text - the one word that separates it
    # from its two neighbours.
    c.eq("...including a MELEE psychic weapon, which this card does not exclude",
         epw.adjusted_weapon(_WPsychicMelee(), _ss_model).anti,
         (("MONSTER", 2), ("VEHICLE", 2)))
    # NEVER a replacement: the printed entries are kept, because the crit fold
    # takes the BEST threshold and losing one could cost a better answer
    # against a keyword this card does not name.
    c.eq("a printed [ANTI-X] entry survives beside the granted pair",
         epw.adjusted_weapon(_WPsychicAnti(), _ss_model).anti,
         (("INFANTRY", 4), ("MONSTER", 2), ("VEHICLE", 2)))

_sf_seer = sq("Eldrad Ulthran")
_sf_model = _sf_seer.models[0]
E.grant(_sf_seer, "Stone of Eldritch Fury")
with only("SEER_COUNCIL_PLAYERS"):
    c.eq('a ranged psychic weapon reaches 12" further',
         weapon_range.effective_range_in(_sf_model, _WPsychic()), _W.range_in + 12.0)
    # ...and its HALF range moves with it, for free.
    c.eq("...and half range moves with it",
         weapon_range.half_range_in(_sf_model, _WPsychic()), (_W.range_in + 12.0) / 2)
    c.eq("a non-psychic gun keeps its printed range",
         weapon_range.effective_range_in(_sf_model, _W()), _W.range_in)
with none_fielded():
    c.eq("no detachment, no range",
         weapon_range.effective_range_in(_sf_model, _WPsychic()), _W.range_in)

# --- 2c. Aspect of Murder: the first Enhancement in the MELEE chain -------
_am_autarch = sq("Autarch")
_am_model = _am_autarch.models[0]
E.grant(_am_autarch, "Aspect of Murder")
with only("ASPECT_HOST_PLAYERS"):
    # The input is held, because `x is not _WMelee()` compares against a NEW
    # instance and is true whatever the code does - a tautology the probe
    # caught.
    _am_in = _WMelee()
    _am_out = eam.adjusted_weapon(_am_in, _am_model)
    c.eq("a melee weapon gains 1 Damage", _am_out.damage, _W.damage + 1)
    c.true("...and [PRECISION]", _am_out.precision)
    c.true("...on a COPY, leaving the input alone", _am_out is not _am_in)
    c.true("...which is measured on the INPUT, not on a fresh instance",
           not _am_in.precision and _am_in.damage == _W.damage)
    c.eq("a RANGED weapon gains nothing - the text says melee",
         eam.adjusted_weapon(_W(), _am_model).damage, _W.damage)
    # NEVER a downgrade: a weapon already printing [PRECISION] keeps it and
    # only the Damage moves.
    _am_pre = eam.adjusted_weapon(_WMeleePrecise(), _am_model)
    c.true("a weapon already printing [PRECISION] keeps it", _am_pre.precision)
    c.eq("...and still gains the Damage", _am_pre.damage, _W.damage + 1)
    # A ROLLED Damage gets the bonus on its NOTATION, exactly as Psychic
    # Destroyer does - the same printed phrase, so the same treatment, and the
    # same trap of moving only the preview value the roll overwrites.
    _am_roll = eam.adjusted_weapon(_WMeleeNotation(), _am_model)
    c.eq("a rolled Damage gains the bonus on its NOTATION",
         _am_roll.damage_notation.bonus,
         _WMeleeNotation.damage_notation.bonus + 1)
    c.eq("...the die itself is untouched", _am_roll.damage_notation.sides, 3)
    c.true("...and it still grants [PRECISION]", _am_roll.precision)
with none_fielded():
    c.true("no detachment, nothing",
           not eam.adjusted_weapon(_WMelee(), _am_model).precision)

# --- 2d. the two attack keys ----------------------------------------------
# The one-representative shortcut: without a key term a bearer hands its whole
# group its answer. Measured as a key DIFFERENCE, not as a source string.
_key_shoot = io.open("game/shooting.py", encoding="utf-8").read()
_main_src2 = io.open("main.py", encoding="utf-8").read()
_key_fight = io.open("game/fight.py", encoding="utf-8").read()
c.true("the ranged key carries the psychic-weapon term",
       "enh_psychic_weapons.attack_key(model))" in _key_shoot)
c.true("the melee key carries Aspect of Murder's",
       "enh_aspect_of_murder.attack_key(model))" in _key_fight)
with only("WARHOST_PLAYERS"):
    c.true("the bearer keys differently from a squadmate",
           epw.attack_key(_pw_model) != epw.attack_key(sq("Farseer").models[0]))
c.eq("...and every other model keys the same",
     epw.attack_key(sq("Dire Avengers").models[0]), (False, False))
with only("ASPECT_HOST_PLAYERS"):
    c.true("the melee bearer keys differently too",
           eam.attack_key(_am_model) != eam.attack_key(sq("Autarch").models[0]))

# --- 2e. end to end, through the REAL chains -------------------------------
print("   end to end")

with only("PATH_OF_THE_OUTCAST_PLAYERS"):
    _e2e = tk.shooting_scene(D["Rangers"], D["Farseer"], attacker_owner=HUMAN)
    tk.line_up(_e2e["attacker"], 30.0, 30.0, spacing=1.2)
    tk.line_up(_e2e["target"], 30.0, 34.0, spacing=1.2)
    _e2e_shoot = _e2e["shooting"]
    _e2e_shoot.active_squad = _e2e["attacker"]
    _e2e_gun = next(w for w in _e2e["attacker"].models[0].weapons
                    if w.weapon_type == RANGED)
    _e2e_pairs = [(m, _e2e_gun) for m in _e2e["attacker"].models]
    _base_ap = _e2e_shoot._adjusted_weapon(_e2e_pairs, _e2e["target"]).ap
    E.grant(_e2e["attacker"], "Assassins' Eye")
    c.eq("the real ranged chain improves the AP against a CHARACTER",
         _e2e_shoot._adjusted_weapon(_e2e_pairs, _e2e["target"]).ap, _base_ap - 1)

with only("ASPECT_HOST_PLAYERS"):
    _fe = tk.fight_scene(D["Autarch"], D["Guardian Defenders"], attacker_owner=HUMAN)
    tk.line_up(_fe["attacker"], 30.0, 30.0, spacing=1.2)
    tk.line_up(_fe["target"], 31.0, 30.0, spacing=1.2)
    _fe_fight = _fe["fight"]
    _fe_fight.fighting_squad = _fe["attacker"]
    _fe_blade = next(w for w in _fe["attacker"].models[0].weapons
                     if w.weapon_type != RANGED and w.damage_notation is None)
    _fe_pairs = [(m, _fe_blade) for m in _fe["attacker"].models]
    _fe_base = _fe_fight._adjusted_weapon(_fe_pairs, _fe["target"]).damage
    E.grant(_fe["attacker"], "Aspect of Murder")
    _fe_out = _fe_fight._adjusted_weapon(_fe_pairs, _fe["target"])
    c.eq("the real MELEE chain adds 1 Damage", _fe_out.damage, _fe_base + 1)
    c.true("...and grants [PRECISION]", _fe_out.precision)

# ...and the psychic-weapon adjuster through the same real chain. Driven on a
# unit whose gun IS psychic, because the module's whole gate is that keyword.
#
# TWO BEARERS, because a ranged psychic weapon prints its Damage in TWO forms
# and the rule reaches both. MEASURED over every Aeldari datasheet: the four
# most likely bearers of a 30-point ASURYANI PSYKER Enhancement (Farseer,
# Eldrad, Farseer Skyrunner, the Yncarne) ALL print a ROLLED Damage, and the
# flat ones are the Warlock guns. A pin on one form alone would have left the
# other free - and the notation half is the one an earlier version of this
# module got wrong, skipping it outright and making the Enhancement inert on
# exactly those four.
def _psychic_gun(squad, rolled):
    """The unit's first ranged [PSYCHIC] weapon with a rolled / flat Damage."""
    return next((w for w in squad.models[0].weapons
                 if w.weapon_type == RANGED and getattr(w, "psychic", False)
                 and ((w.damage_notation is not None) == rolled)), None)


for _pe_sheet, _pe_rolled, _pe_what in (("Farseer", True, "a ROLLED Damage (D3)"),
                                        ("Warlock", False, "a flat Damage")):
    with only("WARHOST_PLAYERS"):
        _pe = tk.shooting_scene(D[_pe_sheet], D["Guardian Defenders"], attacker_owner=HUMAN)
        tk.line_up(_pe["attacker"], 30.0, 30.0, spacing=1.2)
        tk.line_up(_pe["target"], 30.0, 33.0, spacing=1.2)
        _pe_shoot = _pe["shooting"]
        _pe_shoot.active_squad = _pe["attacker"]
        _pe_gun = _psychic_gun(_pe["attacker"], _pe_rolled)
        c.true("the %s really carries a ranged psychic weapon with %s"
               % (_pe_sheet, _pe_what), _pe_gun is not None)
        if _pe_gun is not None:
            _pe_pairs = [(m, _pe_gun) for m in _pe["attacker"].models]
            _pe_in = _pe_shoot._adjusted_weapon(_pe_pairs, _pe["target"])
            _pe_base, _pe_base_bonus = _pe_in.damage, (
                _pe_in.damage_notation.bonus if _pe_in.damage_notation else None)
            E.grant(_pe["attacker"], "Psychic Destroyer")
            _pe_out = _pe_shoot._adjusted_weapon(_pe_pairs, _pe["target"])
            c.eq("the real ranged chain adds 1 Damage to the %s gun" % _pe_sheet,
                 _pe_out.damage, _pe_base + 1)
            if _pe_rolled:
                # THE HALF THAT DECIDES THE ROLL. `damage` beside it is only the
                # preview; DiceNotation.bonus is what the Damage roll actually
                # reads, so a version that moved only the preview would look
                # right here and pay nothing on the table.
                c.eq("...on its NOTATION, which is what the roll reads",
                     _pe_out.damage_notation.bonus, _pe_base_bonus + 1)
                c.eq("...and the die itself is untouched (D3 stays a D3)",
                     _pe_out.damage_notation.sides, _pe_in.damage_notation.sides)
            else:
                c.true("...and a flat Damage grows no notation",
                       _pe_out.damage_notation is None)
            # NEVER A MUTATION: the WeaponProfile class is shared by every model
            # in the game carrying that gun.
            c.eq("...and the shared instance is untouched", _pe_in.damage, _pe_base)

# NEGATIVE SPACE: each module reaches exactly one chain.
c.true("Aspect of Murder never reaches the Shooting phase",
       "enh_aspect_of_murder" not in _key_shoot)
c.true("Assassins' Eye never reaches the Fight phase",
       "enh_assassins_eye" not in _key_fight)
c.true("...nor do the psychic-weapon three",
       "enh_psychic_weapons" not in _key_fight)


# --- 2f. Stave of Kurnous, and the melee critical-wound split -------------
print("   the critical-wound split")

from game import critical_wound_split, crit_ap  # noqa: E402
from game import enh_stave_of_kurnous as esk  # noqa: E402
from game.enh_stave_of_kurnous import StaveOfKurnousController  # noqa: E402

# THE RENAME: third carrier, and the first whose consequence is not an AP.
c.true("crit_ap re-exports the renamed module",
       crit_ap.applies is critical_wound_split.applies
       and crit_ap.adjusted_weapon is critical_wound_split.adjusted_weapon)

# THE RANGED TEST MOVED from the door into the two sources that print it.
_cws_src = io.open("game/critical_wound_split.py", encoding="utf-8").read()
c.true("the module no longer refuses a melee weapon outright",
       "if weapon is None or weapon.weapon_type != RANGED:" not in _cws_src)
c.true("...and the two ranged sources still test it",
       "ranged = weapon.weapon_type == RANGED" in _cws_src)

_sk_guard = sq("Wraithguard")
_sk_blades = sq("Wraithblades")
c.true("a marked unit is a split source in EITHER phase",
       not esk.applies(_sk_blades))
setattr(_sk_blades, esk.FLAG_ATTR, True)
c.true("...once marked", esk.applies(_sk_blades))

# The effect is [PRECISION] on the split share, never a downgrade.
_sk_in = _WMelee()
_sk_out = esk.adjusted_weapon(_sk_in)
c.true("the split weapon gains [PRECISION]", _sk_out.precision)
c.true("...on a COPY, leaving the input alone",
       _sk_out is not _sk_in and not _sk_in.precision)
_sk_pre = _WMeleePrecise()
c.true("...and a weapon already printing it comes back untouched",
       esk.adjusted_weapon(_sk_pre) is _sk_pre)

# THE TITANIC EXCLUSION IS THIS CARD'S ALONE.
c.true("a plain WRAITH CONSTRUCT unit is a legal target",
       esk.eligible_target(_sk_guard))
_sk_sheet = _sk_guard.datasheet


class _TitanicWraith:
    keywords = ("INFANTRY", "AELDARI", "WRAITH CONSTRUCT", "TITANIC")


_sk_guard.datasheet = _TitanicWraith
c.true("...and a TITANIC one is not", not esk.eligible_target(_sk_guard))
# ...while its two neighbours, which do NOT print the exclusion, still take it.
c.true("Light of Clarity does not exclude TITANIC",
       wraith_construct.is_wraith_construct_unit(_sk_guard))
_sk_guard.datasheet = _sk_sheet

# THE MELEE SPLIT, driven through the REAL FightController. This is the whole
# reason the Enhancement is expensive: without it the ranged-only reading would
# leave it nearly inert on its own targets, which are melee units.
_fight_src = io.open("game/fight.py", encoding="utf-8").read()
c.true("the Fight phase has a critical-wound split at all",
       "_pending_crit_split" in _fight_src)
c.true("...which asks the shared module",
       "critical_wound_split.applies(weapon, _fighter, self.fighting_squad)" in _fight_src)
c.true("...pulls the crits OUT of the normal save",
       "wounds - self._devastating_crits - self._pending_crit_split" in _fight_src)
c.true("...and resolves them after [DEVASTATING WOUNDS] has taken its share",
       before(_fight_src, "self._begin_devastating_wounds(weapon, target_squad)",
              "self._begin_crit_split_save()"))
# The precision question used to be asked inline in this branch. It now goes
# through _continue_after_save(), the one continuation the acknowledged and the
# skipped-Save paths share (see test_impossible_save_skip.py) - so the
# assurance is in two halves: this branch hands over the SPLIT weapon, and the
# continuation asks the precision question of whatever weapon it was handed.
# Pinned as the two call expressions rather than as one literal statement,
# which is what made the old line brittle to a refactor that changed nothing.
c.true("...handing the SPLIT weapon to the shared post-save continuation",
       "self._continue_after_save(rolls, split_weapon, target_squad, weapon_label, group)"
       in _fight_src)
_cont = _fight_src.split("def _continue_after_save(")[1][:900]
c.true("...and that continuation asks the precision question against the weapon it was given",
       "self._precision_choice_needed(weapon, target_squad)" in _cont)

with only("SPIRIT_CONCLAVE_PLAYERS"):
    _sk_scene = tk.fight_scene(D["Wraithblades"], D["Guardian Defenders"],
                               attacker_owner=HUMAN)
    tk.line_up(_sk_scene["attacker"], 30.0, 30.0, spacing=1.4)
    tk.line_up(_sk_scene["target"], 31.0, 30.0, spacing=1.2)
    _sk_fight = _sk_scene["fight"]
    _sk_fight.fighting_squad = _sk_scene["attacker"]
    _sk_weapon = next(w for w in _sk_scene["attacker"].models[0].weapons
                      if w.weapon_type != RANGED)
    _sk_fighter = _sk_scene["attacker"].models[0]
    c.true("unmarked, the real fight step splits nothing",
           not critical_wound_split.applies(_sk_weapon, _sk_fighter,
                                            _sk_scene["attacker"]))
    setattr(_sk_scene["attacker"], esk.FLAG_ATTR, True)
    c.true("...and marked, it does",
           critical_wound_split.applies(_sk_weapon, _sk_fighter,
                                        _sk_scene["attacker"]))
    c.true("...naming this Enhancement as the source",
           critical_wound_split.label(_sk_weapon, _sk_fighter,
                                      _sk_scene["attacker"]) == esk.STAVE_OF_KURNOUS)
    c.true("...and the split weapon is precise where the group's is not",
           critical_wound_split.adjusted_weapon(
               _sk_weapon, _sk_fighter, _sk_scene["attacker"]).precision
           and not _sk_weapon.precision)

    # DRIVEN THROUGH THE REAL _resolve_wounds: the source guards above say the
    # code exists, not that it runs. Six wounds of which two critical - the
    # normal save must lose exactly the critical share, and the sub-step must
    # be the one left pending.
    # A COMPLETE group, including the two keys only the group-finishing tail
    # reads. Without them a probe that neutralises the split dispatch makes
    # this fall through to _finish_group() and die on a KeyError - which hides
    # the assertion behind a crash instead of a clean red.
    def _sk_arm():
        """Re-arm the group before EVERY drive below. Each drive can finish the
        group and clear current_group, and a drive that starts with it already
        None dies on a TypeError - which would hide the next assertion behind a
        crash instead of turning it red."""
        _sk_fight.current_group = {
            "pairs": [(m, _sk_weapon) for m in _sk_scene["attacker"].models],
            "target_squad": _sk_scene["target"], "weapon": _sk_weapon,
            "weapon_key": _gf._melee_attack_key(_sk_scene["attacker"].models[0], _sk_weapon),
            "weapon_label": _sk_weapon.name,
        }
        _sk_fight.pending_step = None

    _sk_arm()
    _sk_fight.target_squad = _sk_scene["target"]
    _sk_dice = _sk_fight.dice_manager
    _sk_before = len(getattr(_sk_dice, "rolls", []) or [])
    setattr(_sk_scene["attacker"], esk.FLAG_ATTR, False)
    _sk_fight._resolve_wounds(_sk_weapon, _sk_scene["target"],
                              _sk_scene["target"].models[0].profile,
                              "probe", 6, 2)
    c.eq("unmarked, all six wounds go to one Save roll",
         _sk_fight._pending_crit_split, 0)
    c.eq("...and the pending step is the ordinary save",
         _sk_fight.pending_step, "save")

    setattr(_sk_scene["attacker"], esk.FLAG_ATTR, True)
    _sk_arm()
    _sk_fight._resolve_wounds(_sk_weapon, _sk_scene["target"],
                              _sk_scene["target"].models[0].profile,
                              "probe", 6, 2)
    c.eq("marked, the two critical wounds are pulled out",
         _sk_fight._pending_crit_split, 2)

    # ...AND THE SUB-STEP IS REALLY DISPATCHED. Pulling the crits out is half
    # the work; a version that computes the split and never runs it looks
    # identical to the assertion above. Two wounds, BOTH critical, so there is
    # no ordinary Save to resolve first and the dispatch is immediate.
    _sk_arm()
    _sk_fight._resolve_wounds(_sk_weapon, _sk_scene["target"],
                              _sk_scene["target"].models[0].profile,
                              "probe", 2, 2)
    c.eq("an all-critical roll goes straight to the split save",
         _sk_fight.pending_step, "save_crit_split")

    # THE MIXED CASE, which is the one that goes missing: ordinary wounds and
    # critical ones from the SAME roll. The ordinary share resolves first, and
    # the critical share is still owed its own Save afterwards - so the split
    # counter must survive that first save rather than being finished away.
    _sk_arm()
    _sk_fight._resolve_wounds(_sk_weapon, _sk_scene["target"],
                              _sk_scene["target"].models[0].profile,
                              "probe", 6, 2)
    c.eq("a mixed roll resolves the ordinary wounds first",
         _sk_fight.pending_step, "save")
    c.eq("...and still owes the critical share its own save",
         _sk_fight._pending_crit_split, 2)
    # The CALL, not a two-line literal. The first version of this guard pinned
    # `elif ...:\n            self._begin_crit_split_save()` and went red the
    # moment a comment was written between the two - the same lesson this repo
    # already records about pinning punctuation instead of the call expression.
    # THREE dispatch sites, and each is a different way a wound roll can end:
    # every wound critical (_resolve_wounds_now), an ordinary save resolved
    # first (_check_allocation_done), and [DEVASTATING WOUNDS] taking its share
    # first (_check_devastating_wounds_done). Losing any one of them makes the
    # split silently vanish down that path alone.
    c.eq("...which game/fight.py picks up after that save, as the ranged twin does",
         _fight_src.count("self._begin_crit_split_save()"), 3)
    setattr(_sk_scene["attacker"], esk.FLAG_ATTR, False)

# WIRING - the seventh "built but never fed" is why this is checked.
c.true("main.py builds the Stave of Kurnous controller",
       "stave_of_kurnous_controller = StaveOfKurnousController(" in _main_src2)
c.true("...and drives it from the Command phase",
       "stave_of_kurnous_controller.begin_command_phase(turn_tracker.turn_owner)"
       in _main_src2)


# =========================================================================
# 3. Rolls and re-rolls
#    Mirage Field, Shimmerstone, Guiding Presence, Breath of Vaul,
#    Mantle of Wisdom.
# =========================================================================
print("\n3. Rolls and re-rolls")

import game.fight as _f_mod  # noqa: E402
from game import enh_breath_of_vaul as ebv  # noqa: E402
from game import enh_guiding_presence as egp  # noqa: E402
from game import enh_mantle_of_wisdom as emw  # noqa: E402
from game import enh_mirage_field as emf  # noqa: E402
from game import enh_shimmerstone as esh  # noqa: E402
from game import path_of_the_warrior as potw  # noqa: E402
from game.factions import aeldari as aeldari_mod  # noqa: E402
from game.modifiers import apply_modifiers  # noqa: E402
from game.weapons import RANGED  # noqa: E402

_shoot_src = io.open("game/shooting.py", encoding="utf-8").read()


class _E3State:
    """The two fields the controllers here read off game_state."""

    def __init__(self, *squads):
        self.tokens = [m for s in squads for m in s.models]


def _ranged_gun(squad):
    return next(w for w in squad.models[0].weapons if w.weapon_type == RANGED)


def _group(scene, gun=None):
    """What _hit_modifiers()/_begin_resolution() actually take."""
    gun = gun if gun is not None else _ranged_gun(scene["attacker"])
    return {"pairs": [(m, gun) for m in scene["attacker"].models],
            "target_squad": scene["target"]}


def _led(leader_name, unit_name, owner=HUMAN):
    """A real 19.01 attached unit, built through the real attach()."""
    leader = sq(leader_name, owner)
    unit = sq(unit_name, owner)
    reasons = attached_units.can_attach(leader, unit)
    assert not reasons, (leader_name, unit_name, reasons)
    attached_units.attach(leader, unit)
    return unit


def _leader_model(unit, leader_name):
    """The merged-in leader model, for naming a bearer explicitly. Several of
    these cards are "ASURYANI model only", so every bodyguard qualifies too and
    grant() refuses to guess which one carries the upgrade."""
    return next(m for m in unit.models if m.profile.name == leader_name)


# --- 3a. Mirage Field: DEFENDER-side, and in BOTH chains ------------------
_mf_unit = sq("Windriders")
# Every Windrider is ASURYANI MOUNTED, so grant() refuses to guess which one
# carries a 25-point upgrade - the bearer is named, as army building would.
E.grant(_mf_unit, "Mirage Field", model=_mf_unit.models[0])

with only("WINDRIDER_HOST_PLAYERS"):
    c.true("attacks targeting the bearer's unit take the malus", emf.applies(_mf_unit))
with none_fielded():
    c.true("no detachment, no malus", not emf.applies(_mf_unit))

# "the bearer's UNIT" - one model carries it, every model is shielded. Under
# 19.01 that is what a joined character's Enhancement means, and it is the
# reason this is asked of the SQUAD.
c.eq("exactly one model carries it", len(E.bearer_models(_mf_unit, "Mirage Field")), 1)
c.true("...but the whole unit is protected",
       len(_mf_unit.models) > 1)

# THE SIGN. Positive = worse. Written the other way round this would be an
# army-wide bonus to everything shooting at the bearer.
c.true("it WORSENS the roll", emf.MIRAGE_FIELD_PENALTY > 0)

# ...end to end, through the REAL shooting hit step.
_mf_scene = tk.shooting_scene(D["Dire Avengers"], D["Windriders"], attacker_owner="Player 2")
tk.line_up(_mf_scene["attacker"], 20.0, 20.0, spacing=1.2)
tk.line_up(_mf_scene["target"], 20.0, 26.0, spacing=1.2)
_mf_shoot = _mf_scene["shooting"]
_mf_shoot.active_squad = _mf_scene["attacker"]
_mf_grp = _group(_mf_scene)
with none_fielded():
    _mf_without = [m.source for m in _mf_shoot._hit_modifiers(_mf_grp)]
E.grant(_mf_scene["target"], "Mirage Field", model=_mf_scene["target"].models[0])
with only("WINDRIDER_HOST_PLAYERS", players=("Player 1",)):
    _mf_with = _mf_shoot._hit_modifiers(_mf_grp)
c.true("the real RANGED hit step is clean without it",
       emf.MIRAGE_FIELD_LABEL not in _mf_without)
c.true("...and carries it with", emf.MIRAGE_FIELD_LABEL in [m.source for m in _mf_with])
c.eq("...as a +1 on the threshold, i.e. a HARDER roll",
     apply_modifiers(3, [m for m in _mf_with if m.source == emf.MIRAGE_FIELD_LABEL]), 4)

# ...and through the REAL melee hit step. "An attack", not "a ranged attack" -
# the one word that separates it from Shimmerstone, so this is measured and
# not assumed.
_mff = tk.fight_scene(D["Dire Avengers"], D["Windriders"], attacker_owner="Player 2")
tk.line_up(_mff["attacker"], 20.0, 20.0, spacing=1.2)
tk.line_up(_mff["target"], 20.0, 21.0, spacing=1.2)
_mff_fight = _mff["fight"]
_mff_fight.fighting_squad = _mff["attacker"]
_mff_model = _mff["attacker"].models[0]
with none_fielded():
    _mff_without = [m.source for m in _mff_fight._hit_modifiers(_mff_model, _mff["target"])]
E.grant(_mff["target"], "Mirage Field", model=_mff["target"].models[0])
with only("WINDRIDER_HOST_PLAYERS", players=("Player 1",)):
    _mff_with = [m.source for m in _mff_fight._hit_modifiers(_mff_model, _mff["target"])]
c.true("the real MELEE hit step is clean without it",
       emf.MIRAGE_FIELD_LABEL not in _mff_without)
c.true("...and carries it with - 'an attack' means both phases",
       emf.MIRAGE_FIELD_LABEL in _mff_with)


# --- 3b. Shimmerstone: three conditions, RANGED only ----------------------
_sh_unit = _led("Autarch", "Howling Banshees")
E.grant(_sh_unit, "Shimmerstone")

with only("ASPECT_HOST_PLAYERS"):
    c.true("a led ASPECT WARRIORS unit is protected", esh.applies(_sh_unit))

    # CONDITION 2, ISOLATED. A lone Autarch would be refused by the KEYWORD
    # too (measured: an Autarch carries neither ASPECT WARRIORS nor STORM
    # GUARDIANS), so it proves nothing about "leading" - the masking that made
    # the first version of this probe pass with the condition deleted. Instead:
    # an ASPECT WARRIORS unit carrying the flag with nobody leading it, where
    # only condition 2 can refuse.
    _sh_unled = sq("Dire Avengers")
    setattr(_sh_unled.models[0].profile, "shimmerstone", True)
    c.true("the isolating unit really is ASPECT WARRIORS",
           attached_units.unit_has_datasheet_keyword(_sh_unled, "ASPECT WARRIORS"))
    c.true("...and really carries it", E.is_active(_sh_unled, "Shimmerstone"))
    c.true("...but nothing is leading it, so it is not protected",
           not esh.applies(_sh_unled))

    # CONDITION 3, isolated: leading, but not ASPECT WARRIORS. Guardian
    # Defenders measured above as carrying neither keyword.
    _sh_wrong = _led("Farseer", "Guardian Defenders")
    setattr(_sh_wrong.models[0].profile, "shimmerstone", True)
    c.true("...and a led unit that is not ASPECT WARRIORS is not either",
           not esh.applies(_sh_wrong))
with none_fielded():
    c.true("no detachment, nothing", not esh.applies(_sh_unit))

c.true("it WORSENS the roll", esh.SHIMMERSTONE_PENALTY > 0)

# ...end to end through the REAL wound step.
_sh_scene = tk.shooting_scene(D["Dire Avengers"], D["Howling Banshees"], attacker_owner="Player 2")
tk.line_up(_sh_scene["attacker"], 20.0, 20.0, spacing=1.2)
tk.line_up(_sh_scene["target"], 20.0, 26.0, spacing=1.2)
_sh_shoot = _sh_scene["shooting"]
_sh_shoot.active_squad = _sh_scene["attacker"]
_sh_target = _sh_scene["target"]
attached_units.attach(sq("Autarch", "Player 1"), _sh_target)
E.grant(_sh_target, "Shimmerstone")
with none_fielded():
    _sh_without = [m.source for m in _sh_shoot._wound_modifiers(_sh_target)]
with only("ASPECT_HOST_PLAYERS", players=("Player 1",)):
    _sh_with = _sh_shoot._wound_modifiers(_sh_target)
c.true("the real wound step is clean without it",
       esh.SHIMMERSTONE_LABEL not in _sh_without)
c.true("...and carries it with", esh.SHIMMERSTONE_LABEL in [m.source for m in _sh_with])
c.eq("...as a +1 on the WOUND threshold",
     apply_modifiers(4, [m for m in _sh_with if m.source == esh.SHIMMERSTONE_LABEL]), 5)

# RANGED-ONLY, asserted at the SOURCE. A melee scene that happens to come out
# unchanged would not distinguish "not wired" from "wired and inapplicable".
c.true("Shimmerstone never reaches the Fight phase",
       "enh_shimmerstone" not in _fight_src)
c.true("...while Mirage Field does", "enh_mirage_field" in _fight_src)


# --- 3c. Guiding Presence: a mark on a FRIENDLY unit ----------------------
_gp_seer = sq("Farseer")
E.grant(_gp_seer, "Guiding Presence")
_gp_falcon = sq("Falcon")
_gp_enemy_falcon = sq("Falcon", "Player 2")
_gp_banshees = sq("Howling Banshees")

with only("ARMOURED_WARHOST_PLAYERS"):
    c.true("a friendly AELDARI VEHICLE unit is eligible",
           egp.is_eligible_target(_gp_falcon, HUMAN))
    # "FRIENDLY" - an enemy vehicle would be a 25-point gift.
    c.true("...an ENEMY vehicle is not",
           not egp.is_eligible_target(_gp_enemy_falcon, HUMAN))
    # "VEHICLE" - not just any Aeldari unit.
    c.true("...and a non-VEHICLE friendly unit is not",
           not egp.is_eligible_target(_gp_banshees, HUMAN))

c.true("+1 to hit is a BONUS, so a NEGATIVE threshold adjustment",
       egp.GUIDING_PRESENCE_BONUS < 0)

# The 6" boundary and the visibility clause, measured through the controller.
_gp_state = _E3State(_gp_seer, _gp_falcon, _gp_banshees, _gp_enemy_falcon)
_gp_ctrl = egp.GuidingPresenceController(game_state=_gp_state, auto_players=(HUMAN,))
with only("ARMOURED_WARHOST_PLAYERS"):
    tk.line_up(_gp_seer, 20.0, 20.0, spacing=1.2)
    tk.line_up(_gp_falcon, 20.0, 24.0, spacing=1.2)      # inside 6"
    c.true("a vehicle within 6\" is a candidate",
           _gp_falcon in _gp_ctrl.candidates(HUMAN))
    tk.line_up(_gp_falcon, 20.0, 40.0, spacing=1.2)      # far outside
    c.true("...and one far away is not",
           _gp_falcon not in _gp_ctrl.candidates(HUMAN))
    # "VISIBLE" - the optional collaborator, refusing everything.
    tk.line_up(_gp_falcon, 20.0, 24.0, spacing=1.2)
    _gp_blind = egp.GuidingPresenceController(
        game_state=_gp_state, auto_players=(HUMAN,), visible=lambda a, b: False)
    c.eq("...and one in range but not VISIBLE is not either",
         _gp_blind.candidates(HUMAN), [])

    # The mark itself, and its lifetime.
    c.true("nothing is marked before the phase starts", not _gp_ctrl.applies(_gp_falcon))
    _gp_ctrl.offer_at_start_of_shooting_phase(HUMAN)
    c.true("...the chosen unit is marked", _gp_ctrl.applies(_gp_falcon))
    c.true("...and no other unit is", not _gp_ctrl.applies(_gp_banshees))
    _gp_ctrl.reset_phase()
    c.true("...and the mark is gone next phase", not _gp_ctrl.applies(_gp_falcon))

# ...end to end through the REAL hit step.
_gp_scene = tk.shooting_scene(D["Falcon"], D["Dire Avengers"], attacker_owner=HUMAN)
tk.line_up(_gp_scene["attacker"], 20.0, 20.0, spacing=1.2)
tk.line_up(_gp_scene["target"], 20.0, 26.0, spacing=1.2)
_gp_shoot = _gp_scene["shooting"]
_gp_shoot.active_squad = _gp_scene["attacker"]
_gp_grp = _group(_gp_scene)
_gp_live = egp.GuidingPresenceController(game_state=_gp_state)
_gp_shoot.guiding_presence = _gp_live
with only("ARMOURED_WARHOST_PLAYERS"):
    _gp_before = [m.source for m in _gp_shoot._hit_modifiers(_gp_grp)]
    _gp_live._choose(HUMAN, _gp_scene["attacker"])
    _gp_after = _gp_shoot._hit_modifiers(_gp_grp)
c.true("the real hit step is clean before the mark",
       egp.GUIDING_PRESENCE_LABEL not in _gp_before)
c.true("...and carries it after",
       egp.GUIDING_PRESENCE_LABEL in [m.source for m in _gp_after])
c.eq("...as a -1 on the threshold, i.e. an EASIER roll",
     apply_modifiers(3, [m for m in _gp_after
                         if m.source == egp.GUIDING_PRESENCE_LABEL]), 2)

# RANGED, so not in the Fight phase.
c.true("Guiding Presence never reaches the Fight phase",
       "enh_guiding_presence" not in _fight_src)

# WIRING - the class this repo has been bitten by seven times.
c.true("main.py builds the Guiding Presence controller",
       "guiding_presence_controller = GuidingPresenceController(" in _main_src2)
c.true("...hands it to the shooting controller",
       "shooting_controller.guiding_presence = guiding_presence_controller" in _main_src2)
c.true("...and drives it at the start of the Shooting phase",
       "guiding_presence_controller.offer_at_start_of_shooting_phase(" in _main_src2)
c.true("...clearing the previous mark first",
       before(_main_src2, "guiding_presence_controller.reset_phase()",
              "guiding_presence_controller.offer_at_start_of_shooting_phase("))


# --- 3d. Breath of Vaul: two re-rolls, two different rolls ----------------
# BUILT WITH THE TWO SPECIAL WEAPONS. The default Storm Guardian carries a
# shuriken pistol and nothing this card names, so a unit built plainly would
# exercise neither half - the checks below would pass while proving nothing.
_bv_leader = sq("Farseer")
_bv_unit = tk.build(D["Storm Guardians"], HUMAN, name="1 Storm Guardians 9", choices={
    "Storm Guardian": {aeldari_mod.STORM_GUARDIAN_PISTOL_TO_FLAMER: 1,
                       aeldari_mod.STORM_GUARDIAN_PISTOL_TO_FUSION: 1}})
attached_units.attach(_bv_leader, _bv_unit)
E.grant(_bv_unit, "Breath of Vaul", model=_leader_model(_bv_unit, "Farseer"))
_bv_flamer = next((w for m in _bv_unit.models for w in m.weapons
                   if ebv.is_flamer(w)), None)
_bv_fusion = next((w for m in _bv_unit.models for w in m.weapons
                   if ebv.is_fusion_gun(w)), None)
_bv_pistol = next(w for m in _bv_unit.models for w in m.weapons
                  if w.weapon_type == RANGED and not ebv.is_flamer(w)
                  and not ebv.is_fusion_gun(w))
c.true("the unit really carries a flamer", _bv_flamer is not None)
c.true("...and a fusion gun", _bv_fusion is not None)
# The flamer's Attacks characteristic IS a die - which is the whole reason the
# first half exists.
c.true("...whose Attacks characteristic is a die",
       _bv_flamer is not None and _bv_flamer.attacks_notation is not None)
c.true("...and the fusion gun's Damage is a die too",
       _bv_fusion is not None and _bv_fusion.damage_notation is not None)

with only("GUARDIAN_BATTLEHOST_PLAYERS"):
    c.true("the three shared conditions hold for a led STORM GUARDIANS unit",
           ebv.applies(_bv_unit))
    _bv_wrong = _led("Autarch", "Howling Banshees")
    setattr(_bv_wrong.models[0].profile, "breath_of_vaul", True)
    c.true("...and not for a led unit that is not STORM GUARDIANS",
           not ebv.applies(_bv_wrong))
    # LEADING, isolated: a STORM GUARDIANS unit carrying it with nobody
    # leading, so the keyword clause cannot be the one refusing.
    _bv_unled = sq("Storm Guardians")
    setattr(_bv_unled.models[0].profile, "breath_of_vaul", True)
    c.true("the isolating unit really is STORM GUARDIANS",
           attached_units.unit_has_datasheet_keyword(_bv_unled, "STORM GUARDIANS"))
    c.true("...but with nobody leading it, neither half applies",
           not ebv.applies(_bv_unled))
with none_fielded():
    c.true("no detachment, nothing", not ebv.applies(_bv_unit))

# THE TWO HALVES ARE DIFFERENT WEAPONS. Reading one for the other would make
# the card fire on the wrong die.
with only("GUARDIAN_BATTLEHOST_PLAYERS"):
    c.true("the FLAMER gets the Attacks half", ebv.attacks_reroll_applies(_bv_unit, _bv_flamer))
    c.true("...and not the Damage half", not ebv.damage_reroll_applies(_bv_unit, _bv_flamer))
    c.true("the FUSION GUN gets the Damage half", ebv.damage_reroll_applies(_bv_unit, _bv_fusion))
    c.true("...and not the Attacks half", not ebv.attacks_reroll_applies(_bv_unit, _bv_fusion))
    c.true("a shuriken pistol gets neither half",
           not ebv.attacks_reroll_applies(_bv_unit, _bv_pistol)
           and not ebv.damage_reroll_applies(_bv_unit, _bv_pistol))
with none_fielded():
    c.true("...and without the detachment, the flamer gets nothing either",
           not ebv.attacks_reroll_applies(_bv_unit, _bv_flamer))

# The class match is EXACT, measured: neither profile has subclasses, so
# matching by class cannot quietly widen to another datasheet's flamer.
import inspect as _inspect  # noqa: E402
from game import weapons as _W  # noqa: E402
for _bv_name in ("AeldariFlamerProfile", "FusionGunProfile"):
    _bv_base = getattr(_W, _bv_name)
    c.eq("%s has no subclasses to widen into" % _bv_name,
         [k.__name__ for k in vars(_W).values()
          if _inspect.isclass(k) and k is not _bv_base and issubclass(k, _bv_base)], [])

# NOT a reroll_scope source. That module is the narrower "the 1s OR the whole
# roll" shape; listing these there would offer a failures-only subset the
# printed text never grants. Only visible as an absence.
c.true("Breath of Vaul is not a reroll_scope source",
       "breath_of_vaul" not in io.open("game/reroll_scope.py", encoding="utf-8").read())

# WIRING, both halves, at the call expression.
c.true("the ATTACKS half is offered in the real attacks step",
       "enh_breath_of_vaul.attacks_reroll_applies(self.active_squad, raw_weapon)" in _shoot_src)
c.true("the DAMAGE half joins the existing offer chain",
       "enh_breath_of_vaul.damage_reroll_applies(self.active_squad, weapon)" in _shoot_src)
# The re-roll has to be a REAL new visible roll, or the offer buys nothing.
# THE CODE FORM, not the bare flag name: the first version of this guard
# matched the method's own DOCSTRING, which explains that the re-roll is
# "marked is_reroll=True" - so it stayed green with the flag deleted from the
# call. Same lesson this repo records about guards matching their own
# explanation.
c.true("...and an accepted Attacks re-roll throws a new visible roll",
       "log=self._log, is_reroll=True," in
       _shoot_src.split("def _after_attacks_reroll")[1].split("def _finish_attacks_roll")[0])

# THE EXTRACTION: one definition, two names.
from game import damage_reroll as _dr_shim  # noqa: E402
from game import notation_reroll as _nr  # noqa: E402
c.true("damage_reroll re-exports notation_reroll's class, not a copy",
       _dr_shim.DamageRerollOffer is _nr.DamageRerollOffer)
c.eq("...and the roll name defaults to Damage, so every old caller is unchanged",
     _nr.DamageRerollOffer("x").roll_name, "Damage")


# --- 3e. Mantle of Wisdom: it widens the RULE ------------------------------
_mw_unit = _led("Autarch", "Dire Avengers")
E.grant(_mw_unit, "Mantle of Wisdom")
_mw_ctrl = potw.PathOfTheWarriorController()

with only("ASPECT_HOST_PLAYERS"):
    c.true("the bearer's led ASPECT WARRIORS unit qualifies", emw.applies(_mw_unit))
    # BOTH abilities - the whole point of the card.
    c.true("it gains the HIT half", _mw_ctrl.hit_ones_apply(_mw_unit))
    c.true("...and the WOUND half at the same time",
           _mw_ctrl.wound_ones_apply(_mw_unit))
    # ...and therefore is never asked to choose. Offering a choice that
    # changes nothing would read as a limit that no longer exists.
    c.true("no choice is offered", not _mw_ctrl.offer(_mw_unit))

    # THE CONTRAST, on a unit without it: exactly one half, and it IS asked.
    _mw_plain = sq("Dire Avengers")
    c.true("a unit without it gets neither half until it chooses",
           not _mw_ctrl.hit_ones_apply(_mw_plain)
           and not _mw_ctrl.wound_ones_apply(_mw_plain))
    _mw_ctrl.choose(_mw_plain, potw.HIT)
    c.true("...and then exactly one",
           _mw_ctrl.hit_ones_apply(_mw_plain)
           and not _mw_ctrl.wound_ones_apply(_mw_plain))
    # THE TWO CONDITIONS, ISOLATED - neither was reachable through the
    # detachment gate alone, so deleting either left the suite green.
    _mw_unled = sq("Dire Avengers")
    setattr(_mw_unled.models[0].profile, "mantle_of_wisdom", True)
    c.true("an ASPECT WARRIORS unit with nobody leading it does not qualify",
           not emw.applies(_mw_unled))
    _mw_wrong = _led("Farseer", "Guardian Defenders")
    setattr(_leader_model(_mw_wrong, "Farseer").profile, "mantle_of_wisdom", True)
    c.true("...and a LED unit that is not ASPECT WARRIORS does not either",
           not emw.applies(_mw_wrong))
    c.true("...though it really is led", 
           attached_units.leader_ability(_mw_wrong, "mantle_of_wisdom"))
with none_fielded():
    c.true("no detachment, nothing", not emw.applies(_mw_unit))

# READ AT THE RULE, not at the four consumers - so a widening cannot be
# applied to three of them.
_potw_src = io.open("game/path_of_the_warrior.py", encoding="utf-8").read()
c.eq("the rule itself reads Mantle of Wisdom, in both of its answers",
     _potw_src.count("enh_mantle_of_wisdom.applies(squad)"), 3)
for _mw_file in ("game/shooting.py", "game/fight.py"):
    c.true("%s never reads it directly" % _mw_file,
           "enh_mantle_of_wisdom" not in io.open(_mw_file, encoding="utf-8").read())


# =========================================================================
# 4. Defence and concealment
#    Runes of Warding, Rune of Mists, Camouflaged Snipers,
#    Spirit Stone of Raelyth.
# =========================================================================
print("\n4. Defence and concealment")

_dr_src = io.open("game/damage_resolution.py", encoding="utf-8").read()

from game import conditional_lone_operative as clo  # noqa: E402
from game import enh_camouflaged_snipers as ecs  # noqa: E402
from game import enh_rune_of_mists as erm  # noqa: E402
from game import enh_runes_of_warding as erw  # noqa: E402
from game import enh_spirit_stone_of_raelyth as essr  # noqa: E402
from game import feel_no_pain as fnp_mod  # noqa: E402
from game import hidden_after_shooting as has_mod  # noqa: E402
from game.decision import DecisionManager  # noqa: E402


# --- 4a. Runes of Warding: THREE conditions, one 4+ -----------------------
_rw_unit = _led("Farseer", "Guardian Defenders")
E.grant(_rw_unit, "Runes of Warding", model=_leader_model(_rw_unit, "Farseer"))
# attach() merges the leader in LAST, so models[-1] IS the Farseer - the
# bearer, not a bodyguard. models[0] is the one that proves "models in the
# bearer's UNIT" rather than "the bearer".
_rw_model = _rw_unit.models[0]

with only("SEER_COUNCIL_PLAYERS"):
    # Each condition ALONE is enough - they are alternatives, not a
    # conjunction. Read as "and" the card would be nearly unreachable.
    c.eq("a MORTAL wound gets the 4+", erw.feel_no_pain(_rw_model, mortal=True), "4+")
    c.eq("a PSYCHIC attack gets it too", erw.feel_no_pain(_rw_model, psychic=True), "4+")
    c.eq("...and a DEVASTATING critical wound", erw.feel_no_pain(_rw_model, devastating=True), "4+")
    # ...and an ordinary wound gets NOTHING, which is the whole point of a
    # conditional source.
    c.eq("an ordinary wound gets nothing", erw.feel_no_pain(_rw_model), "-")
    # The bearer's WHOLE UNIT, not just the bearer.
    c.true("it reaches a bodyguard, not only the bearer",
           _rw_model not in E.bearer_models(_rw_unit, "Runes of Warding"))
with none_fielded():
    c.eq("no detachment, nothing", erw.feel_no_pain(_rw_model, mortal=True), "-")

# NEVER None: the fold parses these strings, and None collapses it.
c.true("it never returns None", erw.feel_no_pain(None, mortal=True) == "-")

# ...end to end, through the REAL fold.
with only("SEER_COUNCIL_PLAYERS"):
    c.eq("the real fold resolves a psychic wound to 4+",
         fnp_mod.current_feel_no_pain(_rw_model, psychic=True), "4+")
    c.eq("...a devastating one likewise",
         fnp_mod.current_feel_no_pain(_rw_model, devastating=True), "4+")
    _rw_plain = fnp_mod.current_feel_no_pain(_rw_model)
    c.true("...and an ordinary wound is left as the model printed it",
           _rw_plain in (None, "-"))
    # NEVER WORSE THAN PRINTED: a model with a better printed FNP keeps it.
    _rw_better = _rw_unit.models[1]
    setattr(_rw_better.profile, "feel_no_pain", "3+")
    c.eq("a printed 3+ survives the granted 4+",
         fnp_mod.current_feel_no_pain(_rw_better, mortal=True), "3+")
    setattr(_rw_better.profile, "feel_no_pain", None)

# ...and through the REAL sessions, which is where the three flags are set.
c.true("the mortal-wound session sets mortal=True",
       "mortal=True" in _dr_src.split("class MortalWoundAllocationSession")[1])
c.true("the devastating session sets devastating=True",
       "devastating=True" in _dr_src.split("class DevastatingWoundAllocationSession")[1])
# BOTH of DamageAllocationSession's Feel No Pain sites, counted. Wiring one
# and not the other is the shape this kind of bug actually takes, and a plain
# "is it in the file" guard cannot see it.
c.eq("...and BOTH damage-session sites read the WEAPON for psychic",
     _dr_src.count('psychic=bool(getattr(self.weapon, "psychic", False))'), 2)

# THE NAMED, UNCHANGED GAP: the devastating session still does NOT pass
# mortal=True, so Advanced Armour and Layered Wards do not apply there. That
# is pre-existing and a deliberate non-change (user decision) - pinned so it
# cannot drift silently in either direction.
# COMMENTS STRIPPED FIRST. The module explains at that very spot why mortal=True
# is deliberately NOT passed, so a plain substring search finds its own
# explanation and the guard passes whatever the code does - the same trap that
# caught the is_reroll guard one stage ago.
_dev_code = "\n".join(
    line for line in _dr_src.split("class DevastatingWoundAllocationSession")[1].splitlines()
    if not line.strip().startswith("#"))
c.true("the devastating session still does not claim to be a mortal wound",
       "mortal=True" not in _dev_code)
c.true("...while it does pass devastating=True", "devastating=True" in _dev_code)


# --- 4b. Rune of Mists: an INVERTED range --------------------------------
_rm_seer = sq("Spiritseer")
_rm_wraiths = sq("Wraithguard")
with only("SPIRIT_CONCLAVE_PLAYERS"):
    c.true("a WRAITH CONSTRUCT unit is a legal target", erm.eligible_target(_rm_wraiths))
    c.true("...and an ordinary unit is not", not erm.eligible_target(sq("Dire Avengers")))

# NO TITANIC EXCLUSION - this card does not print one, its neighbour does.
c.true("Stave of Kurnous excludes TITANIC", "is_non_titanic" in
       io.open("game/enh_stave_of_kurnous.py", encoding="utf-8").read())
c.true("...and Rune of Mists deliberately does not", "is_non_titanic" not in
       io.open("game/enh_rune_of_mists.py", encoding="utf-8").read())

# THE INVERTED DISTANCE, measured on BOTH sides of the line. Written the usual
# way round it would hand cover to exactly the enemies it means to exclude.
_rm_shooter = sq("Dire Avengers", "Player 2").models[0]
tk.line_up(_rm_wraiths, 20.0, 20.0, spacing=1.4)
setattr(_rm_wraiths, erm.FLAG_ATTR, True)
_rm_shooter.x_in, _rm_shooter.y_in = 20.0, 30.0        # 10" away: INSIDE 18"
c.true("an attacker within 18\" grants NO cover",
       not erm.grants_cover(_rm_shooter, _rm_wraiths))
_rm_shooter.x_in, _rm_shooter.y_in = 20.0, 45.0        # 25" away: OUTSIDE 18"
c.true("...and one outside 18\" does grant it",
       erm.grants_cover(_rm_shooter, _rm_wraiths))
setattr(_rm_wraiths, erm.FLAG_ATTR, False)
c.true("...and an unmarked unit gets nothing either way",
       not erm.grants_cover(_rm_shooter, _rm_wraiths))

# ...end to end, through the REAL cover computation.
_rm_scene = tk.shooting_scene(D["Dire Avengers"], D["Wraithguard"], attacker_owner="Player 2")
tk.line_up(_rm_scene["attacker"], 20.0, 50.0, spacing=1.2)   # far away
tk.line_up(_rm_scene["target"], 20.0, 20.0, spacing=1.4)
_rm_shoot = _rm_scene["shooting"]
_rm_before = _rm_shoot._compute_benefit_of_cover(
    _rm_scene["attacker"].models[0], _rm_scene["target"])
setattr(_rm_scene["target"], erm.FLAG_ATTR, True)
_rm_after = _rm_shoot._compute_benefit_of_cover(
    _rm_scene["attacker"].models[0], _rm_scene["target"])
c.true("the real cover step grants it to a distant attacker's target",
       _rm_after and not _rm_before)
setattr(_rm_scene["target"], erm.FLAG_ATTR, False)

# WIRING.
c.true("main.py builds the Rune of Mists controller",
       "rune_of_mists_controller = RuneOfMistsController(" in _main_src2)
c.true("...and drives it from the Command phase",
       "rune_of_mists_controller.begin_command_phase(turn_tracker.turn_owner)" in _main_src2)


# --- 4c. Camouflaged Snipers: the THIRD shared-question source ------------
_cs_rangers = sq("Rangers")
E.grant(_cs_rangers, "Camouflaged Snipers")
with only("PATH_OF_THE_OUTCAST_PLAYERS"):
    c.true("its own shooting no longer breaks Hidden", ecs.applies(_cs_rangers))
    # ...and through the SHARED question, which is what game/shooting.py asks.
    c.true("the shared question says so too", has_mod.keeps_hidden(_cs_rangers))
    # "IN YOUR Shooting phase" is handled once, in the shared module: a
    # REACTIVE shot (Fire Overwatch, in the opponent's turn) still reveals.
    c.true("...but a reactive shot still breaks Hidden",
           not has_mod.keeps_hidden(_cs_rangers, reactive=True))
with none_fielded():
    c.true("no detachment, nothing", not has_mod.keeps_hidden(_cs_rangers))

# UNIT-LEVEL: every model carries it, so "a living model still has it" means
# "the unit still exists".
c.true("every Ranger carries it",
       all(m.profile.camouflaged_snipers for m in _cs_rangers.models))

# game/shooting.py still asks exactly ONCE - which is the point of the shared
# module, and what a third source must not change.
c.eq("shooting.py asks the shared question once",
     _shoot_src.count("hidden_after_shooting.keeps_hidden("), 1)


# --- 4d. Spirit Stone of Raelyth: two clauses, two seams ------------------
_ss_unit = _led("Farseer", "Guardian Defenders")
E.grant(_ss_unit, "Spirit Stone of Raelyth",
        model=_leader_model(_ss_unit, "Farseer"))
_ss_falcon = sq("Falcon")
_ss_banshees = sq("Howling Banshees")
tk.line_up(_ss_unit, 20.0, 20.0, spacing=1.2)
# BOTH clauses measure from the BEARER MODEL, which attach() puts at the end of
# an 11-model line - so a vehicle parked beside models[0] is ~12" away from it.
# Placed relative to the bearer instead, which is what the card measures.
_ss_bearer = _leader_model(_ss_unit, "Farseer")
tk.line_up(_ss_falcon, _ss_bearer.x_in, _ss_bearer.y_in + 2.0, spacing=1.2)
tk.line_up(_ss_banshees, _ss_bearer.x_in, _ss_bearer.y_in + 2.0, spacing=1.2)
_ss_tokens = list(_ss_unit.models) + list(_ss_falcon.models) + list(_ss_banshees.models)

# CLAUSE 1: the fourth conditional Lone Operative.
with only("ARMOURED_WARHOST_PLAYERS"):
    c.true("near a friendly AELDARI VEHICLE, the bearer is a Lone Operative",
           essr.grants_lone_operative(_ss_unit, _ss_tokens))
    # ...and a non-VEHICLE friendly unit does not count.
    c.true("a friendly NON-vehicle does not grant it",
           not essr.grants_lone_operative(
               _ss_unit, list(_ss_unit.models) + list(_ss_banshees.models)))
    # 6" away: outside the printed 3" but inside anything a widened range
    # would plausibly slip to, so this distinguishes the two.
    tk.line_up(_ss_falcon, _ss_bearer.x_in, _ss_bearer.y_in + 6.0, spacing=1.2)
    c.true("...nor one out of 3\"",
           not essr.grants_lone_operative(_ss_unit, _ss_tokens))
    c.eq("...and the range really is the printed 3", essr.SPIRIT_STONE_RANGE_IN, 3.0)
    tk.line_up(_ss_falcon, _ss_bearer.x_in, _ss_bearer.y_in + 2.0, spacing=1.2)
with none_fielded():
    c.true("no detachment, nothing", not essr.grants_lone_operative(_ss_unit, _ss_tokens))

# It joins the SHARED list rather than a fourth hand-written block in
# game/status_effects.py - which is what that extraction was for.
# (the count itself is pinned in section 0b, next to the extraction)
with only("ARMOURED_WARHOST_PLAYERS"):
    c.true("...and the shared reader returns this one's range",
           essr.SPIRIT_STONE_RANGE_IN in clo.granted_ranges(_ss_unit, _ss_tokens))

# CLAUSE 2: the heal, and its TWO moments.
_ss_ctrl = essr.SpiritStoneOfRaelythController(
    game_state=_E3State(_ss_unit, _ss_falcon), auto_players=(HUMAN,))
_ss_hull = _ss_falcon.models[0]
with only("ARMOURED_WARHOST_PLAYERS"):
    # A FULL-strength vehicle is not offered a heal that would do nothing.
    c.eq("an undamaged vehicle is not a heal target",
         essr.heal_targets(_ss_unit, _ss_tokens), [])
    _ss_hull.current_wounds = _ss_hull.profile.wounds - 3
    c.true("a damaged one is",
           _ss_hull in essr.heal_targets(_ss_unit, _ss_tokens))

    # AT THE START of the move.
    _ss_ctrl.on_move_started(_ss_unit)
    c.true("the heal is offered at the START of the move",
           _ss_hull.current_wounds > _ss_falcon.models[0].profile.wounds - 3)
    # ...and ONCE per move: the end no longer offers it.
    _ss_before_end = _ss_hull.current_wounds
    _ss_ctrl.on_move_finished(_ss_unit)
    c.eq("...and not a second time at the end of the same move",
         _ss_hull.current_wounds, _ss_before_end)

    # A NEW move re-opens it.
    _ss_hull.current_wounds = _ss_hull.profile.wounds - 3
    _ss_ctrl.on_move_started(_ss_unit)
    c.true("a new move opens it again",
           _ss_hull.current_wounds > _ss_falcon.models[0].profile.wounds - 3)

    # DECLINING at the start must NOT spend it - "start OR end" is a choice of
    # timing. Driven through a real DecisionManager so the decline is real.
    _ss_hull.current_wounds = _ss_hull.profile.wounds - 3
    _ss_dm = DecisionManager()
    _ss_human = essr.SpiritStoneOfRaelythController(
        game_state=_E3State(_ss_unit, _ss_falcon), decision_manager=_ss_dm)
    _ss_human.on_move_started(_ss_unit)
    tk.pick_option(_ss_dm, "Do not heal")
    c.eq("declining at the start heals nothing",
         _ss_hull.current_wounds, _ss_hull.profile.wounds - 3)
    c.true("...and the end of the move still offers it",
           _ss_human.offer(_ss_unit))

    # The heal never overshoots the printed wounds.
    # SCRIPTED: one wound missing and a rolled 3, so the heal WOULD overshoot
    # by two. Left to chance a rolled 1 lands exactly on full and the cap is
    # never exercised.
    _ss_hull.current_wounds = _ss_hull.profile.wounds - 1
    _ss_ctrl._used_this_move.clear()
    tk.script(3)
    _ss_ctrl.offer(_ss_unit)
    c.eq("a heal is capped at the model's printed wounds",
         _ss_hull.current_wounds, _ss_hull.profile.wounds)
    tk.script()

# THE NEW HOOK is the mirror of the existing one, and fired from the ONE
# shared entry - so it cannot be wired to some move types and not others.
_move_src = io.open("game/movement.py", encoding="utf-8").read()
c.true("MovementController declares on_move_started",
       "self.on_move_started = []" in _move_src)
c.true("...fired from _begin_move, the shared entry",
       "for listener in (self.on_move_started or ()):" in
       _move_src.split("def _begin_move")[1].split("def start_move")[0])
# Ten until Retro-thrusters' Fall Back half was fixed: it used to delegate to
# start_fall_back_move(), which is gated on the Movement phase, so at the end of
# the Fight phase where the ability fires it returned early and NO move was ever
# opened - the half never worked, and this hook could not fire for it. It calls
# _begin_move() directly now, like the Normal half beside it. A count rather
# than a floor on purpose: a new path that skips the shared entry has to be
# noticed, and a >= would let one through.
c.eq("...which every move type goes through", _move_src.count("self._begin_move("), 11)

# WIRING - both hooks, or the card only half works.
c.true("main.py builds the Spirit Stone controller",
       "spirit_stone_controller = SpiritStoneOfRaelythController(" in _main_src2)
c.true("...and listens on the START of a move",
       "movement_controller.on_move_started.append(spirit_stone_controller.on_move_started)"
       in _main_src2)
c.true("...and on the END of one",
       "movement_controller.on_move_finished.append(spirit_stone_controller.on_move_finished)"
       in _main_src2)


# =========================================================================
# 5. CP and resource economy
#    Protector of the Paths, Gift of Foresight, Echoes of Ulthanesh,
#    Torc of Morai-Heg, Timeless Strategist, Lucid Eye.
# =========================================================================
print("\n5. CP and resource economy")

from game import enh_echoes_of_ulthanesh as eeu  # noqa: E402
from game import enh_gift_of_foresight as egf  # noqa: E402
from game import enh_lucid_eye as ele  # noqa: E402
from game import enh_protector_of_the_paths as epp  # noqa: E402
from game import enh_timeless_strategist as ets  # noqa: E402
from game import enh_torc_of_morai_heg as etm  # noqa: E402
from game import free_stratagem_once_per_round as fsopr  # noqa: E402
from game import cp_discount  # noqa: E402
from game.command_points import CommandPointManager  # noqa: E402
from game.stratagems import Stratagem, StratagemController  # noqa: E402

_strat_src = io.open("game/stratagems.py", encoding="utf-8").read()


class _E5Objective:
    """The two things Protector of the Paths asks of an objective."""

    def __init__(self, x_in, y_in, controlled_by):
        self.controlled_by = controlled_by
        self.terrain_area = _E5Area(x_in, y_in)


class _E5Area:
    def __init__(self, x_in, y_in):
        self.x_in, self.y_in = x_in, y_in

    def distance_to_model(self, model):
        return ((model.x_in - self.x_in) ** 2 + (model.y_in - self.y_in) ** 2) ** 0.5


class _E5Zone:
    """A rectangular stand-in for a DeploymentZone - only contains_point is
    read, and the real shapes are exercised by test_deployment_shapes.py."""

    def __init__(self, x_in, y_in, w_in, h_in):
        self.x_in, self.y_in, self.w_in, self.h_in = x_in, y_in, w_in, h_in

    def contains_point(self, x_in, y_in):
        return (self.x_in <= x_in <= self.x_in + self.w_in
                and self.y_in <= y_in <= self.y_in + self.h_in)


class _Turn5:
    def __init__(self, battle_round=1, turn_owner=HUMAN):
        self.battle_round = battle_round
        self.turn_owner = turn_owner


def _cp(**start):
    m = CommandPointManager()
    for player, amount in start.items():
        m.cp[player.replace("_", " ")] = amount
    return m


# --- 5a. the shared "for 0CP" sentence ------------------------------------
# FREE, NOT CHEAPER: the discount is whatever the Stratagem costs, so a 2CP
# use is as free as a 1CP one. A flat -1 would look right on every 1CP
# Stratagem and quietly charge for the rest.
_f_unit = _led("Farseer", "Guardian Defenders")
E.grant(_f_unit, "Gift of Foresight", model=_leader_model(_f_unit, "Farseer"))
_f_disc = egf.GiftOfForesightDiscount(turn_tracker=_Turn5())
_cheap = Stratagem(name="Command Re-roll", cp_cost=1, effect=lambda *a: None)
_dear = Stratagem(name="Command Re-roll", cp_cost=2, effect=lambda *a: None)
_other = Stratagem(name="Fire Overwatch", cp_cost=1, effect=lambda *a: None)
with only("WARHOST_PLAYERS"):
    c.eq("a 1CP use is free", _f_disc.available_discount(HUMAN, _cheap, [_f_unit]), 1)
    c.eq("...and so is a 2CP one, entirely", _f_disc.available_discount(HUMAN, _dear, [_f_unit]), 2)
    # KEYED ON THE STRATAGEM, which is what separates these from the four flat
    # CP discounts: another Stratagem on the same unit gets nothing.
    c.eq("a DIFFERENT Stratagem gets nothing",
         _f_disc.available_discount(HUMAN, _other, [_f_unit]), 0)
    # PURE QUERY: asking the price must never burn the once-per-round use.
    _f_disc.available_discount(HUMAN, _cheap, [_f_unit])
    _f_disc.available_discount(HUMAN, _cheap, [_f_unit])
    c.true("asking twice does not spend it", _f_disc.available(HUMAN))
    _f_disc.consume(HUMAN, _cheap, [_f_unit])
    c.true("...and consuming does", not _f_disc.available(HUMAN))
    c.eq("...so the second use in the round costs full price",
         _f_disc.available_discount(HUMAN, _cheap, [_f_unit]), 0)
with none_fielded():
    c.eq("no detachment, no discount",
         egf.GiftOfForesightDiscount(turn_tracker=_Turn5())
         .available_discount(HUMAN, _cheap, [_f_unit]), 0)

# It is a SUBCLASS of the plain CP discount, so the once-per-round ledger has
# exactly one definition.
c.true("it inherits the shared once-per-round machinery",
       issubclass(fsopr.FreeNamedStratagemOncePerRound, cp_discount.OncePerRoundCpDiscount))


# --- 5b. Protector of the Paths: the Snap Shooting override ---------------
_pp_unit = _led("Farseer", "Guardian Defenders")
E.grant(_pp_unit, "Protector of the Paths", model=_leader_model(_pp_unit, "Farseer"))
_pp_disc = epp.ProtectorOfThePathsDiscount(turn_tracker=_Turn5())
_ow = Stratagem(name="Fire Overwatch", cp_cost=1, effect=lambda *a: None)

with only("GUARDIAN_BATTLEHOST_PLAYERS"):
    # THE LATCH, not merely the bearer. Fire Overwatch is once per PHASE, the
    # discount once per battle ROUND - so a second, PAID Overwatch in the same
    # round is an ordinary one and hits on 6s.
    c.eq("before the free use, nothing overrides 15.09's 6",
         epp.snap_hit_threshold(_pp_disc, _pp_unit, []), None)
    _pp_disc.consume(HUMAN, _ow, [_pp_unit])
    c.eq("the free Overwatch hits on 5+",
         epp.snap_hit_threshold(_pp_disc, _pp_unit, []), 5)
    _pp_disc.clear_activation()
    c.eq("...and once that activation ends, 6s again",
         epp.snap_hit_threshold(_pp_disc, _pp_unit, []), None)

    # THE 4+ NEEDS A CONTROLLED OBJECTIVE - both halves.
    _pp_disc2 = epp.ProtectorOfThePathsDiscount(turn_tracker=_Turn5())
    _pp_disc2.consume(HUMAN, _ow, [_pp_unit])
    tk.line_up(_pp_unit, 20.0, 20.0, spacing=1.2)
    _pp_mine = _E5Objective(20.0, 20.0, HUMAN)
    _pp_theirs = _E5Objective(20.0, 20.0, "Player 2")
    c.eq("an objective the OPPONENT controls does not improve it",
         epp.snap_hit_threshold(_pp_disc2, _pp_unit, [_pp_theirs]), 5)
    c.eq("...one I control does", epp.snap_hit_threshold(_pp_disc2, _pp_unit, [_pp_mine]), 4)
    _pp_far = _E5Objective(20.0, 60.0, HUMAN)
    c.eq("...and one I control but am nowhere near does not",
         epp.snap_hit_threshold(_pp_disc2, _pp_unit, [_pp_far]), 5)

    # "WHILE THE BEARER IS LEADING A DIRE AVENGERS OR GUARDIANS UNIT" - EITHER
    # keyword, and neither is decoration. Guardian Defenders above carries
    # GUARDIANS; a led unit carrying neither gets nothing at all.
    c.true("Guardian Defenders carry one of the two named keywords",
           attached_units.unit_has_datasheet_keyword(_pp_unit, "GUARDIANS"))
    _pp_wrong = _led("Eldrad Ulthran", "Storm Guardians")
    setattr(_leader_model(_pp_wrong, "Eldrad Ulthran").profile,
            epp.FLAG_ATTR, True)
    c.true("...and Storm Guardians carry GUARDIANS too, so they qualify",
           epp.unit_has_bearer(_pp_wrong))

    # THE TWO CLAUSES, ISOLATED. A lone Farseer fails BOTH of them, so it
    # proves neither - neutralising either one left it refused by the other.
    # LEADING alone: a unit that HAS the keyword, carries the flag, and has
    # nobody leading it.
    _pp_unled = sq("Guardian Defenders")
    setattr(_pp_unled.models[0].profile, epp.FLAG_ATTR, True)
    c.true("the isolating unit really carries GUARDIANS",
           attached_units.unit_has_datasheet_keyword(_pp_unled, "GUARDIANS"))
    c.true("...but with nobody leading it, it does not qualify",
           not epp.unit_has_bearer(_pp_unled))
    # KEYWORD alone: a LED unit carrying neither printed keyword. Howling
    # Banshees are ASPECT WARRIORS and neither DIRE AVENGERS nor GUARDIANS.
    _pp_nokw = _led("Autarch", "Howling Banshees")
    setattr(_leader_model(_pp_nokw, "Autarch").profile, epp.FLAG_ATTR, True)
    c.true("the isolating unit really is led",
           attached_units.leader_ability(_pp_nokw, epp.FLAG_ATTR))
    c.true("...but carries neither named keyword, so it does not qualify",
           not epp.unit_has_bearer(_pp_nokw))

    # BOTH HALVES OF THE CARD ask the same three questions - granting the free
    # Overwatch where the threshold half refuses would be one sentence
    # disagreeing with itself. A FRESH discount, because _pp_disc2 has already
    # spent its once-per-round use and would answer 0 for that reason alone.
    _pp_disc3 = epp.ProtectorOfThePathsDiscount(turn_tracker=_Turn5())
    c.eq("...and it grants the free Overwatch where the threshold half agrees",
         _pp_disc3.available_discount(HUMAN, _ow, [_pp_unit]), 1)
    c.eq("...but refuses on a unit leading nothing",
         _pp_disc3.available_discount(HUMAN, _ow, [_pp_unled]), 0)
    c.eq("...and on one without either keyword",
         _pp_disc3.available_discount(HUMAN, _ow, [_pp_nokw]), 0)

# AN OVERRIDE, NOT A MODIFIER: 15.09 says modifiers are ignored, so a Modifier
# would be thrown away by the very rule this is meant to beat.
c.true("the shooting step overrides the base threshold rather than modifying it",
       "override = enh_protector_of_the_paths.snap_hit_threshold(" in _shoot_src)
c.true("...at 15.09's own branch",
       "override if override is not None else 6" in _shoot_src)
# ...and the latch is released when the activation ends.
_ow_src = io.open("game/overwatch.py", encoding="utf-8").read()
c.true("the Overwatch controller releases the latch",
       "self.protector_of_the_paths.clear_activation()" in _ow_src)


# --- 5c. Torc of Morai-Heg: the first SURCHARGE ---------------------------
_tm_unit = _led("Farseer", "Guardian Defenders")
E.grant(_tm_unit, "Torc of Morai-Heg", model=_leader_model(_tm_unit, "Farseer"))
_tm_enemy = sq("Dire Avengers", "Player 2")
tk.line_up(_tm_unit, 20.0, 20.0, spacing=1.2)
_tm_bearer = _leader_model(_tm_unit, "Farseer")
tk.line_up(_tm_enemy, _tm_bearer.x_in, _tm_bearer.y_in + 6.0, spacing=1.2)
_tm_state = _E3State(_tm_unit, _tm_enemy)

with only("SEER_COUNCIL_PLAYERS"):
    _tm = etm.TorcOfMoraiHegSurcharge(game_state=_tm_state, turn_tracker=_Turn5())
    _tm_strat = Stratagem(name="Some Ploy", cp_cost=1, effect=lambda *a: None)
    c.eq("an enemy Stratagem on a unit within 12\" costs 1CP more",
         _tm.available_surcharge("Player 2", _tm_strat, [_tm_enemy]), 1)
    # "YOUR OPPONENT targets" - it never taxes its own side.
    c.eq("...and the bearer's own Stratagems are untouched",
         _tm.available_surcharge(HUMAN, _tm_strat, [_tm_unit]), 0)
    # PURE QUERY again.
    _tm.available_surcharge("Player 2", _tm_strat, [_tm_enemy])
    c.true("asking does not spend it", _tm.available(HUMAN))
    # OUT OF RANGE.
    tk.line_up(_tm_enemy, _tm_bearer.x_in, _tm_bearer.y_in + 40.0, spacing=1.2)
    c.eq("a target out of 12\" is not taxed",
         _tm.available_surcharge("Player 2", _tm_strat, [_tm_enemy]), 0)
    tk.line_up(_tm_enemy, _tm_bearer.x_in, _tm_bearer.y_in + 6.0, spacing=1.2)
    # ONCE PER TURN.
    _tm.consume("Player 2", _tm_strat, [_tm_enemy])
    c.eq("...and only once per turn",
         _tm.available_surcharge("Player 2", _tm_strat, [_tm_enemy]), 0)

# THE ORDER: discount, clamp, THEN surcharge. The two orders differ exactly
# when a discount exceeds the cost - and the other one would let any discount
# at all cancel the tax.
c.true("the cost is clamped before the surcharge is added",
       before(_strat_src, "cost = max(0, cost)", "for surcharge in self.cost_surcharges:"))

# ...end to end, through the REAL StratagemController.
with only("SEER_COUNCIL_PLAYERS"):
    _sc = StratagemController(command_points=_cp(Player_2=1))
    _sc.cost_surcharges.append(
        etm.TorcOfMoraiHegSurcharge(game_state=_tm_state, turn_tracker=_Turn5()))
    _tax_strat = Stratagem(name="Taxed Ploy", cp_cost=1, effect=lambda *a: None)
    c.eq("a 1CP Stratagem costs 2CP under the Torc",
         _sc._cost_for("Player 2", _tax_strat, [_tm_enemy], 0), 2)
    # THE FAQ CLAUSE: priced out, it still counts as used this phase.
    c.true("...so with only 1CP it cannot be used",
           not _sc.can_use("Player 2", _tax_strat, [_tm_enemy]))
    c.true("...and using it fails", not _sc.use("Player 2", _tax_strat, [_tm_enemy]))
    c.true("...but it COUNTS AS USED this phase",
           ("Player 2", "Taxed Ploy") in _sc.used_this_phase)
    c.eq("...with no CP spent", _sc.command_points.cp["Player 2"], 1)

    # THE CONTRAST: unaffordable ANYWAY records nothing, which is the old
    # behaviour and must not change.
    _sc2 = StratagemController(command_points=_cp(Player_2=0))
    _sc2.cost_surcharges.append(
        etm.TorcOfMoraiHegSurcharge(game_state=_tm_state, turn_tracker=_Turn5()))
    _poor = Stratagem(name="Unaffordable Ploy", cp_cost=1, effect=lambda *a: None)
    c.true("a Stratagem nobody could afford anyway fails",
           not _sc2.use("Player 2", _poor, [_tm_enemy]))
    c.true("...and is NOT recorded as used",
           ("Player 2", "Unaffordable Ploy") not in _sc2.used_this_phase)


# --- 5d. Echoes of Ulthanesh: the two bonuses STACK -----------------------
_eu_unit = sq("Windriders")
E.grant(_eu_unit, "Echoes of Ulthanesh", model=_eu_unit.models[0])
_eu_model = _eu_unit.models[0]
_eu_own = _E5Zone(0.0, 0.0, 40.0, 12.0)
_eu_enemy = _E5Zone(0.0, 40.0, 40.0, 12.0)

_eu_model.x_in, _eu_model.y_in = 20.0, 6.0            # inside its own zone
c.eq("in your own zone: no bonus", eeu.roll_bonus(_eu_model, _eu_own, _eu_enemy), 0)
_eu_model.x_in, _eu_model.y_in = 20.0, 25.0           # no man's land
c.eq("outside it: +1", eeu.roll_bonus(_eu_model, _eu_own, _eu_enemy), 1)
_eu_model.x_in, _eu_model.y_in = 20.0, 45.0           # in the enemy zone
# THE STACK: a bearer in the opponent's zone is by definition not in its own,
# so it gets BOTH - a 3+ rather than a 5+. Read as either/or the card caps at
# +1 and the aggressive play it rewards buys nothing extra.
c.eq("in the ENEMY zone: +2, because both clauses apply",
     eeu.roll_bonus(_eu_model, _eu_own, _eu_enemy), 2)
c.eq("...which turns the printed 5+ into a 3+",
     eeu.ECHOES_THRESHOLD - 2, 3)

# NO ROLL WHEN THE CP CANNOT BE PAID.
with only("WINDRIDER_HOST_PLAYERS"):
    _eu_cp = _cp(Player_1=0)
    _eu_ctrl = eeu.EchoesOfUlthaneshController(
        game_state=_E3State(_eu_unit), command_points=_eu_cp,
        turn_tracker=_Turn5(), zones={HUMAN: (_eu_own, _eu_enemy)})
    tk.script(6)
    c.true("with headroom, it rolls", _eu_ctrl.begin_command_phase(HUMAN))
    c.eq("...and a 6 gains the CP", _eu_cp.cp.get(HUMAN, 0), 1)
    tk.script(6)
    c.true("...and with the round's bonus cap already spent, it does not roll",
           not _eu_ctrl.begin_command_phase(HUMAN))
    tk.script()


# --- 5e. Timeless Strategist: two ways to be present ----------------------
_ts_unit = _led("Farseer", "Guardian Defenders")
E.grant(_ts_unit, "Timeless Strategist", model=_leader_model(_ts_unit, "Farseer"))
with only("WARHOST_PLAYERS"):
    c.eq("a bearer on the battlefield grants a token",
         ets.extra_tokens_for(HUMAN, [_ts_unit], []), 1)
    # THE CLAUSE THAT IS EASY TO DROP: embarked in a transport that IS on the
    # battlefield still counts, and its models are off the token list.
    c.eq("...and so does one embarked in a transport that is",
         ets.extra_tokens_for(HUMAN, [], [_ts_unit]), 1)
    # ...while a unit in NEITHER collection - Strategic Reserves - does not.
    # Vacuous on its own (nothing is iterated), so it is stated together with
    # the discrimination that gives it meaning: the SAME unit grants a token
    # from either collection and nothing from neither.
    c.eq("a bearer in Reserves grants nothing",
         ets.extra_tokens_for(HUMAN, [], []), 0)
    c.true("...and that is a real discrimination, not an empty input",
           ets.extra_tokens_for(HUMAN, [_ts_unit], []) == 1
           and ets.extra_tokens_for(HUMAN, [], [_ts_unit]) == 1
           and ets.extra_tokens_for(HUMAN, [], []) == 0)
    c.eq("...and the other player gets nothing either",
         ets.extra_tokens_for("Player 2", [_ts_unit], []), 0)
with none_fielded():
    c.eq("no detachment, nothing", ets.extra_tokens_for(HUMAN, [_ts_unit], []), 0)

# It is a SECOND term beside Martial Grace's, not a replacement.
_bf_src = io.open("game/battle_focus.py", encoding="utf-8").read()
c.true("the grant adds Martial Grace's term",
       "martial_grace.extra_tokens_for(player)" in _bf_src)
c.true("...and this one as well",
       "enh_timeless_strategist.extra_tokens_for(" in _bf_src)


# --- 5f. Lucid Eye: a SWAP, not a bonus -----------------------------------
_le_unit = _led("Farseer", "Guardian Defenders")
E.grant(_le_unit, "Lucid Eye", model=_leader_model(_le_unit, "Farseer"))

# A Fate die's FACE is which Stratagem it pays for, and consume() removes by
# VALUE - so +-1 must REPLACE an entry. Modelled as a bonus the pool would
# still hold the old value and nothing would change.
_le_faces = [3, 3, 5]
c.true("a 3 can become a 4", (3, 4) in ele.adjustments(_le_faces))
c.true("...and a 2", (3, 2) in ele.adjustments(_le_faces))
# DEDUPLICATED ON THE PAIR: two 3s offer one "3 -> 4", not two identical
# choices.
c.eq("two identical dice offer one change each way",
     len([p for p in ele.adjustments(_le_faces) if p[0] == 3]), 2)
# CLAMPED TO A REAL FACE: a 6 cannot become a 7, or the pool holds a die that
# can never be spent.
c.true("a 6 cannot go above the highest real face",
       not any(b > max(ele.legal_values()) for _a, b in ele.adjustments([6])))
c.true("...and a 1 cannot go below the lowest",
       not any(b < min(ele.legal_values()) for _a, b in ele.adjustments([1])))

# THE SWAP ITSELF, in place.
_le_pool_faces = [3, 3, 5]
c.true("applying a change edits the pool", ele.apply_adjustment(_le_pool_faces, 3, 4))
c.eq("...replacing exactly one die", sorted(_le_pool_faces), [3, 4, 5])
c.true("...and a value that is not held changes nothing",
       not ele.apply_adjustment(_le_pool_faces, 6, 5))


# =========================================================================
# 6. Pre-game, movement and return
#    Firstdrawn Blade, Ethereal Pathway, Higher Duty, Phoenix Gem
#    - plus the SpiritMarkController repair.
# =========================================================================
print("\n6. Pre-game, movement and return")

from game import enh_ethereal_pathway as eep  # noqa: E402
from game import enh_firstdrawn_blade as efb  # noqa: E402
from game import enh_higher_duty as ehd  # noqa: E402
from game import enh_phoenix_gem as epg  # noqa: E402
from game import spiritseer as ss_mod  # noqa: E402
from game.movement import MovementController  # noqa: E402
from game.squad import squad_has_infiltrators  # noqa: E402

_pregame_src = io.open("game/pregame.py", encoding="utf-8").read()
_panel_src = io.open("game/ui/action_panel.py", encoding="utf-8").read()
_move_src6 = io.open("game/movement.py", encoding="utf-8").read()


# --- 6a. Firstdrawn Blade: Scouts, and the ordering that makes it real -----
_fb_unit = sq("Windriders")
E.grant(_fb_unit, "Firstdrawn Blade", model=_fb_unit.models[0])
with only("WINDRIDER_HOST_PLAYERS"):
    c.true("the bearer's unit qualifies", efb.applies(_fb_unit))
    efb.grant_scouts(_fb_unit)
    c.true("...and every model gets the Scouts range",
           all(m.profile.scouts == efb.FIRSTDRAWN_BLADE_SCOUTS_IN
               for m in _fb_unit.models))
c.eq("...which is the printed 9\"", efb.FIRSTDRAWN_BLADE_SCOUTS_IN, 9.0)
with none_fielded():
    c.true("no detachment, nothing", not efb.applies(sq("Windriders")))

# NEVER A DOWNGRADE. This card has NO "that do not have the Scouts ability"
# clause (its T'au cousin does), so it can land on a unit that already scouts -
# and shortening that unit's move would be a 10-point penalty.
# Striking Scorpions print Scouts 7" - SHORTER than the grant, so it is raised.
_fb_scorps = sq("Striking Scorpions")
c.true("Striking Scorpions print a Scouts range of their own",
       (_fb_scorps.models[0].profile.scouts or 0) > 0)
c.true("...which is shorter than this grant",
       _fb_scorps.models[0].profile.scouts < efb.FIRSTDRAWN_BLADE_SCOUTS_IN)
efb.grant_scouts(_fb_scorps)
c.eq("...so the grant raises it to 9",
     _fb_scorps.models[0].profile.scouts, efb.FIRSTDRAWN_BLADE_SCOUTS_IN)
# A LONGER one has to be CONSTRUCTED. Measured across every Aeldari datasheet,
# the longest printed Scouts range is exactly 9" (Leystalker, Shroud Runners,
# War Walkers) - so max() and a plain overwrite agree on the entire roster, and
# a guard using only real units would look tested while proving nothing.
_fb_long = sq("Striking Scorpions")
for _m in _fb_long.models:
    _m.profile.scouts = 12.0
efb.grant_scouts(_fb_long)
c.eq("...while a LONGER one survives untouched",
     _fb_long.models[0].profile.scouts, 12.0)

# THE ORDERING, which is the whole reason this is a pre-battle STEP: a Scouts
# grant made AFTER the Scout move step is carried and never used.
c.true("its step is registered BEFORE the Scouts step",
       "pregame_controller.prebattle_steps.insert(0, FirstdrawnBladeStep(" in _main_src2)
c.true("...and the queue really drains in order",
       "while self._prebattle_queue:" in _pregame_src
       and before(_pregame_src, "self._prebattle_queue.pop(0)", "self.scouts_step.start(self)"))
# It asks nothing, so it never stalls the sequence.
c.true("it resolves inline rather than prompting",
       efb.FirstdrawnBladeStep(game_state=_E3State(_fb_unit)).start(None) is False)


# --- 6b. Ethereal Pathway: one step EARLIER -------------------------------
_ep_seer = sq("Farseer")
E.grant(_ep_seer, "Ethereal Pathway")
_ep_guardians = sq("Guardian Defenders")
_ep_banshees = sq("Howling Banshees")

with only("ARMOURED_WARHOST_PLAYERS"):
    c.true("a GUARDIANS unit is a legal target",
           eep.is_eligible_target(_ep_guardians, HUMAN))
    c.true("...and a non-GUARDIANS unit is not",
           not eep.is_eligible_target(_ep_banshees, HUMAN))
    c.true("...nor an enemy one",
           not eep.is_eligible_target(sq("Guardian Defenders", "Player 2"), HUMAN))

    # 24.20 IS AN EVERY-MODEL ABILITY, so the grant has to mark all of them -
    # marking some would satisfy squad_has_infiltrators() not at all.
    c.true("before the grant the unit has no Infiltrators",
           not squad_has_infiltrators(_ep_guardians))
    eep.grant_infiltrators(_ep_guardians)
    c.true("every model is marked",
           all(m.profile.infiltrators for m in _ep_guardians.models))
    c.true("...so rule 24.20's every-model gate is satisfied",
           squad_has_infiltrators(_ep_guardians))
    # ...and a unit that already has it is not offered one that buys nothing.
    c.true("a unit that already has Infiltrators is not offered the grant",
           not eep.is_eligible_target(_ep_guardians, HUMAN))
c.eq("up to TWO units", eep.ETHEREAL_PATHWAY_MAX_UNITS, 2)

# THE ORDERING, and it is a step EARLIER than Firstdrawn Blade's: rule 24.20
# decides both WHERE a unit may be placed and WHEN, and the Deploy Armies step
# reads both. A grant made after it is carried and never used.
c.true("its step goes in deploy_armies_steps, not prebattle_steps",
       "pregame_controller.deploy_armies_steps.append(EtherealPathwayStep(" in _main_src2)
c.true("...which PregameController runs at the top of _set_deploy_order()",
       before(_pregame_src, "for step in self.deploy_armies_steps:",
              "self.state = DEPLOYING"))
# ...and that really is before deployment reads either half of 24.20.
c.true("...i.e. before the deployment order is set",
       before(_pregame_src, "for step in self.deploy_armies_steps:",
              "self.active_player = first_to_place"))


# --- 6c. Higher Duty: a REACTIVE move, with all four parts ----------------
_hd_unit = sq("Spiritseer")
E.grant(_hd_unit, "Higher Duty")
_hd_enemy = sq("Dire Avengers", "Player 2")
tk.line_up(_hd_unit, 20.0, 20.0, spacing=1.2)
tk.line_up(_hd_enemy, 20.0, 25.0, spacing=1.2)          # 5" away: inside 8"
_hd_tokens = list(_hd_unit.models) + list(_hd_enemy.models)
_hd_ctrl = ehd.HigherDutyController(
    game_state=_E3State(_hd_unit, _hd_enemy), all_tokens=_hd_tokens)

with only("SPIRIT_CONCLAVE_PLAYERS"):
    c.true("an enemy ending a move within 8\" lets it react",
           _hd_ctrl.can_react(_hd_unit, _hd_enemy))
    tk.line_up(_hd_enemy, 20.0, 40.0, spacing=1.2)      # 20" away
    c.true("...and not for an enemy that ended far away",
           not _hd_ctrl.can_react(_hd_unit, _hd_enemy))
    tk.line_up(_hd_enemy, 20.0, 25.0, spacing=1.2)

    # THE SECOND CLAUSE IS ABOUT THE REACTOR, not the mover, and isolating it
    # needs a THIRD unit: with the mover itself standing in Engagement Range
    # BOTH readings refuse (engagement is symmetric), so that case proves
    # nothing. Here a SECOND enemy pins the reactor while the mover ends its
    # move cleanly 5" away - only the reactor-side reading refuses.
    _hd_pinner = sq("Howling Banshees", "Player 2")
    tk.line_up(_hd_pinner, 20.0, 21.0, spacing=1.2)     # in Engagement Range
    _hd_ctrl2 = ehd.HigherDutyController(
        game_state=_E3State(_hd_unit, _hd_enemy, _hd_pinner),
        all_tokens=list(_hd_unit.models) + list(_hd_enemy.models)
        + list(_hd_pinner.models))
    c.true("the mover itself is clear of Engagement Range",
           not _hd_enemy.is_engaged(list(_hd_unit.models) + list(_hd_enemy.models)
                                    + list(_hd_pinner.models)))
    c.true("...but the REACTOR is pinned, so it cannot use this to walk away",
           not _hd_ctrl2.can_react(_hd_unit, _hd_enemy))

    # "YOUR OPPONENT'S Movement phase" - it never reacts to its own side. The
    # friendly mover is placed 5" away so the trigger distance and the
    # engagement clause both PASS and only the owner check can refuse.
    _hd_friend = sq("Dire Avengers", HUMAN)
    tk.line_up(_hd_friend, 20.0, 25.0, spacing=1.2)
    c.true("a friendly mover is within the trigger distance",
           _hd_ctrl._within(_hd_unit, _hd_friend, ehd.HIGHER_DUTY_TRIGGER_RANGE_IN))
    c.true("...and never triggers it anyway",
           not _hd_ctrl.can_react(_hd_unit, _hd_friend))
with none_fielded():
    c.true("no detachment, no reaction", not _hd_ctrl.can_react(_hd_unit, _hd_enemy))

c.eq("the trigger is 8\"", ehd.HIGHER_DUTY_TRIGGER_RANGE_IN, 8.0)
c.eq("...and the move is 6\"", ehd.HIGHER_DUTY_MOVE_IN, 6.0)

# THE FOUR PARTS OF A REACTIVE MOVE. CLAUDE.md records this exact failure being
# reported THREE times, so each is pinned rather than assumed.
c.true("1. its mode is registered in REACTIVE_MOVE_MODES",
       ehd.HIGHER_DUTY_MOVE_MODE in MovementController.REACTIVE_MOVE_MODES)
c.true("2. it hands active_player over and back",
       "self.turn_tracker.set_active(squad.owner)" in
       io.open("game/enh_higher_duty.py", encoding="utf-8").read()
       and "self.turn_tracker.set_active(self._restore_active)" in
       io.open("game/enh_higher_duty.py", encoding="utf-8").read())
c.true("3. the panel routes Confirm back to it",
       "confirm_callback = higher_duty_controller.confirm_move" in _panel_src)
c.true("...and Cancel too",
       "cancel_callback = higher_duty_controller.cancel_move" in _panel_src)
c.true("4. an open move blocks the phase change",
       "or higher_duty_controller.is_busy" in _main_src2)
# ...and it goes through the ONE door that reactive moves use.
c.true("it starts the move through start_battle_focus_move",
       "self.movement_controller.start_battle_focus_move(" in
       io.open("game/enh_higher_duty.py", encoding="utf-8").read())
c.true("main.py feeds it from on_move_finished",
       "movement_controller.on_move_finished.append(higher_duty_controller.on_move_finished)"
       in _main_src2)


# --- 6d. Phoenix Gem: once, at the end of the phase ------------------------
_pg_unit = sq("Guardian Defenders")
E.grant(_pg_unit, "Phoenix Gem", model=_pg_unit.models[0])
_pg_model = _pg_unit.models[0]
tk.line_up(_pg_unit, 30.0, 30.0, spacing=1.2)
_pg_ctrl = epg.PhoenixGemController(game_state=_E3State(_pg_unit), all_tokens=[])

with only("WARHOST_PLAYERS"):
    c.true("the bearer is recognised", epg.is_bearer(_pg_model))
    c.true("...and a squadmate is not", not epg.is_bearer(_pg_unit.models[1]))

    # "THE FIRST TIME" - once per battle, and NOT cleared by any reset.
    # NOTED WITH THE BEARER ALREADY DEAD, which is the only state this ever
    # sees. enhancements.is_active() would answer False here - its bearer half
    # filters the dead - so the gate is split into is_bearer() off the flag and
    # the detachment off the owner. Written the obvious way the card could
    # never have fired in a real game.
    _pg_model.current_wounds = 0
    c.true("its death is noted even though the bearer is dead",
           _pg_ctrl.notify_model_destroyed(_pg_unit, _pg_model))
    c.true("...but a second death is not",
           not _pg_ctrl.notify_model_destroyed(_pg_unit, _pg_model))

    # "AT THE END OF THE PHASE", on a 2+. Scripted, so both bands are measured
    # rather than whichever the die happened to give.
    tk.script(1)
    c.eq("a rolled 1 returns nothing", _pg_ctrl.resolve_end_of_phase(), [])
    _pg_ctrl._used.clear()
    _pg_ctrl.notify_model_destroyed(_pg_unit, _pg_model)
    tk.script(2)
    c.eq("...and a 2 returns it", len(_pg_ctrl.resolve_end_of_phase()), 1)
    c.eq("...with its FULL wounds", _pg_model.current_wounds, _pg_model.profile.wounds)
    tk.script()
c.eq("the threshold is the printed 2+", epg.PHOENIX_GEM_THRESHOLD, 2)

# "NOT WITHIN ENGAGEMENT RANGE" - the half position_valid() explicitly does not
# cover, and without it the model returns into the combat that killed it.
with only("WARHOST_PLAYERS"):
    _pg_enemy = sq("Dire Avengers", "Player 2")
    tk.line_up(_pg_enemy, 30.0, 30.5, spacing=1.2)       # right on top of it
    _pg_ctrl2 = epg.PhoenixGemController(
        game_state=_E3State(_pg_unit, _pg_enemy),
        all_tokens=list(_pg_unit.models) + list(_pg_enemy.models))
    _pg_spot = _pg_ctrl2._spot_for(_pg_model)
    c.true("a returning model is placed clear of Engagement Range",
           _pg_spot is None
           or all(((_pg_spot[0] - e.x_in) ** 2 + (_pg_spot[1] - e.y_in) ** 2) ** 0.5
                  - _pg_model.radius_in - e.radius_in > 2.0
                  for e in _pg_enemy.models))

# WIRING - the same two seams as its twin.
c.true("main.py notes the death in the sweep",
       "phoenix_gem_controller.notify_model_destroyed(" in _main_src2)
c.true("...and rolls at the end of the phase",
       "phoenix_gem_controller.resolve_end_of_phase()" in _main_src2)


# --- 6e. the SpiritMarkController repair ----------------------------------
# BUILT AND NEVER FED: mark(), available(), both candidate lists and
# start_of_movement_phase() all existed and were unit-tested, and nothing in
# main.py ever called any of them - so the mark could never be placed and the
# [SUSTAINED HITS 1] half above it was dead code.
c.true("main.py now feeds it at the START of a move",
       "movement_controller.on_move_started.append(spirit_mark_controller.on_move_started)"
       in _main_src2)
c.true("...and at the END of one",
       "movement_controller.on_move_finished.append(spirit_mark_controller.on_move_finished)"
       in _main_src2)
c.true("...which is what its printed text says",
       "starts or ends a move" in io.open("game/spiritseer.py", encoding="utf-8").read())
c.true("...and its own reset point is driven too",
       "spirit_mark_controller.start_of_movement_phase(turn_tracker.turn_owner)"
       in _main_src2)

# ...and the offer itself works end to end.
_sm_seer = sq("Spiritseer")
setattr(_sm_seer.models[0].profile, "spirit_mark", True)
_sm_wraiths = sq("Wraithguard")
_sm_enemy = sq("Dire Avengers", "Player 2")
tk.line_up(_sm_seer, 20.0, 20.0, spacing=1.2)
tk.line_up(_sm_wraiths, 20.0, 22.0, spacing=1.4)
tk.line_up(_sm_enemy, 20.0, 30.0, spacing=1.2)
_sm_dm = DecisionManager()
_sm_ctrl = ss_mod.SpiritMarkController(
    decision_manager=_sm_dm, all_tokens=list(_sm_seer.models) + list(_sm_wraiths.models)
    + list(_sm_enemy.models))
c.true("the mark is available before it is used", _sm_ctrl.available(_sm_seer))
# on_move_started RETURNS the offer's answer - it dropped it at first, so the
# hook reported "nothing happened" for an offer that was on screen.
c.true("a move offers it", _sm_ctrl.on_move_started(_sm_seer))
tk.pick_option(_sm_dm, _sm_wraiths.name)
if _sm_dm.is_pending:
    tk.pick_option(_sm_dm, _sm_enemy.name)
c.true("...and the pair is marked", _sm_ctrl.applies_to(_sm_wraiths, _sm_enemy))
# ONCE PER TURN, per army.
c.true("...once per turn", not _sm_ctrl.available(_sm_seer))
# "UNTIL THE START OF YOUR NEXT MOVEMENT PHASE" - its own, later reset point.
_sm_ctrl.start_of_movement_phase(HUMAN)
c.true("...and the mark is gone at the next Movement phase",
       not _sm_ctrl.applies_to(_sm_wraiths, _sm_enemy))
c.true("...and it is available again", _sm_ctrl.available(_sm_seer))


# --- 6f. all 28 are built -------------------------------------------------
_MODULE_FOR = {
    "Craftworld's Champion": "enh_craftworlds_champion",
    "Strategic Savant": "enh_strategic_savant",
    "Light of Clarity": "enh_light_of_clarity",
    "Assassins' Eye": "enh_assassins_eye",
    "Seersight Strike": "enh_psychic_weapons",
    "Psychic Destroyer": "enh_psychic_weapons",
    "Stone of Eldritch Fury": "enh_psychic_weapons",
    "Aspect of Murder": "enh_aspect_of_murder",
    "Stave of Kurnous": "enh_stave_of_kurnous",
    "Mirage Field": "enh_mirage_field",
    "Shimmerstone": "enh_shimmerstone",
    "Guiding Presence": "enh_guiding_presence",
    "Breath of Vaul": "enh_breath_of_vaul",
    "Mantle of Wisdom": "enh_mantle_of_wisdom",
    "Runes of Warding": "enh_runes_of_warding",
    "Rune of Mists": "enh_rune_of_mists",
    "Camouflaged Snipers": "enh_camouflaged_snipers",
    "Spirit Stone of Raelyth": "enh_spirit_stone_of_raelyth",
    "Protector of the Paths": "enh_protector_of_the_paths",
    "Gift of Foresight": "enh_gift_of_foresight",
    "Echoes of Ulthanesh": "enh_echoes_of_ulthanesh",
    "Torc of Morai-Heg": "enh_torc_of_morai_heg",
    "Timeless Strategist": "enh_timeless_strategist",
    "Lucid Eye": "enh_lucid_eye",
    "Firstdrawn Blade": "enh_firstdrawn_blade",
    "Ethereal Pathway": "enh_ethereal_pathway",
    "Higher Duty": "enh_higher_duty",
    "Phoenix Gem": "enh_phoenix_gem",
}
c.eq("every one of the 28 names a module", sorted(_MODULE_FOR), sorted(SPECS))
import importlib  # noqa: E402
for _name, _mod in sorted(_MODULE_FOR.items()):
    _m = importlib.import_module("game.%s" % _mod)
    # Each module QUOTES its own printed rule, so a card cannot be built from
    # memory of what it probably said.
    c.true("%s quotes its printed text" % _name,
           _name in (_m.__doc__ or "") or _name.replace("'", "\u2019") in (_m.__doc__ or ""))

# NEGATIVE SPACE: no AI path for any of the 28 (standing Aeldari rule).
_ai_src = io.open("ai/agent_driver.py", encoding="utf-8").read()
c.eq("no Enhancement module is imported by the AI",
     [m for m in set(_MODULE_FOR.values()) if m in _ai_src], [])


# --- 7. every one of the 28 is grantable, and grant() is what makes it live --
print("--- 7. grant() ---")

# The sections above prove the RULES work. They cannot prove an Enhancement is
# ever GIVEN to anybody - and section 9 measures that no shipped army list ever
# gives one, so is_active() is False for all 28 in a real game. That makes this
# the only place the grant path is exercised at all.
#
# The bearer is FOUND rather than transcribed: a table of "which datasheet
# carries which Enhancement" is a second copy of spec.can_bear(), and the copy
# is what drifts.

def _find_bearer(spec):
    """The first Aeldari unit with a model this Enhancement may be given to."""
    for _sheet_name in sorted(D):
        try:
            squad = tk.build(D[_sheet_name], HUMAN, name="1 %s 1" % _sheet_name)
        except Exception:
            continue
        if any(spec.can_bear(m, squad) for m in squad.models):
            return _sheet_name, squad
    return None, None


_no_bearer, _not_active, _wrong_points, _still_active, _not_refused = [], [], [], [], []
for _ename, _spec in sorted(SPECS.items()):
    _sheet, _squad = _find_bearer(_spec)
    if _squad is None:
        _no_bearer.append(_ename)
        continue
    _before_points = _squad.points
    with only(_spec.setting):
        E.grant(_squad, _ename)
        if not E.is_active(_squad, _ename):
            _not_active.append(_ename)
        if _before_points is not None and _squad.points != _before_points + _spec.points:
            _wrong_points.append((_ename, _squad.points, _before_points))
        # 19.04 IN THE SAME FRAME. remove_dead_models() runs once per frame, so
        # a model that died this frame is still in squad.models - the reading
        # is "a LIVING model still has it", not "the list still holds it".
        _was = [(m, m.current_wounds) for m in _squad.models]
        for _m in _squad.models:
            _m.current_wounds = 0
        if E.is_active(_squad, _ename):
            _still_active.append(_ename)
        for _m, _w in _was:
            _m.current_wounds = _w
    # ...and the DETACHMENT is what makes it live, not the grant. has() still
    # answers yes; is_active() must not. Two separate questions, because a
    # test that only asks has() passes with the gate deleted.
    with none_fielded():
        if E.is_active(_squad, _ename) or not E.has(_squad, _ename):
            _not_refused.append(_ename)

c.eq("every Aeldari Enhancement has a legal bearer among the built datasheets",
     _no_bearer, [])
c.eq("...and grant() really makes each one active", _not_active, [])
c.eq("...and moves the unit's points by exactly its cost", _wrong_points, [])
c.eq("...and a wiped-out bearer stops it in the SAME frame", _still_active, [])
c.eq("...while the detachment being off leaves has() true and is_active() false",
     _not_refused, [])
c.eq("...for all 28 of them", len(SPECS), 28)

# grant() REFUSES rather than guessing. Both refusals matter: a silently
# dropped Enhancement turns up much later as "the rule never triggers".
_spec7 = SPECS["Lucid Eye"]
_sheet7, _squad7 = _find_bearer(_spec7)
try:
    E.grant(_squad7, "Lucid Eye")
    E.grant(_squad7, "Lucid Eye")
    c.true("granting the same Enhancement twice is refused", False)
except ValueError:
    c.true("granting the same Enhancement twice is refused", True)
_wrong7 = tk.build(D["Guardian Defenders"], HUMAN, name="1 Guardian Defenders 9")
try:
    E.grant(_wrong7, "Lucid Eye")
    c.true("...and so is a bearer the printed line does not allow", False)
except ValueError:
    c.true("...and so is a bearer the printed line does not allow", True)


# --- 8. the five that ask the player something -----------------------------
print("--- 8. the prompts ---")

# Five Enhancement modules open a DecisionManager prompt of their own; the rest
# are passive adjustments. The difference is worth pinning: an Enhancement that
# should ask and does not is the "bought and did nothing" shape, and one that
# asks when it should not is a prompt nobody can explain.
_PROMPTING = sorted(m for m in set(_MODULE_FOR.values())
                    if "decision_manager.request" in
                    io.open("game/%s.py" % m, encoding="utf-8").read())
c.eq("exactly five Enhancement modules raise a prompt of their own",
     len(_PROMPTING), 5)
c.eq("...and they are the ones with a choice to make", _PROMPTING,
     ["enh_ethereal_pathway", "enh_guiding_presence", "enh_higher_duty",
      "enh_lucid_eye", "enh_spirit_stone_of_raelyth"])

# NOT ONE OF THEM IS A PANEL BUTTON. An Enhancement is not bought during the
# battle - it is paid for in the list - so none may join the proactive
# Stratagem registry. A set difference rather than a spot check: a future one
# that becomes a button has to force a decision here instead of appearing
# silently among the nineteen Stratagems.
_with_panel_label = sorted(m for m in set(_MODULE_FOR.values())
                           if "def panel_label(" in
                           io.open("game/%s.py" % m, encoding="utf-8").read())
c.eq("no Enhancement module offers itself as a panel button", _with_panel_label, [])
_main_src9 = io.open("main.py", encoding="utf-8").read()
c.eq("...and none is on the proactive Stratagem registry",
     [m for m in sorted(set(_MODULE_FOR.values()))
      if ("proactive_stratagems.add(%s" % m) in _main_src9], [])


# --- 9. the dormancy, measured and NAMED -----------------------------------
print("--- 9. dormant by roster ---")

# EXACTLY ONE of the 28 is bought by a shipped list, and 27 are still dormant.
#
# This used to read "NO shipped army list buys an Aeldari Enhancement", scoped
# to the single Aeldari list that existed - and it stayed GREEN when a second
# one arrived buying Timeless Strategist, because it only ever asked the first.
# That is the Mont'ka failure shape in miniature: the justification went stale
# while the assertion held. So the sweep is over EVERY shipped Aeldari list now,
# and the count is the claim.
#
# Named rather than left to be rediscovered, and deliberately NOT fixed by
# inventing roster content: which Enhancements a list buys is the list's own
# statement.
from game import army_lists as _al  # noqa: E402

_al_src = io.open("game/army_lists.py", encoding="utf-8").read()
c.eq("the eight Aeldari detachments print 28 Enhancements", len(SPECS), 28)
# COUNTED AS CALLS, not as text: army_lists.py mentions enhancements.grant()
# in the wrapper's own docstring, so a substring count reports two - the
# "a guard that matches its own explanation" trap this repo has met three
# times before.
import ast as _ast  # noqa: E402

_al_calls = [n for n in _ast.walk(_ast.parse(_al_src))
             if isinstance(n, _ast.Call) and isinstance(n.func, _ast.Attribute)
             and n.func.attr == "grant"
             and isinstance(n.func.value, _ast.Name)
             and n.func.value.id == "enhancements"]
c.eq("...and army_lists.py grants none itself any more",
     len(_al_calls), 0)
# Army lists are DATA now (armies/*.json), so this is asked of the loaded list
# rather than grepped out of a builder's source - which is both the stronger
# question and the only one that still has an answer. game/army_roster.py is the
# single place a grant happens, for every list alike.
_ar_src = io.open("game/army_roster.py", encoding="utf-8").read()
_ar_calls = [n for n in _ast.walk(_ast.parse(_ar_src))
             if isinstance(n, _ast.Call) and isinstance(n.func, _ast.Attribute)
             and n.func.attr == "grant"
             and isinstance(n.func.value, _ast.Name)
             and n.func.value.id == "enhancements"]
c.eq("...the ONE builder grants in exactly two places (a unit and its leaders)",
     len(_ar_calls), 2)
_aeldari_lists = [e for e in _al.ARMY_LISTS if e.faction_keyword == "AELDARI"]
c.eq("three shipped lists field this faction",
     [e.key for e in _aeldari_lists], ["aeldari", "aeldari_warhost", "aeldari_guardian_battlehost"])
_bought = sorted({n for e in _aeldari_lists for n in e.enhancement_names()})
# Asked of the LOADED lists rather than grepped out of a builder's source: army
# lists are data now, and enhancement_names() reads the same roster the game
# builds from.
c.eq("...and between them buy exactly one Enhancement",
     _bought, ["Timeless Strategist"])
c.eq("...which is a real Warhost Enhancement, not a name nothing resolves",
     SPECS["Timeless Strategist"].detachment, "Warhost")
c.eq("...leaving 27 of the 28 dormant by roster",
     len(SPECS) - len(_bought), 27)

# THE SECOND HALF OF THE SAME GAP, and the heavier one: the shipped lists
# declare five of the eight detachments between them, so three of them - and
# every Enhancement and Stratagem they carry - cannot be reached in a real game
# at all.
_declared = {d for e in _aeldari_lists for d in e.detachments}
c.eq("the shipped lists declare five of the eight detachments",
     (len(_declared), len(AELDARI_DETACHMENTS)), (5, 8))
c.eq("...namely these", sorted(_declared),
     ["Armoured Warhost", "Guardian Battlehost", "Path of the Outcast",
      "Seer Council", "Warhost"])
_reachable = sorted(n for n, s in SPECS.items() if s.detachment in _declared)
c.eq("...so sixteen of the Enhancements belong to a fielded detachment",
     len(_reachable), 16)
# BELONGING TO A FIELDED DETACHMENT IS NOT THE SAME AS BEING BOUGHT, and the
# gap between the two numbers is the whole point: a list can put a detachment
# on the table and still spend nothing on its Enhancements.
c.eq("...and fifteen of those sixteen are never granted",
     [n for n in _reachable if n not in _bought], sorted(set(_reachable) - set(_bought)))
c.eq("...which is fifteen", len([n for n in _reachable if n not in _bought]), 15)


c.finish()
