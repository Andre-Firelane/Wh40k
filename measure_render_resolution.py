"""End-to-end cost of the derived board render resolution, on the real scene.

Measures what the user actually pays for the sharpness fix: per-frame board
render time, peak process memory, and how much of the shown image is real
rendered detail vs invented by the upscaler - before and after, per map.

Run:  python measure_render_resolution.py [map_key]
Uses MockAgent - no API calls.
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

from game import config                              # noqa: E402
from game import render_resolution                   # noqa: E402
from game.board import Board                         # noqa: E402
from game.camera import Camera, MAX_ZOOM             # noqa: E402
from game.renderer import Renderer                   # noqa: E402

OLD_SUPERSAMPLE = 2.5  # the fixed constant this replaced

grabbed, frames = {}, {"n": 0}


def _rss_mb():
    import ctypes
    class PMC(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
    c = PMC(); c.cb = ctypes.sizeof(PMC)
    import ctypes.wintypes as w
    fn = ctypes.windll.kernel32.K32GetProcessMemoryInfo
    fn.argtypes = [w.HANDLE, ctypes.POINTER(PMC), ctypes.c_ulong]
    fn.restype = w.BOOL
    if fn(ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(c), c.cb):
        return c.WorkingSetSize / 1e6
    return float("nan")


def _main_locals():
    frame = sys._getframe(1)
    while frame is not None:
        if "turn_tracker" in frame.f_locals:
            return frame.f_locals
        frame = frame.f_back
    return {}


def fake_events():
    frames["n"] += 1
    if frames["n"] > 4000:
        raise SystemExit(0)
    loc = _main_locals()
    if not frames.get("armed"):
        frames["armed"] = True
        return [pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_a, "mod": pygame.KMOD_LSHIFT,
                                                    "unicode": "A", "scancode": 4})]
    st = loc.get("state")
    if st is not None and len(getattr(st, "tokens", ())) >= 40:
        grabbed.update(loc)
        raise SystemExit(0)
    for name in ("turn_start_overlay", "turn_plan_overlay",
                 "stratagem_notice_overlay", "waaagh_notice_overlay"):
        ov = loc.get(name)
        if ov is not None and getattr(ov, "is_pending", False):
            return _click((10, 10))
    dm = loc.get("dice_manager")
    if dm is not None and getattr(dm, "is_pending", False):
        surf = pygame.display.get_surface()
        w, h = surf.get_size() if surf else (1200, 800)
        return _click((w - 8, h - 8))
    pg = loc.get("pregame_controller")
    if pg is not None and getattr(pg, "is_active", False):
        dec = loc.get("decision_manager")
        if dec is not None and dec.is_pending:
            dec.choose(0)
            return []
        if pg.state == "deploying" and pg.active_player == pg.human_player and pg.selected_unit is None:
            pending = pg.pending_units(pg.human_player)
            if pending:
                pg.select_unit(pending[0])
                return []
        buttons = getattr(loc.get("action_panel"), "_buttons", [])
        if buttons:
            return _click(buttons[0][0].center)
    return []


def _click(pos):
    return [pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": pos, "button": 1}),
            pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": pos, "button": 1})]


pygame.event.get = fake_events
pygame.display.flip = lambda *a, **k: None
import main  # noqa: E402
try:
    main.main(map_key=MAP_KEY)
except SystemExit:
    pass

state = grabbed["state"]
top = SCREEN_H - config.RESERVES_PANEL_HEIGHT
rect_w = SCREEN_W - config.LEFT_PANEL_WIDTH - config.RIGHT_PANEL_WIDTH
bw, bh = config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN
print(f'\n{MAP_KEY}  board {bw:.0f}"x{bh:.0f}"  {len(state.tokens)} tokens  '
      f'screen board area {rect_w}x{top}\n')
print(f"{'':>8} {'ppi':>6} {'native px':>13} {'MP':>6} {'RAM MB':>7} "
      f"{'frame ms':>9} {'max-zoom detail':>16}")

for label, ppi, clip in (("before", config.PIXELS_PER_INCH * OLD_SUPERSAMPLE, False),
                         ("after", render_resolution.board_pixels_per_inch(rect_w, top, bw, bh), True)):
    base = _rss_mb()
    board = Board(bw, bh, ppi)
    surf = pygame.Surface((board.width_px, board.height_px))
    cam = Camera(rect_w, top, board.width_px, board.height_px)
    r = Renderer(render_scale=ppi / config.PIXELS_PER_INCH)
    cam.zoom = MAX_ZOOM
    vis, dest = cam.visible_rect(), cam.dest_rect()

    def one_frame():
        if clip:
            surf.set_clip(vis)
        r.draw(surf, board, state.tokens, state.obstacles,
               deployment_zones=state.deployment_zones, blood_decals=state.blood_decals,
               terrain_areas=state.terrain_areas)
        surf.set_clip(None)
        view = surf.subsurface(vis)
        if view.get_size() == (dest.width, dest.height):
            return view
        return pygame.transform.smoothscale(view, (dest.width, dest.height))

    for _ in range(3):
        one_frame()
    peak = _rss_mb() - base
    n = 20
    t0 = time.perf_counter()
    for _ in range(n):
        one_frame()
    ms = (time.perf_counter() - t0) / n * 1000
    up = cam._fit_scale * MAX_ZOOM
    detail = f"{min(1.0, 1 / up) * 100:.0f}% real"
    print(f"{label:>8} {ppi:>6.1f} {board.width_px:>5}x{board.height_px:<7} "
          f"{board.width_px * board.height_px / 1e6:>6.1f} {peak:>7.0f} {ms:>9.1f} {detail:>16}")

# --- visual proof: the same model, same final on-screen size, both ways ---
if os.environ.get("SAVE_CROPS"):
    crops = {}
    tok = max(state.tokens, key=lambda t: t.radius_in)
    for label, ppi, clip in (("before", config.PIXELS_PER_INCH * OLD_SUPERSAMPLE, False),
                             ("after", render_resolution.board_pixels_per_inch(rect_w, top, bw, bh), True)):
        board = Board(bw, bh, ppi)
        surf = pygame.Surface((board.width_px, board.height_px))
        cam = Camera(rect_w, top, board.width_px, board.height_px)
        r = Renderer(render_scale=ppi / config.PIXELS_PER_INCH)
        cam.zoom = MAX_ZOOM
        # centre the camera on that model
        px, py = board.to_px(tok.x_in, tok.y_in)
        vw, vh = cam.visible_size()
        cam.pan_x, cam.pan_y = px - vw / 2, py - vh / 2
        vis, dest = cam.visible_rect(), cam.dest_rect()
        r.draw(surf, board, state.tokens, state.obstacles,
               deployment_zones=state.deployment_zones, blood_decals=state.blood_decals,
               terrain_areas=state.terrain_areas)
        view = surf.subsurface(vis)
        shown = (view if view.get_size() == (dest.width, dest.height)
                 else pygame.transform.smoothscale(view, (dest.width, dest.height)))
        # crop a 320px box around where that model landed on screen
        cx = (px - vis.x) * dest.width / vis.width
        cy = (py - vis.y) * dest.height / vis.height
        box = pygame.Rect(0, 0, 320, 320)
        box.center = (round(cx), round(cy))
        box = box.clamp(shown.get_rect())
        out = f"crop_{MAP_KEY}_{label}.png"
        pygame.image.save(shown.subsurface(box).copy(), out)
        crops[label] = out
        print(f"  wrote {out}  ({tok.squad.name if tok.squad else tok.profile.name})")
