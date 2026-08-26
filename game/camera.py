"""Board viewport: lets the board be zoomed in and panned around without
resizing the window or touching any of the board's own inch<->pixel math
(game/board.py's Board.to_px()/to_in() stay untouched, along with everything
built on top of them - Renderer, InputManager's screen<->inch conversion,
etc.). Später-Liste (Kamera-Scrolling/Viewport): the board is always
rendered at its full native resolution onto its own offscreen Surface
exactly as before; a Camera only decides which native-pixel sub-rect of
that Surface gets scaled up to fill the on-screen board area each frame
(see main.py's render loop) - "zoom" is just "show a smaller native rect".

zoom == DEFAULT_ZOOM (1.0) shows as much of the native board as possible
with NO wasted screen space and no distortion - i.e. the on-screen board
area is always fully covered, at a single uniform scale (so circular model
bases never stretch into ellipses). Fullscreen mode (main.py) means the
on-screen board area's own aspect ratio essentially never matches the
board's fixed 44"x60" (it's whatever's left over between the fixed-width
side panels on an arbitrary screen resolution) - showing the ENTIRE board
at some zoom would then either distort it (non-uniform stretch) or leave
letterbox bars unused on one axis. `_fit_scale` (the scale at DEFAULT_ZOOM)
therefore picks the LARGER of the two axis ratios ("cover"), not the
smaller ("contain") - the on-screen board area starts out fully used, no
dead space, cropping whichever axis has "extra" board relative to the
screen's own aspect.

User follow-up ("ich würde gerne noch weiter rauszoomen können, sodass ich
das ganze Spielfeld sehen kann"): zooming OUT further than DEFAULT_ZOOM (a
"cover" fit) is exactly what's needed to reveal the cropped part of that
axis, down to `min_zoom` - the zoom level at which the WHOLE board fits (a
"contain" fit). Below DEFAULT_ZOOM, the visible native crop's own aspect
ratio no longer matches the screen's (it interpolates from the screen's own
aspect at DEFAULT_ZOOM to the board's native aspect at min_zoom) - scaling
that crop up to fill the ENTIRE screen area would distort it again, so
dest_rect() below computes a real (but now dynamic, only appearing in this
zoomed-out range) letterbox sub-rect instead; to_native_px()/zoom_at()/
update_pan() all go through it too, so clicking/dragging/zooming stays
correct even while it's letterboxed.

Important: "zoom" is deliberately relative to "the whole screen area is
covered" (DEFAULT_ZOOM), NOT to raw 1-native-pixel-per-screen-pixel parity -
those are only the same thing when native_w/h == screen_w/h. Once main.py
started rendering the board's offscreen Surface at a higher resolution than
the screen (see game/render_resolution.py, so Camera zoom wouldn't look
blocky), native_w/h became e.g. 2x screen_w/h - under a naive "zoom 1.0 ==
1:1 native:screen" definition, DEFAULT_ZOOM would then already show only
HALF the board (a de-facto 2x crop) with no way to zoom out any further,
matching a real bug a user hit: "the game starts at 2x zoom and I can't
zoom out". `_fit_scale` below is exactly the correction for that - the
native<->screen pixel ratio at which the screen area is covered, whatever
that ratio happens to be."""

import pygame

DEFAULT_ZOOM = 1.0
MAX_ZOOM = 2.5
WHEEL_ZOOM_STEP = 1.15  # multiplicative zoom change per wheel notch (event.y of +-1)


class Camera:
    def __init__(self, screen_w, screen_h, native_w, native_h, max_zoom=MAX_ZOOM):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.native_w = native_w
        self.native_h = native_h
        cover_scale = max(screen_w / native_w, screen_h / native_h)
        contain_scale = min(screen_w / native_w, screen_h / native_h)
        # The native-px-per-screen-px scale at DEFAULT_ZOOM: the screen's
        # board area is fully COVERED (no wasted space on either axis) - see
        # this module's docstring for why this is max(), not min()
        # ("contain"). "zoom" is always relative to THIS baseline, not to
        # raw pixel parity, so DEFAULT_ZOOM always means "screen fully
        # covered" regardless of the native render resolution.
        self._fit_scale = cover_scale
        # How far below DEFAULT_ZOOM you can go: exactly the zoom level at
        # which scale drops to contain_scale, i.e. the WHOLE native board
        # fits - see the module docstring. <= 1.0 always; == 1.0 only when
        # the screen area's aspect ratio happens to exactly match the
        # board's (nothing to zoom out to reveal).
        self.min_zoom = contain_scale / cover_scale
        self.max_zoom = max_zoom
        self.zoom = DEFAULT_ZOOM
        self.pan_x = 0.0  # top-left of the visible native-pixel rect
        self.pan_y = 0.0
        self._panning = False
        self._pan_drag_start_screen = (0, 0)
        self._pan_drag_start_pan = (0.0, 0.0)

    @property
    def is_panning(self):
        return self._panning

    def visible_size(self):
        """How many native pixels the current zoom requests across the
        fixed on-screen board area - shrinks as zoom increases. NOT yet
        clamped to the native board's own bounds - see visible_rect()."""
        scale = self._fit_scale * self.zoom
        return self.screen_w / scale, self.screen_h / scale

    def visible_rect(self):
        """The native-pixel sub-rect of the board's offscreen Surface that
        should be shown this frame - always clamped fully inside the native
        board, so it's always safe to pass straight to Surface.subsurface().
        At zoom >= DEFAULT_ZOOM this never actually needs clamping (both
        axes naturally stay within native bounds - see the module
        docstring), so its aspect ratio exactly matches the screen's own;
        below DEFAULT_ZOOM one axis does get clamped, so the returned
        rect's aspect drifts away from the screen's own - dest_rect()
        below is what turns that into a real (letterboxed), not
        distorted, on-screen image."""
        vw, vh = self.visible_size()
        vw = min(vw, self.native_w)
        vh = min(vh, self.native_h)
        x = max(0.0, min(self.pan_x, self.native_w - vw))
        y = max(0.0, min(self.pan_y, self.native_h - vh))
        rect = pygame.Rect(round(x), round(y), max(1, round(vw)), max(1, round(vh)))
        # Rounding each part separately can still push 1px past the edge -
        # clamp the rounded rect too, not just the pre-rounding float one.
        rect.x = max(0, min(rect.x, self.native_w - rect.width))
        rect.y = max(0, min(rect.y, self.native_h - rect.height))
        return rect

    def dest_rect(self):
        """Where, within the fixed (0, 0, screen_w, screen_h) on-screen
        board area, this frame's visible_rect() should actually be drawn -
        preserving ITS aspect ratio (never stretching it), so the caller
        can pass this straight as the destination size/offset for
        transform.smoothscale()/blit(). Equal to the full board area
        whenever visible_rect()'s aspect already matches the screen's own
        (always true for zoom >= DEFAULT_ZOOM); shrinks and centers
        (letterboxes) only in the zoom < DEFAULT_ZOOM range, where
        visible_rect() shows more of the board than the screen's own
        aspect ratio can display without either cropping or distorting."""
        vis = self.visible_rect()
        scale = min(self.screen_w / vis.width, self.screen_h / vis.height)
        dest_w = max(1, round(vis.width * scale))
        dest_h = max(1, round(vis.height * scale))
        return pygame.Rect((self.screen_w - dest_w) // 2, (self.screen_h - dest_h) // 2, dest_w, dest_h)

    def _clamp_pan(self):
        vw, vh = self.visible_size()
        max_x = max(0.0, self.native_w - vw)
        max_y = max(0.0, self.native_h - vh)
        self.pan_x = max(0.0, min(self.pan_x, max_x))
        self.pan_y = max(0.0, min(self.pan_y, max_y))

    def to_native_px(self, screen_local_pos):
        """Maps a pixel position relative to the on-screen board area's own
        top-left (NOT full-window coordinates - the caller subtracts that
        first) to the equivalent position in the board's native, unzoomed
        pixel space - what InputManager/Board.to_in() need to keep working
        unchanged regardless of the current zoom/pan. Goes through
        dest_rect() (not a flat screen_w/h ratio) so this stays correct
        even while letterboxed - a position outside dest_rect (i.e. over a
        letterbox bar) clamps to the nearest edge of the visible crop
        rather than extrapolating past it."""
        sx, sy = screen_local_pos
        vis = self.visible_rect()
        dest = self.dest_rect()
        frac_x = min(1.0, max(0.0, (sx - dest.x) / dest.width))
        frac_y = min(1.0, max(0.0, (sy - dest.y) / dest.height))
        return vis.x + frac_x * vis.width, vis.y + frac_y * vis.height

    def zoom_at(self, screen_local_pos, factor):
        """Multiply the zoom by `factor` (>1 to zoom in, <1 to zoom out),
        keeping the native-space point currently under screen_local_pos
        fixed on screen - so zooming with the mouse wheel zooms toward/away
        from the cursor, not the board's corner."""
        new_zoom = min(self.max_zoom, max(self.min_zoom, self.zoom * factor))
        if new_zoom == self.zoom:
            return
        native_pos = self.to_native_px(screen_local_pos)
        dest = self.dest_rect()  # captured before self.zoom changes below
        frac_x = min(1.0, max(0.0, (screen_local_pos[0] - dest.x) / dest.width))
        frac_y = min(1.0, max(0.0, (screen_local_pos[1] - dest.y) / dest.height))
        self.zoom = new_zoom
        vw, vh = self.visible_size()
        self.pan_x = native_pos[0] - frac_x * vw
        self.pan_y = native_pos[1] - frac_y * vh
        self._clamp_pan()

    def begin_pan(self, screen_pos):
        """screen_pos is full-window coordinates (e.g. a raw pygame event's
        .pos) - only ever used to measure a delta against a later
        update_pan() call, so it doesn't need the board-offset subtraction
        to_native_px() does; the offset cancels out in the subtraction."""
        self._panning = True
        self._pan_drag_start_screen = screen_pos
        self._pan_drag_start_pan = (self.pan_x, self.pan_y)

    def update_pan(self, screen_pos):
        if not self._panning:
            return
        vw, vh = self.visible_size()
        dest = self.dest_rect()
        dx_screen = screen_pos[0] - self._pan_drag_start_screen[0]
        dy_screen = screen_pos[1] - self._pan_drag_start_screen[1]
        # Dragging the view right should reveal content to the left (like
        # grabbing and pulling a map) - the visible rect's own top-left
        # moves opposite to the drag. Divides by dest.width/height (the
        # ACTUAL rendered pixel span), not the outer screen_w/h, so a drag
        # still feels 1:1 even while letterboxed.
        self.pan_x = self._pan_drag_start_pan[0] - dx_screen * (vw / dest.width)
        self.pan_y = self._pan_drag_start_pan[1] - dy_screen * (vh / dest.height)
        self._clamp_pan()

    def end_pan(self):
        self._panning = False
