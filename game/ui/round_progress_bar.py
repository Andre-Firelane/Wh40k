"""The battle's progress as a bar along the top edge of the board.

Replaces the "ROUND n" number the Game Status panel used to print (user: "fuer
die Anzeige der aktuellen runde haette ich gerne anstatt der Zahl einen
schoenen Fortschrittsbalken am oberen Bildschirmrand"). Three things that were
asked for, each of which decides something here:

  * the PHASES may be separated but need no labels - so they are the track's
    finest division and carry no text of their own;
  * the TURN must be labelled - so every turn segment is named, and the one
    being played is named again in full beside the badge;
  * the FACTION logo/colour must be in it - so each turn segment is filled in
    its owner's constant team colour and the current owner's badge sits at the
    left end.

WHAT COUNTS AS "FULL": the whole battle. missions.BATTLE_ROUNDS rounds, two
turns each, five phases per turn - 50 cells, full when the battle is over. The
alternative (just this turn's five phases, with the round as a number beside
it) was put and turned down: it says nothing about how far the game is, which
is the one thing a progress bar is for.

WHERE IT SITS: its own row across the FULL window width, with the board and
both side panels starting underneath it.

That is the second answer to this question, and the first one is worth keeping
because the reason it was wrong is not obvious. The bar was first drawn over
the BOARD only, as chrome on top of the map - the board rect was left alone and
the four things that own the board's top edge (AI badge, dice panel, MENU
button, AI switch) were handed a shortened rect to step down into. It measured
green and looked fine in a screenshot of the strip. Reported: "der balken
ueberdeckt die map. das muss nicht sein" and "die map schliesst jetzt nicht
mehr links und rechts mit den 2 seiten panels ab" - because the map's top edge
had moved 34 px below the panels' top edge, so the three columns no longer
lined up along the top, and the strip ate map instead of occupying space.

Owning a full-width row fixes both at once and is SIMPLER: the board rect now
starts below the bar by construction, so there is no second rect to derive, no
four consumers to re-point, and no way for the MENU button to be drawn from one
rect and clicked against another. The height comes half out of the reserves
panel (the user's own suggestion, "du kannst zb die reserves sektion unten
etwas kleiner machen") and half out of the board column - see
config.RESERVES_PANEL_HEIGHT, which had exactly 14 px of slack over its own
content and now has 4.
"""

import pygame

from game import config, missions, sprites
from game.renderer import TOKEN_TEAM_COLORS
from game.turn import PHASES
from game.ui import button_style, faction_badge

#: The strip's height. Everything inside is derived from it, so this is the one
#: number to change - but it is also a slice off the window that the board and
#: the reserves panel have to give up between them, so it is deliberately tight
#: rather than comfortable: PAD twice, one row of cells and one row of labels.
BAR_HEIGHT = 28
PAD = 3                  # inside the strip, all round
BADGE_TEXT_GAP = 7       # between the faction tile and the text beside it
TEXT_TRACK_GAP = 12      # between that text and the left end of the track

#: Gap between the two turns of the SAME round, and between rounds. The round
#: gap is wider on purpose: it is the only thing that groups the pairs, since
#: the phases inside a turn are drawn as an unbroken run of cells.
TURN_GAP = 2
ROUND_GAP = 7
PHASE_GAP = 1            # hairline between phase cells inside one turn

BG_COLOR = (18, 20, 24)
BORDER_COLOR = button_style.BOX_BORDER_COLOR
#: An unplayed cell. Dark enough to read as empty against BG_COLOR without
#: becoming invisible - the track has to be legible as a track before anything
#: is filled in, which is exactly what the first frame of a battle looks like.
EMPTY_COLOR = (44, 48, 56)
#: A phase that has been played is its owner's colour, dimmed - see _dim().
PLAYED_DIM = 0.55
#: The phase being played right now: full colour plus this outline, so it is
#: findable at a glance on a fifty-cell track.
CURRENT_OUTLINE_COLOR = config.PANEL_HEADER_COLOR
LABEL_COLOR = (150, 165, 180)
#: The current turn's label, in the header gold that means "this is the
#: subject" everywhere else in this UI.
CURRENT_LABEL_COLOR = config.PANEL_HEADER_COLOR

LABEL_FONT_SIZE = 11
TITLE_FONT_SIZE = 13
#: Below this a turn segment gets no label of its own - the round grouping and
#: the colour still say what it is, and squeezing three characters into eight
#: pixels reads as dirt rather than as text.
MIN_SEGMENT_LABEL_WIDTH = 22

_FONTS = {}

#: What the last draw() actually laid out, for anything that has to measure the
#: bar rather than recompute it: the track is whatever is left after the badge
#: and the title text, so a caller (or a test) that derives it a second time is
#: deriving it from different inputs. Same idiom as DicePanel.last_backdrop_rect.
last_track_rect = None
last_badge_rect = None


def _font(size, bold=True):
    key = (size, bold)
    if key not in _FONTS:
        _FONTS[key] = pygame.font.SysFont(config.FONT_NAME, size, bold=bold)
    return _FONTS[key]


def _dim(color, factor):
    return tuple(max(0, min(255, int(channel * factor))) for channel in color[:3])


def bar_rect(window_width):
    """The strip: the full width of the window, at the very top of it.

    Takes the WINDOW width rather than a board rect, because that is the whole
    correction - the bar is a row of the window that the board and the panels
    both start below, not something drawn on top of one of them. Everything
    that used to need a "board minus the bar" rect now simply gets the board
    rect, which already excludes it."""
    return pygame.Rect(0, 0, window_width, BAR_HEIGHT)


def turn_owners(turn_tracker):
    """The owner of every turn of the battle, in order.

    Read off first_player rather than from any per-round record: the same
    player takes the first turn of every battle round, so the whole sequence is
    known from one name - including the turns nobody has played yet, which is
    the half a progress bar exists to show."""
    first = turn_tracker.first_player
    second = turn_tracker._other_player(first)
    out = []
    for _round_index in range(missions.BATTLE_ROUNDS):
        out.append(first)
        out.append(second)
    return out


def current_turn_index(turn_tracker):
    """Which entry of turn_owners() is being played, or None before the battle
    has started.

    Both ends are handled here rather than by each caller: battle_round is 0
    for the whole pre-game (TurnTracker's deferred_start), and it can read one
    PAST the last round in the frame between the final turn ending and the
    battle-end check."""
    if turn_tracker.battle_round < 1:
        return None
    index = (turn_tracker.battle_round - 1) * 2 + turn_tracker.turn_index_in_round
    return min(index, missions.BATTLE_ROUNDS * 2 - 1)


def title_text(turn_tracker):
    """The line beside the badge. Names the TURN in full, which is the one
    thing that was asked to be labelled rather than merely separated."""
    if current_turn_index(turn_tracker) is None:
        return "DEPLOYMENT"
    return "ROUND %d - %s" % (turn_tracker.battle_round,
                              str(turn_tracker.turn_owner).upper())


def draw(surface, window_width, turn_tracker, player_factions=None):
    """Draw the strip and return its rect.

    `player_factions` is main()'s one derivation of {player: faction keyword};
    None, or a player missing from it, simply means no badge - exactly how the
    Game Status panel and the turn banner already treat a factionless side."""
    global last_track_rect, last_badge_rect
    last_track_rect = None
    last_badge_rect = None
    rect = bar_rect(window_width)
    if rect.width <= 0 or rect.height <= 0:
        return rect
    pygame.draw.rect(surface, BG_COLOR, rect)
    pygame.draw.line(surface, BORDER_COLOR, (rect.x, rect.bottom - 1),
                     (rect.right - 1, rect.bottom - 1))

    x = rect.x + PAD
    inner_height = rect.height - 2 * PAD

    keyword = (player_factions or {}).get(turn_tracker.turn_owner)
    logo_path = sprites.faction_logo_path(keyword) if keyword else None
    if faction_badge.has_content(logo_path, keyword):
        tile = pygame.Rect(x, rect.y + PAD, inner_height, inner_height)
        faction_badge.draw(surface, tile, logo_path, active=True, keyword=keyword)
        last_badge_rect = tile
        x = tile.right + BADGE_TEXT_GAP

    title_surf = _font(TITLE_FONT_SIZE).render(title_text(turn_tracker), True,
                                               CURRENT_LABEL_COLOR)
    surface.blit(title_surf, title_surf.get_rect(midleft=(x, rect.centery)))
    x += title_surf.get_width() + TEXT_TRACK_GAP

    track = pygame.Rect(x, rect.y + PAD, rect.right - PAD - x, inner_height)
    if track.width > 0:
        last_track_rect = track
        draw_track(surface, track, turn_tracker)
    return rect


def turn_segments(track, turn_count):
    """Left edge and width of every turn segment, laid out with the wider gap
    between rounds.

    Widths come off a running float and are rounded at each edge rather than
    every segment being given `width // n`: the second form loses up to a pixel
    per segment, which over ten of them is a visible drift of the right-hand
    end away from the track's own right edge."""
    rounds = max(1, turn_count // 2)
    gaps = (rounds - 1) * ROUND_GAP + rounds * TURN_GAP
    usable = max(0, track.width - gaps)
    step = usable / turn_count if turn_count else 0
    out = []
    cursor = float(track.x)
    for index in range(turn_count):
        left = int(round(cursor))
        cursor += step
        right = int(round(cursor))
        out.append(pygame.Rect(left, track.y, max(1, right - left), track.height))
        last = index == turn_count - 1
        cursor += TURN_GAP if index % 2 == 0 else (0 if last else ROUND_GAP)
    return out


def phase_cell(segment, phase_index, phase_count):
    """One phase inside a turn segment. Same running-float rounding as
    turn_segments(), for the same reason one level down."""
    gaps = (phase_count - 1) * PHASE_GAP
    step = max(0.0, segment.width - gaps) / phase_count
    start = segment.x + phase_index * (step + PHASE_GAP)
    left = int(round(start))
    right = int(round(start + step))
    return pygame.Rect(left, segment.y, max(1, right - left), segment.height)


def draw_track(surface, track, turn_tracker):
    owners = turn_owners(turn_tracker)
    playing = current_turn_index(turn_tracker)
    phase_count = len(PHASES)
    phase_now = turn_tracker.phase_index if playing is not None else 0

    label_font = _font(LABEL_FONT_SIZE)
    label_height = label_font.get_height()
    cells = pygame.Rect(track.x, track.y, track.width,
                        max(1, track.height - label_height))

    for index, segment in enumerate(turn_segments(cells, len(owners))):
        owner = owners[index]
        base = TOKEN_TEAM_COLORS.get(owner, EMPTY_COLOR)
        for phase_index in range(phase_count):
            cell = phase_cell(segment, phase_index, phase_count)
            if playing is None or index > playing:
                color = EMPTY_COLOR
            elif index < playing or phase_index < phase_now:
                color = _dim(base, PLAYED_DIM)
            elif phase_index == phase_now:
                color = base
            else:
                color = EMPTY_COLOR
            pygame.draw.rect(surface, color, cell)
            if index == playing and phase_index == phase_now:
                pygame.draw.rect(surface, CURRENT_OUTLINE_COLOR, cell, 1)

        # The turn's own label, short by necessity: ten segments across a
        # 1280 px window leave each one about 70 px. The round number and the
        # owner's digit together name the turn exactly - "3.2" is Player 2's
        # turn in battle round 3 - and the colour underneath repeats the owner.
        if segment.width >= MIN_SEGMENT_LABEL_WIDTH:
            text = "%d.%s" % (index // 2 + 1, str(owner)[-1])
            color = CURRENT_LABEL_COLOR if index == playing else LABEL_COLOR
            label = label_font.render(text, True, color)
            surface.blit(label, label.get_rect(centerx=segment.centerx,
                                               top=cells.bottom))
