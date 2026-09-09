"""Picking a unit ON THE BATTLEFIELD through main()'s REAL loop.

User: "Immer wenn man eine einheit auf dem schlachtfeld waehlen muss (zb wall
of mirrors) will ich die einheit nicht aus einer liste waehlen, sondern auf dem
schlachtfeld. Wie bei overwatch."

WHY A SMOKE AND NOT ONLY A SUITE. test_unit_pick.py proves each link on its own
- game/unit_pick.py decides, the panel draws the screen, the renderer draws the
rings, main.py contains the branch (source guard). What no suite can reach is
the CHAIN: that a REAL click on a REAL board pixel, in a REAL frame, resolves
the decision. This repo has been bitten six times by something built,
unit-tested and never fed, and here that failure mode is not a silent no-op but
a HARD DEADLOCK - a decision that blocks the game and cannot be answered
(CLAUDE.md's Fehlerklasse 25).

IT STAGES THE DECISION ITSELF, deliberately. Every prompt of this kind is
reactive - Wall of Mirrors wants the end of the opponent's Fight phase with a
STEALTH unit out of Engagement Range, Isha's Fury wants an enemy Advance - and
a MockAgent run does not reliably reach one (the documented harness limit). A
passive counter would have reported 0 and looked exactly like a pass. So ONE
decision is enqueued on the REAL DecisionManager main() built, tagged with a
REAL unit standing on the REAL board. Everything after that is the game:
main()'s own chain, its own panel, its own renderer.

--neutralize restores the pre-fix world at the one place that decides it - the
option keeps its label and its callback and loses only its unit, which is what
all ~56 call sites looked like before - and MUST fail.

Uses MockAgent - no API calls.

Run: python smoke_unit_pick.py [map] [--neutralize]
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

args = [a for a in sys.argv[1:] if not a.startswith("--")]
NEUTRALIZE = "--neutralize" in sys.argv
MAP_KEY = args[0] if args else "map2"
MAX_FRAMES = 6000

pygame.init()

from game import config  # noqa: E402

state = {"frames": 0, "armed": False, "stage": "settle", "rec": {}, "error": None,
         "staged": None, "panel_screens": 0, "ringed": [], "overlay_painted": None,
         "resolved": False, "rule_name": None, "rule_drawn": None}


def _main_locals():
    frame = sys._getframe(2)
    while frame is not None:
        if "turn_tracker" in frame.f_locals:
            return frame.f_locals
        frame = frame.f_back
    return {}


def _press(pos, button=1):
    return [pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": button})]


def _release(pos, button=1):
    return [pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": pos, "button": button})]


def _click(pos):
    return _press(pos) + _release(pos)


def _drive_pregame(loc):
    """Get to battle round 1 - the same short way smoke_selection.py does. Only
    the waiting rooms that belong to the HUMAN; Player 2's own side of rule
    03.01 is driven by main()'s auto-play."""
    for name in ("turn_start_overlay", "turn_plan_overlay",
                 "stratagem_notice_overlay", "waaagh_notice_overlay"):
        overlay = loc.get(name)
        if overlay is not None and getattr(overlay, "is_pending", False):
            return _click((10, 10))

    dice_manager = loc.get("dice_manager")
    if dice_manager is not None and dice_manager.is_pending:
        surface = pygame.display.get_surface()
        w, h = surface.get_size() if surface else (1200, 800)
        return _click((w - 8, h - 8))

    pregame_ctrl = loc.get("pregame_controller")
    if pregame_ctrl is None or not getattr(pregame_ctrl, "is_active", False):
        return None

    decisions = loc.get("decision_manager")
    if decisions is not None and decisions.is_pending:
        decisions.choose(0)
        return []
    if (pregame_ctrl.state == "deploying"
            and pregame_ctrl.active_player == pregame_ctrl.human_player
            and pregame_ctrl.selected_unit is None):
        pending = pregame_ctrl.pending_units(pregame_ctrl.human_player)
        if pending:
            pregame_ctrl.select_unit(pending[0])
            return []
    buttons = getattr(loc.get("action_panel"), "_buttons", [])
    if buttons:
        return _click(buttons[0][0].center)
    return []


def _clear_the_way(loc):
    """Events that dismiss whatever modal owns the board's clicks right now, or
    None once nothing does. Battle round 1 opens with the turn-start banner up,
    and the first gesture would otherwise be spent on it."""
    for name in ("turn_start_overlay", "turn_plan_overlay", "mission_draw_overlay",
                 "stratagem_notice_overlay", "waaagh_notice_overlay",
                 "fight_warning_overlay"):
        overlay = loc.get(name)
        if overlay is not None and getattr(overlay, "is_pending", False):
            return _click((10, 10))
    dice_manager = loc.get("dice_manager")
    if dice_manager is not None and dice_manager.is_pending:
        surface = pygame.display.get_surface()
        w, h = surface.get_size() if surface else (1200, 800)
        return _click((w - 8, h - 8))
    return None


def _pixel_over(loc, squad):
    """A screen pixel over one of `squad`'s models, found by asking main()'s
    OWN input_manager - the same screen -> camera -> board -> inches mapping
    the click under test will go through. A re-derivation here could agree with
    itself while both were wrong."""
    im = loc["input_manager"]
    board = loc["board"]
    rect = loc["board_rect_screen"]
    tokens = loc["state"].tokens
    for gy in range(2, 100):
        for gx in range(2, 100):
            pos = (rect.x + rect.width * gx // 100, rect.y + rect.height * gy // 100)
            hit = im.token_at_event(tokens, board, pos)
            if hit is not None and hit.squad is squad:
                return pos
    return None


def _stageable_unit(loc):
    """A living, multi-model unit of the player whose turn it is, standing on
    the board. Multi-model so "the rings landed on the right unit" is a claim
    with a number behind it."""
    owner = loc["turn_tracker"].turn_owner
    seen = []
    for token in loc["state"].tokens:
        squad = getattr(token, "squad", None)
        if squad is None or squad in seen:
            continue
        seen.append(squad)
        if squad.owner != owner or len(squad.models) < 3:
            continue
        if all(model.is_dead() for model in squad.models):
            continue
        return squad
    return None


def fake_events():
    state["frames"] += 1
    if state["frames"] >= MAX_FRAMES:
        state["error"] = f"never finished within {MAX_FRAMES} frames (stage {state['stage']})"
        raise SystemExit(0)
    loc = _main_locals()
    if not loc:
        return []

    if not state["armed"]:
        state["armed"] = True
        return [pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_a, "mod": pygame.KMOD_LSHIFT,
                                                    "unicode": "A", "scancode": 4})]

    rec = state["rec"]
    stage = state["stage"]

    if stage == "settle":
        if not loc["turn_tracker"].started:
            pending = _drive_pregame(loc)
            return pending if pending is not None else []
        clearing = _clear_the_way(loc)
        if clearing is not None:
            return clearing
        # Auto-play off from here: the AI advancing phases underneath would
        # move the units this smoke is about to aim at.
        loc_ai = loc.get("ai_auto_play")
        if loc_ai:
            state["stage"] = "stage_it"
            return [pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_a, "mod": pygame.KMOD_LSHIFT,
                                                        "unicode": "A", "scancode": 4})]
        state["stage"] = "stage_it"
        return []

    if stage == "stage_it":
        decisions = loc.get("decision_manager")
        if decisions is None or decisions.is_pending:
            return []
        squad = _stageable_unit(loc)
        if squad is None:
            state["error"] = "no multi-model unit on the board to stage a decision with"
            raise SystemExit(0)

        def taken():
            state["resolved"] = True

        # The prompt NAMES a printed rule of the staged unit, because that is
        # the shape every real one has ("{squad.name}: Living Lightning -
        # strike which unit?") and it is what game/prompt_rule.py reads back
        # out. A staged prompt naming no rule would leave the right panel
        # correctly empty and prove nothing about it.
        rule_name = _printed_rule_of(squad)
        state["rule_name"] = rule_name
        prompt = (f"{squad.name}: {rule_name} - which unit?" if rule_name
                  else "STAGED: which unit?")
        options = [(squad.name, taken, squad), ("Decline", lambda: None)]
        if NEUTRALIZE:
            # The pre-fix world at the ONE place that decides it: the option
            # keeps its label and callback and loses only its unit.
            options = [tuple(option[:2]) for option in options]
        decisions.request(squad.owner, prompt, options,
                          subject="Smoke Objective")
        state["staged"] = (squad.name, len([m for m in squad.models if not m.is_dead()]))
        state["stage"] = "look"
        return []

    if stage == "look":
        # One frame of drawing has to happen before anything is asserted about
        # what was drawn.
        if state["frames"] < 3 + rec.get("staged_frame", 0):
            rec.setdefault("staged_frame", state["frames"])
        rec["pick_seen"] = _pick_of(loc) is not None
        rec["overlay_painted"] = state["overlay_painted"]
        rec["panel_screens"] = state["panel_screens"]
        rec["ringed"] = list(state["ringed"])
        rec["rule_drawn"] = state["rule_drawn"]
        state["stage"] = "click"
        return []

    if stage == "click":
        squad = _squad_named(loc, state["staged"][0])
        pos = _pixel_over(loc, squad) if squad is not None else None
        if pos is None:
            state["error"] = "could not find a screen pixel over the staged unit"
            raise SystemExit(0)
        state["stage"] = "done"
        return _click(pos)

    if stage == "done":
        rec["resolved"] = state["resolved"]
        rec["still_pending"] = loc["decision_manager"].is_pending
        rec["still_running"] = True
        raise SystemExit(0)
    return []


def _printed_rule_of(squad):
    """A printed ability NAME this unit really has, or None.

    Read from the corpus rather than written down here: a hard-coded name would
    quietly stop matching the moment a datasheet is re-scraped, and the smoke
    would pass while measuring nothing."""
    from game import prompt_rule
    from game import rules_text
    for sheet in prompt_rule._datasheets([squad]):
        for ability in rules_text.abilities_for(sheet):
            if ability.title and rules_text.ability_blocks(sheet, ability.title):
                return ability.title
    return None


def _pick_of(loc):
    from game import unit_pick
    return unit_pick.pending(loc["decision_manager"], loc["state"].tokens)


def _squad_named(loc, name):
    for token in loc["state"].tokens:
        squad = getattr(token, "squad", None)
        if squad is not None and squad.name == name:
            return squad
    return None


pygame.event.get = lambda *a, **k: fake_events()

# The two pre-game SCREENS run their own event loops, and their frames have no
# turn_tracker - without this the pump is drained by the map picker and main()
# is never reached at all. (Cost one debugging round: the harness reported 6000
# frames and an empty locals dict.)
config.ARMY_SELECT = False
config.MAP_SELECT = False
# This harness answers no prompt that belongs to the human outside the pre-game
# and the one it stages itself - the same reason every other smoke turns the
# deck off, and there is a source guard in test_secondary_missions.py for it.
config.SECONDARY_MISSION_CARD_PLAYERS = ()

from game.renderer import Renderer  # noqa: E402
from game.ui.action_panel import ActionPanel  # noqa: E402
from game.ui.decision_overlay import DecisionOverlay  # noqa: E402

import main  # noqa: E402
from ai.mock_agent import MockAgent  # noqa: E402

main.ClaudeAgent = lambda *a, **k: MockAgent()   # 0 API calls

# --- spies: what main() really handed each reader on a real frame ------------
_real_pick_ui = ActionPanel._draw_unit_pick_ui


def _spy_pick_ui(self, surface, rect, pick, **kwargs):
    if state["staged"] is not None:
        state["panel_screens"] += 1
    return _real_pick_ui(self, surface, rect, pick, **kwargs)


ActionPanel._draw_unit_pick_ui = _spy_pick_ui

_real_targets = Renderer.draw_shoot_targets


def _spy_targets(self, surface, board, targets):
    if state["staged"] is not None and targets:
        names = {t.squad.name for t in targets if getattr(t, "squad", None) is not None}
        if state["staged"][0] in names:
            state["ringed"] = [t for t in targets
                               if getattr(t, "squad", None) is not None
                               and t.squad.name == state["staged"][0]]
    return _real_targets(self, surface, board, targets)


Renderer.draw_shoot_targets = _spy_targets

_real_overlay = DecisionOverlay.draw


def _spy_overlay(self, surface, decision_manager, squads=(), board_pick=False):
    if state["staged"] is not None and decision_manager.is_pending:
        middle = (surface.get_width() // 2, surface.get_height() // 2)
        before = surface.get_at(middle)
        result = _real_overlay(self, surface, decision_manager, squads, board_pick=board_pick)
        state["overlay_painted"] = surface.get_at(middle) != before
        return result
    return _real_overlay(self, surface, decision_manager, squads, board_pick=board_pick)


DecisionOverlay.draw = _spy_overlay

# The RIGHT panel: what main() actually handed it on a real frame. A source
# guard shows the call is written down; only a spy shows it arrives.
# The rule box moved to the LEFT panel, where the question already is
# (user: "'why you are choosing' soll in die linke spalte, nicht rechts").
from game.ui.action_panel import ActionPanel  # noqa: E402

_real_rule = ActionPanel._draw_decision_rule


def _spy_rule(self, surface, rect, y, decision_rule):
    if state["staged"] is not None and decision_rule:
        state["rule_drawn"] = decision_rule.name
    return _real_rule(self, surface, rect, y, decision_rule)


ActionPanel._draw_decision_rule = _spy_rule

try:
    main.main(MAP_KEY)
except SystemExit:
    pass

print(f"\nunit pick smoke ({MAP_KEY}), {state['frames']} frames"
      + ("   [NEUTRALIZED - expected to fail]" if NEUTRALIZE else ""))
failures = []


def check(label, condition, detail=""):
    print(f"  {'PASS' if condition else 'FAIL'}  {label}{'   ' + detail if detail else ''}")
    if not condition:
        failures.append(label)


rec = state["rec"]
if state["error"]:
    check(state["error"], False)
else:
    name, alive = state["staged"]
    print(f"  staged: {name} ({alive} living models) + Decline")
    check("the decision is recognised as a BOARD pick", rec.get("pick_seen") is True)
    check("the left panel really draws the pick screen",
          rec.get("panel_screens", 0) > 0, str(rec.get("panel_screens")))
    check("the board really gets rings on that unit",
          len(rec.get("ringed", [])) == alive,
          f"{len(rec.get('ringed', []))} of {alive}")
    check("the LEFT panel is handed the printed rule the prompt names",
          rec.get("rule_drawn") == state["rule_name"] and state["rule_name"] is not None,
          f"{rec.get('rule_drawn')!r} vs prompt's {state['rule_name']!r}")
    check("the modal overlay does NOT cover the board",
          rec.get("overlay_painted") is False, str(rec.get("overlay_painted")))
    # Sentinel, not .get(None): an absent key would otherwise read as a pass
    # precisely when the run fell over before clicking.
    check("a REAL click on the unit resolves the decision",
          rec.get("resolved", "<never reached>") is True, str(rec.get("resolved")))
    check("...and the decision is gone", rec.get("still_pending", True) is False)

print(f"\n{'OK' if not failures else 'FAILED: ' + ', '.join(f.strip() for f in failures)}")
sys.exit(1 if failures else 0)
