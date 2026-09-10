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

from game import config, decline_option  # noqa: E402
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


# --- 2b. ...and the ordinary option is BLUE, not grey -----------------------

print("\n2b) the ordinary option is blue")

# User: "bei normalen overlays habe ich jetzt meiste einen grauen knopf und
# einen roten decline knopf. aendere die grauen knoepfe in blau." The red half
# of that pair was fixed one report earlier; the other half stayed a flat grey
# of its own, which said nothing - and this box is where ~90 of the game's
# decisions actually FALL, so it was the one place with no colour code at all.
#
# Measured on PIXELS against the palette, and against GREYNESS separately: an
# overlay that reads button_style but was handed a grey palette would satisfy
# the first claim and not the second, and it is the second that was reported.
blue_fill, = _fills(["Use (1 CP)"])
c.eq("the ordinary option is drawn in the HUD's no-cost blue",
     blue_fill, button_style.BG_NORMAL)
c.true("...which is blue-dominant", blue_fill[2] > blue_fill[0] and blue_fill[2] > blue_fill[1])
c.true("...and is not a grey", len(set(blue_fill)) > 1)

surface, rects = _draw(["Use (1 CP)"])
border = surface.get_at((rects[0].centerx, rects[0].y))[:3]
inside = set(surface.get_at((x, y))[:3]
             for x in range(rects[0].x + 3, rects[0].right - 3)
             for y in range(rects[0].y + 3, rects[0].bottom - 3))
c.eq("its border is the HUD's no-cost border", border, button_style.BORDER_NORMAL)
c.true("...blue-dominant too", border[2] > border[0] and border[2] > border[1])
c.true("...and not a grey", len(set(border)) > 1)
c.true("its label is drawn in the HUD's no-cost text colour",
       button_style.TEXT_NORMAL in inside)
c.true("...and that is not a grey either",
       len(set(button_style.TEXT_NORMAL)) > 1)

# The three OLD values, pinned as gone. Without this the section above passes
# on any palette that happens not to be grey, and what was reported was these
# exact three flat greys.
for name, was in (("fill", (45, 45, 45)), ("border", (120, 120, 120)),
                  ("text", (255, 255, 255))):
    c.true("the old flat-grey %s is gone" % name,
           was not in (dov.BUTTON_BG_COLOR, dov.BUTTON_BORDER_COLOR, dov.BUTTON_TEXT_COLOR))

# ONE blue, so the modal box and the left panel cannot end up with two of them
# meaning one thing - the same reason the decline colours are shared. Pinned
# against what ActionPanel really DRAWS for a no-cost button, not against the
# constant both of them read.
_panel_probe = pygame.Surface((200, 40))
_panel_probe.fill((0, 0, 0))
_probe_rect = pygame.Rect(10, 5, 180, 30)
button_style.draw_button(_panel_probe, _probe_rect, "Move",
                         pygame.font.SysFont(config.FONT_NAME, config.FONT_SIZE, bold=True))
_panel_fill = _panel_probe.get_at((_probe_rect.centerx, _probe_rect.centery + 8))[:3]
c.eq("the panel's no-cost button is the same blue", _panel_fill, blue_fill)



# --- 3. the vocabulary, against the QUELLE ---------------------------------

print("\n3) every literal option label in game/ is classified")

# Every string that is the first element of a tuple inside a call that RAISES
# options - i.e. every option label written as a literal anywhere in game/.
#
# offer_each() IS ON THE LIST, and adding it closed a real blind spot rather
# than accommodating one module: game/per_unit_offer.py builds its options and
# hands them to request() one file away, so every per-unit offer's labels were
# invisible to this sweep. A new spelling of "no" in one of them could not turn
# this section red, which is the whole thing it is for.
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
            if name not in ("request", "request_unit_pick", "offer_each"):
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
    "Keep it", "Keep the card", "Keep the model", "Keep the token",
    "Keep the token - one ability",
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
# The whole ASSIGNMENT, not just the name: "BG_NORMAL" is a prefix of
# "BG_NORMAL_DANGER", so a substring test alone is satisfied by the red.
c.true("...and its BLUE from the same place, for the same reason",
       "BUTTON_BG_COLOR = button_style.BG_NORMAL" in OVERLAY_SRC
       and "BUTTON_BORDER_COLOR = button_style.BORDER_NORMAL" in OVERLAY_SRC
       and "BUTTON_TEXT_COLOR = button_style.TEXT_NORMAL" in OVERLAY_SRC)
c.true("the panel's board-pick screen already draws its skip options red",
       'accent="danger"' in open(os.path.join(GAME_DIR, "ui", "action_panel.py"),
                                 encoding="utf-8").read())

c.finish()
