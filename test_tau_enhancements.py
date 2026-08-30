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

import io

import testkit as tk
from game import config
from game import enhancements as E
from game.factions import build_squad
from game.factions.tau_empire import (CADRE_FIREBLADE, COMMANDER_FARSIGHT,
                                      COMMANDER_IN_COLDSTAR_BATTLESUIT, CRISIS_FIREKNIFE,
                                      CRISIS_STARSCYTHE, GHOSTKEEL_BATTLESUIT,
                                      KROOT_CARNIVORES, KROOT_FLESH_SHAPER,
                                      PATHFINDER_TEAM, STEALTH_BATTLESUITS, STRIKE_TEAM,
                                      TAU_EMPIRE)

c = tk.Checks("T'au detachment Enhancements")


class settings_as:
    """Set config constants for one block and put them back - config is a
    module, so a test that forgets is a test that poisons every later one."""

    def __init__(self, **values):
        self.values = values

    def __enter__(self):
        self.old = {k: getattr(config, k) for k in self.values}
        for k, v in self.values.items():
            setattr(config, k, v)

    def __exit__(self, *exc):
        for k, v in self.old.items():
            setattr(config, k, v)


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
       before(_pregame_src, "self.redeploy_step.start(self, self._finish_deployment)",
              "if SCOUTS_BEFORE_FIRST_TURN_ROLLOFF:"))
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


class granting:
    """Populate game/army_lists.py's Enhancement table for one block.

    The 2026-08-30 T'au roster buys NO Enhancement - it names none, and every
    character in it is priced at base cost. So the MECHANISM (one Enhancement
    per declared detachment, bearer found by datasheet, points on the squad,
    answerable at preview time before anything reaches config) is driven with a
    table written here rather than through the roster. That is deliberate: a
    section that only asserted "the list grants nothing" would go quiet exactly
    where the grant used to be tested."""

    def __init__(self, table):
        self.table = table

    def __enter__(self):
        self.old = army_lists._TAU_LIST_ENHANCEMENTS
        army_lists._TAU_LIST_ENHANCEMENTS = dict(self.table)

    def __exit__(self, *exc):
        army_lists._TAU_LIST_ENHANCEMENTS = self.old


def granted_for(names, table):
    with fielding(names), granting(table):
        squads = army_lists.preview_squads("tau", "Player 1")
        return sorted(n for s in squads for n in E.granted_names(s)), \
            sum(s.points or 0 for s in squads)


# What the roster as supplied does: nothing, and its points are its units'.
_names, _points = granted_for(["Kauyon", "Advanced Acquisition Cadre"],
                              army_lists._TAU_LIST_ENHANCEMENTS)
c.eq("the supplied list hands out no Enhancement - it names none", _names, [])
c.eq("...so its 2030 pts are its units and nothing else", _points, 2030)
c.eq("...and the table says so by being empty", army_lists._TAU_LIST_ENHANCEMENTS, {})

# The mechanism, driven with a table of its own.
_TABLE = {
    "Kauyon": ("Exemplar of the Kauyon", "Cadre Fireblade"),
    "Advanced Acquisition Cadre": ("Negation Emitters", "Stealth Battlesuits"),
    "Auxiliary Cadre": ("Admired Leader", "Cadre Fireblade"),
    "Retaliation Cadre": ("Starflare Ignition System", "Riptide Battlesuit"),
}
c.eq("a declared detachment hands out its Enhancement",
     granted_for(["Kauyon"], _TABLE)[0], ["Exemplar of the Kauyon"])
c.eq("...and one the list does not declare hands out nothing",
     granted_for(["Mont'ka"], _TABLE)[0], [])
c.eq("two declared detachments hand out two Enhancements",
     granted_for(["Kauyon", "Advanced Acquisition Cadre"], _TABLE)[0],
     ["Exemplar of the Kauyon", "Negation Emitters"])
c.eq("...and the points land on the army",
     granted_for(["Kauyon", "Advanced Acquisition Cadre"], _TABLE)[1], 2030 + 20 + 15)

# The bearer is the right unit, not just "somebody" - and _find_by_datasheet()
# sees through 19.01, which is the half that is easy to get wrong: by the time
# the grant runs, the Cadre Fireblade is INSIDE a Breacher Team.
with fielding(["Kauyon"]), granting(_TABLE):
    _sq = army_lists.preview_squads("tau", "Player 1")
    _bearers = [m.profile.name for s in _sq
                for m in E.enhancement_models(s, "Exemplar of the Kauyon")]
    c.eq("Exemplar of the Kauyon lands on a Cadre Fireblade merged into his unit",
         _bearers, ["Cadre Fireblade"])
    c.eq("...whose unit is the Breacher Team he leads",
         [s.name for s in _sq if E.granted_names(s)],
         ["1 Breacher Team 1 + Cadre Fireblade"])
with fielding(["Advanced Acquisition Cadre"]), granting(_TABLE):
    _sq = army_lists.preview_squads("tau", "Player 1")
    c.eq("Negation Emitters lands on the Stealth Battlesuits",
         [s.name for s in _sq if E.granted_names(s)], ["1 Stealth Battlesuits 1"])

# A bearer the roster does not field is skipped rather than crashing - the
# documented legal outcome (Experimental Prototype Cadre had it before this
# roster, and any table entry naming a unit that left has it now).
c.eq("an Enhancement whose bearer is not in the list hands out nothing",
     granted_for(["Mont'ka"],
                 {"Mont'ka": ("Exemplar of the Mont'ka", "Commander Farsight")})[0], [])


# --- 10. Source guards ----------------------------------------------------
print("\n10. Source guards")

# The grant reads the LIST's declared detachments, not config - preview_squads()
# builds the army screen's tile before anything is applied to config.
_army_src = io.open("game/army_lists.py", encoding="utf-8").read()
c.true("the grant reads the list's own detachments",
       "for detachment in get(TAU_ARMY).detachments:" in _army_src)
c.true("...and not the config constants",
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
    "enh_prototype_weapons.apply_all(state.all_squads(), game_log=game_log)",
    "_student_of_kauyon_step.start(_player_squads(state, _owner), _owner)",
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

c.finish()
