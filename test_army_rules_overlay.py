"""The "see army rules" link and the reader it opens.

User: "es fehlt noch ein ort, wo man armeeregel und detachment regeln anschauen
kann. ich wuerde vorschlagen, das im game info panel rechts zu platzieren. dort
soll irgendwo ein kleiner link sein 'see army rules' unter den logos und
volkernamen."

Two halves, and the second is the one no unit test would otherwise reach: the
overlay works when driven directly, and main() has to actually route the click
to it. "Built, but never fed" has shipped in this repo six times over, so
section 5 asks the SOURCE.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

pygame.init()
pygame.font.init()
pygame.display.set_mode((1, 1))   # sprites.fitted_surface() needs a display format for convert_alpha()

import testkit as tk  # noqa: E402

# Asked for by FACTION, not named: a suite that hardcodes a list key breaks
# when that list is retired, and breaks as a crash rather than a red line.
DG_LIST = tk.list_key("DEATH GUARD")
from game import army_lists, config, rules_text  # noqa: E402
from game.command_points import CommandPointManager  # noqa: E402
from game.missions import MissionController  # noqa: E402
from game.turn import TurnTracker  # noqa: E402
from game.ui import game_status_panel as gsp  # noqa: E402
from game.ui import army_rules_overlay as aro  # noqa: E402
from game.ui.army_rules_overlay import ArmyRulesOverlay  # noqa: E402

c = tk.Checks("Army rules reader")

W, H = 1600, 900
SCREEN = pygame.Rect(0, 0, W, H)
ARMIES = {"Player 1": "aeldari", "Player 2": "necrons"}


def overlay(armies=None, player="Player 1"):
    ov = ArmyRulesOverlay()
    ov.show(armies if armies is not None else ARMIES, player)
    return ov


def flat(ov):
    """The reader's text as one whitespace-normalised string - what the
    losslessness checks compare against rules_text."""
    return " ".join(" ".join(b.text.split()) for b in ov._blocks if b.text)


# --- 1. what it contains ---------------------------------------------------
print("\n=== 1. contents ===")

ov = overlay()
c.true("it opens", ov.is_pending)
kinds = [b.kind for b in ov._blocks]
texts = [b.text for b in ov._blocks]

# ONE ARMY PER LINK. This reverses the original "BOTH ARMIES, not just the
# reader's" design, and the argument it was built on survives: you do need the
# opponent's army rule, and it is still one click away - under THEIR badge.
# What changed is that there are two links now, so reaching your own no longer
# means scrolling past theirs. User: "außerdem sollten dort 2 links sein einer
# für Spieler 1 und einer für Spieler 2".
c.eq("exactly one army is shown", sum(1 for k in kinds if k == "player"), 1)
c.true("...and it is the one whose link was clicked", texts[0].startswith("Player 1"))
c.true("...named by its list", "Aeldari" in texts[0])
c.eq("the opponent is NOT in it",
     [t for t in texts if t.startswith("Player 2")], [])

other = overlay(player="Player 2")
other_texts = [b.text for b in other._blocks]
c.true("the other link opens the other army", other_texts[0].startswith("Player 2"))
c.true("...named by its list", "Necrons" in other_texts[0])
c.eq("...and not the first player's",
     [t for t in other_texts if t.startswith("Player 1")], [])
# The two together still cover everything the single reader used to, which is
# what keeps the reversal a rearrangement rather than a loss.
c.true("between them both armies are still readable",
       any("Aeldari" in t for t in texts) and any("Necrons" in t for t in other_texts))

# The army rule and every detachment, by name.
c.true("the army rule is headed by name",
       any(t == "ARMY RULE: Battle Focus" for t in texts))
c.true("...and its printed text is there",
       any("Battle Focus tokens" in t for t in texts))
aeldari_entry = army_lists.get("aeldari")
c.true("the fixture really fields two detachments", len(aeldari_entry.detachments) == 2)
for detachment in aeldari_entry.detachments:
    c.true(f"{detachment} has a heading",
           any(t.startswith(f"DETACHMENT: {detachment}") for t in texts))
c.true("...and a detachment heading carries its RULE's name, not just its own",
       any("Strands of Fate" in t for t in texts))
c.true("the detachment rule's printed text is there",
       any("Fate dice" in t for t in texts))

# PRINTED text, not a summary - read through rules_text so there is one
# definition of what "printed" means.
#
# STRONGER than the check this replaces. That one asked whether each parsed
# paragraph appeared SOMEWHERE as a whole block, which a reader that dropped
# or duplicated a word elsewhere would still pass. The reader now splits at
# corpus-LINE granularity (so the Orks' flavour text stops being fused to
# their rule), so the honest question is whether the same WORDS come out in
# the same order - the losslessness guarantee split_paragraphs() documents,
# applied one level up.
_printed = " ".join(" ".join(p.split())
                    for p in rules_text.army_rule_text("AELDARI", "Battle Focus") if p)
c.true("every printed word of the army rule reaches the reader, in order",
       _printed in flat(ov))
_dname, _dtext = rules_text.detachment_rule_text("AELDARI", "Seer Council")
c.true("...and every printed word of a detachment rule too",
       " ".join(" ".join(p.split()) for p in _dtext if p) in flat(ov))
c.eq("no engine-implementation note reaches the reader",
     [t for t in texts if "see game/" in t or ".py" in t], [])
c.eq("no markdown marker survives to the screen",
     [t for t in texts if "**" in t], [])

# Nothing to show opens nothing: an empty modal that must be clicked away is
# worse than no link.
c.eq("no armies, no overlay", ArmyRulesOverlay().show({}, "Player 1"), False)
c.eq("...and it stays closed",
     ArmyRulesOverlay().show({}, "Player 1") or ArmyRulesOverlay().is_pending, False)
c.eq("an unknown army key is skipped rather than crashing a frame",
     ArmyRulesOverlay().show({"Player 1": "no-such-army"}, "Player 1"), False)
c.eq("...and so is a player who is not in the mapping",
     ArmyRulesOverlay().show(ARMIES, "Player 3"), False)


# --- 1b. ONLY RULES TEXT - no lore, no worked examples ----------------------
# User, after a game: "keine hintergrund info texte und example texte in den
# armeeregeln bitte. nur reine regeltexte."
#
# Every one of these paragraphs used to open its rule in this reader. They are
# gone at the SCRAPE (Wahapedia marks them ShowFluff / redExample, and
# test_datasheet_rules.py section 5c pins that every such block on the page is
# absent from the corpus) - this section is the same claim where the user
# meets it, on the blocks the panel is handed.
#
# Each faction is a PAIR: the lore sentence that must be gone, and a rule
# sentence from the same section that must still be there. Absence on its own
# is also true of a reader showing nothing at all.
print("\n=== 1b. rules text only ===")

FLUFF_AND_RULE = [
    ("aeldari", "In war, as in all things", "Battle Focus tokens"),
    ("orks", "The infamous war cry of the Orks", "call a Waaagh!"),
    ("necrons", "The Necron dynasties benefit", "heals D3 wounds"),
    ("tau", "The Hunter Cadres battle for the betterment", "Observer unit"),
    (DG_LIST, "The Death Guard are warriors of the Plague God",
     "Contagion Range"),
]
for _key, _lore, _rule in FLUFF_AND_RULE:
    _text = flat(overlay({"Player 1": _key}))
    c.eq(f"{_key}: the lore paragraph is gone", _lore in _text, False)
    c.true(f"{_key}: ...and the rule beside it is not", _rule in _text)

# The Necron worked example is the other kind the report named, and it is the
# one that is hardest to spot: it reads like rules prose for six lines.
_nec = flat(overlay({"Player 1": "necrons"}))
c.eq("no worked example reaches the reader", "Example:" in _nec, False)
c.eq("...not even the unit it walked through",
     "currently contains 2 models" in _nec, False)

# A STRATAGEM's own legend is lifted off the page by its own regex, so the
# skip that removes every other block of flavour cannot reach it - it is left
# unread instead. Different mechanism, same claim, so it gets its own check.
_ael = flat(overlay({"Player 1": "aeldari"}))
c.eq("a stratagem's legend is gone too",
     "The seer plucks fate to find the foe" in _ael, False)
c.true("...while its name, subtitle and WHEN survive",
       "PRESENTIMENT OF DREAD" in _ael.upper()
       and "Strategic Ploy Stratagem" in _ael and "WHEN:" in _ael)

# Death Guard is the case where lore and rule alternate line by line - one
# flavour sentence above each of the three Plagues - so a filter that only
# dropped a section's OPENING paragraph would still leak here.
_dg = flat(overlay({"Player 1": DG_LIST}))
c.eq("per-Plague flavour lines are gone as well",
     any(s in _dg for s in ("This horrifying affliction",
                            "Limbs shuddering with fever palsy",
                            "Victims of this insidious ailment")), False)
c.true("...and all three Plagues still print their name and effect",
       all(s in _dg for s in ("Skullsquirm Blight", "Rattlejoint Ague",
                              "Scabrous Soulrot"))
       and "Worsen the Save characteristic" in _dg)


# --- 2. dismissing and scrolling -------------------------------------------
print("\n=== 2. dismiss and scroll ===")

ov = overlay()
c.true("ESC closes it",
       ov.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_ESCAPE}))
       and not ov.is_pending)

ov = overlay()
c.true("a click closes it",
       ov.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (5, 5), "button": 1}))
       and not ov.is_pending)
# Anywhere, inside the panel included - there is nothing to click in there, so
# making the player find the edge would be a puzzle rather than a control.
ov = overlay()
surface = pygame.Surface((W, H))
ov.draw(surface)
c.true("...including inside the panel itself",
       ov.handle_event(pygame.event.Event(
           pygame.MOUSEBUTTONDOWN, {"pos": ov.last_rect.center, "button": 1}))
       and not ov.is_pending)

# Scrolling. These texts are hundreds of words, so this is not optional.
ov = overlay()
surface = pygame.Surface((W, H))
ov.draw(surface)
c.true("the content is taller than the panel", ov._scroll_max > 0)
c.eq("...and it starts at the top", ov.scroll, 0)
ov.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, {"y": -1, "x": 0}))
c.true("the wheel scrolls it", ov.scroll > 0)
for _ in range(200):
    ov.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, {"y": -1, "x": 0}))
ov.draw(surface)
c.eq("scrolling down clamps at the end", ov.scroll, ov._scroll_max)
for _ in range(200):
    ov.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, {"y": 1, "x": 0}))
c.eq("...and up at the top", ov.scroll, 0)
c.eq("a closed overlay consumes nothing",
     ArmyRulesOverlay().handle_event(
         pygame.event.Event(pygame.MOUSEWHEEL, {"y": -1, "x": 0})), False)


# --- 3. drawing ------------------------------------------------------------
print("\n=== 3. drawing ===")

BG = (40, 60, 40)
surface = pygame.Surface((W, H))
surface.fill(BG)
ArmyRulesOverlay().draw(surface)
c.true("a closed overlay draws nothing",
       all(surface.get_at((x, y))[:3] == BG
           for x in range(0, W, 37) for y in range(0, H, 41)))

ov = overlay()
ov.draw(surface)
rect = ov.last_rect
c.true("the panel stays on screen", SCREEN.contains(rect))
c.true("...and is big enough to read in", rect.width > 500 and rect.height > 400)
c.true("the board behind it is dimmed, not left bright",
       surface.get_at((4, 4))[:3] != BG)


def ink(rect_):
    return sum(1 for x in range(rect_.left, rect_.right, 3)
               for y in range(rect_.top, rect_.bottom, 3)
               if surface.get_at((x, y))[:3] != (12, 18, 28))


c.true("the panel has text in it", ink(rect.inflate(-40, -40)) > 400)

# Scrolled content is drawn at a negative offset, so it MUST clip.
ov = overlay()
for _ in range(4):
    ov.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, {"y": -1, "x": 0}))
surface.fill(BG)
ov.draw(surface)
above = pygame.Rect(ov.last_rect.x, 0, ov.last_rect.width, max(0, ov.last_rect.top))
c.true("there is board visible above the panel", above.height > 0)
c.true("...and the scroll really moved", ov.scroll > 0)
# Containment: none of the BODY colour appears above the panel's own top edge.
# By colour rather than "anything not the background", because the scrim dims
# that whole area on purpose - a plain "is it untouched" test would fail on the
# dimming and pass on escaping text.
c.eq("no body text escapes the panel",
     [(x, y) for x in range(above.left, above.right, 3)
      for y in range(above.top, max(above.top, above.bottom - 2), 3)
      if surface.get_at((x, y))[:3] == (215, 232, 245)], [])

# The clip has to be handed back, or every later draw call this frame is
# confined to the panel.
guard = pygame.Rect(10, 10, 100, 100)
surface.set_clip(guard)
overlay().draw(surface)
c.eq("the surface clip is restored", surface.get_clip(), guard)
surface.set_clip(None)


# --- 4. the link in the panel ----------------------------------------------
print("\n=== 4. the link ===")

panel = gsp.GameStatusPanel()
tracker = TurnTracker("Player 1")
cp = CommandPointManager(["Player 1", "Player 2"], game_log=tk.Log())
mission = MissionController(game_log=tk.Log())
PANEL_RECT = pygame.Rect(0, 0, 240, 800)
BOTH = {"Player 1": "AELDARI", "Player 2": "NECRONS"}

panel_surface = pygame.Surface((260, 820))
panel.draw(panel_surface, PANEL_RECT, tracker, cp, mission, player_factions=BOTH)
links = panel.army_rules_rects
c.eq("ONE LINK PER PLAYER is drawn when both factions are known", len(links), 2)
by_player = dict(links)
c.eq("...one for each", sorted(by_player), ["Player 1", "Player 2"])
for player, link in links:
    c.true(f"{player}'s link is inside the panel", PANEL_RECT.contains(link))
    c.eq(f"...and answers with {player}", panel.army_rules_player_at(link.center), player)
c.eq("...and nowhere else answers", panel.army_rules_player_at((5, 5)), None)

# Each link sits under ITS OWN badge, which is what makes "which player is
# this?" answerable without reading the label.
# .get() rather than [], so a regression that drops one link makes the checks
# below go RED instead of crashing the suite - a crash hides which one broke.
# Fourth time this lesson has been paid for in this repo.
left = by_player.get("Player 1", pygame.Rect(0, 0, 0, 0))
right = by_player.get("Player 2", pygame.Rect(0, 0, 0, 0))
c.true("both links exist to compare", bool(left.width and right.width))
c.true("the two links do not overlap", not left.colliderect(right))
c.true("...and the first player's is the left one", left.centerx < right.centerx)
c.true("...each centred under its own badge tile",
       abs(left.centerx - (PANEL_RECT.x + 10 + gsp.LOGO_BOX // 2)) <= 2
       and abs(right.centerx
               - (PANEL_RECT.x + PANEL_RECT.width - 10 - gsp.LOGO_BOX // 2)) <= 2)

# UNDER the logos and the faction names, as asked.
c.true("the links sit below the badge tiles",
       left.top >= PANEL_RECT.y + gsp.LOGO_BOX)
c.true("...and below the faction name row",
       left.top >= PANEL_RECT.y + gsp.LOGO_BOX + gsp.NAME_ROW_HEIGHT - 8)
c.true("...and above the Next Phase button", left.bottom < panel.button_rect.top)

# The label had to shrink to fit two of them - measured, because the old one
# physically cannot be doubled inside a 220px panel.
# The label had to shrink, and the binding constraint is the CENTRING rather
# than the total width: a link centred under a tile whose centre is LOGO_BOX/2
# from the panel edge may only reach that far. Both links being inside the
# panel is asserted above; this pins WHY the wording changed.
c.true("the old label, centred under a tile, would hang off the panel",
       (panel.link_font.size("see army rules")[0] + 2 * gsp.ARMY_RULES_LINK_PAD) / 2
       > gsp.LOGO_BOX / 2)
c.true("...and the new one does not",
       (panel.link_font.size(gsp.ARMY_RULES_LINK_TEXT)[0] + 2 * gsp.ARMY_RULES_LINK_PAD) / 2
       <= gsp.LOGO_BOX / 2)
c.eq("...and a tile too small for either degrades instead of overhanging",
     panel._link_text(12), gsp.ARMY_RULES_LINK_SHORT_TEXT)

# It must not be the Next Phase button, and must not answer for it: reading a
# rule can never advance the phase.
c.eq("a link is not the phase button", panel.handle_click(left.center), False)
c.eq("...and the phase button is not a link",
     panel.army_rules_player_at(panel.button_rect.center), None)

# No badges, no links: without a faction there is nothing to look up.
panel.draw(panel_surface, PANEL_RECT, tracker, cp, mission, player_factions=None)
c.eq("no factions, no links", panel.army_rules_rects, [])
c.eq("...and nothing to click", panel.army_rules_player_at((120, 120)), None)


# --- 5. wiring: main() really routes to it ---------------------------------
print("\n=== 5. wiring ===")

MAIN = open("main.py", encoding="utf-8").read()

c.true("main() builds the overlay", "army_rules_overlay = ArmyRulesOverlay()" in MAIN)
c.true("...and draws it", "army_rules_overlay.draw(screen)" in MAIN)
c.true("...and opens it from the link",
       "game_status_panel.army_rules_player_at(event.pos)" in MAIN)
c.true("...on the army whose link was clicked, not on both",
       "army_rules_overlay.show(armies, rules_player)" in MAIN)
c.true("...and hands it the events while it is open",
       "army_rules_overlay.handle_event(event)" in MAIN)

# The link's branch must come BEFORE the Next Phase button's: both live in the
# right panel and the first matching branch wins, so the other order would
# advance the phase when the player asked to read a rule.
link_at = MAIN.index("game_status_panel.army_rules_player_at(event.pos)")
button_at = MAIN.index("and game_status_panel.handle_click(event.pos)")
c.true("the link is hit-tested before the phase button", link_at < button_at)

# The reader is a VIEW: it must be handled ahead of the state-gated chain, or
# it joins the five controls that chain has swallowed (error class 15).
handler_at = MAIN.index("army_rules_overlay.handle_event(event)")
c.true("...and the reader is handled before the phase button's branch too",
       handler_at < button_at)
c.true("it consumes the event rather than letting it fall through to the board",
       "army_rules_overlay.handle_event(event)\n                continue" in MAIN)
# Drawn last, over every notice - it is the one overlay the player opened.
c.true("it is drawn after the notices",
       MAIN.index("army_rules_overlay.draw(screen)") > MAIN.index("_notice.draw(screen)"))
# And it suppresses the hover datacard, which would otherwise sit on top of the
# very text that was just opened.
# find(), never index(): a guard that CRASHES when its needle moves reports
# "the suite died" instead of naming the assertion that broke - which is what
# happened here when the Unit Statistics resume joined this very branch.
_aside = MAIN.find("if army_rules_overlay.is_pending or unit_stats_overlay_view.is_pending:")
_hover = MAIN.find("unit_datacard.update_hover(")
c.true("the hover datacard steps aside for it", 0 <= _aside < _hover)


# --- 6. the REPORTED scroll bug: the wheel must not close it ----------------
print("\n=== 6. wheel vs click ===")

# User: "außerdem könnte ich das Fenster nicht scrollen. beim scrollen ging das
# Fenster wieder zu", and on being asked: "Bisher schliesst auch das Mausrad
# das Fenster. Das sollen 2 verschiedene Eingaben sein."
#
# pygame keeps pygame 1.x compatibility by emitting MOUSEBUTTONDOWN with
# button 4/5 ALONGSIDE every MOUSEWHEEL, so one physical notch arrives as TWO
# events. handle_event() dismissed on any button, so a notch scrolled and
# closed in the same frame - and since dismiss() resets `scroll`, the reader
# could not be scrolled at all.
#
# 58 checks stayed green through that because they all send a BARE
# MOUSEWHEEL, which is not what the hardware delivers. This section sends the
# PAIR.


def wheel_notch(ov, y=-1):
    """One physical notch, as pygame really queues it."""
    ov.handle_event(pygame.event.Event(pygame.MOUSEWHEEL, {"y": y, "x": 0}))
    ov.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                       {"pos": (W // 2, H // 2), "button": 4 if y > 0 else 5}))


ov = overlay()
ov.draw(pygame.Surface((W, H)))
c.true("the fixture is long enough to scroll", ov._scroll_max > 0)
wheel_notch(ov)
c.true("one real wheel notch scrolls it", ov.scroll > 0)
c.true("...and leaves it OPEN - the reported bug", ov.is_pending)
for _ in range(3):
    wheel_notch(ov)
c.true("...and it keeps scrolling", ov.scroll > 0 and ov.is_pending)

# The counter-check, without which the fix could just have made every button
# inert: the user asked for click-to-close to STAY.
ov = overlay()
ov.draw(pygame.Surface((W, H)))
c.true("a left click still closes it",
       ov.handle_event(pygame.event.Event(
           pygame.MOUSEBUTTONDOWN, {"pos": (W // 2, H // 2), "button": 1}))
       and not ov.is_pending)

# The keyboard is the second route in, because a view control with exactly one
# route is one swallowed event away from unusable.
ov = overlay()
ov.draw(pygame.Surface((W, H)))
c.true("PageDown scrolls",
       ov.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_PAGEDOWN}))
       and ov.scroll > 0)
c.true("End jumps to the bottom",
       ov.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_END}))
       and ov.scroll == ov._scroll_max)
c.true("Home jumps back to the top",
       ov.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_HOME}))
       and ov.scroll == 0)
c.true("...and none of that closed it", ov.is_pending)
c.eq("an unrelated key is not consumed",
     ov.handle_event(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_q})), False)


# --- 7. the text is STRUCTURED, not one grey block --------------------------
print("\n=== 7. structure ===")

# User: "der Text hinter See Army Rules ist noch schwer lesbar. Beispiel
# aeldari. es fehlt an überschriften, ansätzen, fett geschriebenen Namen."
#
# The structure was never missing from the corpus - rules_text deleted it
# before the reader saw it. These check it arrives.

ov = overlay()
kinds = [b.kind for b in ov._blocks]
c.true("the manoeuvre NAMES are headings, not prose",
       all(any(b.kind == "heading" and b.text == name for b in ov._blocks)
           for name in ("AGILE MANOEUVRES", "SWIFT AS THE WIND", "FADE BACK")))
c.true("TRIGGER/EFFECT are labelled rows",
       len([b for b in ov._blocks if b.kind == "label"]) >= 12)
c.true("...and carry their label separately from their sentence",
       all(b.label and not b.text.startswith(b.label + ":" + b.label)
           for b in ov._blocks if b.kind == "label"))
# The Agile Manoeuvres print TRIGGER/EFFECT; the Stratagems below them print
# WHEN/TARGET/EFFECT/RESTRICTIONS. Pinned as an exact SET rather than "at
# least these", so a classifier that started inventing labels out of ordinary
# prose would move this line.
c.eq("...with only the printed labels",
     sorted({b.label for b in ov._blocks if b.kind == "label"}),
     ["EFFECT", "RESTRICTIONS", "TARGET", "TRIGGER", "WHEN"])
c.true("the battle-size table is table rows",
       [b.cells for b in ov._blocks if b.kind == "table"][:3]
       == [("Incursion", "2"), ("Strike Force", "4"), ("Onslaught", "6")])
c.true("inline bold survives to the reader",
       any(any(text == "Normal" and bold for text, bold in (b.runs or ()))
           for b in ov._blocks))
c.true("...and the markers do not",
       not any("**" in b.text for b in ov._blocks))
c.true("paragraphs are marked as such",
       any(b.new_para for b in ov._blocks if b.kind == "text"))


# --- 8. the MEASURE - the cause that is not about styling -------------------
print("\n=== 8. line length ===")

# Before this the panel took 62% of the screen and gave the text all of it:
# 937px at 1600x900, which at the body font's ~6.2px average character is 151
# characters per line. Typographic practice puts a comfortable measure at
# 45-90, and no amount of bold or headings rescues a line that long.
for screen_w, screen_h in ((1280, 720), (1600, 900), (2560, 1440)):
    rect = ov.panel_rect(pygame.Rect(0, 0, screen_w, screen_h))
    column = ov._text_width(rect)
    avg = ov.font.size("abcdefghijklmnopqrstuvwxyz ")[0] / 27.0
    c.true(f"{screen_w}x{screen_h}: the column is a readable measure",
           column <= aro.MAX_TEXT_WIDTH and column / avg <= 95)
c.true("...and the panel is still big enough to read in",
       ov.panel_rect(SCREEN).width > 500 and ov.panel_rect(SCREEN).height > 400)

# Measured against DRAWN output, not just predicted: the mission-cards work
# found a real double-counted gap exactly this way, and the gap bookkeeping
# here is more complicated than that one.
surface = pygame.Surface((W, H))
ov.scroll = 0
ov.draw(surface)
rect = ov.panel_rect(SCREEN)
body_top = rect.y + aro.HEADER_HEIGHT + 6
c.eq("what was predicted is what was laid down",
     ov._content_height(rect), ov._last_content_bottom - body_top)


# --- 9. the hierarchy is VISIBLE, measured on pixels ------------------------
print("\n=== 9. typography on pixels ===")

# Sections 7-8 prove the structure arrives and the measure is sane. Neither
# would notice a reader that classified everything correctly and then drew it
# all in one font at one colour - which is exactly the state being fixed. So
# these read the actual surface.


def _band(surface, rect, y, height):
    """Every distinct colour in a horizontal strip of the panel."""
    seen = {}
    for py in range(max(rect.top, y), min(rect.bottom, y + height)):
        for px in range(rect.left + 4, rect.right - 4):
            colour = surface.get_at((px, py))[:3]
            seen[colour] = seen.get(colour, 0) + 1
    return seen


def _draw_one(block_kinds):
    """Draw a reader holding only blocks of these kinds, and report where each
    one landed. Isolating them is what lets a band be attributed to a kind."""
    probe = ArmyRulesOverlay()
    probe.show(ARMIES, "Player 1")
    probe._blocks = [b for b in ov._blocks if b.kind in block_kinds]
    probe._invalidate()
    surf = pygame.Surface((W, H))
    probe.draw(surf)
    entries, _total = probe._layout_for(probe.panel_rect(SCREEN))
    return probe, surf, entries


rect = ov.panel_rect(SCREEN)

# A heading and a body line, each drawn alone, then compared.
head_probe, head_surf, head_entries = _draw_one({"heading"})
body_probe, body_surf, body_entries = _draw_one({"text"})
body_top = rect.y + aro.HEADER_HEIGHT + 6

head_colours = _band(head_surf, rect, body_top, 60)
body_colours = _band(body_surf, rect, body_top, 60)
c.true("a heading is drawn in the rule-name colour, not the body colour",
       aro.RULE_NAME_COLOR in head_colours and aro.TEXT_COLOR not in head_colours)
c.true("...and body text in the body colour, not the heading's",
       aro.TEXT_COLOR in body_colours and aro.RULE_NAME_COLOR not in body_colours)
c.true("a heading uses more ink than body text of the same length",
       head_probe.heading_font.get_height() > body_probe.font.get_height())

# A label's prefix is a different colour from its own sentence, INSIDE one
# wrapped paragraph - that is what splitting them into two draws would lose.
label_probe, label_surf, _e = _draw_one({"label"})
label_colours = _band(label_surf, rect, body_top, 40)
c.true("a label prefix is drawn in the label colour",
       aro.LABEL_COLOR in label_colours)
c.true("...and its sentence continues in the body colour on the same rows",
       aro.TEXT_COLOR in label_colours)

# A bullet hangs: its text starts further right than a body line's.
bullet_blocks = [b for b in ov._blocks if b.kind == "bullet"]
if bullet_blocks:
    c.true("a bullet is indented past body text",
           aro.BULLET_INDENT > 0)


def _first_ink_x(surface, rect, y, height):
    for px in range(rect.left + 4, rect.right - 4):
        for py in range(max(rect.top, y), min(rect.bottom, y + height)):
            if surface.get_at((px, py))[:3] != aro.BG_COLOR:
                return px
    return None


# The table values form a COLUMN: their right edges cluster while their labels
# start at the same left margin. Same claim the mission cards' VP column makes.
table_probe, table_surf, table_entries = _draw_one({"table"})
rights = []
for block, offset, height in table_entries[:3]:
    y = body_top + offset
    row = _band(table_surf, rect, y, height)
    right = max((px for px in range(rect.left + 4, rect.right - 4)
                 for py in range(max(rect.top, y), min(rect.bottom, y + height))
                 if table_surf.get_at((px, py))[:3] != aro.BG_COLOR), default=None)
    if right is not None:
        rights.append(right)
c.true("the table VALUES share a right edge", len(rights) >= 3 and max(rights) - min(rights) <= 6)
c.true("...while their labels all start at the same left margin",
       len({_first_ink_x(table_surf, rect, body_top + o, h)
            for _b, o, h in table_entries[:3]}) == 1)

# And the whole point of the panel-width cap, on pixels: nothing is drawn
# outside the text column.
surface = pygame.Surface((W, H))
ov.scroll = 0
ov.draw(surface)
column_right = rect.x + aro.PADDING + ov._text_width(rect)
# The hairlines under headings and between sections are deliberately drawn
# to the panel's edge - they are RULES, not text, and running them the full
# width is what makes them read as separators. So the check is about ink that
# is neither the background nor a hairline.
strays = 0
for py in range(body_top, min(rect.bottom - aro.FOOTER_HEIGHT, body_top + 400)):
    for px in range(column_right + 8, rect.right - aro.PADDING):
        if surface.get_at((px, py))[:3] not in (aro.BG_COLOR, aro.RULE_LINE_COLOR):
            strays += 1
c.eq("no text is drawn past the text column", strays, 0)
c.true("...and the hairlines that DO run wider are only hairlines",
       any(surface.get_at((column_right + 8, py))[:3] == aro.RULE_LINE_COLOR
           for py in range(body_top, min(rect.bottom - aro.FOOTER_HEIGHT,
                                         body_top + 400))))


c.finish()
