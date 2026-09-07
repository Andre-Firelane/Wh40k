"""Runtime proof through the REAL main() loop that the turn banner is actually
HANDED a faction, and really draws its badge.

User: "es gibt ja den promt, der anzeigt, wer jetzt am zug ist. 'Player 2, Turn
1' baue dort bitte auch das fraktions Logo ein."

A source guard shows main.py passes `faction_keyword=`. It does not show that
the value is anything but None on a real frame - and None is exactly what the
pre-fix banner drew. "Built but never FED" has shipped in this repo six times,
and here it would be invisible: a banner with no badge looks like a banner.

So this drives selfplay.py's real main() loop and reports, per player, which
faction the banner was given and how big a tile faction_badge.draw() was really
asked for. Nothing is staged - the banner opens by itself at the start of every
player turn, so this one CAN be measured passively.

--neutralize drops the keyword on its way in and must report None for everyone.

Harness traps, both already paid for once:
  * importing selfplay runs nothing (its __main__ guard), so it goes via runpy;
  * selfplay REPLACES pygame.event.get at import, so nothing may be hooked onto
    the pump from out here.

Usage:  python verify_turn_badge.py [map2]
        python verify_turn_badge.py map2 --neutralize
"""

import runpy
import sys

from game.ui import faction_badge
from game.ui.turn_start_overlay import TurnStartOverlay

NEUTRALIZE = "--neutralize" in sys.argv
if NEUTRALIZE:
    sys.argv.remove("--neutralize")

seen = {}      # player -> (keyword, logo file or None)
tiles = []     # every tile size faction_badge.draw() was asked for, from the banner

_real_show = TurnStartOverlay.show
_real_draw = faction_badge.draw


def show(self, player, turn_number, faction_keyword=None):
    if NEUTRALIZE:
        faction_keyword = None      # the pre-fix banner: it never knew
    _real_show(self, player, turn_number, faction_keyword=faction_keyword)
    logo = self._logo_path
    seen[player] = (faction_keyword, logo.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
                    if logo else None)


TurnStartOverlay.show = show


def draw_badge(surface, tile_rect, logo_path, active, keyword=None):
    # Only the banner's own tile is of interest here; the Game Status panel
    # draws its badges every frame and would drown the signal.
    if tile_rect.width != 58:
        tiles.append((tile_rect.width, keyword, logo_path is not None))
    return _real_draw(surface, tile_rect, logo_path, active, keyword)


faction_badge.draw = draw_badge
# The banner imported the module, not the function, so patching the attribute
# is enough - and it has to be patched on the module object the banner reads.
import game.ui.turn_start_overlay as banner_module  # noqa: E402

banner_module.faction_badge.draw = draw_badge

sys.argv = ["selfplay.py"] + (sys.argv[1:] or ["map2"])
runpy.run_module("selfplay", run_name="__main__")

print()
print("--- turn banner badge" + (" (NEUTRALIZED)" if NEUTRALIZE else "") + " ---")
if not seen:
    print("  the banner never opened - INCONCLUSIVE")
    raise SystemExit(2)
for player in sorted(seen):
    keyword, logo = seen[player]
    print(f"  {player:9} -> faction {keyword!r}, art {logo!r}")
drawn = [t for t in tiles]
print(f"  banner tiles drawn   : {len(drawn)}")
if drawn:
    width, keyword, had_art = drawn[-1]
    print(f"  last tile            : {width}px, {keyword!r}, artwork={had_art}")
