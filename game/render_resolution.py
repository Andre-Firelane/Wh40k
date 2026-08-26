"""How many pixels the board's offscreen Surface is rendered at.

User report: "kannst du die auflösung der sprites noch erhöhen. das ist
momentan alles noch sehr pixelig". Measured against the real scene, the
sprite FILES are not the limit - most are ~1000px square, while a 0.63"
model was only ever baked at ~57-83 board pixels. What was pixelated is the
last step: main.py renders the board onto an offscreen Surface at a fixed
resolution and Camera then scales the visible sub-rect of it up to fill the
on-screen board area, so past a certain zoom the screen shows more pixels
than were ever rendered and the rest are invented by the upscaler.

That fixed resolution used to be config.PIXELS_PER_INCH * a hand-tuned
RENDER_SUPERSAMPLE constant (2.5), chosen when the board was one fixed size.
It cannot be right for more than one map, because how far the camera blows
the board up depends on how big the board is relative to the screen - a
SMALL board is magnified MORE. Measured at 1920x1200, the same 2.5 gave:

    map1 44"x60"   x1.87 upscale at max zoom  (46% of shown pixels invented)
    map2 60"x44"   x1.37                      (27% invented)
    map3 30"x30"   x2.74                      (64% invented)

So the resolution is derived here instead of configured. `needed` below is
exactly the resolution at which, at MAX_ZOOM, one rendered pixel maps to one
screen pixel - nothing is ever upscaled, and no pixel is rendered that the
camera can never show (raising it further is pure waste, which is why this
is a target and not a floor to keep raising).

The other half of making that affordable lives in main.py: the board draw is
clipped to the camera's visible rect, so the per-frame cost follows the
SCREEN area rather than the board's full pixel count. Measured on the real
army, derived resolution + that clip is FASTER than the old fixed 2.5 was:

    map1  9.2ms -> 7.3ms      map2  9.9ms -> 6.3ms      map3  5.6ms -> 7.8ms

(map3 is the one that costs more - it was also the blurriest by far.)
"""

from game import config
from game.camera import MAX_ZOOM


def board_pixels_per_inch(area_w_px, area_h_px, board_w_in, board_h_in,
                          max_zoom=MAX_ZOOM, max_pixels=None):
    """Board pixels per inch to render the offscreen board Surface at, for a
    board of board_w_in x board_h_in shown in an area_w_px x area_h_px
    on-screen rect.

    Two bounds around the ideal:
      * never coarser than config.PIXELS_PER_INCH - the historical baseline,
        so a small window can only ever save work, never look worse than the
        fixed-resolution version did.
      * never more than max_pixels total (config.RENDER_MAX_PIXELS), because
        the cost that does NOT follow the visible area is memory: the board
        Surface, the cached static terrain layer and the placement overlay
        are each the full board, at 4 bytes a pixel. Hitting this cap gives
        back some upscaling at max zoom, still far less than the fixed
        constant did.
    """
    if max_pixels is None:
        max_pixels = config.RENDER_MAX_PIXELS
    # Camera "covers" the board area (see game/camera.py), i.e. it scales by
    # whichever axis ratio is LARGER - so that axis is the one that decides.
    needed = max_zoom * max(area_w_px / board_w_in, area_h_px / board_h_in)
    ppi = max(float(config.PIXELS_PER_INCH), needed)
    budget_ppi = (max_pixels / (board_w_in * board_h_in)) ** 0.5
    return max(float(config.PIXELS_PER_INCH), min(ppi, budget_ppi))
