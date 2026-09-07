"""The mission strip's accordion layout (game/ui/mission_cards.py) and the
click-away draw notice (game/ui/mission_draw_overlay.py).

Rendered against a real pygame surface rather than asserted on constants: the
whole point of the redesign is that an unbounded hand still FITS, and "fits" is
a fact about measured rectangles, not about the numbers that went into them.

The two things most easily broken here, both pinned below:
  - the bottom-up accumulator's SIGN. Laying out upward, the next bar's bottom
    sits a gap ABOVE this one's top, so a negative gap must SUBTRACT. Getting
    it backwards spreads the bars apart instead of shingling them, and the
    stack silently runs off the top of the screen - which looks fine with three
    cards and is catastrophic with thirty.
  - Player 2's cards must be gone. The user asked for the opponent's missions
    to leave this strip entirely.
"""

import io
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

pygame.init()
pygame.font.init()

import testkit as tk  # noqa: E402
from game import config, secondary_missions as sm  # noqa: E402
from game.missions import MissionController, PRIMARY_MISSION_NAME  # noqa: E402
from game.ui import mission_cards as mcui  # noqa: E402
from game.ui.mission_draw_overlay import MissionDrawOverlay  # noqa: E402

checks = tk.Checks("Mission strip")

config.SECONDARY_MISSION_CARD_PLAYERS = ("Player 1",)

SURFACE = pygame.Surface((1920, 1080))
# The real left panel rect main.py builds: full width, minus the reserves strip.
LEFT_PANEL = pygame.Rect(0, 0, config.LEFT_PANEL_WIDTH,
                         1080 - config.RESERVES_PANEL_HEIGHT)
NOWHERE = (-1, -1)


def deck(hand_size, player="Player 1"):
    ctrl = sm.SecondaryMissionController(player=player)
    ctrl.set_tokens_source(lambda: [])
    ctrl.hand = [
        sm.SecondaryMissionCard(f"k{i}", f"Mission {i}",
                                "Some printed mission text that wraps across "
                                "several lines of the card body. " * 2,
                                sm.TIMING_END_OF_YOUR_TURN, lambda ctx: 0)
        for i in range(hand_size)
    ]
    return ctrl


def draw(overlay, mission, secondary, mouse_pos=NOWHERE, frames=1):
    for _ in range(frames):
        overlay.draw(SURFACE, LEFT_PANEL, mission, secondary, mouse_pos=mouse_pos)
    return overlay._cards, overlay._rects(LEFT_PANEL, overlay._cards)


# --- 1. contents: the human's Primary plus their hand, and nobody else's ---
print("--- 1. contents ---")

mission = MissionController(game_log=tk.Log())
overlay = mcui.MissionCardsOverlay()
cards, rects = draw(overlay, mission, deck(2))

checks.eq("one Primary plus the two hand cards", len(cards), 3)
checks.eq("the first card is the Primary", cards[0].category, mcui.PRIMARY)
checks.eq("and it is the player's own mission", cards[0].title, PRIMARY_MISSION_NAME)
checks.eq("the rest are Secondaries",
          [c.category for c in cards[1:]], [mcui.SECONDARY] * 2)
checks.eq("every card belongs to the card player",
          sorted({c.player for c in cards}), ["Player 1"])
checks.eq("NO Player 2 card is in the strip",
          any(c.player == "Player 2" for c in cards), False)

# The Primary carries its running score on the collapsed bar.
mission.primary_points["Player 1"] = 12
cards, rects = draw(mcui.MissionCardsOverlay(), mission, deck(0))
checks.eq("an empty hand still shows the Primary", len(cards), 1)
checks.eq("the Primary bar shows its score", cards[0].status, "12 pts")

# No deck at all (the harnesses' config) still renders the Primary.
cards, rects = draw(mcui.MissionCardsOverlay(), mission, None)
checks.eq("with no deck the strip is just the Primary", len(cards), 1)


# --- 2. the bar shows WHEN a card is checked, not a live fulfilment claim ---
print("--- 2. the status marker ---")

# The reported bug: the bar used to render a live "would this score if the turn
# ended now" snapshot, so standing on the centre in the MOVEMENT phase already
# read as complete. User: "mir ist aufgefallen, dass ich gerade Center Ground
# mitten im Zug schon erfuellt habe... Center Ground wird erst am Ende meines
# Zuges erfuellt." A card is measured at its own printed instant and nowhere
# else, so mid-turn the bar names that instant instead.
from game.command_points import CommandPointManager  # noqa: E402
from game.decision import DecisionManager  # noqa: E402
from game.turn import TurnTracker  # noqa: E402
from game.factions import aeldari as ae  # noqa: E402

config.BOARD_WIDTH_IN, config.BOARD_HEIGHT_IN = 60.0, 44.0
cx, cy = sm.board_centre()


def centre_held_scene():
    """A board where Centre Ground's CONDITION holds - a friendly unit on the
    centre, no enemy anywhere - but the turn has not ended."""
    decision = DecisionManager()
    ctrl = sm.SecondaryMissionController(
        player="Player 1", mission_controller=mission,
        command_points=CommandPointManager(), decision_manager=decision,
        turn_tracker=TurnTracker(game_log=tk.Log()))
    mine = tk.build(ae.RANGERS, owner="Player 1", name="1 Rangers 1")
    for i, m in enumerate(mine.models):
        m.x_in, m.y_in = cx + i * 1.2, cy
    ctrl.set_tokens_source(lambda: list(mine.models))
    ctrl.hand = [sm.CENTRE_GROUND]
    return ctrl, decision


ctrl, decision = centre_held_scene()
# Sanity: the condition really does hold, so this is a genuine mid-turn
# "achieved" state and not a scene that would have shown nothing anyway.
checks.eq("the condition really is met mid-turn",
          sm.CENTRE_GROUND.score(sm.MissionContext("Player 1", tokens=ctrl._tokens())),
          sm.CENTRE_GROUND_FAR_VP)
cards, rects = draw(mcui.MissionCardsOverlay(), mission, ctrl)
checks.eq("mid-turn the bar names the card's own instant instead",
          cards[1].status, sm.CENTRE_GROUND.timing_label)
checks.eq("in the muted timing colour, not the READY highlight",
          cards[1].status_color, mcui.CARD_TIMING_COLOR)
checks.eq("it does NOT claim to be complete",
          "READY" in (cards[1].status or ""), False)

# READY appears exactly while the cash-in prompt is open - the moment the
# player is actually being asked.
ctrl.begin_end_of_turn("Player 1")
checks.true("the end of the turn opens the prompt", decision.is_pending)
cards, rects = draw(mcui.MissionCardsOverlay(), mission, ctrl)
checks.eq("now the bar reads READY", cards[1].status,
          f"READY - {sm.CENTRE_GROUND_FAR_VP} VP")
checks.eq("in the highlight colour", cards[1].status_color, mcui.CARD_READY_COLOR)

# ...and drops back once the choice is answered.
tk.pick_option(decision, "Keep the card")
if decision.is_pending:
    tk.pick_option(decision, "Keep them all")
cards, rects = draw(mcui.MissionCardsOverlay(), mission, ctrl)
checks.eq("keeping the card returns the bar to its timing",
          cards[1].status, sm.CENTRE_GROUND.timing_label)

# Bring It Down names a different instant, and the bar says so.
ctrl2 = sm.SecondaryMissionController(player="Player 1")
ctrl2.set_tokens_source(lambda: [])
ctrl2.hand = [sm.BRING_IT_DOWN]
cards, rects = draw(mcui.MissionCardsOverlay(), mission, ctrl2)
checks.eq("Bring It Down's bar names ITS instant", cards[1].status, "end of a turn")
checks.eq("which differs from Centre Ground's",
          sm.BRING_IT_DOWN.timing_label == sm.CENTRE_GROUND.timing_label, False)


# --- 3. the accordion: hover opens ONE card ---
print("--- 3. the accordion ---")

overlay = mcui.MissionCardsOverlay()
cards, rects = draw(overlay, mission, deck(3))
checks.eq("everything starts collapsed to a bar",
          [round(c.height) for c in cards], [mcui.BAR_HEIGHT] * 4)
checks.eq("every bar is the full card width",
          sorted({r.width for r in rects}), [mcui.CARD_WIDTH])
checks.eq("and anchored at the left panel's right edge",
          sorted({r.x for r in rects}), [LEFT_PANEL.right])

# Settle the animation on the second card.
target = rects[1].center
cards, rects = draw(overlay, mission, deck(3), mouse_pos=target, frames=60)
checks.true("the hovered card is taller than a bar", cards[1].height > mcui.BAR_HEIGHT)
checks.true("tall enough to show its text",
            cards[1].height >= mcui.BAR_HEIGHT + mcui.TEXT_REVEAL_MARGIN)
checks.eq("every OTHER card stays a bar",
          [round(c.height) for i, c in enumerate(cards) if i != 1],
          [mcui.BAR_HEIGHT] * 3)

# Moving away closes it again - the animation is not one-way.
cards, rects = draw(overlay, mission, deck(3), mouse_pos=NOWHERE, frames=60)
checks.eq("moving off collapses it again",
          [round(c.height) for c in cards], [mcui.BAR_HEIGHT] * 4)

# The expanded card pushes the ones ABOVE it up - it is anchored bottom-up.
overlay = mcui.MissionCardsOverlay()
_, rects_before = draw(overlay, mission, deck(3))
bottom_before = rects_before[-1].bottom
cards, rects_after = draw(overlay, mission, deck(3),
                          mouse_pos=rects_before[-1].center, frames=60)
checks.eq("the bottom card stays pinned to the bottom",
          rects_after[-1].bottom, bottom_before)
checks.true("the cards above it are pushed up", rects_after[0].y < rects_before[0].y)


# --- 4. overflow shingles instead of running off the screen ---
print("--- 4. shingling ---")

for hand_size in (1, 5, 20, 40):
    overlay = mcui.MissionCardsOverlay()
    cards, rects = draw(overlay, mission, deck(hand_size))
    fits = rects[0].y >= LEFT_PANEL.top and rects[-1].bottom <= LEFT_PANEL.bottom
    checks.true(f"a hand of {hand_size} fits inside the panel height", fits)
    steps = [rects[i + 1].y - rects[i].y for i in range(len(rects) - 1)]
    if steps:
        checks.true(f"a hand of {hand_size} keeps every bar's title row visible",
                    min(steps) >= mcui.MIN_BAR_OVERLAP_STEP)
        checks.true(f"a hand of {hand_size} keeps the bars in order", min(steps) > 0)

# A small hand is NOT shingled - the bars sit apart by the normal gap.
overlay = mcui.MissionCardsOverlay()
cards, rects = draw(overlay, mission, deck(3))
checks.eq("a small hand uses the normal gap, no overlap",
          rects[1].y - rects[0].y, mcui.BAR_HEIGHT + mcui.BAR_GAP)
# A large one IS - which is the whole point of the redesign.
overlay = mcui.MissionCardsOverlay()
cards, rects = draw(overlay, mission, deck(40))
checks.true("a large hand overlaps its bars",
            rects[1].y - rects[0].y < mcui.BAR_HEIGHT)


# --- 5. hovering picks the card actually under the cursor ---
print("--- 5. hit testing ---")

# When bars shingle they overlap, and the one drawn ON TOP (later in the list)
# is the one the cursor is pointing at. Hit-testing front-to-back would open
# the card behind it.
overlay = mcui.MissionCardsOverlay()
cards, rects = draw(overlay, mission, deck(40))
overlap_point = (rects[5].centerx, rects[6].y + 2)  # inside both bar 5 and bar 6
checks.true("the probe point really is inside both bars",
            rects[5].collidepoint(overlap_point) and rects[6].collidepoint(overlap_point))
cards, _ = draw(overlay, mission, deck(40), mouse_pos=overlap_point, frames=60)
checks.true("the card drawn on top is the one that opens",
            cards[6].height > cards[5].height)


# --- 6. the draw notice ---
print("--- 6. the draw notice ---")

notice = MissionDrawOverlay()
checks.eq("nothing pending to start with", notice.is_pending, False)
notice.draw(SURFACE)  # must be a no-op, not a crash
notice.enqueue("Player 1", [sm.CENTRE_GROUND, sm.BRING_IT_DOWN])
checks.true("a draw makes it pending", notice.is_pending)
notice.draw(SURFACE)
notice.dismiss()
checks.eq("a click clears it", notice.is_pending, False)

# A queue, not a slot: a second announcement must not clobber an unread one.
notice.enqueue("Player 1", [sm.CENTRE_GROUND])
notice.enqueue("Player 1", [sm.BRING_IT_DOWN])
notice.dismiss()
checks.true("the second announcement survives the first being dismissed",
            notice.is_pending)
notice.dismiss()
checks.eq("and clears in turn", notice.is_pending, False)

# An empty draw is not an announcement.
notice.enqueue("Player 1", [])
checks.eq("an empty draw enqueues nothing", notice.is_pending, False)

# One card and two cards both render (the heading changes number).
for cards_in in ([sm.CENTRE_GROUND], [sm.CENTRE_GROUND, sm.BRING_IT_DOWN]):
    notice.enqueue("Player 1", cards_in)
    notice.draw(SURFACE)
    notice.dismiss()
checks.true("one- and two-card notices both render", True)


# --- 7. the strip stays draw-only ---
print("--- 7. draw-only ---")

# These cards sit over the BOARD, not over the left panel, so a click on one
# reaches main.py's board branch. Every choice they offer is a DecisionManager
# prompt instead - if that ever changes, main.py needs a new event branch ahead
# of the board's, and this check is where that decision gets revisited.
checks.eq("the strip exposes no click handler",
          hasattr(mcui.MissionCardsOverlay, "handle_click"), False)
main_src = io.open("main.py", encoding="utf-8").read()
checks.eq("and main.py routes no clicks to it",
          "mission_cards_overlay.handle_click" in main_src, False)
cards, rects = draw(mcui.MissionCardsOverlay(), mission, deck(1))
checks.true("the cards really do overhang the board",
            rects[0].right > config.LEFT_PANEL_WIDTH)


# --- 8. legibility: the metadata block is a real two-column table -----------
print("--- 8. the info block ---")

# User: "auch auf den missionskarten. die sind gerade sehr schwer lesbar. die
# sollten etwas aufgeraeumter und besser lesbarer sein."
#
# The measured cause was not the font size. The info rows were single strings
# with their value pushed across by spaces ("WHEN     end of your turn"), which
# only lines up in a MONOSPACE font - and config.FONT_NAME is None, pygame's
# proportional default. Worse, wrap_text() splits on spaces, so the one row long
# enough to wrap lost its indent completely on the second line and read as a new
# sentence. Hence (label, value) pairs and two real columns.
_strip = mcui.MissionCardsOverlay()

checks.true("the default font really is proportional - the premise of all this",
            _strip.body_font.size("WWWW")[0] != _strip.body_font.size("iiii")[0])

# A real card with a long, wrapping value: Cleanse's ACTION row.
_cleanse = next(c for c in sm.ALL_CARDS if c.key == "cleanse")
_rows = _cleanse.info_rows()
checks.true("info comes back as (label, value) pairs",
            all(isinstance(r, tuple) and len(r) == 2 for r in _rows))
checks.true("...with both halves filled in",
            all(label and value for label, value in _rows))
# The old shape hid the value inside a padded string. If that ever comes back,
# the label carries the whole row and the value column is empty - or the label
# holds run-together spaces.
checks.eq("no row smuggles its value into the label as padding",
          [label for label, _ in _rows if "  " in label], [])
checks.true("the fixture really has a value too long for one line",
            _strip.body_font.size(dict(_rows)["ACTION"])[0]
            > _strip._info_value_width())

# ...and it must WRAP INSIDE ITS OWN COLUMN. This is the whole fix: measured on
# pixels, because "the value column starts at x" is a claim about the drawing.
_deck = sm.SecondaryMissionController(player="Player 1")
_deck.set_tokens_source(lambda: [])
_deck.hand = [_cleanse]
_shot = pygame.Surface((640, 1080))
BG = (30, 34, 40)


def settle(mouse_pos, frames=80):
    for _ in range(frames):
        _shot.fill(BG)
        _strip.draw(_shot, LEFT_PANEL, mission, _deck, mouse_pos=mouse_pos)
    return _strip._rects(LEFT_PANEL, _strip._cards)


_rects = settle(NOWHERE)
_rects = settle(_rects[1].center)   # index 1 is the Cleanse card
_card_rect = _rects[1]
checks.true("the card really did expand", _card_rect.height > mcui.BAR_HEIGHT * 2)


def row_ink_columns(y):
    """x of the leftmost and rightmost non-background pixel on scanline `y`."""
    xs = [x for x in range(_card_rect.left + 2, _card_rect.right - 2)
          if _shot.get_at((x, y))[:3] != mcui.CARD_BG_COLOR]
    return (min(xs), max(xs)) if xs else (None, None)


_label_x = _card_rect.x + mcui.CARD_PADDING
_value_x = _label_x + mcui.INFO_LABEL_WIDTH + mcui.INFO_COLUMN_GAP
_info_top = _card_rect.y + mcui.BAR_HEIGHT + mcui.BODY_GAP
_info_bottom = _info_top + _strip._info_height(_strip._cards[1])

_lines_with_ink = [y for y in range(_info_top, _info_bottom)
                   if row_ink_columns(y)[0] is not None]
checks.true("the info block actually rendered", len(_lines_with_ink) > 10)

# Every scanline in the block starts either in the label column or in the value
# column - never between them. A padded string ignores the columns entirely and
# a wrapped continuation lands wherever the words happen to fall.
_strays = [y for y in _lines_with_ink
           if not (abs(row_ink_columns(y)[0] - _label_x) <= 2
                   or row_ink_columns(y)[0] >= _value_x - 2)]
checks.eq("every info line starts in one of the two columns", _strays, [])
checks.true("...and both columns are actually used",
            any(abs(row_ink_columns(y)[0] - _label_x) <= 2 for y in _lines_with_ink)
            and any(row_ink_columns(y)[0] >= _value_x - 2 for y in _lines_with_ink))
# The load-bearing one: the long ACTION value wraps onto lines that still begin
# in the value column. Under the old padded-string layout those continuation
# lines began at the left padding instead.
_value_lines = [y for y in _lines_with_ink if row_ink_columns(y)[0] >= _value_x - 2]
checks.true("a wrapped value keeps its own column on every line",
            len(_value_lines) > len(_rows))
checks.true("nothing overruns the card's right padding",
            max(row_ink_columns(y)[1] for y in _lines_with_ink)
            <= _card_rect.right - mcui.CARD_PADDING + 2)

# And the height the card reserved has to match what it actually drew, or the
# printed mission text is clipped off the bottom. This is the failure a wrapped
# info value causes: it pushes everything below it down.
checks.true("the card reserved enough height for what it drew",
            _strip._last_content_bottom is not None
            and _strip._last_content_bottom <= _card_rect.bottom - 2)
checks.true("...and did not reserve far too much either",
            _card_rect.bottom - _strip._last_content_bottom <= mcui.CARD_PADDING + 4)


# --- 9. the scoring table, and paragraphed prose ---------------------------
print("--- 9. WHAT | WHEN | VP ---")

# User: "koenntest du hier absaetze unten einbauen, was wieviele punkte gibt?
# und vielleicht punkte und text tabellarisch trennen? so im fliesstext ist die
# information sehr unuebersichtlich. vielleicht eine kleine tablle /
# Was | Wann | VP".
from game import primary_missions as pm  # noqa: E402
from game.ui.text_utils import split_paragraphs  # noqa: E402

# 9a. The paragraph split changes NO WORDS. This is the load-bearing check:
# the whole point of the previous change was to stop showing self-written
# variants of printed rules, and re-flowing prose is one edit away from
# rewriting it. Checked over every mission text the repo ships.
_texts = [m.text for m in pm.ALL_MISSIONS] + [c.text for c in sm.ALL_CARDS]
checks.true("there really are mission texts to check", len(_texts) >= 20)
_lossy = [t[:40] for t in _texts if " ".join(split_paragraphs(t)) != " ".join(t.split())]
checks.eq("splitting into paragraphs changes not one word", _lossy, [])
checks.true("...and it really splits - every card gets more than one block",
            all(len(split_paragraphs(t)) >= 2 for t in _texts))
checks.eq("empty text splits to nothing", split_paragraphs(""), [])
# The two shapes that must NOT split: an inches mark and a round band carry no
# full stop, and splitting inside them would cut a clause in half.
checks.eq('a 6" measurement does not split a sentence',
          len(split_paragraphs('units within 6" of the centre and not beyond.')), 1)
checks.eq("a rounds band does not split either",
          len(split_paragraphs("Rounds 1-2, at the end of your turn: 2VP.")), 1)

# 9b. Every scoring box states its rate, on every card.
for _m in pm.ALL_MISSIONS:
    _rows = _m.scoring_rows()
    checks.eq(f"{_m.name}: one scoring row per printed box", len(_rows), len(_m.boxes))
    checks.eq(f"{_m.name}: every row states a VP rate",
              [w for w, _t, v in _rows if not str(v).strip()], [])
    checks.eq(f"{_m.name}: and names its instant",
              [w for w, t, _v in _rows if not str(t).strip()], [])
# Derived from the same constants the score functions read, so the printed rate
# and the paid rate cannot drift. Spot-checked on the card the user reported.
_recon = dict((w, v) for w, _t, v in pm.RECONNAISSANCE_SWEEP.scoring_rows())
checks.eq("Reconnaissance Sweep's SPREAD box prints both tiers",
          _recon["SPREAD"],
          "%d or %d" % (pm.RECON_THREE_QUARTERS_VP, pm.RECON_FOUR_QUARTERS_VP))
checks.eq("...its KILLS box prints a per-unit rate",
          _recon["KILLS"], "%d/unit" % pm.RECON_PER_KILL_VP)
checks.eq("...and its OBJECTIVE box a flat one",
          _recon["OBJECTIVE"], "%d" % pm.RECON_OBJECTIVE_VP)

# 9c. Drawn as a real table. Pixels again: "the VP line up in a column" is a
# claim about the drawing, and it is the whole reason for pulling them out of
# the prose.
_prim = pm.RECONNAISSANCE_SWEEP


class _FakePrimaryController:
    player = "Player 1"
    plays_card = True
    mission = _prim

    def detail(self):
        return None


_strip2 = mcui.MissionCardsOverlay()
_shot2 = pygame.Surface((700, 1080))


def settle2(pos, frames=80):
    for _ in range(frames):
        _shot2.fill(BG)
        _strip2.draw(_shot2, LEFT_PANEL, mission, _deck, mouse_pos=pos,
                     primary_controller=_FakePrimaryController())
    return _strip2._rects(LEFT_PANEL, _strip2._cards)


_r = settle2(NOWHERE)
_r = settle2(_r[0].center)          # the Primary is always first
_pcard, _prect = _strip2._cards[0], _r[0]
checks.eq("the strip shows the Force Disposition card", _pcard.title, _prim.name)
checks.eq("...with a scoring row per box", len(_pcard.scoring), len(_prim.boxes))
checks.true("...and it expanded", _prect.height > mcui.BAR_HEIGHT * 3)


def ink_span(y, left, right):
    """(leftmost, rightmost) inked x on scanline `y` within [left, right), or
    (None, None). Bounded so the card's own rounded border - which bulges past
    the text column near the bottom corners - cannot be read as a table cell."""
    xs = [x for x in range(left, right)
          if _shot2.get_at((x, y))[:3] != mcui.CARD_BG_COLOR]
    return (min(xs), max(xs)) if xs else (None, None)


# The three columns of the scoring table, by their own layout constants. The VP
# column is scanned by its OWN x-range, not by "ink near the right margin":
# the WHEN column's wrapped text reaches into that band, and counting it as a
# VP cell is what made the first version of this check fail.
_text_x = _prect.x + mcui.CARD_PADDING
_when_x = _text_x + mcui.SCORE_WHAT_WIDTH + mcui.INFO_COLUMN_GAP
_vp_left = _when_x + _strip2._score_when_width()
_vp_right = _prect.right - mcui.CARD_PADDING
_table_top = _prect.top + mcui.BAR_HEIGHT + mcui.BODY_GAP + _strip2._info_height(_pcard)
_table_bottom = _table_top + _strip2._scoring_height(_pcard)

_vp_edges = [ink_span(y, _vp_left, _vp_right + 1)
             for y in range(int(_table_top), int(_table_bottom))]
# A scanline whose ink spans the whole column is one of the table's horizontal
# RULES, not a cell - it would otherwise anchor the "left edge" measurement at
# the column boundary and hide what the cells actually do.
_column_width = _vp_right - _vp_left
_vp_edges = [(lo, hi) for lo, hi in _vp_edges
             if lo is not None and (hi - lo) < _column_width * 0.8]
checks.true("the VP column rendered", len(_vp_edges) >= 3)
checks.true("...and never spills past its right edge",
            all(hi <= _vp_right for _lo, hi in _vp_edges))
# Right-ALIGNED, not merely inside the column: the right edges cluster while
# the left edges spread, because "3 or 6" and "3" are different widths. Left
# alignment would show exactly the opposite. The tolerance is glyph BEARING -
# the cells are blitted flush right by surface width, but "6", "t" and "3"
# each stop a couple of antialiased pixels short of their own edge (measured
# spread: 5px at this size), so demanding an exact match would be asserting
# something about the font rather than about the layout.
_right_spread = max(hi for _lo, hi in _vp_edges) - min(hi for _lo, hi in _vp_edges)
_left_spread = max(lo for lo, _hi in _vp_edges) - min(lo for lo, _hi in _vp_edges)
checks.true("...the VP cells share a right edge", _right_spread <= 6)
checks.true("...and it really is right alignment, not a coincidence of equal widths",
            _left_spread > _right_spread)
# The WHEN column must not run into the VP column, or the wrapped timings would
# collide with the numbers.
_when_edges = [ink_span(y, _when_x, _vp_left)
               for y in range(int(_table_top), int(_table_bottom))]
checks.true("the WHEN column rendered",
            sum(1 for lo, _hi in _when_edges if lo is not None) >= 3)

# The prose below is set as separate blocks. Measured as blank scanlines INSIDE
# the prose region - one continuous block has none.
_prose_top = _strip2._last_content_bottom - _strip2._prose_height(_pcard)
_blank_runs, _run = 0, 0
for y in range(int(_prose_top), int(_strip2._last_content_bottom)):
    xs = [x for x in range(_prect.left + mcui.CARD_PADDING, _prect.right - mcui.CARD_PADDING, 2)
          if _shot2.get_at((x, y))[:3] != mcui.CARD_BG_COLOR]
    if xs:
        _run = 0
    else:
        _run += 1
        if _run == mcui.PARAGRAPH_GAP:
            _blank_runs += 1
checks.true("the printed text is set as separate paragraphs, not one block",
            _blank_runs >= len(split_paragraphs(_pcard.text)) - 1)

# And the card still reserves exactly what it draws, now with a table in it.
checks.true("a card with a scoring table still fits its own content",
            _strip2._last_content_bottom <= _prect.bottom - 2)
checks.true("...and does not over-reserve",
            _prect.bottom - _strip2._last_content_bottom <= mcui.CARD_PADDING + 4)

checks.finish()
