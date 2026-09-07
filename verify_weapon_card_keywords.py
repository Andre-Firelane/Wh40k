"""Runtime proof through the REAL main() loop that the hover datacard's weapon
tables print each weapon's KEYWORDS.

Reported: "in den weapon info tabellen im overlay fehlen die keywords (zb twin
linked oder sustained hits)". The table drew Range/A/BS/S/AP/D and stopped
there, so the half of a weapon row that decides how it behaves was on no
screen anywhere in the game.

A suite already draws the real overlay with real fonts (test_unit_datacard.py
section 10), and the SET of keywords is measured against rules/*.md
(test_weapon_characteristics.py section 5). What neither can show is that the
card main() actually BUILDS, on a real frame of a real battle, puts them on
the screen - and "built but never FED" has shipped in this repo six times. So
this reaches into main()'s own frame, takes the live UnitDatacardOverlay and
live tokens off the board, draws, and then counts KEYWORD_COLOR pixels on the
live screen surface: rendering a string proves a render call, coloured pixels
prove the blit.

WHAT IS STAGED, and why it has to be: the card opens on CTRL+hover or on a
dwell over a token, and a MockAgent run never moves a mouse - `hovered_token`
is None on every frame, so a passive counter reports 0 cards drawn and looks
exactly like a pass (the documented harness limit). The armies are chosen
rather than left to the defaults, because both reported keywords have to be ON
the board to be measured: [SUSTAINED HITS X] comes from the Necron list
(voltaic storm, tesla carbine) and [TWIN-LINKED] from the T'au one (the
Devilfish's twin pulse carbines).

Everything else is real: the overlay main() constructed, tokens from the live
board, the live screen surface, the real fonts, the real draw path.

--neutralize puts the pre-fix world back (the row draws no keyword band) and
must report nothing drawn.

Harness trap, already paid for once: importing selfplay runs nothing (its
__main__ guard), so it goes via runpy.

Usage:  python verify_weapon_card_keywords.py [map2]
        python verify_weapon_card_keywords.py map2 --neutralize
"""

import runpy
import sys

import pygame

from game import config
from game.ui import unit_datacard as udc

MAP = next((a for a in sys.argv[1:] if a.startswith("map")), "map2")
NEUTRALIZE = "--neutralize" in sys.argv

if NEUTRALIZE:
    # The pre-fix world at the source: the row has no keyword band at all.
    udc.UnitDatacardOverlay._weapon_keyword_lines = lambda self, weapon, box_rect=None: []

# What the printed rows of rules/*.md say for two weapons carrying exactly the
# keywords the report named.
WANTED = {
    "Voltaic Storm": ["BLAST", "SUSTAINED HITS 2"],
    "Twin Pulse Carbine": ["ASSAULT", "TWIN-LINKED"],
}

drawn = {}          # weapon name -> the keyword lines the LIVE card produced
tables = [0]
ink = [0]

_real_draw_weapon_table = udc.UnitDatacardOverlay._draw_weapon_table


def spy_weapon_table(self, surface, box_rect, y, title, weapons, skill_for, skill_label):
    tables[0] += 1
    result = _real_draw_weapon_table(self, surface, box_rect, y, title, weapons,
                                     skill_for, skill_label)
    # Recorded AFTER the real draw, so a table that stopped emitting a band
    # cannot be papered over by asking the helper here.
    for weapon in weapons:
        lines = self._weapon_keyword_lines(weapon, box_rect)
        if lines:
            drawn[weapon.name] = lines
    return result


udc.UnitDatacardOverlay._draw_weapon_table = spy_weapon_table


def count_keyword_ink(surface, rect):
    """Keyword-coloured pixels really on the live screen surface."""
    hits = 0
    for y in range(max(0, rect.y), min(surface.get_height(), rect.bottom)):
        for x in range(max(0, rect.x), min(surface.get_width(), rect.right)):
            if surface.get_at((x, y))[:3] == udc.KEYWORD_COLOR:
                hits += 1
    return hits


def hover_every_token(main_locals):
    card = main_locals.get("unit_datacard")
    state = main_locals.get("state")
    screen = main_locals.get("screen")
    if card is None or state is None or screen is None:
        raise SystemExit("main()'s frame did not carry unit_datacard/state/screen")
    for token in list(state.tokens):
        card.draw(screen, token, (60, 40),
                  transport_controller=main_locals.get("transport_controller"))
        if card.last_rect is not None:
            ink[0] += count_keyword_ink(screen, card.last_rect)


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


# Both reported keywords on the table at once.
config.PLAYER1_ARMY = "necrons"
config.PLAYER2_ARMY = "tau"

if not drive(frames=400, at=300):
    raise SystemExit("FAILED: never reached main()'s frame")

pygame.quit()

print("\n=== hover datacard keywords, through the real main() loop ===")
print("armies: %s vs %s on %s" % (config.PLAYER1_ARMY, config.PLAYER2_ARMY, MAP))
print("mode: %s" % ("NEUTRALIZED (pre-fix)" if NEUTRALIZE else "fixed"))
print("weapon tables drawn on real frames: %d" % tables[0])
print("weapons that drew a keyword band:   %d" % len(drawn))
print("keyword-coloured pixels on screen:  %d" % ink[0])

if tables[0] == 0:
    raise SystemExit("NO WEAPON TABLE DRAWN - the card never opened, so this proves nothing")

wrong = 0
for name, want in sorted(WANTED.items()):
    lines = drawn.get(name)
    got = " ".join(lines) if lines else "-"
    ok = lines is not None and all(k in got for k in want)
    wrong += 0 if ok else 1
    print("  %-24s printed %-28s card shows %-28s %s"
          % (name, ", ".join(want), got, "OK" if ok else "MISSING"))

if ink[0] == 0:
    print("  ...and no keyword text reached the screen at all")
    wrong += 1

raise SystemExit(1 if wrong else 0)
