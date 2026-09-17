"""Runtime proof through the REAL main() loop that the 2026-09 Ork vehicles'
reactive abilities are wired.

test_ork_vehicles.py drives each ability through real controllers built by the
test and pins main.py by AST. What it cannot show is that MAIN'S objects, built by
MAIN'S constructors in MAIN'S order, are connected when the game runs. So this
runs selfplay.py's real main() loop with the ORKS AS PLAYER 1 and asks main()'s
live objects:

  A. THE WIRING. Pilin' Out listens on the live MovementController,
     IngressController and TransportController and holds main()'s transport
     controller and clock; both AI policies are injected; the live
     ShootingController holds main()'s IngressController (Deff from Above).
  B. PILIN' OUT through main()'s own listener list, placement gate and resolved
     hook. A Player 2 unit ends a Normal move within 8" of a Player 1 Trukk in
     Player 2's Movement phase: the human is asked, the answer opens a RAPID
     disembark placement, main()'s AI (Player 2's own turn) is HELD while it is
     open, and confirming it runs the resolved hook main() registered.
  C. AERIAL MANOOVER and THE TURN-END SWEEP through main()'s own
     advance_turn_phase(): Player 2's Fight phase ends, Player 1's Deffkoptas are
     asked, the answer puts them in Strategic Reserves, and the charge lock the
     Pilin' Out disembark set in Player 2's turn is gone in Player 1's.
  D. DEFF FROM ABOVE through the live ShootingController: the Deffkoptas, marked
     as having made an ingress move this turn in main()'s IngressController, get
     the +1 to hit in the live hit modifiers.

STAGED, each named rather than quietly faked:
  * THE ORKS AS PLAYER 1 (config ships aeldari against necrons).
  * A Trukk carrying a Boyz unit is BUILT and put on the board within 8" of a
    Player 2 unit, on a spot whose disembark ring is clear (the shipped list has
    no Trukk); a Deffkoptas unit is BUILT on the spot farthest from Player 2.
  * B: the phase (Player 2's Movement) and the "move ended" moment - main()'s
    listeners are called the way MovementController calls them; the prompt is
    answered yes; after HOLD_FRAMES the Boyz are laid out in the ring around the
    Trukk the way a human would drag them, and the placement is confirmed.
  * C: the jump to the end of Player 2's Fight phase, in the same frame as B's
    confirm (so no AI frame runs in between), and main()'s own
    advance_turn_phase() called once. If B produced no disembark (the neutralized
    world), the charge lock is set on the Boyz by hand, and the report says so.
  * D: the ingress mark and the active squad, set and taken back in one frame.
  * Player 1 prompts this harness does not answer are declined after STALE_FRAMES.

--neutralize loads main.py through an import hook with the measured seams undone
(the three Pilin' Out listeners, the Aerial Manoover offer, the all-squads sweep
back to ending_squads, the ShootingController's IngressController). The files on
disk are not touched.

Usage:  python verify_ork_vehicles.py [map2] [frames]
        python verify_ork_vehicles.py map2 --neutralize
"""

import importlib.abc
import importlib.util
import math
import os
import runpy
import sys

import pygame

from game import config
from game.decision import DecisionManager
from game.factions import build_squad
from game.factions.orks import BOYZ, DEFFKOPTAS, TRUKK
from game.setup import PLACING
from game.squad import edge_distance
from game.transport import RAPID
from game.turn import PHASES, PHASE_FIGHT, PHASE_MOVEMENT, TurnTracker
from game.weapons import RANGED

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

HUMAN = "Player 1"
FOE = "Player 2"
STAGE_AT = 150
STALE_FRAMES = 30
HOLD_FRAMES = 90
WAIT = 400
RAPID_IN = 3.0
ENGAGEMENT_IN = 1.0

NEUTRALIZE_EDITS = (
    ("    movement_controller.on_move_finished.append(pilin_out_controller.on_move_finished)\n",
     "    pass\n"),
    ("    ingress_controller.on_ingress_resolved.append(pilin_out_controller.on_ingress_resolved)\n",
     "    pass\n"),
    ("    transport_controller.on_disembark_resolved.append(pilin_out_controller.on_disembark_resolved)\n",
     "    pass\n"),
    ("            aerial_manoover_controller.offer_at_end_of_fight_phase(\n",
     "            (lambda *_a: None)(\n"),
    ("            for squad in state.all_squads():\n                squad.fights_first = False\n",
     "            for squad in ending_squads:\n                squad.fights_first = False\n"),
    ("    shooting_controller.ingress_controller = ingress_controller\n", "    pass\n"),
)

if NEUTRALIZE:
    _MAIN_PATH = os.path.abspath("main.py")
    with open(_MAIN_PATH, encoding="utf-8") as fh:
        _src = fh.read().replace("\r\n", "\n")
    for _anchor, _replacement in NEUTRALIZE_EDITS:
        if _src.count(_anchor) != 1:
            raise SystemExit("neutralize anchor not unique in main.py: %r (%d)"
                             % (_anchor[:80], _src.count(_anchor)))
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

state = {"frames": 0, "tracker": None, "wiring": None, "setup": None, "b": None, "c": None, "d": None,
         "stale": None, "stale_since": 0, "declined_other": [], "prompts": []}


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
    if "Pilin' Out" in (prompt or "") or "Aerial Manoover" in (prompt or ""):
        state["prompts"].append({"player": player, "frame": state["frames"], "prompt": prompt,
                                 "labels": [o[0] for o in options]})
    return out


DecisionManager.request = request


def _alive(squad):
    return any(not m.is_dead() for m in squad.models)


def _quiet(L):
    return (not L["dice_manager"].is_pending and not L["decision_manager"].is_pending
            and L["setup_controller"].state != PLACING)


def _decline_stale_human_prompt(decisions):
    if decisions is None or not decisions.is_pending or decisions.player != HUMAN:
        state["stale"] = None
        return
    prompt = decisions.prompt or ""
    if "Pilin' Out" in prompt or "Aerial Manoover" in prompt:
        return                        # this harness's own subjects, answered below
    key = (id(decisions._queue[0]), prompt)
    if state["stale"] != key:
        state["stale"], state["stale_since"] = key, state["frames"]
        return
    if state["frames"] - state["stale_since"] >= STALE_FRAMES:
        state["declined_other"].append(prompt[:60])
        decisions.choose(len(decisions.options) - 1)
        state["stale"] = None


def _set_phase(phase, owner):
    tracker = state["tracker"]
    tracker.phase_index = PHASES.index(phase)
    tracker.turn_owner = owner
    tracker.set_active(owner)


def _wiring(L):
    po = L["pilin_out_controller"]
    am = L["aerial_manoover_controller"]
    return {
        "po_move": po.on_move_finished in L["movement_controller"].on_move_finished,
        "po_ingress": po.on_ingress_resolved in L["ingress_controller"].on_ingress_resolved,
        "po_disembark": po.on_disembark_resolved in L["transport_controller"].on_disembark_resolved,
        "po_objects": (po.transport_controller is L["transport_controller"]
                       and po.turn_tracker is L["turn_tracker"] and po.game_state is L["state"]),
        "po_ai": callable(po.choose),
        "am_ai": callable(am.choose),
        "dfa": getattr(L["shooting_controller"], "ingress_controller", None) is L["ingress_controller"],
    }


def _answer(decisions, needle):
    if not decisions.is_pending:
        return None
    for i, option in enumerate(decisions.options):
        if option["label"].startswith(needle):
            decisions.choose(i)
            return option["label"]
    return None


def _ring_slots(center, model_radius, ring_count=2):
    """Points around a hull, ring by ring, spaced a base apart."""
    slots = []
    ring = center.radius_in + model_radius + 0.15
    for _ in range(ring_count):
        steps = max(8, int(2 * math.pi * ring / (2 * model_radius + 0.1)))
        slots.append([(center.x_in + ring * math.cos(2 * math.pi * i / steps),
                       center.y_in + ring * math.sin(2 * math.pi * i / steps)) for i in range(steps)])
        ring += 2 * model_radius + 0.1
    return slots


def _clear_of(enemy_tokens, x, y, radius, gap):
    return all(math.hypot(x - e.x_in, y - e.y_in) - radius - e.radius_in > gap for e in enemy_tokens)


def _setup(L):
    """A Trukk within 8" of a Player 2 unit with its first disembark ring clear,
    the Boyz aboard, and Deffkoptas on the spot farthest from Player 2."""
    st, setup = L["state"], L["setup_controller"]
    enemies = [t for t in st.tokens if t.squad is not None and t.squad.owner == FOE and not t.is_dead()]
    movers = sorted({t.squad for t in enemies if _alive(t.squad)}, key=lambda s: s.name)
    trukk = build_squad(TRUKK, HUMAN, name="1 Trukk (staged)")
    boyz = build_squad(BOYZ, HUMAN, name="1 Boyz (staged)")
    kop = build_squad(DEFFKOPTAS, HUMAN, name="1 Deffkoptas (staged)")
    token = trukk.models[0]
    boy_r = boyz.models[0].radius_in
    found = None
    for mover in movers:
        for anchor in (m for m in mover.models if not m.is_dead() and m in st.tokens):
            for gap in (4.0, 5.5):
                for k in range(16):
                    ang = 2 * math.pi * k / 16
                    dist = anchor.radius_in + token.radius_in + gap
                    x, y = anchor.x_in + dist * math.cos(ang), anchor.y_in + dist * math.sin(ang)
                    if not setup.position_valid(token, x, y, squad=trukk):
                        continue
                    if not _clear_of(enemies, x, y, token.radius_in, 2.0):
                        continue
                    token.x_in, token.y_in = x, y
                    ring = _ring_slots(token, boy_r, ring_count=1)[0]
                    if all(setup.position_valid(boyz.models[0], sx, sy, squad=boyz)
                           and _clear_of(enemies, sx, sy, boy_r, ENGAGEMENT_IN + 0.3) for sx, sy in ring):
                        found = (mover, x, y)
                        break
                if found:
                    break
            if found:
                break
        if found:
            break
    if found is None:
        state["setup"] = {"error": "no clear spot for a Trukk within 8\" of a Player 2 unit"}
        return
    mover, token.x_in, token.y_in = found
    st.add_token(token)
    boyz.embarked_in = token
    st.embarked_squads.append(boyz)

    kr = kop.models[0].radius_in
    best = None
    for gx in range(3, int(setup.board_width_in) - 2, 2):
        for gy in range(3, int(setup.board_height_in) - 2, 2):
            row = [(gx + (i - 1) * (2 * kr + 0.3), float(gy)) for i in range(len(kop.models))]
            if not all(setup.position_valid(kop.models[0], px, py, squad=kop) for px, py in row):
                continue
            if any(math.hypot(px - token.x_in, py - token.y_in) < token.radius_in + kr + 6.0 for px, py in row):
                continue
            score = min(math.hypot(px - e.x_in, py - e.y_in) for px, py in row for e in enemies)
            if best is None or score > best[0]:
                best = (score, row)
    if best is None:
        state["setup"] = {"error": "no clear spot for the Deffkoptas"}
        return
    for model, (px, py) in zip(kop.models, best[1]):
        model.x_in, model.y_in = px, py
        st.add_token(model)
    state["setup"] = {"trukk": trukk, "boyz": boyz, "kop": kop, "mover": mover,
                      "gap": min(edge_distance(token, m) for m in mover.models if m in st.tokens),
                      "kop_clearance": best[0]}


def _stage_d(L):
    """Deff from Above on the live ShootingController, set and taken back here."""
    kop, mover = state["setup"]["kop"], state["setup"]["mover"]
    sc, ingress = L["shooting_controller"], L["ingress_controller"]
    weapon = next(w for w in kop.models[0].weapons if w.weapon_type == RANGED)
    group = {"pairs": [(m, weapon) for m in kop.models], "target_squad": mover}
    saved_active, saved_reactive = sc.active_squad, sc._reactive
    sc.active_squad, sc._reactive = kop, False
    try:
        plain = [m.amount for m in sc._hit_modifiers(group) if m.source == "Deff from Above"]
        ingress.ingressed_this_turn.add(kop)
        marked = [m.amount for m in sc._hit_modifiers(group) if m.source == "Deff from Above"]
    except Exception as exc:          # a probe must report, not crash the loop
        state["d"] = {"error": "_hit_modifiers raised %r" % exc}
        return
    finally:
        ingress.ingressed_this_turn.discard(kop)
        sc.active_squad, sc._reactive = saved_active, saved_reactive
    state["d"] = {"plain": plain, "marked": marked}


def _stage_b(L):
    boyz, mover, trukk = state["setup"]["boyz"], state["setup"]["mover"], state["setup"]["trukk"]
    _set_phase(PHASE_MOVEMENT, FOE)
    tc = L["transport_controller"]
    prompts_before = len(state["prompts"])
    raised = []
    for listener in list(L["movement_controller"].on_move_finished):
        try:
            listener(mover, "normal")
        except Exception as exc:     # another listener's precondition, not this probe's subject
            raised.append("listener %r raised %r" % (getattr(listener, "__name__", "?"), exc))
    asked = [p for p in state["prompts"][prompts_before:] if "Pilin' Out" in p["prompt"]]
    front = L["decision_manager"].prompt if L["decision_manager"].is_pending else None
    chosen = _answer(L["decision_manager"], "Disembark") if asked and "Pilin' Out" in (front or "") else None
    state["b"] = {"frame": state["frames"], "asked": asked, "chosen": chosen, "raised": raised,
                  "opened": (L["setup_controller"].state == PLACING, tc.disembark_mode, tc.is_disembarking(boyz)),
                  "held_frames": 0, "broke_hold": None, "trukk": trukk.name,
                  "foe_at": _foe_positions(L)}


def _foe_positions(L):
    return {id(t): (t.x_in, t.y_in) for t in L["state"].tokens
            if t.squad is not None and t.squad.owner == FOE}


def _lay_out(L, squad, token, away):
    tc = L["transport_controller"]
    placed = []
    radius = squad.models[0].radius_in
    rings = _ring_slots(token, radius, ring_count=3)
    order = [(ri, -math.hypot(x - away.x_in, y - away.y_in), x, y)
             for ri, ring in enumerate(rings) for x, y in ring]
    order.sort()
    for model in squad.models:
        spot = None
        for ri, _far, x, y in order:
            if math.hypot(x - token.x_in, y - token.y_in) - model.radius_in - token.radius_in > RAPID_IN:
                continue
            if any(math.hypot(x - px, y - py) < 2 * model.radius_in + 0.1 for px, py in placed):
                continue
            if not tc.position_valid(squad, model, x, y):
                continue
            spot = (x, y)
            break
        if spot is None:
            return False
        model.x_in, model.y_in = spot
        placed.append(spot)
    return True


def _watch_b(L):
    b = state["b"]
    boyz, trukk = state["setup"]["boyz"], state["setup"]["trukk"]
    tc, tracker = L["transport_controller"], state["tracker"]
    if not b["opened"][2]:
        b["done"] = True
        return
    still = tc.is_disembarking(boyz) and tracker.phase == PHASE_MOVEMENT and tracker.turn_owner == FOE
    if not still:
        b["broke_hold"] = state["frames"] - b["frame"]
        b["done"] = True
        return
    b["held_frames"] = state["frames"] - b["frame"]
    if b["held_frames"] < HOLD_FRAMES:
        return
    now = _foe_positions(L)
    b["foe_moved"] = sum(1 for k, xy in b["foe_at"].items() if now.get(k, xy) != xy)
    mover = state["setup"]["mover"]
    away = next(m for m in mover.models if not m.is_dead())
    b["laid_out"] = _lay_out(L, boyz, trukk.models[0], away)
    tc.confirm_disembark()
    b["errors"] = list(L["setup_controller"].errors) if L["setup_controller"].state == PLACING else []
    if L["setup_controller"].state == PLACING:
        tc.cancel_disembark()
    tokens = L["state"].tokens
    b["on_board"] = all(m in tokens for m in boyz.models)
    b["locked"] = bool(boyz.charge_locked_until_end_of_turn)
    b["from"] = boyz.disembarked_from_this_turn is trukk.models[0]
    b["current_after"] = L["pilin_out_controller"]._current
    b["done"] = True
    _stage_c(L)


def _stage_c(L):
    boyz = state["setup"]["boyz"]
    staged_lock = False
    if not boyz.charge_locked_until_end_of_turn:
        boyz.charge_locked_until_end_of_turn = True
        staged_lock = True
    prompts_before = len(state["prompts"])
    _set_phase(PHASE_FIGHT, FOE)
    tracker = state["tracker"]
    try:
        L["advance_turn_phase"]()
    except Exception as exc:
        state["c"] = {"error": "advance_turn_phase raised %r" % exc}
        return
    state["c"] = {"frame": state["frames"], "prompts_before": prompts_before, "staged_lock": staged_lock,
                  "owner_after": tracker.turn_owner, "lock_after": bool(boyz.charge_locked_until_end_of_turn),
                  "from_after": boyz.disembarked_from_this_turn, "answered": []}


def _watch_c(L):
    c = state["c"]
    kop = state["setup"]["kop"]
    decisions = L["decision_manager"]
    if decisions.is_pending and decisions.player == HUMAN and "Aerial Manoover" in (decisions.prompt or ""):
        needle = "Go into Strategic Reserves" if kop.name in decisions.prompt else "Stay on the battlefield"
        c["answered"].append((decisions.prompt[:50], _answer(decisions, needle)))
    asked = [p for p in state["prompts"][c["prompts_before"]:] if "Aerial Manoover" in p["prompt"]]
    in_reserves = kop in L["state"].reserves
    if in_reserves or state["frames"] - c["frame"] >= WAIT:
        c["done"] = True
        c["asked"] = asked
        c["in_reserves"] = in_reserves
        c["off_board"] = not any(m in L["state"].tokens for m in kop.models)


def flip(*args, **kwargs):
    state["frames"] += 1
    tracker = state["tracker"]
    if tracker is not None and getattr(tracker, "started", False):
        L = _main_locals()
        if L is not None and "pilin_out_controller" in L:
            if state["wiring"] is None:
                state["wiring"] = _wiring(L)
            _decline_stale_human_prompt(L.get("decision_manager"))
            if state["setup"] is None:
                if state["frames"] >= STAGE_AT and _quiet(L):
                    _setup(L)
            elif state["setup"].get("error"):
                raise SystemExit(0)
            elif state["d"] is None:
                _stage_d(L)
            elif state["b"] is None:
                if _quiet(L):
                    _stage_b(L)
            elif not state["b"].get("done"):
                _watch_b(L)
            elif state["c"] is None:
                _stage_c(L)
            elif not state["c"].get("done") and not state["c"].get("error"):
                _watch_c(L)
            else:
                raise SystemExit(0)
    return _real_flip(*args, **kwargs)


_real_flip = pygame.display.flip
pygame.display.flip = flip

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
s = state["setup"] or {}
b = state["b"] or {}
cc = state["c"] or {}
d = state["d"] or {}
print()
print("--- Ork vehicles, live" + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
print("  frames                                : %d" % state["frames"])
print("  A. Pilin' Out hears moves / arrivals / disembarks: %s / %s / %s" % (
    w.get("po_move"), w.get("po_ingress"), w.get("po_disembark")))
print("     ...holds main()'s transport controller, clock, state: %s" % w.get("po_objects"))
print("     AI policies injected (Pilin' Out / Aerial Manoover): %s / %s" % (w.get("po_ai"), w.get("am_ai")))
print("     ShootingController has main()'s IngressController: %s" % w.get("dfa"))
if s.get("error"):
    print("  SETUP ERROR " + s["error"])
else:
    print("  staged %s (Boyz aboard) %.2f\" from %s; Deffkoptas %.1f\" from Player 2" % (
        getattr(s.get("trukk"), "name", None), s.get("gap") or -1, getattr(s.get("mover"), "name", None),
        s.get("kop_clearance") or -1))
print("  D. Deff from Above modifiers (not ingressed / ingressed): %s / %s%s" % (
    d.get("plain"), d.get("marked"), (" ERROR " + d["error"]) if d.get("error") else ""))
print("  B. Pilin' Out prompts                 : %s" % ([(p["player"], p["labels"]) for p in b.get("asked") or []],))
print("     answered / placement (PLACING, mode, disembarking): %s / %s" % (b.get("chosen"), b.get("opened")))
print("     AI held for                        : %s frames%s; Player 2 models moved meanwhile: %s" % (
    b.get("held_frames"), "" if b.get("broke_hold") is None else " (hold BROKE after %s)" % b.get("broke_hold"),
    b.get("foe_moved")))
print("     laid out / confirm errors          : %s / %s" % (b.get("laid_out"), b.get("errors")))
print("     on board / charge locked / from the Trukk / resolved hook ran: %s / %s / %s / %s" % (
    b.get("on_board"), b.get("locked"), b.get("from"), "current_after" in b and b.get("current_after") is None))
if b.get("raised"):
    print("     other listeners raised             : %s" % b["raised"])
print("  C. turn owner after the advance       : %s%s" % (
    cc.get("owner_after"), (" ERROR " + cc["error"]) if cc.get("error") else ""))
print("     charge lock after (staged by hand: %s): %s; disembarked_from after: %s" % (
    cc.get("staged_lock"), cc.get("lock_after"), cc.get("from_after")))
print("     Aerial Manoover prompts            : %s" % ([(p["player"], p["prompt"][:40]) for p in cc.get("asked") or []],))
print("     answered                           : %s" % (cc.get("answered"),))
print("     staged Deffkoptas in reserves / off the board: %s / %s" % (cc.get("in_reserves"), cc.get("off_board")))
print("  stale Player 1 prompts declined       : %s" % (state["declined_other"] or "none"))

if not state["wiring"] or s.get("error") or d.get("error") or cc.get("error") or not cc.get("done"):
    print("  INCONCLUSIVE - the run never got through the staging")
    raise SystemExit(2)

if not NEUTRALIZE:
    checks = (
        ("Pilin' Out listens on the live move, arrival and disembark hooks",
         w.get("po_move") and w.get("po_ingress") and w.get("po_disembark")),
        ("...with main()'s transport controller, clock and state", w.get("po_objects") is True),
        ("both AI policies are injected (0 API calls)", w.get("po_ai") and w.get("am_ai")),
        ("the live ShootingController holds main()'s IngressController", w.get("dfa") is True),
        ("Deff from Above: +1 to hit only once the unit made an ingress move this turn",
         d.get("plain") == [] and d.get("marked") == [-1]),
        ("a Player 2 move ending within 8\" asks Player 1 about Pilin' Out",
         any(p["player"] == HUMAN for p in b.get("asked") or []) and b.get("chosen") is not None),
        ("...the answer opens a RAPID disembark placement", b.get("opened") == (True, RAPID, True)),
        ("...main()'s AI is held in its own Movement phase while it is open",
         b.get("broke_hold") is None and (b.get("held_frames") or 0) >= HOLD_FRAMES
         and b.get("foe_moved") == 0),
        ("...the placement confirms with no errors", b.get("errors") == [] and b.get("on_board") is True),
        ("...locks the charge, names the Trukk, and main()'s resolved hook ran",
         b.get("locked") is True and b.get("from") is True and "current_after" in b and b.get("current_after") is None),
        ("the end of Player 2's Fight phase asks Player 1 about Aerial Manoover",
         any(p["player"] == HUMAN and s["kop"].name in p["prompt"] for p in cc.get("asked") or [])),
        ("...the answer puts the Deffkoptas in Strategic Reserves",
         cc.get("in_reserves") is True and cc.get("off_board") is True),
        ("main()'s turn-end sweep ends the Pilin' Out charge lock with Player 2's turn",
         cc.get("owner_after") == HUMAN and cc.get("lock_after") is False and cc.get("from_after") is None),
    )
else:
    checks = (
        ("Pilin' Out does not listen", not (w.get("po_move") or w.get("po_ingress") or w.get("po_disembark"))),
        ("no Pilin' Out prompt, no placement", not b.get("asked") and not (b.get("opened") or (0, 0, False))[2]),
        ("no Aerial Manoover prompt", not cc.get("asked")),
        ("the Deffkoptas stay on the board", cc.get("in_reserves") is False),
        ("the charge lock set in Player 2's turn survives it", cc.get("lock_after") is True),
        ("no Deff from Above bonus", d.get("marked") == []),
    )
failed = 0
for label, ok in checks:
    print("  %s  %s" % ("PASS" if ok else "FAIL", label))
    failed += 0 if ok else 1
raise SystemExit(1 if failed else 0)
