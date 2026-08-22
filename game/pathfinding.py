"""Auxiliary grid/A* pathfinding for the AI's movement planning.

This is a pure geometry/search utility with zero game-rule knowledge - it
mirrors the existing split between `game/geometry.py` (pure math, no rule
knowledge) and `game/movement.py` (decides what actually counts as
blocking for a given mover/move type). Callers pre-filter which obstacles
and models are hard-blocking for their specific mover (see
`blocking_obstacles_for()`/`enemy_models_for()` below, which mirror the
exact predicates `MovementController.clamp_move()` already uses) and pass
those in - `find_route()` only ever proposes a *candidate* waypoint list
for the caller's existing per-model walk-and-commit loop to execute. The
real per-model legality (`clamp_move()`/`try_commit_segment()`) still
gatekeeps every step exactly as before; this module never touches game
state and never mutates a token.
"""
import heapq
import math
from collections import deque

from game import geometry

_DIAGONAL = math.sqrt(2)
_NEIGHBOR_OFFSETS = (
    (1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
    (1, 1, _DIAGONAL), (1, -1, _DIAGONAL), (-1, 1, _DIAGONAL), (-1, -1, _DIAGONAL),
)
_WINDOW_MARGIN_IN = 2.0
_MAX_GRID_CELLS = 20000  # safety cap so a too-fine cell_size_in can't hang a call


def blocking_obstacles_for(mover_token, obstacles):
    """The same predicate `MovementController.clamp_move()` already uses:
    Dense terrain blocks everyone except INFANTRY/BEASTS/SWARM/MOBILE
    movers (rule 13.05/13.06)."""
    return [o for o in obstacles if o.blocks_movement_for(mover_token)]


def enemy_models_for(mover_token, all_tokens):
    """Same semantics as `MovementController._enemy_models()`: a model's
    base can be moved through friendly models, but not through enemy ones
    (rule 03.01)."""
    if mover_token.squad is None:
        return []
    return [
        other for other in all_tokens
        if other is not mover_token and other.squad is not None
        and other.squad.owner != mover_token.squad.owner
    ]


def find_route(
    start_xy, goal_xy, mover_radius_in, max_distance_in,
    hard_obstacles, hard_models,
    board_width_in, board_height_in,
    cell_size_in=1.0,
):
    """Find a short waypoint list from start_xy toward (as close as
    possible to) goal_xy, avoiding hard_obstacles/hard_models, using at
    most max_distance_in inches of total travel.

    Returns:
    - None if start_xy is invalid (blocked / can't even begin), or the
      windowed grid finds no reachable cell at all.
    - [] if start_xy is already effectively at goal_xy.
    - otherwise a list of (x, y) waypoints (string-pulled, NOT one point
      per grid cell, and NOT including start_xy itself) truncated to the
      movement budget - feed these one at a time into the caller's
      existing clamp_move()/try_commit_segment() loop, exactly like a
      single aim point is used today.
    """
    if _distance(start_xy, goal_xy) <= 1e-6:
        return []

    if _direct_line_clear(start_xy, goal_xy, hard_obstacles, hard_models, mover_radius_in):
        return _truncate_path([start_xy, goal_xy], max_distance_in)

    grid = _Grid(
        start_xy, goal_xy, mover_radius_in, max_distance_in,
        hard_obstacles, hard_models, board_width_in, board_height_in, cell_size_in,
    )
    start_cell = grid.start_cell
    if grid.is_blocked(start_cell):
        # The mover is standing HERE, legally - the engine put it there - so
        # its true position is passable by definition. Only the GRID says
        # otherwise, because is_blocked() tests the cell CENTRE, which can sit
        # up to half a cell away and land inside a wall the mover is merely
        # parked next to. Giving up there fails routing for exactly the units
        # that need it most: one that cannot cross Dense terrain (rule 13.06)
        # and has stopped against a wall gets no route at all, so every
        # remaining candidate its caller tries is a straight line into that
        # wall, so it does not move - and because it does not move, the same
        # thing happens again next turn, and every turn after.
        #
        # Measured on the reported Deff Dread ("deffdread haengt an der mauer
        # und bewegt sich nicht mehr") at (26.70,15.94) against map2's central
        # ruin: the start cell tested blocked and this returned None, while
        # the very same query with a larger budget - which changes nothing but
        # the window origin, and with it the PHASE of the cell centres - found
        # a route through the ruin door immediately. Whether a unit can route
        # at all was decided by grid alignment.
        #
        # Same treatment the blocked GOAL cell already gets below: step to the
        # nearest cell that is genuinely usable. The extra condition is that
        # the mover must be able to reach it in a straight line, so the route
        # never opens with a leg through the wall it is standing against.
        start_cell = grid.nearest_unblocked_cell(
            start_cell,
            predicate=lambda c: _direct_line_clear(
                start_xy, grid.cell_center(c), hard_obstacles, hard_models, mover_radius_in
            ),
        )
        if start_cell is None:
            return None

    goal_cell = grid.goal_cell
    used_true_goal = True
    if grid.is_blocked(goal_cell):
        goal_cell = grid.nearest_unblocked_cell(goal_cell)
        used_true_goal = False
        if goal_cell is None:
            return None

    raw_cells = _astar(grid, start_cell, goal_cell)
    if not raw_cells or len(raw_cells) < 2:
        return None

    raw_path = [grid.cell_center(c) for c in raw_cells]
    if start_cell == grid.start_cell:
        raw_path[0] = start_xy
    else:
        # Keep the substituted cell as a real waypoint rather than overwriting
        # it: that first leg is the one checked above, and dropping it would
        # leave an unchecked line from the true position straight to the
        # SECOND cell - past the wall the substitution exists to get around.
        raw_path.insert(0, start_xy)
    if used_true_goal and raw_cells[-1] == grid.goal_cell:
        # Snap the final waypoint back to the exact goal instead of its
        # (slightly off) cell center, as long as that doesn't reintroduce
        # a blocked line from the previous waypoint.
        if _direct_line_clear(raw_path[-2], goal_xy, hard_obstacles, hard_models, mover_radius_in):
            raw_path[-1] = goal_xy

    simplified = _string_pull(raw_path, hard_obstacles, hard_models, mover_radius_in)
    return _truncate_path(simplified, max_distance_in)


def _distance(p1, p2):
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])


def _direct_line_clear(p1, p2, hard_obstacles, hard_models, mover_radius_in):
    """True if a straight line from p1 to p2 never enters an obstacle or a
    hard-blocking model's base, inflated by the mover's own radius - reuses
    the exact same fraction checks the continuous engine already uses
    mid-drag (`geometry.max_unblocked_fraction`/`_models`)."""
    if geometry.max_unblocked_fraction(p1, p2, hard_obstacles, inflate_radius=mover_radius_in) < 1.0:
        return False
    if geometry.max_unblocked_fraction_models(p1, p2, hard_models, inflate_radius=mover_radius_in) < 1.0:
        return False
    return True


def _truncate_path(path, max_distance_in):
    """path[0] is the start position; returns the subsequent waypoints
    (excluding the start) reachable within max_distance_in inches of
    total travel, inserting a partial point if the budget runs out
    mid-segment."""
    if len(path) < 2:
        return []
    result = []
    remaining = max_distance_in
    prev = path[0]
    for point in path[1:]:
        seg_len = _distance(prev, point)
        if seg_len <= remaining + 1e-9:
            result.append(point)
            remaining -= seg_len
            prev = point
            if remaining <= 1e-9:
                break
        else:
            if seg_len > 1e-9:
                frac = max(0.0, remaining) / seg_len
                result.append((
                    prev[0] + (point[0] - prev[0]) * frac,
                    prev[1] + (point[1] - prev[1]) * frac,
                ))
            break
    return result


def _string_pull(raw_path, hard_obstacles, hard_models, mover_radius_in):
    """Collapse a dense per-cell path down to the few waypoints actually
    needed: from each anchor, jump to the farthest point still reachable
    by a clear straight line."""
    n = len(raw_path)
    if n <= 2:
        return list(raw_path)

    simplified = [raw_path[0]]
    anchor_idx = 0
    while anchor_idx < n - 1:
        anchor = raw_path[anchor_idx]
        farthest = anchor_idx + 1
        for candidate_idx in range(n - 1, anchor_idx, -1):
            if _direct_line_clear(anchor, raw_path[candidate_idx], hard_obstacles, hard_models, mover_radius_in):
                farthest = candidate_idx
                break
        simplified.append(raw_path[farthest])
        anchor_idx = farthest
    return simplified


class _Grid:
    """A local, windowed grid (bounded by start/goal + movement budget, not
    the whole board) used only to drive the A* search - a helper, not a
    replacement for the continuous engine."""

    def __init__(self, start_xy, goal_xy, mover_radius_in, max_distance_in,
                 hard_obstacles, hard_models, board_width_in, board_height_in, cell_size_in):
        self.hard_obstacles = hard_obstacles
        self.hard_models = hard_models
        self.mover_radius_in = mover_radius_in
        self.board_width_in = board_width_in
        self.board_height_in = board_height_in

        margin = max(_WINDOW_MARGIN_IN, mover_radius_in * 2.0, cell_size_in * 2.0)
        min_x = max(0.0, min(start_xy[0], goal_xy[0]) - max_distance_in - margin)
        max_x = min(board_width_in, max(start_xy[0], goal_xy[0]) + max_distance_in + margin)
        min_y = max(0.0, min(start_xy[1], goal_xy[1]) - max_distance_in - margin)
        max_y = min(board_height_in, max(start_xy[1], goal_xy[1]) + max_distance_in + margin)

        cols = max(1, math.ceil((max_x - min_x) / cell_size_in))
        rows = max(1, math.ceil((max_y - min_y) / cell_size_in))
        if cols * rows > _MAX_GRID_CELLS:
            scale = math.sqrt((cols * rows) / _MAX_GRID_CELLS)
            cell_size_in *= scale
            cols = max(1, math.ceil((max_x - min_x) / cell_size_in))
            rows = max(1, math.ceil((max_y - min_y) / cell_size_in))

        self.min_x, self.min_y = min_x, min_y
        self.cell_size_in = cell_size_in
        self.cols, self.rows = cols, rows
        self._blocked_cache = {}

        self.start_cell = self.cell_of(start_xy)
        self.goal_cell = self.cell_of(goal_xy)

    def cell_of(self, xy):
        col = int((xy[0] - self.min_x) / self.cell_size_in)
        row = int((xy[1] - self.min_y) / self.cell_size_in)
        col = max(0, min(self.cols - 1, col))
        row = max(0, min(self.rows - 1, row))
        return (col, row)

    def cell_center(self, cell):
        col, row = cell
        return (
            self.min_x + (col + 0.5) * self.cell_size_in,
            self.min_y + (row + 0.5) * self.cell_size_in,
        )

    def in_bounds(self, cell):
        col, row = cell
        return 0 <= col < self.cols and 0 <= row < self.rows

    def is_blocked(self, cell):
        cached = self._blocked_cache.get(cell)
        if cached is not None:
            return cached
        x, y = self.cell_center(cell)
        blocked = (
            x < self.mover_radius_in or x > self.board_width_in - self.mover_radius_in
            or y < self.mover_radius_in or y > self.board_height_in - self.mover_radius_in
            # Use the same square-corner rect inflation `max_unblocked_fraction()`
            # uses (not `Obstacle.overlaps_circle()`'s rounded-corner distance
            # check) - the two must agree, since `_direct_line_clear()` (used by
            # both string-pulling and this test suite) is the ultimate judge of
            # whether a waypoint segment is actually legal, and it calls
            # `max_unblocked_fraction()`. A point this cell-blocked test allows
            # but the segment check disallows (or vice versa) near a corner
            # would let an "individually unblocked" cell produce a segment the
            # continuous check rejects.
            or any(
                o.min_x - self.mover_radius_in <= x <= o.max_x + self.mover_radius_in
                and o.min_y - self.mover_radius_in <= y <= o.max_y + self.mover_radius_in
                for o in self.hard_obstacles
            )
            or any(
                _distance((x, y), (m.x_in, m.y_in)) <= m.radius_in + self.mover_radius_in
                for m in self.hard_models
            )
        )
        self._blocked_cache[cell] = blocked
        return blocked

    def neighbors(self, cell):
        col, row = cell
        for dcol, drow, cost in _NEIGHBOR_OFFSETS:
            nxt = (col + dcol, row + drow)
            if not self.in_bounds(nxt) or self.is_blocked(nxt):
                continue
            if dcol != 0 and drow != 0:
                # Disallow cutting a diagonal corner: a thin obstacle/model
                # corner could otherwise slip between two cells that are each
                # individually unblocked but whose diagonal connects straight
                # through it. Require both orthogonal flanking cells clear too.
                flank_a = (col + dcol, row)
                flank_b = (col, row + drow)
                if (not self.in_bounds(flank_a) or self.is_blocked(flank_a)
                        or not self.in_bounds(flank_b) or self.is_blocked(flank_b)):
                    continue
            yield nxt, cost * self.cell_size_in

    def nearest_unblocked_cell(self, cell, predicate=None):
        """Ring search outward from `cell` for the closest unblocked cell -
        used when the true goal cell itself is blocked, so the mover can
        still approach as close as possible, and when the START cell tests
        blocked because its centre landed inside a wall the mover is merely
        standing beside (see find_route()).

        `predicate`, if given, is an extra condition a candidate must also
        satisfy - the start-cell case uses it to require a clear straight
        line from the mover's true position, which the goal case does not
        need."""
        seen = {cell}
        queue = deque([cell])
        while queue:
            current = queue.popleft()
            if (self.in_bounds(current) and not self.is_blocked(current)
                    and (predicate is None or predicate(current))):
                return current
            col, row = current
            for dcol, drow, _ in _NEIGHBOR_OFFSETS:
                nxt = (col + dcol, row + drow)
                if nxt not in seen and self.in_bounds(nxt):
                    seen.add(nxt)
                    queue.append(nxt)
        return None


def _astar(grid, start_cell, goal_cell):
    open_heap = [(0.0, start_cell)]
    g_score = {start_cell: 0.0}
    came_from = {}
    closed = set()
    best_cell = start_cell
    best_h = _distance(grid.cell_center(start_cell), grid.cell_center(goal_cell))

    while open_heap:
        _, current = heapq.heappop(open_heap)
        if current in closed:
            continue
        closed.add(current)

        h = _distance(grid.cell_center(current), grid.cell_center(goal_cell))
        if h < best_h:
            best_h = h
            best_cell = current

        if current == goal_cell:
            return _reconstruct(came_from, current)

        for neighbor, step_cost in grid.neighbors(current):
            if neighbor in closed:
                continue
            tentative_g = g_score[current] + step_cost
            if tentative_g < g_score.get(neighbor, float("inf")):
                g_score[neighbor] = tentative_g
                came_from[neighbor] = current
                f = tentative_g + _distance(grid.cell_center(neighbor), grid.cell_center(goal_cell))
                heapq.heappush(open_heap, (f, neighbor))

    if best_cell == start_cell:
        return None
    return _reconstruct(came_from, best_cell)


def _reconstruct(came_from, cell):
    path = [cell]
    while cell in came_from:
        cell = came_from[cell]
        path.append(cell)
    path.reverse()
    return path
