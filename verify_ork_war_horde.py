"""Runtime proof through the REAL main() loop that War Horde is wired.

test_ork_war_horde.py and test_ork_detachment_ui.py drive the controllers and the
panel directly and pin main.py by AST. What neither can show is that MAIN'S
objects, built by MAIN'S constructors in MAIN'S order, are connected when the
game runs. So this runs selfplay.py's real main() loop with the ORKS AS PLAYER 1
and asks main()'s live objects four questions:

  A. THE WIRING. The five panel controllers are on main()'s live registry, Breakin'
     Heads listens at game/battle_shock.py's one door, Orks Is Never Beaten sits in
     the live FightController's target reactions, and the shipped Ork list really
     declares War Horde for Player 1.
  B. BREAKIN' HEADS END TO END. A unit made battle-shocked through the real door
     is offered the Stratagem by main()'s own per-frame hook - a prompt to Player 1
     - and declining it costs nothing.
  C. A KEPT MODEL SURVIVES MAIN'S SWEEPS. The finding of this stage: a destroyed
     model a rule keeps on the battlefield was swept again the next frame. A model
     Orks Is Never Beaten keeps must still be on the board KEPT_FRAMES later, with
     main()'s own remove_dead_models() running every one of those frames.
  D. THE FIVE BUTTONS reach the screen, and only in their printed phases.

STAGED, each named rather than quietly faked:
  * THE ORKS AS PLAYER 1 (config ships aeldari against necrons).
  * B: the battle-shock itself (set through the real door) and 3 CP for Player 1,
    so a CP-less first round cannot hide the offer.
  * C: the protection (the unit is marked protected on the live controller, as
    use() would), the model's death (0 wounds), and the ledger's D6 (a 6). The
    sweep, the interception and every later frame are main()'s.
  * D: a selected Player 1 unit every frame and the phase (a MockAgent run does
    not visit all five reliably), the Da Boss is Watchin' Enhancement on the
    Warboss (no shipped list buys it), a Battlewagon that "charged", and "eligible
    to fight" answered yes on the live FightController - nothing is engaged.
  * Player 1 prompts this harness does not answer (War Cry, and the like) are
    declined after STALE_FRAMES frames and named in the report.

--neutralize loads main.py through an import hook with the measured seams undone
(the listener registration and the five registry registrations) and restores the
pre-fix sweep that takes a kept model again. The files on disk are not touched.

Usage:  python verify_ork_war_horde.py [map2] [frames]
        python verify_ork_war_horde.py map2 --neutralize
"""

import importlib.abc
import importlib.util
import os
import runpy
import sys

import pygame

from game import battle_shock, config, enhancements
from game.decision import DecisionManager
from game.game_state import GameState
from game.renderer import Renderer
from game.turn import (PHASES, PHASE_CHARGE, PHASE_COMMAND, PHASE_FIGHT,
                       PHASE_MOVEMENT, PHASE_SHOOTING, TurnTracker)
from game.ui import button_style

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

HUMAN = "Player 1"
STAGE_AT = 150
STALE_FRAMES = 30
KEPT_FRAMES = 60
PROMPT_WAIT = 90
ROTATE_FRAMES = 900

WHEN = {
    "Da Boss is Watchin'": {PHASE_MOVEMENT},
    "Fungus-Fuel Injection": {PHASE_MOVEMENT},
    "Close-Range Dakka": {PHASE_SHOOTING},
    "Hit 'Em Harder": {PHASE_FIGHT},
    "Mow 'Em Down": {PHASE_FIGHT},
}
REGISTERED = ("da_boss_controller", "fungus_fuel_controller", "close_range_dakka_controller",
              "hit_em_harder_controller", "mow_em_down_controller")

NEUTRALIZE_EDITS = (
    ("    battle_shock_module.add_became_battle_shocked_listener(breakin_heads_controller.on_became_battle_shocked)\n",
     "    pass\n"),
    ("hit_em_harder_controller = proactive_stratagems.add(HitEmHarderController(",
     "hit_em_harder_controller = (HitEmHarderController("),
    ("mow_em_down_controller = proactive_stratagems.add(MowEmDownController(",
     "mow_em_down_controller = (MowEmDownController("),
    ("fungus_fuel_controller = proactive_stratagems.add(FungusFuelInjectionController(",
     "fungus_fuel_controller = (FungusFuelInjectionController("),
    ("close_range_dakka_controller = proactive_stratagems.add(CloseRangeDakkaController(",
     "close_range_dakka_controller = (CloseRangeDakkaController("),
    ("da_boss_controller = proactive_stratagems.add(DaBossIsWatchinController(",
     "da_boss_controller = (DaBossIsWatchinController("),
)

if NEUTRALIZE:
    _MAIN_PATH = os.path.abspath("main.py")
    with open(_MAIN_PATH, encoding="utf-8") as fh:
        _src = fh.read().replace("\r\n", "\n")
    for _anchor, _replacement in NEUTRALIZE_EDITS:
        if _src.count(_anchor) != 1:
            raise SystemExit("neutralize anchor not unique in main.py: %r (%d)"
                             % (_anchor, _src.count(_anchor)))
        _src = _src.replace(_anchor, _replacement)
    _NEUTRAL_SRC = _src

    class _NeutralLoader(importlib.abc.Loader):
        def create_module(self, spec):
            return None

        def exec_module(self, module):
            module.__file__ = _MAIN_PATH
            exec(compile(_NEUTRAL_SRC, _MAIN_PATH, "exec"), module.__dict__)

    class _NeutralFinder(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path, target=None):
            if fullname != "main":
                return None
            return importlib.util.spec_from_loader("main", _NeutralLoader(), origin=_MAIN_PATH)

    sys.meta_path.insert(0, _NeutralFinder())

    def _pre_fix_sweep(self):
        """GameState.remove_dead_models() as it was before this stage."""
        dead = []
        while True:
            batch = [token for token in self.tokens if token.is_dead()]
            if not batch:
                return dead
            self._remove_tokens(batch)
            dead.extend(batch)

    GameState.remove_dead_models = _pre_fix_sweep

state = {"frames": 0, "tracker": None, "wiring": None, "b": None, "c": None, "prompts": [],
         "declined_other": [], "stale": None, "stale_since": 0, "rotating": False, "rotate_start": None,
         "seen": {}, "off_when": [], "phases": set(), "staged_d": None, "asked": {}}


def _main_locals():
    frame = sys._getframe(1)
    while frame is not None and frame.f_code.co_name != "main":
        frame = frame.f_back
    return frame.f_locals if frame is not None else None


_real_tracker_init = TurnTracker.__init__


def tracker_init(self, *args, **kwargs):
    _real_tracker_init(self, *args, **kwargs)
    state["tracker"] = self


TurnTracker.__init__ = tracker_init

_real_request = DecisionManager.request


def request(self, player, prompt, options, *args, **kwargs):
    out = _real_request(self, player, prompt, options, *args, **kwargs)
    if "Breakin' Heads" in (prompt or ""):
        state["prompts"].append({"player": player, "frame": state["frames"], "prompt": prompt})
    return out


DecisionManager.request = request

_real_draw_button = button_style.draw_button


def draw_button(surface, rect, label, font, hovered=False, pressed=False, accent=None):
    name = (label or "").split(" (")[0].strip()
    if state["rotating"] and name in WHEN:
        tracker = state["tracker"]
        phase = tracker.phase if tracker is not None else None
        seen = state["seen"].setdefault(name, {"frame": state["frames"], "phases": set()})
        if phase is not None:
            seen["phases"].add(phase)
            if phase not in WHEN[name]:
                state["off_when"].append((name, phase, state["frames"]))
    return _real_draw_button(surface, rect, label, font, hovered=hovered, pressed=pressed, accent=accent)


button_style.draw_button = draw_button

# WHY a button was refused in its own phase, MEASURED rather than guessed: an
# absence nobody explained is a story about the harness.
from game import enh_da_boss_is_watchin as _boss_mod   # noqa: E402
from game import horde_mow_em_down as _mow_mod         # noqa: E402
from game import riled_up as _riled                    # noqa: E402


def _why_boss(ctrl, squad):
    tt = ctrl.turn_tracker
    if tt.phase != PHASE_MOVEMENT or squad.owner != tt.turn_owner:
        return "clock (%s, %s)" % (tt.phase, tt.turn_owner)
    if not enhancements.is_active(squad, _boss_mod.DA_BOSS_IS_WATCHIN):
        return "Enhancement not active"
    if not _riled.has_ability(squad):
        return "no Waaagh! ability"
    if ctrl.is_used(squad.owner, squad):
        return "already used"
    return "?"


def _why_mow(ctrl, squad):
    fc = ctrl.fight_controller
    if not _mow_mod.is_eligible_vehicle(squad):
        return "not an ORKS VEHICLE, or a WALKER"
    if not getattr(squad, "charged_this_turn", False):
        return "did not charge"
    if squad in getattr(fc, "fought_squad_ids", ()) or getattr(fc, "fighting_squad", None) is squad:
        return "fought / fighting"
    if not fc.is_eligible_to_fight(squad):
        return "not eligible to fight"
    if _mow_mod.is_active(squad):
        return "already active"
    return "Stratagem refused (CP / 15.01)"


def _spy_can_use(cls, name, why):
    real = cls.can_use

    def can_use(self, squad):
        out = real(self, squad)
        tt = self.turn_tracker
        if (state["rotating"] and squad is not None and getattr(squad, "owner", None) == HUMAN
                and tt is not None and tt.phase in WHEN[name]):
            reason = "offered" if out else why(self, squad)
            counts = state["asked"].setdefault(name, {})
            k = "%s: %s" % (squad.name, reason)
            counts[k] = counts.get(k, 0) + 1
        return out

    cls.can_use = can_use


_spy_can_use(_boss_mod.DaBossIsWatchinController, "Da Boss is Watchin'", _why_boss)
_spy_can_use(_mow_mod.MowEmDownController, "Mow 'Em Down", _why_mow)


def _quiet(L):
    return not L["dice_manager"].is_pending and not L["decision_manager"].is_pending


def _decline_stale_human_prompt(decisions):
    if decisions is None or not decisions.is_pending or decisions.player != HUMAN:
        state["stale"] = None
        return
    prompt = decisions.prompt or ""
    if "Breakin' Heads" in prompt:
        return
    key = (id(decisions._queue[0]), prompt)
    if state["stale"] != key:
        state["stale"], state["stale_since"] = key, state["frames"]
        return
    if state["frames"] - state["stale_since"] >= STALE_FRAMES:
        state["declined_other"].append(prompt[:60])
        decisions.choose(len(decisions.options) - 1)
        state["stale"] = None


def _wiring(L):
    registry = L.get("proactive_stratagems")
    live = list(getattr(registry, "controllers", ()) or ())
    heads = L.get("breakin_heads_controller")
    fight = L.get("fight_controller")
    return {
        "on_registry": [n for n in REGISTERED if L.get(n) is not None and any(c is L[n] for c in live)],
        "listener": heads is not None and any(
            fn == heads.on_became_battle_shocked for fn in battle_shock._became_battle_shocked_listeners),
        "target_reaction": fight is not None and L.get("never_beaten_controller") in fight.target_reactions,
        "war_horde_players": tuple(getattr(config, "WAR_HORDE_PLAYERS", ())),
    }


def _human_units(L):
    return [s for s in L["state"].all_squads() if s.owner == HUMAN]


def _stage_b(L):
    from game import horde_breakin_heads as bh
    unit = next((s for s in sorted(_human_units(L), key=lambda s: s.name)
                 if bh.is_eligible_unit(s) and not s.battle_shocked), None)
    r = state["b"] = {"frame": state["frames"], "unit": getattr(unit, "name", None)}
    if unit is None:
        r["error"] = "no attached ORKS INFANTRY unit for Player 1"
        return
    pool = L["stratagem_controller"].command_points
    pool.cp[HUMAN] = max(pool.cp.get(HUMAN, 0), 3)
    r["cp_before"] = pool.cp[HUMAN]
    r["became"] = battle_shock.set_battle_shocked(unit, source="staged by verify_ork_war_horde.py")
    r["unit_obj"] = unit


def _watch_b(L):
    r = state["b"]
    if r is None or r.get("done") or r.get("error"):
        return
    decisions = L["decision_manager"]
    if (decisions.is_pending and decisions.player == HUMAN and "Breakin' Heads" in (decisions.prompt or "")):
        r["prompt_frame"] = state["frames"]
        r["labels"] = [o["label"] for o in decisions.options]
        decisions.choose(len(decisions.options) - 1)
        unit = r["unit_obj"]
        r["cp_after"] = L["stratagem_controller"].command_points.cp[HUMAN]
        r["still_shocked"] = unit.battle_shocked
        r["done"] = True
    elif state["frames"] - r["frame"] > PROMPT_WAIT:
        r["done"] = True


def _stage_c(L):
    ctrl = L["never_beaten_controller"]
    unit = next((s for s in sorted(_human_units(L), key=lambda s: s.name)
                 if sum(1 for m in s.models if not m.is_dead() and m in L["state"].tokens) >= 3), None)
    r = state["c"] = {"frame": state["frames"], "unit": getattr(unit, "name", None), "present": 0, "gone_at": None}
    if unit is None:
        r["error"] = "no Player 1 unit with three models on the board"
        return
    victim = next(m for m in unit.models if not m.is_dead() and not getattr(m.profile, "character", False)
                  and m in L["state"].tokens)
    ctrl._active.add(id(unit))
    # The FIRST roll keeps it; every later one is a 1. A sweep that takes the
    # model again (the pre-fix world) loses it on its second frame, while a sweep
    # that leaves it alone never rolls again.
    rolls = iter([6])
    ctrl._ledger._roll_one = lambda: next(rolls, 1)
    victim.current_wounds = 0
    tracker = state["tracker"]
    r["key"] = (tracker.battle_round, tracker.turn_owner, tracker.phase)
    r["victim"] = victim
    r["ctrl"] = ctrl


def _watch_c(L):
    r = state["c"]
    if r is None or r.get("done") or r.get("error"):
        return
    victim = r["victim"]
    tracker = state["tracker"]
    key = (tracker.battle_round, tracker.turn_owner, tracker.phase)
    if victim in L["state"].tokens:
        r["present"] += 1
        r["kept"] = r["ctrl"].models_kept().count(victim)
        if r["present"] >= KEPT_FRAMES:
            r["done"] = True
    else:
        r["gone_at"] = state["frames"] - r["frame"]
        # "...or at the end of the phase": main()'s own reset removes a kept
        # model at a phase boundary, which is the rule and not the bug.
        r["gone_at_phase_change"] = key != r["key"]
        r["done"] = True
    if r.get("done"):
        r["ctrl"].reset_phase()      # cleanup before D - named, not measured


def _restamp_d(L):
    """Re-applied EVERY rotation frame: selfplay still clicks Next Phase in
    Player 1's turn, and a real end of turn clears charged_this_turn."""
    wagon = state.get("wagon")
    if wagon is not None:
        wagon.charged_this_turn = True
    L["fight_controller"].is_eligible_to_fight = lambda squad: True


def _stage_d(L):
    from game.factions import orks as ork
    units = _human_units(L)
    led = next((s for s in units if any(getattr(m.profile, "character", False)
                                         and getattr(m.profile, "orks", False) for m in s.models)
                and any(m in L["state"].tokens for m in s.models)), None)
    wagon = next((s for s in units if s.datasheet is ork.BATTLEWAGON), None)
    r = state["staged_d"] = {"led": getattr(led, "name", None), "wagon": getattr(wagon, "name", None)}
    if led is not None:
        bearer = next(m for m in led.models if getattr(m.profile, "character", False))
        if not enhancements.has(led, "Da Boss is Watchin'"):
            enhancements.grant(led, "Da Boss is Watchin'", model=bearer)
    state["wagon"], state["led"] = wagon, led
    _restamp_d(L)
    state["pile_in"], state["fight"] = L.get("pile_in_controller"), L.get("fight_controller")
    state["rotating"] = True
    state["rotate_start"] = state["frames"]
    pool = L["stratagem_controller"].command_points
    pool.cp[HUMAN] = max(pool.cp.get(HUMAN, 0), 10)


_ORDER = (PHASE_COMMAND, PHASE_MOVEMENT, PHASE_SHOOTING, PHASE_CHARGE, PHASE_FIGHT)
_real_flip = pygame.display.flip


def flip(*args, **kwargs):
    state["frames"] += 1
    tracker = state["tracker"]
    if tracker is not None and getattr(tracker, "started", False):
        L = _main_locals()
        if L is not None and "never_beaten_controller" in L:
            if state["wiring"] is None:
                state["wiring"] = _wiring(L)
            if not state["rotating"]:
                _decline_stale_human_prompt(L.get("decision_manager"))
            if state["b"] is None and state["frames"] >= STAGE_AT and _quiet(L):
                _stage_b(L)
            elif state["b"] is not None and not state["b"].get("done"):
                _watch_b(L)
            elif state["b"] is not None and state["c"] is None and _quiet(L):
                _stage_c(L)
            elif state["c"] is not None and not state["c"].get("done"):
                _watch_c(L)
            elif state["c"] is not None and state["staged_d"] is None:
                _stage_d(L)
            if state["rotating"]:
                phase = _ORDER[(state["frames"] // 40) % len(_ORDER)]
                if phase == PHASE_FIGHT and state.get("staged_phase") != PHASE_FIGHT:
                    for _ctrl in (state.get("pile_in"), state.get("fight")):
                        if _ctrl is not None:
                            _ctrl.reset_fight_phase()
                _restamp_d(L)
                state["staged_phase"] = phase
                tracker.phase_index = PHASES.index(phase)
                tracker.turn_owner = HUMAN
                tracker.set_active(HUMAN)
                state["phases"].add(phase)
                decisions = L["decision_manager"]
                if decisions.is_pending:
                    decisions.choose(len(decisions.options) - 1)
                if state["frames"] - state["rotate_start"] >= ROTATE_FRAMES:
                    raise SystemExit(0)
    return _real_flip(*args, **kwargs)


pygame.display.flip = flip

_real_move_range = Renderer.draw_move_range


def draw_move_range(self, surface, board, movement_controller):
    if state["rotating"]:
        squads = []
        for token in movement_controller.all_tokens or ():
            squad = getattr(token, "squad", None)
            if squad is not None and squad.owner == HUMAN and squad not in squads:
                squads.append(squad)
        if squads and (state["frames"] % 17 == 0 or movement_controller.selected_squad is None):
            movement_controller.select(squads[(state["frames"] // 17) % len(squads)].models[0])
    return _real_move_range(self, surface, board, movement_controller)


Renderer.draw_move_range = draw_move_range

_argv = sys.argv[1:] or ["map2", "4000"]
sys.argv = ["selfplay.py"] + _argv
config.PLAYER1_ARMY = "orks"
config.PLAYER2_ARMY = "necrons"
config.ARMY_SELECT = False

try:
    runpy.run_module("selfplay", run_name="__main__")
except SystemExit:
    pass

w = state["wiring"] or {}
b = state["b"] or {}
cc = state["c"] or {}
print()
print("--- War Horde wiring" + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
print("  frames                          : %d" % state["frames"])
print("  A. on main()'s live registry    : %s" % w.get("on_registry"))
print("     Breakin' Heads at the door   : %s" % w.get("listener"))
print("     Never Beaten a target reaction: %s" % w.get("target_reaction"))
print("     WAR_HORDE_PLAYERS            : %s" % (w.get("war_horde_players"),))
print("  B. shocked through the door     : %s (became: %s)%s"
      % (b.get("unit"), b.get("became"), (" ERROR " + b["error"]) if b.get("error") else ""))
print("     prompt to Player 1           : %s" % (("frame +%d, options %s" % (b["prompt_frame"] - b["frame"], b.get("labels")))
                                                  if b.get("prompt_frame") else "NEVER"))
print("     declined: CP %s -> %s, still shocked %s" % (b.get("cp_before"), b.get("cp_after"), b.get("still_shocked")))
print("  C. kept model of                : %s%s" % (cc.get("unit"), (" ERROR " + cc["error"]) if cc.get("error") else ""))
print("     frames on the board          : %d%s" % (
    cc.get("present", 0),
    (" - GONE after %d frame(s) %s" % (cc["gone_at"], "at a phase change" if cc.get("gone_at_phase_change")
                                       else "inside the same phase"))
    if cc.get("gone_at") is not None else ""))
print("     times on the ledger          : %s" % cc.get("kept"))
print("  D. staged                       : %s" % (state["staged_d"],))
for name in sorted(WHEN):
    info = state["seen"].get(name)
    print("     %-24s %s" % (name, ("f%d %s" % (info["frame"], ",".join(sorted(info["phases"])))) if info else "NOT DRAWN"))
print("     off-WHEN sightings           : %d" % len(state["off_when"]))
for _name, _counts in sorted(state["asked"].items()):
    for _k, _n in sorted(_counts.items(), key=lambda kv: -kv[1])[:4]:
        print("     %-24s asked %4dx - %s" % (_name, _n, _k))
print("     stale Player 1 prompts declined: %s" % (state["declined_other"] or "none"))

if not state["wiring"] or state["staged_d"] is None or b.get("error") or cc.get("error"):
    print("  INCONCLUSIVE - the run never got through the staging")
    raise SystemExit(2)

if not NEUTRALIZE:
    checks = (
        ("all five War Horde panel controllers are on main()'s live registry",
         sorted(w.get("on_registry") or []) == sorted(REGISTERED)),
        ("Breakin' Heads listens at the battle-shock door", w.get("listener") is True),
        ("Orks Is Never Beaten is a live Fight target reaction", w.get("target_reaction") is True),
        ("the shipped Ork list fields War Horde for Player 1", HUMAN in (w.get("war_horde_players") or ())),
        ("a unit shocked through the door is offered Breakin' Heads by main()", bool(b.get("prompt_frame"))),
        ("declining costs nothing and leaves it shocked",
         b.get("cp_after") == b.get("cp_before") and b.get("still_shocked") is True),
        ("a kept model survives main()'s sweeps - %d frames, or until main() ends the phase" % KEPT_FRAMES,
         cc.get("present", 0) >= 3
         and (cc.get("present", 0) >= KEPT_FRAMES or cc.get("gone_at_phase_change") is True)),
        ("...kept exactly once", cc.get("kept") == 1),
        ("all five buttons reached the screen", set(state["seen"]) == set(WHEN)),
        ("no button outside its printed WHEN", not state["off_when"]),
    )
else:
    checks = (
        ("no War Horde controller on the live registry", not w.get("on_registry")),
        ("Breakin' Heads never hears the door", w.get("listener") is False),
        ("no Breakin' Heads prompt", not b.get("prompt_frame")),
        ("the kept model is swept again at once, inside the same phase (the pre-fix world)",
         cc.get("gone_at") is not None and cc.get("gone_at") <= 3 and cc.get("gone_at_phase_change") is False),
        ("no War Horde button reached the screen", not state["seen"]),
    )
ok = True
for label, passed in checks:
    print("  %-4s %s" % ("ok" if passed else "FAIL", label))
    ok = ok and bool(passed)
print("  VERDICT: %s" % ("OK" if ok else "FAILED"))
raise SystemExit(0 if ok else 1)
