"""Aeldari Seer Council detachment rule: Strands of Fate (the Fate dice pool
and the CP discount it pays for).

None of the six stratagems it discounts exist yet, so the discount is asserted
against throwaway Stratagem objects carrying their real names and CP costs
through the REAL StratagemController - that is the only thing that has to be
right for the pool to work once they land.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from game import strands_of_fate
from game.command_points import CommandPointManager
from game.factions.tau_empire import COMMANDER_FARSIGHT, CRISIS_SUNFORGE, STRIKE_TEAM
from game.puretide import PuretideController
from game.stratagems import Stratagem, StratagemController
from testkit import Checks, Log, TurnTracker, build, script

checks = Checks("Strands of Fate")

PRESENTIMENT = Stratagem("Presentiment of Dread", 1, effect=lambda *a: None)
FOREWARNED = Stratagem("Forewarned", 1, effect=lambda *a: None)
FATE_INESCAPABLE = Stratagem("Fate Inescapable", 2, effect=lambda *a: None)
PSYCHIC_SHIELD = Stratagem("Psychic Shield", 2, effect=lambda *a: None)
NOT_IN_THE_TABLE = Stratagem("Command Re-roll", 1, effect=lambda *a: None)


def pool(faces=None, players=("Player 1",), armed=True):
    """A pool with an exact set of faces, by scripting the dice."""
    p = strands_of_fate.FateDicePool(players=players, game_log=Log(), armed=armed)
    if faces is not None:
        script(*faces)
        p.sync_battle_round(1)
        p.dice["Player 1"] = sorted(faces)  # the script gives these; pin them for clarity
    return p


def controller(fate=None, cp=6, players=("Player 1", "Player 2")):
    log = Log()
    points = CommandPointManager(players=players, game_log=log)
    for player in players:
        points.cp[player] = cp
    sc = StratagemController(game_log=log, command_points=points)
    if fate is not None:
        sc.cost_discounts.append(fate)
    return sc, points, log


# ------------------------------------------------------------ 1. the pool

print("--- 1. the pool ---")

for size, want in (("incursion", 3), ("strike_force", 6), ("onslaught", 9),
                   ("Strike Force", 6), ("nonsense", 6)):
    checks.eq(f"battle size {size!r} rolls", strands_of_fate.fate_dice_for_battle_size(size), want)

script(1, 2, 3, 4, 5, 6)
p = strands_of_fate.FateDicePool(players=("Player 1",), game_log=Log())
p.sync_battle_round(1)
checks.eq("six dice for Strike Force", len(p.pool("Player 1")), 6)
checks.eq("the scripted faces are the pool", p.pool("Player 1"), [1, 2, 3, 4, 5, 6])
checks.true("the roll is logged with each face's stratagem",
            p.game_log.has("Fate dice rolled") and p.game_log.has("Fate Inescapable"))

# The pool is rolled ONCE for the battle - later rounds must not re-roll it,
# which is the one thing that differs from the Battle Focus token account.
script(6, 6, 6, 6, 6, 6)
p.sync_battle_round(2)
p.sync_battle_round(5)
checks.eq("a later battle round does NOT re-roll the pool", p.pool("Player 1"), [1, 2, 3, 4, 5, 6])

empty = strands_of_fate.FateDicePool(players=(), game_log=Log())
script(1, 1, 1, 1, 1, 1)
empty.sync_battle_round(1)
checks.eq("no Seer Council player: no dice at all", empty.pool("Player 1"), [])

checks.eq("the value->stratagem table is the rule's own",
          strands_of_fate.STRATAGEM_BY_FATE_VALUE[4], "Fate Inescapable")
checks.eq("and it round-trips", strands_of_fate.FATE_VALUE_BY_STRATAGEM["Psychic Shield"], 6)
checks.eq("all six values are mapped", sorted(strands_of_fate.STRATAGEM_BY_FATE_VALUE), [1, 2, 3, 4, 5, 6])


# --------------------------------------------------- 2. what a die is worth

print("--- 2. matching ---")

fate = pool([1, 1, 4])
checks.eq("a 1 discounts Presentiment of Dread",
          fate.available_discount("Player 1", PRESENTIMENT), 1)
checks.eq("a 4 discounts Fate Inescapable",
          fate.available_discount("Player 1", FATE_INESCAPABLE), 1)
checks.eq("nothing shows a 2, so Forewarned gets nothing",
          fate.available_discount("Player 1", FOREWARNED), 0)
checks.eq("a stratagem outside the table never matches",
          fate.available_discount("Player 1", NOT_IN_THE_TABLE), 0)
checks.eq("and neither does another player's use",
          fate.available_discount("Player 2", PRESENTIMENT), 0)

checks.eq("asking does not spend anything", fate.pool("Player 1"), [1, 1, 4])
fate.consume("Player 1", PRESENTIMENT)
checks.eq("consuming discards exactly one matching die", fate.pool("Player 1"), [1, 4])
checks.true("and says which die and which stratagem",
            fate.game_log.has("showing 1") and fate.game_log.has("Presentiment of Dread"))
fate.consume("Player 1", FOREWARNED)
checks.eq("consuming with no match discards nothing", fate.pool("Player 1"), [1, 4])

disarmed = pool([1], armed=False)
checks.eq("a disarmed pool offers no discount",
          disarmed.available_discount("Player 1", PRESENTIMENT), 0)
checks.eq("and keeps its die", disarmed.pool("Player 1"), [1])


# ------------------------------------- 3. through the real StratagemController

print("--- 3. the discount, end to end ---")

fate = pool([3, 4, 4])
sc, points, log = controller(fate)
target = build(STRIKE_TEAM, "Player 1", name="Guardians")

checks.eq("a 2CP stratagem with a matching 4 costs 1",
          sc._cost_for("Player 1", FATE_INESCAPABLE, [target], 0), 1)
checks.eq("without a matching die it costs full price",
          sc._cost_for("Player 1", FOREWARNED, [target], 0), 1)
checks.eq("pricing it did not spend a die", fate.pool("Player 1"), [3, 4, 4])

checks.true("using it succeeds", sc.use("Player 1", FATE_INESCAPABLE, [target]))
checks.eq("exactly 1 CP was spent, not 2", points.cp["Player 1"], 5)
checks.eq("and one 4 is gone", fate.pool("Player 1"), [3, 4])

# The die is what makes an otherwise unaffordable use possible - the reason
# holding one back is a real decision (see the module docstring).
broke_fate = pool([6])
sc2, points2, _ = controller(broke_fate, cp=1)
checks.true("1 CP is not enough for a 2CP stratagem without a die",
            not StratagemController(command_points=points2).can_use("Player 1", PSYCHIC_SHIELD, [target]))
checks.true("but the matching 6 makes it affordable",
            sc2.can_use("Player 1", PSYCHIC_SHIELD, [target]))
checks.true("and it goes through", sc2.use("Player 1", PSYCHIC_SHIELD, [target]))
checks.eq("paying exactly 1 CP", points2.cp["Player 1"], 0)

# A use that is refused must not eat the die. Deliberately a 2CP stratagem
# against 0 CP: at 1CP the discount would take the price to zero and the use
# would correctly go through, which is not the case being tested here.
refused_fate = pool([6])
sc3, points3, _ = controller(refused_fate, cp=0)
checks.eq("still 1CP short after the discount, so the use is refused",
          sc3.use("Player 1", PSYCHIC_SHIELD, [target]), False)
checks.eq("and the die survives", refused_fate.pool("Player 1"), [6])

# Never below zero.
free_fate = pool([1])
sc4, points4, _ = controller(free_fate)
checks.eq("a 1CP stratagem with a matching die is free",
          sc4._cost_for("Player 1", PRESENTIMENT, [target], 0), 0)


# ------------------------------------------ 4. the other discount still works

print("--- 4. Puretide coexistence ---")

# The protocol grew a `stratagem` argument for Strands of Fate; Puretide keys
# off the TARGET and must be unaffected by that.
tracker = TurnTracker(first_player="Player 1")
puretide = PuretideController(turn_tracker=tracker, game_log=Log())
sunforge = build(CRISIS_SUNFORGE, "Player 1", name="Sunforge")
farsight = build(COMMANDER_FARSIGHT, "Player 1", name="Farsight")
from game import attached_units
attached_units.attach(farsight, sunforge)

sc5, points5, _ = controller(None)
sc5.cost_discounts.append(puretide)
checks.eq("Puretide still discounts a use aimed at its own unit",
          sc5._cost_for("Player 1", FATE_INESCAPABLE, [sunforge], 0), 1)
checks.eq("and still ignores which stratagem it was",
          sc5._cost_for("Player 1", PRESENTIMENT, [sunforge], 0), 0)
checks.eq("a unit without it gets nothing",
          sc5._cost_for("Player 1", FATE_INESCAPABLE, [target], 0), 2)
checks.true("a discounted use goes through", sc5.use("Player 1", FATE_INESCAPABLE, [sunforge]))
checks.eq("at the reduced price", points5.cp["Player 1"], 5)
checks.eq("and Puretide is now used up this round",
          puretide.available_discount("Player 1", FATE_INESCAPABLE, [sunforge]), 0)


# --------------------------------------------------------- 5. the panel row

print("--- 5. panel ---")

import pygame

from game import config as game_config
from game.ui.game_status_panel import GameStatusPanel

pygame.init()
pygame.display.set_mode((320, 240))

rows = pool([2, 4, 4, 6]).summary_rows("Player 1")
checks.eq("one row per distinct face, low to high",
          [(v, c) for v, c, _ in rows], [(2, 1), (4, 2), (6, 1)])
checks.eq("each row names the stratagem that face can discount",
          [name for _, _, name in rows],
          ["Forewarned", "Fate Inescapable", "Psychic Shield"])
checks.eq("an emptied pool has no rows", pool([]).summary_rows("Player 1"), [])

status = GameStatusPanel()
status_rect = pygame.Rect(0, 0, game_config.RIGHT_PANEL_WIDTH, 700)
tracker8 = TurnTracker(first_player="Player 1")
shown = pygame.Surface((game_config.RIGHT_PANEL_WIDTH, 700))
hidden = pygame.Surface((game_config.RIGHT_PANEL_WIDTH, 700))
full = pool([1, 2, 3, 4, 5, 6])
status.draw(shown, status_rect, tracker8, None, None, None, full)
status.draw(hidden, status_rect, tracker8, None, None, None, None)
checks.true("the Fate dice group is drawn for a Seer Council army",
            pygame.image.tobytes(shown, "RGB") != pygame.image.tobytes(hidden, "RGB"))

no_players = strands_of_fate.FateDicePool(players=(), game_log=Log())
neutral = pygame.Surface((game_config.RIGHT_PANEL_WIDTH, 700))
status.draw(neutral, status_rect, tracker8, None, None, None, no_players)
checks.true("and a game without one renders exactly as before",
            pygame.image.tobytes(neutral, "RGB") == pygame.image.tobytes(hidden, "RGB"))

# The longest stratagem name in a 220px panel is the overflow case this
# project's text_utils exists for - assert it wraps instead of running out.
longest = max(strands_of_fate.STRATAGEM_BY_FATE_VALUE.values(), key=len)
from game.ui.text_utils import wrap_text
wrapped = wrap_text(status.font, f"6 x9  {longest}", game_config.RIGHT_PANEL_WIDTH - 20)
checks.true("every wrapped line fits the panel width",
            all(status.font.size(line)[0] <= game_config.RIGHT_PANEL_WIDTH - 20 for line in wrapped))

# Both players holding dice at once must still lay out (and be labelled).
both = strands_of_fate.FateDicePool(players=("Player 1", "Player 2"), game_log=Log())
script(*([2] * 12))
both.sync_battle_round(1)
two_up = pygame.Surface((game_config.RIGHT_PANEL_WIDTH, 700))
status.draw(two_up, status_rect, tracker8, None, None, None, both)
checks.eq("both pools were rolled", (len(both.pool("Player 1")), len(both.pool("Player 2"))), (6, 6))
checks.true("and the two-player layout renders differently from one player",
            pygame.image.tobytes(two_up, "RGB") != pygame.image.tobytes(shown, "RGB"))


# ------------------------------------------------------------ 6. A/B probe

print("--- 6. A/B probe ---")

# With the discount neutralised the price must go back to full - otherwise a
# green suite would only prove the stratagems were cheap to begin with.
probe_fate = pool([4])
sc6, points6, _ = controller(probe_fate)
saved = strands_of_fate.FateDicePool.available_discount
strands_of_fate.FateDicePool.available_discount = lambda *a, **k: 0
checks.eq("A/B: neutralised, Fate Inescapable is back to 2CP",
          sc6._cost_for("Player 1", FATE_INESCAPABLE, [target], 0), 2)
strands_of_fate.FateDicePool.available_discount = saved
checks.eq("A/B: restored, it is 1CP again",
          sc6._cost_for("Player 1", FATE_INESCAPABLE, [target], 0), 1)

checks.finish()
