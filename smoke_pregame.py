"""Headless smoke test: drive main()'s real loop through rule 03.01's pre-game
sequence and into the battle proper.

Same technique as selfplay.py - SDL dummy drivers, pygame.event.get
monkeypatched before importing main, ClaudeAgent swapped for a stub so no API
call can happen. Reads main()'s own locals off the call stack to decide which
single input the game is currently waiting on.

Run: python smoke_pregame.py [map_key] [frames] [--no-deployment]
"""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

MAP_KEY = "map2"
MAX_FRAMES = 900
PREGAME = True
for arg in sys.argv[1:]:
    if arg == "--no-deployment":
        PREGAME = False
    elif arg.isdigit():
        MAX_FRAMES = int(arg)
    else:
        MAP_KEY = arg

frames = 0
armed_auto_play = False
seen_states = []
milestones = {}


pregame_is_running = False
agent_calls_during_pregame = []


class StubAgent:
    """Answers 0 to everything, so no API call can happen. The assertion is the
    point: the pre-game is built to be entirely deterministic, so a call
    arriving while it is still running is a real regression."""

    def decide(self, observation):
        if pregame_is_running:
            agent_calls_during_pregame.append(observation)
        return 0

    def plan_turn(self, observation, problems=()):
        if pregame_is_running:
            agent_calls_during_pregame.append(observation)
        return {"turn_intent": "", "unit_plans": {}, "malformed": False}


report = []
exposures = {}
forwards = {}


def _snapshot(loc):
    """What the board actually looks like the moment the battle begins."""
    from game import config
    from game import deployment as dep

    state = loc["state"]
    tt = loc["turn_tracker"]
    zones = {z.owner: z for z in state.deployment_zones}
    on_board = []
    for token in state.tokens:
        if token.squad is not None and token.squad not in on_board:
            on_board.append(token.squad)

    report.append(f"first player: {tt.first_player} (battle round {tt.battle_round})")
    for owner in ("Player 1", "Player 2"):
        mine = [s for s in on_board if s.owner == owner]
        reserved = [s for s in state.reserves if s.owner == owner]
        embarked = [s for s in state.embarked_squads if s.owner == owner]
        zone = zones.get(owner)
        outside = [
            s.name for s in mine
            if zone is not None and not all(
                zone.contains_circle(m.x_in, m.y_in, m.radius_in) for m in s.models
            )
        ]
        incoherent = [s.name for s in mine if s.check_coherency()]
        flagged = [s.name for s in mine + reserved + embarked if s.set_up_this_turn]
        report.append(
            f"{owner}: {len(mine)} deployed, {len(reserved)} in reserve, {len(embarked)} embarked"
        )
        report.append(f"   deployed: {', '.join(s.name for s in mine)}")
        if reserved:
            report.append(f"   reserves: {', '.join(s.name for s in reserved)}")
        if embarked:
            report.append(f"   embarked: {', '.join(s.name for s in embarked)}")
        report.append(f"   outside own zone: {outside or 'none'}")
        report.append(f"   incoherent: {incoherent or 'none'}")
        report.append(f"   still flagged set_up_this_turn: {flagged or 'none'}")

        # The claim the AI's scorer makes: "key" units end up less visible from
        # the enemy deployment zone than "screen" units, which is the whole of
        # "wichtige Einheiten hinter Gelaende verstecken". Measured, not assumed.
        from ai import deployment_ai, observation

        probes = []
        for zone in dep.enemy_zones(state.deployment_zones, owner):
            probes.extend(deployment_ai._zone_probe_points(zone))
        forward_axis = deployment_ai._forward_axis(
            zones.get(owner), config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN)
        by_role = {}
        forward_by_role = {}
        for squad in mine:
            role = deployment_ai._deployment_role(squad)
            cx = sum(m.x_in for m in squad.models) / len(squad.models)
            cy = sum(m.y_in for m in squad.models) / len(squad.models)
            exposure = observation.zone_visibility_from_point(
                cx, cy, max(m.radius_in for m in squad.models), owner, probes,
                state.obstacles, state.terrain_areas, state.tokens,
            )
            by_role.setdefault(role, []).append((squad.name, exposure))
            forward_by_role.setdefault(role, []).append(
                cx * forward_axis[0] + cy * forward_axis[1])
        forwards.setdefault(owner, {}).update(forward_by_role)
        report.append(f"   exposure to the enemy zone (out of {len(probes)} probe points):")
        for role in ("heavy", "key", "shooter", "screen"):
            entries = by_role.get(role, [])
            if not entries:
                continue
            avg = sum(e for _, e in entries) / len(entries)
            report.append(f"      {role:<8} avg {avg:5.2f}  " + ", ".join(f"{n}={e}" for n, e in entries))
        exposures.setdefault(owner, {}).update(
            {role: [e for _, e in entries] for role, entries in by_role.items()}
        )


def _click(pos):
    return [
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": 1}),
        pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": pos, "button": 1}),
    ]


def _main_locals():
    depth = 1
    while True:
        try:
            frame = sys._getframe(depth)
        except ValueError:
            return {}
        if "turn_tracker" in frame.f_locals and "pregame_controller" in frame.f_locals:
            return frame.f_locals
        depth += 1


def fake_events():
    global frames, armed_auto_play, pregame_is_running
    frames += 1
    if frames >= MAX_FRAMES:
        raise SystemExit(0)

    loc = _main_locals()
    if not loc:
        return []

    pre = loc.get("pregame_controller")
    tt = loc.get("turn_tracker")
    if pre is not None:
        pregame_is_running = pre.is_active
        state_name = pre.state
        if not seen_states or seen_states[-1] != state_name:
            seen_states.append(state_name)
            milestones.setdefault(state_name, frames)
            if state_name == "done" and not report:
                _snapshot(loc)

    if not armed_auto_play:
        armed_auto_play = True
        return [pygame.event.Event(
            pygame.KEYDOWN, {"key": pygame.K_a, "mod": pygame.KMOD_LSHIFT, "unicode": "A"}
        )]

    # Modal notices first - they swallow every other input anyway.
    for name in ("turn_start_overlay", "turn_plan_overlay",
                 "stratagem_notice_overlay", "waaagh_notice_overlay"):
        overlay = loc.get(name)
        if overlay is not None and overlay.is_pending:
            return _click((10, 10))

    dice = loc.get("dice_manager")
    if dice is not None and dice.is_pending:
        # Bottom-right, deliberately NOT the left panel: main.py routes
        # left-panel clicks to the action panel instead of acknowledging.
        surf = pygame.display.get_surface()
        return _click((surf.get_width() - 8, surf.get_height() - 8))

    # Rule 24.31/24.32: the human's Scouts choice now really is a choice, and
    # its first option OPENS a scout move rather than resolving anything. The
    # harness clicks option 0 below, so it also has to finish what that starts -
    # otherwise the pre-game sits in MOVING for ever and this smoke reports
    # "the pre-game never finished", which is exactly how this was found.
    #
    # Confirmed rather than cancelled, and with the models left where they
    # stand: a zero-distance scout move is legal (24.31 offers, never compels)
    # and it exercises the confirm path, which is the one that has to resume
    # the SCOUTS queue.
    mover = loc.get("movement_controller")
    if mover is not None and getattr(mover, "move_mode", None) == "scout":
        mover.confirm_move()
        return []

    decisions = loc.get("decision_manager")
    if decisions is not None and decisions.is_pending:
        overlay = loc.get("decision_overlay")
        rects = getattr(overlay, "_option_rects", None)
        if rects:
            return _click(rects[0].center)
        decisions.choose(0)
        return []

    panel = loc.get("action_panel")

    if pre is not None and pre.is_active:
        # Player 1's side of the pre-game: press whichever button the panel is
        # currently offering. Formations declares one unit per click; during
        # deployment, "Auto-place this unit" needs a selected unit first.
        if pre.state == "deploying" and pre.active_player == pre.human_player:
            if pre.selected_unit is None:
                pending = pre.pending_units(pre.human_player)
                if pending:
                    pre.select_unit(pending[0])
                    return []
        buttons = getattr(panel, "_buttons", [])
        if buttons:
            return _click(buttons[0][0].center)
        return []

    status = loc.get("game_status_panel")
    if tt is not None and tt.started and tt.turn_owner == "Player 1":
        button = getattr(status, "_button_rect", None)
        if button is not None:
            return _click(button.center)
    return []


pygame.event.get = lambda *a, **k: fake_events()

from game import config  # noqa: E402

config.PREGAME_DEPLOYMENT = PREGAME
# The army selection screen (game/ui/army_select.py) waits for a click, and
# nothing here answers one before main()'s own loop starts - so this harness
# fields whatever config.PLAYER1_ARMY/PLAYER2_ARMY say, exactly as every run
# of it did before that screen existed. smoke_army_select.py is the one that
# drives the screen for real.
config.ARMY_SELECT = False
# The map selection screen (game/ui/map_select.py) waits for a click too -
# same reason as ARMY_SELECT above.
config.MAP_SELECT = False
# The Tactical Secondary Mission deck asks the human a question at the end of
# every one of their turns, and this harness answers no prompt that belongs to
# the human outside the pre-game - so leaving it on would stall here on a
# decision nobody is present to make. Same reason ARMY_SELECT/MAP_SELECT are
# off above. test_secondary_missions.py has a source guard requiring this of
# every harness.
config.SECONDARY_MISSION_CARD_PLAYERS = ()

import main  # noqa: E402

main.ClaudeAgent = lambda *a, **k: StubAgent()

print(f"map={MAP_KEY} frames={MAX_FRAMES} pregame={PREGAME}")
try:
    main.main(MAP_KEY)
except SystemExit:
    pass

print(f"\nran {frames} frames")
print("pre-game states seen:", " -> ".join(seen_states) or "(none)")
for name, frame_no in milestones.items():
    print(f"  {name}: first seen at frame {frame_no}")
if report:
    print("\n--- board state at the moment the battle began ---")
    for line in report:
        print(line)
print(f"\nagent calls during the pre-game: {len(agent_calls_during_pregame)} (must be 0)")
if PREGAME and "done" not in seen_states:
    print("FAILED: the pre-game never finished")
    sys.exit(1)

# Player 2 is the side the AI actually deployed on its own (Player 1 was
# driven by this harness clicking "Auto-place"), so it is the honest sample.
#
# What this guards is that the role-based scorer is not INVERTED - that the
# AI is not tucking its cheap screens away while parking its vehicles and
# characters in the open. The original form was a strict "key < screen",
# which held while screens were pushed forward and therefore visible.
#
# That form became unsatisfiable rather than false when the Ork roster was
# replaced: the AI now hides the screens perfectly (screen avg 0.00), and no
# number can be below zero. Two of the new "key" units are also among the
# largest models in the game (the Kill Rig and Battlewagon share the
# Devilfish's 2.1" base, over 4" across) - there is simply less terrain that
# can cover them completely.
#
# So the absolute floor is checked as well: a key exposure that is LOW in
# its own right passes even when the screens happen to reach zero. A real
# inversion - screens hidden, key units out in the open - still fails,
# because it would blow past the ceiling. measure_deployment_safety.py is
# the finer-grained companion check.
KEY_EXPOSURE_CEILING = 3.0  # of 33 probe points, i.e. ~9% of the enemy zone
ai_side = exposures.get("Player 2", {})
for role in ("key", "heavy"):
    if not (PREGAME and ai_side.get(role) and ai_side.get("screen")):
        continue
    role_avg = sum(ai_side[role]) / len(ai_side[role])
    screen_avg = sum(ai_side["screen"]) / len(ai_side["screen"])
    ok = role_avg < screen_avg or role_avg <= KEY_EXPOSURE_CEILING
    print(f"\n[{'ok' if ok else 'FAILED'}] AI's {role} units are not left in the open: "
          f"{role} avg {role_avg:.2f} vs screen avg {screen_avg:.2f} "
          f"(ceiling {KEY_EXPOSURE_CEILING:.2f} of 33)")
    if not ok:
        sys.exit(1)

# The front-row guard. This is the property the "heavy" role exists for, and
# unlike exposure it can only be checked on the finished board: a big model has
# to be deployed AHEAD of the cheap bodies, or it spends its first turns
# grinding through them. The reported case had the army's five biggest at ranks
# 11-15 of 15 with a mean of 8.4 friendly models in each one's lane.
ai_forward = forwards.get("Player 2", {})
if PREGAME and ai_forward.get("heavy") and ai_forward.get("screen"):
    heavy_fwd = sum(ai_forward["heavy"]) / len(ai_forward["heavy"])
    screen_fwd = sum(ai_forward["screen"]) / len(ai_forward["screen"])
    ok = heavy_fwd >= screen_fwd
    print(f"[{'ok' if ok else 'FAILED'}] AI's heavy units deploy in the front row: "
          f"heavy {heavy_fwd:.2f}\" forward vs screen {screen_fwd:.2f}\"")
    if not ok:
        sys.exit(1)
if agent_calls_during_pregame:
    print("FAILED: the pre-game consulted the agent")
    sys.exit(1)
