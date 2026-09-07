"""Runtime proof through the REAL main() loop that the hover datacard draws a
weapon's PRINTED characteristic, not the grouping placeholder beside it.

Reported: "in den infos stehen voellig falsche schadenswerte ... shard of the
voiddragon: void spear w6+2 statt 8 / Plagueburst Crawler: entropy cannon w6+1
statt 4 / BLight hauler multimelter w6 statt 3."

A suite already draws the real overlay with real fonts (test_unit_datacard.py
section 9). What it cannot show is that the card main() actually BUILDS, on a
real frame of a real battle, renders those same cells - and "built but never
FED" has shipped in this repo six times. So this reaches into main()'s own
frame, takes the live UnitDatacardOverlay and a live token off the board, and
draws.

WHAT IS STAGED, and why it has to be: the card opens on CTRL+hover or on a
dwell over a token, and a MockAgent run never moves a mouse - `hovered_token`
is None on every frame, so a passive counter reports 0 cards drawn and looks
exactly like a pass (the documented harness limit; an earlier version of this
script did precisely that). The armies are also chosen rather than left to the
defaults, because all three reported weapons have to be ON the board to be
measured at all: the C'tan Shard of the Void Dragon is in the Necron list, the
Plagueburst Crawler and Myphitic Blight-hauler in the Death Guard one.

Everything else is real: the overlay main() constructed, tokens from the live
board, the live screen surface, the real fonts, the real draw path.

--neutralize puts the pre-fix world back (the table reads weapon.damage /
weapon.attacks again) and must report the placeholders.

Harness trap, already paid for once: importing selfplay runs nothing (its
__main__ guard), so it goes via runpy.

Usage:  python verify_weapon_card_values.py [map2]
        python verify_weapon_card_values.py map2 --neutralize
"""

import runpy
import sys

import pygame

from game import config
from game.ui import unit_datacard as udc

MAP = next((a for a in sys.argv[1:] if a.startswith("map")), "map2")
NEUTRALIZE = "--neutralize" in sys.argv

if NEUTRALIZE:
    # The pre-fix table, restored at the source: every column reads the plain
    # int sitting next to the notation.
    udc.printed_characteristic = lambda weapon, which: str(getattr(weapon, which))

# The three weapons from the report, with the row printed in rules/*.md.
WANTED = {
    "Spear of the Void Dragon": ("D", "D6+2"),
    "Entropy Cannon": ("D", "D6+1"),
    "Multi-melta": ("D", "D6"),
}

rows = {}        # weapon name -> the cells the LIVE card rendered
tables = [0]

_real_draw_weapon_table = udc.UnitDatacardOverlay._draw_weapon_table


def spy_weapon_table(self, surface, box_rect, y, title, weapons, skill_for, skill_label):
    """Records each cell the way the row builder does, then lets the real one
    draw - so a row builder that stopped going through printed_characteristic()
    would show up here as the placeholder."""
    tables[0] += 1
    for weapon in weapons:
        rows[weapon.name] = {
            "A": udc.printed_characteristic(weapon, "attacks"),
            "S": udc.printed_characteristic(weapon, "strength"),
            "D": udc.printed_characteristic(weapon, "damage"),
        }
    return _real_draw_weapon_table(self, surface, box_rect, y, title, weapons,
                                   skill_for, skill_label)


udc.UnitDatacardOverlay._draw_weapon_table = spy_weapon_table


def hover_every_token(main_locals):
    """Draw the LIVE card for every token on the board, one after another."""
    card = main_locals.get("unit_datacard")
    state = main_locals.get("state")
    screen = main_locals.get("screen")
    if card is None or state is None or screen is None:
        raise SystemExit("main()'s frame did not carry unit_datacard/state/screen")
    for token in list(state.tokens):
        card.draw(screen, token, (60, 40),
                  transport_controller=main_locals.get("transport_controller"))


def drive(frames, at):
    reached = []
    count = {"n": 0}
    real_flip = pygame.display.flip

    def flip(*args, **kwargs):
        count["n"] += 1
        if count["n"] == at and not reached:
            reached.append(True)
            frame = sys._getframe(1)
            while frame is not None and frame.f_code.co_name != "main":
                frame = frame.f_back
            if frame is None:
                raise SystemExit("could not reach main()'s frame")
            hover_every_token(frame.f_locals)
        return real_flip(*args, **kwargs)

    pygame.display.flip = flip
    sys.argv = ["selfplay.py", MAP, str(frames)]
    try:
        runpy.run_module("selfplay", run_name="__main__")
    except SystemExit:
        pass
    finally:
        pygame.display.flip = real_flip
    return bool(reached)


# Both reported factions on the table at once.
config.PLAYER1_ARMY = "necrons"
config.PLAYER2_ARMY = "death_guard"

if not drive(frames=400, at=300):
    raise SystemExit("FAILED: never reached main()'s frame")

pygame.quit()

print("\n=== hover datacard, through the real main() loop ===")
print("armies: %s vs %s on %s" % (config.PLAYER1_ARMY, config.PLAYER2_ARMY, MAP))
print("mode: %s" % ("NEUTRALIZED (pre-fix)" if NEUTRALIZE else "fixed"))
print("weapon tables drawn on real frames: %d  (%d distinct weapons)"
      % (tables[0], len(rows)))

if not rows:
    raise SystemExit("NOTHING DRAWN - the card never opened, so this proves nothing")

wrong = 0
for name, (column, want) in sorted(WANTED.items()):
    if name not in rows:
        print("  %-30s NOT ON THIS BOARD" % name)
        continue
    got = rows[name][column]
    ok = got == want
    wrong += 0 if ok else 1
    print("  %-30s printed %-6s card shows %-6s  %s"
          % (name, want, got, "OK" if ok else "WRONG"))

missing = [n for n in WANTED if n not in rows]
if missing:
    print("\n%d of the reported weapons were not fielded: %s" % (len(missing), ", ".join(missing)))

raise SystemExit(1 if (wrong or missing) else 0)
