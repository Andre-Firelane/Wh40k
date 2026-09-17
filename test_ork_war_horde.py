"""War Horde (Orks, 2026-09 codex): its rule, four Enhancements and six
Stratagems, driven through the real controllers - plus the engine seam the
detachment exposed: a destroyed model a rule keeps on the battlefield used to be
swept again the very next frame.

WHAT THIS SUITE PINS, and why each part is here:

  1. THE RECORD AGAINST THE CORPUS - DP, both Force Dispositions, the rule text,
     every Enhancement's points and every Stratagem's CP read from
     rules/orks/detachments/War Horde.md rather than typed twice, and each
     module quoting its own printed line.
  2. GET STUCK IN on the detachment gate.
  3. THE FOUR ENHANCEMENTS - bearer, gate, and the one reader each.
  4-7. THE FOUR PANEL STRATAGEMS at their WHEN/TARGET borders; the keyword grants
     through the real adjuster chains AND the extra-dice step that is their
     actual reader.
  8. BREAKIN' HEADS - the "becomes battle-shocked" door, the deferred offer, the
     D3, the mortal wounds landing, the shock lifted.
  9. ORKS IS NEVER BEATEN - a kept model stays on the board, fights with its
     unit, adds no Objective Control or coherency, and is removed per unit or at
     the end of the phase.
 10. THE SHARED LEDGER - the sweep no longer takes a kept model again, for all
     five rules built on game/fight_after_death.py.
 11. THE AI's deterministic handlers at their decision boundaries.
 12. WIRING (main.py by AST, the save flags) and the roster.

Real controllers, real datasheets, scripted dice (testkit).
"""

import ast
import io
import os
import re
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import testkit as tk                                                 # noqa: E402
from testkit import Checks, settings_as                              # noqa: E402

from ai import agent_driver, observation                             # noqa: E402
from game import (activation_state, army_lists, attached_units,      # noqa: E402
                  battle_shock, coldstar, enhancements as E, force_dispositions,
                  maps, move_exceptions, riled_up, scene_io, titanic, war_horde)
from game import enh_da_boss_is_watchin as boss                      # noqa: E402
from game import enh_follow_me_ladz as ladz                          # noqa: E402
from game import enh_headwoppas_killchoppa as woppa                  # noqa: E402
from game import enh_kunnin_but_brutal as kunnin                     # noqa: E402
from game import horde_breakin_heads as bh                           # noqa: E402
from game import horde_close_range_dakka as crd                      # noqa: E402
from game import horde_fungus_fuel_injection as ffi                  # noqa: E402
from game import horde_hit_em_harder as hit                          # noqa: E402
from game import horde_mow_em_down as mow                            # noqa: E402
from game import horde_orks_is_never_beaten as nb                    # noqa: E402
from game.command_points import CommandPointManager                  # noqa: E402
from game.decision import DecisionManager                            # noqa: E402
from game.dice import DiceManager                                    # noqa: E402
from game.fight import FightController, _melee_attack_groups, _melee_attack_key  # noqa: E402
from game.fight_after_death import FightAfterDeath                   # noqa: E402
from game.game_state import GameState                                # noqa: E402
from game.mission_context import objective_centre                    # noqa: E402
from game.shooting import extra_attack_dice                          # noqa: E402
from game.stratagems import StratagemController                      # noqa: E402
from game.turn import (PHASES, PHASE_COMMAND, PHASE_FIGHT,           # noqa: E402
                       PHASE_MOVEMENT, PHASE_SHOOTING, TurnTracker)
from game.weapons import MELEE, RANGED                                # noqa: E402

from game.factions import orks as ork                                # noqa: E402
from game.factions.necrons import NECRON_WARRIORS                    # noqa: E402

c = Checks("War Horde (Orks)")

ORK = "Player 1"
FOE = "Player 2"
WH = dict(WAR_HORDE_PLAYERS=(ORK,))
BOTH = dict(WAR_HORDE_PLAYERS=(ORK, FOE))
NO_WH = dict(WAR_HORDE_PLAYERS=())

M2 = maps.get("map2")
maps.apply_to_config(M2)

CORPUS = io.open(os.path.join("rules", "orks", "detachments", "War Horde.md"), encoding="utf-8").read()
MAIN_SRC = io.open("main.py", encoding="utf-8").read()


def norm(text):
    """The corpus prints typographic apostrophes and **bold**; the modules do not."""
    return " ".join((text or "").replace("’", "'").replace("**", "").split())


def tracker(phase, owner=ORK, battle_round=2):
    tt = TurnTracker()
    tt.started = True
    tt.battle_round = battle_round
    tt.turn_index_in_round = 0
    tt.phase_index = PHASES.index(phase)
    tt.turn_owner = owner
    tt.set_active(owner)
    return tt


def strat(cp=10):
    pool = CommandPointManager()
    for player in pool.cp:
        pool.cp[player] = cp
    return StratagemController(command_points=pool, game_log=tk.Log())


def cp_of(sc, player=ORK):
    return sc.command_points.cp[player]


def cluster(squad, point, spacing=1.35, per_row=4):
    n = len(squad.models)
    rows = (n + per_row - 1) // per_row
    cols = min(n, per_row)
    for i, model in enumerate(squad.models):
        r, col = divmod(i, per_row)
        model.x_in = point[0] + (col - (cols - 1) / 2.0) * spacing
        model.y_in = point[1] + (r - (rows - 1) / 2.0) * spacing
    return squad


def led_boyz(owner=ORK, name="1 Boyz 1"):
    """A Warboss leading Boyz - an attached ORKS INFANTRY unit (19.01)."""
    boyz = tk.build(ork.BOYZ, owner, name=name)
    warboss = tk.build(ork.WARBOSS, owner, name=name.replace("Boyz", "Warboss"))
    return attached_units.attach(warboss, boyz)


def boss_of(squad):
    return next((m for m in squad.models if getattr(m.profile, "character", False)), None)


def boy_of(squad):
    return next((m for m in squad.models if not getattr(m.profile, "character", False)), None)


def melee_of(model):
    return next((w for w in model.weapons if w.weapon_type == MELEE), None)


def ranged_of(model, name=None):
    return next((w for w in model.weapons
                 if w.weapon_type == RANGED and (name is None or w.name == name)), None)


def labels(dm):
    out = []
    for option in dm.options or []:
        out.append(option.get("label") if isinstance(option, dict) else option[0])
    return out


def pick(dm, needle):
    """Choose the option whose label contains `needle`; False if none."""
    for i, label in enumerate(labels(dm)):
        if needle.lower() in (label or "").lower():
            dm.choose(i)
            return True
    return False


def total_wounds(squad):
    return sum(max(0, m.current_wounds or 0) for m in squad.models)


def on_board(state, *squads):
    for squad in squads:
        for model in squad.models:
            state.add_token(model)


def place_at_gap(mover, enemy, gap, base=(20.0, 20.0)):
    """Put `enemy` straight north of `mover` so the AI's unit distance is `gap`."""
    t = gap
    for _ in range(40):
        tk.line_up(enemy, base[0], base[1] + t)
        d = agent_driver._squad_distance_between(mover, enemy)
        if abs(d - gap) < 0.01:
            break
        t += gap - d
    return enemy


# ==========================================================================
print("=== 1. the record, against the corpus ===")
# ==========================================================================

REC = ork.WAR_HORDE
c.true("the detachment is registered on the faction", ork.ORKS.detachments.get("War Horde") is REC)
c.eq("its rule is Get Stuck In", REC.rule_name, "Get Stuck In")
c.eq("...gated on WAR_HORDE_PLAYERS", REC.setting, war_horde.SETTING)
_dp = re.search(r"(\d+) DP detachment", CORPUS)
c.eq("its DP match the printed heading", REC.points, int(_dp.group(1)) if _dp else None)
_fd = re.search(r"Force Disposition: (.+)$", CORPUS, re.M)
c.eq("both printed Force Dispositions, in order",
     tuple(REC.force_dispositions),
     tuple(force_dispositions.from_printed_list(_fd.group(1).strip())) if _fd else None)
c.true("the record carries the PRINTED rule text",
       "Friendly ORKS units' melee attacks have [Sustained Hits 1]" in norm(REC.rule_text)
       and norm("Friendly ORKS units’ melee attacks have [Sustained Hits 1]") in norm(CORPUS))

_printed_enh = {name.strip(): int(pts) for name, pts in re.findall(r"^### (.+?) - (\d+) pts$", CORPUS, re.M)}
c.eq("the corpus prints four Enhancements", len(_printed_enh), 4)
c.eq("...the record names the same four at the same points",
     {e.name: e.points for e in REC.enhancements}, _printed_enh)
_wh_specs = {n: s for n, s in E.ENHANCEMENTS.items() if s.detachment == "War Horde"}
c.eq("...and all four are ENGINE-WIRED in the registry, at the same points",
     {n: s.points for n, s in _wh_specs.items()}, _printed_enh)
for _name, _spec in sorted(_wh_specs.items()):
    c.eq("%s gates on the detachment's setting" % _name, _spec.setting, REC.setting)
    c.eq("%s is printed ORKS model only" % _name, _spec.bearer_text, "ORKS model only")

_printed_strat = {norm(name).upper(): int(cp) for name, cp in re.findall(r"^### (.+?) - (\d)CP$", CORPUS, re.M)}
MODULE_STRATS = {
    bh.BREAKIN_HEADS_NAME: bh.BREAKIN_HEADS_CP,
    hit.HIT_EM_HARDER_NAME: hit.HIT_EM_HARDER_CP,
    nb.NEVER_BEATEN_NAME: nb.NEVER_BEATEN_CP,
    mow.MOW_EM_DOWN_NAME: mow.MOW_EM_DOWN_CP,
    ffi.FUNGUS_FUEL_NAME: ffi.FUNGUS_FUEL_CP,
    crd.CLOSE_RANGE_DAKKA_NAME: crd.CLOSE_RANGE_DAKKA_CP,
}
c.eq("the corpus prints six Stratagems", len(_printed_strat), 6)
c.eq("...and the six modules carry the same names at the same CP",
     {n.upper(): cp for n, cp in MODULE_STRATS.items()}, _printed_strat)

# Each module quotes its own printed line - a paraphrase would drift silently.
QUOTES = (
    (bh, "Roll one D3"),
    (hit, "Your unit's melee attacks have [Lethal Hits]"),
    (nb, "if your unit has not been selected to fight this phase"),
    (mow, "[CLEAVE 1] becomes [CLEAVE 2]"),
    (ffi, 'Your unit has +2" M'),
    (crd, "[RAPID FIRE 1] becomes [RAPID FIRE 2]"),
    (woppa, "this model's melee attacks have +1 AP"),
    (boss, "this unit is riled up until the start of your next turn"),
    (kunnin, "that fall-back move does not prevent this unit from being eligible to shoot"),
    (ladz, 'This unit has +2" M'),
)
for _module, _phrase in QUOTES:
    c.true("%s quotes '%s' - and the corpus prints it" % (_module.__name__, _phrase),
           _phrase in norm(_module.__doc__) and _phrase in norm(CORPUS))


# ==========================================================================
print("=== 2. Get Stuck In, on the detachment gate ===")
# ==========================================================================

_boyz = tk.build(ork.BOYZ, ORK, name="1 Boyz 1")
_boy = boy_of(_boyz)
_choppa = melee_of(_boy)
with settings_as(**WH):
    c.eq("War Horde: an Ork's melee weapon has [SUSTAINED HITS 1]",
         war_horde.get_stuck_in_adjusted_weapon(_choppa, [(_boy, _choppa)]).sustained_hits, 1)
with settings_as(**NO_WH):
    c.eq("...and without the detachment it does not",
         war_horde.get_stuck_in_adjusted_weapon(_choppa, [(_boy, _choppa)]).sustained_hits,
         _choppa.sustained_hits)


# ==========================================================================
print("=== 3. the four Enhancements ===")
# ==========================================================================

_plain = tk.build(ork.BOYZ, ORK, name="1 Boyz 2")
try:
    E.grant(_plain, ladz.FOLLOW_ME_LADZ)
    _refused = False
except ValueError:
    _refused = True
c.true("a unit with no ORKS CHARACTER cannot take one", _refused)

# --- Headwoppa's Killchoppa
W1 = led_boyz(name="1 Boyz 3")
W1_BOSS = boss_of(W1)
E.grant(W1, woppa.HEADWOPPAS_KILLCHOPPA, model=W1_BOSS)
_w_choppa = melee_of(W1_BOSS)
_w_boy = boy_of(W1)
with settings_as(**WH):
    c.eq("Killchoppa: no charge this turn, no AP", woppa.adjusted_weapon(_w_choppa, W1_BOSS).ap, _w_choppa.ap)
    W1.charged_this_turn = True
    _adj = woppa.adjusted_weapon(_w_choppa, W1_BOSS)
    c.eq("...after the unit charged, the BEARER's melee weapon has +1 AP", _adj.ap, _w_choppa.ap - 1)
    c.true("...on a copy - the shared instance is untouched", _adj is not _w_choppa)
    c.eq("...but a Boy in the same unit gets nothing",
         woppa.adjusted_weapon(melee_of(_w_boy), _w_boy).ap, melee_of(_w_boy).ap)
    _slugga = ranged_of(W1_BOSS)
    c.true("...and a ranged weapon is never touched", woppa.adjusted_weapon(_slugga, W1_BOSS) is _slugga)
    # Asked by VALUE, not by tuple position: rule 04.01.03 appended a profile
    # chain term after this one, and a [-1] pin went red on a key that was right.
    _term = object()
    _real_term = woppa.attack_key
    woppa.attack_key = lambda model: _term
    try:
        _in_key = _term in _melee_attack_key(W1_BOSS, _w_choppa)
    finally:
        woppa.attack_key = _real_term
    c.true("the melee grouping key carries the Killchoppa term", _in_key)
    c.eq("the bearer carries its own melee grouping term", woppa.attack_key(W1_BOSS), True)
    c.eq("...a Boy does not", woppa.attack_key(_w_boy), False)
    _fc = FightController(dice_manager=DiceManager(), turn_tracker=tracker(PHASE_FIGHT),
                          all_tokens=list(W1.models), decision_manager=DecisionManager(), game_log=tk.Log())
    _fc.fighting_squad = W1
    c.eq("...and game/fight.py's own chain applies it",
         _fc._adjusted_weapon([(W1_BOSS, _w_choppa)]).ap, _w_choppa.ap - 1)
with settings_as(**NO_WH):
    c.eq("without War Horde the charged bearer gets nothing", woppa.adjusted_weapon(_w_choppa, W1_BOSS).ap,
         _w_choppa.ap)
W1.charged_this_turn = False

# --- Da Boss is Watchin'
with settings_as(**BOTH):
    D1 = led_boyz(name="1 Boyz 4")
    D2 = led_boyz(name="1 Boyz 5")
    DF = led_boyz(owner=FOE, name="2 Boyz 4")
    for _squad in (D1, D2, DF):
        E.grant(_squad, boss.DA_BOSS_IS_WATCHIN, model=boss_of(_squad))
    _tt = tracker(PHASE_MOVEMENT)
    DB = boss.DaBossIsWatchinController(turn_tracker=_tt, squads_provider=lambda: [D1, D2, DF],
                                        game_log=tk.Log())
    c.true("Da Boss: offered in your Movement phase", DB.can_use(D1))
    c.true("...labelled as costing no CP", "no CP" in DB.panel_label(D1))
    c.true("...used", DB.use(D1))
    c.true("...the unit is riled up", riled_up.is_riled_up(D1))
    c.eq("...until the start of your next turn", D1.riled_up_expires_turn,
         riled_up.until_start_of_your_next_turn(_tt, ORK))
    c.true("...and the spend is written on the unit (a save keeps it)", D1.da_boss_is_watchin_used)
    c.eq("once per battle PER ARMY: a second bearer is refused", DB.can_use(D2), False)
    DB.turn_tracker = tracker(PHASE_MOVEMENT, owner=FOE)
    c.true("...while the OTHER army still has its own use", DB.can_use(DF))
    c.eq("not in your opponent's Movement phase", DB.can_use(D2), False)
    DB2 = boss.DaBossIsWatchinController(turn_tracker=tracker(PHASE_SHOOTING), squads_provider=lambda: [D2])
    c.eq("not in the Shooting phase", DB2.can_use(D2), False)
    DB3 = boss.DaBossIsWatchinController(turn_tracker=tracker(PHASE_MOVEMENT), squads_provider=lambda: [_plain])
    c.eq("not for a unit without the Enhancement", DB3.can_use(_plain), False)
with settings_as(**NO_WH):
    DB4 = boss.DaBossIsWatchinController(turn_tracker=tracker(PHASE_MOVEMENT), squads_provider=lambda: [D2])
    c.eq("not without War Horde", DB4.can_use(D2), False)

# --- Kunnin' But Brutal
K1 = led_boyz(name="1 Boyz 6")
E.grant(K1, kunnin.KUNNIN_BUT_BRUTAL, model=boss_of(K1))
K0 = led_boyz(name="1 Boyz 7")
with settings_as(**WH):
    c.true("Kunnin' But Brutal: may SHOOT after Falling Back", move_exceptions.may_shoot_after_falling_back(K1))
    c.true("...and may CHARGE after Falling Back", move_exceptions.may_charge_after_falling_back(K1))
    c.eq("the same unit without it may do neither (the counter-proof)",
         (move_exceptions.may_shoot_after_falling_back(K0), move_exceptions.may_charge_after_falling_back(K0)),
         (False, False))
with settings_as(**NO_WH):
    c.eq("...and without War Horde neither",
         (move_exceptions.may_shoot_after_falling_back(K1), move_exceptions.may_charge_after_falling_back(K1)),
         (False, False))

# --- Follow Me Ladz
L1 = led_boyz(name="1 Boyz 8")
E.grant(L1, ladz.FOLLOW_ME_LADZ, model=boss_of(L1))
_l_boy = boy_of(L1)
with settings_as(**NO_WH):
    _base = coldstar.effective_movement_in(_l_boy)
with settings_as(**WH):
    c.eq("Follow Me Ladz: +2\" Move for every model of the unit",
         coldstar.effective_movement_in(_l_boy), _base + ladz.FOLLOW_ME_LADZ_BONUS_IN)
    boss_of(L1).current_wounds = 0
    c.eq("...and nothing once the bearer is dead (19.04)", coldstar.effective_movement_in(_l_boy), _base)


# ==========================================================================
print("=== 4. Hit 'Em Harder ===")
# ==========================================================================

def hit_scene(engaged=True, owner=ORK, composition=0):
    scene = tk.fight_scene(ork.BOYZ, NECRON_WARRIORS, attacker_owner=ORK, engaged=engaged)
    if composition:
        big = tk.build(ork.BOYZ, ORK, name="Boyz A", composition_index=composition)
        tk.line_up(big, y=20.0)
        for model in scene["attacker"].models:
            scene["state"].tokens.remove(model)
        for model in big.models:
            scene["state"].add_token(model)
        scene["attacker"] = big
    scene["turn"].turn_owner = owner
    scene["sc"] = strat()
    scene["ctrl"] = hit.HitEmHarderController(scene["sc"], turn_tracker=scene["turn"],
                                              fight_controller=scene["fight"], game_log=tk.Log())
    return scene


with settings_as(**WH):
    S = hit_scene()
    A, T, FC, CTRL, SC = S["attacker"], S["target"], S["fight"], S["ctrl"], S["sc"]
    c.true("offered for an engaged ORKS unit that has not fought", CTRL.can_use(A))
    c.eq("...not for the enemy unit", CTRL.can_use(T), False)
    _pairs = [(m, melee_of(m)) for m in A.models]
    c.eq("before it, no [LETHAL HITS]", hit.adjusted_weapon(_pairs[0][1], A).lethal_hits, False)
    _before = cp_of(SC)
    c.true("...bought", CTRL.use(A))
    c.eq("...for its printed 1CP", _before - cp_of(SC), hit.HIT_EM_HARDER_CP)
    c.true("...melee attacks have [LETHAL HITS]", hit.adjusted_weapon(_pairs[0][1], A).lethal_hits)
    _s = ranged_of(A.models[0])
    c.true("...ranged weapons untouched", hit.adjusted_weapon(_s, A) is _s)
    FC.fighting_squad = A
    c.true("...and game/fight.py's chain carries it", FC._adjusted_weapon(_pairs[:1]).lethal_hits)
    FC.fighting_squad = None
    c.eq("not offered twice", CTRL.can_use(A), False)
    CTRL.reset_phase([A])
    c.eq("the end of the phase clears the grant", hit.is_active(A), False)

    S = hit_scene(owner=FOE)
    c.true("\"Fight phase\" has no 'your': offered in the OPPONENT's Fight phase too", S["ctrl"].can_use(S["attacker"]))

    S = hit_scene()
    S["fight"].fought_squad_ids.add(S["attacker"])
    c.eq("not once the unit has fought", S["ctrl"].can_use(S["attacker"]), False)
    S = hit_scene()
    S["fight"].fighting_squad = S["attacker"]
    c.eq("not while it is fighting", S["ctrl"].can_use(S["attacker"]), False)
    S = hit_scene(engaged=False)
    c.eq("not for a unit that is not eligible to fight", S["ctrl"].can_use(S["attacker"]), False)
    S = hit_scene()
    for _m in S["attacker"].models:
        for _w in _m.weapons:
            if _w.weapon_type == MELEE:
                _w.lethal_hits = True
    c.eq("never offered when every melee weapon already has [LETHAL HITS]", S["ctrl"].can_use(S["attacker"]), False)
    c.eq("...which the AI's gain also reads as nothing", hit.expected_lethal_gain(S["attacker"], S["target"]), 0.0)
    S = hit_scene()
    S["turn"].phase_index = PHASES.index(PHASE_SHOOTING)
    c.eq("not outside the Fight phase", S["ctrl"].can_use(S["attacker"]), False)
with settings_as(**NO_WH):
    S = hit_scene()
    c.eq("not without War Horde", S["ctrl"].can_use(S["attacker"]), False)


# ==========================================================================
print("=== 5. Mow 'Em Down ===")
# ==========================================================================

def mow_scene(sheet=ork.BATTLEWAGON, charged=True):
    scene = tk.fight_scene(sheet, NECRON_WARRIORS, attacker_owner=ORK)
    scene["attacker"].charged_this_turn = charged
    scene["sc"] = strat()
    scene["ctrl"] = mow.MowEmDownController(scene["sc"], turn_tracker=scene["turn"],
                                            fight_controller=scene["fight"], game_log=tk.Log())
    return scene


with settings_as(**WH):
    S = mow_scene()
    A, T, FC, CTRL = S["attacker"], S["target"], S["fight"], S["ctrl"]
    c.true("offered for an ORKS VEHICLE that charged this turn", CTRL.can_use(A))
    _pairs = [(m, melee_of(m)) for m in A.models]
    _w = _pairs[0][1]
    # Crushin' Bulk since stage E3d prints [CLEAVE 1] itself, so the grant is
    # measured as the step from one to two rather than from none to one.
    c.eq("(live) the Battlewagon's Crushin' Bulk prints [CLEAVE 1]", _w.cleave, 1)
    c.eq("...so it rolls one extra die per five models against ten",
         extra_attack_dice(_w, T, None, False, {}, _pairs), len(T.models) // 5)
    c.true("...bought", CTRL.use(A))
    _adj = mow.adjusted_weapon(_w, A)
    c.eq("...it becomes [CLEAVE 2]", _adj.cleave, 2)
    c.eq("...and the extra-dice step READS the grant: two dice per five models",
         extra_attack_dice(_adj, T, None, False, {}, _pairs), 2 * (len(T.models) // 5))
    FC.fighting_squad = A
    c.eq("...game/fight.py's chain carries it", FC._adjusted_weapon(_pairs).cleave, 2)
    FC.fighting_squad = None
    import copy as _copy
    _c2 = _copy.copy(_w)
    _c2.cleave = 2
    c.eq("an existing [CLEAVE 2] becomes [CLEAVE 3]", mow.adjusted_weapon(_c2, A).cleave, 3)
    c.eq("not twice", CTRL.can_use(A), False)
    CTRL.reset_phase([A])
    c.eq("the end of the phase clears it", mow.is_active(A), False)

    c.eq("not for a vehicle that did not charge", mow_scene(charged=False)["ctrl"].can_use(
        mow_scene(charged=False)["attacker"]), False)
    S = mow_scene(sheet=ork.DEFF_DREAD)
    c.eq("not for a WALKER (the Deff Dread)", S["ctrl"].can_use(S["attacker"]), False)
    S = mow_scene(sheet=ork.BOYZ)
    c.eq("not for INFANTRY", S["ctrl"].can_use(S["attacker"]), False)
with settings_as(**NO_WH):
    S = mow_scene()
    c.eq("not without War Horde", S["ctrl"].can_use(S["attacker"]), False)


# ==========================================================================
print("=== 6. Fungus-Fuel Injection ===")
# ==========================================================================

def fuel(owner=ORK, phase=PHASE_MOVEMENT):
    mover = SimpleNamespace(moved_squad_ids=set(), advanced_squad_ids=set())
    sc = strat()
    return sc, mover, ffi.FungusFuelInjectionController(sc, turn_tracker=tracker(phase, owner=owner),
                                                        movement_controller=mover, game_log=tk.Log())


with settings_as(**WH):
    TRUKK = tk.build(ork.TRUKK, ORK, name="1 Trukk 1")
    _base = coldstar.effective_movement_in(TRUKK.models[0])
    SC, MOVER, CTRL = fuel()
    c.true("offered for an ORKS VEHICLE that has not moved", CTRL.can_use(TRUKK))
    _before = cp_of(SC)
    c.true("...bought", CTRL.use(TRUKK))
    c.eq("...for 1CP", _before - cp_of(SC), ffi.FUNGUS_FUEL_CP)
    c.eq("...+2\" Move", coldstar.effective_movement_in(TRUKK.models[0]), _base + ffi.FUNGUS_FUEL_BONUS_IN)
    CTRL.reset_phase([TRUKK])
    c.eq("the end of the phase takes it back", coldstar.effective_movement_in(TRUKK.models[0]), _base)
    SC, MOVER, CTRL = fuel()
    MOVER.moved_squad_ids.add(TRUKK)
    c.eq("not once the unit has moved", CTRL.can_use(TRUKK), False)
    SC, MOVER, CTRL = fuel()
    MOVER.advanced_squad_ids.add(TRUKK)
    c.eq("not once it has Advanced", CTRL.can_use(TRUKK), False)
    c.eq("not for INFANTRY", fuel()[2].can_use(tk.build(ork.BOYZ, ORK, name="1 Boyz 9")), False)
    c.eq("not in your opponent's Movement phase", fuel(owner=FOE)[2].can_use(TRUKK), False)
    c.eq("not in the Shooting phase", fuel(phase=PHASE_SHOOTING)[2].can_use(TRUKK), False)
with settings_as(**NO_WH):
    c.eq("not without War Horde", fuel()[2].can_use(TRUKK), False)


# ==========================================================================
print("=== 7. Close-Range Dakka ===")
# ==========================================================================

def dakka(gap=6.0, sheet=ork.BOYZ, owner=ORK):
    scene = tk.shooting_scene(sheet, NECRON_WARRIORS, attacker_owner=ORK, gap=gap)
    scene["turn"].turn_owner = owner
    scene["sc"] = strat()
    scene["ctrl"] = crd.CloseRangeDakkaController(scene["sc"], turn_tracker=scene["turn"],
                                                  shooting_controller=scene["shooting"], game_log=tk.Log())
    return scene


with settings_as(**WH):
    S = dakka()
    A, T, CTRL = S["attacker"], S["target"], S["ctrl"]
    _pairs = [(m, w) for m in A.models for w in m.weapons if w.name == "Slugga"]
    _w = _pairs[0][1]
    c.true("offered for an ORKS unit that may shoot", CTRL.can_use(A))
    c.eq("(live) the Slugga has no [RAPID FIRE] - no extra dice in half range",
         extra_attack_dice(_w, T, None, False, {}, _pairs), 0)
    # A Boy carries a Shoota AND a close-quarters Slugga (2026-09 codex) and
    # may fire only one side of the two (rule 24.07), so the count is one die
    # per model that shoots, not one per weapon it carries.
    c.eq("the AI's count: one die per model inside half range, never both sides of 24.07",
         crd.expected_extra_dice(A, T.models),
         len([m for m in A.models if any(w.weapon_type == "ranged" for w in m.weapons)]))
    c.true("...bought", CTRL.use(A))
    _adj = crd.adjusted_weapon(_w, A)
    c.eq("...[RAPID FIRE 1]", _adj.rapid_fire, 1)
    c.eq("...and the extra-dice step READS it: one die per model in half range",
         extra_attack_dice(_adj, T, None, False, {}, _pairs), len(_pairs))
    S["shooting"].active_squad = A
    c.eq("...and game/shooting.py's chain carries it", S["shooting"]._adjusted_weapon(_pairs[:1], T).rapid_fire, 1)
    S["shooting"].active_squad = None
    _choppa = melee_of(A.models[0])
    c.true("...melee weapons untouched", crd.adjusted_weapon(_choppa, A) is _choppa)
    # The Warboss in Mega Armour's Big Shoota prints [RAPID FIRE 2] (the
    # pre-codex Warboss's Kombi-weapon, which stood here, is retired).
    _kombi_boss = tk.build(ork.WARBOSS_MEGA_ARMOUR, ORK, name="1 Warboss in Mega Armour 9")
    _kombi_boss.close_range_dakka_active = True
    _kombi = ranged_of(_kombi_boss.models[0], "Big Shoota")
    c.eq("an existing [RAPID FIRE 2] becomes [RAPID FIRE 3]",
         crd.adjusted_weapon(_kombi, _kombi_boss).rapid_fire, 3)
    c.eq("not twice", CTRL.can_use(A), False)

    FAR = dakka(gap=20.0)
    FAR["attacker"].close_range_dakka_active = True
    _fpairs = [(m, w) for m in FAR["attacker"].models for w in m.weapons if w.name == "Slugga"]
    c.eq("outside half range the grant adds no die",
         extra_attack_dice(crd.adjusted_weapon(_fpairs[0][1], FAR["attacker"]), FAR["target"], None, False, {},
                           _fpairs), 0)
    c.eq("...and the AI's count agrees", crd.expected_extra_dice(FAR["attacker"], FAR["target"].models), 0)

    S = dakka()
    S["shooting"].active_squad = S["attacker"]
    c.eq("not while the unit is mid-activation", S["ctrl"].can_use(S["attacker"]), False)
    S = dakka()
    S["shooting"].shot_squad_ids.add(S["attacker"])
    c.eq("not once it has shot", S["ctrl"].can_use(S["attacker"]), False)
    S = dakka(owner=FOE)
    c.eq("not in your opponent's Shooting phase", S["ctrl"].can_use(S["attacker"]), False)
    S = dakka()
    S["turn"].phase_index = PHASES.index(PHASE_MOVEMENT)
    c.eq("not outside the Shooting phase", S["ctrl"].can_use(S["attacker"]), False)
    S = dakka(sheet=ork.BATTLEWAGON)
    c.eq("not for a unit with no ranged weapon", S["ctrl"].can_use(S["attacker"]), False)
with settings_as(**NO_WH):
    S = dakka()
    c.eq("not without War Horde", S["ctrl"].can_use(S["attacker"]), False)


# ==========================================================================
print("=== 8. Breakin' Heads ===")
# ==========================================================================

def heads(auto=(), verdict=None, phase=PHASE_COMMAND):
    battle_shock.clear_became_battle_shocked_listeners()
    sc = strat()
    dice = DiceManager()
    dm = DecisionManager()
    log = tk.Log()
    ctrl = bh.BreakinHeadsController(sc, dice_manager=dice, decision_manager=dm,
                                     turn_tracker=tracker(phase), game_log=log,
                                     auto_players=auto, verdict=verdict)
    battle_shock.add_became_battle_shocked_listener(ctrl.on_became_battle_shocked)
    return SimpleNamespace(sc=sc, dice=dice, dm=dm, log=log, ctrl=ctrl)


def allocate_all(ctrl, limit=40):
    steps = 0
    while ctrl.pending_damage_choice and steps < limit:
        ctrl.choose_damage_model(list(ctrl.pending_damage_choice)[0])
        steps += 1
    return steps


with settings_as(**WH):
    H = heads()
    LED = led_boyz(name="1 Boyz 10")
    PLAIN = tk.build(ork.BOYZ, ORK, name="1 Boyz 11")
    WAGON = tk.build(ork.BATTLEWAGON, ORK, name="1 Battlewagon 1")
    c.true("the door reports a transition", battle_shock.set_battle_shocked(LED, source="a failed test"))
    c.eq("an attached ORKS INFANTRY unit that BECOMES battle-shocked is queued", H.ctrl.queued, [LED])
    battle_shock.set_battle_shocked(PLAIN)
    c.eq("...an unattached one is not", PLAIN in H.ctrl.queued, False)
    battle_shock.set_battle_shocked(WAGON)
    c.eq("...nor a vehicle", WAGON in H.ctrl.queued, False)
    # The vehicle is ALSO unattached, so the line above cannot tell which clause
    # refused it; no Ork vehicle can be attached, so the INFANTRY clause is
    # isolated by answering "attached" for both.
    _real_attached = bh.attached_units.is_attached_unit
    bh.attached_units.is_attached_unit = lambda squad: True
    try:
        c.eq("...and with 'attached' answered yes, a VEHICLE is still refused - INFANTRY only",
             (bh.is_eligible_unit(WAGON), bh.is_eligible_unit(PLAIN)), (False, True))
    finally:
        bh.attached_units.is_attached_unit = _real_attached
    c.eq("a unit already shocked does not 'become' so again", battle_shock.set_battle_shocked(LED), False)
    c.eq("...and is not queued twice", H.ctrl.queued, [LED])

    H.dice.roll(count=1, label="someone else's roll")
    c.eq("the offer waits while dice are on the table", H.ctrl.offer_pending(), False)
    c.eq("...nothing asked", H.dm.is_pending, False)
    H.dice.acknowledge()
    c.true("...and is raised once they are gone", H.ctrl.offer_pending())
    c.true("...as a prompt to the Ork player", H.dm.is_pending and H.dm.player == ORK)
    c.eq("...Use or Decline", len(labels(H.dm)), 2)
    c.true("the target may be picked although it is battle-shocked", H.ctrl.can_use(LED))
    _before_cp = cp_of(H.sc)
    _before_w = total_wounds(LED)
    tk.script(2)
    c.true("Use", pick(H.dm, "Use"))
    c.eq("...1CP spent", _before_cp - cp_of(H.sc), bh.BREAKIN_HEADS_CP)
    c.true("...a D3 is rolled on the dice panel", H.dice.pending_values is not None)
    c.true("...and the controller is busy", H.ctrl.is_busy)
    H.dice.acknowledge()
    H.ctrl.on_dice_acknowledged()
    c.true("the allocation is the Ork player's own (several models qualify)",
           H.ctrl.pending_damage_choice is not None)
    allocate_all(H.ctrl)
    c.eq("...the D3's mortal wounds really land", _before_w - total_wounds(LED), 2)
    c.eq("...and the unit is no longer battle-shocked", LED.battle_shocked, False)
    c.eq("...and nothing is left open", H.ctrl.is_busy, False)

    H = heads()
    LED2 = led_boyz(name="1 Boyz 12")
    battle_shock.set_battle_shocked(LED2)
    H.ctrl.offer_pending()
    _before_cp = cp_of(H.sc)
    c.true("Decline", pick(H.dm, "Decline"))
    c.eq("...costs nothing and leaves it shocked", (cp_of(H.sc), LED2.battle_shocked), (_before_cp, True))

    H = heads(auto=(ORK,), verdict=lambda squad: True)
    LED3 = led_boyz(name="1 Boyz 13")
    battle_shock.set_battle_shocked(LED3)
    c.true("the AI buys it without a prompt when its verdict says so", H.ctrl.offer_pending())
    c.eq("...no prompt", H.dm.is_pending, False)
    c.true("...the D3 is rolled", H.dice.pending_values is not None)

    H = heads(auto=(ORK,), verdict=lambda squad: False)
    LED4 = led_boyz(name="1 Boyz 14")
    battle_shock.set_battle_shocked(LED4)
    _before_cp = cp_of(H.sc)
    c.eq("...and passes when it does not", (H.ctrl.offer_pending(), H.dm.is_pending, cp_of(H.sc)),
         (False, False, _before_cp))

with settings_as(**NO_WH):
    H = heads()
    LED5 = led_boyz(name="1 Boyz 15")
    battle_shock.set_battle_shocked(LED5)
    c.eq("without War Horde nothing is queued", H.ctrl.queued, [])
battle_shock.clear_became_battle_shocked_listeners()

# The AI's verdict at its boundaries. The positions are SEARCHED and checked
# live: an objective or an enemy the stage did not intend would decide it.
from game.objectives import is_within_range_of_objective as _in_obj_range  # noqa: E402
_st = GameState()
M2.build(_st)
_obj = _st.objectives[0]
_ox, _oy = objective_centre(_obj)
V = cluster(led_boyz(name="1 Boyz 16"), (_ox, _oy))
_foe = tk.build(NECRON_WARRIORS, FOE, name="2 Necron Warriors 1")
_open = next((x, y) for y in [v * 1.0 for v in range(6, 40)] for x in [v * 1.0 for v in range(6, 55)]
             if not _in_obj_range(cluster(V, (x, y)), _st.objectives))
cluster(V, _open)
cluster(_foe, (_open[0], _open[1] + 30.0))
c.true("(live) the open spot is out of every objective's range", not _in_obj_range(V, _st.objectives))
c.true("(live) ...and the enemy is more than 9\" away", V.min_distance_to(_foe) > bh.BREAKIN_HEADS_ENEMY_RANGE_IN)
c.eq("verdict: off every objective and far from the enemy, a sturdy unit passes",
     bh.ai_verdict(V, _foe.models, _st.objectives), False)
cluster(V, (_ox, _oy))
c.true("...on an objective it buys", bh.ai_verdict(V, _foe.models, _st.objectives))
cluster(V, _open)
cluster(_foe, (_open[0], _open[1] + 7.0))
c.true("(live) the enemy is now within 9\"", V.min_distance_to(_foe) <= bh.BREAKIN_HEADS_ENEMY_RANGE_IN)
c.true("...within 9\" of an enemy it buys", bh.ai_verdict(V, _foe.models, _st.objectives))
for _m in V.models[1:]:
    _m.current_wounds = 0
c.true("(live) fewer than six wounds left (%d)" % bh.remaining_wounds(V),
       bh.remaining_wounds(V) < bh.BREAKIN_HEADS_MIN_WOUNDS)
c.eq("...and a nearly dead unit is not worth it", bh.ai_verdict(V, _foe.models, _st.objectives), False)


# ==========================================================================
print("=== 9. Orks Is Never Beaten ===")
# ==========================================================================

def beaten(auto=(), worth=None, phase=PHASE_FIGHT, sheet=ork.BOYZ):
    st = GameState()
    M2.build(st)
    obj = st.objectives[0]
    ox, oy = objective_centre(obj)
    orks = cluster(tk.build(sheet, ORK, name="1 %s 1" % sheet.name), (ox, oy))
    foe = cluster(tk.build(NECRON_WARRIORS, FOE, name="2 Necron Warriors 1"), (ox, oy + 5.0))
    on_board(st, orks, foe)
    sc = strat()
    dm = DecisionManager()
    fc = SimpleNamespace(fought_squad_ids=set(), fighting_squad=None)
    ctrl = nb.OrksIsNeverBeatenController(sc, decision_manager=dm, turn_tracker=tracker(phase, owner=FOE),
                                          fight_controller=fc, game_state=st, game_log=tk.Log(),
                                          auto_players=auto, worth_using=worth)
    return SimpleNamespace(st=st, obj=obj, orks=orks, foe=foe, sc=sc, dm=dm, fc=fc, ctrl=ctrl)


def kill(n, model, roll):
    model.current_wounds = 0
    tk.script(roll)
    return n.ctrl.intercept_destroyed(n.st.remove_dead_models())


with settings_as(**WH):
    N = beaten()
    c.eq("a ranged attack does not open it", N.ctrl.maybe_offer(N.foe, N.orks, melee=False), False)
    c.eq("...nor an attack by a friendly unit", N.ctrl.maybe_offer(N.orks, N.orks, melee=True), False)
    c.true("a melee attack on an ORKS unit asks its player", N.ctrl.maybe_offer(N.foe, N.orks, melee=True))
    c.true("...the Ork player", N.dm.is_pending and N.dm.player == ORK)
    c.eq("...once per attacker", N.ctrl.maybe_offer(N.foe, N.orks, melee=True), False)
    _before = cp_of(N.sc)
    c.true("Use", pick(N.dm, "Use"))
    c.eq("...1CP", _before - cp_of(N.sc), nb.NEVER_BEATEN_CP)
    c.true("...the unit is protected", N.ctrl.is_active(N.orks))

    VICTIM = N.orks.models[1]
    _alive_oc = N.obj.level_of_control(N.st.tokens).get(ORK, 0)
    c.eq("a 4 keeps the destroyed model", kill(N, VICTIM, 4), [VICTIM])
    c.true("...on the battlefield, in its unit, off the destroyed list",
           VICTIM in N.st.tokens and VICTIM in N.orks.models and VICTIM not in N.orks.destroyed_models)
    c.eq("...marked so the sweep leaves it", VICTIM.kept_after_death, True)
    c.eq("the NEXT frame's sweep does not take it again", N.st.remove_dead_models(), [])
    c.true("...it is still there", VICTIM in N.st.tokens)
    c.eq("...and still kept exactly once", N.ctrl.models_kept(), [VICTIM])
    c.true("it fights with its unit - it is in the unit's melee groups",
           any(m is VICTIM for pairs in _melee_attack_groups(N.orks).values() for m, _w in pairs))
    _dead_oc = N.obj.level_of_control(N.st.tokens).get(ORK, 0)
    c.eq("it adds no Objective Control", _alive_oc - _dead_oc, VICTIM.profile.oc)
    _saved = (VICTIM.x_in, VICTIM.y_in)
    VICTIM.x_in, VICTIM.y_in = _saved[0] + 25.0, _saved[1]
    c.eq("it is not part of the unit's coherency", N.orks.check_coherency(), [])
    _other = N.orks.models[2]
    _other_saved = (_other.x_in, _other.y_in)
    _other.x_in = _other.x_in + 25.0
    c.true("...while a LIVING straggler still breaks it (the counter-proof)", bool(N.orks.check_coherency()))
    _other.x_in, _other.y_in = _other_saved
    VICTIM.x_in, VICTIM.y_in = _saved
    _snap = scene_io.capture(N.st, "map2")
    _entry = next((e for e in _snap.get("squads", []) if e.get("name") == N.orks.name), None)
    c.eq("a save lists it as a casualty, not as a model", len((_entry or {}).get("models", ())),
         len(N.orks.models) - 1)

    c.eq("a 3 is not enough without riled up", kill(N, N.orks.models[3], 3), [])
    N.orks.riled_up = True
    _m4 = N.orks.models[4]
    c.eq("...but +1 while riled up makes it", kill(N, _m4, 3), [_m4])
    N.orks.riled_up = False

    N.fc.fought_squad_ids.add(N.orks)
    c.eq("once the unit has been selected to fight, a death is not rolled for", kill(N, N.orks.models[5], 6), [])
    c.eq("...and it is not offered", N.ctrl.can_use(N.orks), False)
    N.fc.fought_squad_ids.discard(N.orks)

    _removed = N.ctrl.on_unit_finished_fighting(N.orks)
    c.eq("when YOUR unit has fought, its kept models are removed", sorted(id(m) for m in _removed),
         sorted(id(m) for m in (VICTIM, _m4)))
    c.true("...off the battlefield and on the destroyed list",
           VICTIM not in N.st.tokens and VICTIM not in N.orks.models and VICTIM in N.orks.destroyed_models)
    c.eq("...and no longer marked", VICTIM.kept_after_death, False)
    c.eq("...nothing kept any more", N.ctrl.models_kept(), [])

    # Removal is per UNIT: two protected units, each keeps one.
    N = beaten()
    GRETS = cluster(tk.build(ork.BOYZ, ORK, name="1 Boyz 99"), (objective_centre(N.obj)[0] + 8.0,
                                                                  objective_centre(N.obj)[1]))
    on_board(N.st, GRETS)
    N.ctrl.use(N.orks)
    N.ctrl._stratagem.allow_repeat_target = True
    N.sc.reset_phase()
    N.ctrl.use(GRETS)
    _a, _b = N.orks.models[1], GRETS.models[1]
    kill(N, _a, 6)
    kill(N, _b, 6)
    c.eq("(live) both units keep one", len(N.ctrl.models_kept()), 2)
    N.ctrl.on_unit_finished_fighting(N.orks)
    c.eq("...one unit fighting removes only ITS model", N.ctrl.models_kept(), [_b])
    # The ledger alone would still list a model the board has lost; the board
    # is what the other unit fights with.
    c.true("...and the other unit's kept model is still on the battlefield",
           _b in N.st.tokens and _b in GRETS.models and _a not in N.st.tokens)
    N.ctrl.reset_phase()
    c.true("the end of the phase removes the rest", _b not in N.st.tokens and N.ctrl.models_kept() == [])
    c.eq("...and ends the protection", N.ctrl.is_active(GRETS), False)

    N = beaten(auto=(ORK,), worth=lambda attacker, target: False)
    _before = cp_of(N.sc)
    c.eq("the AI passes when its verdict says the attack will not kill enough",
         (N.ctrl.maybe_offer(N.foe, N.orks, melee=True), N.dm.is_pending, cp_of(N.sc)), (False, False, _before))
    N = beaten(auto=(ORK,), worth=lambda attacker, target: True)
    c.true("...and buys it without a prompt when it does", N.ctrl.maybe_offer(N.foe, N.orks, melee=True)
           and not N.dm.is_pending and N.ctrl.is_active(N.orks))

    N = beaten(phase=PHASE_SHOOTING)
    c.eq("not outside the Fight phase", N.ctrl.can_use(N.orks), False)
    N = beaten()
    c.eq("not for the enemy unit", N.ctrl.can_use(N.foe), False)
    _real_titanic = titanic.is_titanic_unit
    titanic.is_titanic_unit = lambda squad: True
    try:
        c.eq("not for a TITANIC unit", N.ctrl.can_use(N.orks), False)
    finally:
        titanic.is_titanic_unit = _real_titanic
with settings_as(**NO_WH):
    N = beaten()
    c.eq("not without War Horde", N.ctrl.can_use(N.orks), False)


# ==========================================================================
print("=== 10. the shared ledger: a kept model is not swept again ===")
# ==========================================================================

_st = GameState()
_squad = tk.line_up(tk.build(ork.BOYZ, ORK, name="1 Boyz 50"), 20, 20)
on_board(_st, _squad)
_ledger = FightAfterDeath(4, "Probe", game_state=_st)
_v = _squad.models[0]
_v.current_wounds = 0
tk.script(6)
c.eq("frame 0: swept once and kept", _ledger.roll_for(_st.remove_dead_models(), lambda m: True), [_v])
for _frame in range(1, 6):
    tk.script(1)
    _ledger.roll_for(_st.remove_dead_models(), lambda m: True)
c.true("...still on the board five frames later, with a 1 scripted every frame", _v in _st.tokens)
tk.script(6)
_ledger.roll_for([_v], lambda m: True)
c.eq("...and owed exactly once even if handed over again", _ledger.models_owed_an_activation(), [_v])
_plain_dead = _squad.models[1]
_plain_dead.current_wounds = 0
c.eq("an ordinary dead token is still swept (the counter-proof)", _st.remove_dead_models(), [_plain_dead])
_ledger.resolve_after_attacks()
c.true("removal clears the mark and takes it off", not _v.kept_after_death and _v not in _st.tokens)

_ledger_modules = sorted(
    f[:-3] for f in os.listdir("game")
    if f.endswith(".py") and f != "fight_after_death.py"
    and "FightAfterDeath(" in io.open(os.path.join("game", f), encoding="utf-8").read())
c.eq("the five rules on the ledger inherit the fix", _ledger_modules,
     ["aspect_to_their_final_breath", "cryptothralls", "dlc_undying_spite",
      "horde_orks_is_never_beaten", "malevolent_souls"])


# ==========================================================================
print("=== 11. the AI's deterministic handlers ===")
# ==========================================================================

with settings_as(**WH):
    # Da Boss is Watchin'
    A = cluster(led_boyz(name="1 Boyz 60"), (20.0, 20.0))
    E.grant(A, boss.DA_BOSS_IS_WATCHIN, model=boss_of(A))
    ENEMY = tk.build(NECRON_WARRIORS, FOE, name="2 Necron Warriors 60")
    CTRL = boss.DaBossIsWatchinController(turn_tracker=tracker(PHASE_MOVEMENT), squads_provider=lambda: [A])
    _reach = observation.advance_reach_in(A) + agent_driver.CHARGE_RANGE_IN
    place_at_gap(A, ENEMY, _reach + 3.0, base=(20.0, 23.0))
    c.eq("Da Boss: an enemy beyond Advance + charge, the AI holds it",
         agent_driver._handle_da_boss(ORK, A.models + ENEMY.models, CTRL), False)
    place_at_gap(A, ENEMY, _reach - 3.0, base=(20.0, 23.0))
    c.true("...within reach, it riles the unit up",
           agent_driver._handle_da_boss(ORK, A.models + ENEMY.models, CTRL) and riled_up.is_riled_up(A))

    # Fungus-Fuel Injection
    TR = tk.line_up(tk.build(ork.TRUKK, ORK, name="1 Trukk 60"), 20.0, 20.0)
    FOES = tk.build(NECRON_WARRIORS, FOE, name="2 Necron Warriors 61")
    _move = agent_driver.min_model_movement(TR)
    for _gap, _want in ((_move - 1.0, False), (_move + 1.0, True), (_move + ffi.FUNGUS_FUEL_BONUS_IN + 1.0, False)):
        _sc, _mover, _ctrl = fuel()
        place_at_gap(TR, FOES, _gap)
        c.eq("Fungus-Fuel: the nearest enemy %.1f\" away with Move %.0f\"" % (_gap, _move),
             agent_driver._handle_fungus_fuel(ORK, TR.models + FOES.models, _ctrl), _want)

    # Close-Range Dakka
    S = dakka()
    c.true("(live) ten Sluggas inside half range",
           crd.expected_extra_dice(S["attacker"], S["target"].models) >= crd.CLOSE_RANGE_DAKKA_MIN_EXTRA_DICE)
    c.true("Close-Range Dakka: the AI buys it for enough extra dice",
           agent_driver._handle_close_range_dakka(ORK, S["state"].tokens, S["ctrl"]))
    S = dakka(gap=20.0)
    c.eq("...and not when the target is outside half range",
         agent_driver._handle_close_range_dakka(ORK, S["state"].tokens, S["ctrl"]), False)

    # Hit 'Em Harder. Ten Boyz against Necron Warriors come out under the AI's
    # floor (measured 1.61), so the buying side is the twenty-model mob.
    S = hit_scene()
    _gain10 = hit.expected_lethal_gain(S["attacker"], S["target"])
    c.true("(live) ten Boyz stay under the floor (%.2f)" % _gain10, _gain10 < hit.HIT_EM_HARDER_MIN_GAIN)
    c.eq("Hit 'Em Harder: the AI keeps its CP for them",
         agent_driver._handle_hit_em_harder(ORK, S["state"].tokens, S["fight"], S["ctrl"]), False)
    S = hit_scene(composition=1)
    _gain = hit.expected_lethal_gain(S["attacker"], S["target"])
    c.true("(live) twenty Boyz reach it (%.2f)" % _gain, _gain >= hit.HIT_EM_HARDER_MIN_GAIN)
    c.true("...and the AI buys it for them",
           agent_driver._handle_hit_em_harder(ORK, S["state"].tokens, S["fight"], S["ctrl"]))
    S = hit_scene()
    for _m in list(S["attacker"].models[1:]):
        S["attacker"].models.remove(_m)
        S["state"].tokens.remove(_m)
    _gain = hit.expected_lethal_gain(S["attacker"], S["target"])
    c.true("(live) one model gains less (%.2f)" % _gain, _gain < hit.HIT_EM_HARDER_MIN_GAIN)
    c.eq("...and the AI keeps its CP",
         agent_driver._handle_hit_em_harder(ORK, S["state"].tokens, S["fight"], S["ctrl"]), False)

    # Mow 'Em Down
    S = mow_scene()
    c.true("Mow 'Em Down: the AI buys it against ten models",
           agent_driver._handle_mow_em_down(ORK, S["state"].tokens, S["fight"], S["ctrl"]))
    S = mow_scene()
    for _m in list(S["target"].models[mow.MOW_EM_DOWN_MIN_TARGET_MODELS - 1:]):
        S["target"].models.remove(_m)
        S["state"].tokens.remove(_m)
    c.eq("...and not against four, where [CLEAVE 2] adds no die",
         agent_driver._handle_mow_em_down(ORK, S["state"].tokens, S["fight"], S["ctrl"]), False)


# ==========================================================================
print("=== 12. wiring and roster ===")
# ==========================================================================

_tree = ast.parse(MAIN_SRC)
_lines = MAIN_SRC.splitlines()
_statements = {}
for _node in ast.walk(_tree):
    if isinstance(_node, ast.Expr) and isinstance(_node.value, ast.Call):
        _text = " ".join(" ".join(_lines[_node.lineno - 1:_node.end_lineno]).split())
        _statements.setdefault(_text, _node.lineno)


def statement_line(needle):
    return next((line for text, line in _statements.items() if text == needle or text.startswith(needle)), None)


for _needle in (
    "battle_shock_module.clear_became_battle_shocked_listeners()",
    "battle_shock_module.add_became_battle_shocked_listener(breakin_heads_controller.on_became_battle_shocked)",
    "fight_controller.target_reactions.append(never_beaten_controller)",
    "never_beaten_controller.intercept_destroyed(_swept)",
    "never_beaten_controller.on_unit_finished_fighting(_fighter)",
    "never_beaten_controller.reset_phase()",
    "breakin_heads_controller.offer_pending()",
    "breakin_heads_controller.on_dice_acknowledged()",
    "hit_em_harder_controller.reset_phase(_horde_squads)",
    "mow_em_down_controller.reset_phase(_horde_squads)",
    "fungus_fuel_controller.reset_phase(_horde_squads)",
    "close_range_dakka_controller.reset_phase(_horde_squads)",
):
    c.true("main.py runs `%s` as a statement" % _needle, statement_line(_needle) is not None)
_clear = statement_line("battle_shock_module.clear_became_battle_shocked_listeners()")
_add = statement_line("battle_shock_module.add_became_battle_shocked_listener(")
c.true("...the listener list is cleared BEFORE Breakin' Heads joins it",
       _clear is not None and _add is not None and _clear < _add)
_sweep = MAIN_SRC.find("_swept = state.remove_dead_models()")
_intercept = MAIN_SRC.find("never_beaten_controller.intercept_destroyed(_swept)")
c.true("...Never Beaten intercepts right after the sweep", 0 <= _sweep < _intercept)

_registered = set()
for _node in ast.walk(_tree):
    if (isinstance(_node, ast.Call) and isinstance(_node.func, ast.Attribute) and _node.func.attr == "add"
            and isinstance(_node.func.value, ast.Name) and _node.func.value.id == "proactive_stratagems"):
        for _arg in _node.args:
            if isinstance(_arg, ast.Call) and isinstance(_arg.func, ast.Name):
                _registered.add(_arg.func.id)
for _cls in ("DaBossIsWatchinController", "HitEmHarderController", "MowEmDownController",
             "FungusFuelInjectionController", "CloseRangeDakkaController"):
    c.true("%s is on main.py's panel registry" % _cls, _cls in _registered)
c.eq("...the two reactive Stratagems are not",
     sorted(n for n in ("BreakinHeadsController", "OrksIsNeverBeatenController") if n in _registered), [])

_kw = set()
for _node in ast.walk(_tree):
    if isinstance(_node, ast.Call) and (
            (isinstance(_node.func, ast.Name) and _node.func.id == "take_one_action")
            or (isinstance(_node.func, ast.Attribute) and _node.func.attr == "take_one_action")):
        _kw |= {k.arg for k in _node.keywords}
c.true("(live) main.py calls take_one_action with keywords", len(_kw) > 5)
for _name in ("da_boss_controller", "fungus_fuel_controller", "close_range_dakka_controller",
              "hit_em_harder_controller", "mow_em_down_controller", "breakin_heads_controller"):
    c.true("the AI's take_one_action gets %s" % _name, _name in _kw)

for _flag in ("hit_em_harder_active", "mow_em_down_active", "fungus_fuel_injection_active",
              "close_range_dakka_active", "da_boss_is_watchin_used"):
    c.true("a save keeps %s" % _flag, _flag in activation_state.SQUAD_FLAGS)

_orks_list = army_lists.get("orks")
c.eq("the shipped Ork list declares War Horde", tuple(_orks_list.detachments), ("War Horde",))
c.eq("...and buys none of its Enhancements - they are dormant by roster, the Stratagems are live",
     list(_orks_list.enhancement_names()), [])

c.finish()
