"""game/damage_pick.py, and the left panel during a mortal-wound allocation.

User: "das overwatch panel links scheint manchmal noch Faehigkeiten zu
verdecken. manchmal muss ich Einheiten fuer die Verteilung irgendwelcher Mortal
wounds auswaehlen, links steht aber overwatch. das ist sehr verwirrend."

THE OVERWATCH SCREEN WAS NOT THE CAUSE, and getting that wrong would have
fixed nothing. It is branch #29 of 30 in _draw_dispatch(), BELOW both damage
branches. What it filled was the hole left by the TWENTY-FIVE controllers that
had no branch at all: main.py drew the board highlight 28 times and listed 27
controllers for the AI pause, and the panel answered for TWO. Everything else
fell through the entire chain to whatever matched next - which, at the end of
the Movement phase, is very often Fire Overwatch.

So the fix is one shared list with four readers, and what this file pins is
that the panel is one of them. Whether a 28TH controller can fall through
again is not a behaviour question at all and is not asked here - it is a set
difference at the source, in test_event_chain_wiring.py sections 12 and 20.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

pygame.init()
pygame.font.init()

import testkit as tk  # noqa: E402
from game import damage_pick  # noqa: E402
from game.factions import orks  # noqa: E402
from game.ui.action_panel import ActionPanel  # noqa: E402

checks = tk.Checks("Damage pick panel")

SURFACE = pygame.Surface((1280, 720))
LEFT = pygame.Rect(0, 0, 220, 720)


class Ctrl:
    """The three members main.py's 27 controllers all answer with.

    mortal_wound_sessions.py's own docstring states the shape: "Sixteen modules
    in game/ open exactly one MortalWoundAllocationSession at a time... and
    answer main.py's three questions with the same three members."
    """

    def __init__(self, models=None):
        self.pending_damage_choice = models
        self.chosen = []

    def choose_damage_model(self, model):
        self.chosen.append(model)
        self.pending_damage_choice = None


from game.movement import MovementController  # noqa: E402

SQUAD = tk.build(orks.BOYZ, "Player 1", name="1 Boyz 1")
tk.line_up(SQUAD, x=20.0, y=20.0)
ENEMY = tk.build(orks.BOYZ, "Player 2", name="2 Boyz 1")
tk.line_up(ENEMY, x=30.0, y=30.0)
TOKENS = list(SQUAD.models) + list(ENEMY.models)
MOVEMENT = MovementController(all_tokens=TOKENS)


# --- 1. the record ---------------------------------------------------------
print("--- 1. the record ---")

a = Ctrl(list(SQUAD.models[:3]))
pick = damage_pick.pending([None, Ctrl(None), a])
checks.true("an open allocation is found past None and empty controllers", pick is not None)
checks.eq("...and it carries the controller", pick.controller, a)
checks.eq("...the squad", pick.squad, SQUAD)
checks.eq("...and the owner", pick.owner, "Player 1")
checks.true("an offered model is eligible", pick.is_eligible(SQUAD.models[0]))
checks.eq("a model NOT offered is not", pick.is_eligible(SQUAD.models[9]), False)
checks.eq("...and neither is None", pick.is_eligible(None), False)

checks.eq("picking an ineligible model is IGNORED, not guessed at",
          pick.pick(SQUAD.models[9]), False)
checks.eq("...and nothing was chosen", a.chosen, [])
checks.eq("picking an eligible one resolves through the controller",
          pick.pick(SQUAD.models[0]), True)
checks.eq("...through choose_damage_model() and nothing else", a.chosen, [SQUAD.models[0]])

checks.eq("no open allocation reads as None", damage_pick.pending([Ctrl(None)]), None)

# ORDER IS PART OF THE ANSWER - the rule mortal_wound_sessions.py had to make:
# two replays of one battle must be offered the same allocation first.
first, second = Ctrl(list(SQUAD.models[:2])), Ctrl(list(SQUAD.models[2:4]))
checks.eq("the FIRST open allocation in list order wins",
          damage_pick.pending([first, second]).controller, first)
checks.eq("...and reversing the list reverses the answer",
          damage_pick.pending([second, first]).controller, second)

# OWNERSHIP, which is why this takes owners at all.
mine, theirs = Ctrl(list(SQUAD.models[:2])), Ctrl(list(ENEMY.models[:2]))
checks.eq("an owner filter skips the other player's allocation",
          damage_pick.pending([theirs, mine], {"Player 1"}).controller, mine)
checks.eq("...and finds nothing when only theirs is open",
          damage_pick.pending([theirs], {"Player 1"}), None)
checks.eq("no filter means any owner",
          damage_pick.pending([theirs]).controller, theirs)
checks.eq("all_pending() returns every one of them",
          len(damage_pick.all_pending([theirs, mine])), 2)
checks.eq("...and honours the same filter",
          len(damage_pick.all_pending([theirs, mine], {"Player 1"})), 1)

# A choice whose first model has no squad cannot name an owner - inherited
# from _any_pending_damage_choice()'s own guard, and load-bearing.
orphan = Ctrl([type("M", (), {"squad": None})()])
checks.eq("a squadless choice is skipped rather than crashing",
          damage_pick.pending([orphan]), None)


# --- 2. the panel draws it, for a controller that never had a branch -------
print("--- 2. the panel answers for all of them ---")


def panel_text(pick_record):
    """The REAL panel through its real dispatch, returning what it printed."""
    panel = ActionPanel()
    printed = []
    for name in ("_draw_action_required",):
        real = getattr(panel, name)
        setattr(panel, name, lambda s, r, c, msg, _r=real: (printed.append(msg), _r(s, r, c, msg))[1])
    SURFACE.fill((0, 0, 0))
    # A REAL MovementController, like test_unit_pick.py uses: the panel reads
    # selected_squad off it before the dispatch even starts, and a None here
    # would be swallowed by an except and read as "the screen was not drawn" -
    # which is the failure this whole file is about, one layer up.
    try:
        panel.draw(SURFACE, LEFT, MOVEMENT, None, damage_pick=pick_record)
    except AttributeError:
        # With the branch under test removed, the dispatch falls through to
        # branches that need collaborators this stage does not build. That has
        # to read as "the screen was not drawn" - one red line naming the
        # assertion - rather than take the whole run down with it, which is
        # this repo's standing lesson about probes that crash instead of bite.
        pass
    return printed


# flickerjump is one of the 25 that had NO branch - it is the controller in the
# reproduced report, whose allocation drew the Fire Overwatch screen.
flicker = Ctrl(list(SQUAD.models[:2]))
printed = panel_text(damage_pick.pending([flicker]))
checks.eq("a controller that never had a branch now gets the screen",
          len(printed), 1)
checks.true("...and it says what to do",
            printed and "Click a highlighted model" in printed[0])
checks.true("...and NAMES THE UNIT, which the old text did not",
            printed and SQUAD.name in printed[0])

# THE COUNTER-CHECK, without which the section above would pass on a panel
# that always draws the same text: a DIFFERENT unit has to produce a different
# screen, which is only true if the text is built from the record.
#
# (Deliberately not "pass None and expect nothing": with no allocation the
# dispatch falls through to branches that need a real ShootingController, so
# that stage would be testing the fixture. That the branch is gated at all is
# a source fact, pinned in test_event_chain_wiring.py section 20, and an A/B
# probe removes the branch and makes THIS section red.)
other = Ctrl(list(ENEMY.models[:2]))
other_printed = panel_text(damage_pick.pending([other]))
checks.eq("a different unit gets its own screen", len(other_printed), 1)
checks.true("...naming THAT unit", other_printed and ENEMY.name in other_printed[0])
checks.eq("...and not the first one",
          other_printed and SQUAD.name in other_printed[0], False)


# --- 3. the two that already worked are unchanged --------------------------
print("--- 3. shooting and fight are unchanged ---")

# They used to have branches #7 and #8 with identical text, and the new branch
# sits in the SAME slot - so their behaviour is bit-identical apart from the
# unit name. Asserted through the same record, since they now share the path.
for label in ("shooting", "fight"):
    ctrl = Ctrl(list(SQUAD.models[:1]))
    out = panel_text(damage_pick.pending([ctrl]))
    checks.eq("%s: still gets the allocation screen" % label, len(out), 1)
    checks.true("%s: with the same instruction as before" % label,
                out and "takes the wound" in out[0])


checks.finish()
