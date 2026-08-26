"""Unit portraits wherever an overlay talks ABOUT a unit.

User, on a Psychic Shield prompt reading "2 Deff Dread 1 has targeted 1
Guardian Defenders 1 + Farseer + Warlock Conclave. Until the end of the
phase...": "hier will ich auch diese portraits haben. der text ist mir zu
unübersichtlich. ich fände die portraits überall gut, wo von einheiten
gesprochen wird. in allen overlays."

The interesting part is not the drawing - it is working out WHICH units an
overlay is talking about. A DecisionManager prompt is a plain string built at
46 different call sites, so the units are recovered by scanning it for their
own names. That scan is the thing that can quietly go wrong (a name that is a
prefix of another one, a unit that is off the board and so missing from the
squad list it is scanned against), and it is what most of this file tests.

Real squads, a real GameState and a real headless render throughout, with an
A/B on the drawing itself.
"""

import os
import sys

sys.path.insert(0, r"c:\Users\Andre\Desktop\WH40")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

import testkit as tk
from testkit import Checks

from game import attached_units
from game.decision import DecisionManager
from game.game_state import GameState
from game.factions.aeldari import FARSEER, GUARDIAN_DEFENDERS, WARLOCK_CONCLAVE
from game.factions.orks import BOYZ, DEFF_DREAD, GRETCHIN, WARBOSS

c = Checks("overlay unit portraits")

pygame.init()
screen = pygame.display.set_mode((900, 760))

from game.ui import unit_thumbs                       # noqa: E402  (needs a display)
from game.ui.decision_overlay import DecisionOverlay  # noqa: E402
from game.ui.turn_plan_overlay import TurnPlanOverlay # noqa: E402


def build(sheet, owner, name, **kw):
    return tk.build(sheet, owner, name=name, **kw)


# The reported scene: an Ork walker targeting a Farseer-led Guardian mob.
guardians = attached_units.attach(
    build(WARLOCK_CONCLAVE, "Player 1", "1 Warlock Conclave 1"),
    attached_units.attach(build(FARSEER, "Player 1", "1 Farseer 1"),
                          build(GUARDIAN_DEFENDERS, "Player 1", "1 Guardian Defenders 1")))
dread = build(DEFF_DREAD, "Player 2", "2 Deff Dread 1")
mob = attached_units.attach(build(WARBOSS, "Player 2", "2 Warboss 1"),
                            build(BOYZ, "Player 2", "2 Boyz 1", composition_index=1))
grots = build(GRETCHIN, "Player 2", "2 Gretchin 1")
reserve = build(GRETCHIN, "Player 2", "2 Gretchin 2")

state = GameState()
for squad in (guardians, dread, mob, grots):
    for model in squad.models:
        state.add_token(model)
state.add_reserve_squad(reserve)


# ---------------------------------------------------------------------------
# 1. which units a prompt is talking about
# ---------------------------------------------------------------------------

print("--- 1. resolving names ---")

squads = state.all_squads()
c.true("all_squads() includes what is on the board", guardians in squads and dread in squads)
c.true("...and what is in Strategic Reserves, which a prompt can still name",
       reserve in squads)
c.eq("...with no duplicates", len(squads), len(set(id(s) for s in squads)))

prompt = (f'Psychic Shield (1 CP): {dread.name} has targeted {guardians.name}. Until the end '
          f'of the phase it can only be targeted by ranged attacks from within 18" - which may '
          f'force {dread.name} to pick a different target.')
named = unit_thumbs.squads_named_in(prompt, squads)
c.eq("both units are found", [s.name for s in named], [dread.name, guardians.name])
c.true("in the order they appear in the text", named[0] is dread)
c.eq("a unit the prompt does not name is not shown", grots in named, False)
c.eq("no text, no units", unit_thumbs.squads_named_in("", squads), [])
c.eq("a prompt naming nobody finds nobody",
     unit_thumbs.squads_named_in("The Fight phase begins.", squads), [])

# The one hazard the scan has: "2 Boyz 1" is a prefix of "2 Boyz 1 + Warboss".
# The longer name has to win, and the shorter one must not then match what is
# left of it.
plain_boyz = build(BOYZ, "Player 2", "2 Boyz 1", composition_index=1)
c.true("the scene really does contain the prefix hazard",
       mob.name.startswith(plain_boyz.name) and mob.name != plain_boyz.name)
hit = unit_thumbs.squads_named_in(f"{mob.name} charges.", squads + [plain_boyz])
c.eq("the longer name wins, and the shorter one does not also match",
     [s.name for s in hit], [mob.name])
both = unit_thumbs.squads_named_in(f"{plain_boyz.name} and {mob.name} both charge.",
                                   squads + [plain_boyz])
c.eq("...but naming both still finds both", len(both), 2)


# ---------------------------------------------------------------------------
# 2. the thumbnails themselves
# ---------------------------------------------------------------------------

print("--- 2. thumbnails ---")

groups = unit_thumbs.groups_for(named)
c.eq("one group per unit", len(groups), 2)
c.eq("the walker has one thumbnail", len(groups[0]), 1)
c.eq("the attached unit has two - its character and its rank and file",
     len(groups[1]), 2)
c.eq("and the character leads", os.path.basename(groups[1][0]), "Farseer.png")

placed, width, height = unit_thumbs.row_size(named, 400)
c.eq("three cells in all", len(placed), 3)
c.eq("the row is one cell tall", height, unit_thumbs.BOX_PX)
c.true("units are spaced further apart than one unit's own two cells",
       placed[1][1] - placed[0][1] > placed[2][1] - placed[1][1])

# Two units with the same art say nothing twice - the prompt names them both.
twins = unit_thumbs.groups_for([grots, reserve])
c.eq("identical art is not repeated for a second unit", len(twins), 1)

# A narrow row drops WHOLE units rather than half of one.
narrow, _w, _h = unit_thumbs.row_size(named, unit_thumbs.BOX_PX + 4)
c.eq("a row too narrow for both units keeps only the first, whole",
     len(narrow), 1)
c.eq("no art, no row", unit_thumbs.row_size([], 400)[0], [])


# ---------------------------------------------------------------------------
# 3. the overlays actually draw them
# ---------------------------------------------------------------------------

print("--- 3. the overlays ---")

decision = DecisionManager()
decision.request("Player 1", prompt,
                 [("Psychic Shield (1 CP)", None), ("Decline", None)], is_stratagem=True)

cells = []
real_cell = unit_thumbs.draw_cell


def cell_spy(surface, rect, path):
    cells.append((pygame.Rect(rect), path))
    real_cell(surface, rect, path)


def render(fn):
    cells.clear()
    unit_thumbs.draw_cell = cell_spy
    screen.fill((30, 26, 20))
    fn()
    unit_thumbs.draw_cell = real_cell
    return list(cells)


overlay = DecisionOverlay()
drawn = render(lambda: overlay.draw(screen, decision, squads))
c.eq("the decision overlay draws one cell per thumbnail", len(drawn), 3)
c.true("all of them inside the box",
       all(overlay._button_rects and r.left >= overlay._button_rects[0].left - 1 for r, _p in drawn))
c.true("...and above the option buttons",
       all(r.bottom <= overlay._button_rects[0].top for r, _p in drawn))

# A/B: without the squads there is nothing to resolve the names against, and
# the overlay is exactly what it was before - so the checks above are testing
# the new row, not something already on screen.
before = render(lambda: overlay.draw(screen, decision))
c.eq("A/B: with no squads passed, no portraits at all", before, [])
c.true("...and the overlay still draws its buttons", len(overlay._button_rects) == 2)

plan = {
    "turn_intent": "Push the centre.",
    "unit_plans": {
        mob.name: {"role": "advance", "target": guardians.name, "priority": 1, "reason": "trading up"},
        dread.name: {"role": "charge", "target": "", "priority": 2, "reason": "needs 7+"},
        grots.name: {"role": "hold", "target": "P2 Home Objective", "priority": 3, "reason": ""},
    },
}
plan_overlay = TurnPlanOverlay()
plan_overlay.show(plan, squads)
drawn = render(lambda: plan_overlay.draw(screen))
c.eq("the turn plan draws one portrait per unit it lists", len(drawn), 3)
c.true("each is the small size, not the decision overlay's",
       all(r.width == 38 for r, _p in drawn))
c.true("they are stacked down the box, one per entry",
       [r.y for r, _p in drawn] == sorted(r.y for r, _p in drawn))

plan_overlay.show(plan)
drawn = render(lambda: plan_overlay.draw(screen))
c.eq("A/B: with no squads passed, the turn plan is text-only as before",
     drawn, [])

c.finish()
