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


class settings_as:
    """config constants are real module globals; a test that left one set would
    change what every later test measures."""

    def __init__(self, **values):
        self.values = values

    def __enter__(self):
        self.old = {k: getattr(config, k) for k in self.values}
        for key, value in self.values.items():
            setattr(config, key, value)
        return self

    def __exit__(self, *exc):
        for key, value in self.old.items():
            setattr(config, key, value)


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
c.eq("three conditional sources are registered",
     len(conditional_lone_operative.SOURCES), 3)
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
c.true("...asking the precision question against the SPLIT weapon",
       "if self._precision_choice_needed(split_weapon, target_squad):" in _fight_src)

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


c.finish()
