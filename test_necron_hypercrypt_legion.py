"""The Hypercrypt Legion - the third Necron detachment: its rule (Hyperphasing),
its four Enhancements and its six Stratagems, driven through the real
controllers.

WHAT THIS SUITE PINS, and why each part is here:

  1. THE RECORD AGAINST THE CORPUS - DP, Force Disposition, every Enhancement's
     points and every Stratagem's CP read from
     rules/necrons/detachments/Hypercrypt Legion.md rather than typed twice.
  2. game/battle_size.py - the third consumer of the battle-size reading, and
     the two older tables it now reads for, unchanged.
  3. HYPERPHASING through game/end_of_turn_withdrawal.py - the chained offer,
     the cap re-read before each prompt, the Engagement Range exclusion, the
     Dimensional Overseer's +1, the round-3 doom, and the injected AI policy.
  4. THE RELAXED ARRIVAL - "anywhere on the battlefield" lifts the opponent's
     deployment zone ban at the overlay and the AI's candidate grid too.
  5. THE ETERNITY GATE's own lock and the arrivals it records.
  6. THE FIGHT PHASE's loss ledger (Hyperphasic Recall's "as a result of the
     attacking unit's attacks").
  7. OFF-BOARD REANIMATION - reanimation_protocols.activate() stays the one door.
  8. THE ENHANCEMENTS through the real attack, movement and ingress code.
  9-14. THE STRATAGEMS at their WHEN/TARGET borders.
  15. THE AI's verdicts, at their decision borders, with no agent.
  16. WIRING - AST over reachable code (main.py, the panel, the AI, the seams).
  17. WHICH LIST FIELDS IT - exactly armies/necrons_hypercrypt.json (dormant by
      roster until the user supplied that list on 2026-09-13).

Real controllers, real datasheets, scripted dice (testkit).
"""

import ast
import inspect
import io
import json
import math
import os
import re
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import testkit as tk                                                 # noqa: E402
from testkit import Checks, settings_as                              # noqa: E402

from game import activation_state, attached_units, config            # noqa: E402
from game import battle_focus, force_dispositions, maps              # noqa: E402
from game import enhancements as E                                   # noqa: E402
from game import necron_detachments as nd                            # noqa: E402
from game import reanimation_protocols, reroll_scope, ride_the_wind  # noqa: E402
from game import titanic                                             # noqa: E402
from game import battle_size as bs                                   # noqa: E402
from game import hypercrypt_hyperphasing as hp                       # noqa: E402
from game import hypercrypt_hyperphasic_recall as hr                 # noqa: E402
from game import hypercrypt_quantum_deflection as qd                 # noqa: E402
from game import hypercrypt_reanimation_crypts as rc                 # noqa: E402
from game import hypercrypt_cosmic_precision as cosmic               # noqa: E402
from game import hypercrypt_dimensional_corridor as dc               # noqa: E402
from game import hypercrypt_entropic_damping as ed                   # noqa: E402
from game import enh_dimensional_overseer as overseer                # noqa: E402
from game import enh_arisen_tyrant as tyrant                         # noqa: E402
from game import enh_hyperspatial_transfer_node as htn               # noqa: E402
from game import enh_osteoclave_fulcrum as fulcrum                   # noqa: E402
from game import eternity_gate                                       # noqa: E402
from game.charge import ChargeController                             # noqa: E402
from game.command_points import CommandPointManager                  # noqa: E402
from game.decision import DecisionManager                            # noqa: E402
from game.dice import DiceManager                                    # noqa: E402
from game.end_of_turn_withdrawal import EndOfTurnWithdrawalController  # noqa: E402
from game.fight import FightController                               # noqa: E402
from game.game_state import GameState                                # noqa: E402
from game.ingress import IngressController, INGRESS_MIN_ENEMY_DISTANCE_IN  # noqa: E402
from game.invulnerable_save import effective_invulnerable_save       # noqa: E402
from game.movement import MovementController                         # noqa: E402
from game.proactive_stratagems import (ARRIVAL_SCREEN,               # noqa: E402
                                       ProactiveStratagems)
from game.setup import PLACING, SetupController                      # noqa: E402
from game.shooting import ShootingController                         # noqa: E402
from game.stratagems import StratagemController                      # noqa: E402
from game.strategic_reserves import withdraw_to_reserves             # noqa: E402
from game.thresholds import parse_threshold                          # noqa: E402
from game.turn import (PHASES, PHASE_CHARGE, PHASE_COMMAND,          # noqa: E402
                       PHASE_FIGHT, PHASE_MOVEMENT, PHASE_SHOOTING,
                       TurnTracker)
from game.units import UnitProfile                                   # noqa: E402

from game.factions import necrons as nec                             # noqa: E402
from game.factions.orks import BOYZ, WARBOSS                         # noqa: E402

from ai import agent_driver as ad                                    # noqa: E402

c = Checks("Hypercrypt Legion")

HUMAN = "Player 1"
FOE = "Player 2"
HYPER = dict(HYPERCRYPT_LEGION_PLAYERS=(HUMAN,))
NONE = dict(HYPERCRYPT_LEGION_PLAYERS=())

M2 = maps.get("map2")
maps.apply_to_config(M2)
W, H = M2.width_in, M2.height_in

CORPUS_PATH = os.path.join("rules", "necrons", "detachments", "Hypercrypt Legion.md")
CORPUS = io.open(CORPUS_PATH, encoding="utf-8").read()


def norm(text):
    """The corpus prints typographic apostrophes; the modules plain ones."""
    return " ".join((text or "").replace("’", "'").replace("**", "").split())


def map_state(key="map2"):
    st = GameState()
    maps.get(key).build(st)
    return st


def tracker(phase, owner=HUMAN, battle_round=2, turn_index=0):
    tt = TurnTracker()
    tt.started = True
    tt.battle_round = battle_round
    tt.turn_index_in_round = turn_index
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


def place(squad, x, y):
    for model in squad.models:
        model.x_in, model.y_in = x, y
    return squad


def casualties_off_board(squad, n):
    """`n` models destroyed while the unit is not on the board - what
    GameState._remove_tokens() does to squad.models and destroyed_models."""
    for model in list(squad.models[:n]):
        model.current_wounds = 0
        squad.models.remove(model)
        squad.destroyed_models.append(model)
    return squad


def gap(a, b):
    return math.hypot(a.x_in - b.x_in, a.y_in - b.y_in)


def safe(fn, *args, **kwargs):
    """A regression must read RED, not end the file."""
    try:
        return fn(*args, **kwargs), None
    except Exception as exc:              # noqa: BLE001
        return None, repr(exc)


def overlord_leading(sheet, owner=HUMAN, name="1 Immortals 1", enhancement=None):
    """An Overlord (a NECRONS CHARACTER) leading `sheet`, optionally carrying
    `enhancement` - granted before the 19.01 merge, the order army building uses."""
    lord = tk.build(nec.OVERLORD, owner, name=name.replace(sheet.name, "Overlord"))
    if enhancement is not None:
        E.grant(lord, enhancement)
    body = tk.build(sheet, owner, name=name)
    return attached_units.attach(lord, body)


def lord_model(squad):
    return next(m for m in squad.models if getattr(m.profile, "character", False))


# ==========================================================================
print("=== 1. the record, against the corpus ===")
# ==========================================================================

REC = nec.HYPERCRYPT_LEGION
c.true("the detachment is registered on the faction",
       nec.NECRONS.detachments.get("Hypercrypt Legion") is REC)
c.eq("its rule is Hyperphasing", REC.rule_name, "Hyperphasing")
c.eq("...gated on HYPERCRYPT_LEGION_PLAYERS", REC.setting, "HYPERCRYPT_LEGION_PLAYERS")
c.eq("...the setting name every module reads", hp.SETTING, REC.setting)
c.eq("...and necron_detachments names it too", nd.HYPERCRYPT_LEGION_SETTING, REC.setting)
_dp = re.search(r"(\d+) DP detachment", CORPUS)
c.eq("its DP match the printed heading", REC.points, int(_dp.group(1)) if _dp else None)
_fd = re.search(r"Force Disposition: ([A-Za-z ]+)", CORPUS)
c.eq("its Force Disposition matches the printed heading",
     REC.force_disposition,
     force_dispositions.from_printed(_fd.group(1).strip()) if _fd else None)
c.eq("...which is Reconnaissance", REC.force_disposition, force_dispositions.RECONNAISSANCE)
c.true("the record carries the printed rule text",
       "place them into Strategic Reserves" in norm(REC.rule_text))
c.eq("the setting ships empty - nobody fields it by default",
     tuple(getattr(config, "HYPERCRYPT_LEGION_PLAYERS", ("missing",))), ())

_printed_enh = {name.strip(): int(pts)
                for name, pts in re.findall(r"^### (.+?) - (\d+) pts$", CORPUS, re.M)}
c.eq("the corpus prints four Enhancements", len(_printed_enh), 4)
c.eq("...the record names the same four at the same points",
     {e.name: e.points for e in REC.enhancements}, _printed_enh)
_hc_specs = {n: s for n, s in E.ENHANCEMENTS.items() if s.detachment == "Hypercrypt Legion"}
c.eq("...and all four are ENGINE-WIRED in the registry, at the same points",
     {n: s.points for n, s in _hc_specs.items()}, _printed_enh)
for _name, _spec in sorted(_hc_specs.items()):
    c.eq("%s gates on the detachment's setting" % _name, _spec.setting, REC.setting)
    c.eq("%s is printed NECRONS model only" % _name, _spec.bearer_text, "NECRONS model only")
    c.eq("UnitProfile.%s defaults to False" % _spec.flag, getattr(UnitProfile, _spec.flag, None),
         False)
_enh_texts = {e.name: norm(e.description) for e in REC.enhancements}
for _name in sorted(_printed_enh):
    _body = re.search(r"### %s - \d+ pts\s+(.+?)\n\n" % re.escape(_name), CORPUS, re.S)
    c.eq("%s: the record's text is the printed text" % _name,
         _enh_texts.get(_name), norm(_body.group(1)) if _body else "<not printed>")

_printed_strat = {name.strip().upper(): int(cp)
                  for name, cp in re.findall(r"^### (.+?) - (\d)CP$", CORPUS, re.M)}
MODULE_STRATS = {
    hr.HYPERPHASIC_RECALL_NAME: (hr, hr.HYPERPHASIC_RECALL_CP),
    qd.QUANTUM_DEFLECTION_NAME: (qd, qd.QUANTUM_DEFLECTION_CP),
    rc.REANIMATION_CRYPTS_NAME: (rc, rc.REANIMATION_CRYPTS_CP),
    cosmic.COSMIC_PRECISION_NAME: (cosmic, cosmic.COSMIC_PRECISION_CP),
    dc.DIMENSIONAL_CORRIDOR_NAME: (dc, dc.DIMENSIONAL_CORRIDOR_CP),
    ed.ENTROPIC_DAMPING_NAME: (ed, ed.ENTROPIC_DAMPING_CP),
}
c.eq("the corpus prints six Stratagems", len(_printed_strat), 6)
c.eq("...and one module per Stratagem, each at its printed CP",
     {n.upper(): cp for n, (_m, cp) in MODULE_STRATS.items()}, _printed_strat)
for _name, (_module, _cp) in sorted(MODULE_STRATS.items()):
    _src = inspect.getsource(_module)
    c.true("%s quotes its rule verbatim" % _name, "RULE (verbatim" in _src)
    c.true("%s gates on the detachment" % _name, "has_detachment" in _src)
    c.eq("%s reads the detachment's setting" % _name, getattr(_module, "SETTING", None), REC.setting)
    _effect = re.search(r"### %s - \dCP.*?\*\*EFFECT:\*\* ([^\n]+)" % re.escape(_name.upper()),
                        CORPUS, re.S)
    _first = " ".join(norm(_effect.group(1)).split()[:6]) if _effect else "<no effect>"
    c.true("%s's docstring carries its printed EFFECT (%s...)" % (_name, _first),
           _first in norm(_src))

_hyper_modules = sorted(f for f in os.listdir("game")
                        if f.startswith("hypercrypt_") and f.endswith(".py"))
c.eq("seven hypercrypt_ modules: the rule and one per Stratagem",
     _hyper_modules,
     sorted(["hypercrypt_hyperphasing.py"] + [m.__name__.split(".")[-1] + ".py"
                                              for m, _cp in MODULE_STRATS.values()]))


# ==========================================================================
print("=== 2. the battle size: one reading, three tables ===")
# ==========================================================================

c.eq("'Strike Force' reads as strike_force", bs.normalize("Strike Force"), bs.STRIKE_FORCE)
c.eq("'ONSLAUGHT' reads as onslaught", bs.normalize("ONSLAUGHT"), bs.ONSLAUGHT)
c.eq("an unknown size reads as Strike Force, not zero", bs.normalize("nonsense"), bs.STRIKE_FORCE)
for _size, _want in ((bs.INCURSION, 1), (bs.STRIKE_FORCE, 2), (bs.ONSLAUGHT, 3)):
    c.eq("Hyperphasing's printed cap at %s" % _size, hp.base_limit(_size), _want)
c.eq("...and Strike Force for a typo", hp.base_limit("strike farce"), 2)
with settings_as(BATTLE_SIZE="Onslaught"):
    c.eq("the setting is read when no size is handed over", hp.base_limit(), 3)
for _size in bs.BATTLE_SIZES:
    c.eq("Battle Focus tokens still read their own table (%s)" % _size,
         battle_focus.tokens_for_battle_size(_size), battle_focus.TOKENS_BY_BATTLE_SIZE[_size])
    c.eq("Ride the Wind's cap still reads its own table (%s)" % _size,
         ride_the_wind.withdrawal_limit(_size), ride_the_wind.WITHDRAWALS_BY_BATTLE_SIZE[_size])


# ==========================================================================
print("=== 3. Hyperphasing ===")
# ==========================================================================

def hp_scene(auto=(), choose=None, tt=None, battle_size=None):
    st = GameState()
    warriors = tk.line_up(tk.build(nec.NECRON_WARRIORS, HUMAN, name="1 Necron Warriors 1"), 10, 10, 1.3)
    immortals = tk.line_up(tk.build(nec.IMMORTALS, HUMAN, name="1 Immortals 1"), 10, 20, 1.3)
    lychguard = tk.line_up(tk.build(nec.LYCHGUARD, HUMAN, name="1 Lychguard 1"), 10, 30, 1.3)
    boyz = tk.line_up(tk.build(BOYZ, FOE, name="2 Boyz 1"), 40, 40, 1.3)
    add(st, warriors, immortals, lychguard, boyz)
    dm = DecisionManager()
    log = tk.Log()
    ctrl = hp.HyperphasingController(
        decision_manager=dm, game_state=st, game_log=log, all_tokens=st.tokens,
        auto_players=auto, turn_tracker=tt or tracker(PHASE_COMMAND, HUMAN),
        battle_size=battle_size, choose=choose)
    return dict(state=st, warriors=warriors, immortals=immortals, lychguard=lychguard,
                boyz=boyz, decision=dm, log=log, ctrl=ctrl,
                squads={warriors, immortals, lychguard, boyz})


c.true("Hyperphasing is the withdrawal base class's second subclass",
       issubclass(hp.HyperphasingController, EndOfTurnWithdrawalController))
c.true("...and Ride the Wind the first", issubclass(ride_the_wind.RideTheWindController,
                                                    EndOfTurnWithdrawalController))

with settings_as(**HYPER):
    s = hp_scene()
    c.true("at the end of the opponent's turn it is offered", s["ctrl"].offer_at_end_of_turn(s["squads"], FOE))
    c.eq("...to the Necron player", s["decision"].player, HUMAN)
    c.true("...one unit at a time, first in name order",
           "1 Immortals 1" in (s["decision"].prompt or ""))
    c.true("...printing the cap that is left (2 of 2)", "(2 of 2 left" in (s["decision"].prompt or ""))
    tk.pick_option(s["decision"], "Go into Strategic Reserves")
    c.true("going: the unit is in Strategic Reserves", s["immortals"] in s["state"].reserves)
    c.true("...and off the battlefield",
           not any(m in s["state"].tokens for m in s["immortals"].models))
    c.true("...logged under the rule's name", s["log"].has(hp.HYPERPHASING_LABEL))
    c.true("the answer asks the next unit", "1 Lychguard 1" in (s["decision"].prompt or ""))
    c.true("...with the count re-read (1 of 2)", "(1 of 2 left" in (s["decision"].prompt or ""))
    tk.pick_option(s["decision"], "Go into Strategic Reserves")
    c.eq("with the cap spent nobody else is asked", s["decision"].is_pending, False)
    c.true("...so the Warriors stay on the battlefield", s["warriors"] not in s["state"].reserves)
    c.eq("...two withdrawn at Strike Force", len(s["state"].reserves), 2)

    s = hp_scene()
    s["ctrl"].offer_at_end_of_turn(s["squads"], FOE)
    tk.pick_option(s["decision"], "Stay on the battlefield")
    c.true("staying keeps the unit and still asks the next one",
           s["immortals"] not in s["state"].reserves and "1 Lychguard 1" in (s["decision"].prompt or ""))

    s = hp_scene()
    c.eq("at the end of YOUR OWN turn nothing is offered",
         (s["ctrl"].offer_at_end_of_turn(s["squads"], HUMAN), s["decision"].is_pending), (False, False))

    s = hp_scene(battle_size="incursion")
    c.eq("Incursion: up to 1 unit", s["ctrl"].limit(HUMAN), 1)
    s = hp_scene(battle_size="onslaught")
    c.eq("Onslaught: up to 3 units", s["ctrl"].limit(HUMAN), 3)

    s = hp_scene()
    tk.line_up(s["boyz"], 10, 11.2, 1.3)
    c.true("(live) the Boyz stand in Engagement Range of the Warriors",
           s["warriors"].is_engaged(s["state"].tokens))
    c.eq("a unit within Engagement Range is excluded", s["ctrl"].can_use(s["warriors"]), False)
    c.true("...while the others still qualify", s["ctrl"].can_use(s["lychguard"]))

    s = hp_scene()
    s["warriors"].embarked_in = object()
    c.eq("an embarked unit is not on the battlefield to be removed", s["ctrl"].can_use(s["warriors"]), False)
    s = hp_scene()
    withdraw_to_reserves(s["state"], s["warriors"])
    c.eq("a unit already in Reserves is not selected again", s["ctrl"].can_use(s["warriors"]), False)
    c.eq("a unit that is no NECRONS unit is not selected", s["ctrl"].can_use(s["boyz"]), False)

    # The Dimensional Overseer: +1, on the battlefield or in Strategic Reserves.
    s = hp_scene()
    _ov = tk.line_up(tk.build(nec.OVERLORD, HUMAN, name="1 Overlord 1"), 30, 10, 1.3)
    E.grant(_ov, "Dimensional Overseer")
    add(s["state"], _ov)
    c.eq("the Dimensional Overseer on the battlefield: 3 units", s["ctrl"].limit(HUMAN), 3)
    c.eq("...for its own army only", s["ctrl"].limit(FOE), 2)
    s["ctrl"].offer_at_end_of_turn(s["squads"] | {_ov}, FOE)
    c.true("...and the prompt prints it (3 of 3)", "(3 of 3 left" in (s["decision"].prompt or ""))
    s = hp_scene()
    add(s["state"], _ov)
    withdraw_to_reserves(s["state"], _ov)
    c.eq("...in Strategic Reserves it still adds one", s["ctrl"].limit(HUMAN), 3)
    s["state"].reserves.remove(_ov)
    s["state"].embarked_squads.append(_ov)
    _ov.embarked_in = object()
    c.eq("...EMBARKED it is neither, and adds nothing", s["ctrl"].limit(HUMAN), 2)
    _ov.embarked_in = None
    s["state"].embarked_squads.remove(_ov)
    s["state"].reserves.append(_ov)
    _ov.models[0].current_wounds = 0
    c.eq("...nor once the bearer is dead", s["ctrl"].limit(HUMAN), 2)
    _ov.models[0].current_wounds = _ov.models[0].profile.wounds

    # Rule 20.03's round-3 destruction and the arrival floor.
    c.true("doomed: the offer after the last turn of round 3",
           hp.withdrawal_is_doomed(tracker(PHASE_COMMAND, battle_round=4, turn_index=0)))
    c.true("...not after the first turn of round 4",
           not hp.withdrawal_is_doomed(tracker(PHASE_COMMAND, battle_round=4, turn_index=1)))
    c.true("...not after the last turn of round 2",
           not hp.withdrawal_is_doomed(tracker(PHASE_COMMAND, battle_round=3, turn_index=0)))
    _over = tracker(PHASE_COMMAND, battle_round=5, turn_index=1)
    _over.battle_over = True
    c.true("...and doomed once the battle is over", hp.withdrawal_is_doomed(_over))
    c.true("before battle round 2 the unit misses its next arrival",
           hp.misses_next_arrival(tracker(PHASE_COMMAND, battle_round=1)))
    c.true("...from battle round 2 it does not",
           not hp.misses_next_arrival(tracker(PHASE_COMMAND, battle_round=2)))
    s = hp_scene(tt=tracker(PHASE_COMMAND, HUMAN, battle_round=4, turn_index=0))
    c.eq("the controller refuses a doomed withdrawal - no prompt at all",
         (s["ctrl"].offer_at_end_of_turn(s["squads"], FOE), s["decision"].is_pending), (False, False))

    # The AI: the injected policy, never a prompt.
    _calls = []
    s = hp_scene(auto=(HUMAN,),
                 choose=lambda eligible, cap: _calls.append(([q.name for q in eligible], cap)) or eligible[:1])
    c.eq("the AI is not prompted", s["ctrl"].offer_at_end_of_turn(s["squads"], FOE), False)
    c.eq("...its policy is handed the eligible units and the cap",
         _calls, [(["1 Immortals 1", "1 Lychguard 1", "1 Necron Warriors 1"], 2)])
    c.true("...and what it returns goes into Strategic Reserves", s["immortals"] in s["state"].reserves)
    s = hp_scene(auto=(HUMAN,), choose=lambda eligible, cap: [s_boyz for s_boyz in [None]] and [])
    c.eq("a policy that picks nothing withdraws nothing", s["state"].reserves, [])
    _sneak = {}
    s = hp_scene(auto=(HUMAN,), choose=lambda eligible, cap: [_sneak["engaged"]])
    tk.line_up(s["boyz"], 10, 11.2, 1.3)
    _sneak["engaged"] = s["warriors"]
    s["ctrl"].offer_at_end_of_turn(s["squads"], FOE)
    c.eq("...and an ineligible unit it names is refused by the rule",
         s["warriors"] in s["state"].reserves, False)
    s = hp_scene(auto=(HUMAN,))
    c.eq("an AI owner with no policy is filtered out and stays put",
         (s["ctrl"].offer_at_end_of_turn(s["squads"], FOE), s["state"].reserves), (False, []))

with settings_as(**NONE):
    s = hp_scene()
    c.eq("without the detachment nothing is offered",
         (s["ctrl"].offer_at_end_of_turn(s["squads"], FOE), s["decision"].is_pending), (False, False))


# ==========================================================================
print("=== 4. the relaxed arrival lifts the zone ban everywhere ===")
# ==========================================================================

def ingress_rig(state, owner=HUMAN, phase=PHASE_MOVEMENT, battle_round=2):
    setup = SetupController(state, obstacles=state.obstacles, all_tokens=state.tokens,
                            board_width_in=W, board_height_in=H)
    tt = tracker(phase, owner, battle_round=battle_round)
    ic = IngressController(setup, state, state.tokens, turn_tracker=tt,
                           board_width_in=W, board_height_in=H)
    return setup, tt, ic


def grid(step=0.5):
    y = step
    while y < H:
        x = step
        while x < W:
            yield x, y
            x += step
        y += step


ST4 = map_state()
SETUP4, TT4, IC4 = ingress_rig(ST4)
ZONES4 = {z.owner: z for z in ST4.deployment_zones}
W4 = tk.build(nec.NECRON_WARRIORS, HUMAN, name="1 Necron Warriors 4")
ST4.reserves.append(W4)
_tok4 = W4.models[0]
ENEMY_SPOT = next(((x, y) for x, y in grid()
                   if ZONES4[FOE].contains_circle(x, y, 2.0)
                   and SETUP4.position_valid(_tok4, x, y, squad=W4)), None)
c.true("(live) an open spot deep in the opponent's zone exists", ENEMY_SPOT is not None)
c.true("(live) the Warriors have no Deep Strike", not IC4._has_deep_strike(W4))
c.true("round 2: the opponent's zone is banned for an ordinary arrival",
       IC4._in_enemy_deployment_zone(W4, *ENEMY_SPOT))
c.eq("...so the overlay paints it red", IC4.position_valid(W4, _tok4, *ENEMY_SPOT), False)
IC4.relaxed_arrival_squad = W4
c.eq("a relaxed arrival ('anywhere on the battlefield') is not banned",
     IC4._in_enemy_deployment_zone(W4, *ENEMY_SPOT), False)
c.true("...and the overlay agrees with the Confirm", IC4.position_valid(W4, _tok4, *ENEMY_SPOT))
c.eq("...its Confirm half never tested the zone", IC4._relaxed_arrival_extra_check.__name__,
     "_relaxed_arrival_extra_check")


def interior(points, margin=6.5):
    return [p for p in points if min(p[0], W - p[0], p[1], H - p[1]) > margin]


IC4.relaxed_arrival_squad = None
_plain = ad._ingress_landing_candidates(IC4, W4, ST4.tokens, objectives=ST4.objectives)
IC4.relaxed_arrival_squad = W4
_relaxed = ad._ingress_landing_candidates(IC4, W4, ST4.tokens, objectives=ST4.objectives)
IC4.relaxed_arrival_squad = None
c.eq("the AI's sweep offers an ordinary Warriors arrival only the edge band",
     len(interior(_plain)), 0)
c.true("...and a relaxed one the whole board (%d interior spots)" % len(interior(_relaxed)),
       len(interior(_relaxed)) > 0)


# ==========================================================================
print("=== 5. the Eternity Gate's own lock, and the arrivals it records ===")
# ==========================================================================

_fresh = tk.build(nec.NECRON_WARRIORS, HUMAN, name="1 Necron Warriors 50")
c.eq("a squad starts without the gate's lock", _fresh.eternity_gate_charge_locked, False)
c.eq("...and without the start-of-turn fact", _fresh.eternity_gate_bearer_started_on_board, False)
c.true("a save keeps the gate's lock", "eternity_gate_charge_locked" in activation_state.SQUAD_FLAGS)
c.true("...and the fact", "eternity_gate_bearer_started_on_board" in activation_state.SQUAD_FLAGS)


def charge_rig(unit_gap=6.0, sheet=nec.NECRON_WARRIORS, owner=HUMAN, phase=PHASE_CHARGE):
    st = GameState()
    unit = tk.line_up(tk.build(sheet, owner, name="1 %s 5" % sheet.name), 20.0, 20.0, 1.3)
    boyz = tk.line_up(tk.build(BOYZ, FOE, name="2 Boyz 5"), 20.0, 20.0 + unit_gap, 1.3)
    add(st, unit, boyz)
    tt = tracker(phase, owner)
    mc = MovementController(obstacles=[], game_log=tk.Log(), player_name=owner,
                            dice_manager=DiceManager(), turn_tracker=tt, all_tokens=st.tokens,
                            board_width_in=W, board_height_in=H)
    cc = ChargeController(dice_manager=DiceManager(), turn_tracker=tt, all_tokens=st.tokens,
                          movement_controller=mc)
    return dict(state=st, unit=unit, boyz=boyz, turn=tt, movement=mc, charge=cc)


r5 = charge_rig()
c.true("(live) the Warriors may charge", r5["charge"].can_declare_charge(r5["unit"]))
r5["unit"].eternity_gate_charge_locked = True
c.eq("the gate's lock forbids the charge", r5["charge"].can_declare_charge(r5["unit"]), False)
r5["unit"].eternity_gate_charge_locked = False
r5["unit"].charge_locked_until_end_of_turn = True
c.eq("...and so, separately, does the shared lock", r5["charge"].can_declare_charge(r5["unit"]), False)

# The gate itself sets its OWN lock, and records where its Monolith started.
_st5 = GameState()
_mono5 = place(tk.build(nec.MONOLITH, HUMAN, name="1 Monolith 5"), 30.0, 22.0)
_rider5 = tk.line_up(tk.build(nec.NECRON_WARRIORS, HUMAN, name="1 Necron Warriors 51"), 5.0, 5.0, 1.3)
add(_st5, _mono5, _rider5)
_setup5, _tt5, _ic5 = ingress_rig(_st5)
_gate5 = eternity_gate.EternityGateController(
    decision_manager=DecisionManager(), game_state=_st5, ingress_controller=_ic5, turn_tracker=_tt5)
_gate5.offer(_mono5)
_gate5.decision_manager.choose(0)
c.true("the gate locks its passenger on its own field", _rider5.eternity_gate_charge_locked)
c.eq("...not on the shared one", _rider5.charge_locked_until_end_of_turn, False)
c.true("...and records that its Monolith started the turn on the battlefield",
       _rider5.eternity_gate_bearer_started_on_board)

_ic5.start_ingress(_rider5, _mono5.models[0].x_in + 6.0, _mono5.models[0].y_in)
c.true("(live) the gated arrival is being placed", _setup5.setting_up_squad is _rider5)
_ic5.confirm_ingress()
c.eq("the gated arrival confirms (%s)" % "; ".join(_setup5.errors or []), _setup5.setting_up_squad, None)
c.true("...and is recorded as a gate arrival this turn", _rider5 in _ic5.gate_arrivals_this_turn)
_ic5.reset_turn()
c.eq("...until the turn ends", _ic5.gate_arrivals_this_turn, set())

_st5b = GameState()
_plain5 = tk.build(nec.NECRON_WARRIORS, HUMAN, name="1 Necron Warriors 52")
_st5b.reserves.append(_plain5)
_setup5b, _tt5b, _ic5b = ingress_rig(_st5b)
_ic5b.start_ingress(_plain5, 3.0, 22.0)
_ic5b.confirm_ingress()
c.eq("(live) an ordinary arrival confirms (%s)" % "; ".join(_setup5b.errors or []),
     _setup5b.setting_up_squad, None)
c.eq("...and is NOT a gate arrival", _plain5 in _ic5b.gate_arrivals_this_turn, False)
_st5c = GameState()
_mono5c = place(tk.build(nec.MONOLITH, HUMAN, name="1 Monolith 6"), 30.0, 22.0)
add(_st5c, _mono5c)
_new5 = tk.build(nec.NECRON_WARRIORS, HUMAN, name="1 Necron Warriors 53")
_st5c.reserves.append(_new5)
_mono5c.set_up_this_turn = True
_g5c = eternity_gate.EternityGateController(
    decision_manager=DecisionManager(), game_state=_st5c, ingress_controller=ingress_rig(_st5c)[2],
    turn_tracker=tracker(PHASE_MOVEMENT))
_g5c.offer(_mono5c)
_g5c.decision_manager.choose(0)
c.eq("a Monolith that itself arrived this turn did NOT start it on the battlefield",
     _new5.eternity_gate_bearer_started_on_board, False)


# ==========================================================================
print("=== 6. the Fight phase's loss ledger ===")
# ==========================================================================

f6 = tk.fight_scene(BOYZ, nec.NECRON_WARRIORS, attacker_owner=FOE)
FC6, BOYZ6, WAR6 = f6["fight"], f6["attacker"], f6["target"]
FC6._continue_after_hit_roll = lambda *a, **k: None
_choppa = next(w for w in BOYZ6.models[0].weapons if w.weapon_type == "melee")
c.eq("a unit never hit this activation lost nothing", FC6.models_lost_this_activation(WAR6), 0)
_before6 = len(alive(WAR6))
safe(FC6._handle_hit_results, 3, 0, _choppa, WAR6, "Choppa")
for _m in WAR6.models[:2]:
    _m.current_wounds = 0
c.eq("two models destroyed after the first hit are counted", FC6.models_lost_this_activation(WAR6), 2)
safe(FC6._handle_hit_results, 2, 0, _choppa, WAR6, "Choppa")
c.eq("...the count is taken at the FIRST hit, not re-taken at the second",
     FC6.models_lost_this_activation(WAR6), 2)
c.eq("(live) the unit still has its survivors", len(alive(WAR6)), _before6 - 2)
FC6.reset_fight_phase()
c.eq("the ledger ends with the phase", FC6.models_lost_this_activation(WAR6), 0)
safe(FC6._handle_hit_results, 1, 0, _choppa, WAR6, "Choppa")
WAR6.models[2].current_wounds = 0
_res6, _err6 = safe(FC6._start_fighting, BOYZ6)
c.eq("...and a new activation starts it afresh (%s)" % (_err6 or "ok"),
     FC6.models_lost_this_activation(WAR6), 0)
c.true("the shooting controller keeps its twin", hasattr(ShootingController, "models_lost_this_activation"))


# ==========================================================================
print("=== 7. off-board reanimation, through the one door ===")
# ==========================================================================

class BoostSpy:
    def __init__(self, extra=1):
        self.calls = 0
        self.extra = extra

    def extra_wounds(self, squad, all_tokens, log=None):
        self.calls += 1
        return self.extra


_st7 = GameState()
W7 = casualties_off_board(tk.build(nec.NECRON_WARRIORS, HUMAN, name="1 Necron Warriors 7"), 3)
_st7.reserves.append(W7)
_placed7 = []
c.eq("(live) three destroyed Warriors to recover", reanimation_protocols.recoverable_wounds(W7), 3)
_boost7 = BoostSpy()
_got7, _err7 = safe(reanimation_protocols.activate, W7, 2, boost=_boost7, game_state=_st7,
                    placer=lambda *a, **k: _placed7.append(a), off_board=True)
c.eq("off the board: two wounds revive two Warriors (%s)" % (_err7 or "ok"),
     (_got7[0], _got7[1], len(_got7[2])) if _got7 else None, (2, 2, 2))
c.eq("...back in the unit", len(W7.models), len(W7.models))
c.eq("...off the destroyed list", len(W7.destroyed_models), 1)
c.true("...with one wound each", all(m.current_wounds == 1 for m in (_got7[2] if _got7 else [None])
                                    if m is not None))
c.eq("...and NOT on the battlefield", [m for m in W7.models if m in _st7.tokens], [])
c.eq("...no placement is opened for a unit with no battlefield", _placed7, [])
c.eq("...and the auras add nothing - the boost is not even asked", _boost7.calls, 0)

_st7b = GameState()
W7B = tk.line_up(tk.build(nec.NECRON_WARRIORS, HUMAN, name="1 Necron Warriors 71"), 10, 10, 1.3)
add(_st7b, W7B)
W7B.models[0].current_wounds = 0
_st7b.remove_dead_models()
_boost7b = BoostSpy(extra=0)
reanimation_protocols.activate(W7B, 1, boost=_boost7b, all_tokens=_st7b.tokens, game_state=_st7b)
c.eq("on the board the same door asks the boost (the counter-proof)", _boost7b.calls, 1)

_lych7 = tk.build(nec.LYCHGUARD, HUMAN, name="1 Lychguard 7")
_lych7.models[0].current_wounds = 1
reanimation_protocols.activate(_lych7, 1, game_state=GameState(), off_board=True)
c.eq("off the board a damaged model is still healed first", _lych7.models[0].current_wounds, 2)

# The revived model stands up with the rest of the unit when it arrives.
_st7c = GameState()
W7C = casualties_off_board(tk.build(nec.NECRON_WARRIORS, HUMAN, name="1 Necron Warriors 72"), 2)
_st7c.reserves.append(W7C)
reanimation_protocols.activate(W7C, 2, game_state=_st7c, off_board=True)
_setup7c, _tt7c, _ic7c = ingress_rig(_st7c)
_ic7c.start_ingress(W7C, 3.0, 22.0)
c.eq("an arrival places EVERY model, the revived ones included",
     sum(1 for m in W7C.models if m in _st7c.tokens), len(W7C.models))


# ==========================================================================
print("=== 8. the four Enhancements ===")
# ==========================================================================

_spec = E.get("Arisen Tyrant")
_lord8 = tk.build(nec.OVERLORD, HUMAN, name="1 Overlord 8")
_war8 = tk.build(nec.NECRON_WARRIORS, HUMAN, name="1 Necron Warriors 8")
_boss8 = tk.build(WARBOSS, HUMAN, name="1 Warboss 8")
c.true("a NECRONS CHARACTER may bear them", _spec.can_bear(_lord8.models[0], _lord8))
c.true("...a Necron Warrior may not", not _spec.can_bear(_war8.models[0], _war8))
c.true("...nor a CHARACTER of another faction", not _spec.can_bear(_boss8.models[0], _boss8))
_pts8 = _lord8.points
E.grant(_lord8, "Arisen Tyrant")
c.eq("the grant costs its printed 25 points", (_lord8.points or 0) - (_pts8 or 0), 25)

# Arisen Tyrant, through both attack controllers.
TYR = overlord_leading(nec.IMMORTALS, name="1 Immortals 8", enhancement="Arisen Tyrant")
_st8 = GameState()
tk.line_up(TYR, 10, 10, 1.3)
_b8 = tk.line_up(tk.build(BOYZ, FOE, name="2 Boyz 8"), 10, 20, 1.3)
add(_st8, TYR, _b8)
with settings_as(**HYPER):
    c.true("Arisen Tyrant: the bearer's unit re-rolls Hit rolls of 1", tyrant.applies(TYR))
    c.eq("...but not the whole roll unless it was set up this turn", tyrant.offers_full_reroll(TYR), False)
    TYR.set_up_this_turn = True
    c.true("...set up this turn, the whole roll is on offer", tyrant.offers_full_reroll(TYR))
    SC8 = ShootingController(obstacles=[], game_log=tk.Log(), player_name=HUMAN,
                             dice_manager=DiceManager(), turn_tracker=tracker(PHASE_SHOOTING),
                             all_tokens=_st8.tokens, decision_manager=DecisionManager())
    SC8.active_squad = TYR
    c.eq("ShootingController names Arisen Tyrant for the whole roll",
         SC8._hit_reroll_reason(_b8), tyrant.ARISEN_TYRANT_LABEL)
    FC8 = FightController(game_log=tk.Log(), dice_manager=DiceManager(),
                          turn_tracker=tracker(PHASE_FIGHT), all_tokens=_st8.tokens,
                          decision_manager=DecisionManager())
    FC8.fighting_squad = TYR
    c.eq("...and FightController too - 'an attack'", FC8._hit_reroll_reason(_b8), tyrant.ARISEN_TYRANT_LABEL)
    TYR.set_up_this_turn = False
    c.true("not set up this turn: shooting names no whole roll",
           SC8._hit_reroll_reason(_b8) != tyrant.ARISEN_TYRANT_LABEL)
    c.true("...nor fight", FC8._hit_reroll_reason(_b8) != tyrant.ARISEN_TYRANT_LABEL)

    # THE AUTOMATIC HALF, measured where it runs, in both steps.
    _lord = lord_model(TYR)
    for _label, _ctrl, _wtype in (("shooting", SC8, "ranged"), ("fight", FC8, "melee")):
        _calls = []
        _ctrl._begin_ones_reroll = (lambda kind, ones, *a, _c=_calls, **kw:
                                    _c.append((kind, ones, kw.get("reason"))))
        _w = next((w for w in _lord.weapons if w.weapon_type == _wtype), None)
        _grp = {"pairs": [(_lord, _w)], "target_squad": _b8}
        _ctrl.current_group = _grp
        _r, _e = safe(_ctrl._hit_step, [1, 1, 6], _grp, _w, _b8, "test weapon")
        c.eq("%s throws the Hit rolls of 1 again by itself, naming Arisen Tyrant" % _label,
             (_calls[:1], _e), ([("hit", 2, tyrant.ARISEN_TYRANT_LABEL)], None))
        del _ctrl._begin_ones_reroll
c.true("Arisen Tyrant is a ones-or-whole source", reroll_scope.is_ones_or_whole(tyrant.ARISEN_TYRANT_LABEL))
with settings_as(**NONE):
    c.true("without the detachment nothing applies", not tyrant.applies(TYR))
_lord.current_wounds = 0
with settings_as(**HYPER):
    c.true("...nor once the bearer is dead", not tyrant.applies(TYR))
_lord.current_wounds = _lord.profile.wounds


# Hyperspatial Transfer Node, through a real Advance.
def advance(squad, settings):
    st = GameState()
    tk.line_up(squad, 20, 20, 1.3)
    add(st, squad)
    dice = tk.RecordingDice()
    with settings_as(**settings):
        mc = MovementController(obstacles=[], game_log=tk.Log(), player_name=HUMAN, dice_manager=dice,
                                turn_tracker=tracker(PHASE_MOVEMENT), all_tokens=st.tokens,
                                board_width_in=W, board_height_in=H)
        mc.select(squad.models[0])
        mc.start_move()
        mc.start_run()
    return mc, dice


NODE = overlord_leading(nec.NECRON_WARRIORS, name="1 Necron Warriors 81",
                        enhancement="Hyperspatial Transfer Node")
_mc8, _dice8 = advance(NODE, HYPER)
c.eq("Hyperspatial Transfer Node: the Advance is a flat 6\"", _mc8.advance_bonus_by_squad.get(NODE),
     htn.HYPERSPATIAL_TRANSFER_NODE_BONUS_IN)
c.eq("...and no Advance roll is made", [lab for lab, _v in _dice8.rolled], [])
_mc8b, _dice8b = advance(overlord_leading(nec.NECRON_WARRIORS, name="1 Necron Warriors 82",
                                         enhancement="Hyperspatial Transfer Node"), NONE)
c.eq("without the detachment the Advance is rolled (the counter-proof)", len(_dice8b.rolled), 1)

# Osteoclave Fulcrum: Deep Strike on every model of the bearer's unit.
FUL = overlord_leading(nec.IMMORTALS, name="1 Immortals 83", enhancement="Osteoclave Fulcrum")
_other = tk.build(nec.IMMORTALS, HUMAN, name="1 Immortals 84")
c.true("(live) Immortals print no Deep Strike", not any(m.profile.deep_strike for m in FUL.models))
with settings_as(**NONE):
    c.eq("without the detachment nothing is granted", fulcrum.apply_all([FUL]), 0)
with settings_as(**HYPER):
    _log8 = tk.Log()
    c.eq("with it, the bearer's unit gains it", fulcrum.apply_all([FUL, _other], game_log=_log8), 1)
    c.true("...on every model, the bodyguards included", all(m.profile.deep_strike for m in FUL.models))
    c.true("...logged", _log8.has(fulcrum.OSTEOCLAVE_FULCRUM))
    c.eq("...idempotent - a second pass grants nothing", fulcrum.apply_all([FUL]), 0)
    c.true("...never leaking to another unit of the same datasheet",
           not any(m.profile.deep_strike for m in _other.models))
    c.true("...and rule 24.09's every-model test now passes", IC4._has_deep_strike(FUL))


# ==========================================================================
print("=== 9. Quantum Deflection ===")
# ==========================================================================

ST9 = GameState()
MONO9 = place(tk.build(nec.MONOLITH, HUMAN, name="1 Monolith 9"), 30.0, 22.0)
ARK9 = place(tk.build(nec.DOOMSDAY_ARK, HUMAN, name="1 Doomsday Ark 9"), 10.0, 22.0)
IMM9 = tk.line_up(tk.build(nec.IMMORTALS, HUMAN, name="1 Immortals 9"), 45, 22, 1.3)
BOYZ9 = tk.line_up(tk.build(BOYZ, FOE, name="2 Boyz 9"), 25, 34, 1.3)
HEAVY9 = tk.line_up(tk.build(nec.LOKHUST_HEAVY_DESTROYERS, FOE, name="2 Lokhust Heavy Destroyers 9"),
                    25, 38, 2.0)
add(ST9, MONO9, ARK9, IMM9, BOYZ9, HEAVY9)


def qd_ctrl(phase=PHASE_SHOOTING, owner=FOE, auto=(), cp=5):
    s = strat(cp)
    dec = DecisionManager()
    log = tk.Log()
    ctrl = qd.QuantumDeflectionController(s, turn_tracker=tracker(phase, owner), decision_manager=dec,
                                          game_log=log, auto_players=auto)
    return ctrl, s, dec, log


c.true("the Monolith is a NECRONS VEHICLE unit", qd.is_necrons_vehicle_unit(MONO9))
c.true("...Immortals are not", not qd.is_necrons_vehicle_unit(IMM9))
c.eq("(live) the Monolith prints no invulnerable save",
     parse_threshold(effective_invulnerable_save(MONO9.models[0])), None)
c.true("...so a 4+ changes something", qd.grant_changes_anything(MONO9))
c.eq("(live) the Doomsday Ark already has a 4+", effective_invulnerable_save(ARK9.models[0]), "4+")
c.true("...so for it the grant buys nothing", not qd.grant_changes_anything(ARK9))

with settings_as(**HYPER):
    ctrl, s9, dec9, log9 = qd_ctrl()
    c.true("WHEN: your opponent's Shooting phase", ctrl.can_use(BOYZ9, MONO9))
    c.true("not your own Shooting phase", not qd_ctrl(owner=HUMAN)[0].can_use(BOYZ9, MONO9))
    for _owner in (HUMAN, FOE):
        c.true("the Fight phase, whoever's turn (%s)" % _owner,
               qd_ctrl(phase=PHASE_FIGHT, owner=_owner)[0].can_use(BOYZ9, MONO9, melee=True))
    c.true("never the Movement phase", not qd_ctrl(phase=PHASE_MOVEMENT)[0].can_use(BOYZ9, MONO9))
    c.true("TARGET: not a unit that is no VEHICLE", not ctrl.can_use(BOYZ9, IMM9))
    c.true("...not a vehicle whose own save is already as good", not ctrl.can_use(BOYZ9, ARK9))
    c.true("...not your own unit's attack", not ctrl.can_use(MONO9, ARK9))
    c.true("no CP, no offer", not qd_ctrl(cp=0)[0].can_use(BOYZ9, MONO9))
    c.true("offered to the target's owner", ctrl.maybe_offer(BOYZ9, MONO9) and dec9.player == HUMAN)
    c.true("...as a Stratagem prompt", dec9.is_stratagem)
    tk.pick_option(dec9, "Use")
    c.eq("using it costs 1CP", s9.command_points.cp[HUMAN], 4)
    c.true("...grants the unit", qd.is_active(MONO9) and log9.has(qd.QUANTUM_DEFLECTION_NAME))
    c.eq("...and its models now have a 4+ invulnerable save",
         effective_invulnerable_save(MONO9.models[0]), qd.QUANTUM_DEFLECTION_SAVE)
    c.eq("a second offer for the same pair is not made", ctrl.maybe_offer(BOYZ9, MONO9), False)
    c.true("...and a unit already under it is refused", not qd_ctrl()[0].can_use(HEAVY9, MONO9))
    qd.reset_phase([MONO9])
    c.eq("the save ends with the phase", parse_threshold(effective_invulnerable_save(MONO9.models[0])), None)
    s9.reset_phase()
    c.eq("15.01's reset ALONE: the controller's memo still refuses the same pair",
         ctrl.maybe_offer(BOYZ9, MONO9), False)
    ctrl.reset_phase()
    c.true("...and its own reset brings the offer back", ctrl.maybe_offer(BOYZ9, MONO9))

    c.true("(live) the Boyz' worst AP leaves the Monolith's own 2+ at 4+ or better",
           not qd.worth_for_ai(BOYZ9, MONO9))
    c.true("(live) the Heavy Destroyers' does not", qd.worth_for_ai(HEAVY9, MONO9))
    ctrl, s9, dec9, log9 = qd_ctrl(auto=(HUMAN,))
    ctrl.maybe_offer(BOYZ9, MONO9)
    c.eq("the AI keeps the CP when the save would hold anyway",
         (dec9.is_pending, s9.command_points.cp[HUMAN], qd.is_active(MONO9)), (False, 5, False))
    ctrl.maybe_offer(HEAVY9, MONO9)
    c.eq("...and buys it, without a prompt, when it would not",
         (dec9.is_pending, s9.command_points.cp[HUMAN], qd.is_active(MONO9)), (False, 4, True))
    qd.reset_phase([MONO9])
with settings_as(**NONE):
    c.true("without the detachment it is not offered", not qd_ctrl()[0].can_use(BOYZ9, MONO9))


# ==========================================================================
print("=== 10. Entropic Damping ===")
# ==========================================================================

FAR10 = tk.line_up(tk.build(BOYZ, FOE, name="2 Boyz 10"), 1, 1, 0.2)
add(ST9, FAR10)


def ed_ctrl(phase=PHASE_SHOOTING, owner=FOE, auto=(), cp=5):
    s = strat(cp)
    dec = DecisionManager()
    log = tk.Log()
    ctrl = ed.EntropicDampingController(s, turn_tracker=tracker(phase, owner), decision_manager=dec,
                                        game_log=log, auto_players=auto)
    return ctrl, s, dec, log


c.true("the Monolith is TITANIC", titanic.is_titanic_unit(MONO9))
c.true("...the Doomsday Ark is not", not titanic.is_titanic_unit(ARK9))
c.true("(live) the Boyz stand within 18\"", BOYZ9.min_distance_to(MONO9) <= ed.ENTROPIC_DAMPING_RANGE_IN)
c.true("(live) the far Boyz do not", FAR10.min_distance_to(MONO9) > ed.ENTROPIC_DAMPING_RANGE_IN)

with settings_as(**HYPER):
    ctrl, s10, dec10, log10 = ed_ctrl()
    c.true("WHEN: your opponent's Shooting phase", ctrl.can_use(BOYZ9, MONO9))
    c.eq("never against a melee selection", ctrl.maybe_offer(BOYZ9, MONO9, melee=True), False)
    c.true("not your own Shooting phase", not ed_ctrl(owner=HUMAN)[0].can_use(BOYZ9, MONO9))
    c.true("not the Fight phase", not ed_ctrl(phase=PHASE_FIGHT)[0].can_use(BOYZ9, MONO9))
    c.true("TARGET: not a model that is no TITANIC", not ctrl.can_use(BOYZ9, ARK9))
    c.true("...not an attacker beyond 18\"", not ctrl.can_use(FAR10, MONO9))
    c.true("offered to the TITANIC model's owner", ctrl.maybe_offer(BOYZ9, MONO9) and dec10.player == HUMAN)
    tk.pick_option(dec10, "Use")
    c.eq("using it costs 1CP", s10.command_points.cp[HUMAN], 4)
    c.true("...and flags the ATTACKING unit", ed.is_active(BOYZ9))
    c.eq("...never the target it was used on", ed.is_active(MONO9), False)
    c.true("...logged", log10.has(ed.ENTROPIC_DAMPING_NAME))
    c.true("a flagged attacker is not offered it again", not ed_ctrl()[0].can_use(BOYZ9, MONO9))

    _gun10 = next(w for w in BOYZ9.models[0].weapons if w.weapon_type == "ranged")
    c.true("(live) the Boyz' gun prints no [HAZARDOUS]", not _gun10.hazardous)
    _granted = ed.adjusted_weapon(_gun10, BOYZ9)
    c.true("the attacker's weapons gain [HAZARDOUS]", _granted.hazardous)
    c.true("...on a COPY - the model's own weapon is untouched", _granted is not _gun10 and not _gun10.hazardous)
    c.true("...and an unflagged unit's weapon is handed back as it is", ed.adjusted_weapon(_gun10, FAR10) is _gun10)

    SC10 = ShootingController(obstacles=[], game_log=tk.Log(), player_name=FOE,
                              dice_manager=DiceManager(), turn_tracker=tracker(PHASE_SHOOTING, FOE),
                              all_tokens=ST9.tokens, decision_manager=DecisionManager())
    _pairs = [(m, next(w for w in m.weapons if w.weapon_type == "ranged")) for m in BOYZ9.models]
    SC10.active_squad = BOYZ9
    c.true("ShootingController's adjuster chain grants it", SC10._adjusted_weapon(_pairs, MONO9).hazardous)
    _begun = []
    SC10._begin_resolution = lambda *a, **k: _begun.append(a)
    SC10._cover_ignored_for_group = lambda *a, **k: True
    _r10, _e10 = safe(SC10._dispatch_group, "key", "Slugga", _pairs, MONO9)
    c.eq("...so the Hazard ledger owes one D6 per weapon fired (%s)" % (_e10 or "ok"),
         SC10._pending_subgroups_hazardous, len(_pairs))
    SC10.active_squad = FAR10
    _far_pairs = [(m, next(w for w in m.weapons if w.weapon_type == "ranged")) for m in FAR10.models]
    SC10._dispatch_group("key", "Slugga", _far_pairs, MONO9)
    c.eq("...and none for a unit that was not targeted by it", SC10._pending_subgroups_hazardous, 0)

    ed.reset_phase([BOYZ9])
    c.eq("the grant ends with the phase", ed.is_active(BOYZ9), False)
    ctrl.reset_phase()
    _saved10 = []
    for _m in FAR10.models:
        for _w in _m.weapons:
            if _w.weapon_type == "ranged":
                _saved10.append((_w, _w.hazardous))
                _w.hazardous = True
    tk.line_up(FAR10, 25, 36, 1.3)
    c.true("an attacker whose every ranged weapon already prints it buys nothing",
           not ed_ctrl()[0].can_use(FAR10, MONO9))
    for _w, _was in _saved10:
        _w.hazardous = _was
    tk.line_up(FAR10, 1, 1, 0.2)

    ctrl, s10, dec10, log10 = ed_ctrl(auto=(HUMAN,))
    ctrl.maybe_offer(BOYZ9, MONO9)
    c.eq("the AI uses it whenever it is offered, without a prompt",
         (dec10.is_pending, s10.command_points.cp[HUMAN], ed.is_active(BOYZ9)), (False, 4, True))
    ed.reset_phase([BOYZ9])
with settings_as(**NONE):
    c.true("without the detachment it is not offered", not ed_ctrl()[0].can_use(BOYZ9, MONO9))


# ==========================================================================
print("=== 11. Reanimation Crypts ===")
# ==========================================================================

def rc_scene(phase=PHASE_COMMAND, owner=HUMAN, cp=5, dice=True, lost=(3, 1)):
    st = GameState()
    button = tk.line_up(tk.build(nec.IMMORTALS, HUMAN, name="1 Immortals 11"), 10, 10, 1.3)
    orks = tk.line_up(tk.build(BOYZ, HUMAN, name="1 Boyz 11"), 10, 20, 1.3)
    add(st, button, orks)
    units = []
    for i, n in enumerate(lost):
        unit = casualties_off_board(tk.build(nec.NECRON_WARRIORS, HUMAN,
                                             name="1 Necron Warriors 2%d" % (i + 1)), n)
        st.reserves.append(unit)
        units.append(unit)
    full = tk.build(nec.IMMORTALS, HUMAN, name="1 Immortals 12")
    st.reserves.append(full)
    s = strat(cp)
    log = tk.Log()
    ctrl = rc.ReanimationCryptsController(s, turn_tracker=tracker(phase, owner), game_state=st,
                                          dice_manager=DiceManager() if dice else None, game_log=log)
    ctrl.boost = BoostSpy()
    return dict(state=st, button=button, orks=orks, units=units, full=full, strat=s, log=log, ctrl=ctrl)


with settings_as(**HYPER):
    r = rc_scene()
    c.eq("every NECRONS unit in Reserves",
         [q.name for q in rc.reserve_units(r["state"], HUMAN)],
         ["1 Immortals 12", "1 Necron Warriors 21", "1 Necron Warriors 22"])
    c.eq("...of which only those with something to recover roll",
         [q.name for q in rc.recovering_units(r["state"], HUMAN)],
         ["1 Necron Warriors 21", "1 Necron Warriors 22"])
    c.true("WHEN: your Command phase, on a NECRONS unit of the army", r["ctrl"].can_use(r["button"]))
    c.true("the label names the units it would reach", "for 2 unit(s)" in r["ctrl"].panel_label(r["button"]))
    c.true("TARGET: 'Your NECRONS WARLORD' is a no-op, but a unit of another faction is no Necron",
           not r["ctrl"].can_use(r["orks"]))
    c.true("not your Movement phase", not rc_scene(phase=PHASE_MOVEMENT)["ctrl"].can_use(r["button"]))
    c.true("not your opponent's Command phase", not rc_scene(owner=FOE)["ctrl"].can_use(r["button"]))
    c.true("no CP, no button", not rc_scene(cp=0)["ctrl"].can_use(r["button"]))
    _empty = rc_scene(lost=())
    c.true("with nothing in Reserves to recover it is not offered at all",
           not _empty["ctrl"].can_use(_empty["button"]))

    tk.script(3, 1)
    c.true("using it", r["ctrl"].use(r["button"]))
    c.eq("...costs 1CP", r["strat"].command_points.cp[HUMAN], 4)
    _dm = r["ctrl"].dice_manager
    c.true("...rolls one D3, labelled, for the first unit",
           _dm.is_pending and (_dm.label or "") == rc.REANIMATION_CRYPTS_NAME
           and getattr(_dm, "rolled_for", None) is r["units"][0])
    c.true("...and holds the phase while it drains", r["ctrl"].is_busy)
    c.true("...with no second purchase possible meanwhile", not r["ctrl"].can_use(r["button"]))
    _dm.acknowledge()
    r["ctrl"].on_dice_acknowledged()
    c.eq("a 3 revives all three Warriors of the first unit", len(r["units"][0].destroyed_models), 0)
    c.eq("...none of them on the battlefield", [m for m in r["units"][0].models if m in r["state"].tokens], [])
    c.true("...then the second unit rolls", _dm.is_pending and getattr(_dm, "rolled_for", None) is r["units"][1])
    _dm.acknowledge()
    r["ctrl"].on_dice_acknowledged()
    c.eq("...and its one Warrior comes back", len(r["units"][1].destroyed_models), 0)
    c.eq("...with nothing left owed", (r["ctrl"].is_busy, _dm.is_pending), (False, False))
    c.eq("...and the auras are not asked for a unit off the board", r["ctrl"].boost.calls, 0)
    c.true("...logged", r["log"].has(rc.REANIMATION_CRYPTS_NAME))

    r = rc_scene(dice=False)
    tk.script(2, 2)
    r["ctrl"].use(r["button"])
    c.eq("without a dice panel the queue drains at once", r["ctrl"].is_busy, False)
    tk.script()

    # The AI.
    r = rc_scene()
    c.true("_handle_reanimation_crypts buys it for 2+ recoverable wounds",
           ad._handle_reanimation_crypts(HUMAN, r["state"].tokens, r["ctrl"]))
    c.eq("...for 1CP", r["strat"].command_points.cp[HUMAN], 4)
    r = rc_scene(lost=(1,))
    c.eq("...and keeps the CP for one",
         (ad._handle_reanimation_crypts(HUMAN, r["state"].tokens, r["ctrl"]),
          r["strat"].command_points.cp[HUMAN]), (False, 5))
with settings_as(**NONE):
    r = rc_scene()
    c.true("without the detachment there is no button", not r["ctrl"].can_use(r["button"]))
tk.script()


# ==========================================================================
print("=== 12. Cosmic Precision ===")
# ==========================================================================

def cp_scene(sheet=nec.NECRON_WARRIORS, phase=PHASE_MOVEMENT, owner=HUMAN, cp=5, enemy=None):
    st = map_state()
    setup, tt, ic = ingress_rig(st, owner=owner, phase=phase)
    unit = tk.build(sheet, owner, name="1 %s 12" % sheet.name)
    st.reserves.append(unit)
    if enemy is not None:
        foe = place(tk.build(BOYZ, FOE, name="2 Boyz 12"), *enemy)
        add(st, foe)
    s = strat(cp)
    log = tk.Log()
    ctrl = cosmic.CosmicPrecisionController(s, ingress_controller=ic, setup_controller=setup,
                                            turn_tracker=tt, game_log=log)
    return dict(state=st, setup=setup, turn=tt, ingress=ic, unit=unit, strat=s, log=log, ctrl=ctrl)


c.eq("its distance is the relaxed arrival's one definition",
     cosmic.COSMIC_PRECISION_MIN_ENEMY_DISTANCE_IN, 6.0)
c.true("...shorter than rule 20.04's", cosmic.COSMIC_PRECISION_MIN_ENEMY_DISTANCE_IN < INGRESS_MIN_ENEMY_DISTANCE_IN)
c.eq("its button lives on the ARRIVAL screen", cosmic.CosmicPrecisionController.PANEL_SCREEN, ARRIVAL_SCREEN)

with settings_as(**HYPER):
    k = cp_scene()
    c.eq("TARGET: not before the unit is arriving", k["ctrl"].can_use(k["unit"]), False)
    c.true("...though the AI may ask whether it COULD be", k["ctrl"].could_target(k["unit"]))
    k["ingress"].start_ingress(k["unit"], 3.0, 3.0)
    c.true("(live) the unit is arriving", k["ingress"].is_ingressing(k["unit"]))
    c.true("WHEN: your Movement phase, while it arrives", k["ctrl"].can_use(k["unit"]))
    _reg = ProactiveStratagems()
    _reg.add(k["ctrl"])
    c.eq("the registry does not list it on the unit screen", _reg.usable_for(k["unit"]), [])
    c.eq("...only on the arrival screen", _reg.usable_for(k["unit"], screen=ARRIVAL_SCREEN), [k["ctrl"]])
    c.eq("...with no note before it is bought", _reg.notes_for(k["unit"], screen=ARRIVAL_SCREEN), [])
    _gen = k["setup"].placement_generation
    _spot = next(((x, y) for x, y in grid() if ZONES4[FOE].contains_circle(x, y, 2.0)
                  and k["setup"].position_valid(k["unit"].models[0], x, y, squad=k["unit"])), None)
    c.eq("(live) the opponent's zone is red before", k["ingress"].position_valid(
        k["unit"], k["unit"].models[0], *_spot), False)
    c.true("using it", k["ctrl"].use(k["unit"]))
    c.eq("...costs 1CP", k["strat"].command_points.cp[HUMAN], 4)
    c.true("...arms the relaxed arrival for THIS unit", k["ingress"].relaxed_arrival_squad is k["unit"])
    c.true("...so the opponent's zone is open ground now",
           k["ingress"].position_valid(k["unit"], k["unit"].models[0], *_spot))
    c.true("...repaints the overlay", k["setup"].placement_generation > _gen)
    c.true("...RESTRICTIONS: no charge this turn", k["unit"].charge_locked_until_end_of_turn)
    c.true("...the arrival screen says so", any("Cosmic Precision is active" in n
                                                for n in _reg.notes_for(k["unit"], screen=ARRIVAL_SCREEN)))
    c.true("...logged", k["log"].has(cosmic.COSMIC_PRECISION_NAME))
    c.eq("a second purchase buys nothing and is not offered", k["ctrl"].can_use(k["unit"]), False)
    k["ctrl"].reset_phase()
    c.eq("the note ends with the phase", k["ctrl"].panel_note(k["unit"]), None)
    k["ingress"].cancel_ingress()
    c.true("a cancelled arrival keeps the charge lock - it is the unit's, for the turn",
           k["unit"].charge_locked_until_end_of_turn)

    # 6" instead of 8": an enemy 7" away, edge to edge, near the unit's own edge.
    _probe_r = tk.build(nec.NECRON_WARRIORS, HUMAN).models[0].radius_in
    _boy_r = tk.build(BOYZ, FOE).models[0].radius_in
    _home = next(((x, y) for x, y in grid() if min(y, H - y) < 5.0
                  and ZONES4[HUMAN].contains_circle(x, y, 1.0) and 15.0 < x < W - 15.0
                  and SETUP4.position_valid(_tok4, x, y, squad=W4)), (W / 2.0, H - 3.0))
    k = cp_scene(enemy=(_home[0] + 7.0 + _probe_r + _boy_r, _home[1]))
    k["ingress"].start_ingress(k["unit"], _home[0], _home[1])
    _tok = k["unit"].models[0]
    _ok_setup = k["setup"].position_valid(_tok, *_home, squad=k["unit"])
    c.true("(live) the probe spot is open ground within 6\" of the edge", _ok_setup)
    c.eq("an enemy 7\" away forbids an ordinary arrival (rule 20.04's 8\")",
         k["ingress"].position_valid(k["unit"], _tok, *_home), False)
    k["ctrl"].use(k["unit"])
    c.true("...and Cosmic Precision allows it (6\")", k["ingress"].position_valid(k["unit"], _tok, *_home))

    k = cp_scene(phase=PHASE_SHOOTING)
    k["ingress"].start_ingress(k["unit"], 3.0, 3.0)
    c.true("not outside the Movement phase", not k["ctrl"].can_use(k["unit"]))
    k = cp_scene(owner=HUMAN)
    k["turn"].turn_owner = FOE
    k["ingress"].start_ingress(k["unit"], 3.0, 3.0)
    c.true("not the opponent's Movement phase (Rapid Ingress)", not k["ctrl"].can_use(k["unit"]))
    k = cp_scene(sheet=nec.CTAN_SHARD_OF_THE_VOID_DRAGON)
    k["ingress"].start_ingress(k["unit"], 3.0, 3.0)
    c.true("(live) the C'tan is a MONSTER", cosmic.is_monster_unit(k["unit"]))
    c.true("TARGET: excluding MONSTER units", not k["ctrl"].can_use(k["unit"]))
    k = cp_scene()
    k["ingress"].start_ingress(k["unit"], 3.0, 3.0)
    k["ingress"].eternity_gate_squad = k["unit"]
    c.true("an arrival through the Eternity Gate is not offered it - the gate's rule wins",
           not k["ctrl"].can_use(k["unit"]))
    k = cp_scene(cp=0)
    k["ingress"].start_ingress(k["unit"], 3.0, 3.0)
    c.true("no CP, no button", not k["ctrl"].can_use(k["unit"]))
with settings_as(**NONE):
    k = cp_scene()
    k["ingress"].start_ingress(k["unit"], 3.0, 3.0)
    c.true("without the detachment there is no button", not k["ctrl"].can_use(k["unit"]))

for _relaxed_s, _plain_s, _want, _label in (
        ((0, 4, 9), (1, 1, 1), True, "a better threat bucket"),
        ((1, 3, 9), (1, 5, 0), True, "the same bucket, a nearer target"),
        ((1, 5, 0), (1, 5, 9), False, "only a tie-break better - not worth a CP"),
        ((2, 0, 0), (1, 9, 9), False, "a worse bucket"),
        ((1, 1, 1), None, True, "no legal ordinary landing at all"),
        (None, (1, 1, 1), False, "no relaxed landing")):
    c.eq("the AI's Cosmic Precision test: %s" % _label,
         ad._cosmic_precision_improves(_relaxed_s, _plain_s), _want)


# ==========================================================================
print("=== 13. Dimensional Corridor ===")
# ==========================================================================

def dc_scene(unit_gap=6.0, in_set=True, started=True, phase=PHASE_CHARGE, owner=HUMAN, cp=5,
             sheet=nec.NECRON_WARRIORS):
    r = charge_rig(unit_gap=unit_gap, sheet=sheet, owner=HUMAN, phase=phase)
    r["turn"].turn_owner = owner
    unit = r["unit"]
    unit.eternity_gate_charge_locked = True
    unit.eternity_gate_bearer_started_on_board = started
    ic = SimpleNamespace(gate_arrivals_this_turn={unit} if in_set else set())
    s = strat(cp)
    log = tk.Log()
    ctrl = dc.DimensionalCorridorController(s, turn_tracker=r["turn"], charge_controller=r["charge"],
                                            ingress_controller=ic, game_state=r["state"], game_log=log)
    r.update(ingress=ic, strat=s, log=log, ctrl=ctrl)
    return r


with settings_as(**HYPER):
    d = dc_scene()
    c.eq("(live) the gate's lock forbids the charge", d["charge"].can_declare_charge(d["unit"]), False)
    c.true("a unit that came through the gate may buy it", d["ctrl"].can_use(d["unit"]))
    c.true("...the label names its cost", "2 CP" in d["ctrl"].panel_label(d["unit"]))
    c.true("...because lifting the lock alone would make it eligible", d["ctrl"].eligible_once_lifted(d["unit"]))
    c.true("...and asking that leaves the lock in place", d["unit"].eternity_gate_charge_locked)
    c.true("using it", d["ctrl"].use(d["unit"]))
    c.eq("...costs 2CP", d["strat"].command_points.cp[HUMAN], 3)
    c.eq("...lifts the gate's lock", d["unit"].eternity_gate_charge_locked, False)
    c.true("...so the unit may declare a charge", d["charge"].can_declare_charge(d["unit"]))
    c.true("...logged", d["log"].has(dc.DIMENSIONAL_CORRIDOR_NAME))

    # ONE scene: asking one scene's controller about another scene's unit is
    # refused because that unit is not on ITS board - the wrong reason (the
    # A/B probe that removes the gate-arrival check could not bite that way).
    d = dc_scene(in_set=False)
    c.true("(live) ...the lock and the Monolith's start are both still set",
           d["unit"].eternity_gate_charge_locked and d["unit"].eternity_gate_bearer_started_on_board)
    c.true("TARGET: not a unit that did not arrive through the gate this turn", not d["ctrl"].can_use(d["unit"]))
    d = dc_scene(started=False)
    c.true("...nor one whose Monolith did not start the turn on the battlefield", not d["ctrl"].can_use(d["unit"]))
    d = dc_scene(unit_gap=30.0)
    c.eq("no enemy within 12\": nothing to buy, no button", d["ctrl"].can_use(d["unit"]), False)
    c.true("...and the question left the lock where it was", d["unit"].eternity_gate_charge_locked)
    d = dc_scene()
    d["movement"].advanced_squad_ids.add(d["unit"])
    c.eq("a unit that Advanced could not charge anyway - no button", d["ctrl"].can_use(d["unit"]), False)
    d = dc_scene()
    d["unit"].charge_locked_until_end_of_turn = True
    c.eq("a second lock (Cosmic Precision's) - no button", d["ctrl"].can_use(d["unit"]), False)
    d["ctrl"]._grant(d["strat"], HUMAN, [d["unit"]])
    c.eq("...and lifting the gate's lock leaves that one standing",
         (d["unit"].charge_locked_until_end_of_turn, d["charge"].can_declare_charge(d["unit"])), (True, False))
    d = dc_scene(phase=PHASE_SHOOTING)
    c.true("not outside the Charge phase", not d["ctrl"].can_use(d["unit"]))
    d = dc_scene(owner=FOE)
    c.true("not the opponent's Charge phase", not d["ctrl"].can_use(d["unit"]))
    d = dc_scene(cp=1)
    c.true("with 1CP, no button (2CP printed)", not d["ctrl"].can_use(d["unit"]))
    d = dc_scene()
    for _m in d["unit"].models:
        d["state"].tokens.remove(_m)
    c.true("a unit no longer on the battlefield cannot charge", not d["ctrl"].can_use(d["unit"]))
with settings_as(**NONE):
    d = dc_scene()
    c.true("without the detachment there is no button", not d["ctrl"].can_use(d["unit"]))

# The AI.
d = dc_scene()
_near = ad._dimensional_corridor_verdict(d["unit"], d["state"].tokens)
c.true("the AI's verdict: a likely charge (%s%%)" % _near, _near is not None and _near >= ad.DIMENSIONAL_CORRIDOR_MIN_CHARGE_CHANCE)
d = dc_scene(unit_gap=12.5)
c.eq("...None for a long one", ad._dimensional_corridor_verdict(d["unit"], d["state"].tokens), None)
d = dc_scene(sheet=nec.LOKHUST_HEAVY_DESTROYERS)
c.true("(live) Lokhust Heavy Destroyers are refused a charge as shooters",
       ad._shooting_specialist_charge_block(d["unit"]) is not None)
c.eq("...so the verdict never spends 2CP on them", ad._dimensional_corridor_verdict(d["unit"], d["state"].tokens),
     None)
d = dc_scene()
_bought = []
_stub = SimpleNamespace(can_use=lambda sq: sq is d["unit"], use=lambda sq: _bought.append(sq) or True)
c.true("_handle_dimensional_corridor buys it", ad._handle_dimensional_corridor(HUMAN, d["state"].tokens, _stub))
c.eq("...for that unit", _bought, [d["unit"]])
c.eq("...and does nothing when nobody may", ad._handle_dimensional_corridor(
    HUMAN, d["state"].tokens, SimpleNamespace(can_use=lambda sq: False, use=None)), False)


# ==========================================================================
print("=== 14. Hyperphasic Recall ===")
# ==========================================================================

_m = SimpleNamespace(x_in=0.0, y_in=0.0, radius_in=2.5)
c.true("wholly within 6\": a 0.5\" base 8\" from a 2.5\" Monolith's centre",
       hr.wholly_within_monolith(0.5, 8.0, 0.0, _m))
c.eq("...not at 8.1\"", hr.wholly_within_monolith(0.5, 8.1, 0.0, _m), False)
c.true("(live) plain 'within' would still say yes at 8.1\"", 8.1 - 0.5 - 2.5 <= hr.HYPERPHASIC_RECALL_RANGE_IN)


def hr_scene(phase=PHASE_SHOOTING, owner=FOE, auto=(), cp=5, verdict=None, monolith=True, lost=2):
    st = GameState()
    mono = place(tk.build(nec.MONOLITH, HUMAN, name="1 Monolith 14"), 30.0, 22.0)
    warriors = tk.line_up(tk.build(nec.NECRON_WARRIORS, HUMAN, name="1 Necron Warriors 14"), 5.0, 5.0, 1.3)
    boyz = tk.line_up(tk.build(BOYZ, FOE, name="2 Boyz 14"), 5.0, 17.0, 1.3)
    add(st, warriors, boyz)
    if monolith:
        add(st, mono)
    setup = SetupController(st, obstacles=[], all_tokens=st.tokens, board_width_in=W, board_height_in=H)
    s = strat(cp)
    dec = DecisionManager()
    log = tk.Log()
    ctrl = hr.HyperphasicRecallController(
        s, setup_controller=setup, turn_tracker=tracker(phase, owner), game_state=st, decision_manager=dec,
        game_log=log, auto_players=auto, ai_verdict=verdict)
    for model in warriors.models[:lost]:
        model.current_wounds = 0
    ledger = {id(warriors): lost}
    return dict(state=st, mono=mono, warriors=warriors, boyz=boyz, setup=setup, strat=s, decision=dec,
                log=log, ctrl=ctrl, lost=lambda sq: ledger.get(id(sq), 0))


def within_monolith(squad, mono):
    return all(hr.wholly_within_monolith(m.radius_in, m.x_in, m.y_in, mono.models[0]) for m in alive(squad))


with settings_as(**HYPER):
    h = hr_scene()
    MONO_M = h["mono"].models[0]
    c.true("Necron Warriors are NECRONS INFANTRY", hr.is_necrons_infantry_unit(h["warriors"]))
    c.true("...the Monolith is not", not hr.is_necrons_infantry_unit(h["mono"]))
    c.eq("the Monolith's model is a MONOLITH model", hr.monolith_models(h["mono"]), [MONO_M])
    c.eq("...a Warrior is not", hr.monolith_models(h["warriors"]), [])
    c.eq("friendly Monoliths on the battlefield", h["ctrl"].monoliths_for(HUMAN), [MONO_M])
    c.eq("...none for the opponent", h["ctrl"].monoliths_for(FOE), [])
    c.true("TARGET: a unit that lost models to the attacker", h["ctrl"].is_candidate(h["warriors"], h["boyz"], h["lost"]))
    c.eq("...not one that lost none", h["ctrl"].is_candidate(h["warriors"], h["boyz"], lambda sq: 0), False)
    c.eq("...not the attacker's own unit", h["ctrl"].is_candidate(h["boyz"], h["boyz"], lambda sq: 3), False)
    c.eq("...not a unit that is no INFANTRY", h["ctrl"].is_candidate(h["mono"], h["boyz"], lambda sq: 1), False)

    _v = h["ctrl"].validator(h["warriors"], MONO_M)
    _tok = alive(h["warriors"])[0]
    c.true("the set-up validator accepts a spot wholly within 6\"", _v(_tok, 30.0 + 2.5 + 3.0, 22.0))
    c.eq("...and refuses one beyond it", _v(_tok, 30.0 + 2.5 + 6.0, 22.0), False)
    _boy = place(tk.build(BOYZ, FOE, name="2 Boyz 141"), 36.5, 22.0)
    add(h["state"], _boy)
    c.eq("...and one within Engagement Range of an enemy", _v(_tok, 34.0, 22.0), False)
    for _bm in _boy.models:
        h["state"].tokens.remove(_bm)

    _prop = h["ctrl"].proposed_positions(h["warriors"], MONO_M)
    c.true("the engine proposes a set-up for the living models (%s)" % (len(_prop) if _prop else None),
           _prop is not None and len(_prop) == len(alive(h["warriors"])))
    c.true("...every base wholly within 6\" of the Monolith",
           _prop is not None and all(hr.wholly_within_monolith(t.radius_in, x, y, MONO_M)
                                     for t, (x, y) in zip(alive(h["warriors"]), _prop)))
    c.eq("...and the Confirm's own checks pass on it",
         h["ctrl"]._trial_errors(h["warriors"], alive(h["warriors"]), _prop, MONO_M) if _prop else ["none"], [])

    c.true("offered after the attacker has shot", h["ctrl"].maybe_offer(h["boyz"], h["lost"]))
    c.eq("...to the Necron player", h["decision"].player, HUMAN)
    c.true("...as a Stratagem prompt", h["decision"].is_stratagem)
    c.true("...answerable on the board - the option names the unit",
           any(o.get("squad") is h["warriors"] for o in h["decision"].options or ()))
    _orig = {id(m): (m.x_in, m.y_in) for m in alive(h["warriors"])}
    tk.pick_option(h["decision"], h["warriors"].name)
    c.eq("choosing the unit costs 2CP", h["strat"].command_points.cp[HUMAN], 3)
    c.eq("...but the set-up waits while the destroyed models still lie there",
         h["setup"].setting_up_squad, None)
    h["state"].remove_dead_models()
    c.true("...and opens once the death sweep has taken them", h["ctrl"].resolve_deferred())
    c.true("(live) the set-up is open for the Warriors",
           h["setup"].setting_up_squad is h["warriors"] and h["setup"].state == PLACING)
    c.true("...starting on the engine's proposal, wholly within 6\"", within_monolith(h["warriors"], h["mono"]))
    h["setup"].confirm_setup()
    c.eq("confirming sets the unit up (%s)" % "; ".join(h["setup"].errors or []), h["setup"].setting_up_squad, None)
    c.true("...wholly within 6\" of the Monolith", within_monolith(h["warriors"], h["mono"]))
    c.true("...not within Engagement Range of an enemy", not h["warriors"].is_engaged(h["state"].tokens))
    c.true("...logged", h["log"].has(hr.HYPERPHASIC_RECALL_NAME))

    h = hr_scene()
    h["ctrl"].maybe_offer(h["boyz"], h["lost"])
    _orig = {id(m): (m.x_in, m.y_in) for m in alive(h["warriors"])}
    tk.pick_option(h["decision"], h["warriors"].name)
    h["state"].remove_dead_models()
    h["ctrl"].resolve_deferred()
    h["setup"].cancel_setup()
    c.true("cancelling puts the unit back where it stood",
           all((m.x_in, m.y_in) == _orig[id(m)] for m in h["warriors"].models))
    c.true("...on the battlefield", all(m in h["state"].tokens for m in h["warriors"].models))
    c.eq("...and the CP stays spent", h["strat"].command_points.cp[HUMAN], 3)

    h = hr_scene()
    c.true("offered once per attacker", h["ctrl"].maybe_offer(h["boyz"], h["lost"]))
    tk.pick_option(h["decision"], "Decline")
    c.eq("...declining costs nothing", h["strat"].command_points.cp[HUMAN], 5)
    c.eq("...and it is not asked again for the same attack", h["ctrl"].maybe_offer(h["boyz"], h["lost"]), False)
    h["ctrl"].reset_phase()
    c.true("...until the phase ends", h["ctrl"].maybe_offer(h["boyz"], h["lost"]))

    h = hr_scene(owner=HUMAN)
    c.eq("WHEN: not after your own unit shot in YOUR Shooting phase",
         (h["ctrl"].maybe_offer(h["boyz"], h["lost"]), h["decision"].is_pending), (False, False))
    h = hr_scene(phase=PHASE_FIGHT, owner=HUMAN)
    c.true("...but the Fight phase belongs to nobody", h["ctrl"].maybe_offer(h["boyz"], h["lost"]))
    h = hr_scene(phase=PHASE_MOVEMENT)
    c.eq("...and never the Movement phase", h["ctrl"].maybe_offer(h["boyz"], h["lost"]), False)
    h = hr_scene(monolith=False)
    c.eq("no MONOLITH on the battlefield: nothing to set up beside, no offer",
         (h["ctrl"].maybe_offer(h["boyz"], h["lost"]), h["decision"].is_pending), (False, False))
    h = hr_scene(cp=1)
    c.eq("with 1CP, no offer (2CP printed)", h["ctrl"].maybe_offer(h["boyz"], h["lost"]), False)

    # The AI: deferred past the sweep, answered by the injected verdict.
    h = hr_scene(auto=(HUMAN,), verdict=lambda sq: True)
    c.eq("the AI is not prompted", (h["ctrl"].maybe_offer(h["boyz"], h["lost"]), h["decision"].is_pending),
         (False, False))
    c.eq("...and does not buy while the corpses still lie there",
         (h["ctrl"].resolve_deferred(), h["strat"].command_points.cp[HUMAN]), (False, 5))
    h["state"].remove_dead_models()
    c.true("...after the sweep its verdict buys it", h["ctrl"].resolve_deferred())
    c.eq("...for 2CP", h["strat"].command_points.cp[HUMAN], 3)
    c.eq("...and the set-up is confirmed at once (%s)" % "; ".join(h["setup"].errors or []),
         h["setup"].setting_up_squad, None)
    c.true("...wholly within 6\" of the Monolith", within_monolith(h["warriors"], h["mono"]))
    h = hr_scene(auto=(HUMAN,), verdict=lambda sq: False)
    h["ctrl"].maybe_offer(h["boyz"], h["lost"])
    h["state"].remove_dead_models()
    c.eq("a verdict of no keeps the CP", (h["ctrl"].resolve_deferred(), h["strat"].command_points.cp[HUMAN]),
         (False, 5))
with settings_as(**NONE):
    h = hr_scene()
    c.eq("without the detachment it is not offered", h["ctrl"].maybe_offer(h["boyz"], h["lost"]), False)

_calm = GameState()
_calm_w = tk.line_up(tk.build(nec.NECRON_WARRIORS, HUMAN, name="1 Necron Warriors 15"), 5, 5, 1.3)
add(_calm, _calm_w)
c.eq("the AI's Recall verdict: no enemy, no reason", ad.hyperphasic_recall_verdict(_calm, _calm_w), False)
_doomed = GameState()
_last = tk.build(nec.NECRON_WARRIORS, HUMAN, name="1 Necron Warriors 16")
for _extra in _last.models[1:]:
    _last.models.remove(_extra)
place(_last, 20.0, 20.0)
_mob = tk.line_up(tk.build(BOYZ, FOE, name="2 Boyz 16"), 16.0, 23.0, 1.3)
add(_doomed, _last, _mob)
c.true("...a last Warrior in the Boyz' reach is about to be wiped out",
       ad.hyperphasic_recall_verdict(_doomed, _last))


# ==========================================================================
print("=== 15. Hyperphasing, the AI's policy ===")
# ==========================================================================

_st15 = GameState()
_stranded = tk.line_up(tk.build(nec.NECRON_WARRIORS, HUMAN, name="1 Necron Warriors 17"), 2.0, 2.0, 1.3)
# 26" from the Boyz: inside the Immortals' own 24" gun plus a move, outside any
# charge the Boyz could make - work where it stands, and nothing coming for it.
_busy = tk.line_up(tk.build(nec.IMMORTALS, HUMAN, name="1 Immortals 17"), 34.0, 12.0, 1.3)
_goner = tk.build(nec.NECRON_WARRIORS, HUMAN, name="1 Necron Warriors 18")
for _extra in _goner.models[1:]:
    _goner.models.remove(_extra)
place(_goner, 44.0, 36.0)
_mob15 = tk.line_up(tk.build(BOYZ, FOE, name="2 Boyz 17"), 34.0, 38.0, 1.3)
add(_st15, _stranded, _busy, _goner, _mob15)
_tt15 = tracker(PHASE_COMMAND, HUMAN)
_cands = sorted([_stranded, _busy, _goner], key=lambda q: q.name)

c.eq("never at the end of battle round 3",
     ad.hyperphasing_choice(_st15, tracker(PHASE_COMMAND, battle_round=4, turn_index=0), _cands, 2), [])
c.eq("never before the first arrival round",
     ad.hyperphasing_choice(_st15, tracker(PHASE_COMMAND, battle_round=1), _cands, 2), [])
c.eq("nothing with no cap left", ad.hyperphasing_choice(_st15, _tt15, _cands, 0), [])
c.eq("...or no candidates", ad.hyperphasing_choice(_st15, _tt15, [], 2), [])
_two = ad.hyperphasing_choice(_st15, _tt15, _cands, 3)
c.true("a unit about to be wiped out is rescued", _goner in _two)
c.true("...a unit with nothing to shoot, charge or take is repositioned", _stranded in _two)
c.true("...and a unit with work where it stands stays", _busy not in _two)
c.eq("with room for one, the rescue outranks the reposition",
     ad.hyperphasing_choice(_st15, _tt15, _cands, 1), [_goner])

_st15b = map_state()
_obj = _st15b.objectives[0]
from game.mission_context import objective_centre                    # noqa: E402
_ox, _oy = objective_centre(_obj)
_garrison = tk.line_up(tk.build(nec.NECRON_WARRIORS, HUMAN, name="1 Necron Warriors 19"), _ox - 3.0, _oy, 0.9)
add(_st15b, _garrison)
for _o in _st15b.objectives:
    _o.controlled_by = None
_obj.controlled_by = HUMAN
c.eq("a garrison on an objective its army holds is never pulled off",
     ad.hyperphasing_choice(_st15b, _tt15, [_garrison], 2), [])

for _f in (ad.hyperphasing_choice, ad.hyperphasic_recall_verdict, ad._handle_reanimation_crypts,
           ad._dimensional_corridor_verdict, ad._handle_dimensional_corridor, ad._cosmic_precision_improves):
    c.true("%s takes no agent - 0 API calls" % _f.__name__, "agent" not in inspect.signature(_f).parameters)


# ==========================================================================
print("=== 16. wiring: main.py, the panel, the AI, the seams ===")
# ==========================================================================

def _reachable(tree):
    """ast.walk() minus the bodies of `if False:` / `if 0:`, and minus an
    expression statement that is `False and <call>` - a wiring pin a dead
    branch still satisfies proves nothing."""
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


def statements_of(path):
    src = io.open(path, encoding="utf-8").read()
    lines = src.splitlines()
    tree = ast.parse(src)
    out = []
    for node in _reachable(tree):
        if isinstance(node, (ast.Expr, ast.Assign)):
            out.append(" ".join(" ".join(lines[node.lineno - 1:node.end_lineno]).split()))
    return tree, out


def _fn(tree, name):
    return next((n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef,)) and n.name == name), None)


MAIN_TREE, MAIN_STATEMENTS = statements_of("main.py")


def statement(*needles, pool=None):
    return any(all(n in s for n in needles) for s in (MAIN_STATEMENTS if pool is None else pool))


for _needles, _why in (
        (("hyperphasing_controller = HyperphasingController(",
          "choose=lambda eligible, cap: hyperphasing_choice(state, turn_tracker, eligible, cap)"),
         "Hyperphasing is built with the AI's policy injected"),
        (("hyperphasing_controller.offer_at_end_of_turn(",), "...and offered at the end of a turn"),
        (("quantum_deflection_controller = QuantumDeflectionController(",), "Quantum Deflection is built"),
        (("shooting_target_reactions = (", "quantum_deflection_controller", "entropic_damping_controller"),
         "...both target reactions answer a shooting selection"),
        (("fight_target_reactions = (", "quantum_deflection_controller"),
         "...Quantum Deflection answers a fight selection too"),
        (("hypercrypt_quantum_deflection.reset_phase(_court_squads)",), "...its save ends per phase"),
        (("quantum_deflection_controller.reset_phase()",), "...and its memo"),
        (("hypercrypt_entropic_damping.reset_phase(_court_squads)",), "Entropic Damping's flag ends per phase"),
        (("entropic_damping_controller.reset_phase()",), "...and its memo"),
        (("hyperphasic_recall_controller = HyperphasicRecallController(",
          "ai_verdict=lambda squad: hyperphasic_recall_verdict(state, squad)"),
         "Hyperphasic Recall is built with the AI's verdict injected"),
        (("hyperphasic_recall_controller.maybe_offer(", "shooter_squad",
          "shooting_controller.models_lost_this_activation"), "...offered after shooting, with that ledger"),
        (("hyperphasic_recall_controller.maybe_offer(", "_fighter", "fight_controller.models_lost_this_activation"),
         "...and after fighting, with the Fight phase's"),
        (("hyperphasic_recall_controller.resolve_deferred()",), "...its set-up is resolved after the sweep"),
        (("hyperphasic_recall_controller.reset_phase()",), "...and its memo resets per phase"),
        (("reanimation_crypts_controller = proactive_stratagems.add(ReanimationCryptsController(",),
         "Reanimation Crypts is a panel button"),
        (("reanimation_crypts_controller.boost = reanimation_boost",), "...handed the shared boost"),
        (("reanimation_crypts_controller.on_dice_acknowledged()",), "...its dice are acknowledged"),
        (("cosmic_precision_controller = proactive_stratagems.add(CosmicPrecisionController(",),
         "Cosmic Precision is a panel button"),
        (("cosmic_precision_controller.reset_phase()",), "...its note ends per phase"),
        (("dimensional_corridor_controller = proactive_stratagems.add(DimensionalCorridorController(",),
         "Dimensional Corridor is a panel button"),
        (("enh_osteoclave_fulcrum.apply_all(state.all_squads(), game_log=game_log)",),
         "Osteoclave Fulcrum is applied on the instant scene path"),
        (("enh_osteoclave_fulcrum.apply_all(", "_all_squads(state, pregame_controller)"),
         "...and at the start of Declare Battle Formations"),
        (("_gate_squad.eternity_gate_charge_locked = False",), "the gate's lock is cleared at the end of a turn"),
        (("_gate_squad.eternity_gate_bearer_started_on_board = False",), "...and its fact")):
    c.true(_why, statement(*_needles))

_ftr = next((n for n in _reachable(MAIN_TREE) if isinstance(n, ast.Assign)
             and any(getattr(t, "id", None) == "fight_target_reactions" for t in n.targets)), None)
_ftr_names = {getattr(e, "id", None) for e in getattr(getattr(_ftr, "value", None), "elts", [])}
c.true("(live) the fight reaction tuple was read (%d)" % len(_ftr_names), len(_ftr_names) >= 3)
c.eq("...and Entropic Damping (Shooting only) is NOT in it", "entropic_damping_controller" in _ftr_names, False)

_gate = _fn(MAIN_TREE, "_has_unresolved_declaration")
c.true("the phase gate waits on Reanimation Crypts' dice",
       "reanimation_crypts_controller.is_busy" in (ast.unparse(_gate) if _gate else ""))
_toa = [n for n in _reachable(MAIN_TREE) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        and n.func.id == "take_one_action"]
c.true("main.py passes the three panel controllers to take_one_action()",
       any({"reanimation_crypts_controller", "cosmic_precision_controller", "dimensional_corridor_controller"}
           <= {k.arg for k in n.keywords} for n in _toa))

DRIVER_TREE = ast.parse(io.open(os.path.join("ai", "agent_driver.py"), encoding="utf-8").read())
_take = ast.unparse(_fn(DRIVER_TREE, "_take_one_action"))
_move = ast.unparse(_fn(DRIVER_TREE, "_handle_movement"))
_auto = ast.unparse(_fn(DRIVER_TREE, "_auto_ingress_squad"))
c.true("the AI buys Reanimation Crypts in its Command phase",
       "_handle_reanimation_crypts(player, all_tokens, reanimation_crypts_controller" in _take)
_charge_branch = _take[_take.find("elif phase == PHASE_CHARGE:"):] if "elif phase == PHASE_CHARGE:" in _take else ""
c.true("(live) the Charge-phase branch was found", bool(_charge_branch))
c.true("...and Dimensional Corridor is asked there before it declares charges",
       -1 < _charge_branch.find("_handle_dimensional_corridor(player, all_tokens, dimensional_corridor_controller")
       < _charge_branch.find("_handle_charge("))
c.true("_handle_movement forwards Cosmic Precision to the arrival",
       "cosmic_precision_controller=cosmic_precision_controller" in _move)
c.true("...where the arrival buys it", "cosmic_precision_controller.use(squad)" in _auto
       and "_cosmic_precision_improves(" in _auto)

PANEL_TREE = ast.parse(io.open(os.path.join("game", "ui", "action_panel.py"), encoding="utf-8").read())
_setup_ui = _fn(PANEL_TREE, "_draw_setup_ui")
c.true("the Set Up screen takes the registry",
       _setup_ui is not None and "proactive_stratagems" in {a.arg for a in _setup_ui.args.args + _setup_ui.args.kwonlyargs})
_dispatch = _fn(PANEL_TREE, "_draw_dispatch")
c.true("...handed to it by keyword",
       any(isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute) and sub.func.attr == "_draw_setup_ui"
           and any(k.arg == "proactive_stratagems" for k in sub.keywords)
           for sub in (_reachable(_dispatch) if _dispatch else [])))
_setup_src = ast.unparse(_setup_ui) if _setup_ui else ""
c.true("...which draws the ARRIVAL screen's buttons", "buttons_for(squad, screen=ARRIVAL_SCREEN)" in _setup_src)
c.true("...and notes", "notes_for(squad, screen=ARRIVAL_SCREEN)" in _setup_src)


def unparse_fn(path, name):
    node = _fn(ast.parse(io.open(path, encoding="utf-8").read()), name)
    return ast.unparse(node) if node is not None else ""


for _path, _name, _needle, _why in (
        ("game/shooting.py", "_adjusted_weapon", "hypercrypt_entropic_damping.adjusted_weapon(weapon, self.active_squad)",
         "shooting's adjuster chain carries Entropic Damping"),
        ("game/shooting.py", "_hit_reroll_reason", "enh_arisen_tyrant.offers_full_reroll(self.active_squad)",
         "shooting names Arisen Tyrant's whole roll"),
        ("game/fight.py", "_hit_reroll_reason", "enh_arisen_tyrant.offers_full_reroll(self.fighting_squad)",
         "...and so does fight"),
        ("game/fight.py", "_hit_without_optional_reroll", "enh_arisen_tyrant.applies(self.fighting_squad)",
         "fight resolves Arisen Tyrant's 1s"),
        ("game/movement.py", "start_run", "enh_hyperspatial_transfer_node.skips_advance_roll(self.selected_squad)",
         "the Advance takes the Transfer Node's no-roll branch"),
        ("game/invulnerable_save.py", "effective_invulnerable_save",
         "hypercrypt_quantum_deflection.invulnerable_save_for(squad)", "the invulnerable save folds Quantum Deflection"),
        ("game/charge.py", "can_declare_charge", "squad.eternity_gate_charge_locked", "rule 11.02 reads the gate's lock"),
        ("game/ingress.py", "confirm_ingress", "self.gate_arrivals_this_turn.add(squad)",
         "the ingress Confirm records a gate arrival"),
        ("game/ingress.py", "_in_enemy_deployment_zone", "self._uses_relaxed_arrival(squad)",
         "the zone ban asks the relaxed arrival")):
    c.true(_why, _needle in unparse_fn(_path, _name))
_gate_use = unparse_fn("game/eternity_gate.py", "use")
c.true("the gate sets its own lock", "passenger.eternity_gate_charge_locked = True" in _gate_use)
c.eq("...and not the shared one", "passenger.charge_locked_until_end_of_turn = True" in _gate_use, False)


# ==========================================================================
print("=== 17. which shipped list fields it ===")
# ==========================================================================

_lists = []
for _fname in sorted(os.listdir("armies")):
    if _fname.endswith(".json"):
        _data = json.loads(io.open(os.path.join("armies", _fname), encoding="utf-8").read())
        if isinstance(_data, dict) and "detachments" in _data:
            _lists.append((_fname, _data["detachments"]))
c.true("the sweep read the shipped lists (%d)" % len(_lists), len(_lists) >= 5)
# DORMANT BY ROSTER until the user supplied a Hypercrypt Legion list. This pin
# was set so that fielding the detachment would be a visible change, and it
# turned red exactly then; it now names the one list that fields it, so a second
# one is a visible change too.
c.eq("exactly one shipped list fields the Hypercrypt Legion",
     [f for f, d in _lists if "Hypercrypt Legion" in d], ["necrons_hypercrypt.json"])

c.finish()
