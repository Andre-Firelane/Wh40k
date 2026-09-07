"""A/B probes for the faction step's grid.

Each probe restores ONE piece of the pre-change world AT THE SOURCE, runs the
affected suites, and puts it back. A probe that does not bite is a finding about
the TEST (CLAUDE.md error class 24).

THREE suites, because tile_screen.py is shared: the faction grid must arrive
without moving the two screens that still lay out a single row. A probe that
reddens test_map_select.py is telling you the shared skeleton changed for
everyone, which was the main risk here.
"""

import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
ARMY = os.path.join(ROOT, "game", "ui", "army_select.py")
TILES = os.path.join(ROOT, "game", "ui", "tile_screen.py")

SUITES = {
    "army": (os.path.join(ROOT, "test_army_select.py"), 331),
    "map": (os.path.join(ROOT, "test_map_select.py"), 154),
    "biome": (os.path.join(ROOT, "test_biomes.py"), 100),
}


def clear_cache():
    for root, dirs, _f in os.walk(ROOT):
        for d in list(dirs):
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
                dirs.remove(d)


def run(path):
    out = subprocess.run([sys.executable, path], capture_output=True, text=True,
                         cwd=ROOT).stdout
    for line in out.splitlines():
        if "checks passed" in line:
            got, total = line.strip().split()[0].split("/")
            return int(got), int(total)
    return -1, -1


def probe(label, old, new, path=ARMY):
    src = open(path, encoding="utf-8").read()
    if src.count(old) != 1:
        print(f"  SKIP {label}: anchor found {src.count(old)}x")
        return
    open(path, "w", encoding="utf-8").write(src.replace(old, new))
    try:
        clear_cache()
        results = {k: run(p) for k, (p, _b) in SUITES.items()}
    finally:
        open(path, "w", encoding="utf-8").write(src)
    bit = any(results[k][0] < SUITES[k][1] for k in results)
    shown = "  ".join(f"{k} {results[k][0]}/{SUITES[k][1]}" for k in SUITES)
    print(f"  {'BITES' if bit else '*** DID NOT BITE ***':22} {shown}  {label}")


clear_cache()
print("baseline: " + "  ".join(f"{k} {run(p)[0]}/{b}" for k, (p, b) in SUITES.items()))

# 1. THE WHOLE PRE-CHANGE WORLD: one row, top-aligned, cards at their minimum.
probe(
    "the whole pre-change world (a single row of minimum-height cards)",
    """        floor = min(area.height, self._faction_tile_min_height())""",
    """        floor = min(area.height, self._faction_tile_min_height())
        per_page = self.fit_page(area.width)
        page_items = self.page_items
        rects = ts.tile_rects(area, per_page, len(page_items), floor)
        self.tiles = [_Tile(i, r, [], [], []) for i, r in zip(page_items, rects)]
        return self.tiles""",
)

# 2. Grid capacity, but still ONE row of rects - the layout half undone while
#    the paging half stands. The pager would go quiet and the extra tiles would
#    be laid out off the right-hand edge.
probe(
    "capacity for a grid, but the rects stay in one row",
    "        rects = ts.tile_rects(block, columns, len(page_items), height)",
    "        rects = [pygame.Rect(block.x + i * (block.width // max(1, columns) + ts.TILE_GAP),\n"
    "                             block.y, block.width // max(1, columns) - ts.TILE_GAP, height)\n"
    "                 for i in range(len(page_items))]",
)

# 3. Rows uncounted: capacity falls back to one row, so five factions page
#    again. This is the line that buys "paginierung erst sehr spaet".
probe(
    "only one row of capacity",
    "        rows = rows_that_fit(area_height, tile_height)",
    "        rows = 1",
    path=TILES,
)

# 4. The block pinned to the top of the band instead of centred - the "one row
#    nailed to the ceiling over a void" look the report is about.
probe(
    "the grid is pinned to the top, not centred",
    "    top = area.y + max(0, (area.height - block) // 2)",
    "    top = area.y",
    path=TILES,
)

# 5. Cards never grow: the grid arrives but "die volk kacheln sehr klein"
#    stands.
probe(
    "the cards stay at their minimum height",
    "        height = self._faction_tile_height(area.height, rows, floor)",
    "        height = floor",
)

# 6. Cards grow WITHOUT a cap - they would swell to fill half the band each,
#    which is the "mostly empty box" this screen's own layout rule rules out.
probe(
    "the growth is uncapped",
    "        ceiling = TILE_PAD * 2 + FACTION_LOGO_MAX_PX\n"
    "        return max(floor, min(share, max(floor, ceiling)))",
    "        return max(floor, share)",
)

# 7. The badge does not grow with the card, so every added pixel is padding.
probe(
    "the badge does not follow the card's height",
    "        logo_px = max(LOGO_PX, min(FACTION_LOGO_MAX_PX, rect.height - 2 * TILE_PAD))",
    "        logo_px = LOGO_PX",
)

# 8. Column count taken from the page total instead of the width - five
#    factions would come out five columns wide and each card a fifth too small,
#    which is the clamp fit_page() has always carried.
probe(
    "columns come from the page size rather than the window",
    "        columns = max(1, min(tiles_that_fit(area_width), len(self.items)))",
    "        columns = max(1, len(self.items))",
    path=TILES,
)

# 9. THE SHARED SKELETON. tile_rects() wrapping must be invisible to the two
#    screens that pass count <= per_row; breaking the single-row arithmetic has
#    to redden the map picker, or nothing here is guarding it.
probe(
    "the shared row arithmetic is broken for everyone",
    "    width = (area.width - TILE_GAP * (per_row - 1)) // max(1, per_row)",
    "    width = (area.width - TILE_GAP * per_row) // max(1, per_row)",
    path=TILES,
)
