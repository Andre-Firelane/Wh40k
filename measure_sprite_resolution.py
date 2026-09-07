"""What limits on-screen sprite sharpness, measured on the real scene.

User report: "kannst du die auflösung der sprites noch erhöhen. das ist
momentan alles noch sehr pixelig".

The source art is NOT the limit (most files are ~1000px square). The limit is
that every token is baked onto board_surface at config.PIXELS_PER_INCH *
RENDER_SUPERSAMPLE, and the camera then scales that surface UP past zoom
~1.34 - so at max zoom the screen shows ~1.9 screen px per rendered px.

This measures the cost curve of raising RENDER_SUPERSAMPLE against the real
army, so the choice is made on numbers instead of on the old comment's
estimate. Run:  python measure_sprite_resolution.py [map_key]
"""
import os
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

MAP_KEY = sys.argv[1] if len(sys.argv) > 1 else "map2"
SCREEN_W, SCREEN_H = 1920, 1200  # the user's actual desktop, measured

pygame.init()

from game import config                      # noqa: E402
from game.board import Board                 # noqa: E402
from game.camera import Camera, MAX_ZOOM     # noqa: E402
from game.renderer import Renderer           # noqa: E402

grabbed = {}
frames = {"n": 0}


def _main_locals():
    frame = sys._getframe(1)
    while frame is not None:
        if "turn_tracker" in frame.f_locals:
            return frame.f_locals
        frame = frame.f_back
    return {}


def _click(pos):
    return [pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": 1}),
            pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": pos, "button": 1})]


def fake_events():
    """Drive rule 03.01's pre-game just far enough to get a deployed board -
    the same five traps selfplay.py's docstring lists, nothing more."""
    frames["n"] += 1
    if frames["n"] > 4000:
        print("gave up at frame", frames["n"], "tokens=", len(getattr(_main_locals().get("state"), "tokens", ())))
        raise SystemExit(0)
    loc = _main_locals()

    if not frames.get("armed"):
        # Shift+A: Player 2's auto-play, otherwise its half of the pre-game
        # sequence never advances and the board stays empty.
        frames["armed"] = True
        return [pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_a, "mod": pygame.KMOD_LSHIFT,
                                                    "unicode": "A", "scancode": 4})]

    st = loc.get("state")
    if st is not None and len(getattr(st, "tokens", ())) >= 40:
        grabbed.update(loc)
        raise SystemExit(0)

    for name in ("turn_start_overlay", "turn_plan_overlay",
                 "stratagem_notice_overlay", "waaagh_notice_overlay"):
        overlay = loc.get(name)
        if overlay is not None and getattr(overlay, "is_pending", False):
            return _click((10, 10))

    dice_manager = loc.get("dice_manager")
    if dice_manager is not None and getattr(dice_manager, "is_pending", False):
        surface = pygame.display.get_surface()
        w, h = surface.get_size() if surface else (1200, 800)
        return _click((w - 8, h - 8))

    pregame_ctrl = loc.get("pregame_controller")
    if pregame_ctrl is not None and getattr(pregame_ctrl, "is_active", False):
        decisions = loc.get("decision_manager")
        if decisions is not None and decisions.is_pending:
            decisions.choose(0)
            return []
        if pregame_ctrl.state == "deploying" and pregame_ctrl.active_player == pregame_ctrl.human_player:
            if pregame_ctrl.selected_unit is None:
                pending = pregame_ctrl.pending_units(pregame_ctrl.human_player)
                if pending:
                    pregame_ctrl.select_unit(pending[0])
                    return []
        panel = loc.get("action_panel")
        buttons = getattr(panel, "_buttons", [])
        if buttons:
            return _click(buttons[0][0].center)
    return []


pygame.event.get = fake_events
pygame.display.flip = lambda *a, **k: None
import main  # noqa: E402
try:
    main.main(map_key=MAP_KEY)
except SystemExit:
    pass

state = grabbed["state"]
n_tokens = len(state.tokens)
top = SCREEN_H - config.RESERVES_PANEL_HEIGHT
rect_w = SCREEN_W - config.LEFT_PANEL_WIDTH - config.RIGHT_PANEL_WIDTH
print(f"scene: {n_tokens} tokens, {len(state.obstacles)} obstacles, board area {rect_w}x{top}\n")
print(f"{'ppi':>6} {'native px':>13} {'MP':>6} {'clip':>6} {'draw ms':>9} {'scale ms':>9} {'total ms':>9} {'upscale':>9}")

bw, bh = config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN
needed_ppi = MAX_ZOOM * max(rect_w / bw, top / bh)

for ppi, clip in ((config.PIXELS_PER_INCH * config.RENDER_SUPERSAMPLE, False),
                  (needed_ppi, False),
                  (needed_ppi, True)):
    board = Board(bw, bh, ppi)
    surf = pygame.Surface((board.width_px, board.height_px))
    cam = Camera(rect_w, top, board.width_px, board.height_px)
    r = Renderer(render_scale=ppi / config.PIXELS_PER_INCH)
    cam.zoom = MAX_ZOOM
    vis = cam.visible_rect()
    for _ in range(2):
        r.draw(surf, board, state.tokens, state.obstacles,
               deployment_zones=state.deployment_zones, blood_decals=state.blood_decals,
               terrain_areas=state.terrain_areas)
    n = 15
    t0 = time.perf_counter()
    for _ in range(n):
        if clip:
            surf.set_clip(vis)
        r.draw(surf, board, state.tokens, state.obstacles,
               deployment_zones=state.deployment_zones, blood_decals=state.blood_decals,
               terrain_areas=state.terrain_areas)
        if clip:
            surf.set_clip(None)
    draw_ms = (time.perf_counter() - t0) / n * 1000
    dest = cam.dest_rect()
    t0 = time.perf_counter()
    for _ in range(n):
        view = surf.subsurface(vis)
        if (dest.width, dest.height) == view.get_size():
            view.copy()
        else:
            pygame.transform.smoothscale(view, (dest.width, dest.height))
    scale_ms = (time.perf_counter() - t0) / n * 1000
    mp = board.width_px * board.height_px / 1e6
    up = cam._fit_scale * MAX_ZOOM
    print(f"{ppi:>6.1f} {board.width_px:>5}x{board.height_px:<7} {mp:>6.1f} {str(clip):>6} "
          f"{draw_ms:>9.1f} {scale_ms:>9.1f} {draw_ms+scale_ms:>9.1f} {('x%.2f' % up):>9}")
