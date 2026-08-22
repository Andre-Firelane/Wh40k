"""Where on this map could a squad actually hide? Rendered, so it can be checked.

The acceptance test for step 0 of the placements plan is not a number: the user
drew good staging spots on map 2 by hand and said "ich kann mir nicht
vorstellen, dass da keine squads dahinterpassen. man muss die modelle halt nur
gut anordnen". A search that cannot find those is wrong no matter what it
reports, and the drawing is a picture - so the check has to be a picture too.

This sweeps the board for ground where a squad could stand fully out of enemy
line of sight, lays its models out with formation_layout.pack_positions() (the
same deformable pour the AI uses, not a disc approximation), and writes a PNG:
terrain in grey, enemies in red, the searched unit's start in blue, and every
anchor from which a FULLY hidden placement exists in green.

Deliberately independent of the AI's own staging filters - no progress
threshold, no direction test, no "does it still hide after the enemy moves".
Those are judgements about whether a spot is WORTH taking; this answers the
prior question of whether the spot exists at all, which is the one that was
answered wrongly before.

Run:  python render_hidden_ground.py [map_key] [--unit=Boyz] [--step=1.0]
"""

import math
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

import measure_crowded_movement as H
import measure_placement_headroom as P
from game import config, formation_layout, maps
from game.game_state import GameState

PIXELS_PER_INCH = 14
DEFAULT_STEP_IN = 1.0
FACINGS = 6


def sweep(state, squad, sight, step_in):
    """Every anchor on the board from which this squad can be laid out fully
    hidden. Returns (hidden_anchors, point_hidden_anchors, tested)."""
    valid = P.slot_validator(state, squad)
    widest = max(squad.models, key=lambda m: m.radius_in)
    smallest = min(m.radius_in for m in squad.models)
    gap_in = 2 * smallest + 0.05

    anchors, point_hidden, hidden = [], [], []
    x = widest.radius_in
    while x <= config.BOARD_WIDTH_IN - widest.radius_in:
        y = widest.radius_in
        while y <= config.BOARD_HEIGHT_IN - widest.radius_in:
            if valid(widest, x, y):
                anchors.append((x, y))
            y += step_in
        x += step_in

    for (x, y) in anchors:
        if sight.seen(widest, x, y):
            continue
        point_hidden.append((x, y))
        for k in range(FACINGS):
            slots = formation_layout.pack_positions(
                squad, x, y, base_angle=-math.pi / 2 + k * 2 * math.pi / FACINGS,
                position_valid=valid, gap_in=gap_in)
            if len(set(slots)) != len(slots):
                continue
            if any(sight.seen(m, sx, sy) for m, (sx, sy) in zip(squad.models, slots)):
                continue
            hidden.append(((x, y), slots))
            break
    return hidden, point_hidden, anchors


def draw(state, squad, hidden, point_hidden, enemy_models, path):
    w = int(config.BOARD_WIDTH_IN * PIXELS_PER_INCH)
    h = int(config.BOARD_HEIGHT_IN * PIXELS_PER_INCH)
    surface = pygame.Surface((w, h))
    surface.fill((22, 24, 28))
    to_px = lambda x, y: (int(x * PIXELS_PER_INCH), int(y * PIXELS_PER_INCH))

    for area in state.terrain_areas:
        for feature in getattr(area, "features", []) or []:
            rect = pygame.Rect(*to_px(feature.min_x, feature.min_y),
                               max(1, int((feature.max_x - feature.min_x) * PIXELS_PER_INCH)),
                               max(1, int((feature.max_y - feature.min_y) * PIXELS_PER_INCH)))
            pygame.draw.rect(surface, (58, 62, 70), rect)
    for obstacle in state.obstacles:
        rect = pygame.Rect(*to_px(obstacle.min_x, obstacle.min_y),
                           max(1, int((obstacle.max_x - obstacle.min_x) * PIXELS_PER_INCH)),
                           max(1, int((obstacle.max_y - obstacle.min_y) * PIXELS_PER_INCH)))
        pygame.draw.rect(surface, (110, 116, 128), rect)

    for (x, y) in point_hidden:
        pygame.draw.circle(surface, (40, 90, 55), to_px(x, y), 2)
    for (anchor, _slots) in hidden:
        pygame.draw.circle(surface, (70, 220, 110), to_px(*anchor), 4)

    for model in enemy_models:
        pygame.draw.circle(surface, (220, 70, 70), to_px(model.x_in, model.y_in),
                           max(2, int(model.radius_in * PIXELS_PER_INCH)))
    for model in squad.models:
        pygame.draw.circle(surface, (80, 150, 255), to_px(model.x_in, model.y_in),
                           max(2, int(model.radius_in * PIXELS_PER_INCH)))

    pygame.image.save(surface, path)


def main():
    pygame.init()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    map_key = args[0] if args else "map2"
    want, step_in = "Boyz", DEFAULT_STEP_IN
    for flag in flags:
        if flag.startswith("--unit="):
            want = flag.split("=", 1)[1]
        if flag.startswith("--step="):
            step_in = float(flag.split("=", 1)[1])

    battle_map = maps.apply_to_config(maps.get(map_key))
    state = GameState()
    battle_map.build(state)
    settled = []
    placed = H.lay_out(state, H.movers(state), (4.0, config.BOARD_HEIGHT_IN * 0.30), settled)
    enemy = [(sq.name, sq) for sq in H.defenders()]
    enemy_placed = H.lay_out(state, enemy,
                             (config.BOARD_HEIGHT_IN * 0.62, config.BOARD_HEIGHT_IN * 0.88),
                             settled)
    enemy_models = [m for _l, sq in enemy_placed for m in sq.models]
    state.tokens = [m for _l, sq in placed for m in sq.models] + enemy_models

    label, squad = next((l, s) for l, s in placed if want.lower() in l.lower())
    sight = P.Sight(state, enemy_models)
    hidden, point_hidden, anchors = sweep(state, squad, sight, step_in)

    print(f"{map_key}, {label} ({len(squad.models)} models, "
          f"packed spread {formation_layout.packed_spread(squad):.1f}\")")
    print(f"  legal anchors on the board            {len(anchors)}")
    print(f"  anchors whose own POINT is hidden     {len(point_hidden)}")
    print(f"  anchors that hide the WHOLE unit      {len(hidden)}")
    if hidden:
        xs = [a[0] for a, _s in hidden]
        ys = [a[1] for a, _s in hidden]
        print(f"  spanning x {min(xs):.0f}-{max(xs):.0f}, y {min(ys):.0f}-{max(ys):.0f}")
    print(f"  line-of-sight calls {sight.calls}")

    path = os.path.join(os.getcwd(), f"hidden_ground_{map_key}_{want}.png")
    draw(state, squad, hidden, point_hidden, enemy_models, path)
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
