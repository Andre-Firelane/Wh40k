"""Detachment Stratagems: the corpus reader, the reader overlay, and the
dwell tooltip on a Stratagem button.

User: "was noch fehlt sind die Infos zu den detachment stratagems. die gehören
zum einen in die Army Rules overlays. zum anderen sollte das stratagems
vollständig angezeigt werden wenn man ein paar Sekunden über einen stratagems
Knopf hovert."

Two halves that share one source. The "## Stratagems" section of a detachment
file was deliberately skipped when the reader was built ("those are pages of
text that belong on a screen of their own"); this is that screen, plus a box
beside the button that spends the CP.

WHAT IS WORTH GUARDING is not "text appeared". It is:
  * that the NAME on a button resolves to the RIGHT printed Stratagem - the
    panel shortens some of them, and showing the wrong rules would look
    exactly like showing the right ones;
  * that a Stratagem with no printed entry draws NOTHING rather than an empty
    box;
  * that the dwell really is a dwell - a tooltip that opens on contact would
    flash across a column of buttons.
"""

import io
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

pygame.init()
pygame.font.init()
pygame.display.set_mode((1, 1))

import testkit as tk  # noqa: E402
from game import army_lists, rules_text  # noqa: E402
from game.ui import action_panel as ap  # noqa: E402
from game.ui import rules_body  # noqa: E402
from game.ui import stratagem_tooltip as st  # noqa: E402
from game.ui.army_rules_overlay import ArmyRulesOverlay  # noqa: E402
from game.ui.stratagem_tooltip import StratagemTooltip  # noqa: E402

c = tk.Checks("detachment stratagems")

W, H = 1600, 900
# ONE list per shipped faction, derived rather than written down: this block
# cares that every faction can be reached, not which of its lists answers.
# A hardcoded tuple here goes stale whenever a list is retired, and does it
# as a SystemExit out of army_lists.get() rather than as a red line.
from game import army_lists as _al  # noqa: E402
SHIPPED = tuple(f.lists[0].key for f in _al.factions())


def read(path):
    return io.open(path, encoding="utf-8").read()


# --- 1. the corpus reader ---------------------------------------------------
print("\n=== 1. reading the corpus ===")

seer = rules_text.detachment_stratagems("AELDARI", "Seer Council")
c.eq("a detachment's Stratagems are found", len(seer), 6)
c.eq("...named as printed", [s.name for s in seer][:2],
     ["PRESENTIMENT OF DREAD", "FOREWARNED"])
c.eq("...with the cost split off the heading, not left in the name",
     [s.cost for s in seer], ["1CP"] * 6)
c.eq("...and put back for display",
     seer[0].heading if seer else None, "PRESENTIMENT OF DREAD - 1CP")

# A guard, not decoration: a regression that returns NO Stratagems must make
# these checks red rather than IndexError out of the suite - a crash hides
# which check broke. Fifth time this lesson has been paid for in this repo.
body = seer[1] if len(seer) > 1 else rules_text.RuleStratagem("", None, [])
kinds = [line.kind for line in body.lines]
c.true("a Stratagem carries its classified lines", len(body.lines) >= 4)
c.true("...its subtitle", "subtitle" in kinds)
c.eq("...and its printed label rows",
     sorted({line.label for line in body.lines if line.kind == "label"}),
     ["EFFECT", "TARGET", "WHEN"])
c.true("the subtitle's asterisks are gone from what gets drawn",
       all("*" not in text
           for line in body.lines if line.kind == "subtitle"
           for text, _bold in line.runs))
# ...but NOT from the flat view, which is defined as "what _paragraphs() has
# always emitted" and must not move. That split is what let the parser learn
# about italics at all without disturbing army_rule_text().
c.true("...and still present in the flat text, which may not move",
       all(line.text.startswith("*") and line.text.endswith("*")
           for line in body.lines if line.kind == "subtitle"))

c.eq("an unknown detachment reads as nothing, not a crash",
     rules_text.detachment_stratagems("AELDARI", "No Such Detachment"), [])
c.eq("...and an unknown faction likewise",
     rules_text.detachment_stratagems("NO SUCH", "Seer Council"), [])

# Every shipped list can be read, so this is not green on one lucky file.
_totals = {}
for key in SHIPPED:
    entry = army_lists.get(key)
    _totals[key] = sum(len(rules_text.detachment_stratagems(entry.faction_keyword, d))
                       for d in entry.detachments)
c.true("every shipped list's detachments have printed Stratagems",
       all(count > 0 for count in _totals.values()))
c.eq("...36 of them in total", sum(_totals.values()), 36)


# --- 2. name lookup: the half that could silently show the WRONG rules ------
print("\n=== 2. resolving a button label to a Stratagem ===")

AELDARI = ("Seer Council", "Path of the Outcast")
def resolved(faction, detachments, name):
    """The resolved NAME or None - never a bare attribute access, so a lookup
    that regresses to None turns these checks red instead of crashing."""
    found = rules_text.stratagem_named(faction, detachments, name)
    return found.name if found is not None else None


c.eq("an exact name resolves", resolved("AELDARI", AELDARI, "Forewarned"), "FOREWARNED")
c.eq("...case and apostrophe folded like every other name in this module",
     resolved("AELDARI", AELDARI, "Isha's Fury"), "ISHA'S FURY")

# The panel shortens some names to fit a 220px button. A suffix match is what
# recovers those, and it is only allowed when it is UNAMBIGUOUS.
c.eq("a shortened name resolves by its unique suffix",
     resolved("NECRONS", ("Awakened Dynasty",), "Sudden Storm"),
     "PROTOCOL OF THE SUDDEN STORM")
c.eq("...and so does a dropped leading article",
     resolved("T'AU EMPIRE", ("Retaliation Cadre",), "Arro'kon Protocol"),
     "THE ARRO'KON PROTOCOL")
c.eq("a name the corpus does not carry resolves to nothing",
     rules_text.stratagem_named("AELDARI", AELDARI, "Command Re-roll"), None)
c.eq("...and so does an empty one",
     rules_text.stratagem_named("AELDARI", AELDARI, ""), None)

# THE COUNTER-CHECK: an ambiguous suffix must refuse rather than pick one.
# Showing the wrong Stratagem's rules is worse than showing none, because
# nothing on screen would say it was the wrong one.
_real = rules_text.detachment_stratagems
try:
    twins = [rules_text.RuleStratagem("ALPHA STRIKE", "1CP", []),
             rules_text.RuleStratagem("OMEGA STRIKE", "1CP", [])]
    rules_text.detachment_stratagems = lambda *a, **k: twins
    c.eq("an AMBIGUOUS suffix refuses instead of guessing",
         rules_text.stratagem_named("X", ("Y",), "Strike"), None)
    c.eq("...while the same lookup on one of them still works",
         resolved("X", ("Y",), "Alpha Strike"), "ALPHA STRIKE")
finally:
    rules_text.detachment_stratagems = _real

# Every label the panel can draw is checked against the corpus, so a renamed
# Stratagem shows up here rather than as a tooltip that quietly stopped
# opening. Derived with the panel's OWN extractor, not a copy of it.
c.eq("the label extractor takes the name and drops cost and summary",
     ap._stratagem_name_in("Sudden Storm (1 CP) - ranged weapons gain [ASSAULT]"),
     "Sudden Storm")
c.eq("...and copes with a label that is only a name and a cost",
     ap._stratagem_name_in("Epic Challenge (1CP)"), "Epic Challenge")
c.eq("...and with nothing at all", ap._stratagem_name_in(None), "")

_PANEL_SRC = read(os.path.join("game", "ui", "action_panel.py"))
c.true("the panel records its Stratagem buttons where it DRAWS them",
       'if accent == "stratagem":' in _PANEL_SRC
       and "self._stratagem_buttons.append((drawn, _stratagem_name_in(label)))" in _PANEL_SRC)
c.true("...and does not widen self._buttons, which handle_click destructures",
       "for rect, callback in self._buttons:" in _PANEL_SRC)


# --- 3. the Stratagems in the army-rules reader -----------------------------
print("\n=== 3. in the reader ===")

ov = ArmyRulesOverlay()
ov.show({"Player 1": "aeldari"}, "Player 1")
texts = [b.text for b in ov._blocks]
kinds = [b.kind for b in ov._blocks]

c.true("the reader has a STRATAGEMS divider", "STRATAGEMS" in texts)
c.eq("...and every printed Stratagem of every fielded detachment",
     sum(1 for k in kinds if k == "stratagem"), 9)
c.true("...each with its name and cost",
       any(t == "PRESENTIMENT OF DREAD - 1CP" for t in texts))
c.true("...and its printed WHEN/TARGET/EFFECT",
       {"WHEN", "TARGET", "EFFECT"} <=
       {b.label for b in ov._blocks if b.kind == "label"})
c.true("both detachments contribute",
       any("NOMADS OF THE HIDDEN WAY" in t for t in texts)
       and any("PRESENTIMENT" in t for t in texts))
c.true("no markdown marker reaches the screen",
       not any("**" in b.text for b in ov._blocks if b.kind != "subtitle"))

# A Stratagem name is drawn in the accent its BUTTON uses, so the two read as
# one idea. Pinned against button_style rather than as a literal.
from game.ui import button_style  # noqa: E402
c.eq("a Stratagem name uses the button's own accent",
     rules_body.STRATAGEM_NAME_COLOR, button_style.BORDER_HOVER_STRATAGEM)

surface = pygame.Surface((W, H))
ov.draw(surface)
rect = ov.panel_rect(pygame.Rect(0, 0, W, H))
c.true("the reader still fits its measure with the Stratagems in it",
       ov._text_width(rect) <= 560)
c.eq("...and what was predicted is still what was laid down",
     ov._content_height(rect),
     ov._last_content_bottom - (rect.y + 44 + 6))


# --- 4. the tooltip -------------------------------------------------------
print("\n=== 4. the tooltip ===")

tip = StratagemTooltip()
blocks = tip.blocks_for("AELDARI", AELDARI, "Forewarned")
c.true("it finds the printed text for a button's name", len(blocks) > 3)
# Read through a guard for the same reason section 1 does: a regression that
# finds nothing must turn these red, not IndexError the suite out.
_head = blocks[0] if blocks else rules_body.Block("none", "")
c.eq("...headed by the Stratagem itself", _head.kind, "stratagem")
c.eq("...naming it with its cost", _head.text, "FOREWARNED - 1CP")
c.eq("a Stratagem with no printed entry yields nothing",
     tip.blocks_for("AELDARI", AELDARI, "Command Re-roll"), [])

surface = pygame.Surface((W, H))
surface.fill((30, 40, 55))
SCREEN = pygame.Rect(0, 0, W, H)


def on_screen(box):
    """None counts as "not on screen" rather than exploding: a regression that
    draws nothing must make these red, not raise out of the suite."""
    return box is not None and SCREEN.contains(box)


drawn = tip.draw(surface, "AELDARI", AELDARI, "Forewarned", (400, 300))
c.true("it draws a box",
       drawn is not None and drawn.width > 200 and drawn.height > 80)
c.true("...on screen", on_screen(drawn))
c.eq("nothing printed, nothing drawn - an empty box is worse than none",
     tip.draw(surface, "AELDARI", AELDARI, "Command Re-roll", (400, 300)), None)
c.eq("...and last_rect says so too", tip.last_rect, None)

# It must stay on screen from any corner, or the one at the bottom of a long
# panel would hang off the edge exactly when it is longest.
for pos in ((W - 10, H - 10), (5, H - 10), (W - 10, 5), (5, 5)):
    box = tip.draw(surface, "AELDARI", AELDARI, "Forewarned", pos)
    c.true(f"the box stays on screen from {pos}", on_screen(box))

# The clip is restored, or everything drawn after it would be cut to this box.
guard = pygame.Rect(3, 4, 500, 500)
surface.set_clip(guard)
tip.draw(surface, "AELDARI", AELDARI, "Forewarned", (100, 100))
c.eq("the surface clip is restored", surface.get_clip(), guard)


# --- 5. the DWELL, not a hover --------------------------------------------
print("\n=== 5. dwell ===")

panel = ap.ActionPanel()
BUTTON = pygame.Rect(10, 100, 200, 30)
OTHER = pygame.Rect(10, 140, 200, 30)


def arm(rects_names):
    panel._stratagem_buttons = list(rects_names)


arm([(BUTTON, "Forewarned"), (OTHER, "Psychic Shield")])
inside = BUTTON.center
c.eq("resting is not yet asking", panel.update_tooltip(inside, False, 0), None)
c.eq("...still not, just short of the delay",
     panel.update_tooltip(inside, False, ap.STRATAGEM_TIP_DELAY_MS - 1), None)
c.eq("...and then it opens",
     panel.update_tooltip(inside, False, ap.STRATAGEM_TIP_DELAY_MS), "Forewarned")
c.eq("...naming the button it belongs to", panel.tooltip_rect, BUTTON)

# Moving beyond the jitter allowance restarts the dwell - but staying within it
# does not, or a hand resting on a mouse would never trigger it at all.
drifted = (inside[0] + ap.STRATAGEM_TIP_JITTER_PX, inside[1])
c.eq("a hand's drift does not restart the dwell",
     panel.update_tooltip(drifted, False, ap.STRATAGEM_TIP_DELAY_MS + 1), "Forewarned")
moved = (inside[0] + ap.STRATAGEM_TIP_JITTER_PX + 5, inside[1])
c.eq("...but a real move does",
     panel.update_tooltip(moved, False, ap.STRATAGEM_TIP_DELAY_MS + 2), None)

arm([(BUTTON, "Forewarned"), (OTHER, "Psychic Shield")])
c.eq("moving to another button starts ITS own dwell",
     panel.update_tooltip(OTHER.center, False, 10_000), None)
c.eq("...which then opens on that one",
     panel.update_tooltip(OTHER.center, False, 10_000 + ap.STRATAGEM_TIP_DELAY_MS),
     "Psychic Shield")

c.eq("pressing a button closes it - you are clicking, not asking",
     panel.update_tooltip(OTHER.center, True, 20_000), None)
c.eq("leaving the buttons closes it",
     panel.update_tooltip((900, 900), False, 30_000), None)
c.eq("a non-stratagem button has no tooltip", panel.stratagem_at((900, 900)), None)

# The rects are rebuilt every frame, so the dwell has to key on the NAME.
# Comparing rect identity would reset the timer every frame and the tooltip
# would never open at all.
# Both the rect AND the name are rebuilt every frame in the real panel: the
# labels are f-strings, so _stratagem_name_in() hands back a NEW string object
# each time. A dwell that compared either by identity would restart every
# frame and never open. Modelled with a freshly built string rather than a
# literal, because Python interns literals and the check would pass on
# identity comparison by accident.
def fresh_name():
    return "".join(["Fore", "warned"])


arm([(pygame.Rect(BUTTON), fresh_name())])
panel.update_tooltip(inside, False, 40_000)
arm([(pygame.Rect(BUTTON), fresh_name())])
c.eq("a rebuilt rect and a rebuilt name do not restart the dwell",
     panel.update_tooltip(inside, False, 40_000 + ap.STRATAGEM_TIP_DELAY_MS),
     "Forewarned")

c.true("the dwell is longer than the datacard's - a panel is buttons to click"
       " past, a board is models to ask about",
       ap.STRATAGEM_TIP_DELAY_MS > 900)


# --- 6. wiring: main() really polls and draws it ---------------------------
print("\n=== 6. wiring ===")

MAIN = read("main.py")
c.true("main() builds the tooltip", "stratagem_tooltip = StratagemTooltip()" in MAIN)
c.true("...polls the panel for it", "action_panel.update_tooltip(" in MAIN)
c.true("...with an injected clock, like the datacard", "pygame.time.get_ticks()," in MAIN)
c.true("...and draws it", "stratagem_tooltip.draw(" in MAIN)
# Beside the datacard, so it inherits the same modal suppression: a box drawn
# over a prompt that has to be answered first is the bug that list exists for.
c.true("a modal suppresses it", "if not _modal_up else None" in MAIN)
c.true("...and that list is the datacard's own",
       "_modal_up = (" in MAIN and "army_rules_overlay.is_pending" in MAIN)
# AFTER the panel and the mission strip, or the strip slides out over it.
c.true("it is drawn after the panel", MAIN.index("stratagem_tooltip.draw(")
       > MAIN.index("action_panel.draw("))
c.true("...and after the mission strip that slides over the panel's edge",
       MAIN.index("stratagem_tooltip.draw(") > MAIN.index("mission_cards_overlay.draw("))
# The owner comes from the SELECTED unit, not from whose turn it is: reactive
# Stratagems are bought in the opponent's turn.
c.true("the army looked up is the selected unit's",
       "movement_controller.selected_squad" in MAIN
       and "_tip_owner = _tip_squad.owner" in MAIN)

c.finish()
