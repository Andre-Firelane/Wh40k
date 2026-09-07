"""The "no" option is RED, in the modal overlay too - not only in the panel.

User: "Decline Buttons auch in den overlays rot einfaerben."

game/ui/button_style.py has said for a long time what red means in this HUD:
"this button abandons/declines the current action". ActionPanel honoured it -
every Cancel, every "Decline Charge" - but DecisionOverlay, which carries ~90
of this game's break points, painted every option the same flat grey, so the
one place a decision is actually MADE was the one place the colour code did
not apply.

TWO HALVES, and either alone is worthless:

  * the drawing: a decline option comes out in button_style's danger palette
    and a real choice does not (measured on PIXELS - a test that only asked the
    predicate would pass against an overlay that never reads it);
  * the vocabulary: game/decline_option.py has to recognise how this codebase
    spells "no". Section 3 is a set difference over the QUELLE - every literal
    option label in game/ - so a NEW way of saying it turns this red instead of
    quietly drawing another grey Decline, which no behaviour test can see
    because that label does not exist yet.

Run: python test_decline_buttons.py
"""

import ast
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((400, 300))

from game import decline_option  # noqa: E402
from game.decision import DecisionManager  # noqa: E402
from game.ui import button_style, decision_overlay as dov  # noqa: E402
from game.ui.decision_overlay import DecisionOverlay  # noqa: E402
from testkit import Checks  # noqa: E402

c = Checks("decline buttons")

HERE = os.path.dirname(os.path.abspath(__file__))
GAME_DIR = os.path.join(HERE, "game")


# --- 1. the predicate -------------------------------------------------------

print("\n1) what counts as a decline")

for label in ("Decline", "Decline Charge", "Decline Consolidation", "Cancel",
              "Stay put", "Stay on the battlefield", "Keep it", "Keep result",
              "Keep the token", "Keep the token - one ability", "Keep the card",
              "Keep the Advance roll (4)", "Do not use it", "Don't use it",
              "Do not mark", "No more", "Save it for later",
              "Leave them unguarded", "Leave the pool alone"):
    c.true("%r declines" % label, decline_option.is_decline(label))

# A real two-way choice has no "no" branch, and painting half of one red would
# say something false about it.
for label in ("Use (1 CP)", "Fire Overwatch (1 CP)", "[LETHAL HITS]",
              "[SUSTAINED HITS 1]", "Spend a token - two abilities",
              "Make the move", "Go into Strategic Reserves", "Withdraw",
              "Shoot back", "I place first", "My opponent places first",
              "Re-roll", "Discard and redraw", "Assign guards"):
    c.true("%r does not" % label, not decline_option.is_decline(label))

c.true("an empty label is not a decline", not decline_option.is_decline(""))
c.true("...nor is None, rather than throwing", not decline_option.is_decline(None))
c.true("leading space does not hide it", decline_option.is_decline("  Decline"))


# --- 2. the overlay paints it ----------------------------------------------

print("\n2) the modal box draws it red")


def _draw(labels):
    """The overlay, drawn for real, plus its button rects - measured off the
    surface rather than asked of the predicate, because an overlay that ignores
    the predicate would pass the latter."""
    dm = DecisionManager()
    dm.request("Player 1", "Test prompt", [(lab, None) for lab in labels])
    surface = pygame.Surface((900, 600))
    surface.fill((0, 0, 0))
    overlay = DecisionOverlay()
    overlay.draw(surface, dm)
    return surface, overlay._button_rects


def _fills(labels):
    surface, rects = _draw(labels)
    return [surface.get_at((r.centerx, r.y + 3))[:3] for r in rects]


fills = _fills(["Use (1 CP)", "Decline"])
c.eq("the overlay drew both options", len(fills), 2)
c.eq("the ordinary option keeps the plain fill", fills[0], dov.BUTTON_BG_COLOR)
c.eq("the decline option is drawn in the danger fill", fills[1], button_style.BG_NORMAL_DANGER)
c.true("...which is red-dominant", fills[1][0] > fills[1][1] and fills[1][0] > fills[1][2])
c.true("...and the two are not the same colour", fills[0] != fills[1])

# The border and the text too, so a colour-blind reader is not left with a fill
# a few points darker than its neighbour.
surface, rects = _draw(["Use (1 CP)", "Decline"])


def _border_and_row(index):
    """The button's border pixel, and every colour inside it - the label is
    antialiased, so one scan line can miss the glyph cores entirely."""
    rect = rects[index]
    border = surface.get_at((rect.centerx, rect.y))[:3]
    inside = set(surface.get_at((x, y))[:3]
                 for x in range(rect.x + 3, rect.right - 3)
                 for y in range(rect.y + 3, rect.bottom - 3))
    return border, inside


border, row = _border_and_row(1)
c.eq("the decline border is the danger border", border, button_style.BORDER_NORMAL_DANGER)
c.true("...and its label is drawn in the danger text colour",
       button_style.TEXT_NORMAL_DANGER in row)
border0, row0 = _border_and_row(0)
c.eq("an ordinary option keeps the plain border", border0, dov.BUTTON_BORDER_COLOR)
c.true("...and the plain text colour", dov.BUTTON_TEXT_COLOR in row0)

# Position is not what decides it: a decline first and a real option after it
# must still come out the right way round.
flipped = _fills(["Stay put", "Make the move"])
c.eq("a decline that is not last is still red", flipped[0], button_style.BG_NORMAL_DANGER)
c.eq("...and the option after it is not", flipped[1], dov.BUTTON_BG_COLOR)

# A list of nothing but real choices gets no red at all - without this the
# section passes against an overlay that paints every button red.
neither = _fills(["[LETHAL HITS]", "[SUSTAINED HITS 1]"])
c.true("a genuine two-way choice gets no red",
       all(fill == dov.BUTTON_BG_COLOR for fill in neither))


# --- 3. the vocabulary, against the QUELLE ---------------------------------

print("\n3) every literal option label in game/ is classified")

# Every string that is the first element of a tuple inside a request() call -
# i.e. every option label written as a literal anywhere in game/.
LITERAL_LABELS = set()
for root, _dirs, files in os.walk(GAME_DIR):
    for filename in sorted(files):
        if not filename.endswith(".py"):
            continue
        tree = ast.parse(open(os.path.join(root, filename), encoding="utf-8").read())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = (node.func.attr if isinstance(node.func, ast.Attribute)
                    else getattr(node.func, "id", ""))
            if name not in ("request", "request_unit_pick"):
                continue
            args = list(node.args) + [kw.value for kw in node.keywords if kw.arg == "options"]
            for arg in args:
                for sub in ast.walk(arg):
                    if (isinstance(sub, ast.Tuple) and sub.elts
                            and isinstance(sub.elts[0], ast.Constant)
                            and isinstance(sub.elts[0].value, str)):
                        LITERAL_LABELS.add(sub.elts[0].value)

c.true("the sweep found the option labels at all", len(LITERAL_LABELS) > 30)

# The full expected classification. A new spelling of "no" that nobody teaches
# game/decline_option.py lands in the first list and turns this red.
EXPECTED_DECLINES = {
    "Cancel", "Decline", "Do not mark", "Do not use it", "Don't use it",
    "Keep it", "Keep the card", "Keep the token", "Keep the token - one ability",
    "Leave the pool alone", "Leave them unguarded", "No more", "Save it",
    "Save it for later", "Stay on the battlefield", "Stay put",
}
got = set(label for label in LITERAL_LABELS if decline_option.is_decline(label))
c.eq("no new way of spelling 'no' has appeared unclassified",
     sorted(EXPECTED_DECLINES - got), [])
c.eq("...and nothing that is a real choice was painted red",
     sorted(got - EXPECTED_DECLINES), [])


# --- 4. one definition ------------------------------------------------------

print("\n4) one definition, read by the overlay")

OVERLAY_SRC = open(os.path.join(GAME_DIR, "ui", "decision_overlay.py"), encoding="utf-8").read()
c.true("the overlay asks decline_option rather than matching strings itself",
       "decline_option.is_decline(" in OVERLAY_SRC)
c.true("...and takes its red from button_style, not a second one of its own",
       "button_style.BG_NORMAL_DANGER" in OVERLAY_SRC
       and "button_style.BORDER_NORMAL_DANGER" in OVERLAY_SRC
       and "button_style.TEXT_NORMAL_DANGER" in OVERLAY_SRC)
c.true("the panel's board-pick screen already draws its skip options red",
       'accent="danger"' in open(os.path.join(GAME_DIR, "ui", "action_panel.py"),
                                 encoding="utf-8").read())

c.finish()
