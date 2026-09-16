"""The 2026-09 Ork codex's specialists (stage E3c): Flash Gitz, Tankbustas.

Run: python test_ork_specialists.py

Every ability through the real controller or seam that reads it:
  * Finderz Keeperz (game/finderz_keeperz.py) through a real ShootingController's
    adjuster chain - all four objective states, the reactive shot, a melee weapon;
  * Rokkit Barrage (game/rokkit_barrage.py) - the fourth carrier of
    game/battle_shock_after_shooting.py, with a real BattleShockController, the
    human's board pick and the AI's deterministic answer (0 API calls);
  * Bomb Squigs (game/bomb_squigs.py) - every refusal reason, once per turn, twice
    per battle, the D6 gate then the D3, the 06.02 drain, a single-model victim,
    the AI, the Decline that spends nothing, and a real MovementController's
    confirmed Normal move feeding it;
  * Pulsa Rokkit (game/pulsa_rokkit.py) - offered at start_shooting() of a real
    ShootingController, the mark, +1 AP and [LETHAL HITS] only against the marked
    MONSTER/VEHICLE unit, the phase reset, the AI;
  * game/weapon_profiles.py's valued_profiles() - how every AI estimate reads a
    multi-profile weapon.
Plus the two datasheets, the retirements and main.py's wiring at the source.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import ast                                                           # noqa: E402
import io                                                            # noqa: E402

import testkit as tk                                                 # noqa: E402
from testkit import (Checks, GameState, RecordingDice, build, line_up,  # noqa: E402
                     options_of, pick_option, script, shooting_scene)

from ai import deployment_ai                                         # noqa: E402
from ai.agent_driver import battle_shock_target_choice               # noqa: E402
from game import (activation_state, bomb_squigs, combat_focus, finderz_keeperz,  # noqa: E402
                  pulsa_rokkit, rokkit_barrage, unit_pick, weapon_profiles)
from game import weapons as weapons_mod                              # noqa: E402
from game.attached_units import attach                               # noqa: E402
from game.battle_shock import BattleShockController                  # noqa: E402
from game.decision import DecisionManager                            # noqa: E402
from game.dice_notation import describe as describe_dice             # noqa: E402
from game.dice import DiceManager                                    # noqa: E402
from game.face_of_death import FaceOfDeathController                 # noqa: E402
from game.factions import build_squad                                # noqa: E402
from game.factions import orks as ork                                # noqa: E402
from game.factions.death_guard import MYPHITIC_BLIGHT_HAULER         # noqa: E402
from game.factions.tau_empire import DEVILFISH, KROOT_CARNIVORES, STRIKE_TEAM  # noqa: E402
from game.movement import MovementController                         # noqa: E402
from game.panicked_quarry import PanickedQuarryController            # noqa: E402
from game.shooting import ShootingController                         # noqa: E402
from game.squad import Squad, tank_hunters_modifiers                 # noqa: E402
from game.token import Token                                         # noqa: E402
from game.turn import PHASES, PHASE_MOVEMENT, PHASE_SHOOTING, TurnTracker  # noqa: E402
from game.units import UnitProfile                                   # noqa: E402
from game.weapons import WeaponProfile                               # noqa: E402

c = Checks("Ork specialists (2026-09 codex)")
HERE = os.path.dirname(os.path.abspath(__file__))
HUMAN, FOE = "Player 1", "Player 2"


def weapon_named(model, name):
    return next((w for w in model.weapons if w.name == name), None)


def tracker(phase, owner=HUMAN, battle_round=2):
    tt = TurnTracker(first_player=owner)
    tt.started = True
    tt.phase_index = PHASES.index(phase)
    tt.turn_owner = owner
    tt.set_active(owner)
    tt.battle_round = battle_round
    return tt


def names(chain):
    return [p.name for p in chain]


def alive(squad):
    return sum(1 for m in squad.models if not m.is_dead())


class _Area:
    """A terrain area reduced to what objectives.py asks of it."""

    def __init__(self, x, y):
        self.x, self.y = x, y

    def distance_to_model(self, m):
        return ((m.x_in - self.x) ** 2 + (m.y_in - self.y) ** 2) ** 0.5


class _Objective:
    def __init__(self, x, y):
        self.terrain_area = _Area(x, y)


# ===========================================================================
print("\n1. the two datasheets")
# ===========================================================================
_g5 = build(ork.FLASH_GITZ, HUMAN, name="1 Flash Gitz 1")
_g10 = build(ork.FLASH_GITZ, HUMAN, name="1 Flash Gitz 2", composition_index=1)
c.eq("Flash Gitz: 1 Kaptin + 4 Flash Gitz, or + 9", (len(_g5.models), len(_g10.models)), (5, 10))
c.eq("...the Kaptin leads", [m.profile.name for m in _g5.models[:2]], ["Kaptin", "Flash Git"])
c.eq("every Git carries Choppa + Snazzgun, the Snazzgun as its FIRST profile (Cutta)",
     {tuple(sorted(w.name for w in m.weapons)) for m in _g10.models}, {("Choppa", "Snazzgun - Cutta")})
_snazz = weapon_named(_g5.models[0], "Snazzgun - Cutta")
c.eq("the Snazzgun is a three-profile chain", names(weapon_profiles.profiles(_snazz)),
     ["Snazzgun - Cutta", "Snazzgun - Dakka", "Snazzgun - Kill Shot"])
_cutta, _dakka, _kill = weapon_profiles.profiles(_snazz)
c.eq("Cutta 12\" A1 S9 AP-3, [HAZARDOUS] [MELTA 2]",
     (_cutta.range_in, _cutta.attacks, _cutta.strength, _cutta.ap, _cutta.hazardous, _cutta.melta), (12, 1, 9, -3, True, 2))
c.eq("...D3+2 damage", describe_dice(_cutta.damage_notation), "D3+2")
c.eq("Dakka 24\" A3 S6 AP-1 D2, [SUSTAINED HITS 1], not hazardous",
     (_dakka.range_in, _dakka.attacks, _dakka.strength, _dakka.ap, _dakka.damage, _dakka.sustained_hits,
      bool(_dakka.hazardous)), (24, 3, 6, -1, 2, 1, False))
c.true("...with [LETHAL HITS] only against non-MONSTER/VEHICLE targets",
       any(k[0] == "lethal_hits" for k in _dakka.conditional_keywords))
c.eq("Kill Shot 36\" A2 S8 AP-2 D2, [HAZARDOUS]",
     (_kill.range_in, _kill.attacks, _kill.strength, _kill.ap, _kill.damage, _kill.hazardous), (36, 2, 8, -2, 2, True))
_choppa = weapon_named(_g5.models[0], "Choppa")
c.eq("the Choppa both specialists print is the Boyz' row with A4", (_choppa.attacks, _choppa.ap), (4, -1))
c.true("...a subclass of it", isinstance(_choppa, weapons_mod.ChoppaProfile))
c.eq("Flash Git statline T/W/Sv/BS", tuple(getattr(_g5.models[1].profile, a) for a in
                                          ("toughness", "wounds", "armor_save", "ballistic_skill")), (5, 3, "4+", "4+"))
c.true("...Finderz Keeperz on every Git", all(m.profile.finderz_keeperz for m in _g10.models))
c.eq("points: 105 / 210 for the first two units", (_g5.points, _g10.points), (105, 210))
c.eq("keywords", ork.FLASH_GITZ.keywords, ("INFANTRY", "EXPLOSIVES"))

_tb = build(ork.TANKBUSTAS, HUMAN, name="1 Tankbustas 1")
c.eq("Tankbustas: 1 Nob + 5 Tankbustas", [m.profile.name for m in _tb.models], ["Nob"] + ["Tankbusta"] * 5)
c.eq("the Nob: Choppa and two Rokkit Pistols", sorted(w.name for w in _tb.models[0].weapons),
     ["Choppa", "Rokkit Pistol", "Rokkit Pistol"])
c.eq("the Nob is W3 on 40mm and leads", (_tb.models[0].profile.wounds, _tb.models[0].profile.base_radius_in,
                                         _tb.models[0].profile.squad_leader), (3, 0.79, True))
c.eq("a Tankbusta: Busta Rokkit Launcha (Standard first) and Gitstikka", sorted(w.name for w in _tb.models[1].weapons),
     ["Busta Rokkit Launcha - Standard", "Gitstikka"])
_launcha = weapon_named(_tb.models[1], "Busta Rokkit Launcha - Standard")
_std, _hunt = weapon_profiles.profiles(_launcha)
c.eq("Standard 24\" A2 S10 AP-2 D3", (_std.range_in, _std.attacks, _std.strength, _std.ap, _std.damage), (24, 2, 10, -2, 3))
c.eq("Hunter 24\" A3 S12 AP-2 D3", (_hunt.range_in, _hunt.attacks, _hunt.strength, _hunt.ap, _hunt.damage),
     (24, 3, 12, -2, 3))
c.true("...and only the Hunter profile is a Hunter", weapon_profiles.is_hunter(_hunt) and not weapon_profiles.is_hunter(_std))
c.eq("Tankbusta statline T/W/Sv/BS/WS", tuple(getattr(_tb.models[1].profile, a) for a in
                                             ("toughness", "wounds", "armor_save", "ballistic_skill", "weapon_skill")),
     (5, 2, "4+", "4+", "3+"))
c.true("Rokkit Barrage and Bomb Squigs on every Tankbusta",
       all(m.profile.rokkit_barrage and m.profile.bomb_squigs for m in _tb.models))
c.eq("points: 145, 145, then 155 from the third unit",
     [build_squad(ork.TANKBUSTAS, HUMAN, name="t%d" % i, unit_index=i).points for i in (1, 2, 3)],
     [145, 145, 155])
c.eq("Flash Gitz from the third unit: 135 / 240",
     [build_squad(ork.FLASH_GITZ, HUMAN, name="g%d" % n, unit_index=3, composition_index=n).points for n in (0, 1)],
     [135, 240])
_sh = build(ork.TANKBUSTAS, HUMAN, name="sh", choices={"Nob": {ork.TANKBUSTAS_NOB_SMASH_HAMMER: 1}})
c.eq("the Nob's Smash Hammer takes ONE pistol", sorted(w.name for w in _sh.models[0].weapons),
     ["Choppa", "Rokkit Pistol", "Smash Hammer - Standard"])
_hammer = weapon_named(_sh.models[0], "Smash Hammer - Standard")
c.eq("...and prints a Hunter profile too", names(weapon_profiles.profiles(_hammer)),
     ["Smash Hammer - Standard", "Smash Hammer - Hunter"])
_extra = build(ork.TANKBUSTAS, HUMAN, name="ex", choices={"Tankbusta": {ork.TANKBUSTAS_ADD_BUSTA_ROKKIT_LAUNCHA: 1}})
c.eq("one Tankbusta may add a second launcha", sum(1 for m in _extra.models
                                                    if sum(1 for w in m.weapons if w.name.startswith("Busta")) == 2), 1)
_pul = build(ork.TANKBUSTAS, HUMAN, name="pu", gear={"Tankbusta": [ork.TANKBUSTAS_PULSA_ROKKIT]})
c.eq("the Pulsa Rokkit is gear on exactly one Tankbusta", sum(1 for m in _pul.models if m.pulsa_rokkit), 1)
c.true("...and only Tankbusta models may carry it", not _pul.models[0].pulsa_rokkit)
c.eq("keywords", ork.TANKBUSTAS.keywords, ("INFANTRY", "EXPLOSIVES"))


# ===========================================================================
print("\n2. Finderz Keeperz (Flash Gitz)")
# ===========================================================================
def gitz_scene(objectives=(), reactive=False):
    scene = shooting_scene(ork.FLASH_GITZ, STRIKE_TEAM, attacker_owner=HUMAN, gap=10.0)
    sc = scene["shooting"]
    sc.objectives = list(objectives)
    sc.active_squad = scene["attacker"]
    sc._reactive = reactive
    shooter = scene["attacker"].models[0]
    return scene, sc, [(shooter, weapon_named(shooter, "Snazzgun - Cutta"))]


_NEAR_GITZ = _Objective(20.0, 20.0)
_NEAR_TARGET = _Objective(26.0, 30.0)
_FAR = _Objective(60.0, 60.0)
for _label, _objs, _want in (("the Gitz are within range of an objective", (_NEAR_GITZ,), -4),
                             ("the TARGET is within range of an objective", (_NEAR_TARGET,), -4),
                             ("both are - still one +1 AP", (_NEAR_GITZ, _NEAR_TARGET), -4),
                             ("neither is", (_FAR,), -3),
                             ("no objectives at all", (), -3)):
    _s, _sc, _pairs = gitz_scene(_objs)
    c.eq("through the real adjuster chain: %s" % _label, _sc._adjusted_weapon(_pairs, _s["target"]).ap, _want)
_s, _sc, _pairs = gitz_scene((_NEAR_GITZ,))
c.eq("the carried weapon is not mutated", _pairs[0][1].ap, -3)
_s, _sc, _pairs = gitz_scene((_NEAR_GITZ,), reactive=True)
c.eq("a reactive shot is not 'your Shooting phase'", _sc._adjusted_weapon(_pairs, _s["target"]).ap, -3)
_s, _sc, _pairs = gitz_scene((_NEAR_GITZ,))
c.eq("a melee weapon never gains it", finderz_keeperz.adjusted_weapon(
    weapon_named(_s["attacker"].models[0], "Choppa"), _s["attacker"], _s["target"], (_NEAR_GITZ,)).ap, -1)
c.true("a unit without it gains nothing", not finderz_keeperz.applies(_s["target"], _s["attacker"], (_NEAR_TARGET,)))
_led = attach(build(ork.PAINBOY, HUMAN, name="1 Painboy 1"), build(ork.FLASH_GITZ, HUMAN, name="1 Flash Gitz 9"),
              game_state=GameState())
c.true("a Painboy supporting the Gitz does not strip it (rule 19.04)", finderz_keeperz.has_ability(_led))


# ===========================================================================
print("\n3. Rokkit Barrage (Tankbustas)")
# ===========================================================================
def barrage_scene(auto=(), target_pick=None):
    st = GameState()
    tt = tracker(PHASE_SHOOTING)
    tank = line_up(build(ork.TANKBUSTAS, HUMAN, name="1 Tankbustas 1"), x=10.0, y=20.0)
    team = line_up(build(STRIKE_TEAM, FOE, name="2 Strike Team 1"), x=10.0, y=30.0)
    # Named to sort AFTER the Strike Team: the AI policy checks below need the right
    # answer to be neither the first by name nor the richer unit, or a broken
    # ranking would pass by accident (found by ab_ork_specialists.py).
    kroot = line_up(build(KROOT_CARNIVORES, FOE, name="2 Zeta Kroot 1"), x=10.0, y=40.0)
    fish = line_up(build(DEVILFISH, FOE, name="2 Devilfish 1"), x=40.0, y=30.0)
    for sq in (tank, team, kroot, fish):
        for m in sq.models:
            st.add_token(m)
    dice, dm = RecordingDice(), DecisionManager()
    bs = BattleShockController(game_log=tk.Log(), dice_manager=dice, turn_tracker=tt, all_tokens=st.tokens)
    ctrl = rokkit_barrage.RokkitBarrageController(battle_shock_controller=bs, decision_manager=dm, game_log=tk.Log(),
                                                  auto_players=auto, target_pick=target_pick)
    return dict(state=st, tank=tank, team=team, kroot=kroot, fish=fish, dice=dice, decision=dm, bs=bs, ctrl=ctrl)


_r = barrage_scene()
c.true("one unit hit: its test starts at once, no prompt", _r["ctrl"].offer_after_shooting(_r["tank"], [_r["fish"]])
       and not _r["decision"].is_pending)
c.true("...a VEHICLE is a legal choice (no MONSTER/VEHICLE exclusion, unlike Panicked Quarry)",
       _r["bs"].rolling_squad is _r["fish"])
c.true("...named Rokkit Barrage on the dice, at -1", bool(_r["dice"].rolled)
       and "Rokkit Barrage" in _r["dice"].rolled[-1][0] and "-1 to the test" in _r["dice"].rolled[-1][0])
_r = barrage_scene()
_r["ctrl"].offer_after_shooting(_r["tank"], [_r["team"], _r["kroot"]])
c.true("two units hit: a human picks on the board", _r["decision"].is_pending
       and unit_pick.pending(_r["decision"], _r["state"].tokens) is not None)
c.true("...with no Decline - 'select' and 'makes' are not optional",
       not any(lab in ("Decline", "Cancel") for lab in options_of(_r["decision"])))
c.true("choosing the Kroot", pick_option(_r["decision"], _r["kroot"].name))
c.true("...tests the Kroot", _r["bs"].rolling_squad is _r["kroot"])
_r = barrage_scene()
c.eq("a unit without Rokkit Barrage offers nothing",
     _r["ctrl"].offer_after_shooting(_r["team"], [_r["kroot"]]), False)
for _m in _r["tank"].models:
    _m.current_wounds = 0
c.true("...nor does a Tankbustas unit whose every model is dead", not rokkit_barrage.has_rokkit_barrage(_r["tank"]))

_r = barrage_scene(auto=(HUMAN,), target_pick=lambda s, cands: battle_shock_target_choice(s, cands))
# The Strike Team (70 pts, first by name) is shocked, so the right answer is the
# Kroot (65 pts, second by name): neither name order nor points alone reach it.
_r["team"].battle_shocked = True
_r["ctrl"].offer_after_shooting(_r["tank"], [_r["team"], _r["kroot"]])
c.true("the AI answers without a prompt", not _r["decision"].is_pending and _r["bs"].rolling_squad is not None)
c.true("...and tests the unit NOT already battle-shocked (a pass would unshock the other)",
       _r["bs"].rolling_squad is _r["kroot"])
_r = barrage_scene()
_on_kroot = [_Objective(15.0, 40.0)]
c.true("AI policy: an unshocked unit on an objective first (the cheaper one, second by name)",
       battle_shock_target_choice(_r["tank"], [_r["team"], _r["kroot"]], _on_kroot) is _r["kroot"])
_late = build(STRIKE_TEAM, FOE, name="2 Zzz Strike Team 1")
c.true("(scene) the later-named unit is the richer one", (_late.points or 0) > (_r["kroot"].points or 0)
       and _late.name > _r["kroot"].name)
c.true("...then the more valuable unit", battle_shock_target_choice(_r["tank"], [_r["kroot"], _late]) is _late)
c.eq("...and nobody from an empty list", battle_shock_target_choice(_r["tank"], []), None)
for _cls in (FaceOfDeathController, PanickedQuarryController):
    _inst = _cls()
    c.true("%s is unchanged: no auto players, no pick" % _cls.__name__,
           "Player 1" not in _inst.auto_players and "Player 2" not in _inst.auto_players and _inst.target_pick is None)


# ===========================================================================
print("\n4. Bomb Squigs (Tankbustas)")
# ===========================================================================
def squig_scene(auto=(), phase=PHASE_MOVEMENT, turn_owner=HUMAN, foes=(STRIKE_TEAM,), foe_y=28.0,
                visible=None, target_pick=None, battle_round=2):
    st = GameState()
    tt = tracker(phase, turn_owner, battle_round)
    # Two rows of three, 1.8" apart: the Nob's 40mm and a Tankbusta's 32mm overlap at
    # line_up()'s 1.4", and a real confirm_move() refuses a move that ends on a model.
    tank = build(ork.TANKBUSTAS, HUMAN, name="1 Tankbustas 1")
    for i, m in enumerate(tank.models):
        row, col = divmod(i, 3)
        m.x_in, m.y_in = 10.0 + col * 1.8, 20.0 + row * 1.8
    enemies = []
    for i, sheet in enumerate(foes):
        enemies.append(line_up(build(sheet, FOE, name="2 %s %d" % (sheet.name, i)),
                               x=10.0 + i * 22.0, y=foe_y + 1.8, spacing=2.0))
    for sq in [tank] + enemies:
        for m in sq.models:
            st.add_token(m)
    dice, dm = RecordingDice(), DecisionManager()
    ctrl = bomb_squigs.BombSquigsController(dice_manager=dice, decision_manager=dm, game_log=tk.Log(), game_state=st,
                                            auto_players=auto, target_pick=target_pick, turn_tracker=tt,
                                            visible=visible)
    return dict(state=st, turn=tt, tank=tank, foes=enemies, dice=dice, decision=dm, ctrl=ctrl)


def ack(scene):
    scene["dice"].acknowledge()
    return scene["ctrl"].on_dice_acknowledged()


def drain(ctrl):
    guard = 0
    while ctrl.pending_damage_choice and guard < 50:
        ctrl.choose_damage_model(sorted(ctrl.pending_damage_choice, key=lambda m: m.id)[0])
        guard += 1
    return guard


_q = squig_scene()
c.eq("a Normal move in your Movement phase, a foe 8\" away: usable", _q["ctrl"].why_not(_q["tank"]), None)
c.eq("an Advance does not throw one", _q["ctrl"].why_not(_q["tank"], "advance"), "not a normal move")
c.eq("...nor a Fall Back", _q["ctrl"].why_not(_q["tank"], "fall_back"), "not a normal move")
c.eq("a unit without it", _q["ctrl"].why_not(_q["foes"][0]), "this unit has no Bomb Squigs")
c.eq("not in the Shooting phase", squig_scene(phase=PHASE_SHOOTING)["ctrl"].why_not(_q["tank"]),
     "not your Movement phase")
_o = squig_scene(turn_owner=FOE)
c.eq("not in the opponent's Movement phase", _o["ctrl"].why_not(_o["tank"]), "not your Movement phase")
_f = squig_scene(foe_y=40.0)
c.eq("no enemy within 12\"", _f["ctrl"].why_not(_f["tank"]), "no visible enemy unit within 12\"")
_v = squig_scene(visible=lambda model, squad: False)
c.eq("...or none VISIBLE", _v["ctrl"].why_not(_v["tank"]), "no visible enemy unit within 12\"")
c.eq("turn numbers are 1-based (the save keeps only truthy values)", bomb_squigs.turn_number(tracker(PHASE_MOVEMENT,
                                                                                                   battle_round=1)), 1)

_q = squig_scene()
c.true("a human is asked", _q["ctrl"].on_move_finished(_q["tank"], "normal") and _q["decision"].is_pending)
c.eq("...which unit, or Decline", options_of(_q["decision"]), ["Bomb Squigs: %s" % _q["foes"][0].name, "Decline"])
c.true("...a board pick", unit_pick.pending(_q["decision"], _q["state"].tokens) is not None)
pick_option(_q["decision"], "Decline")
c.true("Decline spends no token and rolls nothing", _q["tank"].bomb_squigs_used == 0 and not _q["dice"].rolled)
script(2)
_q["ctrl"].on_move_finished(_q["tank"], "normal")
pick_option(_q["decision"], "Bomb Squigs:")
c.eq("choosing a unit spends a token and stamps the turn",
     (_q["tank"].bomb_squigs_used, _q["tank"].bomb_squigs_turn), (1, bomb_squigs.turn_number(_q["turn"])))
c.eq("...and rolls one D6 named Bomb Squigs, 3+", (_q["dice"].rolled[-1][0], len(_q["dice"].rolled[-1][1]),
                                                   _q["dice"].success_threshold), ("Bomb Squigs", 1, 3))
ack(_q)
c.true("a 2 fizzles: no D3, nothing open", len(_q["dice"].rolled) == 1 and not _q["ctrl"].is_busy)
c.eq("...and the token stays spent ('removing one each time this ability is used')", _q["tank"].bomb_squigs_used, 1)
c.eq("once per turn", _q["ctrl"].why_not(_q["tank"]), "already used this turn")
_q["turn"].battle_round = 3
c.eq("...back next turn", _q["ctrl"].why_not(_q["tank"]), None)
_before = alive(_q["foes"][0])
script(5, 3)
_q["ctrl"].on_move_finished(_q["tank"], "normal")
pick_option(_q["decision"], "Bomb Squigs:")
ack(_q)
c.eq("a 5 rolls the D3", _q["dice"].rolled[-1][0], "Bomb Squigs - mortal wounds")
ack(_q)
c.true("a multi-model target parks the 06.02 allocation for its owner", bool(_q["ctrl"].pending_damage_choice))
drain(_q["ctrl"])
c.eq("...and all three mortal wounds land", _before - alive(_q["foes"][0]), 3)
c.true("...nothing is left open", _q["ctrl"].pending_damage_choice is None and not _q["ctrl"].is_busy)
_q["turn"].battle_round = 4
c.eq("twice per battle, per unit", _q["ctrl"].why_not(_q["tank"]), "no Bomb Squig tokens left")
_other = build(ork.TANKBUSTAS, HUMAN, name="1 Tankbustas 2")
c.eq("...a second Tankbustas unit has its own two", bomb_squigs.squigs_left(_other), 2)

_s1 = squig_scene(auto=(HUMAN,), foes=(DEVILFISH,))
_fish = _s1["foes"][0].models[0]
_w0 = _fish.current_wounds
script(6, 2)
c.true("the AI throws without a prompt", _s1["ctrl"].on_move_finished(_s1["tank"], "normal")
       and not _s1["decision"].is_pending)
ack(_s1)
ack(_s1)
c.eq("a single-model target takes the wounds at once", _w0 - _fish.current_wounds, 2)
_s1["turn"].battle_round = 3
c.eq("...and its finished allocation does not block the second token next turn", _s1["ctrl"].why_not(_s1["tank"]), None)

_s2 = squig_scene(auto=(HUMAN,), foes=(STRIKE_TEAM, KROOT_CARNIVORES), foe_y=26.0,
                  target_pick=lambda squad, cands: next(u for u in cands if "Kroot" in u.name))
_s2["foes"][1].models[0].x_in = 20.0
script(6)
_s2["ctrl"].on_move_finished(_s2["tank"], "normal")
c.eq("the AI's target is the injected ranking's pick", _s2["dice"].target_name, _s2["foes"][1].name)
c.true("bomb_squigs_used and bomb_squigs_turn survive a save",
       {"bomb_squigs_used", "bomb_squigs_turn"} <= set(activation_state.SQUAD_FLAGS))

# The trigger through a REAL MovementController's confirmed Normal move.
_e = squig_scene(auto=(HUMAN,))
_mover = MovementController([], tk.Log(), HUMAN, DiceManager(), _e["turn"], _e["state"].tokens)
_mover.on_move_finished.append(_e["ctrl"].on_move_finished)
_mover.select(_e["tank"].models[0])
_mover.start_move()
for _m in _e["tank"].models:
    _m.x_in += 2.0
script(6, 1)
_mover.confirm_move()
c.eq("(live) the real move was accepted", _mover.errors, [])
c.true("a confirmed Normal move throws the squig through the hook", _e["tank"].bomb_squigs_used == 1
       and _e["dice"].rolled and _e["dice"].rolled[-1][0] == "Bomb Squigs")


# ===========================================================================
print("\n5. Pulsa Rokkit (Tankbustas)")
# ===========================================================================
def pulsa_scene(auto=(), turn_owner=HUMAN, gear=True, fish_y=30.0, target_pick=None):
    st = GameState()
    tt = tracker(PHASE_SHOOTING, turn_owner)
    tank = line_up(build(ork.TANKBUSTAS, HUMAN, name="1 Tankbustas 1",
                         gear={"Tankbusta": [ork.TANKBUSTAS_PULSA_ROKKIT]} if gear else None), x=10.0, y=20.0)
    fish = line_up(build(DEVILFISH, FOE, name="2 Devilfish 1"), x=12.0, y=fish_y)
    team = line_up(build(STRIKE_TEAM, FOE, name="2 Strike Team 1"), x=26.0, y=30.0, spacing=1.2)
    for sq in (tank, fish, team):
        for m in sq.models:
            st.add_token(m)
    dm, log = DecisionManager(), tk.Log()
    ctrl = pulsa_rokkit.PulsaRokkitController(decision_manager=dm, turn_tracker=tt, game_log=log, game_state=st,
                                              auto_players=auto, target_pick=target_pick)
    sc = ShootingController(dice_manager=RecordingDice(), turn_tracker=tt, all_tokens=st.tokens, decision_manager=dm,
                            game_log=log, obstacles=[], pulsa_rokkit=ctrl)
    return dict(state=st, turn=tt, tank=tank, fish=fish, team=team, decision=dm, ctrl=ctrl, shooting=sc)


_p = pulsa_scene()
_shooter = next(m for m in _p["tank"].models if weapon_named(m, "Busta Rokkit Launcha - Standard"))
_pairs = [(_shooter, weapon_named(_shooter, "Busta Rokkit Launcha - Standard"))]
c.eq("only MONSTER/VEHICLE units within 24\" are candidates", pulsa_rokkit.targets(_p["tank"], _p["state"].tokens),
     [_p["fish"]])
_p["shooting"].start_shooting(_p["tank"])
c.true("selected to shoot, a human is asked", _p["decision"].is_pending)
c.eq("...which unit, or Decline", options_of(_p["decision"]), ["Pulsa Rokkit: 2 Devilfish 1", "Decline"])
c.true("...a board pick", unit_pick.pending(_p["decision"], _p["state"].tokens) is not None)
_adj = _p["shooting"]._adjusted_weapon(_pairs, _p["fish"])
c.eq("before the answer: nothing", (_adj.ap, bool(_adj.lethal_hits)), (-2, False))
pick_option(_p["decision"], "Pulsa Rokkit:")
c.true("marked", _p["ctrl"].marked_target(_p["tank"]) is _p["fish"])
_adj = _p["shooting"]._adjusted_weapon(_pairs, _p["fish"])
c.eq("against the marked unit, through the real chain: +1 AP and [LETHAL HITS]", (_adj.ap, bool(_adj.lethal_hits)),
     (-3, True))
_adj = _p["shooting"]._adjusted_weapon(_pairs, _p["team"])
c.eq("...against any other unit: nothing", (_adj.ap, bool(_adj.lethal_hits)), (-2, False))
c.eq("...and the carried weapon is not mutated", (_pairs[0][1].ap, bool(_pairs[0][1].lethal_hits)), (-2, False))
_p["shooting"]._reactive = True
c.eq("a reactive shot gets nothing", _p["shooting"]._adjusted_weapon(_pairs, _p["fish"]).ap, -2)
_p["shooting"]._reactive = False
c.eq("once marked, not asked again this phase", _p["ctrl"].why_not(_p["tank"]), "already marked a unit this phase")
_p["ctrl"].reset_phase()
c.true("the mark ends with the phase", _p["ctrl"].marked_target(_p["tank"]) is None
       and _p["ctrl"].why_not(_p["tank"]) is None)
c.eq("an infantry unit cannot be marked", _p["ctrl"].mark(_p["tank"], _p["team"]), False)

_p = pulsa_scene()
_p["shooting"].start_shooting(_p["tank"])
pick_option(_p["decision"], "Decline")
c.true("Decline marks nothing", _p["ctrl"].marked_target(_p["tank"]) is None)
c.eq("not in the opponent's Shooting phase", pulsa_scene(turn_owner=FOE)["ctrl"].why_not(_p["tank"]),
     "not your Shooting phase")
_ng = pulsa_scene(gear=False)
c.eq("no Pulsa Rokkit bought, no ability", _ng["ctrl"].why_not(_ng["tank"]), "no model carries a Pulsa Rokkit")
_dead = pulsa_scene()
next(m for m in _dead["tank"].models if m.pulsa_rokkit).current_wounds = 0
c.eq("...and it goes with its bearer", _dead["ctrl"].why_not(_dead["tank"]), "no model carries a Pulsa Rokkit")
_far = pulsa_scene(fish_y=60.0)
c.eq("no vehicle within 24\"", _far["ctrl"].why_not(_far["tank"]), "no enemy MONSTER/VEHICLE unit within 24\"")
_ai = pulsa_scene(auto=(HUMAN,), target_pick=lambda squad, cands: cands[0])
_ai["shooting"].start_shooting(_ai["tank"])
c.true("the AI marks without a prompt", not _ai["decision"].is_pending
       and _ai["ctrl"].marked_target(_ai["tank"]) is _ai["fish"])


# ===========================================================================
print("\n6. valued_profiles(): how an AI estimate reads a multi-profile weapon")
# ===========================================================================
_fish_sq = build(DEVILFISH, FOE, name="vf")
_team_sq = build(STRIKE_TEAM, FOE, name="vt")
c.eq("a single-profile weapon is always itself", names(weapon_profiles.valued_profiles(
    weapon_named(_tb.models[1], "Gitstikka"))), ["Gitstikka"])
c.eq("the Snazzgun is its non-hazardous Dakka (no target)", names(weapon_profiles.valued_profiles(_snazz)),
     ["Snazzgun - Dakka"])
c.eq("...and against a vehicle too (no Hunter profile to add)",
     names(weapon_profiles.valued_profiles(_snazz, _fish_sq)), ["Snazzgun - Dakka"])
c.eq("the launcha without a target cannot assume a vehicle: Standard only",
     names(weapon_profiles.valued_profiles(_launcha)), ["Busta Rokkit Launcha - Standard"])
c.eq("...against a VEHICLE both profiles count", names(weapon_profiles.valued_profiles(_launcha, _fish_sq)),
     ["Busta Rokkit Launcha - Standard", "Busta Rokkit Launcha - Hunter"])
c.eq("...against infantry only the Standard", names(weapon_profiles.valued_profiles(_launcha, _team_sq)),
     ["Busta Rokkit Launcha - Standard"])


class _HazB(WeaponProfile):
    name = "hazard B"
    hazardous = True


class _HazA(WeaponProfile):
    name = "hazard A"
    hazardous = True
    overcharge_profile = _HazB


c.eq("a chain with nothing usable falls back to its first profile", names(weapon_profiles.valued_profiles(_HazA())),
     ["hazard A"])
c.eq("the AI deploys Flash Gitz on their 24\" Dakka, not the 12\" Cutta", deployment_ai._max_ranged_range(_g5), 24.0)
c.eq("...and reads the same reach for garrison ranking", combat_focus.best_ranged_reach_in(_g5), 24.0)


# ===========================================================================
print("\n7. retired")
# ===========================================================================
for _mod in ("gun_crazy_showoffs", "ammo_runt"):
    c.true("game/%s.py is gone" % _mod, not os.path.exists(os.path.join(HERE, "game", "%s.py" % _mod)))
for _cls in ("RokkitLunchaProfile", "TankbustaChoppaProfile", "TankbustaCloseCombatWeaponProfile", "SnazzgunProfile",
             "FlashGitzChoppaProfile"):
    c.true("weapons.%s is gone" % _cls, not hasattr(weapons_mod, _cls))
for _flag in ("tank_hunters", "gun_crazy_showoffs"):
    c.true("UnitProfile carries no %s flag" % _flag, not hasattr(UnitProfile, _flag))
c.true("Token carries no ammo_runt field", "ammo_runt" not in Token.__dataclass_fields__)
c.true("Squad carries no ammo_runt_active flag", not hasattr(build(ork.BOYZ, HUMAN, name="r"), "ammo_runt_active")
       and "ammo_runt_active" not in activation_state.SQUAD_FLAGS)
c.true("the Flash Gitz' Ammo Runt gear name is gone", not hasattr(ork, "FLASH_GITZ_AMMO_RUNT"))
_bh = build(MYPHITIC_BLIGHT_HAULER, HUMAN, name="bh")
c.eq("the Blight-hauler's ranged-only Tank Hunters still works (one -1 on each threshold)",
     [m.amount for m in tank_hunters_modifiers(_bh.models[0], _fish_sq)], [-1])
c.eq("...and not in melee", tank_hunters_modifiers(_bh.models[0], _fish_sq, melee=True), [])
c.eq("...and the Tankbustas get nothing from it any more", tank_hunters_modifiers(_tb.models[1], _fish_sq), [])
c.true("Squad starts with both Bomb Squig ledgers empty", Squad.__init__ is not None
       and (_tb.bomb_squigs_used, _tb.bomb_squigs_turn) == (0, None))


# ===========================================================================
print("\n8. wiring, at the source")
# ===========================================================================
def read(rel):
    return io.open(os.path.join(HERE, rel), encoding="utf-8").read()


def body_calls(rel, name, cls=None):
    """unparse() of every reachable call in `name`'s body - a call behind
    `if False:` or `False and` does not count."""
    tree = ast.parse(read(rel))
    scope = tree if cls is None else next((n for n in ast.walk(tree)
                                           if isinstance(n, ast.ClassDef) and n.name == cls), None)
    fn = next((n for n in ast.walk(scope) if isinstance(n, ast.FunctionDef) and n.name == name), None) \
        if scope is not None else None
    out = set()
    if fn is None:
        return out

    def walk(node):
        if isinstance(node, ast.If) and isinstance(node.test, ast.Constant) and not node.test.value:
            for child in node.orelse:
                walk(child)
            return
        if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And) and any(
                isinstance(v, ast.Constant) and not v.value for v in node.values):
            return
        if isinstance(node, ast.Call):
            out.add(ast.unparse(node))
        for child in ast.iter_child_nodes(node):
            walk(child)

    for stmt in fn.body:
        walk(stmt)
    return out


for _rel, _cls, _fn, _call in (
        ("game/shooting.py", "ShootingController", "start_shooting", "self.pulsa_rokkit.offer(squad)"),
        ("game/shooting.py", "ShootingController", "_adjusted_weapon",
         "self.pulsa_rokkit.adjusted_weapon(weapon, self.active_squad, target_squad, reactive=self._reactive)"),
        ("game/shooting.py", "ShootingController", "_adjusted_weapon",
         "finderz_keeperz.adjusted_weapon(weapon, self.active_squad, target_squad, self.objectives, "
         "reactive=self._reactive)"),
        ("game/defend_at_all_costs.py", None, "applies",
         "objectives_module.attacker_or_target_within_range_of_objective(attacking_squad, target_squad, objectives)")):
    c.true("%s %s() reaches %s" % (_rel, _fn, _call), _call in body_calls(_rel, _fn, _cls))
c.true("game/fight.py no longer asks Tank Hunters", "tank_hunters_modifiers" not in read("game/fight.py"))

MAIN = read("main.py")
MAIN_TREE = ast.parse(MAIN)
_main_fn = next(n for n in MAIN_TREE.body if isinstance(n, ast.FunctionDef) and n.name == "main")
_statements = {ast.unparse(n.value) for n in ast.walk(_main_fn)
               if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)}


def ctor(cls):
    call = next((n for n in ast.walk(_main_fn) if isinstance(n, ast.Call) and ast.unparse(n.func) == cls), None)
    return {kw.arg: ast.unparse(kw.value) for kw in call.keywords} if call is not None else None


for _cls, _want in (("BombSquigsController", {"auto_players": "ai_players", "target_pick": "_best_damage_target",
                                              "turn_tracker": "turn_tracker", "visible": "_psychic_visible",
                                              "dice_manager": "dice_manager"}),
                    ("PulsaRokkitController", {"auto_players": "ai_players", "target_pick": "_best_damage_target",
                                               "turn_tracker": "turn_tracker"}),
                    ("RokkitBarrageController", {"auto_players": "ai_players",
                                                 "battle_shock_controller": "battle_shock_controller"})):
    _kw = ctor(_cls)
    c.true("main() builds %s" % _cls, _kw is not None)
    for _k, _v in _want.items():
        c.eq("...with %s=%s" % (_k, _v), (_kw or {}).get(_k), _v)
c.true("Rokkit Barrage's pick is the AI policy", "battle_shock_target_choice" in (ctor("RokkitBarrageController")
                                                                                   or {}).get("target_pick", ""))
c.eq("ShootingController gets the Pulsa Rokkit controller", (ctor("ShootingController") or {}).get("pulsa_rokkit"),
     "pulsa_rokkit_controller")
for _stmt in ("shooting_controller.on_squad_finished_shooting.append(rokkit_barrage_controller.offer_after_shooting)",
              "movement_controller.on_move_finished.append(bomb_squigs_controller.on_move_finished)",
              "bomb_squigs_controller.on_dice_acknowledged()",
              "pulsa_rokkit_controller.reset_phase()",
              "renderer.draw_damage_choice_highlight(board_surface, board, bomb_squigs_controller.pending_damage_choice)",
              "bomb_squigs_controller.choose_damage_model(clicked)"):
    c.true("main() runs %s" % _stmt, _stmt in _statements)
_tuple = next((n for n in ast.walk(_main_fn) if isinstance(n, ast.Assign)
               and any(ast.unparse(t) == "damage_choice_controllers" for t in n.targets)), None)
c.true("Bomb Squigs is in the damage-choice list (AI pause, panel, AI answer)",
       _tuple is not None and "bomb_squigs_controller" in ast.unparse(_tuple.value))
_gate = next((n for n in ast.walk(_main_fn) if isinstance(n, ast.FunctionDef)
              and n.name == "_has_unresolved_declaration"), None)
c.true("...and its dice and open allocation hold the phase",
       _gate is not None and "bomb_squigs_controller.is_busy" in ast.unparse(_gate)
       and "bomb_squigs_controller.pending_damage_choice is not None" in ast.unparse(_gate))
_pulsa_at = next((n.lineno for n in ast.walk(_main_fn) if isinstance(n, ast.Assign)
                  and any(ast.unparse(t) == "pulsa_rokkit_controller" for t in n.targets)), None)
_best_at = next((n.lineno for n in ast.walk(_main_fn) if isinstance(n, ast.FunctionDef)
                 and n.name == "_best_damage_target"), None)
c.true("the Pulsa Rokkit controller is built AFTER _best_damage_target exists (error class 23)",
       _pulsa_at is not None and _best_at is not None and _best_at < _pulsa_at)

c.finish()
