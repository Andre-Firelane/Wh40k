"""The nineteen T'au detachment Enhancements.

Eighteen were built in one stage; the nineteenth (Starflare Ignition System)
already existed and was folded onto the shared registry, so it is checked here
too - the point of the registry is that all nineteen answer the same way.

Structure:
  1. game/enhancements.py - the registry, the bearer restrictions, grant()
  2. the detachment gate (what closes game/starflare_ignition.py's limitation)
  3. Retaliation Cadre - four
  4. Kauyon - four
  5. Mont'ka - four
  6. Experimental Prototype Cadre - three
  7. Advanced Acquisition Cadre - two
  8. Auxiliary Cadre - two
  9. what the predefined list hands out
 10. source guards (wiring that no behaviour test can see)
"""

import ast
import os
import collections
import io
import json

import testkit as tk
from game import army_io
from game import config
from game import enhancements as E
from game import enh_prototype_weapons as prototype_weapons
from game.factions import build_squad
from game.factions import tau_empire as t
from game.factions.tau_empire import (CADRE_FIREBLADE, COMMANDER_FARSIGHT,
                                      COMMANDER_IN_COLDSTAR_BATTLESUIT, CRISIS_FIREKNIFE,
                                      CRISIS_STARSCYTHE, GHOSTKEEL_BATTLESUIT,
                                      KROOT_CARNIVORES, KROOT_FLESH_SHAPER,
                                      PATHFINDER_TEAM, STEALTH_BATTLESUITS, STRIKE_TEAM,
                                      TAU_EMPIRE)

c = tk.Checks("T'au detachment Enhancements")


# The one definition lives in testkit - eight suites had their own copy.
settings_as = tk.settings_as

ALL_SETTINGS = sorted({spec.setting for spec in E.ENHANCEMENTS.values()})


def only(setting, players=("Player 2",)):
    """Field exactly one detachment - every other T'au setting emptied, so a
    test can never pass because some OTHER detachment happened to be on."""
    values = {name: () for name in ALL_SETTINGS}
    values[setting] = tuple(players)
    return settings_as(**values)


def none_fielded():
    return settings_as(**{name: () for name in ALL_SETTINGS})



class SpyDice:
    """A DiceManager stand-in that records the KWARGS of each roll.

    tk.RecordingDice keeps (label, values) but not the threshold or the count
    it was asked for, and these rules are about exactly those - "roll six D6:
    for each 4+". Values are injected, so nothing here depends on chance."""

    def __init__(self):
        self.rolls = []
        self.pending_values = []
        self.last_values = []
        self.already_rerolled = set()

    def roll(self, count, sides=6, **kwargs):
        self.rolls.append(dict(count=count, sides=sides, **kwargs))
        self.pending_values = [1] * count
        self.last_values = list(self.pending_values)
        return self.last_values

    @property
    def last(self):
        return self.rolls[-1] if self.rolls else {}

    def acknowledge(self):
        self.pending_values = []



def before(src, first, second):
    """True if `first` appears before `second` in `src`.

    A helper rather than two str.index() calls, because index() RAISES when a
    needle is gone - and a source guard that crashes the suite instead of
    failing one line hides which check broke. Found by an A/B probe that
    removed one of the two needles and got a traceback where it wanted a red
    line."""
    i, j = src.find(first), src.find(second)
    return i != -1 and j != -1 and i < j


def build(sheet, owner="Player 2", **kw):
    return tk.build(sheet, owner, **kw)


# --- 1. The registry ------------------------------------------------------
print("\n1. The registry")

# SCOPED TO T'AU, and that scoping is the point. These lines used to read the
# WHOLE registry, which was the same set while every Enhancement in it was a
# T'au one - a proxy that stopped being true the moment the 28 Aeldari ones
# arrived. They now say what they always meant, and the Aeldari suite counts
# its own.
TAU_SPECS = {name: spec for name, spec in E.ENHANCEMENTS.items()
             if spec.detachment in {d.name for d in TAU_EMPIRE.detachments.values()}}
c.eq("nineteen T'au Enhancements are engine-wired", len(TAU_SPECS), 19)
# Counted per detachment, so a twentieth cannot appear without this line
# moving - the same guard the T'au stratagem suite uses.
c.eq("Retaliation Cadre has four", len(E.for_detachment("Retaliation Cadre")), 4)
c.eq("Kauyon has four", len(E.for_detachment("Kauyon")), 4)
c.eq("Mont'ka has four", len(E.for_detachment("Mont'ka")), 4)
c.eq("Experimental Prototype Cadre has three",
     len(E.for_detachment("Experimental Prototype Cadre")), 3)
c.eq("Advanced Acquisition Cadre has two",
     len(E.for_detachment("Advanced Acquisition Cadre")), 2)
c.eq("Auxiliary Cadre has two", len(E.for_detachment("Auxiliary Cadre")), 2)
c.true("Kroot Hunting Pack is deliberately absent - it was excluded by the user",
       not E.for_detachment("Kroot Hunting Pack"))

# Every flag really exists on UnitProfile: a registry entry naming a field
# nothing declares would raise on the first getattr rather than reading False.
from game.units import UnitProfile  # noqa: E402
c.true("every registered flag is declared on UnitProfile",
       all(hasattr(UnitProfile, spec.flag) for spec in E.ENHANCEMENTS.values()))
c.true("...and every one of them defaults to False",
       all(getattr(UnitProfile, spec.flag) is False for spec in E.ENHANCEMENTS.values()))
# The flag check stays over the WHOLE registry - "no entry names a field nobody
# declares" is a property of the registry, not of one faction. The COUNT is the
# part that is per faction.
c.eq("nineteen DISTINCT T'au flags - no two share one",
     len({spec.flag for spec in TAU_SPECS.values()}), 19)
c.eq("...and no two Enhancements share a flag ACROSS factions either",
     len({spec.flag for spec in E.ENHANCEMENTS.values()}), len(E.ENHANCEMENTS))

# Points and detachment agree with the descriptive faction record. Pinned
# against each other rather than against literals, which is the assurance that
# matters: the two must not drift.
_recorded = {}
for _detachment in TAU_EMPIRE.detachments.values():
    for _e in _detachment.enhancements:
        _recorded[_e.name] = (_e.points, _detachment.name)
_mismatch = [name for name, spec in TAU_SPECS.items()
             if _recorded.get(name) != (spec.points, spec.detachment)]
c.eq("points and detachment match game/factions/tau_empire.py's own record",
     _mismatch, [])

# --- grant() --------------------------------------------------------------
coldstar = build(COMMANDER_IN_COLDSTAR_BATTLESUIT, name="Coldstar")
c.eq("granting sets the flag on the bearer's own profile instance",
     E.grant(coldstar, "Starflare Ignition System").profile.starflare_ignition_system, True)
c.true("...and only on that model", not any(
    m.profile.starflare_ignition_system for m in coldstar.models[1:]))

# Points land on Squad.points.
_points_before = build(COMMANDER_IN_COLDSTAR_BATTLESUIT, name="C2")
_p0 = _points_before.points
E.grant(_points_before, "Internal Grenade Racks")
c.eq("the Enhancement's points land on the unit", _points_before.points - _p0, 20)

# "None is contagious": an unpriced unit must not gain an invented total.
_unpriced = build(COMMANDER_IN_COLDSTAR_BATTLESUIT, name="C3")
_unpriced.points = None
E.grant(_unpriced, "Prototype Weapon System")
c.eq("an unpriced unit stays unpriced", _unpriced.points, None)


def refused(fn):
    try:
        fn()
    except ValueError as exc:
        return str(exc)
    return None


c.true("a second copy of the same Enhancement is refused",
       refused(lambda: E.grant(coldstar, "Starflare Ignition System")) is not None)
_strike = build(STRIKE_TEAM, name="Strike")
c.true("a bearer that fails the printed restriction is refused LOUDLY",
       refused(lambda: E.grant(_strike, "Starflare Ignition System")) is not None)
# Ambiguity is refused rather than guessed at - which model carries a 20-point
# upgrade is not something to pick arbitrarily.
_twin = build(TAU_EMPIRE.datasheets["The Twin Lance"], name="Twins")
c.eq("two eligible models means the bearer must be named",
     "name the bearer explicitly" in (refused(
         lambda: E.grant(_twin, "Internal Grenade Racks")) or ""), True)
c.true("...and naming one works",
       E.grant(_twin, "Internal Grenade Racks", model=_twin.models[0]) is _twin.models[0])

# The 19.04 reading: a dead bearer means the unit no longer has it, and a model
# killed this frame is STILL in Squad.models (remove_dead_models() runs once a
# frame). That is the bug game/starflare_ignition.py was fixed for.
_dead = build(COMMANDER_IN_COLDSTAR_BATTLESUIT, name="C4")
E.grant(_dead, "Starflare Ignition System")
with only("RETALIATION_CADRE_PLAYERS"):
    c.true("a live bearer has it", E.has(_dead, "Starflare Ignition System"))
    _dead.models[0].current_wounds = 0
    c.true("a bearer killed this frame no longer has it - it is still in models",
           not E.has(_dead, "Starflare Ignition System"))
    c.true("...but it is still the unit the rule is ABOUT, for reporting",
           bool(E.enhancement_models(_dead, "Starflare Ignition System")))

# Unit-level: the two Advanced Acquisition Cadre ones are given to a UNIT.
_stealth = build(STEALTH_BATTLESUITS, name="Stealth")
E.grant(_stealth, "Negation Emitters")
c.true("a unit-level Enhancement marks every model of the unit",
       all(m.profile.negation_emitters for m in _stealth.models))
c.true("a unit the printed text does not name is refused",
       refused(lambda: E.grant(build(STRIKE_TEAM, name="S2"), "Negation Emitters")) is not None)
c.true("the Pathfinder Team is a legal Unmasking Suite unit",
       refused(lambda: E.grant(build(PATHFINDER_TEAM, name="P"), "Unmasking Suite")) is None)
c.true("...and the Ghostkeel too",
       refused(lambda: E.grant(build(GHOSTKEEL_BATTLESUIT, name="G"), "Unmasking Suite")) is None)
c.true("...but Negation Emitters is STEALTH BATTLESUITS only, narrower than that",
       refused(lambda: E.grant(build(PATHFINDER_TEAM, name="P2"),
                               "Negation Emitters")) is not None)

# The two bearer lines that EXCLUDE something, each measured on the model the
# exclusion is about.
_shaper = build(KROOT_FLESH_SHAPER, name="Shaper")
c.true("a KROOT SHAPER may not take Exemplar of the Kauyon",
       refused(lambda: E.grant(_shaper, "Exemplar of the Kauyon")) is not None)
c.true("...nor Admired Leader, which excludes KROOT models",
       refused(lambda: E.grant(build(KROOT_FLESH_SHAPER, name="S3"),
                               "Admired Leader")) is not None)
c.true("...but Student of Kauyon is KROOT SHAPER ONLY, so he is its bearer",
       refused(lambda: E.grant(build(KROOT_FLESH_SHAPER, name="S4"),
                               "Student of Kauyon")) is None)
c.true("a non-Kroot T'au character may not take Student of Kauyon",
       refused(lambda: E.grant(build(CADRE_FIREBLADE, name="F"),
                               "Student of Kauyon")) is not None)
c.true("...and he IS a legal Admired Leader bearer",
       refused(lambda: E.grant(build(CADRE_FIREBLADE, name="F2"),
                               "Admired Leader")) is None)
# The three Experimental Prototype ones print BATTLESUIT without CHARACTER -
# kept as printed, so a non-character battlesuit is a legal bearer.
_starscythes = build(CRISIS_STARSCYTHE, name="Scythes")
c.true("a non-CHARACTER BATTLESUIT may bear a prototype weapon Enhancement",
       refused(lambda: E.grant(_starscythes, "Thermoneutronic Projector",
                               model=_starscythes.models[0])) is None)


# --- 2. The detachment gate ----------------------------------------------
print("\n2. The detachment gate")

_gated = build(COMMANDER_IN_COLDSTAR_BATTLESUIT, name="Gate")
E.grant(_gated, "Exemplar of the Kauyon")
with only("KAUYON_PLAYERS"):
    c.true("an Enhancement is live for a player who fields its detachment",
           E.is_active(_gated, "Exemplar of the Kauyon"))
with only("MONTKA_PLAYERS"):
    c.true("...and inert for a player fielding a DIFFERENT T'au detachment",
           not E.is_active(_gated, "Exemplar of the Kauyon"))
with none_fielded():
    c.true("...and inert for a player fielding none",
           not E.is_active(_gated, "Exemplar of the Kauyon"))
    c.true("has() still sees the bearer - only is_active() gates",
           E.has(_gated, "Exemplar of the Kauyon"))
with only("KAUYON_PLAYERS", players=("Player 1",)):
    c.true("the gate is per PLAYER, not per army",
           not E.is_active(_gated, "Exemplar of the Kauyon"))

# The same question asked of a MODEL, which is what the per-model rules use.
with only("KAUYON_PLAYERS"):
    c.true("model_is_active() agrees for the bearer",
           E.model_is_active(_gated.models[0], "Exemplar of the Kauyon"))
    c.true("...and is False for a model without the Enhancement",
           not E.model_is_active(_starscythes.models[1], "Exemplar of the Kauyon"))


# --- 3. Retaliation Cadre -------------------------------------------------
print("\n3. Retaliation Cadre")

from game import enh_internal_grenade_racks as IGR  # noqa: E402
from game import enh_prototype_weapon_system as PWS  # noqa: E402
from game import enh_puretide_neurochip as PEN  # noqa: E402
from game import wraith_form  # noqa: E402

# --- Internal Grenade Racks ---
igr = build(COMMANDER_IN_COLDSTAR_BATTLESUIT, name="IGR", owner="Player 2")
E.grant(igr, "Internal Grenade Racks")
enemy = build(STRIKE_TEAM, owner="Player 1", name="Prey")
tk.line_up(igr, x=10.0, y=10.0)
tk.line_up(enemy, x=10.0, y=14.0)
from game.game_state import GameState  # noqa: E402
_state = GameState()
for _s in (igr, enemy):
    for _m in _s.models:
        _state.add_token(_m)

with only("RETALIATION_CADRE_PLAYERS"):
    c.true("the bearer has the GRENADES keyword (rule 15.05)",
           IGR.has_grenades_keyword(igr.models[0]))
    c.true("...and a model without the Enhancement does not",
           not IGR.has_grenades_keyword(enemy.models[0]))
with none_fielded():
    c.true("the granted keyword is gated on the detachment too",
           not IGR.has_grenades_keyword(igr.models[0]))

# "Moved over": the bearer's own path, not its unit's.
_starts = {igr.models[0].id: (10.0, 18.0)}   # walked north to south, over the Strike Team
with only("RETALIATION_CADRE_PLAYERS"):
    _over = IGR.units_moved_over(igr.models[0], _starts, _state.tokens)
    c.eq("an enemy unit the bearer walked over is a candidate",
         [s.name for s in _over], ["Prey"])
    # A sideways march along y=10, four inches clear of a line of enemies at
    # y=14 - chosen rather than "somewhere else", because a diagonal from the
    # far corner clips the line on its way in, which is exactly the kind of
    # accidental hit this geometry is supposed to report.
    _aside = {igr.models[0].id: (40.0, 10.0)}
    c.eq("...and one it walked nowhere near is not",
         IGR.units_moved_over(igr.models[0], _aside, _state.tokens), [])
    c.true("the geometry is game/wraith_form.py's, not a second copy",
           "wraith_form.units_moved_over" in
           io.open("game/enh_internal_grenade_racks.py", encoding="utf-8").read())

# End to end through the controller: six D6, 4+ each a mortal wound.
_dice = SpyDice()
_log = tk.Log()


class _Mover:
    last_move_start = _starts


with only("RETALIATION_CADRE_PLAYERS"):
    ctrl = IGR.InternalGrenadeRacksController(
        dice_manager=_dice, decision_manager=None, game_log=_log, game_state=_state,
        movement_controller=_Mover(), auto_players=("Player 2",))
    c.true("a Normal move that passed over an enemy offers it",
           ctrl.on_move_finished(igr, "normal"))
    # Against the LITERALS the rule prints, not against the module's own
    # constants. Written the other way round this was a tautology: an A/B probe
    # that changed GRENADE_RACK_DICE to 3 moved both sides of the comparison and
    # the suite stayed green - a finding about the test, which is what an
    # unbroken probe always is.
    c.eq("six D6 are rolled", _dice.last["count"], 6)
    c.eq("...on a 4+", _dice.last["success_threshold"], 4)
    c.eq("the constants say the same", (IGR.GRENADE_RACK_DICE, IGR.MORTAL_WOUND_THRESHOLD),
         (6, 4))
    # Six FLAT, which is what separates it from Wraith Form's one-per-model.
    c.true("six is a flat count, not this unit's model count",
           IGR.GRENADE_RACK_DICE != len(igr.models))
    _dice.last_values = [4, 4, 4, 1, 1, 1]
    ctrl.on_dice_acknowledged()
    c.true("three 4+ inflict three mortal wounds", _log.has("3 mortal wound"))

# An ADVANCE does not trigger it - "a Normal move" is printed.
with only("RETALIATION_CADRE_PLAYERS"):
    ctrl2 = IGR.InternalGrenadeRacksController(
        dice_manager=SpyDice(), game_log=tk.Log(), game_state=_state,
        movement_controller=_Mover(), auto_players=("Player 2",))
    c.true("an Advance does not trigger it", not ctrl2.on_move_finished(igr, "advance"))
c.eq("the move kind is shared with Wraith Form's, not restated",
     IGR.GRENADE_RACK_MOVE_KIND, wraith_form.WRAITH_FORM_MOVE_KIND)

# PER MODEL, where Wraith Form is per unit: a bodyguard's path must not find a
# target the bearer never approached.
_solo = build(COMMANDER_IN_COLDSTAR_BATTLESUIT, name="Solo", owner="Player 2")
E.grant(_solo, "Internal Grenade Racks")
_body = build(CRISIS_STARSCYTHE, name="Body", owner="Player 2")
from game import attached_units  # noqa: E402
_merged = attached_units.attach(_solo, _body)
tk.line_up(_merged, x=30.0, y=30.0)
_far_enemy = build(STRIKE_TEAM, owner="Player 1", name="Far")
tk.line_up(_far_enemy, x=34.0, y=34.0)
_state2 = GameState()
for _s in (_merged, _far_enemy):
    for _m in _s.models:
        _state2.add_token(_m)
_bearer = E.enhancement_models(_merged, "Internal Grenade Racks")[0]
_other = [m for m in _merged.models if m is not _bearer][0]
# Only the OTHER model's path crosses the enemy.
_mixed = {_other.id: (34.0, 40.0)}
with only("RETALIATION_CADRE_PLAYERS"):
    c.eq("only the BEARER's path counts, not a bodyguard's",
         IGR.units_moved_over(_bearer, _mixed, _state2.tokens), [])

# --- Prototype Weapon System ---
pws = build(COMMANDER_IN_COLDSTAR_BATTLESUIT, name="PWS", owner="Player 2")
E.grant(pws, "Prototype Weapon System")
_dec = None
with only("RETALIATION_CADRE_PLAYERS"):
    pws_ctrl = PWS.PrototypeWeaponSystemController(
        decision_manager=None, game_log=tk.Log(), auto_players=("Player 2",))
    c.true("the bearer is offered a choice when selected to shoot",
           pws_ctrl.begin_activation(pws))
    _chosen = PWS.choice_for(pws.models[0])
    c.true("a choice was recorded", _chosen in (PWS.LETHAL_HITS, PWS.SUSTAINED_HITS))
    _weapon = [w for w in pws.models[0].weapons if w.weapon_type == "ranged"][0]
    _adj = PWS.adjusted_weapon(_weapon, pws.models[0])
    c.true("the chosen keyword really lands on the weapon",
           _adj.lethal_hits or _adj.sustained_hits >= 1)
    c.true("...on a COPY - the shared profile instance is never mutated",
           _adj is not _weapon)
    pws_ctrl.end_activation(pws)
    c.eq("the grant ends with the activation", PWS.choice_for(pws.models[0]), None)

# The choice is the BEARER's weapons only.
with only("RETALIATION_CADRE_PLAYERS"):
    _merged2 = attached_units.attach(
        build(COMMANDER_IN_COLDSTAR_BATTLESUIT, name="PWS2", owner="Player 2"),
        build(CRISIS_STARSCYTHE, name="Guard", owner="Player 2"))
    E.grant(_merged2, "Prototype Weapon System",
            model=[m for m in _merged2.models if m.profile.character][0])
    pws_ctrl2 = PWS.PrototypeWeaponSystemController(auto_players=("Player 2",),
                                                    game_log=tk.Log())
    pws_ctrl2.begin_activation(_merged2)
    _bearer2 = E.enhancement_models(_merged2, "Prototype Weapon System")[0]
    _guard = [m for m in _merged2.models if m is not _bearer2][0]
    c.true("the bearer has a choice", PWS.choice_for(_bearer2) is not None)
    c.eq("a bodyguard does not", PWS.choice_for(_guard), None)
    _gw = [w for w in _guard.weapons if w.weapon_type == "ranged"][0]
    c.true("...so its weapon is returned untouched",
           PWS.adjusted_weapon(_gw, _guard) is _gw)

# The grant is part of _attack_key(), which is what makes the one-representative
# read exact. Without it a bodyguard sharing the bearer's BS/S/AP/D would
# inherit or lose the keyword.
_shooting_src = io.open("game/shooting.py", encoding="utf-8").read()
c.true("Prototype Weapon System is part of _attack_key()",
       "enh_prototype_weapon_system.attack_key(model)" in _shooting_src)

# --- Puretide Engram Neurochip ---
from game.command_points import CommandPointManager  # noqa: E402
from game.stratagems import Stratagem, StratagemController  # noqa: E402

pen = build(COMMANDER_IN_COLDSTAR_BATTLESUIT, name="PEN", owner="Player 2")
E.grant(pen, "Puretide Engram Neurochip")
with only("RETALIATION_CADRE_PLAYERS"):
    _cp = CommandPointManager(game_log=tk.Log())
    _cp.cp["Player 2"] = 5
    _pen_dice = SpyDice()
    pen_ctrl = PEN.PuretideNeurochipController(
        dice_manager=_pen_dice, command_points=_cp, turn_tracker=tk._tracker("Command"),
        game_log=tk.Log())
    _strat = Stratagem(name="Some Stratagem", cp_cost=1, effect=lambda *a: None)
    c.true("targeting the bearer's unit rolls a D6",
           pen_ctrl.on_targets_chosen("Player 2", _strat, [pen]))
    c.eq("one die", _pen_dice.last["count"], 1)
    c.eq("...on a 4+", _pen_dice.last["success_threshold"], PEN.NEUROCHIP_THRESHOLD)
    _before = _cp.cp["Player 2"]
    _pen_dice.last_values = [5]
    pen_ctrl.on_dice_acknowledged()
    c.eq("a 4+ gains 1 CP", _cp.cp["Player 2"] - _before, PEN.NEUROCHIP_CP)

with only("RETALIATION_CADRE_PLAYERS"):
    _cp2 = CommandPointManager(game_log=tk.Log())
    _cp2.cp["Player 2"] = 5
    pen_ctrl2 = PEN.PuretideNeurochipController(
        dice_manager=SpyDice(), command_points=_cp2,
        turn_tracker=tk._tracker("Command"), game_log=tk.Log())
    c.true("targeting somebody ELSE's unit does not",
           not pen_ctrl2.on_targets_chosen("Player 2", _strat, [enemy]))
    c.true("nor does targeting a friendly unit without the Enhancement",
           not pen_ctrl2.on_targets_chosen("Player 2", _strat, [_starscythes]))

# Never rolls a die that could not pay - the cap is CommandPointManager's, and
# is read rather than re-implemented.
with only("RETALIATION_CADRE_PLAYERS"):
    _cp3 = CommandPointManager(game_log=tk.Log())
    _cp3.cp["Player 2"] = 5
    _cp3.gain_cp("Player 2", 1, 1, reason="something else")   # spends the round's headroom
    pen_ctrl3 = PEN.PuretideNeurochipController(
        dice_manager=SpyDice(), command_points=_cp3,
        turn_tracker=tk._tracker("Command"), game_log=tk.Log())
    c.true("with the round's bonus-CP cap already reached, it does not roll",
           not pen_ctrl3.on_targets_chosen("Player 2", _strat, [pen]))

# StratagemController really calls the listener, with the targets.
_seen = []
_sc = StratagemController(game_log=tk.Log(), command_points=CommandPointManager())
_sc.command_points.cp["Player 2"] = 5
_sc.on_targets_chosen.append(lambda p, s, t: _seen.append((p, s.name, list(t))))
_sc.use("Player 2", _strat, [pen])
c.eq("StratagemController notifies its listeners with the targets",
     [(p, n, [x.name for x in t]) for p, n, t in _seen],
     [("Player 2", "Some Stratagem", ["PEN"])])

# Named after its own effect, not after Farsight's similarly-named ability.
c.true("it is a different module from Commander Farsight's Puretide's Teachings",
       "puretide_engram_neurochip" != "puretide_teachings"
       and "PURETIDE_DISCOUNT_CP" not in
       io.open("game/enh_puretide_neurochip.py", encoding="utf-8").read())


# --- 4. Kauyon ------------------------------------------------------------
print("\n4. Kauyon")

from game import enh_exemplars, enh_guided_keyword_grants as GKG  # noqa: E402
from game import enh_precision_patient_hunter as PPH  # noqa: E402
from game import enh_solid_image_projection as SIP  # noqa: E402
from game import pregame  # noqa: E402
from game import kauyon, montka, tau_detachments  # noqa: E402


class _Round:
    def __init__(self, n):
        self.battle_round = n


# --- Exemplar of the Kauyon: the detachment rule starts a round earlier ---
_ex_leader = build(COMMANDER_IN_COLDSTAR_BATTLESUIT, name="Exemplar", owner="Player 2")
_ex_unit = attached_units.attach(_ex_leader, build(CRISIS_STARSCYTHE, name="Led",
                                                   owner="Player 2"))
E.grant(_ex_unit, "Exemplar of the Kauyon",
        model=[m for m in _ex_unit.models if m.profile.character][0])
_plain = build(CRISIS_STARSCYTHE, name="Plain", owner="Player 2")

with only("KAUYON_PLAYERS"):
    c.true("Patient Hunter normally starts in round 3",
           not kauyon.is_active(_plain, _Round(2)) and kauyon.is_active(_plain, _Round(3)))
    c.true("the Exemplar's unit gets it in round 2",
           kauyon.is_active(_ex_unit, _Round(2)))
    c.true("...and still has it in rounds 3-5", kauyon.is_active(_ex_unit, _Round(5)))
    c.true("...but not in round 1 - it is 'from the second onwards'",
           not kauyon.is_active(_ex_unit, _Round(1)))
    c.true("a unit the bearer does not lead is unaffected",
           not kauyon.is_active(_plain, _Round(2)))

# A bearer standing ALONE leads nothing, so the Enhancement does nothing.
_alone = build(COMMANDER_IN_COLDSTAR_BATTLESUIT, name="Alone", owner="Player 2")
E.grant(_alone, "Exemplar of the Kauyon")
with only("KAUYON_PLAYERS"):
    c.true("a bearer leading no unit widens nothing",
           not kauyon.is_active(_alone, _Round(2)))

# It widens KAUYON's window and not Mont'ka's.
with only("MONTKA_PLAYERS"):
    c.true("a Kauyon Enhancement does not widen the Mont'ka window",
           not montka.is_active(_ex_unit, _Round(4)))

# --- Precision of the Patient Hunter ---
_pph = build(COMMANDER_IN_COLDSTAR_BATTLESUIT, name="Precision", owner="Player 2")
E.grant(_pph, "Precision of the Patient Hunter")
with only("KAUYON_PLAYERS"):
    c.eq("the bearer gets +1 to the Hit roll (a -1 on the threshold)",
         [m.amount for m in PPH.hit_modifiers(_pph.models[0])], [-1])
    c.eq("a model without it gets nothing",
         PPH.hit_modifiers(_starscythes.models[0]), [])
    c.eq("no Wound bonus before round 3",
         PPH.wound_modifiers(_pph.models[0], _Round(2)), [])
    c.eq("...and +1 from round 3 onwards",
         [m.amount for m in PPH.wound_modifiers(_pph.models[0], _Round(3))], [-1])
    c.eq("...still there in round 5",
         len(PPH.wound_modifiers(_pph.models[0], _Round(5))), 1)
    # NOT the same condition as Exemplar of the Kauyon: this one is a flat
    # "from the third battle round", so an Exemplar-led unit does not get its
    # Wound bonus a round early.
    c.eq("the round-3 clause is flat - Exemplar of the Kauyon does not move it",
         PPH.wound_modifiers(_pph.models[0], _Round(2)), [])
c.eq("it is part of _attack_key(), so the group's representative is exact",
     "enh_precision_patient_hunter.hit_bonus(model)" in _shooting_src, True)
with only("KAUYON_PLAYERS"):
    c.eq("hit_bonus() is 1 for the bearer", PPH.hit_bonus(_pph.models[0]), 1)
    c.eq("...and 0 for everyone else, so no existing group splits",
         PPH.hit_bonus(_starscythes.models[0]), 0)

# --- Through Unity, Devastation ---
class _FakeGreaterGood:
    """Just enough of GreaterGoodController for the two Observer Enhancements:
    which units acted as Observers this phase, and whether an attack is Guided."""

    def __init__(self, observers=(), guided=()):
        self.observer_squad_ids = set(observers)
        self._guided = set(guided)

    def is_guided_attack(self, attacker, target):
        return (attacker, target) in self._guided


_obs_leader = build(COMMANDER_IN_COLDSTAR_BATTLESUIT, name="Obs", owner="Player 2")
_obs_unit = attached_units.attach(_obs_leader, build(CRISIS_STARSCYTHE, name="ObsGuard",
                                                     owner="Player 2"))
E.grant(_obs_unit, "Through Unity, Devastation",
        model=[m for m in _obs_unit.models if m.profile.character][0])
_shooter = build(STRIKE_TEAM, name="Shooter", owner="Player 2")
_spotted = build(STRIKE_TEAM, name="Spotted", owner="Player 1")
_gg = _FakeGreaterGood(observers=[_obs_unit], guided=[(_shooter, _spotted)])

with only("KAUYON_PLAYERS"):
    c.true("once the bearer's unit has spotted, every Guided attack gets [LETHAL HITS]",
           GKG.lethal_hits_applies(_shooter, _spotted, _gg))
    c.true("an attack that is NOT Guided gets nothing",
           not GKG.lethal_hits_applies(_shooter, _obs_unit, _gg))
    c.true("...and so does everything, before the bearer's unit is an Observer",
           not GKG.lethal_hits_applies(
               _shooter, _spotted, _FakeGreaterGood(guided=[(_shooter, _spotted)])))
    _w = [w for w in _shooter.models[0].weapons if w.weapon_type == "ranged"][0]
    _adj = GKG.adjusted_weapon(_w, _shooter, _spotted, _gg)
    c.true("the keyword lands on a COPY of the weapon",
           _adj.lethal_hits and _adj is not _w)
    c.true("Coordinated Exploitation is Mont'ka's and does not fire here",
           not GKG.sustained_hits_applies(_shooter, _spotted, _gg))

# The bearer must be LEADING - a lone Observer with the Enhancement grants
# nothing, because the printed text says "while the bearer is leading a unit".
_lone_obs = build(COMMANDER_IN_COLDSTAR_BATTLESUIT, name="LoneObs", owner="Player 2")
E.grant(_lone_obs, "Through Unity, Devastation")
with only("KAUYON_PLAYERS"):
    c.true("a lone bearer acting as Observer grants nothing",
           not GKG.lethal_hits_applies(
               _shooter, _spotted,
               _FakeGreaterGood(observers=[_lone_obs], guided=[(_shooter, _spotted)])))

# --- Solid-image Projection Unit ---
c.eq("it is offered after deployment, not in the pre-battle step",
     "redeploy_step" in io.open("game/pregame.py", encoding="utf-8").read(), True)
_pregame_src = io.open("game/pregame.py", encoding="utf-8").read()
c.true("the redeploy hook runs inside _finish_deployment()",
       "if self.redeploy_step is not None and not self._redeploy_done:" in _pregame_src)
c.true("...and BEFORE the first-turn roll-off, which is what the printed timing says",
       before(_pregame_src, "self.redeploy_step.start(self, resume)",
              "if SCOUTS_BEFORE_FIRST_TURN_ROLLOFF:"))
# The hand-off is one-shot AND its result is read. A step may resume the
# sequence by calling the continuation and still answer "nothing to do" (four
# shipped ones do), and without the second test this hook starts a SECOND
# first-turn roll-off - which then starts the battle a second time and pays a
# second Command phase of Primary VP. See game/pregame.py's Resume.
c.true("...and the hand-off cannot run the rest of the sequence twice",
       "resume = Resume(self._deployment_finished)" in _pregame_src
       and "or resume.fired" in _pregame_src)
# Measured rather than pinned on the prose: an owner that answers its own
# prompts declines outright, so the step hands straight back and the pre-game
# carries on. See the module docstring for why there is deliberately no
# redeployment heuristic here.
_sip_state = GameState()
_sip_bearer = build(COMMANDER_IN_COLDSTAR_BATTLESUIT, name="SIP", owner="Player 2")
E.grant(_sip_bearer, "Solid-image Projection Unit")
tk.line_up(_sip_bearer, x=10.0, y=10.0)
for _m in _sip_bearer.models:
    _sip_state.add_token(_m)


class _FakePregame:
    def _owners(self):
        return ["Player 2"]


with only("KAUYON_PLAYERS"):
    _resumed = []
    sip = SIP.SolidImageProjectionStep(game_state=_sip_state, decision_manager=None,
                                       game_log=tk.Log(), auto_players=("Player 2",))
    c.true("an owner that answers its own prompts does not take the step over",
           not sip.start(_FakePregame(), on_done=lambda: _resumed.append(True)))
    c.eq("...and nothing is redeployed", sip.chosen, {})
    c.true("the bearer IS recognised, so this is a decline and not a miss",
           bool(sip.bearer_units("Player 2")))

# The redeploy branch itself, end to end - the riskiest path here, because it
# hands the pre-game back into DEPLOYING and a mistake there is a second
# first-turn roll-off rather than a wrong number.
_sip2 = GameState()
_sip_b = build(COMMANDER_IN_COLDSTAR_BATTLESUIT, name="Bearer2", owner="Player 2")
E.grant(_sip_b, "Solid-image Projection Unit")
tk.line_up(_sip_b, x=10.0, y=10.0)
_victim = build(STRIKE_TEAM, name="Victim", owner="Player 2")
tk.line_up(_victim, x=20.0, y=10.0, spacing=0.9)
_reserved = build(STRIKE_TEAM, name="Reserved", owner="Player 2")
tk.line_up(_reserved, x=30.0, y=10.0, spacing=0.9)
for _s in (_sip_b, _victim, _reserved):
    for _m in _s.models:
        _sip2.add_token(_m)


class _RedeployPregame:
    state = pregame.DONE
    active_player = "Player 2"

    def __init__(self):
        self._pending = {}

    def _owners(self):
        return ["Player 2"]

    def _sync_turn_tracker(self):
        pass


with only("KAUYON_PLAYERS"):
    _pg = _RedeployPregame()
    _resumed = []
    step2 = SIP.SolidImageProjectionStep(game_state=_sip2, decision_manager=None,
                                         game_log=tk.Log(), auto_players=())
    step2._pregame = _pg
    step2._on_done = lambda: _resumed.append(True)
    step2._pending_players = []
    # The two answers a human can give, together.
    step2.chosen = {"Player 2": [(_victim, SIP.REDEPLOY), (_reserved, SIP.RESERVES)]}
    c.true("applying the answers takes the sequence over", step2._apply())
    c.eq("the redeployed unit is back in the deployment queue",
         [s.name for s in _pg._pending["Player 2"]], ["Victim"])
    c.eq("...and off the board while it waits to be placed again",
         any(m in _sip2.tokens for m in _victim.models), False)
    c.eq("the controller is back in DEPLOYING", _pg.state, pregame.DEPLOYING)
    c.eq("the reserves branch really reserves", _reserved in _sip2.reserves, True)
    c.eq("...and takes it off the board too",
         any(m in _sip2.tokens for m in _reserved.models), False)
    c.true("the bearer itself is untouched",
           all(m in _sip2.tokens for m in _sip_b.models))
    # on_done is NOT called on this branch: placing the unit reaches
    # _finish_deployment() again on its own, and calling it here as well is
    # exactly how a second first-turn roll-off happens.
    c.eq("the caller is NOT resumed - the deployment flow will reach it", _resumed, [])

# TWO STEPS, so the unit is chosen on the BOARD. It used to be one prompt
# listing every unit TWICE (once per destination), which game/unit_pick.py
# rightly refuses - a click says "this unit" and cannot pick between two
# fates. Reported: "Solid Image Projection Unit - ich will die Einheit auf dem
# Schlachtfeld waehlen, nicht aus einer Liste".
from game import unit_pick as _up  # noqa: E402
from game.decision import DecisionManager  # noqa: E402

_sip3 = GameState()
_sip_b3 = build(COMMANDER_IN_COLDSTAR_BATTLESUIT, name="Bearer3", owner="Player 2")
E.grant(_sip_b3, "Solid-image Projection Unit")
tk.line_up(_sip_b3, x=10.0, y=10.0)
_v3 = build(STRIKE_TEAM, name="Victim3", owner="Player 2")
tk.line_up(_v3, x=20.0, y=10.0, spacing=0.9)
for _s in (_sip_b3, _v3):
    for _m in _s.models:
        _sip3.add_token(_m)

with only("KAUYON_PLAYERS"):
    _dec3 = DecisionManager()
    step3 = SIP.SolidImageProjectionStep(game_state=_sip3, decision_manager=_dec3,
                                         game_log=tk.Log(), auto_players=())
    step3._pregame = _RedeployPregame()
    c.true("step one opens a prompt", step3._offer("Player 2"))
    _labels3 = [o["label"] for o in _dec3.options]
    c.eq("...naming every eligible unit exactly ONCE",
         sorted(l for l in _labels3 if l != "No more"), ["Bearer3", "Victim3"])
    c.true("...tagged with their squads, so it is answerable on the board",
           all(o["squad"] is not None for o in _dec3.options if o["label"] != "No more"))
    _pick3 = _up.pending(_dec3, _sip3.tokens)
    c.true("game/unit_pick.py accepts it as a board pick", _pick3 is not None)
    c.eq("...offering exactly the eligible units",
         sorted(s.name for s in _pick3.squads), ["Bearer3", "Victim3"])

    # Step two: the fate, as an ordinary list - the two destinations are not units.
    c.true("clicking the unit opens the destination question",
           _pick3.pick(_v3) and _dec3.is_pending)
    c.eq("...with both printed outcomes",
         [o["label"] for o in _dec3.options],
         ["Set up again elsewhere", "Into Strategic Reserves"])
    c.true("...and they are NOT tagged - an objective/fate is not a unit",
           all(o["squad"] is None for o in _dec3.options))
    _dec3.choose(1)
    c.eq("choosing Strategic Reserves records that fate",
         [(sq.name, dest) for sq, dest in step3.chosen["Player 2"] if sq is not None],
         [("Victim3", SIP.RESERVES)])


# --- 5. Mont'ka -----------------------------------------------------------
print("\n5. Mont'ka")

from game import enh_strategic_conqueror as SCQ  # noqa: E402
from game import enh_strike_swiftly as SWIFT  # noqa: E402
from game import scouts  # noqa: E402

# --- Exemplar of the Mont'ka ---
_mk_leader = build(COMMANDER_IN_COLDSTAR_BATTLESUIT, name="MkExemplar", owner="Player 2")
_mk_unit = attached_units.attach(_mk_leader, build(CRISIS_STARSCYTHE, name="MkLed",
                                                   owner="Player 2"))
E.grant(_mk_unit, "Exemplar of the Mont'ka",
        model=[m for m in _mk_unit.models if m.profile.character][0])
with only("MONTKA_PLAYERS"):
    c.true("Killing Blow normally stops after round 3",
           montka.is_active(_plain, _Round(3)) and not montka.is_active(_plain, _Round(4)))
    c.true("the Exemplar's unit keeps it in round 4", montka.is_active(_mk_unit, _Round(4)))
    c.true("...but not in round 5 - it is 'the fourth as well', not 'onwards'",
           not montka.is_active(_mk_unit, _Round(5)))
    c.true("...and it still has rounds 1-3", montka.is_active(_mk_unit, _Round(1)))

    # AND THE WIDENING SURVIVES THE FLAG. Killing Blow's [ASSAULT] half reaches
    # rule 10.05 through Squad.montka_killing_blow, because
    # game/coldstar.py's weapon_has_assault() is handed only (weapon, squad)
    # and cannot ask a round question. That stamp has to be derived from the
    # same is_active() the checks above use: written against the printed
    # KILLING_BLOW_ROUNDS instead, it would drop this Enhancement's fourth
    # round at the Advance gate ONLY - the damage chain would still grant
    # [ASSAULT] in round 4 while the unit was refused permission to shoot after
    # Advancing, which is one rule with two readers disagreeing.
    montka.refresh_killing_blow([_mk_unit, _plain], _Round(4))
    c.true("the Exemplar's fourth round reaches the Advance gate too",
           montka.grants_assault(_mk_unit))
    c.true("...while a plain unit's window has already closed",
           not montka.grants_assault(_plain))
    montka.refresh_killing_blow([_mk_unit], _Round(5))
    c.true("...and round 5 closes it for the bearer as well",
           not montka.grants_assault(_mk_unit))

# --- Coordinated Exploitation ---
_ce_leader = build(COMMANDER_IN_COLDSTAR_BATTLESUIT, name="CE", owner="Player 2")
_ce_unit = attached_units.attach(_ce_leader, build(CRISIS_STARSCYTHE, name="CEGuard",
                                                   owner="Player 2"))
E.grant(_ce_unit, "Coordinated Exploitation",
        model=[m for m in _ce_unit.models if m.profile.character][0])
_ce_gg = _FakeGreaterGood(observers=[_ce_unit], guided=[(_shooter, _spotted)])
with only("MONTKA_PLAYERS"):
    c.true("Coordinated Exploitation grants [SUSTAINED HITS 1] to Guided attacks",
           GKG.sustained_hits_applies(_shooter, _spotted, _ce_gg))
    _w2 = [w for w in _shooter.models[0].weapons if w.weapon_type == "ranged"][0]
    _adj2 = GKG.adjusted_weapon(_w2, _shooter, _spotted, _ce_gg)
    c.eq("...to a value of 1", _adj2.sustained_hits, GKG.SUSTAINED_HITS_GRANTED)
    c.true("Through Unity is Kauyon's and does not fire here",
           not GKG.lethal_hits_applies(_shooter, _spotted, _ce_gg))


# NEVER DOWNGRADES: a weapon already printing a higher X keeps it.
class _Sustained2:
    weapon_type = "ranged"
    lethal_hits = False
    sustained_hits = 2
    sustained_hits_notation = None


with only("MONTKA_PLAYERS"):
    _high = _Sustained2()
    c.true("a weapon printing [SUSTAINED HITS 2] keeps its 2",
           GKG.adjusted_weapon(_high, _shooter, _spotted, _ce_gg) is _high)

# --- Strategic Conqueror ---
from game.objectives import Objective  # noqa: E402
from game.terrain import EXPOSED, Obstacle, TerrainArea  # noqa: E402
from game import objective_control  # noqa: E402


def _objective(name, x, y, size=6.0):
    return Objective(TerrainArea([Obstacle(x_in=x, y_in=y, width_in=size, height_in=size,
                                           category=EXPOSED)]), name=name)


_obj = _objective("Central Objective", 20.0, 20.0)
_other_obj = _objective("Objective East", 40.0, 40.0)

_scq_bearer = build(COMMANDER_IN_COLDSTAR_BATTLESUIT, name="SCQ", owner="Player 2")
E.grant(_scq_bearer, "Strategic Conqueror")
tk.line_up(_scq_bearer, x=50.0, y=50.0)     # far from the objective - "that friendly model"
_holder = build(STRIKE_TEAM, name="Holder", owner="Player 2")
tk.line_up(_holder, x=21.0, y=22.0, spacing=0.9)
_state3 = GameState()
for _s in (_scq_bearer, _holder):
    for _m in _s.models:
        _state3.add_token(_m)

with only("MONTKA_PLAYERS"):
    SCQ.clear([_obj, _other_obj])
    _model = _holder.models[0]
    _base = objective_control.effective_oc(_model, _state3.tokens, objective=_obj)
    SCQ.choose(_obj, "Player 2")
    c.eq("a friendly T'AU model in range of the named objective gets +1 OC",
         objective_control.effective_oc(_model, _state3.tokens, objective=_obj) - _base,
         SCQ.STRATEGIC_CONQUEROR_OC_BONUS)
    c.eq("...and nothing on a DIFFERENT objective",
         objective_control.effective_oc(_model, _state3.tokens, objective=_other_obj),
         _base)
    c.eq("...and nothing when no objective is being asked about",
         objective_control.effective_oc(_model, _state3.tokens), _base)
    # The bearer must be ON THE BATTLEFIELD - a live condition.
    for _m in _scq_bearer.models:
        _state3.tokens.remove(_m)
    c.eq("with the bearer off the battlefield the bonus is gone",
         objective_control.effective_oc(_model, _state3.tokens, objective=_obj), _base)
    for _m in _scq_bearer.models:
        _state3.tokens.append(_m)
    # The enemy gets nothing from someone else's mark.
    _enemy_holder = build(STRIKE_TEAM, name="EnemyHolder", owner="Player 1")
    tk.line_up(_enemy_holder, x=21.0, y=22.0, spacing=0.9)
    c.eq("an enemy model in range of the mark gets nothing",
         SCQ.oc_bonus(_enemy_holder.models[0], _obj, _state3.tokens), 0)
with none_fielded():
    c.eq("and the whole thing is gated on the detachment",
         SCQ.oc_bonus(_holder.models[0], _obj, _state3.tokens), 0)
SCQ.clear([_obj, _other_obj])

# --- Strike Swiftly ---
_swift_bearer = build(COMMANDER_IN_COLDSTAR_BATTLESUIT, name="Swift", owner="Player 2")
E.grant(_swift_bearer, "Strike Swiftly")
tk.line_up(_swift_bearer, x=10.0, y=10.0)
_near = build(STRIKE_TEAM, name="Near", owner="Player 2")
tk.line_up(_near, x=12.0, y=10.0, spacing=0.9)
_far = build(STRIKE_TEAM, name="FarAway", owner="Player 2")
tk.line_up(_far, x=40.0, y=40.0, spacing=0.9)
_state4 = GameState()
for _s in (_swift_bearer, _near, _far):
    for _m in _s.models:
        _state4.add_token(_m)

with only("MONTKA_PLAYERS"):
    step = SWIFT.StrikeSwiftlyStep(decision_manager=None, game_log=tk.Log(),
                                   auto_players=("Player 2",), game_state=_state4)
    _targets = step.eligible_targets(_swift_bearer)
    c.true("a friendly T'au unit within 6\" is eligible", _near in _targets)
    c.true("...and one 30 inches away is not", _far not in _targets)
    c.true("the Strike Team has no Scouts to start with", not scouts.has_scouts(_near))
    SWIFT.grant_scouts(_near)
    c.true("after the grant it does", scouts.has_scouts(_near))
    c.eq("...at exactly 6 inches", scouts.scout_distance(_near),
         SWIFT.GRANTED_SCOUT_DISTANCE_IN)
    c.true("a unit that already has Scouts is not offered it again",
           _near not in step.eligible_targets(_swift_bearer))

# The ORDER is the whole point: it must run before the Scouts step.
c.true("PregameController runs prebattle_steps before scouts_step",
       before(_pregame_src, "while self._prebattle_queue:", "self.scouts_step.start(self)"))
_main_src = io.open("main.py", encoding="utf-8").read()
c.true("main.py registers Strike Swiftly into that ordered list",
       "pregame_controller.prebattle_steps.append(StrikeSwiftlyStep(" in _main_src)


# --- 6. Experimental Prototype Cadre --------------------------------------
print("\n6. Experimental Prototype Cadre")

from game import enh_prototype_weapons as PROTO  # noqa: E402
from game.weapons import (AirburstingFragmentationProjectorProfile,  # noqa: E402
                          HighIntensityPlasmaRifleProfile, PlasmaRifleProfile,
                          TauFlamerProfile, TwinPlasmaRifleProfile, TwinTauFlamerProfile)

_fireknife = build(CRISIS_FIREKNIFE, name="Fireknife", owner="Player 2")
E.grant(_fireknife, "Plasma Accelerator Rifle", model=_fireknife.models[0])
_rifle = [w for w in _fireknife.models[0].weapons if type(w) is PlasmaRifleProfile][0]
_before = (_rifle.strength, _rifle.attacks, _rifle.ap, _rifle.damage)
with only("EXPERIMENTAL_PROTOTYPE_CADRE_PLAYERS"):
    _changed = PROTO.apply_to_squad(_fireknife, game_log=tk.Log())
    c.eq("one weapon is upgraded", len(_changed), 1)
    c.eq("+2 S", _rifle.strength - _before[0], 2)
    c.eq("+1 A", _rifle.attacks - _before[1], 1)
    c.eq("+1 AP means MORE negative", _rifle.ap - _before[2], -1)
    c.eq("+1 D", _rifle.damage - _before[3], 1)
    # Idempotent: a second Declare Battle Formations pass must not stack it.
    PROTO.apply_to_squad(_fireknife, game_log=tk.Log())
    c.eq("a second pass changes nothing", _rifle.strength - _before[0], 2)

# The three upgrades match by profile CLASS, and the twin/high-intensity
# variants are NOT subclasses of the three named - so the class reading and the
# name reading coincide today. Pinned, because a refactor that made one of them
# a subclass would silently widen all three Enhancements.
c.true("Twin T'au Flamer is not a T'au Flamer subclass",
       not issubclass(TwinTauFlamerProfile, TauFlamerProfile))
c.true("Twin Plasma Rifle is not a Plasma Rifle subclass",
       not issubclass(TwinPlasmaRifleProfile, PlasmaRifleProfile))
c.true("High-intensity Plasma Rifle is not either",
       not issubclass(HighIntensityPlasmaRifleProfile, PlasmaRifleProfile))
_farsight = build(COMMANDER_FARSIGHT, name="Farsight", owner="Player 2")
E.grant(_farsight, "Plasma Accelerator Rifle")
with only("EXPERIMENTAL_PROTOTYPE_CADRE_PLAYERS"):
    c.eq("so Farsight's High-intensity Plasma Rifle is NOT upgraded",
         PROTO.apply_to_squad(_farsight, game_log=tk.Log()), [])

# The Starscythes' T'au Flamer is the one this list would use - if the list
# kept any.
_flamers = build(CRISIS_STARSCYTHE, name="Flamers", owner="Player 2")
E.grant(_flamers, "Thermoneutronic Projector", model=_flamers.models[0])
_flamer = [w for w in _flamers.models[0].weapons if type(w) is TauFlamerProfile][0]
_fs = _flamer.strength
with only("EXPERIMENTAL_PROTOTYPE_CADRE_PLAYERS"):
    PROTO.apply_to_squad(_flamers, game_log=tk.Log())
    c.eq("the Thermoneutronic Projector adds +2 S to a T'au Flamer",
         _flamer.strength - _fs, 2)

c.eq("the Supernova Launcher names the Airbursting Fragmentation Projector",
     PROTO.upgrade_for("Supernova Launcher").weapon_cls,
     AirburstingFragmentationProjectorProfile)
c.eq("...and adds +3 S, the only one of the three that does",
     PROTO.upgrade_for("Supernova Launcher").strength, 3)

# MEASURED limitation: no model of the predefined T'au list carries any of the
# three weapons, so all three Enhancements are inert in it. Named, not hidden.
from game import army_lists  # noqa: E402
_tau_squads = army_lists.preview_squads("tau", "Player 1")
_carriers = [m.profile.name for s in _tau_squads for m in s.models
             for w in m.weapons
             if type(w) in (TauFlamerProfile, PlasmaRifleProfile,
                            AirburstingFragmentationProjectorProfile)]
c.eq("no model in the predefined T'au list carries one of the three weapons",
     _carriers, [])


# --- 7. Advanced Acquisition Cadre ----------------------------------------
print("\n7. Advanced Acquisition Cadre")

from game import detection_range, status_effects  # noqa: E402
from game import enh_negation_emitters as NEG  # noqa: E402
from game import enh_unmasking_suite as UNM  # noqa: E402

_neg_unit = build(STEALTH_BATTLESUITS, name="Negators", owner="Player 2")
E.grant(_neg_unit, "Negation Emitters")
with only("ADVANCED_ACQUISITION_CADRE_PLAYERS"):
    c.eq("Negation Emitters is -3 inches of detection range",
         NEG.detection_bonus_in(_neg_unit), NEG.NEGATION_EMITTERS_MODIFIER_IN)
    c.eq("...applied through the shared fold",
         detection_range.bonus_in(_neg_unit), -3.0)
    # Both bands, because the base is not a single number: 15" default and the
    # 12" house rule when a Dense wall sits on the model's own footprint.
    c.eq("15 inch default becomes 12", detection_range.apply(15.0, _neg_unit), 12.0)
    c.eq("12 inch house rule becomes 9", detection_range.apply(12.0, _neg_unit), 9.0)
with none_fielded():
    c.eq("gated on the detachment", detection_range.bonus_in(_neg_unit), 0.0)

_unm_unit = build(PATHFINDER_TEAM, name="Unmaskers", owner="Player 2")
E.grant(_unm_unit, "Unmasking Suite")
tk.line_up(_unm_unit, x=10.0, y=10.0, spacing=0.9)
_hidden = build(STRIKE_TEAM, name="Hider", owner="Player 1")
tk.line_up(_hidden, x=25.0, y=10.0, spacing=0.9)
_far_hidden = build(STRIKE_TEAM, name="FarHider", owner="Player 1")
tk.line_up(_far_hidden, x=60.0, y=10.0, spacing=0.9)
_state5 = GameState()
for _s in (_unm_unit, _hidden, _far_hidden):
    for _m in _s.models:
        _state5.add_token(_m)

with only("ADVANCED_ACQUISITION_CADRE_PLAYERS"):
    unm = UNM.UnmaskingSuiteController(game_state=_state5, decision_manager=None,
                                        game_log=tk.Log(), auto_players=("Player 2",))
    _elig = unm.eligible_targets(_unm_unit)
    c.true("an enemy unit within 24 inches is eligible", _hidden in _elig)
    c.true("...and one 50 inches away is not", _far_hidden not in _elig)
    c.true("selecting to shoot marks one", unm.begin_activation(_unm_unit))
    c.eq("the mark is +9 inches of detection range on the MARKED unit",
         unm.detection_bonus_in(unm.marked), UNM.UNMASKING_DETECTION_BONUS_IN)
    c.eq("...and nothing on anyone else", unm.detection_bonus_in(_far_hidden), 0.0)
    c.eq("15 inch default becomes 24 for the marked unit",
         detection_range.apply(15.0, unm.marked, unmasking=unm), 24.0)
    unm.end_activation(_unm_unit)
    c.eq("the mark ends when the unit has shot", unm.marked, None)

# The two sources go through ONE fold, which is the whole point of the
# extraction - is_detectable() asks once.
_status_src = io.open("game/status_effects.py", encoding="utf-8").read()
c.true("is_detectable() reads the shared fold, not three named arguments summed",
       "detection_range_module.apply(" in _status_src)
c.true("...and takes both new sources", "unmasking=unmasking" in _status_src)
c.true("game/shooting.py passes the Unmasking Suite in",
       "unmasking=self.unmasking_suite" in _shooting_src)


# --- 8. Auxiliary Cadre ---------------------------------------------------
print("\n8. Auxiliary Cadre")

from game import enh_admired_leader as ADM  # noqa: E402
from game import enh_student_of_kauyon as SOK  # noqa: E402
from game.leadership import leadership_threshold  # noqa: E402

# --- Student of Kauyon ---
_sok_bearer = build(KROOT_FLESH_SHAPER, name="SoK", owner="Player 2")
E.grant(_sok_bearer, "Student of Kauyon")
_carnivores = build(KROOT_CARNIVORES, name="Carnivores", owner="Player 2")
_hounds = build(TAU_EMPIRE.datasheets["Kroot Hounds"], name="Hounds", owner="Player 2")
with only("AUXILIARY_CADRE_PLAYERS"):
    sok = SOK.StudentOfKauyonStep(decision_manager=None, game_log=tk.Log(),
                                  auto_players=("Player 2",))
    _army = [_sok_bearer, _carnivores, _hounds]
    c.true("Kroot Carnivores are eligible", SOK.is_eligible_unit(_carnivores))
    # KROOT is a keyword; the printed text names two DATASHEETS. Kroot Hounds
    # carry the keyword and are NOT eligible - the difference is the rule.
    c.true("Kroot Hounds carry the KROOT keyword",
           any(m.profile.kroot for m in _hounds.models))
    c.true("...but are not one of the two named datasheets",
           not SOK.is_eligible_unit(_hounds))
    c.true("no Deep Strike to begin with", not SOK.has_deep_strike(_carnivores))
    sok.start(_army, "Player 2")
    c.true("the Carnivores now have Deep Strike (rule 24.09)",
           SOK.has_deep_strike(_carnivores))
    c.true("...and the Hounds still do not", not SOK.has_deep_strike(_hounds))
    c.eq("at most three units", SOK.MAX_UNITS, 3)

# --- Admired Leader ---
_adm_bearer = build(CADRE_FIREBLADE, name="Fireblade", owner="Player 2")
E.grant(_adm_bearer, "Admired Leader")
tk.line_up(_adm_bearer, x=10.0, y=10.0)
_kroot = build(KROOT_CARNIVORES, name="AdmiredKroot", owner="Player 2")
tk.line_up(_kroot, x=14.0, y=10.0, spacing=0.9)
_far_kroot = build(KROOT_CARNIVORES, name="FarKroot", owner="Player 2")
tk.line_up(_far_kroot, x=50.0, y=50.0, spacing=0.9)
_not_kroot = build(STRIKE_TEAM, name="NotKroot", owner="Player 2")
tk.line_up(_not_kroot, x=13.0, y=11.0, spacing=0.9)
_state6 = GameState()
for _s in (_adm_bearer, _kroot, _far_kroot, _not_kroot):
    for _m in _s.models:
        _state6.add_token(_m)

with only("AUXILIARY_CADRE_PLAYERS"):
    adm = ADM.AdmiredLeaderController(game_state=_state6, decision_manager=None,
                                       game_log=tk.Log(), auto_players=("Player 2",))
    _elig = adm.eligible_targets(_adm_bearer)
    c.true("a KROOT unit within 12 inches is eligible", _kroot in _elig)
    c.true("...one 50 inches away is not", _far_kroot not in _elig)
    c.true("...and a non-KROOT unit is not, however close", _not_kroot not in _elig)

    _ld_before = leadership_threshold(_kroot)
    _oc_before = objective_control.effective_oc(_kroot.models[0], _state6.tokens)
    adm.begin_command_phase("Player 2")
    c.true("a unit is marked", ADM.is_marked(_kroot))
    c.eq("+1 Ld is a BETTER characteristic, so a LOWER threshold",
         leadership_threshold(_kroot) - _ld_before, -1)
    c.eq("+1 OC", objective_control.effective_oc(_kroot.models[0], _state6.tokens)
         - _oc_before, 1)
    # "Until the start of your next Command phase": the same instant a round
    # apart, so one call clears and then re-offers - in that order.
    adm.begin_command_phase("Player 2")
    c.true("the mark survives its own re-offer (cleared, then set again)",
           ADM.is_marked(_kroot))
    adm.auto_players = set()
    adm.decision_manager = None
    adm.clear("Player 2")
    c.true("clearing really ends it", not ADM.is_marked(_kroot))
    c.eq("...and the Ld goes back", leadership_threshold(_kroot), _ld_before)
# THE ASSURANCE MOVED WITH THE CODE, it was not loosened. begin_command_phase()
# now lives in game/command_phase_mark.py, extracted when the three Spirit
# Conclave marks made this printed sentence a fourth carrier - so the ordering
# guard reads the shared machine, where getting it wrong would break four
# Enhancements instead of one.
_cpm_src = io.open("game/command_phase_mark.py", encoding="utf-8").read()
c.true("begin_command_phase() clears BEFORE it offers",
       before(_cpm_src, "self.clear(player)\n        asked = False",
              "for bearer_squad in self.bearer_units(player):"))
# ...and the one clause that is Admired Leader's own rather than the machine's:
# it skips the bearer's OWN unit, which the three new marks must not.
_adm_src = io.open("game/enh_admired_leader.py", encoding="utf-8").read()
c.true("Admired Leader keeps its own-unit exclusion",
       "exclude_own_unit=True" in _adm_src)
c.true("...as a PARAMETER of the shared machine, not a hard-coded line",
       "self.exclude_own_unit and squad is bearer_squad" in _cpm_src)


# --- 9. What the predefined list hands out --------------------------------
print("\n9. The predefined T'au list")


class fielding:
    """Give the T'au list a different set of detachments for one block.
    ArmyList entries are module-level singletons, so this puts the tuple back."""

    def __init__(self, names):
        self.entry = army_lists.get("tau")
        self.names = tuple(names)

    def __enter__(self):
        self.old = self.entry.detachments
        self.entry.detachments = self.names

    def __exit__(self, *exc):
        self.entry.detachments = self.old


# The 2026-09-05 roster buys SIX Enhancements across its two declared
# detachments, where the roster before it bought none. So this section drives
# the REAL list rather than a table written here - which is what the previous
# version had to do, and said so.
_squads = army_lists.preview_squads("tau", "Player 1")
_granted = sorted(n for s in _squads for n in E.granted_names(s))
c.eq("the list hands out six Enhancements", _granted, [
    "Exemplar of the Kauyon",
    "Negation Emitters",
    "Precision of the Patient Hunter",
    "Solid-image Projection Unit",
    "Through Unity, Devastation",
    "Unmasking Suite",
])
c.eq("...and the Kauyon table says exactly those",
     sorted(army_lists.get("tau").enhancement_names()), _granted)

# WHICH unit carries which. This is the half a datasheet lookup cannot do:
# there are TWO Cadre Fireblades taking different Enhancements, and TWO
# identical Stealth Battlesuits teams of which only the first takes one.
_bearer = {}
for _s in _squads:
    for _n in E.granted_names(_s):
        _bearer[_n] = _s.name
c.eq("the first Fireblade carries Through Unity, Devastation",
     _bearer["Through Unity, Devastation"], "1 Breacher Team 1 + Cadre Fireblade")
c.eq("...and the SECOND carries Precision of the Patient Hunter",
     _bearer["Precision of the Patient Hunter"], "1 Breacher Team 2 + Cadre Fireblade")
c.eq("the Commander carries Exemplar of the Kauyon, on the unit he leads",
     _bearer["Exemplar of the Kauyon"],
     "1 Crisis Sunforge Battlesuits 1 + Commander in Coldstar Battlesuit")
c.eq("the Ethereal carries Solid-image Projection Unit",
     _bearer["Solid-image Projection Unit"], "1 Ethereal 1")
c.eq("only the FIRST Stealth team carries Negation Emitters",
     _bearer["Negation Emitters"], "1 Stealth Battlesuits 1")
c.eq("the Ghostkeel carries Unmasking Suite",
     _bearer["Unmasking Suite"], "1 Ghostkeel Battlesuit 1")

# TWO of them are on the model, four on... no: two are UNIT-level and four are
# model-level, and a model-level one has to land on the right MODEL after the
# 19.01 merge - by then the Fireblade is one of eleven.
_models = [m.profile.name for s in _squads
           for m in E.enhancement_models(s, "Through Unity, Devastation")]
c.eq("a model-level Enhancement lands on the character, not the bodyguard",
     _models, ["Cadre Fireblade"])

# The points are the units' plus the Enhancements'.
c.eq("...and their points are on the army", sum(s.points or 0 for s in _squads), 2165)

# THE DETACHMENT GATES IT, which is what closes starflare_ignition.py's old
# limitation: the same units under a detachment the list does not declare hold
# their Enhancement but it does nothing.
# is_active() reads the CONFIG constants, which preview_squads() deliberately
# never writes - that separation is the whole reason the grant reads the list
# instead. So the config is set the way a battle sets it, and put back.

army_lists.apply_to_config({"Player 1": "tau", "Player 2": "tau"})
_live_now = [n for s in _squads for n in E.granted_names(s) if E.is_active(s, n)]
c.eq("under the declared pair, all six are active", sorted(_live_now), _granted)
with fielding(["Mont'ka"]):
    army_lists.apply_to_config({"Player 1": "tau", "Player 2": "tau"})
    _live = [n for s in _squads for n in E.granted_names(s) if E.is_active(s, n)]
    c.eq("...and under a detachment the list does not field, none of them is",
         _live, [])
army_lists.apply_to_config({"Player 1": "tau", "Player 2": "tau"})

# An Enhancement this list may not buy is refused when the list is LOADED, not
# granted and then quietly inert. This replaces a hand-maintained whitelist that
# only knew the names some T'au builder happened to mention; the check now reads
# the Enhancement's own detachment against the ones the list declares, so it
# covers every faction and cannot fall behind a new list.
_bad = {"format": 1, "key": "probe", "name": "Probe",
        "faction_keyword": "T'AU EMPIRE", "detachments": ["Mont'ka"],
        "roster": [{"datasheet": "Cadre Fireblade", "color": [1, 2, 3],
                    "enhancement": "Exemplar of the Kauyon"}]}
_problems = army_io.parse(_bad, "probe.json")[1]
c.true("an Enhancement from a detachment the list does not field is refused",
       any("does not field" in p for p in _problems))
# The far more likely mistake, and the one a NameError used to catch: a typo.
_typo = dict(_bad, detachments=["Kauyon"],
             roster=[dict(_bad["roster"][0], enhancement="Exemplar of the Kauyonn")])
c.true("...and a misspelt Enhancement is refused too",
       any("not an engine-wired Enhancement" in p
           for p in army_io.parse(_typo, "probe.json")[1]))


# --- 9b. The SECOND T'au list ---------------------------------------------
print("\n9b. The Mont'ka list")

# REPLACED 2026-09-06 by the roster the user exported from the app ("Tau -
# RC 1k", 1975 points). It used to BE the Kauyon roster with a different
# Enhancement table; it now shares fourteen of twenty-one entries with it,
# which is not a shared roster, so it has its own builder.
_mk = army_lists.preview_squads("tau_montka", "Player 1")
_mk_granted = sorted(n for s in _mk for n in E.granted_names(s))
c.eq("the Mont'ka list hands out ONE", _mk_granted, ["Strategic Conqueror"])
c.eq("...which is Mont'ka's own",
     E.get("Strategic Conqueror").setting, "MONTKA_PLAYERS")
c.eq("it totals its printed 1975", sum(s.points or 0 for s in _mk), 1975)
c.eq("18 list entries become 14 units", len(_mk), 14)
c.eq("...over 69 models", sum(len(s.models) for s in _mk), 69)

# THE BEARER MOVED from a Cadre Fireblade to the Commander in Coldstar, and it
# is pinned at the MODEL: after 19.01 his unit holds four, and "the unit
# carries it" would pass with it on a Starscythe suit.
_mk_bearers = [(s.name, m) for s in _mk
               for m in E.enhancement_models(s, "Strategic Conqueror")]
c.eq("exactly one model carries it", len(_mk_bearers), 1)
_mk_unit, _mk_model = _mk_bearers[0] if _mk_bearers else ("(nobody)", None)
c.eq("...in the unit the Coldstar leads", _mk_unit,
     "1 Crisis Starscythe Battlesuits 1 + Commander in Coldstar Battlesuit")
c.true("...and it is the Coldstar himself",
       _mk_model is not None and "Coldstar" in _mk_model.profile.name)
c.eq("exactly one unit in the list carries one",
     sum(1 for s in _mk if E.granted_names(s)), 1)
# The two Fireblades take nothing, which the export says by pricing them at
# their base 50. They are merged now, so read the LEADER COMPONENT - the squad
# total is the Breachers' 90 plus theirs.
_mk_fireblades = [c_ for s in _mk for c_ in attached_units.leader_components(s)
                  if c_.datasheet.name == "Cadre Fireblade"]
c.eq("both Cadre Fireblades are in the list at their base 50",
     [c_.points for c_ in _mk_fireblades], [50, 50])

# THREE OF MONT'KA'S FOUR ENHANCEMENTS LOSE THEIR ONLY CARRIER. Named rather
# than left to be rediscovered: they are built, wired and tested, and from here
# no shipped list fields them - the same "dormant by construction" state the
# Experimental Prototype Cadre trio was in before a list equipped their guns.
_MONTKA_ENHANCEMENTS = sorted(n for n, s in E.ENHANCEMENTS.items()
                              if s.setting == "MONTKA_PLAYERS")
c.eq("Mont'ka prints four Enhancements", len(_MONTKA_ENHANCEMENTS), 4)
c.eq("...and this list now fields exactly one of them",
     sorted(set(_MONTKA_ENHANCEMENTS) - set(_mk_granted)),
     ["Coordinated Exploitation", "Exemplar of the Mont'ka", "Strike Swiftly"])

# TWO ATTACHMENTS (19.01), and this is the first roster in the project whose
# source STATES them - the export prints an "Attached Units" heading with each
# model's role, rather than leaving it to a sentence from the user.
_mk_pairs = sorted(
    (attached_units.bodyguard_components(s)[0].datasheet.name,
     attached_units.leader_components(s)[0].datasheet.name)
    for s in _mk
    if attached_units.leader_components(s) and attached_units.bodyguard_components(s))
c.eq("four units are attached, and nothing else is", _mk_pairs, [
    ("Breacher Team", "Cadre Fireblade"),
    ("Breacher Team", "Cadre Fireblade"),
    ("Crisis Starscythe Battlesuits", "Commander in Coldstar Battlesuit"),
    ("Crisis Sunforge Battlesuits", "Commander Farsight"),
])
# THE TWO FIREBLADES ARE THE USER'S CALL AGAINST THE EXPORT (2026-09-06: "bei
# der Tau Montka liste sollen die fireblades die breacher anfuehren"), which
# prints them under CHARACTERS and prices its Breacher Teams at the un-led 90.
# It costs NOTHING - attach() sums the components - so the army total cannot
# see it and only the unit count and these pairings move. That is exactly why
# they are pinned here rather than left to the total.
c.true("each Breacher Team is 11 models at 140 once its Fireblade joins",
       [(len(s.models), s.points) for s in _mk if "Breacher" in s.name]
       == [(11, 140), (11, 140)])
# DARKSTRIDER is the one character still standing alone, and that is a LIST
# decision rather than a rules one: his own printed LEADER line names the
# Pathfinder Team, so attach() would take him.
# next(...) with no default would CRASH the suite for a probe that removes him
# rather than turning it red, and a crash hides which check broke.
_mk_ds = next((s for s in _mk if "Darkstrider" in s.name), None)
c.true("Darkstrider is in the list", _mk_ds is not None)
c.eq("...standing alone",
     attached_units.is_attached_unit(_mk_ds) if _mk_ds else "(absent)", False)
c.eq("...though his datasheet would let him lead the Pathfinders",
     attached_units.leadable_unit_names(_mk_ds) if _mk_ds else None,
     ("Pathfinder Team",))

# EACH BREACHER TEAM RIDES ITS OWN DEVILFISH. preview_squads() throws the
# destination away, so this drives the builder's register callback directly -
# the hint is the only thing that says who is in which transport, and a wrong
# pairing (both teams into one Devilfish) is silent everywhere else.
_mk_reg = []
army_lists.get("tau_montka").build(
    "Player 1",
    lambda s, d=pregame.DEPLOY, transport=None: _mk_reg.append(
        (s.name, d, transport.squad.name if transport is not None else None)))
c.eq("each Breacher Team is declared into its own Devilfish",
     [(n, t) for n, d, t in _mk_reg if d == pregame.EMBARK],
     [("1 Breacher Team 1 + Cadre Fireblade", "1 Devilfish 1"),
      ("1 Breacher Team 2 + Cadre Fireblade", "1 Devilfish 2")])
c.true("...and nothing else is declared anywhere but the board",
       all(d == pregame.DEPLOY for n, d, _t in _mk_reg if "Breacher" not in n))

# THE PATHFINDER TEAM is the one entry that needed a datasheet change: its
# Shas'ui carries the semi-automatic grenade launcher, and the option was only
# ever offered on the rank and file - while the comment above the datasheet
# claimed both lines. A `choices` entry naming a (line, option) pair the
# datasheet does not have is DROPPED SILENTLY, so the build came out one weapon
# short and correctly priced, which is the shape that survives review.
_mk_pf = next(s for s in _mk if "Pathfinder" in s.name)
_mk_shasui = _mk_pf.models[0]
c.true("the Pathfinder Shas'ui carries the grenade launcher",
       any("Grenade Launcher" in w.name for w in _mk_shasui.weapons))
c.true("...and keeps his pulse carbine, because the option is an ADDITION",
       any(w.name == "Pulse Carbine" for w in _mk_shasui.weapons))
c.eq("...while three of the nine trade theirs for an Ion rifle",
     sum(1 for m in _mk_pf.models for w in m.weapons if "Ion Rifle" in w.name), 3)
c.eq("...which is what makes it 100 rather than the bare 85",
     _mk_pf.points, 100)

# THE DRONES, which the export names model by model and which NOTHING ELSE
# HERE CAN CATCH: every one of them is free, so a wrong drone leaves the unit
# total, the army total and the weapon count untouched. Three of these moved
# against the roster this replaces - the Breacher Shas'ui (Gun -> Shield), the
# Coldstar (Marker+Shield -> two Shields) and the second Fireblade (bare -> two
# Gun Drones) - and an A/B probe that put one back was SILENT until this block
# existed.
_mk_gear = {}
for _s in _mk:
    for _m in _s.models:
        if _m.gear_names:
            _mk_gear.setdefault(_m.profile.name, []).append(sorted(_m.gear_names))
c.eq("the export's drones, model by model",
     {k: sorted(v) for k, v in sorted(_mk_gear.items())}, {
         "Breacher Fire Warrior Shas'ui": [["Guardian Drone", "Shield Drone"]] * 2,
         "Broadside Shas'ui": [["Missile Drone", "Missile Drone",
                                "Seeker Missile", "Twin Plasma Rifle"]] * 2,
         "Broadside Shas'vre": [["Missile Drone", "Missile Drone",
                                 "Seeker Missile", "Twin Plasma Rifle"]],
         "Cadre Fireblade": [["Gun Drone", "Gun Drone"]] * 2,
         # Not only drones: the Coldstar's "up to three of the following" menu
         # is Gear too, so his two added burst cannons and cyclic ion blaster
         # are recorded here alongside the drones. They used to be one bundled
         # wargear option, which is why this line was drones-only before.
         "Commander in Coldstar Battlesuit": [["Burst Cannon", "Burst Cannon",
                                               "Cyclic Ion Blaster",
                                               "Shield Drone", "Shield Drone"]],
         "Crisis Starscythe Shas'ui": [["Gun Drone", "Shield Drone"]] * 2,
         "Crisis Starscythe Shas'vre": [["Marker Drone", "Shield Drone"]],
         "Crisis Sunforge Shas'ui": [["Gun Drone", "Shield Drone"]] * 2,
         "Crisis Sunforge Shas'vre": [["Marker Drone", "Shield Drone"]],
         "Pathfinder Shas'ui": [["Grav-inhibitor Drone", "Gun Drone", "Gun Drone"]],
         "Stealth Shas'ui": [["Homing Beacon"]] * 2,
         "Stealth Shas'vre": [["Gun Drone", "Marker Drone"]] * 2,
     })


# --- 9c. RETIRED --------------------------------------------------------
# The Prototypes list (Auxiliary Cadre + Experimental Prototype Cadre) was
# removed on user request ("diese liste kann weg"), and this block went with
# it. What it proved is not lost: the Recon list fields Experimental Prototype
# Cadre too and buys two of its three weapon Enhancements, so their upgrades
# are still exercised below. What DID go dormant with it is named rather than
# quietly dropped - Death Trap (see test_force_dispositions.py) and the two
# Enhancements no list buys any more (section 13).

# --- 9d. The FOURTH T'au list, and the pricing it corrected ---------------
print("\n9d. The Retaliation Cadre list")

# User: "jetzt noch retaliation cadre Liste zusaetzlich". The only T'au list
# that does NOT share the other three's roster - no Breachers, no Devilfish,
# no Ethereal, no Fireblades - so it has its own builder.
_rc = army_lists.preview_squads("tau_retaliation", "Player 1")
_rc_granted = sorted(n for s in _rc for n in E.granted_names(s))
c.eq("it hands out ONE Enhancement", _rc_granted, ["Starflare Ignition System"])
c.eq("...which is Retaliation Cadre's own",
     E.get("Starflare Ignition System").setting, "RETALIATION_CADRE_PLAYERS")
c.eq("it totals its printed 1965", sum(s.points or 0 for s in _rc), 1965)


# FOUR ATTACHMENTS (19.01), every one of them named by the user rather than
# guessed: "Farsight in die Flamer Starsythe / Burst Cannon Coldstar in die
# Burst Cannon Starsysthe / Missile Pod Enforcer in die Fireknife / Fusion
# Enforcer in die Sunforge". All three commanders may lead all three Crisis
# datasheets, so nothing in the rules picks between them - the pairing is a
# LIST fact and is pinned by the WEAPONS, which is how the user named them.
def _weapon_names(models):
    return {w.name for m in models for w in m.weapons}


_pairs = {}
for _s in _rc:
    _leaders = attached_units.leader_components(_s)
    _bodies = attached_units.bodyguard_components(_s)
    if _leaders and _bodies:
        _pairs[(_bodies[0].datasheet.name,
                _leaders[0].datasheet.name)] = (_weapon_names(_bodies[0].starting_models),
                                                _weapon_names(_leaders[0].starting_models))


def _pair(body, leader):
    """The two weapon sets of one pairing, or two EMPTY sets if that pairing
    was never formed. Indexing the dict directly would make a probe that
    removes an attachment CRASH the suite rather than turn it red, and this
    repo has recorded that failure enough times to have a rule about it."""
    return _pairs.get((body, leader), (set(), set()))


c.eq("four units are attached, and nothing else is",
     sorted(_pairs), [
         ("Crisis Fireknife Battlesuits", "Commander in Enforcer Battlesuit"),
         ("Crisis Starscythe Battlesuits", "Commander Farsight"),
         ("Crisis Starscythe Battlesuits", "Commander in Coldstar Battlesuit"),
         ("Crisis Sunforge Battlesuits", "Commander in Enforcer Battlesuit"),
     ])
# The two Starscythe units are the SAME datasheet and differ only in their
# guns, so a leader put on the wrong one is invisible to a name check.
_body, _lead = _pair("Crisis Starscythe Battlesuits", "Commander Farsight")
c.true("Farsight joins the FLAMER Starscythe", "T'au Flamer" in _body
       and "Burst Cannon" not in _body)
_body, _lead = _pair("Crisis Starscythe Battlesuits", "Commander in Coldstar Battlesuit")
c.true("the Coldstar joins the BURST CANNON Starscythe", "Burst Cannon" in _body
       and "T'au Flamer" not in _body)
c.true("...and he is the burst-cannon Coldstar himself",
       "High-output Burst Cannon" in _lead and "Burst Cannon" in _lead)
# Likewise the two Enforcers: one datasheet, told apart only by its support
# slots, so the pairing has to be read off the guns on both sides.
_body, _lead = _pair("Crisis Fireknife Battlesuits", "Commander in Enforcer Battlesuit")
c.true("the MISSILE POD Enforcer joins the Fireknife",
       "Missile Pod" in _lead and "Fusion Blaster" not in _lead
       and "Missile Pod" in _body)
_body, _lead = _pair("Crisis Sunforge Battlesuits", "Commander in Enforcer Battlesuit")
c.true("the FUSION Enforcer joins the Sunforge",
       "Fusion Blaster" in _lead and "Missile Pod" not in _lead
       and "Fusion Blaster" in _body)

# The Enhancement rides with the missile-pod Enforcer into the Fireknife. It
# is pinned at the MODEL, not the unit: after 19.01 the squad holds four
# models, and "the unit carries it" would pass with it on a Fireknife suit.
_bearers = [(s.name, m) for s in _rc
            for m in E.enhancement_models(s, "Starflare Ignition System")]
c.eq("its one Enhancement is carried by exactly one model", len(_bearers), 1)
_bearer_unit, _bearer_weapons = (_bearers[0][0], _weapon_names([_bearers[0][1]])) \
    if _bearers else ("(nobody)", set())
c.eq("...in the unit the missile-pod Enforcer leads", _bearer_unit,
     "1 Crisis Fireknife Battlesuits 1 + Commander in Enforcer Battlesuit")
c.true("...and by the Enforcer himself, not one of his Fireknife suits",
       "Missile Pod" in _bearer_weapons and "Twin Pulse Carbine" not in _bearer_weapons)

# THE TWIN LANCE is the one character left standing alone, and that is its
# DATASHEET rather than a forgotten pairing: it prints no LEADER line, so
# leadable_unit_names() is empty and can_attach() would refuse every unit.
_twin = next(s for s in _rc if "Twin Lance" in s.name)
c.eq("The Twin Lance stands alone", attached_units.is_attached_unit(_twin), False)
c.eq("...because its datasheet leads nothing",
     attached_units.leadable_unit_names(_twin), ())
c.eq("sixteen list entries become twelve units", len(_rc), 12)
c.eq("...with the same 57 models either way",
     sum(len(s.models) for s in _rc), 57)

# THREE POINTS CORRECTIONS came out of transcribing it, and each is pinned
# against the CORPUS rather than against a literal, so a GW update moves them.
_corpus = io.open("rules/tau_empire/The Twin Lance.md", encoding="utf-8").read()
c.true("The Twin Lance prints 230, which is what the engine now charges",
       "| YOUR UNIT COSTS | 2 models | 230 |" in _corpus)
c.eq("...and it does", t.THE_TWIN_LANCE.points_for(0, unit_index=1), 230)
_corpus = io.open("rules/tau_empire/Crisis Starscythe Battlesuits.md", encoding="utf-8").read()
c.true("Crisis Starscythe prints 100 / 110, not the 90 / 100 transcribed before",
       "| YOUR 1ST TO 2ND UNITS COST | 3 models | 100 |" in _corpus
       and "| YOUR 3RD + UNIT COSTS | 3 models | 110 |" in _corpus)

# THE PER-WEAPON PRICE. The list prices the SAME datasheet twice, which is the
# measurement that settles it: 130 with six T'au flamers, 100 with none.
# Read off the BODYGUARD COMPONENT, not the merged squad - both Starscythe
# units now carry an 80-point commander, and Squad.points is the sum of the
# two. The component keeps its own price for exactly this kind of question.
# It falls back to the squad when there is no component, so that a probe which
# removes the attachments turns the checks below RED instead of crashing here.
_ss = []
for _s in _rc:
    if "Starscythe" not in _s.name:
        continue
    _bodies = attached_units.bodyguard_components(_s)
    _points = _bodies[0].points if _bodies else _s.points
    _models = _bodies[0].starting_models if _bodies else _s.models
    _ss.append((_points, sum(1 for m in _models for w in m.weapons
                             if w.name == "T'au Flamer")))
_ss.sort()
c.eq("two Starscythe units, one all flamers and one none", _ss, [(100, 0), (130, 6)])
c.eq("...so each flamer costs 5 on a base of 100",
     (_ss[1][0] - _ss[0][0]) // _ss[1][1], 5)
# ...and the printed DEFAULT, which carries three, therefore costs 115 - the
# number the old "per swap" reading could not produce.
c.eq("the printed default carries three and costs 115",
     tk.build_squad(t.CRISIS_STARSCYTHE, "Player 1", name="x").points, 115)

# ONLY TWO DATASHEETS ARE AFFECTED, and that is measured rather than asserted:
# for every other priced option the printed default carries none of the weapon,
# so per-swap and per-weapon agree. A third would have to be added on purpose.
_per_weapon = []
for _fac in (t.TAU_EMPIRE,):
    for _ds in _fac.datasheets.values():
        if getattr(_ds.points, "per_weapon", None):
            _per_weapon.append(_ds.name)
c.eq("exactly two datasheets price per weapon", sorted(_per_weapon),
     ["Crisis Fireknife Battlesuits", "Crisis Starscythe Battlesuits"])
c.true("...and neither charges the swap as well, which would double it",
       not any(o.points for ds_name in _per_weapon
               for o in (t.TAU_EMPIRE.datasheets[ds_name].wargear_options or ())))


def _roster_signatures(key):
    """One canonical string per roster entry of armies/<key>.json, ignoring the
    `id` (which only exists so a passenger can name its carrier) and any `note`
    (prose, not part of the list). Two entries with the same signature are the
    same declaration."""
    data = json.load(io.open("armies/%s.json" % key, encoding="utf-8"))
    return [json.dumps({k: v for k, v in entry.items() if k not in ("id", "note")},
                       sort_keys=True)
            for entry in data["roster"]]


# --- 10. Source guards ----------------------------------------------------
print("\n10. Source guards")

# The grant reads the LIST's declared detachments, not config - preview_squads()
# builds the army screen's tile before anything is applied to config.
_army_src = io.open("game/army_lists.py", encoding="utf-8").read()
# The grant happens where the units are BUILT, because that is the only place
# that can tell two Cadre Fireblades apart - a lookup by datasheet finds the
# first of each. And it still never reads config: preview_squads() builds the
# army screen's tile before anything is applied there, so a config-driven grant
# would make the screen's points disagree with the battle's.
_roster_src = io.open("game/army_roster.py", encoding="utf-8").read()
c.true("the grant runs at the build site",
       "enhancements.grant(squad, entry.enhancement)" in _roster_src)
c.true("...for the leaders too - a list may field more than one",
       "enhancements.grant(leader_squad, spec.enhancement)" in _roster_src)
c.true("...and BEFORE the merge, while the character is still his own squad",
       _roster_src.find("PASS 2 - Enhancements") < _roster_src.find("PASS 3 - 19.01"))
# EVERY LIST IS ITS OWN FILE, which inverts what this block used to assert.
# Kauyon and the Prototypes list were once ONE _build_tau_roster() with a
# different Enhancement table each, and the pair that proved the split is gone -
# the Prototypes list was retired on user request. So the claim is now made
# against the four that remain: no two of them share anything but a faction, and
# nothing in army_lists.py builds a roster at all.
#
# The reason the duplication was accepted when the pair existed still stands and
# is worth keeping written down: an army list is a DECLARATION, not code, and
# under the shared builder editing the Kauyon Pathfinders silently edited the
# Prototypes list too - coupling shaped like a bug.
_tau_keys = [e.key for e in army_lists.lists_for("T'AU EMPIRE")]
c.eq("the T'au ship four lists, each its own file", len(_tau_keys), 4)
c.true("...and every one of them is on disk",
       all(os.path.exists("armies/%s.json" % k) for k in _tau_keys))
c.true("no list is built by a function in army_lists.py any more",
       not [n for n in ast.walk(ast.parse(_army_src))
            if isinstance(n, ast.FunctionDef) and n.name.startswith("build_")])
c.true("...without reading the config constants",
       "player_has_detachment" not in _army_src)

# Every one of the nineteen has a module that cites its printed rule, and gates
# on its detachment. A twentieth cannot arrive without this loop covering it.
_MODULE_FOR = {
    "Internal Grenade Racks": "game/enh_internal_grenade_racks.py",
    "Prototype Weapon System": "game/enh_prototype_weapon_system.py",
    "Puretide Engram Neurochip": "game/enh_puretide_neurochip.py",
    "Starflare Ignition System": "game/starflare_ignition.py",
    "Exemplar of the Kauyon": "game/enh_exemplars.py",
    "Exemplar of the Mont'ka": "game/enh_exemplars.py",
    "Precision of the Patient Hunter": "game/enh_precision_patient_hunter.py",
    "Solid-image Projection Unit": "game/enh_solid_image_projection.py",
    "Through Unity, Devastation": "game/enh_guided_keyword_grants.py",
    "Coordinated Exploitation": "game/enh_guided_keyword_grants.py",
    "Strategic Conqueror": "game/enh_strategic_conqueror.py",
    "Strike Swiftly": "game/enh_strike_swiftly.py",
    "Thermoneutronic Projector": "game/enh_prototype_weapons.py",
    "Plasma Accelerator Rifle": "game/enh_prototype_weapons.py",
    "Supernova Launcher": "game/enh_prototype_weapons.py",
    "Negation Emitters": "game/enh_negation_emitters.py",
    "Unmasking Suite": "game/enh_unmasking_suite.py",
    "Student of Kauyon": "game/enh_student_of_kauyon.py",
    "Admired Leader": "game/enh_admired_leader.py",
}
# Applied on BOTH start paths, not only the pre-game one: a legacy or --load
# scene has no Declare Battle Formations step, and without the second call it
# would carry the Enhancement (and its points) with none of its effect.
c.eq("the prototype weapon upgrades run on both start paths",
     _main_src.count("enh_prototype_weapons.apply_all("), 2)
c.eq("every registered T'au Enhancement has a module here",
     sorted(_MODULE_FOR), sorted(TAU_SPECS))
for _name, _path in sorted(_MODULE_FOR.items()):
    _src = io.open(_path, encoding="utf-8").read()
    c.true(f"{_name}: its module quotes the printed rule", "RULE" in _src)
    c.true(f"{_name}: its module names the Enhancement",
           _name in _src or _name.replace("'", "’") in _src)

# main.py's wiring: a controller that is constructed and never fed is invisible
# to every behaviour test (this repo has recorded four of them).
for _call in (
    "movement_controller.on_move_finished.append(\n        internal_grenade_racks_controller.on_move_finished)",
    "stratagem_controller.on_targets_chosen.append(\n        puretide_neurochip_controller.on_targets_chosen)",
    "admired_leader_controller.begin_command_phase(turn_tracker.turn_owner)",
    "enh_strategic_conqueror.offer(",
    # _all_squads(), NOT state.all_squads()/_player_squads(): at Declare Battle
    # Formations those read three containers that register_unit() deliberately
    # leaves empty while PREGAME_DEPLOYMENT is on, so both of these steps used
    # to be handed NOTHING and quietly upgraded/granted nothing at all.
    # Reported: "experimental cadre waffen upgrades greifen alle nicht".
    "enh_prototype_weapons.apply_all(",
    "_all_squads(state, pregame_controller), game_log=game_log)",
    "[s for s in _all_squads(state, pregame_controller) if s.owner == _owner]",
    # Prince Yriel's Prince of Corsairs fires at the SAME instant, and
    # PregameController has one redeploy_step slot - so main.py now chains the
    # two. What this pin has always been about is that Solid-image REACHES that
    # hook, so it names the step and the chain rather than one assignment.
    "_solid_image_step = SolidImageProjectionStep(",
    "pregame_controller.redeploy_step = _RedeployChain(",
    "prototype_weapon_system=prototype_weapon_system_controller,",
    "unmasking_suite=unmasking_suite_controller,",
    "internal_grenade_racks_controller.on_dice_acknowledged()",
    "puretide_neurochip_controller.on_dice_acknowledged()",
):
    c.true(f"main.py wires: {_call.splitlines()[0][:60]}", _call in _main_src)

# The two activation-scoped ones open and close on the SAME pair of seams.
c.true("Prototype Weapon System opens on start_shooting()",
       "self.prototype_weapon_system.begin_activation(squad)" in _shooting_src)
c.true("...and closes on the end of the activation",
       "self.prototype_weapon_system.end_activation(self.active_squad)" in _shooting_src)
c.true("Unmasking Suite uses the same two",
       "self.unmasking_suite.begin_activation(squad)" in _shooting_src
       and "self.unmasking_suite.end_activation(self.active_squad)" in _shooting_src)

# No AI path - the standing T'au rule. Checked as NEGATIVE SPACE: none of the
# nineteen may be reachable from ai/agent_driver.py.
_driver = io.open("ai/agent_driver.py", encoding="utf-8").read()
_leaks = [n for n in E.ENHANCEMENTS if n.lower() in _driver.lower()]
c.eq("no Enhancement has an AI path in ai/agent_driver.py", _leaks, [])
c.true("...and no enh_* module is imported there", "enh_" not in _driver)

_SHOOTING_PATH = os.path.join("game", "shooting.py")


# --- 11. The two that were only ever pinned by SUBSTRING -------------------
print("\n11. Through a real ShootingController")

# WHAT THIS CLOSES. Everything above drives rule modules and controllers
# directly, which is the right level for a rule - but two of the nineteen
# reach the engine through seams no direct call exercises, and for those the
# only evidence was a string:
#
#     "enh_precision_patient_hunter.hit_bonus(model)" in _shooting_src
#     "enh_prototype_weapon_system.attack_key(model)" in _shooting_src
#
# A substring holds while the call sits behind a condition that is never true,
# while its result is discarded, and while _attack_key() groups the models back
# together anyway. So this section builds a REAL ShootingController and asks
# what it actually did - the same step the panel matrix is for the Stratagems.
from game.shooting import ShootingController  # noqa: E402
from game.dice import DiceManager  # noqa: E402
from game.decision import DecisionManager  # noqa: E402
from game.factions.orks import BOYZ  # noqa: E402
from game import enh_precision_patient_hunter as PPH2  # noqa: E402
from game import enh_prototype_weapon_system as PWS2  # noqa: E402
from game.turn import PHASES, PHASE_SHOOTING, TurnTracker  # noqa: E402

HUMAN2 = "Player 1"


def _shoot_scene(bearer_sheet, name):
    """A real controller over a real board: bearer at 10,10 and an enemy 8"
    away - in range, out of Engagement Range."""
    unit = tk.line_up(build(bearer_sheet, owner=HUMAN2, name=name), 10.0, 10.0)
    foe = tk.line_up(build(BOYZ, owner="Player 2", name="2 Boyz 1"), 10.0, 18.0)
    tokens = list(unit.models) + list(foe.models)
    tracker = TurnTracker(first_player=HUMAN2)
    tracker.phase_index = PHASES.index(PHASE_SHOOTING)
    tracker.turn_owner = HUMAN2
    tracker.active_player = HUMAN2
    # ROUND 3. Precision of the Patient Hunter's wound half is "from the third
    # battle round onwards", so a scene at round 2 would measure the rule
    # correctly withholding it and read as a missing wire.
    tracker.battle_round = 3
    # BY KEYWORD, all of it: ShootingController's first positional is
    # `obstacles`, not the token list. Handing it the tokens works right up
    # until something asks for line of sight, and then a Token is asked for
    # its .max_x - so a positional call here reads as a plausible scene and
    # falls over the first time cover is computed.
    ctrl = ShootingController(obstacles=[], game_log=tk.Log(),
                              player_name=HUMAN2, dice_manager=DiceManager(),
                              turn_tracker=tracker, all_tokens=tokens,
                              decision_manager=DecisionManager())
    return unit, foe, ctrl


# --- Precision of the Patient Hunter, through _hit_modifiers() -------------
# "+1 to the Hit roll" is a BETTER roll, so game/modifiers.py's convention
# makes it a NEGATIVE adjustment to the threshold. Measured as the threshold
# the controller really computes, not as the Modifier object the rule returns:
# a rule that emitted the right object into a chain nothing reads would pass
# the second and fail the first.
_pph_unit, _pph_foe, _pph_ctrl = _shoot_scene(CADRE_FIREBLADE, "1 Cadre Fireblade 1")
_pph_model = _pph_unit.models[0]
_pph_weapon = next(w for w in _pph_model.weapons if getattr(w, "range_in", 0))


def _group(model, weapon, target):
    """The shape _hit_modifiers() reads: it takes the GROUP rule 04.03 rolls
    together, not a loose (model, weapon, target) triple."""
    return {"pairs": [(model, weapon)], "target_squad": target,
            "shooter_squad": model.squad}


with only("KAUYON_PLAYERS", players=(HUMAN2,)):
    _g = _group(_pph_model, _pph_weapon, _pph_foe)
    _before = _pph_ctrl._hit_modifiers(_g)
    E.grant(_pph_unit, "Precision of the Patient Hunter", model=_pph_model)
    _after = _pph_ctrl._hit_modifiers(_g)
    _delta = sum(m.amount for m in _after) - sum(m.amount for m in _before)
    c.eq("Precision reaches the real controller's hit modifiers", _delta, -1)
    c.true("...and it is labelled, so a die can say where the bonus came from",
           any("Precision" in (m.source or "") for m in _after))

    # The same rule also feeds the WOUND step through the same module, and a
    # fix wired to one and not the other is the shape this audit keeps finding.
    # _wound_modifiers() reads the REPRESENTATIVE shooter off current_group,
    # so the group has to be set the way a real activation sets it.
    # active_squad AND current_group: _wound_modifiers() reads the first for
    # the attacking unit and picks the representative shooter off the second.
    _pph_ctrl.active_squad = _pph_unit
    _pph_ctrl.current_group = _g
    _wafter = _pph_ctrl._wound_modifiers(_pph_foe)
    c.true("...and the wound step picks it up too",
           any("Precision" in (m.source or "") for m in _wafter))
    _pph_ctrl.current_group = None
    _pph_ctrl.active_squad = None

# THE GROUPING HALF, which is the one a substring cannot check at all. The
# bonus is PER MODEL, and rule 04.03 groups identical attacks together - so
# _attack_key() has to put a bearer in a DIFFERENT group from its squadmates,
# or the group would resolve at one threshold for models that do not share one.
from game.shooting import _attack_key  # noqa: E402

# THE SHIPPED BEARER, not a constructed one. The printed BEARER line is
# "T'AU EMPIRE model only" plus CHARACTER, so a plain Strike Team cannot carry
# it - and the unit that CAN is one with a character leading squadmates, which
# is exactly the shape the grouping question is about. The `tau` list already
# puts it on a Cadre Fireblade leading a Breacher Team, so this drives that.
_pph2_unit = next(s for s in army_lists.preview_squads("tau", "Player 1")
                  if E.has(s, "Precision of the Patient Hunter"))
_pph2_bearer = E.bearer_models(_pph2_unit, "Precision of the Patient Hunter")[0]
_pph2_other = next(m for m in _pph2_unit.models if m is not _pph2_bearer)

# INSIDE the detachment context: applies() goes through is_active(), which asks
# whether the owner actually fields Kauyon - and preview_squads() deliberately
# writes no config. Outside it every model reads bonus 0, which looks exactly
# like a rule that never reached _attack_key().
with only("KAUYON_PLAYERS", players=("Player 1",)):
    c.true("the shipped bearer really leads squadmates", len(_pph2_unit.models) > 1)
    c.true("...and it is a CHARACTER, as the printed BEARER line demands",
           _pph2_bearer.profile.character)
    c.eq("the bearer carries the hit bonus", PPH2.hit_bonus(_pph2_bearer), 1)
    c.eq("...and its squadmates do not", PPH2.hit_bonus(_pph2_other), 0)
    c.true("...so their attacks fall into DIFFERENT groups under rule 04.03",
           _attack_key(_pph2_bearer, _pph2_bearer.weapons[0])
           != _attack_key(_pph2_other, _pph2_other.weapons[0]))

# ...and with the detachment off, the split disappears - the counter-proof that
# the two keys above differ BECAUSE of the Enhancement and not because a
# Fireblade and a Fire Warrior carry different guns anyway.
with none_fielded():
    c.eq("without Kauyon the bearer carries no bonus",
         PPH2.hit_bonus(_pph2_bearer), 0)
    _key_off = _attack_key(_pph2_bearer, _pph2_bearer.weapons[0])
with only("KAUYON_PLAYERS", players=("Player 1",)):
    _key_on = _attack_key(_pph2_bearer, _pph2_bearer.weapons[0])
# THE DECISIVE ONE: the SAME model and the SAME weapon, keyed with the
# detachment on and off. The comparison against a squadmate above could pass
# because a Fireblade and a Fire Warrior carry different guns; this cannot -
# nothing changes between the two lines except whether the Enhancement is live.
c.true("the Enhancement itself is what changes the bearer's group key",
       _key_on != _key_off)

# --- Prototype Weapon System, through the activation window ----------------
# Its choice lives on the TOKEN for one activation, so there are three things
# to see and a substring sees none of them: the window opens, the adjusted
# weapon really carries the chosen keyword, and the window closes again.
_pws_unit, _pws_foe, _pws_ctrl = _shoot_scene(COMMANDER_IN_COLDSTAR_BATTLESUIT,
                                              "1 Commander in Coldstar Battlesuit 1")
_pws_model = _pws_unit.models[0]
_pws_weapon = next(w for w in _pws_model.weapons if getattr(w, "range_in", 0))
with only("RETALIATION_CADRE_PLAYERS", players=(HUMAN2,)):
    E.grant(_pws_unit, "Prototype Weapon System", model=_pws_model)
    c.true("no choice is standing before the unit is selected to shoot",
           getattr(_pws_model, "prototype_weapon_choice", None) is None)
    _pws_model.prototype_weapon_choice = PWS2.LETHAL_HITS
    _adj = PWS2.adjusted_weapon(_pws_weapon, _pws_model)
    c.true("the chosen keyword lands on the weapon the shooting step uses",
           _adj.lethal_hits and not _pws_weapon.lethal_hits)
    c.true("...on a COPY, so the shared profile is never mutated",
           _adj is not _pws_weapon)
    # And the grouping half again: the choice is per model.
    c.true("the bearer's attacks carry its choice into the group key",
           PWS2.attack_key(_pws_model) != PWS2.attack_key(_pws_foe.models[0]))


# --- 12. What each shipped list SAYS it buys, against what LANDS ------------
print("\n12. The four lists: file against reality")

# Newly possible after the army-list rework: ArmyList.enhancement_names() reads
# what the roster FILE buys, while E.granted_names() reads what actually ended
# up on a model. Either one alone is half an answer - a list that names an
# Enhancement nothing grants looks fine from the file, and a grant nobody asked
# for looks fine from the board. Set equality per list is the whole assertion,
# and it needs no table here to drift.
# DERIVED, not written down: a list arriving or being retired should cost this
# block nothing. A hardcoded tuple here is the same shape of second copy the
# army-list rework existed to remove, and it would fail as a KeyError - which is
# a crash, not a diagnosable check.
_TAU_LIST_KEYS = tuple(e.key for e in army_lists.lists_for("T'AU EMPIRE"))
_all_granted = set()
for _key in _TAU_LIST_KEYS:
    _entry = army_lists.get(_key)
    _said = sorted(_entry.enhancement_names())
    _landed = sorted(n for s in army_lists.preview_squads(_key, "Player 1")
                     for n in E.granted_names(s))
    _all_granted |= set(_landed)
    c.eq("%s grants exactly what its roster file buys" % _key, _landed, _said)
    c.true("...and every one of them is a registered Enhancement" % (),
           all(n in E.ENHANCEMENTS for n in _landed))

c.true("the four lists between them really buy something", len(_all_granted) > 0)


# --- 13. The seven no shipped list buys ------------------------------------
print("\n13. Dormant by roster, named rather than assumed")

# DORMANT BY CONSTRUCTION, not broken: every one of the nineteen is wired and
# tested above, and these seven simply have no carrier on the table. Which
# Enhancements a list buys is the LIST's statement, so this is pinned as a
# measured fact rather than "fixed" by inventing roster content - the same
# treatment the Experimental Prototype Cadre trio had before a list bought its
# three weapons, and the same the Aeldari twenty-eight have now.
#
# DERIVED, not transcribed: the dormant set is the registry minus what section
# 12 measured. A hand-written list of seven names would be a second copy of a
# fact that already exists, and it would go stale the moment a list bought one.
# Scoped to the T'AU nineteen through TAU_SPECS - the same scoping section 1
# uses. ALL_SETTINGS spans every faction in the registry, so filtering on it
# would sweep the Aeldari twenty-eight in here as well and this section would
# be reporting a different fact than its heading claims.
_TAU_NAMES = set(TAU_SPECS)
_tau_dormant = sorted(_TAU_NAMES - _all_granted)

c.eq("nine of the nineteen T'au Enhancements have no carrier", len(_tau_dormant), 9)
c.eq("...and these are they", _tau_dormant, sorted([
    "Admired Leader", "Coordinated Exploitation", "Exemplar of the Mont'ka",
    "Internal Grenade Racks", "Prototype Weapon System",
    "Puretide Engram Neurochip", "Strike Swiftly", "Student of Kauyon",
    "Supernova Launcher"]))
c.eq("...so ten DO have one", len(_TAU_NAMES) - len(_tau_dormant), 10)

# Each with its reason, and the reason is checkable rather than remembered.
_by_det = {}
for _n in _tau_dormant:
    _by_det.setdefault(E.get(_n).detachment, []).append(_n)
c.eq("three are Retaliation Cadre's, whose list buys only Starflare",
     sorted(_by_det.get("Retaliation Cadre", [])),
     ["Internal Grenade Racks", "Prototype Weapon System",
      "Puretide Engram Neurochip"])
c.eq("three are Mont'ka's, dropped when that roster was replaced",
     sorted(_by_det.get("Mont'ka", [])),
     ["Coordinated Exploitation", "Exemplar of the Mont'ka", "Strike Swiftly"])
# TWO went dormant together when the Prototypes list was retired: its Ethereal
# carried Admired Leader and one of its three Coldstars the Supernova Launcher.
# The Recon list fields Experimental Prototype Cadre too and buys the other two
# weapon Enhancements, so only the Launcher lost its bearer there.
c.eq("two are Auxiliary Cadre's - no list fields a Kroot Shaper, and the "
     "Ethereal that carried Admired Leader went with the Prototypes list",
     sorted(_by_det.get("Auxiliary Cadre", [])),
     ["Admired Leader", "Student of Kauyon"])
c.eq("...and one is Experimental Prototype Cadre's, for the same reason",
     sorted(_by_det.get("Experimental Prototype Cadre", [])), ["Supernova Launcher"])
c.true("...which is what its BEARER line asks for",
       "KROOT SHAPER" in E.get("Student of Kauyon").bearer_text)

# Dormant is about the ROSTER, not the wiring: each of the seven still grants
# and still activates when a unit that can bear it is given one by hand. Without
# this the section above would read as "seven are broken".
for _n in _tau_dormant:
    _spec = E.get(_n)
    # "KROOT SHAPER model only" wants a Shaper; "excluding KROOT SHAPER
    # models" wants anything but one - and a substring test for "KROOT SHAPER"
    # reads them as the same requirement, which picks the one model the second
    # forbids.
    _sheet = (KROOT_FLESH_SHAPER
              if _spec.bearer_text.startswith("KROOT SHAPER")
              else COMMANDER_IN_COLDSTAR_BATTLESUIT)
    _u = build(_sheet, owner="Player 2", name="dormant %s" % _n)
    E.grant(_u, _n)
    with only(_spec.setting):
        c.true("%s is dormant by roster, not by wiring" % _n, E.is_active(_u, _n))

c.finish()
