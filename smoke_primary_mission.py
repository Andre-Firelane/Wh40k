"""The Force Disposition Primary Mission, through main()'s REAL loop.

test_primary_missions.py proves every scoring box in isolation and reads
main.py as text. Neither can prove the wiring actually runs: three of the four
seams this feature hangs on are inside main()'s advance_turn_phase() and
_check_battle_end(), no suite drives main(), and this repo has SIX recorded
cases of a controller that was built, unit-tested, and never fed.

So this drives the real loop with real board state and reads only what main()'s
own live objects say afterwards. Three stages, one per seam:

  A  END OF CMD PHASE  - hold a non-home objective in round 2, cross the
                         Command-phase boundary, and the shared Primary ledger
                         has to move. Also: Hold the Line must NOT pay the
                         same player, because the disposition Primary replaces
                         it.
  B  END OF BATTLE     - switch the list's disposition to Purge the Foe (the
                         one dormant mission with a FINAL SCORING box, one line
                         from live), stand on the central objective, end the
                         battle, and the result overlay has to show the 5 VP.
  C  THE PANEL         - switch to Disruption and check the left panel really
                         draws a Booby Trap button for a unit standing in a
                         terrain area. The action framework is shared, so the
                         button is the only part that is new wiring.

Stage B also exercises something worth having: the mission is read from the
army list on EVERY access, so changing the list's declared disposition mid-run
really changes the mission.

A/B: run with `--neutralize` to put the pre-feature world back (nobody plays a
disposition Primary). That must FAIL.

Usage:  python smoke_primary_mission.py [map_key] [--neutralize]
Uses MockAgent - no API calls.
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

args = [a for a in sys.argv[1:] if not a.startswith("--")]
NEUTRALIZE = "--neutralize" in sys.argv
MAP_KEY = args[0] if args else "map2"
MAX_FRAMES = 12000

pygame.init()

from game import army_lists, force_dispositions as fd  # noqa: E402
from game import mission_context as mc  # noqa: E402
from game import primary_missions as pm  # noqa: E402
from game.missions import BATTLE_ROUNDS  # noqa: E402
from game.turn import PHASES, PHASE_COMMAND, PHASE_SHOOTING  # noqa: E402

HUMAN = "Player 1"
AI = "Player 2"

state = {"frames": 0, "stage": "auto_on", "error": None, "rec": {}, "settle": 0}


def _main_locals():
    frame = sys._getframe(2)
    while frame is not None:
        if "turn_tracker" in frame.f_locals:
            return frame.f_locals
        frame = frame.f_back
    return {}


def _click(pos):
    return [pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": 1}),
            pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": pos, "button": 1})]


def _shift_a():
    return [pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_a, "mod": pygame.KMOD_LSHIFT,
                                                "unicode": "A", "scancode": 4})]


def _drive_pregame(loc):
    """Get to battle round 1 - the human's waiting rooms only; main()'s own
    auto-play drives Player 2's side of rule 03.01. Same shape as
    smoke_end_turn_warning.py's own copy."""
    for name in ("fight_warning_overlay", "turn_start_overlay", "turn_plan_overlay",
                 "mission_draw_overlay", "stratagem_notice_overlay",
                 "waaagh_notice_overlay"):
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


def _clear_blockers(loc):
    notice = loc["_front_notice"]()
    if notice is not None:
        return _click((10, 10))
    if loc["decision_manager"].is_pending:
        loc["decision_manager"].choose(0)
        return []
    if loc["dice_manager"].is_pending:
        surface = pygame.display.get_surface()
        w, h = surface.get_size() if surface else (1200, 800)
        return _click((w - 8, h - 8))
    return None


def _squads_on_board(loc, owner):
    seen = {}
    for token in loc["state"].tokens:
        if token.squad is not None and token.squad.owner == owner:
            seen.setdefault(id(token.squad), token.squad)
    return list(seen.values())


def _ctx(loc):
    st = loc["state"]
    return mc.MissionContext(HUMAN, tokens=st.tokens, objectives=st.objectives,
                             deployment_zones=st.deployment_zones,
                             terrain_areas=st.terrain_areas)


def _park_on(loc, objective, owner=HUMAN):
    """Move one small unit of `owner` onto an objective, rigidly and tightly,
    and clear everyone else off it.

    RIGID and tight because 14.02 counts OC of models inside the footprint and
    09.02 coherency is checked at phase boundaries - a scattered unit would
    fail to control the objective, or block the boundary, and this smoke would
    report the wiring broken when the staging was."""
    cx, cy = mc.objective_centre(objective)
    squads = [s for s in _squads_on_board(loc, owner) if 1 <= len(s.models) <= 6]
    if not squads:
        return None
    squad = min(squads, key=lambda s: len(s.models))
    # Anyone else standing there first - including the AI, or control is a tie.
    for token in loc["state"].tokens:
        if token.squad is squad or token.squad is None:
            continue
        if objective.terrain_area.overlaps_model(token):
            token.x_in, token.y_in = 2.0, 2.0
    for i, model in enumerate(squad.models):
        model.x_in, model.y_in = cx + (i % 3) * 0.9 - 0.9, cy + (i // 3) * 0.9
    return squad


def fake_events():
    state["frames"] += 1
    if state["frames"] >= MAX_FRAMES:
        state["error"] = f"never finished within {MAX_FRAMES} frames (stage {state['stage']})"
        raise SystemExit(0)
    loc = _main_locals()
    if loc.get("turn_tracker") is None:
        return []
    stage = state["stage"]
    rec = state["rec"]

    if stage == "auto_on":
        state["stage"] = "settle"
        return _shift_a()

    if stage == "settle":
        if not loc["turn_tracker"].started:
            pending = _drive_pregame(loc)
            return pending if pending is not None else []
        state["stage"] = "auto_off"
        return _shift_a()

    if stage == "auto_off":
        state["stage"] = "clear"
        return []

    if stage == "clear":
        pending = _clear_blockers(loc)
        if pending is not None:
            state["settle"] += 1
            if state["settle"] > 300:
                state["error"] = "something above the board never cleared"
                raise SystemExit(0)
            return pending
        state["stage"] = "stage_a"
        return []

    # ---------------------------------------------------- A: end of Cmd phase
    if stage == "stage_a":
        ctrl = loc["primary_mission_controller"]
        rec["wired"] = ctrl is not None
        rec["plays_card"] = bool(ctrl and ctrl.plays_card)
        rec["mission_name"] = ctrl.mission.name if ctrl and ctrl.mission else None
        rec["disposition"] = army_lists.force_disposition_for(HUMAN)
        # ...and the sources really reach it, rather than being None defaults.
        rec["sees_objectives"] = len(ctrl._objectives()) if ctrl else 0
        rec["sees_terrain"] = len(ctrl._terrain()) if ctrl else 0
        rec["sees_tokens"] = len(ctrl._tokens()) if ctrl else 0

        objective = next((o for o in mc._non_home_objectives(_ctx(loc))), None)
        if objective is None:
            state["error"] = "no non-home objective on this map"
            raise SystemExit(0)
        squad = _park_on(loc, objective)
        if squad is None:
            state["error"] = "no small human unit to park on an objective"
            raise SystemExit(0)
        rec["parked"] = squad.name
        rec["objective"] = objective.name

        tt = loc["turn_tracker"]
        tt.turn_owner = HUMAN
        tt.set_active(HUMAN)
        tt.phase_index = PHASES.index(PHASE_COMMAND)
        tt.battle_round = 2          # the "2ND ROUND ONWARD" band
        for o in loc["state"].objectives:
            o.update_control(loc["state"].tokens)
        rec["controls_it"] = objective.controlled_by == HUMAN
        # How many objectives are held decides which of Secure Asset's two
        # end-of-Command-phase rows fire, and they STACK. Recorded rather than
        # assumed: parking one unit does not mean only one is held - the rest
        # of the army is still standing wherever it deployed.
        held = [o for o in loc["state"].objectives if o.controlled_by == HUMAN]
        rec["held_total"] = len(held)
        rec["held_non_home"] = len([o for o in mc._non_home_objectives(_ctx(loc))
                                    if o.controlled_by == HUMAN])
        rec["primary_before"] = loc["mission_controller"].primary_points[HUMAN]
        # main()'s OWN phase advance - the function the End Turn button and the
        # AI both go through, and the one that holds the seam under test.
        loc["advance_turn_phase"]()
        rec["primary_after"] = loc["mission_controller"].primary_points[HUMAN]
        rec["phase_after"] = tt.phase
        state["stage"] = "stage_b"
        return []

    # ------------------------------------------------------- B: end of battle
    if stage == "stage_b":
        # One line makes a dormant mission live: the list declares a different
        # Force Disposition. Purge the Foe is the only one with a FINAL SCORING
        # box, so it is the only way to reach that seam at all.
        army_lists.get(army_lists.configured_choices()[HUMAN]).force_disposition = \
            fd.PURGE_THE_FOE
        ctrl = loc["primary_mission_controller"]
        rec["mission_after_switch"] = ctrl.mission.name if ctrl.mission else None

        central = mc.central_objectives(_ctx(loc))
        rec["central_names"] = [o.name for o in central]
        if not central:
            state["error"] = "no central objective on this map"
            raise SystemExit(0)
        squad = _park_on(loc, central[0])
        rec["parked_central"] = squad.name if squad else None
        for o in loc["state"].objectives:
            o.update_control(loc["state"].tokens)
        rec["controls_central"] = central[0].controlled_by == HUMAN

        tt = loc["turn_tracker"]
        tt.battle_round = BATTLE_ROUNDS
        # battle_over is set inside TurnTracker.advance_phase(); _check_battle_end()
        # only READS it. Setting it here is the honest way to reach the seam
        # under test - that the flag gets set after five rounds is turn.py's
        # business and is tested there.
        tt.battle_over = True
        rec["primary_before_final"] = loc["mission_controller"].primary_points[HUMAN]
        # main()'s own end-of-battle check, which is where final scoring hangs.
        loc["_check_battle_end"]()
        rec["battle_over"] = tt.battle_over
        rec["primary_after_final"] = loc["mission_controller"].primary_points[HUMAN]
        overlay = loc["battle_end_overlay"]
        rec["overlay_up"] = overlay.is_pending
        rec["overlay_primary"] = next(
            (row[1] for row in (overlay._result or []) if row[0] == HUMAN), None)
        state["stage"] = "stage_c"
        return []

    # ------------------------------------------------------------- C: the panel
    if stage == "stage_c":
        army_lists.get(army_lists.configured_choices()[HUMAN]).force_disposition = \
            fd.DISRUPTION
        ctrl = loc["primary_mission_controller"]
        rec["mission_disruption"] = ctrl.mission.name if ctrl.mission else None

        tt = loc["turn_tracker"]
        tt.battle_over = False
        tt.turn_owner = HUMAN
        tt.set_active(HUMAN)
        tt.phase_index = PHASES.index(PHASE_SHOOTING)   # Booby Trap's STARTS line

        # Put a unit inside a plain terrain area outside my own deployment zone
        # - the action's second UNITS branch.
        ctx = _ctx(loc)
        areas = [a for a in loc["state"].terrain_areas
                 if not pm.area_is_an_objective(ctx, a)
                 and pm._area_outside_own_deployment_zone(ctx, a)]
        squads = [s for s in _squads_on_board(loc, HUMAN) if 1 <= len(s.models) <= 6]
        if not areas or not squads:
            state["error"] = "no plain outside terrain area, or no small unit"
            raise SystemExit(0)
        area = areas[0]
        x0, y0, x1, y1 = area.bounding_box
        ax, ay = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        squad = min(squads, key=lambda s: len(s.models))
        # Rule 16.01 refuses an ENGAGED unit, and stage A parked displaced
        # tokens in a corner that can be anywhere relative to this area. Push
        # every enemy right away first, or the action is refused for a reason
        # that has nothing to do with the wiring under test.
        for token in loc["state"].tokens:
            if token.squad is not None and token.squad.owner != HUMAN:
                token.x_in, token.y_in = ax + 30.0, ay + 30.0
        for i, model in enumerate(squad.models):
            model.x_in, model.y_in = ax + (i % 3) * 0.6, ay + (i // 3) * 0.6
        # select() takes a TOKEN (a model), not a squad - it reads token.squad.
        loc["movement_controller"].select(squad.models[0])
        rec["trap_unit"] = squad.name
        rec["offers"] = [o[0] for o in ctrl.available_actions_for(squad)]
        rec["trap_area"] = "(%.0f, %.0f)" % (ax, ay)
        rec["in_area"] = any(area.overlaps_model(m) for m in squad.models)
        # If it was refused, say WHY - a silently missing offer is exactly how
        # an eligibility bug hides, which is why can_start() returns a reason.
        rec["refusal"] = ctrl.action_controller.can_start(
            pm.BOOBY_TRAP_ACTION, squad, ctrl._context())[1]
        state["stage"] = "read_panel"
        return []

    if stage == "read_panel":
        # One frame later the panel has been drawn for the selected unit, so
        # its own button list is the honest record of what a human could click.
        labels = []
        for rect, _cb in getattr(loc.get("action_panel"), "_buttons", []):
            labels.append(rect)
        rec["panel_button_count"] = len(labels)
        rec["panel_has_booby_trap"] = any(
            "Booby Trap" in (lbl or "")
            for lbl in getattr(loc["action_panel"], "_last_labels", []))
        # The renderer question: does main.py ask the controller for markers?
        ctrl = loc["primary_mission_controller"]
        chosen = loc["movement_controller"].selected_squad
        offers = ctrl.available_actions_for(chosen) if chosen is not None else []
        if offers:
            ctrl.start_action(offers[0][1], chosen, offers[0][2])
        rec["trapped_after_start"] = len(ctrl.trapped_areas_on_board())
        raise SystemExit(0)

    raise SystemExit(0)


pygame.event.get = lambda *a, **k: fake_events()
pygame.display.flip = lambda *a, **k: None
pygame.display.update = lambda *a, **k: None

from game import config  # noqa: E402

# The two pre-game SCREENS wait for a click before main()'s loop even starts,
# and the Tactical Secondary deck asks the human a question at the end of each
# of their turns - the same three every harness here turns off.
#
# PRIMARY_MISSION_CARD_PLAYERS is deliberately NOT among them: a Primary asks
# nothing, and it is the thing under test.
config.ARMY_SELECT = False
config.MAP_SELECT = False
config.SECONDARY_MISSION_CARD_PLAYERS = ()

import main  # noqa: E402
from ai.mock_agent import MockAgent  # noqa: E402

main.ClaudeAgent = lambda *a, **k: MockAgent()

# The panel does not keep its button LABELS, only their rects and callbacks, so
# they are recorded here rather than by changing the panel to suit a test.
_ORIGINAL_DRAW_BUTTON = None
try:
    from game.ui.action_panel import ActionPanel

    _ORIGINAL_DRAW_BUTTON = ActionPanel._draw_button

    def _recording_draw_button(self, surface, rect, label, *a, **k):
        if not hasattr(self, "_last_labels"):
            self._last_labels = []
        if getattr(self, "_buttons", None) == []:
            self._last_labels = []
        self._last_labels.append(label)
        return _ORIGINAL_DRAW_BUTTON(self, surface, rect, label, *a, **k)

    ActionPanel._draw_button = _recording_draw_button
except Exception:  # pragma: no cover - the smoke still runs without labels
    pass

if NEUTRALIZE:
    # The pre-feature world: nobody plays a Force Disposition Primary, so
    # "Hold the Line" runs for everyone and no box ever scores. Stubbing the
    # property (rather than deleting one hook) is what main.py did before -
    # every seam is still called, and every one of them does nothing.
    pm.PrimaryMissionController.plays_card = property(lambda self: False)

try:
    main.main(MAP_KEY)
except SystemExit:
    pass

rec = state["rec"]
print(f"\nPrimary Mission smoke ({MAP_KEY}), {state['frames']} frames"
      + ("   [NEUTRALIZED - expected to fail]" if NEUTRALIZE else ""))
failures = []


def check(label, condition, detail=""):
    print(f"  {'PASS' if condition else 'FAIL'}  {label}{'   ' + detail if detail else ''}")
    if not condition:
        failures.append(label)


if state["error"]:
    check(state["error"], False)
else:
    print("\n  wiring:")
    check("    main() builds a PrimaryMissionController", rec.get("wired") is True)
    check("    the human is on a Force Disposition Primary", rec.get("plays_card") is True)
    check("    it resolves to a mission from the army list",
          rec.get("mission_name") == "Secure Asset",
          f"{rec.get('disposition')} -> {rec.get('mission_name')}")
    check("    its board sources are fed, not left as empty defaults",
          (rec.get("sees_objectives", 0) > 0 and rec.get("sees_terrain", 0) > 0
           and rec.get("sees_tokens", 0) > 0),
          f"objectives={rec.get('sees_objectives')} terrain={rec.get('sees_terrain')} "
          f"tokens={rec.get('sees_tokens')}")

    print(f"\n  A - end of Command phase ({rec.get('parked')} on {rec.get('objective')}):")
    check("    the unit really controls the objective (14.02)",
          rec.get("controls_it") is True)
    check("    the phase really advanced out of Command",
          rec.get("phase_after") not in (None, "Command"), str(rec.get("phase_after")))
    check("    crossing the boundary credits Primary VP",
          (rec.get("primary_after", 0) - rec.get("primary_before", 0)) > 0,
          f"{rec.get('primary_before')} -> {rec.get('primary_after')}")
    _gained = rec.get("primary_after", 0) - rec.get("primary_before", 0)
    _want = ((pm.SECURE_ASSET_ONE_OBJECTIVE_VP if rec.get("held_non_home", 0) >= 1 else 0)
             + (pm.SECURE_ASSET_THREE_OBJECTIVES_VP
                if rec.get("held_total", 0) >= pm.SECURE_ASSET_THREE_NEEDED else 0))
    check("    ...and it is Secure Asset's own rows, not Hold the Line's 3 per objective",
          _gained == _want and _gained != rec.get("held_total", 0) * 3,
          f"+{_gained}, expected +{_want} "
          f"(holding {rec.get('held_total')}, {rec.get('held_non_home')} non-home; "
          f"Hold the Line would have paid {rec.get('held_total', 0) * 3})")

    print(f"\n  B - end of battle (central: {rec.get('central_names')}):")
    check("    changing the list's disposition changes the mission mid-run",
          rec.get("mission_after_switch") == "Unstoppable Force",
          str(rec.get("mission_after_switch")))
    check("    the unit controls a central objective",
          rec.get("controls_central") is True, str(rec.get("parked_central")))
    check("    the battle really ended", rec.get("battle_over") is True)
    check("    final scoring credits its 5 VP",
          (rec.get("primary_after_final", 0) - rec.get("primary_before_final", 0))
          == pm.UNSTOPPABLE_CENTRAL_VP,
          f"{rec.get('primary_before_final')} -> {rec.get('primary_after_final')}")
    check("    the result overlay shows the total INCLUDING it",
          rec.get("overlay_up") is True
          and rec.get("overlay_primary") == rec.get("primary_after_final"),
          f"overlay={rec.get('overlay_primary')} ledger={rec.get('primary_after_final')}")

    print(f"\n  C - the panel ({rec.get('trap_unit')}):")
    check("    a third disposition gives a third mission",
          rec.get("mission_disruption") == "Death Trap", str(rec.get("mission_disruption")))
    check("    the unit really is standing in that terrain area",
          rec.get("in_area") is True, str(rec.get("trap_area")))
    check("    the controller offers Booby Trap for it",
          bool(rec.get("offers")),
          str(rec.get("offers"))[:120] or f"refused: {rec.get('refusal')}")
    check("    the LEFT PANEL actually draws that button",
          rec.get("panel_has_booby_trap") is True,
          f"{rec.get('panel_button_count')} buttons drawn")
    check("    starting it marks an area for the renderer to draw",
          rec.get("trapped_after_start", 0) > 0)

print(f"\n{'OK' if not failures else 'FAILED: ' + ', '.join(f.strip() for f in failures)}")
sys.exit(1 if failures else 0)
