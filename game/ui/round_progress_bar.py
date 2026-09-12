"""The battle's progress as a bar along the top edge of the board.

Replaces the "ROUND n" number the Game Status panel used to print (user: "fuer
die Anzeige der aktuellen runde haette ich gerne anstatt der Zahl einen
schoenen Fortschrittsbalken am oberen Bildschirmrand"). Three things that were
asked for, each of which decides something here:

  * the PHASES may be separated but need no labels - so they are the track's
    finest division and carry no text of their own;
  * the TURN must be labelled - so every battle round carries its number ON
    the bar ("1" to "5"), and the turn being played is named again in full
    beside the badge;
  * the FACTION logo/colour must be in it - so each turn segment is filled in
    its owner's constant team colour and the current owner's badge sits at the
    left end.

THE LABEL IS THE ROUND NUMBER, NOT THE PLAYER (user: "die farbe reicht als
player indikator. ich haette aber gerne den Turncounter als Label ueber der
Leiste nicht den Spieler, also 1 2 3 4 5"). The version before this one drew
"P1"/"P2" on every one of the ten turn segments - which said twice what the
cell colour already says, and never said the one thing the colour cannot: how
many rounds in the battle is. So:

  * ONE label per BATTLE ROUND, centred over that round's two turn segments -
    which puts it on the gap between the round's first and second turn, the
    one place that belongs to the round rather than to either player. "Turn"
    in this UI means the battle round (the turn banner reads "Player 2, Turn
    1"), and there are missions.BATTLE_ROUNDS of them, hence 1 to 5;
  * a NEUTRAL light colour, never a team colour - the colour of the cells is
    the player indicator, and a round belongs to both players;
  * the CURRENT round's number in the header gold, the same gold as the title
    beside the badge ("ROUND 3 - PLAYER 2"), so the two read as one statement;
  * a dark outline, because the label sits on cells of every brightness,
    including the full-colour current phase;
  * drawn during DEPLOYMENT too. The P1/P2 labels had to wait for the
    first-turn roll-off (see below); a round number does not depend on who
    goes first, so there is nothing to wait for.

THE LABELS SIT ON THE BAR, NOT UNDER IT, and every turn is in its owner's colour
from the first turn on (user: "momentan sind ganz kleine labels unter den
zugabschnitten. die koennen weg. stattdessen koennen P1 bzw P2 labels direkt auf
der leiste sein ... auch von anfang an in den richtigen farben"). The first
version reserved a row of 11 px text under nine-pixel cells and left every turn
nobody had played yet EMPTY_COLOR grey. That half still stands:

  * the cells get the whole track height, and the label is drawn on top;
  * it is bigger than the text it replaced - 9 px glyphs, against 6 px before;
  * an UPCOMING turn is its owner's colour, dark; a PLAYED phase the same
    colour, brighter; the current phase full plus the outline - three steps of
    one hue, so "whose" and "how far" are both readable at once.

BEFORE THE FIRST-TURN ROLL-OFF THE CELLS STAY NEUTRAL, and that is a fact about
TurnTracker rather than a style choice: a deferred-start tracker is built with a
PLACEHOLDER first_player and told the real one by start_battle(). Colouring the
upcoming turns during deployment would draw an order that can flip the moment
the roll-off is decided, so no colour appears until it is. (The round numbers
do - see above.)

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
four consumers to re-point, and no way for a control up there to be drawn from
one rect and clicked against another. (Three consumers today - the MENU button
has since moved into the right panel's header row, so the AI switch has the
board's corner to itself.) The height comes half out of the reserves
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
#: rather than comfortable: PAD twice and one row of cells, the labels on them.
BAR_HEIGHT = 28
PAD = 3                  # inside the strip, all round
BADGE_TEXT_GAP = 7       # between the faction tile and the text beside it
TEXT_TRACK_GAP = 12      # between that text and the left end of the track

#: Gap between the two turns of the SAME round, and between rounds. The round
#: gap is wider on purpose: together with the round number it groups the pairs,
#: since the phases inside a turn are drawn as an unbroken run of cells.
TURN_GAP = 2
ROUND_GAP = 7
PHASE_GAP = 1            # hairline between phase cells inside one turn

BG_COLOR = (18, 20, 24)
BORDER_COLOR = button_style.BOX_BORDER_COLOR
#: A cell whose owner is not known: the whole track during deployment (the turn
#: order is not decided before the first-turn roll-off), and any owner missing
#: from TOKEN_TEAM_COLORS. Dark enough to read as empty against BG_COLOR without
#: becoming invisible - the track has to be legible as a track before anything
#: is coloured in.
EMPTY_COLOR = (44, 48, 56)
#: Three steps of the OWNER'S colour, darkest first - see cell_color(). A turn
#: nobody has played yet is already its owner's hue, so the bar says whose turn
#: is where from the first turn on; a played phase is brighter; the phase being
#: played is the full colour plus CURRENT_OUTLINE_COLOR.
UPCOMING_DIM = 0.3
PLAYED_DIM = 0.55
#: The phase being played right now: full colour plus this outline, so it is
#: findable at a glance on a fifty-cell track.
CURRENT_OUTLINE_COLOR = config.PANEL_HEADER_COLOR
#: The current turn's title beside the badge, in the header gold that means
#: "this is the subject" everywhere else in this UI.
CURRENT_LABEL_COLOR = config.PANEL_HEADER_COLOR

#: The round number ("1".."5") drawn ON the bar over each battle round.
#:
#: 18 is measured, not picked: pygame's default font is small for its size
#: (at 12 a digit is 6 px tall - no bigger than the labels the user called
#: "ganz klein"), 18 gives 9 px glyphs in the 22 px track, and 20 draws the same
#: 9 px glyphs, only wider.
LABEL_FONT_SIZE = 18
#: Neutral, not a team colour: the CELLS say whose turn is where, and a round
#: belongs to both players.
LABEL_COLOR = (226, 229, 236)
#: The round being played, in the same gold as the title beside the badge.
CURRENT_ROUND_LABEL_COLOR = config.PANEL_HEADER_COLOR
LABEL_OUTLINE_COLOR = (8, 9, 12)
#: Free pixels either side of a label inside its round's span. A span too
#: narrow for that gets no label - the gaps still group the rounds, and text
#: squeezed across the cells of a two-pixel turn reads as dirt rather than text.
LABEL_MARGIN = 2
TITLE_FONT_SIZE = 13

_FONTS = {}

#: What the last draw() actually laid out, for anything that has to measure the
#: bar rather than recompute it: the track is whatever is left after the badge
#: and the title text, so a caller (or a test) that derives it a second time is
#: deriving it from different inputs. Same idiom as DicePanel.last_backdrop_rect.
last_track_rect = None
last_badge_rect = None
#: (round_number, text, rect) of every round label the last draw() blitted, in
#: track order - the blit rect of the text, not the glyphs.
last_label_rects = []


def _font(size, bold=True):
    key = (size, bold)
    if key not in _FONTS:
        _FONTS[key] = pygame.font.SysFont(config.FONT_NAME, size, bold=bold)
    return _FONTS[key]


def _dim(color, factor):
    return tuple(max(0, min(255, int(channel * factor))) for channel in color[:3])


def round_label_color(round_number, current_round):
    """Gold for the round being played, the neutral label colour otherwise.

    `current_round` is None before the battle has started - no round is being
    played yet, so none is highlighted."""
    if current_round is not None and round_number == current_round:
        return CURRENT_ROUND_LABEL_COLOR
    return LABEL_COLOR


def cell_color(owner, turn, phase, playing, phase_now):
    """The fill of one phase cell.

    `playing` is current_turn_index(): None means the battle has not started,
    and then the turn order is not decided yet (see the module docstring), so
    every cell is EMPTY_COLOR. After that every cell carries its owner's hue in
    one of three steps - upcoming, played, current."""
    if playing is None:
        return EMPTY_COLOR
    base = TOKEN_TEAM_COLORS.get(owner, EMPTY_COLOR)
    if turn < playing or (turn == playing and phase < phase_now):
        return _dim(base, PLAYED_DIM)
    if turn == playing and phase == phase_now:
        return tuple(base[:3])
    return _dim(base, UPCOMING_DIM)


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


def current_round(turn_tracker):
    """The battle round being played (1-based), or None before the battle.

    Derived from current_turn_index() rather than read off battle_round, so it
    inherits the one-past-the-end clamp: the gold label can never point at a
    sixth round that is not on the track."""
    playing = current_turn_index(turn_tracker)
    return None if playing is None else playing // 2 + 1


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
    global last_track_rect, last_badge_rect, last_label_rects
    last_track_rect = None
    last_badge_rect = None
    last_label_rects = []
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


def round_spans(track, turn_count):
    """One rect per battle round: from its first turn segment's left edge to
    its second's right edge, the TURN_GAP between them included.

    Built off turn_segments() rather than laid out a second time, so a label
    centred on a span is centred on exactly the cells that were drawn."""
    segments = turn_segments(track, turn_count)
    return [segments[i].union(segments[i + 1]) if i + 1 < len(segments) else segments[i]
            for i in range(0, len(segments), 2)]


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
    global last_label_rects
    owners = turn_owners(turn_tracker)
    playing = current_turn_index(turn_tracker)
    phase_count = len(PHASES)
    phase_now = turn_tracker.phase_index if playing is not None else 0

    # The cells take the WHOLE track height - there is no label row under them.
    for index, segment in enumerate(turn_segments(track, len(owners))):
        owner = owners[index]
        for phase_index in range(phase_count):
            cell = phase_cell(segment, phase_index, phase_count)
            pygame.draw.rect(surface, cell_color(owner, index, phase_index,
                                                 playing, phase_now), cell)
            if index == playing and phase_index == phase_now:
                pygame.draw.rect(surface, CURRENT_OUTLINE_COLOR, cell, 1)

    # The labels AFTER every cell: a round's label spans two turn segments, so
    # drawn inside the loop above its right half would be painted over by the
    # round's second turn.
    font = _font(LABEL_FONT_SIZE)
    now = current_round(turn_tracker)
    labels = []
    rounds = round_spans(track, len(owners))
    for number, span in enumerate(rounds, start=1):
        drawn = _draw_round_label(surface, span, number,
                                  round_label_color(number, now), font)
        if drawn is not None:
            labels.append(drawn)
    last_label_rects = labels


#: A one-pixel ring, diagonals included: at 9 px glyphs a plain drop shadow
#: leaves the digit's left and top edges touching a cell of similar brightness.
_OUTLINE_OFFSETS = ((-1, -1), (0, -1), (1, -1), (-1, 0),
                    (1, 0), (-1, 1), (0, 1), (1, 1))


def _draw_round_label(surface, span, number, color, font):
    """Blit the round number centred on its round's span; return
    (number, text, rect), or None when the span is too narrow for it.

    Centred on the text SURFACE. Centring on the glyph extents from
    font.metrics() was tried for the P1/P2 labels this replaced - measured at
    sizes 12 to 20 it lands on the same row every time."""
    text = str(number)
    ink = font.render(text, True, color)
    rect = ink.get_rect(center=span.center)
    if rect.width + 2 * (LABEL_MARGIN + 1) > span.width:
        return None
    outline = font.render(text, True, LABEL_OUTLINE_COLOR)
    for dx, dy in _OUTLINE_OFFSETS:
        surface.blit(outline, rect.move(dx, dy))
    surface.blit(ink, rect)
    return number, text, rect
