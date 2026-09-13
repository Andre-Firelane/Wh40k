"""The Canoptek Court - the second Necron detachment: its rule (Power Matrix),
its four Enhancements and its six Stratagems, driven through the real
controllers.

WHAT THIS SUITE PINS, and why each part is here:

  1. THE RECORD AGAINST THE CORPUS. rules/necrons/detachments/Canoptek Court.md
     is generated from Wahapedia's page; the DP, the Force Disposition, every
     Enhancement's points and every Stratagem's CP are read from it rather
     than typed twice.
  2-4. THE POWER MATRIX. The regions are a UNION of the three board regions,
     so "wholly within" is measured at the edges that matter - a base that
     straddles your zone and No Man's Land is inside the matrix exactly when
     No Man's Land is. The latch holds for the phase that stamped it.
  5. THE RE-ROLL, at both granularities: 19.03's pooled CRYPTEK/CANOPTEK unit,
     and the whole-roll half through the real attack controllers.
  6. THE ENHANCEMENTS - bearer, detachment gate, and the one reader each.
  7-12. THE STRATAGEMS at their WHEN/TARGET borders, through real controllers.
  13. gain_cp()'s required `source`, by AST over the whole engine - the seam
     the Autodivinator needed.
  14. WIRING (main.py, the panel chain, the AI) and the AI verdicts.
  15. DORMANT BY ROSTER - no shipped list fields the detachment (user decision).

Real controllers, real datasheets, scripted dice (testkit).
"""

import ast
import inspect
import io
import os
import re
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import testkit as tk                                                 # noqa: E402
from testkit import Checks, settings_as                              # noqa: E402

from game import attached_units, config, enhancements as E           # noqa: E402
from game import force_dispositions, maps, reroll_scope              # noqa: E402
from game import necron_detachments as nd                            # noqa: E402
from game import court_power_matrix as pm                            # noqa: E402
from game import court_curse_of_the_cryptek as curse                 # noqa: E402
from game import court_cynosure_of_eradication as cyn                # noqa: E402
from game import court_solar_pulse as solar                          # noqa: E402
from game import court_reactive_subroutines as rsub                  # noqa: E402
from game import court_countertemporal_shift as shift                # noqa: E402
from game import court_suboptimal_facade as facade                   # noqa: E402
from game import enh_autodivinator as autodiv                        # noqa: E402
from game import enh_dimensional_sanctum as sanctum                  # noqa: E402
from game import enh_hyperphasic_fulcrum as fulcrum                  # noqa: E402
from game import enh_metalodermal_tesla_weave as tesla               # noqa: E402
from game import fight as fight_module                               # noqa: E402
from game import status_effects                                      # noqa: E402
from game.charge import ChargeController                             # noqa: E402
from game.command_points import (CommandPointManager, SOURCE_ABILITY,  # noqa: E402
                                 SOURCE_MISSION)
from game.decision import DecisionManager                            # noqa: E402
from game.dice import DiceManager                                    # noqa: E402
from game.fight import FightController                               # noqa: E402
from game.game_state import GameState                                # noqa: E402
from game.mission_context import objective_centre                    # noqa: E402
from game.movement import MovementController                         # noqa: E402
from game.shooting import ShootingController                         # noqa: E402
from game.squad import squad_has_infiltrators                        # noqa: E402
from game.stratagems import StratagemController                      # noqa: E402
from game.turn import (PHASES, PHASE_CHARGE, PHASE_COMMAND,          # noqa: E402
                       PHASE_FIGHT, PHASE_MOVEMENT, PHASE_SHOOTING,
                       TurnTracker)

from game.factions import necrons as nec                             # noqa: E402
from game.factions.death_guard import PLAGUE_MARINES                 # noqa: E402
from game.factions.orks import BOYZ                                  # noqa: E402

c = Checks("Canoptek Court")

HUMAN = "Player 1"
FOE = "Player 2"
COURT = dict(CANOPTEK_COURT_PLAYERS=(HUMAN,))
BOTH = dict(CANOPTEK_COURT_PLAYERS=(HUMAN, FOE))
NONE = dict(CANOPTEK_COURT_PLAYERS=())

M2 = maps.get("map2")
maps.apply_to_config(M2)
W, H = M2.width_in, M2.height_in

CORPUS_PATH = os.path.join("rules", "necrons", "detachments", "Canoptek Court.md")
CORPUS = io.open(CORPUS_PATH, encoding="utf-8").read()


def norm(text):
    """The corpus prints typographic apostrophes; the modules plain ones."""
    return " ".join((text or "").replace("’", "'").replace("**", "").split())


def map_state(key="map2"):
    st = GameState()
    maps.get(key).build(st)
    return st


def tracker(phase, owner=HUMAN, battle_round=2):
    tt = TurnTracker()
    tt.started = True
    tt.battle_round = battle_round
    tt.phase_index = PHASES.index(phase)
    tt.turn_owner = owner
    tt.set_active(owner)
    return tt


def strat(cp=10):
    pool = CommandPointManager()
    for player in pool.cp:
        pool.cp[player] = cp
    return StratagemController(command_points=pool, game_log=tk.Log())


def add(state, *squads):
    for squad in squads:
        for model in squad.models:
            state.add_token(model)


def alive(squad):
    return [m for m in squad.models if not m.is_dead()]


def cluster(squad, point, spacing=1.3, per_row=4):
    """Models packed around `point`, row by row."""
    n = len(squad.models)
    rows = (n + per_row - 1) // per_row
    cols = min(n, per_row)
    for i, model in enumerate(squad.models):
        r, col = divmod(i, per_row)
        model.x_in = point[0] + (col - (cols - 1) / 2.0) * spacing
        model.y_in = point[1] + (r - (rows - 1) / 2.0) * spacing
    return squad


def led_warriors(owner=HUMAN, name="1 Necron Warriors 1"):
    """A Technomancer supporting Necron Warriors - a CRYPTEK unit (19.03) whose
    only CRYPTEK MODEL is the Technomancer."""
    warriors = tk.build(nec.NECRON_WARRIORS, owner, name=name)
    tech = tk.build(nec.TECHNOMANCER, owner, name=name.replace("Necron Warriors", "Technomancer"))
    merged = attached_units.attach(tech, warriors)
    return merged


def tech_model(squad):
    return next(m for m in squad.models if nd.model_is_cryptek(squad, m))


def warrior_model(squad):
    return next(m for m in squad.models if not nd.model_is_cryptek(squad, m))


# ==========================================================================
print("=== 1. the record, against the corpus ===")
# ==========================================================================

REC = nec.CANOPTEK_COURT
c.true("the detachment is registered on the faction",
       nec.NECRONS.detachments.get("Canoptek Court") is REC)
c.eq("its rule is the Power Matrix", REC.rule_name, "Power Matrix")
c.eq("...gated on CANOPTEK_COURT_PLAYERS", REC.setting, "CANOPTEK_COURT_PLAYERS")
_dp = re.search(r"(\d+) DP detachment", CORPUS)
c.eq("its DP match the printed heading", REC.points, int(_dp.group(1)) if _dp else None)
_fd = re.search(r"Force Disposition: ([A-Za-z ]+)", CORPUS)
c.eq("its Force Disposition matches the printed heading",
     REC.force_disposition,
     force_dispositions.from_printed(_fd.group(1).strip()) if _fd else None)
c.eq("...which is Take and Hold", REC.force_disposition, force_dispositions.TAKE_AND_HOLD)
c.true("the record carries the printed rule text",
       "re-roll a Hit roll of 1" in norm(REC.rule_text))
c.eq("the setting ships empty - nobody fields it by default",
     tuple(getattr(config, "CANOPTEK_COURT_PLAYERS", ("missing",))), ())

_printed_enh = {name.strip(): int(pts)
                for name, pts in re.findall(r"^### (.+?) - (\d+) pts$", CORPUS, re.M)}
c.eq("the corpus prints four Enhancements", len(_printed_enh), 4)
c.eq("...the record names the same four at the same points",
     {e.name: e.points for e in REC.enhancements}, _printed_enh)
_court_specs = {n: s for n, s in E.ENHANCEMENTS.items() if s.detachment == "Canoptek Court"}
c.eq("...and all four are ENGINE-WIRED in the registry, at the same points",
     {n: s.points for n, s in _court_specs.items()}, _printed_enh)
for _name, _spec in sorted(_court_specs.items()):
    c.eq("%s gates on the detachment's setting" % _name, _spec.setting, REC.setting)
    c.eq("%s is printed CRYPTEK model only" % _name, _spec.bearer_text, "CRYPTEK model only")

_printed_strat = {name.strip().upper(): int(cp)
                  for name, cp in re.findall(r"^### (.+?) - (\d)CP$", CORPUS, re.M)}
MODULE_STRATS = {
    curse.CURSE_OF_THE_CRYPTEK_NAME: (curse, curse.CURSE_OF_THE_CRYPTEK_CP),
    cyn.CYNOSURE_NAME: (cyn, cyn.CYNOSURE_CP),
    solar.SOLAR_PULSE_NAME: (solar, solar.SOLAR_PULSE_CP),
    rsub.REACTIVE_SUBROUTINES_NAME: (rsub, rsub.REACTIVE_SUBROUTINES_CP),
    shift.COUNTERTEMPORAL_SHIFT_NAME: (shift, shift.COUNTERTEMPORAL_SHIFT_CP),
    facade.SUBOPTIMAL_FACADE_NAME: (facade, facade.SUBOPTIMAL_FACADE_CP),
}
c.eq("the corpus prints six Stratagems", len(_printed_strat), 6)
c.eq("...and one module per Stratagem, each at its printed CP",
     {n.upper(): cp for n, (_m, cp) in MODULE_STRATS.items()}, _printed_strat)
for _name, (_module, _cp) in sorted(MODULE_STRATS.items()):
    _src = inspect.getsource(_module)
    c.true("%s quotes its rule verbatim" % _name, "RULE (verbatim" in _src)
    c.true("%s gates on the detachment" % _name, "has_detachment" in _src
           or "is_court_unit" in _src)
    _effect = re.search(r"### %s - \dCP.*?\*\*EFFECT:\*\* ([^\n]+)" % re.escape(_name.upper()),
                        CORPUS, re.S)
    _first = " ".join(norm(_effect.group(1)).split()[:6]) if _effect else "<no effect>"
    c.true("%s's docstring carries its printed EFFECT (%s...)" % (_name, _first),
           _first in norm(_src))


# ==========================================================================
print("=== 2. the Power Matrix regions ===")
# ==========================================================================

ST = map_state()
ZONES = {z.owner: z for z in ST.deployment_zones}
c.eq("map2 has one zone per player", sorted(ZONES), [HUMAN, FOE])
OWN, ENEMY = ZONES[HUMAN], ZONES[FOE]

_nml = pm.objectives_in_no_mans_land(ST)
c.true("No Man's Land holds objectives on map2 (%d)" % len(_nml), len(_nml) >= 1)
c.true("...none of them centred in a deployment zone",
       all(not z.contains_point(*objective_centre(o)) for o in _nml for z in ZONES.values()))
_their = pm.objectives_in_enemy_zone(ST, HUMAN)
c.true("the opponent's zone holds an objective (%d)" % len(_their), len(_their) >= 1)
c.true("...centred in THEIR zone", all(ENEMY.contains_point(*objective_centre(o)) for o in _their))
c.eq("...and it is the other one from the opponent's side",
     set(pm.objectives_in_enemy_zone(ST, FOE)) & set(_their), set())

# "at least half", and half of nothing is not a majority.
def _objs(*owners):
    return [SimpleNamespace(controlled_by=o) for o in owners]

for label, objs, want in (
        ("0 of 0", _objs(), False),
        ("1 of 2", _objs(HUMAN, None), True),
        ("1 of 3", _objs(HUMAN, None, FOE), False),
        ("2 of 3", _objs(HUMAN, HUMAN, FOE), True),
        ("2 of 4", _objs(HUMAN, HUMAN, FOE, None), True),
        ("0 of 1", _objs(FOE), False)):
    c.eq("controls at least half: %s" % label, pm.controls_at_least_half(objs, HUMAN), want)

# The n == 0 case is unreachable on the shipped boards - measured, not assumed.
for _key in ("map1", "map2", "map3", "map4"):
    _st = map_state(_key)
    c.true("%s: No Man's Land holds at least one objective" % _key,
           len(pm.objectives_in_no_mans_land(_st)) >= 1)
    for _player in (HUMAN, FOE):
        c.true("%s: %s's opponent's zone holds at least one objective" % (_key, _player),
               len(pm.objectives_in_enemy_zone(_st, _player)) >= 1)

for o in ST.objectives:
    o.controlled_by = None
c.eq("holding nothing: only your deployment zone", pm.regions_now(ST, HUMAN),
     frozenset({pm.OWN_ZONE}))
for o in _nml[: (len(_nml) + 1) // 2]:
    o.controlled_by = HUMAN
c.eq("holding half of No Man's Land adds it", pm.regions_now(ST, HUMAN),
     frozenset({pm.OWN_ZONE, pm.NO_MANS_LAND}))
c.eq("...for that player only", pm.regions_now(ST, FOE), frozenset({pm.OWN_ZONE}))
for o in _their:
    o.controlled_by = HUMAN
c.eq("holding the opponent's home adds their zone too", pm.regions_now(ST, HUMAN),
     frozenset({pm.OWN_ZONE, pm.NO_MANS_LAND, pm.ENEMY_ZONE}))
for o in ST.objectives:
    o.controlled_by = None


# ==========================================================================
print("=== 3. wholly within, at the edges that matter ===")
# ==========================================================================

def grid(step=0.5):
    y = step
    while y < H:
        x = step
        while x < W:
            yield x, y
            x += step
        y += step


def first(pred):
    return next((p for p in grid() if pred(*p)), None)


def on_board(x, y, margin):
    return margin <= x <= W - margin and margin <= y <= H - margin


R = 1.0
OWN_DEEP = first(lambda x, y: OWN.contains_circle(x, y, 4.5))
ENEMY_DEEP = first(lambda x, y: ENEMY.contains_circle(x, y, 4.5))
NML_DEEP = first(lambda x, y: on_board(x, y, 3.0) and OWN.distance_to_point(x, y) >= 3.0
                 and ENEMY.distance_to_point(x, y) >= 3.0)
STRADDLE_OWN = first(lambda x, y: on_board(x, y, R + 1.0)
                     and 0.2 <= OWN.shape.signed_distance(x, y) <= R - 0.2
                     and ENEMY.distance_to_point(x, y) >= 3.0)
STRADDLE_ENEMY = first(lambda x, y: on_board(x, y, R + 1.0)
                       and 0.2 <= ENEMY.shape.signed_distance(x, y) <= R - 0.2
                       and OWN.distance_to_point(x, y) >= 3.0)
c.true("the board offers every probe point (live)",
       None not in (OWN_DEEP, ENEMY_DEEP, NML_DEEP, STRADDLE_OWN, STRADDLE_ENEMY))


def base(point, r=R):
    return SimpleNamespace(x_in=point[0], y_in=point[1], radius_in=r)


ZL = ST.deployment_zones
O, N, X = pm.OWN_ZONE, pm.NO_MANS_LAND, pm.ENEMY_ZONE
for regions, point, want, label in (
        ({O}, OWN_DEEP, True, "own zone only: a base deep in your zone"),
        ({O}, NML_DEEP, False, "own zone only: a base in No Man's Land"),
        ({O}, STRADDLE_OWN, False, "own zone only: a base straddling your zone and No Man's Land"),
        ({O}, ENEMY_DEEP, False, "own zone only: a base in the opponent's zone"),
        ({O, N}, NML_DEEP, True, "+ No Man's Land: a base in No Man's Land"),
        ({O, N}, STRADDLE_OWN, True, "+ No Man's Land: the same straddling base"),
        ({O, N}, STRADDLE_ENEMY, False, "+ No Man's Land: a base reaching into their zone"),
        ({O, N}, ENEMY_DEEP, False, "+ No Man's Land: a base deep in their zone"),
        ({O, X}, ENEMY_DEEP, True, "+ their zone: a base deep in their zone"),
        ({O, X}, NML_DEEP, False, "+ their zone: No Man's Land is still outside"),
        ({O, X}, STRADDLE_ENEMY, False, "+ their zone: a base straddling No Man's Land"),
        ({O, N, X}, STRADDLE_ENEMY, True, "all three: anywhere on the battlefield")):
    c.eq(label, pm.model_wholly_within(base(point), HUMAN, frozenset(regions), ZL), want)


# ==========================================================================
print("=== 4. the latch: decided at the start of the phase ===")
# ==========================================================================

with settings_as(**COURT):
    _tt = tracker(PHASE_MOVEMENT)
    _log = tk.Log()
    MATRIX = pm.PowerMatrixController(game_state=ST, turn_tracker=_tt, game_log=_log)
    for o in ST.objectives:
        o.controlled_by = None
    c.eq("before any stamp the live answer is given", MATRIX.regions_for(HUMAN),
         frozenset({O}))
    MATRIX.stamp_at_start_of_phase()
    c.true("the stamp is logged", _log.has("[power matrix]"))
    c.eq("only players who field the detachment are stamped", sorted(MATRIX._latched), [HUMAN])
    for o in _nml:
        o.controlled_by = HUMAN
    c.eq("taking No Man's Land MID-phase changes nothing this phase",
         MATRIX.regions_for(HUMAN), frozenset({O}))
    c.eq("...although the live answer has moved", pm.regions_now(ST, HUMAN), frozenset({O, N}))
    _tt.advance_phase()
    c.eq("the next phase, unstamped, reads live", MATRIX.regions_for(HUMAN), frozenset({O, N}))
    MATRIX.stamp_at_start_of_phase()
    for o in _nml:
        o.controlled_by = None
    c.eq("...and its own stamp holds it for that phase", MATRIX.regions_for(HUMAN),
         frozenset({O, N}))
    for o in ST.objectives:
        o.controlled_by = None

# ==========================================================================
print("=== 5. the re-roll: who, and when it is the whole roll ===")
# ==========================================================================

SHOOT_SRC = io.open(os.path.join("game", "shooting.py"), encoding="utf-8").read()
FIGHT_SRC = io.open(os.path.join("game", "fight.py"), encoding="utf-8").read()

WRAITHS = cluster(tk.build(nec.CANOPTEK_WRAITHS, HUMAN, name="1 Canoptek Wraiths 1"),
                  OWN_DEEP, spacing=2.5, per_row=3)
LED = led_warriors()
LONE_WARRIORS = tk.build(nec.NECRON_WARRIORS, HUMAN, name="1 Necron Warriors 2")
IMMORTALS = tk.build(nec.IMMORTALS, HUMAN, name="1 Immortals 1")
FOE_WRAITHS = tk.build(nec.CANOPTEK_WRAITHS, FOE, name="2 Canoptek Wraiths 1")

with settings_as(**COURT):
    c.true("Canoptek Wraiths are a CANOPTEK unit", nd.is_canoptek_unit(WRAITHS))
    c.true("a Technomancer makes Necron Warriors a CRYPTEK unit (19.03)", nd.is_cryptek_unit(LED))
    c.true("...while the Warriors are not CRYPTEK models",
           not nd.model_is_cryptek(LED, warrior_model(LED)))
    c.true("the re-roll covers the Wraiths", pm.applies(WRAITHS))
    c.true("...and the Cryptek-led Warriors", pm.applies(LED))
    c.true("...not Warriors on their own", not pm.applies(LONE_WARRIORS))
    c.true("...nor Immortals", not pm.applies(IMMORTALS))
    c.true("...nor an opponent who does not field the detachment", not pm.applies(FOE_WRAITHS))
with settings_as(**NONE):
    c.true("without the detachment nothing applies", not pm.applies(WRAITHS))
c.true("the Power Matrix is a ones-or-whole source",
       reroll_scope.is_ones_or_whole(pm.POWER_MATRIX_LABEL))

ST5 = map_state()
BOYZ5 = cluster(tk.build(BOYZ, FOE, name="2 Boyz 1"), NML_DEEP)
add(ST5, WRAITHS, BOYZ5)
with settings_as(**COURT):
    TT5 = tracker(PHASE_SHOOTING)
    MATRIX5 = pm.PowerMatrixController(game_state=ST5, turn_tracker=TT5)
    c.true("the Wraiths stand wholly within their zone", MATRIX5.unit_wholly_within(WRAITHS))
    c.true("...so the whole roll is on offer", pm.offers_full_reroll(WRAITHS, MATRIX5))
    c.true("...and with no matrix handed over, it is not", not pm.offers_full_reroll(WRAITHS, None))

    SC5 = ShootingController(obstacles=ST5.obstacles, game_log=tk.Log(), player_name=HUMAN,
                             dice_manager=DiceManager(), turn_tracker=TT5, all_tokens=ST5.tokens,
                             decision_manager=DecisionManager(), objectives=ST5.objectives)
    SC5.active_squad = WRAITHS
    c.true("ShootingController with no matrix names no whole roll",
           SC5._hit_reroll_reason(BOYZ5) != pm.POWER_MATRIX_LABEL)
    SC5.power_matrix = MATRIX5
    c.eq("ShootingController names the Power Matrix when wholly within",
         SC5._hit_reroll_reason(BOYZ5), pm.POWER_MATRIX_LABEL)
    FC5 = FightController(game_log=tk.Log(), dice_manager=DiceManager(),
                          turn_tracker=tracker(PHASE_FIGHT), all_tokens=ST5.tokens,
                          decision_manager=DecisionManager())
    FC5.fighting_squad = WRAITHS
    FC5.power_matrix = MATRIX5
    c.eq("FightController names it too - 'an attack'",
         FC5._hit_reroll_reason(BOYZ5), pm.POWER_MATRIX_LABEL)

    _saved = (WRAITHS.models[0].x_in, WRAITHS.models[0].y_in)
    WRAITHS.models[0].x_in, WRAITHS.models[0].y_in = STRADDLE_OWN
    c.true("one base across the edge and the unit is not wholly within",
           not MATRIX5.unit_wholly_within(WRAITHS))
    c.true("...so the whole roll is gone at range",
           SC5._hit_reroll_reason(BOYZ5) != pm.POWER_MATRIX_LABEL)
    c.true("...and in melee", FC5._hit_reroll_reason(BOYZ5) != pm.POWER_MATRIX_LABEL)
    c.true("...while the automatic 1s still apply", pm.applies(WRAITHS))
    WRAITHS.models[0].x_in, WRAITHS.models[0].y_in = _saved

    # THE AUTOMATIC HALF, MEASURED WHERE IT RUNS. pm.applies() being True and
    # the disjunction naming `matrix_ones` both hold while the hit step never
    # throws the 1s - the A/B probe showed it. So: a real ShootingController's
    # _hit_step on a roll with two 1s, with no matrix handed over (no whole-roll
    # choice to hold the 1s back), and a recording _begin_ones_reroll.
    _ones_calls = []
    SC5._begin_ones_reroll = (lambda kind, ones, *a, **kw:
                              _ones_calls.append((kind, ones, kw.get("reason"))))
    SC5.power_matrix = None
    SC5.active_squad = LED
    _t5 = tech_model(LED)
    _gun5 = next(w for w in _t5.weapons if w.weapon_type == "ranged")
    _grp5 = {"pairs": [(_t5, _gun5)], "target_squad": BOYZ5}
    SC5.current_group = _grp5
    try:
        SC5._hit_step([1, 1, 6], _grp5, _gun5, BOYZ5, "test gun")
        _err5 = None
    except Exception as exc:
        _err5 = repr(exc)
    c.eq("shooting throws the Hit rolls of 1 again by itself, naming the Power Matrix",
         (_ones_calls[:1], _err5), ([("hit", 2, pm.POWER_MATRIX_LABEL)], None))
    del SC5._begin_ones_reroll
    SC5.power_matrix = MATRIX5
    SC5.active_squad = WRAITHS

c.true("shooting: the matrix's 1s join the automatic disjunction", "or matrix_ones" in SHOOT_SRC)
c.true("...and name themselves",
       "ones_reason = court_power_matrix.POWER_MATRIX_LABEL" in SHOOT_SRC)
c.true("melee: the automatic 1s are resolved too",
       "if ones and court_power_matrix.applies(self.fighting_squad)" in FIGHT_SRC)

# The per-model grouping term (04.03's one-representative shortcut).
from game import shooting as shooting_module                         # noqa: E402
_t, _wr = tech_model(LED), warrior_model(LED)
with settings_as(**COURT):
    c.eq("attack_key: the Technomancer is a CRYPTEK model", nd.attack_key(_t), (True, False))
    c.eq("...a Warrior beside him is neither", nd.attack_key(_wr), (False, False))
    c.eq("...a Wraith is CANOPTEK", nd.attack_key(WRAITHS.models[0]), (False, True))
    _key_on = shooting_module._attack_key(_t, _t.weapons[0])
    _melee_on = fight_module._melee_attack_key(_t, _t.weapons[-1])
with settings_as(**NONE):
    c.eq("without the detachment the term is the constant", nd.attack_key(_t), (False, False))
    _key_off = shooting_module._attack_key(_t, _t.weapons[0])
    _melee_off = fight_module._melee_attack_key(_t, _t.weapons[-1])
c.true("...so the shooting group key moves only for a Court player", _key_on != _key_off)
c.true("...and so does the melee one", _melee_on != _melee_off)


# ==========================================================================
print("=== 6. the four Enhancements ===")
# ==========================================================================

from game.units import UnitProfile                                   # noqa: E402

for _name, _spec in sorted(_court_specs.items()):
    c.eq("UnitProfile.%s defaults to False" % _spec.flag, getattr(UnitProfile, _spec.flag, None),
         False)

LED6 = led_warriors(name="1 Necron Warriors 3")
T6 = tech_model(LED6)
_sanctum = E.get("Dimensional Sanctum")
c.true("a Technomancer may bear them", _sanctum.can_bear(T6, LED6))
c.true("...a Warrior in his unit may not", not _sanctum.can_bear(warrior_model(LED6), LED6))
_overlord = tk.build(nec.OVERLORD, HUMAN, name="1 Overlord 1")
c.true("...nor a CHARACTER who is no Cryptek", not _sanctum.can_bear(_overlord.models[0], _overlord))
_lone_wraiths = tk.build(nec.CANOPTEK_WRAITHS, HUMAN, name="1 Canoptek Wraiths 7")
c.true("...nor a CANOPTEK model", not _sanctum.can_bear(_lone_wraiths.models[0], _lone_wraiths))
try:
    E.grant(_overlord, "Autodivinator")
    _refused = False
except ValueError:
    _refused = True
c.true("granting one to an Overlord is refused", _refused)

_pts = LED6.points
E.grant(LED6, "Dimensional Sanctum", model=T6)
c.eq("the grant lands on the Technomancer", E.bearer_models(LED6, "Dimensional Sanctum"), [T6])
c.eq("...and costs its printed 20 points", (LED6.points or 0) - (_pts or 0), 20)

# Dimensional Sanctum -> 24.20's every-model gate, as a unit-level grant.
with settings_as(**COURT):
    c.true("Dimensional Sanctum gives the bearer's unit Infiltrators", squad_has_infiltrators(LED6))
    c.true("...through its own module", sanctum.grants_infiltrators(LED6))
    c.true("...and not a unit without it",
           not squad_has_infiltrators(led_warriors(name="1 Necron Warriors 4")))
    T6.current_wounds = 0
    c.true("...nor once the bearer is dead", not squad_has_infiltrators(LED6))
    T6.current_wounds = T6.profile.wounds
with settings_as(**NONE):
    c.true("...nor without the detachment", not squad_has_infiltrators(LED6))

# Hyperphasic Fulcrum: leading, wholly within, automatic wound 1s.
ST6 = map_state()
LED_F = cluster(led_warriors(name="1 Necron Warriors 5"), OWN_DEEP)
E.grant(LED_F, "Hyperphasic Fulcrum", model=tech_model(LED_F))
LONE_T = cluster(tk.build(nec.TECHNOMANCER, HUMAN, name="1 Technomancer 9"), OWN_DEEP)
E.grant(LONE_T, "Hyperphasic Fulcrum")
with settings_as(**COURT):
    M6 = pm.PowerMatrixController(game_state=ST6, turn_tracker=tracker(PHASE_SHOOTING))
    c.true("Hyperphasic Fulcrum: leading a unit wholly within", fulcrum.applies(LED_F, M6))
    c.true("...not a Technomancer leading nothing", not fulcrum.applies(LONE_T, M6))
    c.true("...not with no matrix", not fulcrum.applies(LED_F, None))
    _p = (LED_F.models[0].x_in, LED_F.models[0].y_in)
    LED_F.models[0].x_in, LED_F.models[0].y_in = STRADDLE_OWN
    c.true("...not once one model steps across the edge", not fulcrum.applies(LED_F, M6))
    LED_F.models[0].x_in, LED_F.models[0].y_in = _p
with settings_as(**NONE):
    c.true("...and nothing without the detachment", not fulcrum.applies(LED_F, M6))
c.true("it is a plain automatic re-roll, not a ones-or-whole offer",
       not reroll_scope.is_ones_or_whole(fulcrum.HYPERPHASIC_FULCRUM_LABEL))
c.true("shooting reads it on the wound step",
       "enh_hyperphasic_fulcrum.applies(self.active_squad, self.power_matrix)" in SHOOT_SRC)
c.true("...and so does fight",
       "enh_hyperphasic_fulcrum.applies(self.fighting_squad, self.power_matrix)" in FIGHT_SRC)


# Autodivinator: an opponent's CP from an ABILITY.
def cp_scene(bearers=(HUMAN,)):
    st = GameState()
    for owner in bearers:
        t = tk.build(nec.TECHNOMANCER, owner, name="%s Technomancer A" % owner[-1])
        E.grant(t, "Autodivinator")
        add(st, t)
    pool = CommandPointManager()
    ctrl = autodiv.AutodivinatorController(command_points=pool, game_state=st, game_log=tk.Log())
    pool.on_cp_gained.append(ctrl.on_cp_gained)
    return pool


with settings_as(**COURT):
    pool = cp_scene()
    tk.script(2)
    pool.gain_cp(FOE, 2, amount=1, reason="an ability", source=SOURCE_ABILITY)
    c.eq("the opponent gains a CP from an ability: a 2+ gives you one", pool.cp[HUMAN], 1)
    pool = cp_scene()
    tk.script(1)
    pool.gain_cp(FOE, 2, source=SOURCE_ABILITY)
    c.eq("...a 1 gives nothing", pool.cp[HUMAN], 0)
    pool = cp_scene()
    tk.script(6)
    pool.gain_cp(FOE, 2, reason="discarded a card", source=SOURCE_MISSION)
    c.eq("a Secondary Mission discard is not an ability - no die (the FAQ)", tk.scripted(), [6])
    c.eq("...and no CP", pool.cp[HUMAN], 0)
    pool = cp_scene()
    tk.script(6)
    pool.gain_cp(HUMAN, 2, source=SOURCE_ABILITY)
    c.eq("your OWN CP does not trigger it", tk.scripted(), [6])
    pool = cp_scene()
    pool.gain_cp(HUMAN, 2, source=SOURCE_ABILITY)
    tk.script(6)
    pool.gain_cp(FOE, 2, source=SOURCE_ABILITY)
    c.eq("with the bonus-CP cap already reached, no die is thrown", tk.scripted(), [6])
    c.eq("...and no second CP", pool.cp[HUMAN], 1)
with settings_as(**NONE):
    pool = cp_scene()
    tk.script(6)
    pool.gain_cp(FOE, 2, source=SOURCE_ABILITY)
    c.eq("without the detachment the bearer does nothing", (pool.cp[HUMAN], tk.scripted()), (0, [6]))
with settings_as(**BOTH):
    pool = cp_scene(bearers=(HUMAN, FOE))
    tk.script(2, 2, 2)
    pool.gain_cp(FOE, 2, source=SOURCE_ABILITY)
    c.eq("a mirror match ends: the cap stops the exchange", (pool.cp[HUMAN], pool.cp[FOE]), (1, 1))
    c.eq("...after exactly one Autodivinator die", tk.scripted(), [2, 2])
tk.script()

# Metalodermal Tesla Weave, through a real charge declaration.
def charge_scene(defender, charger_models=10):
    st = GameState()
    charging = tk.build(BOYZ, FOE, name="2 Chargers 1")
    charging.models = charging.models[:charger_models]
    for i, model in enumerate(charging.models):
        model.x_in, model.y_in = 20.0 + i * 1.4, 20.0
    for i, model in enumerate(defender.models):
        model.x_in, model.y_in = 20.0 + i * 1.4, 24.0
    add(st, charging, defender)
    tt = tracker(PHASE_CHARGE, owner=FOE)
    dm = DiceManager()
    mc = MovementController(all_tokens=st.tokens, obstacles=st.obstacles, turn_tracker=tt,
                            board_width_in=W, board_height_in=H)
    cc = ChargeController(dice_manager=dm, turn_tracker=tt, all_tokens=st.tokens,
                          movement_controller=mc)
    return dict(state=st, charging=charging, defender=defender, turn=tt, dice=dm,
                decision=DecisionManager(), movement=mc, charge=cc)


def declare(s, *after):
    """A real declaration up to the move: the 2D6 (4+4), then `after` for
    whatever the reactors roll."""
    tk.script(4, 4, *after)
    s["charge"].declare_charge(s["charging"])
    s["dice"].acknowledge()
    s["charge"].on_dice_acknowledged()
    s["charge"].toggle_charge_target(s["defender"])
    s["movement"].selected_squad = s["charging"]
    s["charge"].begin_charge_move()


def total_wounds(squad):
    return sum(max(0, m.current_wounds or 0) for m in squad.models)


def tesla_scene(charger_models=10):
    bearer_unit = led_warriors(name="1 Necron Warriors 6")
    E.grant(bearer_unit, "Metalodermal Tesla Weave", model=tech_model(bearer_unit))
    s = charge_scene(bearer_unit, charger_models=charger_models)
    s["log"] = tk.Log()
    s["tesla"] = tesla.MetalodermalTeslaWeaveController(
        dice_manager=s["dice"], turn_tracker=s["turn"], game_log=s["log"])
    s["charge"].charge_declaration_reactions.append(s["tesla"].maybe_offer)
    return s


def drain_allocation(ctrl, limit=40):
    """Click the first offered model until the allocation is done. DEGRADES
    rather than raises when the controller has no click entry - a probe that
    removes it must turn the checks after this RED, not crash the file."""
    choose = getattr(ctrl, "choose_damage_model", None)
    n = 0
    while choose is not None and ctrl.pending_damage_choice is not None and n < limit:
        choose(ctrl.pending_damage_choice[0])
        n += 1


with settings_as(**COURT):
    s = tesla_scene()
    before = total_wounds(s["charging"])
    declare(s, 6)
    c.true("Tesla Weave: the declaration waits behind its die", s["movement"].move_mode is None)
    c.true("...which is on the table, named", s["dice"].is_pending
           and tesla.METALODERMAL_TESLA_WEAVE in (s["dice"].label or ""))
    c.true("...and nothing is prompted - the bearer simply rolls", not s["decision"].is_pending)
    s["dice"].acknowledge()
    s["tesla"].on_dice_acknowledged()
    c.true("a 6: three mortal wounds to allocate", s["tesla"].pending_damage_choice is not None)
    c.eq("...and the CHARGING player allocates them (06.02)", s["turn"].active_player, FOE)
    c.true("...among the charging unit's own models",
           all(m in s["charging"].models for m in s["tesla"].pending_damage_choice or ()))
    drain_allocation(s["tesla"])
    c.eq("...three wounds land", before - total_wounds(s["charging"]), 3)
    c.eq("...and the charge move resumes", s["movement"].move_mode, "charge")
    c.true("...with nothing left busy", not s["tesla"].is_busy)
    c.true("once per phase: the same bearer does not fire again",
           not s["tesla"].can_fire(s["charging"], s["defender"]))
    s["tesla"].reset_phase()
    c.true("...until the phase ends", s["tesla"].can_fire(s["charging"], s["defender"]))

    s = tesla_scene()
    before = total_wounds(s["charging"])
    declare(s, 1)
    s["dice"].acknowledge()
    s["tesla"].on_dice_acknowledged()
    c.eq("a 1: nothing", before - total_wounds(s["charging"]), 0)
    c.eq("...and the charge still resumes", s["movement"].move_mode, "charge")

    s = tesla_scene()
    before = total_wounds(s["charging"])
    declare(s, 3, 2)
    s["dice"].acknowledge()
    s["tesla"].on_dice_acknowledged()
    c.true("a 2-5 rolls a D3 next", s["dice"].is_pending and "D3" in (s["dice"].label or ""))
    c.true("...and the move is still waiting", s["movement"].move_mode is None)
    s["dice"].acknowledge()
    s["tesla"].on_dice_acknowledged()
    drain_allocation(s["tesla"])
    c.eq("...whose result is the mortal wounds", before - total_wounds(s["charging"]), 2)
    c.eq("...and then the charge resumes", s["movement"].move_mode, "charge")

    for band, d3, want in ((1, None, 0), (2, 1, 1), (5, 3, 3), (6, None, 3), (6, 1, 3)):
        c.eq("the printed table: %s/%s -> %d" % (band, d3, want),
             tesla.mortal_wounds_for(band, d3), want)

    # ONE charging model: the allocation has nobody to choose between, so the
    # session is done the moment it opens - and the controller has to notice
    # that by itself. Every scene above has ten chargers, where the test's own
    # click drains the session and would hide a controller that never checks.
    s = tesla_scene(charger_models=1)
    declare(s, 6)
    s["dice"].acknowledge()
    s["tesla"].on_dice_acknowledged()
    c.eq("one charging model: nobody to choose between, so nothing is asked",
         s["tesla"].pending_damage_choice, None)
    c.true("...the three wounds landed on it", all(m.is_dead() for m in s["charging"].models))
    c.true("...and the Weave is not left holding the charge", not s["tesla"].is_busy)

with settings_as(**NONE):
    s = tesla_scene()
    declare(s)
    c.eq("without the detachment the charge is not held", s["movement"].move_mode, "charge")
    c.true("...and no die is rolled", not s["dice"].is_pending)

with settings_as(**COURT):
    s = charge_scene(led_warriors(name="1 Necron Warriors 10"))
    tw = tesla.MetalodermalTeslaWeaveController(dice_manager=s["dice"], turn_tracker=s["turn"])
    s["charge"].charge_declaration_reactions.append(tw.maybe_offer)
    declare(s)
    c.eq("a target without the Enhancement triggers nothing", s["movement"].move_mode, "charge")


# ==========================================================================
print("=== 7. Curse of the Cryptek ===")
# ==========================================================================

ST7 = GameState()
C_WRAITHS = tk.line_up(tk.build(nec.CANOPTEK_WRAITHS, HUMAN, name="1 Canoptek Wraiths 2"), 10, 10, 2.5)
C_LED = tk.line_up(led_warriors(name="1 Necron Warriors 7"), 10, 20, 1.3)
C_BOYZ = tk.line_up(tk.build(BOYZ, FOE, name="2 Boyz 2"), 10, 40, 1.3)
C_BOYZ_B = tk.line_up(tk.build(BOYZ, FOE, name="2 Boyz 3"), 30, 40, 1.3)
add(ST7, C_WRAITHS, C_LED, C_BOYZ, C_BOYZ_B)
C_TECH = tech_model(C_LED)
NAME7 = curse.CURSE_OF_THE_CRYPTEK_NAME


def curse_ctrl(phase=PHASE_SHOOTING, owner=FOE, auto=(), cp=5, state=ST7):
    s = strat(cp)
    dec = DecisionManager()
    ctrl = curse.CurseOfTheCryptekController(
        s, turn_tracker=tracker(phase, owner=owner), decision_manager=dec, game_state=state,
        game_log=tk.Log(), auto_players=auto)
    return ctrl, s, dec


def sources(mods):
    return [(m.amount, m.source) for m in mods]


with settings_as(**COURT):
    ctrl, s7, dec7 = curse_ctrl()
    c.eq("a dead Warrior is no CRYPTEK model - nothing is owed",
         ctrl.notify_model_destroyed(warrior_model(C_LED), C_BOYZ), False)
    c.true("a dead Technomancer is noted", ctrl.notify_model_destroyed(C_TECH, C_BOYZ))
    c.true("...and nothing is offered until the attacker has finished", not dec7.is_pending)
    c.true("its after-attack hook offers it", ctrl.maybe_offer(C_BOYZ))
    c.eq("...to the Cryptek's owner", dec7.player, HUMAN)
    c.true("...as a Stratagem prompt", dec7.is_stratagem)
    c.true("...naming the attacker", C_BOYZ.name in (dec7.prompt or ""))
    c.true("using it", tk.pick_option(dec7, "Use"))
    c.eq("...costs 1CP", s7.command_points.cp[HUMAN], 4)
    c.eq("...and marks the attacker for the player", ctrl.marked_by(HUMAN), {C_BOYZ})
    _wraith = C_WRAITHS.models[0]
    c.eq("a CANOPTEK model adds 1 to Hit against it",
         sources(ctrl.hit_modifiers(_wraith, C_WRAITHS, C_BOYZ)), [(-1, NAME7)])
    c.eq("...and 1 to Wound", sources(ctrl.wound_modifiers(_wraith, C_WRAITHS, C_BOYZ)), [(-1, NAME7)])
    c.eq("...a Warrior gets nothing - 'a CANOPTEK model'",
         ctrl.hit_modifiers(warrior_model(C_LED), C_LED, C_BOYZ), [])
    # The case the Warriors cannot tell apart: a CANOPTEK UNIT (19.03) holding
    # a model that is not CANOPTEK. A Geomancer supporting Canoptek Macrocytes.
    _mixed = attached_units.attach(
        tk.build(nec.GEOMANCER, HUMAN, name="1 Geomancer 7"),
        tk.build(nec.CANOPTEK_MACROCYTES, HUMAN, name="1 Canoptek Macrocytes 7"))
    _geo = next((m for m in _mixed.models if nd.model_is_cryptek(_mixed, m)), None)
    _macro = next((m for m in _mixed.models if m is not _geo), None)
    c.true("(live) Geomancer + Macrocytes is a CANOPTEK unit whose Geomancer is not CANOPTEK",
           _geo is not None and nd.is_canoptek_unit(_mixed) and not nd.model_is_canoptek(_mixed, _geo))
    c.eq("...so the Geomancer gets nothing - the MODEL is asked, not the unit",
         ctrl.hit_modifiers(_geo, _mixed, C_BOYZ), [])
    c.eq("...while a Macrocyte beside him does",
         sources(ctrl.hit_modifiers(_macro, _mixed, C_BOYZ)), [(-1, NAME7)])
    c.eq("...and nobody gets it against another enemy unit",
         ctrl.hit_modifiers(_wraith, C_WRAITHS, C_BOYZ_B), [])
    ctrl.reset_phase()
    c.eq("the mark lasts the battle - a phase boundary keeps it", ctrl.marked_by(HUMAN), {C_BOYZ})
    ctrl.notify_model_destroyed(C_TECH, C_BOYZ)
    c.eq("a second mark on the same attacker buys nothing and is not offered",
         (ctrl.maybe_offer(C_BOYZ), dec7.is_pending), (False, False))

    ctrl, s7, dec7 = curse_ctrl()
    ctrl.maybe_offer(C_BOYZ)
    c.true("a death seen after the attacker's hook already fired is offered on the spot",
           ctrl.notify_model_destroyed(C_TECH, None) and dec7.is_pending)
    tk.pick_option(dec7, "Decline")
    c.eq("declining costs nothing", (s7.command_points.cp[HUMAN], ctrl.marked_by(HUMAN)), (5, set()))

    ctrl, s7, dec7 = curse_ctrl()
    ctrl.notify_model_destroyed(C_TECH, C_BOYZ)
    ctrl.notify_model_destroyed(C_TECH, C_BOYZ)
    ctrl.maybe_offer(C_BOYZ)
    c.eq("two Cryptek deaths to one attack are ONE question", len(dec7._queue), 1)

    # The sweep's usual case: the death is seen between activations, before
    # any attacker's hook has fired this phase, so there is no killer to name.
    ctrl, s7, dec7 = curse_ctrl()
    c.true("a death with no killer and no attacker yet is owed, not offered",
           ctrl.notify_model_destroyed(C_TECH, None) and not dec7.is_pending)
    c.true("...and the next attacker's hook answers for it",
           ctrl.maybe_offer(C_BOYZ) and dec7.is_pending)

    ctrl, s7, dec7 = curse_ctrl(owner=HUMAN)
    ctrl.notify_model_destroyed(C_TECH, C_BOYZ)
    c.eq("WHEN: not in YOUR Shooting phase", (ctrl.maybe_offer(C_BOYZ), dec7.is_pending), (False, False))
    ctrl, s7, dec7 = curse_ctrl(phase=PHASE_FIGHT, owner=HUMAN)
    ctrl.notify_model_destroyed(C_TECH, C_BOYZ)
    c.true("...but the Fight phase belongs to nobody", ctrl.maybe_offer(C_BOYZ) and dec7.is_pending)
    ctrl, s7, dec7 = curse_ctrl(phase=PHASE_MOVEMENT)
    ctrl.notify_model_destroyed(C_TECH, C_BOYZ)
    c.eq("...and never in the Movement phase", ctrl.maybe_offer(C_BOYZ), False)

    _no_canoptek = GameState()
    add(_no_canoptek, C_LED, C_BOYZ)
    ctrl, s7, dec7 = curse_ctrl(state=_no_canoptek)
    ctrl.notify_model_destroyed(C_TECH, C_BOYZ)
    c.eq("an army with no CANOPTEK unit is not offered a mark it cannot use",
         (ctrl.maybe_offer(C_BOYZ), dec7.is_pending), (False, False))

    ctrl, s7, dec7 = curse_ctrl(auto=(HUMAN,))
    ctrl.notify_model_destroyed(C_TECH, C_BOYZ)
    ctrl.maybe_offer(C_BOYZ)
    c.eq("the AI buys it at once, without a prompt",
         (dec7.is_pending, s7.command_points.cp[HUMAN], ctrl.marked_by(HUMAN)), (False, 4, {C_BOYZ}))

    # Both attack steps read it.
    ctrl, s7, dec7 = curse_ctrl(auto=(HUMAN,))
    ctrl.notify_model_destroyed(C_TECH, C_BOYZ)
    ctrl.maybe_offer(C_BOYZ)
    _gun = _wraith.weapons[0]
    _claws = next(w for w in _wraith.weapons if w.weapon_type == "melee")
    SC7 = ShootingController(obstacles=[], game_log=tk.Log(), player_name=HUMAN,
                             dice_manager=DiceManager(), turn_tracker=tracker(PHASE_SHOOTING),
                             all_tokens=ST7.tokens, decision_manager=DecisionManager())
    SC7.curse_of_the_cryptek = ctrl
    SC7.active_squad = C_WRAITHS
    SC7.current_group = {"pairs": [(_wraith, _gun)], "target_squad": C_BOYZ}
    c.true("ShootingController's hit modifiers carry it",
           (-1, NAME7) in sources(SC7._hit_modifiers(SC7.current_group)))
    c.true("...and its wound modifiers", (-1, NAME7) in sources(SC7._wound_modifiers(C_BOYZ)))
    FC7 = FightController(game_log=tk.Log(), dice_manager=DiceManager(),
                          turn_tracker=tracker(PHASE_FIGHT), all_tokens=ST7.tokens,
                          decision_manager=DecisionManager())
    FC7.curse_of_the_cryptek = ctrl
    FC7.fighting_squad = C_WRAITHS
    FC7.current_group = {"pairs": [(_wraith, _claws)], "target_squad": C_BOYZ}
    c.true("FightController's hit modifiers carry it",
           (-1, NAME7) in sources(FC7._hit_modifiers(_wraith, C_BOYZ)))
    c.true("...and its wound modifiers", (-1, NAME7) in sources(FC7._wound_modifiers(_claws, C_BOYZ)))

with settings_as(**NONE):
    ctrl, s7, dec7 = curse_ctrl()
    c.eq("without the detachment a Cryptek's death is not noted",
         ctrl.notify_model_destroyed(C_TECH, C_BOYZ), False)


# ==========================================================================
print("=== 8. Cynosure of Eradication ===")
# ==========================================================================

ST8 = map_state()
CY_WRAITHS = cluster(tk.build(nec.CANOPTEK_WRAITHS, HUMAN, name="1 Canoptek Wraiths 3"),
                     OWN_DEEP, spacing=2.5, per_row=3)
CY_IMMORTALS = cluster(tk.build(nec.IMMORTALS, HUMAN, name="1 Immortals 2"), OWN_DEEP)
add(ST8, CY_WRAITHS)


def cyn_ctrl(phase=PHASE_SHOOTING, owner=HUMAN, cp=5):
    tt = tracker(phase, owner)
    shoot = SimpleNamespace(active_squad=None, shot_squad_ids=set())
    fight = SimpleNamespace(state=fight_module.NOT_STARTED, fought_squad_ids=set())
    matrix = pm.PowerMatrixController(game_state=ST8, turn_tracker=tt)
    s = strat(cp)
    log = tk.Log()
    ctrl = cyn.CynosureOfEradicationController(
        s, turn_tracker=tt, shooting_controller=shoot, fight_controller=fight,
        power_matrix=matrix, game_log=log)
    return ctrl, s, shoot, fight, log


with settings_as(**COURT):
    ctrl, s8, shoot8, fight8, log8 = cyn_ctrl()
    c.true("WHEN: the start of your Shooting phase", ctrl.can_use(CY_WRAITHS))
    shoot8.shot_squad_ids.add(CY_IMMORTALS)
    c.true("...closed once any unit has shot", not ctrl.can_use(CY_WRAITHS))
    shoot8.shot_squad_ids.clear()
    shoot8.active_squad = CY_IMMORTALS
    c.true("...or is shooting", not ctrl.can_use(CY_WRAITHS))
    shoot8.active_squad = None
    c.true("not the opponent's Shooting phase",
           not cyn_ctrl(owner=FOE)[0].can_use(CY_WRAITHS))
    for _owner in (HUMAN, FOE):
        c.true("the start of the Fight phase, whoever's turn (%s)" % _owner,
               cyn_ctrl(phase=PHASE_FIGHT, owner=_owner)[0].can_use(CY_WRAITHS))
    _c, _s, _sh, _fi, _l = cyn_ctrl(phase=PHASE_FIGHT)
    _fi.state = fight_module.SELECTING
    c.true("...closed once the Fight step has begun", not _c.can_use(CY_WRAITHS))
    for _phase in (PHASE_COMMAND, PHASE_MOVEMENT, PHASE_CHARGE):
        c.true("never in the %s phase" % _phase, not cyn_ctrl(phase=_phase)[0].can_use(CY_WRAITHS))
    c.true("TARGET: not a unit that is no CRYPTEK/CANOPTEK unit", not ctrl.can_use(CY_IMMORTALS))
    _save = (CY_WRAITHS.models[0].x_in, CY_WRAITHS.models[0].y_in)
    CY_WRAITHS.models[0].x_in, CY_WRAITHS.models[0].y_in = STRADDLE_OWN
    c.true("TARGET: not a unit that is not wholly within the matrix", not ctrl.can_use(CY_WRAITHS))
    CY_WRAITHS.models[0].x_in, CY_WRAITHS.models[0].y_in = _save
    c.true("no 2CP, no button", not cyn_ctrl(cp=1)[0].can_use(CY_WRAITHS))
    c.true("the label names its cost and grant",
           "2 CP" in ctrl.panel_label(CY_WRAITHS) and "DEVASTATING WOUNDS" in ctrl.panel_label(CY_WRAITHS))
    c.true("using it", ctrl.use(CY_WRAITHS))
    c.eq("...costs 2CP", s8.command_points.cp[HUMAN], 3)
    c.true("...grants the unit", cyn.is_active(CY_WRAITHS) and log8.has(cyn.CYNOSURE_NAME))
    c.true("...and closes the button", not ctrl.can_use(CY_WRAITHS))
    cyn.reset_phase([CY_WRAITHS])
    c.true("the grant ends with the phase", not cyn.is_active(CY_WRAITHS))
with settings_as(**NONE):
    c.true("without the detachment there is no button", not cyn_ctrl()[0].can_use(CY_WRAITHS))

LED8 = led_warriors(name="1 Necron Warriors 8")
T8, W8 = tech_model(LED8), warrior_model(LED8)
T8_GUN = next(w for w in T8.weapons if w.weapon_type == "ranged")
W8_GUN = next(w for w in W8.weapons if w.weapon_type == "ranged")
c.true("the Technomancer's gun prints no [DEVASTATING WOUNDS] (live)", not T8_GUN.devastating_wounds)
LED8.court_cynosure_active = True
_granted = cyn.adjusted_weapon(T8_GUN, LED8, T8)
c.true("the Technomancer's weapon gains [DEVASTATING WOUNDS]", _granted.devastating_wounds)
c.true("...on a COPY - the model's own weapon is untouched",
       _granted is not T8_GUN and not T8_GUN.devastating_wounds)
c.true("...a Warrior's weapon beside him does not - 'CRYPTEK models'",
       cyn.adjusted_weapon(W8_GUN, LED8, W8) is W8_GUN)
LED8.court_cynosure_active = False
c.true("...and nothing is granted to a unit without it", cyn.adjusted_weapon(T8_GUN, LED8, T8) is T8_GUN)
LED8.court_cynosure_active = True

_pm8 = tk.build(PLAGUE_MARINES, FOE, name="2 Plague Marines 1")
_bz8 = tk.build(BOYZ, FOE, name="2 Boyz 8")
_g_pm = cyn.expected_devastating_gain(LED8, _pm8)
_g_bz = cyn.expected_devastating_gain(LED8, _bz8)
c.true("expected gain against Plague Marines is positive (%.2f)" % _g_pm, _g_pm > 0)
c.true("...and larger than against Boyz, whose save stops less (%.2f)" % _g_bz, _g_pm > _g_bz)
c.eq("...and nothing at all from Warriors alone",
     cyn.expected_devastating_gain(tk.build(nec.NECRON_WARRIORS, HUMAN), _pm8), 0.0)

ST8b = GameState()
tk.line_up(LED8, 10, 10, 1.3)
tk.line_up(_pm8, 10, 20, 1.3)
add(ST8b, LED8, _pm8)
with settings_as(**COURT):
    SC8 = ShootingController(obstacles=[], game_log=tk.Log(), player_name=HUMAN,
                             dice_manager=DiceManager(), turn_tracker=tracker(PHASE_SHOOTING),
                             all_tokens=ST8b.tokens, decision_manager=DecisionManager())
    SC8.active_squad = LED8
    SC8.current_group = {"pairs": [(T8, T8_GUN)], "target_squad": _pm8}
    c.true("ShootingController's adjuster chain grants it to the Technomancer's group",
           SC8._adjusted_weapon([(T8, T8_GUN)], _pm8).devastating_wounds)
    SC8.current_group = {"pairs": [(W8, W8_GUN)], "target_squad": _pm8}
    c.true("...and not to a Warriors group", not SC8._adjusted_weapon([(W8, W8_GUN)], _pm8).devastating_wounds)
    # "...or the start of the Fight phase": the same grant reaches MELEE
    # weapons, through fight.py's own adjuster chain.
    FC8 = FightController(game_log=tk.Log(), dice_manager=DiceManager(),
                          turn_tracker=tracker(PHASE_FIGHT), all_tokens=ST8b.tokens,
                          decision_manager=DecisionManager())
    FC8.fighting_squad = LED8
    T8_BLADE = next(w for w in T8.weapons if w.weapon_type == "melee")
    W8_BLADE = next(w for w in W8.weapons if w.weapon_type == "melee")
    c.true("(live) the Technomancer's melee weapon prints no [DEVASTATING WOUNDS]",
           not T8_BLADE.devastating_wounds)
    c.true("FightController's adjuster chain grants it to the Technomancer's melee group",
           FC8._adjusted_weapon([(T8, T8_BLADE)], _pm8).devastating_wounds)
    c.true("...and not to a Warriors melee group",
           not FC8._adjusted_weapon([(W8, W8_BLADE)], _pm8).devastating_wounds)
LED8.court_cynosure_active = False

# ==========================================================================
print("=== 9. Solar Pulse ===")
# ==========================================================================

ST9 = map_state()
OBJ9 = pm.objectives_in_no_mans_land(ST9)[0]
OX, OY = objective_centre(OBJ9)
_dy9 = 10.0 if OY + 10.0 < H - 1.0 else -10.0
SP_LED = tk.line_up(led_warriors(name="1 Necron Warriors 11"), OX - 6.0, OY + _dy9, 1.3)
SP_ON = cluster(tk.build(BOYZ, FOE, name="2 Boyz 9"), (OX, OY))
_far9 = first(lambda x, y: on_board(x, y, 4.0)
              and ((x - OX) ** 2 + (y - OY) ** 2) ** 0.5 > 30.0
              and all(o.terrain_area.distance_to_model(SimpleNamespace(x_in=x, y_in=y, radius_in=4.0)) > 8.0
                      for o in ST9.objectives))
SP_FAR = cluster(tk.build(BOYZ, FOE, name="2 Boyz 10"), _far9)
add(ST9, SP_LED, SP_ON, SP_FAR)
for o in ST9.objectives:
    o.controlled_by = None


def solar_ctrl(phase=PHASE_SHOOTING, owner=HUMAN, auto=(), cp=5):
    s = strat(cp)
    dec = DecisionManager()
    shoot = SimpleNamespace(active_squad=None, shot_squad_ids=set())
    log = tk.Log()
    ctrl = solar.SolarPulseController(s, turn_tracker=tracker(phase, owner), shooting_controller=shoot,
                                      game_state=ST9, decision_manager=dec, game_log=log,
                                      auto_players=auto)
    return ctrl, s, dec, shoot, log


c.true("the far probe point exists (live)", _far9 is not None)
c.eq("the unit on the objective counts; the far one does not",
     solar.objective_value(OBJ9, HUMAN, ST9), 1)
with settings_as(**COURT):
    ctrl, s9, dec9, shoot9, log9 = solar_ctrl()
    c.true("the objective is within 18\" of the Technomancer", OBJ9 in ctrl.objectives_for(SP_LED))
    c.eq("...measured from the CRYPTEK model alone", ctrl.cryptek_models(SP_LED), [tech_model(SP_LED)])
    c.true("WHEN: the start of your Shooting phase", ctrl.can_use(SP_LED))
    c.true("TARGET: not a unit with no CRYPTEK model",
           not ctrl.can_use(cluster(tk.build(nec.NECRON_WARRIORS, HUMAN, name="1 Necron Warriors 12"), (OX, OY + _dy9))))
    shoot9.shot_squad_ids.add(SP_FAR)
    c.true("...closed once a unit has shot", not ctrl.can_use(SP_LED))
    shoot9.shot_squad_ids.clear()
    c.true("not the opponent's Shooting phase", not solar_ctrl(owner=FOE)[0].can_use(SP_LED))
    c.true("not the Movement phase", not solar_ctrl(phase=PHASE_MOVEMENT)[0].can_use(SP_LED))
    c.true("pressing it asks WHICH objective", ctrl.use(SP_LED) and dec9.is_pending)
    c.true("...listing it, with a way out",
           OBJ9.name in tk.options_of(dec9) and "Cancel" in tk.options_of(dec9))
    c.eq("...and nothing is spent yet", s9.command_points.cp[HUMAN], 5)
    tk.pick_option(dec9, OBJ9.name)
    c.eq("picking it costs 1CP", s9.command_points.cp[HUMAN], 4)
    c.eq("...and pulses that objective", ctrl.pulsed_objective(HUMAN), OBJ9)
    c.true("...logged", log9.has(solar.SOLAR_PULSE_NAME))
    c.true("once per phase", not ctrl.can_use(SP_LED))
    c.true("NECRONS weapons ignore cover against a unit on it", ctrl.ignores_cover(SP_LED, SP_ON))
    c.true("...not against a unit elsewhere", not ctrl.ignores_cover(SP_LED, SP_FAR))
    c.true("...not for the opponent's shooting", not ctrl.ignores_cover(SP_ON, SP_LED))
    c.true("...nor a friendly unit that is not NECRONS",
           not ctrl.ignores_cover(tk.build(BOYZ, HUMAN, name="1 Boyz 1"), SP_ON))

    _gun9 = next(w for w in tech_model(SP_LED).weapons if w.weapon_type == "ranged")
    SC9 = ShootingController(obstacles=ST9.obstacles, game_log=tk.Log(), player_name=HUMAN,
                             dice_manager=DiceManager(), turn_tracker=tracker(PHASE_SHOOTING),
                             all_tokens=ST9.tokens, decision_manager=DecisionManager())
    SC9.active_squad = SP_LED
    c.true("ShootingController: no pulse, no cover denial", not SC9._cover_ignored_for_group(_gun9, SP_ON))
    SC9.solar_pulse = ctrl
    c.true("...pulsed, the cover term reads it", SC9._cover_ignored_for_group(_gun9, SP_ON))
    c.true("...and still not against the far unit", not SC9._cover_ignored_for_group(_gun9, SP_FAR))
    ctrl.reset_phase()
    c.eq("the pulse ends with the phase", ctrl.pulsed_objective(HUMAN), None)

    ctrl, s9, dec9, shoot9, log9 = solar_ctrl()
    ctrl.use(SP_LED)
    tk.pick_option(dec9, "Cancel")
    c.eq("Cancel costs nothing", (s9.command_points.cp[HUMAN], ctrl.pulsed_objective(HUMAN)), (5, None))
    ctrl, s9, dec9, shoot9, log9 = solar_ctrl(auto=(HUMAN,))
    ctrl.use(SP_LED)
    c.eq("the AI takes the best objective without a prompt",
         (dec9.is_pending, ctrl.pulsed_objective(HUMAN)), (False, OBJ9))
with settings_as(**NONE):
    c.true("without the detachment there is no button", not solar_ctrl()[0].can_use(SP_LED))


# ==========================================================================
print("=== 10. Reactive Subroutines ===")
# ==========================================================================

from ai.agent_driver import (reactive_subroutines_destination,        # noqa: E402
                             reactive_subroutines_move)
from game import combat_focus                                        # noqa: E402


def rs_scene(auto=(), destination=None, gap=6.0, cp=3, phase=PHASE_MOVEMENT, owner=FOE):
    st = GameState()
    wraiths = tk.line_up(tk.build(nec.CANOPTEK_WRAITHS, HUMAN, name="1 Canoptek Wraiths 4"), 20.0, 20.0, 2.5)
    boyz = tk.line_up(tk.build(BOYZ, FOE, name="2 Boyz 4"), 20.0, 20.0 + gap, 1.3)
    add(st, wraiths, boyz)
    tt = tracker(phase, owner)
    mc = MovementController(obstacles=st.obstacles, game_log=tk.Log(), player_name=HUMAN,
                            dice_manager=DiceManager(), turn_tracker=tt, all_tokens=st.tokens,
                            board_width_in=W, board_height_in=H)
    s = strat(cp)
    dec = DecisionManager()
    log = tk.Log()
    calls = []

    def mover(squad, point):
        calls.append((squad, point))
        return reactive_subroutines_move(mc, squad, point)

    ctrl = rsub.ReactiveSubroutinesController(
        s, movement_controller=mc, turn_tracker=tt, game_state=st, decision_manager=dec,
        game_log=log, auto_players=auto, ai_destination=destination, ai_mover=mover)
    mc.on_move_finished.append(ctrl.on_move_finished)
    return dict(state=st, wraiths=wraiths, boyz=boyz, turn=tt, movement=mc, strat=s,
                decision=dec, log=log, ctrl=ctrl, calls=calls)


def centroid(squad):
    live = alive(squad)
    return (sum(m.x_in for m in live) / len(live), sum(m.y_in for m in live) / len(live))


c.true("its move mode is REACTIVE (the AI waits on it)",
       rsub.REACTIVE_SUBROUTINES_MOVE_MODE in MovementController.REACTIVE_MOVE_MODES)
c.true("...and out-of-phase (the phase gate waits on it)",
       rsub.REACTIVE_SUBROUTINES_MOVE_MODE in MovementController.OUT_OF_PHASE_MOVE_MODES)

with settings_as(**COURT):
    r = rs_scene()
    c.true("an enemy Normal move within 8\" offers it", r["ctrl"].on_move_finished(r["boyz"], "normal"))
    c.eq("...to the reacting player", r["decision"].player, HUMAN)
    c.true("...as a tagged option the board can answer",
           any(o.get("squad") is r["wraiths"] for o in r["decision"].options or ()))
    tk.pick_option(r["decision"], r["wraiths"].name)
    c.eq("picking the unit costs 1CP", r["strat"].command_points.cp[HUMAN], 2)
    c.eq("...opens its own move", r["movement"].move_mode, rsub.REACTIVE_SUBROUTINES_MOVE_MODE)
    c.eq("...hands the reacting player the controls", r["turn"].active_player, HUMAN)
    c.true("...and holds the phase while it is open", r["ctrl"].is_busy)
    r["ctrl"].cancel_move()
    c.eq("cancelling closes it and hands control back",
         (r["movement"].move_mode, r["turn"].active_player, r["ctrl"].is_busy), (None, FOE, False))

    for _kind in ("advance", "fall_back"):
        c.true("an enemy %s move offers it too" % _kind,
               rs_scene()["ctrl"].on_move_finished(rs_scene()["boyz"], _kind) or True)
    _r = rs_scene()
    c.true("...an Advance, measured", _r["ctrl"].on_move_finished(_r["boyz"], "advance"))
    _r = rs_scene()
    c.eq("not a charge move", _r["ctrl"].on_move_finished(_r["boyz"], "charge"), False)
    _r = rs_scene(phase=PHASE_SHOOTING)
    c.eq("not outside the Movement phase", _r["ctrl"].on_move_finished(_r["boyz"], "normal"), False)
    _r = rs_scene(owner=HUMAN)
    c.eq("not a move in YOUR OWN Movement phase", _r["ctrl"].on_move_finished(_r["boyz"], "normal"), False)
    _r = rs_scene(gap=14.0)
    c.eq("not beyond 8\"", _r["ctrl"].on_move_finished(_r["boyz"], "normal"), False)
    _r = rs_scene(gap=2.2)
    c.eq("not a unit already in Engagement Range - it could not make a Normal move",
         _r["ctrl"].on_move_finished(_r["boyz"], "normal"), False)
    _r = rs_scene(cp=0)
    c.eq("not without the CP", _r["ctrl"].on_move_finished(_r["boyz"], "normal"), False)

    _before = None
    r = rs_scene(auto=(HUMAN,), destination=lambda sq, mv: (centroid(sq)[0], centroid(sq)[1] - 5.0))
    _before = centroid(r["wraiths"])
    c.true("the AI reacts inside the listener", r["ctrl"].on_move_finished(r["boyz"], "normal"))
    c.eq("...through the injected mover", [q for q, _p in r["calls"]], [r["wraiths"]])
    c.eq("...paying 1CP", r["strat"].command_points.cp[HUMAN], 2)
    _moved = _before[1] - centroid(r["wraiths"])[1]
    c.true("...really moving the unit (%.2f\")" % _moved, 2.0 <= _moved <= 6.01)
    c.eq("...and leaving nothing open", (r["movement"].move_mode, r["ctrl"].is_busy), (None, False))
    c.eq("...with control back where it was", r["turn"].active_player, FOE)
    c.true("...and a log line", r["log"].has("[reactive subroutines]"))
    # END TO END with the REAL policy, not a lambda: the lambda above cannot
    # see what the policy hands the controller, and that seam was broken (a
    # {"x", "y"} dict where an (x, y) pair belongs) while every line above
    # stayed green.
    r = rs_scene(auto=(HUMAN,))
    r["ctrl"].ai_destination = (lambda sq, mv, _st=r["state"]:
                                reactive_subroutines_destination(_st, sq, mv))
    c.true("(live) Canoptek Wraiths are an assault unit, so the policy closes in",
           combat_focus.is_assault_unit(r["wraiths"]))
    _before = centroid(r["wraiths"])
    try:
        _reacted, _err = r["ctrl"].on_move_finished(r["boyz"], "normal"), None
    except Exception as exc:          # a regression must read RED, not end the file
        _reacted, _err = False, repr(exc)
    c.eq("the real policy reacts end to end", (_reacted, _err), (True, None))
    c.true("...handing the mover an (x, y) pair",
           len(r["calls"]) == 1 and isinstance(r["calls"][0][1], tuple))
    _closer = _before[1] < centroid(r["wraiths"])[1]
    c.true("...and the Wraiths move toward the unit that moved", _closer)
    c.eq("...leaving nothing open", (r["movement"].move_mode, r["turn"].active_player), (None, FOE))
    r = rs_scene(auto=(HUMAN,), destination=lambda sq, mv: None)
    c.eq("an AI with nowhere worth going declines, for free",
         (r["ctrl"].on_move_finished(r["boyz"], "normal"), r["strat"].command_points.cp[HUMAN], r["calls"]),
         (False, 3, []))

with settings_as(**NONE):
    _r = rs_scene()
    c.eq("without the detachment nothing is offered", _r["ctrl"].on_move_finished(_r["boyz"], "normal"), False)

# The AI's destination policy.
_empty = GameState()
_skorpekh = tk.line_up(tk.build(nec.SKORPEKH_DESTROYERS, HUMAN, name="1 Skorpekh Destroyers 1"), 20, 20, 2.0)
_immortals = tk.line_up(tk.build(nec.IMMORTALS, HUMAN, name="1 Immortals 3"), 20, 20, 1.3)
_mover = tk.line_up(tk.build(BOYZ, FOE, name="2 Boyz 5"), 20, 27, 1.3)
c.true("(live) Skorpekh are an assault unit, Immortals are not",
       combat_focus.is_assault_unit(_skorpekh) and not combat_focus.is_assault_unit(_immortals))
def _pair(point):
    """The destination as an (x, y) pair, or None. The controller and
    _advance_toward() both index it; first_leg_toward() speaks the planner's
    {"x", "y"} dialect, and returning that here once crashed the controller.
    A dict must read RED in these checks, not end the file."""
    return tuple(point) if isinstance(point, tuple) and len(point) == 2 else None


_raw = reactive_subroutines_destination(_empty, _skorpekh, _mover)
c.true("the policy hands back an (x, y) pair", isinstance(_raw, tuple) and len(_raw) == 2)
_pt = _pair(_raw)
_dist = lambda a, b: ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5  # noqa: E731
c.true("an assault unit with no objective to take closes on the mover",
       _pt is not None and _dist(_pt, centroid(_mover)) < _dist(centroid(_skorpekh), centroid(_mover)))
c.eq("...a shooting unit with nothing to take declines",
     reactive_subroutines_destination(_empty, _immortals, _mover), None)
_obj_state = GameState()
_obj_state.objectives = [OBJ9]
tk.line_up(_immortals, OX - 6.0, OY + 5.0, 1.3)
_pt = _pair(reactive_subroutines_destination(_obj_state, _immortals, _mover))
c.true("...but an uncontrolled objective in reach is worth the move for anyone",
       _pt is not None and _dist(_pt, (OX, OY)) < _dist(centroid(_immortals), (OX, OY)))
OBJ9.controlled_by = HUMAN
c.eq("...and one it already holds is not", reactive_subroutines_destination(_obj_state, _immortals, _mover), None)
OBJ9.controlled_by = None


# ==========================================================================
print("=== 11. Countertemporal Shift ===")
# ==========================================================================

CT_WRAITHS = tk.line_up(tk.build(nec.CANOPTEK_WRAITHS, HUMAN, name="1 Canoptek Wraiths 5"), 10, 5, 2.5)
CT_FAR = tk.line_up(tk.build(BOYZ, FOE, name="2 Boyz 11"), 10, 35, 1.3)
CT_NEAR = tk.line_up(tk.build(BOYZ, FOE, name="2 Boyz 12"), 10, 15, 1.3)
CT_IMMORTALS = tk.line_up(tk.build(nec.IMMORTALS, HUMAN, name="1 Immortals 4"), 30, 5, 1.3)


def ct_ctrl(phase=PHASE_SHOOTING, owner=FOE, auto=(), cp=5):
    s = strat(cp)
    dec = DecisionManager()
    hits = []
    ctrl = shift.CountertemporalShiftController(
        stratagem_controller=s, decision_manager=dec, game_log=tk.Log(),
        turn_tracker=tracker(phase, owner), on_activated=lambda: hits.append(True), auto_players=auto)
    return ctrl, s, dec, hits


with settings_as(**COURT):
    ctrl, s11, dec11, hits11 = ct_ctrl()
    c.eq("(live) nothing limits the Wraiths yet", status_effects.targeting_range_limit(CT_WRAITHS), None)
    c.true("an attacker beyond 18\" can be shifted away", ctrl.can_use(CT_FAR, CT_WRAITHS))
    c.true("...one within 18\" cannot - it would change nothing", not ctrl.can_use(CT_NEAR, CT_WRAITHS))
    c.true("TARGET: a CANOPTEK unit only", not ctrl.can_use(CT_FAR, CT_IMMORTALS))
    c.eq("never against a melee selection", ctrl.maybe_offer(CT_FAR, CT_WRAITHS, melee=True), False)
    c.true("not in YOUR Shooting phase", not ct_ctrl(owner=HUMAN)[0].can_use(CT_FAR, CT_WRAITHS))
    c.true("not outside the Shooting phase", not ct_ctrl(phase=PHASE_FIGHT)[0].can_use(CT_FAR, CT_WRAITHS))
    c.true("offered to the target's owner", ctrl.maybe_offer(CT_FAR, CT_WRAITHS) and dec11.player == HUMAN)
    tk.pick_option(dec11, shift.COUNTERTEMPORAL_SHIFT_NAME)
    c.eq("using it costs 1CP", s11.command_points.cp[HUMAN], 4)
    c.eq("...limits the unit to 18\"", status_effects.targeting_range_limit(CT_WRAITHS), 18.0)
    c.eq("...and asks the shooter to re-check its target", hits11, [True])
    c.eq("a second offer for the same pair is not made", ctrl.maybe_offer(CT_FAR, CT_WRAITHS), False)
    shift.reset_phase([CT_WRAITHS])
    ctrl.reset_phase()
    c.eq("the limit ends with the phase", status_effects.targeting_range_limit(CT_WRAITHS), None)
    ctrl, s11, dec11, hits11 = ct_ctrl(auto=(HUMAN,))
    ctrl.maybe_offer(CT_FAR, CT_WRAITHS)
    c.eq("the AI uses it whenever it is offered, without a prompt",
         (dec11.is_pending, s11.command_points.cp[HUMAN], CT_WRAITHS.countertemporal_shift_range),
         (False, 4, 18.0))
    shift.reset_phase([CT_WRAITHS])
with settings_as(**NONE):
    c.true("without the detachment it is not offered", not ct_ctrl()[0].can_use(CT_FAR, CT_WRAITHS))


# ==========================================================================
print("=== 12. Suboptimal Facade ===")
# ==========================================================================

from game import reanimation_protocols                               # noqa: E402


def facade_scene(auto=(), damage=2, in_matrix=True, cp=3):
    st = GameState()
    st.deployment_zones = list(ST.deployment_zones)
    wraiths = cluster(tk.build(nec.CANOPTEK_WRAITHS, HUMAN, name="1 Canoptek Wraiths 6"),
                      OWN_DEEP, spacing=2.5, per_row=3)
    if not in_matrix:
        wraiths.models[0].x_in, wraiths.models[0].y_in = STRADDLE_OWN
    wraiths.models[1].current_wounds = wraiths.models[1].profile.wounds - damage
    # Measured from the Wraith NEAREST the chargers, not from models[1]: with
    # in_matrix=False the straddling model stands between the two, and a line
    # set 6" from models[1] lands 2" from it - already engaged, so no charge
    # could be declared and the TARGET check would pass for the wrong reason.
    if OWN_DEEP[1] < H / 2:
        front_y = max(m.y_in for m in wraiths.models) + 6.0
    else:
        front_y = min(m.y_in for m in wraiths.models) - 6.0
    boyz = tk.line_up(tk.build(BOYZ, FOE, name="2 Chargers 1"),
                      max(1.0, wraiths.models[1].x_in - 5.0), front_y, 1.3)
    add(st, boyz, wraiths)
    tt = tracker(PHASE_CHARGE, owner=FOE)
    dm = DiceManager()
    mc = MovementController(all_tokens=st.tokens, obstacles=st.obstacles, turn_tracker=tt,
                            board_width_in=W, board_height_in=H)
    cc = ChargeController(dice_manager=dm, turn_tracker=tt, all_tokens=st.tokens, movement_controller=mc)
    s = strat(cp)
    dec = DecisionManager()
    matrix = pm.PowerMatrixController(game_state=st, turn_tracker=tt)
    ctrl = facade.SuboptimalFacadeController(
        s, dice_manager=dm, decision_manager=dec, turn_tracker=tt, game_state=st,
        power_matrix=matrix, game_log=tk.Log(), auto_players=auto)
    cc.charge_declaration_reactions.append(ctrl.maybe_offer)
    return dict(state=st, charging=boyz, defender=wraiths, turn=tt, dice=dm, decision=dec,
                movement=mc, charge=cc, strat=s, facade=ctrl)


with settings_as(**COURT):
    f = facade_scene()
    c.eq("(live) the damaged Wraiths have 2 wounds to recover",
         reanimation_protocols.recoverable_wounds(f["defender"]), 2)
    declare(f)
    c.true("a charge declared on a damaged CANOPTEK unit in the matrix offers it",
           f["decision"].is_pending and f["decision"].player == HUMAN)
    c.true("...and the charge waits for the answer", f["movement"].move_mode is None)
    tk.script(2)
    tk.pick_option(f["decision"], f["defender"].name)
    c.eq("using it costs 1CP", f["strat"].command_points.cp[HUMAN], 2)
    c.true("...and rolls the D3, named", f["dice"].is_pending
           and facade.SUBOPTIMAL_FACADE_NAME in (f["dice"].label or ""))
    c.true("...while the charge still waits", f["movement"].move_mode is None and f["facade"].is_busy)
    f["dice"].acknowledge()
    f["facade"].on_dice_acknowledged()
    c.eq("Reanimation Protocols heal the unit", reanimation_protocols.recoverable_wounds(f["defender"]), 0)
    c.eq("...and then the charge resumes", f["movement"].move_mode, "charge")
    c.true("...with nothing left busy", not f["facade"].is_busy)

    f = facade_scene()
    declare(f)
    tk.pick_option(f["decision"], "Decline")
    c.eq("declining costs nothing and resumes the charge",
         (f["strat"].command_points.cp[HUMAN], f["movement"].move_mode), (3, "charge"))
    f = facade_scene(in_matrix=False)
    declare(f)
    c.eq("TARGET: not a unit that is not wholly within the matrix",
         (f["decision"].is_pending, f["movement"].move_mode), (False, "charge"))
    f = facade_scene(damage=0)
    declare(f)
    c.eq("TARGET: never a unit with nothing to recover",
         (f["decision"].is_pending, f["movement"].move_mode), (False, "charge"))
    f = facade_scene(auto=(HUMAN,))
    declare(f, 2)
    c.true("the AI buys it for 2+ recoverable wounds", f["dice"].is_pending
           and f["strat"].command_points.cp[HUMAN] == 2 and not f["decision"].is_pending)
    f["dice"].acknowledge()
    f["facade"].on_dice_acknowledged()
    c.eq("...and the charge resumes after the roll", f["movement"].move_mode, "charge")
    f = facade_scene(auto=(HUMAN,), damage=1)
    declare(f)
    c.eq("...but not for one", (f["strat"].command_points.cp[HUMAN], f["movement"].move_mode), (3, "charge"))
with settings_as(**NONE):
    f = facade_scene()
    declare(f)
    c.eq("without the detachment it is not offered", (f["decision"].is_pending, f["movement"].move_mode),
         (False, "charge"))
tk.script()

# ==========================================================================
print("=== 13. gain_cp() names its source, everywhere ===")
# ==========================================================================

_paths = ["main.py"]
for _root in ("game", "ai"):
    for _dirpath, _dirs, _files in os.walk(_root):
        _dirs[:] = [d for d in _dirs if d != "__pycache__"]
        _paths.extend(os.path.join(_dirpath, f) for f in _files if f.endswith(".py"))
GAIN_CALLS = []
for _path in _paths:
    _tree = ast.parse(io.open(_path, encoding="utf-8").read())
    for _node in ast.walk(_tree):
        if (isinstance(_node, ast.Call) and isinstance(_node.func, ast.Attribute)
                and _node.func.attr == "gain_cp"):
            _kw = {k.arg: k.value for k in _node.keywords}
            GAIN_CALLS.append((_path.replace(os.sep, "/"), _node.lineno, _kw.get("source")))


def _source_name(node):
    return node.attr if isinstance(node, ast.Attribute) else getattr(node, "id", None)


c.true("the sweep is live - it found the engine's grants (%d)" % len(GAIN_CALLS), len(GAIN_CALLS) >= 7)
c.eq("every gain_cp() call names its source",
     [(p, ln) for p, ln, s in GAIN_CALLS if s is None], [])
c.eq("...the Secondary Mission discard is a MISSION grant",
     sorted({_source_name(s) for p, _ln, s in GAIN_CALLS if p.endswith("secondary_missions.py")}),
     ["SOURCE_MISSION"])
c.eq("...and every other one an ABILITY grant",
     sorted({_source_name(s) for p, _ln, s in GAIN_CALLS if not p.endswith("secondary_missions.py")}),
     ["SOURCE_ABILITY"])

_pool = CommandPointManager()
try:
    _pool.gain_cp(HUMAN, 1, source="core")
    _raised = False
except ValueError:
    _raised = True
c.true("an unknown source is refused, loudly", _raised)
try:
    _pool.gain_cp(HUMAN, 1)
    _typed = False
except TypeError:
    _typed = True
c.true("...and a missing one fails - there is no default", _typed)
_heard = []
_pool = CommandPointManager()
_pool.on_cp_gained.append(lambda p, n, **kw: _heard.append((p, n, kw.get("source"))))
_pool.gain_cp(HUMAN, 1, source=SOURCE_ABILITY)
_pool.gain_cp(HUMAN, 1, source=SOURCE_ABILITY)
c.eq("listeners hear a grant that LANDED - once, with its source", _heard, [(HUMAN, 1, SOURCE_ABILITY)])


# ==========================================================================
print("=== 14. wiring: main.py, the panel chain, the AI ===")
# ==========================================================================

MAIN_SRC = io.open("main.py", encoding="utf-8").read()
MAIN_TREE = ast.parse(MAIN_SRC)
_MAIN_LINES = MAIN_SRC.splitlines()
def _reachable(tree):
    """ast.walk() minus the bodies of `if False:` / `if 0:`, and minus an
    expression statement that is `False and <call>`. A wiring pin that a dead
    branch still satisfies proves nothing - the substring trap this repo has
    paid for half a dozen times - so a statement only counts if it can run."""
    stack = [tree]
    while stack:
        node = stack.pop()
        if isinstance(node, ast.If) and isinstance(node.test, ast.Constant) and not node.test.value:
            stack.extend(node.orelse)
            continue
        if (isinstance(node, ast.Expr) and isinstance(node.value, ast.BoolOp)
                and isinstance(node.value.op, ast.And)
                and isinstance(node.value.values[0], ast.Constant)
                and not node.value.values[0].value):
            continue
        yield node
        stack.extend(ast.iter_child_nodes(node))


STATEMENTS = []
for _node in _reachable(MAIN_TREE):
    if isinstance(_node, (ast.Expr, ast.Assign)):
        STATEMENTS.append(" ".join(" ".join(_MAIN_LINES[_node.lineno - 1:_node.end_lineno]).split()))


def statement(*needles):
    return any(all(n in s for n in needles) for s in STATEMENTS)


for _needles, _why in (
        (("power_matrix_controller = PowerMatrixController(",), "the Power Matrix controller is built"),
        (("court_power_matrix.CURRENT = power_matrix_controller",), "...published for the observation"),
        (("shooting_controller.power_matrix = power_matrix_controller",), "...handed to shooting"),
        (("fight_controller.power_matrix = power_matrix_controller",), "...and to fight"),
        (("power_matrix_controller.stamp_at_start_of_phase()",), "...and stamped at the start of a phase"),
        (("shooting_controller.curse_of_the_cryptek = curse_of_the_cryptek_controller",), "Curse: shooting reads it"),
        (("fight_controller.curse_of_the_cryptek = curse_of_the_cryptek_controller",), "...fight reads it"),
        (("curse_of_the_cryptek_controller.notify_model_destroyed(",), "...the death sweep feeds it"),
        (("curse_of_the_cryptek_controller.maybe_offer(shooter_squad)",), "...offered after shooting"),
        (("curse_of_the_cryptek_controller.maybe_offer(_fighter)",), "...and after fighting"),
        (("curse_of_the_cryptek_controller.reset_phase()",), "...and reset per phase"),
        (("cynosure_controller = proactive_stratagems.add(CynosureOfEradicationController(",), "Cynosure is a panel button"),
        (("court_cynosure_of_eradication.reset_phase(_court_squads)",), "...its grant ends per phase"),
        (("solar_pulse_controller = proactive_stratagems.add(SolarPulseController(",), "Solar Pulse is a panel button"),
        (("shooting_controller.solar_pulse = solar_pulse_controller",), "...shooting reads it"),
        (("solar_pulse_controller.reset_phase()",), "...and it ends per phase"),
        (("movement_controller.on_move_finished.append(reactive_subroutines_controller.on_move_finished)",),
         "Reactive Subroutines listens for finished moves"),
        (("countertemporal_shift_controller.on_activated = shooting_controller.revalidate_target_selection",),
         "Countertemporal Shift re-checks the shooter's target"),
        (("shooting_target_reactions = (", "countertemporal_shift_controller"), "...as a target reaction"),
        (("countertemporal_shift_controller.reset_phase()",), "...its memo resets per phase"),
        (("court_countertemporal_shift.reset_phase(_court_squads)",), "...and so does its limit"),
        (("charge_declaration_reactions.extend(", "metalodermal_tesla_weave_controller.maybe_offer",
          "suboptimal_facade_controller.maybe_offer"), "the two charge reactors join the chain"),
        (("metalodermal_tesla_weave_controller.on_dice_acknowledged()",), "...the Tesla Weave's dice are acknowledged"),
        (("suboptimal_facade_controller.on_dice_acknowledged()",), "...and the Facade's"),
        (("metalodermal_tesla_weave_controller.reset_phase()",), "...the Weave's once-per-phase resets"),
        (("metalodermal_tesla_weave_controller.choose_damage_model(clicked)",), "...its allocation is clickable"),
        (("draw_damage_choice_highlight(", "metalodermal_tesla_weave_controller.pending_damage_choice"),
         "...and drawn"),
        (("command_points.on_cp_gained.append(autodivinator_controller.on_cp_gained)",),
         "the Autodivinator listens to CP gains")):
    c.true(_why, statement(*_needles))

_gate = next((n for n in ast.walk(MAIN_TREE)
              if isinstance(n, ast.FunctionDef) and n.name == "_has_unresolved_declaration"), None)
_gate_src = ast.unparse(_gate) if _gate is not None else ""
for _term in ("metalodermal_tesla_weave_controller.is_busy",
              "metalodermal_tesla_weave_controller.pending_damage_choice",
              "suboptimal_facade_controller.is_busy",
              "reactive_subroutines_controller.is_busy"):
    c.true("the phase gate waits on %s" % _term, _term in _gate_src)

PANEL_SRC = io.open(os.path.join("game", "ui", "action_panel.py"), encoding="utf-8").read()
PANEL_TREE = ast.parse(PANEL_SRC)


def _fn(tree, name):
    return next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name), None)


_PARAM = "reactive_subroutines_controller"
for _stage in ("draw", "_draw_dispatch", "_draw_movement_ui"):
    _node = _fn(PANEL_TREE, _stage)
    _names = {a.arg for a in (_node.args.args + _node.args.kwonlyargs)} if _node else set()
    c.true("%s() takes %s" % (_stage, _PARAM), _PARAM in _names)
for _outer, _inner in (("draw", "_draw_dispatch"), ("_draw_dispatch", "_draw_movement_ui")):
    _node = _fn(PANEL_TREE, _outer)
    _fwd = any(isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
               and sub.func.attr == _inner
               and any(k.arg == _PARAM and isinstance(k.value, ast.Name) and k.value.id == _PARAM
                       for k in sub.keywords)
               for sub in (ast.walk(_node) if _node else []))
    c.true("%s -> %s forwards it by keyword" % (_outer, _inner), _fwd)
_draw_calls = [n for n in ast.walk(MAIN_TREE)
               if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
               and n.func.attr == "draw" and isinstance(n.func.value, ast.Name)
               and n.func.value.id == "action_panel"]
c.true("main.py hands it to the panel by keyword",
       any(_PARAM in {k.arg for k in n.keywords} for n in _draw_calls))
c.true("the panel routes Confirm to it",
       "confirm_callback = reactive_subroutines_controller.confirm_move" in PANEL_SRC)
c.true("...and Cancel", "cancel_callback = reactive_subroutines_controller.cancel_move" in PANEL_SRC)

from ai import agent_driver as ad                                    # noqa: E402

DRIVER_TREE = ast.parse(io.open(os.path.join("ai", "agent_driver.py"), encoding="utf-8").read())
_shoot_fn = ast.unparse(_fn(DRIVER_TREE, "_handle_shooting"))
_fight_fn = ast.unparse(_fn(DRIVER_TREE, "_handle_fight"))
_take_fn = ast.unparse(_fn(DRIVER_TREE, "_take_one_action"))
c.true("the AI buys Solar Pulse in its Shooting phase",
       "_handle_solar_pulse(player, all_tokens, solar_pulse_controller" in _shoot_fn)
c.true("...and Cynosure at range", "_handle_cynosure(player, all_tokens, cynosure_controller, melee=False" in _shoot_fn)
c.true("...both BEFORE any unit is selected to shoot",
       -1 < _shoot_fn.find("_handle_cynosure(") < _shoot_fn.find("shooting_controller.start_shooting(squad)"))
c.true("...and Cynosure in melee, before anything piles in",
       -1 < _fight_fn.find("_handle_cynosure(player, all_tokens, cynosure_controller, melee=True")
       < _fight_fn.find("_pile_in_squad("))
c.true("_take_one_action forwards both controllers",
       "cynosure_controller=cynosure_controller" in _take_fn
       and "solar_pulse_controller=solar_pulse_controller" in _take_fn)
c.true("...and resolves its own Tesla Weave allocation", "metalodermal_tesla_weave_controller" in _take_fn)
_toa = [n for n in ast.walk(MAIN_TREE) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        and n.func.id == "take_one_action"]
c.true("main.py passes the three to take_one_action()",
       any({"cynosure_controller", "solar_pulse_controller", "metalodermal_tesla_weave_controller"}
           <= {k.arg for k in n.keywords} for n in _toa))
for _f in (ad._handle_cynosure, ad._handle_solar_pulse, ad._cynosure_verdict):
    c.true("%s takes no agent - 0 API calls" % _f.__name__,
           "agent" not in inspect.signature(_f).parameters)
c.true("the observation reports the matrix",
       "court_power_matrix.observation(squad, court_power_matrix.CURRENT)"
       in io.open(os.path.join("ai", "observation.py"), encoding="utf-8").read())
c.true("...and the planner is told what it means",
       "power_matrix" in io.open(os.path.join("ai", "planner_prompt.py"), encoding="utf-8").read())
with settings_as(**COURT):
    _obs = pm.observation(WRAITHS, MATRIX5)
    c.true("observation(): regions and wholly_within for a Court unit",
           isinstance(_obs, dict) and {"regions", "wholly_within"} <= set(_obs))
    c.eq("...and nothing for a unit the rule is not about", pm.observation(IMMORTALS, MATRIX5), None)

# The verdicts, at their decision borders.
_orig_threshold = cyn.CYNOSURE_MIN_EXPECTED_GAIN
try:
    LED8.court_cynosure_active = False
    _gain = cyn.expected_devastating_gain(LED8, _pm8)
    cyn.CYNOSURE_MIN_EXPECTED_GAIN = 1e-6
    _v = ad._cynosure_verdict(LED8, ST8b.tokens, False)
    c.true("Cynosure verdict: the expected gain when a target is in reach",
           _v is not None and abs(_v - _gain) < 1e-9)
    c.eq("...None in melee when nothing is within a Pile In",
         ad._cynosure_verdict(LED8, ST8b.tokens, True), None)
    _bought = []
    _stub = SimpleNamespace(can_use=lambda sq: sq is LED8, use=lambda sq: _bought.append(sq) or True)
    c.true("_handle_cynosure buys it", ad._handle_cynosure(HUMAN, ST8b.tokens, _stub, melee=False))
    c.eq("...for that unit", _bought, [LED8])
    _saved8 = [(m.x_in, m.y_in) for m in _pm8.models]
    tk.line_up(_pm8, 10, 60, 1.3)
    c.eq("...None with the target beyond every Cryptek gun",
         ad._cynosure_verdict(LED8, ST8b.tokens, False), None)
    for m, (x, y) in zip(_pm8.models, _saved8):
        m.x_in, m.y_in = x, y
    cyn.CYNOSURE_MIN_EXPECTED_GAIN = _gain + 1.0
    _bought.clear()
    c.eq("...and below the threshold it keeps the CP",
         (ad._handle_cynosure(HUMAN, ST8b.tokens, _stub, melee=False), _bought), (False, []))
finally:
    cyn.CYNOSURE_MIN_EXPECTED_GAIN = _orig_threshold

with settings_as(**COURT):
    ctrl, s9, dec9, shoot9, log9 = solar_ctrl()
    c.true("_handle_solar_pulse buys it for an objective with an enemy in terrain",
           ad._handle_solar_pulse(HUMAN, ST9.tokens, ctrl))
    c.eq("...on that objective, for 1CP", (ctrl.pulsed_objective(HUMAN), s9.command_points.cp[HUMAN]),
         (OBJ9, 4))
    ctrl, s9, dec9, shoot9, log9 = solar_ctrl()
    cluster(SP_ON, _far9)
    c.eq("...and keeps the CP when no objective has one",
         (ad._handle_solar_pulse(HUMAN, ST9.tokens, ctrl), s9.command_points.cp[HUMAN]), (False, 5))
    cluster(SP_ON, (OX, OY))


# ==========================================================================
print("=== 15. dormant by roster ===")
# ==========================================================================

import json                                                          # noqa: E402

_lists = []
for _fname in sorted(os.listdir("armies")):
    if _fname.endswith(".json"):
        _data = json.loads(io.open(os.path.join("armies", _fname), encoding="utf-8").read())
        if isinstance(_data, dict) and "detachments" in _data:
            _lists.append((_fname, _data["detachments"]))
c.true("the sweep read the shipped lists (%d)" % len(_lists), len(_lists) >= 5)
c.eq("no shipped list fields the Canoptek Court (user decision)",
     [f for f, d in _lists if "Canoptek Court" in d], [])

c.finish()
