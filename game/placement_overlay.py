"""The green/red "where may this model be set up" overlay (rules 03.02 /
20.04 / 18.04-18.05), split out of Renderer because it stopped being a
throwaway per-frame fill.

Three things this fixes, all reported by the User against the same screenshot
("ich kann nicht so gut erkennen, wo ich jetzt modelle platzieren kann und wo
nicht", "warum kann das nicht ein feinerer uebergang sein", "warum ist die zone
ganz nah am transporter hier wieder rot"):

1. RESOLUTION. The overlay used to sample legality once per 1" cell, at the
   cell's centre, and paint that whole square one colour. Measured against a
   0.05" ground truth around a real disembarking Devilfish, that mislabels
   13% of the legal ground as red and paints 4.9 sq.in of illegal ground
   green - which is exactly the "red right next to the transport" the User
   spotted: a display artefact of the grid, not a rule. The true legal
   annulus starts at hull_radius + base_radius from the transport's centre,
   and a 1" cell straddling that boundary reads as fully red.

2. COST. Because the grid was rebuilt every frame it cost ~207 ms PER FRAME on
   the demo scene (measured) - the whole game ran at ~5 fps during any
   placement, which is the other half of "I can't see what's going on". As the
   User put it: "das raster muss ja nicht aktualisiert werden pro frame. das
   muss einmal berechnet werden und gilt dann." It genuinely holds: the
   predicate deliberately ignores the placing squad's own models (see
   SetupController.position_valid), and nothing else on the board moves while
   a unit is being set up, so the mask is constant for a whole placement.

3. READABILITY. Hard-edged 1" squares of 60-alpha green over 60-alpha red on a
   busy board read as noise. Now the illegal ground is dimmed rather than
   painted, the mask is smoothed as it is scaled up (the "feinerer Uebergang"),
   and the boundary of the legal region gets a crisp outline drawn at full
   resolution on top - so the soft fill says "roughly here" and the outline
   says "exactly here".

Resolution is reached adaptively: a full coarse pass first (fast, and correct
at 1"), then only the coarse cells that straddle a boundary get subdivided.
Measured on the demo scene that is ~3.8k predicate calls instead of the 42k a
flat 0.25" grid needs for the disembark case. The subdivision is spread across
frames under a call budget so a placement never stalls the window, and the
coarse mask is shown meanwhile.

WHAT THE COLOURS MEAN - BASE EDGES, NOT CENTRES. User: "momentan ist die
Grenze des overlays so dass der Base Mittelpunkt bis zur Grenze gehen kann.
intuitiver waere aber der Baserand ... bei Baserand muss jedes Modell
unabhaengig von der Basegroesse den selben Abstand einhalten."

Both masks are evaluated for a POINT-SIZED base, which is what makes them one
picture for the whole unit instead of one curve per base size:

  * RED is ground no part of any base may touch - board edge, Dense terrain,
    other models, and whatever the placing rule adds.
  * GREEN is 09.02's coherency band, which reads the other way round: the base
    must REACH it. Only drawn for a model RETURN, where the survivors are the
    anchor that makes it exact.

Both readings are the rule itself, not an approximation of it: every test in
this engine is measured edge to edge, so "the base is clear of the red" and
"the base touches the green" are literally the predicates - see
SetupController.base_edge_zones(). Which is also why the mask no longer
depends on WHICH model is being placed for the red half; it used to, and
main.py had to guess a representative one.
"""

import pygame

# 1" coarse pass, subdivided 4x -> 0.25" where it matters. Chosen off the
# measurement above: 0.25" cuts the mislabelled-legal-ground error from 13% to
# ~5% and the mislabelled-illegal ground from 4.9 to 0.55 sq.in.
COARSE_CELL_IN = 1.0
REFINE_FACTOR = 4
FINE_CELL_IN = COARSE_CELL_IN / REFINE_FACTOR

# Predicate calls allowed per frame while subdividing. The predicate costs
# ~30-50 us on the demo scene, so this is a ~10-15 ms slice per frame - the
# coarse mask is already correct and on screen throughout, so spreading it thin
# costs nothing but a moment of lower resolution. Measured worst case (a [DEEP
# STRIKE] unit, whose legal region covers the whole board and therefore has the
# most boundary to subdivide): ~30 frames, i.e. half a second.
REFINE_BUDGET_PER_FRAME = 300

# Illegal ground is DIMMED (dark red wash) rather than painted red, so terrain
# and models underneath stay readable; legal ground gets only a faint tint, and
# the boundary carries the actual information.
VALID_COLOR = (0, 0, 0, 0)          # legal ground is left alone - see below
INVALID_COLOR = (105, 8, 8, 120)
EDGE_COLOR = (190, 60, 60, 235)

# The keep-out layer now paints ONLY what is forbidden: with base-edge
# semantics the legal area is most of the board, and washing it green said
# nothing while hiding the terrain under it. The edge is red for the same
# reason - it is the line a base may not cross.

# The coherency band is the opposite: it is the small region the base has to
# reach, so THAT is what gets the green tint and the bright outline.
BAND_COLOR = (70, 235, 115, 44)
BAND_OUTSIDE_COLOR = (0, 0, 0, 0)
BAND_EDGE_COLOR = (150, 255, 175, 235)
EDGE_WIDTH_PX = 3


class _Mask:
    """One placement's legality grid, for one base size."""

    def __init__(self, board_width_in, board_height_in, valid_fn):
        self._valid_fn = valid_fn
        self.cols = max(1, int(board_width_in / COARSE_CELL_IN + 0.999))
        self.rows = max(1, int(board_height_in / COARSE_CELL_IN + 0.999))
        self.fine_cols = self.cols * REFINE_FACTOR
        self.fine_rows = self.rows * REFINE_FACTOR

        coarse = [
            [valid_fn((c + 0.5) * COARSE_CELL_IN, (r + 0.5) * COARSE_CELL_IN) for c in range(self.cols)]
            for r in range(self.rows)
        ]
        # Start from the coarse answer replicated into the fine grid, so the
        # mask is complete and usable from frame one; subdivision only ever
        # corrects cells near a boundary.
        self.fine = [
            [coarse[r // REFINE_FACTOR][c // REFINE_FACTOR] for c in range(self.fine_cols)]
            for r in range(self.fine_rows)
        ]
        # A coarse cell is worth subdividing only if legality changes somewhere
        # in its 8-neighbourhood - anywhere else the 1" answer is already the
        # 0.25" answer.
        self._pending = [
            (c, r)
            for r in range(self.rows)
            for c in range(self.cols)
            if any(
                0 <= r + dr < self.rows and 0 <= c + dc < self.cols and coarse[r + dr][c + dc] != coarse[r][c]
                for dr in (-1, 0, 1)
                for dc in (-1, 0, 1)
            )
        ]
        self.dirty = True

    @property
    def done(self):
        return not self._pending

    def refine(self, budget_calls=REFINE_BUDGET_PER_FRAME):
        """Subdivide as many queued boundary cells as the budget allows."""
        per_cell = REFINE_FACTOR * REFINE_FACTOR
        while self._pending and budget_calls >= per_cell:
            c, r = self._pending.pop()
            budget_calls -= per_cell
            for sr in range(REFINE_FACTOR):
                y = r * COARSE_CELL_IN + (sr + 0.5) * FINE_CELL_IN
                row = self.fine[r * REFINE_FACTOR + sr]
                for sc in range(REFINE_FACTOR):
                    x = c * COARSE_CELL_IN + (sc + 0.5) * FINE_CELL_IN
                    row[c * REFINE_FACTOR + sc] = self._valid_fn(x, y)
        # Deliberately NOT redrawn after every slice: re-rendering costs about
        # as much as a whole refinement slice (~15 ms, measured), and a
        # half-subdivided mask looks no different from the coarse one anyway.
        # So there are exactly two renders per mask - the coarse one, and the
        # finished one.
        if self.done:
            self.dirty = True


class PlacementOverlay:
    """Builds and caches the mask + its rendered surface across frames.

    Keyed by (session, base radius): a placement session is one Set Up (see
    SetupController.placement_generation), and a unit with mixed base sizes
    legitimately has a different legal region per base size, so each gets its
    own mask - cached, so alternating between two models doesn't rebuild."""

    MAX_CACHED_MASKS = 4

    def __init__(self, valid_color=VALID_COLOR, invalid_color=INVALID_COLOR,
                 edge_color=EDGE_COLOR):
        """`valid_color`/`invalid_color`/`edge_color` say what this layer MEANS.

        Two layers use it with opposite palettes: the keep-out layer paints the
        forbidden side, the coherency band paints the required side. Same mask
        machinery, because the only difference is which side is the message."""
        self.valid_color = valid_color
        self.invalid_color = invalid_color
        self.edge_color = edge_color
        self._masks = {}          # key -> _Mask
        self._surface = None
        self._surface_key = None
        self._surface_size = None

    def update(self, key, board_width_in, board_height_in, valid_fn):
        """Get (building if needed, refining if not finished) the mask for
        `key`. `valid_fn(x_in, y_in)` must be the caller's full placement
        predicate for one specific model."""
        mask = self._masks.get(key)
        if mask is None:
            mask = _Mask(board_width_in, board_height_in, valid_fn)
            if len(self._masks) >= self.MAX_CACHED_MASKS:
                self._masks.pop(next(iter(self._masks)))
            self._masks[key] = mask
        elif not mask.done:
            mask.refine()
        return mask

    def draw(self, surface, board, key, valid_fn):
        mask = self.update(key, board.width_in, board.height_in, valid_fn)
        size = (board.width_px, board.height_px)
        if mask.dirty or self._surface_key != key or self._surface_size != size:
            self._surface = self._render(mask, board)
            self._surface_key = key
            self._surface_size = size
            mask.dirty = False
        if self._surface is not None:
            surface.blit(self._surface, (0, 0))

    def _render(self, mask, board):
        """Soft fill + crisp outline. The fill is built at mask resolution and
        smoothscaled up (that interpolation IS the soft red->green transition);
        the outline is drawn afterwards at full board resolution so it stays
        sharp instead of being blurred along with the fill."""
        small = pygame.Surface((mask.fine_cols, mask.fine_rows), pygame.SRCALPHA)
        pixels = pygame.PixelArray(small)
        valid_px = small.map_rgb(self.valid_color)
        invalid_px = small.map_rgb(self.invalid_color)
        for r in range(mask.fine_rows):
            row = mask.fine[r]
            for c in range(mask.fine_cols):
                pixels[c, r] = valid_px if row[c] else invalid_px
        pixels.close()

        out = pygame.transform.smoothscale(small, (board.width_px, board.height_px))

        cell_px = board.in_to_px_len(FINE_CELL_IN)
        for r in range(mask.fine_rows):
            row = mask.fine[r]
            below = mask.fine[r + 1] if r + 1 < mask.fine_rows else None
            for c in range(mask.fine_cols):
                if not row[c]:
                    continue
                x0, y0 = c * cell_px, r * cell_px
                x1, y1 = x0 + cell_px, y0 + cell_px
                if c == 0 or not row[c - 1]:
                    pygame.draw.line(out, self.edge_color, (x0, y0), (x0, y1), EDGE_WIDTH_PX)
                if c + 1 >= mask.fine_cols or not row[c + 1]:
                    pygame.draw.line(out, self.edge_color, (x1, y0), (x1, y1), EDGE_WIDTH_PX)
                if r == 0 or not mask.fine[r - 1][c]:
                    pygame.draw.line(out, self.edge_color, (x0, y0), (x1, y0), EDGE_WIDTH_PX)
                if below is None or not below[c]:
                    pygame.draw.line(out, self.edge_color, (x0, y1), (x1, y1), EDGE_WIDTH_PX)
        return out
