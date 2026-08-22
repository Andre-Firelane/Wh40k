"""The on-screen log is filterable and scrollable.

User request: "das log unten rechts so wie es momentan ist, bringt mir nicht
viel. ich moechte dort lieber von mir ausgesuchte sachen sehen, anstatt alles.
zuerst moechte ich dort bitte sehen, wenn die ki einen befehl vom planner nicht
ausfuehren konnte, weil alle versuche fehlgeschlagen sind... zb bei bewegung
oder beim aussteigen. ausserdem moechte ich im log scrollen koennen."

Two halves, tested separately:

  * the TAGGING - the engine's own failure sites are the ones that carry
    game_log.FAILED_ORDER, checked by driving the real agent_driver helpers
    rather than by matching on message text;
  * the PANEL - filter chips, scrolling, and the layout, checked against a
    real headless render so a chip that is drawn off-panel (and therefore
    unclickable) fails here rather than in the game.
"""

import os
import sys

sys.path.insert(0, r"c:\Users\Andre\Desktop\WH40")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from testkit import Checks

from game import config, game_log as game_log_module
from game.game_log import GameLog, FAILED_ORDER

c = Checks("log panel (filters + scrolling)")

pygame.init()
pygame.display.set_mode((1600, 900))

from game.ui.log_panel import ALL_FILTER, LogPanel  # noqa: E402  (needs a display)


# ---------------------------------------------------------------------------
# 1. GameLog carries the category without breaking any existing reader
# ---------------------------------------------------------------------------

log = GameLog()
log.add("plain line")
log.add("a failure", category=FAILED_ORDER)
log.add("file only, invisible", file_only=True, category=FAILED_ORDER)

c.eq("only on-screen entries are buffered", len(log.entries), 2)
c.eq("an entry still behaves as its message", log.entries[0], "plain line")
c.true("...including substring tests, which every existing reader uses",
       "failure" in log.entries[1])
c.eq("an untagged entry has no category", log.entries[0].category, None)
c.eq("a tagged entry keeps its category", log.entries[1].category, FAILED_ORDER)
c.true("file_only lines never reach the panel buffer",
       not any("invisible" in e for e in log.entries))

c.true("the buffer holds far more than fits on screen", game_log_module.MAX_ENTRIES >= 200)
big = GameLog()
for i in range(game_log_module.MAX_ENTRIES + 25):
    big.add(f"line {i}")
c.eq("...and is still a ring buffer", len(big.entries), game_log_module.MAX_ENTRIES)
c.eq("...keeping the newest", big.entries[-1], f"line {game_log_module.MAX_ENTRIES + 24}")


# ---------------------------------------------------------------------------
# 2. The engine tags the failures the request named
# ---------------------------------------------------------------------------
#
# Driven through the real helpers, not by asserting on wording: what has to
# hold is that these outcomes are findable under the filter.

from ai import agent_driver  # noqa: E402


class _Squad:
    def __init__(self, name):
        self.name = name


def categories_of(entries):
    return [getattr(e, "category", None) for e in entries]


log = GameLog()
plan = {"2 Boyz 1": {"role": "disembark"}}
agent_driver._log_disembark(log, "Player 2", _Squad("2 Boyz 1"),
                            "could not be placed after disembarking from any facing - stayed aboard",
                            plan, failed=True)
c.eq("a failed disembark is tagged", categories_of(log.entries), [FAILED_ORDER])
c.true("...and still says the plan ordered it",
       "turn plan ordered it to disembark" in log.entries[0])

log = GameLog()
agent_driver._log_disembark(log, "Player 2", _Squad("2 Boyz 1"), "chose to stay embarked", plan)
c.eq("a DECISION to stay aboard is not a failure", categories_of(log.entries), [None])

# The eligibility refusal is a failure only when the plan actually asked for it,
# so the filter does not fill up with "its transport advanced this phase".
log = GameLog()
agent_driver._log_disembark(
    log, "Player 2", _Squad("2 Boyz 1"), "is not eligible to disembark this phase (rule 18.04)",
    plan, failed=agent_driver._plan_ordered_disembark(plan, _Squad("2 Boyz 1")))
c.eq("an ordered-but-ineligible disembark is a failure", categories_of(log.entries), [FAILED_ORDER])

log = GameLog()
agent_driver._log_disembark(
    log, "Player 2", _Squad("2 Boyz 1"), "is not eligible to disembark this phase (rule 18.04)",
    {"2 Boyz 1": {"role": "hold"}},
    failed=agent_driver._plan_ordered_disembark({"2 Boyz 1": {"role": "hold"}}, _Squad("2 Boyz 1")))
c.eq("...but the same line without such an order is not",
     categories_of(log.entries), [None])

# The movement / charge / consolidate sites, read from the source so this
# cannot pass while the tag sits on the wrong call.
import inspect  # noqa: E402

source = inspect.getsource(agent_driver)
for needle in ("advance was illegal, remained stationary instead",
               "Fall Back move was illegal, remained stationary instead",
               "could not complete its charge on",
               "consolidation move was illegal, skipped instead"):
    at = source.index(needle)
    window = source[at:at + 400]
    c.true(f"tagged: {needle[:34]}...", "FAILED_ORDER" in window)


# ---------------------------------------------------------------------------
# 3. The panel filters
# ---------------------------------------------------------------------------

log = GameLog()
for i in range(30):
    log.add(f"ordinary event {i}")
log.add("2 Trukk 1's advance was illegal, remained stationary instead.", category=FAILED_ORDER)
for i in range(10):
    log.add(f"later event {i}")
log.add("2 Boyz 1 could not be placed after disembarking.", category=FAILED_ORDER)

surface = pygame.Surface((1600, 900))
rect = pygame.Rect(1300, 400, 300, config.LOG_HEIGHT)
panel = LogPanel()

c.eq("the panel starts unfiltered", panel.filter, ALL_FILTER)
panel.draw(surface, rect, log)
c.eq("All shows every entry", panel._visible_count, len(log.entries))
c.true("...and something actually fits on screen", panel._shown_count > 0)

chip_keys = [key for key, _rect in panel._chips]
c.eq("there is a chip per category plus All",
     chip_keys, [ALL_FILTER] + [k for k, _l, _w in game_log_module.CATEGORIES])
c.true("every chip is inside the panel",
       all(rect.contains(r) for _k, r in panel._chips))

failed_chip = next(r for k, r in panel._chips if k == FAILED_ORDER)
c.true("clicking a chip is reported as handled", panel.handle_click(failed_chip.center))
c.eq("...and selects that filter", panel.filter, FAILED_ORDER)
panel.draw(surface, rect, log)
c.eq("the failure filter shows only the two failures", panel._visible_count, 2)

c.true("a click on empty panel space is not a chip hit",
       not panel.handle_click((rect.x + 5, rect.bottom - 5)))
c.eq("...and leaves the filter alone", panel.filter, FAILED_ORDER)

all_chip = next(r for k, r in panel._chips if k is ALL_FILTER)
panel.handle_click(all_chip.center)
panel.draw(surface, rect, log)
c.eq("switching back to All restores everything", panel._visible_count, len(log.entries))

# An empty filter has to look empty rather than broken.
empty_log = GameLog()
empty_log.add("nothing has failed yet")
panel.handle_click(failed_chip.center)
panel.draw(surface, rect, empty_log)
c.eq("an empty filter shows nothing", panel._shown_count, 0)
panel.handle_click(all_chip.center)


# ---------------------------------------------------------------------------
# 4. Scrolling
# ---------------------------------------------------------------------------

panel = LogPanel()
panel.draw(surface, rect, log)
fits = panel._shown_count
c.true("the scene has more entries than fit, so scrolling means something",
       len(log.entries) > fits)

c.eq("it starts pinned to the newest", panel.scroll, 0)
c.true("...and is not reported as scrolled", not panel.is_scrolled)

panel.handle_scroll(1)          # wheel up = back through history
c.true("wheel up scrolls back", panel.scroll > 0)
panel.draw(surface, rect, log)
c.true("...and is reported as scrolled", panel.is_scrolled)

panel.handle_scroll(-5)         # wheel down, past the newest
c.eq("wheel down cannot go past the newest entry", panel.scroll, 0)

for _ in range(200):            # far past the oldest
    panel.handle_scroll(1)
    panel.draw(surface, rect, log)
c.eq("scrolling stops at the oldest entry", panel.scroll, len(log.entries) - fits)
c.true("...with something still on screen at the far end", panel._shown_count > 0)

# The reported behaviour that makes scrolling usable: new lines arriving while
# scrolled back must not slide the view forward under the reader.
panel.scroll = 5
panel.draw(surface, rect, log)
top_before = list(reversed(log.entries))[panel.scroll]
log.add("a brand new event")
log.add("and another")
panel.draw(surface, rect, log)
c.eq("new entries do not drag the view along",
     list(reversed(log.entries))[panel.scroll], top_before)

panel.scroll = 0
log.add("newest of all")
panel.draw(surface, rect, log)
c.eq("...but at scroll 0 the panel stays pinned to the newest", panel.scroll, 0)

# Changing filter resets the position: entry 5 of one filter is not entry 5 of
# another, so keeping the number would land somewhere arbitrary.
panel.handle_scroll(2)
panel.handle_click(failed_chip.center)
c.eq("changing the filter returns to the newest", panel.scroll, 0)


# ---------------------------------------------------------------------------
# 5. It renders at the sizes the game actually uses
# ---------------------------------------------------------------------------

# The strip main() actually gives it, plus the old 180px one - the second so a
# future shrink cannot quietly stop fitting anything.
SHIPPED_HEIGHT = config.LOG_HEIGHT
c.true("the shipped log is taller than the old 180px strip", SHIPPED_HEIGHT > 180)

for width in (300, 260, 220, 180):
    for height in (SHIPPED_HEIGHT, 180):
        for filter_key in (ALL_FILTER, FAILED_ORDER):
            p = LogPanel()
            p.filter = filter_key
            r = pygame.Rect(0, 0, width, height)
            s = pygame.Surface((width, height))
            p.draw(s, r, log)
            tag = f"w={width} h={height} {filter_key or 'all'}"
            c.true(f"{tag}: chips stay inside the panel",
                   all(r.contains(cr) for _k, cr in p._chips))
            c.true(f"{tag}: entries still fit below the chips",
                   p._shown_count > 0 or p._visible_count == 0)

# At the shipped height the failure filter shows a useful number of entries -
# the whole point of the request was that one line is not a log.
p = LogPanel()
p.filter = FAILED_ORDER
p.draw(pygame.Surface((config.RIGHT_PANEL_WIDTH, SHIPPED_HEIGHT)),
       pygame.Rect(0, 0, config.RIGHT_PANEL_WIDTH, SHIPPED_HEIGHT), log)
c.true(f"all {p._visible_count} failures fit on screen at once (shown {p._shown_count})",
       p._shown_count == p._visible_count)

c.finish()
