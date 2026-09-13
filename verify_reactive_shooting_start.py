"""Does a reactive shooting activation OPEN, and SURVIVE, in the REAL main() loop?

User report, a crash out of main() (necrons_hypercrypt, the AI shooting a unit
next to the human's Hexmark Destroyer):

    reactive_bodyguard_shooting.py, on_squad_finished_shooting
        return self.shooting_controller.start_reactive_shooting(reactor, restrict_to=attacker)
    shooting.py, start_reactive_shooting
        self._restrict_targets_to = list(restrict_to) if restrict_to else None
    TypeError: 'Squad' object is not iterable

Two defects, the second behind the first: the start took only a LIST while
three callers pass the unit itself, and a reactive activation started from
inside the loop that closes the attacker's activation was wiped the instant it
opened. test_reactive_shooting_start.py pins both on the real controller. This
asks the controller main() actually built, in the loop that crashed, and then
asks the two things only the loop can answer: does the AI WAIT for the human's
activation instead of playing through it, and does a REAL board click take the
target.

WHAT IS STAGED, and why each - named rather than quietly faked:
  * necrons_hypercrypt AS PLAYER 1: the one shipped list that fields a Hexmark
    Destroyer, and in the report the reactor was the human's.
  * THE MOMENT. A MockAgent run does not reliably make an AI unit shoot a unit
    standing within 3" of the human's Hexmark inside a fixed frame budget, so a
    passive counter would report zero and read like a pass. So at OPEN_AT this
    reaches into main()'s frame, stands a friendly unit next to the Hexmark and
    an AI unit where it is a LEGAL TARGET for the Hexmark - line of sight
    checked independently (game/line_of_sight.py) AND the live controller's
    has_valid_target() asked BEFORE any activation opens, so the restriction
    under test is not set yet and cannot be what answers. Line of sight alone
    was this probe's first stage, and the board then offered no target at all,
    so the real click had nothing to take - opens the AI
    unit's activation on the LIVE controller, raises the human's Multi-threat
    Eliminator prompt through the live controller's own maybe_offer() and
    answers "Shoot back" through the live DecisionManager, then closes the AI
    unit's activation through _actually_finish_squad() - the frame the
    traceback died in.
  * THE HUMAN'S STOP. selfplay clicks no left-panel weapon button for a human,
    so after the real click takes the target the activation is ended through
    the live controller's cancel(), standing in for the stop button.
Everything else is real: main()'s event chain for the click, the AI's gate,
the frames in between.

Usage:  python verify_reactive_shooting_start.py [map2] [frames]
        --neutralize        the shipped start: list(restrict_to), opened inside
                            the loop. MUST report the crash.
        --neutralize-wipe   only the list half fixed: MUST report the Hexmark's
                            activation wiped the instant it opened.
"""

import os
import runpy
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame                                   # noqa: E402

NEUTRALIZE = "--neutralize" in sys.argv
NEUTRALIZE_WIPE = "--neutralize-wipe" in sys.argv
_args = [a for a in sys.argv[1:] if not a.startswith("--")]
MAP = next((a for a in _args if a.startswith("map")), "map2")
FRAMES = next((int(a) for a in _args if a.isdigit()), 1800)
OPEN_AT = 800
WAIT_FRAMES = 240
HUMAN, AI = "Player 1", "Player 2"

from game import config, line_of_sight, weapon_range      # noqa: E402
from game import shooting as shooting_mod                # noqa: E402
from game.turn import PHASES, PHASE_SHOOTING             # noqa: E402
from game.weapons import RANGED                          # noqa: E402

config.PLAYER1_ARMY = "necrons_hypercrypt"
config.PLAYER2_ARMY = "necrons"
config.ARMY_SELECT = False
config.MAP_SELECT = False
config.MAP = MAP

R = {"frames": 0, "staged_at": None, "error": None, "crash": None,
     "held": 0, "ai_activations_while_open": 0, "clicked_at": None,
     "target_taken": None, "ai_resumed_at": None}
L = {}


def name_of(squad):
    return getattr(squad, "name", None)


def _living(squad):
    return [m for m in getattr(squad, "models", ()) or () if not m.is_dead()]


def _on_board(squad, tokens):
    ids = {id(t) for t in tokens}
    return bool(_living(squad)) and all(id(m) in ids for m in _living(squad))


def _move(squad, x_in, y_in):
    for i, model in enumerate(squad.models):
        model.x_in, model.y_in = x_in + i * 1.4, y_in


def _squads(state):
    seen = []
    for token in state.tokens:
        squad = getattr(token, "squad", None)
        if squad is not None and squad not in seen:
            seen.append(squad)
    return sorted(seen, key=lambda s: s.name)


# --- the two pre-fix worlds, on the LIVE controller ------------------------
def _neutralize(sc, list_half_fixed):
    real = sc.start_reactive_shooting

    def shipped(squad, restrict_to=None, on_finished=None):
        if list_half_fixed:
            restrict = ([restrict_to] if hasattr(restrict_to, "models")
                        else (list(restrict_to) if restrict_to else None))
        else:
            restrict = list(restrict_to) if restrict_to else None   # the shipped line
        saved = sc._closing_activation
        sc._closing_activation = False                               # opened in the loop
        try:
            return real(squad, restrict_to=restrict, on_finished=on_finished)
        finally:
            sc._closing_activation = saved

    sc.start_reactive_shooting = shipped


# --- the click -------------------------------------------------------------
def screen_pos_of(model):
    """The pixel a human clicks to pick `model` - the inverse of
    input_handler.token_at_event() (verify_necron_wraith_form.py's)."""
    handler, board = L.get("input_manager"), L.get("board")
    if handler is None or board is None:
        return None
    nx, ny = board.to_px(model.x_in, model.y_in)
    camera = getattr(handler, "camera", None)
    if camera is not None:
        vis, dest = camera.visible_rect(), camera.dest_rect()
        local = (dest.x + (nx - vis.x) / vis.width * dest.width,
                 dest.y + (ny - vis.y) / vis.height * dest.height)
    else:
        local = (nx, ny)
    off = getattr(handler, "board_offset", (0, 0))
    return (int(local[0] + off[0]), int(local[1] + off[1]))


_pump = {"real": None, "events": None}


def _install_pump():
    """selfplay REPLACES pygame.event.get at import; installed from the frame
    hook, once its pump is in place."""
    if _pump["real"] is None:
        _pump["real"] = pygame.event.get
        pygame.event.get = _event_get


def _event_get(*args, **kwargs):
    events = list(_pump["real"](*args, **kwargs))
    if R["staged_at"] is None or R["ai_resumed_at"] is not None:
        return events
    if _pump["events"] is not None:
        out, _pump["events"] = _pump["events"], None
        return out
    # REPLACED, not added to, while the human's activation is open: selfplay
    # clicks the board every frame, and a click landing on a model would take
    # the target for the wrong reason.
    if R["target_taken"] is None:
        return []
    return events


# --- staging ---------------------------------------------------------------
def _stage():
    sc = L["shooting_controller"]
    mte = L["multi_threat_eliminator_controller"]
    dm, tt, state = L["decision_manager"], L["turn_tracker"], L["state"]
    tokens = state.tokens
    squads = _squads(state)

    hexmark = next((s for s in squads if s.owner == HUMAN and mte.carries(s)
                    and _on_board(s, tokens)), None)
    if hexmark is None:
        where = [s.name for s in state.all_squads() if s.owner == HUMAN and mte.carries(s)]
        return "no Hexmark of the human's on the board (carriers anywhere: %s)" % where
    friend = next((s for s in squads if s.owner == HUMAN and s is not hexmark
                   and mte.protects(s) and _on_board(s, tokens)), None)
    shooter = next((s for s in squads if s.owner == AI and _on_board(s, tokens)
                    and any(w.weapon_type == RANGED for m in s.models for w in m.weapons)),
                   None)
    if friend is None or shooter is None:
        return "no friendly NECRONS unit or no armed AI unit on the board"

    hm = hexmark.models[0]
    hx, hy = hm.x_in, hm.y_in
    _move(friend, hx + hm.radius_in + friend.models[0].radius_in + 1.0, hy)

    # No activation may be open while the stage asks its questions: a
    # restriction left over from one would answer them.
    sc.cancel()
    types = shooting_mod.available_shooting_types(hexmark, tokens, sc.movement_controller)
    R["reactor_types"] = types
    if not types:
        return ("the Hexmark has no shooting type open on this board (engaged=%s)"
                % hexmark.is_engaged(tokens))

    reach = max(weapon_range.effective_range_in(hm, w) for w in hm.weapons
                if w.weapon_type == RANGED)
    cx = sum(t.x_in for t in tokens) / len(tokens)
    cy = sum(t.y_in for t in tokens) / len(tokens)
    directions = sorted(((0, 1), (0, -1), (1, 0), (-1, 0), (0.7, 0.7), (-0.7, 0.7),
                         (0.7, -0.7), (-0.7, -0.7)),
                        key=lambda d: -((cx - hx) * d[0] + (cy - hy) * d[1]))
    tried = []
    placed = False
    for gap in (6.0, 9.0, 3.5, 12.0):
        if gap > reach - 0.5:
            continue
        for dx, dy in directions:
            d = hm.radius_in + shooter.models[0].radius_in + gap
            _move(shooter, hx + dx * d, hy + dy * d)
            los = any(line_of_sight.has_line_of_sight(hm, sm, state.obstacles, tokens,
                                                      state.terrain_areas)
                      for sm in shooter.models)
            legal = sc.has_valid_target(
                hexmark, types[0], tokens,
                target_filter=lambda t: getattr(t, "squad", t) is shooter)
            tried.append((gap, (dx, dy), los, legal, shooter.is_engaged(tokens)))
            if los and legal:
                placed = True
                break
        if placed:
            break
    if not placed:
        return ("no placement where the AI unit is a legal target for the Hexmark "
                "(reach %.1f, types %s; tried gap/dir/LoS/legal/engaged: %s)"
                % (reach, types, tried[:6]))

    R.update(hexmark=hexmark.name, friend=friend.name, shooter=shooter.name)
    L.update(hexmark=hexmark, shooter=shooter)

    # A standing prompt first: "Shoot back" has to be the one answered.
    for _ in range(20):
        if not dm.is_pending:
            break
        dm.choose(len(dm.options) - 1)

    tt.phase_index = PHASES.index(PHASE_SHOOTING)
    tt.turn_owner = AI
    tt.set_active(AI)
    sc.cancel()
    sc.start_shooting(shooter)
    R["shooter_opened_for_real"] = sc.active_squad is shooter
    if sc.active_squad is not shooter:
        # can_shoot() refuses a unit that has shot this phase already; the
        # funnel under test does not care how the activation began.
        sc.active_squad, sc._reactive = shooter, False

    if not mte.maybe_offer(shooter, friend) or not dm.is_pending:
        return "the Multi-threat Eliminator prompt was not raised"
    labels = [o["label"] for o in dm.options]
    R["prompt_options"] = labels
    idx = next((i for i, label in enumerate(labels) if label.startswith("Shoot back")), None)
    if idx is None:
        return "no 'Shoot back' option: %s" % labels
    dm.choose(idx)
    R["owed"] = mte._owed is not None

    if NEUTRALIZE or NEUTRALIZE_WIPE:
        _neutralize(sc, list_half_fixed=NEUTRALIZE_WIPE)
    try:
        sc._actually_finish_squad()          # the frame the traceback died in
    except Exception as exc:                 # noqa: BLE001 - reported below
        R["crash"] = "%s: %s" % (type(exc).__name__, exc)

    R["after"] = (name_of(sc.active_squad), sc.state,
                  [name_of(s) for s in (sc._restrict_targets_to or [])])
    try:
        R["offered"] = sorted({t.squad.name for t in sc.valid_target_models(tokens)
                               if t.squad is not None})
    except Exception as exc:                 # noqa: BLE001
        R["offered"] = ["<%s>" % exc]
    return None


def _main_locals(frame):
    while frame is not None and frame.f_code.co_name != "main":
        frame = frame.f_back
    return None if frame is None else frame.f_locals


_real_flip = pygame.display.flip


def flip(*args, **kwargs):
    _install_pump()
    R["frames"] += 1
    frame_no = R["frames"]

    if not L:
        found = _main_locals(sys._getframe(1))
        if found is not None and "shooting_controller" in found:
            for key in ("shooting_controller", "multi_threat_eliminator_controller",
                        "decision_manager", "dice_manager", "turn_tracker", "state",
                        "input_manager", "board"):
                if key in found:
                    L[key] = found[key]

    if L and R["staged_at"] is None and R["error"] is None and frame_no >= OPEN_AT:
        tt = L["turn_tracker"]
        if getattr(tt, "started", False) and not L["dice_manager"].is_pending:
            R["error"] = _stage()
            R["staged_at"] = frame_no

    if R["staged_at"] is not None and R["error"] is None and R["crash"] is None:
        sc = L["shooting_controller"]
        since = frame_no - R["staged_at"]
        if R["target_taken"] is None:
            if 0 < since <= WAIT_FRAMES:
                if sc.active_squad is L["hexmark"]:
                    R["held"] += 1
                if sc.active_squad is not None and sc.active_squad.owner == AI:
                    R["ai_activations_while_open"] += 1
            if since == WAIT_FRAMES and sc.active_squad is L["hexmark"]:
                pos = screen_pos_of(L["shooter"].models[0])
                if pos is not None:
                    _pump["events"] = [
                        pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": 1}),
                        pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": pos, "button": 1})]
                    R["clicked_at"] = frame_no
            if R["clicked_at"] is not None and frame_no >= R["clicked_at"] + 2:
                R["target_taken"] = sc.target_squad is L["shooter"]
                sc.cancel()                  # the human's stop - see the docstring
                R["after_stop"] = name_of(sc.active_squad)
        elif R["ai_resumed_at"] is None:
            tt = L["turn_tracker"]
            if ((sc.active_squad is not None and sc.active_squad.owner == AI)
                    or tt.phase != PHASE_SHOOTING or tt.turn_owner != AI):
                R["ai_resumed_at"] = frame_no

    return _real_flip(*args, **kwargs)


pygame.display.flip = flip
sys.argv = ["selfplay.py", MAP, str(FRAMES)]
try:
    runpy.run_module("selfplay", run_name="__main__")
except SystemExit:
    pass
finally:
    pygame.display.flip = _real_flip

mode = ("NEUTRALIZED (shipped)" if NEUTRALIZE
        else "NEUTRALIZED (list half fixed only)" if NEUTRALIZE_WIPE else "fixed")
print("\n" + "=" * 74)
print("reactive shooting start -", mode)
print("=" * 74)
if R["staged_at"] is None:
    print("INCONCLUSIVE: never staged (frames=%d)" % R["frames"])
    sys.exit(1)
if R["error"]:
    print("INCONCLUSIVE:", R["error"])
    sys.exit(1)

print("reactor / friend / AI shooter   : %s / %s / %s" % (R["hexmark"], R["friend"], R["shooter"]))
print("AI activation opened for real   : %s" % R["shooter_opened_for_real"])
print("prompt options                  : %s" % R["prompt_options"])
print("reaction owed after 'Shoot back': %s" % R["owed"])
print("CRASH closing the AI activation : %s" % R["crash"])
print("controller afterwards           : %s" % (R["after"],))
print("board offers as targets         : %s" % R.get("offered"))
print("frames the Hexmark held it      : %d of %d" % (R["held"], WAIT_FRAMES))
print("AI activations while it was open: %d" % R["ai_activations_while_open"])
print("real click on the AI unit takes : %s (clicked at frame %s)"
      % (R["target_taken"], R["clicked_at"]))
print("AI resumed after the stop       : frame %s" % R["ai_resumed_at"])

if NEUTRALIZE:
    ok = R["crash"] is not None and "not iterable" in R["crash"]
    print("\n" + ("PASS - reproduced: the reported TypeError" if ok else "FAIL - not reproduced"))
elif NEUTRALIZE_WIPE:
    ok = R["crash"] is None and R["after"][0] is None
    print("\n" + ("PASS - reproduced: the Hexmark's activation was wiped as it opened"
                  if ok else "FAIL - the wipe was not reproduced"))
else:
    ok = (R["crash"] is None and R["after"] == (R["hexmark"], shooting_mod.CHOOSING_TARGET,
                                                  [R["shooter"]])
          and R.get("offered") == [R["shooter"]]
          and R["held"] == WAIT_FRAMES and R["ai_activations_while_open"] == 0
          and R["target_taken"] is True and R["ai_resumed_at"] is not None)
    print("\n" + ("PASS" if ok else "FAIL"))
sys.exit(0 if ok else 1)
