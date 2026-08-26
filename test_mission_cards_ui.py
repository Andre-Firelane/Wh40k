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

checks.finish()
