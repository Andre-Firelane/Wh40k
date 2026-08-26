"""Game Status panel: faction badges instead of an "(Active)" line.

User request, with a layout sketch: show each player's faction logo at the
top of the right column with the Round counter between them, and mark whose
turn it is by highlighting that player's badge rather than writing
"(Active)" underneath.

What this pins down:
  * player_factions() derives who fields what from the units themselves
    (game/factions/faction.py), the same way battle_focus decides whose army
    is ASURYANI - so swapping an army list cannot leave a stale label behind.
  * the badge row only appears when BOTH players have art, and otherwise the
    panel falls all the way back to the plain text layout it had before -
    a half-filled badge row reads worse than the line it replaced.
  * the highlight really follows turn_tracker.active_player, measured in gold
    pixels inside each tile rather than by reading back the flag that put
    them there.

Every rendering check is A/B'd against a probe that empties
sprites.FACTION_LOGO_KEYS, which is the whole of the pre-change world here:
without it a green run would only prove the scene never reaches the feature.
"""

import contextlib
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

import testkit as tk
from game import config, sprites
from game.factions import build_squad
from game.factions.aeldari import GUARDIAN_DEFENDERS
from game.factions.faction import faction_keyword_of, player_factions
from game.factions.orks import BOYZ
from game.factions.tau_empire import STRIKE_TEAM
from game.turn import TurnTracker
from game.ui import game_status_panel as gsp
from game.ui.game_status_panel import GameStatusPanel

pygame.init()
pygame.display.set_mode((1, 1))

checks = tk.Checks("faction badges")

TAU = "T'AU EMPIRE"


@contextlib.contextmanager
def no_logo_art():
    """The pre-change world: no faction has a badge, so the panel can only
    draw the old text layout."""
    saved = dict(sprites.FACTION_LOGO_KEYS)
    sprites.FACTION_LOGO_KEYS.clear()
    try:
        yield
    finally:
        sprites.FACTION_LOGO_KEYS.update(saved)


# --- 1. deriving which faction a player fields ------------------------

aeldari = build_squad(GUARDIAN_DEFENDERS, "Player 1")
orks = build_squad(BOYZ, "Player 2")
tau = build_squad(STRIKE_TEAM, "Player 1")

checks.eq("a built squad knows its faction keyword", faction_keyword_of(aeldari), "AELDARI")
checks.eq("...and so does an Ork one", faction_keyword_of(orks), "ORKS")
checks.eq("...and a Tau one", faction_keyword_of(tau), TAU)

hand_built = build_squad(BOYZ, "Player 2")
hand_built.datasheet = None  # what a Squad assembled by hand looks like
checks.eq("a squad with no datasheet has no faction", faction_keyword_of(hand_built), None)

checks.eq("both armies are derived from their units",
          player_factions([aeldari, orks]),
          {"Player 1": "AELDARI", "Player 2": "ORKS"})
checks.eq("no units means nothing to show", player_factions([]), {})
checks.eq("a player whose units carry no faction is left out",
          player_factions([hand_built]), {})

mixed = build_squad(BOYZ, "Player 1")
checks.eq("a mixed army answers with its majority faction",
          player_factions([aeldari, aeldari, mixed]), {"Player 1": "AELDARI"})


# --- 2. logo lookup ---------------------------------------------------

for keyword in ("AELDARI", "ORKS", TAU, "NECRONS"):
    checks.true(keyword + " resolves to a badge file",
                sprites.faction_logo_path(keyword) is not None)
# A MADE-UP keyword, not a real faction without art yet. This check used
# "NECRONS" and broke the day that badge was added - which is the whole point
# of the check working, but a stand-in that a future faction can turn real is
# a stand-in that will keep breaking. Nothing will ever ship art for this one.
checks.eq("a faction with no badge resolves to nothing",
          sprites.faction_logo_path("NO SUCH FACTION"), None)
checks.eq("...and so does no faction at all", sprites.faction_logo_path(None), None)


# --- 3. the badge row appears only when it can be drawn whole ---------

panel = GameStatusPanel()
tracker = TurnTracker(first_player="Player 1")
BOTH = {"Player 1": "AELDARI", "Player 2": "ORKS"}

row = panel._badge_row(tracker, BOTH)
checks.true("both players' badges are found", row is not None and len(row) == 2)
checks.eq("Player 1 is on the left, in tracker order", [player for player, _, _ in row],
          ["Player 1", "Player 2"])
checks.eq("no factions at all means no badge row", panel._badge_row(tracker, None), None)
checks.eq("...and neither does an empty mapping", panel._badge_row(tracker, {}), None)
checks.eq("one player missing drops the whole row, rather than half-drawing it",
          panel._badge_row(tracker, {"Player 1": "AELDARI"}), None)
checks.eq("a faction with no art drops it too",
          panel._badge_row(tracker, {"Player 1": "AELDARI", "Player 2": "NO SUCH FACTION"}), None)
with no_logo_art():
    checks.eq("A/B: with no badge art at all there is no row",
              panel._badge_row(tracker, BOTH), None)


# --- 4. the labels under the tiles ------------------------------------

width = config.RIGHT_PANEL_WIDTH - 20
checks.eq("short names keep their player prefix",
          panel._badge_labels(panel._badge_row(tracker, BOTH), width),
          ["P1: AELDARI", "P2: ORKS"])

two_tau = {"Player 1": TAU, "Player 2": TAU}
checks.eq("two long names drop the prefix rather than collide",
          panel._badge_labels(panel._badge_row(tracker, two_tau), width),
          [TAU, TAU])
checks.true("...and the prefixed form really would not have fit",
            sum(panel.badge_font.size(t)[0] for t in ("P1: " + TAU, "P2: " + TAU))
            > width - gsp.LABEL_MIN_GAP)


# --- 5. what actually gets drawn --------------------------------------

W, H = config.RIGHT_PANEL_WIDTH, 300
RECT = pygame.Rect(0, 0, W, H)


def render(factions, active):
    tr = TurnTracker(first_player="Player 1")
    tr.active_player = active
    surf = pygame.Surface((W, H))
    surf.fill((0, 0, 0))
    panel.draw(surf, RECT, tr, None, None, player_factions=factions)
    return surf


def tile_rects():
    """Where the two badges land, from the panel's own constants."""
    content_x, content_width = RECT.x + 10, RECT.width - 20
    top = RECT.y + 50 + gsp.SECTION_GAP
    left = pygame.Rect(content_x, top, gsp.LOGO_BOX, gsp.LOGO_BOX)
    right = pygame.Rect(content_x + content_width - gsp.LOGO_BOX, top, gsp.LOGO_BOX, gsp.LOGO_BOX)
    return left, right


def count_color(surf, rect, color, tolerance=40):
    hits = 0
    for x in range(rect.left, rect.right):
        for y in range(rect.top, rect.bottom):
            r, g, b, _ = surf.get_at((x, y))
            if (abs(r - color[0]) <= tolerance
                    and abs(g - color[1]) <= tolerance
                    and abs(b - color[2]) <= tolerance):
                hits += 1
    return hits


left_tile, right_tile = tile_rects()
GOLD = config.PANEL_HEADER_COLOR

p1_active = render(BOTH, "Player 1")
p2_active = render(BOTH, "Player 2")

# The frame is measured in pixels, not read back off the flag that drew it -
# a highlight that is computed and never blitted would pass the latter.
p1_left = count_color(p1_active, left_tile, GOLD)
p1_right = count_color(p1_active, right_tile, GOLD)
p2_left = count_color(p2_active, left_tile, GOLD)
p2_right = count_color(p2_active, right_tile, GOLD)

checks.true("Player 1 active: the left badge is framed in gold", p1_left > 100)
checks.true("...and the right one is not", p1_right < p1_left / 4)
checks.true("Player 2 active: the right badge is framed instead", p2_right > 100)
checks.true("...and the left one is not", p2_left < p2_right / 4)

# Ork green inside the right tile: proof the artwork itself is blitted, not
# just an empty framed square.
checks.true("the Ork badge art is drawn in the right tile",
            count_color(p1_active, right_tile, (94, 166, 93), tolerance=45) > 200)

checks.true("the highlight is what makes the two sides differ",
            abs(p1_left - p1_right) > 100 and abs(p2_left - p2_right) > 100)

checks.true("the two frames mirror each other when the active player swaps",
            abs(p1_left - p2_right) < 30 and abs(p1_right - p2_left) < 30)

with no_logo_art():
    plain_p1 = render(BOTH, "Player 1")
    plain_p2 = render(BOTH, "Player 2")
checks.true("A/B: with no art the same call renders differently",
            pygame.image.tobytes(plain_p1, "RGB") != pygame.image.tobytes(p1_active, "RGB"))
# Deliberately not "no gold at all" in that region: the fallback's own
# full-width Round bar prints its title in the same header gold. The claim
# is that WHO IS ACTIVE stops moving any gold there, which is what having no
# highlight to draw means.
checks.eq("A/B: without badges the active player changes nothing in that region",
          count_color(plain_p1, left_tile, GOLD), count_color(plain_p2, left_tile, GOLD))


# --- 6. the line the badges replaced ----------------------------------

badge_lines = panel._status_lines(tracker, panel._badge_row(tracker, BOTH))
plain_lines = panel._status_lines(tracker, None)
checks.eq("with badges, only the phase is spelled out", badge_lines, ["Command Phase"])
checks.eq("without them the Active Player line is still there",
          plain_lines, ["Command Phase", "Active Player: Player 1"])


# --- 7. CP/VP as one short column per player --------------------------
# Second user request: "die Command Points und Mission Points koennten auch
# nebeneinander in den Spalten stehen / abgekuerzt zu CP: 1 / VP: 24".

class FakeCP:
    def __init__(self, values):
        self.cp = values


class FakeMission:
    def __init__(self, primary, secondary):
        self.primary_points = primary
        self.secondary_points = secondary

    def total_points(self, player):
        return self.primary_points[player] + self.secondary_points[player]


cp = FakeCP({"Player 1": 1, "Player 2": 3})
mission = FakeMission({"Player 1": 12, "Player 2": 9}, {"Player 1": 12, "Player 2": 9})
badges = panel._badge_row(tracker, BOTH)

checks.eq("each player gets a short CP/VP column, in badge order",
          [(player, [text for text, _ in rows])
           for player, rows in panel._score_columns(badges, cp, mission)],
          [("Player 1", ["CP: 1", "VP: 24"]), ("Player 2", ["CP: 3", "VP: 18"])])
checks.eq("with no mission running the column is just CP",
          [text for _, rows in panel._score_columns(badges, cp, None) for text, _ in rows],
          ["CP: 1", "CP: 3"])
checks.eq("with no command points it is just VP",
          [text for _, rows in panel._score_columns(badges, None, mission) for text, _ in rows],
          ["VP: 24", "VP: 18"])
checks.eq("with neither there are no columns to draw",
          panel._score_columns(badges, None, None), [])
checks.true("CP and VP keep the colors they had in the long form",
            [color for _, rows in panel._score_columns(badges, cp, mission) for _, color in rows]
            == [gsp.CP_TEXT_COLOR, gsp.MISSION_TEXT_COLOR] * 2)

# The compact columns REPLACE the two long groups rather than adding a third,
# which is measurable: the button below everything moves up.
tall = pygame.Surface((W, H))
panel.draw(tall, RECT, tracker, cp, mission, player_factions=None)
long_form_button = panel.button_rect.copy()
short = pygame.Surface((W, H))
panel.draw(short, RECT, tracker, cp, mission, player_factions=BOTH)
short_form_button = panel.button_rect.copy()
checks.true("the columns replace the two labelled groups, not add to them",
            short_form_button.top < long_form_button.top - 40)

# ---------------------------------------------------------------------------
# Battle Focus joins the same column, abbreviated
# ---------------------------------------------------------------------------
#
# User: "Battle FOcus kann auch mit in die CP/VP spalte / mit BF abkuerzen" -
# so the Aeldari army rule's tokens are a third row in that player's own
# column instead of a separate full-width group repeating both names.
print("--- 7. Battle Focus in the score column ---")


class FakePool:
    """Only what the panel reads: who gets tokens, and how many."""

    def __init__(self, tokens):
        self.tokens = dict(tokens)
        self.players = tuple(tokens)


pool = FakePool({"Player 1": 4})
badges = panel._badge_row(tracker, BOTH)
columns = panel._score_columns(badges, cp, mission, pool)
texts = {player: [text for text, _color in rows] for player, rows in columns}
checks.eq("the Aeldari column gains a BF row", texts["Player 1"], ["CP: 1", "VP: 24", "BF: 4"])
checks.eq("the Ork column does not - the pool does not name that player",
          texts["Player 2"], ["CP: 3", "VP: 18"])
checks.eq("BF has its own tint, so the three rows stay tellable apart",
          [color for _t, color in columns[0][1]],
          [gsp.CP_TEXT_COLOR, gsp.MISSION_TEXT_COLOR, gsp.BATTLE_FOCUS_TEXT_COLOR])
checks.eq("A/B: with no pool at all the column is CP/VP as before",
          [t for t, _c in panel._score_columns(badges, cp, mission, None)[0][1]],
          ["CP: 1", "VP: 24"])

# ...and the separate full-width "Battle Focus:" group is not ALSO drawn -
# saying it twice is exactly what moving it into the column avoids. Measured
# the same way the CP/VP move was: the button below everything sits higher.
with_group = pygame.Surface((W, H))
panel.draw(with_group, RECT, tracker, cp, mission, battle_focus_pool=pool, player_factions=None)
long_form = panel.button_rect.copy()
in_column = pygame.Surface((W, H))
panel.draw(in_column, RECT, tracker, cp, mission, battle_focus_pool=pool, player_factions=BOTH)
column_form = panel.button_rect.copy()
checks.true("the tokens move into the column rather than adding a group",
            column_form.top < long_form.top - 40)
# Without badges there are no columns to put it in, so the long form stays.
checks.true("a game with no badges keeps the labelled Battle Focus group",
            long_form.top > column_form.top)

checks.finish()
